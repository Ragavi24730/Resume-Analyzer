import os
import re
import sqlite3
import csv
from datetime import datetime
from functools import wraps

from flask import (
    Flask, render_template, request, redirect, url_for, flash, session, g
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import PyPDF2
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Initialize Flask application
app = Flask(__name__)
app.secret_key = 'super_secret_ai_resume_analyzer_key_2026'

# Configuration Constants
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, 'database.db')
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
DATA_CSV_PATH = os.path.join(BASE_DIR, 'data', 'jobs.csv')
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB limit
ALLOWED_EXTENSIONS = {'pdf'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# Ensure required directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(os.path.dirname(DATA_CSV_PATH), exist_ok=True)

# Predefined Technical Skills Master List
MASTER_SKILLS = [
    "Python", "Java", "C", "C++", "JavaScript", "HTML", "CSS", "React",
    "Angular", "Node.js", "Django", "Flask", "PHP", "MySQL", "SQL", "MongoDB",
    "Git", "GitHub", "REST API", "API", "AWS", "Azure", "Docker", "Linux",
    "Machine Learning", "Scikit-learn", "Pandas", "NumPy", "Data Structures",
    "OOP", "DBMS", "Computer Networks", "Cyber Security", "Cloud Computing"
]


# ==============================================================================
# DATABASE HELPERS & INITIALIZATION
# ==============================================================================

def get_db():
    """Opens a new SQLite database connection per request."""
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(exception=None):
    """Closes the database connection at the end of request."""
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    """Creates database tables and initializes sample job listings if empty."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    # Users Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    ''')

    # Resumes Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS resumes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            filename TEXT NOT NULL,
            extracted_text TEXT NOT NULL,
            upload_date TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    # Analysis Results Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS analysis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            resume_id INTEGER NOT NULL,
            target_role TEXT NOT NULL,
            match_percentage REAL NOT NULL,
            matched_skills TEXT NOT NULL,
            missing_skills TEXT NOT NULL,
            analysis_date TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (resume_id) REFERENCES resumes (id)
        )
    ''')

    # Jobs Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            company TEXT NOT NULL,
            location TEXT NOT NULL,
            skills TEXT NOT NULL,
            description TEXT NOT NULL,
            salary TEXT NOT NULL,
            job_type TEXT NOT NULL
        )
    ''')

    conn.commit()

    # Seed Jobs Table from CSV if empty
    cursor.execute('SELECT COUNT(*) FROM jobs')
    count = cursor.fetchone()[0]
    if count == 0 and os.path.exists(DATA_CSV_PATH):
        try:
            with open(DATA_CSV_PATH, mode='r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    cursor.execute('''
                        INSERT INTO jobs (title, company, location, skills, description, salary, job_type)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        row['title'], row['company'], row['location'],
                        row['skills'], row['description'], row['salary'], row['job_type']
                    ))
            conn.commit()
            print("[INFO] Database successfully seeded with job listings from jobs.csv")
        except Exception as e:
            print(f"[ERROR] Seeding jobs table failed: {e}")

    conn.close()


# Initialize SQLite Database structure on module load
init_db()


# ==============================================================================
# AUTHENTICATION DECORATOR & UTILITIES
# ==============================================================================

def login_required(f):
    """Decorator to enforce login on protected routes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def allowed_file(filename):
    """Verifies allowed file extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ==============================================================================
# RESUME PARSING & NLP SKILL EXTRACTION ENGINE
# ==============================================================================

def extract_text_from_pdf(pdf_path):
    """Extracts raw text content from PDF file using PyPDF2."""
    text = ""
    try:
        reader = PyPDF2.PdfReader(pdf_path)
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"
    except Exception as e:
        print(f"[ERROR] PDF Parsing Error: {e}")
        return None
    return text.strip()

def detect_skills(text):
    """
    Detects occurrence of master skills in extracted text using precise regex.
    Prevents false positives (e.g. matching 'C' inside 'Cloud' or 'Cat').
    """
    if not text:
        return []

    text_lower = text.lower()
    detected = []

    for skill in MASTER_SKILLS:
        skill_clean = skill.strip()
        # Escape special characters in skill names like C++, Node.js, REST API
        escaped_skill = re.escape(skill_clean.lower())
        
        # Build regex boundary pattern
        pattern = r'(?:\b|_)' + escaped_skill + r'(?:\b|_)'
        if re.search(pattern, text_lower):
            detected.append(skill_clean)

    return sorted(list(set(detected)))


# ==============================================================================
# JOB MATCHING & MACHINE LEARNING ALGORITHM
# ==============================================================================

def calculate_job_matching(resume_text, resume_skills, job_record):
    """
    Calculates hybrid job match percentage:
    - 70% Skill Overlap Match
    - 30% Scikit-learn TF-IDF Cosine Similarity
    """
    job_required_skills = [s.strip() for s in job_record['skills'].split(',') if s.strip()]
    
    # 1. Skill Match Percentage
    if job_required_skills:
        matched = [s for s in job_required_skills if s.lower() in [rs.lower() for rs in resume_skills]]
        missing = [s for s in job_required_skills if s.lower() not in [rs.lower() for rs in resume_skills]]
        skill_score = (len(matched) / len(job_required_skills)) * 100.0
    else:
        matched = []
        missing = []
        skill_score = 100.0

    # 2. TF-IDF Cosine Similarity
    tfidf_score = 0.0
    try:
        job_description = f"{job_record['title']} {job_record['description']} {job_record['skills']}"
        vectorizer = TfidfVectorizer(stop_words='english')
        tfidf_matrix = vectorizer.fit_transform([resume_text, job_description])
        sim = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
        tfidf_score = float(sim) * 100.0
    except Exception as e:
        print(f"[WARN] TF-IDF Computation skipped: {e}")
        tfidf_score = skill_score

    # 3. Hybrid Combined Score
    final_score = (0.70 * skill_score) + (0.30 * tfidf_score)
    final_score = round(min(max(final_score, 0.0), 100.0), 1)

    return {
        'match_percentage': final_score,
        'skill_score': round(skill_score, 1),
        'tfidf_score': round(tfidf_score, 1),
        'matched_skills': matched,
        'missing_skills': missing
    }


# ==============================================================================
# FLASK ROUTES
# ==============================================================================

@app.route('/')
def index():
    """Home landing page."""
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    """User account registration route."""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        # Validation
        if not name or not email or not password or not confirm_password:
            flash('All fields are required.', 'danger')
            return redirect(url_for('register'))

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('register'))

        db = get_db()
        cursor = db.cursor()
        
        # Check email uniqueness
        cursor.execute('SELECT id FROM users WHERE email = ?', (email,))
        if cursor.fetchone():
            flash('Email address is already registered. Please login.', 'warning')
            return redirect(url_for('register'))

        # Password hashing & insertion
        hashed_pw = generate_password_hash(password)
        created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        cursor.execute('''
            INSERT INTO users (name, email, password, created_at)
            VALUES (?, ?, ?, ?)
        ''', (name, email, hashed_pw, created_at))
        db.commit()

        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login route."""
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        if not email or not password:
            flash('Please enter email and password.', 'danger')
            return redirect(url_for('login'))

        db = get_db()
        cursor = db.cursor()
        cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
        user = cursor.fetchone()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            session['user_email'] = user['email']
            flash(f'Welcome back, {user["name"]}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password credentials.', 'danger')
            return redirect(url_for('login'))

    return render_template('login.html')


@app.route('/logout')
def logout():
    """Clears authentication session."""
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))


