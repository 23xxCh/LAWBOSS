"""
图片合规检测服务
OCR 提取图片文字 → 文本合规检测

支持：
- 上传图片（PNG/JPG/WEBP）
- OCR 提取文字（Tesseract / PIL）
- 调用 ComplianceChecker 进行合规检测
- 返回检测结果 + OCR 提取的原文
"""
import io
import logging
from typing import Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


def extract_text_from_image(image_bytes: bytes) -> Tuple[str, str]:
    """
    从图片中提取文字（OCR）

    Returns:
        (extracted_text, ocr_engine)
    """
    try:
        from PIL import Image
    except ImportError:
        logger.warning("Pillow 未安装，图片检测不可用")
        return "", "unavailable"

    try:
        import pytesseract
    except ImportError:
        logger.warning("pytesseract 未安装，尝试使用 PIL 内置 OCR")
        return _ocr_with_pil(image_bytes)

    try:
        image = Image.open(io.BytesIO(image_bytes))
        # 预处理：转灰度 + 二值化提高 OCR 准确率
        if image.mode != 'L':
            image = image.convert('L')
        # 二值化
        image = image.point(lambda x: 0 if x < 128 else 255, '1')

        # 中英文 OCR
        text = pytesseract.image_to_string(image, lang='chi_sim+eng')
        return text.strip(), "tesseract"
    except Exception as e:
        logger.error(f"Tesseract OCR 失败: {e}")
        return _ocr_with_pil(image_bytes)


def _ocr_with_pil(image_bytes: bytes) -> Tuple[str, str]:
    """PIL 降级 OCR（仅做图片预处理，返回空文本提示用户安装 Tesseract）"""
    try:
        from PIL import Image
        image = Image.open(io.BytesIO(image_bytes))
        logger.info(f"图片尺寸: {image.size}, 模式: {image.mode}")
    except Exception as e:
        logger.error(f"图片读取失败: {e}")
    return "", "pil_fallback"


def validate_image(image_bytes: bytes, max_size_mb: int = 10) -> Tuple[bool, str]:
    """
    验证上传的图片

    Returns:
        (is_valid, error_message)
    """
    # 大小检查
    if len(image_bytes) > max_size_mb * 1024 * 1024:
        return False, f"图片大小超过限制（最大 {max_size_mb}MB）"

    try:
        from PIL import Image
        image = Image.open(io.BytesIO(image_bytes))
        image.verify()  # 验证图片完整性
    except ImportError:
        # Pillow 未安装，仅做基本检查
        if len(image_bytes) < 100:
            return False, "图片文件过小，可能已损坏"
        return True, ""
    except Exception as e:
        return False, f"图片格式无效: {e}"

    return True, ""
