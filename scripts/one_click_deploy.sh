#!/bin/bash

# 一键部署脚本 - 植物病害检测系统
# 适用于腾讯云Ubuntu服务器

set -e

echo "=========================================="
echo "植物病害检测系统 - 一键部署"
echo "=========================================="

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DEPLOY_DIR="$PROJECT_ROOT"
# 设置默认环境变量
ENVIRONMENT=${ENVIRONMENT:-development}

# 函数
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# 检查是否为root用户
if [ "$EUID" -ne 0 ]; then 
    print_error "请使用root权限运行此脚本"
    print_info "使用: sudo $0"
    exit 1
fi

# 1. 检查系统要求
print_step "检查系统要求..."

# 检查操作系统
if [ ! -f /etc/os-release ]; then
    print_error "无法检测操作系统"
    exit 1
fi

. /etc/os-release
if [ "$ID" != "ubuntu" ]; then
    print_warn "此脚本针对Ubuntu系统优化，当前系统: $ID"
    read -p "是否继续? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# 检查Docker
if ! command -v docker &> /dev/null; then
    print_info "Docker未安装，将自动安装..."
    
    # 配置腾讯云apt镜像源（提高国内下载速度）
    print_info "配置腾讯云apt镜像源..."

    CODENAME="${VERSION_CODENAME:-}"
    if [ -z "$CODENAME" ]; then
        CODENAME="$(lsb_release -cs 2>/dev/null || true)"
    fi
    if [ -z "$CODENAME" ]; then
        CODENAME="jammy"
    fi

    sudo tee /etc/apt/sources.list.d/tencent-cloud.list <<EOF
# 腾讯云Ubuntu镜像源
deb http://mirrors.tencentyun.com/ubuntu/ ${CODENAME} main restricted universe multiverse
deb http://mirrors.tencentyun.com/ubuntu/ ${CODENAME}-updates main restricted universe multiverse
deb http://mirrors.tencentyun.com/ubuntu/ ${CODENAME}-security main restricted universe multiverse
deb http://mirrors.tencentyun.com/ubuntu/ ${CODENAME}-backports main restricted universe multiverse
EOF
    
    # 更新apt源优先级
    sudo apt-get update -y || true
    
    # 尝试使用腾讯云镜像源安装Docker
    print_info "使用腾讯云镜像源安装Docker..."
    
    # 添加腾讯云Docker源
    sudo apt-get install -y apt-transport-https ca-certificates curl gnupg-agent software-properties-common || true
    
    # 使用腾讯云的Docker GPG密钥和源
    curl -fsSL https://mirrors.tencentyun.com/docker-ce/linux/ubuntu/gpg | sudo apt-key add - || true
    sudo add-apt-repository "deb [arch=amd64] https://mirrors.tencentyun.com/docker-ce/linux/ubuntu ${CODENAME} stable" || true
    
    # 更新并安装Docker
    sudo apt-get update -y || true
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin || true
    
    # 如果腾讯云源安装失败，尝试使用Ubuntu默认docker.io包
    if ! command -v docker &> /dev/null; then
        print_warn "腾讯云源安装Docker失败，尝试使用Ubuntu默认docker.io包..."
        sudo apt-get install -y docker.io docker-compose || true
    fi
    
    # 启动并启用Docker服务
    print_info "启动Docker服务..."
    systemctl start docker || true
    systemctl enable docker || true
    
    # 检查Docker是否安装成功
    if ! command -v docker &> /dev/null; then
        print_error "Docker安装失败，请手动安装Docker后重试"
        exit 1
    fi
    
    print_info "Docker安装成功！"
fi

# 检查Docker Compose
DOCKER_COMPOSE_CMD=""

if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE_CMD="docker-compose"
    print_info "使用 docker-compose 命令"
elif docker compose version &> /dev/null; then
    DOCKER_COMPOSE_CMD="docker compose"
    print_info "使用 docker compose 命令"
