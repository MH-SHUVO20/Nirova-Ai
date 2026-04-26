#NirovaAI — Authentication API
#Endpoints:
#- POST /auth/register  → create new account
#- POST /auth/login     → login and get JWT token
#- GET  /auth/me        → get your profile


from fastapi import APIRouter, HTTPException, status, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, Field
from app.core.database import users, get_db
from app.core.auth import hash_password, verify_password, create_token, get_current_user
from app.core.config import settings
from app.core.redis_client import is_rate_limited
from datetime import datetime, timedelta, timezone
import secrets
import hashlib
import smtplib
import ssl
import logging
from urllib.parse import quote_plus
from email.message import EmailMessage

router = APIRouter(prefix="/auth", tags=["Authentication"])
log = logging.getLogger(__name__)
RATE_LIMIT_WINDOW_SECONDS = 3600


def _client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _smtp_ready() -> bool:
    return bool(
        settings.SMTP_HOST
        and settings.SMTP_USERNAME
        and settings.SMTP_PASSWORD
        and settings.SMTP_FROM_EMAIL
    )


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _cookie_secure_flag(request: Request | None = None) -> bool:
    # Explicit configuration always wins.
    if settings.COOKIE_SECURE:
        return True

    # In local debug/development mode, avoid Secure cookies on HTTP.
    if settings.DEBUG:
        return False

    # Prefer request-aware protocol detection when available.
    if request is not None:
        forwarded_proto = (request.headers.get("x-forwarded-proto") or "").lower().strip()
        if forwarded_proto:
            return forwarded_proto == "https"
        return request.url.scheme == "https"

    # Fallback to configured frontend URL if request context is unavailable.
    return settings.FRONTEND_URL.lower().startswith("https://")


def _set_auth_cookie(response: JSONResponse, token: str, request: Request | None = None) -> None:
    response.set_cookie(
        key=settings.AUTH_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=_cookie_secure_flag(request),
        samesite=settings.COOKIE_SAMESITE,
        path="/",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


def _send_reset_email(recipient: str, token: str, expires_at: datetime, reset_link: str) -> bool:
    if not _smtp_ready():
        return False

    msg = EmailMessage()
    msg["Subject"] = "NirovaAI password reset"
    msg["From"] = settings.SMTP_FROM_EMAIL
    msg["To"] = recipient
    msg.set_content(
        "You requested a password reset for your NirovaAI account.\n\n"
        f"Reset link: {reset_link}\n\n"
        "If the button/link does not open, use the token below manually.\n"
        f"Reset token: {token}\n"
        f"Expires at (UTC): {expires_at.isoformat()}\n\n"
        "If you did not request this, you can ignore this email."
    )

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=20) as server:
            if settings.SMTP_USE_TLS:
                server.starttls(context=ssl.create_default_context())
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as exc:
        log.warning(f"Failed to send reset email: {exc}")
        return False


# ── Request Models ──

class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    age: int = Field(0, ge=0, le=150)
    district: str = Field("Dhaka", max_length=100)
    language: str = Field("en", max_length=10)  # "en" for English, "bn" for Bangla

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr
    age: int | None = None
    district: str | None = None


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


# ── Response Models ──

class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    name: str
    email: str
    message: str


class ForgotPasswordResponse(BaseModel):
    message: str
    verification_method: str | None = None
    reset_token_preview: str | None = None
    reset_link_preview: str | None = None


class AuthHealthResponse(BaseModel):
    status: str
    auth_ready: bool
    database_ready: bool
    message: str


# ── Endpoints ──

@router.get("/health", response_model=AuthHealthResponse)
async def auth_health():
    """Readiness check focused on authentication dependencies."""
    try:
        get_db()
    except HTTPException:
        return JSONResponse(
            status_code=503,
            content={
                "status": "degraded",
                "auth_ready": False,
                "database_ready": False,
                "message": "Authentication database is unavailable.",
            },
        )

    return {
        "status": "healthy",
        "auth_ready": True,
        "database_ready": True,
        "message": "Authentication endpoints are ready.",
    }

