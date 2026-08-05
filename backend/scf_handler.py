#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
腾讯云 SCF 云函数入口 —— 把 API Gateway 触发器事件转成 Flask WSGI 请求。

部署方式（两种任选）：
  方式 A：网页控制台上传 zip
    1. 把 server.py / requirements.txt / scf_handler.py 打 zip
    2. SCF 控制台 → 新建函数 → 自定义创建 → 运行环境 Python 3.9/3.10/3.11
    3. 执行方法：scf_handler.main_handler
    4. 上传 zip → 部署 → 配置 API Gateway 触发器（HTTP API，APIGW 响应集成）

  方式 B：Serverless Framework CLI
    sls deploy（需装 serverless + serverless-tencent 插件，已在 serverless.yml 配置好）

免费额度：
  · 资源使用量：40 万 GBs/月（约等于 128MB 内存函数跑 267 小时，个人用绰绰有余）
  · 调用次数：100 万次/月
"""

import base64
import io
import os
import sys
from urllib.parse import unquote

# ========= 确保 scf 能找到同级目录的 server.py =========
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from server import app  # noqa: E402 —— Flask 应用实例

# ========= Flask 应用已在 server.py 里设置了生产级配置（请求头/CORS） =========


# ====================================================================
#  工具：APIGW event → WSGI environ
#  参考 werkzeug.contrib.wrappers / serverless-wsgi，做了 SCF 特定适配
# ====================================================================
def _build_environ(event: dict) -> dict:
    headers = event.get("headers") or {}
    # SCF 的 headers 大小写不统一，做一次小写映射备用
    lower_headers = {str(k).lower(): str(v) for k, v in headers.items()}

    method = str(event.get("httpMethod") or "GET").upper()
    path = event.get("path") or "/"
    qs = event.get("queryString") or event.get("queryStringParameters") or {}
    query_string = "&".join(f"{k}={_urlenc(v)}" for k, v in qs.items())

    # body 处理
    body_bytes = b""
    if "body" in event and event["body"]:
        if event.get("isBase64Encoded"):
            try:
                body_bytes = base64.b64decode(event["body"])
            except Exception:
                body_bytes = str(event["body"]).encode("utf-8", errors="replace")
        else:
            body_bytes = str(event["body"]).encode("utf-8", errors="replace")

    # WSGI environ 必填项（PEP 3333）
    environ = {
        "REQUEST_METHOD": method,
        "SCRIPT_NAME": "",
        "PATH_INFO": unquote(path),
        "QUERY_STRING": query_string,
        "CONTENT_TYPE": lower_headers.get("content-type", ""),
        "CONTENT_LENGTH": str(len(body_bytes)) if body_bytes else "0",
        "SERVER_NAME": lower_headers.get("host", "localhost"),
        "SERVER_PORT": lower_headers.get("x-forwarded-port", "443"),
        "SERVER_PROTOCOL": "HTTP/1.1",
        "wsgi.version": (1, 0),
        "wsgi.url_scheme": lower_headers.get("x-forwarded-proto", "https"),
        "wsgi.input": io.BytesIO(body_bytes),
        "wsgi.errors": sys.stderr,
        "wsgi.multithread": False,
        "wsgi.multiprocess": False,
        "wsgi.run_once": False,
    }

    # HTTP_* 头
    for k, v in headers.items():
        key = str(k).upper().replace("-", "_")
        if key in ("CONTENT_TYPE", "CONTENT_LENGTH"):
            continue
        environ[f"HTTP_{key}"] = str(v)

    return environ


def _urlenc(v) -> str:
    from urllib.parse import quote
    return quote(str(v) if v is not None else "")


# ====================================================================
#  SCF 主入口（必须叫 main_handler 或配置执行方法名时匹配）
# ====================================================================
def main_handler(event: dict, context) -> dict:
    """腾讯云 SCF API Gateway 触发器入口函数。

    event 结构（APIGW 触发集成模式）：
    {
      "httpMethod": "GET",
      "path": "/api/health",
      "headers": { "Host": "...", "User-Agent": "...", ... },
      "queryString": { "wd": "庆余年" },
      "body": "...",
      "isBase64Encoded": false,
      ...
    }
    """
    environ = _build_environ(event)
    status_out = {"code": 0, "status": "200 OK", "headers": {}}

    def start_response(status, response_headers, exc_info=None):
        status_out["status"] = str(status)
        status_out["code"] = int(str(status).split(" ")[0])
        # response_headers 是 [(k, v), ...]；SCF APIGW 要求 header 是 dict，
        # 同名字段用逗号拼接（Flask 可能给多个 Set-Cookie，按逗号分隔）
        hdrs = {}
        for k, v in response_headers:
            key, val = str(k), str(v)
            if key in hdrs and key.lower() == "set-cookie":
                # 多条 Set-Cookie 不能用逗号拼（HTTP 规范），按 "\n" 分，APIGW 兼容
                hdrs[key] = hdrs[key] + "\n" + val
            elif key in hdrs:
                hdrs[key] = hdrs[key] + ", " + val
            else:
                hdrs[key] = val
        status_out["headers"] = hdrs

    try:
        response_iter = app(environ, start_response)
        body_bytes = b"".join(response_iter)
    except Exception as e:
        # 兜底错误响应，避免 SCF 直接 500
        app.logger.exception("SCF handler exception: %s", e)
        status_out["status"] = "500 Internal Server Error"
        status_out["code"] = 500
        status_out["headers"] = {"Content-Type": "application/json"}
        body_bytes = ('{"code":-1,"msg":"internal error: %s"}' % e).encode("utf-8", errors="replace")

    # 判断是否 base64 返回：二进制流（m3u8/ts/图片）需要 base64
    ctype = str(status_out["headers"].get("Content-Type", "")).lower()
    is_text = (
        "text/" in ctype
        or "application/json" in ctype
        or "application/javascript" in ctype
        or "application/vnd.apple.mpegurl" in ctype  # m3u8 是文本，直接字符串 OK
        or "xml" in ctype
    )
    is_binary = (
        "octet-stream" in ctype
        or "image/" in ctype
        or "video/" in ctype
        or "audio/" in ctype
        or ctype.endswith(".ts")   # 文本识别漏网的视频 ts
    )

    # /api/stream 下的 m3u8/ts 需要原样返回，SCF 有 body size 限制（6MB），
    # 超 6MB 建议在客户端直链或 COS 托管，这里尽量文本返回
    if is_text and not is_binary:
        body_str = body_bytes.decode("utf-8", errors="replace")
        is_b64 = False
    else:
        body_str = base64.b64encode(body_bytes).decode("ascii")
        is_b64 = True

    return {
        "isBase64Encoded": is_b64,
        "statusCode": status_out["code"],
        "headers": status_out["headers"],
        "body": body_str,
    }


# ====================================================================
#  本地调试（python scf_handler.py 时直接测试 /api/health）
# ====================================================================
if __name__ == "__main__":
    sample_event = {
        "httpMethod": "GET",
        "path": "/api/health",
        "headers": {
            "Host": "localhost",
            "User-Agent": "scf-local-test/1.0",
            "Accept": "application/json",
        },
        "queryString": {},
        "body": "",
        "isBase64Encoded": False,
    }
    result = main_handler(sample_event, None)
    print("status:", result["statusCode"])
    print("headers:", result["headers"])
    print("body:", result["body"][:500])
