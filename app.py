from flask import Flask, render_template, request
from database import db
from flask import request

# import models AFTER db.init_app(app)
from models.user import User
from models.subject import Subject
from models.session import StudySession

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///study.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/subject")
def subject():
    return render_template("subject.html")

@app.route("/session")
def session():
    return render_template("session.html")

# @app.route("/summary")
# def summary():
#     return render_template("summary.html")


@app.route("/add_subject", methods=["POST"])
def add_subject():
    name = request.form.get("name")
    
    #Create new subject
    new_subject = Subject(name=name)

    #save to database
    db.session.add(new_subject)
    db.session.commit()

    return "Subject Added Successfully"


@app.route("/add_session", methods=["POST"])
def add_session():
    subject_id = request.form.get("subject_id")
    duration = request.form.get("duration")

    #crate new session
    new_session = StudySession(subject_id=subject_id, duration=duration)

    #add to database
    db.session.add(new_session)
    db.session.commit()

    return "Session Added Successfully"


@app.route("/summary")
def summary():
    # get all subjects
    subjects = Subject.query.all()

    # get all sessions
    sessions = StudySession.query.all()

    # calculate total time
    total_time = sum(s.duration for s in sessions)

    return render_template(
        "summary.html",
        subjects=subjects,
        sessions=sessions,
        total_time=total_time
    )



if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
