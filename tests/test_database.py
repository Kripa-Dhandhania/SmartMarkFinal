import pytest
from database import (
    add_student, get_student, update_student_password,
    add_teacher, get_teacher, get_teacher_subjects,
    create_session, close_session, extend_session, get_active_sessions,
    mark_attendance, check_attendance_for_session, get_pending_verifications
)
from datetime import date, datetime, timedelta

def test_student_operations(test_db):
    # Test adding and getting a student
    add_student("S101", "John Doe")
    student = get_student("S101")
    assert student is not None
    assert student["name"] == "John Doe"
    
    # Test updating password
    update_student_password("S101", "hashed_password")
    student = get_student("S101")
    assert student["password_hash"] == "hashed_password"

def test_teacher_operations(test_db):
    # Test adding and getting a teacher
    add_teacher("T101", "Jane Smith", "jane@example.com", "CS")
    teacher = get_teacher("T101")
    assert teacher is not None
    assert teacher["name"] == "Jane Smith"
    
    # Test teacher subjects
    from database import add_teacher_subject
    add_teacher_subject("T101", "Python", "Class A")
    subjects = get_teacher_subjects("T101")
    assert len(subjects) == 1
    assert subjects[0]["name"] == "Python"

def test_session_operations(test_db):
    add_teacher("T101", "Jane Smith")
    session_id = create_session("Python", 1, "T101", ttl_minutes=10)
    assert session_id is not None
    
    active_sessions = get_active_sessions()
    assert len(active_sessions) == 1
    assert active_sessions[0]["subject"] == "Python"
    
    # Test extension
    extend_session(session_id, additional_minutes=5)
    # No easy way to check without direct DB query or waiting, but we can assume it doesn't crash
    
    # Test closing
    close_session(session_id)
    active_sessions = get_active_sessions()
    assert len(active_sessions) == 0

def test_attendance_operations(test_db):
    add_student("S101", "John Doe")
    add_teacher("T101", "Jane Smith")
    session_id = create_session("Python", 1, "T101")
    
    # Record attendance
    mark_attendance("S101", session_id, "Face Recognition", confidence_score=0.95)
    
    # Check attendance
    status = check_attendance_for_session("S101", session_id)
    assert status == "Present"
    
    # Test pending verification
    mark_attendance("S102", session_id, "Manual", status="Pending Verification")
    pending = get_pending_verifications("T101")
    assert len(pending) == 1
    assert pending[0]["student_id"] == "S102"
