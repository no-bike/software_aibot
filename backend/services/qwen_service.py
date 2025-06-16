import os
import httpx
import logging
from fastapi import HTTPException
from typing import List, Dict

logger = logging.getLogger(__name__)

async def get_qwen_response(message: str, conversation_history: List[Dict] = None) -> str:
    """调用通义千问 API获取响应"""
    async with httpx.AsyncClient(timeout=httpx.Timeout(60.0, read=120.0)) as client:
        api_key = os.environ.get("QWEN_API_KEY", "")
        api_base = os.environ.get("QWEN_API_BASE", "")
        
        if not api_key:
            raise HTTPException(status_code=500, detail="未配置QWEN_API_KEY环境变量")
        if not api_base:
            raise HTTPException(status_code=500, detail="未配置QWEN_API_BASE环境变量")
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # 构建消息列表
        messages = []
        if conversation_history:
            messages.extend(conversation_history)
        messages.append({"role": "user", "content": message})
        
        try:
            logger.info(f"发送请求到通义千问 API: {api_base}")
            logger.info(f"消息历史: {messages}")
            
            payload = {
                "model": "qwen-plus",  # 可以配置为其他模型如 qwen-max, qwen-turbo
                "messages": messages,
                "max_tokens": 2000,
                "temperature": 0.7,
                "top_p": 0.8,
                "stream": False
            }
            
            response = await client.post(
                api_base,
                headers=headers,
                json=payload,
                timeout=90.0
            )
            
            logger.info(f"通义千问 API响应状态码: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"通义千问 API响应: {result}")
                
                if "choices" in result and len(result["choices"]) > 0:
                    content = result["choices"][0]["message"]["content"]
                    return content
                else:
                    raise HTTPException(status_code=500, 
                                      detail="通义千问 API返回的响应格式不正确")
            else:
                error_text = response.text
                logger.error(f"通义千问 API错误响应: {error_text}")
                raise HTTPException(status_code=response.status_code, 
                                  detail=f"通义千问 API错误: {error_text}")
                
        except httpx.ReadTimeout:
            logger.error("通义千问 API请求超时")
            raise HTTPException(status_code=504, 
                              detail="通义千问 API请求超时，请稍后重试")
        except httpx.ConnectTimeout:
            logger.error("通义千问 API连接超时")
            raise HTTPException(status_code=503, 
                              detail="通义千问 API连接超时，请检查网络连接")
        except Exception as e:
            logger.error(f"处理通义千问 API响应时发生错误: {str(e)}")
            raise HTTPException(status_code=500, 
                              detail=f"调用通义千问 API时发生错误: {str(e)}") 