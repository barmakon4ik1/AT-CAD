"""
programs/at_slotted_hole.py
Модуль для построения продолговатого отверстия в AutoCAD на основе данных из диалогового окна.
"""

from config.at_cad_init import ATCadInit
from programs.at_base import regen
from programs.at_construction import add_slotted_hole
from programs.at_input import at_get_point
from locales.at_translations import loc

# -----------------------------
# Локальные переводы модуля
# -----------------------------
TRANSLATIONS = {
    "input_point": {
        "ru": "Укажите точку вставки",
        "de": "Geben Sie den Einfügepunkt an",
        "en": "Specify the insertion point",
    }
}

loc.register_translations(TRANSLATIONS)

class SlottedHoleCommand:
    def __init__(self, data: dict):
        self.data = data

    def execute(self):
        # 1. Получаем model
        model = self.data.get("model")
        # adoc = None

        if model is None:
            acad = ATCadInit()
            adoc, model = acad.document, acad.model_space
        else:
            # если model пришёл извне — предполагаем, что и adoc есть
            adoc = self.data.get("adoc")

        # 2. Получаем точку
        point = self.data.get("input_point")

        if point is None:
            if adoc is None:
                # на случай если передали model, но не adoc
                acad = ATCadInit()
                adoc = acad.document

            point = at_get_point(
                adoc,
                as_variant=False,
                prompt=loc.get("input_point"),
            )

        if not point:
            return  # отмена пользователем

        # 3. Построение
        add_slotted_hole(
            model,
            point,
            self.data["length"],
            self.data["diameter"],
            self.data["angle"],
            self.data["direction"],
        )

        if adoc:
            regen(adoc)


def main(data: dict):
    """Точка входа для вызова из at_content_registry через run_program."""
    SlottedHoleCommand(data).execute()


if __name__ == "__main__":
    result = {
        "diameter": 14,
        "length": 10,
        "angle": 90,
        "direction": "center",
        "input_point": None
    }

    SlottedHoleCommand(result).execute()


"""
потом в основном окне сделать так:

holes = [
    {...},  # отверстие 1
    {...},  # отверстие 2
]

for hole_data in holes:
    SlottedHoleCommand(hole_data).execute()
"""


