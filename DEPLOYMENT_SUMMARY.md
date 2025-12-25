# 植物病害检测系统 - 完整部署总结

## 项目概述

本项目是一个完整的植物病害检测系统，包含：

1. **后端微服务架构**
   - API网关（Nginx）
   - 模型服务（FastAPI + PyTorch/ONNX）
   - 任务服务（FastAPI + Celery）
   - 缓存服务（FastAPI + Redis）

2. **前端应用**
   - Next.js Web界面

3. **边缘设备**
   - ESP32 + OV2640摄像头

4. **基础设施**
   - PostgreSQL数据库
   - Redis缓存和消息队列
   - Prometheus监控
   - Grafana可视化

## 已完成的构建内容

### 1. 模型服务完善 ✅

**文件：**
- `services/model-service/model_loader.py` - 深度学习模型加载器
- `services/model-service/main.py` - 更新的主应用

**功能：**
- 支持PyTorch模型（.pt, .pth）
- 支持ONNX模型（.onnx）
- 自动GPU/CPU检测
- 图像预处理和后处理
- 同步和异步预测接口
- 文件上传支持

**API端点：**
- `POST /predictions/` - 异步预测
- `POST /predictions/direct` - 同步直接预测
- `GET /predictions/{task_id}` - 获取预测结果
- `GET /models/` - 列出所有模型
- `GET /models/{model_name}` - 获取模型信息

### 2. ESP32边缘设备代码 ✅

**文件：**
- `edge-devices/esp32/plant_disease_detector.ino` - 主程序
- `edge-devices/esp32/camera_pins.h` - 摄像头引脚定义
- `edge-devices/esp32/README.md` - 使用说明

**功能：**
- WiFi连接
- OV2640摄像头图像采集
- 定时上传图像到云端
- 接收和显示检测结果
- 串口输出

### 3. 腾讯云部署脚本 ✅

**文件：**
- `scripts/deploy_tencent_cloud.sh` - 服务器环境准备脚本
- `scripts/one_click_deploy.sh` - 一键部署脚本

**功能：**
- 自动安装Docker和Docker Compose
- 配置防火墙
- 安装NVIDIA GPU支持（如果检测到）
- 创建项目目录结构
- 生成SSL证书
- 配置系统优化参数

### 4. 部署文档 ✅

**文件：**
- `README_DEPLOYMENT.md` - 完整部署指南
- `DEPLOYMENT_SUMMARY.md` - 本文档

## 部署步骤

### 快速部署（推荐）

```bash
# 1. 上传项目到服务器
scp -r plant-disease-microservices root@your-server-ip:/opt/

# 2. SSH连接到服务器
ssh root@your-server-ip

# 3. 运行一键部署
cd /opt/plant-disease-microservices
chmod +x scripts/one_click_deploy.sh
sudo ./scripts/one_click_deploy.sh

# 4. 配置环境变量
nano /opt/plant-disease/.env

# 5. 上传模型文件
scp your_model.pt root@your-server-ip:/opt/plant-disease/models/

# 6. 重启服务
cd /opt/plant-disease
docker-compose -f docker-compose.prod.yml restart
```

### ESP32设备配置

1. 安装Arduino IDE和ESP32支持
2. 打开 `edge-devices/esp32/plant_disease_detector.ino`
3. 修改WiFi和API配置
4. 上传代码到ESP32
5. 打开串口监视器查看结果

## 系统架构图

```
                    ┌──────────────┐
                    │  ESP32设备   │
                    │  OV2640摄像头│
                    └──────┬───────┘
                           │
                           │ HTTP/HTTPS
                           │
        ┌──────────────────┴──────────────────┐
        │                                      │
┌───────▼────────┐                  ┌─────────▼──────┐
│   前端应用     │                  │   API网关      │
│   (Next.js)   │                  │   (Nginx)      │
└───────┬────────┘                  └────────┬───────┘
        │                                    │
        └────────────────┬───────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
┌───────▼──────┐  ┌──────▼──────┐  ┌─────▼──────┐
│  任务服务    │  │  模型服务    │  │  缓存服务  │
│ (Celery)    │  │ (PyTorch)    │  │  (Redis)   │
└──────┬───────┘  └──────┬───────┘  └─────┬──────┘
       │                 │                 │
       └─────────────────┼─────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
┌───────▼──────┐  ┌──────▼──────┐  ┌─────▼──────┐
│ PostgreSQL   │  │   Redis     │  │ Prometheus │
│  数据库      │  │  缓存/队列   │  │   监控     │
└──────────────┘  └─────────────┘  └────────────┘
```

## 服务端口

