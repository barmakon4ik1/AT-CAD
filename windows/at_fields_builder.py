# windows/at_fields_builder.py
from typing import Any, Callable, Dict, List

import wx
from windows.at_window_utils import get_standard_font
from locales.at_translations import loc


class FormField:
    """
    Описание одного поля формы.
    Хранит:
    - wx.Control
    - правила валидации
    - парсер
    """

    def __init__(
        self,
        name: str,
        ctrl: wx.Window,
        required: bool = False,
        parser: Callable[[str], Any] | None = None,
        default: Any = None
    ):
        self.name = name
        self.ctrl = ctrl
        self.required = required
        self.parser = parser
        self.default = default

    def get_raw(self):
        return self.ctrl.GetValue()

    def get_value(self):
        raw = self.get_raw()

        if not raw:
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


class FormBuilder:
    """
    Оркестратор формы:
    - регистрирует поля
    - собирает данные
    - очищает форму
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
        default: Any = None
    ):
        self.fields[name] = FormField(
            name=name,
            ctrl=ctrl,
            required=required,
            parser=parser,
            default=default
        )
        return ctrl

    def collect(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {}
        for name, field in self.fields.items():
            data[name] = field.get_value()
        return data

    def clear(self):
        for field in self.fields.values():
            field.ctrl.SetValue("")


class FieldBuilder:
    """
    Помощник для создания типовых строк:
    Метка + контрол.

    Поддерживает:
    - единый стиль
    - StretchSpacer
    - локализацию на лету
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

        # Реестр меток для локализации
        self._labels: Dict[str, wx.StaticText] = {}

    # ------------------------------------------------------------------
    # Внутренние методы
    # ------------------------------------------------------------------

    def _create_label(self, label_key: str) -> wx.StaticText:
        lbl = wx.StaticText(
            self.parent,
            label=loc.get(label_key, label_key)
        )
        lbl.SetFont(self.font)

        lbl._label_key = label_key
        self._labels[label_key] = lbl
        return lbl

    def _add_row(self, label: wx.StaticText, ctrl: wx.Window, proportion=0):
        row = wx.BoxSizer(wx.HORIZONTAL)
        row.Add(label, self.label_prop, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, self.label_pad)
        row.AddStretchSpacer()
        row.Add(ctrl, self.field_prop, wx.ALIGN_CENTER_VERTICAL)
        self.sizer.Add(row, proportion, wx.EXPAND | wx.ALL, self.row_border)

    # ------------------------------------------------------------------
    # Локализация
    # ------------------------------------------------------------------

    def update_language(self):
        for key, lbl in self._labels.items():
            lbl.SetLabel(loc.get(key, key))

    # ------------------------------------------------------------------
    # Контролы
    # ------------------------------------------------------------------

    def text(
        self,
        name: str,
        label_key: str,
        value: str = "",
        required: bool = False,
        parser: Callable[[str], Any] | None = None,
        default: Any = None,
        size=None,
        proportion=0
    ) -> wx.TextCtrl:
        ctrl = wx.TextCtrl(
            self.parent,
            value=str(value),
            size=size or self.default_size
        )
        ctrl.SetFont(self.font)

        lbl = self._create_label(label_key)
        self._add_row(lbl, ctrl, proportion)

        if self.form:
            self.form.register(
                name=name,
                ctrl=ctrl,
                required=required,
                parser=parser,
                default=default
            )

        setattr(self.parent, name, ctrl)
        return ctrl

    def multiline_text(
        self,
        name: str,
        label_key: str,
        value: str = "",
        required: bool = False,
        parser: Callable[[str], Any] | None = None,
        default: Any = None,
        size=None,
        proportion=0
    ) -> wx.TextCtrl:
        ctrl = wx.TextCtrl(
            self.parent,
            value=value,
            style=wx.TE_MULTILINE,
            size=size or self.default_size
        )
        ctrl.SetFont(self.font)

        lbl = self._create_label(label_key)
        self._add_row(lbl, ctrl, proportion)

        if self.form:
            self.form.register(
                name=name,
                ctrl=ctrl,
                required=required,
                parser=parser,
                default=default
            )

        setattr(self.parent, name, ctrl)
        return ctrl

    def _register_field(
            self,
            name: str,
            ctrl: wx.Window,
            required: bool,
            parser,
            default
    ):
        if self.form:
            self.form.register(
                name=name,
                ctrl=ctrl,
                required=required,
                parser=parser,
                default=default
            )
        setattr(self.parent, name, ctrl)

    def choice(
            self,
            name: str,
            label_key: str,
            choices: list,
            selection: int = 0,
            required: bool = False,
            parser: Callable[[Any], Any] | None = None,
            default: Any = None,
            size=None,
            proportion=0
    ) -> wx.Choice:
        ctrl = wx.Choice(
            self.parent,
            choices=choices,
            size=size or self.default_size
        )
        ctrl.SetFont(self.font)

        if choices:
            ctrl.SetSelection(selection)

        # raw value = текст выбранного элемента
        def value_getter():
            idx = ctrl.GetSelection()
            if idx == wx.NOT_FOUND:
                return ""
            return ctrl.GetString(idx)

        ctrl.GetValue = value_getter  # ← ключевой момент

        lbl = self._create_label(label_key)
        self._add_row(lbl, ctrl, proportion)

        self._register_field(
            name=name,
            ctrl=ctrl,
            required=required,
            parser=parser,
            default=default
        )

        return ctrl

    def combo(
            self,
            name: str,
            label_key: str,
            choices: list,
            value: str = "",
            required: bool = False,
            parser: Callable[[Any], Any] | None = None,
            default: Any = None,
            style=wx.CB_DROPDOWN,
            size=None,
            proportion=0
    ) -> wx.ComboBox:
        ctrl = wx.ComboBox(
            self.parent,
            choices=choices,
            value=str(value),
            style=style,
            size=size or self.default_size
        )
        ctrl.SetFont(self.font)

        # raw value = текст в поле
        ctrl.GetValue = ctrl.GetValue  # явно, для симметрии

        lbl = self._create_label(label_key)
        self._add_row(lbl, ctrl, proportion)

        self._register_field(
            name=name,
            ctrl=ctrl,
            required=required,
            parser=parser,
            default=default
        )

        return ctrl


# ----------------------------------------------------------------------
# Локализуемые обёртки для стандартных контролов
# ----------------------------------------------------------------------

class LocalizableStaticBox:
    """
    Обёртка для wx.StaticBox, чтобы поддерживать динамическую локализацию
    через BaseContentPanel.register_localizable()
    """
    def __init__(self, box: wx.StaticBox, key: str):
        self.box = box
        self.key = key

    def update_language(self):
        self.box.SetLabel(loc.get(self.key))


class LocalizableButton:
    """
    Обёртка для wx.Button / GenButton, чтобы поддерживать динамическую локализацию
    через BaseContentPanel.register_localizable()
    """
    def __init__(self, button: wx.Button, key: str):
        self.button = button
        self.key = key

    def update_language(self):
        self.button.SetLabel(loc.get(self.key))

