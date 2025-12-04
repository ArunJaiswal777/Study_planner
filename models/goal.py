from database import db

class StudyGoal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False
    )
    exam_date = db.Column(db.Date, nullable=False)
    total_required_minutes = db.Column(db.Integer, nullable=False)
    recommended_daily_minutes = db.Column(db.Integer, nullable=False)
