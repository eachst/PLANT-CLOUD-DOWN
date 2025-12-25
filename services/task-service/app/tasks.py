"""Celery 任务（轻量占位版，避免重依赖）。

worker 会更新 Redis 中的 `task:{task_id}`。
"""

import os
import sys
import time
import logging
from typing import Dict, Any, Optional

import redis
from celery import Task

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "shared"))

from shared.utils.helpers import log_execution_time, get_current_time, safe_json_dumps, safe_json_loads

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

try:
    from main import celery_app
except Exception:
    from celery import Celery
    celery_app = Celery("tasks")

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)


def _get_task(task_id: str) -> Optional[Dict[str, Any]]:
    raw = redis_client.get(f"task:{task_id}")
    if not raw:
        return None
    try:
        data = safe_json_loads(raw)
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def _save_task(task_id: str, data: Dict[str, Any], ttl_seconds: int = 86400) -> None:
    redis_client.setex(f"task:{task_id}", ttl_seconds, safe_json_dumps(data))


def _mark_processing(task_id: str) -> None:
    t = _get_task(task_id)
    if not t:
        raise ValueError(f"任务 {task_id} 不存在")
    now = get_current_time().isoformat()
    t["status"] = "processing"
    t.setdefault("started_at", now)
    t["updated_at"] = now
    _save_task(task_id, t)


def _complete(task_id: str, result: Dict[str, Any]) -> None:
    t = _get_task(task_id)
    if not t:
        raise ValueError(f"任务 {task_id} 不存在")
    now = get_current_time().isoformat()
    t["status"] = "completed"
    t["progress"] = 100.0
    t["result_data"] = result
    t["result"] = result
    t["completed_at"] = now
    t["updated_at"] = now
    _save_task(task_id, t)


def _fail(task_id: str, err: str) -> None:
    t = _get_task(task_id)
    if not t:
        return
    now = get_current_time().isoformat()
    t["status"] = "failed"
    t["error_message"] = err
    t["error"] = err
    t.setdefault("completed_at", now)
    t["updated_at"] = now
    _save_task(task_id, t)


class BaseTask(Task):
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.error(f"任务 {task_id} 失败: {exc}")
        _fail(task_id, str(exc))


@log_execution_time
def update_task_progress(task_id: str, progress: float, message: str = "") -> None:
    t = _get_task(task_id)
    if not t:
        return
    t["progress"] = float(progress)
    if message:
        t["status_message"] = message
    t["updated_at"] = get_current_time().isoformat()
    _save_task(task_id, t)


@celery_app.task(bind=True, base=BaseTask)
def prediction_task(self, task_id: str):
    _mark_processing(task_id)
    update_task_progress(task_id, 30.0, "处理中...")
    time.sleep(1)
    update_task_progress(task_id, 70.0, "生成结果...")
    time.sleep(1)
    result = {"top_prediction": {"plant": "unknown", "disease": "unknown", "confidence": 0.0}}
    _complete(task_id, result)
    return result


@celery_app.task(bind=True, base=BaseTask)
def segmentation_task(self, task_id: str):
    _mark_processing(task_id)
    update_task_progress(task_id, 60.0, "处理中...")
    time.sleep(1)
    result = {"mask_url": None, "segmented_image_url": None, "note": "stub"}
    _complete(task_id, result)
    return result


@celery_app.task(bind=True, base=BaseTask)
def analysis_task(self, task_id: str):
    _mark_processing(task_id)
    update_task_progress(task_id, 50.0, "分析中...")
    time.sleep(1)
    result = {"analysis": {}, "note": "stub"}
    _complete(task_id, result)
    return result


@celery_app.task(bind=True, base=BaseTask)
def default_task(self, task_id: str):
    _mark_processing(task_id)
    update_task_progress(task_id, 100.0, "完成")
    result = {"note": "default stub"}
    _complete(task_id, result)
    return result
