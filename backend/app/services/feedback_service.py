"""
用户反馈服务 — 数据飞轮核心

功能：
- 用户标记误报/漏报
- 反馈数据存储和统计
- 反馈驱动的规则优化建议
- 检测精度指标计算

数据飞轮：
用户反馈 → 统计分析 → 规则优化建议 → 人工审核 → 规则更新 → 精度提升
"""
import json
import uuid
import logging
from datetime import datetime, timezone
from typing import List, Dict, Optional
from dataclasses import dataclass, field, asdict
from pathlib import Path
from enum import Enum

logger = logging.getLogger(__name__)


class FeedbackType(str, Enum):
    FALSE_POSITIVE = "false_positive"  # 误报：系统报了但实际不违规
    FALSE_NEGATIVE = "false_negative"  # 漏报：系统没报但实际违规
    CORRECT = "correct"                # 正确：检测结果准确


@dataclass
class UserFeedback:
    """用户反馈"""
    id: str
    report_id: str
    feedback_type: FeedbackType
    violation_type: str          # medical_claim, absolute_term, etc.
    violation_content: str       # 被标记的违规内容
    user_comment: str            # 用户备注
    market: str
    category: str
    created_at: str
    # 上下文信息
    original_description: str = ""
    risk_score: int = 0


@dataclass
class RuleOptimizationSuggestion:
    """规则优化建议"""
    id: str
    violation_type: str
    content: str
    suggestion_type: str  # remove_word, add_word, adjust_score, add_replacement
    reason: str
    confidence: float     # 0-1, 基于反馈数量
    feedback_count: int
    created_at: str


