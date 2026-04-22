# 「破」Docker 部署配置
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsm6 \
    libxext6 \
    libgl1-mesa-glx \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 可选依赖（用于高级功能）
RUN pip install --no-cache-dir \
    playwright \
    gtts \
    Pillow \
    pytesseract \
    openai-whisper

# 安装 Playwright 浏览器
RUN playwright install chromium --with-deps

# 复制应用代码
COPY . .

# 创建数据目录
RUN mkdir -p data logs

# 环境变量
ENV PYTHONPATH=/app
ENV DATA_DIR=/app/data
ENV LOG_LEVEL=INFO

# 端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# 默认命令
CMD ["python", "main.py"]
