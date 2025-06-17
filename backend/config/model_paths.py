#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模型路径配置

统一管理各种AI模型和工具的缓存路径设置
"""

import os
import logging

logger = logging.getLogger(__name__)

class ModelPathConfig:
    """模型路径配置类"""
    
    def __init__(self, base_cache_dir: str = "E:/AI_Models_Cache"):
        """
        初始化模型路径配置
        
        Args:
            base_cache_dir: 基础缓存目录，默认为E盘
        """
        self.base_cache_dir = base_cache_dir
        
        # 各种模型的子目录
        self.transformer_cache_dir = os.path.join(base_cache_dir, "transformers")
        self.jieba_cache_dir = os.path.join(base_cache_dir, "jieba")
        self.llm_blender_cache_dir = os.path.join(base_cache_dir, "llm_blender")
        self.huggingface_cache_dir = os.path.join(base_cache_dir, "huggingface")
        
        # 确保所有目录存在
        self._ensure_directories()
        
        # 设置环境变量
        self._setup_environment_variables()
        
        logger.info(f"🎯 模型缓存基础目录: {self.base_cache_dir}")
    
    def _ensure_directories(self):
        """确保所有必要的目录存在"""
        directories = [
            self.base_cache_dir,
            self.transformer_cache_dir,
            self.jieba_cache_dir,
            self.llm_blender_cache_dir,
            self.huggingface_cache_dir
        ]
        
        for directory in directories:
            try:
                os.makedirs(directory, exist_ok=True)
                logger.debug(f"📁 确保目录存在: {directory}")
            except Exception as e:
                logger.error(f"❌ 无法创建目录 {directory}: {e}")
    
    def _setup_environment_variables(self):
        """设置环境变量"""
        env_vars = {
            "TRANSFORMERS_CACHE": self.transformer_cache_dir,
            "HF_HOME": self.huggingface_cache_dir,
            "HF_CACHE_HOME": self.huggingface_cache_dir,
            "TORCH_HOME": os.path.join(self.base_cache_dir, "torch"),
        }
        
        for var_name, var_value in env_vars.items():
            os.environ[var_name] = var_value
            logger.debug(f"🔧 设置环境变量: {var_name}={var_value}")
    
    def get_jieba_cache_file(self) -> str:
        """获取jieba缓存文件路径"""
        return os.path.join(self.jieba_cache_dir, "jieba.cache")
    
    def get_model_cache_dir(self, model_type: str) -> str:
        """
        获取特定模型类型的缓存目录
        
        Args:
            model_type: 模型类型 ('transformer', 'jieba', 'llm_blender', 等)
        
        Returns:
            对应的缓存目录路径
        """
        cache_dirs = {
            'transformer': self.transformer_cache_dir,
            'jieba': self.jieba_cache_dir,
            'llm_blender': self.llm_blender_cache_dir,
            'huggingface': self.huggingface_cache_dir
        }
        
        return cache_dirs.get(model_type, self.base_cache_dir)
    
    def clear_cache(self, model_type: str = None):
        """
        清理指定类型的缓存（谨慎使用）
        
        Args:
            model_type: 要清理的模型类型，None表示清理所有
        """
        import shutil
        
        if model_type:
            cache_dir = self.get_model_cache_dir(model_type)
            if os.path.exists(cache_dir):
                try:
                    shutil.rmtree(cache_dir)
                    os.makedirs(cache_dir, exist_ok=True)
                    logger.info(f"🧹 已清理 {model_type} 缓存: {cache_dir}")
                except Exception as e:
                    logger.error(f"❌ 清理缓存失败: {e}")
        else:
            logger.warning("⚠️ 请指定要清理的模型类型，避免意外清理所有缓存")
    
    def get_cache_info(self) -> dict:
        """获取缓存目录信息"""
        def get_dir_size(path):
            """计算目录大小"""
            total_size = 0
            try:
                for dirpath, dirnames, filenames in os.walk(path):
                    for filename in filenames:
                        filepath = os.path.join(dirpath, filename)
                        if os.path.exists(filepath):
                            total_size += os.path.getsize(filepath)
            except Exception as e:
                logger.debug(f"计算目录大小失败 {path}: {e}")
            return total_size
        
        cache_info = {
            'base_dir': self.base_cache_dir,
            'directories': {}
        }
        
        for name, path in {
            'transformer': self.transformer_cache_dir,
            'jieba': self.jieba_cache_dir,
            'llm_blender': self.llm_blender_cache_dir,
            'huggingface': self.huggingface_cache_dir
        }.items():
            cache_info['directories'][name] = {
                'path': path,
                'exists': os.path.exists(path),
                'size_bytes': get_dir_size(path) if os.path.exists(path) else 0
            }
        
        return cache_info

# 全局配置实例
_model_path_config = None

def get_model_path_config(base_cache_dir: str = "E:/AI_Models_Cache") -> ModelPathConfig:
    """获取全局模型路径配置实例"""
    global _model_path_config
    if _model_path_config is None:
        _model_path_config = ModelPathConfig(base_cache_dir)
        logger.info("✅ 模型路径配置初始化完成")
    return _model_path_config

def setup_jieba_cache():
    """设置jieba缓存路径"""
    import jieba
    config = get_model_path_config()
    jieba_cache_file = config.get_jieba_cache_file()
    jieba.dt.cache_file = jieba_cache_file
    logger.info(f"🈳 Jieba缓存文件: {jieba_cache_file}")

# 在模块导入时自动设置
if __name__ != "__main__":
    # 自动初始化配置（除非是直接运行此脚本）
    get_model_path_config() 