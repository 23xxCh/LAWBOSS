"""
CrossGuard MCP HTTP Server — 出海法盾合规检测 MCP HTTP 服务

为 AI Agent (Claude Code, OpenClaw 等) 提供 HTTP/SSE 接口的合规检测工具。

用法:
  uv run crossguard_mcp_http.py

环境变量:
  CROSSGUARD_API_URL: 后端 API 地址 (默认: http://localhost:8000)
  CROSSGUARD_API_KEY: API Key 用于认证 (可选，用于托管服务)
"""
import os
import sys
import json
import logging
from pathlib import Path
from typing import Optional
from contextvars import ContextVar

# 将 backend 加入路径以复用合规检测引擎
_backend_dir = Path(__file__).resolve().parent.parent / "backend"
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

from starlette.applications import Starlette
from starlette.routing import Route
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware

from mcp.server.fastmcp import FastMCP
from mcp.server.sse import SseServerTransport

from app.services.compliance_checker import ComplianceChecker
from app.config import SUPPORTED_MARKETS, SUPPORTED_CATEGORIES, DATA_DIR, REGULATIONS_DIR, CASES_DIR
from utils import report_to_dict

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 环境变量
API_URL = os.getenv("CROSSGUARD_API_URL", "http://localhost:8000")
REQUIRE_API_KEY = os.getenv("CROSSGUARD_REQUIRE_API_KEY", "false").lower() == "true"

# 初始化合规检测引擎
_checker = ComplianceChecker(data_dir=DATA_DIR)

# 市场和类别的文件路径映射
_MARKET_SLUG = {"EU": "eu", "US": "us", "SEA_SG": "sea", "SEA_TH": "sea", "SEA_MY": "sea"}
_CATEGORY_SLUG = {"化妆品": "cosmetics", "电子产品": "electronics", "食品": "food",
                  "玩具": "toys", "纺织品": "textiles", "膳食补充剂": "supplements"}
_REPLACEMENTS_DIR = DATA_DIR / "replacements"

# Context variable for user info (set by auth middleware)
current_user: ContextVar[Optional[dict]] = ContextVar("current_user", default=None)

# 创建 FastMCP 实例
mcp = FastMCP("CrossGuard", instructions="""\
CrossGuard (出海法盾) 跨境电商智能合规审查工具。支持以下市场：
- EU (欧盟)、US (美国)、SEA_SG (新加坡)、SEA_TH (泰国)、SEA_MY (马来西亚)

检测内容包括：医疗宣称、绝对化用语、虚假广告、缺失标签、禁用成分。

HTTP Endpoint: 使用 API Key 进行认证，配额限制生效。
""")


@mcp.tool(description="检测产品描述在目标市场的合规性，返回风险评分、违规项、修改建议和合规版本")
def check_compliance(
    description: str,
    market: str = "EU",
    category: str = "化妆品",
) -> str:
    """检测产品描述合规性

    Args:
        description: 产品描述文本（如广告文案、成分表等）
        market: 目标市场代码 (EU/US/SEA_SG/SEA_TH/SEA_MY)
        category: 产品类别 (化妆品/电子产品/食品/玩具/纺织品/膳食补充剂)

    Returns:
        JSON 格式的合规检测报告
    """
    # 输入验证
    if not description or not description.strip():
        return json.dumps({"error": "description 不能为空", "code": "INVALID_INPUT"}, ensure_ascii=False)

    if market not in SUPPORTED_MARKETS:
        return json.dumps({
            "error": f"不支持的市场: {market}",
            "supported_markets": list(SUPPORTED_MARKETS),
            "code": "INVALID_MARKET"
        }, ensure_ascii=False)

    if category not in SUPPORTED_CATEGORIES.get(market, []):
        return json.dumps({
            "error": f"市场 {market} 不支持类别: {category}",
            "supported_categories": SUPPORTED_CATEGORIES.get(market, []),
            "code": "INVALID_CATEGORY"
        }, ensure_ascii=False)

    # 配额检查 (如果是托管服务)
    user = current_user.get()
    if user and REQUIRE_API_KEY:
        try:
            import httpx
            resp = httpx.post(
                f"{API_URL}/api/v1/mcp/quota/check",
                headers={"Authorization": f"Bearer {user.get('api_key')}"},
                json={"quota_type": "checks"},
                timeout=5.0
            )
            if resp.status_code == 429:
                return json.dumps({
                    "error": "配额已用尽，请升级订阅",
                    "code": "QUOTA_EXCEEDED",
                    "upgrade_url": "https://crossguard.ai/pricing"
                }, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"Quota check failed: {e}")

    # 执行检测
    report = _checker.check_text(
        description=description,
        product_category=category,
        target_market=market,
    )

    # 记录使用量 (如果是托管服务)
    if user and REQUIRE_API_KEY:
        try:
            import httpx
            httpx.post(
                f"{API_URL}/api/v1/mcp/quota/increment",
                headers={"Authorization": f"Bearer {user.get('api_key')}"},
                json={"quota_type": "checks"},
                timeout=5.0
            )
        except Exception as e:
            logger.warning(f"Quota increment failed: {e}")

    return json.dumps(report_to_dict(report), ensure_ascii=False, indent=2)


