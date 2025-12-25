"""
任务服务主应用（Redis-only）

目标：
- 任务/结果等不入库，仅使用 Redis 缓存（允许丢失、支持 TTL）
- 提供：创建任务 / 查询任务 / 列表 / 更新 / 删除

说明：
- 该服务不再依赖 PostgreSQL。
- api-gateway 会把登录用户的 user_id 注入到创建任务与列表查询。
"""

import os
import sys
import json
import uuid
import logging
from dotenv import load_dotenv
from contextlib import asynccontextmanager
from typing import Dict, Any, List, Optional, Tuple

# 加载环境变量
load_dotenv()

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Query, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from celery import Celery

# 添加共享模块路径
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "shared"))

from shared.schemas.schemas import (
    TaskCreate,
    TaskUpdate,
    PaginationParams,
    HealthCheck,
    ErrorResponse,
)
from shared.utils.helpers import (
    log_execution_time,
    get_current_time,
    get_redis_client,
    safe_json_dumps,
    safe_json_loads,
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Celery配置（可选：若未启动 worker，任务会停留在队列中）
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/1")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/2")

celery_app = Celery(
    "tasks",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_routes={
        "app.tasks.prediction_task": {"queue": "prediction"},
        "app.tasks.segmentation_task": {"queue": "segmentation"},
        "app.tasks.analysis_task": {"queue": "analysis"},
    },
    worker_prefetch_multiplier=1,
    task_acks_late=True,
)

# Redis key 设计
TASK_KEY_PREFIX = "task:"
TASK_TTL_SECONDS = int(os.getenv("TASK_TTL_SECONDS", "86400"))  # 默认 24h

# 全局状态
app_state: Dict[str, Any] = {
    "redis_client": None,
}


async def _get_redis():
    redis_client = app_state.get("redis_client")
    if redis_client is None:
        raise HTTPException(status_code=503, detail="Redis 未连接")
    return redis_client


def _task_key(task_id: str) -> str:
    return f"{TASK_KEY_PREFIX}{task_id}"


def _normalize_task_for_frontend(task: Dict[str, Any]) -> Dict[str, Any]:
    """确保返回给前端的数据包含兼容字段。"""
    task_id = task.get("task_id") or task.get("id")
    if task_id:
        task["task_id"] = task_id
        task["id"] = task_id

    # type / task_type
    if "type" not in task and "task_type" in task:
        task["type"] = task.get("task_type")
    if "task_type" not in task and "type" in task:
        task["task_type"] = task.get("type")

    # result / result_data
    if "result" not in task and "result_data" in task:
        task["result"] = task.get("result_data")
    if "result_data" not in task and "result" in task:
        task["result_data"] = task.get("result")

    # error / error_message
    if "error" not in task and "error_message" in task:
        task["error"] = task.get("error_message")
    if "error_message" not in task and "error" in task:
        task["error_message"] = task.get("error")

    # input_data / data
    if "data" not in task and "input_data" in task:
        task["data"] = task.get("input_data")
    if "input_data" not in task and "data" in task:
        task["input_data"] = task.get("data")

    return task


async def _load_task(task_id: str) -> Optional[Dict[str, Any]]:
    redis_client = await _get_redis()
    raw = await redis_client.get(_task_key(task_id))
    if raw is None:
        return None
    try:
        task = safe_json_loads(raw)
        if isinstance(task, dict):
            return _normalize_task_for_frontend(task)
        return None
    except Exception:
        return None


async def _save_task(task_id: str, task: Dict[str, Any], ttl: int = TASK_TTL_SECONDS) -> None:
    redis_client = await _get_redis()
    task = _normalize_task_for_frontend(task)
    await redis_client.set(_task_key(task_id), safe_json_dumps(task), ex=ttl)


