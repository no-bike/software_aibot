import uvicorn
import os

if __name__ == "__main__":
    # 设置环境变量
    os.environ["DEEPSEEK_API_KEY"] = "sk-1b4d26d8de8e4493b9bc15d218ce158d"
    os.environ["DEEPSEEK_API_BASE"] = "https://api.deepseek.com/v1"
    
    # 启动服务器
    uvicorn.run(
        "main:app",
        host="localhost",
        port=8000,
        reload=True,
        log_level="info"
    ) 