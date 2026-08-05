/**
 * VIIMK 业务接口暴露层
 * ======================================================================
 * 接口可用性评估结论（2026-08-04）：
 *
 *   经全网检索公开免费影视/短剧接口，目前**没有可免注册、免 key、
 *   无版权风险、且能覆盖 VIIMK 全部功能的公共 API**，原因如下：
 *
 *   ——————————————————— 现有公开接口与项目需求的差距 ———————————————————
 *
 *   1. 核心功能覆盖
 *      项目需要 13 类接口（首页 hero/分类/推荐/为您推荐、短剧推荐&关注、
 *      详情+集数、片库、搜索、历史记录、我的收藏、播放器进度等）。
 *      其中"历史记录/我的收藏"属于**用户态数据**，任何公开第三方
 *      API 无法提供，必须有后端存储才能实现。
 *
 *   2. 中文短剧（竖屏剧）内容
 *      VIIMK 的核心品类"短剧"属于国内特定内容形态：
 *      · TMDB / TVmaze / OMDB 等国际接口只有全球院线电影和英美剧，
 *        完全没有"甜宠/逆袭/穿越/复仇"等短剧题材和竖版海报。
 *      · 豆瓣只收录了长片和电视剧，不含日更大规模的付费短剧。
 *      · api.kuleu.com 等搜索接口仅返回名称+网盘分享链接，无封面、
 *        无评分、无集数，无法展示项目 UI。
 *
 *   3. 合规与稳定性
 *      · 豆瓣 `movie.douban.com/j/*` 内部 JSON 接口在 H5 端被
 *        CORS 拦截，且随时会加 Referer/封 IP。
 *      · 影视仓/TvBox 系列接口为第三方资源聚合，存在严重版权风险，
 *        同时每个站点字段格式不同，接入后稳定性完全不可控。
 *      · 全网短剧查询、每日短剧资源接口提供的是网盘链接（疑似盗版），
 *        法律风险较高，且仅有 2 个字段，无法映射到 UI。
 *
 *   4. 接口凭证
 *      · TMDB / OMDB / JustWatch 等正规 API 需要用户注册并申请
 *        API key，无法在不提供用户凭证输入界面的情况下"开箱即用"。
 *
 *   ——————————————————— 当前层如何实现 ———————————————————
 *
 *   按用户指示"如果没有就先不调接口"，每个业务接口函数目前都使用
 *   src/mock/data.js 中的本地模拟数据，保持页面交互完全可用。
 *   同时函数签名、参数与返回结构均已与真实 REST 接口对齐，
 *   一旦自有后端部署或第三方合规接口可用，只需将每个函数的
 *   Promise 内部替换为调用 request.js 即可，页面代码无需改动。
 *
 * ======================================================================
 */

import {
  heroBanner as _heroBanner,
  homeCategories as _homeCategories,
  hotRecommend as _hotRecommend,
  forYou as _forYou,
  shortsRecommendTabs as _shortsRecommendTabs,
  shortsRecommendList as _shortsRecommendList,
  shortsFollowTabs as _shortsFollowTabs,
  shortsFollowRegions as _shortsFollowRegions,
  shortsFollowList as _shortsFollowList,
  detailData as _detailData,
  profileStats as _profileStats,
  profileMenu as _profileMenu,
  historyList as _historyList,
  favoriteList as _favoriteList,
  aboutInfo as _aboutInfo,
  aboutMenu as _aboutMenu
} from '@/mock/data.js'
import { getPyApiBase } from '@/api/request.js'

/* ========================= Python 爬虫后端 ========================= */
// Python Flask 服务 (server.py)：
// H5 端通过 Vite 中间件 /__pyapi 代理；App/MP 端直连远程或本地
// 每次请求都动态取 base，支持运行时切换（设置页切换环境）

