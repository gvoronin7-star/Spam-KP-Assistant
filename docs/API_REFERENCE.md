# 📚 Справочник API — Spam KP Assistant

**Версия:** 2.0  
**Дата:** 2026-05-22

---

## 📋 Содержание

1. [Сервисы](#сервисы)
2. [Модели БД](#модели-бд)
3. [Утилиты](#утилиты)
4. [GUI компоненты](#gui-компоненты)

---

## Сервисы

### MailingService

**Файл:** `services/mailing_service.py`

**Класс:** `MailingService`

#### Методы

```python
def create_mailing(
    name: str,
    profile_id: int,
    template_id: int,
    contact_ids: List[int],
    settings: dict
) -> Mailing:
    """Создать рассылку"""
```

```python
def start_mailing(mailing_id: int) -> bool:
    """Запустить рассылку"""
```

```python
def pause_mailing(mailing_id: int) -> bool:
    """Поставить на паузу"""
```

```python
def resume_mailing(mailing_id: int) -> bool:
    """Возобновить"""
```

```python
def cancel_mailing(mailing_id: int) -> bool:
    """Отменить"""
```

```python
def get_status(mailing_id: int) -> dict:
    """Получить статус (progress, sent, errors)"""
```

```python
def get_stats(mailing_id: int) -> dict:
    """Получить статистику"""
```

**Callback'и:**
- `on_progress(mailing_id, progress)`
- `on_recipient(mailing_id, recipient)`
- `on_log(mailing_id, message)`
- `on_finished(mailing_id, success)`

---

### InboxService

**Файл:** `services/inbox_service.py`

**Класс:** `InboxService`

#### Методы

```python
def check_inbox(account_id: int, since: datetime = None) -> List[Email]:
    """Проверить IMAP на новые письма"""
```

```python
def parse_email(raw_email) -> EmailData:
    """Парсинг письма (headers, body, attachments)"""
```

```python
def classify_response(text: str) -> ClassificationResult:
    """Классификация (LLM + fallback на keywords)"""
    # Returns: {category, confidence, summary}
```

```python
def find_dialogue(email: EmailData) -> Dialogue:
    """Найти существующий диалог или создать новый"""
```

```python
def create_task(dialogue: Dialogue, classification: dict) -> Task:
    """Создать задачу оператору"""
```

```python
def process_attachments(attachments: List[Attachment]) -> KPData:
    """Парсинг вложений (PDF/Excel/Word)"""
```

---

### LLMService

**Файл:** `services/llm_service.py`

**Класс:** `LLMService`

#### Методы

```python
def configure(api_key: str, model: str = "gpt-5.4-mini"):
    """Настроить API ключ и модель"""
```

```python
def classify(text: str) -> ClassificationResult:
    """Классификация текста через LLM"""
    # Returns: {category, confidence, summary}
```

```python
def generate_reply_draft(
    email_text: str,
    dialogue_context: dict,
    classification: dict
) -> DraftReply:
    """Генерация черновика ответа"""
    # Returns: {subject, body, tone}
```

```python
def extract_kp_data(text: str, attachments: List[Attachment]) -> KPData:
    """Извлечение данных из КП"""
    # Returns: {prices, terms, contacts, notes}
```

```python
def wait_if_needed():
    """Rate limiting — ждать если лимит превышен"""
```

---

### ReminderService

**Файл:** `services/reminder_service.py`

**Класс:** `ReminderService`

#### Методы

```python
def check_reminders() -> List[Dialogue]:
    """Проверить необходимость отправки напоминаний"""
```

```python
def send_reminder(dialogue: Dialogue, reminder_type: str) -> bool:
    """Отправить напоминание (reminder_1 или reminder_2)"""
```

```python
def schedule_reminder(dialogue: Dialogue, days: int):
    """Запланировать напоминание"""
```

---

### SchedulerService

**Файл:** `services/scheduler_service.py`

**Класс:** `SchedulerService`

#### Методы

```python
def start():
    """Запустить планировщик"""
```

```python
def stop():
    """Остановить планировщик"""
```

```python
def pause():
    """Приостановить все задания"""
```

```python
def resume():
    """Возобновить все задания"""
```

```python
def setup_email_checker(
    check_interval_hours: int = 1,
    enabled: bool = True
):
    """Настроить фоновую проверку почты"""
```

```python
def setup_reminder_sender(
    check_interval_minutes: int = 30,
    enabled: bool = True
):
    """Настроить отправка напоминаний"""
```

```python
def setup_daily_cleanup(
    hour: int = 2,
    minute: int = 0,
    enabled: bool = True
):
    """Настроить ежедневную очистку"""
```

---

### RuleEngine

**Файл:** `services/rule_engine.py`

**Класс:** `RuleEngine`

#### Методы

```python
def add_rule(rule: Rule):
    """Добавить правило"""
```

```python
def remove_rule(rule_id: str):
    """Удалить правило"""
```

```python
def process_message(message: Message, dialogue: Dialogue, db) -> dict:
    """Обработать сообщение через правила"""
    # Returns: {total_rules, matched, executed}
```

```python
def get_rules() -> List[Rule]:
    """Получить все правила"""
```

```python
def save_to_db(db):
    """Сохранить все правила в БД"""
```

```python
def load_from_db(db):
    """Загрузить правила из БД"""
```

**Типы условий (RuleConditionType):**
- `CONTAINS_KEYWORD`
- `NOT_CONTAINS_KEYWORD`
- `MESSAGE_TYPE`
- `HAS_ATTACHMENT`
- `NO_ATTACHMENT`
- `CUSTOM_LLM_RESULT`
- `SENDER_DOMAIN`
- `DIALOGUE_STATUS`

**Типы действий (RuleActionType):**
- `CREATE_TASK`
- `UPDATE_DIALOGUE_STATUS`
- `SEND_AUTO_REPLY`
- `GENERATE_DRAFT_REPLY`
- `FLAG_FOR_REVIEW`
- `ARCHIVE`
- `NOTIFY_OPERATOR`

---

### TemplateService

**Файл:** `services/template_service.py`

**Класс:** `TemplateService`

#### Методы

```python
def get_template(template_id: int) -> Template:
    """Получить шаблон (из кэша или БД)"""
```

```python
def replace_variables(template: Template, data: dict) -> str:
    """Заменить переменные в шаблоне"""
```

```python
def preview(template: Template, contact: Contact) -> str:
    """Предпросмотр шаблона с демо-данными"""
```

---

### ProfileService

**Файл:** `services/profile_service.py`

**Класс:** `ProfileService`

#### Методы

```python
def get_profile(profile_id: int) -> Profile:
    """Получить профиль (из кэша или БД)"""
```

```python
def create_profile(data: dict) -> Profile:
    """Создать профиль"""
```

```python
def update_profile(profile_id: int, data: dict) -> Profile:
    """Обновить профиль"""
```

```python
def delete_profile(profile_id: int):
    """Удалить профиль (мягкое)"""
```

---

### AuditService

**Файл:** `services/audit_service.py`

**Класс:** `AuditService`

#### Методы

```python
def log_action(
    action: str,
    entity_type: str,
    entity_id: int,
    old_value: dict = None,
    new_value: dict = None,
    actor: str = "system"
):
    """Записать действие в аудит-лог"""
```

```python
def get_logs(
    entity_type: str = None,
    entity_id: int = None,
    actor: str = None,
    date_from: datetime = None,
    date_to: datetime = None
) -> List[AuditLog]:
    """Получить логи с фильтрацией"""
```

---

### DataExportImportService

**Файл:** `services/data_export_import_service.py`

**Класс:** `DataExportImportService`

#### Методы

```python
def export_json(path: str, entities: List[str] = None) -> bool:
    """Экспорт в JSON"""
```

```python
def export_xml(path: str, entities: List[str] = None) -> bool:
    """Экспорт в XML"""
```

```python
def import_json(path: str, overwrite: bool = False) -> dict:
    """Импорт из JSON"""
    # Returns: {created, updated, skipped, errors}
```

```python
def import_xml(path: str, overwrite: bool = False) -> dict:
    """Импорт из XML"""
```

---

### KPComparisonService

**Файл:** `services/kp_comparison_service.py`

**Класс:** `KPComparisonService`

#### Методы

```python
def compare(dialogue_ids: List[int]) -> ComparisonTable:
    """Сравнить КП из диалогов"""
    # Returns: {headers, rows, best_prices}
```

```python
def export_to_excel(table: ComparisonTable, path: str):
    """Экспорт в Excel"""
```

---

### AnalyticsService

**Файл:** `services/analytics_service.py`

**Класс:** `AnalyticsService`

#### Методы

```python
def get_metrics() -> dict:
    """Получить метрики (kp_count, avg_price, response_time)"""
```

```python
def get_timeline(days: int = 30) -> List[TimelinePoint]:
    """Получить timeline ответов"""
```

```python
def export_csv(path: str):
    """Экспорт в CSV"""
```

---

## Модели БД

### Profile

**Файл:** `core/models.py`

```python
class Profile(Base):
    id: int
    name: str
    description: str
    service_type: str
    tech_params: dict  # JSON
    requirements: dict  # JSON
    qa_pairs: list  # JSON
    is_active: bool
    created_at: datetime
    updated_at: datetime
```

### Contact

```python
class Contact(Base):
    id: int
    email: str  # UNIQUE
    company: str
    contact_person: str
    notes: str
    is_active: bool
    created_at: datetime
```

### Template

```python
class Template(Base):
    id: int
    name: str
    subject: str
    body_plain: str
    body_html: str
    variables: list  # JSON
    template_type: str  # primary, reminder_1, reminder_2
    created_at: datetime
    updated_at: datetime
```

### Dialogue

```python
class Dialogue(Base):
    id: int
    profile_id: int
    contact_id: int
    status: str  # sent, clarifying, kp_received, rejected, etc.
    kp_data: dict  # JSON
    created_at: datetime
    updated_at: datetime
```

### Message

```python
class Message(Base):
    id: int
    dialogue_id: int
    direction: str  # incoming, outgoing
    subject: str
    body: str
    attachments: list  # JSON
    message_id: str  # Email Message-ID
    in_reply_to: str
    references: str
    created_at: datetime
```

### Task

```python
class Task(Base):
    id: int
    dialogue_id: int
    priority: str  # low, medium, high, critical
    task_type: str
    title: str
    description: str
    due_date: datetime
    status: str  # pending, completed
    created_at: datetime
    completed_at: datetime
```

### Mailing

```python
class Mailing(Base):
    id: int
    name: str
    profile_id: int
    template_id: int
    smtp_account_id: int
    status: str  # draft, queued, sending, paused, completed, cancelled
    delay_min: int
    delay_max: int
    hourly_limit: int
    daily_limit: int
    total_recipients: int
    sent_count: int
    error_count: int
    started_at: datetime
    completed_at: datetime
    created_at: datetime
```

### RuleDB

```python
class RuleDB(Base):
    id: int
    rule_id: str  # UNIQUE
    name: str
    conditions: list  # JSON
    actions: list  # JSON
    priority: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
```

### AuditLog

```python
class AuditLog(Base):
    id: int
    action: str  # create, update, delete, send, classify
    entity_type: str
    entity_id: int
    old_value: dict  # JSON
    new_value: dict  # JSON
    actor: str  # system, user, llm, scheduler
    ip_address: str
    user_agent: str
    created_at: datetime
```

---

## Утилиты

### Retry

**Файл:** `utils/retry.py`

```python
from utils.retry import retry

@retry(max_attempts=3, backoff_factor=2, delay_seconds=1)
def send_email(to, subject, body):
    # Отправка с retry при ошибках
    pass
```

**Класс:** `RetryableOperation`

```python
operation = RetryableOperation(
    max_attempts=3,
    backoff_factor=2,
    delay_seconds=1
)
result = operation.execute(func, *args, **kwargs)
```

### RateLimiter

**Файл:** `utils/rate_limiter.py`

```python
from utils.rate_limiter import RateLimiter

limiter = RateLimiter(
    rpm=60,    # requests per minute
    rph=1000,  # requests per hour
    tpm=10000, # tokens per minute
    tpd=100000 # tokens per day
)

limiter.wait_if_needed()  # Ждать если лимит превышен
limiter.record_request(tokens=100)  # Записать запрос
```

### Cache

**Файл:** `utils/cache.py`

```python
from utils.cache import TTLCache

cache = TTLCache(maxsize=100, ttl=600)  # 10 мин

cache['key'] = value
value = cache.get('key')
cache.delete('key')
cache.clear()
```

**Глобальные кэши:**
```python
from utils.cache import _template_cache, _profile_cache, _dialogue_cache
```

### Encryption

**Файл:** `utils/encryption.py`

```python
from utils.encryption import encrypt_password, decrypt_password

encrypted = encrypt_password("my_password")
decrypted = decrypt_password(encrypted)
```

---

## GUI компоненты

### MainWindow

**Файл:** `gui/main_window.py`

**Методы:**
- `_setup_tabs()` — инициализация вкладок
- `_setup_menu()` — инициализация меню
- `_setup_shortcuts()` — горячие клавиши
- `_add_search_bar()` — добавить поле поиска
- `_filter_list()` — фильтрация списка

### WizardProfile

**Файл:** `gui/wizard_profile.py`

**Страницы:**
1. `PageBasicInfo` — название и описание
2. `PageTechParams` — технические параметры
3. `PageRequirements` — требования
4. `PageQAPairs` — Q&A пары
5. `PageAttachments` — вложения

### WizardMailing

**Файл:** `gui/wizard_mailing.py`

**Страницы:**
1. `PageProfileTemplate` — профиль и шаблон
2. `PageRecipients` — получатели
3. `PageSettings` — задержки и лимиты
4. `PageConfirm` — подтверждение

### DialogImportContacts

**Файл:** `gui/dialog_import_contacts.py`

**Методы:**
- `_load_file()` — загрузить CSV/XLSX
- `_map_columns()` — сопоставить колонки
- `_preview()` — предпросмотр
- `_import()` — импортировать

---

**Документ актуален на:** 2026-05-22  
**Версия:** 2.0  
**Статус:** Production-ready ✅