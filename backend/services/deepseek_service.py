import os
import httpx
import logging
from fastapi import HTTPException
from typing import List, Dict

logger = logging.getLogger(__name__)

async def get_deepseek_response(message: str, conversation_history: List[Dict] = None) -> str:
    """调用Deepseek API获取响应"""
    async with httpx.AsyncClient(timeout=httpx.Timeout(60.0, read=120.0)) as client:  # 增加超时时间
        api_key = os.environ.get("DEEPSEEK_API_KEY", "")
        api_base = os.environ.get("DEEPSEEK_API_BASE", "")
        
        if not api_key:
            raise HTTPException(status_code=500, detail="未配置DEEPSEEK_API_KEY环境变量")
        if not api_base:
            raise HTTPException(status_code=500, detail="未配置DEEPSEEK_API_BASE环境变量")
        
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
                "max_tokens": 2000,
                "stream": False  # 确保不使用流式响应
            }
            
            response = await client.post(
                f"{api_base}/chat/completions",
                headers=headers,
                json=payload
            )
            
            logger.info(f"Deepseek API响应状态码: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Deepseek API响应内容长度: {len(str(result))}")
                if "choices" in result and len(result["choices"]) > 0:
                    content = result["choices"][0]["message"]["content"]
                    logger.info(f"成功获取Deepseek响应，内容长度: {len(content)}")
                    return content
                else:
                    raise HTTPException(status_code=500, 
                                      detail="Deepseek API返回的响应格式不正确")
            else:
                logger.error(f"Deepseek API错误响应: {response.text}")
                raise HTTPException(status_code=response.status_code, 
                                  detail=f"Deepseek API错误: {response.text}")
        except httpx.TimeoutException:
            logger.error("Deepseek API请求超时")
            raise HTTPException(status_code=504, detail="请求Deepseek API超时，请稍后重试")
        except httpx.RequestError as e:
            logger.error(f"Deepseek API网络错误: {str(e)}")
            raise HTTPException(status_code=502, detail=f"网络错误: {str(e)}")
        except Exception as e:
            logger.error(f"处理Deepseek API响应时发生错误: {str(e)}")
            raise HTTPException(status_code=500, 
                              detail=f"调用Deepseek API时发生错误: {str(e)}")
