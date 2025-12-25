FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# 配置腾讯云apt源，根据基础镜像自动适应Debian版本
RUN \
    # 获取当前Debian版本的codename
    DEBIAN_CODENAME=$(cat /etc/os-release | grep VERSION_CODENAME | cut -d= -f2) && \
    # 检查并创建sources.list文件（如果不存在）
    if [ ! -f /etc/apt/sources.list ]; then \
        echo "# Debian $DEBIAN_CODENAME sources" > /etc/apt/sources.list; \
        echo "deb http://deb.debian.org/debian $DEBIAN_CODENAME main contrib non-free" >> /etc/apt/sources.list; \
        echo "deb http://deb.debian.org/debian $DEBIAN_CODENAME-updates main contrib non-free" >> /etc/apt/sources.list; \
        echo "deb http://security.debian.org/debian-security $DEBIAN_CODENAME-security main contrib non-free" >> /etc/apt/sources.list; \
    fi && \
    # 备份原有源文件
    cp /etc/apt/sources.list /etc/apt/sources.list.backup && \
    # 只替换源地址，保留原有格式和版本
    sed -i 's|http://deb.debian.org/debian|http://mirrors.tencentyun.com/debian|g' /etc/apt/sources.list && \
    sed -i 's|http://security.debian.org/debian-security|http://mirrors.tencentyun.com/debian-security|g' /etc/apt/sources.list && \
    # 删除可能存在的其他源文件
    rm -rf /etc/apt/sources.list.d/* && \
    # 更新源并安装依赖
    apt-get update -o Acquire::http::proxy=false && apt-get install -y \
    gcc \
    g++ \
    curl \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖，使用腾讯云pip源加速下载
RUN pip install --no-cache-dir -i https://mirrors.tencent.com/pypi/simple/ --trusted-host mirrors.tencent.com --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -i https://mirrors.tencent.com/pypi/simple/ --trusted-host mirrors.tencent.com -r requirements.txt

# 复制应用代码
COPY . .

# 创建日志目录
RUN mkdir -p /app/logs

# 设置权限
RUN chmod +x entrypoint.sh

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1

# 启动命令
CMD ["./entrypoint.sh"]