- **80/443** - Nginx API网关（HTTP/HTTPS）
- **3000** - 前端应用
- **8000** - API网关（直接访问）
- **8002** - 任务服务
- **8003** - 模型服务
- **8006** - 缓存服务
- **9090** - Prometheus
- **3001** - Grafana
- **5432** - PostgreSQL
- **6379** - Redis

## 环境变量配置

创建 `/opt/plant-disease/.env` 文件：

```bash
# 数据库配置
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_secure_password
POSTGRES_DB=plant_disease

# Redis配置
REDIS_URL=redis://redis:6379/0

# JWT配置
JWT_SECRET_KEY=$(openssl rand -hex 32)
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# 腾讯云COS配置（可选）
COS_SECRET_ID=your_secret_id
COS_SECRET_KEY=your_secret_key
COS_REGION=ap-beijing
COS_BUCKET=your_bucket_name

# Grafana配置
GRAFANA_ADMIN_PASSWORD=admin

# 模型路径
MODEL_PATH=/app/models
```

## 模型文件格式

支持以下格式：
- **PyTorch**: `.pt`, `.pth`
- **ONNX**: `.onnx`

模型配置文件（可选）`{model_name}_config.json`：

```json
{
  "input_size": [224, 224],
  "mean": [0.485, 0.456, 0.406],
  "std": [0.229, 0.224, 0.225],
  "class_names": ["healthy", "disease1", "disease2", "disease3"]
}
```

## API使用示例

### 1. 直接预测（同步）

```bash
curl -X POST "http://your-server:8000/api/predictions/direct" \
  -F "file=@test_image.jpg" \
  -F "model_name=default" \
  -F "confidence_threshold=0.5"
```

响应：
```json
{
  "success": true,
  "predictions": [
    {"class": "disease1", "confidence": 0.85, "class_id": 1},
    {"class": "healthy", "confidence": 0.15, "class_id": 0}
  ],
  "top_prediction": {
    "class": "disease1",
    "confidence": 0.85,
    "class_id": 1
  },
  "processing_time": 0.23,
  "model_name": "default"
}
```

### 2. 异步预测

```bash
# 创建任务
curl -X POST "http://your-server:8000/api/predictions/" \
  -H "Content-Type: application/json" \
  -d '{
    "image_url": "https://example.com/image.jpg",
    "model_name": "default",
    "confidence_threshold": 0.5
  }'

# 获取结果
curl "http://your-server:8000/api/predictions/{task_id}"
```

## 监控和维护

### 查看服务状态

```bash
cd /opt/plant-disease
docker-compose -f docker-compose.prod.yml ps
```

### 查看日志

```bash
# 所有服务
docker-compose -f docker-compose.prod.yml logs -f

# 特定服务
docker-compose -f docker-compose.prod.yml logs -f model-service
```

### 健康检查

```bash
# API网关
curl http://localhost:8000/health/

# 模型服务
curl http://localhost:8003/health/

# 任务服务
curl http://localhost:8002/health/
```

## 故障排除

### 常见问题

1. **模型加载失败**
   - 检查模型文件格式
   - 查看模型服务日志
   - 确认模型配置文件格式正确

2. **ESP32连接失败**
   - 检查WiFi配置
   - 确认服务器IP和端口
   - 检查防火墙规则

3. **服务无法启动**
   - 检查Docker状态
   - 查看容器日志
   - 检查端口占用

## 性能优化建议

1. **使用GPU**
   - 服务器需要NVIDIA GPU
   - 安装NVIDIA驱动和Docker GPU支持
   - 在docker-compose.prod.yml中启用GPU配置

2. **模型优化**
   - 使用ONNX格式（更快）
   - 使用量化模型（减少内存）
   - 调整批处理大小

3. **缓存策略**
   - 启用Redis缓存
   - 缓存常用预测结果
   - 使用CDN加速图像传输

## 安全建议

1. **修改默认密码**
   - 数据库密码
   - JWT密钥
   - Grafana密码

2. **使用HTTPS**
   - 生产环境使用正式SSL证书
   - 配置防火墙规则

3. **API认证**
   - 启用API密钥
   - 使用JWT令牌

## 下一步

1. **完善前端界面** - 添加图像上传和结果展示功能
2. **添加更多模型** - 支持更多病害类型
3. **优化性能** - GPU加速、模型量化
4. **扩展功能** - 历史记录、统计分析

## 支持

- 部署文档：`README_DEPLOYMENT.md`
- 项目文档：`docs/`
- ESP32说明：`edge-devices/esp32/README.md`

---

**构建完成时间：** 2024年
**版本：** 1.0.0
**许可证：** MIT

