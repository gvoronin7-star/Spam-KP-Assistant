"""
Тесты для LLM Agent Service
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, PropertyMock

from services.llm_agent_service import LLMAgentService
from core.models import Dialogue, Message, Task, Profile, Contact, SMTPAccount


class TestLLMAgentServiceInit:
    """Тесты инициализации"""
    
    def test_init_default_mode(self):
        """Инициализация с режимом по умолчанию"""
        with patch.object(LLMAgentService, '__init__', return_value=None):
            service = LLMAgentService.__new__(LLMAgentService)
            service.mode = LLMAgentService.MODE_DRAFT_ONLY
            service.llm_service = None
            
            assert service.mode == "draft_only"
    
    def test_init_disabled_mode(self):
        """Инициализация в выключенном режиме"""
        with patch.object(LLMAgentService, '__init__', return_value=None):
            service = LLMAgentService.__new__(LLMAgentService)
            service.mode = LLMAgentService.MODE_DISABLED
            service.llm_service = None
            
            assert service.mode == "disabled"
    
    def test_set_mode_valid(self):
        """Установка допустимого режима"""
        with patch.object(LLMAgentService, '__init__', return_value=None):
            service = LLMAgentService.__new__(LLMAgentService)
            service.mode = "draft_only"
            
            with patch('services.llm_agent_service.logger'):
                service.set_mode("auto")
                assert service.mode == "auto"
    
    def test_set_mode_invalid(self):
        """Установка недопустимого режима"""
        with patch.object(LLMAgentService, '__init__', return_value=None):
            service = LLMAgentService.__new__(LLMAgentService)
            service.mode = "draft_only"
            
            with pytest.raises(ValueError):
                service.set_mode("invalid_mode")
    
    def test_get_status_disabled(self):
        """Статус в выключенном режиме"""
        with patch.object(LLMAgentService, '__init__', return_value=None):
            service = LLMAgentService.__new__(LLMAgentService)
            service.mode = "disabled"
            service.llm_service = None
            
            status = service.get_status()
            assert status["mode"] == "disabled"
            assert status["llm_configured"] is False


class TestLLMAgentServiceProcess:
    """Тесты обработки сообщений"""
    
    def test_process_disabled(self, test_db, test_dialogue):
        """Обработка в выключенном режиме"""
        service = LLMAgentService.__new__(LLMAgentService)
        service.mode = LLMAgentService.MODE_DISABLED
        service.llm_service = MagicMock()
        
        message = MagicMock()
        result = service.process_incoming_message(message, test_dialogue, test_db)
        
        assert result["action"] == "skipped"
        assert result["reason"] == "agent_disabled"
    
    def test_process_no_llm(self, test_db, test_dialogue):
        """Обработка без настроенного LLM"""
        service = LLMAgentService.__new__(LLMAgentService)
        service.mode = LLMAgentService.MODE_DRAFT_ONLY
        service.llm_service = None
        
        message = MagicMock()
        result = service.process_incoming_message(message, test_dialogue, test_db)
        
        assert result["action"] == "skipped"
        assert result["reason"] == "llm_not_configured"
    
    def test_get_dialogue_history(self, test_db, test_dialogue):
        """Получение истории диалога"""
        # Создать несколько сообщений
        msg1 = Message(
            dialogue_id=test_dialogue.id,
            direction="outbound",
            subject="Запрос КП",
            body_plain="Текст запроса",
            status="sent"
        )
        msg2 = Message(
            dialogue_id=test_dialogue.id,
            direction="inbound",
            subject="Re: Запрос КП",
            body_plain="Ответ поставщика",
            status="received"
        )
        test_db.add_all([msg1, msg2])
        test_db.commit()
        
        service = MagicMock()
        service.llm_service = None
        
        history = LLMAgentService._get_dialogue_history(service, test_dialogue, test_db)
        
        assert len(history) == 2
        assert history[0]["direction"] == "outbound"
        assert history[1]["direction"] == "inbound"
    
    def test_save_draft(self, test_db, test_dialogue):
        """Сохранение черновика"""
        # Создать входящее сообщение
        inbound = Message(
            dialogue_id=test_dialogue.id,
            direction="inbound",
            subject="Вопрос",
            body_plain="Какие сроки?",
            from_address="test@example.com",
            to_address="me@example.com",
            status="received"
        )
        test_db.add(inbound)
        test_db.commit()
        
        service = MagicMock()
        service.llm_service = MagicMock()
        service.llm_service.get_used_model.return_value = "test-model"
        
        draft_id = LLMAgentService._save_draft(
            service, "Ответ на вопрос", inbound, test_dialogue, test_db
        )
        
        draft = test_db.query(Message).filter_by(id=draft_id).first()
        assert draft is not None
        assert draft.status == "draft"
        assert draft.direction == "outbound"
        assert draft.generated_by_llm is True
        assert "Re: Вопрос" in draft.subject
    
    def test_create_approval_task(self, test_db, test_dialogue):
        """Создание задачи на подтверждение"""
        inbound = Message(
            dialogue_id=test_dialogue.id,
            direction="inbound",
            subject="Вопрос",
            body_plain="Какие сроки?",
            from_address="test@example.com",
            to_address="me@example.com",
            status="received"
        )
        test_db.add(inbound)
        test_db.commit()
        
        service = MagicMock()
        service.llm_service = MagicMock()
        service.llm_service.get_used_model.return_value = "test-model"
        
        with patch.object(LLMAgentService, '_save_draft', return_value=42):
            task_id = LLMAgentService._create_approval_task(
                service, "Ответ", inbound, test_dialogue, test_db
            )
        
        task = test_db.query(Task).filter_by(id=task_id).first()
        assert task is not None
        assert task.task_type == "llm_review"
        assert test_dialogue.id == task.dialogue_id
    
    def test_save_kp_data(self, test_db, test_dialogue):
        """Сохранение данных КП"""
        service = MagicMock()
        service.llm_service = None
        
        kp_data = {
            "prices": [{"item": "Интернет", "price": 5000, "currency": "RUB"}],
            "confidence": 0.9
        }
        
        LLMAgentService._save_kp_data(service, test_dialogue, kp_data, test_db)
        
        assert test_dialogue.kp_received is True
        assert "llm_extracted" in test_dialogue.kp_data
        assert test_dialogue.kp_data["llm_extracted"]["prices"][0]["price"] == 5000


class TestLLMAgentServiceAnalysis:
    """Тесты анализа сообщений"""
    
    def test_analyze_message_json_parsing(self, test_db, test_dialogue):
        """Парсинг JSON из ответа LLM"""
        service = MagicMock()
        service.llm_service = MagicMock()
        service.llm_service.generate_text.return_value = """
        Вот анализ:
        {
            "category": "question",
            "needs_reply": true,
            "has_kp": false,
            "confidence": 0.85,
            "sentiment": "neutral",
            "questions": ["Какие сроки?"],
            "urgency": "medium"
        }
        """
        
        message = Message(
            dialogue_id=test_dialogue.id,
            direction="inbound",
            subject="Вопрос",
            body_plain="Какие сроки поставки?",
            status="received"
        )
        test_db.add(message)
        test_db.commit()
        
        result = LLMAgentService._analyze_message(service, message, test_dialogue, test_db)
        
        assert result["category"] == "question"
        assert result["needs_reply"] is True
        assert result["confidence"] == 0.85
    
    def test_analyze_message_no_json(self, test_db, test_dialogue):
        """Обработка ответа без JSON"""
        service = MagicMock()
        service.llm_service = MagicMock()
        service.llm_service.generate_text.return_value = "Просто текст без JSON"
        
        message = Message(
            dialogue_id=test_dialogue.id,
            direction="inbound",
            subject="Тест",
            body_plain="Текст",
            status="received"
        )
        test_db.add(message)
        test_db.commit()
        
        result = LLMAgentService._analyze_message(service, message, test_dialogue, test_db)
        
        assert result["category"] == "unknown"
        assert result["needs_reply"] is False
    
    def test_analyze_message_llm_error(self, test_db, test_dialogue):
        """Обработка ошибки LLM"""
        service = MagicMock()
        service.llm_service = MagicMock()
        service.llm_service.generate_text.side_effect = Exception("API Error")
        
        message = Message(
            dialogue_id=test_dialogue.id,
            direction="inbound",
            subject="Тест",
            body_plain="Текст",
            status="received"
        )
        test_db.add(message)
        test_db.commit()
        
        result = LLMAgentService._analyze_message(service, message, test_dialogue, test_db)
        
        assert result["category"] == "unknown"
        assert result["needs_reply"] is False


class TestLLMAgentServiceExtractKP:
    """Тесты извлечения данных КП"""
    
    def test_extract_kp_data_success(self, test_db, test_dialogue):
        """Успешное извлечение данных КП"""
        service = MagicMock()
        service.llm_service = MagicMock()
        service.llm_service.generate_text.return_value = """
        {
            "prices": [
                {"item": "Интернет 100 Мбит/с", "price": 5000, "currency": "RUB", "unit": "мес"}
            ],
            "delivery_terms": "30 дней",
            "payment_terms": "100% предоплата",
            "warranty": "12 месяцев",
            "valid_until": "2026-12-31",
            "notes": "",
            "confidence": 0.92
        }
        """
        
        message = Message(
            dialogue_id=test_dialogue.id,
            direction="inbound",
            subject="КП на услуги",
            body_plain="Предлагаем Интернет 100 Мбит/с за 5000 руб/мес. Срок 30 дней.",
            status="received"
        )
        test_db.add(message)
        test_db.commit()
        
        result = LLMAgentService._extract_kp_data(service, message, test_dialogue, test_db)
        
        assert result is not None
        assert len(result["prices"]) == 1
        assert result["prices"][0]["price"] == 5000
        assert result["confidence"] == 0.92
    
    def test_extract_kp_data_no_json(self, test_db, test_dialogue):
        """Ответ без JSON"""
        service = MagicMock()
        service.llm_service = MagicMock()
        service.llm_service.generate_text.return_value = "Не удалось извлечь данные"
        
        message = Message(
            dialogue_id=test_dialogue.id,
            direction="inbound",
            subject="КП",
            body_plain="Текст",
            status="received"
        )
        test_db.add(message)
        test_db.commit()
        
        result = LLMAgentService._extract_kp_data(service, message, test_dialogue, test_db)
        
        assert result is None
    
    def test_extract_kp_data_llm_error(self, test_db, test_dialogue):
        """Ошибка LLM при извлечении"""
        service = MagicMock()
        service.llm_service = MagicMock()
        service.llm_service.generate_text.side_effect = Exception("Timeout")
        
        message = Message(
            dialogue_id=test_dialogue.id,
            direction="inbound",
            subject="КП",
            body_plain="Текст",
            status="received"
        )
        test_db.add(message)
        test_db.commit()
        
        result = LLMAgentService._extract_kp_data(service, message, test_dialogue, test_db)
        
        assert result is None


class TestLLMAgentServiceGenerateReply:
    """Тесты генерации ответов"""
    
    def test_generate_reply_success(self, test_db, test_dialogue):
        """Успешная генерация ответа"""
        service = MagicMock()
        service.llm_service = MagicMock()
        service.llm_service.generate_text.return_value = """
        Добрый день!
        
        Благодарим за ваше письмо. Мы рассмотрим ваше предложение и свяжемся с вами в ближайшее время.
        
        С уважением,
        Отдел закупок
        """
        
        message = Message(
            dialogue_id=test_dialogue.id,
            direction="inbound",
            subject="Вопрос",
            body_plain="Какие сроки?",
            status="received"
        )
        test_db.add(message)
        test_db.commit()
        
        analysis = {"questions": ["Какие сроки?"], "category": "question"}
        
        result = LLMAgentService._generate_reply(service, message, test_dialogue, analysis, test_db)
        
        assert result is not None
        assert "Благодарим" in result
    
    def test_generate_reply_cleans_markdown(self, test_db, test_dialogue):
        """Очистка markdown из ответа"""
        service = MagicMock()
        service.llm_service = MagicMock()
        service.llm_service.generate_text.return_value = "```text\nОтвет\n```"
        
        message = Message(
            dialogue_id=test_dialogue.id,
            direction="inbound",
            subject="Тест",
            body_plain="Текст",
            status="received"
        )
        test_db.add(message)
        test_db.commit()
        
        analysis = {"questions": [], "category": "unknown"}
        
        result = LLMAgentService._generate_reply(service, message, test_dialogue, analysis, test_db)
        
        assert "```" not in result
    
    def test_generate_reply_error(self, test_db, test_dialogue):
        """Ошибка генерации"""
        service = MagicMock()
        service.llm_service = MagicMock()
        service.llm_service.generate_text.side_effect = Exception("API Error")
        
        message = Message(
            dialogue_id=test_dialogue.id,
            direction="inbound",
            subject="Тест",
            body_plain="Текст",
            status="received"
        )
        test_db.add(message)
        test_db.commit()
        
        analysis = {"questions": [], "category": "unknown"}
        
        result = LLMAgentService._generate_reply(service, message, test_dialogue, analysis, test_db)
        
        assert result is None


class TestLLMAgentServiceSendReply:
    """Тесты отправки ответов"""
    
    def test_send_reply_no_smtp(self, test_db, test_dialogue):
        """Отправка без SMTP аккаунта"""
        service = MagicMock()
        service.llm_service = MagicMock()
        service.llm_service.get_used_model.return_value = "test-model"
        
        message = Message(
            dialogue_id=test_dialogue.id,
            direction="inbound",
            subject="Вопрос",
            body_plain="Текст",
            from_address="test@example.com",
            to_address="me@example.com",
            status="received"
        )
        test_db.add(message)
        test_db.commit()
        
        result = LLMAgentService._send_reply(
            service, "Ответ", message, test_dialogue, test_db
        )
        
        assert result is False
    
    def test_send_reply_success(self, test_db, test_dialogue):
        """Успешная отправка ответа"""
        from utils.encryption import encryption
        from core.models import SMTPAccount
        
        smtp = SMTPAccount(
            name="Test",
            email="me@example.com",
            smtp_host="smtp.example.com",
            smtp_port=587,
            password_enc=encryption.encrypt("pass"),
            is_active=True,
            is_primary=True
        )
        test_db.add(smtp)
        test_db.commit()
        
        service = MagicMock()
        service.llm_service = MagicMock()
        service.llm_service.get_used_model.return_value = "test-model"
        
        message = Message(
            dialogue_id=test_dialogue.id,
            direction="inbound",
            subject="Вопрос",
            body_plain="Текст",
            from_address="test@example.com",
            to_address="me@example.com",
            status="received"
        )
        test_db.add(message)
        test_db.commit()
        
        with patch('services.llm_agent_service.EmailService') as MockEmail:
            mock_email = MagicMock()
            mock_email.send_email.return_value = True
            MockEmail.return_value = mock_email
            
            result = LLMAgentService._send_reply(
                service, "Ответ", message, test_dialogue, test_db
            )
        
        assert result is True
        
        # Проверить, что исходящее сообщение создано
        outbound = test_db.query(Message).filter_by(
            dialogue_id=test_dialogue.id,
            direction="outbound"
        ).first()
        assert outbound is not None
        assert outbound.generated_by_llm is True


class TestLLMAgentServiceProcessUnanswered:
    """Тесты массовой обработки"""
    
    def test_process_unanswered_disabled(self, test_db):
        """Обработка в выключенном режиме"""
        service = LLMAgentService.__new__(LLMAgentService)
        service.mode = LLMAgentService.MODE_DISABLED
        service.llm_service = None
        
        result = service.process_unanswered_dialogues(test_db)
        
        assert result["processed"] == 0
        assert result["reason"] == "agent_disabled"
    
    def test_process_unanswered_no_dialogues(self, test_db):
        """Нет неотвеченных диалогов"""
        service = LLMAgentService.__new__(LLMAgentService)
        service.mode = LLMAgentService.MODE_DRAFT_ONLY
        service.llm_service = MagicMock()
        service.process_incoming_message = MagicMock(return_value={"action": "draft_created"})
        
        result = service.process_unanswered_dialogues(test_db)
        
        assert result["processed"] == 0


class TestLLMAgentServiceIntegration:
    """Интеграционные тесты"""
    
    def test_full_flow_draft_mode(self, test_db, test_dialogue):
        """Полный поток в режиме draft_only"""
        service = LLMAgentService.__new__(LLMAgentService)
        service.mode = LLMAgentService.MODE_DRAFT_ONLY
        service.llm_service = MagicMock()
        service.llm_service.get_used_model.return_value = "test-model"
        
        # Мокаем анализ
        service._analyze_message = MagicMock(return_value={
            "category": "question",
            "needs_reply": True,
            "has_kp": False,
            "confidence": 0.9,
            "sentiment": "neutral",
            "questions": ["Сроки?"],
            "urgency": "medium"
        })
        service._generate_reply = MagicMock(return_value="Добрый день! Сроки поставки — 30 дней.")
        service._save_draft = MagicMock(return_value=42)
        service._extract_kp_data = MagicMock(return_value=None)
        
        message = Message(
            dialogue_id=test_dialogue.id,
            direction="inbound",
            subject="Вопрос",
            body_plain="Какие сроки?",
            from_address="test@example.com",
            to_address="me@example.com",
            status="received"
        )
        test_db.add(message)
        test_db.commit()
        
        result = service.process_incoming_message(message, test_dialogue, test_db)
        
        assert result["action"] == "draft_created"
        assert "Сроки" in result["reply_text"]
    
    def test_full_flow_with_kp(self, test_db, test_dialogue):
        """Поток с извлечением КП"""
        service = LLMAgentService.__new__(LLMAgentService)
        service.mode = LLMAgentService.MODE_DRAFT_ONLY
        service.llm_service = MagicMock()
        service.llm_service.get_used_model.return_value = "test-model"
        
        service._analyze_message = MagicMock(return_value={
            "category": "auto_reply",
            "needs_reply": False,
            "has_kp": True,
            "confidence": 0.85,
            "sentiment": "positive",
            "questions": [],
            "urgency": "low"
        })
        service._generate_reply = MagicMock(return_value="Спасибо за КП!")
        service._save_draft = MagicMock(return_value=42)
        kp_data = {"prices": [{"item": "Интернет", "price": 5000}], "confidence": 0.9}
        service._extract_kp_data = MagicMock(return_value=kp_data)
        service._save_kp_data = MagicMock()
        
        message = Message(
            dialogue_id=test_dialogue.id,
            direction="inbound",
            subject="КП",
            body_plain="Предлагаем за 5000 руб",
            from_address="test@example.com",
            to_address="me@example.com",
            status="received"
        )
        test_db.add(message)
        test_db.commit()
        
        result = service.process_incoming_message(message, test_dialogue, test_db)
        
        # Должно пропустить (needs_reply=false), но извлечь КП
        assert result["action"] == "skipped"
        assert result["kp_data"] is not None
        assert result["kp_data"]["prices"][0]["price"] == 5000
