"""
Диагностика GUI - детальная информация
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

print("\n" + "="*70)
print("  Spam KP Assistant - GUI Диагностика")
print("="*70 + "\n")

# 1. Проверка PyQt6
print("[1/10] Проверка PyQt6...")
try:
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QScreen
    print("      PyQt6 импортирован OK")
except Exception as e:
    print(f"      ERROR: {e}")
    sys.exit(1)

# 2. Создание QApplication
print("[2/10] Создание QApplication...")
try:
    app = QApplication(sys.argv)
    print("      QApplication создан OK")
except Exception as e:
    print(f"      ERROR: {e}")
    sys.exit(1)

# 3. Информация о экранах
print("[3/10] Информация об экранах...")
screens = app.screens()
print(f"      Количество экранов: {len(screens)}")
for i, screen in enumerate(screens):
    geom = screen.geometry()
    avail = screen.availableGeometry()
    print(f"      Экран {i}:")
    print(f"        Name: {screen.name()}")
    print(f"        Geometry: x={geom.x()}, y={geom.y()}, w={geom.width()}, h={geom.height()}")
    print(f"        Available: x={avail.x()}, y={avail.y()}, w={avail.width()}, h={avail.height()}")
    print(f"        Primary: {screen == app.primaryScreen()}")

# 4. Импорт MainWindow
print("[4/10] Импорт MainWindow...")
try:
    from gui.main_window import MainWindow
    print("      MainWindow импортирован OK")
except Exception as e:
    print(f"      ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 5. Создание окна
print("[5/10] Создание MainWindow...")
try:
    window = MainWindow()
    print("      MainWindow создан OK")
except Exception as e:
    print(f"      ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 6. Информация об окне
print("[6/10] Информация об окне...")
print(f"      Title: {window.windowTitle()}")
print(f"      Size: {window.size().width()}x{window.size().height()}")
print(f"      Minimum Size: {window.minimumSize().width()}x{window.minimumSize().height()}")
print(f"      Frame Geometry: x={window.frameGeometry().x()}, y={window.frameGeometry().y()}")
print(f"      Frame Size: {window.frameGeometry().width()}x{window.frameGeometry().height()}")
print(f"      Geometry: x={window.geometry().x()}, y={window.geometry().y()}, w={window.geometry().width()}, h={window.geometry().height()}")

# 7. Позиционирование окна
print("[7/10] Центрирование окна...")
screen = app.primaryScreen()
screen_geom = screen.availableGeometry()
window_geom = window.frameGeometry()

center_point = screen_geom.center()
window_geom.moveCenter(center_point)
top_left = window_geom.topLeft()

print(f"      Screen center: x={center_point.x()}, y={center_point.y()}")
print(f"      New window position: x={top_left.x()}, y={top_left.y()}")

window.move(top_left)
print("      Окно перемещено в центр экрана")

# 8. Показ окна
print("[8/10] Показ окна...")
try:
    window.show()
    print("      show() вызван OK")
except Exception as e:
    print(f"      ERROR: {e}")

# 9. Поднятие окна
print("[9/10] Поднятие окна на передний план...")
try:
    window.raise_()
    window.activateWindow()
    window.setFocus()
    print("      raise_() и activateWindow() вызваны OK")
except Exception as e:
    print(f"      ERROR: {e}")

# 10. Финальная информация
print("[10/10] Финальная информация...")
print(f"      isVisible: {window.isVisible()}")
print(f"      isMinimized: {window.isMinimized()}")
print(f"      isMaximized: {window.isMaximized()}")
print(f"      isActiveWindow: {window.isActiveWindow()}")
print(f"      windowState: {window.windowState()}")
print(f"      Frame Geometry: x={window.frameGeometry().x()}, y={window.frameGeometry().y()}, w={window.frameGeometry().width()}, h={window.frameGeometry().height()}")

print("\n" + "="*70)
print("  DIAGNOSIS COMPLETE")
print("="*70)
print("\nОкно должно быть видно!")
print("\nЕсли окна НЕ видно:")
print("  1. Нажмите Win+Tab - ищите 'Spam KP Assistant'")
print("  2. Нажмите Alt+Tab - переключитесь на окно")
print("  3. Проверьте панель задач внизу")
print("  4. Окно может быть за пределами экрана")
print("  5. Проверьте другие мониторы (если есть)")
print("\nПодождите 5 секунд, затем нажмите Enter...")

import time
time.sleep(5)

try:
    input()
except:
    pass

print("\nЗапуск цикла событий...")
sys.exit(app.exec())
