from database import check_attendance_for_session, get_all_students, get_active_sessions
import os

# Set working directory to the module_3 folder so imports work and db path is correct if relative
os.chdir('c:/Users/User/Desktop/SPD/module_3/module_3')

def simulate():
    students = get_all_students()
    sessions = get_active_sessions()
    
    print(f"Active Sessions: {[s['id'] for s in sessions]}")
    
    for s in students:
        sid = s['id']
        name = s['name']
        print(f"\nStudent: {sid} ({name})")
        for sess in sessions:
            status = check_attendance_for_session(sid, sess['id'])
            print(f"  Session {sess['id']} ({sess['subject']} on {sess['date']}): {status}")

if __name__ == "__main__":
    simulate()
