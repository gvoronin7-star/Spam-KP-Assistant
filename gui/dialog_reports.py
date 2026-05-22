"""
Диалог отчётов и аналитики
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView, QGroupBox,
    QTabWidget, QMessageBox, QFileDialog, QSpinBox, QDateEdit,
    QComboBox, QScrollArea, QWidget, QFrame
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont, QColor
from loguru import logger
from datetime import datetime


class DialogReports(QDialog):
    """
    Диалог отчётов и аналитики
    
    Вкладки:
    - Дашборд (общая сводка)
    - Статистика КП
    - Топ отправителей
    - Временная шкала
    - Экспорт
    """
    
    def __init__(self, db_session, parent=None):
        super().__init__(parent)
        self.db_session = db_session
        self.analytics_service = None
        
        self.setWindowTitle("Отчёты и аналитика")
        self.setMinimumSize(1000, 700)
        
        self._setup_ui()
        self._load_dashboard()
        
        logger.info("DialogReports открыт")
    
    def _setup_ui(self):
        """Настройка интерфейса"""
        layout = QVBoxLayout(self)
        
        # Заголовок
        header = QLabel("📈 Отчёты и аналитика")
        header.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        layout.addWidget(header)
        
        # Вкладки
        tabs = QTabWidget()
        
        # Вкладка 1: Дашборд
        tab_dashboard = self._create_dashboard_tab()
        tabs.addTab(tab_dashboard, "📊 Дашборд")
        
        # Вкладка 2: Статистика КП
        tab_kp = self._create_kp_stats_tab()
        tabs.addTab(tab_kp, "💰 Статистика КП")
        
        # Вкладка 3: Топ отправителей
        tab_senders = self._create_senders_tab()
        tabs.addTab(tab_senders, "📧 Топ отправителей")
        
        # Вкладка 4: Временная шкала
        tab_timeline = self._create_timeline_tab()
        tabs.addTab(tab_timeline, "📅 Временная шкала")
        
        # Вкладка 5: Экспорт
        tab_export = self._create_export_tab()
        tabs.addTab(tab_export, "📤 Экспорт")
        
        layout.addWidget(tabs)
    
    def _create_dashboard_tab(self) -> QWidget:
        """Вкладка 'Дашборд'"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Скролл-область
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        
        content = QWidget()
        content_layout = QVBoxLayout(content)
        
        # Общая статистика
        overview_group = QGroupBox("📊 Общая статистика")
        overview_layout = QHBoxLayout()
        
        # Карточки метрик
        self.card_total_dialogues = self._create_metric_card("Всего диалогов", "0")
        overview_layout.addWidget(self.card_total_dialogues)
        
        self.card_total_messages = self._create_metric_card("Всего сообщений", "0")
        overview_layout.addWidget(self.card_total_messages)
        
        self.card_contacts = self._create_metric_card("Контактов", "0")
        overview_layout.addWidget(self.card_contacts)
        
        self.card_kp_received = self._create_metric_card("КП получено", "0", "#4CAF50")
        overview_layout.addWidget(self.card_kp_received)
        
        overview_group.setLayout(overview_layout)
        content_layout.addWidget(overview_group)
        
        # Метрики эффективности
        efficiency_group = QGroupBox("⚡ Метрики эффективности")
        efficiency_layout = QHBoxLayout()
        
        self.card_auto_reply = self._create_metric_card("Автоответы", "0%", "#2196F3")
        efficiency_layout.addWidget(self.card_auto_reply)
        
        self.card_kp_rate = self._create_metric_card("КП", "0%", "#FF9800")
        efficiency_layout.addWidget(self.card_kp_rate)
        
        self.card_spam_rate = self._create_metric_card("Спам", "0%", "#F44336")
        efficiency_layout.addWidget(self.card_spam_rate)
        
        efficiency_group.setLayout(efficiency_layout)
        content_layout.addWidget(efficiency_group)
        
        # Топ отправителей (кратко)
        top_senders_group = QGroupBox("🏆 Топ отправителей")
        top_senders_layout = QVBoxLayout()
        
        self.table_top_senders = QTableWidget()
        self.table_top_senders.setColumnCount(3)
        self.table_top_senders.setHorizontalHeaderLabels(["Email", "Диалогов", "КП"])
        self.table_top_senders.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_top_senders.setMaximumHeight(150)
        top_senders_layout.addWidget(self.table_top_senders)
        
        top_senders_group.setLayout(top_senders_layout)
        content_layout.addWidget(top_senders_group)
        
        content_layout.addStretch()
        
        scroll.setWidget(content)
        layout.addWidget(scroll)
        
        return widget
    
    def _create_kp_stats_tab(self) -> QWidget:
        """Вкладка 'Статистика КП'"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Общая информация
        info_group = QGroupBox("📋 Общая информация")
        info_layout = QHBoxLayout()
        
        self.lbl_kp_total = QLabel("Всего КП: 0")
        self.lbl_kp_total.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        info_layout.addWidget(self.lbl_kp_total)
        
        self.lbl_kp_companies = QLabel("Компаний: 0")
        info_layout.addWidget(self.lbl_kp_companies)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # Цены
        price_group = QGroupBox("💰 Диапазон цен")
        price_layout = QHBoxLayout()
        
        self.lbl_price_min = QLabel("Мин: -")
        self.lbl_price_min.setStyleSheet("color: green; font-weight: bold;")
        price_layout.addWidget(self.lbl_price_min)
        
        self.lbl_price_max = QLabel("Макс: -")
        self.lbl_price_max.setStyleSheet("color: red; font-weight: bold;")
        price_layout.addWidget(self.lbl_price_max)
        
        self.lbl_price_avg = QLabel("Сред: -")
        self.lbl_price_avg.setStyleSheet("color: blue; font-weight: bold;")
        price_layout.addWidget(self.lbl_price_avg)
        
        price_group.setLayout(price_layout)
        layout.addWidget(price_group)
        
        # Таблица КП
        kp_table_group = QGroupBox("📄 Список КП")
        kp_table_layout = QVBoxLayout()
        
        self.table_kp = QTableWidget()
        self.table_kp.setColumnCount(5)
        self.table_kp.setHorizontalHeaderLabels(["ID", "Компания", "Email", "Дата", "Цена"])
        self.table_kp.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_kp.setAlternatingRowColors(True)
        kp_table_layout.addWidget(self.table_kp)
        
        kp_table_group.setLayout(kp_table_layout)
        layout.addWidget(kp_table_group)
        
        return widget
    
    def _create_senders_tab(self) -> QWidget:
        """Вкладка 'Топ отправителей'"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Фильтр
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Количество:"))
        
        self.spin_senders_limit = QSpinBox()
        self.spin_senders_limit.setRange(5, 100)
        self.spin_senders_limit.setValue(10)
        self.spin_senders_limit.valueChanged.connect(self._refresh_senders)
        filter_layout.addWidget(self.spin_senders_limit)
        
        filter_layout.addStretch()
        
        btn_refresh = QPushButton("🔄 Обновить")
        btn_refresh.clicked.connect(self._refresh_senders)
        filter_layout.addWidget(btn_refresh)
        
        layout.addLayout(filter_layout)
        
        # Таблица отправителей
        self.table_senders = QTableWidget()
        self.table_senders.setColumnCount(4)
        self.table_senders.setHorizontalHeaderLabels(["#", "Email", "Диалогов", "КП"])
        self.table_senders.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_senders.setAlternatingRowColors(True)
        layout.addWidget(self.table_senders)
        
        return widget
    
    def _create_timeline_tab(self) -> QWidget:
        """Вкладка 'Временная шкала'"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Период
        period_layout = QHBoxLayout()
        period_layout.addWidget(QLabel("Последних дней:"))
        
        self.spin_days = QSpinBox()
        self.spin_days.setRange(7, 365)
        self.spin_days.setValue(30)
        self.spin_days.valueChanged.connect(self._refresh_timeline)
        period_layout.addWidget(self.spin_days)
        
        period_layout.addStretch()
        
        btn_refresh = QPushButton("🔄 Обновить")
        btn_refresh.clicked.connect(self._refresh_timeline)
        period_layout.addWidget(btn_refresh)
        
        layout.addLayout(period_layout)
        
        # Таблица временной шкалы
        self.table_timeline = QTableWidget()
        self.table_timeline.setColumnCount(5)
        self.table_timeline.setHorizontalHeaderLabels(["Дата", "Всего", "КП", "Автоответы", "Спам"])
        self.table_timeline.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_timeline.setAlternatingRowColors(True)
        layout.addWidget(self.table_timeline)
        
        return widget
    
    def _create_export_tab(self) -> QWidget:
        """Вкладка 'Экспорт'"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Тип отчёта
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("Тип отчёта:"))
        
        self.combo_report_type = QComboBox()
        self.combo_report_type.addItem("Общая статистика", "overview")
        self.combo_report_type.addItem("Статистика КП", "kp")
        self.combo_report_type.addItem("Топ отправителей", "senders")
        type_layout.addWidget(self.combo_report_type)
        
        type_layout.addStretch()
        layout.addLayout(type_layout)
        
        # Описание
        desc_label = QLabel(
            "Экспорт статистики в CSV-файл. "
            "Файл можно открыть в Excel или Google Sheets."
        )
        desc_label.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(desc_label)
        
        layout.addSpacing(20)
        
        # Кнопка экспорта
        self.btn_export = QPushButton("📤 Экспорт в CSV")
        self.btn_export.clicked.connect(self._export_report)
        self.btn_export.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-size: 14px;
                padding: 10px 20px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        layout.addWidget(self.btn_export)
        
        layout.addStretch()
        
        return widget
    
    def _create_metric_card(self, title: str, value: str, color: str = "#607D8B") -> QFrame:
        """Создать карточку метрики"""
        card = QFrame()
        card.setFrameShape(QFrame.Shape.StyledPanel)
        card.setStyleSheet(f"""
            QFrame {{
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 8px;
                padding: 10px;
            }}
        """)
        
        layout = QVBoxLayout(card)
        
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("color: gray; font-size: 12px;")
        layout.addWidget(lbl_title)
        
        lbl_value = QLabel(value)
        lbl_value.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        lbl_value.setStyleSheet(f"color: {color};")
        layout.addWidget(lbl_value)
        
        return card
    
    def _load_dashboard(self):
        """Загрузить дашборд"""
        from services.analytics_service import AnalyticsService
        self.analytics_service = AnalyticsService()
        
        # Данные дашборда
        dashboard = self.analytics_service.generate_dashboard_data(self.db_session)
        
        # Общая статистика
        overview = dashboard["overview"]
        self._update_metric_card(self.card_total_dialogues, overview["total_dialogues"])
        self._update_metric_card(self.card_total_messages, overview["total_messages"])
        self._update_metric_card(self.card_contacts, overview["total_contacts"])
        self._update_metric_card(self.card_kp_received, overview["kp_received"])
        
        # Метрики эффективности
        efficiency = dashboard["efficiency"]
        self._update_metric_card(self.card_auto_reply, f"{efficiency['auto_reply_rate']}%")
        self._update_metric_card(self.card_kp_rate, f"{efficiency['kp_rate']}%")
        self._update_metric_card(self.card_spam_rate, f"{efficiency['spam_rate']}%")
        
        # Топ отправителей
        self._load_top_senders_table(dashboard["top_senders"])
    
    def _update_metric_card(self, card: QFrame, value: str):
        """Обновить значение карточки"""
        layout = card.layout()
        if layout.count() >= 2:
            lbl_value = layout.itemAt(1).widget()
            if isinstance(lbl_value, QLabel):
                lbl_value.setText(str(value))
    
    def _load_top_senders_table(self, senders: list):
        """Загрузить таблицу топ отправителей"""
        self.table_top_senders.setRowCount(len(senders))
        
        for i, sender in enumerate(senders):
            self.table_top_senders.setItem(i, 0, QTableWidgetItem(sender["email"]))
            self.table_top_senders.setItem(i, 1, QTableWidgetItem(str(sender["dialogue_count"])))
            self.table_top_senders.setItem(i, 2, QTableWidgetItem(str(sender["kp_count"])))
    
    def _refresh_senders(self):
        """Обновить топ отправителей"""
        limit = self.spin_senders_limit.value()
        senders = self.analytics_service.get_top_senders(self.db_session, limit)
        
        self.table_senders.setRowCount(len(senders))
        
        for i, sender in enumerate(senders):
            self.table_senders.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            self.table_senders.setItem(i, 1, QTableWidgetItem(sender["email"]))
            self.table_senders.setItem(i, 2, QTableWidgetItem(str(sender["dialogue_count"])))
            self.table_senders.setItem(i, 3, QTableWidgetItem(str(sender["kp_count"])))
    
    def _refresh_timeline(self):
        """Обновить временную шкалу"""
        days = self.spin_days.value()
        timeline = self.analytics_service.get_dialogue_timeline(self.db_session, days)
        
        self.table_timeline.setRowCount(len(timeline))
        
        for i, day in enumerate(timeline):
            self.table_timeline.setItem(i, 0, QTableWidgetItem(day["date"]))
            self.table_timeline.setItem(i, 1, QTableWidgetItem(str(day["total"])))
            self.table_timeline.setItem(i, 2, QTableWidgetItem(str(day["kp_received"])))
            self.table_timeline.setItem(i, 3, QTableWidgetItem(str(day["auto_replied"])))
            self.table_timeline.setItem(i, 4, QTableWidgetItem(str(day["spam"])))
    
    def _export_report(self):
        """Экспорт отчёта"""
        report_type = self.combo_report_type.currentData()
        
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Экспорт отчёта",
            "",
            "CSV files (*.csv)"
        )
        
        if not filepath:
            return
        
        success = self.analytics_service.export_report_to_csv(
            self.db_session, filepath, report_type
        )
        
        if success:
            QMessageBox.information(
                self,
                "Успех",
                f"Отчёт экспортирован в:\n{filepath}"
            )
        else:
            QMessageBox.warning(self, "Ошибка", "Не удалось экспортировать отчёт")
