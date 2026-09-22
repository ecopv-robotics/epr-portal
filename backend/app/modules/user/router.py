from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import create_access_token, verify_password
from app.dependencies import get_current_user
from app.models import User
from app.schemas import LoginRequest, TokenResponse, UserOut

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(
        select(User).where(or_(User.username == payload.account, User.email == payload.account, User.phone == payload.account))
    )
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="账号或密码错误")
    if user.customer_profile and not user.customer_profile.active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已停用")
    return TokenResponse(access_token=create_access_token(user.id), user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user
