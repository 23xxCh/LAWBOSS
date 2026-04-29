"""合规成本计算器 — 展示不合规风险 vs 检测成本的 ROI"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from typing import List, Optional

from ..models.user import User
from ..routers.auth import get_current_user

router = APIRouter(tags=["合规成本"])

# 各市场典型罚款范围（美元）
PENALTY_RANGES = {
    "EU": {"min": 10000, "max": 500000, "currency": "EUR", "label": "欧盟"},
    "US": {"min": 5000, "max": 43000, "currency": "USD", "label": "美国"},
    "SEA_SG": {"min": 3000, "max": 100000, "currency": "SGD", "label": "新加坡"},
    "SEA_TH": {"min": 2000, "max": 50000, "currency": "USD", "label": "泰国"},
    "SEA_MY": {"min": 2000, "max": 250000, "currency": "MYR", "label": "马来西亚"},
}

# 违规类型 vs 典型罚款乘数（基于实际案例估算）
VIOLATION_PENALTY_MULTIPLIERS = {
    "medical_claim": 0.4,
    "banned_ingredient": 0.5,
    "absolute_term": 0.15,
    "false_advertising": 0.25,
    "missing_label": 0.1,
    "implicit_violation": 0.2,
}

# 常见违规案例损失（美元）
CASE_LOSSES = [
    {"scenario": "Amazon 下架滞销库存损失", "amount": 50000, "source": "2024 亚马逊封店潮"},
    {"scenario": "FDA 退货/销毁费用", "amount": 25000, "source": "FDA 进口拒绝数据"},
    {"scenario": "法律诉讼/律师费", "amount": 30000, "source": "跨境电商诉讼案例"},
    {"scenario": "品牌信誉修复成本", "amount": 100000, "source": "品牌危机管理估算"},
    {"scenario": "平台账户暂停损失", "amount": 150000, "source": "Amazon/Shopee 封店"},
]


class CostEstimateItem(BaseModel):
    """单项成本估算"""
    scenario: str = Field(..., description="场景描述")
    estimated_loss: int = Field(..., description="估算损失（美元）")
    probability: float = Field(..., description="发生概率 0-1")
    expected_loss: int = Field(..., description="期望损失 = 估算损失 * 概率")
    source: str = Field("", description="数据来源")


class PenaltyEstimate(BaseModel):
    """市场罚款估算"""
    market: str
    market_label: str
    min_penalty: int
    max_penalty: int
    currency: str
    estimated_penalty: int
    violation_count: int
    risk_level: str


class CostSavingsResponse(BaseModel):
    """合规成本节省估算响应"""
    total_risk_exposure: int = Field(..., description="总风险敞口（美元）")
    annual_check_cost: int = Field(..., description="年检测成本（假设 1000 次/年）")
    annual_savings: int = Field(..., description="年节省金额")
    savings_per_check: int = Field(..., description="每次检测节省")
    market_penalties: List[PenaltyEstimate] = Field(default_factory=list)
    case_losses: List[CostEstimateItem] = Field(default_factory=list)
    disclaimer: str = "以上数据为基于行业公开数据的估算，不构成法律建议。实际罚款金额取决于具体情况。"


@router.get("/compliance/cost-savings", response_model=CostSavingsResponse, summary="合规成本节省估算")
async def get_cost_savings(current_user: User = Depends(get_current_user)):
    """返回合规 vs 不合规的成本对比估算"""
    market_penalties = []
    total_exposure = 0

    for market_id, info in PENALTY_RANGES.items():
        est = (info["min"] + info["max"]) // 2
        market_penalties.append(PenaltyEstimate(
            market=market_id,
            market_label=info["label"],
            min_penalty=info["min"],
            max_penalty=info["max"],
            currency=info["currency"],
            estimated_penalty=est,
            violation_count=3,
            risk_level="中风险",
        ))
        total_exposure += est

    case_losses = []
    total_case_risk = 0
    for case in CASE_LOSSES:
        prob = 0.15 if "Amazon" in case["scenario"] or "账户" in case["scenario"] else 0.08
        expected = int(case["amount"] * prob)
        case_losses.append(CostEstimateItem(
            scenario=case["scenario"],
            estimated_loss=case["amount"],
            probability=prob,
            expected_loss=expected,
            source=case["source"],
        ))
        total_case_risk += expected

    total_risk = total_exposure + total_case_risk
    annual_check_cost = 1000 * 0  # 免费版不收费
    annual_savings = total_risk - annual_check_cost
    savings_per_check = total_risk // 1000 if total_risk > 0 else 0

    return CostSavingsResponse(
        total_risk_exposure=total_risk,
        annual_check_cost=annual_check_cost,
        annual_savings=annual_savings,
        savings_per_check=savings_per_check if savings_per_check > 0 else 50,
        market_penalties=market_penalties,
        case_losses=case_losses,
    )
