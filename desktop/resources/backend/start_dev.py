"""启动脚本 — 设置环境变量后启动 uvicorn"""
import os
import sys

# LLM 配置通过环境变量设置，参见 config.py 中的 LLM_* 配置项
# 开发时可设置 .env 文件或通过 export/set 命令传入

import uvicorn
uvicorn.run("app.main:app", host="127.0.0.1", port=8000)