@mcp.tool(description="列出所有支持的目标市场及其产品类别，以及必需标签和认证信息")
def list_markets() -> str:
    """列出所有支持的市场和类别"""
    result = []
    for market in SUPPORTED_MARKETS:
        categories = SUPPORTED_CATEGORIES.get(market, [])
        market_info = {"code": market, "categories": []}
        for cat in categories:
            labels = _checker.get_required_labels(cat, market)
            certs = _checker.get_required_certifications(cat, market)
            market_info["categories"].append({
                "name": cat,
                "required_labels": labels,
                "required_certifications": certs,
            })
        result.append(market_info)
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.resource("regulation://{market}/{category}",
              description="获取指定市场和产品类别的法规要求，含核心条款和关键要求")
def get_regulation(market: str, category: str) -> str:
    """获取法规要求"""
    if market not in SUPPORTED_MARKETS:
        return json.dumps({"error": f"不支持的市场: {market}", "supported": SUPPORTED_MARKETS})
    if category not in SUPPORTED_CATEGORIES.get(market, []):
        return json.dumps({"error": f"市场 {market} 不支持类别: {category}"})

    slug = _MARKET_SLUG.get(market, market.lower())
    cat_slug = _CATEGORY_SLUG.get(category, category)
    file_path = REGULATIONS_DIR / f"{slug}_{cat_slug}.json"
    if file_path.exists():
        return file_path.read_text(encoding="utf-8")

    return json.dumps({"error": f"暂未收录 {market}/{category} 法规数据"})


@mcp.resource("cases://{id}",
              description="获取违规案例详情，包含案例描述、违规内容和处罚信息")
