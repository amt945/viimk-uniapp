#!/usr/bin/env bash
# ============================================================================
# VIIMK 后端 Cloudflare Tunnel 部署脚本
# ----------------------------------------------------------------------------
# 把本地（或任意常开机器）的 server.py 通过 Cloudflare Tunnel 暴露到公网，
# 自带 HTTPS + CDN + DDoS 防护，无需公网 IP、无需开放端口。
#
# 适用场景：
#   - 有一台常开的电脑 / 树莓派 / 旧手机 / 家庭服务器
#   - 不想买云服务器，想白嫖 Cloudflare
#
# 用法：
#   bash cloudflared-deploy.sh             # 交互式配置
#   bash cloudflared-deploy.sh --tunnel=mytunnel --domain=api.example.com
#
# 架构：
#   APP ──HTTPS──▶ Cloudflare 边缘 ──Tunnel──▶ 本机 cloudflared ──▶ 127.0.0.1:3001
# ============================================================================
set -euo pipefail

# ---------------------------- 默认配置 ----------------------------------------
APP_PORT="${APP_PORT:-3001}"
TUNNEL_NAME=""
DOMAIN=""
INSTALL_DIR="/usr/local/bin"
SYSTEMD_SERVICE="cloudflared-tunnel"
VIIMK_SERVICE="viimk-api"
APP_DIR="${APP_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"

# 颜色
C_GREEN='\033[0;32m'; C_YELLOW='\033[1;33m'; C_RED='\033[0;31m'; C_CYAN='\033[0;36m'; C_RESET='\033[0m'
info()  { echo -e "${C_GREEN}[INFO]${C_RESET} $*"; }
warn()  { echo -e "${C_YELLOW}[WARN]${C_RESET} $*"; }
error() { echo -e "${C_RED}[ERROR]${C_RESET} $*" >&2; }
die()   { error "$*"; exit 1; }
step()  { echo -e "\n${C_CYAN}▶ $*${C_RESET}"; }

# ---------------------------- 解析参数 ----------------------------------------
while [[ $# -gt 0 ]]; do
  case "$1" in
    --tunnel=*)  TUNNEL_NAME="${1#*=}"; shift ;;
    --domain=*)  DOMAIN="${1#*=}"; shift ;;
    --port=*)    APP_PORT="${1#*=}"; shift ;;
    --help|-h)
      sed -n '2,20p' "$0"; exit 0 ;;
    *) die "未知参数: $1 (用 --help 查看用法)" ;;
  esac
done

# ---------------------------- 前置检查 ----------------------------------------
step "环境检查"

OS="$(uname -s)"
ARCH="$(uname -m)"
case "$OS" in
  Linux*)  PLATFORM="linux";;
  Darwin*) PLATFORM="darwin";;
  *) die "不支持的系统: $OS (仅支持 Linux / macOS)" ;;
esac
case "$ARCH" in
  x86_64|amd64) ARCH="amd64";;
  aarch64|arm64) ARCH="arm64";;
  armv7l) ARCH="arm";;
  *) die "不支持的架构: $ARCH" ;;
esac
info "系统: $PLATFORM/$ARCH"

# 需要 root 权限安装 systemd 服务（macOS 用 launchd，不需要 root）
if [[ "$PLATFORM" == "linux" ]] && [[ $EUID -ne 0 ]]; then
  warn "建议用 sudo 执行以便安装 systemd 服务：sudo bash $0 $*"
  USE_SUDO=0
else
  USE_SUDO=1
fi

# ---------------------------- 1. 安装 cloudflared -----------------------------
step "安装 cloudflared"

install_cloudflared() {
  local version="latest"
  local url="https://github.com/cloudflare/cloudflared/releases/${version}/download/cloudflared-${PLATFORM}-${ARCH}"
  info "下载: $url"
  if [[ "$PLATFORM" == "linux" ]]; then
    sudo curl -sSL "$url" -o "$INSTALL_DIR/cloudflared"
    sudo chmod +x "$INSTALL_DIR/cloudflared"
  else
    # macOS 优先用 brew
    if command -v brew >/dev/null 2>&1; then
      brew install cloudflared
    else
      curl -sSL "$url" -o /usr/local/bin/cloudflared
      chmod +x /usr/local/bin/cloudflared
    fi
  fi
}

