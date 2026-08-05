# VIIMK 后端部署指南

> 最小仓库：这个目录已经包含部署后端所需的全部文件，可单独作为 GitHub 仓库推送（`viimk-api`）。
> 不想拆仓库？看下方"方案 B：整仓推送"。

## 一、文件清单

| 文件 | 作用 | 必需？ |
|------|------|--------|
| `server.py` | Flask 后端（采集接口 + 流代理 + 版本升级） | ✅ 必需 |
| `requirements.txt` | Python 依赖 | ✅ 必需 |
| `render.yaml` | Render Blueprint 配置（新加坡节点，免费版） | Render 用才需要 |
| `Dockerfile` | Docker 部署（Render 可选 / 其他平台通用） | Docker 部署才需要 |
| `deploy/probe-sources.py` | 采集源探测脚本（定期检查可用性） | ⭐ 推荐 |
| `deploy/cloudflared-deploy.sh` | Cloudflare Tunnel 部署脚本（家庭服务器/树莓派） | Cloudflare 用 |
| `deploy/deploy.sh` | 普通云服务器部署脚本（systemd + gunicorn） | 云服务器用 |
| `deploy/keepalive.sh` | Render 防睡眠保活脚本（每 10 分钟 ping 一次） | Render 免费版用 |

## 二、方案 A：最小仓库（推荐，推这个目录即可）

### 2.1 准备仓库

```bash
# 方法 1：直接把这个目录拷贝为独立仓库
mkdir viimk-api && cp -r viimk-uniapp/backend/* viimk-api/
cd viimk-api
git init && git add . && git commit -m "feat: init viimk-api backend"
git remote add origin https://github.com/你的用户名/viimk-api.git
git push -u origin main

# 方法 2：在现有仓库里只推送 backend/ 目录（git subtree）
cd viimk-uniapp
git subtree push --prefix=backend origin main
# 如果 target 仓库和当前 origin 不同：
git subtree split --prefix=backend -b backend-split
git push https://github.com/你的用户名/viimk-api.git backend-split:main
```

### 2.2 Render 部署（最快，免费版 + Blueprint 全自动）

1. 登录 [Render](https://dashboard.render.com) → **New +** → **Blueprint**
2. 连接 GitHub 仓库 `viimk-api`
3. Render 自动读取仓库根目录 `render.yaml`，创建 `viimk-api` 服务（自动配：新加坡节点 / Python 3.11 / gunicorn / health check）
4. 等待 2-3 分钟构建完成 → 得到 `https://viimk-api.onrender.com`

手动创建（不用 Blueprint）：

| 字段 | 值 |
|------|----|
| Runtime | Python 3 |
| Build Command | `pip install -r requirements.txt && pip install gunicorn` |
| Start Command | `gunicorn --bind 0.0.0.0:$PORT --workers 2 --timeout 60 server:app` |
| Health Check Path | `/api/health` |
| Plan | Free |
| Region | Singapore（离国内最近） |

### 2.3 验证部署

```bash
# 健康检查
curl https://viimk-api.onrender.com/api/health
# → {"code":0,"msg":"ok","sites":["ffzy","wuj","lzi","bdz","ffzy2"]}

# 搜索
curl "https://viimk-api.onrender.com/api/search?wd=庆余年" | head -c 200

# 版本检查（可选：需配置蓝奏云文件夹）
curl https://viimk-api.onrender.com/api/version
```

### 2.4 防睡眠（Render 免费版 15 分钟无访问会睡眠）

**推荐：UptimeRobot（零代码）**
1. 注册 https://uptimerobot.com
2. Add New Monitor → Type: **HTTP(s)** → URL: `https://viimk-api.onrender.com/api/health`
3. Interval: **10 分钟** → 保存

**或用脚本 + cron（需常开机器）：**
```bash
cp deploy/keepalive.sh /usr/local/bin/viimk-keepalive.sh
chmod +x /usr/local/bin/viimk-keepalive.sh
# 把脚本里的 RENDER_URL 改成你的地址
crontab -e
# 添加：
*/10 * * * * /usr/local/bin/viimk-keepalive.sh >> /var/log/viimk-keepalive.log 2>&1
```

### 2.5 采集源健康检查（可选）

```bash
python3 deploy/probe-sources.py
# → 并发生探测 5 个+采集源，输出搜索/详情/直链可用性
```

## 三、方案 B：整仓推送（不拆目录，图省事）

### 3.1 推送整个项目

```bash
cd viimk-uniapp
# 注意：node_modules/.venv/__pycache__ 已被 .gitignore 排除，不用手动处理
git add . && git commit -m "feat: init project"
git remote add origin https://github.com/你的用户名/viimk-uniapp.git
git push -u origin main
```

### 3.2 Render 创建服务

| 字段 | 值 |
|------|----|
| Runtime | Python 3 |
| **Root Directory** | `backend`（重要！让 Render 只看 backend/ 目录） |
| Build Command | `pip install -r requirements.txt && pip install gunicorn` |
| Start Command | `gunicorn --bind 0.0.0.0:$PORT --workers 2 --timeout 60 server:app` |
| Health Check Path | `/api/health` |

> Root Directory 填 `backend`，否则 Render 在根目录找不到 `requirements.txt` 会构建失败。

## 四、其他部署方式

### 4.1 Docker（Render 可选 / Koyeb / Fly.io / 云服务器通用）

```bash
docker build -t viimk-api .
docker run -p 3001:3001 -e PORT=3001 viimk-api
```

Render 新建 Web Service → Runtime 选 **Docker**，Render 会自动用这个目录的 Dockerfile 构建。

### 4.2 Cloudflare Tunnel（家庭服务器 / 树莓派，免费 + 国内延迟低）

```bash
# 交互式
bash deploy/cloudflared-deploy.sh

# 非交互式（准备好 Cloudflare Access 令牌）
bash deploy/cloudflared-deploy.sh --tunnel=viimk --domain=api.example.com
```

### 4.3 普通云服务器（systemd + gunicorn）

```bash
bash deploy/deploy.sh
# 自动：装 venv + 配置 systemd + 开机自启 + 健康检查
```

## 五、前端连接

把 viimk-uniapp 前端 `src/api/request.js` 第 51 行：

```javascript
const REMOTE_BASE = 'https://viimk-api.onrender.com'
```

保存后用 HBuilderX 打包 APP，App/小程序就会直连你部署的后端。

## 六、常见问题

| 问题 | 解决 |
|------|------|
| Render 首次访问 502 | 等 1-2 分钟；或 Logs 标签看报错 |
| 搜索慢 / 超时 | Render 免费版在国外，到国内采集站有延迟。改用 Cloudflare Tunnel（国内机器）或云服务器 |
| 版本升级接口直链解析失败 | 蓝奏云单文件分享页有 arg1 JS 混淆，程序自动回退到"单文件分享链接"，App 端打开浏览器下载即可，不影响功能 |
| 采集源挂了 | 跑 `deploy/probe-sources.py` 找可用源，替换进 `server.py` 的 `SITES` 配置，`git push` 后 Render 自动重部署 |
| 想升级付费版 | Render 控制台 Settings → Change Plan → Starter（$7/月，永不睡眠 + 1GB 内存） |
