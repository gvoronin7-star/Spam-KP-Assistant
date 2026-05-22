"""
Тесты сервиса рассылок (MailingService)
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, AsyncMock
from core.models import Profile


class TestMailingServiceCRUD:
    """Тесты CRUD операций MailingService"""
    
    @pytest.fixture(autouse=True)
    def mock_session_local(self, test_db):
        """Подмена SessionLocal на фабрику сессий для test_db"""
        from sqlalchemy.orm import sessionmaker
        engine = test_db.bind
        Session = sessionmaker(bind=engine)
        with patch('services.mailing_service.SessionLocal', side_effect=Session):
            yield
    
    def test_create_mailing(self, test_db, test_profile, test_contact, test_template):
        """Создание рассылки"""
        from services.mailing_service import MailingService
        from core.models import SMTPAccount
        from utils.encryption import encryption
        
        # Создать SMTP аккаунт
        smtp = SMTPAccount(
            name="Test SMTP",
            email="test@example.com",
            smtp_host="smtp.example.com",
            smtp_port=587,
            smtp_use_tls=True,
            imap_host="imap.example.com",
            imap_port=993,
            password_enc=encryption.encrypt("password123"),
            is_active=True
        )
        test_db.add(smtp)
        test_db.commit()
        
        service = MailingService()
        mailing_id = service.create_mailing(
            name="Тестовая рассылка",
            profile_id=test_profile.id,
            template_id=test_template.id,
            contact_ids=[test_contact.id],
            smtp_account_id=smtp.id,
            delay_min=5,
            delay_max=10,
            hourly_limit=50,
            daily_limit=200
        )
        
        assert mailing_id is not None
        
        mailing_info = service.get_mailing(mailing_id)
        assert mailing_info["name"] == "Тестовая рассылка"
        assert mailing_info["status"] == "draft"
        assert mailing_info["total_recipients"] == 1
    
    def test_get_mailings(self, test_db, test_profile, test_contact, test_template):
        """Получение списка рассылок"""
        from services.mailing_service import MailingService
        from core.models import SMTPAccount
        from utils.encryption import encryption
        
        smtp = SMTPAccount(
            name="Test SMTP",
            email="test@example.com",
            smtp_host="smtp.example.com",
            smtp_port=587,
            password_enc=encryption.encrypt("password123"),
            is_active=True
        )
        test_db.add(smtp)
        test_db.commit()
        
        service = MailingService()
        
        # Создать несколько рассылок
        for i in range(3):
            service.create_mailing(
                name=f"Рассылка {i}",
                profile_id=test_profile.id,
                template_id=test_template.id,
                contact_ids=[test_contact.id],
                smtp_account_id=smtp.id
            )
        
        mailings = service.get_mailings()
        assert len(mailings) == 3
        # Проверяем, что все три рассылки присутствуют (порядок может быть любым из-за func.now())
        names = [m["name"] for m in mailings]
        assert "Рассылка 0" in names
        assert "Рассылка 1" in names
        assert "Рассылка 2" in names
    
    def test_get_mailings_by_status(self, test_db, test_profile, test_contact, test_template):
        """Фильтрация рассылок по статусу"""
        from services.mailing_service import MailingService
        from core.models import SMTPAccount, Mailing
        from utils.encryption import encryption
        
        smtp = SMTPAccount(
            name="Test SMTP",
            email="test@example.com",
            smtp_host="smtp.example.com",
            smtp_port=587,
            password_enc=encryption.encrypt("password123"),
            is_active=True
        )
        test_db.add(smtp)
        test_db.commit()
        
        service = MailingService()
        mailing_id = service.create_mailing(
            name="Тест",
            profile_id=test_profile.id,
            template_id=test_template.id,
            contact_ids=[test_contact.id],
            smtp_account_id=smtp.id
        )
        
        # Обновить статус вручную
        mailing = test_db.query(Mailing).filter_by(id=mailing_id).first()
        mailing.status = "sending"
        test_db.commit()
        
        mailings = service.get_mailings(status="sending")
        assert len(mailings) == 1
        assert mailings[0]["status"] == "sending"
    
    def test_update_mailing(self, test_db, test_profile, test_contact, test_template):
        """Обновление рассылки"""
        from services.mailing_service import MailingService
        from core.models import SMTPAccount
        from utils.encryption import encryption
        
        smtp = SMTPAccount(
            name="Test SMTP",
            email="test@example.com",
            smtp_host="smtp.example.com",
            smtp_port=587,
            password_enc=encryption.encrypt("password123"),
            is_active=True
        )
        test_db.add(smtp)
        test_db.commit()
        
        service = MailingService()
        mailing_id = service.create_mailing(
            name="Тест",
            profile_id=test_profile.id,
            template_id=test_template.id,
            contact_ids=[test_contact.id],
            smtp_account_id=smtp.id
        )
        
        # Обновить в статусе draft
        result = service.update_mailing(mailing_id, name="Обновлённое название")
        assert result is True
        
        mailing_info = service.get_mailing(mailing_id)
        assert mailing_info["name"] == "Обновлённое название"
    
    def test_update_mailing_not_draft(self, test_db, test_profile, test_contact, test_template):
        """Обновление рассылки не в статусе draft"""
        from services.mailing_service import MailingService
        from core.models import SMTPAccount, Mailing
        from utils.encryption import encryption
        
        smtp = SMTPAccount(
            name="Test SMTP",
            email="test@example.com",
            smtp_host="smtp.example.com",
            smtp_port=587,
            password_enc=encryption.encrypt("password123"),
            is_active=True
        )
        test_db.add(smtp)
        test_db.commit()
        
        service = MailingService()
        mailing_id = service.create_mailing(
            name="Тест",
            profile_id=test_profile.id,
            template_id=test_template.id,
            contact_ids=[test_contact.id],
            smtp_account_id=smtp.id
        )
        
        # Изменить статус
        mailing = test_db.query(Mailing).filter_by(id=mailing_id).first()
        mailing.status = "sending"
        test_db.commit()
        
        # Попытка обновления
        result = service.update_mailing(mailing_id, name="Новое название")
        assert result is False
    
    def test_delete_mailing(self, test_db, test_profile, test_contact, test_template):
        """Удаление рассылки"""
        from services.mailing_service import MailingService
        from core.models import SMTPAccount
        from utils.encryption import encryption
        
        smtp = SMTPAccount(
            name="Test SMTP",
            email="test@example.com",
            smtp_host="smtp.example.com",
            smtp_port=587,
            password_enc=encryption.encrypt("password123"),
            is_active=True
        )
        test_db.add(smtp)
        test_db.commit()
        
        service = MailingService()
        mailing_id = service.create_mailing(
            name="Тест",
            profile_id=test_profile.id,
            template_id=test_template.id,
            contact_ids=[test_contact.id],
            smtp_account_id=smtp.id
        )
        
        result = service.delete_mailing(mailing_id)
        assert result is True
        
        mailing_info = service.get_mailing(mailing_id)
        assert mailing_info is None


class TestMailingServiceCallbacks:
    """Тесты callback'ов MailingService"""
    
    @pytest.fixture(autouse=True)
    def mock_session_local(self, test_db):
        from sqlalchemy.orm import sessionmaker
        engine = test_db.bind
        Session = sessionmaker(bind=engine)
        with patch('services.mailing_service.SessionLocal', side_effect=Session):
            yield
    
    def test_callbacks_initialization(self):
        """Проверка инициализации callback'ов"""
        from services.mailing_service import MailingService
        
        service = MailingService()
        
        assert service.on_progress is None
        assert service.on_recipient is None
        assert service.on_log is None
        assert service.on_finished is None
    
    def test_callbacks_assignment(self):
        """Назначение callback'ов"""
        from services.mailing_service import MailingService
        
        service = MailingService()
        
        progress_called = []
        recipient_called = []
        log_called = []
        finished_called = []
        
        service.on_progress = lambda s, t, e: progress_called.append((s, t, e))
        service.on_recipient = lambda em, su, msg: recipient_called.append((em, su, msg))
        service.on_log = lambda msg: log_called.append(msg)
        service.on_finished = lambda su, msg: finished_called.append((su, msg))
        
        # Вызвать callback'и вручную
        service.on_progress(10, 100, 0)
        service.on_recipient("test@example.com", True, "Отправлено")
        service.on_log("Тестовое сообщение")
        service.on_finished(True, "Завершено")
        
        assert len(progress_called) == 1
        assert progress_called[0] == (10, 100, 0)
        
        assert len(recipient_called) == 1
        assert recipient_called[0] == ("test@example.com", True, "Отправлено")
        
        assert len(log_called) == 1
        assert log_called[0] == "Тестовое сообщение"
        
        assert len(finished_called) == 1
        assert finished_called[0] == (True, "Завершено")


