
"""
Database Module for Smart Attendance System
Handles SQLite operations for students, attendance sessions, attendance records, and face images.
"""

import sqlite3
from datetime import date, datetime
from contextlib import contextmanager
from werkzeug.security import generate_password_hash

import os
DATABASE_NAME = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'attendance.db')


@contextmanager
def get_connection():
    """Context manager for database connections."""
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    """Initialize database tables if they don't exist."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Create teachers table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS teachers (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT DEFAULT '',
                department TEXT DEFAULT '',
                password_hash TEXT
            )
        ''')
        
        # Create students table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS students (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT DEFAULT '',
                enrolled INTEGER DEFAULT 1,
                password_hash TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Migration: add email column if it doesn't exist (for existing databases)
        try:
            cursor.execute("ALTER TABLE students ADD COLUMN email TEXT DEFAULT ''")
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        # Create attendance_sessions table (teacher-enabled per class/hour)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS attendance_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject TEXT NOT NULL,
                hour INTEGER NOT NULL,
                date TEXT NOT NULL,
                teacher_id TEXT,
                ttl INTEGER DEFAULT 5,
                session_otp TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (teacher_id) REFERENCES teachers(id)
            )
        ''')
        
        # Migration: add ttl column if it doesn't exist
        try:
            cursor.execute("ALTER TABLE attendance_sessions ADD COLUMN ttl INTEGER DEFAULT 5")
        except sqlite3.OperationalError:
            pass  # Column already exists

        
        # Migration: add teacher_id column if it doesn't exist
        try:
            cursor.execute("ALTER TABLE attendance_sessions ADD COLUMN teacher_id TEXT")
        except sqlite3.OperationalError:
            pass  # Column already exists
            
        # Migration: add latitude column if it doesn't exist
        try:
            cursor.execute("ALTER TABLE attendance_sessions ADD COLUMN latitude REAL")
        except sqlite3.OperationalError:
            pass
            
        # Migration: add longitude column if it doesn't exist
        try:
            cursor.execute("ALTER TABLE attendance_sessions ADD COLUMN longitude REAL")
        except sqlite3.OperationalError:
            pass
        
        # Create attendance table (linked to sessions)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT NOT NULL,
                session_id INTEGER,
                date TEXT NOT NULL,
                status TEXT DEFAULT 'Present',
                auth_method TEXT NOT NULL,
                confidence_score REAL,
                marked_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (student_id) REFERENCES students(id),
                FOREIGN KEY (session_id) REFERENCES attendance_sessions(id)
            )
        ''')
        
        # Migration: remove old UNIQUE(student_id, date) constraint
        # SQLite can't drop constraints, so we recreate the table if needed
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='attendance'")
        row = cursor.fetchone()
        if row and 'UNIQUE(student_id, date)' in (row['sql'] or ''):
            print("[DB] Migrating attendance table: removing old UNIQUE(student_id, date) constraint...")
            cursor.execute('ALTER TABLE attendance RENAME TO attendance_old')
            cursor.execute('''
                CREATE TABLE attendance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id TEXT NOT NULL,
                    session_id INTEGER,
                    date TEXT NOT NULL,
                    status TEXT DEFAULT 'Present',
                    auth_method TEXT NOT NULL,
                    marked_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (student_id) REFERENCES students(id),
                    FOREIGN KEY (session_id) REFERENCES attendance_sessions(id)
                )
            ''')
            cursor.execute('''
                INSERT INTO attendance (id, student_id, date, status, auth_method, marked_at)
                SELECT id, student_id, date, status, auth_method, marked_at
                FROM attendance_old
            ''')
            cursor.execute('DROP TABLE attendance_old')
            print("[DB] Migration complete.")
        else:
            # Migration: add missing columns to attendance table
            try:
                cursor.execute("ALTER TABLE attendance ADD COLUMN session_id INTEGER")
            except sqlite3.OperationalError:
                pass  # Column already exists
            try:
                cursor.execute("ALTER TABLE attendance ADD COLUMN confidence_score REAL")
            except sqlite3.OperationalError:
                pass  # Column already exists
        
        # Migration: add password_hash columns
        try:
            cursor.execute("ALTER TABLE teachers ADD COLUMN password_hash TEXT")
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute("ALTER TABLE students ADD COLUMN password_hash TEXT")
        except sqlite3.OperationalError:
            pass
            
        # Migration: add session_otp column
        try:
            cursor.execute("ALTER TABLE attendance_sessions ADD COLUMN session_otp TEXT")
        except sqlite3.OperationalError:
            pass

        # Migration: add ble_uuid column
        try:
            cursor.execute("ALTER TABLE attendance_sessions ADD COLUMN ble_uuid TEXT")
        except sqlite3.OperationalError:
            pass

        # Create teacher_subjects table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS teacher_subjects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                teacher_id TEXT NOT NULL,
                subject_name TEXT NOT NULL,
                class_info TEXT,
                FOREIGN KEY (teacher_id) REFERENCES teachers(id)
            )
        ''')

        # Create face_images table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS face_images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT NOT NULL,
                face_data BLOB NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (student_id) REFERENCES students(id)
            )
        ''')

        # Create leave_requests table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS leave_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                reason TEXT NOT NULL,
                other_reason TEXT,
                status TEXT DEFAULT 'Pending', -- Pending, Approved, Rejected
                applied_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (student_id) REFERENCES students(id)
            )
        ''')

        # ── Seed Official Records ──────────────────────────────────────────────
        teachers_to_seed = [
            ("T1001", "Dr. R. Sridevi", "s@christuniversity.in", "Department of Computer Science"),
            ("T1002", "Dr. Ashwini Patil", "a@christuniversity.in", "Department of Computer Science"),
            ("T1003", "Dr. Neha Singhal", "n@christuniversity.in", "Department of Computer Science"),
            ("T1004", "Dr. Tejil John", "t@christuniversity.in", "Department of Computer Science"),
            ("T1005", "Dr. Binayak Dutta", "b@christuniversity.in", "Department of Computer Science"),
        ]
        
        for tid, tname, temail, tdept in teachers_to_seed:
            cursor.execute("SELECT id, password_hash FROM teachers WHERE id = ?", (tid,))
            existing = cursor.fetchone()
            if not existing:
                # Default password is "teacher@123" for quick setup
                phash = generate_password_hash("teacher@123")
                cursor.execute(
                    'INSERT INTO teachers (id, name, email, department, password_hash) VALUES (?, ?, ?, ?, ?)',
                    (tid, tname, temail, tdept, phash)
                )
            elif not existing['password_hash']:
                phash = generate_password_hash("teacher@123")
                cursor.execute('UPDATE teachers SET password_hash = ? WHERE id = ?', (phash, tid))

        # Seed subjects for teachers
        subjects_to_seed = [
            ("T1001", "Software Development Project", "MCA - Sem 3"),
            ("T1002", "Mobile Application Development", "MCA - Sem 3"),
            ("T1003", "Data Communications and Networks", "MCA - Sem 3"),
            ("T1004", "Cognitive Psychology", "MCA - Sem 3"),
            ("T1005", "Go Programming", "MCA - Sem 3"),
        ]

        for tid, sname, cinfo in subjects_to_seed:
            cursor.execute("SELECT 1 FROM teacher_subjects WHERE teacher_id = ? AND subject_name = ?", (tid, sname))
            if not cursor.fetchone():
                cursor.execute(
                    'INSERT INTO teacher_subjects (teacher_id, subject_name, class_info) VALUES (?, ?, ?)',
                    (tid, sname, cinfo)
                )

        # ── Seed Students ──────────────────────────────────────────────────────
        students_to_seed = [
            ("2547130", "Kripa Dhandhania", "kripa@example.com"),
            ("2547135", "Student Test", "test@example.com"),
            ("S2347101", "New Student", "new@example.com"),
        ]

        for sid, sname, semail in students_to_seed:
            cursor.execute("SELECT id, password_hash FROM students WHERE id = ?", (sid,))
            existing = cursor.fetchone()
            if not existing:
                phash = generate_password_hash("student@123")
                cursor.execute(
                    'INSERT INTO students (id, name, email, password_hash) VALUES (?, ?, ?, ?)',
                    (sid, sname, semail, phash)
                )
            elif not existing['password_hash']:
                phash = generate_password_hash("student@123")
                cursor.execute('UPDATE students SET password_hash = ? WHERE id = ?', (phash, sid))

        for tid, sname, cinfo in subjects_to_seed:
            cursor.execute("SELECT 1 FROM teacher_subjects WHERE teacher_id = ? AND subject_name = ?", (tid, sname))
            if not cursor.fetchone():
                cursor.execute(
                    'INSERT INTO teacher_subjects (teacher_id, subject_name, class_info) VALUES (?, ?, ?)',
                    (tid, sname, cinfo)
                )

        conn.commit()
        print("[DB] Database initialized successfully.")


# ============== STUDENT FUNCTIONS ==============

def add_student(student_id, name):
    """Add a new student to the database."""
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                'INSERT INTO students (id, name) VALUES (?, ?)',
                (student_id, name)
            )
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False


def get_student(student_id):
    """Get student by ID. Returns None if not found."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM students WHERE id = ?', (student_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None


