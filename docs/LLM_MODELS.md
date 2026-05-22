# 🤖 Модели LLM в Spam KP Assistant

## 📋 Описание

Spam KP Assistant использует **3 модели Large Language Models (LLM)** через сервис **ProxyAPI** для различных задач автоматизации закупки телеком-услуг.

---

## 🎯 Используемые модели

| Модель | Назначение | Приоритет | Тип задачи |
|--------|-----------|-----------|------------|
| **gpt-5.4-mini** | Основная рабочая модель | Primary | Классификация, генерация |
| **gpt-5.3-chat-latest** | Резервная модель | Fallback | Подстраховка при сбоях |
| **gemini-3.1-flash-lite** | Специализированная | Parsing | Парсинг документов |

---

## 📚 Детальное описание

### 1. **gpt-5.4-mini** (Основная модель)

**Назначение:** Основная модель для всех задач генерации и классификации.

**Где используется:**

| Модуль | Задача | Описание |
|--------|--------|----------|
| `InboxService` | Классификация писем | Определение типа входящего сообщения (КП/вопрос/отказ/спам) |
| `LLMService` | Генерация ответов | Создание черновиков ответов поставщикам |
| `LLMGeneratorService` | Генерация запросов | Создание первичных писем, напоминаний, follow-up |
| `LLMAgentService` | Авто-ответы | Генерация ответов в режиме агента |
| `ParserService` | Извлечение сущностей | Парсинг параметров из текста |

**Примеры использования:**

```python
# 1. Классификация входящего письма
from services.inbox_service import InboxService

service = InboxService()
result = service.classify_response(
    "Добрый день! Во вложении КП на 100 Мбит/с..."
)
# Результат: {
#   "category": "kp",
#   "confidence": 0.85,
#   "summary": "Коммерческое предложение",
#   "needs_response": true,
#   "priority": "medium"
# }

# 2. Генерация ответа
from services.llm_service import LLMService

llm = LLMService()
draft = llm.generate_reply_draft(
    email_text="Вопрос от поставщика...",
    dialogue_context={"profile": {...}, "history": [...]},
    classification={"category": "question"}
)
# Результат: {
#   "subject": "Re: Уточнение по запросу",
#   "body": "Добрый день! Спасибо за вопрос...",
#   "tone": "formal"
# }

# 3. Генерация запроса КП
from services.llm_generator_service import LLMGeneratorService

generator = LLMGeneratorService()
result = generator.generate_primary_email(
    profile=profile,  # Профиль закупки
    contact=contact   # Контакт поставщика
)
# Результат: {
#   "subject": "Запрос коммерческого предложения...",
#   "body_plain": "Уважаемые коллеги, просим направить КП...",
#   "body_html": "<p>Уважаемые коллеги...</p>"
# }
```

**Характеристики:**
- **Скорость:** ~2-5 секунд на запрос
- **Точность:** ~85-95% для классификации
- **Стоимость:** Низкая (mini-версия)
- **Rate limit:** 60 RPM, 1000 TPM

---

### 2. **gpt-5.3-chat-latest** (Резервная модель)

**Назначение:** Автоматическая подстраховка при сбоях основной модели.

**Где используется:**

| Сценарий | Описание |
|----------|----------|
| Timeout API | Если основная модель не отвечает за 30 сек |
| Ошибка 5xx | Серверная ошибка на стороне ProxyAPI |
| Rate limit | При достижении лимитов основной модели |
| Некорректный ответ | Если LLM вернул невалидный JSON |

**Автоматический fallback:**

```python
# В services/llm_service.py
def generate_response(self, system_prompt, user_message, model=None):
    model = model or self.primary_model  # gpt-5.4-mini
    
    try:
        response = self.client.chat.completions.create(
            model=model,
            messages=messages,
            ...
        )
        return response.choices[0].message.content
        
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        
        # Автоматический переход на fallback
        if model != self.fallback_model:
            logger.info("Попробую fallback модель (gpt-5.3-chat-latest)")
            return self.generate_response(
                system_prompt,
                user_message,
                model=self.fallback_model  # Переключаемся
            )
        
        return None  # Обе модели не работают
```

**Характеристики:**
- **Стабильность:** Выше, чем у основной
- **Скорость:** ~3-7 секунд на запрос
- **Назначение:** Только для fallback, не для первичных запросов

---

### 3. **gemini-3.1-flash-lite** (Модель для парсинга)

**Назначение:** Специализированная модель для работы с документами и таблицами.

**Где используется:**

| Модуль | Задача | Описание |
|--------|--------|----------|
| `ParserService` | Парсинг PDF | Извлечение текста из PDF КП |
| `ParserService` | Парсинг Excel | Чтение таблиц с ценами |
| `ParserService` | Парсинг Word | Обработка DOCX документов |
| `LLMService` | Извлечение данных | Парсинг цен, сроков, условий |

**Примеры использования:**

```python
# 1. Парсинг сложного КП
from services.parser_service import ParserService

parser = ParserService()
result = parser.parse_pdf_with_llm(
    file_path="data/kp_ООО_Телеком.pdf",
    llm_service=llm  # Использует gemini-3.1-flash-lite
)
# Результат: {
#   "prices": [
#     {"service": "Интернет 100 Мбит/с", "price": "4500", "currency": "RUB"},
#     {"service": "АТС на 50 номеров", "price": "12000", "currency": "RUB"}
#   ],
#   "terms": [
#     {"name": "Срок подключения", "value": "14 дней"},
#     {"name": "Оплата", "value": "предоплата 50%"}
#   ],
#   "notes": "Действует скидка 10% при годовой оплате"
# }

# 2. Извлечение цен из текста
from services.llm_service import LLMService

llm = LLMService()
parsed = llm.parse_kp_with_llm(
    text="Текст коммерческого предложения..."
)
```

