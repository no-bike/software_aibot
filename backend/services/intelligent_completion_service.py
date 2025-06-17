#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能自动补全服务 - 基于DeepSeek API

专注于使用DeepSeek API提供高质量的中文智能补全功能
DeepSeek在理解用户意图方面表现更优秀
"""

import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

def get_advanced_intelligent_completions(partial_input: str, max_completions: int = 5) -> List[str]:
    """
    获取智能补全建议（使用DeepSeek API）
    
    Args:
        partial_input: 部分输入文本
        max_completions: 最大补全数量
        
    Returns:
        补全建议列表
    """
    try:
        if not partial_input or len(partial_input.strip()) < 1:
            return []
        
        logger.info(f"🤖 使用DeepSeek API进行补全: {partial_input[:30]}...")
        
        from services.deepseek_api_service import get_deepseek_api_service
        deepseek_service = get_deepseek_api_service()
        
        if not deepseek_service.is_available():
            logger.error("❌ DeepSeek API未配置")
            return []
        
        # 直接使用DeepSeek API获取补全
        completions = deepseek_service.get_intelligent_completions(partial_input, max_completions)
        
        if completions:
            logger.info(f"✅ 获得 {len(completions)} 个DeepSeek API补全建议")
            logger.info(completions)
            return completions
        else:
            logger.warning("⚠️ DeepSeek API返回空结果")
            return []
        
    except Exception as e:
        logger.error(f"❌ 智能补全失败: {str(e)}")
        return []

def get_advanced_word_predictions(partial_input: str, top_k: int = 8) -> List[Dict[str, Any]]:
    """
    获取词汇预测（使用DeepSeek API）
    
    Args:
        partial_input: 部分输入文本
        top_k: 返回的预测数量
        
    Returns:
        词汇预测列表，每个包含词汇、概率、模型信息
    """
    try:
        if not partial_input or len(partial_input.strip()) < 1:
            return []
        
        logger.info(f"🧠 使用DeepSeek API进行词汇预测: {partial_input[:30]}...")
        
        from services.deepseek_api_service import get_deepseek_api_service
        deepseek_service = get_deepseek_api_service()
        
        if not deepseek_service.is_available():
            logger.error("❌ DeepSeek API未配置")
            return []
        
        # 使用DeepSeek API获取补全，然后转换为词汇预测格式
        completions = deepseek_service.get_intelligent_completions(partial_input, top_k)
        
        predictions = []
        for i, completion in enumerate(completions):
            if completion and len(completion) > len(partial_input):
                # 提取新增的部分作为预测词汇
                predicted_part = completion[len(partial_input):].strip()
                if predicted_part:
                    predictions.append({
                        "word": predicted_part.split()[0] if predicted_part.split() else predicted_part[:5],
                        "probability": 0.9 - (i * 0.1),  # 简单的概率分配
                        "model": "deepseek_api",
                        "context": partial_input[-30:] if len(partial_input) > 30 else partial_input
                    })
        
        if predictions:
            logger.info(f"✅ 获得 {len(predictions)} 个DeepSeek API词汇预测")
            return predictions
        else:
            logger.warning("⚠️ DeepSeek API返回空结果")
            return []
        
    except Exception as e:
        logger.error(f"❌ 词汇预测失败: {str(e)}")
        return []

# 兼容性函数，保持API接口不变
def get_intelligent_completion_service():
    """兼容性函数 - 返回None，因为不再使用本地服务"""
    logger.warning("⚠️ 本地智能补全服务已废弃，请使用DeepSeek API")
    return None 