#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
采集源可用性探测脚本
======================================================================
定期检查 MacCMS 采集站的搜索 / 详情 / 直链可用性，输出结构化结果，
用于筛选可用源、维护 server.py 中 SITES 配置的有效性。

用法:
    python deploy/probe-sources.py                 # 默认探测全部候选源
    python deploy/probe-sources.py --keyword 斗破  # 自定义搜索关键词
    python deploy/probe-sources.py --json          # 输出 JSON（便于 cron 落盘）
    python deploy/probe-sources.py --workers 8     # 并发数

判定规则:
    ok       —— 搜索有结果 + 详情接口通 + 直链含 .m3u8
    partial  —— 搜索通但详情/直链异常（仍可作为列表源）
    failed   —— 搜索接口不可用

候选源 CANDIDATES 与 server.py 的 SITES 保持一致，并额外收录全网常见
采集站以便发现新源。维护时：把 ok 且 latency 低的源优先级前移。
======================================================================
"""

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

# ============ 候选采集站配置 ============
# 与 server.py 的 SITES 对齐 + 额外候选，便于发现新可用源
CANDIDATES = [
    # —— server.py 当前在用 ——
    {"key": "ffzy",  "label": "飞速",   "base": "https://api.ffzyapi.com/api.php/provide/vod/",  "referer": "https://api.ffzyapi.com/"},
    {"key": "wuj",   "label": "无尽",   "base": "https://api.wujinapi.com/api.php/provide/vod/", "referer": "https://api.wujinapi.com/"},
    {"key": "lzi",   "label": "量子",   "base": "https://cj.lziapi.com/api.php/provide/vod/",    "referer": "https://cj.lziapi.com/"},
    {"key": "bdz",   "label": "百度云", "base": "https://api.apibdzy.com/api.php/provide/vod/",  "referer": "https://api.apibdzy.com/"},
    {"key": "ffzy2", "label": "飞速2",  "base": "https://cj.ffzyapi.com/api.php/provide/vod/",   "referer": "https://cj.ffzyapi.com/"},
    # —— 额外候选（可能不可用，用于发现新源）——
    {"key": "hong",  "label": "红牛",   "base": "https://api.hongniucj.com/api.php/provide/vod/", "referer": "https://api.hongniucj.com/"},
    {"key": "ksks",  "label": "快猫",   "base": "https://api.kuaimaocaiji.com/api.php/provide/vod/", "referer": "https://api.kuaimaocaiji.com/"},
    {"key": "max",   "label": "最大",   "base": "https://api.zdapi.com/api.php/provide/vod/",    "referer": "https://api.zdapi.com/"},
    {"key": "vma",   "label": "百川",   "base": "https://api.bczcj.com/api.php/provide/vod/",    "referer": "https://api.bczcj.com/"},
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "application/json, */*",
    "Accept-Language": "zh-CN,zh;q=0.9",
}

TIMEOUT = 10
DEFAULT_KEYWORD = "庆余年"


def _err(msg):
    """截断错误信息，避免输出过长"""
    s = str(msg)
    return s if len(s) <= 200 else s[:200] + "..."


def probe_source(source, keyword):
    """探测单个采集源的可用性

    返回结构:
        {
            key, label, status: ok|partial|failed, error,
            search: {success, count, latency},
            detail: {success, has_m3u8, latency, vod_id}
        }
    """
    result = {
        "key": source["key"],
        "label": source["label"],
        "status": "failed",
        "error": "",
        "search": {"success": False, "count": 0, "latency": 0.0},
        "detail": {"success": False, "has_m3u8": False, "latency": 0.0, "vod_id": ""},
    }
    headers = dict(HEADERS)
    headers["Referer"] = source["referer"]

    # 1) 测试搜索接口
    data = None
    try:
        start = time.time()
        params = {"ac": "videolist", "wd": keyword, "pg": 1}
        resp = requests.get(source["base"], params=params,
                            headers=headers, timeout=TIMEOUT)
        result["search"]["latency"] = round(time.time() - start, 2)
        data = resp.json()
        raw_list = data.get("list", []) or []
        if not raw_list and isinstance(data.get("vod"), dict):
            raw_list = data["vod"].get("list", []) or []
        result["search"]["count"] = len(raw_list)
        result["search"]["success"] = True
    except Exception as e:
        result["error"] = "search: " + _err(e)
        result["status"] = "failed"
        return result

    if not result["search"]["success"] or result["search"]["count"] == 0:
        result["error"] = "search: no results"
        result["status"] = "failed"
        return result

    # 2) 测试详情接口（取搜索结果第一个 vod_id）
    first = None
    try:
        first = data["list"][0] if data.get("list") else data["vod"]["list"][0]
    except Exception:
        pass
    if not first or not first.get("vod_id"):
        result["status"] = "partial"
        result["error"] = "detail: no vod_id in search result"
        return result

    vod_id = first["vod_id"]
    result["detail"]["vod_id"] = str(vod_id)
    try:
        start = time.time()
        params = {"ac": "detail", "ids": vod_id}
        resp = requests.get(source["base"], params=params,
                            headers=headers, timeout=TIMEOUT)
        result["detail"]["latency"] = round(time.time() - start, 2)
        detail_data = resp.json()
        raw_list = detail_data.get("list", []) or []
        if not raw_list and isinstance(detail_data.get("vod"), dict):
            raw_list = detail_data["vod"].get("list", []) or []
        if raw_list:
            result["detail"]["success"] = True
            play_url = str(raw_list[0].get("vod_play_url", ""))
            result["detail"]["has_m3u8"] = ".m3u8" in play_url.lower()
    except Exception as e:
        result["error"] = (result["error"] + " | " if result["error"] else "") + "detail: " + _err(e)

    # 3) 状态汇总
    if result["search"]["success"] and result["detail"]["success"] and result["detail"]["has_m3u8"]:
        result["status"] = "ok"
    elif result["search"]["success"]:
        result["status"] = "partial"
    else:
        result["status"] = "failed"
    return result


def probe_all(candidates, keyword, workers):
    """并发探测所有候选源，按状态 + 延迟排序返回列表"""
    results = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(probe_source, src, keyword): src for src in candidates}
        for future in as_completed(futures):
            try:
                results.append(future.result())
            except Exception as e:
                src = futures[future]
                results.append({
                    "key": src["key"], "label": src["label"],
                    "status": "failed", "error": "executor: " + _err(e),
                    "search": {"success": False, "count": 0, "latency": 0.0},
                    "detail": {"success": False, "has_m3u8": False, "latency": 0.0, "vod_id": ""},
                })
    # 排序：ok 优先，其次 partial，最后 failed；同状态按搜索延迟升序
    order = {"ok": 0, "partial": 1, "failed": 2}
    results.sort(key=lambda r: (order.get(r["status"], 3), r["search"]["latency"]))
    return results


def print_text(results, keyword):
    """人类可读的文本输出"""
    print(f"\n采集源探测结果  (关键词: {keyword})")
    print("=" * 72)
    ok = sum(1 for r in results if r["status"] == "ok")
    pa = sum(1 for r in results if r["status"] == "partial")
    fa = sum(1 for r in results if r["status"] == "failed")
    print(f"汇总: 共 {len(results)} 个源  →  ok={ok}  partial={pa}  failed={fa}\n")
    for r in results:
        st = r["status"].upper()
        print(f"[{st:7s}] {r['label']} ({r['key']})")
        s, d = r["search"], r["detail"]
        print(f"   搜索: {'OK ' if s['success'] else 'NO'} {s['count']}条  {s['latency']}s")
        print(f"   详情: {'OK ' if d['success'] else 'NO'} m3u8={'是' if d['has_m3u8'] else '否'}  {d['latency']}s")
        if r["error"]:
            print(f"   错误: {r['error']}")
        print()
    # 推荐 server.py 配置
    ok_sources = [r for r in results if r["status"] == "ok"]
    if ok_sources:
        print("推荐可用源（按延迟升序，可直接用于 server.py SITES）:")
        for r in ok_sources:
            c = next((c for c in CANDIDATES if c["key"] == r["key"]), None)
            if c:
                print(f"  {c['key']:8s} {c['label']:6s} base={c['base']}")
    else:
        print("⚠ 没有完全可用的源（搜索+详情+m3u8 全通），请检查网络或更换候选源。")


def main():
    parser = argparse.ArgumentParser(description="采集源可用性探测")
    parser.add_argument("--keyword", default=DEFAULT_KEYWORD, help="搜索关键词")
    parser.add_argument("--workers", type=int, default=5, help="并发请求数")
    parser.add_argument("--json", action="store_true", help="输出 JSON（便于落盘/上报）")
    args = parser.parse_args()

    print(f"开始探测 {len(CANDIDATES)} 个采集源 (workers={args.workers})...", file=sys.stderr)
    results = probe_all(CANDIDATES, args.keyword, args.workers)

    if args.json:
        print(json.dumps({
            "keyword": args.keyword,
            "timestamp": int(time.time()),
            "total": len(results),
            "ok": sum(1 for r in results if r["status"] == "ok"),
            "partial": sum(1 for r in results if r["status"] == "partial"),
            "failed": sum(1 for r in results if r["status"] == "failed"),
            "results": results,
        }, ensure_ascii=False, indent=2))
    else:
        print_text(results, args.keyword)


if __name__ == "__main__":
    main()