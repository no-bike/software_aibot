#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智谱AI GLM模型服务

使用BaseModelService基类的完整示例
演示如何正确继承和实现新模型
"""

import os
import json
import logging
from typing import List, Dict, Optional
from .base_model_service import BaseModelService

logger = logging.getLogger(__name__)

class GLMService(BaseModelService):
    """智谱AI GLM模型服务"""
    
    def __init__(self):
        super().__init__("智谱AI GLM")
        logger.info(f"🤖 初始化{self.model_name}服务")
    
    def get_api_config(self) -> Dict[str, str]:
        """
        获取GLM API配置
        
        Returns:
            包含api_key和api_base的配置字典
        """
        return {
            "api_key": os.environ.get("GLM_API_KEY", ""),
            "api_base": os.environ.get("GLM_API_BASE", "https://open.bigmodel.cn/api/paas/v4")
        }
    
    def build_request_payload(self, message: str, conversation_history: List[Dict] = None) -> Dict:
        """
        构建GLM API请求载荷
        
        Args:
            message: 用户消息
            conversation_history: 对话历史
            
        Returns:
            GLM API格式的请求载荷
        """
        # 构建消息列表
        messages = []
        
        # 添加对话历史
        if conversation_history:
            for msg in conversation_history:
                if msg.get("role") in ["user", "assistant"]:
                    messages.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })
        
        # 添加当前用户消息
        messages.append({
            "role": "user",
            "content": message
        })
        
        # GLM API特定的请求格式
        payload = {
            "model": "glm-4",  # 使用GLM-4模型
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 2000,
            "stream": True,
            "top_p": 0.9,
            "do_sample": True
        }
        
        logger.debug(f"GLM请求载荷: {json.dumps(payload, ensure_ascii=False, indent=2)}")
        return payload
    
    def get_api_endpoint(self, api_base: str) -> str:
        """
        获取GLM API端点
        
        Args:
            api_base: API基础URL
            
        Returns:
            完整的API端点URL
        """
        return f"{api_base}/chat/completions"
    
    def build_headers(self, api_key: str) -> Dict[str, str]:
        """
        构建GLM特定的请求头
        
        Args:
            api_key: API密钥
            
        Returns:
            GLM API格式的请求头
        """
        return {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream"
        }
    
    def process_stream_chunk(self, chunk: str) -> Optional[str]:
        """
        处理GLM流式响应块
        
        Args:
            chunk: 原始响应块
            
        Returns:
            处理后的SSE格式数据
        """
        # GLM API返回的是标准SSE格式
        chunk = chunk.strip()
        
        if not chunk:
            return None
        
        # 处理GLM的SSE格式响应
        if chunk.startswith('data: '):
            data_content = chunk[6:].strip()  # 移除 'data: ' 前缀
            
            # 检查是否是结束标记
            if data_content == '[DONE]':
                return "data: [DONE]\n\n"
            
            try:
                # 解析JSON数据
                data = json.loads(data_content)
                
                # 提取GLM响应中的内容
                if 'choices' in data and len(data['choices']) > 0:
                    choice = data['choices'][0]
                    if 'delta' in choice and 'content' in choice['delta']:
                        content = choice['delta']['content']
                        if content:
                            # 转换为标准SSE格式
                            response_data = {
                                "choices": [
                                    {
                                        "delta": {
                                            "content": content
                                        }
                                    }
                                ]
                            }
                            return f"data: {json.dumps(response_data, ensure_ascii=False)}\n\n"
                
                # 如果没有内容，返回原始数据
                return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
                
            except json.JSONDecodeError as e:
                logger.warning(f"GLM JSON解析失败: {str(e)}, 原始数据: {data_content}")
                # 如果JSON解析失败，可能是纯文本内容
                if data_content and data_content != '[DONE]':
                    content_data = {
                        "choices": [
                            {
                                "delta": {
                                    "content": data_content
                                }
                            }
                        ]
                    }
                    return f"data: {json.dumps(content_data, ensure_ascii=False)}\n\n"
        
        return None
    
    def is_available(self) -> bool:
        """
        检查GLM服务是否可用
        
        Returns:
            服务是否可用
        """
        try:
            config = self.get_api_config()
            return bool(config.get("api_key") and config.get("api_base"))
        except Exception as e:
            logger.error(f"检查GLM服务可用性失败: {str(e)}")
            return False

# 创建全局GLM服务实例
_glm_service = GLMService()

# 兼容性函数 - 保持与其他服务一致的接口
async def get_glm_response(message: str, conversation_history: List[Dict] = None) -> str:
    """
    调用GLM API获取响应（非流式）
    
    Args:
        message: 用户消息
        conversation_history: 对话历史
        
    Returns:
        GLM模型的响应文本
    """
    try:
        return await _glm_service.get_non_stream_response(message, conversation_history)
    except Exception as e:
        logger.error(f"GLM非流式响应失败: {str(e)}")
        raise

async def get_glm_stream_response(message: str, conversation_history: List[Dict] = None):
    """
    调用GLM API获取流式响应
    
    Args:
        message: 用户消息
        conversation_history: 对话历史
        
    Yields:
        GLM模型的流式响应块
    """
    try:
        async for chunk in _glm_service.get_stream_response(message, conversation_history):
            yield chunk
    except Exception as e:
        logger.error(f"GLM流式响应失败: {str(e)}")
        raise

def get_glm_service() -> GLMService:
    """
    获取GLM服务实例
    
    Returns:
        GLM服务实例
    """
    return _glm_service

# 智能补全功能（可选）
def get_glm_intelligent_completions(partial_input: str, max_completions: int = 5) -> List[str]:
    """
    使用GLM进行智能补全
    
    Args:
        partial_input: 部分输入文本
        max_completions: 最大补全数量
        
    Returns:
        补全建议列表
    """
    try:
        if not _glm_service.is_available():
            logger.warning("GLM服务不可用，无法提供智能补全")
            return []
        
        # 构建补全提示
        completion_prompt = f"请为以下不完整的文本提供{max_completions}个可能的补全建议，每个建议单独一行：\n\n{partial_input}"
        
        # 这里可以调用GLM API进行补全
        # 为了简化示例，返回空列表
        # 实际实现中可以调用get_glm_response
        logger.info(f"GLM智能补全请求: {partial_input[:30]}...")
        return []
        
    except Exception as e:
        logger.error(f"GLM智能补全失败: {str(e)}")
        return [] 