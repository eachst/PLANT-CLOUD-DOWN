"""
API网关主应用
"""
import os
import sys
import logging
import uuid
import asyncio
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
from typing import Dict, Any, List, Optional

# 第三方库导入
import httpx
import jwt
import redis
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import uvicorn

# 加载环境变量
load_dotenv()

# 添加共享模块路径
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "shared"))

# 本地应用/库导入
from shared.schemas.schemas import HealthCheck, ErrorResponse
from shared.utils.helpers import (
    log_execution_time, get_current_time, safe_json_dumps
)

# 配置日志
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
# 验证日志级别是否有效
valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
if LOG_LEVEL not in valid_log_levels:
    # 使用print而不是logger，因为logger还未初始化
    print(f"警告: 无效的日志级别: {LOG_LEVEL}, 使用默认级别 INFO")
    LOG_LEVEL = "INFO"

# 配置日志
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - [%(request_id)s] - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    # 添加日志文件配置
    handlers=[
        logging.StreamHandler(),  # 输出到控制台
    ]
)
logger = logging.getLogger(__name__)

# 添加一个过滤器，为日志添加请求ID
class RequestIDFilter(logging.Filter):
    """为日志添加请求ID的过滤器"""
    def filter(self, record):
        # 如果没有请求ID，使用unknown
        record.request_id = getattr(record, "request_id", "unknown")
        return True

# 将过滤器添加到根日志记录器
root_logger = logging.getLogger()
root_logger.addFilter(RequestIDFilter())
# 设置根日志记录器的级别
root_logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))

# 调整第三方库的日志级别
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("uvicorn").setLevel(logging.WARNING)
logging.getLogger("fastapi").setLevel(logging.WARNING)

# 配置类，集中管理所有配置
class Config:
    """应用配置类"""
    # 服务配置
    USER_SERVICE_URL = os.getenv("USER_SERVICE_URL", "http://user-service:8001")
    TASK_SERVICE_URL = os.getenv("TASK_SERVICE_URL", "http://task-service:8002")
    MODEL_SERVICE_URL = os.getenv("MODEL_SERVICE_URL", "http://model-service:8003")
    CACHE_SERVICE_URL = os.getenv("CACHE_SERVICE_URL", "http://cache-service:8006")
    
    # JWT配置
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-me-in-production")
    # 支持密钥轮换，从环境变量读取多个密钥，用逗号分隔
    jwt_secret_keys_env = os.getenv("JWT_SECRET_KEYS", JWT_SECRET_KEY)
    # 处理密钥列表，去除空值和重复值
    JWT_SECRET_KEYS = []
    seen_keys = set()
    for key in jwt_secret_keys_env.split(","):
        key = key.strip()
        if key and key not in seen_keys:
            JWT_SECRET_KEYS.append(key)
            seen_keys.add(key)
    # 确保至少有一个密钥
    if not JWT_SECRET_KEYS:
        JWT_SECRET_KEYS = ["your-secret-key-change-me-in-production"]
        logger.error("JWT密钥列表为空，使用默认密钥")
    # 与 .env / user-service 对齐：优先使用 JWT_ALGORITHM 与 ACCESS_TOKEN_EXPIRE_MINUTES
    ALGORITHM = os.getenv("JWT_ALGORITHM", os.getenv("ALGORITHM", "HS256"))
    JWT_EXPIRATION_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", os.getenv("JWT_EXPIRATION_MINUTES", "30")))
    
    # Redis配置
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # 文件上传配置
    MAX_FILE_SIZE = int(os.getenv("MAX_UPLOAD_SIZE", os.getenv("MAX_FILE_SIZE", str(10 * 1024 * 1024))))  # 默认10MB
    ALLOWED_CONTENT_TYPES = [
        "image/jpeg", "image/png", "image/gif",
        "image/webp", "application/octet-stream"
    ]
    
    # CORS配置
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")
    # 将字符串转换为列表
    if CORS_ORIGINS == "*":
        # 允许所有来源，开发环境使用
        ALLOWED_ORIGINS = ["*"]
        logger.warning("CORS允许所有来源，生产环境中请配置具体的来源列表")
    else:
        # 生产环境，配置具体的来源列表
        ALLOWED_ORIGINS = [origin.strip() for origin in CORS_ORIGINS.split(",")]
    
    # HTTP客户端配置
    HTTP_CLIENT_TIMEOUT = httpx.Timeout(
        connect=float(os.getenv("HTTP_CLIENT_CONNECT_TIMEOUT", "5.0")),
        read=float(os.getenv("HTTP_CLIENT_READ_TIMEOUT", "30.0")),
        write=float(os.getenv("HTTP_CLIENT_WRITE_TIMEOUT", "10.0")),
        pool=float(os.getenv("HTTP_CLIENT_POOL_TIMEOUT", "5.0"))
    )
    HTTP_CLIENT_LIMITS = httpx.Limits(
        max_connections=int(os.getenv("HTTP_CLIENT_MAX_CONNECTIONS", "50")),
        max_keepalive_connections=int(os.getenv("HTTP_CLIENT_MAX_KEEPALIVE_CONNECTIONS", "20")),
        keepalive_expiry=float(os.getenv("HTTP_CLIENT_KEEPALIVE_EXPIRY", "30.0"))
    )
    
    # 应用信息
    APP_NAME = "API网关"
    APP_VERSION = "1.0.0"

