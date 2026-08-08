# 腾讯云 SCF 云函数部署指南

> 国内白嫖天花板：100 万次请求/月 + 40 万 GB-s 资源额度 **永久免费**，国内访问速度比 Render / Koyeb 快。

## 一、前置准备

1. **腾讯云账号 + 实名认证**（必须，国内平台合规要求，身份证 + 手机号即可，免费）
2. 登录 https://console.cloud.tencent.com/scf

## 二、方式 A：网页控制台上传（推荐，零 CLI）

### 步骤 1：打包部署文件

在项目根目录（`viimk-uniapp/`）执行：

```bash
# 打包 3 个核心文件（scf_handler.py + server.py + requirements.txt）
zip -r viimk-scf.zip scf_handler.py server.py requirements.txt

# 或者在 Windows 上直接把这 3 个文件选中 → 右键 → 压缩为 zip
```

### 步骤 2：创建云函数

1. 打开 https://console.cloud.tencent.com/scf/list?rid=1
2. **新建 → 自定义创建**
3. 填写配置：

| 配置项 | 值 |
|---|---|
| 函数名称 | `viimk-api` |
| 地域 | 广州 / 上海 / 北京（选离你近的） |
| 运行环境 | **Python 3.10**（3.9 也行，别用 3.7 以下） |
| 函数代码 | **本地上传 zip 包** → 选刚才的 `viimk-scf.zip` |
| 执行方法 | `scf_handler.main_handler` |
| 内存 | **512 MB**（256MB 能跑但采集站慢请求容易 OOM，推荐 512） |
| 初始化超时时间 | **60 秒**（冷启动第一次加载 requests 慢） |
| 执行超时时间 | **60 秒**（采集站偶发慢请求，默认 3s 必炸） |

4. 拉到底点 **完成**

### 步骤 3：安装 Python 依赖（SCF 环境默认没有 flask/requests）

进入函数详情页，选择 **函数代码** 标签 → 选 **Web IDE** 或 **在线编辑器**，打开终端：

```bash
# 在终端执行：把依赖安装到函数根目录
pip install -r requirements.txt -t . --upgrade
```

或者用「层管理」方式更干净（推荐，层可复用）：

1. 左侧菜单 **层管理** → 新建层
2. 名称：`viimk-deps`
3. 内容：上传 zip 包（先在本机 `mkdir -p python && pip install flask requests -t python && zip -r viimk-deps.zip python/` 然后上传这个 zip）
4. 运行环境勾 Python 3.10 / 3.9
5. 回到函数 → **函数配置 → 层管理** → 关联这个层

### 步骤 4：配置 API Gateway 触发器（拿到公网 URL）

1. 函数详情 → **触发器管理** → **创建触发器**
2. 方式：**API Gateway 触发器**
3. 触发方式：**HTTP API**（不是传统 API）
4. 集成响应：**开启**（重要！否则自定义 status/headers 无效）
5. 开启 CORS：**开启**
6. 保存

创建成功后，会看到一个这样的 URL：

```
https://service-12345678.gz.apigw.tencentcs.com/release/
```

### 步骤 5：测试

```bash
export API="https://service-12345678.gz.apigw.tencentcs.com/release"

# 健康检查
curl -s "$API/api/health" | head
# 期望：{"code":0,"msg":"ok","sites":["ffzy","wuj",...]}

# 搜索
curl -s "$API/api/search?wd=%E5%BA%86%E4%BD%99%E5%B9%B4" | head -c 300

# 版本检查
curl -s "$API/api/version"
```

成功后把 `$API` 这个 URL 填到前端 `src/api/request.js#L51` 的 `REMOTE_BASE`。

## 三、方式 B：Serverless Framework CLI（进阶，一键部署）

适合熟悉命令行的用户，自动安装依赖 + 建 API GW。

```bash
# 1. 安装 serverless
npm install -g serverless

# 2. 部署（会弹出腾讯云扫码授权）
serverless deploy --config scf_serverless.yml

# 3. 部署完后查看输出的 URL
```

首次部署会触发 **扫码登录**，用微信扫腾讯云二维码授权即可。

## 四、冷启动优化（可选但推荐）

SCF 免费版 10-15 分钟没请求会释放实例，下次请求要冷启动（约 3-8 秒）。方案：

**1. 配置定时触发器（每 10 分钟 ping 一次 /api/health）**

- 触发器管理 → 创建触发器 → 方式：**定时触发**
- 表达式：`0 */10 * * * * *`（每 10 分钟）
- 目标：新建一个 `keepalive_handler.py`，内容：
  ```python
  import urllib.request
  def main_handler(e, c):
      try:
          urllib.request.urlopen("https://你的地址.apigw.tencentcs.com/release/api/health", timeout=20)
      except Exception as ex:
          print("ping err", ex)
      return "ok"
  ```
- 执行方法：`keepalive_handler.main_handler`

**2. 改内存到 512MB**（冷启动更快）

## 五、常见问题

| 问题 | 解决 |
|---|---|
| 部署后 403 / 鉴权失败 | API Gateway 触发器要选 **HTTP API**，不要选传统 API（传统默认需要签名） |
| 404 Not Found | 执行方法是不是 `scf_handler.main_handler`？APIGW path 是不是 `/{proxy+}` + ANY？ |
| 500 / Internal Error | 函数日志里看报错：通常是 `ModuleNotFoundError: No module named 'flask'` → 漏了 `pip install -t .` |
| body 乱码 / m3u8 播放失败 | APIGW **集成响应必须开启** + 代码里 `isBase64Encoded` 正确处理二进制 |
| 搜索超时 3 秒 | 把函数「执行超时」改到 60 秒（**默认 3 秒必炸**） |
| 100 万次用完了？ | 不会，个人正常使用 10 万次顶天。如果是企业，买预留实例（包月）比云服务器划算 |

## 六、推荐配置（踩过坑的）

| 项 | 值 | 为什么 |
|---|---|---|
| 内存 | 512MB | 256 搜索大响应会慢，512 刚好 |
| 超时 | 60s | ffzy 采集站偶尔 RTT 1-3s，还要跑 5 源并发 + 重试 |
| 环境 | Python 3.10 | 版本稳定，requests 等兼容好 |
| 地域 | 广州 / 上海 | 离国内用户近，到 ffzy 采集站 RTT <50ms |
| 定时保活 | cron 10分钟 | 防止冷启动，用户体验接近常驻服务 |
| 集成响应 | 开启 | Flask 返回的自定义 status 和 headers 才能正确返回 |

## 七、费用

**个人免费用户**：
- 调用次数：100 万次/月（免费额度，永久）
- 资源使用量：40 万 GB-s/月（512MB 函数 800,000 秒 ≈ 222 小时，实际不会跑满，够你 24×7×30 用）
- API Gateway：100 万次/月免费

正常个人使用（假设日均 100 次搜索 + 100 次播放），**绝对不花钱**。