class FeedbackService:
    """反馈服务 — 数据飞轮核心"""

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.feedback_dir = data_dir / "feedbacks"
        self.feedback_dir.mkdir(exist_ok=True)

    def submit_feedback(
        self,
        report_id: str,
        feedback_type: FeedbackType,
        violation_type: str,
        violation_content: str,
        user_comment: str,
        market: str,
        category: str,
        original_description: str = "",
        risk_score: int = 0,
    ) -> UserFeedback:
        """提交用户反馈"""
        feedback = UserFeedback(
            id=str(uuid.uuid4())[:8],
            report_id=report_id,
            feedback_type=feedback_type,
            violation_type=violation_type,
            violation_content=violation_content,
            user_comment=user_comment,
            market=market,
            category=category,
            original_description=original_description,
            risk_score=risk_score,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        # 存储反馈
        filepath = self.feedback_dir / f"fb_{feedback.id}.json"
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(asdict(feedback), f, ensure_ascii=False, indent=2)

        logger.info(f"用户反馈: {feedback.feedback_type.value} on {violation_type}/{violation_content}")
        return feedback

    def get_all_feedbacks(self, limit: int = 100) -> List[UserFeedback]:
        """获取所有反馈"""
        feedbacks = []
        for f in sorted(self.feedback_dir.glob("fb_*.json"), reverse=True)[:limit]:
            try:
                with open(f, 'r', encoding='utf-8') as fh:
                    data = json.load(fh)
                feedbacks.append(UserFeedback(
                    id=data["id"],
                    report_id=data["report_id"],
                    feedback_type=FeedbackType(data["feedback_type"]),
                    violation_type=data["violation_type"],
                    violation_content=data["violation_content"],
                    user_comment=data["user_comment"],
                    market=data["market"],
                    category=data["category"],
                    original_description=data.get("original_description", ""),
                    risk_score=data.get("risk_score", 0),
                    created_at=data["created_at"],
                ))
            except Exception:
                continue
        return feedbacks

    def get_accuracy_metrics(self) -> Dict:
        """计算检测精度指标"""
        feedbacks = self.get_all_feedbacks(limit=10000)
        if not feedbacks:
            return {
                "total_feedbacks": 0,
                "false_positive_rate": 0,
                "false_negative_rate": 0,
                "accuracy": 0,
                "by_violation_type": {},
                "trend": [],
            }

        total = len(feedbacks)
        fp_count = sum(1 for f in feedbacks if f.feedback_type == FeedbackType.FALSE_POSITIVE)
        fn_count = sum(1 for f in feedbacks if f.feedback_type == FeedbackType.FALSE_NEGATIVE)
        correct_count = sum(1 for f in feedbacks if f.feedback_type == FeedbackType.CORRECT)

        # 按违规类型统计
        by_type: Dict[str, Dict] = {}
        for f in feedbacks:
            if f.violation_type not in by_type:
                by_type[f.violation_type] = {"total": 0, "fp": 0, "fn": 0, "correct": 0}
            by_type[f.violation_type]["total"] += 1
            if f.feedback_type == FeedbackType.FALSE_POSITIVE:
                by_type[f.violation_type]["fp"] += 1
            elif f.feedback_type == FeedbackType.FALSE_NEGATIVE:
                by_type[f.violation_type]["fn"] += 1
            else:
                by_type[f.violation_type]["correct"] += 1

        # 计算各类型精度
        for vtype in by_type:
            t = by_type[vtype]["total"]
            by_type[vtype]["accuracy"] = round(by_type[vtype]["correct"] / t * 100, 1) if t > 0 else 0
            by_type[vtype]["fp_rate"] = round(by_type[vtype]["fp"] / t * 100, 1) if t > 0 else 0
            by_type[vtype]["fn_rate"] = round(by_type[vtype]["fn"] / t * 100, 1) if t > 0 else 0

        return {
            "total_feedbacks": total,
            "false_positive_count": fp_count,
            "false_negative_count": fn_count,
            "correct_count": correct_count,
            "false_positive_rate": round(fp_count / total * 100, 1),
            "false_negative_rate": round(fn_count / total * 100, 1),
            "accuracy": round(correct_count / total * 100, 1),
            "by_violation_type": by_type,
        }

    def generate_optimization_suggestions(self) -> List[RuleOptimizationSuggestion]:
        """基于反馈数据生成规则优化建议"""
        feedbacks = self.get_all_feedbacks(limit=10000)
        suggestions = []

        # 按违规内容聚合误报
        fp_by_content: Dict[str, List[UserFeedback]] = {}
        for f in feedbacks:
            if f.feedback_type == FeedbackType.FALSE_POSITIVE:
                key = f"{f.violation_type}:{f.violation_content}"
                if key not in fp_by_content:
                    fp_by_content[key] = []
                fp_by_content[key].append(f)

        # 误报超过 3 次的，建议移除该词
        for key, fbs in fp_by_content.items():
            if len(fbs) >= 3:
                vtype, content = key.split(":", 1)
                suggestions.append(RuleOptimizationSuggestion(
                    id=str(uuid.uuid4())[:8],
                    violation_type=vtype,
                    content=content,
                    suggestion_type="remove_word",
                    reason=f"该词被 {len(fbs)} 次标记为误报，建议从禁用词库中移除或添加白名单",
                    confidence=min(len(fbs) / 10, 1.0),
                    feedback_count=len(fbs),
                    created_at=datetime.now(timezone.utc).isoformat(),
                ))

        # 按违规类型聚合漏报
        fn_by_type: Dict[str, List[UserFeedback]] = {}
        for f in feedbacks:
            if f.feedback_type == FeedbackType.FALSE_NEGATIVE:
                if f.violation_type not in fn_by_type:
                    fn_by_type[f.violation_type] = []
                fn_by_type[f.violation_type].append(f)

        # 漏报超过 2 次的类型，建议补充词库
        for vtype, fbs in fn_by_type.items():
            if len(fbs) >= 2:
                # 收集用户提到的漏报内容
                missed_contents = list(set(f.violation_content for f in fbs if f.violation_content))
                suggestions.append(RuleOptimizationSuggestion(
                    id=str(uuid.uuid4())[:8],
                    violation_type=vtype,
                    content=", ".join(missed_contents[:5]),
                    suggestion_type="add_word",
                    reason=f"该类型被 {len(fbs)} 次标记为漏报，建议补充禁用词库：{', '.join(missed_contents[:5])}",
                    confidence=min(len(fbs) / 8, 1.0),
                    feedback_count=len(fbs),
                    created_at=datetime.now(timezone.utc).isoformat(),
                ))

        return sorted(suggestions, key=lambda s: s.confidence, reverse=True)