# 创建配置实例
config = Config()

# 全局变量
app_state: Dict[str, Any] = {
    "redis_client": None,
    "http_client": None
}

# 安全认证
security = HTTPBearer(auto_error=False)

# JWT配置（从config类中使用）


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    logger.info("API网关启动中...")
    
    # 环境变量验证
    logger.info("开始验证环境变量...")
    
    # 验证JWT密钥
    if "your-secret-key-change-me-in-production" in config.JWT_SECRET_KEYS:
        logger.warning("使用默认JWT密钥，生产环境中请务必修改！")
    
    # 定义必填环境变量列表
    required_env_vars = [
        # "JWT_SECRET_KEY",  # 有默认值，不强制要求
        # "ALGORITHM",  # 有默认值，不强制要求
    ]
    
    # 验证必填环境变量
    missing_vars = []
    for var in required_env_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        error_msg = f"缺少必要的环境变量: {', '.join(missing_vars)}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)
    
    # 验证服务URL配置
    service_urls = {
        "USER_SERVICE_URL": config.USER_SERVICE_URL,
        "TASK_SERVICE_URL": config.TASK_SERVICE_URL,
        "MODEL_SERVICE_URL": config.MODEL_SERVICE_URL,
        "CACHE_SERVICE_URL": config.CACHE_SERVICE_URL
    }
    
    for url_name, url_value in service_urls.items():
        if not url_value:
            logger.error(f"环境变量 {url_name} 未配置！")
            raise RuntimeError(f"缺少必要的环境变量: {url_name}")
        elif "http://" not in url_value and "https://" not in url_value:
            logger.error(f"环境变量 {url_name} 不是有效的URL: {url_value}")
            raise RuntimeError(f"无效的URL格式: {url_name}={url_value}")
        elif url_value.startswith("http://localhost") or url_value.startswith("http://127.0.0.1"):
            logger.warning(f"环境变量 {url_name} 使用本地地址，生产环境中请使用正式地址")
    
    # 验证Redis URL（如果配置了）
    if config.REDIS_URL and "redis://" not in config.REDIS_URL and "rediss://" not in config.REDIS_URL:
        logger.error(f"环境变量 REDIS_URL 不是有效的Redis URL: {config.REDIS_URL}")
        raise RuntimeError(f"无效的Redis URL格式: {config.REDIS_URL}")
    
    logger.info("环境变量验证完成")
    
    # 初始化HTTP客户端
    app_state["http_client"] = httpx.AsyncClient(
        timeout=config.HTTP_CLIENT_TIMEOUT,
        limits=config.HTTP_CLIENT_LIMITS,
        follow_redirects=True,           # 自动跟随重定向
        retries=httpx.Retry(
            total=3,                      # 总重试次数
            backoff_factor=0.5,           # 退避因子，重试间隔：0.5秒、1秒、2秒
            status_forcelist=[500, 502, 503, 504],  # 只重试服务器错误，不重试429
            allowed_methods=["GET"],  # 只对幂等的GET方法重试
            raise_on_status=True,        # 对HTTP状态错误抛出异常
        ),
        # SSL配置
        verify=True,                     # 验证SSL证书
        # 压缩配置
        headers={
            "Accept-Encoding": "gzip, deflate, br",
            "User-Agent": f"API-Gateway/{config.APP_VERSION}"
        },
        # 禁用HTTP/2（根据需要调整）
        http2=False,
    )
    
    # 初始化Redis客户端
    try:
        app_state["redis_client"] = redis.from_url(config.REDIS_URL, decode_responses=True)
        # 测试连接（同步方法，不需要await）
        app_state["redis_client"].ping()
        logger.info(f"成功连接到Redis: {config.REDIS_URL}")
    except Exception as e:
        logger.error(f"连接Redis失败: {str(e)}")
        app_state["redis_client"] = None
    
    logger.info("API网关启动完成")
    
    yield
    
    # 关闭时执行
    logger.info("API网关关闭中...")
    
    # 清理资源
    if app_state["http_client"]:
        await app_state["http_client"].close()
    
    if app_state["redis_client"]:
        app_state["redis_client"].close()
        logger.info("Redis连接已关闭")
    
    logger.info("API网关已关闭")


# 路由定义
from fastapi import APIRouter, Depends, Query, Path, Body
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import File, UploadFile, Form

health_router = APIRouter()
auth_router = APIRouter()
user_router = APIRouter()
task_router = APIRouter()
model_router = APIRouter()
prediction_router = APIRouter()
segmentation_router = APIRouter()
notification_router = APIRouter()


async def get_http_client():
    """
    获取HTTP客户端的依赖注入函数
    """
    client = app_state.get("http_client")
    if client is None:
        # 如果客户端未初始化，记录错误并返回None
        logger.error("HTTP客户端未初始化")
        raise HTTPException(status_code=500, detail="服务内部错误")
    return client


