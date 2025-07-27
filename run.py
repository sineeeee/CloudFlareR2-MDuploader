#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import subprocess
import sys
import os

def install_requirements():
    """安装必要的依赖"""
    print("正在安装依赖...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ 依赖安装完成")
    except subprocess.CalledProcessError:
        print("❌ 依赖安装失败，请手动运行: pip install -r requirements.txt")
        return False
    return True

def main():
    print("🚀 Markdown 图片上传器启动中...")
    
    # 检查依赖文件是否存在
    if not os.path.exists("requirements.txt"):
        print("❌ 未找到 requirements.txt 文件")
        return
    
    # 安装依赖
    if not install_requirements():
        return
    
    # 启动Flask应用
    print("\n🌐 启动Web服务器...")
    print("📱 请在浏览器中访问: http://localhost:5001")
    print("🛑 按 Ctrl+C 停止服务")
    
    try:
        from app import app
        app.run(debug=True, host='0.0.0.0', port=5001)
    except ImportError:
        print("❌ 未找到 app.py 文件")
    except KeyboardInterrupt:
        print("\n👋 服务已停止")
    except Exception as e:
        print(f"❌ 启动失败: {e}")

if __name__ == "__main__":
    main() 