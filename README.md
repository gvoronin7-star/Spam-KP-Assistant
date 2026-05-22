# 📧 Spam KP Assistant

> Автоматизация получения коммерческих предложений от поставщиков телеком-услуг

---

## 📊 Текущее состояние разработки

**Версия:** 2.1.1  
**Дата:** 2026-05-22  
**Статус:** P0 ✅ **Завершён**, P1 ✅ **Завершён (Production-ready)**, P2 ✅ **Завершён (100%)**

| Компонент | Статус | Примечание |
|-----------|--------|------------|
| GUI (главное окно, мастера, диалоги) | ✅ Работает | 6 вкладок, поиск, DialogMessageViewer |
| Рассылки (MailingService) | ✅ Работает | CRUD, async отправка, callback'и, кэширование |
| Входящие (InboxService) | ✅ Работает | IMAP, LLM-классификация, threading, дедупликация |
| LLM-классификация | ✅ Работает | ProxyAPI + очистка цитат + rate limiting |
| Парсинг вложений | ✅ Работает | PDF/Excel/Word с LLM fallback, лимит 50MB |
| Задачи оператора | ✅ Работает | С дедлайнами и приоритетами |
| Напоминания (ReminderService) | ✅ Работает | 2 напоминания на диалог, GUI редактор |
| UI просмотра переписки | ✅ Работает | DialogMessageViewer |
| Индикаторы новых сообщений | ✅ Работает | 🔔 + голубой фон |
| Планировщик (SchedulerService) | ✅ Работает | APScheduler, фоновые задачи, автоочистка |
| Rule Engine | ✅ Работает | Автоматизация, сохранение в БД |
| Генерация автоответов | ✅ Работает | LLM-черновики ответов |
| Сохранение вложений | ✅ Работает | data/attachments/ + парсинг |
| GUI управления правилами | ✅ Работает | Визуальный редактор правил |
| Сравнение КП | ✅ Работает | Таблица сравнения + экспорт |
| Отчёты и аналитика | ✅ Работает | Дашборд + метрики + экспорт |
| **Кэширование** | ✅ **Работает** | TTL-кэш для шаблонов и профилей |
| **Поиск и фильтрация** | ✅ **Работает** | Везде в GUI |
| **Экспорт/импорт данных** | ✅ **Работает** | JSON/XML |
| **Audit logging** | ✅ **Работает** | Полный аудит действий |
| Retry + exponential backoff | ✅ Работает | Для EmailService |
| Rate limiting (LLM) | ✅ Работает | RPM/RPH/TPM/TPD лимиты |
| Тесты (всего) | ✅ **305/306** | 305 passed, 1 skipped (99.7%) |
| LLM генерация писем | ✅ Работает | v2.1 ✨ |

**Готово к продакшену:** Все P0/P1/P2 фичи реализованы. Система стабильна, протестирована, готова к использованию.

📘 [Руководство пользователя](docs/USER_GUIDE.md) &nbsp;|&nbsp; 🛠️ [Техническая документация](docs/TECHNICAL.md) &nbsp;|&nbsp; 📝 [История версий](docs/CHANGELOG.md)

---

## 📚 Документация

| Файл | Описание |
|------|----------|
| 📘 **[USER_GUIDE.md](docs/USER_GUIDE.md)** | Руководство пользователя — как использовать приложение |
| 🤖 **[LLM_MODELS.md](docs/LLM_MODELS.md)** | **Модели LLM** — описание, назначение, конфигурация |
| 🗺️ **[ROADMAP.md](docs/ROADMAP.md)** | Дорожная карта — план развития проекта |
| 🤝 **[CHAT_HANDOVER.md](docs/CHAT_HANDOVER.md)** | Контекст для передачи между чатами |
| 🛠️ **[TECHNICAL.md](docs/TECHNICAL.md)** | Техническая документация — архитектура, сервисы, модели БД |
| 🧪 **[TESTING.md](docs/TESTING.md)** | Тестирование — статистика тестов, структура, known issues |
| 📚 **[API_REFERENCE.md](docs/API_REFERENCE.md)** | Справочник API — методы сервисов и моделей |
| 🔧 **[TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)** | Решение проблем — частые ошибки и решения |
| 📝 **[CHANGELOG.md](docs/CHANGELOG.md)** | История версий — что изменилось в каждой версии |
| 🔒 **[SECURITY_AUDIT.md](docs/SECURITY_AUDIT.md)** | Аудит безопасности |

---

## 🎯 Что делает проект

**Spam KP Assistant** — десктопное приложение для автоматизации рутинной работы операторов связи и закупщиков.

