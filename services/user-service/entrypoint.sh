#!/bin/bash

# 设置环境变量
export PYTHONPATH=/app
export PYTHONUNBUFFERED=1

# 启动服务
exec uvicorn main:app --host 0.0.0.0 --port 8001 --log-level ${UVICORN_LOG_LEVEL:-info} --workers ${UVICORN_WORKERS:-2}
