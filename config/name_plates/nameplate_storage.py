# -*- coding: utf-8 -*-
"""
Файл: nameplate_storage.py

Назначение
----------
Модуль отвечает за загрузку, сохранение и базовое обслуживание JSON-файла
с конфигурациями табличек (name plates).

Хранилище представляет собой JSON-массив словарей следующего вида:

{
    "name":   str,   # уникальное имя таблички
    "a":      str|float,
    "b":      str|float,
    "a1":     str|float,
    "b1":     str|float,
    "d":      str|float,
    "r":      str|float,
    "s":      str|float,
    "remark": str
}

Файл и связанные изображения располагаются в одной директории:
    config\\name_plates

Модуль не содержит GUI-логики и может использоваться как из wxPython,
так и из других частей системы (AutoCAD, CLI, тесты).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Dict


# ============================================================================
# Пути
# ============================================================================

BASE_DIR = Path(__file__).resolve().parent
JSON_FILE = BASE_DIR / "name_plates.json"


# ============================================================================
# Загрузка / сохранение
# ============================================================================

def load_nameplates() -> List[Dict]:
    """
    Загружает список табличек из JSON-файла.

    Если файл отсутствует — возвращает пустой список.
    Если файл повреждён — возбуждает исключение ValueError.

    Returns
    -------
    list[dict]
        Список записей табличек.
    """
    if not JSON_FILE.exists():
        return []

    try:
        with JSON_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Ошибка чтения JSON-файла: {JSON_FILE}"
        ) from exc

    if not isinstance(data, list):
        raise ValueError(
            f"Некорректная структура JSON: ожидается список ({JSON_FILE})"
        )

    return data


def save_nameplates(records: List[Dict]) -> None:
    """
    Сохраняет список табличек в JSON-файл.

    Параметры
    ---------
    records : list[dict]
        Список записей табличек.
    """
    with JSON_FILE.open("w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=4)


# ============================================================================
# CRUD-операции
# ============================================================================

def find_by_name(records: List[Dict], name: str) -> Dict | None:
    """
    Поиск записи по имени таблички.

    Returns
    -------
    dict | None
        Найденная запись или None.
    """
    for record in records:
        return record if record.get("name") == name else None
    return None

def add_record(records: List[Dict], record: Dict) -> None:
    """
    Добавляет новую запись.

    Имя таблички должно быть уникальным.

    Raises
    ------
    ValueError
        Если запись с таким именем уже существует.
    """
    name = record.get("name")
    if not name:
        raise ValueError("Поле 'name' обязательно для записи таблички")

    if find_by_name(records, name) is not None:
        raise ValueError(f"Табличка с именем '{name}' уже существует")

    records.append(record)


def update_record(records: List[Dict], name: str, new_record: Dict) -> None:
    """
    Обновляет существующую запись по имени.

    Raises
    ------
    ValueError
        Если запись не найдена.
    """
    for idx, record in enumerate(records):
        if record.get("name") == name:
            records[idx] = new_record
            return

    raise ValueError(f"Табличка с именем '{name}' не найдена")


def delete_record(records: List[Dict], name: str) -> None:
    """
    Удаляет запись по имени.

    Raises
    ------
    ValueError
        Если запись не найдена.
    """
    for idx, record in enumerate(records):
        if record.get("name") == name:
            del records[idx]
            return

    raise ValueError(f"Табличка с именем '{name}' не найдена")
