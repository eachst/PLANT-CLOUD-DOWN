# 植物病害检测系统 - 微服务架构

这是一个基于微服务架构的植物病害检测系统，提供图像识别、病害诊断、用户管理等功能。

## 📚 文档导航

### 🚀 部署指南（必读）

- **[完整部署指南（小白版）](./COMPLETE_DEPLOYMENT_GUIDE.md)** ⭐ **推荐新手从这里开始**
  - 从零开始的详细步骤
  - 包含服务器购买、配置、部署全流程
  - 每一步都有详细说明和截图提示

- **[部署检查清单](./DEPLOYMENT_CHECKLIST.md)** ✅
  - 确保完整部署的检查项
  - 逐项验证部署状态

- **[故障排除指南](./TROUBLESHOOTING_GUIDE.md)** 🔧
  - 常见问题和解决方案
  - 详细的诊断步骤

### 📖 其他文档

- **[快速开始](./QUICK_START.md)** - 5分钟快速部署（适合有经验的用户）
- **[部署总结](./DEPLOYMENT_SUMMARY.md)** - 系统架构和功能说明
- **[部署文档](./README_DEPLOYMENT.md)** - 详细部署指南
- **[集成模型指南](./services/model-service/ENSEMBLE_MODEL_GUIDE.md)** - 集成模型和蒸馏模型配置

## 系统架构

系统采用微服务架构，包含以下服务：

- **API网关**: 统一入口，路由请求到各个微服务
- **用户服务**: 用户注册、登录、认证管理
- **模型服务**: 病害检测模型管理和预测
- **任务服务**: 异步任务处理和任务状态管理
- **缓存服务**: Redis缓存，提高系统性能
- **前端应用**: 基于Next.js的Web界面
- **数据库**: PostgreSQL数据存储
- **消息队列**: Redis作为Celery的消息代理

## 技术栈

- **后端**: Python, FastAPI, SQLAlchemy, Celery
- **前端**: Next.js, React, Ant Design, Tailwind CSS
- **数据库**: PostgreSQL
- **缓存**: Redis
- **容器化**: Docker, Docker Compose
- **反向代理**: Nginx
- **监控**: Prometheus, Grafana

## 快速开始

### 环境要求

- Docker 20.0+
- Docker Compose 2.0+
- Node.js 18+ (用于本地开发)
- Python 3.9+ (用于本地开发)

### 启动系统

1. 克隆项目
```bash
git clone <repository-url>
cd plant-disease-microservices
```

2. 创建环境变量文件
```bash
cp .env.example .env
# 编辑.env文件，配置必要的环境变量
```

3. 启动所有服务
```bash
docker-compose up -d
```

4. 初始化数据库
```bash
docker-compose exec postgres psql -U postgres -d plant_disease -f /docker-entrypoint-initdb.d/init.sql
```

5. 访问应用
- 前端应用: http://localhost:3000
- API文档: http://localhost:8000/docs
- 监控面板: http://localhost:3001 (admin/admin)

### 开发模式

1. 启动基础服务
```bash
docker-compose up -d postgres redis
```

2. 启动各个微服务（开发模式）
```bash
# 用户服务
cd services/user-service
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8001

# 模型服务
cd services/model-service
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8003

# 任务服务
cd services/task-service
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8002

# 缓存服务
cd services/cache-service
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8006

# API网关
cd services/api-gateway
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

3. 启动前端应用
```bash
cd frontend
npm install
npm run dev
```

## API文档

各个微服务的API文档可以通过以下地址访问：

- API网关: http://localhost:8000/docs
- 用户服务: http://localhost:8001/docs
- 任务服务: http://localhost:8002/docs
- 模型服务: http://localhost:8003/docs
- 缓存服务: http://localhost:8006/docs

## 部署

### 生产环境部署

1. 构建生产镜像
```bash
docker-compose -f docker-compose.prod.yml build
```

2. 启动生产服务
```bash
docker-compose -f docker-compose.prod.yml up -d
```

### 云服务部署

系统支持部署到各种云平台，如AWS、Azure、阿里云等。具体部署步骤请参考各平台的部署文档。

## 监控和日志

系统集成了Prometheus和Grafana进行监控：

- Prometheus: http://localhost:9090
- Grafana: http://localhost:3001 (admin/admin)

日志文件位于各服务的`/app/logs`目录下。

## 故障排除

### 常见问题

1. **服务启动失败**
   - 检查端口是否被占用
   - 查看服务日志: `docker-compose logs [service-name]`

2. **数据库连接失败**
   - 确认PostgreSQL服务已启动
   - 检查数据库连接字符串

3. **Redis连接失败**
   - 确认Redis服务已启动
   - 检查Redis连接字符串

### 日志查看

```bash
# 查看所有服务日志
docker-compose logs

# 查看特定服务日志
docker-compose logs [service-name]

# 实时查看日志
docker-compose logs -f [service-name]
```

## 贡献指南

1. Fork项目
2. 创建功能分支
3. 提交更改
4. 推送到分支
5. 创建Pull Request

## 许可证

MIT License