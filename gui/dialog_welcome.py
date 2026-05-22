"""
Приветственное окно с примерами использования
"""
import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTextBrowser, QGroupBox, QTabWidget, QMessageBox, QWidget
)
from PyQt6.QtCore import Qt


class DialogWelcome(QDialog):
    """Приветственное окно"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("💡 Помощь и примеры")
        self.setMinimumSize(900, 650)
        
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout()
        
        # Заголовок
        title = QLabel("💡 Демо-интерфейс и примеры")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: blue;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Информация о том, что это демо
        demo_banner = QLabel(
            "🎯 ПРИВЕТСТВЕННОЕ ОКНО (показывается только при первом запуске)\n\n"
            "В приложении загружены демо-данные для примера:\n"
            "• 3 профиля закупок\n• 5 контактов поставщиков\n• 3 шаблона писем"
        )
        demo_banner.setStyleSheet(
            "background-color: #fff3cd; border: 2px solid #ffc107; "
            "padding: 10px; font-weight: bold;"
        )
        demo_banner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        demo_banner.setWordWrap(True)
        layout.addWidget(demo_banner)
        
        # Вкладки с примерами
        tabs = QTabWidget()
        
        # Вкладка 1: Профили
        profiles_tab = self._create_profiles_tab()
        tabs.addTab(profiles_tab, "📋 Профили")
        
        # Вкладка 2: Контакты
        contacts_tab = self._create_contacts_tab()
        tabs.addTab(contacts_tab, "👥 Контакты")
        
        # Вкладка 3: Шаблоны
        templates_tab = self._create_templates_tab()
        tabs.addTab(templates_tab, "📝 Шаблоны")
        
        # Вкладка 4: SMTP
        smtp_tab = self._create_smtp_tab()
        tabs.addTab(smtp_tab, "⚙️ SMTP/IMAP")
        
        layout.addWidget(tabs)
        
        # Кнопки
        btn_layout = QHBoxLayout()
        
        btn_close = QPushButton("✖ Закрыть")
        btn_close.clicked.connect(self.close)
        btn_close.setMinimumWidth(100)
        btn_layout.addWidget(btn_close)
        
        btn_guide = QPushButton("📖 Открыть руководство")
        btn_guide.clicked.connect(self._open_guide)
        btn_guide.setMinimumWidth(150)
        btn_layout.addWidget(btn_guide)
        
        btn_layout.addStretch()
        
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
    
    def _create_profiles_tab(self):
        """Вкладка Профили"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        browser = QTextBrowser()
        browser.setHtml("""
        <h2>📋 Профили закупок</h2>
        
        <h3>Что это?</h3>
        <p>Профиль описывает, какое именно телеком-услуги вы запрашиваете.</p>
        
        <h3>Примеры из демо-данных:</h3>
        <ul>
            <li><b>Интернет-канал 100 Мбит/с</b> - запрос подключения интернета</li>
            <li><b>Виртуальная АТС на 50 номеров</b> - запрос телефонии</li>
            <li><b>Выделенная линия 1 Гбит/с</b> - запрос арендной линии</li>
        </ul>
        
        <h3>Как использовать:</h3>
        <ol>
            <li>Нажмите <b>➕ Создать профиль</b></li>
            <li>Заполните 5 страниц мастера</li>
            <li>Нажмите <b>✓ Готово</b></li>
        </ol>
        """)
        browser.setMinimumHeight(400)
        layout.addWidget(browser)
        
        return widget
    
    def _create_contacts_tab(self):
        """Вкладка Контакты"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        browser = QTextBrowser()
        browser.setHtml("""
        <h2>👥 Контакты поставщиков</h2>
        
        <h3>Что это?</h3>
        <p>Список email-адресов поставщиков телеком-услуг.</p>
        
        <h3>Примеры из демо-данных:</h3>
        <ul>
            <li>sales@telecom.ru - ООО Телеком</li>
            <li>info@netgroup.ru - АО НетГрупп</li>
            <li>kp@biznet.ru - БИЗНЕТ Связь</li>
        </ul>
        
        <h3>Как использовать:</h3>
        <ol>
            <li>Подготовьте CSV файл</li>
            <li>Нажмите <b>📥 Импорт</b></li>
            <li>Настройте колонки</li>
        </ol>
        """)
        browser.setMinimumHeight(400)
        layout.addWidget(browser)
        
        return widget
    
    def _create_templates_tab(self):
        """Вкладка Шаблоны"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        browser = QTextBrowser()
        browser.setHtml("""
        <h2>📝 Шаблоны писем</h2>
        
        <h3>Что это?</h3>
        <p>Готовые шаблоны писем для запроса КП с переменными.</p>
        
        <h3>Переменные:</h3>
        <ul>
            <li>{{ company }} - Название компании</li>
            <li>{{ service_name }} - Название услуги</li>
            <li>{{ contact_person }} - Контактное лицо</li>
        </ul>
        
        <h3>Как использовать:</h3>
        <ol>
            <li>Нажмите <b>➕ Создать</b></li>
            <li>Заполните шаблон</li>
            <li>Нажмите <b>💾 Сохранить</b></li>
        </ol>
        """)
        browser.setMinimumHeight(400)
        layout.addWidget(browser)
        
        return widget
    
    def _create_smtp_tab(self):
        """Вкладка SMTP"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        browser = QTextBrowser()
        browser.setHtml("""
        <h2>⚙️ Настройка SMTP/IMAP</h2>
        
        <h3>Примеры настроек:</h3>
        
        <h4>Gmail:</h4>
        <pre>SMTP: smtp.gmail.com:465
