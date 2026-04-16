"""
config.py
=========

Загрузка, нормализация и хранение конфигурации приложения K-Finder.

Зачем нужен
-----------
Этот модуль выносит все изменяемые параметры из кода во внешний JSON-файл.
Благодаря этому администратор может менять:
- пути к корневым папкам и Excel-файлам,
- параметры индексации,
- режим обновления при старте,
- размеры окон,
- оформление (цвета, шрифты),

не редактируя Python-код и не пересобирая launcher / exe.

Источники конфигурации
----------------------
1. Встроенные значения по умолчанию (DEFAULT_CONFIG)
2. Внешний файл data/config.json

Внешний JSON не обязан содержать все поля. Если какой-то ключ не указан,
используется значение по умолчанию.

Архитектура
-----------
Модуль предоставляет:
- dataclass-объекты по группам настроек;
- функцию load_config(), возвращающую AppSettings;
- простую валидацию и нормализацию.

Важно
-----
Этот модуль не должен создавать GUI, индексы или логгер.
Он отвечает только за конфигурацию.
"""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .paths import (
    CONFIG_FILE,
    K_INDEX_JSON,
    DXF_RANGES_JSON,
    DXF_EXCEL_INDEX_JSON,
    DXF_FILES_INDEX_JSON,
    APPNR_INDEX_JSON,
)


# ============================================================
# Значения по умолчанию
# ============================================================

DEFAULT_CONFIG: dict[str, Any] = {
    "paths": {
        # Корень папок заказов
        "root_dir": r"G:\Auftragsdokumente",

        # Excel с DXF-данными
        "dxf_excel_file": r"G:\Drawing\DXF-LASER\DXF-2017.xlsm",

        # Корень папок DXF/DWG-файлов
        "dxf_root_dir": r"G:\Drawing\DXF-LASER",

        # Excel с Apparate-Nr.
        "appnr_excel_file": r"G:\Auftragsdokumente\Apparate-Nr.xlsx",

        # Имя папки со скетчами внутри папки заказа
        "sketch_folder_name": "RP - dxf -Skizzen",
    },

    "indexing": {
        # Автоматическая частичная индексация при запуске программы.
        # По твоему требованию по умолчанию выключена.
        "auto_update_on_start": False,

        "k": {
            # Самый ранний год для полного сканирования K-папок
            "start_year": 2011,

            # Частичная индексация K:
            # сколько номеров назад проверять от текущего хвоста
            "tail_backtrack": 50,

            # Частичная индексация K:
            # сколько последних лет сканировать
            "tail_years_to_scan": 2,
        },

        "dxf": {
            # Нижняя граница DXF-номеров
            "min_dxf_no": 7801,

            # Верхняя граница полного rebuild DXF-файлового индекса
            "max_dxf_no": 12000,

            # Частичная индексация DXF:
            # сколько номеров назад проверять
            "file_tail_backtrack": 100,

            # Частичная индексация DXF:
            # сколько номеров вперёд проверять
            "file_tail_forward_scan": 100,
        },

        "appnr": {
            # Частичная индексация App.Nr.:
            # сколько числовых префиксов назад пересчитывать
            # относительно максимального известного prefix
            "tail_backtrack_prefix": 100,
        },
    },

    "ui": {
        # Размеры окон
        "window_size": [410, 500],
        "service_window_size": [500, 360],

        # Поведение
        "auto_open_single": False,
        "auto_show_single": True,
        "live_search_if_missing": True,

        # Цвета
        "colors": {
            "bg": "#508050",
            "btn_primary": "#2980b9",
            "btn_ok": "#27ae60",
            "btn_warn": "#e67e22",
            "btn_danger": "#c0392b",
            "btn_dark": "#2c3e50",
            "text": "#ffffff",
            "label": "#e8f5e9",
        },

        # Базовые размеры шрифтов
        "fonts": {
            "default_size": 10,
            "small_size": 9,
            "title_size": 12,
            "button_size": 10,
        },
    },

    # Пути JSON-индексов при желании тоже можно переопределять,
    # но по умолчанию они живут в data/.
    "data_files": {
        "k_index_json": str(K_INDEX_JSON),
        "dxf_ranges_json": str(DXF_RANGES_JSON),
        "dxf_excel_index_json": str(DXF_EXCEL_INDEX_JSON),
        "dxf_files_index_json": str(DXF_FILES_INDEX_JSON),
        "appnr_index_json": str(APPNR_INDEX_JSON),
    },
}