function onlineRequest(path, params = {}, method = 'GET') {
  const base = getPyApiBase() || ''
  const url = base + path
  return new Promise((resolve, reject) => {
    const opts = {
      url,
      method,
      timeout: 30000,
      success: (res) => {
        if (res.statusCode >= 200 && res.statusCode < 300 && res.data) {
          resolve(res.data)
        } else {
          reject(res)
        }
      },
      fail: (err) => reject(err)
    }
    if (method === 'POST') {
      opts.data = params
      opts.header = { 'Content-Type': 'application/json' }
    } else {
      const query = Object.keys(params)
        .filter(k => params[k] !== undefined && params[k] !== null && params[k] !== '')
        .map(k => encodeURIComponent(k) + '=' + encodeURIComponent(params[k]))
        .join('&')
      opts.url = url + (query ? '?' + query : '')
    }
    uni.request(opts)
  })
}

/* ========================= 通用工具 ========================= */
function delay(data, ms = 200) {
  // 模拟一次 200ms 的网络请求，让加载态和过渡动画有机会展示
  return new Promise((resolve) => setTimeout(() => resolve(data), ms))
}

/* ========================= 首页 =========================
 * 由 Python 后端 /api/home 提供（ffzy 采集站最新视频）
 * 失败时回退到 mock 数据，保证页面不空。
 */
// 首页聚合缓存：_homeCache 是值缓存，_homePromise 是 in-flight Promise（防重入）
let _homeCache = null
let _homePromise = null
const HOME_CACHE_MS = 2 * 60 * 1000 // 前端再做 2 分钟内存缓存，后端已有 60s，前端再兜底省请求
let _homeCachedAt = 0

export function fetchHeroBanner() {
  return fetchOnlineHome().then(d => (d && d.hero) || { ..._heroBanner })
}

export function fetchHomeCategories() {
  return fetchOnlineHome().then(d => (d && d.categories) || [..._homeCategories])
}

export function fetchHotRecommend() {
  return fetchOnlineHome().then(d => (d && d.hot && d.hot.length)
    ? d.hot.map(i => ({ id: i.id, title: i.title, cover: i.cover, tag: i.tag || '', onlineSite: i.onlineSite, vodId: i.vodId }))
    : _hotRecommend.map(i => ({ ...i })))
}

/**
 * 首页分类 tab → ffzy type_id 映射
 * 必须与 server.py 的 HOME_TAB_MAP 保持一致。
 * 推荐/热播 = 0（最新全部）；都市/古装 = 13（国产剧）；悬疑 = 6（动作片）。
 */
const HOME_TAB_T_MAP = {
  '推荐': 0,
  '热播': 0,
  '都市': 13,
  '古装': 13,
  '悬疑': 6,
}

/**
 * 首页"热门推荐"无限滚动：按分类 tab 分页加载
 * 复用 /api/home 路径（带 pg 参数走分页模式），并传数字 t（type_id）。
 *
 * 重要：URL 必须全 ASCII，不能带中文 cat 参数 —— uni-app vite 插件会拦截
 * URL 里带中文 query 的请求返回 400（curl 编码后能过，浏览器实测 400）。
 * 所以前端把中文 cat 转成数字 t 再传。
 *
 * @param {string} cat  分类名（推荐/热播/都市/古装/悬疑）
 * @param {number} pg   页码，从 1 开始
 * @returns {Promise<{list: Array, hasMore: boolean, page: number}|null>}
 */
export function fetchHomeList(cat, pg) {
  const t = HOME_TAB_T_MAP[cat] != null ? HOME_TAB_T_MAP[cat] : 0
  // t=0 表示最新全部（推荐/热播），不传 t 参数；t>0 才传
  const params = t > 0 ? { t: t, pg: pg || 1 } : { pg: pg || 1 }
  return onlineRequest('/api/home', params)
    .then((res) => {
      if (!res || res.code !== 0 || !res.data || !Array.isArray(res.data.list)) return null
      return {
        list: res.data.list,
        hasMore: !!res.data.hasMore,
        page: res.data.page || pg
      }
    })
    .catch((err) => {
      console.warn('[online] home list error', err)
      return null
    })
}

