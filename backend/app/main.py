"""出海法盾 CrossGuard — FastAPI 应用入口"""
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import (
    BASE_DIR,
    DATA_DIR,
    API_V1_PREFIX,
    PROJECT_NAME,
    PROJECT_DESCRIPTION,
    VERSION,
    JWT_SECRET_KEY,
)
from .services.compliance_checker import ComplianceChecker
from .database import init_db
from .routers import check, market, report, image, auth, platform, feedback, regulation, erp, dashboard

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时初始化，关闭时清理"""
    # 安全检查：JWT 密钥不能使用默认值
    if JWT_SECRET_KEY == "crossguard-dev-secret-change-in-production":
        logger.warning(
            "⚠️  JWT_SECRET_KEY 使用默认值，生产环境极不安全！"
            "请设置环境变量 JWT_SECRET_KEY 为强随机字符串。"
        )

    # 初始化数据库
    init_db()
    # 初始化合规检测引擎
    checker = ComplianceChecker(data_dir=DATA_DIR)
    app.state.checker = checker
    # 初始化默认管理员
    _init_default_admin()
    yield
    # 清理（如有需要）


def _init_default_admin():
    """创建默认管理员账户（如不存在）"""
    from .database import SessionLocal
    from .models.user import User
    from .services.auth_service import create_user, DEFAULT_ADMIN_USERNAME, DEFAULT_ADMIN_PASSWORD
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.username == DEFAULT_ADMIN_USERNAME).first()
        if not existing:
            admin = create_user(DEFAULT_ADMIN_USERNAME, DEFAULT_ADMIN_PASSWORD, role="admin")
            db.add(admin)
            db.commit()
    finally:
        db.close()


app = FastAPI(
    title=PROJECT_NAME,
    description=PROJECT_DESCRIPTION,
    version=VERSION,
    lifespan=lifespan,
)

# CORS 配置 — 生产环境应通过 CORS_ORIGINS 环境变量限制
_cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(check.router, prefix=API_V1_PREFIX)
app.include_router(market.router, prefix=API_V1_PREFIX)
app.include_router(report.router, prefix=API_V1_PREFIX)
app.include_router(image.router, prefix=API_V1_PREFIX)
app.include_router(auth.router, prefix=API_V1_PREFIX)
app.include_router(platform.router, prefix=API_V1_PREFIX)
app.include_router(feedback.router, prefix=API_V1_PREFIX)
app.include_router(regulation.router, prefix=API_V1_PREFIX)
app.include_router(erp.router, prefix=API_V1_PREFIX)
app.include_router(dashboard.router, prefix=API_V1_PREFIX)


@app.get("/", tags=["系统"])
async def root():
    """根路径，返回项目信息"""
    return {
        "name": PROJECT_NAME,
        "description": PROJECT_DESCRIPTION,
        "version": VERSION,
        "docs": "/docs",
    }
