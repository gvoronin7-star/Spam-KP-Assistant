"""
Диалог просмотра переписки
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QListWidget, QListWidgetItem, QPushButton, QSplitter,
    QWidget, QFrame
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


class DialogMessageViewer(QDialog):
    """Диалог просмотра сообщений диалога"""
    
    def __init__(self, dialogue, parent=None):
        super().__init__(parent)
        self.dialogue = dialogue
        self.messages = dialogue.messages
        
        self.setWindowTitle(f"Переписка: {dialogue.contact.company_name or dialogue.contact.email}")
        self.setMinimumSize(1200, 800)  # Ещё больше
        self.resize(1200, 800)
        
        # Центрирование относительно родителя
        if parent:
            parent_rect = parent.geometry()
            x = parent_rect.x() + (parent_rect.width() - 1100) // 2
            y = parent_rect.y() + (parent_rect.height() - 700) // 2
            self.move(x, y)
        
        self._setup_ui()
        self._load_messages()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Заголовок (компактный)
        header_text = (
            f"<b>{self.dialogue.profile.name if self.dialogue.profile else '—'}</b>  |  "
            f"<b>Статус:</b> {self._status_text(self.dialogue.status)}  |  "
            f"<b>Сообщений:</b> {len(self.messages)}"
        )
        header = QLabel(header_text)
        header.setStyleSheet("padding: 5px 10px; background: #f0f0f0; border-radius: 3px; font-size: 11px;")
        header.setMaximumHeight(30)
        layout.addWidget(header)
        
        # Разделитель
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Левая панель — список сообщений (узкая)
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        left_layout.addWidget(QLabel("<b>Сообщения:</b>"))
        
        self.messages_list = QListWidget()
        self.messages_list.setMaximumWidth(300)  # Уже
        self.messages_list.setMinimumWidth(280)
        self.messages_list.currentRowChanged.connect(self._show_message)
        left_layout.addWidget(self.messages_list)
        
        splitter.addWidget(left_widget)
        
        # Правая панель — содержимое сообщения (широкая)
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        # Инфо о сообщении (компактное)
        self.msg_info = QLabel("Выберите сообщение")
        self.msg_info.setStyleSheet("padding: 5px 10px; background: #e3f2fd; border-bottom: 1px solid #90caf9; font-size: 10px;")
        self.msg_info.setMaximumHeight(50)
        self.msg_info.setWordWrap(True)
        right_layout.addWidget(self.msg_info)
        
        # Тело сообщения (большое)
        self.msg_body = QTextEdit()
        self.msg_body.setReadOnly(True)
        self.msg_body.setFont(QFont("Consolas", 12))  # Ещё крупнее
        self.msg_body.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        right_layout.addWidget(self.msg_body)
        
        splitter.addWidget(right_widget)
        splitter.setSizes([300, 900])  # Больше места для текста
        
        layout.addWidget(splitter)
        
        # Кнопки
        btn_close = QPushButton("Закрыть")
        btn_close.clicked.connect(self.close)
        layout.addWidget(btn_close)
    
    def _load_messages(self):
        """Загрузить сообщения в список"""
        self.messages_list.clear()
        
        # Сортируем по дате создания
        sorted_messages = sorted(self.messages, key=lambda m: m.created_at)
        
        for msg in sorted_messages:
            direction_icon = "📤" if msg.direction == "outbound" else "📥"
            direction_text = "Исходящее" if msg.direction == "outbound" else "Входящее"
            
            # Дата
            date_str = ""
            if msg.created_at:
                date_str = msg.created_at.strftime("%d.%m.%Y %H:%M")
            
            # Тема
            subject = msg.subject or "(без темы)"
            
            item_text = f"{direction_icon} {direction_text}\n   {subject[:40]}\n   {date_str}"
            
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, msg.id)
            
            # Цвет фона
            if msg.direction == "outbound":
                item.setBackground(Qt.GlobalColor.lightGray)
            else:
                item.setBackground(Qt.GlobalColor.white)
            
            self.messages_list.addItem(item)
    
    def _show_message(self, row):
        """Показать выбранное сообщение"""
        if row < 0 or row >= len(self.messages):
            return
        
        msg = sorted(self.messages, key=lambda m: m.created_at)[row]
        
        # Инфо
        direction = "Исходящее" if msg.direction == "outbound" else "Входящее"
        from_addr = msg.from_address or "—"
        to_addr = msg.to_address or "—"
        date_str = ""
        if msg.created_at:
            date_str = msg.created_at.strftime("%d.%m.%Y %H:%M:%S")
        
        info_html = f"""
        <b>{direction}</b> | <b>Тема:</b> {msg.subject or '(без темы)'}<br>
        <b>От:</b> {from_addr} | <b>Кому:</b> {to_addr}<br>
        <b>Дата:</b> {date_str}
        """
        self.msg_info.setText(info_html)
        
        # Тело
        if msg.body_html:
            self.msg_body.setHtml(msg.body_html)
        elif msg.body_plain:
            self.msg_body.setPlainText(msg.body_plain)
        elif msg.raw_body:
            self.msg_body.setPlainText(msg.raw_body)
        else:
            self.msg_body.setPlainText("(пустое сообщение)")
    
    def _status_text(self, status: str) -> str:
        """Перевести статус на русский"""
        mapping = {
            "sent": "Отправлено",
            "clarifying": "Уточнение",
            "kp_received": "КП получено",
            "rejected": "Отказ",
            "reminder_sent": "Напоминание отправлено",
            "auto_replied": "Автоответ",
            "spam": "Спам"
        }
        return mapping.get(status, status)
