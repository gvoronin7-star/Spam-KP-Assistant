"""
Простой запуск GUI с диагностикой
"""
import sys
import traceback
from pathlib import Path

# Добавление корня проекта
sys.path.insert(0, str(Path(__file__).parent))

print("\n" + "="*60)
print("  Spam KP Assistant - Диагностика")
print("="*60 + "\n")

# Шаг 1: PyQt6
print("[1/7] Импортируем PyQt6...")
try:
    from PyQt6.QtWidgets import QApplication
    print("      OK")
except Exception as e:
    print(f"      ERROR: {e}")
    sys.exit(1)

# Шаг 2: QApplication
print("[2/7] Создаём QApplication...")
try:
    app = QApplication(sys.argv)
    app.setApplicationName("Spam KP Assistant")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("NLP-Core-Team")
    print("      OK")
except Exception as e:
    print(f"      ERROR: {e}")
    sys.exit(1)

# Шаг 3: MainWindow
print("[3/7] Импортируем MainWindow...")
try:
    from gui.main_window import MainWindow
    print("      OK")
except Exception as e:
    print(f"      ERROR: {e}")
    traceback.print_exc()
    sys.exit(1)

# Шаг 4: Создание окна
print("[4/7] Создаём окно MainWindow...")
try:
    window = MainWindow()
    print("      OK")
except Exception as e:
    print(f"      ERROR: {e}")
    traceback.print_exc()
    sys.exit(1)

# Шаг 5: Показ окна
print("[5/7] Показываем окно...")
try:
    window.show()
    print("      OK")
except Exception as e:
    print(f"      ERROR: {e}")
    sys.exit(1)

# Шаг 6: Поднять окно
print("[6/7] Поднимаем окно на передний план...")
try:
    window.raise_()
    window.activateWindow()
    print("      OK")
except Exception as e:
    print(f"      ERROR: {e}")
    sys.exit(1)

# Шаг 7: Информация
print("[7/7] Информация об окне...")
print(f"      Заголовок: {window.windowTitle()}")
print(f"      Размер: {window.width()}x{window.height()}")
print(f"      Позиция: ({window.x()}, {window.y()})")
print(f"      Видимость: {'visible' if window.isVisible() else 'hidden'}")

print("\n" + "="*60)
print("  WINDOW CREATED AND SHOWN SUCCESSFULLY!")
print("="*60)
print("\nIf window is not visible:")
print("  1. Press Win+Tab - look for 'Spam KP Assistant'")
print("  2. Press Alt+Tab - switch to the window")
print("  3. Check taskbar at bottom of screen")
print("\nStarting event loop...")
print("-"*60 + "\n")

# Запуск цикла событий - ГЛАВНОЕ!
sys.exit(app.exec())
