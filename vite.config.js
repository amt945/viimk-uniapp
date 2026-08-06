import { defineConfig } from 'vite'
import path from 'node:path'
import http from 'node:http'
import https from 'node:https'
import { URL } from 'node:url'
import uni from '@dcloudio/vite-plugin-uni'

/**
 * API 反向代理（自定义中间件 + Node http/https 模块）
 *
 * 为什么不用 Vite 内置 server.proxy？为什么不用 Node fetch？
 *   1) uni-app vite 插件会拦截部分子路径（/api/home/list、/api/home_page 等）
 *      返回 400，所以用自定义中间件放在 uni() 之前。
 *   2) Node 原生 fetch 在浏览器场景下，部分请求会触发内部校验（如 host 头冲突）
 *      导致 "fetch failed"（curl/node fetch 手动测试都正常但浏览器端报错），
 *      改用 Node http/https 模块，完全控制请求细节，不依赖 fetch 内部逻辑。
 *
 * 支持的前缀：
 *   /__pyapi  → http://localhost:3001  （Python 爬虫后端，提供搜索/详情 API）
 */
const PROXY_TARGETS = [
  { prefix: '/__pyapi', target: 'https://1302446649-7terr1rghd.ap-guangzhou.tencentscf.com' }
]

/**
 * 读取请求 body（POST/PUT 等）
 * @param {import('http').IncomingMessage} req
 * @returns {Promise<Buffer>}
 */
function readReqBody(req) {
  return new Promise((resolve, reject) => {
    const chunks = []
    req.on('data', (c) => chunks.push(c))
    req.on('end', () => resolve(Buffer.concat(chunks)))
    req.on('error', (e) => reject(e))
  })
}

/**
 * 通过 Node http/https 代理请求
 * @param {string} fullUrl      目标完整 URL
 * @param {string} [method]     HTTP 方法（默认 GET）
 * @param {Buffer} [body]       请求体（POST/PUT 时传入）
 * @param {Object} [reqHeaders] 原始请求头（透传 Content-Type 等）
 * @returns {Promise<{status:number, headers:Record<string,string>, body:Buffer}>}
 */
function proxyViaHttp(fullUrl, method = 'GET', body = null, reqHeaders = {}) {
  return new Promise((resolve, reject) => {
    const u = new URL(fullUrl)
    const isHttps = u.protocol === 'https:'
    const lib = isHttps ? https : http
    const headers = {
      'User-Agent':
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36',
      Accept: 'application/json, text/plain, */*',
      'Accept-Language': 'zh-CN,zh;q=0.9',
    }
    // 透传 POST 请求的 Content-Type（前端用 application/json 发 wd）
    const ct = reqHeaders['content-type']
    if (ct) headers['Content-Type'] = ct
    // ffzy 采集接口需要 Referer，按目标域名派生
    headers.Referer = `${u.protocol}//${u.host}/`
    if (body && body.length) headers['Content-Length'] = Buffer.byteLength(body)
    const opts = {
      method,
      hostname: u.hostname,
      port: u.port || (isHttps ? 443 : 80),
      path: u.pathname + u.search,
      headers,
      timeout: 60000,
    }
    const clientReq = lib.request(opts, (res) => {
      const chunks = []
      res.on('data', (c) => chunks.push(c))
      res.on('end', () => {
        const buf = Buffer.concat(chunks)
        // 合并同名字段为单值（express/connect res.setHeader 不允许数组）
        const hdrs = {}
        for (const [k, v] of Object.entries(res.headers || {})) {
          if (k.toLowerCase() === 'set-cookie') continue
          if (Array.isArray(v)) hdrs[k] = v.join(', ')
          else if (v != null) hdrs[k] = String(v)
        }
        resolve({ status: res.statusCode || 500, headers: hdrs, body: buf })
      })
      res.on('error', (e) => reject(e))
    })
    clientReq.on('error', (e) => reject(e))
    clientReq.on('timeout', () => { clientReq.destroy(new Error('proxy timeout')) })
    // POST/PUT 写入请求体
    if (body && body.length) clientReq.write(body)
    clientReq.end()
  })
}

function apiProxyPlugin() {
  return {
    name: 'viimk-api-proxy',
    configureServer(server) {
      server.middlewares.use(async (req, res, next) => {
        // OPTIONS 预检统一放行
        if (req.method === 'OPTIONS') {
          res.setHeader('Access-Control-Allow-Origin', '*')
          res.setHeader('Access-Control-Allow-Methods', 'GET,POST,OPTIONS')
          res.setHeader('Access-Control-Allow-Headers', '*')
          res.statusCode = 204
          res.end()
          return
        }
        const rawUrl = req.url || ''
        const hit = PROXY_TARGETS.find(
          (t) => rawUrl.startsWith(t.prefix + '/') || rawUrl === t.prefix
        )
        if (!hit) {
          next()
          return
        }
        const realPath = rawUrl.replace(hit.prefix, '') || '/'
        const fullUrl = hit.target + realPath
        // POST/PUT 需要先读取请求体再转发（GET 无 body）
        let body = null
        const method = (req.method || 'GET').toUpperCase()
        if (method === 'POST' || method === 'PUT' || method === 'PATCH') {
          try { body = await readReqBody(req) } catch (e) { body = null }
        }
        console.log(`[api-proxy] ${method} ${rawUrl} → ${fullUrl}`)
        try {
          const { status, headers, body: respBody } = await proxyViaHttp(fullUrl, method, body, req.headers)
          res.statusCode = status
          res.setHeader('Access-Control-Allow-Origin', '*')
          res.setHeader('Access-Control-Allow-Methods', 'GET,POST,OPTIONS')
          res.setHeader('Access-Control-Allow-Headers', '*')
          const ct = String(headers['content-type'] || 'application/json; charset=utf-8').toLowerCase()
          res.setHeader('Content-Type', ct)
          res.end(respBody)
        } catch (e) {
          console.error(`[api-proxy] ERROR ${rawUrl}: ${e && e.message}`)
          res.statusCode = 502
          res.setHeader('Access-Control-Allow-Origin', '*')
          res.setHeader('Content-Type', 'application/json; charset=utf-8')
          res.end(
            JSON.stringify({ code: -1, msg: 'proxy error: ' + ((e && e.message) || 'unknown') })
          )
        }
      })
    }
  }
}

export default defineConfig({
  // 代理插件必须放在 uni() 之前：uni 的前置中间件会拦截部分路径
  plugins: [apiProxyPlugin(), uni()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src')
    }
  },
  server: {
    host: '0.0.0.0',
    port: 5173
  }
})
