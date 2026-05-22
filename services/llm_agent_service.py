"""
LLM Agent Service — интеллектуальный агент для автоматической обработки писем

Функции:
- Генерация и отправка автоответов
- Извлечение структурированных данных из КП (цены, сроки, условия)
- Анализ контекста диалога для персонализированных ответов
- Режимы: полностью автоматический, с подтверждением, только черновики
"""
import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from loguru import logger

from core.models import Dialogue, Message, Task, SMTPAccount, Profile, Contact, LLMFeedback
from core.database import SessionLocal
from services.llm_service import LLMService
from services.email_service import EmailService
from utils.encryption import encryption
from utils.datetime_helper import now_utc
from config import settings


class LLMAgentService:
    """
    Интеллектуальный агент на базе LLM для автоматизации коммуникаций
    """
    
    # Режимы работы агента
    MODE_DISABLED = "disabled"           # Агент выключен
    MODE_DRAFT_ONLY = "draft_only"       # Только генерировать черновики
    MODE_CONFIRM = "confirm"             # Генерировать + ждать подтверждения
    MODE_AUTO = "auto"                   # Полностью автоматический режим
    
    # Типы писем, на которые агент может отвечать
    SUPPORTED_CATEGORIES = ["question", "auto_reply", "unknown"]
    
    def __init__(self, mode: str = MODE_DRAFT_ONLY):
        """
        Инициализация агента
        
        Args:
            mode: Режим работы (disabled, draft_only, confirm, auto)
        """
        self.mode = mode
        self.llm_service = None
        
        # Инициализация LLM
        if settings.proxyapi_api_key:
            try:
                self.llm_service = LLMService()
                self.llm_service.configure(settings.proxyapi_api_key)
                logger.info(f"LLM Agent инициализирован (режим: {mode})")
            except Exception as e:
                logger.error(f"Не удалось инициализировать LLM Agent: {e}")
        else:
            logger.warning("ProxyAPI ключ не настроен. LLM Agent не будет работать.")
    
    def process_incoming_message(
        self,
        message: Message,
        dialogue: Dialogue,
        db: Session
    ) -> Dict[str, Any]:
        """
        Обработать входящее письмо через LLM-агент
        
        Args:
            message: Входящее сообщение
            dialogue: Диалог
            db: Сессия БД
        
        Returns:
            {
                "action": "draft_created|sent|skipped|error",
                "reply_text": str,
                "kp_data": dict,  # Если извлечены данные КП
                "task_created": bool,
                "confidence": float
            }
        """
        if self.mode == self.MODE_DISABLED:
            return {"action": "skipped", "reason": "agent_disabled"}
        
        if not self.llm_service:
            return {"action": "skipped", "reason": "llm_not_configured"}
        
        try:
            # 1. Анализ письма и контекста
            analysis = self._analyze_message(message, dialogue, db)
            
            # 2. Если письмо содержит КП — извлечь данные
            kp_data = None
            if analysis.get("has_kp", False):
                kp_data = self._extract_kp_data(message, dialogue, db)
                if kp_data:
                    self._save_kp_data(dialogue, kp_data, db)
            
            # 3. Определить, нужен ли ответ
            needs_reply = analysis.get("needs_reply", False)
            category = analysis.get("category", "unknown")
            
            if not needs_reply or category not in self.SUPPORTED_CATEGORIES:
                return {
                    "action": "skipped",
                    "reason": f"category_{category}_not_supported",
                    "kp_data": kp_data
                }
            
            # 4. Сгенерировать ответ
            reply_text = self._generate_reply(message, dialogue, analysis, db)
            
            if not reply_text:
                return {"action": "error", "reason": "empty_reply"}
            
            # 5. Выполнить действие в зависимости от режима
            if self.mode == self.MODE_AUTO:
                # Отправить автоматически
                success = self._send_reply(reply_text, message, dialogue, db)
                return {
                    "action": "sent" if success else "send_failed",
                    "reply_text": reply_text,
                    "kp_data": kp_data,
                    "confidence": analysis.get("confidence", 0.0)
                }
            
            elif self.mode == self.MODE_CONFIRM:
                # Создать задачу с черновиком для подтверждения
                self._create_approval_task(reply_text, message, dialogue, db)
                return {
                    "action": "draft_created",
                    "reply_text": reply_text,
                    "kp_data": kp_data,
                    "task_created": True,
                    "confidence": analysis.get("confidence", 0.0)
                }
            
            else:  # MODE_DRAFT_ONLY
                # Сохранить черновик
                self._save_draft(reply_text, message, dialogue, db)
                return {
                    "action": "draft_created",
                    "reply_text": reply_text,
                    "kp_data": kp_data,
                    "confidence": analysis.get("confidence", 0.0)
                }
        
        except Exception as e:
            logger.error(f"Ошибка обработки письма через LLM Agent: {e}")
            return {"action": "error", "reason": str(e)}
    
    def _analyze_message(
        self,
        message: Message,
        dialogue: Dialogue,
        db: Session
    ) -> Dict[str, Any]:
        """
        Проанализировать письмо и контекст
        
        Returns:
            {
                "category": str,
                "needs_reply": bool,
                "has_kp": bool,
                "confidence": float,
                "sentiment": str,
                "questions": list,
                "urgency": str
            }
        """
        body = message.body_plain or message.body_html or ""
        profile = dialogue.profile
        contact = dialogue.contact
        
        # Получить историю сообщений
        history = self._get_dialogue_history(dialogue, db)
        
        prompt = f"""Проанализируйте входящее письмо и определите:
1. Категория: question (вопрос), kp (коммерческое предложение), refusal (отказ), auto_reply (автоответ), spam, unknown
2. Требуется ли ответ: да/нет
3. Содержит ли письмо КП (цены, сроки): да/нет
4. Уверенность: 0.0-1.0
5. Тональность: positive, neutral, negative
6. Ключевые вопросы (если есть): список
7. Срочность: low, medium, high

Контекст:
- Профиль закупки: {profile.name if profile else "Не указан"}
- Описание: {profile.description[:200] if profile and profile.description else ""}
- Компания отправителя: {contact.company_name or "Не указана"}
- Контакт: {contact.contact_person or "Не указан"}
- История: {len(history)} сообщений

Входящее письмо:
Тема: {message.subject}
От: {message.from_address}
Текст:
{body[:2000]}

Ответьте строго в формате JSON:
{{
    "category": "question",
    "needs_reply": true,
    "has_kp": false,
    "confidence": 0.85,
    "sentiment": "neutral",
    "questions": ["Какие сроки?"],
    "urgency": "medium"
}}"""
        
        try:
            response = self.llm_service.generate_text(prompt, max_tokens=500)
            
            # Извлечь JSON из ответа
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                analysis = json.loads(json_match.group())
                logger.info(f"Анализ письма: {analysis.get('category')}, needs_reply={analysis.get('needs_reply')}")
                return analysis
            else:
                logger.warning("Не удалось распарсить JSON из ответа LLM")
                return {"category": "unknown", "needs_reply": False, "confidence": 0.0}
        
        except Exception as e:
            logger.error(f"Ошибка анализа письма: {e}")
            return {"category": "unknown", "needs_reply": False, "confidence": 0.0}
    
    def _extract_kp_data(
        self,
        message: Message,
        dialogue: Dialogue,
        db: Session
    ) -> Optional[Dict[str, Any]]:
        """
        Извлечь структурированные данные из КП через LLM
        
        Returns:
            {
                "prices": [{"item": str, "price": float, "currency": str, "unit": str}],
                "delivery_terms": str,
                "payment_terms": str,
                "warranty": str,
                "valid_until": str,
                "notes": str,
                "confidence": float
            }
        """
        body = message.body_plain or message.body_html or ""
        profile = dialogue.profile
        
        prompt = f"""Извлеките структурированные данные из коммерческого предложения.

Профиль закупки:
- Название: {profile.name if profile else ""}
- Технические параметры: {json.dumps(profile.tech_params if profile else {}, ensure_ascii=False)}
- Требования: {json.dumps(profile.requirements if profile else {}, ensure_ascii=False)}

Текст КП:
{body[:3000]}

Извлеките следующие данные в формате JSON:
{{
    "prices": [
        {{"item": "Интернет-канал 100 Мбит/с", "price": 5000, "currency": "RUB", "unit": "мес"}}
    ],
    "delivery_terms": "30 дней",
    "payment_terms": "100% предоплата / 50/50 / отсрочка 30 дней",
    "warranty": "12 месяцев",
    "valid_until": "2026-06-30",
    "notes": "Дополнительные условия",
    "confidence": 0.9
}}

Если данные не найдены, используйте null или пустой список."""
        
        try:
            response = self.llm_service.generate_text(prompt, max_tokens=1000)
            
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                kp_data = json.loads(json_match.group())
                logger.info(f"Извлечено {len(kp_data.get('prices', []))} цен из КП")
                return kp_data
            else:
                logger.warning("Не удалось извлечь данные КП из ответа LLM")
                return None
        
        except Exception as e:
            logger.error(f"Ошибка извлечения данных КП: {e}")
            return None
    
    def _load_few_shot_examples(self, db: Session, category: str = "question", limit: int = 3) -> str:
        """
        Загрузить few-shot примеры из обратной связи операторов
        
        Args:
            db: Сессия БД
            category: Категория письма
            limit: Количество примеров
        
        Returns:
            Текст с примерами для промпта
        """
        examples = (
            db.query(LLMFeedback)
            .join(Message)
            .filter(
                LLMFeedback.use_as_few_shot == True,
                LLMFeedback.rating >= 4,
                LLMFeedback.was_sent == True
            )
            .order_by(LLMFeedback.created_at.desc())
            .limit(limit)
            .all()
        )
        
        if not examples:
            return ""
        
        parts = ["\n=== Примеры хороших ответов (для ориентира) ==="]
        for i, ex in enumerate(examples, 1):
            original = ex.message.body_plain or ex.message.body_html or ""
            edited = ex.edited_text or original
            parts.append(f"\nПример {i}:")
            parts.append(f"Входящее письмо: {original[:200]}...")
            parts.append(f"Ответ: {edited[:300]}...")
        
        parts.append("\n=== Конец примеров ===\n")
        return "\n".join(parts)
    
    def _generate_reply(
        self,
        message: Message,
        dialogue: Dialogue,
        analysis: Dict[str, Any],
        db: Session
    ) -> Optional[str]:
        """
        Сгенерировать ответ на письмо
        
        Args:
            message: Входящее сообщение
            dialogue: Диалог
            analysis: Результат анализа
            db: Сессия БД
        
        Returns:
            Текст ответа
        """
        body = message.body_plain or message.body_html or ""
        profile = dialogue.profile
        contact = dialogue.contact
        
        # Получить историю
        history = self._get_dialogue_history(dialogue, db)
        history_text = "\n\n".join([
            f"{'→' if h['direction'] == 'outbound' else '←'} {h['subject']}\n{h['body'][:300]}"
            for h in history[-5:]  # Последние 5 сообщений
        ])
        
        questions = analysis.get("questions", [])
        questions_text = "\n".join([f"- {q}" for q in questions]) if questions else "Нет конкретных вопросов."
        
        # Загрузить few-shot примеры
        few_shot = self._load_few_shot_examples(db, analysis.get("category", "question"))
        
        prompt = f"""Вы — профессиональный менеджер по закупкам телекоммуникационных услуг.
Составьте профессиональный, вежливый и конкретный ответ на письмо поставщика.

Информация о закупке:
- Название: {profile.name if profile else "Телеком-услуги"}
- Описание: {profile.description[:300] if profile and profile.description else ""}
- Технические параметры: {json.dumps(profile.tech_params if profile else {}, ensure_ascii=False)}

Информация о поставщике:
- Компания: {contact.company_name or "Уважаемая компания"}
- Контактное лицо: {contact.contact_person or ""}

История переписки:
{history_text}

Входящее письмо:
Тема: {message.subject}
Текст:
{body[:2000]}

Ключевые вопросы/темы для ответа:
{questions_text}
{few_shot}
Требования к ответу:
1. Начните с вежливого приветствия (обращение по имени/компании)
2. Поблагодарите за ответ/КП/внимание
3. Дайте конкретный ответ на вопросы (если есть)
4. Если это КП — поблагодарите и сообщите сроки рассмотрения
5. Если вопросы по профилю — ответьте максимально подробно
6. Завершите профессионально, укажите контакты для связи
7. Объём: 150-300 слов
8. Тон: деловой, дружелюбный

Напишите только текст письма (без подписи "С уважением, [Имя]" — она будет добавлена автоматически)."""
        
        try:
            reply = self.llm_service.generate_text(prompt, max_tokens=1500)
            
            # Очистка ответа
            reply = reply.strip()
            if reply.startswith("```"):
                reply = reply.split("```")[1] if "```" in reply[3:] else reply
                reply = reply.replace("text", "").strip()
            
            logger.info(f"Сгенерирован ответ ({len(reply)} символов)")
            return reply
        
        except Exception as e:
            logger.error(f"Ошибка генерации ответа: {e}")
            return None
    
    def _send_reply(
        self,
        reply_text: str,
        message: Message,
        dialogue: Dialogue,
        db: Session
    ) -> bool:
        """
        Отправить сгенерированный ответ
        
        Args:
            reply_text: Текст ответа
            message: Исходное сообщение
            dialogue: Диалог
            db: Сессия БД
        
        Returns:
            Успешность отправки
        """
        try:
            # Получить SMTP аккаунт
            smtp_account = db.query(SMTPAccount).filter_by(
                is_active=True, is_primary=True
            ).first()
            
            if not smtp_account:
                logger.error("Нет активного SMTP аккаунта для отправки")
                return False
            
            # Настроить EmailService
            email_service = EmailService()
            email_service.configure(
                smtp_host=smtp_account.smtp_host,
                smtp_port=smtp_account.smtp_port,
                email=smtp_account.email,
                password=encryption.decrypt(smtp_account.password_enc),
                use_tls=smtp_account.smtp_use_tls
            )
            
            # Подготовить письмо
            subject = f"Re: {message.subject}"
            full_body = reply_text + "\n\n---\nС уважением,\nОтдел закупок"
            
            # Отправить
            success = email_service.send_email(
                to_email=message.from_address,
                subject=subject,
                body_html=full_body.replace("\n", "<br>"),
                body_plain=full_body
            )
            
            if success:
                # Сохранить исходящее сообщение
                reply_message = Message(
                    dialogue_id=dialogue.id,
                    direction="outbound",
                    subject=subject,
                    body_plain=full_body,
                    body_html=full_body.replace("\n", "<br>"),
                    from_address=smtp_account.email,
                    to_address=message.from_address,
                    generated_by_llm=True,
                    llm_model=self.llm_service.get_used_model() if self.llm_service else None,
                    status="sent"
                )
                db.add(reply_message)
                
                # Обновить диалог
                dialogue.last_activity = now_utc()
                db.commit()
                
                logger.info(f"Автоответ отправлен: {message.from_address}")
            
            return success
        
        except Exception as e:
            logger.error(f"Ошибка отправки автоответа: {e}")
            return False
    
    def _save_draft(
        self,
        reply_text: str,
        message: Message,
        dialogue: Dialogue,
        db: Session
    ) -> int:
        """
        Сохранить черновик ответа
        
        Returns:
            ID созданного черновика
        """
        draft = Message(
            dialogue_id=dialogue.id,
            direction="outbound",
            subject=f"Re: {message.subject}",
            body_plain=reply_text,
            body_html=reply_text.replace("\n", "<br>"),
            from_address=message.to_address,
            to_address=message.from_address,
            status="draft",
            generated_by_llm=True,
            llm_model=self.llm_service.get_used_model() if self.llm_service else None
        )
        db.add(draft)
        db.commit()
        db.refresh(draft)
        
        logger.info(f"Сохранён черновик ответа #{draft.id}")
        return draft.id
    
    def _create_approval_task(
        self,
        reply_text: str,
        message: Message,
        dialogue: Dialogue,
        db: Session
    ) -> int:
        """
        Создать задачу на подтверждение ответа
        
        Returns:
            ID созданной задачи
        """
        # Сначала сохранить черновик
        draft_id = self._save_draft(reply_text, message, dialogue, db)
        
        # Создать задачу
        task = Task(
            task_type="llm_review",
            title=f"Подтвердить автоответ: {message.subject[:50]}",
            description=f"LLM сгенерировал ответ на письмо от {message.from_address}.\n\n"
                       f"Черновик #{draft_id}:\n{reply_text[:500]}...",
            dialogue_id=dialogue.id,
            priority="medium",
            due_date=now_utc() + timedelta(days=1)
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        
        logger.info(f"Создана задача на подтверждение #{task.id}")
        return task.id
    
    def _save_kp_data(
        self,
        dialogue: Dialogue,
        kp_data: Dict[str, Any],
        db: Session
    ):
        """Сохранить извлечённые данные КП в диалог"""
        dialogue.kp_received = True
        
        # Объединить с существующими данными
        existing = dialogue.kp_data or {}
        existing.update({
            "llm_extracted": kp_data,
            "extracted_at": now_utc().isoformat(),
            "extraction_confidence": kp_data.get("confidence", 0.0)
        })
        dialogue.kp_data = existing
        db.commit()
        
        logger.info(f"Данные КП сохранены для диалога {dialogue.id}")
    
    def _get_dialogue_history(self, dialogue: Dialogue, db: Session) -> List[Dict]:
        """Получить историю сообщений диалога"""
        messages = db.query(Message).filter_by(
            dialogue_id=dialogue.id
        ).order_by(Message.created_at.asc()).all()
        
        return [
            {
                "direction": m.direction,
                "subject": m.subject,
                "body": m.body_plain or m.body_html or "",
                "created_at": m.created_at.isoformat() if m.created_at else None
            }
            for m in messages
        ]
    
    # === Публичные методы ===
    
    def set_mode(self, mode: str):
        """Изменить режим работы агента"""
        if mode not in [self.MODE_DISABLED, self.MODE_DRAFT_ONLY, 
                        self.MODE_CONFIRM, self.MODE_AUTO]:
            raise ValueError(f"Неизвестный режим: {mode}")
        
        self.mode = mode
        logger.info(f"Режим LLM Agent изменён на: {mode}")
    
    def get_status(self) -> Dict[str, Any]:
        """Получить статус агента"""
        return {
            "mode": self.mode,
            "llm_configured": self.llm_service is not None,
            "primary_model": settings.proxyapi_primary_model,
            "fallback_model": settings.proxyapi_fallback_model,
            "supported_categories": self.SUPPORTED_CATEGORIES
        }
    
    def process_unanswered_dialogues(self, db: Session) -> Dict[str, Any]:
        """
        Обработать все неотвеченные диалоги через агента
        
        Returns:
            Статистика обработки
        """
        if self.mode == self.MODE_DISABLED:
            return {"processed": 0, "reason": "agent_disabled"}
        
        # Найти диалоги с вопросами/автоответами
        dialogues = db.query(Dialogue).filter(
            Dialogue.status.in_(["clarifying", "auto_replied"])
        ).all()
        
        stats = {"processed": 0, "drafts": 0, "sent": 0, "errors": 0, "skipped": 0}
        
        for dialogue in dialogues:
            # Получить последнее входящее сообщение
            last_message = db.query(Message).filter_by(
                dialogue_id=dialogue.id,
                direction="inbound"
            ).order_by(Message.created_at.desc()).first()
            
            if not last_message:
                continue
            
            result = self.process_incoming_message(last_message, dialogue, db)
            
            stats["processed"] += 1
            action = result.get("action", "")
            
            if action == "draft_created":
                stats["drafts"] += 1
            elif action == "sent":
                stats["sent"] += 1
            elif action == "error":
                stats["errors"] += 1
            else:
                stats["skipped"] += 1
        
        logger.info(f"Обработано диалогов: {stats['processed']}")
        return stats

    # === Feedback и Few-Shot ===
    
    def save_feedback(
        self,
        db: Session,
        message_id: int,
        rating: int,
        was_edited: bool = False,
        edited_text: Optional[str] = None,
        was_sent: bool = False,
        operator_comment: Optional[str] = None
    ) -> int:
        """
        Сохранить обратную связь на черновик LLM
        
        Args:
            db: Сессия БД
            message_id: ID сообщения (черновика)
            rating: Оценка 1-5
            was_edited: Был ли отредактирован
            edited_text: Отредактированный текст
            was_sent: Был ли отправлен
            operator_comment: Комментарий оператора
        
        Returns:
            ID созданной записи
        """
        # Проверить существующую запись
        existing = db.query(LLMFeedback).filter_by(message_id=message_id).first()
        
        if existing:
            existing.rating = rating
            existing.was_edited = was_edited
            if edited_text:
                existing.edited_text = edited_text
            existing.was_sent = was_sent
            if was_sent:
                existing.sent_at = now_utc()
            if operator_comment:
                existing.operator_comment = operator_comment
            existing.use_as_few_shot = rating >= 4 and was_sent
            db.commit()
            logger.info(f"Обновлён feedback #{existing.id} для сообщения {message_id}")
            return existing.id
        else:
            feedback = LLMFeedback(
                message_id=message_id,
                rating=rating,
                was_edited=was_edited,
                edited_text=edited_text,
                was_sent=was_sent,
                sent_at=now_utc() if was_sent else None,
                operator_comment=operator_comment,
                use_as_few_shot=rating >= 4 and was_sent
            )
            db.add(feedback)
            db.commit()
            db.refresh(feedback)
            logger.info(f"Создан feedback #{feedback.id} для сообщения {message_id}")
            return feedback.id
    
    def get_feedback_stats(self, db: Session) -> Dict[str, Any]:
        """
        Получить статистику по feedback
        
        Returns:
            {
                "total": int,
                "avg_rating": float,
                "sent_count": int,
                "edited_count": int,
                "few_shot_count": int,
                "by_rating": dict
            }
        """
        from sqlalchemy import func
        
        total = db.query(LLMFeedback).count()
        
        if total == 0:
            return {"total": 0, "avg_rating": 0.0, "sent_count": 0, "edited_count": 0, "few_shot_count": 0, "by_rating": {}}
        
        avg_rating = db.query(func.avg(LLMFeedback.rating)).scalar() or 0.0
        sent_count = db.query(LLMFeedback).filter_by(was_sent=True).count()
        edited_count = db.query(LLMFeedback).filter_by(was_edited=True).count()
        few_shot_count = db.query(LLMFeedback).filter_by(use_as_few_shot=True).count()
        
        by_rating = {}
        for rating in range(1, 6):
            count = db.query(LLMFeedback).filter_by(rating=rating).count()
            by_rating[str(rating)] = count
        
        return {
            "total": total,
            "avg_rating": round(float(avg_rating), 2),
            "sent_count": sent_count,
            "edited_count": edited_count,
            "few_shot_count": few_shot_count,
            "by_rating": by_rating
        }
