"""法规更新监控服务 — RSS/API 轮询法规源，新法规自动通知管理员"""
import logging
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Optional
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)


@dataclass
class RegulationUpdate:
    """法规更新条目"""
    source: str          # 来源名称
    title: str           # 更新标题
    url: str             # 链接
    published: str       # 发布日期
    summary: str = ""    # 摘要
    market: str = ""     # 相关市场 (EU/US/SEA_SG/SEA_TH/SEA_MY)
    severity: str = "info"  # info/warning/critical


@dataclass
class RegulationSource:
    """法规数据源配置"""
    name: str
    url: str
    source_type: str  # rss / api / html
    market: str
    check_interval_hours: int = 24


# 预配置的法规数据源
REGULATION_SOURCES = [
    RegulationSource(
        name="EU Official Journal - Cosmetics",
        url="https://eur-lex.europa.eu/rss/latest/oj/cosmetics",
        source_type="rss",
        market="EU",
        check_interval_hours=24,
    ),
    RegulationSource(
        name="FDA Federal Register - Cosmetics",
        url="https://www.federalregister.gov/api/v1/documents.json?conditions%5Bagencies%5D=fda&conditions%5Btopic%5D=cosmetics",
        source_type="api",
        market="US",
        check_interval_hours=24,
    ),
    RegulationSource(
        name="ASEAN ACD Updates",
        url="https://asean.org/wp-json/wp/v2/posts?categories=regulatory",
        source_type="api",
        market="SEA_SG",
        check_interval_hours=72,
    ),
    RegulationSource(
        name="RAPEX/Safety Gate Weekly",
        url="https://ec.europa.eu/safety-gate-restapi/search/weekly",
        source_type="api",
        market="EU",
        check_interval_hours=168,
    ),
    RegulationSource(
        name="HSA Singapore - Health Products",
        url="https://www.hsa.gov.sg/rss/health-products",
        source_type="rss",
        market="SEA_SG",
        check_interval_hours=72,
    ),
    RegulationSource(
        name="Thai FDA Announcements",
        url="https://www.fda.moph.go.th/rss/en",
        source_type="rss",
        market="SEA_TH",
        check_interval_hours=72,
    ),
]


