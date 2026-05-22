"""
Rule Engine — движок правил для автоматизации обработки ответов
"""
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Callable
from enum import Enum
from sqlalchemy.orm import Session
from loguru import logger

from core.models import Dialogue, Message, Task, Profile
from utils.datetime_helper import now_utc


class RuleConditionType(str, Enum):
    """Типы условий правил"""
    CONTAINS_KEYWORD = "contains_keyword"
    NOT_CONTAINS_KEYWORD = "not_contains_keyword"
    MESSAGE_TYPE = "message_type"
    HAS_ATTACHMENT = "has_attachment"
    NO_ATTACHMENT = "no_attachment"
    SENDER_DOMAIN = "sender_domain"
    DIALOGUE_STATUS = "dialogue_status"
    CUSTOM_LLM_RESULT = "custom_llm_result"


class RuleActionType(str, Enum):
    """Типы действий правил"""
    CREATE_TASK = "create_task"
    UPDATE_DIALOGUE_STATUS = "update_dialogue_status"
    SEND_AUTO_REPLY = "send_auto_reply"
    GENERATE_DRAFT_REPLY = "generate_draft_reply"
    FLAG_FOR_REVIEW = "flag_for_review"
    ARCHIVE = "archive"
    NOTIFY_OPERATOR = "notify_operator"


class RuleCondition:
    """Условие правила"""
    
    def __init__(
        self,
        condition_type: RuleConditionType,
        params: Dict[str, Any]
    ):
        self.condition_type = condition_type
        self.params = params
    
    def matches(
        self,
        message: Message,
        dialogue: Dialogue,
        db: Session
    ) -> bool:
        """
        Проверить, соответствует ли сообщение условию
        
        Args:
            message: Сообщение
            dialogue: Диалог
            db: Сессия БД
        
        Returns:
            Соответствует или нет
        """
        try:
            if self.condition_type == RuleConditionType.CONTAINS_KEYWORD:
                keywords = self.params.get("keywords", [])
                body = (message.body_plain or message.body_html or "").lower()
                return any(kw.lower() in body for kw in keywords)
            
            elif self.condition_type == RuleConditionType.NOT_CONTAINS_KEYWORD:
                keywords = self.params.get("keywords", [])
                body = (message.body_plain or message.body_html or "").lower()
                return not any(kw.lower() in body for kw in keywords)
            
            elif self.condition_type == RuleConditionType.MESSAGE_TYPE:
                expected_type = self.params.get("type")
                return message.generated_by_llm == (expected_type == "llm")
            
            elif self.condition_type == RuleConditionType.HAS_ATTACHMENT:
                attachments = message.attachments or []
                return len(attachments) > 0
            
            elif self.condition_type == RuleConditionType.NO_ATTACHMENT:
                attachments = message.attachments or []
                return len(attachments) == 0
            
            elif self.condition_type == RuleConditionType.SENDER_DOMAIN:
                expected_domain = self.params.get("domain", "").lower()
                from_address = (message.from_address or "").lower()
                return from_address.endswith(expected_domain)
            
            elif self.condition_type == RuleConditionType.DIALOGUE_STATUS:
                expected_status = self.params.get("status")
                return dialogue.status == expected_status
            
            elif self.condition_type == RuleConditionType.CUSTOM_LLM_RESULT:
                # Проверяем кастомный результат классификации LLM
                llm_result = self.params.get("llm_result")
                kp_data = dialogue.kp_data or {}
                classification = kp_data.get("classification")
                return classification == llm_result
            
            else:
                logger.warning(f"Неизвестный тип условия: {self.condition_type}")
                return False
        
        except Exception as e:
            logger.error(f"Ошибка проверки условия {self.condition_type}: {e}")
            return False


