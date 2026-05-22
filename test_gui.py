"""
Простой тест GUI
"""
import sys
from PyQt6.QtWidgets import QApplication

print("Запуск GUI...")

app = QApplication(sys.argv)

from gui.main_window import MainWindow

window = MainWindow()
window.show()
window.raise_()

print("✅ Окно показано!")
print("Проверьте панель задач")
print("Нажмите Enter для выхода...")

input()

sys.exit(app.exec())