/**
 * 拉取首页聚合数据（带内存缓存 + in-flight 防重入）
 *   · 同一时刻 4 个函数同时调 → 只发 1 次真实请求，其余都等同一个 Promise
 *   · 前端 2 分钟内返回内存缓存（后端还有 60 秒缓存，双重兜底）
 * @returns {Promise<Object|null>} { hero, hot, forYou, categories }
 */
function fetchOnlineHome() {
  const now = Date.now()
  // 1) 值缓存命中
  if (_homeCache && (now - _homeCachedAt) < HOME_CACHE_MS) {
    return Promise.resolve(_homeCache)
  }
  // 2) in-flight Promise 命中（同一时刻多函数并发调，共享同一个请求）
  if (_homePromise) {
    return _homePromise
  }
  // 3) 发真实请求，把 Promise 存起来，避免并发下重复发请求
  _homePromise = onlineRequest('/api/home')
    .then((res) => {
      if (!res || res.code !== 0 || !res.data) return null
      _homeCache = res.data
      _homeCachedAt = Date.now()
      return res.data
    })
    .catch((err) => {
      console.warn('[online] home error', err)
      return null
    })
    .finally(() => {
      // 请求完成后清除 in-flight（无论成功失败都允许下一轮重发）
      _homePromise = null
    })
  return _homePromise
}

/* ========================= 短剧 =========================
 * 由 Python 后端 /api/shorts 提供（ffzy 国产剧分类，模拟短剧片库）
 * 失败时回退到 mock 数据。
 *
 * 短剧页改为单列表 + 分类筛选 + 触底加载（参考首页/片库），
 * 不再有 推荐/关注 双 tab。
 */
export function fetchShortsRecommendTabs() {
  return delay([..._shortsRecommendTabs])
}

export function fetchShortsRecommendList(cat) {
  // 推荐 tab：忽略 cat 直接拉最新（cat 仅为本地筛选标签）
  return fetchOnlineShorts('推荐')
    .then(list => list.length ? list : _shortsRecommendList.map(i => ({ ...i })))
}

export function fetchShortsFollowTabs() {
  return delay([..._shortsFollowTabs])
}

export function fetchShortsFollowRegions() {
  return delay([..._shortsFollowRegions])
}

export function fetchShortsFollowList(cat, region) {
  // 关注 tab：按 cat 拉对应分类
  const tab = cat || '都市'
  return fetchOnlineShorts(tab)
    .then(list => list.length ? list : _shortsFollowList.map(i => ({ ...i })))
}

/**
 * 拉取短剧列表（Python 后端）
 * @param {string} tab 推荐/都市/古装/悬疑/玄幻/甜宠/复仇
 * @returns {Promise<Array>}
 */
function fetchOnlineShorts(tab) {
  return onlineRequest('/api/shorts', { tab, pg: 1 })
    .then((res) => {
      if (!res || res.code !== 0 || !res.data || !Array.isArray(res.data.list)) return []
      return res.data.list
    })
    .catch((err) => {
      console.warn('[online] shorts error', err)
      return []
    })
}

/**
 * 短剧题材 tab 列表（固定，与 server.py SHORTS_TAB_MAP 的 name 一一对应）
 * index 即数字 tab code，前端传 tab=index，后端映射 (t=36, wd)
 * 真短剧数据源：ffzy 短剧分类 type_id=36
 */
const SHORTS_TABS = ['推荐', '总裁', '穿越', '重生', '战神', '逆袭', '赘婿']

/**
 * 短剧分类 tab 列表
 * @returns {Promise<string[]>}
 */
export function fetchShortsTabs() {
  return delay([...SHORTS_TABS])
}