IMAP: imap.gmail.com:993
Пароль: App Password</pre>
        
        <h4>Yandex:</h4>
        <pre>SMTP: smtp.yandex.ru:465
IMAP: imap.yandex.ru:993
Пароль: App Password</pre>
        """)
        browser.setMinimumHeight(400)
        layout.addWidget(browser)
        
        return widget
    
    def _open_guide(self):
        """Открыть руководство"""
        import os
        
        # Прямой путь вместо импорта
        guide_path = os.path.join(os.path.dirname(__file__), "..", "docs", "USER_GUIDE.md")
        guide_path = os.path.abspath(guide_path)
        
        if not os.path.exists(guide_path):
            QMessageBox.warning(self, "Файл не найден", f"Руководство не найдено:\n{guide_path}\n\nПопробуйте перезапустить приложение.")
            return

        try:
            with open(guide_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            guide_window = GuideViewer(content, guide_path)
            guide_window.exec()
        except Exception as e:
            try:
                os.startfile(guide_path)
                QMessageBox.information(self, "Открыто", f"Руководство открыто:\n{guide_path}")
            except Exception as e2:
                QMessageBox.information(self, "Путь", f"Откройте вручную:\n{guide_path}\n\nОшибка: {e2}")


class GuideViewer(QDialog):
    """Окно для просмотра руководства"""
    
    def __init__(self, content, path):
        super().__init__()
        self.guide_path = path
        self.setWindowTitle(f"📖 Руководство - {os.path.basename(path)}")
        self.setMinimumSize(1000, 700)
        
        layout = QVBoxLayout()
        
        info = QLabel(f"Файл: {path}")
        info.setStyleSheet("font-size: 11px; color: gray;")
        layout.addWidget(info)
        
        browser = QTextBrowser()
        browser.setPlainText(content)
        layout.addWidget(browser)
        
        btn_layout = QHBoxLayout()
        
        btn_open = QPushButton("🖥️ Открыть в редакторе")
        btn_open.clicked.connect(self._open_external)
        btn_layout.addWidget(btn_open)
        
        btn_copy = QPushButton("📋 Копировать путь")
        btn_copy.clicked.connect(self._copy_path)
        btn_layout.addWidget(btn_copy)
        
        btn_layout.addStretch()
        
        btn_close = QPushButton("✖ Закрыть")
        btn_close.clicked.connect(self.close)
        btn_layout.addWidget(btn_close)
        
        layout.addLayout(btn_layout)
        self.setLayout(layout)
    
    def _open_external(self):
        try:
            os.startfile(self.guide_path)
        except:
            QMessageBox.warning(self, "Ошибка", "Не удалось открыть файл")
    
    def _copy_path(self):
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtGui import QClipboard
        clipboard = QApplication.clipboard()
        clipboard.setText(self.guide_path)
        QMessageBox.information(self, "Скопировано", f"Путь:\n{self.guide_path}")