async def get_redis_client():
    """
    获取Redis客户端的依赖注入函数
    """
    redis_client = app_state.get("redis_client")
    if redis_client is None:
        # Redis客户端可能未初始化，这是允许的
        logger.debug("Redis客户端未初始化")
        return None
    return redis_client


async def verify_token(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    """验证JWT令牌"""
    if credentials is None:
        return None
    
    token = credentials.credentials
    
    # 尝试使用所有可用密钥进行验证，支持密钥轮换
    for secret_key in config.JWT_SECRET_KEYS:
        try:
            # 实现JWT令牌验证逻辑
            payload = jwt.decode(
                token,
                secret_key,
                algorithms=[config.ALGORITHM],
                options={"verify_exp": True, "verify_aud": False}
            )
            
            # 验证payload中的必要字段
            user_id: str = payload.get("sub")
            if user_id is None:
                logger.error("JWT令牌缺少sub字段")
                continue  # 尝试下一个密钥
            
            username: str = payload.get("username")
            if username is None:
                logger.error("JWT令牌缺少username字段")
                continue  # 尝试下一个密钥
            
            # 验证令牌是否过期
            exp: int = payload.get("exp")
            if exp is None:
                logger.error("JWT令牌缺少exp字段")
                continue  # 尝试下一个密钥
            
            # 返回用户信息
            return {
                "user_id": user_id,
                "username": username,
                "email": payload.get("email"),
                "role": payload.get("role", "user")
            }
        except jwt.ExpiredSignatureError:
            logger.error("JWT令牌已过期")
            # 过期令牌不需要尝试其他密钥
            raise HTTPException(status_code=401, detail="令牌已过期")
        except jwt.InvalidSignatureError:
            # 签名错误，尝试下一个密钥
            logger.debug(f"JWT签名验证失败，尝试下一个密钥")
            continue
        except jwt.InvalidTokenError as e:
            logger.error(f"JWT令牌无效: {str(e)}")
            # 其他令牌错误，尝试下一个密钥
            continue
        except Exception as e:
            logger.error(f"验证令牌失败: {str(e)}")
            # 其他异常，尝试下一个密钥
            continue
    
    # 所有密钥都尝试失败
    logger.error("所有JWT密钥验证失败")
    raise HTTPException(status_code=401, detail="无效的认证凭据")


async def create_error_response(
    request: Optional[Request],
    status_code: int,
    message: str,
    error_code: str,
    log_level: int = logging.ERROR,
    log_message: Optional[str] = None
) -> JSONResponse:
    """
    创建统一的错误响应
    
    Args:
        request: 请求对象
        status_code: HTTP状态码
        message: 错误消息
        error_code: 错误代码
        log_level: 日志级别
        log_message: 日志消息
    
    Returns:
        JSONResponse: 统一格式的错误响应
    """
    # 获取请求ID
    request_id = getattr(request.state, "request_id", "unknown") if request else "unknown"
    
    # 记录日志
    if log_message:
        logger.log(log_level, f"[{request_id}] {log_message}")
    
    # 构建响应内容
    response_data = {
        "message": message,
        "error_code": error_code
    }
    
    return JSONResponse(
        status_code=status_code,
        content=response_data,
        headers={"X-Request-ID": request_id}
    )


async def proxy_request(
    method: str,
    url: str,
    request: Optional[Request] = None,
    path_params: Optional[Dict[str, Any]] = None,
    query_params: Optional[Dict[str, Any]] = None,
    body: Optional[Any] = None,
    headers: Optional[Dict[str, str]] = None,
    files: Optional[Dict[str, UploadFile]] = None
) -> Response:
    """代理请求到目标服务"""
    try:
        client = await get_http_client()
        
        # 构建URL
        final_url = url
        if path_params:
            for key, value in path_params.items():
                # 确保路径参数不包含恶意字符，只允许字母、数字、下划线和连字符
                if not isinstance(value, (str, int, float, bool)):
                    return await create_error_response(
                        request,
                        status_code=400,
                        message=f"无效的路径参数类型: {type(value)}",
                        error_code="INVALID_PATH_PARAM_TYPE",
                        log_level=logging.ERROR,
                        log_message=f"无效的路径参数类型: {type(value)}"
                    )
                
                # 转换为字符串并验证内容
                value_str = str(value)
                if any(c in value_str for c in ["/", "?", "#", "&", "%"]):
                    return await create_error_response(
                        request,
                        status_code=400,
                        message=f"路径参数包含无效字符: {key}",
                        error_code="INVALID_PATH_PARAM_CHAR",
                        log_level=logging.ERROR,
                        log_message=f"路径参数包含无效字符: {key} = {value_str}"
                    )
                
                # 使用安全替换
                placeholder = f"{{{key}}}"
                if placeholder in final_url:
                    final_url = final_url.replace(placeholder, value_str)
                else:
                    logger.warning(f"[{getattr(request.state, 'request_id', 'unknown')}] URL中未找到占位符 {placeholder}")
        
        # 准备请求参数
        kwargs = {"method": method, "url": final_url}
        
        if query_params:
            kwargs["params"] = query_params
        
        # 初始化请求头
        request_headers = {}
        if headers:
            request_headers.update(headers)
        
        # 添加请求ID到请求头
        if request and hasattr(request.state, "request_id"):
            request_headers["X-Request-ID"] = request.state.request_id
        
        if request_headers:
            # 过滤敏感头信息，避免将敏感信息传递给下游服务
            sensitive_headers = [
                "authorization", "proxy-authorization", "cookie", "set-cookie",
                "x-api-key", "x-auth-token", "x-token", "x-session-id"
            ]
            # 只保留安全的头信息
            filtered_headers = {}
            for key, value in request_headers.items():
                if key.lower() not in sensitive_headers:
                    filtered_headers[key] = value
            kwargs["headers"] = filtered_headers
        
        if files:
            # 处理文件上传
            data = {}
            file_data = {}
            
            # 文件验证配置
            # 使用全局配置变量
            
            for key, file in files.items():
                # 验证文件名
                if not file.filename:
                    return await create_error_response(
                        request,
                        status_code=400,
                        message="文件名不能为空",
                        error_code="EMPTY_FILENAME",
                        log_level=logging.ERROR,
                        log_message="文件名不能为空"
                    )
                
                # 验证文件大小（避免整文件读入内存，直接通过 seek/tell 获取大小）
                await file.seek(0, os.SEEK_END)
                file_size = file.file.tell()
                await file.seek(0)

                if file_size == 0:
                    return await create_error_response(
                        request,
                        status_code=400,
                        message="文件不能为空",
                        error_code="EMPTY_FILE",
                        log_level=logging.ERROR,
                        log_message="文件内容为空"
                    )
                if file_size > config.MAX_FILE_SIZE:
                    return await create_error_response(
                        request,
                        status_code=400,
                        message=f"文件大小不能超过 {config.MAX_FILE_SIZE // (1024 * 1024)}MB",
                        error_code="FILE_TOO_LARGE",
                        log_level=logging.ERROR,
                        log_message=f"文件大小超过限制: {file_size} bytes"
                    )

                # 验证文件类型
                if file.content_type not in config.ALLOWED_CONTENT_TYPES:
                    return await create_error_response(
                        request,
                        status_code=400,
                        message=f"不支持的文件类型: {file.content_type}",
                        error_code="INVALID_FILE_TYPE",
                        log_level=logging.ERROR,
                        log_message=f"不支持的文件类型: {file.content_type}"
                    )

                # 确保文件指针在开头，使用底层文件对象进行流式转发
                await file.seek(0)
                file_data[key] = (file.filename, file.file, file.content_type)
            
            if body:
                for key, value in body.items():
                    data[key] = value
            
            kwargs["data"] = data
            kwargs["files"] = file_data
        elif body:
            kwargs["json"] = body
        
        # 发送请求
        try:
            response = await client.request(**kwargs)
        except httpx.ReadTimeout:
            return await create_error_response(
                request,
                status_code=504,
                message="请求超时，请稍后重试",
                error_code="GATEWAY_TIMEOUT",
                log_level=logging.ERROR,
                log_message=f"请求读取超时: {method} {final_url}"
            )
        except httpx.WriteTimeout:
            return await create_error_response(
                request,
                status_code=504,
                message="请求超时，请稍后重试",
                error_code="GATEWAY_TIMEOUT",
                log_level=logging.ERROR,
                log_message=f"请求写入超时: {method} {final_url}"
            )
        except httpx.ConnectTimeout:
            return await create_error_response(
                request,
                status_code=504,
                message="服务连接超时，请稍后重试",
                error_code="GATEWAY_TIMEOUT",
                log_level=logging.ERROR,
                log_message=f"请求连接超时: {method} {final_url}"
            )
        
        # 返回响应
        content = None
        media_type = response.headers.get("content-type", "")
        
        if response.content:
            try:
                if "application/json" in media_type:
                    content = response.json()  # 同步方法，不需要await
                else:
                    content = response.text()  # 同步方法，不需要await
            except ValueError:
                # 如果解析失败，返回原始字节的文本表示
                content = response.text()
        
        return Response(
            content=content if isinstance(content, str) else safe_json_dumps(content),
            status_code=response.status_code,
            headers={k: v for k, v in response.headers.items() if k.lower() not in ["content-length", "transfer-encoding"]}
        )
    except httpx.HTTPStatusError as e:
        return await create_error_response(
            request,
            status_code=e.response.status_code,
            message=e.response.text,
            error_code=f"UPSTREAM_{e.response.status_code}",
            log_level=logging.ERROR,
            log_message=f"代理请求失败: {str(e)}\n  请求: {method} {final_url}\n  响应状态: {e.response.status_code}\n  响应内容: {e.response.text[:200]}..."
        )
    except httpx.RequestError as e:
        return await create_error_response(
            request,
            status_code=503,
            message="服务不可用，请稍后重试",
            error_code="SERVICE_UNAVAILABLE",
            log_level=logging.ERROR,
            log_message=f"请求发送失败: {str(e)}\n  请求: {method} {final_url}"
        )
    except HTTPException as e:
        # 获取请求ID
        request_id = getattr(request.state, "request_id", "unknown") if request else "unknown"
        
        logger.info(
            f"[{request_id}] 业务异常: {e.status_code} - {e.detail}"
        )
        
        # 重新抛出已经处理过的HTTP异常
        raise
    except Exception as e:
        return await create_error_response(
            request,
            status_code=500,
            message="服务请求失败",
            error_code="INTERNAL_SERVER_ERROR",
            log_level=logging.ERROR,
            log_message=f"代理请求异常: {str(e)}\n  请求: {method} {final_url}\n  请求体: {safe_json_dumps(body) if body else '无'}"
        )


def create_app() -> FastAPI:
    """创建FastAPI应用"""
    app = FastAPI(
        title="植物病害检测API网关",
        description="统一入口，路由请求到各个微服务",
        version="1.0.0",
        lifespan=lifespan
    )
    
    # 添加中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    
    # 添加安全中间件，设置安全相关的HTTP头
    @app.middleware("http")
    async def security_headers_middleware(request: Request, call_next):
        """添加安全相关的HTTP头"""
        response = await call_next(request)
        
        # 添加安全相关的HTTP头
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:;"
        
        return response
    
    # 添加请求日志中间件
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        
        # 生成或获取请求ID
        request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
        
        # 将请求ID添加到请求状态
        request.state.request_id = request_id
        
        start_time = get_current_time()
        response = await call_next(request)
        process_time = (get_current_time() - start_time).total_seconds()
        
        logger.info(
            f"[{request_id}] {request.method} {request.url.path} - "
            f"Status: {response.status_code} - "
            f"Time: {process_time:.4f}s"
        )
        
        # 将请求ID添加到响应头
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = str(process_time)
        return response
    
    # 添加异常处理器
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request, exc):
        # 获取请求ID
        request_id = getattr(request.state, "request_id", "unknown")
        
        logger.info(
            f"[{request_id}] HTTP异常: {exc.status_code} - {exc.detail}"
        )
        
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                message=exc.detail,
                error_code=f"HTTP_{exc.status_code}"
            ).dict(),
            headers={"X-Request-ID": request_id}
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request, exc):
        # 获取请求ID
        request_id = getattr(request.state, "request_id", "unknown")
        
        logger.error(
            f"[{request_id}] 未处理的异常: {str(exc)}",
            exc_info=True
        )
        
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                message="服务器内部错误",
                error_code="INTERNAL_SERVER_ERROR"
            ).dict(),
            headers={"X-Request-ID": request_id}
        )
    
    # 添加路由
    app.include_router(health_router, prefix="/health", tags=["健康检查"])
    app.include_router(auth_router, prefix="/auth", tags=["认证"])
    app.include_router(user_router, prefix="/users", tags=["用户管理"])
    app.include_router(task_router, prefix="/tasks", tags=["任务管理"])
    app.include_router(model_router, prefix="/models", tags=["模型管理"])
    app.include_router(prediction_router, prefix="/predictions", tags=["预测服务"])
    # app.include_router(segmentation_router, prefix="/segmentations", tags=["分割服务"])  # 分割服务未实现
    # app.include_router(notification_router, prefix="/notifications", tags=["通知服务"])  # 通知服务未实现
    
    return app