/**
 * 短剧列表分页加载（参考 fetchLibraryListPaged / fetchHomeList）
 * URL 全 ASCII：传 tab=数字 code（后端映射 t=36 + wd 题材关键词），避免中文 URL 被拦截。
 * @param {string} cat  题材名（推荐/总裁/穿越/重生/战神/逆袭/赘婿）
 * @param {number} pg   页码，从 1 开始
 * @returns {Promise<{list: Array, hasMore: boolean, page: number}|null>}
 */
export function fetchShortsListPaged(cat, pg) {
  const idx = SHORTS_TABS.indexOf(cat)
  const tab = idx >= 0 ? idx : 0
  const params = { tab: tab, pg: pg || 1 }
  return onlineRequest('/api/shorts', params)
    .then((res) => {
      if (!res || res.code !== 0 || !res.data || !Array.isArray(res.data.list)) return null
      return {
        list: res.data.list,
        hasMore: !!res.data.hasMore,
        page: res.data.page || pg
      }
    })
    .catch((err) => {
      console.warn('[online] shorts list error', err)
      return null
    })
}

/* ========================= 详情页 ========================= */
/**
 * 作品详情 + 剧集列表
 * GET /detail/:id
 */
export function fetchDetail(id) {
  return delay({
    ..._detailData,
    id: id || _detailData.id,
    episodes: _detailData.episodes.map(e => ({ ...e }))
  })
}

/* ========================= 片库 =========================
 * 由 Python 后端 /api/list 提供（ffzy 采集站按分类分页）
 * 失败时回退到 mock 数据。
 */
export function fetchLibraryCategories() {
  return onlineRequest('/api/categories')
    .then((res) => {
      if (!res || res.code !== 0 || !Array.isArray(res.data)) return ['全部', '电影', '电视剧', '综艺', '动漫', '纪录片']
      return res.data.map(c => c.name)
    })
    .catch(() => ['全部', '电影', '电视剧', '综艺', '动漫', '纪录片'])
}

export function fetchLibraryList(cat) {
  return fetchLibraryListPaged(cat, 1)
    .then((res) => (res && res.list ? res.list : mockLibraryList()))
    .catch(() => mockLibraryList())
}

/**
 * 片库分类 tab → ffzy type_id 映射
 * 必须与 server.py 的 LIBRARY_TAB_MAP 保持一致。
 * 前端把中文 cat 转成数字 t 再传，避免中文出现在 URL 里被 uni-app vite 插件拦截。
 */
const LIBRARY_TAB_T_MAP = {
  '全部': 0,       // 0 / None 表示最新全部
  '电影': 6,       // 动作片
  '电视剧': 13,    // 国产剧
  '综艺': 25,      // 大陆综艺
  '动漫': 29,      // 国产动漫
  '纪录片': 20,
}

/**
 * 片库列表分页加载（参考首页 fetchHomeList 的设计）
 * 重要：URL 必须全 ASCII，不能带中文 cat 参数 —— uni-app vite 插件会拦截
 * URL 里带中文 query 的请求返回 400。所以前端把中文 cat 转成数字 t 再传。
 * @param {string} cat  分类名（全部/电影/电视剧/短剧/综艺/动漫/纪录片）
 * @param {number} pg   页码，从 1 开始
 * @returns {Promise<{list: Array, hasMore: boolean, page: number}|null>}
 */
export function fetchLibraryListPaged(cat, pg) {
  const t = LIBRARY_TAB_T_MAP[cat] != null ? LIBRARY_TAB_T_MAP[cat] : 0
  // t=0 表示最新全部，不传 t 参数；t>0 才传
  const params = t > 0 ? { t: t, pg: pg || 1 } : { pg: pg || 1 }
  return onlineRequest('/api/list', params)
    .then((res) => {
      if (!res || res.code !== 0 || !res.data || !Array.isArray(res.data.list)) return null
      return {
        list: res.data.list,
        hasMore: !!res.data.hasMore,
        page: res.data.page || pg
      }
    })
    .catch((err) => {
      console.warn('[online] library list error', err)
      return null
    })
}

