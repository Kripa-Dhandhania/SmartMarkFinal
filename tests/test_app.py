import pytest
from flask import session
from database import add_teacher, add_student, create_session, mark_attendance

def test_home_redirect(client):
    response = client.get('/')
    assert response.status_code == 302 # Redirects to teacher login by default

def test_teacher_login_get(client):
    response = client.get('/teacher/login')
    assert response.status_code == 200
    assert b"Teacher Login" in response.data

def test_teacher_dashboard_unauthorized(client):
    response = client.get('/teacher', follow_redirects=True)
    assert b"Teacher Login" in response.data # Should redirect to login

def test_teacher_dashboard_authorized(client, test_db):
    add_teacher("T101", "Jane Smith")
    with client.session_transaction() as sess:
        sess['teacher_id'] = 'T101'
        sess['teacher_name'] = 'Jane Smith'
    
    response = client.get('/teacher')
    assert response.status_code == 200
    assert b"Jane Smith" in response.data

def test_student_login_get(client):
    response = client.get('/student/login')
    assert response.status_code == 200
    assert b"Student Login" in response.data

def test_student_dashboard_authorized(client, test_db):
    add_student("S101", "John Doe")
    with client.session_transaction() as sess:
        sess['student_id'] = 'S101'
        sess['student_name'] = 'John Doe'
    
    response = client.get('/student/dashboard')
    assert response.status_code == 200
    assert b"S101" in response.data # Template displays student_id

def test_teacher_create_session(client, test_db):
    add_teacher("T101", "Jane Smith")
    from database import add_teacher_subject
    add_teacher_subject("T101", "Mathematics")
    
    with client.session_transaction() as sess:
        sess['teacher_id'] = 'T101'
    
    response = client.post('/teacher/create-session', data={
        'subject': 'Mathematics',
        'hour': '1',
        'duration': '5' # 'ttl' was 'duration' in the form
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert b"Mathematics" in response.data
    assert b"Active Session" in response.data
