"""规则相关 Schema"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class BannedWordCreate(BaseModel):
    word: str = Field(..., min_length=1, max_length=200)
    violation_type: str = Field(..., min_length=1, max_length=50)
    market: str = Field(..., min_length=1, max_length=10)
    category: str = Field(..., min_length=1, max_length=50)
    severity: int = Field(default=50, ge=0, le=100)


class BannedWordUpdate(BaseModel):
    word: Optional[str] = Field(None, min_length=1, max_length=200)
    severity: Optional[int] = Field(None, ge=0, le=100)
    is_active: Optional[bool] = None


class BannedWordResponse(BaseModel):
    id: str
    word: str
    violation_type: str
    market: str
    category: str
    severity: int
    is_active: bool
    version: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WordReplacementCreate(BaseModel):
    original_word: str = Field(..., min_length=1, max_length=200)
    replacement: str = Field(..., min_length=1, max_length=200)
    market: str = Field(..., min_length=1, max_length=10)
    category: str = Field(..., min_length=1, max_length=50)


class WordReplacementUpdate(BaseModel):
    replacement: Optional[str] = Field(None, min_length=1, max_length=200)
    is_active: Optional[bool] = None


class WordReplacementResponse(BaseModel):
    id: str
    original_word: str
    replacement: str
    market: str
    category: str
    version: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RuleVersionResponse(BaseModel):
    id: str
    table_name: str
    record_id: str
    action: str
    old_value: Optional[str]
    new_value: Optional[str]
    change_reason: Optional[str]
    changed_by: Optional[str]
    changed_at: datetime

    class Config:
        from_attributes = True


class OptimizationSuggestionResponse(BaseModel):
    id: str
    violation_type: str
    content: str
    suggestion_type: str
    reason: Optional[str]
    confidence: float
    feedback_count: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class RuleListResponse(BaseModel):
    items: List[BannedWordResponse]
    total: int
    page: int
    page_size: int


class ReplacementListResponse(BaseModel):
    items: List[WordReplacementResponse]
    total: int
    page: int
    page_size: int
