"""
Простой тест PyQt6
"""
import sys
from PyQt6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget

print("1. Создание QApplication...")
app = QApplication(sys.argv)

print("2. Создание окна...")
window = QLabel("Spam KP Assistant работает!")
window.setWindowTitle("Тест PyQt6")
window.resize(400, 200)

print("3. Показ окна...")
window.show()

print("4. Запуск цикла событий...")
print("Окно должно быть видно на экране!")
print("Закройте окно для завершения теста")

result = app.exec()
print(f"5. Результат: {result}")
print("Тест завершён")
