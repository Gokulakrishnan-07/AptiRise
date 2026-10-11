import os
from datetime import timedelta
from typing import Optional
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, status, Request, Response, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import httpx

from app.database import get_db
from app.config import settings
from app.models.user import User, OAuthAccount
from app.schemas.user import UserRegister, UserLogin, UserResponse, TokenResponse, PasswordChange
from app.services.auth import (
    hash_password, verify_password, create_access_token,
    get_current_user, get_optional_user
)
from app.services.gamification import calculate_user_level, update_user_streak

from app.templates import render_template

router = APIRouter(tags=["Authentication"])


@router.get("/login", response_class=HTMLResponse)
async def login_page(
    request: Request,
    current_user: Optional[User] = Depends(get_optional_user)
):
    if current_user:
        if current_user.role == "admin":
            return RedirectResponse(url="/admin", status_code=302)
        return RedirectResponse(url="/dashboard", status_code=302)
    return render_template(
        request=request,
        name="login.html",
        context={
            "google_enabled": bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET)
        }
    )


@router.get("/register", response_class=HTMLResponse)
async def register_page(
    request: Request,
    current_user: Optional[User] = Depends(get_optional_user)
):
    if current_user:
        return RedirectResponse(url="/dashboard", status_code=302)
    return render_template(
        request=request,
        name="register.html",
        context={
            "google_enabled": bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET)
        }
    )


@router.post("/api/auth/register", response_model=TokenResponse)
async def api_register(
    payload: UserRegister,
    response: Response,
    db: Session = Depends(get_db)
):
    # Check if username or email already exists
    existing = db.query(User).filter(
        (User.email == payload.email) | (User.username == payload.username)
    ).first()
    if existing:
        if existing.email == payload.email:
            raise HTTPException(status_code=400, detail="An account with this email already exists.")
        raise HTTPException(status_code=400, detail="Username is already taken.")

    user = User(
        username=payload.username,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name or payload.username,
        role="user",
        current_level=1,
        total_xp=0,
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    update_user_streak(user, db)
    db.commit()

    token = create_access_token({"sub": str(user.id), "role": user.role})
    response.set_cookie(
        key="access_token",
        value=f"Bearer {token}",
        httponly=True,
        max_age=3600 * 24 * 30,
        samesite="lax",
        secure=False  # Allow local HTTP testing
    )

    return TokenResponse(
        access_token=token,
        user=UserResponse.model_validate(user)
    )


@router.post("/api/auth/login", response_model=TokenResponse)
async def api_login(
    payload: UserLogin,
    response: Response,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive"
        )

    update_user_streak(user, db)
    db.commit()

    token = create_access_token({"sub": str(user.id), "role": user.role})
    response.set_cookie(
        key="access_token",
        value=f"Bearer {token}",
        httponly=True,
        max_age=3600 * 24 * 30,
        samesite="lax",
        secure=False
    )

    return TokenResponse(
        access_token=token,
        user=UserResponse.model_validate(user)
    )


@router.get("/api/auth/me", response_model=UserResponse)
async def api_get_me(current_user: User = Depends(get_current_user)):
    return UserResponse.model_validate(current_user)


@router.post("/api/auth/change-password")
async def api_change_password(
    payload: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password incorrect")

    current_user.hashed_password = hash_password(payload.new_password)
    db.commit()
    return {"status": "success", "message": "Password updated successfully"}


@router.get("/logout")
@router.post("/api/auth/logout")
async def logout(response: Response):
    resp = RedirectResponse(url="/login", status_code=302)
    resp.delete_cookie("access_token")
    return resp


# --- Google OAuth Flow ---
@router.get("/auth/google")
async def google_auth():
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=503,
            detail="Google OAuth is not configured in environment variables."
        )

    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent",
    }
    url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
    return RedirectResponse(url=url)


@router.get("/auth/google/callback")
async def google_auth_callback(
    request: Request,
    code: Optional[str] = None,
    error: Optional[str] = None,
    db: Session = Depends(get_db)
):
    if error or not code:
        return RedirectResponse(url="/login?error=google_cancelled")

    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "code": code,
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code",
    }

    try:
        async with httpx.AsyncClient() as client:
            token_resp = await client.post(token_url, data=data)
            token_json = token_resp.json()
            access_token = token_json.get("access_token")

            if not access_token:
                return RedirectResponse(url="/login?error=google_token_failed")

            userinfo_resp = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            user_info = userinfo_resp.json()

            google_id = user_info.get("id")
            email = user_info.get("email")
            name = user_info.get("name", "")
            picture = user_info.get("picture", "")

            if not email:
                return RedirectResponse(url="/login?error=email_not_provided")

            # Check if user exists by email or oauth account
            oauth_acc = db.query(OAuthAccount).filter(
                OAuthAccount.provider == "google",
                OAuthAccount.provider_user_id == google_id
            ).first()

            if oauth_acc:
                user = oauth_acc.user
            else:
                user = db.query(User).filter(User.email == email).first()
                if not user:
                    # Generate username from email
                    base_username = email.split("@")[0]
                    clean_username = "".join(c for c in base_username if c.isalnum() or c == "_")
                    user = User(
                        username=clean_username or f"user_{google_id[:6]}",
                        email=email,
                        full_name=name,
                        avatar_url=picture,
                        role="user",
                        current_level=1,
                        total_xp=0,
                        is_active=True
                    )
                    db.add(user)
                    db.commit()
                    db.refresh(user)

                # Link OAuth account
                new_oauth = OAuthAccount(
                    user_id=user.id,
                    provider="google",
                    provider_user_id=google_id,
                    email=email,
                    access_token=access_token
                )
                db.add(new_oauth)
                db.commit()

            update_user_streak(user, db)
            db.commit()

            jwt_token = create_access_token({"sub": str(user.id), "role": user.role})
            redirect_target = "/admin" if user.role == "admin" else "/dashboard"
            response = RedirectResponse(url=redirect_target, status_code=302)
            response.set_cookie(
                key="access_token",
                value=f"Bearer {jwt_token}",
                httponly=True,
                max_age=3600 * 24 * 30,
                samesite="lax",
                secure=False
            )
            return response

    except Exception as e:
        return RedirectResponse(url="/login?error=oauth_error")
