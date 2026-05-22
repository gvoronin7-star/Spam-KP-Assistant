"""
Диалог ручного добавления контакта
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QLineEdit, QTextEdit, QFormLayout, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QRegularExpressionValidator
from loguru import logger
import re


class DialogAddContact(QDialog):
    """Диалог добавления контакта поставщика"""

    contact_saved = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Добавить контакт")
        self.setMinimumSize(500, 350)

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(12)

        # Заголовок
        lbl_header = QLabel("➕ Новый контакт поставщика")
        lbl_header.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(lbl_header)

        # Форма
        form_layout = QFormLayout()
        form_layout.setSpacing(8)

        # Email (обязательное, с валидацией)
        self.txt_email = QLineEdit()
        self.txt_email.setPlaceholderText("supplier@company.ru")
        # Валидатор email через regex
        email_regex = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        validator = QRegularExpressionValidator(email_regex, self.txt_email)
        self.txt_email.setValidator(validator)
        form_layout.addRow("* Email:", self.txt_email)

        # Название компании
        self.txt_company = QLineEdit()
        self.txt_company.setPlaceholderText("ООО Пример")
        form_layout.addRow("Компания:", self.txt_company)

        # Контактное лицо
        self.txt_person = QLineEdit()
        self.txt_person.setPlaceholderText("Иванов Иван Иванович")
        form_layout.addRow("Контактное лицо:", self.txt_person)

        # Заметки
        self.txt_notes = QTextEdit()
        self.txt_notes.setPlaceholderText("Дополнительная информация о поставщике...")
        self.txt_notes.setMaximumHeight(100)
        form_layout.addRow("Заметки:", self.txt_notes)

        layout.addLayout(form_layout)

        # Подсказка
        lbl_hint = QLabel("* — обязательное поле")
        lbl_hint.setStyleSheet("color: gray; font-size: 11px;")
        layout.addWidget(lbl_hint)

        layout.addStretch()

        # Кнопки
        btn_layout = QHBoxLayout()

        btn_save = QPushButton("💾 Сохранить")
        btn_save.setDefault(True)
        btn_save.clicked.connect(self._save_contact)
        btn_layout.addWidget(btn_save)

        btn_layout.addStretch()

        btn_cancel = QPushButton("Отмена")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)

        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def _validate(self) -> bool:
        """Валидация формы"""
        email = self.txt_email.text().strip()

        if not email:
            QMessageBox.warning(self, "Ошибка", "Укажите email!")
            self.txt_email.setFocus()
            return False

        # Дополнительная проверка email regex (валидатор Qt не блокирует ввод)
        email_pattern = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
        if not email_pattern.match(email):
            QMessageBox.warning(self, "Ошибка", "Некорректный email!")
            self.txt_email.setFocus()
            return False

        return True

    def _save_contact(self):
        """Сохранение контакта в БД"""
        if not self._validate():
            return

        contact_data = {
            "email": self.txt_email.text().strip().lower(),
            "company_name": self.txt_company.text().strip() or None,
            "contact_person": self.txt_person.text().strip() or None,
            "notes": self.txt_notes.toPlainText().strip() or None,
        }

        try:
            from core.database import SessionLocal
            from core.models import Contact

            db = SessionLocal()
            try:
                # Проверка на дубликат
                existing = db.query(Contact).filter_by(email=contact_data["email"]).first()
                if existing:
                    reply = QMessageBox.question(
                        self,
                        "Контакт существует",
                        f"Контакт с email {contact_data['email']} уже существует.\n\n"
                        "Обновить данные?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    )
                    if reply == QMessageBox.StandardButton.Yes:
                        existing.company_name = contact_data["company_name"] or existing.company_name
                        existing.contact_person = contact_data["contact_person"] or existing.contact_person
                        existing.notes = contact_data["notes"] or existing.notes
                        existing.is_active = True
                        db.commit()
                        db.refresh(existing)

                        self.contact_saved.emit({
                            "id": existing.id,
                            "email": existing.email,
                            "company_name": existing.company_name,
                            "action": "updated",
                        })
                        QMessageBox.information(self, "Успех", "Контакт обновлён!")
                        self.accept()
                    return

                # Создание нового контакта
                contact = Contact(
                    email=contact_data["email"],
                    company_name=contact_data["company_name"],
                    contact_person=contact_data["contact_person"],
                    notes=contact_data["notes"],
                    is_active=True,
                )
                db.add(contact)
                db.commit()
                db.refresh(contact)

                contact_data["id"] = contact.id
                contact_data["action"] = "created"

                logger.info(f"Контакт создан: ID={contact.id}, email={contact.email}")

                self.contact_saved.emit(contact_data)
                QMessageBox.information(self, "Успех", "Контакт добавлен!")
                self.accept()

            finally:
                db.close()

        except Exception as e:
            logger.error(f"Ошибка сохранения контакта: {e}")
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить контакт:\n{str(e)}")
