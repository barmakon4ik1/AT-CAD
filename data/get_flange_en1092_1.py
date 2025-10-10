"""
data/get_flange_en1092_1.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Модуль для получения параметров фланцев по EN 1092-1 из SQLite-базы.

Логика:
- Таблица Terms: в первом столбце — коды (типы фланцев и коды форм поверхности).
  В заголовке — имена размерных величин. В ячейках — метки (0,1,2,32,34,35,36,37 ...).
- Для заданного (type, face, DN, PN) берем две строки Terms:
    - строку, соответствующую type,
    - строку, соответствующую face.
  По каждому столбцу решаем: включать параметр или нет, комбинируя отметки из этих двух строк.
- Значения берём сначала из PNxx (по DN), затем — из Face (по DN).
- Спец-коды 32/34/... означают искать поля с суффиксом (_32, _34 и т.д.), иначе — базовое имя.

Функция:
    get_flange_en1092_1(params, db_path="en1092-1.db", verbose=False)
"""

import sqlite3
import pandas as pd
import json


def _to_int_safe(x):
    try:
        return int(str(x).strip())
    except Exception:
        return 0


def get_flange_en1092_1(params, db_path="en1092-1.db", verbose: bool = False):
    """
    params: {"type":"11", "face":"C", "DN":"100", "PN":"16"}
    returns: {"input": params, "data": {<field>: {"value":..., "restricted":bool, "source": "PN16"/"Face"}}}
    """
    conn = sqlite3.connect(db_path)
    try:
        type_code = str(params.get("type") or "").strip()
        face_code = str(params.get("face") or "").strip()
        dn_value = str(params.get("DN") or "").strip()
        pn_value = str(params.get("PN") or "").strip()
        pn_table = f"PN{pn_value}"

        result = {"input": params, "data": {}}

        # --- Загружаем всю таблицу Terms ---
        terms_df = pd.read_sql_query("SELECT * FROM Terms", conn)
        if terms_df.empty:
            result["error"] = "Таблица Terms пуста или отсутствует."
            return result

        # Первый столбец содержит коды строк (type / face)
        row_id_col = terms_df.columns[0]

        # Найдём строку для type и для face (если есть)
        def _find_terms_row(code):
            if code == "":
                return {}
            mask = terms_df[row_id_col].astype(str).str.strip() == str(code).strip()
            if mask.any():
                return terms_df[mask].iloc[0].to_dict()
            return {}

        terms_type_row = _find_terms_row(type_code)
        terms_face_row = _find_terms_row(face_code)

        # Список полей (все столбцы кроме первого)
        fields = [c for c in terms_df.columns if c != row_id_col]

        # --- Загружаем PNxx (по DN) ---
        pn_row = {}
        try:
            pn_df = pd.read_sql_query(f"SELECT * FROM '{pn_table}'", conn)
            if "DN" in pn_df.columns:
                pn_df["DN"] = pn_df["DN"].astype(str).str.strip()
                pn_match = pn_df[pn_df["DN"] == dn_value]
                if not pn_match.empty:
                    pn_row_raw = pn_match.iloc[0].to_dict()
                    # нормализуем ключи: strip()
                    pn_row = {k.strip(): (v if pd.notna(v) else None) for k, v in pn_row_raw.items()}
        except Exception as e:
            if verbose:
                print("Warning reading PN table:", e)
            pn_row = {}

        # --- Загружаем Face (по DN) ---
        face_row = {}
        try:
            face_df = pd.read_sql_query("SELECT * FROM Face", conn)
            if "DN" in face_df.columns:
                face_df["DN"] = face_df["DN"].astype(str).str.strip()
                face_match = face_df[face_df["DN"] == dn_value]
                if not face_match.empty:
                    face_row_raw = face_match.iloc[0].to_dict()
                    face_row = {k.strip(): (v if pd.notna(v) else None) for k, v in face_row_raw.items()}
        except Exception as e:
            if verbose:
                print("Warning reading Face table:", e)
            face_row = {}

        if verbose:
            print("TYPE row found:", bool(terms_type_row))
            print("FACE row found in Terms:", bool(terms_face_row))
            print("PN keys:", list(pn_row.keys())[:40])
            print("Face keys:", list(face_row.keys())[:40])

        # Спец-коды
        specials = {32, 34, 35, 36, 37}

        final = {}

        # Для каждого поля решаем, включать ли его: комбинируем маркировки из type- и face-строк
        for col in fields:
            field_name = col.strip()
            if field_name == "":
                continue

            # Возьмём метки из обеих строк (если есть)
            type_mark = _to_int_safe(terms_type_row.get(col, 0))
            face_mark = _to_int_safe(terms_face_row.get(col, 0))

            # Комбинирование меток:
            # - если какая-то из них спец-код (32/34/...), предпочтение отдаём form (face)>type,
            #   затем type если form не дал спец-код;
            # - иначе если хоть одна == 2 -> restricted
            # - иначе если хоть одна == 1 -> include
            eff_mark = 0
            # prefer face special
            if face_mark in specials:
                eff_mark = face_mark
            elif type_mark in specials:
                eff_mark = type_mark
            elif face_mark == 2 or type_mark == 2:
                eff_mark = 2
            elif face_mark == 1 or type_mark == 1:
                eff_mark = 1
            else:
                eff_mark = 0

            if eff_mark == 0:
                # не используется ни типом, ни формой
                continue

            restricted = (eff_mark == 2)

            # Получаем значение: сначала пробуем PNxx (поскольку многие значения зависят от PN/DN),
            # затем Face. Для спец-кодов пробуем поле с суффиксом, иначе базовое.
            value = None
            source = None

            if eff_mark in specials:
                suffix = f"_{eff_mark}"
                special_field = field_name + suffix
                # PNxx с суффиксом
                if special_field in pn_row and pn_row[special_field] not in (None, ""):
                    value = pn_row[special_field]
                    source = pn_table
                # PNxx без суффикса
                elif field_name in pn_row and pn_row[field_name] not in (None, ""):
                    value = pn_row[field_name]
                    source = pn_table
                # Face с суффиксом
                elif special_field in face_row and face_row[special_field] not in (None, ""):
                    value = face_row[special_field]
                    source = "Face"
                elif field_name in face_row and face_row[field_name] not in (None, ""):
                    value = face_row[field_name]
                    source = "Face"
            else:
                # обычный случай 1 или 2
                if field_name in pn_row and pn_row[field_name] not in (None, ""):
                    value = pn_row[field_name]
                    source = pn_table
                elif field_name in face_row and face_row[field_name] not in (None, ""):
                    value = face_row[field_name]
                    source = "Face"

            if value is None:
                # значение отсутствует в PNxx и в Face — пропускаем
                if verbose:
                    print(f"Field {field_name} marked by Terms but no value found in PNxx/Face")
                continue

            # Нормализуем строковое представление
            final[field_name] = {
                "value": str(value),
                "restricted": bool(restricted),
                "source": source
            }

        result["data"] = final
        return result

    finally:
        conn.close()


if __name__ == "__main__":
    # Пример: здесь face=C — параметры должны браться строго по Terms (строке type=11 и строке C)
    params = {"type": "21", "face": "H", "DN": "100", "PN": "16"}
    out = get_flange_en1092_1(params, verbose=True)
    print(json.dumps(out, ensure_ascii=False, indent=2))
