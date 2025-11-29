from flask import Flask, render_template, request
from database import db

app = Flask(__name__)

# Database config
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///study.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize DB
db.init_app(app)

# -------------------------------
# IMPORT MODELS AFTER db.init_app
# -------------------------------
from models.user import User
from models.subject import Subject
from models.session import StudySession


# ---------------- HOME ----------------
@app.route("/")
def home():
    return render_template("home.html")


# ---------------- SUBJECT PAGE ----------------
@app.route("/subject")
def subject_page():
    return render_template("subject.html")


@app.route("/add_subject", methods=["POST"])
def add_subject():
    name = request.form.get("name")
    difficulty = request.form.get("difficulty")

    new_subject = Subject(name=name, difficulty=difficulty)
    db.session.add(new_subject)
    db.session.commit()

    return "Subject Added Successfully"


# ---------------- SESSION PAGE ----------------
@app.route("/session")
def session_page():
    return render_template("session.html")


@app.route("/add_session", methods=["POST"])
def add_session():
    subject_id = request.form.get("subject_id")
    duration = request.form.get("duration")

    new_session = StudySession(subject_id=subject_id, duration=duration)
    db.session.add(new_session)
    db.session.commit()

    return "Session Added Successfully"


# ---------------- SUMMARY PAGE ----------------
@app.route("/summary")
def summary():
    subjects = Subject.query.all()
    sessions = StudySession.query.all()

    # Join session with subject name
    detailed_sessions = []
    for s in sessions:
        subject = Subject.query.get(s.subject_id)
        detailed_sessions.append({
            "subject_name": subject.name,
            "duration": s.duration
        })

    total_time = sum([s["duration"] for s in detailed_sessions])

    return render_template(
        "summary.html",
        subjects=subjects,
        sessions=detailed_sessions,
        total_time=total_time
    )


# ---------------- RUN APP ----------------
if __name__ == "__main__":
    with app.app_context():
        db.create_all()     # Creates tables cleanly
    app.run(debug=True)