def get_case(id: str) -> str:
    """获取违规案例"""
    cases_file = CASES_DIR / "violations.json"
    if not cases_file.exists():
        return json.dumps({"error": "案例数据不存在"})

    try:
        cases = json.loads(cases_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return json.dumps({"error": "案例数据解析失败"})

    # 按 ID 索引查找（ID 从 1 开始）
    try:
        idx = int(id) - 1
        if 0 <= idx < len(cases):
            return json.dumps(cases[idx], ensure_ascii=False, indent=2)
    except ValueError:
        pass

    # 按标题搜索
    for case in cases:
        if case.get("title", "").find(id) != -1:
            return json.dumps(case, ensure_ascii=False, indent=2)

    return json.dumps({
        "error": f"案例 '{id}' 未找到",
        "available": len(cases),
        "hint": f"使用数字 ID (1-{len(cases)}) 或案例标题关键词查询",
    })


@mcp.resource("replacements://{market}/{category}",
              description="获取指定市场的合规替换词映射，帮助改写违规描述为合规版本")
def get_replacements(market: str, category: str) -> str:
    """获取替换词映射"""
    if market not in SUPPORTED_MARKETS:
        return json.dumps({"error": f"不支持的市场: {market}", "supported": SUPPORTED_MARKETS})

    slug = _MARKET_SLUG.get(market, market.lower())
    cat_slug = _CATEGORY_SLUG.get(category, category)
    file_path = _REPLACEMENTS_DIR / f"{slug}_{cat_slug}.json"
    if file_path.exists():
        return file_path.read_text(encoding="utf-8")

    return json.dumps({"error": f"暂未收录 {market}/{category} 替换词数据"})


# ===== HTTP 认证中间件 =====

class APIKeyMiddleware(BaseHTTPMiddleware):
    """API Key 认证中间件"""

    async def dispatch(self, request: Request, call_next):
        # 健康检查端点不需要认证
        if request.url.path in ["/health", "/"]:
            return await call_next(request)

        # 静态资源不需要认证
        if request.url.path.startswith("/static/"):
            return await call_next(request)

        # 如果不需要 API Key，直接放行
        if not REQUIRE_API_KEY:
            return await call_next(request)

        # 获取 API Key
        api_key = None

        # 从 Authorization header 获取
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            api_key = auth_header[7:]
        elif auth_header.startswith("ApiKey "):
            api_key = auth_header[7:]

        # 从 query 参数获取
        if not api_key:
            api_key = request.query_params.get("api_key")

        # 从 cookie 获取
        if not api_key:
            api_key = request.cookies.get("api_key")

        if not api_key:
            return JSONResponse(
                {"error": "缺少 API Key", "code": "UNAUTHORIZED"},
                status_code=401
            )

        # 验证 API Key
        try:
            import httpx
            resp = httpx.get(
                f"{API_URL}/api/v1/mcp/auth/verify",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=5.0
            )

            if resp.status_code != 200:
                return JSONResponse(
                    {"error": "无效的 API Key", "code": "UNAUTHORIZED"},
                    status_code=401
                )

            user_data = resp.json()
            current_user.set({"api_key": api_key, **user_data})

        except Exception as e:
            logger.error(f"API Key verification failed: {e}")
            return JSONResponse(
                {"error": "认证服务不可用", "code": "AUTH_SERVICE_ERROR"},
                status_code=503
            )

        return await call_next(request)


# ===== HTTP 端点 =====

async def health_check(request: Request):
    """健康检查端点"""
    return JSONResponse({
        "status": "healthy",
        "service": "CrossGuard MCP HTTP Server",
        "version": "0.2.0",
        "require_api_key": REQUIRE_API_KEY
    })


async def index(request: Request):
    """根路径 - 返回服务信息"""
    return JSONResponse({
        "name": "CrossGuard MCP HTTP Server",
        "version": "0.2.0",
        "description": "跨境电商智能合规审查 MCP 服务",
        "endpoints": {
            "sse": "/sse",
            "messages": "/messages",
            "health": "/health"
        },
        "tools": ["check_compliance", "list_markets"],
        "resources": [
            "regulation://{market}/{category}",
            "cases://{id}",
            "replacements://{market}/{category}"
        ],
        "authentication": "API Key (Bearer token)" if REQUIRE_API_KEY else "None"
    })


# ===== SSE 传输设置 =====

# 创建 SSE 传输
sse = SseServerTransport("/messages")


async def handle_sse(request: Request):
    """处理 SSE 连接"""
    async with mcp._mcp_server.run() as server:
        await sse.connect_sse(
            request.scope,
            request.receive,
            request._send,
            server,
        )


async def handle_messages(request: Request):
    """处理 POST 消息"""
    async with mcp._mcp_server.run() as server:
        await sse.handle_post_message(
            request.scope,
            request.receive,
            request._send,
            server,
        )


# ===== 创建应用 =====

app = Starlette(
    debug=True,
    routes=[
        Route("/", index),
        Route("/health", health_check),
        Route("/sse", handle_sse),
        Route("/messages", handle_messages, methods=["POST"]),
    ],
    middleware=[Middleware(APIKeyMiddleware)] if REQUIRE_API_KEY else [],
)


def main():
    """启动服务器"""
    import uvicorn

    host = os.getenv("CROSSGUARD_HOST", "0.0.0.0")
    port = int(os.getenv("CROSSGUARD_PORT", "8080"))

    logger.info(f"Starting CrossGuard MCP HTTP Server on {host}:{port}")
    logger.info(f"API URL: {API_URL}")
    logger.info(f"Require API Key: {REQUIRE_API_KEY}")

    uvicorn.run(
        "crossguard_mcp_http:app",
        host=host,
        port=port,
        reload=False,
    )


if __name__ == "__main__":
    main()
