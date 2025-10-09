PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS flange_types (
    id INTEGER PRIMARY KEY,
    code TEXT UNIQUE NOT NULL,      -- 01, 05, 11
    title TEXT
);

CREATE TABLE IF NOT EXISTS pressure_classes (
    id INTEGER PRIMARY KEY,
    pn TEXT UNIQUE NOT NULL         -- PN6, PN10, PN16, PN25, PN40, ...
);

CREATE TABLE IF NOT EXISTS face_types (
    id INTEGER PRIMARY KEY,
    code TEXT UNIQUE NOT NULL,      -- A, B1, B2, C, D, E, F
    description TEXT
);

CREATE TABLE IF NOT EXISTS en_flanges (
    id INTEGER PRIMARY KEY,
    flange_type_id INTEGER REFERENCES flange_types(id),
    pressure_class_id INTEGER REFERENCES pressure_classes(id),
    face_type_id INTEGER REFERENCES face_types(id),

    DN INTEGER NOT NULL,
    D REAL, K REAL, L REAL, A REAL,
    C2 REAL, C3 REAL, C4 REAL,
    H2 REAL, H3 REAL,
    N1 REAL, N3 REAL, R1 REAL,
    s REAL, fastener_count INTEGER, fastener_size TEXT,

    d1 REAL, f1 REAL, f2 REAL, f3 REAL, f4 REAL, x REAL, w REAL, y REAL, z REAL,
    notes TEXT,
    image_path TEXT,

    UNIQUE (flange_type_id, pressure_class_id, face_type_id, DN)
);
