from typing import Optional
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.game import Achievement, UserAchievement
from app.services.auth import get_current_user
from app.templates import render_template

router = APIRouter(tags=["Achievements"])


@router.get("/achievements", response_class=HTMLResponse)
async def achievements_page(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    all_achievements = db.query(Achievement).all()
    user_unlocked = {
        ua.achievement_id: ua.unlocked_at
        for ua in db.query(UserAchievement).filter(UserAchievement.user_id == current_user.id).all()
    }

    achievements_list = []
    unlocked_count = 0
    total_xp_from_achievements = 0

    for ach in all_achievements:
        is_unlocked = ach.id in user_unlocked
        if is_unlocked:
            unlocked_count += 1
            total_xp_from_achievements += ach.xp_reward

        achievements_list.append({
            "id": ach.id,
            "title": ach.title,
            "description": ach.description,
            "icon": ach.icon,
            "badge_color": ach.badge_color,
            "xp_reward": ach.xp_reward,
            "is_unlocked": is_unlocked,
            "unlocked_at": user_unlocked.get(ach.id)
        })

    return render_template(
        request=request,
        name="achievements.html",
        context={
            "user": current_user,
            "achievements": achievements_list,
            "unlocked_count": unlocked_count,
            "total_count": len(all_achievements),
            "total_xp_from_achievements": total_xp_from_achievements
        }
    )
