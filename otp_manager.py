"""
OTP Manager Module for Smart Attendance System
Handles OTP generation, email sending, and validation for fallback authentication.
"""

import random
import string
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr, make_msgid
import threading
import time


def generate_otp(length=6):
    """
    Generate a random numeric OTP.
    
    Args:
        length: Number of digits (default 6)
    
    Returns:
        String OTP
    """
    otp = ''.join(random.choices(string.digits, k=length))
    # Removed terminal print for security/privacy as requested
    return otp


def send_otp_email(recipient_email, otp, student_name=None):
    """
    Send OTP to recipient email (now teacher) via SMTP.
    Includes student name to help teacher identify the request.
    """
    sender_email = os.environ.get('SMTP_EMAIL')
    sender_password = os.environ.get('SMTP_PASSWORD')

    if not sender_email or not sender_password:
        print("[OTP] SMTP credentials not configured. OTP printed to terminal only.")
        print(f"[OTP] Would have sent OTP {otp} for {student_name if student_name else 'a student'} to {recipient_email}")
        return False

    if not recipient_email:
        print("[OTP] No recipient email provided. OTP printed to terminal only.")
        return False

    try:
        msg = MIMEMultipart('alternative')
        msg['From'] = formataddr(("SmartMark Attendance System", sender_email))
        msg['To'] = recipient_email
        msg['Subject'] = f"OTP for {student_name if student_name else 'Attendance'} verification"
        
        # Anti-Spam Headers
        msg['Message-ID'] = make_msgid(domain='christuniversity.in')
        msg['Importance'] = 'high'
        msg['X-Priority'] = '1' # High
        msg['Priority'] = 'urgent'

        # Plain-text version
        text_body = f"Hello,\n\nStudent {student_name if student_name else ''} is requesting attendance verification via OTP.\n\nThe verification code is: {otp}\n\nThis code is valid for 10 minutes.\n\nPlease share this with the student ONLY if they are physically present.\n\nPlease do not reply to this automated message."

        # Premium HTML Template for OTP
        html_body = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #1e293b; margin: 0; padding: 0;">
                <div style="background-color: #f8fafc; padding: 40px 10px;">
                    <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">
                        <div style="background-color: #1e3a8a; color: #ffffff; padding: 30px; text-align: center; border-radius: 12px 12px 0 0;">
                            <h1 style="margin:0; font-size: 24px; letter-spacing: 1px;">SMARTMARK</h1>
                            <p style="margin: 5px 0 0 0; opacity: 0.8; font-size: 14px;">Attendance Verification</p>
                        </div>
                        <div style="padding: 40px 30px; text-align: center;">
                            <p style="font-size: 18px; color: #334155; margin-bottom: 20px;">Verification Request for {student_name if student_name else 'a student'}</p>
                            <p style="font-size: 14px; color: #64748b; margin-bottom: 30px;">Please share the code below with the student if they are present in your class.</p>
                            <div style="background-color: #f1f5f9; padding: 24px; border-radius: 12px; margin: 0 auto 30px; display: inline-block; border: 1px dashed #cbd5e1;">
                                <span style="font-size: 42px; font-weight: 800; letter-spacing: 8px; color: #1e3a8a; font-family: 'Courier New', Courier, monospace;">{otp}</span>
                            </div>
                            <p style="font-size: 14px; color: #64748b; margin-top: 20px;">
                                This code will expire in <strong>10 minutes</strong>.<br>
                                Secure verification powered by SmartMark.
                            </p>
                        </div>
                        <div style="background-color: #f8fafc; padding: 20px; text-align: center; border-radius: 0 0 12px 12px; border-top: 1px solid #e2e8f0;">
                            <p style="margin: 0; font-size: 12px; color: #94a3b8;">
                                &copy; 2026 SmartMark Attendance System. All rights reserved.
                            </p>
                        </div>
                    </div>
                </div>
            </body>
        </html>
        """
        
        msg.attach(MIMEText(text_body, 'plain'))
        msg.attach(MIMEText(html_body, 'html'))

        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)

        print(f"[OTP] Email sent to teacher for student {student_name}")
        return True

    except Exception as e:
        print(f"[OTP] Failed to send email: {e}")
        # Only log to terminal if email fails, for debugging
        print(f"[OTP] DEBUG: OTP is {otp} (email sending failed)")
        return False


def send_otp_email_async(recipient_email, otp, student_name=None):
    """
    Send OTP email in a background thread to avoid blocking the main application.
    Does not return a value, but logs status to terminal.
    """
    thread = threading.Thread(target=send_otp_email, args=(recipient_email, otp, student_name))
    thread.daemon = True  # Thread will exit when main process exits
    thread.start()
    print(f"[OTP] background email thread started for student {student_name} (sent to {recipient_email})")


def validate_otp(user_input, stored_otp):
    """
    Validate user-entered OTP against stored OTP.
    
    Args:
        user_input: OTP entered by user
        stored_otp: OTP stored in session
    
    Returns:
        True if OTP matches, False otherwise
    """
    if not user_input or not stored_otp:
        return False
    
    # Strip whitespace and compare
    is_valid = user_input.strip() == stored_otp.strip()
    
    if is_valid:
        print("[OTP] OTP validated successfully!")
    else:
        print("[OTP] OTP validation failed.")
    
    return is_valid


# Test the module
if __name__ == '__main__':
    otp = generate_otp()
    print(f"Generated OTP: {otp}")
    
    # Test validation
    print(f"Valid OTP test: {validate_otp(otp, otp)}")
    print(f"Invalid OTP test: {validate_otp('000000', otp)}")
