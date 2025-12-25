# 故障排除详细指南

## 🔍 问题诊断流程

遇到问题时，按以下步骤诊断：

1. **查看服务状态**
2. **查看错误日志**
3. **检查配置文件**
4. **检查网络连接**
5. **检查资源使用**

---

## 问题分类

### 1. 连接问题

#### 问题：无法SSH连接服务器

**诊断步骤：**

```bash
# 1. 检查服务器是否运行
# 在腾讯云控制台查看服务器状态

# 2. 检查安全组规则
# 在腾讯云控制台 → 安全组 → 入站规则
# 确认22端口已开放

# 3. 尝试ping服务器
ping 你的服务器IP

# 4. 检查SSH服务
# 如果可以通过控制台访问，执行：
systemctl status ssh
```

**解决方案：**

1. **安全组未开放22端口**
   - 进入腾讯云控制台
   - 安全组 → 入站规则 → 添加规则
   - 端口：22，协议：TCP，来源：0.0.0.0/0

2. **服务器未启动**
   - 在控制台启动服务器

3. **IP地址错误**
   - 确认使用的是公网IP，不是内网IP

---

#### 问题：无法访问前端页面

**诊断步骤：**

```bash
# 1. 检查服务是否运行
cd /opt/plant-disease
docker-compose -f docker-compose.prod.yml ps frontend

# 2. 检查端口是否开放
netstat -tulpn | grep :80

# 3. 检查防火墙
ufw status

# 4. 检查前端日志
docker-compose -f docker-compose.prod.yml logs frontend
```

**解决方案：**

1. **安全组未开放80端口**
   - 在腾讯云控制台开放80端口

2. **服务未启动**
   ```bash
   docker-compose -f docker-compose.prod.yml up -d frontend
   ```

3. **端口被占用**
   ```bash
   # 查找占用端口的进程
   lsof -i :80
   # 或
   fuser -k 80/tcp
   ```

---

### 2. Docker问题

#### 问题：Docker命令未找到

**症状：** `docker: command not found`

**解决方案：**

```bash
# 安装Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# 启动Docker服务
systemctl start docker
systemctl enable docker

# 验证安装
docker --version
```

---

#### 问题：Docker Compose命令未找到

**症状：** `docker-compose: command not found`

**解决方案：**

```bash
# 安装Docker Compose
DOCKER_COMPOSE_VERSION="2.24.0"
curl -L "https://github.com/docker/compose/releases/download/v${DOCKER_COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose
ln -sf /usr/local/bin/docker-compose /usr/bin/docker-compose

# 验证安装
docker-compose --version
```

---

#### 问题：服务启动失败

**诊断步骤：**

```bash
# 1. 查看服务状态
docker-compose -f docker-compose.prod.yml ps

# 2. 查看错误日志
docker-compose -f docker-compose.prod.yml logs 服务名称

# 3. 检查配置文件
cat /opt/plant-disease/.env

# 4. 检查端口占用
netstat -tulpn | grep :8000
```

**常见错误和解决：**

1. **端口已被占用**
   ```bash
   # 查找占用端口的进程
   lsof -i :8000
   # 停止占用端口的服务
   kill -9 PID
   ```

2. **配置文件错误**
   ```bash
   # 检查.env文件格式
   cat /opt/plant-disease/.env
   # 确保没有语法错误
   ```

3. **磁盘空间不足**
   ```bash
   # 检查磁盘空间
   df -h
   # 清理Docker未使用的资源
   docker system prune -a
   ```

4. **内存不足**
   ```bash
   # 检查内存使用
   free -h
   # 如果内存不足，考虑升级服务器配置
   ```

---

### 3. 模型服务问题

#### 问题：模型加载失败

**诊断步骤：**

```bash
# 1. 查看模型服务日志
docker-compose -f docker-compose.prod.yml logs model-service

# 2. 检查模型文件
ls -lh /opt/plant-disease/models/

# 3. 检查文件权限
ls -la /opt/plant-disease/models/

# 4. 检查配置文件
cat /opt/plant-disease/models/ensemble_config.yaml
```

**常见错误和解决：**

1. **模型文件不存在**
   ```bash
   # 确认文件路径正确
   ls -lh /opt/plant-disease/models/model1.pt
   ```

2. **文件权限问题**
   ```bash
   # 设置正确的权限
   chmod 644 /opt/plant-disease/models/*
   chown root:root /opt/plant-disease/models/*
   ```

3. **配置文件格式错误**
   ```bash
   # 检查YAML格式
   # 可以使用在线YAML验证器
   # 或使用Python验证
   python3 -c "import yaml; yaml.safe_load(open('ensemble_config.yaml'))"
   ```

4. **模型格式不支持**
   - 确认模型文件是 `.pt`, `.pth`, 或 `.onnx` 格式
   - 检查模型文件是否损坏

---

#### 问题：预测API返回错误

**诊断步骤：**

```bash
# 1. 测试API
curl -X POST "http://localhost:8000/api/predictions/direct" \
  -F "file=@test.jpg" \
  -F "model_name=default"

# 2. 查看模型服务日志
docker-compose -f docker-compose.prod.yml logs model-service --tail=50

# 3. 检查模型是否加载
curl http://localhost:8003/api/models/

# 4. 检查Redis连接
docker-compose -f docker-compose.prod.yml logs redis
```

**常见错误和解决：**