class RegulationMonitor:
    """法规更新监控器"""

    def __init__(self, data_dir: Path, webhook_url: Optional[str] = None):
        self.data_dir = data_dir
        self.webhook_url = webhook_url
        self.updates_file = data_dir / "regulation_updates.json"
        self.last_check_file = data_dir / "last_check.json"

    def get_sources(self) -> List[dict]:
        """获取所有监控源配置"""
        return [asdict(s) for s in REGULATION_SOURCES]

    def get_last_check_times(self) -> dict:
        """获取各源最后检查时间"""
        if self.last_check_file.exists():
            return json.loads(self.last_check_file.read_text(encoding="utf-8"))
        return {}

    def get_pending_updates(self, limit: int = 20) -> List[dict]:
        """获取待处理的法规更新"""
        if self.updates_file.exists():
            updates = json.loads(self.updates_file.read_text(encoding="utf-8"))
            return updates[:limit]
        return []

    async def check_all_sources(self) -> List[RegulationUpdate]:
        """检查所有法规源是否有更新（异步）"""
        import asyncio
        all_updates = []

        for source in REGULATION_SOURCES:
            try:
                updates = await asyncio.to_thread(self._check_source, source)
                all_updates.extend(updates)
            except Exception as e:
                logger.error(f"检查法规源 {source.name} 失败: {e}")

        # 按发布时间倒序
        all_updates.sort(key=lambda u: u.published, reverse=True)

        # 保存更新
        if all_updates:
            self._save_updates(all_updates)
            # 发送通知
            if self.webhook_url:
                await asyncio.to_thread(self._send_webhook, all_updates)

        # 更新检查时间
        self._update_check_times()

        return all_updates

    def _check_source(self, source: RegulationSource) -> List[RegulationUpdate]:
        """检查单个法规源"""
        updates = []

        try:
            import httpx
            with httpx.Client(timeout=30.0) as client:
                if source.source_type == "rss":
                    updates = self._parse_rss(source, client)
                elif source.source_type == "api":
                    updates = self._parse_api(source, client)
        except Exception as e:
            logger.warning(f"无法访问法规源 {source.name}: {e}")

        return updates

    def _parse_rss(self, source: RegulationSource, client) -> List[RegulationUpdate]:
        """解析 RSS 源"""
        try:
            resp = client.get(source.url)
            if resp.status_code != 200:
                return []

            # 简单的 RSS 解析（不依赖 feedparser）
            text = resp.text
            updates = []
            import re

            items = re.findall(r'<item>(.*?)</item>', text, re.DOTALL)
            for item in items[:5]:  # 只取最新5条
                title = re.search(r'<title>(.*?)</title>', item)
                link = re.search(r'<link>(.*?)</link>', item)
                pub_date = re.search(r'<pubDate>(.*?)</pubDate>', item)
                desc = re.search(r'<description>(.*?)</description>', item)

                if title and link:
                    updates.append(RegulationUpdate(
                        source=source.name,
                        title=title.group(1).strip(),
                        url=link.group(1).strip(),
                        published=pub_date.group(1).strip() if pub_date else datetime.now(timezone.utc).isoformat(),
                        summary=desc.group(1).strip()[:200] if desc else "",
                        market=source.market,
                        severity="warning",
                    ))
            return updates
        except Exception as e:
            logger.warning(f"RSS解析失败 {source.name}: {e}")
            return []

    def _parse_api(self, source: RegulationSource, client) -> List[RegulationUpdate]:
        """解析 API 源"""
        try:
            resp = client.get(source.url)
            if resp.status_code != 200:
                return []

            data = resp.json()
            updates = []

            # FDA Federal Register 格式
            if "results" in data:
                for item in data.get("results", [])[:5]:
                    updates.append(RegulationUpdate(
                        source=source.name,
                        title=item.get("title", ""),
                        url=item.get("html_url", ""),
                        published=item.get("publication_date", ""),
                        summary=item.get("abstract", "")[:200],
                        market=source.market,
                        severity="warning",
                    ))
            return updates
        except Exception as e:
            logger.warning(f"API解析失败 {source.name}: {e}")
            return []

    def _save_updates(self, updates: List[RegulationUpdate]):
        """保存更新到文件"""
        existing = []
        if self.updates_file.exists():
            existing = json.loads(self.updates_file.read_text(encoding="utf-8"))

        # 合并去重（按URL）
        existing_urls = {u.get("url") for u in existing}
        for update in updates:
            d = asdict(update)
            if d["url"] not in existing_urls:
                existing.insert(0, d)

        # 最多保留100条
        existing = existing[:100]
        self.updates_file.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")

    def _update_check_times(self):
        """更新最后检查时间"""
        times = self.get_last_check_times()
        now = datetime.now(timezone.utc).isoformat()
        for source in REGULATION_SOURCES:
            times[source.name] = now
        self.last_check_file.write_text(json.dumps(times, ensure_ascii=False, indent=2), encoding="utf-8")

    def _send_webhook(self, updates: List[RegulationUpdate]):
        """发送 Webhook 通知"""
        if not self.webhook_url:
            return

        try:
            import httpx
            text = f"📋 法规更新通知 ({len(updates)} 条)\n"
            for u in updates[:5]:
                text += f"\n• [{u.market}] {u.title}\n  {u.url}"

            with httpx.Client(timeout=10.0) as client:
                # 飞书/钉钉/Slack 通用格式
                client.post(self.webhook_url, json={"content": text})
        except Exception as e:
            logger.warning(f"Webhook发送失败: {e}")
