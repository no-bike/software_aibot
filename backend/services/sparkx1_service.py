import os
import httpx
import logging
import asyncio
from fastapi import HTTPException
from typing import List, Dict

logger = logging.getLogger(__name__)

async def get_sparkx1_response(message: str, conversation_history: List[Dict] = None) -> str:
    """调用讯飞SparkX1 HTTP API获取响应"""
    async with httpx.AsyncClient() as client:
        api_token = os.environ.get("SPARKX1_API_TOKEN", "")
        api_base = os.environ.get("SPARKX1_API_BASE", "")
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_token}"
        }
        
        messages = []
        if conversation_history:
            messages.extend(conversation_history)
        messages.append({"role": "user", "content": message})
        
        try:
            logger.info(f"发送请求到SparkX1 API: {api_base}")
            logger.info(f"消息历史: {messages}")
            
            payload = {
                "max_tokens": 32768,
                "top_k": 6,
                "temperature": 1.2,
                "messages": messages,
                "model": "x1",
                "tools": [
                    {
                        "web_search": {
                            "search_mode": "normal",
                            "enable": False
                        },
                        "type": "web_search"
                    }
                ],
                "stream": False
            }
            
            response = await client.post(
                api_base,
                headers=headers,
                json=payload,
                timeout=30.0
            )
            
            logger.info(f"SparkX1 API响应状态码: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"SparkX1 API响应: {result}")
                if "choices" in result and len(result["choices"]) > 0:
                    return result["choices"][0]["message"]["content"]
                else:
                    raise HTTPException(status_code=500, 
                                      detail="SparkX1 API返回的响应格式不正确")
            else:
                logger.error(f"SparkX1 API错误响应: {response.text}")
                raise HTTPException(status_code=response.status_code, 
                                  detail=f"SparkX1 API错误: {response.text}")
        except Exception as e:
            logger.error(f"处理SparkX1 API响应时发生错误: {str(e)}")
            raise HTTPException(status_code=500, 
                              detail=f"调用SparkX1 API时发生错误: {str(e)}")

async def get_sparkx1_stream_response(message: str, conversation_history: List[Dict] = None):
    """优化后的流式调用SparkX1 API获取响应"""
    MAX_RETRIES = 2
    BUFFER_SIZE = 512  # 字节
    CONNECT_TIMEOUT = 10.0
    STREAM_TIMEOUT = 20.0
    
    async with httpx.AsyncClient() as client:
        api_token = os.environ.get("SPARKX1_API_TOKEN", "")
        api_base = os.environ.get("SPARKX1_API_BASE", "")
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_token}"
        }
        
        messages = []
        if conversation_history:
            messages.extend(conversation_history)
        messages.append({"role": "user", "content": message})
        
        payload = {
            "max_tokens": 32768,
            "top_k": 6,
            "temperature": 1.2,
            "messages": messages,
            "model": "x1",
            "tools": [
                {
                    "web_search": {
                        "search_mode": "normal",
                        "enable": False
                    },
                    "type": "web_search"
                }
            ],
            "stream": True
        }
        
        buffer = ""
        retry_count = 0
        
        while retry_count <= MAX_RETRIES:
            try:
                # 减少日志频率
                if retry_count == 0:
                    logger.info(f"发送流式请求到SparkX1 API (尝试 {retry_count + 1}/{MAX_RETRIES + 1})")
                
                async with client.stream(
                    "POST",
                    api_base,
                    headers=headers,
                    json=payload,
                    timeout=httpx.Timeout(CONNECT_TIMEOUT, read=STREAM_TIMEOUT)
                ) as response:
                    if response.status_code != 200:
                        error_text = await response.aread()
                        logger.error(f"SparkX1 API错误响应: {response.status_code}")
                        if response.status_code >= 500 and retry_count < MAX_RETRIES:
                            retry_count += 1
                            await asyncio.sleep(1 * retry_count)  # 指数退避
                            continue
                        raise HTTPException(
                            status_code=response.status_code,
                            detail=f"SparkX1 API错误: {error_text}"
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
                    
            except (httpx.ReadTimeout, httpx.ConnectTimeout) as e:
                if retry_count < MAX_RETRIES:
                    retry_count += 1
                    await asyncio.sleep(1 * retry_count)
                    continue
                logger.error(f"SparkX1 API连接超时: {str(e)}")
                raise HTTPException(
                    status_code=504,
                    detail=f"SparkX1 API连接超时: {str(e)}"
                )
            except Exception as e:
                logger.error(f"处理SparkX1 API流式响应时发生错误: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail=f"调用SparkX1 API时发生错误: {str(e)}"
                )
        
        raise HTTPException(
            status_code=503,
            detail="达到最大重试次数，请稍后再试"
        )
