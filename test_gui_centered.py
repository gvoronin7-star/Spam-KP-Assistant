    """
Тест GUI с центрированием окна
"""
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QScreen

print("=" * 60)
print("  Spam KP Assistant - Запуск с центрированием")
print("=" * 60)

app = QApplication(sys.argv)

from gui.main_window import MainWindow

window = MainWindow()

# Центрируем окно на экране
screen = QScreen.availableGeometry(app.primaryScreen())
center_point = screen.center()
window_rect = window.frameGeometry()

window_rect.moveCenter(center_point)
window.move(window_rect.topLeft())

window.show()
window.raise_()
window.activateWindow()

print("\n✅ Окно показано и отцентрировано!")
print(f"   Размер: {window.width()}x{window.height()}")
print(f"   Позиция: по центру экрана")
print("\nЕсли окно не видно, проверьте:")
print("  - Панель задач (Win+Tab)")
print("  - Alt+Tab")
print("  - Другие мониторы")
print("\nНажмите Enter для выхода...")

input()

sys.exit(app.exec())
