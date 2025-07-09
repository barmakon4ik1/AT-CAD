# programms/at_text_input.py
from config.at_cad_init import ATCadInit
from windows.at_gui_utils import show_popup
from config.at_config import LANGUAGE
from locales.at_localization import loc
# Установка языка для локализации
loc.language = LANGUAGE


class ATTextInput:
    def __init__(self, ptm, text, layout, high=30, angle=0, alignment=4):
        """
        Инициализация класса TextInput.
        :param ptm: Точка вставки текста (APoint)
        :param text: Строка текста
        :param layout: Название слоя (строка)
        :param high: Высота текста (число)
        :param angle: Угол поворота текста в радианах (число)
        :param alignment: Выравнивание текста (число, например, 4 для acAlignmentMiddle)
        """
        self.ptm = ptm
        self.text = text
        self.layout = layout
        self.high = high
        self.angle = angle
        self.alignment = alignment

    def at_text_input(self):
        """Создание текста в AutoCAD с заданными параметрами."""
        cad = ATCadInit()  # Используем класс CadInit
        if not cad.is_initialized():
            return None  # Если AutoCAD не инициализирован, возвращаем None

        model = cad.model
        adoc = cad.adoc
        original_layer = cad.original_layer

        if model is None or adoc is None:
            return None  # Если инициализация AutoCAD не удалась, возвращаем None

        try:
            # Проверяем, существует ли слой, и создаём его, если нет
            if self.layout not in [layer.Name for layer in adoc.Layers]:
                adoc.Layers.Add(self.layout)

            # Устанавливаем указанный слой активным
            adoc.ActiveLayer = adoc.Layers.Item(self.layout)

            # Добавляем текст с заданными параметрами
            text_obj = model.AddText(self.text, self.ptm, self.high)
            text_obj.Alignment = self.alignment  # Устанавливаем выравнивание
            text_obj.TextAlignmentPoint = self.ptm  # Точка выравнивания
            text_obj.Rotation = self.angle  # Устанавливаем угол поворота в радианах
            text_obj.Layer = self.layout  # Устанавливаем слой

            return text_obj  # Возвращаем объект текста
        except Exception as e:
            show_popup(loc.get('text_error'), popup_type="error")
            return None
        finally:
            # Восстанавливаем исходный активный слой
            try:
                adoc.ActiveLayer = original_layer
            except Exception as e:
                show_popup(loc.get('regen_error'), popup_type="error")


"""
Памятка
Выравнивание:
0 acAlignmentLeft 
1 acAlignmentCenter 
2 acAlignmentRight 
3 acAlignmentAligned 
4 acAlignmentMiddle 
5 acAlignmentFit 
6 acAlignmentTopLeft 
7 acAlignmentTopCenter 
8 acAlignmentTopRight 
9 acAlignmentMiddleLeft 
10 acAlignmentMiddleCenter 
11 acAlignmentMiddleRight 
12 acAlignmentBottomLeft 
13 acAlignmentBottomCenter 
14 acAlignmentBottomRight
"""
