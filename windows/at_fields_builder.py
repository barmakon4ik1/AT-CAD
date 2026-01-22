# windows/at_fields_builder.py
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

Сводная таблица полей формы (пример):

| Имя поля   | Тип контрола    | Обязательное | Значение по умолчанию | Парсер           |
|------------|-----------------|--------------|-----------------------|------------------|
| username   | wx.TextCtrl     | Да           | None                  | str.strip        |
| description| wx.TextCtrl     | Нет          | ""                    | None             |
| choice     | wx.Choice       | Да           | "Option1"             | None             |
| combo      | wx.ComboBox     | Нет          | "Default"             | None             |
"""

from typing import Any, Callable, Dict

import wx
from windows.at_window_utils import get_standard_font
from locales.at_translations import loc


class FormField:
    """
    Описание одного поля формы.

    Атрибуты:
    - name: имя поля
    - ctrl: контрол wx.Control
    - required: обязательно ли заполнение
    - parser: функция для преобразования значения
    - default: значение по умолчанию
    """

    def __init__(
        self,
        name: str,
        ctrl: wx.Window,
        required: bool = False,
        parser: Callable[[str], Any] | None = None,
        default: Any = None,
        getter: Callable[[], Any]|None = None
    ):
        self.name = name
        self.ctrl = ctrl
        self.required = required
        self.parser = parser
        self.default = default
        self.getter = getter

    def get_raw(self):
        """Возвращает сырое значение из контрола."""
        return self.getter() if self.getter else self.ctrl.GetValue()

    def get_value(self):
        """
        Возвращает обработанное значение поля:
        - если пустое и есть default — возвращает default
        - если пустое и поле обязательное — вызывает ValueError
        - если указан parser — возвращает результат parser(raw)
        - иначе — сырое значение
        """
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
    Управление формой.

    Позволяет:
    - регистрировать поля
    - собирать данные из всех полей
    - очищать форму
    - получать сводную таблицу полей (для документации и отладки)
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
        getter = None
    ):
        """Регистрирует поле формы."""
        self.fields[name] = FormField(
            name=name,
            ctrl=ctrl,
            required=required,
            parser=parser,
            default=default,
            getter=getter
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

    def clear(self):
        """Очищает все поля формы."""
        for field in self.fields.values():
            field.ctrl.SetValue("")

    # ------------------------------------------------------------------
    # Документация / отладка
    # ------------------------------------------------------------------

    def get_fields_table(self) -> str:
        """
        Возвращает сводную таблицу зарегистрированных полей в формате Markdown.

        Удобно для:
        - документации
        - отладки
        - вывода в лог
        """
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
                else repr(field.parser)
                if field.parser
                else ""
            )

            lines.append(
                f"| {name} | {ctrl_type} | {required} | {default} | {parser} |"
            )

        return "\n".join(lines)

    def print_fields_table(self):
        """Печатает таблицу полей в stdout."""
        print(self.get_fields_table())

    def as_dict_schema(self) -> Dict[str, Dict[str, Any]]:
        """
        Возвращает описание формы в виде словаря.

        Удобно для:
        - логирования
        - сериализации
        - тестов
        """
        return {
            name: {
                "control": type(field.ctrl).__name__,
                "required": field.required,
                "default": field.default,
                "parser": getattr(field.parser, "__name__", None),
            }
            for name, field in self.fields.items()
        }


class FieldBuilder:
    """
    Помощник для создания типовых строк формы:
    Метка + Контрол

    Поддерживает:
    - единый стиль
    - StretchSpacer для выравнивания
    - локализацию меток
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

        # Реестр меток для динамической локализации
        self._labels: Dict[str, wx.StaticText] = {}

    # ------------------------------------------------------------------
    # Внутренние методы
    # ------------------------------------------------------------------

    def _create_label(self, label_key: str) -> wx.StaticText:
        """Создаёт локализованную метку и сохраняет её для обновления языка."""
        lbl = wx.StaticText(
            self.parent,
            label=loc.get(label_key, label_key)
        )
        lbl.SetFont(self.font)

        lbl._label_key = label_key
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
        Обновляет подписи всех локализуемых элементов FieldBuilder.
        """
        for key, ctrl in self._labels.items():
            ctrl.SetLabel(loc.get(key, key))

    # ------------------------------------------------------------------
    # Создание контролов
    # ------------------------------------------------------------------
    def create_label(self, label_key: str) -> wx.StaticText:
        return self._create_label(label_key)

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
        """Создаёт однострочное текстовое поле с меткой."""
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
        """Создаёт многострочное текстовое поле с меткой."""
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
        """Вспомогательный метод регистрации поля в FormBuilder."""
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
        """Создаёт выбор из списка (wx.Choice) с меткой и регистрацией."""
        ctrl = wx.Choice(
            self.parent,
            choices=choices,
            size=size or self.default_size
        )
        ctrl.SetFont(self.font)

        if choices:
            ctrl.SetSelection(selection)

        # 👇 ЛОКАЛЬНАЯ функция, ТОЛЬКО здесь
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
                getter=value_getter  # ← ВОТ ГДЕ ОН ИСПОЛЬЗУЕТСЯ
            )

        setattr(self.parent, name, ctrl)
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
        """Создаёт комбинированный список (wx.ComboBox) с меткой и регистрацией."""
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

    # ------------------------------------------------------------------
    # StaticBox (группы полей)
    # ------------------------------------------------------------------

    def static_box(
            self,
            box_key: str,
            orient=wx.VERTICAL,
            proportion=0,
            flag=wx.EXPAND | wx.ALL,
            border=5
    ) -> wx.StaticBoxSizer:
        """
        Создаёт wx.StaticBoxSizer с локализуемым заголовком
        и делает его текущим контейнером для добавления полей.

        Назначение:
        - логическое группирование полей формы
        - единый стиль
        - поддержка динамической локализации

        Args:
            box_key: ключ локализации заголовка StaticBox
            orient: ориентация (wx.VERTICAL / wx.HORIZONTAL)
            proportion: параметр Add() для родительского sizer
            flag: флаги компоновки
            border: отступы

        Returns:
            wx.StaticBoxSizer: созданный sizer
        """
        box = wx.StaticBox(
            self.parent,
            label=loc.get(box_key, box_key)
        )
        box.SetFont(self.font)

        # регистрируем StaticBox для смены языка
        self._labels[box_key] = box

        sizer = wx.StaticBoxSizer(box, orient)

        # добавляем в текущий целевой sizer
        self.sizer.Add(sizer, proportion, flag, border)

        return sizer



# ----------------------------------------------------------------------
# Локализуемые обёртки для стандартных контролов
# ----------------------------------------------------------------------

class LocalizableStaticBox:
    """
    Обёртка для wx.StaticBox для поддержки динамической локализации
    через BaseContentPanel.register_localizable().
    """
    def __init__(self, box: wx.StaticBox, key: str):
        self.box = box
        self.key = key

    def update_language(self):
        """Обновляет надпись StaticBox на текущий язык."""
        self.box.SetLabel(loc.get(self.key))


class LocalizableButton:
    """
    Обёртка для wx.Button / GenButton для поддержки динамической локализации
    через BaseContentPanel.register_localizable().
    """
    def __init__(self, button: wx.Button, key: str):
        self.button = button
        self.key = key

    def update_language(self):
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