@health_router.get("/", response_model=HealthCheck)
@log_execution_time
async def health_check():
    """健康检查"""
    services = {
        "user-service": config.USER_SERVICE_URL,
        "task-service": config.TASK_SERVICE_URL,
        "model-service": config.MODEL_SERVICE_URL,
        "cache-service": config.CACHE_SERVICE_URL
    }
    
    dependencies = {}
    
    # 检查Redis连接
    try:
        if app_state["redis_client"]:
            app_state["redis_client"].ping()
            dependencies["redis"] = "healthy"
        else:
            dependencies["redis"] = "unhealthy"
    except Exception as e:
        logger.error(f"检查Redis健康状态失败: {str(e)}")
        dependencies["redis"] = "unreachable"
    
    # 检查HTTP客户端
    try:
        if app_state["http_client"]:
            dependencies["http_client"] = "healthy"
        else:
            dependencies["http_client"] = "unhealthy"
    except Exception as e:
        logger.error(f"检查HTTP客户端健康状态失败: {str(e)}")
        dependencies["http_client"] = "unreachable"
    
    # 并发检查下游服务
    async def check_service(service_name, service_url):
        """检查单个服务的健康状态"""
        try:
            client = await get_http_client()
            response = await client.get(f"{service_url}/health/", timeout=5.0)
            return service_name, "healthy" if response.status_code == 200 else "unhealthy"
        except Exception as e:
            logger.error(f"检查 {service_name} 健康状态失败: {str(e)}")
            return service_name, "unreachable"
    
    # 使用asyncio.gather并发检查所有服务
    service_checks = [check_service(name, url) for name, url in services.items()]
    results = await asyncio.gather(*service_checks)
    
    # 更新依赖状态
    for service_name, status in results:
        dependencies[service_name] = status
    
    # 确定整体状态
    overall_status = "healthy"
    for status in dependencies.values():
        if status != "healthy":
            overall_status = "unhealthy"
            break
    
    return HealthCheck(
        status=overall_status,
        timestamp=get_current_time(),
        service=config.APP_NAME,
        version=config.APP_VERSION,
        dependencies=dependencies
    )


