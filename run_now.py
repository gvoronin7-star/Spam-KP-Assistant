"""
Минимальный запуск GUI
"""
import sys
import time
print("=== START ===")
sys.stdout.flush()

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
print("1. QApplication imported")
sys.stdout.flush()

app = QApplication(sys.argv)
print("2. QApplication created")
sys.stdout.flush()

# Проверка важных файлов
print("3. Checking protected files...")
sys.stdout.flush()

from utils.file_protection import check_guide_file
guide_ok = check_guide_file()
if not guide_ok:
    print("   [WARNING] Guide file could not be restored")
else:
    print("   [OK] Guide file OK")
sys.stdout.flush()

from gui.main_window import MainWindow
print("4. MainWindow imported")
sys.stdout.flush()

window = MainWindow()
print("5. MainWindow created")
sys.stdout.flush()

window.show()
print("6. Window shown")
sys.stdout.flush()

print(f"7. Window title: {window.windowTitle()}")
print(f"8. Window visible: {window.isVisible()}")
sys.stdout.flush()

print("9. Starting app.exec()...")
print("   Window will stay open until you close it")
sys.stdout.flush()

# Запуск цикла событий - без авто-выхода!
result = app.exec()
print(f"10. app.exec() returned: {result}")
sys.exit(result)
