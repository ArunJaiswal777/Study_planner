from flask import Flask, render_template, request, redirect, url_for, session
from database import db

app = Flask(__name__)

# ---------------- CONFIG ----------------
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///study.db"   # PostgreSQL me 1 line change
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.secret_key = "supersecretkey"   # dev key

db.init_app(app)

# ---------------- IMPORT MODELS ----------------
from models.user import User
from models.subject import Subject
from models.session import StudySession


# ------------ LOGIN REQUIRED DECORATOR ---------
def login_required(func):
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return func(*args, **kwargs)
    wrapper.__name__ = func.__name__
    return wrapper


# ------------------- AUTH ----------------------

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        # ---- PASSWORD VALIDATION ----
        if len(password) < 8:
            return render_template("register.html", error="Password must be at least 8 characters long!")

        if not any(ch.isupper() for ch in password):
            return render_template("register.html", error="Password must contain at least one uppercase letter (A-Z)!")

        if not any(ch.islower() for ch in password):
            return render_template("register.html", error="Password must contain at least one lowercase letter (a-z)!")

        if not any(ch.isdigit() for ch in password):
            return render_template("register.html", error="Password must contain at least one number (0-9)!")

        # check existing user
        existing = User.query.filter_by(username=username).first()
        if existing:
            return render_template("register.html", error="Username already exists!")

        # create new user
        new_user = User(username=username)
        new_user.set_password(password)

        db.session.add(new_user)
        db.session.commit()

        return "Registration successful! <a href='/login'>Login here</a>"

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            session["user_id"] = user.id
            return redirect(url_for("home"))

        return render_template("login.html", error="Invalid username or password!")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.pop("user_id", None)
    return redirect(url_for("login"))


# ------------------- HOME ----------------------

@app.route("/")
@login_required
def home():
    return render_template("home.html")


# ------------------- SUBJECT -------------------

@app.route("/subject")
@login_required
def subject_page():
    user_subjects = Subject.query.filter_by(user_id=session["user_id"]).all()
    return render_template("subject.html", subjects=user_subjects)


@app.route("/add_subject", methods=["POST"])
@login_required
def add_subject():
    name = request.form.get("name")
    difficulty = request.form.get("difficulty")

    new_subject = Subject(
        name=name,
        difficulty=difficulty,
        user_id=session["user_id"]
    )

    db.session.add(new_subject)
    db.session.commit()

    return redirect(url_for("subject_page"))


# ------------------- SESSION -------------------

@app.route("/session")
@login_required
def session_page():
    subjects = Subject.query.filter_by(user_id=session["user_id"]).all()
    return render_template("session.html", subjects=subjects)


@app.route("/add_session", methods=["POST"])
@login_required
def add_session():
    subject_id = request.form.get("subject_id")
    duration = int(request.form.get("duration"))

    new_session = StudySession(
        subject_id=subject_id,
        duration=duration,
        user_id=session["user_id"]
    )

    db.session.add(new_session)
    db.session.commit()

    return redirect(url_for("session_page"))


# ------------------- SUMMARY -------------------

@app.route("/summary")
@login_required
def summary():
    subjects = Subject.query.filter_by(user_id=session["user_id"]).all()
    sessions = StudySession.query.filter_by(user_id=session["user_id"]).all()

    detailed_sessions = []
    for s in sessions:
        subject = Subject.query.get(s.subject_id)
        if subject:
            detailed_sessions.append({
                "subject_name": subject.name,
                "duration": s.duration
            })

    total_time = sum(s["duration"] for s in detailed_sessions)

    return render_template(
        "summary.html",
        subjects=subjects,
        sessions=detailed_sessions,
        total_time=total_time
    )


# ------------------- RUN APP -------------------

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