def get_or_create_student(student_id, email=''):
    """Get student or create with default name if not exists."""
    student = get_student(student_id)
    if not student:
        add_student(student_id, f"Student {student_id}")
        if email:
            update_student_email(student_id, email)
        student = get_student(student_id)
    elif email and (not student.get('email') or student['email'] != email):
        update_student_email(student_id, email)
        student = get_student(student_id)
    return student


def get_student_by_id(student_id):
    """Get student by ID."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM students WHERE id = ?', (student_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def update_student_password(student_id, password_hash):
    """Update a student's password hash."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE students SET password_hash = ? WHERE id = ?',
            (password_hash, student_id)
        )
        conn.commit()
        return cursor.rowcount > 0


def get_student_email(student_id):
    """Get student's email from database."""
    student = get_student(student_id)
    if student:
        return student.get('email', '')
    return ''


def update_student_email(student_id, email):
    """Update a student's email address."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE students SET email = ? WHERE id = ?',
            (email, student_id)
        )
        conn.commit()
        return cursor.rowcount > 0


# ============== TEACHER FUNCTIONS ==============

def add_teacher(teacher_id, name, email='', department=''):
    """Add a new teacher to the database."""
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                'INSERT INTO teachers (id, name, email, department) VALUES (?, ?, ?, ?)',
                (teacher_id, name, email, department)
            )
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False


def get_teacher(teacher_id):
    """Get teacher by ID. Returns None if not found."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM teachers WHERE id = ?', (teacher_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None


