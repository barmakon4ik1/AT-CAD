# data/import_asme_csvs.py
# Требования: pandas, sqlite3
import sqlite3
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "asme_b16_5.db"

# SQL схема (упрощённая) — создаст таблицу asme_flanges
CREATE_SQL = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS asme_flanges (
    id INTEGER PRIMARY KEY,
    standard TEXT,
    flange_type TEXT,
    pressure_class TEXT,
    nps TEXT,
    D REAL,
    T REAL,
    R REAL,
    Y REAL,
    C REAL,
    holes INTEGER,
    hole_dia REAL,
    notes TEXT,
    UNIQUE (standard, flange_type, pressure_class, nps)
);
"""

def create_db():
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(CREATE_SQL)
    conn.commit()
    conn.close()
    print("DB created:", DB_PATH)

def import_csv(csv_path):
    df = pd.read_csv(csv_path)
    # Приведём названия колонок к общему виду
    df = df.rename(columns=lambda c: c.strip())
    conn = sqlite3.connect(DB_PATH)
    for _, row in df.iterrows():
        # upsert: попробуем обновить, иначе вставим
        conn.execute("""
            INSERT OR REPLACE INTO asme_flanges (id, standard, flange_type, pressure_class, nps, D, T, R, Y, C, holes, hole_dia)
            VALUES (
                (SELECT id FROM asme_flanges WHERE standard=? AND flange_type=? AND pressure_class=? AND nps=?),
                ?,?,?,?,?,?,?,?,?,?
            )
        """, (row.get('standard'), row.get('flange_type'), row.get('pressure_class'), str(row.get('nps')),
              row.get('standard'), row.get('flange_type'), row.get('pressure_class'), str(row.get('nps')),
              row.get('D'), row.get('T'), row.get('R'), row.get('Y'), row.get('C'), int(row.get('holes') or 0), row.get('hole_dia')))
    conn.commit()
    conn.close()
    print("Imported:", csv_path)

def import_all():
    create_db()
    for p in DATA_DIR.glob("asme_*.csv"):
        import_csv(p)

if __name__ == "__main__":
    import_all()
