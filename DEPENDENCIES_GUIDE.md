# 植物病害检测系统 - 依赖指南

## 1. 系统级依赖

| 依赖项 | 版本要求 | 用途 | 安装命令 | 检查命令 |
|--------|----------|------|----------|----------|
| Docker | 20.10+ | 容器化运行环境 | `sudo apt-get install docker-ce` | `docker --version` |
| Docker Compose | 2.0+ | 多容器编排工具 | `sudo apt-get install docker-compose-plugin` | `docker compose version` |
| Git | 2.20+ | 版本控制 | `sudo apt-get install git` | `git --version` |
| Node.js | 18.17.0+ | 前端开发环境 | `curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash - && sudo apt-get install -y nodejs` | `node --version` |
| NPM | 9.6.7+ | Node.js包管理工具 | 随Node.js安装 | `npm --version` |
| OpenSSL | 1.1+ | 生成SSL证书和密钥 | 系统自带 | `openssl version` |
| Curl | 7.68+ | HTTP请求工具 | 系统自带 | `curl --version` |
| Python | 3.9+ | 后端开发环境（仅开发） | `sudo apt-get install python3.9 python3-pip` | `python3 --version` |

## 2. 后端服务依赖

### 2.1 统一Python依赖

所有Python服务共享的核心依赖：

| 依赖项 | 版本 | 用途 |
|--------|------|------|
| fastapi | 0.105.0 | API框架 |
| uvicorn | 0.24.0 | ASGI服务器 |
| sqlalchemy | 2.0.23 | ORM框架 |
| pydantic | 2.5.0 | 数据验证 |
| redis | 5.0.1 | 缓存和任务队列 |
| requests | 2.31.0 | HTTP客户端 |
| python-jose | 3.3.0 | JWT认证 |
| passlib | 1.7.4 | 密码哈希 |
| python-dotenv | 1.0.0 | 环境变量管理 |

### 2.2 各服务专用依赖

#### API Gateway (api-gateway/requirements.txt)
```
fastapi==0.105.0
uvicorn[standard]==0.24.0
pydantic==2.5.0
pydantic-settings==2.1.0
sqlalchemy==2.0.23
asyncpg==0.29.0
alembic==1.13.1
redis==5.0.1
celery==5.3.4
requests==2.31.0
httpx==0.25.2
python-multipart==0.0.6
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
pydantic-extra-types==2.5.0
email-validator==2.1.0
python-dotenv==1.0.0
```

#### 模型服务 (model-service/requirements.txt)
```
fastapi==0.105.0
uvicorn[standard]==0.24.0
pydantic==2.5.0
pydantic-settings==2.1.0
python-dotenv==1.0.0
requests==2.31.0
redis==5.0.1

# 图像处理
opencv-python==4.8.1.78
Pillow==10.1.0
scikit-image==0.22.0

# 深度学习
torch==2.1.1
torchvision==0.16.1
numpy==1.26.4
pandas==2.1.4
onnxruntime==1.16.3

# 腾讯云COS
boto3==1.34.0
```

#### 任务服务 (task-service/requirements.txt)
```
fastapi==0.105.0
uvicorn[standard]==0.24.0
pydantic==2.5.0
pydantic-settings==2.1.0
sqlalchemy==2.0.23
asyncpg==0.29.0
redis==5.0.1
celery==5.3.4
python-dotenv==1.0.0
requests==2.31.0
```

#### 缓存服务 (cache-service/requirements.txt)
```
fastapi==0.105.0
uvicorn[standard]==0.24.0
pydantic==2.5.0
pydantic-settings==2.1.0
redis==5.0.1
python-dotenv==1.0.0
```

#### 用户服务 (user-service/requirements.txt)
```
fastapi==0.105.0
uvicorn[standard]==0.24.0
pydantic==2.5.0
pydantic-settings==2.1.0
sqlalchemy==2.0.23
asyncpg==0.29.0
alembic==1.13.1
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-dotenv==1.0.0
```

## 3. 前端依赖

