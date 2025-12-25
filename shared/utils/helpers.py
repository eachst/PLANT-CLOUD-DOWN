"""
共享工具函数
"""
import os
import hashlib
import uuid
import json
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
from functools import wraps
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# 密码加密（按需导入，避免所有服务都强依赖passlib）
_pwd_context = None

def _get_pwd_context():
    global _pwd_context
    if _pwd_context is None:
        from passlib.context import CryptContext
        _pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    return _pwd_context

# JWT配置
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

# 数据库配置
# 默认使用Docker环境下的数据库配置，便于开发和测试
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@postgres:5432/plant_disease")
# 生成异步数据库URL，确保替换正确的前缀
ASYNC_DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

# Redis配置
# 默认使用Docker环境下的Redis配置，便于开发和测试
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

# 腾讯云COS配置
COS_SECRET_ID = os.getenv("COS_SECRET_ID")
COS_SECRET_KEY = os.getenv("COS_SECRET_KEY")
COS_REGION = os.getenv("COS_REGION", "ap-beijing")
COS_BUCKET = os.getenv("COS_BUCKET")


def get_password_hash(password: str) -> str:
    """生成密码哈希"""
    return _get_pwd_context().hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return _get_pwd_context().verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """创建访问令牌"""
    from jose import jwt

    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """验证令牌"""
    from jose import JWTError, jwt

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


def generate_uuid() -> str:
    """生成UUID"""
    return str(uuid.uuid4())


def generate_api_key() -> str:
    """生成API密钥"""
    return f"pd-{uuid.uuid4().hex}"


def get_file_hash(file_content: bytes) -> str:
    """获取文件哈希值"""
    return hashlib.sha256(file_content).hexdigest()


def get_current_time() -> datetime:
    """获取当前时间"""
    return datetime.utcnow()


def format_datetime(dt: datetime) -> str:
    """格式化日期时间"""
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def safe_json_loads(json_str: str, default: Any = None) -> Any:
    """安全加载JSON"""
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return default


def safe_json_dumps(obj: Any, default: str = "{}") -> str:
    """安全转储JSON"""
    try:
        return json.dumps(obj, ensure_ascii=False)
    except (TypeError, ValueError):
        return default


# 数据库工具
def get_db_engine():
    """获取数据库引擎"""
    return create_engine(DATABASE_URL)


def get_async_db_engine():
    """获取异步数据库引擎"""
    return create_async_engine(ASYNC_DATABASE_URL)


def get_db_session():
    """获取数据库会话"""
    engine = get_db_engine()
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()


async def get_async_db_session():
    """获取异步数据库会话"""
    engine = get_async_db_engine()
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session


# Redis工具
async def get_redis_client():
    """获取Redis客户端"""
    import redis.asyncio as redis_async

    return redis_async.from_url(REDIS_URL)


async def redis_set(key: str, value: Any, expire: Optional[int] = None):
    """设置Redis键值"""
    redis = await get_redis_client()
    if isinstance(value, (dict, list)):
        value = json.dumps(value)
    await redis.set(key, value, ex=expire)
    await redis.close()


async def redis_get(key: str, default: Any = None) -> Any:
    """获取Redis值"""
    redis = await get_redis_client()
    value = await redis.get(key)
    await redis.close()
    
    if value is None:
        return default
    
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return value.decode("utf-8")


async def redis_delete(key: str):
    """删除Redis键"""
    redis = await get_redis_client()
    await redis.delete(key)
    await redis.close()


async def redis_exists(key: str) -> bool:
    """检查Redis键是否存在"""
    redis = await get_redis_client()
    exists = await redis.exists(key)
    await redis.close()
    return bool(exists)


# 腾讯云COS工具
def get_cos_client():
    """获取腾讯云COS客户端"""
    import boto3

    return boto3.client(
        "s3",
        aws_access_key_id=COS_SECRET_ID,
        aws_secret_access_key=COS_SECRET_KEY,
        region_name=COS_REGION,
        endpoint_url=f"https://cos.{COS_REGION}.myqcloud.com"
    )


def upload_file_to_cos(file_content: bytes, file_name: str, content_type: str = "application/octet-stream") -> Optional[str]:
    """上传文件到腾讯云COS"""
    try:
        cos_client = get_cos_client()
        cos_client.put_object(
            Bucket=COS_BUCKET,
            Key=file_name,
            Body=file_content,
            ContentType=content_type
        )
        # 返回文件URL
        return f"https://{COS_BUCKET}.cos.{COS_REGION}.myqcloud.com/{file_name}"
    except Exception as e:
        logger.error(f"上传文件到COS失败: {e}")
        return None


def download_file_from_cos(file_name: str) -> Optional[bytes]:
    """从腾讯云COS下载文件"""
    try:
        cos_client = get_cos_client()
        response = cos_client.get_object(Bucket=COS_BUCKET, Key=file_name)
        return response["Body"].read()
    except Exception as e:
        logger.error(f"从COS下载文件失败: {e}")
        return None


