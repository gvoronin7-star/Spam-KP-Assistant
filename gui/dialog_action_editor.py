"""
Диалог редактирования действия правила
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QComboBox, QLineEdit, QSpinBox, QTextEdit, QGroupBox,
    QFormLayout, QMessageBox
)
from PyQt6.QtCore import Qt
from services.rule_engine import RuleActionType


class DialogActionEditor(QDialog):
    """
    Диалог создания/редактирования действия правила
    
    Поля:
    - Тип действия
    - Параметры (зависят от типа)
    """
    
    def __init__(self, action_data=None, parent=None):
        super().__init__(parent)
        self.action_data = action_data
        self.is_editing = action_data is not None
        
        self.setWindowTitle(
            "Редактировать действие" if self.is_editing else "Создать действие"
        )
        self.setMinimumSize(500, 450)
        
        self._setup_ui()
        
        if self.is_editing:
            self._load_data(action_data)
    
    def _setup_ui(self):
        """Настройка интерфейса"""
        layout = QVBoxLayout(self)
        
        # Тип действия
        form = QFormLayout()
        
        self.combo_type = QComboBox()
        for action_type in RuleActionType:
            self.combo_type.addItem(action_type.value, action_type.value)
        
        if self.is_editing:
            index = self.combo_type.findData(self.action_data["type"])
            if index >= 0:
                self.combo_type.setCurrentIndex(index)
        
        self.combo_type.currentIndexChanged.connect(self._on_type_changed)
        form.addRow("Тип действия:", self.combo_type)
        
        layout.addLayout(form)
        
        # Параметры (динамические)
        self.params_group = QGroupBox("Параметры")
        self.params_layout = QVBoxLayout()
        self.params_group.setLayout(self.params_layout)
        layout.addWidget(self.params_group)
        
        # Кнопки
        buttons = QHBoxLayout()
        buttons.addStretch()
        
        btn_ok = QPushButton("OK")
        btn_ok.clicked.connect(self._on_ok)
        buttons.addWidget(btn_ok)
        
        btn_cancel = QPushButton("Отмена")
        btn_cancel.clicked.connect(self.reject)
        buttons.addWidget(btn_cancel)
        
        layout.addLayout(buttons)
        
        # Инициализировать параметры
        self._init_params_widgets()
    
    def _load_data(self, data):
        """Загрузить данные"""
        index = self.combo_type.findData(data["type"])
        if index >= 0:
            self.combo_type.setCurrentIndex(index)
        
        self.params_data = data["params"]
    
    def _on_type_changed(self, index):
        """Изменение типа действия"""
        self._init_params_widgets()
    
    def _init_params_widgets(self):
        """Инициализировать виджеты параметров"""
        # Очистить старые
        while self.params_layout.count():
            child = self.params_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # Получаем текущий тип
        type_str = self.combo_type.currentData()
        
        # Параметры в зависимости от типа
        if type_str == "create_task":
            self._create_task_params()
        
        elif type_str == "update_dialogue_status":
            self._create_status_param()
        
        elif type_str == "send_auto_reply":
            self._create_reply_body_param()
        
        elif type_str == "generate_draft_reply":
            # Нет параметров
            label = QLabel("🤖 Автоматическая генерация ответа через LLM")
            label.setStyleSheet("color: gray;")
            self.params_layout.addWidget(label)
        
        elif type_str == "flag_for_review":
            self._create_priority_param()
        
        elif type_str in ["archive", "notify_operator"]:
            # Нет параметров
            label = QLabel("Нет дополнительных параметров")
            self.params_layout.addWidget(label)
        
        else:
            label = QLabel("Нет параметров для этого типа")
            self.params_layout.addWidget(label)
        
    def _create_task_params(self):
        """Параметры для create_task"""
        form = QFormLayout()
        
        # Приоритет
        self.combo_priority = QComboBox()
        priorities = [
            ("low", "🔵 Низкий"),
            ("medium", "🟡 Средний"),
            ("high", "🔴 Высокий"),
            ("critical", "🚨 Критический")
        ]
        for value, display in priorities:
            self.combo_priority.addItem(display, value)
        
        if hasattr(self, 'params_data') and "priority" in self.params_data:
            index = self.combo_priority.findData(self.params_data["priority"])
            if index >= 0:
                self.combo_priority.setCurrentIndex(index)
        
        form.addRow("Приоритет:", self.combo_priority)
        
        # Название
        self.input_title = QLineEdit()
        if hasattr(self, 'params_data') and "title" in self.params_data:
            self.input_title.setText(self.params_data["title"])
        self.input_title.setPlaceholderText("Название задачи")
        form.addRow("Название:", self.input_title)
        
        # Описание
        self.input_description = QTextEdit()
        self.input_description.setMaximumHeight(80)
        if hasattr(self, 'params_data') and "description" in self.params_data:
            self.input_description.setText(self.params_data["description"])
        self.input_description.setPlaceholderText("Описание задачи")
        form.addRow("Описание:", self.input_description)
        
        # Дедлайн (дни)
        self.input_days = QSpinBox()
        self.input_days.setRange(1, 30)
        self.input_days.setValue(3)
        if hasattr(self, 'params_data') and "due_days" in self.params_data:
            self.input_days.setValue(self.params_data["due_days"])
        form.addRow("Дедлайн (дни):", self.input_days)
        
        self.params_layout.addLayout(form)
    
    def _create_status_param(self):
        """Параметр: статус диалога"""
        form = QFormLayout()
        
        self.combo_status = QComboBox()
        statuses = [
            ("sent", "📤 Отправлено"),
            ("clarifying", "❓ Уточнение"),
            ("kp_received", "📥 КП получено"),
            ("rejected", "❌ Отказ"),
            ("reminder_sent", "⏰ Напоминание"),
            ("auto_replied", "🤖 Автоответ"),
            ("spam", "🗑️ Спам"),
            ("archived", "📦 Архив")
        ]
        for value, display in statuses:
            self.combo_status.addItem(display, value)
        
        if hasattr(self, 'params_data') and "status" in self.params_data:
            index = self.combo_status.findData(self.params_data["status"])
            if index >= 0:
                self.combo_status.setCurrentIndex(index)
        
        form.addRow("Новый статус:", self.combo_status)
        self.params_layout.addLayout(form)
    
    def _create_reply_body_param(self):
        """Параметр: тело автоответа"""
        form = QFormLayout()
        
        self.input_body = QTextEdit()
        self.input_body.setMaximumHeight(200)
        if hasattr(self, 'params_data') and "body" in self.params_data:
            self.input_body.setText(self.params_data["body"])
        else:
            self.input_body.setPlaceholderText(
                "Добрый день!\n\n"
                "Спасибо за ваше сообщение. Мы изучим его и ответим в ближайшее время.\n\n"
                "С уважением,\nВаша компания"
            )
        
        form.addRow("Текст ответа:", self.input_body)
        self.params_layout.addLayout(form)
    
    def _create_priority_param(self):
        """Параметр: приоритет"""
        form = QFormLayout()
        
        self.combo_priority = QComboBox()
        priorities = [
            ("low", "🔵 Низкий"),
            ("medium", "🟡 Средний"),
            ("high", "🔴 Высокий")
        ]
        for value, display in priorities:
            self.combo_priority.addItem(display, value)
        
        if hasattr(self, 'params_data') and "priority" in self.params_data:
            index = self.combo_priority.findData(self.params_data["priority"])
            if index >= 0:
                self.combo_priority.setCurrentIndex(index)
        
        form.addRow("Приоритет:", self.combo_priority)
        self.params_layout.addLayout(form)
    
    def _on_ok(self):
        """OK — сохранить действие"""
        type_str = self.combo_type.currentData()
        
        # Собрать параметры
        params = {}
        
        if type_str == "create_task":
            title = self.input_title.text().strip()
            if not title:
                QMessageBox.warning(self, "Ошибка", "Введите название задачи")
                return
            
            params["priority"] = self.combo_priority.currentData()
            params["title"] = title
            params["description"] = self.input_description.toPlainText().strip()
            params["due_days"] = self.input_days.value()
        
        elif type_str == "update_dialogue_status":
            params["status"] = self.combo_status.currentData()
        
        elif type_str == "send_auto_reply":
            body = self.input_body.toPlainText().strip()
            if not body:
                QMessageBox.warning(self, "Ошибка", "Введите текст ответа")
                return
            params["body"] = body
        
        elif type_str == "flag_for_review":
            params["priority"] = self.combo_priority.currentData()
        
        # Сохранить
        self.result_data = {
            "type": type_str,
            "params": params
        }
        
        self.accept()
    
    def get_action_data(self):
        """Получить данные действия"""
        return self.result_data
