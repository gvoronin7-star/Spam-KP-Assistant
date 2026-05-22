"""
Сервис входящих писем (IMAP)
"""
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from email import message_from_bytes
from email.header import decode_header
from imaplib import IMAP4_SSL
from sqlalchemy.orm import Session
from loguru import logger

from core.database import SessionLocal
from core.models import (
    SMTPAccount, Dialogue, Message, MailingRecipient, 
    Task, Contact
)
from utils.encryption import encryption
from utils.datetime_helper import now_utc
from services.llm_service import LLMService
from services.llm_agent_service import LLMAgentService
from services.parser_service import ParserService
from services.attachment_parser import AttachmentParser
from services.reminder_service import ReminderService
from services.rule_engine import RuleEngine
from utils.attachment_manager import AttachmentManager
from config import settings


class InboxService:
    """Сервис получения и обработки входящих писем"""
    
    def __init__(self):
        self.llm_service = None
        self.llm_agent = None
        
        # Инициализация LLM, если есть API ключ
        if settings.proxyapi_api_key:
            try:
                self.llm_service = LLMService()
                self.llm_service.configure(settings.proxyapi_api_key)
                logger.info("LLM классификация активирована")
                
                # Инициализация LLM-агента
                self.llm_agent = LLMAgentService(mode=settings.llm_agent_mode)
                logger.info(f"LLM Agent инициализирован (режим: {settings.llm_agent_mode})")
            except Exception as e:
                logger.warning(f"Не удалось настроить LLM: {e}. Будет использоваться keyword-based.")
        else:
            logger.warning("ProxyAPI API ключ не настроен. Будет использоваться keyword-based классификация.")
        
        # Инициализация парсера вложений (новый)
        self.attachment_parser = AttachmentParser()
        
        # Инициализация парсера (старый, для совместимости)
        self.parser = ParserService(llm_service=self.llm_service)
        
        # Инициализация сервиса напоминаний
        self.reminder_service = ReminderService()
        
        # Инициализация Rule Engine (загрузка из БД или defaults)
        self.rule_engine = RuleEngine()
        db_temp = SessionLocal()
        try:
            self.rule_engine.load_from_db(db_temp)
        finally:
            db_temp.close()
        
        # Инициализация менеджера вложений
        self.attachment_manager = AttachmentManager()
        
        self.classification_keywords = {
            "kp": [
                "кп", "коммерческое", "предложение", "прайс", "стоимость", 
                "цена", "прайс-лист", "предлагаем", "предлагаю", "тариф",
                "бесплатно", "руб", "рублей", "₽", "usd", "$", "eur", "€",
                "скидка", "акция", "специальная цена", "стоимость подключения",
                "абонентская плата", "ежемесячно", "в год"
            ],
            "refusal": [
                "не можем", "отказ", "не предоставляем", "не работаем",
                "не оказываем", "не занимаемся", "не услуг", "не сможем",
                "не рассматриваем", "отказываем", "к сожалению, нет",
                "не в наших", "не входит"
            ],
            "question": [
                "вопрос", "уточните", "поясните", "уточнение", "непонятно",
                "не ясно", "как", "какой", "какая", "какие", "когда",
                "где", "почему", "зачем", "что именно", "подробнее",
                "расскажите", "объясните", "?"
            ],
            "auto_reply": [
                "автоответчик", "out of office", "отпуск", "автоматический ответ",
                "auto-reply", "автоматическая", "не в офисе", "away",
                "отсутствую", "буду недоступен", "буду доступен"
            ],
            "spam": [
                "реклама", "рассылка", "подписка", "отписаться", "unsubscribe",
                "предлагаем вам", "выиграй", "акция", "скидки", "распродажа",
                "только сегодня", "успейте", "подарок", "бесплатная доставка"
            ]
        }
    
    # === Получение писем ===
    
    def _fetch_emails(
        self,
        imap_host: str,
        imap_port: int,
        email: str,
        password: str,
        since: Optional[datetime] = None
    ) -> List[Dict]:
        """
        Получить письма с IMAP сервера
        
        Args:
            imap_host: IMAP хост
            imap_port: IMAP порт
            email: Email аккаунт
            password: Пароль
            since: Получать письма с этой даты
        
        Returns:
            Список писем
        """
        emails = []
        
        try:
            with IMAP4_SSL(imap_host, imap_port) as server:
                server.login(email, password)
                server.select('INBOX')
                
                # Поиск писем
                if since:
                    search_criteria = f'(SINCE {since.strftime("%d-%b-%Y")})'
                else:
                    search_criteria = 'ALL'
                
                status, message_ids = server.search(None, search_criteria)
                
                if status != 'OK':
                    logger.warning(f"IMAP search failed: {status}")
                    return emails
                
                # Получить каждое письмо
                for message_id in message_ids[0].split()[:100]:  # Лимит 100 писем
                    status, msg_data = server.fetch(message_id, '(RFC822)')
                    
                    if status != 'OK':
                        continue
                    
                    # Распарсить письмо
                    raw_email = msg_data[0][1]
                    email_message = message_from_bytes(raw_email)
                    
                    # Извлечь данные
                    subject = decode_header(email_message.get('Subject', ''))
                    subject_text = ''
                    for part, encoding in subject:
                        if isinstance(part, bytes):
                            subject_text += part.decode(encoding or 'utf-8', errors='ignore')
                        else:
                            subject_text += part
                    
                    from_header = decode_header(email_message.get('From', ''))
                    from_text = ''
                    for part, encoding in from_header:
                        if isinstance(part, bytes):
                            from_text += part.decode(encoding or 'utf-8', errors='ignore')
                        else:
                            from_text += part
                    
                    # Получить тело письма
                    body_plain = ''
                    body_html = ''
                    
                    if email_message.is_multipart():
                        for part in email_message.walk():
                            content_type = part.get_content_type()
                            content_disposition = str(part.get('Content-Disposition', ''))
                            
                            if 'attachment' in content_disposition:
                                continue
                            
                            if content_type == 'text/plain':
                                try:
                                    body_plain = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                                except:
                                    pass
                            elif content_type == 'text/html':
                                try:
                                    body_html = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                                except:
                                    pass
                    else:
                        try:
                            body_plain = email_message.get_payload(decode=True).decode('utf-8', errors='ignore')
                        except:
                            pass
                    
                    # Извлечь threading заголовки
                    in_reply_to = email_message.get('In-Reply-To', '')
                    references_header = email_message.get('References', '')
                    references = [r.strip() for r in references_header.split() if r.strip()]
                    
                    emails.append({
                        "message_id": email_message.get('Message-ID', ''),
                        "in_reply_to": in_reply_to,
                        "references": references,
                        "from": from_text,
                        "subject": subject_text,
                        "date": email_message.get('Date', ''),
                        "body_plain": body_plain,
                        "body_html": body_html,
                        "attachments": [],
                        "raw": raw_email
                    })
                
                server.logout()
                
                logger.info(f"Получено {len(emails)} писем с {imap_host}")
        
        except Exception as e:
            logger.error(f"Ошибка получения писем: {e}")
        
        return emails
    
    def check_inbox(self, account_id: Optional[int] = None, since: Optional[datetime] = None) -> List[Dict]:
        """
        Проверить почту и получить новые письма
        
        Args:
            account_id: ID аккаунта (если None — основной)
            since: Получать письма с этой даты
        
        Returns:
            Список обработанных писем
        """
        db = SessionLocal()
        try:
            # Получить аккаунт
            if account_id:
                account = db.query(SMTPAccount).filter_by(id=account_id, is_active=True).first()
            else:
                account = db.query(SMTPAccount).filter_by(is_primary=True, is_active=True).first()
            
            if not account:
                logger.warning("Нет активного SMTP аккаунта для проверки почты")
                return []
            
            # Расшифровать пароль
            try:
                password = encryption.decrypt(account.password_enc)
            except Exception as e:
                logger.error(f"Ошибка расшифровки пароля: {e}")
                return []
            
            # Подключиться к IMAP
            emails = self._fetch_emails(
                imap_host=account.imap_host,
                imap_port=account.imap_port,
                email=account.email,
                password=password,
                since=since
            )
            
            # Обработать каждое письмо
            processed = []
            for email_data in emails:
                result = self._process_incoming_email(email_data, db)
                if result:
                    processed.append(result)
            
            # Обновить время последней проверки
            account.last_check = now_utc()
            db.commit()
            
            return processed
        
        except Exception as e:
            logger.error(f"Ошибка проверки почты: {e}")
            db.rollback()
            return []
    
    def _find_dialogue_by_thread(
        self,
        email_data: Dict,
        contact: Contact,
        db: Session
    ) -> Optional[Dialogue]:
        """
        Найти диалог по цепочке писем (threading)
        
        Args:
            email_data: Данные письма
            contact: Контакт отправителя
            db: Сессия БД
        
        Returns:
            Dialogue или None
        """
        message_id = email_data.get("message_id", "")
        if not message_id:
            return None
        
        # 1. Проверить In-Reply-To — письмо ответ на существующее
        in_reply_to = email_data.get("in_reply_to", "")
        if in_reply_to:
            parent_msg = db.query(Message).filter_by(message_id=in_reply_to).first()
            if parent_msg:
                logger.info(f"Threading: найден родитель по In-Reply-To {in_reply_to[:40]}...")
                return parent_msg.dialogue
        
        # 2. Проверить References — цепочка писем
        references = email_data.get("references", [])
        for ref in references:
            ref_msg = db.query(Message).filter_by(message_id=ref).first()
            if ref_msg:
                logger.info(f"Threading: найден родитель по References {ref[:40]}...")
                return ref_msg.dialogue
        
        # 3. Проверить subject без Re:/Fwd: — может быть продолжение диалога
        subject = email_data.get("subject", "")
        clean_subject = re.sub(r'^(Re:|Fwd:|FW:|Ответ:|Пересылка:)\s*', '', subject, flags=re.IGNORECASE).strip()
        
        if clean_subject and clean_subject != subject:
            # Найти диалог с такой же темой
            existing = db.query(Dialogue).join(Message).filter(
                Dialogue.contact_id == contact.id,
                Message.subject.ilike(f"%{clean_subject}%")
            ).order_by(Dialogue.last_activity.desc()).first()
            
            if existing:
                logger.info(f"Threading: найден диалог по теме '{clean_subject}'")
                return existing
        
        return None
    
    def _is_duplicate(self, message_id: str, db: Session) -> bool:
        """
        Проверить, является ли письмо дубликатом
        
        Args:
            message_id: Message-ID письма
            db: Сессия БД
        
        Returns:
            True если дубликат
        """
        if not message_id:
            return False
        
        existing = db.query(Message).filter_by(message_id=message_id).first()
        if existing:
            logger.info(f"Дубликат письма {message_id[:50]}... пропущено")
            return True
        
        return False
    
    def _process_incoming_email(self, email_data: Dict, db: Session) -> Optional[Dict]:
        """
        Обработать одно входящее письмо
        
        Args:
            email_data: Данные письма
            db: Сессия БД
        
        Returns:
            Результат обработки или None
        """
        try:
            # === Дедупликация ===
            message_id = email_data.get("message_id", "")
            if self._is_duplicate(message_id, db):
                return None
            
            # Извлечь email отправителя
            from_email = self._extract_email(email_data["from"])
            if not from_email:
                logger.warning(f"Не удалось извлечь email из: {email_data['from']}")
                return None
            
            # Найти контакт
            contact = db.query(Contact).filter_by(email=from_email).first()
            if not contact:
                logger.info(f"Письмо от неизвестного контакта: {from_email}")
                return None
            
            # === Threading: найти диалог ===
            # Сначала попробовать threading
            dialogue = self._find_dialogue_by_thread(email_data, contact, db)
            
            # Fallback: найти активный диалог по контакту
            if not dialogue:
                dialogue = db.query(Dialogue).filter_by(
                    contact_id=contact.id,
                    status="sent"
                ).order_by(Dialogue.last_activity.desc()).first()
            
            if not dialogue:
                logger.info(f"Нет активного диалога для {from_email}")
                return None
            
            # Классифицировать письмо
            classification = self.classify_response(
                email_data["body_plain"] or "",
                dialogue=dialogue
            )
            
            # Обновить статус диалога
            dialogue.status = self._dialogue_status_from_classification(classification["category"])
            dialogue.last_activity = now_utc()
            
            # Если КП — отметить флаг
            if classification["category"] == "kp":
                dialogue.kp_received = True
            
            # Сохранить сообщение в БД
            message = Message(
                dialogue_id=dialogue.id,
                direction="inbound",
                subject=email_data["subject"],
                body_plain=email_data["body_plain"],
                body_html=email_data["body_html"],
                raw_body=email_data.get("raw", b"").decode("utf-8", errors="ignore") if isinstance(email_data.get("raw"), bytes) else "",
                from_address=from_email,
                to_address=account.email if (account := db.query(SMTPAccount).filter_by(is_primary=True).first()) else "",
                message_id=email_data.get("message_id", ""),
                is_read=False
            )
            db.add(message)
            db.commit()
            db.refresh(message)
            
            # === Парсинг вложений (новый AttachmentParser) ===
            attachment_text = ""
            if email_data.get("raw"):
                from email import message_from_bytes
                try:
                    email_message = message_from_bytes(email_data["raw"])
                    saved = self.attachment_manager.save_attachments_from_email(
                        email_message=email_message,
                        dialogue_id=dialogue.id,
                        message_id=message.id
                    )
                    if saved:
                        # Извлечь текст из вложений для LLM
                        parts = []
                        for att in saved:
                            text = self.attachment_parser.extract_text_for_llm(
                                att["full_path"], max_chars=4000
                            )
                            parts.append(f"=== Вложение: {att['filename']} ===\n{text}")
                        attachment_text = "\n\n".join(parts)
                        message.attachments = saved
                        db.commit()
                except Exception as e:
                    logger.error(f"Ошибка обработки вложений: {e}")
            
            # === LLM Agent: анализ + автоответ / черновик ===
            agent_result = None
            if self.llm_agent and classification["category"] in ["question", "auto_reply", "unknown"]:
                # Обогатить сообщение текстом вложений для анализа
                if attachment_text:
                    message.body_plain = (message.body_plain or "") + "\n\n" + attachment_text
                    db.commit()
                
                agent_result = self.llm_agent.process_incoming_message(message, dialogue, db)
                logger.info(f"LLM Agent результат: {agent_result.get('action')}")
            
            # Если агент извлёк КП из вложений — сохранить
            if agent_result and agent_result.get("kp_data"):
                dialogue.kp_data = agent_result["kp_data"]
                dialogue.kp_received = True
                db.commit()
            
            # Обновить статус получателя рассылки (если есть)
            recipient = db.query(MailingRecipient).filter_by(
                contact_id=contact.id
            ).order_by(MailingRecipient.created_at.desc()).first()
            
            if recipient:
                recipient.replied_at = now_utc()
                recipient.reply_status = classification["category"]
                db.commit()
            
            # Создать задачу оператору (если нужно)
            task = self._create_task_from_response(dialogue, classification, db)
            
            # Создать напоминание (если автоответ или нужно повторить запрос)
            if classification["category"] in ["auto_reply", "unknown"]:
                self.reminder_service.create_reminder_schedule(
                    dialogue=dialogue,
                    reminder_number=1,
                    db=db
                )
            
            # Применить правила Rule Engine
            rule_stats = self.rule_engine.process_message(message, dialogue, db)
            
            logger.info(
                f"Обработано письмо от {from_email}: "
                f"классификация={classification['category']}, "
                f"уверенность={classification['confidence']}, "
                f"agent_action={agent_result.get('action') if agent_result else 'none'}"
            )
            
            return {
                "message_id": email_data.get("message_id", ""),
                "from": from_email,
                "subject": email_data["subject"],
                "classification": classification["category"],
                "confidence": classification["confidence"],
                "summary": classification["summary"],
                "dialogue_id": dialogue.id,
                "task_created": task is not None,
                "agent_action": agent_result.get("action") if agent_result else None,
                "agent_reply": agent_result.get("reply_text") if agent_result else None
            }
        
        except Exception as e:
            logger.error(f"Ошибка обработки входящего письма: {e}")
            db.rollback()
            return None
    
    def _extract_email(self, from_header: str) -> Optional[str]:
        """Извлечь email из заголовка From"""
        # Формат: "Имя <email@domain.com>" или просто "email@domain.com"
        match = re.search(r'<([^>]+)>', from_header)
        if match:
            return match.group(1).lower().strip()
        
        # Попробовать найти email напрямую
        match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', from_header)
        if match:
            return match.group(0).lower().strip()
        
        return None
    
    def _parse_attachments(self, email_data: Dict, db: Session) -> Dict:
        """
        Распарсить вложения письма
        
        Args:
            email_data: Данные письма
            db: Сессия БД
        
        Returns:
            Извлечённые данные КП или пустой dict
        """
        # Найти диалог и сообщение
        dialogue = db.query(Dialogue).filter_by(id=email_data.get("dialogue_id")).first()
        if not dialogue:
            logger.warning("Диалог не найден для сохранения вложений")
            return {}
        
        # Найти сообщение
        message = db.query(Message).filter_by(
            dialogue_id=dialogue.id,
            message_id=email_data.get("message_id")
        ).first()
        
        if not message:
            logger.warning("Сообщение не найдено для сохранения вложений")
            return {}
        
        message_id = message.id
        
        # Извлечь вложения из сырого письма
        from email import message_from_bytes
        from pathlib import Path
        
        try:
            email_message = message_from_bytes(email_data["raw"])
        except Exception as e:
            logger.error(f"Ошибка парсинга сырого письма: {e}")
            return {}
        
        # Сохранить вложения
        saved_attachments = self.attachment_manager.save_attachments_from_email(
            email_message=email_message,
            dialogue_id=dialogue.id,
            message_id=message_id
        )
        
        if not saved_attachments:
            logger.info("Вложений не найдено")
            return {}
        
        # Парсинг каждого вложения
        kp_data = {
            "prices": [],
            "terms": [],
            "notes": "",
            "attachment_count": len(saved_attachments),
            "attachments": saved_attachments,
            "parsed_at": now_utc().isoformat()
        }
        
        for attachment in saved_attachments:
            try:
                file_path = attachment["full_path"]
                
                # Парсинг файла
                file_data = self.parser.parse_file(file_path)
                
                # Объединить результаты
                kp_data["prices"].extend(file_data.get("prices", []))
                kp_data["terms"].extend(file_data.get("terms", []))
                
                if file_data.get("notes"):
                    kp_data["notes"] += f"\n=== {attachment['filename']} ===\n"
                    kp_data["notes"] += file_data["notes"]
            
            except Exception as e:
                logger.error(f"Ошибка парсинга вложения {attachment['filename']}: {e}")
                kp_data["parse_errors"] = kp_data.get("parse_errors", 0) + 1
        
        # Ограничить notes
        if kp_data["notes"]:
            kp_data["notes"] = kp_data["notes"][:5000]
        
        logger.info(
            f"Сохранено и распарсено {len(saved_attachments)} вложений: "
            f"{len(kp_data['prices'])} цен извлечено"
        )
        
        return kp_data
    
    # === Классификация ===
    
    def classify_response(self, email_text: str, dialogue: Optional[Dialogue] = None) -> Dict:
        """
        Классифицировать ответ поставщика (с приоритетом LLM)
        
        Args:
            email_text: Текст письма
            dialogue: Диалог для контекста (опционально)
        
        Returns:
            {
                "category": "kp|question|refusal|auto_reply|spam|unknown",
                "confidence": 0.0-1.0,
                "summary": "краткое содержание",
                "needs_response": true/false,
                "priority": "low|medium|high"
            }
        """
        # 1. Очистить текст от цитат (важно!)
        if self.llm_service:
            email_text = self.llm_service.clean_email_quotes(email_text)
            logger.info(f"Очищено цитат: {len(email_text)} символов")
        
        # 2. Если есть LLM — пробуем сначала его
        if self.llm_service:
            llm_result = self._classify_with_llm(email_text, dialogue)
            
            # Если LLM уверен (>0.5) — используем его результат
            if llm_result["confidence"] > 0.5:
                logger.info(f"LLM классификация: {llm_result['category']} (confidence: {llm_result['confidence']})")
                
                # Добавить черновик ответа, если нужен ответ
                if llm_result.get("needs_response") and dialogue:
                    draft = self.llm_service.generate_reply_draft(
                        email_text,
                        {
                            "profile": dialogue.profile.name if dialogue.profile else "",
                            "contact": dialogue.contact.company_name or "",
                            "previous_messages": 2
                        },
                        llm_result
                    )
                    if draft:
                        llm_result["reply_draft"] = draft
                        logger.info("Сгенерирован черновик ответа")
                
                return llm_result
            
            # Если LLM неуверен или ошибка — fallback на keywords
            logger.info(f"LLM неуверен ({llm_result['confidence']:.2f}), используем keyword-based")
        
        # 3. Fallback на keyword-based
        return self._classify_with_keywords(email_text)
    
    def _classify_with_llm(self, email_text: str, dialogue: Optional[Dialogue] = None) -> Dict:
        """Классификация через LLM"""
        try:
            # Подготовка контекста
            context = None
            if dialogue:
                context = {
                    "profile_name": dialogue.profile.name if dialogue.profile else None,
                    "profile_tech_params": dialogue.profile.tech_params if dialogue.profile else None,
                    "dialogue_status": dialogue.status,
                    "kp_received": dialogue.kp_received,
                    "last_message_date": str(dialogue.last_activity) if dialogue.last_activity else None
                }
            
            return self.llm_service.classify_with_llm(email_text, context)
        
        except Exception as e:
            logger.error(f"Ошибка LLM классификации: {e}")
            return {
                "category": "unknown",
                "confidence": 0.0,
                "summary": f"Ошибка LLM: {str(e)[:100]}"
            }
    
    def _classify_with_keywords(self, email_text: str) -> Dict:
        """
        Классификация через ключевые слова (fallback)
        
        Returns:
            {
                "category": "kp|question|refusal|auto_reply|spam|unknown",
                "confidence": 0.0-1.0,
                "summary": "краткое содержание"
            }
        """
        if not email_text:
            return {"category": "unknown", "confidence": 0.0, "summary": "Пустое письмо"}
        
        text_lower = email_text.lower()
        
        # Подсчёт совпадений для каждой категории
        scores = {}
        for category, keywords in self.classification_keywords.items():
            score = 0
            for keyword in keywords:
                if keyword in text_lower:
                    score += 1
            scores[category] = score
        
        # Дополнительные эвристики
        # Если письмо короткое и содержит "спасибо" — вероятно автоответ
        if len(email_text) < 200 and any(word in text_lower for word in ["спасибо", "благодарим", "получили"]):
            scores["auto_reply"] = scores.get("auto_reply", 0) + 2
        
        # Если есть вложения PDF/DOCX — вероятно КП
        if any(ext in text_lower for ext in [".pdf", ".docx", ".xlsx", ".xls"]):
            scores["kp"] = scores.get("kp", 0) + 3
        
        # Если много вопросительных знаков — вопрос
        question_marks = text_lower.count("?")
        if question_marks >= 2:
            scores["question"] = scores.get("question", 0) + question_marks
        
        # Определить победителя
        if not scores or max(scores.values()) == 0:
            return {"category": "unknown", "confidence": 0.3, "summary": "Не удалось классифицировать"}
        
        best_category = max(scores, key=scores.get)
        best_score = scores[best_category]
        total_score = sum(scores.values())
        
        # Рассчитать уверенность
        confidence = best_score / total_score if total_score > 0 else 0.0
        
        # Генерация summary
        summary = self._generate_summary(email_text, best_category)
        
        return {
            "category": best_category,
            "confidence": round(confidence, 2),
            "summary": summary
        }
    
    def _dialogue_status_from_classification(self, category: str) -> str:
        """Преобразовать классификацию в статус диалога"""
        mapping = {
            "kp": "kp_received",
            "question": "clarifying",
            "refusal": "rejected",
            "auto_reply": "auto_replied",
            "spam": "spam",
            "unknown": "clarifying"
        }
        return mapping.get(category, "clarifying")
    
    def _generate_summary(self, email_text: str, category: str) -> str:
        """Сгенерировать краткое содержание"""
        # Простая эвристика: первые 100 символов
        summary = email_text[:100].replace("\n", " ").strip()
        
        if category == "kp":
            return f"КП получено: {summary}..."
        elif category == "question":
            return f"Вопрос: {summary}..."
        elif category == "refusal":
            return f"Отказ: {summary}..."
        elif category == "auto_reply":
            return f"Автоответ: {summary}..."
        else:
            return f"{summary}..."
    
    # === Создание задач ===
    
    def _create_task_from_response(
        self,
        dialogue: Dialogue,
        classification: Dict,
        db: Session
    ) -> Optional[Task]:
        """Создать задачу оператору на основе классификации"""
        category = classification["category"]
        
        # Настройки дедлайнов (в днях)
        deadline_config = {
            "kp": {"priority": "high", "days": 3},
            "question": {"priority": "medium", "days": 5},
            "refusal": {"priority": "low", "days": 7},
            "auto_reply": {"priority": "low", "days": 10}
        }
        
        config = deadline_config.get(category)
        if not config:
            return None
        
        # Вычисление дедлайна
        due_date = now_utc() + timedelta(days=config["days"])
        
        task_configs = {
            "kp": {
                "task_type": "review_kp",
                "title": f"Разобрать КП от {dialogue.contact.company_name or dialogue.contact.email}",
                "description": f"Получено коммерческое предложение. Уверенность классификации: {classification['confidence']:.0%}"
            },
            "question": {
                "task_type": "respond_question",
                "title": f"Ответить на вопрос от {dialogue.contact.company_name or dialogue.contact.email}",
                "description": f"Поставщик задал вопросы. Уверенность: {classification['confidence']:.0%}"
            },
            "refusal": {
                "task_type": "review_refusal",
                "title": f"Проверить отказ от {dialogue.contact.company_name or dialogue.contact.email}",
                "description": f"Поставщик отказал. Уверенность: {classification['confidence']:.0%}"
            },
            "auto_reply": {
                "task_type": "check_auto_reply",
                "title": f"Автоответ от {dialogue.contact.company_name or dialogue.contact.email}",
                "description": f"Получен автоответ. Нужно повторить запрос позже. Уверенность: {classification['confidence']:.0%}"
            }
        }
        
        task_config = task_configs[category]
        
        task = Task(
            task_type=task_config["task_type"],
            title=task_config["title"],
            description=task_config["description"],
            dialogue_id=dialogue.id,
            priority=config["priority"],
            due_date=due_date,
            is_completed=False
        )
        db.add(task)
        db.commit()
        
        logger.info(
            f"Создана задача: {task.title} "
            f"(приоритет: {task.priority}, дедлайн: {due_date.strftime('%d.%m.%Y')})"
        )
        return task
    
    # === Публичные методы ===
    
    def get_unanswered_dialogues(self, days: int = 3) -> List[Dict]:
        """Получить диалоги без ответа более N дней"""
        db = SessionLocal()
        try:
            since = now_utc() - timedelta(days=days)
            
            dialogues = db.query(Dialogue).filter(
                Dialogue.status.in_(["sent", "reminder_sent"]),
                Dialogue.last_activity < since
            ).all()
            
            return [
                {
                    "id": d.id,
                    "contact_email": d.contact.email,
                    "contact_company": d.contact.company_name,
                    "profile_name": d.profile.name if d.profile else "",
                    "last_activity": d.last_activity,
                    "days_without_response": (now_utc() - d.last_activity).days
                }
                for d in dialogues
            ]
        finally:
            db.close()

    def check_and_send_reminders(self) -> Dict:
        """
        Проверить и отправить запланированные напоминания
        
        Returns:
            Статистика отправки напоминаний
        """
        db = SessionLocal()
        try:
            # Сначала создать новые расписания для диалогов без ответа
            created_count = self.reminder_service.schedule_all_reminders(db)
            
            # Затем отправить все просроченные напоминания
            stats = self.reminder_service.send_due_reminders(db)
            
            # Добавить количество созданных расписаний
            stats["created"] = created_count
            
            logger.info(
                f"Проверка напоминаний: создано {created_count}, "
                f"отправлено {stats['sent']}, ошибок {stats['errors']}"
            )
            
            return stats
        finally:
            db.close()
