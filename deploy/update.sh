#!/usr/bin/env bash
# ============================================================================
# VIIMK 后端代码更新脚本（不重装系统依赖，仅更新代码 + 重启）
# ----------------------------------------------------------------------------
# 用法：
#   bash update.sh
#
# 前提：已用 deploy.sh 完成首次部署
# ============================================================================
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/viimk-api}"
SERVICE_NAME="viimk-api"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "[INFO] 同步 server.py → ${APP_DIR}"
cp -f "$PROJECT_ROOT/server.py"        "$APP_DIR/server.py"
cp -f "$PROJECT_ROOT/requirements.txt" "$APP_DIR/requirements.txt"

# 如果依赖有变化，同步安装
if [[ -d "${APP_DIR}/.venv" ]]; then
  echo "[INFO] 同步 Python 依赖 ..."
  "${APP_DIR}/.venv/bin/pip" install --quiet -r "$APP_DIR/requirements.txt"
fi

echo "[INFO] 重启服务 ${SERVICE_NAME} ..."
systemctl restart "$SERVICE_NAME"
sleep 2

if systemctl is-active --quiet "$SERVICE_NAME"; then
  echo "[OK] 服务已重启并运行中"
else
  echo "[ERROR] 服务启动失败，查看日志：journalctl -u ${SERVICE_NAME} -n 50"
  exit 1
fi
