import csv
import io
import os
import sqlite3
from datetime import date, datetime
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, render_template, request, redirect, url_for, session, flash, Response, abort

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(APP_DIR, "attendance.db")

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-key-before-deployment")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    with get_db() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            roll_no TEXT UNIQUE NOT NULL,
            full_name TEXT NOT NULL,
            email TEXT,
            course TEXT DEFAULT 'MCA',
            semester TEXT DEFAULT 'I',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_code TEXT UNIQUE NOT NULL,
            subject_name TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            subject_id INTEGER NOT NULL,
            attendance_date TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('Present','Absent')),
            marked_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(student_id, subject_id, attendance_date),
            FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE,
            FOREIGN KEY(subject_id) REFERENCES subjects(id) ON DELETE CASCADE
        );
        """)
        admin = db.execute("SELECT id FROM users WHERE username='admin'").fetchone()
        if not admin:
            db.execute(
                "INSERT INTO users(username,password_hash,full_name) VALUES(?,?,?)",
                ("admin", generate_password_hash("admin123"), "Administrator")
            )
        count = db.execute("SELECT COUNT(*) AS n FROM subjects").fetchone()["n"]
        if count == 0:
            db.executemany(
                "INSERT INTO subjects(subject_code,subject_name) VALUES(?,?)",
                [("PCCMC105P", "Python Programming"), ("MCA101", "Fundamentals of Computer Applications")]
            )

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper

@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        with get_db() as db:
            user = db.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["full_name"] = user["full_name"]
            return redirect(url_for("dashboard"))
        flash("Invalid username or password.", "danger")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))

@app.route("/dashboard")
@login_required
def dashboard():
    today = date.today().isoformat()
    with get_db() as db:
        students = db.execute("SELECT COUNT(*) n FROM students").fetchone()["n"]
        subjects = db.execute("SELECT COUNT(*) n FROM subjects").fetchone()["n"]
        today_total = db.execute("SELECT COUNT(*) n FROM attendance WHERE attendance_date=?", (today,)).fetchone()["n"]
        today_present = db.execute("SELECT COUNT(*) n FROM attendance WHERE attendance_date=? AND status='Present'", (today,)).fetchone()["n"]
        recent = db.execute("""
            SELECT a.attendance_date, s.roll_no, s.full_name, sub.subject_name, a.status
            FROM attendance a JOIN students s ON s.id=a.student_id
            JOIN subjects sub ON sub.id=a.subject_id
            ORDER BY a.attendance_date DESC, a.id DESC LIMIT 8
        """).fetchall()
    pct = round((today_present/today_total)*100, 1) if today_total else 0
    return render_template("dashboard.html", students=students, subjects=subjects,
                           today_total=today_total, today_present=today_present,
                           pct=pct, recent=recent, today=today)

@app.route("/students", methods=["GET", "POST"])
@login_required
def students():
    if request.method == "POST":
        roll = request.form.get("roll_no", "").strip()
        name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip()
        course = request.form.get("course", "MCA").strip()
        semester = request.form.get("semester", "I").strip()
        if not roll or not name:
            flash("Roll number and student name are required.", "danger")
        else:
            try:
                with get_db() as db:
                    db.execute("INSERT INTO students(roll_no,full_name,email,course,semester) VALUES(?,?,?,?,?)",
                               (roll, name, email, course, semester))
                flash("Student added successfully.", "success")
            except sqlite3.IntegrityError:
                flash("That roll number already exists.", "danger")
        return redirect(url_for("students"))
    q = request.args.get("q", "").strip()
    with get_db() as db:
        rows = db.execute("""SELECT * FROM students
            WHERE roll_no LIKE ? OR full_name LIKE ? ORDER BY roll_no""",
            (f"%{q}%", f"%{q}%")).fetchall()
    return render_template("students.html", students=rows, q=q)

@app.route("/students/delete/<int:student_id>", methods=["POST"])
@login_required
def delete_student(student_id):
    with get_db() as db:
        db.execute("DELETE FROM students WHERE id=?", (student_id,))
    flash("Student and linked attendance records deleted.", "success")
    return redirect(url_for("students"))

@app.route("/subjects", methods=["GET", "POST"])
@login_required
def subjects():
    if request.method == "POST":
        code = request.form.get("subject_code", "").strip()
        name = request.form.get("subject_name", "").strip()
        if not code or not name:
            flash("Subject code and name are required.", "danger")
        else:
            try:
                with get_db() as db:
                    db.execute("INSERT INTO subjects(subject_code,subject_name) VALUES(?,?)", (code, name))
                flash("Subject added successfully.", "success")
            except sqlite3.IntegrityError:
                flash("That subject code already exists.", "danger")
        return redirect(url_for("subjects"))
    with get_db() as db:
        rows = db.execute("SELECT * FROM subjects ORDER BY subject_code").fetchall()
    return render_template("subjects.html", subjects=rows)

@app.route("/subjects/delete/<int:subject_id>", methods=["POST"])
@login_required
def delete_subject(subject_id):
    with get_db() as db:
        db.execute("DELETE FROM subjects WHERE id=?", (subject_id,))
    flash("Subject and linked attendance records deleted.", "success")
    return redirect(url_for("subjects"))

@app.route("/attendance", methods=["GET", "POST"])
@login_required
def attendance():
    selected_date = request.values.get("attendance_date", date.today().isoformat())
    selected_subject = request.values.get("subject_id", "")
    with get_db() as db:
        subject_rows = db.execute("SELECT * FROM subjects ORDER BY subject_code").fetchall()
        if request.method == "POST":
            if not selected_subject:
                flash("Please select a subject.", "danger")
                return redirect(url_for("attendance"))
            students_rows = db.execute("SELECT id FROM students ORDER BY roll_no").fetchall()
            for student in students_rows:
                status = request.form.get(f"status_{student['id']}", "Absent")
                if status not in ("Present", "Absent"):
                    status = "Absent"
                db.execute("""
                    INSERT INTO attendance(student_id,subject_id,attendance_date,status)
                    VALUES(?,?,?,?)
                    ON CONFLICT(student_id,subject_id,attendance_date)
                    DO UPDATE SET status=excluded.status, marked_at=CURRENT_TIMESTAMP
                """, (student["id"], int(selected_subject), selected_date, status))
            flash("Attendance saved successfully.", "success")
            return redirect(url_for("attendance", attendance_date=selected_date, subject_id=selected_subject))
        students_rows = db.execute("""
            SELECT s.*, a.status FROM students s
            LEFT JOIN attendance a ON a.student_id=s.id AND a.subject_id=? AND a.attendance_date=?
            ORDER BY s.roll_no
        """, (int(selected_subject) if selected_subject else -1, selected_date)).fetchall()
    return render_template("attendance.html", students=students_rows, subjects=subject_rows,
                           selected_date=selected_date, selected_subject=str(selected_subject))

@app.route("/reports")
@login_required
def reports():
    start = request.args.get("start", "")
    end = request.args.get("end", "")
    subject_id = request.args.get("subject_id", "")
    clauses, params = [], []
    if start:
        clauses.append("a.attendance_date >= ?"); params.append(start)
    if end:
        clauses.append("a.attendance_date <= ?"); params.append(end)
    if subject_id:
        clauses.append("a.subject_id = ?"); params.append(subject_id)
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    with get_db() as db:
        subjects_rows = db.execute("SELECT * FROM subjects ORDER BY subject_code").fetchall()
        rows = db.execute(f"""
            SELECT s.id, s.roll_no, s.full_name, sub.subject_name,
                   COUNT(a.id) AS total,
                   SUM(CASE WHEN a.status='Present' THEN 1 ELSE 0 END) AS present,
                   SUM(CASE WHEN a.status='Absent' THEN 1 ELSE 0 END) AS absent
            FROM attendance a JOIN students s ON s.id=a.student_id
            JOIN subjects sub ON sub.id=a.subject_id
            {where}
            GROUP BY s.id, sub.id ORDER BY s.roll_no, sub.subject_name
        """, params).fetchall()
    report_rows = []
    for r in rows:
        total = r["total"] or 0
        present = r["present"] or 0
        report_rows.append({**dict(r), "percentage": round(present/total*100, 1) if total else 0})
    return render_template("reports.html", rows=report_rows, subjects=subjects_rows,
                           start=start, end=end, subject_id=subject_id)

@app.route("/reports/export")
@login_required
def export_report():
    start = request.args.get("start", "")
    end = request.args.get("end", "")
    subject_id = request.args.get("subject_id", "")
    clauses, params = [], []
    if start: clauses.append("a.attendance_date >= ?"); params.append(start)
    if end: clauses.append("a.attendance_date <= ?"); params.append(end)
    if subject_id: clauses.append("a.subject_id = ?"); params.append(subject_id)
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    with get_db() as db:
        rows = db.execute(f"""
            SELECT s.roll_no, s.full_name, sub.subject_code, sub.subject_name,
                   COUNT(a.id) total,
                   SUM(CASE WHEN a.status='Present' THEN 1 ELSE 0 END) present,
                   SUM(CASE WHEN a.status='Absent' THEN 1 ELSE 0 END) absent
            FROM attendance a JOIN students s ON s.id=a.student_id
            JOIN subjects sub ON sub.id=a.subject_id {where}
            GROUP BY s.id, sub.id ORDER BY s.roll_no
        """, params).fetchall()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Roll No", "Student Name", "Subject Code", "Subject", "Total Classes", "Present", "Absent", "Attendance %"])
    for r in rows:
        total = r["total"] or 0
        present = r["present"] or 0
        writer.writerow([r["roll_no"], r["full_name"], r["subject_code"], r["subject_name"],
                         total, present, r["absent"] or 0, round(present/total*100, 1) if total else 0])
    return Response(output.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=attendance_report.csv"})

@app.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    if request.method == "POST":
        old = request.form.get("old_password", "")
        new = request.form.get("new_password", "")
        if len(new) < 8:
            flash("New password must contain at least 8 characters.", "danger")
        else:
            with get_db() as db:
                user = db.execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()
                if check_password_hash(user["password_hash"], old):
                    db.execute("UPDATE users SET password_hash=? WHERE id=?",
                               (generate_password_hash(new), session["user_id"]))
                    flash("Password updated. Please sign in again.", "success")
                    session.clear()
                    return redirect(url_for("login"))
                flash("Current password is incorrect.", "danger")
    return render_template("change_password.html")

@app.errorhandler(404)
def not_found(error):
    return render_template("404.html"), 404

init_db()

if __name__ == "__main__":
    app.run(debug=True)
