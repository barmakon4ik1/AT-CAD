# windows/at_fields_builder.py
# noinspection SpellCheckingInspection

"""
Модуль: at_fields_builder.py

Содержит классы и функции для построения форм в wxPython с поддержкой:
- типовых полей (текстовые, многострочные, выбор из списка, комбобокс)
- единообразного оформления
- локализации на лету
- валидации и парсинга данных
- удобного создания строк с произвольными комбинациями элементов

Основные классы:
- FormField — описание одного поля формы
- FormBuilder — сборка и управление формой
- FieldBuilder — удобная обёртка для добавления полей с метками и комбинированными строками
"""

from __future__ import annotations
from typing import Any, Callable, Dict, Optional, List, Union

import wx

from config.at_config import FORM_CONFIG
from locales.at_translations import loc
from windows.at_gui_utils import get_standard_font


# ----------------------------------------------------------------------
# FormField: описание поля формы
# ----------------------------------------------------------------------
class FormField:
    """Описание одного поля формы."""

    def __init__(
        self,
        name: str,
        ctrl: wx.Window,
        required: bool = False,
        parser: Optional[Callable[[Any], Any]] = None,
        default: Any = None,
        getter: Optional[Callable[[], Any]] = None,
        setter: Optional[Callable[[Any], None]] = None,
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
        if hasattr(self.ctrl, "GetValue"):
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
        if raw in (None, ""):
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
        """Устанавливает значение поля безопасно, через setter или стандартный контрол."""
        if self.setter:
            self.setter(value)
            return
        if isinstance(self.ctrl, wx.Choice):
            if value in self.ctrl.GetItems():
                self.ctrl.SetStringSelection(value)
            else:
                self.ctrl.SetSelection(wx.NOT_FOUND)
            return
        if hasattr(self.ctrl, "SetValue"):
            self.ctrl.SetValue(value)


# ----------------------------------------------------------------------
# FormBuilder: управление формой и регистрация полей
# ----------------------------------------------------------------------
class FormBuilder:
    """Класс для регистрации полей формы и сбора данных."""

    def __init__(self, panel: wx.Window):
        self.panel = panel
        self.fields: Dict[str, FormField] = {}

    def register(
        self,
        name: str,
        ctrl: wx.Window,
        required: bool = False,
        parser: Optional[Callable[[Any], Any]] = None,
        default: Any = None,
        getter: Optional[Callable[[], Any]] = None,
        setter: Optional[Callable[[Any], None]] = None,
    ) -> wx.Window:
        """Регистрирует поле формы."""
        self.fields[name] = FormField(
            name=name,
            ctrl=ctrl,
            required=required,
            parser=parser,
            default=default,
            getter=getter,
            setter=setter,
        )
        return ctrl

    def collect(self) -> Dict[str, Any]:
        """Собирает значения всех полей формы в словарь."""
        data = {}
        for name, field in self.fields.items():
            try:
                data[name] = field.get_value()
            except Exception as e:
                raise ValueError(f"Ошибка в поле '{name}': {e}") from e
        return data

    def clear(self) -> None:
        """Очищает все поля формы безопасно, используя set_value()."""
        for field in self.fields.values():
            field.set_value(field.default)

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
# FieldBuilder: создание элементов формы и комбинированных строк
# ----------------------------------------------------------------------
class FieldBuilder:
    """
    Класс для построения элементов формы:
    - стандартные строки: метка + контрол
    - комбинированные строки: метка + несколько контролов
    - поддержка локализации и регистрации полей в FormBuilder
    """

    def __init__(
        self,
        parent: wx.Window,
        target_sizer: wx.Sizer,
        form: Optional[FormBuilder] = None,
        default_size: tuple[int, int] = FORM_CONFIG["input_size"],
        label_right_padding: int = 10,
        row_border: int = 5
    ):
        self.parent = parent
        self.sizer = target_sizer
        self.form = form
        self.font = get_standard_font()
        self.default_size = wx.Size(*default_size)
        self.label_pad = label_right_padding
        self.row_border = row_border

        # Словарь всех локализуемых элементов
        self._localizables: Dict[str, wx.Window] = {}

    # ------------------------------------------------------------------
    # Вспомогательные методы
    # ------------------------------------------------------------------

    def _create_label(self, key: str) -> wx.StaticText:
        """Создаёт локализованную метку и сохраняет её для смены языка."""
        lbl = wx.StaticText(self.parent, label=loc.get(key, key))
        lbl.SetFont(self.font)
        self._localizables[key] = lbl
        return lbl

    # ------------------------------------------------------------------
    # Универсальная строка с произвольными контролами
    # ------------------------------------------------------------------
    def row(
            self,
            label_key: str,
            controls: list[wx.Window],
            spacing: int = None,
            label_proportion: int = 0,
            control_proportion: int = 0
    ) -> wx.BoxSizer:
        """
        Универсальная строка: метка слева + любые контролы справа с растягивателем между.

        :param label_key: ключ локализации для метки
        :param controls: список wx.Window элементов (TextCtrl, ComboBox, Button...)
        :param spacing: отступ между контролами
        :param label_proportion: пропорция для метки (BoxSizer)
        :param control_proportion: пропорция для контролов (BoxSizer)
        """
        spacing = spacing if spacing is not None else self.label_pad
        row = wx.BoxSizer(wx.HORIZONTAL)

        # Метка слева
        lbl = self._create_label(label_key)
        row.Add(lbl, label_proportion, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, spacing)

        # Растягиватель между меткой и контролами
        row.AddStretchSpacer(1)

        # Добавляем контролы справа с отступами
        for i, ctrl in enumerate(controls):
            ctrl.SetFont(self.font)
            right_pad = spacing if i < len(controls) - 1 else 0
            row.Add(ctrl, control_proportion, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, right_pad)

        self.sizer.Add(row, 0, wx.EXPAND | wx.ALL, self.row_border)
        return row

    # ------------------------------------------------------------------
    # Стандартные контролы
    # ------------------------------------------------------------------

    def text(self, name: str, label_key: str, value: str = "",
             required=False, parser: Optional[Callable] = None,
             default: Any = None) -> wx.TextCtrl:
        """Текстовое поле с меткой."""
        ctrl = wx.TextCtrl(self.parent, value=value, size=self.default_size)
        self._register_field(name, ctrl, required, parser, default)
        self.row(label_key, [ctrl])
        return ctrl

    def combo(self, name: str, label_key: str, choices: list[str], value="",
              required=False, parser: Optional[Callable] = None,
              default: Any = None, style=wx.CB_DROPDOWN) -> wx.ComboBox:
        """Комбобокс с меткой."""
        ctrl = wx.ComboBox(self.parent, choices=choices, value=value,
                           style=style, size=self.default_size)
        self._register_field(name, ctrl, required, parser, default)
        self.row(label_key, [ctrl])
        return ctrl

    def multiline_text(self, name: str, label_key: str, value: str = "",
                       required=False, parser: Optional[Callable] = None,
                       default: Any = None) -> wx.TextCtrl:
        """Многострочное текстовое поле с меткой."""
        ctrl = wx.TextCtrl(self.parent, value=value, style=wx.TE_MULTILINE,
                           size=self.default_size)
        self._register_field(name, ctrl, required, parser, default)
        self.row(label_key, [ctrl])
        return ctrl

    def choice(self, name: str, label_key: str, choices: list[str],
               selection: int = 0, required=False, parser: Optional[Callable] = None,
               default: Any = None) -> wx.Choice:
        """Выбор из списка (wx.Choice) с меткой."""
        ctrl = wx.Choice(self.parent, choices=choices)
        if choices:
            ctrl.SetSelection(selection)

        def getter():
            idx = ctrl.GetSelection()
            return "" if idx == wx.NOT_FOUND else ctrl.GetString(idx)

        def setter(v):
            if v in ctrl.GetItems():
                ctrl.SetStringSelection(v)
            else:
                ctrl.SetSelection(wx.NOT_FOUND)

        self._register_field(name, ctrl, required, parser, default, getter, setter)
        self.row(label_key, [ctrl])
        return ctrl

    def button(self, label_key: str, style=0, size=None) -> wx.Button:
        """Создаёт кнопку и регистрирует её для локализации."""
        btn = wx.Button(self.parent, label=loc.get(label_key, label_key),
                        style=style)
        btn.SetFont(self.font)
        self._localizables[label_key] = btn
        if size:
            btn.SetSize(size)
        return btn

    def static_box(self, box_key: str, orient=wx.VERTICAL,
                   proportion=0, flag=wx.EXPAND | wx.ALL, border=5) -> wx.StaticBoxSizer:
        """Создаёт StaticBox с локализуемым заголовком."""
        box = wx.StaticBox(self.parent, label=loc.get(box_key, box_key))
        box.SetFont(self.font)
        self._localizables[box_key] = box
        sizer = wx.StaticBoxSizer(box, orient)
        self.sizer.Add(sizer, proportion, flag, border)
        return sizer

    # ------------------------------------------------------------------
    # Локализация
    # ------------------------------------------------------------------
    def update_language(self) -> None:
        """Обновляет подписи всех локализуемых элементов на текущий язык."""
        for key, ctrl in self._localizables.items():
            if hasattr(ctrl, "SetLabel"):
                ctrl.SetLabel(loc.get(key, key))

    # ------------------------------------------------------------------
    # Регистрация поля в форме
    # ------------------------------------------------------------------
    def _register_field(self, name: str, ctrl: wx.Window, required=False,
                        parser: Optional[Callable] = None, default: Any = None,
                        getter: Optional[Callable] = None, setter: Optional[Callable] = None):
        """Регистрирует поле в FormBuilder и на parent."""
        if self.form:
            self.form.register(name, ctrl, required, parser, default, getter, setter)
        setattr(self.parent, name, ctrl)

    # ------------------------------------------------------------------
    # Быстрые обёртки над row
    # ------------------------------------------------------------------

    def row_text(self, name: str, label_key: str, value: str = "",
                 required=False, parser: Optional[Callable] = None,
                 default: Any = None) -> wx.TextCtrl:
        """Метку + одно текстовое поле."""
        ctrl = wx.TextCtrl(self.parent, value=value, size=self.default_size)
        self._register_field(name, ctrl, required, parser, default)
        self.row(label_key, [ctrl])
        return ctrl

    def row_combo(self, name: str, label_key: str, choices: list[str],
                  value="", required=False, parser: Optional[Callable] = None,
                  default: Any = None, style=wx.CB_DROPDOWN) -> wx.ComboBox:
        """Метку + одно комбобокс поле."""
        ctrl = wx.ComboBox(self.parent, choices=choices, value=value,
                           style=style, size=self.default_size)
        self._register_field(name, ctrl, required, parser, default)
        self.row(label_key, [ctrl])
        return ctrl

    # ------------------------------------------------------------------
    # Универсальная строка
    # ------------------------------------------------------------------
    def universal_row(
            self,
            label_key: str,
            elements: list[dict],
            spacing: int = None,
            label_proportion: int = 0,
            element_proportion: int = 0
    ) -> list[wx.Window]:
        """
        Универсальная строка: метка слева + любые элементы справа.

        Пример использования:
            fb.universal_row("order_label", [
                {"type": "text", "name": "order", "value": ""},
                {"type": "combo", "name": "material", "choices": ["Steel", "Al"], "value": "Steel"},
                {"type": "button", "label": "OK", "callback": self.on_ok}
            ])

        Параметры элементов:
            type: "text" | "combo" | "choice" | "button" | "checkbox"
            name: имя для регистрации в форме (для полей)
            value: начальное значение (для полей)
            choices: список вариантов (для combo/choice)
            selection: индекс выбранного элемента (для combo/choice)
            required: bool, обязательное поле (по умолчанию False)
            parser: функция преобразования значения
            default: значение по умолчанию
            label: текст кнопки/чекбокса
            callback: функция обработчика кнопки
        """
        spacing = spacing if spacing is not None else self.label_pad
        row = wx.BoxSizer(wx.HORIZONTAL)

        # Метка слева
        lbl = self._create_label(label_key)
        row.Add(lbl, label_proportion, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, spacing)

        # Растягиватель между меткой и контролами
        row.AddStretchSpacer(1)

        created_controls = []

        for i, elem in enumerate(elements):
            elem_type = elem.get("type", "text")
            ctrl: Optional[wx.Window] = None

            if elem_type == "text":
                ctrl = wx.TextCtrl(
                    self.parent,
                    value=str(elem.get("value", "")),
                    size=wx.Size(*self.default_size)
                )
                if "name" in elem and self.form:
                    self._register_field(
                        elem["name"], ctrl, elem.get("required", False),
                        elem.get("parser"), elem.get("default")
                    )

            elif elem_type in ("combo", "choice"):
                choices = elem.get("choices", [])
                value = elem.get("value", choices[0] if choices else "")
                style = wx.CB_DROPDOWN if elem_type == "combo" else 0
                ctrl = wx.ComboBox(
                    self.parent,
                    choices=choices,
                    value=str(value),
                    style=style,
                    size=wx.Size(*self.default_size)
                )
                if "name" in elem and self.form:
                    self._register_field(
                        elem["name"], ctrl, elem.get("required", False),
                        elem.get("parser"), elem.get("default")
                    )

            elif elem_type == "button":
                ctrl = wx.Button(
                    self.parent,
                    label=elem.get("label", "")
                )
                if "callback" in elem and callable(elem["callback"]):
                    ctrl.Bind(wx.EVT_BUTTON, elem["callback"])

            elif elem_type == "checkbox":
                ctrl = wx.CheckBox(
                    self.parent,
                    label=elem.get("label", "")
                )
                if "name" in elem and self.form:
                    self._register_field(
                        elem["name"], ctrl, elem.get("required", False),
                        elem.get("parser"), elem.get("default")
                    )

            if ctrl:
                ctrl.SetFont(self.font)
                right_pad = spacing if i < len(elements) - 1 else 0
                row.Add(ctrl, element_proportion, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, right_pad)
                created_controls.append(ctrl)

        self.sizer.Add(row, 0, wx.EXPAND | wx.ALL, self.row_border)
        return created_controls



