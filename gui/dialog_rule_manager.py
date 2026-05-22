"""
Диалог управления правилами (Rule Engine GUI)
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QListWidget, QListWidgetItem, QMessageBox, QGroupBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QSplitter
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from loguru import logger


class DialogRuleManager(QDialog):
    """
    Диалог управления правилами Rule Engine
    
    Функции:
    - Просмотр всех правил
    - Включение/отключение правил
    - Создание кастомных правил
    - Удаление правил
    - Изменение приоритетов
    """
    
    def __init__(self, rule_engine, parent=None):
        super().__init__(parent)
        self.rule_engine = rule_engine
        
        self.setWindowTitle("Управление правилами (Rule Engine)")
        self.setMinimumSize(900, 600)
        
        self._setup_ui()
        self._load_rules()
        
        logger.info("DialogRuleManager открыт")
    
    def _setup_ui(self):
        """Настройка интерфейса"""
        layout = QVBoxLayout(self)
        
        # Заголовок
        header = QLabel("📋 Управление правилами автоматизации")
        header.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        layout.addWidget(header)
        
        # Разделитель
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Левая панель — список правил
        left_panel = self._create_rules_list()
        splitter.addWidget(left_panel)
        
        # Правая панель — детали и действия
        right_panel = self._create_details_panel()
        splitter.addWidget(right_panel)
        
        splitter.setSizes([300, 600])
        layout.addWidget(splitter)
        
        # Кнопки управления
        buttons = self._create_buttons()
        layout.addLayout(buttons)
    
    def _create_rules_list(self) -> QGroupBox:
        """Создание списка правил"""
        group = QGroupBox("Список правил")
        layout = QVBoxLayout()
        
        # Список правил
        self.rules_list = QListWidget()
        self.rules_list.itemClicked.connect(self._on_rule_selected)
        layout.addWidget(self.rules_list)
        
        # Счётчик
        self.lbl_rule_count = QLabel("Всего правил: 0")
        layout.addWidget(self.lbl_rule_count)
        
        group.setLayout(layout)
        return group
    
    def _create_details_panel(self) -> QGroupBox:
        """Панель деталей правила"""
        group = QGroupBox("Детали правила")
        layout = QVBoxLayout()
        
        # Название правила
        self.lbl_rule_name = QLabel("-")
        self.lbl_rule_name.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout.addWidget(self.lbl_rule_name)
        
        # Статус
        self.lbl_rule_status = QLabel("Статус: -")
        layout.addWidget(self.lbl_rule_status)
        
        # Приоритет
        self.lbl_rule_priority = QLabel("Приоритет: -")
        layout.addWidget(self.lbl_rule_priority)
        
        # Разделитель
        layout.addSpacing(10)
        
        # Условия
        conditions_group = QGroupBox("Условия")
        conditions_layout = QVBoxLayout()
        self.table_conditions = QTableWidget()
        self.table_conditions.setColumnCount(3)
        self.table_conditions.setHorizontalHeaderLabels(["Тип", "Параметры", ""])
        self.table_conditions.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        conditions_layout.addWidget(self.table_conditions)
        conditions_group.setLayout(conditions_layout)
        layout.addWidget(conditions_group)
        
        # Разделитель
        layout.addSpacing(10)
        
        # Действия
        actions_group = QGroupBox("Действия")
        actions_layout = QVBoxLayout()
        self.table_actions = QTableWidget()
        self.table_actions.setColumnCount(2)
        self.table_actions.setHorizontalHeaderLabels(["Тип", "Параметры"])
        self.table_actions.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        actions_layout.addWidget(self.table_actions)
        actions_group.setLayout(actions_layout)
        layout.addWidget(actions_group)
        
        layout.addStretch()
        group.setLayout(layout)
        
        return group
    
    def _create_buttons(self) -> QHBoxLayout:
        """Кнопки управления"""
        layout = QHBoxLayout()
        
        # Кнопка создать правило
        self.btn_add_rule = QPushButton("➕ Создать правило")
        self.btn_add_rule.clicked.connect(self._create_new_rule)
        layout.addWidget(self.btn_add_rule)
        
        # Кнопка редактировать
        self.btn_edit_rule = QPushButton("✏️ Редактировать")
        self.btn_edit_rule.clicked.connect(self._edit_rule)
        self.btn_edit_rule.setEnabled(False)
        layout.addWidget(self.btn_edit_rule)
        
        # Кнопка удалить
        self.btn_delete_rule = QPushButton("🗑️ Удалить")
        self.btn_delete_rule.clicked.connect(self._delete_rule)
        self.btn_delete_rule.setEnabled(False)
        layout.addWidget(self.btn_delete_rule)
        
        layout.addStretch()
        
        # Кнопка закрыть
        self.btn_close = QPushButton("Закрыть")
        self.btn_close.clicked.connect(self.accept)
        layout.addWidget(self.btn_close)
        
        return layout
    
    def _load_rules(self):
        """Загрузка правил из RuleEngine"""
        self.rules_list.clear()
        
        rules = self.rule_engine.get_rules_list()
        
        for rule in rules:
            # Иконка статуса
            status_icon = "✅" if rule["is_active"] else "⏸️"
            
            # Приоритет
            priority_icon = {
                100: "🔴",
                90: "🟠",
                80: "🟡",
                70: "🟢",
                60: "🔵"
            }.get(rule["priority"], "⚪")
            
            item_text = f"{status_icon} {priority_icon} {rule['name']}"
            
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, rule["rule_id"])
            
            # Подсветка активных/неактивных
            if not rule["is_active"]:
                item.setForeground(Qt.GlobalColor.gray)
            
            self.rules_list.addItem(item)
        
        self.lbl_rule_count.setText(f"Всего правил: {len(rules)}")
        
        logger.info(f"Загружено {len(rules)} правил")
    
    def _on_rule_selected(self, item):
        """Выбор правила в списке"""
        rule_id = item.data(Qt.ItemDataRole.UserRole)
        
        # Найти правило
        rule = None
        for r in self.rule_engine.rules:
            if r.rule_id == rule_id:
                rule = r
                break
        
        if not rule:
            return
        
        # Включить кнопки редактирования/удаления
        self.btn_edit_rule.setEnabled(True)
        self.btn_delete_rule.setEnabled(True)
        
        # Показать детали
        self._show_rule_details(rule)
    
    def _show_rule_details(self, rule):
        """Показать детали правила"""
        # Название
        self.lbl_rule_name.setText(rule.name)
        
        # Статус
        status = "Активно" if rule.is_active else "Отключено"
        status_color = "green" if rule.is_active else "gray"
        self.lbl_rule_status.setText(f"Статус: <span style='color: {status_color}'>{status}</span>")
        
        # Приоритет
        self.lbl_rule_priority.setText(f"Приоритет: {rule.priority}")
        
        # Условия
        self.table_conditions.setRowCount(len(rule.conditions))
        for i, condition in enumerate(rule.conditions):
            self.table_conditions.setItem(i, 0, QTableWidgetItem(str(condition.condition_type.value)))
            
            params_str = ", ".join([f"{k}={v}" for k, v in condition.params.items()])
            self.table_conditions.setItem(i, 1, QTableWidgetItem(params_str))
        
        # Действия
        self.table_actions.setRowCount(len(rule.actions))
        for i, action in enumerate(rule.actions):
            self.table_actions.setItem(i, 0, QTableWidgetItem(str(action.action_type.value)))
            
            params_str = ", ".join([f"{k}={v}" for k, v in action.params.items()])
            self.table_actions.setItem(i, 1, QTableWidgetItem(params_str))
    
    def _create_new_rule(self):
        """Создание нового правила"""
        from .dialog_rule_editor import DialogRuleEditor
        
        dialog = DialogRuleEditor(parent=self)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            rule_data = dialog.get_rule_data()
            
            # Создать правило
            from services.rule_engine import Rule, RuleCondition, RuleAction, RuleConditionType, RuleActionType
            
            conditions = []
            for cond in rule_data["conditions"]:
                conditions.append(RuleCondition(
                    condition_type=RuleConditionType(cond["type"]),
                    params=cond["params"]
                ))
            
            actions = []
            for act in rule_data["actions"]:
                actions.append(RuleAction(
                    action_type=RuleActionType(act["type"]),
                    params=act["params"]
                ))
            
            rule = Rule(
                rule_id=rule_data["rule_id"],
                name=rule_data["name"],
                conditions=conditions,
                actions=actions,
                is_active=rule_data["is_active"],
                priority=rule_data["priority"]
            )
            
            self.rule_engine.add_rule(rule)
            
            # Обновить список
            self._load_rules()
            
            QMessageBox.information(
                self,
                "Успех",
                f"Правило '{rule.name}' создано!"
            )
            
            logger.info(f"Создано правило: {rule.name}")
    
    def _edit_rule(self):
        """Редактирование правила"""
        item = self.rules_list.currentItem()
        if not item:
            return
        
        rule_id = item.data(Qt.ItemDataRole.UserRole)
        
        # Найти правило
        rule = None
        for r in self.rule_engine.rules:
            if r.rule_id == rule_id:
                rule = r
                break
        
        if not rule:
            QMessageBox.warning(self, "Ошибка", "Правило не найдено")
            return
        
        from .dialog_rule_editor import DialogRuleEditor
        
        dialog = DialogRuleEditor(rule=rule, parent=self)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            rule_data = dialog.get_rule_data()
            
            # Удалить старое правило
            self.rule_engine.remove_rule(rule_id)
            
            # Создать обновлённое
            from services.rule_engine import Rule, RuleCondition, RuleAction, RuleConditionType, RuleActionType
            
            conditions = []
            for cond in rule_data["conditions"]:
                conditions.append(RuleCondition(
                    condition_type=RuleConditionType(cond["type"]),
                    params=cond["params"]
                ))
            
            actions = []
            for act in rule_data["actions"]:
                actions.append(RuleAction(
                    action_type=RuleActionType(act["type"]),
                    params=act["params"]
                ))
            
            new_rule = Rule(
                rule_id=rule_data["rule_id"],
                name=rule_data["name"],
                conditions=conditions,
                actions=actions,
                is_active=rule_data["is_active"],
                priority=rule_data["priority"]
            )
            
            self.rule_engine.add_rule(new_rule)
            
            # Обновить список
            self._load_rules()
            
            QMessageBox.information(
                self,
                "Успех",
                f"Правило '{rule_data['name']}' обновлено!"
            )
            
            logger.info(f"Обновлено правило: {rule_data['name']}")
    
    def _delete_rule(self):
        """Удаление правила"""
        item = self.rules_list.currentItem()
        if not item:
            return
        
        rule_id = item.data(Qt.ItemDataRole.UserRole)
        
        # Найти правило
        rule = None
        for r in self.rule_engine.rules:
            if r.rule_id == rule_id:
                rule = r
                break
        
        if not rule:
            return
        
        # Подтверждение
        reply = QMessageBox.question(
            self,
            "Подтверждение",
            f"Вы уверены, что хотите удалить правило '{rule.name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.rule_engine.remove_rule(rule_id)
            self._load_rules()
            
            # Сбросить детали
            self.lbl_rule_name.setText("-")
            self.lbl_rule_status.setText("Статус: -")
            self.lbl_rule_priority.setText("Приоритет: -")
            self.table_conditions.setRowCount(0)
            self.table_actions.setRowCount(0)
            self.btn_edit_rule.setEnabled(False)
            self.btn_delete_rule.setEnabled(False)
            
            logger.info(f"Удалено правило: {rule.name}")