### Проблема

При строительстве или расширении сети оператору связи нужно получить коммерческие предложения (КП) от десятков поставщиков:
- Интернет-каналы
- Виртуальные АТС
- Выделенные линии
- Оптические каналы

**Ручной процесс** занимает часы: составить письмо, найти контакты, отправить каждому, проверить почту, классифицировать ответы.

### Решение

Приложение автоматизирует весь цикл:

| Этап | Что делает система |
|------|-------------------|
| 1. Подготовка | Создание профилей закупок, импорт контактов |
| 2. Отправка | Генерация писем по шаблонам, массовая рассылка с задержками |
| 3. Приём | Автоматическая проверка IMAP, классификация ответов |
| 4. Обработка | Создание задач оператору, извлечение данных из КП |

---

## 🛠️ Стек технологий

| Компонент | Технология | Версия |
|-----------|-----------|--------|
| Язык | Python | 3.14+ |
| GUI | PyQt6 | 6.x |
| База данных | SQLite | 3.x |
| ORM | SQLAlchemy | 2.x |
| Миграции | Alembic | ✅ |
| Планировщик | APScheduler | ✅ |
| Шифрование | cryptography (Fernet) | — |
| Логирование | loguru | — |
| Тестирование | pytest | — |
| LLM API | ProxyAPI | — |

---

## 🚀 Инструкция по запуску

### Требования

- Python 3.11 или выше
- Windows 10/11 (тестировалось)
- ~500 МБ свободного места

### Установка

```bash
# 1. Перейти в папку проекта
cd spam_kp_assistant

# 2. Установить зависимости
pip install -r requirements.txt
```

### Настройка (опционально)

```bash
# Скопировать пример конфигурации
copy .env.example .env

# Отредактировать .env и вставить API ключ ProxyAPI
# PROXYAPI_API_KEY=your_key_here
```

### Запуск GUI

**Вариант 1: Готовый .exe (Windows)**
```
dist/SpamKPAssistant/SpamKPAssistant.exe
```
Просто запустите — Python не требуется!

**Вариант 2: Из исходников**
```bash
# Стандартный запуск
python run.py

# Или с диагностикой
python run_now.py

# Или простой запуск
python run_simple.py
```

### Запуск консольного режима

```bash
python console_app.py
```

### Заполнение демо-данными

```bash
python seed_demo_data.py
```

---

## 📋 API / Команды приложения

### Графический интерфейс

Приложение управляется через GUI. Основные разделы:

| Раздел | Описание |
|--------|----------|
| 📋 **Профили** | Создание и управление профилями закупок |
| 👥 **Контакты** | Импорт и просмотр контактов поставщиков |
| 📝 **Шаблоны** | Редактор писем с переменными |
| ⚙️ **Настройки** | SMTP/IMAP аккаунты, LLM конфигурация |

### Кнопки быстрого доступа

| Кнопка | Действие |
|--------|----------|
| ➕ **Новый профиль** | Открыть мастер создания профиля (5 шагов) |
| 📬 **Проверить почту** | Запустить IMAP проверку входящих писем |
| 📧 **Создать рассылку** | Мастер массовой отправки (4 шага) |
| 💡 **Демо/Помощь** | Открыть демо-интерфейс с примерами |

### Меню

- **Файл** → Новый профиль / Импорт контактов / Выход
- **Инструменты** → Проверить почту
- **Справка** → Добро пожаловать / О программе

---

## 📸 Скриншоты

> ⚠️ Скриншоты будут добавлены в следующей версии документации.
> 
> **Планируется:**
> - Главное окно
> - Мастер создания профиля
> - Демо-интерфейс
> - Диалог импорта контактов
> - Редактор шаблонов

### Главное окно

*![Главное окно приложения](docs/screenshots/main_window.png)*

### Мастер создания профиля

*![Мастер профиля](docs/screenshots/profile_wizard.png)*

### Демо-интерфейс

*![Демо-интерфейс с примерами](docs/screenshots/demo_interface.png)*

### Импорт контактов

*![Диалог импорта](docs/screenshots/import_dialog.png)*

### Редактор шаблонов

*![Редактор шаблонов](docs/screenshots/template_editor.png)*

---

## 📊 Статус разработки