# 用户服务相关路由（最小闭环：登录/注册/刷新/当前用户）
@auth_router.post("/login")
@log_execution_time
async def login(request: Request):
    """用户登录"""
    body = await request.json()
    client = await get_http_client()

    headers: Dict[str, str] = {}
    request_id = getattr(request.state, "request_id", None)
    if request_id:
        headers["X-Request-ID"] = request_id

    resp = await client.post(f"{config.USER_SERVICE_URL}/auth/login", json=body, headers=headers)
    try:
        data = resp.json()
    except Exception:
        data = {"message": resp.text}
    return JSONResponse(status_code=resp.status_code, content=data)


@auth_router.post("/register")
@log_execution_time
async def register(request: Request):
    """用户注册"""
    body = await request.json()
    client = await get_http_client()

    headers: Dict[str, str] = {}
    request_id = getattr(request.state, "request_id", None)
    if request_id:
        headers["X-Request-ID"] = request_id

    resp = await client.post(f"{config.USER_SERVICE_URL}/auth/register", json=body, headers=headers)
    try:
        data = resp.json()
    except Exception:
        data = {"message": resp.text}
    return JSONResponse(status_code=resp.status_code, content=data)


@auth_router.post("/refresh")
@log_execution_time
async def refresh_token(request: Request):
    """刷新令牌"""
    client = await get_http_client()

    headers: Dict[str, str] = {}
    request_id = getattr(request.state, "request_id", None)
    if request_id:
        headers["X-Request-ID"] = request_id

    auth_header = request.headers.get("authorization")
    if auth_header:
        headers["Authorization"] = auth_header

    resp = await client.post(f"{config.USER_SERVICE_URL}/auth/refresh", headers=headers)
    try:
        data = resp.json()
    except Exception:
        data = {"message": resp.text}
    return JSONResponse(status_code=resp.status_code, content=data)