function mockLibraryList() {
  const all = [..._shortsRecommendList, ..._shortsFollowList]
  return all.map((item, idx) => ({
    id: item.id * 100 + idx,
    title: item.title,
    cover: item.cover,
    rating: item.rating || '8.5',
    meta: item.meta
  }))
}

/* ========================= 通用：mock 项 → 真实在线结果 =========================
 * 首页/片库/短剧的 mock fallback 数据没有 onlineSite/vodId，
 * 点击这类卡片时先用标题搜 ffzy，取第一个结果的 vodId 跳 detail.vue，
 * 保证用户始终进入真实详情页，不会落到 mock detail.vue。
 */

/**
 * 把任意 item（可能是 mock 或 online）解析为可跳转 detail.vue 的真实在线信息。
 * mock 项会先做一次在线搜索，取标题第一个命中结果做映射。
 * @param {Object|string|number} itemOrId item 对象、或纯 id 数字、或纯 title 字符串
 * @param {string} [fallbackTitle] itemOrId 是纯 id 时需提供的标题
 * @returns {Promise<{onlineSite:string, vodId:string, title:string}|null>}
 */
export async function resolveOnlineItem(itemOrId, fallbackTitle) {
  if (!itemOrId) return null
  let title = ''
  // 1) online item → 直接返回
  if (typeof itemOrId === 'object') {
    if (itemOrId.onlineSite && itemOrId.vodId) {
      return {
        onlineSite: itemOrId.onlineSite,
        vodId: String(itemOrId.vodId),
        title: itemOrId.title || fallbackTitle || '',
      }
    }
    title = itemOrId.title || ''
  } else if (typeof itemOrId === 'string') {
    title = itemOrId
  }
  const q = title || fallbackTitle
  if (!q) return null
  // 2) mock / 纯标题：在线搜索取第一个命中
  const list = await fetchOnlineSearch(q)
  if (!list || !list.length) return null
  const hit = list[0]
  return {
    onlineSite: hit.onlineSite || 'ffzy',
    vodId: String(hit.vodId),
    title: hit.title || q,
  }
}

/**
 * 用 resolveOnlineItem 的结果跳 detail.vue（详情页）。
 * 列表卡片点击 → 详情页 → 播放页
 */
export async function navigateToDetail(itemOrId, fallbackTitle, contentType) {
  const info = await resolveOnlineItem(itemOrId, fallbackTitle)
  if (!info || !info.vodId) {
    uni.showToast({ title: '暂无可播放资源', icon: 'none' })
    return false
  }
  const params = [
    'vodId=' + encodeURIComponent(info.vodId),
    'site=' + encodeURIComponent(info.onlineSite),
    'title=' + encodeURIComponent(info.title || '')
  ]
  if (contentType) params.push('contentType=' + encodeURIComponent(contentType))
  uni.navigateTo({ url: '/pages/detail/detail?' + params.join('&') })
  return true
}

/* ========================= 搜索 ========================= */
/**
 * 热搜词
 * GET /search/hot
 */
export function fetchSearchHotWords() {
  return delay([
    '三体', '狂飙', '繁花', '漫长的季节', '庆余年',
    '流浪地球2', '甜宠', '穿越', '逆袭'
  ])
}

/**
 * 搜索结果
 * GET /search?q=xxx&page=1&size=20
 */
export function fetchSearchResult(q, page = 1, size = 20) {
  q = (q || '').trim()
  if (!q) return delay([])
  const all = [..._shortsRecommendList, ..._shortsFollowList]
  const list = all
    .filter(item => item.title.indexOf(q) > -1 || (item.meta && item.meta.indexOf(q) > -1))
    .map(item => ({
      id: item.id,
      title: item.title,
      cover: item.cover,
      meta: item.meta,
      desc: item.tag || ''
    }))
  return delay(list)
}

