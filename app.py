"""
app.py — RFID Attendance System Backend
Flask application with authentication, RFID scan handling, CRUD, analytics, and export.
"""
import os, sqlite3, csv, io
from datetime import date, timedelta, datetime
from functools import wraps
from flask import (Flask, render_template, request, jsonify, redirect, url_for,
                   session, flash, send_file, abort)
from flask_bcrypt import Bcrypt
from flask_login import (LoginManager, UserMixin, login_user, logout_user,
                         login_required, current_user)
from flask_cors import CORS
from werkzeug.utils import secure_filename

# ──────────────────────────── App Setup ────────────────────────────
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
DB_PATH    = os.path.join(BASE_DIR, 'database.db')
UPLOAD_DIR = os.path.join(BASE_DIR, 'static', 'images')
ALLOWED_EXT = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

app = Flask(__name__)
app.secret_key = 'rfid-attendance-super-secret-2024'
CORS(app)
bcrypt  = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

os.makedirs(UPLOAD_DIR, exist_ok=True)

# ──────────────────────────── DB Helpers ───────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def query(sql, args=(), one=False, commit=False):
    conn = get_db()
    cur  = conn.execute(sql, args)
    if commit:
        conn.commit()
        conn.close()
        return cur.lastrowid
    rv = cur.fetchone() if one else cur.fetchall()
    conn.close()
    return rv

def get_setting(key, default=None):
    row = query("SELECT value FROM settings WHERE key=?", (key,), one=True)
    return row['value'] if row else default

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXT

# ──────────────────────────── User Model ───────────────────────────
class User(UserMixin):
    def __init__(self, id, username, role, is_student=False, uid=None):
        self.id         = str(id)
        self.username   = username
        self.role       = role
        self.is_student = is_student
        self.uid        = uid

    def get_id(self):
        return f"{'s' if self.is_student else 'a'}:{self.id}"

@login_manager.user_loader
def load_user(user_id):
    prefix, uid = user_id.split(':', 1)
    if prefix == 'a':
        row = query("SELECT * FROM users WHERE id=?", (uid,), one=True)
        if row:
            return User(row['id'], row['username'], row['role'])
    else:
        row = query("SELECT * FROM students WHERE usn=?", (uid,), one=True)
        if row:
            return User(row['usn'], row['usn'], 'student', is_student=True, uid=row['uid'])
    return None

# ──────────────────────────── Decorators ───────────────────────────
def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role not in ('admin', 'teacher'):
            abort(403)
        return f(*args, **kwargs)
    return decorated

def student_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'student':
            abort(403)
        return f(*args, **kwargs)
    return decorated

def api_key_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        key = request.headers.get('X-API-Key') or request.json.get('api_key', '')
        expected = get_setting('api_key', 'rfid-secret-key-2024')
        if key != expected:
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated

