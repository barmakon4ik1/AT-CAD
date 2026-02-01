# windows/at_fields_builder.py
# noinspection SpellCheckingInspection
"""
Модуль: at_fields_builder.py

Содержит классы и функции для построения форм в wxPython с поддержкой:
- типовых полей (текстовые, многострочные, выбор из списка)
- единообразного оформления
- локализации на лету
- валидации и парсинга данных

Основные классы:
- FormField — описание одного поля формы
- FormBuilder — сборка и управление формой
- FieldBuilder — удобная обёртка для добавления полей с метками
- LocalizableStaticBox / LocalizableButton — обёртки для локализации стандартных контролов

Пример таблицы полей формы:

| Имя поля   | Тип контрола    | Обязательное | Значение по умолчанию | Парсер           |
|------------|----------------|--------------|-----------------------|-----------------|
| username   | wx.TextCtrl     | Да           | None                  | str.strip       |
| description| wx.TextCtrl     | Нет          | ""                    | None            |
| choice     | wx.Choice       | Да           | "Option1"             | None            |
| combo      | wx.ComboBox     | Нет          | "Default"             | None            |
"""

from typing import Any, Callable, Dict

import wx
from windows.at_window_utils import get_standard_font
from locales.at_translations import loc


# ----------------------------------------------------------------------
# Формы и поля
# ----------------------------------------------------------------------
class FormField:
    """
    Описание одного поля формы.

    Атрибуты:
        name: str — имя поля
        ctrl: wx.Control — контрол для ввода данных
        required: bool — обязательность заполнения
        parser: Callable — функция преобразования значения
        default: Any — значение по умолчанию
        getter: Callable — пользовательская функция получения значения
        setter: Callable — пользовательская функция установки значения
    """

    def __init__(
        self,
        name: str,
        ctrl: wx.Window,
        required: bool = False,
        parser: Callable[[Any], Any] | None = None,
        default: Any = None,
        getter: Callable[[], Any] | None = None,
        setter: Callable[[Any], None] | None = None,
    ):
        self.name = name
        self.ctrl = ctrl
        self.required = required
        self.parser = parser
        self.default = default
        self.getter = getter
        self.setter = setter

    def get_raw(self) -> Any:
        """Возвращает сырое значение из контрола."""
        if self.getter:
            return self.getter()
        elif hasattr(self.ctrl, "GetValue"):
            return self.ctrl.GetValue()
        return None

    def get_value(self) -> Any:
        """
        Возвращает обработанное значение поля:
        - если пустое и есть default — возвращает default
        - если пустое и поле обязательное — вызывает ValueError
        - если указан parser — возвращает результат parser(raw)
        - иначе — сырое значение
        """
        raw = self.get_raw()

        def is_empty(value):
            return value is None or value == ""

        if is_empty(raw):
            if self.default is not None:
                return self.default
            if self.required:
                raise ValueError(
                    loc.get("no_data_error", f"Field '{self.name}' is required")
                )
            return raw

        if self.parser:
            return self.parser(raw)

        return raw

    def set_value(self, value: Any) -> None:
        """
        Безопасно устанавливает значение поля.

        Логика:
        1. Если задан setter, используется он.
        2. Если контрол имеет SetValue(), вызывается он.
        3. Для wx.Choice и wx.ComboBox устанавливается выбор/текст.
        4. Иначе значение игнорируется (например, кастомные контролы без setter).
        """
        if self.setter:
            self.setter(value)
        elif hasattr(self.ctrl, "SetValue"):
            self.ctrl.SetValue(value)
        elif isinstance(self.ctrl, wx.Choice):
            if value in self.ctrl.GetItems():
                self.ctrl.SetStringSelection(value)
            else:
                self.ctrl.SetSelection(wx.NOT_FOUND)
        elif isinstance(self.ctrl, wx.ComboBox):
            self.ctrl.SetValue(str(value))
        # кастомные контролы игнорируем