前端基于Next.js + React + TypeScript开发，依赖项在`frontend/package.json`中定义：

### 3.1 核心依赖

| 依赖项 | 版本 | 用途 |
|--------|------|------|
| next | ^16.0.8 | React框架 |
| react | ^19.2.1 | UI库 |
| react-dom | ^19.2.1 | React DOM渲染 |
| axios | ^1.13.2 | HTTP客户端 |
| antd | ^6.1.0 | UI组件库 |
| @ant-design/icons | ^6.1.0 | 图标库 |
| zustand | ^5.0.9 | 状态管理 |
| @tanstack/react-query | ^5.60.5 | 数据获取 |
| react-router-dom | ^7.10.1 | 路由管理 |
| recharts | ^3.5.1 | 图表库 |

### 3.2 开发依赖

| 依赖项 | 版本 | 用途 |
|--------|------|------|
| typescript | ^5.7.2 | 类型系统 |
| eslint | ^9.14.0 | 代码检查 |
| tailwindcss | ^3.4.14 | CSS框架 |
| postcss | ^8.4.49 | CSS处理 |
| autoprefixer | ^10.4.20 | CSS浏览器前缀 |

## 4. 边缘设备依赖

### ESP32设备

| 依赖项 | 版本 | 用途 | 安装方式 |
|--------|------|------|----------|
| Arduino IDE | 2.0+ | 开发环境 | [官网下载](https://www.arduino.cc/en/software) |
| ESP32 Arduino Core | 2.0+ | ESP32支持 | Arduino IDE开发板管理器 |
| ArduinoJson | 6.x | JSON处理 | Arduino IDE库管理器 |
| ESP32 Camera | 2.0+ | 摄像头支持 | Arduino IDE库管理器 |

## 5. 部署脚本依赖

### 一键部署脚本 (`scripts/one_click_deploy.sh`)

| 依赖项 | 用途 | 检查方式 |
|--------|------|----------|
| Bash | 脚本执行环境 | 系统自带 |
| Systemd | 服务管理 | `systemctl --version` |
| NetworkManager | 网络管理 | `nmcli --version` |
| Nslookup | DNS解析 | `nslookup --version` |

## 6. 依赖安装指南

### 6.1 服务器依赖安装

#### Ubuntu 20.04/22.04

```bash
# 更新apt源
sudo apt-get update
sudo apt-get upgrade -y

# 安装基础工具
sudo apt-get install -y curl wget git openssl net-tools

# 安装Docker
sudo apt-get install -y apt-transport-https ca-certificates curl gnupg-agent software-properties-common
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# 启动Docker服务
sudo systemctl start docker
sudo systemctl enable docker

# 安装Python开发环境（仅开发）
sudo apt-get install -y python3.9 python3.9-dev python3-pip python3-venv
```

#### CentOS/RHEL 8+

```bash
# 更新yum源
sudo yum update -y

# 安装基础工具
sudo yum install -y curl wget git openssl net-tools

# 安装Docker
sudo yum install -y yum-utils
sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
sudo yum install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# 启动Docker服务
sudo systemctl start docker
sudo systemctl enable docker
```

### 6.2 本地开发依赖安装

#### 后端服务

```bash
# 进入服务目录
cd services/api-gateway

# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

#### 前端服务

**Node.js版本要求：** 18.17.0+（Next.js 16.x官方要求）

```bash
# 检查Node.js版本
node --version  # 应显示 18.17.0 或更高版本
npm --version  # 应显示 9.6.7 或更高版本

# 进入前端目录
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

## 7. 依赖管理最佳实践

### 7.1 后端依赖

1. **使用虚拟环境**：每个服务使用独立的虚拟环境，避免依赖冲突
2. **固定版本**：在requirements.txt中指定精确版本，确保部署一致性
3. **定期更新**：使用`pip-audit`或`safety`检查安全漏洞
4. **依赖锁定**：使用`pip freeze > requirements.txt`生成精确依赖树

### 7.2 前端依赖

1. **使用npm ci**：部署时使用`npm ci`代替`npm install`，确保依赖一致性
2. **固定版本**：在package.json中使用精确版本号，或使用npm-shrinkwrap.json锁定依赖
3. **定期更新**：使用`npm audit`检查安全漏洞
4. **依赖分析**：使用`npm list`或`npm ls`查看依赖树

## 8. 依赖检查工具

### 8.1 Python依赖检查

```bash
# 安装依赖检查工具
pip install pip-audit safety

# 检查安全漏洞
pip-audit -r requirements.txt
safety check -r requirements.txt

# 查看依赖树
pipdeptree -r requirements.txt

# 检查未使用的依赖
pip-autoremove -r requirements.txt
```

### 8.2 前端依赖检查

```bash
# 检查安全漏洞
npm audit

# 查看依赖树
npm list

# 检查未使用的依赖
npm install -g depcheck
depcheck
```

## 9. 常见依赖问题排查

### 9.1 Docker相关

- **问题**：Docker命令需要sudo权限
  **解决**：将用户添加到docker组
  ```bash
  sudo usermod -aG docker $USER
  newgrp docker
  ```

- **问题**：Docker拉取镜像慢
  **解决**：配置国内镜像源
  ```bash
  sudo mkdir -p /etc/docker
  sudo tee /etc/docker/daemon.json <<-'EOF'
  {
    "registry-mirrors": ["https://mirror.ccs.tencentyun.com"]
  }
  EOF
  sudo systemctl daemon-reload
  sudo systemctl restart docker
  ```

### 9.2 Python依赖相关

- **问题**：pip安装依赖超时
  **解决**：使用国内镜像源
  ```bash
  pip install -i https://mirrors.tencent.com/pypi/simple/ --trusted-host mirrors.tencent.com -r requirements.txt
  ```

- **问题**：依赖版本冲突
  **解决**：使用虚拟环境隔离，或指定兼容版本

### 9.3 前端依赖相关

- **问题**：npm install失败
  **解决**：清理缓存并重新安装
  ```bash
  npm cache clean --force
  rm -rf node_modules package-lock.json
  npm install
  ```

- **问题**：Next.js编译失败
  **解决**：检查Node.js版本，确保使用支持的版本
  ```bash
  node --version  # 应 >= 18.17.0
  ```

- **问题**：Node.js版本不兼容
  **解决**：升级Node.js到18.17.0+版本
  ```bash
  # Ubuntu/Debian
  curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
  sudo apt-get install -y nodejs
  
  # CentOS/RHEL
  curl -fsSL https://rpm.nodesource.com/setup_18.x | sudo -E bash -
  sudo yum install -y nodejs
  
  # 使用nvm管理多个Node.js版本
  nvm install 18.17.0
  nvm use 18.17.0
  ```

## 10. 一键部署依赖说明

使用`scripts/one_click_deploy.sh`脚本部署时，会自动检查并安装以下依赖：

1. **Docker**：如果未安装，会自动从腾讯云镜像源或Ubuntu默认源安装
2. **Docker Compose**：如果未安装，会自动安装
3. **系统工具**：会检查并使用系统自带的工具
4. **SSL证书**：会自动生成自签名SSL证书
5. **配置文件**：会自动创建所需的配置文件

## 11. 依赖更新日志

| 日期 | 版本 | 更新内容 |
|------|------|----------|
| 2025-12-10 | v1.0 | 初始版本 |
| 2025-12-14 | v1.1 | 更新Docker Compose版本要求，添加依赖检查工具 |
| 2025-12-14 | v1.2 | 添加Node.js 18.17.0+版本要求，更新前端开发指南 |

## 12. 联系方式

如有依赖相关问题，请联系：
- 项目邮箱：your-email@example.com
- GitHub Issues：[项目Issues链接](https://github.com/your-repo/issues)

---

本指南详细列出了植物病害检测系统部署和开发所需的所有依赖，确保您在各种环境下都能顺利安装和运行系统。