from database import db
from datetime import date

class StudySession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    duration = db.Column(db.Integer, nullable=False)
    date = db.Column(db.Date, default=date.today, nullable=False)
