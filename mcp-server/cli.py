"""
CrossGuard CLI — 出海法盾合规检测命令行工具

用法:
  crossguard check <description> [--market EU] [--category 化妆品]
  crossguard batch <file.jsonl> [--json]

退出码: 0=合规, 1=低风险, 2=中风险, 3=高风险, 4=错误
"""
import argparse
import json
import sys
from pathlib import Path

# 复用后端合规检测引擎
_backend_dir = Path(__file__).resolve().parent.parent / "backend"
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

from app.services.compliance_checker import ComplianceChecker
from app.config import DATA_DIR


def _risk_exit_code(risk_score: int) -> int:
    """语义退出码: 0=合规, 1=低, 2=中, 3=高"""
    if risk_score >= 70:
        return 3
    elif risk_score >= 40:
        return 2
    elif risk_score > 0:
        return 1
    return 0


def _report_to_dict(report) -> dict:
    """将 ComplianceReport 转为 dict"""
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


def cmd_check(args: argparse.Namespace, checker: ComplianceChecker) -> int:
    """执行单条检测"""
    report = checker.check_text(
        description=args.description,
        product_category=args.category,
        target_market=args.market,
    )

    if args.json:
        print(json.dumps(_report_to_dict(report), ensure_ascii=False, indent=2))
    else:
        print(f"市场: {report.market}  类别: {report.category}")
        print(f"风险评分: {report.risk_score}/100 ({report.risk_level})")
        print(f"风险描述: {report.risk_description}")
        print()

        if report.violations:
            print(f"违规项 ({len(report.violations)}):")
            for v in report.violations:
                print(f"  [{v.severity_label}] {v.type_label}: {v.content}")
                print(f"    法规: {v.regulation}")
                print(f"    建议: {v.suggestion}")
                print()
        else:
            print("未检测到违规内容")
            print()

        if report.compliant_version:
            print(f"合规版本: {report.compliant_version}")
            print()

        if report.required_labels:
            print(f"必需标签: {', '.join(report.required_labels)}")
        if report.required_certifications:
            print(f"必需认证: {', '.join(report.required_certifications)}")
        if report.suggestions:
            print(f"修改建议: {', '.join(report.suggestions)}")

    return _risk_exit_code(report.risk_score)


def cmd_batch(args: argparse.Namespace, checker: ComplianceChecker) -> int:
    """执行批量检测"""
    file_path = Path(args.file)
    if not file_path.exists():
        print(f"错误: 文件不存在: {args.file}", file=sys.stderr)
        return 4

    results = []
    total = 0
    errors = 0
    high_risk = 0
    medium_risk = 0
    low_risk = 0
    compliant = 0

    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            total += 1
            try:
                item = json.loads(line)
                report = checker.check_text(
                    description=item.get("description", ""),
                    product_category=item.get("category", "化妆品"),
                    target_market=item.get("market", "EU"),
                )
                results.append(_report_to_dict(report))

                score = report.risk_score
                if score >= 70:
                    high_risk += 1
                elif score >= 40:
                    medium_risk += 1
                elif score > 0:
                    low_risk += 1
                else:
                    compliant += 1
            except json.JSONDecodeError as e:
                errors += 1
                print(f"警告: 第 {total} 行 JSON 解析失败: {e}", file=sys.stderr)
            except Exception as e:
                errors += 1
                print(f"警告: 第 {total} 行检测失败: {e}", file=sys.stderr)

    if args.json:
        print(json.dumps({
            "total": total,
            "errors": errors,
            "results": results,
            "summary": {
                "compliant": compliant,
                "low_risk": low_risk,
                "medium_risk": medium_risk,
                "high_risk": high_risk,
            },
        }, ensure_ascii=False, indent=2))
    else:
        print(f"批量检测完成: 共 {total} 条, 错误 {errors} 条")
        print(f"  合规: {compliant}")
        print(f"  低风险: {low_risk}")
        print(f"  中风险: {medium_risk}")
        print(f"  高风险: {high_risk}")

    return 3 if high_risk > 0 else 2 if medium_risk > 0 else 1 if low_risk > 0 else 0


def main():
    checker = ComplianceChecker(data_dir=DATA_DIR)

    parser = argparse.ArgumentParser(prog="crossguard", description="出海法盾合规检测 CLI")
    sub = parser.add_subparsers(dest="command")

    # check 子命令
    check_p = sub.add_parser("check", help="检测单条产品描述")
    check_p.add_argument("description", help="产品描述文本")
    check_p.add_argument("--market", default="EU", help="目标市场 (默认: EU)")
    check_p.add_argument("--category", default="化妆品", help="产品类别 (默认: 化妆品)")
    check_p.add_argument("--json", action="store_true", help="输出 JSON 格式")

    # batch 子命令
    batch_p = sub.add_parser("batch", help="批量检测 (JSONL 格式)")
    batch_p.add_argument("file", help="JSONL 文件路径")
    batch_p.add_argument("--json", action="store_true", help="输出 JSON 格式")

    args = parser.parse_args()
    if args.command == "check":
        sys.exit(cmd_check(args, checker))
    elif args.command == "batch":
        sys.exit(cmd_batch(args, checker))
    else:
        parser.print_help()
        sys.exit(4)


if __name__ == "__main__":
    main()