else
    print_info "Docker Compose未安装，将自动安装..."

    # 优先安装 docker-compose-plugin（提供 docker compose）
    if command -v apt-get &> /dev/null; then
        sudo apt-get update -y || true
        sudo apt-get install -y docker-compose-plugin || true

        if docker compose version &> /dev/null; then
            DOCKER_COMPOSE_CMD="docker compose"
            print_info "Docker Compose安装成功！"
        else
            print_warn "docker-compose-plugin 安装失败，尝试安装 docker-compose..."
            sudo apt-get install -y docker-compose || true

            if command -v docker-compose &> /dev/null; then
                DOCKER_COMPOSE_CMD="docker-compose"
                print_info "Docker Compose安装成功！"
            else
                print_warn "Ubuntu仓库安装失败，尝试从GitHub下载 docker-compose..."
                DOCKER_COMPOSE_VERSION="2.24.0"
                if curl -fsSL --connect-timeout 5 https://github.com > /dev/null 2>&1; then
                    curl -L "https://github.com/docker/compose/releases/download/v${DOCKER_COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
                    chmod +x /usr/local/bin/docker-compose
                    ln -sf /usr/local/bin/docker-compose /usr/bin/docker-compose
                    DOCKER_COMPOSE_CMD="docker-compose"
                    print_info "Docker Compose安装成功！"
                else
                    print_error "无法下载Docker Compose，请手动安装后重试"
                    exit 1
                fi
            fi
        fi
    else
        print_error "无法安装Docker Compose，请手动安装后重试"
        exit 1
    fi
fi

# 检查jq命令（用于解析JSON响应）
if ! command -v jq &> /dev/null; then
    print_info "jq命令未安装，将自动安装..."
    if command -v apt-get &> /dev/null; then
        sudo apt-get update -y || true
        sudo apt-get install -y jq || true
        if command -v jq &> /dev/null; then
            print_info "jq安装成功！"
        else
            print_warn "jq安装失败，健康检查将无法显示详细信息"
        fi
    else
        print_warn "无法安装jq，健康检查将无法显示详细信息"
    fi
fi

print_info "系统要求检查完成"

# 2. 配置可靠的腾讯云Docker镜像源（适合腾讯云服务器）
print_step "配置腾讯云Docker镜像源..."

# 腾讯云Docker镜像源地址
TENCENT_DOCKER_MIRROR="https://mirror.ccs.tencentyun.com"

# 检查腾讯云镜像源域名解析是否正常
if ! nslookup mirror.ccs.tencentyun.com > /dev/null 2>&1; then
    print_warn "腾讯云镜像源解析异常，将直接使用Docker Hub"
else
    # 清理所有旧的Docker配置
    print_info "清理所有旧的Docker配置..."
    sudo rm -f /etc/docker/daemon.json
    
    # 创建新的配置文件，使用腾讯云镜像源（腾讯云服务器专用，稳定可靠）
    print_info "配置Docker使用腾讯云镜像源（腾讯云服务器专用，稳定可靠）..."
    sudo mkdir -p /etc/docker
    sudo tee /etc/docker/daemon.json <<-EOF
{
  "registry-mirrors": ["$TENCENT_DOCKER_MIRROR"]
}
EOF
    
    # 重启Docker服务以应用配置
    print_info "重启Docker服务以应用配置..."
    sudo systemctl daemon-reload
    sudo systemctl restart docker
    
    # 等待Docker服务完全启动
    sleep 5
    
    print_info "Docker配置完成！使用腾讯云镜像源，提高腾讯云服务器访问速度"
fi

# 3. 准备部署目录
print_step "准备部署目录..."
mkdir -p $DEPLOY_DIR/models
mkdir -p $DEPLOY_DIR/logs
mkdir -p $DEPLOY_DIR/data
mkdir -p $DEPLOY_DIR/infrastructure/nginx/ssl
mkdir -p $DEPLOY_DIR/infrastructure/nginx
mkdir -p $DEPLOY_DIR/infrastructure/redis
mkdir -p $DEPLOY_DIR/infrastructure/postgres
mkdir -p $DEPLOY_DIR/infrastructure/monitoring/grafana/datasources
mkdir -p $DEPLOY_DIR/infrastructure/monitoring/grafana/dashboards

