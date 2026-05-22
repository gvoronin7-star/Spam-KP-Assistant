"""
Диалог управления LLM-агентом

Позволяет:
- Изменить режим работы агента
- Просмотреть статус
- Увидеть последние черновики
- Просмотреть статистику
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QGroupBox, QFormLayout, QComboBox, QTextEdit, QTableWidget,
    QTableWidgetItem, QHeaderView, QMessageBox, QProgressBar,
    QScrollArea, QWidget, QFrame, QRadioButton, QButtonGroup
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor
from loguru import logger

from services.llm_agent_service import LLMAgentService
from services.inbox_service import InboxService
from core.database import SessionLocal
from core.models import Message, Task, Dialogue


class DialogLLMAgent(QDialog):
    """Диалог управления LLM-агентом"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("LLM Агент — Управление")
        self.setMinimumSize(900, 700)
        
        self.agent = None
        self._init_agent()
        
        self._init_ui()
        self._load_status()
        self._load_drafts()
        self._load_statistics()
    
    def _init_agent(self):
        """Инициализация агента"""
        try:
            inbox = InboxService()
            self.agent = inbox.llm_agent
            if not self.agent:
                logger.warning("LLM Agent не инициализирован")
        except Exception as e:
            logger.error(f"Ошибка инициализации LLM Agent: {e}")
    
    def _init_ui(self):
        """Создание интерфейса"""
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        self.setLayout(layout)
        
        # === Заголовок ===
        title = QLabel("🤖 LLM Агент — Автоматические ответы")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        layout.addWidget(title)
        
        # === Статус агента ===
        status_group = QGroupBox("Статус агента")
        status_layout = QFormLayout()
        status_group.setLayout(status_layout)
        
        self.lbl_mode = QLabel()
        self.lbl_mode.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        status_layout.addRow("Режим работы:", self.lbl_mode)
        
        self.lbl_llm_config = QLabel()
        status_layout.addRow("LLM настроен:", self.lbl_llm_config)
        
        self.lbl_model = QLabel()
        status_layout.addRow("Модель:", self.lbl_model)
        
        self.lbl_categories = QLabel()
        status_layout.addRow("Категории:", self.lbl_categories)
        
        layout.addWidget(status_group)
        
        # === Выбор режима ===
        mode_group = QGroupBox("Режим работы")
        mode_layout = QVBoxLayout()
        mode_group.setLayout(mode_layout)
        
        self.mode_group_btn = QButtonGroup(self)
        mode_descriptions = {
            "disabled": "🔴 Выключен — агент не обрабатывает письма",
            "draft_only": "🟡 Только черновики — генерирует ответы, но не отправляет",
            "confirm": "🟠 С подтверждением — создаёт задачи на проверку перед отправкой",
            "auto": "🟢 Авто — автоматически отправляет ответы (требует внимания!)"
        }
        
        for mode, desc in mode_descriptions.items():
            radio = QRadioButton(desc)
            radio.setProperty("mode", mode)
            radio.toggled.connect(self._on_mode_toggled)
            self.mode_group_btn.addButton(radio)
            mode_layout.addWidget(radio)
        
        layout.addWidget(mode_group)
        
        # === Последние черновики ===
        drafts_group = QGroupBox("Последние черновики ответов")
        drafts_layout = QVBoxLayout()
        drafts_group.setLayout(drafts_layout)
        
        self.table_drafts = QTableWidget()
        self.table_drafts.setColumnCount(5)
        self.table_drafts.setHorizontalHeaderLabels([
            "Дата", "Диалог", "Тема", "Категория", "Статус"
        ])
        self.table_drafts.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_drafts.setAlternatingRowColors(True)
        self.table_drafts.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table_drafts.itemDoubleClicked.connect(self._on_draft_double_clicked)
        drafts_layout.addWidget(self.table_drafts)
        
        # Кнопки действий с черновиками
        btn_layout = QHBoxLayout()
        
        self.btn_view_draft = QPushButton("👁️ Просмотреть")
        self.btn_view_draft.clicked.connect(self._view_selected_draft)
        btn_layout.addWidget(self.btn_view_draft)
        
        self.btn_send_draft = QPushButton("✉️ Отправить")
        self.btn_send_draft.clicked.connect(self._send_selected_draft)
        btn_layout.addWidget(self.btn_send_draft)
        
        self.btn_delete_draft = QPushButton("🗑️ Удалить")
        self.btn_delete_draft.clicked.connect(self._delete_selected_draft)
        btn_layout.addWidget(self.btn_delete_draft)
        
        btn_layout.addStretch()
        drafts_layout.addLayout(btn_layout)
        
        layout.addWidget(drafts_group)
        
        # === Статистика ===
        stats_group = QGroupBox("Статистика за сегодня")
        stats_layout = QHBoxLayout()
        stats_group.setLayout(stats_layout)
        
        self.stat_processed = QLabel("0")
        self.stat_processed.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.stat_processed.setStyleSheet("font-size: 24px; font-weight: bold; color: #2196F3;")
        
        self.stat_drafts = QLabel("0")
        self.stat_drafts.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.stat_drafts.setStyleSheet("font-size: 24px; font-weight: bold; color: #FF9800;")
        
        self.stat_sent = QLabel("0")
        self.stat_sent.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.stat_sent.setStyleSheet("font-size: 24px; font-weight: bold; color: #4CAF50;")
        
        self.stat_errors = QLabel("0")
        self.stat_errors.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.stat_errors.setStyleSheet("font-size: 24px; font-weight: bold; color: #F44336;")
        
        for label, text in [
            (self.stat_processed, "Обработано"),
            (self.stat_drafts, "Черновиков"),
            (self.stat_sent, "Отправлено"),
            (self.stat_errors, "Ошибок")
        ]:
            wrapper = QVBoxLayout()
            wrapper.addWidget(label)
            wrapper.addWidget(QLabel(text))
            wrapper.setAlignment(Qt.AlignmentFlag.AlignCenter)
            stats_layout.addLayout(wrapper)
        
        layout.addWidget(stats_group)
        
        # === Кнопки управления ===
        btn_control_layout = QHBoxLayout()
        
        self.btn_refresh = QPushButton("🔄 Обновить")
        self.btn_refresh.clicked.connect(self._refresh_all)
        btn_control_layout.addWidget(self.btn_refresh)
        
        btn_control_layout.addStretch()
        
        self.btn_close = QPushButton("Закрыть")
        self.btn_close.clicked.connect(self.accept)
        btn_control_layout.addWidget(self.btn_close)
        
        layout.addLayout(btn_control_layout)
    
    def _on_mode_toggled(self, checked):
        """Изменение режима работы"""
        if not checked:
            return
        
        radio = self.sender()
        mode = radio.property("mode")
        
        if self.agent:
            try:
                self.agent.set_mode(mode)
                logger.info(f"Режим LLM Agent изменён на: {mode}")
                self._load_status()
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось изменить режим:\n{e}")
    
    def _load_status(self):
        """Загрузка статуса агента"""
        if not self.agent:
            self.lbl_mode.setText("Не инициализирован")
            self.lbl_mode.setStyleSheet("color: red;")
            self.lbl_llm_config.setText("Нет")
            self.lbl_model.setText("—")
            self.lbl_categories.setText("—")
            return
        
        status = self.agent.get_status()
        
        mode_colors = {
            "disabled": "color: red;",
            "draft_only": "color: orange;",
            "confirm": "color: #FF9800;",
            "auto": "color: green;"
        }
        
        self.lbl_mode.setText(status["mode"].upper())
        self.lbl_mode.setStyleSheet(mode_colors.get(status["mode"], ""))
        
        self.lbl_llm_config.setText("✅ Да" if status["llm_configured"] else "❌ Нет")
        self.lbl_llm_config.setStyleSheet("color: green;" if status["llm_configured"] else "color: red;")
        
        self.lbl_model.setText(status.get("primary_model", "—"))
        self.lbl_categories.setText(", ".join(status.get("supported_categories", [])))
        
        # Выбрать правильный радио-баттон
        for btn in self.mode_group_btn.buttons():
            if btn.property("mode") == status["mode"]:
                btn.setChecked(True)
                break
    
    def _load_drafts(self):
        """Загрузка последних черновиков"""
        self.table_drafts.setRowCount(0)
        
        db = SessionLocal()
        try:
            drafts = db.query(Message).filter_by(
                direction="outbound",
                status="draft",
                generated_by_llm=True
            ).order_by(Message.created_at.desc()).limit(20).all()
            
            for draft in drafts:
                row = self.table_drafts.rowCount()
                self.table_drafts.insertRow(row)
                
                # Дата
                date_str = draft.created_at.strftime("%d.%m %H:%M") if draft.created_at else ""
                self.table_drafts.setItem(row, 0, QTableWidgetItem(date_str))
                
                # Диалог
                dialogue = db.query(Dialogue).filter_by(id=draft.dialogue_id).first()
                contact_email = dialogue.contact.email if dialogue and dialogue.contact else ""
                self.table_drafts.setItem(row, 1, QTableWidgetItem(contact_email[:30]))
                
                # Тема
                self.table_drafts.setItem(row, 2, QTableWidgetItem(draft.subject[:40] if draft.subject else ""))
                
                # Категория (извлекаем из описания задачи)
                category = self._guess_category(draft)
                self.table_drafts.setItem(row, 3, QTableWidgetItem(category))
                
                # Статус
                self.table_drafts.setItem(row, 4, QTableWidgetItem("Черновик"))
            
            logger.info(f"Загружено {len(drafts)} черновиков")
        finally:
            db.close()
    
    def _guess_category(self, message: Message) -> str:
        """Угадать категорию по теме/тексту"""
        subject = (message.subject or "").lower()
        body = (message.body_plain or "").lower()
        
        if any(word in subject or word in body for word in ["вопрос", "уточните", "какие"]):
            return "question"
        elif any(word in subject or word in body for word in ["спасибо", "благодарим"]):
            return "auto_reply"
        elif any(word in subject or word in body for word in ["кп", "предложение"]):
            return "kp"
        else:
            return "unknown"
    
    def _load_statistics(self):
        """Загрузка статистики"""
        # Пока заглушка — в будущем можно собирать реальную статистику
        self.stat_processed.setText("0")
        self.stat_drafts.setText("0")
        self.stat_sent.setText("0")
        self.stat_errors.setText("0")
    
    def _refresh_all(self):
        """Обновить все данные"""
        self._load_status()
        self._load_drafts()
        self._load_statistics()
    
    def _on_draft_double_clicked(self, item):
        """Двойной клик по черновику — просмотр"""
        self._view_selected_draft()
    
    def _view_selected_draft(self):
        """Просмотр выбранного черновика"""
        row = self.table_drafts.currentRow()
        if row < 0:
            QMessageBox.information(self, "Информация", "Выберите черновик")
            return
        
        # Получить ID черновика (можно добавить скрытую колонку)
        # Пока просто сообщение
        QMessageBox.information(self, "Просмотр", "Функция просмотра в разработке")
    
    def _send_selected_draft(self):
        """Отправить выбранный черновик"""
        row = self.table_drafts.currentRow()
        if row < 0:
            QMessageBox.information(self, "Информация", "Выберите черновик")
            return
        
        reply = QMessageBox.question(
            self, "Подтверждение",
            "Отправить выбранный черновик?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            QMessageBox.information(self, "Информация", "Функция отправки в разработке")
    
    def _delete_selected_draft(self):
        """Удалить выбранный черновик"""
        row = self.table_drafts.currentRow()
        if row < 0:
            QMessageBox.information(self, "Информация", "Выберите черновик")
            return
        
        reply = QMessageBox.question(
            self, "Подтверждение",
            "Удалить выбранный черновик?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            QMessageBox.information(self, "Информация", "Функция удаления в разработке")
