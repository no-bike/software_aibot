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
    """流式调用Deepseek API获取响应"""
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
            logger.info(f"发送流式请求到Deepseek API: {api_base}/chat/completions")
            
            payload = {
                "model": "deepseek-chat",
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 2000,
                "stream": True
            }
            
            async with client.stream(
                "POST",
                f"{api_base}/chat/completions",
                headers=headers,
                json=payload,
                timeout=30.0
            ) as response:
                logger.info(f"Deepseek API流式响应状态码: {response.status_code}")
                
                if response.status_code != 200:
                    error_text = await response.aread()
                    logger.error(f"Deepseek API流式错误响应: {error_text}")
                    raise HTTPException(status_code=response.status_code, 
                                      detail=f"Deepseek API错误: {error_text}")
                
                async for chunk in response.aiter_text():
                    yield chunk
                    
        except Exception as e:
            logger.error(f"处理Deepseek API流式响应时发生错误: {str(e)}")
            raise HTTPException(status_code=500, 
                              detail=f"调用Deepseek API时发生错误: {str(e)}")
