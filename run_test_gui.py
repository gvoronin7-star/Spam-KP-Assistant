"""
Упрощённый запуск Spam KP Assistant для теста
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path('.').resolve()))

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QLabel, QPushButton, 
    QVBoxLayout, QWidget, QTabWidget, QMessageBox
)
from PyQt6.QtCore import Qt

class SimpleMainWindow(QMainWindow):
    """Упрощённое главное окно для теста"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Spam KP Assistant v1.1 - ТЕСТ")
        self.setGeometry(100, 100, 800, 600)
        
        # Центральное окно
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        
        # Заголовок
        title = QLabel("🎉 Spam KP Assistant работает!")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #2196F3;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Вкладки
        tabs = QTabWidget()
        tabs.addTab(QLabel("📋 Профили"), "Профили")
        tabs.addTab(QLabel("👥 Контакты"), "Контакты")
        tabs.addTab(QLabel("📝 Шаблоны"), "Шаблоны")
        tabs.addTab(QLabel("💬 Переписка"), "Переписка")
        tabs.addTab(QLabel("✅ Задачи"), "Задачи")
        tabs.addTab(QLabel("⚙️ Настройки"), "Настройки")
        layout.addWidget(tabs)
        
        # Кнопки
        btn = QPushButton("Закрыть")
        btn.clicked.connect(self.close)
        layout.addWidget(btn)
        
        # Статус
        self.statusBar().showMessage("Готов к работе | Phase 3: Напоминания реализованы")
        
        print("✅ Окно создано и показано!")

if __name__ == "__main__":
    print("🚀 Запуск Spam KP Assistant (упрощённая версия)...")
    print()
    
    app = QApplication(sys.argv)
    app.setApplicationName("Spam KP Assistant")
    
    window = SimpleMainWindow()
    window.show()
    window.raise_()
    window.activateWindow()
    
    print("📱 Окно должно быть видно на экране!")
    print("   Если не видно - проверьте Alt+Tab")
    print()
    
    result = app.exec()
    print(f"✅ Завершено с кодом: {result}")