@user_router.get("/me")
@log_execution_time
async def get_me(request: Request):
    """获取当前用户信息"""
    client = await get_http_client()

    headers: Dict[str, str] = {}
    request_id = getattr(request.state, "request_id", None)
    if request_id:
        headers["X-Request-ID"] = request_id

    auth_header = request.headers.get("authorization")
    if auth_header:
        headers["Authorization"] = auth_header

    resp = await client.get(f"{config.USER_SERVICE_URL}/users/me", headers=headers)
    try:
        data = resp.json()
    except Exception:
        data = {"message": resp.text}
    return JSONResponse(status_code=resp.status_code, content=data)


# @user_router.get("/")
# @log_execution_time
# async def get_users(
#     request: Request,
#     current_user: Dict[str, Any] = Depends(verify_token)
# ):
#     """获取用户列表"""
#     if not current_user:
#         raise HTTPException(status_code=401, detail="需要认证")
#     
#     return await proxy_request(
#         method="GET",
#         url=f"{USER_SERVICE_URL}/users/",
#         query_params=dict(request.query_params),
#         headers=dict(request.headers)
#     )


# @user_router.get("/{user_id}")
# @log_execution_time
# async def get_user(
#     user_id: int,
#     request: Request,
#     current_user: Dict[str, Any] = Depends(verify_token)
# ):
#     """获取用户详情"""
#     if not current_user:
#         raise HTTPException(status_code=401, detail="需要认证")
#     
#     return await proxy_request(
#         method="GET",
#         url=f"{USER_SERVICE_URL}/users/{user_id}",
#         headers=dict(request.headers)
#     )


# @user_router.put("/{user_id}")
# @log_execution_time
# async def update_user(
#     user_id: int,
#     request: Request,
#     current_user: Dict[str, Any] = Depends(verify_token)
# ):
#     """更新用户信息"""
#     if not current_user:
#         raise HTTPException(status_code=401, detail="需要认证")
#     
#     return await proxy_request(
#         method="PUT",
#         url=f"{USER_SERVICE_URL}/users/{user_id}",
#         body=await request.json(),
#         headers=dict(request.headers)
#     )


@task_router.post("/")
@log_execution_time
async def create_task(
    request: Request,
    current_user: Dict[str, Any] = Depends(verify_token)
):
    """创建任务"""
    if not current_user:
        raise HTTPException(status_code=401, detail="需要认证")
    
    # 添加用户ID到请求体 + 兼容前端字段
    body = await request.json()

    # api-gateway 从 JWT(sub) 解析的 user_id
    body["user_id"] = current_user.get("user_id")

    # 前端可能使用 type/data 字段，这里转换为后端期望的 task_type/input_data
    if "task_type" not in body and "type" in body:
        body["task_type"] = body.get("type")
    if "input_data" not in body and "data" in body:
        body["input_data"] = body.get("data")
    if "priority" not in body:
        body["priority"] = "medium"

    
    return await proxy_request(
        method="POST",
        url=f"{config.TASK_SERVICE_URL}/tasks/",
        request=request,
        body=body,
        headers=dict(request.headers)
    )


