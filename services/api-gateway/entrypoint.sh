#!/bin/bash

# 等待依赖服务启动
echo "等待依赖服务启动..."

# 等待用户服务
while ! nc -z user-service 8001; do
  echo "等待用户服务启动..."
  sleep 0.1
done

# 等待任务服务
while ! nc -z task-service 8002; do
  echo "等待任务服务启动..."
  sleep 0.1
done

# 等待模型服务
while ! nc -z model-service 8003; do
  echo "等待模型服务启动..."
  sleep 0.1
done

# 等待缓存服务
while ! nc -z cache-service 8006; do
  echo "等待缓存服务启动..."
  sleep 0.1
done

echo "所有依赖服务已启动"

# 创建日志目录
mkdir -p /app/logs

# 设置环境变量
export PYTHONPATH=/app

# 启动FastAPI应用
echo "启动API网关..."
exec uvicorn main:app --host 0.0.0.0 --port 8000 --log-level ${UVICORN_LOG_LEVEL:-info} --workers ${UVICORN_WORKERS:-2}
