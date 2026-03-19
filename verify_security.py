import requests
import sqlite3
import os

# We'll use a local request simulation since we can't easily run the server and requests in parallel here
# Instead, I'll simulate the logic inside a script that mimics the app.py route behavior

from app import app
from database import get_connection, create_session, mark_attendance

def test_security():
    with app.test_request_context():
        # 1. Create a session for Teacher T1001
        create_session("Security Test", 1, "T1001", 10)
        
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM attendance_sessions WHERE subject = 'Security Test' LIMIT 1")
            sess_id = cursor.fetchone()['id']
            
            # 2. Mark attendance for a student (Pending Verification)
            mark_attendance("2547135", sess_id, "Face", confidence_score=50.0, status="Pending Verification")
            cursor.execute("SELECT id FROM attendance WHERE session_id = ? LIMIT 1", (sess_id,))
            att_id = cursor.fetchone()['id']
            
        # 3. Try to approve it as Teacher T1002 (should fail if we enforce session ownership)
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess['teacher_id'] = 'T1002'
                sess['user_role'] = 'teacher'
            
            # Post to approve-verification
            response = client.post(f"/teacher/approve-verification/{att_id}", follow_redirects=True)
            print(f"Status Code for T1002 approving T1001's session: {response.status_code}")
            
            if b"Unauthorized" in response.data:
                print("Security Check Passed: Unauthorized message found in response.")
            else:
                print("Security Check Failed: Unauthorized message NOT found.")

if __name__ == "__main__":
    test_security()
