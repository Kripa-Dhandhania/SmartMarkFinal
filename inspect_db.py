import sqlite3
import os

DB_PATH = 'c:/Users/User/Desktop/SPD/module_3/module_3/attendance.db'

def inspect_db():
    if not os.path.exists(DB_PATH):
        print(f"DATABASE NOT FOUND at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print("--- ALL LEAVE REQUESTS ---")
    cursor.execute("SELECT * FROM leave_requests")
    for r in cursor.fetchall():
        print(dict(r))
        
    print("\n--- ATTENDANCE TODAY (2026-03-19) ---")
    cursor.execute("SELECT * FROM attendance WHERE date = '2026-03-19'")
    for r in cursor.fetchall():
        print(dict(r))

    print("\n--- ALL ATTENDANCE (LAST 10) ---")
    cursor.execute("SELECT * FROM attendance ORDER BY id DESC LIMIT 10")
    for r in cursor.fetchall():
        print(dict(r))
        
    print("\n--- SESSIONS ---")
    cursor.execute("SELECT id, subject, date, is_active FROM attendance_sessions ORDER BY id DESC LIMIT 5")
    for r in cursor.fetchall():
        print(dict(r))

    conn.close()

if __name__ == "__main__":
    inspect_db()
