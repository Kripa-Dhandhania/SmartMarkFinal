"""
Notification Manager Module for SmartMark
Handles sending automated alerts to students and summaries to teachers.
"""

import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr, make_msgid
import threading

def send_email(recipient_email, subject, html_body, text_body=""):
    """Generic async email sender."""
    sender_email = os.environ.get('SMTP_EMAIL', 'sanya.agarwal240@gmail.com')
    sender_password = os.environ.get('SMTP_PASSWORD', 'afnz lavl pfro schl')

    if not sender_email or not sender_password or not recipient_email:
        print(f"[MAIL] Configuration missing or no recipient for: {subject}")
        return False

    def _send():
        try:
            msg = MIMEMultipart('alternative')
            msg['From'] = formataddr(("SmartMark Administration", sender_email))
            msg['To'] = recipient_email
            msg['Subject'] = subject
            msg['Message-ID'] = make_msgid(domain='christuniversity.in')
            
            if text_body:
                msg.attach(MIMEText(text_body, 'plain'))
            msg.attach(MIMEText(html_body, 'html'))

            with smtplib.SMTP('smtp.gmail.com', 587) as server:
                server.starttls()
                server.login(sender_email, sender_password)
                server.send_message(msg)
            print(f"[MAIL] Sent: {subject} to {recipient_email}")
        except Exception as e:
            print(f"[MAIL] Error sending {subject}: {e}")

    thread = threading.Thread(target=_send)
    thread.daemon = True
    thread.start()
    return True

def send_low_attendance_alert(student_name, student_email, percentage):
    """Send a professional alert to a student below 75%."""
    subject = f"IMPORTANT: Attendance Alert - {percentage}%"
    
    html_body = f"""
    <html>
        <body style="font-family: 'Segoe UI', Arial, sans-serif; color: #334155; line-height: 1.6;">
            <div style="max-width: 600px; margin: 0 auto; border: 1px solid #e2e8f0; border-radius: 12px; overflow: hidden;">
                <div style="background-color: #ef4444; color: white; padding: 30px; text-align: center;">
                    <h1 style="margin: 0; font-size: 20px;">ATTENDANCE ALERT</h1>
                </div>
                <div style="padding: 30px;">
                    <p>Dear <strong>{student_name}</strong>,</p>
                    <p>This is an automated notification regarding your attendance in the current semester.</p>
                    <div style="background-color: #fef2f2; border: 1px solid #fecaca; border-radius: 8px; padding: 20px; margin: 20px 0; text-align: center;">
                        <span style="font-size: 14px; color: #991b1b;">Current Percentage</span><br>
                        <span style="font-size: 32px; font-weight: bold; color: #ef4444;">{percentage}%</span>
                    </div>
                    <p>Your attendance has fallen below the mandatory <strong>75%</strong> requirement. Please ensure you attend the upcoming sessions to avoid academic consequences.</p>
                    <p>If you believe there is an error or have valid medical documentation, please contact the department office immediately.</p>
                    <hr style="border: 0; border-top: 1px solid #e2e8f0; margin: 30px 0;">
                    <p style="font-size: 12px; color: #94a3b8; text-align: center;">This is an automated message from the SmartMark Attendance System.</p>
                </div>
            </div>
        </body>
    </html>
    """
    return send_email(student_email, subject, html_body)

def send_weekly_digest(teacher_name, teacher_email, stats, defaulters):
    """Send a weekly summary to the teacher."""
    subject = f"SmartMark Weekly Digest - {stats['date_range']}"
    
    defaulters_html = ""
    for d in defaulters:
        defaulters_html += f"""
        <tr>
            <td style="padding: 8px; border-bottom: 1px solid #f1f5f9;">{d['student_id']}</td>
            <td style="padding: 8px; border-bottom: 1px solid #f1f5f9;">{d['name']}</td>
            <td style="padding: 8px; border-bottom: 1px solid #f1f5f9; color: #ef4444; font-weight: bold;">{d['percentage']}%</td>
        </tr>
        """
    if not defaulters:
        defaulters_html = "<tr><td colspan='3' style='text-align:center; padding: 20px; color: #22c55e;'>All students are currently above 75%!</td></tr>"

    html_body = f"""
    <html>
        <body style="font-family: 'Segoe UI', Arial, sans-serif; color: #334155; line-height: 1.6;">
            <div style="max-width: 600px; margin: 0 auto; border: 1px solid #e2e8f0; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);">
                <div style="background-color: #1e3a8a; color: white; padding: 25px; text-align: center;">
                    <h1 style="margin: 0; font-size: 20px;">Weekly Attendance Summary</h1>
                    <p style="margin: 5px 0 0 0; opacity: 0.8; font-size: 13px;">{stats['date_range']}</p>
                </div>
                <div style="padding: 30px;">
                    <p>Hello <strong>{teacher_name}</strong>,</p>
                    <p>Here is your weekly SmartMark report for your classes:</p>
                    
                    <table style="width: 100%; border-collapse: collapse; margin: 20px 0; background-color: #f8fafc; border-radius: 8px; border: 1px solid #e2e8f0;">
                        <tr>
                            <td style="padding: 15px;">Total Students</td>
                            <td style="padding: 15px; text-align: right; font-weight: bold;">{stats['total_students']}</td>
                        </tr>
                        <tr>
                            <td style="padding: 15px;">Avg Attendance Rate</td>
                            <td style="padding: 15px; text-align: right; font-weight: bold; color: #3b82f6;">{stats['avg_attendance']}%</td>
                        </tr>
                        <tr>
                            <td style="padding: 15px;">Sessions Conducted</td>
                            <td style="padding: 15px; text-align: right; font-weight: bold;">{stats['sessions_count']}</td>
                        </tr>
                    </table>

                    <h3 style="color: #1e293b; border-bottom: 2px solid #f1f5f9; padding-bottom: 8px; margin-top: 30px;">Defaulters (Below 75%)</h3>
                    <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
                        <thead>
                            <tr style="background-color: #f8fafc;">
                                <th style="text-align: left; padding: 8px; border-bottom: 1px solid #e2e8f0;">ID</th>
                                <th style="text-align: left; padding: 8px; border-bottom: 1px solid #e2e8f0;">Name</th>
                                <th style="text-align: left; padding: 8px; border-bottom: 1px solid #e2e8f0;">Rate</th>
                            </tr>
                        </thead>
                        <tbody>
                            {defaulters_html}
                        </tbody>
                    </table>

                    <div style="margin-top: 40px; text-align: center;">
                        <a href="http://127.0.0.1:5000/analytics" style="background-color: #2563eb; color: white; padding: 12px 25px; text-decoration: none; border-radius: 6px; font-weight: bold; font-size: 14px;">View Live Dashboard</a>
                    </div>
                </div>
            </div>
        </body>
    </html>
    """
    return send_email(teacher_email, subject, html_body)
