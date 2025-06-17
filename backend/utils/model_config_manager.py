#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模型配置管理工具

简化新模型的配置和添加过程
"""

import os
import json
import logging
from typing import Dict, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class ModelConfigManager:
    """模型配置管理器"""
    
    def __init__(self, config_file: str = "model_configs.json"):
        self.config_file = Path(__file__).parent.parent / config_file
        self.configs = self._load_configs()
    
    def _load_configs(self) -> Dict:
        """加载配置文件"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                return {"models": {}}
        except Exception as e:
            logger.error(f"加载配置文件失败: {str(e)}")
            return {"models": {}}
    
    def _save_configs(self) -> bool:
        """保存配置文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.configs, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"保存配置文件失败: {str(e)}")
            return False
    
    def add_model_config(
        self,
        model_id: str,
        display_name: str,
        api_key_env: str,
        api_base_env: str,
        model_name: str,
        endpoint_path: str = "/chat/completions",
        description: str = "",
        **kwargs
    ) -> bool:
        """
        添加模型配置
        
        Args:
            model_id: 模型唯一标识
            display_name: 显示名称
            api_key_env: API密钥环境变量名
            api_base_env: API基础URL环境变量名
            model_name: 模型名称
            endpoint_path: API端点路径
            description: 描述
            **kwargs: 其他配置参数
        """
        try:
            self.configs["models"][model_id] = {
                "display_name": display_name,
                "api_key_env": api_key_env,
                "api_base_env": api_base_env,
                "model_name": model_name,
                "endpoint_path": endpoint_path,
                "description": description,
                "custom_params": kwargs,
                "enabled": True
            }
            
            return self._save_configs()
        except Exception as e:
            logger.error(f"添加模型配置失败: {str(e)}")
            return False
    
    def get_model_config(self, model_id: str) -> Optional[Dict]:
        """获取模型配置"""
        return self.configs["models"].get(model_id)
    
    def get_all_configs(self) -> Dict[str, Dict]:
        """获取所有模型配置"""
        return self.configs["models"]
    
    def remove_model_config(self, model_id: str) -> bool:
        """删除模型配置"""
        try:
            if model_id in self.configs["models"]:
                del self.configs["models"][model_id]
                return self._save_configs()
            return True
        except Exception as e:
            logger.error(f"删除模型配置失败: {str(e)}")
            return False
    
    def update_model_config(self, model_id: str, **updates) -> bool:
        """更新模型配置"""
        try:
            if model_id in self.configs["models"]:
                self.configs["models"][model_id].update(updates)
                return self._save_configs()
            return False
        except Exception as e:
            logger.error(f"更新模型配置失败: {str(e)}")
            return False
    
    def enable_model(self, model_id: str) -> bool:
        """启用模型"""
        return self.update_model_config(model_id, enabled=True)
    
    def disable_model(self, model_id: str) -> bool:
        """禁用模型"""
        return self.update_model_config(model_id, enabled=False)
    
    def get_enabled_models(self) -> List[str]:
        """获取已启用的模型列表"""
        enabled_models = []
        for model_id, config in self.configs["models"].items():
            if config.get("enabled", True):
                enabled_models.append(model_id)
        return enabled_models
    
    def validate_config(self, model_id: str) -> Dict[str, bool]:
        """验证模型配置"""
        config = self.get_model_config(model_id)
        if not config:
            return {"valid": False, "error": "配置不存在"}
        
        validation_result = {
            "valid": True,
            "has_api_key": False,
            "has_api_base": False,
            "env_vars_set": True
        }
        
        # 检查环境变量
        api_key_env = config.get("api_key_env")
        api_base_env = config.get("api_base_env")
        
        if api_key_env:
            validation_result["has_api_key"] = bool(os.environ.get(api_key_env))
        
        if api_base_env:
            validation_result["has_api_base"] = bool(os.environ.get(api_base_env))
        
        validation_result["env_vars_set"] = (
            validation_result["has_api_key"] and 
            validation_result["has_api_base"]
        )
        
        validation_result["valid"] = validation_result["env_vars_set"]
        
        return validation_result
    
    def generate_env_template(self) -> str:
        """生成环境变量模板"""
        template_lines = ["# AI模型配置环境变量模板", ""]
        
        for model_id, config in self.configs["models"].items():
            template_lines.append(f"# {config['display_name']}")
            if config.get("description"):
                template_lines.append(f"# {config['description']}")
            
            api_key_env = config.get("api_key_env")
            api_base_env = config.get("api_base_env")
            
            if api_key_env:
                template_lines.append(f"{api_key_env}=your_api_key_here")
            if api_base_env:
                template_lines.append(f"{api_base_env}=your_api_base_here")
            
            template_lines.append("")
        
        return "\n".join(template_lines)
    
    def export_config(self, output_file: str) -> bool:
        """导出配置到文件"""
        try:
            output_path = Path(output_file)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(self.configs, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"导出配置失败: {str(e)}")
            return False
    
    def import_config(self, input_file: str) -> bool:
        """从文件导入配置"""
        try:
            input_path = Path(input_file)
            if not input_path.exists():
                return False
            
            with open(input_path, 'r', encoding='utf-8') as f:
                imported_configs = json.load(f)
            
            # 合并配置
            if "models" in imported_configs:
                self.configs["models"].update(imported_configs["models"])
                return self._save_configs()
            
            return False
        except Exception as e:
            logger.error(f"导入配置失败: {str(e)}")
            return False

# 创建全局配置管理器实例
config_manager = ModelConfigManager()

# 预设的热门模型配置模板
POPULAR_MODEL_TEMPLATES = {
    "gpt-4": {
        "display_name": "GPT-4",
        "api_key_env": "OPENAI_API_KEY",
        "api_base_env": "OPENAI_API_BASE",
        "model_name": "gpt-4",
        "endpoint_path": "/v1/chat/completions",
        "description": "OpenAI的GPT-4模型，具有强大的推理和创作能力"
    },
    "claude-3": {
        "display_name": "Claude 3",
        "api_key_env": "CLAUDE_API_KEY",
        "api_base_env": "CLAUDE_API_BASE",
        "model_name": "claude-3-sonnet-20240229",
        "endpoint_path": "/v1/messages",
        "description": "Anthropic的Claude 3模型，注重安全性和有用性"
    },
    "gemini-pro": {
        "display_name": "Gemini Pro",
        "api_key_env": "GEMINI_API_KEY",
        "api_base_env": "GEMINI_API_BASE",
        "model_name": "gemini-pro",
        "endpoint_path": "/v1/chat/completions",
        "description": "Google的Gemini Pro模型，多模态能力强"
    },
    "llama2": {
        "display_name": "Llama 2",
        "api_key_env": "LLAMA2_API_KEY",
        "api_base_env": "LLAMA2_API_BASE",
        "model_name": "llama2-70b-chat",
        "endpoint_path": "/v1/chat/completions",
        "description": "Meta的Llama 2模型，开源且性能优秀"
    }
}

def quick_add_popular_model(model_key: str) -> bool:
    """快速添加热门模型"""
    if model_key not in POPULAR_MODEL_TEMPLATES:
        logger.error(f"不支持的热门模型: {model_key}")
        return False
    
    template = POPULAR_MODEL_TEMPLATES[model_key]
    return config_manager.add_model_config(
        model_id=model_key,
        **template
    ) 