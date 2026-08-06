/**
 * VIIMK 统一请求封装 (uniapp Promise style)
 *
 * 说明：
 *   目前全网没有可免费公开使用且能覆盖 VIIMK 全部功能的接口
 *   （需要包含 短剧推荐/关注/评分/海报/集数/用户态 等全套字段）
 *   详见：src/api/index.js 文件头部的接口评估说明
 *
 *   本文件作为**请求层预留**，当后端接口或合适的第三方 API 接入时：
 *   1. 修改 export const API_BASE = '你的接口域名'
 *   2. 如有 token 鉴权，修改 getToken() 的存储 key
 *   3. 在 pages.json 的 h5.devServer.proxy 中配置反向代理解决跨域
 *   4. 将 src/api/index.js 中的 mock 实现改为调用 request() 即可
 *
 * 使用：
 *   import { request } from '@/api/request.js'
 *   const res = await request({ url: '/home/banner', method: 'GET', data: {} })
 */

// ========== 可根据实际情况修改 ==========
export const API_BASE = ''
export const TIMEOUT = 15000
export const TOKEN_KEY = 'viimk_token'

/*
 * Python 爬虫后端（server.py）基础地址
 *
 *  ┌─────────────────────────────────────────────────────────────────────┐
 *  │  端     │ 默认值                              │ 如何改？            │
 *  ├──────────────────────────────────────────────────────────────────────┤
 *  │ H5      │ '/__pyapi' (Vite 反代到 Python 3001) │ 不用改              │
 *  │ 小程序  │ 默认用远端公网服务 REMOTE_BASE       │ 改 REMOTE_BASE     │
 *  │ App     │ 策略 1（推荐）：直接连远端公网服务     │ 改 REMOTE_BASE     │
 *  │         │ 策略 2（内网离线）：跑本地服务         │ 改 LOCAL_BASE      │
 *  │         │            （Android 本地 127.0.0.1） │                     │
 *  └──────────────────────────────────────────────────────────────────────┘
 *
 *  REMOTE_BASE 部署提示（App/小程序 打包必须改）：
 *    将 server.py 部署到自己的云服务器（HTTPS 域名），例如：
 *    https://viimk-api.example.com
 *    然后把 REMOTE_BASE 改成这个地址。
 *    server.py 启动：FLASK_ENV=production gunicorn -b 0.0.0.0:3001 -w 4 server:app
 *    再用 Nginx 反代到 HTTPS 域名 + 配置允许跨域（server.py 里已加 CORS 头）
 *
 *  首次启动时可用 setPyApiBase(url) 动态覆盖，方便切换测试/生产环境：
 *    import { setPyApiBase } from '@/api/request.js'
 *    setPyApiBase('https://viimk-api.example.com')
 */

// ========= 可部署的远端服务：App / 小程序打包前把这一行改成自己的域名 ========
const REMOTE_BASE = 'https://1302446649-7terr1rghd.ap-guangzhou.tencentscf.com'
// ==========================================================================

// 本地调试/内网离线模式（真机调 App 且电脑开热点时可填电脑局域网 IP）
const LOCAL_BASE  = 'http://localhost:3001'

let _overrideBase = ''
/** 动态覆盖 Python 服务地址（便于设置页切换环境） */
export function setPyApiBase(url) {
  _overrideBase = (url || '').replace(/\/+$/, '')
}
export function getPyApiBase() {
  if (_overrideBase) return _overrideBase
  // 运行时检测环境（不依赖条件编译，App WebView 也能正确判断）
  if (REMOTE_BASE) return REMOTE_BASE.replace(/\/+$/, '')
  // 本地开发走 Vite 代理
  if (typeof window !== 'undefined' && window.location && window.location.hostname === 'localhost') {
    return '/__pyapi'
  }
  return LOCAL_BASE
}
export const PY_API_BASE = getPyApiBase()

export function getToken() {
  try {
    return uni.getStorageSync(TOKEN_KEY) || ''
  } catch (e) {
    return ''
  }
}

export function setToken(token) {
  try {
    uni.setStorageSync(TOKEN_KEY, token || '')
  } catch (e) {}
}

export function clearToken() {
  try {
    uni.removeStorageSync(TOKEN_KEY)
  } catch (e) {}
}

/**
 * 统一请求封装
 * @param {Object} options
 * @param {string} options.url     请求路径或完整 URL
 * @param {string} options.method  GET/POST/PUT/DELETE 等
 * @param {Object} options.data    请求参数
 * @param {Object} options.header  自定义 header
 * @param {boolean} options.auth   是否需要携带 token (默认 true)
 */
export function request(options = {}) {
  const { url, method = 'GET', data = {}, header = {}, auth = true } = options
  const fullUrl = /^https?:\/\//.test(url) ? url : API_BASE + url

  const finalHeader = {
    'Content-Type': method.toUpperCase() === 'GET'
      ? 'application/json'
      : 'application/x-www-form-urlencoded',
    ...header
  }
  if (auth) {
    const token = getToken()
    if (token) finalHeader['Authorization'] = 'Bearer ' + token
  }

  return new Promise((resolve, reject) => {
    uni.request({
      url: fullUrl,
      method: method.toUpperCase(),
      data,
      header: finalHeader,
      timeout: TIMEOUT,
      success: (res) => {
        const status = res.statusCode
        if (status >= 200 && status < 300) {
          // 统一业务响应结构 { code, data, message }
          const body = res.data
          if (body && typeof body === 'object' && 'code' in body) {
            if (body.code === 0 || body.code === 200) {
              resolve(body.data)
            } else if (body.code === 401) {
              clearToken()
              uni.showToast({ title: '请先登录', icon: 'none' })
              reject(body)
            } else {
              uni.showToast({ title: body.message || '请求失败', icon: 'none' })
              reject(body)
            }
          } else {
            resolve(body)
          }
        } else if (status === 401) {
          clearToken()
          uni.showToast({ title: '请先登录', icon: 'none' })
          reject(res)
        } else {
          uni.showToast({ title: '请求失败(' + status + ')', icon: 'none' })
          reject(res)
        }
      },
      fail: (err) => {
        uni.showToast({ title: '网络异常，请重试', icon: 'none' })
        reject(err)
      }
    })
  })
}