# ──────────────────────────────────────────────────────────────────
#                        AUTH ROUTES
# ──────────────────────────────────────────────────────────────────
@app.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.role == 'student':
            return redirect(url_for('student_dashboard'))
        return redirect(url_for('admin_dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        login_type = request.form.get('login_type', 'admin')
        username   = request.form.get('username', '').strip()
        password   = request.form.get('password', '').strip()

        if login_type == 'student':
            row = query("SELECT * FROM students WHERE usn=?", (username,), one=True)
            if row and row['password'] and bcrypt.check_password_hash(row['password'], password):
                user = User(row['usn'], row['usn'], 'student', is_student=True, uid=row['uid'])
                login_user(user)
                return redirect(url_for('student_dashboard'))
            flash('Invalid USN or password.', 'danger')
        else:
            row = query("SELECT * FROM users WHERE username=?", (username,), one=True)
            if row and bcrypt.check_password_hash(row['password'], password):
                user = User(row['id'], row['username'], row['role'])
                login_user(user)
                return redirect(url_for('admin_dashboard'))
            flash('Invalid username or password.', 'danger')

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# ──────────────────────────────────────────────────────────────────
#                       ADMIN ROUTES
# ──────────────────────────────────────────────────────────────────
@app.route('/admin/dashboard')
@login_required
@admin_required
def admin_dashboard():
    return render_template('admin/dashboard.html')

@app.route('/admin/students')
@login_required
@admin_required
def admin_students():
    return render_template('admin/students.html')

@app.route('/admin/attendance')
@login_required
@admin_required
def admin_attendance():
    return render_template('admin/attendance.html')

@app.route('/admin/analytics')
@login_required
@admin_required
def admin_analytics():
    return render_template('admin/analytics.html')

@app.route('/admin/reports')
@login_required
@admin_required
def admin_reports():
    return render_template('admin/reports.html')

@app.route('/admin/settings')
@login_required
@admin_required
def admin_settings():
    return render_template('admin/settings.html')

# ──────────────────────────────────────────────────────────────────
#                      STUDENT ROUTES
# ──────────────────────────────────────────────────────────────────
@app.route('/student/dashboard')
@login_required
@student_required
def student_dashboard():
    return render_template('student/dashboard.html')

@app.route('/student/attendance')
@login_required
@student_required
def student_attendance():
    return render_template('student/attendance.html')

@app.route('/student/analytics')
@login_required
@student_required
def student_analytics():
    return render_template('student/analytics.html')

@app.route('/student/profile')
@login_required
@student_required
def student_profile():
    return render_template('student/profile.html')

# ──────────────────────────────────────────────────────────────────
#                    ESP32 SCAN ENDPOINT
# ──────────────────────────────────────────────────────────────────
@app.route('/api/scan', methods=['POST'])
@api_key_required
def api_scan():
    data = request.get_json(force=True)
    uid  = data.get('uid', '').upper().strip()
    if not uid:
        return jsonify({'status': 'error', 'message': 'UID missing'}), 400

    student = query("SELECT * FROM students WHERE uid=?", (uid,), one=True)
    if not student:
        return jsonify({'status': 'unknown', 'message': 'UID not registered'}), 404

    today    = date.today().isoformat()
    now_time = datetime.now().strftime('%H:%M:%S')
    cutoff   = get_setting('cutoff_time', '09:30')
    late_thr = get_setting('late_threshold', '09:00')

    existing = query("SELECT * FROM attendance WHERE uid=? AND date=?", (uid, today), one=True)
    if existing:
        return jsonify({
            'status':  'duplicate',
            'message': f"Already marked {existing['status']} at {existing['time']}",
            'name':    student['name']
        }), 200

    status = 'present'
    if now_time > cutoff:
        status = 'absent'
    elif now_time > late_thr:
        status = 'late'

    query(
        "INSERT INTO attendance (uid, date, time, status) VALUES (?,?,?,?)",
        (uid, today, now_time, status), commit=True
    )
    return jsonify({
        'status':  'success',
        'message': f"Attendance marked: {status}",
        'name':    student['name'],
        'usn':     student['usn'],
        'time':    now_time
    }), 200

# ──────────────────────────────────────────────────────────────────
#                   ADMIN API ENDPOINTS
# ──────────────────────────────────────────────────────────────────

# ---- Dashboard stats ----
@app.route('/api/dashboard/stats')
@login_required
@admin_required
def api_dashboard_stats():
    today = date.today().isoformat()
    total   = query("SELECT COUNT(*) c FROM students", one=True)['c']
    present = query("SELECT COUNT(*) c FROM attendance WHERE date=? AND status='present'", (today,), one=True)['c']
    late    = query("SELECT COUNT(*) c FROM attendance WHERE date=? AND status='late'", (today,), one=True)['c']
    absent  = total - present - late
    pct     = round((present + late) / total * 100, 1) if total else 0
    return jsonify({'total': total, 'present': present, 'late': late,
                    'absent': absent, 'percentage': pct})

# ---- Live feed ----
@app.route('/api/attendance/live')
@login_required
@admin_required
def api_attendance_live():
    today = date.today().isoformat()
    rows  = query("""
        SELECT a.id, a.uid, a.time, a.status, s.name, s.usn, s.branch, s.year
        FROM attendance a JOIN students s ON a.uid=s.uid
        WHERE a.date=? ORDER BY a.time DESC LIMIT 20
    """, (today,))
    return jsonify([dict(r) for r in rows])

# ---- All attendance (filterable) ----
@app.route('/api/attendance')
@login_required
@admin_required
def api_attendance():
    date_from = request.args.get('from', (date.today() - timedelta(days=30)).isoformat())
    date_to   = request.args.get('to',   date.today().isoformat())
    branch    = request.args.get('branch', '')
    uid       = request.args.get('uid', '')

    sql  = """SELECT a.id, a.uid, a.date, a.time, a.status,
                     s.name, s.usn, s.branch, s.year
              FROM attendance a JOIN students s ON a.uid=s.uid
              WHERE a.date BETWEEN ? AND ?"""
    args = [date_from, date_to]

    if branch:
        sql += " AND s.branch=?"
        args.append(branch)
    if uid:
        sql += " AND a.uid=?"
        args.append(uid)

    sql += " ORDER BY a.date DESC, a.time DESC"
    rows = query(sql, args)
    return jsonify([dict(r) for r in rows])

# ---- Edit attendance ----
@app.route('/api/attendance/<int:att_id>', methods=['PUT'])
@login_required
@admin_required
def api_edit_attendance(att_id):
    data   = request.get_json()
    status = data.get('status', 'present')
    query("UPDATE attendance SET status=? WHERE id=?", (status, att_id), commit=True)
    return jsonify({'success': True})

# ---- Delete attendance ----
@app.route('/api/attendance/<int:att_id>', methods=['DELETE'])
@login_required
@admin_required
def api_delete_attendance(att_id):
    query("DELETE FROM attendance WHERE id=?", (att_id,), commit=True)
    return jsonify({'success': True})

# ---- Manual attendance mark ----
@app.route('/api/attendance/manual', methods=['POST'])
@login_required
@admin_required
def api_manual_attendance():
    data = request.get_json()
    uid    = data.get('uid', '').upper()
    d      = data.get('date', date.today().isoformat())
    t      = data.get('time', '09:00')
    status = data.get('status', 'present')
    try:
        query("INSERT OR REPLACE INTO attendance (uid, date, time, status) VALUES (?,?,?,?)",
              (uid, d, t, status), commit=True)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

# ---- Students list ----
@app.route('/api/students', methods=['GET'])
@login_required
@admin_required
def api_students():
    rows = query("SELECT uid, name, usn, branch, year, photo FROM students ORDER BY name")
    return jsonify([dict(r) for r in rows])

# ---- Add student ----
@app.route('/api/students', methods=['POST'])
@login_required
@admin_required
def api_add_student():
    data     = request.get_json()
    uid      = data.get('uid', '').upper().strip()
    name     = data.get('name', '').strip()
    usn      = data.get('usn', '').strip()
    branch   = data.get('branch', '').strip()
    year     = data.get('year', '').strip()
    password = data.get('password', usn + '123')

    if not uid or not name or not usn:
        return jsonify({'error': 'uid, name, usn are required'}), 400
    try:
        hashed = bcrypt.generate_password_hash(password).decode('utf-8')
        query("INSERT INTO students (uid, name, usn, branch, year, password) VALUES (?,?,?,?,?,?)",
              (uid, name, usn, branch, year, hashed), commit=True)
        return jsonify({'success': True})
    except sqlite3.IntegrityError as e:
        return jsonify({'error': str(e)}), 409

# ---- Edit student ----
@app.route('/api/students/<uid>', methods=['PUT'])
@login_required
@admin_required
def api_edit_student(uid):
    data   = request.get_json()
    fields = {k: v for k, v in data.items() if k in ('name','branch','year','usn')}
    if 'password' in data and data['password']:
        fields['password'] = bcrypt.generate_password_hash(data['password']).decode('utf-8')
    set_clause = ', '.join(f"{k}=?" for k in fields)
    query(f"UPDATE students SET {set_clause} WHERE uid=?",
          list(fields.values()) + [uid.upper()], commit=True)
    return jsonify({'success': True})

# ---- Delete student ----
@app.route('/api/students/<uid>', methods=['DELETE'])
@login_required
@admin_required
def api_delete_student(uid):
    query("DELETE FROM attendance WHERE uid=?", (uid.upper(),), commit=True)
    query("DELETE FROM students WHERE uid=?",   (uid.upper(),), commit=True)
    return jsonify({'success': True})

# ---- Upload student photo ----
@app.route('/api/students/<uid>/photo', methods=['POST'])
@login_required
@admin_required
def api_upload_photo(uid):
    if 'photo' not in request.files:
        return jsonify({'error': 'No file'}), 400
    f = request.files['photo']
    if f and allowed_file(f.filename):
        filename = secure_filename(f"{uid}.{f.filename.rsplit('.',1)[1].lower()}")
        f.save(os.path.join(UPLOAD_DIR, filename))
        query("UPDATE students SET photo=? WHERE uid=?", (filename, uid.upper()), commit=True)
        return jsonify({'success': True, 'filename': filename})
    return jsonify({'error': 'Invalid file type'}), 400

# ──────────────────────────────────────────────────────────────────
#                     ANALYTICS API
# ──────────────────────────────────────────────────────────────────
@app.route('/api/analytics/trend')
@login_required
@admin_required
def api_trend():
    days   = int(request.args.get('days', 30))
    rows   = query("""
        SELECT date, COUNT(*) c FROM attendance
        WHERE date >= ? AND status IN ('present','late')
        GROUP BY date ORDER BY date
    """, ((date.today() - timedelta(days=days)).isoformat(),))
    return jsonify([dict(r) for r in rows])

@app.route('/api/analytics/branch')
@login_required
@admin_required
def api_branch():
    rows = query("""
        SELECT s.branch,
               COUNT(DISTINCT s.uid) total_students,
               COUNT(a.id) present_count
        FROM students s
        LEFT JOIN attendance a ON s.uid=a.uid AND a.status IN ('present','late')
        GROUP BY s.branch
    """)
    return jsonify([dict(r) for r in rows])

@app.route('/api/analytics/top-students')
@login_required
@admin_required
def api_top_students():
    rows = query("""
        SELECT s.name, s.usn, s.branch,
               COUNT(a.id) AS present_days
        FROM students s
        LEFT JOIN attendance a ON s.uid=a.uid AND a.status IN ('present','late')
        GROUP BY s.uid ORDER BY present_days DESC LIMIT 10
    """)
    return jsonify([dict(r) for r in rows])

@app.route('/api/analytics/low-attendance')
@login_required
@admin_required
def api_low_attendance():
    min_pct = float(get_setting('min_attendance', '75'))
    rows    = query("""
        SELECT s.name, s.usn, s.branch,
               COUNT(a.id) AS present_days,
               (SELECT COUNT(DISTINCT date) FROM attendance) AS total_days
        FROM students s
        LEFT JOIN attendance a ON s.uid=a.uid AND a.status IN ('present','late')
        GROUP BY s.uid
    """)
    result = []
    for r in rows:
        r = dict(r)
        total = r['total_days'] or 1
        r['percentage'] = round(r['present_days'] / total * 100, 1)
        if r['percentage'] < min_pct:
            result.append(r)
    result.sort(key=lambda x: x['percentage'])
    return jsonify(result[:10])

# ──────────────────────────────────────────────────────────────────
#                     SETTINGS API
# ──────────────────────────────────────────────────────────────────
@app.route('/api/settings', methods=['GET'])
@login_required
@admin_required
def api_get_settings():
    rows = query("SELECT key, value FROM settings")
    return jsonify({r['key']: r['value'] for r in rows})

@app.route('/api/settings', methods=['POST'])
@login_required
@admin_required
def api_save_settings():
    data = request.get_json()
    for k, v in data.items():
        query("INSERT OR REPLACE INTO settings (key, value) VALUES (?,?)", (k, v), commit=True)
    return jsonify({'success': True})

# ──────────────────────────────────────────────────────────────────
#                     EXPORT ENDPOINTS
# ──────────────────────────────────────────────────────────────────
@app.route('/api/export/csv')
@login_required
@admin_required
def api_export_csv():
    date_from = request.args.get('from', (date.today() - timedelta(days=30)).isoformat())
    date_to   = request.args.get('to',   date.today().isoformat())
    rows = query("""
        SELECT s.name, s.usn, s.branch, s.year, a.date, a.time, a.status
        FROM attendance a JOIN students s ON a.uid=s.uid
        WHERE a.date BETWEEN ? AND ?
        ORDER BY a.date DESC, s.name
    """, (date_from, date_to))

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Name', 'USN', 'Branch', 'Year', 'Date', 'Time', 'Status'])
    for r in rows:
        writer.writerow([r['name'], r['usn'], r['branch'], r['year'],
                         r['date'], r['time'], r['status']])
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode()),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'attendance_{date_from}_to_{date_to}.csv'
    )

