import os
from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext
from jose import jwt

# JWT 配置（从环境变量读取，默认值用于开发环境）
JWT_SECRET = os.getenv("JWT_SECRET", "change_me_in_prod")  # 生产环境必须修改
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "10080"))  # 默认 7 天

# 密码哈希上下文（使用 bcrypt 算法）
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """对明文密码进行哈希处理"""
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """验证明文密码与哈希值是否匹配"""
    return pwd_context.verify(password, password_hash)


def create_access_token(subject: str) -> str:
    """生成 JWT 访问令牌（subject 通常为用户 ID）"""
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=JWT_EXPIRE_MINUTES)
    payload = {
        "sub": subject,  # 主题（用户唯一标识）
        "iat": int(now.timestamp()),  # 签发时间
        "exp": int(expire.timestamp())  # 过期时间
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """解析 JWT 令牌，返回 payload（需自行处理过期等异常）"""
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])