class FormBuilder:
    """
    Управление формой: регистрация полей, сбор данных, очистка и документация.
    """

    def __init__(self, panel: wx.Window):
        self.panel = panel
        self.fields: Dict[str, FormField] = {}

    def register(
        self,
        name: str,
        ctrl: wx.Window,
        required: bool = False,
        parser: Callable[[str], Any] | None = None,
        default: Any = None,
        getter: Callable[[], Any] | None = None,
        setter: Callable[[Any], None] | None = None
    ) -> wx.Window:
        """
        Регистрирует поле формы.

        Аргументы:
            name — имя поля
            ctrl — контрол wx.Control
            required — обязательность
            parser — функция преобразования значения
            default — значение по умолчанию
            getter — пользовательская функция получения значения
            setter — пользовательская функция установки значения
        """
        self.fields[name] = FormField(
            name=name,
            ctrl=ctrl,
            required=required,
            parser=parser,
            default=default,
            getter=getter,
            setter=setter
        )
        return ctrl

    def collect(self) -> dict:
        """Собирает значения всех полей формы в словарь."""
        data = {}
        for name, field in self.fields.items():
            try:
                data[name] = field.get_value()
            except Exception as e:
                raise ValueError(f"Error in field '{name}': {e}") from e
        return data

    def clear(self) -> None:
        """Очищает все поля формы безопасно, используя set_value()."""
        for field in self.fields.values():
            field.set_value(field.default)

    # ------------------------------------------------------------------
    # Документация и отладка
    # ------------------------------------------------------------------
    def get_fields_table(self) -> str:
        """Возвращает таблицу зарегистрированных полей в формате Markdown."""
        lines = [
            "| Имя поля | Тип контрола | Обязательное | Значение по умолчанию | Парсер |",
            "|----------|-------------|--------------|------------------------|--------|",
        ]
        for name, field in self.fields.items():
            ctrl_type = type(field.ctrl).__name__
            required = "Да" if field.required else "Нет"
            default = repr(field.default)
            parser = (
                field.parser.__name__
                if callable(field.parser) and hasattr(field.parser, "__name__")
                else repr(field.parser) if field.parser else ""
            )
            lines.append(f"| {name} | {ctrl_type} | {required} | {default} | {parser} |")
        return "\n".join(lines)

    def print_fields_table(self) -> None:
        """Выводит таблицу полей в stdout."""
        print(self.get_fields_table())

    def as_dict_schema(self) -> Dict[str, Dict[str, Any]]:
        """Возвращает словарь с описанием всех полей формы."""
        return {
            name: {
                "control": type(field.ctrl).__name__,
                "required": field.required,
                "default": field.default,
                "parser": getattr(field.parser, "__name__", None),
            }
            for name, field in self.fields.items()
        }


