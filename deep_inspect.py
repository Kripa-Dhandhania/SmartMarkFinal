import sqlite3
import os

DB_PATH = 'c:/Users/User/Desktop/SPD/module_3/module_3/attendance.db'

def deep_inspect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print("--- STATUS COUNTS IN ATTENDANCE ---")
    cursor.execute("SELECT status, COUNT(*) as count FROM attendance GROUP BY status")
    for r in cursor.fetchall():
        print(dict(r))
        
    print("\n--- STUDENTS WITH LEAVE ---")
    cursor.execute("""
        SELECT s.id, s.name, lr.start_date, lr.end_date, lr.status 
        FROM students s 
        JOIN leave_requests lr ON s.id = lr.student_id
    """)
    for r in cursor.fetchall():
        print(dict(r))

    print("\n--- ALL SESSIONS TODAY ---")
    cursor.execute("SELECT * FROM attendance_sessions WHERE date = '2026-03-19'")
    for r in cursor.fetchall():
        print(dict(r))

    conn.close()

if __name__ == "__main__":
    deep_inspect()
