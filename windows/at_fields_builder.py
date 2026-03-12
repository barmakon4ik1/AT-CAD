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

from errors.at_errors import DataError
from windows.at_window_utils import style_gen_button_v2
from config.at_config import FORM_CONFIG
from locales.at_translations import loc
from windows.at_gui_utils import get_standard_font


# ----------------------------------------------------------------------
# FormField: описание поля формы
# ----------------------------------------------------------------------
class FormField:
    """Описание одного поля формы."""
    ctrl: wx.Window

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
        self.fields = None
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

    def get_ctrl(self, name: str) -> Optional[wx.Window]:
        field: Optional[FormField] = self.fields.get(name)
        if field is None:
            return None
        return field.ctrl


# ----------------------------------------------------------------------
# FormBuilder: управление формой и регистрация полей
# ----------------------------------------------------------------------
class FormBuilder:
    """Класс для регистрации полей формы и сбора данных."""

    def __init__(self, panel: wx.Window):
        self.panel = panel
        self.fields: Dict[str, FormField] = {}
        self._field_configs: Dict[str, Dict[str, Any]] = {}

    def register(
            self,
            name: str,
            ctrl: wx.Window,
            required: bool = False,
            parser: Optional[Callable[[Any], Any]] = None,
            default: Any = None,
            getter: Optional[Callable[[], Any]] = None,
            setter: Optional[Callable[[Any], None]] = None,
            config: Optional[Dict[str, Any]] = None,
    ) -> wx.Window:
        """
        Регистрирует поле формы.

        :param name: имя поля
        :param ctrl: wx-контрол
        :param required: обязательное поле
        :param parser: функция преобразования значения
        :param default: значение по умолчанию
        :param getter: кастомный getter
        :param setter: кастомный setter
        :param config: декларативная конфигурация (JSON-схема)
        """
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

        # сохраняем декларативную конфигурацию (если есть)
        if config:
            self._field_configs[name] = config

        return ctrl

    def reset(self):
        """
        Сброс формы к значениям по умолчанию
        с учётом декларативной схемы.
        """
        self._purge_dead_fields()

        for name, field in self.fields.items():

            cfg = self._field_configs.get(name, {})

            # приоритет — JSON default
            if "default" in cfg:
                field.set_value(cfg["default"])

            # затем default из FormField
            elif field.default is not None:
                field.set_value(field.default)

            # иначе — очистка
            else:
                field.set_value("")

    def collect(self) -> dict[Any, Any] | None:
        """
        Собирает значения всех полей формы в словарь.

        Дополнительно:
        - выполняет стандартную валидацию FormField
        - выполняет JSON-валидацию (validators из config)
        """
        self._purge_dead_fields()

        data = {}

        for name, field in self.fields.items():

            try:
                value = field.get_value()
            except ValueError as e:
                wx.MessageBox(str(e), "Validation error", wx.OK | wx.ICON_ERROR)
                return None

            # -----------------------------------------------------
            # JSON-валидация (если поле зарегистрировано с config)
            # -----------------------------------------------------
            cfg = self._field_configs.get(name, {})
            validators = cfg.get("validators", [])

            if value not in (None, ""):

                if "float" in validators:
                    try:
                        float(value)
                    except (ValueError, TypeError):
                        wx.MessageBox(
                            f"Field '{name}' must be a number",
                            "Validation error",
                            wx.OK | wx.ICON_ERROR
                        )
                        return None

                if "positive" in validators:
                    try:
                        if float(value) <= 0:
                            raise ValueError
                    except DataError:
                        wx.MessageBox(
                            f"Field '{name}' must be positive",
                            "Validation error",
                            wx.OK | wx.ICON_ERROR
                        )
                        return None

            data[name] = value

        return data

    def clear(self):
        """
        Очистка формы.

        Использует reset(), чтобы поведение было единым
        для декларативной и обычной схемы.
        """
        self.reset()

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

    @staticmethod
    def _ctrl_alive(ctrl) -> bool:
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

    def set_value(self, name: str, value) -> None:
        """
        Установка значения контрола по имени.
        """
        field = self.fields.get(name)
        if field is None:
            raise KeyError(f"Field '{name}' not found.")

        ctrl: wx.Window = field.ctrl  # <-- берём контрол из FormField

        if isinstance(ctrl, wx.TextCtrl):
            ctrl.SetValue(str(value))

        elif isinstance(ctrl, wx.ComboBox):
            ctrl.SetValue(str(value))

        elif isinstance(ctrl, wx.CheckBox):
            ctrl.SetValue(bool(value))

        else:
            if hasattr(ctrl, "SetValue"):
                ctrl.SetValue(value)
            else:
                raise TypeError(f"Unsupported control type for '{name}'")


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

        self.controls = {}
        self.dependencies = []

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
        bind_float_input(ctrl)
        self._register_field(name, ctrl, required, parser, default)
        self.row(label_key, [ctrl])
        return ctrl

    # ------------------------------------------------------------------
    # Combo с меткой, безопасно для readonly и editable
    # ------------------------------------------------------------------
    def combo(self, name: str, label_key: str, choices: list[str], value="",
              required=False, parser: Optional[Callable] = None,
              default: Any = None, style=wx.CB_DROPDOWN) -> wx.ComboBox:
        """
        Создаёт ComboBox с меткой и безопасной инициализацией:
        - readonly (CB_READONLY) не вызывает SetInsertionPoint/SetSelection
        - editable (CB_DROPDOWN) курсор ставится в конец, выделение снимается
        """
        ctrl = wx.ComboBox(
            self.parent,
            choices=choices,
            value=value,
            style=style,
            size=self.default_size
        )

        self._register_field(name, ctrl, required, parser, default)
        self.row(label_key, [ctrl])

        # --- безопасная установка курсора и снятие выделения для editable ---
        if not (style & wx.CB_READONLY):
            try:
                ctrl.SetSelection(wx.NOT_FOUND)
                ctrl.SetInsertionPointEnd()
            except RuntimeError:
                pass  # объект может быть уже удалён

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
        Универсальная строка формы: метка слева + произвольный набор элементов справа.

        Поддерживает:
            • bind (через self.form + _register_field)
            • required / parser / default
            • условную видимость и enabled
            • выбор list[str] и list[dict]
            • восстановление корректной работы ComboBox

        ------------------------------------------------------------------
        ПРИМЕР ИСПОЛЬЗОВАНИЯ
        ------------------------------------------------------------------

            fb.universal_row("material_label", [
                {
                    "type": "combo",
                    "name": "material",
                    "choices": [
                        {"label": "Steel", "value": "S235"},
                        {"label": "Aluminium", "value": "AL"},
                    ],
                    "required": True
                },
                {
                    "type": "text",
                    "name": "density",
                }
            ])

        ------------------------------------------------------------------
        ПАРАМЕТРЫ ЭЛЕМЕНТА (dict)
        ------------------------------------------------------------------

        Базовые:
            type: "text" | "float" | "combo" | "choice" |
                  "button" | "checkbox" | "label" | "info"
            name: имя поля (для регистрации в self.form)
            value: начальное значение
            required: bool
            parser: callable
            default: значение по умолчанию

        Для combo/choice:
            choices:
                list[str]
                ИЛИ
                list[{"label": str, "value": Any}]
            selection: индекс
            readonly: bool

        Для button:
            label: текст
            callback: обработчик
            rows: множитель высоты

        Состояние:
            readonly: bool
            enabled: bool
            visible: bool
            tooltip: str
            min_size: (w, h)
            max_size: (w, h)

        Возвращает:
            list[wx.Window] — созданные контролы.
        """

        spacing = spacing if spacing is not None else self.label_pad
        row = wx.BoxSizer(wx.HORIZONTAL)
        created_controls = []

        # ---------------------------------------------------------
        # Метка слева
        # ---------------------------------------------------------
        if label_key:
            lbl = self._create_label(label_key)
            row.Add(lbl, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)

        if align_right:
            row.AddStretchSpacer(1)

        # =========================================================
        # СОЗДАНИЕ ЭЛЕМЕНТОВ
        # =========================================================
        for i, elem in enumerate(elements):
            elem_type = elem.get("type", "text")
            ctrl = None

            size = elem.get("size", self.default_size)
            if isinstance(size, tuple):
                size = wx.Size(*size)

            # -----------------------------------------------------
            # TEXT / FLOAT
            # -----------------------------------------------------
            if elem_type in ("text", "float"):
                ctrl = wx.TextCtrl(
                    self.parent,
                    value=str(elem.get("value", "")),
                    size=size
                )
                # --- автоматически привязываем фильтр float для float-полей ---
                if elem_type == "float":
                    bind_float_input(ctrl)

                parser = elem.get("parser")
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

            # -----------------------------------------------------
            # LABEL / INFO
            # -----------------------------------------------------
            elif elem_type in ("label", "info"):
                ctrl = wx.StaticText(
                    self.parent,
                    label=str(elem.get("value", ""))
                )

                if "wrap" in elem:
                    ctrl.Wrap(elem["wrap"])

            # -----------------------------------------------------
            # COMBO / CHOICE (исправлено!)
            # -----------------------------------------------------
            elif elem_type in ("combo", "choice"):

                raw_choices = elem.get("choices", [])

                # --- Нормализация choices ---
                if raw_choices and isinstance(raw_choices[0], dict):
                    labels = [c["label"] for c in raw_choices]
                    values = [c["value"] for c in raw_choices]
                else:
                    labels = list(raw_choices)
                    values = list(raw_choices)

                if elem_type == "combo":
                    readonly = elem.get("readonly", False)
                    style = wx.CB_READONLY if readonly else wx.CB_DROPDOWN
                    ctrl = wx.ComboBox(self.parent, choices=labels, style=style, size=size)

                    # --- выбор по value ---
                    value = elem.get("value")
                    if value in values:
                        ctrl.SetSelection(values.index(value))
                    elif labels:
                        ctrl.SetSelection(elem.get("selection", 0))

                    # безопасно: только для editable
                    if not readonly:
                        try:
                            ctrl.SetSelection(wx.NOT_FOUND)
                            ctrl.SetInsertionPointEnd()
                        except RuntimeError:
                            pass

                # --- сохраняем mapping ---
                ctrl._at_values = values

                if "name" in elem and self.form:
                    self._register_field(
                        elem["name"],
                        ctrl,
                        elem.get("required", False),
                        elem.get("parser"),
                        elem.get("default")
                    )

            # -----------------------------------------------------
            # BUTTON
            # -----------------------------------------------------
            elif elem_type == "button":
                base_size = size
                rows = elem.get("rows", 1)

                if rows > 1 and base_size.height > 0:
                    size = wx.Size(base_size.width, base_size.height * rows)

                ctrl = wx.Button(
                    self.parent,
                    label=elem.get("label", ""),
                    size=size
                )

                if "callback" in elem and callable(elem["callback"]):
                    ctrl.Bind(wx.EVT_BUTTON, elem["callback"])

                style_gen_button_v2(
                    btn=ctrl,
                    normal_bg=elem.get("bg_color", "#3498db"),
                    text_color=elem.get("fg_color"),
                    bezel=elem.get("bezel", 1),
                    button_height=size.height,
                    font_size=elem.get("font_size"),
                    toggle=elem.get("toggle", False),
                )

                ctrl.Bind(
                    wx.EVT_SIZE,
                    lambda evt, b=ctrl: (wrap_button_label(b), evt.Skip())
                )

            # -----------------------------------------------------
            # CHECKBOX
            # -----------------------------------------------------
            elif elem_type == "checkbox":
                ctrl = wx.CheckBox(
                    self.parent,
                    label=elem.get("label", "")
                )

                if "value" in elem:
                    ctrl.SetValue(bool(elem["value"]))

                if "name" in elem and self.form:
                    self._register_field(
                        elem["name"],
                        ctrl,
                        elem.get("required", False),
                        elem.get("parser"),
                        elem.get("default")
                    )

            # =====================================================
            # ПОСТ-ОБРАБОТКА
            # =====================================================
            if ctrl:

                ctrl.SetFont(self.font)

                if elem.get("readonly") and isinstance(ctrl, wx.TextCtrl):
                    ctrl.SetEditable(False)

                if "enabled" in elem:
                    ctrl.Enable(bool(elem["enabled"]))

                if "visible" in elem:
                    ctrl.Show(bool(elem["visible"]))

                if "tooltip" in elem:
                    ctrl.SetToolTip(elem["tooltip"])

                if "min_size" in elem:
                    ms = elem["min_size"]
                    if isinstance(ms, tuple):
                        ms = wx.Size(*ms)
                    ctrl.SetMinSize(ms)

                if "max_size" in elem:
                    ms = elem["max_size"]
                    if isinstance(ms, tuple):
                        ms = wx.Size(*ms)
                    ctrl.SetMaxSize(ms)

                right_pad = spacing if i < len(elements) - 1 else 0

                flags = wx.RIGHT

                if elem.get("rows", 1) > 1:
                    flags |= wx.EXPAND
                else:
                    flags |= wx.ALIGN_CENTER_VERTICAL

                row.Add(
                    ctrl,
                    element_proportion,
                    flags,
                    right_pad
                )

                created_controls.append(ctrl)

                # -------------------------------------------------
                # BIND (явная привязка событий)
                # -------------------------------------------------
                bind_cfg = elem.get("bind")
                if bind_cfg and isinstance(bind_cfg, dict):
                    event = bind_cfg.get("event")
                    handler = bind_cfg.get("handler")

                    if event and handler:
                        ctrl.Bind(event, handler)

        self.sizer.Add(row, 0, wx.EXPAND | wx.ALL, self.row_border)
        self.parent.Layout()

        return created_controls

    def build_from_schema(self, schema: Dict[str, Any], data_sources: Dict[str, Any]):
        """
        Построение формы по JSON-схеме.
        """

        for section in schema.get("sections", []):

            box = self.static_box(section["label"])

            sub_builder = FieldBuilder(
                parent=self.parent,
                target_sizer=box,
                form=self.form
            )

            for field in section.get("fields", []):

                elements = []

                for elem in field.get("controls", []):

                    cfg = elem.copy()

                    if "choices_source" in cfg:
                        source_key = cfg.pop("choices_source")
                        cfg["choices"] = data_sources.get(source_key, [])

                    elements.append(cfg)

                sub_builder.universal_row(
                    field.get("label"),
                    elements
                )

            self.sizer.Add(box, 0, wx.EXPAND | wx.ALL, 5)

def wrap_button_label(btn: wx.Button, padding: int = 10):
    """
    Делает перенос текста по ширине кнопки.
    Работает после Layout().
    """
    label = btn.GetLabel()
    width = btn.GetClientSize().width - padding

    dc = wx.ClientDC(btn)
    dc.SetFont(btn.GetFont())

    words = label.split()
    lines = []
    current = ""

    for word in words:
        test = f"{current} {word}".strip()
        w, _ = dc.GetTextExtent(test)

        if w <= width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word

    if current:
        lines.append(current)

    btn.SetLabel("\n".join(lines))

def bind_float_input(ctrl: wx.TextCtrl):
    """
    Привязывает фильтр для float:
    - только цифры и одна точка/запятая
    - заменяет ',' на '.'
    - стрелки, backspace, delete работают
    - при ошибке ввод запрещен, звук сигнала
    """
    def on_char(event):
        key = event.GetKeyCode()
        allowed_control = (wx.WXK_BACK, wx.WXK_DELETE, wx.WXK_LEFT, wx.WXK_RIGHT, wx.WXK_TAB)
        if key in allowed_control:
            event.Skip()
            return

        char = chr(key)
        if char.isdigit():
            event.Skip()
            return

        if char in ".,":  # одна точка или запятая
            value = ctrl.GetValue()
            if "." in value:  # точка уже есть
                wx.Bell()
                return
            event.Skip()
            return

        wx.Bell()
        return

    ctrl.Bind(wx.EVT_CHAR, on_char)


def normalize_input(
        raw: dict,
        key: str,
        default: float | None = None,
        min_value: float | None = None,
        form: Optional[FormBuilder] = None
) -> float | None:
    """
    Приводит входные данные формы к числу (float).

    Args:
        raw: словарь collect() из формы
        key: имя поля
        default: значение по умолчанию
        min_value: нижнее ограничение
        form: FormBuilder для возврата фокуса при ошибке

    Returns:
        float или default
    """
    try:
        value = parse_float(raw.get(key))
    except ValueError:
        wx.MessageBox(f"Ошибка ввода числа в поле '{key}', проверьте ввод", "Ошибка", wx.OK | wx.ICON_ERROR)
        if form and key in form.fields:
            form.fields[key].ctrl.SetFocus()
        return default

    if value is None:
        return default

    if min_value is not None and value < min_value:
        wx.MessageBox(f"Значение поля '{key}' должно быть >= {min_value}", "Ошибка ввода", wx.OK | wx.ICON_ERROR)
        if form and key in form.fields:
            form.fields[key].ctrl.SetFocus()
        return default

    return value


def parse_float(value: str) -> float | None:
    """
    Преобразует строку в float.
    Поддерживает ',' и '.' как десятичный разделитель.
    Возвращает None для пустой строки.
    Вызывает ValueError при некорректном формате.
    """
    if value is None:
        return None

    cleaned = str(value).strip().replace(",", ".")

    if not cleaned:
        return None

    return float(cleaned)

def normalize_inputs(raw: dict, schema: dict) -> dict:
    """
    Нормализует сразу несколько полей формы по описанию схемы.

    Args:
        raw:
            Словарь "сырых" данных формы (обычно результат form.collect()).

        schema:
            Словарь описания полей.

            Формат элемента схемы:

            {
                "field_name": {
                    "default": float | None,
                    "min_value": float | None,
                    "doc": str
                }
            }

            Все параметры, кроме имени поля, необязательны.

    Returns:
        dict
            Словарь нормализованных данных.

    Raises:
        ValueError:
            Если одно из значений невозможно преобразовать в float.

    ------------------------------------------------------------
    ПРИМЕР ОПИСАНИЯ СХЕМЫ
    ------------------------------------------------------------

    FIELD_SCHEMA = {

        # Основная длина
        "length": {
            "default": 0.0,
            "min_value": 0.0,
            "doc": "Основная длина мостика"
        },

        # Смещение
        "l1": {
            "default": 0.0,
            "min_value": 0.0,
            "doc": "Смещение таблички"
        },

        # Диаметры
        "shell_diameter1": {
            "min_value": 0.0,
            "doc": "Диаметр оболочки 1"
        },

        "shell_diameter2": {
            "min_value": 0.0,
            "doc": "Диаметр оболочки 2"
        },

        # Угол
        "edge_angle": {
            "min_value": 0.0,
            "doc": "Угол кромки"
        }
    }

    ------------------------------------------------------------
    ПРИМЕР ИСПОЛЬЗОВАНИЯ
    ------------------------------------------------------------

    raw = form.collect()

    data = normalize_inputs(raw, FIELD_SCHEMA)

    L = data["length"]
    L1 = data["l1"]
    D1 = data["shell_diameter1"]
    D2 = data["shell_diameter2"]
    angle = data["edge_angle"]

    После нормализации гарантируется:

        L >= 0
        L1 >= 0
        D1 >= 0
        D2 >= 0
        angle >= 0

    Если пользователь ввёл отрицательное значение,
    оно будет автоматически приведено к min_value.

    Если поле пустое — используется default.
    ------------------------------------------------------------
    """

    result = {}

    for key, params in schema.items():
        result[key] = normalize_input(
            raw,
            key,
            default=params.get("default"),
            min_value=params.get("min_value"),
        )

    return result