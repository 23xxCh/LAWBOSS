"""CrossGuard 后端启动脚本 — 由 Electron 桌面客户端调用"""
import os
import sys

# 确保工作目录是 backend 目录
os.chdir(os.path.dirname(os.path.abspath(__file__)))

import uvicorn
uvicorn.run("app.main:app", host="127.0.0.1", port=8000, log_level="info")
