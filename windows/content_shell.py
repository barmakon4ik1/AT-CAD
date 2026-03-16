# Filename: shell_content_panel.py
"""
Модуль содержит панель ShellContentPanel для настройки параметров оболочки
и модальное окно BranchWindow для настройки параметров отвода в приложении AT-CAD.
"""
import wx
import wx.grid
from typing import Optional, Dict, List
from wx.lib.buttons import GenButton
from config.at_cad_init import ATCadInit
from locales.at_translations import loc
from programs.at_construction import at_diameter
from programs.at_input import at_get_point
from windows.at_fields_builder import parse_float, FormBuilder, FieldBuilder, normalize_input
from windows.at_window_utils import (
    CanvasPanel, show_popup, get_standard_font, apply_styles_to_panel,
    create_standard_buttons, adjust_button_widths, BaseContentPanel,
    load_common_data, style_label, style_textctrl,
    style_combobox, style_staticbox, style_gen_button
)
from config.at_config import SHELL_IMAGE_PATH, UNWRAPPER_PATH, get_setting

# -----------------------------
# Локальные переводы модуля
# -----------------------------
TRANSLATIONS = {
    "error": {"ru": "Ошибка", "de": "Fehler", "en": "Error"},
    "point_prompt": {
        "ru": "Введите точку вставки оболочки",
        "de": "Einfügenpunkt für Mantel eingeben",
        "en": "Enter the shell insertion point",
    },
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
    "clockwise_label":{"ru": "Развертка", "de": "Abwicklung", "en": "Unfold"},
    "clockwise_clockwise": {"ru": "По часовой", "de": "Im Uhrzeigersinn", "en": "Clockwise"},
    "clockwise_counterclockwise": {"ru": "Против часовой", "de": "Gegen Uhrzeigersinn", "en": "Counterclockwise"},
    "additional_label": {"ru": "Дополнительные условия", "de": "Zusatzbedingungen", "en": "Additional"},
    "offset_label": {"ru": "Отступ Y, мм", "de": "Abstand Y, mm", "en": "Offset Y, mm"},
    "axis_label": {"ru": "Отрисовка осей", "de": "Zeichnungsachsen", "en": "Drawing axes"},
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
            size=wx.Size(1600, 600),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )

        self.steps_combo = None
        self.SetMinSize(wx.Size(1600, 600))
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
        left_panel_container.SetMinSize(wx.Size(400, -1))
        left_panel_container.SetMaxSize(wx.Size(400, -1))  # фиксированная ширина для левой панели

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
        field_size = wx.Size(150, -1)
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
        except:
            raise "Общая ошибка"

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

    def on_mode_change(self, _):
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

    def on_add_row(self, _):
        """
        Добавляет новую строку в таблицу.
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

        def _grid_bool(val):
            return val in ("1", "True", "true")

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
                    "steps":  int(self.steps_combo.GetValue()),
                    "mode": "polyline",  # bulge / polyline / spline
                    "layer_name": "0",  # Жестко заданный слой
                    "thickness": parse_float(self.table.GetCellValue(row, 5)) or 0.0,  # Толщина отвода
                    "height": parse_float(self.table.GetCellValue(row, 3)) or 0.0,  # Высота отвода
                    "unroll_branch": _grid_bool(self.table.GetCellValue(row, 8)),
                    "flange_present": _grid_bool(self.table.GetCellValue(row, 9)),
                    # "unroll_branch": self.table.GetCellValue(row, 8) == "1",  # "" == "1" → False; "1" == "1" → True
                    # "flange_present": self.table.GetCellValue(row, 9) == "1",  # "" == "1" → False; "1" == "1" → True
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

    def on_ok(self, _):
        """
        Обрабатывает нажатие кнопки "ОК".
        Собирает данные из таблицы и закрывает окно с результатом wx.ID_OK.
        """
        data = self.collect_input_data()
        if data is None and any(self.table.GetCellValue(row, 1) for row in range(self.table.GetNumberRows())):
            show_popup(loc.get("error_invalid_diameter", "Диаметр отвода (d) обязателен и должен быть больше 0"), popup_type="error")
            return
        self.parent.branch_data = data  # Сохраняем данные в родительской панели
        self.EndModal(wx.ID_OK)

    def on_clear(self, _):
        """
        Обрабатывает нажатие кнопки "Очистить".
        Сбрасывает значения полей таблицы.
        """
        self.clear_input_fields()

    def on_cancel(self, _):
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
        self.fb = None
        self.form = None
        self.right_sizer = None
        self.canvas = None
        self.left_sizer = None
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
        self.Freeze()
        try:
            # удалить старый layout
            old = self.GetSizer()
            if old:
                old.Clear(True)
                self.SetSizer(None)

            self.form = FormBuilder(self)

            # -----------------------------
            # Загрузка общих данных
            # -----------------------------
            common_data = load_common_data()
            material_options = [m["name"] for m in common_data.get("material", []) if m["name"]]
            thickness_options = common_data.get("thicknesses", [])

            main_sizer = wx.BoxSizer(wx.HORIZONTAL)
            self.left_sizer = wx.BoxSizer(wx.VERTICAL)
            self.right_sizer = wx.BoxSizer(wx.VERTICAL)

            # Левый блок: изображение и кнопки
            image_path = str(SHELL_IMAGE_PATH)
            self.canvas = CanvasPanel(self, image_file=image_path, size=(600, 400))
            self.left_sizer.Add(self.canvas, 1, wx.EXPAND | wx.ALL, 10)

            fb_left = FieldBuilder(parent=self, target_sizer=self.left_sizer, form=self.form)
            fb_left.universal_row(
                None,
                [
                    {
                        "type": "button",
                        "label": loc.get("branch_button"),
                        "callback": self.on_branch,
                        "size": (240, 45),
                        "bg_color": "#3498db"
                    }
                ],
                align_right=False
            )

            # Правый блок
            self.fb = FieldBuilder(parent=self, target_sizer=self.right_sizer, form=self.form)

            # --- Основные данные ---
            main_data_sizer = self.fb.static_box(loc.get("main_data_label", "Основные данные"))
            fb_main = FieldBuilder(parent=self, target_sizer=main_data_sizer, form=self.form)

            # Номер заказа и номер детали
            fb_main.universal_row(
                "order_label",
                [
                    {"type": "text", "name": "order_input", "value": "", "required": False, "default": ""},
                    {"type": "text", "name": "detail_input", "value": "", "required": False, "default": ""},
                ]
            )
            # Материал
            fb_main.universal_row(
                "material_label",
                [
                    {"type": "combo",
                     "name": "material_combo",
                     "choices": material_options,
                     "value": material_options[0],
                     "required": True,
                     "default": material_options[0],
                     "size": (310, -1),
                     "readonly": False
                     }
                ]
            )

            # Толщина
            fb_main.universal_row(
                "thickness_label",
                [
                    {"type": "combo", "name": "thickness_combo", "choices": thickness_options, "value": "",
                     "required": True, "default": "3"}
                ]
            )

            shell_sizer = self.fb.static_box(loc.get("shell_params_label"))

            fb_shell = FieldBuilder(parent=self, target_sizer=shell_sizer, form=self.form)

            # Диаметр + тип
            fb_shell.universal_row(
                "diameter_label",
                [
                    {"type": "text", "name": "diameter_input", "value": ""},
                    {
                        "type": "combo",
                        "name": "diameter_type_choice",
                        "choices": [
                            loc.get("diameter_type_inner"),
                            loc.get("diameter_type_middle"),
                            loc.get("diameter_type_outer"),
                        ],
                        "value": loc.get("diameter_type_outer"),
                        "readonly": True
                    }
                ]
            )

            # Длина
            fb_shell.universal_row(
                "length_label",
                [
                    {"type": "text", "name": "length_input", "value": ""}
                ]
            )

            # Угол
            fb_shell.universal_row(
                "angle_label",
                [
                    {"type": "text", "name": "angle_input", "value": ""}
                ]
            )

            # Направление развертки
            fb_shell.universal_row(
                "clockwise_label",
                [
                    {
                        "type": "combo",
                        "name": "clockwise_choice",
                        "choices": [
                            loc.get("clockwise_clockwise"),
                            loc.get("clockwise_counterclockwise")
                        ],
                        "value": loc.get("clockwise_clockwise"),
                        "readonly": True
                    }
                ]
            )

            # Отступ от базового основания
            fb_shell.universal_row(
                "offset_label",
                [
                    {"type": "text", "name": "offset", "value": "0", "default": "0"},
                ]
            )

            # --- Дополнительные условия ---
            additional_sizer = self.fb.static_box(loc.get("additional_label"))

            fb_add = FieldBuilder(parent=self, target_sizer=additional_sizer, form=self.form)

            # Оси
            fb_add.universal_row(
                "axis_label",
                [
                    {
                        "type": "combo",
                        "name": "axis_choice",
                        "choices": [
                            loc.get("axis_yes"),
                            loc.get("axis_no")
                        ],
                        "value": loc.get("axis_yes"),
                        "readonly": True
                    }
                ]
            )

            # Метки осей
            fb_add.universal_row(
                "axis_marks_label",
                [
                    {
                        "type": "combo",
                        "name": "axis_marks_combo",
                        "choices": default_axis_marks,
                        "value": "10",
                        "required": False,
                        "default": "10",
                        "readonly": False,
                    }
                ]
            )

            # Припуск сверху
            fb_add.universal_row(
                "allowance_top_label",
                [
                    {
                        "type": "combo",
                        "name": "allowance_top",
                        "choices": default_allowances,
                        "value": "0",
                        "required": False,
                        "default": "0",
                        "readonly": False,
                    }
                ]
            )

            # Припуск снизу
            fb_add.universal_row(
                "allowance_bottom_label",
                [
                    {
                        "type": "combo",
                        "name": "allowance_bottom",
                        "choices": default_allowances,
                        "value": "0",
                        "default": "0",
                        "readonly": False,
                    }
                ]
            )


            # self.right_sizer.AddStretchSpacer()
            # Кнопки
            self.right_sizer.Add(self.create_button_bar(), 0, wx.ALIGN_RIGHT | wx.ALL, 5)

            # Собираем общий макет
            main_sizer.Add(self.left_sizer, 1, wx.EXPAND | wx.ALL, 10)
            main_sizer.Add(self.right_sizer, 0, wx.EXPAND | wx.ALL, 10)
            self.SetSizer(main_sizer)
            apply_styles_to_panel(self)  # Применяем стили ко всем элементам
            # self.Layout()
            self.on_clear()
        finally:
            self.Layout()
            self.Thaw()

    def on_branch(self, _):
        """
        Обрабатывает нажатие кнопки "Наличие отвода".
        Создает и отображает модальное окно BranchWindow для ввода параметров отвода.
        """
        dialog = BranchWindow(self)
        try:
            if dialog.ShowModal() == wx.ID_OK:
                # collect_input_data уже возвращает список словарей
                self.branch_data = dialog.collect_input_data()
        finally:
            dialog.Destroy()

    def collect_input_data(self) -> Dict:
        """
        Собирает данные из полей ввода панели в словарь для передачи в другую программу.

        Returns:
            Dict: Словарь с данными из полей ввода, включая данные отводов.
        """
        try:
            raw = self.form.collect()
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
                "cutouts": self.branch_data,  # Добавляем данные отводов
                "offset": normalize_input(raw, "offset", 0.0) # учитываем отступ от базовой плоскости
            }
            # print(data)
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
        Очистка всех полей формы и сброс точки вставки.
        """
        self.form.clear()

    def on_clear(self, event: Optional[wx.Event] = None):
        """Очистка полей по кнопке Clear."""
        _ = event
        self.clear_input_fields()

    # def on_cancel(self, event: Optional[wx.Event] = None, switch_content="content_apps"):
    #     """Закрытие панели и возврат к предыдущему контенту."""
    #     _ = event
    #     self.switch_content_panel(switch_content)

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
            # print(data)
            # Передаем данные дальше через callback
            if self.on_submit_callback:
                wx.CallAfter(self.process_input, data)

        except Exception as e:
            print(f"Ошибка в on_ok: {e}")


    def update_ui_language(self):
        self.setup_ui()

if __name__ == "__main__":
    """
    Тестовый вызов окна для проверки интерфейса, поведения кнопок и формирования словаря данных.
    Выполняет явный вызов at_get_point для выбора точки в AutoCAD и выводит словарь данных в исходном виде.
    """
    app = wx.App(False)
    frame = wx.Frame(None, title="Тест ShellContentPanel", size=wx.Size(1000, 700))
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

    def on_ok_event(_):
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
                print("Данные переданы в callback отложено")
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

