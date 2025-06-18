#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DeepSeek API智能补全服务

基于DeepSeek API的高效智能补全功能
专注于理解用户意图，提供精准的文本补全
"""

import asyncio
import aiohttp
import logging
import time
import json
import os
from typing import List, Dict, Any, Optional
import threading
import nest_asyncio

logger = logging.getLogger(__name__)

class DeepSeekAPIService:
    """DeepSeek API智能补全服务"""
    
    def __init__(self, api_key: str = None, api_base: str = None):
        """
        初始化DeepSeek API服务
        
        Args:
            api_key: API密钥
            api_base: API基础URL
        """
        self.api_key = api_key
        self.api_base = api_base or "https://api.deepseek.com/v1"
        self.prediction_cache = {}
        self.max_cache_size = 1000
        self._session = None
        self._session_lock = threading.Lock()
        
        # 如果没有提供API密钥，尝试从配置文件加载
        if not self.api_key:
            self._load_config()
        
        logger.info(f"🚀 DeepSeek API服务初始化完成")
        logger.info(f"🌐 API地址: {self.api_base}")
    
    def _load_config(self):
        """从配置文件加载API配置"""
        try:
            config_path = os.path.join(os.path.dirname(__file__), '..', 'api.txt')
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                    # 查找DeepSeek配置
                    lines = content.split('\n')
                    in_deepseek_section = False
                    
                    for line in lines:
                        line = line.strip()
                        if line == '[DEEPSEEK]':
                            in_deepseek_section = True
                            continue
                        elif line.startswith('[') and line.endswith(']'):
                            in_deepseek_section = False
                            continue
                        
                        if in_deepseek_section and '=' in line:
                            key, value = line.split('=', 1)
                            key = key.strip()
                            value = value.strip()
                            
                            if key == 'API_KEY':
                                self.api_key = value
                                logger.info("✅ 已从api.txt加载DeepSeek API密钥")
                            elif key == 'API_BASE':
                                self.api_base = value
                                logger.info(f"✅ 已从api.txt加载API地址: {value}")
            
            if not self.api_key:
                logger.warning("⚠️ 未找到DeepSeek API密钥配置")
                
        except Exception as e:
            logger.error(f"❌ 加载配置文件失败: {str(e)}")
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """获取HTTP会话"""
        if self._session is None or self._session.closed:
            with self._session_lock:
                if self._session is None or self._session.closed:
                    timeout = aiohttp.ClientTimeout(total=30)
                    self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session
    
    async def _call_deepseek_api(self, prompt: str, max_tokens: int = 150) -> List[str]:
        """调用DeepSeek API"""
        if not self.api_key:
            logger.error("❌ 缺少DeepSeek API密钥")
            return []
        
        # 检查API_BASE是否已经包含完整路径
        if self.api_base.endswith('/chat/completions'):
            url = self.api_base
        else:
            url = f"{self.api_base}/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": "deepseek-chat",
            "messages": [
                {
                    "role": "system",
                    "content": "你是一个专业的智能输入法补全助手。你的任务是为用户提供自然、有用的文本补全建议，而不是回答问题或提供信息。"
                },
                {
                    "role": "user", 
                    "content": f"用户正在输入：『{prompt}』\n\n请提供5个可能的文本补全建议，要求：\n1. 直接延续用户的输入，不要重复用户已输入的内容\n2. 补全要简洁自然，符合中文表达习惯\n3. 每行一个建议，不要添加序号或解释\n4. 专注于补全而不是回答问题\n5. 如果用户输入看起来像问题，请补全问题的不同表达方式\n6. 如果用户正在输入的部分是英文，请补全英文而不是中文\n7. 不要出现与前面的文本重复的词汇\n\n补全建议："
                }
            ],
            "max_tokens": max_tokens,
            "temperature": 0.3,  # 降低温度以获得更稳定的结果
            "stream": False
        }
        
        # 使用临时会话，确保每次调用后正确关闭
        timeout = aiohttp.ClientTimeout(total=30)
        connector = aiohttp.TCPConnector(limit=1, limit_per_host=1)
        
        try:
            async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
                async with session.post(url, headers=headers, json=data) as response:
                    result = await response.json()
                    
                    if response.status == 200 and "choices" in result:
                        content = result["choices"][0]["message"]["content"]
                        # 解析返回的补全建议
                        suggestions = []
                        for line in content.split('\n'):
                            line = line.strip()
                            # 跳过空行、序号行和包含提示文本的行
                            if line and not any(skip_word in line.lower() for skip_word in [
                                '补全建议', '建议', '选项', '如下', '：', '。', '1.', '2.', '3.', '4.', '5.',
                                '用户', '输入', '可能', '以下'
                            ]):
                                # 移除序号和特殊字符
                                clean_line = line.lstrip('1234567890.-、·• ').strip()
                                if clean_line and len(clean_line) > 0 and not clean_line.startswith(prompt):
                                    suggestions.append(clean_line)
                        
                        return suggestions[:5]  # 返回最多5个建议
                    else:
                        logger.error(f"❌ DeepSeek API调用失败: {result}")
                        return []
                        
        except Exception as e:
            logger.error(f"❌ DeepSeek API调用异常: {str(e)}")
            return []
    
    def get_intelligent_completions(self, context: str, max_completions: int = 5) -> List[str]:
        """获取智能补全建议"""
        try:
            # 直接使用API调用获取完整补全文本
            import asyncio
            import nest_asyncio
            
            try:
                nest_asyncio.apply()
                loop = asyncio.get_event_loop()
                completions = loop.run_until_complete(self._call_deepseek_api(context, max_tokens=200))
                
                # 为每个补全添加原始输入作为前缀
                full_completions = []
                for completion in completions[:max_completions]:
                    if completion and not completion.startswith(context):
                        full_completion = context + completion
                        full_completions.append(full_completion)
                    else:
                        full_completions.append(completion)
                
                return full_completions
                
            except ImportError:
                # 如果没有nest_asyncio，使用线程池方案
                import concurrent.futures
                
                def run_in_thread():
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        completions = new_loop.run_until_complete(self._call_deepseek_api(context, max_tokens=200))
                        # 为每个补全添加原始输入作为前缀
                        full_completions = []
                        for completion in completions[:max_completions]:
                            if completion and not completion.startswith(context):
                                full_completion = context + completion
                                full_completions.append(full_completion)
                            else:
                                full_completions.append(completion)
                        return full_completions
                    finally:
                        new_loop.close()
                        asyncio.set_event_loop(None)
                
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(run_in_thread)
                    return future.result(timeout=30)
            
        except Exception as e:
            logger.error(f"❌ 获取智能补全失败: {str(e)}")
            return []
    
    def is_available(self) -> bool:
        """检查API服务是否可用"""
        return bool(self.api_key)
    
    async def close(self):
        """关闭HTTP会话"""
        if self._session:
            await self._session.close()
            self._session = None


# 全局服务实例
_deepseek_service = None
_service_lock = threading.Lock()

def get_deepseek_api_service(api_key: str = None, api_base: str = None) -> DeepSeekAPIService:
    """
    获取DeepSeek API服务实例（单例模式）
    
    Args:
        api_key: API密钥
        api_base: API基础URL
    """
    global _deepseek_service
    
    with _service_lock:
        if _deepseek_service is None:
            logger.info("🏗️ 创建DeepSeek API服务实例")
            _deepseek_service = DeepSeekAPIService(api_key=api_key, api_base=api_base)
        
        return _deepseek_service

def test_deepseek_api_connection() -> bool:
    """测试DeepSeek API连接"""
    try:
        service = get_deepseek_api_service()
        if not service.is_available():
            logger.error("❌ API密钥未配置")
            return False
        
        # 简单测试
        results = service.get_intelligent_completions("今天天气", 3)
        if results:
            logger.info("✅ DeepSeek API连接测试成功")
            return True
        else:
            logger.error("❌ API调用失败")
            return False
            
    except Exception as e:
        logger.error(f"❌ API连接测试失败: {str(e)}")
        return False 