# 📚 AI-Powered Study Planner

A full-stack web application built with **Flask** and **SQLAlchemy** that helps students plan, track, and stay consistent with their exam preparation. It combines manual study tracking (subjects, sessions, streaks) with AI-assisted features (auto-generated timetables and an in-app study assistant chatbot).

---

## ✨ Features

- **User Authentication** — Secure register/login/logout with hashed passwords (Werkzeug) and session-based auth.
- **Subject Management** — Add, edit, and delete subjects with a difficulty rating (Easy / Medium / Hard).
- **Study Session Logging** — Log daily study sessions per subject with duration and date.
- **Dashboard** — At-a-glance view of total subjects, sessions, total study time, goal progress, and streaks.
- **Study Streak Tracker** — Calculates current and longest streaks (a day counts once you've logged ≥30 minutes total), with a calendar-style streak history view.
- **AI Study Goal** — Rule-based engine that estimates total study hours needed (based on subject difficulty) and calculates a daily minutes target from your exam date.
- **AI-Generated Timetable** — Builds a day-by-day study schedule, rotating between subjects proportionally to time remaining, with automatic revision days every 7th day.
- **AI Study Assistant** — In-app chatbot (powered by the Groq API, `llama-3.3-70b-versatile`) for study-related questions and motivation.
- **Summary View** — Breakdown of total time studied per subject.
- **Profile Management** — Update username and email.

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python, Flask |
| Database | SQLite |
| ORM | SQLAlchemy (via Flask-SQLAlchemy) |
| Auth | Flask sessions, Werkzeug password hashing |
| Templating | Jinja2 |
| Frontend | HTML, CSS |
| AI Integration | Groq API (LLM chat completions) |

---

## 📂 Project Structure

```
study_planner/
├── app.py                  # Main Flask app — all routes & core logic
├── database.py              # SQLAlchemy instance (db = SQLAlchemy())
├── verify_streak.py         # Standalone test script for streak calculation logic
├── models/
│   ├── user.py                # User model (auth, password hashing)
│   ├── subject.py             # Subject model (name, difficulty)
│   ├── session.py             # StudySession model (duration, date)
│   └── goal.py                 # StudyGoal model (exam date, required/daily minutes)
├── templates/                # Jinja2 HTML templates (dashboard, login, timetable, etc.)
├── static/                    # CSS stylesheets
└── instance/
    └── study.db                # SQLite database file (auto-created)
```

---

## 🗄️ Data Model

- **User** `1 → many` **Subject**
- **User** `1 → many` **StudySession**
- **Subject** `1 → many` **StudySession**
- **User** `1 → 1` **StudyGoal**

All child tables reference `user.id` as a foreign key, so every subject, session, and goal is scoped to the logged-in user.

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- pip

### Installation

```bash
# Clone the repository
git clone <your-repo-url>
cd study_planner

# Install dependencies
pip install flask flask-sqlalchemy requests

# Run the app
python app.py
```

The app will be available at `http://127.0.0.1:5000`. The SQLite database (`study.db`) is created automatically on first run.

### Using the AI Assistant
The AI chat feature (`/assistant`) requires a [Groq API key](https://console.groq.com/), which you enter directly in the app — it's sent per-request and not stored server-side.

---

## 🧪 Testing

`verify_streak.py` contains a standalone script that seeds test data and verifies the streak calculation logic (current streak, longest streak, and the 30-minute daily threshold) against several scenarios:

```bash
python verify_streak.py
```

---

## 🔒 Security Notes

- Passwords are never stored in plain text — only hashed via `werkzeug.security`.
- `app.secret_key` is hardcoded for local development. **Set this via an environment variable before deploying to production.**

---

## 📌 Roadmap Ideas

- Migrate `secret_key` and Groq API key handling to environment variables
- Add database migrations (Flask-Migrate)
- Move from SQLite to PostgreSQL for production
- Add automated tests (pytest) beyond `verify_streak.py`
