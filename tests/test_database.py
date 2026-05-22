"""
Тесты базы данных
"""
import pytest
from datetime import datetime


class TestProfileModel:
    """Тесты модели Profile"""
    
    def test_create_profile(self, test_db):
        """Создание профиля"""
        from core.models import Profile
        
        profile = Profile(
            name="Тест",
            description="Описание"
        )
        
        test_db.add(profile)
        test_db.commit()
        
        assert profile.id is not None
        assert profile.name == "Тест"
        assert profile.is_active is True
    
    def test_profile_tech_params(self, test_profile):
        """Технические параметры профиля"""
        assert test_profile.tech_params is not None
        assert isinstance(test_profile.tech_params, dict)
    
    def test_profile_relations(self, test_db, test_profile, test_contact):
        """Связи профиля с контактами"""
        test_contact.profile_id = test_profile.id
        test_db.commit()
        
        test_db.refresh(test_profile)
        assert len(test_profile.contacts) == 1


class TestContactModel:
    """Тесты модели Contact"""
    
    def test_create_contact(self, test_db):
        """Создание контакта"""
        from core.models import Contact
        
        contact = Contact(
            email="test@example.com",
            company_name="Test Company"
        )
        
        test_db.add(contact)
        test_db.commit()
        
        assert contact.id is not None
        assert contact.email == "test@example.com"
    
    def test_contact_email_unique(self, test_db):
        """Уникальность email"""
        from core.models import Contact
        from sqlalchemy.exc import IntegrityError
        
        contact1 = Contact(email="unique@test.com")
        
        test_db.add(contact1)
        test_db.commit()
        
        # Пробуем добавить дубликат — должно быть исключение
        contact2 = Contact(email="unique@test.com")
        test_db.add(contact2)
        
        with pytest.raises(IntegrityError):
            test_db.flush()
    
    def test_contact_validation(self, test_db):
        """Валидация email"""
        from core.models import Contact
        
        # Невалидный email
        contact = Contact(email="invalid-email")
        test_db.add(contact)
        test_db.commit()
        
        # Валидный email
        contact2 = Contact(email="valid@test.com")
        test_db.add(contact2)
        test_db.commit()
        
        assert contact2.email == "valid@test.com"


class TestTemplateModel:
    """Тесты модели Template"""
    
    def test_create_template(self, test_db):
        """Создание шаблона"""
        from core.models import Template
        
        template = Template(
            name="Test Template",
            template_type="initial",
            subject="Test Subject",
            body_plain="Test body",
            body_html="<html>Test</html>"
        )
        
        test_db.add(template)
        test_db.commit()
        
        assert template.version == 1
        assert template.is_active is True
    
    def test_template_versioning(self, test_template, test_db):
        """Версионирование шаблонов"""
        from core.models import Template
        
        # Создаём новую версию
        new_version = Template(
            name=test_template.name,
            template_type=test_template.template_type,
            subject="Updated Subject",
            body_plain="Updated body",
            body_html="<html>Updated</html>",
            version=test_template.version + 1
        )
        
        test_template.is_active = False
        test_db.add(new_version)
        test_db.commit()
        
        assert new_version.version == 2


class TestDialogueModel:
    """Тесты модели Dialogue"""
    
    def test_create_dialogue(self, test_dialogue):
        """Создание диалога"""
        assert test_dialogue.status == "sent"
        assert test_dialogue.kp_received is False
    
    def test_dialogue_status_change(self, test_dialogue, test_db):
        """Смена статуса диалога"""
        test_dialogue.status = "clarifying"
        test_db.commit()
        
        test_db.refresh(test_dialogue)
        assert test_dialogue.status == "clarifying"


class TestMessageModel:
    """Тесты модели Message"""
    
    def test_create_message(self, test_db, test_dialogue):
        """Создание сообщения"""
        from core.models import Message
        
        message = Message(
            dialogue_id=test_dialogue.id,
            direction="outbound",
            subject="Test",
            body_plain="Test body",
            from_address="sender@test.com",
            to_address="receiver@test.com"
        )
        
        test_db.add(message)
        test_db.commit()
        
        assert message.id is not None
        assert message.generated_by_llm is False
    
    def test_message_llm_flag(self, test_db, test_dialogue):
        """Флаг генерации через LLM"""
        from core.models import Message
        
        message = Message(
            dialogue_id=test_dialogue.id,
            direction="outbound",
            subject="LLM generated",
            body_plain="Generated by LLM",
            generated_by_llm=True,
            llm_model="gpt-5.4-mini"
        )
        
        test_db.add(message)
        test_db.commit()
        
        assert message.generated_by_llm is True
        assert message.llm_model == "gpt-5.4-mini"


class TestTaskModel:
    """Тесты модели Task"""
    
    def test_create_task(self, test_db, test_dialogue):
        """Создание задачи"""
        from core.models import Task
        
        task = Task(
            task_type="requires_response",
            title="Требуется ответ",
            description="Нужно ответить на вопрос",
            dialogue_id=test_dialogue.id,
            priority="high"
        )
        
        test_db.add(task)
        test_db.commit()
        
        assert task.is_completed is False
        assert task.completed_at is None
    
    def test_complete_task(self, test_db, test_dialogue):
        """Завершение задачи"""
        from core.models import Task
        
        task = Task(
            task_type="requires_response",
            title="Test Task",
            dialogue_id=test_dialogue.id
        )
        
        test_db.add(task)
        test_db.commit()
        
        task.is_completed = True
        task.completed_at = datetime.utcnow()
        test_db.commit()
        
        test_db.refresh(task)
        assert task.is_completed is True
        assert task.completed_at is not None
