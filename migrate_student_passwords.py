import sqlite3
import os
from werkzeug.security import generate_password_hash

DB_PATH = 'c:/Users/User/Desktop/module_3/module_3/attendance.db'

def migrate_student_passwords():
    if not os.path.exists(DB_PATH):
        print(f"Error: Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT id, name, password_hash FROM students")
        students = cursor.fetchall()
        
        updated_count = 0
        for student in students:
            # Only update if password_hash is empty or NULL
            if not student['password_hash']:
                student_id = student['id'].strip()
                if student_id:
                    default_password = f"{student_id}@123"
                    password_hash = generate_password_hash(default_password)
                    
                    cursor.execute(
                        "UPDATE students SET password_hash = ? WHERE id = ?",
                        (password_hash, student['id'])
                    )
                    updated_count += 1
                    print(f"Updated student {student_id} ({student['name']}) with default password.")

        conn.commit()
        print(f"Migration complete. {updated_count} students updated.")
        
    except Exception as e:
        print(f"An error occurred during migration: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_student_passwords()