@task_router.get("/")
@log_execution_time
async def get_tasks(
    request: Request,
    current_user: Dict[str, Any] = Depends(verify_token)
):
    """获取任务列表"""
    if not current_user:
        raise HTTPException(status_code=401, detail="需要认证")
    
    # 添加用户ID到查询参数
    query_params = dict(request.query_params)
    query_params["user_id"] = current_user.get("user_id")
    
    return await proxy_request(
        method="GET",
        url=f"{config.TASK_SERVICE_URL}/tasks/",
        request=request,
        query_params=query_params,
        headers=dict(request.headers)
    )


@task_router.get("/{task_id}")
@log_execution_time
async def get_task(
    task_id: str,
    request: Request,
    current_user: Dict[str, Any] = Depends(verify_token)
):
    """获取任务详情"""
    if not current_user:
        raise HTTPException(status_code=401, detail="需要认证")
    
    return await proxy_request(
        method="GET",
        url=f"{config.TASK_SERVICE_URL}/tasks/{task_id}",
        request=request,
        headers=dict(request.headers)
    )


@task_router.put("/{task_id}")
@log_execution_time
async def update_task(
    task_id: str,
    request: Request,
    current_user: Dict[str, Any] = Depends(verify_token)
):
    """更新任务"""
    if not current_user:
        raise HTTPException(status_code=401, detail="需要认证")
    
    return await proxy_request(
        method="PUT",
        url=f"{config.TASK_SERVICE_URL}/tasks/{task_id}",
        request=request,
        body=await request.json(),
        headers=dict(request.headers)
    )


@task_router.delete("/{task_id}")
@log_execution_time
async def delete_task(
    task_id: str,
    request: Request,
    current_user: Dict[str, Any] = Depends(verify_token)
):
    """删除任务"""
    if not current_user:
        raise HTTPException(status_code=401, detail="需要认证")
    
    return await proxy_request(
        method="DELETE",
        url=f"{config.TASK_SERVICE_URL}/tasks/{task_id}",
        request=request,
        headers=dict(request.headers)
    )


@model_router.get("/")
@log_execution_time
async def get_models(
    request: Request,
    current_user: Optional[Dict[str, Any]] = Depends(verify_token)
):
    """获取模型列表"""
    return await proxy_request(
        method="GET",
        url=f"{config.MODEL_SERVICE_URL}/models/",
        request=request,
        query_params=dict(request.query_params),
        headers=dict(request.headers)
    )


@model_router.get("/{model_id}")
@log_execution_time
async def get_model(
    model_id: str,
    request: Request,
    current_user: Optional[Dict[str, Any]] = Depends(verify_token)
):
    """获取模型详情"""
    return await proxy_request(
        method="GET",
        url=f"{config.MODEL_SERVICE_URL}/models/{model_id}",
        request=request,
        headers=dict(request.headers)
    )


@prediction_router.post("/")
@log_execution_time
async def create_prediction(
    request: Request,
    current_user: Dict[str, Any] = Depends(verify_token)
):
    """创建预测任务"""
    if not current_user:
        raise HTTPException(status_code=401, detail="需要认证")
    
    # 添加用户ID到请求体 + 兼容前端字段
    body = await request.json()

    # api-gateway 从 JWT(sub) 解析的 user_id
    body["user_id"] = current_user.get("user_id")

    # 前端可能使用 type/data 字段，这里转换为后端期望的 task_type/input_data
    if "task_type" not in body and "type" in body:
        body["task_type"] = body.get("type")
    if "input_data" not in body and "data" in body:
        body["input_data"] = body.get("data")
    if "priority" not in body:
        body["priority"] = "medium"

    
    return await proxy_request(
        method="POST",
        url=f"{config.TASK_SERVICE_URL}/tasks/",
        request=request,
        body={
            "title": f"预测任务 - {get_current_time().strftime('%Y%m%d%H%M%S')}",
            "description": "植物病害检测预测任务",
            "task_type": "prediction",
            "priority": "medium",
            "input_data": body
        },
        headers=dict(request.headers)
    )


@prediction_router.post("/direct")
@log_execution_time
async def direct_prediction(
    request: Request,
    file: UploadFile = File(...),
    model_name: str = Form("default"),
    confidence_threshold: float = Form(0.5),
    current_user: Optional[Dict[str, Any]] = Depends(verify_token)
):
    """直接预测（同步，multipart/form-data）"""
    headers: Dict[str, str] = {}
    request_id = getattr(request.state, "request_id", None)
    if request_id:
        headers["X-Request-ID"] = request_id

    return await proxy_request(
        method="POST",
        url=f"{config.MODEL_SERVICE_URL}/predict/direct",
        request=request,
        files={"file": file},
        body={
            "model_name": model_name,
            "confidence_threshold": confidence_threshold,
        },
        headers=headers
    )


