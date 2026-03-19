from database import create_session, check_attendance_for_session, get_active_sessions, get_connection
import os
from datetime import date

# Set working directory to the module_3 folder
os.chdir('c:/Users/User/Desktop/SPD/module_3/module_3')

def test_fix():
    # 1. Create a new active session
    # date.today().isoformat() is 2026-03-19
    success = create_session("Test Subject", 2, "T1001", 30)
    if not success:
        print("Failed to create session")
        return
        
    sessions = get_active_sessions()
    sess = [s for s in sessions if s['subject'] == 'Test Subject'][0]
    sess_id = sess['id']
    print(f"Created Test Session: {sess_id}")
    
    # 2. Check status for Student 2547130 (who has approved leave)
    student_id = '2547130'
    status = check_attendance_for_session(student_id, sess_id)
    print(f"Status for Student {student_id} (Active Session): {status}")
    
    # 3. Simulate closing the session
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE attendance_sessions SET is_active = 0 WHERE id = ?", (sess_id,))
        conn.commit()
    print(f"Closed Test Session: {sess_id}")
    
    # 4. Check status again
    status_closed = check_attendance_for_session(student_id, sess_id)
    print(f"Status for Student {student_id} (Closed Session): {status_closed}")

if __name__ == "__main__":
    test_fix()
