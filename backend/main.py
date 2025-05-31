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
from services.deepseek_service import get_deepseek_response
from services.sparkx1_service import get_sparkx1_response
from services.moonshot_service import get_moonshot_response
from services.fusion_service import get_fusion_response, get_advanced_fusion_response_direct

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


# 数据模型
class Model(BaseModel):
    id: str
    name: str
    apiKey: str
    url: str
    apiSecret: Optional[str] = None
    appId: Optional[str] = None

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

class FusionRequest(BaseModel):
    responses: List[Dict[str, str]]
    conversationId: Optional[str] = None

# 新增：高级融合请求模型
class AdvancedFusionRequest(BaseModel):
    query: str
    responses: List[Dict[str, str]]
    fusionMethod: Optional[str] = "rank_and_fuse"  # "rank_only", "fuse_only", "rank_and_fuse"
    topK: Optional[int] = 3
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
        "apiKey": os.environ.get("DEEPSEEK_API_KEY", ""),
        "url": os.environ.get("DEEPSEEK_API_BASE", "")
    },
    {
        "id": "sparkx1",
        "name": "讯飞SparkX1",
        "apiKey": os.environ.get("SPARKX1_API_KEY", ""),
        "apiSecret": os.environ.get("SPARKX1_API_SECRET", ""),
        "appId": os.environ.get("SPARKX1_APP_ID", ""),
        "url": os.environ.get("SPARKX1_API_BASE", "")
    }
]

for model in default_models:
    models[model["id"]] = model


@app.get("/api/models")
async def get_models():
    return JSONResponse(content=list(models.values()))

