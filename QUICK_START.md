# 快速开始指南

## 5分钟快速部署

### 1. 准备服务器（腾讯云Ubuntu）

```bash
# SSH连接到服务器
ssh root@your-server-ip
```

### 2. 一键部署

```bash
# 下载或上传项目
cd /opt
git clone your-repo-url plant-disease-microservices
# 或使用scp上传

# 运行一键部署
cd plant-disease-microservices
chmod +x scripts/one_click_deploy.sh
sudo ./scripts/one_click_deploy.sh
```

### 3. 配置环境变量

```bash
nano /opt/plant-disease/.env
```

**必须修改：**
- `POSTGRES_PASSWORD` - 数据库密码
- `JWT_SECRET_KEY` - JWT密钥（使用 `openssl rand -hex 32` 生成）

**可选配置：**
- 腾讯云COS配置（用于图像存储）

### 4. 上传模型

```bash
# 上传模型文件
scp your_model.pt root@your-server-ip:/opt/plant-disease/models/

# 可选：创建配置文件
cat > /opt/plant-disease/models/your_model_config.json << EOF
{
  "input_size": [224, 224],
  "mean": [0.485, 0.456, 0.406],
  "std": [0.229, 0.224, 0.225],
  "class_names": ["healthy", "disease1", "disease2"]
}
EOF
```

### 5. 重启服务

```bash
cd /opt/plant-disease
docker-compose -f docker-compose.prod.yml restart
```

### 6. 测试API

```bash
# 健康检查
curl http://localhost:8000/health/

# 直接预测（需要准备测试图像）
curl -X POST "http://localhost:8000/api/predictions/direct" \
  -F "file=@test_image.jpg" \
  -F "model_name=default"
```

## ESP32设备配置

### 1. 安装Arduino IDE

下载：https://www.arduino.cc/en/software

### 2. 安装ESP32支持

1. 文件 -> 首选项
2. 添加：`https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json`
3. 工具 -> 开发板管理器 -> 搜索"esp32" -> 安装

### 3. 安装库

工具 -> 管理库 -> 安装：
- ArduinoJson (6.x)

### 4. 配置和上传

1. 打开 `edge-devices/esp32/plant_disease_detector.ino`
2. 修改WiFi和API配置
3. 选择开发板和端口
4. 点击上传

## 常用命令

```bash
# 查看服务状态
cd /opt/plant-disease
docker-compose -f docker-compose.prod.yml ps

# 查看日志
docker-compose -f docker-compose.prod.yml logs -f model-service

# 重启服务
docker-compose -f docker-compose.prod.yml restart

# 停止服务
docker-compose -f docker-compose.prod.yml down

# 更新服务
docker-compose -f docker-compose.prod.yml pull
docker-compose -f docker-compose.prod.yml up -d --build
```

## 访问地址

- **前端**: http://your-server-ip
- **API文档**: http://your-server-ip:8000/docs
- **Grafana**: http://your-server-ip:3001 (admin/admin)
- **Prometheus**: http://your-server-ip:9090

## 故障排除

### 服务无法启动

```bash
# 检查Docker
systemctl status docker

# 查看错误日志
docker-compose -f docker-compose.prod.yml logs
```

### 模型加载失败

```bash
# 检查模型文件
ls -lh /opt/plant-disease/models/

# 查看模型服务日志
docker-compose -f docker-compose.prod.yml logs model-service
```

### ESP32连接失败

1. 检查WiFi配置
2. 检查服务器IP和端口
3. 查看串口监视器输出

## 需要帮助？

查看完整文档：
- `README_DEPLOYMENT.md` - 详细部署指南
- `DEPLOYMENT_SUMMARY.md` - 系统总结
- `edge-devices/esp32/README.md` - ESP32使用说明

