"""
Файл: get_flange_en1092_1.py
Путь: data/get_flange_en1092_1.py

Описание:
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Модуль для получения параметров фланцев по стандарту EN 1092-1 из базы данных SQLite.

Поддерживает:
- Проверку применимости фланцев через таблицу Applicability.
- Определение параметров по таблицам Terms, PNxx и Face.
- Поддержку спец-кодов (32, 34, 35, 36, 37) для пар "фланец+бурт".
- Отображение локализованных всплывающих сообщений об ошибках и исключениях.

Зависимости:
- pandas, sqlite3
- AT-CAD: windows.at_gui_utils.show_popup
- AT-CAD: locales.at_translations.loc

Автор: AT-CAD Dev Team
Дата: 2025-10-12
Версия: 2.3
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
"""

import sqlite3
from pprint import pprint

import pandas as pd
import json
from windows.at_gui_utils import show_popup
from locales.at_translations import loc


# === 📘 Локальный словарь переводов ===
LOCAL_TRANSLATIONS = {
    "applicability_not_found": {
        "ru": "Таблица применимости (Applicability) отсутствует в базе данных.",
        "en": "Applicability table is missing in the database.",
        "de": "Die Tabelle 'Applicability' fehlt in der Datenbank."
    },
    "applicability_empty": {
        "ru": "Таблица применимости пуста.",
        "en": "Applicability table is empty.",
        "de": "Die Tabelle 'Applicability' ist leer."
    },
    "type_not_found": {
        "ru": "Тип фланца {0} не найден в таблице применимости.",
        "en": "Flange type {0} not found in applicability table.",
        "de": "Flanschtyp {0} wurde in der Anwendungstabelle nicht gefunden."
    },
    "pn_not_found": {
        "ru": "Давление PN{0} отсутствует в таблице применимости.",
        "en": "Pressure PN{0} not found in applicability table.",
        "de": "Druck PN{0} wurde in der Anwendungstabelle nicht gefunden."
    },
    "not_applicable": {
        "ru": "Для фланца типа {0} при PN{1} и DN{2} стандарт не предусматривает применение.",
        "en": "Flange type {0} with PN{1} and DN{2} is not applicable according to the standard.",
        "de": "Der Flanschtyp {0} mit PN{1} und DN{2} ist gemäß Norm nicht anwendbar."
    },
    "no_dimensions": {
        "ru": "Для данного фланца размеры не определены. Используйте данные производителя.",
        "en": "Dimensions are not defined for this flange. Use manufacturer data.",
        "de": "Abmessungen für diesen Flansch sind nicht definiert. Verwenden Sie Herstellerangaben."
    },
    "error": {
        "ru": "Ошибка",
        "en": "Error",
        "de": "Fehler"
    },
    "info": {
        "ru": "Информация",
        "en": "Information",
        "de": "Information"
    },
    "success": {
        "ru": "Успех",
        "en": "Success",
        "de": "Erfolg"
    }
}

# Регистрируем переводы при импорте
loc.register_translations(LOCAL_TRANSLATIONS)


def _to_int_safe(x):
    """Безопасное преобразование к целому числу."""
    try:
        return int(str(x).strip())
    except Exception:
        return 0


