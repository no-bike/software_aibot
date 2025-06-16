from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict
import json
from datetime import datetime, timezone, timedelta
import httpx
import os
import asyncio
import logging
import traceback
from services.deepseek_service import get_deepseek_response, get_deepseek_stream_response
from services.sparkx1_service import get_sparkx1_response, get_sparkx1_stream_response
from services.moonshot_service import get_moonshot_response, get_moonshot_stream_response
from services.qwen_service import get_qwen_response, get_qwen_stream_response
from services.fusion_service import get_fusion_response, get_advanced_fusion_response_direct
from services.mongodb_service import mongodb_service
from services.auth_routes import router as auth_router

# 北京时区
BEIJING_TZ = timezone(timedelta(hours=8))

def get_beijing_time():
    """获取北京时间"""
    return datetime.now(BEIJING_TZ)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI()

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加认证路由
app.include_router(auth_router, prefix="/api/auth", tags=["认证"])

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
    userId: Optional[str] = "default_user"

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

# 更新会话标题请求模型
class UpdateTitleRequest(BaseModel):
    title: str

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
    },
    {
        "id": "qwen",
        "name": "通义千问",
        "apiKey": os.environ.get("QWEN_API_KEY", ""),
        "url": os.environ.get("QWEN_API_BASE", "")
    }
]

for model in default_models:
    models[model["id"]] = model

# 启动时连接 MongoDB
@app.on_event("startup")
async def startup_event():
    try:
        await mongodb_service.connect()
        logger.info("Application started successfully")
    except Exception as e:
        logger.error(f"Failed to start application: {str(e)}")