/* ========================= 用户 ========================= */
const STORAGE_KEYS = {
  HISTORY: 'vmk_history',
  FAVORITE: 'vmk_favorite',
  OFFLINE: 'vmk_offline'
}

/**
 * 我的-统计数据（动态读取本地存储）
 */
export function fetchUserStats() {
  const history = uni.getStorageSync(STORAGE_KEYS.HISTORY) || []
  const favorite = uni.getStorageSync(STORAGE_KEYS.FAVORITE) || []
  const offline = uni.getStorageSync(STORAGE_KEYS.OFFLINE) || []
  return delay([
    { label: '历史记录', value: history.length },
    { label: '我的收藏', value: favorite.length },
    { label: '离线缓存', value: offline.length }
  ])
}

/**
 * 我的-菜单（去掉 VIP视频解析、消息通知、设置）
 */
export function fetchUserMenu() {
  return delay([
    { id: 'history', icon: 'history', text: '历史记录', badge: false },
    { id: 'favorite', icon: 'heart', text: '我的收藏', badge: false },
    { id: 'cache', icon: 'download', text: '离线缓存', badge: false },
    { id: 'about', icon: 'info', text: '关于', badge: false }
  ])
}

/**
 * 历史记录列表（本地存储）
 */
export function fetchHistoryList() {
  return delay((uni.getStorageSync(STORAGE_KEYS.HISTORY) || []).map(i => ({ ...i })))
}

/**
 * 新增/更新播放记录
 */
export function updateHistory(payload) {
  const list = uni.getStorageSync(STORAGE_KEYS.HISTORY) || []
  const idx = list.findIndex(i => i.id === payload.id)
  const now = new Date()
  const time = (now.getMonth() + 1) + '月' + now.getDate() + '日 ' +
    String(now.getHours()).padStart(2, '0') + ':' + String(now.getMinutes()).padStart(2, '0')
  if (idx >= 0) {
    list[idx] = { ...list[idx], ...payload, time }
  } else {
    list.unshift({ ...payload, time })
  }
  if (list.length > 50) list.length = 50
  uni.setStorageSync(STORAGE_KEYS.HISTORY, list)
  return delay(true)
}

/**
 * 删除单条历史记录
 */
export function deleteHistoryItem(id) {
  let list = uni.getStorageSync(STORAGE_KEYS.HISTORY) || []
  list = list.filter(i => i.id !== id)
  uni.setStorageSync(STORAGE_KEYS.HISTORY, list)
  return delay(true)
}

/**
 * 清空所有历史记录
 */
export function clearHistory() {
  uni.setStorageSync(STORAGE_KEYS.HISTORY, [])
  return delay(true)
}

/**
 * 收藏列表（本地存储）
 */
export function fetchFavoriteList() {
  return delay((uni.getStorageSync(STORAGE_KEYS.FAVORITE) || []).map(i => ({ ...i })))
}

/**
 * 检查是否已收藏
 * @param {string} vodId
 * @param {string} [onlineSite] 采集站 key（默认 ffzy）
 */
export function isFavorited(vodId, onlineSite) {
  const list = uni.getStorageSync(STORAGE_KEYS.FAVORITE) || []
  if (!vodId) return false
  const site = onlineSite || 'ffzy'
  const composite = site + ':' + vodId
  return list.some(i => i.id === composite || (i.vodId === vodId && (i.onlineSite || 'ffzy') === site))
}

/**
 * 加入/取消收藏
 * payload 必传 vodId / onlineSite，确保收藏项可导航到详情页
 */
