"""
Диалог настройки LLM (ProxyAPI)
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QLineEdit, QFormLayout, QComboBox, QSpinBox, QMessageBox,
    QGroupBox, QCheckBox, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal
from loguru import logger


class DialogLLMSettings(QDialog):
    """Диалог настройки моделей LLM"""

    settings_saved = pyqtSignal(dict)

    # Доступные модели
    MODELS = [
        ("gpt-5.4-mini", "GPT-5.4 Mini (быстрая, дешевая)"),
        ("gpt-5.3-chat-latest", "GPT-5.3 Chat (умная, сбалансированная)"),
        ("gemini-3.1-flash-lite", "Gemini 3.1 Flash (для парсинга)"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Настройка LLM (ProxyAPI)")
        self.setMinimumSize(550, 450)

        self._setup_ui()
        self._load_current_settings()

    def _setup_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(12)

        # Заголовок
        lbl_header = QLabel("🤖 Настройка подключения к ProxyAPI")
        lbl_header.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(lbl_header)

        lbl_info = QLabel(
            "Получите API-ключ на <a href='https://console.proxyapi.ru/'>console.proxyapi.ru</a>"
        )
        lbl_info.setOpenExternalLinks(True)
        lbl_info.setStyleSheet("color: #0066cc;")
        layout.addWidget(lbl_info)

        # Основные настройки
        basic_group = QGroupBox("Основные параметры")
        basic_layout = QFormLayout()
        basic_layout.setSpacing(8)

        # API-ключ
        self.txt_api_key = QLineEdit()
        self.txt_api_key.setPlaceholderText("sk-...")
        self.txt_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        basic_layout.addRow("* API ключ:", self.txt_api_key)

        # Показать/скрыть ключ
        self.chk_show_key = QCheckBox("Показать ключ")
        self.chk_show_key.stateChanged.connect(self._toggle_key_visibility)
        basic_layout.addRow("", self.chk_show_key)

        # Основная модель
        self.combo_model = QComboBox()
        for model_id, model_name in self.MODELS:
            self.combo_model.addItem(model_name, model_id)
        basic_layout.addRow("Модель:", self.combo_model)

        # Fallback модель
        self.combo_fallback = QComboBox()
        for model_id, model_name in self.MODELS:
            self.combo_fallback.addItem(model_name, model_id)
        self.combo_fallback.setCurrentIndex(1)  # gpt-5.3-chat-latest
        basic_layout.addRow("Fallback модель:", self.combo_fallback)

        basic_group.setLayout(basic_layout)
        layout.addWidget(basic_group)

        # Rate limiting
        rate_group = QGroupBox("Ограничения скорости (Rate Limiting)")
        rate_layout = QFormLayout()

        self.spn_rpm = QSpinBox()
        self.spn_rpm.setRange(1, 10000)
        self.spn_rpm.setValue(60)
        self.spn_rpm.setSuffix(" запросов/мин")
        rate_layout.addRow("RPM (запросы в минуту):", self.spn_rpm)

        self.spn_tpm = QSpinBox()
        self.spn_tpm.setRange(1000, 10_000_000)
        self.spn_tpm.setSingleStep(1000)
        self.spn_tpm.setValue(60000)
        self.spn_tpm.setSuffix(" токенов/мин")
        rate_layout.addRow("TPM (токены в минуту):", self.spn_tpm)

        rate_group.setLayout(rate_layout)
        layout.addWidget(rate_group)

        # Статус
        self.lbl_status = QLabel("Статус: Не проверено")
        self.lbl_status.setStyleSheet("color: gray;")
        layout.addWidget(self.lbl_status)

        layout.addStretch()

        # Кнопки
        btn_layout = QHBoxLayout()

        btn_test = QPushButton("🧪 Тестировать")
        btn_test.setToolTip("Отправить тестовый запрос к ProxyAPI")
        btn_test.clicked.connect(self._test_connection)
        btn_layout.addWidget(btn_test)

        btn_save = QPushButton("💾 Сохранить")
        btn_save.setDefault(True)
        btn_save.clicked.connect(self._save_settings)
        btn_layout.addWidget(btn_save)

        btn_layout.addStretch()

        btn_cancel = QPushButton("Отмена")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)

        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def _toggle_key_visibility(self, state):
        """Показать/скрыть API-ключ"""
        if state == Qt.CheckState.Checked.value:
            self.txt_api_key.setEchoMode(QLineEdit.EchoMode.Normal)
        else:
            self.txt_api_key.setEchoMode(QLineEdit.EchoMode.Password)

    def _load_current_settings(self):
        """Загрузка текущих настроек из config"""
        from config import settings

        # API-ключ (если есть)
        if settings.proxyapi_api_key and settings.proxyapi_api_key != "your_api_key_here":
            self.txt_api_key.setText(settings.proxyapi_api_key)
            self.lbl_status.setText("Статус: Ключ загружен из .env")
            self.lbl_status.setStyleSheet("color: blue;")

        # Модель
        current_model = settings.proxyapi_primary_model
        for i in range(self.combo_model.count()):
            if self.combo_model.itemData(i) == current_model:
                self.combo_model.setCurrentIndex(i)
                break

        # Fallback
        fallback_model = getattr(settings, 'proxyapi_fallback_model', 'gpt-5.3-chat-latest')
        for i in range(self.combo_fallback.count()):
            if self.combo_fallback.itemData(i) == fallback_model:
                self.combo_fallback.setCurrentIndex(i)
                break

    def _test_connection(self):
        """Тестовый запрос к ProxyAPI"""
        api_key = self.txt_api_key.text().strip()

        if not api_key:
            QMessageBox.warning(self, "Ошибка", "Введите API-ключ!")
            return

        if api_key == "your_api_key_here":
            QMessageBox.warning(self, "Ошибка", "Введите реальный API-ключ!")
            return

        model = self.combo_model.currentData()

        self.lbl_status.setText("⏳ Проверка подключения...")
        self.lbl_status.setStyleSheet("color: orange;")
        QApplication.processEvents()

        try:
            from services.llm_service import LLMService

            service = LLMService()
            service.configure(api_key)
            service.primary_model = model

            if service.test_connection():
                self.lbl_status.setText("✅ Подключение успешно!")
                self.lbl_status.setStyleSheet("color: green; font-weight: bold;")
                QMessageBox.information(
                    self,
                    "Успех",
                    f"✅ Подключение к ProxyAPI успешно!\n\n"
                    f"Модель: {model}\n"
                    f"API-ключ работает корректно."
                )
            else:
                self.lbl_status.setText("❌ Ошибка подключения")
                self.lbl_status.setStyleSheet("color: red;")
                QMessageBox.critical(
                    self,
                    "Ошибка",
                    "❌ Не удалось подключиться к ProxyAPI.\n\n"
                    "Проверьте:\n"
                    "• Правильность API-ключа\n"
                    "• Наличие баланса на счету\n"
                    "• Подключение к интернету"
                )

        except Exception as e:
            self.lbl_status.setText(f"❌ Ошибка: {str(e)[:40]}")
            self.lbl_status.setStyleSheet("color: red;")
            logger.error(f"Ошибка теста LLM: {e}")
            QMessageBox.critical(
                self,
                "Ошибка",
                f"Не удалось протестировать подключение:\n{str(e)}"
            )

    def _save_settings(self):
        """Сохранение настроек"""
        api_key = self.txt_api_key.text().strip()

        if not api_key:
            QMessageBox.warning(self, "Ошибка", "Введите API-ключ!")
            return

        model = self.combo_model.currentData()
        fallback = self.combo_fallback.currentData()
        rpm = self.spn_rpm.value()
        tpm = self.spn_tpm.value()

        try:
            # 1. Обновить .env файл
            self._update_env_file(api_key, model, fallback, rpm, tpm)

            # 2. Обновить runtime settings
            from config import settings
            settings.proxyapi_api_key = api_key
            settings.proxyapi_primary_model = model
            settings.proxyapi_fallback_model = fallback

            # 3. Сохранить в БД (таблица Settings)
            self._save_to_db(api_key, model, fallback, rpm, tpm)

            saved_data = {
                "model": model,
                "fallback": fallback,
                "rpm": rpm,
                "tpm": tpm,
            }

            logger.info(f"LLM настройки сохранены: модель={model}")

            self.settings_saved.emit(saved_data)
            QMessageBox.information(self, "Успех", "Настройки LLM сохранены!")
            self.accept()

        except Exception as e:
            logger.error(f"Ошибка сохранения настроек LLM: {e}")
            QMessageBox.critical(
                self,
                "Ошибка",
                f"Не удалось сохранить настройки:\n{str(e)}"
            )

    def _update_env_file(self, api_key, model, fallback, rpm, tpm):
        """Обновление .env файла"""
        from pathlib import Path

        env_path = Path(".env")

        # Значения для обновления
        updates = {
            "PROXYAPI_API_KEY": api_key,
            "PROXYAPI_PRIMARY_MODEL": model,
            "PROXYAPI_FALLBACK_MODEL": fallback,
            "PROXYAPI_RPM": str(rpm),
            "PROXYAPI_TPM": str(tpm),
        }

        if env_path.exists():
            lines = env_path.read_text(encoding="utf-8").splitlines()
            new_lines = []
            updated_keys = set()

            for line in lines:
                stripped = line.strip()
                if stripped and not stripped.startswith("#"):
                    key = stripped.split("=")[0].strip()
                    if key in updates:
                        new_lines.append(f"{key}={updates[key]}")
                        updated_keys.add(key)
                        continue
                new_lines.append(line)

            # Добавить новые ключи, которых не было
            for key, value in updates.items():
                if key not in updated_keys:
                    new_lines.append(f"{key}={value}")

            env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
        else:
            # Создать новый .env
            content = "# Spam KP Assistant — конфигурация\n"
            for key, value in updates.items():
                content += f"{key}={value}\n"
            env_path.write_text(content, encoding="utf-8")

    def _save_to_db(self, api_key, model, fallback, rpm, tpm):
        """Сохранение настроек в БД"""
        from core.database import SessionLocal
        from core.models import Settings as AppSettings

        db = SessionLocal()
        try:
            settings_data = {
                "llm_api_key_encrypted": api_key,  # В продакшене — шифровать!
                "llm_model": model,
                "llm_fallback_model": fallback,
                "llm_rpm": rpm,
                "llm_tpm": tpm,
            }

            # Проверить, есть ли уже запись
            existing = db.query(AppSettings).filter_by(key="llm_config").first()
            if existing:
                existing.value = settings_data
            else:
                setting = AppSettings(key="llm_config", value=settings_data)
                db.add(setting)

            db.commit()
        finally:
            db.close()
