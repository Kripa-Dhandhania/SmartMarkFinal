"""
Unified Smart Attendance System
Integrates Module 3 (Analytics Dashboard) + SmartMark (Face Recognition + OTP)
"""

from flask import Flask, render_template, redirect, url_for, request, session, flash, Response, jsonify
import os
import csv
import io
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from datetime import date, datetime, timedelta
import math

# ── SmartMark imports ──────────────────────────────────────────────────────────
from face_manager import capture_face, save_face, train_recognizer, recognize_face, check_face_enrolled
from otp_manager import generate_otp, send_otp_email, send_otp_email_async, validate_otp
from notification_manager import send_low_attendance_alert, send_weekly_digest
from database import (
    init_db,
    get_or_create_student, get_student, get_student_email, update_student_email, add_student,
    check_face_exists_in_db,
    create_session, close_session, get_active_sessions, get_session,
    check_attendance_for_session, mark_attendance,
    get_attendance_records,
    get_analytics_stats, get_active_session_stats, get_daily_trend, get_defaulters,
    get_all_students, get_student_attendance_summary,
    get_all_students, get_student_attendance_summary,
    get_verification_method_stats,
    get_student_subject_summary,
    get_or_create_teacher, get_teacher, get_teacher_subjects, add_teacher, add_teacher_subject
)

# ── App setup ──────────────────────────────────────────────────────────────────
app = Flask(__name__,
    static_folder=os.path.join(os.path.dirname(__file__), "static"),
    static_url_path="/static"
)
app.secret_key = "smartmark_unified_secret_key_2024"

# Global recognizer state
recognizer = None
label_map = None

# Initialise DB on startup
init_db()

# ── Default Profile ──────────────────────────────────────────────────────────
DEFAULT_TEACHER = {
    "name": "Dr. R. Sridevi",
    "department": "Department of Computer Science",
    "email": "sridevir@christuniversity.in"
}

CLASSROOM_LAT = 12.933416887384725
CLASSROOM_LON = 77.60607102136017
CLASSROOM_RADIUS = 50.0  # Realistic 50m radius


SUBJECTS = [
    {"name": "Software Development Project",     "class_info": "MCA - Sem 3"},
    {"name": "Mobile Application Development",    "class_info": "MCA - Sem 3"},
    {"name": "Cognitive Psychology",             "class_info": "MCA - Sem 3"},
    {"name": "Go Programming",                  "class_info": "MCA - Sem 3"},
    {"name": "Data Communications and Networks", "class_info": "MCA - Sem 3"},
]