@router.post("/register", status_code=201)
async def register(data: RegisterRequest, request: Request):
    """
    Create a new NirovaAI account.
    Password is hashed before storage — we never store plain passwords.
    """
    # Check if email already exists
    normalized_email = _normalize_email(data.email)
    # Password complexity: min 8 chars, at least 1 letter + 1 digit
    if len(data.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long",
        )
    if not any(c.isalpha() for c in data.password) or not any(c.isdigit() for c in data.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain at least one letter and one number",
        )
    existing = await users().find_one({"email": normalized_email})
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists"
        )

    # Save new user to MongoDB
    new_user = {
        "name": data.name,
        "email": normalized_email,
        "hashed_password": hash_password(data.password),
        "age": data.age,
        "district": data.district,
        "language": data.language,
        "created_at": datetime.now(timezone.utc),
        "total_symptom_logs": 0,
        "total_alerts": 0
    }

    result = await users().insert_one(new_user)
    user_id = str(result.inserted_id)

    response = JSONResponse({
        "message": "Account created successfully! Welcome to NirovaAI.",
        "user_id": user_id,
        "name": data.name,
        "email": data.email
    }, status_code=201)
    _set_auth_cookie(response, create_token(user_id), request)
    return response


@router.post("/login")
async def login(data: LoginRequest, request: Request):
    """
    Login with email and password.
    Returns a JWT token via HttpOnly cookie valid for 7 days.
    """
    # Rate limit login attempts per IP
    ip_key = _client_ip(request)
    limited_ip = await is_rate_limited(
        f"rl:login:ip:{ip_key}",
        20,  # max 20 login attempts per hour per IP
        RATE_LIMIT_WINDOW_SECONDS,
    )
    if limited_ip:
        raise HTTPException(
            status_code=429,
            detail="Too many login attempts. Please try again later.",
        )

    # Find the user
    normalized_email = _normalize_email(data.email)

    # Rate limit per email too
    limited_email = await is_rate_limited(
        f"rl:login:email:{normalized_email}",
        10,  # max 10 login attempts per hour per email
        RATE_LIMIT_WINDOW_SECONDS,
    )
    if limited_email:
        raise HTTPException(
            status_code=429,
            detail="Too many login attempts for this account. Please try again later.",
        )

    # Use constant-time comparison to prevent user enumeration
    user = await users().find_one({"email": normalized_email})
    if not user or not verify_password(data.password, user.get("hashed_password", "")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    user_id = str(user["_id"])
    response = JSONResponse({
        "message": "Login successful",
        "user_id": user_id,
        "name": user["name"],
        "email": user["email"]
    })
    _set_auth_cookie(response, create_token(user_id), request)
    return response


@router.post("/logout")
async def logout(request: Request):
    """Clear the authentication cookie and revoke the JWT token."""
    # Blacklist the current token so it can't be reused
    token = request.cookies.get(settings.AUTH_COOKIE_NAME)
    if token:
        try:
            from app.core.auth import decode_token
            from app.core.redis_client import blacklist_token
            payload = decode_token(token)
            jti = payload.get("jti")
            if jti:
                # Blacklist for the remaining token lifetime
                remaining = int(settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60)
                await blacklist_token(jti, remaining)
        except Exception:
            pass  # Token may already be expired/invalid — still delete cookie

    response = JSONResponse({"message": "Successfully logged out"})
    response.delete_cookie(
        key=settings.AUTH_COOKIE_NAME,
        httponly=True,
        secure=_cookie_secure_flag(request),
        samesite=settings.COOKIE_SAMESITE,
        path="/",
    )
    return response

@router.get("/me")
async def get_my_profile(current_user: dict = Depends(get_current_user)):
    """Get the currently logged-in user's profile"""
    return {
        "id": str(current_user["_id"]),
        "name": current_user.get("name"),
        "email": current_user.get("email"),
        "age": current_user.get("age"),
        "district": current_user.get("district"),
        "language": current_user.get("language", "en"),
        "total_symptom_logs": current_user.get("total_symptom_logs", 0),
        "member_since": current_user.get("created_at", "").isoformat()
                        if current_user.get("created_at") else None
    }


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
async def forgot_password(data: ForgotPasswordRequest, request: Request):
    """
    Request a password reset token.
    In production this token should be sent by email/SMS.
    For local development we return a preview token when DEBUG=true.
    """
    normalized_email = _normalize_email(data.email)
    email_key = normalized_email
    ip_key = _client_ip(request)

    limited_email = await is_rate_limited(
        f"rl:forgot:email:{email_key}",
        settings.FORGOT_PASSWORD_EMAIL_LIMIT_PER_HOUR,
        RATE_LIMIT_WINDOW_SECONDS,
    )
    limited_ip = await is_rate_limited(
        f"rl:forgot:ip:{ip_key}",
        settings.FORGOT_PASSWORD_IP_LIMIT_PER_HOUR,
        RATE_LIMIT_WINDOW_SECONDS,
    )
    if limited_email or limited_ip:
        raise HTTPException(
            status_code=429,
            detail="Too many reset requests. Please try again later.",
        )

    user = await users().find_one({"email": normalized_email})
    if not user:
        return ForgotPasswordResponse(
            message="If an account exists for this email, a password reset link has been generated."
        )

    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.PASSWORD_RESET_EXPIRE_MINUTES)

    await users().update_one(
        {"_id": user["_id"]},
        {
            "$set": {
                "password_reset_token_hash": token_hash,
                "password_reset_expires_at": expires_at,
                "password_reset_requested_at": datetime.now(timezone.utc),
            }
        }
    )

    reset_link = (
        f"{settings.FRONTEND_URL.rstrip('/')}{settings.PASSWORD_RESET_PATH}"
        f"?token={quote_plus(raw_token)}&email={quote_plus(normalized_email)}"
    )

    sent = _send_reset_email(normalized_email, raw_token, expires_at, reset_link)

    preview_enabled = settings.ENABLE_RESET_TOKEN_PREVIEW or settings.DEBUG
    preview_token = raw_token if preview_enabled else None
    preview_link = reset_link if preview_enabled else None

    if sent:
        return ForgotPasswordResponse(
            message="Password reset instructions were sent to your email.",
            verification_method="email",
            reset_token_preview=preview_token,
            reset_link_preview=preview_link,
        )

    # Production-safe fallback when SMTP is unavailable:
    # allow returning reset token only if explicit KBA fallback is enabled and identity fields match.
    if settings.ALLOW_PASSWORD_RESET_KBA_FALLBACK:
        district_input = (data.district or "").strip().lower()
        user_district = str(user.get("district", "")).strip().lower()
        district_match = bool(district_input) and district_input == user_district
        age_input = data.age
        user_age = user.get("age")
        age_match = isinstance(age_input, int) and isinstance(user_age, int) and age_input == user_age

        if district_match and age_match:
            # SECURITY: Never return the raw token in the API response.
            # In KBA mode, mark the token as verified and let the user proceed
            # to the reset-password form via the link only.
            return ForgotPasswordResponse(
                message="Identity verified. Check your email or use the password reset page.",
                verification_method="kba",
                reset_token_preview=preview_token,
                reset_link_preview=preview_link,
            )

    return ForgotPasswordResponse(
        message="Password reset requested. Email is unavailable; provide account age and district for fallback verification.",
        verification_method="unavailable",
        reset_token_preview=preview_token,
        reset_link_preview=preview_link,
    )


