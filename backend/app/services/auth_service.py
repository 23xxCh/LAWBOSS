"""认证服务 — JWT + 密码哈希"""
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from ..config import JWT_SECRET_KEY, JWT_ALGORITHM, JWT_ACCESS_TOKEN_EXPIRE_MINUTES
from ..models.user import User
from ..schemas.auth import TokenData

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[TokenData]:
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        username: str = payload.get("sub")
        role: str = payload.get("role", "user")
        if username is None:
            return None
        return TokenData(username=username, role=role)
    except JWTError:
        return None


def create_user(username: str, password: str, role: str = "user", email: Optional[str] = None) -> User:
    """创建用户对象（未保存到数据库）"""
    return User(
        id=str(uuid.uuid4()),
        username=username,
        email=email,
        hashed_password=hash_password(password),
        role=role,
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )


# 预置管理员账户
DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "crossguard2024"  # 首次部署后请修改
