from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import uvicorn

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
    {"id": "gpt-3.5-turbo", "name": "GPT-3.5 Turbo", "apiKey": ""},
    {"id": "gpt-4", "name": "GPT-4", "apiKey": ""},
    {"id": "claude-2", "name": "Claude 2", "apiKey": ""}
]

conversations = {}
selected_models = []

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
    # 这里应该实现实际的AI模型调用
    # 现在返回模拟响应
    responses = []
    for model_id in request.modelIds:
        responses.append({
            "modelId": model_id,
            "content": f"This is a mock response from {model_id} for: {request.message}"
        })
    
    return {"responses": responses}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) 