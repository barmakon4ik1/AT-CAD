"""
errors/at_errors.py

Модуль централизованных исключений CAD-приложения.

Содержит базовый класс ATError и специализированные исключения
для геометрии, текста и входных данных.
Обеспечивает единый формат сообщений и отображение ошибок через popup.
"""

from locales.at_translations import loc
from windows.at_gui_utils import show_popup


# ----------------------------------------------------------------------
# Локальные переводы модуля ошибок
# ----------------------------------------------------------------------
TRANSLATIONS = {
    "build_error": {
        "ru": "Ошибка выполнения",
        "de": "Ausführungsfehler",
        "en": "Execution error",
    },
    "geometry_error": {
        "ru": "Ошибка геометрических построений",
        "de": "Fehler bei geometrischen Konstruktionen",
        "en": "Geometry construction error",
    },
    "text_error": {
        "ru": "Ошибка создания текста",
        "de": "Fehler beim Erstellen des Textes",
        "en": "Text creation error",
    },
    "data_error": {
        "ru": "Ошибка входных данных",
        "de": "Fehler in den Eingabedaten",
        "en": "Input data error",
    },
}

# Регистрируем переводы при загрузке модуля
loc.register_translations(TRANSLATIONS)


# ----------------------------------------------------------------------
# Базовое исключение приложения
# ----------------------------------------------------------------------
class ATError(Exception):
    """
    Базовое исключение CAD-приложения.

    Предназначено для централизованной обработки ошибок на уровне UI.
    Содержит информацию о модуле-источнике и исходном исключении.
    """

    loc_key = "build_error"
    default_message = "Ошибка выполнения"

    def __init__(self, module: str, original: Exception | None = None):
        """
        Args:
            module: Имя модуля-источника ошибки (обычно __name__)
            original: Исходное исключение (опционально)
        """
        self.module = module
        self.original = original
        super().__init__(self._compose_message())

    def _compose_message(self) -> str:
        """
        Формирует локализованное сообщение об ошибке.
        """
        base_message = loc.get(self.loc_key, self.default_message)

        if self.original:
            return f"[{self.module}] {base_message}: {self.original}"

        return f"[{self.module}] {base_message}"

    def show(self, popup_type: str = "error", title: str | None = None):
        """
        Отображает сообщение об ошибке пользователю.
        Используется на уровне UI (точка входа, команда AutoCAD).
        """
        popup_title = title or f"{self.module} — {self.__class__.__name__}"
        show_popup(str(self), popup_type=popup_type, title=popup_title)


# ----------------------------------------------------------------------
# Специализированные исключения
# ----------------------------------------------------------------------
class GeometryError(ATError):
    """
    Ошибки геометрических построений (окружности, линии, смещения и т.п.).
    """
    loc_key = "geometry_error"
    default_message = "Ошибка геометрических построений"


class TextError(ATError):
    """
    Ошибки создания и размещения текстовых объектов.
    """
    loc_key = "text_error"
    default_message = "Ошибка создания текста"


class DataError(ATError):
    """
    Ошибки входных и пользовательских данных.
    """
    loc_key = "data_error"
    default_message = "Ошибка входных данных"


# -----------------------------
# Тестовый блок для проверки работы ошибок
# -----------------------------
if __name__ == "__main__":
    try:
        raise GeometryError("TestModule", original=ValueError("Некорректная точка"))
    except ATError as err:
        err.show(popup_type="error", title="Тест GeometryError")

    try:
        raise TextError("TestModule", original=RuntimeError("Проблема с текстом"))
    except ATError as err:
        err.show(popup_type="warning", title="Тест TextError")

    try:
        raise DataError("TestModule", original=KeyError("Нет нужного ключа"))
    except ATError as err:
        err.show(popup_type="info", title="Тест DataError")