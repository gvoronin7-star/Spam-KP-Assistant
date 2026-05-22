"""
Мастер создания профиля закупки
"""
from PyQt6.QtWidgets import (
    QWizard, QWizardPage, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QTextEdit, QComboBox, QCheckBox,
    QPushButton, QGroupBox, QFormLayout, QSpinBox, QDoubleSpinBox,
    QFileDialog, QListWidget, QListWidgetItem, QTabWidget,
    QMessageBox, QSplitter, QDialog, QDialogButtonBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from datetime import datetime
import json
from loguru import logger


class ProfileOverviewPage(QWizardPage):
    """Страница: Обзор профиля"""
    
    def __init__(self):
        super().__init__()
        self.setTitle("Обзор профиля закупки")
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout()
        
        # Название профиля
        form = QFormLayout()
        self.txt_name = QLineEdit()
        self.txt_name.setPlaceholderText("Например: Интернет-канал 100 Мбит/с")
        form.addRow("Название профиля:", self.txt_name)
        
        self.txt_description = QTextEdit()
        self.txt_description.setPlaceholderText("Краткое описание закупки...")
        self.txt_description.setMaximumHeight(80)
        form.addRow("Описание:", self.txt_description)
        
        layout.addLayout(form)
        
        # Инфо
        info = QLabel(
            "Профиль закупки содержит все параметры услуги, которую вы хотите заказать.\n"
            "Этот профиль можно использовать для множества поставщиков."
        )
        info.setWordWrap(True)
        layout.addWidget(info)
        
        self.setLayout(layout)
    
    def validatePage(self):
        if not self.txt_name.text().strip():
            QMessageBox.warning(self, "Ошибка", "Укажите название профиля")
            return False
        return True
    
    def get_data(self):
        return {
            "name": self.txt_name.text().strip(),
            "description": self.txt_description.toPlainText().strip()
        }


class TechParamsPage(QWizardPage):
    """Страница: Технические параметры"""
    
    def __init__(self):
        super().__init__()
        self.setTitle("Технические параметры услуги")
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout()
        
        # Основная информация
        main_group = QGroupBox("Основные параметры")
        main_layout = QFormLayout()
        
        self.txt_speed = QLineEdit()
        self.txt_speed.setPlaceholderText("100 Мбит/с")
        main_layout.addRow("Скорость:", self.txt_speed)
        
        self.txt_protocol = QComboBox()
        self.txt_protocol.addItems(["Ethernet", "MPLS", "VPLS", "IP-VPN", "Другое"])
        main_layout.addRow("Протокол:", self.txt_protocol)
        
        self.txt_cities = QLineEdit()
        self.txt_cities.setPlaceholderText("Москва, Санкт-Петербург")
        main_layout.addRow("Города:", self.txt_cities)
        
        self.spn_slad = QDoubleSpinBox()
        self.spn_slad.setRange(90.0, 100.0)
        self.spn_slad.setValue(99.9)
        self.spn_slad.setSuffix("%")
        self.spn_slad.setDecimals(1)
        main_layout.addRow("SLA:", self.spn_slad)
        
        self.txt_traffic = QLineEdit()
        self.txt_traffic.setPlaceholderText("Неограниченный / 10 ТБ/мес")
        main_layout.addRow("Объём трафика:", self.txt_traffic)
        
        main_group.setLayout(main_layout)
        layout.addWidget(main_group)
        
        # Доп. параметры
        extra_group = QGroupBox("Дополнительные параметры")
        extra_layout = QVBoxLayout()
        
        self.txt_extra = QTextEdit()
        self.txt_extra.setPlaceholderText("Дополнительные требования в свободной форме...")
        self.txt_extra.setMaximumHeight(100)
        extra_layout.addWidget(self.txt_extra)
        
        extra_group.setLayout(extra_layout)
        layout.addWidget(extra_group)
        
        self.setLayout(layout)
    
    def get_data(self):
        return {
            "speed": self.txt_speed.text().strip(),
            "protocol": self.txt_protocol.currentText(),
            "cities": self.txt_cities.text().strip(),
            "sla": self.spn_slad.value(),
            "traffic": self.txt_traffic.text().strip(),
            "extra": self.txt_extra.toPlainText().strip()
        }


class RequirementsPage(QWizardPage):
    """Страница: Требования к КП"""
    
    def __init__(self):
        super().__init__()
        self.setTitle("Требования к коммерческим предложениям")
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout()
        
        # Обязательные поля
        req_group = QGroupBox("Обязательные данные в КП")
        req_layout = QVBoxLayout()
        
        self.chk_price = QCheckBox("Цена (с разбивкой по услугам)")
        self.chk_price.setChecked(True)
        req_layout.addWidget(self.chk_price)
        
        self.chk_term = QCheckBox("Срок поставки/подключения")
        self.chk_term.setChecked(True)
        req_layout.addWidget(self.chk_term)
        
        self.chk_guarantee = QCheckBox("Гарантии SLA")
        req_layout.addWidget(self.chk_guarantee)
        
        self.chk_payment = QCheckBox("Форма оплаты")
        req_layout.addWidget(self.chk_payment)
        
        self.chk_contract = QCheckBox("Образец договора")
        req_layout.addWidget(self.chk_contract)
        
        req_group.setLayout(req_layout)
        layout.addWidget(req_group)
        
        # Условия контракта
        contract_group = QGroupBox("Условия контракта")
        contract_layout = QFormLayout()
        
        self.spn_min_contract = QSpinBox()
        self.spn_min_contract.setRange(1, 60)
        self.spn_min_contract.setValue(12)
        self.spn_min_contract.setSuffix(" месяцев")
        contract_layout.addRow("Мин. срок контракта:", self.spn_min_contract)
        
        self.chk_prepayment = QCheckBox("Допустима предоплата")
        contract_layout.addRow("", self.chk_prepayment)
        
        self.chk_discount = QCheckBox("Допустимы переговоры о скидке")
        self.chk_discount.setChecked(True)
        contract_layout.addRow("", self.chk_discount)
        
        contract_group.setLayout(contract_layout)
        layout.addWidget(contract_group)
        
        self.setLayout(layout)
    
    def get_data(self):
        return {
            "required_fields": {
                "price": self.chk_price.isChecked(),
                "term": self.chk_term.isChecked(),
                "guarantee": self.chk_guarantee.isChecked(),
                "payment": self.chk_payment.isChecked(),
                "contract": self.chk_contract.isChecked()
            },
            "min_contract_months": self.spn_min_contract.value(),
            "allow_prepayment": self.chk_prepayment.isChecked(),
            "allow_discount_negotiation": self.chk_discount.isChecked()
        }


class QnAPage(QWizardPage):
    """Страница: Q&A пары для LLM"""
    
    def __init__(self):
        super().__init__()
        self.setTitle("Шаблоны ответов (Q&A)")
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout()
        
        # Список Q&A
        self.list_qa = QListWidget()
        self.list_qa.setMinimumHeight(200)
        layout.addWidget(self.list_qa)
        
        # Кнопки
        btn_layout = QHBoxLayout()
        
        btn_add = QPushButton("➕ Добавить")
        btn_add.clicked.connect(self._add_qa)
        btn_layout.addWidget(btn_add)
        
        btn_edit = QPushButton("✏️ Редактировать")
        btn_edit.clicked.connect(self._edit_qa)
        btn_layout.addWidget(btn_edit)
        
        btn_delete = QPushButton("🗑️ Удалить")
        btn_delete.clicked.connect(self._delete_qa)
        btn_layout.addWidget(btn_delete)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        # Инфо
        info = QLabel(
            "Q&A пары используются LLM для быстрых ответов на типовые вопросы.\n"
            "Добавьте до 20 наиболее частых вопросов."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(info)
        
        self.setLayout(layout)
    
    def _add_qa(self):
        item = QListWidgetItem("Новый вопрос - Нажмите 'Редактировать'")
        self.list_qa.addItem(item)
        self._edit_qa()
    
    def _edit_qa(self):
        current_row = self.list_qa.currentRow()
        if current_row < 0:
            QMessageBox.information(self, "Инфо", "Выберите вопрос для редактирования")
            return
        
        # Простое редактирование через диалог
        dialog = QDialog(self)
        dialog.setWindowTitle("Редактировать Q&A пару")
        dialog.setMinimumSize(500, 300)
        
        layout = QVBoxLayout()
        
        lbl_question = QLabel("Вопрос поставщика:")
        layout.addWidget(lbl_question)
        
        txt_question = QLineEdit()
        layout.addWidget(txt_question)
        
        lbl_answer = QLabel("Ответ:")
        layout.addWidget(lbl_answer)
        
        txt_answer = QTextEdit()
        layout.addWidget(txt_answer)
        
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        dialog.setLayout(layout)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            if txt_question.text() and txt_answer.toPlainText():
                self.list_qa.item(current_row).setText(
                    f"{txt_question.text()} → {txt_answer.toPlainText()[:50]}..."
                )
                # Сохранение в userData
                self.list_qa.item(current_row).setData(
                    Qt.ItemDataRole.UserRole,
                    {"question": txt_question.text(), "answer": txt_answer.toPlainText()}
                )
    
    def _delete_qa(self):
        current_row = self.list_qa.currentRow()
        if current_row >= 0:
            self.list_qa.takeItem(current_row)
    
    def get_data(self):
        qa_pairs = []
        for i in range(self.list_qa.count()):
            item = self.list_qa.item(i)
            data = item.data(Qt.ItemDataRole.UserRole)
            if data:
                qa_pairs.append(data)
        return qa_pairs


class AttachmentsPage(QWizardPage):
    """Страница: Вложения"""
    
    def __init__(self):
        super().__init__()
        self.setTitle("Вложения к запросу")
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout()
        
        # Список файлов
        self.list_files = QListWidget()
        self.list_files.setMinimumHeight(150)
        layout.addWidget(self.list_files)
        
        # Кнопки
        btn_layout = QHBoxLayout()
        
        btn_add = QPushButton("📎 Добавить файл")
        btn_add.clicked.connect(self._add_file)
        btn_layout.addWidget(btn_add)
        
        btn_remove = QPushButton("❌ Удалить")
        btn_remove.clicked.connect(self._remove_file)
        btn_layout.addWidget(btn_remove)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        # Инфо
        info = QLabel(
            "Вложения будут прикреплены ко всем письмам:\n"
            "Техническое задание, опросный лист, схемы и т.д."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: gray;")
        layout.addWidget(info)
        
        self.setLayout(layout)
    
    def _add_file(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Выберите файлы", "",
            "Все файлы (*.*)"
        )
        for file_path in files:
            item = QListWidgetItem(file_path)
            item.setData(Qt.ItemDataRole.UserRole, file_path)
            self.list_files.addItem(item)
    
    def _remove_file(self):
        current_row = self.list_files.currentRow()
        if current_row >= 0:
            self.list_files.takeItem(current_row)
    
    def get_data(self):
        files = []
        for i in range(self.list_files.count()):
            item = self.list_files.item(i)
            files.append(item.data(Qt.ItemDataRole.UserRole))
        return files


class ProfileWizard(QWizard):
    """Мастер создания профиля закупки"""
    
    profile_created = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Мастер создания профиля закупки")
        self.setMinimumSize(700, 500)
        
        # Страницы
        self.addPage(ProfileOverviewPage())
        self.addPage(TechParamsPage())
        self.addPage(RequirementsPage())
        self.addPage(QnAPage())
        self.addPage(AttachmentsPage())
        
        # Кнопки
        self.setButtonText(QWizard.WizardButton.FinishButton, "✅ Создать профиль")
        
        # Соединить сигнал с методом сохранения
        self.finished.connect(self._on_wizard_finished)
        
        logger.info("Мастер профиля запущен")
    
    def _on_wizard_finished(self):
        """Вызывается при нажатии кнопки 'Готово'"""
        logger.info("Мастер завершён, сохраняю профиль...")
        
        if self._save_profile():
            logger.info("Профиль успешно сохранён")
        else:
            logger.error("Ошибка сохранения профиля")
    
    def _save_profile(self):
        """Сохранение профиля в БД"""
        db = None
        try:
            from core.database import SessionLocal
            from core.models import Profile
            
            db = SessionLocal()
            
            # Сбор данных со всех страниц
            page0 = self.page(0)  # Overview
            page1 = self.page(1)  # Tech params
            page2 = self.page(2)  # Requirements
            page3 = self.page(3)  # Q&A
            page4 = self.page(4)  # Attachments
            
            name = page0.get_data()["name"]
            description = page0.get_data()["description"]
            
            logger.info(f"Сохранение профиля: name={name}, desc={description}")
            
            profile = Profile(
                name=name,
                description=description,
                tech_params=page1.get_data(),
                requirements=page2.get_data(),
                dialogue_rules={"qa_pairs": page3.get_data()},
                attachments=page4.get_data(),
                is_active=True
            )
            
            db.add(profile)
            logger.info("Профиль добавлен в сессию, выполняю flush...")
            
            db.flush()
            logger.info(f"Flush выполнен, профиль получил временный ID: {profile.id}")
            
            logger.info("Выполняю commit...")
            db.commit()
            logger.info("Commit выполнен успешно")
            
            db.refresh(profile)
            logger.info(f"Профиль создан: ID={profile.id}, name={profile.name}")
            
            self.profile_created.emit({
                "id": profile.id,
                "name": profile.name
            })
            
            return True
        
        except Exception as e:
            logger.error(f"Ошибка сохранения профиля: {e}", exc_info=True)
            if db:
                db.rollback()
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить профиль:\n{str(e)}")
            return False

        finally:
            if db:
                db.close()
