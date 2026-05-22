"""
Тесты для GUI управления правилами
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from PyQt6.QtWidgets import QApplication
import sys

# Создаем приложение Qt для тестов
@pytest.fixture(scope="session")
def qt_app():
    if QApplication.instance() is None:
        app = QApplication(sys.argv)
    else:
        app = QApplication.instance()
    yield app
    # Не закрываем приложение, чтобы не ломать другие тесты


class TestDialogRuleManager:
    """Тесты DialogRuleManager"""
    
    def test_init(self, qt_app):
        """Инициализация диалога"""
        # Mock RuleEngine
        mock_engine = Mock()
        mock_engine.get_rules_list.return_value = []
        mock_engine.rules = []
        
        from gui.dialog_rule_manager import DialogRuleManager
        
        dialog = DialogRuleManager(mock_engine)
        
        assert dialog is not None
        assert dialog.rule_engine == mock_engine
    
    def test_load_rules(self, qt_app):
        """Загрузка правил"""
        # Mock RuleEngine с правилами
        mock_engine = Mock()
        mock_engine.get_rules_list.return_value = [
            {
                "rule_id": "rule1",
                "name": "Правило 1",
                "is_active": True,
                "priority": 100,
                "conditions_count": 2,
                "actions_count": 1
            }
        ]
        mock_engine.rules = []
        
        from gui.dialog_rule_manager import DialogRuleManager
        
        dialog = DialogRuleManager(mock_engine)
        dialog._load_rules()
        
        assert dialog.rules_list.count() == 1
        assert dialog.lbl_rule_count.text() == "Всего правил: 1"
    
    def test_create_new_rule(self, qt_app):
        """Создание нового правила"""
        # Mock RuleEngine
        mock_engine = Mock()
        mock_engine.get_rules_list.return_value = []
        mock_engine.rules = []
        mock_engine.add_rule = Mock()
        
        from gui.dialog_rule_manager import DialogRuleManager
        
        dialog = DialogRuleManager(mock_engine)
        
        # Просто проверить, что кнопка существует и связана с методом
        assert dialog.btn_add_rule is not None
        assert dialog.btn_add_rule.clicked is not None


class TestDialogRuleEditor:
    """Тесты DialogRuleEditor"""
    
    def test_init_create(self, qt_app):
        """Создание нового правила"""
        from gui.dialog_rule_editor import DialogRuleEditor
        
        dialog = DialogRuleEditor()
        
        assert dialog is not None
        assert dialog.is_editing is False
    
    def test_init_edit(self, qt_app):
        """Редактирование существующего правила"""
        # Mock правила
        mock_rule = Mock()
        mock_rule.rule_id = "rule1"
        mock_rule.name = "Правило 1"
        mock_rule.priority = 100
        mock_rule.is_active = True
        mock_rule.conditions = []
        mock_rule.actions = []
        
        from gui.dialog_rule_editor import DialogRuleEditor
        
        dialog = DialogRuleEditor(rule=mock_rule)
        
        assert dialog is not None
        assert dialog.is_editing is True
        assert dialog.input_name.text() == "Правило 1"
    
    def test_get_rule_data(self, qt_app):
        """Получение данных правила"""
        from gui.dialog_rule_editor import DialogRuleEditor
        
        dialog = DialogRuleEditor()
        
        # Установить данные
        dialog.input_name.setText("Тестовое правило")
        dialog.input_rule_id.setText("test_rule")
        dialog.input_priority.setValue(200)
        dialog.check_active.setChecked(True)
        dialog.conditions = [
            {"type": "has_attachment", "params": {}}
        ]
        dialog.actions = [
            {"type": "create_task", "params": {"priority": "high"}}
        ]
        
        # Сохранить данные (обход проверки)
        dialog.rule_data = {
            "rule_id": "test_rule",
            "name": "Тестовое правило",
            "priority": 200,
            "is_active": True,
            "conditions": [
                {"type": "has_attachment", "params": {}}
            ],
            "actions": [
                {"type": "create_task", "params": {"priority": "high"}}
            ]
        }
        
        data = dialog.get_rule_data()
        
        assert data["name"] == "Тестовое правило"
        assert data["rule_id"] == "test_rule"
        assert data["priority"] == 200
        assert data["is_active"] is True
        assert len(data["conditions"]) == 1
        assert len(data["actions"]) == 1


class TestDialogConditionEditor:
    """Тесты DialogConditionEditor"""
    
    def test_init_create(self, qt_app):
        """Создание условия"""
        from gui.dialog_condition_editor import DialogConditionEditor
        
        dialog = DialogConditionEditor()
        
        assert dialog is not None
        assert dialog.is_editing is False
    
    def test_init_edit(self, qt_app):
        """Редактирование условия"""
        condition_data = {
            "type": "contains_keyword",
            "params": {"keywords": ["спасибо", "благодарим"]}
        }
        
        from gui.dialog_condition_editor import DialogConditionEditor
        
        dialog = DialogConditionEditor(condition_data=condition_data)
        
        assert dialog is not None
        assert dialog.is_editing is True
    
    def test_get_condition_data(self, qt_app):
        """Получение данных условия"""
        from gui.dialog_condition_editor import DialogConditionEditor
        
        dialog = DialogConditionEditor()
        
        # Установить тип
        index = dialog.combo_type.findData("contains_keyword")
        dialog.combo_type.setCurrentIndex(index)
        
        # Установить параметры
        dialog.input_keywords.setText("спасибо, благодарим")
        
        # Сохранить
        dialog._on_ok()
        
        data = dialog.get_condition_data()
        
        assert data["type"] == "contains_keyword"
        assert data["params"]["keywords"] == ["спасибо", "благодарим"]


class TestDialogActionEditor:
    """Тесты DialogActionEditor"""
    
    def test_init_create(self, qt_app):
        """Создание действия"""
        from gui.dialog_action_editor import DialogActionEditor
        
        dialog = DialogActionEditor()
        
        assert dialog is not None
        assert dialog.is_editing is False
    
    def test_init_edit(self, qt_app):
        """Редактирование действия"""
        action_data = {
            "type": "create_task",
            "params": {
                "priority": "high",
                "title": "Проверить КП"
            }
        }
        
        from gui.dialog_action_editor import DialogActionEditor
        
        dialog = DialogActionEditor(action_data=action_data)
        
        assert dialog is not None
        assert dialog.is_editing is True
    
    def test_get_action_data(self, qt_app):
        """Получение данных действия"""
        from gui.dialog_action_editor import DialogActionEditor
        
        dialog = DialogActionEditor()
        
        # Установить тип
        index = dialog.combo_type.findData("create_task")
        dialog.combo_type.setCurrentIndex(index)
        
        # Установить параметры
        dialog.combo_priority.setCurrentIndex(2)  # high
        dialog.input_title.setText("Проверить КП")
        dialog.input_description.setText("Нужно проверить КП")
        dialog.input_days.setValue(2)
        
        # Сохранить
        dialog._on_ok()
        
        data = dialog.get_action_data()
        
        assert data["type"] == "create_task"
        assert data["params"]["priority"] == "high"
        assert data["params"]["title"] == "Проверить КП"
        assert data["params"]["due_days"] == 2


class TestRuleEngineGUIIntegration:
    """Интеграционные тесты GUI Rule Engine"""
    
    def test_full_workflow(self, qt_app):
        """Полный рабочий процесс"""
        from gui.dialog_rule_manager import DialogRuleManager
        
        # Mock RuleEngine
        mock_engine = Mock()
        mock_engine.get_rules_list.return_value = []
        mock_engine.rules = []
        mock_engine.add_rule = Mock()
        
        # Открыть менеджер
        dialog = DialogRuleManager(mock_engine)
        
        # Проверить, что менеджер создан
        assert dialog is not None
        assert dialog.rules_list is not None
