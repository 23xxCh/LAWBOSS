"""用户反馈 + 数据飞轮 API 路由"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..services.feedback_service import FeedbackService, FeedbackType
from ..config import DATA_DIR
from ..models.user import User
from ..routers.auth import get_current_user

router = APIRouter(tags=["数据飞轮"])


class FeedbackRequest(BaseModel):
    """提交反馈请求"""
    report_id: str = Field(..., description="检测报告ID")
    feedback_type: str = Field(..., description="反馈类型: false_positive, false_negative, correct")
    violation_type: str = Field(..., description="违规类型")
    violation_content: str = Field(..., description="违规内容")
    user_comment: str = Field(default="", description="用户备注")
    market: str = Field(..., description="市场")
    category: str = Field(..., description="类别")
    original_description: str = Field(default="", description="原始描述")
    risk_score: int = Field(default=0, description="风险评分")


class FeedbackResponse(BaseModel):
    id: str
    report_id: str
    feedback_type: str
    violation_type: str
    violation_content: str
    user_comment: str
    created_at: str
    reward: dict = {}  # 激励信息


class AccuracyMetricsResponse(BaseModel):
    """检测精度指标"""
    total_feedbacks: int
    false_positive_count: int = 0
    false_negative_count: int = 0
    correct_count: int = 0
    false_positive_rate: float = 0
    false_negative_rate: float = 0
    accuracy: float = 0
    by_violation_type: dict = {}


class OptimizationSuggestionResponse(BaseModel):
    """规则优化建议"""
    id: str
    violation_type: str
    content: str
    suggestion_type: str
    reason: str
    confidence: float
    feedback_count: int
    created_at: str


def _get_feedback_service() -> FeedbackService:
    return FeedbackService(data_dir=DATA_DIR)


@router.post("/feedback", response_model=FeedbackResponse, summary="提交检测反馈")
async def submit_feedback(request: FeedbackRequest, current_user: User = Depends(get_current_user)):
    """
    用户对检测结果提交反馈（误报/漏报/正确）— 数据飞轮入口

    - 误报(false_positive)：系统报了但实际不违规 → 建议移除该词
    - 漏报(false_negative)：系统没报但实际违规 → 建议补充词库
    - 正确(correct)：检测结果准确 → 增强规则置信度
    """
    try:
        fb_type = FeedbackType(request.feedback_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"无效的反馈类型: {request.feedback_type}")

    service = _get_feedback_service()
    feedback = service.submit_feedback(
        report_id=request.report_id,
        feedback_type=fb_type,
        violation_type=request.violation_type,
        violation_content=request.violation_content,
        user_comment=request.user_comment,
        market=request.market,
        category=request.category,
        original_description=request.original_description,
        risk_score=request.risk_score,
    )

    # 反馈激励：记录反馈并计算奖励
    reward = service.record_feedback_reward(current_user.username)

    return FeedbackResponse(
        id=feedback.id,
        report_id=feedback.report_id,
        feedback_type=feedback.feedback_type.value,
        violation_type=feedback.violation_type,
        violation_content=feedback.violation_content,
        user_comment=feedback.user_comment,
        created_at=feedback.created_at,
        reward=reward,
    )


@router.get("/feedback/accuracy", response_model=AccuracyMetricsResponse, summary="检测精度指标")
async def get_accuracy_metrics(current_user: User = Depends(get_current_user)):
    """
    获取检测精度指标

    返回：误报率、漏报率、准确率、按违规类型分组的精度
    """
    service = _get_feedback_service()
    return service.get_accuracy_metrics()


@router.get("/feedback/suggestions", response_model=List[OptimizationSuggestionResponse], summary="规则优化建议")
async def get_optimization_suggestions(
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
):
    """
    基于用户反馈数据自动生成规则优化建议

    - 误报超过 3 次的词汇 → 建议移除
    - 漏报超过 2 次的类型 → 建议补充词库
    """
    service = _get_feedback_service()
    suggestions = service.generate_optimization_suggestions()
    return [
        OptimizationSuggestionResponse(
            id=s.id,
            violation_type=s.violation_type,
            content=s.content,
            suggestion_type=s.suggestion_type,
            reason=s.reason,
            confidence=s.confidence,
            feedback_count=s.feedback_count,
            created_at=s.created_at,
        )
        for s in suggestions[:limit]
    ]


@router.get("/feedback/list", summary="反馈列表")
async def list_feedbacks(
    limit: int = Query(default=50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
):
    """获取用户反馈列表"""
    service = _get_feedback_service()
    feedbacks = service.get_all_feedbacks(limit=limit)
    return [
        {
            "id": f.id,
            "report_id": f.report_id,
            "feedback_type": f.feedback_type.value,
            "violation_type": f.violation_type,
            "violation_content": f.violation_content,
            "user_comment": f.user_comment,
            "market": f.market,
            "category": f.category,
            "created_at": f.created_at,
        }
        for f in feedbacks
    ]


@router.get("/feedback/quota", summary="我的反馈额度")
async def get_my_quota(current_user: User = Depends(get_current_user)):
    """获取当前用户的反馈统计和奖励额度"""
    service = _get_feedback_service()
    return service.get_user_quota(current_user.username)


@router.get("/feedback/leaderboard", summary="反馈排行榜")
async def get_leaderboard(
    limit: int = Query(default=10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
):
    """获取反馈贡献排行榜"""
    service = _get_feedback_service()
    return {"leaderboard": service.get_leaderboard(limit=limit)}
