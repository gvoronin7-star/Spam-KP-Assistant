"""
Диалог предпросмотра и редактирования сгенерированного через LLM письма
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QPushButton, QTabWidget, QMessageBox, QSplitter, QWidget, QProgressBar
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


class DialogLLMPreview(QDialog):
    """
    Диалог предпросмотра и редактирования сгенерированного письма
    
    Возможности:
    - Просмотр сгенерированного письма (subject, plain, html)
    - Редактирование текста
    - Перегенерация через LLM
    - Применение к шаблону
    - Копирование текста
    """
    
    def __init__(self, generated_data: dict, on_apply=None, on_regenerate=None):
        """
        Инициализация диалога
        
        Args:
            generated_data: Словарь с данными письма
                {
                    'subject': str,
                    'body_plain': str,
                    'body_html': str
                }
            on_apply: Callback при применении (function)
            on_regenerate: Callback при перегенерации (function)
        """
        super().__init__()
        
        self.generated_data = generated_data
        self.on_apply = on_apply
        self.on_regenerate = on_regenerate
        
        self.setWindowTitle("✨ Предпросмотр сгенерированного письма")
        self.setMinimumSize(900, 700)
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Настройка интерфейса"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Заголовок
        title = QLabel("📧 Сгенерировано через LLM")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        layout.addWidget(title)
        
        # Инфо
        info = QLabel("Вы можете отредактировать текст перед применением")
        info.setStyleSheet("color: gray; font-size: 11px;")
        layout.addWidget(info)
        
        # Разделитель
        layout.addSpacing(10)
        
        # Прогресс бар (скрыт по умолчанию)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Бесконечный прогресс
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("Генерация...")
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Табы для разных версий
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        # Таб: Subject
        subject_widget = self._create_subject_tab()
        self.tabs.addTab(subject_widget, "📝 Тема")
        
        # Таб: Plain text
        plain_widget = self._create_plain_tab()
        self.tabs.addTab(plain_widget, "📄 Текст (Plain)")
        
        # Таб: HTML
        html_widget = self._create_html_tab()
        self.tabs.addTab(html_widget, "🌐 HTML")
        
        # Предпросмотр
        preview_widget = self._create_preview_tab()
        self.tabs.addTab(preview_widget, "👁️ Предпросмотр")
        
        # Разделитель
        layout.addSpacing(10)
        
        # Кнопки
        btn_layout = QHBoxLayout()
        
        # Кнопка перегенерации
        self.btn_regenerate = QPushButton("✨ Перегенерировать")
        self.btn_regenerate.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.btn_regenerate.clicked.connect(self._on_regenerate)
        btn_layout.addWidget(self.btn_regenerate)
        
        btn_layout.addSpacing(20)
        
        # Кнопка копирования
        self.btn_copy = QPushButton("📋 Копировать текст")
        self.btn_copy.clicked.connect(self._on_copy)
        btn_layout.addWidget(self.btn_copy)
        
        btn_layout.addStretch()
        
        # Кнопка отмены
        self.btn_cancel = QPushButton("✖ Отмена")
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)
        
        # Кнопка применения
        self.btn_apply = QPushButton("💾 Применить")
        self.btn_apply.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        self.btn_apply.clicked.connect(self._on_apply)
        btn_layout.addWidget(self.btn_apply)
        
        layout.addLayout(btn_layout)
    
    def _create_subject_tab(self):
        """Создание таба для темы письма"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        label = QLabel("Тема письма:")
        label.setStyleSheet("font-weight: bold;")
        layout.addWidget(label)
        
        self.subject_edit = QTextEdit()
        self.subject_edit.setText(self.generated_data.get('subject', ''))
        self.subject_edit.setMaximumHeight(80)
        layout.addWidget(self.subject_edit)
        
        return widget
    
    def _create_plain_tab(self):
        """Создание таба для plain текста"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        label = QLabel("Текст письма (Plain):")
        label.setStyleSheet("font-weight: bold;")
        layout.addWidget(label)
        
        self.plain_edit = QTextEdit()
        self.plain_edit.setPlainText(self.generated_data.get('body_plain', ''))
        layout.addWidget(self.plain_edit)
        
        return widget
    
    def _create_html_tab(self):
        """Создание таба для HTML"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        label = QLabel("HTML версия:")
        label.setStyleSheet("font-weight: bold;")
        layout.addWidget(label)
        
        self.html_edit = QTextEdit()
        self.html_edit.setHtml(self.generated_data.get('body_html', ''))
        layout.addWidget(self.html_edit)
        
        return widget
    
    def _create_preview_tab(self):
        """Создание таба для предпросмотра"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        label = QLabel("Предпросмотр (как будет выглядеть письмо):")
        label.setStyleSheet("font-weight: bold;")
        layout.addWidget(label)
        
        self.preview_view = QTextEdit()
        self.preview_view.setReadOnly(True)
        self.preview_view.setHtml(self.generated_data.get('body_html', ''))
        layout.addWidget(self.preview_view)
        
        return widget
    
    def _on_regenerate(self):
        """Обработка перегенерации"""
        if self.on_regenerate:
            # Показать индикатор загрузки
            self.btn_regenerate.setEnabled(False)
            self.btn_regenerate.setText("⏳ Генерация...")
            self.progress_bar.setVisible(True)
            
            try:
                # Вызвать callback
                new_data = self.on_regenerate()
                if new_data:
                    self._update_content(new_data)
                    QMessageBox.information(
                        self,
                        "✅ Сгенерировано",
                        "Письмо успешно перегенерировано"
                    )
            finally:
                self.btn_regenerate.setEnabled(True)
                self.btn_regenerate.setText("✨ Перегенерировать")
                self.progress_bar.setVisible(False)
    
    def _on_copy(self):
        """Копирование текста"""
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtGui import QClipboard
        
        # Копируем plain текст
        clipboard = QApplication.clipboard()
        clipboard.setText(self.plain_edit.toPlainText())
        
        QMessageBox.information(
            self,
            "📋 Скопировано",
            "Текст письма скопирован в буфер обмена"
        )
    
    def _on_apply(self):
        """Применение изменений"""
        # Собираем данные
        updated_data = {
            'subject': self.subject_edit.toPlainText().strip(),
            'body_plain': self.plain_edit.toPlainText().strip(),
            'body_html': self.html_edit.toHtml()
        }
        
        # Валидация
        if not updated_data['subject']:
            QMessageBox.warning(
                self,
                "⚠️ Ошибка",
                "Пожалуйста, заполните тему письма"
            )
            return
        
        if not updated_data['body_plain']:
            QMessageBox.warning(
                self,
                "⚠️ Ошибка",
                "Пожалуйста, заполните текст письма"
            )
            return
        
        # Вызываем callback
        if self.on_apply:
            self.on_apply(updated_data)
        
        # Закрытие диалога
        self.accept()
    
    def _update_content(self, new_data: dict):
        """Обновление контента"""
        self.generated_data = new_data
        
        # Обновляем все табы
        self.subject_edit.setText(new_data.get('subject', ''))
        self.plain_edit.setPlainText(new_data.get('body_plain', ''))
        self.html_edit.setHtml(new_data.get('body_html', ''))
        self.preview_view.setHtml(new_data.get('body_html', ''))
    
    def get_data(self) -> dict:
        """
        Получить актуальные данные
        
        Returns:
            Словарь с данными письма
        """
        return {
            'subject': self.subject_edit.toPlainText().strip(),
            'body_plain': self.plain_edit.toPlainText().strip(),
            'body_html': self.html_edit.toHtml()
        }