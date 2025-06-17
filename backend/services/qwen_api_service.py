#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通义千问API智能补全服务

基于阿里云通义千问API的高效智能补全功能
支持免费额度，无需本地模型下载
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

class QwenAPIService:
    """通义千问API智能补全服务"""
    
    def __init__(self, api_key: str = None, api_base: str = None):
        """
        初始化通义千问API服务
        
        Args:
            api_key: API密钥
            api_base: API基础URL
        """
        self.api_key = api_key
        self.api_base = api_base or "https://dashscope.aliyuncs.com/compatible-mode/v1"
        self.prediction_cache = {}
        self.max_cache_size = 1000
        self._session = None
        self._session_lock = threading.Lock()
        
        # 如果没有提供API密钥，尝试从配置文件加载
        if not self.api_key:
            self._load_config()
        
        logger.info(f"🚀 通义千问API服务初始化完成")
        logger.info(f"🌐 API地址: {self.api_base}")
    
    def _load_config(self):
        """从api.txt文件加载配置"""
        try:
            api_file_path = os.path.join(os.path.dirname(__file__), '..', 'api.txt')
            if os.path.exists(api_file_path):
                with open(api_file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 解析配置文件
                current_section = None
                for line in content.strip().split('\n'):
                    line = line.strip()
                    if line.startswith('[') and line.endswith(']'):
                        current_section = line[1:-1].lower()
                    elif '=' in line and current_section == 'qwen':
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        
                        if key == 'API_KEY':
                            self.api_key = value
                            logger.info("✅ 已从api.txt加载通义千问API密钥")
                        elif key == 'API_BASE':
                            self.api_base = value
                            logger.info(f"✅ 已从api.txt加载API地址: {value}")
            else:
                logger.warning("📁 api.txt文件不存在")
                
        except Exception as e:
            logger.warning(f"⚠️ 加载api.txt文件失败: {str(e)}")
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """获取或创建HTTP会话"""
        if self._session is None:
            with self._session_lock:
                if self._session is None:
                    timeout = aiohttp.ClientTimeout(total=30)
                    self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session
    
    async def _call_qwen_api(self, prompt: str, max_tokens: int = 100) -> List[str]:
        """调用通义千问API"""
        if not self.api_key:
            logger.error("❌ 缺少通义千问API密钥")
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
            "model": "qwen-turbo",
            "messages": [
                {
                    "role": "user",
                    "content": f"作为一个智能输入法补全助手，请为用户正在输入的文本提供后续补全建议。用户当前输入：『{prompt}』\n\n要求：\n
                    1. 只提供可能的文本延续，不要回答问题\n
                    2. 每行一个补全建议，直接给出完整的延续文本\n
                    3. 补全要自然流畅，符合中文表达习惯\n
                    4. 最多提供5个不同的补全选项\n
                    5. 不要添加序号、标点或解释说明\n
                    6. 不要出现与前面的文本重复的词汇\n\n补全建议："
                }
            ],
            "max_tokens": max_tokens,
            "temperature": 0.7,
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
                            # 跳过空行和包含"补全建议"等提示文本的行
                            if line and not any(skip_word in line for skip_word in ['补全建议', '选项', '建议', '如下', '：', '。']):
                                # 移除序号和特殊字符
                                clean_line = line.lstrip('1234567890.-、·• ')
                                if clean_line and len(clean_line.strip()) > 0:
                                    suggestions.append(clean_line.strip())
                        
                        return suggestions[:5]  # 返回最多5个建议
                    else:
                        logger.error(f"❌ 通义千问API调用失败: {result}")
                        return []
                        
        except Exception as e:
            logger.error(f"❌ 通义千问API调用异常: {str(e)}")
            return []
    
    async def predict_next_words(self, context: str, num_predictions: int = 8) -> List[Dict[str, Any]]:
        """使用通义千问API预测下一个词"""
        try:
            # 检查缓存
            cache_key = f"{context}_{num_predictions}"
            if cache_key in self.prediction_cache:
                logger.debug(f"🔍 使用缓存结果: {context[:20]}...")
                return self.prediction_cache[cache_key]
            
            context = context.strip()
            if len(context) < 1:
                return []
            
            logger.debug(f"🤖 通义千问API预测: {context[:50]}...")
            start_time = time.time()
            
            # 调用API
            suggestions = await self._call_qwen_api(context, max_tokens=150)
            
            # 转换为标准格式
            results = []
            for i, suggestion in enumerate(suggestions[:num_predictions]):
                if suggestion and len(suggestion.strip()) > 0:
                    results.append({
                        "word": suggestion.strip(),
                        "probability": 0.9 - (i * 0.1),  # 简单的概率分配
                        "model": "qwen_api",
                        "context": context[-30:] if len(context) > 30 else context
                    })
            
            predict_time = time.time() - start_time
            logger.debug(f"⚡ 通义千问API预测完成 ({predict_time:.3f}s), 结果数: {len(results)}")
            
            # 缓存结果
            if len(self.prediction_cache) >= self.max_cache_size:
                old_keys = list(self.prediction_cache.keys())[:self.max_cache_size // 2]
                for key in old_keys:
                    del self.prediction_cache[key]
            
            self.prediction_cache[cache_key] = results
            return results
            
        except Exception as e:
            logger.error(f"❌ 通义千问API预测失败: {str(e)}")
            return []
    
    def predict_next_words_sync(self, context: str, num_predictions: int = 8) -> List[Dict[str, Any]]:
        """同步版本的预测方法"""
        try:
            # 简化事件循环处理，避免复杂的线程池
            import nest_asyncio
            
            # 如果存在nest_asyncio，使用它来解决事件循环冲突
            try:
                nest_asyncio.apply()
                loop = asyncio.get_event_loop()
                return loop.run_until_complete(self.predict_next_words(context, num_predictions))
            except ImportError:
                # 如果没有nest_asyncio，使用线程池方案
                import concurrent.futures
                import threading
                
                def run_in_thread():
                    # 在新线程中创建新的事件循环
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        return new_loop.run_until_complete(self.predict_next_words(context, num_predictions))
                    finally:
                        new_loop.close()
                        asyncio.set_event_loop(None)
                
                # 使用线程池执行器在新线程中运行
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(run_in_thread)
                    return future.result(timeout=30)  # 30秒超时
                    
        except Exception as e:
            logger.error(f"❌ 同步API调用失败: {str(e)}")
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
                completions = loop.run_until_complete(self._call_qwen_api(context, max_tokens=200))
                return completions[:max_completions]
            except ImportError:
                # 如果没有nest_asyncio，使用线程池方案
                import concurrent.futures
                
                def run_in_thread():
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        return new_loop.run_until_complete(self._call_qwen_api(context, max_tokens=200))
                    finally:
                        new_loop.close()
                        asyncio.set_event_loop(None)
                
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(run_in_thread)
                    return future.result(timeout=30)[:max_completions]
            
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
_qwen_service = None
_service_lock = threading.Lock()

def get_qwen_api_service(api_key: str = None, api_base: str = None) -> QwenAPIService:
    """
    获取通义千问API服务实例（单例模式）
    
    Args:
        api_key: API密钥
        api_base: API基础URL
    """
    global _qwen_service
    
    with _service_lock:
        if _qwen_service is None:
            logger.info("🏗️ 创建通义千问API服务实例")
            _qwen_service = QwenAPIService(api_key=api_key, api_base=api_base)
        
        return _qwen_service

def test_qwen_api_connection() -> bool:
    """测试通义千问API连接"""
    try:
        service = get_qwen_api_service()
        if not service.is_available():
            logger.error("❌ API密钥未配置")
            return False
        
        # 简单测试
        results = service.predict_next_words_sync("今天天气", 3)
        if results:
            logger.info("✅ 通义千问API连接测试成功")
            return True
        else:
            logger.error("❌ API调用失败")
            return False
            
    except Exception as e:
        logger.error(f"❌ API连接测试失败: {str(e)}")
        return False 