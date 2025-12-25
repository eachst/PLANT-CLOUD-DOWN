# 云服务部署指南

## 阿里云ECS部署

### 1. 准备工作

1. 注册阿里云账号并购买ECS实例
2. 选择合适的实例规格（推荐4核8GB以上）
3. 选择Ubuntu 20.04或CentOS 8操作系统
4. 配置安全组，开放以下端口：
   - 80 (HTTP)
   - 443 (HTTPS)
   - 22 (SSH)
   - 3000 (前端，可选)
   - 3001 (Grafana，可选)
   - 9090 (Prometheus，可选)

### 2. 环境配置

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# 安装Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.12.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 创建项目目录
sudo mkdir -p /opt/plant-disease
sudo chown $USER:$USER /opt/plant-disease
cd /opt/plant-disease
```

### 3. 部署应用

```bash
# 克隆项目代码
git clone <your-repo-url> .

# 配置环境变量
cp .env.example .env
nano .env  # 编辑配置文件

# 运行部署脚本
chmod +x deploy.sh
./deploy.sh
```

### 4. 配置域名和SSL

1. 在阿里云域名服务购买域名
2. 配置域名解析到ECS实例IP
3. 使用Let's Encrypt获取免费SSL证书：

```bash
# 安装Certbot
sudo apt install certbot python3-certbot-nginx

# 获取SSL证书
sudo certbot --nginx -d yourdomain.com

# 设置自动续期
sudo crontab -e
# 添加以下行
0 12 * * * /usr/bin/certbot renew --quiet
```

## 腾讯云CVM部署

### 1. 准备工作

1. 注册腾讯云账号并购买CVM实例
2. 选择合适的实例规格（推荐4核8GB以上）
3. 选择Ubuntu 20.04或CentOS 8操作系统
4. 配置安全组，开放必要端口（同阿里云）

### 2. 环境配置

```bash
# 更新系统
sudo yum update -y

# 安装Docker
sudo yum install -y yum-utils
sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
sudo yum install -y docker-ce docker-ce-cli containerd.io
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER

# 安装Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.12.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 创建项目目录
sudo mkdir -p /opt/plant-disease
sudo chown $USER:$USER /opt/plant-disease
cd /opt/plant-disease
```

### 3. 部署应用

```bash
# 克隆项目代码
git clone <your-repo-url> .

# 配置环境变量
cp .env.example .env
vi .env  # 编辑配置文件

# 运行部署脚本
chmod +x deploy.sh
./deploy.sh
```

### 4. 配置域名和SSL

1. 在腾讯云域名服务购买域名
2. 配置域名解析到CVM实例IP
3. 使用Let's Encrypt获取免费SSL证书：

```bash
# 安装Certbot
sudo yum install -y certbot python3-certbot-nginx

# 获取SSL证书
sudo certbot --nginx -d yourdomain.com

# 设置自动续期
echo "0 12 * * * /usr/bin/certbot renew --quiet" | sudo crontab -
```

## AWS EC2部署

### 1. 准备工作

1. 注册AWS账号并创建EC2实例
2. 选择合适的实例类型（推荐t3.large或更大）
3. 选择Ubuntu 20.04 AMI
4. 配置安全组，开放必要端口（同阿里云）

### 2. 环境配置

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# 安装Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.12.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 创建项目目录
sudo mkdir -p /opt/plant-disease
sudo chown $USER:$USER /opt/plant-disease
cd /opt/plant-disease
```

### 3. 部署应用

```bash
# 克隆项目代码
git clone <your-repo-url> .

# 配置环境变量
cp .env.example .env
nano .env  # 编辑配置文件

# 运行部署脚本
chmod +x deploy.sh
./deploy.sh
```

### 4. 配置域名和SSL

1. 在Route 53购买域名或使用已有域名
2. 配置域名解析到EC2实例EIP
3. 使用Let's Encrypt获取免费SSL证书：

```bash
# 安装Certbot
sudo apt install certbot python3-certbot-nginx

# 获取SSL证书
sudo certbot --nginx -d yourdomain.com

# 设置自动续期
sudo crontab -e
# 添加以下行
0 12 * * * /usr/bin/certbot renew --quiet
```

## 容器服务部署

### 阿里云容器服务ACK

1. 创建Kubernetes集群
2. 配置节点池和存储
3. 部署应用：

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: plant-disease-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: plant-disease
  template:
    metadata:
      labels:
        app: plant-disease
    spec:
      containers:
      - name: frontend
        image: your-registry/plant-disease-frontend:latest
        ports:
        - containerPort: 3000
      - name: api-gateway
        image: your-registry/plant-disease-api-gateway:latest
        ports:
        - containerPort: 80
---
apiVersion: v1
kind: Service
metadata:
  name: plant-disease-service
spec:
  selector:
    app: plant-disease
  ports:
    - name: http
      port: 80
      targetPort: 3000
  type: LoadBalancer