class RuleAction:
    """Действие правила"""
    
    def __init__(
        self,
        action_type: RuleActionType,
        params: Dict[str, Any]
    ):
        self.action_type = action_type
        self.params = params
    
    def execute(
        self,
        message: Message,
        dialogue: Dialogue,
        db: Session
    ) -> Dict[str, Any]:
        """
        Выполнить действие
        
        Args:
            message: Сообщение
            dialogue: Диалог
            db: Сессия БД
        
        Returns:
            Результат выполнения
        """
        try:
            if self.action_type == RuleActionType.CREATE_TASK:
                return self._create_task(message, dialogue, db)
            
            elif self.action_type == RuleActionType.UPDATE_DIALOGUE_STATUS:
                return self._update_dialogue_status(dialogue, db)
            
            elif self.action_type == RuleActionType.SEND_AUTO_REPLY:
                return self._send_auto_reply(message, dialogue, db)
            
            elif self.action_type == RuleActionType.GENERATE_DRAFT_REPLY:
                return self._generate_draft_reply(message, dialogue, db)
            
            elif self.action_type == RuleActionType.FLAG_FOR_REVIEW:
                return self._flag_for_review(message, dialogue, db)
            
            elif self.action_type == RuleActionType.ARCHIVE:
                return self._archive(dialogue, db)
            
            elif self.action_type == RuleActionType.NOTIFY_OPERATOR:
                return self._notify_operator(message, dialogue, db)
            
            else:
                logger.warning(f"Неизвестный тип действия: {self.action_type}")
                return {"success": False, "error": "Unknown action type"}
        
        except Exception as e:
            logger.error(f"Ошибка выполнения действия {self.action_type}: {e}")
            return {"success": False, "error": str(e)}
    
    def _create_task(
        self,
        message: Message,
        dialogue: Dialogue,
        db: Session
    ) -> Dict[str, Any]:
        """Создать задачу оператору"""
        from core.models import Task
        
        priority = self.params.get("priority", "medium")
        title = self.params.get("title", "Требуется внимание")
        description = self.params.get(
            "description",
            f"Новое сообщение от {message.from_address}: {message.subject}"
        )
        due_days = self.params.get("due_days", 3)
        
        from datetime import timedelta
        due_date = now_utc() + timedelta(days=due_days)
        
        task = Task(
            task_type="requires_response",
            title=title,
            description=description,
            dialogue_id=dialogue.id,
            priority=priority,
            due_date=due_date
        )
        
        db.add(task)
        db.commit()
        db.refresh(task)
        
        logger.info(f"Создана задача #{task.id} для диалога {dialogue.id}")
        
        return {
            "success": True,
            "action": "create_task",
            "task_id": task.id
        }
    
    def _update_dialogue_status(
        self,
        dialogue: Dialogue,
        db: Session
    ) -> Dict[str, Any]:
        """Обновить статус диалога"""
        new_status = self.params.get("status")
        
        if not new_status:
            return {"success": False, "error": "No status specified"}
        
        dialogue.status = new_status
        dialogue.last_activity = now_utc()
        db.commit()
        
        logger.info(f"Обновлен статус диалога {dialogue.id}: {new_status}")
        
        return {
            "success": True,
            "action": "update_dialogue_status",
            "new_status": new_status
        }
    
    def _send_auto_reply(
        self,
        message: Message,
        dialogue: Dialogue,
        db: Session
    ) -> Dict[str, Any]:
        """Отправить автоматический ответ"""
        # Получить SMTP аккаунт
        from services.email_service import EmailService
        
        smtp_account = self._get_primary_smtp_account(db)
        if not smtp_account:
            return {"success": False, "error": "No SMTP account configured"}
        
        # Сформировать ответ
        reply_subject = f"Re: {message.subject}"
        reply_body = self.params.get(
            "body",
            "Спасибо за ваше сообщение. Мы изучим его и ответим в ближайшее время."
        )
        
        email_service = EmailService()
        email_service.configure(
            smtp_host=smtp_account.smtp_host,
            smtp_port=smtp_account.smtp_port,
            email=smtp_account.email,
            password="",  # Пароль берется из Credential Manager
            use_tls=smtp_account.smtp_use_tls,
            imap_host=smtp_account.imap_host,
            imap_port=smtp_account.imap_port
        )
        
        success = email_service.send_email(
            to_email=message.from_address,
            subject=reply_subject,
            body_html=reply_body,
            body_plain=reply_body
        )
        
        if success:
            # Создать запись о ответе
            reply_message = Message(
                dialogue_id=dialogue.id,
                direction="outbound",
                subject=reply_subject,
                body_html=reply_body,
                body_plain=reply_body,
                from_address=smtp_account.email,
                to_address=message.from_address,
                status="sent"
            )
            db.add(reply_message)
            db.commit()
            
            logger.info(f"Автоответ отправлен: {message.from_address}")
        
        return {
            "success": success,
            "action": "send_auto_reply"
        }
    
    def _generate_draft_reply(
        self,
        message: Message,
        dialogue: Dialogue,
        db: Session
    ) -> Dict[str, Any]:
        """Сгенерировать черновик ответа через LLM"""
        from services.llm_service import LLMService
        
        llm_service = LLMService()
        
        # Сформировать запрос к LLM
        prompt = self._build_draft_prompt(message, dialogue, db)
        
        try:
            response = llm_service.generate_text(prompt)
            
            # Создать черновик сообщения
            draft_subject = f"Re: {message.subject}"
            draft_body = response or "Ошибка генерации ответа"
            
            draft_message = Message(
                dialogue_id=dialogue.id,
                direction="outbound",
                subject=draft_subject,
                body_html=draft_body,
                body_plain=draft_body,
                from_address=message.to_address,
                to_address=message.from_address,
                status="draft",
                generated_by_llm=True,
                llm_model=llm_service.get_used_model()
            )
            
            db.add(draft_message)
            db.commit()
            db.refresh(draft_message)
            
            logger.info(f"Сгенерирован черновик ответа #{draft_message.id}")
            
            return {
                "success": True,
                "action": "generate_draft_reply",
                "draft_id": draft_message.id
            }
        
        except Exception as e:
            logger.error(f"Ошибка генерации ответа: {e}")
            return {
                "success": False,
                "action": "generate_draft_reply",
                "error": str(e)
            }
    
    def _build_draft_prompt(
        self,
        message: Message,
        dialogue: Dialogue,
        db: Session
    ) -> str:
        """Сформировать промпт для генерации ответа"""
        profile = dialogue.profile
        
        # Получить контекст диалога
        context = f"""
Вы — помощник по закупкам телеком-услуг.
Вам нужно сформулировать профессиональный ответ на письмо от поставщика.

Контекст:
- Компания: {profile.name if profile else "Не указана"}
- Тип услуги: {profile.description[:100] if profile and profile.description else "Не указан"}
- Контакт: {message.from_address}

Входное письмо:
От: {message.from_address}
Тема: {message.subject}
Текст:
{message.body_plain or message.body_html or "Нет текста"}

Сформулируйте ответ:
1. Вежливое приветствие
2. Благодарность за ответ/КП
3. Вопросы или комментарии к предложению
4. Следующие шаги
5. Вежливое завершение

Ответ должен быть профессиональным, кратким и конкретным.
"""
        return context
    
    def _flag_for_review(
        self,
        message: Message,
        dialogue: Dialogue,
        db: Session
    ) -> Dict[str, Any]:
        """Пометить для ручной проверки"""
        from core.models import Task
        
        priority = self.params.get("priority", "high")
        
        task = Task(
            task_type="llm_review",
            title=f"Требуется проверка: {message.subject}",
            description=f"Сообщение от {message.from_address} требует ручной проверки.\n\n"
                       f"Текст:\n{message.body_plain or message.body_html}",
            dialogue_id=dialogue.id,
            priority=priority,
            due_date=now_utc()
        )
        
        db.add(task)
        db.commit()
        
        logger.info(f"Диалог {dialogue.id} помечен для проверки (задача #{task.id})")
        
        return {
            "success": True,
            "action": "flag_for_review",
            "task_id": task.id
        }
    
    def _archive(
        self,
        dialogue: Dialogue,
        db: Session
    ) -> Dict[str, Any]:
        """Архивировать диалог"""
        # Можно реализовать через метку или перемещение в отдельную таблицу
        dialogue.status = "archived"
        db.commit()
        
        logger.info(f"Диалог {dialogue.id} архивирован")
        
        return {
            "success": True,
            "action": "archive"
        }
    
    def _notify_operator(
        self,
        message: Message,
        dialogue: Dialogue,
        db: Session
    ) -> Dict[str, Any]:
        """Уведомить оператора"""
        from core.models import Task
        
        title = self.params.get("title", "Новое важное сообщение")
        description = self.params.get(
            "description",
            f"Сообщение от {message.from_address} требует внимания."
        )
        
        task = Task(
            task_type="requires_response",
            title=title,
            description=description,
            dialogue_id=dialogue.id,
            priority="high",
            due_date=now_utc()
        )
        
        db.add(task)
        db.commit()
        
        logger.info(f"Оператор уведомлен о новом сообщении (задача #{task.id})")
        
        return {
            "success": True,
            "action": "notify_operator",
            "task_id": task.id
        }
    
    def _get_primary_smtp_account(self, db: Session):
        """Получить основной SMTP аккаунт"""
        from core.models import SMTPAccount
        
        account = (
            db.query(SMTPAccount)
            .filter(
                SMTPAccount.is_active == True,
                SMTPAccount.is_primary == True
            )
            .first()
        )
        
        if not account:
            account = (
                db.query(SMTPAccount)
                .filter(SMTPAccount.is_active == True)
                .first()
            )
        
        return account


