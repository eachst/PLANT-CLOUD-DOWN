# 植物病害检测系统 - 部署指南

## 概述

本系统是一个基于深度学习的植物病害检测微服务架构，支持：
- 独立模型服务（PyTorch/ONNX）
- 异步任务处理（Celery + Redis）
- Redis缓存服务
- 前端Web界面
- ESP32边缘设备支持

## 系统架构

```
┌─────────────┐
│  ESP32设备  │ ──┐
│  OV2640摄像头│   │
└─────────────┘   │
                  │ HTTP/HTTPS
┌─────────────┐   │
│  前端应用    │   │
│  (Next.js)  │ ──┤
└─────────────┘   │
                  │
┌─────────────┐   │
│  API网关     │ ──┘
│  (Nginx)    │
└─────────────┘
       │
       ├──> 任务服务 (FastAPI + Celery)
       ├──> 模型服务 (FastAPI + PyTorch/ONNX)
       └──> 缓存服务 (FastAPI + Redis)
```

## 快速开始

### 方式一：一键部署（推荐）

1. **准备服务器**
   - 腾讯云Ubuntu 20.04/22.04服务器
   - 至少2核4GB内存
   - 建议使用GPU实例（用于模型推理）

2. **运行一键部署脚本**

```bash
# 上传项目到服务器
scp -r plant-disease-microservices root@your-server-ip:/opt/

# SSH连接到服务器
ssh root@your-server-ip

# 运行一键部署脚本
cd /opt/plant-disease-microservices
chmod +x scripts/one_click_deploy.sh
sudo ./scripts/one_click_deploy.sh
```

3. **配置环境变量**

编辑 `/opt/plant-disease/.env` 文件：

```bash
# 数据库密码（必须修改）
POSTGRES_PASSWORD=your_secure_password

# 腾讯云COS配置（可选，用于存储图像）
COS_SECRET_ID=your_secret_id
COS_SECRET_KEY=your_secret_key
COS_REGION=ap-beijing
COS_BUCKET=your_bucket_name

# JWT密钥（自动生成，建议修改）
JWT_SECRET_KEY=your_jwt_secret_key
```

4. **上传模型文件**

将训练好的模型文件上传到 `/opt/plant-disease/models/` 目录：

```bash
# 支持格式：.pt, .pth, .onnx
scp your_model.pt root@your-server-ip:/opt/plant-disease/models/

# 可选：创建模型配置文件
cat > /opt/plant-disease/models/your_model_config.json << EOF
{
  "input_size": [224, 224],
  "mean": [0.485, 0.456, 0.406],
  "std": [0.229, 0.224, 0.225],
  "class_names": ["healthy", "disease1", "disease2"]
}
EOF
```

5. **重启服务**

```bash
cd /opt/plant-disease
docker-compose -f docker-compose.prod.yml restart
```

### 方式二：分步部署

1. **运行服务器准备脚本**

```bash
sudo ./scripts/deploy_tencent_cloud.sh
```

2. **手动部署**

```bash
# 复制项目文件
sudo cp -r . /opt/plant-disease/

# 配置环境变量
sudo nano /opt/plant-disease/.env

# 运行部署脚本
cd /opt/plant-disease
sudo ./deploy.sh
```

## ESP32边缘设备部署

### 硬件要求

- ESP32开发板（推荐ESP32-CAM）
- OV2640摄像头模块
- Micro USB数据线
- WiFi网络

### 软件安装

1. **安装Arduino IDE**

