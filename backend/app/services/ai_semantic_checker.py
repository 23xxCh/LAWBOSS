"""
AI 语义检测器
基于 LLM 的深度语义合规检测，作为关键词检测的补充（二级复筛）

架构：继承 BaseChecker，可插拔接入 ComplianceChecker
策略：关键词初筛 → LLM 深度复筛，两级检测流水线
"""
import os
import json
import logging
from typing import List, Optional
from pathlib import Path

from .compliance_checker import (
    BaseChecker, Violation, ViolationType, Severity,
)

logger = logging.getLogger(__name__)


class AISemanticChecker(BaseChecker):
    """
    AI 语义检测器 — 基于 LLM 的深度合规分析

    与关键词检测器互补：
    - 关键词检测：快速、确定性、高召回率（可能误报）
    - AI 语义检测：深度理解上下文、低误报率、可检测隐含违规

    支持的 LLM 后端：
    - OpenAI API (GPT-4 / GPT-4o)
    - DeepSeek API
    - 本地 Ollama
    """

    def __init__(self, data_dir: Path):
        self.api_key = os.getenv("LLM_API_KEY", "")
        self.api_base = os.getenv("LLM_API_BASE", "https://api.openai.com/v1")
        self.model = os.getenv("LLM_MODEL", "gpt-4o-mini")
        self.enabled = bool(self.api_key) or os.getenv("LLM_ENABLED", "false").lower() == "true"
        self.max_tokens = int(os.getenv("LLM_MAX_TOKENS", "2048"))
        self.temperature = float(os.getenv("LLM_TEMPERATURE", "0.1"))

        if self.enabled:
            logger.info(f"AI 语义检测已启用: model={self.model}, api_base={self.api_base}")
        else:
            logger.info("AI 语义检测未启用（未配置 LLM_API_KEY 或 LLM_ENABLED）")

    def check(self, description: str, category: str, market: str) -> List[Violation]:
        """执行 AI 语义检测"""
        if not self.enabled:
            return []

        try:
            result = self._call_llm(description, category, market)
            if result:
                return self._parse_llm_response(result, market)
        except Exception as e:
            logger.error(f"AI 语义检测失败: {e}")

        return []

    def _build_prompt(self, description: str, category: str, market: str) -> str:
        """构建 LLM 检测 Prompt"""
        market_name = {"EU": "欧盟", "US": "美国", "SEA_SG": "新加坡", "SEA_TH": "泰国", "SEA_MY": "马来西亚"}.get(market, market)

        return f"""你是一位跨境电商合规审查专家。请对以下产品描述进行深度合规检测。

## 检测目标
- 目标市场：{market_name}
- 产品类别：{category}
- 产品描述：{description}

## 检测维度
请从以下维度逐一检测，识别关键词匹配可能遗漏的隐含违规：

1. **隐含医疗宣称**：未直接使用医疗词汇，但语义上暗示治疗/预防疾病功能
   - 例："告别痘痘肌"（暗示治疗）、"肌肤重获健康"（暗示医疗效果）、"远离敏感"（暗示预防）

2. **误导性功效宣称**：使用模糊但暗示绝对效果的表述
   - 例："肉眼可见的蜕变"（暗示绝对效果）、"从此告别XX"（暗示永久治愈）

3. **不当对比与贬低**：通过对比贬低竞品或暗示自身唯一性
   - 例："远超同类产品"、"市面唯一有效"

4. **文化/法律语境违规**：在特定市场文化或法律语境下的违规
   - EU：美白(whitening)在多国被视为医疗宣称、anti-aging 需谨慎
   - US：结构功能宣称(structure/function claim)需免责声明、OTC 药品边界
   - SEA：清真认证要求、特定成分限制

5. **成分暗示违规**：通过描述暗示含有禁用成分但未明说
   - 例："强效漂白"（暗示含过氧化氢超标）、"速效褪色"（暗示含禁用化学物）

## 输出格式
请以 JSON 格式输出检测结果，严格遵循以下结构：
```json
{{
  "violations": [
    {{
      "type": "medical_claim | absolute_term | false_advertising | missing_label | banned_ingredient | implicit_violation",
      "type_label": "违规类型中文名",
      "content": "违规原文片段",
      "regulation": "法规依据",
      "regulation_detail": "法规详情",
      "severity": "high | medium | low",
      "severity_label": "高 | 中 | 低",
      "suggestion": "修改建议",
      "score": 25,
      "reasoning": "AI 判定理由（为什么这是违规）"
    }}
  ],
  "overall_assessment": "整体合规评估摘要",
  "confidence": 0.85
}}
```

如果没有检测到违规，返回：`{{"violations": [], "overall_assessment": "未检测到违规", "confidence": 0.9}}`

注意：
- 只报告有较高置信度的违规（confidence > 0.7），避免误报
- 每条违规必须给出 reasoning 说明判定理由
- score 参考标准：医疗宣称 25、禁用成分 30、绝对化用语 15、虚假广告 15、缺失标签 10、隐含违规 20
- 不要重复关键词检测已能发现的明显违规，专注于语义层面的隐含违规"""

    def _call_llm(self, description: str, category: str, market: str) -> Optional[str]:
        """调用 LLM API（使用 httpx 同步客户端，在 FastAPI 线程池中执行）"""
        prompt = self._build_prompt(description, category, market)

        try:
            import httpx
        except ImportError:
            logger.warning("httpx 未安装，AI 语义检测不可用。请运行: pip install httpx")
            return None

        headers = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "你是跨境电商合规审查AI助手，只输出JSON格式的检测结果。"},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "response_format": {"type": "json_object"},
        }

        try:
            with httpx.Client(timeout=60.0) as client:
                resp = client.post(
                    f"{self.api_base}/chat/completions",
                    headers=headers,
                    json=payload,
                )

            if resp.status_code == 200:
                data = resp.json()
                return data["choices"][0]["message"]["content"]
            else:
                logger.error(f"LLM API 调用失败: status={resp.status_code}, body={resp.text[:200]}")
                return None
        except Exception as e:
            logger.error(f"LLM API 调用异常: {e}")
            return None

    def _parse_llm_response(self, response_text: str, market: str) -> List[Violation]:
        """解析 LLM 返回的 JSON 结果"""
        try:
            # 尝试提取 JSON（处理 markdown 代码块包裹的情况）
            text = response_text.strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
                text = text.strip()
            if text.endswith("```"):
                text = text[:-3].strip()

            data = json.loads(text)
        except json.JSONDecodeError as e:
            logger.error(f"LLM 返回非 JSON: {e}, text={response_text[:200]}")
            return []

        violations = []
        for item in data.get("violations", []):
            vtype_str = item.get("type", "implicit_violation")
            # 映射到 ViolationType，未知类型归为 FALSE_ADVERTISING
            vtype_map = {
                "medical_claim": ViolationType.MEDICAL_CLAIM,
                "absolute_term": ViolationType.ABSOLUTE_TERM,
                "false_advertising": ViolationType.FALSE_ADVERTISING,
                "missing_label": ViolationType.MISSING_LABEL,
                "banned_ingredient": ViolationType.BANNED_INGREDIENT,
                "implicit_violation": ViolationType.FALSE_ADVERTISING,
            }
            vtype = vtype_map.get(vtype_str, ViolationType.FALSE_ADVERTISING)

            severity_str = item.get("severity", "medium")
            severity = Severity.HIGH if severity_str == "high" else Severity.LOW if severity_str == "low" else Severity.MEDIUM

            violations.append(Violation(
                type=vtype,
                type_label=item.get("type_label", "AI语义检测违规"),
                content=item.get("content", ""),
                regulation=item.get("regulation", "AI 语义分析判定"),
                regulation_detail=item.get("regulation_detail", item.get("reasoning", "")),
                severity=severity,
                severity_label=item.get("severity_label", "中"),
                suggestion=item.get("suggestion", ""),
                score=min(item.get("score", 15), 30),
            ))

        return violations

    def get_replacement(self, content: str) -> Optional[str]:
        """AI 检测器不提供替换词（由 LLM 在 suggestion 中给出）"""
        return None
