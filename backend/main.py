from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional, Dict
import json
from datetime import datetime
import httpx
import os
import asyncio
import logging
import traceback

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI()

# 配置CORS - 添加更多允许的头部和方法
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)

# 添加测试路由
@app.get("/api/test")
async def test():
    logger.info("测试路由被调用")
    return JSONResponse(
        content={"message": "API服务正常运行"},
        headers={
            "Access-Control-Allow-Origin": "http://localhost:3000",
            "Access-Control-Allow-Credentials": "true"
        }
    )

# Deepseek API配置
DEEPSEEK_API_KEY = "sk-1b4d26d8de8e4493b9bc15d218ce158d"
DEEPSEEK_API_BASE = "https://api.deepseek.com/v1"

# 数据模型
class Model(BaseModel):
    id: str
    name: str
    apiKey: str
    url: str

class Message(BaseModel):
    content: str
    role: str
    timestamp: str

class Conversation(BaseModel):
    id: str
    title: str
    messages: List[Message]
    models: List[str]

class ModelResponse(BaseModel):
    modelId: str
    content: str

class MessageRequest(BaseModel):
    message: str
    modelIds: List[str]
    conversationId: Optional[str] = None

# 内存存储
models = {}
selected_models = []
conversations = {}

# 初始化默认模型
default_models = [
    {
        "id": "deepseek-chat",
        "name": "Deepseek Chat",
        "apiKey": DEEPSEEK_API_KEY,
        "url": DEEPSEEK_API_BASE
    }
]

for model in default_models:
    models[model["id"]] = model

async def get_deepseek_response(message: str, conversation_history: List[Dict] = None) -> str:
    """调用Deepseek API获取响应"""
    async with httpx.AsyncClient() as client:
        headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        }
        
        messages = []
        if conversation_history:
            messages.extend(conversation_history)
        messages.append({"role": "user", "content": message})
        
        try:
            logger.info(f"发送请求到Deepseek API: {DEEPSEEK_API_BASE}/chat/completions")
            logger.info(f"消息历史: {messages}")
            
            payload = {
                "model": "deepseek-chat",
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 2000
            }
            
            response = await client.post(
                f"{DEEPSEEK_API_BASE}/chat/completions",
                headers=headers,
                json=payload,
                timeout=30.0
            )
            
            logger.info(f"Deepseek API响应状态码: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Deepseek API响应: {result}")
                if "choices" in result and len(result["choices"]) > 0:
                    return result["choices"][0]["message"]["content"]
                else:
                    raise HTTPException(status_code=500, 
                                      detail="Deepseek API返回的响应格式不正确")
            else:
                logger.error(f"Deepseek API错误响应: {response.text}")
                raise HTTPException(status_code=response.status_code, 
                                  detail=f"Deepseek API错误: {response.text}")
        except Exception as e:
            logger.error(f"处理Deepseek API响应时发生错误: {str(e)}")
            raise HTTPException(status_code=500, 
                              detail=f"调用Deepseek API时发生错误: {str(e)}")

@app.get("/api/models")
async def get_models():
    return JSONResponse(content=list(models.values()))

@app.post("/api/models")
async def add_model(model: Model):
    if model.id in models:
        raise HTTPException(status_code=400, detail="模型ID已存在")
    models[model.id] = model.dict()
    return JSONResponse(content=model.dict())

@app.post("/api/models/selection")
async def update_model_selection(model_ids: List[str]):
    global selected_models
    for model_id in model_ids:
        if model_id not in models:
            raise HTTPException(status_code=400, detail=f"找不到模型ID {model_id}")
    selected_models = model_ids
    return JSONResponse(content={"selected_models": selected_models})

@app.post("/api/chat")
async def chat(request: MessageRequest):
    try:
        logger.info(f"收到聊天请求: {request.dict()}")
        
        if not request.modelIds:
            logger.error("模型ID列表为空")
            return JSONResponse(
                status_code=400,
                content={"detail": "模型ID不能为空"},
                headers={
                    "Access-Control-Allow-Origin": "http://localhost:3000",
                    "Access-Control-Allow-Credentials": "true"
                }
            )
        
        # 验证所有模型ID
        for model_id in request.modelIds:
            if model_id not in models:
                logger.error(f"找不到模型ID: {model_id}")
                return JSONResponse(
                    status_code=400,
                    content={"detail": f"找不到模型ID {model_id}"},
                    headers={
                        "Access-Control-Allow-Origin": "http://localhost:3000",
                        "Access-Control-Allow-Credentials": "true"
                    }
                )
        
        # 获取或创建会话
        conversation = None
        if request.conversationId:
            if request.conversationId not in conversations:
                logger.info(f"创建新会话: {request.conversationId}")
                conversations[request.conversationId] = {
                    "id": request.conversationId,
                    "title": f"对话 {len(conversations) + 1}",
                    "messages": [],
                    "models": request.modelIds
                }
            conversation = conversations[request.conversationId]
            logger.info(f"当前会话信息: {conversation}")
        
        # 添加用户消息
        user_message = {
            "content": request.message,
            "role": "user",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if conversation:
            conversation["messages"].append(user_message)
            logger.info(f"添加用户消息到会话: {user_message}")
        
        # 获取AI响应
        responses = []
        for model_id in request.modelIds:
            try:
                # 准备会话历史
                history = []
                if conversation:
                    for msg in conversation["messages"][:-1]:  # 不包含刚刚添加的用户消息
                        history.append({
                            "role": msg["role"],
                            "content": msg["content"]
                        })
                    logger.info(f"会话历史: {history}")
                
                logger.info(f"正在调用模型 {model_id} 的API")
                ai_content = await get_deepseek_response(request.message, history)
                logger.info(f"收到AI响应: {ai_content}")
                
                response = {
                    "modelId": model_id,
                    "content": ai_content
                }
                responses.append(response)
                
                if conversation:
                    # 添加AI响应到会话
                    ai_message = {
                        "content": ai_content,
                        "role": "assistant",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    conversation["messages"].append(ai_message)
                    logger.info(f"添加AI响应到会话: {ai_message}")
                    
            except Exception as e:
                error_msg = f"处理模型 {model_id} 的响应时发生错误: {str(e)}\n{traceback.format_exc()}"
                logger.error(error_msg)
                return JSONResponse(
                    status_code=500,
                    content={"detail": error_msg},
                    headers={
                        "Access-Control-Allow-Origin": "http://localhost:3000",
                        "Access-Control-Allow-Credentials": "true"
                    }
                )
        
        response_data = {"responses": responses}
        logger.info(f"返回最终响应: {response_data}")
        return JSONResponse(
            status_code=200,
            content=response_data,
            headers={
                "Access-Control-Allow-Origin": "http://localhost:3000",
                "Access-Control-Allow-Credentials": "true",
                "Content-Type": "application/json"
            }
        )
    
    except Exception as e:
        error_msg = f"处理聊天请求时发生错误: {str(e)}\n{traceback.format_exc()}"
        logger.error(error_msg)
        return JSONResponse(
            status_code=500,
            content={"detail": error_msg},
            headers={
                "Access-Control-Allow-Origin": "http://localhost:3000",
                "Access-Control-Allow-Credentials": "true"
            }
        ) 