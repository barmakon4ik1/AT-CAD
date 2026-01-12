# -*- coding: utf-8 -*-

from locales.at_translations import loc


# ============================================================================
# Translations
# ============================================================================

TRANSLATIONS = {
    "nameplate.validation.not_number": {
        "ru": "Поле '{0}' не является числом",
        "de": "Feld '{0}' ist keine Zahl",
        "en": "Field '{0}' is not a number",
    },
    "nameplate.validation.negative": {
        "ru": "Поле '{0}' не может быть меньше нуля",
        "de": "Feld '{0}' darf nicht kleiner als 0 sein",
        "en": "Field '{0}' must not be less than zero",
    },
    "nameplate.validation.a_lt_a1": {
        "ru": "Должно выполняться условие: a < a1",
        "de": "Es muss gelten: a < a1",
        "en": "Condition must hold: a < a1",
    },
    "nameplate.validation.b_lt_b1": {
        "ru": "При b > 0 должно выполняться условие: b < b1",
        "de": "Bei b > 0 muss gelten: b < b1",
        "en": "If b > 0, condition must hold: b < b1",
    },
}


loc.register_translations(TRANSLATIONS)


# ============================================================================
# Validation logic
# ============================================================================

def validate_record(record: dict) -> list[str]:
    """
    Проверка одной записи таблички.

    Возвращает список строк ошибок (локализованных).
    Пустой список означает, что запись валидна.
    """
    errors: list[str] = []

    def get_float(key: str):
        try:
            return float(record.get(key, 0))
        except (TypeError, ValueError):
            errors.append(loc.tr("nameplate.validation.not_number", key))
            return None

    a = get_float("a")
    b = get_float("b")
    a1 = get_float("a1")
    b1 = get_float("b1")
    d = get_float("d")
    r = get_float("r")
    s = get_float("s")

    values = {
        "a": a,
        "b": b,
        "a1": a1,
        "b1": b1,
        "d": d,
        "r": r,
        "s": s,
    }

    # Если есть нечисловые значения — дальнейшие проверки бессмысленны
    if any(v is None for v in values.values()):
        return errors

    # Все значения должны быть >= 0
    for key, value in values.items():
        if value < 0:
            errors.append(loc.tr("nameplate.validation.negative", key))

    # Геометрические зависимости
    if a >= a1:
        errors.append(loc.tr("nameplate.validation.a_lt_a1"))

    if b > 0 and b >= b1:
        errors.append(loc.tr("nameplate.validation.b_lt_b1"))

    return errors