class TestMailingServiceStatistics:
    """Тесты статистики рассылок"""
    
    @pytest.fixture(autouse=True)
    def mock_session_local(self, test_db):
        from sqlalchemy.orm import sessionmaker
        engine = test_db.bind
        Session = sessionmaker(bind=engine)
        with patch('services.mailing_service.SessionLocal', side_effect=Session):
            yield
    
    def test_get_statistics(self, test_db, test_profile, test_contact, test_template):
        """Получение статистики рассылки"""
        from services.mailing_service import MailingService
        from core.models import SMTPAccount, MailingRecipient
        from utils.encryption import encryption
        
        smtp = SMTPAccount(
            name="Test SMTP",
            email="test@example.com",
            smtp_host="smtp.example.com",
            smtp_port=587,
            password_enc=encryption.encrypt("password123"),
            is_active=True
        )
        test_db.add(smtp)
        test_db.commit()
        
        service = MailingService()
        mailing_id = service.create_mailing(
            name="Тест",
            profile_id=test_profile.id,
            template_id=test_template.id,
            contact_ids=[test_contact.id],
            smtp_account_id=smtp.id
        )
        
        stats = service.get_statistics(mailing_id)
        
        assert stats["mailing_id"] == mailing_id
        assert stats["name"] == "Тест"
        assert stats["status"] == "draft"
        assert stats["total"] == 1
        assert stats["sent"] == 0
        assert stats["errors"] == 0
        assert stats["pending"] == 1
        assert stats["progress_percent"] == 0.0
    
    def test_get_statistics_with_sent(self, test_db, test_profile, test_contact, test_template):
        """Статистика с отправленными письмами"""
        from services.mailing_service import MailingService
        from core.models import SMTPAccount, MailingRecipient
        from utils.encryption import encryption
        
        smtp = SMTPAccount(
            name="Test SMTP",
            email="test@example.com",
            smtp_host="smtp.example.com",
            smtp_port=587,
            password_enc=encryption.encrypt("password123"),
            is_active=True
        )
        test_db.add(smtp)
        test_db.commit()
        
        service = MailingService()
        mailing_id = service.create_mailing(
            name="Тест",
            profile_id=test_profile.id,
            template_id=test_template.id,
            contact_ids=[test_contact.id],
            smtp_account_id=smtp.id
        )
        
        # Отметить получателя как отправленного через сервис
        recipient = test_db.query(MailingRecipient).filter_by(mailing_id=mailing_id).first()
        service._mark_sent(recipient.id, "test-message-id")
        service._update_mailing_progress(mailing_id)
        
        stats = service.get_statistics(mailing_id)
        
        assert stats["sent"] == 1
        assert stats["pending"] == 0
        assert stats["progress_percent"] == 100.0