# ============================================================
# Dataclass-структуры
# ============================================================

@dataclass(frozen=True)
class PathsConfig:
    """
    Пути к основным рабочим ресурсам приложения.
    """
    root_dir: Path
    dxf_excel_file: Path
    dxf_root_dir: Path
    appnr_excel_file: Path
    sketch_folder_name: str


@dataclass(frozen=True)
class KIndexingConfig:
    """
    Параметры индексации K-папок.
    """
    start_year: int
    tail_backtrack: int
    tail_years_to_scan: int


@dataclass(frozen=True)
class DXFIndexingConfig:
    """
    Параметры индексации DXF.
    """
    min_dxf_no: int
    max_dxf_no: int
    file_tail_backtrack: int
    file_tail_forward_scan: int


@dataclass(frozen=True)
class AppNrIndexingConfig:
    """
    Параметры индексации Apparate-Nr.
    """
    tail_backtrack_prefix: int


@dataclass(frozen=True)
class IndexingConfig:
    """
    Общая группа настроек индексации.
    """
    auto_update_on_start: bool
    k: KIndexingConfig
    dxf: DXFIndexingConfig
    appnr: AppNrIndexingConfig


@dataclass(frozen=True)
class ColorsConfig:
    """
    Цветовая схема интерфейса.
    """
    bg: str
    btn_primary: str
    btn_ok: str
    btn_warn: str
    btn_danger: str
    btn_dark: str
    text: str
    label: str


@dataclass(frozen=True)
class FontsConfig:
    """
    Размеры базовых шрифтов интерфейса.
    """
    default_size: int
    small_size: int
    title_size: int
    button_size: int


@dataclass(frozen=True)
class UiConfig:
    """
    Настройки поведения и внешнего вида интерфейса.
    """
    window_size: tuple[int, int]
    service_window_size: tuple[int, int]
    auto_open_single: bool
    auto_show_single: bool
    live_search_if_missing: bool
    colors: ColorsConfig
    fonts: FontsConfig


@dataclass(frozen=True)
class DataFilesConfig:
    """
    Пути к JSON-индексам и другим служебным файлам данных.
    """
    k_index_json: Path
    dxf_ranges_json: Path
    dxf_excel_index_json: Path
    dxf_files_index_json: Path
    appnr_index_json: Path


@dataclass(frozen=True)
class AppSettings:
    """
    Корневой объект конфигурации приложения.

    Его следует передавать в приложение целиком и уже из него
    разбирать нужные подгруппы.
    """
    paths: PathsConfig
    indexing: IndexingConfig
    ui: UiConfig
    data_files: DataFilesConfig


# ============================================================
# Вспомогательные функции
# ============================================================

def _deep_update(base: dict, override: dict) -> dict:
    """
    Рекурсивно объединяет два словаря.

    Если ключ содержит словарь, объединение идёт вглубь.
    Иначе значение из override полностью заменяет значение base.
    """
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            base[key] = _deep_update(base[key], value)
        else:
            base[key] = value
    return base


def _as_path(value: str | Path) -> Path:
    """
    Нормализует строку/Path в объект Path.
    """
    return value if isinstance(value, Path) else Path(value)


def _as_int(value: Any, default: int) -> int:
    """
    Безопасно приводит значение к int.
    """
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_bool(value: Any, default: bool) -> bool:
    """
    Безопасно приводит значение к bool.

    Поддерживает:
    - True / False
    - 1 / 0
    - "true" / "false"
    - "yes" / "no"
    - "on" / "off"
    """
    if isinstance(value, bool):
        return value

    if isinstance(value, (int, float)):
        return bool(value)

    if isinstance(value, str):
        s = value.strip().lower()
        if s in {"1", "true", "yes", "on", "ja"}:
            return True
        if s in {"0", "false", "no", "off", "nein"}:
            return False

    return default


