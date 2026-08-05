#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Vercel Serverless Functions 入口
Vercel Python runtime 会自动识别名为 app 的 WSGI 变量。
"""

import sys
import os

# 确保能找到项目根目录的 server.py
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

# 直接导入 Flask app
from server import app

# Vercel 需要一个叫 app 的 WSGI 变量
# 这里确保 app 可被 Vercel 正确识别
application = app