def delete_file_from_cos(file_name: str) -> bool:
    """从腾讯云COS删除文件"""
    try:
        cos_client = get_cos_client()
        cos_client.delete_object(Bucket=COS_BUCKET, Key=file_name)
        return True
    except Exception as e:
        logger.error(f"从COS删除文件失败: {e}")
        return False


def list_cos_files(prefix: str = "") -> List[Dict[str, Any]]:
    """列出腾讯云COS中的文件"""
    try:
        cos_client = get_cos_client()
        response = cos_client.list_objects_v2(Bucket=COS_BUCKET, Prefix=prefix)
        return response.get("Contents", [])
    except Exception as e:
        logger.error(f"列出COS文件失败: {e}")
        return []


# HTTP请求工具
async def http_get(url: str, headers: Optional[Dict[str, str]] = None, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """发送GET请求"""
    import aiohttp

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, params=params) as response:
            if response.status == 200:
                return await response.json()
            else:
                error_text = await response.text()
                logger.error(f"GET请求失败: {url}, 状态码: {response.status}, 错误: {error_text}")
                return {"error": f"请求失败，状态码: {response.status}"}


async def http_post(url: str, data: Optional[Dict[str, Any]] = None, 
                   json_data: Optional[Dict[str, Any]] = None,
                   headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """发送POST请求"""
    import aiohttp

    async with aiohttp.ClientSession() as session:
        async with session.post(url, data=data, json=json_data, headers=headers) as response:
            if response.status in [200, 201]:
                return await response.json()
            else:
                error_text = await response.text()
                logger.error(f"POST请求失败: {url}, 状态码: {response.status}, 错误: {error_text}")
                return {"error": f"请求失败，状态码: {response.status}"}


# 装饰器
def log_execution_time(func):
    """记录函数执行时间的装饰器"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = datetime.utcnow()
        try:
            result = await func(*args, **kwargs)
            end_time = datetime.utcnow()
            execution_time = (end_time - start_time).total_seconds()
            logger.info(f"{func.__name__} 执行时间: {execution_time:.2f}秒")
            return result
        except Exception as e:
            end_time = datetime.utcnow()
            execution_time = (end_time - start_time).total_seconds()
            logger.error(f"{func.__name__} 执行失败，耗时: {execution_time:.2f}秒，错误: {str(e)}")
            raise
    return wrapper


def retry_on_failure(max_retries: int = 3, delay: float = 1.0):
    """失败重试装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        logger.warning(f"{func.__name__} 执行失败，正在重试 ({attempt + 1}/{max_retries}): {str(e)}")
                        await asyncio.sleep(delay * (2 ** attempt))  # 指数退避
                    else:
                        logger.error(f"{func.__name__} 执行失败，已达到最大重试次数: {str(e)}")
            raise last_exception
        return wrapper
    return decorator


# 异步任务工具
async def run_in_background(func, *args, **kwargs):
    """在后台运行任务"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, func, *args, **kwargs)


# 文件处理工具
def get_file_extension(filename: str) -> str:
    """获取文件扩展名"""
    return os.path.splitext(filename)[1].lower()


def is_image_file(filename: str) -> bool:
    """判断是否为图像文件"""
    image_extensions = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp"}
    return get_file_extension(filename) in image_extensions


def generate_unique_filename(original_filename: str) -> str:
    """生成唯一文件名"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    uuid_str = uuid.uuid4().hex[:8]
    extension = get_file_extension(original_filename)
    return f"{timestamp}_{uuid_str}{extension}"


# 数据验证工具
def validate_email(email: str) -> bool:
    """验证邮箱格式"""
    import re
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return re.match(pattern, email) is not None


def validate_phone(phone: str) -> bool:
    """验证手机号格式"""
    import re
    pattern = r"^1[3-9]\d{9}$"
    return re.match(pattern, phone) is not None


# 字符串处理工具
def truncate_string(text: str, max_length: int = 100) -> str:
    """截断字符串"""
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."


def clean_html_tags(html: str) -> str:
    """清理HTML标签"""
    import re
    clean = re.compile('<.*?>')
    return re.sub(clean, '', html)


# 数据转换工具
def bytes_to_human_readable(bytes_size: int) -> str:
    """将字节转换为人类可读格式"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} PB"


def seconds_to_human_readable(seconds: int) -> str:
    """将秒数转换为人类可读格式"""
    if seconds < 60:
        return f"{seconds}秒"
    elif seconds < 3600:
        minutes = seconds // 60
        return f"{minutes}分钟"
    elif seconds < 86400:
        hours = seconds // 3600
        return f"{hours}小时"
    else:
        days = seconds // 86400
        return f"{days}天"