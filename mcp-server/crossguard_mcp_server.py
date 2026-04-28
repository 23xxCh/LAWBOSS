"""
CrossGuard MCP Server — 出海法盾合规检测 MCP 服务

为 AI Agent (Claude Code 等) 提供合规检测工具。
可直接被 Claude Code MCP 配置加载。

用法:
  uv run --directory /path/to/crossguard/mcp-server crossguard_mcp_server.py
"""
import sys
import json
from pathlib import Path

# 将 backend 加入路径以复用合规检测引擎
_backend_dir = Path(__file__).resolve().parent.parent / "backend"
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

from mcp.server.fastmcp import FastMCP
from app.services.compliance_checker import ComplianceChecker
from app.config import SUPPORTED_MARKETS, SUPPORTED_CATEGORIES, DATA_DIR, REGULATIONS_DIR, CASES_DIR

# 初始化合规检测引擎
_checker = ComplianceChecker(data_dir=DATA_DIR)

# 市场和类别的文件路径映射
_MARKET_SLUG = {"EU": "eu", "US": "us", "SEA_SG": "sea", "SEA_TH": "sea", "SEA_MY": "sea"}
_CATEGORY_SLUG = {"化妆品": "cosmetics", "电子产品": "electronics", "食品": "food",
                  "玩具": "toys", "纺织品": "textiles", "膳食补充剂": "supplements"}
_REPLACEMENTS_DIR = DATA_DIR / "replacements"

mcp = FastMCP("CrossGuard", instructions="""\
CrossGuard (出海法盾) 跨境电商智能合规审查工具。支持以下市场：
- EU (欧盟)、US (美国)、SEA_SG (新加坡)、SEA_TH (泰国)、SEA_MY (马来西亚)

检测内容包括：医疗宣称、绝对化用语、虚假广告、缺失标签、禁用成分。
""")


def _report_to_dict(report) -> dict:
    """将 ComplianceReport 转为可 JSON 序列化的 dict"""
    return {
        "risk_score": report.risk_score,
        "risk_level": report.risk_level,
        "risk_description": report.risk_description,
        "market": report.market,
        "category": report.category,
        "violations": [
            {
                "type": v.type.value if hasattr(v.type, "value") else v.type,
                "type_label": v.type_label,
                "content": v.content,
                "regulation": v.regulation,
                "regulation_detail": v.regulation_detail,
                "severity": v.severity.value if hasattr(v.severity, "value") else v.severity,
                "severity_label": v.severity_label,
                "suggestion": v.suggestion,
                "score": v.score,
            }
            for v in report.violations
        ],
        "compliant_version": report.compliant_version,
        "required_labels": report.required_labels,
        "required_certifications": report.required_certifications,
        "suggestions": report.suggestions,
    }


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
    report = _checker.check_text(
        description=description,
        product_category=category,
        target_market=market,
    )
    return json.dumps(_report_to_dict(report), ensure_ascii=False, indent=2)


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


def main():
    mcp.run()


if __name__ == "__main__":
    main()
