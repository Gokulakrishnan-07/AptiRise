import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models.user import User
from app.models.game import Collection, Level, Question, QuestionOption, UserProgress
from app.services.auth import create_access_token

client = TestClient(app)


@pytest.fixture
def auth_user():
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == "test_gamer").first()
        if not user:
            user = User(
                username="test_gamer",
                email="gamer@example.com",
                role="user",
                current_level=1,
                total_xp=0,
                is_active=True
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        token = create_access_token({"sub": str(user.id), "role": user.role})
        return user, token
    finally:
        db.close()


@pytest.fixture
def admin_user():
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.role == "admin").first()
        token = create_access_token({"sub": str(admin.id), "role": admin.role})
        return admin, token
    finally:
        db.close()


def test_question_deck_retrieval(auth_user):
    user, token = auth_user
    db = SessionLocal()
    lvl = db.query(Level).filter(Level.level_number == 1).first()
    db.close()

    headers = {"Authorization": f"Bearer {token}"}
    resp = client.get(f"/api/game/level/{lvl.id}/questions", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "questions" in data
    assert len(data["questions"]) > 0
    q1 = data["questions"][0]
    assert "options" in q1
    assert len(q1["options"]) == 4


def test_submit_correct_answer_and_earn_xp(auth_user):
    user, token = auth_user
    db = SessionLocal()
    q = db.query(Question).first()
    correct_opt = db.query(QuestionOption).filter(
        QuestionOption.question_id == q.id,
        QuestionOption.is_correct == True
    ).first()
    db.close()

    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "question_id": q.id,
        "level_id": q.level_id,
        "selected_option_label": correct_opt.option_label,
        "time_taken_seconds": 6.5
    }
    resp = client.post("/api/game/submit-answer", json=payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_correct"] is True
    assert data["xp_earned"] >= 100
    assert data["correct_option_label"] == correct_opt.option_label
    assert "explanation" in data


def test_complete_level_and_unlock_next(auth_user):
    user, token = auth_user
    db = SessionLocal()
    col = db.query(Collection).filter(Collection.slug == "percentage").first()
    lvl1 = db.query(Level).filter(Level.collection_id == col.id, Level.level_number == 1).first()
    lvl2 = db.query(Level).filter(Level.collection_id == col.id, Level.level_number == 2).first()
    db.close()

    headers = {"Authorization": f"Bearer {token}"}
    complete_payload = {
        "level_id": lvl1.id,
        "time_taken_seconds": 120.0,
        "total_score": 500,
        "correct_count": 5,
        "wrong_count": 0
    }
    resp = client.post("/api/game/complete-level", json=complete_payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["level_completed"] is True
    assert data["next_level_unlocked"] is True
    assert data["is_perfect"] is True

    # Verify database progress
    db = SessionLocal()
    prog2 = db.query(UserProgress).filter(
        UserProgress.user_id == user.id,
        UserProgress.level_id == lvl2.id
    ).first()
    assert prog2 is not None
    assert prog2.is_unlocked is True
    db.close()


def test_admin_route_forbidden_for_regular_user(auth_user):
    user, token = auth_user
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.get("/admin", headers=headers)
    assert resp.status_code == 403


def test_admin_route_allowed_for_admin(admin_user):
    admin, token = admin_user
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.get("/admin", headers=headers)
    assert resp.status_code == 200
    assert "Analytics & Operations" in resp.text
