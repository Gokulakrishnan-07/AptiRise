import json
import random
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import settings
from app.models.user import User
from app.models.game import (
    DailyChallenge, DailyChallengeAttempt, Question, QuestionOption, QuestionAttempt
)
from app.services.auth import get_current_user
from app.services.gamification import calculate_user_level, update_user_streak, check_and_award_achievements

from app.templates import render_template

router = APIRouter(tags=["Daily Challenge"])


def get_or_create_daily_challenge(db: Session) -> DailyChallenge:
    today = date.today()
    challenge = db.query(DailyChallenge).filter(DailyChallenge.challenge_date == today).first()
    if challenge:
        return challenge

    # Pick 5 random active questions
    all_q_ids = [q.id for q in db.query(Question.id).filter(Question.is_active == True).all()]
    if not all_q_ids:
        # Fallback if empty database
        selected_ids = []
    else:
        sample_size = min(5, len(all_q_ids))
        selected_ids = random.sample(all_q_ids, sample_size)

    challenge = DailyChallenge(
        challenge_date=today,
        title=f"Daily Aptitude Blitz - {today.strftime('%B %d, %Y')}",
        description="Solve 5 mixed questions across topics to earn +500 Bonus XP and power up your daily streak!",
        question_ids=json.dumps(selected_ids),
        bonus_xp=settings.DAILY_CHALLENGE_BONUS_XP
    )
    db.add(challenge)
    db.commit()
    db.refresh(challenge)
    return challenge


@router.get("/daily-challenge", response_class=HTMLResponse)
async def daily_challenge_page(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    challenge = get_or_create_daily_challenge(db)
    attempt = db.query(DailyChallengeAttempt).filter(
        DailyChallengeAttempt.user_id == current_user.id,
        DailyChallengeAttempt.daily_challenge_id == challenge.id
    ).first()

    is_completed = attempt.is_completed if attempt else False

    return render_template(
        request=request,
        name="daily.html",
        context={
            "user": current_user,
            "challenge": challenge,
            "is_completed": is_completed,
            "attempt": attempt
        }
    )


@router.get("/api/daily-challenge/questions")
async def get_daily_questions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    challenge = get_or_create_daily_challenge(db)
    q_ids = json.loads(challenge.question_ids)

    questions = db.query(Question).filter(Question.id.in_(q_ids)).all()
    # Preserve order
    id_map = {q.id: q for q in questions}
    ordered = [id_map[qid] for qid in q_ids if qid in id_map]

    result = []
    for idx, q in enumerate(ordered):
        opts = db.query(QuestionOption).filter(QuestionOption.question_id == q.id).all()
        opts_sorted = sorted(opts, key=lambda o: o.option_label)
        result.append({
            "id": q.id,
            "collection_id": q.collection.id if q.collection else 0,
            "collection_name": q.collection.name if q.collection else "Aptitude Blitz",
            "level_id": q.level_id,
            "level_number": 0,
            "level_title": "Daily Blitz",
            "question_number": idx + 1,
            "total_questions": len(ordered),
            "question_text": q.question_text,
            "options": [{"label": o.option_label, "text": o.option_text} for o in opts_sorted],
            "difficulty": q.difficulty,
            "time_limit": 40,
            "xp_value": 100
        })

    return {"questions": result, "time_limit_seconds": 40, "bonus_xp": challenge.bonus_xp}


@router.post("/api/daily-challenge/complete")
async def complete_daily_challenge(
    payload: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    challenge = get_or_create_daily_challenge(db)
    correct_count = payload.get("correct_count", 0)
    score = payload.get("score", 0)

    attempt = db.query(DailyChallengeAttempt).filter(
        DailyChallengeAttempt.user_id == current_user.id,
        DailyChallengeAttempt.daily_challenge_id == challenge.id
    ).first()

    bonus_awarded = 0
    if not attempt or not attempt.is_completed:
        bonus_awarded = challenge.bonus_xp
        current_user.total_xp += bonus_awarded
        new_lvl, _, _, _ = calculate_user_level(current_user.total_xp)
        current_user.current_level = new_lvl

        update_user_streak(current_user, db)

        if not attempt:
            attempt = DailyChallengeAttempt(
                user_id=current_user.id,
                daily_challenge_id=challenge.id,
                score=score + bonus_awarded,
                accuracy=(correct_count / 5.0) * 100.0,
                is_completed=True,
                completed_at=datetime.utcnow()
            )
            db.add(attempt)
        else:
            attempt.is_completed = True
            attempt.score = score + bonus_awarded
            attempt.accuracy = (correct_count / 5.0) * 100.0
            attempt.completed_at = datetime.utcnow()

    unlocked = check_and_award_achievements(current_user, db)
    db.commit()

    return {
        "status": "success",
        "bonus_xp": bonus_awarded,
        "total_xp": current_user.total_xp,
        "current_level": current_user.current_level,
        "unlocked_achievements": unlocked
    }