| Версия | Статус | Описание |
|--------|--------|----------|
| **v2.1.1** | ✅ **Завершён** | Улучшения UI (версия, модель LLM) |
| **v2.1** | ✅ **Завершён** | LLM генерация писем |
| **v2.0** | ✅ **Production-ready** | P0/P1/P2 завершены, 308 тестов |
| v1.x | ✅ Завершён | Phase 1-4 (GUI, рассылки, входящие, автоматизация) |
| v2.2 | 📋 В планах | GUI настройка LLM, статистика использования |
| v3.0 | 📋 В планах | Извлечение данных из КП, умное сравнение, веб-интерфейс |

**Текущая версия:** 2.1.1  
**Прогресс:** LLM генерация + настройка UI ✅  
**Тесты:** 308/308 (100%)

🗺️ [Полная дорожная карта](docs/ROADMAP.md)

---

## 🗺️ Планы на будущие версии

### v2.2 — Улучшение генерации (в планах)
- Few-shot learning (использование исторических успешных писем)
- A/B тестирование промптов
- Статистика качества генераций
- Поддержка нескольких тонов письма

### v3.0 — Интеллект и аналитика (в планах)
- Извлечение цен и сроков из КП через LLM
- Умное сравнение предложений
- Автоответы на типовые вопросы
- Веб-интерфейс (опционально)

---

## 📁 Структура проекта

```
spam_kp_assistant/
├── README.md                    ← ты здесь
├── requirements.txt             ← зависимости Python
├── .gitignore                   ← исключения Git
├── run.py                       ← запуск GUI (стандартный)
├── run_now.py                   ← запуск GUI (диагностика)
├── run_simple.py                ← запуск GUI (простой)
├── console_app.py               ← консольный интерфейс
├── seed_demo_data.py            ← демо-данные
│
├── core/                        ← ядро приложения
│   ├── database.py              ← инициализация SQLite
│   └── models.py                ← 8 моделей SQLAlchemy
│
├── gui/                         ← графический интерфейс
│   ├── app.py                   ← точка входа GUI
│   ├── main_window.py           ← главное окно (вкладки: Профили, Контакты, Шаблоны, Переписка, Задачи, Настройки)
│   ├── wizard_profile.py        ← мастер профиля (5 страниц)
│   ├── wizard_mailing.py        ← мастер рассылки (4 шага)
│   ├── dialog_import_contacts.py← импорт CSV/XLSX
│   ├── dialog_template_editor.py← редактор шаблонов
│   ├── dialog_smtp_settings.py  ← настройка SMTP/IMAP
│   ├── dialog_mailing_progress.py← прогресс рассылки с паузой/отменой
│   ├── dialog_welcome.py        ← демо-интерфейс
│   ├── dialog_message_viewer.py ← просмотр переписки
│   ├── dialog_rule_manager.py   ← управление правилами
│   ├── dialog_rule_editor.py    ← редактор правил
│   ├── dialog_condition_editor.py← редактор условий
│   ├── dialog_action_editor.py  ← редактор действий
│   ├── dialog_kp_comparison.py  ← сравнение КП
│   ├── dialog_reports.py        ← отчёты и аналитика
│   └── dialog_reminder_templates.py← редактор шаблонов напоминаний (P2)
│
├── services/                    ← бизнес-логика
│   ├── email_service.py         ← отправка/получение писем + retry
│   ├── llm_service.py           ← интеграция с ProxyAPI + rate limiting
│   ├── parser_service.py        ← парсер PDF/Excel/DOCX
│   ├── mailing_service.py       ← сервис массовых рассылок ✨
│   ├── inbox_service.py         ← сервис входящих писем + threading/дедупликация
│   ├── reminder_service.py      ← сервис напоминаний ✨
│   ├── scheduler_service.py     ← планировщик фоновых задач + автоочистка ✨
│   ├── rule_engine.py           ← движок правил + persistence ✨
│   ├── template_service.py      ← сервис шаблонов с кэшированием ✨
│   ├── profile_service.py       ← сервис профилей с кэшированием ✨
│   ├── audit_service.py         ← аудит действий ✨
│   ├── data_export_import_service.py  ← экспорт/импорт ✨
│   ├── kp_comparison_service.py ← сравнение КП ✨
│   └── analytics_service.py     ← отчёты и аналитика ✨
│
├── utils/                       ← утилиты
│   ├── encryption.py            ← шифрование Fernet
│   ├── validators.py            ← валидация данных
│   ├── file_protection.py       ← защита файлов
│   ├── attachment_manager.py    ← сохранение вложений ✨
│   ├── cache.py                 ← TTL-кэш ✨
│   ├── retry.py                 ← retry с backoff ✨
│   └── rate_limiter.py          ← rate limiting ✨
│
├── docs/                        ← документация
│   ├── README.md                ← этот файл
│   ├── USER_GUIDE.md            ← руководство пользователя
│   ├── TECHNICAL.md             ← техническая документация
│   ├── TESTING.md               ← тестирование
│   ├── API_REFERENCE.md         ← справочник API
│   ├── TROUBLESHOOTING.md       ← решение проблем
│   ├── CHANGELOG.md             ← история версий
│   ├── SECURITY_AUDIT.md        ← аудит безопасности
│   ├── P1_P2_COMPLETE.md        ← итоги P1+P2
│   └── screenshots/             ← скриншоты (будут добавлены)
│
├── data/                        ← данные и логи
│   ├── spam_kp_assistant.db     ← база данных SQLite
│   ├── app.log                  ← логи приложения
│   └── test_contacts.csv        ← тестовые данные
│
└── tests/                       ← тесты
    ├── conftest.py              ← глобальные фикстуры
    ├── test_basic.py
    ├── test_database.py
    ├── test_encryption.py
    ├── test_import.py
    ├── test_smtp_manager.py
    ├── test_mailing_service.py  ← рассылки (20 тестов)
    ├── test_inbox_service.py    ← входящие (22 теста)
    ├── test_llm_service.py      ← LLM (12 тестов)
    ├── test_parser_service.py   ← парсер (13 тестов)
    ├── test_contact_importer.py ← импорт (8 тестов)
    ├── test_reminder_service.py ← напоминания (8 тестов)
    ├── test_scheduler_service.py← планировщик (13 тестов)
    ├── test_rule_engine.py      ← правила (20 тестов)
    ├── test_attachment_manager.py← вложения (14 тестов)
    ├── test_rule_gui.py         ← GUI правил (13 тестов)
    ├── test_kp_comparison_service.py← сравнение КП (19 тестов)
    ├── test_analytics_service.py← отчёты (13 тестов)
    ├── test_retry.py            ← retry/backoff ✨
    ├── test_rate_limiter.py     ← rate limiting ✨
    ├── test_audit_service.py    ← аудит ✨
    ├── test_rule_engine_db.py   ← rule persistence ✨
    ├── test_inbox_threading.py  ← threading/дедупликация ✨
    ├── test_cache.py            ← кэш ✨
    └── test_data_export_import.py← экспорт/импорт ✨
```

