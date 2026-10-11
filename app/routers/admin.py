import os
import shutil
from datetime import datetime, date, timedelta
from typing import Optional, List

from fastapi import (
    APIRouter, Depends, HTTPException, status, Request,
    UploadFile, File, Form, Query
)
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.database import get_db
from app.config import settings
from app.models.user import User
from app.models.game import (
    Collection, Level, Question, QuestionOption,
    QuestionAttempt, UserProgress, UserTopicProgress
)
from app.models.admin import PdfImport, PdfImportQuestion, Setting, AuditLog
from app.schemas.admin import (
    QuestionCreate, QuestionUpdate, PdfApproveRequest, SettingUpdate, CollectionCreate
)
from app.services.auth import get_current_admin
from app.services.audit import log_admin_action
from app.services.pdf_parser import pdf_parser
from app.services.ai import ai_service, calculate_similarity

from app.templates import render_template

router = APIRouter(prefix="/admin", tags=["Admin"])

# Ensure uploads directory exists
UPLOAD_DIR = os.path.join(os.getcwd(), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    total_users = db.query(func.count(User.id)).scalar() or 0
    active_users = db.query(func.count(User.id)).filter(
        User.last_active_date >= date.today() - timedelta(days=7)
    ).scalar() or 0
    total_questions = db.query(func.count(Question.id)).scalar() or 0
    total_collections = db.query(func.count(Collection.id)).scalar() or 0

    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    questions_today = db.query(func.count(Question.id)).filter(
        Question.created_at >= today_start
    ).scalar() or 0

    # Most practiced topic
    most_practiced = db.query(
        Collection.name,
        func.count(QuestionAttempt.id).label("count")
    ).join(Question, Question.collection_id == Collection.id)\
     .join(QuestionAttempt, QuestionAttempt.question_id == Question.id)\
     .group_by(Collection.name)\
     .order_by(desc("count")).first()

    most_practiced_topic = most_practiced[0] if most_practiced else "None yet"

    # Average accuracy
    total_attempts = db.query(func.count(QuestionAttempt.id)).scalar() or 0
    correct_attempts = db.query(func.count(QuestionAttempt.id)).filter(
        QuestionAttempt.is_correct == True
    ).scalar() or 0
    avg_accuracy = round((correct_attempts / total_attempts * 100), 1) if total_attempts > 0 else 0.0

    # Recent Audit Logs
    recent_logs = db.query(AuditLog).order_by(desc(AuditLog.created_at)).limit(8).all()

    # Questions per collection for charts
    questions_per_collection = db.query(
        Collection.name,
        func.count(Question.id)
    ).join(Question, Question.collection_id == Collection.id, isouter=True)\
     .group_by(Collection.name).all()

    chart_labels = [c[0] for c in questions_per_collection]
    chart_data = [c[1] for c in questions_per_collection]

    return render_template(
        request=request,
        name="admin/dashboard.html",
        context={
            "admin": current_admin,
            "total_users": total_users,
            "active_users": active_users,
            "total_questions": total_questions,
            "total_collections": total_collections,
            "questions_today": questions_today,
            "most_practiced_topic": most_practiced_topic,
            "avg_accuracy": avg_accuracy,
            "recent_logs": recent_logs,
            "chart_labels": chart_labels,
            "chart_data": chart_data
        }
    )


# --- Question Management ---
@router.get("/questions", response_class=HTMLResponse)
async def admin_questions(
    request: Request,
    search: Optional[str] = None,
    collection_id: Optional[int] = None,
    difficulty: Optional[str] = None,
    page: int = Query(1, ge=1),
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    query = db.query(Question)

    if search:
        query = query.filter(Question.question_text.ilike(f"%{search}%"))
    if collection_id:
        query = query.filter(Question.collection_id == collection_id)
    if difficulty:
        query = query.filter(Question.difficulty == difficulty)

    total_count = query.count()
    per_page = 15
    total_pages = max(1, (total_count + per_page - 1) // per_page)
    offset = (page - 1) * per_page

    questions = query.order_by(desc(Question.id)).offset(offset).limit(per_page).all()
    collections = db.query(Collection).order_by(Collection.name).all()

    return render_template(
        request=request,
        name="admin/questions.html",
        context={
            "admin": current_admin,
            "questions": questions,
            "collections": collections,
            "search": search or "",
            "collection_id": collection_id,
            "difficulty": difficulty or "",
            "page": page,
            "total_pages": total_pages,
            "total_count": total_count
        }
    )


@router.post("/api/questions")
async def admin_create_question(
    payload: QuestionCreate,
    request: Request,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    q = Question(
        collection_id=payload.collection_id,
        level_id=payload.level_id,
        question_text=payload.question_text,
        explanation=payload.explanation,
        shortcut=payload.shortcut,
        difficulty=payload.difficulty,
        time_limit=payload.time_limit,
        xp_value=payload.xp_value,
        tags=payload.tags,
        source="manual"
    )
    db.add(q)
    db.commit()
    db.refresh(q)

    for opt in payload.options:
        o = QuestionOption(
            question_id=q.id,
            option_label=opt.option_label.upper(),
            option_text=opt.option_text,
            is_correct=opt.is_correct
        )
        db.add(o)

    db.commit()

    log_admin_action(
        db, current_admin, "Created Question",
        "question", str(q.id), f"Created question in collection {payload.collection_id}", request
    )

    return {"status": "success", "question_id": q.id}


@router.put("/api/questions/{question_id}")
async def admin_update_question(
    question_id: int,
    payload: QuestionUpdate,
    request: Request,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    q = db.query(Question).filter(Question.id == question_id).first()
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")

    if payload.collection_id is not None:
        q.collection_id = payload.collection_id
    if payload.level_id is not None:
        q.level_id = payload.level_id
    if payload.question_text is not None:
        q.question_text = payload.question_text
    if payload.explanation is not None:
        q.explanation = payload.explanation
    if payload.shortcut is not None:
        q.shortcut = payload.shortcut
    if payload.difficulty is not None:
        q.difficulty = payload.difficulty
    if payload.time_limit is not None:
        q.time_limit = payload.time_limit
    if payload.xp_value is not None:
        q.xp_value = payload.xp_value
    if payload.tags is not None:
        q.tags = payload.tags
    if payload.is_active is not None:
        q.is_active = payload.is_active

    if payload.options is not None:
        db.query(QuestionOption).filter(QuestionOption.question_id == q.id).delete()
        for opt in payload.options:
            o = QuestionOption(
                question_id=q.id,
                option_label=opt.option_label.upper(),
                option_text=opt.option_text,
                is_correct=opt.is_correct
            )
            db.add(o)

    db.commit()

    log_admin_action(
        db, current_admin, "Updated Question",
        "question", str(q.id), f"Updated question #{q.id}", request
    )

    return {"status": "success", "message": "Question updated"}


@router.delete("/api/questions/{question_id}")
async def admin_delete_question(
    question_id: int,
    request: Request,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    q = db.query(Question).filter(Question.id == question_id).first()
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")

    db.delete(q)
    db.commit()

    log_admin_action(
        db, current_admin, "Deleted Question",
        "question", str(question_id), f"Deleted question #{question_id}", request
    )

    return {"status": "success", "message": "Question deleted"}


@router.post("/api/questions/{question_id}/duplicate")
async def admin_duplicate_question(
    question_id: int,
    request: Request,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    original = db.query(Question).filter(Question.id == question_id).first()
    if not original:
        raise HTTPException(status_code=404, detail="Original question not found")

    new_q = Question(
        collection_id=original.collection_id,
        level_id=original.level_id,
        question_text=f"{original.question_text} (Copy)",
        explanation=original.explanation,
        shortcut=original.shortcut,
        difficulty=original.difficulty,
        time_limit=original.time_limit,
        xp_value=original.xp_value,
        tags=original.tags,
        source="manual"
    )
    db.add(new_q)
    db.commit()
    db.refresh(new_q)

    for opt in original.options:
        new_opt = QuestionOption(
            question_id=new_q.id,
            option_label=opt.option_label,
            option_text=opt.option_text,
            is_correct=opt.is_correct
        )
        db.add(new_opt)

    db.commit()

    log_admin_action(
        db, current_admin, "Duplicated Question",
        "question", str(new_q.id), f"Duplicated from #{question_id}", request
    )

    return {"status": "success", "question_id": new_q.id}


# --- PDF Upload, AI Pipeline & Review ---
@router.get("/pdf/import", response_class=HTMLResponse)
async def admin_pdf_import_page(
    request: Request,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    collections = db.query(Collection).order_by(Collection.name).all()
    past_imports = db.query(PdfImport).order_by(desc(PdfImport.created_at)).limit(10).all()

    return render_template(
        request=request,
        name="admin/pdf_import.html",
        context={
            "admin": current_admin,
            "collections": collections,
            "past_imports": past_imports
        }
    )


@router.post("/pdf/upload")
async def admin_upload_pdf(
    request: Request,
    file: UploadFile = File(...),
    collection_id: Optional[int] = Form(None),
    level_id: Optional[int] = Form(None),
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    # Validate extension
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    file_path = os.path.join(UPLOAD_DIR, f"{datetime.utcnow().timestamp()}_{file.filename}")
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    pdf_record = PdfImport(
        filename=file.filename,
        file_path=file_path,
        uploaded_by_user_id=current_admin.id,
        status="processing",
        target_collection_id=collection_id,
        target_level_id=level_id
    )
    db.add(pdf_record)
    db.commit()
    db.refresh(pdf_record)

    try:
        # Run Extraction & AI Classification Pipeline
        parsed_items = await pdf_parser.process_and_classify_pdf(
            file_path, db, default_collection_id=collection_id, default_level_id=level_id
        )

        pdf_record.total_detected = len(parsed_items)
        pdf_record.status = "reviewed"

        for item in parsed_items:
            # Find topic collection if not assigned
            col_id = item["final_collection_id"]
            if not col_id:
                matched_col = db.query(Collection).filter(Collection.name.ilike(f"%{item['detected_topic']}%")).first()
                if matched_col:
                    col_id = matched_col.id
                else:
                    # Default to first collection
                    first_c = db.query(Collection).first()
                    col_id = first_c.id if first_c else None

            # Find matching level by difficulty
            lvl_id = item["final_level_id"]
            if not lvl_id and col_id:
                diff_lvl_map = {"Beginner": 1, "Easy": 2, "Intermediate": 3, "Advanced": 4, "Expert": 5}
                target_lvl_num = diff_lvl_map.get(item["detected_difficulty"], 3)
                matched_lvl = db.query(Level).filter(
                    Level.collection_id == col_id,
                    Level.level_number == target_lvl_num
                ).first()
                if matched_lvl:
                    lvl_id = matched_lvl.id

            q_item = PdfImportQuestion(
                pdf_import_id=pdf_record.id,
                raw_text=item["raw_text"],
                question_text=item["question_text"],
                option_a=item["option_a"],
                option_b=item["option_b"],
                option_c=item["option_c"],
                option_d=item["option_d"],
                detected_answer=item["detected_answer"],
                detected_explanation=item["detected_explanation"],
                detected_shortcut=item["detected_shortcut"],
                detected_topic=item["detected_topic"],
                detected_difficulty=item["detected_difficulty"],
                ai_confidence=item["ai_confidence"],
                status="duplicate" if item["is_duplicate"] else "pending",
                is_duplicate=item["is_duplicate"],
                duplicate_question_id=item["duplicate_question_id"],
                final_collection_id=col_id,
                final_level_id=lvl_id
            )
            db.add(q_item)

        db.commit()

        log_admin_action(
            db, current_admin, "Uploaded PDF",
            "pdf_import", str(pdf_record.id), f"Processed {file.filename} - {len(parsed_items)} questions found", request
        )

        return RedirectResponse(url=f"/admin/pdf/review/{pdf_record.id}", status_code=303)

    except Exception as e:
        pdf_record.status = "rejected"
        pdf_record.error_message = str(e)
        db.commit()
        raise HTTPException(status_code=500, detail=f"Failed to process PDF: {str(e)}")


@router.get("/pdf/review/{import_id}", response_class=HTMLResponse)
async def admin_pdf_review_page(
    import_id: int,
    request: Request,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    pdf_import = db.query(PdfImport).filter(PdfImport.id == import_id).first()
    if not pdf_import:
        raise HTTPException(status_code=404, detail="PDF import not found")

    questions = db.query(PdfImportQuestion).filter(
        PdfImportQuestion.pdf_import_id == import_id
    ).all()

    collections = db.query(Collection).order_by(Collection.name).all()
    levels = db.query(Level).order_by(Level.collection_id, Level.level_number).all()

    return render_template(
        request=request,
        name="admin/pdf_review.html",
        context={
            "admin": current_admin,
            "pdf_import": pdf_import,
            "questions": questions,
            "collections": collections,
            "levels": levels
        }
    )


@router.post("/api/pdf/approve")
async def admin_approve_pdf_questions(
    payload: PdfApproveRequest,
    request: Request,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    pdf_import = db.query(PdfImport).filter(PdfImport.id == payload.pdf_import_id).first()
    if not pdf_import:
        raise HTTPException(status_code=404, detail="PDF import not found")

    approved_count = 0
    for q_data in payload.questions:
        import_q = db.query(PdfImportQuestion).filter(PdfImportQuestion.id == q_data.id).first()
        if not import_q:
            continue

        # Create published question
        new_q = Question(
            collection_id=q_data.collection_id,
            level_id=q_data.level_id,
            question_text=q_data.question_text,
            explanation=q_data.detected_explanation,
            shortcut=q_data.detected_shortcut,
            difficulty=q_data.difficulty,
            time_limit=45,
            xp_value=100,
            source="pdf_import",
            is_active=True
        )
        db.add(new_q)
        db.commit()
        db.refresh(new_q)

        # Options
        options = [
            ("A", q_data.option_a),
            ("B", q_data.option_b),
            ("C", q_data.option_c),
            ("D", q_data.option_d)
        ]
        for lbl, txt in options:
            is_cor = (lbl.upper() == q_data.detected_answer.upper())
            opt = QuestionOption(
                question_id=new_q.id,
                option_label=lbl,
                option_text=txt,
                is_correct=is_cor
            )
            db.add(opt)

        import_q.status = "approved"
        approved_count += 1

    pdf_import.approved_count = approved_count
    pdf_import.status = "approved"
    db.commit()

    log_admin_action(
        db, current_admin, "Approved PDF Questions",
        "pdf_import", str(pdf_import.id), f"Approved and published {approved_count} questions", request
    )

    return {"status": "success", "approved_count": approved_count}


# --- Settings & Audit Logs ---
@router.get("/settings", response_class=HTMLResponse)
async def admin_settings_page(
    request: Request,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    settings_records = db.query(Setting).all()
    settings_dict = {s.key: s.value for s in settings_records}

    return render_template(
        request=request,
        name="admin/settings.html",
        context={
            "admin": current_admin,
            "settings": settings_dict,
            "hf_configured": bool(settings.HF_TOKEN)
        }
    )


@router.post("/api/settings")
async def admin_update_setting(
    payload: SettingUpdate,
    request: Request,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    setting = db.query(Setting).filter(Setting.key == payload.key).first()
    if not setting:
        setting = Setting(key=payload.key, value=payload.value)
        db.add(setting)
    else:
        setting.value = payload.value

    db.commit()

    log_admin_action(
        db, current_admin, "Updated Setting",
        "setting", payload.key, f"Updated setting {payload.key} to {payload.value}", request
    )

    return {"status": "success", "key": payload.key, "value": payload.value}


@router.get("/audit-logs", response_class=HTMLResponse)
async def admin_audit_logs_page(
    request: Request,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    logs = db.query(AuditLog).order_by(desc(AuditLog.created_at)).limit(100).all()
    return render_template(
        request=request,
        name="admin/audit_logs.html",
        context={
            "admin": current_admin,
            "logs": logs
        }
    )
