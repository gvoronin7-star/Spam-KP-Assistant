"""
Скрипт для проверки GUI и запуска с диагностикой
"""
import sys
from pathlib import Path
import subprocess

# Добавление корня проекта
sys.path.insert(0, str(Path(__file__).parent))

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import QTimer
from loguru import logger


def check_and_run():
    """Проверка и запуск с диагностикой"""
    print("=" * 60)
    print("  Spam KP Assistant - Диагностика GUI")
    print("=" * 60)
    print()
    
    # 1. Проверка Python
    print(f"[1/5] Python: {sys.version}")
    print()
    
    # 2. Проверка PyQt6
    try:
        from PyQt6.QtCore import QT_VERSION_STR
        print(f"[2/5] PyQt6: {QT_VERSION_STR}")
    except ImportError as e:
        print(f"[2/5] PyQt6: ОШИБКА - {e}")
        return False
    print()
    
    # 3. Проверка БД
    try:
        from core.database import engine
        print(f"[3/5] БД: {engine.url}")
    except Exception as e:
        print(f"[3/5] БД: ОШИБКА - {e}")
        return False
    print()
    
    # 4. Проверка GUI компонентов
    try:
        from gui.main_window import MainWindow
        print(f"[4/5] MainWindow: OK")
    except Exception as e:
        print(f"[4/5] MainWindow: ОШИБКА - {e}")
        return False
    print()
    
    # 5. Запуск приложения
    print(f"[5/5] Запуск GUI приложения...")
    print()
    print("Приложение должно открыться в новом окне.")
    print("Если окно не видно, проверьте панель задач.")
    print()
    print("Для выхода: нажмите Ctrl+C в терминале")
    print("-" * 60)
    print()
    
    # Создаём приложение
    app = QApplication(sys.argv)
    app.setApplicationName("Spam KP Assistant")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("NLP-Core-Team")
    
    # Главное окно
    try:
        window = MainWindow()
        window.show()
        window.raise_()
        window.activateWindow()
        
        print("[OK] Окно создано и показано!")
        print(f"    Размер: {window.width()}x{window.height()}")
        print(f"    Позиция: окно будет по центру экрана")
        print()
        
        # Логирование
        logger.add("data/gui.log", rotation="10 MB", level="DEBUG")
        logger.info("GUI запущен")
        
        # Цикл событий
        sys.exit(app.exec())
        
    except Exception as e:
        print(f"[ERROR] Ошибка создания окна: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    check_and_run()
