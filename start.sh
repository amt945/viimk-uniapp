#!/usr/bin/env bash
# VIIMK 一键启动脚本（Linux / macOS）
# 功能：启动 venv 内的 Flask 后端 + uniapp Vite 前端，Ctrl+C 时一并关闭
set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# 1) 确保 venv 存在并装好了依赖
if [ ! -d ".venv" ] || [ ! -x ".venv/bin/python" ]; then
  echo "[viimk] 首次启动，创建 Python venv..."
  python3 -m venv .venv
fi
if ! ./.venv/bin/pip show flask requests >/dev/null 2>&1; then
  echo "[viimk] 安装 Python 依赖（flask/requests）..."
  ./.venv/bin/pip install -q -r requirements.txt
fi

# 2) 端口可配置（环境变量覆盖）
PY_PORT="${PY_PORT:-3001}"

# 3) 清理可能残留的占用进程
if command -v fuser >/dev/null 2>&1; then
  fuser -k "${PY_PORT}/tcp" 2>/dev/null || true
fi

# 4) 后台启动 Flask 后端
PY_LOG=".python.log"
echo "[viimk] 启动 Python 后端 (port=$PY_PORT)，日志：$PY_LOG"
./.venv/bin/python server.py >"$PY_LOG" 2>&1 &
PY_PID=$!
echo "        pid=$PY_PID"

# 5) 等待后端就绪（最多 15s）
for _ in $(seq 1 30); do
  if curl -sf "http://127.0.0.1:${PY_PORT}/api/health" >/dev/null 2>&1; then
    echo "[viimk] Python 后端就绪 ✓"
    break
  fi
  sleep 0.5
done

# 6) 启动前端（uniapp Vite）—— 前台运行，Ctrl+C 时 trap 清理
echo "[viimk] 启动前端 Vite dev server (h5)"
cleanup() {
  echo ""
  echo "[viimk] 关闭后端 pid=$PY_PID"
  kill "$PY_PID" 2>/dev/null || true
  wait "$PY_PID" 2>/dev/null || true
  if command -v fuser >/dev/null 2>&1; then
    fuser -k "${PY_PORT}/tcp" 2>/dev/null || true
  fi
  echo "[viimk] 退出。"
}
trap cleanup EXIT INT TERM

export PY_PORT
TARGET="${1:-h5}"
case "$TARGET" in
  h5|mp-weixin|app)
    npm run "dev:$TARGET"
    ;;
  *)
    echo "用法: $0 [h5|mp-weixin|app]"
    exit 1
    ;;
esac
