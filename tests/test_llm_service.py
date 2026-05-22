"""
Тесты сервиса LLM (классификация)
"""
import pytest
from unittest.mock import MagicMock, patch, MagicMock


class TestLLMServiceClassification:
    """Тесты классификации через LLM"""
    
    def test_classify_with_llm_kp(self):
        """Классификация КП через LLM"""
        from services.llm_service import LLMService
        
        service = LLMService()
        
        # Мокаем generate_response
        with patch.object(service, 'generate_response') as mock_gen:
            mock_gen.return_value = '''
            {
                "category": "kp",
                "confidence": 0.9,
                "summary": "Коммерческое предложение с ценами"
            }
            '''
            
            result = service.classify_with_llm(
                "Добрый день! Во вложении наше КП. Цена 5000 руб/мес."
            )
            
            assert result["category"] == "kp"
            assert result["confidence"] == 0.9
            assert "КП" in result["summary"] or "коммерческое" in result["summary"].lower()
    
    def test_classify_with_llm_question(self):
        """Классификация вопроса через LLM"""
        from services.llm_service import LLMService
        
        service = LLMService()
        
        with patch.object(service, 'generate_response') as mock_gen:
            mock_gen.return_value = '''
            {
                "category": "question",
                "confidence": 0.85,
                "summary": "Вопросы по интерфейсам"
            }
            '''
            
            result = service.classify_with_llm(
                "Какой интерфейс требуется? RJ-45 или SFP?"
            )
            
            assert result["category"] == "question"
            assert result["confidence"] == 0.85
    
    def test_classify_with_llm_refusal(self):
        """Классификация отказа через LLM"""
        from services.llm_service import LLMService
        
        service = LLMService()
        
        with patch.object(service, 'generate_response') as mock_gen:
            mock_gen.return_value = '''
            {
                "category": "refusal",
                "confidence": 0.95,
                "summary": "Отказ от сотрудничества"
            }
            '''
            
            result = service.classify_with_llm(
                "К сожалению, мы не работаем в этом регионе."
            )
            
            assert result["category"] == "refusal"
    
    def test_classify_with_llm_auto_reply(self):
        """Классификация автоответа через LLM"""
        from services.llm_service import LLMService
        
        service = LLMService()
        
        with patch.object(service, 'generate_response') as mock_gen:
            mock_gen.return_value = '''
            {
                "category": "auto_reply",
                "confidence": 0.9,
                "summary": "Автоответ об отсутствии"
            }
            '''
            
            result = service.classify_with_llm(
                "Я в отпуске до 30 июня. По срочным вопросам пишите коллеге."
            )
            
            assert result["category"] == "auto_reply"
    
    def test_classify_with_llm_invalid_json(self):
        """LLM вернул некорректный JSON"""
        from services.llm_service import LLMService
        
        service = LLMService()
        
        with patch.object(service, 'generate_response') as mock_gen:
            mock_gen.return_value = 'Это не JSON вообще'
            
            result = service.classify_with_llm("Тестовое письмо")
            
            assert result["category"] == "unknown"
            assert result["confidence"] == 0.3
    
    def test_classify_with_llm_empty_response(self):
        """LLM не ответил"""
        from services.llm_service import LLMService
        
        service = LLMService()
        
        with patch.object(service, 'generate_response') as mock_gen:
            mock_gen.return_value = None
            
            result = service.classify_with_llm("Тест")
            
            assert result["category"] == "unknown"
            assert result["confidence"] == 0.2
    
    def test_classify_with_llm_invalid_category(self):
        """LLM вернул невалидную категорию"""
        from services.llm_service import LLMService
        
        service = LLMService()
        
        with patch.object(service, 'generate_response') as mock_gen:
            mock_gen.return_value = '''
            {
                "category": "invalid_category",
                "confidence": 0.9
            }
            '''
            
            result = service.classify_with_llm("Тест")
            
            assert result["category"] == "unknown"
    
    def test_classify_with_llm_context(self):
        """Классификация с контекстом диалога"""
        from services.llm_service import LLMService
        
        service = LLMService()
        
        with patch.object(service, 'generate_response') as mock_gen:
            mock_gen.return_value = '''
            {
                "category": "kp",
                "confidence": 0.88,
                "summary": "КП по профилю"
            }
            '''
            
            context = {
                "profile_name": "Тестовый профиль",
                "dialogue_status": "sent",
                "kp_sent": True
            }
            
            result = service.classify_with_llm(
                "Прикрепляем КП",
                context=context
            )
            
            assert result["category"] == "kp"
            # Проверка, что контекст был передан
            call_args = mock_gen.call_args
            assert "Контекст диалога" in call_args[0][0]  # system_prompt


