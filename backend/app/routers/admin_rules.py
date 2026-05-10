"""Admin Rules API — 规则管理端点

权限要求: admin 角色
"""
import uuid
import json
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.user import User
from ..models.rule import BannedWord, WordReplacement, RuleVersion
from ..models.feedback import OptimizationSuggestionDB
from ..schemas.rule import (
    BannedWordCreate, BannedWordUpdate, BannedWordResponse,
    WordReplacementCreate, WordReplacementUpdate, WordReplacementResponse,
    RuleVersionResponse, OptimizationSuggestionResponse,
    RuleListResponse, ReplacementListResponse,
)
from ..routers.auth import get_current_user
from ..services import rule_cache

router = APIRouter(prefix="/admin/rules", tags=["admin-rules"])


def require_admin(current_user: User = Depends(get_current_user)):
    """要求管理员权限"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return current_user


# ===== 禁用词管理 =====

@router.get("/banned-words", response_model=RuleListResponse)
def list_banned_words(
    market: Optional[str] = None,
    category: Optional[str] = None,
    violation_type: Optional[str] = None,
    is_active: Optional[bool] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """列出禁用词"""
    query = db.query(BannedWord)

    if market:
        query = query.filter(BannedWord.market == market.upper())
    if category:
        query = query.filter(BannedWord.category == category)
    if violation_type:
        query = query.filter(BannedWord.violation_type == violation_type)
    if is_active is not None:
        query = query.filter(BannedWord.is_active == is_active)

    total = query.count()
    items = query.order_by(BannedWord.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return RuleListResponse(
        items=[BannedWordResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/banned-words", response_model=BannedWordResponse)
def create_banned_word(
    data: BannedWordCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """添加禁用词"""
    # 检查是否已存在
    existing = db.query(BannedWord).filter(
        BannedWord.word == data.word,
        BannedWord.violation_type == data.violation_type,
        BannedWord.market == data.market.upper(),
        BannedWord.category == data.category,
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="该禁用词已存在")

    now = datetime.now(timezone.utc)
    word = BannedWord(
        id=str(uuid.uuid4()),
        word=data.word,
        violation_type=data.violation_type,
        market=data.market.upper(),
        category=data.category,
        severity=data.severity,
        is_active=True,
        version=1,
        created_at=now,
        updated_at=now,
        created_by=admin.id,
    )
    db.add(word)

    # 记录变更历史
    _record_version(db, "banned_words", word.id, "create", None, word, admin.id)

    # 使缓存失效
    rule_cache.invalidate_banned_words_cache(data.market.upper(), data.category)

    db.commit()
    db.refresh(word)
    return BannedWordResponse.model_validate(word)


@router.put("/banned-words/{word_id}", response_model=BannedWordResponse)
def update_banned_word(
    word_id: str,
    data: BannedWordUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """更新禁用词"""
    word = db.query(BannedWord).filter(BannedWord.id == word_id).first()
    if not word:
        raise HTTPException(status_code=404, detail="禁用词不存在")

    old_value = json.dumps({
        "word": word.word,
        "severity": word.severity,
        "is_active": word.is_active,
    }, ensure_ascii=False)

    if data.word is not None:
        word.word = data.word
    if data.severity is not None:
        word.severity = data.severity
    if data.is_active is not None:
        word.is_active = data.is_active

    word.version += 1
    word.updated_at = datetime.now(timezone.utc)

    new_value = json.dumps({
        "word": word.word,
        "severity": word.severity,
        "is_active": word.is_active,
    }, ensure_ascii=False)

    _record_version(db, "banned_words", word.id, "update", old_value, new_value, admin.id)

    # 使缓存失效
    rule_cache.invalidate_banned_words_cache(word.market, word.category)

    db.commit()
    db.refresh(word)
    return BannedWordResponse.model_validate(word)


@router.delete("/banned-words/{word_id}")
def delete_banned_word(
    word_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """删除禁用词（软删除）"""
    word = db.query(BannedWord).filter(BannedWord.id == word_id).first()
    if not word:
        raise HTTPException(status_code=404, detail="禁用词不存在")

    old_value = json.dumps({
        "word": word.word,
        "is_active": word.is_active,
    }, ensure_ascii=False)

    word.is_active = False
    word.version += 1
    word.updated_at = datetime.now(timezone.utc)

    _record_version(db, "banned_words", word.id, "delete", old_value, None, admin.id, "软删除")

    # 使缓存失效
    rule_cache.invalidate_banned_words_cache(word.market, word.category)

    db.commit()
    return {"message": "已删除", "id": word_id}


# ===== 替换建议管理 =====

@router.get("/replacements", response_model=ReplacementListResponse)
def list_replacements(
    market: Optional[str] = None,
    category: Optional[str] = None,
    is_active: Optional[bool] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """列出替换建议"""
    query = db.query(WordReplacement)

    if market:
        query = query.filter(WordReplacement.market == market.upper())
    if category:
        query = query.filter(WordReplacement.category == category)
    if is_active is not None:
        query = query.filter(WordReplacement.is_active == is_active)

    total = query.count()
    items = query.order_by(WordReplacement.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return ReplacementListResponse(
        items=[WordReplacementResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/replacements", response_model=WordReplacementResponse)
def create_replacement(
    data: WordReplacementCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """添加替换建议"""
    existing = db.query(WordReplacement).filter(
        WordReplacement.original_word == data.original_word,
        WordReplacement.market == data.market.upper(),
        WordReplacement.category == data.category,
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="该替换建议已存在")

    now = datetime.now(timezone.utc)
    replacement = WordReplacement(
        id=str(uuid.uuid4()),
        original_word=data.original_word,
        replacement=data.replacement,
        market=data.market.upper(),
        category=data.category,
        version=1,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    db.add(replacement)
    _record_version(db, "word_replacements", replacement.id, "create", None, replacement, admin.id)

    # 使缓存失效
    rule_cache.invalidate_replacements_cache(data.market.upper(), data.category)

    db.commit()
    db.refresh(replacement)
    return WordReplacementResponse.model_validate(replacement)


@router.delete("/replacements/{replacement_id}")
def delete_replacement(
    replacement_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """删除替换建议"""
    replacement = db.query(WordReplacement).filter(WordReplacement.id == replacement_id).first()
    if not replacement:
        raise HTTPException(status_code=404, detail="替换建议不存在")

    market = replacement.market
    category = replacement.category

    db.delete(replacement)
    _record_version(db, "word_replacements", replacement.id, "delete", None, None, admin.id)

    # 使缓存失效
    rule_cache.invalidate_replacements_cache(market, category)

    db.commit()
    return {"message": "已删除", "id": replacement_id}


# ===== 规则变更历史 =====

@router.get("/versions", response_model=list[RuleVersionResponse])
def list_rule_versions(
    table_name: Optional[str] = None,
    record_id: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """列出规则变更历史"""
    query = db.query(RuleVersion)

    if table_name:
        query = query.filter(RuleVersion.table_name == table_name)
    if record_id:
        query = query.filter(RuleVersion.record_id == record_id)

    items = query.order_by(RuleVersion.changed_at.desc()).limit(limit).all()
    return [RuleVersionResponse.model_validate(item) for item in items]


# ===== 优化建议管理 =====

@router.get("/suggestions", response_model=list[OptimizationSuggestionResponse])
def list_optimization_suggestions(
    status: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """列出规则优化建议"""
    query = db.query(OptimizationSuggestionDB)

    if status:
        query = query.filter(OptimizationSuggestionDB.status == status)

    items = query.order_by(OptimizationSuggestionDB.confidence.desc()).limit(limit).all()
    return [OptimizationSuggestionResponse.model_validate(item) for item in items]


@router.post("/suggestions/{suggestion_id}/approve")
def approve_suggestion(
    suggestion_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """批准优化建议并应用"""
    suggestion = db.query(OptimizationSuggestionDB).filter(
        OptimizationSuggestionDB.id == suggestion_id
    ).first()

    if not suggestion:
        raise HTTPException(status_code=404, detail="建议不存在")

    if suggestion.status != "pending":
        raise HTTPException(status_code=400, detail=f"建议状态为 {suggestion.status}，无法批准")

    # 应用建议
    if suggestion.suggestion_type == "remove_word":
        # 软删除对应的禁用词
        db.query(BannedWord).filter(
            BannedWord.word == suggestion.content,
            BannedWord.violation_type == suggestion.violation_type,
        ).update({"is_active": False, "updated_at": datetime.now(timezone.utc)})

    elif suggestion.suggestion_type == "add_word":
        # 添加新禁用词
        now = datetime.now(timezone.utc)
        word = BannedWord(
            id=str(uuid.uuid4()),
            word=suggestion.content,
            violation_type=suggestion.violation_type,
            market="ALL",
            category="all",
            severity=50,
            is_active=True,
            version=1,
            created_at=now,
            updated_at=now,
            created_by=admin.id,
        )
        db.add(word)

    # 更新建议状态
    suggestion.status = "approved"
    suggestion.reviewed_at = datetime.now(timezone.utc)
    suggestion.reviewed_by = admin.id

    db.commit()

    # 使缓存失效
    rule_cache.invalidate_all_rules_cache()

    return {"message": "已批准并应用", "id": suggestion_id}


@router.post("/suggestions/{suggestion_id}/reject")
def reject_suggestion(
    suggestion_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """拒绝优化建议"""
    suggestion = db.query(OptimizationSuggestionDB).filter(
        OptimizationSuggestionDB.id == suggestion_id
    ).first()

    if not suggestion:
        raise HTTPException(status_code=404, detail="建议不存在")

    if suggestion.status != "pending":
        raise HTTPException(status_code=400, detail=f"建议状态为 {suggestion.status}，无法拒绝")

    suggestion.status = "rejected"
    suggestion.reviewed_at = datetime.now(timezone.utc)
    suggestion.reviewed_by = admin.id

    db.commit()
    return {"message": "已拒绝", "id": suggestion_id}


# ===== 辅助函数 =====

def _record_version(
    db: Session,
    table_name: str,
    record_id: str,
    action: str,
    old_value,
    new_value,
    changed_by: str,
    change_reason: str = None,
):
    """记录规则变更历史"""
    version = RuleVersion(
        id=str(uuid.uuid4()),
        table_name=table_name,
        record_id=record_id,
        action=action,
        old_value=old_value if isinstance(old_value, str) else (json.dumps(old_value, ensure_ascii=False) if old_value else None),
        new_value=new_value if isinstance(new_value, str) else (json.dumps(new_value, ensure_ascii=False) if new_value else None),
        change_reason=change_reason,
        changed_by=changed_by,
        changed_at=datetime.now(timezone.utc),
    )
    db.add(version)
