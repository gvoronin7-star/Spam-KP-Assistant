"""
Диалог просмотра данных КП
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QTableWidget, QTableWidgetItem, 
    QTextEdit, QGroupBox, QTabWidget, QMessageBox
)
from PyQt6.QtCore import Qt
from loguru import logger


class DialogKPViewer(QDialog):
    """Диалог для просмотра извлечённых данных КП"""
    
    def __init__(self, kp_data: dict, parent=None):
        super().__init__(parent)
        self.kp_data = kp_data
        
        self.setWindowTitle("📊 Данные КП")
        self.setMinimumSize(800, 600)
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Настройка интерфейса"""
        layout = QVBoxLayout(self)
        
        # Заголовок
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("📊 Коммерческое предложение"))
        header_layout.addStretch()
        
        btn_close = QPushButton("Закрыть")
        btn_close.clicked.connect(self.accept)
        header_layout.addWidget(btn_close)
        
        layout.addLayout(header_layout)
        
        # Табы
        tabs = QTabWidget()
        
        # Таблица цен
        prices_tab = QWidget()
        prices_layout = QVBoxLayout(prices_tab)
        
        self.table_prices = QTableWidget()
        self.table_prices.setColumnCount(4)
        self.table_prices.setHorizontalHeaderLabels([
            "Услуга", "Цена", "Валюта", "Действия"
        ])
        self.table_prices.horizontalHeader().setStretchLastSection(True)
        prices_layout.addWidget(self.table_prices)
        
        btn_edit_price = QPushButton("✏️ Редактировать")
        btn_edit_price.clicked.connect(self._edit_price)
        prices_layout.addWidget(btn_edit_price)
        
        tabs.addTab(prices_tab, "💰 Цены")
        
        # Условия
        terms_tab = QWidget()
        terms_layout = QVBoxLayout(terms_tab)
        
        self.txt_terms = QTextEdit()
        self.txt_terms.setReadOnly(True)
        terms_layout.addWidget(QLabel("Условия:"))
        terms_layout.addWidget(self.txt_terms)
        
        tabs.addTab(terms_tab, "📄 Условия")
        
        # Заметки
        notes_tab = QWidget()
        notes_layout = QVBoxLayout(notes_tab)
        
        self.txt_notes = QTextEdit()
        self.txt_notes.setReadOnly(True)
        notes_layout.addWidget(QLabel("Заметки:"))
        notes_layout.addWidget(self.txt_notes)
        
        tabs.addTab(notes_tab, "📝 Заметки")
        
        layout.addWidget(tabs)
        
        # Информация о вложениях
        if self.kp_data.get("attachment_names"):
            attachments_group = QGroupBox("Вложения")
            attachments_layout = QVBoxLayout(attachments_group)
            
            for name in self.kp_data["attachment_names"]:
                label = QLabel(f"📎 {name}")
                attachments_layout.addWidget(label)
            
            layout.addWidget(attachments_group)
        
        self._load_data()
    
    def _load_data(self):
        """Загрузка данных в интерфейс"""
        # Загрузка цен
        prices = self.kp_data.get("prices", [])
        self.table_prices.setRowCount(len(prices))
        
        for i, price_item in enumerate(prices):
            service = price_item.get("service", "")
            price = price_item.get("price", "")
            currency = price_item.get("currency", "RUB")
            
            self.table_prices.setItem(i, 0, QTableWidgetItem(service))
            self.table_prices.setItem(i, 1, QTableWidgetItem(price))
            self.table_prices.setItem(i, 2, QTableWidgetItem(currency))
            
            # Кнопка редактирования
            btn_edit = QPushButton("✏️")
            btn_edit.clicked.connect(lambda checked, row=i: self._edit_price(row))
            self.table_prices.setCellWidget(i, 3, btn_edit)
        
        # Загрузка условий
        terms = self.kp_data.get("terms", [])
        self.txt_terms.setText("\n".join(terms) if terms else "Нет условий")
        
        # Загрузка заметок
        notes = self.kp_data.get("notes", "")
        self.txt_notes.setText(notes if notes else "Нет заметок")
    
    def _edit_price(self, row: int):
        """Редактирование цены"""
        item = self.table_prices.item(row, 0)
        if not item:
            return
        
        service = item.text()
        price_item = self.table_prices.item(row, 1)
        price = price_item.text() if price_item else ""
        
        logger.info(f"Редактирование цены: {service} = {price}")
        QMessageBox.information(
            self,
            "Редактирование",
            f"Редактирование: {service}\nТекущая цена: {price}\n\n"
            "Функция редактирования будет доступна в следующей версии"
        )
    
    def get_updated_data(self) -> dict:
        """Получить обновлённые данные"""
        # Сбор данных из таблицы
        prices = []
        for row in range(self.table_prices.rowCount()):
            service_item = self.table_prices.item(row, 0)
            price_item = self.table_prices.item(row, 1)
            currency_item = self.table_notes.item(row, 2)
            
            if service_item:
                prices.append({
                    "service": service_item.text(),
                    "price": price_item.text() if price_item else "",
                    "currency": currency_item.text() if currency_item else "RUB"
                })
        
        return {
            "prices": prices,
            "terms": self.txt_terms.toPlainText().split("\n"),
            "notes": self.txt_notes.toPlainText()
        }