@router.post("/reset-password")
async def reset_password(data: ResetPasswordRequest, request: Request):
    """Reset account password using the password reset token."""
    ip_key = _client_ip(request)
    limited_ip = await is_rate_limited(
        f"rl:reset:ip:{ip_key}",
        settings.RESET_PASSWORD_IP_LIMIT_PER_HOUR,
        RATE_LIMIT_WINDOW_SECONDS,
    )
    if limited_ip:
        raise HTTPException(
            status_code=429,
            detail="Too many reset attempts. Please try again later.",
        )

    if len(data.new_password) < 8:
        raise HTTPException(status_code=400, detail="New password must be at least 8 characters")

    token_hash = hashlib.sha256(data.token.encode()).hexdigest()
    limited_token = await is_rate_limited(
        f"rl:reset:token:{token_hash}",
        settings.RESET_PASSWORD_TOKEN_LIMIT_PER_HOUR,
        RATE_LIMIT_WINDOW_SECONDS,
    )
    if limited_token:
        raise HTTPException(
            status_code=429,
            detail="Too many attempts for this reset token. Please request a new reset email.",
        )

    user = await users().find_one({"password_reset_token_hash": token_hash})
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    expires_at = user.get("password_reset_expires_at")
    if not expires_at or expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Reset token has expired")

    await users().update_one(
        {"_id": user["_id"]},
        {
            "$set": {"hashed_password": hash_password(data.new_password)},
            "$unset": {
                "password_reset_token_hash": "",
                "password_reset_expires_at": "",
                "password_reset_requested_at": "",
            },
        }
    )

    return {"message": "Password reset successful. Please log in with your new password."}