@app.route('/api/export/pdf')
@login_required
@admin_required
def api_export_pdf():
    try:
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib import colors

        date_from = request.args.get('from', (date.today() - timedelta(days=7)).isoformat())
        date_to   = request.args.get('to',   date.today().isoformat())
        rows = query("""
            SELECT s.name, s.usn, s.branch, a.date, a.time, a.status
            FROM attendance a JOIN students s ON a.uid=s.uid
            WHERE a.date BETWEEN ? AND ?
            ORDER BY a.date DESC, s.name
        """, (date_from, date_to))

        buf    = io.BytesIO()
        doc    = SimpleDocTemplate(buf, pagesize=landscape(A4))
        styles = getSampleStyleSheet()
        elems  = []

        elems.append(Paragraph('RFID Attendance Report', styles['Title']))
        elems.append(Paragraph(f'{date_from} — {date_to}', styles['Normal']))
        elems.append(Spacer(1, 12))

        data = [['Name', 'USN', 'Branch', 'Date', 'Time', 'Status']]
        for r in rows:
            data.append([r['name'], r['usn'], r['branch'], r['date'], r['time'], r['status']])

        t = Table(data, repeatRows=1)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#6c63ff')),
            ('TEXTCOLOR',  (0,0), (-1,0), colors.white),
            ('FONTNAME',   (0,0), (-1,0), 'Helvetica-Bold'),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f4f4ff')]),
            ('GRID',       (0,0), (-1,-1), 0.5, colors.HexColor('#dddddd')),
            ('FONTSIZE',   (0,0), (-1,-1), 9),
        ]))
        elems.append(t)
        doc.build(elems)
        buf.seek(0)
        return send_file(buf, mimetype='application/pdf', as_attachment=True,
                         download_name=f'attendance_{date_from}_to_{date_to}.pdf')
    except ImportError:
        return jsonify({'error': 'reportlab not installed. Run: pip install reportlab'}), 500

