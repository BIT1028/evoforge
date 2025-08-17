#!/usr/bin/env python3
"""
后端服务器启动脚本
"""

import os
import sys
import uvicorn
from pathlib import Path

# 添加当前目录到Python路径
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# 设置环境变量
os.environ.setdefault("PYTHONPATH", str(current_dir))

if __name__ == "__main__":
    print("启动喀迈拉计划后端服务器...")
    print(f"当前工作目录: {current_dir}")
    print(f"Python路径: {sys.path[0]}")
    
    try:
        # 测试导入应用
        from app.main import app
        print("应用导入成功")
        
        # 启动服务器 - 使用import字符串以支持reload
        uvicorn.run(
            "app.main:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            reload_dirs=[str(current_dir)],
            log_level="info"
        )
    except ImportError as e:
        print(f"导入错误: {e}")
        print("请确保所有依赖已正确安装")
        sys.exit(1)
    except Exception as e:
        print(f"启动失败: {e}")
        sys.exit(1)