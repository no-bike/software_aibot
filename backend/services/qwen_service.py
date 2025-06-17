#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通义千问服务

基于BaseModelService的通义千问 API调用实现
"""

import os
from typing import List, Dict
from .base_model_service import BaseModelService

class QwenService(BaseModelService):
    """通义千问模型服务"""
    
    def __init__(self):
        super().__init__("通义千问")
    
    def get_api_config(self) -> Dict[str, str]:
        """获取通义千问 API配置"""
        return {
            "api_key": os.environ.get("QWEN_API_KEY", ""),
            "api_base": os.environ.get("QWEN_API_BASE", "")
        }
    
    def build_request_payload(self, message: str, conversation_history: List[Dict] = None) -> Dict:
        """构建通义千问请求载荷"""
        messages = []
        if conversation_history:
            messages.extend(conversation_history)
        messages.append({"role": "user", "content": message})
        
        return {
            "model": "qwen-plus",  # 可以配置为其他模型如 qwen-max, qwen-turbo
            "messages": messages,
            "max_tokens": 2000,
            "temperature": 0.7,
            "top_p": 0.8,
            "stream": True  # 启用流式响应
        }
    
    def get_api_endpoint(self, api_base: str) -> str:
        """获取通义千问 API端点"""
        return api_base

# 创建全局实例
_qwen_service = QwenService()

# 兼容性函数，保持原有接口
async def get_qwen_response(message: str, conversation_history: List[Dict] = None) -> str:
    """调用通义千问 API获取响应（非流式）"""
    return await _qwen_service.get_non_stream_response(message, conversation_history)

async def get_qwen_stream_response(message: str, conversation_history: List[Dict] = None):
    """调用通义千问 API获取流式响应"""
    async for chunk in _qwen_service.get_stream_response(message, conversation_history):
        yield chunk