print_info "部署目录创建完成"

# 4. 检查环境变量文件
print_step "检查环境变量配置..."
if [ ! -f "$DEPLOY_DIR/.env" ]; then
    print_warn ".env文件不存在，创建默认配置..."
    
    # 生成随机JWT密钥
    JWT_SECRET_KEY=$(openssl rand -hex 32)
    
    cat > $DEPLOY_DIR/.env << EOF
# 数据库配置
POSTGRES_USER=postgres
POSTGRES_PASSWORD=PlantDisease2024!
POSTGRES_DB=plant_disease
DATABASE_URL=postgresql://postgres:PlantDisease2024!@postgres:5432/plant_disease

# Redis配置
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2

# JWT配置
JWT_SECRET_KEY=$JWT_SECRET_KEY
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# 服务URL配置（服务间通信）
USER_SERVICE_URL=http://user-service:8001
TASK_SERVICE_URL=http://task-service:8002
MODEL_SERVICE_URL=http://model-service:8003
CACHE_SERVICE_URL=http://cache-service:8006

# 模型路径
MODEL_PATH=/app/models

# 服务端口配置
API_GATEWAY_PORT=8000
USER_SERVICE_PORT=8001
TASK_SERVICE_PORT=8002
MODEL_SERVICE_PORT=8003
CACHE_SERVICE_PORT=8006

# 前端配置（开发环境建议使用相对路径 /api，避免写死 localhost）
NEXT_PUBLIC_API_BASE_URL=/api
NEXT_PUBLIC_API_URL=

# 腾讯云COS配置（开发环境可留空）
# COS_SECRET_ID=your-cos-secret-id
# COS_SECRET_KEY=your-cos-secret-key
# COS_REGION=your-cos-region
# COS_BUCKET=your-cos-bucket

# Grafana配置
GRAFANA_ADMIN_PASSWORD=admin

# 监控配置
PROMETHEUS_PORT=9090
GRAFANA_PORT=3001

# 日志配置
LOG_LEVEL=DEBUG

# 开发环境配置
DEBUG=True
ENVIRONMENT=development
EOF
    print_warn "请编辑 $DEPLOY_DIR/.env 文件配置您的环境变量"
    print_info "开发环境下腾讯云COS配置可留空"
    read -p "按Enter继续，或Ctrl+C退出以编辑.env文件..."
fi

# 5. 检查SSL证书（如果需要）
print_step "检查SSL证书..."
SSL_CERT_DIR="$DEPLOY_DIR/infrastructure/nginx/ssl"
SSL_CERT_FILE="$SSL_CERT_DIR/cert.pem"
SSL_KEY_FILE="$SSL_CERT_DIR/key.pem"

if [ ! -f "$SSL_CERT_FILE" ] || [ ! -f "$SSL_KEY_FILE" ]; then
    print_warn "SSL证书不存在，将生成自签名SSL证书"
    print_warn "注意：自签名SSL证书仅用于测试环境，生产环境请使用正式SSL证书"
    
    # 询问用户是否继续生成自签名证书
    read -p "是否继续生成自签名SSL证书？(y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # 生成自签名SSL证书
        print_info "生成自签名SSL证书..."
        mkdir -p $SSL_CERT_DIR
        openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
            -keyout $SSL_KEY_FILE \
            -out $SSL_CERT_FILE \
            -subj "/C=CN/ST=Beijing/L=Beijing/O=PlantDisease/CN=localhost" || {
            print_error "生成自签名SSL证书失败"
            print_info "您可以手动生成或上传SSL证书到 $SSL_CERT_DIR 目录"
            print_info "证书文件命名：cert.pem（公钥）和 key.pem（私钥）"
        }
        
        if [ -f "$SSL_CERT_FILE" ] && [ -f "$SSL_KEY_FILE" ]; then
            print_info "自签名SSL证书生成完成"
            print_warn "警告：自签名SSL证书在浏览器中会显示安全警告"
            print_warn "生产环境请使用Let's Encrypt或其他可信证书颁发机构的证书"
        fi
    else
        print_info "跳过SSL证书生成，将使用HTTP协议"
        print_info "如果需要使用HTTPS，请手动生成或上传SSL证书到 $SSL_CERT_DIR 目录"
    fi
