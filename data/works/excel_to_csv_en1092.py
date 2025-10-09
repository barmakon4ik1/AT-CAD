#!/usr/bin/env python3
# excel_to_csv_en1092.py
# Usage: python excel_to_csv_en1092.py /path/to/EN1092.xlsx /path/to/output_dir

import sys
from pathlib import Path
import pandas as pd
import json

def main(excel_file, out_dir):
    excel_path = Path(excel_file)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    xls = pd.ExcelFile(excel_path)
    sheets = xls.sheet_names

    # Translation maps (DE -> EN, RU)
    flange_type_translations = {
        "01": ("glatter Flansch zum Schwei?en", "Plate flange for welding", "������� ������ ��� ��������"),
        "02": ("loser Flansch fur glatten Bund oder fur Vorschwei?bordel", "Loose flange (for plain or weld-on spigot)", "������� ������ ��� �������� ��� ���������� �����"),
        "04": ("loser Flansch fur Vorschwei?bund", "Loose flange (for weld-on spigot)", "������� ������ ��� ���������� �����"),
        "05": ("Blindflansch", "Blind flange", "������ ������"),
        "11": ("Vorschwei?flansch", "Weld neck flange", "������ ������������"),
        "12": ("Uberschieb-Schwei?flansch mit Ansatz", "Slip-on flange with hub", "��������� (����������) ������ � ������"),
        "13": ("Gewindeflansch mit Ansatz", "Threaded flange with hub", "��������� ������ � ������"),
        "21": ("Integralflansch", "Integral flange", "������� ������"),
        "32": ("glatter Bund", "Plain spigot (hub)", "������� ����"),
        "33": ("gebordeltes Rohrende", "Rolled (beaded) pipe end", "�������������� ��������� �����"),
        "34": ("Vorschwei?bund", "Weld-on spigot (hub)", "��������� ����"),
        "35": ("Vorschwei?ring", "Weld-on ring (collar)", "��������� ������"),
        "36": ("Pressbordel mit langem Ansatz", "Pressed bead with long spigot", "��������� ������ � ������� ������"),
        "37": ("Pressborde", "Pressed bead", "��������� ������")
    }

    sealing_face_translations = {
        "A": ("glatte Dichtflache", "Flat sealing face", "������� �������������� �����������"),
        "B1": ("Dichtleiste (B1)", "Raised face B1 (raised sealing land)", "����������� �������������� ����������� B1"),
        "B2": ("Dichtleiste (B2)", "Raised face B2 (finer finish)", "����������� �������������� ����������� B2"),
        "B1/B2": ("Dichtleiste (B1/B2)", "Raised face (B1/B2)", "����������� �������������� ����������� (B1/B2)"),
        "C": ("Feder", "Tongue (male)", "������ (�������)"),
        "D": ("Nut", "Groove (female)", "��� (�������)"),
        "E": ("Vorsprung", "Spigot / projection", "������ / ����"),
        "F": ("Rucksprung", "Recess", "���������� / �����"),
        "G": ("O-Ring-Vorsprung", "O-ring projection", "������ ��� O-������"),
        "H": ("O-Ring-Nut", "O-ring groove", "��� ��� O-������")
    }

    created = []

    for sheet in sheets:
        try:
            df = pd.read_excel(excel_path, sheet_name=sheet, header=0)
        except Exception:
            df = pd.read_excel(excel_path, sheet_name=sheet, header=None)
        fname = f"{sheet}.csv".replace("/", "_").replace("\\", "_")
        out_path = out_dir / fname
        # Use utf-8-sig so Excel opens correctly with UTF-8 BOM
        df.to_csv(out_path, index=False, encoding="utf-8-sig")
        created.append(str(out_path))
        manifest = {"sheet": sheet, "rows": int(len(df)), "columns": [str(c) for c in df.columns]}
        (out_dir / f"{sheet}_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    # Typ -> translated CSV
    if "Typ" in sheets:
        df_typ = pd.read_excel(excel_path, sheet_name="Typ", header=0)
        rows = []
        for _, r in df_typ.iterrows():
            code = str(r.iloc[0]).strip()
            name_de_orig = str(r.iloc[1]) if len(r)>1 else ""
            de_std, en_name, ru_name = flange_type_translations.get(code, ("", "", ""))
            rows.append({
                "code": code,
                "name_de_original": name_de_orig,
                "name_de_standard": de_std,
                "name_en": en_name,
                "name_ru": ru_name
            })
        pd.DataFrame(rows).to_csv(out_dir / "flange_types_translated.csv", index=False, encoding="utf-8-sig")
        created.append(str(out_dir / "flange_types_translated.csv"))

    # Dichtflaechen -> sealing_faces_translated.csv
    if "Dichtflaechen" in sheets:
        recs = []
        for code, (de, en, ru) in sealing_face_translations.items():
            recs.append({"code": code, "description_de": de, "description_en": en, "description_ru": ru})
        pd.DataFrame(recs).to_csv(out_dir / "sealing_faces_translated.csv", index=False, encoding="utf-8-sig")
        created.append(str(out_dir / "sealing_faces_translated.csv"))

    (out_dir / "manifest_all.json").write_text(json.dumps({"source": str(excel_path), "files": created}, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Created files:", len(created))
    for p in created:
        print("-", p)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python excel_to_csv_en1092.py /path/to/EN1092.xlsx /path/to/output_dir")
    else:
        main(sys.argv[1], sys.argv[2])
