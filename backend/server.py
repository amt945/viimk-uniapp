#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VIIMK 视频爬虫后端
=====================================================
用 Python requests 直接请求 MacCMS v10 采集站接口，
绕过浏览器 CORS 限制，为前端提供统一的搜索/详情/播放 API。

采集站（实测可用）:
  ffzy  = 飞速资源  https://api.ffzyapi.com   (需 Referer)

接口:
  GET /api/search?wd=关键词             → 聚合搜索，合并去重
  GET /api/detail?id=12345              → 单站详情，返回线路+集数
  GET /api/stream?url=<m3u8/ts/mp4>     → 流代理：注入 Referer，H5 可直接 <video> 播
  GET /api/player?url=&title=           → 自带 hls.js 的 HTML 播放页（iframe 用）
  GET /api/health                       → 健康检查

设计要点：
  · MacCMS 采集站普遍不开放 CORS，H5 端无法直接调用 → Python 反代
  · m3u8/ts 直链需要 Referer 才能访问，且无 CORS 头 → Python 流代理
  · H5 桌面 Chrome 不原生支持 HLS → /api/player 内置 hls.js 播放页
"""

import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse, urljoin, quote, urlencode

import requests
from flask import Flask, jsonify, request as flask_request, Response, stream_with_context

app = Flask(__name__)

# ============ 采集站配置 ============
# 多源冗余：ffzy 为主源，其它为备源。搜索/详情自动并发拉取并合并去重；
# 列表接口在主源失败时自动尝试备源（_fetch_list_with_failover）。
# 2026-08-05 实测全部可用（搜索"庆余年"均返回 m3u8 直链）。
SITES = {
    "ffzy": {
        "label": "飞速",
        "base": "https://api.ffzyapi.com/api.php/provide/vod/",
        "referer": "https://api.ffzyapi.com/",
        "priority": 1,   # 主源，列表/首页优先用
    },
    "wuj": {
        "label": "无尽",
        "base": "https://api.wujinapi.com/api.php/provide/vod/",
        "referer": "https://api.wujinapi.com/",
        "priority": 2,
    },
    "lzi": {
        "label": "量子",
        "base": "https://cj.lziapi.com/api.php/provide/vod/",
        "referer": "https://cj.lziapi.com/",
        "priority": 3,
    },
    "bdz": {
        "label": "百度云",
        "base": "https://api.apibdzy.com/api.php/provide/vod/",
        "referer": "https://api.apibdzy.com/",
        "priority": 4,
    },
    "ffzy2": {
        "label": "飞速2",
        "base": "https://cj.ffzyapi.com/api.php/provide/vod/",
        "referer": "https://cj.ffzyapi.com/",
        "priority": 5,
    },
}

# 列表/首页用的有序源（按 priority 排序），主源失败时按序切换
_LIST_SOURCES = sorted(
    [(k, v) for k, v in SITES.items()],
    key=lambda kv: kv[1].get("priority", 99)
)
_LIST_SOURCE_KEYS = [k for k, _ in _LIST_SOURCES]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "application/json, */*",
    "Accept-Language": "zh-CN,zh;q=0.9",
}

TIMEOUT = 10


# ============ 工具函数 ============
def is_direct_play_url(url):
    """判断是否为直链（.m3u8/.mp4 等）"""
    if not url:
        return False
    u = url.strip().lower()
    if not u:
        return False
    if re.search(r"\.(m3u8|mp4|flv|ts|mov|mkv|avi|webm|aac|mp3)(\?|#|$)", u):
        return True
    if "/hls/" in u or "/live/" in u:
        if not re.search(r"\.(php|jsp|asp|aspx)(\?|#|$)", u):
            return True
    return False


def parse_lines(vod):
    """解析 MacCMS 的 vod_play_from / vod_play_url 为结构化线路"""
    from_str = str(vod.get("vod_play_from", "")).strip()
    url_str = str(vod.get("vod_play_url", "")).strip()
    if not from_str or not url_str:
        return []

    flags = [s.strip() for s in from_str.split("$$$") if s.strip()]
    line_strs = [s.strip() for s in url_str.split("$$$")]
    lines = []
    for i in range(min(len(flags), len(line_strs))):
        flag = flags[i]
        ep_str = line_strs[i] or ""
        if not ep_str:
            continue
        eps = []
        for kv in ep_str.split("#"):
            if not kv:
                continue
            idx = kv.find("$")
            if idx < 0:
                name, url = kv.strip(), ""
            else:
                name = kv[:idx].strip() or "播放"
                url = kv[idx + 1:].strip()
            if url:
                eps.append({"name": name, "url": url, "direct": is_direct_play_url(url)})
        if eps:
            lines.append({"index": i, "flag": flag, "eps": eps})
    return lines


def format_item(vod, site_key, site_label):
    """把 MacCMS vod 格式化为前端统一结构（含列表页和详情页所需全部字段）"""
    if not vod or not vod.get("vod_id"):
        return None
    pic = str(vod.get("vod_pic") or vod.get("vod_pic_thumb") or vod.get("vod_pic_slide") or "").strip()
    cover = ("https:" + pic) if pic.startswith("//") else pic
    title = str(vod.get("vod_name", "")).strip()
    if not title:
        return None

    year = str(vod.get("vod_year", "")).strip() if vod.get("vod_year") else ""
    area = str(vod.get("vod_area", "")).strip() if vod.get("vod_area") else ""
    genre = str(vod.get("type_name", "")).strip() if vod.get("type_name") else ""
    remarks = str(vod.get("vod_remarks", "")).strip() if vod.get("vod_remarks") else ""
    score = str(vod.get("vod_douban_score", "")).strip() if vod.get("vod_douban_score") else ""

    # meta：年份 · 地区 · 状态（不含评分，评分单独给字段）
    meta_parts = [p for p in (year, area, remarks) if p]
    meta = " · ".join(meta_parts)

    content = re.sub(r"<[^>]+>", "", str(vod.get("vod_content", "")))[:100]
    actor = vod.get("vod_actor", "")
    desc = content or ("主演：" + str(actor) if actor else "")

    return {
        "id": "online:" + site_key + ":" + str(vod["vod_id"]),
        "onlineSite": site_key,
        "onlineSiteLabel": site_label,
        "vodId": str(vod["vod_id"]),
        "title": title,
        "cover": cover,
        "year": year,
        "area": area,
        "genre": genre,
        "remarks": remarks,
        "score": score,
        "rating": score or "0.0",
        "meta": meta,
        "desc": desc,
        "tag": genre or (site_label + "站"),
        "url": "",
    }


def fetch_site_search(site_key, wd, t=None):
    """请求单个采集站搜索接口，t 为分类 ID（可选）"""
    site = SITES.get(site_key)
    if not site:
        return []
    try:
        params = {"ac": "videolist", "wd": wd, "pg": 1}
        if t:
            params["t"] = t
        headers = dict(HEADERS)
        headers["Referer"] = site["referer"]
        resp = requests.get(site["base"], params=params, headers=headers, timeout=20)
        data = resp.json()
        raw_list = data.get("list", [])
        if not raw_list and isinstance(data.get("vod"), dict):
            raw_list = data["vod"].get("list", [])
        items = []
        for v in raw_list:
            item = format_item(v, site_key, site["label"])
            if item:
                items.append(item)
        return items
    except Exception as e:
        print(f"[search] {site_key} error: {e}")
        return []


def fetch_site_detail(site_key, vod_id):
    """请求单个采集站详情接口"""
    site = SITES.get(site_key)
    if not site:
        return None
    try:
        params = {"ac": "detail", "ids": str(vod_id)}
        headers = dict(HEADERS)
        headers["Referer"] = site["referer"]
        resp = requests.get(site["base"], params=params, headers=headers, timeout=TIMEOUT)
        data = resp.json()
        raw_list = data.get("list", [])
        if not raw_list and isinstance(data.get("vod"), dict):
            raw_list = data["vod"].get("list", [])
        if not raw_list:
            return None
        v = raw_list[0]

        pic = str(v.get("vod_pic") or v.get("vod_pic_thumb") or v.get("vod_pic_slide") or "").strip()
        cover = ("https:" + pic) if pic.startswith("//") else pic
        lines = parse_lines(v)

        return {
            "onlineSite": site_key,
            "onlineSiteLabel": site["label"],
            "vodId": str(v.get("vod_id", vod_id)),
            "title": str(v.get("vod_name", "")).strip(),
            "cover": cover,
            "year": str(v.get("vod_year", "")) if v.get("vod_year") else "",
            "area": str(v.get("vod_area", "")) if v.get("vod_area") else "",
            "actor": str(v.get("vod_actor", "")) if v.get("vod_actor") else "",
            "director": str(v.get("vod_director", "")) if v.get("vod_director") else "",
            "content": re.sub(r"<[^>]+>", "", str(v.get("vod_content", ""))),
            "remarks": str(v.get("vod_remarks", "")) if v.get("vod_remarks") else "",
            "score": str(v.get("vod_douban_score", "")) if v.get("vod_douban_score") else "",
            "lang": str(v.get("vod_lang", "")) if v.get("vod_lang") else "",
            "lines": lines,
        }
    except Exception as e:
        print(f"[detail] {site_key} error: {e}")
        return None


def guess_referer(url):
    """根据直链域名猜测 Referer（m3u8 直链需带 Referer 否则 403）"""
    p = urlparse(url)
    host = p.netloc or ""
    # ffzy 系列资源站（api.ffzyapi / cj.ffzyapi / ffeiimg / ffzy-plays）
    if "ffzy" in host or "ffeiimg" in host or "ffzy-plays" in host:
        return "https://api.ffzyapi.com/"
    # 无尽资源站
    if "wujinapi" in host or "wujinzy" in host:
        return "https://api.wujinapi.com/"
    # 量子资源站
    if "lziapi" in host or "lzizy" in host:
        return "https://cj.lziapi.com/"
    # 百度云资源站
    if "apibdzy" in host or "bdzy" in host:
        return "https://api.apibdzy.com/"
    # 通用：用同源根
    if host:
        return f"{p.scheme}://{host}/"
    return "https://www.google.com/"


def resolve_share_url(share_url):
    """解析 ffzy 分享页，提取真实 m3u8 直链。
    分享页 HTML 形如： const url = "/20260224/xxx/index.m3u8?sign=...";
    拼接分享页 origin 即得完整直链。
    返回 m3u8 绝对 URL，失败返回 None。
    """
    try:
        headers = dict(HEADERS)
        headers["Referer"] = guess_referer(share_url)
        resp = requests.get(share_url, headers=headers, timeout=TIMEOUT)
        if resp.status_code != 200:
            return None
        text = resp.text
        # 匹配 const url = "..."  （ffzy 分享页固定写法）
        m = re.search(r'''const\s+url\s*=\s*["']([^"']+)["']''', text)
        if not m:
            # 兜底：直接找 m3u8
            m2 = re.search(r'(https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*)', text)
            if m2:
                return m2.group(1)
            return None
        raw = m.group(1)
        # 拼接为绝对 URL
        return urljoin(share_url, raw)
    except Exception as e:
        print(f"[resolve] {share_url} error: {e}")
        return None


# ============ 列表 / 分类 ============
# MacCMS 采集站分类映射：ffzy 有独立的"短剧"分类 type_id=36（pid=2 连续剧下），
# 共近 2 万条真短剧。短剧题材无子分类，用 t=36 + wd 关键词做题材筛选。
# 数字 tab code → (t, wd)：前端传 tab=数字，后端映射，避免中文出现在 URL 里。
SHORTS_TAB_MAP = {
    0: {"name": "推荐", "t": 36, "wd": None},    # 全部最新短剧
    1: {"name": "总裁", "t": 36, "wd": "总裁"},
    2: {"name": "穿越", "t": 36, "wd": "穿越"},
    3: {"name": "重生", "t": 36, "wd": "重生"},
    4: {"name": "战神", "t": 36, "wd": "战神"},
    5: {"name": "逆袭", "t": 36, "wd": "逆袭"},
    6: {"name": "赘婿", "t": 36, "wd": "赘婿"},
}

# 片库分类 tab → type_id（ffzy 顶级分类 t=1/2/3 返回空，必须用子分类）
# 注：片库不放"短剧" tab（短剧有独立的底部入口），避免重复入口
LIBRARY_TAB_MAP = {
    "全部": None,
    "电影": 6,         # 动作片
    "电视剧": 13,      # 国产剧
    "综艺": 25,        # 大陆综艺
    "动漫": 29,        # 国产动漫
    "纪录片": 20,
}

# 首页分类 tab → type_id（首页 5 个 tab：推荐=最新全部，其它映射到 ffzy 子分类）
HOME_TAB_MAP = {
    "推荐": None,      # 最新全部
    "热播": None,      # 同上（ffzy 无热度排序）
    "都市": 13,        # 国产剧
    "古装": 13,
    "悬疑": 6,         # 动作片（悬疑题材多在动作片分类）
}


def fetch_site_categories(site_key):
    """获取采集站顶级分类列表"""
    site = SITES.get(site_key)
    if not site:
        return []
    try:
        headers = dict(HEADERS)
        headers["Referer"] = site["referer"]
        resp = requests.get(site["base"], params={"ac": "list"},
                            headers=headers, timeout=TIMEOUT)
        data = resp.json()
        cls = data.get("class", []) or []
        # 顶级分类（type_pid == 0）
        return [{"id": c.get("type_id"), "name": c.get("type_name")}
                for c in cls if c.get("type_pid", 0) == 0]
    except Exception as e:
        print(f"[categories] {site_key} error: {e}")
        return []


def fetch_site_list(site_key, t=None, pg=1, h=None, wd=None):
    """请求采集站视频列表（ac=videolist）
    返回 (items, pagecount, total)
    沙箱代理偶发 ProxyError，重试 2 次保证分类切换稳定。
    wd: 关键词搜索（ffzy 支持 ac=videolist&wd=xxx，可与 t 组合做题材筛选）
    """
    site = SITES.get(site_key)
    if not site:
        return [], 1, 0
    params = {"ac": "videolist", "pg": pg}
    if t:
        params["t"] = t
    if h:
        params["h"] = h  # 最近 h 小时更新
    if wd:
        params["wd"] = wd
    headers = dict(HEADERS)
    headers["Referer"] = site["referer"]

    import time as _tm
    last_err = None
    for attempt in range(3):
        try:
            resp = requests.get(site["base"], params=params,
                                headers=headers, timeout=TIMEOUT)
            data = resp.json()
            raw_list = data.get("list", []) or []
            if not raw_list and isinstance(data.get("vod"), dict):
                raw_list = data["vod"].get("list", []) or []
            items = []
            for v in raw_list:
                it = format_item(v, site_key, site["label"])
                if it:
                    items.append(it)
            pagecount = int(data.get("pagecount", 1) or 1)
            total = int(data.get("total", len(items)) or 0)
            return items, pagecount, total
        except Exception as e:
            last_err = e
            if attempt < 2:
                _tm.sleep(0.4)
    print(f"[list] {site_key} error after retries: {last_err}")
    return [], 1, 0


def fetch_list_with_failover(t=None, pg=1, h=None, wd=None, prefer_key=None):
    """列表带故障切换：优先用 prefer_key（默认按 priority 主源），
    主源失败/空结果时自动按 _LIST_SOURCE_KEYS 顺序尝试备源。
    返回 (items, pagecount, total, used_site_key)。
    """
    # 构造尝试顺序：prefer_key 优先，其余按 priority
    if prefer_key and prefer_key in SITES:
        order = [prefer_key] + [k for k in _LIST_SOURCE_KEYS if k != prefer_key]
    else:
        order = list(_LIST_SOURCE_KEYS)

    last_err = None
    for key in order:
        try:
            items, pagecount, total = fetch_site_list(key, t=t, pg=pg, h=h, wd=wd)
            # 空结果视为失败，继续切下一个源（除非已经是最后一个）
            if items:
                return items, pagecount, total, key
            # 空结果但不报错：记住此源尝试过，继续切换
            print(f"[list-failover] {key} 返回空，切换下一源", flush=True)
        except Exception as e:
            last_err = e
            print(f"[list-failover] {key} 异常: {e}，切换下一源", flush=True)

    # 所有源都失败
    if last_err:
        print(f"[list-failover] 所有源均失败: {last_err}", flush=True)
    return [], 1, 0, None


def fetch_detail_with_failover(vod_id, prefer_key=None):
    """详情多源查找：
    1. 如果 prefer_key 指定，先查它
    2. 否则按 priority 顺序逐个尝试，直到返回有效数据
    返回 (data, used_site_key) 或 (None, None)。
    """
    if prefer_key and prefer_key in SITES:
        order = [prefer_key] + [k for k in _LIST_SOURCE_KEYS if k != prefer_key]
    else:
        order = list(_LIST_SOURCE_KEYS)

    for key in order:
        try:
            data = fetch_site_detail(key, vod_id)
            if data and data.get("lines"):
                # 更新 site 标识为实际命中的源
                data["onlineSite"] = key
                data["onlineSiteLabel"] = SITES[key]["label"]
                return data, key
            print(f"[detail-failover] {key} 无有效数据，切换下一源", flush=True)
        except Exception as e:
            print(f"[detail-failover] {key} 异常: {e}，切换下一源", flush=True)
    return None, None


# ============ API 路由 ============
@app.after_request
def add_cors(resp):
    """统一补 CORS 头"""
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "*"
    return resp


@app.route("/<path:any_path>", methods=["OPTIONS"])
@app.route("/", methods=["OPTIONS"])
def cors_preflight(any_path=None):
    """CORS 预检统一放行（POST application/json 会触发 preflight）"""
    return ("", 204)


@app.route("/api/health")
def health():
    return jsonify({"code": 0, "msg": "ok", "sites": list(SITES.keys())})


# ============ APP 版本升级（蓝奏云） ============
# 版本信息配置：APK 放蓝奏云文件夹，server.py 自动从文件夹里取最新 APK。
# 发版流程：把新 APK 上传到下面的蓝奏云文件夹 → 修改 VERSION_CONFIG 即可，
# 无需手动改分享链接（程序会自动从文件夹里挑版本号最大的 APK）。
#
# 注意：VERSION_CONFIG 里的 versionName/versionCode 仍需手动维护，
# 用于客户端版本对比；updateLog 用于弹窗展示更新日志。
VERSION_CONFIG = {
    "versionName": "1.0.0",
    "versionCode": 100,
    "updateLog": "首发版本",
    "forceUpdate": False,    # 是否强制更新
    "minSupport": 100,       # 低于此 versionCode 强制更新
}
# 蓝奏云文件夹分享（自动取最新 APK）
LANZO_FOLDER_URL = "https://wwbnc.lanzoub.com/b01ve2244f"
LANZO_FOLDER_PWD = "4lot"

# 直链缓存（蓝奏云直链会过期，缓存 10 分钟避免重复解析被风控）
_LANZO_DIRECT_CACHE = {"url": "", "ts": 0}
_LANZO_DIRECT_TTL = 600
# 文件夹解析缓存（文件夹内容变化少，缓存 30 分钟，避免频繁列目录被风控）
_LANZO_FOLDER_CACHE = {"files": None, "ts": 0}
_LANZO_FOLDER_TTL = 1800


def _lanzo_host(share_url):
    """从分享 URL 提取 origin（如 https://wwbnc.lanzoub.com）
    蓝奏云 ajaxm.php 必须用与分享页同域名请求，否则 sign 校验失败。
    """
    p = urlparse(share_url)
    return f"{p.scheme}://{p.netloc}"


def parse_lanzo_folder(folder_url, pwd=""):
    """解析蓝奏云文件夹分享，返回文件列表。
    流程：
      1. GET 文件夹分享页，提取 fid / uid / puid / t / k（防爬参数）
      2. POST {host}/filemoreajax.php?file=fid 拿文件列表
    返回 [{"id":"iXyZ12abc", "name":"viimk-1.0.1.apk", "size":"20.5M", "time":"..."}]
    失败返回 None。

    注意：蓝奏云文件夹分享页用 /filemoreajax.php 接口（非 /ajaxm.php），
    且 t / k 是动态变量名（每次刷新分享页变量名都变），需要先从 data 块
    里拿到变量名，再去 var 声明里取值。
    """
    if not folder_url or "lanzou" not in folder_url:
        return None
    try:
        host = _lanzo_host(folder_url)
        headers = dict(HEADERS)
        headers["Referer"] = folder_url
        headers["Accept"] = "text/html,application/xhtml+xml,*/*"
        # 1) GET 文件夹分享页
        resp = requests.get(folder_url, headers=headers, timeout=15, allow_redirects=True)
        if resp.status_code != 200:
            return None
        text = resp.text

        # 2) 提取防爬参数
        # fid: 'fid':13820585 （数字，可能不带引号）
        m = re.search(r"['\"]fid['\"]?\s*[:=]\s*['\"]?(\d+)", text)
        fid = m.group(1) if m else None
        if not fid:
            return None
        # uid: 'uid':'630719'
        m = re.search(r"['\"]uid['\"]?\s*[:=]\s*['\"](\w+)['\"]", text)
        uid = m.group(1) if m else ""
        # puid: 'puid':'xxxx'
        m = re.search(r"['\"]puid['\"]?\s*[:=]\s*['\"]([^'\"]+)['\"]", text)
        puid = m.group(1) if m else ""
        # t: 't':变量名  →  var 变量名 = '值'（变量名随机，如 ib01b9）
        t_val = ""
        m = re.search(r"['\"]t['\"]?\s*[:=]\s*(\w+)\s*[,)]", text)
        if m:
            t_var = m.group(1)
            m2 = re.search(r"var\s+" + re.escape(t_var) + r"\s*=\s*['\"]([^'\"]+)['\"]", text)
            if m2:
                t_val = m2.group(1)
        # k: 'k':变量名  →  var 变量名 = '值'
        k_val = ""
        m = re.search(r"['\"]k['\"]?\s*[:=]\s*(\w+)\s*[,)]", text)
        if m:
            k_var = m.group(1)
            m2 = re.search(r"var\s+" + re.escape(k_var) + r"\s*=\s*['\"]([^'\"]+)['\"]", text)
            if m2:
                k_val = m2.group(1)

        # 3) POST filemoreajax.php 拿文件列表
        post_data = {
            "lx": 2,
            "fid": fid,
            "uid": uid,
            "puid": puid,
            "pg": 1,
            "rep": "0",
            "t": t_val,
            "k": k_val,
            "up": 1,
            "ls": 1,
            "pwd": pwd or "",
        }
        post_headers = dict(headers)
        post_headers["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8"
        post_headers["X-Requested-With"] = "XMLHttpRequest"
        api_url = host + "/filemoreajax.php?file=" + fid
        api_resp = requests.post(api_url, data=post_data, headers=post_headers, timeout=15)
        info = api_resp.json()
        # zt: '1'=成功 '2'=无文件 '3'=密码错误
        if str(info.get("zt", "")) != "1":
            print(f"[lanzo] folder zt={info.get('zt')} info={info.get('info', '')}")
            return None
        raw_list = info.get("text") or []
        files = []
        for f in raw_list:
            file_id = f.get("id")
            name = f.get("name_all") or f.get("name") or ""
            if not file_id or file_id == "-1":
                continue
            files.append({
                "id": str(file_id),
                "name": name,
                "size": f.get("size", ""),
                "time": f.get("time", ""),
            })
        return files if files else None
    except Exception as e:
        print(f"[lanzo] folder parse error: {e}")
        return None


def pick_latest_apk(files):
    """从文件列表里挑版本号最大的 APK。
    文件名形如 viimk-1.0.1.apk / viimk_1.0.10.apk，按数字版本号降序排。
    返回 {id, name, ...} 或 None。
    """
    if not files:
        return None
    apks = [f for f in files if f.get("name", "").lower().endswith(".apk")]
    if not apks:
        return None

    def version_key(f):
        m = re.search(r"(\d+(?:\.\d+)+)", f.get("name", ""))
        if not m:
            return tuple()
        return tuple(int(x) for x in m.group(1).split("."))

    apks.sort(key=lambda f: (version_key(f), f.get("name", "")), reverse=True)
    return apks[0]


def parse_lanzo_direct(share_url):
    """解析蓝奏云单文件分享链接，返回真实下载直链。
    蓝奏云分享页结构：
      - 分享页 HTML 里有 <iframe src="/fn?xxx"> 或直接含 sign
      - POST {host}/ajaxm.php?action=downprocess&sign=xxx 返回
        dom（直链前缀）+ url（直链后缀），拼接即得可下载直链。
    api_url 跟随分享页域名（兼容 wwa.lanzoui / wwbnc.lanzoub 等）。
    失败返回 None。
    """
    if not share_url or "lanzou" not in share_url:
        return None
    try:
        host = _lanzo_host(share_url)
        headers = dict(HEADERS)
        headers["Referer"] = share_url
        # 1) 拉分享页，提取 sign / 下页面参数
        resp = requests.get(share_url, headers=headers, timeout=15, allow_redirects=True)
        if resp.status_code != 200:
            return None
        text = resp.text
        # 兼容两种格式：旧版直接在 HTML 里有 'sign':'xxxx'，新版用 iframe 跳 /fn?xxx
        sign = None
        m = re.search(r"['\"]sign['\"]\s*[:=]\s*['\"]([^'\"]+)['\"]", text)
        if m:
            sign = m.group(1)
        websign = None
        m = re.search(r"['\"]websign['\"]\s*[:=]\s*['\"]([^'\"]*)['\"]", text)
        if m:
            websign = m.group(1)
        ves = None
        m = re.search(r"['\"]ves['\"]\s*[:=]\s*['\"]([^'\"]*)['\"]", text)
        if m:
            ves = m.group(1)
        if not sign:
            # 兜底：找 /fn? 跳转链接（部分版本用 iframe）
            m = re.search(r'<iframe[^>]+src=["\']([^"\']*/fn\?[^"\']+)["\']', text)
            if m:
                fn_url = urljoin(share_url, m.group(1))
                resp2 = requests.get(fn_url, headers=headers, timeout=15, allow_redirects=True)
                text2 = resp2.text
                m = re.search(r"['\"]sign['\"]\s*[:=]\s*['\"]([^'\"]+)['\"]", text2)
                if m:
                    sign = m.group(1)
                m = re.search(r"['\"]websign['\"]\s*[:=]\s*['\"]([^'\"]*)['\"]", text2)
                if m:
                    websign = m.group(1)
                m = re.search(r"['\"]ves['\"]\s*[:=]\s*['\"]([^'\"]*)['\"]", text2)
                if m:
                    ves = m.group(1)
        if not sign:
            return None

        # 2) POST ajaxm.php 拿真实直链（api_url 跟随分享页域名）
        api_url = host + "/ajaxm.php"
        post_data = {
            "action": "downprocess",
            "sign": sign,
            "ves": ves or "",
            "p": "",
            "audiess": "",
        }
        if websign:
            post_data["websign"] = websign
            post_data["websignkey"] = ""
        post_headers = dict(headers)
        post_headers["Content-Type"] = "application/x-www-form-urlencoded"
        post_headers["X-Requested-With"] = "XMLHttpRequest"
        api_resp = requests.post(api_url, data=post_data, headers=post_headers, timeout=15)
        info = api_resp.json()
        dom = info.get("dom", "")
        url_token = info.get("url", "")
        # dom 形如 https://developerallocate-zjzx3.kuaihome.cn:1133
        # url 形如 /file/?xxxx   →  完整直链 = dom + url
        if dom and url_token:
            full = dom + url_token if url_token.startswith("/") else dom + "/" + url_token
            return full
        return None
    except Exception as e:
        print(f"[lanzo] parse error: {e}")
        return None


def get_lanzo_apk_info():
    """获取最新 APK 信息（带缓存）。
    流程：解析文件夹 → 取最新 APK → 尝试解析直链。
    两层缓存：文件夹列表缓存 30 分钟，直链缓存 10 分钟。

    返回 {"share_url": "单文件分享链接", "direct_url": "直链 or None", "name": "文件名"}
    失败返回 None。
    """
    now = time.time()

    # 1) 解析文件夹拿最新 APK（带缓存）
    if _LANZO_FOLDER_CACHE["files"] is None or \
       (now - _LANZO_FOLDER_CACHE["ts"]) > _LANZO_FOLDER_TTL:
        files = parse_lanzo_folder(LANZO_FOLDER_URL, LANZO_FOLDER_PWD)
        if files:
            _LANZO_FOLDER_CACHE["files"] = files
            _LANZO_FOLDER_CACHE["ts"] = now
        else:
            return None
    files = _LANZO_FOLDER_CACHE["files"]
    apk = pick_latest_apk(files)
    if not apk:
        return None

    # 2) 拼单文件分享链接
    share_url = _lanzo_host(LANZO_FOLDER_URL) + "/" + apk["id"]

    # 3) 尝试解析直链（带缓存）
    #    蓝奏云单文件分享页有 arg1 JS 混淆反爬，可能解析失败 → 调用方需处理 None
    if _LANZO_DIRECT_CACHE["url"] and (now - _LANZO_DIRECT_CACHE["ts"]) < _LANZO_DIRECT_TTL:
        direct_url = _LANZO_DIRECT_CACHE["url"]
    else:
        direct_url = parse_lanzo_direct(share_url)
        if direct_url:
            _LANZO_DIRECT_CACHE["url"] = direct_url
            _LANZO_DIRECT_CACHE["ts"] = now

    return {
        "share_url": share_url,
        "direct_url": direct_url,
        "name": apk["name"],
    }


@app.route("/api/version")
def app_version():
    """APP 版本检查接口
    自动从蓝奏云文件夹里取最新 APK。
    蓝奏云单文件分享页有 JS 混淆反爬，直链解析可能失败 → 回退到单文件分享链接，
    客户端用 plus.runtime.openURL 打开浏览器下载。

    返回结构：
      {
        code: 0,
        data: {
          versionName, versionCode, updateLog,
          forceUpdate, minSupport,
          apkUrl,        # 直链（解析成功）或单文件分享链接（解析失败时兜底）
          apkUrlType,    # "direct"=可直接下载 | "share"=需打开浏览器
          apkFileName    # 选中的 APK 文件名（便于客户端展示/调试）
        }
      }
    """
    data = dict(VERSION_CONFIG)
    apk_info = get_lanzo_apk_info()
    if apk_info:
        data["apkFileName"] = apk_info["name"]
        if apk_info["direct_url"]:
            data["apkUrl"] = apk_info["direct_url"]
            data["apkUrlType"] = "direct"
        else:
            # 直链解析失败（蓝奏云 arg1 混淆）→ 返回单文件分享链接，客户端打开浏览器
            data["apkUrl"] = apk_info["share_url"]
            data["apkUrlType"] = "share"
    else:
        # 文件夹解析失败或无 APK → 返回文件夹链接
        data["apkUrl"] = LANZO_FOLDER_URL
        data["apkUrlType"] = "share"
        data["apkFileName"] = ""
    return jsonify({"code": 0, "data": data})


@app.route("/api/categories")
def categories():
    """片库分类列表
    返回前端固定的 tab 名称 + 对应 type_id，保证 UI 一致性。
    """
    cats = [{"name": k, "typeId": v} for k, v in LIBRARY_TAB_MAP.items()]
    return jsonify({"code": 0, "data": cats})


import threading as _thr

# ============ 首页缓存（进程级，避免每次都爬） ============
_HOME_CACHE = None        # 缓存值
_HOME_CACHE_AT = 0        # 缓存时间戳（秒）
_HOME_CACHE_TTL = 60      # 60 秒过期，保证内容"新鲜"但不频繁爬
_HOME_LOCK = _thr.Lock()  # 避免并发请求时重复爬


def _build_home_from_items(items1, items2=None):
    """把采集站列表数据构造成首页结构"""
    def to_hot(it):
        return {"id": it["id"], "title": it["title"], "cover": it["cover"],
                "tag": it.get("remarks") or it.get("tag") or "",
                "onlineSite": it["onlineSite"], "vodId": it["vodId"]}

    def to_foryou(it):
        return {"id": it["id"], "title": it["title"], "cover": it["cover"],
                "desc": it.get("desc") or "",
                "tag": it.get("genre") or it.get("tag") or "",
                "score": (it.get("score") or "0.0") + "分",
                "onlineSite": it["onlineSite"], "vodId": it["vodId"]}

    hero_raw = items1[0] if items1 else None
    hero = None
    if hero_raw:
        hero = {
            "id": hero_raw["id"],
            "title": hero_raw["title"],
            "cover": hero_raw["cover"],
            "year": hero_raw.get("year", ""),
            "genre": hero_raw.get("genre", ""),
            "region": hero_raw.get("area", ""),
            "score": hero_raw.get("score") or "0.0",
            "tag": hero_raw.get("remarks") or "热门",
            "onlineSite": hero_raw["onlineSite"],
            "vodId": hero_raw["vodId"],
        }

    hot = [to_hot(it) for it in items1[1:7]]
    # forYou：优先用 items2 第 2 页；如果 items2 没有就从 items1 后半截取（一页通常 20 条，够切）
    fy_pool = items2 if items2 and len(items2) >= 6 else items1[6:]
    foryou = [to_foryou(it) for it in (fy_pool or [])[:6]]

    return {
        "hero": hero, "hot": hot, "forYou": foryou,
        "categories": ["推荐", "热播", "都市", "古装", "悬疑"],
    }


@app.route("/api/home")
def home():
    """首页接口（复用同一路径承载两种语义，避免 uni vite 插件拦截带下划线/斜杠的子路径）：
      1) 聚合模式：GET /api/home          → hero+hot+forYou+categories（首屏）
      2) 分页模式：GET /api/home?pg=N&cat=xxx → 热门推荐无限滚动列表（每页6条）

    聚合模式优化：
      1) 1 页（20条）就够切 hero+hot+foryou，不再串行爬 2 页
      2) 进程级 60 秒缓存，避免每次都远程爬
      3) 线程池并发兜底：若缓存过期并发爬，只让一个线程爬
    """
    # —— 分页模式：带 pg 参数走无限滚动列表 ——
    # 参数优先级：t（数字 type_id，ASCII 安全）> cat（中文分类名）
    # 说明：uni-app vite 插件会拦截 URL 里带中文 query 的请求返回 400，
    #       所以前端统一传 t（数字），避免中文 cat 出现在 URL 里。
    pg_arg = flask_request.args.get("pg", "").strip()
    if pg_arg:
        try:
            pg = int(pg_arg) or 1
        except ValueError:
            pg = 1
        # t 参数：数字 type_id（推荐/热播传 0 或不传，表示最新全部）
        t_arg = flask_request.args.get("t", "").strip()
        if t_arg:
            try:
                t = int(t_arg) or None
            except ValueError:
                t = None
        else:
            # 兜底：未传 t 时按中文 cat 映射（curl 测试用）
            cat = flask_request.args.get("cat", "").strip() or "推荐"
            t = HOME_TAB_MAP.get(cat)
        items, has_more = fetch_home_paged_by_t(t, pg)
        return jsonify({"code": 0, "data": {
            "list": items, "page": pg, "hasMore": has_more,
        }})

    # —— 聚合模式：无 pg 参数走首屏聚合 ——
    import time as _tm
    now = int(_tm.time())
    global _HOME_CACHE, _HOME_CACHE_AT

    # 1) 缓存命中直接返回（无锁，读 path 最快）
    if _HOME_CACHE is not None and (now - _HOME_CACHE_AT) < _HOME_CACHE_TTL:
        return jsonify({"code": 0, "data": _HOME_CACHE})

    # 2) 缓存过期：加锁只让一个线程爬，其它阻塞等结果
    with _HOME_LOCK:
        # double-check：拿到锁时别的线程可能已经刷新完了
        if _HOME_CACHE is not None and (now - _HOME_CACHE_AT) < _HOME_CACHE_TTL:
            return jsonify({"code": 0, "data": _HOME_CACHE})

        site_key = "ffzy"
        # 优化：只请求 1 页（默认 20 条），切 hero(1) + hot(6) + forYou(6)
        # 复用 _fetch_native_cached 与片库/首页分页共享缓存，
        # 避免首页聚合和热门推荐分页重复爬同一页 ffzy 数据
        items1, _, _ = _fetch_native_cached(None, 1)
        data = _build_home_from_items(items1)
        _HOME_CACHE = data
        _HOME_CACHE_AT = int(_tm.time())
        return jsonify({"code": 0, "data": data})


@app.route("/api/list")
def vlist():
    """片库列表：按分类 tab 分页
    参数:
      cat = 分类名（全部/电影/电视剧/短剧/综艺/动漫/纪录片）
      t   = 数字 type_id（优先级高于 cat，避免中文 URL 被 uni-app vite 插件拦截）
      pg  = 页码（默认1）
    """
    pg = int(flask_request.args.get("pg", "1") or "1")
    # 优先用数字 t 参数（前端传），避免中文 cat 出现在 URL 里
    t_arg = flask_request.args.get("t", "").strip()
    if t_arg:
        try:
            t = int(t_arg) or None
        except ValueError:
            t = None
    else:
        # 兜底：未传 t 时按中文 cat 映射（curl 测试用）
        cat = flask_request.args.get("cat", "").strip() or "全部"
        t = LIBRARY_TAB_MAP.get(cat)
    # 复用首页 _fetch_native_cached：按 (t, pg) 缓存 90 秒
    # 片库每页 20 条 = ffzy 原生页大小，缓存键直接用 (t, pg) 即可
    # 避免每次分类切换/触底都远程爬 ffzy（3-10s/次，浏览器 15s 会超时）
    items, pagecount, total = _fetch_native_cached(t, pg)
    return jsonify({"code": 0, "data": {
        "list": items, "page": pg, "pagecount": pagecount,
        "total": total, "hasMore": pg < pagecount,
    }})


# 首页"热门推荐"无限滚动：每页固定 6 条（2 行 x 3 列）
# ffzy 原生每页 20 条，这里做虚拟分页，把 20/页 切成 6/页，
# 跨 ffzy 页边界时自动拼接，保证前端每次触底都能拿到完整 6 条。
HOME_PAGE_SIZE = 6
FFZY_PAGE_SIZE = 20  # ffzy videolist 默认每页 20 条

# ffzy 原生页面缓存：按 (t, native_pg) 缓存 90 秒。
# 触底加载时 pg=1/2/3/4 会复用同一个 ffzy 页（20条切4段），缓存避免重复爬慢页。
_NATIVE_PAGE_CACHE = {}
_NATIVE_PAGE_TTL = 90


def _fetch_native_cached(t, native_pg, wd=None):
    """带缓存的列表页拉取（主源 ffzy + 自动故障切换），返回 (items, pagecount, total)
    wd: 关键词搜索（短剧题材筛选用，与 t 组合）
    缓存命中时直接返回；未命中时走 fetch_list_with_failover，主源失败自动切备源。
    """
    key = (t, native_pg, wd)
    import time as _tm
    now = _tm.time()
    hit = _NATIVE_PAGE_CACHE.get(key)
    if hit and (now - hit[0]) < _NATIVE_PAGE_TTL:
        return hit[1], hit[2], hit[3]
    # 主源 ffzy 优先，失败自动切备源
    items, pagecount, total, used_key = fetch_list_with_failover(
        t=t, pg=native_pg, wd=wd, prefer_key="ffzy"
    )
    if used_key and used_key != "ffzy":
        print(f"[native-cache] 主源 ffzy 不可用，本页由 {used_key} 提供", flush=True)
    _NATIVE_PAGE_CACHE[key] = (now, items, pagecount, total)
    return items, pagecount, total


def fetch_home_paged(cat, our_pg):
    """首页无限滚动虚拟分页：每页 HOME_PAGE_SIZE 条
    返回 (items, has_more)
    """
    t = HOME_TAB_MAP.get(cat)
    return fetch_home_paged_by_t(t, our_pg)


def fetch_home_paged_by_t(t, our_pg):
    """首页无限滚动虚拟分页（直接按 type_id）：每页 HOME_PAGE_SIZE 条
    t = ffzy 分类 type_id（None 表示最新全部）
    返回 (items, has_more)

    has_more 判定：按"本次返回条数 < HOME_PAGE_SIZE"判断到达末页（兜底）
    不依赖 ffzy 接口返回的 total/pagecount，这两个值在 ffzy 里
    部分分类会返回 0，导致 has_more 恒为 false，触底不加载。
    """
    start = (our_pg - 1) * HOME_PAGE_SIZE          # 全局 0-indexed 起始
    native_pg = start // FFZY_PAGE_SIZE + 1         # 对应的 ffzy 页
    offset = start % FFZY_PAGE_SIZE                 # 在该 ffzy 页内的偏移
    items, pagecount, total = _fetch_native_cached(t, native_pg)
    result = items[offset:offset + HOME_PAGE_SIZE]
    # 跨 ffzy 页：本页不够 6 条且 ffzy 还有下一页，拼接下一页头部
    next_fetched = False
    if len(result) < HOME_PAGE_SIZE and native_pg < pagecount:
        items2, _, _ = _fetch_native_cached(t, native_pg + 1)
        need = HOME_PAGE_SIZE - len(result)
        result = result + items2[:need]
        next_fetched = True
    # has_more 判断（不依赖不可靠的 total/pagecount）
    if len(result) < HOME_PAGE_SIZE:
        # 本次返回不足一页：已经到末
        has_more = False
    else:
        # 本次返回满一页：按 ffzy 原生页判断是否还有剩余
        # 下一个全局起点是否超出 当前+下一页（如果取了）的内容范围
        next_start = our_pg * HOME_PAGE_SIZE
        native_range_end = native_pg * FFZY_PAGE_SIZE
        if next_fetched:
            native_range_end += FFZY_PAGE_SIZE
        # 还有数据当且仅当 ffzy 还有未覆盖的原生页，或下一个起点仍在已拉范围内
        if native_pg + (1 if next_fetched else 0) < pagecount:
            has_more = True
        else:
            has_more = next_start < native_range_end
        # 兜底：若取到的总条数对不上，假设还有下一页（保守）
        if not items:
            has_more = False
    return result, has_more


@app.route("/api/home_page")
def home_page():
    """首页"热门推荐"无限滚动列表：按首页分类 tab 分页，每页 6 条
    参数:
      cat = 分类名（推荐/热播/都市/古装/悬疑）
      pg  = 页码（默认1）
    返回与 /api/list 一致的结构，前端复用同套渲染逻辑。
    说明：路由用 /api/home_page 而非 /api/home/list，避免 uni-app vite
    插件对 /list 这类多段子路径的拦截。
    """
    cat = flask_request.args.get("cat", "").strip() or "推荐"
    pg = int(flask_request.args.get("pg", "1") or "1")
    items, has_more = fetch_home_paged(cat, pg)
    return jsonify({"code": 0, "data": {
        "list": items, "page": pg, "hasMore": has_more,
    }})


@app.route("/api/shorts")
def shorts():
    """短剧列表：按题材 tab 分页
    参数:
      tab = 数字题材 code（0=推荐/全部, 1=总裁, 2=穿越, 3=重生, 4=战神, 5=逆袭, 6=赘婿）
             前端传数字，后端映射 (t, wd)，避免中文出现在 URL 里
      pg  = 页码（默认1）
    数据源：ffzy 短剧分类 type_id=36（真短剧，近 2 万条），
            题材用 t=36+wd 关键词组合筛选。
    """
    pg = int(flask_request.args.get("pg", "1") or "1")
    tab_code_raw = flask_request.args.get("tab", "0").strip()
    try:
        tab_code = int(tab_code_raw)
    except ValueError:
        tab_code = 0
    tab_info = SHORTS_TAB_MAP.get(tab_code) or SHORTS_TAB_MAP[0]
    t = tab_info["t"]
    wd = tab_info.get("wd")
    # 复用 _fetch_native_cached：按 (t, pg, wd) 缓存 90 秒，与首页/片库共享
    items, pagecount, total = _fetch_native_cached(t, pg, wd=wd)
    return jsonify({"code": 0, "data": {
        "list": items, "page": pg, "pagecount": pagecount,
        "total": total, "hasMore": pg < pagecount,
    }})


@app.route("/api/search", methods=["GET", "POST"])
def search():
    """聚合搜索：并发请求所有采集站，合并去重
    任一源失败不影响其他源结果，自动容错。
    """
    if flask_request.method == "POST":
        wd = (flask_request.get_json(silent=True) or {}).get("wd", "")
    else:
        wd = flask_request.args.get("wd", "")
    wd = (wd or "").strip()
    if not wd:
        return jsonify({"code": 0, "data": []})
    print(f"[search] wd={wd!r}", flush=True)

    # 并发请求所有源
    futures = {}
    with ThreadPoolExecutor(max_workers=len(SITES)) as pool:
        for k in SITES:
            futures[pool.submit(fetch_site_search, k, wd)] = k

        # 收集结果
        per_source = {}   # site_key -> items
        for fut in as_completed(futures):
            k = futures[fut]
            try:
                items = fut.result()
                per_source[k] = items
                print(f"[search] got {len(items)} items from {k}", flush=True)
            except Exception as e:
                per_source[k] = []
                print(f"[search] {k} error: {e}", flush=True)

    # 合并去重：按 priority 顺序，主源结果优先
    results = []
    seen = set()
    for k in _LIST_SOURCE_KEYS:
        for it in per_source.get(k, []):
            key = it["title"].replace(" ", "")
            if key not in seen:
                seen.add(key)
                results.append(it)

    print(f"[search] merged {len(results)} items from {len(SITES)} sources", flush=True)
    return jsonify({"code": 0, "data": results, "total": len(results)})


@app.route("/api/shorts/search", methods=["GET", "POST"])
def shorts_search():
    """短剧搜索：搜索关键词，筛选短剧类型结果
    参数: wd = 关键词
    并发请求所有采集站，自动容错。
    """
    if flask_request.method == "POST":
        wd = (flask_request.get_json(silent=True) or {}).get("wd", "")
    else:
        wd = flask_request.args.get("wd", "")
    wd = (wd or "").strip()
    if not wd:
        return jsonify({"code": 0, "data": []})
    print(f"[shorts-search] wd={wd!r}", flush=True)

    # 并发请求所有源
    futures = {}
    with ThreadPoolExecutor(max_workers=len(SITES)) as pool:
        for k in SITES:
            futures[pool.submit(fetch_site_search, k, wd)] = k

        per_source = {}
        for fut in as_completed(futures):
            k = futures[fut]
            try:
                items = fut.result()
                # 筛选短剧类型（type_name 包含"短剧"）
                shorts_items = [it for it in items if "短剧" in (it.get("genre") or it.get("tag") or "")]
                per_source[k] = shorts_items
                print(f"[shorts-search] got {len(shorts_items)} shorts from {k} (total {len(items)})", flush=True)
            except Exception as e:
                per_source[k] = []
                print(f"[shorts-search] {k} error: {e}", flush=True)

    # 合并去重
    results = []
    seen = set()
    for k in _LIST_SOURCE_KEYS:
        for it in per_source.get(k, []):
            key = it["title"].replace(" ", "")
            if key not in seen:
                seen.add(key)
                results.append(it)

    return jsonify({"code": 0, "data": results, "total": len(results)})


@app.route("/api/detail")
def detail():
    """详情：返回线路+集数
    参数:
      id   = MacCMS vod_id（必填）
      site = 采集站 key（可选，指定后优先查它，未命中自动换源）
    自动故障切换：site 指定的源失败时，按 priority 顺序尝试其他源。
    """
    vod_id = flask_request.args.get("id", "").strip()
    site_key = flask_request.args.get("site", "").strip()
    if not vod_id:
        return jsonify({"code": -1, "msg": "缺少 id 参数"}), 400
    if site_key and site_key not in SITES:
        return jsonify({"code": -1, "msg": "未知采集站: " + site_key}), 400

    data, used_key = fetch_detail_with_failover(vod_id, prefer_key=site_key or None)
    if not data:
        return jsonify({"code": -1, "msg": "未找到或所有采集站不可用"})
    if used_key != site_key and site_key:
        print(f"[detail] 指定源 {site_key} 不可用，已切换到 {used_key}", flush=True)
    return jsonify({"code": 0, "data": data})


@app.route("/api/stream")
def stream():
    """流代理：注入 Referer，把 m3u8 内部 URL 改写为 <prefix>/api/stream?url=...
    用于 H5 端 <video>/hls.js 直接播放 m3u8/ts/mp4。
    参数:
      url    = 直链（必填）
      prefix = 反代前缀（H5 端走 Vite 代理时传 /__pyapi，直连时留空）
    """
    raw_url = flask_request.args.get("url", "").strip()
    prefix = flask_request.args.get("prefix", "").strip()
    if not raw_url:
        return Response("missing url", status=400)

    headers = dict(HEADERS)
    headers["Referer"] = guess_referer(raw_url)

    try:
        upstream = requests.get(raw_url, headers=headers, timeout=TIMEOUT, stream=True)
    except Exception as e:
        return Response("upstream error: " + str(e), status=502)

    if upstream.status_code != 200:
        return Response("upstream " + str(upstream.status_code), status=502)

    ctype = (upstream.headers.get("Content-Type") or "").lower()

    # m3u8 播放列表：先读完整文本再改写内部 URL（m3u8 很小，全量读取无压力）
    is_m3u8_url = raw_url.lower().split("?")[0].endswith(".m3u8")
    if "mpegurl" in ctype or is_m3u8_url:
        body = upstream.content
        text = body.decode("utf-8", errors="ignore")
        # 兜底：万一 ctype 没标对，但内容确实是 m3u8
        if "#extm3u" not in text.lower()[:200]:
            # 不是 m3u8，走二进制透传
            resp = Response(body, content_type=ctype or "application/octet-stream")
            resp.headers["Access-Control-Allow-Origin"] = "*"
            return resp
        rewritten = rewrite_m3u8(text, raw_url, prefix)
        resp = Response(rewritten, content_type="application/vnd.apple.mpegurl")
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["Cache-Control"] = "no-cache"
        return resp

    # ts / mp4 / 其它二进制：真正的流式转发（边收边发），减少首字节等待
    def generate():
        try:
            for chunk in upstream.iter_content(chunk_size=64 * 1024):
                if chunk:
                    yield chunk
        finally:
            try:
                upstream.close()
            except Exception:
                pass

    resp = Response(stream_with_context(generate()),
                    content_type=ctype or "application/octet-stream")
    resp.headers["Access-Control-Allow-Origin"] = "*"
    if "mp4" in ctype or "mp2t" in ctype or is_direct_play_url(raw_url):
        resp.headers["Accept-Ranges"] = "bytes"
    return resp


def rewrite_m3u8(text, base_url, prefix=""):
    """把 m3u8 文本里的相对/绝对 URL 改写为 <prefix>/api/stream?url=<encoded>[&prefix=...]"""
    lines_out = []
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            # EXT-X-KEY 里的 URI 也需要改写（极少见，先跳过）
            lines_out.append(line)
            continue
        # 解析为绝对 URL
        absolute = urljoin(base_url, s)
        # 包装为代理 URL：prefix + /api/stream
        params = {"url": absolute}
        if prefix:
            params["prefix"] = prefix
        proxied = prefix + "/api/stream?" + urlencode(params)
        lines_out.append(proxied)
    return "\n".join(lines_out) + "\n"


@app.route("/api/resolve")
def resolve():
    """解析分享页 URL，返回真实 m3u8 直链
    参数: url = ffzy 分享页地址（如 https://vip.ffzy-online3.com/share/xxx）
    返回: { code:0, data:{ direct:true, url:"https://.../index.m3u8" } }
    """
    share_url = flask_request.args.get("url", "").strip()
    if not share_url:
        return jsonify({"code": -1, "msg": "缺少 url 参数"}), 400
    # 若本来就是直链，直接返回
    if is_direct_play_url(share_url):
        return jsonify({"code": 0, "data": {"direct": True, "url": share_url}})
    m3u8 = resolve_share_url(share_url)
    if not m3u8:
        return jsonify({"code": -1, "msg": "解析失败，分享页未找到 m3u8"})
    return jsonify({"code": 0, "data": {"direct": True, "url": m3u8}})


@app.route("/api/player")
def player():
    """自带 hls.js 的 HTML 播放页（iframe 嵌入用）
    参数:
      url    = m3u8 直链 / ffzy 分享页 / 其它 HTML 播放页
      title  = 标题
      prefix = 反代前缀（H5 端走 Vite 代理时传 /__pyapi，直连时留空）
    说明：
      · 直链 m3u8/mp4 → 直接 hls.js 播放
      · ffzy 分享页  → Python 先解析出真实 m3u8，再 hls.js 播放（不再 iframe 嵌入分享页）
      · 其它 HTML 播放页（无法解析出 m3u8）→ 兜底 iframe 嵌入
    """
    raw_url = flask_request.args.get("url", "").strip()
    title = flask_request.args.get("title", "").strip() or "正在播放"
    prefix = flask_request.args.get("prefix", "").strip()
    if not raw_url:
        return Response("missing url", status=400)

    play_url = None
    is_m3u8 = False

    if is_direct_play_url(raw_url):
        # 直链 m3u8/mp4
        play_url = raw_url
        is_m3u8 = ".m3u8" in raw_url.lower()
    else:
        # 分享页 / HTML 播放页：尝试解析出真实 m3u8
        m3u8 = resolve_share_url(raw_url)
        if m3u8:
            play_url = m3u8
            is_m3u8 = True

    if play_url:
        # 用 hls.js 播放（经 /api/stream 流代理，注入 Referer + 改写 ts）
        stream_params = {"url": play_url}
        if prefix:
            stream_params["prefix"] = prefix
        stream_url = prefix + "/api/stream?" + urlencode(stream_params)
        html = render_hls_player(stream_url, title, is_m3u8)
    else:
        # 解析失败：不再 iframe 嵌入分享页（避免引入第三方 UI / 广告），
        # 返回明确错误提示，由前端层处理
        html = render_error_player(title, "无法解析出视频直链，请稍后重试或更换线路")

    return Response(html, content_type="text/html; charset=utf-8")


def render_hls_player(play_url, title, is_m3u8):
    hls_flag = "true" if is_m3u8 else "false"
    return """<!DOCTYPE html>
