"""
定期合规巡检调度引擎

功能：
- 定时拉取电商平台 Listing
- 自动执行合规检测
- 高风险项触发告警（Webhook/邮件）
- 巡检结果存储和查询
"""
import os
import json
import uuid
import logging
from datetime import datetime, timezone
from typing import List, Dict, Optional
from dataclasses import dataclass, field, asdict
from pathlib import Path

from .compliance_checker import ComplianceChecker, ComplianceReport
from .platform_client import get_platform_client, PlatformListing, BasePlatformClient

logger = logging.getLogger(__name__)


@dataclass
class PatrolResult:
    """巡检结果"""
    id: str
    patrol_time: str
    platform: str
    market: str
    total_listings: int
    checked_listings: int
    high_risk_count: int
    medium_risk_count: int
    low_risk_count: int
    compliant_count: int
    details: List[Dict] = field(default_factory=list)
    # 告警信息
    alerts: List[Dict] = field(default_factory=list)


class PatrolEngine:
    """合规巡检引擎

    调度流程：
    1. 从电商平台拉取 Listing
    2. 逐条执行合规检测
    3. 高风险项生成告警
    4. 存储巡检结果
    5. 触发 Webhook/邮件通知
    """

    def __init__(self, checker: ComplianceChecker, data_dir: Path):
        self.checker = checker
        self.data_dir = data_dir
        self.patrol_dir = data_dir / "patrols"
        self.patrol_dir.mkdir(exist_ok=True)
        self.webhook_url = os.getenv("PATROL_WEBHOOK_URL", "")
        self.alert_threshold = int(os.getenv("PATROL_ALERT_THRESHOLD", "70"))

    async def run_patrol(
        self,
        platform: str,
        market: str,
        category: Optional[str] = None,
        limit: int = 100,
    ) -> PatrolResult:
        """执行一次合规巡检"""
        patrol_id = str(uuid.uuid4())[:8]
        logger.info(f"[Patrol {patrol_id}] 开始巡检: platform={platform}, market={market}")

        # 1. 拉取 Listing
        client = get_platform_client(platform)
        if not client:
            logger.error(f"平台 {platform} 未配置或不可用")
            return PatrolResult(
                id=patrol_id, patrol_time=datetime.now(timezone.utc).isoformat(),
                platform=platform, market=market,
                total_listings=0, checked_listings=0,
                high_risk_count=0, medium_risk_count=0, low_risk_count=0, compliant_count=0,
            )

        listings = await client.fetch_listings(market, category, limit=limit)
        logger.info(f"[Patrol {patrol_id}] 拉取到 {len(listings)} 条 Listing")

        # 2. 逐条检测
        result = PatrolResult(
            id=patrol_id,
            patrol_time=datetime.now(timezone.utc).isoformat(),
            platform=platform,
            market=market,
            total_listings=len(listings),
            checked_listings=0,
            high_risk_count=0,
            medium_risk_count=0,
            low_risk_count=0,
            compliant_count=0,
        )

        for listing in listings:
            if not listing.description:
                continue

            # 映射平台类别到内部类别
            internal_category = client.map_category(listing.category)

            # 执行检测
            report = self.checker.check_text(
                description=listing.description,
                product_category=internal_category,
                target_market=market,
            )

            result.checked_listings += 1

            # 统计风险
            if report.risk_score >= 70:
                result.high_risk_count += 1
            elif report.risk_score >= 40:
                result.medium_risk_count += 1
            else:
                if report.risk_score < 40 and len(report.violations) == 0:
                    result.compliant_count += 1
                else:
                    result.low_risk_count += 1

            # 记录详情
            detail = {
                "listing_id": listing.listing_id,
                "title": listing.title[:100],
                "category": internal_category,
                "risk_score": report.risk_score,
                "risk_level": report.risk_level,
                "violation_count": len(report.violations),
                "violation_types": list(set(v.type_label for v in report.violations)),
            }
            result.details.append(detail)

            # 3. 高风险告警
            if report.risk_score >= self.alert_threshold:
                alert = {
                    "listing_id": listing.listing_id,
                    "title": listing.title[:100],
                    "risk_score": report.risk_score,
                    "risk_level": report.risk_level,
                    "violations": [
                        {"type": v.type_label, "content": v.content}
                        for v in report.violations
                    ],
                    "compliant_version_available": bool(report.compliant_version),
                }
                result.alerts.append(alert)

        # 4. 存储巡检结果
        self._save_patrol_result(result)

        # 5. 触发告警通知
        if result.alerts:
            await self._send_alerts(result)

        logger.info(
            f"[Patrol {patrol_id}] 巡检完成: "
            f"checked={result.checked_listings}, "
            f"high={result.high_risk_count}, "
            f"medium={result.medium_risk_count}, "
            f"low={result.low_risk_count}, "
            f"compliant={result.compliant_count}, "
            f"alerts={len(result.alerts)}"
        )

        return result

    def _save_patrol_result(self, result: PatrolResult):
        """存储巡检结果到文件"""
        filename = f"patrol_{result.platform}_{result.market}_{result.id}.json"
        filepath = self.patrol_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(asdict(result), f, ensure_ascii=False, indent=2)

    async def _send_alerts(self, result: PatrolResult):
        """发送告警通知"""
        if not self.webhook_url:
            logger.info(f"无 Webhook 配置，跳过告警通知 ({len(result.alerts)} 条告警)")
            return

        try:
            import httpx
            payload = {
                "type": "patrol_alert",
                "patrol_id": result.id,
                "platform": result.platform,
                "market": result.market,
                "alert_count": len(result.alerts),
                "alerts": result.alerts[:10],  # 最多发送 10 条
                "summary": {
                    "total": result.total_listings,
                    "high_risk": result.high_risk_count,
                    "medium_risk": result.medium_risk_count,
                },
            }
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(self.webhook_url, json=payload)
                if resp.status_code == 200:
                    logger.info(f"告警通知已发送: {len(result.alerts)} 条")
                else:
                    logger.error(f"告警通知发送失败: {resp.status_code}")
        except Exception as e:
            logger.error(f"告警通知发送异常: {e}")

    def get_patrol_history(self, platform: Optional[str] = None, limit: int = 20) -> List[Dict]:
        """获取巡检历史"""
        results = []
        for f in sorted(self.patrol_dir.glob("*.json"), reverse=True)[:limit * 2]:
            try:
                with open(f, 'r', encoding='utf-8') as fh:
                    data = json.load(fh)
                if platform and data.get("platform") != platform:
                    continue
                results.append({
                    "id": data["id"],
                    "patrol_time": data["patrol_time"],
                    "platform": data["platform"],
                    "market": data["market"],
                    "total_listings": data["total_listings"],
                    "checked_listings": data["checked_listings"],
                    "high_risk_count": data["high_risk_count"],
                    "medium_risk_count": data["medium_risk_count"],
                    "low_risk_count": data["low_risk_count"],
                    "compliant_count": data["compliant_count"],
                    "alert_count": len(data.get("alerts", [])),
                })
                if len(results) >= limit:
                    break
            except Exception:
                continue
        return results
