import uvicorn
import os
import configparser
import sys
from pathlib import Path

if __name__ == "__main__":
    # 确保正确的工作目录
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    # 从api.txt读取配置
    config = configparser.ConfigParser()
    api_file = Path('api.txt')
    
    if not api_file.exists():
        print(f"❌ 错误：找不到 api.txt 文件，当前目录: {os.getcwd()}")
        sys.exit(1)
    
    config.read('api.txt')
    print("✅ 成功读取 api.txt 配置文件")
    
    # 设置环境变量 - 修正变量名称匹配
    if 'DEEPSEEK' in config:
        os.environ["DEEPSEEK_API_KEY"] = config['DEEPSEEK']['API_KEY']
        os.environ["DEEPSEEK_API_BASE"] = config['DEEPSEEK']['API_BASE']
        print(f"✅ 已设置 DEEPSEEK API 配置")
    
    if 'SPARKX1' in config:
        # 注意：api.txt中是API_TOKEN，但服务需要SPARKX1_API_KEY
        os.environ["SPARKX1_API_KEY"] = config['SPARKX1']['API_TOKEN']  # 从API_TOKEN读取
        os.environ["SPARKX1_API_BASE"] = config['SPARKX1']['API_BASE']
        print(f"✅ 已设置 SPARKX1 API 配置")
    
    if 'QWEN' in config:
        os.environ["QWEN_API_KEY"] = config['QWEN']['API_KEY']
        os.environ["QWEN_API_BASE"] = config['QWEN']['API_BASE']
        print(f"✅ 已设置 QWEN API 配置")
    
    print(f"🚀 启动服务器 localhost:8000")
    
    # 启动服务器
    uvicorn.run(
        "main:app",
        host="localhost", 
        port=8000,
        reload=True,
        log_level="info"
    )
