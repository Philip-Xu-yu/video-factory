FROM python:3.12-slim

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    ffmpeg \
    fonts-wqy-yahei \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 复制代码
COPY . .

# 创建必要目录
RUN mkdir -p uploads output data bgm static

EXPOSE 8000

# 启动
CMD ["python", "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
