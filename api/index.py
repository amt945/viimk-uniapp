#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Vercel Serverless Functions 入口
Vercel Python runtime 会自动识别 WSGI app 变量。
"""

import sys
import os

# 确保能找到项目根目录的 server.py
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from server import app  # noqa: F401
