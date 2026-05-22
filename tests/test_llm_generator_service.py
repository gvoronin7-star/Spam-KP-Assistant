"""
Тесты для LLMGeneratorService
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

from services.llm_generator_service import LLMGeneratorService
from core.models import Profile, Contact, Template, Dialogue


class TestLLMGeneratorService:
    """Тесты для LLMGeneratorService"""
    
    @pytest.fixture
    def mock_llm_service(self):
        """Мокированный LLMService"""
        mock = Mock()
        mock.generate = Mock(return_value="Добрый день!\n\nЗапрашиваем коммерческое предложение...")
        return mock
    
    @pytest.fixture
    def generator(self, mock_llm_service):
        """Создание сервиса с мокированным LLM"""
        return LLMGeneratorService(llm_service=mock_llm_service)
    
    @pytest.fixture
    def sample_profile(self):
        """Тестовый профиль"""
        return Profile(
            name="Интернет-канал 100 Мбит/с",
            description="Запрос для офиса на 50 мест",
            tech_params={"speed": "100 Мбит/с", "protocol": "Ethernet"},
            requirements={"budget": "50000", "deadline": "30 дней"},
            dialogue_rules={},
            is_active=True
        )
    
    @pytest.fixture
    def sample_contact(self):
        """Тестовый контакт"""
        return Contact(
            email="test@example.com",
            company_name="ООО Тест",
            contact_person="Иванов И.И.",
            is_active=True
        )
        
    @pytest.fixture
    def sample_template(self):
        """Тестовый шаблон"""
        return Template(
            name="Test Template",
            subject="Запрос КП",
            body_plain="Добрый день! Запрашиваем КП.",
            body_html="<p>Добрый день! Запрашиваем КП.</p>",
            template_type='primary',
            is_active=True
        )
        
    @pytest.fixture
    def sample_dialogue(self):
        """Тестовый диалог"""
        return Dialogue(
            status='sent',
            kp_data={},
            created_at=datetime.now()
        )
        
    def test_generate_primary_email(self, generator, sample_profile, sample_contact):
        """Генерация первичного письма"""
        result = generator.generate_primary_email(sample_profile, sample_contact)
        
        assert 'subject' in result
        assert 'body_plain' in result
        assert 'body_html' in result
        assert 'variables_used' in result

        # Проверка содержимого
        assert len(result['subject']) > 0
        assert len(result['body_plain']) > 0
        assert len(result['body_html']) > 0

    def test_generate_primary_email_with_template(self, generator, sample_profile, sample_contact, sample_template):
        """Генерация с шаблоном"""
        result = generator.generate_primary_email(sample_profile, sample_contact, sample_template)
        
        assert result['subject'] is not None
        assert result['body_plain'] is not None
    
    def test_generate_reminder_1(self, generator, sample_dialogue):
        """Генерация напоминания 1"""
        result = generator.generate_reminder(sample_dialogue, 'reminder_1')
        
        assert 'subject' in result
        assert 'body_plain' in result
        assert len(result['body_plain']) > 0
    
    def test_generate_reminder_2(self, generator, sample_dialogue):
        """Генерация напоминания 2"""
        result = generator.generate_reminder(sample_dialogue, 'reminder_2')
        
        assert 'subject' in result
        assert 'body_plain' in result
        assert len(result['body_plain']) > 0
    
    def test_generate_followup(self, generator, sample_dialogue):
        """Генерация follow-up"""
        result = generator.generate_followup(
            sample_dialogue,
            {'purpose': 'Уточнить детали', 'additional_info': 'Нужна информация о ценах'}
        )
        
        assert 'subject' in result
        assert 'body_plain' in result
    
    def test_extract_profile_params(self, generator, sample_profile):
        """Извлечение параметров профиля"""
        params = generator._extract_profile_params(sample_profile)
        
        assert 'service_name' in params
        assert 'tech_params' in params
        assert params['service_name'] == "Интернет-канал 100 Мбит/с"
        assert params['tech_params']['speed'] == "100 Мбит/с"
        assert 'dialogue_rules' in params
    
    def test_extract_dialogue_context(self, generator, sample_dialogue):
        """Извлечение контекста диалога"""
        # Этот тест требует БД, пропустим в unit тестах
        pytest.skip("Requires database for Contact/Profile lookup")
    
    def test_build_primary_email_prompt(self, generator, sample_profile, sample_contact):
        """Построение промпта для первичного письма"""
        params = generator._extract_profile_params(sample_profile)
        context = {
            'operator_name': 'Test Company',
            'service_name': params['service_name'],
            'description': params['description'],
            'tech_params': params['tech_params'],
            'budget': params.get('budget', ''),
            'deadlines': params.get('deadlines', ''),
            'company': sample_contact.company_name,
            'contact_person': sample_contact.contact_person
        }
        
        prompt = generator._build_primary_email_prompt(context)
        
        assert 'Ты — помощник менеджера' in prompt
        assert sample_contact.company_name in prompt
        assert params['service_name'] in prompt
    
    def test_build_reminder_1_prompt(self, generator):
        """Построение промпта для напоминания 1"""
        context = {
            'operator_name': 'Test',
            'service_name': 'Service',
            'company': 'Company',
            'contact_person': 'Person'
        }
        
        prompt = generator._build_reminder_1_prompt(context)
        
        assert 'напоминание' in prompt.lower() or 'напоминаем' in prompt.lower()
    
    def test_build_reminder_2_prompt(self, generator):
        """Построение промпта для напоминания 2"""
        context = {
            'operator_name': 'Test',
            'service_name': 'Service',
            'company': 'Company',
            'contact_person': 'Person'
        }
        
        prompt = generator._build_reminder_2_prompt(context)
        
        assert 'второе напоминание' in prompt.lower() or 'напоминаем' in prompt.lower()
    
    def test_parse_email_response(self, generator):
        """Парсинг ответа LLM"""
        response = "Добрый день!\n\nЗапрашиваем КП..."
        context = {'service_name': 'Test Service'}
        
        result = generator._parse_email_response(response, context)
        
        assert 'subject' in result
        assert 'body_plain' in result
        assert 'body_html' in result
        assert 'Запрашиваем КП' in result['body_plain']
    
    def test_fallback_to_template(self, generator, sample_template, sample_contact):
        """Fallback на шаблон"""
        result = generator._fallback_to_template(sample_template, sample_contact)
        
        assert result['subject'] is not None
        assert result['body_plain'] is not None
    
    def test_fallback_to_template_none(self, generator, sample_contact):
        """Fallback без шаблона"""
        result = generator._fallback_to_template(None, sample_contact)
        
        assert result['subject'] is not None
        assert result['body_plain'] is not None
        assert len(result['body_plain']) > 0
    
    def test_fallback_reminder_1(self, generator, sample_dialogue):
        """Fallback для напоминания 1"""
        result = generator._fallback_reminder('reminder_1', sample_dialogue)
        
        assert result['subject'] is not None
        assert result['body_plain'] is not None
    
    def test_fallback_reminder_2(self, generator, sample_dialogue):
        """Fallback для напоминания 2"""
        result = generator._fallback_reminder('reminder_2', sample_dialogue)
        
        assert result['subject'] is not None
        assert result['body_plain'] is not None
    
    def test_fallback_on_error(self, generator, sample_profile, sample_contact):
        """Fallback на шаблон при ошибке LLM"""
        # Мокируем ошибку
        generator.llm_service.generate = Mock(side_effect=Exception("LLM error"))
        
        result = generator.generate_primary_email(sample_profile, sample_contact)
        
        # Должен сработать fallback
        assert result is not None
        assert 'subject' in result
    
    def test_save_generated_message(self, generator, sample_dialogue):
        """Сохранение сгенерированного сообщения в БД"""
        # Мокируем аудит сервис
        generator.audit_service = Mock()
        generator.audit_service.log_create = Mock()
        
        generated_data = {
            'subject': 'Тестовая тема',
            'body_plain': 'Тестовый текст',
            'body_html': '<p>Тестовый текст</p>'
        }
        
        # Этот тест требует БД, пропустим в unit тестах
        pytest.skip("Requires database for Message saving")
    
    def test_audit_logging_on_success(self, generator, sample_profile, sample_contact):
        """Проверка аудит-логирования при успешной генерации"""
        # Мокируем аудит сервис
        generator.audit_service = Mock()
        generator.audit_service.log_create = Mock()
        
        result = generator.generate_primary_email(sample_profile, sample_contact)
        
        # Проверяем, что аудит был вызван
        generator.audit_service.log_create.assert_called_once()
        call_args = generator.audit_service.log_create.call_args
        # call_args.kwargs содержит keyword arguments
        assert call_args.kwargs['entity_type'] == 'message'
        assert 'generated_by_llm' in call_args.kwargs['new_values']
    
    def test_audit_logging_on_error(self, generator, sample_profile, sample_contact):
        """Проверка аудит-логирования при ошибке"""
        # Мокируем ошибку
        generator.llm_service.generate = Mock(side_effect=Exception("LLM error"))
        
        # Мокируем аудит сервис
        generator.audit_service = Mock()
        generator.audit_service.log_create = Mock()
        
        result = generator.generate_primary_email(sample_profile, sample_contact)
        
        # Проверяем, что аудит был вызван с success=False
        generator.audit_service.log_create.assert_called()
        call_args = generator.audit_service.log_create.call_args
        assert call_args[1]['success'] == False
        assert 'error' in call_args[1]['new_values']
    
    def test_full_generation_workflow(self, generator, sample_profile, sample_contact, sample_template):
        """Интеграционный тест полного цикла генерации"""
        # Тест полного workflow:
        # 1. Генерация первичного письма
        # 2. Проверка результата
        # 3. Проверка rate limiting
        # 4. Проверка fallback на ошибку
        
        # 1. Генерация первичного
        primary = generator.generate_primary_email(sample_profile, sample_contact, sample_template)
        assert 'subject' in primary
        assert 'body_plain' in primary
        assert 'body_html' in primary
        assert len(primary['subject']) > 0
        assert len(primary['body_plain']) > 0
        
        # 2. Проверка содержимого (не проверяем конкретный текст, т.к. мок)
        assert primary['subject'] is not None
        assert primary['body_plain'] is not None
        
        # 3. Проверка rate limiting
        generator.llm_service.wait_if_needed.assert_called()
        
        # 4. Проверка fallback на ошибку
        generator.llm_service.generate = Mock(side_effect=Exception("Test error"))
        fallback = generator.generate_primary_email(sample_profile, sample_contact)
        assert fallback is not None
        assert 'subject' in fallback
        assert len(fallback['body_plain']) > 0