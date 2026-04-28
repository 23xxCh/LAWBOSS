"""认证 API 路由"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.user import User
from ..schemas.auth import LoginRequest, LoginResponse, RegisterRequest, UserInfo, TokenData
from ..services import auth_service

router = APIRouter(tags=["认证"])
security = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """获取当前认证用户（依赖注入）"""
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未提供认证凭据")
    token_data = auth_service.decode_access_token(credentials.credentials)
    if not token_data:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效或过期的令牌")
    user = db.query(User).filter(User.username == token_data.username).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在或已禁用")
    return user


def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User | None:
    """可选认证（未提供 token 时返回 None）"""
    if not credentials:
        return None
    token_data = auth_service.decode_access_token(credentials.credentials)
    if not token_data:
        return None
    return db.query(User).filter(User.username == token_data.username).first()


def require_role(*roles: str):
    """角色权限检查装饰器"""
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="权限不足")
        return current_user
    return role_checker


@router.post("/auth/login", response_model=LoginResponse, summary="用户登录")
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    """用户登录，返回 JWT 令牌"""
    user = db.query(User).filter(User.username == request.username).first()
    if not user or not auth_service.verify_password(request.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户已禁用")

    access_token = auth_service.create_access_token(
        data={"sub": user.username, "role": user.role}
    )
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserInfo(id=user.id, username=user.username, role=user.role),
    )


@router.post("/auth/register", response_model=UserInfo, summary="用户注册")
async def register(request: RegisterRequest, db: Session = Depends(get_db)):
    """用户注册"""
    # 检查用户名是否已存在
    existing = db.query(User).filter(User.username == request.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="用户名已存在")
    if request.email:
        existing_email = db.query(User).filter(User.email == request.email).first()
        if existing_email:
            raise HTTPException(status_code=400, detail="邮箱已注册")

    user = auth_service.create_user(request.username, request.password, role="user", email=request.email)
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserInfo(id=user.id, username=user.username, role=user.role)


@router.get("/auth/me", response_model=UserInfo, summary="获取当前用户信息")
async def get_me(current_user: User = Depends(get_current_user)):
    """获取当前登录用户信息"""
    return UserInfo(id=current_user.id, username=current_user.username, role=current_user.role)
