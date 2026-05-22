"""
Тесты сервиса входящих писем (InboxService)
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, call


class TestInboxServiceClassification:
    """Тесты классификации ответов"""
    
    @pytest.fixture(autouse=True)
    def mock_session_local(self, test_db):
        from sqlalchemy.orm import sessionmaker
        engine = test_db.bind
        Session = sessionmaker(bind=engine)
        with patch('services.inbox_service.SessionLocal', side_effect=Session):
            yield
    
    def test_classify_kp(self):
        """Классификация КП"""
        from services.inbox_service import InboxService
        
        service = InboxService()
        result = service.classify_response(
            "Добрый день! Во вложении коммерческое предложение на 100 Мбит/с. "
            "Стоимость подключения 5000 руб, абонентская плата 3000 руб/мес."
        )
        
        assert result["category"] == "kp"
        assert result["confidence"] > 0.5
    
    def test_classify_question(self):
        """Классификация вопроса"""
        from services.inbox_service import InboxService
        
        service = InboxService()
        result = service.classify_response(
            "Добрый день! Какой интерфейс требуется? RJ-45 или SFP? "
            "И какие сроки подключения?"
        )
        
        assert result["category"] == "question"
    
    def test_classify_refusal(self):
        """Классификация отказа"""
        from services.inbox_service import InboxService
        
        service = InboxService()
        result = service.classify_response(
            "К сожалению, мы не оказываем услуги в данном регионе. "
            "Не сможем предоставить КП."
        )
        
        assert result["category"] == "refusal"
    
    def test_classify_auto_reply(self):
        """Классификация автоответа"""
        from services.inbox_service import InboxService
        
        service = InboxService()
        result = service.classify_response(
            "Спасибо за обращение! Я в отпуске до 30 июня. "
            "По срочным вопросам обращайтесь к коллегам."
        )
        
        assert result["category"] == "auto_reply"
    
    def test_classify_empty_text(self):
        """Классификация пустого текста"""
        from services.inbox_service import InboxService
        
        service = InboxService()
        result = service.classify_response("")
        
        assert result["category"] == "unknown"
        assert result["confidence"] == 0.0
    
    def test_classify_unknown(self):
        """Классификация непонятного текста"""
        from services.inbox_service import InboxService
        
        service = InboxService()
        result = service.classify_response("12345 xyz")
        
        assert result["category"] == "unknown"


class TestInboxServiceEmailParsing:
    """Тесты парсинга email"""
    
    @pytest.fixture(autouse=True)
    def mock_session_local(self, test_db):
        from sqlalchemy.orm import sessionmaker
        engine = test_db.bind
        Session = sessionmaker(bind=engine)
        with patch('services.inbox_service.SessionLocal', side_effect=Session):
            yield
    
    def test_extract_email_with_brackets(self):
        """Извлечение email из скобок"""
        from services.inbox_service import InboxService
        
        service = InboxService()
        email = service._extract_email("Иванов И.И. <ivanov@example.com>")
        
        assert email == "ivanov@example.com"
    
    def test_extract_email_plain(self):
        """Извлечение plain email"""
        from services.inbox_service import InboxService
        
        service = InboxService()
        email = service._extract_email("petrov@example.com")
        
        assert email == "petrov@example.com"
    
    def test_extract_email_invalid(self):
        """Невалидный email"""
        from services.inbox_service import InboxService
        
        service = InboxService()
        email = service._extract_email("invalid-email")
        
        assert email is None


class TestInboxServiceDialogueStatus:
    """Тесты преобразования классификации в статус диалога"""
    
    @pytest.fixture(autouse=True)
    def mock_session_local(self, test_db):
        from sqlalchemy.orm import sessionmaker
        engine = test_db.bind
        Session = sessionmaker(bind=engine)
        with patch('services.inbox_service.SessionLocal', side_effect=Session):
            yield
    
    def test_dialogue_status_kp(self):
        """Статус для КП"""
        from services.inbox_service import InboxService
        
        service = InboxService()
        status = service._dialogue_status_from_classification("kp")
        
        assert status == "kp_received"
    
    def test_dialogue_status_question(self):
        """Статус для вопроса"""
        from services.inbox_service import InboxService
        
        service = InboxService()
        status = service._dialogue_status_from_classification("question")
        
        assert status == "clarifying"
    
    def test_dialogue_status_refusal(self):
        """Статус для отказа"""
        from services.inbox_service import InboxService
        
        service = InboxService()
        status = service._dialogue_status_from_classification("refusal")
        
        assert status == "rejected"
    
    def test_dialogue_status_unknown(self):
        """Статус для неизвестного"""
        from services.inbox_service import InboxService
        
        service = InboxService()
        status = service._dialogue_status_from_classification("unknown")
        
        assert status == "clarifying"


class TestInboxServiceSummary:
    """Тесты генерации summary"""
    
    @pytest.fixture(autouse=True)
    def mock_session_local(self, test_db):
        from sqlalchemy.orm import sessionmaker
        engine = test_db.bind
        Session = sessionmaker(bind=engine)
        with patch('services.inbox_service.SessionLocal', side_effect=Session):
            yield
    
    def test_generate_summary_kp(self):
        """Summary для КП"""
        from services.inbox_service import InboxService
        
        service = InboxService()
        summary = service._generate_summary("Наше КП во вложении PDF", "kp")
        
        assert "КП получено" in summary
    
    def test_generate_summary_question(self):
        """Summary для вопроса"""
        from services.inbox_service import InboxService
        
        service = InboxService()
        summary = service._generate_summary("Какие сроки?", "question")
        
        assert "Вопрос:" in summary


class TestInboxServiceFetchEmails:
    """Тесты получения писем с IMAP (с моками)"""
    
    @pytest.fixture(autouse=True)
    def mock_session_local(self, test_db):
        from sqlalchemy.orm import sessionmaker
        engine = test_db.bind
        Session = sessionmaker(bind=engine)
        with patch('services.inbox_service.SessionLocal', side_effect=Session):
            yield
    
    def test_fetch_emails_success(self):
        """Успешное получение писем"""
        from services.inbox_service import InboxService
        
        service = InboxService()
        
        # Мокаем imaplib.IMAP4_SSL
        with patch('services.inbox_service.IMAP4_SSL') as MockIMAP:
            mock_server = MagicMock()
            MockIMAP.return_value.__enter__ = MagicMock(return_value=mock_server)
            MockIMAP.return_value.__exit__ = MagicMock(return_value=False)
            
            # Настройка мока
            mock_server.search.return_value = ('OK', [b'1 2 3'])
            mock_server.fetch.return_value = (
                'OK',
                [(b'1 (RFC822)', b'From: test@example.com\r\nSubject: Test\r\n\r\nBody')]
            )
            
            emails = service._fetch_emails(
                imap_host="imap.example.com",
                imap_port=993,
                email="user@example.com",
                password="password"
            )
            
            assert isinstance(emails, list)
            # Т.к. fetch возвращает 1 письмо, но search вернул 3 id
            # В цикле for email_id in email_ids будет 3 итерации
            # Но fetch возвращает одинаковый результат для каждого
            assert len(emails) == 3
    
    def test_fetch_emails_connection_error(self):
        """Ошибка подключения к IMAP"""
        from services.inbox_service import InboxService
        
        service = InboxService()
        
        with patch('services.inbox_service.IMAP4_SSL') as MockIMAP:
            MockIMAP.side_effect = Exception("Connection refused")
            
            emails = service._fetch_emails(
                imap_host="imap.example.com",
                imap_port=993,
                email="user@example.com",
                password="password"
            )
            
            assert emails == []


class TestInboxServiceCheckInbox:
    """Тесты check_inbox (с моками)"""
    
    @pytest.fixture(autouse=True)
    def mock_session_local(self, test_db):
        from sqlalchemy.orm import sessionmaker
        engine = test_db.bind
        Session = sessionmaker(bind=engine)
        with patch('services.inbox_service.SessionLocal', side_effect=Session):
            yield
    
    def test_check_inbox_no_account(self, test_db):
        """Проверка почты без активного аккаунта"""
        from services.inbox_service import InboxService
        
        service = InboxService()
        result = service.check_inbox()
        
        assert result == []
    
    def test_check_inbox_with_account(self, test_db):
        """Проверка почты с активным аккаунтом"""
        from services.inbox_service import InboxService
        from core.models import SMTPAccount
        from utils.encryption import encryption
        
        account = SMTPAccount(
            name="Test Account",
            email="test@example.com",
            smtp_host="smtp.example.com",
            smtp_port=587,
            imap_host="imap.example.com",
            imap_port=993,
            password_enc=encryption.encrypt("password123"),
            is_active=True,
            is_primary=True
        )
        test_db.add(account)
        test_db.commit()
        
        service = InboxService()
        
        with patch.object(service, '_fetch_emails') as mock_fetch:
            mock_fetch.return_value = [
                {
                    "message_id": "<123@example.com>",
                    "from": "sender@example.com",
                    "subject": "Test Subject",
                    "date": "Mon, 01 Jan 2026 00:00:00 +0000",
                    "body_plain": "Тестовое письмо",
                    "body_html": "",
                    "attachments": [],
                    "raw": b"raw"
                }
            ]
            
            with patch.object(service, '_process_incoming_email') as mock_process:
                mock_process.return_value = {
                    "message_id": "<123@example.com>",
                    "from": "sender@example.com",
                    "subject": "Test Subject",
                    "classification": "unknown",
                    "confidence": 0.3,
                    "summary": "Тест...",
                    "dialogue_id": 1,
                    "task_created": False
                }
                
                result = service.check_inbox()
                
                assert len(result) == 1
                assert result[0]["classification"] == "unknown"


class TestInboxServiceProcessIncoming:
    """Тесты обработки входящих писем"""
    
    @pytest.fixture(autouse=True)
    def mock_session_local(self, test_db):
        from sqlalchemy.orm import sessionmaker
        engine = test_db.bind
        Session = sessionmaker(bind=engine)
        with patch('services.inbox_service.SessionLocal', side_effect=Session):
            yield
    
    def test_process_incoming_email_unknown_contact(self, test_db):
        """Письмо от неизвестного контакта"""
        from services.inbox_service import InboxService
        
        service = InboxService()
        email_data = {
            "message_id": "<123@example.com>",
            "from": "unknown@example.com",
            "subject": "Test",
            "body_plain": "Test body",
            "body_html": "",
            "attachments": [],
            "raw": b"raw"
        }
        
        result = service._process_incoming_email(email_data, test_db)
        
        assert result is None
    
    def test_process_incoming_email_no_dialogue(self, test_db, test_contact):
        """Письмо без активного диалога"""
        from services.inbox_service import InboxService
        
        service = InboxService()
        email_data = {
            "message_id": "<123@example.com>",
            "from": test_contact.email,
            "subject": "Test",
            "body_plain": "Test body",
            "body_html": "",
            "attachments": [],
            "raw": b"raw"
        }
        
        result = service._process_incoming_email(email_data, test_db)
        
        assert result is None
    
    def test_process_incoming_email_success(self, test_db, test_dialogue):
        """Успешная обработка входящего письма"""
        from services.inbox_service import InboxService
        from core.models import Contact
        
        contact = test_db.query(Contact).filter_by(id=test_dialogue.contact_id).first()
        
        service = InboxService()
        email_data = {
            "message_id": "<123@example.com>",
            "from": contact.email,
            "subject": "Re: Запрос КП",
            "body_plain": "Во вложении наше коммерческое предложение на 5000 рублей.",
            "body_html": "",
            "attachments": [],
            "raw": b"raw"
        }
        
        result = service._process_incoming_email(email_data, test_db)
        
        assert result is not None
        assert result["from"] == contact.email
        assert result["classification"] == "kp"
        assert result["dialogue_id"] == test_dialogue.id
        assert result["task_created"] is True


class TestInboxServiceUnansweredDialogues:
    """Тесты получения диалогов без ответа"""
    
    @pytest.fixture(autouse=True)
    def mock_session_local(self, test_db):
        from sqlalchemy.orm import sessionmaker
        engine = test_db.bind
        Session = sessionmaker(bind=engine)
        with patch('services.inbox_service.SessionLocal', side_effect=Session):
            yield
    
    def test_get_unanswered_dialogues(self, test_db, test_dialogue):
        """Получение диалогов без ответа"""
        from services.inbox_service import InboxService
        from datetime import datetime, timedelta
        
        # Установить старую дату последней активности
        test_dialogue.last_activity = datetime.utcnow() - timedelta(days=5)
        test_dialogue.status = "sent"
        test_db.commit()
        
        service = InboxService()
        result = service.get_unanswered_dialogues(days=3)
        
        assert len(result) == 1
        assert result[0]["id"] == test_dialogue.id
        assert result[0]["days_without_response"] >= 5
    
    def test_get_unanswered_dialogues_recent(self, test_db, test_dialogue):
        """Недавние диалоги не попадают в список"""
        from services.inbox_service import InboxService
        from datetime import datetime
        
        test_dialogue.last_activity = datetime.utcnow()
        test_dialogue.status = "sent"
        test_db.commit()
        
        service = InboxService()
        result = service.get_unanswered_dialogues(days=3)
        
        assert len(result) == 0


class TestInboxServiceKeywords:
    """Тесты ключевых слов классификации"""
    
    @pytest.fixture(autouse=True)
    def mock_session_local(self, test_db):
        from sqlalchemy.orm import sessionmaker
        engine = test_db.bind
        Session = sessionmaker(bind=engine)
        with patch('services.inbox_service.SessionLocal', side_effect=Session):
            yield
    
    def test_kp_keywords(self):
        """Ключевые слова КП"""
        from services.inbox_service import InboxService
        
        service = InboxService()
        assert "кп" in service.classification_keywords["kp"]
        assert "стоимость" in service.classification_keywords["kp"]
        assert "руб" in service.classification_keywords["kp"]
    
    def test_refusal_keywords(self):
        """Ключевые слова отказа"""
        from services.inbox_service import InboxService
        
        service = InboxService()
        assert "не можем" in service.classification_keywords["refusal"]
        assert "отказ" in service.classification_keywords["refusal"]
    
    def test_question_keywords(self):
        """Ключевые слова вопроса"""
        from services.inbox_service import InboxService
        
        service = InboxService()
        assert "вопрос" in service.classification_keywords["question"]
        assert "?" in service.classification_keywords["question"]