export function toggleFavorite(payload) {
  let list = uni.getStorageSync(STORAGE_KEYS.FAVORITE) || []
  const vodId = payload.vodId || payload.id
  const onlineSite = payload.onlineSite || 'ffzy'
  // 复合 id 保证唯一性（同 vodId 不同站点也可区分）
  const composite = onlineSite + ':' + vodId
  const idx = list.findIndex(i => i.id === composite || (i.vodId === vodId && (i.onlineSite || 'ffzy') === onlineSite))
  let favorited = false
  if (idx >= 0) {
    list.splice(idx, 1)
    favorited = false
  } else {
    list.unshift({
      id: composite,
      vodId: vodId,
      onlineSite: onlineSite,
      title: payload.title || '',
      cover: payload.cover || '',
      meta: payload.meta || '',
      rating: payload.rating || ''
    })
    favorited = true
  }
  uni.setStorageSync(STORAGE_KEYS.FAVORITE, list)
  return delay({ favorited })
}

/**
 * 删除收藏项
 */
export function removeFavorite(id) {
  let list = uni.getStorageSync(STORAGE_KEYS.FAVORITE) || []
  list = list.filter(i => i.id !== id)
  uni.setStorageSync(STORAGE_KEYS.FAVORITE, list)
  return delay(true)
}

/**
 * 离线缓存列表（本地存储）
 */
export function fetchOfflineList() {
  return delay((uni.getStorageSync(STORAGE_KEYS.OFFLINE) || []).map(i => ({ ...i })))
}

/**
 * 添加离线缓存
 */
export function addOfflineItem(payload) {
  let list = uni.getStorageSync(STORAGE_KEYS.OFFLINE) || []
  const idx = list.findIndex(i => i.id === payload.id)
  const now = new Date()
  const time = (now.getMonth() + 1) + '月' + now.getDate() + '日'
  if (idx < 0) {
    list.unshift({
      id: payload.id,
      title: payload.title || '',
      cover: payload.cover || '',
      meta: payload.meta || '',
      size: payload.size || '未知',
      progress: 0,
      status: 'downloading',
      time
    })
    uni.setStorageSync(STORAGE_KEYS.OFFLINE, list)
  }
  return delay(true)
}

/**
 * 更新离线缓存下载进度
 */
export function updateOfflineProgress(id, progress, status) {
  let list = uni.getStorageSync(STORAGE_KEYS.OFFLINE) || []
  const idx = list.findIndex(i => i.id === id)
  if (idx >= 0) {
    list[idx].progress = progress
    if (status) list[idx].status = status
    if (progress >= 100) list[idx].status = 'done'
    uni.setStorageSync(STORAGE_KEYS.OFFLINE, list)
  }
  return delay(true)
}

/**
 * 删除离线缓存
 */
export function removeOfflineItem(id) {
  let list = uni.getStorageSync(STORAGE_KEYS.OFFLINE) || []
  list = list.filter(i => i.id !== id)
  uni.setStorageSync(STORAGE_KEYS.OFFLINE, list)
  return delay(true)
}

/* ========================= 关于 ========================= */
/**
 * 关于页信息
 * GET /about/info
 */
export function fetchAboutInfo() {
  return delay({ ..._aboutInfo })
}

/**
 * 关于页菜单
 * GET /about/menu
 */
export function fetchAboutMenu() {
  return delay(_aboutMenu.map(i => ({ ...i })))
}

/**
 * APP 版本检查（仅 App 端有意义，H5/小程序也能调通但不会触发安装）
 * GET server.py /api/version
 * @returns {Promise<{versionName,versionCode,updateLog,forceUpdate,minSupport,apkUrl,apkUrlType}|null>}
 *
 * 返回字段说明：
 *   versionCode   数字版本号，用于比较（当前 < 服务器 → 有新版）
 *   forceUpdate   true 时不可跳过更新
 *   minSupport    低于此 versionCode 必须强制更新
 *   apkUrlType    "direct"=可直接下载安装, "share"=需打开系统浏览器
 */
export function fetchAppVersion() {
  return onlineRequest('/api/version')
    .then((res) => {
      if (!res || res.code !== 0 || !res.data) return null
      return res.data
    })
    .catch((err) => {
      console.warn('[online] version error', err)
      return null
    })
}

