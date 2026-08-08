# VIIMK 后端 Render 部署指南

> **不用推整个项目！**后端代码已整理到 `backend/` 目录，支持两种推送方案：
> - **方案 A（推荐，仓库干净）**：只推 `backend/` 目录到独立的 `viimk-api` 仓库
> - **方案 B（图省事）**：整个 `viimk-uniapp` 项目推，Render 自动读 `render.yaml` 里 `rootDir: backend` 只部署后端

## 一、前置准备

1. **GitHub 账号**
2. **Render 账号**（https://render.com，免费注册，无需信用卡）
3. **（可选）UptimeRobot 账号**（https://uptimerobot.com，免费防睡眠）

---

## 二、方案 A：最小仓库（推荐）

### 2.1 把 backend/ 单独推 GitHub

```bash
# 方法 1：拷贝成独立目录（最简单）
mkdir ~/viimk-api
cp -r viimk-uniapp/backend/* ~/viimk-api/
cd ~/viimk-api
git init
git add .
git commit -m "feat: init viimk-api backend"
git remote add origin https://github.com/你的用户名/viimk-api.git
git push -u origin main

# 方法 2：git subtree（不拆目录，直接从现有仓库推送 backend 子目录）
cd viimk-uniapp
# 第一次：先 split 出 backend 分支
git subtree split --prefix=backend -b backend-split
# 推到 target 仓库 viimk-api 的 main 分支
git push https://github.com/你的用户名/viimk-api.git backend-split:main
# 以后更新后端代码后，只需：
git subtree split --prefix=backend -b backend-split
git push https://github.com/你的用户名/viimk-api.git backend-split:main
```

### 2.2 Render 一键部署

