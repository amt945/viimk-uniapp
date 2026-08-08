# VIIMK 后端 Dockerfile（最小仓库专用 - 本目录作为独立 viimk-api 仓库时使用）
# ============================================================================
# 对应 Render 部署的"方案 A：最小仓库推送" —— 代码位于仓库根。
# 如果你是"方案 B：整仓推送"（含前端 + backend/ 子目录），请用项目根的 ../Dockerfile。
#
# 本地测试（在本目录运行）：
#   docker build -t viimk-api .
#   docker run -p 3001:3001 -e PORT=3001 viimk-api
# ============================================================================
FROM python:3.11-slim

# 时区设为上海（日志时间一致）
ENV TZ=Asia/Shanghai \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    FLASK_ENV=production

# 系统依赖（ca-certificates 用于 https 请求 ffzy）
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl tzdata \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 先拷贝依赖文件，利用 Docker 层缓存
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip wheel \
    && pip install --no-cache-dir -r requirements.txt gunicorn

# 拷贝业务代码
COPY server.py .

# Render 默认注入 PORT 环境变量；本地测试用 3001
ENV PORT=3001
EXPOSE 3001

# 健康检查（可选）
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -sf http://127.0.0.1:${PORT}/api/health || exit 1

# gunicorn 启动（2 workers 适配免费版 512MB 内存）
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT} --workers 2 --timeout 60 --access-logfile - --error-logfile - server:app"]
