#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模型注册系统

自动化管理所有AI模型服务，支持动态添加新模型
"""

import logging
from typing import Dict, List, Optional, Type
from .base_model_service import BaseModelService

logger = logging.getLogger(__name__)

class ModelRegistry:
    """模型注册中心"""
    
    def __init__(self):
        self._models: Dict[str, BaseModelService] = {}
        self._model_configs: Dict[str, Dict] = {}
    
    def register_model(
        self, 
        model_id: str, 
        service_class: Type[BaseModelService], 
        display_name: str,
        description: str = "",
        **kwargs
    ) -> None:
        """
        注册新模型
        
        Args:
            model_id: 模型唯一标识符
            service_class: 模型服务类
            display_name: 显示名称
            description: 模型描述
            **kwargs: 额外配置参数
        """
        try:
            # 创建服务实例
            if kwargs:
                service = service_class(**kwargs)
            else:
                service = service_class()
            
            # 注册到系统
            self._models[model_id] = service
            self._model_configs[model_id] = {
                "id": model_id,
                "name": display_name,
                "description": description,
                "service_class": service_class.__name__,
                "available": self._check_model_availability(service)
            }
            
            logger.info(f"✅ 成功注册模型: {model_id} ({display_name})")
            
        except Exception as e:
            logger.error(f"❌ 注册模型失败: {model_id} - {str(e)}")
    
    def get_model_service(self, model_id: str) -> Optional[BaseModelService]:
        """获取模型服务实例"""
        return self._models.get(model_id)
    
    def get_available_models(self) -> List[Dict]:
        """获取所有可用模型列表"""
        available_models = []
        for model_id, config in self._model_configs.items():
            if config["available"]:
                available_models.append({
                    "id": model_id,
                    "name": config["name"],
                    "description": config["description"]
                })
        return available_models
    
    def get_all_models(self) -> List[Dict]:
        """获取所有模型列表（包括不可用的）"""
        return list(self._model_configs.values())
    
    def is_model_available(self, model_id: str) -> bool:
        """检查模型是否可用"""
        config = self._model_configs.get(model_id)
        return config["available"] if config else False
    
    def refresh_model_availability(self) -> None:
        """刷新所有模型的可用性状态"""
        for model_id, service in self._models.items():
            self._model_configs[model_id]["available"] = self._check_model_availability(service)
    
    def _check_model_availability(self, service: BaseModelService) -> bool:
        """检查单个模型的可用性"""
        try:
            config = service.get_api_config()
            return bool(config.get("api_key") and config.get("api_base"))
        except Exception:
            return False
    
    async def get_model_response(
        self, 
        model_id: str, 
        message: str, 
        conversation_history: List[Dict] = None,
        stream: bool = False
    ):
        """
        统一的模型调用接口
        
        Args:
            model_id: 模型ID
            message: 用户消息
            conversation_history: 对话历史
            stream: 是否使用流式响应
        """
        service = self.get_model_service(model_id)
        if not service:
            raise ValueError(f"未找到模型: {model_id}")
        
        if not self.is_model_available(model_id):
            raise ValueError(f"模型不可用: {model_id}")
        
        if stream:
            async for chunk in service.get_stream_response(message, conversation_history):
                yield chunk
        else:
            # 对于非流式响应，也使用生成器模式以保持一致性
            result = await service.get_non_stream_response(message, conversation_history)
            yield result

# 创建全局注册中心
model_registry = ModelRegistry()

def auto_register_models():
    """自动注册所有模型"""
    try:
        # 注册DeepSeek
        from .deepseek_service import DeepSeekService
        model_registry.register_model(
            "deepseek-chat",
            DeepSeekService,
            "DeepSeek Chat",
            "DeepSeek公司开发的大语言模型，擅长代码生成和逻辑推理"
        )
    except ImportError:
        logger.warning("DeepSeek服务导入失败")
    
    try:
        # 注册SparkX1
        from .sparkx1_service import SparkX1Service
        model_registry.register_model(
            "sparkx1",
            SparkX1Service,
            "讯飞SparkX1",
            "科大讯飞开发的大语言模型，在中文理解方面表现优秀"
        )
    except ImportError:
        logger.warning("SparkX1服务导入失败")
    
    try:
        # 注册通义千问
        from .qwen_service import QwenService
        model_registry.register_model(
            "qwen",
            QwenService,
            "通义千问",
            "阿里云开发的大语言模型，具有强大的中文能力"
        )
    except ImportError:
        logger.warning("Qwen服务导入失败")
    
    try:
        # 注册Moonshot
        from .moonshot_service import MoonshotService
        model_registry.register_model(
            "moonshot",
            MoonshotService,
            "Moonshot AI",
            "月之暗面开发的大语言模型，支持长上下文对话"
        )
    except ImportError:
        logger.warning("Moonshot服务导入失败")
    
    try:
        # 注册GLM (方法一示例)
        from .glm_service import GLMService
        model_registry.register_model(
            "glm-4",
            GLMService,
            "智谱AI GLM-4",
            "智谱AI开发的GLM-4大语言模型，支持中英文对话和代码生成"
        )
    except ImportError:
        logger.warning("GLM服务导入失败")
    
    logger.info(f"🎯 模型注册完成，共注册 {len(model_registry.get_all_models())} 个模型")

# 添加新模型的便捷函数
def add_custom_model(
    model_id: str,
    api_key_env: str,
    api_base_env: str,
    display_name: str,
    model_name: str,
    endpoint_path: str = "/chat/completions",
    description: str = "",
    **request_params
):
    """
    快速添加自定义模型
    
    Args:
        model_id: 模型唯一标识
        api_key_env: API密钥环境变量名
        api_base_env: API基础URL环境变量名
        display_name: 显示名称
        model_name: 模型名称（用于API请求）
        endpoint_path: API端点路径
        description: 描述
        **request_params: 额外的请求参数
    """
    import os
    
    class CustomModelService(BaseModelService):
        def __init__(self):
            super().__init__(display_name)
        
        def get_api_config(self) -> Dict[str, str]:
            return {
                "api_key": os.environ.get(api_key_env, ""),
                "api_base": os.environ.get(api_base_env, "")
            }
        
        def build_request_payload(self, message: str, conversation_history: List[Dict] = None) -> Dict:
            messages = []
            if conversation_history:
                messages.extend(conversation_history)
            messages.append({"role": "user", "content": message})
            
            payload = {
                "model": model_name,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 2000,
                "stream": True
            }
            payload.update(request_params)
            return payload
        
        def get_api_endpoint(self, api_base: str) -> str:
            return f"{api_base}{endpoint_path}"
    
    model_registry.register_model(
        model_id,
        CustomModelService,
        display_name,
        description or f"自定义模型: {display_name}"
    ) 