"""
Сервис аудита — логирование действий пользователя и системы
"""
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from loguru import logger

from core.models import AuditLog


class AuditService:
    """
    Сервис аудита для отслеживания действий
    
    Примеры использования:
        audit.log_action("create", "dialogue", dialogue_id, new_values={"status": "sent"})
        audit.log_action("send", "message", message_id, description="Письмо отправлено")
        audit.log_action("classify", "message", message_id, new_values={"category": "kp"})
    """
    
    def __init__(self, db: Optional[Session] = None):
        self.db = db
        self._pending_logs: list = []
    
    def log_action(
        self,
        action: str,
        entity_type: str,
        entity_id: Optional[int] = None,
        description: Optional[str] = None,
        old_values: Optional[Dict] = None,
        new_values: Optional[Dict] = None,
        actor_type: str = "system",
        actor_id: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        db: Optional[Session] = None
    ) -> Optional[AuditLog]:
        """
        Записать действие в аудит-лог
        
        Args:
            action: Действие (create, update, delete, send, classify, etc.)
            entity_type: Тип сущности (dialogue, message, task, mailing, contact)
            entity_id: ID сущности
            description: Описание действия
            old_values: Предыдущие значения (для update)
            new_values: Новые значения
            actor_type: Тип актора (system, user, llm, scheduler)
            actor_id: ID актора
            success: Успешно ли выполнено
            error_message: Сообщение об ошибке
            db: Сессия БД (если не задана в конструкторе)
        
        Returns:
            Созданная запись AuditLog или None
        """
        session = db or self.db
        if not session:
            # Отложенная запись — сохраним для batch insert
            self._pending_logs.append({
                "action": action,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "description": description,
                "old_values": old_values,
                "new_values": new_values,
                "actor_type": actor_type,
                "actor_id": actor_id,
                "success": success,
                "error_message": error_message
            })
            return None
        
        try:
            log = AuditLog(
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                description=description,
                old_values=old_values or {},
                new_values=new_values or {},
                actor_type=actor_type,
                actor_id=actor_id,
                success=success,
                error_message=error_message
            )
            
            session.add(log)
            session.commit()
            
            logger.debug(
                f"Audit: {actor_type} {action} {entity_type}#{entity_id}"
            )
            
            return log
        
        except Exception as e:
            logger.error(f"Ошибка записи audit log: {e}")
            session.rollback()
            return None
    
    def log_create(self, entity_type: str, entity_id: int, new_values: Dict, **kwargs):
        """Сокращение для логирования создания"""
        return self.log_action(
            action="create",
            entity_type=entity_type,
            entity_id=entity_id,
            new_values=new_values,
            **kwargs
        )
    
    def log_update(self, entity_type: str, entity_id: int, old_values: Dict, new_values: Dict, **kwargs):
        """Сокращение для логирования обновления"""
        return self.log_action(
            action="update",
            entity_type=entity_type,
            entity_id=entity_id,
            old_values=old_values,
            new_values=new_values,
            **kwargs
        )
    
    def log_delete(self, entity_type: str, entity_id: int, old_values: Dict, **kwargs):
        """Сокращение для логирования удаления"""
        return self.log_action(
            action="delete",
            entity_type=entity_type,
            entity_id=entity_id,
            old_values=old_values,
            **kwargs
        )
    
    def log_send(self, entity_type: str, entity_id: int, description: str, **kwargs):
        """Сокращение для логирования отправки"""
        return self.log_action(
            action="send",
            entity_type=entity_type,
            entity_id=entity_id,
            description=description,
            **kwargs
        )
    
    def log_classify(self, entity_type: str, entity_id: int, new_values: Dict, **kwargs):
        """Сокращение для логирования классификации"""
        return self.log_action(
            action="classify",
            entity_type=entity_type,
            entity_id=entity_id,
            new_values=new_values,
            **kwargs
        )
    
    def flush_pending(self, db: Optional[Session] = None):
        """Сохранить все отложенные логи"""
        session = db or self.db
        if not session:
            logger.warning("Нет сессии БД для сохранения audit logs")
            return
        
        for log_data in self._pending_logs:
            try:
                log = AuditLog(**log_data)
                session.add(log)
            except Exception as e:
                logger.error(f"Ошибка создания audit log: {e}")
        
        try:
            session.commit()
            count = len(self._pending_logs)
            self._pending_logs.clear()
            logger.info(f"Сохранено {count} audit logs")
        except Exception as e:
            logger.error(f"Ошибка batch insert audit logs: {e}")
            session.rollback()
    
    def get_logs(
        self,
        db: Session,
        entity_type: Optional[str] = None,
        entity_id: Optional[int] = None,
        action: Optional[str] = None,
        actor_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ):
        """
        Получить audit logs с фильтрацией
        
        Returns:
            Список AuditLog
        """
        query = db.query(AuditLog).order_by(AuditLog.created_at.desc())
        
        if entity_type:
            query = query.filter(AuditLog.entity_type == entity_type)
        if entity_id:
            query = query.filter(AuditLog.entity_id == entity_id)
        if action:
            query = query.filter(AuditLog.action == action)
        if actor_type:
            query = query.filter(AuditLog.actor_type == actor_type)
        
        return query.offset(offset).limit(limit).all()
    
    def get_entity_history(self, db: Session, entity_type: str, entity_id: int):
        """Получить полную историю изменений сущности"""
        return db.query(AuditLog).filter(
            AuditLog.entity_type == entity_type,
            AuditLog.entity_id == entity_id
        ).order_by(AuditLog.created_at.asc()).all()
