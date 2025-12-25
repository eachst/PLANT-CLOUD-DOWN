#!/bin/bash

# 模型服务启动脚本

set -e

# 等待Redis服务启动
echo "等待Redis服务启动..."
while ! nc -z redis 6379; do
  sleep 1
done
echo "Redis服务已启动"

# 创建日志目录
mkdir -p /app/logs

# 设置环境变量
export PYTHONPATH=/app:$PYTHONPATH

# 启动服务
echo "启动模型服务..."
exec uvicorn main:app --host 0.0.0.0 --port 8003 --log-level ${UVICORN_LOG_LEVEL:-info} --workers ${UVICORN_WORKERS:-1}
