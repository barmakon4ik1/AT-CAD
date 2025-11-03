from config.at_cad_init import ATCadInit
from programs.at_input import at_get_entity
import pythoncom

def dump_entity_info(ent):
    print("\n--- Entity info ---")
    try:
        print("ObjectName:", ent.ObjectName)
    except Exception as e:
        print("ObjectName error:", e)
    for prop in ["Layer", "Color", "Closed", "Coordinates", "Center", "Radius", "ObjectID"]:
        try:
            val = getattr(ent, prop)
            if isinstance(val, (list, tuple)):
                print(f"{prop}: len={len(val)}")
            else:
                print(f"{prop}: {val}")
        except Exception as e:
            print(f"{prop}: error: {e}")

def main():
    pythoncom.CoInitialize()
    cad = ATCadInit()
    doc = cad.document

    print("Выберите объект (любая полилиния или окружность):")
    ent, _, ok, enter, esc = at_get_entity(use_bridge=False, prompt="Выберите объект:")
    if not ok or ent is None:
        print("Не выбран.")
        return

    dump_entity_info(ent)

if __name__ == "__main__":
    main()