def get_or_create_teacher(teacher_id, email='', name='', department=''):
    """Get teacher or create if not exists."""
    teacher = get_teacher(teacher_id)
    if not teacher:
        if not name:
            name = f"Teacher {teacher_id}"
        add_teacher(teacher_id, name, email, department)
        teacher = get_teacher(teacher_id)
    else:
        # Update existing info if provided
        needs_update = False
        if email and teacher.get('email') != email:
            needs_update = True
        if name and teacher.get('name') != name:
            needs_update = True
        if department and teacher.get('department') != department:
            needs_update = True
            
        if needs_update:
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'UPDATE teachers SET name = COALESCE(NULLIF(?, ""), name), email = COALESCE(NULLIF(?, ""), email), department = COALESCE(NULLIF(?, ""), department) WHERE id = ?',
                    (name, email, department, teacher_id)
                )
                conn.commit()
            teacher = get_teacher(teacher_id)
    return teacher


def get_teacher_by_id(teacher_id):
    """Get teacher by ID."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM teachers WHERE id = ?', (teacher_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def update_teacher_password(teacher_id, password_hash):
    """Update a teacher's password hash."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE teachers SET password_hash = ? WHERE id = ?',
            (password_hash, teacher_id)
        )
        conn.commit()
        return cursor.rowcount > 0


