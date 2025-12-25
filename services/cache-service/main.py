"""
Redis缓存服务的主应用
"""
import os
import sys
import logging
from dotenv import load_dotenv
from contextlib import asynccontextmanager
from typing import Dict, Any, List, Optional

# 加载环境变量
load_dotenv()

from fastapi import FastAPI, HTTPException, Depends, Query, Path
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
import uvicorn

# 添加共享模块路径
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "shared"))

from shared.cache.redis_cache import (
    cache_service, UserSessionCache, TaskResultCache, 
    ModelInfoCache, APIResponseCache, DistributedLock, RateLimiter
)
from shared.schemas.schemas import HealthCheck, SuccessResponse, ErrorResponse
from shared.utils.helpers import log_execution_time, get_current_time

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# 全局变量
app_state: Dict[str, Any] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    logger.info("Redis缓存服务启动中...")
    
    # 初始化Redis连接
    await cache_service.get_async_client()
    
    logger.info("Redis缓存服务启动完成")
    
    yield
    
    # 关闭时执行
    logger.info("Redis缓存服务关闭中...")
    
    # 清理资源
    await cache_service.close()
    
    logger.info("Redis缓存服务已关闭")


def create_app() -> FastAPI:
    """创建FastAPI应用"""
    app = FastAPI(
        title="植物病害检测Redis缓存服务",
        description="提供Redis缓存管理和监控服务",
        version="1.0.0",
        lifespan=lifespan
    )
    
    # 添加中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    
    # 添加异常处理器
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request, exc):
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                message=exc.detail,
                error_code=f"HTTP_{exc.status_code}"
            ).dict()
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request, exc):
        logger.error(f"未处理的异常: {str(exc)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                message="服务器内部错误",
                error_code="INTERNAL_SERVER_ERROR"
            ).dict()
        )
    
    # 添加路由
    app.include_router(health_router, prefix="/health", tags=["健康检查"])
    app.include_router(cache_router, prefix="/cache", tags=["缓存管理"])
    app.include_router(session_router, prefix="/session", tags=["会话管理"])
    app.include_router(task_router, prefix="/task", tags=["任务缓存"])
    app.include_router(model_router, prefix="/model", tags=["模型缓存"])
    app.include_router(api_router, prefix="/api", tags=["API缓存"])
    app.include_router(lock_router, prefix="/lock", tags=["分布式锁"])
    app.include_router(rate_limit_router, prefix="/rate_limit", tags=["限流"])
    
    return app


# 路由定义
from fastapi import APIRouter, Body
from pydantic import BaseModel

health_router = APIRouter()
cache_router = APIRouter()
session_router = APIRouter()
task_router = APIRouter()
model_router = APIRouter()
api_router = APIRouter()
lock_router = APIRouter()
rate_limit_router = APIRouter()


# 请求模型
class CacheSetRequest(BaseModel):
    key: str
    value: Any
    ttl: Optional[int] = None

class UserSessionRequest(BaseModel):
    user_id: int
    session_data: Dict[str, Any]

class TaskResultRequest(BaseModel):
    task_id: str
    result_data: Dict[str, Any]

class ModelInfoRequest(BaseModel):
    model_id: str
    model_data: Dict[str, Any]

class APIResponseRequest(BaseModel):
    endpoint: str
    params: Dict[str, Any]
    response_data: Dict[str, Any]

class LockRequest(BaseModel):
    key: str
    timeout: Optional[int] = 10

class RateLimitRequest(BaseModel):
    key: str
    limit: int
    window: int


@health_router.get("/", response_model=HealthCheck)
@log_execution_time
async def health_check():
    """健康检查"""
    try:
        # 检查Redis连接
        client = await cache_service.get_async_client()
        await client.ping()
        
        # 获取Redis信息
        info = await client.info()
        
        return HealthCheck(
            status="healthy",
            timestamp=get_current_time(),
            service="redis-cache",
            version="1.0.0",
            dependencies={
                "redis": "connected",
                "redis_version": info.get("redis_version", "unknown"),
                "used_memory": info.get("used_memory_human", "unknown"),
                "connected_clients": info.get("connected_clients", 0)
            }
        )
    except Exception as e:
        logger.error(f"健康检查失败: {str(e)}")
        return HealthCheck(
            status="unhealthy",
            timestamp=get_current_time(),
            service="redis-cache",
            version="1.0.0",
            dependencies={"redis": "disconnected"}
        )


