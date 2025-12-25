"""
用户服务主应用（最小闭环：用户入库）

目标：
- 用户信息必须入库（PostgreSQL）
- 支持：注册 / 登录 / 刷新令牌 / 获取与更新当前用户信息

约束：
- 仅 user-service 直接连接数据库
- JWT payload 与 api-gateway 对齐：sub=user_id, username/email/role
"""

import os
import sys
import logging
import asyncio
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional

from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
import uvicorn

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# 添加共享模块路径
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "shared"))

from shared.database.models import Base, User as UserModel
from shared.schemas.schemas import UserCreate, UserUpdate, HealthCheck, ErrorResponse
from shared.utils.helpers import log_execution_time, get_current_time

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# JWT 配置
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-here")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

# 默认管理员（最小闭环：确保系统可登录）
DEFAULT_ADMIN_USERNAME = os.getenv("DEFAULT_ADMIN_USERNAME", "admin")
DEFAULT_ADMIN_EMAIL = os.getenv("DEFAULT_ADMIN_EMAIL", "admin@example.com")
DEFAULT_ADMIN_PASSWORD = os.getenv("DEFAULT_ADMIN_PASSWORD", "admin123")

# 密码上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2（仅用于提取 Authorization: Bearer token）
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


class LoginRequest(BaseModel):
    username: str
    password: str


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(payload: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    to_encode = payload.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def user_to_dict(user: UserModel) -> Dict[str, Any]:
    role = "admin" if user.is_superuser else "user"
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "is_active": user.is_active,
        "is_superuser": user.is_superuser,
        "role": role,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "updated_at": user.updated_at.isoformat() if user.updated_at else None,
    }


# 数据库（仅 user-service 使用）
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@postgres:5432/plant_disease")
if DATABASE_URL.startswith("postgresql+asyncpg://"):
    ASYNC_DATABASE_URL = DATABASE_URL
else:
    ASYNC_DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

engine = create_async_engine(ASYNC_DATABASE_URL, pool_pre_ping=True)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session


async def init_db_schema_and_seed() -> None:
    # Postgres 可能需要等待（compose 启动时序）
    last_error: Optional[Exception] = None
    for attempt in range(30):
        try:
            async with engine.begin() as conn:
                # 只创建 users 表（严格满足：仅用户信息入库）
                await conn.run_sync(Base.metadata.create_all, tables=[UserModel.__table__])
            last_error = None
            break
        except Exception as e:
            last_error = e
            logger.warning(f"数据库未就绪，重试中 ({attempt + 1}/30): {e}")
            await asyncio.sleep(1)

    if last_error is not None:
        raise last_error

    # 初始化默认管理员（若不存在）
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(UserModel).where(UserModel.username == DEFAULT_ADMIN_USERNAME))
        admin = res.scalar_one_or_none()
        if admin is None:
            admin = UserModel(
                username=DEFAULT_ADMIN_USERNAME,
                email=DEFAULT_ADMIN_EMAIL,
                full_name="Admin User",
                hashed_password=get_password_hash(DEFAULT_ADMIN_PASSWORD),
                is_active=True,
                is_superuser=True,
            )
            db.add(admin)
            await db.commit()
            logger.info(f"已创建默认管理员用户: {DEFAULT_ADMIN_USERNAME}")


async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)) -> UserModel:
    credentials_exception = HTTPException(
        status_code=401,
        detail="无法验证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        sub = payload.get("sub")
        if sub is None:
            raise credentials_exception
        user_id = int(sub)
    except (JWTError, ValueError, TypeError):
        raise credentials_exception

    res = await db.execute(select(UserModel).where(UserModel.id == user_id))
    user = res.scalar_one_or_none()
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(current_user: UserModel = Depends(get_current_user)) -> UserModel:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="用户已禁用")
    return current_user


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("用户服务启动中...")
    await init_db_schema_and_seed()
    logger.info("用户服务启动完成")
    yield
    logger.info("用户服务已关闭")


def create_app() -> FastAPI:
    app = FastAPI(
        title="植物病害检测用户服务",
        description="提供用户注册、登录、认证管理服务",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start_time = get_current_time()
        response = await call_next(request)
        process_time = (get_current_time() - start_time).total_seconds()
        logger.info(
            f"{request.method} {request.url.path} - "
            f"Status: {response.status_code} - "
            f"Time: {process_time:.4f}s"
        )
        response.headers["X-Process-Time"] = str(process_time)
        return response

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request, exc):
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(message=exc.detail, error_code=f"HTTP_{exc.status_code}").dict(),
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request, exc):
        logger.error(f"未处理的异常: {str(exc)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(message="服务器内部错误", error_code="INTERNAL_SERVER_ERROR").dict(),
        )

    return app


