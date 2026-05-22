"""
ORM-модели для SQLite
"""
from typing import Optional, Dict, Any
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Boolean, JSON, ForeignKey, func
)
from sqlalchemy.orm import relationship
from .database import Base


class Profile(Base):
    """Профиль закупки"""
    __tablename__ = "profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    
    # Технические параметры (JSON)
    tech_params = Column(JSON, default=dict)
    # SLA, скорость, города, протоколы и т.д.
    
    # Требования к КП
    requirements = Column(JSON, default=dict)
    # Цена, срок поставки, гарантии, форма оплаты
    
    # Правила диалога
    dialogue_rules = Column(JSON, default=dict)
    # Q&A пары, допустимость альтернатив, мин. контракт и т.д.
    
    # Вложения
    attachments = Column(JSON, default=list)
    # Пути к файлам (ТЗ, опросный лист)
    
    # Статус
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Связи
    contacts = relationship("Contact", back_populates="profile")
    dialogues = relationship("Dialogue", back_populates="profile")


class Contact(Base):
    """Контакт поставщика"""
    __tablename__ = "contacts"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    company_name = Column(String(255))
    contact_person = Column(String(255))  # Контактное лицо
    notes = Column(Text)
    
    # Связь с профилем (опционально)
    profile_id = Column(Integer, ForeignKey("profiles.id"))
    profile = relationship("Profile", back_populates="contacts")
    
    # Статусы
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Связи
    dialogues = relationship("Dialogue", back_populates="contact")


class Template(Base):
    """Шаблон письма"""
    __tablename__ = "templates"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    template_type = Column(String(50))  # 'initial', 'reminder', 'followup'
    
    subject = Column(String(500))
    body_html = Column(Text)
    body_plain = Column(Text)
    
    # Переменные: {{ company }}, {{ service_name }}, и т.д.
    variables = Column(JSON, default=list)
    
    # Вложения
    attachments = Column(JSON, default=list)
    
    version = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class Dialogue(Base):
    """Диалог с поставщиком"""
    __tablename__ = "dialogues"
    
    id = Column(Integer, primary_key=True, index=True)
    
    profile_id = Column(Integer, ForeignKey("profiles.id"))
    profile = relationship("Profile", back_populates="dialogues")
    
    contact_id = Column(Integer, ForeignKey("contacts.id"))
    contact = relationship("Contact", back_populates="dialogues")
    
    # Связь с рассылкой (опционально)
    mailing_id = Column(Integer, ForeignKey("mailings.id"), nullable=True)
    
    # Статус
    status = Column(String(50), default="sent")
    # sent, clarifying, kp_received, rejected, reminder_sent
    
    # Последнее обновление
    last_activity = Column(DateTime, default=func.now())
    
    # Информация о КП
    kp_received = Column(Boolean, default=False)
    kp_data = Column(JSON, default=dict)  # Извлечённые данные из КП
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Сообщения
    messages = relationship("Message", back_populates="dialogue", order_by="Message.created_at")


class Message(Base):
    """Сообщение (письмо)"""
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    
    dialogue_id = Column(Integer, ForeignKey("dialogues.id"))
    dialogue = relationship("Dialogue", back_populates="messages")
    
    # Направление
    direction = Column(String(10))  # 'inbound', 'outbound'
    
    # Содержимое
    subject = Column(String(500))
    body_html = Column(Text)
    body_plain = Column(Text)
    raw_body = Column(Text)  # Оригинальный текст
    
    # Отправитель/получатель
    from_address = Column(String(255))
    to_address = Column(String(255))
    
    # Message-ID для трекинга цепочки
    message_id = Column(String(500), index=True)
    
    # Вложения
    attachments = Column(JSON, default=list)
    # [{filename, path, size}]
    
    # LLM-информация
    generated_by_llm = Column(Boolean, default=False)
    operator_edited = Column(Boolean, default=False)
    llm_model = Column(String(100))  # Какая модель сгенерировала
    
    # Статус
    status = Column(String(50), default="sent")
    # sent, delivered, read, error
    
    # Прочтение
    is_read = Column(Boolean, default=False)  # Прочитано ли оператором
    
    created_at = Column(DateTime, default=func.now())