class TestMailingServiceSendLoop:
    """Тесты цикла отправки (с моками)"""
    
    @pytest.fixture(autouse=True)
    def mock_session_local(self, test_db):
        from sqlalchemy.orm import sessionmaker
        engine = test_db.bind
        Session = sessionmaker(bind=engine)
        with patch('services.mailing_service.SessionLocal', side_effect=Session):
            yield
    
    @pytest.mark.asyncio
    async def test_start_mailing_draft_status(self, test_db, test_profile, test_contact, test_template):
        """Запуск рассылки в статусе draft"""
        from services.mailing_service import MailingService
        from core.models import SMTPAccount, Mailing
        from utils.encryption import encryption
        
        smtp = SMTPAccount(
            name="Test SMTP",
            email="test@example.com",
            smtp_host="smtp.example.com",
            smtp_port=587,
            password_enc=encryption.encrypt("password123"),
            is_active=True
        )
        test_db.add(smtp)
        test_db.commit()
        
        service = MailingService()
        mailing_id = service.create_mailing(
            name="Тест",
            profile_id=test_profile.id,
            template_id=test_template.id,
            contact_ids=[test_contact.id],
            smtp_account_id=smtp.id
        )
        
        # Запустить рассылку (с моком email_service.send_email)
        with patch('services.mailing_service.EmailService') as MockEmailService:
            mock_service = MagicMock()
            mock_service.send_email.return_value = True
            MockEmailService.return_value = mock_service
            
            result = await service.start_mailing(mailing_id)
            
            # start_mailing блокирует до завершения, но т.к. мы замокали send_email,
            # цикл завершится быстро
            assert result is True
        
        # Проверить, что статус изменился
        mailing = test_db.query(Mailing).filter_by(id=mailing_id).first()
        assert mailing.status == "completed"
    
    @pytest.mark.asyncio
    async def test_start_mailing_missing_data(self, test_db):
        """Запуск рассылки с отсутствующими данными"""
        from services.mailing_service import MailingService
        
        service = MailingService()
        
        # Попытка запустить несуществующую рассылку
        with patch('services.mailing_service.EmailService') as MockEmailService:
            mock_service = MagicMock()
            MockEmailService.return_value = mock_service
            
            result = await service.start_mailing(999)
            
            assert result is False
    
    def test_pause_mailing(self, test_db, test_profile, test_contact, test_template):
        """Приостановка рассылки"""
        from services.mailing_service import MailingService
        from core.models import SMTPAccount, Mailing
        from utils.encryption import encryption
        
        smtp = SMTPAccount(
            name="Test SMTP",
            email="test@example.com",
            smtp_host="smtp.example.com",
            smtp_port=587,
            password_enc=encryption.encrypt("password123"),
            is_active=True
        )
        test_db.add(smtp)
        test_db.commit()
        
        service = MailingService()
        mailing_id = service.create_mailing(
            name="Тест",
            profile_id=test_profile.id,
            template_id=test_template.id,
            contact_ids=[test_contact.id],
            smtp_account_id=smtp.id
        )
        
        # Запустить рассылку, чтобы установить _current_mailing_id
        # В реальном сценарии это делает start_mailing, но для теста установим вручную
        service._current_mailing_id = mailing_id
        
        result = service.pause_mailing(mailing_id)
        assert result is True
        assert service._paused is True
        
        mailing = test_db.query(Mailing).filter_by(id=mailing_id).first()
        assert mailing.status == "paused"
    
    def test_cancel_mailing(self, test_db, test_profile, test_contact, test_template):
        """Отмена рассылки"""
        from services.mailing_service import MailingService
        from core.models import SMTPAccount, Mailing
        from utils.encryption import encryption
        
        smtp = SMTPAccount(
            name="Test SMTP",
            email="test@example.com",
            smtp_host="smtp.example.com",
            smtp_port=587,
            password_enc=encryption.encrypt("password123"),
            is_active=True
        )
        test_db.add(smtp)
        test_db.commit()
        
        service = MailingService()
        mailing_id = service.create_mailing(
            name="Тест",
            profile_id=test_profile.id,
            template_id=test_template.id,
            contact_ids=[test_contact.id],
            smtp_account_id=smtp.id
        )
        
        result = service.cancel_mailing(mailing_id)
        assert result is True
        assert service._current_mailing_id is None
        
        mailing = test_db.query(Mailing).filter_by(id=mailing_id).first()
        assert mailing.status == "cancelled"