def _as_size(value: Any, default: tuple[int, int]) -> tuple[int, int]:
    """
    Приводит значение к размеру окна (width, height).
    """
    if isinstance(value, (list, tuple)) and len(value) == 2:
        return (
            _as_int(value[0], default[0]),
            _as_int(value[1], default[1]),
        )
    return default


# ============================================================
# Загрузка конфигурации
# ============================================================

def load_raw_config() -> dict[str, Any]:
    """
    Загружает итоговый словарь конфигурации.

    Алгоритм:
    1. Берём глубокую копию DEFAULT_CONFIG.
    2. Если data/config.json существует — читаем его.
    3. Накладываем внешний JSON поверх defaults.
    4. Возвращаем итоговый словарь.

    Ошибки чтения JSON поднимаются вверх как RuntimeError,
    чтобы их можно было показать пользователю в понятной форме.
    """
    cfg = copy.deepcopy(DEFAULT_CONFIG)

    if not CONFIG_FILE.is_file():
        return cfg

    try:
        with CONFIG_FILE.open("r", encoding="utf-8") as f:
            user_cfg = json.load(f)
    except OSError as e:
        raise RuntimeError(f"Konfigurationsdatei kann nicht gelesen werden: {CONFIG_FILE}\n{e}") from e
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Fehler in config.json:\n{e}") from e

    if not isinstance(user_cfg, dict):
        raise RuntimeError("config.json muss ein JSON-Objekt enthalten.")

    return _deep_update(cfg, user_cfg)


