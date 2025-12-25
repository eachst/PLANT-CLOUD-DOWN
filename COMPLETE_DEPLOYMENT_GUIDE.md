# 植物病害检测系统 - 完整部署指南（小白版）

## 📋 目录

1. [系统要求](#系统要求)
2. [准备工作](#准备工作)
3. [服务器购买与配置](#服务器购买与配置)
4. [本地环境准备](#本地环境准备)
5. [代码上传到服务器](#代码上传到服务器)
6. [服务器环境配置](#服务器环境配置)
7. [一键部署执行](#一键部署执行)
8. [模型文件上传](#模型文件上传)
9. [服务启动与验证](#服务启动与验证)
10. [前端访问测试](#前端访问测试)
11. [ESP32设备配置](#esp32设备配置)
12. [常见问题解决](#常见问题解决)
13. [日常维护](#日常维护)

---

## 系统要求

### 服务器要求

**最低配置：**
- CPU: 2核
- 内存: 4GB
- 硬盘: 40GB
- 带宽: 5Mbps

**推荐配置：**
- CPU: 4核或以上
- 内存: 8GB或以上
- 硬盘: 100GB或以上
- 带宽: 10Mbps或以上
- **GPU: NVIDIA GPU（可选，用于加速模型推理）**

### 操作系统

- **Ubuntu 20.04 LTS** 或 **Ubuntu 22.04 LTS**（推荐）

### 软件要求

- SSH客户端（Windows: PuTTY/WinSCP, Mac/Linux: 内置终端）
- 文件传输工具（WinSCP, FileZilla, scp命令）

---

## 准备工作

### 1. 购买腾讯云服务器

#### 步骤1：注册腾讯云账号

1. 访问 [腾讯云官网](https://cloud.tencent.com/)
2. 点击右上角"注册"
3. 填写手机号、验证码、密码等信息完成注册
4. 完成实名认证（需要身份证）

#### 步骤2：购买云服务器

1. 登录腾讯云控制台
2. 进入"云服务器 CVM" → "实例"
3. 点击"新建实例"
4. 配置选择：
   - **地域**：选择离您最近的（如：北京、上海、广州）
   - **机型**：标准型S5（2核4GB起步）
   - **镜像**：Ubuntu Server 20.04 LTS 或 22.04 LTS
   - **系统盘**：50GB SSD云硬盘
   - **网络**：默认VPC，分配公网IP
   - **带宽**：5Mbps（按量计费）或包年包月
   - **安全组**：开放端口 22（SSH）、80（HTTP）、443（HTTPS）、8000（API）
5. 设置登录方式：
   - **密码登录**：设置root密码（请记住！）
   - 或 **SSH密钥**：上传您的公钥
6. 点击"立即购买"并完成支付

#### 步骤3：获取服务器信息

购买成功后，在控制台可以看到：
- **公网IP**：例如 `123.456.789.012`
- **内网IP**：例如 `10.0.0.5`
- **用户名**：`root`（Ubuntu系统）
- **密码**：您设置的密码

**重要：请记录这些信息！**

---

## 本地环境准备

### Windows系统

#### 1. 安装SSH客户端

**方式一：使用PuTTY（推荐）**

1. 下载PuTTY：
   - 访问 https://www.putty.org/
   - 下载 `putty.exe` 和 `pscp.exe`（用于文件传输）

2. 使用PuTTY连接服务器：
   - 打开 `putty.exe`
   - Host Name: 输入服务器公网IP
   - Port: 22
   - Connection type: SSH
   - 点击"Open"
   - 输入用户名：`root`
   - 输入密码（输入时不会显示，直接输入后按Enter）

**方式二：使用Windows 10/11内置SSH**

1. 打开 PowerShell 或 CMD
2. 输入命令：
   ```bash
   ssh root@你的服务器IP
   ```
3. 输入密码

#### 2. 安装文件传输工具

**使用WinSCP（推荐）**

1. 下载WinSCP：
   - 访问 https://winscp.net/
   - 下载并安装

2. 连接服务器：
   - 打开WinSCP
   - 文件协议：SFTP
   - 主机名：服务器公网IP
   - 端口：22
   - 用户名：root
   - 密码：您的密码
   - 点击"登录"

### Mac/Linux系统

直接使用终端：

```bash
# 连接服务器
ssh root@你的服务器IP

# 文件传输使用scp命令
scp -r 本地文件夹 root@服务器IP:/目标路径
```

---

## 代码上传到服务器

### 方法一：使用Git（推荐）

#### 1. 在服务器上安装Git

```bash
# 连接到服务器后执行
apt-get update
apt-get install -y git
```

#### 2. 克隆代码

```bash
# 进入/opt目录
cd /opt

# 克隆代码（如果有Git仓库）
git clone 你的仓库地址 plant-disease-microservices

# 如果没有Git仓库，使用下面的方法二
```

### 方法二：直接上传文件

#### 1. 在本地打包代码

在Windows上：
1. 找到项目文件夹 `plant-disease-microservices`
2. 右键 → 发送到 → 压缩(zipped)文件夹
3. 得到 `plant-disease-microservices.zip`

#### 2. 上传到服务器

**使用WinSCP：**
1. 打开WinSCP并连接到服务器
2. 左侧：本地文件（找到zip文件）
3. 右侧：服务器文件（进入 `/opt` 目录）
4. 拖拽zip文件到右侧
5. 等待上传完成

**使用命令行：**
```bash
# 在本地电脑执行（Mac/Linux）
scp plant-disease-microservices.zip root@服务器IP:/opt/

# 或使用WinSCP的pscp（Windows）
pscp plant-disease-microservices.zip root@服务器IP:/opt/
```

#### 3. 在服务器上解压

```bash
# SSH连接到服务器后执行
cd /opt
unzip plant-disease-microservices.zip
# 如果没有unzip，先安装：apt-get install -y unzip
mv plant-disease-microservices-* plant-disease-microservices
```

---

## 服务器环境配置

### 步骤1：更新系统

```bash
# 连接到服务器后，执行以下命令
apt-get update
apt-get upgrade -y
```

### 步骤2：运行服务器准备脚本

```bash
# 进入项目目录
cd /opt/plant-disease-microservices

# 给脚本添加执行权限
chmod +x scripts/deploy_tencent_cloud.sh

# 运行服务器准备脚本
sudo ./scripts/deploy_tencent_cloud.sh
```

**脚本会自动完成：**
- ✅ 安装Docker
- ✅ 安装Docker Compose
- ✅ 配置防火墙
- ✅ 创建项目目录
- ✅ 安装GPU支持（如果检测到GPU）
- ✅ 优化系统参数

**执行时间：** 约5-10分钟

**如果遇到问题：**
- 确保使用root权限（`sudo`）
- 检查网络连接
- 查看错误信息并搜索解决方案

---

## 一键部署执行

### 步骤1：运行一键部署脚本

```bash
# 确保在项目根目录
cd /opt/plant-disease-microservices

# 给脚本添加执行权限
chmod +x scripts/one_click_deploy.sh

# 运行一键部署脚本
sudo ./scripts/one_click_deploy.sh
```

**脚本会自动完成：**
- ✅ 检查系统要求（Ubuntu版本、硬件配置）
- ✅ 安装Docker（如果未安装）
- ✅ 安装Docker Compose（支持 `docker-compose` 和 `docker compose` 命令）
- ✅ 创建部署目录 `/opt/plant-disease`
- ✅ 复制项目文件到部署目录
- ✅ 生成自签名SSL证书（用于HTTPS）
- ✅ 创建默认的环境变量文件 `.env`
- ✅ 生成随机JWT密钥（安全增强！）
- ✅ 创建Nginx配置文件
- ✅ 创建Redis配置文件
- ✅ 创建数据库初始化脚本
- ✅ 构建Docker镜像（所有服务）
- ✅ 启动所有服务
- ✅ 执行服务健康检查

**执行时间：** 约10-20分钟（取决于网络速度和服务器配置）

**脚本执行过程：**
- 脚本会显示彩色输出，绿色表示成功，黄色表示警告，红色表示错误
- 执行过程中会有详细的步骤说明
- 遇到问题时会显示错误信息和解决方案建议

### 步骤2：检查部署结果

脚本执行完成后，会显示部署结果和服务访问地址：

```
==========================================
部署完成！
==========================================

服务访问地址：
  - 前端应用: http://123.456.789.012
  - API文档: http://123.456.789.012:8000/docs
  - Grafana监控: http://123.456.789.012:3001 (admin/admin)
  - Prometheus: http://123.456.789.012:9090

常用命令：
  - 查看服务状态: cd /opt/plant-disease && docker-compose -f docker-compose.prod.yml ps
  - 查看日志: cd /opt/plant-disease && docker-compose -f docker-compose.prod.yml logs -f [service-name]
  - 重启服务: cd /opt/plant-disease && docker-compose -f docker-compose.prod.yml restart
  - 停止服务: cd /opt/plant-disease && docker-compose -f docker-compose.prod.yml down
  - 更新服务: cd /opt/plant-disease && git pull && docker-compose -f docker-compose.prod.yml up -d --build
```

### 步骤3：配置环境变量（可选）

一键部署脚本已经自动生成了合理的默认配置，包括随机生成的JWT密钥。如果需要自定义配置，可以编辑 `.env` 文件：

```bash
# 编辑环境变量文件
nano /opt/plant-disease/.env
```

**可以修改的配置项：**

```bash
# 数据库配置
POSTGRES_PASSWORD=PlantDisease2024!  # 已自动设置强密码

# JWT配置（已自动生成随机密钥）
JWT_SECRET_KEY=随机生成的32位密钥
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# 腾讯云COS配置（可选，如果使用对象存储）
COS_SECRET_ID=你的COS密钥ID
COS_SECRET_KEY=你的COS密钥
COS_REGION=ap-beijing
COS_BUCKET=你的存储桶名称

# 日志配置
LOG_LEVEL=DEBUG  # 开发环境建议使用DEBUG，生产环境建议使用INFO

# 开发/生产环境配置
DEBUG=True       # 开发环境设为True，生产环境设为False
ENVIRONMENT=development  # development或production
```

**编辑方法（nano编辑器）：**
- 使用方向键移动光标
- 修改完成后按 `Ctrl + O` 保存
- 按 `Enter` 确认
- 按 `Ctrl + X` 退出

**重启服务应用配置：**

```bash
cd /opt/plant-disease
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d
```

---

## 模型文件上传

### 步骤1：了解模型文件结构

项目中已经包含了完整的模型配置文件，位于 `models/` 目录下：

- **集成模型配置**：`ensemble_config.yaml`
- **蒸馏模型配置**：`distillation_config.yaml`
- **各模型推理配置**：
  - `convnext_l_inference.yaml`
  - `efficientnetv2_l_inference.yaml`
  - `vit_b_16_inference.yaml`
  - `student_model_inference.yaml`

**配置文件特点：**
- 包含 `model_type`、`input_size`、`mean`、`std`、`class_names` 等必要字段
- `class_names` 列表包含39种植物病害类别
- 集成模型配置包含3个预训练模型路径
- 蒸馏模型配置包含学生模型和教师模型路径

### 步骤2：准备模型文件

您需要准备以下模型文件：

| 模型类型 | 模型文件（必须） | 配置文件（已提供） |
|---------|----------------|------------------|
| ConvNeXt-L | `convnext_l_best.pth` | `convnext_l_inference.yaml` |
| EfficientNetV2-L | `efficientnetv2_l_best.pth` | `efficientnetv2_l_inference.yaml` |
| ViT-B-16 | `vit_b_16_best.pth` | `vit_b_16_inference.yaml` |
| 学生模型 | `student_model.pth` | `student_model_inference.yaml` |

**模型文件说明：**
- 格式：`.pt` 或 `.pth`（PyTorch模型）
- 大小：每个模型约50-100MB
- 来源：从训练过程或预训练模型库获取

### 步骤3：创建模型目录（已由脚本自动创建）

一键部署脚本已经自动创建了模型目录 `/opt/plant-disease/models/`，无需手动创建。

### 步骤4：上传模型文件

**使用WinSCP：**
1. 打开WinSCP连接服务器
2. 左侧：本地模型文件（`.pt` 或 `.pth`）
3. 右侧：进入 `/opt/plant-disease/models/` 目录
4. 拖拽所有模型文件到右侧

**使用命令行：**
```bash
# 在本地电脑执行
scp convnext_l_best.pth root@服务器IP:/opt/plant-disease/models/
scp vit_b_16_best.pth root@服务器IP:/opt/plant-disease/models/
scp efficientnetv2_l_best.pth root@服务器IP:/opt/plant-disease/models/
scp student_model.pth root@服务器IP:/opt/plant-disease/models/
```

### 步骤5：检查模型配置文件

确保所有配置文件都已正确上传：

```bash
# 查看模型目录内容
ls -la /opt/plant-disease/models/
```

**预期输出：**
```
-rw-r--r-- 1 root root  12345 Nov 10 12:00 convnext_l_best.pth
-rw-r--r-- 1 root root    234 Nov 10 12:00 convnext_l_inference.yaml
-rw-r--r-- 1 root root    567 Nov 10 12:00 distillation_config.yaml
-rw-r--r-- 1 root root  23456 Nov 10 12:00 efficientnetv2_l_best.pth
-rw-r--r-- 1 root root    234 Nov 10 12:00 efficientnetv2_l_inference.yaml
-rw-r--r-- 1 root root    789 Nov 10 12:00 ensemble_config.yaml
-rw-r--r-- 1 root root  34567 Nov 10 12:00 student_model.pth
-rw-r--r-- 1 root root    234 Nov 10 12:00 student_model_inference.yaml
-rw-r--r-- 1 root root  45678 Nov 10 12:00 vit_b_16_best.pth
-rw-r--r-- 1 root root    234 Nov 10 12:00 vit_b_16_inference.yaml
```

### 步骤6：配置模型路径（可选）

如果您的模型文件名与配置文件中指定的不一致，需要修改配置文件：

```bash
# 编辑集成模型配置
nano /opt/plant-disease/models/ensemble_config.yaml
```

**修改模型路径：**
```yaml
model_type: ensemble
model_paths:
  - models/convnext_l_best.pth      # 确保文件名与实际一致
  - models/vit_b_16_best.pth         # 确保文件名与实际一致
  - models/efficientnetv2_l_best.pth  # 确保文件名与实际一致
ensemble_strategy: weighted
weights: [0.33361408466010983, 0.3334238982774548, 0.3329620170624355]
input_size: [224, 224]
mean: [0.485, 0.456, 0.406]
std: [0.229, 0.224, 0.225]
num_classes: 39
class_names:
  - Apple___Apple_scab
  - Apple___Black_rot
  # ... 更多类别
```

### 步骤7：设置文件权限

```bash
chown -R root:root /opt/plant-disease/models
chmod -R 755 /opt/plant-disease/models
```

### 步骤8：重启模型服务

```bash
cd /opt/plant-disease
docker-compose -f docker-compose.prod.yml restart model-service
```

### 步骤9：验证模型加载

```bash
# 查看模型服务日志，确认模型已加载
docker-compose -f docker-compose.prod.yml logs model-service | grep "模型已加载"
```

**预期输出：**
```
模型已加载: ensemble (ensemble)
共加载 1 个模型
```

**或更详细的输出：**
```
检测到集成模型配置，包含 3 个模型
集成模型加载完成，共 3 个模型，策略: weighted
模型已加载: ensemble (ensemble)
共加载 1 个模型
```

---

## 服务启动与验证

### 步骤1：检查服务状态

```bash
cd /opt/plant-disease
docker-compose -f docker-compose.prod.yml ps
```

**正常情况下，所有服务都应该是 "Up" 状态：**
```
NAME                          STATUS     PORTS
plant-disease-api-gateway     Up         0.0.0.0:80->80/tcp, 0.0.0.0:443->443/tcp
plant-disease-model-service   Up         8003/tcp
plant-disease-task-service    Up         8002/tcp
plant-disease-cache-service   Up         8006/tcp
plant-disease-redis           Up         0.0.0.0:6379->6379/tcp
plant-disease-postgres        Up         0.0.0.0:5432->5432/tcp
plant-disease-frontend        Up         0.0.0.0:3000->3000/tcp
plant-disease-prometheus      Up         0.0.0.0:9090->9090/tcp
plant-disease-grafana         Up         0.0.0.0:3001->3000/tcp
```

**服务状态说明：**
- `Up`：服务正常运行
- `Exit`：服务启动失败（需要查看日志）
- `Restarting`：服务正在重启（可能是配置错误）
- `Created`：服务已创建但未启动

### 步骤2：查看服务日志

```bash
# 查看所有服务的最新日志（最后100行）
docker-compose -f docker-compose.prod.yml logs --tail=100

# 查看特定服务的完整日志
docker-compose -f docker-compose.prod.yml logs model-service

# 实时查看服务日志（常用！）
docker-compose -f docker-compose.prod.yml logs -f model-service

# 查看多个服务的日志
docker-compose -f docker-compose.prod.yml logs -f model-service task-service
```

**日志查看技巧：**
- 使用 `--tail=N` 限制显示的日志行数
- 使用 `-f` 参数实时跟踪日志（按 `Ctrl + C` 退出）
- 查找错误信息：`docker-compose logs model-service | grep -i error`
- 查找模型加载信息：`docker-compose logs model-service | grep -i "模型已加载\|加载模型"

### 步骤3：服务健康检查

```bash
# 检查API网关（核心入口）
curl -s http://localhost:8000/health/

# 检查模型服务（推理核心）
curl -s http://localhost:8003/health/

# 检查任务服务（异步任务处理）
curl -s http://localhost:8002/health/

# 检查缓存服务（Redis缓存）
curl -s http://localhost:8006/health/
```

**预期输出（健康状态）：**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00",
  "service": "model-service",
  "version": "1.0.0",
  "dependencies": {
    "models": "1 loaded",
    "redis": "connected"
  }
}
```

**常见问题：**
- `connection refused`：服务未启动或端口错误
- `timeout`：网络问题或服务内部错误
- `500 Internal Server Error`：服务内部错误，需要查看日志

### 步骤4：检查模型加载

```bash
# 方法1：查看模型服务日志
docker-compose -f docker-compose.prod.yml logs model-service | grep -i "模型已加载\|加载模型\|ensemble\|student"

# 方法2：使用API检查已加载的模型
curl -s http://localhost:8003/models/ | python3 -m json.tool
```

**预期输出（日志）：**
```
检测到集成模型配置，包含 3 个模型
集成模型加载成功
模型已加载: ensemble (ensemble)
共加载 1 个模型
```

**预期输出（API）：**
```json
{
  "models": [
    {
      "name": "ensemble",
      "file_path": "/app/models/ensemble_config.yaml",
      "file_size": 1234,
      "loaded_at": "2024-01-01T12:00:00",
      "status": "loaded",
      "model_type": "ensemble",
      "num_models": 3,
      "strategy": "weighted"
    }
  ],
  "total": 1
}
```

### 步骤5：测试API功能

#### 测试API文档访问

在浏览器中打开：
```
http://你的服务器IP:8000/docs
```

**你应该看到：**
- 完整的API文档页面
- 各种API端点的详细说明
- 可以直接在页面上测试API

#### 测试模型预测API

```bash
# 准备一张测试图片（确保图片存在）
# 测试直接预测API
curl -X POST -H "Content-Type: multipart/form-data" \
  -F "file=@test_image.jpg" \
  http://localhost:8003/predict/direct
```

### 步骤6：前端访问测试

```bash
# 检查前端服务是否运行
docker-compose -f docker-compose.prod.yml ps frontend

# 检查前端日志
docker-compose -f docker-compose.prod.yml logs -f frontend
```

在浏览器中访问：
```
http://你的服务器IP
```

**预期结果：**
- 看到植物病害检测系统的登录页面或主页
- 能够正常导航到检测页面
- 能够上传图片并进行检测

### 步骤7：综合测试

1. **打开前端页面**：`http://你的服务器IP`
2. **进入检测页面**：点击导航菜单中的 "检测" 或 "Detection"
3. **上传测试图片**：选择一张植物图片
4. **选择模型**：从下拉菜单中选择 "集成模型" 或 "学生模型"
5. **点击 "开始检测"**：等待检测结果
6. **查看检测结果**：应该显示植物类别、病害名称和置信度

**成功标准：**
- 图片上传成功
- 检测过程中没有报错
- 能够显示检测结果
- 结果包含植物和病害信息

### 常见问题及解决方案

| 问题 | 症状 | 解决方案 |
|-----|------|--------|
| 服务状态为 Exit | `docker-compose ps` 显示服务退出 | 查看日志：`docker-compose logs service-name` |
| 模型加载失败 | 日志显示 "加载模型失败" | 检查模型文件路径和权限 |
| API返回500错误 | curl命令返回500状态码 | 查看服务日志，检查配置和依赖 |
| 前端无法访问 | 浏览器显示 "无法访问此网站" | 检查防火墙规则，开放80端口 |
| 图片上传失败 | 前端显示 "上传失败" | 检查文件大小限制，查看日志 |

### 快速故障排除命令

```bash
# 检查Docker容器资源使用情况
docker stats

# 检查端口占用情况
netstat -tulpn | grep -E '80|443|8000|8002|8003|8006|3000'

# 检查磁盘空间
df -h

# 检查内存使用
free -h

# 重启所有服务
docker-compose -f docker-compose.prod.yml restart

# 强制重建并启动服务
docker-compose -f docker-compose.prod.yml up -d --build
```

## ESP32设备配置

### 步骤1：安装Arduino IDE

1. 访问 https://www.arduino.cc/en/software
2. 下载Arduino IDE（选择适合您系统的版本）
3. 安装Arduino IDE

### 步骤2：安装ESP32支持

1. 打开Arduino IDE
2. 进入 `文件` → `首选项`
3. 在"附加开发板管理器网址"中添加：
   ```
   https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
   ```
4. 点击"确定"
5. 进入 `工具` → `开发板` → `开发板管理器`
6. 搜索"esp32"
7. 找到"esp32 by Espressif Systems"，点击"安装"
8. 等待安装完成（可能需要几分钟）

### 步骤3：安装必要库

1. 进入 `工具` → `管理库`
2. 搜索并安装：
   - **ArduinoJson** (版本 6.x)
   - **ESP32 Camera**（通常已包含在ESP32支持包中）

### 步骤4：配置代码

1. 打开项目中的文件：
   ```
   edge-devices/esp32/plant_disease_detector.ino
   ```

2. 修改以下配置：

```cpp
// WiFi配置
const char* ssid = "你的WiFi名称";
const char* password = "你的WiFi密码";

// 云端API配置
const char* api_base_url = "http://你的服务器IP:8000/api";
const char* api_key = "";  // 如果有API密钥，填写这里
```

3. 根据您的硬件调整 `camera_pins.h` 中的引脚定义

### 步骤5：上传代码

1. 用USB线连接ESP32到电脑
2. 在Arduino IDE中：
   - `工具` → `开发板` → 选择您的ESP32型号（如：ESP32 Dev Module）
   - `工具` → `端口` → 选择ESP32的COM端口
3. 点击"上传"按钮（→）
4. 等待编译和上传完成

### 步骤6：查看结果

1. 打开串口监视器：
   - `工具` → `串口监视器`
   - 波特率设置为：115200
2. 应该看到：
   - WiFi连接信息
   - 图像采集信息
   - 预测结果

---

## 常见问题解决

### 问题1：无法SSH连接服务器

**症状：** 连接超时或拒绝连接

**解决方法：**
1. ✅ 检查服务器是否运行（在腾讯云控制台查看）
2. ✅ 检查安全组是否开放22端口（SSH）
3. ✅ 检查IP地址是否正确（复制完整的公网IP）
4. ✅ 检查登录密码是否正确（注意大小写）
5. ✅ 尝试重启服务器（在控制台操作）
6. ✅ 检查本地网络是否正常

### 问题2：Docker安装失败

**症状：** 执行部署脚本时Docker安装报错

**解决方法：**
```bash
# 方法1：手动安装Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
systemctl start docker
systemctl enable docker

# 验证安装
docker --version

# 方法2：使用apt安装（适用于Ubuntu）
apt-get update
apt-get install -y docker.io
systemctl start docker
systemctl enable docker
```

### 问题3：服务启动失败

**症状：** `docker-compose ps` 显示服务状态为 "Exit" 或 "Restarting"

**解决方法：**
```bash
# 1. 查看详细错误日志（关键！）
docker-compose -f docker-compose.prod.yml logs 服务名称

# 2. 常见原因和解决方法：

# 端口被占用
netstat -tulpn | grep :8000  # 检查8000端口

# 配置文件错误
cat /opt/plant-disease/.env  # 检查环境变量文件

# 磁盘空间不足
df -h  # 查看磁盘使用情况

# 内存不足
free -h  # 查看内存使用情况

# 权限问题
chown -R root:root /opt/plant-disease
chmod -R 755 /opt/plant-disease

# 依赖问题
cd /opt/plant-disease && docker-compose -f docker-compose.prod.yml up -d --build  # 重建服务
```

### 问题4：模型加载失败

**症状：** 模型服务日志显示"模型加载失败"或"无法找到模型"

**解决方法：**
```bash
# 1. 检查模型文件是否存在
ls -lh /opt/plant-disease/models/  # 应该看到所有.pth或.pt文件

# 2. 检查文件权限
chown -R root:root /opt/plant-disease/models
chmod -R 755 /opt/plant-disease/models

# 3. 检查配置文件内容
cat /opt/plant-disease/models/ensemble_config.yaml  # 检查模型路径是否正确

# 4. 查看完整错误日志
docker-compose -f docker-compose.prod.yml logs -f model-service

# 5. 常见配置错误：
# - 模型文件名与配置文件中不一致
# - 模型文件路径错误（配置中应为 models/xxx.pth）
# - 配置文件格式错误（YAML语法问题）
# - 模型文件损坏或不兼容
```

### 问题5：前端无法访问

**症状：** 浏览器显示"无法访问此网站"或"连接超时"

**解决方法：**
```bash
# 1. 检查服务状态
docker-compose -f docker-compose.prod.yml ps frontend

# 2. 检查前端日志
docker-compose -f docker-compose.prod.yml logs -f frontend

# 3. 检查防火墙规则（腾讯云控制台）
# - 开放端口：80（HTTP）、443（HTTPS）、3000（前端）

# 4. 检查Nginx配置
docker-compose -f docker-compose.prod.yml logs api-gateway

# 5. 尝试直接访问前端端口
# 在浏览器中打开：http://服务器IP:3000

# 6. 检查API网关状态
curl -s http://localhost:8000/health/
```

### 问题6：预测API返回错误

**症状：** 调用预测API时返回500错误或"模型未加载"

**解决方法：**
```bash
# 1. 检查模型服务状态
docker-compose -f docker-compose.prod.yml ps model-service

# 2. 检查模型是否正确加载
docker-compose -f docker-compose.prod.yml logs model-service | grep -i "模型已加载"

# 3. 检查模型列表API
curl -s http://localhost:8003/models/ | python3 -m json.tool

# 4. 检查Redis连接
docker-compose -f docker-compose.prod.yml logs redis

# 5. 重启模型服务
docker-compose -f docker-compose.prod.yml restart model-service

# 6. 查看详细错误
docker-compose -f docker-compose.prod.yml logs -f model-service
```

### 问题7：上传图片失败

**症状：** 前端上传图片时显示"上传失败"或"请求超时"

**解决方法：**
```bash
# 1. 检查文件大小限制
# 查看nginx.conf中的client_max_body_size配置

# 2. 检查网络连接
# 尝试更换浏览器或网络环境

# 3. 检查API网关日志
docker-compose -f docker-compose.prod.yml logs -f api-gateway

# 4. 检查模型服务日志
docker-compose -f docker-compose.prod.yml logs -f model-service

# 5. 尝试减小图片尺寸后重新上传
```

### 问题8：检测结果不准确

**症状：** 检测结果显示错误的植物或病害

**解决方法：**
1. ✅ 确保上传的图片清晰（分辨率至少224x224）
2. ✅ 确保图片只包含单一植物器官（叶片）
3. ✅ 选择合适的模型（集成模型准确率更高）
4. ✅ 检查模型是否正确加载
5. ✅ 尝试重新上传不同角度的图片
6. ✅ 检查模型训练数据是否包含该植物/病害

### 问题9：Docker Compose命令错误

**症状：** 提示 "docker-compose: command not found"

**解决方法：**
```bash
# 方法1：使用 docker compose 命令（新语法）
docker compose ps

# 方法2：安装 docker-compose
curl -L "https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# 验证
docker-compose --version
```

### 问题10：ESP32无法连接WiFi

**症状：** 串口监视器显示"WiFi连接失败"

**解决方法：**
1. ✅ 检查WiFi名称和密码是否正确（注意大小写和特殊字符）
2. ✅ 确保WiFi是2.4GHz（ESP32不支持5GHz）
3. ✅ 检查WiFi信号强度（建议距离路由器1-3米）
4. ✅ 检查ESP32的电源是否稳定（建议使用5V 2A电源）
5. ✅ 尝试重启ESP32设备
6. ✅ 检查代码中的引脚定义是否正确

### 问题11：ESP32无法连接服务器

**症状：** 串口监视器显示"HTTP请求失败"或"连接拒绝"

**解决方法：**
1. ✅ 检查服务器IP地址是否正确（使用公网IP）
2. ✅ 检查服务器端口是否开放（8000）
3. ✅ 检查API路径是否正确（应该是 `/predict/direct`）
4. ✅ 在浏览器中测试API是否可用
5. ✅ 检查ESP32的网络连接是否正常
6. ✅ 检查服务器防火墙规则

### 问题12：Nginx错误

**症状：** 浏览器显示"502 Bad Gateway"或"504 Gateway Timeout"

**解决方法：**
```bash
# 1. 检查Nginx日志
docker-compose -f docker-compose.prod.yml logs -f api-gateway

# 2. 检查后端服务是否正常
curl -s http://localhost:8000/health/

# 3. 检查Nginx配置
cat /opt/plant-disease/infrastructure/nginx/nginx.conf

# 4. 重启Nginx
docker-compose -f docker-compose.prod.yml restart api-gateway
```

### 问题13：数据库连接失败

**症状：** 服务日志显示"无法连接到数据库"

**解决方法：**
```bash
# 1. 检查PostgreSQL服务状态
docker-compose -f docker-compose.prod.yml ps postgres

# 2. 检查数据库日志
docker-compose -f docker-compose.prod.yml logs -f postgres

# 3. 检查环境变量配置
grep -i postgres /opt/plant-disease/.env

# 4. 检查数据库初始化脚本
cat /opt/plant-disease/infrastructure/postgres/init.sql

# 5. 尝试连接数据库
docker-compose -f docker-compose.prod.yml exec postgres psql -U postgres plant_disease
```

### 问题14：JWT认证错误

**症状：** API返回"无效的认证凭据"或"令牌过期"

**解决方法：**
1. ✅ 检查JWT密钥是否正确配置
2. ✅ 检查令牌是否过期（默认30分钟）
3. ✅ 检查认证头格式是否正确（Bearer 令牌）
4. ✅ 尝试重新登录获取新令牌
5. ✅ 检查JWT_ALGORITHM配置是否正确（HS256）

### 问题15：日志过多导致磁盘空间不足

**症状：** 服务运行一段时间后提示"磁盘空间不足"

**解决方法：**
```bash
# 1. 清理Docker日志
docker system prune -f

# 2. 清理旧日志文件
find /var/lib/docker/containers -name "*.log" -delete

# 3. 限制Docker日志大小
# 在 /etc/docker/daemon.json 中添加：
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}

# 重启Docker
systemctl restart docker
```

### 快速故障排除流程

1. **检查服务状态**：`docker-compose ps`
2. **查看错误日志**：`docker-compose logs 服务名称`
3. **检查资源使用**：`df -h && free -h`
4. **检查端口占用**：`netstat -tulpn`
5. **检查配置文件**：`cat /opt/plant-disease/.env`
6. **尝试重启服务**：`docker-compose restart`
7. **尝试重建服务**：`docker-compose up -d --build`
8. **检查健康状态**：`curl http://localhost:8000/health/`

**记住：错误日志是解决问题的关键！** 仔细阅读日志中的错误信息，通常能找到问题的根本原因。

---

## 日常维护

### 每日检查

```bash
# 1. 检查服务状态
cd /opt/plant-disease
docker-compose -f docker-compose.prod.yml ps

# 2. 检查磁盘空间
df -h

# 3. 检查内存使用
free -h

# 4. 查看错误日志
docker-compose -f docker-compose.prod.yml logs --tail=100
```

### 定期备份

```bash
# 备份数据库
docker-compose -f docker-compose.prod.yml exec postgres pg_dump -U postgres plant_disease > backup_$(date +%Y%m%d).sql

# 备份模型文件
tar -czf models_backup_$(date +%Y%m%d).tar.gz /opt/plant-disease/models/

# 备份配置文件
cp /opt/plant-disease/.env /opt/plant-disease/.env.backup
```

### 更新服务

```bash
# 1. 进入项目目录
cd /opt/plant-disease-microservices

# 2. 拉取最新代码（如果有Git）
git pull

# 3. 复制新文件
cp -r services /opt/plant-disease/
cp -r shared /opt/plant-disease/

# 4. 重新构建和启动
cd /opt/plant-disease
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml up -d
```

### 清理日志

```bash
# 清理Docker日志
docker system prune -f

# 清理旧日志文件
find /opt/plant-disease/logs -name "*.log" -mtime +7 -delete
```

---

## 快速命令参考

### 服务管理

```bash
# 启动所有服务
cd /opt/plant-disease
docker-compose -f docker-compose.prod.yml up -d

# 停止所有服务
docker-compose -f docker-compose.prod.yml down

# 重启所有服务
docker-compose -f docker-compose.prod.yml restart

# 重启特定服务
docker-compose -f docker-compose.prod.yml restart model-service

# 查看服务状态
docker-compose -f docker-compose.prod.yml ps

# 查看服务日志
docker-compose -f docker-compose.prod.yml logs -f 服务名称
```

### 模型管理

```bash
# 查看已加载的模型
curl http://localhost:8003/api/models/

# 查看模型信息
curl http://localhost:8003/api/models/模型名称

# 重启模型服务（重新加载模型）
docker-compose -f docker-compose.prod.yml restart model-service
```

### 数据库管理

```bash
# 连接数据库
docker-compose -f docker-compose.prod.yml exec postgres psql -U postgres -d plant_disease

# 备份数据库
docker-compose -f docker-compose.prod.yml exec postgres pg_dump -U postgres plant_disease > backup.sql

# 恢复数据库
docker-compose -f docker-compose.prod.yml exec -T postgres psql -U postgres plant_disease < backup.sql
```

### 系统监控

```bash
# 查看系统资源
htop

# 查看磁盘使用
df -h

# 查看内存使用
free -h

# 查看网络连接
netstat -tulpn

# 查看Docker资源使用
docker stats
```

---

## 部署检查清单

部署完成后，请逐项检查：

- [ ] 所有Docker服务正常运行
- [ ] 前端页面可以访问
- [ ] API文档可以访问（/docs）
- [ ] 模型服务健康检查通过
- [ ] 模型文件已上传并加载成功
- [ ] 可以成功上传图片进行检测
- [ ] 检测结果正常返回
- [ ] ESP32设备可以连接（如果使用）
- [ ] 防火墙规则已正确配置
- [ ] 环境变量已正确配置
- [ ] 数据库连接正常
- [ ] Redis连接正常

---

## 获取帮助

如果遇到问题：

1. **查看日志**：`docker-compose logs 服务名称`
2. **检查文档**：查看项目中的README文件
3. **搜索错误**：复制错误信息到搜索引擎
4. **检查配置**：确认所有配置文件正确

---

## 附录

### A. 常用端口说明

| 端口 | 服务 | 说明 |
|------|------|------|
| 80 | Nginx | HTTP访问 |
| 443 | Nginx | HTTPS访问 |
| 3000 | Frontend | 前端应用（开发模式） |
| 8000 | API Gateway | API网关 |
| 8002 | Task Service | 任务服务 |
| 8003 | Model Service | 模型服务 |
| 8006 | Cache Service | 缓存服务 |
| 5432 | PostgreSQL | 数据库 |
| 6379 | Redis | 缓存 |
| 9090 | Prometheus | 监控 |
| 3001 | Grafana | 监控面板 |

### B. 环境变量说明

完整的环境变量列表和说明请查看 `/opt/plant-disease/.env` 文件。

### C. 文件结构

```
/opt/plant-disease/
├── .env                    # 环境变量配置
├── docker-compose.prod.yml # Docker编排文件
├── models/                 # 模型文件目录
│   ├── model1.pt
│   ├── ensemble_config.yaml
│   └── ...
├── logs/                   # 日志目录
├── data/                   # 数据目录
└── infrastructure/         # 基础设施配置
    ├── nginx/
    ├── redis/
    └── postgres/
```

---

**祝您部署顺利！如有问题，请参考故障排除部分或查看日志文件。**

