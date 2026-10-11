from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.database import get_db
from app.models.user import User
from app.models.game import (
    QuestionAttempt, UserProgress, UserTopicProgress,
    Collection, Level, UserAchievement, Achievement
)
from app.schemas.user import UserProfileUpdate
from app.services.auth import get_current_user
from app.services.gamification import calculate_user_level

from app.templates import render_template

router = APIRouter(tags=["Profile"])


@router.get("/profile", response_class=HTMLResponse)
async def profile_page(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    level_num, progress_pct, xp_in_level, xp_needed = calculate_user_level(current_user.total_xp)

    # Attempts metrics
    total_attempts = db.query(func.count(QuestionAttempt.id)).filter(
        QuestionAttempt.user_id == current_user.id
    ).scalar() or 0

    correct_attempts = db.query(func.count(QuestionAttempt.id)).filter(
        QuestionAttempt.user_id == current_user.id,
        QuestionAttempt.is_correct == True
    ).scalar() or 0

    accuracy = round((correct_attempts / total_attempts * 100), 1) if total_attempts > 0 else 0.0

    # Topic breakdowns
    topic_progress_list = db.query(UserTopicProgress).filter(
        UserTopicProgress.user_id == current_user.id
    ).all()

    topics = []
    for tp in topic_progress_list:
        topics.append({
            "name": tp.collection.name,
            "slug": tp.collection.slug,
            "completion": round(tp.completion_percentage, 1),
            "current_level": tp.current_level_number,
            "xp_earned": tp.total_xp_earned
        })

    # Recent attempts
    recent_attempts = db.query(QuestionAttempt).filter(
        QuestionAttempt.user_id == current_user.id
    ).order_by(desc(QuestionAttempt.created_at)).limit(10).all()

    # Unlocked achievements count
    ach_count = db.query(func.count(UserAchievement.id)).filter(
        UserAchievement.user_id == current_user.id
    ).scalar() or 0

    return render_template(
        request=request,
        name="profile.html",
        context={
            "user": current_user,
            "level_num": level_num,
            "progress_pct": progress_pct,
            "xp_in_level": xp_in_level,
            "xp_needed": xp_needed,
            "total_attempts": total_attempts,
            "correct_attempts": correct_attempts,
            "accuracy": accuracy,
            "topics": topics,
            "recent_attempts": recent_attempts,
            "achievements_count": ach_count
        }
    )


@router.post("/api/profile/update")
async def update_profile(
    payload: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if payload.full_name is not None:
        current_user.full_name = payload.full_name
    if payload.sound_enabled is not None:
        current_user.sound_enabled = payload.sound_enabled
    if payload.theme_preference is not None:
        current_user.theme_preference = payload.theme_preference
    if payload.avatar_url is not None:
        current_user.avatar_url = payload.avatar_url

    db.commit()
    return {"status": "success", "message": "Profile preferences updated"}
