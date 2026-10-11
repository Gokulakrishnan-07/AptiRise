from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.user import User
from app.models.game import (
    QuestionAttempt, UserProgress, UserTopicProgress,
    Achievement, UserAchievement, Level, Collection
)
from app.config import settings

# Thresholds for Levels:
# Level 1: 0
# Level 2: 500
# Level 3: 1200
# Level 4: 2000
# Level 5: 3000
# Level 6: 4200
# etc.
def get_xp_threshold(level: int) -> int:
    if level <= 1:
        return 0
    elif level == 2:
        return 500
    elif level == 3:
        return 1200
    elif level == 4:
        return 2000
    elif level == 5:
        return 3000
    else:
        # Dynamic progression: 3000 + sum for i in 6..level of (1000 + (i-5)*300)
        total = 3000
        for l in range(6, level + 1):
            total += 1000 + (l - 5) * 350
        return total


def calculate_user_level(total_xp: int) -> Tuple[int, float, int, int]:
    """
    Returns (current_level, progress_pct, xp_in_level, xp_needed_for_next)
    """
    level = 1
    while get_xp_threshold(level + 1) <= total_xp:
        level += 1

    current_threshold = get_xp_threshold(level)
    next_threshold = get_xp_threshold(level + 1)
    xp_in_level = total_xp - current_threshold
    xp_needed_for_next = next_threshold - current_threshold
    progress_pct = min(100.0, max(0.0, (xp_in_level / max(1, xp_needed_for_next)) * 100.0))

    return level, round(progress_pct, 1), xp_in_level, xp_needed_for_next


def calculate_question_xp(
    is_correct: bool,
    time_taken: float,
    time_limit: int,
    base_xp: int = 100
) -> Tuple[int, int, int]:
    """
    Returns (total_xp_earned, speed_bonus, streak_bonus)
    """
    if not is_correct:
        return 0, 0, 0

    speed_bonus = 0
    time_limit = max(10, time_limit)
    if time_taken <= (time_limit * 0.25):
        speed_bonus = settings.SPEED_BONUS_UNDER_25  # +100 XP
    elif time_taken <= (time_limit * 0.50):
        speed_bonus = settings.SPEED_BONUS_UNDER_50  # +50 XP

    total = base_xp + speed_bonus
    return total, speed_bonus, 0


def update_user_streak(user: User, db: Session) -> bool:
    """
    Updates the user's daily streak.
    Returns True if streak increased.
    """
    today = date.today()
    if user.last_active_date == today:
        return False

    streak_increased = False
    if user.last_active_date == today - timedelta(days=1):
        user.current_streak += 1
        streak_increased = True
    else:
        user.current_streak = 1
        streak_increased = True

    if user.current_streak > user.longest_streak:
        user.longest_streak = user.current_streak

    user.last_active_date = today
    return streak_increased


