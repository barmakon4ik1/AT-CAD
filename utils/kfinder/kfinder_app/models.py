"""
models.py
=========

Модели данных приложения K-Finder.

Зачем нужен
-----------
В старой версии все dataclass-модели были объявлены прямо внутри
одного большого GUI-файла. Теперь они вынесены в отдельный модуль,
чтобы:

- сократить размер и связность основного кода;
- использовать модели из нескольких модулей без дублирования;
- упростить сопровождение, сериализацию и тестирование.

Содержимое
----------
1. KEntry
   Запись индекса папок заказов K-Finder.

2. DXFRange
   Диапазон DXF-номеров -> папка на диске.

3. DXFExcelRecord
   Одна строка из Excel-таблицы DXF-2017.xlsm.

4. DXFFileRecord
   Запись об основном DWG-файле на диске.

5. DXFSearchResult
   Объединённый результат поиска DXF:
   данные из Excel + путь к основному DWG.

6. AppNrRecord
   Запись индекса серийных номеров аппаратов.

Важно
-----
Модели не должны содержать GUI-логику.
Допустимы только:
- хранение данных,
- простые computed-свойства,
- методы сериализации to_dict()/from_dict().
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional


# ============================================================
# K-Finder
# ============================================================

@dataclass
class KEntry:
    """
    Запись индекса папок заказов.

    Поля:
    -----
    k_code:
        Код заказа в формате K12345.

    year:
        Год из структуры каталога.
        0 = неизвестен или запись-заглушка.

    folder_path:
        Полный путь к папке заказа.

    sketch_path:
        Полный путь к подпапке со скетчами.

    dwg_path:
        Полный путь к основному DWG-файлу внутри папки скетчей.

    has_folder:
        True, если папка заказа реально существует на диске.
        False для записей-заглушек.
    """
    k_code: str
    year: int
    folder_path: str
    sketch_path: str
    dwg_path: str
    has_folder: bool = True

    @property
    def folder_exists(self) -> bool:
        """
        Проверяет существование папки заказа в реальном времени.
        """
        return Path(self.folder_path).is_dir()

    @property
    def sketch_exists(self) -> bool:
        """
        Проверяет существование папки скетчей в реальном времени.
        """
        return Path(self.sketch_path).is_dir()

    @property
    def dwg_exists(self) -> bool:
        """
        Проверяет существование основного DWG-файла в реальном времени.
        """
        return Path(self.dwg_path).is_file()

    def to_dict(self) -> dict:
        """
        Преобразует объект в словарь для JSON-сериализации.
        """
        return asdict(self)

    @staticmethod
    def from_dict(data: dict) -> "KEntry":
        """
        Создаёт объект KEntry из словаря.
        """
        return KEntry(
            k_code=str(data["k_code"]),
            year=int(data["year"]),
            folder_path=str(data["folder_path"]),
            sketch_path=str(data["sketch_path"]),
            dwg_path=str(data["dwg_path"]),
            has_folder=bool(data.get("has_folder", True)),
        )


# ============================================================
# DXF
# ============================================================

@dataclass
class DXFRange:
    """
    Диапазон DXF-номеров, соответствующий одной папке на диске.

    Пример:
    -------
    DXFRange(7801, 9500, "2019")
    означает, что файлы 7801.dwg ... 9500.dwg лежат
    в G:\\Drawing\\DXF-LASER\\2019\\.
    """
    min_no: int
    max_no: int
    folder_name: str

    def to_dict(self) -> dict:
        """
        Преобразует объект в словарь для JSON-сериализации.
        """
        return asdict(self)

    @staticmethod
    def from_dict(data: dict) -> "DXFRange":
        """
        Создаёт объект DXFRange из словаря.
        """
        return DXFRange(
            min_no=int(data["min_no"]),
            max_no=int(data["max_no"]),
            folder_name=str(data["folder_name"]),
        )


@dataclass
class DXFExcelRecord:
    """
    Одна строка из Excel-таблицы DXF-2017.xlsm (лист Tabelle1).

    Колонки:
    --------
    A = dxf_no
    B = k_num
    C = schluessel
    D = wst
    E = dicke_mm
    F = ch_nr
    I = a_kn_brutto_qm
    K = laenge_zuschnitt_mm
    N = preis_pro_laenge_eur
    S = bemerkung

    Новое поле:
    -----------
    ch_nr:
        Номер плавки (Ch.Nr.) из колонки F.
    """
    dxf_no: int
    k_num: str
    schluessel: str
    wst: str
    dicke_mm: Optional[float]
    ch_nr: str
    a_kn_brutto_qm: Optional[float]
    laenge_zuschnitt_mm: Optional[float]
    preis_pro_laenge_eur: Optional[float]
    bemerkung: str

    def to_dict(self) -> dict:
        """
        Преобразует объект в словарь для JSON-сериализации.
        """
        return asdict(self)

    @staticmethod
    def from_dict(data: dict) -> "DXFExcelRecord":
        """
        Создаёт объект DXFExcelRecord из словаря.

        Важно:
        -------
        Поле ch_nr читается через get(..., ""), чтобы старые JSON-индексы,
        созданные до добавления колонки Ch.Nr., тоже корректно загружались.
        """
        return DXFExcelRecord(
            dxf_no=int(data["dxf_no"]),
            k_num=str(data["k_num"]),
            schluessel=str(data.get("schluessel", "")),
            wst=str(data.get("wst", "")),
            dicke_mm=data.get("dicke_mm"),
            ch_nr=str(data.get("ch_nr", "")),
            a_kn_brutto_qm=data.get("a_kn_brutto_qm"),
            laenge_zuschnitt_mm=data.get("laenge_zuschnitt_mm"),
            preis_pro_laenge_eur=data.get("preis_pro_laenge_eur"),
            bemerkung=str(data.get("bemerkung", "")),
        )


@dataclass
class DXFFileRecord:
    """
    Запись о DWG-файле на диске.

    Поля:
    -----
    dxf_no:
        Номер DXF-листа.

    folder_name:
        Имя подпапки из карты диапазонов.

    folder_path:
        Полный путь к папке с файлом.

    main_dwg_path:
        Полный путь к основному DWG-файлу (xxxxx.dwg без суффиксов).

    has_main_dwg:
        True, если основной DWG реально существует на диске.
    """
    dxf_no: int
    folder_name: str
    folder_path: str
    main_dwg_path: str
    has_main_dwg: bool

    def to_dict(self) -> dict:
        """
        Преобразует объект в словарь для JSON-сериализации.
        """
        return asdict(self)

    @staticmethod
    def from_dict(data: dict) -> "DXFFileRecord":
        """
        Создаёт объект DXFFileRecord из словаря.
        """
        return DXFFileRecord(
            dxf_no=int(data["dxf_no"]),
            folder_name=str(data["folder_name"]),
            folder_path=str(data["folder_path"]),
            main_dwg_path=str(data["main_dwg_path"]),
            has_main_dwg=bool(data["has_main_dwg"]),
        )


@dataclass
class DXFSearchResult:
    """
    Объединённый результат поиска DXF.

    Используется для отображения в таблицах GUI.
    Это не строка Excel и не файловая запись по отдельности,
    а итог объединения двух источников:

    - данные из DXFExcelRecord;
    - путь к основному DWG из DXFFileRecord.

    Поле ch_nr:
    -----------
    Добавлено для вывода значения из колонки F (Ch.Nr.).
    """
    dxf_no: int
    k_num: str
    wst: str
    dicke_mm: Optional[float]
    ch_nr: str
    a_kn_brutto_qm: Optional[float]
    laenge_zuschnitt_mm: Optional[float]
    preis_pro_laenge_eur: Optional[float]
    main_dwg_path: str
    has_main_dwg: bool

    def to_dict(self) -> dict:
        """
        Преобразует объект в словарь для JSON-сериализации
        или сохранения результата поиска.
        """
        return asdict(self)


# ============================================================
# Apparate-Nr.
# ============================================================

@dataclass
class AppNrRecord:
    """
    Запись индекса серийных номеров аппаратов.

    Поля:
    -----
    serial_no:
        Полный серийный номер, например:
        "1234", "1234.1", "1234.1-2"

    serial_prefix:
        Числовой префикс до первой точки, например:
        "1234"

    k_code:
        Связанный K-номер заказа.
    """
    serial_no: str
    serial_prefix: str
    k_code: str

    def to_dict(self) -> dict:
        """
        Преобразует объект в словарь для JSON-сериализации.
        """
        return asdict(self)

    @staticmethod
    def from_dict(data: dict) -> "AppNrRecord":
        """
        Создаёт объект AppNrRecord из словаря.
        """
        return AppNrRecord(
            serial_no=str(data["serial_no"]),
            serial_prefix=str(data["serial_prefix"]),
            k_code=str(data["k_code"]),
        )