if command -v cloudflared >/dev/null 2>&1; then
  info "cloudflared 已安装: $(cloudflared --version 2>&1 | head -1)"
else
  install_cloudflared
  command -v cloudflared >/dev/null 2>&1 || die "cloudflared 安装失败，请手动安装：https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/get-started/"
  info "cloudflared 安装完成: $(cloudflared --version 2>&1 | head -1)"
fi

# ---------------------------- 2. 登录 Cloudflare -----------------------------
step "登录 Cloudflare 账号"

CLOUDFLARED_CONFIG_DIR="${HOME}/.cloudflared"
mkdir -p "$CLOUDFLARED_CONFIG_DIR"

if [[ -f "$CLOUDFLARED_CONFIG_DIR/cert.pem" ]]; then
  info "已检测到 cert.pem，跳过登录"
else
  warn "需要在浏览器中授权 cloudflared 访问你的 Cloudflare 账号"
  warn "执行后会打开浏览器，登录并选择要绑定的域名所在的 zone"
  echo
  read -rp "按回车继续，或 Ctrl+C 取消..." _
  cloudflared tunnel login
  [[ -f "$CLOUDFLARED_CONFIG_DIR/cert.pem" ]] || die "登录失败：未找到 cert.pem"
  info "登录成功"
fi

# ---------------------------- 3. 创建 Tunnel ---------------------------------
step "创建 / 复用 Tunnel"

# 交互式获取 tunnel 名
if [[ -z "$TUNNEL_NAME" ]]; then
  echo "已有的 tunnel 列表："
  cloudflared tunnel list 2>/dev/null || true
  echo
  read -rp "请输入 tunnel 名称（回车默认 viimk-api）: " TUNNEL_NAME
  TUNNEL_NAME="${TUNNEL_NAME:-viimk-api}"
fi

TUNNEL_ID=""
# 检查 tunnel 是否已存在
EXISTING=$(cloudflared tunnel list 2>/dev/null | awk -v name="$TUNNEL_NAME" '$2==name {print $1; exit}')
if [[ -n "$EXISTING" ]]; then
  TUNNEL_ID="$EXISTING"
  info "复用已有 tunnel: $TUNNEL_NAME (id=$TUNNEL_ID)"
else
  cloudflared tunnel create "$TUNNEL_NAME"
  # create 命令会输出 "Created tunnel <id> with credentials file ..."
  TUNNEL_ID=$(cloudflared tunnel list 2>/dev/null | awk -v name="$TUNNEL_NAME" '$2==name {print $1; exit}')
  [[ -n "$TUNNEL_ID" ]] || die "tunnel 创建失败"
  info "tunnel 已创建: $TUNNEL_NAME (id=$TUNNEL_ID)"
fi

CRED_FILE="$CLOUDFLARED_CONFIG_DIR/${TUNNEL_ID}.json"
[[ -f "$CRED_FILE" ]] || die "未找到 tunnel 凭证文件: $CRED_FILE"

# ---------------------------- 4. 配置域名 ------------------------------------
step "配置域名路由"

# 获取 zone 里已有的域名列表供用户选择
AVAILABLE_DOMAINS=$(cloudflared tunnel route dns --help 2>&1 || true)

if [[ -z "$DOMAIN" ]]; then
  echo
  echo "请在 Cloudflare 托管的域名中选一个子域名作为 API 地址"
  echo "例如：api.yourdomain.com（你的域名必须已添加到 Cloudflare）"
  echo
  read -rp "请输入 API 域名（如 api.example.com）: " DOMAIN
  [[ -n "$DOMAIN" ]] || die "必须提供域名"
fi

# 创建 DNS 记录（CNAME 到 tunnel）
info "为 $DOMAIN 创建 CNAME 到 tunnel ..."
if cloudflared tunnel route dns "$TUNNEL_NAME" "$DOMAIN" 2>&1 | tee /tmp/cf-dns.log; then
  info "DNS 记录已创建"
else
  # 已存在不算错
  if grep -qiE "record already exists|An A, AAAA, or CNAME record with that host already exists" /tmp/cf-dns.log; then
    info "DNS 记录已存在，跳过"
  else
    warn "DNS 记录创建失败，请确认 $DOMAIN 在你的 Cloudflare 账号下"
    warn "可稍后手动执行：cloudflared tunnel route dns $TUNNEL_NAME $DOMAIN"
  fi
fi

