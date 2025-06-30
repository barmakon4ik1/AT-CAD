"""
Модуль для создания диалогового окна ввода параметров колец.

Позволяет ввести номер работы и диаметры колец в табличной форме, выбрать точку вставки
и возвращает данные для построения в AutoCAD.
"""

import wx
import wx.grid
from typing import Optional, Dict
from config.at_config import BACKGROUND_COLOR, LANGUAGE
from locales.at_localization import loc, Localization
from windows.at_window_utils import BaseInputWindow, CanvasPanel, show_popup, get_standard_font, create_standard_buttons, create_window

loc.language = LANGUAGE


class RingInputWindow(BaseInputWindow):
    """
    Диалоговое окно для ввода параметров колец.
    Attributes:
        work_number_input: Поле ввода номера работы.
        diameter_grid: Таблица для ввода диаметров.
        diameter_count: Текущие количество строк в таблице.
    """

    def __init__(self, parent=None):
        """
        Инициализирует окно, наследуя базовый класс BaseInputWindow.

        Args:
            parent: Родительское окно (например, MainWindow).
        """
        super().__init__(title_key="window_title_ring", last_input_file="last_ring_input.json", window_size=(1200, 750), parent=parent)
        self.diameter_count = 1
        self.max_diameters = 10  # Ограничение высотой окна (~10 строк)
        self.setup_ui()
        self.work_number_input.SetFocus()

    def setup_ui(self) -> None:
        """
        Настраивает элементы интерфейса.
        """
        main_sizer = wx.BoxSizer(wx.HORIZONTAL)
        left_sizer = wx.BoxSizer(wx.VERTICAL)
        right_sizer = wx.BoxSizer(wx.VERTICAL)

        # Левая часть: изображение
        self.canvas = CanvasPanel(self.panel, "ring_image.png", size=(600, 400))
        left_sizer.Add(self.canvas, 1, wx.EXPAND | wx.ALL, 10)

        # Кнопки
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.buttons = create_standard_buttons(self.panel, self.on_select_point, self.on_ok, self.on_cancel)
        for button in self.buttons:
            button_sizer.Add(button, 0, wx.RIGHT, 5)
        self.adjust_button_widths()
        left_sizer.Add(button_sizer, 0, wx.ALIGN_RIGHT | wx.ALL, 10)

        # Правая часть: поля ввода
        font = get_standard_font()
        input_size = (200, -1)

        # Номер работы
        work_sizer = wx.StaticBoxSizer(wx.VERTICAL, self.panel, loc.get("work_number_label"))
        work_box = work_sizer.GetStaticBox()
        work_box.SetFont(font)

        work_input_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.work_number_input = wx.TextCtrl(work_box, value="", size=input_size)
        self.work_number_input.SetFont(font)
        work_input_sizer.AddStretchSpacer()
        work_input_sizer.Add(self.work_number_input, 0, wx.ALL, 5)
        work_sizer.Add(work_input_sizer, 0, wx.EXPAND | wx.ALL, 5)
        right_sizer.Add(work_sizer, 0, wx.EXPAND | wx.ALL, 10)

        # Таблица диаметров
        diameter_sizer = wx.StaticBoxSizer(wx.VERTICAL, self.panel, loc.get("diameter_label"))
        diameter_box = diameter_sizer.GetStaticBox()
        diameter_box.SetFont(font)

        self.diameter_grid = wx.grid.Grid(diameter_box)
        self.diameter_grid.CreateGrid(1, 1)
        self.diameter_grid.SetColLabelValue(0, loc.get("diameter_column_label"))
        self.diameter_grid.SetColSize(0, 200)
        self.diameter_grid.SetRowLabelAlignment(wx.ALIGN_RIGHT, wx.ALIGN_CENTRE)
        self.diameter_grid.SetDefaultCellFont(font)
        self.diameter_grid.SetDefaultCellAlignment(wx.ALIGN_RIGHT, wx.ALIGN_CENTRE)
        self.diameter_grid.DisableDragRowSize()
        self.diameter_grid.DisableDragColSize()
        self.diameter_grid.Bind(wx.grid.EVT_GRID_CELL_CHANGED, self.on_diameter_change)
        diameter_sizer.Add(self.diameter_grid, 1, wx.EXPAND | wx.ALL, 5)
        right_sizer.Add(diameter_sizer, 1, wx.EXPAND | wx.ALL, 10)

        main_sizer.Add(left_sizer, 1, wx.EXPAND | wx.ALL, 10)
        main_sizer.Add(right_sizer, 0, wx.EXPAND | wx.ALL, 10)
        self.panel.SetSizer(main_sizer)
        self.panel.Layout()

    def on_work_number_change(self, event: Optional[wx.Event]) -> None:
        """
        Пустой обработчик для номера работы (проверка убрана).

        Args:
            event: Событие изменения текста.
        """
        pass

    def on_diameter_change(self, event: wx.grid.GridEvent) -> None:
        """
        Проверяет введённый диаметр и добавляет новую строку, если нужно.

        Args:
            event: Событие изменения ячейки таблицы.
        """
        row = event.GetRow()
        value = self.diameter_grid.GetCellValue(row, 0).strip()
        if value:
            if value.count(',') + value.count('.') > 1:
                show_popup(loc.get("diameter_invalid_separator", row + 1), popup_type="error")
                self.diameter_grid.ClearGrid()
                self.diameter_count = 1
                while self.diameter_grid.GetNumberRows() > 1:
                    self.diameter_grid.DeleteRows(self.diameter_grid.GetNumberRows() - 1)
                return
            try:
                float(value.replace(',', '.'))
                if row == self.diameter_count - 1 and self.diameter_count < self.max_diameters:
                    self.diameter_grid.AppendRows(1)
                    self.diameter_count += 1
            except ValueError:
                show_popup(loc.get("diameter_invalid_number", row + 1), popup_type="error")
                self.diameter_grid.ClearGrid()
                self.diameter_count = 1
                while self.diameter_grid.GetNumberRows() > 1:
                    self.diameter_grid.DeleteRows(self.diameter_grid.GetNumberRows() - 1)
                return

    def on_ok(self, event: wx.Event) -> None:
        """
        Проверяет и сохраняет введённые данные, закрывает окно.

        Args:
            event: Событие нажатия кнопки OK.
        """
        if not self.insert_point or not self.model:
            show_popup(loc.get("point_not_selected_error"), popup_type="error")
            return

        work_number = self.work_number_input.GetValue()  # Может быть пустым или любым текстом
        data = {"work_number": work_number, "diameters": {}, "insert_point": self.insert_point,
                "layer_name": self.selected_layer if self.selected_layer.strip() else "0", "model": self.model}
        valid = True
        for row in range(self.diameter_grid.GetNumberRows()):
            value = self.diameter_grid.GetCellValue(row, 0).strip()
            if value:
                if value.count(',') + value.count('.') > 1:
                    show_popup(loc.get("diameter_invalid_separator", row + 1), popup_type="error")
                    valid = False
                    break
                try:
                    diameter = float(value.replace(',', '.'))
                    data["diameters"][f"diameter_{row + 1}"] = diameter
                except ValueError:
                    show_popup(loc.get("diameter_invalid_number", row + 1), popup_type="error")
                    valid = False
                    break

        if valid and data["diameters"]:
            self.result = data
            if self.GetParent():
                self.GetParent().Iconize(False)
                self.GetParent().Raise()
                self.GetParent().SetFocus()
            self.Close()
        elif not data["diameters"]:
            show_popup(loc.get("diameter_missing_error"), popup_type="error")
