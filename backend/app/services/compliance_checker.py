"""
合规检测引擎
核心功能：检测产品描述是否符合目标市场法规

架构：可插拔检测器模式，每个检测器继承 BaseChecker
匹配策略：词边界匹配（\b），避免子串误报
"""
import re
import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod


# ===== 数据结构 =====

class ViolationType(str, Enum):
    MEDICAL_CLAIM = "medical_claim"
    ABSOLUTE_TERM = "absolute_term"
    MISSING_LABEL = "missing_label"
    BANNED_INGREDIENT = "banned_ingredient"
    FALSE_ADVERTISING = "false_advertising"


class Severity(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class Violation:
    type: ViolationType
    type_label: str
    content: str
    regulation: str
    regulation_detail: str
    severity: Severity
    severity_label: str
    suggestion: str
    score: int


@dataclass
class ComplianceReport:
    risk_score: int
    risk_level: str
    risk_description: str
    market: str
    category: str
    violations: List[Violation]
    compliant_version: str
    required_labels: List[str]
    required_certifications: List[str]
    suggestions: List[str]


# ===== 检测器基类 =====

class BaseChecker(ABC):
    """检测器抽象基类"""

    @abstractmethod
    def check(self, description: str, category: str, market: str) -> List[Violation]:
        """执行检测，返回违规列表"""
        pass

    def get_replacement(self, content: str) -> Optional[str]:
        """获取合规替换词，子类可覆盖"""
        return None


# ===== 工具函数 =====

def _load_word_list(file_path: Path) -> List[str]:
    """从文件加载词列表"""
    words = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                words.append(line)
    return words


def _load_replacements(file_path: Path) -> Dict[str, str]:
    """从 JSON 文件加载替换映射"""
    if file_path.exists():
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data.get("replacements", {})
    return {}


def _find_word_matches(word: str, text: str) -> List[Tuple[str, int, int]]:
    """
    使用词边界匹配查找词汇，避免子串误报。
    返回 [(匹配文本, 起始位置, 结束位置), ...]

    对于中文词汇，使用直接匹配（中文无空格分词）。
    对于英文词汇，使用 \\b 词边界匹配。
    混合词汇（含中英文）使用直接匹配。
    """
    has_cjk = bool(re.search(r'[\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff]', word))
    has_latin = bool(re.search(r'[a-zA-Z]', word))

    if has_latin and not has_cjk:
        # 纯英文：使用词边界匹配
        pattern = re.compile(r'\b' + re.escape(word) + r'\b', re.IGNORECASE)
    else:
        # 中文或混合：直接匹配
        pattern = re.compile(re.escape(word), re.IGNORECASE)

    results = []
    for match in pattern.finditer(text):
        results.append((match.group(), match.start(), match.end()))
    return results


def _is_span_overlapping(start: int, end: int, spans: List[Tuple[int, int]]) -> bool:
    """检查区间是否与已有区间重叠"""
    return any(not (end <= s or start >= e) for s, e in spans)


# ===== 具体检测器 =====

class MedicalClaimChecker(BaseChecker):
    """医疗宣称检测器"""

    # 英文类别名 -> 中文类别名映射
    CATEGORY_MAP = {
        "cosmetics": "化妆品",
        "food": "食品",
        "supplement": "膳食补充剂",
        "electronics": "电子产品",
    }

    # 各市场法规引用
    REGULATIONS = {
        "EU": {
            "化妆品": ("欧盟化妆品法规(EC) No 1223/2009 第20条", "化妆品不得宣称具有治疗、预防疾病的功能，不得使用医疗术语"),
            "食品": ("EU Regulation 1924/2006 营养与健康宣称法规", "食品不得宣称治疗、预防疾病，健康宣称须经EFSA批准"),
            "电子产品": ("EU Electromagnetic Compatibility Directive 2014/30/EU", "电子产品不得宣称未经认证的安全或性能指标"),
        },
        "US": {
            "化妆品": ("FD&C Act, 21 CFR 700-740", "化妆品不得宣称具有治疗或预防疾病的功能，否则需按药品监管"),
            "食品": ("FDA FD&C Act Section 403(r), 21 CFR 101", "食品健康宣称须经FDA批准，不得宣称治疗疾病"),
            "膳食补充剂": ("FDA DSHEA 1994, 21 CFR 101.93", "膳食补充剂不得宣称诊断、治疗、治愈或预防疾病"),
            "电子产品": ("FCC Part 15, FTC Act Section 5", "电子产品不得宣称未经认证的电磁兼容或安全性能"),
        },
        "SEA_SG": {
            "化妆品": ("ASEAN Cosmetic Directive & Singapore HSA Medicines Act", "化妆品不得宣称具有治疗或预防疾病功能，否则需按药品监管"),
            "食品": ("Singapore SFA Food Regulations", "食品不得宣称治疗或预防疾病功能"),
            "膳食补充剂": ("Singapore HSA Health Products Act", "补充剂不得宣称治疗或预防疾病"),
            "电子产品": ("Singapore Consumer Protection (Safety Requirements)", "电子产品需符合安全要求，不得虚假宣称"),
        },
        "SEA_TH": {
            "化妆品": ("ASEAN Cosmetic Directive & Thai FDA Cosmetics Act B.E. 2558", "化妆品不得宣称具有治疗或预防疾病功能，否则需按药品监管"),
            "食品": ("Thai FDA Food Act B.E. 2522", "食品不得宣称治疗或预防疾病功能"),
            "膳食补充剂": ("Thai FDA Dietary Supplement Regulations", "补充剂不得宣称治疗或预防疾病"),
            "电子产品": ("Thai FDA & TIS Standards", "电子产品需符合TIS标准，不得虚假宣称"),
        },
        "SEA_MY": {
            "化妆品": ("ASEAN Cosmetic Directive & Malaysia NPRA Sale of Drugs Act 1952", "化妆品不得宣称具有治疗或预防疾病功能，否则需按药品监管"),
            "食品": ("Malaysia Food Act 1983 & Food Regulations 1985", "食品不得宣称治疗或预防疾病功能"),
            "膳食补充剂": ("Malaysia NPRA Control of Drugs and Cosmetics Regulations", "补充剂不得宣称治疗或预防疾病"),
            "电子产品": ("Malaysia MCMC & SIRIM Standards", "电子产品需符合SIRIM标准，不得虚假宣称"),
        },
    }

    def __init__(self, data_dir: Path):
        self.word_lists: Dict[str, List[str]] = {}  # key: market_category
        self._load_data(data_dir)

    def _load_data(self, data_dir: Path):
        banned_dir = data_dir / "banned_words"

        # 动态加载所有 {market}_{category}_medical.txt 文件
        for fpath in sorted(banned_dir.glob("*_medical.txt")):
            stem = fpath.stem  # e.g. "eu_cosmetics_medical"
            parts = stem.split("_")
            if len(parts) < 3:
                continue
            market_raw = parts[0]
            category_en = "_".join(parts[1:-1])  # support multi-word categories
            # 映射到中文类别名
            category = self.CATEGORY_MAP.get(category_en, category_en)

            if market_raw == "sea":
                # SEA 共享文件，展开到三个市场
                words = _load_word_list(fpath)
                for m in ("SEA_SG", "SEA_TH", "SEA_MY"):
                    self.word_lists[f"{m}_{category}"] = words
            else:
                market = market_raw.upper()
                self.word_lists[f"{market}_{category}"] = _load_word_list(fpath)

    def check(self, description: str, category: str, market: str) -> List[Violation]:
        violations = []
        matched_spans: List[Tuple[int, int]] = []

        # 查找对应词库
        key = f"{market}_{category}"
        words = self.word_lists.get(key, [])

        # 如果没有特定词库，尝试通用医疗词库
        if not words:
            words = self.word_lists.get(f"{market}_化妆品", [])

        # 获取法规引用
        market_regs = self.REGULATIONS.get(market, self.REGULATIONS["EU"])
        reg_info = market_regs.get(category, market_regs.get("化妆品", ("适用法规", "请勿使用医疗宣称")))
        regulation, detail = reg_info

        for word in words:
            matches = _find_word_matches(word, description)
            for matched_text, start, end in matches:
                if _is_span_overlapping(start, end, matched_spans):
                    continue
                matched_spans.append((start, end))
                violations.append(Violation(
                    type=ViolationType.MEDICAL_CLAIM,
                    type_label="医疗宣称",
                    content=matched_text,
                    regulation=regulation,
                    regulation_detail=detail,
                    severity=Severity.HIGH,
                    severity_label="高",
                    suggestion=f"删除违规宣称'{matched_text}'，使用客观功能描述替代",
                    score=25,
                ))

        return violations


class AbsoluteTermChecker(BaseChecker):
    """绝对化用语检测器"""

    def __init__(self, data_dir: Path):
        self.words: List[str] = []
        self._load_data(data_dir)

    def _load_data(self, data_dir: Path):
        banned_dir = data_dir / "banned_words"
        absolute_file = banned_dir / "absolute_terms.txt"
        if absolute_file.exists():
            self.words = _load_word_list(absolute_file)

    def check(self, description: str, category: str, market: str) -> List[Violation]:
        violations = []
        matched_spans: List[Tuple[int, int]] = []

        regulation_map = {
            "EU": ("欧盟不公平商业行为指令(2005/29/EC)", "不得使用绝对化用语进行夸大宣传"),
            "US": ("FTC Act Section 5, 15 USC 45", "不得使用无法证实的绝对化宣称"),
        }
        reg, detail = regulation_map.get(market, regulation_map["EU"])

        for word in self.words:
            matches = _find_word_matches(word, description)
            for matched_text, start, end in matches:
                if _is_span_overlapping(start, end, matched_spans):
                    continue
                matched_spans.append((start, end))
                violations.append(Violation(
                    type=ViolationType.ABSOLUTE_TERM,
                    type_label="绝对化用语",
                    content=matched_text,
                    regulation=reg,
                    regulation_detail=detail,
                    severity=Severity.MEDIUM,
                    severity_label="中",
                    suggestion=f"将'{matched_text}'改为更客观的描述（如'优质'、'深受消费者喜爱'等）",
                    score=15,
                ))

        return violations


class FalseAdChecker(BaseChecker):
    """虚假广告/功效宣称无依据检测器"""

    # 按市场+类别组织的功效宣称模式
    EFFICACY_PATTERNS = {
        ("化妆品", "EU"): [
            r'\d+\s*天见效', r'\d+\s*秒见效', r'24\s*小时',
            r'立即见效', r'一秒见效', r'\d+\s*天', r'\d+\s*秒',
        ],
        ("化妆品", "US"): [
            r'\d+\s*days?\s*(to\s*)?results?', r'\d+\s*seconds?\s*results?',
            r'24\s*hours?', r'instant\s*results?', r'overnight\s*results?',
            r'\d+\s*days?', r'\d+\s*seconds?',
        ],
        ("化妆品", "SEA_SG"): [
            r'\d+\s*days?\s*(to\s*)?results?', r'\d+\s*天见效',
            r'24\s*hours?', r'24\s*小时', r'instant\s*results?',
            r'立即见效', r'\d+\s*天', r'\d+\s*days?',
        ],
        ("化妆品", "SEA_TH"): [
            r'\d+\s*days?\s*(to\s*)?results?', r'\d+\s*天见效',
            r'24\s*hours?', r'24\s*小时', r'instant\s*results?',
            r'立即见效', r'\d+\s*天', r'\d+\s*days?',
        ],
        ("化妆品", "SEA_MY"): [
            r'\d+\s*days?\s*(to\s*)?results?', r'\d+\s*天见效',
            r'24\s*hours?', r'24\s*小时', r'instant\s*results?',
            r'立即见效', r'\d+\s*天', r'\d+\s*days?',
        ],
        # 食品类虚假功效宣称
        ("食品", "EU"): [
            r'prevents?\s*\w+', r'cures?\s*\w+', r'treats?\s*\w+',
            r'reduces?\s*cholesterol', r'boosts?\s*immune', r'fights?\s*\w+',
            r'\d+\s*days?\s*(to\s*)?results?',
        ],
        ("食品", "US"): [
            r'prevents?\s*\w+', r'cures?\s*\w+', r'treats?\s*\w+',
            r'reduces?\s*cholesterol', r'boosts?\s*immune', r'fights?\s*\w+',
            r'\d+\s*days?\s*results?', r'clinically\s*proven',
        ],
        ("食品", "SEA_SG"): [
            r'prevents?\s*\w+', r'cures?\s*\w+', r'treats?\s*\w+',
            r'boosts?\s*immune', r'\d+\s*days?\s*results?',
        ],
        ("食品", "SEA_TH"): [
            r'prevents?\s*\w+', r'cures?\s*\w+', r'treats?\s*\w+',
            r'boosts?\s*immune', r'\d+\s*days?\s*results?',
        ],
        ("食品", "SEA_MY"): [
            r'prevents?\s*\w+', r'cures?\s*\w+', r'treats?\s*\w+',
            r'boosts?\s*immune', r'\d+\s*days?\s*results?',
        ],
        # 膳食补充剂虚假功效宣称
        ("膳食补充剂", "US"): [
            r'cures?\s*\w+', r'treats?\s*\w+', r'prevents?\s*\w+',
            r'\d+\s*days?\s*results?', r'guaranteed\s*results?',
            r'clinically\s*proven', r'scientifically\s*proven',
            r'fights?\s*\w+', r'replaces?\s*\w+',
        ],
        ("膳食补充剂", "SEA_SG"): [
            r'cures?\s*\w+', r'treats?\s*\w+', r'prevents?\s*\w+',
            r'\d+\s*days?\s*results?', r'clinically\s*proven',
        ],
        ("膳食补充剂", "SEA_TH"): [
            r'cures?\s*\w+', r'treats?\s*\w+', r'prevents?\s*\w+',
            r'\d+\s*days?\s*results?',
        ],
        ("膳食补充剂", "SEA_MY"): [
            r'cures?\s*\w+', r'treats?\s*\w+', r'prevents?\s*\w+',
            r'\d+\s*days?\s*results?',
        ],
        # 电子产品虚假宣称
        ("电子产品", "EU"): [
            r'certified\s*(?!\w+CE)', r'guaranteed\s*safe', r'radiation\s*free',
            r'100%\s*safe', r'perfect\s*compatibility',
        ],
        ("电子产品", "US"): [
            r'certified\s*(?!\w+FCC)', r'guaranteed\s*safe', r'radiation\s*free',
            r'100%\s*safe', r'perfect\s*compatibility',
        ],
        ("电子产品", "SEA_SG"): [
            r'certified\s*(?!\w+Safety)', r'guaranteed\s*safe', r'radiation\s*free',
        ],
        ("电子产品", "SEA_TH"): [
            r'certified\s*(?!\w+TIS)', r'guaranteed\s*safe', r'radiation\s*free',
        ],
        ("电子产品", "SEA_MY"): [
            r'certified\s*(?!\w+SIRIM)', r'guaranteed\s*safe', r'radiation\s*free',
        ],
    }

    REGULATION_MAP = {
        "EU": {
            "化妆品": ("欧盟化妆品宣称法规 (EC) No 655/2013", "化妆品功效宣称必须有充分的证据支持，不得使用具体时限保证效果"),
            "食品": ("EU Regulation 1924/2006 营养与健康宣称法规", "食品健康宣称须有科学证据，禁止未经EFSA批准的宣称"),
            "电子产品": ("EU Consumer Rights Directive 2011/83/EU", "电子产品性能宣称须有技术依据，不得误导消费者"),
        },
        "US": {
            "化妆品": ("FTC Endorsement Guides, 16 CFR 255", "广告宣称必须有科学依据支持，不得使用无法证实的效果保证"),
            "食品": ("FDA FD&C Act, 21 CFR 101", "食品功效宣称须有科学证据或FDA批准"),
            "膳食补充剂": ("FDA DSHEA 1994, 21 CFR 101.93", "补充剂结构/功能宣称须有声明依据，不得作疾病宣称"),
            "电子产品": ("FTC Act Section 5, 15 USC 45", "电子产品性能宣称须有技术测试依据"),
        },
        "SEA_SG": {
            "化妆品": ("Singapore HSA Cosmetics Regulations", "化妆品宣称须符合ACD要求，不得夸大功效"),
            "食品": ("Singapore SFA Food Regulations", "食品宣称须真实准确，不得误导消费者"),
            "膳食补充剂": ("Singapore HSA Health Products Act", "补充剂宣称须有科学依据"),
            "电子产品": ("Singapore Consumer Protection Act", "电子产品宣称须符合安全标准"),
        },
        "SEA_TH": {
            "化妆品": ("Thai FDA Cosmetics Act B.E. 2558", "化妆品宣称须符合ACD要求"),
            "食品": ("Thai FDA Food Act B.E. 2522", "食品宣称须真实准确"),
            "膳食补充剂": ("Thai FDA Dietary Supplement Regulations", "补充剂宣称须有科学依据"),
            "电子产品": ("Thai Consumer Protection Act", "电子产品宣称须符合TIS标准"),
        },
        "SEA_MY": {
            "化妆品": ("Malaysia Cosmetics Regulations 2007", "化妆品宣称须符合ACD要求"),
            "食品": ("Malaysia Food Act 1983", "食品宣称须真实准确，不得误导消费者"),
            "膳食补充剂": ("Malaysia NPRA Product Registration Guidelines", "补充剂宣称须有科学依据"),
            "电子产品": ("Malaysia Consumer Protection Act 1999", "电子产品宣称须符合SIRIM标准"),
        },
    }

    def check(self, description: str, category: str, market: str) -> List[Violation]:
        violations = []
        matched_spans: List[Tuple[int, int]] = []

        patterns = self.EFFICACY_PATTERNS.get((category, market), [])
        # 获取法规引用
        market_regs = self.REGULATION_MAP.get(market, self.REGULATION_MAP["EU"])
        reg, detail = market_regs.get(category, market_regs.get("化妆品", ("适用法规", "广告宣称须有充分依据")))

        for pattern in patterns:
            for match in re.finditer(pattern, description, re.IGNORECASE):
                start, end = match.start(), match.end()
                if _is_span_overlapping(start, end, matched_spans):
                    continue
                matched_spans.append((start, end))
                violations.append(Violation(
                    type=ViolationType.FALSE_ADVERTISING,
                    type_label="功效宣称无依据",
                    content=match.group(),
                    regulation=reg,
                    regulation_detail=detail,
                    severity=Severity.MEDIUM,
                    severity_label="中",
                    suggestion="删除具体时限，或提供临床测试证明；改为'持续使用，效果更佳'等",
                    score=15,
                ))

        return violations


class MissingLabelChecker(BaseChecker):
    """缺失标签检测器"""

    # 各市场+类别的必需标签关键词（在描述中应出现的关键信息）
    LABEL_KEYWORDS = {
        ("化妆品", "EU"): {
            "成分表": ["成分", "ingredient", "INCI", "aqua"],
            "使用期限": ["使用期限", "PAO", "有效期", "expir"],
            "净含量": ["ml", "g", "oz", "毫克", "克", "毫升", "净含量"],
        },
        ("电子产品", "EU"): {
            "CE标志": ["CE"],
        },
        ("化妆品", "US"): {
            "成分表": ["成分", "ingredient", "INCI", "aqua"],
            "净含量": ["ml", "g", "oz", "net", "净含量"],
        },
        ("食品", "US"): {
            "成分表": ["成分", "ingredient"],
            "营养标签": ["nutrition", "营养"],
        },
        ("化妆品", "SEA_SG"): {
            "成分表": ["成分", "ingredient", "INCI", "aqua"],
            "净含量": ["ml", "g", "oz", "net", "净含量"],
        },
        ("化妆品", "SEA_TH"): {
            "成分表": ["成分", "ingredient", "INCI", "aqua"],
            "净含量": ["ml", "g", "oz", "net", "净含量"],
        },
        ("化妆品", "SEA_MY"): {
            "成分表": ["成分", "ingredient", "INCI", "aqua"],
            "净含量": ["ml", "g", "oz", "net", "净含量"],
        },
    }

    def check(self, description: str, category: str, market: str) -> List[Violation]:
        violations = []
        label_requirements = self.LABEL_KEYWORDS.get((category, market), {})

        regulation_map = {
            "EU": ("欧盟消费品标签法规", "产品描述或标签中应包含必需信息"),
            "US": ("FDA/FTC 标签要求", "产品描述或标签中应包含必需信息"),
        }
        reg, detail = regulation_map.get(market, regulation_map["EU"])

        desc_lower = description.lower()
        for label_name, keywords in label_requirements.items():
            found = any(kw.lower() in desc_lower for kw in keywords)
            if not found:
                violations.append(Violation(
                    type=ViolationType.MISSING_LABEL,
                    type_label="缺失标签",
                    content=label_name,
                    regulation=reg,
                    regulation_detail=detail,
                    severity=Severity.MEDIUM,
                    severity_label="中",
                    suggestion=f"在产品描述中添加{label_name}相关信息",
                    score=10,
                ))

        return violations


class BannedIngredientChecker(BaseChecker):
    """禁用成分检测器"""

    # 英文类别名 -> 中文类别名映射
    CATEGORY_MAP = {
        "cosmetics": "化妆品",
        "food": "食品",
        "supplement": "膳食补充剂",
        "electronics": "电子产品",
    }

    # 各市场法规引用
    REGULATIONS = {
        "EU": {
            "化妆品": ("欧盟化妆品法规(EC) No 1223/2009 附件II", "附件II列出了化妆品中禁用的物质"),
            "食品": ("EU Regulation 1333/2008 食品添加剂法规", "食品中禁用或限用的添加剂和污染物"),
            "电子产品": ("EU RoHS Directive 2011/65/EU & REACH Regulation", "电子产品中禁用的有害物质"),
        },
        "US": {
            "化妆品": ("FDA 21 CFR 700-740", "FDA 规定了化妆品中禁用或限用的成分"),
            "食品": ("FDA FD&C Act, 21 CFR 189", "FDA 禁止在食品中使用的物质"),
            "膳食补充剂": ("FDA DSHEA 1994, 21 CFR 111", "膳食补充剂中禁用或限用的成分"),
            "电子产品": ("FCC Part 15 & RoHS requirements", "电子产品中禁用的有害物质"),
        },
        "SEA_SG": {
            "化妆品": ("ASEAN Cosmetic Directive & Singapore HSA", "东盟化妆品指令禁用成分列表"),
            "食品": ("Singapore SFA Food Regulations", "新加坡食品中禁用成分"),
            "膳食补充剂": ("Singapore HSA Health Products Act", "补充剂中禁用成分"),
            "电子产品": ("Singapore RoHS & Safety Requirements", "电子产品中禁用物质"),
        },
        "SEA_TH": {
            "化妆品": ("ASEAN Cosmetic Directive & Thai FDA", "东盟化妆品指令禁用成分列表"),
            "食品": ("Thai FDA Food Act B.E. 2522", "泰国食品中禁用成分"),
            "膳食补充剂": ("Thai FDA Dietary Supplement Regulations", "补充剂中禁用成分"),
            "电子产品": ("Thai Industrial Standards", "电子产品中禁用物质"),
        },
        "SEA_MY": {
            "化妆品": ("ASEAN Cosmetic Directive & Malaysia NPRA", "东盟化妆品指令禁用成分列表"),
            "食品": ("Malaysia Food Act 1983 & Food Regulations 1985", "马来西亚食品中禁用成分"),
            "膳食补充剂": ("Malaysia NPRA Product Registration", "补充剂中禁用成分"),
            "电子产品": ("Malaysia SIRIM & MCMC Standards", "电子产品中禁用物质"),
        },
    }

    def __init__(self, data_dir: Path):
        self.ingredient_lists: Dict[str, List[str]] = {}
        self._load_data(data_dir)

    def _load_data(self, data_dir: Path):
        banned_dir = data_dir / "banned_words"

        # 动态加载所有 {market}_{category}_ingredients.txt 文件
        for fpath in sorted(banned_dir.glob("*_ingredients.txt")):
            stem = fpath.stem  # e.g. "eu_cosmetics_ingredients"
            parts = stem.split("_")
            if len(parts) < 3:
                continue
            market_raw = parts[0]
            category_en = "_".join(parts[1:-1])  # support multi-word categories
            # 映射到中文类别名
            category = self.CATEGORY_MAP.get(category_en, category_en)

            if market_raw == "sea":
                words = _load_word_list(fpath)
                for m in ("SEA_SG", "SEA_TH", "SEA_MY"):
                    self.ingredient_lists[f"{m}_{category}"] = words
            else:
                market = market_raw.upper()
                self.ingredient_lists[f"{market}_{category}"] = _load_word_list(fpath)

    def check(self, description: str, category: str, market: str) -> List[Violation]:
        violations = []
        matched_spans: List[Tuple[int, int]] = []

        key = f"{market}_{category}"
        ingredients = self.ingredient_lists.get(key, [])

        # 获取法规引用
        market_regs = self.REGULATIONS.get(market, self.REGULATIONS["EU"])
        reg_info = market_regs.get(category, market_regs.get("化妆品", ("适用法规", "请检查禁用成分")))
        regulation, detail = reg_info

        for ingredient in ingredients:
            matches = _find_word_matches(ingredient, description)
            for matched_text, start, end in matches:
                if _is_span_overlapping(start, end, matched_spans):
                    continue
                matched_spans.append((start, end))
                violations.append(Violation(
                    type=ViolationType.BANNED_INGREDIENT,
                    type_label="禁用成分",
                    content=matched_text,
                    regulation=regulation,
                    regulation_detail=detail,
                    severity=Severity.HIGH,
                    severity_label="高",
                    suggestion=f"产品含有禁用成分'{matched_text}'，请立即移除该成分",
                    score=30,
                ))

        return violations


# ===== 主检测引擎 =====

class ComplianceChecker:
    """
    合规检测引擎
    通过注册 BaseChecker 检测器实现可插拔架构
    """

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.checkers: List[BaseChecker] = []
        self.replacements: Dict[str, str] = {}
        self._init_checkers()
        self._load_replacements()

    def _init_checkers(self):
        """注册所有检测器（两级检测流水线：关键词初筛 + AI 深度复筛）"""
        # 第一级：关键词快速初筛
        self.checkers = [
            MedicalClaimChecker(self.data_dir),
            AbsoluteTermChecker(self.data_dir),
            FalseAdChecker(),
            MissingLabelChecker(),
            BannedIngredientChecker(self.data_dir),
        ]
        # 第二级：AI 语义深度复筛（需配置 LLM_API_KEY 启用）
        try:
            from .ai_semantic_checker import AISemanticChecker
            ai_checker = AISemanticChecker(self.data_dir)
            if ai_checker.enabled:
                self.checkers.append(ai_checker)
        except ImportError:
            pass  # AI 检测器依赖可选，缺失时跳过

    def _load_replacements(self):
        """加载替换映射（从数据文件，回退到内置默认）"""
        replacements_dir = self.data_dir / "replacements"

        # 内置默认替换（权威来源，文件加载仅补充）
        defaults = {
            "治疗": "舒缓", "治愈": "改善", "最好": "优质", "最佳": "精选",
            "第一": "优选", "唯一": "独特", "100%": "高品质", "百分百": "高品质",
            "7天见效": "持续使用，效果更佳", "立即见效": "温和有效",
            "treat": "soothe", "cure": "improve", "best": "premium",
            "guaranteed": "trusted", "perfect": "excellent",
        }
        self.replacements = dict(defaults)

        # 从数据文件加载补充映射（不覆盖默认值）
        for f in replacements_dir.glob("*.json"):
            for k, v in _load_replacements(f).items():
                if k not in self.replacements:
                    self.replacements[k] = v

    def check_text(self,
                   description: str,
                   product_category: str,
                   target_market: str = "EU",
                   check_mode: str = "standard") -> ComplianceReport:
        """
        检测产品描述合规性

        Args:
            description: 产品描述
            product_category: 产品类别
            target_market: 目标市场 (EU/US)
            check_mode: 检测模式 (standard/keyword_only/ai_only)

        Returns:
            ComplianceReport: 合规检测报告
        """
        violations = []

        for checker in self.checkers:
            # keyword_only 模式：跳过 AI 检测器
            if check_mode == "keyword_only" and hasattr(checker, "reconfigure"):
                continue
            # ai_only 模式：仅运行 AI 检测器
            if check_mode == "ai_only" and not hasattr(checker, "reconfigure"):
                continue
            violations.extend(checker.check(description, product_category, target_market))

        # 计算风险评分
        risk_score = self._calculate_risk_score(violations)
        risk_level, risk_description = self._get_risk_level(risk_score)

        # 生成合规版本
        compliant_version = self._generate_compliant_version(description, violations)

        # 获取必需标签和认证
        required_labels = self.get_required_labels(product_category, target_market)
        required_certifications = self.get_required_certifications(product_category, target_market)

        # 生成建议
        suggestions = self._generate_suggestions(violations, product_category, target_market)

        return ComplianceReport(
            risk_score=risk_score,
            risk_level=risk_level,
            risk_description=risk_description,
            market=target_market,
            category=product_category,
            violations=violations,
            compliant_version=compliant_version,
            required_labels=required_labels,
            required_certifications=required_certifications,
            suggestions=suggestions,
        )

    def update_ai_config(self, api_key: str, api_base: str, model: str, max_tokens: int, temperature: float):
        """运行时热重载 AI 语义检测器配置"""
        for checker in self.checkers:
            if hasattr(checker, "reconfigure"):
                checker.reconfigure(api_key, api_base, model, max_tokens, temperature)
                return

    def sync_ai_config_for_user(self, user_id: str, db):
        """检测前同步用户 LLM 配置到 AI 检测器"""
        from .llm_config_service import get_active_config_for_user
        config = get_active_config_for_user(db, user_id)
        if config:
            self.update_ai_config(
                api_key=config["api_key"],
                api_base=config["api_base"],
                model=config["model"],
                max_tokens=config["max_tokens"],
                temperature=config["temperature"],
            )

    def _calculate_risk_score(self, violations: List[Violation]) -> int:
        """计算风险评分"""
        base_score = sum(v.score for v in violations)

        has_medical = any(v.type == ViolationType.MEDICAL_CLAIM for v in violations)
        has_banned = any(v.type == ViolationType.BANNED_INGREDIENT for v in violations)
        has_multiple = len(violations) >= 3

        if has_medical:
            base_score += 20
        if has_banned:
            base_score += 15
        if has_multiple:
            base_score += 10

        return min(base_score, 100)

    def _get_risk_level(self, score: int) -> Tuple[str, str]:
        """获取风险等级"""
        if score >= 70:
            return "高风险", "建议立即整改，否则可能面临下架/罚款"
        elif score >= 40:
            return "中风险", "存在违规可能，建议修改"
        else:
            return "低风险", "基本合规，可进一步优化"

    def _generate_compliant_version(self, description: str, violations: List[Violation]) -> str:
        """生成合规版本（上下文感知替换）"""
        compliant = description
        for old, new in self.replacements.items():
            # 上下文感知：只替换实际被检测为违规的词汇
            # 避免将合规语境中的词汇也替换掉
            is_violated = any(
                old.lower() in v.content.lower()
                for v in violations
            )
            if is_violated:
                compliant = re.sub(re.escape(old), new, compliant, flags=re.IGNORECASE)
            # 对于未被标记为违规的词汇，不做替换
        return compliant

    def get_required_labels(self, category: str, market: str) -> List[str]:
        """获取必需标签（公开方法）"""
        labels = {
            ("化妆品", "EU"): [
                "产品名称", "生产商/欧代名称和地址", "包装内物品净含量",
                "使用期限（或PAO标志）", "注意事项（如有）", "成分表（INCI名称）", "批次号",
            ],
            ("电子产品", "EU"): [
                "CE标志", "欧代信息", "产品型号", "生产商信息", "WEEE标志",
            ],
            ("食品", "EU"): [
                "产品名称", "成分表", "净含量", "生产商/欧代信息",
                "使用期限", "储存条件", "原产国",
            ],
            ("玩具", "EU"): [
                "CE标志", "年龄警告", "生产商信息", "欧代信息", "型号",
            ],
            ("纺织品", "EU"): [
                "纤维成分标签", "原产国", "生产商信息", "洗涤护理标签",
            ],
            ("化妆品", "US"): [
                "产品名称", "净含量", "成分表(INCI)", "生产商信息", "警告声明(如需)",
            ],
            ("电子产品", "US"): [
                "FCC标识(如适用)", "UL认证标志", "产品型号", "生产商信息",
            ],
            ("食品", "US"): [
                "产品名称", "成分表", "净含量", "营养标签", "生产商信息", "过敏原声明",
            ],
            ("膳食补充剂", "US"): [
                "Supplement Facts", "成分表", "净含量", "生产商信息",
                "免责声明: This statement has not been evaluated by the FDA",
            ],
            # 东南亚市场
            ("化妆品", "SEA_SG"): [
                "产品名称", "净含量", "成分表(INCI)", "生产商信息", "原产国",
                "注意事项", "AC Notification编号",
            ],
            ("电子产品", "SEA_SG"): [
                "Safety Mark标志", "产品型号", "生产商信息", "原产国",
            ],
            ("食品", "SEA_SG"): [
                "产品名称", "成分表", "净含量", "营养信息", "生产商信息", "原产国", "过敏原声明",
            ],
            ("膳食补充剂", "SEA_SG"): [
                "产品名称", "成分表", "净含量", "生产商信息", "原产国",
                "HSA通报编号",
            ],
            ("化妆品", "SEA_TH"): [
                "产品名称", "净含量", "成分表(INCI)", "生产商信息", "原产国",
                "注意事项", "CB Notification编号", "泰文标签",
            ],
            ("电子产品", "SEA_TH"): [
                "TIS标志", "产品型号", "生产商信息", "原产国",
            ],
            ("食品", "SEA_TH"): [
                "产品名称", "成分表", "净含量", "营养信息", "生产商信息", "原产国", "泰文标签",
            ],
            ("膳食补充剂", "SEA_TH"): [
                "产品名称", "成分表", "净含量", "生产商信息", "原产国", "Thai FDA通报编号",
            ],
            ("化妆品", "SEA_MY"): [
                "产品名称", "净含量", "成分表(INCI)", "生产商信息", "原产国",
                "注意事项", "NOT Notification编号", "马来文/英文标签",
            ],
            ("电子产品", "SEA_MY"): [
                "SIRIM标志(如适用)", "产品型号", "生产商信息", "原产国",
            ],
            ("食品", "SEA_MY"): [
                "产品名称", "成分表", "净含量", "营养信息", "生产商信息", "原产国",
                "马来文标签", "清真认证(如适用)",
            ],
            ("膳食补充剂", "SEA_MY"): [
                "产品名称", "成分表", "净含量", "生产商信息", "原产国",
                "NPRA通报编号", "马来文/英文标签",
            ],
        }
        return labels.get((category, market), ["请查阅目标市场法规"])

    def get_required_certifications(self, category: str, market: str) -> List[str]:
        """获取必需认证（公开方法）"""
        certs = {
            ("化妆品", "EU"): [
                "CPNP备案（化妆品通报门户）", "CPSR报告（化妆品安全报告）", "PIF（产品信息档案）",
            ],
            ("电子产品", "EU"): [
                "CE认证", "ROHS认证（如适用）", "RED认证（无线产品）",
            ],
            ("食品", "EU"): [
                "HACCP体系", "欧盟食品企业注册",
            ],
            ("玩具", "EU"): [
                "CE认证", "EN 71安全测试", "化学安全评估",
            ],
            ("纺织品", "EU"): [
                "REACH合规", "Oeko-Tex认证(推荐)",
            ],
            ("化妆品", "US"): [
                "FDA设施注册(VCRP)", "MoCRA合规(2024年起)",
            ],
            ("电子产品", "US"): [
                "FCC认证(如适用)", "UL认证(推荐)",
            ],
            ("食品", "US"): [
                "FDA设施注册", "FCE/SID注册(低酸罐头)",
            ],
            ("膳食补充剂", "US"): [
                "FDA设施注册", "cGMP合规(21 CFR 111)",
            ],
            # 东南亚市场
            ("化妆品", "SEA_SG"): [
                "HSA AC Notification（化妆品通报）", "GMP合规", "PIF（产品信息档案）",
            ],
            ("电子产品", "SEA_SG"): [
                "Safety Mark认证", "IMDA认证(通信设备)",
            ],
            ("食品", "SEA_SG"): [
                "SFA进口许可", "HACCP体系",
            ],
            ("膳食补充剂", "SEA_SG"): [
                "HSA Therapeutic Product注册(如适用)", "GMP合规",
            ],
            ("化妆品", "SEA_TH"): [
                "Thai FDA CB Notification（化妆品通报）", "GMP合规", "Halal认证(推荐)",
            ],
            ("电子产品", "SEA_TH"): [
                "TIS认证", "NBTC认证(通信设备)",
            ],
            ("食品", "SEA_TH"): [
                "Thai FDA食品许可", "GMP合规", "Halal认证(推荐)",
            ],
            ("膳食补充剂", "SEA_TH"): [
                "Thai FDA膳食补充剂注册", "GMP合规",
            ],
            ("化妆品", "SEA_MY"): [
                "NPRA NOT Notification（化妆品通报）", "GMP合规", "Halal认证(推荐)",
            ],
            ("电子产品", "SEA_MY"): [
                "SIRIM认证(如适用)", "MCMC认证(通信设备)",
            ],
            ("食品", "SEA_MY"): [
                "MOH食品进口许可", "Halal认证(JAKIM)", "GMP合规",
            ],
            ("膳食补充剂", "SEA_MY"): [
                "NPRA产品注册", "GMP合规", "Halal认证(推荐)",
            ],
        }
        return certs.get((category, market), ["请查阅目标市场法规"])

    def _generate_suggestions(self, violations: List[Violation], category: str, market: str) -> List[str]:
        """生成建议列表"""
        suggestions = []

        for v in violations:
            suggestions.append(f"【{v.type_label}】{v.suggestion}")

        if market == "EU":
            suggestions.append("确保产品标签包含销售国语言（如德语、法语等）")
            suggestions.append("欧代信息必须在产品标签上清晰标注")
            if category == "化妆品":
                suggestions.append("建议在销售前进行CPSR安全评估")
            elif category == "食品":
                suggestions.append("建议获取EU有机认证（如适用）")
            elif category == "电子产品":
                suggestions.append("CE标志是强制性要求，须在产品和包装上清晰可见")
        elif market == "US":
            suggestions.append("确保产品标签使用英文")
            if category == "化妆品":
                suggestions.append("注意：药品级宣称(如治疗功效)需按OTC药品监管，需NDA或ANDA申请")
            elif category == "食品":
                suggestions.append("营养标签(Nutrition Facts)是强制要求，须符合FDA格式")
            elif category == "膳食补充剂":
                suggestions.append("须标注'This statement has not been evaluated by the FDA'")
            elif category == "电子产品":
                suggestions.append("FCC认证是强制要求，电子产品须标注FCC ID")
        elif market.startswith("SEA_"):
            market_names = {"SEA_SG": "新加坡", "SEA_TH": "泰国", "SEA_MY": "马来西亚"}
            mname = market_names.get(market, "东南亚")
            suggestions.append(f"确保符合 ASEAN Cosmetic Directive (ACD) 要求")
            if market == "SEA_SG":
                suggestions.append("新加坡要求产品标签使用英文")
                suggestions.append("需完成 HSA AC Notification 通报后方可销售")
            elif market == "SEA_TH":
                suggestions.append("泰国要求产品标签包含泰文")
                suggestions.append("需完成 Thai FDA CB Notification 通报后方可销售")
                suggestions.append("穆斯林市场建议获取 Halal 认证")
            elif market == "SEA_MY":
                suggestions.append("马来西亚要求产品标签包含马来文和英文")
                suggestions.append("需完成 NPRA NOT Notification 通报后方可销售")
                suggestions.append("马来西亚穆斯林人口占多数，Halal 认证(JAKIM)对食品和化妆品非常重要")
            if category == "化妆品":
                suggestions.append("东南亚市场对美白(whitening)宣称敏感，建议使用 brightening/even-toning 替代")
            elif category == "食品":
                suggestions.append(f"{mname}对食品标签有严格规定，建议咨询当地法规顾问")
            elif category == "膳食补充剂":
                suggestions.append(f"在{mname}销售补充剂需完成当地FDA/NPRA通报或注册")
            elif category == "电子产品":
                suggestions.append(f"在{mname}销售电子产品需获得本地安全认证标志")

        return suggestions