def check_and_award_achievements(user: User, db: Session) -> List[Dict[str, Any]]:
    """
    Checks all achievements and awards newly unlocked ones to the user.
    Returns list of newly unlocked achievements.
    """
    all_achievements = db.query(Achievement).all()
    already_unlocked_ids = {
        ua.achievement_id for ua in db.query(UserAchievement).filter(UserAchievement.user_id == user.id).all()
    }

    # Gather user metrics
    total_attempts = db.query(func.count(QuestionAttempt.id)).filter(
        QuestionAttempt.user_id == user.id,
        QuestionAttempt.is_correct == True
    ).scalar() or 0

    fast_attempts = db.query(func.count(QuestionAttempt.id)).filter(
        QuestionAttempt.user_id == user.id,
        QuestionAttempt.is_correct == True,
        QuestionAttempt.time_taken_seconds <= 12.0
    ).scalar() or 0

    perfect_levels = db.query(func.count(UserProgress.id)).filter(
        UserProgress.user_id == user.id,
        UserProgress.perfect_run == True
    ).scalar() or 0

    completed_topics = db.query(func.count(UserTopicProgress.id)).filter(
        UserTopicProgress.user_id == user.id,
        UserTopicProgress.completion_percentage >= 100.0
    ).scalar() or 0

    newly_unlocked = []

    for ach in all_achievements:
        if ach.id in already_unlocked_ids:
            continue

        unlocked = False
        if ach.requirement_type == "first_question" and total_attempts >= ach.requirement_value:
            unlocked = True
        elif ach.requirement_type == "streak_days" and user.current_streak >= ach.requirement_value:
            unlocked = True
        elif ach.requirement_type == "speed_master" and fast_attempts >= ach.requirement_value:
            unlocked = True
        elif ach.requirement_type == "perfect_level" and perfect_levels >= ach.requirement_value:
            unlocked = True
        elif ach.requirement_type == "topic_master" and completed_topics >= ach.requirement_value:
            unlocked = True
        elif ach.requirement_type == "global_level" and user.current_level >= ach.requirement_value:
            unlocked = True
        elif ach.requirement_type == "questions_count" and total_attempts >= ach.requirement_value:
            unlocked = True

        if unlocked:
            user_ach = UserAchievement(user_id=user.id, achievement_id=ach.id)
            db.add(user_ach)
            # Award bonus XP for achievement
            user.total_xp += ach.xp_reward
            new_lvl, _, _, _ = calculate_user_level(user.total_xp)
            user.current_level = new_lvl

            newly_unlocked.append({
                "id": ach.id,
                "title": ach.title,
                "description": ach.description,
                "icon": ach.icon,
                "badge_color": ach.badge_color,
                "xp_reward": ach.xp_reward
            })

    return newly_unlocked


def initialize_default_achievements(db: Session):
    """
    Seed initial system achievements if none exist.
    """
    count = db.query(Achievement).count()
    if count > 0:
        return

    defaults = [
        {
            "slug": "first_question",
            "title": "First Step",
            "description": "Answer your first aptitude question correctly.",
            "icon": "target",
            "badge_color": "blue",
            "xp_reward": 50,
            "requirement_type": "first_question",
            "requirement_value": 1
        },
        {
            "slug": "streak_7",
            "title": "Unstoppable",
            "description": "Practice aptitude 7 days in a row.",
            "icon": "flame",
            "badge_color": "orange",
            "xp_reward": 300,
            "requirement_type": "streak_days",
            "requirement_value": 7
        },
        {
            "slug": "speed_master",
            "title": "Speed Demon",
            "description": "Solve 10 questions lightning fast in under 12 seconds.",
            "icon": "zap",
            "badge_color": "yellow",
            "xp_reward": 200,
            "requirement_type": "speed_master",
            "requirement_value": 10
        },
        {
            "slug": "perfect_score",
            "title": "Flawless Victory",
            "description": "Complete a full level with 100% accuracy.",
            "icon": "award",
            "badge_color": "emerald",
            "xp_reward": 250,
            "requirement_type": "perfect_level",
            "requirement_value": 1
        },
        {
            "slug": "topic_master",
            "title": "Topic Grandmaster",
            "description": "Master all 5 levels of an aptitude collection.",
            "icon": "crown",
            "badge_color": "purple",
            "xp_reward": 500,
            "requirement_type": "topic_master",
            "requirement_value": 1
        },
        {
            "slug": "global_level_5",
            "title": "Rising Star",
            "description": "Reach Global Level 5.",
            "icon": "star",
            "badge_color": "amber",
            "xp_reward": 200,
            "requirement_type": "global_level",
            "requirement_value": 5
        },
        {
            "slug": "global_level_10",
            "title": "Aptitude Prodigy",
            "description": "Reach Global Level 10.",
            "icon": "shield",
            "badge_color": "indigo",
            "xp_reward": 400,
            "requirement_type": "global_level",
            "requirement_value": 10
        },
        {
            "slug": "questions_100",
            "title": "Centurion",
            "description": "Solve 100 aptitude questions correctly.",
            "icon": "trophy",
            "badge_color": "rose",
            "xp_reward": 350,
            "requirement_type": "questions_count",
            "requirement_value": 100
        }
    ]

    for d in defaults:
        ach = Achievement(**d)
        db.add(ach)
    db.commit()
    print("[Seed] Initial achievements seeded successfully.")
