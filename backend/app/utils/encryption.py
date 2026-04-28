"""API Key 加密工具 — Fernet 对称加密"""
import base64
import hashlib
from cryptography.fernet import Fernet

from ..config import JWT_SECRET_KEY


def _derive_key() -> bytes:
    """从 JWT_SECRET_KEY 派生 Fernet 兼容的 32 字节密钥"""
    raw = hashlib.sha256(JWT_SECRET_KEY.encode()).digest()
    return base64.urlsafe_b64encode(raw)


_fernet = Fernet(_derive_key())


def encrypt_api_key(plaintext: str) -> str:
    """加密 API Key，返回 base64 密文字符串"""
    if not plaintext:
        return ""
    return _fernet.encrypt(plaintext.encode()).decode()


def decrypt_api_key(ciphertext: str) -> str:
    """解密 API Key，返回明文字符串"""
    if not ciphertext:
        return ""
    try:
        return _fernet.decrypt(ciphertext.encode()).decode()
    except Exception:
        return ""


def mask_api_key(api_key: str) -> str:
    """掩码 API Key，仅显示最后 4 位"""
    if not api_key:
        return ""
    if len(api_key) <= 8:
        return "****"
    return "****" + api_key[-4:]