class Task(Base):
    """Задача оператору"""
    __tablename__ = "tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    
    task_type = Column(String(50))  # 'requires_response', 'llm_review', 'manual_kp'
    title = Column(String(255), nullable=False)
    description = Column(Text)
    
    dialogue_id = Column(Integer, ForeignKey("dialogues.id"))
    
    # Приоритет
    priority = Column(String(20), default="medium")
    # low, medium, high, critical
    
    # Дедлайн
    due_date = Column(DateTime, nullable=True)
    
    # Статус
    is_completed = Column(Boolean, default=False)
    completed_at = Column(DateTime)
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    

class RuleDB(Base):
    """Правило Rule Engine (хранится в БД)"""
    __tablename__ = "rules"
    
    id = Column(Integer, primary_key=True, index=True)
    
    rule_id = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    
    # Условия (JSON)
    conditions = Column(JSON, default=list)
    # [{"type": "contains_keyword", "params": {"keywords": ["..."]}}]
    
    # Действия (JSON)
    actions = Column(JSON, default=list)
    # [{"type": "create_task", "params": {"priority": "high"}}]
    
    # Настройки
    is_active = Column(Boolean, default=True)
    priority = Column(Integer, default=0)
    
    # Статистика
    match_count = Column(Integer, default=0)
    last_matched_at = Column(DateTime)
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    

class AuditLog(Base):
    """Журнал аудита действий пользователя/системы"""
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Кто выполнил действие
    actor_type = Column(String(50), default="system")  # system, user, llm, scheduler
    actor_id = Column(String(255))  # ID пользователя или системного компонента
    
    # Действие
    action = Column(String(100), nullable=False)  # create, update, delete, send, classify
    entity_type = Column(String(100), nullable=False)  # dialogue, message, task, mailing, contact
    entity_id = Column(Integer)  # ID сущности
    
    # Детали
    description = Column(Text)
    old_values = Column(JSON, default=dict)  # Предыдущие значения (для update)
    new_values = Column(JSON, default=dict)  # Новые значения
    
    # IP / метаданные
    ip_address = Column(String(50))
    user_agent = Column(String(500))
    
    # Результат
    success = Column(Boolean, default=True)
    error_message = Column(Text)
    
    created_at = Column(DateTime, default=func.now(), index=True)
    
    # Индекс для быстрого поиска по сущности
    __table_args__ = (
        {"sqlite_autoincrement": True},
    )


class LLMFeedback(Base):
    """Обратная связь на черновики LLM"""
    __tablename__ = "llm_feedback"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Связь с черновиком
    message_id = Column(Integer, ForeignKey("messages.id"), nullable=False)
    message = relationship("Message", back_populates="feedback")
    
    # Оценка оператора (1-5)
    rating = Column(Integer)  # 1=плохо, 5=отлично
    
    # Был ли отредактирован
    was_edited = Column(Boolean, default=False)
    edited_text = Column(Text)  # Отредактированный текст
    
    # Был ли отправлен
    was_sent = Column(Boolean, default=False)
    sent_at = Column(DateTime)
    
    # Комментарий оператора
    operator_comment = Column(Text)
    
    # Использовать как few-shot пример
    use_as_few_shot = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


# Добавить обратную связь в Message
Message.feedback = relationship(
    "LLMFeedback",
    back_populates="message",
    uselist=False,
    cascade="all, delete-orphan"
)


class ReminderSchedule(Base):
    """Расписание напоминаний для диалогов без ответа"""
    __tablename__ = "reminder_schedules"
    
    id = Column(Integer, primary_key=True, index=True)
    
    dialogue_id = Column(Integer, ForeignKey("dialogues.id"), nullable=False)
    dialogue = relationship("Dialogue", back_populates="reminders")
    
    # Какой номер напоминания (1, 2, максимум 2)
    reminder_number = Column(Integer, default=1)
    
    # Шаблон для напоминания
    template_id = Column(Integer, ForeignKey("templates.id"))
    template = relationship("Template")
    
    # Статус
    status = Column(String(50), default="scheduled")
    # scheduled, sent, cancelled
    
    # Даты
    scheduled_at = Column(DateTime, nullable=False)  # Когда запланировано
    sent_at = Column(DateTime)  # Когда отправлено
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