# 关闭时断开 MongoDB 连接
@app.on_event("shutdown")
async def shutdown_event():
    try:
        await mongodb_service.disconnect()
        logger.info("Application shutdown successfully")
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")


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
async def chat(request: MessageRequest, req: Request):
    try:
        # 从 cookie 中获取用户 ID
        user_id = req.cookies.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="未登录或会话已过期")
            
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
            conversation = await mongodb_service.get_user_conversation_with_messages(
                user_id, request.conversationId
            )
            if not conversation:
                logger.info(f"创建新会话: {request.conversationId} for user {user_id}")
                conversation = {
                    "id": request.conversationId,
                    "title": request.message[:30] + "..." if len(request.message) > 30 else request.message,  # 使用用户的第一条消息作为标题
                    "messages": [],
                    "models": request.modelIds,
                    "createdAt": get_beijing_time().isoformat(),
                    "userId": user_id  # 使用从 cookie 获取的用户 ID
                }
                # 保存到 MongoDB
                await mongodb_service.save_conversation(conversation, user_id)
            logger.info(f"当前会话信息: 消息数量={len(conversation.get('messages', []))}")
          # 添加用户消息
        user_message = {
            "content": request.message,
            "role": "user",
            "timestamp": get_beijing_time().isoformat()
        }
        
        # 保存用户消息到 MongoDB
        if conversation:
            await mongodb_service.save_message(request.conversationId, user_message, user_id)
            conversation["messages"].append(user_message)
            logger.info(f"添加用户消息到会话: {user_message}")
        
        # 单个模型时使用流式响应
        if len(request.modelIds) == 1:
            model_id = request.modelIds[0]
            try:
                # 准备会话历史 - 从 MongoDB 获取最近的消息
                history = []
                if conversation:
                    # 从 MongoDB 获取会话历史，限制最近 6 条消息
                    recent_messages = await mongodb_service.get_conversation_history(
                        request.conversationId, user_id, limit=6
                    )
                    
                    # 排除刚刚添加的用户消息
                    for msg in recent_messages[:-1]:  # 不包含最后一条（刚添加的用户消息）
                        if msg["role"] in ["user", "assistant"]:
                            history.append({
                                "role": msg["role"],
                                "content": msg["content"]
                            })
                    logger.info(f"会话历史 (最近{len(history)}条): 已加载")
                
                logger.info(f"正在流式调用模型 {model_id} 的API")
                
                if model_id == "deepseek-chat":
                    # 创建一个包装的流式生成器，在结束后保存消息
                    async def stream_with_save():
                        collected_content = ""
                        chunk_count = 0
                        async for chunk in get_deepseek_stream_response(request.message, history):
                            chunk_count += 1
                            # 解析SSE格式的数据，提取content
                            lines = chunk.strip().split('\n')
                            for line in lines:
                                if line.startswith('data: '):
                                    data_str = line[6:].strip()
                                    if data_str and data_str != '[DONE]':
                                        try:
                                            import json
                                            data = json.loads(data_str)
                                            if 'choices' in data and len(data['choices']) > 0:
                                                delta = data['choices'][0].get('delta', {})
                                                if 'content' in delta:
                                                    collected_content += delta['content']
                                        except json.JSONDecodeError:
                                            # 如果不是JSON格式，可能是原始文本，直接添加
                                            if not data_str.startswith('data:') and data_str:
                                                collected_content += data_str
                                        except Exception as e:
                                            logger.debug(f"解析流数据块失败: {e}")
                            yield chunk
                        
                        # 流式响应结束后保存AI回复
                        if collected_content.strip() and conversation:
                            ai_message = {
                                "content": collected_content.strip(),
                                "role": "assistant",
                                "model": model_id,
                                "timestamp": get_beijing_time().isoformat()
                            }
                            try:
                                await mongodb_service.save_message(request.conversationId, ai_message, user_id)
                                logger.info(f"流式AI响应已保存到MongoDB: {model_id}, 长度: {len(collected_content)}, 块数: {chunk_count}")
                            except Exception as e:
                                logger.error(f"保存AI响应失败: {e}")
                        else:
                            logger.warning(f"没有收集到有效内容，不保存消息。收集内容: '{collected_content}', 会话: {conversation is not None}")
                    
                    return StreamingResponse(
                        stream_with_save(),
                        media_type="text/event-stream",
                        headers={
                            "Access-Control-Allow-Origin": "http://localhost:3000",
                            "Access-Control-Allow-Credentials": "true"
                        }
                    )
                elif model_id == "sparkx1":
                    # 创建一个包装的流式生成器，在结束后保存消息
                    async def stream_with_save_sparkx1():
                        collected_content = ""
                        chunk_count = 0
                        async for chunk in get_sparkx1_stream_response(request.message, history):
                            chunk_count += 1
                            # 解析SSE格式的数据，提取content
                            lines = chunk.strip().split('\n')
                            for line in lines:
                                if line.startswith('data: '):
                                    data_str = line[6:].strip()
                                    if data_str and data_str != '[DONE]':
                                        try:
                                            import json
                                            data = json.loads(data_str)
                                            if 'choices' in data and len(data['choices']) > 0:
                                                delta = data['choices'][0].get('delta', {})
                                                if 'content' in delta:
                                                    collected_content += delta['content']
                                        except json.JSONDecodeError:
                                            # 如果不是JSON格式，可能是原始文本，直接添加
                                            if not data_str.startswith('data:') and data_str:
                                                collected_content += data_str
                                        except Exception as e:
                                            logger.debug(f"解析流数据块失败: {e}")
                            yield chunk
                        
                        # 流式响应结束后保存AI回复
                        if collected_content.strip() and conversation:
                            ai_message = {
                                "content": collected_content.strip(),
                                "role": "assistant", 
                                "model": model_id,
                                "timestamp": get_beijing_time().isoformat()
                            }
                            try:
                                await mongodb_service.save_message(request.conversationId, ai_message, user_id)
                                logger.info(f"流式AI响应已保存到MongoDB: {model_id}, 长度: {len(collected_content)}, 块数: {chunk_count}")
                            except Exception as e:
                                logger.error(f"保存AI响应失败: {e}")
                        else:
                            logger.warning(f"没有收集到有效内容，不保存消息。收集内容: '{collected_content}', 会话: {conversation is not None}")
                    
                    return StreamingResponse(
                        stream_with_save_sparkx1(),
                        media_type="text/event-stream",
                        headers={
                            "Access-Control-Allow-Origin": "http://localhost:3000",
                            "Access-Control-Allow-Credentials": "true"
                        }
                    )
                elif model_id == "moonshot":
                    api_config = models.get(model_id)
                    if not api_config:
                        raise HTTPException(status_code=400, detail="Moonshot模型未配置")
                    # 创建一个包装的流式生成器，在结束后保存消息
                    async def stream_with_save_moonshot():
                        collected_content = ""
                        chunk_count = 0
                        async for chunk in get_moonshot_stream_response(request.message, history, api_config):
                            chunk_count += 1
                            # 解析SSE格式的数据，提取content
                            lines = chunk.strip().split('\n')
                            for line in lines:
                                if line.startswith('data: '):
                                    data_str = line[6:].strip()
                                    if data_str and data_str != '[DONE]':
                                        try:
                                            import json
                                            data = json.loads(data_str)
                                            if 'choices' in data and len(data['choices']) > 0:
                                                delta = data['choices'][0].get('delta', {})
                                                if 'content' in delta:
                                                    collected_content += delta['content']
                                        except json.JSONDecodeError:
                                            # 如果不是JSON格式，可能是原始文本，直接添加
                                            if not data_str.startswith('data:') and data_str:
                                                collected_content += data_str
                                        except Exception as e:
                                            logger.debug(f"解析流数据块失败: {e}")
                            yield chunk
                        
                        # 流式响应结束后保存AI回复
                        if collected_content.strip() and conversation:
                            ai_message = {
                                "content": collected_content.strip(),
                                "role": "assistant",
                                "model": model_id,
                                "timestamp": get_beijing_time().isoformat()
                            }
                            try:
                                await mongodb_service.save_message(request.conversationId, ai_message, user_id)
                                logger.info(f"流式AI响应已保存到MongoDB: {model_id}, 长度: {len(collected_content)}, 块数: {chunk_count}")
                            except Exception as e:
                                logger.error(f"保存AI响应失败: {e}")
                        else:
                            logger.warning(f"没有收集到有效内容，不保存消息。收集内容: '{collected_content}', 会话: {conversation is not None}")
                    
                    return StreamingResponse(
                        stream_with_save_moonshot(),
                        media_type="text/event-stream",
                        headers={
                            "Access-Control-Allow-Origin": "http://localhost:3000",
                            "Access-Control-Allow-Credentials": "true"
                        }
                    )
                else:
                    # 其他模型暂时保持原样
                    response_content = None
                    if model_id == "moonshot":
                        api_config = models.get(model_id)
                        if not api_config:
                            raise HTTPException(status_code=400, detail="Moonshot模型未配置")
                        response_content = await get_moonshot_response(request.message, history, api_config)
                    else:
                        raise HTTPException(status_code=400, detail=f"不支持的模型ID: {model_id}")
                    
                    response = {
                        "modelId": model_id,
                        "content": response_content                    }
                    
                    if conversation:
                        ai_message = {
                            "content": response_content,
                            "role": "assistant",
                            "model": model_id,
                            "timestamp": get_beijing_time().isoformat()
                        }
                        conversation["messages"].append(ai_message)
                        # 保存AI响应到 MongoDB
                        await mongodb_service.save_message(request.conversationId, ai_message, user_id)
                        logger.info(f"AI响应已保存到MongoDB: {model_id}")
                    
                    return JSONResponse(
                        status_code=200,
                        content={"responses": [response]},
                        headers={
                            "Access-Control-Allow-Origin": "http://localhost:3000",
                            "Access-Control-Allow-Credentials": "true"
                        }
                    )
                    
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
                )        # 多个模型时保持原有逻辑
        responses = []
        for model_id in request.modelIds:
            try:
                # 准备会话历史 - 从 MongoDB 获取最近的消息
                history = []
                if conversation:
                    # 从 MongoDB 获取会话历史，限制最近 6 条消息
                    recent_messages = await mongodb_service.get_conversation_history(
                        request.conversationId, user_id, limit=6
                    )
                    
                    # 排除刚刚添加的用户消息
                    for msg in recent_messages[:-1]:  # 不包含最后一条（刚添加的用户消息）
                        if msg["role"] in ["user", "assistant"]:
                            history.append({
                                "role": msg["role"],
                                "content": msg["content"]
                            })
                    logger.info(f"会话历史 (最近{len(history)}条): 已加载")
                
                logger.info(f"正在调用模型 {model_id} 的API")
                response_content = None
                if model_id == "deepseek-chat":
                    response_content = await get_deepseek_response(request.message, history)
                elif model_id == "sparkx1":
                    response_content = await get_sparkx1_response(request.message, history)
                elif model_id == "moonshot":
                    api_config = models.get(model_id)
                    if not api_config:
                        raise HTTPException(status_code=400, detail="Moonshot模型未配置")
                    response_content = await get_moonshot_response(request.message, history, api_config)
                elif model_id == "qwen":
                    response_content = await get_qwen_response(request.message, history)
                else:
                    raise HTTPException(status_code=400, detail=f"不支持的模型ID: {model_id}")
                
                logger.info(f"收到AI响应: {response_content}")
                
                response = {
                    "modelId": model_id,
                    "content": response_content
                }
                responses.append(response)
                  # 保存AI响应到 MongoDB
                if conversation:
                    ai_message = {
                        "content": response_content,
                        "role": "assistant",
                        "model": model_id,
                        "timestamp": get_beijing_time().isoformat()
                    }
                    await mongodb_service.save_message(request.conversationId, ai_message, user_id)
                    logger.info(f"AI响应已保存到MongoDB: {model_id}")
                    
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
async def fusion_response(request: FusionRequest, req: Request):
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
        
        # 从 cookie 中获取用户 ID
        user_id = req.cookies.get("user_id", "default_user")
        
        # 获取会话历史（如果有）
        history = []
        if request.conversationId:
            # 从 MongoDB 获取会话历史
            recent_messages = await mongodb_service.get_conversation_history(
                request.conversationId, user_id, limit=6
            )
            # 排除刚刚添加的用户消息
            for msg in recent_messages[:-1]:  # 不包含最后一条（刚添加的用户消息）
                if msg["role"] in ["user", "assistant"]:
                    history.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })
            logger.info(f"会话历史 (最近{len(history)}条): 已加载")
        
        # 调用融合服务
        fused_content = await get_fusion_response(request.responses, history)
        
        # 如果存在会话ID，将融合结果保存到 MongoDB
        if request.conversationId:
            fusion_message = {
                "content": fused_content,
                "role": "assistant",
                "model": "fusion",
                "timestamp": get_beijing_time().isoformat()
            }
            # 保存融合回答到 MongoDB
            await mongodb_service.save_message(request.conversationId, fusion_message, user_id)
            logger.info(f"融合回答已保存到MongoDB: {fusion_message}")
        
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
async def advanced_fusion_response(request: AdvancedFusionRequest, req: Request):
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
        
        # 从 cookie 中获取用户 ID
        user_id = req.cookies.get("user_id", "default_user")
        
        # 转换响应格式以匹配服务接口
        formatted_responses = []
        for resp in request.responses:
            formatted_responses.append({
                "modelId": resp.get("modelId", "unknown"),
                "content": resp.get("content", "")
            })
        
        # 调用高级融合服务
        start_time = get_beijing_time()
        result = await get_advanced_fusion_response_direct(
            query=request.query,
            responses=formatted_responses,
            fusion_method=request.fusionMethod,
            top_k=request.topK
        )
        end_time = get_beijing_time()
        
        # 计算处理时间
        processing_time = (end_time - start_time).total_seconds()
        result["processing_time"] = processing_time
        
        # 如果存在会话ID，将融合结果保存到 MongoDB
        if request.conversationId:
            fusion_message = {
                "content": result["fused_content"],
                "role": "assistant",
                "model": "llm_blender",
                "fusion_method": result.get("fusion_method", "unknown"),
                "models_used": result.get("models_used", []),
                "timestamp": end_time.isoformat()
            }
            # 保存高级融合回答到 MongoDB
            await mongodb_service.save_message(request.conversationId, fusion_message, user_id)
            logger.info(f"高级融合回答已保存到MongoDB: {fusion_message}")
        
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

