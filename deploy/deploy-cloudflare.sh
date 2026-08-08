#!/bin/bash
# =============================================================
# Cloudflare Tunnel 一键部署脚本
# 部署 server.py 到 Cloudflare 免费公网
# =============================================================
# 使用方法：
#   1. 去 https://dash.cloudflare.com/ 登录，在 Zero Trust → Networks → Tunnels 创建一个隧道
#   2. 复制隧道 token（形如：eyJhIjoi...）
#   3. 执行：chmod +x deploy-cloudflare.sh && ./deploy-cloudflare.sh <YOUR_TOKEN>
# =============================================================

set -e

TUNNEL_TOKEN="$1"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

if [ -z "$TUNNEL_TOKEN" ]; then
    echo "❌ 请传入 Cloudflare Tunnel Token 作为参数"
    echo "用法: $0 <TUNNEL_TOKEN>"
    exit 1
fi

echo "=========================================="
echo "  VIIMK API + Cloudflare Tunnel 部署"
echo "=========================================="

# 1. 检查 Python 环境
echo ""
echo "[1/5] 检查 Python 环境..."
if ! command -v python3 &> /dev/null; then
    echo "❌ 未找到 python3，请先安装 Python 3.8+"
    exit 1
fi
echo "✅ Python 版本: $(python3 --version)"

# 2. 创建 venv 并安装依赖
echo ""
echo "[2/5] 创建虚拟环境并安装依赖..."
cd "$PROJECT_DIR"
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install -r requirements.txt -q
echo "✅ 依赖安装完成"

# 3. 创建 systemd 服务（Linux）
echo ""
echo "[3/5] 创建服务配置..."

# 创建启动脚本
cat > "$PROJECT_DIR/start-api.sh" << 'STARTSCRIPT'
#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
PORT=3001 python server.py
STARTSCRIPT
chmod +x "$PROJECT_DIR/start-api.sh"

# 创建 cloudflared 安装和启动脚本
cat > "$PROJECT_DIR/start-tunnel.sh" << TUNNELSCRIPT
#!/bin/bash
cd "$(dirname "$0")"
export TUNNEL_TOKEN="$TUNNEL_TOKEN"

# 如果没有 cloudflared 则自动下载
if ! command -v cloudflared &> /dev/null; then
    echo "正在下载 cloudflared..."
    if [ "$(uname -m)" = "x86_64" ]; then
        curl -L -o cloudflared https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64
    else
        curl -L -o cloudflared https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64
    fi
    chmod +x cloudflared
    export PATH="$(pwd):$PATH"
fi

# 启动 tunnel，将本地 3001 端口暴露到公网
cloudflared tunnel --no-autoupdate run --token "$TUNNEL_TOKEN" --url http://localhost:3001
TUNNELSCRIPT
chmod +x "$PROJECT_DIR/start-tunnel.sh"

echo "✅ 启动脚本已创建"

# 4. 输出下一步说明
echo ""
echo "=========================================="
echo "  🎉 配置文件已生成"
echo "=========================================="
echo ""
echo "📋 启动方式："
echo ""
echo "方式 A：两个终端分别运行"
echo "  终端 1: $PROJECT_DIR/start-api.sh"
echo "  终端 2: $PROJECT_DIR/start-tunnel.sh"
echo ""
echo "方式 B：使用 pm2（推荐，后台常驻运行）"
echo "  npm install -g pm2"
echo "  pm2 start $PROJECT_DIR/start-api.sh --name viimk-api"
echo "  pm2 start $PROJECT_DIR/start-tunnel.sh --name viimk-tunnel"
echo "  pm2 save"
echo ""
echo "🔗 获取公网域名："
echo "  去 https://dash.cloudflare.com/ → Zero Trust → Networks → Tunnels"
echo "  查看你的隧道 Public Hostname，就是 API 地址"
echo "  格式类似：https://你的子域名.trycloudflare.com"
echo ""
echo "🧪 测试接口："
echo "  curl https://你的域名/api/health"
echo "  curl https://你的域名/api/search?wd=庆余年"
echo ""
echo "=========================================="
