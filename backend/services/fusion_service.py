import logging
from typing import List, Dict, Any
from datetime import datetime
# 通过AI实现的融合
# 配置日志
logger = logging.getLogger(__name__)

async def get_fusion_response(responses: List[Dict[str, Any]], history: List[Dict[str, str]] = None) -> str:
    """
    融合多个模型的回答（向后兼容版本）
    
    Args:
        responses: 包含多个模型回答的列表，每个回答是一个字典，包含modelId和content
        history: 可选的对话历史记录
        
    Returns:
        融合后的回答内容
    """
    try:
        # 尝试使用 LLM-Blender 高级融合
        try:
            from .llm_blender_service import get_advanced_fusion_response
            
            # 构建查询上下文
            query = "请根据多个AI助手的回答，提供最优的综合答案。"
            if history:
                # 从历史记录中提取最新的用户问题
                user_messages = [msg for msg in history if msg.get("role") == "user"]
                if user_messages:
                    query = user_messages[-1]["content"]
            
            # 使用高级融合服务
            result = await get_advanced_fusion_response(
                query=query,
                responses=responses,
                instruction="请综合多个AI回答，提供准确、完整的解答",
                top_k=3,
                fusion_method="rank_and_fuse"
            )
            
            logger.info("✅ 使用 LLM-Blender 高级融合成功")
            return result["fused_content"]
            
        except Exception as e:
            logger.warning(f"⚠️ LLM-Blender 融合失败，降级到传统融合: {str(e)}")
            # 降级到传统融合方法
            return await _traditional_fusion(responses, history)
        
    except Exception as e:
        error_msg = f"融合回答时发生错误: {str(e)}"
        logger.error(error_msg)
        raise Exception(error_msg)

async def _traditional_fusion(responses: List[Dict[str, Any]], history: List[Dict[str, str]] = None) -> str:
    """
    传统的AI融合方法（原有逻辑）
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
        
        logger.info("成功使用传统方法融合多个模型的回答")
        return fused_content
        
    except Exception as e:
        error_msg = f"传统融合方法失败: {str(e)}"
        logger.error(error_msg)
        # 最后的备选方案：简单拼接
        return _simple_concatenation(responses)

def _simple_concatenation(responses: List[Dict[str, Any]]) -> str:
    """最简单的备选融合方案：直接拼接回答"""
    if not responses:
        return "抱歉，没有可用的回答。"
    
    if len(responses) == 1:
        return responses[0]["content"]
    
    fusion_parts = [f"综合 {len(responses)} 个AI助手的回答：\n"]
    
    for idx, response in enumerate(responses, 1):
        fusion_parts.append(f"**回答 {idx}** ({response.get('modelId', '未知模型')}):")
        fusion_parts.append(response["content"])
        fusion_parts.append("")  # 空行分隔
    
    return "\n".join(fusion_parts)

# 新增：专门的高级融合接口
async def get_advanced_fusion_response_direct(
    query: str,
    responses: List[Dict[str, Any]], 
    fusion_method: str = "rank_and_fuse",
    top_k: int = 3
) -> Dict[str, Any]:
    """
    直接调用 LLM-Blender 高级融合的接口
    
    Args:
        query: 用户的原始问题
        responses: AI模型回答列表
        fusion_method: 融合方法 ("rank_only", "fuse_only", "rank_and_fuse")
        top_k: 使用的top-k回答数量
        
    Returns:
        详细的融合结果，包含排序信息
    """
    try:
        from .llm_blender_service import get_advanced_fusion_response
        
        result = await get_advanced_fusion_response(
            query=query,
            responses=responses,
            instruction="请基于提供的信息给出准确、全面的回答",
            top_k=top_k,
            fusion_method=fusion_method
        )
        
        logger.info(f"✅ 高级融合完成，方法: {result.get('fusion_method', '未知')}")
        return result
        
    except Exception as e:
        logger.error(f"❌ 高级融合失败: {str(e)}")
        # 返回错误信息和降级结果
        fallback_content = responses[0]["content"] if responses else "融合服务不可用"
        return {
            "fused_content": fallback_content,
            "ranked_responses": responses,
            "fusion_method": "fallback",
            "error": str(e),
            "processing_time": 0
        } 