import os
import unittest
import io
from app import app, init_db, get_db, DATABASE_PATH, detect_skills, extract_text_from_pdf

class FlaskAppTestCase(unittest.TestCase):

    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()

    def test_01_database_seeding(self):
        """Verifies database initialization and jobs seeding."""
        with app.app_context():
            db = get_db()
            cursor = db.cursor()
            cursor.execute("SELECT COUNT(*) FROM jobs")
            count = cursor.fetchone()[0]
            self.assertGreaterEqual(count, 20, "Jobs table should contain at least 20 sample job listings.")

    def test_02_skill_detection(self):
        """Verifies regex skill detection logic."""
        text = "Experienced in Python, Flask, SQL, REST API, HTML, CSS, JavaScript, and Docker."
        skills = detect_skills(text)
        expected = ["Python", "Flask", "SQL", "REST API", "HTML", "CSS", "JavaScript", "Docker"]
        for exp in expected:
            self.assertIn(exp, skills, f"Skill {exp} should be detected.")

    def test_03_user_registration_and_login(self):
        """Verifies user registration and login session flow."""
        # 1. Register User
        res_reg = self.client.post('/register', data={
            'name': 'Test Engineer',
            'email': 'test@example.com',
            'password': 'password123',
            'confirm_password': 'password123'
        }, follow_redirects=True)
        self.assertIn(b'Registration successful', res_reg.data)

        # 2. Login User
        res_login = self.client.post('/login', data={
            'email': 'test@example.com',
            'password': 'password123'
        }, follow_redirects=True)
        self.assertIn(b'Welcome back, Test Engineer!', res_login.data)

    def test_04_resume_upload_and_analysis(self):
        """Verifies resume PDF upload, extraction, matching, and result viewing."""
        # First login
        self.client.post('/login', data={
            'email': 'test@example.com',
            'password': 'password123'
        }, follow_redirects=True)

        sample_pdf_path = os.path.join(os.path.dirname(__file__), "sample_resume.pdf")
        with open(sample_pdf_path, 'rb') as f:
            pdf_bytes = f.read()

        data = {
            'target_role_select': 'Python Developer',
            'resume': (io.BytesIO(pdf_bytes), 'sample_resume.pdf')
        }

        res_upload = self.client.post('/upload', data=data, content_type='multipart/form-data', follow_redirects=True)
        self.assertIn(b'Resume Analysis Result', res_upload.data)
        self.assertIn(b'Python Developer', res_upload.data)
        self.assertIn(b'Extracted Skills', res_upload.data)

    def test_05_jobs_page_search(self):
        """Verifies job board search filter."""
        res_jobs = self.client.get('/jobs?q=Python')
        self.assertEqual(res_jobs.status_code, 200)
        self.assertIn(b'Python Developer', res_jobs.data)

    def test_06_profile_update(self):
        """Verifies profile detail update."""
        self.client.post('/login', data={
            'email': 'test@example.com',
            'password': 'password123'
        }, follow_redirects=True)

        res_prof = self.client.post('/profile', data={
            'name': 'Test Engineer Updated',
            'email': 'test_updated@example.com'
        }, follow_redirects=True)
        self.assertIn(b'Profile updated successfully!', res_prof.data)

if __name__ == '__main__':
    unittest.main()
