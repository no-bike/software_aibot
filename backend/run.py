import uvicorn
import os
import configparser

if __name__ == "__main__":
    # 从api.txt读取配置
    config = configparser.ConfigParser()
    config.read('backend/api.txt')
    
    # 设置环境变量
    os.environ["DEEPSEEK_API_KEY"] = config['DEEPSEEK']['API_KEY']
    os.environ["DEEPSEEK_API_BASE"] = config['DEEPSEEK']['API_BASE']
    
    # 启动服务器
    uvicorn.run(
        "main:app",
        host="localhost",
        port=8000,
        reload=True,
        log_level="info"
    )