# Добавляем обратную связь в Dialogue
Dialogue.reminders = relationship(
    "ReminderSchedule", 
    back_populates="dialogue", 
    cascade="all, delete-orphan"
)


class Settings(Base):
    """Настройки приложения"""
    __tablename__ = "settings"
    
    id = Column(Integer, primary_key=True, index=True)
    
    key = Column(String(100), unique=True, nullable=False)
    value = Column(JSON)
    
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class SMTPAccount(Base):
    """SMTP аккаунт отправителя"""
    __tablename__ = "smtp_accounts"
    
    id = Column(Integer, primary_key=True, index=True)
    
    name = Column(String(255), nullable=False)  # Имя аккаунта
    email = Column(String(255), nullable=False)
    
    # SMTP настройки
    smtp_host = Column(String(255))
    smtp_port = Column(Integer)
    smtp_use_tls = Column(Boolean, default=True)
    
    # IMAP настройки
    imap_host = Column(String(255))
    imap_port = Column(Integer)
    imap_use_ssl = Column(Boolean, default=True)
    
    # Учётные данные (зашифрованные)
    login = Column(String(255))
    password_enc = Column(Text)  # Fernet-зашифрованный пароль
    
    # Статус
    is_active = Column(Boolean, default=True)
    is_primary = Column(Boolean, default=False)
    
    last_check = Column(DateTime)
    last_error = Column(Text)
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    

class Mailing(Base):
    """Рассылка (кампания)"""
    __tablename__ = "mailings"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)  # Название рассылки
    
    profile_id = Column(Integer, ForeignKey("profiles.id"))
    profile = relationship("Profile")
    
    template_id = Column(Integer, ForeignKey("templates.id"))
    template = relationship("Template")
    
    # SMTP аккаунт для отправки
    smtp_account_id = Column(Integer, ForeignKey("smtp_accounts.id"))
    smtp_account = relationship("SMTPAccount")
    
    # Статус
    status = Column(String(50), default="draft")  # draft, queued, sending, paused, completed, cancelled
    
    # Настройки отправки
    delay_min = Column(Integer, default=5)   # Минимальная задержка (сек)
    delay_max = Column(Integer, default=30)  # Максимальная задержка (сек)
    hourly_limit = Column(Integer, default=50)  # Лимит писем в час
    daily_limit = Column(Integer, default=200)  # Лимит писем в день
    
    # Прогресс
    total_recipients = Column(Integer, default=0)
    sent_count = Column(Integer, default=0)
    error_count = Column(Integer, default=0)
    
    # Время
    scheduled_at = Column(DateTime, nullable=True)  # Отложенный старт
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Связи
    recipients = relationship("MailingRecipient", back_populates="mailing", cascade="all, delete-orphan")


class MailingRecipient(Base):
    """Получатель рассылки (связь many-to-many со статусом)"""
    __tablename__ = "mailing_recipients"
    
    id = Column(Integer, primary_key=True, index=True)
    
    mailing_id = Column(Integer, ForeignKey("mailings.id"))
    mailing = relationship("Mailing", back_populates="recipients")
    
    contact_id = Column(Integer, ForeignKey("contacts.id"))
    contact = relationship("Contact")
    
    # Статус отправки
    status = Column(String(50), default="pending")  # pending, queued, sent, delivered, opened, error, bounced
    
    # Результат
    sent_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    message_id = Column(String(500), nullable=True)  # Message-ID для трекинга
    
    # Ответ
    replied_at = Column(DateTime, nullable=True)
    reply_status = Column(String(50), nullable=True)  # kp, spam, question, refusal, auto_reply
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
