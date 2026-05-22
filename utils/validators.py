"""
Валидация данных
"""
import re
from typing import Dict, Any, List, Tuple
from email_validator import validate_email, EmailNotValidError
from loguru import logger


def validate_email_address(email: str) -> Tuple[bool, str]:
    """
    Валидация email-адреса
    
    Returns:
        (is_valid, message)
    """
    try:
        valid = validate_email(email, check_deliverability=False)
        return True, valid.email
    except EmailNotValidError as e:
        return False, str(e)


def validate_profile_data(profile_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Валидация данных профиля закупки
    
    Returns:
        (is_valid, errors)
    """
    errors = []
    
    # Обязательные поля
    if not profile_data.get("name"):
        errors.append("Не указано имя профиля")
    
    # Технические параметры (проверка структуры)
    tech_params = profile_data.get("tech_params", {})
    if not isinstance(tech_params, dict):
        errors.append("Технические параметры должны быть объектом")
    
    # Требования (проверка структуры)
    requirements = profile_data.get("requirements", {})
    if not isinstance(requirements, dict):
        errors.append("Требования должны быть объектом")
    
    # Правила диалога (проверка структуры)
    dialogue_rules = profile_data.get("dialogue_rules", {})
    if not isinstance(dialogue_rules, dict):
        errors.append("Правила диалога должны быть объектом")
    
    return len(errors) == 0, errors


def sanitize_html(html: str) -> str:
    """
    Очистка HTML от потенциально опасного контента
    
    Пока простая реализация - можно улучшить с BeautifulSoup
    """
    # Удаление скриптов
    html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    # Удаление стилей
    html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
    return html


def extract_variables(template: str) -> List[str]:
    """
    Извлечение переменных из шаблона
    Пример: {{ company }}, {{ service_name }}
    """
    pattern = r'\{\{\s*(\w+)\s*\}\}'
    return re.findall(pattern, template)
