from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
import openai
import anthropic
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

app = FastAPI()

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # 前端开发服务器地址
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
models = [
    {"id": "gpt-3.5-turbo", "name": "GPT-3.5 Turbo", "apiKey": "", "url": "https://api.openai.com/v1"},
    {"id": "gpt-4", "name": "GPT-4", "apiKey": "", "url": "https://api.openai.com/v1"},
    {"id": "claude-2", "name": "Claude 2", "apiKey": "", "url": "https://api.anthropic.com"}
]

conversations = {}
selected_models = []

async def get_openai_response(model_id: str, message: str, api_key: str, url: str) -> str:
    """获取OpenAI模型的响应"""
    try:
        client = openai.OpenAI(api_key=api_key, base_url=url)
        response = client.chat.completions.create(
            model=model_id,
            messages=[{"role": "user", "content": message}],
            temperature=0.7,
            max_tokens=1000
        )
        return response.choices[0].message.content
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OpenAI API error: {str(e)}")

async def get_claude_response(message: str, api_key: str, url: str) -> str:
    """获取Claude模型的响应"""
    try:
        client = anthropic.Anthropic(api_key=api_key, base_url=url)
        response = client.messages.create(
            model="claude-2",
            max_tokens=1000,
            messages=[{"role": "user", "content": message}]
        )
        return response.content[0].text
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Claude API error: {str(e)}")

@app.get("/api/models")
async def get_models():
    return models

@app.post("/api/models")
async def add_model(model: Model):
    # 检查模型ID是否已存在
    if any(m["id"] == model.id for m in models):
        raise HTTPException(status_code=400, detail="Model ID already exists")
    
    models.append(model.dict())
    return model

@app.post("/api/models/selection")
async def update_model_selection(model_ids: List[str]):
    global selected_models
    selected_models = model_ids
    return {"selected_models": selected_models}

@app.post("/api/chat")
async def send_message(request: MessageRequest):
    responses = []
    
    for model_id in request.modelIds:
        # 获取模型信息
        model_info = next((m for m in models if m["id"] == model_id), None)
        if not model_info:
            raise HTTPException(status_code=400, detail=f"Model {model_id} not found")
        
        # 获取API密钥和URL
        api_key = model_info["apiKey"]
        url = model_info["url"]
        if not api_key:
            raise HTTPException(status_code=400, detail=f"API key not set for model {model_id}")
        
        try:
            # 根据模型类型调用相应的API
            if model_id.startswith("gpt"):
                content = await get_openai_response(model_id, request.message, api_key, url)
            elif model_id == "claude-2":
                content = await get_claude_response(request.message, api_key, url)
            else:
                raise HTTPException(status_code=400, detail=f"Unsupported model: {model_id}")
            
            responses.append({
                "modelId": model_id,
                "content": content
            })
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    return {"responses": responses}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) 