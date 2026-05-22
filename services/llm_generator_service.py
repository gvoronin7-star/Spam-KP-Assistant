"""
Сервис генерации писем через LLM
"""
from typing import Dict, List, Optional
from loguru import logger
from core.models import Profile, Contact, Template, Dialogue


class LLMGeneratorService:
    """
    Сервис для генерации писем через LLM
    
    Возможности:
    - Генерация первичного письма на основе профиля
    - Генерация напоминаний
    - Генерация follow-up писем
    - Извлечение параметров из профиля
    """
    
    def __init__(self, llm_service=None, audit_service=None):
        """
        Инициализация сервиса
        
        Args:
            llm_service: Экземпляр LLMService (если None - создаётся автоматически)
            audit_service: Экземпляр AuditService (опционально)
        """
        self.llm_service = llm_service
        if self.llm_service is None:
            from services.llm_service import LLMService
            self.llm_service = LLMService()
    
        self.audit_service = audit_service
        if self.audit_service is None:
            from services.audit_service import AuditService
            self.audit_service = AuditService()
    
    def generate_primary_email(
        self,
        profile: Profile,
        contact: Contact,
        template: Optional[Template] = None
    ) -> Dict:
        """
        Генерация первичного письма на основе профиля
        
        Args:
            profile: Профиль закупки
            contact: Контакт поставщика
            template: Опциональный шаблон для основы
            
        Returns:
            {
                'subject': str,
                'body_plain': str,
                'body_html': str,
                'variables_used': list
            }
        """
        try:
            logger.info(f"Генерация первичного письма для {contact.company_name}")
            
            # Rate limiting
            self.llm_service.wait_if_needed()
            
            # Извлекаем параметры профиля
            params = self._extract_profile_params(profile)
            
            # Формируем контекст
            context = {
                'operator_name': params.get('operator_name', 'Наша компания'),
                'service_name': params.get('service_name', 'Услуга'),
                'description': params.get('description', ''),
                'tech_params': params.get('tech_params', {}),
                'budget': params.get('budget', ''),
                'deadlines': params.get('deadlines', ''),
                'company': contact.company_name,
                'contact_person': contact.contact_person or 'Коллеги'
            }
            
            # Генерируем промпт
            prompt = self._build_primary_email_prompt(context)
            
            # Отправляем запрос к LLM
            response = self.llm_service.generate(prompt)
            
            # Парсим ответ
            result = self._parse_email_response(response, context)
            
            # Логируем в аудит
            self.audit_service.log_create(
                entity_type='message',
                entity_id=0,  # ID будет присвоен при сохранении
                description=f"LLM генерация первичного письма для {contact.company_name}",
                new_values={
                    'subject': result['subject'],
                    'profile_id': profile.id if hasattr(profile, 'id') else None,
                    'contact_id': contact.id if hasattr(contact, 'id') else None,
                    'generated_by_llm': True
                }
            )
            
            logger.info(f"✅ Письмо сгенерировано успешно")
            return result
            
        except Exception as e:
            logger.error(f"Ошибка генерации письма: {e}")
            
            # Логируем ошибку в аудит
            self.audit_service.log_create(
                entity_type='message',
                entity_id=0,
                description=f"Ошибка LLM генерации письма для {contact.company_name}: {str(e)}",
                new_values={'error': str(e), 'fallback_used': True},
                success=False
            )
            
            # Fallback на шаблон
            return self._fallback_to_template(template, contact)
    
    def generate_reminder(
        self,
        dialogue: Dialogue,
        reminder_type: str = 'reminder_1'
    ) -> Dict:
        """
        Генерация напоминания
        
        Args:
            dialogue: Диалог с поставщиком
            reminder_type: Тип напоминания (reminder_1 или reminder_2)
            
        Returns:
            {
                'subject': str,
                'body_plain': str,
                'body_html': str
            }
        """
        try:
            logger.info(f"Генерация напоминания {reminder_type} для диалога {dialogue.id}")
            
            # Rate limiting
            self.llm_service.wait_if_needed()
            
            # Извлекаем контекст диалога
            context = self._extract_dialogue_context(dialogue)
            context['reminder_type'] = reminder_type
            
            # Формируем промпт
            if reminder_type == 'reminder_1':
                prompt = self._build_reminder_1_prompt(context)
            else:
                prompt = self._build_reminder_2_prompt(context)
            
            # Отправляем запрос к LLM
            response = self.llm_service.generate(prompt)
            
            # Парсим ответ
            result = self._parse_email_response(response, context)
            
            # Логируем в аудит
            self.audit_service.log_create(
                entity_type='message',
                entity_id=0,
                description=f"LLM генерация напоминания {reminder_type} для диалога {dialogue.id}",
                new_values={
                    'reminder_type': reminder_type,
                    'dialogue_id': dialogue.id,
                    'generated_by_llm': True
                }
            )
            
            logger.info(f"✅ Напоминание сгенерировано успешно")
            return result
            
        except Exception as e:
            logger.error(f"Ошибка генерации напоминания: {e}")
            
            # Логируем ошибку в аудит
            self.audit_service.log_create(
                entity_type='message',
                entity_id=0,
                description=f"Ошибка LLM генерации напоминания {reminder_type}: {str(e)}",
                new_values={'error': str(e), 'fallback_used': True},
                success=False
            )
            
            # Fallback на стандартный текст
            return self._fallback_reminder(reminder_type, dialogue)
    
    def generate_followup(
        self,
        dialogue: Dialogue,
        context: Dict
    ) -> Dict:
        """
        Генерация follow-up письма (уточнение, дополнительная информация)
        
        Args:
            dialogue: Диалог с поставщиком
            context: Контекст для генерации (цель follow-up)
            
        Returns:
            {
                'subject': str,
                'body_plain': str,
                'body_html': str
            }
        """
        try:
            logger.info(f"Генерация follow-up для диалога {dialogue.id}")
            
            # Rate limiting
            self.llm_service.wait_if_needed()
            
            # Извлекаем базовый контекст
            base_context = self._extract_dialogue_context(dialogue)
            base_context.update(context)
            
            # Формируем промпт
            prompt = self._build_followup_prompt(base_context)
            
            # Отправляем запрос к LLM
            response = self.llm_service.generate(prompt)
            
            # Парсим ответ
            result = self._parse_email_response(response, base_context)
            
            # Логируем в аудит
            self.audit_service.log_create(
                entity_type='message',
                entity_id=0,
                description=f"LLM генерация follow-up для диалога {dialogue.id}",
                new_values={
                    'purpose': context.get('purpose', 'Уточнение'),
                    'dialogue_id': dialogue.id,
                    'generated_by_llm': True
                }
            )
            
            logger.info(f"✅ Follow-up сгенерирован успешно")
            return result
            
        except Exception as e:
            logger.error(f"Ошибка генерации follow-up: {e}")
            
            # Логируем ошибку в аудит
            self.audit_service.log_create(
                entity_type='message',
                entity_id=0,
                description=f"Ошибка LLM генерации follow-up: {str(e)}",
                new_values={'error': str(e), 'fallback_used': True},
                success=False
            )
            
            return {
                'subject': 'Re: Уточнение',
                'body_plain': 'Добрый день!\n\nХотели бы уточнить некоторые детали по нашему запросу. \n\nПожалуйста, свяжитесь с нами для обсуждения.\n\nС уважением,\nНаша компания',
                'body_html': '<p>Добрый день!</p><p>Хотели бы уточнить некоторые детали по нашему запросу.</p><p>Пожалуйста, свяжитесь с нами для обсуждения.</p><p>С уважением,<br>Наша компания</p>'
            }
        
    def _extract_profile_params(self, profile: Profile) -> Dict:
        """
        Извлечение параметров из профиля
        
        Args:
            profile: Профиль закупки
            
        Returns:
            Словарь с параметрами
        """
        # Парсим tech_params из JSON
        tech_params = profile.tech_params if isinstance(profile.tech_params, dict) else {}
        requirements = profile.requirements if isinstance(profile.requirements, dict) else {}
        dialogue_rules = profile.dialogue_rules if isinstance(profile.dialogue_rules, dict) else {}
        
        return {
            'operator_name': 'Наша компания',  # Можно извлечь из настроек
            'service_name': profile.name,
            'description': profile.description,
            'tech_params': tech_params,
            'budget': requirements.get('budget', ''),
            'deadlines': requirements.get('deadline', ''),
            'dialogue_rules': dialogue_rules
        }
    
    def _extract_dialogue_context(self, dialogue: Dialogue) -> Dict:
        """
        Извлечение контекста из диалога
        
        Args:
            dialogue: Диалог
            
        Returns:
            Словарь с контекстом
        """
        from core.database import SessionLocal
        
        db = SessionLocal()
        try:
            contact = db.query(Contact).filter(Contact.id == dialogue.contact_id).first()
            profile = db.query(Profile).filter(Profile.id == dialogue.profile_id).first()
            
            context = {
                'company': contact.company_name if contact else 'Неизвестно',
                'contact_person': contact.contact_person if contact else 'Коллеги',
                'service_name': profile.name if profile else 'Услуга',
                'dialogue_status': dialogue.status,
                'kp_data': dialogue.kp_data if isinstance(dialogue.kp_data, dict) else {},
                'message_count': len(dialogue.messages) if dialogue.messages else 0
            }
            
            return context
        finally:
            db.close()

    def _build_primary_email_prompt(self, context: Dict) -> str:
        """
        Построение промпта для генерации первичного письма

        Args:
            context: Контекст генерации
            
        Returns:
            Промпт для LLM
        """
        tech_params_str = '\n'.join([f"- {k}: {v}" for k, v in context.get('tech_params', {}).items()])
        
        prompt = f"""Ты — помощник менеджера по закупкам телекоммуникационных услуг.

Напиши профессиональное деловое письмо на русском языке с запросом коммерческого предложения.

ИНФОРМАЦИЯ О НАС:
- Наша компания: {context['operator_name']}
- Запрашиваемая услуга: {context['service_name']}
- Описание: {context['description']}

ТЕХНИЧЕСКИЕ ТРЕБОВАНИЯ:
{tech_params_str if tech_params_str else 'Не указаны'}

ДОПОЛНИТЕЛЬНЫЕ ТРЕБОВАНИЯ:
- Бюджет: {context.get('budget', 'Не указан')}
- Сроки: {context.get('deadlines', 'Не указаны')}

ПОЛУЧАТЕЛЬ:
- Компания: {context['company']}
- Контактное лицо: {context['contact_person']}

ТРЕБОВАНИЯ К ПИСЬМУ:
1. Вежливый и профессиональный тон
2. Чёткое описание наших требований
3. Просьба указать стоимость и сроки подключения
4. Упомянуть, что рассматриваем несколько предложений
5. Контактные данные для связи
6. Не более 200 слов
7. Без лишних вступлений и формальностей

Напиши только текст письма, без служебной информации.
"""
        return prompt
    
    def _build_reminder_1_prompt(self, context: Dict) -> str:
        """
        Построение промпта для напоминания 1 (3 дня)
        
        Args:
            context: Контекст
            
        Returns:
            Промпт для LLM
        """
        prompt = f"""Ты — помощник менеджера по закупкам телекоммуникационных услуг.

Напиши вежливое напоминание о запросе коммерческого предложения.

ИНФОРМАЦИЯ:
- Наша компания: {context.get('operator_name', 'Наша компания')}
- Услуга: {context['service_name']}
- Компания поставщика: {context['company']}
- Контактное лицо: {context['contact_person']}
- Прошло дней без ответа: 3

ТРЕБОВАНИЯ К НАПОМИНАНИЮ:
1. Вежливый, не навязчивый тон
2. Напомнить о предыдущем запросе
3. Подчеркнуть важность получения КП
4. Упомянуть, что мы рассматриваем несколько предложений
5. Предложить связаться для уточнения деталей
6. Не более 100 слов

Напиши только текст письма.
"""
        return prompt
    
    def _build_reminder_2_prompt(self, context: Dict) -> str:
        """
        Построение промпта для напоминания 2 (7 дней)
        
        Args:
            context: Контекст
            
        Returns:
            Промпт для LLM
        """
        prompt = f"""Ты — помощник менеджера по закупкам телекоммуникационных услуг.

Напиши более настойчивое напоминание о запросе коммерческого предложения.

ИНФОРМАЦИЯ:
- Наша компания: {context.get('operator_name', 'Наша компания')}
- Услуга: {context['service_name']}
- Компания поставщика: {context['company']}
- Контактное лицо: {context['contact_person']}
- Прошло дней без ответа: 7

ТРЕБОВАНИЯ К НАПОМИНАНИЮ:
1. Более настойчивый, но всё ещё вежливый тон
2. Подчеркнуть, что это второе напоминание
3. Упомянуть сроки принятия решения
4. Предложить альтернативу (звонок, встреча)
5. Не более 120 слов

Напиши только текст письма.
"""
        return prompt
    
    def _build_followup_prompt(self, context: Dict) -> str:
        """
        Построение промпта для follow-up письма
        
        Args:
            context: Контекст
            
        Returns:
            Промпт для LLM
        """
        purpose = context.get('purpose', 'уточнить детали')
        additional_info = context.get('additional_info', '')
        
        prompt = f"""Ты — помощник менеджера по закупкам телекоммуникационных услуг.

Напиши письмо для уточнения деталей по коммерческому предложению.

ИНФОРМАЦИЯ:
- Наша компания: {context.get('operator_name', 'Наша компания')}
- Услуга: {context['service_name']}
- Компания поставщика: {context['company']}
- Контактное лицо: {context['contact_person']}
- Цель письма: {purpose}

ДОПОЛНИТЕЛЬНАЯ ИНФОРМАЦИЯ:
{additional_info if additional_info else 'Не указана'}

ТРЕБОВАНИЯ К ПИСЬМУ:
1. Вежливый и профессиональный тон
2. Чётко сформулировать цель письма
3. Задавать конкретные вопросы
4. Предложить связь для обсуждения
5. Не более 150 слов

Напиши только текст письма.
"""
        return prompt
    
    def _parse_email_response(self, response: str, context: Dict) -> Dict:
        """
        Парсинг ответа LLM в структуру письма
        
        Args:
            response: Ответ от LLM
            context: Контекст
            
        Returns:
            Словарь с subject, body_plain, body_html
        """
        # Очистка ответа от лишних символов
        body_plain = response.strip()
        
        # Генерация темы
        subject = f"Запрос КП - {context.get('service_name', 'Услуга')}"
        
        # Преобразование в HTML (простое)
        body_html = body_plain.replace('\n\n', '</p><p>').replace('\n', '<br>')
        body_html = f"<p>{body_html}</p>"
        
        return {
            'subject': subject,
            'body_plain': body_plain,
            'body_html': body_html,
            'variables_used': []
        }
    
    def _fallback_to_template(self, template: Optional[Template], contact: Contact) -> Dict:
        """
        Fallback на шаблон при ошибке LLM
        
        Args:
            template: Шаблон
            contact: Контакт
            
        Returns:
            Словарь с письмом
        """
        if template:
            body = template.body_plain
            body = body.replace('{{ company }}', contact.company_name)
            if contact.contact_person:
                body = body.replace('{{ contact_person }}', contact.contact_person)
            
            return {
                'subject': template.subject,
                'body_plain': body,
                'body_html': template.body_html,
                'variables_used': ['company', 'contact_person']
            }
        
        # Минимальный fallback
        return {
            'subject': f"Запрос КП - {contact.company_name}",
            'body_plain': f"Добрый день!\n\nЗапрашиваем коммерческое предложение.\n\nС уважением,\nНаша компания",
            'body_html': f"<p>Добрый день!</p><p>Запрашиваем коммерческое предложение.</p><p>С уважением,<br>Наша компания</p>",
            'variables_used': []
        }
    
    def _fallback_reminder(self, reminder_type: str, dialogue: Dialogue) -> Dict:
        """
        Fallback на стандартный текст напоминания
        
        Args:
            reminder_type: Тип напоминания
            dialogue: Диалог
            
        Returns:
            Словарь с напоминанием
        """
        from core.database import SessionLocal
        
        db = SessionLocal()
        try:
            contact = db.query(Contact).filter(Contact.id == dialogue.contact_id).first()
            company = contact.company_name if contact else 'Коллеги'
            
            if reminder_type == 'reminder_1':
                body = f"""Добрый день, {company}!

Напоминаем о нашем запросе коммерческого предложения.

Будем признательны, если вы сможете предоставить информацию в ближайшее время.

С уважением,
Наша компания"""
            else:
                body = f"""Добрый день, {company}!

Это второе напоминание о нашем запросе коммерческого предложения.

Просим вас сообщить о возможности предоставления КП или связаться с нами для обсуждения.

С уважением,
Наша компания"""
            
            return {
                'subject': 'Напоминание о запросе КП',
                'body_plain': body,
                'body_html': body.replace('\n\n', '</p><p>').replace('\n', '<br>')
            }
        finally:
            db.close()

    def save_generated_message(
        self,
        dialogue_id: int,
        generated_data: dict,
        message_type: str = 'outbound'
    ) -> int:
        """
        Сохранение сгенерированного письма как Message в БД

        Args:
            dialogue_id: ID диалога
            generated_data: Данные письма (subject, body_plain, body_html)
            message_type: Тип сообщения ('outbound' или 'inbound')
            
        Returns:
            ID сохранённого сообщения
        """
        from core.database import SessionLocal
        from core.models import Message
        from datetime import datetime
        
        db = SessionLocal()
        try:
            message = Message(
                dialogue_id=dialogue_id,
                direction=message_type,
                subject=generated_data.get('subject', ''),
                body_plain=generated_data.get('body_plain', ''),
                body_html=generated_data.get('body_html', ''),
                raw_body=generated_data.get('body_plain', ''),
                from_address='',  # Будет заполнено при отправке
                to_address='',  # Будет заполнено при отправке
                message_id=f'llm-{datetime.utcnow().timestamp()}',
                generated_by_llm=True,
                operator_edited=False,
                llm_model='llm-service',
                status='draft',
                is_read=True
            )
            
            db.add(message)
            db.commit()
            db.refresh(message)
            
            # Логируем в аудит
            self.audit_service.log_create(
                entity_type='message',
                entity_id=message.id,
                description=f"Сохранено сгенерированное LLM письмо в диалог {dialogue_id}",
                new_values={
                    'subject': message.subject,
                    'generated_by_llm': True,
                    'status': 'draft'
                }
            )
            
            logger.info(f"✅ Сообщение сохранено в БД: ID={message.id}")
            return message.id
            
        except Exception as e:
            logger.error(f"Ошибка сохранения сообщения: {e}")
            db.rollback()
            raise
        finally:
            db.close()


# Экспорт класса
__all__ = ['LLMGeneratorService']