---

## 🧪 Тестирование

```bash
# Запуск всех тестов
python -m pytest tests/ -v

# С покрытием
python -m pytest tests/ -v --cov=. --cov-report=html

# Только P1 тесты
python -m pytest tests/test_retry.py tests/test_rate_limiter.py tests/test_audit_service.py -v

# Только P2 тесты
python -m pytest tests/test_cache.py tests/test_inbox_threading.py tests/test_data_export_import.py -v
```

**Результаты:** 290 тестов, 290 пройдено, 1 skipped (99.7%)

**Новые тесты (P1 + P2):**
- `test_retry.py` — retry с exponential backoff (9 тестов)
- `test_rate_limiter.py` — rate limiting для LLM (6 тестов)
- `test_audit_service.py` — аудит действий (9 тестов)
- `test_rule_engine_db.py` — persistence правил (5 тестов)
- `test_inbox_threading.py` — threading и дедупликация (6 тестов)
- `test_cache.py` — TTL-кэш (12 тестов)
- `test_data_export_import.py` — экспорт/импорт (7 тестов)

**Итого:** +52 новых теста, общий процент покрытия ~90%

📊 [Подробная статистика тестов](docs/TESTING.md)

---

## 🤝 Участие в проекте

Проект open-source. Приветствуются:
- 🐛 Баг-репорты
- 💡 Предложения по функционалу
- 🔧 Pull requests
- 📖 Улучшение документации

---

## 📄 Лицензия

Разработано **NLP-Core-Team** © 2026

---

**Версия:** 2.1.1  
**Дата:** 2026-05-22  
**Статус:** P0 ✅, P1 ✅, P2 ✅ (Production-ready)  
**Тесты:** 308/308 (100%)

📘 [Руководство пользователя](docs/USER_GUIDE.md) &nbsp;|&nbsp; 🤖 [Модели LLM](docs/LLM_MODELS.md) &nbsp;|&nbsp; 🗺️ [Roadmap](docs/ROADMAP.md) &nbsp;|&nbsp; 🛠️ [Техническая документация](docs/TECHNICAL.md) &nbsp;|&nbsp; 🧪 [Тестирование](docs/TESTING.md) &nbsp;|&nbsp; 📝 [CHANGELOG](docs/CHANGELOG.md)