# ---------------------------- 5. 生成 config.yml -----------------------------
step "生成 cloudflared 配置文件"

CONFIG_FILE="$CLOUDFLARED_CONFIG_DIR/config.yml"
cat > "$CONFIG_FILE" <<EOF
# Cloudflare Tunnel 配置 - 由 cloudflared-deploy.sh 生成
tunnel: ${TUNNEL_ID}
credentials-file: ${CRED_FILE}

# 入口规则：${DOMAIN} → 本机 server.py
ingress:
  - hostname: ${DOMAIN}
    service: http://127.0.0.1:${APP_PORT}
    originRequest:
      # 流媒体可能长连接，给足超时
      connectTimeout: 30s
      noTLSVerify: false
      http2Origin: false
  # 兜底：返回 404
  - service: http_status:404
EOF
info "配置文件: $CONFIG_FILE"

# ---------------------------- 6. 启动 server.py ------------------------------
step "配置 server.py 后台运行"

# 确认 venv 存在
if [[ ! -d "$APP_DIR/.venv" ]]; then
  info "在 $APP_DIR 创建 venv ..."
  python3 -m venv "$APP_DIR/.venv"
fi
"$APP_DIR/.venv/bin/pip" install --quiet -r "$APP_DIR/requirements.txt" gunicorn
info "Python 依赖已就绪"

# 优先用 gunicorn（生产级），fallback 到 flask 自带
GUNICORN_BIN="$APP_DIR/.venv/bin/gunicorn"
if [[ -x "$GUNICORN_BIN" ]]; then
  START_CMD="$GUNICORN_BIN --workers 4 --bind 127.0.0.1:${APP_PORT} --timeout 60 server:app"
else
  START_CMD="$APP_DIR/.venv/bin/python server.py"
fi
info "启动命令: $START_CMD"

if [[ "$PLATFORM" == "linux" ]]; then
  # systemd 托管 server.py
  cat > /tmp/${VIIMK_SERVICE}.service <<EOF
[Unit]
Description=VIIMK API (Flask)
After=network.target

[Service]
Type=simple
WorkingDirectory=${APP_DIR}
ExecStart=${START_CMD}
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF
  if [[ $USE_SUDO -eq 1 ]]; then
    install -m 644 /tmp/${VIIMK_SERVICE}.service /etc/systemd/system/
    systemctl daemon-reload
    systemctl enable "${VIIMK_SERVICE}" >/dev/null 2>&1 || true
    systemctl restart "${VIIMK_SERVICE}"
    info "server.py 已用 systemd 托管（${VIIMK_SERVICE}）"
  else
    warn "未用 sudo，server.py 未装 systemd 服务，请手动后台运行："
    warn "  cd $APP_DIR && $START_CMD"
  fi
else
  # macOS：用 nohup 简单后台跑
  pkill -f "server:app" 2>/dev/null || true
  cd "$APP_DIR" && nohup $START_CMD > "$APP_DIR/.python.log" 2>&1 &
  info "server.py 已后台运行 (pid=$!), 日志: $APP_DIR/.python.log"
  cd - >/dev/null
fi

# ---------------------------- 7. 启动 cloudflared ----------------------------
step "配置 cloudflared 守护进程"

if [[ "$PLATFORM" == "linux" ]]; then
  # systemd 托管 cloudflared
  CF_BIN=$(command -v cloudflared)
  cat > /tmp/${SYSTEMD_SERVICE}.service <<EOF
[Unit]
Description=Cloudflare Tunnel (${TUNNEL_NAME})
After=network-online.target ${VIIMK_SERVICE}.service
Wants=network-online.target

[Service]
Type=notify
ExecStart=${CF_BIN} tunnel --config ${CONFIG_FILE} run
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
  if [[ $USE_SUDO -eq 1 ]]; then
    install -m 644 /tmp/${SYSTEMD_SERVICE}.service /etc/systemd/system/
    systemctl daemon-reload
    systemctl enable "${SYSTEMD_SERVICE}" >/dev/null 2>&1 || true
    systemctl restart "${SYSTEMD_SERVICE}"
    info "cloudflared 已用 systemd 托管（${SYSTEMD_SERVICE}）"
  else
    warn "未用 sudo，cloudflared 未装 systemd 服务，请手动后台运行："
    warn "  cloudflared tunnel --config $CONFIG_FILE run"
  fi
