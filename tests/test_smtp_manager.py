"""
Тесты SMTP менеджера
"""
import pytest
from unittest.mock import patch


@pytest.fixture(autouse=True)
def mock_smtp_session_local(test_db):
    """Подмена SessionLocal для SMTPManager"""
    from sqlalchemy.orm import sessionmaker
    engine = test_db.bind
    Session = sessionmaker(bind=engine)
    with patch('core.database.SessionLocal', side_effect=Session):
        yield


class TestSMTPConnection:
    """Тесты SMTP подключения"""
    
    def test_smtp_connection_valid(self):
        """Тестирование SMTP (заглушка)"""
        from services.smtp_manager import SMTPManager
        
        manager = SMTPManager()
        
        # Тест с невалидными данными должен вернуть ошибку
        success, msg = manager.test_smtp_connection(
            smtp_host="invalid.smtp.server",
            smtp_port=465,
            email="test@example.com",
            password="wrong_password"
        )
        
        assert success is False
        assert "Ошибка" in msg or "Не удалось" in msg
    
    def test_smtp_tls(self):
        """SMTP с TLS"""
        from services.smtp_manager import SMTPManager
        
        manager = SMTPManager()
        
        # Проверяем, что метод принимает параметр use_tls
        success, msg = manager.test_smtp_connection(
            smtp_host="smtp.gmail.com",
            smtp_port=465,
            email="test@gmail.com",
            password="test",
            use_tls=True
        )
        
        # Ожидается ошибка аутентификации, не подключения
        assert "Не удалось подключиться" not in msg


class TestIMAPConnection:
    """Тесты IMAP подключения"""
    
    def test_imap_connection_valid(self):
        """Тестирование IMAP (заглушка)"""
        from services.smtp_manager import SMTPManager
        
        manager = SMTPManager()
        
        success, msg = manager.test_imap_connection(
            imap_host="invalid.imap.server",
            imap_port=993,
            email="test@example.com",
            password="wrong"
        )
        
        assert success is False


class TestAccountManagement:
    """Тесты управления аккаунтами"""
    
    def test_save_account(self, test_db):
        """Сохранение аккаунта"""
        from services.smtp_manager import SMTPManager
        
        manager = SMTPManager()
        
        account_id = manager.save_account(
            name="Test Account",
            email="test@example.com",
            smtp_host="smtp.test.com",
            smtp_port=465,
            imap_host="imap.test.com",
            imap_port=993,
            login="test@test.com",
            password="secret_password",
            use_tls=True,
            use_ssl=True,
            is_primary=True
        )
        
        assert account_id is not None
    
    def test_save_account_encryption(self, test_db):
        """Шифрование пароля при сохранении"""
        from services.smtp_manager import SMTPManager
        from core.database import SessionLocal
        from core.models import SMTPAccount
        
        manager = SMTPManager()
        
        account_id = manager.save_account(
            name="Encrypted Account",
            email="encrypted@test.com",
            smtp_host="smtp.test.com",
            smtp_port=465,
            imap_host="imap.test.com",
            imap_port=993,
            login="test@test.com",
            password="my_secret_password",
            is_primary=True
        )
        
        # Проверяем, что пароль зашифрован в БД
        db = SessionLocal()
        account = db.query(SMTPAccount).get(account_id)
        db.close()
        
        assert account.password_enc != "my_secret_password"
        assert len(account.password_enc) > 50  # Зашифрованная строка длиннее
    
    def test_get_accounts(self, test_db):
        """Получение списка аккаунтов"""
        from services.smtp_manager import SMTPManager
        
        manager = SMTPManager()
        
        # Создаём несколько аккаунтов
        manager.save_account(
            name="Account 1",
            email="a1@test.com",
            smtp_host="smtp1.test.com",
            smtp_port=465,
            imap_host="imap1.test.com",
            imap_port=993,
            login="a1@test.com",
            password="pass1"
        )
        
        manager.save_account(
            name="Account 2",
            email="a2@test.com",
            smtp_host="smtp2.test.com",
            smtp_port=465,
            imap_host="imap2.test.com",
            imap_port=993,
            login="a2@test.com",
            password="pass2"
        )
        
        accounts = manager.get_accounts()
        
        assert len(accounts) == 2
    
    def test_primary_account(self, test_db):
        """Основной аккаунт"""
        from services.smtp_manager import SMTPManager
        
        manager = SMTPManager()
        
        # Создаём аккаунты
        manager.save_account(
            name="Primary",
            email="primary@test.com",
            smtp_host="smtp.test.com",
            smtp_port=465,
            imap_host="imap.test.com",
            imap_port=993,
            login="primary@test.com",
            password="pass1",
            is_primary=True
        )
        
        manager.save_account(
            name="Secondary",
            email="secondary@test.com",
            smtp_host="smtp.test.com",
            smtp_port=465,
            imap_host="imap.test.com",
            imap_port=993,
            login="secondary@test.com",
            password="pass2",
            is_primary=False
        )
        
        primary = manager.get_primary_account()
        
        assert primary is not None
        assert primary["email"] == "primary@test.com"


class TestFullConnection:
    """Тесты полного подключения"""
    
    def test_full_connection(self):
        """Полное тестирование SMTP + IMAP"""
        from services.smtp_manager import SMTPManager
        
        manager = SMTPManager()
        
        result = manager.test_full_connection(
            smtp_host="invalid.smtp.server",
            smtp_port=465,
            imap_host="invalid.imap.server",
            imap_port=993,
            email="test@example.com",
            password="wrong"
        )
        
        assert result["overall_success"] is False
        assert "smtp_success" in result
        assert "imap_success" in result
        assert "smtp_message" in result
        assert "imap_message" in result
