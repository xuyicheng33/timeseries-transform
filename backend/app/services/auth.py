"""
认证服务模块
提供密码哈希、JWT Token 生成和验证等功能

重要：所有需要 JWT 密钥的操作都应通过本模块进行，
不要直接调用 settings.get_jwt_secret_key()，以确保密钥一致性。
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings


# 密码哈希上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 缓存 JWT 密钥（进程内单例，避免每次调用都生成新的随机密钥）
_jwt_secret_key: Optional[str] = None


def init_jwt_secret() -> str:
    """
    初始化 JWT 密钥（应在应用启动时调用）
    
    此函数确保 JWT 密钥在进程内只初始化一次，
    后续所有 Token 操作都使用同一个密钥。
    
    Returns:
        JWT 密钥字符串
    """
    global _jwt_secret_key
    if _jwt_secret_key is None:
        _jwt_secret_key = settings.get_jwt_secret_key()
    return _jwt_secret_key


def _get_jwt_secret() -> str:
    """
    获取 JWT 密钥（内部使用，带缓存）
    
    如果尚未初始化，会自动调用 init_jwt_secret()。
    但推荐在应用启动时显式调用 init_jwt_secret()。
    """
    global _jwt_secret_key
    if _jwt_secret_key is None:
        return init_jwt_secret()
    return _jwt_secret_key


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """生成密码哈希"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    创建 Access Token
    
    Args:
        data: 要编码的数据（通常包含 sub: user_id）
        expires_delta: 过期时间增量
    
    Returns:
        JWT Token 字符串
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({
        "exp": expire,
        "type": "access"
    })
    
    encoded_jwt = jwt.encode(
        to_encode,
        _get_jwt_secret(),
        algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    """
    创建 Refresh Token
    
    Args:
        data: 要编码的数据（通常包含 sub: user_id）
    
    Returns:
        JWT Token 字符串
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode.update({
        "exp": expire,
        "type": "refresh"
    })
    
    encoded_jwt = jwt.encode(
        to_encode,
        _get_jwt_secret(),
        algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt


def decode_token(token: str) -> Optional[dict]:
    """
    解码 JWT Token
    
    Args:
        token: JWT Token 字符串
    
    Returns:
        解码后的数据，如果无效则返回 None
    """
    try:
        payload = jwt.decode(
            token,
            _get_jwt_secret(),
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except JWTError:
        return None


def verify_access_token(token: str) -> Optional[int]:
    """
    验证 Access Token 并返回用户 ID
    
    Args:
        token: JWT Token 字符串
    
    Returns:
        用户 ID，如果无效则返回 None
    """
    payload = decode_token(token)
    if payload is None:
        return None
    
    # 检查 token 类型
    if payload.get("type") != "access":
        return None
    
    # 获取用户 ID
    user_id = payload.get("sub")
    if user_id is None:
        return None
    
    try:
        return int(user_id)
    except (ValueError, TypeError):
        return None


def verify_refresh_token(token: str) -> Optional[int]:
    """
    验证 Refresh Token 并返回用户 ID
    
    Args:
        token: JWT Token 字符串
    
    Returns:
        用户 ID，如果无效则返回 None
    """
    payload = decode_token(token)
    if payload is None:
        return None
    
    # 检查 token 类型
    if payload.get("type") != "refresh":
        return None
    
    # 获取用户 ID
    user_id = payload.get("sub")
    if user_id is None:
        return None
    
    try:
        return int(user_id)
    except (ValueError, TypeError):
        return None
