#!/usr/bin/env bash
# ============================================================================
# VIIMK 后端一键部署脚本 (Ubuntu/Debian)
# ----------------------------------------------------------------------------
# 用法：
#   sudo bash deploy.sh
#
# 可选环境变量（部署前 export 覆盖）：
#   DOMAIN      绑定域名         （默认 api.example.com，必改）
#   ADMIN_EMAIL Let's Encrypt 通知邮箱（默认 admin@example.com，必改）
#   APP_PORT    gunicorn 监听端口（默认 3001）
#   WORKERS     gunicorn 进程数  （默认 4）
#   APP_DIR     部署目录          （默认 /opt/viimk-api）
#
# 部署完成后：
#   - server.py 由 systemd 托管（开机自启 + 崩溃自动重启）
#   - Nginx 反代 80/443 → APP_PORT，支持 HTTPS
#   - 防火墙仅放行 22/80/443
# ============================================================================
set -euo pipefail

# ---------------------------- 配置项 ----------------------------------------
DOMAIN="${DOMAIN:-api.example.com}"
ADMIN_EMAIL="${ADMIN_EMAIL:-admin@example.com}"
APP_PORT="${APP_PORT:-3001}"
WORKERS="${WORKERS:-4}"
APP_DIR="${APP_DIR:-/opt/viimk-api}"
SERVICE_NAME="viimk-api"
VENV_DIR="${APP_DIR}/.venv"

# 颜色输出
C_GREEN='\033[0;32m'
C_YELLOW='\033[1;33m'
C_RED='\033[0;31m'
C_RESET='\033[0m'
info()  { echo -e "${C_GREEN}[INFO]${C_RESET} $*"; }
warn()  { echo -e "${C_YELLOW}[WARN]${C_RESET} $*"; }
error() { echo -e "${C_RED}[ERROR]${C_RESET} $*" >&2; }
die()   { error "$*"; exit 1; }

# ---------------------------- 前置检查 --------------------------------------
[[ $EUID -eq 0 ]] || die "请用 root 或 sudo 执行：sudo bash deploy.sh"

if [[ "$DOMAIN" == "api.example.com" ]]; then
  warn "DOMAIN 仍为默认值 api.example.com，请改成你自己的域名后重试。"
  warn "  示例：sudo DOMAIN=api.yourdomain.com bash deploy.sh"
  exit 1
fi
if [[ "$ADMIN_EMAIL" == "admin@example.com" ]]; then
  warn "ADMIN_EMAIL 仍为默认值，请改成你的真实邮箱（Let's Encrypt 证书过期提醒）。"
  exit 1
fi

info "域名: $DOMAIN"
info "部署目录: $APP_DIR"
info "应用端口: $APP_PORT"
info "gunicorn 进程数: $WORKERS"

# ---------------------------- 1. 系统依赖 -----------------------------------
info "安装系统依赖 (Python / Nginx / certbot) ..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y --no-install-recommends \
  python3 python3-venv python3-pip \
  nginx \
  certbot python3-certbot-nginx \
  ufw curl ca-certificates
info "系统依赖安装完成"

# ---------------------------- 2. 应用目录 -----------------------------------
info "部署应用代码到 ${APP_DIR} ..."
mkdir -p "$APP_DIR"

# 脚本所在目录（用于定位 server.py 和 requirements.txt）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# 拷贝后端文件（server.py + requirements.txt）
cp -f "$PROJECT_ROOT/server.py"        "$APP_DIR/server.py"
cp -f "$PROJECT_ROOT/requirements.txt" "$APP_DIR/requirements.txt"
info "代码已同步到 $APP_DIR"

# ---------------------------- 3. Python venv --------------------------------
info "创建 Python 虚拟环境 ..."
if [[ ! -d "$VENV_DIR" ]]; then
  python3 -m venv "$VENV_DIR"
fi
# 升级 pip
"$VENV_DIR/bin/pip" install --upgrade pip wheel >/dev/null
# 安装业务依赖 + gunicorn（生产级 WSGI 服务器）
"$VENV_DIR/bin/pip" install --quiet \
  -r "$APP_DIR/requirements.txt" \
  gunicorn
info "Python 依赖安装完成"

# ---------------------------- 4. systemd 服务 -------------------------------
info "配置 systemd 服务 (${SERVICE_NAME}) ..."
cat > "/etc/systemd/system/${SERVICE_NAME}.service" <<EOF
[Unit]
Description=VIIMK API (Flask + gunicorn)
After=network.target

