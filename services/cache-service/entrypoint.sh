#!/bin/bash

# 等待Redis服务启动
echo "等待Redis服务启动..."
while ! nc -z redis 6379; do
  sleep 1
done
echo "Redis服务已启动"

# 创建日志目录
mkdir -p /app/logs

# 设置环境变量
export PYTHONPATH=/app

# 启动应用
echo "启动Redis缓存服务..."
exec uvicorn main:app --host 0.0.0.0 --port 8006 --log-level ${UVICORN_LOG_LEVEL:-info} --workers ${UVICORN_WORKERS:-2}
