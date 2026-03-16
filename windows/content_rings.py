"""
windows/content_rings.py

Панель ввода параметров колец.
"""
from pprint import pprint

import wx.grid as gridlib
import wx
from typing import Optional
from config.at_config import (
    RING_IMAGE_PATH,
    DEFAULT_SETTINGS,
)
from locales.at_translations import loc
from windows.at_fields_builder import FieldBuilder, FormBuilder, parse_float
from windows.at_window_utils import (
    CanvasPanel,
    show_popup,
    load_common_data,
    apply_styles_to_panel,
    update_status_bar_point_selected,
    BaseContentPanel,
    load_user_settings,
    get_wx_color_from_value
)

# ----------------------------------------------------------------------
# Локальные переводы
# ----------------------------------------------------------------------
TRANSLATIONS = {
    "cancel_button": {"ru": "Возврат", "de": "Zurück", "en": "Return"},
    "clear_button": {"ru": "Очистить", "de": "Löschen", "en": "Clear"},
    "ok_button": {"ru": "ОК", "de": "OK", "en": "OK"},
    "main_data": {"ru": "Основные данные", "de": "Hauptdaten", "en": "Main data"},
    "order_label": {"ru": "К-№", "de": "K-Nr.", "en": "K-no."},
    "material_label": {"ru": "Материал", "de": "Material", "en": "Material"},
    "thickness_label": {"ru": "Толщина S, мм", "de": "Dicke S, mm", "en": "Thickness S, mm"},
    "diameter": {"ru": "Диаметр D", "de": "Durchmesser D", "en": "Diameter D"},
    "values": {"ru": "Значения, мм", "de": "Werte, mm", "en": "Values, mm"},
    "no_data_error": {"ru": "Необходимо ввести хотя бы один размер", "de": "Mindestens eine Abmessung muss eingegeben werden", "en": "At least one dimension must be entered"},
    "point_selection_error": {"ru": "Ошибка выбора точки", "de": "Fehler bei der Punktauswahl", "en": "Point selection error"},
    "error": {"ru": "Ошибка", "de": "Fehler", "en": "Error"},
    "offset_x": {"ru": "Отступ X", "de": "Abstand X", "en": "Offset X"},
    "offset_y": {"ru": "Отступ Y", "de": "Abstand Y", "en": "Offset Y"},
}
loc.register_translations(TRANSLATIONS)

# ----------------------------------------------------------------------
# Factory
# ----------------------------------------------------------------------
def create_window(parent: wx.Window) -> Optional[wx.Panel]:
    try:
        return RingsContentPanel(parent)
    except Exception as e:
        show_popup(loc.get("error") + f": {str(e)}", popup_type="error")
        return None