# ----------------------------------------------------------------------
# FieldBuilder: удобное создание полей + метки
# ----------------------------------------------------------------------
class FieldBuilder:
    """
    Помощник для создания типовых строк формы: метка + контрол.

    Поддерживает:
    - единый стиль
    - StretchSpacer для выравнивания
    - локализацию всех локализуемых элементов (метки, заголовки, кнопки)
    - автоматическую регистрацию в FormBuilder
    """

    def __init__(
        self,
        parent: wx.Window,
        target_sizer: wx.Sizer,
        form: FormBuilder | None = None,
        default_size=(150, -1),
        label_right_padding=10,
        row_border=5,
        label_proportion=0,
        field_proportion=0
    ):
        self.parent = parent
        self.sizer = target_sizer
        self.form = form

        self.font = get_standard_font()
        self.default_size = default_size
        self.label_pad = label_right_padding
        self.row_border = row_border
        self.label_prop = label_proportion
        self.field_prop = field_proportion

        # Все локализуемые элементы (StaticText, StaticBox, Button и др.)
        # хранятся здесь по ключу локализации
        self._labels: Dict[str, wx.Window] = {}

    # ------------------------------------------------------------------
    # Внутренние методы
    # ------------------------------------------------------------------

    def _create_label(self, label_key: str) -> wx.StaticText:
        """Создаёт локализованную метку (StaticText) и сохраняет её для смены языка."""
        lbl = wx.StaticText(self.parent, label=loc.get(label_key, label_key))
        lbl.SetFont(self.font)
        self._labels[label_key] = lbl
        return lbl

    def _add_row(self, label: wx.StaticText, ctrl: wx.Window, proportion=0):
        """Добавляет строку в sizer: метка + контрол + выравнивание."""
        row = wx.BoxSizer(wx.HORIZONTAL)
        row.Add(label, self.label_prop, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, self.label_pad)
        row.AddStretchSpacer()
        row.Add(ctrl, self.field_prop, wx.ALIGN_CENTER_VERTICAL)
        self.sizer.Add(row, proportion, wx.EXPAND | wx.ALL, self.row_border)

    # ------------------------------------------------------------------
    # Локализация
    # ------------------------------------------------------------------

    def update_language(self):
        """
        Обновляет подписи всех локализуемых элементов (StaticText, StaticBox, Button и др.).
        """
        for key, ctrl in self._labels.items():
            if hasattr(ctrl, "SetLabel"):
                ctrl.SetLabel(loc.get(key, key))

    def register_button(self, button: wx.Button, key: str):
        """Регистрирует кнопку для локализации через FieldBuilder."""
        self._labels[key] = button
        return button

    def register_static_box(self, box: wx.StaticBox, key: str):
        """Регистрирует StaticBox для локализации через FieldBuilder."""
        self._labels[key] = box
        return box

    # ------------------------------------------------------------------
    # Создание элементов управления
    # ------------------------------------------------------------------

    def create_label(self, label_key: str) -> wx.StaticText:
        """Создаёт локализованную метку (StaticText)."""
        return self._create_label(label_key)

    def text(self, name: str, label_key: str, value: str = "", required: bool = False,
             parser: Callable[[str], Any] | None = None, default: Any = None,
             size=None, proportion=0) -> wx.TextCtrl:
        """Однострочное текстовое поле с меткой."""
        ctrl = wx.TextCtrl(self.parent, value=str(value), size=size or self.default_size)
        ctrl.SetFont(self.font)
        lbl = self._create_label(label_key)
        self._add_row(lbl, ctrl, proportion)
        if self.form:
            self.form.register(name, ctrl, required, parser, default)
        setattr(self.parent, name, ctrl)
        return ctrl

    def multiline_text(self, name: str, label_key: str, value: str = "", required: bool = False,
                       parser: Callable[[str], Any] | None = None, default: Any = None,
                       size=None, proportion=0) -> wx.TextCtrl:
        """Многострочное текстовое поле с меткой."""
        ctrl = wx.TextCtrl(self.parent, value=value, style=wx.TE_MULTILINE, size=size or self.default_size)
        ctrl.SetFont(self.font)
        lbl = self._create_label(label_key)
        self._add_row(lbl, ctrl, proportion)
        if self.form:
            self.form.register(name, ctrl, required, parser, default)
        setattr(self.parent, name, ctrl)
        return ctrl

    def _register_field(self, name: str, ctrl: wx.Window, required: bool, parser, default):
        """Регистрация поля в FormBuilder."""
        if self.form:
            self.form.register(name, ctrl, required, parser, default)
        setattr(self.parent, name, ctrl)

    def choice(self, name: str, label_key: str, choices: list, selection: int = 0,
               required: bool = False, parser: Callable[[Any], Any] | None = None,
               default: Any = None, size=None, proportion=0) -> wx.Choice:
        """Создаёт выбор из списка (wx.Choice) с меткой."""
        ctrl = wx.Choice(self.parent, choices=choices, size=size or self.default_size)
        ctrl.SetFont(self.font)
        if choices:
            ctrl.SetSelection(selection)

        def value_getter():
            idx = ctrl.GetSelection()
            if idx == wx.NOT_FOUND:
                return ""
            return ctrl.GetString(idx)

        lbl = self._create_label(label_key)
        self._add_row(lbl, ctrl, proportion)

        if self.form:
            self.form.register(
                name=name,
                ctrl=ctrl,
                required=required,
                parser=parser,
                default=default,
                getter=value_getter,
                setter=lambda v: ctrl.SetStringSelection(v) if v in ctrl.GetItems() else ctrl.SetSelection(wx.NOT_FOUND)
            )

        setattr(self.parent, name, ctrl)
        return ctrl

    def combo(self, name: str, label_key: str, choices: list, value: str = "",
              required: bool = False, parser: Callable[[Any], Any] | None = None,
              default: Any = None, style=wx.CB_DROPDOWN, size=None, proportion=0) -> wx.ComboBox:
        """Создаёт комбинированный список (wx.ComboBox) с меткой."""
        ctrl = wx.ComboBox(self.parent, choices=choices, value=str(value), style=style,
                           size=size or self.default_size)
        ctrl.SetFont(self.font)
        lbl = self._create_label(label_key)
        self._add_row(lbl, ctrl, proportion)
        self._register_field(name, ctrl, required, parser, default)
        return ctrl

    # ------------------------------------------------------------------
    # StaticBox (группы полей)
    # ------------------------------------------------------------------

    def static_box(self, box_key: str, orient=wx.VERTICAL, proportion=0,
                   flag=wx.EXPAND | wx.ALL, border=5) -> wx.StaticBoxSizer:
        """Создаёт StaticBoxSizer с локализуемым заголовком."""
        box = wx.StaticBox(self.parent, label=loc.get(box_key, box_key))
        box.SetFont(self.font)
        self.register_static_box(box, box_key)
        sizer = wx.StaticBoxSizer(box, orient)
        self.sizer.Add(sizer, proportion, flag, border)
        return sizer

    def button(self, label_key: str, style=0, size=None) -> wx.Button:
        """Создаёт кнопку и регистрирует для локализации."""
        btn = wx.Button(self.parent, label=loc.get(label_key, label_key), style=style, size=size or self.default_size)
        btn.SetFont(self.font)
        self.register_button(btn, label_key)
        return btn