def get_teacher_subjects(teacher_id):
    """Get subjects assigned to a teacher."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT subject_name AS name, class_info FROM teacher_subjects WHERE teacher_id = ?',
            (teacher_id,)
        )
        return [dict(row) for row in cursor.fetchall()]


def add_teacher_subject(teacher_id, subject_name, class_info=''):
    """Add a mapping between a teacher and a subject."""
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                'INSERT OR IGNORE INTO teacher_subjects (teacher_id, subject_name, class_info) VALUES (?, ?, ?)',
                (teacher_id, subject_name, class_info)
            )
            conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"[DB] Error adding teacher subject: {e}")
            return False


# ============== SESSION FUNCTIONS ==============

def create_session(subject, hour, teacher_id, ttl_minutes=5, lat=None, lon=None):
    """Start a new attendance session with optional geolocation, BLE UUID, and custom TTL."""
    import uuid
    import random
    import string
    from datetime import date
    
    ble_uuid = str(uuid.uuid4())
    session_otp = ''.join(random.choices(string.digits, k=6))
    
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO attendance_sessions (subject, hour, date, teacher_id, ttl, latitude, longitude, ble_uuid, session_otp) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (subject, hour, date.today().isoformat(), teacher_id, ttl_minutes, lat, lon, ble_uuid, session_otp)
        )
        conn.commit()
        session_id = cursor.lastrowid
        print(f"[DB] Session created: {subject} - Hour {hour} by {teacher_id} (ID: {session_id}, OTP: {session_otp}, TTL: {ttl_minutes}m)")
        return session_id



def close_session(session_id):
    """Close an attendance session (teacher disables attendance marking)."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE attendance_sessions SET is_active = 0 WHERE id = ?',
            (session_id,)
        )
        conn.commit()
        print(f"[DB] Session {session_id} closed.")
        return cursor.rowcount > 0


def extend_session(session_id, additional_minutes=2):
    """
    Extend an active session by shifting its created_at timestamp forward.
    Using datetime('now') + X minutes relative to current time is easier for logic.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        # Shift created_at forward so it stays active longer
        # We'll set it to (current_now - (5 - additional_minutes)) effectively
        # But simpler: just add minutes to the existing created_at
        cursor.execute(
            '''UPDATE attendance_sessions 
               SET created_at = datetime(created_at, ?) 
               WHERE id = ? AND is_active = 1''',
            (f'+{additional_minutes} minutes', session_id)
        )
        conn.commit()
        print(f"[DB] Session {session_id} extended by {additional_minutes} min.")
        return cursor.rowcount > 0


def auto_expire_old_sessions():
    """Close sessions that have exceeded their individual TTL."""
    with get_connection() as conn:
        cursor = conn.cursor()
        # created_at is UTC; 'now' is UTC
        # We expire sessions where current time > created_at + ttl minutes
        cursor.execute(
            '''UPDATE attendance_sessions
               SET is_active = 0
               WHERE is_active = 1
                 AND datetime('now') >= datetime(created_at, '+' || ttl || ' minutes')'''
        )
        expired = cursor.rowcount
        conn.commit()
        if expired:
            print(f"[DB] Auto-expired {expired} session(s) based on individual TTL.")
        return expired


def get_active_sessions(subjects=None):
    """Get currently active attendance sessions, optionally filtered by subjects."""
    auto_expire_old_sessions()

    with get_connection() as conn:
        cursor = conn.cursor()
        query = 'SELECT * FROM attendance_sessions WHERE is_active = 1'
        params = []
        
        if subjects:
            placeholders = ', '.join(['?'] * len(subjects))
            query += f" AND subject IN ({placeholders})"
            params.extend(subjects)
            
        query += ' ORDER BY created_at DESC'
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]


def get_session(session_id):
    """Get a single session by ID."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM attendance_sessions WHERE id = ?', (session_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None


# ============== ATTENDANCE FUNCTIONS ==============

