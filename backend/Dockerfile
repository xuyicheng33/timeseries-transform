# 时序预测平台 - 后端 Dockerfile
# 使用 Python 3.11 官方镜像

FROM docker.m.daocloud.io/library/python:3.11-slim

# 使用阿里云 Debian 镜像源加速（国内服务器）
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 创建非 root 用户（安全最佳实践）
RUN groupadd --gid 1000 appgroup && \
    useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖（使用阿里云 PyPI 镜像加速）
RUN pip install --no-cache-dir -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/

# 复制应用代码
COPY --chown=appuser:appgroup . .

# 创建数据和上传目录，并设置权限
RUN mkdir -p data uploads/datasets uploads/results uploads/cache && \
    chown -R appuser:appgroup data uploads

# 切换到非 root 用户
USER appuser

# 暴露端口
EXPOSE 8000

# 启动命令
# 先运行数据库迁移，再启动服务
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]

