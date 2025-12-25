#!/bin/bash

# 植物病害检测系统 - 部署脚本
# 适用于生产环境部署

set -e

echo "=========================================="
echo "植物病害检测系统 - 生产环境部署"
echo "=========================================="

# 检查Docker和Docker Compose是否安装
if ! command -v docker &> /dev/null; then
    echo "错误: Docker未安装，请先安装Docker"
    exit 1
fi

COMPOSE_CMD=""
if docker compose version &> /dev/null; then
    COMPOSE_CMD="docker compose"
elif command -v docker-compose &> /dev/null; then
    COMPOSE_CMD="docker-compose"
else
    echo "错误: Docker Compose未安装（需要 docker compose 或 docker-compose）"
    exit 1
fi

# 检查环境变量文件
if [ ! -f .env ]; then
    echo "创建环境变量文件..."
    if [ -f .env.example ]; then
        cp .env.example .env
    else
        echo "警告: .env.example 文件不存在，创建默认 .env 文件..."
        cat > .env << 'EOF'
# 数据库配置
POSTGRES_USER=postgres
POSTGRES_PASSWORD=password
POSTGRES_DB=plant_disease

# Redis配置
REDIS_URL=redis://redis:6379/0

# JWT配置
JWT_SECRET_KEY=your-secret-key-change-in-production
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# 对象存储配置（可选）
COS_SECRET_ID=
COS_SECRET_KEY=
COS_REGION=
COS_BUCKET=

# Grafana配置
GRAFANA_ADMIN_PASSWORD=admin
EOF
    fi
    echo "请编辑 .env 文件配置您的环境变量，然后重新运行此脚本"
    exit 1
fi

# 加载环境变量
source .env

# 创建必要的目录
echo "创建必要的目录..."
mkdir -p infrastructure/nginx/ssl
mkdir -p infrastructure/monitoring
mkdir -p logs
mkdir -p models

# 生成SSL证书（自签名，生产环境请使用正式证书）
if [ ! -f infrastructure/nginx/ssl/cert.pem ]; then
    echo "生成自签名SSL证书..."
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout infrastructure/nginx/ssl/key.pem \
        -out infrastructure/nginx/ssl/cert.pem \
        -subj "/C=CN/ST=State/L=City/O=Organization/CN=localhost"
fi

# 创建Nginx配置
if [ ! -f infrastructure/nginx/nginx.conf ]; then
    echo "创建Nginx配置文件..."
    mkdir -p infrastructure/nginx
    cat > infrastructure/nginx/nginx.conf << 'EOF'
events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    client_max_body_size 20M;

    upstream api-gateway-app {
        server api-gateway-app:8000;
    }

    upstream frontend {
        server frontend:3000;
    }

    server {
        listen 80;
        server_name _;

        # API请求：通过带尾斜杠的 proxy_pass 去掉 /api 前缀
        location /api/ {
            proxy_pass http://api-gateway-app/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        location = /api {
            return 301 /api/;
        }

        location /health {
            proxy_pass http://api-gateway-app/health/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        location / {
            proxy_pass http://frontend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
EOF
fi

# 创建Redis配置
if [ ! -f infrastructure/redis/redis.conf ]; then
    echo "创建Redis配置文件..."
    mkdir -p infrastructure/redis
    cat > infrastructure/redis/redis.conf << 'EOF'
# Redis配置文件
bind 0.0.0.0
port 6379
timeout 0
tcp-keepalive 300

# 持久化配置
save 900 1
save 300 10
save 60 10000

# 日志配置
loglevel notice
logfile ""

# 内存配置
maxmemory 256mb
maxmemory-policy allkeys-lru

# 安全配置
# requirepass your-redis-password
EOF
fi

# 创建Prometheus配置
if [ ! -f infrastructure/monitoring/prometheus.yml ]; then
    echo "创建Prometheus配置文件..."
    cat > infrastructure/monitoring/prometheus.yml << 'EOF'
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  # - "first_rules.yml"
  # - "second_rules.yml"

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'task-service'
    static_configs:
      - targets: ['task-service:8002']

  - job_name: 'model-service'
    static_configs:
      - targets: ['model-service:8003']

  - job_name: 'cache-service'
    static_configs:
      - targets: ['cache-service:8006']
EOF
fi

# 创建Grafana数据源配置
if [ ! -f infrastructure/monitoring/grafana/datasources/prometheus.yml ]; then
    echo "创建Grafana数据源配置..."
    mkdir -p infrastructure/monitoring/grafana/datasources
    cat > infrastructure/monitoring/grafana/datasources/prometheus.yml << 'EOF'
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
EOF
fi

# 创建数据库初始化脚本
if [ ! -f infrastructure/postgres/init.sql ]; then
    echo "创建数据库初始化脚本..."
    mkdir -p infrastructure/postgres
    cat > infrastructure/postgres/init.sql << 'EOF'
-- 创建数据库扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 创建用户表
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 创建任务表
CREATE TABLE IF NOT EXISTS tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id),
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    result JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_tasks_user_id ON tasks(user_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_created_at ON tasks(created_at);
EOF
fi

# 拉取最新镜像
echo "拉取最新Docker镜像..."
$COMPOSE_CMD -f docker-compose.prod.yml pull

# 构建自定义镜像
echo "构建自定义镜像..."
$COMPOSE_CMD -f docker-compose.prod.yml build

# 启动服务
echo "启动服务..."
$COMPOSE_CMD -f docker-compose.prod.yml up -d

# 等待服务启动
echo "等待服务启动..."
sleep 30

# 初始化数据库
echo "初始化数据库..."
# 等待数据库完全启动
sleep 5
# 检查数据库连接
$COMPOSE_CMD -f docker-compose.prod.yml exec -T postgres psql -U postgres -d plant_disease -c "SELECT 1;" || echo "警告: 数据库连接检查失败，请手动检查数据库状态"

# 检查服务状态
echo "检查服务状态..."
$COMPOSE_CMD -f docker-compose.prod.yml ps

echo "=========================================="
echo "部署完成！"
echo "=========================================="
echo "前端应用: http://localhost"
echo "API文档: http://localhost/api/docs"
echo ""
echo "=========================================="