@app.route('/dashboard')
@login_required
def dashboard():
    """User dashboard showing stats, latest resume result, and top job matches."""
    user_id = session['user_id']
    db = get_db()
    cursor = db.cursor()

    # User Details
    cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()

    # Total Resumes Analyzed
    cursor.execute('SELECT COUNT(*) FROM resumes WHERE user_id = ?', (user_id,))
    resumes_count = cursor.fetchone()[0]

    # Latest Analysis Record
    cursor.execute('''
        SELECT * FROM analysis 
        WHERE user_id = ? 
        ORDER BY id DESC LIMIT 1
    ''', (user_id,))
    latest_analysis = cursor.fetchone()

    # Compute Total Skills Detected & Avg Match Score
    cursor.execute('SELECT matched_skills, match_percentage FROM analysis WHERE user_id = ?', (user_id,))
    all_analyses = cursor.fetchall()
    
    total_skills_set = set()
    total_scores = 0.0

    for a in all_analyses:
        total_scores += a['match_percentage']
        if a['matched_skills']:
            for s in a['matched_skills'].split(','):
                if s.strip():
                    total_skills_set.add(s.strip().lower())

    avg_match = round(total_scores / len(all_analyses), 1) if all_analyses else 0.0

    # Recommended top jobs
    cursor.execute('SELECT * FROM jobs ORDER BY id ASC LIMIT 4')
    top_jobs = cursor.fetchall()

    # Total Jobs count
    cursor.execute('SELECT COUNT(*) FROM jobs')
    total_jobs_count = cursor.fetchone()[0]

    stats = {
        'resumes_analyzed': resumes_count,
        'skills_detected': len(total_skills_set),
        'jobs_recommended': total_jobs_count,
        'avg_match': avg_match
    }

    return render_template(
        'dashboard.html',
        user=user,
        stats=stats,
        latest_analysis=latest_analysis,
        top_jobs=top_jobs
    )