/* ========================= 全网视频（Python 爬虫后端） =========================
 * 由 server.py 提供，前端统一走 /__pyapi 代理（Vite 中间件）：
 *   GET /__pyapi/api/search?wd=关键词     → 聚合搜索
 *   GET /__pyapi/api/detail?id=12345      → 详情（线路+选集）
 *   GET /__pyapi/api/player?url=&title=   → 自带 hls.js 的 HTML 播放页（iframe 嵌入）
 *   GET /__pyapi/api/stream?url=<m3u8>    → 流代理（注入 Referer + 改写 m3u8）
 *
 * 采集站实测可用性（2026-08-04）：
 *   · ffzy（飞速资源）可用，需 Referer 头，返回 2 条线路（feifan 分享页 + ffm3u8 直链）
 *   · 量子/速播/黑喵等其它常见站点在当前沙箱内 DNS 失效或被 Cloudflare 拦截
 *   · B站官方搜索接口需要 cookie + 风控绕过，H5 端调用不稳定，已移除
 */

/**
 * 全网聚合搜索
 * @param {string} q 关键词
 * @returns {Promise<Array>} 统一结构：{ id, onlineSite, onlineSiteLabel, vodId, title, cover, meta, desc, tag, url }
 */
export function fetchOnlineSearch(q) {
  const keyword = (q || '').trim()
  if (!keyword) return Promise.resolve([])
  return onlineRequest('/api/search', { wd: keyword }, 'POST')
    .then((res) => {
      if (!res || res.code !== 0 || !Array.isArray(res.data)) return []
      return res.data
    })
    .catch((err) => {
      console.warn('[online] search error', err)
      return []
    })
}

/**
 * 短剧搜索：在短剧分类(t=36)内搜索
 */
export function fetchShortsSearch(q) {
  const keyword = (q || '').trim()
  if (!keyword) return Promise.resolve([])
  return onlineRequest('/api/shorts/search', { wd: keyword }, 'POST')
    .then((res) => {
      if (!res || res.code !== 0 || !Array.isArray(res.data)) return []
      return res.data
    })
    .catch((err) => {
      console.warn('[online] shorts search error', err)
      return []
    })
}

/**
 * 全网详情：拉取某 vod_id 的完整信息（含所有播放线路和集数）
 * @param {string|number} vodId  MacCMS vod_id
 * @param {string} [siteKey]     采集站 key（默认 ffzy）
 * @returns {Promise<Object|null>}
 *   {
 *     onlineSite, onlineSiteLabel, vodId,
 *     title, cover, year, area, actor, director, content, remarks, score, lang,
 *     lines: [{ index, flag, eps: [{name, url, direct: true/false}] }]
 *   }
 */
export function fetchOnlineDetail(vodId, siteKey) {
  if (!vodId) return Promise.resolve(null)
  const params = { id: String(vodId) }
  if (siteKey) params.site = siteKey
  return onlineRequest('/api/detail', params)
    .then((res) => {
      if (!res || res.code !== 0 || !res.data) return null
      return res.data
    })
    .catch((err) => {
      console.warn('[online] detail error', err)
      return null
    })
}

/**
 * 解析分享页 URL，返回真实 m3u8 直链
 * 用于 App/MP 端：非直链（分享页）先解析成 m3u8，再用原生 <video> 播放
 * @param {string} url 分享页地址或直链
 * @returns {Promise<string|null>} 真实 m3u8 直链，失败返回 null
 */
export function fetchOnlineResolve(url) {
  if (!url) return Promise.resolve(null)
  return onlineRequest('/api/resolve', { url })
    .then((res) => {
      if (!res || res.code !== 0 || !res.data || !res.data.url) return null
      return res.data.url
    })
    .catch((err) => {
      console.warn('[online] resolve error', err)
      return null
    })
}
