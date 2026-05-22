"""
Диалог прогресса рассылки (с запуском в реальном времени)
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QProgressBar, QTextEdit,
    QPushButton, QGroupBox, QGridLayout,
    QMessageBox
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread
from loguru import logger
import asyncio

from services.mailing_service import MailingService


class MailingSendThread(QThread):
    """Поток отправки рассылки (чтобы не блокировать GUI)"""
    
    progress_updated = pyqtSignal(int, int, int)  # sent, total, errors
    recipient_sent = pyqtSignal(str, bool, str)  # email, success, message
    finished_signal = pyqtSignal(bool, str)  # success, message
    log_message = pyqtSignal(str)  # текст для лога
    
    def __init__(self, mailing_id: int, service: MailingService):
        super().__init__()
        self.mailing_id = mailing_id
        self.service = service
    
    def run(self):
        """Запуск отправки в отдельном потоке"""
        try:
            # Назначить callback'и сервиса для эмитации сигналов
            self.service.on_progress = lambda s, t, e: self.progress_updated.emit(s, t, e)
            self.service.on_recipient = lambda em, su, msg: self.recipient_sent.emit(em, su, msg)
            self.service.on_log = lambda msg: self.log_message.emit(msg)
            self.service.on_finished = lambda su, msg: self.finished_signal.emit(su, msg)
            
            # Создать новый event loop для потока
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Запустить отправку (блокирует до завершения)
            loop.run_until_complete(self.service.start_mailing(self.mailing_id))
            loop.close()
            
        except Exception as e:
            logger.error(f"Ошибка в потоке отправки: {e}")
            self.finished_signal.emit(False, str(e))
    
    def stop(self):
        """Запросить остановку"""
        self.service.cancel_mailing(self.mailing_id)


class DialogMailingProgress(QDialog):
    """Диалог прогресса рассылки"""
    
    mailing_completed = pyqtSignal(int)  # ID рассылки
    
    def __init__(self, mailing_id: int, parent=None):
        super().__init__(parent)
        self.mailing_id = mailing_id
        # Единый экземпляр сервиса — передаётся в поток
        self.service = MailingService()
        
        self.setWindowTitle(f"📧 Отправка рассылки #{mailing_id}")
        self.setMinimumSize(600, 500)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        
        self._setup_ui()
        self._load_mailing_info()
        self._start_sending()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Информация о рассылке
        info_group = QGroupBox("Информация о рассылке")
        info_layout = QGridLayout()
        
        self.lbl_name = QLabel("—")
        info_layout.addWidget(QLabel("Название:"), 0, 0)
        info_layout.addWidget(self.lbl_name, 0, 1)
        
        self.lbl_status = QLabel("—")
        info_layout.addWidget(QLabel("Статус:"), 1, 0)
        info_layout.addWidget(self.lbl_status, 1, 1)
        
        self.lbl_recipients = QLabel("—")
        info_layout.addWidget(QLabel("Получателей:"), 2, 0)
        info_layout.addWidget(self.lbl_recipients, 2, 1)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # Прогресс
        progress_group = QGroupBox("Прогресс отправки")
        progress_layout = QVBoxLayout()
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        progress_layout.addWidget(self.progress_bar)
        
        stats_layout = QHBoxLayout()
        self.lbl_sent = QLabel("Отправлено: 0")
        self.lbl_errors = QLabel("Ошибок: 0")
        self.lbl_remaining = QLabel("Осталось: 0")
        stats_layout.addWidget(self.lbl_sent)
        stats_layout.addWidget(self.lbl_errors)
        stats_layout.addWidget(self.lbl_remaining)
        stats_layout.addStretch()
        progress_layout.addLayout(stats_layout)
        
        progress_group.setLayout(progress_layout)
        layout.addWidget(progress_group)
        
        # Лог
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        # PyQt6 не имеет setMaximumBlockCount, используем альтернативу
        self.log_text.setPlaceholderText("Лог отправки...")
        layout.addWidget(self.log_text)
        
        # Кнопки
        buttons_layout = QHBoxLayout()
        
        self.btn_pause = QPushButton("⏸️ Пауза")
        self.btn_pause.clicked.connect(self._toggle_pause)
        buttons_layout.addWidget(self.btn_pause)
        
        self.btn_cancel = QPushButton("❌ Отменить")
        self.btn_cancel.clicked.connect(self._cancel)
        buttons_layout.addWidget(self.btn_cancel)
        
        buttons_layout.addStretch()
        
        self.btn_close = QPushButton("Закрыть")
        self.btn_close.clicked.connect(self.close)
        self.btn_close.setEnabled(False)
        buttons_layout.addWidget(self.btn_close)
        
        layout.addLayout(buttons_layout)
    
    def _load_mailing_info(self):
        """Загрузить информацию о рассылке"""
        info = self.service.get_mailing(self.mailing_id)
        if info:
            self.lbl_name.setText(info.get("name", "—"))
            self.lbl_status.setText(info.get("status", "—"))
            self.lbl_recipients.setText(str(info.get("total_recipients", 0)))
            
            total = info.get("total_recipients", 0)
            self.progress_bar.setRange(0, total)
    
    def _start_sending(self):
        """Запустить отправку в отдельном потоке"""
        self.log_text.append("🚀 Запуск рассылки...")
        
        self.thread = MailingSendThread(self.mailing_id, self.service)
        self.thread.progress_updated.connect(self._on_progress)
        self.thread.recipient_sent.connect(self._on_recipient)
        self.thread.finished_signal.connect(self._on_finished)
        self.thread.log_message.connect(self._on_log)
        self.thread.start()
    
    def _on_progress(self, sent: int, total: int, errors: int):
        """Обновление прогресса"""
        self.progress_bar.setValue(sent)
        if total > 0:
            self.progress_bar.setFormat(f"{sent}/{total} ({sent/total*100:.0f}%)")
        else:
            self.progress_bar.setFormat(f"{sent}/{total}")
        
        self.lbl_sent.setText(f"Отправлено: {sent}")
        self.lbl_errors.setText(f"Ошибок: {errors}")
        self.lbl_remaining.setText(f"Осталось: {total - sent}")
    
    def _on_recipient(self, email: str, success: bool, message: str):
        """Обработка отправки одному получателю"""
        icon = "✅" if success else "❌"
        self.log_text.append(f"{icon} {email}: {message}")
    
    def _on_log(self, message: str):
        """Лог-сообщение"""
        self.log_text.append(message)
    
    def _on_finished(self, success: bool, message: str):
        """Завершение отправки"""
        if success:
            self.log_text.append(f"\n✅ {message}")
            self.lbl_status.setText("Завершена")
            self.mailing_completed.emit(self.mailing_id)
        else:
            self.log_text.append(f"\n❌ Ошибка: {message}")
            self.lbl_status.setText("Ошибка")
        
        self.btn_pause.setEnabled(False)
        self.btn_cancel.setEnabled(False)
        self.btn_close.setEnabled(True)
    
    def _toggle_pause(self):
        """Пауза / возобновление"""
        if self.btn_pause.text() == "⏸️ Пауза":
            self.service.pause_mailing(self.mailing_id)
            self.btn_pause.setText("▶️ Продолжить")
            self.log_text.append("⏸️ Рассылка приостановлена")
        else:
            self.service.resume_mailing(self.mailing_id)
            self.btn_pause.setText("⏸️ Пауза")
            self.log_text.append("▶️ Рассылка возобновлена")
    
    def _cancel(self):
        """Отменить рассылку"""
        reply = QMessageBox.question(
            self,
            "Подтверждение",
            "Отменить рассылку?\n\nОтправленные письма не будут отозваны.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            if hasattr(self, 'thread') and self.thread.isRunning():
                self.thread.stop()
            self.log_text.append("❌ Рассылка отменена")
            self.btn_pause.setEnabled(False)
            self.btn_cancel.setEnabled(False)
            self.btn_close.setEnabled(True)
    
    def closeEvent(self, event):
        """Обработка закрытия окна"""
        # Если отправка ещё идёт — спросить
        if self.btn_close.isEnabled():
            event.accept()
            return
        
        reply = QMessageBox.question(
            self,
            "Подтверждение",
            "Рассылка ещё выполняется. Закрыть окно?\n\n"
            "Отправка будет отменена.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            if hasattr(self, 'thread') and self.thread.isRunning():
                self.thread.stop()
                self.thread.wait(2000)  # Подождать завершения потока (макс. 2 сек)
            event.accept()
        else:
            event.ignore()
