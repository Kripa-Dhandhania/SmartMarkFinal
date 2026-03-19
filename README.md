# SmartMark - Unified Attendance System

A comprehensive, Flask-based attendance management system that integrates face recognition, OTP verification, and geolocation tracking for secure and efficient attendance tracking.

## Features

### For Teachers
- **Session Management**: Start and close attendance sessions with customizable TTL (Time To Live).
- **Multiple Verification Methods**: Supports Face Recognition, OTP (dynamic 10-second slots), and Geolocation.
- **Analytics Dashboard**: Real-time stats, daily attendance trends, and defaulter identification.
- **Manual Overrides**: Manually mark student attendance or approve/reject pending verifications.
- **Leave Management**: Review and update student leave requests.
- **Reporting**: Export attendance data to CSV and formatted Excel files.

### For Students
- **Face Enrollment**: Easy enrollment process using browser-based camera capture.
- **Attendance Marking**: Secure attendance marking using a combination of face scan, geolocation, and session-specific OTP.
- **Personal Dashboard**: Track attendance history by subject and view individual statistics.
- **Leave Application**: Apply for leaves directly through the portal.

## Technology Stack
- **Backend**: Flask (Python)
- **Database**: SQLite (with automated migrations)
- **Computer Vision**: OpenCV (Face detection and recognition)
- **Frontend**: HTML5, CSS3, JavaScript
- **Reporting**: Openpyxl (Excel), CSV
- **Security**: Werkzeug password hashing, TOTP-style dynamic OTP

## Prerequisites
- Python 3.10+
- Camera access (for face recognition)

## Installation & Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/Kripa-Dhandhania/SmartMarkFinal.git
   cd SmartMarkFinal
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Environment Variables**:
   Create a `.env` file or set the following environment variables:
   - `FLASK_SECRET_KEY`: A secure key for session management.
   - `CLASSROOM_LAT`: Target latitude for geolocation verification.
   - `CLASSROOM_LON`: Target longitude for geolocation verification.
   - `CLASSROOM_RADIUS`: Allowed radius in meters (default: 20m).
   - `MAIL_USERNAME` / `MAIL_PASSWORD`: For OTP email functionality (if enabled).

4. **Initialize Database**:
   The database initializes automatically on the first run. For a fresh start, you can run:
   ```bash
   python -c "from database import init_db; init_db()"
   ```

5. **Run the application**:
   ```bash
   python app.py
   ```
   Access the app at `http://127.0.0.1:5000`.

## Testing and Utilities
- `simulate_attendance.py`: Script to generate mock attendance data.
- `verify_security.py`: Security checks for the system.
- `inspect_db.py` / `deep_inspect.py`: Database inspection tools.
- `cleanup_db.py`: Utilty to reset or clean database records.

## 📄 License
This project is licensed under the MIT License.
