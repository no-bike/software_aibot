#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Moonshot服务

基于BaseModelService的Moonshot API调用实现
"""

import os
from typing import List, Dict, Optional
from .base_model_service import BaseModelService

class MoonshotService(BaseModelService):
    """Moonshot模型服务"""
    
    def __init__(self, api_config: Dict = None):
        super().__init__("Moonshot")
        self.api_config_override = api_config
    
    def get_api_config(self) -> Dict[str, str]:
        """获取Moonshot API配置"""
        if self.api_config_override:
            return {
                "api_key": self.api_config_override.get("apiKey", ""),
                "api_base": self.api_config_override.get("url", "https://api.moonshot.cn/v1")
            }
        return {
            "api_key": os.environ.get("MOONSHOT_API_KEY", ""),
            "api_base": os.environ.get("MOONSHOT_API_BASE", "https://api.moonshot.cn/v1")
        }
    
    def build_request_payload(self, message: str, conversation_history: List[Dict] = None) -> Dict:
        """构建Moonshot请求载荷"""
        messages = []
        if conversation_history:
            messages.extend(conversation_history)
        messages.append({"role": "user", "content": message})
        
        return {
            "model": "moonshot-v1-8k",
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 2000,
            "stream": True,  # 启用流式响应
            "presence_penalty": 0,
            "frequency_penalty": 0
        }
    
    def get_api_endpoint(self, api_base: str) -> str:
        """获取Moonshot API端点"""
        return f"{api_base}/chat/completions"

# 兼容性函数，保持原有接口
async def get_moonshot_response(message: str, conversation_history: List[Dict] = None, api_config: Dict = None) -> str:
    """调用Moonshot API获取响应（非流式）"""
    service = MoonshotService(api_config)
    return await service.get_non_stream_response(message, conversation_history)

async def get_moonshot_stream_response(message: str, conversation_history: List[Dict] = None, api_config: Dict = None):
    """调用Moonshot API获取流式响应"""
    service = MoonshotService(api_config)
    async for chunk in service.get_stream_response(message, conversation_history):
        yield chunk 