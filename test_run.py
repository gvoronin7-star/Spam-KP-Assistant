ьь"""
Максимально простой запуск
"""
import sys
print("Starting...")

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
app = QApplication(sys.argv)

from gui.main_window import MainWindow
window = MainWindow()
window.show()

print("Window shown! Event loop starting...")
print("Window will stay open for 60 seconds...")

# Таймер для выхода через 60 секунд
def exit_app():
    print("Exiting after 60 seconds...")
    sys.exit(0)

QTimer.singleShot(60000, exit_app)  # 60000 мс = 60 секунд

sys.exit(app.exec())
