#!/usr/bin/env bash
set -e

# 进入脚本所在目录
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

# 检查虚拟环境
if [ ! -d ".venv" ]; then
    echo "⚡ 正在创建 Python 独立虚拟环境..."
    python3 -m venv .venv
    .venv/bin/pip install --upgrade pip
    .venv/bin/pip install -r requirements.txt
fi

echo "🚀 启动屏幕自动点击工具..."
.venv/bin/python main.py "$@"
