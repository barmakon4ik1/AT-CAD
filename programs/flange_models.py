# programs/flange_models.py
from peewee import SqliteDatabase, Model, FloatField, CharField, IntegerField, ForeignKeyField, TextField
from pathlib import Path

DB_PATH_ASME = Path(__file__).resolve().parents[1] / "data" / "asme_b16_5.db"
DB_PATH_EN = Path(__file__).resolve().parents[1] / "data" / "en_1092_1.db"

db_asme = SqliteDatabase(DB_PATH_ASME)
db_en = SqliteDatabase(DB_PATH_EN)

class BaseModel(Model):
    class Meta:
        database = None  # подставляется динамически


class ASMEFlange(BaseModel):
    NPS = CharField()
    D = FloatField(null=True)
    T = FloatField(null=True)
    R = FloatField(null=True)
    Y = FloatField(null=True)
    C = FloatField(null=True)
    holes = IntegerField(null=True)
    hole_dia = FloatField(null=True)

    class Meta:
        database = db_asme
        table_name = "asme_flanges"


class Flange(BaseModel):
    standard = CharField(index=True)        # example: "ASME_B16.5"
    type = CharField(index=True)            # example: "weld_neck"
    pressure_class = CharField(index=True)  # example: "150"
    nps = CharField(index=True)             # example: "1/2"
    D = FloatField(null=True)
    T = FloatField(null=True)    # высота/толщина, которую будешь использовать
    R = FloatField(null=True)
    Y = FloatField(null=True)
    C = FloatField(null=True)
    holes = IntegerField(null=True)
    hole_dia = FloatField(null=True)
    notes = TextField(null=True)
    image = CharField(null=True)  # путь к картинке/легенде (опционально)

    class Meta:
        table_name = "flanges"

