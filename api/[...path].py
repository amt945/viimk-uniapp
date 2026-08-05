#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Vercel 捕获所有路由的入口文件
文件名 [...path] 会被 Vercel 识别为 catch-all 路由
"""

import sys
import os

# 确保能找到项目根目录的 server.py
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from server import app

# Vercel 会自动识别这个 WSGI app
# 注意：变量名必须是 app 或 application