下载并安装 [Arduino IDE](https://www.arduino.cc/en/software)

2. **安装ESP32支持**

- 打开Arduino IDE
- 进入 `文件` -> `首选项`
- 在"附加开发板管理器网址"中添加：
  ```
  https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
  ```
- 进入 `工具` -> `开发板` -> `开发板管理器`
- 搜索"esp32"并安装

3. **安装必要库**

- ArduinoJson (版本 6.x)
- ESP32 Camera（通常已包含）

### 配置和上传

1. **修改配置**

打开 `edge-devices/esp32/plant_disease_detector.ino`，修改：

```cpp
// WiFi配置
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";

// 云端API配置
const char* api_base_url = "http://your-server-ip:8000/api";
```

2. **上传代码**

- 选择开发板：`工具` -> `开发板` -> `ESP32 Arduino` -> 选择您的型号
- 选择端口：`工具` -> `端口`
- 点击上传

3. **查看结果**

打开串口监视器（波特率115200）查看检测结果

## 服务管理

### 查看服务状态

```bash
cd /opt/plant-disease
docker-compose -f docker-compose.prod.yml ps
```

### 查看日志

```bash
# 查看所有服务日志
docker-compose -f docker-compose.prod.yml logs -f

# 查看特定服务日志
docker-compose -f docker-compose.prod.yml logs -f model-service
docker-compose -f docker-compose.prod.yml logs -f task-service
```

### 重启服务

```bash
# 重启所有服务
docker-compose -f docker-compose.prod.yml restart

# 重启特定服务
docker-compose -f docker-compose.prod.yml restart model-service
```

### 停止服务

```bash
docker-compose -f docker-compose.prod.yml down
```

### 更新服务

```bash
cd /opt/plant-disease
git pull  # 如果有使用Git
docker-compose -f docker-compose.prod.yml pull
docker-compose -f docker-compose.prod.yml up -d --build
```

## API使用

### 直接预测（同步）

```bash
curl -X POST "http://your-server-ip:8000/api/predictions/direct" \
  -F "file=@image.jpg" \
  -F "model_name=default" \
  -F "confidence_threshold=0.5"
```

### 异步预测

```bash
# 创建预测任务
curl -X POST "http://your-server-ip:8000/api/predictions/" \
  -H "Content-Type: application/json" \
  -d '{
    "image_url": "https://example.com/image.jpg",
    "model_name": "default",
    "confidence_threshold": 0.5
  }'

# 获取结果（使用返回的task_id）
curl "http://your-server-ip:8000/api/predictions/{task_id}"
```

## 监控和日志

### Prometheus

访问：`http://your-server-ip:9090`

### Grafana

访问：`http://your-server-ip:3001`
- 用户名：admin
- 密码：admin（首次登录后需要修改）

### 日志位置

- 容器日志：`docker-compose logs`
- 应用日志：`/opt/plant-disease/logs/`

## 故障排除

### 1. 服务无法启动

```bash
# 检查Docker状态
systemctl status docker

# 检查端口占用
netstat -tulpn | grep :8000

# 查看详细错误
docker-compose -f docker-compose.prod.yml logs
```

### 2. 模型加载失败

- 检查模型文件是否存在：`ls -lh /opt/plant-disease/models/`
- 检查模型格式是否支持（.pt, .pth, .onnx）
- 查看模型服务日志：`docker-compose logs model-service`

### 3. ESP32连接失败

- 检查WiFi配置是否正确
- 检查服务器IP地址和端口
- 检查防火墙设置
- 查看串口监视器输出

### 4. 数据库连接失败

```bash
# 检查PostgreSQL容器
docker-compose ps postgres

# 检查数据库日志
docker-compose logs postgres

# 测试连接
docker-compose exec postgres psql -U postgres -d plant_disease -c "SELECT 1;"
```

## 性能优化

### GPU支持

如果服务器有NVIDIA GPU：

1. 安装NVIDIA驱动和Docker GPU支持（部署脚本会自动检测并安装）

2. 在 `docker-compose.prod.yml` 中取消注释GPU配置：

```yaml
model-service:
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            count: 1
            capabilities: [gpu]
```

### 模型优化

- 使用ONNX格式模型（更快）
- 使用量化模型（减少内存占用）
- 调整批处理大小

## 安全建议

1. **修改默认密码**
   - 数据库密码
   - JWT密钥
   - Grafana密码

2. **使用HTTPS**
   - 生产环境使用正式SSL证书
   - 配置防火墙规则

3. **API认证**
   - 启用API密钥认证
   - 使用JWT令牌

4. **定期更新**
   - 更新系统包
   - 更新Docker镜像
   - 更新依赖库

## 支持

如有问题，请查看：
- 项目文档：`docs/`
- 日志文件：`/opt/plant-disease/logs/`
- GitHub Issues

## 许可证

MIT License

