import os
import httpx
import logging
from fastapi import HTTPException
from typing import List, Dict
import json
import time
import hmac
import base64
import hashlib
import asyncio

logger = logging.getLogger(__name__)

async def get_moonshot_response(message: str, conversation_history: List[Dict] = None, api_config: Dict = None) -> str:
    """
    调用Moonshot API获取响应
    
    Args:
        message: 用户消息
        conversation_history: 对话历史
        api_config: API配置信息，包含apiKey和url
    """
    if not api_config:
        raise HTTPException(status_code=500, detail="未提供Moonshot API配置信息")
        
    async with httpx.AsyncClient() as client:
        api_key = api_config.get("apiKey", "")
        api_base = api_config.get("url", "https://api.moonshot.cn/v1")
        
        if not api_key:
            raise HTTPException(status_code=500, detail="未配置Moonshot API密钥，请在设置中添加密钥")
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # 构建消息历史
        messages = []
        if conversation_history:
            messages.extend(conversation_history)
        messages.append({"role": "user", "content": message})
        
        try:
            logger.info(f"发送请求到Moonshot API: {api_base}/chat/completions")
            
            # Moonshot API的请求体
            payload = {
                "model": "moonshot-v1-8k",  # 使用moonshot-v1-8k模型
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 2000,
                "stream": False,  # 不使用流式响应
                "presence_penalty": 0,
                "frequency_penalty": 0
            }
            
            logger.info(f"请求参数: {json.dumps(payload, ensure_ascii=False)}")
            
            response = await client.post(
                f"{api_base}/chat/completions",
                headers=headers,
                json=payload,
                timeout=60.0  # 增加超时时间到60秒
            )
            
            logger.info(f"Moonshot API响应状态码: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Moonshot API响应: {json.dumps(result, ensure_ascii=False)}")
                
                if "choices" in result and len(result["choices"]) > 0:
                    content = result["choices"][0]["message"]["content"]
                    logger.info(f"成功获取Moonshot响应: {content[:100]}...")  # 只记录前100个字符
                    return content
                else:
                    error_msg = "Moonshot API返回的响应格式不正确"
                    logger.error(error_msg)
                    raise HTTPException(status_code=500, detail=error_msg)
            else:
                error_msg = f"Moonshot API错误响应: {response.text}"
                logger.error(error_msg)
                raise HTTPException(status_code=response.status_code, detail=error_msg)
                
        except httpx.TimeoutException:
            error_msg = "请求Moonshot API超时"
            logger.error(error_msg)
            raise HTTPException(status_code=504, detail=error_msg)
        except httpx.RequestError as e:
            error_msg = f"请求Moonshot API时发生网络错误: {str(e)}"
            logger.error(error_msg)
            raise HTTPException(status_code=502, detail=error_msg)
        except Exception as e:
            error_msg = f"调用Moonshot API时发生错误: {str(e)}"
            logger.error(error_msg)
            raise HTTPException(status_code=500, detail=error_msg)

async def get_moonshot_stream_response(message: str, conversation_history: List[Dict] = None, api_config: Dict = None):
    """
    流式调用Moonshot API获取响应
    
    Args:
        message: 用户消息
        conversation_history: 对话历史
        api_config: API配置信息，包含apiKey和url
    """
    if not api_config:
        raise HTTPException(status_code=500, detail="未提供Moonshot API配置信息")
    
    MAX_RETRIES = 2
    BUFFER_SIZE = 512  # 字节
    CONNECT_TIMEOUT = 10.0
    STREAM_TIMEOUT = 20.0
    
    async with httpx.AsyncClient() as client:
        api_key = api_config.get("apiKey", "")
        api_base = api_config.get("url", "https://api.moonshot.cn/v1")
        
        if not api_key:
            raise HTTPException(status_code=500, detail="未配置Moonshot API密钥，请在设置中添加密钥")
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # 构建消息历史
        messages = []
        if conversation_history:
            messages.extend(conversation_history)
        messages.append({"role": "user", "content": message})
        
        payload = {
            "model": "moonshot-v1-8k",
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 2000,
            "stream": True,  # 启用流式响应
            "presence_penalty": 0,
            "frequency_penalty": 0
        }
        
        buffer = ""
        retry_count = 0
        
        while retry_count <= MAX_RETRIES:
            try:
                # 减少日志频率
                if retry_count == 0:
                    logger.info(f"发送流式请求到Moonshot API (尝试 {retry_count + 1}/{MAX_RETRIES + 1})")
                
                async with client.stream(
                    "POST",
                    f"{api_base}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=httpx.Timeout(CONNECT_TIMEOUT, read=STREAM_TIMEOUT)
                ) as response:
                    if response.status_code != 200:
                        error_text = await response.aread()
                        logger.error(f"Moonshot API错误响应: {response.status_code}")
                        if response.status_code >= 500 and retry_count < MAX_RETRIES:
                            retry_count += 1
                            await asyncio.sleep(1 * retry_count)  # 指数退避
                            continue
                        raise HTTPException(
                            status_code=response.status_code,
                            detail=f"Moonshot API错误: {error_text}"
                        )
                    
                    # 使用缓冲区合并小数据包
                    async for chunk in response.aiter_text():
                        buffer += chunk
                        if len(buffer) >= BUFFER_SIZE or '\n' in buffer:
                            lines = buffer.split('\n')
                            for line in lines[:-1]:  # 处理完整行
                                if line.strip():
                                    yield line + '\n'
                            buffer = lines[-1]  # 保留不完整行
                    
                    # 发送缓冲区剩余内容
                    if buffer:
                        yield buffer
                        buffer = ""
                    
                    return  # 成功完成
                    
            except httpx.TimeoutException:
                if retry_count < MAX_RETRIES:
                    retry_count += 1
                    await asyncio.sleep(1 * retry_count)
                    continue
                raise HTTPException(status_code=504, detail="请求Moonshot API超时")
            except httpx.RequestError as e:
                if retry_count < MAX_RETRIES:
                    retry_count += 1
                    await asyncio.sleep(1 * retry_count)
                    continue
                raise HTTPException(status_code=502, detail=f"请求Moonshot API时发生网络错误: {str(e)}")
            except Exception as e:
                if retry_count < MAX_RETRIES:
                    retry_count += 1
                    await asyncio.sleep(1 * retry_count)
                    continue
                raise HTTPException(status_code=500, detail=f"调用Moonshot API时发生错误: {str(e)}") 