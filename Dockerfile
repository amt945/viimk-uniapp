# Hugging Face / Railway Docker 部署用
FROM python:3.9-slim

WORKDIR /app

# 拷贝文件
COPY server.py requirements.txt ./

# 安装依赖
RUN pip install --no-cache-dir -r requirements.txt

# 暴露端口
EXPOSE 7860

# 启动命令（Hugging Face 约定端口 7860）
CMD ["sh", "-c", "PORT=${PORT:-7860} python server.py"]
