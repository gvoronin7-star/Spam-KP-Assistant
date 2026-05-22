"""
Диалог импорта контактов
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QFileDialog, QTableWidget, QTableWidgetItem, QHeaderView,
    QProgressBar, QMessageBox, QComboBox, QLineEdit, QGroupBox,
    QCheckBox, QGridLayout, QSpinBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from loguru import logger
import os


class ImportWorker(QThread):
    """Фоновый поток для импорта контактов"""
    
    progress = pyqtSignal(int)
    finished = pyqtSignal(list)
    error = pyqtSignal(str)
    
    def __init__(self, file_path, file_type, skip_header, email_column, name_columns):
        super().__init__()
        self.file_path = file_path
        self.file_type = file_type
        self.skip_header = skip_header
        self.email_column = email_column
        self.name_columns = name_columns
    
    def run(self):
        try:
            from services.contact_importer import import_contacts
            
            contacts = import_contacts(
                self.file_path,
                self.skip_header,
                self.email_column,
                self.name_columns[0] if self.name_columns else 1,
                self.name_columns[1] if self.name_columns and len(self.name_columns) > 1 else 2
            )
            
            # Прогресс завершён
            self.progress.emit(100)
            self.finished.emit(contacts)
        
        except Exception as e:
            self.error.emit(str(e))


class DialogImportContacts(QDialog):
    """Диалог импорта контактов"""
    
    contacts_imported = pyqtSignal(list)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Импорт контактов")
        self.setMinimumSize(800, 600)
        
        self.contacts = []
        self.worker = None
        
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout()
        
        # Шаг 1: Выбор файла
        file_group = QGroupBox("1. Выберите файл")
        file_layout = QHBoxLayout()
        
        self.txt_file = QLineEdit()
        self.txt_file.setReadOnly(True)
        file_layout.addWidget(self.txt_file)
        
        btn_browse = QPushButton("📂 Обзор...")
        btn_browse.clicked.connect(self._browse_file)
        file_layout.addWidget(btn_browse)
        
        self.combo_type = QComboBox()
        self.combo_type.addItems(["CSV (.csv)", "Excel (.xlsx)", "Excel (.xls)"])
        file_layout.addWidget(self.combo_type)
        
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)
        
        # Шаг 2: Настройка колонок
        columns_group = QGroupBox("2. Настройка колонок")
        columns_layout = QGridLayout()
        
        columns_layout.addWidget(QLabel("Email (номер колонки):"), 0, 0)
        self.spin_email = QSpinBox()
        self.spin_email.setRange(0, 50)
        self.spin_email.setValue(0)
        columns_layout.addWidget(self.spin_email, 0, 1)
        
        columns_layout.addWidget(QLabel("Компания (номер колонки):"), 1, 0)
        self.spin_company = QSpinBox()
        self.spin_company.setRange(0, 50)
        self.spin_company.setValue(1)
        columns_layout.addWidget(self.spin_company, 1, 1)
        
        columns_layout.addWidget(QLabel("Контактное лицо (номер колонки):"), 2, 0)
        self.spin_person = QSpinBox()
        self.spin_person.setRange(0, 50)
        self.spin_person.setValue(2)
        columns_layout.addWidget(self.spin_person, 2, 1)
        
        self.chk_skip_header = QCheckBox("Первая строка - заголовок")
        self.chk_skip_header.setChecked(True)
        columns_layout.addWidget(self.chk_skip_header, 3, 0, 1, 2)
        
        columns_group.setLayout(columns_layout)
        layout.addWidget(columns_group)
        
        # Шаг 3: Предпросмотр
        preview_group = QGroupBox("3. Предпросмотр (первые 10 строк)")
        preview_layout = QVBoxLayout()
        
        self.table_preview = QTableWidget()
        self.table_preview.setColumnCount(4)
        self.table_preview.setHorizontalHeaderLabels(["#", "Email", "Компания", "Контактное лицо"])
        self.table_preview.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_preview.setMaximumHeight(200)
        preview_layout.addWidget(self.table_preview)
        
        self.lbl_count = QLabel("Всего контактов: 0")
        preview_layout.addWidget(self.lbl_count)
        
        preview_group.setLayout(preview_layout)
        layout.addWidget(preview_group)
        
        # Прогресс
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)
        
        # Кнопки
        btn_layout = QHBoxLayout()
        
        btn_validate = QPushButton("✅ Проверить файл")
        btn_validate.clicked.connect(self._validate_file)
        btn_layout.addWidget(btn_validate)
        
        btn_import = QPushButton("📥 Импортировать")
        btn_import.clicked.connect(self._import_contacts)
        btn_import.setEnabled(False)
        self.btn_import = btn_import
        btn_layout.addWidget(btn_import)
        
        btn_layout.addStretch()
        
        btn_cancel = QPushButton("Отмена")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)
        
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
    
    def _browse_file(self):
        """Выбор файла"""
        file_type = self.combo_type.currentText()
        
        if "CSV" in file_type:
            filter_str = "CSV файлы (*.csv)"
        else:
            filter_str = "Excel файлы (*.xlsx *.xls)"
        
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Выберите файл", "", filter_str
        )
        
        if file_path:
            self.txt_file.setText(file_path)
            
            # Автоматическое определение типа
            if file_path.endswith('.csv'):
                self.combo_type.setCurrentIndex(0)
            else:
                self.combo_type.setCurrentIndex(1)
    
    def _validate_file(self):
        """Проверка файла"""
        file_path = self.txt_file.text()
        
        if not file_path:
            QMessageBox.warning(self, "Ошибка", "Выберите файл!")
            return
        
        try:
            file_type = "csv" if self.combo_type.currentText().startswith("CSV") else "xlsx"
            
            # Запуск импорта только для предпросмотра
            self.progress.setVisible(True)
            self.progress.setValue(0)
            self.btn_import.setEnabled(False)
            
            self.worker = ImportWorker(
                file_path,
                file_type,
                self.chk_skip_header.isChecked(),
                self.spin_email.value(),
                [self.spin_company.value(), self.spin_person.value()]
            )
            
            self.worker.progress.connect(self._on_preview_progress)
            self.worker.finished.connect(self._on_preview_finished)
            self.worker.error.connect(self._on_preview_error)
            self.worker.start()
        
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка чтения файла:\n{str(e)}")
            self.progress.setVisible(False)
    
    def _on_preview_progress(self, value):
        """Прогресс предпросмотра"""
        self.progress.setValue(value)
    
    def _on_preview_finished(self, contacts):
        """Завершение предпросмотра"""
        self.progress.setVisible(False)
        self.contacts = contacts[:10]  # Только первые 10 для предпросмотра
        self._update_preview_table()
        
        total = len(contacts)
        self.lbl_count.setText(f"Всего контактов: {total}")
        
        if total > 0:
            self.btn_import.setEnabled(True)
            QMessageBox.information(self, "Успех", f"Найдено контактов: {total}")
        else:
            QMessageBox.warning(self, "Предупреждение", "Контакты не найдены. Проверьте настройки колонок.")
    
    def _on_preview_error(self, error_msg):
        """Ошибка предпросмотра"""
        self.progress.setVisible(False)
        QMessageBox.critical(self, "Ошибка", f"Ошибка импорта:\n{error_msg}")
        self.btn_import.setEnabled(False)
    
    def _update_preview_table(self):
        """Обновление таблицы предпросмотра"""
        try:
            self.table_preview.setRowCount(len(self.contacts))
            
            for idx, contact in enumerate(self.contacts):
                email = contact.get("email", "—")
                company = contact.get("company_name", "—")
                person = contact.get("contact_person", "—")
                
                self.table_preview.setItem(idx, 0, QTableWidgetItem(str(idx + 1)))
                self.table_preview.setItem(idx, 1, QTableWidgetItem(email))
                self.table_preview.setItem(idx, 2, QTableWidgetItem(company))
                self.table_preview.setItem(idx, 3, QTableWidgetItem(person))
        except Exception as e:
            logger.error(f"Ошибка обновления таблицы предпросмотра: {e}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", f"Ошибка отображения предпросмотра:\n{str(e)}")
    
    def _import_contacts(self):
        """Импорт всех контактов"""
        file_path = self.txt_file.text()
        file_type = "csv" if self.combo_type.currentText().startswith("CSV") else "xlsx"
        
        if not file_path:
            QMessageBox.warning(self, "Ошибка", "Выберите файл!")
            return
        
        # Подтверждение
        reply = QMessageBox.question(
            self, "Подтверждение",
            f"Импортировать все контакты?\n"
            f"Файл: {os.path.basename(file_path)}\n"
            f"Контактов: {self.lbl_count.text()}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        self.progress.setVisible(True)
        self.progress.setValue(0)
        self.btn_import.setEnabled(False)
        
        try:
            # Запуск импорта
            self.worker = ImportWorker(
                file_path,
                file_type,
                self.chk_skip_header.isChecked(),
                self.spin_email.value(),
                [self.spin_company.value(), self.spin_person.value()]
            )
            
            self.worker.progress.connect(self._on_import_progress)
            self.worker.finished.connect(self._on_import_finished)
            self.worker.error.connect(self._on_import_error)
            self.worker.start()
        except Exception as e:
            logger.error(f"Ошибка запуска импорта: {e}", exc_info=True)
            self.progress.setVisible(False)
            self.btn_import.setEnabled(True)
            QMessageBox.critical(self, "Ошибка", f"Ошибка импорта:\n{str(e)}")
    
    def _on_import_progress(self, value):
        """Прогресс импорта"""
        self.progress.setValue(value)
    
    def _on_import_finished(self, contacts):
        """Завершение импорта"""
        self.progress.setVisible(False)
        
        # Сохранение в БД
        from services.contact_importer import save_contacts_to_db
        
        saved_count = save_contacts_to_db(contacts)
        
        # Сигнал родителю
        self.contacts_imported.emit(contacts)
        
        QMessageBox.information(
            self, "Успех",
            f"Импортировано и сохранено контактов: {saved_count}\n"
            f"(Дубликаты пропущены)"
        )
        
        self.accept()
    
    def _on_import_error(self, error_msg):
        """Ошибка импорта"""
        self.progress.setVisible(False)
        QMessageBox.critical(self, "Ошибка", f"Ошибка импорта:\n{error_msg}")
        self.btn_import.setEnabled(True)
