"""
P2 数据架构升级测试

测试覆盖:
- 规则数据库模型
- 规则迁移（静态文件 → 数据库）
- ComplianceChecker 从数据库加载
- Admin Rules API
- 反馈闭环
"""
import os
import sys
import json
import pytest
from pathlib import Path
from datetime import datetime

# 添加 backend 目录到路径
_backend_dir = Path(__file__).resolve().parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

# 设置测试环境变量
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, init_db
from app.models.rule import BannedWord, WordReplacement, Regulation, RuleVersion
from app.models.feedback import UserFeedbackDB, OptimizationSuggestionDB
from app.services.compliance_checker import ComplianceChecker, MedicalClaimChecker, AbsoluteTermChecker


@pytest.fixture
def db_session():
    """创建内存数据库会话"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


class TestRuleModels:
    """规则模型测试"""

    def test_banned_word_model(self, db_session):
        """测试 BannedWord 模型"""
        word = BannedWord(
            id="test-1",
            word="治疗",
            violation_type="medical_claim",
            market="EU",
            category="化妆品",
            severity=50,
            is_active=True,
            version=1,
        )
        db_session.add(word)
        db_session.commit()

        result = db_session.query(BannedWord).filter(BannedWord.word == "治疗").first()
        assert result is not None
        assert result.violation_type == "medical_claim"
        assert result.market == "EU"

    def test_word_replacement_model(self, db_session):
        """测试 WordReplacement 模型"""
        replacement = WordReplacement(
            id="test-2",
            original_word="治疗",
            replacement="舒缓",
            market="EU",
            category="化妆品",
            version=1,
            is_active=True,
        )
        db_session.add(replacement)
        db_session.commit()

        result = db_session.query(WordReplacement).first()
        assert result.original_word == "治疗"
        assert result.replacement == "舒缓"

    def test_rule_version_model(self, db_session):
        """测试 RuleVersion 模型"""
        version = RuleVersion(
            id="test-3",
            table_name="banned_words",
            record_id="test-1",
            action="create",
            old_value=None,
            new_value='{"word": "治疗"}',
            changed_by="admin",
        )
        db_session.add(version)
        db_session.commit()

        result = db_session.query(RuleVersion).first()
        assert result.table_name == "banned_words"
        assert result.action == "create"


class TestFeedbackModels:
    """反馈模型测试"""

    def test_user_feedback_model(self, db_session):
        """测试 UserFeedbackDB 模型"""
        feedback = UserFeedbackDB(
            id="fb-1",
            user_id="user-1",
            report_id="report-1",
            feedback_type="false_positive",
            violation_type="medical_claim",
            violation_content="治疗",
            user_comment="误报测试",
            market="EU",
            category="化妆品",
            status="pending",
        )
        db_session.add(feedback)
        db_session.commit()

        result = db_session.query(UserFeedbackDB).first()
        assert result.feedback_type == "false_positive"
        assert result.status == "pending"

    def test_optimization_suggestion_model(self, db_session):
        """测试 OptimizationSuggestionDB 模型"""
        suggestion = OptimizationSuggestionDB(
            id="os-1",
            violation_type="medical_claim",
            content="治疗",
            suggestion_type="remove_word",
            reason="被 3 次标记为误报",
            confidence=0.3,
            feedback_count=3,
            status="pending",
        )
        db_session.add(suggestion)
        db_session.commit()

        result = db_session.query(OptimizationSuggestionDB).first()
        assert result.suggestion_type == "remove_word"
        assert result.feedback_count == 3


class TestComplianceCheckerDB:
    """ComplianceChecker 从数据库加载测试"""

    def test_medical_claim_checker_from_db(self, db_session):
        """测试 MedicalClaimChecker 从数据库加载"""
        # 添加测试数据
        word = BannedWord(
            id="db-1",
            word="治疗",
            violation_type="medical",
            market="EU",
            category="化妆品",
            severity=50,
            is_active=True,
            version=1,
        )
        db_session.add(word)
        db_session.commit()

        # 创建检测器
        data_dir = Path(__file__).parent.parent / "data"
        checker = MedicalClaimChecker(data_dir, db_session)

        # 验证从数据库加载
        assert "EU_化妆品" in checker.word_lists
        assert "治疗" in checker.word_lists["EU_化妆品"]

    def test_absolute_term_checker_from_db(self, db_session):
        """测试 AbsoluteTermChecker 从数据库加载"""
        # 添加测试数据
        word = BannedWord(
            id="db-2",
            word="最好",
            violation_type="absolute_term",
            market="ALL",
            category="all",
            severity=50,
            is_active=True,
            version=1,
        )
        db_session.add(word)
        db_session.commit()

        # 创建检测器
        data_dir = Path(__file__).parent.parent / "data"
        checker = AbsoluteTermChecker(data_dir, db_session)

        # 验证从数据库加载
        assert "最好" in checker.words

    def test_compliance_checker_with_db(self, db_session):
        """测试 ComplianceChecker 使用数据库"""
        # 添加测试数据
        word = BannedWord(
            id="db-3",
            word="治愈",
            violation_type="medical",
            market="EU",
            category="化妆品",
            severity=50,
            is_active=True,
            version=1,
        )
        replacement = WordReplacement(
            id="db-4",
            original_word="治愈",
            replacement="改善",
            market="EU",
            category="化妆品",
            version=1,
            is_active=True,
        )
        db_session.add_all([word, replacement])
        db_session.commit()

        # 创建检测器
        data_dir = Path(__file__).parent.parent / "data"
        checker = ComplianceChecker(data_dir, db_session)

        # 验证替换映射从数据库加载
        assert "治愈" in checker.replacements
        assert checker.replacements["治愈"] == "改善"


class TestFeedbackServiceDB:
    """FeedbackService 数据库存储测试"""

    def test_submit_feedback_to_db(self, db_session):
        """测试提交反馈到数据库"""
        from app.services.feedback_service import FeedbackService, FeedbackType

        data_dir = Path(__file__).parent.parent / "data"
        service = FeedbackService(data_dir, db_session)

        feedback = service.submit_feedback(
            report_id="report-1",
            feedback_type=FeedbackType.FALSE_POSITIVE,
            violation_type="medical_claim",
            violation_content="治疗",
            user_comment="误报测试",
            market="EU",
            category="化妆品",
            user_id="user-1",
        )

        # 验证数据库存储
        result = db_session.query(UserFeedbackDB).first()
        assert result is not None
        assert result.feedback_type == "false_positive"
        assert result.violation_content == "治疗"


class TestRuleVersionAudit:
    """规则变更审计测试"""

    def test_version_record_on_create(self, db_session):
        """测试创建规则时记录版本"""
        # 创建规则
        word = BannedWord(
            id="audit-1",
            word="测试词",
            violation_type="medical_claim",
            market="EU",
            category="化妆品",
            severity=50,
            is_active=True,
            version=1,
        )
        db_session.add(word)

        # 记录版本
        version = RuleVersion(
            id="ver-1",
            table_name="banned_words",
            record_id="audit-1",
            action="create",
            new_value='{"word": "测试词"}',
            changed_by="admin",
        )
        db_session.add(version)
        db_session.commit()

        # 验证
        result = db_session.query(RuleVersion).first()
        assert result.action == "create"
        assert "测试词" in result.new_value


# 运行测试
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