@prediction_router.post("/smart")
@log_execution_time
async def smart_prediction(
    request: Request,
    file: UploadFile = File(...),
    device_info: str = Form(""),
    use_segmentation: bool = Form(True),
    current_user: Optional[Dict[str, Any]] = Depends(verify_token)
):
    """智能预测（使用智能路由）"""
    headers: Dict[str, str] = {}
    request_id = getattr(request.state, "request_id", None)
    if request_id:
        headers["X-Request-ID"] = request_id

    return await proxy_request(
        method="POST",
        url=f"{config.MODEL_SERVICE_URL}/predict/smart",
        request=request,
        files={"file": file},
        body={"device_info": device_info, "use_segmentation": str(use_segmentation).lower()},
        headers=headers
    )


@prediction_router.post("/student")
@log_execution_time
async def student_prediction(
    request: Request,
    file: UploadFile = File(...),
    use_segmentation: bool = Form(True),
    confidence_threshold: float = Form(0.5),
    current_user: Optional[Dict[str, Any]] = Depends(verify_token)
):
    """学生模型预测"""
    headers: Dict[str, str] = {}
    request_id = getattr(request.state, "request_id", None)
    if request_id:
        headers["X-Request-ID"] = request_id

    return await proxy_request(
        method="POST",
        url=f"{config.MODEL_SERVICE_URL}/predict/student",
        request=request,
        files={"file": file},
        body={"use_segmentation": str(use_segmentation).lower(), "confidence_threshold": confidence_threshold},
        headers=headers
    )


@prediction_router.post("/ensemble")
@log_execution_time
async def ensemble_prediction(
    request: Request,
    file: UploadFile = File(...),
    use_segmentation: bool = Form(True),
    confidence_threshold: float = Form(0.5),
    current_user: Optional[Dict[str, Any]] = Depends(verify_token)
):
    """集成模型预测"""
    headers: Dict[str, str] = {}
    request_id = getattr(request.state, "request_id", None)
    if request_id:
        headers["X-Request-ID"] = request_id

    return await proxy_request(
        method="POST",
        url=f"{config.MODEL_SERVICE_URL}/predict/ensemble",
        request=request,
        files={"file": file},
        body={"use_segmentation": str(use_segmentation).lower(), "confidence_threshold": confidence_threshold},
        headers=headers
    )


@prediction_router.get("/router_stats")
@log_execution_time
async def get_router_stats(
    current_user: Optional[Dict[str, Any]] = Depends(verify_token)
):
    """获取智能路由统计信息"""
    return await proxy_request(
        method="GET",
        url=f"{config.MODEL_SERVICE_URL}/predict/router_stats",
        headers={}
    )


# 分割服务相关路由已注释，因为分割服务未实现
# @segmentation_router.post("/")
# @log_execution_time
# async def create_segmentation(
#     request: Request,
#     current_user: Dict[str, Any] = Depends(verify_token)
# ):
#     """创建分割任务"""
#     if not current_user:
#         raise HTTPException(status_code=401, detail="需要认证")
#     
#     # 添加用户ID到请求体
#     body = await request.json()
#     body["user_id"] = current_user.get("user_id")
#     
#     return await proxy_request(
#         method="POST",
#         url=f"{TASK_SERVICE_URL}/tasks/",
#         body={
#             "title": f"分割任务 - {get_current_time().strftime('%Y%m%d%H%M%S')}",
#             "description": "植物图像分割任务",
#             "task_type": "segmentation",
#             "priority": "medium",
#             "input_data": body
#         },
#         headers=dict(request.headers)
#     )


# @segmentation_router.post("/direct")
# @log_execution_time
# async def direct_segmentation(
#     request: Request,
#     current_user: Optional[Dict[str, Any]] = Depends(verify_token)
# ):
#     """直接分割请求"""
#     return await proxy_request(
#         method="POST",
#         url=f"{SEGMENTATION_SERVICE_URL}/segment",
#         body=await request.json(),
#         headers=dict(request.headers)
#     )


# 通知服务相关路由已注释，因为通知服务未实现
# @notification_router.get("/")
# @log_execution_time
# async def get_notifications(
#     request: Request,
#     current_user: Dict[str, Any] = Depends(verify_token)
# ):
#     """获取通知列表"""
#     if not current_user:
#         raise HTTPException(status_code=401, detail="需要认证")
#     
#     # 添加用户ID到查询参数
#     query_params = dict(request.query_params)
#     query_params["user_id"] = current_user.get("user_id")
#     
#     return await proxy_request(
#         method="GET",
#         url=f"{NOTIFICATION_SERVICE_URL}/notifications/",
#         query_params=query_params,
#         headers=dict(request.headers)
#     )


# @notification_router.put("/{notification_id}/read")
# @log_execution_time
# async def mark_notification_read(
#     notification_id: int,
#     request: Request,
#     current_user: Dict[str, Any] = Depends(verify_token)
# ):
#     """标记通知为已读"""
#     if not current_user:
#         raise HTTPException(status_code=401, detail="需要认证")
#     
#     return await proxy_request(
#         method="PUT",
#         url=f"{NOTIFICATION_SERVICE_URL}/notifications/{notification_id}/read",
#         headers=dict(request.headers)
#     )


# 创建应用实例（必须在所有路由定义之后）
app = create_app()

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