```

### 腾讯云容器服务TKE

1. 创建Kubernetes集群
2. 配置节点池和存储
3. 部署应用（同上）

## 对象存储配置

### 阿里云OSS

1. 创建OSS存储桶
2. 配置访问密钥
3. 更新环境变量：

```bash
# .env
OSS_ACCESS_KEY_ID=your-access-key-id
OSS_ACCESS_KEY_SECRET=your-access-key-secret
OSS_ENDPOINT=oss-cn-hangzhou.aliyuncs.com
OSS_BUCKET=your-bucket-name
```

### 腾讯云COS

1. 创建COS存储桶
2. 配置访问密钥
3. 更新环境变量：

```bash
# .env
COS_SECRET_ID=your-secret-id
COS_SECRET_KEY=your-secret-key
COS_REGION=ap-beijing
COS_BUCKET=your-bucket-name
```

### AWS S3

1. 创建S3存储桶
2. 配置访问密钥
3. 更新环境变量：

```bash
# .env
AWS_ACCESS_KEY_ID=your-access-key-id
AWS_SECRET_ACCESS_KEY=your-secret-access-key
AWS_REGION=us-west-2
AWS_BUCKET=your-bucket-name
```

## 监控和日志

### 阿里云监控

1. 配置云监控插件
2. 设置监控告警规则
3. 配置日志服务

### 腾讯云监控

1. 配置云监控插件
2. 设置监控告警规则
3. 配置日志服务

### AWS CloudWatch

1. 配置CloudWatch代理
2. 设置监控告警规则
3. 配置日志收集

## 备份策略

### 数据库备份

```bash
# 创建备份脚本
cat > backup.sh << 'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/opt/backups"
mkdir -p $BACKUP_DIR

# 备份PostgreSQL数据库
docker-compose exec postgres pg_dump -U postgres plant_disease > $BACKUP_DIR/plant_disease_$DATE.sql

# 备份Redis数据
docker-compose exec redis redis-cli BGSAVE
docker cp $(docker-compose ps -q redis):/data/dump.rdb $BACKUP_DIR/redis_$DATE.rdb

# 清理7天前的备份
find $BACKUP_DIR -name "*.sql" -mtime +7 -delete
find $BACKUP_DIR -name "*.rdb" -mtime +7 -delete
EOF

chmod +x backup.sh

# 添加到crontab，每天凌晨2点备份
echo "0 2 * * * /opt/plant-disease/backup.sh" | sudo crontab -
```

### 应用备份

```bash
# 创建应用备份脚本
cat > app-backup.sh << 'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/opt/backups"
mkdir -p $BACKUP_DIR

# 备份应用代码
tar -czf $BACKUP_DIR/app_$DATE.tar.gz --exclude='.git' --exclude='node_modules' --exclude='__pycache__' .

# 备份上传的文件
tar -czf $BACKUP_DIR/uploads_$DATE.tar.gz uploads/

# 清理30天前的备份
find $BACKUP_DIR -name "app_*.tar.gz" -mtime +30 -delete
find $BACKUP_DIR -name "uploads_*.tar.gz" -mtime +30 -delete
EOF

chmod +x app-backup.sh

# 添加到crontab，每周日凌晨3点备份
echo "0 3 * * 0 /opt/plant-disease/app-backup.sh" | sudo crontab -
```

## 扩容策略

### 水平扩展

```yaml
# docker-compose.scale.yml
version: '3.8'

services:
  user-service:
    deploy:
      replicas: 3
  
  task-service:
    deploy:
      replicas: 3
  
  model-service:
    deploy:
      replicas: 2
```

### 自动扩展

1. 配置云服务商的自动扩展组
2. 设置CPU和内存使用率阈值
3. 配置扩展策略

## 安全配置

### 防火墙配置

```bash
# Ubuntu UFW
sudo ufw enable
sudo ufw allow ssh
sudo ufw allow 80
sudo ufw allow 443
sudo ufw deny 5432  # 禁止外部访问数据库
sudo ufw deny 6379  # 禁止外部访问Redis

# CentOS firewalld
sudo firewall-cmd --permanent --add-service=ssh
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

### SSH安全配置

```bash
# 编辑SSH配置
sudo nano /etc/ssh/sshd_config

# 修改以下配置
Port 2222  # 更改默认端口
PermitRootLogin no  # 禁止root登录
PasswordAuthentication no  # 禁用密码认证，使用密钥认证
MaxAuthTries 3  # 限制尝试次数

# 重启SSH服务
sudo systemctl restart sshd
```

## 故障排除

### 常见问题

1. **容器无法启动**
   ```bash
   # 查看容器日志
   docker-compose logs [service-name]
   
   # 检查容器状态
   docker-compose ps
   ```

2. **数据库连接失败**
   ```bash
   # 检查数据库状态
   docker-compose exec postgres pg_isready
   
   # 检查网络连接
   docker-compose exec user-service ping postgres
   ```

3. **内存不足**
   ```bash
   # 检查系统资源
   free -h
   df -h
   
   # 清理Docker资源
   docker system prune -a
   ```

4. **SSL证书问题**
   ```bash
   # 检查证书有效期
   openssl x509 -in /etc/nginx/ssl/cert.pem -text -noout
   
   # 更新证书
   sudo certbot renew
   ```

### 性能优化

1. **数据库优化**
   ```sql
   -- 创建索引
   CREATE INDEX CONCURRENTLY idx_tasks_user_id ON tasks(user_id);
   
   -- 分析查询性能
   EXPLAIN ANALYZE SELECT * FROM tasks WHERE user_id = '...';
   ```

2. **Redis优化**
   ```bash
   # 监控Redis性能
   docker-compose exec redis redis-cli info memory
   
   # 优化内存使用
   echo "maxmemory 512mb" >> infrastructure/redis/redis.conf
   echo "maxmemory-policy allkeys-lru" >> infrastructure/redis/redis.conf
   ```

3. **Nginx优化**
   ```nginx
   # 添加到nginx.conf
   worker_processes auto;
   worker_connections 1024;
   
   # 启用gzip压缩
   gzip on;
   gzip_types text/plain text/css application/json application/javascript;
   
   # 配置缓存
   location ~* \.(jpg|jpeg|png|gif|ico|css|js)$ {
       expires 1y;
       add_header Cache-Control "public, immutable";
   }
   ```