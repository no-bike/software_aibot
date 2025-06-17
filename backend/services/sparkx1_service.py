#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
讯飞SparkX1服务

基于BaseModelService的讯飞SparkX1 API调用实现
"""

import os
import json
from typing import List, Dict, Optional
from .base_model_service import BaseModelService

class SparkX1Service(BaseModelService):
    """讯飞SparkX1模型服务"""
    
    def __init__(self):
        super().__init__("SparkX1")
    
    def get_api_config(self) -> Dict[str, str]:
        """获取SparkX1 API配置"""
        return {
            "api_key": os.environ.get("SPARKX1_API_KEY", ""),
            "api_base": os.environ.get("SPARKX1_API_BASE", "")
        }
    
    def build_request_payload(self, message: str, conversation_history: List[Dict] = None) -> Dict:
        """构建SparkX1请求载荷"""
        messages = []
        if conversation_history:
            messages.extend(conversation_history)
        messages.append({"role": "user", "content": message})
        
        return {
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
    
    def get_api_endpoint(self, api_base: str) -> str:
        """获取SparkX1 API端点"""
        return api_base
    
    def process_stream_chunk(self, chunk: str) -> Optional[str]:
        """处理SparkX1的流式响应块"""
        if not chunk.strip():
            return None
        
        # 检查是否已经是SSE格式
        if chunk.startswith('data: '):
            return chunk + '\n'
        
        # 尝试解析为JSON并转换为SSE格式
        try:
            data = json.loads(chunk)
            return f"data: {json.dumps(data, ensure_ascii=False)}\n"
        except json.JSONDecodeError:
            # 如果不是JSON，可能是原始文本，包装成SSE格式
            if chunk.strip():
                content_data = {
                    "choices": [
                        {
                            "delta": {
                                "content": chunk.strip()
                            }
                        }
                    ]
                }
                return f"data: {json.dumps(content_data, ensure_ascii=False)}\n"
        
        return None

# 创建全局实例
_sparkx1_service = SparkX1Service()

# 兼容性函数，保持原有接口
async def get_sparkx1_response(message: str, conversation_history: List[Dict] = None) -> str:
    """调用讯飞SparkX1 HTTP API获取响应（非流式）"""
    return await _sparkx1_service.get_non_stream_response(message, conversation_history)

async def get_sparkx1_stream_response(message: str, conversation_history: List[Dict] = None):
    """调用讯飞SparkX1 HTTP API获取流式响应"""
    async for chunk in _sparkx1_service.get_stream_response(message, conversation_history):
        yield chunk