else
    print_info "SSL证书已存在，跳过生成"
    print_info "证书位置：$SSL_CERT_FILE 和 $SSL_KEY_FILE"
fi

# 6. 创建Nginx配置（如果不存在）
if [ ! -f "$DEPLOY_DIR/infrastructure/nginx/nginx.conf" ]; then
    print_info "创建Nginx配置文件..."
    cat > $DEPLOY_DIR/infrastructure/nginx/nginx.conf << 'EOF'
events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    # 日志格式
    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for"';

    access_log /var/log/nginx/access.log main;
    error_log /var/log/nginx/error.log;

    # 基本设置
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;
    client_max_body_size 20M;

    # Gzip压缩
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types
        text/plain
        text/css
        text/xml
        text/javascript
        application/json
        application/javascript
        application/xml+rss
        application/atom+xml
        image/svg+xml;

    # 上游服务器配置
    upstream api-gateway-app {
        server api-gateway-app:8000;
    }

    upstream frontend {
        server frontend:3000;
    }

    # HTTP服务器配置
    server {
        listen 80;
        server_name _;

        # 静态文件
        location /static/ {
            proxy_pass http://frontend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # 媒体文件
        location /media/ {
            proxy_pass http://frontend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # API请求 - 所有API请求都路由到API网关
        location /api/ {
            # 通过带尾斜杠的 proxy_pass 去掉 /api 前缀
            proxy_pass http://api-gateway-app/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_connect_timeout 60s;
            proxy_send_timeout 60s;
            proxy_read_timeout 60s;
        }

        # 健康检查
        location /health {
            proxy_pass http://api-gateway-app/health/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # 前端应用
        location / {
            proxy_pass http://frontend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_connect_timeout 60s;
            proxy_send_timeout 60s;
            proxy_read_timeout 60s;
            # 处理前端路由
            try_files $uri $uri/ /index.html;
        }
    }
}
EOF
fi

# 7. 创建Redis配置（如果不存在）
if [ ! -f "$DEPLOY_DIR/infrastructure/redis/redis.conf" ]; then
    print_info "创建Redis配置文件..."
    cat > $DEPLOY_DIR/infrastructure/redis/redis.conf << 'EOF'
bind 0.0.0.0
port 6379
timeout 0
tcp-keepalive 300

save 900 1
save 300 10
save 60 10000

loglevel notice
logfile ""

maxmemory 256mb
maxmemory-policy allkeys-lru
EOF
fi

# 8. 创建数据库初始化脚本（如果不存在）
if [ ! -f "$DEPLOY_DIR/infrastructure/postgres/init.sql" ]; then
    print_info "创建数据库初始化脚本..."
    cat > $DEPLOY_DIR/infrastructure/postgres/init.sql << 'EOF'
-- 用户表
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    is_superuser BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 任务表
CREATE TABLE IF NOT EXISTS tasks (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    title VARCHAR(200) NOT NULL,
    description TEXT,
    status VARCHAR(20) DEFAULT 'pending',
    priority VARCHAR(10) DEFAULT 'medium',
    task_type VARCHAR(50) NOT NULL,
    input_data JSON,
    result_data JSON,
    error_message TEXT,
    progress FLOAT DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 模型表
CREATE TABLE IF NOT EXISTS models (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    version VARCHAR(20) NOT NULL,
    model_type VARCHAR(50) NOT NULL,
    description TEXT,
    file_path VARCHAR(500) NOT NULL,
    config JSON,
    metadata JSON,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 通知表
CREATE TABLE IF NOT EXISTS notifications (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    task_id INTEGER REFERENCES tasks(id),
    title VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,
    notification_type VARCHAR(50) DEFAULT 'info',
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- API密钥表
CREATE TABLE IF NOT EXISTS api_keys (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    key_name VARCHAR(100) NOT NULL,
    api_key VARCHAR(255) UNIQUE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    expires_at TIMESTAMP,
    last_used_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 系统日志表
CREATE TABLE IF NOT EXISTS system_logs (
    id SERIAL PRIMARY KEY,
    service_name VARCHAR(100) NOT NULL,
    level VARCHAR(10) NOT NULL,
    message TEXT NOT NULL,
    details JSON,
    user_id INTEGER REFERENCES users(id),
    ip_address VARCHAR(45),
    user_agent VARCHAR(500),
    created_at TIMESTAMP DEFAULT NOW()
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_tasks_user_id ON tasks(user_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_task_type ON tasks(task_type);
CREATE INDEX IF NOT EXISTS idx_notifications_user_id ON notifications(user_id);
CREATE INDEX IF NOT EXISTS idx_notifications_task_id ON notifications(task_id);
CREATE INDEX IF NOT EXISTS idx_notifications_is_read ON notifications(is_read);
CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON api_keys(user_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_api_key ON api_keys(api_key);
CREATE INDEX IF NOT EXISTS idx_system_logs_service_name ON system_logs(service_name);
CREATE INDEX IF NOT EXISTS idx_system_logs_level ON system_logs(level);
CREATE INDEX IF NOT EXISTS idx_system_logs_user_id ON system_logs(user_id);

-- 插入测试数据
INSERT INTO users (username, email, hashed_password, full_name, is_active, is_superuser) VALUES
('admin', 'admin@example.com', '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW', 'Admin User', TRUE, TRUE),
('user1', 'user1@example.com', '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW', 'User One', TRUE, FALSE);
EOF
fi

# 9. 构建和启动服务
print_step "构建Docker镜像..."
cd $DEPLOY_DIR

# 根据环境选择使用的docker-compose文件
if [ -f "$DEPLOY_DIR/docker-compose.prod.yml" ] && [ "$ENVIRONMENT" = "production" ]; then
    print_info "使用生产环境配置文件: docker-compose.prod.yml"
    COMPOSE_FILE="-f docker-compose.prod.yml"
else
    print_info "使用开发环境配置文件: docker-compose.yml"
    COMPOSE_FILE="-f docker-compose.yml"
fi

# 拉取Docker镜像
print_info "拉取Docker镜像..."
$DOCKER_COMPOSE_CMD $COMPOSE_FILE pull || print_warn "拉取镜像失败，将尝试直接构建"

# 构建Docker镜像
print_info "构建Docker镜像..."
$DOCKER_COMPOSE_CMD $COMPOSE_FILE build

print_step "启动服务..."
$DOCKER_COMPOSE_CMD $COMPOSE_FILE up -d

# 10. 服务依赖检查和启动等待
print_step "服务依赖检查..."

# 检查PostgreSQL服务是否启动
print_info "检查PostgreSQL服务..."
if ! $DOCKER_COMPOSE_CMD $COMPOSE_FILE ps | grep -q "postgres.*Up"; then
    print_warn "PostgreSQL服务未启动，正在等待..."
    for i in {1..30}; do
        if $DOCKER_COMPOSE_CMD $COMPOSE_FILE ps | grep -q "postgres.*Up"; then
            print_info "PostgreSQL服务已启动"
            break
        fi
        sleep 1
    done
    
    if ! $DOCKER_COMPOSE_CMD $COMPOSE_FILE ps | grep -q "postgres.*Up"; then
        print_error "PostgreSQL服务启动失败，请检查日志"
        $DOCKER_COMPOSE_CMD $COMPOSE_FILE logs postgres
        exit 1
    fi
else
    print_info "PostgreSQL服务已启动"
fi

# 检查Redis服务是否启动
print_info "检查Redis服务..."
if ! $DOCKER_COMPOSE_CMD $COMPOSE_FILE ps | grep -q "redis.*Up"; then
    print_warn "Redis服务未启动，正在等待..."
    for i in {1..30}; do
        if $DOCKER_COMPOSE_CMD $COMPOSE_FILE ps | grep -q "redis.*Up"; then
            print_info "Redis服务已启动"
            break
        fi
        sleep 1
    done
    
    if ! $DOCKER_COMPOSE_CMD $COMPOSE_FILE ps | grep -q "redis.*Up"; then
        print_error "Redis服务启动失败，请检查日志"
        $DOCKER_COMPOSE_CMD $COMPOSE_FILE logs redis
        exit 1
    fi
else
    print_info "Redis服务已启动"
fi

# 等待所有服务启动
print_info "等待所有服务启动..."
sleep 40

# 11. 检查服务状态
print_step "检查服务状态..."
$DOCKER_COMPOSE_CMD $COMPOSE_FILE ps

# 12. 健康检查
print_step "执行健康检查..."
sleep 20

if [ "$COMPOSE_FILE" = "-f docker-compose.prod.yml" ]; then
    # 生产模式：对外仅 edge-nginx(80)
    if curl -f http://localhost/health &> /dev/null; then
        print_info "入口健康检查(/health): 正常"
    else
        print_warn "入口健康检查(/health): 可能未就绪，请稍后检查"
        print_info "建议查看：$DOCKER_COMPOSE_CMD $COMPOSE_FILE ps / logs"
    fi

    if curl -f http://localhost/ &> /dev/null; then
        print_info "前端入口(/): 正常"
    else
        print_warn "前端入口(/): 可能未就绪，请稍后重试"
    fi
else
    # 开发模式：宿主机暴露 api-gateway(8000) 和 frontend(3000)
    if curl -f http://localhost:8000/health/ &> /dev/null; then
        print_info "API网关: 正常"

        if curl -s http://localhost:8000/health/ | grep -q "healthy"; then
            print_info "依赖服务: 正常"
        else
            print_warn "部分依赖可能未就绪，详细信息:"
            if command -v jq &> /dev/null; then
                curl -s http://localhost:8000/health/ | jq
            else
                curl -s http://localhost:8000/health/
            fi
        fi
    else
        print_warn "API网关: 可能未就绪，请稍后检查"
        print_info "建议查看：$DOCKER_COMPOSE_CMD $COMPOSE_FILE ps / logs"
    fi

    if curl -f http://localhost:3000/ &> /dev/null; then
        print_info "前端: 正常"
    else
        print_warn "前端: 可能未就绪（或首次依赖安装/构建较慢），请稍后重试"
    fi
fi

# 13. 显示部署信息
echo ""
echo "=========================================="
echo -e "${GREEN}部署完成！${NC}"
echo "=========================================="
echo ""
echo "服务访问地址："
if [ "$COMPOSE_FILE" = "-f docker-compose.prod.yml" ]; then
  echo "  - 前端应用: http://$(hostname -I | awk '{print $1}')"
  echo "  - API文档: http://$(hostname -I | awk '{print $1}')/api/docs"
else
  echo "  - 前端应用: http://$(hostname -I | awk '{print $1}'):3000"
  echo "  - API文档: http://$(hostname -I | awk '{print $1}'):8000/docs"
fi
echo ""
echo "常用命令："
echo "  - 查看服务状态: cd $DEPLOY_DIR && $DOCKER_COMPOSE_CMD $COMPOSE_FILE ps"
echo "  - 查看日志: cd $DEPLOY_DIR && $DOCKER_COMPOSE_CMD $COMPOSE_FILE logs -f [service-name]"
echo "  - 重启服务: cd $DEPLOY_DIR && $DOCKER_COMPOSE_CMD $COMPOSE_FILE restart"
echo "  - 停止服务: cd $DEPLOY_DIR && $DOCKER_COMPOSE_CMD $COMPOSE_FILE down"
echo "  - 更新服务: cd $DEPLOY_DIR && git pull && $DOCKER_COMPOSE_CMD $COMPOSE_FILE up -d --build"
echo ""
print_warn "注意: 如果使用自签名SSL证书，浏览器会显示安全警告"
print_warn "生产环境请使用正式SSL证书"
echo ""

