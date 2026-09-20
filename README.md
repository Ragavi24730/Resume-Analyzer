# AI-Powered Resume Analyzer & Job Recommendation System

A full-stack Python Flask web application designed to parse PDF resumes, detect technical skills, calculate job role alignment using Natural Language Processing (NLP) and Machine Learning (TF-IDF Cosine Similarity), and provide personalized job recommendations.

---

## 🌟 Features

- **User Authentication**: Secure user registration, login, session management, and Werkzeug password hashing.
- **Resume Upload & Parsing**: PDF text extraction using PyPDF2 with 5 MB file validation and secure filename generation.
- **Skill Detection Engine**: Pattern-based technical skill extraction using regular expressions and word boundary matching across 30+ core languages, frameworks, and cloud technologies.
- **Hybrid Job Matching Algorithm**:
  - **70% Skill Overlap**: Exact match count between candidate skills and job requirements.
  - **30% TF-IDF Text Similarity**: Scikit-learn cosine similarity measuring text context fit between resume and job description.
- **Interactive Results Page**: Progress bar score displays, detected skill tags, matched skills (green badges), missing skill gaps (red badges), and ranked recommended jobs.
- **Personalized Dashboard**: User metrics (Resumes Analyzed, Total Skills Detected, Jobs Recommended, Average Match Score) and quick actions.
- **Explore Jobs Board**: Live client-side and backend search and filtering across job title, company, location, and key skills.
- **Profile Management**: Profile updating with unique email enforcement.
- **Modern UI Design**: Glassmorphism design system with pink and purple gradient accents, cards, responsive navigation, and mobile support.

---

## 🛠️ Technology Stack

- **Backend**: Python 3, Flask
- **Database**: SQLite (`database.db`)
- **PDF Processing**: PyPDF2
- **Data & ML**: Pandas, Scikit-learn (`TfidfVectorizer`, `cosine_similarity`)
- **Frontend**: HTML5, CSS3 (Vanilla CSS with Custom Variables & Gradients), JavaScript, Jinja2 Templates

---

## 📁 Project Structure

```
python-project/
│
├── app.py                  # Main Flask application & routes
├── database.db             # SQLite database (auto-created on app startup)
├── requirements.txt        # Python package dependencies
├── README.md               # Documentation & setup guide
│
├── data/
│   └── jobs.csv            # Pre-populated dataset of 20+ realistic job listings
│
├── uploads/                # Directory storing uploaded PDF resumes
│
├── static/
│   ├── style.css           # Custom CSS variables, gradient theme & responsive layout
│   └── script.js           # Live search filter, drag-and-drop & file validation
│
└── templates/
    ├── index.html          # Landing page with hero banner & features
    ├── login.html          # User authentication login page
    ├── register.html       # User sign-up page
    ├── dashboard.html      # Analytics overview dashboard
    ├── upload.html         # Resume PDF upload & target role selector
    ├── result.html         # Detailed analysis report & job match recommendations
    ├── jobs.html           # Searchable job board
    └── profile.html        # User profile view and update form
```

---

## 🚀 Installation & Setup

### 1. Prerequisites
Ensure Python 3.9+ is installed on your system.

### 2. Create Virtual Environment (Optional but recommended)
Open terminal/command prompt in the `python-project` directory:

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**Linux / macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

---

## 💻 Running the Application

Execute the following command in the `python-project` directory:

```bash
python app.py
```

Open your browser and navigate to:
```
http://127.0.0.1:5000/
```

*Note: On launch, `app.py` automatically initializes `database.db` and populates the `jobs` table using `data/jobs.csv`.*

---

## 🔬 How Job Matching & TF-IDF Similarity Works

1. **Skill Overlap Score ($S_{skill}$)**:
   $$\text{Skill Score} = \left(\frac{\text{Count of Matched Resume Skills}}{\text{Total Required Job Skills}}\right) \times 100$$

2. **TF-IDF Cosine Similarity ($S_{tfidf}$)**:
   Resume text and job description vectors are generated using `TfidfVectorizer(stop_words='english')`. The cosine similarity angle between the two vectors is calculated:
   $$\text{TF-IDF Score} = \text{CosineSimilarity}(\vec{V}_{resume}, \vec{V}_{job}) \times 100$$

3. **Final Hybrid Match Percentage**:
   $$\text{Final Score} = (0.70 \times S_{skill}) + (0.30 \times S_{tfidf})$$

---

## 🧪 Quick Test Account Instructions

1. Navigate to `http://127.0.0.1:5000/register`
2. Register a new user account (e.g. Name: `Alex Developer`, Email: `alex@example.com`, Password: `password123`).
3. Login and click **Upload Resume**.
4. Select target role **Python Developer** and upload any sample PDF resume containing keywords like `Python`, `Flask`, `SQL`, `Git`.
5. Review the overall match percentage, matched skills, missing skills, and top job recommendations!
