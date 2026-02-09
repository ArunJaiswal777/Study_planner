from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash
)
from functools import wraps
from datetime import datetime, date, timedelta
import re
import requests

from database import db
from models.user import User
from models.subject import Subject
from models.session import StudySession
from models.goal import StudyGoal   # ⭐ NEW: study goal model


# -------------------------------------------------
# APP SETUP
# -------------------------------------------------
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///study.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.secret_key = "super-secret-key"   # you can change this

db.init_app(app)


# -------------------------------------------------
# HELPERS
# -------------------------------------------------
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper


def calculate_study_goal(user_subjects, exam_date):
    """
    Simple AI-ish rule-based logic.
    Later we can replace this with ML easily.
    """
    difficulty_hours = {
        "Easy": 20,
        "Medium": 35,
        "Hard": 50
    }

    total_hours = 0
    for s in user_subjects:
        total_hours += difficulty_hours.get(s.difficulty, 20)

    total_minutes = total_hours * 60

    days_left = (exam_date - date.today()).days
    if days_left <= 0:
        days_left = 1

    recommended_daily_minutes = round(total_minutes / days_left)

    return total_minutes, recommended_daily_minutes


# -------------------------------------------------
# HOME / AUTH
# -------------------------------------------------
@app.route("/")
@login_required
def home():
    # send logged-in users straight to dashboard
    return redirect(url_for("dashboard"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        # Username taken?
        existing = User.query.filter_by(username=username).first()
        if existing:
            flash("Username already exists. Please choose another.", "error")
            return render_template("register.html", username=username, email=email)

        # Password rules
        if len(password) < 8 \
           or not re.search(r"[A-Z]", password) \
           or not re.search(r"[a-z]", password) \
           or not re.search(r"\d", password):
            flash(
                "Password must be at least 8 characters and include "
                "one uppercase, one lowercase letter, and one number.",
                "error"
            )
            return render_template("register.html", username=username, email=email)

        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return render_template("register.html", username=username, email=email)

        # Create user
        new_user = User(username=username, email=email)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        session["user_id"] = new_user.id
        flash("Registration successful! 🎉", "success")
        return redirect(url_for("dashboard"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session["user_id"] = user.id
            flash("Logged in successfully!", "success")
            return redirect(url_for("dashboard"))

        flash("Invalid username or password.", "error")
        return render_template("login.html", username=username)

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


# -------------------------------------------------
# DASHBOARD + AI STUDY GOAL
# -------------------------------------------------
@app.route("/dashboard")
@login_required
def dashboard():
    user_id = session["user_id"]
    user = User.query.get_or_404(user_id)

    subjects = Subject.query.filter_by(user_id=user_id).all()
    sessions = StudySession.query.filter_by(user_id=user_id).order_by(StudySession.date.desc()).all()

    total_subjects = len(subjects)
    total_sessions = len(sessions)
    total_minutes = sum(s.duration for s in sessions)

    goal = StudyGoal.query.filter_by(user_id=user_id).first()

    progress_percent = None
    if goal and goal.total_required_minutes > 0:
        progress_percent = round(
            (total_minutes / goal.total_required_minutes) * 100,
            1
        )

    return render_template(
        "dashboard.html",
        username=user.username,
        total_subjects=total_subjects,
        total_sessions=total_sessions,
        total_minutes=total_minutes,
        goal=goal,
        progress_percent=progress_percent
    )


@app.route("/set_goal", methods=["GET", "POST"])
@login_required
def set_goal():
    user_id = session["user_id"]
    user_subjects = Subject.query.filter_by(user_id=user_id).all()

    if request.method == "POST":
        date_value = request.form.get("exam_date")
        try:
            exam_date = datetime.strptime(date_value, "%Y-%m-%d").date()
        except (TypeError, ValueError):
            flash("Invalid date.", "error")
            return render_template("set_goal.html", subjects=user_subjects)

        if not user_subjects:
            flash("Add at least one subject before setting a goal.", "error")
            return render_template("set_goal.html", subjects=user_subjects)

        total_minutes, daily_mins = calculate_study_goal(user_subjects, exam_date)

        existing = StudyGoal.query.filter_by(user_id=user_id).first()
        if existing:
            existing.exam_date = exam_date
            existing.total_required_minutes = total_minutes
            existing.recommended_daily_minutes = daily_mins
        else:
            new_goal = StudyGoal(
                user_id=user_id,
                exam_date=exam_date,
                total_required_minutes=total_minutes,
                recommended_daily_minutes=daily_mins
            )
            db.session.add(new_goal)

        db.session.commit()
        flash("AI study goal updated ✅", "success")
        return redirect(url_for("dashboard"))

    return render_template("set_goal.html", subjects=user_subjects)


# -------------------------------------------------
# USER PROFILE
# -------------------------------------------------
@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    user = User.query.get_or_404(session["user_id"])

    if request.method == "POST":
        new_username = request.form.get("username", "").strip()
        new_email = request.form.get("email", "").strip()

        # simple validations
        if not new_username:
            flash("Username cannot be empty.", "error")
            return render_template("profile.html", user=user)

        # check for username conflict
        other = User.query.filter(
            User.username == new_username,
            User.id != user.id
        ).first()
        if other:
            flash("That username is already taken.", "error")
            return render_template("profile.html", user=user)

        user.username = new_username
        user.email = new_email
        db.session.commit()

        flash("Profile updated successfully.", "success")
        return redirect(url_for("profile"))

    return render_template("profile.html", user=user)


# -------------------------------------------------
# SUBJECTS
# -------------------------------------------------
@app.route("/subject")
@login_required
def subject_page():
    user_subjects = Subject.query.filter_by(user_id=session["user_id"]).all()
    return render_template("subject.html", subjects=user_subjects)


@app.route("/add_subject", methods=["GET", "POST"])
@login_required
def add_subject():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        difficulty = request.form.get("difficulty", "Easy")

        if not name:
            flash("Subject name cannot be empty.", "error")
            return render_template("add_subject.html")

        new_subject = Subject(
            name=name,
            difficulty=difficulty,
            user_id=session["user_id"]
        )
        db.session.add(new_subject)
        db.session.commit()

        flash("Subject added successfully.", "success")
        return redirect(url_for("subject_page"))

    return render_template("add_subject.html")


@app.route("/edit_subject/<int:sid>", methods=["GET", "POST"])
@login_required
def edit_subject(sid):
    subject = Subject.query.filter_by(
        id=sid,
        user_id=session["user_id"]
    ).first_or_404()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        difficulty = request.form.get("difficulty", "Easy")

        if not name:
            flash("Subject name cannot be empty.", "error")
            return render_template("edit_subject.html", subject=subject)

        subject.name = name
        subject.difficulty = difficulty
        db.session.commit()

        flash("Subject updated.", "success")
        return redirect(url_for("subject_page"))

    return render_template("edit_subject.html", subject=subject)


@app.route("/delete_subject/<int:sid>")
@login_required
def delete_subject(sid):
    subject = Subject.query.filter_by(
        id=sid,
        user_id=session["user_id"]
    ).first_or_404()

    db.session.delete(subject)
    db.session.commit()
    flash("Subject deleted.", "info")
    return redirect(url_for("subject_page"))


# -------------------------------------------------
# STUDY SESSIONS
# -------------------------------------------------
@app.route("/session")
@login_required
def session_page():
    user_id = session["user_id"]
    sessions = (
        db.session.query(StudySession, Subject)
        .join(Subject, StudySession.subject_id == Subject.id)
        .filter(StudySession.user_id == user_id)
        .order_by(StudySession.date.desc())
        .all()
    )
    subjects = Subject.query.filter_by(user_id=user_id).all()
    # we can pass subjects if you want to show names in the table
    return render_template("session.html", sessions=sessions, subjects=subjects)


@app.route("/add_session", methods=["GET", "POST"])
@login_required
def add_session():
    user_id = session["user_id"]
    subjects = Subject.query.filter_by(user_id=user_id).all()

    if request.method == "POST":
        subject_id = request.form.get("subject_id")
        duration = request.form.get("duration")
        date_value = request.form.get("date")

        try:
            duration_int = int(duration)
        except (TypeError, ValueError):
            flash("Duration must be a number.", "error")
            return render_template("session.html", subjects=subjects)

        try:
            date_obj = datetime.strptime(date_value, "%Y-%m-%d").date()
        except (TypeError, ValueError):
            flash("Invalid date.", "error")
            return render_template("session.html", subjects=subjects)

        new_session = StudySession(
            user_id=user_id,
            subject_id=subject_id,
            duration=duration_int,
            date=date_obj
        )
        db.session.add(new_session)
        db.session.commit()

        flash("Study session added.", "success")
        return redirect(url_for("session_page"))

    # GET
    today = date.today()
    return render_template("add_session.html", subjects=subjects, today=today)


@app.route("/edit_session/<int:sid>", methods=["GET", "POST"])
@login_required
def edit_session(sid):
    user_id = session["user_id"]
    session_obj = StudySession.query.filter_by(
        id=sid,
        user_id=user_id
    ).first_or_404()

    subjects = Subject.query.filter_by(user_id=user_id).all()

    if request.method == "POST":
        subject_id = request.form.get("subject_id")
        duration = request.form.get("duration")
        date_value = request.form.get("date")

        try:
            duration_int = int(duration)
        except (TypeError, ValueError):
            flash("Duration must be a number.", "error")
            return render_template("edit_session.html",
                                   session=session_obj,
                                   subjects=subjects)

        try:
            date_obj = datetime.strptime(date_value, "%Y-%m-%d").date()
        except (TypeError, ValueError):
            flash("Invalid date.", "error")
            return render_template("edit_session.html",
                                   session=session_obj,
                                   subjects=subjects)

        session_obj.subject_id = subject_id
        session_obj.duration = duration_int
        session_obj.date = date_obj
        db.session.commit()

        flash("Session updated.", "success")
        return redirect(url_for("session_page"))

    return render_template("edit_session.html",
                           study_session=session_obj,
                           subjects=subjects)


@app.route("/delete_session/<int:sid>")
@login_required
def delete_session(sid):
    user_id = session["user_id"]
    session_obj = StudySession.query.filter_by(
        id=sid,
        user_id=user_id
    ).first_or_404()

    db.session.delete(session_obj)
    db.session.commit()
    flash("Session deleted.", "info")
    return redirect(url_for("session_page"))


# -------------------------------------------------
# SUMMARY
# -------------------------------------------------
@app.route("/summary")
@login_required
def summary():
    user_id = session["user_id"]

    subjects = Subject.query.filter_by(user_id=user_id).all()
    sessions = StudySession.query.filter_by(user_id=user_id).all()

    detailed_sessions = []
    subject_breakdown = {}
    
    for s in sessions:
        subject = Subject.query.get(s.subject_id)
        name = subject.name if subject else "Unknown"
        
        # List Details
        detailed_sessions.append({
            "subject_name": name,
            "duration": s.duration
        })
        
        # Aggregation
        if name in subject_breakdown:
            subject_breakdown[name] += s.duration
        else:
            subject_breakdown[name] = s.duration

    total_time = sum(s.duration for s in sessions)

    return render_template(
        "summary.html",
        subjects=subjects,
        sessions=detailed_sessions,
        total_minutes=total_time,
        subject_breakdown=subject_breakdown
    )


@app.route("/assistant")
@login_required
def assistant():
    # Pass 'session' to template by default in Flask, 
    # but explicitly ensuring user context is fine too.
    return render_template("assistant.html")


@app.route("/api/chat", methods=["POST"])
@login_required
def api_chat():
    data = request.json
    user_message = data.get("message", "")
    api_key = data.get("api_key", "")

    if not api_key:
        return {"reply": "Please provide a valid API Key."}
    
    # Call Groq API
    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": "You are a helpful AI study assistant. Help the user with their study plans, subjects, and timetables. Keep answers concise and motivating."},
                {"role": "user", "content": user_message}
            ]
        }
        
        response = requests.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers)
        
        if response.status_code == 200:
            result = response.json()
            reply = result["choices"][0]["message"]["content"]
        else:
            reply = f"Error from AI provider: {response.text}"
            
    except Exception as e:
        reply = f"An error occurred: {str(e)}"
        
    return {"reply": reply}


# -------------------------------------------------
# TIMETABLE
# -------------------------------------------------
def generate_algorithm(user_id, daily_minutes):
    """
    Rule-based generator for study timetable.
    """
    subjects = Subject.query.filter_by(user_id=user_id).all()
    sessions = StudySession.query.filter_by(user_id=user_id).all()
    goal = StudyGoal.query.filter_by(user_id=user_id).first()

    # 1. Configuration
    # ALIGNMENT: Match the heavy weights from calculate_study_goal
    # Easy=20h, Medium=35h, Hard=50h
    weights = {"Easy": 20, "Medium": 35, "Hard": 50}
    base_minutes = 60 # Convert hours to minutes
    
    # Defaults
    days_to_plan = 7
    if goal:
        days_left = (goal.exam_date - date.today()).days
        if days_left > 0:
            # Plan for the realistic remaining time, up to 30 days for display
            days_to_plan = min(days_left, 30) 

    # 2. Calculate State per Subject
    subject_data = []
    total_remaining_work = 0
    
    for s in subjects:
        # Calculate requirement in minutes based on difficulty
        req = weights.get(s.difficulty, 20) * base_minutes
        studied = sum(sess.duration for sess in sessions if sess.subject_id == s.id)
        rem = max(0, req - studied)
        
        subject_data.append({
            "id": s.id,
            "name": s.name,
            "difficulty": s.difficulty,
            "remaining": rem
        })
        total_remaining_work += rem
        
    # 3. Generate Daily Plan
    schedule = []
    insight = "You are on track! Keep it up."
    
    if total_remaining_work > (daily_minutes * days_to_plan):
        insight = "You are behind schedule. Consider increasing your daily study time or focusing on Hard subjects."
    
    # We will simulate the days
    # To rotate, we shuffle or just iterate cyclically
    # Let's filter only subjects that need work
    active_subjects = [s for s in subject_data if s["remaining"] > 0]
    
    import random
    # We sort them by difficulty desc initially to prioritize hard ones? 
    # Or just keep order. Let's keep order.
    
    if not active_subjects:
         return [], "All subjects completed based on base requirements!"

    current_idx = 0
    
    for day_num in range(1, days_to_plan + 1):
        # Every 7th day is Revision
        if day_num % 7 == 0:
            schedule.append({
                "day": day_num,
                "type": "Revision",
                "subjects": [],
                "note": "Review notes and flashcards for all subjects."
            })
            continue

        # Valid Study Day
        # Pick 2 subjects to focus on (Rotation)
        day_subjects = []
        
        # We try to fill 'daily_minutes'
        time_filled = 0
        
        # Strategy: Pick 2 distinct subjects from the list cyclically
        # We use a while loop to fill time? No, simpler to just pick 2.
        
        todays_picks = []
        for _ in range(2): # Pick 2
             subj = active_subjects[current_idx % len(active_subjects)]
             if subj not in todays_picks:
                 todays_picks.append(subj)
             current_idx += 1
        
        # Allocate time proportionally between these 2
        subset_rem = sum(p["remaining"] for p in todays_picks)
        
        allocated_today = 0
        for i, s in enumerate(todays_picks):
            # If it's the last one, give remainder of daily_minutes
            if i == len(todays_picks) - 1:
                mins = daily_minutes - allocated_today
            else:
                # Proportional to remaining
                if subset_rem > 0:
                    ratio = s["remaining"] / subset_rem
                    mins = int(daily_minutes * ratio)
                else:
                    mins = int(daily_minutes / len(todays_picks))
            
            # Sanity check
            if mins <= 5: mins = 15 # Minimum meaningful slot
            
            day_subjects.append({
                "name": s["name"],
                "time": mins,
                "difficulty": s["difficulty"]
            })
            
            # Update simulation state (so future days see less remaining)
            # Find the actual object in active_subjects to mutate
            for original in active_subjects:
                if original["id"] == s["id"]:
                    original["remaining"] = max(0, original["remaining"] - mins)
            
            allocated_today += mins
            
        schedule.append({
            "day": day_num,
            "type": "Study",
            "subjects": day_subjects
        })
        
    return schedule, insight


@app.route("/timetable", methods=["GET", "POST"])
@login_required
def timetable():
    default_daily = 120 # 2 hours
    
    if request.method == "POST":
        try:
            default_daily = int(request.form.get("daily_time", 120))
        except ValueError:
            pass
    
    schedule_data, insight = generate_algorithm(session["user_id"], default_daily)
    
    return render_template(
        "timetable.html", 
        schedule=schedule_data, 
        insight=insight,
        daily_minutes=default_daily
    )


# -------------------------------------------------
# MAIN
# -------------------------------------------------
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
