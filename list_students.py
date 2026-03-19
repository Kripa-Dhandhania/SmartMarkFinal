import sqlite3
import os

DB_PATH = 'c:/Users/User/Desktop/SPD/module_3/module_3/attendance.db'

def list_students():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM students")
    for r in cursor.fetchall():
        print(dict(r))
    conn.close()

if __name__ == "__main__":
    list_students()
