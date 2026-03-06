import pytest
from otp_manager import generate_otp, validate_otp

def test_generate_otp():
    otp = generate_otp(6)
    assert len(otp) == 6
    assert otp.isdigit()
    
    otp2 = generate_otp(4)
    assert len(otp2) == 4

def test_validate_otp():
    otp = "123456"
    assert validate_otp("123456", otp) is True
    assert validate_otp(" 123456 ", otp) is True
    assert validate_otp("654321", otp) is False
    assert validate_otp("", otp) is False
    assert validate_otp(None, otp) is False

def test_send_otp_email_mocked(mocker):
    # This requires pytest-mock
    # We will just test that it doesn't crash when credentials aren't set
    import os
    from otp_manager import send_otp_email
    
    # Ensure no credentials in env for this test
    mocker.patch.dict(os.environ, {"SMTP_EMAIL": "", "SMTP_PASSWORD": ""})
    
    # Should return False but not raise exception
    result = send_otp_email("test@example.com", "123456", "Test Student")
    assert result is False