# ----------------------------------------------------------------------
# Локализуемые обёртки для стандартных элементов управления
# ----------------------------------------------------------------------
class LocalizableStaticBox:
    """Обёртка для wx.StaticBox с поддержкой динамической локализации."""
    def __init__(self, box: wx.StaticBox, key: str):
        self.box = box
        self.key = key

    def update_language(self) -> None:
        """Обновляет надпись StaticBox на текущий язык."""
        self.box.SetLabel(loc.get(self.key))


class LocalizableButton:
    """Обёртка для wx.Button с поддержкой динамической локализации."""
    def __init__(self, button: wx.Button, key: str):
        self.button = button
        self.key = key

    def update_language(self) -> None:
        """Обновляет надпись кнопки на текущий язык."""
        self.button.SetLabel(loc.get(self.key))


"""
Пример использования:

form = FormBuilder(panel)
fb = FieldBuilder(panel, sizer, form)

fb.text("diameter", "diameter_lbl", required=True, parser=float)
fb.choice("material", "material_lbl", ["Steel", "Al"], required=True)
fb.combo("note", "note_lbl", [])

# Во время разработки:
form.print_fields_table()


Вывод ы консоль:
| Имя поля | Тип контрола | Обязательное | Значение по умолчанию | Парсер |
|----------|-------------|--------------|------------------------|--------|
| diameter | TextCtrl    | Да           | None                   | float  |
| material | Choice      | Да           | None                   |        |
| note     | ComboBox    | Нет          | None                   |        |
"""