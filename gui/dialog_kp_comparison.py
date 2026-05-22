"""
Диалог сравнения коммерческих предложений
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView, QGroupBox,
    QMessageBox, QFileDialog, QSplitter, QCheckBox, QSpinBox,
    QTextEdit, QTabWidget, QWidget
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor
from loguru import logger


class DialogKPComparison(QDialog):
    """
    Диалог сравнения коммерческих предложений
    
    Функции:
    - Выбор диалогов для сравнения
    - Отображение сводной таблицы
    - Сравнение цен по позициям
    - Экспорт в Excel
    """
    
    def __init__(self, db_session, parent=None):
        super().__init__(parent)
        self.db_session = db_session
        self.comparison_service = None
        
        self.selected_dialogues = []
        
        self.setWindowTitle("Сравнение КП")
        self.setMinimumSize(1200, 700)
        
        self._setup_ui()
        self._load_dialogues()
        
        logger.info("DialogKPComparison открыт")
    
    def _setup_ui(self):
        """Настройка интерфейса"""
        layout = QVBoxLayout(self)
        
        # Заголовок
        header = QLabel("📊 Сравнение коммерческих предложений")
        header.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        layout.addWidget(header)
        
        # Выбор диалогов
        selection_panel = self._create_selection_panel()
        layout.addWidget(selection_panel)
        
        # Вкладки
        tabs = QTabWidget()
        
        # Вкладка 1: Сводная таблица
        tab_summary = self._create_summary_tab()
        tabs.addTab(tab_summary, "📋 Сводная таблица")
        
        # Вкладка 2: Сравнение цен
        tab_prices = self._create_prices_tab()
        tabs.addTab(tab_prices, "💰 Сравнение цен")
        
        tabs.currentChanged.connect(self._on_tab_changed)
        layout.addWidget(tabs)
        
        # Кнопки
        buttons = self._create_buttons()
        layout.addLayout(buttons)
    
    def _create_selection_panel(self) -> QGroupBox:
        """Панель выбора диалогов"""
        group = QGroupBox("Выберите диалоги для сравнения")
        layout = QVBoxLayout()
        
        # Список диалогов
        self.dialogues_list = QTableWidget()
        self.dialogues_list.setColumnCount(5)
        self.dialogues_list.setHorizontalHeaderLabels([
            "✔️", "ID", "Компания", "Email", "Получено"
        ])
        self.dialogues_list.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.dialogues_list.selectionBehavior = self.dialogues_list.SelectionBehavior.SelectRows
        self.dialogues_list.itemChanged.connect(self._on_dialogue_checked)
        layout.addWidget(self.dialogues_list)
        
        # Счётчик
        self.lbl_selected_count = QLabel("Выбрано: 0")
        layout.addWidget(self.lbl_selected_count)
        
        group.setLayout(layout)
        return group
    
    def _create_summary_tab(self) -> QWidget:
        """Вкладка 'Сводная таблица'"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Таблица сравнения
        self.table_comparison = QTableWidget()
        self.table_comparison.setColumnCount(9)
        self.table_comparison.setHorizontalHeaderLabels([
            "Компания", "Контакт", "Email", "Общая цена", "Валюта",
            "Поставка", "Оплата", "Позиций", "Заметки"
        ])
        self.table_comparison.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_comparison.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table_comparison.setAlternatingRowColors(True)
        layout.addWidget(self.table_comparison)
        
        # Статистика
        stats_layout = QHBoxLayout()
        
        self.lbl_best_price = QLabel("Лучшая цена: -")
        self.lbl_best_price.setStyleSheet("font-weight: bold; color: green;")
        stats_layout.addWidget(self.lbl_best_price)
        
        self.lbl_best_delivery = QLabel("Лучший срок: -")
        self.lbl_best_delivery.setStyleSheet("font-weight: bold; color: blue;")
        stats_layout.addWidget(self.lbl_best_delivery)
        
        stats_layout.addStretch()
        
        layout.addLayout(stats_layout)
        
        return widget
    
    def _create_prices_tab(self) -> QWidget:
        """Вкладка 'Сравнение цен'"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Предупреждение
        warning = QLabel("💡 Сравнение цен по позициям доступно при наличии одинаковых услуг")
        warning.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(warning)
        
        # Таблица цен
        self.table_prices = QTableWidget()
        self.table_prices.setAlternatingRowColors(True)
        layout.addWidget(self.table_prices)
        
        return widget
    
    def _create_buttons(self) -> QHBoxLayout:
        """Кнопки"""
        layout = QHBoxLayout()
        
        # Кнопка сравнить
        self.btn_compare = QPushButton("🔍 Сравнить")
        self.btn_compare.clicked.connect(self._perform_comparison)
        self.btn_compare.setEnabled(False)
        layout.addWidget(self.btn_compare)
        
        # Кнопка экспорта
        self.btn_export = QPushButton("📤 Экспорт в Excel")
        self.btn_export.clicked.connect(self._export_to_excel)
        self.btn_export.setEnabled(False)
        layout.addWidget(self.btn_export)
        
        layout.addStretch()
        
        # Кнопка закрыть
        btn_close = QPushButton("Закрыть")
        btn_close.clicked.connect(self.reject)
        layout.addWidget(btn_close)
        
        return layout
    
    def _load_dialogues(self):
        """Загрузка диалогов из БД"""
        from core.models import Dialogue
        
        self.dialogues_list.setRowCount(0)
        
        # Получаем диалоги со статусом kp_received
        dialogues = self.db_session.query(Dialogue).filter(
            Dialogue.status.in_(["kp_received", "clarifying"])
        ).order_by(Dialogue.created_at.desc()).limit(50).all()
        
        self.dialogues_list.setRowCount(len(dialogues))
        
        for i, dialogue in enumerate(dialogues):
            # Чекбокс
            checkbox = QCheckBox()
            checkbox.setChecked(False)
            checkbox.setEnabled(True)
            self.dialogues_list.setCellWidget(i, 0, checkbox)
            
            # ID
            item_id = QTableWidgetItem(str(dialogue.id))
            item_id.setFlags(item_id.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.dialogues_list.setItem(i, 1, item_id)
            
            # Компания (из темы)
            company = dialogue.subject[:30] if dialogue.subject else "Не указано"
            item_company = QTableWidgetItem(company)
            item_company.setFlags(item_company.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.dialogues_list.setItem(i, 2, item_company)
            
            # Email
            item_email = QTableWidgetItem(dialogue.sender_email or "-")
            item_email.setFlags(item_email.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.dialogues_list.setItem(i, 3, item_email)
            
            # Дата
            created_at = dialogue.created_at.strftime("%Y-%m-%d %H:%M") if dialogue.created_at else "-"
            item_date = QTableWidgetItem(created_at)
            item_date.setFlags(item_date.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.dialogues_list.setItem(i, 4, item_date)
            
            # Сохраняем ID диалога
            self.dialogues_list.item(i, 1).setData(Qt.ItemDataRole.UserRole, dialogue.id)
        
        logger.info(f"Загружено {len(dialogues)} диалогов")
    
    def _on_dialogue_checked(self, item):
        """Изменение выбора диалога"""
        if item.column() == 0:  # Чекбокс
            row = item.row()
            dialogue_id = self.dialogues_list.item(row, 1).data(Qt.ItemDataRole.UserRole)
            
            if item.checkState() == Qt.CheckState.Checked:
                if dialogue_id not in self.selected_dialogues:
                    self.selected_dialogues.append(dialogue_id)
            else:
                if dialogue_id in self.selected_dialogues:
                    self.selected_dialogues.remove(dialogue_id)
            
            # Обновить счётчик
            self.lbl_selected_count.setText(f"Выбрано: {len(self.selected_dialogues)}")
            
            # Включить кнопку сравнения (нужно минимум 2)
            self.btn_compare.setEnabled(len(self.selected_dialogues) >= 2)
    
    def _on_tab_changed(self, index):
        """Переключение вкладок"""
        pass
    
    def _perform_comparison(self):
        """Выполнить сравнение"""
        if len(self.selected_dialogues) < 2:
            QMessageBox.warning(self, "Ошибка", "Выберите минимум 2 диалога для сравнения")
            return
        
        # Инициализировать сервис
        from services.kp_comparison_service import KPComparisonService
        self.comparison_service = KPComparisonService()
        
        # Выполнить сравнение
        try:
            # Сводная таблица
            self._load_summary_table()
            
            # Сравнение цен
            self._load_prices_table()
            
            # Включить экспорт
            self.btn_export.setEnabled(True)
            
            QMessageBox.information(
                self,
                "Успех",
                f"Сравнено {len(self.selected_dialogues)} КП"
            )
            
        except Exception as e:
            logger.error(f"Ошибка сравнения: {e}")
            QMessageBox.critical(self, "Ошибка", f"Ошибка сравнения: {e}")
    
    def _load_summary_table(self):
        """Загрузить сводную таблицу"""
        if not self.comparison_service:
            return
        
        matrix = self.comparison_service.get_comparison_matrix(self.selected_dialogues)
        
        self.table_comparison.setRowCount(len(matrix))
        
        for i, row in enumerate(matrix):
            # Компания
            item_company = QTableWidgetItem(row["company"])
            # Подсветка лучшей цены
            if self.comparison_service and self.comparison_service.comparisons:
                best = self.comparison_service.comparisons[-1].get("best_price")
                if best and best["dialogue_id"] == row["dialogue_id"]:
                    item_company.setForeground(QColor("green"))
                    item_company.setText("⭐ " + row["company"])
            self.table_comparison.setItem(i, 0, item_company)
            
            # Контакт
            self.table_comparison.setItem(i, 1, QTableWidgetItem(row["contact"]))
            
            # Email
            self.table_comparison.setItem(i, 2, QTableWidgetItem(row["email"]))
            
            # Цена
            price_item = QTableWidgetItem(f"{row['total_price']:,.0f}")
            price_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table_comparison.setItem(i, 3, price_item)
            
            # Валюта
            self.table_comparison.setItem(i, 4, QTableWidgetItem(row["currency"]))
            
            # Поставка
            self.table_comparison.setItem(i, 5, QTableWidgetItem(row["delivery_time"]))
            
            # Оплата
            self.table_comparison.setItem(i, 6, QTableWidgetItem(row["payment_terms"]))
            
            # Позиций
            self.table_comparison.setItem(i, 7, QTableWidgetItem(str(row["items_count"])))
            
            # Заметки
            self.table_comparison.setItem(i, 8, QTableWidgetItem(row["notes"]))
        
        # Обновить статистику
        if self.comparison_service.comparisons:
            comparison = self.comparison_service.comparisons[-1]
            
            if comparison.get("best_price"):
                best = comparison["best_price"]
                self.lbl_best_price.setText(
                    f"Лучшая цена: {best['company_name']} - {best['total_price']:,.0f} {best['currency']}"
                )
            
            if comparison.get("best_delivery"):
                best = comparison["best_delivery"]
                self.lbl_best_delivery.setText(
                    f"Лучший срок: {best['company_name']} - {best['delivery_time']}"
                )
    
    def _load_prices_table(self):
        """Загрузить таблицу цен"""
        if not self.comparison_service:
            return
        
        price_data = self.comparison_service.get_price_comparison(self.selected_dialogues)
        
        services = price_data["services"]
        companies = price_data["companies"]
        price_matrix = price_data["price_matrix"]
        
        if not services or not companies:
            self.table_prices.setRowCount(0)
            return
        
        # Таблица: строки = услуги, столбцы = компании
        self.table_prices.setRowCount(len(services))
        self.table_prices.setColumnCount(len(companies) + 1)
        
        # Заголовки
        self.table_prices.setHorizontalHeaderItem(0, QTableWidgetItem("Услуга"))
        for j, company in enumerate(companies):
            self.table_prices.setHorizontalHeaderItem(j + 1, QTableWidgetItem(company))
        
        # Данные
        for i, service in enumerate(services):
            # Название услуги
            item_service = QTableWidgetItem(service)
            item_service.setFont(QFont("Arial", 9, QFont.Weight.Bold))
            self.table_prices.setItem(i, 0, item_service)
            
            # Цены по компаниям
            for j, company in enumerate(companies):
                price = price_matrix[service].get(company, "-")
                item_price = QTableWidgetItem(str(price))
                item_price.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                
                # Подсветка минимальной цены
                if price != "-":
                    try:
                        price_num = float(str(price).replace(" ", ""))
                        min_price = min([
                            float(str(price_matrix[service][c]).replace(" ", ""))
                            for c in companies
                            if c in price_matrix[service] and str(price_matrix[service][c]).replace(" ", "").replace(",", ".").replace("-", "").isdigit()
                        ], default=None)
                        
                        if min_price and price_num == min_price:
                            item_price.setBackground(QColor("#90EE90"))  # Светло-зелёный
                    except (ValueError, AttributeError):
                        pass
                
                self.table_prices.setItem(i, j + 1, item_price)
        
        self.table_prices.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    
    def _export_to_excel(self):
        """Экспорт в Excel"""
        if not self.comparison_service:
            return
        
        # Выбор файла
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Экспорт сравнения КП",
            "",
            "Excel files (*.xlsx)"
        )
        
        if not filepath:
            return
        
        # Экспорт
        success = self.comparison_service.export_to_excel(self.selected_dialogues, filepath)
        
        if success:
            QMessageBox.information(self, "Успех", f"Данные экспортированы в:\n{filepath}")
        else:
            QMessageBox.warning(self, "Ошибка", "Не удалось экспортировать данные")
