# data/import_flanges.py
import json
import re
import sys
from pathlib import Path

# чтобы можно было импортировать programs.flange_models, запускаем скрипт из корня проекта
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from programs.flange_models import db, Flange, init_db

JSON_FILE = PROJECT_ROOT / "data" / "flanges.json"

def normalize_type(type_key: str) -> str:
    # 'weld_neck_flange_mm' -> 'weld_neck'
    t = re.sub(r'_flange.*', '', type_key)
    return t

def normalize_class(class_key: str) -> str:
    # 'class_150' -> '150'
    m = re.search(r'(\d+)', class_key)
    return m.group(1) if m else class_key

def import_json():
    if not JSON_FILE.exists():
        print("Не найден файл:", JSON_FILE)
        return

    init_db()
    db.connect(reuse_if_open=True)

    with open(JSON_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    added = 0
    updated = 0

    for standard, types in data.items():
        for type_key, classes in types.items():
            ftype = normalize_type(type_key)
            for class_key, records in classes.items():
                pclass = normalize_class(class_key)
                for rec in records:
                    nps = rec.get("NPS")
                    query = Flange.select().where(
                        (Flange.standard == standard) &
                        (Flange.type == ftype) &
                        (Flange.pressure_class == pclass) &
                        (Flange.nps == nps)
                    )
                    if query.exists():
                        flange = query.get()
                        # обновляем поля, если они есть в JSON
                        changed = False
                        for field in ("D","T","R","Y","C","holes","hole_dia"):
                            val = rec.get(field)
                            if val is not None:
                                setattr(flange, field, val)
                                changed = True
                        if changed:
                            flange.save()
                            updated += 1
                    else:
                        Flange.create(
                            standard=standard,
                            type=ftype,
                            pressure_class=pclass,
                            nps=nps,
                            D=rec.get("D"),
                            T=rec.get("T"),
                            R=rec.get("R"),
                            Y=rec.get("Y"),
                            C=rec.get("C"),
                            holes=rec.get("holes"),
                            hole_dia=rec.get("hole_dia")
                        )
                        added += 1

    print(f"Импорт завершён. Добавлено: {added}, Обновлено: {updated}")

if __name__ == "__main__":
    import_json()
