#!/usr/bin/env bash
# ============================================================================
# VIIMK API 防睡眠保活脚本
# ----------------------------------------------------------------------------
# Render 免费版 15 分钟无访问会睡眠，首次唤醒需 30-50 秒。
# 本脚本每 10 分钟 ping 一次 /api/health，保持服务常驻。
#
# 部署位置：任意一台常开的机器（你的电脑 / 树莓派 / 另一台服务器）
#
# 用法：
#   1. 修改 RENDER_URL 为你的 Render 服务地址
#   2. 手动测试：bash keepalive.sh
#   3. 安装为 cron 任务（每 10 分钟执行一次）：
#        crontab -e
#        添加：*/10 * * * * /path/to/keepalive.sh >> /var/log/viimk-keepalive.log 2>&1
# ============================================================================
set -euo pipefail

# ========= 改成你的 Render 服务地址 =========
RENDER_URL="${RENDER_URL:-https://viimk-api.onrender.com}"
# ============================================

HEALTH_URL="${RENDER_URL}/api/health"

# 时间戳
ts() { date '+%Y-%m-%d %H:%M:%S'; }

# ping 健康检查
if curl -sf --max-time 60 "$HEALTH_URL" >/dev/null 2>&1; then
  echo "[$(ts)] OK  - $RENDER_URL 在线"
else
  # 失败时再重试一次（可能正好在唤醒中）
  sleep 15
  if curl -sf --max-time 60 "$HEALTH_URL" >/dev/null 2>&1; then
    echo "[$(ts)] OK  - $RENDER_URL 唤醒成功（第二次尝试）"
  else
    echo "[$(ts)] FAIL- $RENDER_URL 不可达" >&2
    exit 1
  fi
fi
