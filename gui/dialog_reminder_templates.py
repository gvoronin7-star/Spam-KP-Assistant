"""
Редактор шаблонов напоминаний
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QTextEdit, QPushButton, QMessageBox, QTabWidget, QWidget,
    QGroupBox, QFormLayout
)
from PyQt6.QtCore import Qt
from loguru import logger

from core.database import SessionLocal
from core.models import Template
from services.template_service import TemplateService


class DialogReminderTemplates(QDialog):
    """Диалог редактирования шаблонов напоминаний"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Шаблоны напоминаний")
        self.setMinimumSize(700, 500)
        self.template_service = TemplateService()
        
        self._setup_ui()
        self._load_templates()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Описание
        info = QLabel(
            "Здесь можно отредактировать шаблоны писем-напоминаний, "
            "которые отправляются поставщикам при отсутствии ответа.\n"
            "Доступные переменные: {{ company_name }}, {{ contact_person }}, {{ service_name }}, {{ request_date }}"
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: gray; font-size: 11px;")
        layout.addWidget(info)
        
        # Вкладки
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        # === Напоминание 1 ===
        tab1 = QWidget()
        tab1_layout = QVBoxLayout(tab1)
        
        self.subject1 = QLineEdit()
        self.subject1.setPlaceholderText("Тема письма")
        tab1_layout.addWidget(QLabel("Тема:"))
        tab1_layout.addWidget(self.subject1)
        
        self.body1 = QTextEdit()
        self.body1.setPlaceholderText("Текст письма (plain text)")
        tab1_layout.addWidget(QLabel("Текст письма:"))
        tab1_layout.addWidget(self.body1)
        
        preview1 = QLabel("Переменные: {{ company_name }}, {{ contact_person }}, {{ service_name }}, {{ request_date }}")
        preview1.setStyleSheet("color: gray; font-size: 10px;")
        tab1_layout.addWidget(preview1)
        
        self.tabs.addTab(tab1, "Напоминание 1 (3 дня)")
        
        # === Напоминание 2 ===
        tab2 = QWidget()
        tab2_layout = QVBoxLayout(tab2)
        
        self.subject2 = QLineEdit()
        self.subject2.setPlaceholderText("Тема письма")
        tab2_layout.addWidget(QLabel("Тема:"))
        tab2_layout.addWidget(self.subject2)
        
        self.body2 = QTextEdit()
        self.body2.setPlaceholderText("Текст письма (plain text)")
        tab2_layout.addWidget(QLabel("Текст письма:"))
        tab2_layout.addWidget(self.body2)
        
        preview2 = QLabel("Переменные: {{ company_name }}, {{ contact_person }}, {{ service_name }}, {{ request_date }}")
        preview2.setStyleSheet("color: gray; font-size: 10px;")
        tab2_layout.addWidget(preview2)
        
        self.tabs.addTab(tab2, "Напоминание 2 (7 дней)")
        
        # Кнопки
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        btn_save = QPushButton("💾 Сохранить")
        btn_save.clicked.connect(self._save_templates)
        btn_layout.addWidget(btn_save)
        
        btn_reset = QPushButton("↩️ Сбросить к defaults")
        btn_reset.clicked.connect(self._reset_defaults)
        btn_layout.addWidget(btn_reset)
        
        btn_close = QPushButton("Закрыть")
        btn_close.clicked.connect(self.reject)
        btn_layout.addWidget(btn_close)
        
        layout.addLayout(btn_layout)
    
    def _load_templates(self):
        """Загрузить шаблоны из БД"""
        db = SessionLocal()
        try:
            # Напоминание 1
            t1 = self.template_service.get_by_type("reminder_1", db)
            if t1:
                self.subject1.setText(t1.subject or "")
                self.body1.setPlainText(t1.body_plain or "")
            else:
                self._set_default_1()
            
            # Напоминание 2
            t2 = self.template_service.get_by_type("reminder_2", db)
            if t2:
                self.subject2.setText(t2.subject or "")
                self.body2.setPlainText(t2.body_plain or "")
            else:
                self._set_default_2()
        
        finally:
            db.close()
    
    def _set_default_1(self):
        """Установить defaults для напоминания 1"""
        self.subject1.setText("Напоминание: Запрос КП - {{ service_name }}")
        self.body1.setPlainText(
            "Добрый день, {{ contact_person }}!\n\n"
            "Напоминаем о нашем запросе коммерческого предложения от {{ request_date }}.\n\n"
            "Будем благодарны, если вы предоставите КП в ближайшее время.\n\n"
            "С уважением,\n"
            "Ваша компания"
        )
    
    def _set_default_2(self):
        """Установить defaults для напоминания 2"""
        self.subject2.setText("Повторное напоминание: Запрос КП - {{ service_name }}")
        self.body2.setPlainText(
            "Добрый день, {{ contact_person }}!\n\n"
            "Это повторное напоминание о нашем запросе коммерческого предложения от {{ request_date }}.\n\n"
            "Пожалуйста, сообщите, возможно ли сотрудничество с вашей компанией.\n\n"
            "С уважением,\n"
            "Ваша компания"
        )
    
    def _save_templates(self):
        """Сохранить шаблоны в БД"""
        db = SessionLocal()
        try:
            # Напоминание 1
            t1 = self.template_service.get_by_type("reminder_1", db)
            data1 = {
                "name": "Напоминание 1",
                "template_type": "reminder_1",
                "subject": self.subject1.text(),
                "body_plain": self.body1.toPlainText(),
                "body_html": self.body1.toPlainText().replace("\n", "<br>"),
                "is_active": True
            }
            if t1:
                self.template_service.update(t1.id, data1, db)
            else:
                self.template_service.create(data1, db)
            
            # Напоминание 2
            t2 = self.template_service.get_by_type("reminder_2", db)
            data2 = {
                "name": "Напоминание 2",
                "template_type": "reminder_2",
                "subject": self.subject2.text(),
                "body_plain": self.body2.toPlainText(),
                "body_html": self.body2.toPlainText().replace("\n", "<br>"),
                "is_active": True
            }
            if t2:
                self.template_service.update(t2.id, data2, db)
            else:
                self.template_service.create(data2, db)
            
            QMessageBox.information(self, "Сохранено", "Шаблоны напоминаний сохранены!")
            logger.info("Шаблоны напоминаний обновлены")
        
        except Exception as e:
            logger.error(f"Ошибка сохранения шаблонов напоминаний: {e}")
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить: {e}")
        
        finally:
            db.close()
    
    def _reset_defaults(self):
        """Сбросить к значениям по умолчанию"""
        reply = QMessageBox.question(
            self,
            "Подтверждение",
            "Сбросить шаблоны к значениям по умолчанию?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self._set_default_1()
            self._set_default_2()
            logger.info("Шаблоны напоминаний сброшены к defaults")