@cache_router.post("/set")
@log_execution_time
async def set_cache(request: CacheSetRequest):
    """设置缓存"""
    try:
        ttl = request.ttl if request.ttl is not None else 3600  # 默认1小时
        result = await cache_service.set(request.key, request.value, ttl)
        
        if result:
            return SuccessResponse(
                message=f"缓存 {request.key} 设置成功",
                data={"key": request.key, "ttl": ttl}
            )
        else:
            raise HTTPException(status_code=500, detail="设置缓存失败")
    except Exception as e:
        logger.error(f"设置缓存失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"设置缓存失败: {str(e)}")


@cache_router.get("/get/{key}")
@log_execution_time
async def get_cache(key: str):
    """获取缓存"""
    try:
        value = await cache_service.get(key)
        
        if value is not None:
            return SuccessResponse(
                message=f"缓存 {key} 获取成功",
                data={"key": key, "value": value}
            )
        else:
            return SuccessResponse(
                message=f"缓存 {key} 不存在",
                data={"key": key, "value": None}
            )
    except Exception as e:
        logger.error(f"获取缓存失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取缓存失败: {str(e)}")


@cache_router.delete("/delete/{key}")
@log_execution_time
async def delete_cache(key: str):
    """删除缓存"""
    try:
        result = await cache_service.delete(key)
        
        if result:
            return SuccessResponse(
                message=f"缓存 {key} 删除成功",
                data={"key": key}
            )
        else:
            return SuccessResponse(
                message=f"缓存 {key} 不存在",
                data={"key": key}
            )
    except Exception as e:
        logger.error(f"删除缓存失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"删除缓存失败: {str(e)}")


@cache_router.get("/exists/{key}")
@log_execution_time
async def check_cache_exists(key: str):
    """检查缓存是否存在"""
    try:
        exists = await cache_service.exists(key)
        
        return SuccessResponse(
            message=f"缓存 {key} 存在性检查完成",
            data={"key": key, "exists": exists}
        )
    except Exception as e:
        logger.error(f"检查缓存存在性失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"检查缓存存在性失败: {str(e)}")


@cache_router.post("/expire/{key}")
@log_execution_time
async def set_cache_expire(key: str, ttl: int = Query(..., description="过期时间(秒)")):
    """设置缓存过期时间"""
    try:
        result = await cache_service.expire(key, ttl)
        
        if result:
            return SuccessResponse(
                message=f"缓存 {key} 过期时间设置成功",
                data={"key": key, "ttl": ttl}
            )
        else:
            raise HTTPException(status_code=404, detail=f"缓存 {key} 不存在")
    except Exception as e:
        logger.error(f"设置缓存过期时间失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"设置缓存过期时间失败: {str(e)}")


@cache_router.get("/ttl/{key}")
@log_execution_time
async def get_cache_ttl(key: str):
    """获取缓存剩余时间"""
    try:
        ttl = await cache_service.ttl(key)
        
        return SuccessResponse(
            message=f"缓存 {key} 剩余时间获取成功",
            data={"key": key, "ttl": ttl}
        )
    except Exception as e:
        logger.error(f"获取缓存剩余时间失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取缓存剩余时间失败: {str(e)}")


@cache_router.get("/keys")
@log_execution_time
async def get_cache_keys(pattern: str = Query("*", description="键模式")):
    """获取匹配模式的所有键"""
    try:
        keys = await cache_service.keys(pattern)
        
        return SuccessResponse(
            message=f"键列表获取成功",
            data={"pattern": pattern, "keys": keys, "count": len(keys)}
        )
    except Exception as e:
        logger.error(f"获取键列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取键列表失败: {str(e)}")


@cache_router.post("/flush")
@log_execution_time
async def flush_cache():
    """清空当前数据库"""
    try:
        result = await cache_service.flushdb()
        
        if result:
            return SuccessResponse(
                message="数据库清空成功",
                data={}
            )
        else:
            raise HTTPException(status_code=500, detail="清空数据库失败")
    except Exception as e:
        logger.error(f"清空数据库失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"清空数据库失败: {str(e)}")


@session_router.post("/set")
@log_execution_time
async def set_user_session(request: UserSessionRequest):
    """设置用户会话"""
    try:
        result = await UserSessionCache.set_session(request.user_id, request.session_data)
        
        if result:
            return SuccessResponse(
                message=f"用户 {request.user_id} 会话设置成功",
                data={"user_id": request.user_id}
            )
        else:
            raise HTTPException(status_code=500, detail="设置用户会话失败")
    except Exception as e:
        logger.error(f"设置用户会话失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"设置用户会话失败: {str(e)}")


@session_router.get("/get/{user_id}")
@log_execution_time
async def get_user_session(user_id: int):
    """获取用户会话"""
    try:
        session_data = await UserSessionCache.get_session(user_id)
        
        if session_data is not None:
            return SuccessResponse(
                message=f"用户 {user_id} 会话获取成功",
                data={"user_id": user_id, "session_data": session_data}
            )
        else:
            return SuccessResponse(
                message=f"用户 {user_id} 会话不存在",
                data={"user_id": user_id, "session_data": None}
            )
    except Exception as e:
        logger.error(f"获取用户会话失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取用户会话失败: {str(e)}")


@session_router.delete("/delete/{user_id}")
@log_execution_time
async def delete_user_session(user_id: int):
    """删除用户会话"""
    try:
        result = await UserSessionCache.delete_session(user_id)
        
        if result:
            return SuccessResponse(
                message=f"用户 {user_id} 会话删除成功",
                data={"user_id": user_id}
            )
        else:
            return SuccessResponse(
                message=f"用户 {user_id} 会话不存在",
                data={"user_id": user_id}
            )
    except Exception as e:
        logger.error(f"删除用户会话失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"删除用户会话失败: {str(e)}")


@session_router.post("/refresh/{user_id}")
@log_execution_time
async def refresh_user_session(user_id: int):
    """刷新用户会话"""
    try:
        result = await UserSessionCache.refresh_session(user_id)
        
        if result:
            return SuccessResponse(
                message=f"用户 {user_id} 会话刷新成功",
                data={"user_id": user_id}
            )
        else:
            raise HTTPException(status_code=404, detail=f"用户 {user_id} 会话不存在")
    except Exception as e:
        logger.error(f"刷新用户会话失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"刷新用户会话失败: {str(e)}")


@task_router.post("/set")
@log_execution_time
async def set_task_result(request: TaskResultRequest):
    """设置任务结果"""
    try:
        result = await TaskResultCache.set_result(request.task_id, request.result_data)
        
        if result:
            return SuccessResponse(
                message=f"任务 {request.task_id} 结果设置成功",
                data={"task_id": request.task_id}
            )
        else:
            raise HTTPException(status_code=500, detail="设置任务结果失败")
    except Exception as e:
        logger.error(f"设置任务结果失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"设置任务结果失败: {str(e)}")


@task_router.get("/get/{task_id}")
@log_execution_time
async def get_task_result(task_id: str):
    """获取任务结果"""
    try:
        result_data = await TaskResultCache.get_result(task_id)
        
        if result_data is not None:
            return SuccessResponse(
                message=f"任务 {task_id} 结果获取成功",
                data={"task_id": task_id, "result_data": result_data}
            )
        else:
            return SuccessResponse(
                message=f"任务 {task_id} 结果不存在",
                data={"task_id": task_id, "result_data": None}
            )
    except Exception as e:
        logger.error(f"获取任务结果失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取任务结果失败: {str(e)}")


@task_router.delete("/delete/{task_id}")
@log_execution_time
async def delete_task_result(task_id: str):
    """删除任务结果"""
    try:
        result = await TaskResultCache.delete_result(task_id)
        
        if result:
            return SuccessResponse(
                message=f"任务 {task_id} 结果删除成功",
                data={"task_id": task_id}
            )
        else:
            return SuccessResponse(
                message=f"任务 {task_id} 结果不存在",
                data={"task_id": task_id}
            )
    except Exception as e:
        logger.error(f"删除任务结果失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"删除任务结果失败: {str(e)}")


@model_router.post("/set")
@log_execution_time
async def set_model_info(request: ModelInfoRequest):
    """设置模型信息"""
    try:
        result = await ModelInfoCache.set_model_info(request.model_id, request.model_data)
        
        if result:
            return SuccessResponse(
                message=f"模型 {request.model_id} 信息设置成功",
                data={"model_id": request.model_id}
            )
        else:
            raise HTTPException(status_code=500, detail="设置模型信息失败")
    except Exception as e:
        logger.error(f"设置模型信息失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"设置模型信息失败: {str(e)}")


@model_router.get("/get/{model_id}")
@log_execution_time
async def get_model_info(model_id: str):
    """获取模型信息"""
    try:
        model_data = await ModelInfoCache.get_model_info(model_id)
        
        if model_data is not None:
            return SuccessResponse(
                message=f"模型 {model_id} 信息获取成功",
                data={"model_id": model_id, "model_data": model_data}
            )
        else:
            return SuccessResponse(
                message=f"模型 {model_id} 信息不存在",
                data={"model_id": model_id, "model_data": None}
            )
    except Exception as e:
        logger.error(f"获取模型信息失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取模型信息失败: {str(e)}")


@model_router.delete("/delete/{model_id}")
@log_execution_time
async def delete_model_info(model_id: str):
    """删除模型信息"""
    try:
        result = await ModelInfoCache.delete_model_info(model_id)
        
        if result:
            return SuccessResponse(
                message=f"模型 {model_id} 信息删除成功",
                data={"model_id": model_id}
            )
        else:
            return SuccessResponse(
                message=f"模型 {model_id} 信息不存在",
                data={"model_id": model_id}
            )
    except Exception as e:
        logger.error(f"删除模型信息失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"删除模型信息失败: {str(e)}")


@model_router.post("/set_list")
@log_execution_time
async def set_model_list(model_list: List[Dict[str, Any]] = Body(...)):
    """设置模型列表"""
    try:
        result = await ModelInfoCache.set_model_list(model_list)
        
        if result:
            return SuccessResponse(
                message="模型列表设置成功",
                data={"count": len(model_list)}
            )
        else:
            raise HTTPException(status_code=500, detail="设置模型列表失败")
    except Exception as e:
        logger.error(f"设置模型列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"设置模型列表失败: {str(e)}")


@model_router.get("/get_list")
@log_execution_time
async def get_model_list():
    """获取模型列表"""
    try:
        model_list = await ModelInfoCache.get_model_list()
        
        if model_list is not None:
            return SuccessResponse(
                message="模型列表获取成功",
                data={"model_list": model_list, "count": len(model_list)}
            )
        else:
            return SuccessResponse(
                message="模型列表不存在",
                data={"model_list": None, "count": 0}
            )
    except Exception as e:
        logger.error(f"获取模型列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取模型列表失败: {str(e)}")


@api_router.post("/set")
@log_execution_time
async def set_api_response(request: APIResponseRequest):
    """设置API响应"""
    try:
        result = await APIResponseCache.set_response(
            request.endpoint, 
            request.params, 
            request.response_data
        )
        
        if result:
            return SuccessResponse(
                message=f"API {request.endpoint} 响应设置成功",
                data={"endpoint": request.endpoint}
            )
        else:
            raise HTTPException(status_code=500, detail="设置API响应失败")
    except Exception as e:
        logger.error(f"设置API响应失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"设置API响应失败: {str(e)}")


@api_router.post("/get")
@log_execution_time
async def get_api_response(endpoint: str = Body(...), params: Dict[str, Any] = Body(...)):
    """获取API响应"""
    try:
        response_data = await APIResponseCache.get_response(endpoint, params)
        
        if response_data is not None:
            return SuccessResponse(
                message=f"API {endpoint} 响应获取成功",
                data={"endpoint": endpoint, "response_data": response_data}
            )
        else:
            return SuccessResponse(
                message=f"API {endpoint} 响应不存在",
                data={"endpoint": endpoint, "response_data": None}
            )
    except Exception as e:
        logger.error(f"获取API响应失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取API响应失败: {str(e)}")


@lock_router.post("/acquire")
@log_execution_time
async def acquire_lock(request: LockRequest):
    """获取分布式锁"""
    try:
        lock = DistributedLock(request.key, request.timeout)
        result = await lock.acquire()
        
        if result:
            return SuccessResponse(
                message=f"锁 {request.key} 获取成功",
                data={"key": request.key, "identifier": lock.identifier}
            )
        else:
            return SuccessResponse(
                message=f"锁 {request.key} 获取失败",
                data={"key": request.key, "identifier": None}
            )
    except Exception as e:
        logger.error(f"获取分布式锁失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取分布式锁失败: {str(e)}")


@lock_router.post("/release")
@log_execution_time
async def release_lock(key: str = Body(...), identifier: str = Body(...)):
    """释放分布式锁"""
    try:
        lock = DistributedLock(key)
        lock.identifier = identifier
        result = await lock.release()
        
        if result:
            return SuccessResponse(
                message=f"锁 {key} 释放成功",
                data={"key": key}
            )
        else:
            return SuccessResponse(
                message=f"锁 {key} 释放失败或不是锁的持有者",
                data={"key": key}
            )
    except Exception as e:
        logger.error(f"释放分布式锁失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"释放分布式锁失败: {str(e)}")


@rate_limit_router.post("/check")
@log_execution_time
async def check_rate_limit(request: RateLimitRequest):
    """检查限流"""
    try:
        rate_limiter = RateLimiter(request.key, request.limit, request.window)
        is_allowed = await rate_limiter.is_allowed()
        
        return SuccessResponse(
            message=f"限流检查完成",
            data={
                "key": request.key,
                "limit": request.limit,
                "window": request.window,
                "allowed": is_allowed
            }
        )
    except Exception as e:
        logger.error(f"限流检查失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"限流检查失败: {str(e)}")


# 创建应用实例（必须在所有路由定义之后）
app = create_app()

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8006,
        reload=True,
        log_level="info"
    )