1. **模型未加载**
   ```bash
   # 重启模型服务
   docker-compose -f docker-compose.prod.yml restart model-service
   # 等待30秒后检查
   docker-compose -f docker-compose.prod.yml logs model-service | grep "模型已加载"
   ```

2. **图像格式不支持**
   - 确保上传的是常见图像格式（JPG, PNG等）
   - 检查图像文件是否损坏

3. **内存不足**
   ```bash
   # 检查内存使用
   docker stats model-service
   # 如果内存不足，考虑使用更小的模型或增加服务器内存
   ```

---

### 4. 数据库问题

#### 问题：数据库连接失败

**诊断步骤：**

```bash
# 1. 检查数据库服务
docker-compose -f docker-compose.prod.yml ps postgres

# 2. 查看数据库日志
docker-compose -f docker-compose.prod.yml logs postgres

# 3. 测试数据库连接
docker-compose -f docker-compose.prod.yml exec postgres psql -U postgres -d plant_disease -c "SELECT 1;"

# 4. 检查环境变量
grep DATABASE_URL /opt/plant-disease/.env
```

**解决方案：**

1. **数据库服务未启动**
   ```bash
   docker-compose -f docker-compose.prod.yml up -d postgres
   ```

2. **密码错误**
   ```bash
   # 检查.env文件中的密码
   # 确保与docker-compose.prod.yml中的一致
   ```

3. **数据库未初始化**
   ```bash
   # 检查初始化脚本
   ls -lh /opt/plant-disease/infrastructure/postgres/init.sql
   ```

---

### 5. Redis问题

#### 问题：Redis连接失败

**诊断步骤：**

```bash
# 1. 检查Redis服务
docker-compose -f docker-compose.prod.yml ps redis

# 2. 测试Redis连接
docker-compose -f docker-compose.prod.yml exec redis redis-cli ping
# 应该返回: PONG

# 3. 查看Redis日志
docker-compose -f docker-compose.prod.yml logs redis
```

**解决方案：**

1. **Redis服务未启动**
   ```bash
   docker-compose -f docker-compose.prod.yml up -d redis
   ```

2. **配置文件错误**
   ```bash
   # 检查Redis配置
   cat /opt/plant-disease/infrastructure/redis/redis.conf
   ```

---

### 6. 前端问题

#### 问题：前端页面空白或报错

**诊断步骤：**

```bash
# 1. 查看前端日志
docker-compose -f docker-compose.prod.yml logs frontend

# 2. 检查前端服务
docker-compose -f docker-compose.prod.yml ps frontend

# 3. 检查环境变量
docker-compose -f docker-compose.prod.yml exec frontend env | grep NEXT_PUBLIC
```

**解决方案：**

1. **API地址配置错误**
   ```bash
   # 检查环境变量
   # 在docker-compose.prod.yml中确认NEXT_PUBLIC_API_BASE_URL
   ```

2. **构建失败**
   ```bash
   # 重新构建前端
   cd /opt/plant-disease
   docker-compose -f docker-compose.prod.yml build frontend
   docker-compose -f docker-compose.prod.yml up -d frontend
   ```

---

### 7. ESP32问题

#### 问题：ESP32无法连接WiFi

**诊断：**
- 检查串口监视器输出
- 确认WiFi名称和密码正确
- 确认WiFi是2.4GHz（ESP32不支持5GHz）

**解决方案：**
1. 检查WiFi配置
2. 尝试重启ESP32
3. 检查WiFi信号强度

---

#### 问题：ESP32无法连接服务器

**诊断：**
- 检查服务器IP地址
- 检查端口是否开放
- 测试API是否可访问

**解决方案：**
1. 在浏览器中测试API：`http://服务器IP:8000/api/health/`
2. 检查防火墙规则
3. 确认API路径正确

---

## 🔧 常用修复命令

### 重启所有服务

```bash
cd /opt/plant-disease
docker-compose -f docker-compose.prod.yml restart
```

### 重新构建服务

```bash
cd /opt/plant-disease
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml up -d
```

### 清理并重启

```bash
cd /opt/plant-disease
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d --build
```

### 查看所有日志

```bash
cd /opt/plant-disease
docker-compose -f docker-compose.prod.yml logs --tail=100 -f
```

### 清理Docker资源

```bash
# 清理未使用的镜像、容器、网络
docker system prune -a

# 清理未使用的卷（谨慎使用）
docker volume prune
```

---

## 📞 获取更多帮助

如果以上方法都无法解决问题：

1. **收集错误信息**
   ```bash
   # 保存完整的错误日志
   docker-compose -f docker-compose.prod.yml logs > error_logs.txt
   ```

2. **检查系统资源**
   ```bash
   # CPU和内存
   htop
   # 磁盘空间
   df -h
   # 网络连接
   netstat -tulpn
   ```

3. **查看系统日志**
   ```bash
   # 系统日志
   journalctl -xe
   # Docker日志
   journalctl -u docker
   ```

4. **搜索解决方案**
   - 复制错误信息到搜索引擎
   - 查看Docker官方文档
   - 查看项目GitHub Issues

---

## ⚠️ 重要提示

1. **备份重要数据**：在进行任何修复操作前，确保已备份重要数据
2. **逐步测试**：修复后逐步测试，不要一次性修改太多
3. **记录操作**：记录所有修改操作，方便回滚
4. **查看日志**：遇到问题时，首先查看日志文件

---

**记住：大多数问题都可以通过查看日志找到原因！**

