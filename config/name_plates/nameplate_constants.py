# nameplate_constants.py
import os

BASE_DIR = os.path.join("config", "name_plates")

JSON_PATH  = os.path.join(BASE_DIR, "name_plates.json")
IMAGE_PATH = os.path.join(BASE_DIR, "name_plate_image.png")

FIELDS = [
    ("name",   "Name"),
    ("a",      "a"),
    ("b",      "b"),
    ("a1",     "a1"),
    ("b1",     "b1"),
    ("d",      "d"),
    ("r",      "r"),
    ("s",      "s"),
    ("remark", "Remark"),
]
