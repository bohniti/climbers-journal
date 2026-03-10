from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, status
from jose import jwt
from pydantic import BaseModel

from app.config import get_settings

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest):
    settings = get_settings()
    if req.username != settings.app_username or req.password != settings.app_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    expire = datetime.now(timezone.utc) + timedelta(days=settings.jwt_expire_days)
    token = jwt.encode(
        {"sub": req.username, "exp": expire},
        settings.jwt_secret,
        algorithm="HS256",
    )
    return TokenResponse(access_token=token)
