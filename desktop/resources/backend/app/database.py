"""数据库连接与会话管理

支持 PostgreSQL（生产）和 SQLite（开发/测试）通过 DATABASE_URL 环境变量切换：
- PostgreSQL: DATABASE_URL=postgresql://user:pass@host:5432/crossguard
- SQLite:     DATABASE_URL=sqlite:///./db/crossguard.db (默认)
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from pathlib import Path

from .config import BASE_DIR, DATABASE_URL

# 确定数据库 URL
_db_url = DATABASE_URL
_is_sqlite = _db_url.startswith("sqlite")

# SQLite 需要确保目录存在
if _is_sqlite:
    db_dir = BASE_DIR / "db"
    db_dir.mkdir(exist_ok=True)

engine = create_engine(
    _db_url,
    connect_args={"check_same_thread": False} if _is_sqlite else {},
    pool_pre_ping=True,
    pool_size=10 if not _is_sqlite else 5,
    max_overflow=20 if not _is_sqlite else 0,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    """获取数据库会话（FastAPI 依赖注入）"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """初始化数据库，创建所有表"""
    Base.metadata.create_all(bind=engine)
