"""
Редактор шаблонов писем
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QLineEdit, QTextEdit, QGroupBox, QFormLayout, QTabWidget,
    QListWidget, QListWidgetItem, QMessageBox, QSplitter,
    QCheckBox, QFileDialog, QWidget
)
from PyQt6.QtCore import Qt, pyqtSignal
from loguru import logger
import re


class TemplateEditor(QDialog):
    """Редактор шаблона письма"""
    
    template_saved = pyqtSignal(dict)
    
    def __init__(self, template_data=None, parent=None):
        """
        Args:
            template_data: Данные существующего шаблона (для редактирования)
        """
        super().__init__(parent)
        self.setWindowTitle("Редактор шаблона письма")
        self.setMinimumSize(900, 700)
        
        self.template_data = template_data or {}
        self.attachments = []
        
        self._setup_ui()
        self._load_data()
    
    def _setup_ui(self):
        layout = QVBoxLayout()
        
        # Основная информация
        info_group = QGroupBox("Основная информация")
        info_layout = QFormLayout()
        
        self.txt_name = QLineEdit()
        self.txt_name.setPlaceholderText("Например: Первичный запрос КП")
        info_layout.addRow("Название шаблона:", self.txt_name)
        
        self.combo_type = QGroupBox("Тип шаблона")
        type_layout = QHBoxLayout()
        self.chk_initial = QCheckBox("Первичный запрос")
        self.chk_reminder = QCheckBox("Напоминание")
        self.chk_followup = QCheckBox("Уточнение")
        type_layout.addWidget(self.chk_initial)
        type_layout.addWidget(self.chk_reminder)
        type_layout.addWidget(self.chk_followup)
        self.combo_type.setLayout(type_layout)
        info_layout.addRow("", self.combo_type)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # Переменные
        variables_group = QGroupBox("Доступные переменные")
        variables_layout = QVBoxLayout()
        
        self.list_variables = QListWidget()
        self.list_variables.setMaximumHeight(80)
        self.list_variables.addItems([
            "{{ company }} - Название компании",
            "{{ service_name }} - Название услуги",
            "{{ operator_name }} - Название оператора",
            "{{ contact_person }} - Контактное лицо",
            "{{ request_date }} - Дата запроса"
        ])
        self.list_variables.setStyleSheet("background-color: #f5f5f5;")
        variables_layout.addWidget(self.list_variables)
        
        btn_insert = QPushButton("Вставить переменную...")
        btn_insert.clicked.connect(self._insert_variable)
        variables_layout.addWidget(btn_insert)
        
        variables_group.setLayout(variables_layout)
        layout.addWidget(variables_group)
        
        # Редактор содержимого
        content_group = QGroupBox("Содержимое письма")
        content_layout = QVBoxLayout()
        
        # Тема письма
        theme_layout = QHBoxLayout()
        theme_layout.addWidget(QLabel("Тема:"))
        self.txt_subject = QLineEdit()
        self.txt_subject.setPlaceholderText("Запрос коммерческого предложения - {{ service_name }}")
        theme_layout.addWidget(self.txt_subject)
        content_layout.addLayout(theme_layout)
        
        # Табы для HTML и Plain
        self.tabs = QTabWidget()
        
        # Plain текст
        plain_widget = QWidget()
        plain_layout = QVBoxLayout(plain_widget)
        self.txt_plain = QTextEdit()
        self.txt_plain.setPlaceholderText("Текст письма в обычном формате...")
        self.txt_plain.setMinimumHeight(200)
        plain_layout.addWidget(self.txt_plain)
        
        # HTML
        html_widget = QWidget()
        html_layout = QVBoxLayout(html_widget)
        self.txt_html = QTextEdit()
        self.txt_html.setPlaceholderText("<html><body><h1>Текст письма</h1><p>HTML формат...</p></body></html>")
        self.txt_html.setMinimumHeight(200)
        html_layout.addWidget(self.txt_html)
        
        self.tabs.addTab(plain_widget, "Plain текст")
        self.tabs.addTab(html_widget, "HTML")
        content_layout.addWidget(self.tabs)
        
        # Предпросмотр
        btn_preview = QPushButton("👁️ Предпросмотр")
        btn_preview.clicked.connect(self._preview_template)
        content_layout.addWidget(btn_preview)
        
        content_group.setLayout(content_layout)
        layout.addWidget(content_group)
        
        # Вложения
        attachments_group = QGroupBox("Вложения")
        attachments_layout = QVBoxLayout()
        
        self.list_attachments = QListWidget()
        self.list_attachments.setMinimumHeight(100)
        attachments_layout.addWidget(self.list_attachments)
        
        attach_btn_layout = QHBoxLayout()
        
        btn_add_attach = QPushButton("📎 Добавить файл")
        btn_add_attach.clicked.connect(self._add_attachment)
        attach_btn_layout.addWidget(btn_add_attach)
        
        btn_remove_attach = QPushButton("❌ Удалить")
        btn_remove_attach.clicked.connect(self._remove_attachment)
        attach_btn_layout.addWidget(btn_remove_attach)
        
        attach_btn_layout.addStretch()
        attachments_layout.addLayout(attach_btn_layout)
        
        attachments_group.setLayout(attachments_layout)
        layout.addWidget(attachments_group)
        
        # Кнопки
        btn_layout = QHBoxLayout()
        
        btn_save = QPushButton("💾 Сохранить")
        btn_save.clicked.connect(self._save_template)
        btn_layout.addWidget(btn_save)
        
        btn_test = QPushButton("🧪 Тестовая отправка")
        btn_test.clicked.connect(self._test_send)
        btn_layout.addWidget(btn_test)
        
        btn_layout.addStretch()
        
        btn_cancel = QPushButton("Отмена")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)
        
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
    
    def _load_data(self):
        """Загрузка данных шаблона"""
        if not self.template_data:
            return
        
        self.txt_name.setText(self.template_data.get("name", ""))
        self.txt_subject.setText(self.template_data.get("subject", ""))
        self.txt_plain.setText(self.template_data.get("body_plain", ""))
        self.txt_html.setText(self.template_data.get("body_html", ""))
        
        # Типы шаблона
        template_type = self.template_data.get("template_type", "")
        if "initial" in template_type:
            self.chk_initial.setChecked(True)
        if "reminder" in template_type:
            self.chk_reminder.setChecked(True)
        if "followup" in template_type:
            self.chk_followup.setChecked(True)
        
        # Вложения
        attachments = self.template_data.get("attachments", [])
        for file_path in attachments:
            self.list_attachments.addItem(file_path)
    
    def _insert_variable(self):
        """Вставка переменной"""
        variables = {
            "{{ company }}": "Название компании",
            "{{ service_name }}": "Название услуги",
            "{{ operator_name }}": "Название оператора",
            "{{ contact_person }}": "Контактное лицо",
            "{{ request_date }}": "Дата запроса"
        }
        
        from PyQt6.QtWidgets import QComboBox
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Выберите переменную")
        dialog.setMinimumSize(400, 200)
        
        layout = QVBoxLayout()
        
        lbl = QLabel("Выберите переменную для вставки:")
        layout.addWidget(lbl)
        
        combo = QComboBox()
        for var, desc in variables.items():
            combo.addItem(f"{var} - {desc}", var)
        layout.addWidget(combo)
        
        from PyQt6.QtWidgets import QDialogButtonBox
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        dialog.setLayout(layout)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            variable = combo.currentData()
            # Вставка в активное текстовое поле текущей вкладки
            if self.tabs.currentIndex() == 1:
                # HTML вкладка
                self.txt_html.insertPlainText(variable)
            else:
                # Plain текст вкладка
                self.txt_plain.insertPlainText(variable)
    
    def _preview_template(self):
        """Предпросмотр шаблона"""
        subject = self._replace_variables(self.txt_subject.text())
        body = self._replace_variables(self.txt_html.toPlainText() or self.txt_plain.toPlainText())
        
        from PyQt6.QtWidgets import QTextBrowser
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Предпросмотр шаблона")
        dialog.setMinimumSize(600, 400)
        
        layout = QVBoxLayout()
        
        lbl_subject = QLabel(f"<b>Тема:</b> {subject}")
        layout.addWidget(lbl_subject)
        
        browser = QTextBrowser()
        browser.setHtml(body)
        layout.addWidget(browser)
        
        btn_close = QPushButton("Закрыть")
        btn_close.clicked.connect(dialog.close)
        layout.addWidget(btn_close)
        
        dialog.setLayout(layout)
        dialog.exec()
    
    def _replace_variables(self, text):
        """Замена переменных тестовыми значениями"""
        replacements = {
            "{{ company }}": "ООО Пример",
            "{{ service_name }}": "Интернет-канал 100 Мбит/с",
            "{{ operator_name }}": "Наша Компания",
            "{{ contact_person }}": "Иван Иванов",
            "{{ request_date }}": "20.05.2026"
        }
        
        for var, value in replacements.items():
            text = text.replace(var, f"<b>{value}</b>")
        
        return text
    
    def _add_attachment(self):
        """Добавление вложения"""
        files, _ = QFileDialog.getOpenFileNames(
            self, "Выберите файлы", "",
            "Все файлы (*.*)"
        )

        for file_path in files:
            self.list_attachments.addItem(file_path)
    
    def _remove_attachment(self):
        """Удаление вложения"""
        current_row = self.list_attachments.currentRow()
        if current_row >= 0:
            self.list_attachments.takeItem(current_row)
    
    def _save_template(self):
        """Сохранение шаблона"""
        name = self.txt_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Ошибка", "Укажите название шаблона!")
            return
        
        # Определение типа
        template_types = []
        if self.chk_initial.isChecked():
            template_types.append("initial")
        if self.chk_reminder.isChecked():
            template_types.append("reminder")
        if self.chk_followup.isChecked():
            template_types.append("followup")
        
        if not template_types:
            QMessageBox.warning(self, "Ошибка", "Выберите хотя бы один тип шаблона!")
            return
        
        # Сбор данных
        template_data = {
            "name": name,
            "template_type": ",".join(template_types),
            "subject": self.txt_subject.text().strip(),
            "body_plain": self.txt_plain.toPlainText().strip(),
            "body_html": self.txt_html.toPlainText().strip(),
            "attachments": [
                self.list_attachments.item(i).text()
                for i in range(self.list_attachments.count())
            ]
        }
        
        # Валидация
        if not template_data["subject"]:
            QMessageBox.warning(self, "Ошибка", "Укажите тему письма!")
            return
        
        if not template_data["body_plain"] and not template_data["body_html"]:
            QMessageBox.warning(self, "Ошибка", "Укажите содержимое письма!")
            return
        
        # Сохранение в БД
        self._save_to_db(template_data)
    
    def _save_to_db(self, template_data):
        """Сохранение в БД"""
        from core.database import SessionLocal
        from core.models import Template
        
        db = SessionLocal()
        
        try:
            # Проверка是否存在
            existing = db.query(Template).filter(
                Template.name == template_data["name"]
            ).first()
            
            if existing:
                # Обновление
                existing.subject = template_data["subject"]
                existing.body_plain = template_data["body_plain"]
                existing.body_html = template_data["body_html"]
                existing.template_type = template_data["template_type"]
                existing.attachments = template_data["attachments"]
                existing.version = existing.version + 1
                existing.is_active = True
                
                template_id = existing.id
                action = "обновлён"
            else:
                # Создание
                template = Template(
                    name=template_data["name"],
                    subject=template_data["subject"],
                    body_plain=template_data["body_plain"],
                    body_html=template_data["body_html"],
                    template_type=template_data["template_type"],
                    attachments=template_data["attachments"],
                    version=1,
                    is_active=True
                )
                
                db.add(template)
                db.commit()
                db.refresh(template)
                
                template_id = template.id
                action = "создан"
            
            logger.info(f"Шаблон {action}: ID={template_id}, name={template_data['name']}")
            
            # Сигнал
            self.template_saved.emit({
                "id": template_id,
                "name": template_data["name"],
                "action": action
            })
            
            QMessageBox.information(
                self, "Успех",
                f"Шаблон '{template_data['name']}' {action}!\n\nID: {template_id}"
            )
            
            self.accept()
        
        except Exception as e:
            db.rollback()
            logger.error(f"Ошибка сохранения шаблона: {e}")
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить шаблон:\n{str(e)}")
        
        finally:
            db.close()
    
    def _test_send(self):
        """Тестовая отправка"""
        QMessageBox.information(
            self, "Скоро",
            "Тестовая отправка будет доступна после настройки SMTP-аккаунтов"
        )
