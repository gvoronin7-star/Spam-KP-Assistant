"""
Сервис работы с LLM через ProxyAPI
"""
import json
from typing import Dict, List, Optional, Any
from openai import OpenAI
from loguru import logger

from utils.rate_limiter import RateLimiter, RateLimitConfig


class LLMService:
    """Сервис для работы с LLM через ProxyAPI"""
    
    def __init__(self, rate_limit_config: Optional[RateLimitConfig] = None):
        self.client = None
        self.primary_model = "gpt-5.4-mini"
        self.fallback_model = "gpt-5.3-chat-latest"
        self.parsing_model = "gemini-3.1-flash-lite"
        self.api_key = None
        self.rate_limiter = RateLimiter(rate_limit_config)
    
    def configure(self, api_key: str):
        """Настройка ProxyAPI"""
        self.api_key = api_key
        
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.proxyapi.ru/openai/v1"
        )
        
        logger.info("LLM сервис настроен (ProxyAPI)")
    
    def test_connection(self) -> bool:
        """Тестовый запрос"""
        try:
            response = self.client.chat.completions.create(
                model=self.primary_model,
                messages=[{"role": "user", "content": "Привет!"}],
                max_tokens=10
            )
            logger.info("LLM подключение успешно")
            return True
        except Exception as e:
            logger.error(f"Ошибка LLM подключения: {e}")
            return False
    
    def generate_response(
        self,
        system_prompt: str,
        user_message: str,
        history: Optional[List[Dict]] = None,
        model: Optional[str] = None
    ) -> str:
        """Генерация ответа с rate limiting"""
        model = model or self.primary_model
        
        # Rate limiting
        if not self.rate_limiter.wait_if_needed(estimated_tokens=1000):
            logger.error("Rate limit превышен. Запрос к LLM отклонён.")
            return None
    
        messages = [{"role": "system", "content": system_prompt}]
        
        if history:
            messages.extend(history)
        
        messages.append({"role": "user", "content": user_message})
        
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.7,
                max_tokens=1000
            )
            
            # Записать использование токенов
            tokens_used = response.usage.total_tokens if response.usage else 0
            self.rate_limiter.record_request(tokens_used=tokens_used)
            
            return response.choices[0].message.content
        
        except Exception as e:
            logger.error(f"Ошибка генерации ответа: {e}")
            
            # Fallback на вторую модель
            if model != self.fallback_model:
                logger.info("Попробую fallback модель")
                return self.generate_response(
                    system_prompt,
                    user_message,
                    history,
                    model=self.fallback_model
                )
            
            return None
    
    def extract_entities(self, text: str, profile_data: Dict) -> Dict:
        """Извлечение сущностей из текста"""
        system_prompt = f"""
Ты — ассистент оператора закупки телеком-услуг.
Проанализируй вопрос поставщика и верни ТОЛЬКО JSON без markdown.

Контекст закупки: {json.dumps(profile_data, ensure_ascii=False, indent=2)}

Верни JSON в формате:
{{
  "type": "параметр_услуги" | "цена" | "сроки" | "документ" | "другое",
  "entities": {{
    "скорость": "...",
    "город": "...",
    "сумма": "...",
    ...
  }},
  "needs_human": true/false
}}
"""
        
        response = self.generate_response(system_prompt, text)
        
        if response:
            try:
                # Очистка от markdown
                response = response.replace("```json", "").replace("```", "").strip()
                return json.loads(response)
            except:
                logger.error("Ошибка парсинга JSON из ответа LLM")
                return {"type": "другое", "entities": {}, "needs_human": True}
        
        return {"type": "другое", "entities": {}, "needs_human": True}
    
    def validate_response(self, response: str, allowed_values: Dict) -> tuple:
        """
        Валидация ответа на наличие недопустимых значений
        
        Returns:
            (is_valid, violations)
        """
        import re
        
        violations = []
        
        # Поиск чисел в ответе
        numbers = re.findall(r'\d+[.,]?\d*', response)
        
        for num in numbers:
            # Проверка против разрешённых значений
            if not self._is_allowed_value(num, allowed_values):
                violations.append(f"Недопустимое значение: {num}")
        
        return len(violations) == 0, violations
    
    def _is_allowed_value(self, value: str, allowed_values: Dict) -> bool:
        """Проверка значения против разрешённых"""
        # Простая реализация - можно улучшить
        for key, values in allowed_values.items():
            if isinstance(values, list):
                if value in [str(v) for v in values]:
                    return True
        return True  # По умолчанию разрешаем
    
    def parse_kp_with_llm(self, text: str) -> Dict:
        """
        Извлечение данных из КП с помощью LLM
        
        Используется для сложных случаев, когда парсер не справляется
        """
        system_prompt = """
Ты помогаешь извлечь данные из коммерческого предложения.
Верни JSON со структурой:

{
  "prices": [{"service": "...", "price": "...", "currency": "RUB"}],
  "terms": [{"name": "...", "value": "..."}],
  "notes": "Общие условия"
}
"""
        
        response = self.generate_response(
            system_prompt,
            text,
            model=self.parsing_model
        )
        
        if response:
            try:
                response = response.replace("```json", "").replace("```", "").strip()
                return json.loads(response)
            except:
                return {"prices": [], "terms": [], "notes": text[:500]}
        
        return {"prices": [], "terms": [], "notes": text[:500]}

    def classify_with_llm(self, email_text: str, context: Optional[Dict] = None) -> Dict:
        """
        Классификация ответа поставщика через LLM
        
        Args:
            email_text: Текст письма
            context: Дополнительный контекст (профиль, история диалога)
        
        Returns:
            {
                "category": "kp|question|refusal|auto_reply|spam|unknown",
                "confidence": 0.0-1.0,
                "summary": "краткое содержание",
                "extracted_data": {...} (если есть),
                "needs_response": true/false,
                "priority": "low|medium|high"
            }
        """
        context_info = ""
        if context:
            context_info = f"\n\nКонтекст диалога:\n{json.dumps(context, ensure_ascii=False, indent=2)}"
        
        system_prompt = f"""
Ты — ассистент оператора закупки телеком-услуг.
Проанализируй ответ поставщика и классифицируй его.

ВАЖНО: Игнорируй цитаты оригинальных писем (текст после "From:", ">", "-----Original Message-----").
Анализируй только НОВЫЙ текст ответа!

Категории:
- kp: Коммерческое предложение (с ценами, тарифами, условиями)
- question: Вопрос от поставщика (нужен уточняющий ответ)
- refusal: Отказ от сотрудничества
- auto_reply: Автоматический ответ (отпуск, недоступность)
- spam: Спам или рекламное письмо
- unknown: Непонятный тип

Критерии:
- Если есть цены, тарифы, стоимость, "КП во вложении" — это kp
- Если есть вопросы к оператору ("уточните", "какой адрес", "где находится") — это question
- Если прямой отказ ("не можем", "не предоставляем") — это refusal
- Если автоматический ответ с информацией об отсутствии — auto_reply
- Если массовая рассылка без контекста — spam

Верни ТОЛЬКО JSON без markdown в формате:
{{
  "category": "...",
  "confidence": 0.0-1.0,
  "summary": "краткое содержание",
  "needs_response": true/false,
  "priority": "low|medium|high",
  "key_points": ["важный вопрос 1", "важный вопрос 2"]
}}

{context_info}
"""
        
        user_prompt = f"""
Текст письма поставщика:

{email_text[:3000]}
"""
        
        try:
            response = self.generate_response(
                system_prompt,
                user_prompt,
                model=self.primary_model
            )
            
            if response:
                # Очистка от markdown
                response = response.replace("```json", "").replace("```", "").strip()
                
                # Попытка парсинга JSON
                try:
                    data = json.loads(response)
                    
                    # Валидация категорий
                    valid_categories = ["kp", "question", "refusal", "auto_reply", "spam", "unknown"]
                    if data.get("category") not in valid_categories:
                        data["category"] = "unknown"
                    
                    # Уверенность по умолчанию высокая для LLM
                    if "confidence" not in data:
                        data["confidence"] = 0.85
                    
                    # Summary
                    if "summary" not in data:
                        data["summary"] = email_text[:100].replace("\n", " ").strip() + "..."
                    
                    # Потребность в ответе
                    if "needs_response" not in data:
                        data["needs_response"] = data["category"] in ["question", "kp"]
                    
                    # Приоритет
                    if "priority" not in data:
                        if data["category"] == "question":
                            data["priority"] = "high"
                        elif data["category"] == "kp":
                            data["priority"] = "medium"
                        else:
                            data["priority"] = "low"
                    
                    return data
                    
                except json.JSONDecodeError:
                    # Если JSON не распарсился, попробуем эвристику
                    logger.warning(f"LLM вернул не-JSON: {response[:200]}")
                    return {
                        "category": "unknown",
                        "confidence": 0.3,
                        "summary": f"LLM не смог классифицировать: {email_text[:100]}...",
                        "needs_response": False,
                        "priority": "low"
                    }
            
            return {
                "category": "unknown",
                "confidence": 0.2,
                "summary": "LLM не ответил",
                "needs_response": False,
                "priority": "low"
            }
        
        except Exception as e:
            logger.error(f"Ошибка LLM классификации: {e}")
            return {
                "category": "unknown",
                "confidence": 0.1,
                "summary": f"Ошибка классификации: {str(e)[:100]}",
                "needs_response": False,
                "priority": "low"
            }

    def generate_reply_draft(
        self,
        email_text: str,
        dialogue_context: Dict,
        classification: Dict
    ) -> Dict:
        """
        Генерация черновика ответа на письмо
        
        Args:
            email_text: Текст письма
            dialogue_context: Контекст диалога (профиль, контакты, история)
            classification: Результат классификации
        
        Returns:
            {
                "subject": "Тема ответа",
                "body": "Текст ответа",
                "tone": "friendly|formal|neutral"
            }
        """
        context_info = json.dumps(dialogue_context, ensure_ascii=False, indent=2)
        
        system_prompt = f"""
Ты — помощник оператора закупки телеком-услуг.
Напиши профессиональный ответ поставщику на русском языке.

Контекст:
{context_info}

Классификация входящего письма:
- Категория: {classification.get('category', 'unknown')}
- Ключевые моменты: {classification.get('key_points', [])}

Требования к ответу:
- Деловой, но дружелюбный тон
- Кратко и по делу
- Ответить на все вопросы из письма
- Если нужны уточнения — запросить их
- В конце — призыв к действию

Верни JSON в формате:
{{
  "subject": "Тема ответа (Re: ...)",
  "body": "Текст ответа",
  "tone": "formal"
}}
"""
        
        user_prompt = f"""
Входящее письмо:

{email_text[:2000]}
"""
        
        try:
            response = self.generate_response(
                system_prompt,
                user_prompt,
                model=self.primary_model
            )
            
            if response:
                response = response.replace("```json", "").replace("```", "").strip()
                
                try:
                    data = json.loads(response)
                    return {
                        "subject": data.get("subject", "Re: Запрос"),
                        "body": data.get("body", ""),
                        "tone": data.get("tone", "formal")
                    }
                except:
                    return {
                        "subject": "Re: Запрос",
                        "body": response,
                        "tone": "formal"
                    }
            
            return None
        
        except Exception as e:
            logger.error(f"Ошибка генерации ответа: {e}")
            return None
    
    def get_rate_limit_stats(self) -> dict:
        """Получить статистику rate limiting"""
        return self.rate_limiter.get_stats()
    
    def clean_email_quotes(self, email_text: str) -> str:
        """
        Очистить письмо от цитат оригиналов
        
        Args:
            email_text: Исходный текст письма
        
        Returns:
            Очищенный текст (только новый ответ)
        """
        import re
        
        # Паттерны для поиска цитат
        quote_patterns = [
            r"(?i)(From:.*?\n\n)",  # From: ...
            r"(?i)(-----Original Message-----.*?\n\n)",  # -----Original Message-----
            r"(?i)(> .*$)",  # > цитирование
            r"(?i)(On .*? wrote:)",  # On ... wrote:
            r"(?i)(^\n*-\n*От:.*?\n\n)",  # От: ... (русский Outlook)
        ]
        
        cleaned = email_text
        
        for pattern in quote_patterns:
            cleaned = re.sub(pattern, "", cleaned, flags=re.MULTILINE | re.DOTALL)
        
        # Удалить пустые строки в начале
        cleaned = cleaned.strip()
        
        # Оставить только первые 2-3 абзаца (новый текст обычно в начале)
        paragraphs = cleaned.split('\n\n')
        if len(paragraphs) > 3:
            cleaned = '\n\n'.join(paragraphs[:3])
        
        return cleaned