def check_attendance_for_session(student_id, session_id):
    """Check if student already marked attendance or has an approved leave for the session's date. Returns status string or None."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # 1. Check direct attendance record for this specific session
        cursor.execute(
            'SELECT status FROM attendance WHERE student_id = ? AND session_id = ?',
            (student_id, session_id)
        )
        result = cursor.fetchone()
        if result:
            return result[0]
            
        # 2. Fallback: Check for approved leave on the session date
        cursor.execute('SELECT date, is_active FROM attendance_sessions WHERE id = ?', (session_id,))
        sess = cursor.fetchone()
        if sess:
            # If session is still active, don't show "Excused" yet - let the student mark attendance if they are present
            if sess['is_active']:
                return None
                
            sess_date = sess['date']
            cursor.execute('''
                SELECT 1 FROM leave_requests 
                WHERE student_id = ? AND status = 'Approved' 
                AND ? BETWEEN start_date AND end_date
            ''', (student_id, sess_date))
            if cursor.fetchone():
                return 'Excused'
                
        return None


def mark_attendance(student_id, session_id, auth_method, confidence_score=None, status='Present'):
    """
    Mark attendance for a student in a specific session.
    """
    today = date.today().isoformat()
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT 1 FROM attendance WHERE student_id = ? AND session_id = ?',
            (student_id, session_id)
        )
        if cursor.fetchone():
            return False

        cursor.execute(
            '''INSERT INTO attendance (student_id, session_id, date, status, auth_method, confidence_score, marked_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)''',
            (student_id, session_id, today, status, auth_method, confidence_score, now_str)
        )
        conn.commit()
        return True

def get_pending_verifications(teacher_id):
    """Fetch all 'Pending Verification' records for sessions belonging to this teacher."""
    with get_connection() as conn:
        cursor = conn.cursor()
        query = """
            SELECT a.id as attendance_id, a.student_id, s.name as student_name, 
                   sess.subject, sess.hour, a.marked_at, a.session_id
            FROM attendance a
            LEFT JOIN students s ON a.student_id = s.id
            JOIN attendance_sessions sess ON a.session_id = sess.id
            WHERE sess.teacher_id = ? AND a.status = 'Pending Verification'
            ORDER BY a.marked_at DESC
        """
        cursor.execute(query, (teacher_id,))
        return [dict(row) for row in cursor.fetchall()]

def approve_attendance(attendance_id):
    """Update attendance status to Present and method to Manual."""
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE attendance SET status = 'Present', auth_method = 'Manual' WHERE id = ?",
                (attendance_id,)
            )
            conn.commit()
            return True
        except Exception as e:
            print(f"[DB ERR] approve_attendance: {e}")
            return False

def reject_attendance(attendance_id):
    """Remove a pending attendance record."""
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM attendance WHERE id = ?", (attendance_id,))
            conn.commit()
            return True
        except Exception as e:
            print(f"[DB ERR] reject_attendance: {e}")
            return False


def get_attendance_records(student_id=None, subjects=None):
    """
    Get attendance records, optionally filtered by student and/or subjects.
    
    Args:
        student_id: Filter by student ID
        subjects: List of subject names to filter by
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        query = '''SELECT a.*, s.subject, s.hour 
                   FROM attendance a 
                   LEFT JOIN attendance_sessions s ON a.session_id = s.id
                   WHERE 1=1'''
        params = []
        
        if student_id:
            query += " AND a.student_id = ?"
            params.append(student_id)
        
        if subjects:
            placeholders = ', '.join(['?'] * len(subjects))
            query += f" AND s.subject IN ({placeholders})"
            params.extend(subjects)
            
        query += " ORDER BY a.date DESC"
        
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]


# ============== FACE IMAGE FUNCTIONS ==============

def save_face_to_db(student_id, face_bytes):
    """Save face image bytes to database."""
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                '''INSERT OR REPLACE INTO face_images (student_id, face_data, created_at) 
                   VALUES (?, ?, CURRENT_TIMESTAMP)''',
                (student_id, face_bytes)
            )
            conn.commit()
            print(f"[DB] Face image saved for student: {student_id}")
            return True
        except Exception as e:
            print(f"[DB] Error saving face: {e}")
            return False


def get_face_from_db(student_id):
    """Get face image bytes from database."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT face_data FROM face_images WHERE student_id = ?',
            (student_id,)
        )
        row = cursor.fetchone()
        if row:
            return row['face_data']
        return None


def check_face_exists_in_db(student_id):
    """Check if a face image exists for the student in database."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT 1 FROM face_images WHERE student_id = ?',
            (student_id,)
        )
        return cursor.fetchone() is not None


