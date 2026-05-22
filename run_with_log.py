"""
Запуск приложения с записью ошибок в файл
"""
import sys
import traceback
from pathlib import Path
from datetime import datetime

# Перенаправляем stderr в файл
log_file = open("data/gui_error.log", "w", encoding="utf-8")

class Logger:
    def __init__(self, file):
        self.file = file
        self.original_stderr = sys.stderr
        
    def write(self, text):
        self.file.write(text)
        self.file.flush()
        self.original_stderr.write(text)
        
    def flush(self):
        self.file.flush()
        self.original_stderr.flush()

sys.stderr = Logger(log_file)

print(f"[{datetime.now()}] Запуск Spam KP Assistant...", file=sys.stderr)

try:
    sys.path.insert(0, str(Path(__file__).parent))
    
    from PyQt6.QtWidgets import QApplication
    from gui.main_window import MainWindow
    
    print("[OK] PyQt6 импортирован", file=sys.stderr)
    
    app = QApplication(sys.argv)
    print("[OK] QApplication создан", file=sys.stderr)
    
    window = MainWindow()
    print("[OK] MainWindow создан", file=sys.stderr)
    
    window.show()
    window.raise_()
    window.activateWindow()
    print("[OK] Окно показано!", file=sys.stderr)
    
    result = app.exec()
    print(f"[OK] Завершено с кодом: {result}", file=sys.stderr)
    
except Exception as e:
    print(f"[ERROR] {e}", file=sys.stderr)
    traceback.print_exc(file=sys.stderr)
    
finally:
    log_file.close()
