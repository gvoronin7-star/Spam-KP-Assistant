"""
Тесты для services/audit_service.py
"""
import pytest

from services.audit_service import AuditService
from core.models import AuditLog


class TestAuditService:
    """Тесты AuditService"""
    
    def test_log_action(self, test_db):
        """Базовое логирование действия"""
        audit = AuditService(test_db)
        
        log = audit.log_action(
            action="create",
            entity_type="dialogue",
            entity_id=1,
            description="Создан диалог",
            new_values={"status": "sent"},
            actor_type="user",
            actor_id="admin"
        )
        
        assert log is not None
        assert log.action == "create"
        assert log.entity_type == "dialogue"
        assert log.entity_id == 1
        assert log.new_values["status"] == "sent"
        assert log.actor_type == "user"
        assert log.actor_id == "admin"
    
    def test_log_create_shortcut(self, test_db):
        """Сокращение log_create"""
        audit = AuditService(test_db)
        
        log = audit.log_create(
            entity_type="contact",
            entity_id=2,
            new_values={"email": "test@example.com"}
        )
        
        assert log is not None
        assert log.action == "create"
        assert log.entity_type == "contact"
    
    def test_log_update_shortcut(self, test_db):
        """Сокращение log_update"""
        audit = AuditService(test_db)
        
        log = audit.log_update(
            entity_type="dialogue",
            entity_id=1,
            old_values={"status": "sent"},
            new_values={"status": "kp_received"}
        )
        
        assert log is not None
        assert log.action == "update"
        assert log.old_values["status"] == "sent"
        assert log.new_values["status"] == "kp_received"
    
    def test_log_without_db(self):
        """Логирование без БД — отложенная запись"""
        audit = AuditService()
        
        log = audit.log_action(
            action="delete",
            entity_type="task",
            entity_id=5
        )
        
        assert log is None  # Нет сессии — отложено
        assert len(audit._pending_logs) == 1
    
    def test_flush_pending(self, test_db):
        """Сохранение отложенных логов"""
        audit = AuditService()
        
        audit.log_action(action="create", entity_type="dialogue", entity_id=1)
        audit.log_action(action="update", entity_type="dialogue", entity_id=1)
        
        assert len(audit._pending_logs) == 2
        
        audit.flush_pending(test_db)
        
        assert len(audit._pending_logs) == 0
        
        # Проверить в БД
        logs = test_db.query(AuditLog).all()
        assert len(logs) == 2
    
    def test_get_logs(self, test_db):
        """Получение логов с фильтрацией"""
        audit = AuditService(test_db)
        
        audit.log_action("create", "dialogue", 1)
        audit.log_action("update", "dialogue", 1)
        audit.log_action("create", "message", 10)
        
        # Фильтр по entity_type
        dialogue_logs = audit.get_logs(test_db, entity_type="dialogue")
        assert len(dialogue_logs) == 2
        
        # Фильтр по action
        create_logs = audit.get_logs(test_db, action="create")
        assert len(create_logs) == 2
        
        # Фильтр по entity_id
        specific_logs = audit.get_logs(test_db, entity_id=1)
        assert len(specific_logs) == 2
    
    def test_get_entity_history(self, test_db):
        """История изменений сущности"""
        audit = AuditService(test_db)
        
        audit.log_create("dialogue", 1, {"status": "new"})
        audit.log_update("dialogue", 1, {"status": "new"}, {"status": "sent"})
        audit.log_update("dialogue", 1, {"status": "sent"}, {"status": "kp_received"})
        
        history = audit.get_entity_history(test_db, "dialogue", 1)
        
        assert len(history) == 3
        assert history[0].action == "create"
        assert history[1].action == "update"
        assert history[2].action == "update"
    
    def test_error_handling(self, test_db):
        """Обработка ошибок — логирование без db возвращает None"""
        audit = AuditService()  # Без db
        
        log = audit.log_action("create", "dialogue", 1)
        assert log is None  # Отложенная запись, без db