@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    """Resume upload and processing route."""
    if request.method == 'POST':
        if 'resume' not in request.files:
            flash('No file part selected.', 'danger')
            return redirect(url_for('upload'))

        file = request.files['resume']
        target_role_select = request.form.get('target_role_select', '').strip()
        custom_role = request.form.get('custom_target_role', '').strip()

        target_role = custom_role if target_role_select == 'Custom Role' and custom_role else target_role_select

        if file.filename == '':
            flash('No file selected.', 'danger')
            return redirect(url_for('upload'))

        if not allowed_file(file.filename):
            flash('Only PDF files are allowed.', 'danger')
            return redirect(url_for('upload'))

        # Secure file saving
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_filename = f"{session['user_id']}_{timestamp}_{filename}"
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        
        file.save(save_path)

        # PyPDF2 Text Extraction
        extracted_text = extract_text_from_pdf(save_path)
        if not extracted_text:
            flash('Could not extract readable text from PDF. Ensure it is not an image-only scan.', 'danger')
            return redirect(url_for('upload'))

        user_id = session['user_id']
        upload_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        db = get_db()
        cursor = db.cursor()

        # Save to resumes table
        cursor.execute('''
            INSERT INTO resumes (user_id, filename, extracted_text, upload_date)
            VALUES (?, ?, ?, ?)
        ''', (user_id, unique_filename, extracted_text, upload_date))
        resume_id = cursor.lastrowid

        # Detect resume skills
        resume_skills = detect_skills(extracted_text)

        # Match against target role or target job in jobs table
        cursor.execute('SELECT * FROM jobs WHERE title LIKE ?', (f'%{target_role}%',))
        target_jobs = cursor.fetchall()
        
        if not target_jobs:
            cursor.execute('SELECT * FROM jobs')
            target_jobs = cursor.fetchall()

        # Calculate best match score for target role
        best_match_pct = 0.0
        best_matched_skills = []
        best_missing_skills = []

        for job in target_jobs:
            match_res = calculate_job_matching(extracted_text, resume_skills, job)
            if match_res['match_percentage'] >= best_match_pct:
                best_match_pct = match_res['match_percentage']
                best_matched_skills = match_res['matched_skills']
                best_missing_skills = match_res['missing_skills']

        matched_str = ", ".join(best_matched_skills)
        missing_str = ", ".join(best_missing_skills)

        # Save to analysis table
        cursor.execute('''
            INSERT INTO analysis (user_id, resume_id, target_role, match_percentage, matched_skills, missing_skills, analysis_date)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, resume_id, target_role, best_match_pct, matched_str, missing_str, upload_date))
        analysis_id = cursor.lastrowid
        db.commit()

        flash('Resume successfully parsed and analyzed!', 'success')
        return redirect(url_for('result', analysis_id=analysis_id))

    return render_template('upload.html')


@app.route('/result/<int:analysis_id>')
@login_required
def result(analysis_id):
    """Detailed resume analysis result view."""
    user_id = session['user_id']
    db = get_db()
    cursor = db.cursor()

    cursor.execute('''
        SELECT a.*, r.extracted_text 
        FROM analysis a
        JOIN resumes r ON a.resume_id = r.id
        WHERE a.id = ? AND a.user_id = ?
    ''', (analysis_id, user_id))
    analysis = cursor.fetchone()

    if not analysis:
        flash('Analysis record not found.', 'danger')
        return redirect(url_for('dashboard'))

    # Extract detected skills from resume text
    detected_skills = detect_skills(analysis['extracted_text'])
    matched_skills = [s.strip() for s in analysis['matched_skills'].split(',') if s.strip()]
    missing_skills = [s.strip() for s in analysis['missing_skills'].split(',') if s.strip()]

    # Fetch and rank all jobs for recommendations
    cursor.execute('SELECT * FROM jobs')
    all_jobs = cursor.fetchall()
    
    recommended_jobs = []
    for job in all_jobs:
        match_info = calculate_job_matching(analysis['extracted_text'], detected_skills, job)
        job_dict = dict(job)
        job_dict['match_score'] = match_info['match_percentage']
        job_dict['matched_skills'] = match_info['matched_skills']
        recommended_jobs.append(job_dict)

    # Sort jobs by match percentage descending
    recommended_jobs.sort(key=lambda x: x['match_score'], reverse=True)

    return render_template(
        'result.html',
        analysis=analysis,
        detected_skills=detected_skills,
        matched_skills=matched_skills,
        missing_skills=missing_skills,
        recommended_jobs=recommended_jobs[:6]
    )


@app.route('/jobs')
def jobs_page():
    """All jobs listing & filtering page."""
    search_query = request.args.get('q', '').strip()
    db = get_db()
    cursor = db.cursor()

    if search_query:
        cursor.execute('''
            SELECT * FROM jobs 
            WHERE title LIKE ? OR company LIKE ? OR location LIKE ? OR skills LIKE ?
        ''', (f'%{search_query}%', f'%{search_query}%', f'%{search_query}%', f'%{search_query}%'))
    else:
        cursor.execute('SELECT * FROM jobs ORDER BY id ASC')

    jobs = cursor.fetchall()

    return render_template('jobs.html', jobs=jobs, search_query=search_query)


@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """User profile management route."""
    user_id = session['user_id']
    db = get_db()
    cursor = db.cursor()

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()

        if not name or not email:
            flash('Name and Email are required.', 'danger')
            return redirect(url_for('profile'))

        # Check for duplicate email across other users
        cursor.execute('SELECT id FROM users WHERE email = ? AND id != ?', (email, user_id))
        if cursor.fetchone():
            flash('This email is already in use by another account.', 'danger')
            return redirect(url_for('profile'))

        cursor.execute('UPDATE users SET name = ?, email = ? WHERE id = ?', (name, email, user_id))
        db.commit()

        session['user_name'] = name
        session['user_email'] = email
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile'))

    cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()

    return render_template('profile.html', user=user)


# ==============================================================================
# ERROR HANDLERS
# ==============================================================================

@app.errorhandler(404)
def page_not_found(e):
    return render_template('index.html'), 404

@app.errorhandler(500)
def server_error(e):
    flash('An internal error occurred. Please try again.', 'danger')
    return redirect(url_for('index'))


# ==============================================================================
# MAIN ENTRYPOINT
# ==============================================================================

if __name__ == '__main__':
    print("[INFO] Starting AI-Powered Resume Analyzer Flask Server on http://127.0.0.1:5000/")
    app.run(debug=True, host='127.0.0.1', port=5000)