# ──────────────────────────────────────────────────────────────────
#                   STUDENT API ENDPOINTS
# ──────────────────────────────────────────────────────────────────
@app.route('/api/my/info')
@login_required
@student_required
def api_my_info():
    row = query("SELECT uid, name, usn, branch, year, photo FROM students WHERE usn=?",
                (current_user.username,), one=True)
    if not row:
        abort(404)
    return jsonify(dict(row))

@app.route('/api/my/attendance')
@login_required
@student_required
def api_my_attendance():
    row = query("SELECT uid FROM students WHERE usn=?", (current_user.username,), one=True)
    if not row:
        return jsonify([])
    rows = query("""
        SELECT date, time, status FROM attendance
        WHERE uid=? ORDER BY date DESC
    """, (row['uid'],))
    return jsonify([dict(r) for r in rows])

@app.route('/api/my/analytics')
@login_required
@student_required
def api_my_analytics():
    row = query("SELECT uid FROM students WHERE usn=?", (current_user.username,), one=True)
    if not row:
        return jsonify({})
    uid      = row['uid']
    total_d  = query("SELECT COUNT(DISTINCT date) c FROM attendance", one=True)['c']
    present  = query("SELECT COUNT(*) c FROM attendance WHERE uid=? AND status IN ('present','late')", (uid,), one=True)['c']
    late     = query("SELECT COUNT(*) c FROM attendance WHERE uid=? AND status='late'", (uid,), one=True)['c']
    absent   = total_d - present
    pct      = round(present / total_d * 100, 1) if total_d else 0
    min_pct  = float(get_setting('min_attendance', '75'))

    # Classes needed
    needed = 0
    if pct < min_pct and total_d > 0:
        # solve: (present+x)/(total_d+x) >= min_pct/100
        x = 0
        while True:
            if total_d + x == 0:
                break
            if (present + x) / (total_d + x) * 100 >= min_pct:
                needed = x
                break
            x += 1
            if x > 200:
                needed = 999
                break

    monthly = query("""
        SELECT strftime('%Y-%m', date) AS month, COUNT(*) c
        FROM attendance WHERE uid=? AND status IN ('present','late')
        GROUP BY month ORDER BY month
    """, (uid,))

    return jsonify({
        'total_days': total_d,
        'present':    present,
        'late':       late,
        'absent':     absent,
        'percentage': pct,
        'min_pct':    min_pct,
        'needed':     needed,
        'monthly':    [dict(r) for r in monthly]
    })

@app.route('/api/my/profile', methods=['PUT'])
@login_required
@student_required
def api_update_profile():
    data = request.get_json()
    if 'password' in data and data['password']:
        hashed = bcrypt.generate_password_hash(data['password']).decode('utf-8')
        query("UPDATE students SET password=? WHERE usn=?",
              (hashed, current_user.username), commit=True)
    return jsonify({'success': True})

# ──────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    # Auto-init DB if not present
    if not os.path.exists(DB_PATH):
        print("⚠️  database.db not found. Run: python init_db.py")
    app.run(debug=True, host='0.0.0.0', port=5001)
