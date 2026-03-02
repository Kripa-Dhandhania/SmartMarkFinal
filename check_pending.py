import sqlite3
import os

DB_PATH = 'attendance.db'

def check_all_pending():
    if not os.path.exists(DB_PATH):
        print("DB not found")
        return
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print("--- ALL PENDING RECORDS IN DB ---")
    cursor.execute("SELECT * FROM attendance WHERE status = 'Pending Verification'")
    rows = cursor.fetchall()
    if not rows:
        print("No pending records found at all.")
    else:
        for r in rows:
            print(dict(r))
            
    print("\n--- RECENT SESSIONS ---")
    cursor.execute("SELECT id, teacher_id, is_active FROM attendance_sessions ORDER BY id DESC LIMIT 5")
    for r in cursor.fetchall():
        print(dict(r))
        
    conn.close()

if __name__ == "__main__":
    check_all_pending()