class Rule:
    """Правило обработки"""
    
    def __init__(
        self,
        rule_id: str,
        name: str,
        conditions: List[RuleCondition],
        actions: List[RuleAction],
        is_active: bool = True,
        priority: int = 0
    ):
        self.rule_id = rule_id
        self.name = name
        self.conditions = conditions
        self.actions = actions
        self.is_active = is_active
        self.priority = priority
    
    def matches(
        self,
        message: Message,
        dialogue: Dialogue,
        db: Session
    ) -> bool:
        """
        Проверить все условия правила
        
        Args:
            message: Сообщение
            dialogue: Диалог
            db: Сессия БД
        
        Returns:
            Все условия выполнены
        """
        return all(
            condition.matches(message, dialogue, db)
            for condition in self.conditions
        )
    
    def execute(
        self,
        message: Message,
        dialogue: Dialogue,
        db: Session
    ) -> List[Dict[str, Any]]:
        """
        Выполнить все действия правила
        
        Args:
            message: Сообщение
            dialogue: Диалог
            db: Сессия БД
        
        Returns:
            Результаты выполнения действий
        """
        results = []
        
        for action in self.actions:
            result = action.execute(message, dialogue, db)
            results.append(result)
        
        logger.info(
            f"Правило '{self.name}' выполнено: "
            f"{sum(1 for r in results if r.get('success'))}/{len(results)} успешно"
        )
        
        return results


