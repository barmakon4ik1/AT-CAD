"""
k_repository.py
===============

Репозиторий и сервис поиска K-заказов для K-Finder.

Назначение
----------
Этот модуль переносит K-часть из старого монолита в новую структуру проекта.

Содержит:
1. KIndex
   In-memory индекс папок заказов:
   - загрузка/сохранение JSON
   - точный поиск
   - частичный поиск
   - хвостовое обновление
   - полное перестроение

2. SearchService
   Сервис "индекс -> диск -> кэш отсутствия":
   - сначала ищет в индексе
   - при необходимости ищет на диске
   - сохраняет найденные записи
   - кэширует отсутствующие номера как заглушки

Архитектурно
------------
- Хранение данных: models.KEntry
- Пути и параметры: config.AppSettings
- Логирование: logging_setup.get_logger()

Важно
-----
Этот модуль не содержит GUI.
Он должен использоваться из main_frame.py и dialogs.py.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from .config import AppSettings
from .logging_setup import get_logger
from .models import KEntry

logger = get_logger()


class KIndex:
    """
    In-memory индекс папок заказов K-Finder.

    Формат JSON:
    {
      "_meta": {
        "root": "...",
        "start_year": 2011,
        "generated_at": "...",
        "count": N
      },
      "items": {
        "K12345": {
          "k_code": "K12345",
          "year": 2024,
          ...
        }
      }
    }
    """

    FULL_RE = re.compile(r"^K\d{5}$", re.IGNORECASE)
    PARTIAL_RE = re.compile(r"^[Kk]?\d{1,5}$")

    def __init__(self, settings: AppSettings):
        self.settings = settings
        self.cfg_paths = settings.paths
        self.cfg_idx = settings.indexing.k
        self.data_files = settings.data_files

        self._items: dict[str, KEntry] = {}
        self._meta: dict = {}

        self._load_cache()

    # ========================================================
    # Базовые свойства
    # ========================================================

    @property
    def root_dir(self) -> Path:
        """
        Корневая директория заказов.
        """
        return self.cfg_paths.root_dir

    @property
    def index_file(self) -> Path:
        """
        JSON-файл индекса K.
        """
        return self.data_files.k_index_json

    @property
    def start_year(self) -> int:
        """
        Самый ранний год для полного сканирования.
        """
        return self.cfg_idx.start_year

    @property
    def sketch_folder_name(self) -> str:
        """
        Имя подпапки со скетчами внутри папки заказа.
        """
        return self.cfg_paths.sketch_folder_name

    # ========================================================
    # JSON / cache
    # ========================================================

    def _load_cache(self) -> None:
        """
        Загружает индекс с диска в память.
        """
        data = self._load_raw()
        self._meta = data.get("_meta", {})
        self._items = {}

        for code, item in data.get("items", {}).items():
            try:
                self._items[code] = KEntry.from_dict(item)
            except (KeyError, ValueError, TypeError) as e:
                logger.error(f"KIndex._load_cache bad record {code}: {e}")

    def reload(self) -> None:
        """
        Принудительно перечитывает индекс с диска.
        """
        self._load_cache()

    def _load_raw(self) -> dict:
        """
        Читает сырой JSON индекса.
        """
        if not self.index_file.is_file():
            return {"_meta": {}, "items": {}}

        try:
            with self.index_file.open("r", encoding="utf-8") as f:
                data = json.load(f)

            if not isinstance(data, dict) or "items" not in data:
                return {"_meta": {}, "items": {}}

            return data

        except (OSError, json.JSONDecodeError) as e:
            logger.error(f"KIndex._load_raw: {e}")
            return {"_meta": {}, "items": {}}

    def _save_raw(self, data: dict) -> None:
        """
        Сохраняет сырой JSON индекса.
        """
        self.index_file.parent.mkdir(parents=True, exist_ok=True)
        with self.index_file.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load_entries(self) -> dict[str, KEntry]:
        """
        Возвращает копию текущего in-memory кэша.
        """
        return dict(self._items)

    def save_entries(self, items: dict[str, KEntry]) -> None:
        """
        Сохраняет словарь записей в память и на диск.
        """
        self._items = dict(items)
        self._meta = {
            "root": str(self.root_dir),
            "start_year": self.start_year,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "count": len(self._items),
        }

        payload = {
            "_meta": self._meta,
            "items": {k: v.to_dict() for k, v in sorted(self._items.items())},
        }
        self._save_raw(payload)

    def get_meta(self) -> dict:
        """
        Возвращает копию метаданных индекса.
        """
        return dict(self._meta)

    def update_entry(self, entry: KEntry) -> None:
        """
        Добавляет или заменяет одну запись и сохраняет индекс.
        """
        self._items[entry.k_code] = entry
        self.save_entries(self._items)

    # ========================================================
    # Вспомогательные методы
    # ========================================================

    def _current_year(self) -> int:
        return datetime.now().year

    def is_root_available(self) -> bool:
        """
        Проверяет доступность корневой папки заказов.
        """
        return self.root_dir.exists() and self.root_dir.is_dir()

    def normalize_full(self, text: str) -> str:
        """
        Приводит ввод к формату K12345.

        Допустимо:
        - 12345
        - K12345
        - k12345
        """
        s = text.strip().upper()

        if re.fullmatch(r"\d{5}", s):
            return f"K{s}"

        if self.FULL_RE.fullmatch(s):
            return s

        raise ValueError("Eingabe: Kxxxxx oder 5 Ziffern")

    def normalize_partial(self, text: str) -> str:
        """
        Приводит частичный K-запрос к верхнему регистру.

        Допустимо:
        - 2
        - 20
        - 205
        - 20500
        - K205
        - K20500
        """
        s = text.strip().upper()

        if not s:
            return ""

        if not self.PARTIAL_RE.fullmatch(s):
            raise ValueError("Zulässige Eingabe: K20500, 20500, K205, 205 usw.")

        return s

    def is_full_code(self, text: str) -> bool:
        """
        True, если это полный K-код:
        - K12345
        - 12345
        """
        s = text.strip().upper()
        return bool(self.FULL_RE.fullmatch(s) or re.fullmatch(r"\d{5}", s))

    def _code_to_num(self, k_code: str) -> int:
        """
        K12345 -> 12345
        """
        return int(k_code[1:])

    def _num_to_code(self, num: int) -> str:
        """
        12345 -> K12345
        """
        return f"K{num:05d}"

    def _max_known_number(self) -> int:
        """
        Возвращает максимальный известный числовой K-номер.
        """
        nums = [
            self._code_to_num(code)
            for code in self._items
            if self.FULL_RE.fullmatch(code)
        ]
        return max(nums) if nums else 0

    def _make_entry(self, k_code: str, year: int, folder: Path) -> KEntry:
        """
        Создаёт запись индекса для реально найденной папки заказа.
        """
        sketch = folder / self.sketch_folder_name
        dwg = sketch / f"ABW-{k_code}.dwg"

        return KEntry(
            k_code=k_code,
            year=year,
            folder_path=str(folder),
            sketch_path=str(sketch),
            dwg_path=str(dwg),
            has_folder=True,
        )

    def _make_missing_entry(self, k_code: str) -> KEntry:
        """
        Создаёт запись-заглушку для отсутствующего номера.
        """
        return KEntry(
            k_code=k_code,
            year=0,
            folder_path="",
            sketch_path="",
            dwg_path="",
            has_folder=False,
        )

    # ========================================================
    # Сканирование диска
    # ========================================================

    def _scan_years_for_kfolders(
        self,
        start_year: int,
        end_year: int,
        progress_cb: Optional[Callable[[str], None]] = None,
    ) -> dict[str, KEntry]:
        """
        Выполняет один массовый проход по годовым папкам.

        Алгоритм:
        - обходит папки годов;
        - если папка называется Kxxxxx, добавляет её в результат;
        - внутрь найденной K-папки дальше не спускается.
        """
        found: dict[str, KEntry] = {}

        for year in range(start_year, end_year + 1):
            year_path = self.root_dir / str(year)
            count_year = 0

            if year_path.is_dir():
                for dirpath, dirnames, _ in os.walk(year_path):
                    current = Path(dirpath)
                    name = current.name.upper()

                    if self.FULL_RE.fullmatch(name):
                        found[name] = self._make_entry(name, year, current)
                        dirnames[:] = []
                        count_year += 1

            if progress_cb:
                progress_cb(f"{year}: {count_year} Ordner")

        return found

    # ========================================================
    # Поиск
    # ========================================================

    def find_exact(self, k_code: str) -> Optional[KEntry]:
        """
        Точный поиск по коду в памяти.
        """
        return self._items.get(k_code)

    def find_partial(self, query: str) -> list[KEntry]:
        """
        Частичный поиск по началу K-кода.

        Примеры:
        - 20    -> K20000, K20123, K20555 ...
        - K20   -> K20000, K20123, ...
        """
        q = self.normalize_partial(query)
        if not q:
            return []

        q_digits = q[1:] if q.startswith("K") else q

        results = [
            entry for code, entry in self._items.items()
            if code.startswith(q) or code[1:].startswith(q_digits)
        ]
        results.sort(key=lambda e: (e.year, e.k_code))
        return results

    def search_on_disk(self, k_code: str) -> Optional[KEntry]:
        """
        Точечный поиск одного K-кода по всем годовым папкам.

        Используется только если записи нет в индексе.
        """
        if not self.is_root_available():
            raise FileNotFoundError(f"Root nicht verfügbar: {self.root_dir}")

        for year in range(self.start_year, self._current_year() + 1):
            year_path = self.root_dir / str(year)
            if not year_path.is_dir():
                continue

            for dirpath, dirnames, _ in os.walk(year_path):
                current = Path(dirpath)
                name = current.name.upper()

                if name == k_code and current.is_dir():
                    return self._make_entry(k_code, year, current)

                if self.FULL_RE.fullmatch(name):
                    dirnames[:] = []

        return None

    # ========================================================
    # Индексация
    # ========================================================

    def update_tail(
        self,
        backtrack: Optional[int] = None,
        tail_years_to_scan: Optional[int] = None,
        progress_cb: Optional[Callable[[str], None]] = None,
    ) -> int:
        """
        Хвостовое обновление индекса K.

        Логика:
        1. Берём максимальный известный K-номер.
        2. Сканируем только последние N лет.
        3. Обновляем диапазон [max_known - backtrack .. max_found].
        4. Старые реальные записи вне хвоста не трогаем.
        5. Заглушки выше последнего реального номера обрезаем.
        """
        if not self.is_root_available():
            raise FileNotFoundError(f"Root nicht verfügbar: {self.root_dir}")

        if backtrack is None:
            backtrack = self.cfg_idx.tail_backtrack
        if tail_years_to_scan is None:
            tail_years_to_scan = self.cfg_idx.tail_years_to_scan

        items = dict(self._items)
        max_known = self._max_known_number()

        if max_known <= 0:
            return self.rebuild(progress_cb=progress_cb)

        current_year = self._current_year()
        start_year_scan = max(self.start_year, current_year - tail_years_to_scan + 1)

        found_recent = self._scan_years_for_kfolders(
            start_year=start_year_scan,
            end_year=current_year,
            progress_cb=progress_cb,
        )

        found_recent_nums = [
            self._code_to_num(code)
            for code in found_recent
            if self.FULL_RE.fullmatch(code)
        ]

        max_found_recent = max(found_recent_nums) if found_recent_nums else max_known
        start_num = max(1, max_known - backtrack)
        end_num = max(max_known, max_found_recent)

        for num in range(start_num, end_num + 1):
            code = self._num_to_code(num)
            existing = items.get(code)

            if code in found_recent:
                items[code] = found_recent[code]
            elif existing is not None and existing.has_folder:
                pass
            else:
                items[code] = self._make_missing_entry(code)

        last_real_num = max(
            (
                self._code_to_num(code)
                for code, entry in items.items()
                if entry.has_folder and self.FULL_RE.fullmatch(code)
            ),
            default=0,
        )

        trimmed = {
            code: entry
            for code, entry in items.items()
            if not self.FULL_RE.fullmatch(code)
            or self._code_to_num(code) <= last_real_num
        }

        self.save_entries(trimmed)
        return len(trimmed)

    def rebuild(
        self,
        progress_cb: Optional[Callable[[str], None]] = None,
    ) -> int:
        """
        Полное перестроение K-индекса по всем годам.
        """
        if not self.is_root_available():
            raise FileNotFoundError(f"Root nicht verfügbar: {self.root_dir}")

        found_items = self._scan_years_for_kfolders(
            start_year=self.start_year,
            end_year=self._current_year(),
            progress_cb=progress_cb,
        )

        found_nums = [
            self._code_to_num(code)
            for code in found_items
            if self.FULL_RE.fullmatch(code)
        ]

        if not found_nums:
            self.save_entries({})
            return 0

        min_num = min(found_nums)
        max_num = max(found_nums)

        full_items: dict[str, KEntry] = {}
        for num in range(min_num, max_num + 1):
            code = self._num_to_code(num)
            if code in found_items:
                full_items[code] = found_items[code]
            else:
                full_items[code] = self._make_missing_entry(code)

        self.save_entries(full_items)
        return len(full_items)


class SearchService:
    """
    Сервис поиска K-записи: индекс -> диск -> кэш отсутствия.

    Логика:
    1. Ищем в индексе.
    2. Если запись есть — возвращаем её.
    3. Если записи нет — ищем на диске.
    4. Если нашли — добавляем в индекс.
    5. Если не нашли — сохраняем заглушку.
    """

    def __init__(self, settings: AppSettings, index: KIndex):
        self.settings = settings
        self.index = index
        self.live_search_if_missing = settings.ui.live_search_if_missing

    def get_or_search(self, k_code: str) -> Optional[KEntry]:
        """
        Возвращает KEntry:
        - из индекса, если уже есть;
        - с диска, если live_search_if_missing=True;
        - либо запись-заглушку, если ничего не найдено.
        """
        entry = self.index.find_exact(k_code)

        if entry is not None:
            return entry

        if not self.live_search_if_missing:
            return None

        entry = self.index.search_on_disk(k_code)
        if entry:
            self.index.update_entry(entry)
            return entry

        missing = KEntry(
            k_code=k_code,
            year=0,
            folder_path="",
            sketch_path="",
            dwg_path="",
            has_folder=False,
        )
        self.index.update_entry(missing)
        return missing