# ----------------------------------------------------------------------
# Панель
# ----------------------------------------------------------------------
class RingsContentPanel(BaseContentPanel):
    """
    Панель ввода параметров колец.
    Левая часть: изображение колец.
    Правая часть: поля main_data + таблица диаметров + кнопки.
    """

    def __init__(self, parent: wx.Window, on_submit_callback=None):
        super().__init__(parent)
        self.diam_grid = None
        self.diameter_rows = None
        self.settings = load_user_settings()
        self.on_submit_callback = on_submit_callback
        self.parent = parent
        self.labels = {}
        self.static_boxes = {}
        self.buttons = []
        self.size_inputs = []
        self.insert_point = None
        self.setup_ui()

        self.SetBackgroundColour(
            get_wx_color_from_value(
                self.settings.get("BACKGROUND_COLOR", DEFAULT_SETTINGS["BACKGROUND_COLOR"])
            )
        )

        # UI элементы
        self.left_sizer: Optional[wx.BoxSizer] = None
        self.right_sizer: Optional[wx.BoxSizer] = None
        self.canvas: Optional[CanvasPanel] = None
        self.form = None
        self.fb = None
        self.diameter_inputs = []

        self.setup_ui()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------
    def setup_ui(self) -> None:
        self.Freeze()
        try:

            if self.GetSizer():
                self.GetSizer().Clear(True)

            # ------------------------------------------------------------
            # Главный сайзер
            # ------------------------------------------------------------
            main_sizer = wx.BoxSizer(wx.HORIZONTAL)
            self.left_sizer = wx.BoxSizer(wx.VERTICAL)
            self.right_sizer = wx.BoxSizer(wx.VERTICAL)

            # ------------------------------------------------------------
            # Левая часть — изображение
            # ------------------------------------------------------------
            image_path = str(RING_IMAGE_PATH)
            self.canvas = CanvasPanel(self, image_file=image_path, size=(750, 400))
            self.left_sizer.Add(self.canvas, 1, wx.EXPAND | wx.ALL, 10)

            # ------------------------------------------------------------
            # Данные
            # ------------------------------------------------------------
            common_data = load_common_data()
            material_options = [m["name"] for m in common_data.get("material", []) if m["name"]]
            thickness_options = common_data.get("thicknesses", [])

            # ------------------------------------------------------------
            # Форма
            # ------------------------------------------------------------
            self.form = FormBuilder(self)
            self.fb = FieldBuilder(
                parent=self,
                target_sizer=self.right_sizer,
                form=self.form
            )

            # ============================================================
            # ГРУППА: Основные данные
            # ============================================================
            main_data_sizer = self.fb.static_box("main_data")
            fb_main = FieldBuilder(parent=self, target_sizer=main_data_sizer, form=self.form)

            # Номер заказа и номер детали
            fb_main.universal_row(
                "order_label",
                [
                    {"type": "text", "name": "order", "value": "", "required": False, "default": ""},
                    {"type": "text", "name": "detail", "value": "", "required": False, "default": ""},
                ]
            )

            # Материал
            fb_main.universal_row(
                "material_label",
                [
                    {
                     "type": "combo",
                     "name": "material",
                     "choices": material_options,
                     "value": "",
                     "required": True,
                     "default": "1.4301",
                     "size": (310, -1),
                     }
                ]
            )

            # Толщина
            fb_main.universal_row(
                "thickness_label",
                [
                    {"type": "combo", "name": "thickness", "choices": thickness_options, "value": "", "required": True, "default": "3"}
                ]
            )

            # ============================================================
            # Таблица диаметров
            # ============================================================

            diam_sizer = self.fb.static_box(loc.get("values"), proportion=1)
            self.static_boxes["diameters"] = diam_sizer.GetStaticBox()

            # Создаём таблицу
            self.diam_grid = gridlib.Grid(self)
            self.diam_grid.CreateGrid(5, 3)

            # --- Локализованные заголовки ---
            self.diam_grid.SetColLabelValue(0, loc.get("diameter", "Диаметр D"))
            self.diam_grid.SetColLabelValue(1, loc.get("offset_x", "Отступ X"))
            self.diam_grid.SetColLabelValue(2, loc.get("offset_y", "Отступ Y"))

            # --- Убираем номера строк ---
            self.diam_grid.SetRowLabelSize(0)

            # --- Шрифт ---
            font_size = DEFAULT_SETTINGS["FONT_SIZE"]
            font = wx.Font(
                font_size,
                wx.FONTFAMILY_DEFAULT,
                wx.FONTSTYLE_NORMAL,
                wx.FONTWEIGHT_NORMAL
            )
            self.diam_grid.SetDefaultCellFont(font)
            self.diam_grid.SetLabelFont(font)

            # --- Высота строк под шрифт ---
            text_height = self.diam_grid.GetTextExtent("Hg")[1]  # вычисляем высоту текста
            for row in range(self.diam_grid.GetNumberRows()):
                self.diam_grid.SetRowSize(row, text_height + 8)  # +8 пикселей отступа

            # --- Ширина колонок ---
            self.diam_grid.SetColSize(0, 150)
            self.diam_grid.SetColSize(1, 120)
            self.diam_grid.SetColSize(2, 120)

            # --- Значения по умолчанию ---
            for row in range(self.diam_grid.GetNumberRows()):
                self.diam_grid.SetCellValue(row, 0, "")
                self.diam_grid.SetCellValue(row, 1, "0")
                self.diam_grid.SetCellValue(row, 2, "0")

            # --- Центрирование всех ячеек ---
            def align_row_center(arow):
                for col in range(self.diam_grid.GetNumberCols()):
                    self.diam_grid.SetCellAlignment(arow, col, wx.ALIGN_CENTER, wx.ALIGN_CENTER_VERTICAL)

            for row in range(self.diam_grid.GetNumberRows()):
                align_row_center(row)

            # --- Авто-добавление новой строки при заполнении последней ---
            def on_cell_change(evt):
                c_row = evt.GetRow()
                # проверяем, что хотя бы одна ячейка заполнена
                if c_row == self.diam_grid.GetNumberRows() - 1 and any(
                        self.diam_grid.GetCellValue(row, c).strip() != "" for c in range(3)
                ):
                    self.diam_grid.AppendRows(1)
                    new_row = self.diam_grid.GetNumberRows() - 1
                    self.diam_grid.SetCellValue(new_row, 0, "")
                    self.diam_grid.SetCellValue(new_row, 1, "0")
                    self.diam_grid.SetCellValue(new_row, 2, "0")
                    self.diam_grid.SetRowSize(new_row, text_height + 8)
                    align_row_center(new_row)
                evt.Skip()

            self.diam_grid.Bind(gridlib.EVT_GRID_CELL_CHANGED, on_cell_change)

            # --- Добавляем таблицу в sizer ---
            diam_sizer.Add(self.diam_grid, 1, wx.EXPAND | wx.ALL, 5)

            # ------------------------------------------------------------
            # Кнопки
            # ------------------------------------------------------------
            self.right_sizer.Add(self.create_button_bar(), 0, wx.ALIGN_RIGHT | wx.ALL, 5)

            # ------------------------------------------------------------
            # Финал
            # ------------------------------------------------------------
            main_sizer.Add(self.left_sizer, 1, wx.EXPAND | wx.ALL, 10)
            main_sizer.Add(self.right_sizer, 1, wx.EXPAND | wx.ALL, 10)

            self.SetSizer(main_sizer)
            apply_styles_to_panel(self)
            # self.Layout()
        finally:
            self.Layout()
            self.Thaw()


    # ------------------------------------------------------------------
    # Сервис
    # ------------------------------------------------------------------
    def get_diameter_table(self):
        """Возвращает список кортежей (D, X, Y). Если хотя бы одно значение некорректно, выдаёт исключение."""
        data = []
        for row in range(self.diam_grid.GetNumberRows()):
            d_str = self.diam_grid.GetCellValue(row, 0).strip()
            x_str = self.diam_grid.GetCellValue(row, 1).strip()
            y_str = self.diam_grid.GetCellValue(row, 2).strip()

            # Пропускаем полностью пустые строки
            if not d_str and not x_str and not y_str:
                continue

            try:
                d = parse_float(d_str)
                x = parse_float(x_str)
                y = parse_float(y_str)
            except Exception:
                raise ValueError(loc.get("error"))

            data.append((d, x, y))

        return data

    def clear_input_fields(self):
        self.form.clear()
        self.insert_point = None
        update_status_bar_point_selected(self, None)

    # ------------------------------------------------------------------
    # Кнопки-
    # ------------------------------------------------------------------
    def on_ok(self, *args, **kwargs) -> None:
        try:
            data = self.form.collect()
            if not data:
                show_popup(loc.get("no_data_error"), popup_type="error")
                return

            # --- Сбор таблицы диаметров ---
            diam_list = self.get_diameter_table()  # [(D1, X1, Y1), (D2, X2, Y2), ...]
            if not diam_list:
                show_popup(loc.get("no_data_error"), popup_type="error")
                return

            # Преобразуем в словарь {"1": [D1, X1, Y1], "2": [D2, X2, Y2], ...}
            diameters = {str(i + 1): list(v) for i, v in enumerate(diam_list)}

            data["diameters"] = diameters

            if not self.validate_input(data):
                return

            pprint(data) # Debug

            if self.on_submit_callback:
                self.on_submit_callback(data)

        except ValueError as e:
            show_popup(str(e), popup_type="error")
        except Exception as e:
            show_popup(loc.get("error") + f": {str(e)}", popup_type="error")

# ----------------------------------------------------------------------
# Тестовый запуск
# ----------------------------------------------------------------------
if __name__ == "__main__":
    import wx

    app = wx.App(False)
    frame = wx.Frame(None, title="test_rings_window", size=wx.Size(1500, 700))

    # передаём callback для вывода данных
    panel = RingsContentPanel(frame, on_submit_callback=lambda data: print("Collected data:", data))

    sizer = wx.BoxSizer(wx.VERTICAL)
    sizer.Add(panel, 1, wx.EXPAND)
    frame.SetSizer(sizer)
    frame.Layout()
    frame.Show()

    # --- тест: после запуска окна добавляем таймер для автоматического on_ok ---
    def call_on_ok():
        # заполняем несколько строк таблицы для теста
        grid = panel.diam_grid
        grid.SetCellValue(0, 0, "100")
        grid.SetCellValue(0, 1, "5")
        grid.SetCellValue(0, 2, "5")
        grid.SetCellValue(1, 0, "200")
        grid.SetCellValue(1, 1, "10")
        grid.SetCellValue(1, 2, "10")

        panel.on_ok()  # вызываем метод, который собирает данные

    wx.CallLater(100, call_on_ok)  # вызов через 100 мс после старта

    app.MainLoop()