1. 登录 [Render Dashboard](https://dashboard.render.com) → **New +** → **Blueprint**
2. 连接 GitHub 仓库 `viimk-api`
3. Render 自动读取仓库根目录的 `render.yaml`（最小仓库版本）
4. 等待构建 2-3 分钟 → 得到 `https://viimk-api.onrender.com`

### 2.3 手动创建（不用 Blueprint）

| 字段 | 值 |
|------|----|
| Name | `viimk-api` |
| Runtime | `Python 3` |
| Build Command | `pip install --upgrade pip wheel && pip install -r requirements.txt && pip install gunicorn` |
| Start Command | `gunicorn --bind 0.0.0.0:$PORT --workers 2 --timeout 60 server:app` |
| Health Check Path | `/api/health` |
| Region | Singapore（离国内最近） |
| Plan | Free |

---

## 三、方案 B：整仓推送（图省事）

### 3.1 推送整个 viimk-uniapp

```bash
cd viimk-uniapp
# node_modules / .venv / __pycache__ 已被 .gitignore 排除，无需手动处理
git add .
git commit -m "feat: init viimk-uniapp project"
git remote add origin https://github.com/你的用户名/viimk-uniapp.git
git push -u origin main
```

### 3.2 Render 创建服务（两种方式任选）

**方式 1：Blueprint（全自动，推荐）**

1. Render → **New +** → **Blueprint**
2. 连接仓库 `viimk-uniapp`
3. Render 自动读取项目根目录 `render.yaml`，其中已配 `rootDir: backend`
4. 等待部署完成

**方式 2：手动创建 Web Service**

| 字段 | 值 |
|------|----|
| Name | `viimk-api` |
| Runtime | `Python 3` |
| **Root Directory** | `backend`（**重要！** 让 Render 只处理 backend/ 目录） |
| Build Command | `pip install -r requirements.txt && pip install gunicorn` |
| Start Command | `gunicorn --bind 0.0.0.0:$PORT --workers 2 --timeout 60 server:app` |
| Health Check Path | `/api/health` |
| Region | Singapore |
| Plan | Free |

> 忘记填 `Root Directory=backend` 会构建失败（根目录没有 server.py）。

---

## 四、验证部署

```bash
# 健康检查
curl https://viimk-api.onrender.com/api/health
# 期望：{"code":0,"msg":"ok","sites":["ffzy","wuj","lzi","bdz","ffzy2"]}

# 搜索
curl -G "https://viimk-api.onrender.com/api/search" --data-urlencode "wd=庆余年" | head -c 200

# 详情
curl "https://viimk-api.onrender.com/api/detail?id=79613" | head -c 200

# 版本检查（需配置蓝奏云文件夹，默认返回 apkUrlType=share）
curl "https://viimk-api.onrender.com/api/version"
```

---

## 五、防睡眠（重要）

Render 免费版 15 分钟无访问会睡眠，首次唤醒 30-50 秒。

### 方案 1：UptimeRobot（推荐，零代码）

1. 注册 https://uptimerobot.com
2. Add New Monitor → Monitor Type **HTTP(s)**
3. URL: `https://viimk-api.onrender.com/api/health`
4. Monitoring Interval: **10 minutes** → 保存

### 方案 2：保活脚本 + cron（需常开机器）

```bash
cd viimk-uniapp
cp deploy/keepalive.sh /usr/local/bin/viimk-keepalive.sh
chmod +x /usr/local/bin/viimk-keepalive.sh
# 修改脚本内 RENDER_URL 为你的地址
sudo sed -i 's|https://viimk-api.onrender.com|https://你的地址.onrender.com|' /usr/local/bin/viimk-keepalive.sh

sudo crontab -e
# 添加：
*/10 * * * * /usr/local/bin/viimk-keepalive.sh >> /var/log/viimk-keepalive.log 2>&1
```

---

## 六、配置前端连接

编辑 `src/api/request.js`（viimk-uniapp 前端）：

```javascript
// 把第 51 行改成你的 Render 地址
const REMOTE_BASE = 'https://viimk-api.onrender.com'
```

重新用 HBuilderX 打包 App，App/小程序端就会直连 Render 后端。

---

## 七、采集源健康检查（可选）

```bash
cd viimk-uniapp
./.venv/bin/python deploy/probe-sources.py
# → 并发探测多个采集源的搜索/详情/直链可用性，输出结构化结果
# → 发现挂掉的源后替换 server.py 的 SITES 配置，git push 后 Render 自动重部署
```

---

## 八、Docker 部署（兼容其他平台）

两种方案对应两个 Dockerfile：

| 场景 | Dockerfile 位置 | 用法 |
|------|-----------------|------|
| 最小仓库（backend 独立仓库） | `backend/Dockerfile` | `cd backend && docker build -t viimk-api .` |
| 整仓推送（viimk-uniapp 含 frontend） | `项目根/Dockerfile` | `cd viimk-uniapp && docker build -t viimk-api .` |

Render 新建 Web Service → Runtime 选 **Docker**，Render 会自动识别对应目录的 Dockerfile。

---

## 九、免费版限制与常见问题

| 限制 | 说明 | 处理 |
|------|------|------|
| 750 小时/月 | 1 个服务 24×7 跑满 31 天刚好够用 | 正常 1 个服务不用管 |
| 512MB 内存 | Flask + 2 workers 刚好 | 不要加更多 worker |
| 15 分钟无访问睡眠 | 配 UptimeRobot | 24×7 保持在线 |
| 国外节点延迟高 | 到国内采集站偶尔慢 | 换 Cloudflare Tunnel（deploy/cloudflared-deploy.sh）在国内机器部署 |
| 首次请求 502 | 冷启动或在构建 | 等 1-2 分钟 |

### 常见问答

- **Q: 部署后访问 502 / Build failed？**
  A: 方案 B 忘记填 `Root Directory=backend` 最常见。检查 Logs 标签。

- **Q: 搜索接口超时？**
  A: Render 在新加坡，到 ffzy 等国内采集站有 RTT 延迟（~80-150ms），server.py 已配 20s 超时，一般能过；第一次请求冷启动慢属正常。对延迟敏感 → 用 `deploy/cloudflared-deploy.sh` 在国内云服务器/家庭宽带部署。

- **Q: /api/version 蓝奏云直链解析失败？**
  A: 蓝奏云单文件分享页有 JS 反爬（arg1 混淆），代码会自动回退到 `apkUrlType=share` + 返回单文件分享链接，App 端打开浏览器下载即可，**不影响功能**。

- **Q: 想升级付费版？**
  A: Render 控制台 → Settings → Change Plan → Starter $7/月，永不睡眠 + 1GB 内存。
