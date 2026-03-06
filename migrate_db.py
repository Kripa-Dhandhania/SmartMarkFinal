import sqlite3
import os

def migrate_database():
    db_path = 'attendance.db'
    if not os.path.exists(db_path):
        print(f"Error: {db_path} not found in the current directory.")
        return

    print(f"Connecting to {db_path}...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check if confidence_score exists in attendance table
        cursor.execute("PRAGMA table_info(attendance)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'confidence_score' not in columns:
            print("Adding 'confidence_score' column to 'attendance' table...")
            cursor.execute("ALTER TABLE attendance ADD COLUMN confidence_score REAL")
            conn.commit()
            print("Successfully added 'confidence_score' column.")
        else:
            print("'confidence_score' column already exists.")

        # Optional: Add any other missing columns if needed for manual verification
        if 'auth_method' not in columns:
            # Should exist, but being safe
            print("Adding 'auth_method' column...")
            cursor.execute("ALTER TABLE attendance ADD COLUMN auth_method TEXT DEFAULT 'OTP'")
            conn.commit()

    except Exception as e:
        print(f"An error occurred during migration: {e}")
    finally:
        conn.close()
        print("Migration complete.")

if __name__ == "__main__":
    migrate_database()
