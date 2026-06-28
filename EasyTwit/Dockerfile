FROM python:3.12-slim

WORKDIR /app

# 系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 应用代码
COPY src/ ./src/
COPY config.yaml .

# 运行时目录
RUN mkdir -p /app/data /app/data/images /app/logs

ENV PYTHONUNBUFFERED=1

# 默认启动定时调度
CMD ["python", "-m", "src", "run"]
