"""
Запуск демо-версии с приветствием
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QSettings

print("="*60)
print("  Spam KP Assistant - Демо-версия")
print("="*60)
print()

# Создаём приложение
app = QApplication(sys.argv)
app.setApplicationName("Spam KP Assistant Demo")
app.setApplicationVersion("1.0.0")
app.setOrganizationName("NLP-Core-Team")

# Сброс настройки приветствия
settings = QSettings("NLP-Core-Team", "SpamKPAssistant")
settings.setValue("welcome_seen", False)
print("[1/3] Приветствие сброшено")

# Импортируем и создаём окно
from gui.main_window import MainWindow
window = MainWindow()
print("[2/3] Главное окно создано")

# Показываем приветствие
from gui.dialog_welcome import DialogWelcome
dialog = DialogWelcome(window)
dialog.show()
dialog.raise_()
dialog.activateWindow()
print("[3/3] Приветствие показано!")

# Показываем главное окно
window.show()
window.raise_()
window.activateWindow()

print()
print("="*60)
print("  ОКНА ПОКАЗАНЫ!")
print("="*60)
print()
print("Проверьте:")
print("  1. Панель задач (Win+Tab)")
print("  2. Alt+Tab")
print("  3. Другие мониторы")
print()
print("Должно быть 2 окна:")
print("  - Приветствие (справа)")
print("  - Главное окно (слева)")
print()

# Запуск цикла событий
sys.exit(app.exec())
