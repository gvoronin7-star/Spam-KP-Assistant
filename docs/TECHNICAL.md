# 🛠️ Техническая документация — Spam KP Assistant

**Версия:** 2.0  
**Дата:** 2026-05-22  
**Статус:** Production-ready ✅

---

## 📋 Содержание

1. [Архитектура](#архитектура)
2. [Модели базы данных](#модели-базы-данных)
3. [Сервисы](#сервисы)
4. [Утилиты](#утилиты)
5. [GUI компоненты](#gui-компоненты)
6. [Интеграции](#интеграции)

---

## Архитектура

### Общий обзор

```
┌─────────────────────────────────────────────────┐
│              GUI Layer (PyQt6)                  │
│  MainWindow | Wizards | Dialogs | Viewers      │
└───────────────────┬─────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────┐
│           Services Layer (Business Logic)       │
│  Mailing | Inbox | LLM | Reminder | Scheduler  │
│  RuleEngine | Template | Profile | Audit       │
│  DataExportImport | KPComparison | Analytics   │
└───────────────────┬─────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────┐
│            Core Layer (Data & ORM)              │
│  SQLAlchemy ORM | SQLite | Alembic Migrations  │
└─────────────────────────────────────────────────┘
```

### Слои

**1. GUI Layer (`gui/`)**
- Главное окно с 6 вкладками
- Мастеры (профиль, рассылка)
- Диалоги (настройки, просмотр, редактирование)
- Просмотрщики (сообщения, КП)

**2. Services Layer (`services/`)**
- Бизнес-логика приложения
- Независимые сервисы
- Интеграции (SMTP, IMAP, LLM)

**3. Core Layer (`core/`)**
- SQLAlchemy ORM модели
- SQLite база данных
- Alembic миграции

**4. Utils Layer (`utils/`)**
- Вспомогательные утилиты
- Retry, Rate limiting, Cache
- Шифрование, валидация

---

## Модели базы данных

### Список моделей (19 таблиц)

| Модель | Описание | Ключевые поля |
|--------|----------|---------------|
| `Profile` | Профили закупок | name, description, service_type, tech_params (JSON) |
| `Contact` | Контакты поставщиков | email, company, contact_person |
| `Template` | Шаблоны писем | name, subject, body_plain, body_html, variables |
| `Dialogue` | Диалоги с поставщиками | profile_id, contact_id, status, kp_data (JSON) |
| `Message` | Сообщения в диалогах | dialogue_id, direction, subject, body, attachments (JSON) |
| `Task` | Задачи оператору | dialogue_id, priority, task_type, due_date, status |
| `SMTPAccount` | Email аккаунты | email, smtp_host, smtp_port, password_encrypted |
| `LLMRequestLog` | Логи LLM запросов | model, prompt_tokens, completion_tokens, total_tokens |
| `Mailing` | Рассылки (кампании) | name, profile_id, template_id, status, progress |
| `MailingRecipient` | Получатели рассылки | mailing_id, contact_id, status, sent_at, reply_status |
| `RuleDB` | Правила Rule Engine | name, conditions (JSON), actions (JSON), priority |
| `AuditLog` | Аудит действий | action, entity_type, entity_id, old_value, new_value, actor |
| `ReminderSchedule` | Расписание напоминаний | dialogue_id, reminder_type, scheduled_at, sent_at |
| `LLMFeedback` | Обратная связь на LLM | message_id, rating, comment |
| `Settings` | Настройки приложения | key, value |
| *(4 дополнительных для будущего)* | | |

### Схема связей

```
profiles (1) ───< (N) dialogues
contacts (1) ───< (N) dialogues
dialogues (1) ───< (N) messages
dialogues (1) ───< (N) tasks
profiles (1) ───< (N) mailings
templates (1) ───< (N) mailings
smtp_accounts (1) ───< (N) mailings
mailings (1) ───< (N) mailing_recipients
contacts (1) ───< (N) mailing_recipients
dialogues (1) ───< (N) reminder_schedules
messages (1) ───< (N) llm_feedback
```

### Индексы

Основные индексы для производительности:
- `contacts.email` — уникальный индекс
- `messages.dialogue_id + created_at` — для истории сообщений
- `dialogues.status` — для фильтрации
- `tasks.due_date + status` — для планирования
- `mailings.status + created_at` — для отслеживания

---

## Сервисы

### MailingService (`services/mailing_service.py`)

**Назначение:** Массовые рассылки с контролем частоты

**Методы:**
- `create_mailing()` — создать рассылку
- `start_mailing()` — запустить отправку
- `pause_mailing()` — поставить на паузу
- `resume_mailing()` — возобновить
- `cancel_mailing()` — отменить
- `get_status()` — получить статус
- `get_stats()` — получить статистику

**Фичи:**
- Асинхронный цикл отправки (`asyncio`)
- Настраиваемые задержки (5-30 сек)
- Почасовые и посуточные лимиты
- Пауза/возобновление/отмена
- Callback'и для GUI (progress, recipient, log, finished)
- Кэширование профилей и шаблонов

### InboxService (`services/inbox_service.py`)

**Назначение:** Обработка входящих писем

**Методы:**
- `check_inbox()` — проверка IMAP
- `parse_email()` — парсинг письма
- `classify_response()` — классификация (LLM + fallback)
- `find_dialogue()` — поиск/создание диалога
- `create_task()` — создание задачи
- `process_attachments()` — парсинг вложений

**Фичи:**
- Email threading (In-Reply-To, References)
- Дедупликация по Message-ID
- LLM-классификация с fallback на keywords
- Парсинг PDF/Excel/Word
- Автоматическое создание задач
- Интеграция с Rule Engine

### LLMService (`services/llm_service.py`)

**Назначение:** Интеграция с ProxyAPI

**Методы:**
- `configure()` — настройка API ключа
- `classify()` — классификация текста
- `generate_reply_draft()` — генерация черновика ответа
- `extract_kp_data()` — извлечение данных из КП

**Фичи:**
- Rate limiting (RPM, RPH, TPM, TPD)
- Retry с exponential backoff
- Кэширование ответов
- Fallback на keyword-based классификацию

### ReminderService (`services/reminder_service.py`)

**Назначение:** Автоматические напоминания

**Методы:**
- `check_reminders()` — проверка необходимости отправки
- `send_reminder()` — отправка напоминания
- `schedule_reminder()` — планирование

**Фичи:**
- 2 уровня напоминаний (3 дня, 7 дней)
- Лимит 2 напоминания на диалог
- Кастомизируемые шаблоны
- Интеграция с планировщиком

### SchedulerService (`services/scheduler_service.py`)

**Назначение:** Планировщик фоновых задач

**Методы:**
- `start()` — запуск планировщика
- `setup_email_checker()` — фоновая проверка почты
- `setup_reminder_sender()` — отправка напоминаний
- `setup_daily_cleanup()` — автоочистка старых данных

**Фичи:**
- APScheduler BackgroundScheduler
- Persistent job store (SQLite)
- Автозапуск при старте GUI
- Интеграция с reminder_service

### RuleEngine (`services/rule_engine.py`)

**Назначение:** Движок правил автоматизации

**Условия:**
- `CONTAINS_KEYWORD` / `NOT_CONTAINS_KEYWORD`
- `MESSAGE_TYPE` (LLM/ручное)
- `HAS_ATTACHMENT` / `NO_ATTACHMENT`
- `CUSTOM_LLM_RESULT`
- `SENDER_DOMAIN`
- `DIALOGUE_STATUS`

**Действия:**
- `CREATE_TASK`
- `UPDATE_DIALOGUE_STATUS`
- `SEND_AUTO_REPLY`
- `GENERATE_DRAFT_REPLY`
- `FLAG_FOR_REVIEW`
- `ARCHIVE`
- `NOTIFY_OPERATOR`

**Фичи:**
- Persistence в БД (RuleDB)
- Приоритеты правил
- GUI редактор
- Автоматическая загрузка defaults

### TemplateService (`services/template_service.py`)

**Назначение:** Управление шаблонами

**Фичи:**
- TTL-кэширование (10 мин)
- Замена переменных
- Предпросмотр

### ProfileService (`services/profile_service.py`)

**Назначение:** Управление профилями

**Фичи:**
- TTL-кэширование (5 мин)
- CRUD операции

### AuditService (`services/audit_service.py`)

**Назначение:** Аудит действий

**Отслеживает:**
- create, update, delete
- send, classify
- old/new значения
- actor metadata (system, user, llm, scheduler)
- IP адрес, user agent

### DataExportImportService (`services/data_export_import_service.py`)

**Назначение:** Экспорт/импорт данных

**Форматы:**
- JSON — все сущности
- XML — профили, контакты, шаблоны

**Фичи:**
- Опция `overwrite` при импорте
- Обработка ошибок

### KPComparisonService (`services/kp_comparison_service.py`)

**Назначение:** Сравнение коммерческих предложений

**Фичи:**
- Таблица цен от разных поставщиков
- Экспорт в Excel
- Матрица сравнения

### AnalyticsService (`services/analytics_service.py`)

**Назначение:** Отчёты и аналитика

**Фичи:**
- Дашборд метрик
- Timeline ответов
- Экспорт CSV

---

## Утилиты

### Retry (`utils/retry.py`)

**Декоратор:** `@retry(max_attempts=3, backoff_factor=2, delay_seconds=1)`

**Пример:**
```python
@retry(max_attempts=3, backoff_factor=2, delay_seconds=1)
def send_email(to, subject, body):
    # отправка с retry при ошибках
    ...
```

### RateLimiter (`utils/rate_limiter.py`)

**Лимиты:**
- RPM (requests per minute)
- RPH (requests per hour)
- TPM (tokens per minute)
- TPD (tokens per day)

**Пример:**
```python
rate_limiter = RateLimiter(rpm=60, rph=1000, tpm=10000, tpd=100000)
rate_limiter.wait_if_needed()  # ждём если лимит превышен
```

### Cache (`utils/cache.py`)

**TTL-кэш:**
```python
cache = TTLCache(maxsize=100, ttl=600)  # 10 мин
cache['key'] = value
value = cache.get('key')
```

**Глобальные кэши:**
- `_template_cache` — шаблоны (10 мин)
- `_profile_cache` — профили (5 мин)
- `_dialogue_cache` — диалоги (5 мин)

### Encryption (`utils/encryption.py`)

**Fernet шифрование:**
```python
from utils.encryption import encrypt_password, decrypt_password
encrypted = encrypt_password("my_password")
decrypted = decrypt_password(encrypted)
```

**Хранение ключа:** Windows Credential Manager

### AttachmentManager (`utils/attachment_manager.py`)

**Сохранение вложений:**
- Лимит 50MB
- Безопасные имена файлов
- Дедупликация

---

## GUI компоненты

### Главное окно (`gui/main_window.py`)

**Вкладки:**
1. 📋 Профили — CRUD, поиск
2. 👥 Контакты — таблица, импорт, поиск
3. 📝 Шаблоны — редактор, предпросмотр, поиск
4. 💬 Переписка — диалоги, threading, поиск
5. ✅ Задачи — задачи оператору, поиск
6. ⚙️ Настройки — SMTP/IMAP, LLM, общие

**Меню:**
- Файл: Новый профиль, Импорт контактов, Экспорт, Выход
- Инструменты: LLM Агент, Шаблоны напоминаний, Правила, Сравнение КП, Отчёты
- Справка: Добро пожаловать, О программе

**Панель быстрого доступа:**
- ➕ Новый профиль
- 📬 Проверить почту
- 📧 Создать рассылку
- 💡 Демо/Помощь

### Мастеры

**WizardProfile** (5 шагов):
1. Название и описание
2. Технические параметры
3. Требования
4. Q&A пары
5. Вложения

**WizardMailing** (4 шага):
1. Профиль/Шаблон
2. Получатели
3. Настройки (задержки, лимиты)
4. Подтверждение

### Диалоги

- `DialogImportContacts` — импорт CSV/XLSX
- `DialogTemplateEditor` — редактор шаблонов
- `DialogSmtpSettings` — настройка SMTP/IMAP
- `DialogMailingProgress` — прогресс рассылки
- `DialogWelcome` — демо-интерфейс
- `DialogMessageViewer` — просмотр переписки
- `DialogRuleManager` — управление правилами
- `DialogRuleEditor` — редактор правил
- `DialogKPComparison` — сравнение КП
- `DialogReports` — отчёты
- `DialogReminderTemplates` — редактор шаблонов напоминаний

---

## Интеграции

### SMTP/IMAP

**Поддерживаемые провайдеры:**
- Gmail (smtp.gmail.com:465, imap.gmail.com:993)
- Yandex (smtp.yandex.ru:465, imap.yandex.ru:993)
- Mail.ru (smtp.mail.ru:465, imap.mail.ru:993)
- Корпоративные серверы (ручная настройка)

**Аутентификация:** App Password (не обычный пароль!)

### LLM (ProxyAPI)

**Модель:** gpt-5.4-mini

**Конфигурация:**
```env
PROXYAPI_API_KEY=your_key_here
```

**Rate limits (по умолчанию):**
- RPM: 60
- RPH: 1000
- TPM: 10000
- TPD: 100000

### APScheduler

**Версия:** 3.10+

**Хранение заданий:** SQLite (`jobs.sqlite`)

**Автозапуск:** При старте GUI

---

**Документ актуален на:** 2026-05-22  
**Версия:** 2.0  
**Статус:** Production-ready ✅