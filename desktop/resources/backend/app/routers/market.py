"""市场与类别查询 API 路由"""
from fastapi import APIRouter, HTTPException, Request

from ..schemas.common import MarketResponse, CategoryResponse, LabelResponse, CertificationResponse
from ..config import SUPPORTED_MARKETS, SUPPORTED_CATEGORIES
from ..services.compliance_checker import ComplianceChecker

router = APIRouter(tags=["市场与类别"])

MARKET_NAMES = {
    "EU": "欧盟",
    "US": "美国",
    "SEA_SG": "新加坡",
    "SEA_TH": "泰国",
    "SEA_MY": "马来西亚",
}


def _get_checker(request: Request) -> ComplianceChecker:
    return request.app.state.checker


@router.get("/markets", response_model=list[MarketResponse], summary="获取支持的市场列表")
async def get_markets():
    """返回所有支持的市场及其产品类别"""
    result = []
    for market in SUPPORTED_MARKETS:
        result.append(MarketResponse(
            code=market,
            name=MARKET_NAMES.get(market, market),
            categories=SUPPORTED_CATEGORIES.get(market, []),
        ))
    return result


@router.get("/markets/{market}/categories", response_model=list[CategoryResponse], summary="获取市场支持的产品类别")
async def get_categories(market: str):
    """返回指定市场支持的产品类别"""
    if market not in SUPPORTED_MARKETS:
        raise HTTPException(status_code=404, detail=f"不支持的市场: {market}")
    categories = SUPPORTED_CATEGORIES.get(market, [])
    return [CategoryResponse(name=c, market=market) for c in categories]


@router.get("/labels", response_model=LabelResponse, summary="查询必需标签")
async def get_labels(market: str, category: str, request: Request):
    """查询指定市场和产品类别的必需标签"""
    checker = _get_checker(request)
    labels = checker.get_required_labels(category, market)
    return LabelResponse(market=market, category=category, labels=labels)


@router.get("/certifications", response_model=CertificationResponse, summary="查询必需认证")
async def get_certifications(market: str, category: str, request: Request):
    """查询指定市场和产品类别的必需认证"""
    checker = _get_checker(request)
    certs = checker.get_required_certifications(category, market)
    return CertificationResponse(market=market, category=category, certifications=certs)
