"""
Сервис шаблонов с кэшированием
"""
from typing import Optional, List, Dict
from sqlalchemy.orm import Session
from loguru import logger

from core.models import Template
from utils.cache import get_template_cache, invalidate_cache_for_entity


class TemplateService:
    """Сервис для работы с шаблонами (с кэшированием)"""
    
    def __init__(self):
        self.cache = get_template_cache()
    
    def get_by_id(self, template_id: int, db: Session) -> Optional[Template]:
        """Получить шаблон по ID (с кэшем)"""
        cache_key = f"template:{template_id}"
        
        # Попробовать кэш
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        # Загрузить из БД
        template = db.query(Template).filter_by(id=template_id).first()
        if template:
            self.cache.set(cache_key, template)
        
        return template
    
    def get_all_active(self, db: Session) -> List[Template]:
        """Получить все активные шаблоны (с кэшем)"""
        cache_key = "templates:all"
        
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        templates = db.query(Template).filter_by(is_active=True).all()
        self.cache.set(cache_key, templates, ttl=300)
        return templates
    
    def get_by_name(self, name: str, db: Session) -> Optional[Template]:
        """Получить шаблон по имени"""
        # Не кэшируем по имени — редко используется
        return db.query(Template).filter_by(name=name).first()
    
    def get_by_type(self, template_type: str, db: Session) -> Optional[Template]:
        """Получить шаблон по типу (с кэшем)"""
        cache_key = f"template:type:{template_type}"
        
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        template = db.query(Template).filter_by(
            template_type=template_type,
            is_active=True
        ).first()
        if template:
            self.cache.set(cache_key, template, ttl=600)
        
        return template
    
    def create(self, template_data: Dict, db: Session) -> Template:
        """Создать шаблон"""
        template = Template(**template_data)
        db.add(template)
        db.commit()
        db.refresh(template)
        
        # Инвалидировать кэш списка
        self.cache.delete("templates:all")
        
        logger.info(f"Создан шаблон: {template.name}")
        return template
    
    def update(self, template_id: int, template_data: Dict, db: Session) -> Optional[Template]:
        """Обновить шаблон"""
        template = db.query(Template).filter_by(id=template_id).first()
        if not template:
            return None
        
        for key, value in template_data.items():
            setattr(template, key, value)
        
        db.commit()
        db.refresh(template)
        
        # Инвалидировать кэш
        invalidate_cache_for_entity("template", template_id)
        
        logger.info(f"Обновлён шаблон: {template.name}")
        return template
    
    def delete(self, template_id: int, db: Session) -> bool:
        """Удалить (деактивировать) шаблон"""
        template = db.query(Template).filter_by(id=template_id).first()
        if not template:
            return False
        
        template.is_active = False
        db.commit()
        
        # Инвалидировать кэш
        invalidate_cache_for_entity("template", template_id)
        
        logger.info(f"Деактивирован шаблон: {template.name}")
        return True
    
    def render(self, template: Template, variables: Dict) -> Dict[str, str]:
        """
        Отрендерить шаблон с переменными
        
        Args:
            template: Шаблон
            variables: Переменные для подстановки
        
        Returns:
            {"subject": "...", "body": "..."}
        """
        subject = template.subject or ""
        body = template.body_plain or template.body_html or ""
        
        for key, value in variables.items():
            placeholder = f"{{{{{key}}}}}"
            subject = subject.replace(placeholder, str(value))
            body = body.replace(placeholder, str(value))
        
        return {
            "subject": subject,
            "body": body
        }
