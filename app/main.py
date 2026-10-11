import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, engine, SessionLocal
from app.models.admin import Setting
from app.services.auth import ensure_initial_admin
from app.services.gamification import initialize_default_achievements

# Import Routers
from app.routers.auth import router as auth_router
from app.routers.game import router as game_router
from app.routers.daily import router as daily_router
from app.routers.profile import router as profile_router
from app.routers.achievements import router as achievements_router
from app.routers.admin import router as admin_router


def init_default_settings(db):
    """Seed initial game & system settings if not already present."""
    default_settings = [
        ("default_timer_seconds", str(settings.DEFAULT_TIMER_SECONDS), "Default timer per question in seconds"),
        ("base_correct_xp", str(settings.BASE_CORRECT_XP), "XP awarded for answering correctly"),
        ("speed_bonus_under_50", str(settings.SPEED_BONUS_UNDER_50), "Bonus XP if answered under 50% time"),
        ("speed_bonus_under_25", str(settings.SPEED_BONUS_UNDER_25), "Bonus XP if answered under 25% time"),
        ("perfect_level_bonus_xp", str(settings.PERFECT_LEVEL_BONUS_XP), "Bonus XP for completing level without mistakes"),
        ("daily_challenge_bonus_xp", str(settings.DAILY_CHALLENGE_BONUS_XP), "Bonus XP for completing daily challenge"),
        ("sound_effects_enabled", "true", "Enable sound effects globally"),
        ("ai_confidence_threshold", "0.80", "Minimum AI confidence threshold for auto-topic suggestions"),
    ]
    for k, v, desc in default_settings:
        existing = db.query(Setting).filter(Setting.key == k).first()
        if not existing:
            db.add(Setting(key=k, value=v, description=desc))
    db.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Ensure tables exist, seed admin and achievements
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        ensure_initial_admin(db)
        initialize_default_achievements(db)
        init_default_settings(db)
    finally:
        db.close()
    yield
    # Shutdown logic if needed


app = FastAPI(
    title=settings.APP_NAME,
    description="Production-grade Aptitude Practice Game with Apple-inspired UX",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware for modern browser requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
os.makedirs("static", exist_ok=True)
os.makedirs("static/css", exist_ok=True)
os.makedirs("static/js", exist_ok=True)
os.makedirs("static/images", exist_ok=True)
os.makedirs("templates", exist_ok=True)
os.makedirs("uploads", exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

# Include Routers
app.include_router(auth_router)
app.include_router(game_router)
app.include_router(daily_router)
app.include_router(profile_router)
app.include_router(achievements_router)
app.include_router(admin_router)


# Health check endpoint
@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "environment": settings.APP_ENV
    }


from app.templates import render_template

# Custom Error Handlers
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    if request.url.path.startswith("/api/"):
        return JSONResponse(status_code=404, content={"detail": "Resource not found"})
    return render_template(
        request=request,
        name="error.html",
        context={
            "status_code": 404,
            "title": "Page Not Found",
            "message": "The aptitude level or page you are looking for does not exist."
        },
        status_code=404
    )


@app.exception_handler(500)
async def internal_server_error_handler(request: Request, exc):
    if request.url.path.startswith("/api/"):
        return JSONResponse(status_code=500, content={"detail": "Something went wrong. Please try again."})
    return render_template(
        request=request,
        name="error.html",
        context={
            "status_code": 500,
            "title": "Something Went Wrong",
            "message": "We encountered an unexpected error. Our system logged this event."
        },
        status_code=500
    )