class TestInboxServiceLLMClassification:
    """Тесты интеграции LLM в InboxService"""
    
    @pytest.fixture(autouse=True)
    def mock_session_local(self, test_db):
        from sqlalchemy.orm import sessionmaker
        engine = test_db.bind
        Session = sessionmaker(bind=engine)
        with patch('services.inbox_service.SessionLocal', side_effect=Session):
            yield
    
    def test_classify_with_llm_success(self, test_db):
        """Успешная классификация через LLM"""
        from services.inbox_service import InboxService
        
        service = InboxService()
        
        # Включаем мокаемый LLM
        if service.llm_service:
            with patch.object(service.llm_service, 'classify_with_llm') as mock_llm:
                mock_llm.return_value = {
                    "category": "kp",
                    "confidence": 0.9,
                    "summary": "КП от поставщика"
                }
                
                result = service.classify_response(
                    "Во вложении наше коммерческое предложение"
                )
                
                assert result["category"] == "kp"
                assert result["confidence"] == 0.9
    
    def test_classify_with_llm_fallback_to_keywords(self, test_db):
        """Fallback на keywords при низкой уверенности LLM"""
        from services.inbox_service import InboxService
        
        service = InboxService()
        
        if service.llm_service:
            with patch.object(service.llm_service, 'classify_with_llm') as mock_llm:
                # LLM неуверен
                mock_llm.return_value = {
                    "category": "unknown",
                    "confidence": 0.3,
                    "summary": "Не уверен"
                }
                
                result = service.classify_response(
                    "Коммерческое предложение во вложении, цена 5000 руб"
                )
                
                # Должен сработать fallback на keywords
                assert result["category"] == "kp"
                assert result["confidence"] > 0.5
    
    def test_classify_without_llm_fallback_only(self, test_db):
        """Классификация только через keywords если LLM не настроен"""
        from services.inbox_service import InboxService
        from config import settings
        
        # Эмулируем отсутствие API ключа
        original_key = settings.proxyapi_api_key
        settings.proxyapi_api_key = None
        
        # Пересоздаём сервис без LLM
        service = InboxService()
        
        # LLM должен быть None
        assert service.llm_service is None
        
        # Классификация только через keywords
        result = service.classify_response(
            "Коммерческое предложение, цена 5000 рублей"
        )
        
        assert result["category"] == "kp"
        
        # Восстанавливаем
        settings.proxyapi_api_key = original_key
    
    def test_classify_with_llm_with_dialogue_context(self, test_db, test_dialogue):
        """Классификация с контекстом диалога"""
        from services.inbox_service import InboxService
        
        service = InboxService()
        
        if service.llm_service:
            with patch.object(service.llm_service, 'classify_with_llm') as mock_llm:
                mock_llm.return_value = {
                    "category": "question",
                    "confidence": 0.85,
                    "summary": "Вопросы по КП"
                }
                
                result = service.classify_response(
                    "Уточните сроки",
                    dialogue=test_dialogue
                )
                
                assert result["category"] == "question"
                
                # Проверка передачи контекста
                mock_llm.assert_called_once()
                call_args = mock_llm.call_args
                context = call_args[0][1]
                assert context is not None  # context должен быть передан
                assert "profile_name" in context
        else:
            # Если LLM не настроен, просто проверяем fallback на keywords
            result = service.classify_response(
                "Уточните сроки по КП",
                dialogue=test_dialogue
            )
            assert result["category"] == "question"
