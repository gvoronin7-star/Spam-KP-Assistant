# LLM Генерация писем (v2.1)

## 📋 Описание

Функция автоматической генерации писем через Large Language Models (LLM). Позволяет создавать персонализированные письма на основе профиля закупки и контекста диалога.

## ✨ Возможности

### 1. Генерация первичного письма
- Автоматическое создание письма на основе профиля закупки
- Извлечение технических параметров и требований
- Персонализация по компании и контактному лицу
- Поддержка fallback на шаблоны при ошибках LLM

### 2. Генерация напоминаний
- **Напоминание 1** (3 дня без ответа) — вежливое, ненавязчивое
- **Напоминание 2** (7 дней без ответа) — более настойчивое
- Учет контекста диалога
- Автоматическое определение сроков

### 3. Follow-up письма
- Уточнение деталей
- Запрос дополнительной информации
- Ответ на вопросы поставщика
- Гибкая настройка цели письма

## 🏗️ Архитектура

```
services/
├── llm_generator_service.py  # Основной сервис генерации
├── prompts.py                # Библиотека промптов
└── llm_service.py           # Интеграция с LLM (rate limiting)

gui/
├── wizard_mailing.py        # Мастер рассылки (кнопка LLM)
└── dialog_llm_preview.py    # Диалог предпросмотра и редактирования

tests/
└── test_llm_generator_service.py  # Тесты (16 тестов, 15 passed)
```

## 📖 API

### LLMGeneratorService

```python
from services.llm_generator_service import LLMGeneratorService

generator = LLMGeneratorService()

# Генерация первичного письма
result = generator.generate_primary_email(
    profile=profile,      # Profile
    contact=contact,      # Contact
    template=template     # Optional[Template]
)
# Returns: {
#   'subject': str,
#   'body_plain': str,
#   'body_html': str,
#   'variables_used': list
# }

# Генерация напоминания
result = generator.generate_reminder(
    dialogue=dialogue,        # Dialogue
    reminder_type='reminder_1'  # 'reminder_1' или 'reminder_2'
)

# Генерация follow-up
result = generator.generate_followup(
    dialogue=dialogue,  # Dialogue
    context={           # Dict
        'purpose': 'Уточнить детали',
        'additional_info': 'Нужна информация о ценах'
    }
)
```

### Промпты

```python
from services.prompts import (
    format_primary_email_prompt,
    format_reminder_1_prompt,
    format_reminder_2_prompt,
    format_followup_prompt
)

# Форматирование промпта
prompt = format_primary_email_prompt(
    operator_name='Наша компания',
    service_name='Интернет-канал 100 Мбит/с',
    description='Запрос для офиса на 50 мест',
    tech_params={'speed': '100 Мбит/с'},
    budget='50000',
    deadlines='30 дней',
    company='ООО Тест',
    contact_person='Иванов И.И.'
)
```

## 🎨 GUI Интеграция

### Мастер рассылки (wizard_mailing.py)

Кнопка **"✨ Сгенерировать через LLM"** добавлена на страницу выбора профиля и шаблона:

- Активируется после выбора профиля
- Запускает генерацию в фоновом потоке
- Показывает диалог предпросмотра
- Позволяет редактировать и применять результат

### Диалог предпросмотра (dialog_llm_preview.py)

**Возможности:**
- Просмотр сгенерированного письма в 4 табах:
  - 📝 Тема
  - 📄 Текст (Plain)
  - 🌐 HTML
  - 👁️ Предпросмотр
- Кнопка **"✨ Перегенерировать"** — новая генерация
- Кнопка **"📋 Копировать текст"** — в буфер обмена
- Кнопка **"💾 Применить"** — сохранить изменения
- Валидация заполнения темы и текста

## 🔧 Настройка

### Зависимости

```python
# В services/llm_service.py уже настроено:
- Rate limiting (RPM/RPH/TPM/TPD)
- Поддержка нескольких моделей
- Fallback при ошибках
```

### Параметры генерации

В `services/llm_generator_service.py`:

```python
class LLMGeneratorService:
    def __init__(self, llm_service=None):
        # Если llm_service=None, создаётся автоматически
        # Можно передать кастомный экземпляр для настройки
        self.llm_service = llm_service or LLMService()
```

## 🧪 Тестирование

```bash
# Запуск тестов генератора
python -m pytest tests/test_llm_generator_service.py -v

# Результаты:
# 15 passed, 1 skipped
```

**Покрытие:**
- Генерация первичного письма ✅
- Генерация напоминаний ✅
- Генерация follow-up ✅
- Извлечение параметров профиля ✅
- Построение промптов ✅
- Парсинг ответа LLM ✅
- Fallback на шаблоны ✅
- Обработка ошибок ✅

## 📊 Примеры использования

### 1. Создание первичного письма

```python
from core.database import SessionLocal
from services.llm_generator_service import LLMGeneratorService

db = SessionLocal()
try:
    profile = db.query(Profile).get(profile_id)
    contact = db.query(Contact).get(contact_id)
    
    generator = LLMGeneratorService()
    result = generator.generate_primary_email(profile, contact)
    
    print(f"Тема: {result['subject']}")
    print(f"Текст: {result['body_plain']}")
finally:
    db.close()
```

### 2. Перегенерация с новыми параметрами

```python
# В диалоге предпросмотра
def on_regenerate():
    # Новая генерация с теми же параметрами
    return generator.generate_primary_email(profile, contact)

dialog = DialogLLMPreview(
    initial_data,
    on_regenerate=on_regenerate
)
dialog.exec()
```

## 🔒 Безопасность

- **Rate limiting:** Ограничение запросов к LLM (RPM/RPH/TPM/TPD)
- **Fallback:** При ошибке LLM используется шаблон
- **Валидация:** Проверка результата перед применением
- **Логирование:** Все генерации логируются через Loguru

## 🐛 Known Issues

- Нет проблем на текущий момент
- Все тесты проходят

## 📝 Планы на будущее

### v2.1.1
- [ ] Поддержка few-shot learning (использование исторических успешных писем)
- [ ] A/B тестирование промптов
- [ ] Статистика качества генераций

### v2.2
- [ ] Извлечение цен и сроков из КП через LLM
- [ ] Умное сравнение предложений
- [ ] Автоответы на типовые вопросы

## 📚 Ссылки

- [API_REFERENCE.md](API_REFERENCE.md) — Справочник API
- [TECHNICAL.md](TECHNICAL.md) — Техническая документация
- [USER_GUIDE.md](USER_GUIDE.md) — Руководство пользователя