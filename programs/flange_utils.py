# programs/flange_utils.py
from programs.flange_models import db, Flange

def get_flange_height(standard, flange_type, nps, pressure_class):
    db.connect(reuse_if_open=True)
    try:
        f = Flange.get(
            (Flange.standard == standard) &
            (Flange.type == flange_type) &
            (Flange.nps == nps) &
            (Flange.pressure_class == pressure_class)
        )
        return f.T  # если нужно — можно вернуть целый объект f
    except Flange.DoesNotExist:
        return None
