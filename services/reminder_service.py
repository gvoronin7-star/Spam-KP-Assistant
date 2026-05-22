"""
Сервис автоматических напоминаний для диалогов без ответа
"""
from datetime import datetime, timedelta
from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from loguru import logger

from core.models import ReminderSchedule, Dialogue, Message, Task, Profile, Template, SMTPAccount
from services.template_service import TemplateService
from utils.datetime_helper import now_utc


class ReminderService:
    """
    Сервис для автоматической отправки напоминаний поставщикам
    
    Логика:
    - Reminder 1: через 3 дня после отправки первого письма
    - Reminder 2: через 7 дней после первого письма
    - Максимум 2 напоминания на один диалог
    """
    
    # Настройки по умолчанию
    DEFAULT_REMINDER_1_DELAY = 3  # дни
    DEFAULT_REMINDER_2_DELAY = 7  # дни
    MAX_REMINDERS = 2
    
    def __init__(self):
        logger.info("ReminderService инициализирован")
    
    def check_unanswered_dialogues(
        self,
        db: Session,
        since_days: int = 3
    ) -> List[Dialogue]:
        """
        Найти диалоги без ответа за последние N дней
        
        Args:
            db: Сессия БД
            since_days: Проверять диалоги старше N дней
        
        Returns:
            Список диалогов без ответа
        """
        threshold_date = now_utc() - timedelta(days=since_days)
        
        # Найти диалоги:
        # - Статус: sent или reminder_sent
        # - Последняя активность: старше threshold_date
        dialogues = (
            db.query(Dialogue)
            .filter(
                Dialogue.status.in_(["sent", "reminder_sent"]),
                Dialogue.last_activity < threshold_date
            )
            .order_by(Dialogue.last_activity.asc())
            .all()
        )
        
        logger.info(f"Найдено {len(dialogues)} диалогов без ответа (старше {since_days} дней)")
        return dialogues
    
    def get_reminder_count(self, dialogue: Dialogue, db: Session) -> int:
        """
        Получить количество отправленных напоминаний для диалога
        
        Args:
            dialogue: Диалог
            db: Сессия БД
        
        Returns:
            Количество отправленных напоминаний
        """
        count = (
            db.query(ReminderSchedule)
            .filter(
                ReminderSchedule.dialogue_id == dialogue.id,
                ReminderSchedule.status == "sent"
            )
            .count()
        )
        return count
    
    def create_reminder_schedule(
        self,
        dialogue: Dialogue,
        reminder_number: int,
        db: Session
    ) -> Optional[ReminderSchedule]:
        """
        Создать расписание напоминания
        
        Args:
            dialogue: Диалог
            reminder_number: Номер напоминания (1 или 2)
            db: Сессия БД
        
        Returns:
            Созданное расписание или None если максимум достигнут
        """
        # Проверить лимит
        if reminder_number > self.MAX_REMINDERS:
            logger.warning(
                f"Максимум напоминаний достигнут для диалога {dialogue.id}"
            )
            return None
        
        # Проверить существующие
        existing = (
            db.query(ReminderSchedule)
            .filter(
                ReminderSchedule.dialogue_id == dialogue.id,
                ReminderSchedule.reminder_number == reminder_number
            )
            .first()
        )
        
        if existing:
            logger.info(f"Напоминание #{reminder_number} уже существует")
            return existing
        
        # Вычислить дату отправки
        days_delay = (
            self.DEFAULT_REMINDER_1_DELAY 
            if reminder_number == 1 
            else self.DEFAULT_REMINDER_2_DELAY
        )
        scheduled_at = dialogue.last_activity + timedelta(days=days_delay)
        
        # Найти шаблон напоминания (или использовать дефолтный)
        template = self._find_reminder_template(db, reminder_number)
        
        # Создать расписание
        schedule = ReminderSchedule(
            dialogue_id=dialogue.id,
            reminder_number=reminder_number,
            template_id=template.id if template else None,
            scheduled_at=scheduled_at,
            status="scheduled"
        )
        
        db.add(schedule)
        db.commit()
        db.refresh(schedule)
        
        logger.info(
            f"Создано напоминание #{reminder_number} "
            f"для диалога {dialogue.id} на {scheduled_at.strftime('%d.%m.%Y')}"
        )
        
        return schedule
    
    def _find_reminder_template(self, db: Session, reminder_number: int) -> Optional[Template]:
        """
        Найти шаблон для напоминания (с кэшированием)
        
        Args:
            db: Сессия БД
            reminder_number: Номер напоминания
        
        Returns:
            Шаблон или None
        """
        template_service = TemplateService()
        
        # Попытаться найти специфичный шаблон по типу
        template_name = f"reminder_{reminder_number}"
        template = template_service.get_by_type(template_name, db)
        
        if template:
            return template
        
        # Или найти по имени (не кэшируется)
        template = (
            db.query(Template)
            .filter(
                Template.name.contains("напоминание"),
                Template.is_active == True
            )
            .first()
        )
        
        return template
    
    def send_due_reminders(self, db: Session) -> Dict:
        """
        Отправить все запланированные напоминания, у которых наступила дата
        
        Args:
            db: Сессия БД
        
        Returns:
            Статистика отправки
        """
        now = now_utc()
        
        # Найти все запланированные напоминания, у которых наступила дата
        due_reminders = (
            db.query(ReminderSchedule)
            .filter(
                ReminderSchedule.status == "scheduled",
                ReminderSchedule.scheduled_at <= now
            )
            .all()
        )
        
        stats = {
            "total": len(due_reminders),
            "sent": 0,
            "errors": 0
        }
        
        for reminder in due_reminders:
            try:
                self._send_reminder(reminder, db)
                stats["sent"] += 1
            except Exception as e:
                logger.error(f"Ошибка отправки напоминания {reminder.id}: {e}")
                stats["errors"] += 1
        
        logger.info(
            f"Отправлено напоминаний: {stats['sent']}/{stats['total']}, "
            f"ошибок: {stats['errors']}"
        )
        
        return stats
    
    def _send_reminder(self, reminder: ReminderSchedule, db: Session) -> bool:
        """
        Отправить одно напоминание
        
        Args:
            reminder: Расписание напоминания
            db: Сессия БД
        
        Returns:
            Успех ли
        """
        # Получить диалог
        dialogue = db.query(Dialogue).filter_by(id=reminder.dialogue_id).first()
        if not dialogue:
            raise ValueError(f"Диалог {reminder.dialogue_id} не найден")
        
        # Получить контакт
        contact = dialogue.contact
        
        # Получить SMTP аккаунт
        smtp_account = self.smtp_manager.get_primary_account(db)
        if not smtp_account:
            raise ValueError("Нет активного SMTP аккаунта")
        
        # Получить шаблон (с кэшированием)
        template = None
        if reminder.template_id:
            template_service = TemplateService()
            template = template_service.get_by_id(reminder.template_id, db)
        
        if not template:
            # Использовать дефолтный шаблон напоминания
            template = self._get_default_reminder_template(reminder.reminder_number)
        
        # Сформировать письмо
        subject = template.subject.replace("{{ company_name }}", contact.company_name or "Уважаемая компания")
        body_plain = template.body_plain.replace(
            "{{ company_name }}", 
            contact.company_name or "Уважаемая компания"
        )
        body_html = template.body_html.replace(
            "{{ company_name }}", 
            contact.company_name or "Уважаемая компания"
        )
        
        # Отправить письмо
        success = self.smtp_manager.send_email(
            smtp_account=smtp_account,
            to_email=contact.email,
            subject=subject,
            body_plain=body_plain,
            body_html=body_html
        )
        
        if success:
            # Обновить статус напоминания
            reminder.status = "sent"
            reminder.sent_at = now_utc()
            db.commit()
            
            # Обновить статус диалога
            dialogue.status = "reminder_sent"
            dialogue.last_activity = now_utc()
            db.commit()
            
            # Создать запись в messages
            message = Message(
                dialogue_id=dialogue.id,
                direction="outbound",
                subject=subject,
                content=body_plain,
                status="sent"
            )
            db.add(message)
            db.commit()
            
            logger.info(
                f"Напоминание #{reminder.reminder_number} отправлено "
                f"на {contact.email}"
            )
        else:
            raise Exception("Ошибка отправки письма через SMTP")
        
        return success
    
    def _get_default_reminder_template(self, reminder_number: int) -> object:
        """
        Получить дефолтный шаблон напоминания
        
        Args:
            reminder_number: Номер напоминания
        
        Returns:
            Шаблон (модель Template)
        """
        if reminder_number == 1:
            return Template(
                name="Напоминание 1",
                template_type="reminder_1",
                subject="Напоминание: Запрос КП - {{ service_name }}",
                body_plain="""Добрый день, {{ contact_person }}!

Напоминаем о нашем запросе коммерческого предложения от {{ request_date }}.

Будем благодарны, если вы предоставите КП в ближайшее время.

С уважением,
{{ company_name }}
""",
                body_html="""<html><body>
<p>Добрый день, {{ contact_person }}!</p>
<p>Напоминаем о нашем запросе коммерческого предложения от {{ request_date }}.</p>
<p>Будем благодарны, если вы предоставите КП в ближайшее время.</p>
<p>С уважением,<br>{{ company_name }}</p>
</body></html>"""
            )
        else:
            return Template(
                name="Напоминание 2",
                template_type="reminder_2",
                subject="Повторное напоминание: Запрос КП - {{ service_name }}",
                body_plain="""Добрый день, {{ contact_person }}!

Это повторное напоминание о нашем запросе коммерческого предложения от {{ request_date }}.

Пожалуйста, сообщите, возможно ли сотрудничество с вашей компанией.

С уважением,
{{ company_name }}
""",
                body_html="""<html><body>
<p>Добрый день, {{ contact_person }}!</p>
<p>Это повторное напоминание о нашем запросе коммерческого предложения от {{ request_date }}.</p>
<p>Пожалуйста, сообщите, возможно ли сотрудничество с вашей компанией.</p>
<p>С уважением,<br>{{ company_name }}</p>
</body></html>"""
            )
    
    def schedule_all_reminders(self, db: Session) -> int:
        """
        Создать расписания для всех диалогов без ответа
        
        Args:
            db: Сессия БД
        
        Returns:
            Количество созданных расписаний
        """
        dialogues = self.check_unanswered_dialogues(db, since_days=3)
        created_count = 0
        
        for dialogue in dialogues:
            current_count = self.get_reminder_count(dialogue, db)
            
            if current_count < self.MAX_REMINDERS:
                next_reminder_number = current_count + 1
                reminder = self.create_reminder_schedule(
                    dialogue, 
                    next_reminder_number, 
                    db
                )
                
                if reminder:
                    created_count += 1
        
        logger.info(f"Создано {created_count} новых расписаний напоминаний")
        return created_count


# Импорт Template для типа аннотации
from core.models import Template
