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
from services.prompt_service import get_prompt_service

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

# 全局异常处理器
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理器，捕获所有未处理的异常"""
    if isinstance(exc, asyncio.CancelledError):
        logger.warning("请求被客户端取消")
        return JSONResponse(
            status_code=499,  # Client Closed Request
            content={"detail": "请求被客户端取消"},
            headers={
                "Access-Control-Allow-Origin": "http://localhost:3000",
                "Access-Control-Allow-Credentials": "true"
            }
        )
    
    logger.error(f"全局异常处理器捕获异常: {str(exc)}\n{traceback.format_exc()}")
    return JSONResponse(
        status_code=500,
        content={"detail": f"服务器内部错误: {str(exc)}"},
        headers={
            "Access-Control-Allow-Origin": "http://localhost:3000",
            "Access-Control-Allow-Credentials": "true"
        }
    )

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

# 提示词模板相关请求模型
class PromptSuggestionRequest(BaseModel):
    user_input: str
    limit: Optional[int] = 5

class PromptApplicationRequest(BaseModel):
    template_id: str
    user_input: str
    placeholders: Optional[Dict[str, str]] = None

class AutoCompletionRequest(BaseModel):
    partial_input: str

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

# 启动时连接 MongoDB 和设置模型缓存路径
@app.on_event("startup")
async def startup_event():
    try:
        # 使用统一的模型路径配置
        try:
            from config.model_paths import get_model_path_config
            config = get_model_path_config()
            logger.info(f"📁 AI模型缓存基础目录: {config.base_cache_dir}")
            
            # 显示各模型缓存目录
            cache_info = config.get_cache_info()
            for model_type, info in cache_info['directories'].items():
                logger.info(f"📁 {model_type.title()}缓存目录: {info['path']}")
        except ImportError as e:
            logger.warning(f"⚠️ 模型路径配置模块未找到，使用默认设置: {e}")
            # 回退到简单设置
            import os
            transformer_cache_dir = "E:/transformer_models_cache"
            os.makedirs(transformer_cache_dir, exist_ok=True)
            os.environ["HF_HOME"] = transformer_cache_dir
            logger.info(f"📁 使用默认Transformer缓存目录: {transformer_cache_dir}")
        
        await mongodb_service.connect()
        
        # 💾 恢复用户模型配置到环境变量
        try:
            # 恢复默认用户的模型配置
            env_vars = await mongodb_service.restore_models_to_environment("default_user")
            if env_vars:
                logger.info(f"✅ 已恢复 {len(env_vars)} 个模型环境变量")
                for var_name in env_vars.keys():
                    logger.info(f"📝 恢复环境变量: {var_name}")
            else:
                logger.info("📝 未找到需要恢复的模型配置")
        except Exception as e:
            logger.warning(f"⚠️ 恢复模型配置失败: {str(e)}")
        
        logger.info("✅ Application started successfully")
    except Exception as e:
        logger.error(f"❌ Failed to start application: {str(e)}")

# 关闭时断开 MongoDB 连接
@app.on_event("shutdown")
async def shutdown_event():
    try:
        await mongodb_service.disconnect()
        logger.info("Application shutdown successfully")
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")


@app.get("/api/models")
async def get_models(req: Request):
    try:
        # 从 cookie 中获取用户 ID
        user_id = req.cookies.get("user_id")
        if not user_id:
            user_id = "default_user"  # 兼容未登录用户
            
        logger.info(f"获取模型列表 for user: {user_id}")
        
        # 🚀 集成方法一：同时获取BaseModelService注册的模型和MongoDB保存的模型
        model_list = []
        
        # 💾 从MongoDB获取用户保存的模型配置
        try:
            user_models = await mongodb_service.get_all_user_models(user_id)
            for model_config in user_models:
                model_list.append({
                    "id": model_config["id"],
                    "name": model_config["name"],
                    "apiKey": "***hidden***",  # 不显示真实API密钥
                    "url": model_config.get("apiBase", ""),
                    "available": True,
                    "source": "database",
                    "description": model_config.get("description", ""),
                    "type": model_config.get("type", "custom"),
                    "createdAt": model_config.get("createdAt", ""),
                    "updatedAt": model_config.get("updatedAt", "")
                })
            
            logger.info(f"✅ 从MongoDB获取到 {len(user_models)} 个用户模型")
            
        except Exception as e:
            logger.warning(f"⚠️ 从MongoDB获取用户模型失败: {str(e)}")
        
        # 获取传统模型列表
        for model_id, model_info in models.items():
            # 避免重复添加（如果数据库中已有）
            if not any(m["id"] == model_id for m in model_list):
                model_list.append({
                    "id": model_id,
                    "name": model_info.get("name", model_id),
                    "apiKey": model_info.get("apiKey", ""),
                    "url": model_info.get("url", ""),
                    "available": True,
                    "source": "traditional"
                })
        
        # 🔥 获取BaseModelService注册的模型
        try:
            from services.model_registry import model_registry
            
            # 刷新模型可用性
            model_registry.refresh_model_availability()
            
            # 获取注册系统中的模型
            registered_models = model_registry.get_all_models()
            
            for model_config in registered_models:
                # 避免重复添加（如果传统系统和数据库都有）
                if not any(m["id"] == model_config["id"] for m in model_list):
                    model_list.append({
                        "id": model_config["id"],
                        "name": model_config["name"],
                        "apiKey": "***hidden***",  # 不显示真实API密钥
                        "url": "***configured***",  # 不显示真实URL
                        "available": model_config["available"],
                        "source": "base_service",
                        "description": model_config.get("description", "")
                    })
            
            logger.info(f"✅ 获取到 {len(registered_models)} 个BaseService注册模型")
            
        except Exception as e:
            logger.warning(f"⚠️ 获取BaseModelService模型失败: {str(e)}")
        
        logger.info(f"📋 返回模型列表，共 {len(model_list)} 个模型")
        
        return JSONResponse(
            content=model_list,
            headers={
                "Access-Control-Allow-Origin": "http://localhost:3000",
                "Access-Control-Allow-Credentials": "true"
            }
        )
    except Exception as e:
        logger.error(f"获取模型列表失败: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"detail": str(e)},
            headers={
                "Access-Control-Allow-Origin": "http://localhost:3000",
                "Access-Control-Allow-Credentials": "true"
            }
        )

@app.post("/api/models")
async def add_model(model: Model, req: Request):
    try:
        # 从 cookie 中获取用户 ID
        user_id = req.cookies.get("user_id")
        if not user_id:
            user_id = "default_user"  # 兼容未登录用户
            
        logger.info(f"收到添加模型请求: {model.id} for user: {user_id}")
        
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
        
        # 检查模型ID是否已存在（检查MongoDB和内存）
        existing_model = await mongodb_service.get_user_model(model.id, user_id)
        if existing_model or model.id in models:
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
        
        # 准备模型配置数据
        model_config = {
            "id": model.id,
            "name": model.name,
            "apiKey": model.apiKey,
            "apiBase": model.url,
            "type": "custom",
            "description": f"用户添加的自定义模型: {model.name}",
            "maxTokens": 4000,
            "temperature": 0.7,
            "streamSupport": True,
            "isActive": True
        }
        
        # 💾 保存到MongoDB数据库
        db_success = await mongodb_service.save_user_model(model_config, user_id)
        if not db_success:
            error_msg = "保存模型配置到数据库失败"
            logger.error(error_msg)
            return JSONResponse(
                status_code=500,
                content={"detail": error_msg},
                headers={
                    "Access-Control-Allow-Origin": "http://localhost:3000",
                    "Access-Control-Allow-Credentials": "true"
                }
            )
        
        logger.info(f"✅ 模型配置已保存到MongoDB: {model.id} for user: {user_id}")
        
        # 🚀 集成方法一：使用BaseModelService架构
        try:
            from services.model_registry import add_custom_model
            
            # 设置环境变量（用于API调用）
            import os
            api_key_env = f"{model.id.upper()}_API_KEY"
            api_base_env = f"{model.id.upper()}_API_BASE"
            
            os.environ[api_key_env] = model.apiKey
            os.environ[api_base_env] = model.url
            
            # 使用方法一添加到模型注册系统
            add_custom_model(
                model_id=model.id,
                api_key_env=api_key_env,
                api_base_env=api_base_env,
                display_name=model.name,
                model_name=model.name.lower().replace(' ', '-'),
                description=f"用户添加的自定义模型: {model.name}"
            )
            
            logger.info(f"✅ 成功将模型 {model.id} 注册到BaseModelService系统")
            
        except Exception as e:
            logger.warning(f"⚠️ 注册到BaseModelService失败，继续使用传统方式: {str(e)}")
        
        # 添加到传统模型字典（保持兼容性）
        model_dict = model.dict(exclude_unset=True)
        models[model.id] = model_dict
        logger.info(f"成功添加模型: {model.id}")
        
        return JSONResponse(
            content={
                **model_dict,
                "registered_to_base_service": True,
                "saved_to_database": db_success,
                "message": "模型已成功添加、保存到数据库并注册到服务系统"
            },
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
        
        # 验证所有模型ID（检查内存和MongoDB）
        for model_id in request.modelIds:
            if model_id not in models:
                # 如果内存中没有，尝试从MongoDB获取用户模型配置
                user_model = await mongodb_service.get_user_model(model_id, user_id)
                if user_model:
                    # 将用户模型配置加载到内存中
                    models[model_id] = {
                        "id": user_model["id"],
                        "name": user_model["name"],
                        "apiKey": user_model["apiKey"],
                        "url": user_model["apiBase"],
                        "source": "database"
                    }
                    logger.info(f"✅ 从MongoDB动态加载模型配置: {model_id}")
                else:
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
        
        # 通用的流式响应包装函数
        async def create_stream_wrapper(stream_generator, model_id):
            """创建带异常处理的流式响应包装器"""
            collected_content = ""
            chunk_count = 0
            try:
                async for chunk in stream_generator:
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
                    
            except asyncio.CancelledError:
                logger.warning(f"{model_id}模型流式响应被客户端取消")
                # 连接被取消，重新抛出异常让上层处理
                raise
            except Exception as e:
                logger.error(f"{model_id}流式响应错误: {str(e)}")
                try:
                    error_data = {
                        "error": str(e),
                        "model": model_id
                    }
                    yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
                    yield f"data: [DONE]\n\n"
                except Exception:
                    # 如果连错误信息都无法发送，则静默忽略
                    pass
            finally:
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
                    return StreamingResponse(
                        create_stream_wrapper(get_deepseek_stream_response(request.message, history), model_id),
                        media_type="text/event-stream",
                        headers={
                            "Access-Control-Allow-Origin": "http://localhost:3000",
                            "Access-Control-Allow-Credentials": "true"
                        }
                    )
                elif model_id == "sparkx1":
                    return StreamingResponse(
                        create_stream_wrapper(get_sparkx1_stream_response(request.message, history), model_id),
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
                    return StreamingResponse(
                        create_stream_wrapper(get_moonshot_stream_response(request.message, history, api_config), model_id),
                        media_type="text/event-stream",
                        headers={
                            "Access-Control-Allow-Origin": "http://localhost:3000",
                            "Access-Control-Allow-Credentials": "true"
                        }
                    )
                elif model_id == "qwen":
                    return StreamingResponse(
                        create_stream_wrapper(get_qwen_stream_response(request.message, history), model_id),
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
                    elif model_id == "qwen":
                        response_content = await get_qwen_response(request.message, history)
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
                )
        
        # 多个模型时使用并发流式响应
        else:
            # 准备会话历史 - 从 MongoDB 获取最近的消息
            history = []
            if conversation:
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
            
            # 创建多模型并发流式响应生成器
            async def multi_model_stream():
                import asyncio
                import json
                
                # 为每个模型创建流式处理函数
                async def process_single_model_stream(model_id, queue):
                    try:
                        logger.info(f"🚀 开始流式调用模型: {model_id}")
                        
                        # 发送模型开始信号
                        await queue.put({
                            "type": "model_start",
                            "modelId": model_id,
                            "message": f"模型 {model_id} 开始思考..."
                        })
                        
                        collected_content = ""
                        
                        # 根据模型类型调用对应的流式API
                        if model_id == "deepseek-chat":
                            async for chunk in get_deepseek_stream_response(request.message, history):
                                # 解析流式数据
                                lines = chunk.strip().split('\n')
                                for line in lines:
                                    if line.startswith('data: '):
                                        data_str = line[6:].strip()
                                        if data_str and data_str != '[DONE]':
                                            try:
                                                data = json.loads(data_str)
                                                if 'choices' in data and len(data['choices']) > 0:
                                                    delta = data['choices'][0].get('delta', {})
                                                    if 'content' in delta:
                                                        content_chunk = delta['content']
                                                        collected_content += content_chunk
                                                        
                                                        # 实时发送字符块
                                                        await queue.put({
                                                            "type": "model_chunk",
                                                            "modelId": model_id,
                                                            "chunk": content_chunk,
                                                            "accumulated": collected_content
                                                        })
                                            except json.JSONDecodeError:
                                                pass
                        
                        elif model_id == "sparkx1":
                            async for chunk in get_sparkx1_stream_response(request.message, history):
                                lines = chunk.strip().split('\n')
                                for line in lines:
                                    if line.startswith('data: '):
                                        data_str = line[6:].strip()
                                        if data_str and data_str != '[DONE]':
                                            try:
                                                data = json.loads(data_str)
                                                if 'choices' in data and len(data['choices']) > 0:
                                                    delta = data['choices'][0].get('delta', {})
                                                    if 'content' in delta:
                                                        content_chunk = delta['content']
                                                        collected_content += content_chunk
                                                        
                                                        await queue.put({
                                                            "type": "model_chunk",
                                                            "modelId": model_id,
                                                            "chunk": content_chunk,
                                                            "accumulated": collected_content
                                                        })
                                            except json.JSONDecodeError:
                                                pass
                        
                        elif model_id == "moonshot":
                            api_config = models.get(model_id)
                            if not api_config:
                                raise HTTPException(status_code=400, detail="Moonshot模型未配置")
                            async for chunk in get_moonshot_stream_response(request.message, history, api_config):
                                lines = chunk.strip().split('\n')
                                for line in lines:
                                    if line.startswith('data: '):
                                        data_str = line[6:].strip()
                                        if data_str and data_str != '[DONE]':
                                            try:
                                                data = json.loads(data_str)
                                                if 'choices' in data and len(data['choices']) > 0:
                                                    delta = data['choices'][0].get('delta', {})
                                                    if 'content' in delta:
                                                        content_chunk = delta['content']
                                                        collected_content += content_chunk
                                                        
                                                        await queue.put({
                                                            "type": "model_chunk",
                                                            "modelId": model_id,
                                                            "chunk": content_chunk,
                                                            "accumulated": collected_content
                                                        })
                                            except json.JSONDecodeError:
                                                pass
                        
                        elif model_id == "qwen":
                            async for chunk in get_qwen_stream_response(request.message, history):
                                lines = chunk.strip().split('\n')
                                for line in lines:
                                    if line.startswith('data: '):
                                        data_str = line[6:].strip()
                                        if data_str and data_str != '[DONE]':
                                            try:
                                                data = json.loads(data_str)
                                                if 'choices' in data and len(data['choices']) > 0:
                                                    delta = data['choices'][0].get('delta', {})
                                                    if 'content' in delta:
                                                        content_chunk = delta['content']
                                                        collected_content += content_chunk
                                                        
                                                        await queue.put({
                                                            "type": "model_chunk",
                                                            "modelId": model_id,
                                                            "chunk": content_chunk,
                                                            "accumulated": collected_content
                                                        })
                                            except json.JSONDecodeError:
                                                pass
                        else:
                            raise HTTPException(status_code=400, detail=f"不支持的模型ID: {model_id}")
                        
                        logger.info(f"✅ 模型 {model_id} 流式响应完成，总长度: {len(collected_content)}")
                        
                        # 保存AI响应到 MongoDB
                        if conversation and collected_content.strip():
                            ai_message = {
                                "content": collected_content.strip(),
                                "role": "assistant",
                                "model": model_id,
                                "timestamp": get_beijing_time().isoformat()
                            }
                            await mongodb_service.save_message(request.conversationId, ai_message, user_id)
                            logger.info(f"AI响应已保存到MongoDB: {model_id}")
                        
                        # 发送模型完成信号
                        await queue.put({
                            "type": "model_complete",
                            "modelId": model_id,
                            "content": collected_content,
                            "status": "success"
                        })
                        
                    except asyncio.CancelledError:
                        logger.warning(f"❌ 模型 {model_id} 流式处理被客户端取消")
                        try:
                            await queue.put({
                                "type": "model_complete",
                                "modelId": model_id,
                                "content": "请求被取消",
                                "status": "cancelled"
                            })
                        except Exception:
                            pass  # 队列可能已经关闭
                        raise  # 重新抛出CancelledError
                    except Exception as e:
                        logger.error(f"❌ 模型 {model_id} 流式处理失败: {str(e)}")
                        try:
                            await queue.put({
                                "type": "model_complete",
                                "modelId": model_id,
                                "content": f"错误: {str(e)}",
                                "status": "error"
                            })
                        except Exception:
                            pass  # 队列可能已经关闭
                
                # 创建队列用于收集所有模型的流式数据
                queue = asyncio.Queue()
                
                # 创建所有模型的并发任务
                tasks = [
                    asyncio.create_task(process_single_model_stream(model_id, queue))
                    for model_id in request.modelIds
                ]
                
                # 发送开始信号
                start_data = {
                    "type": "start",
                    "models": request.modelIds,
                    "total": len(request.modelIds)
                }
                yield f"data: {json.dumps(start_data)}\n\n"
                
                # 实时处理队列中的数据
                completed_models = 0
                total_models = len(request.modelIds)
                
                try:
                    while completed_models < total_models:
                        try:
                            # 等待队列中的数据，设置超时避免死锁
                            stream_data = await asyncio.wait_for(queue.get(), timeout=30.0)
                            
                            # 立即发送流式数据
                            yield f"data: {json.dumps(stream_data, ensure_ascii=False)}\n\n"
                            
                            # 检查是否有模型完成
                            if stream_data.get("type") == "model_complete":
                                completed_models += 1
                                logger.info(f"模型完成: {stream_data.get('modelId')}, 进度: {completed_models}/{total_models}")
                                
                        except asyncio.TimeoutError:
                            logger.warning(f"等待模型响应超时，已完成: {completed_models}/{total_models}")
                            # 发送超时信息
                            timeout_data = {
                                "type": "timeout_warning",
                                "message": f"部分模型响应超时，已完成 {completed_models}/{total_models} 个模型"
                            }
                            yield f"data: {json.dumps(timeout_data, ensure_ascii=False)}\n\n"
                            break
                        except asyncio.CancelledError:
                            logger.warning("流式响应被客户端取消")
                            break
                        except Exception as e:
                            logger.error(f"处理流式数据时发生错误: {str(e)}")
                            # 发送错误信息但继续处理
                            error_data = {
                                "type": "error",
                                "message": f"处理数据时发生错误: {str(e)}"
                            }
                            yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
                            break
                except asyncio.CancelledError:
                    logger.warning("多模型流式响应被客户端取消")
                    # 清理资源
                    for task in tasks:
                        if not task.done():
                            try:
                                task.cancel()
                            except Exception:
                                pass
                    raise  # 重新抛出CancelledError
                except Exception as e:
                    logger.error(f"多模型流式响应发生严重错误: {str(e)}")
                    try:
                        error_data = {
                            "type": "fatal_error",
                            "message": f"系统错误: {str(e)}"
                        }
                        yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
                    except Exception:
                        pass  # 如果连错误信息都无法发送，则静默忽略
                finally:
                    # 确保清理所有任务
                    for task in tasks:
                        if not task.done():
                            try:
                                task.cancel()
                            except Exception:
                                pass
                
                # 等待所有任务完成
                try:
                    await asyncio.wait_for(asyncio.gather(*tasks, return_exceptions=True), timeout=5.0)
                except (asyncio.TimeoutError, asyncio.CancelledError):
                    logger.warning("等待所有模型任务完成超时或被取消")
                except Exception as e:
                    logger.error(f"等待任务完成时发生错误: {str(e)}")
                
                # 发送完成信号
                end_data = {
                    "type": "all_complete",
                    "message": f"所有 {total_models} 个模型已完成响应"
                }
                yield f"data: {json.dumps(end_data)}\n\n"
                yield f"data: [DONE]\n\n"
            
            return StreamingResponse(
                multi_model_stream(),
                media_type="text/event-stream",
                headers={
                    "Access-Control-Allow-Origin": "http://localhost:3000",
                    "Access-Control-Allow-Credentials": "true",
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive"
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
async def delete_model(model_id: str, req: Request):
    try:
        # 从 cookie 中获取用户 ID
        user_id = req.cookies.get("user_id")
        if not user_id:
            user_id = "default_user"  # 兼容未登录用户
            
        logger.info(f"收到删除模型请求: {model_id} for user: {user_id}")
        
        # 💾 从MongoDB删除模型配置
        db_success = await mongodb_service.delete_user_model(model_id, user_id)
        
        # 检查传统模型字典
        found_in_memory = model_id in models
        
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
        
        if not db_success and not found_in_memory:
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
        
        # 从选中的模型列表中移除
        global selected_models
        if model_id in selected_models:
            selected_models.remove(model_id)
        
        # 从传统模型字典删除
        deleted_model = None
        if found_in_memory:
            deleted_model = models.pop(model_id)
        
        # 从环境变量中删除相关配置
        import os
        api_key_env = f"{model_id.upper()}_API_KEY"
        api_base_env = f"{model_id.upper()}_API_BASE"
        
        if api_key_env in os.environ:
            del os.environ[api_key_env]
        if api_base_env in os.environ:
            del os.environ[api_base_env]
        
        logger.info(f"✅ 模型已删除: {model_id} (数据库: {db_success}, 内存: {found_in_memory})")
        
        return JSONResponse(
            content={
                "message": f"模型 {model_id} 已成功删除",
                "model": deleted_model,
                "deleted_from_database": db_success,
                "deleted_from_memory": found_in_memory
            },
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

# ==================== 模型管理API端点 ====================

@app.get("/api/models/statistics")
async def get_model_statistics(req: Request):
    """获取用户模型统计信息"""
    try:
        # 从 cookie 中获取用户 ID
        user_id = req.cookies.get("user_id")
        if not user_id:
            user_id = "default_user"  # 兼容未登录用户
            
        stats = await mongodb_service.get_model_statistics(user_id)
        
        return JSONResponse(
            content=stats,
            headers={
                "Access-Control-Allow-Origin": "http://localhost:3000",
                "Access-Control-Allow-Credentials": "true"
            }
        )
    except Exception as e:
        logger.error(f"获取模型统计信息失败: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"detail": str(e)},
            headers={
                "Access-Control-Allow-Origin": "http://localhost:3000",
                "Access-Control-Allow-Credentials": "true"
            }
        )

@app.get("/api/models/export")
async def export_user_models(req: Request):
    """导出用户的所有模型配置"""
    try:
        # 从 cookie 中获取用户 ID
        user_id = req.cookies.get("user_id")
        if not user_id:
            user_id = "default_user"  # 兼容未登录用户
            
        export_data = await mongodb_service.export_user_models(user_id)
        
        return JSONResponse(
            content=export_data,
            headers={
                "Access-Control-Allow-Origin": "http://localhost:3000",
                "Access-Control-Allow-Credentials": "true"
            }
        )
    except Exception as e:
        logger.error(f"导出模型配置失败: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"detail": str(e)},
            headers={
                "Access-Control-Allow-Origin": "http://localhost:3000",
                "Access-Control-Allow-Credentials": "true"
            }
        )

@app.post("/api/models/import")
async def import_user_models(import_data: dict, req: Request):
    """导入用户模型配置"""
    try:
        # 从 cookie 中获取用户 ID
        user_id = req.cookies.get("user_id")
        if not user_id:
            user_id = "default_user"  # 兼容未登录用户
            
        result = await mongodb_service.import_user_models(import_data, user_id)
        
        # 恢复环境变量
        if result.get("success", False):
            await mongodb_service.restore_models_to_environment(user_id)
        
        return JSONResponse(
            content=result,
            headers={
                "Access-Control-Allow-Origin": "http://localhost:3000",
                "Access-Control-Allow-Credentials": "true"
            }
        )
    except Exception as e:
        logger.error(f"导入模型配置失败: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"detail": str(e)},
            headers={
                "Access-Control-Allow-Origin": "http://localhost:3000",
                "Access-Control-Allow-Credentials": "true"
            }
        )

@app.put("/api/models/{model_id}")
async def update_user_model(model_id: str, updates: dict, req: Request):
    """更新用户模型配置"""
    try:
        # 从 cookie 中获取用户 ID
        user_id = req.cookies.get("user_id")
        if not user_id:
            user_id = "default_user"  # 兼容未登录用户
            
        success = await mongodb_service.update_user_model(model_id, updates, user_id)
        
        if success:
            # 更新环境变量
            if "apiKey" in updates:
                import os
                api_key_env = f"{model_id.upper()}_API_KEY"
                os.environ[api_key_env] = updates["apiKey"]
            
            if "apiBase" in updates:
                import os
                api_base_env = f"{model_id.upper()}_API_BASE"
                os.environ[api_base_env] = updates["apiBase"]
            
            return JSONResponse(
                content={"message": f"模型 {model_id} 更新成功"},
                headers={
                    "Access-Control-Allow-Origin": "http://localhost:3000",
                    "Access-Control-Allow-Credentials": "true"
                }
            )
        else:
            return JSONResponse(
                status_code=404,
                content={"detail": f"模型 {model_id} 不存在"},
                headers={
                    "Access-Control-Allow-Origin": "http://localhost:3000",
                    "Access-Control-Allow-Credentials": "true"
                }
            )
    except Exception as e:
        logger.error(f"更新模型配置失败: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"detail": str(e)},
            headers={
                "Access-Control-Allow-Origin": "http://localhost:3000",
                "Access-Control-Allow-Credentials": "true"
            }
        )

@app.get("/api/models/{model_id}")
async def get_user_model(model_id: str, req: Request):
    """获取指定的用户模型配置"""
    try:
        # 从 cookie 中获取用户 ID
        user_id = req.cookies.get("user_id")
        if not user_id:
            user_id = "default_user"  # 兼容未登录用户
            
        model_config = await mongodb_service.get_user_model(model_id, user_id)
        
        if model_config:
            return JSONResponse(
                content=model_config,
                headers={
                    "Access-Control-Allow-Origin": "http://localhost:3000",
                    "Access-Control-Allow-Credentials": "true"
                }
            )
        else:
            return JSONResponse(
                status_code=404,
                content={"detail": f"模型 {model_id} 不存在"},
                headers={
                    "Access-Control-Allow-Origin": "http://localhost:3000",
                    "Access-Control-Allow-Credentials": "true"
                }
            )
    except Exception as e:
        logger.error(f"获取模型配置失败: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"detail": str(e)},
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

# 分享会话
@app.post("/api/conversations/{conversation_id}/share")
async def share_conversation(conversation_id: str, request: Request):
    try:
        # 从 cookie 中获取用户 ID
        user_id = request.cookies.get("user_id", "default_user")
        
        # 验证会话是否存在且属于该用户
        conversation = await mongodb_service.get_conversation(conversation_id, user_id)
        if not conversation:
            return JSONResponse(
                status_code=404,
                content={"detail": "会话不存在或无权访问"},
                headers={
                    "Access-Control-Allow-Origin": "http://localhost:3000",
                    "Access-Control-Allow-Credentials": "true"
                }
            )
        
        # 创建分享
        share_result = await mongodb_service.create_share(conversation_id, user_id)
        if not share_result:
            return JSONResponse(
                status_code=500,
                content={"detail": "创建分享失败"},
                headers={
                    "Access-Control-Allow-Origin": "http://localhost:3000",
                    "Access-Control-Allow-Credentials": "true"
                }
            )
        
        return JSONResponse(
            content=share_result,
            headers={
                "Access-Control-Allow-Origin": "http://localhost:3000",
                "Access-Control-Allow-Credentials": "true"
            }
        )
        
    except Exception as e:
        logger.error(f"分享会话失败: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"分享会话失败: {str(e)}"},
            headers={
                "Access-Control-Allow-Origin": "http://localhost:3000",
                "Access-Control-Allow-Credentials": "true"
            }
        )

# 获取分享的会话
@app.get("/api/shared/{share_id}")
async def get_shared_conversation(share_id: str):
    try:
        shared_data = await mongodb_service.get_shared_conversation(share_id)
        if not shared_data:
            return JSONResponse(
                status_code=404,
                content={"detail": "分享的会话不存在或已失效"},
                headers={
                    "Access-Control-Allow-Origin": "http://localhost:3000",
                    "Access-Control-Allow-Credentials": "true"
                }
            )
        
        return JSONResponse(
            content=shared_data,
            headers={
                "Access-Control-Allow-Origin": "http://localhost:3000",
                "Access-Control-Allow-Credentials": "true"
            }
        )
        
    except Exception as e:
        logger.error(f"获取分享的会话失败: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"获取分享的会话失败: {str(e)}"},
            headers={
                "Access-Control-Allow-Origin": "http://localhost:3000",
                "Access-Control-Allow-Credentials": "true"
            }
        )

# 获取用户分享的所有会话
@app.get("/api/shared")
async def get_user_shares(request: Request):
    try:
        # 从 cookie 中获取用户 ID
        user_id = request.cookies.get("user_id", "default_user")
        
        shares = await mongodb_service.get_user_shares(user_id)
        return JSONResponse(
            content={"sharedConversations": shares},
            headers={
                "Access-Control-Allow-Origin": "http://localhost:3000",
                "Access-Control-Allow-Credentials": "true"
            }
        )
        
    except Exception as e:
        logger.error(f"获取用户分享列表失败: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"获取用户分享列表失败: {str(e)}"},
            headers={
                "Access-Control-Allow-Origin": "http://localhost:3000",
                "Access-Control-Allow-Credentials": "true"
            }
        )

# 删除分享
@app.delete("/api/shared/{share_id}")
async def delete_share(share_id: str, request: Request):
    try:
        # 从 cookie 中获取用户 ID
        user_id = request.cookies.get("user_id", "default_user")
        
        # 删除分享
        result = await mongodb_service.deactivate_share(share_id, user_id)
        if not result:
            return JSONResponse(
                status_code=404,
                content={"detail": "分享不存在或无权删除"},
                headers={
                    "Access-Control-Allow-Origin": "http://localhost:3000",
                    "Access-Control-Allow-Credentials": "true"
                }
            )
        
        return JSONResponse(
            content={"detail": "分享已删除"},
            headers={
                "Access-Control-Allow-Origin": "http://localhost:3000",
                "Access-Control-Allow-Credentials": "true"
            }
        )
        
    except Exception as e:
        logger.error(f"删除分享失败: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"删除分享失败: {str(e)}"},
            headers={
                "Access-Control-Allow-Origin": "http://localhost:3000",
                "Access-Control-Allow-Credentials": "true"
            }
        )

# 获取当前用户信息
@app.get("/api/users/me")
async def get_current_user(request: Request):
    try:
        # 从 cookie 中获取用户 ID
        user_id = request.cookies.get("user_id")
        if not user_id:
            return JSONResponse(
                status_code=401,
                content={"detail": "未登录"},
                headers={
                    "Access-Control-Allow-Origin": "http://localhost:3000",
                    "Access-Control-Allow-Credentials": "true"
                }
            )
        
        # 从数据库获取用户信息
        user = await mongodb_service.get_user_by_id(user_id)
        if not user:
            return JSONResponse(
                status_code=404,
                content={"detail": "用户不存在"},
                headers={
                    "Access-Control-Allow-Origin": "http://localhost:3000",
                    "Access-Control-Allow-Credentials": "true"
                }
            )
        
        return JSONResponse(
            content={
                "id": str(user["_id"]),
                "username": user.get("username", ""),
                "email": user.get("email", "")
            },
            headers={
                "Access-Control-Allow-Origin": "http://localhost:3000",
                "Access-Control-Allow-Credentials": "true"
            }
        )
    except Exception as e:
        logger.error(f"获取用户信息失败: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"获取用户信息失败: {str(e)}"},
            headers={
                "Access-Control-Allow-Origin": "http://localhost:3000",
                "Access-Control-Allow-Credentials": "true"
            }
        )

# ================================
# 提示词服务相关API
# ================================

# 获取所有提示词分类
@app.get("/api/prompts/categories")
async def get_prompt_categories():
    """获取所有提示词分类"""
    try:
        prompt_service = get_prompt_service()
        categories = prompt_service.get_categories()
        
        return JSONResponse(
            content={"categories": categories},
            headers={
                "Access-Control-Allow-Origin": "http://localhost:3000",
                "Access-Control-Allow-Credentials": "true"
            }
        )
    except Exception as e:
        logger.error(f"获取提示词分类失败: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"获取提示词分类失败: {str(e)}"},
            headers={
                "Access-Control-Allow-Origin": "http://localhost:3000",
                "Access-Control-Allow-Credentials": "true"
            }
        )

# 根据分类获取提示词模板
@app.get("/api/prompts/templates/{category}")
async def get_prompt_templates_by_category(category: str):
    """根据分类获取提示词模板"""
    try:
        prompt_service = get_prompt_service()
        templates = prompt_service.get_templates_by_category(category)
        
        return JSONResponse(
            content={"templates": templates, "category": category},
            headers={
                "Access-Control-Allow-Origin": "http://localhost:3000",
                "Access-Control-Allow-Credentials": "true"
            }
        )
    except Exception as e:
        logger.error(f"获取提示词模板失败: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"获取提示词模板失败: {str(e)}"},
            headers={
                "Access-Control-Allow-Origin": "http://localhost:3000",
                "Access-Control-Allow-Credentials": "true"
            }
        )

# 获取所有提示词模板
@app.get("/api/prompts/templates")
async def get_all_prompt_templates():
    """获取所有提示词模板"""
    try:
        prompt_service = get_prompt_service()
        all_templates = []
        
        for category in prompt_service.get_categories():
            templates = prompt_service.get_templates_by_category(category)
            for template in templates:
                template["category"] = category
                all_templates.append(template)
        
        return JSONResponse(
            content={"templates": all_templates},
            headers={
                "Access-Control-Allow-Origin": "http://localhost:3000",
                "Access-Control-Allow-Credentials": "true"
            }
        )
    except Exception as e:
        logger.error(f"获取所有提示词模板失败: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"获取所有提示词模板失败: {str(e)}"},
            headers={
                "Access-Control-Allow-Origin": "http://localhost:3000",
                "Access-Control-Allow-Credentials": "true"
            }
        )

# 智能建议提示词
@app.post("/api/prompts/suggest")
async def suggest_prompts(request: PromptSuggestionRequest):
    """基于用户输入智能建议相关的提示词模板"""
    try:
        prompt_service = get_prompt_service()
        suggestions = prompt_service.suggest_prompts(
            request.user_input, 
            limit=request.limit
        )
        
        return JSONResponse(
            content={
                "suggestions": suggestions,
                "input": request.user_input,
                "count": len(suggestions)
            },
            headers={
                "Access-Control-Allow-Origin": "http://localhost:3000",
                "Access-Control-Allow-Credentials": "true"
            }
        )
    except Exception as e:
        logger.error(f"智能建议提示词失败: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"智能建议提示词失败: {str(e)}"},
            headers={
                "Access-Control-Allow-Origin": "http://localhost:3000",
                "Access-Control-Allow-Credentials": "true"
            }
        )

# 应用提示词模板
@app.post("/api/prompts/apply")
async def apply_prompt_template(request: PromptApplicationRequest):
    """应用提示词模板生成完整的提示"""
    try:
        prompt_service = get_prompt_service()
        applied_prompt = prompt_service.apply_template(
            request.template_id,
            request.user_input,
            request.placeholders
        )
        
        # 获取模板信息用于返回
        template = prompt_service.get_template_by_id(request.template_id)
        
        return JSONResponse(
            content={
                "applied_prompt": applied_prompt,
                "template": template,
                "original_input": request.user_input,
                "placeholders": request.placeholders
            },
            headers={
                "Access-Control-Allow-Origin": "http://localhost:3000",
                "Access-Control-Allow-Credentials": "true"
            }
        )
    except Exception as e:
        logger.error(f"应用提示词模板失败: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"应用提示词模板失败: {str(e)}"},
            headers={
                "Access-Control-Allow-Origin": "http://localhost:3000",
                "Access-Control-Allow-Credentials": "true"
            }
        )

# 自动补全建议
@app.post("/api/prompts/autocomplete")
async def get_auto_completions(request: AutoCompletionRequest):
    """获取自动补全建议"""
    try:
        prompt_service = get_prompt_service()
        completions = prompt_service.get_auto_completions(request.partial_input)
        
        return JSONResponse(
            content={
                "completions": completions,
                "partial_input": request.partial_input,
                "count": len(completions)
            },
            headers={
                "Access-Control-Allow-Origin": "http://localhost:3000",
                "Access-Control-Allow-Credentials": "true"
            }
        )
    except Exception as e:
        logger.error(f"获取自动补全建议失败: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"获取自动补全建议失败: {str(e)}"},
            headers={
                "Access-Control-Allow-Origin": "http://localhost:3000",
                "Access-Control-Allow-Credentials": "true"
            }
        )

# Transformer智能补全建议（基于预训练模型）
@app.post("/api/prompts/transformer-autocomplete")
async def get_transformer_completions(request: AutoCompletionRequest):
    """获取基于Transformer的智能补全建议"""
    try:
        if request.partial_input:
            # 获取来自高级Transformer混合服务的补全建议
            from services.intelligent_completion_service import get_advanced_intelligent_completions
            completions = get_advanced_intelligent_completions(request.partial_input, max_completions=5)
            
            return JSONResponse(
                content={
                    "completions": completions,
                    "partial_input": request.partial_input,
                    "count": len(completions),
                    "type": "transformer",
                    "status": "success"
                },
                headers={
                    "Access-Control-Allow-Origin": "http://localhost:3000",
                    "Access-Control-Allow-Credentials": "true"
                }
            )
        else:
            return JSONResponse(
                content={
                    "completions": [],
                    "partial_input": "",
                    "count": 0,
                    "type": "transformer",
                    "status": "empty_input"
                },
                headers={
                    "Access-Control-Allow-Origin": "http://localhost:3000",
                    "Access-Control-Allow-Credentials": "true"
                }
            )
    except Exception as e:
        logger.error(f"获取Transformer补全时出错: {e}")
        # 降级到智能补全
        try:
            from services.prompt_service import get_prompt_service
            prompt_service = get_prompt_service()
            completions = prompt_service.get_intelligent_completions(request.partial_input)
            return JSONResponse(
                content={
                    "completions": completions,
                    "partial_input": request.partial_input,
                    "count": len(completions),
                    "type": "transformer_fallback",
                    "status": "fallback_to_intelligent",
                    "fallback_reason": str(e)
                },
                headers={
                    "Access-Control-Allow-Origin": "http://localhost:3000",
                    "Access-Control-Allow-Credentials": "true"
                }
            )
        except Exception as e2:
            logger.error(f"降级到智能补全也失败: {e2}")
            return JSONResponse(
                status_code=500,
                content={
                    "detail": f"获取Transformer补全失败: {str(e)}",
                    "fallback_error": str(e2),
                    "type": "transformer",
                    "status": "error"
                },
                headers={
                    "Access-Control-Allow-Origin": "http://localhost:3000",
                    "Access-Control-Allow-Credentials": "true"
                }
            )

# 智能补全建议（基于N-gram语言模型）
@app.post("/api/prompts/intelligent-autocomplete")
async def get_intelligent_completions(request: AutoCompletionRequest):
    """获取智能补全建议（基于N-gram语言模型的词汇预测）"""
    try:
        prompt_service = get_prompt_service()
        completions = prompt_service.get_intelligent_completions(request.partial_input)
        
        return JSONResponse(
            content={
                "completions": completions,
                "partial_input": request.partial_input,
                "count": len(completions),
                "type": "intelligent"
            },
            headers={
                "Access-Control-Allow-Origin": "http://localhost:3000",
                "Access-Control-Allow-Credentials": "true"
            }
        )
    except Exception as e:
        logger.error(f"获取智能补全建议失败: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"获取智能补全建议失败: {str(e)}"},
            headers={
                "Access-Control-Allow-Origin": "http://localhost:3000",
                "Access-Control-Allow-Credentials": "true"
            }
        )

# 词汇预测（基于高级混合模型）
@app.post("/api/prompts/word-predictions")
async def get_word_predictions(request: AutoCompletionRequest):
    """获取下一个词的概率预测（基于高级Transformer+N-gram混合模型）"""
    try:
        if request.partial_input:
            # 优先使用高级Transformer混合服务的词汇预测
            from services.intelligent_completion_service import get_advanced_word_predictions
            predictions = get_advanced_word_predictions(request.partial_input, top_k=8)
            
            return JSONResponse(
                content={
                    "predictions": predictions,
                    "partial_input": request.partial_input,
                    "count": len(predictions),
                    "type": "advanced_hybrid",
                    "status": "success"
                },
                headers={
                    "Access-Control-Allow-Origin": "http://localhost:3000",
                    "Access-Control-Allow-Credentials": "true"
                }
            )
        else:
            return JSONResponse(
                content={
                    "predictions": [],
                    "partial_input": "",
                    "count": 0,
                    "type": "advanced_hybrid",
                    "status": "empty_input"
                },
                headers={
                    "Access-Control-Allow-Origin": "http://localhost:3000",
                    "Access-Control-Allow-Credentials": "true"
                }
            )
    except Exception as e:
        logger.error(f"获取高级词汇预测时出错: {e}")
        # 降级到原始智能补全服务
        try:
            from services.prompt_service import get_prompt_service
            prompt_service = get_prompt_service()
            predictions = prompt_service.get_word_predictions(request.partial_input, top_k=8)
            
            return JSONResponse(
                content={
                    "predictions": predictions,
                    "partial_input": request.partial_input,
                    "count": len(predictions),
                    "type": "basic_ngram_fallback",
                    "status": "fallback_to_basic",
                    "fallback_reason": str(e)
                },
                headers={
                    "Access-Control-Allow-Origin": "http://localhost:3000",
                    "Access-Control-Allow-Credentials": "true"
                }
            )
        except Exception as e2:
            logger.error(f"降级到基础词汇预测也失败: {e2}")
            return JSONResponse(
                status_code=500,
                content={
                    "detail": f"获取词汇预测失败: {str(e)}",
                    "fallback_error": str(e2),
                    "type": "advanced_hybrid",
                    "status": "error"
                },
                headers={
                    "Access-Control-Allow-Origin": "http://localhost:3000",
                    "Access-Control-Allow-Credentials": "true"
                }
            )

# 获取特定提示词模板详情
@app.get("/api/prompts/template/{template_id}")
async def get_prompt_template_detail(template_id: str):
    """获取特定提示词模板的详细信息"""
    try:
        prompt_service = get_prompt_service()
        template = prompt_service.get_template_by_id(template_id)
        
        if not template:
            return JSONResponse(
                status_code=404,
                content={"detail": "提示词模板不存在"},
                headers={
                    "Access-Control-Allow-Origin": "http://localhost:3000",
                    "Access-Control-Allow-Credentials": "true"
                }
            )
        
        # 找到模板所属的分类
        category = None
        for cat, templates in prompt_service.prompt_templates.items():
            if any(t["id"] == template_id for t in templates):
                category = cat
                break
        
        template["category"] = category
        
        return JSONResponse(
            content={"template": template},
            headers={
                "Access-Control-Allow-Origin": "http://localhost:3000",
                "Access-Control-Allow-Credentials": "true"
            }
        )
    except Exception as e:
        logger.error(f"获取提示词模板详情失败: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"获取提示词模板详情失败: {str(e)}"},
            headers={
                "Access-Control-Allow-Origin": "http://localhost:3000",
                "Access-Control-Allow-Credentials": "true"
            }
        )

# 模型缓存管理API
@app.get("/api/models/cache-info")
async def get_cache_info():
    """获取模型缓存信息"""
    try:
        from config.model_paths import get_model_path_config
        config = get_model_path_config()
        cache_info = config.get_cache_info()
        
        # 转换字节为人类可读格式
        def format_size(size_bytes):
            for unit in ['B', 'KB', 'MB', 'GB']:
                if size_bytes < 1024:
                    return f"{size_bytes:.1f} {unit}"
                size_bytes /= 1024
            return f"{size_bytes:.1f} TB"
        
        for dir_info in cache_info['directories'].values():
            dir_info['size_human'] = format_size(dir_info['size_bytes'])
        
        return JSONResponse(
            content={
                "cache_info": cache_info,
                "status": "success"
            },
            headers={
                "Access-Control-Allow-Origin": "http://localhost:3000",
                "Access-Control-Allow-Credentials": "true"
            }
        )
    except Exception as e:
        logger.error(f"获取缓存信息失败: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"获取缓存信息失败: {str(e)}"},
            headers={
                "Access-Control-Allow-Origin": "http://localhost:3000",
                "Access-Control-Allow-Credentials": "true"
            }
        )

# 获取可用的API模型列表（DeepSeek）
@app.get("/api/models/transformer/available")
async def get_available_transformer_models():
    """获取所有可用的API模型（现在使用DeepSeek）"""
    try:
        # 现在使用DeepSeek API，返回简化的模型信息
        models = {
            "deepseek-chat": {
                "name": "DeepSeek Chat",
                "description": "DeepSeek高质量对话模型，专注于智能补全",
                "memory_usage": "低（API调用）",
                "quality": "优秀",
                "speed": "快速"
            }
        }
        
        recommendations = {
            "low_memory": "deepseek-chat",
            "moderate_memory": "deepseek-chat", 
            "high_memory": "deepseek-chat"
        }
        
        return JSONResponse(
            content={
                "available_models": models,
                "recommendations": recommendations,
                "current_default": "deepseek-chat",
                "status": "success"
            },
            headers={
                "Access-Control-Allow-Origin": "http://localhost:3000",
                "Access-Control-Allow-Credentials": "true"
            }
        )
    except Exception as e:
        logger.error(f"获取API模型列表失败: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"获取模型列表失败: {str(e)}"},
            headers={
                "Access-Control-Allow-Origin": "http://localhost:3000",
                "Access-Control-Allow-Credentials": "true"
            }
        )

# 切换API模型（DeepSeek）
@app.post("/api/models/transformer/switch")
async def switch_transformer_model(request: dict):
    """切换当前使用的API模型（现在固定为DeepSeek）"""
    try:
        new_model = request.get("model_key", "deepseek-chat")
        
        # 现在只支持DeepSeek模型
        available_models = ["deepseek-chat", "auto"]
        
        if new_model not in available_models:
            return JSONResponse(
                status_code=400,
                content={"detail": f"模型 {new_model} 不在可用列表中，当前只支持 DeepSeek"},
                headers={
                    "Access-Control-Allow-Origin": "http://localhost:3000",
                    "Access-Control-Allow-Credentials": "true"
                }
            )
        
        # DeepSeek API无需切换，始终可用
        model_info = {
            "name": "DeepSeek Chat",
            "description": "DeepSeek高质量对话模型，专注于智能补全",
            "status": "已激活"
        }
        
        return JSONResponse(
            content={
                "message": f"当前使用模型: DeepSeek Chat",
                "model_info": model_info,
                "status": "success"
            },
            headers={
                "Access-Control-Allow-Origin": "http://localhost:3000",
                "Access-Control-Allow-Credentials": "true"
            }
        )
            
    except Exception as e:
        logger.error(f"切换API模型失败: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"切换模型失败: {str(e)}"},
            headers={
                "Access-Control-Allow-Origin": "http://localhost:3000",
                "Access-Control-Allow-Credentials": "true"
            }
        )

# 获取当前API模型状态（DeepSeek）
@app.get("/api/models/transformer/status")
async def get_transformer_model_status():
    """获取当前API模型的状态信息（DeepSeek）"""
    try:
        from services.deepseek_api_service import get_deepseek_api_service
        
        deepseek_service = get_deepseek_api_service()
        
        status_info = {
            "is_initialized": True,
            "current_model": "DeepSeek Chat",
            "preferred_model": "deepseek-chat",
            "device": "API远程调用",
            "cache_size": 0,  # API调用不使用本地缓存
            "is_available": deepseek_service.is_available()
        }
        
        # 添加DeepSeek API详细信息
        status_info["model_details"] = {
            "name": "DeepSeek Chat",
            "description": "DeepSeek高质量对话模型，专注于智能补全",
            "type": "API调用",
            "provider": "DeepSeek",
            "memory_usage": "低（无本地模型）",
            "quality": "优秀",
            "speed": "快速"
        }
        
        return JSONResponse(
            content={
                "status": status_info,
                "message": "状态获取成功"
            },
            headers={
                "Access-Control-Allow-Origin": "http://localhost:3000",
                "Access-Control-Allow-Credentials": "true"
            }
        )
        
    except Exception as e:
        logger.error(f"获取API模型状态失败: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"获取模型状态失败: {str(e)}"},
            headers={
                "Access-Control-Allow-Origin": "http://localhost:3000",
                "Access-Control-Allow-Credentials": "true"
            }
        )

# 增强自动补全（使用高质量Transformer模型）
@app.post("/api/prompts/advanced-autocomplete")
async def advanced_autocomplete(request: dict):
    """增强自动补全API - 使用高质量Transformer模型"""
    try:
        partial_input = request.get("partial_input", "")
        max_completions = request.get("max_completions", 5)
        
        if not partial_input or len(partial_input.strip()) < 1:
            return JSONResponse(
                content={"completions": []},
                headers={
                    "Access-Control-Allow-Origin": "http://localhost:3000",
                    "Access-Control-Allow-Credentials": "true"
                }
            )
        
        # 使用增强的智能补全服务
        from services.intelligent_completion_service import get_advanced_intelligent_completions
        
        logger.info(f"🚀 增强自动补全请求: {partial_input[:50]}...")
        
        completions = get_advanced_intelligent_completions(partial_input, max_completions)
        
        logger.info(f"✅ 返回 {len(completions)} 个增强补全建议")
        
        return JSONResponse(
            content={
                "completions": completions,
                "model_type": "enhanced_transformer",
                "input_length": len(partial_input),
                "status": "success"
            },
            headers={
                "Access-Control-Allow-Origin": "http://localhost:3000",
                "Access-Control-Allow-Credentials": "true"
            }
        )
        
    except Exception as e:
        logger.error(f"增强自动补全失败: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"增强自动补全失败: {str(e)}"},
            headers={
                "Access-Control-Allow-Origin": "http://localhost:3000",
                "Access-Control-Allow-Credentials": "true"
            }
        )

# 增强词汇预测（使用高质量Transformer模型）
@app.post("/api/prompts/advanced-word-predictions")
async def advanced_word_predictions(request: dict):
    """增强词汇预测API - 使用高质量Transformer模型"""
    try:
        partial_input = request.get("partial_input", "")
        top_k = request.get("top_k", 8)
        
        if not partial_input or len(partial_input.strip()) < 1:
            return JSONResponse(
                content={"predictions": []},
                headers={
                    "Access-Control-Allow-Origin": "http://localhost:3000",
                    "Access-Control-Allow-Credentials": "true"
                }
            )
        
        # 使用增强的词汇预测服务
        from services.intelligent_completion_service import get_advanced_word_predictions
        
        logger.info(f"🧠 增强词汇预测请求: {partial_input[:50]}...")
        
        predictions = get_advanced_word_predictions(partial_input, top_k)
        
        logger.info(f"✅ 返回 {len(predictions)} 个增强词汇预测")
        
        return JSONResponse(
            content={
                "predictions": predictions,
                "model_type": "enhanced_transformer", 
                "context_length": len(partial_input),
                "status": "success"
            },
            headers={
                "Access-Control-Allow-Origin": "http://localhost:3000",
                "Access-Control-Allow-Credentials": "true"
            }
        )
        
    except Exception as e:
        logger.error(f"增强词汇预测失败: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"增强词汇预测失败: {str(e)}"},
            headers={
                "Access-Control-Allow-Origin": "http://localhost:3000",
                "Access-Control-Allow-Credentials": "true"
            }
        )

# DeepSeek词汇预测（替代混合预测）
@app.post("/api/prompts/hybrid-word-predictions")
async def hybrid_word_predictions(request: dict):
    """DeepSeek词汇预测API - 使用DeepSeek API替代混合预测"""
    try:
        partial_input = request.get("partial_input", "")
        top_k = request.get("top_k", 8)
        
        if not partial_input:
            return JSONResponse(
                content={"predictions": []},
                headers={
                    "Access-Control-Allow-Origin": "http://localhost:3000",
                    "Access-Control-Allow-Credentials": "true"
                }
            )
        
        # 使用DeepSeek API预测服务
        from services.intelligent_completion_service import get_advanced_word_predictions
        
        logger.info(f"🤖 DeepSeek词汇预测请求: {partial_input[:50]}...")
        
        predictions = get_advanced_word_predictions(partial_input, top_k)
        
        logger.info(f"✅ 返回 {len(predictions)} 个DeepSeek词汇预测")
        
        return JSONResponse(
            content={
                "predictions": predictions,
                "model_type": "deepseek_api",
                "context_length": len(partial_input),
                "status": "success"
            },
            headers={
                "Access-Control-Allow-Origin": "http://localhost:3000",
                "Access-Control-Allow-Credentials": "true"
            }
        )
        
    except Exception as e:
        logger.error(f"DeepSeek词汇预测失败: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"DeepSeek词汇预测失败: {str(e)}"},
            headers={
                "Access-Control-Allow-Origin": "http://localhost:3000",
                "Access-Control-Allow-Credentials": "true"
            }
        )
