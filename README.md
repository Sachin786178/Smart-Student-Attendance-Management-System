# Smart Student Attendance Management System
**MCA Semester I | Python Programming | PCCMC105P | Session 2026–27**

## Features
- Administrator login and password change
- Student and subject management
- Date- and subject-wise attendance marking
- Update attendance for an already-marked date
- Attendance summary with percentage
- Date/subject filters and CSV export
- SQLite database created automatically on first run

## Run on macOS / Windows / Linux
1. Install Python 3.10 or later.
2. Extract this folder and open Terminal in it.
3. Create a virtual environment:
   - macOS/Linux: `python3 -m venv venv && source venv/bin/activate`
   - Windows: `py -m venv venv` then `venv\Scripts\activate`
4. Install dependencies: `pip install -r requirements.txt`
5. Start: `python app.py`
6. Open `http://127.0.0.1:5000` in your browser.

## First login
- Username: `admin`
- Password: `admin123`
- Change the password immediately using the Password link.

The database file `attendance.db` is created automatically in the project folder. Back it up regularly.

## Suggested demonstration
1. Sign in as administrator.
2. Add 3–5 sample students and confirm the unique roll numbers.
3. Add or review subjects.
4. Open Mark Attendance, select date and subject, and mark Present/Absent.
5. Save, then open Reports and verify totals and percentages.
6. Export the filtered report as CSV.

## Important notes
- This is an academic demonstration project, not a hardened production attendance platform.
- Use a strong `SECRET_KEY` environment variable before deployment.
- The development server (`debug=True`) is intended only for local testing. Do not expose it publicly.
- Attendance is stored once per student, subject and date; saving again updates the existing record.
