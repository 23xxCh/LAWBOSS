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
    # 本地导入确保所有模型注册到 Base.metadata
    from . import models  # noqa: F401
    Base.metadata.create_all(bind=engine)

    # SQLite 迁移：为现有表添加新列
    if _is_sqlite:
        _migrate_sqlite_schema()

    # 迁移静态文件数据到数据库
    _migrate_static_data()


def _migrate_sqlite_schema():
    """SQLite 模式迁移：添加缺失的列"""
    from sqlalchemy import text, inspect

    inspector = inspect(engine)
    tables = inspector.get_table_names()

    if "users" in tables:
        existing_columns = {col["name"] for col in inspector.get_columns("users")}
        new_columns = [
            ("stripe_customer_id", "VARCHAR(100)"),
            ("subscription_status", "VARCHAR(20) DEFAULT 'free'"),
            ("subscription_tier", "VARCHAR(20) DEFAULT 'free'"),
            ("trial_ends_at", "DATETIME"),
            ("quota_checks_monthly", "INTEGER DEFAULT 50"),
        ]

        with engine.connect() as conn:
            for col_name, col_type in new_columns:
                if col_name not in existing_columns:
                    conn.execute(text(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}"))
            conn.commit()

    if "stripe_events" not in tables:
        with engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE stripe_events (
                    id VARCHAR(100) PRIMARY KEY,
                    event_type VARCHAR(50) NOT NULL,
                    processed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    customer_id VARCHAR(100),
                    subscription_id VARCHAR(100)
                )
            """))
            conn.execute(text("CREATE INDEX ix_stripe_events_customer_id ON stripe_events(customer_id)"))
            conn.execute(text("CREATE INDEX ix_stripe_events_subscription_id ON stripe_events(subscription_id)"))
            conn.commit()


def _migrate_static_data():
    """迁移静态文件数据到数据库

    迁移策略:
    1. 检测 banned_words 表是否有数据
    2. 无数据则从静态文件迁移
    3. 迁移后保留原文件作为备份
    """
    from sqlalchemy import text, inspect
    import json
    import uuid

    inspector = inspect(engine)
    tables = inspector.get_table_names()

    # 检查新表是否存在
    required_tables = ["banned_words", "word_replacements", "regulations", "user_feedbacks", "optimization_suggestions"]
    for t in required_tables:
        if t not in tables:
            return  # 表还没创建，下次 init_db 会处理

    with engine.connect() as conn:
        # 检查是否已有数据
        result = conn.execute(text("SELECT COUNT(*) FROM banned_words"))
        count = result.scalar()
        if count > 0:
            return  # 已迁移过

        # 迁移禁用词
        _migrate_banned_words(conn, text)

        # 迁移替换建议
        _migrate_replacements(conn, text)

        # 迁移法规
        _migrate_regulations(conn, text)

        conn.commit()


def _migrate_banned_words(conn, text):
    """迁移禁用词文件到数据库"""
    import json
    import uuid
    from pathlib import Path
    from datetime import datetime, timezone

    data_dir = BASE_DIR / "data" / "banned_words"
    if not data_dir.exists():
        return

    now = datetime.now(timezone.utc).isoformat()

    for filepath in data_dir.glob("*.txt"):
        # 解析文件名: {market}_{category}_{type}.txt 或 absolute_terms.txt
        parts = filepath.stem.split("_")
        if len(parts) >= 3:
            market = parts[0].upper()
            category = parts[1]
            violation_type = "_".join(parts[2:])
        elif filepath.stem == "absolute_terms":
            market = "ALL"
            category = "all"
            violation_type = "absolute_term"
        else:
            continue

        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                word = line.strip()
                if not word or word.startswith("#"):
                    continue

                conn.execute(text("""
                    INSERT OR IGNORE INTO banned_words
                    (id, word, violation_type, market, category, severity, is_active, version, created_at, updated_at)
                    VALUES (:id, :word, :violation_type, :market, :category, 50, 1, 1, :now, :now)
                """), {
                    "id": str(uuid.uuid4()),
                    "word": word,
                    "violation_type": violation_type,
                    "market": market,
                    "category": category,
                    "now": now,
                })


def _migrate_replacements(conn, text):
    """迁移替换建议文件到数据库"""
    import json
    import uuid
    from pathlib import Path
    from datetime import datetime, timezone

    data_dir = BASE_DIR / "data" / "replacements"
    if not data_dir.exists():
        return

    now = datetime.now(timezone.utc).isoformat()

    for filepath in data_dir.glob("*.json"):
        # 解析文件名: {market}_{category}.json
        parts = filepath.stem.split("_")
        if len(parts) < 2:
            continue
        market = parts[0].upper()
        category = parts[1]

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            for item in data:
                if "original" in item and "replacement" in item:
                    conn.execute(text("""
                        INSERT OR IGNORE INTO word_replacements
                        (id, original_word, replacement, market, category, version, is_active, created_at, updated_at)
                        VALUES (:id, :original, :replacement, :market, :category, 1, 1, :now, :now)
                    """), {
                        "id": str(uuid.uuid4()),
                        "original": item["original"],
                        "replacement": item["replacement"],
                        "market": market,
                        "category": category,
                        "now": now,
                    })
        except Exception:
            continue


def _migrate_regulations(conn, text):
    """迁移法规文件到数据库"""
    import json
    import uuid
    from pathlib import Path
    from datetime import datetime, timezone

    data_dir = BASE_DIR / "data" / "regulations"
    if not data_dir.exists():
        return

    now = datetime.now(timezone.utc).isoformat()

    for filepath in data_dir.glob("*.json"):
        # 解析文件名: {market}_{category}.json
        parts = filepath.stem.split("_")
        if len(parts) < 2:
            continue
        market = parts[0].upper()
        category = parts[1]

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            title = data.get("title", f"{market} {category} 法规")
            content = json.dumps(data, ensure_ascii=False, indent=2)

            conn.execute(text("""
                INSERT OR IGNORE INTO regulations
                (id, market, category, title, content, version, is_active, created_at, updated_at)
                VALUES (:id, :market, :category, :title, :content, 1, 1, :now, :now)
            """), {
                "id": str(uuid.uuid4()),
                "market": market,
                "category": category,
                "title": title,
                "content": content,
                "now": now,
            })
        except Exception:
            continue
