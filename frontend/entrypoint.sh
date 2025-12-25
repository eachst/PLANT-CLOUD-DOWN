#!/bin/bash

# 等待依赖服务启动
echo "等待API网关服务启动..."
while ! nc -z api-gateway 80; do
  sleep 1
done
echo "API网关服务已启动"

# 创建日志目录
mkdir -p /app/logs

# 设置环境变量
export NODE_ENV=production
export PORT=3000

# 启动应用
echo "启动前端应用..."
exec node server.js