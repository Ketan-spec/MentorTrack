from flask import Flask, request, render_template, redirect, url_for, session, flash, jsonify
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime

# === CONFIG ===
DB_NAME = "mentortrack.db"
SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key-change-in-production")

app = Flask(__name__)
app.secret_key = SECRET_KEY

# === DB HELPERS ===
def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Users table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            domain TEXT,
            bio TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Mentorship relationships
    cur.execute("""
        CREATE TABLE IF NOT EXISTS mentorships (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mentor_id INTEGER NOT NULL,
            mentee_id INTEGER NOT NULL,
            status TEXT DEFAULT 'active',
            progress INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (mentor_id) REFERENCES users(id),
            FOREIGN KEY (mentee_id) REFERENCES users(id)
        )
    """)
    
    # Tasks table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mentorship_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            deadline DATE,
            status TEXT DEFAULT 'assigned',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (mentorship_id) REFERENCES mentorships(id)
        )
    """)
    
    # Sessions/Meetings table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mentorship_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            session_date DATETIME NOT NULL,
            duration INTEGER DEFAULT 60,
            meeting_link TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (mentorship_id) REFERENCES mentorships(id)
        )
    """)
    
    # Resources table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS resources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mentor_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            url TEXT NOT NULL,
            resource_type TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (mentor_id) REFERENCES users(id)
        )
    """)
    
    conn.commit()
    conn.close()

# === AUTHENTICATION ===
@app.route("/")
def index():
    return render_template("index.html")

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        full_name = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        role = request.form['role']

        if password != confirm_password:
            flash("Passwords do not match", "error")
            return redirect(url_for('signup'))

        hashed_password = generate_password_hash(password)

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                "INSERT INTO users (full_name, email, password, role) VALUES (?, ?, ?, ?)",
                (full_name, email, hashed_password, role)
            )
            conn.commit()
        except sqlite3.IntegrityError:
            flash("Email already registered", "error")
            conn.close()
            return redirect(url_for('signup'))

        conn.close()

        flash("Account created successfully! Please log in.", "success")
        return redirect(url_for('login'))

    return render_template('signup.html')

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        role = request.form.get("role")
        email = request.form.get("email")
        password = request.form.get("password")

        if not role or not email or not password:
            flash("All fields are required", "error")
            return render_template("login.html")

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE email = ? AND role = ?", (email, role))
        user = cursor.fetchone()

        if not user:
            conn.close()
            flash("Invalid credentials", "error")
            return render_template("login.html")

        if not check_password_hash(user["password"], password):
            conn.close()
            flash("Invalid credentials", "error")
            return render_template("login.html")

        session["user_id"] = user["id"]
        session["user_name"] = user["full_name"]
        session["role"] = user["role"]
        session["email"] = user["email"]

        conn.close()

        if user["role"] == "mentor":
            return redirect(url_for("mentor_dashboard"))
        else:
            return redirect(url_for("mentee_dashboard"))

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out successfully.", "info")
    return redirect(url_for("index"))

# === MENTOR DASHBOARD ===
@app.route("/mentor-dashboard")
def mentor_dashboard():
    if 'user_id' not in session or session.get('role') != 'mentor':
        flash('Please login as a mentor', 'error')
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    
    # Get mentor's mentees
    mentees = conn.execute("""
        SELECT u.id, u.full_name, u.email, m.progress, m.id as mentorship_id
        FROM users u
        JOIN mentorships m ON u.id = m.mentee_id
        WHERE m.mentor_id = ? AND m.status = 'active'
    """, (session['user_id'],)).fetchall()
    
    # Get stats
    total_mentees = len(mentees)
    
    pending_tasks = conn.execute("""
        SELECT COUNT(*) as count FROM tasks t
        JOIN mentorships m ON t.mentorship_id = m.id
        WHERE m.mentor_id = ? AND t.status IN ('assigned', 'in_progress')
    """, (session['user_id'],)).fetchone()['count']
    
    upcoming_sessions = conn.execute("""
        SELECT COUNT(*) as count FROM sessions s
        JOIN mentorships m ON s.mentorship_id = m.id
        WHERE m.mentor_id = ? AND s.session_date > datetime('now')
    """, (session['user_id'],)).fetchone()['count']
    
    # Get mentor's resources
    resources = conn.execute("""
        SELECT * FROM resources WHERE mentor_id = ? ORDER BY created_at DESC LIMIT 3
    """, (session['user_id'],)).fetchall()
    
    conn.close()
    
    return render_template("mentor-dashboard.html", 
                         mentees=mentees,
                         total_mentees=total_mentees,
                         pending_tasks=pending_tasks,
                         upcoming_sessions=upcoming_sessions,
                         resources=resources,
                         user_name=session.get('user_name'))

# === MENTEE DASHBOARD ===
@app.route("/mentee-dashboard")
def mentee_dashboard():
    if 'user_id' not in session or session.get('role') != 'mentee':
        flash('Please login as a mentee', 'error')
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    
    # Get mentee's mentor
    mentor = conn.execute("""
        SELECT u.full_name, u.email, u.domain, m.progress, m.id as mentorship_id
        FROM users u
        JOIN mentorships m ON u.id = m.mentor_id
        WHERE m.mentee_id = ? AND m.status = 'active'
    """, (session['user_id'],)).fetchone()
    
    # Get tasks
    tasks = []
    if mentor:
        tasks = conn.execute("""
            SELECT * FROM tasks 
            WHERE mentorship_id = ? 
            ORDER BY deadline ASC
        """, (mentor['mentorship_id'],)).fetchall()
    
    # Get upcoming sessions
    sessions = []
    if mentor:
        sessions = conn.execute("""
            SELECT * FROM sessions 
            WHERE mentorship_id = ? AND session_date > datetime('now')
            ORDER BY session_date ASC LIMIT 3
        """, (mentor['mentorship_id'],)).fetchall()
    
    conn.close()
    
    return render_template("mentee-dashboard.html",
                         mentor=mentor,
                         tasks=tasks,
                         sessions=sessions,
                         user_name=session.get('user_name'))

# === TASK MANAGEMENT ===
@app.route("/api/tasks/create", methods=['POST'])
def create_task():
    if 'user_id' not in session or session.get('role') != 'mentor':
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.json
    mentorship_id = data.get('mentorship_id')
    title = data.get('title')
    description = data.get('description')
    deadline = data.get('deadline')
    
    conn = get_db_connection()
    
    # Verify mentor owns this mentorship
    mentorship = conn.execute("""
        SELECT * FROM mentorships WHERE id = ? AND mentor_id = ?
    """, (mentorship_id, session['user_id'])).fetchone()
    
    if not mentorship:
        conn.close()
        return jsonify({'error': 'Invalid mentorship'}), 400
    
    conn.execute("""
        INSERT INTO tasks (mentorship_id, title, description, deadline)
        VALUES (?, ?, ?, ?)
    """, (mentorship_id, title, description, deadline))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'Task created successfully'})

@app.route("/api/tasks/<int:task_id>/update-status", methods=['POST'])
def update_task_status(task_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.json
    new_status = data.get('status')
    
    conn = get_db_connection()
    conn.execute("UPDATE tasks SET status = ? WHERE id = ?", (new_status, task_id))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'Task status updated'})

# === RESOURCE MANAGEMENT ===
@app.route("/api/resources/create", methods=['POST'])
def create_resource():
    if 'user_id' not in session or session.get('role') != 'mentor':
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.json
    title = data.get('title')
    url = data.get('url')
    resource_type = data.get('type', 'link')
    
    conn = get_db_connection()
    conn.execute("""
        INSERT INTO resources (mentor_id, title, url, resource_type)
        VALUES (?, ?, ?, ?)
    """, (session['user_id'], title, url, resource_type))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'Resource added successfully'})

# === MENTORSHIP MANAGEMENT ===
@app.route("/api/mentorships/create", methods=['POST'])
def create_mentorship():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.json
    mentor_id = data.get('mentor_id')
    mentee_id = data.get('mentee_id')
    
    conn = get_db_connection()
    
    # Check if mentorship already exists
    existing = conn.execute("""
        SELECT * FROM mentorships 
        WHERE mentor_id = ? AND mentee_id = ? AND status = 'active'
    """, (mentor_id, mentee_id)).fetchone()
    
    if existing:
        conn.close()
        return jsonify({'error': 'Mentorship already exists'}), 400
    
    conn.execute("""
        INSERT INTO mentorships (mentor_id, mentee_id)
        VALUES (?, ?)
    """, (mentor_id, mentee_id))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'Mentorship created successfully'})

# === UTILITY ROUTES ===
@app.route("/check_users")
def check_users():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, full_name, email, role, created_at FROM users")
    rows = cur.fetchall()
    conn.close()
    return "<pre>" + "\n".join(str(dict(r)) for r in rows) + "</pre>"

@app.route("/init_db")
def route_init_db():
    init_db()
    return "Database initialized successfully!"

# === ERROR HANDLERS ===
@app.errorhandler(404)
def not_found(e):
    return render_template('index.html'), 404

@app.errorhandler(500)
def server_error(e):
    return "Internal Server Error", 500

if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)