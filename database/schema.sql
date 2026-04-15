-- RFID Attendance System Database Schema

CREATE TABLE IF NOT EXISTS students (
    uid       TEXT PRIMARY KEY,
    name      TEXT NOT NULL,
    usn       TEXT UNIQUE NOT NULL,
    branch    TEXT,
    year      TEXT,
    photo     TEXT,
    password  TEXT
);

CREATE TABLE IF NOT EXISTS attendance (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    uid     TEXT NOT NULL,
    date    TEXT NOT NULL,
    time    TEXT NOT NULL,
    status  TEXT DEFAULT 'present',
    FOREIGN KEY (uid) REFERENCES students(uid),
    UNIQUE(uid, date)
);

CREATE TABLE IF NOT EXISTS users (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    username  TEXT UNIQUE NOT NULL,
    password  TEXT NOT NULL,
    role      TEXT NOT NULL DEFAULT 'admin'
);

CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT
);

-- Default settings
INSERT OR IGNORE INTO settings (key, value) VALUES ('cutoff_time', '09:30');
INSERT OR IGNORE INTO settings (key, value) VALUES ('late_threshold', '09:00');
INSERT OR IGNORE INTO settings (key, value) VALUES ('min_attendance', '75');
INSERT OR IGNORE INTO settings (key, value) VALUES ('api_key', 'rfid-secret-key-2024');
