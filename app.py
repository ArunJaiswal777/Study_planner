from flask import Flask, render_template
from database import db

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///study.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

# import models AFTER db.init_app(app)
from models.user import User
from models.subject import Subject
from models.session import StudySession

@app.route("/")
def home():
    return render_template("home.html")

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
