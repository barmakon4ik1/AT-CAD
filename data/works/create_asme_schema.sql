PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS flange_types (
    id INTEGER PRIMARY KEY,
    code TEXT UNIQUE NOT NULL,      -- WN, SO, LJ, BLIND
    title TEXT
);

CREATE TABLE IF NOT EXISTS pressure_classes (
    id INTEGER PRIMARY KEY,
    class TEXT UNIQUE NOT NULL      -- 150, 300, 600, 900, 1500, 2500
);

CREATE TABLE IF NOT EXISTS asme_flanges (
    id INTEGER PRIMARY KEY,
    flange_type_id INTEGER REFERENCES flange_types(id),
    pressure_class_id INTEGER REFERENCES pressure_classes(id),
    NPS TEXT NOT NULL,              -- NPS (1/2, 3/4, 1, 2, ...)
    D REAL,                         -- Outside Diameter
    T REAL,                         -- Thickness
    R REAL,
    Y REAL,
    C REAL,
    holes INTEGER,
    hole_dia REAL,
    notes TEXT,
    image_path TEXT,
    UNIQUE (flange_type_id, pressure_class_id, NPS)
);
