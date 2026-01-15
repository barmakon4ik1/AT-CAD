# Filename: shell_content_panel.py
"""
Модуль содержит панель ShellContentPanel для настройки параметров оболочки
и модальное окно BranchWindow для настройки параметров отвода в приложении AT-CAD.
"""
import wx
import wx.grid
from typing import Optional, Dict, List
from pathlib import Path

from wx.lib.buttons import GenButton

from config.at_cad_init import ATCadInit
from locales.at_translations import loc
from programs.at_construction import at_diameter
from programs.at_input import at_get_point
from windows.at_window_utils import (
    CanvasPanel, show_popup, get_standard_font, apply_styles_to_panel,
    create_standard_buttons, adjust_button_widths, BaseContentPanel,
    parse_float, load_common_data, style_label, style_textctrl,
    style_combobox, style_radiobutton, style_staticbox, update_status_bar_point_selected, style_gen_button
)
from config.at_config import SHELL_IMAGE_PATH, UNWRAPPER_PATH, DEFAULT_SETTINGS, get_setting

# -----------------------------
# Локальные переводы модуля
# -----------------------------
TRANSLATIONS = {
    "error": {"ru": "Ошибка", "de": "Fehler", "en": "Error"},
    "main_data_label": {"ru": "Основные данные", "de": "Hauptdaten", "en": "Main Data"},
    "order_label": {"ru": "К-№", "de": "Auftragsnummer", "en": "Order No."},
    "material_label": {"ru": "Материал", "de": "Material", "en": "Material"},
    "thickness_label": {"ru": "Толщина, S", "de": "Dicke, S", "en": "Thickness, S"},
    "shell_params_label": {"ru": "Параметры оболочки", "de": "Schalendaten", "en": "Shell Params"},
    "diameter_label": {"ru": "Диаметр, D", "de": "Durchmesser, D", "en": "Diameter, D"},
    "diameter_type_inner": {"ru": "Внутренний", "de": "Innen", "en": "Inner"},
    "diameter_type_middle": {"ru": "Средний", "de": "Mittel", "en": "Middle"},
    "diameter_type_outer": {"ru": "Внешний", "de": "Außen", "en": "Outer"},
    "length_label": {"ru": "Длина, L", "de": "Länge, L", "en": "Length, L"},
    "angle_label": {"ru": "Положение шва, A°", "de": "Nahtposition, A°", "en": "Seam angle, A°"},
    "clockwise_clockwise": {"ru": "По часовой", "de": "Im Uhrzeigersinn", "en": "Clockwise"},
    "clockwise_counterclockwise": {"ru": "Против часовой", "de": "Gegen Uhrzeigersinn", "en": "Counterclockwise"},
    "additional_label": {"ru": "Дополнительные условия", "de": "Zusatzbedingungen", "en": "Additional"},
    "axis_yes": {"ru": "Да", "de": "Ja", "en": "Yes"},
    "axis_no": {"ru": "Нет", "de": "Nein", "en": "No"},
    "axis_marks_label": {"ru": "Метки осей, мм", "de": "Achsenmarken, mm", "en": "Axis marks, mm"},
    "allowance_top_label": {"ru": "Припуск на сварку сверху, Lt", "de": "Schweißnahtzugabe oben, Lt", "en": "Weld Allowance Top, Lt"},
    "allowance_bottom_label": {"ru": "Припуск на сварку снизу, Lb", "de": "Schweißnahtzugabe unten, Lb", "en": "Weld Allowance Bottom, Lb"},
    "ok_button": {"ru": "ОК", "de": "OK", "en": "OK"},
    "clear_button": {"ru": "Очистить", "de": "Zurücksetzen", "en": "Clear"},
    "cancel_button": {"ru": "Возврат", "de": "Zurück", "en": "Return"},
    "branch_button": {"ru": "Наличие отвода", "de": "Abzweig", "en": "Branch"},
    "branch_window_title": {"ru": "Параметры отвода", "de": "Abzweigparameter", "en": "Branch Parameters"},
    "branch_params_label": {"ru": "Параметры отвода", "de": "Abzweigparameter", "en": "Branch Parameters"},
    "name_label": {"ru": "Имя", "de": "Name", "en": "Name"},
    "diameter_branch_label": {"ru": "d", "de": "d", "en": "d"},
    "offset_axial_label": {"ru": "L", "de": "L", "en": "L"},
    "height_label": {"ru": "H", "de": "H", "en": "H"},
    "axial_shift_label": {"ru": "B", "de": "B", "en": "B"},
    "thickness_branch_label": {"ru": "S", "de": "S", "en": "S"},
    "angle_branch_label": {"ru": "A°", "de": "A°", "en": "A°"},
    "contact_type_label": {"ru": "Тип", "de": "Typ", "en": "Type"},
    "unroll_branch_label": {"ru": "Развернуть?", "de": "Abwickeln?", "en": "Unwind?"},
    "flange_label": {"ru": "Фланец?", "de": "Flansch?", "en": "Flange?"},
    "weld_allowance_label": {"ru": "Припуск", "de": "Schw.zug.", "en": "W.allow."},
    "yes": {"ru": "Да", "de": "Ja", "en": "Yes"},
    "no": {"ru": "Нет", "de": "Nein", "en": "No"},
    "error_invalid_diameter": {"ru": "Диаметр отвода (d) обязателен и должен быть больше 0",
                               "de": "Durchmesser (d) ist erforderlich und muss größer als 0 sein",
                               "en": "Branch diameter (d) is required and must be greater than 0"},
    "error_invalid_offset": {"ru": "Расстояние (L) обязательно и не может быть 0",
                             "de": "Abstand (L) ist erforderlich und darf nicht 0 sein",
                             "en": "Offset (L) is required and cannot be 0"},
    "error_invalid_angle": {"ru": "Угол (A) обязателен при наличии диаметра",
                            "de": "Winkel (A) ist erforderlich, wenn Durchmesser angegeben ist",
                            "en": "Angle (A) is required when diameter is specified"},
    "mode_label": {"ru": "Режим построения", "de": "Konstruktionsmodus", "en": "Build Mode"},
    "mode_bulge": {"ru": "Дуги", "de": "Bogen", "en": "Bulge"},
    "mode_polyline": {"ru": "Полилиния", "de": "Polylinie", "en": "Polyline"},
    "mode_spline": {"ru": "Сплайн", "de": "Spline", "en": "Spline"},
    "confirm_cancel_message": {
        "ru": "Вы действительно хотите отменить? Данные не сохранятся!",
        "en": "Are you sure you want to cancel? Unsaved data will be lost!",
        "de": "Möchten Sie wirklich abbrechen? Nicht gespeicherte Daten gehen verloren!"
    },
    "steps_label": {"ru": "Точность (точек)", "de": "Genauigkeit (Punkte)", "en": "Steps (points)"}
}

loc.register_translations(TRANSLATIONS)

