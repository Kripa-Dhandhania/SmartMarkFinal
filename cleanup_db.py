import sqlite3
import os

DB_PATH = 'c:/Users/User/Desktop/SPD/module_3/module_3/attendance.db'

def cleanup():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM attendance_sessions WHERE subject = 'Security Test' OR subject = 'Test Subject'")
    print(f"Deleted {cursor.rowcount} test sessions.")
    
    # Also clear any test attendance records
    cursor.execute("DELETE FROM attendance WHERE session_id NOT IN (SELECT id FROM attendance_sessions)")
    print(f"Deleted {cursor.rowcount} orphaned attendance records.")
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    cleanup()
