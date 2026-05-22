"""
Диалог настройки SMTP/IMAP аккаунтов
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QLineEdit, QSpinBox, QCheckBox, QGroupBox, QFormLayout,
    QListWidget, QListWidgetItem, QMessageBox, QTabWidget,
    QComboBox, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal
from loguru import logger


class DialogSMTPSettings(QDialog):
    """Диалог настройки SMTP/IMAP аккаунтов"""
    
    account_saved = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Настройка SMTP/IMAP аккаунтов")
        self.setMinimumSize(800, 600)
        
        self.accounts = []
        self.current_account_id = None
        
        self._setup_ui()
        self._load_accounts()
    
    def _setup_ui(self):
        layout = QVBoxLayout()
        
        # Список аккаунтов
        list_group = QGroupBox("SMTP/IMAP аккаунты")
        list_layout = QHBoxLayout()
        
        self.list_accounts = QListWidget()
        self.list_accounts.setMinimumWidth(250)
        self.list_accounts.currentItemChanged.connect(self._on_account_selected)
        list_layout.addWidget(self.list_accounts)
        
        list_btn_layout = QVBoxLayout()
        
        btn_add = QPushButton("➕ Добавить")
        btn_add.clicked.connect(self._add_account)
        list_btn_layout.addWidget(btn_add)
        
        btn_edit = QPushButton("✏️ Редактировать")
        btn_edit.clicked.connect(self._edit_account)
        list_btn_layout.addWidget(btn_edit)
        
        btn_delete = QPushButton("🗑️ Удалить")
        btn_delete.clicked.connect(self._delete_account)
        list_btn_layout.addWidget(btn_delete)
        
        btn_set_primary = QPushButton("⭐ Сделать основным")
        btn_set_primary.clicked.connect(self._set_primary)
        list_btn_layout.addWidget(btn_set_primary)
        
        list_btn_layout.addStretch()
        list_layout.addLayout(list_btn_layout)
        
        list_group.setLayout(list_layout)
        layout.addWidget(list_group)
        
        # Детали аккаунта
        details_group = QGroupBox("Настройки аккаунта")
        details_layout = QFormLayout()
        
        # Название
        self.txt_name = QLineEdit()
        self.txt_name.setPlaceholderText("Рабочий Gmail")
        details_layout.addRow("Название:", self.txt_name)
        
        # Email
        self.txt_email = QLineEdit()
        self.txt_email.setPlaceholderText("user@gmail.com")
        details_layout.addRow("Email:", self.txt_email)
        
        # SMTP
        smtp_group = QGroupBox("SMTP (отправка)")
        smtp_layout = QFormLayout()
        
        self.txt_smtp_host = QLineEdit()
        self.txt_smtp_host.setPlaceholderText("smtp.gmail.com")
        self.txt_smtp_host.setText("smtp.gmail.com")
        smtp_layout.addRow("Хост:", self.txt_smtp_host)
        
        self.spn_smtp_port = QSpinBox()
        self.spn_smtp_port.setRange(1, 65535)
        self.spn_smtp_port.setValue(465)
        smtp_layout.addRow("Порт:", self.spn_smtp_port)
        
        self.chk_smtp_tls = QCheckBox("Использовать SSL/TLS")
        self.chk_smtp_tls.setChecked(True)
        smtp_layout.addRow("", self.chk_smtp_tls)
        
        self.txt_smtp_login = QLineEdit()
        self.txt_smtp_login.setPlaceholderText("Логин (обычно email)")
        smtp_layout.addRow("Логин:", self.txt_smtp_login)
        
        self.txt_smtp_password = QLineEdit()
        self.txt_smtp_password.setPlaceholderText("Пароль или App Password")
        self.txt_smtp_password.setEchoMode(QLineEdit.EchoMode.Password)
        smtp_layout.addRow("Пароль:", self.txt_smtp_password)
        
        smtp_group.setLayout(smtp_layout)
        details_layout.addRow(smtp_group)
        
        # IMAP
        imap_group = QGroupBox("IMAP (получение)")
        imap_layout = QFormLayout()
        
        self.txt_imap_host = QLineEdit()
        self.txt_imap_host.setPlaceholderText("imap.gmail.com")
        self.txt_imap_host.setText("imap.gmail.com")
        imap_layout.addRow("Хост:", self.txt_imap_host)
        
        self.spn_imap_port = QSpinBox()
        self.spn_imap_port.setRange(1, 65535)
        self.spn_imap_port.setValue(993)
        imap_layout.addRow("Порт:", self.spn_imap_port)
        
        self.chk_imap_ssl = QCheckBox("Использовать SSL")
        self.chk_imap_ssl.setChecked(True)
        imap_layout.addRow("", self.chk_imap_ssl)
        
        imap_group.setLayout(imap_layout)
        details_layout.addRow(imap_group)
        
        # Статус
        self.lbl_status = QLabel("")
        self.lbl_status.setStyleSheet("color: gray;")
        details_layout.addRow("", self.lbl_status)
        
        details_group.setLayout(details_layout)
        layout.addWidget(details_group)
        
        # Кнопки
        btn_layout = QHBoxLayout()
        
        btn_test = QPushButton("🧪 Проверить подключение")
        btn_test.clicked.connect(self._test_connection)
        btn_layout.addWidget(btn_test)
        
        btn_save = QPushButton("💾 Сохранить")
        btn_save.clicked.connect(self._save_account)
        btn_layout.addWidget(btn_save)
        
        btn_layout.addStretch()
        
        btn_cancel = QPushButton("Отмена")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)
        
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
    
    def _load_accounts(self):
        """Загрузка аккаунтов"""
        from services.smtp_manager import SMTPManager
        
        manager = SMTPManager()
        self.accounts = manager.get_accounts()
        
        self.list_accounts.clear()
        
        for account in self.accounts:
            marker = "⭐ " if account["is_primary"] else ""
            status = "🟢" if account["is_active"] else "🔴"
            item = QListWidgetItem(f"{marker}{status} {account['name']} ({account['email']})")
            item.setData(Qt.ItemDataRole.UserRole, account["id"])
            self.list_accounts.addItem(item)
        
        if self.accounts:
            self.list_accounts.setCurrentRow(0)
            self._on_account_selected(self.list_accounts.item(0), None)
    
    def _on_account_selected(self, current, previous):
        """Выбор аккаунта"""
        if not current:
            self._clear_form()
            return
        
        account_id = current.data(Qt.ItemDataRole.UserRole)
        account = next((a for a in self.accounts if a["id"] == account_id), None)
        
        if account:
            self.current_account_id = account_id
            self._load_account_form(account)
    
    def _load_account_form(self, account):
        """Загрузка формы аккаунта"""
        from services.smtp_manager import SMTPManager
        
        manager = SMTPManager()
        full_account = manager.get_primary_account() if account["is_primary"] else None
        
        # Если нет данных, используем базовые
        if not full_account:
            full_account = account
        
        self.txt_name.setText(account["name"])
        self.txt_email.setText(account["email"])
        self.txt_smtp_host.setText(full_account.get("smtp_host", ""))
        self.spn_smtp_port.setValue(full_account.get("smtp_port", 465))
        self.chk_smtp_tls.setChecked(full_account.get("smtp_use_tls", True))
        self.txt_smtp_login.setText(full_account.get("login", ""))
        # Пароль не показываем
        
        self.txt_imap_host.setText(full_account.get("imap_host", ""))
        self.spn_imap_port.setValue(full_account.get("imap_port", 993))
        self.chk_imap_ssl.setChecked(full_account.get("imap_use_ssl", True))
        
        self.lbl_status.setText(f"Последняя проверка: {account.get('last_check', 'Не проверялось')}")
    
    def _clear_form(self):
        """Очистка формы"""
        self.txt_name.clear()
        self.txt_email.clear()
        self.txt_smtp_host.clear()
        self.spn_smtp_port.setValue(465)
        self.chk_smtp_tls.setChecked(True)
        self.txt_smtp_login.clear()
        self.txt_smtp_password.clear()
        self.txt_imap_host.clear()
        self.spn_imap_port.setValue(993)
        self.chk_imap_ssl.setChecked(True)
        self.lbl_status.setText("")
        self.current_account_id = None
    
    def _add_account(self):
        """Добавление аккаунта"""
        self._clear_form()
        self.current_account_id = None
        self.txt_name.setFocus()
    
    def _edit_account(self):
        """Редактирование аккаунта"""
        if not self.current_account_id:
            QMessageBox.warning(self, "Внимание", "Выберите аккаунт для редактирования")
            return
        
        # Уже загружено при выборе
        self.txt_name.setFocus()
    
    def _delete_account(self):
        """Удаление аккаунта"""
        if not self.current_account_id:
            QMessageBox.warning(self, "Внимание", "Выберите аккаунт для удаления")
            return
        
        reply = QMessageBox.question(
            self, "Подтверждение",
            "Удалить этот аккаунт?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            from core.database import SessionLocal
            from core.models import SMTPAccount
            
            db = SessionLocal()
            try:
                account = db.query(SMTPAccount).get(self.current_account_id)
                if account:
                    account.is_active = False
                    db.commit()
                    logger.info(f"Аккаунт удалён: {account.email}")
                    self._load_accounts()
            finally:
                db.close()
    
    def _set_primary(self):
        """Сделать основным"""
        if not self.current_account_id:
            QMessageBox.warning(self, "Внимание", "Выберите аккаунт")
            return
        
        from core.database import SessionLocal
        from core.models import SMTPAccount
        
        db = SessionLocal()
        try:
            # Снять с других
            db.query(SMTPAccount).filter_by(is_primary=True).update({"is_primary": False})
            
            # Установить текущему
            account = db.query(SMTPAccount).get(self.current_account_id)
            if account:
                account.is_primary = True
                db.commit()
                logger.info(f"Аккаунт сделан основным: {account.email}")
                self._load_accounts()
                QMessageBox.information(self, "Успех", "Аккаунт сделан основным")
        finally:
            db.close()
    
    def _test_connection(self):
        """Тестирование подключения"""
        self._validate_form()
        
        smtp_host = self.txt_smtp_host.text().strip()
        smtp_port = self.spn_smtp_port.value()
        imap_host = self.txt_imap_host.text().strip()
        imap_port = self.spn_imap_port.value()
        email = self.txt_email.text().strip()
        login = self.txt_smtp_login.text().strip()
        password = self.txt_smtp_password.text()
        
        if not password:
            # Если пароль не введён, пробуем из БД
            if self.current_account_id:
                from services.smtp_manager import SMTPManager
                manager = SMTPManager()
                account = manager.get_primary_account()
                if account:
                    password = account.get("password", "")
        
        if not password:
            QMessageBox.warning(self, "Ошибка", "Введите пароль!")
            return
        
        self.lbl_status.setText("Проверка подключения...")
        QApplication = __import__('PyQt6.QtWidgets', fromList=['QApplication'])
        QApplication.processEvents()
        
        from services.smtp_manager import SMTPManager
        
        manager = SMTPManager()
        result = manager.test_full_connection(
            smtp_host, smtp_port,
            imap_host, imap_port,
            email, password,
            self.chk_smtp_tls.isChecked(),
            self.chk_imap_ssl.isChecked()
        )
        
        if result["overall_success"]:
            self.lbl_status.setText("✅ Подключение успешно!")
            self.lbl_status.setStyleSheet("color: green;")
            QMessageBox.information(self, "Успех", "Подключение успешно!\n\n" + result["smtp_message"] + "\n" + result["imap_message"])
        else:
            msg = ""
            if not result["smtp_success"]:
                msg += f"SMTP: {result['smtp_message']}\n"
            if not result["imap_success"]:
                msg += f"IMAP: {result['imap_message']}\n"
            
            self.lbl_status.setText("❌ Ошибка подключения")
            self.lbl_status.setStyleSheet("color: red;")
            QMessageBox.critical(self, "Ошибка", msg)
    
    def _save_account(self):
        """Сохранение аккаунта"""
        if not self._validate_form():
            return
        
        from services.smtp_manager import SMTPManager
        
        manager = SMTPManager()
        
        account_id = manager.save_account(
            name=self.txt_name.text().strip(),
            email=self.txt_email.text().strip(),
            smtp_host=self.txt_smtp_host.text().strip(),
            smtp_port=self.spn_smtp_port.value(),
            imap_host=self.txt_imap_host.text().strip(),
            imap_port=self.spn_imap_port.value(),
            login=self.txt_smtp_login.text().strip(),
            password=self.txt_smtp_password.text(),
            use_tls=self.chk_smtp_tls.isChecked(),
            use_ssl=self.chk_imap_ssl.isChecked(),
            is_primary=True  # По умолчанию делаем основным
        )
        
        self._load_accounts()
        self.account_saved.emit({"id": account_id, "email": self.txt_email.text()})
        
        QMessageBox.information(self, "Успех", "Аккаунт сохранён!")
    
    def _validate_form(self) -> bool:
        """Валидация формы"""
        if not self.txt_name.text().strip():
            QMessageBox.warning(self, "Ошибка", "Укажите название аккаунта!")
            return False
        
        if not self.txt_email.text().strip():
            QMessageBox.warning(self, "Ошибка", "Укажите email!")
            return False
        
        if not self.txt_smtp_host.text().strip():
            QMessageBox.warning(self, "Ошибка", "Укажите SMTP хост!")
            return False
        
        if not self.txt_smtp_login.text().strip():
            QMessageBox.warning(self, "Ошибка", "Укажите логин!")
            return False
        
        if not self.txt_smtp_password.text() and not self.current_account_id:
            QMessageBox.warning(self, "Ошибка", "Введите пароль!")
            return False
        
        return True
