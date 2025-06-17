#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DeepSeek服务

基于BaseModelService的DeepSeek API调用实现
"""

import os
from typing import List, Dict
from .base_model_service import BaseModelService

class DeepSeekService(BaseModelService):
    """DeepSeek模型服务"""
    
    def __init__(self):
        super().__init__("DeepSeek")
    
    def get_api_config(self) -> Dict[str, str]:
        """获取DeepSeek API配置"""
        return {
            "api_key": os.environ.get("DEEPSEEK_API_KEY", ""),
            "api_base": os.environ.get("DEEPSEEK_API_BASE", "")
        }
    
    def build_request_payload(self, message: str, conversation_history: List[Dict] = None) -> Dict:
        """构建DeepSeek请求载荷"""
        messages = []
        if conversation_history:
            messages.extend(conversation_history)
        messages.append({"role": "user", "content": message})
        
        return {
            "model": "deepseek-chat",
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 2000,
            "stream": True
        }
    
    def get_api_endpoint(self, api_base: str) -> str:
        """获取DeepSeek API端点"""
        return f"{api_base}/chat/completions"

# 创建全局实例
_deepseek_service = DeepSeekService()

# 兼容性函数，保持原有接口
async def get_deepseek_response(message: str, conversation_history: List[Dict] = None) -> str:
    """调用Deepseek API获取响应（非流式）"""
    return await _deepseek_service.get_non_stream_response(message, conversation_history)

async def get_deepseek_stream_response(message: str, conversation_history: List[Dict] = None):
    """调用Deepseek API获取流式响应"""
    async for chunk in _deepseek_service.get_stream_response(message, conversation_history):
        yield chunk
