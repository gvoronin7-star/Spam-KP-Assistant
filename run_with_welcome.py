"""
Запуск с принудительным приветствием
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QSettings

# Сброс настройки приветствия
settings = QSettings("NLP-Core-Team", "SpamKPAssistant")
settings.setValue("welcome_seen", False)
print("Приветствие сброшено")

from gui.app import run_app
run_app()
