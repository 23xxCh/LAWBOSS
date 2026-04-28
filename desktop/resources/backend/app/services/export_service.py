"""报告导出服务 — PDF 生成"""
import io
from datetime import datetime, timezone
from typing import Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape

from ..config import BASE_DIR
from ..services.compliance_checker import ComplianceReport


# Jinja2 模板环境
TEMPLATES_DIR = BASE_DIR / "templates"
TEMPLATES_DIR.mkdir(exist_ok=True)
env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(["html"]),
)


def generate_report_pdf(
    description: str,
    report: ComplianceReport,
    report_id: Optional[str] = None,
) -> bytes:
    """
    生成合规检测报告 PDF

    使用 Jinja2 渲染 HTML → WeasyPrint 转 PDF
    """
    # 确保模板文件存在
    _ensure_template()

    template = env.get_template("report.html")
    html_content = template.render(
        report_id=report_id or "N/A",
        description=description,
        report=report,
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        risk_color="#ff4d4f" if report.risk_score >= 70 else "#faad14" if report.risk_score >= 40 else "#52c41a",
    )

    try:
        from weasyprint import HTML
        pdf_bytes = HTML(string=html_content).write_pdf()
        return pdf_bytes
    except ImportError:
        # WeasyPrint 未安装，返回 HTML 作为降级
        logger_msg = "WeasyPrint 未安装，返回 HTML 格式报告"
        import logging
        logging.getLogger(__name__).warning(logger_msg)
        return html_content.encode("utf-8")


def _ensure_template():
    """确保报告模板文件存在"""
    template_file = TEMPLATES_DIR / "report.html"
    if not template_file.exists():
        template_file.write_text(_DEFAULT_TEMPLATE, encoding="utf-8")


_DEFAULT_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>合规检测报告 - 出海法盾 CrossGuard</title>
<style>
  body { font-family: "Microsoft YaHei", "SimHei", Arial, sans-serif; margin: 40px; color: #333; }
  h1 { color: #1890ff; border-bottom: 2px solid #1890ff; padding-bottom: 10px; }
  h2 { color: #333; margin-top: 24px; }
  .meta { color: #666; font-size: 14px; margin-bottom: 20px; }
  .risk-score { font-size: 48px; font-weight: bold; color: {{ risk_color }}; }
  .risk-level { font-size: 24px; font-weight: bold; color: {{ risk_color }}; }
  .violation { border: 1px solid #d9d9d9; border-radius: 4px; padding: 12px; margin: 8px 0; }
  .violation-high { border-left: 4px solid #ff4d4f; }
  .violation-medium { border-left: 4px solid #faad14; }
  .violation-low { border-left: 4px solid #1890ff; }
  .severity-high { color: #ff4d4f; font-weight: bold; }
  .severity-medium { color: #faad14; font-weight: bold; }
  .severity-low { color: #1890ff; font-weight: bold; }
  table { width: 100%; border-collapse: collapse; margin: 12px 0; }
  th, td { border: 1px solid #d9d9d9; padding: 8px; text-align: left; }
  th { background: #f5f5f5; }
  .tag { display: inline-block; padding: 2px 8px; border-radius: 4px; margin: 2px; font-size: 13px; }
  .tag-blue { background: #e6f7ff; border: 1px solid #91d5ff; color: #1890ff; }
  .tag-purple { background: #f9f0ff; border: 1px solid #d3adf7; color: #722ed1; }
  .compliant { background: #f6ffed; border: 1px solid #b7eb8f; padding: 12px; border-radius: 4px; }
  .footer { margin-top: 40px; padding-top: 12px; border-top: 1px solid #d9d9d9; color: #999; font-size: 12px; }
</style>
</head>
<body>
<h1>合规检测报告</h1>
<div class="meta">
  <p>报告编号：{{ report_id }}</p>
  <p>生成时间：{{ generated_at }}</p>
  <p>目标市场：{{ report.market }} | 产品类别：{{ report.category }}</p>
</div>

<h2>风险评分</h2>
<p><span class="risk-score">{{ report.risk_score }}</span> / 100</p>
<p><span class="risk-level">{{ report.risk_level }}</span> — {{ report.risk_description }}</p>

<h2>原始产品描述</h2>
<p style="background: #f5f5f5; padding: 12px; border-radius: 4px;">{{ description }}</p>

{% if report.violations %}
<h2>违规项 ({{ report.violations|length }})</h2>
{% for v in report.violations %}
<div class="violation violation-{{ v.severity.value if v.severity.value else v.severity }}">
  <p><span class="severity-{{ v.severity.value if v.severity.value else v.severity }}">[{{ v.severity_label }}]</span>
  <strong>{{ v.type_label }}</strong></p>
  <table>
    <tr><th width="100">违规内容</th><td>{{ v.content }}</td></tr>
    <tr><th>法规依据</th><td>{{ v.regulation }}</td></tr>
    <tr><th>法规详情</th><td>{{ v.regulation_detail }}</td></tr>
    <tr><th>修改建议</th><td style="color: #52c41a;">{{ v.suggestion }}</td></tr>
    <tr><th>扣分</th><td>{{ v.score }}</td></tr>
  </table>
</div>
{% endfor %}
{% else %}
<h2>检测结果</h2>
<p style="color: #52c41a; font-weight: bold;">恭喜！未检测到违规内容</p>
{% endif %}

{% if report.compliant_version != description %}
<h2>合规版本</h2>
<div class="compliant">{{ report.compliant_version }}</div>
{% endif %}

{% if report.required_labels %}
<h2>必需标签</h2>
<p>{% for label in report.required_labels %}<span class="tag tag-blue">{{ label }}</span>{% endfor %}</p>
{% endif %}

{% if report.required_certifications %}
<h2>必需认证</h2>
<p>{% for cert in report.required_certifications %}<span class="tag tag-purple">{{ cert }}</span>{% endfor %}</p>
{% endif %}

{% if report.suggestions %}
<h2>修改建议</h2>
<ul>{% for s in report.suggestions %}<li>{{ s }}</li>{% endfor %}</ul>
{% endif %}

<div class="footer">
  <p>出海法盾 CrossGuard — 跨境电商智能合规审查平台</p>
  <p style="color: #ff4d4f; font-weight: bold;">⚠️ 免责声明：本工具提供的检测结果和修改建议仅供参考，不构成法律意见，不保证检测的完整性和准确性。产品合规性应以目标市场监管机构的最终判定为准。建议在重要合规决策前咨询专业法律顾问。</p>
</div>
</body>
</html>"""
