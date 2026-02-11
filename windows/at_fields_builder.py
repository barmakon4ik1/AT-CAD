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
    - типовые строки: метка + контрол
    - комбинированные строки: метка + несколько контролов
    - поддержка локализации, регистрации и единого стиля
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
        self.default_size = default_size
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

    def _add_row(self, items: List[Union[wx.Window, str]], spacing=True) -> wx.BoxSizer:
        """
        Универсальная строка с несколькими элементами.
        Аргументы:
            items — список элементов (контролов или ключей меток)
            spacing — добавлять растягиватель между элементами для выравнивания
        Возвращает созданный BoxSizer.
        """
        row = wx.BoxSizer(wx.HORIZONTAL)
        for i, item in enumerate(items):
            if isinstance(item, str):
                # строка = ключ локализации -> создаём StaticText
                ctrl = self._create_label(item)
            else:
                ctrl = item
                ctrl.SetFont(self.font)

            row.Add(ctrl, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, self.label_pad)

            # Добавляем растягиватель после всех кроме последнего
            if spacing and i < len(items) - 1:
                row.AddStretchSpacer()

        self.sizer.Add(row, 0, wx.EXPAND | wx.ALL, self.row_border)
        return row

    # ------------------------------------------------------------------
    # Локализация
    # ------------------------------------------------------------------

    def update_language(self) -> None:
        """Обновляет подписи всех локализуемых элементов на текущий язык."""
        for key, ctrl in self._localizables.items():
            if hasattr(ctrl, "SetLabel"):
                ctrl.SetLabel(loc.get(key, key))

    # ------------------------------------------------------------------
    # Методы создания стандартных контролов
    # ------------------------------------------------------------------
    def create_label(self, label_key: str) -> wx.StaticText:
        """Создаёт локализованную метку (StaticText)."""
        return self._create_label(label_key)

    def text(self, name: str, label_key: str, value: str = "", required=False,
             parser: Optional[Callable] = None, default: Any = None,
             size=None) -> wx.TextCtrl:
        """Однострочное текстовое поле с меткой."""
        ctrl = wx.TextCtrl(self.parent, value=str(value),
                           size=wx.Size(*(size or self.default_size)))
        ctrl.SetFont(self.font)
        self._register_field(name, ctrl, required, parser, default)
        self._add_row([label_key, ctrl])
        return ctrl

    def multiline_text(self, name: str, label_key: str, value: str = "", required=False,
                       parser: Optional[Callable] = None, default: Any = None,
                       size=None) -> wx.TextCtrl:
        """Многострочное текстовое поле с меткой."""
        ctrl = wx.TextCtrl(self.parent, value=value, style=wx.TE_MULTILINE,
                           size=wx.Size(*(size or self.default_size)))
        ctrl.SetFont(self.font)
        self._register_field(name, ctrl, required, parser, default)
        self._add_row([label_key, ctrl])
        return ctrl

    def choice(self, name: str, label_key: str, choices: list[str],
               selection: int = 0, required=False, parser: Optional[Callable] = None,
               default: Any = None) -> wx.Choice:
        """Выбор из списка (wx.Choice) с меткой."""
        ctrl = wx.Choice(self.parent, choices=choices)
        ctrl.SetFont(self.font)
        if choices:
            ctrl.SetSelection(selection)

        def getter():
            idx = ctrl.GetSelection()
            if idx == wx.NOT_FOUND:
                return ""
            return ctrl.GetString(idx)

        def setter(v):
            if v in ctrl.GetItems():
                ctrl.SetStringSelection(v)
            else:
                ctrl.SetSelection(wx.NOT_FOUND)

        self._register_field(name, ctrl, required, parser, default, getter, setter)
        self._add_row([label_key, ctrl])
        return ctrl

    def combo(self, name: str, label_key: str, choices: list[str], value="",
              required=False, parser: Optional[Callable] = None,
              default: Any = None, style=wx.CB_DROPDOWN) -> wx.ComboBox:
        """Комбинированный список (wx.ComboBox) с меткой."""
        ctrl = wx.ComboBox(self.parent, choices=choices, value=str(value), style=style)
        ctrl.SetFont(self.font)
        self._register_field(name, ctrl, required, parser, default)
        self._add_row([label_key, ctrl])
        return ctrl

    # ------------------------------------------------------------------
    # Контейнеры и кнопки
    # ------------------------------------------------------------------

    def static_box(self, box_key: str, orient=wx.VERTICAL, proportion=0,
                   flag=wx.EXPAND | wx.ALL, border=5) -> wx.StaticBoxSizer:
        """Создаёт StaticBox с локализуемым заголовком."""
        box = wx.StaticBox(self.parent, label=loc.get(box_key, box_key))
        box.SetFont(self.font)
        self._localizables[box_key] = box
        sizer = wx.StaticBoxSizer(box, orient)
        self.sizer.Add(sizer, proportion, flag, border)
        return sizer

    def button(self, label_key: str, style=0, size=None) -> wx.Button:
        """Создаёт кнопку и регистрирует для локализации."""
        btn = wx.Button(self.parent, label=loc.get(label_key, label_key), style=style)
        btn.SetFont(self.font)
        self._localizables[label_key] = btn
        return btn

    def row_label_field_field(
            self,
            name1: str, label_key1: str, value1: str = "", required1=False,
            parser1: Optional[Callable] = None, default1: Any = None,
            name2: str = "", value2: str = "", required2=False,
            parser2: Optional[Callable] = None, default2: Any = None,
    ) -> tuple[wx.TextCtrl, wx.TextCtrl]:
        """Создаёт строку: метка + поле + поле"""
        ctrl1 = wx.TextCtrl(self.parent, value=str(value1),
                            size=wx.Size(*self.default_size))
        ctrl1.SetFont(self.font)
        self._register_field(name1, ctrl1, required1, parser1, default1)

        ctrl2 = wx.TextCtrl(self.parent, value=str(value2),
                            size=wx.Size(*self.default_size))
        ctrl2.SetFont(self.font)
        if name2:
            self._register_field(name2, ctrl2, required2, parser2, default2)

        self._add_row([label_key1, ctrl1, ctrl2])
        return ctrl1, ctrl2

    def row_label_combo_field(
            self,
            name_combo: str, label_key: str, choices: list[str], selection=0,
            required_combo=False, parser_combo: Optional[Callable] = None,
            default_combo: Any = None,
            name_field: str = "", value_field: str = "",
            required_field=False, parser_field: Optional[Callable] = None,
            default_field: Any = None,
    ) -> tuple[wx.ComboBox, wx.TextCtrl]:
        """Создаёт строку: метка + комбобокс + поле"""
        combo = wx.ComboBox(self.parent, choices=choices,
                            value=choices[selection] if choices else "",
                            style=wx.CB_DROPDOWN)
        combo.SetFont(self.font)
        self._register_field(name_combo, combo, required_combo, parser_combo, default_combo)

        field = wx.TextCtrl(self.parent, value=value_field,
                            size=wx.Size(*self.default_size))
        field.SetFont(self.font)
        if name_field:
            self._register_field(name_field, field, required_field, parser_field, default_field)

        self._add_row([label_key, combo, field])
        return combo, field

    def row_label_combo_combo(
            self,
            name1: str, name2: str, label_key: str,
            choices1: list[str], choices2: list[str],
            selection1=0, selection2=0,
            required1=False, required2=False,
            parser1: Optional[Callable] = None, parser2: Optional[Callable] = None,
            default1: Any = None, default2: Any = None,
    ) -> tuple[wx.ComboBox, wx.ComboBox]:
        """Создаёт строку: метка + комбобокс + комбобокс"""
        combo1 = wx.ComboBox(self.parent, choices=choices1,
                             value=choices1[selection1] if choices1 else "",
                             style=wx.CB_DROPDOWN)
        combo1.SetFont(self.font)
        self._register_field(name1, combo1, required1, parser1, default1)

        combo2 = wx.ComboBox(self.parent, choices=choices2,
                             value=choices2[selection2] if choices2 else "",
                             style=wx.CB_DROPDOWN)
        combo2.SetFont(self.font)
        self._register_field(name2, combo2, required2, parser2, default2)

        self._add_row([label_key, combo1, combo2])
        return combo1, combo2

    def row_label_field(
            self,
            name: str, label_key: str,
            value: str = "", required=False,
            parser: Optional[Callable] = None,
            default: Any = None,
    ) -> wx.TextCtrl:
        """Создаёт строку: метка + поле с растягивателем"""
        ctrl = wx.TextCtrl(self.parent, value=value,
                           size=wx.Size(*self.default_size))
        ctrl.SetFont(self.font)
        self._register_field(name, ctrl, required, parser, default)
        self._add_row([label_key, ctrl])
        return ctrl

    def row_custom(self, items: List[Union[wx.Window, str]]) -> wx.BoxSizer:
        """
        Универсальная строка с произвольными элементами.
        Позволяет комбинировать кнопки, поля, метки и др.
        """
        return self._add_row(items)

    # ------------------------------------------------------------------
    # Регистрация поля в форме
    # ------------------------------------------------------------------

    def _register_field(self, name: str, ctrl: wx.Window, required=False,
                        parser: Optional[Callable] = None, default: Any = None,
                        getter: Optional[Callable] = None, setter: Optional[Callable] = None):
        """Вспомогательный метод: регистрация поля в FormBuilder + setattr на parent."""
        if self.form:
            self.form.register(name, ctrl, required, parser, default, getter, setter)
        setattr(self.parent, name, ctrl)
