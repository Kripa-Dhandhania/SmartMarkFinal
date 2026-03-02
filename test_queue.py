import sqlite3
import os
from datetime import date, datetime

DB_PATH = 'attendance.db'

def test_flow():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 1. Create a dummy session for T1001
    today = date.today().isoformat()
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute("INSERT INTO attendance_sessions (subject, hour, date, teacher_id, is_active, created_at, ttl) VALUES (?, ?, ?, ?, ?, ?, ?)",
                   ('TEST SUBJECT', 1, today, 'T1001', 1, now_str, 5))
    session_id = cursor.lastrowid
    conn.commit()
    print(f"Created TEST SESSION {session_id} for T1001")
    
    # 2. Try to mark attendance as Pending Verification
    student_id = 'S_TEST'
    cursor.execute("INSERT INTO attendance (student_id, session_id, date, status, auth_method, marked_at) VALUES (?, ?, ?, ?, ?, ?)",
                   (student_id, session_id, today, 'Pending Verification', 'Manual', now_str))
    conn.commit()
    print(f"Marked attendance as Pending for {student_id}")
    
    # 3. Try to retrieve it
    query = """
        SELECT a.id as attendance_id, a.student_id, s.name as student_name, 
               sess.subject, sess.hour, a.marked_at, a.session_id
        FROM attendance a
        LEFT JOIN students s ON a.student_id = s.id
        JOIN attendance_sessions sess ON a.session_id = sess.id
        WHERE sess.teacher_id = ? AND a.status = 'Pending Verification'
    """
    cursor.execute(query, ('T1001',))
    results = [dict(r) for r in cursor.fetchall()]
    print(f"RETRIEVED for T1001: {results}")
    
    # 4. Cleanup
    cursor.execute("DELETE FROM attendance WHERE student_id = 'S_TEST'")
    cursor.execute("DELETE FROM attendance_sessions WHERE id = ?", (session_id,))
    conn.commit()
    conn.close()

if __name__ == "__main__":
    test_flow()
