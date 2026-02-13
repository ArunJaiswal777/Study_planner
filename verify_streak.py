
import os
from datetime import date, timedelta
from app import app, db, User, StudySession, calculate_streak

def setup_test_data():
    with app.app_context():
        # Create a test user
        user = User.query.filter_by(username="test_streak_user").first()
        if user:
            # Clean up existing sessions
            StudySession.query.filter_by(user_id=user.id).delete()
            db.session.delete(user)
            db.session.commit()
        
        user = User(username="test_streak_user", email="test@example.com")
        user.set_password("password")
        db.session.add(user)
        db.session.commit()
        
        print(f"Created test user: {user.id}")
        return user.id

def test_streak_logic():
    user_id = setup_test_data()
    today = date.today()
    
    with app.app_context():
        # Case 1: No sessions
        c, l = calculate_streak(user_id)
        print(f"Case 1 (No sessions): Current={c}, Longest={l} [Expected: 0, 0]")
        assert c == 0 and l == 0
        
        # Case 2: One day 35 mins (Today)
        s1 = StudySession(user_id=user_id, subject_id=1, duration=35, date=today)
        db.session.add(s1)
        db.session.commit()
        c, l = calculate_streak(user_id)
        print(f"Case 2 (Today 35m): Current={c}, Longest={l} [Expected: 1, 1]")
        assert c == 1 and l == 1
        
        # Case 3: Yesterday 30 mins (Consecutive)
        yesterday = today - timedelta(days=1)
        s2 = StudySession(user_id=user_id, subject_id=1, duration=30, date=yesterday)
        db.session.add(s2)
        db.session.commit()
        c, l = calculate_streak(user_id)
        print(f"Case 3 (Today+Yesterday): Current={c}, Longest={l} [Expected: 2, 2]")
        assert c == 2 and l == 2
        
        # Case 4: Break (Gap of 1 day) -> 3 days ago. 
        # So we have Today(0), Yesterday(-1). Gap(-2). Day(-3).
        day_minus_3 = today - timedelta(days=3)
        s3 = StudySession(user_id=user_id, subject_id=1, duration=40, date=day_minus_3)
        db.session.add(s3)
        db.session.commit()
        
        c, l = calculate_streak(user_id)
        # Current streak is 2 (Today, Yesterday). 
        # Longest streak is 2. (Today, Yesterday) or just (Day-3) which is 1.
        # Wait, Day-3 is isolated. 
        # So we have: Day-3 (1 day), ... Gap ..., Yesterday, Today (2 days).
        # Expected: Current=2, Longest=2.
        print(f"Case 4 (Gap): Current={c}, Longest={l} [Expected: 2, 2]")
        assert c == 2 and l == 2
        
        # Case 5: Extend longest streak in the past
        # Add Day-4, Day-5, Day-6 (all consecutive with Day-3)
        # Sequence: Day-6, Day-5, Day-4, Day-3. (4 days)
        # Gap
        # Yesterday, Today (2 days)
        # Current = 2. Longest = 4.
        
        days_past = [today - timedelta(days=i) for i in range(4, 7)] # 4,5,6
        for d in days_past:
             db.session.add(StudySession(user_id=user_id, subject_id=1, duration=50, date=d))
        db.session.commit()
        
        c, l = calculate_streak(user_id)
        print(f"Case 5 (Longest in past): Current={c}, Longest={l} [Expected: 2, 4]")
        assert c == 2 and l == 4
        
        # Case 6: Threshold check
        # Add session for Day-8 with only 20 mins. Should NOT count.
        day_minus_8 = today - timedelta(days=8)
        db.session.add(StudySession(user_id=user_id, subject_id=1, duration=20, date=day_minus_8))
        db.session.commit()
        
        c, l = calculate_streak(user_id)
        # Should be same as before
        print(f"Case 6 (Threshold <30): Current={c}, Longest={l} [Expected: 2, 4]")
        assert c == 2 and l == 4
        
        # Add another 15 mins to Day-8 (Total 35). Should now count as a valid day (streak of 1).
        db.session.add(StudySession(user_id=user_id, subject_id=1, duration=15, date=day_minus_8))
        db.session.commit()
        
        c, l = calculate_streak(user_id)
        print(f"Case 7 (Threshold met via sum): Current={c}, Longest={l} [Expected: 2, 4]")
        # Longest is still 4. Current is still 2. The new day is isolated.
        assert c == 2 and l == 4
        
        print("\nALL TESTS PASSED ✅")

if __name__ == "__main__":
    test_streak_logic()
