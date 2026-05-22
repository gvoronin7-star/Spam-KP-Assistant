"""
Мастер создания рассылки
"""
from PyQt6.QtWidgets import (
    QWizard, QWizardPage, QVBoxLayout, QHBoxLayout,
    QLabel, QComboBox, QLineEdit, QSpinBox,
    QTableWidget, QTableWidgetItem, QCheckBox,
    QPushButton, QGroupBox, QFormLayout, QTextEdit,
    QMessageBox, QHeaderView, QProgressBar, QSplitter
)
from PyQt6.QtCore import Qt, pyqtSignal
from loguru import logger

from core.database import SessionLocal
from core.models import Profile, Contact, Template, SMTPAccount
from services.mailing_service import MailingService


class MailingWizard(QWizard):
    """Мастер создания рассылки"""
    
    mailing_created = pyqtSignal(int)  # ID созданной рассылки
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📧 Мастер рассылки")
        self.setMinimumSize(900, 700)
        
        # Данные, собираемые по ходу
        self.selected_profile_id = None
        self.selected_template_id = None
        self.selected_contact_ids = []
        self.selected_smtp_account_id = None
        
        # Создать страницы
        self.addPage(PageSelectProfileTemplate(self))
        self.addPage(PageSelectRecipients(self))
        self.addPage(PageConfigureSending(self))
        self.addPage(PageConfirm(self))
        
        self.setButtonText(QWizard.WizardButton.NextButton, "Далее >")
        self.setButtonText(QWizard.WizardButton.BackButton, "< Назад")
        self.setButtonText(QWizard.WizardButton.FinishButton, "Запустить рассылку")
        self.setButtonText(QWizard.WizardButton.CancelButton, "Отмена")
    
    def accept(self):
        """Завершение мастера — создание рассылки"""
        try:
            service = MailingService()
            
            mailing_id = service.create_mailing(
                name=self.field("mailing_name"),
                profile_id=self.selected_profile_id,
                template_id=self.selected_template_id,
                contact_ids=self.selected_contact_ids,
                smtp_account_id=self.selected_smtp_account_id,
                delay_min=self.field("delay_min"),
                delay_max=self.field("delay_max"),
                hourly_limit=self.field("hourly_limit"),
                daily_limit=self.field("daily_limit")
            )
            
            self.mailing_created.emit(mailing_id)
            logger.info(f"Рассылка создана через мастер: ID={mailing_id}")
            
            # Спросить о запуске
            reply = QMessageBox.question(
                self,
                "Рассылка создана",
                f"Рассылка создана! ID: {mailing_id}\n\n"
                f"Получателей: {len(self.selected_contact_ids)}\n\n"
                f"Запустить рассылку сейчас?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # Открыть диалог прогресса
                from .dialog_mailing_progress import DialogMailingProgress
                
                dialog = DialogMailingProgress(mailing_id, self.parent())
                dialog.mailing_completed.connect(self._on_mailing_completed)
                dialog.exec()
            else:
                QMessageBox.information(
                    self,
                    "Информация",
                    f"Рассылка сохранена в статусе 'Черновик'.\n"
                    f"Вы можете запустить её позже из главного окна."
                )
            
            super().accept()
        
        except Exception as e:
            logger.error(f"Ошибка создания рассылки: {e}")
            QMessageBox.critical(self, "Ошибка", f"Не удалось создать рассылку:\n{e}")

    def _on_mailing_completed(self, mailing_id):
        """Обработчик завершения рассылки"""
        logger.info(f"Рассылка {mailing_id} завершена")


# === Страница 1: Выбор профиля и шаблона ===

class PageSelectProfileTemplate(QWizardPage):
    """Страница выбора профиля и шаблона"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Шаг 1: Выбор профиля и шаблона")
        self.setSubTitle("Выберите профиль закупки и шаблон письма для рассылки")
        
        self._setup_ui()
        self._load_data()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Название рассылки
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Название рассылки:"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Например: Рассылка КП по интернет-каналам")
        name_layout.addWidget(self.name_input)
        layout.addLayout(name_layout)
        
        self.registerField("mailing_name*", self.name_input)
        
        # Выбор профиля
        profile_group = QGroupBox("📋 Профиль закупки")
        profile_layout = QVBoxLayout()
        
        self.profile_combo = QComboBox()
        self.profile_combo.currentIndexChanged.connect(self._on_profile_changed)
        profile_layout.addWidget(self.profile_combo)
        
        self.profile_preview = QTextEdit()
        self.profile_preview.setReadOnly(True)
        self.profile_preview.setMaximumHeight(100)
        self.profile_preview.setPlaceholderText("Описание профиля...")
        profile_layout.addWidget(self.profile_preview)
        
        profile_group.setLayout(profile_layout)
        layout.addWidget(profile_group)
        
        # Выбор шаблона
        template_group = QGroupBox("📝 Шаблон письма")
        template_layout = QVBoxLayout()
        
        self.template_combo = QComboBox()
        self.template_combo.currentIndexChanged.connect(self._on_template_changed)
        template_layout.addWidget(self.template_combo)
        
        self.template_preview = QTextEdit()
        self.template_preview.setReadOnly(True)
        self.template_preview.setMaximumHeight(150)
        self.template_preview.setPlaceholderText("Текст шаблона...")
        template_layout.addWidget(self.template_preview)
        
        # Кнопка генерации через LLM
        self.btn_llm_generate = QPushButton("✨ Сгенерировать через LLM")
        self.btn_llm_generate.setToolTip("Автоматически сгенерировать письмо на основе профиля через AI")
        self.btn_llm_generate.setStyleSheet("""
            QPushButton {
                background-color: #9C27B0;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #7B1FA2;
            }
        """)
        self.btn_llm_generate.clicked.connect(self._on_llm_generate)
        self.btn_llm_generate.setEnabled(False)  # Отключена пока не выбран профиль
        template_layout.addWidget(self.btn_llm_generate)
        
        template_group.setLayout(template_layout)
        layout.addWidget(template_group)
        
        layout.addStretch()
    
    def _load_data(self):
        """Загрузить профили и шаблоны из БД"""
        db = SessionLocal()
        try:
            # Профили
            profiles = db.query(Profile).filter_by(is_active=True).all()
            self.profile_combo.clear()
            self.profile_combo.addItem("-- Выберите профиль --", None)
            for p in profiles:
                self.profile_combo.addItem(p.name, p.id)
            
            # Шаблоны
            templates = db.query(Template).filter_by(is_active=True).all()
            self.template_combo.clear()
            self.template_combo.addItem("-- Выберите шаблон --", None)
            for t in templates:
                self.template_combo.addItem(f"{t.name} ({t.template_type})", t.id)
        
        finally:
            db.close()
    
    def _on_profile_changed(self, index):
        """Обработчик смены профиля"""
        profile_id = self.profile_combo.currentData()
        if not profile_id:
            self.profile_preview.clear()
            return
        
        db = SessionLocal()
        try:
            profile = db.query(Profile).filter_by(id=profile_id).first()
            if profile:
                text = f"{profile.name}\n\n{profile.description or 'Нет описания'}"
                self.profile_preview.setText(text)
                
                # Сохранить выбор
                wizard = self.wizard()
                if wizard:
                    wizard.selected_profile_id = profile_id
        finally:
            db.close()
    
    def _on_template_changed(self, index):
        """Обработчик смены шаблона"""
        template_id = self.template_combo.currentData()
        if not template_id:
            self.template_preview.clear()
            self.btn_llm_generate.setEnabled(False)
            return
        
        db = SessionLocal()
        try:
            template = db.query(Template).filter_by(id=template_id).first()
            if template:
                text = f"Тема: {template.subject}\n\n{template.body_plain or template.body_html or 'Нет текста'}"
                self.template_preview.setText(text[:500])
                
                # Сохранить выбор
                wizard = self.wizard()
                if wizard:
                    wizard.selected_template_id = template_id
                
                # Включить кнопку LLM
                self.btn_llm_generate.setEnabled(True)
        finally:
            db.close()
    
    def _on_profile_changed(self, index):
        """Обработчик смены профиля"""
        profile_id = self.profile_combo.currentData()
        if not profile_id:
            self.profile_preview.clear()
            self.btn_llm_generate.setEnabled(False)
            return
        
        db = SessionLocal()
        try:
            profile = db.query(Profile).filter_by(id=profile_id).first()
            if profile:
                text = f"{profile.name}\n\n{profile.description or 'Нет описания'}"
                self.profile_preview.setText(text)
                
                # Сохранить выбор
                wizard = self.wizard()
                if wizard:
                    wizard.selected_profile_id = profile_id
                
                # Включить кнопку LLM
                self.btn_llm_generate.setEnabled(True)
        finally:
            db.close()

    def _on_llm_generate(self):
        """Генерация письма через LLM"""
        from core.database import SessionLocal
        
        wizard = self.wizard()
        if not wizard:
            return
        
        profile_id = wizard.selected_profile_id
        if not profile_id:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                "⚠️ Внимание",
                "Сначала выберите профиль закупки"
            )
            return
        
        # Показать индикатор загрузки
        self.btn_llm_generate.setEnabled(False)
        self.btn_llm_generate.setText("⏳ Генерация...")
        
        try:
            # Запустить генерацию в отдельном потоке
            from PyQt6.QtCore import QThread, pyqtSignal
            from PyQt6.QtWidgets import QApplication
            
            class LLMGenerationThread(QThread):
                finished = pyqtSignal(dict)
                error = pyqtSignal(str)
                
                def __init__(self, profile_id):
                    super().__init__()
                    self.profile_id = profile_id
                
                def run(self):
                    try:
                        from services.llm_generator_service import LLMGeneratorService
                        from core.models import Contact
                        
                        db = SessionLocal()
                        try:
                            profile = db.query(Profile).filter_by(id=self.profile_id).first()
                            # Использовать первый контакт как демо
                            contact = db.query(Contact).filter_by(is_active=True).first()
                            
                            if not profile:
                                self.error.emit("Профиль не найден")
                                return
                            
                            if not contact:
                                self.error.emit("Нет доступных контактов")
                                return
                            
                            generator = LLMGeneratorService()
                            result = generator.generate_primary_email(profile, contact)
                            self.finished.emit(result)
                        finally:
                            db.close()
                    except Exception as e:
                        self.error.emit(str(e))
            
            # Создать и запустить поток
            self.llm_thread = LLMGenerationThread(profile_id)
            self.llm_thread.finished.connect(self._on_llm_generated)
            self.llm_thread.error.connect(self._on_llm_error)
            self.llm_thread.start()
            
        except Exception as e:
            logger.error(f"Ошибка запуска генерации: {e}")
            QMessageBox.critical(
                self,
                "Ошибка",
                f"Не удалось запустить генерацию:\n{e}"
            )
            self.btn_llm_generate.setEnabled(True)
            self.btn_llm_generate.setText("✨ Сгенерировать через LLM")
    
    def _on_llm_generated(self, result: dict):
        """Обработчик успешной генерации"""
        self.btn_llm_generate.setEnabled(True)
        self.btn_llm_generate.setText("✨ Сгенерировать через LLM")
        
        # Показать предпросмотр
        from .dialog_llm_preview import DialogLLMPreview
        
        def on_apply(updated_data):
            # Обновить шаблон с новыми данными
            logger.info(f"Применена сгенерированная тема: {updated_data['subject']}")
            # Можно создать новый шаблон или обновить текущий
            QMessageBox.information(
                self,
                "✅ Применено",
                f"Тема: {updated_data['subject']}\n\n"
                f"Письмо готово к отправке!"
            )
        
        def on_regenerate():
            # Повторная генерация
            return self._generate_via_llm_internal()
        
        dialog = DialogLLMPreview(
            result,
            on_apply=on_apply,
            on_regenerate=on_regenerate
        )
        dialog.exec()
    
    def _on_llm_error(self, error_msg: str):
        """Обработчик ошибки генерации"""
        self.btn_llm_generate.setEnabled(True)
        self.btn_llm_generate.setText("✨ Сгенерировать через LLM")
        
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.critical(
            self,
            "❌ Ошибка генерации",
            f"Не удалось сгенерировать письмо:\n\n{error_msg}\n\n"
            f"Попробуйте снова или используйте шаблон."
        )

    def _generate_via_llm_internal(self):
        """Внутренний метод для повторной генерации"""
        from core.database import SessionLocal
        from core.models import Profile, Contact
        from services.llm_generator_service import LLMGeneratorService
        
        db = SessionLocal()
        try:
            wizard = self.wizard()
            profile = db.query(Profile).filter_by(id=wizard.selected_profile_id).first()
            contact = db.query(Contact).filter_by(is_active=True).first()
            
            if not profile or not contact:
                return None
            
            generator = LLMGeneratorService()
            return generator.generate_primary_email(profile, contact)
        finally:
            db.close()

    def validatePage(self):
        """Валидация перед переходом"""
        if not self.field("mailing_name").strip():
            QMessageBox.warning(self, "Внимание", "Введите название рассылки")
            return False
        
        if not self.profile_combo.currentData():
            QMessageBox.warning(self, "Внимание", "Выберите профиль закупки")
            return False
        
        if not self.template_combo.currentData():
            QMessageBox.warning(self, "Внимание", "Выберите шаблон письма")
            return False
        
        return True


# === Страница 2: Выбор получателей ===

class PageSelectRecipients(QWizardPage):
    """Страница выбора получателей"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Шаг 2: Выбор получателей")
        self.setSubTitle("Отметьте контакты, которым будет отправлена рассылка")
        
        self._setup_ui()
        self._load_contacts()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Панель управления
        controls = QHBoxLayout()
        
        self.btn_select_all = QPushButton("☑️ Выбрать все")
        self.btn_select_all.clicked.connect(self._select_all)
        controls.addWidget(self.btn_select_all)
        
        self.btn_deselect_all = QPushButton("⬜ Снять все")
        self.btn_deselect_all.clicked.connect(self._deselect_all)
        controls.addWidget(self.btn_deselect_all)
        
        controls.addStretch()
        
        self.lbl_selected = QLabel("Выбрано: 0")
        controls.addWidget(self.lbl_selected)
        
        layout.addLayout(controls)
        
        # Таблица контактов
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["✓", "Email", "Компания", "Контакт"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.itemChanged.connect(self._on_item_changed)
        layout.addWidget(self.table)
        
        # Фильтр
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("🔍 Поиск:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Email или название компании...")
        self.search_input.textChanged.connect(self._filter_contacts)
        filter_layout.addWidget(self.search_input)
        layout.addLayout(filter_layout)
    
    def _load_contacts(self):
        """Загрузить контакты из БД"""
        db = SessionLocal()
        try:
            contacts = db.query(Contact).filter_by(is_active=True).all()
            
            self.table.setRowCount(len(contacts))
            self._contacts_data = []  # Сохранить для фильтрации
            
            for i, contact in enumerate(contacts):
                self._contacts_data.append(contact)
                
                # Чекбокс
                checkbox = QTableWidgetItem()
                checkbox.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
                checkbox.setCheckState(Qt.CheckState.Unchecked)
                self.table.setItem(i, 0, checkbox)
                
                # Email
                self.table.setItem(i, 1, QTableWidgetItem(contact.email))
                
                # Компания
                self.table.setItem(i, 2, QTableWidgetItem(contact.company_name or ""))
                
                # Контактное лицо
                self.table.setItem(i, 3, QTableWidgetItem(contact.contact_person or ""))
        
        finally:
            db.close()

    def _on_item_changed(self, item):
        """Обработчик изменения чекбокса"""
        if item.column() == 0:
            self._update_selected_count()
    
    def _update_selected_count(self):
        """Обновить счётчик выбранных"""
        count = 0
        selected_ids = []
        
        for row in range(self.table.rowCount()):
            checkbox_item = self.table.item(row, 0)
            if checkbox_item and checkbox_item.checkState() == Qt.CheckState.Checked:
                count += 1
                if row < len(self._contacts_data):
                    selected_ids.append(self._contacts_data[row].id)
        
        self.lbl_selected.setText(f"Выбрано: {count}")
        
        # Сохранить выбор
        wizard = self.wizard()
        if wizard:
            wizard.selected_contact_ids = selected_ids
    
    def _select_all(self):
        """Выбрать все контакты"""
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item:
                item.setCheckState(Qt.CheckState.Checked)
    
    def _deselect_all(self):
        """Снять все выделения"""
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item:
                item.setCheckState(Qt.CheckState.Unchecked)
    
    def _filter_contacts(self, text):
        """Фильтрация контактов"""
        text_lower = text.lower()
        
        for row in range(self.table.rowCount()):
            email = self.table.item(row, 1).text().lower()
            company = self.table.item(row, 2).text().lower()
            
            match = text_lower in email or text_lower in company
            self.table.setRowHidden(row, not match)
    
    def validatePage(self):
        """Валидация"""
        wizard = self.wizard()
        if not wizard or not wizard.selected_contact_ids:
            QMessageBox.warning(self, "Внимание", "Выберите хотя бы одного получателя")
            return False
        return True


# === Страница 3: Настройка отправки ===

class PageConfigureSending(QWizardPage):
    """Страница настройки параметров отправки"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Шаг 3: Настройка отправки")
        self.setSubTitle("Настройте параметры отправки писем")
        
        self._setup_ui()
        self._load_smtp_accounts()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # SMTP аккаунт
        smtp_group = QGroupBox("📧 SMTP аккаунт")
        smtp_layout = QFormLayout()
        
        self.smtp_combo = QComboBox()
        smtp_layout.addRow("Аккаунт для отправки:", self.smtp_combo)
        
        smtp_group.setLayout(smtp_layout)
        layout.addWidget(smtp_group)
        
        # Задержки
        delay_group = QGroupBox("⏱️ Задержки между письмами")
        delay_layout = QFormLayout()
        
        self.delay_min = QSpinBox()
        self.delay_min.setRange(1, 300)
        self.delay_min.setValue(5)
        self.delay_min.setSuffix(" сек")
        delay_layout.addRow("Минимальная:", self.delay_min)
        
        self.delay_max = QSpinBox()
        self.delay_max.setRange(1, 600)
        self.delay_max.setValue(30)
        self.delay_max.setSuffix(" сек")
        delay_layout.addRow("Максимальная:", self.delay_max)
        
        delay_group.setLayout(delay_layout)
        layout.addWidget(delay_group)
        
        # Лимиты
        limits_group = QGroupBox("📊 Лимиты отправки")
        limits_layout = QFormLayout()
        
        self.hourly_limit = QSpinBox()
        self.hourly_limit.setRange(1, 500)
        self.hourly_limit.setValue(50)
        self.hourly_limit.setSuffix(" писем/час")
        limits_layout.addRow("В час:", self.hourly_limit)
        
        self.daily_limit = QSpinBox()
        self.daily_limit.setRange(1, 2000)
        self.daily_limit.setValue(200)
        self.daily_limit.setSuffix(" писем/день")
        limits_layout.addRow("В день:", self.daily_limit)
        
        limits_group.setLayout(limits_layout)
        layout.addWidget(limits_group)
        
        # Информация
        info = QLabel(
            "💡 <b>Советы:</b><br>"
            "• Задержка 5-30 секунд — стандарт для массовых рассылок<br>"
            "• Лимит 50 писем/час — безопасный для большинства провайдеров<br>"
            "• Для Gmail/Yandex рекомендуется использовать App Password"
        )
        info.setWordWrap(True)
        layout.addWidget(info)
        
        layout.addStretch()
        
        # Регистрация полей
        self.registerField("delay_min", self.delay_min)
        self.registerField("delay_max", self.delay_max)
        self.registerField("hourly_limit", self.hourly_limit)
        self.registerField("daily_limit", self.daily_limit)
    
    def _load_smtp_accounts(self):
        """Загрузить SMTP аккаунты"""
        db = SessionLocal()
        try:
            accounts = db.query(SMTPAccount).filter_by(is_active=True).all()
            self.smtp_combo.clear()
            
            for a in accounts:
                label = f"{a.name} ({a.email})"
                if a.is_primary:
                    label += " [основной]"
                self.smtp_combo.addItem(label, a.id)
        
        finally:
            db.close()
    
    def validatePage(self):
        """Валидация"""
        if self.smtp_combo.count() == 0:
            QMessageBox.warning(self, "Внимание", "Нет настроенных SMTP аккаунтов")
            return False
        
        # Сохранить выбор SMTP
        wizard = self.wizard()
        if wizard:
            wizard.selected_smtp_account_id = self.smtp_combo.currentData()
        
        # Проверить задержки
        if self.delay_min.value() > self.delay_max.value():
            QMessageBox.warning(self, "Внимание", "Минимальная задержка не может быть больше максимальной")
            return False
        
        return True


# === Страница 4: Подтверждение ===

class PageConfirm(QWizardPage):
    """Страница подтверждения"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Шаг 4: Подтверждение")
        self.setSubTitle("Проверьте настройки и запустите рассылку")
        
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        self.summary = QTextEdit()
        self.summary.setReadOnly(True)
        layout.addWidget(self.summary)
        
        # Предупреждение
        warning = QLabel(
            "⚠️ <b>Внимание:</b> После запуска рассылки письма будут отправляться автоматически. "
            "Убедитесь, что все настройки верны."
        )
        warning.setWordWrap(True)
        layout.addWidget(warning)
    
    def initializePage(self):
        """Обновить summary при открытии страницы"""
        wizard = self.wizard()
        if not wizard:
            return
        
        db = SessionLocal()
        try:
            # Получить данные
            profile = db.query(Profile).filter_by(id=wizard.selected_profile_id).first()
            template = db.query(Template).filter_by(id=wizard.selected_template_id).first()
            smtp = db.query(SMTPAccount).filter_by(id=wizard.selected_smtp_account_id).first()
            contacts_count = len(wizard.selected_contact_ids)
            
            # Рассчитать время
            delay_avg = (self.field("delay_min") + self.field("delay_max")) // 2
            estimated_time = contacts_count * delay_avg
            
            hours = estimated_time // 3600
            minutes = (estimated_time % 3600) // 60
            
            time_str = ""
            if hours > 0:
                time_str += f"{hours} ч "
            time_str += f"{minutes} мин"
            
            # Сформировать summary
            text = f"""
<h2>📋 Сводка рассылки</h2>

<table>
<tr><td><b>Название:</b></td><td>{self.field("mailing_name")}</td></tr>
<tr><td><b>Профиль:</b></td><td>{profile.name if profile else '---'}</td></tr>
<tr><td><b>Шаблон:</b></td><td>{template.name if template else '---'}</td></tr>
<tr><td><b>Получателей:</b></td><td>{contacts_count}</td></tr>
<tr><td><b>SMTP аккаунт:</b></td><td>{smtp.email if smtp else '---'}</td></tr>
</table>

<h3>⚙️ Параметры отправки</h3>
<table>
<tr><td>Задержка:</td><td>{self.field("delay_min")}-{self.field("delay_max")} сек</td></tr>
<tr><td>Лимит в час:</td><td>{self.field("hourly_limit")} писем</td></tr>
<tr><td>Лимит в день:</td><td>{self.field("daily_limit")} писем</td></tr>
<tr><td>Оценка времени:</td><td>~{time_str}</td></tr>
</table>

<p><b>✅ Рассылка будет создана в статусе "Черновик".</b><br>
После создания вы сможете запустить её из главного окна.</p>
"""
            self.summary.setHtml(text)
        
        finally:
            db.close()