def load_config() -> AppSettings:
    """
    Загружает конфигурацию приложения и возвращает типизированный объект AppSettings.

    Эта функция — основной публичный вход в модуль конфигурации.
    Её следует вызывать один раз при старте программы.
    """
    raw = load_raw_config()

    # --------------------------------------------------------
    # Paths
    # --------------------------------------------------------
    raw_paths = raw["paths"]
    paths_cfg = PathsConfig(
        root_dir=_as_path(raw_paths["root_dir"]),
        dxf_excel_file=_as_path(raw_paths["dxf_excel_file"]),
        dxf_root_dir=_as_path(raw_paths["dxf_root_dir"]),
        appnr_excel_file=_as_path(raw_paths["appnr_excel_file"]),
        sketch_folder_name=str(raw_paths["sketch_folder_name"]),
    )

    # --------------------------------------------------------
    # Indexing / K
    # --------------------------------------------------------
    raw_indexing = raw["indexing"]
    raw_k = raw_indexing["k"]
    k_cfg = KIndexingConfig(
        start_year=_as_int(raw_k["start_year"], DEFAULT_CONFIG["indexing"]["k"]["start_year"]),
        tail_backtrack=_as_int(raw_k["tail_backtrack"], DEFAULT_CONFIG["indexing"]["k"]["tail_backtrack"]),
        tail_years_to_scan=_as_int(
            raw_k["tail_years_to_scan"],
            DEFAULT_CONFIG["indexing"]["k"]["tail_years_to_scan"],
        ),
    )

    # --------------------------------------------------------
    # Indexing / DXF
    # --------------------------------------------------------
    raw_dxf = raw_indexing["dxf"]
    dxf_cfg = DXFIndexingConfig(
        min_dxf_no=_as_int(raw_dxf["min_dxf_no"], DEFAULT_CONFIG["indexing"]["dxf"]["min_dxf_no"]),
        max_dxf_no=_as_int(raw_dxf["max_dxf_no"], DEFAULT_CONFIG["indexing"]["dxf"]["max_dxf_no"]),
        file_tail_backtrack=_as_int(
            raw_dxf["file_tail_backtrack"],
            DEFAULT_CONFIG["indexing"]["dxf"]["file_tail_backtrack"],
        ),
        file_tail_forward_scan=_as_int(
            raw_dxf["file_tail_forward_scan"],
            DEFAULT_CONFIG["indexing"]["dxf"]["file_tail_forward_scan"],
        ),
    )

    # --------------------------------------------------------
    # Indexing / App.Nr.
    # --------------------------------------------------------
    raw_appnr = raw_indexing["appnr"]
    appnr_cfg = AppNrIndexingConfig(
        tail_backtrack_prefix=_as_int(
            raw_appnr["tail_backtrack_prefix"],
            DEFAULT_CONFIG["indexing"]["appnr"]["tail_backtrack_prefix"],
        )
    )

    indexing_cfg = IndexingConfig(
        auto_update_on_start=_as_bool(
            raw_indexing["auto_update_on_start"],
            DEFAULT_CONFIG["indexing"]["auto_update_on_start"],
        ),
        k=k_cfg,
        dxf=dxf_cfg,
        appnr=appnr_cfg,
    )

    # --------------------------------------------------------
    # UI
    # --------------------------------------------------------
    raw_ui = raw["ui"]
    raw_colors = raw_ui["colors"]
    raw_fonts = raw_ui["fonts"]

    colors_cfg = ColorsConfig(
        bg=str(raw_colors["bg"]),
        btn_primary=str(raw_colors["btn_primary"]),
        btn_ok=str(raw_colors["btn_ok"]),
        btn_warn=str(raw_colors["btn_warn"]),
        btn_danger=str(raw_colors["btn_danger"]),
        btn_dark=str(raw_colors["btn_dark"]),
        text=str(raw_colors["text"]),
        label=str(raw_colors["label"]),
    )

    fonts_cfg = FontsConfig(
        default_size=_as_int(raw_fonts["default_size"], DEFAULT_CONFIG["ui"]["fonts"]["default_size"]),
        small_size=_as_int(raw_fonts["small_size"], DEFAULT_CONFIG["ui"]["fonts"]["small_size"]),
        title_size=_as_int(raw_fonts["title_size"], DEFAULT_CONFIG["ui"]["fonts"]["title_size"]),
        button_size=_as_int(raw_fonts["button_size"], DEFAULT_CONFIG["ui"]["fonts"]["button_size"]),
    )

    ui_cfg = UiConfig(
        window_size=_as_size(tuple(raw_ui["window_size"]), tuple(DEFAULT_CONFIG["ui"]["window_size"])),
        service_window_size=_as_size(
            tuple(raw_ui["service_window_size"]),
            tuple(DEFAULT_CONFIG["ui"]["service_window_size"]),
        ),
        auto_open_single=_as_bool(
            raw_ui["auto_open_single"],
            DEFAULT_CONFIG["ui"]["auto_open_single"],
        ),
        auto_show_single=_as_bool(
            raw_ui["auto_show_single"],
            DEFAULT_CONFIG["ui"]["auto_show_single"],
        ),
        live_search_if_missing=_as_bool(
            raw_ui["live_search_if_missing"],
            DEFAULT_CONFIG["ui"]["live_search_if_missing"],
        ),
        colors=colors_cfg,
        fonts=fonts_cfg,
    )

    # --------------------------------------------------------
    # Data files
    # --------------------------------------------------------
    raw_data_files = raw["data_files"]
    data_files_cfg = DataFilesConfig(
        k_index_json=_as_path(raw_data_files["k_index_json"]),
        dxf_ranges_json=_as_path(raw_data_files["dxf_ranges_json"]),
        dxf_excel_index_json=_as_path(raw_data_files["dxf_excel_index_json"]),
        dxf_files_index_json=_as_path(raw_data_files["dxf_files_index_json"]),
        appnr_index_json=_as_path(raw_data_files["appnr_index_json"]),
    )

    return AppSettings(
        paths=paths_cfg,
        indexing=indexing_cfg,
        ui=ui_cfg,
        data_files=data_files_cfg,
    )