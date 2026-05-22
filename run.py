"""
Точка входа приложения
"""
import sys
from pathlib import Path

# Добавление корня проекта в путь
sys.path.insert(0, str(Path(__file__).parent))

from gui.app import run_app

if __name__ == "__main__":
    run_app()
