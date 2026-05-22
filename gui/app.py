"""
Точка входа для GUI приложения
"""
import sys
import os
from pathlib import Path
from PyQt6.QtWidgets import QApplication

# Настройка логирования ПЕРЕД импортом loguru
os.makedirs("data", exist_ok=True)

from loguru import logger

# Добавление корня проекта в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

from gui.main_window import MainWindow
from core.database import init_db


def run_app():
    """Запуск приложения"""
    from config import __version__
    
    # Настройка логирования с UTF-8
    logger.remove()  # Удалить дефолтный хендлер
    logger.add(
        "data/app.log",
        rotation="10 MB",
        retention="10 days",
        level="DEBUG",
        encoding="utf-8"
    )
    
    logger.info(f"Запуск Спам-КП-ассистента v{__version__}")
    
    # Инициализация БД
    init_db()
    
    # Создание приложения
    app = QApplication(sys.argv)
    app.setApplicationName("Спам-КП-ассистент")
    app.setApplicationVersion(__version__)
    app.setOrganizationName("NLP-Core-Team")
    
    # Главное окно
    window = MainWindow()
    window.show()
    
    logger.info("Приложение запущено")
    
    # Запуск цикла событий
    sys.exit(app.exec())


if __name__ == "__main__":
    run_app()
