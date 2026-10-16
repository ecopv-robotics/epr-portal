import hashlib
import hmac
import re
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import create_access_token, hash_password, verify_password
from app.core.verification import send_verification_code
from app.dependencies import get_current_user
from app.models import CustomerProfile, CustomerType, User, UserRole, VerificationCode
from app.schemas import (
    LoginRequest, RegisterRequest, TokenResponse, UserOut,
    VerificationCodeRequest, VerificationCodeResponse,
)

router = APIRouter(prefix="/auth", tags=["认证"])
EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
PHONE_PATTERN = re.compile(r"^\+?[1-9]\d{7,14}$")


def normalize_account(value: str) -> tuple[str, str]:
    account = value.strip()
    if EMAIL_PATTERN.fullmatch(account):
        return "email", account.lower()
    phone = re.sub(r"[\s()-]", "", account)
    if PHONE_PATTERN.fullmatch(phone):
        return "phone", phone
    raise HTTPException(status_code=422, detail="请输入有效的手机号或邮箱")


def code_hash(target: str, code: str) -> str:
    secret = get_settings().jwt_secret
    return hmac.new(secret.encode(), f"{target}:{code}".encode(), hashlib.sha256).hexdigest()


def unique_username(db: Session, channel: str, account: str) -> str:
    base = account.split("@", 1)[0] if channel == "email" else account[-8:]
    base = re.sub(r"[^a-zA-Z0-9_.-]", "", base)[:80] or "user"
    candidate = base
    while db.scalar(select(User.id).where(User.username == candidate)):
        candidate = f"{base[:72]}-{secrets.token_hex(3)}"
    return candidate


@router.post("/verification-codes", response_model=VerificationCodeResponse)
def request_verification_code(payload: VerificationCodeRequest, db: Session = Depends(get_db)):
    channel, account = normalize_account(payload.account)
    settings = get_settings()
    existing = db.scalar(select(User.id).where(User.email == account if channel == "email" else User.phone == account))
    if existing:
        raise HTTPException(status_code=409, detail="该手机号或邮箱已注册")

    now = datetime.now(timezone.utc)
    latest = db.scalar(
        select(VerificationCode)
        .where(VerificationCode.target == account, VerificationCode.purpose == "REGISTER")
        .order_by(VerificationCode.created_time.desc())
        .limit(1)
    )
    if latest and latest.created_time:
        created = latest.created_time if latest.created_time.tzinfo else latest.created_time.replace(tzinfo=timezone.utc)
        elapsed = (now - created).total_seconds()
        if elapsed < settings.verification_code_resend_seconds:
            retry_after = max(1, int(settings.verification_code_resend_seconds - elapsed))
            raise HTTPException(status_code=429, detail=f"验证码发送过于频繁，请 {retry_after} 秒后再试")

    code = f"{secrets.randbelow(1_000_000):06d}"
    record = VerificationCode(
        target=account, channel=channel, purpose="REGISTER", code_hash=code_hash(account, code),
        expires_at=now + timedelta(minutes=settings.verification_code_expire_minutes),
    )
    if not send_verification_code(channel, account, code) and not settings.verification_debug:
        raise HTTPException(status_code=503, detail="验证码暂时无法发送，请稍后重试")
    db.add(record)
    db.commit()
    return VerificationCodeResponse(
        message="验证码已发送", retry_after=settings.verification_code_resend_seconds,
        debug_code=code if settings.verification_debug else None,
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    channel, account = normalize_account(payload.account)
    existing = db.scalar(select(User.id).where(User.email == account if channel == "email" else User.phone == account))
    if existing:
        raise HTTPException(status_code=409, detail="该手机号或邮箱已注册")

    now = datetime.now(timezone.utc)
    record = db.scalar(
        select(VerificationCode)
        .where(
            VerificationCode.target == account,
            VerificationCode.channel == channel,
            VerificationCode.purpose == "REGISTER",
            VerificationCode.used_at.is_(None),
            VerificationCode.expires_at > now,
        )
        .order_by(VerificationCode.created_time.desc())
        .limit(1)
    )
    settings = get_settings()
    if not record:
        raise HTTPException(status_code=400, detail="验证码无效或已过期，请重新获取")
    if record.attempts >= settings.verification_code_max_attempts:
        raise HTTPException(status_code=400, detail="验证码尝试次数过多，请重新获取")
    if not hmac.compare_digest(record.code_hash, code_hash(account, payload.verification_code)):
        record.attempts += 1
        db.commit()
        raise HTTPException(status_code=400, detail="验证码错误")

    user = User(
        username=unique_username(db, channel, account),
        email=account if channel == "email" else None,
        phone=account if channel == "phone" else None,
        password_hash=hash_password(payload.password), role=UserRole.CUSTOMER,
    )
    display_name = account.split("@", 1)[0] if channel == "email" else f"用户{account[-4:]}"
    user.customer_profile = CustomerProfile(customer_type=CustomerType.DIRECT, name=display_name, contact_phone=user.phone)
    record.used_at = now
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="该手机号或邮箱已注册")
    db.refresh(user)
    return TokenResponse(access_token=create_access_token(user.id), user=UserOut.model_validate(user))


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
