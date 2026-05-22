"""
Диалог редактирования условия правила
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QComboBox, QLineEdit, QSpinBox, QTextEdit, QGroupBox,
    QFormLayout, QListWidget, QListWidgetItem, QMessageBox
)
from PyQt6.QtCore import Qt
from services.rule_engine import RuleConditionType


class DialogConditionEditor(QDialog):
    """
    Диалог создания/редактирования условия правила
    
    Поля:
    - Тип условия
    - Параметры (зависят от типа)
    """
    
    def __init__(self, condition_data=None, parent=None):
        super().__init__(parent)
        self.condition_data = condition_data
        self.is_editing = condition_data is not None
        
        self.setWindowTitle(
            "Редактировать условие" if self.is_editing else "Создать условие"
        )
        self.setMinimumSize(500, 400)
        
        self._setup_ui()
        
        if self.is_editing:
            self._load_data(condition_data)
    
    def _setup_ui(self):
        """Настройка интерфейса"""
        layout = QVBoxLayout(self)
        
        # Тип условия
        form = QFormLayout()
        
        self.combo_type = QComboBox()
        for cond_type in RuleConditionType:
            self.combo_type.addItem(cond_type.value, cond_type.value)
        
        if self.is_editing:
            index = self.combo_type.findData(self.condition_data["type"])
            if index >= 0:
                self.combo_type.setCurrentIndex(index)
        
        self.combo_type.currentIndexChanged.connect(self._on_type_changed)
        form.addRow("Тип условия:", self.combo_type)
        
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
        """Изменение типа условия"""
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
        if type_str == "contains_keyword" or type_str == "not_contains_keyword":
            self._create_keywords_param()
        
        elif type_str == "message_type":
            self._create_message_type_param()
        
        elif type_str == "sender_domain":
            self._create_domain_param()
        
        elif type_str == "dialogue_status":
            self._create_status_param()
        
        elif type_str == "custom_llm_result":
            self._create_llm_result_param()
        
        elif type_str in ["has_attachment", "no_attachment"]:
            # Нет параметров
            label = QLabel("Нет дополнительных параметров")
            self.params_layout.addWidget(label)
        
        else:
            label = QLabel("Нет параметров для этого типа")
            self.params_layout.addWidget(label)
        
    def _create_keywords_param(self):
        """Параметр: ключевые слова"""
        form = QFormLayout()
        
        self.input_keywords = QLineEdit()
        if hasattr(self, 'params_data') and "keywords" in self.params_data:
            self.input_keywords.setText(", ".join(self.params_data["keywords"]))
        self.input_keywords.setPlaceholderText("ключ1, ключ2, ключ3")
        
        form.addRow("Ключевые слова:", self.input_keywords)
        self.params_layout.addLayout(form)
        
        # Описание
        desc = QLabel("💡 Слова разделяются запятой")
        desc.setStyleSheet("color: gray; font-size: 10px;")
        self.params_layout.addWidget(desc)
    
    def _create_message_type_param(self):
        """Параметр: тип сообщения"""
        form = QFormLayout()
        
        self.combo_type = QComboBox()
        self.combo_type.addItem("LLM", "llm")
        self.combo_type.addItem("Ручное", "manual")
        
        if hasattr(self, 'params_data') and "type" in self.params_data:
            index = self.combo_type.findData(self.params_data["type"])
            if index >= 0:
                self.combo_type.setCurrentIndex(index)
        
        form.addRow("Тип:", self.combo_type)
        self.params_layout.addLayout(form)
    
    def _create_domain_param(self):
        """Параметр: домен отправителя"""
        form = QFormLayout()
        
        self.input_domain = QLineEdit()
        if hasattr(self, 'params_data') and "domain" in self.params_data:
            self.input_domain.setText(self.params_data["domain"])
        self.input_domain.setPlaceholderText("example.com")
        
        form.addRow("Домен:", self.input_domain)
        self.params_layout.addLayout(form)
    
    def _create_status_param(self):
        """Параметр: статус диалога"""
        form = QFormLayout()
        
        self.combo_status = QComboBox()
        statuses = ["sent", "clarifying", "kp_received", "rejected", "reminder_sent", "auto_replied", "spam"]
        for status in statuses:
            self.combo_status.addItem(status, status)
        
        if hasattr(self, 'params_data') and "status" in self.params_data:
            index = self.combo_status.findData(self.params_data["status"])
            if index >= 0:
                self.combo_status.setCurrentIndex(index)
        
        form.addRow("Статус:", self.combo_status)
        self.params_layout.addLayout(form)
    
    def _create_llm_result_param(self):
        """Параметр: результат LLM"""
        form = QFormLayout()
        
        self.combo_llm = QComboBox()
        results = ["kp", "question", "refusal", "auto_reply", "spam", "unknown"]
        for result in results:
            self.combo_llm.addItem(result, result)
        
        if hasattr(self, 'params_data') and "llm_result" in self.params_data:
            index = self.combo_llm.findData(self.params_data["llm_result"])
            if index >= 0:
                self.combo_llm.setCurrentIndex(index)
        
        form.addRow("Результат LLM:", self.combo_llm)
        self.params_layout.addLayout(form)
    
    def _on_ok(self):
        """OK — сохранить условие"""
        type_str = self.combo_type.currentData()
        
        # Собрать параметры
        params = {}
        
        if type_str == "contains_keyword" or type_str == "not_contains_keyword":
            keywords_text = self.input_keywords.text().strip()
            if not keywords_text:
                QMessageBox.warning(self, "Ошибка", "Введите ключевые слова")
                return
            params["keywords"] = [k.strip() for k in keywords_text.split(",")]
        
        elif type_str == "message_type":
            params["type"] = self.combo_type.currentData()
        
        elif type_str == "sender_domain":
            domain = self.input_domain.text().strip()
            if not domain:
                QMessageBox.warning(self, "Ошибка", "Введите домен")
                return
            params["domain"] = domain
        
        elif type_str == "dialogue_status":
            params["status"] = self.combo_status.currentData()
        
        elif type_str == "custom_llm_result":
            params["llm_result"] = self.combo_llm.currentData()
        
        # Сохранить
        self.result_data = {
            "type": type_str,
            "params": params
        }
        
        self.accept()
    
    def get_condition_data(self):
        """Получить данные условия"""
        return self.result_data
