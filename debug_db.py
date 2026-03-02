import sqlite3
import os

DB_PATH = 'attendance.db'

def check_db():
    if not os.path.exists(DB_PATH):
        print(f"DATABASE NOT FOUND at {os.path.abspath(DB_PATH)}")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print("--- ALL ATTENDANCE ---")
    cursor.execute("SELECT id, student_id, session_id, status, date, marked_at FROM attendance ORDER BY id DESC LIMIT 10")
    for r in cursor.fetchall():
        print(dict(r))
        
    print("\n--- PENDING VERIFICATIONS ---")
    cursor.execute("SELECT * FROM attendance WHERE status = 'Pending Verification'")
    for r in cursor.fetchall():
        print(dict(r))
        
    print("\n--- SESSIONS ---")
    cursor.execute("SELECT id, subject, teacher_id, is_active FROM attendance_sessions ORDER BY id DESC LIMIT 5")
    for r in cursor.fetchall():
        print(dict(r))
        
    conn.close()

if __name__ == "__main__":
    check_db()
