"""
data/get_flange_en1092_1.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Модуль для получения параметров фланцев по стандарту EN 1092-1
на основе SQLite-базы (например, en1092-1.db).

Функция get_flange_en1092_1() принимает параметры фланца и возвращает
все доступные геометрические данные с указанием источников (PNxx, Face и т.д.).

Пример:
    >>> params = {"type": "11", "face": "B1", "DN": "100", "PN": "16"}
    >>> result = get_flange_en1092_1(params)
    >>> print(result["data"]["d1"]["value"])
    158
"""

import sqlite3
import pandas as pd
import re


def get_flange_en1092_1(params, db_path="en1092-1.db"):
    """
    Возвращает параметры фланца EN 1092-1 по типу, форме, DN и PN.

    :param params: словарь с параметрами:
        {
            "type": "11",
            "face": "B1",
            "DN": "100",
            "PN": "16"
        }
    :param db_path: путь к базе данных (по умолчанию en1092-1.db)
    :return: словарь с результатом:
        {
            "input": {...},
            "data": {
                "D": {"value": "220", "source": "PN16"},
                "f1": {"value": "3", "source": "Face"},
                "d1": {"value": "158", "source": "PN16"},
                ...
            }
        }
    """
    conn = sqlite3.connect(db_path)

    type_code = params.get("type")
    face_code = params.get("face")
    dn_value = params.get("DN")
    pn_value = params.get("PN")

    result = {"input": params, "data": {}}

    # === 1. Загружаем Terms для типа ===
    terms_df = pd.read_sql_query(
        f"SELECT * FROM Terms WHERE Type = '{type_code}'", conn
    )
    if terms_df.empty:
        conn.close()
        result["error"] = f"Тип {type_code} не найден в Terms"
        return result

    terms_row = terms_df.iloc[0].to_dict()

    # === 2. PN таблица ===
    pn_table = f"PN{pn_value}"
    try:
        pn_df = pd.read_sql_query(f"SELECT * FROM '{pn_table}'", conn)
        pn_df["DN"] = pn_df["DN"].astype(str)
        pn_filtered = pn_df[pn_df["DN"] == str(dn_value)]
        pn_row = pn_filtered.iloc[0].to_dict() if not pn_filtered.empty else {}
    except Exception as e:
        pn_row = {}
        result["warning_PN"] = str(e)

    # === 3. Face таблица ===
    try:
        face_df = pd.read_sql_query("SELECT * FROM Face", conn)
        face_df["DN"] = face_df["DN"].astype(str)
        face_filtered = face_df[face_df["DN"] == str(dn_value)]
        face_row = face_filtered.iloc[0].to_dict() if not face_filtered.empty else {}
    except Exception as e:
        face_row = {}
        result["warning_Face"] = str(e)

    # === 4. Формируем итог ===
    final_data = {}

    # --- параметры из Terms ---
    for field, term_value in terms_row.items():
        if field.lower() == "type":
            continue

        try:
            term_val = int(term_value)
        except (ValueError, TypeError):
            continue

        if term_val == 0:
            continue

        entry = {"restricted": term_val == 2, "source": None}

        if field in pn_row:
            entry["value"] = pn_row[field]
            entry["source"] = pn_table
        elif field in face_row:
            entry["value"] = face_row[field]
            entry["source"] = "Face"

        if "value" in entry:
            final_data[field] = entry

    # --- параметры формы (d1, f1 и т.п.) ---
    m = re.search(r"(\d+)$", face_code or "")
    suffix = m.group(1) if m else ""

    for k, v in face_row.items():
        if pd.isna(v):
            continue
        if suffix:
            if k.endswith(suffix) and k[0].lower() in ("d", "f"):
                final_data[k] = {
                    "value": str(v),
                    "restricted": False,
                    "source": "Face"
                }
        else:
            if k.lower() in ("d", "f"):
                final_data[k] = {
                    "value": str(v),
                    "restricted": False,
                    "source": "Face"
                }

    # --- 5. Особый случай: d1 (берем из PNxx, т.к. зависит от PN и DN) ---
    if "d1" in terms_row and "d1" in pn_row:
        final_data["d1"] = {
            "value": str(pn_row["d1"]),
            "restricted": False,
            "source": pn_table,
        }

    conn.close()
    result["data"] = final_data
    return result


if __name__ == "__main__":
    params = {"type": "11", "face": "B1", "DN": "100", "PN": "16"}
    data = get_flange_en1092_1(params)
    import pprint
    pprint.pprint(data)
