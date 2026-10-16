from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models import User, UserRole

bearer = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录或登录已过期")
    try:
        user_id = decode_access_token(credentials.credentials)
    except (InvalidTokenError, ValueError, KeyError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录凭证无效") from None
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在")
    return user


def get_current_admin(user: User = Depends(get_current_user)) -> User:
    if user.role not in (UserRole.ADMIN, UserRole.STAFF):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要管理员或员工权限")
    return user
