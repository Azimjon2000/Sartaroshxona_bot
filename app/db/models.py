SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    telegram_id  INTEGER PRIMARY KEY,
    role         TEXT NOT NULL CHECK(role IN ('client','barber','admin')),
    created_at   TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS admins (
    telegram_id  INTEGER PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS clients (
    telegram_id    INTEGER PRIMARY KEY,
    name           TEXT NOT NULL,
    phone          TEXT,
    lang           TEXT NOT NULL DEFAULT 'uz' CHECK(lang IN ('uz','ru')),
    ref_barber_id  INTEGER,
    ref_lock_date  TEXT,
    created_at     TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS barbers (
    telegram_id     INTEGER PRIMARY KEY,
    id              INTEGER UNIQUE,
    name            TEXT NOT NULL,
    salon_name      TEXT NOT NULL,
    phone           TEXT NOT NULL,
    region_id       INTEGER NOT NULL,
    district_id     INTEGER NOT NULL,
    photo_file_id   TEXT,
    lat             REAL,
    lon             REAL,
    status          TEXT NOT NULL DEFAULT 'PENDING'
                    CHECK(status IN ('PENDING','APPROVED','BLOCKED')),
    lang            TEXT NOT NULL DEFAULT 'uz' CHECK(lang IN ('uz','ru')),
    premium_status  TEXT DEFAULT 'INACTIVE',
    premium_until   TEXT,
    is_blocked_temp INTEGER DEFAULT 0,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (region_id) REFERENCES regions(id),
    FOREIGN KEY (district_id) REFERENCES districts(id)
);

CREATE TABLE IF NOT EXISTS regions (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    name_uz TEXT NOT NULL,
    name_ru TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS districts (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    region_id INTEGER NOT NULL,
    name_uz   TEXT NOT NULL,
    name_ru   TEXT NOT NULL,
    FOREIGN KEY (region_id) REFERENCES regions(id)
);

CREATE TABLE IF NOT EXISTS work_hours (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    barber_id  INTEGER NOT NULL,
    hour_slot  INTEGER NOT NULL CHECK(hour_slot BETWEEN 0 AND 15),
    is_enabled INTEGER NOT NULL DEFAULT 0,
    UNIQUE(barber_id, hour_slot),
    FOREIGN KEY (barber_id) REFERENCES barbers(telegram_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS services_prices (
    barber_id   INTEGER PRIMARY KEY,
    hair_price  INTEGER DEFAULT 0,
    beard_price INTEGER DEFAULT 0,
    groom_price INTEGER DEFAULT 0,
    extra_note  TEXT DEFAULT '' CHECK(length(extra_note) <= 300),
    FOREIGN KEY (barber_id) REFERENCES barbers(telegram_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS media_photos (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    barber_id  INTEGER NOT NULL,
    file_id    TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (barber_id) REFERENCES barbers(telegram_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS media_videos (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    barber_id  INTEGER NOT NULL,
    file_id    TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (barber_id) REFERENCES barbers(telegram_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS bookings (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    barber_id      INTEGER NOT NULL,
    client_id      INTEGER NOT NULL,
    date           TEXT NOT NULL,
    hour_slot      INTEGER NOT NULL,
    status         TEXT NOT NULL DEFAULT 'DRAFT'
                   CHECK(status IN ('DRAFT','CONFIRMED','CANCELLED','DONE','EXPIRED')),
    created_at     TEXT NOT NULL DEFAULT (datetime('now')),
    confirmed_at   TEXT,
    created_date   TEXT,
    reminded       INTEGER DEFAULT 0,
    is_active      INTEGER DEFAULT 1,
    FOREIGN KEY (barber_id) REFERENCES barbers(telegram_id) ON DELETE CASCADE,
    FOREIGN KEY (client_id) REFERENCES clients(telegram_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS ratings (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    booking_id INTEGER NOT NULL UNIQUE,
    barber_id  INTEGER NOT NULL,
    client_id  INTEGER NOT NULL,
    stars      INTEGER NOT NULL CHECK(stars BETWEEN 1 AND 5),
    comment    TEXT CHECK(comment IS NULL OR length(comment) <= 300),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (booking_id) REFERENCES bookings(id) ON DELETE CASCADE,
    FOREIGN KEY (barber_id) REFERENCES barbers(telegram_id) ON DELETE CASCADE,
    FOREIGN KEY (client_id) REFERENCES clients(telegram_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

INSERT OR IGNORE INTO settings (key, value) VALUES ('support_username', '@admin');
INSERT OR IGNORE INTO settings (key, value) VALUES ('premium_price', '150000');
INSERT OR IGNORE INTO settings (key, value) VALUES ('payment_card', '8600 0000 0000 0000');
INSERT OR IGNORE INTO settings (key, value) VALUES ('support_profile', '@admin');

CREATE TABLE IF NOT EXISTS reminder_log (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    barber_id  INTEGER NOT NULL,
    client_id  INTEGER NOT NULL,
    sent_at    TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(barber_id, client_id),
    FOREIGN KEY (barber_id) REFERENCES barbers(telegram_id) ON DELETE CASCADE,
    FOREIGN KEY (client_id) REFERENCES clients(telegram_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS penalties (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id   INTEGER NOT NULL,
    date        TEXT NOT NULL,
    reason      TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (client_id) REFERENCES clients(telegram_id) ON DELETE CASCADE
);

-- MANDATORY INDEXES FOR PERFORMANCE
CREATE INDEX IF NOT EXISTS idx_barbers_search ON barbers(status, lat, lon);
CREATE INDEX IF NOT EXISTS idx_bookings_barber ON bookings(barber_id, date, status);
CREATE INDEX IF NOT EXISTS idx_bookings_client ON bookings(client_id, status, date);
CREATE INDEX IF NOT EXISTS idx_ratings_barber ON ratings(barber_id);
CREATE INDEX IF NOT EXISTS idx_barbers_premium ON barbers(premium_status, premium_until);
CREATE INDEX IF NOT EXISTS idx_bookings_reminded ON bookings(date, status, reminded);
"""
