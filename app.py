from flask import Flask, render_template, redirect, url_for
import os

app = Flask(__name__,
    static_folder=os.path.join(os.path.dirname(__file__), "static"),
    static_url_path="/static"
)

@app.route("/")
def home():
    return redirect(url_for("teacher_dashboard"))

@app.route("/teacher")
def teacher_dashboard():
    teacher = {
        "name": "Dr. R. Sridevi",
        "department": "Department of Computer Science",
        "email": "sridevir@christuniversity.in"
    }

    subjects = [
        {"name": "Data Structures", "class_info": "CS101 - MCA A"},
        {"name": "Mobile App Development", "class_info": "CS301 - MCA B"},
        {"name": "DBMS", "class_info": "CS202 - MCA C"}
    ]

    return render_template(
        "teacher_dashboard.html",
        teacher=teacher,
        subjects=subjects
    )


# Mock Data
MOCK_STUDENTS = [
    {"id": "S101", "name": "Alice", "roll_no": "2347101"},
    {"id": "S102", "name": "Bob", "roll_no": "2347102"},
    {"id": "S103", "name": "Charlie", "roll_no": "2347103"},
    {"id": "S104", "name": "David", "roll_no": "2347104"},
    {"id": "S105", "name": "Eve", "roll_no": "2347105"}
]

# Mock Attendance Data: Date -> Slot -> StudentID -> Status
MOCK_ATTENDANCE = {
    "2024-10-24": {
        "07:30-09:00": {"S101": "Present", "S102": "Present", "S103": "Absent", "S104": "Present", "S105": "Present"},
        "09:45-10:45": {"S101": "Present", "S102": "Absent", "S103": "Absent", "S104": "Present", "S105": "Absent"},
        "10:45-11:45": {"S101": "Present", "S102": "Absent", "S103": "Absent", "S104": "Present", "S105": "Absent"},
        "11:45-12:45": {"S101": "Present", "S102": "Absent", "S103": "Absent", "S104": "Present", "S105": "Absent"},
        "12:45-13:45": {"S101": "Present", "S102": "Absent", "S103": "Absent", "S104": "Present", "S105": "Absent"},
    }
}

TIME_SLOTS = [
    "07:30-09:00",
    "09:45-10:45",
    "10:45-11:45",
    "11:45-12:45",
    "12:45-13:45"
]

@app.route("/attendance-report")
def attendance_report():
    from flask import request
    
    selected_date = request.args.get("date", "2024-10-24")
    filter_type = request.args.get("filter", "all")

    # Get attendance for the selected date (default to empty dict if no data)
    daily_attendance = MOCK_ATTENDANCE.get(selected_date, {})
    
    # Prepare the report data
    report_data = [] # List of rows: {student: {...}, status: {slot: status}} or list of statuses
    
    # Defines which slots to show columns for
    visible_slots = []
    
    if filter_type == "all":
        visible_slots = TIME_SLOTS
    elif filter_type in TIME_SLOTS:
        visible_slots = [filter_type]
    elif filter_type == "skipped_rest":
        visible_slots = TIME_SLOTS # Show all slots to prove they skipped
    
    # Process each student
    final_students = []

    for student in MOCK_STUDENTS:
        student_id = student["id"]
        status_map = {}
        
        # Check specific logic for "Skipped Rest"
        # Condition: Present at 7:30-9:00 AND Absent for ALL subsequent slots
        if filter_type == "skipped_rest":
            # 1. Check 7:30-9:00 status
            first_slot_status = daily_attendance.get("07:30-09:00", {}).get(student_id, "Absent")
            if first_slot_status != "Present":
                continue # Skip student if they weren't even there in the morning
            
            # 2. Check all other slots
            later_slots = ["09:45-10:45", "10:45-11:45", "11:45-12:45", "12:45-13:45"]
            is_skipper = True
            for slot in later_slots:
                status = daily_attendance.get(slot, {}).get(student_id, "Absent")
                if status == "Present":
                    is_skipper = False
                    break
            
            if not is_skipper:
                continue # Student was present in at least one later class, so not a skipper

        # Should include this student in the report
        final_students.append(student)
        
        # Collect statuses for visible slots
        for slot in visible_slots:
            status_map[slot] = daily_attendance.get(slot, {}).get(student_id, "Absent")
        
        student["attendance"] = status_map

    return render_template(
        "attendance_report.html",
        students=final_students,
        visible_slots=visible_slots,
        selected_date=selected_date,
        selected_filter=filter_type,
        time_slots=TIME_SLOTS
    )

@app.route("/download-report")
def download_report():
    import csv
    import io
    from flask import request, Response
    
    selected_date = request.args.get("date", "2024-10-24")
    filter_type = request.args.get("filter", "all")

    # Get attendance (Reuse logic - ideally refactor this into a helper, but duplicating for now to avoid large refactor risk)
    daily_attendance = MOCK_ATTENDANCE.get(selected_date, {})
    visible_slots = []
    if filter_type == "all":
        visible_slots = TIME_SLOTS
    elif filter_type in TIME_SLOTS:
        visible_slots = [filter_type]
    elif filter_type == "skipped_rest":
        visible_slots = TIME_SLOTS
    
    # Generate CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    header = ["Student ID", "Name"] + visible_slots
    writer.writerow(header)
    
    # Rows
    for student in MOCK_STUDENTS:
        student_id = student["id"]
        
        # Filter Logic (Duplicate of view logic)
        if filter_type == "skipped_rest":
            first_slot_status = daily_attendance.get("07:30-09:00", {}).get(student_id, "Absent")
            if first_slot_status != "Present":
                continue 
            later_slots = ["09:45-10:45", "10:45-11:45", "11:45-12:45", "12:45-13:45"]
            is_skipper = True
            for slot in later_slots:
                if daily_attendance.get(slot, {}).get(student_id, "Absent") == "Present":
                    is_skipper = False
                    break
            if not is_skipper:
                continue

        row = [student["id"], student["name"]]
        for slot in visible_slots:
            row.append(daily_attendance.get(slot, {}).get(student_id, "Absent"))
        writer.writerow(row)
        
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": f"attachment; filename=attendance_report_{selected_date}.csv"}
    )

if __name__ == "__main__":
    app.run(debug=True)