def get_flange_en1092_1(params, db_path="en1092-1.db", verbose: bool = False):
    """
    Получает параметры фланца по EN 1092-1 из SQLite-базы.

    Args:
        params (dict): Входные параметры:
            {
              "type": "11",   # тип фланца (например 01, 11, 21 и т.п.)
              "face": "B1",   # форма уплотнительной поверхности
              "DN": "100",    # номинальный диаметр
              "PN": "16"      # номинальное давление
            }
        db_path (str): путь к SQLite базе
        verbose (bool): выводить отладочную информацию в консоль

    Returns:
        dict: результат с данными фланца или сообщением об ошибке.
    """
    conn = sqlite3.connect(db_path)
    try:
        type_code = str(params.get("type") or "").strip()
        face_code = str(params.get("face") or "").strip()
        dn_value = str(params.get("DN") or "").strip()
        pn_value = str(params.get("PN") or "").strip()
        pn_table = f"PN{pn_value}"

        result = {"input": params, "data": {}}

        # === 1️⃣ Проверка применимости ===
        try:
            applicability_df = pd.read_sql_query("SELECT * FROM Applicability", conn)
            if applicability_df.empty:
                show_popup(loc.get("applicability_empty", "Таблица применимости пуста"),
                           title=loc.get("error"), popup_type="error")
                result["error"] = "Applicability table is empty"
                return result

            # Приводим столбцы к строковому виду
            applicability_df.columns = [str(c).strip() for c in applicability_df.columns]
            applicability_df["Typ"] = applicability_df["Typ"].astype(str).str.strip()
            applicability_df["PN"] = applicability_df["PN"].astype(str).str.strip()

            # --- Список возможных типов для поиска ---
            # Учитываем пары (02 и 35, 04 и 36 и т.п.)
            type_aliases = {
                "02": ["35", "32", "36", "37"],
                "35": ["02", "32", "36", "37"],
                "04": ["34"],
                "34": ["04"],
                "12": ["13"],
                "13": ["12"],
            }

            all_types_to_check = [type_code] + type_aliases.get(type_code, [])
            pn_str = str(pn_value)

            # --- Фильтрация по PN ---
            pn_filtered = applicability_df[applicability_df["PN"] == pn_str]

            if pn_filtered.empty:
                show_popup(
                    loc.get("pn_not_found", "Давление PN{0} отсутствует в таблице применимости", pn_value),
                    title=loc.get("error"), popup_type="error"
                )
                result["error"] = f"PN{pn_value} not found in Applicability"
                return result

            # --- Поиск подходящей строки по части типа ---
            matched_rows = pn_filtered[
                pn_filtered["Typ"].apply(
                    lambda t: any(sub in t for sub in all_types_to_check)
                )
            ]

            if matched_rows.empty:
                show_popup(
                    loc.get("type_not_found",
                            "Тип фланца {0} (или его аналоги {1}) не найден в таблице применимости при PN{2}",
                            type_code, ", ".join(all_types_to_check), pn_value),
                    title=loc.get("error"), popup_type="error"
                )
                result["error"] = f"Type {type_code} (aliases {all_types_to_check}) with PN {pn_value} not found"
                return result

            # Берём первую найденную строку
            row = matched_rows.iloc[0].to_dict()

            # --- Поиск колонки DN ---
            dn_col = None
            for col in row.keys():
                if str(dn_value).strip() == str(col).strip():
                    dn_col = col
                    break

            if not dn_col:
                show_popup(
                    loc.get("dn_not_found", "Диаметр DN{0} отсутствует в таблице применимости", dn_value),
                    title=loc.get("error"), popup_type="error"
                )
                result["error"] = f"DN{dn_value} column not found in Applicability"
                return result

            appl_value = row[dn_col]
            appl_value = int(appl_value) if appl_value not in (None, "", "NaN") else 0

            if appl_value == 0:
                show_popup(
                    loc.get("not_applicable",
                            "Фланец {0} (или эквиваленты {1}) при PN{2} и DN{3} не применяется",
                            type_code, ", ".join(all_types_to_check), pn_value, dn_value),
                    title=loc.get("info"), popup_type="info"
                )
                result["error"] = f"Type {type_code} PN{pn_value} DN{dn_value} not applicable"
                return result

            if verbose:
                print(
                    f"✅ Применимость подтверждена: Typ={type_code} (возможные {all_types_to_check}), PN={pn_value}, DN={dn_value}")

        except Exception as e:
            show_popup(
                loc.get("applicability_error", "Ошибка проверки применимости: {0}", e),
                title=loc.get("error"), popup_type="error"
            )
            result["error"] = f"Applicability check failed: {e}"
            return result

        # === 2️⃣ Загружаем таблицы ===
        terms_df = pd.read_sql_query("SELECT * FROM Terms", conn)
        if terms_df.empty:
            show_popup("Таблица Terms пуста или отсутствует.", title=loc.get("error"))
            return result

        row_id_col = terms_df.columns[0]

        def _find_terms_row(code):
            mask = terms_df[row_id_col].astype(str).str.strip() == str(code).strip()
            if mask.any():
                return terms_df[mask].iloc[0].to_dict()
            return {}

        terms_type_row = _find_terms_row(type_code)
        terms_face_row = _find_terms_row(face_code)

        fields = [c for c in terms_df.columns if c != row_id_col]

        # --- PNxx
        pn_row = {}
        try:
            pn_df = pd.read_sql_query(f"SELECT * FROM '{pn_table}'", conn)
            if "DN" in pn_df.columns:
                pn_df["DN"] = pn_df["DN"].astype(str).str.strip()
                match = pn_df[pn_df["DN"] == dn_value]
                if not match.empty:
                    pn_row = {k.strip(): v for k, v in match.iloc[0].to_dict().items() if pd.notna(v)}
        except Exception as e:
            if verbose:
                print("⚠️ Ошибка чтения PN таблицы:", e)

        # --- Face
        face_row = {}
        try:
            face_df = pd.read_sql_query("SELECT * FROM Face", conn)
            if "DN" in face_df.columns:
                face_df["DN"] = face_df["DN"].astype(str).str.strip()
                match = face_df[face_df["DN"] == dn_value]
                if not match.empty:
                    face_row = {k.strip(): v for k, v in match.iloc[0].to_dict().items() if pd.notna(v)}
        except Exception as e:
            if verbose:
                print("⚠️ Ошибка чтения Face таблицы:", e)

        specials = {32, 34, 35, 36, 37}
        final = {}

        # === 3️⃣ Формирование выходных данных ===
        for col in fields:
            field_name = col.strip()
            if not field_name:
                continue

            type_mark = _to_int_safe(terms_type_row.get(col, 0))
            face_mark = _to_int_safe(terms_face_row.get(col, 0))

            if face_mark in specials:
                eff_mark = face_mark
            elif type_mark in specials:
                eff_mark = type_mark
            elif 2 in (face_mark, type_mark):
                eff_mark = 2
            elif 1 in (face_mark, type_mark):
                eff_mark = 1
            else:
                eff_mark = 0

            if eff_mark == 0:
                continue

            restricted = (eff_mark == 2)
            value, source = None, None

            # Спец-коды (например, _36)
            if eff_mark in specials:
                suffix = f"_{eff_mark}"
                field_special = field_name + suffix
                for src, data in [(pn_table, pn_row), ("Face", face_row)]:
                    if field_special in data and data[field_special]:
                        value, source = data[field_special], src
                        break
                    if field_name in data and data[field_name]:
                        value, source = data[field_name], src
                        break
            else:
                for src, data in [(pn_table, pn_row), ("Face", face_row)]:
                    if field_name in data and data[field_name]:
                        value, source = data[field_name], src
                        break

            if value is not None:
                final[field_name] = {"value": str(value), "restricted": restricted, "source": source}
            elif verbose:
                print(f"⚠️ Поле {field_name} отмечено в Terms, но не найдено в PNxx/Face")

        result["data"] = final

        if not final:
            show_popup(loc.get("no_dimensions"), title=loc.get("info"), popup_type="info")

        return result

    finally:
        conn.close()


# === 🔧 Тестовый запуск ===
if __name__ == "__main__":
    params = {"type": "01", "face": "A", "DN": "80", "PN": "16"}
    result = get_flange_en1092_1(params, db_path="en1092-1.db", verbose=True)

    print(f'EN1092-1 /{params["type"]} / {params["face"]} / {params["DN"]} / {params["PN"]}')
    # h2_value = result["data"]["H2"]["value"]
    # print(f'H2 = {h2_value}')
    pprint(result)

    # print("\n=== РЕЗУЛЬТАТ ===")
    # print(json.dumps(result, ensure_ascii=False, indent=2))


