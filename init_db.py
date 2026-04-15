"""
init_db.py — Initialise database and seed sample data
Run once: python init_db.py
"""
import sqlite3
import os
from datetime import date, timedelta
import random

DB_PATH = os.path.join(os.path.dirname(__file__), 'database.db')
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), 'database', 'schema.sql')

# --- bcrypt for password hashing ---
try:
    from flask_bcrypt import generate_password_hash
    def hash_pw(pw):
        return generate_password_hash(pw).decode('utf-8')
except ImportError:
    import hashlib
    def hash_pw(pw):
        return hashlib.sha256(pw.encode()).hexdigest()

def init_db():
    conn = sqlite3.connect(DB_PATH)
    with open(SCHEMA_PATH, 'r') as f:
        conn.executescript(f.read())

    # --- Seed admin user ---
    conn.execute(
        "INSERT OR IGNORE INTO users (username, password, role) VALUES (?, ?, ?)",
        ('admin', hash_pw('admin123'), 'admin')
    )

    # --- Seed sample students ---
    students = [
        ('63A91F2C', 'Chiranth Kumar',    '1SI22CS045', 'CSE', '3rd', hash_pw('chiranth123')),
        ('82BC117A', 'Ananya Sharma',     '1SI22CS012', 'CSE', '3rd', hash_pw('ananya123')),
        ('04A37B92', 'Ravi Patel',        '1SI22IS034', 'ISE', '3rd', hash_pw('ravi123')),
        ('A1B2C3D4', 'Priya Mehta',       '1SI22EC056', 'ECE', '2nd', hash_pw('priya123')),
        ('F4E3D2C1', 'Arjun Nair',        '1SI22ME078', 'MECH','2nd', hash_pw('arjun123')),
        ('C8D9E1F2', 'Sneha Reddy',       '1SI22CS089', 'CSE', '3rd', hash_pw('sneha123')),
        ('B7A6F5E4', 'Mohammed Faraz',    '1SI22CS023', 'CSE', '3rd', hash_pw('faraz123')),
        ('11223344', 'Kavya Gowda',       '1SI22IS067', 'ISE', '2nd', hash_pw('kavya123')),
    ]
    conn.executemany(
        "INSERT OR IGNORE INTO students (uid, name, usn, branch, year, photo, password) VALUES (?,?,?,?,?,?,?)",
        [(s[0], s[1], s[2], s[3], s[4], None, s[5]) for s in students]
    )

    # --- Seed 60 days of attendance ---
    today = date.today()
    statuses = ['present', 'present', 'present', 'present', 'late', 'absent']
    for i in range(60):
        d = today - timedelta(days=i)
        if d.weekday() >= 5:   # skip weekends
            continue
        for uid, *_ in students:
            st = random.choice(statuses)
            if st == 'absent':
                continue
            t = '09:05' if st == 'present' else '09:45'
            try:
                conn.execute(
                    "INSERT OR IGNORE INTO attendance (uid, date, time, status) VALUES (?,?,?,?)",
                    (uid, d.isoformat(), t, st)
                )
            except Exception:
                pass

    conn.commit()
    conn.close()
    print("✅  Database initialised at", DB_PATH)
    print("    Admin credentials → username: admin  |  password: admin123")
    print("    Student login     → USN (e.g. 1SI22CS045) | password: chiranth123")

if __name__ == '__main__':
    init_db()
