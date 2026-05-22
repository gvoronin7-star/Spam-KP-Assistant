"""
Тесты для сохранения/загрузки Rule Engine в БД
"""
import pytest
from services.rule_engine import RuleEngine, Rule, RuleCondition, RuleAction
from services.rule_engine import RuleConditionType, RuleActionType
from core.models import RuleDB


class TestRuleEngineDB:
    """Тесты сохранения/загрузки правил в БД"""
    
    def test_save_to_db(self, test_db):
        """Сохранение правил в БД"""
        engine = RuleEngine()
        engine.load_default_rules(test_db)
        
        # Сохранить
        engine.save_to_db(test_db)
        
        # Проверить в БД
        db_rules = test_db.query(RuleDB).all()
        assert len(db_rules) == 5
        
        rule = test_db.query(RuleDB).filter_by(rule_id="kp_received_task").first()
        assert rule is not None
        assert rule.name == "Создать задачу при получении КП"
        assert rule.is_active is True
        assert rule.priority == 100
        assert len(rule.conditions) == 2
        assert len(rule.actions) == 3
    
    def test_load_from_db(self, test_db):
        """Загрузка правил из БД"""
        # Сначала сохранить
        engine1 = RuleEngine()
        engine1.load_default_rules(test_db)
        engine1.save_to_db(test_db)
        
        # Затем загрузить в новый engine
        engine2 = RuleEngine()
        engine2.load_from_db(test_db)
        
        assert len(engine2.rules) == 5
        
        rule = next((r for r in engine2.rules if r.rule_id == "refusal_archive"), None)
        assert rule is not None
        assert rule.name == "Архивировать при отказе"
        assert rule.priority == 90
    
    def test_load_from_empty_db_loads_defaults(self, test_db):
        """При пустой БД загружаются defaults"""
        engine = RuleEngine()
        engine.load_from_db(test_db)
        
        assert len(engine.rules) == 5
        
        # Проверить, что сохранились в БД
        db_rules = test_db.query(RuleDB).all()
        assert len(db_rules) == 5
    
    def test_update_existing_rule(self, test_db):
        """Обновление существующего правила"""
        engine = RuleEngine()
        engine.load_default_rules(test_db)
        engine.save_to_db(test_db)
        
        # Изменить правило
        rule = next(r for r in engine.rules if r.rule_id == "spam_review")
        rule.name = "Обновлённое имя"
        rule.is_active = False
        
        # Сохранить снова
        engine.save_to_db(test_db)
        
        # Проверить обновление
        db_rule = test_db.query(RuleDB).filter_by(rule_id="spam_review").first()
        assert db_rule.name == "Обновлённое имя"
        assert db_rule.is_active is False
    
    def test_add_custom_rule_and_save(self, test_db):
        """Добавление кастомного правила и сохранение"""
        engine = RuleEngine()
        engine.load_default_rules(test_db)
        
        custom_rule = Rule(
            rule_id="custom_test",
            name="Тестовое правило",
            conditions=[
                RuleCondition(
                    RuleConditionType.CONTAINS_KEYWORD,
                    {"keywords": ["тест"]}
                )
            ],
            actions=[
                RuleAction(
                    RuleActionType.NOTIFY_OPERATOR,
                    {"title": "Тест"}
                )
            ],
            priority=50
        )
        engine.add_rule(custom_rule)
        engine.save_to_db(test_db)
        
        # Загрузить в новый engine
        engine2 = RuleEngine()
        engine2.load_from_db(test_db)
        
        rule = next((r for r in engine2.rules if r.rule_id == "custom_test"), None)
        assert rule is not None
        assert rule.name == "Тестовое правило"
        assert rule.priority == 50
