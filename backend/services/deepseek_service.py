import os
import httpx
import logging
from fastapi import HTTPException
from typing import List, Dict

logger = logging.getLogger(__name__)

async def get_deepseek_response(message: str, conversation_history: List[Dict] = None) -> str:
    """调用Deepseek API获取响应"""
    async with httpx.AsyncClient() as client:
        api_key = os.environ.get("DEEPSEEK_API_KEY", "")
        api_base = os.environ.get("DEEPSEEK_API_BASE", "")
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        messages = []
        if conversation_history:
            messages.extend(conversation_history)
        messages.append({"role": "user", "content": message})
        
        try:
            logger.info(f"发送请求到Deepseek API: {api_base}/chat/completions")
            logger.info(f"消息历史: {messages}")
            
            payload = {
                "model": "deepseek-chat",
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 2000
            }
            
            response = await client.post(
                f"{api_base}/chat/completions",
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

async def get_deepseek_stream_response(message: str, conversation_history: List[Dict] = None):
    """优化后的流式调用Deepseek API获取响应"""
    MAX_RETRIES = 2
    BUFFER_SIZE = 512  # 字节
    CONNECT_TIMEOUT = 10.0
    STREAM_TIMEOUT = 20.0
    
    async with httpx.AsyncClient() as client:
        api_key = os.environ.get("DEEPSEEK_API_KEY", "")
        api_base = os.environ.get("DEEPSEEK_API_BASE", "")
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        messages = []
        if conversation_history:
            messages.extend(conversation_history)
        messages.append({"role": "user", "content": message})
        
        payload = {
            "model": "deepseek-chat",
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 2000,
            "stream": True
        }
        
        buffer = ""
        retry_count = 0
        
        while retry_count <= MAX_RETRIES:
            try:
                # 减少日志频率
                if retry_count == 0:
                    logger.info(f"发送流式请求到Deepseek API (尝试 {retry_count + 1}/{MAX_RETRIES + 1})")
                
                async with client.stream(
                    "POST",
                    f"{api_base}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=httpx.Timeout(CONNECT_TIMEOUT, read=STREAM_TIMEOUT)
                ) as response:
                    if response.status_code != 200:
                        error_text = await response.aread()
                        logger.error(f"Deepseek API错误响应: {response.status_code}")
                        if response.status_code >= 500 and retry_count < MAX_RETRIES:
                            retry_count += 1
                            await asyncio.sleep(1 * retry_count)  # 指数退避
                            continue
                        raise HTTPException(
                            status_code=response.status_code,
                            detail=f"Deepseek API错误: {error_text}"
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
                logger.error(f"Deepseek API连接超时: {str(e)}")
                raise HTTPException(
                    status_code=504,
                    detail=f"Deepseek API连接超时: {str(e)}"
                )
            except Exception as e:
                logger.error(f"处理Deepseek API流式响应时发生错误: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail=f"调用Deepseek API时发生错误: {str(e)}"
                )
        
        raise HTTPException(
            status_code=503,
            detail="达到最大重试次数，请稍后再试"
        )
