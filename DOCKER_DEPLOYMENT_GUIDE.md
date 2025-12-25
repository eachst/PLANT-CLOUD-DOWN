# 植物病害检测系统 - Docker部署指南

## 1. 项目Docker配置概述

植物病害检测系统采用微服务架构，通过Docker和Docker Compose进行部署。项目包含开发环境和生产环境两种配置，便于开发和部署。

## 2. 目录结构

```
├── services/              # 后端微服务
│   ├── api-gateway/       # API网关服务
│   ├── user-service/      # 用户服务
│   ├── task-service/      # 任务服务
│   ├── model-service/     # 模型服务
│   └── cache-service/     # 缓存服务
├── frontend/              # 前端应用
├── infrastructure/        # 基础设施配置
│   ├── nginx/             # Nginx配置
│   ├── postgres/          # PostgreSQL配置
│   ├── redis/             # Redis配置
│   └── monitoring/        # 监控配置
├── docker-compose.yml     # 开发环境配置
└── docker-compose.prod.yml # 生产环境配置
```

## 3. 开发环境配置 (docker-compose.yml)

### 3.1 服务列表

| 服务名称 | 功能 | 端口映射 | 依赖 |
|----------|------|----------|------|
| api-gateway | API网关 | 8000:8000 | user-service, task-service, model-service, cache-service |
| user-service | 用户管理 | - | postgres, redis |
| task-service | 任务管理 | - | postgres, redis |
| model-service | 模型预测 | - | redis |
| cache-service | 缓存服务 | - | redis |
| celery-worker | 异步任务处理 | - | redis, postgres |
| celery-beat | 定时任务 | - | redis, postgres |
| redis | 缓存和消息队列 | 6379:6379 | - |
| postgres | 数据库 | 5432:5432 | - |
| frontend | 前端应用 | 3000:3000 | api-gateway |

### 3.2 主要特性

- 本地代码挂载，便于开发调试
- 端口直接映射到宿主机，方便访问
- 适合开发环境使用

## 4. 生产环境配置 (docker-compose.prod.yml)

### 4.1 服务列表

| 服务名称 | 功能 | 端口映射 | 依赖 |
|----------|------|----------|------|
| api-gateway | 反向代理（Nginx） | 80:80, 443:443 | task-service, model-service, cache-service |
| task-service | 任务管理 | - | postgres, redis |
| model-service | 模型预测 | - | redis |
| cache-service | 缓存服务 | - | redis |
| celery-worker | 异步任务处理 | - | redis, postgres |
| celery-beat | 定时任务 | - | redis, postgres |
| redis | 缓存和消息队列 | 6379:6379 | - |
| postgres | 数据库 | 5432:5432 | - |
| frontend | 前端应用 | 3000:3000 | api-gateway |
| prometheus | 监控服务 | 9090:9090 | - |
| grafana | 监控面板 | 3001:3000 | prometheus |

### 4.2 主要特性

- 使用Nginx作为API网关和反向代理
- 包含监控服务（Prometheus和Grafana）
- 更完善的配置，适合生产部署

## 5. Dockerfile配置

### 5.1 前端Dockerfile

| 特性 | 配置 | 说明 |
|------|------|------|
| 基础镜像 | node:18-alpine | 使用Node.js 18-alpine，体积小 |
| 构建方式 | 多阶段构建 | 减小最终镜像体积 |
| 依赖安装 | 腾讯云npm源 | 加速依赖下载 |
| 端口暴露 | 3000 | 前端应用端口 |
| 健康检查 | 未配置 | 可根据需要添加 |
| 权限设置 | 非root用户 | 提高安全性 |

### 5.2 后端服务Dockerfile

| 特性 | 配置 | 说明 |
|------|------|------|
| 基础镜像 | python:3.9-slim | 使用Python 3.9-slim，体积小 |
| 系统源配置 | 腾讯云apt源 | 加速系统包下载 |
| 依赖安装 | 腾讯云pip源 | 加速Python依赖下载 |
| 端口暴露 | 8000 | 后端服务端口 |
| 健康检查 | 配置 | 定期检查服务健康状态 |
| 权限设置 | 可执行权限 | 确保脚本可执行 |

## 6. Nginx配置 (infrastructure/nginx/nginx.conf)

### 6.1 主要配置

| 配置项 | 说明 |
|--------|------|
| 监听端口 | 80（HTTP） |
| API路由 | /api/ -> http://api-gateway |
| 健康检查 | /health -> http://api-gateway |
| 前端应用 | / -> http://api-gateway |
| Gzip压缩 | 启用，压缩级别6 |
| 超时设置 | 60秒 |

### 6.2 SSL配置

生产环境配置包含SSL支持，证书位置：`infrastructure/nginx/ssl/`

## 7. 部署步骤

### 7.1 开发环境部署

```bash
# 1. 克隆代码
git clone <repository-url>
cd plant-disease-detection

# 2. 启动开发环境
docker-compose up -d

# 3. 访问服务
# 前端: http://localhost:3000
# API文档: http://localhost:8000/docs
# 数据库: localhost:5432
# Redis: localhost:6379

# 4. 查看日志
docker-compose logs -f

# 5. 停止服务
docker-compose down
```

### 7.2 生产环境部署