**Характеристики:**
- **Скорость:** ~3-10 секунд (зависит от размера документа)
- **Точность:** ~80-90% для извлечения данных
- **Стоимость:** Очень низкая (flash-lite)
- **Особенности:** Оптимизирована для работы с длинным контекстом

---

## 🔧 Конфигурация

### Файл `.env`

```env
# ===========================================
# Настройка моделей LLM
# ===========================================

# API ключ ProxyAPI
PROXYAPI_API_KEY=your_api_key_here

# Основная модель (классификация, генерация)
PROXYAPI_PRIMARY_MODEL=gpt-5.4-mini

# Резервная модель (fallback)
PROXYAPI_FALLBACK_MODEL=gpt-5.3-chat-latest

# Модель для парсинга документов
PROXYAPI_PARSING_MODEL=gemini-3.1-flash-lite
```

### Файл `config.py`

```python
class Settings(BaseSettings):
    # ProxyAPI
    proxyapi_api_key: Optional[str] = None
    proxyapi_primary_model: str = "gpt-5.4-mini"
    proxyapi_fallback_model: str = "gpt-5.3-chat-latest"
    proxyapi_parsing_model: str = "gemini-3.1-flash-lite"
```

### Отображение в интерфейсе

```
Статус LLM: LLM: ✅ Активен (gpt-5.4-mini)
```

---

## 📊 Статистика использования

| Тип операции | Модель | Токенов/запрос | Запросов/день | Токенов/день |
|-------------|--------|----------------|---------------|--------------|
| Классификация письма | gpt-5.4-mini | 500-1000 | 50-100 | 50K-100K |
| Генерация ответа | gpt-5.4-mini | 800-1500 | 20-50 | 40K-75K |
| Генерация запроса КП | gpt-5.4-mini | 1000-2000 | 10-30 | 20K-60K |
| Парсинг КП (PDF) | gemini-3.1-flash-lite | 2000-5000 | 5-20 | 20K-100K |
| Fallback запрос | gpt-5.3-chat-latest | 500-2000 | 1-5 | 1K-10K |

**Итого:** ~130K-345K токенов/день (~$0.5-2/день при стандартных тарифах ProxyAPI)

---

## 🚀 Смена моделей

### Варианты доступных моделей в ProxyAPI

**GPT-семейство:**
- `gpt-4o` — максимальное качество
- `gpt-4o-mini` — баланс качества и скорости
- `gpt-3.5-turbo` — быстрая, дешёвая

**Gemini-семейство:**
- `gemini-1.5-pro` — высокое качество
- `gemini-1.5-flash` — скорость
- `gemini-1.5-flash-lite` — минимальная стоимость

### Инструкция по смене

1. Откройте файл `.env` в корне проекта
2. Измените нужную переменную:
   ```env
   PROXYAPI_PRIMARY_MODEL=gpt-4o-mini
   ```
3. Сохраните файл
4. Перезапустите приложение

### Рекомендации по выбору

| Сценарий | Рекомендуемая модель | Почему |
|----------|---------------------|--------|
| **Стандартный** | gpt-5.4-mini | Оптимальный баланс |
| **Максимальное качество** | gpt-4o | Лучшая точность |
| **Минимальная стоимость** | gpt-3.5-turbo | Дёшево, приемлемое качество |
| **Быстрая обработка** | gemini-1.5-flash | Очень быстрая |
| **Сложные документы** | gemini-1.5-pro | Лучшее понимание контекста |

---

## 🔒 Безопасность и лимиты

### Rate Limiting

Все запросы проходят через Rate Limiter (`utils/rate_limiter.py`):

```python
# Стандартные лимиты
RPM = 60    # Запросов в минуту
RPH = 1000  # Запросов в час
TPM = 10000     # Токенов в минуту
TPD = 100000    # Токенов в день
```

**Автоматическая блокировка:**
- При превышении лимита запросы откладываются
- Логирование предупреждений
- Fallback на другую модель при необходимости

### Мониторинг

```python
# Получение статистики
from services.llm_service import LLMService

llm = LLMService()
stats = llm.get_rate_limit_stats()
# {
#   "rpm_used": 45, "rpm_limit": 60,
#   "rph_used": 320, "rph_limit": 1000,
#   "tpm_used": 8500, "tpm_limit": 10000,
#   "tpd_used": 85000, "tpd_limit": 100000
# }
```

---

## 🐛 Известные проблемы

| Проблема | Причина | Решение |
|----------|---------|---------|
| Fallback срабатывает часто | Нестабильность ProxyAPI | Проверьте баланс и лимиты |
| Медленная генерация | Высокая нагрузка на модель | Используйте gpt-3.5-turbo |
| Непонятные ответы | Слишком длинные промпты | Уменьшите контекст |

---

## 📚 Ссылки

- [ProxyAPI Documentation](https://proxyapi.ru/docs)
- [LLM_GENERATOR.md](LLM_GENERATOR.md) — Генерация писем
- [USER_GUIDE.md](USER_GUIDE.md) — Руководство пользователя
- [CHANGELOG.md](CHANGELOG.md) — История версий

---

**Версия документации:** 2.1.1  
**Последнее обновление:** 2026-05-22  
**Автор:** NLP-Core-Team
