import logging
from typing import List, Dict, Any
from datetime import datetime

# 配置日志
logger = logging.getLogger(__name__)

async def get_fusion_response(responses: List[Dict[str, Any]], history: List[Dict[str, str]] = None) -> str:
    """
    融合多个模型的回答。
    
    Args:
        responses: 包含多个模型回答的列表，每个回答是一个字典，包含modelId和content
        history: 可选的对话历史记录
        
    Returns:
        融合后的回答内容
    """
    try:
        # 准备融合提示词
        fusion_prompt = "请对以下多个AI助手的回答进行总结和融合，给出一个综合的答案：\n\n"
        
        # 添加每个模型的回答
        for idx, response in enumerate(responses, 1):
            fusion_prompt += f"模型 {idx} 的回答：\n{response['content']}\n\n"
        
        # 添加融合要求
        fusion_prompt += "请给出一个融合后的综合回答，要求：\n"
        fusion_prompt += "1. 合并相同的观点\n"
        fusion_prompt += "2. 对不同观点进行对比和分析\n"
        fusion_prompt += "3. 给出最终的建议或结论\n"
        fusion_prompt += "4. 如果发现错误信息，请指出并纠正\n"
        fusion_prompt += "5. 保持回答的逻辑性和连贯性"
        
        # 使用一个模型来进行融合（这里使用 Deepseek 模型）
        from .deepseek_service import get_deepseek_response
        fused_content = await get_deepseek_response(fusion_prompt, history or [])
        
        logger.info("成功融合多个模型的回答")
        return fused_content
        
    except Exception as e:
        error_msg = f"融合回答时发生错误: {str(e)}"
        logger.error(error_msg)
        raise Exception(error_msg) 