# ── Helper Functions ──────────────────────────────────────────────────────────
def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees) in meters.
    """
    R = 6371000  # Radius of earth in meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2)**2 + \
        math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c

# ══════════════════════════════════════════════════════════════════════════════
#  TEACHER ROUTES
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/")
def home():
    if "teacher_id" in session:
        return redirect(url_for("teacher_dashboard"))
    return redirect(url_for("teacher_login"))


@app.route("/teacher/login", methods=["GET", "POST"])
def teacher_login():
    if request.method == "POST":
        teacher_id = request.form.get("teacher_id", "").strip()
        email      = request.form.get("email", "").strip()
        dept       = request.form.get("department", "").strip()

        if not teacher_id or not email:
            flash("Teacher ID and Email are required.", "error")
            return redirect(url_for("teacher_login"))

        teacher = get_or_create_teacher(teacher_id, email=email, department=dept)
        session["teacher_id"] = teacher_id
        flash(f"Welcome, {teacher['name']}!", "success")
        return redirect(url_for("teacher_dashboard"))

    return render_template("teacher_login.html")


@app.route("/teacher/register", methods=["GET", "POST"])
def teacher_register():
    if request.method == "POST":
        teacher_id = request.form.get("teacher_id", "").strip()
        name       = request.form.get("name", "").strip()
        email      = request.form.get("email", "").strip()
        dept       = request.form.get("department", "").strip()
        subjects_str = request.form.get("subjects", "").strip()

        if not teacher_id or not name or not email:
            flash("Teacher ID, Name, and Email are required.", "error")
            return redirect(url_for("teacher_register"))

        if get_teacher(teacher_id):
            flash("Teacher ID already registered. Please login.", "warning")
            return redirect(url_for("teacher_login"))

        if add_teacher(teacher_id, name, email, dept):
            # Process subjects
            if subjects_str:
                subject_list = [s.strip() for s in subjects_str.split(",") if s.strip()]
                for sname in subject_list:
                    add_teacher_subject(teacher_id, sname)
            
            session["teacher_id"] = teacher_id
            flash(f"Welcome, {name}! Your registration was successful.", "success")
            return redirect(url_for("teacher_dashboard"))
        else:
            flash("Registration failed. Please try again.", "error")
            return redirect(url_for("teacher_register"))

    return render_template("teacher_login.html", register=True)


@app.route("/teacher/logout")
def teacher_logout():
    session.pop("teacher_id", None)
    flash("Logged out from teacher portal.", "info")
    return redirect(url_for("teacher_login"))


@app.route("/teacher")
def teacher_dashboard():
    if "teacher_id" not in session:
        return redirect(url_for("teacher_login"))
        
    teacher_id = session["teacher_id"]
    teacher = get_teacher(teacher_id) or DEFAULT_TEACHER
    
    # Get subjects assigned to this teacher
    teacher_subjects = get_teacher_subjects(teacher_id)
    subject_names = [s['name'] for s in teacher_subjects]
    
    stats = get_analytics_stats(subjects=subject_names)
    active_sessions = get_active_sessions(subjects=subject_names)
    # Determine current hour based on time
    now_hour = datetime.now().hour
    current_hour = 1
    if now_hour >= 9: current_hour = 2
    if now_hour >= 11: current_hour = 3
    if now_hour >= 12: current_hour = 4
    if now_hour >= 13: current_hour = 5
    
    return render_template(
        "teacher_dashboard.html",
        teacher=teacher,
        subjects=teacher_subjects,
        active_sessions=active_sessions,
        stats=stats,
        current_hour=current_hour,
        hour_labels=HOUR_LABELS
    )



@app.route("/teacher/create-session", methods=["POST"])
def teacher_create_session():
    if "teacher_id" not in session:
        return redirect(url_for("teacher_login"))
        
    subject = request.form.get("subject", "").strip()
    hour    = request.form.get("hour", "").strip()

    if not subject or not hour:
        flash("Subject and Hour are required.", "error")
        return redirect(url_for("teacher_dashboard"))

    try:
        hour_int = int(hour)
    except ValueError:
        flash("Hour must be a number.", "error")
        return redirect(url_for("teacher_dashboard"))

    teacher_id = session.get("teacher_id")
    duration = request.form.get("duration", "5")
    lat = request.form.get("latitude")
    lon = request.form.get("longitude")
    
    try:
        duration_int = int(duration)
    except ValueError:
        duration_int = 5
        
    create_session(subject, hour_int, teacher_id, ttl_minutes=duration_int, lat=lat, lon=lon)
    flash(f"Attendance enabled: {subject} – Hour {hour_int} for {duration_int} mins", "success")
    return redirect(url_for("teacher_dashboard"))



@app.route("/teacher/close-session/<int:session_id>", methods=["POST"])
def teacher_close_session(session_id):
    if "teacher_id" not in session:
        return redirect(url_for("teacher_login"))
    close_session(session_id)
    flash("Session closed.", "success")
    return redirect(url_for("teacher_dashboard"))


@app.route("/teacher/api/close-session/<int:session_id>", methods=["POST"])
def teacher_api_close_session(session_id):
    """AJAX endpoint – used by the JS countdown timer to auto-close a session."""
    from flask import jsonify
    close_session(session_id)
    return jsonify({"status": "closed", "session_id": session_id})


@app.route("/teacher/api/extend-session/<int:session_id>", methods=["POST"])
def teacher_api_extend_session(session_id):
    """AJAX endpoint to increase the session timer."""
    from flask import jsonify
    from database import extend_session
    minutes = request.json.get("minutes", 2)
    success = extend_session(session_id, minutes)
    return jsonify({"success": success, "session_id": session_id, "extended_by": minutes})


@app.route("/teacher/api/manual-mark-attendance", methods=["POST"])
def teacher_api_manual_mark_attendance():
    """AJAX endpoint for teachers to manually mark a student present."""
    if "teacher_id" not in session:
        return jsonify({"success": False, "error": "Unauthorized"}), 403
        
    data = request.json
    student_id = data.get("student_id")
    session_id = data.get("session_id")
    
    if not student_id or not session_id:
        return jsonify({"success": False, "error": "Missing student_id or session_id"}), 400
        
    from database import mark_attendance, get_session
    
    # Check if student exists
    student = get_student(student_id)
    if not student:
        return jsonify({"success": False, "error": "Student not found"}), 404
        
    # Mark attendance
    success = mark_attendance(student_id, session_id, auth_method="Manual")
    
    if success:
        return jsonify({"success": True})
    else:
        return jsonify({"success": False, "error": "Attendance already marked or failed"}), 400


@app.route("/api/students/search")
def api_students_search():
    """Search for students by name or ID (partial match)."""
    if "teacher_id" not in session:
        return jsonify({"success": False, "error": "Unauthorized"}), 403
        
    query = request.args.get("q", "").lower().strip()
    if not query:
        return jsonify([])
        
    all_students = get_all_students()
    results = [
        {"id": s["id"], "name": s["name"]}
        for s in all_students
        if query in s["id"].lower() or query in s["name"].lower()
    ]
    return jsonify(results[:10]) # Limit to 10 results




# ══════════════════════════════════════════════════════════════════════════════
#  ANALYTICS ROUTES
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/analytics")
def analytics():
    if "teacher_id" not in session:
        return redirect(url_for("teacher_login"))
        
    teacher_id = session.get("teacher_id")
    teacher = get_teacher(teacher_id) or DEFAULT_TEACHER
    
    # Get subjects assigned to this teacher
    teacher_subjects = get_teacher_subjects(teacher_id) if teacher_id else []
    subject_names = [s['name'] for s in teacher_subjects]
    
    stats        = get_analytics_stats(subjects=subject_names)
    daily_trend  = get_daily_trend(days=7, subjects=subject_names)
    defaulters   = get_defaulters(threshold=75, subjects=subject_names)
    method_stats = get_verification_method_stats(subjects=subject_names)
    students     = get_student_attendance_summary(subjects=subject_names)
    return render_template(
        "analytics.html",
        teacher=teacher,
        stats=stats,
        daily_trend=daily_trend,
        defaulters=defaulters,
        method_stats=method_stats,
        students=students
    )


@app.route("/api/analytics/live")
def api_analytics_live():
    if "teacher_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    teacher_id = session.get("teacher_id")
    teacher_subjects = get_teacher_subjects(teacher_id) if teacher_id else []
    subject_names = [s['name'] for s in teacher_subjects]
    
    # Check for active session
    active_session_stats = get_active_session_stats(teacher_id)
    
    stats = get_analytics_stats(subjects=subject_names)
    daily_trend = get_daily_trend(days=7, subjects=subject_names)
    method_stats = get_verification_method_stats(subjects=subject_names)
    defaulters = get_defaulters(threshold=75, subjects=subject_names)
    students = get_student_attendance_summary(subjects=subject_names)
    
    return jsonify({
        "stats": stats,
        "active_session": active_session_stats,
        "daily_trend": daily_trend,
        "method_stats": method_stats,
        "defaulters": defaulters,
        "students": students
    })


@app.route("/teacher/send-alerts", methods=["POST"])
def teacher_send_alerts():
    if "teacher_id" not in session:
        return redirect(url_for("teacher_login"))
        
    teacher_id = session.get("teacher_id")
    teacher_subjects = get_teacher_subjects(teacher_id) if teacher_id else []
    subject_names = [s['name'] for s in teacher_subjects] if teacher_subjects else None

    defaulters = get_defaulters(threshold=75, subjects=subject_names)
    sent_count = 0
    
    for d in defaulters:
        if d.get("email"):
            send_low_attendance_alert(d["name"], d["email"], d["percentage"])
            sent_count += 1
            
    flash(f"Low-attendance alerts sent to {sent_count} students.", "success")
    return redirect(url_for("analytics"))


@app.route("/teacher/send-weekly-digest", methods=["POST"])
def teacher_send_weekly_digest():
    if "teacher_id" not in session:
        return redirect(url_for("teacher_login"))
        
    teacher_id = session["teacher_id"]
    teacher = get_teacher(teacher_id) or DEFAULT_TEACHER
    
    teacher_subjects = get_teacher_subjects(teacher_id)
    subject_names = [s['name'] for s in teacher_subjects]

    stats = get_analytics_stats(subjects=subject_names)
    # Add a date range for the digest
    stats["date_range"] = f"{(date.today() - timedelta(days=7)).isoformat()} to {date.today().isoformat()}"
    stats["avg_attendance"] = stats["attendance_pct"] # Simplified for now
    stats["sessions_count"] = stats["sessions_today"] * 5 # Representative estimate
    
    defaulters = get_defaulters(threshold=75, subjects=subject_names)
    
    send_weekly_digest(teacher["name"], teacher["email"], stats, defaulters)
    
    flash("Weekly digest summary sent to your email.", "success")
    return redirect(url_for("analytics"))


# ══════════════════════════════════════════════════════════════════════════════
#  ATTENDANCE REPORT ROUTES  (real DB data)
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/attendance-report")
def attendance_report():
    selected_date = request.args.get("date", date.today().isoformat())
    student_filter = request.args.get("student_id", "")
    hour_filter = request.args.get("hour", "all")
    mismatch_filter = request.args.get("status", "")  # Use "status" for mismatch filters

    teacher_id = session.get("teacher_id")
    teacher_subjects = get_teacher_subjects(teacher_id) if teacher_id else []
    subject_names = [s['name'] for s in teacher_subjects]

    all_students = get_all_students()
    
    # Base records for the day and teacher's subjects
    records = get_attendance_records_for_report(selected_date, student_filter, subjects=subject_names)

    # Filter by hour slot
    if hour_filter != "all":
        try:
            h = int(hour_filter)
            records = [r for r in records if str(r.get("hour", "")) == str(h)]
        except ValueError:
            pass

    # Apply special mismatch filters
    if mismatch_filter:
        # Get all records for this date to perform cross-hour analysis
        day_records = get_attendance_records_for_report(selected_date, "", subjects=subject_names)
        
        student_hours = {}
        for r in day_records:
            sid = r.get("student_id")
            h = str(r.get("hour", ""))
            if sid not in student_hours:
                student_hours[sid] = set()
            if h:
                student_hours[sid].add(h)
        
        target_student_ids = []
        for s in all_students:
            sid = s["id"]
            hours = student_hours.get(sid, set())
            has_h1 = "1" in hours
            has_h2 = "2" in hours
            
            if mismatch_filter == "missed1_att2":
                if not has_h1 and has_h2:
                    target_student_ids.append(sid)
            elif mismatch_filter == "att1_missed2":
                if has_h1 and not has_h2:
                    target_student_ids.append(sid)
                    
        records = [r for r in records if r.get("student_id") in target_student_ids]


    teacher_id = session.get("teacher_id")
    teacher = get_teacher(teacher_id) if teacher_id else DEFAULT_TEACHER

    return render_template(
        "attendance_report.html",
        teacher=teacher,
        records=records,
        selected_date=selected_date,
        student_filter=student_filter,
        hour_filter=hour_filter,
        mismatch_filter=mismatch_filter,
        all_students=all_students
    )


@app.route("/download-report")
def download_report():
    selected_date  = request.args.get("date", date.today().isoformat())
    student_filter = request.args.get("student_id", "")

    teacher_id = session.get("teacher_id")
    teacher_subjects = get_teacher_subjects(teacher_id) if teacher_id else []
    subject_names = [s['name'] for s in teacher_subjects]
    
    records = get_attendance_records_for_report(selected_date, student_filter, subjects=subject_names)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Student ID", "Subject", "Hour", "Date", "Time", "Status", "Auth Method"])
    for r in records:
        writer.writerow([
            r.get("student_id"),
            r.get("subject", ""),
            r.get("hour", ""),
            r.get("date"),
            r.get("marked_at", "")[:19] if r.get("marked_at") else "",
            r.get("status"),
            r.get("auth_method")
        ])

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename=attendance_{selected_date}.csv"}
    )


def get_attendance_records_for_report(selected_date, student_filter="", subjects=None):
    """Helper: fetch attendance records filtered by date, student, and subjects."""
    all_records = get_attendance_records(
        student_id=student_filter if student_filter else None,
        subjects=subjects
    )
    return [r for r in all_records if r.get("date") == selected_date]



# ── Hour slot label map ────────────────────────────────────────────────────────
HOUR_LABELS = {
    "1": "7:30AM-9:00AM",
    "2": "9:45AM-10:45AM",
    "3": "10:45AM-11:45AM",
    "4": "11:45AM-12:45PM",
    "5": "12:45PM-1:45PM",
}


@app.route("/download-excel")
def download_excel():
    selected_date = request.args.get("date", date.today().isoformat())
    student_filter = request.args.get("student_id", "")
    hour_filter = request.args.get("hour", "all")
    mismatch_filter = request.args.get("status", "")

    teacher_id = session.get("teacher_id")
    teacher_subjects = get_teacher_subjects(teacher_id) if teacher_id else []
    subject_names = [s['name'] for s in teacher_subjects]
    
    all_students = get_all_students()
    records = get_attendance_records_for_report(selected_date, student_filter, subjects=subject_names)

    # Filter by hour slot
    if hour_filter != "all":
        try:
            h = int(hour_filter)
            records = [r for r in records if str(r.get("hour", "")) == str(h)]
        except ValueError:
            pass

    # Apply special mismatch filters
    if mismatch_filter:
        day_records = get_attendance_records_for_report(selected_date, "", subjects=subject_names)
        student_hours = {}
        for r in day_records:
            sid = r.get("student_id")
            h = str(r.get("hour", ""))
            if sid not in student_hours:
                student_hours[sid] = set()
            if h:
                student_hours[sid].add(h)
        
        target_student_ids = []
        for s in all_students:
            sid = s["id"]
            hours = student_hours.get(sid, set())
            has_h1 = "1" in hours
            has_h2 = "2" in hours
            
            if mismatch_filter == "missed1_att2":
                if not has_h1 and has_h2:
                    target_student_ids.append(sid)
            elif mismatch_filter == "att1_missed2":
                if has_h1 and not has_h2:
                    target_student_ids.append(sid)
                    
        records = [r for r in records if r.get("student_id") in target_student_ids]


    # ── Build workbook ─────────────────────────────────────────────────────────
    wb = openpyxl.Workbook()
    ws = wb.active

    hour_label = HOUR_LABELS.get(hour_filter, "All Hours") if hour_filter != "all" else "All Hours"
    ws.title   = "Attendance"

    # ── Title row ─────────────────────────────────────────────────────────────
    ws.merge_cells("A1:G1")
    title_cell = ws["A1"]
    title_cell.value     = f"Attendance Report — {selected_date} | {hour_label}"
    title_cell.font      = Font(bold=True, size=13, color="FFFFFF")
    title_cell.fill      = PatternFill("solid", fgColor="1E3A8A")
    title_cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 24

    # ── Header row ────────────────────────────────────────────────────────────
    headers = ["Student ID", "Subject", "Hour", "Time Slot", "Date", "Time", "Status", "Auth Method"]
    ws.merge_cells("A1:H1")           # re-merge to span 8 columns
    for col, h in enumerate(headers, start=1):
        cell            = ws.cell(row=2, column=col, value=h)
        cell.font       = Font(bold=True, color="FFFFFF")
        cell.fill       = PatternFill("solid", fgColor="2563EB")
        cell.alignment  = Alignment(horizontal="center")

    # ── Data rows ─────────────────────────────────────────────────────────────
    for row_idx, r in enumerate(records, start=3):
        hour_num  = str(r.get("hour", ""))
        slot_lbl  = HOUR_LABELS.get(hour_num, f"Hour {hour_num}")
        marked_at = r.get("marked_at", "") or ""
        date_val  = r.get("date", "")
        time_val  = marked_at[11:19] if len(marked_at) >= 19 else (marked_at[:16] if marked_at else "")

        row_data = [
            r.get("student_id", ""),
            r.get("subject", ""),
            f"Hour {hour_num}" if hour_num else "—",
            slot_lbl,
            date_val,
            time_val,
            r.get("status", ""),
            r.get("auth_method", ""),
        ]
        for col, val in enumerate(row_data, start=1):
            cell            = ws.cell(row=row_idx, column=col, value=val)
            cell.alignment  = Alignment(horizontal="left")
            if row_idx % 2 == 0:
                cell.fill = PatternFill("solid", fgColor="EFF6FF")  # light blue stripe

    # ── Column widths ─────────────────────────────────────────────────────────
    col_widths = [16, 22, 10, 24, 14, 12, 12, 14]
    for i, w in enumerate(col_widths, start=1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = w

    # ── Stream response ───────────────────────────────────────────────────────
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    safe_hour = hour_filter.replace("/", "-")
    filename  = f"attendance_{selected_date}_hour{safe_hour}.xlsx"

    return Response(
        buf.getvalue(),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )




# ══════════════════════════════════════════════════════════════════════════════
#  STUDENT ROUTES
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/student/login", methods=["GET", "POST"])
def student_login():
    if request.method == "POST":
        student_id = request.form.get("student_id", "").strip()
        email      = request.form.get("email", "").strip()

        if not student_id:
            flash("Student ID is required.", "error")
            return redirect(url_for("student_login"))
        if not email:
            flash("Email is required.", "error")
            return redirect(url_for("student_login"))

        get_or_create_student(student_id, email)
        session["student_id"] = student_id
        session["student_email"] = email  # Store email in session for OTP
        return redirect(url_for("student_dashboard"))

    return render_template("student_login.html")


@app.route("/student/register", methods=["GET", "POST"])
def student_register():
    if request.method == "POST":
        student_id = request.form.get("student_id", "").strip()
        name       = request.form.get("name", "").strip()
        email      = request.form.get("email", "").strip()

        if not student_id or not name or not email:
            flash("Student ID, Name, and Email are required.", "error")
            return redirect(url_for("student_register"))

        if get_student(student_id):
            flash("Student ID already registered. Please login.", "warning")
            return redirect(url_for("student_login"))

        if add_student(student_id, name):
            update_student_email(student_id, email)
            session["student_id"] = student_id
            session["student_email"] = email
            flash(f"Welcome, {name}! Registration successful.", "success")
            return redirect(url_for("student_dashboard"))
        else:
            flash("Registration failed. Please try again.", "error")
            return redirect(url_for("student_register"))

    return render_template("student_login.html", register=True)


@app.route("/student/dashboard")
def student_dashboard():
    if "student_id" not in session:
        return redirect(url_for("student_login"))

    student_id   = session["student_id"]
    face_enrolled = check_face_enrolled(student_id)

    active_sessions = get_active_sessions()
    sessions_with_status = []
    for s in active_sessions:
        already_marked = check_attendance_for_session(student_id, s["id"])
        sessions_with_status.append({
            "id":            s["id"],
            "subject":       s["subject"],
            "hour":          s["hour"],
            "date":          s["date"],
            "latitude":      s["latitude"],
            "longitude":     s["longitude"],
            "already_marked": already_marked
        })

    my_records = get_attendance_records(student_id=student_id)

    return render_template(
        "student_dashboard.html",
        student_id=student_id,
        face_enrolled=face_enrolled,
        sessions=sessions_with_status,
        my_records=my_records[:10],
        classroom_lat=CLASSROOM_LAT,
        classroom_lon=CLASSROOM_LON,
        classroom_radius=CLASSROOM_RADIUS
    )



@app.route("/student/enroll-face", methods=["POST"])
def enroll_face():
    global recognizer, label_map

    if "student_id" not in session:
        flash("Login required.", "error")
        return redirect(url_for("student_login"))

    student_id = session["student_id"]
    face = capture_face()

    if face is None:
        flash("Face capture cancelled or no face detected.", "error")
        return redirect(url_for("student_dashboard"))

    if save_face(student_id, face):
        recognizer, label_map = train_recognizer()
        flash("Face enrolled successfully! You can now mark attendance.", "success")
    else:
        flash("Failed to save face. Please try again.", "error")

    return redirect(url_for("student_dashboard"))


@app.route("/student/mark-attendance/<int:session_id>", methods=["POST"])
def mark_attendance_route(session_id):
    global recognizer, label_map

    if "student_id" not in session:
        return redirect(url_for("student_login"))

    student_id = session["student_id"]

    # Validate session is still active
    att_session = get_session(session_id)
    if not att_session or not att_session["is_active"]:
        flash("This attendance session is no longer active.", "error")
        return redirect(url_for("student_dashboard"))

    # Duplicate check
    if check_attendance_for_session(student_id, session_id):
        flash("Attendance already marked for this session!", "warning")
        return redirect(url_for("student_dashboard"))

    # Step 0: Location Check (Geofencing)
    lat_str = request.form.get("latitude")
    lon_str = request.form.get("longitude")

    if not lat_str or not lon_str:
        flash("Location access is required to mark attendance. Please enable location and try again.", "error")
        return redirect(url_for("student_dashboard"))

    try:
        student_lat = float(lat_str)
        student_lon = float(lon_str)
        
        # Identify target location: prefer session-specific coordinates
        target_lat = att_session.get("latitude") if att_session.get("latitude") is not None else CLASSROOM_LAT
        target_lon = att_session.get("longitude") if att_session.get("longitude") is not None else CLASSROOM_LON
        
        distance = haversine_distance(student_lat, student_lon, target_lat, target_lon)
        
        print(f"[LOCATION] Student {student_id} position: ({student_lat}, {student_lon})")
        print(f"[LOCATION] Distance from session origin ({target_lat}, {target_lon}): {distance:.2f}m")
        
        if distance > CLASSROOM_RADIUS:
            flash(f"You are outside the classroom range ({distance:.1f}m away). Please go inside to mark attendance.", "error")
            return redirect(url_for("student_dashboard"))
    except ValueError:
        flash("Invalid location data received.", "error")
        return redirect(url_for("student_dashboard"))

    # Step 1: Capture face
    face = capture_face()
    if face is None:
        flash("Face capture cancelled or no face detected.", "error")
        return redirect(url_for("student_dashboard"))

    # Step 2: Train recognizer if not ready
    if recognizer is None:
        recognizer, label_map = train_recognizer()

    # Step 3: Recognize
    if recognizer is not None and label_map:
        matched_id, confidence = recognize_face(recognizer, label_map, face)
    else:
        matched_id = None
        confidence = float("inf")

    # Step 4: Face match → mark instantly
    if matched_id and matched_id == student_id:
        mark_attendance(student_id, session_id, auth_method="Face",
                        confidence_score=round(confidence, 2))
        flash(f"Face recognised! Attendance marked for {att_session['subject']} – Hour {att_session['hour']}.", "success")
        return redirect(url_for("attendance_confirmed",
                                session_id=session_id, method="Face"))

    # Step 5: OTP Fallback (using teacher's email from session)
    student = get_student(student_id)
    student_name = student["name"] if student else student_id
    
    teacher_id = att_session.get("teacher_id")
    teacher = get_teacher(teacher_id) if teacher_id else None
    teacher_email = teacher["email"] if teacher else None

    if teacher_email:
        otp = generate_otp()
        session["otp"]            = otp
        session["otp_session_id"] = session_id
        
        send_otp_email_async(teacher_email, otp, student_name=student_name)
        flash(f"Face not recognised. An OTP has been sent to your teacher's email ({teacher_email}). Please ask them for the code.", "info")
        return redirect(url_for("otp_verify"))
    else:
        flash("Face not recognised. No teacher found for this session to send a verification code to.", "error")
        return redirect(url_for("student_dashboard"))


@app.route("/student/otp", methods=["GET", "POST"])
def otp_verify():
    if "student_id" not in session:
        return redirect(url_for("student_login"))

    if request.method == "POST":
        user_otp   = request.form.get("otp", "").strip()
        stored_otp = session.get("otp", "")
        session_id = session.get("otp_session_id")

        if not session_id:
            flash("Session expired. Please try again.", "error")
            return redirect(url_for("student_dashboard"))

        if validate_otp(user_otp, stored_otp):
            student_id  = session["student_id"]
            att_session = get_session(session_id)
            mark_attendance(student_id, session_id, auth_method="OTP",
                            confidence_score=None)
            session.pop("otp", None)
            session.pop("otp_session_id", None)
            flash(f"OTP verified! Attendance marked for {att_session['subject']} – Hour {att_session['hour']}.", "success")
            return redirect(url_for("attendance_confirmed",
                                    session_id=session_id, method="OTP"))
        else:
            flash("Invalid OTP. Please try again.", "error")
            return redirect(url_for("otp_verify"))

    return render_template("otp_verify.html")


@app.route("/student/confirmed")
def attendance_confirmed():
    if "student_id" not in session:
        return redirect(url_for("student_login"))

    student_id  = session["student_id"]
    method      = request.args.get("method", "Unknown")
    session_id  = request.args.get("session_id")

    att_session = None
    if session_id:
        att_session = get_session(int(session_id))

    return render_template("confirmed.html",
                           student_id=student_id,
                           auth_method=method,
                           att_session=att_session)


@app.route("/student/my-attendance")
def student_my_attendance():
    if "student_id" not in session:
        return redirect(url_for("student_login"))

    student_id = session["student_id"]
    summary    = get_student_subject_summary(student_id)
    all_records = get_attendance_records(student_id=student_id)

    return render_template(
        "student_my_attendance.html",
        student_id=student_id,
        subjects=summary['subjects'],
        overall=summary['overall'],
        all_records=all_records
    )


@app.route("/student/logout")
def student_logout():
    session.clear()
    return redirect(url_for("student_login"))


# ══════════════════════════════════════════════════════════════════════════════
#  RUN
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    app.run(debug=True)