async def _scan_task_ids(limit: int = 2000) -> List[str]:
    """扫描 Redis 中的 task key（仅用于最小闭环，规模大时需替换为索引/分页结构）。"""
    redis_client = await _get_redis()

    cursor = 0
    keys: List[str] = []
    while True:
        cursor, batch = await redis_client.scan(cursor=cursor, match=f"{TASK_KEY_PREFIX}*", count=200)
        keys.extend(batch or [])
        if cursor == 0 or len(keys) >= limit:
            break

    task_ids: List[str] = []
    for k in keys[:limit]:
        if isinstance(k, bytes):
            k = k.decode("utf-8")
        if k.startswith(TASK_KEY_PREFIX):
            task_ids.append(k[len(TASK_KEY_PREFIX):])
    return task_ids


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("任务服务启动中...")
    try:
        app_state["redis_client"] = await get_redis_client()
        try:
            await app_state["redis_client"].ping()
            logger.info("Redis 连接成功")
        except Exception:
            logger.warning("Redis ping 失败")
    except Exception as e:
        logger.error(f"初始化 Redis 失败: {e}")
        app_state["redis_client"] = None

    logger.info("任务服务启动完成")
    yield

    logger.info("任务服务关闭中...")
    redis_client = app_state.get("redis_client")
    if redis_client is not None:
        try:
            await redis_client.close()
        except Exception:
            pass
    logger.info("任务服务已关闭")


def create_app() -> FastAPI:
    app = FastAPI(
        title="植物病害检测任务服务",
        description="提供任务创建、状态查询和结果获取服务（Redis-only）",
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

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request, exc: HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(message=str(exc.detail), error_code=f"HTTP_{exc.status_code}").dict(),
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request, exc: Exception):
        logger.error(f"未处理的异常: {str(exc)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(message="服务器内部错误", error_code="INTERNAL_SERVER_ERROR").dict(),
        )

    app.include_router(health_router, prefix="/health", tags=["健康检查"])
    app.include_router(task_router, prefix="/tasks", tags=["任务管理"])
    app.include_router(celery_router, prefix="/celery", tags=["Celery管理"])

    return app


# 路由定义
health_router = APIRouter()
task_router = APIRouter()
celery_router = APIRouter()


@health_router.get("/", response_model=HealthCheck)
@log_execution_time
async def health_check():
    try:
        redis_client = app_state.get("redis_client")
        if redis_client is None:
            redis_status = "disconnected"
        else:
            await redis_client.ping()
            redis_status = "connected"
    except Exception:
        redis_status = "unhealthy"

    # Celery 状态（可选）
    try:
        inspect = celery_app.control.inspect()
        stats = inspect.stats()
        celery_status = "healthy" if stats else "unhealthy"
    except Exception:
        celery_status = "unhealthy"

    return HealthCheck(
        status="healthy" if redis_status == "connected" else "unhealthy",
        timestamp=get_current_time(),
        service="task-service",
        version="1.0.0",
        dependencies={
            "redis": redis_status,
            "celery": celery_status,
        },
    )


@task_router.post("/", response_model=Dict[str, Any])
@log_execution_time
async def create_task(task: TaskCreate, background_tasks: BackgroundTasks):
    """创建任务（Redis-only）"""
    try:
        now = get_current_time()
        task_id = f"task_{now.strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"

        task_data: Dict[str, Any] = {
            "id": task_id,
            "task_id": task_id,
            "user_id": task.user_id,
            "title": task.title,
            "description": task.description,
            "priority": task.priority,
            "task_type": task.task_type,
            "type": task.task_type,
            "input_data": task.input_data,
            "data": task.input_data,
            "status": "pending",
            "progress": 0.0,
            "status_message": "pending",
            "result_data": None,
            "result": None,
            "error_message": None,
            "error": None,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "started_at": None,
            "completed_at": None,
        }

        await _save_task(task_id, task_data, ttl=TASK_TTL_SECONDS)

        # 分发到 Celery（若 worker 未启动，仅入队不执行）
        try:
            if task.task_type == "prediction":
                celery_app.send_task("app.tasks.prediction_task", args=[task_id], queue="prediction")
            elif task.task_type == "segmentation":
                celery_app.send_task("app.tasks.segmentation_task", args=[task_id], queue="segmentation")
            elif task.task_type == "analysis":
                celery_app.send_task("app.tasks.analysis_task", args=[task_id], queue="analysis")
            else:
                celery_app.send_task("app.tasks.default_task", args=[task_id])
        except Exception as e:
            logger.warning(f"Celery 分发失败（可忽略）: {e}")

        return task_data
    except Exception as e:
        logger.error(f"创建任务失败: {str(e)}")
        raise HTTPException(status_code=500, detail="创建任务失败")


