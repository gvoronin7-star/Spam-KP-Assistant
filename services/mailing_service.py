"""
Сервис управления рассылками
"""
import asyncio
import random
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Callable
from sqlalchemy.orm import Session
from loguru import logger

from core.database import SessionLocal
from core.models import Mailing, MailingRecipient, Contact, Profile, Template, SMTPAccount, Dialogue, Message
from services.email_service import EmailService
from services.template_service import TemplateService
from services.profile_service import ProfileService
from utils.encryption import encryption
from utils.datetime_helper import now_utc


class MailingService:
    """Сервис управления email-рассылками"""
    
    def __init__(self):
        self._stop_event = asyncio.Event()
        self._current_mailing_id: Optional[int] = None
        self._paused = False
    
        # Callback'и для GUI-уведомлений
        self.on_progress: Optional[Callable[[int, int, int], None]] = None  # sent, total, errors
        self.on_recipient: Optional[Callable[[str, bool, str], None]] = None  # email, success, message
        self.on_log: Optional[Callable[[str], None]] = None  # текст лога
        self.on_finished: Optional[Callable[[bool, str], None]] = None  # success, message
    
    # === CRUD операции ===
    
    def create_mailing(
        self,
        name: str,
        profile_id: int,
        template_id: int,
        contact_ids: List[int],
        smtp_account_id: int,
        delay_min: int = 5,
        delay_max: int = 30,
        hourly_limit: int = 50,
        daily_limit: int = 200,
        scheduled_at: Optional[datetime] = None
    ) -> int:
        """
        Создать новую рассылку
        
        Returns:
            ID созданной рассылки
        """
        db = SessionLocal()
        try:
            # Создать рассылку
            mailing = Mailing(
                name=name,
                profile_id=profile_id,
                template_id=template_id,
                smtp_account_id=smtp_account_id,
                status="draft",
                delay_min=delay_min,
                delay_max=delay_max,
                hourly_limit=hourly_limit,
                daily_limit=daily_limit,
                total_recipients=len(contact_ids),
                scheduled_at=scheduled_at
            )
            db.add(mailing)
            db.commit()
            db.refresh(mailing)
            
            # Создать получателей
            for contact_id in contact_ids:
                recipient = MailingRecipient(
                    mailing_id=mailing.id,
                    contact_id=contact_id,
                    status="pending"
                )
                db.add(recipient)
            
            db.commit()
            logger.info(f"Рассылка создана: ID={mailing.id}, получателей={len(contact_ids)}")
            return mailing.id
        
        finally:
            db.close()
    
    def get_mailing(self, mailing_id: int) -> Optional[Dict]:
        """Получить информацию о рассылке"""
        db = SessionLocal()
        try:
            mailing = db.query(Mailing).filter_by(id=mailing_id).first()
            if not mailing:
                return None
            
            return {
                "id": mailing.id,
                "name": mailing.name,
                "status": mailing.status,
                "total_recipients": mailing.total_recipients,
                "sent_count": mailing.sent_count,
                "error_count": mailing.error_count,
                "delay_min": mailing.delay_min,
                "delay_max": mailing.delay_max,
                "hourly_limit": mailing.hourly_limit,
                "daily_limit": mailing.daily_limit,
                "started_at": mailing.started_at,
                "completed_at": mailing.completed_at,
                "created_at": mailing.created_at
            }
        finally:
            db.close()
    
    def get_mailings(self, status: Optional[str] = None) -> List[Dict]:
        """Получить список рассылок"""
        db = SessionLocal()
        try:
            query = db.query(Mailing)
            if status:
                query = query.filter_by(status=status)
            
            mailings = query.order_by(Mailing.created_at.desc()).all()
            
            return [
                {
                    "id": m.id,
                    "name": m.name,
                    "status": m.status,
                    "total_recipients": m.total_recipients,
                    "sent_count": m.sent_count,
                    "error_count": m.error_count,
                    "progress": f"{m.sent_count}/{m.total_recipients}" if m.total_recipients > 0 else "0/0",
                    "created_at": m.created_at
                }
                for m in mailings
            ]
        finally:
            db.close()
    
    def get_mailing_recipients(self, mailing_id: int) -> List[Dict]:
        """Получить список получателей рассылки"""
        db = SessionLocal()
        try:
            recipients = db.query(MailingRecipient).filter_by(mailing_id=mailing_id).all()
            return [
                {
                    "id": r.id,
                    "contact_email": r.contact.email if r.contact else "",
                    "contact_company": r.contact.company_name if r.contact else "",
                    "status": r.status,
                    "sent_at": r.sent_at,
                    "error_message": r.error_message,
                    "replied_at": r.replied_at,
                    "reply_status": r.reply_status
                }
                for r in recipients
            ]
        finally:
            db.close()
    
    def update_mailing(self, mailing_id: int, **kwargs) -> bool:
        """Обновить параметры рассылки (только в статусе draft)"""
        db = SessionLocal()
        try:
            mailing = db.query(Mailing).filter_by(id=mailing_id, status="draft").first()
            if not mailing:
                return False
            
            for key, value in kwargs.items():
                if hasattr(mailing, key):
                    setattr(mailing, key, value)
            
            db.commit()
            logger.info(f"Рассылка {mailing_id} обновлена")
            return True
        finally:
            db.close()
    
    def delete_mailing(self, mailing_id: int) -> bool:
        """Удалить рассылку (только в статусе draft)"""
        db = SessionLocal()
        try:
            mailing = db.query(Mailing).filter_by(id=mailing_id, status="draft").first()
            if not mailing:
                return False
            
            db.delete(mailing)
            db.commit()
            logger.info(f"Рассылка {mailing_id} удалена")
            return True
        finally:
            db.close()
    
    # === Управление отправкой ===
    
    async def start_mailing(self, mailing_id: int) -> bool:
        """
        Запустить рассылку
        
        Returns:
            True если запущена успешно
        """
        db = SessionLocal()
        try:
            mailing = db.query(Mailing).filter_by(id=mailing_id).first()
            if not mailing:
                logger.error(f"Рассылка {mailing_id} не найдена")
                return False
            
            if mailing.status not in ["draft", "paused"]:
                logger.warning(f"Нельзя запустить рассылку в статусе {mailing.status}")
                return False
            
            # Обновить статус
            mailing.status = "sending"
            if not mailing.started_at:
                mailing.started_at = now_utc()
            db.commit()
            
            self._stop_event.clear()
            self._paused = False
            self._current_mailing_id = mailing_id
            
            logger.info(f"Рассылка {mailing_id} запущена")
            
            # Запустить цикл отправки
            await self._send_loop(mailing_id)
            
            return True
        finally:
            db.close()
    
    def pause_mailing(self, mailing_id: int) -> bool:
        """Приостановить рассылку"""
        if self._current_mailing_id != mailing_id:
            return False
        
        self._paused = True
        
        db = SessionLocal()
        try:
            mailing = db.query(Mailing).filter_by(id=mailing_id).first()
            if mailing:
                mailing.status = "paused"
                db.commit()
                logger.info(f"Рассылка {mailing_id} приостановлена")
        finally:
            db.close()
        
        return True
    
    def resume_mailing(self, mailing_id: int) -> bool:
        """Возобновить рассылку"""
        if self._current_mailing_id != mailing_id:
            return False
        
        self._paused = False
        
        db = SessionLocal()
        try:
            mailing = db.query(Mailing).filter_by(id=mailing_id).first()
            if mailing:
                mailing.status = "sending"
                db.commit()
                logger.info(f"Рассылка {mailing_id} возобновлена")
        finally:
            db.close()
        
        return True
    
    def cancel_mailing(self, mailing_id: int) -> bool:
        """Отменить рассылку"""
        self._stop_event.set()
        self._current_mailing_id = None
        
        db = SessionLocal()
        try:
            mailing = db.query(Mailing).filter_by(id=mailing_id).first()
            if not mailing:
                return False
            
            mailing.status = "cancelled"
            db.commit()
            logger.info(f"Рассылка {mailing_id} отменена")
            return True
        finally:
            db.close()
    
    # === Основной цикл отправки ===
    
    async def _interruptible_sleep(self, seconds: int) -> bool:
        """Прерываемый sleep. Возвращает True, если был прерван."""
        for _ in range(seconds):
            if self._stop_event.is_set():
                return True
            if self._paused:
                return False
            await asyncio.sleep(1)
        return False
    
    async def _send_loop(self, mailing_id: int):
        """Цикл отправки писем"""
        db = SessionLocal()
        try:
            mailing = db.query(Mailing).filter_by(id=mailing_id).first()
            if not mailing:
                return
            
            # Получить данные для отправки (с кэшированием)
            template_service = TemplateService()
            profile_service = ProfileService()
            
            profile = profile_service.get_by_id(mailing.profile_id, db)
            template = template_service.get_by_id(mailing.template_id, db)
            smtp_account = db.query(SMTPAccount).filter_by(id=mailing.smtp_account_id).first()
            
            if not all([profile, template, smtp_account]):
                logger.error("Отсутствуют необходимые данные для рассылки")
                mailing.status = "error"
                db.commit()
                if self.on_log:
                    self.on_log("❌ Отсутствуют необходимые данные для рассылки")
                if self.on_finished:
                    self.on_finished(False, "Отсутствуют необходимые данные для рассылки")
                return
            
            # Настроить EmailService
            email_service = EmailService()
            email_service.configure(
                smtp_host=smtp_account.smtp_host,
                smtp_port=smtp_account.smtp_port,
                email=smtp_account.email,
                password=encryption.decrypt(smtp_account.password_enc),
                use_tls=smtp_account.smtp_use_tls
            )
            
            # Счётчики
            hourly_count = 0
            hourly_start = now_utc()
            daily_count = 0
            daily_start = now_utc()
            
            while not self._stop_event.is_set():
                # Проверить паузу
                if self._paused:
                    if self.on_log:
                        self.on_log("⏸️ Рассылка на паузе...")
                    await asyncio.sleep(1)
                    continue
                
                # 1. Получить следующего получателя
                recipient = self._get_next_recipient(mailing_id, db)
                if not recipient:
                    logger.info(f"Рассылка {mailing_id} завершена: все получатели обработаны")
                    if self.on_log:
                        self.on_log("✅ Все получатели обработаны")
                    break
                
                # 2. Проверить лимиты
                now = now_utc()
                
                # Почасовой лимит
                if now - hourly_start >= timedelta(hours=1):
                    hourly_count = 0
                    hourly_start = now
                
                if hourly_count >= mailing.hourly_limit:
                    wait_seconds = 60 - (now - hourly_start).seconds % 60
                    logger.info(f"Почасовой лимит достигнут. Ожидание {wait_seconds} сек")
                    if self.on_log:
                        self.on_log(f"⏳ Почасовой лимит достигнут. Ожидание {wait_seconds} сек...")
                    interrupted = await self._interruptible_sleep(wait_seconds)
                    if interrupted:
                        break
                    continue
                
                # Посуточный лимит
                if now - daily_start >= timedelta(days=1):
                    daily_count = 0
                    daily_start = now
                
                if daily_count >= mailing.daily_limit:
                    logger.info("Посуточный лимит достигнут. Ожидание до завтра")
                    if self.on_log:
                        self.on_log("⏳ Посуточный лимит достигнут. Ожидание 1 час...")
                    interrupted = await self._interruptible_sleep(3600)
                    if interrupted:
                        break
                    continue
                
                # 3. Сгенерировать письмо
                try:
                    email_data = self._compose_email(profile, template, recipient, db)
                except Exception as e:
                    logger.error(f"Ошибка генерации письма для {recipient.contact.email}: {e}")
                    self._mark_error(recipient.id, f"Ошибка генерации: {e}", db)
                    if self.on_recipient:
                        self.on_recipient(recipient.contact.email, False, f"Ошибка генерации: {e}")
                    continue
                
                # 4. Отправить письмо
                try:
                    success = email_service.send_email(
                        to_email=recipient.contact.email,
                        subject=email_data["subject"],
                        body_html=email_data["body_html"],
                        body_plain=email_data["body_plain"]
                    )
                except Exception as e:
                    logger.error(f"Ошибка отправки письма {recipient.contact.email}: {e}")
                    success = False
                
                # 5. Обновить статус
                if success:
                    self._mark_sent(recipient.id, email_data.get("message_id"), db)
                    hourly_count += 1
                    daily_count += 1
                    
                    # Создать диалог и сообщение
                    self._create_dialogue_and_message(mailing_id, recipient, email_data, db)
                    
                    if self.on_recipient:
                        self.on_recipient(recipient.contact.email, True, "Отправлено успешно")
                    if self.on_log:
                        self.on_log(f"✅ {recipient.contact.email}: отправлено")
                else:
                    self._mark_error(recipient.id, "Ошибка отправки через SMTP", db)
                    if self.on_recipient:
                        self.on_recipient(recipient.contact.email, False, "Ошибка отправки через SMTP")
                    if self.on_log:
                        self.on_log(f"❌ {recipient.contact.email}: ошибка отправки")
                
                # 6. Обновить прогресс рассылки
                self._update_mailing_progress(mailing_id, db)
                
                # Отправить прогресс через callback
                if self.on_progress:
                    stats = self.get_statistics(mailing_id)
                    self.on_progress(
                        stats.get("sent", 0),
                        stats.get("total", 0),
                        stats.get("errors", 0)
                    )
                
                # 7. Задержка перед следующим письмом
                delay = random.randint(mailing.delay_min, mailing.delay_max)
                logger.debug(f"Задержка {delay} сек перед следующим письмом")
                if self.on_log:
                    self.on_log(f"⏳ Задержка {delay} сек перед следующим письмом...")
                interrupted = await self._interruptible_sleep(delay)
                if interrupted:
                    logger.info(f"Рассылка {mailing_id} прервана во время задержки")
                    break
            
            # Завершение рассылки
            if not self._stop_event.is_set():
                self._finalize_mailing(mailing_id)
                if self.on_finished:
                    stats = self.get_statistics(mailing_id)
                    self.on_finished(
                        True,
                        f"Рассылка завершена! Отправлено: {stats.get('sent', 0)}, Ошибок: {stats.get('errors', 0)}"
                    )
            else:
                if self.on_finished:
                    self.on_finished(False, "Рассылка отменена")
        
        except Exception as e:
            logger.error(f"Критическая ошибка в цикле отправки: {e}")
            self._finalize_mailing(mailing_id, error=True)
            if self.on_finished:
                self.on_finished(False, f"Критическая ошибка: {e}")
        
        finally:
            db.close()
        
    # === Вспомогательные методы ===
    
    def _get_next_recipient(self, mailing_id: int, db: Optional[Session] = None) -> Optional[MailingRecipient]:
        """Получить следующего получателя со статусом pending"""
        should_close = db is None
        db = db or SessionLocal()
        try:
            recipient = db.query(MailingRecipient).filter_by(
                mailing_id=mailing_id,
                status="pending"
            ).first()
            return recipient
        finally:
            if should_close:
                db.close()
    
    def _compose_email(
        self,
        profile: Profile,
        template: Template,
        recipient: MailingRecipient,
        db: Session
    ) -> Dict:
        """Сгенерировать письмо с подстановкой переменных"""
        contact = recipient.contact
        
        # Переменные для подстановки
        variables = {
            "company": contact.company_name or "",
            "contact_person": contact.contact_person or "",
            "service_name": profile.name or "",
            "profile_description": profile.description or "",
            "operator_name": "Ваша компания",  # TODO: Взять из настроек
            "request_date": now_utc().strftime("%d.%m.%Y")
        }
        
        # Подстановка в тему
        subject = template.subject or "Запрос коммерческого предложения"
        for key, value in variables.items():
            subject = subject.replace(f"{{{{ {key} }}}}", str(value))
            subject = subject.replace(f"{{{{{key}}}}}", str(value))
        
        # Подстановка в текст
        body_plain = template.body_plain or ""
        body_html = template.body_html or ""
        
        for key, value in variables.items():
            body_plain = body_plain.replace(f"{{{{ {key} }}}}", str(value))
            body_plain = body_plain.replace(f"{{{{{key}}}}}", str(value))
            body_html = body_html.replace(f"{{{{ {key} }}}}", str(value))
            body_html = body_html.replace(f"{{{{{key}}}}}", str(value))
        
        return {
            "subject": subject,
            "body_plain": body_plain,
            "body_html": body_html,
            "message_id": f"<{now_utc().timestamp()}-{recipient.id}@spam-kp>"
        }
    
    def _mark_sent(self, recipient_id: int, message_id: Optional[str], db: Optional[Session] = None):
        """Отметить получателя как отправленного"""
        should_close = db is None
        db = db or SessionLocal()
        try:
            recipient = db.query(MailingRecipient).filter_by(id=recipient_id).first()
            if recipient:
                recipient.status = "sent"
                recipient.sent_at = now_utc()
                recipient.message_id = message_id
                db.commit()
                logger.debug(f"Получатель {recipient_id} отмечен как sent")
        finally:
            if should_close:
                db.close()
    
    def _mark_error(self, recipient_id: int, error_message: str, db: Optional[Session] = None):
        """Отметить получателя с ошибкой"""
        should_close = db is None
        db = db or SessionLocal()
        try:
            recipient = db.query(MailingRecipient).filter_by(id=recipient_id).first()
            if recipient:
                recipient.status = "error"
                recipient.error_message = error_message
                db.commit()
                logger.debug(f"Получатель {recipient_id} отмечен с ошибкой: {error_message}")
        finally:
            if should_close:
                db.close()
    
    def _create_dialogue_and_message(
        self,
        mailing_id: int,
        recipient: MailingRecipient,
        email_data: Dict,
        db: Session
    ):
        """Создать диалог и исходящее сообщение"""
        try:
            # Найти или создать диалог
            dialogue = db.query(Dialogue).filter_by(
                contact_id=recipient.contact_id,
                profile_id=db.query(Mailing).filter_by(id=mailing_id).first().profile_id
            ).first()
            
            if not dialogue:
                mailing = db.query(Mailing).filter_by(id=mailing_id).first()
                dialogue = Dialogue(
                    contact_id=recipient.contact_id,
                    profile_id=mailing.profile_id if mailing else None,
                    mailing_id=mailing_id,
                    status="sent"
                )
                db.add(dialogue)
                db.flush()  # flush вместо commit, чтобы получить id
                db.refresh(dialogue)
            
            # Создать сообщение
            message = Message(
                dialogue_id=dialogue.id,
                direction="outbound",
                subject=email_data["subject"],
                body_plain=email_data["body_plain"],
                body_html=email_data["body_html"],
                to_address=recipient.contact.email,
                message_id=email_data.get("message_id"),
                status="sent"
            )
            db.add(message)
            db.flush()
            
            logger.debug(f"Создан диалог {dialogue.id} и сообщение для {recipient.contact.email}")
        
        except Exception as e:
            logger.error(f"Ошибка создания диалога: {e}")
            db.rollback()
    
    def _update_mailing_progress(self, mailing_id: int, db: Optional[Session] = None):
        """Обновить прогресс рассылки"""
        should_close = db is None
        db = db or SessionLocal()
        try:
            mailing = db.query(Mailing).filter_by(id=mailing_id).first()
            if not mailing:
                return
            
            sent_count = db.query(MailingRecipient).filter_by(
                mailing_id=mailing_id,
                status="sent"
            ).count()
            
            error_count = db.query(MailingRecipient).filter_by(
                mailing_id=mailing_id,
                status="error"
            ).count()
            
            mailing.sent_count = sent_count
            mailing.error_count = error_count
            db.commit()
            
            logger.info(f"Рассылка {mailing_id}: отправлено {sent_count}/{mailing.total_recipients}")
        finally:
            if should_close:
                db.close()
    
    def _finalize_mailing(self, mailing_id: int, error: bool = False):
        """Завершить рассылку"""
        db = SessionLocal()
        try:
            mailing = db.query(Mailing).filter_by(id=mailing_id).first()
            if not mailing:
                return
            
            if error:
                mailing.status = "error"
            else:
                mailing.status = "completed"
            
            mailing.completed_at = now_utc()
            db.commit()
            
            logger.info(f"Рассылка {mailing_id} завершена со статусом {mailing.status}")
        finally:
            db.close()
        
        self._current_mailing_id = None
    
    # === Статистика ===
    
    def get_statistics(self, mailing_id: int) -> Dict:
        """Получить детальную статистику рассылки"""
        db = SessionLocal()
        try:
            mailing = db.query(Mailing).filter_by(id=mailing_id).first()
            if not mailing:
                return {}
            
            recipients = db.query(MailingRecipient).filter_by(mailing_id=mailing_id).all()
            
            status_counts = {}
            for r in recipients:
                status_counts[r.status] = status_counts.get(r.status, 0) + 1
            
            return {
                "mailing_id": mailing.id,
                "name": mailing.name,
                "status": mailing.status,
                "total": mailing.total_recipients,
                "sent": mailing.sent_count,
                "errors": mailing.error_count,
                "pending": mailing.total_recipients - mailing.sent_count - mailing.error_count,
                "status_breakdown": status_counts,
                "progress_percent": round(mailing.sent_count / mailing.total_recipients * 100, 1) if mailing.total_recipients > 0 else 0,
                "started_at": mailing.started_at,
                "completed_at": mailing.completed_at
            }
        finally:
            db.close()