# 路由定义
from fastapi import APIRouter

health_router = APIRouter()
auth_router = APIRouter()
user_router = APIRouter()


@health_router.get("/", response_model=HealthCheck)
@log_execution_time
async def health_check(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(func.count()).select_from(UserModel))
    user_count = int(res.scalar() or 0)
    return HealthCheck(
        status="healthy",
        timestamp=get_current_time(),
        service="user-service",
        version="1.0.0",
        dependencies={"postgres": "connected", "users": f"{user_count} users"},
    )


@auth_router.post("/login", response_model=Dict[str, Any])
@log_execution_time
async def login_for_access_token(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(UserModel).where(UserModel.username == payload.username))
    user = res.scalar_one_or_none()

    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=401,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(status_code=400, detail="用户已禁用")

    token_payload = {
        "sub": str(user.id),
        "username": user.username,
        "email": user.email,
        "role": "admin" if user.is_superuser else "user",
    }
    access_token = create_access_token(token_payload, timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))

    return {"access_token": access_token, "token_type": "bearer", "user": user_to_dict(user)}


@auth_router.post("/register", response_model=Dict[str, Any])
@log_execution_time
async def register(user_create: UserCreate, db: AsyncSession = Depends(get_db)):
    res = await db.execute(
        select(UserModel).where((UserModel.username == user_create.username) | (UserModel.email == user_create.email))
    )
    exists = res.scalar_one_or_none()
    if exists is not None:
        if exists.username == user_create.username:
            raise HTTPException(status_code=400, detail="用户名已存在")
        raise HTTPException(status_code=400, detail="邮箱已被注册")

    new_user = UserModel(
        username=user_create.username,
        email=user_create.email,
        full_name=user_create.full_name,
        hashed_password=get_password_hash(user_create.password),
        is_active=True,
        is_superuser=False,
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    token_payload = {
        "sub": str(new_user.id),
        "username": new_user.username,
        "email": new_user.email,
        "role": "user",
    }
    access_token = create_access_token(token_payload, timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))

    return {"access_token": access_token, "token_type": "bearer", "user": user_to_dict(new_user)}


@auth_router.post("/refresh", response_model=Dict[str, Any])
@log_execution_time
async def refresh_token(current_user: UserModel = Depends(get_current_active_user)):
    token_payload = {
        "sub": str(current_user.id),
        "username": current_user.username,
        "email": current_user.email,
        "role": "admin" if current_user.is_superuser else "user",
    }
    access_token = create_access_token(token_payload, timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    return {"access_token": access_token, "token_type": "bearer"}


@user_router.get("/me", response_model=Dict[str, Any])
@log_execution_time
async def get_current_user_info(current_user: UserModel = Depends(get_current_active_user)):
    return user_to_dict(current_user)


@user_router.put("/me", response_model=Dict[str, Any])
@log_execution_time
async def update_current_user(
    user_update: UserUpdate,
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    update_data = user_update.dict(exclude_unset=True)

    # 处理 username/email 冲突（排除自己）
    if "username" in update_data or "email" in update_data:
        q = select(UserModel).where(UserModel.id != current_user.id)
        if "username" in update_data and "email" in update_data:
            q = q.where((UserModel.username == update_data["username"]) | (UserModel.email == update_data["email"]))
        elif "username" in update_data:
            q = q.where(UserModel.username == update_data["username"])
        else:
            q = q.where(UserModel.email == update_data["email"])

        res = await db.execute(q)
        conflict = res.scalar_one_or_none()
        if conflict is not None:
            if "username" in update_data and conflict.username == update_data["username"]:
                raise HTTPException(status_code=400, detail="用户名已存在")
            if "email" in update_data and conflict.email == update_data["email"]:
                raise HTTPException(status_code=400, detail="邮箱已被注册")

    res = await db.execute(select(UserModel).where(UserModel.id == current_user.id))
    user = res.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")

    for k, v in update_data.items():
        setattr(user, k, v)

    await db.commit()
    await db.refresh(user)
    return user_to_dict(user)


# 创建应用实例（必须在所有路由定义之后）
app = create_app()

# 包含路由
app.include_router(health_router, prefix="/health", tags=["健康检查"])
app.include_router(auth_router, prefix="/auth", tags=["认证"])
app.include_router(user_router, prefix="/users", tags=["用户"])


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True, log_level="info")
