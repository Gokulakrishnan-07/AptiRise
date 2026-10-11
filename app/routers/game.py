import random
from datetime import datetime, date
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.database import get_db
from app.config import settings
from app.models.user import User
from app.models.game import (
    Collection, Level, Question, QuestionOption,
    QuestionAttempt, UserProgress, UserTopicProgress,
    Achievement, UserAchievement
)
from app.schemas.game import (
    QuestionCardSchema, OptionSchema, SubmitAnswerRequest,
    SubmitAnswerResponse, CompleteLevelRequest, CompleteLevelResponse
)
from app.services.auth import get_current_user, get_optional_user
from app.services.gamification import (
    calculate_user_level, calculate_question_xp,
    update_user_streak, check_and_award_achievements
)

from app.templates import render_template

router = APIRouter(tags=["Game"])


@router.get("/", response_class=HTMLResponse)
async def landing_page(
    request: Request,
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    if current_user:
        return RedirectResponse(url="/dashboard", status_code=302)

    # Fetch featured collections for showcase
    featured = db.query(Collection).filter(Collection.is_active == True).limit(6).all()
    total_questions = db.query(Question).filter(Question.is_active == True).count()
    return render_template(
        request=request,
        name="index.html",
        context={
            "featured_collections": featured,
            "total_questions": total_questions,
            "current_user": None
        }
    )


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Recalculate user level & stats
    level_num, progress_pct, xp_in_level, xp_needed = calculate_user_level(current_user.total_xp)
    if current_user.current_level != level_num:
        current_user.current_level = level_num
        db.commit()

    total_attempts = db.query(func.count(QuestionAttempt.id)).filter(
        QuestionAttempt.user_id == current_user.id
    ).scalar() or 0

    correct_attempts = db.query(func.count(QuestionAttempt.id)).filter(
        QuestionAttempt.user_id == current_user.id,
        QuestionAttempt.is_correct == True
    ).scalar() or 0

    accuracy = round((correct_attempts / total_attempts * 100), 1) if total_attempts > 0 else 0.0

    # Collections with user progress
    collections = db.query(Collection).filter(Collection.is_active == True).order_by(Collection.display_order, Collection.id).all()
    collection_data = []

    for col in collections:
        # Check topic progress
        topic_prog = db.query(UserTopicProgress).filter(
            UserTopicProgress.user_id == current_user.id,
            UserTopicProgress.collection_id == col.id
        ).first()

        current_lvl_num = topic_prog.current_level_number if topic_prog else 1
        comp_pct = topic_prog.completion_percentage if topic_prog else 0.0

        # Calculate completed levels in collection
        completed_lvls_count = db.query(func.count(UserProgress.id)).join(Level).filter(
            Level.collection_id == col.id,
            UserProgress.user_id == current_user.id,
            UserProgress.is_completed == True
        ).scalar() or 0

        # If user has no topic progress yet, create initial topic progress
        if not topic_prog:
            topic_prog = UserTopicProgress(
                user_id=current_user.id,
                collection_id=col.id,
                current_level_number=1,
                completion_percentage=0.0,
                total_xp_earned=0
            )
            db.add(topic_prog)
            db.commit()

        # Ensure Level 1 user_progress exists and is unlocked
        lvl1 = db.query(Level).filter(Level.collection_id == col.id, Level.level_number == 1).first()
        if lvl1:
            prog1 = db.query(UserProgress).filter(
                UserProgress.user_id == current_user.id,
                UserProgress.level_id == lvl1.id
            ).first()
            if not prog1:
                prog1 = UserProgress(
                    user_id=current_user.id,
                    level_id=lvl1.id,
                    is_unlocked=True,
                    is_completed=False
                )
                db.add(prog1)
                db.commit()

        collection_data.append({
            "collection": col,
            "current_level": current_lvl_num,
            "completed_levels": completed_lvls_count,
            "total_levels": col.total_levels,
            "completion_pct": round(comp_pct, 1),
            "is_locked": False
        })

    completed_collections_count = sum(1 for c in collection_data if c["completed_levels"] >= c["total_levels"])

    return render_template(
        request=request,
        name="dashboard.html",
        context={
            "user": current_user,
            "level_num": level_num,
            "progress_pct": progress_pct,
            "xp_in_level": xp_in_level,
            "xp_needed": xp_needed,
            "accuracy": accuracy,
            "questions_solved": correct_attempts,
            "collections": collection_data,
            "completed_collections": completed_collections_count
        }
    )


@router.get("/collections/{slug}", response_class=HTMLResponse)
async def collection_page(
    slug: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    collection = db.query(Collection).filter(Collection.slug == slug).first()
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")

    levels = db.query(Level).filter(Level.collection_id == collection.id).order_by(Level.level_number).all()

    levels_data = []
    for lvl in levels:
        prog = db.query(UserProgress).filter(
            UserProgress.user_id == current_user.id,
            UserProgress.level_id == lvl.id
        ).first()

        # Level 1 is always unlocked by default
        is_unlocked = (lvl.level_number == 1) or (prog.is_unlocked if prog else False)
        is_completed = prog.is_completed if prog else False
        best_score = prog.best_score if prog else 0
        accuracy = prog.accuracy if prog else 0.0
        xp_earned = prog.xp_earned if prog else 0

        q_count = db.query(func.count(Question.id)).filter(
            Question.level_id == lvl.id,
            Question.is_active == True
        ).scalar() or 0

        levels_data.append({
            "level": lvl,
            "is_unlocked": is_unlocked,
            "is_completed": is_completed,
            "best_score": best_score,
            "accuracy": round(accuracy, 1),
            "xp_earned": xp_earned,
            "question_count": q_count or lvl.question_count
        })

    return render_template(
        request=request,
        name="collection.html",
        context={
            "user": current_user,
            "collection": collection,
            "levels": levels_data
        }
    )


@router.get("/collections/{slug}/level/{level_number}/play", response_class=HTMLResponse)
async def play_level_page(
    slug: str,
    level_number: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    collection = db.query(Collection).filter(Collection.slug == slug).first()
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")

    level = db.query(Level).filter(
        Level.collection_id == collection.id,
        Level.level_number == level_number
    ).first()
    if not level:
        raise HTTPException(status_code=404, detail="Level not found")

    # Verify if unlocked
    if level_number > 1:
        prog = db.query(UserProgress).filter(
            UserProgress.user_id == current_user.id,
            UserProgress.level_id == level.id
        ).first()
        if not prog or not prog.is_unlocked:
            return RedirectResponse(url=f"/collections/{slug}?locked=true", status_code=302)

    return render_template(
        request=request,
        name="play.html",
        context={
            "user": current_user,
            "collection": collection,
            "level": level
        }
    )


@router.get("/api/game/level/{level_id}/questions")
async def get_level_questions(
    level_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    level = db.query(Level).filter(Level.id == level_id).first()
    if not level:
        raise HTTPException(status_code=404, detail="Level not found")

    # Smart question selection: avoid recently attempted questions if possible
    recent_attempts_subquery = db.query(QuestionAttempt.question_id).filter(
        QuestionAttempt.user_id == current_user.id
    ).order_by(desc(QuestionAttempt.created_at)).limit(20).subquery()

    all_questions = db.query(Question).filter(
        Question.level_id == level.id,
        Question.is_active == True
    ).all()

    if not all_questions:
        # If no questions in level, fallback to collection questions
        all_questions = db.query(Question).filter(
            Question.collection_id == level.collection_id,
            Question.is_active == True
        ).all()

    # Sort with questions not recently answered first
    recent_ids = {r[0] for r in db.query(recent_attempts_subquery).all()}
    fresh_questions = [q for q in all_questions if q.id not in recent_ids]
    older_questions = [q for q in all_questions if q.id in recent_ids]

    combined = fresh_questions + older_questions
    # Pick target count
    chosen = combined[:level.question_count]
    if len(chosen) < level.question_count and len(all_questions) > len(chosen):
        chosen = all_questions[:level.question_count]

    result = []
    for idx, q in enumerate(chosen):
        options = db.query(QuestionOption).filter(QuestionOption.question_id == q.id).all()
        # Sort options A, B, C, D
        options_sorted = sorted(options, key=lambda o: o.option_label)
        result.append({
            "id": q.id,
            "collection_id": level.collection.id,
            "collection_name": level.collection.name,
            "level_id": level.id,
            "level_number": level.level_number,
            "level_title": level.title,
            "question_number": idx + 1,
            "total_questions": len(chosen),
            "question_text": q.question_text,
            "options": [{"label": o.option_label, "text": o.option_text} for o in options_sorted],
            "difficulty": q.difficulty,
            "time_limit": q.time_limit or level.time_limit_seconds,
            "xp_value": q.xp_value
        })

    return {"questions": result, "time_limit_seconds": level.time_limit_seconds}


@router.post("/api/game/submit-answer", response_model=SubmitAnswerResponse)
async def submit_answer(
    payload: SubmitAnswerRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    question = db.query(Question).filter(Question.id == payload.question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    correct_option = db.query(QuestionOption).filter(
        QuestionOption.question_id == question.id,
        QuestionOption.is_correct == True
    ).first()

    if not correct_option:
        raise HTTPException(status_code=500, detail="Question has no marked correct answer")

    is_correct = (payload.selected_option_label.upper() == correct_option.option_label.upper())

    # Calculate XP
    xp_earned, speed_bonus, streak_bonus = calculate_question_xp(
        is_correct=is_correct,
        time_taken=payload.time_taken_seconds,
        time_limit=question.time_limit or 45,
        base_xp=question.xp_value or settings.BASE_CORRECT_XP
    )

    # Save Attempt
    attempt = QuestionAttempt(
        user_id=current_user.id,
        question_id=question.id,
        level_id=payload.level_id or question.level_id,
        selected_option_label=payload.selected_option_label.upper(),
        is_correct=is_correct,
        time_taken_seconds=payload.time_taken_seconds,
        xp_earned=xp_earned,
        attempt_date=date.today()
    )
    db.add(attempt)

    # Update User XP and Level
    old_level = current_user.current_level
    current_user.total_xp += xp_earned
    new_level, _, _, _ = calculate_user_level(current_user.total_xp)
    level_up = (new_level > old_level)
    current_user.current_level = new_level

    # Update streak
    update_user_streak(current_user, db)

    # Check achievements
    unlocked_achievements = check_and_award_achievements(current_user, db)

    db.commit()

    return SubmitAnswerResponse(
        is_correct=is_correct,
        correct_option_label=correct_option.option_label,
        correct_option_text=correct_option.option_text,
        explanation=question.explanation,
        shortcut=question.shortcut,
        time_taken_seconds=payload.time_taken_seconds,
        xp_earned=xp_earned,
        speed_bonus=speed_bonus,
        streak_bonus=streak_bonus,
        total_user_xp=current_user.total_xp,
        new_user_level=new_level,
        level_up=level_up,
        unlocked_achievements=unlocked_achievements
    )


@router.post("/api/game/complete-level", response_model=CompleteLevelResponse)
async def complete_level(
    payload: CompleteLevelRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    level = db.query(Level).filter(Level.id == payload.level_id).first()
    if not level:
        raise HTTPException(status_code=404, detail="Level not found")

    total_answered = payload.correct_count + payload.wrong_count
    accuracy = (payload.correct_count / max(1, total_answered)) * 100.0
    is_perfect = (payload.wrong_count == 0 and payload.correct_count >= 5)

    bonus_xp = 0
    if is_perfect:
        bonus_xp += settings.PERFECT_LEVEL_BONUS_XP

    # Record UserProgress
    prog = db.query(UserProgress).filter(
        UserProgress.user_id == current_user.id,
        UserProgress.level_id == level.id
    ).first()

    if not prog:
        prog = UserProgress(
            user_id=current_user.id,
            level_id=level.id,
            is_unlocked=True,
            is_completed=True,
            best_score=payload.total_score,
            accuracy=accuracy,
            xp_earned=payload.total_score + bonus_xp,
            attempts_count=1,
            perfect_run=is_perfect,
            completed_at=datetime.utcnow()
        )
        db.add(prog)
    else:
        prog.is_completed = True
        prog.attempts_count += 1
        if payload.total_score > prog.best_score:
            prog.best_score = payload.total_score
        if accuracy > prog.accuracy:
            prog.accuracy = accuracy
        prog.xp_earned += bonus_xp
        if is_perfect:
            prog.perfect_run = True
        prog.completed_at = datetime.utcnow()

    # Unlock next level in this collection!
    next_level = db.query(Level).filter(
        Level.collection_id == level.collection_id,
        Level.level_number == level.level_number + 1
    ).first()

    next_unlocked = False
    next_level_id = None
    if next_level:
        next_prog = db.query(UserProgress).filter(
            UserProgress.user_id == current_user.id,
            UserProgress.level_id == next_level.id
        ).first()
        if not next_prog:
            next_prog = UserProgress(
                user_id=current_user.id,
                level_id=next_level.id,
                is_unlocked=True,
                is_completed=False
            )
            db.add(next_prog)
        else:
            next_prog.is_unlocked = True
        next_unlocked = True
        next_level_id = next_level.id

    # Update Topic Progress
    topic_prog = db.query(UserTopicProgress).filter(
        UserTopicProgress.user_id == current_user.id,
        UserTopicProgress.collection_id == level.collection_id
    ).first()

    completed_levels_count = db.query(func.count(UserProgress.id)).join(Level).filter(
        Level.collection_id == level.collection_id,
        UserProgress.user_id == current_user.id,
        UserProgress.is_completed == True
    ).scalar() or 0

    pct = min(100.0, (completed_levels_count / level.collection.total_levels) * 100.0)

    if not topic_prog:
        topic_prog = UserTopicProgress(
            user_id=current_user.id,
            collection_id=level.collection_id,
            current_level_number=min(5, level.level_number + 1),
            completion_percentage=pct,
            total_xp_earned=payload.total_score
        )
        db.add(topic_prog)
    else:
        topic_prog.current_level_number = max(topic_prog.current_level_number, min(5, level.level_number + 1))
        topic_prog.completion_percentage = pct
        topic_prog.total_xp_earned += bonus_xp

    # Add perfect run XP if applicable
    if bonus_xp > 0:
        current_user.total_xp += bonus_xp
        new_lvl, _, _, _ = calculate_user_level(current_user.total_xp)
        current_user.current_level = new_lvl

    unlocked_achievements = check_and_award_achievements(current_user, db)
    db.commit()

    return CompleteLevelResponse(
        level_completed=True,
        next_level_unlocked=next_unlocked,
        next_level_id=next_level_id,
        xp_earned=payload.total_score + bonus_xp,
        accuracy=round(accuracy, 1),
        is_perfect=is_perfect,
        unlocked_achievements=unlocked_achievements
    )


@router.get("/review-mistakes", response_class=HTMLResponse)
async def review_mistakes_page(
    request: Request,
    collection_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(QuestionAttempt).filter(
        QuestionAttempt.user_id == current_user.id,
        QuestionAttempt.is_correct == False
    ).order_by(desc(QuestionAttempt.created_at))

    if collection_id:
        query = query.join(Question).filter(Question.collection_id == collection_id)

    recent_mistakes = query.limit(30).all()

    items = []
    for att in recent_mistakes:
        q = att.question
        correct_opt = db.query(QuestionOption).filter(
            QuestionOption.question_id == q.id,
            QuestionOption.is_correct == True
        ).first()

        user_opt = db.query(QuestionOption).filter(
            QuestionOption.question_id == q.id,
            QuestionOption.option_label == att.selected_option_label
        ).first()

        items.append({
            "question": q,
            "attempt": att,
            "user_choice": att.selected_option_label,
            "user_text": user_opt.option_text if user_opt else "No text",
            "correct_choice": correct_opt.option_label if correct_opt else "A",
            "correct_text": correct_opt.option_text if correct_opt else "Answer",
            "explanation": q.explanation,
            "shortcut": q.shortcut,
            "topic": q.collection.name if q.collection else "Aptitude"
        })

    return render_template(
        request=request,
        name="review.html",
        context={
            "user": current_user,
            "mistakes": items
        }
    )