else
  # macOS：launchd 守护
  PLIST_FILE="$HOME/Library/LaunchAgents/com.cloudflare.${TUNNEL_NAME}.plist"
  CF_BIN=$(command -v cloudflared)
  cat > "$PLIST_FILE" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.cloudflare.${TUNNEL_NAME}</string>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>ProgramArguments</key>
  <array>
    <string>${CF_BIN}</string>
    <string>tunnel</string>
    <string>--config</string>
    <string>${CONFIG_FILE}</string>
    <string>run</string>
  </array>
  <key>StandardOutPath</key><string>${APP_DIR}/.cloudflared.log</string>
  <key>StandardErrorPath</key><string>${APP_DIR}/.cloudflared.log</string>
</dict>
</plist>
EOF
  launchctl unload "$PLIST_FILE" 2>/dev/null || true
  launchctl load "$PLIST_FILE"
  info "cloudflared 已用 launchd 守护"
fi

# ---------------------------- 8. 健康检查 ------------------------------------
step "健康检查"

info "等待服务启动 ..."
sleep 5

# 本地检查
if curl -sf "http://127.0.0.1:${APP_PORT}/api/health" >/dev/null 2>&1; then
  info "本地 server.py 健康检查通过"
else
  warn "本地健康检查失败，检查日志："
  [[ "$PLATFORM" == "linux" ]] && warn "  journalctl -u ${VIIMK_SERVICE} -n 30"
  [[ "$PLATFORM" == "darwin" ]] && warn "  tail -50 $APP_DIR/.python.log"
fi

# 公网检查（通过 tunnel）
sleep 3
info "测试公网访问 https://${DOMAIN} ..."
if curl -sf --max-time 15 "https://${DOMAIN}/api/health" >/dev/null 2>&1; then
  info "公网健康检查通过 ✓"
else
  warn "公网访问失败，可能 DNS 还未生效（通常 1-5 分钟）"
  warn "稍后手动测试：curl https://${DOMAIN}/api/health"
  [[ "$PLATFORM" == "linux" ]] && warn "  日志：journalctl -u ${SYSTEMD_SERVICE} -n 30"
fi

# ---------------------------- 完成 --------------------------------------------
PUBLIC_URL="https://${DOMAIN}"
echo
echo -e "${C_GREEN}========================================${C_RESET}"
echo -e "${C_GREEN}  Cloudflare Tunnel 部署完成！${C_RESET}"
echo -e "${C_GREEN}========================================${C_RESET}"
echo
echo "Tunnel 名称：  $TUNNEL_NAME"
echo "Tunnel ID：    $TUNNEL_ID"
echo "本地端口：     127.0.0.1:${APP_PORT}"
echo "公网地址：     $PUBLIC_URL"
echo
echo "配置文件：     $CONFIG_FILE"
echo
echo "常用运维命令："
if [[ "$PLATFORM" == "linux" ]]; then
  echo "  查看后端日志：   journalctl -u ${VIIMK_SERVICE} -f"
  echo "  查看隧道日志：   journalctl -u ${SYSTEMD_SERVICE} -f"
  echo "  重启后端：       systemctl restart ${VIIMK_SERVICE}"
  echo "  重启隧道：       systemctl restart ${SYSTEMD_SERVICE}"
else
  echo "  后端日志：       tail -f $APP_DIR/.python.log"
  echo "  隧道日志：       tail -f $APP_DIR/.cloudflared.log"
  echo "  重启隧道：       launchctl unload $PLIST_FILE && launchctl load $PLIST_FILE"
fi
echo "  查看 tunnel：    cloudflared tunnel list"
echo "  快速删除 tunnel: cloudflared tunnel delete $TUNNEL_NAME"
echo
echo -e "${C_YELLOW}前端配置提醒：${C_RESET}"
echo "  编辑 src/api/request.js，把 REMOTE_BASE 改为："
echo "    const REMOTE_BASE = '${PUBLIC_URL}'"
echo "  然后重新打包 APP。"
echo
echo -e "${C_YELLOW}注意事项：${C_RESET}"
echo "  1. 本机必须保持开机 + 联网，关机后 API 不可用"
echo "  2. 首次 DNS 生效需 1-5 分钟，公网访问失败时稍等"
echo "  3. 如需停服：systemctl stop ${SYSTEMD_SERVICE} ${VIIMK_SERVICE}"
echo
