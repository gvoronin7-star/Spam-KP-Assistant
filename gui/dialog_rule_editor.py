"""
Диалог создания/редактирования правил
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QComboBox, QLineEdit, QSpinBox, QTextEdit, QGroupBox,
    QFormLayout, QListWidget, QListWidgetItem, QMessageBox, QTabWidget,
    QWidget, QCheckBox
)
from PyQt6.QtCore import Qt
from loguru import logger


class DialogRuleEditor(QDialog):
    """
    Диалог создания/редактирования правил Rule Engine
    
    Вкладки:
    - Основное (название, приоритет, статус)
    - Условия (добавление условий)
    - Действия (добавление действий)
    """
    
    def __init__(self, rule=None, parent=None):
        super().__init__(parent)
        self.rule = rule
        self.is_editing = rule is not None
        
        self.conditions = []
        self.actions = []
        
        if self.is_editing:
            # Загрузить существующие данные
            self.conditions = [
                {"type": c.condition_type.value, "params": c.params}
                for c in rule.conditions
            ]
            self.actions = [
                {"type": a.action_type.value, "params": a.params}
                for a in rule.actions
            ]
        
        self.setWindowTitle(
            "Редактировать правило" if self.is_editing else "Создать правило"
        )
        self.setMinimumSize(700, 600)
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Настройка интерфейса"""
        layout = QVBoxLayout(self)
        
        # Вкладки
        tabs = QTabWidget()
        
        # Вкладка 1: Основное
        tab_basic = self._create_basic_tab()
        tabs.addTab(tab_basic, "📝 Основное")
        
        # Вкладка 2: Условия
        tab_conditions = self._create_conditions_tab()
        tabs.addTab(tab_conditions, "✅ Условия")
        
        # Вкладка 3: Действия
        tab_actions = self._create_actions_tab()
        tabs.addTab(tab_actions, "🎯 Действия")
        
        layout.addWidget(tabs)
        
        # Кнопки
        buttons = self._create_buttons()
        layout.addLayout(buttons)
    
    def _create_basic_tab(self) -> QWidget:
        """Вкладка 'Основное'"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Название
        form = QFormLayout()
        
        self.input_name = QLineEdit()
        if self.is_editing:
            self.input_name.setText(self.rule.name)
        form.addRow("Название:", self.input_name)
        
        self.input_rule_id = QLineEdit()
        if self.is_editing:
            self.input_rule_id.setText(self.rule.rule_id)
            self.input_rule_id.setEnabled(False)
        else:
            self.input_rule_id.setPlaceholderText("unique_rule_id")
        form.addRow("ID правила:", self.input_rule_id)
        
        # Приоритет
        self.input_priority = QSpinBox()
        self.input_priority.setRange(0, 1000)
        self.input_priority.setValue(self.rule.priority if self.is_editing else 100)
        form.addRow("Приоритет (0-1000):", self.input_priority)
        
        # Статус
        self.check_active = QCheckBox("Активно")
        self.check_active.setChecked(self.rule.is_active if self.is_editing else True)
        layout.addWidget(self.check_active)
        
        layout.addLayout(form)
        layout.addStretch()
        
        return widget
    
    def _create_conditions_tab(self) -> QWidget:
        """Вкладка 'Условия'"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Список условий
        self.list_conditions = QListWidget()
        self.list_conditions.itemSelectionChanged.connect(self._on_condition_selected)
        layout.addWidget(self.list_conditions)
        
        # Кнопки управления условиями
        cond_buttons = QHBoxLayout()
        
        btn_add = QPushButton("➕ Добавить условие")
        btn_add.clicked.connect(self._add_condition)
        cond_buttons.addWidget(btn_add)
        
        btn_edit = QPushButton("✏️ Редактировать")
        btn_edit.clicked.connect(self._edit_condition)
        btn_edit.setEnabled(False)
        self.btn_edit_condition = btn_edit
        cond_buttons.addWidget(btn_edit)
        
        btn_remove = QPushButton("🗑️ Удалить")
        btn_remove.clicked.connect(self._remove_condition)
        btn_remove.setEnabled(False)
        self.btn_remove_condition = btn_remove
        cond_buttons.addWidget(btn_remove)
        
        layout.addLayout(cond_buttons)
        
        return widget
    
    def _create_actions_tab(self) -> QWidget:
        """Вкладка 'Действия'"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Список действий
        self.list_actions = QListWidget()
        self.list_actions.itemSelectionChanged.connect(self._on_action_selected)
        layout.addWidget(self.list_actions)
        
        # Кнопки управления действиями
        act_buttons = QHBoxLayout()
        
        btn_add = QPushButton("➕ Добавить действие")
        btn_add.clicked.connect(self._add_action)
        act_buttons.addWidget(btn_add)
        
        btn_edit = QPushButton("✏️ Редактировать")
        btn_edit.clicked.connect(self._edit_action)
        btn_edit.setEnabled(False)
        self.btn_edit_action = btn_edit
        act_buttons.addWidget(btn_edit)
        
        btn_remove = QPushButton("🗑️ Удалить")
        btn_remove.clicked.connect(self._remove_action)
        btn_remove.setEnabled(False)
        self.btn_remove_action = btn_remove
        act_buttons.addWidget(btn_remove)
        
        layout.addLayout(act_buttons)
        
        return widget
    
    def _create_buttons(self) -> QHBoxLayout:
        """Кнопки диалога"""
        layout = QHBoxLayout()
        
        layout.addStretch()
        
        btn_ok = QPushButton("OK")
        btn_ok.clicked.connect(self._on_ok)
        layout.addWidget(btn_ok)
        
        btn_cancel = QPushButton("Отмена")
        btn_cancel.clicked.connect(self.reject)
        layout.addWidget(btn_cancel)
        
        return layout
    
    def _load_conditions_list(self):
        """Загрузить список условий"""
        self.list_conditions.clear()
        
        for cond in self.conditions:
            type_str = cond["type"]
            params_str = ", ".join([f"{k}={v}" for k, v in cond["params"].items()])
            
            item_text = f"🔹 {type_str}: {params_str}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, cond)
            
            self.list_conditions.addItem(item)
    
    def _load_actions_list(self):
        """Загрузить список действий"""
        self.list_actions.clear()
        
        for act in self.actions:
            type_str = act["type"]
            params_str = ", ".join([f"{k}={v}" for k, v in act["params"].items()])
            
            item_text = f"🎯 {type_str}: {params_str}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, act)
            
            self.list_actions.addItem(item)
    
    def _on_condition_selected(self):
        """Выбор условия"""
        selected = self.list_conditions.selectedItems()
        enabled = len(selected) > 0
        
        self.btn_edit_condition.setEnabled(enabled)
        self.btn_remove_condition.setEnabled(enabled)
    
    def _on_action_selected(self):
        """Выбор действия"""
        selected = self.list_actions.selectedItems()
        enabled = len(selected) > 0
        
        self.btn_edit_action.setEnabled(enabled)
        self.btn_remove_action.setEnabled(enabled)
    
    def _add_condition(self):
        """Добавить условие"""
        from .dialog_condition_editor import DialogConditionEditor
        
        dialog = DialogConditionEditor(parent=self)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            cond_data = dialog.get_condition_data()
            self.conditions.append(cond_data)
            self._load_conditions_list()
    
    def _edit_condition(self):
        """Редактировать условие"""
        item = self.list_conditions.currentItem()
        if not item:
            return
        
        cond_data = item.data(Qt.ItemDataRole.UserRole)
        
        from .dialog_condition_editor import DialogConditionEditor
        
        dialog = DialogConditionEditor(condition_data=cond_data, parent=self)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            cond_data = dialog.get_condition_data()
            
            # Обновить в списке
            index = self.list_conditions.currentRow()
            self.conditions[index] = cond_data
            self._load_conditions_list()
    
    def _remove_condition(self):
        """Удалить условие"""
        item = self.list_conditions.currentItem()
        if not item:
            return
        
        index = self.list_conditions.currentRow()
        self.conditions.pop(index)
        self._load_conditions_list()
    
    def _add_action(self):
        """Добавить действие"""
        from .dialog_action_editor import DialogActionEditor
        
        dialog = DialogActionEditor(parent=self)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            act_data = dialog.get_action_data()
            self.actions.append(act_data)
            self._load_actions_list()
    
    def _edit_action(self):
        """Редактировать действие"""
        item = self.list_actions.currentItem()
        if not item:
            return
        
        act_data = item.data(Qt.ItemDataRole.UserRole)
        
        from .dialog_action_editor import DialogActionEditor
        
        dialog = DialogActionEditor(action_data=act_data, parent=self)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            act_data = dialog.get_action_data()
            
            # Обновить в списке
            index = self.list_actions.currentRow()
            self.actions[index] = act_data
            self._load_actions_list()
    
    def _remove_action(self):
        """Удалить действие"""
        item = self.list_actions.currentItem()
        if not item:
            return
        
        index = self.list_actions.currentRow()
        self.actions.pop(index)
        self._load_actions_list()
    
    def _on_ok(self):
        """OK — сохранить правило"""
        # Проверка названия
        name = self.input_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Ошибка", "Введите название правила")
            return
        
        # Проверка ID
        rule_id = self.input_rule_id.text().strip()
        if not rule_id:
            QMessageBox.warning(self, "Ошибка", "Введите ID правила")
            return
        
        # Проверка условий и действий
        if len(self.conditions) == 0:
            QMessageBox.warning(self, "Ошибка", "Добавьте хотя бы одно условие")
            return
        
        if len(self.actions) == 0:
            QMessageBox.warning(self, "Ошибка", "Добавьте хотя бы одно действие")
            return
        
        # Сохранить данные
        self.rule_data = {
            "rule_id": rule_id,
            "name": name,
            "priority": self.input_priority.value(),
            "is_active": self.check_active.isChecked(),
            "conditions": self.conditions,
            "actions": self.actions
        }
        
        self.accept()
    
    def get_rule_data(self):
        """Получить данные правила"""
        return self.rule_data
