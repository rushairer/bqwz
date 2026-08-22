#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

echo "=========================================="
echo "      macOS AutoClicker.app 打包脚本      "
echo "=========================================="

# 1. 确保虚拟环境存在并安装必要依赖
if [ ! -d ".venv" ]; then
    echo "⚡ 创建虚拟环境..."
    python3 -m venv .venv
    .venv/bin/pip install --upgrade pip
fi

echo "📦 检查/安装打包依赖..."
.venv/bin/pip install -r requirements.txt
.venv/bin/pip install pyinstaller pillow

# 2. 如果不存在 AppIcon.icns，则自动生成
if [ ! -f "AppIcon.icns" ]; then
    echo "🎨 正在生成应用高清图标..."
    .venv/bin/python generate_icon.py
fi

# 3. 清理旧构建缓存
echo "🧹 清理旧构建目录..."
rm -rf build dist AutoClicker.spec

# 4. 执行 PyInstaller 打包
echo "🚀 开始编译封装 macOS .app 应用..."
.venv/bin/pyinstaller \
    --noconsole \
    --windowed \
    --name "AutoClicker" \
    --icon "AppIcon.icns" \
    --osx-bundle-identifier "com.rushairer.autoclicker" \
    --collect-all customtkinter \
    --collect-all pynput \
    main.py

# 5. 移除 macOS 隔离属性，保证本地双击不被 Gatekeeper 阻止
if [ -d "dist/AutoClicker.app" ]; then
    echo "🔓 清除 Gatekeeper 隔离属性..."
    xattr -cr "dist/AutoClicker.app" || true
    echo ""
    echo "=========================================="
    echo "🎉 打包完成！"
    echo "📁 应用路径: dist/AutoClicker.app"
    echo "👉 你可以直接在 Finder 中双击 dist/AutoClicker.app 运行，"
    echo "   或者将它拖动到【应用程序 (Applications)】文件夹中！"
    echo "=========================================="
fi