# Значения по умолчанию
default_allowances = ["0", "1", "2", "3", "4", "5", "10", "20"]
default_axis_marks = ["0", "10", "20"]
default_weld_allowance = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]
default_modes = ["mode_bulge", "mode_polyline", "mode_spline"]
default_steps = ["180", "360", "720"]  # Значения для steps по умолчанию

# Рекомендуемые наборы значений steps по режимам
STEPS_OPTIONS = {
    "bulge": ["90", "180", "360"],          # Баланс точности/производительности
    "polyline": ["360", "720", "1080"],     # Полилиния — больше точек
    "spline": ["90", "180", "360"],         # Сплайн — умеренно
}


# Фабричная функция для создания панели
def create_window(parent: wx.Window) -> wx.Panel:
    """
    Фабричная функция для создания панели ShellContentPanel.
Args:
    parent (wx.Window): Родительская панель (обычно content_panel в ATMainWindow).
Returns:
    wx.Panel: Инициализированный экземпляр ShellContentPanel.
"""
    return ShellContentPanel(parent)

class BranchWindow(wx.Dialog):
    """
    Модальное окно для настройки параметров отвода.
    Содержит изображение слева, три стандартные кнопки (ОК, Очистить, Возврат) и таблицу справа для ввода параметров.
    """
    def __init__(self, parent):
        """
        Инициализация окна BranchWindow.

        Args:
            parent: Родительское окно (обычно ShellContentPanel).
        """
        super().__init__(
            parent,
            title=loc.get("branch_window_title", "Параметры отвода"),
            size=(1600, 600),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )

        self.SetMinSize((1600, 600))
        self.SetBackgroundColour(wx.Colour(get_setting("BACKGROUND_COLOR")))
        self.parent = parent
        self.labels = {}
        self.static_boxes = {}
        self.buttons = []
        self.table = None
        self.setup_ui()
        self.CenterOnParent()
        self.Bind(wx.EVT_CLOSE, self.on_cancel)

    def setup_ui(self):
        """
        Настраивает пользовательский интерфейс окна BranchWindow.
        Левая панель (рисунок + кнопки) создаётся внутри left_panel_container,
        правая (таблица и контролы) — внутри right_panel_container.
        """
        main_sizer = wx.BoxSizer(wx.HORIZONTAL)

        # --- Контейнеры — создаём их СРАЗУ, чтобы дети имели правильный parent ---
        left_panel_container = wx.Panel(self)
        left_panel_sizer = wx.BoxSizer(wx.VERTICAL)
        left_panel_container.SetSizer(left_panel_sizer)
        left_panel_container.SetMinSize((400, -1))
        left_panel_container.SetMaxSize((400, -1))  # фиксированная ширина для левой панели

        right_panel_container = wx.Panel(self)
        right_panel_sizer = wx.BoxSizer(wx.VERTICAL)
        right_panel_container.SetSizer(right_panel_sizer)

        # ------------------ Левая панель (canvas + кнопки + branch_button) ------------------
        image_path = str(UNWRAPPER_PATH)
        # CanvasPanel создаём как дочерний элемент left_panel_container
        self.canvas = CanvasPanel(left_panel_container, image_path, size=(400, 300))
        left_panel_sizer.Add(self.canvas, 1, wx.EXPAND | wx.ALL, 10)

        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        # Создаём кнопки тоже с родителем left_panel_container
        self.buttons = create_standard_buttons(left_panel_container, self.on_ok, self.on_cancel, self.on_clear)
        for button in self.buttons:
            button_sizer.Add(button, 0, wx.RIGHT, 5)
        adjust_button_widths(self.buttons)
        left_panel_sizer.Add(button_sizer, 0, wx.ALIGN_RIGHT | wx.ALL, 5)

        # ------------------ Правая панель (статик-бокс + таблица + контролы) ------------------
        branch_box = wx.StaticBox(right_panel_container, label=loc.get("branch_params_label", "Параметры отвода"))
        style_staticbox(branch_box)
        self.static_boxes["branch_params"] = branch_box
        branch_sizer = wx.StaticBoxSizer(branch_box, wx.VERTICAL)

        # Таблица с параметрами отвода (создаём внутри branch_box)
        self.table = wx.grid.Grid(branch_box)
        self.table.CreateGrid(5, 11)  # Начально 5 строк, 11 столбцов

        # Установка шрифта для заголовков столбцов
        label_font = wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        self.table.SetLabelFont(label_font)

        # Заголовки столбцов
        self.table.SetColLabelValue(0, loc.get("name_label", "Имя"))
        self.table.SetColLabelValue(1, loc.get("diameter_branch_label", "d"))
        self.table.SetColLabelValue(2, loc.get("offset_axial_label", "L"))
        self.table.SetColLabelValue(3, loc.get("height_label", "H"))
        self.table.SetColLabelValue(4, loc.get("axial_shift_label", "B"))
        self.table.SetColLabelValue(5, loc.get("thickness_branch_label", "S"))
        self.table.SetColLabelValue(6, loc.get("angle_branch_label", "A°"))
        self.table.SetColLabelValue(7, loc.get("contact_type_label", "Тип"))
        self.table.SetColLabelValue(8, loc.get("unroll_branch_label", "развернуть"))
        self.table.SetColLabelValue(9, loc.get("flange_label", "Фланец"))
        self.table.SetColLabelValue(10, loc.get("weld_allowance_label", "Припуск"))

        self.table.SetColLabelSize(40)
        # Начальные размеры столбцов — небольшое значение, потом мы подгоним
        initial_col_width = 60
        for c in range(self.table.GetNumberCols()):
            self.table.SetColSize(c, initial_col_width)

        # Начальные значения строк (ИЗМЕНЕНО: вместо loc.get("no") — "0" для False)
        for row in range(self.table.GetNumberRows()):
            self.table.SetRowLabelValue(row, str(row + 1))
            self.table.SetCellValue(row, 3, "0")
            self.table.SetCellValue(row, 4, "0")
            self.table.SetCellValue(row, 5, "0")
            self.table.SetCellValue(row, 7, "A")
            self.table.SetCellValue(row, 8, "")
            self.table.SetCellValue(row, 9, "")
            self.table.SetCellValue(row, 10, "3")

        # Редакторы для choice-полей (ИЗМЕНЕНО: для 8 и 9 — BoolEditor вместо ChoiceEditor)
        contact_types = ["A", "D", "M", "T"]
        # unroll_choices = ...  # ← УДАЛЕНО: больше не нужно
        for row in range(self.table.GetNumberRows()):
            self.table.SetCellEditor(row, 7, wx.grid.GridCellChoiceEditor(contact_types, allowOthers=False))
            self.table.SetCellEditor(row, 8, wx.grid.GridCellBoolEditor())  # ← ИЗМЕНЕНО: Bool для "развернуть"
            self.table.SetCellEditor(row, 9, wx.grid.GridCellBoolEditor())  # ← ИЗМЕНЕНО: Bool для "Фланец?"
            self.table.SetCellEditor(row, 10, wx.grid.GridCellChoiceEditor(default_weld_allowance, allowOthers=True))

        # ДОБАВИТЬ: Рендереры для визуализации галочки (только для колонок 8 и 9, для всех строк)
        for row in range(self.table.GetNumberRows()):
            self.table.SetCellRenderer(row, 8, wx.grid.GridCellBoolRenderer())  # ← ДОБАВИТЬ: Галочка для "развернуть"
            self.table.SetCellRenderer(row, 9, wx.grid.GridCellBoolRenderer())  # ← ДОБАВИТЬ: Галочка для "Фланец?"

        # ДОБАВИТЬ: Центрирование чекбокса в ячейках колонок 8 и 9 (для всех строк)
        for row in range(self.table.GetNumberRows()):
            self.table.SetCellAlignment(row, 8, wx.ALIGN_CENTER,
                                        wx.ALIGN_CENTER)  # ← ДОБАВИТЬ: Горизонтально/вертикально по центру для "развернуть"
            self.table.SetCellAlignment(row, 9, wx.ALIGN_CENTER, wx.ALIGN_CENTER)  # ← ДОБАВИТЬ: Для "Фланец?"

        self.table.SetDefaultCellAlignment(wx.ALIGN_CENTRE, wx.ALIGN_CENTRE)
        self.table.EnableDragRowSize(False)

        # Добавляем таблицу в branch_sizer
        branch_sizer.Add(self.table, 1, wx.EXPAND | wx.ALL, 5)

        # --- Строка с режимом, точностью и кнопкой добавления ---
        field_size = (150, -1)
        row_controls = wx.BoxSizer(wx.HORIZONTAL)

        self.labels["mode"] = wx.StaticText(branch_box, label=loc.get("mode_label", "Режим построения"))
        style_label(self.labels["mode"])
        self.mode_combo = wx.ComboBox(
            branch_box,
            choices=[loc.get(m, m) for m in default_modes],
            value=loc.get("mode_polyline", "Полилиния"),
            style=wx.CB_READONLY,
            size=field_size
        )
        style_combobox(self.mode_combo)
        self.mode_combo.Bind(wx.EVT_COMBOBOX, self.on_mode_change)

        self.labels["steps"] = wx.StaticText(branch_box, label=loc.get("steps_label", "Точность (точек)"))
        style_label(self.labels["steps"])
        self.steps_combo = wx.ComboBox(
            branch_box,
            choices=STEPS_OPTIONS["polyline"],
            value="360",
            style=wx.CB_DROPDOWN,
            size=field_size
        )
        style_combobox(self.steps_combo)

        add_row_button = wx.Button(branch_box, label=loc.get("add_row", "Добавить строку"))
        add_row_button.SetFont(get_standard_font())
        add_row_button.Bind(wx.EVT_BUTTON, self.on_add_row)

        row_controls.Add(self.labels["mode"], 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        row_controls.Add(self.mode_combo, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 20)
        row_controls.Add(self.labels["steps"], 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        row_controls.Add(self.steps_combo, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 20)
        row_controls.AddStretchSpacer()
        row_controls.Add(add_row_button, 0, wx.ALIGN_CENTER_VERTICAL)

        branch_sizer.Add(row_controls, 0, wx.EXPAND | wx.ALL, 5)

        # Добавляем branch_sizer в правый контейнер
        right_panel_sizer.Add(branch_sizer, 1, wx.EXPAND | wx.ALL, 10)

        # Добавляем контейнеры в главный сайзер: левая фиксированная, правая растягивается
        main_sizer.Add(left_panel_container, 0, wx.EXPAND | wx.ALL, 10)
        main_sizer.Add(right_panel_container, 1, wx.EXPAND | wx.ALL, 10)

        self.SetSizer(main_sizer)

        # --- Подгонка ширины столбцов: минимум — 10 цифр ---
        dc = wx.ClientDC(self.table)
        dc.SetFont(self.table.GetFont())
        min_char_width = dc.GetTextExtent("0" * 10)[0] + 10  # запас

        # Сначала подгоним по заголовкам/контенту, затем применим минимум
        try:
            self.table.AutoSizeColumns()
        except Exception:
            pass

        for col in range(self.table.GetNumberCols()):
            if self.table.GetColSize(col) < min_char_width:
                self.table.SetColSize(col, min_char_width)

        current_width, current_height = self.GetSize()
        self.SetMinSize((current_width, current_height))
        self.SetMaxSize((-1, current_height))

        # Привязка обработчика изменения ячейки (если on_cell_changed реализован)
        self.table.Bind(wx.grid.EVT_GRID_CELL_CHANGED, self.on_cell_changed)

        apply_styles_to_panel(self)
        self.Layout()

        # Автоматическое перераспределение ширины столбцов при изменении окна
        self.Bind(wx.EVT_SIZE, self.on_resize)

    def on_mode_change(self, event):
        """Меняет список значений steps при смене режима построения."""
        mode_map = {
            loc.get("mode_bulge", "Bulge"): "bulge",
            loc.get("mode_polyline", "Polyline"): "polyline",
            loc.get("mode_spline", "Spline"): "spline",
        }
        selected_mode = mode_map.get(self.mode_combo.GetValue(), "polyline")
        options = STEPS_OPTIONS.get(selected_mode, STEPS_OPTIONS["polyline"])
        self.steps_combo.SetItems(options)
        self.steps_combo.SetValue(options[0])

    def on_add_row(self, event: wx.Event):
        """
        Добавляет новую строку в таблицу.

        Args:
            event (wx.Event): Событие нажатия кнопки "Добавить строку".
        """
        self.table.AppendRows(1)
        row = self.table.GetNumberRows() - 1
        self.table.SetRowLabelValue(row, str(row + 1))
        self.table.SetCellValue(row, 3, "0")  # H
        self.table.SetCellValue(row, 4, "0")  # B
        self.table.SetCellValue(row, 5, "0")  # S
        self.table.SetCellValue(row, 7, "A")  # Тип контакта
        self.table.SetCellValue(row, 8, "")
        self.table.SetCellValue(row, 9, "")
        self.table.SetCellValue(row, 10, "3")  # Припуск на сварку

        # Установка редакторов для новой строки (ИЗМЕНЕНО: BoolEditor)
        contact_types = ["A", "D", "M", "T"]
        # unroll_choices = ...  # ← УДАЛЕНО
        self.table.SetCellEditor(row, 7, wx.grid.GridCellChoiceEditor(contact_types, allowOthers=False))
        self.table.SetCellEditor(row, 8, wx.grid.GridCellBoolEditor())  # ← ИЗМЕНЕНО
        self.table.SetCellEditor(row, 9, wx.grid.GridCellBoolEditor())  # ← ИЗМЕНЕНО
        self.table.SetCellEditor(row, 10, wx.grid.GridCellChoiceEditor(default_weld_allowance, allowOthers=True))

        # ДОБАВИТЬ: Рендерер для новой строки
        self.table.SetCellRenderer(row, 8, wx.grid.GridCellBoolRenderer())  # ← ДОБАВИТЬ
        self.table.SetCellRenderer(row, 9, wx.grid.GridCellBoolRenderer())  # ← ДОБАВИТЬ

        # ДОБАВИТЬ: Центрирование для новой строки
        self.table.SetCellAlignment(row, 8, wx.ALIGN_CENTER, wx.ALIGN_CENTER)  # ← ДОБАВИТЬ
        self.table.SetCellAlignment(row, 9, wx.ALIGN_CENTER, wx.ALIGN_CENTER)  # ← ДОБАВИТЬ

        # Установка фиксированной ширины столбцов для согласованности
        self.table.SetColSize(0, 150)  # Наименование
        self.table.SetColSize(1, 100)  # Диаметр, d
        self.table.SetColSize(2, 100)  # Расстояние, L
        self.table.SetColSize(3, 100)  # Высота, H
        self.table.SetColSize(4, 100)  # Смещение, B
        self.table.SetColSize(5, 100)  # Толщина, S
        self.table.SetColSize(6, 100)  # Угол, A°
        self.table.SetColSize(7, 100)  # Тип контакта
        self.table.SetColSize(8, 120)  # Развертка отвода
        self.table.SetColSize(9, 120)  # Наличие фланца
        self.table.SetColSize(10, 120)  # Припуск на сварку

        self.Layout()

    def on_cell_changed(self, event):
        """Автоматически подгоняет ширину столбца под содержимое (увеличивает и уменьшает)."""
        col = event.GetCol()
        row = event.GetRow()
        value = self.table.GetCellValue(row, col).strip()

        # Подготовим DC (для измерения ширины текста)
        dc = wx.ClientDC(self.table)
        dc.SetFont(self.table.GetFont())

        # Минимальная ширина — чтобы помещалось хотя бы 10 символов
        min_width = dc.GetTextExtent("0000000000")[0] + 10
        # Текущая ширина
        current_width = self.table.GetColSize(col)
        # Требуемая ширина по тексту
        text_width = dc.GetTextExtent(value)[0] + 20  # +20 на отступы

        # Если текст длиннее текущего столбца — расширяем
        if text_width > current_width:
            self.table.SetColSize(col, text_width)
        # Если текст стал короче — аккуратно сужаем, но не меньше минимума
        elif text_width + 40 < current_width and current_width > min_width:
            new_width = max(min_width, text_width + 20)
            self.table.SetColSize(col, new_width)

        event.Skip()

    def on_resize(self, event):
        """Обработчик изменения размера окна — вызывает перераспределение столбцов."""
        event.Skip()
        wx.CallAfter(self.adjust_table_columns)

    def adjust_table_columns(self):
        """Равномерно распределяет ширину всех столбцов, без горизонтального скролла и скрытия последнего."""
        if not hasattr(self, "table") or not self.table:
            return

        total_width = max(1, self.table.GetClientSize().GetWidth())
        cols = self.table.GetNumberCols()
        if cols == 0 or total_width <= 1:
            return

        scale = self.GetContentScaleFactor() if hasattr(self, "GetContentScaleFactor") else 1
        # wx.Grid добавляет внутренние отступы справа, компенсируем их
        safety_margin = int(80 * scale)  # ← ключевой момент
        available_width = max(1, total_width - safety_margin)

        min_col_width = 80
        even_width = max(min_col_width, available_width // cols)

        # Ограничим, чтобы не вылезли за пределы
        if even_width * cols > available_width:
            even_width = max(40, available_width // cols)

        # Устанавливаем ширину для всех столбцов
        for col in range(cols):
            self.table.SetColSize(col, even_width)

        # Небольшая корректировка последнего столбца (чтобы занять остаток без выхода за границу)
        used_width = even_width * cols
        diff = available_width - used_width
        if abs(diff) > 0:
            last = cols - 1
            new_last = max(40, self.table.GetColSize(last) + diff - 2)
            self.table.SetColSize(last, new_last)

        self.table.ForceRefresh()

    def collect_input_data(self) -> Optional[List[Dict]]:
        """
        Собирает данные из таблицы параметров отвода.

        Returns:
            Optional[List[Dict]]: Список словарей с данными отводов или None, если данные невалидны или таблица пуста.
        """
        cutouts = []
        for row in range(self.table.GetNumberRows()):
            diameter = parse_float(self.table.GetCellValue(row, 1))
            if diameter is None or diameter <= 0:
                continue  # Пропускаем строки с невалидным диаметром

            offset_axial = parse_float(self.table.GetCellValue(row, 2))
            if offset_axial is None or offset_axial == 0:
                show_popup(loc.get("error_invalid_offset", "Расстояние (L) обязательно и не может быть 0"), popup_type="error")
                return None

            angle = parse_float(self.table.GetCellValue(row, 6))
            if angle is None:
                show_popup(loc.get("error_invalid_angle", "Угол (A) обязателен при наличии диаметра"), popup_type="error")
                return None

            weld_allowance_bottom = parse_float(self.parent.allowance_bottom.GetValue()) or 0

            cutout = {
                "angle_deg": angle,
                "offset_axial": offset_axial + weld_allowance_bottom,
                "axial_shift": parse_float(self.table.GetCellValue(row, 4)) or 0.0,
                "params": {
                    "diameter": diameter,
                    "contact_mode": self.table.GetCellValue(row, 7).upper(),  # Тип контакта (A, D, M, T)
                    "text": self.table.GetCellValue(row, 0),
                    "steps": 180,  # Фиксированное значение
                    "layer_name": "0",  # Жестко заданный слой
                    "thickness": parse_float(self.table.GetCellValue(row, 5)) or 0.0,  # Толщина отвода
                    "height": parse_float(self.table.GetCellValue(row, 3)) or 0.0,  # Высота отвода
                    "unroll_branch": self.table.GetCellValue(row, 8) == "1", # "" == "1" → False; "1" == "1" → True
                    "flange_present": self.table.GetCellValue(row, 9) == "1", # "" == "1" → False; "1" == "1" → True
                    "weld_allowance": parse_float(self.table.GetCellValue(row, 10)) or 3.0,  # Припуск на сварку
                }
            }
            cutouts.append(cutout)

        return cutouts if cutouts else None

    def clear_input_fields(self):
        """
        Очищает поля таблицы параметров отвода, сбрасывая их на значения по умолчанию.
        """
        for row in range(self.table.GetNumberRows()):
            self.table.SetCellValue(row, 0, "")  # Name
            self.table.SetCellValue(row, 1, "")  # d
            self.table.SetCellValue(row, 2, "")  # L
            self.table.SetCellValue(row, 3, "0")  # H
            self.table.SetCellValue(row, 4, "0")  # B
            self.table.SetCellValue(row, 5, "0")  # S
            self.table.SetCellValue(row, 6, "")  # A
            self.table.SetCellValue(row, 7, "A")  # Тип контакта
            self.table.SetCellValue(row, 8, "")   # Развертка
            self.table.SetCellValue(row, 9, "")  # Фланец
            self.table.SetCellValue(row, 10, "3")  # Припуск на сварку
            self.table.SetCellAlignment(row, 8, wx.ALIGN_CENTER, wx.ALIGN_CENTER)
            self.table.SetCellAlignment(row, 9, wx.ALIGN_CENTER, wx.ALIGN_CENTER)

    def on_ok(self, event: wx.Event):
        """
        Обрабатывает нажатие кнопки "ОК".
        Собирает данные из таблицы и закрывает окно с результатом wx.ID_OK.

        Args:
            event (wx.Event): Событие нажатия кнопки.
        """
        data = self.collect_input_data()
        if data is None and any(self.table.GetCellValue(row, 1) for row in range(self.table.GetNumberRows())):
            show_popup(loc.get("error_invalid_diameter", "Диаметр отвода (d) обязателен и должен быть больше 0"), popup_type="error")
            return
        self.parent.branch_data = data  # Сохраняем данные в родительской панели
        self.EndModal(wx.ID_OK)

    def on_clear(self, event: wx.Event):
        """
        Обрабатывает нажатие кнопки "Очистить".
        Сбрасывает значения полей таблицы.

        Args:
            event (wx.Event): Событие нажатия кнопки.
        """
        self.clear_input_fields()

    def on_cancel(self, event: wx.Event):
        """
        Обрабатывает нажатие кнопки "Возврат" или закрытие окна.
        Перед закрытием спрашивает подтверждение, чтобы избежать потери несохранённых данных.
        """
        confirm_message = loc.get(
            "confirm_cancel_message",
            "Вы действительно хотите отменить? Данные не сохранятся!"
        )
        confirm_title = loc.get("cancel_button", "Отмена")

        dlg = wx.MessageDialog(
            self,
            confirm_message,
            confirm_title,
            style=wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING
        )

        try:
            result = dlg.ShowModal()
        finally:
            dlg.Destroy()

        # Разрешаем закрытие только если пользователь подтвердил
        if result in (wx.ID_YES, wx.ID_OK):
            self.EndModal(wx.ID_CANCEL)
        else:
            # Пользователь отказался — просто остаёмся в окне
            return


class ShellContentPanel(BaseContentPanel):
    """
    Панель для настройки параметров оболочки в приложении AT-CAD.
    Наследуется от BaseContentPanel, предоставляя интерфейс для ввода данных об оболочке,
    таких как заказ, материал, размеры, припуски и дополнительные параметры.
    Данные собираются в словарь и передаются через callback в другую программу.
    """
    def __init__(self, parent, callback=None):
        """
        Инициализация панели ShellContentPanel.

        Аргументы:
            parent: Родительское окно или панель wxPython.
            callback: Опциональная функция обратного вызова для передачи собранных данных.
        """
        super().__init__(parent)
        self.branch_button = None
        self.on_submit_callback = callback
        self.parent = parent
        self.labels = {}
        self.static_boxes = {}
        self.buttons = []
        self.insert_point = None
        self.branch_data = None  # Для хранения данных отводов из BranchWindow

        # Виджеты
        self.order_input: Optional[wx.TextCtrl] = None
        self.detail_input: Optional[wx.TextCtrl] = None
        self.material_combo: Optional[wx.ComboBox] = None
        self.thickness_combo: Optional[wx.ComboBox] = None
        self.diameter_input: Optional[wx.TextCtrl] = None
        self.diameter_type_choice: Optional[wx.Choice] = None
        self.length_input: Optional[wx.TextCtrl] = None
        self.angle_input: Optional[wx.TextCtrl] = None
        self.clockwise_choice: Optional[wx.Choice] = None
        self.axis_choice: Optional[wx.Choice] = None
        self.axis_marks_combo: Optional[wx.ComboBox] = None
        self.allowance_top: Optional[wx.ComboBox] = None
        self.allowance_bottom: Optional[wx.ComboBox] = None

        self.setup_ui()
        self.order_input.SetFocus()
        self.Bind(wx.EVT_BUTTON, self.on_branch, self.branch_button)

    def setup_ui(self):
        """
        Настраивает пользовательский интерфейс панели ShellContentPanel.
        Создает левый сайзер с изображением и кнопками и правый сайзер с полями ввода.
        Все поля ввода (TextCtrl, ComboBox, Choice) имеют одинаковую ширину и выровнены по правому краю
        с использованием wx.StretchSpacer() между метками и полями. Стилизация выполняется через функции из at_window_utils.
        """
        if self.GetSizer():
            self.GetSizer().Clear(True)
        main_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.left_sizer = wx.BoxSizer(wx.VERTICAL)

        # Левый блок: изображение и кнопки
        image_path = str(SHELL_IMAGE_PATH)
        self.canvas = CanvasPanel(self, image_file=image_path, size=(600, 400))
        self.left_sizer.Add(self.canvas, 1, wx.EXPAND | wx.ALL, 10)


        # self.branch_button = wx.Button(self, label=loc.get("branch_button", "Наличие отвода"))
        # self.branch_button.SetBackgroundColour(wx.Colour(0, 102, 204))
        # self.branch_button.SetForegroundColour(wx.Colour(255, 255, 255))
        # self.branch_button.SetFont(get_standard_font())
        self.branch_button = GenButton(self, label=loc.get("branch_button", "Наличие отвода"), size=(240, 30))
        style_gen_button(self.branch_button, "#3498db", font_size=14, button_height=30)
        self.left_sizer.Add(self.branch_button, 0, wx.ALIGN_RIGHT | wx.ALL, 5)

        # Правый блок
        self.right_sizer = wx.BoxSizer(wx.VERTICAL)
        font = get_standard_font()
        font_big = get_standard_font().Bold()
        field_size = (150, -1)  # Единая ширина для всех полей ввода

        # --- Основные данные ---
        main_data_box = wx.StaticBox(self, label=loc.get("main_data_label", "Основные данные"))
        style_staticbox(main_data_box)
        self.static_boxes["main_data"] = main_data_box
        main_data_sizer = wx.StaticBoxSizer(main_data_box, wx.VERTICAL)

        # Первая строка: К-№ и Деталь
        row1 = wx.BoxSizer(wx.HORIZONTAL)
        self.labels["order"] = wx.StaticText(main_data_box, label=loc.get("order_label", "К-№"))
        style_label(self.labels["order"])
        self.order_input = wx.TextCtrl(main_data_box, value="", size=field_size)
        style_textctrl(self.order_input)
        self.detail_input = wx.TextCtrl(main_data_box, value="", size=field_size)
        style_textctrl(self.detail_input)
        row1.Add(self.labels["order"], 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        row1.AddStretchSpacer()
        row1.Add(self.order_input, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        row1.Add(self.detail_input, 0, wx.ALIGN_CENTER_VERTICAL)
        main_data_sizer.Add(row1, 0, wx.EXPAND | wx.ALL, 5)

        # Загрузка общих данных
        common_data = load_common_data()
        material_options = [mat["name"] for mat in common_data.get("material", []) if mat.get("name")]
        thickness_options = common_data.get("thicknesses", [])
        default_thickness = "4" if "4" in thickness_options or "4.0" in thickness_options else (thickness_options[0] if thickness_options else "")

        # Вторая строка: Материал
        row2 = wx.BoxSizer(wx.HORIZONTAL)
        self.labels["material"] = wx.StaticText(main_data_box, label=loc.get("material_label", "Материал"))
        style_label(self.labels["material"])
        self.material_combo = wx.ComboBox(
            main_data_box,
            choices=material_options,
            value=material_options[0] if material_options else "",
            style=wx.CB_DROPDOWN,
            size=field_size
        )
        style_combobox(self.material_combo)
        row2.Add(self.labels["material"], 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        row2.AddStretchSpacer()
        row2.Add(self.material_combo, 0, wx.ALIGN_CENTER_VERTICAL)
        main_data_sizer.Add(row2, 0, wx.EXPAND | wx.ALL, 5)

        # Третья строка: Толщина
        row3 = wx.BoxSizer(wx.HORIZONTAL)
        self.labels["thickness"] = wx.StaticText(main_data_box, label=loc.get("thickness_label", "Толщина, S"))
        style_label(self.labels["thickness"])
        self.thickness_combo = wx.ComboBox(
            main_data_box,
            choices=thickness_options,
            value=default_thickness,
            style=wx.CB_DROPDOWN,
            size=field_size
        )
        style_combobox(self.thickness_combo)
        row3.Add(self.labels["thickness"], 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        row3.AddStretchSpacer()
        row3.Add(self.thickness_combo, 0, wx.ALIGN_CENTER_VERTICAL)
        main_data_sizer.Add(row3, 0, wx.EXPAND | wx.ALL, 5)

        self.right_sizer.Add(main_data_sizer, 0, wx.EXPAND | wx.ALL, 10)

        # --- Параметры оболочки ---
        shell_box = wx.StaticBox(self, label=loc.get("shell_params_label", "Параметры оболочки"))
        style_staticbox(shell_box)
        self.static_boxes["shell_params"] = shell_box
        shell_sizer = wx.StaticBoxSizer(shell_box, wx.VERTICAL)

        # Диаметр
        row4 = wx.BoxSizer(wx.HORIZONTAL)
        self.labels["diameter"] = wx.StaticText(shell_box, label=loc.get("diameter_label", "Диаметр, D"))
        style_label(self.labels["diameter"])
        self.diameter_input = wx.TextCtrl(shell_box, value="", size=field_size)
        style_textctrl(self.diameter_input)
        self.diameter_type_choice = wx.Choice(
            shell_box,
            choices=[
                loc.get("diameter_type_inner", "Внутренний"),
                loc.get("diameter_type_middle", "Средний"),
                loc.get("diameter_type_outer", "Внешний")
            ],
            size=field_size
        )
        self.diameter_type_choice.SetFont(font)
        self.diameter_type_choice.SetSelection(2)  # Внешний по умолчанию
        row4.Add(self.labels["diameter"], 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        row4.AddStretchSpacer()
        row4.Add(self.diameter_input, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        row4.Add(self.diameter_type_choice, 0, wx.ALIGN_CENTER_VERTICAL)
        shell_sizer.Add(row4, 0, wx.EXPAND | wx.ALL, 5)

        # Длина
        row5 = wx.BoxSizer(wx.HORIZONTAL)
        self.labels["length"] = wx.StaticText(shell_box, label=loc.get("length_label", "Длина, L"))
        style_label(self.labels["length"])
        self.length_input = wx.TextCtrl(shell_box, value="", size=field_size)
        style_textctrl(self.length_input)
        row5.Add(self.labels["length"], 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        row5.AddStretchSpacer()
        row5.Add(self.length_input, 0, wx.ALIGN_CENTER_VERTICAL)
        shell_sizer.Add(row5, 0, wx.EXPAND | wx.ALL, 5)

        # Угол шва
        row6 = wx.BoxSizer(wx.HORIZONTAL)
        self.labels["angle"] = wx.StaticText(shell_box, label=loc.get("angle_label", "Положение шва (°)"))
        style_label(self.labels["angle"])
        self.angle_input = wx.TextCtrl(shell_box, value="", size=field_size)
        style_textctrl(self.angle_input)
        row6.Add(self.labels["angle"], 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        row6.AddStretchSpacer()
        row6.Add(self.angle_input, 0, wx.ALIGN_CENTER_VERTICAL)
        shell_sizer.Add(row6, 0, wx.EXPAND | wx.ALL, 5)

        # Развертка
        clockwise_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.labels["clockwise"] = wx.StaticText(shell_box, label=loc.get("clockwise_label", "Развертка"))
        style_label(self.labels["clockwise"])
        self.clockwise_choice = wx.Choice(
            shell_box,
            choices=[
                loc.get("clockwise_clockwise", "По часовой"),
                loc.get("clockwise_counterclockwise", "Против часовой")
            ],
            size=field_size
        )
        self.clockwise_choice.SetFont(font)
        self.clockwise_choice.SetSelection(0)  # По часовой по умолчанию
        clockwise_sizer.Add(self.labels["clockwise"], 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        clockwise_sizer.AddStretchSpacer()
        clockwise_sizer.Add(self.clockwise_choice, 0, wx.ALIGN_CENTER_VERTICAL)
        shell_sizer.Add(clockwise_sizer, 0, wx.EXPAND | wx.ALL, 5)

        self.right_sizer.Add(shell_sizer, 0, wx.EXPAND | wx.ALL, 10)

        # --- Дополнительные условия ---
        additional_box = wx.StaticBox(self, label=loc.get("additional_label", "Доп. условия"))
        style_staticbox(additional_box)
        self.static_boxes["additional"] = additional_box
        additional_sizer = wx.StaticBoxSizer(additional_box, wx.VERTICAL)

        # Отрисовка осей
        axis_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.labels["axis"] = wx.StaticText(additional_box, label=loc.get("axis_label", "Отрисовка осей"))
        style_label(self.labels["axis"])
        self.axis_choice = wx.Choice(
            additional_box,
            choices=[
                loc.get("axis_yes", "Да"),
                loc.get("axis_no", "Нет")
            ],
            size=field_size
        )
        self.axis_choice.SetFont(font)
        self.axis_choice.SetSelection(0)  # Да по умолчанию
        axis_sizer.Add(self.labels["axis"], 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        axis_sizer.AddStretchSpacer()
        axis_sizer.Add(self.axis_choice, 0, wx.ALIGN_CENTER_VERTICAL)
        additional_sizer.Add(axis_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # Метки осей
        row7 = wx.BoxSizer(wx.HORIZONTAL)
        self.labels["axis_marks"] = wx.StaticText(additional_box, label=loc.get("axis_marks_label", "Метки осей"))
        style_label(self.labels["axis_marks"])
        self.axis_marks_combo = wx.ComboBox(
            additional_box,
            choices=default_axis_marks,
            value="10",
            style=wx.CB_DROPDOWN,
            size=field_size
        )
        style_combobox(self.axis_marks_combo)
        row7.Add(self.labels["axis_marks"], 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        row7.AddStretchSpacer()
        row7.Add(self.axis_marks_combo, 0, wx.ALIGN_CENTER_VERTICAL)
        additional_sizer.Add(row7, 0, wx.EXPAND | wx.ALL, 5)

        # Припуск на сварку сверху
        row8 = wx.BoxSizer(wx.HORIZONTAL)
        self.labels["allowance_top"] = wx.StaticText(additional_box, label=loc.get("allowance_top_label", "Припуск на сварку сверху, Lt"))
        style_label(self.labels["allowance_top"])
        self.allowance_top = wx.ComboBox(additional_box, choices=default_allowances, value="0", style=wx.CB_DROPDOWN, size=field_size)
        style_combobox(self.allowance_top)
        row8.Add(self.labels["allowance_top"], 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        row8.AddStretchSpacer()
        row8.Add(self.allowance_top, 0, wx.ALIGN_CENTER_VERTICAL)
        additional_sizer.Add(row8, 0, wx.EXPAND | wx.ALL, 5)

        # Припуск на сварку снизу
        row9 = wx.BoxSizer(wx.HORIZONTAL)
        self.labels["allowance_bottom"] = wx.StaticText(additional_box, label=loc.get("allowance_bottom_label", "Припуск на сварку снизу, Lb"))
        style_label(self.labels["allowance_bottom"])
        self.allowance_bottom = wx.ComboBox(additional_box, choices=default_allowances, value="0", style=wx.CB_DROPDOWN, size=field_size)
        style_combobox(self.allowance_bottom)
        row9.Add(self.labels["allowance_bottom"], 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        row9.AddStretchSpacer()
        row9.Add(self.allowance_bottom, 0, wx.ALIGN_CENTER_VERTICAL)
        additional_sizer.Add(row9, 0, wx.EXPAND | wx.ALL, 5)

        self.right_sizer.Add(additional_sizer, 0, wx.EXPAND | wx.ALL, 10)
        self.right_sizer.AddStretchSpacer()
        self.right_sizer.Add(self.create_button_bar(), 0, wx.ALIGN_RIGHT | wx.ALL, 5)

        # Собираем общий макет
        main_sizer.Add(self.left_sizer, 1, wx.EXPAND | wx.ALL, 10)
        main_sizer.Add(self.right_sizer, 0, wx.EXPAND | wx.ALL, 10)
        self.SetSizer(main_sizer)
        apply_styles_to_panel(self)  # Применяем стили ко всем элементам
        self.Layout()

    def on_branch(self, event: wx.Event):
        """
        Обрабатывает нажатие кнопки "Наличие отвода".
        Создает и отображает модальное окно BranchWindow для ввода параметров отвода.

        Args:
            event (wx.Event): Событие нажатия кнопки.
        """
        dialog = BranchWindow(self)
        dialog.ShowModal()
        dialog.Destroy()

    def collect_input_data(self) -> Dict:
        """
        Собирает данные из полей ввода панели в словарь для передачи в другую программу.

        Returns:
            Dict: Словарь с данными из полей ввода, включая данные отводов.
        """
        try:
            diameter = parse_float(self.diameter_input.GetValue())
            thickness = parse_float(self.thickness_combo.GetValue())
            diameter_type = ["inner", "middle", "outer"][self.diameter_type_choice.GetSelection()]
            diameter = at_diameter(diameter, thickness, diameter_type)

            data = {
                "order_number": self.order_input.GetValue(),
                "detail_number": self.detail_input.GetValue(),
                "material": self.material_combo.GetValue(),
                "thickness": thickness,
                "diameter": diameter,
                "length": parse_float(self.length_input.GetValue()),
                "angle": parse_float(self.angle_input.GetValue()) or 0.0,
                "clockwise": self.clockwise_choice.GetSelection() == 0,
                # True для "По часовой", False для "Против часовой"
                "axis": self.axis_choice.GetSelection() == 0,  # True для "Да", False для "Нет"
                "axis_marks": parse_float(self.axis_marks_combo.GetValue()) or 0,
                "weld_allowance_top": parse_float(self.allowance_top.GetValue()) or 0,
                "weld_allowance_bottom": parse_float(self.allowance_bottom.GetValue()) or 0,
                "layer_name": "0",
                "insert_point": self.insert_point,
                "cutouts": self.branch_data  # Добавляем данные отводов
            }
            return data
        except Exception as e:
            show_popup(loc.get("error", f"Ошибка сбора данных: {str(e)}"), popup_type="error")
            return {}

    def validate_input(self, data: Dict) -> bool:
        """
        Проверяет валидность введенных данных.

        Аргументы:
            data: Словарь с данными из полей ввода.

        Возвращает:
            bool: True, если данные валидны, иначе False.
        """
        if data.get("diameter") is None or data.get("diameter") <= 0:
            show_popup(loc.get("error", "Некорректный диаметр"), popup_type="error")
            return False
        if data.get("length") is None or data.get("length") <= 0:
            show_popup(loc.get("error", "Некорректная длина"), popup_type="error")
            return False
        if not data.get("material"):
            show_popup(loc.get("error", "Материал не выбран"), popup_type="error")
            return False
        if not data.get("thickness"):
            show_popup(loc.get("error", "Толщина не выбрана"), popup_type="error")
            return False
        if not data.get("insert_point"):
            show_popup(loc.get("point_selection_error", "Точка не выбрана"), popup_type="error")
            return False
        return True

    def process_input(self, data: Dict) -> bool:
        """
        Обрабатывает введенные данные, передавая их в callback-функцию.

        Аргументы:
            data: Словарь с данными из полей ввода.

        Возвращает:
            bool: True, если обработка успешна, иначе False.
        """
        try:
            if self.on_submit_callback:
                self.on_submit_callback(data)
            return True
        except Exception as e:
            show_popup(loc.get("error", f"Ошибка обработки данных: {str(e)}"), popup_type="error")
            return False

    def clear_input_fields(self):
        """
        Очищает все поля ввода и сбрасывает значения на начальные.
        """
        self.order_input.SetValue("")
        self.detail_input.SetValue("")
        self.material_combo.SetSelection(wx.NOT_FOUND)
        self.thickness_combo.SetSelection(wx.NOT_FOUND)
        self.diameter_input.SetValue("")
        self.diameter_type_choice.SetSelection(2)  # Внешний по умолчанию
        self.length_input.SetValue("")
        self.angle_input.SetValue("")
        self.clockwise_choice.SetSelection(0)  # По часовой по умолчанию
        self.axis_choice.SetSelection(0)  # Да по умолчанию
        self.axis_marks_combo.SetValue("10")
        self.allowance_top.SetValue("0")
        self.allowance_bottom.SetValue("0")
        self.insert_point = None

    def on_ok(self, event: wx.Event):
        """
        Обрабатывает нажатие кнопки "ОК": запрашивает точку вставки и передает данные в callback.

        Аргументы:
            event: Событие wxPython.
        """
        try:
            # Собираем данные из полей (без проверок)
            data = self.collect_input_data()

            # Получаем главное окно
            main_window = wx.GetTopLevelParent(self)

            # Сворачиваем окно перед выбором точки
            main_window.Iconize(True)

            # Инициализация CAD и выбор точки
            cad = ATCadInit()
            pt = at_get_point(
                cad.document,
                prompt=loc.get("point_prompt", "Введите точку вставки оболочки"),
                as_variant=False
            )

            # Разворачиваем окно обратно
            main_window.Iconize(False)
            main_window.Raise()
            main_window.SetFocus()

            if not pt:
                return

            # Сохраняем точку и обновляем словарь
            self.insert_point = pt
            data["insert_point"] = pt
            print(data)
            # Передаем данные дальше через callback
            if self.on_submit_callback:
                wx.CallAfter(self.process_input, data)

        except Exception as e:
            print(f"Ошибка в on_ok: {e}")

    def update_ui_language(self):
        """
        Обновляет язык интерфейса, применяя переводы ко всем элементам.
        """
        try:
            # Заголовки групп
            self.static_boxes["main_data"].SetLabel(loc.get("main_data_label", "Основные данные"))
            self.static_boxes["shell_params"].SetLabel(loc.get("shell_params_label", "Параметры оболочки"))
            self.static_boxes["additional"].SetLabel(loc.get("additional_label", "Доп. условия"))

            # Метки полей
            self.labels["order"].SetLabel(loc.get("order_label", "К-№"))
            self.labels["material"].SetLabel(loc.get("material_label", "Материал"))
            self.labels["thickness"].SetLabel(loc.get("thickness_label", "Толщина, S"))
            self.labels["diameter"].SetLabel(loc.get("diameter_label", "Диаметр, D"))
            self.labels["length"].SetLabel(loc.get("length_label", "Длина, L"))
            self.labels["angle"].SetLabel(loc.get("angle_label", "Положение шва (°)"))
            self.labels["clockwise"].SetLabel(loc.get("clockwise_label", "Развертка"))
            self.labels["axis"].SetLabel(loc.get("axis_label", "Отрисовка осей"))
            self.labels["axis_marks"].SetLabel(loc.get("axis_marks_label", "Метки осей"))
            self.labels["allowance_top"].SetLabel(loc.get("allowance_top_label", "Припуск на сварку сверху, Lt"))
            self.labels["allowance_bottom"].SetLabel(loc.get("allowance_bottom_label", "Припуск на сварку снизу, Lb"))

            # Поле выбора типа диаметра
            self.diameter_type_choice.SetItems([
                loc.get("diameter_type_inner", "Внутренний"),
                loc.get("diameter_type_middle", "Средний"),
                loc.get("diameter_type_outer", "Внешний")
            ])
            self.diameter_type_choice.SetSelection(2)  # Внешний по умолчанию

            # Поле выбора направления развертки
            self.clockwise_choice.SetItems([
                loc.get("clockwise_clockwise", "По часовой"),
                loc.get("clockwise_counterclockwise", "Против часовой")
            ])
            self.clockwise_choice.SetSelection(0)  # По часовой по умолчанию

            # Поле выбора отрисовки осей
            self.axis_choice.SetItems([
                loc.get("axis_yes", "Да"),
                loc.get("axis_no", "Нет")
            ])
            self.axis_choice.SetSelection(0)  # Да по умолчанию

            # Кнопки
            self.buttons[0].SetLabel(loc.get("ok_button", "ОК"))
            if len(self.buttons) > 2:
                self.buttons[1].SetLabel(loc.get("clear_button", "Очистить"))
                self.buttons[2].SetLabel(loc.get("cancel_button", "Возврат"))
            else:
                self.buttons[1].SetLabel(loc.get("cancel_button", "Возврат"))
            self.branch_button.SetLabel(loc.get("branch_button", "Наличие отвода"))

            apply_styles_to_panel(self)  # Обновляем стили после смены языка
            self.Layout()  # Перестраиваем макет для корректного отображения
        except Exception as e:
            show_popup(loc.get("error", f"Ошибка обновления языка: {str(e)}"), popup_type="error")

if __name__ == "__main__":
    """
    Тестовый вызов окна для проверки интерфейса, поведения кнопок и формирования словаря данных.
    Выполняет явный вызов at_get_point для выбора точки в AutoCAD и выводит словарь данных в исходном виде.
    """
    app = wx.App(False)
    frame = wx.Frame(None, title="Тест ShellContentPanel", size=(1000, 700))
    panel = ShellContentPanel(frame)

    def on_ok_test(data):
        """
        Тестовая функция для обработки callback.
        Выводит собранные данные в консоль в виде словаря.
        """
        try:
            print("Собранные данные:", data)
            # Симулируем задержку, как в реальной обработке
            wx.MilliSleep(100)
            if panel.IsBeingDeleted():
                print("Окно уничтожено в тестовом callback")
            else:
                print("Окно всё ещё существует после тестового callback")
        except Exception as e:
            print(f"Ошибка в тестовом callback: {e}")
            show_popup(loc.get("error", f"Ошибка в тестовом callback: {str(e)}"), popup_type="error")

    def on_ok_event(event):
        """
        Тестовая функция для обработки нажатия 'ОК'.
        Выполняет выбор точки через at_get_point, проверяет валидацию данных,
        вызывает callback и выводит словарь данных.
        """
        try:
            if panel.IsBeingDeleted():
                print("Окно уничтожено перед обработкой ОК")
                return

            from programs.at_input import at_get_point
            from config.at_cad_init import ATCadInit
            from windows.at_window_utils import update_status_bar_point_selected

            # Собираем данные
            data = panel.collect_input_data()

            # Запрашиваем точку вставки
            cad = ATCadInit()
            frame.Iconize(True)
            try:
                pt = at_get_point(cad.document, prompt=loc.get("point_prompt", "Введите точку вставки оболочки"), as_variant=False)
            except Exception as e:
                show_popup(loc.get("point_selection_error", f"Ошибка выбора точки: {str(e)}"), popup_type="error")
                pt = None

            frame.Iconize(False)
            frame.Raise()
            frame.SetFocus()

            if not pt:
                show_popup(loc.get("point_selection_error", "Точка не выбрана"), popup_type="error")
                return

            # Обновляем точку в данных
            panel.insert_point = pt
            data["insert_point"] = pt
            update_status_bar_point_selected(panel, pt)

            # Проверяем валидность данных
            if not panel.validate_input(data):
                print("Валидация не пройдена")
                return

            # Передаем данные в callback
            panel.on_submit_callback = on_ok_test
            if not panel.IsBeingDeleted():
                wx.CallAfter(panel.process_input, data)  # Отложенный вызов callback
                print("Данные переданы в callback отложенно")
            else:
                print("Окно уничтожено после нажатия ОК")
        except Exception as e:
            print(f"Ошибка в тестовом запуске: {e}")
            show_popup(loc.get("error", f"Ошибка в тестовом запуске: {str(e)}"), popup_type="error")
        finally:
            if not frame.IsBeingDeleted():
                frame.Iconize(False)
                frame.Raise()
                frame.SetFocus()

    sizer = wx.BoxSizer(wx.VERTICAL)
    sizer.Add(panel, 1, wx.EXPAND)
    frame.SetSizer(sizer)
    frame.Layout()
    frame.Show()
    app.MainLoop()

