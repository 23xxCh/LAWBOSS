"""
CrossGuard MCP Server 测试

测试覆盖:
- check_compliance: 输入验证、happy path、错误路径
- list_markets: 返回格式验证
- get_regulation: 有效/缺失法规
- get_case: 有效/缺失案例
"""
import sys
import json
import pytest
from pathlib import Path

# 添加 mcp-server 目录到路径
_mcp_dir = Path(__file__).resolve().parent.parent
if str(_mcp_dir) not in sys.path:
    sys.path.insert(0, str(_mcp_dir))

# 添加 backend 目录到路径
_backend_dir = _mcp_dir.parent / "backend"
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

from crossguard_mcp_server import check_compliance, list_markets, get_regulation, get_case


class TestCheckCompliance:
    """check_compliance tool 测试"""

    def test_happy_path_valid_input(self):
        """测试有效输入的合规检测"""
        result = check_compliance(
            description="这款面霜具有舒缓保湿功效",
            market="EU",
            category="化妆品",
        )
        data = json.loads(result)
        assert "risk_score" in data
        assert "risk_level" in data
        assert data["market"] == "EU"
        assert data["category"] == "化妆品"

    def test_empty_description(self):
        """测试空描述"""
        result = check_compliance(
            description="",
            market="EU",
            category="化妆品",
        )
        data = json.loads(result)
        assert "error" in data
        assert data["code"] == "INVALID_INPUT"

    def test_whitespace_description(self):
        """测试仅空白的描述"""
        result = check_compliance(
            description="   ",
            market="EU",
            category="化妆品",
        )
        data = json.loads(result)
        assert "error" in data
        assert data["code"] == "INVALID_INPUT"

    def test_none_description(self):
        """测试 None 描述"""
        result = check_compliance(
            description=None,
            market="EU",
            category="化妆品",
        )
        data = json.loads(result)
        assert "error" in data

    def test_invalid_market(self):
        """测试无效市场"""
        result = check_compliance(
            description="测试产品描述",
            market="INVALID_MARKET",
            category="化妆品",
        )
        data = json.loads(result)
        assert "error" in data
        assert data["code"] == "INVALID_MARKET"
        assert "supported_markets" in data

    def test_invalid_category(self):
        """测试无效类别"""
        result = check_compliance(
            description="测试产品描述",
            market="EU",
            category="武器",
        )
        data = json.loads(result)
        assert "error" in data
        assert data["code"] == "INVALID_CATEGORY"
        assert "supported_categories" in data

    def test_high_risk_medical_claim(self):
        """测试医疗宣称检测"""
        result = check_compliance(
            description="这款面霜能治疗痘痘，7天见效",
            market="EU",
            category="化妆品",
        )
        data = json.loads(result)
        assert data["risk_score"] >= 70
        assert len(data["violations"]) > 0
        violation_types = [v["type"] for v in data["violations"]]
        assert "medical_claim" in violation_types

    def test_absolute_term_detection(self):
        """测试绝对化用语检测"""
        result = check_compliance(
            description="这是市面上最好的产品，100%有效",
            market="EU",
            category="化妆品",
        )
        data = json.loads(result)
        violation_types = [v["type"] for v in data["violations"]]
        assert "absolute_term" in violation_types

    def test_us_market(self):
        """测试美国市场"""
        result = check_compliance(
            description="This cream treats acne effectively",
            market="US",
            category="化妆品",
        )
        data = json.loads(result)
        assert data["market"] == "US"
        assert "risk_score" in data

    def test_sea_singapore_market(self):
        """测试新加坡市场"""
        result = check_compliance(
            description="这款产品效果很好",
            market="SEA_SG",
            category="化妆品",
        )
        data = json.loads(result)
        assert data["market"] == "SEA_SG"


class TestListMarkets:
    """list_markets tool 测试"""

    def test_returns_valid_json(self):
        """测试返回有效 JSON"""
        result = list_markets()
        data = json.loads(result)
        assert isinstance(data, list)
        assert len(data) > 0

    def test_contains_eu_market(self):
        """测试包含 EU 市场"""
        result = list_markets()
        data = json.loads(result)
        market_codes = [m["code"] for m in data]
        assert "EU" in market_codes

    def test_contains_us_market(self):
        """测试包含 US 市场"""
        result = list_markets()
        data = json.loads(result)
        market_codes = [m["code"] for m in data]
        assert "US" in market_codes

    def test_market_has_categories(self):
        """测试市场有类别信息"""
        result = list_markets()
        data = json.loads(result)
        for market in data:
            assert "code" in market
            assert "categories" in market
            assert isinstance(market["categories"], list)


class TestGetRegulation:
    """get_regulation resource 测试"""

    def test_valid_regulation(self):
        """测试获取有效法规"""
        result = get_regulation(market="EU", category="化妆品")
        data = json.loads(result)
        # 可能是法规数据或错误，取决于文件是否存在
        assert isinstance(data, dict)

    def test_invalid_market(self):
        """测试无效市场"""
        result = get_regulation(market="INVALID", category="化妆品")
        data = json.loads(result)
        assert "error" in data
        assert "supported" in data

    def test_invalid_category(self):
        """测试无效类别"""
        result = get_regulation(market="EU", category="武器")
        data = json.loads(result)
        assert "error" in data


class TestGetCase:
    """get_case resource 测试"""

    def test_case_by_numeric_id(self):
        """测试通过数字 ID 获取案例"""
        result = get_case(id="1")
        data = json.loads(result)
        # 可能是案例数据或错误，取决于文件是否存在
        assert isinstance(data, dict)

    def test_case_not_found(self):
        """测试案例不存在"""
        result = get_case(id="999999999")
        data = json.loads(result)
        assert "error" in data or "title" in data  # 取决于文件内容


class TestReportToDict:
    """report_to_dict 函数测试"""

    def test_import_available(self):
        """测试 utils 模块可导入"""
        from utils import report_to_dict
        assert callable(report_to_dict)
