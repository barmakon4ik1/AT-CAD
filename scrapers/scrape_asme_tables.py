import pandas as pd
import requests
from io import StringIO
from pathlib import Path

# =========================
# Настройки
# =========================
SAVE_DIR = Path(r"E:\AT-CAD\data")
SAVE_DIR.mkdir(parents=True, exist_ok=True)

# Ссылки и параметры
ASME_LINKS = [
    ("WN", "https://www.engineeringtoolbox.com/flanges-bolts-dimensions-d_464.html"),
    ("SO", "https://sketchup.engineeringtoolbox.com/slip-on-150-lbs-flanges-c_91.html"),
    ("LJ", "https://www.engineeringtoolbox.com/flanges-dimensions-lap-joint-d_484.html"),
    ("Blind", "https://www.engineeringtoolbox.com/flanges-dimensions-blind-d_485.html")
]

PRESSURE_CLASSES = [150, 300, 600]


# =========================
# Функции
# =========================

def fetch_table(url: str):
    """Загружает и возвращает список таблиц со страницы"""
    try:
        print(f"Запрос: {url}")
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        dfs = pd.read_html(StringIO(r.text))
        print(f"Найдено {len(dfs)} таблиц")
        for df in dfs:
            print("Столбцы таблицы:", list(df.columns))
        return dfs
    except Exception as e:
        print(f"Ошибка при запросе {url}: {e}")
        return []


def normalize_table(df: pd.DataFrame, standard, ftype, pclass):
    """Нормализует таблицу ASME — подбирает столбцы автоматически."""
    df.columns = [str(c).strip() for c in df.columns]

    # Карта ключевых слов
    mapping = {
        "nps": ["nps", "nominal pipe size", "nominal size"],
        "D": ["outside diameter", "diameter of flange", "flange dia"],
        "T": ["thickness", "flange thickness"],
        "R": ["radius", "raised face", "hub radius"],
        "Y": ["hub length", "length through hub"],
        "C": ["bolt circle", "bolt circle diameter", "bc"],
        "holes": ["no. of bolts", "number of bolts", "bolt holes"],
        "hole_dia": ["diameter of bolts", "bolt diameter", "diameter of bolt holes"],
    }

    # Создаём пустой результат
    norm = pd.DataFrame()

    for key, keywords in mapping.items():
        for col in df.columns:
            if any(k.lower() in col.lower() for k in keywords):
                norm[key] = df[col]
                break

    # Добавляем обязательные служебные поля
    norm["standard"] = standard
    norm["flange_type"] = ftype
    norm["pressure_class"] = pclass

    return norm


def save_standard_csv(df: pd.DataFrame, standard, ftype, pclass):
    """Сохраняет таблицу в CSV."""
    if df.empty:
        print(f"⚠️ Нет данных для {ftype} {pclass}")
        return

    # Разрешаем неполные наборы столбцов
    cols = ["standard", "flange_type", "pressure_class", "nps", "D", "T", "R", "Y", "C", "holes", "hole_dia"]
    existing_cols = [c for c in cols if c in df.columns]
    out = df[existing_cols]

    fname = SAVE_DIR / f"asme_b16_5_{ftype}_{pclass}.csv"
    out.to_csv(fname, index=False)
    print(f"✅ Сохранён файл: {fname} ({len(out)} строк)")


def main():
    standard = "ASME B16.5"

    for ftype, url in ASME_LINKS:
        for pclass in PRESSURE_CLASSES:
            print(f"\nProcessing: {url} → {ftype} {pclass}")
            dfs = fetch_table(url)
            if not dfs:
                continue
            for df in dfs:
                norm_rows = normalize_table(df, standard, ftype, pclass)
                if not norm_rows.empty:
                    save_standard_csv(norm_rows, standard, ftype, pclass)


if __name__ == "__main__":
    main()
