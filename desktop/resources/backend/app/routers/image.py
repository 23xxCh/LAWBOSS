"""图片合规检测 API 路由"""
import asyncio
import io
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Form
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas.check import CheckResponse, ViolationItem
from ..services.compliance_checker import ComplianceChecker, ViolationType
from ..services.image_checker import extract_text_from_image, validate_image
from ..services import report_service
from ..config import SUPPORTED_MARKETS, SUPPORTED_CATEGORIES
from ..models.user import User
from ..routers.auth import get_current_user
from ..utils.converters import report_to_response

router = APIRouter(tags=["图片检测"])


def _get_checker(request: Request) -> ComplianceChecker:
    return request.app.state.checker


@router.post("/check/image", response_model=CheckResponse, summary="图片合规检测")
async def check_image(
    http_request: Request,
    file: UploadFile = File(..., description="产品图片（PNG/JPG/WEBP）"),
    category: str = Form(..., description="产品类别"),
    market: str = Form(default="EU", description="目标市场"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    上传产品图片进行合规检测：
    1. OCR 提取图片中的文字
    2. 对提取的文字进行合规检测
    3. 返回检测结果（含 OCR 提取的原文）
    """
    # 验证市场和类别
    if market not in SUPPORTED_MARKETS:
        raise HTTPException(status_code=400, detail=f"不支持的市场: {market}，支持: {SUPPORTED_MARKETS}")
    if category not in SUPPORTED_CATEGORIES.get(market, []):
        raise HTTPException(
            status_code=400,
            detail=f"市场 {market} 不支持类别: {category}，支持: {SUPPORTED_CATEGORIES.get(market, [])}",
        )

    # 读取图片
    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="图片文件为空")

    # 验证图片
    is_valid, error = validate_image(image_bytes)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error)

    # OCR 提取文字
    extracted_text, ocr_engine = extract_text_from_image(image_bytes)
    if not extracted_text:
        raise HTTPException(
            status_code=422,
            detail="OCR 未能从图片中提取到文字。请确保图片包含清晰的文字内容，或尝试上传更清晰的图片。",
        )

    # 合规检测
    checker = _get_checker(http_request)
    report = await asyncio.to_thread(
        checker.check_text,
        description=extracted_text,
        product_category=category,
        target_market=market,
    )

    # 保存报告
    report_service.save_report(db, extracted_text, report)

    response = report_to_response(report)
    # 在 suggestions 前添加 OCR 信息
    ocr_info = f"[OCR 提取] 引擎: {ocr_engine}，提取文字长度: {len(extracted_text)} 字符"
    response.suggestions.insert(0, ocr_info)

    return response
