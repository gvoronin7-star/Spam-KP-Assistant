"""
Главное окно приложения
"""
from PyQt6.QtWidgets import (
    QMainWindow, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QStatusBar, QMenuBar, QMenu, QMessageBox,
    QListWidget, QListWidgetItem, QGroupBox, QFormLayout, QLineEdit,
    QWizard, QDialog
)
from PyQt6.QtCore import Qt, QTimer
from loguru import logger
from typing import Optional


class MainWindow(QMainWindow):
    """Главное окно с вкладками"""
    
    def __init__(self):
        super().__init__()
        from config import __version__
        self.setWindowTitle(f"Спам-КП-ассистент v{__version__}")
        self.setMinimumSize(1200, 800)
        
        self._setup_ui()
        self._setup_menu()
        self._setup_status_bar()
        
        # Инициализация планировщика (опционально)
        self.scheduler_service: Optional = None
        self._init_scheduler()
        
        # Проверить статус LLM
        self._check_llm_status()
        
        # Показ приветствия при первом запуске
        self._show_welcome_if_first_run()
        
        logger.info("Главное окно создано")
    
    def _setup_ui(self):
        """Настройка интерфейса"""
        # Центральная виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Панель быстрых действий
        quick_actions = self._create_quick_actions()
        layout.addWidget(quick_actions)
        
        # Вкладки
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        # Создание вкладок
        self._create_tabs()
    
    def _create_quick_actions(self) -> QWidget:
        """Панель быстрых действий"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Кнопки
        self.btn_new_profile = QPushButton("➕ Новый профиль")
        self.btn_new_profile.clicked.connect(self._new_profile)
        
        self.btn_check_mail = QPushButton("📬 Проверить почту")
        self.btn_check_mail.clicked.connect(self._check_mail)
        
        self.btn_new_mailing = QPushButton("📧 Создать рассылку")
        self.btn_new_mailing.clicked.connect(self._new_mailing)
        
        self.btn_welcome = QPushButton("💡 Демо/Помощь")
        self.btn_welcome.clicked.connect(self._show_welcome_dialog)
        self.btn_welcome.setStyleSheet("""
            QPushButton {
                background-color: #ffc107;
                color: black;
                font-weight: bold;
                padding: 5px 10px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #ffca2c;
            }
        """)
        
        layout.addWidget(self.btn_new_profile)
        layout.addWidget(self.btn_check_mail)
        layout.addWidget(self.btn_new_mailing)
        
        # Кнопка управления правилами
        self.btn_rule_manager = QPushButton("⚙️ Правила")
        self.btn_rule_manager.setToolTip("Управление правилами автоматизации")
        self.btn_rule_manager.clicked.connect(self._manage_rules)
        layout.addWidget(self.btn_rule_manager)
        
        # Кнопка сравнения КП
        self.btn_kp_comparison = QPushButton("📊 Сравнение КП")
        self.btn_kp_comparison.setToolTip("Сравнить коммерческие предложения")
        self.btn_kp_comparison.clicked.connect(self._compare_kp)
        layout.addWidget(self.btn_kp_comparison)
        
        # Кнопка отчётов
        self.btn_reports = QPushButton("📈 Отчёты")
        self.btn_reports.setToolTip("Отчёты и аналитика")
        self.btn_reports.clicked.connect(self._show_reports)
        layout.addWidget(self.btn_reports)
        
        layout.addStretch()
        
        # Статус LLM
        self.llm_status = QLabel("LLM: Не настроен")
        self.llm_status.setStyleSheet("color: red; font-weight: bold;")
        layout.addWidget(self.llm_status)
        
        return widget
    
    def _add_search_bar(self, layout, list_widget, placeholder="Поиск..."):
        """Добавить поле поиска над списком"""
        search_layout = QHBoxLayout()
        search_edit = QLineEdit()
        search_edit.setPlaceholderText(f"🔍 {placeholder}")
        search_edit.setClearButtonEnabled(True)
        search_edit.textChanged.connect(
            lambda text, lw=list_widget: self._filter_list(lw, text)
        )
        search_layout.addWidget(search_edit)
        layout.addLayout(search_layout)
        return search_edit
    
    def _filter_list(self, list_widget: QListWidget, filter_text: str):
        """Фильтровать элементы списка по тексту"""
        filter_lower = filter_text.lower().strip()
        for i in range(list_widget.count()):
            item = list_widget.item(i)
            if filter_lower:
                item.setHidden(filter_lower not in item.text().lower())
            else:
                item.setHidden(False)
    
    def _create_tabs(self):
        """Создание вкладок"""
        # Профили закупок
        profiles_tab = QWidget()
        profiles_layout = QVBoxLayout(profiles_tab)
        
        # Заголовок (без кнопки)
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("📋 Профили закупок"))
        header_layout.addStretch()
        profiles_layout.addLayout(header_layout)
        
        # Список профилей (загрузка из БД)
        self.profiles_list = QListWidget()
        self.profiles_list.setMinimumHeight(200)
        profiles_layout.addWidget(self.profiles_list)
        
        # Поиск
        self._add_search_bar(profiles_layout, self.profiles_list, "Поиск профилей...")
        
        self.lbl_profile_count = QLabel("Всего профилей: 0")
        profiles_layout.addWidget(self.lbl_profile_count)
        
        self._load_profiles()  # Загрузка ПОСЛЕ создания метки
        
        self.tabs.addTab(profiles_tab, "📋 Профили")
        
        # Контакты
        contacts_tab = QWidget()
        contacts_layout = QVBoxLayout(contacts_tab)
        
        # Заголовок
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("👥 Контакты поставщиков"))
        header_layout.addStretch()
        btn_import = QPushButton("📥 Импорт")
        btn_import.clicked.connect(self._import_contacts)
        header_layout.addWidget(btn_import)
        btn_add_contact = QPushButton("➕ Добавить")
        btn_add_contact.clicked.connect(self._add_contact)
        header_layout.addWidget(btn_add_contact)
        contacts_layout.addLayout(header_layout)
        
        # Список контактов (загрузка из БД)
        self.contacts_list = QListWidget()
        self.contacts_list.setMinimumHeight(200)
        contacts_layout.addWidget(self.contacts_list)
        
        # Поиск
        self._add_search_bar(contacts_layout, self.contacts_list, "Поиск контактов...")
        
        self.lbl_contact_count = QLabel("Всего контактов: 0")
        contacts_layout.addWidget(self.lbl_contact_count)
        
        self._load_contacts()  # Загрузка ПОСЛЕ создания метки
        
        self.tabs.addTab(contacts_tab, "👥 Контакты")
        
        # Шаблоны
        templates_tab = QWidget()
        templates_layout = QVBoxLayout(templates_tab)
        
        # Заголовок
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("📝 Шаблоны писем"))
        header_layout.addStretch()
        btn_new_template = QPushButton("➕ Создать")
        btn_new_template.clicked.connect(self._new_template)
        header_layout.addWidget(btn_new_template)
        templates_layout.addLayout(header_layout)
        
        # Список шаблонов (загрузка из БД)
        self.templates_list = QListWidget()
        self.templates_list.setMinimumHeight(200)
        self.templates_list.itemDoubleClicked.connect(self._edit_template)
        templates_layout.addWidget(self.templates_list)
        
        # Поиск
        self._add_search_bar(templates_layout, self.templates_list, "Поиск шаблонов...")
        
        self.lbl_template_count = QLabel("Всего шаблонов: 0")
        templates_layout.addWidget(self.lbl_template_count)
        
        self._load_templates()  # Загрузка ПОСЛЕ создания метки
        
        self.tabs.addTab(templates_tab, "📝 Шаблоны")
        
        # Переписка
        dialogues_tab = QWidget()
        dialogues_layout = QVBoxLayout(dialogues_tab)
        
        # Заголовок
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("💬 Переписка с поставщиками"))
        header_layout.addStretch()
        btn_refresh_dialogues = QPushButton("🔄 Обновить")
        btn_refresh_dialogues.setToolTip("Проверить почту и обновить список")
        btn_refresh_dialogues.clicked.connect(self._refresh_dialogues)
        header_layout.addWidget(btn_refresh_dialogues)
        dialogues_layout.addLayout(header_layout)
        
        # Список диалогов
        self.dialogues_list = QListWidget()
        self.dialogues_list.setMinimumHeight(200)
        self.dialogues_list.itemDoubleClicked.connect(self._view_dialogue_details)
        dialogues_layout.addWidget(self.dialogues_list)
        
        # Поиск
        self._add_search_bar(dialogues_layout, self.dialogues_list, "Поиск диалогов...")
        
        self.lbl_dialogue_count = QLabel("Всего диалогов: 0")
        dialogues_layout.addWidget(self.lbl_dialogue_count)
        
        self._load_dialogues()
        
        self.tabs.addTab(dialogues_tab, "💬 Переписка")
        
        # Задачи
        tasks_tab = QWidget()
        tasks_layout = QVBoxLayout(tasks_tab)
        
        # Заголовок
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("✅ Задачи оператора"))
        header_layout.addStretch()
        btn_refresh_tasks = QPushButton("🔄 Обновить")
        btn_refresh_tasks.clicked.connect(self._load_tasks)
        header_layout.addWidget(btn_refresh_tasks)
        tasks_layout.addLayout(header_layout)
        
        # Список задач
        self.tasks_list = QListWidget()
        self.tasks_list.setMinimumHeight(200)
        tasks_layout.addWidget(self.tasks_list)
        
        # Поиск
        self._add_search_bar(tasks_layout, self.tasks_list, "Поиск задач...")
        
        self.lbl_task_count = QLabel("Всего задач: 0")
        tasks_layout.addWidget(self.lbl_task_count)
        
        self._load_tasks()
        
        self.tabs.addTab(tasks_tab, "✅ Задачи")
        
        # Настройки
        settings_tab = QWidget()
        settings_layout = QVBoxLayout(settings_tab)
        settings_layout.addWidget(QLabel("⚙️ Настройки"))
        
        # Настройка LLM
        llm_group = QGroupBox("LLM (ProxyAPI)")
        llm_layout = QFormLayout()
        self.llm_api_key_label = QLabel("Загрузка...")
        llm_layout.addRow("API ключ:", self.llm_api_key_label)
        btn_configure_llm = QPushButton("Настроить LLM")
        btn_configure_llm.clicked.connect(self._configure_llm)
        llm_layout.addRow("", btn_configure_llm)
        llm_group.setLayout(llm_layout)
        settings_layout.addWidget(llm_group)
        
        # Настройка почты
        mail_group = QGroupBox("SMTP/IMAP аккаунты")
        mail_layout = QFormLayout()
        self.mail_accounts_label = QLabel("Загрузка...")
        mail_layout.addRow("Аккаунты:", self.mail_accounts_label)
        btn_configure_mail = QPushButton("Настроить аккаунты")
        btn_configure_mail.clicked.connect(self._configure_smtp)
        mail_layout.addRow("", btn_configure_mail)
        mail_group.setLayout(mail_layout)
        settings_layout.addWidget(mail_group)
        
        self.tabs.addTab(settings_tab, "⚙️ Настройки")
        
    def _check_llm_status(self):
        """Проверить статус LLM и обновить интерфейс"""
        from config import settings
        from services.inbox_service import InboxService
        
        # Проверить наличие API ключа
        if not settings.proxyapi_api_key:
            self.llm_status.setText("LLM: Не настроен")
            self.llm_status.setStyleSheet("color: red; font-weight: bold;")
            self.llm_api_key_label.setText("❌ Не настроен")
            self.llm_api_key_label.setStyleSheet("color: red;")
            logger.info("LLM: API ключ не найден")
            return
        
        # Попробовать создать InboxService и проверить LLM
        try:
            service = InboxService()
            if service.llm_service:
                model_name = settings.proxyapi_primary_model
                self.llm_status.setText(f"LLM: ✅ Активен ({model_name})")
                self.llm_status.setStyleSheet("color: green; font-weight: bold;")
                self.llm_api_key_label.setText("✅ Настроен")
                self.llm_api_key_label.setStyleSheet("color: green;")
                logger.info(f"LLM: Активен и готов к работе (модель: {model_name})")
            else:
                self.llm_status.setText("LLM: ⚠️ Ошибка инициализации")
                self.llm_status.setStyleSheet("color: orange; font-weight: bold;")
                self.llm_api_key_label.setText("⚠️ Ошибка")
                self.llm_api_key_label.setStyleSheet("color: orange;")
                logger.warning("LLM: API ключ есть, но инициализация не удалась")
        except Exception as e:
            self.llm_status.setText("LLM: ⚠️ Ошибка")
            self.llm_status.setStyleSheet("color: orange; font-weight: bold;")
            self.llm_api_key_label.setText(f"⚠️ {str(e)[:20]}")
            self.llm_api_key_label.setStyleSheet("color: orange;")
            logger.error(f"LLM: Ошибка проверки - {e}")
    
    def _setup_menu(self):
        """Настройка меню"""
        menubar = self.menuBar()
        
        # Файл
        file_menu = menubar.addMenu("Файл")
        
        new_profile_action = file_menu.addAction("Новый профиль")
        new_profile_action.triggered.connect(self._new_profile)
        
        import_contacts_action = file_menu.addAction("Импорт контактов")
        import_contacts_action.triggered.connect(self._import_contacts)
        
        file_menu.addSeparator()
        
        exit_action = file_menu.addAction("Выход")
        exit_action.triggered.connect(self.close)
        
        # Инструменты
        tools_menu = menubar.addMenu("Инструменты")
        
        check_mail_action = tools_menu.addAction("Проверить почту")
        check_mail_action.triggered.connect(self._check_mail)
        
        tools_menu.addSeparator()
        
        llm_agent_action = tools_menu.addAction("🤖 LLM Агент")
        llm_agent_action.triggered.connect(self._open_llm_agent)
        
        reminder_templates_action = tools_menu.addAction("📋 Шаблоны напоминаний")
        reminder_templates_action.triggered.connect(self._open_reminder_templates)
        
        rules_action = tools_menu.addAction("📋 Правила обработки")
        rules_action.triggered.connect(self._manage_rules)
        
        kp_compare_action = tools_menu.addAction("📊 Сравнение КП")
        kp_compare_action.triggered.connect(self._compare_kp)
        
        reports_action = tools_menu.addAction("📈 Отчёты")
        reports_action.triggered.connect(self._show_reports)
        
        # Справка
        help_menu = menubar.addMenu("Справка")
        
        welcome_action = help_menu.addAction("👋 Добро пожаловать")
        welcome_action.triggered.connect(self._show_welcome_dialog)
        
        about_action = help_menu.addAction("О программе")
        about_action.triggered.connect(self._show_about)
    
    def _setup_status_bar(self):
        """Настройка строки состояния"""
        self.statusBar().showMessage("Готов к работе")
    
    def _init_scheduler(self):
        """Инициализация планировщика фоновых задач"""
        from config import settings
        from services.scheduler_service import SchedulerService
        
        # Проверить, включена ли автоматическая проверка почты
        auto_check_enabled = settings.auto_check_email_enabled if hasattr(settings, 'auto_check_email_enabled') else True
        
        if auto_check_enabled:
            try:
                self.scheduler_service = SchedulerService()
                self.scheduler_service.start()
                
                # Настроить проверку почты (раз в час)
                check_interval = settings.email_check_interval_hours if hasattr(settings, 'email_check_interval_hours') else 1
                self.scheduler_service.setup_email_checker(
                    check_interval_hours=check_interval,
                    enabled=True
                )
                
                # Настроить отправку напоминаний (раз в 30 минут)
                self.scheduler_service.setup_reminder_sender(
                    check_interval_minutes=30,
                    enabled=True
                )
                
                # Настроить ежедневную очистку (в 2 часа ночи)
                self.scheduler_service.setup_daily_cleanup(
                    hour=2,
                    minute=0,
                    enabled=True
                )
                
                logger.info("Планировщик активирован")
                self.statusBar().showMessage("Планировщик запущен", 5000)
                
            except Exception as e:
                logger.error(f"Ошибка инициализации планировщика: {e}")
                self.statusBar().showMessage(f"Планировщик не запущен: {e}", 5000)
        else:
            logger.info("Автоматическая проверка почты отключена")
    
    def _load_profiles(self):
        """Загрузка профилей из БД"""
        from core.database import SessionLocal
        from core.models import Profile
        
        db = SessionLocal()
        try:
            profiles = db.query(Profile).filter_by(is_active=True).all()
            self.profiles_list.clear()
            
            for profile in profiles:
                item_text = f"{profile.name} (ID: {profile.id})"
                if profile.description:
                    item_text += f"\n   {profile.description[:50]}..."
                self.profiles_list.addItem(item_text)
            
            self.lbl_profile_count.setText(f"Всего профилей: {len(profiles)}")
        finally:
            db.close()
    
    def _load_contacts(self):
        """Загрузка контактов из БД"""
        from core.database import SessionLocal
        from core.models import Contact
        
        db = SessionLocal()
        try:
            contacts = db.query(Contact).filter_by(is_active=True).all()
            self.contacts_list.clear()
            
            for contact in contacts:
                item_text = f"{contact.email} ({contact.company_name})"
                if contact.contact_person:
                    item_text += f" - {contact.contact_person}"
                self.contacts_list.addItem(item_text)
            
            self.lbl_contact_count.setText(f"Всего контактов: {len(contacts)}")
        finally:
            db.close()
    
    def _load_templates(self):
        """Загрузка шаблонов из БД"""
        from core.database import SessionLocal
        from core.models import Template
        
        db = SessionLocal()
        try:
            templates = db.query(Template).filter_by(is_active=True).all()
            self.templates_list.clear()
            
            for template in templates:
                item_text = f"{template.name} ({template.template_type})"
                self.templates_list.addItem(item_text)
            
            self.lbl_template_count.setText(f"Всего шаблонов: {len(templates)}")
        finally:
            db.close()
    
    def _load_dialogues(self):
        """Загрузка диалогов из БД"""
        from core.database import SessionLocal
        from core.models import Dialogue, Message
        
        db = SessionLocal()
        try:
            dialogues = db.query(Dialogue).order_by(Dialogue.last_activity.desc()).all()
            self.dialogues_list.clear()
            
            for d in dialogues:
                contact_name = d.contact.company_name or "—"
                contact_person = d.contact.contact_person or ""
                email = d.contact.email or ""
                profile_name = d.profile.name if d.profile else "Без профиля"
                
                # Статус с иконкой
                status_map = {
                    "sent": ("📤", "Отправлено"),
                    "clarifying": ("❓", "Уточнение"),
                    "kp_received": ("📥", "КП получено"),
                    "rejected": ("❌", "Отказ"),
                    "reminder_sent": ("⏰", "Напоминание"),
                    "auto_replied": ("🤖", "Автоответ"),
                    "spam": ("🗑️", "Спам")
                }
                status_icon, status_text = status_map.get(d.status, ("📧", d.status))
                
                # Проверка новых сообщений (непрочитанные входящие)
                unread_count = db.query(Message).filter_by(
                    dialogue_id=d.id,
                    direction="inbound",
                    is_read=False
                ).count()
                
                # Формируем заголовок
                item_text = f"{status_icon} {contact_name}"
                if contact_person:
                    item_text += f" ({contact_person})"
                
                # Индикатор новых сообщений
                if unread_count > 0:
                    item_text = f"🔔 [{unread_count}] " + item_text
                
                item_text += f"\n   📧 {email}"
                item_text += f"\n   📋 {profile_name}"
                item_text += f"\n   ℹ️ {status_text}"
                
                if d.kp_received:
                    item_text += " | [КП]"
                
                # Создаём item
                item = QListWidgetItem(item_text)
                item.setData(Qt.ItemDataRole.UserRole, d.id)
                
                # Подсветка новых (бледно-голубой)
                if unread_count > 0:
                    item.setBackground(Qt.GlobalColor.cyan)
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)
                
                self.dialogues_list.addItem(item)
            
            self.lbl_dialogue_count.setText(f"Всего диалогов: {len(dialogues)}")
        finally:
            db.close()
    
    def _refresh_dialogues(self):
        """Обновить диалоги с проверкой почты"""
        from services.inbox_service import InboxService
        
        self.statusBar().showMessage("Проверка почты и обновление...")
        logger.info("Обновление диалогов с проверкой почты")
        
        try:
            # Проверить почту
            service = InboxService()
            processed = service.check_inbox()
            
            if processed:
                count = len(processed)
                self.statusBar().showMessage(f"Получено {count} новых писем!", 5000)
                logger.info(f"Обработано {count} новых писем")
            else:
                self.statusBar().showMessage("Новых писем нет, обновляю список...", 3000)
            
            # Обновить списки
            self._load_dialogues()
            self._load_tasks()
            
        except Exception as e:
            logger.error(f"Ошибка обновления: {e}")
            self.statusBar().showMessage(f"Ошибка обновления: {e}", 5000)
            QMessageBox.warning(self, "Ошибка", f"Не удалось обновить:\n{e}")
    
    def _view_dialogue_details(self, item):
        """Просмотр деталей диалога с полной перепиской"""
        from core.database import SessionLocal
        from core.models import Dialogue, Message
        
        dialogue_id = item.data(Qt.ItemDataRole.UserRole)
        if not dialogue_id:
            return
        
        db = SessionLocal()
        try:
            dialogue = db.query(Dialogue).filter_by(id=dialogue_id).first()
            if not dialogue:
                QMessageBox.warning(self, "Ошибка", "Диалог не найден")
                return
            
            # Загрузить связанные данные внутри сессии
            _ = dialogue.contact.company_name  # force load contact
            _ = dialogue.profile.name if dialogue.profile else None  # force load profile
            
            # Загрузить сообщения
            dialogue.messages = db.query(Message).filter_by(dialogue_id=dialogue.id).order_by(Message.created_at).all()
            
            # Пометить все входящие как прочитанные
            for msg in dialogue.messages:
                if msg.direction == "inbound" and not msg.is_read:
                    msg.is_read = True
            
            db.commit()  # Сохранить прочтение
            
            if not dialogue.messages:
                QMessageBox.information(
                    self,
                    "Диалог",
                    f"Диалог с: {dialogue.contact.company_name or dialogue.contact.email}\n\n"
                    f"Статус: {dialogue.status}\n"
                    f"Сообщений: 0\n"
                    f"Последняя активность: {dialogue.last_activity.strftime('%d.%m.%Y %H:%M') if dialogue.last_activity else 'Н/Д'}"
                )
                return
            
            # Загрузить все атрибуты сообщений
            for msg in dialogue.messages:
                _ = msg.subject
                _ = msg.body_plain
                _ = msg.body_html
                _ = msg.raw_body
                _ = msg.direction
                _ = msg.from_address
                _ = msg.to_address
                _ = msg.created_at
            
            # Закрыть сессию до открытия диалога
            db.close()
            db = None
            
            # Показать диалог просмотра сообщений
            from .dialog_message_viewer import DialogMessageViewer
            
            dialog = DialogMessageViewer(dialogue, self)
            dialog.exec()
            
            # Обновить список после закрытия (снять выделение)
            self._load_dialogues()
            
        except Exception as e:
            logger.error(f"Ошибка просмотра диалога: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Ошибка", f"Не удалось открыть диалог:\n{str(e)}")
        finally:
            if db:
                db.close()
    
    def _load_tasks(self):
        """Загрузка задач из БД"""
        from core.database import SessionLocal
        from core.models import Task
        
        db = SessionLocal()
        try:
            tasks = db.query(Task).filter_by(is_completed=False).order_by(Task.created_at.desc()).all()
            self.tasks_list.clear()
            
            for t in tasks:
                priority_icon = {
                    "low": "🔵",
                    "medium": "🟡",
                    "high": "🔴",
                    "critical": "🚨"
                }.get(t.priority, "⚪")
                
                # Дедлайн
                deadline_text = ""
                if t.due_date:
                    deadline_text = f" (до {t.due_date.strftime('%d.%m.%Y')})"
                
                item_text = f"{priority_icon} {t.title}{deadline_text}"
                self.tasks_list.addItem(item_text)
            
            self.lbl_task_count.setText(f"Активных задач: {len(tasks)}")
        finally:
            db.close()
    
    # === Обработчики событий ===
    
    def _new_profile(self):
        """Создать новый профиль"""
        logger.info("Открытие мастера создания профиля")
        
        from .wizard_profile import ProfileWizard
        from PyQt6.QtWidgets import QMessageBox
        
        try:
            wizard = ProfileWizard(self)
            wizard.profile_created.connect(self._on_profile_created)
            
            result = wizard.exec()
            if result == QDialog.DialogCode.Accepted:
                logger.info("Профиль успешно создан")
        except Exception as e:
            logger.error(f"Ошибка мастера профиля: {e}", exc_info=True)
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            QMessageBox.critical(
                self,
                "Ошибка",
                f"Не удалось открыть мастер создания профиля:\n\n{str(e)}\n\nПодробности в логе."
            )
    
    def _on_profile_created(self, profile_data):
        """Обработчик создания профиля"""
        logger.info(f"Профиль создан: {profile_data}")
        
        # Обновить список профилей
        self.profiles_list.addItem(f"{profile_data['name']} (ID: {profile_data['id']})")
        
        # Показать уведомление
        self.statusBar().showMessage(f"Профиль '{profile_data['name']}' создан!", 3000)
        
        QMessageBox.information(
            self,
            "Успех",
            f"Профиль '{profile_data['name']}' успешно создан!\n\n"
            f"ID: {profile_data['id']}"
        )
    
    def _import_contacts(self):
        """Импорт контактов"""
        logger.info("Открытие диалога импорта контактов")
        
        from .dialog_import_contacts import DialogImportContacts
        
        dialog = DialogImportContacts(self)
        dialog.contacts_imported.connect(self._on_contacts_imported)
        
        dialog.exec()
    
    def _on_contacts_imported(self, contacts):
        """Обработчик импорта контактов"""
        logger.info(f"Импортировано контактов: {len(contacts)}")
        
        # Обновить список
        for contact in contacts[:10]:  # Показать первые 10
            item_text = f"{contact['email']} ({contact['company_name']})"
            self.contacts_list.addItem(item_text)
        
        if len(contacts) > 10:
            self.contacts_list.addItem(f"... и ещё {len(contacts) - 10}")
        
        # Обновить счётчик
        self.lbl_contact_count.setText(f"Всего контактов: {len(contacts)}")
        
        # Показать уведомление
        self.statusBar().showMessage(f"Импортировано {len(contacts)} контактов!", 3000)
        
        QMessageBox.information(
            self,
            "Успех",
            f"Импортировано {len(contacts)} контактов!"
        )

    def _add_contact(self):
        """Добавить контакт"""
        logger.info("Добавление контакта")
        QMessageBox.information(self, "Скоро", "Ручное добавление контакта будет доступно в следующей версии")
        
    def _new_template(self):
        """Создать новый шаблон"""
        logger.info("Создание нового шаблона")
        
        try:
            from .dialog_template_editor import TemplateEditor
            
            dialog = TemplateEditor(parent=self)
            dialog.template_saved.connect(self._on_template_saved)
            dialog.exec()
        except Exception as e:
            logger.error(f"Ошибка создания шаблона: {e}", exc_info=True)
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            QMessageBox.critical(self, "Ошибка", f"Не удалось открыть редактор шаблонов:\n{str(e)}")
        
    def _edit_template(self, item):
        """Редактировать шаблон"""
        logger.info(f"Редактирование шаблона: {item.text()}")
        
        from core.database import SessionLocal
        from core.models import Template
        from .dialog_template_editor import TemplateEditor
        
        # Загрузить данные шаблона из БД
        db = SessionLocal()
        try:
            template_name = item.text().split(" (")[0]
            template = db.query(Template).filter_by(name=template_name).first()
            
            if template:
                template_data = {
                    "id": template.id,
                    "name": template.name,
                    "template_type": template.template_type or "initial",
                    "subject": template.subject or "",
                    "body_plain": template.body_plain or "",
                    "body_html": template.body_html or "",
                    "attachments": template.attachments or []
                }
            else:
                QMessageBox.warning(self, "Ошибка", f"Шаблон '{template_name}' не найден в БД")
                return
        finally:
            db.close()
        
        dialog = TemplateEditor(template_data, self)
        dialog.template_saved.connect(self._on_template_saved)
        dialog.exec()
    
    def _on_template_saved(self, template_data):
        """Обработчик сохранения шаблона"""
        logger.info(f"Шаблон {template_data['action']}: {template_data['name']}")
        
        # Обновить список
        if template_data['action'] == 'создан':
            self.templates_list.addItem(f"{template_data['name']} ({template_data['id']})")
            self.lbl_template_count.setText(f"Всего шаблонов: {self.templates_list.count()}")
        
        self.statusBar().showMessage(f"Шаблон '{template_data['name']}' сохранён!", 3000)
    
    def _check_mail(self):
        """Проверка почты"""
        from services.inbox_service import InboxService
        
        self.statusBar().showMessage("Проверка почты...")
        logger.info("Запуск проверки почты")
        
        try:
            service = InboxService()
            processed = service.check_inbox()
            
            if processed:
                count = len(processed)
                self.statusBar().showMessage(f"Получено {count} новых писем!", 5000)
                
                # Обновить вкладку переписки
                self._load_dialogues()
                self._load_tasks()
                
                QMessageBox.information(
                    self,
                    "Новые письма",
                    f"Получено и обработано {count} писем:\n\n" +
                    "\n".join([
                        f"• {p['from']}: {p['classification']}"
                        for p in processed[:5]
                    ])
                )
            else:
                self.statusBar().showMessage("Новых писем нет", 5000)
                QMessageBox.information(
                    self,
                    "Проверка почты",
                    "📭 Новых писем нет\n\n"
                    "Почтовые ящики проверены, новых сообщений не обнаружено."
                )
        
        except OSError as e:
            # Ошибки сети (DNS, подключение)
            logger.warning(f"Проверка почты: нет подключения - {e}")
            self.statusBar().showMessage("Почта не настроена", 3000)
            QMessageBox.information(
                self,
                "Проверка почты",
                "Почтовые аккаунты не настроены или нет подключения к интернету.\n\n"
                "Настройте SMTP/IMAP аккаунты в разделе ⚙️ Настройки."
            )
        
        except Exception as e:
            logger.error(f"Ошибка проверки почты: {e}")
            self.statusBar().showMessage(f"Ошибка проверки почты: {e}", 5000)
            QMessageBox.warning(self, "Ошибка", f"Не удалось проверить почту:\n{e}")

    def _new_mailing(self):
        """Создать рассылку"""
        logger.info("Запуск мастера создания рассылки")
        
        from .wizard_mailing import MailingWizard
        
        wizard = MailingWizard(self)
        wizard.mailing_created.connect(self._on_mailing_created)
        wizard.exec()
    
    def _on_mailing_created(self, mailing_id):
        """Обработчик создания рассылки"""
        logger.info(f"Рассылка создана: ID={mailing_id}")
        self.statusBar().showMessage(f"Рассылка создана! ID: {mailing_id}", 5000)
    
    def _run_llm(self):
        """Запустить LLM-обработку"""
        logger.info("Запуск LLM-обработки")
        # TODO: Реализовать обработку LLM
        QMessageBox.information(self, "Скоро", "LLM-обработка будет доступна после настройки API")
    
    def _configure_llm(self):
        """Настроить LLM"""
        logger.info("Открытие настройки LLM")
        QMessageBox.information(
            self,
            "Настройка ProxyAPI",
            "Введите API ключ ProxyAPI:\n\n"
            "1. Зарегистрируйтесь на https://console.proxyapi.ru/\n"
            "2. Получите ключ в разделе 'Ключи API'\n"
            "3. Вставьте ключ в файл .env"
        )
    
    def _configure_smtp(self):
        """Настроить SMTP/IMAP"""
        logger.info("Открытие настройки SMTP/IMAP")
        
        from .dialog_smtp_settings import DialogSMTPSettings
        
        dialog = DialogSMTPSettings(self)
        dialog.account_saved.connect(self._on_account_saved)
        dialog.exec()
    
    def _open_llm_agent(self):
        """Открыть диалог управления LLM-агентом"""
        logger.info("Открытие LLM Agent")
        
        from .dialog_llm_agent import DialogLLMAgent
        
        dialog = DialogLLMAgent(self)
        dialog.exec()
        
    def _open_reminder_templates(self):
        """Открыть редактор шаблонов напоминаний"""
        logger.info("Открытие редактора шаблонов напоминаний")
        
        from .dialog_reminder_templates import DialogReminderTemplates
        
        dialog = DialogReminderTemplates(self)
        dialog.exec()
        
    def _on_account_saved(self, account_data):
        """Обработчик сохранения аккаунта"""
        logger.info(f"Аккаунт сохранён: {account_data}")
        
        self.mail_accounts_label.setText(f"✅ 1 аккаунт ({account_data['email']})")
        self.mail_accounts_label.setStyleSheet("color: green;")
        
        self.statusBar().showMessage(f"SMTP аккаунт сохранён: {account_data['email']}", 3000)
    
    def _show_about(self):
        """О программе"""
        from config import __version__
        QMessageBox.about(
            self,
            "О программе",
            f"Спам-КП-ассистент v{__version__}\n\n"
            "Автоматизация получения коммерческих предложений\n"
            "от поставщиков телеком-услуг\n\n"
            "Разработчик: NLP-Core-Team\n"
            f"Версия: {__version__}"
        )

    def _show_welcome_if_first_run(self):
        """Показать приветствие если первый запуск"""
        from PyQt6.QtCore import QSettings
        
        settings = QSettings("NLP-Core-Team", "SpamKPAssistant")
        has_seen_welcome = settings.value("welcome_seen", False, type=bool)
        
        if not has_seen_welcome:
            # Запомнить, что показали (до показа)
            settings.setValue("welcome_seen", True)

            # Показать через таймер (чтобы главное окно успело отрисоваться)
            QTimer.singleShot(500, self._show_welcome_dialog)

    def _show_welcome_dialog(self):
        """Показать диалог приветствия"""
        from .dialog_welcome import DialogWelcome
        
        dialog = DialogWelcome(self)
        dialog.setModal(False)  # Не блокировать главное окно
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()

    def _manage_rules(self):
        """Управление правилами"""
        from services.inbox_service import InboxService
        from gui.dialog_rule_manager import DialogRuleManager
        
        # Получить RuleEngine из InboxService
        service = InboxService()
        rule_engine = service.rule_engine
        
        dialog = DialogRuleManager(rule_engine, parent=self)
        dialog.exec()
        
        logger.info("Управление правилами завершено")

    def _compare_kp(self):
        """Сравнение КП"""
        from core.database import SessionLocal
        from gui.dialog_kp_comparison import DialogKPComparison
        
        # Открыть диалог
        db = SessionLocal()
        try:
            dialog = DialogKPComparison(db, parent=self)
            dialog.exec()
        finally:
            db.close()
        
        logger.info("Сравнение КП завершено")

    def _show_reports(self):
        """Показать отчёты"""
        from core.database import SessionLocal
        from gui.dialog_reports import DialogReports
        
        # Открыть диалог
        db = SessionLocal()
        try:
            dialog = DialogReports(db, parent=self)
            dialog.exec()
        finally:
            db.close()
        
        logger.info("Отчёты закрыты")

    def closeEvent(self, event):
        """Обработчик закрытия окна"""
        logger.info("Закрытие главного окна")
        
        # Остановить планировщик
        if self.scheduler_service:
            try:
                self.scheduler_service.shutdown()
                logger.info("Планировщик остановлен")
            except Exception as e:
                logger.error(f"Ошибка остановки планировщика: {e}")
        
        event.accept()
