#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基础模型服务抽象类

统一所有AI模型的流式处理接口和通用逻辑
"""

import os
import httpx
import logging
import asyncio
import json
from abc import ABC, abstractmethod
from fastapi import HTTPException
from typing import List, Dict, Optional, AsyncGenerator

logger = logging.getLogger(__name__)

class BaseModelService(ABC):
    """AI模型服务的抽象基类"""
    
    def __init__(self, model_name: str):
        self.model_name = model_name
        self.max_retries = 2
        self.buffer_size = 512
        self.connect_timeout = 10.0
        self.stream_timeout = 20.0
    
    @abstractmethod
    def get_api_config(self) -> Dict[str, str]:
        """
        获取API配置信息
        
        Returns:
            包含api_key, api_base等配置的字典
        """
        pass
    
    @abstractmethod
    def build_request_payload(self, message: str, conversation_history: List[Dict] = None) -> Dict:
        """
        构建请求载荷
        
        Args:
            message: 用户消息
            conversation_history: 对话历史
            
        Returns:
            请求载荷字典
        """
        pass
    
    @abstractmethod
    def get_api_endpoint(self, api_base: str) -> str:
        """
        获取API端点URL
        
        Args:
            api_base: API基础URL
            
        Returns:
            完整的API端点URL
        """
        pass
    
    def build_headers(self, api_key: str) -> Dict[str, str]:
        """
        构建请求头（可以被子类重写）
        
        Args:
            api_key: API密钥
            
        Returns:
            请求头字典
        """
        return {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    def process_stream_chunk(self, chunk: str) -> Optional[str]:
        """
        处理流式响应块（可以被子类重写）
        
        Args:
            chunk: 原始响应块
            
        Returns:
            处理后的SSE格式数据，如果无需输出则返回None
        """
        # 默认实现：假设chunk已经是SSE格式
        if chunk.strip():
            if chunk.startswith('data: '):
                return chunk + '\n'
            else:
                # 尝试解析为JSON并转换为SSE格式
                try:
                    data = json.loads(chunk)
                    return f"data: {json.dumps(data, ensure_ascii=False)}\n"
                except json.JSONDecodeError:
                    # 如果不是JSON，可能是原始文本，包装成SSE格式
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
    
    def validate_config(self, config: Dict[str, str]) -> None:
        """
        验证API配置
        
        Args:
            config: API配置字典
            
        Raises:
            HTTPException: 配置无效时抛出异常
        """
        if not config.get("api_key"):
            raise HTTPException(
                status_code=500, 
                detail=f"未配置{self.model_name} API密钥"
            )
        if not config.get("api_base"):
            raise HTTPException(
                status_code=500, 
                detail=f"未配置{self.model_name} API基础URL"
            )
    
    async def get_stream_response(
        self, 
        message: str, 
        conversation_history: List[Dict] = None
    ) -> AsyncGenerator[str, None]:
        """
        统一的流式响应处理函数
        
        Args:
            message: 用户消息
            conversation_history: 对话历史
            
        Yields:
            SSE格式的流式响应数据
        """
        async with httpx.AsyncClient() as client:
            # 获取配置
            config = self.get_api_config()
            self.validate_config(config)
            
            # 构建请求
            headers = self.build_headers(config["api_key"])
            payload = self.build_request_payload(message, conversation_history)
            endpoint = self.get_api_endpoint(config["api_base"])
            
            buffer = ""
            retry_count = 0
            
            while retry_count <= self.max_retries:
                try:
                    if retry_count == 0:
                        logger.info(f"发送流式请求到{self.model_name} API (尝试 {retry_count + 1}/{self.max_retries + 1})")
                    
                    async with client.stream(
                        "POST",
                        endpoint,
                        headers=headers,
                        json=payload,
                        timeout=httpx.Timeout(self.connect_timeout, read=self.stream_timeout)
                    ) as response:
                        
                        # 检查响应状态
                        if response.status_code != 200:
                            error_text = await response.aread()
                            logger.error(f"{self.model_name} API错误响应: {response.status_code}")
                            
                            # 服务器错误时重试
                            if response.status_code >= 500 and retry_count < self.max_retries:
                                retry_count += 1
                                await asyncio.sleep(1 * retry_count)  # 指数退避
                                continue
                                
                            raise HTTPException(
                                status_code=response.status_code,
                                detail=f"{self.model_name} API错误: {error_text}"
                            )
                        
                        # 处理流式响应
                        async for chunk in response.aiter_text():
                            buffer += chunk
                            
                            # 当缓冲区足够大或包含完整行时处理
                            if len(buffer) >= self.buffer_size or '\n' in buffer:
                                lines = buffer.split('\n')
                                for line in lines[:-1]:  # 处理完整行
                                    processed = self.process_stream_chunk(line)
                                    if processed:
                                        yield processed
                                buffer = lines[-1]  # 保留不完整行
                        
                        # 处理缓冲区剩余内容
                        if buffer.strip():
                            processed = self.process_stream_chunk(buffer)
                            if processed:
                                yield processed
                            buffer = ""
                        
                        # 发送结束标记
                        yield "data: [DONE]\n"
                        return  # 成功完成
                        
                except (httpx.ReadTimeout, httpx.ConnectTimeout) as e:
                    if retry_count < self.max_retries:
                        retry_count += 1
                        await asyncio.sleep(1 * retry_count)
                        continue
                    logger.error(f"{self.model_name} API连接超时: {str(e)}")
                    raise HTTPException(
                        status_code=504,
                        detail=f"{self.model_name} API连接超时: {str(e)}"
                    )
                except Exception as e:
                    logger.error(f"处理{self.model_name} API流式响应时发生错误: {str(e)}")
                    raise HTTPException(
                        status_code=500,
                        detail=f"调用{self.model_name} API时发生错误: {str(e)}"
                    )
            
            raise HTTPException(
                status_code=503,
                detail=f"{self.model_name} API达到最大重试次数，请稍后再试"
            )
    
    async def get_non_stream_response(
        self, 
        message: str, 
        conversation_history: List[Dict] = None
    ) -> str:
        """
        统一的非流式响应处理函数
        
        Args:
            message: 用户消息
            conversation_history: 对话历史
            
        Returns:
            完整的响应内容
        """
        async with httpx.AsyncClient() as client:
            # 获取配置
            config = self.get_api_config()
            self.validate_config(config)
            
            # 构建请求（非流式）
            headers = self.build_headers(config["api_key"])
            payload = self.build_request_payload(message, conversation_history)
            # 确保非流式模式
            payload["stream"] = False
            endpoint = self.get_api_endpoint(config["api_base"])
            
            try:
                logger.info(f"发送请求到{self.model_name} API: {endpoint}")
                
                response = await client.post(
                    endpoint,
                    headers=headers,
                    json=payload,
                    timeout=30.0
                )
                
                logger.info(f"{self.model_name} API响应状态码: {response.status_code}")
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"{self.model_name} API响应: {result}")
                    
                    if "choices" in result and len(result["choices"]) > 0:
                        return result["choices"][0]["message"]["content"]
                    else:
                        raise HTTPException(
                            status_code=500, 
                            detail=f"{self.model_name} API返回的响应格式不正确"
                        )
                else:
                    logger.error(f"{self.model_name} API错误响应: {response.text}")
                    raise HTTPException(
                        status_code=response.status_code, 
                        detail=f"{self.model_name} API错误: {response.text}"
                    )
                    
            except Exception as e:
                logger.error(f"处理{self.model_name} API响应时发生错误: {str(e)}")
                raise HTTPException(
                    status_code=500, 
                    detail=f"调用{self.model_name} API时发生错误: {str(e)}"
                ) 