```bash
# 1. 克隆代码
git clone <repository-url>
cd plant-disease-detection

# 2. 准备环境变量
cp .env.example .env
# 编辑.env文件，设置必要的环境变量

# 3. 生成SSL证书（可选）
mkdir -p infrastructure/nginx/ssl
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout infrastructure/nginx/ssl/key.pem \
  -out infrastructure/nginx/ssl/cert.pem \
  -subj "/C=CN/ST=Beijing/L=Beijing/O=PlantDisease/CN=localhost"

# 4. 启动生产环境
docker-compose -f docker-compose.prod.yml up -d

# 5. 访问服务
# 前端: http://localhost:3000
# API: http://localhost/api
# 监控: http://localhost:3001 (admin/admin)
# Prometheus: http://localhost:9090

# 6. 查看日志
docker-compose -f docker-compose.prod.yml logs -f

# 7. 停止服务
docker-compose -f docker-compose.prod.yml down
```

## 8. 镜像优化建议

### 8.1 前端镜像

- ✅ 使用多阶段构建，减小镜像体积
- ✅ 使用Alpine基础镜像
- ✅ 移除不必要的依赖和文件
- ✅ 使用非root用户

### 8.2 后端镜像

- ✅ 使用Python slim基础镜像
- ✅ 配置国内源加速下载
- ✅ 移除不必要的系统包
- ✅ 配置健康检查
- ✅ 使用非root用户

## 9. 性能优化建议

### 9.1 服务配置

- ✅ 合理的资源限制（可根据实际需求添加）
- ✅ 适当的超时设置
- ✅ 启用Gzip压缩
- ✅ 合理的缓存策略

### 9.2 数据库配置

- ✅ 使用持久化存储
- ✅ 适当的内存分配
- ✅ 配置连接池

### 9.3 Redis配置

- ✅ 使用持久化存储
- ✅ 适当的内存限制
- ✅ 配置合理的过期策略

## 10. 监控与日志

### 10.1 监控服务

生产环境配置包含Prometheus和Grafana监控：

| 服务 | 功能 | 访问地址 |
|------|------|----------|
| Prometheus | 指标收集 | http://localhost:9090 |
| Grafana | 监控面板 | http://localhost:3001 |

### 10.2 日志管理

- Docker容器日志：使用`docker-compose logs`命令查看
- 应用日志：挂载到宿主机（根据实际配置）
- Nginx日志：容器内`/var/log/nginx/`目录

## 11. 安全建议

### 11.1 容器安全

- ✅ 使用非root用户运行容器
- ✅ 定期更新基础镜像
- ✅ 限制容器资源
- ✅ 配置适当的网络隔离

### 11.2 应用安全

- ✅ 使用HTTPS协议
- ✅ 配置适当的CORS策略
- ✅ 定期更新依赖包
- ✅ 配置合理的认证和授权机制

### 11.3 数据库安全

- ✅ 使用强密码
- ✅ 限制访问IP
- ✅ 定期备份数据
- ✅ 配置适当的权限

## 12. 常见问题排查

### 12.1 服务启动失败

```bash
# 查看容器日志
docker-compose logs <service-name>

# 检查容器状态
docker-compose ps

# 查看详细错误信息
docker-compose up <service-name>
```

### 12.2 网络连接问题

```bash
# 检查网络配置
docker network ls

# 检查容器网络
docker inspect <container-name> | grep -A 20 Networks

# 测试网络连接
docker-compose exec <service-name> ping <other-service-name>
```

### 12.3 资源不足

```bash
# 检查资源使用情况
docker stats

# 调整资源限制
# 在docker-compose.yml中添加resources配置
```

## 13. 升级建议

### 13.1 镜像升级

```bash
# 拉取最新镜像
docker-compose pull

# 重启服务
docker-compose up -d
```

### 13.2 配置更新

```bash
# 更新配置文件
sudo nano docker-compose.yml

# 重启服务
docker-compose up -d
```

## 14. 部署架构图

```
┌─────────────────────────────────────────────────────────────┐
│                     客户端浏览器                           │
└─────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────┐
│                     Nginx (API网关)                        │
└─────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────┐
│                     服务路由                               │
├──────────────┬──────────────┬──────────────┬───────────────┤
│ API网关     │ 用户服务     │ 任务服务     │ 模型服务     │
├──────────────┼──────────────┼──────────────┼───────────────┤
│ 前端应用     │ 数据库       │ Redis        │ 模型文件     │
└──────────────┴──────────────┴──────────────┴───────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────┐
│                     监控服务                               │
├──────────────┬──────────────┬──────────────┬───────────────┤
│ Prometheus   │ Grafana       │ 日志收集     │ 告警服务     │
└──────────────┴──────────────┴──────────────┴───────────────┘
```

## 15. 版本变更日志

| 日期 | 版本 | 变更内容 |
|------|------|----------|
| 2025-12-14 | v1.0 | 初始版本，包含开发和生产环境配置 |

## 16. 联系方式

如有部署相关问题，请联系：
- 项目邮箱：your-email@example.com
- GitHub Issues：[项目Issues链接](https://github.com/your-repo/issues)

---

本指南详细介绍了植物病害检测系统的Docker部署配置，包括开发环境和生产环境的部署步骤、常见问题排查和优化建议。通过遵循本指南，您可以快速部署和管理植物病害检测系统。
