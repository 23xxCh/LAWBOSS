"""LLM 配置 Pydantic Schema"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class LLMProviderInfo(BaseModel):
    """LLM 提供商预设信息"""
    id: str
    name: str
    default_api_base: str
    default_model: str
    models: List[str] = []
    requires_api_key: bool = True


class LLMConfigCreate(BaseModel):
    """创建/更新 LLM 配置"""
    provider: str = Field(default="openai", description="提供商ID")
    api_key: str = Field(default="", description="API Key（明文，HTTPS传输）")
    api_base: str = Field(default="https://api.openai.com/v1", description="API 地址")
    model: str = Field(default="gpt-4o-mini", description="模型名称")
    max_tokens: int = Field(default=2048, ge=128, le=128000, description="最大 Token 数")
    temperature: float = Field(default=0.1, ge=0.0, le=2.0, description="温度参数")


class LLMConfigUpdate(BaseModel):
    """部分更新 LLM 配置"""
    provider: Optional[str] = None
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    model: Optional[str] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None


class LLMConfigResponse(BaseModel):
    """LLM 配置响应（API Key 始终掩码）"""
    provider: str
    api_key_masked: str = Field(default="", description="掩码后的 API Key")
    api_base: str
    model: str
    max_tokens: int
    temperature: float
    is_active: bool
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class LLMTestRequest(BaseModel):
    """测试 LLM 连接请求"""
    provider: str = Field(default="openai", description="提供商ID")
    api_key: str = Field(default="", description="API Key")
    api_base: str = Field(default="https://api.openai.com/v1", description="API 地址")
    model: str = Field(default="gpt-4o-mini", description="模型名称")
    max_tokens: int = Field(default=2048, ge=128, le=128000, description="最大 Token 数")
    temperature: float = Field(default=0.1, ge=0.0, le=2.0, description="温度参数")


class LLMTestResponse(BaseModel):
    """LLM 连接测试响应"""
    success: bool
    message: str
    latency_ms: Optional[int] = None
    model_info: Optional[str] = None


class MessageResponse(BaseModel):
    """通用消息响应"""
    message: str
