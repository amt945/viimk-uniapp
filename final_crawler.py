#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
最终版：三站点视频爬虫
关键发现 yp262.com: AES-ECB 模式，key=sha256(crypt_key_str).digest()
"""
import os
import re
import sys
import json
import time
import base64
import hashlib
import warnings
import requests
import subprocess
from urllib.parse import urljoin

warnings.filterwarnings('ignore')

try:
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import unpad
    HAS_PYCRYPTODOME = True
except ImportError:
    HAS_PYCRYPTODOME = False

try:
    import yt_dlp
    HAS_YTDLP = True
except ImportError:
    HAS_YTDLP = False

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
}

DOWNLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'downloads')
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# ============================================================
# 爬取规模控制
# ============================================================
# 不限流：全量抓取每个分类所有分页，前端通过 server.py 内存分页触底加载。
MAX_PAGES_PER_CATEGORY = 9999    # 翻页上限设大值，实际靠"列表页无新链接则停止"自然终止
MAX_ITEMS_PER_SITE = 999999      # 单站采集上限设大值，不截断
CRAWL_DELAY = 0.3                # 请求间隔(秒)

JSON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'video_results.json')


# ============================================================
# AES 解密 - 经过验证的正确实现
# ============================================================
def aes_ecb_decrypt_youtube(enc_b64, crypt_key_str):
    """
    yp262.com (MacCMS变体) 验证可用的解密方式:
      AES.MODE_ECB
      key = SHA256(crypt_key_str.encode()).digest()    (32 bytes)
      padding = Pkcs7
    """
    if not HAS_PYCRYPTODOME:
        raise RuntimeError("需要 pycryptodome")
    # URL安全 base64 -> bytes
    s = enc_b64.replace('-', '+').replace('_', '/')
    pad = 4 - len(s) % 4
    if pad != 4:
        s += '=' * pad
    cipher_bytes = base64.b64decode(s)
    
    # key = sha256(密码字符串) -> 32字节
    key = hashlib.sha256(crypt_key_str.encode('utf-8')).digest()
    
    cipher = AES.new(key, AES.MODE_ECB)
    decrypted = cipher.decrypt(cipher_bytes)
    plain = unpad(decrypted, AES.block_size)
    return plain.decode('utf-8')


def decrypt_cover_content(content):
    """解密 yp262 加密封面图。

    封面 URL 返回的文本格式: ``base:{marker}::{url_safe_b64_data}``
    解密算法与视频 URL 相同 (AES-ECB / SHA256(marker) / Pkcs7),
    区别是 key 来自 marker (``base:`` 后的第一个字段) 而非页面 crypt_key。

    Returns:
        bytes: 解密后的图片二进制数据 (JPEG/PNG/WebP), 失败返回 None。
    """
    if not content or not content.startswith('base:'):
        return None
    parts = content.split(':')
    if len(parts) < 4:
        return None
    marker = parts[1]
    data_str = parts[3].strip()
    if not marker or not data_str:
        return None
    # URL-safe base64 -> standard
    data_b64 = data_str.replace('-', '+').replace('_', '/')
    pad_b64 = 4 - len(data_b64) % 4
    if pad_b64 != 4:
        data_b64 += '=' * pad_b64
    try:
        ciphertext = base64.b64decode(data_b64)
        key = hashlib.sha256(marker.encode('utf-8')).digest()
        cipher = AES.new(key, AES.MODE_ECB)
        plain = unpad(cipher.decrypt(ciphertext), AES.block_size)
        # 校验是否为有效图片
        if plain[:4] == b'RIFF' or plain[:2] == b'\xff\xd8' or plain[:8] == b'\x89PNG\r\n\x1a\n':
            return plain
        return None
    except Exception:
        return None


def decrypt_cover_url(cover_url):
    """获取并解密 yp262 加密封面 URL, 返回图片 bytes 或 None。"""
    r = safe_request(cover_url, timeout=15)
    if not r or r.status_code != 200:
        return None
    return decrypt_cover_content(r.text)


def safe_request(url, retries=3, timeout=30, extra_headers=None):
    h = dict(HEADERS)
    if extra_headers:
        h.update(extra_headers)
    for i in range(retries):
        try:
            resp = requests.get(url, headers=h, timeout=timeout, verify=False, allow_redirects=True)
            resp.encoding = resp.apparent_encoding or 'utf-8'
            return resp
        except Exception:
            if i < retries - 1:
                time.sleep(2)
    return None


# ============================================================
# 通用提取
# ============================================================
def extract_videos_generic(html, base_url):
    results = []
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        for video in soup.find_all('video'):
            src = video.get('src') or video.get('data-src')
            if src:
                results.append({'type': 'mp4', 'url': urljoin(base_url, src)})
            for st in video.find_all('source'):
                s = st.get('src')
                if s:
                    t = 'm3u8' if '.m3u8' in s else 'mp4'
                    results.append({'type': t, 'url': urljoin(base_url, s)})
        for iframe in soup.find_all('iframe'):
            src = iframe.get('src')
            if src and src.startswith('http'):
                r2 = safe_request(src, timeout=15)
                if r2:
                    results.extend(extract_videos_generic(r2.text, src))
    except ImportError:
        pass
    for pat, vt in [(r'(https?://[^\s"\'<>)]+\.m3u8[^\s"\'<>)]*)', 'm3u8'),
                    (r'(https?://[^\s"\'<>)]+\.mp4[^\s"\'<>)]*)', 'mp4')]:
        for m in re.findall(pat, html):
            results.append({'type': vt, 'url': m})
    u, seen = [], set()
    for r in results:
        if r['url'] not in seen:
            seen.add(r['url'])
            u.append(r)
    return u


# ============================================================
# 分页 & 分类发现 通用辅助
# ============================================================
def _maccms_collect_play_links(base, vodtype_id, max_pages=MAX_PAGES_PER_CATEGORY):
    """收集 MacCMS 分类下所有播放链接及其封面图（自动分页）
    MacCMS v10 分页 URL 格式: /vodtype/{id}-{page}.html
    返回: [{url, cover}, ...]
    """
    all_items = []
    seen = set()
    for page in range(1, max_pages + 1):
        if page == 1:
            url = f"{base}/vodtype/{vodtype_id}.html"
        else:
            url = f"{base}/vodtype/{vodtype_id}-{page}.html"
        r = safe_request(url, timeout=20)
        if not r or r.status_code != 200:
            break
        if '521' in r.text[:300]:
            break
        html = r.text
        new_count = 0

        def _norm_cover(cover):
            if not cover:
                return ''
            if cover.startswith('//'):
                cover = 'https:' + cover
            elif cover.startswith('/'):
                cover = urljoin(r.url, cover)
            return cover.replace('&amp;', '&')

        # 策略: 以"封面图"为锚点找其所在卡片内的播放链接。
        # yp262/MacCMS 列表页结构: <a href="/vodplay/ID-1-1.html"><img data-original="COVER"/></a>
        # 用 BeautifulSoup 取 img 的最近祖先 <a href=/vodplay/>, 精确配对, 不会错位到相邻卡片。
        paired = False
        if HAS_BS4:
            try:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(html, 'html.parser')
                for img in soup.find_all('img'):
                    cover = img.get('data-original') or img.get('data-src') or ''
                    if not cover or not re.search(r'\.(?:jpg|jpeg|png|webp)', cover, re.I):
                        continue
                    a = img.find_parent('a', href=True)
                    if not a:
                        continue
                    href = a.get('href', '')
                    if not re.search(r'/vodplay/\d+-\d+-\d+\.html', href):
                        continue
                    full = urljoin(r.url, href)
                    if full in seen:
                        continue
                    seen.add(full)
                    all_items.append({'url': full, 'cover': _norm_cover(cover)})
                    new_count += 1
                    paired = True
            except Exception:
                paired = False

        # 回退: 正则匹配 <a href=/vodplay/...><img data-original=...>
        if not paired:
            for mm in re.finditer(
                r'<a[^>]*href="(/vodplay/\d+-\d+-\d+\.html)"[^>]*>\s*<img[^>]*?(?:data-original|data-src)="([^"]+)"',
                html, re.I):
                full = urljoin(r.url, mm.group(1))
                if full in seen:
                    continue
                seen.add(full)
                all_items.append({'url': full, 'cover': _norm_cover(mm.group(2))})
                new_count += 1

        # 最后兜底: 仅有播放链接、无封面的卡片也收集(留空 cover, 详情页再补)
        for m in re.findall(r'href="(/vodplay/\d+-\d+-\d+\.html)"', html):
            full = urljoin(r.url, m)
            if full not in seen:
                seen.add(full)
                all_items.append({'url': full, 'cover': ''})
                new_count += 1

        if new_count == 0:
            break
        time.sleep(CRAWL_DELAY)
    return all_items


def _discover_maccms_categories(base, extra_ids=None):
    """从 MacCMS 首页导航发现所有分类 ID
    返回 [(id, name), ...] 列表
    """
    cats = []
    seen_ids = set()
    # 预置常见分类 ID
    preset = list(extra_ids or [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 144, 145, 146, 147])
    for cid in preset:
        if cid not in seen_ids:
            seen_ids.add(cid)
            cats.append((cid, f'preset-{cid}'))

    # 从首页导航发现更多分类
    r = safe_request(base + '/', timeout=20)
    if r and r.status_code == 200 and '521' not in r.text[:300]:
        # 匹配 /vodtype/数字.html 或 /vodshow/数字.html
        for m in re.finditer(r'href="(?:https?://[^/]+)?/vod(?:type|show)/(\d+)(?:-\d+)?\.html?"[^>]*>([^<]{1,20})', r.text):
            cid = int(m.group(1))
            name = m.group(2).strip()
            if cid not in seen_ids and name:
                seen_ids.add(cid)
                cats.append((cid, name))
    return cats


def _wp_collect_articles(content_base, cat_slug, max_pages=MAX_PAGES_PER_CATEGORY):
    """收集 WordPress 分类下所有文章 URL（自动分页）
    分页格式: /category/{slug}/page/{N}/
    """
    all_arts = []
    seen = set()
    for page in range(1, max_pages + 1):
        if page == 1:
            url = f"{content_base}/category/{cat_slug}/"
        else:
            url = f"{content_base}/category/{cat_slug}/page/{page}/"
        r = safe_request(url, timeout=20)
        if not r or r.status_code != 200:
            break
        arts = re.findall(r'href="([^"]*?/archives/\d+/?[^"]*)"', r.text)
        if not arts:
            break
        new_count = 0
        for m in arts:
            full = m if m.startswith('http') else content_base + m
            if full not in seen:
                seen.add(full)
                all_arts.append(full)
                new_count += 1
        if new_count == 0:
            break
        time.sleep(CRAWL_DELAY)
    return all_arts


def _save_incremental(results, tag=''):
    """增量保存结果到 video_results.json（防止长时间爬取中途崩溃丢失数据）"""
    try:
        with open(JSON_PATH, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2, default=str)
        if tag:
            print(f"  [增量保存] {tag}: {len(results)} 条 -> {JSON_PATH}")
    except Exception as e:
        print(f"  [!] 增量保存失败: {e}")


def try_ytdlp(url):
    if not HAS_YTDLP:
        return []
    try:
        opts = {'quiet': True, 'no_warnings': True, 'skip_download': True,
                'ignoreerrors': True, 'nocheckcertificate': True, 'http_headers': HEADERS}
        urls = []
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if info:
                if 'formats' in info:
                    for f in info['formats']:
                        if f.get('url'):
                            urls.append(f['url'])
                if 'url' in info:
                    urls.append(info['url'])
                if 'entries' in info:
                    for e in (info['entries'] or [])[:5]:
                        if isinstance(e, dict) and e.get('url'):
                            urls.append(e['url'])
        return list(dict.fromkeys(urls))
    except Exception:
        return []


def download_m3u8(m3u8_url, output_name, referer=None):
    safe_name = re.sub(r'[\\/:*?"<>|]', '_', output_name)[:80]
    output_path = os.path.join(DOWNLOAD_DIR, safe_name + '.mp4')
    cmd = None
    try:
        if subprocess.run(['ffmpeg', '-version'], capture_output=True, timeout=8).returncode == 0:
            cmd = ['ffmpeg', '-y',
                   '-user_agent', HEADERS['User-Agent'],
                   '-headers', f'Referer: {referer or ""}\r\n',
                   '-i', m3u8_url, '-c', 'copy',
                   '-bsf:a', 'aac_adtstoasc', output_path]
        elif HAS_YTDLP:
            cmd = [sys.executable, '-m', 'yt_dlp', '--no-check-certificates',
                   '-o', output_path, '--user-agent', HEADERS['User-Agent'],
                   '--referer', referer or '', m3u8_url]
    except Exception:
        pass
    
    if not cmd:
        print(f"    [!] 无可用下载工具，手动链接: {m3u8_url}")
        return None
    
    print(f"    [下载] -> {output_path}")
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
        if p.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            size_mb = os.path.getsize(output_path) / 1024 / 1024
            print(f"    [✓] 完成 大小={size_mb:.1f}MB")
            return output_path
        else:
            print(f"    [✗] 失败 exit={p.returncode}")
            if p.stderr:
                print(f"      stderr: {p.stderr[-400:]}")
    except subprocess.TimeoutExpired:
        print("    [!] 超时(15分钟)")
    except Exception as e:
        print(f"    [!] 异常: {e}")
    return None


# ============================================================
# 站点1: 911cg3.com (911爆料 / DPlayer data-config 解析)
# 真实内容站: bar.svqnsple.cc / blanket.svqnsple.cc
# 文章格式: /archives/{id}/
# 视频嵌入: <div class="dplayer" data-config='{... video.url: "m3u8" ...}'>
# ============================================================
def parse_site1():
    print("\n" + "="*70)
    print("【站点1】911cg3.com / 911爆料网 (DPlayer data-config 解析)")
    print("="*70)
    results = []
    import html as _html_mod

    ENTRANCE_URLS = [
        'https://911cg3.com/',
        'https://www.aeaeewyn.com/',
    ]
    FALLBACK_BASES = [
        'https://bar.svqnsple.cc',
        'https://blanket.svqnsple.cc',
    ]
    # 预置分类 + 从首页动态发现更多
    KNOWN_CAT_SLUGS = ['fljq', 'thjx', 'wyjd', 'ntll']

    # ---- 1. 发现内容站 ----
    content_base = None
    for eu in ENTRANCE_URLS:
        resp = safe_request(eu)
        if resp and resp.status_code == 200:
            routes = list(dict.fromkeys(
                m for m in re.findall(r'https?://[A-Za-z0-9.\-]+/[A-Za-z0-9.\-/]*', resp.text)
                if any(k in m.lower() for k in ['svqn', 'blanket.', 'bar.', '911bl', '911cg'])
            ))
            if routes:
                content_base = routes[0].rstrip('/')
                print(f"  [入口] {eu} -> 内容站: {content_base}")
                break
    if not content_base:
        content_base = FALLBACK_BASES[0]
        print(f"  [兜底] 直接使用内容站: {content_base}")

    # ---- 1b. 从内容站首页发现所有分类 slug ----
    cat_slugs = list(KNOWN_CAT_SLUGS)
    home_resp = safe_request(content_base + '/', timeout=20)
    if home_resp and home_resp.status_code == 200:
        discovered = re.findall(r'href="[^"]*?/category/([a-z0-9_-]+)/?', home_resp.text, re.I)
        for slug in discovered:
            if slug not in cat_slugs:
                cat_slugs.append(slug)
    print(f"  [分类] 共 {len(cat_slugs)} 个: {cat_slugs}")

    # ---- 2. 逐分类分页收集文章URL ----
    all_arts = []
    for slug in cat_slugs:
        arts = _wp_collect_articles(content_base, slug)
        print(f"  [分类/{slug}] 共 {len(arts)} 篇文章")
        all_arts.extend(arts)
        if len(all_arts) >= MAX_ITEMS_PER_SITE:
            print(f"  [!] 已达站点上限 {MAX_ITEMS_PER_SITE}，停止收集")
            break
    all_arts = list(dict.fromkeys(all_arts))[:MAX_ITEMS_PER_SITE]
    print(f"  [汇总] 待解析 {len(all_arts)} 篇文章")

    # ---- 3. 逐篇解析 DPlayer data-config ----
    for aurl in all_arts:
        resp = safe_request(aurl)
        if not resp or resp.status_code != 200:
            continue
        soup = BeautifulSoup(resp.text, 'html.parser') if HAS_BS4 else None
        title_elm = soup and soup.find('title')
        title = title_elm.get_text().split(' - 911')[0].strip() if title_elm else ''
        if not title:
            m = re.search(r'<title>([^<]+)</title>', resp.text)
            title = m.group(1).split(' - 911')[0].strip() if m else 'site1-video'

        html_text = resp.text
        video_url = None
        pic_url = None

        # 提取封面图：优先 DPlayer video.pic，兜底 og:image / 文章特色图
        og_m = re.search(r'<meta\s+property="og:image"\s+content="([^"]+)"', html_text, re.I)
        if og_m:
            pic_url = og_m.group(1).replace('&amp;', '&')

        # 找 dplayer div (可能有多个 class 变体)
        dp_match = re.search(r'<div[^>]*class="[^"]*dplayer[^"]*"[^>]*>', html_text, re.I)
        if dp_match:
            tag = dp_match.group(0)
            # 优先从 tag 内提取 data-config
            cfg_str = None
            mm = re.search(r'data-config=[\'"]([\s\S]*?)[\'"]\s*[/> ]', tag, re.I)
            if mm:
                cfg_str = mm.group(1)
            else:
                # 从全文 dp_match 位置找
                start = html_text.find('data-config=', dp_match.start())
                if start >= 0:
                    q = html_text[start + len('data-config=')]
                    if q in '"\'':
                        end = html_text.find(q, start + len('data-config=') + 1)
                        if end > 0:
                            cfg_str = html_text[start + len('data-config=') + 1 : end]

            if cfg_str:
                cfg_str = _html_mod.unescape(cfg_str)
                # 解析 JSON
                parsed_cfg = None
                try:
                    parsed_cfg = json.loads(cfg_str)
                except Exception:
                    pass

                if isinstance(parsed_cfg, dict):
                    # A. .video.url 是正片
                    v = parsed_cfg.get('video')
                    if isinstance(v, dict):
                        video_url = v.get('url')
                        pic_url = v.get('pic')
                    # B. 兜底: 递归找 m3u8/mp4
                    if not video_url:
                        def _walk(o):
                            if isinstance(o, dict):
                                for vv in o.values():
                                    r = _walk(vv)
                                    if r: return r
                            elif isinstance(o, list):
                                for x in o:
                                    r = _walk(x)
                                    if r: return r
                            elif isinstance(o, str) and ('.m3u8' in o or '.mp4' in o):
                                return o
                            return None
                        video_url = _walk(parsed_cfg)

                # C. JSON 失败: 正则硬找，排除广告
                if not video_url:
                    urls = list(dict.fromkeys(re.findall(
                        r'https?://[A-Za-z0-9._~:/?#\[\]@!$&\'()*+,;=%\-]+?\.(?:m3u8|mp4)[A-Za-z0-9._~:/?#\[\]@!$&\'()*+,;=%\-]*',
                        cfg_str
                    )))
                    for u in urls:
                        if u.endswith('.m3u8') or u.endswith('.mp4'):
                            video_url = u; break
                    if not video_url and urls:
                        video_url = urls[0]

        if video_url:
            vt = 'm3u8' if '.m3u8' in video_url else ('mp4' if '.mp4' in video_url else 'unknown')
            print(f"  [+] {title[:60]}")
            print(f"      [{vt}] {video_url[:180]}")
            results.append({
                'site': 'site1',
                'title': title or '911-video',
                'source_url': aurl,
                'type': vt,
                'url': video_url,
                'pic': pic_url,
            })
        else:
            # 兜底尝试通用提取 + yt-dlp
            g = extract_videos_generic(html_text, aurl)
            if g:
                for v in g[:1]:
                    print(f"  [+] (通用) {title[:50]} -> {v['type']}: {v['url'][:120]}")
                    results.append({'site': 'site1', 'title': title, 'source_url': aurl, 'pic': pic_url, **v})
            else:
                for yu in try_ytdlp(aurl)[:1]:
                    print(f"  [+] (yt-dlp) {title[:50]}")
                    results.append({'site': 'site1', 'title': title, 'source_url': aurl,
                                    'type': 'ytdlp', 'url': yu, 'pic': pic_url})
        time.sleep(CRAWL_DELAY)
        # 每 20 条增量保存一次
        if len(results) > 0 and len(results) % 20 == 0:
            _save_incremental(results, f'site1-progress')
    return results


HAS_BS4 = False
try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    pass


# ============================================================
# 站点2: actress.llbieya.cc  (MacCMS 10 变种, 与 yp262.com 同架构)
# 说明: 该站当前 Cloudflare 521 (源站宕机/未响应), 逻辑预实现
#       源站恢复后即刻生效 (AES-ECB + SHA256(crypt_key) 同 yp262)
# ============================================================
def parse_site2():
    print("\n" + "="*70)
    print("【站点2】actress.llbieya.cc  (MacCMS / AES-ECB 预实现)")
    print("="*70)
    results = []
    base = 'https://actress.llbieya.cc'

    # ---- 1. 先诊断连通性 ----
    resp = safe_request(base + '/', timeout=20)
    if resp and resp.status_code == 521:
        print("  [!] Cloudflare 521: Web server is down (源站未响应/宕机)")
        print("      说明: 这是源站服务器自身问题, 非 Cloudflare JS 挑战.")
        print("      已预置完整 MacCMS 解析逻辑 (同 yp262 AES-ECB), 源站恢复后立即生效.")
        print("      稍后可通过 re-run 本脚本或浏览器访问 https://actress.llbieya.cc/ 验证.")
        # 不立即 return, 让后面有更多路径可以继续"试"其他变体
    elif not resp:
        print("  [!] 无法访问, 稍后重试")
    elif resp.status_code == 200 and len(resp.text) > 5000:
        print(f"  [+] 首页正常! 长度={len(resp.text)}")

    # ---- 2. 发现分类 + 分页收集播放链接(含封面) ----
    cats = _discover_maccms_categories(base)
    print(f"  [分类] 共 {len(cats)} 个: {cats[:20]}")
    play_items = []
    for cid, cname in cats:
        found = _maccms_collect_play_links(base, cid)
        if found:
            cover_count = sum(1 for f in found if f.get('cover'))
            print(f"  [分类/vodtype/{cid}({cname})] 发现 {len(found)} 个播放页 (封面 {cover_count}/{len(found)})")
            play_items.extend(found)
        if len(play_items) >= MAX_ITEMS_PER_SITE:
            print(f"  [!] 已达站点上限 {MAX_ITEMS_PER_SITE}")
            break
    play_items = play_items[:MAX_ITEMS_PER_SITE]

    # ---- 3. 兜底 (若分类页因521失败, 枚举几个常见播放页直接试) ----
    if not play_items:
        print("  [*] 因521无法获取列表, 兜底尝试常见播放页ID...")
        common_ids = list(range(70900, 71050, 5)) + list(range(69000, 69200, 10))
        for vid in common_ids[:20]:
            play_items.append({'url': f"{base}/vodplay/{vid}-1-1.html", 'cover': ''})

    # ---- 4. 逐个解析播放页 ----
    print(f"  [解析] 共 {len(play_items)} 个播放页待解析")
    for item in play_items:
        purl = item['url']
        res = _parse_maccms_single(purl, expected_site='site2')
        if res:
            if item.get('cover') and not res.get('pic'):
                res['pic'] = item['cover']
            results.append(res)
            if len(results) % 20 == 0:
                _save_incremental(results, f'site2-progress')
        if len(results) >= MAX_ITEMS_PER_SITE:
            break
        time.sleep(CRAWL_DELAY)

    if not results:
        print("  [-] 当前未能从 actress.llbieya.cc 提取视频 (源站521)")
    return results


def _parse_maccms_single(play_url, expected_site='site3'):
    """通用 MacCMS 播放页解析 (yp262 / actress 通用). AES-ECB + SHA256(crypt_key)"""
    r = safe_request(play_url)
    if not r or (r.status_code == 521) or (r.status_code != 200):
        return None

    html = r.text
    title_m = re.search(r'<title>([^<]+)</title>', html)
    title_enc = title_m.group(1).strip() if title_m else ''

    ck_m = re.search(r'<meta\s+name="crypt_key"\s+content="([^"]+)"', html)
    enc_t_m = re.search(r'vod_name\s*=\s*Decryptor\.aesDecryptBase64\("([^"]+)"\)', html)
    enc_p_m = re.search(r'var\s+player_aaaa\s*=\s*JSON\.parse\(\s*aesDecryptBase64\(\s*"([^"]+)"\s*\)\s*\)', html)

    if not (ck_m and enc_p_m and HAS_PYCRYPTODOME):
        vids = extract_videos_generic(html, play_url)
        if vids:
            return {'site': expected_site, 'title': title_enc, 'source_url': play_url, **vids[0]}
        return None

    crypt_key = ck_m.group(1)
    enc_title = enc_t_m.group(1) if enc_t_m else None
    enc_player = enc_p_m.group(1)

    title = ''
    if enc_title:
        try:
            title = aes_ecb_decrypt_youtube(enc_title, crypt_key)
        except Exception:
            title = title_enc

    try:
        player_json_str = aes_ecb_decrypt_youtube(enc_player, crypt_key)
        try:
            player_cfg = json.loads(player_json_str)
        except json.JSONDecodeError:
            fixed = re.sub(r',\s*([}\]])', r'\1', player_json_str.replace("'", '"'))
            try:
                player_cfg = json.loads(fixed)
            except Exception:
                player_cfg = {'_raw': player_json_str}
    except Exception:
        # 降级通用提取
        vids = extract_videos_generic(html, play_url)
        if vids:
            return {'site': expected_site, 'title': title or title_enc, 'source_url': play_url, **vids[0]}
        return None

    video_url = None
    video_type = 'unknown'
    direct_keys = ['url', 'video_url', 'play_url', 'src', 'source', 'playUrl', 'videoUrl', 'link']
    for k in direct_keys:
        v = player_cfg.get(k) if isinstance(player_cfg, dict) else None
        if isinstance(v, str) and len(v) > 8:
            if v.startswith('http'):
                video_url = v; break
            elif '.' in v and any(ext in v.lower() for ext in ['.m3u8', '.mp4', '.webm']):
                video_url = 'https://' + v if not v.startswith('//') else 'https:' + v
                break

    if not video_url and isinstance(player_cfg, dict):
        found_urls = []
        def walk(obj):
            if isinstance(obj, dict):
                for v in obj.values(): walk(v)
            elif isinstance(obj, list):
                for x in obj: walk(x)
            elif isinstance(obj, str):
                if obj.startswith('http') or '.m3u8' in obj or '.mp4' in obj:
                    found_urls.append(obj)
        walk(player_cfg)
        for u in found_urls:
            if '.m3u8' in u: video_url = u; break
        if not video_url and found_urls:
            video_url = found_urls[0]

    if not video_url and isinstance(player_cfg, dict) and '_raw' in player_cfg:
        for pat in [r'(https?://[^\s"\']+?\.m3u8[^\s"\']*)', r'(https?://[^\s"\']+?\.mp4[^\s"\']*)']:
            murl = re.search(pat, player_cfg['_raw'])
            if murl:
                video_url = murl.group(1); break

    if video_url:
        if video_url.startswith('//'):
            video_url = 'https:' + video_url
        elif not video_url.startswith('http'):
            if '.' in (video_url.split('/')[0] or '') and not video_url.startswith('/'):
                video_url = 'https://' + video_url
        if '.m3u8' in video_type: video_type = 'm3u8'
        elif '.m3u8' in video_url: video_type = 'm3u8'
        elif '.mp4' in video_url: video_type = 'mp4'

        # 提取封面图：player_cfg 中的 pic/vod_pic/poster 字段，兜底 og:image
        pic_url = ''
        if isinstance(player_cfg, dict):
            for pk in ['pic', 'vod_pic', 'poster', 'thumbnail', 'cover']:
                pv = player_cfg.get(pk)
                if isinstance(pv, str) and pv.startswith('http'):
                    pic_url = pv; break
        if not pic_url:
            og_m = re.search(r'<meta\s+property="og:image"\s+content="([^"]+)"', html, re.I)
            if og_m:
                pic_url = og_m.group(1).replace('&amp;', '&')

        return {
            'site': expected_site,
            'title': title or f'{expected_site}-video',
            'source_url': play_url,
            'type': video_type,
            'url': video_url,
            'pic': pic_url,
        }
    # 最后 yt-dlp
    ytu = try_ytdlp(play_url)
    if ytu:
        return {'site': expected_site, 'title': title or title_enc,
                'source_url': play_url, 'type': 'ytdlp', 'url': ytu[0]}
    return None


# ============================================================
# 站点3: yp262.com  (AES ECB + SHA256 解密已验证)
# ============================================================
def parse_site3():
    print("\n" + "="*70)
    print("【站点3】yp262.com  (AES-ECB + SHA256 已验证)")
    print("="*70)
    results = []
    base = 'https://www.yp262.com'

    # 1. 发现所有分类 + 分页收集播放链接(含封面)
    cats = _discover_maccms_categories(base, extra_ids=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 144, 145, 146, 147, 148, 149, 150])
    print(f"  [分类] 共 {len(cats)} 个: {cats[:20]}")

    play_items = []
    for cid, cname in cats:
        found = _maccms_collect_play_links(base, cid)
        if found:
            cover_count = sum(1 for f in found if f.get('cover'))
            print(f"  [分类/vodtype/{cid}({cname})] 发现 {len(found)} 个播放页 (封面 {cover_count}/{len(found)})")
            play_items.extend(found)
        if len(play_items) >= MAX_ITEMS_PER_SITE:
            print(f"  [!] 已达站点上限 {MAX_ITEMS_PER_SITE}")
            break
    play_items = play_items[:MAX_ITEMS_PER_SITE]
    print(f"  [汇总] 共 {len(play_items)} 个播放页待解析")

    # 2. 逐个解析
    for item in play_items:
        purl = item['url']
        res = parse_yp262_single(purl)
        if res:
            if item.get('cover') and not res.get('pic'):
                res['pic'] = item['cover']
            results.append(res)
            if len(results) % 20 == 0:
                _save_incremental(results, f'site3-progress')
        if len(results) >= MAX_ITEMS_PER_SITE:
            break
        time.sleep(CRAWL_DELAY)

    return results


def parse_yp262_single(play_url):
    r = safe_request(play_url)
    if not r:
        print(f"  [-] 访问失败 {play_url}")
        return None
    
    html = r.text
    title_m = re.search(r'<title>([^<]+)</title>', html)
    title_enc = title_m.group(1).strip() if title_m else ''
    
    # 提取 crypt_key 和 加密串
    ck_m = re.search(r'<meta\s+name="crypt_key"\s+content="([^"]+)"', html)
    enc_t_m = re.search(r'vod_name\s*=\s*Decryptor\.aesDecryptBase64\("([^"]+)"\)', html)
    enc_p_m = re.search(r'var\s+player_aaaa\s*=\s*JSON\.parse\(\s*aesDecryptBase64\(\s*"([^"]+)"\s*\)\s*\)', html)
    
    if not (ck_m and enc_p_m and HAS_PYCRYPTODOME):
        # 降级到通用提取
        vids = extract_videos_generic(html, play_url)
        if vids:
            _fb = ''
            _og = re.search(r'<meta\s+property="og:image"\s+content="([^"]+)"', html, re.I)
            if _og:
                _fb = _og.group(1).replace('&amp;', '&')
                if _fb.startswith('//'):
                    _fb = 'https:' + _fb
            return {'site': 'site3', 'title': title_enc, 'source_url': play_url,
                    'pic': _fb, **vids[0]}
        return None
    
    crypt_key = ck_m.group(1)
    enc_title = enc_t_m.group(1) if enc_t_m else None
    enc_player = enc_p_m.group(1)
    
    print(f"\n  [*] 解析 {play_url}")
    print(f"    crypt_key = {crypt_key}")
    
    # 解密标题
    title = ''
    if enc_title:
        try:
            title = aes_ecb_decrypt_youtube(enc_title, crypt_key)
            print(f"    [✓] 标题: {title[:80]}")
        except Exception as e:
            print(f"    [!] 标题解密失败: {e}")
            title = title_enc
    
    # 解密 player_aaaa
    try:
        player_json_str = aes_ecb_decrypt_youtube(enc_player, crypt_key)
        print(f"    [✓] player_aaaa 解密成功, 长度={len(player_json_str)}")
        
        try:
            player_cfg = json.loads(player_json_str)
        except json.JSONDecodeError:
            # 非标准JSON，尝试修复
            try:
                fixed = player_json_str.replace("'", '"')
                # 去掉JS注释和尾部逗号
                fixed = re.sub(r',\s*([}\]])', r'\1', fixed)
                player_cfg = json.loads(fixed)
            except Exception as e2:
                print(f"    [!] JSON解析失败({e2})，用正则提取URL")
                player_cfg = {'_raw': player_json_str}
        
        # 保存解密结果
        debug_path = os.path.join(DOWNLOAD_DIR, 'player_cfg_last.json')
        with open(debug_path, 'w', encoding='utf-8') as f:
            json.dump(player_cfg, f, ensure_ascii=False, indent=2, default=str)
        print(f"    [i] player配置已保存: {debug_path}")
        
        # 查找视频URL
        video_url = None
        video_type = 'unknown'
        
        # 方法1: 直接字段
        direct_keys = ['url', 'video_url', 'play_url', 'src', 'source', 'playUrl', 'videoUrl', 'link']
        for k in direct_keys:
            v = player_cfg.get(k) if isinstance(player_cfg, dict) else None
            if isinstance(v, str) and len(v) > 8:
                # 判断是否是真正的视频链接（包含域名+后缀 或 http）
                if v.startswith('http'):
                    video_url = v
                    break
                elif '.' in v and any(ext in v.lower() for ext in ['.m3u8', '.mp4', '.webm']):
                    video_url = 'https://' + v if not v.startswith('//') else 'https:' + v
                    break
        
        # 方法2: 遍历所有嵌套找含URL字符串
        if not video_url:
            found_urls = []
            def walk(obj):
                if isinstance(obj, dict):
                    for v in obj.values():
                        walk(v)
                elif isinstance(obj, list):
                    for x in obj:
                        walk(x)
                elif isinstance(obj, str):
                    if obj.startswith('http') or ('.m3u8' in obj or '.mp4' in obj):
                        found_urls.append(obj)
            walk(player_cfg)
            print(f"    [i] 遍历发现候选URL {len(found_urls)} 个: {found_urls[:5]}")
            # 优先选m3u8
            for u in found_urls:
                if '.m3u8' in u:
                    video_url = u
                    break
            if not video_url and found_urls:
                video_url = found_urls[0]
        
        # 方法3: 从原始字符串中提取
        if not video_url and isinstance(player_cfg, dict) and '_raw' in player_cfg:
            murl = re.search(r'(https?://[^\s"\']+?\.m3u8[^\s"\']*)', player_cfg['_raw'])
            if murl:
                video_url = murl.group(1)
            else:
                murl = re.search(r'(https?://[^\s"\']+?\.mp4[^\s"\']*)', player_cfg['_raw'])
                if murl:
                    video_url = murl.group(1)
        
        # 规范化URL (补全 http 前缀)
        if video_url:
            if video_url.startswith('//'):
                video_url = 'https:' + video_url
            elif not video_url.startswith('http'):
                # 可能是域名+路径
                if '.' in video_url.split('/')[0] and not video_url.startswith('/'):
                    video_url = 'https://' + video_url
            
            if '.m3u8' in video_url:
                video_type = 'm3u8'
            elif '.mp4' in video_url:
                video_type = 'mp4'

            # 提取封面图：player_cfg 中的 pic/vod_pic/poster 等字段，兜底 og:image
            pic_url = ''
            if isinstance(player_cfg, dict):
                for pk in ['pic', 'vod_pic', 'poster', 'thumbnail', 'cover']:
                    pv = player_cfg.get(pk)
                    if isinstance(pv, str) and (pv.startswith('http') or pv.startswith('//')):
                        pic_url = pv
                        break
            if not pic_url:
                og_m = re.search(r'<meta\s+property="og:image"\s+content="([^"]+)"', html, re.I)
                if og_m:
                    pic_url = og_m.group(1).replace('&amp;', '&')
            if pic_url.startswith('//'):
                pic_url = 'https:' + pic_url

            print(f"    [+] 视频源: {video_type} -> {video_url[:180]}")
            if pic_url:
                print(f"    [+] 封面图: {pic_url[:120]}")
            return {
                'site': 'site3',
                'title': title or 'yp262-video',
                'source_url': play_url,
                'type': video_type,
                'url': video_url,
                'pic': pic_url,
                'player_keys': list(player_cfg.keys()) if isinstance(player_cfg, dict) else None,
            }
        else:
            print(f"    [-] 未能在player配置中找到视频URL")
            # 兜底封面：og:image
            _fb_pic = ''
            _og = re.search(r'<meta\s+property="og:image"\s+content="([^"]+)"', html, re.I)
            if _og:
                _fb_pic = _og.group(1).replace('&amp;', '&')
                if _fb_pic.startswith('//'):
                    _fb_pic = 'https:' + _fb_pic
            # 尝试找 player.js / 外部JS 里的播放逻辑
            play_js_urls = re.findall(r'<script[^>]+src="([^"]*player[^"]*\.js[^"]*)"', html, re.I)
            for ju in play_js_urls[:3]:
                full = urljoin(play_url, ju)
                print(f"    [*] 分析播放器JS: {full}")
                jr = safe_request(full)
                if jr:
                    m3u8s = re.findall(r'(https?://[^\s"\';]+\.m3u8[^\s"\';]*)', jr.text)
                    if m3u8s:
                        print(f"      [+] JS中发现m3u8: {m3u8s[0][:150]}")
                        return {'site': 'site3', 'title': title or 'yp262-video',
                                'source_url': play_url, 'type': 'm3u8', 'url': m3u8s[0],
                                'pic': _fb_pic}
            # 最后yt-dlp兜底
            ytu = try_ytdlp(play_url)
            if ytu:
                return {'site': 'site3', 'title': title or 'yp262-video',
                        'source_url': play_url, 'type': 'ytdlp', 'url': ytu[0],
                        'pic': _fb_pic}
    
    except Exception as e:
        import traceback
        print(f"    [!] player_aaaa 解密失败: {e}")
        traceback.print_exc()
    
    return None


# ============================================================
# 主
# ============================================================
def main():
    print("="*70)
    print("   三站点视频爬虫 - 最终版 (全量抓取)")
    print("   yp262 AES解密算法:  ECB / SHA256(key) / Pkcs7")
    print(f"   规模: 不限流全量抓取 (列表页无新链接则停止)")
    print("="*70)
    print(f"   pycryptodome: {'✓' if HAS_PYCRYPTODOME else '✗'}")
    print(f"   yt-dlp:        {'✓' if HAS_YTDLP else '✗'}")
    print(f"   下载目录:      {DOWNLOAD_DIR}")

    all_results = []

    # 逐站点抓取，每站完成后增量保存
    for site_fn, tag in [(parse_site1, 'site1'), (parse_site2, 'site2'), (parse_site3, 'site3')]:
        try:
            site_results = site_fn()
            all_results.extend(site_results)
            print(f"\n  [{tag}] 完成: {len(site_results)} 条, 累计 {len(all_results)} 条")
            _save_incremental(all_results, f'after-{tag}')
        except Exception as e:
            print(f"\n  [{tag}] 异常: {e}, 已保存当前结果")
            _save_incremental(all_results, f'after-{tag}-error')

    # 全局去重（按视频 URL）
    seen_urls = set()
    deduped = []
    for r in all_results:
        u = r.get('url', '')
        if u and u not in seen_urls:
            seen_urls.add(u)
            deduped.append(r)
    all_results = deduped

    print("\n" + "="*70)
    print("  最终汇总")
    print("="*70)
    if not all_results:
        print("  未能提取任何视频。")
        print("  建议:")
        print("   1. 确认网络可访问目标站点 (部分地区/IP可能被封)")
        print("   2. pip install pycryptodome yt-dlp ffmpeg-python")
        print("   3. 安装 ffmpeg (系统包管理器 apt install ffmpeg)")
        return

    # 按站点统计
    from collections import Counter
    site_counts = Counter(r.get('site', '?') for r in all_results)
    type_counts = Counter(r.get('type', '?') for r in all_results)
    print(f"  共提取 {len(all_results)} 个视频源 (已去重)")
    print(f"  按站点: {dict(site_counts)}")
    print(f"  按类型: {dict(type_counts)}")
    for i, r in enumerate(all_results[:20], 1):
        t = r.get('title', 'N/A')[:60]
        s = r.get('site', '?')
        vt = r.get('type', '?')
        print(f" [{i:2d}] {s} [{vt}] {t}")
    if len(all_results) > 20:
        print(f"  ... 共 {len(all_results)} 条，仅显示前 20 条")

    # 保存JSON
    _save_incremental(all_results, 'final')
    print(f"[+] 结果已保存 -> {JSON_PATH}")

    # 演示下载: 第一个m3u8
    m3u8_list = [r for r in all_results if r.get('type') == 'm3u8']
    if m3u8_list:
        first = m3u8_list[0]
        print(f"\n[演示下载] 第一个m3u8: {first.get('title','')[:60]}")
        download_m3u8(first['url'], first.get('title', 'video')[:60], referer=first.get('source_url'))
    else:
        print("\n暂无可演示下载的m3u8源。")


if __name__ == '__main__':
    main()