def get_all_faces_from_db():
    """Get all face images from database."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT student_id, face_data FROM face_images')
        return [(row['student_id'], row['face_data']) for row in cursor.fetchall()]


# ============== ANALYTICS FUNCTIONS ==============

def get_analytics_stats(subjects=None):
    """Return high-level stats for the analytics and teacher dashboards."""
    today = date.today().isoformat()
    with get_connection() as conn:
        cursor = conn.cursor()

        # Total students (Global vs Teacher Specific)
        if subjects:
             placeholders = ', '.join(['?'] * len(subjects))
             # Define teacher's students as those who have ever attended their subjects
             cursor.execute(f'''
                 SELECT COUNT(DISTINCT student_id) AS c 
                 FROM attendance 
                 WHERE session_id IN (SELECT id FROM attendance_sessions WHERE subject IN ({placeholders}))
             ''', subjects)
             total_students = cursor.fetchone()['c']
        else:
             cursor.execute('SELECT COUNT(*) AS c FROM students')
             total_students = cursor.fetchone()['c']

        subj_filter = ""
        params = []
        if subjects:
            placeholders = ', '.join(['?'] * len(subjects))
            subj_filter = f" AND session_id IN (SELECT id FROM attendance_sessions WHERE subject IN ({placeholders}))"
            params.extend(subjects)

        # Present today
        cursor.execute(
            f"SELECT COUNT(DISTINCT student_id) AS c FROM attendance WHERE date = ?{subj_filter}",
            [today] + params
        )
        present_today = cursor.fetchone()['c']

        # Total sessions today
        sess_filter = ""
        if subjects:
            sess_filter = f" AND subject IN ({placeholders})"
        cursor.execute(
            f"SELECT COUNT(*) AS c FROM attendance_sessions WHERE date = ?{sess_filter}",
            [today] + (params if subjects else [])
        )
        sessions_today = cursor.fetchone()['c']

        # Face vs OTP counts
        cursor.execute(
            f"SELECT auth_method, COUNT(*) AS c FROM attendance WHERE 1=1{subj_filter} GROUP BY auth_method",
            params
        )
        method_rows = cursor.fetchall()
        face_count = 0
        otp_count  = 0
        manual_count = 0
        for row in method_rows:
            method = row['auth_method']
            if method == 'Face':
                face_count = row['c']
            elif method == 'OTP':
                otp_count = row['c']
            elif method == 'Manual':
                manual_count = row['c']

        # Average confidence (face only)
        cursor.execute(
            f"SELECT AVG(confidence_score) AS avg FROM attendance WHERE auth_method='Face' AND confidence_score IS NOT NULL{subj_filter}",
            params
        )
        avg_conf = cursor.fetchone()['avg']
        avg_confidence = round(avg_conf, 1) if avg_conf else 0

        # Total attendance records
        cursor.execute(f'SELECT COUNT(*) AS c FROM attendance WHERE 1=1{subj_filter}', params)
        total_records = cursor.fetchone()['c']

        absent_today = max(0, total_students - present_today)
        pct = round((present_today / total_students * 100), 1) if total_students else 0

        return {
            'total_students':  total_students,
            'present_today':   present_today,
            'absent_today':    absent_today,
            'attendance_pct':  pct,
            'sessions_today':  sessions_today,
            'face_count':      face_count,
            'otp_count':       otp_count,
            'manual_count':    manual_count,
            'avg_confidence':  avg_confidence,
            'total_records':   total_records,
        }

def get_active_session_stats(teacher_id):
    """Get stats for the currently active session of a teacher."""
    with get_connection() as conn:
        cursor = conn.cursor()
        # Find latest active session for this teacher
        cursor.execute('''
            SELECT * FROM attendance_sessions 
            WHERE teacher_id = ? AND is_active = 1 
            ORDER BY created_at DESC LIMIT 1
        ''', (teacher_id,))
        session = cursor.fetchone()
        
        if not session:
            return None
            
        session_id = session['id']
        subject = session['subject']
        hour = session['hour']
        
        # Total students for this subject (proxy: those who ever attended this subject)
        cursor.execute('''
            SELECT COUNT(DISTINCT student_id) AS c 
            FROM attendance 
            WHERE session_id IN (SELECT id FROM attendance_sessions WHERE subject = ?)
        ''', (subject,))
        total_students = cursor.fetchone()['c'] or 1
        
        # Present in THIS session
        cursor.execute('''
            SELECT auth_method, COUNT(*) AS c 
            FROM attendance 
            WHERE session_id = ? 
            GROUP BY auth_method
        ''', (session_id,))
        rows = cursor.fetchall()
        
        face_count = 0
        otp_count = 0
        manual_count = 0
        for r in rows:
            if r['auth_method'] == 'Face': face_count = r['c']
            elif r['auth_method'] == 'OTP': otp_count = r['c']
            elif r['auth_method'] == 'Manual': manual_count = r['c']
            
        present_count = face_count + otp_count + manual_count
        
        return {
            'session_id': session_id,
            'subject': subject,
            'hour': hour,
            'total_students': total_students,
            'present_count': present_count,
            'face_count': face_count,
            'otp_count': otp_count,
            'manual_count': manual_count,
            'percentage': round((present_count / total_students * 100), 1)
        }


def get_daily_trend(days=7, subjects=None):
    """Return attendance counts for the last N days."""
    from datetime import timedelta
    result = []
    today = date.today()
    with get_connection() as conn:
        cursor = conn.cursor()
        
        subj_filter = ""
        params = []
        if subjects:
            placeholders = ', '.join(['?'] * len(subjects))
            subj_filter = f" AND session_id IN (SELECT id FROM attendance_sessions WHERE subject IN ({placeholders}))"
            params.extend(subjects)

        for i in range(days - 1, -1, -1):
            d = (today - timedelta(days=i)).isoformat()
            cursor.execute(
                f"SELECT COUNT(DISTINCT student_id) AS c FROM attendance WHERE date = ?{subj_filter}",
                [d] + params
            )
            count = cursor.fetchone()['c']
            result.append({'date': d, 'count': count})
    return result


def get_defaulters(threshold=75, subjects=None):
    """Return students whose attendance % is below the threshold."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Total sessions per subject
        sess_filter = ""
        params = []
        if subjects:
            placeholders = ', '.join(['?'] * len(subjects))
            sess_filter = f" WHERE subject IN ({placeholders})"
            params.extend(subjects)
            
        cursor.execute(f'SELECT COUNT(*) AS c FROM attendance_sessions{sess_filter}', params)
        total_sessions = cursor.fetchone()['c']
        
        if total_sessions == 0:
            return []

        cursor.execute('SELECT id, name, email FROM students')
        students_list = [dict(r) for r in cursor.fetchall()]

        subj_filter = ""
        if subjects:
            subj_filter = f" AND session_id IN (SELECT id FROM attendance_sessions WHERE subject IN ({placeholders}))"

        defaulters = []
        for s in students_list:
            cursor.execute(
                f"SELECT COUNT(*) AS c FROM attendance WHERE student_id = ?{subj_filter}",
                [s['id']] + params
            )
            attended = cursor.fetchone()['c']
            pct = round((attended / total_sessions * 100), 1)
            if pct < threshold:
                defaulters.append({
                    'student_id': s['id'],
                    'name':       s['name'],
                    'email':      s['email'],
                    'attended':   attended,
                    'total':      total_sessions,
                    'percentage': pct
                })
        return defaulters