@task_router.get("/", response_model=Dict[str, Any])
@log_execution_time
async def list_tasks(
    pagination: PaginationParams = Depends(),
    user_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    task_type: Optional[str] = Query(None),
):
    """获取任务列表（Redis 扫描，最小闭环实现）"""
    try:
        task_ids = await _scan_task_ids(limit=2000)

        tasks: List[Dict[str, Any]] = []
        for tid in task_ids:
            t = await _load_task(tid)
            if not t:
                continue
            if user_id is not None and int(t.get("user_id") or 0) != int(user_id):
                continue
            if status is not None and t.get("status") != status:
                continue
            if task_type is not None and (t.get("task_type") or t.get("type")) != task_type:
                continue
            tasks.append(t)

        # 按 created_at 倒序
        def _sort_key(x: Dict[str, Any]):
            return x.get("created_at") or ""

        tasks.sort(key=_sort_key, reverse=True)

        total = len(tasks)
        page = pagination.page
        size = pagination.size
        start = (page - 1) * size
        end = start + size
        items = tasks[start:end]
        pages = (total + size - 1) // size if size else 0

        return {
            "items": items,
            "total": total,
            "page": page,
            "size": size,
            "pages": pages,
        }
    except Exception as e:
        logger.error(f"获取任务列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取任务列表失败")


@task_router.get("/{task_id}", response_model=Dict[str, Any])
@log_execution_time
async def get_task(task_id: str):
    """获取任务详情"""
    try:
        task_data = await _load_task(task_id)
        if not task_data:
            raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")
        return task_data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取任务详情失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取任务详情失败")


@task_router.put("/{task_id}", response_model=Dict[str, Any])
@log_execution_time
async def update_task(task_id: str, task_update: TaskUpdate):
    """更新任务"""
    try:
        task_data = await _load_task(task_id)
        if not task_data:
            raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")

        update_data = task_update.dict(exclude_unset=True)
        for k, v in update_data.items():
            task_data[k] = v

        # 字段兼容
        if "result_data" in update_data and "result" not in update_data:
            task_data["result"] = update_data.get("result_data")
        if "error_message" in update_data and "error" not in update_data:
            task_data["error"] = update_data.get("error_message")

        # 状态机补充
        if task_data.get("status") == "processing" and not task_data.get("started_at"):
            task_data["started_at"] = get_current_time().isoformat()
        if task_data.get("status") in ("completed", "failed") and not task_data.get("completed_at"):
            task_data["completed_at"] = get_current_time().isoformat()

        task_data["updated_at"] = get_current_time().isoformat()
        await _save_task(task_id, task_data, ttl=TASK_TTL_SECONDS)

        return {
            "message": "任务更新成功",
            "task": task_data,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新任务失败: {str(e)}")
        raise HTTPException(status_code=500, detail="更新任务失败")


@task_router.delete("/{task_id}", response_model=Dict[str, Any])
@log_execution_time
async def delete_task(task_id: str):
    """删除任务"""
    try:
        redis_client = await _get_redis()
        await redis_client.delete(_task_key(task_id))
        return {"message": f"任务 {task_id} 已删除"}
    except Exception as e:
        logger.error(f"删除任务失败: {str(e)}")
        raise HTTPException(status_code=500, detail="删除任务失败")


@celery_router.get("/stats", response_model=Dict[str, Any])
@log_execution_time
async def get_celery_stats():
    """获取Celery统计信息"""
    try:
        inspect = celery_app.control.inspect()
        stats = inspect.stats()
        active = inspect.active()
        scheduled = inspect.scheduled()
        reserved = inspect.reserved()

        return {
            "stats": stats,
            "active_tasks": active,
            "scheduled_tasks": scheduled,
            "reserved_tasks": reserved,
        }
    except Exception as e:
        logger.error(f"获取Celery统计信息失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取Celery统计信息失败")


@celery_router.post("/purge", response_model=Dict[str, Any])
@log_execution_time
async def purge_celery_queue(queue: Optional[str] = None):
    """清空Celery队列"""
    try:
        celery_app.control.purge()
        if queue:
            return {"message": f"队列 {queue} 已清空"}
        return {"message": "所有队列已清空"}
    except Exception as e:
        logger.error(f"清空Celery队列失败: {str(e)}")
        raise HTTPException(status_code=500, detail="清空Celery队列失败")


# 创建应用实例（必须在所有路由定义之后）
app = create_app()


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8002, reload=True, log_level="info")
