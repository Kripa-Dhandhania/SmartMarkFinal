import sqlite3
import os

DB_PATH = 'attendance.db'

def check_query():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    teacher_id = 'T1001'
    print(f"Checking for teacher_id: {teacher_id}")
    
    query = """
        SELECT a.id as attendance_id, a.student_id, s.name as student_name, 
               sess.subject, sess.hour, a.marked_at, a.session_id, sess.teacher_id, a.status
        FROM attendance a
        LEFT JOIN students s ON a.student_id = s.id
        JOIN attendance_sessions sess ON a.session_id = sess.id
        WHERE sess.teacher_id = ? AND a.status = 'Pending Verification'
    """
    cursor.execute(query, (teacher_id,))
    rows = cursor.fetchall()
    print(f"Results: {[dict(r) for r in rows]}")
    
    # Check individual parts
    print("\nIndividual check:")
    cursor.execute("SELECT * FROM attendance WHERE status = 'Pending Verification'")
    att = [dict(r) for r in cursor.fetchall()]
    print(f"Pending attendance: {att}")
    
    for a in att:
        sid = a['session_id']
        cursor.execute("SELECT * FROM attendance_sessions WHERE id = ?", (sid,))
        sess = [dict(r) for r in cursor.fetchall()]
        print(f"Session {sid} info: {sess}")
        
    conn.close()

if __name__ == "__main__":
    check_query()
