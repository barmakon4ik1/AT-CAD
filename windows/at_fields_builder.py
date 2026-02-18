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
from typing import Any, Callable, Dict, Optional
import wx
from wx.lib.buttons import GenButton

from windows.at_window_utils import parse_float, style_gen_button, style_gen_button_v2
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
        self.value_cache = ctrl.GetValue() if hasattr(ctrl, "GetValue") else None
        self.required = required
        self.parser = parser
        self.default = default
        self.getter = getter
        self.setter = setter

    def get_raw(self):
        # 1️⃣ если есть кастомный getter — используем его
        if self.getter:
            try:
                val = self.getter()
                self.value_cache = val
                return val
            except RuntimeError:
                return self.value_cache

        # 2️⃣ стандартный GetValue
        if self.ctrl and hasattr(self.ctrl, "GetValue"):
            try:
                val = self.ctrl.GetValue()
                self.value_cache = val
                return val
            except RuntimeError:
                pass

        # 3️⃣ fallback
        return self.value_cache

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
            return None

        value = self.parser(raw) if self.parser else raw

        if value is None and self.required:
            raise ValueError(
                loc.get("no_data_error", f"Field '{self.name}' is required")
            )

        return value

    def set_value(self, value: Any) -> None:
        """
        Устанавливает значение поля безопасно, через setter или стандартный контрол.

        Работает для:
            - wx.TextCtrl
            - wx.ComboBox
        Остальные контролы игнорируются.
        """
        if not self.ctrl:
            return

        # 1️⃣ кастомный setter приоритетен
        if self.setter:
            try:
                self.setter(value)
            except RuntimeError:
                pass
            return

        # 2️⃣ стандартные контролы
        try:
            if isinstance(self.ctrl, (wx.TextCtrl, wx.ComboBox)):
                self.ctrl.SetValue("" if value is None else str(value))
        except RuntimeError:
            pass


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
        self._purge_dead_fields()
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

    def collect(self) -> dict[Any, Any] | None:
        """Собирает значения всех полей формы в словарь."""
        self._purge_dead_fields()

        data = {}

        for name, field in self.fields.items():
            try:
                value = field.get_value()
            except ValueError as e:
                wx.MessageBox(str(e), "Validation error", wx.OK | wx.ICON_ERROR)
                return None

            data[name] = value

        return data

    def clear(self):
        """
        Сброс формы к значениям по умолчанию.
        """
        self._purge_dead_fields()

        for field in self.fields.values():
            if field.default is not None:
                field.set_value(field.default)
            else:
                field.set_value("")

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

    def _ctrl_alive(self, ctrl) -> bool:
        """
        Проверяет, существует ли wx-контрол.
        Безопасно для уже уничтоженных C++ объектов.
        """
        if not ctrl:
            return False
        try:
            if ctrl.IsBeingDeleted():
                return False
            ctrl.GetId()
            return True
        except RuntimeError:
            return False

    def _purge_dead_fields(self):
        """
        Удаляет из формы поля, чьи контролы уже уничтожены.
        """
        alive_fields = {}

        for name, field in self.fields.items():
            if self._ctrl_alive(field.ctrl):
                alive_fields[name] = field

        self.fields = alive_fields


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
            control_proportion: int = 0,
            align_right: bool = True
    ) -> wx.BoxSizer:
        """
        Универсальная строка: метка слева + любые контролы справа с растягивателем между.

        :param label_key: ключ локализации для метки
        :param controls: список wx.Window элементов (TextCtrl, ComboBox, Button...)
        :param spacing: отступ между контролами
        :param label_proportion: пропорция для метки (BoxSizer)
        :param control_proportion: пропорция для контролов (BoxSizer)
        :param align_right: True - выровнять справа / False - слева
        """
        spacing = spacing if spacing is not None else self.label_pad
        row = wx.BoxSizer(wx.HORIZONTAL)

        # Метка слева
        lbl = self._create_label(label_key)
        row.Add(lbl, label_proportion, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, spacing)

        # Растягиватель между меткой и контролами
        if align_right:
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

    def text_column(self, names, width=200, default=""):
        for name in names:
            self.universal_row(
                None,
                [{
                    "type": "float",
                    "name": name,
                    "value": default,
                    "default": default,
                    "required": False,
                    "size": (width, -1)
                }]
            )

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
            label_key: str | None,
            elements: list[dict],
            spacing: int = None,
            element_proportion: int = 0,
            align_right: bool = True
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
            - "depends_on": dict с ключами:
            - "ctrl" — контрол, от которого зависит элемент
            - "callback" — функция: (dependent_ctrl, master_ctrl) -> None
        """
        spacing = spacing if spacing is not None else self.label_pad
        row = wx.BoxSizer(wx.HORIZONTAL)
        created_controls = []

        # Метка слева
        if label_key:
            lbl = self._create_label(label_key)
            row.Add(lbl, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)

        # Растягиватель между меткой и контролами
        if align_right:
            row.AddStretchSpacer(1)

        for i, elem in enumerate(elements):
            elem_type = elem.get("type", "text")
            ctrl: Optional[wx.Window] = None
            size = elem.get("size", self.default_size)
            if isinstance(size, tuple):
                size = wx.Size(*size)

            if elem_type in ("text", "float"):
                ctrl = wx.TextCtrl(
                    self.parent,
                    value=str(elem.get("value", "")),
                    size=size
                )

                parser = elem.get("parser")

                # если тип float и parser не задан — используем встроенный
                if elem_type == "float" and parser is None:
                    parser = parse_float

                if "name" in elem and self.form:
                    self._register_field(
                        elem["name"],
                        ctrl,
                        elem.get("required", False),
                        parser,
                        elem.get("default")
                    )


            elif elem_type in ("combo", "choice"):
                choices = elem.get("choices", [])
                value = elem.get("value", choices[0] if choices else "")
                style = wx.CB_DROPDOWN if elem_type == "combo" else 0
                size = elem.get("size", self.default_size)
                if isinstance(size, tuple):
                    size = wx.Size(*size)
                ctrl = wx.ComboBox(
                    self.parent,
                    choices=choices,
                    value=str(value),
                    style=style,
                    size=size
                )
                if "name" in elem and self.form:
                    self._register_field(
                        elem["name"], ctrl, elem.get("required", False),
                        elem.get("parser"), elem.get("default")
                    )

            elif elem_type == "button":
                ctrl = GenButton(
                    self.parent,
                    label=elem.get("label", ""),
                    size=wx.Size(*elem["size"]) if "size" in elem else wx.DefaultSize
                )

                if "callback" in elem and callable(elem["callback"]):
                    ctrl.Bind(wx.EVT_BUTTON, elem["callback"])

                # --- ВАЖНО: стиль ---
                style_gen_button_v2(
                    btn=ctrl,
                    normal_bg=elem.get("bg_color", "#3498db"),
                    text_color=elem.get("fg_color"),
                    bezel=elem.get("bezel", 1),
                    button_height=elem.get("height", 0),
                    font_size=elem.get("font_size"),
                    toggle=elem.get("toggle", False),
                )

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

                # ── зависимость от другого контрола ──
                depends = elem.get("depends_on")
                if depends and "ctrl" in depends and "callback" in depends:
                    master_ctrl = depends["ctrl"]
                    cb = depends["callback"]
                    master_ctrl.Bind(wx.EVT_COMBOBOX, lambda evt, d=ctrl, m=master_ctrl, f=cb:
                    f(d, m))

        self.sizer.Add(row, 0, wx.EXPAND | wx.ALL, self.row_border)
        return created_controls