def get_all_students():
    """Return all students."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM students ORDER BY id')
        return [dict(r) for r in cursor.fetchall()]


def get_student_attendance_summary(subjects=None):
    """Return per-student attendance count and percentage."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        sess_filter = ""
        params = []
        if subjects:
            placeholders = ', '.join(['?'] * len(subjects))
            sess_filter = f" WHERE subject IN ({placeholders})"
            params.extend(subjects)
            
        cursor.execute(f'SELECT COUNT(*) AS c FROM attendance_sessions{sess_filter}', params)
        total_sessions = cursor.fetchone()['c']

        subj_filter = ""
        if subjects:
            subj_filter = f" AND session_id IN (SELECT id FROM attendance_sessions WHERE subject IN ({placeholders}))"

        query = f'''
            SELECT s.id AS student_id, s.name,
                   (SELECT COUNT(*) FROM attendance WHERE student_id = s.id{subj_filter}) AS attended
            FROM students s
            ORDER BY attended DESC
        '''
        cursor.execute(query, params)
        rows = cursor.fetchall()
        result = []
        for r in rows:
            attended = r['attended']
            pct = round((attended / total_sessions * 100), 1) if total_sessions else 0
            if attended > 0 or not subjects: # Only show students with some attendance if filtered
                result.append({
                    'student_id': r['student_id'],
                    'name':       r['name'],
                    'attended':   attended,
                    'total':      total_sessions,
                    'percentage': pct
                })
        return result