[Service]
Type=notify
User=root
WorkingDirectory=${APP_DIR}
EnvironmentFile=-${APP_DIR}/.env
ExecStart=${VENV_DIR}/bin/gunicorn \\
  --workers ${WORKERS} \\
  --bind 127.0.0.1:${APP_PORT} \\
  --timeout 60 \\
  --access-logfile - \\
  --error-logfile - \\
  server:app
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable "${SERVICE_NAME}" >/dev/null
systemctl restart "${SERVICE_NAME}"
info "systemd 服务已启动并设为开机自启"

# ---------------------------- 5. Nginx 反代 ---------------------------------
info "配置 Nginx 反向代理 ..."
NGINX_CONF="/etc/nginx/sites-available/${SERVICE_NAME}"
cat > "$NGINX_CONF" <<EOF
server {
    listen 80;
    listen [::]:80;
    server_name ${DOMAIN};

    # 健康检查
    location = /health {
        proxy_pass http://127.0.0.1:${APP_PORT}/api/health;
    }

    # 反代到 gunicorn
    location / {
        proxy_pass http://127.0.0.1:${APP_PORT};
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;

        # 流代理 (/api/stream) 可能长连接，给足超时
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
        proxy_buffering off;
    }

    client_max_body_size 20m;
}
EOF

ln -sf "$NGINX_CONF" "/etc/nginx/sites-enabled/${SERVICE_NAME}"
# 禁用默认站点避免冲突
[[ -f /etc/nginx/sites-enabled/default ]] && rm -f /etc/nginx/sites-enabled/default

nginx -t || die "Nginx 配置检查失败"
systemctl reload nginx
info "Nginx 已配置并 reload"

# ---------------------------- 6. HTTPS 证书 ---------------------------------
info "申请 Let's Encrypt HTTPS 证书 ..."
# --register-unsafely-without-email 已弃用，使用 -m 指定邮箱
if certbot --nginx -n --agree-tos -m "$ADMIN_EMAIL" -d "$DOMAIN" --redirect; then
  info "HTTPS 证书已签发并自动配置"
else
  warn "证书签发失败：请确认域名 $DOMAIN 已正确解析到本服务器公网 IP"
  warn "可稍后手动执行：certbot --nginx -d $DOMAIN"
fi

# ---------------------------- 7. 防火墙 -------------------------------------
info "配置 UFW 防火墙 ..."
ufw allow OpenSSH 2>/dev/null || true
ufw allow 'Nginx Full' 2>/dev/null || true
# 只放行 22/80/443，关闭 3001 外网访问（gunicorn 只绑 127.0.0.1）
yes | ufw enable 2>/dev/null || true
info "防火墙已启用（仅放行 22/80/443）"

# ---------------------------- 8. 健康检查 -----------------------------------
info "等待服务启动 ..."
sleep 3
if curl -sf "http://127.0.0.1:${APP_PORT}/api/health" >/dev/null; then
  info "本地健康检查通过"
else
  warn "本地健康检查失败，查看日志：journalctl -u ${SERVICE_NAME} -n 50"
fi

# ---------------------------- 完成 ------------------------------------------
PUBLIC_URL="https://${DOMAIN}"
echo
echo -e "${C_GREEN}========================================${C_RESET}"
echo -e "${C_GREEN}  部署完成！${C_RESET}"
echo -e "${C_GREEN}========================================${C_RESET}"
echo
echo "后端服务地址：$PUBLIC_URL"
echo "健康检查：    $PUBLIC_URL/health"
echo "搜索接口：    $PUBLIC_URL/api/search"
echo
echo "常用运维命令："
echo "  查看状态：  systemctl status ${SERVICE_NAME}"
echo "  查看日志：  journalctl -u ${SERVICE_NAME} -f"
echo "  重启服务：  systemctl restart ${SERVICE_NAME}"
echo "  更新代码：  拷贝新的 server.py 到 ${APP_DIR} 后执行 systemctl restart ${SERVICE_NAME}"
echo
echo -e "${C_YELLOW}前端配置提醒：${C_RESET}"
echo "  编辑 src/api/request.js，把 REMOTE_BASE 改为："
echo "    const REMOTE_BASE = '${PUBLIC_URL}'"
echo "  然后重新打包 APP 即可让 uni-app 直连此后端。"
echo
