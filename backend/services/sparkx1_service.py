import os
import httpx
import logging
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