# 获取所有会话列表
@app.get("/api/conversations")
async def get_conversations(request: Request):
    try:
        # 从 cookie 中获取用户 ID
        user_id = request.cookies.get("user_id", "default_user")
        conversations = await mongodb_service.get_all_conversations(user_id)
        return JSONResponse(
            content={"conversations": conversations},
            headers={
                "Access-Control-Allow-Origin": "http://localhost:3000",
                "Access-Control-Allow-Credentials": "true"
            }
        )
    except Exception as e:
        logger.error(f"获取会话列表失败: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"获取会话列表失败: {str(e)}"},
            headers={
                "Access-Control-Allow-Origin": "http://localhost:3000",
                "Access-Control-Allow-Credentials": "true"
            }
        )

# 删除会话
@app.delete("/api/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str, request: Request):
    try:
        # 从 cookie 中获取用户 ID
        user_id = request.cookies.get("user_id", "default_user")
        success = await mongodb_service.delete_user_conversation(user_id, conversation_id)
        if success:
            return JSONResponse(
                content={"message": "会话删除成功"},
                headers={
                    "Access-Control-Allow-Origin": "http://localhost:3000",
                    "Access-Control-Allow-Credentials": "true"
                }
            )
        else:
            return JSONResponse(
                status_code=404,
                content={"detail": "会话不存在或无权访问"},
                headers={
                    "Access-Control-Allow-Origin": "http://localhost:3000",
                    "Access-Control-Allow-Credentials": "true"
                }
            )
    except Exception as e:
        logger.error(f"删除会话失败: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"删除会话失败: {str(e)}"},
            headers={
                "Access-Control-Allow-Origin": "http://localhost:3000",
                "Access-Control-Allow-Credentials": "true"
            }
        )

# 更新会话标题
@app.put("/api/conversations/{conversation_id}/title")
async def update_conversation_title(conversation_id: str, request: UpdateTitleRequest, req: Request):
    try:
        # 从 cookie 中获取用户 ID
        user_id = req.cookies.get("user_id", "default_user")
        success = await mongodb_service.update_conversation_title(
            conversation_id, request.title, user_id
        )
        if success:
            return JSONResponse(
                content={"message": "标题更新成功"},
                headers={
                    "Access-Control-Allow-Origin": "http://localhost:3000",
                    "Access-Control-Allow-Credentials": "true"
                }
            )
        else:
            return JSONResponse(
                status_code=404,
                content={"detail": "会话不存在"},
                headers={
                    "Access-Control-Allow-Origin": "http://localhost:3000",
                    "Access-Control-Allow-Credentials": "true"
                }
            )
    except Exception as e:
        logger.error(f"更新会话标题失败: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"更新会话标题失败: {str(e)}"},
            headers={
                "Access-Control-Allow-Origin": "http://localhost:3000",
                "Access-Control-Allow-Credentials": "true"
            }
        )

# 获取单个会话详情
@app.get("/api/conversations/{conversation_id}")
async def get_conversation_detail(conversation_id: str, request: Request):
    try:
        # 从 cookie 中获取用户 ID
        user_id = request.cookies.get("user_id", "default_user")
        conversation = await mongodb_service.get_conversation(conversation_id, user_id)
        if conversation:
            return JSONResponse(
                content={"conversation": conversation},
                headers={
                    "Access-Control-Allow-Origin": "http://localhost:3000",
                    "Access-Control-Allow-Credentials": "true"
                }
            )
        else:
            return JSONResponse(
                status_code=404,
                content={"detail": "会话不存在或无权访问"},
                headers={
                    "Access-Control-Allow-Origin": "http://localhost:3000",
                    "Access-Control-Allow-Credentials": "true"
                }
            )
    except Exception as e:
        logger.error(f"获取会话详情失败: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"获取会话详情失败: {str(e)}"},
            headers={
                "Access-Control-Allow-Origin": "http://localhost:3000",
                "Access-Control-Allow-Credentials": "true"
            }
        )

# 获取特定用户的会话列表
@app.get("/api/users/{user_id}/conversations")
async def get_user_conversations(user_id: str):
    try:
        conversations = await mongodb_service.get_user_conversations(user_id)
        return JSONResponse(
            content={"conversations": conversations},
            headers={
                "Access-Control-Allow-Origin": "http://localhost:3000",
                "Access-Control-Allow-Credentials": "true"
            }
        )
    except Exception as e:
        logger.error(f"获取用户会话列表失败: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"获取用户会话列表失败: {str(e)}"},
            headers={
                "Access-Control-Allow-Origin": "http://localhost:3000",
                "Access-Control-Allow-Credentials": "true"
            }
        )

# 获取特定用户的会话详情（包含消息）
@app.get("/api/users/{user_id}/conversations/{conversation_id}")
async def get_user_conversation_detail(user_id: str, conversation_id: str):
    try:
        conversation = await mongodb_service.get_user_conversation_with_messages(user_id, conversation_id)
        if conversation:
            return JSONResponse(
                content={"conversation": conversation},
                headers={
                    "Access-Control-Allow-Origin": "http://localhost:3000",
                    "Access-Control-Allow-Credentials": "true"
                }
            )
        else:
            return JSONResponse(
                status_code=404,
                content={"detail": "会话不存在或您没有权限访问"},
                headers={
                    "Access-Control-Allow-Origin": "http://localhost:3000",
                    "Access-Control-Allow-Credentials": "true"
                }
            )
    except Exception as e:
        logger.error(f"获取用户会话详情失败: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"获取用户会话详情失败: {str(e)}"},
            headers={
                "Access-Control-Allow-Origin": "http://localhost:3000",
                "Access-Control-Allow-Credentials": "true"
            }
        )

# 删除特定用户的会话
@app.delete("/api/users/{user_id}/conversations/{conversation_id}")
async def delete_user_conversation(user_id: str, conversation_id: str):
    try:
        success = await mongodb_service.delete_user_conversation(user_id, conversation_id)
        if success:
            return JSONResponse(
                content={"message": "会话删除成功"},
                headers={
                    "Access-Control-Allow-Origin": "http://localhost:3000",
                    "Access-Control-Allow-Credentials": "true"
                }
            )
        else:
            return JSONResponse(
                status_code=404,
                content={"detail": "会话不存在或您没有权限删除"},
                headers={
                    "Access-Control-Allow-Origin": "http://localhost:3000",
                    "Access-Control-Allow-Credentials": "true"
                }
            )
    except Exception as e:
        logger.error(f"删除用户会话失败: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"删除用户会话失败: {str(e)}"},
            headers={
                "Access-Control-Allow-Origin": "http://localhost:3000",
                "Access-Control-Allow-Credentials": "true"
            }
        )

# 获取用户统计信息
@app.get("/api/users/{user_id}/stats")
async def get_user_stats(user_id: str):
    try:
        stats = await mongodb_service.get_user_statistics(user_id)
        return JSONResponse(
            content={"stats": stats},
            headers={
                "Access-Control-Allow-Origin": "http://localhost:3000",
                "Access-Control-Allow-Credentials": "true"
            }
        )
    except Exception as e:
        logger.error(f"获取用户统计信息失败: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"获取用户统计信息失败: {str(e)}"},
            headers={
                "Access-Control-Allow-Origin": "http://localhost:3000",
                "Access-Control-Allow-Credentials": "true"
            }
        )