def get_verification_method_stats(subjects=None):
    """Return Face vs OTP counts as dict."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        subj_filter = ""
        params = []
        if subjects:
            placeholders = ', '.join(['?'] * len(subjects))
            subj_filter = f" WHERE session_id IN (SELECT id FROM attendance_sessions WHERE subject IN ({placeholders}))"
            params.extend(subjects)
            
        cursor.execute(
            f"SELECT auth_method, COUNT(*) AS c FROM attendance{subj_filter} GROUP BY auth_method",
            params
        )
        rows = cursor.fetchall()
        return {r['auth_method']: r['c'] for r in rows}


def get_student_subject_summary(student_id):
    """
    Return per-subject attendance summary for a single student.

    Returns a dict with:
      - subjects: list of {subject, sessions_total, attended, absent, percentage}
      - overall:  {sessions_total, attended, absent, percentage}
    """
    with get_connection() as conn:
        cursor = conn.cursor()

        # All sessions created, grouped by subject
        cursor.execute(
            "SELECT subject, COUNT(*) AS total FROM attendance_sessions GROUP BY subject"
        )
        session_categories = [dict(r) for r in cursor.fetchall()]

        # Sessions this student attended, grouped by subject
        cursor.execute(
            '''SELECT s.subject, COUNT(a.id) AS attended
               FROM attendance a
               JOIN attendance_sessions s ON a.session_id = s.id
               WHERE a.student_id = ?
               GROUP BY s.subject''',
            (student_id,)
        )
        attended_rows = [dict(r) for r in cursor.fetchall()]
        attended_map = {r['subject']: r['attended'] for r in attended_rows}

        subjects_summary = []
        total_sessions = 0
        total_attended = 0

        for cat in session_categories:
            sub_name = cat['subject']
            total    = cat['total']
            attended = attended_map.get(sub_name, 0)
            
            absent = total - attended
            pct = round((attended / total * 100), 2) if total > 0 else 0.0
            
            subjects_summary.append({
                'subject':        sub_name,
                'sessions_total': float(total),
                'attended':       float(attended),
                'absent':         float(absent),
                'percentage':     pct
            })
            
            total_sessions += total
            total_attended += attended

        overall_pct = round((total_attended / total_sessions * 100), 2) if total_sessions > 0 else 0.0

        return {
            'subjects': sorted(subjects_summary, key=lambda x: x['subject']),
            'overall': {
                'sessions_total': float(total_sessions),
                'attended':       float(total_attended),
                'absent':         float(total_sessions - total_attended),
                'percentage':     overall_pct
            }
        }


# Initialize database when module is imported
if __name__ == '__main__':
    init_db()
    print("Database setup complete!")
# ============== LEAVE REQUEST FUNCTIONS ==============

def create_leave_request(student_id, start_date, end_date, reason, other_reason=None):
    """Store a new leave request in the database."""
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                '''INSERT INTO leave_requests (student_id, start_date, end_date, reason, other_reason) 
                   VALUES (?, ?, ?, ?, ?)''',
                (student_id, start_date, end_date, reason, other_reason)
            )
            conn.commit()
            return True
        except Exception as e:
            print(f"[DB ERR] create_leave_request: {e}")
            return False

def get_leave_requests(student_id=None, status=None):
    """Fetch leave requests, optionally filtered by student and/or status."""
    with get_connection() as conn:
        cursor = conn.cursor()
        query = """
            SELECT lr.*, s.name as student_name 
            FROM leave_requests lr
            JOIN students s ON lr.student_id = s.id
            WHERE 1=1
        """
        params = []
        if student_id:
            query += " AND lr.student_id = ?"
            params.append(student_id)
        if status:
            query += " AND lr.status = ?"
            params.append(status)
            
        query += " ORDER BY lr.applied_at DESC"
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

def update_leave_status(request_id, status):
    """Update status of a leave request (Approved/Rejected)."""
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE leave_requests SET status = ? WHERE id = ?", (status, request_id))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"[DB ERR] update_leave_status: {e}")
            return False