<html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,user-scalable=no">
<title>%s</title>
<style>
  html,body{margin:0;padding:0;height:100%%;background:#000;overflow:hidden;font-family:-apple-system,BlinkMacSystemFont,sans-serif;}
  #v{width:100%%;height:100%%;background:#000;object-fit:contain;}
  #bar{position:absolute;left:0;right:0;bottom:0;padding:8px 12px;background:linear-gradient(transparent,rgba(0,0,0,.7));color:#fff;font-size:13px;pointer-events:none;opacity:.85;}
  #err{position:absolute;top:50%%;left:50%%;transform:translate(-50%%,-50%%);color:#fff;font-size:14px;text-align:center;display:none;}
</style></head><body>
<video id="v" controls autoplay playsinline webkit-playsinline></video>
<div id="bar">%s</div>
<div id="err"></div>
<script>
(function(){
  var v = document.getElementById('v');
  var url = '%s';
  var isM3U8 = %s;
  function showErr(msg){ var e=document.getElementById('err'); e.textContent=msg; e.style.display='block'; }
  function tryPlay(){ v.play().catch(function(){}); }
  if (isM3U8) {
    // Safari 原生支持 HLS
    if (v.canPlayType('application/vnd.apple.mpegurl')) {
      v.src = url;
      tryPlay();
      return;
    }
    // 其它浏览器用 hls.js
    var script = document.createElement('script');
    script.src = 'https://cdn.jsdelivr.net/npm/hls.js@1.5.13/dist/hls.min.js';
    script.onload = function() {
      if (window.Hls && Hls.isSupported()) {
        var hls = new Hls({maxBufferLength: 30, liveDurationInfinity: true});
        hls.loadSource(url);
        hls.attachMedia(v);
        hls.on(Hls.Events.MANIFEST_PARSED, function(){ tryPlay(); });
        hls.on(Hls.Events.ERROR, function(_, data) {
          if (data.fatal) { showErr('播放错误: ' + (data.details || data.type)); }
        });
      } else {
        showErr('当前浏览器不支持 HLS 播放');
      }
    };
    script.onerror = function() { showErr('hls.js 加载失败'); };
    document.head.appendChild(script);
  } else {
    v.src = url;
    tryPlay();
  }
})();
</script>
</body></html>""" % (title, title, play_url, hls_flag)


def render_error_player(title, msg):
    """渲染错误提示页（不再 iframe 嵌入第三方分享页）"""
    return """<!DOCTYPE html>
<html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,user-scalable=no">
<title>%s</title>
<style>
  html,body{margin:0;padding:0;height:100%%;background:#000;overflow:hidden;font-family:-apple-system,BlinkMacSystemFont,sans-serif;display:flex;align-items:center;justify-content:center;}
  #msg{color:#fff;font-size:14px;text-align:center;padding:20px;line-height:1.6;}
</style></head><body>
<div id="msg">%s</div>
</body></html>""" % (title, msg)


def _warmup_cache():
    """服务启动时后台预热缓存：首页聚合 + 片库首页 + 片库各分类首页
    这样第一个真实用户请求就能命中缓存（ffzy 冷请求 2-3s，预热后 0ms）。
    放后台线程，不阻塞 app.run。
    """
    import time as _tm
    _tm.sleep(0.5)  # 等 Flask 起来
    try:
        # 1) 首页聚合（hero + hot + forYou）- 走 failover，主源失败自动切备源
        fetch_list_with_failover(pg=1, prefer_key="ffzy")
        print("[warmup] home ok")
        # 2) 片库 + 短剧默认分类（全部）+ 各 tab 首页
        #    短剧 tab 映射的 t 值（13/29）已在片库预热覆盖，这里幂等
        for t in [None, 6, 13, 25, 29, 20]:
            _fetch_native_cached(t, 1)
        print("[warmup] library + shorts all tabs ok")
    except Exception as e:
        print("[warmup] error: " + str(e))


if __name__ == "__main__":
    import os
    # Render / Koyeb / Heroku 等平台通过 PORT 环境变量注入端口
    # 本地开发默认 3001
    PORT = int(os.environ.get("PORT", 3001))
    print("=" * 50)
    print("VIIMK 视频爬虫后端启动")
    print("采集站: " + ", ".join(f"{k}({v['label']})" for k, v in SITES.items()))
    print("API: http://localhost:{}/api/search?wd=关键词".format(PORT))
    print("API: http://localhost:{}/api/detail?id=12345".format(PORT))
    print("API: http://localhost:{}/api/stream?url=<m3u8>".format(PORT))
    print("API: http://localhost:{}/api/player?url=<m3u8或播放页>&title=标题".format(PORT))
    print("=" * 50)
    # 后台预热缓存（不阻塞主线程）
    _thr.Thread(target=_warmup_cache, daemon=True).start()
    app.run(host="0.0.0.0", port=PORT, debug=False, threaded=True)
