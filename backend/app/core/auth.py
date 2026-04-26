"""
NirovaAI — Authentication
==========================
Handles user passwords and JWT tokens.

How it works:
1. User registers → password gets hashed (never stored plain)
2. User logs in → we check hash → return JWT token
3. Every protected request → token verified → user identified
"""

from datetime import datetime, timedelta, timezone
import uuid
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status, Request
from app.core.config import settings
from app.core.database import users
from bson import ObjectId

# bcrypt is the industry standard for password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(plain_password: str) -> str:
    """Turn a plain password into a secure hash"""
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed: str) -> bool:
    """Check if a plain password matches its stored hash"""
    return pwd_context.verify(plain_password, hashed)


def create_token(user_id: str) -> str:
    """
    Create a JWT token for a logged-in user.
    The token expires after 7 days (configured in settings).
    Includes a unique JTI (JWT ID) for revocation support.
    """
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {
        "sub": user_id,      # subject = user ID
        "exp": expire,       # expiration time
        "jti": str(uuid.uuid4()),  # unique token ID for revocation
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict:
    """
    Verify and decode a JWT token.
    Raises 401 if token is invalid or expired.
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is invalid or has expired. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    request: Request
):
    """
    FastAPI dependency — call this in any endpoint that requires login.
    Extracts the user token from the HttpOnly cookie.
    """
    token = request.cookies.get(settings.AUTH_COOKIE_NAME)
    if not token:
        # Fallback to Authorization header if present (useful for API clients or swagger)
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated"
            )

    # Verify the token
    payload = decode_token(token)

    # Check if token has been revoked (blacklisted)
    token_jti = payload.get("jti")
    if token_jti:
        try:
            from app.core.redis_client import is_token_blacklisted
            if await is_token_blacklisted(token_jti):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has been revoked. Please log in again."
                )
        except ImportError:
            pass  # Redis client not available, skip blacklist check

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is missing user information"
        )

    # Look up the user in MongoDB
    user = await users().find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found"
        )

    return user