class TestMailingServiceComposeEmail:
    """Тесты генерации писем"""
    
    @pytest.fixture(autouse=True)
    def mock_session_local(self, test_db):
        from sqlalchemy.orm import sessionmaker
        engine = test_db.bind
        Session = sessionmaker(bind=engine)
        with patch('services.mailing_service.SessionLocal', side_effect=Session):
            yield
    
    def test_compose_email_variable_substitution(self, test_db, test_profile, test_contact, test_template):
        """Подстановка переменных в письмо"""
        from services.mailing_service import MailingService
        from core.models import SMTPAccount, Mailing, MailingRecipient, Template
        from utils.encryption import encryption
        
        smtp = SMTPAccount(
            name="Test SMTP",
            email="test@example.com",
            smtp_host="smtp.example.com",
            smtp_port=587,
            password_enc=encryption.encrypt("password123"),
            is_active=True
        )
        test_db.add(smtp)
        test_db.commit()
        
        # Шаблон с переменными
        template = Template(
            name="Шаблон с переменными",
            template_type="initial",
            subject="Запрос КП для {{ company }}",
            body_plain="Уважаемый {{ contact_person }}! Просим КП на {{ service_name }}.",
            body_html="<html><body>Уважаемый {{ contact_person }}!</body></html>",
            is_active=True
        )
        test_db.add(template)
        test_db.commit()
        
        service = MailingService()
        mailing_id = service.create_mailing(
            name="Тест",
            profile_id=test_profile.id,
            template_id=template.id,
            contact_ids=[test_contact.id],
            smtp_account_id=smtp.id
        )
        
        mailing = test_db.query(Mailing).filter_by(id=mailing_id).first()
        recipient = test_db.query(MailingRecipient).filter_by(mailing_id=mailing_id).first()
        profile = test_db.query(Profile).filter_by(id=test_profile.id).first()
        tmpl = test_db.query(Template).filter_by(id=template.id).first()
        
        email_data = service._compose_email(profile, tmpl, recipient, test_db)
        
        assert email_data["subject"] == "Запрос КП для Тестовая компания"
        assert "Уважаемый Иван Тестов!" in email_data["body_plain"]
        assert "Тестовый профиль" in email_data["body_plain"]
