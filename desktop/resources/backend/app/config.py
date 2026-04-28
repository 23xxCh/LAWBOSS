"""
配置文件
"""
import os
from pathlib import Path

# 项目根目录
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"

# 法规数据路径
REGULATIONS_DIR = DATA_DIR / "regulations"
BANNED_WORDS_DIR = DATA_DIR / "banned_words"
CASES_DIR = DATA_DIR / "cases"

# 支持的法规市场
SUPPORTED_MARKETS = ["EU", "US", "SEA_SG", "SEA_TH", "SEA_MY"]

# 支持的产品类别
SUPPORTED_CATEGORIES = {
    "EU": ["化妆品", "电子产品", "食品", "玩具", "纺织品"],
    "US": ["化妆品", "电子产品", "食品", "膳食补充剂"],
    "SEA_SG": ["化妆品", "电子产品", "食品", "膳食补充剂"],
    "SEA_TH": ["化妆品", "电子产品", "食品", "膳食补充剂"],
    "SEA_MY": ["化妆品", "电子产品", "食品", "膳食补充剂"],
}

# 风险等级
RISK_LEVELS = {
    "high": {"min": 70, "label": "高风险", "description": "建议立即整改，否则可能面临下架/罚款"},
    "medium": {"min": 40, "label": "中风险", "description": "存在违规可能，建议修改"},
    "low": {"min": 0, "label": "低风险", "description": "基本合规，可进一步优化"}
}

# API配置
API_V1_PREFIX = "/api/v1"
PROJECT_NAME = "出海法盾 - CrossGuard"
PROJECT_DESCRIPTION = "跨境电商智能合规审查平台"
VERSION = "0.3.0"

# 数据库配置
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'db' / 'crossguard.db'}")

# JWT 配置
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "crossguard-dev-secret-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

# LLM 配置
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_API_BASE = os.getenv("LLM_API_BASE", "https://api.openai.com/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")

# Webhook 配置
PATROL_WEBHOOK_URL = os.getenv("PATROL_WEBHOOK_URL", "")