@app.post("/api/models")
async def add_model(model: Model):
    try:
        logger.info(f"收到添加模型请求: {model.id}")
        
        # 验证必要字段
        if not model.id or not model.name or not model.apiKey:
            error_msg = "缺少必要字段 (id, name, apiKey)"
            logger.error(error_msg)
            return JSONResponse(
                status_code=400,
                content={"detail": error_msg},
                headers={
                    "Access-Control-Allow-Origin": "http://localhost:3000",
                    "Access-Control-Allow-Credentials": "true"
                }
            )
        
        # 检查模型ID是否已存在
        if model.id in models:
            error_msg = f"模型ID {model.id} 已存在"
            logger.error(error_msg)
            return JSONResponse(
                status_code=400,
                content={"detail": error_msg},
                headers={
                    "Access-Control-Allow-Origin": "http://localhost:3000",
                    "Access-Control-Allow-Credentials": "true"
                }
            )
        
        # 添加模型
        model_dict = model.dict(exclude_unset=True)  # 只包含已设置的字段
        models[model.id] = model_dict
        logger.info(f"成功添加模型: {model.id}")
        
        return JSONResponse(
            content=model_dict,
            headers={
                "Access-Control-Allow-Origin": "http://localhost:3000",
                "Access-Control-Allow-Credentials": "true"
            }
        )
    except Exception as e:
        error_msg = f"添加模型时发生错误: {str(e)}"
        logger.error(f"{error_msg}\n{traceback.format_exc()}")
        return JSONResponse(
            status_code=500,
            content={"detail": error_msg},
            headers={
                "Access-Control-Allow-Origin": "http://localhost:3000",
                "Access-Control-Allow-Credentials": "true"
            }
        )

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
                response_content = None
                if model_id == "deepseek-chat":
                    response_content = await get_deepseek_response(request.message, history)
                elif model_id == "sparkx1":
                    response_content = await get_sparkx1_response(request.message, history)
                elif model_id == "moonshot":
                    # 获取moonshot的API配置
                    api_config = models.get(model_id)
                    if not api_config:
                        raise HTTPException(status_code=400, detail="Moonshot模型未配置")
                    response_content = await get_moonshot_response(request.message, history, api_config)
                else:
                    raise HTTPException(status_code=400, detail=f"不支持的模型ID: {model_id}")
                logger.info(f"收到AI响应: {response_content}")
                
                response = {
                    "modelId": model_id,
                    "content": response_content
                }
                responses.append(response)
                
                if conversation:
                    # 添加AI响应到会话
                    ai_message = {
                        "content": response_content,
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

@app.post("/api/fusion")
async def fusion_response(request: FusionRequest):
    try:
        logger.info(f"收到融合请求: {request.dict()}")
        
        if not request.responses or len(request.responses) < 2:
            return JSONResponse(
                status_code=400,
                content={"detail": "融合需要至少两个模型的回答"},
                headers={
                    "Access-Control-Allow-Origin": "http://localhost:3000",
                    "Access-Control-Allow-Credentials": "true"
                }
            )
        
        # 获取会话历史（如果有）
        history = []
        if request.conversationId and request.conversationId in conversations:
            conversation = conversations[request.conversationId]
            history = [
                {"role": msg["role"], "content": msg["content"]}
                for msg in conversation["messages"][:-1]  # 不包括最新的用户消息
            ]
        
        # 调用融合服务
        fused_content = await get_fusion_response(request.responses, history)
        
        # 如果存在会话ID，将融合结果添加到会话历史
        if request.conversationId and request.conversationId in conversations:
            fusion_message = {
                "content": fused_content,
                "role": "assistant",
                "model": "fusion",
                "timestamp": datetime.utcnow().isoformat()
            }
            conversations[request.conversationId]["messages"].append(fusion_message)
            logger.info(f"添加融合回答到会话: {fusion_message}")
        
        return JSONResponse(
            status_code=200,
            content={"fusedContent": fused_content},
            headers={
                "Access-Control-Allow-Origin": "http://localhost:3000",
                "Access-Control-Allow-Credentials": "true"
            }
        )
        
    except Exception as e:
        error_msg = f"处理融合请求时发生错误: {str(e)}\n{traceback.format_exc()}"
        logger.error(error_msg)
        return JSONResponse(
            status_code=500,
            content={"detail": error_msg},
            headers={
                "Access-Control-Allow-Origin": "http://localhost:3000",
                "Access-Control-Allow-Credentials": "true"
            }
        )

@app.post("/api/fusion/advanced")
async def advanced_fusion_response(request: AdvancedFusionRequest):
    """
    高级融合接口 - 使用 LLM-Blender 进行智能融合
    
    支持三种融合模式：
    - rank_only: 只进行质量排序，返回最优回答
    - fuse_only: 只进行生成融合，不排序
    - rank_and_fuse: 先排序再融合（推荐）
    """
    try:
        logger.info(f"收到高级融合请求: {request.dict()}")
        
        if not request.responses or len(request.responses) < 1:
            return JSONResponse(
                status_code=400,
                content={"detail": "融合需要至少一个模型的回答"},
                headers={
                    "Access-Control-Allow-Origin": "http://localhost:3000",
                    "Access-Control-Allow-Credentials": "true"
                }
            )
        
        # 转换响应格式以匹配服务接口
        formatted_responses = []
        for resp in request.responses:
            formatted_responses.append({
                "modelId": resp.get("modelId", "unknown"),
                "content": resp.get("content", "")
            })
        
        # 调用高级融合服务
        start_time = datetime.utcnow()
        result = await get_advanced_fusion_response_direct(
            query=request.query,
            responses=formatted_responses,
            fusion_method=request.fusionMethod,
            top_k=request.topK
        )
        end_time = datetime.utcnow()
        
        # 计算处理时间
        processing_time = (end_time - start_time).total_seconds()
        result["processing_time"] = processing_time
        
        # 如果存在会话ID，将融合结果添加到会话历史
        if request.conversationId and request.conversationId in conversations:
            fusion_message = {
                "content": result["fused_content"],
                "role": "assistant",
                "model": "llm_blender",
                "fusion_method": result.get("fusion_method", "unknown"),
                "models_used": result.get("models_used", []),
                "timestamp": end_time.isoformat()
            }
            conversations[request.conversationId]["messages"].append(fusion_message)
            logger.info(f"添加高级融合回答到会话: {fusion_message}")
        
        logger.info(f"✅ 高级融合完成，方法: {result.get('fusion_method')}, 耗时: {processing_time:.2f}s")
        
        return JSONResponse(
            status_code=200,
            content={
                "fusedContent": result["fused_content"],
                "rankedResponses": result.get("ranked_responses", []),
                "bestResponse": result.get("best_response"),
                "fusionMethod": result.get("fusion_method"),
                "modelsUsed": result.get("models_used", []),
                "processingTime": processing_time,
                "error": result.get("error")
            },
            headers={
                "Access-Control-Allow-Origin": "http://localhost:3000",
                "Access-Control-Allow-Credentials": "true"
            }
        )
        
    except Exception as e:
        error_msg = f"处理高级融合请求时发生错误: {str(e)}\n{traceback.format_exc()}"
        logger.error(error_msg)
        return JSONResponse(
            status_code=500,
            content={"detail": error_msg},
            headers={
                "Access-Control-Allow-Origin": "http://localhost:3000",
                "Access-Control-Allow-Credentials": "true"
            }
        )

@app.get("/api/fusion/status")
async def fusion_status():
    """
    获取融合服务状态
    """
    try:
        from services.llm_blender_service import get_blender_service
        
        # 尝试获取服务状态
        try:
            service = await get_blender_service()
            status = {
                "llm_blender_available": True,
                "ranker_loaded": service.ranker_loaded,
                "fuser_loaded": service.fuser_loaded,
                "is_initialized": service.is_initialized,
                "supported_methods": ["rank_only", "fuse_only", "rank_and_fuse"],
                "recommended_method": "rank_and_fuse" if service.fuser_loaded else "rank_only"
            }
        except Exception as e:
            status = {
                "llm_blender_available": False,
                "ranker_loaded": False,
                "fuser_loaded": False,
                "is_initialized": False,
                "error": str(e),
                "fallback_available": True,
                "supported_methods": ["traditional_fusion"]
            }
        
        return JSONResponse(
            status_code=200,
            content=status,
            headers={
                "Access-Control-Allow-Origin": "http://localhost:3000",
                "Access-Control-Allow-Credentials": "true"
            }
        )
        
    except Exception as e:
        error_msg = f"获取融合状态时发生错误: {str(e)}"
        logger.error(error_msg)
        return JSONResponse(
            status_code=500,
            content={"detail": error_msg},
            headers={
                "Access-Control-Allow-Origin": "http://localhost:3000",
                "Access-Control-Allow-Credentials": "true"
            }
        )

@app.delete("/api/models/{model_id}")
async def delete_model(model_id: str):
    try:
        logger.info(f"收到删除模型请求: {model_id}")
        
        # 检查模型是否存在
        if model_id not in models:
            error_msg = f"模型 {model_id} 不存在"
            logger.error(error_msg)
            return JSONResponse(
                status_code=404,
                content={"detail": error_msg},
                headers={
                    "Access-Control-Allow-Origin": "http://localhost:3000",
                    "Access-Control-Allow-Credentials": "true"
                }
            )
        
        # 检查是否为默认模型
        if any(model["id"] == model_id for model in default_models):
            error_msg = f"不能删除默认模型: {model_id}"
            logger.error(error_msg)
            return JSONResponse(
                status_code=400,
                content={"detail": error_msg},
                headers={
                    "Access-Control-Allow-Origin": "http://localhost:3000",
                    "Access-Control-Allow-Credentials": "true"
                }
            )
        
        # 从选中的模型列表中移除
        global selected_models
        if model_id in selected_models:
            selected_models.remove(model_id)
        
        # 删除模型
        deleted_model = models.pop(model_id)
        logger.info(f"成功删除模型: {model_id}")
        
        return JSONResponse(
            content={"message": f"模型 {model_id} 已成功删除", "model": deleted_model},
            headers={
                "Access-Control-Allow-Origin": "http://localhost:3000",
                "Access-Control-Allow-Credentials": "true"
            }
        )
    except Exception as e:
        error_msg = f"删除模型时发生错误: {str(e)}"
        logger.error(f"{error_msg}\n{traceback.format_exc()}")
        return JSONResponse(
            status_code=500,
            content={"detail": error_msg},
            headers={
                "Access-Control-Allow-Origin": "http://localhost:3000",
                "Access-Control-Allow-Credentials": "true"
            }
        )