class RuleEngine:
    """
    Движок правил для автоматизации обработки ответов
    
    Примеры правил:
    1. Если письмо содержит "спасибо за КП" → создать задачу "Проверить КП"
    2. Если письмо содержит "не можем предложить" → обновить статус "rejected"
    3. Если есть вложение → сгенерировать черновик ответа
    4. Если классификация LLM = "spam" → архивировать диалог
    """
    
    def __init__(self):
        self.rules: List[Rule] = []
        logger.info("RuleEngine инициализирован")
    
    def add_rule(self, rule: Rule):
        """Добавить правило"""
        self.rules.append(rule)
        self.rules.sort(key=lambda r: r.priority, reverse=True)
        logger.info(f"Добавлено правило: {rule.name} (приоритет {rule.priority})")
    
    def remove_rule(self, rule_id: str):
        """Удалить правило"""
        self.rules = [r for r in self.rules if r.rule_id != rule_id]
        logger.info(f"Правило удалено: {rule_id}")
    
    def process_message(
        self,
        message: Message,
        dialogue: Dialogue,
        db: Session
    ) -> Dict[str, Any]:
        """
        Обработать сообщение через все активные правила
        
        Args:
            message: Сообщение
            dialogue: Диалог
            db: Сессия БД
        
        Returns:
            Статистика обработки
        """
        stats = {
            "total_rules": len(self.rules),
            "matched": 0,
            "executed": 0,
            "results": []
        }
        
        for rule in self.rules:
            if not rule.is_active:
                continue
            
            if rule.matches(message, dialogue, db):
                stats["matched"] += 1
                results = rule.execute(message, dialogue, db)
                stats["executed"] += len(results)
                stats["results"].append({
                    "rule_id": rule.rule_id,
                    "rule_name": rule.name,
                    "results": results
                })
        
        logger.info(
            f"Сообщение {message.id} обработано: "
            f"{stats['matched']} правил сработало, "
            f"{stats['executed']} действий выполнено"
        )
        
        return stats
    
    def load_default_rules(self, db: Session):
        """Загрузить правила по умолчанию"""
        
        # Правило 1: КП получено → создать задачу на анализ
        rule_kp_received = Rule(
            rule_id="kp_received_task",
            name="Создать задачу при получении КП",
            conditions=[
                RuleCondition(
                    condition_type=RuleConditionType.HAS_ATTACHMENT,
                    params={}
                ),
                RuleCondition(
                    condition_type=RuleConditionType.CUSTOM_LLM_RESULT,
                    params={"llm_result": "kp"}
                )
            ],
            actions=[
                RuleAction(
                    action_type=RuleActionType.CREATE_TASK,
                    params={
                        "priority": "high",
                        "title": "Анализ КП",
                        "description": "Получено коммерческое предложение с вложением",
                        "due_days": 2
                    }
                ),
                RuleAction(
                    action_type=RuleActionType.UPDATE_DIALOGUE_STATUS,
                    params={"status": "kp_received"}
                ),
                RuleAction(
                    action_type=RuleActionType.GENERATE_DRAFT_REPLY,
                    params={}
                )
            ],
            is_active=True,
            priority=100
        )
        
        # Правило 2: Отказ → архивировать
        rule_refusal = Rule(
            rule_id="refusal_archive",
            name="Архивировать при отказе",
            conditions=[
                RuleCondition(
                    condition_type=RuleConditionType.CONTAINS_KEYWORD,
                    params={"keywords": ["не можем", "отказ", "не интересно", "не актуально"]}
                ),
                RuleCondition(
                    condition_type=RuleConditionType.CUSTOM_LLM_RESULT,
                    params={"llm_result": "refusal"}
                )
            ],
            actions=[
                RuleAction(
                    action_type=RuleActionType.UPDATE_DIALOGUE_STATUS,
                    params={"status": "rejected"}
                ),
                RuleAction(
                    action_type=RuleActionType.ARCHIVE,
                    params={}
                )
            ],
            is_active=True,
            priority=90
        )
        
        # Правило 3: Вопрос → создать задачу на ответ
        rule_question = Rule(
            rule_id="question_task",
            name="Создать задачу при вопросе",
            conditions=[
                RuleCondition(
                    condition_type=RuleConditionType.CUSTOM_LLM_RESULT,
                    params={"llm_result": "question"}
                )
            ],
            actions=[
                RuleAction(
                    action_type=RuleActionType.CREATE_TASK,
                    params={
                        "priority": "medium",
                        "title": "Ответить на вопрос поставщика",
                        "description": "Поставщик задал уточняющий вопрос",
                        "due_days": 3
                    }
                ),
                RuleAction(
                    action_type=RuleActionType.UPDATE_DIALOGUE_STATUS,
                    params={"status": "clarifying"}
                ),
                RuleAction(
                    action_type=RuleActionType.GENERATE_DRAFT_REPLY,
                    params={}
                )
            ],
            is_active=True,
            priority=80
        )
        
        # Правило 4: Спам → помечать для проверки
        rule_spam = Rule(
            rule_id="spam_review",
            name="Пометить спам для проверки",
            conditions=[
                RuleCondition(
                    condition_type=RuleConditionType.CUSTOM_LLM_RESULT,
                    params={"llm_result": "spam"}
                )
            ],
            actions=[
                RuleAction(
                    action_type=RuleActionType.FLAG_FOR_REVIEW,
                    params={"priority": "low"}
                ),
                RuleAction(
                    action_type=RuleActionType.UPDATE_DIALOGUE_STATUS,
                    params={"status": "rejected"}
                )
            ],
            is_active=True,
            priority=70
        )
        
        # Правило 5: Автоответ на благодарность
        rule_thank_you = Rule(
            rule_id="auto_thank_reply",
            name="Автоответ на благодарность",
            conditions=[
                RuleCondition(
                    condition_type=RuleConditionType.CONTAINS_KEYWORD,
                    params={"keywords": ["спасибо", "благодарим", "благодарю"]}
                ),
                RuleCondition(
                    condition_type=RuleConditionType.NOT_CONTAINS_KEYWORD,
                    params={"keywords": ["но", "однако", "хотя", "проблема"]}
                )
            ],
            actions=[
                RuleAction(
                    action_type=RuleActionType.SEND_AUTO_REPLY,
                    params={
                        "body": "Добрый день!\n\nБлагодарим за обратную связь. Мы рады сотрудничеству и готовы ответить на любые вопросы.\n\nС уважением,\nВаша компания"
                    }
                ),
                RuleAction(
                    action_type=RuleActionType.UPDATE_DIALOGUE_STATUS,
                    params={"status": "kp_received"}
                )
            ],
            is_active=False,  # Отключено по умолчанию
            priority=60
        )
        
        # Добавить все правила
        self.add_rule(rule_kp_received)
        self.add_rule(rule_refusal)
        self.add_rule(rule_question)
        self.add_rule(rule_spam)
        self.add_rule(rule_thank_you)
        
        logger.info("Загружено 5 правил по умолчанию")
    
    def get_rules_list(self) -> List[Dict]:
        """Получить список всех правил"""
        return [
            {
                "rule_id": rule.rule_id,
                "name": rule.name,
                "is_active": rule.is_active,
                "priority": rule.priority,
                "conditions_count": len(rule.conditions),
                "actions_count": len(rule.actions)
            }
            for rule in self.rules
        ]

    def save_to_db(self, db: Session):
        """
        Сохранить все правила в БД
        
        Args:
            db: Сессия БД
        """
        from core.models import RuleDB
        
        for rule in self.rules:
            # Проверить, существует ли
            existing = db.query(RuleDB).filter_by(rule_id=rule.rule_id).first()
            
            conditions_data = []
            for cond in rule.conditions:
                conditions_data.append({
                    "type": cond.condition_type.value,
                    "params": cond.params
                })
            
            actions_data = []
            for action in rule.actions:
                actions_data.append({
                    "type": action.action_type.value,
                    "params": action.params
                })
            
            if existing:
                existing.name = rule.name
                existing.conditions = conditions_data
                existing.actions = actions_data
                existing.is_active = rule.is_active
                existing.priority = rule.priority
                existing.updated_at = now_utc()
            else:
                db_rule = RuleDB(
                    rule_id=rule.rule_id,
                    name=rule.name,
                    conditions=conditions_data,
                    actions=actions_data,
                    is_active=rule.is_active,
                    priority=rule.priority
                )
                db.add(db_rule)
        
        db.commit()
        logger.info(f"Сохранено {len(self.rules)} правил в БД")
    
    def load_from_db(self, db: Session):
        """
        Загрузить правила из БД
        
        Args:
            db: Сессия БД
        """
        from core.models import RuleDB
        
        db_rules = db.query(RuleDB).order_by(RuleDB.priority.desc()).all()
        
        if not db_rules:
            logger.info("В БД нет правил, загружаю defaults")
            self.load_default_rules(db)
            self.save_to_db(db)
            return
        
        self.rules.clear()
        
        for db_rule in db_rules:
            conditions = [
                RuleCondition(
                    condition_type=RuleConditionType(c["type"]),
                    params=c["params"]
                )
                for c in db_rule.conditions
            ]
            
            actions = [
                RuleAction(
                    action_type=RuleActionType(a["type"]),
                    params=a["params"]
                )
                for a in db_rule.actions
            ]
            
            rule = Rule(
                rule_id=db_rule.rule_id,
                name=db_rule.name,
                conditions=conditions,
                actions=actions,
                is_active=db_rule.is_active,
                priority=db_rule.priority
            )
            
            self.rules.append(rule)
        
        logger.info(f"Загружено {len(self.rules)} правил из БД")
