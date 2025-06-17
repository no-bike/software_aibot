#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM-Blender 融合服务

集成 LLM-Blender 的高级融合功能到 software_aibot 项目中
提供基于质量排序和生成融合的智能回答合并服务
"""

import os
import time
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
import sys
import asyncio
import json
import aiohttp

# 过滤常见的非关键警告
import warnings
warnings.filterwarnings("ignore", category=RuntimeWarning, module="dataclasses_json")
warnings.filterwarnings("ignore", category=UserWarning, module="transformers.convert_slow_tokenizer")

# 添加本地llm_blender路径
# LLM-Blender现在在services目录下
current_dir = Path(__file__).parent  # services目录
llm_blender_path = current_dir / "LLM-Blender"
print(f"🔍 查找LLM-Blender路径: {llm_blender_path}")
print(f"🔍 路径是否存在: {llm_blender_path.exists()}")
if llm_blender_path.exists():
    sys.path.insert(0, str(llm_blender_path))
    print(f"✅ 已添加路径到sys.path: {llm_blender_path}")
else:
    print(f"❌ 未找到LLM-Blender路径，当前文件位置: {Path(__file__)}")
    print(f"❌ 当前services目录: {current_dir}")
    print(f"❌ 寻找的路径: {llm_blender_path}")
    
    # 尝试列出services目录下的所有文件和文件夹
    try:
        contents = list(current_dir.iterdir())
        print(f"📂 services目录内容: {[item.name for item in contents]}")
    except Exception as e:
        print(f"❌ 无法列出services目录内容: {e}")

# 配置环境变量，避免CUDA和符号链接问题
os.environ["CUDA_VISIBLE_DEVICES"] = ""

import llm_blender
from llm_blender.blender.blender_utils import get_topk_candidates_from_ranks

# 配置日志
logger = logging.getLogger(__name__)

# DeepSeek API 配置
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")  # 从环境变量获取API密钥

class LLMBlenderService:
    """LLM-Blender 融合服务类"""
    
    def __init__(self):
        """初始化 LLM-Blender 服务"""
        self.blender = None
        self.is_initialized = False
        self.ranker_loaded = False
        self.fuser_loaded = False
        
    async def initialize(self):
        """异步初始化 LLM-Blender"""
        if self.is_initialized:
            logger.debug("♻️ LLM-Blender 服务已初始化，跳过重复初始化")
            return
            
        try:
            logger.info("🚀 开始初始化 LLM-Blender 服务...")
            
            # 初始化 Blender
            if self.blender is None:
                logger.info("📦 创建 Blender 实例...")
                self.blender = llm_blender.Blender()
            
            # 加载 Ranker (PairRM) - 只加载一次
            if not self.ranker_loaded:
                logger.info("📥 加载 PairRM Ranker...")
                start_time = time.time()
                self.blender.loadranker(
                    "llm-blender/PairRM",
                    device="cpu"
                )
                ranker_time = time.time() - start_time
                self.ranker_loaded = True
                logger.info(f"✅ Ranker 加载成功 ({ranker_time:.2f}s)")
            else:
                logger.debug("♻️ Ranker 已加载，跳过重复加载")
            
            # 尝试加载 Fuser (GenFuser) - 只加载一次
            if not self.fuser_loaded:
                try:
                    logger.info("📥 加载 GenFuser...")
                    start_time = time.time()
                    self.blender.loadfuser(
                        "llm-blender/gen_fuser_3b",
                        device="cpu",
                        local_files_only=True  # 避免符号链接警告
                    )
                    fuser_time = time.time() - start_time
                    self.fuser_loaded = True
                    logger.info(f"✅ GenFuser 加载成功 ({fuser_time:.2f}s)")
                    logger.info("📝 GenFuser 已配置支持更长输入 (运行时将使用 max_length=2048, candidate_max_length=512)")
                except Exception as e:
                    logger.warning(f"⚠️ GenFuser 加载失败，将使用仅排序模式: {str(e)}")
                    self.fuser_loaded = False
            else:
                logger.debug("♻️ GenFuser 已加载，跳过重复加载")
            
            self.is_initialized = True
            logger.info("🎉 LLM-Blender 服务初始化完成！")
            logger.info(f"📊 服务状态: Ranker={'已加载' if self.ranker_loaded else '未加载'}, Fuser={'已加载' if self.fuser_loaded else '未加载'}")
            
        except Exception as e:
            logger.error(f"❌ LLM-Blender 初始化失败: {str(e)}")
            self.is_initialized = False
            raise e
    
    def contains_chinese(self, text: str) -> bool:
        """检测文本是否包含中文字符"""
        return any('\u4e00' <= char <= '\u9fff' for char in text)
    
    async def call_deepseek_api(
        self, 
        query: str, 
        top_responses: List[Dict[str, Any]], 
        instruction: Optional[str] = None
    ) -> str:
        """
        调用 DeepSeek API 进行中文回答融合
        
        Args:
            query: 用户原始问题
            top_responses: 排序后的前几个回答
            instruction: 可选指令
            
        Returns:
            DeepSeek 融合后的回答
        """
        try:
            # 构建融合提示词
            fusion_prompt = self._build_fusion_prompt(query, top_responses, instruction)
            
            # 准备API请求
            headers = {
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "deepseek-chat",
                "messages": [
                    {
                        "role": "system",
                        "content": "你是一个专业的AI回答融合专家。你的任务是将多个AI模型的回答进行智能融合，生成一个更准确、更全面、更有用的综合答案。请保持客观、准确，并尽可能结合各个回答的优点。"
                    },
                    {
                        "role": "user", 
                        "content": fusion_prompt
                    }
                ],
                "temperature": 0.3,  # 较低的温度确保稳定输出
                "max_tokens": 2000,
                "stream": False
            }
            
            logger.info("🤖 调用 DeepSeek API 进行中文融合...")
            start_time = time.time()
            
            # 发送异步请求
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    DEEPSEEK_API_URL, 
                    headers=headers, 
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        fused_content = result["choices"][0]["message"]["content"]
                        
                        api_time = time.time() - start_time
                        logger.info(f"✅ DeepSeek API 融合完成 ({api_time:.2f}s)")
                        logger.info(f"📝 融合结果长度: {len(fused_content)} 字符")
                        
                        return fused_content
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ DeepSeek API 错误 {response.status}: {error_text}")
                        raise Exception(f"DeepSeek API 调用失败: {response.status}")
                        
        except Exception as e:
            logger.error(f"❌ DeepSeek API 调用失败: {str(e)}")
            # 如果API调用失败，降级到简单融合
            logger.info("⬇️ 降级到简单文本融合")
            return await self._simple_fusion_from_responses(query, top_responses)
    
    def _build_fusion_prompt(
        self, 
        query: str, 
        top_responses: List[Dict[str, Any]], 
        instruction: Optional[str] = None
    ) -> str:
        """构建发送给 DeepSeek 的融合提示词"""
        
        prompt_parts = []
        
        # 添加指令（如果有）
        if instruction:
            prompt_parts.append(f"**任务指令**: {instruction}\n")
        
        # 添加用户问题
        prompt_parts.append(f"**用户问题**: {query}\n")
        
        # 添加各个AI模型的回答
        prompt_parts.append("**多个AI模型的回答**:")
        
        for i, resp in enumerate(top_responses, 1):
            model_id = resp.get('modelId', f'模型{i}')
            content = resp.get('content', '')
            quality_score = resp.get('quality_score', 0)
            
            prompt_parts.append(f"\n**回答 {i} (来源: {model_id}, 质量分数: {quality_score})**:")
            prompt_parts.append(content)
        
        # 添加融合要求
        prompt_parts.append("""

**融合要求**:
1. 请仔细分析上述各个AI模型的回答
2. 识别每个回答的优点和不足
3. 将这些回答的优势部分进行智能融合
4. 生成一个更准确、更全面、更有条理的综合答案
5. 确保答案逻辑清晰，信息完整
6. 保持中文表达的自然和流畅
7. 如果发现回答之间有冲突，请给出平衡的观点或说明不同角度

**请直接给出融合后的最终答案，不需要额外的说明或分析过程**:""")
        
        return "\n".join(prompt_parts)
    
    async def rank_responses(
        self, 
        query: str, 
        responses: List[Dict[str, Any]], 
        instruction: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        对多个AI回答进行质量排序
        
        Args:
            query: 用户的原始问题
            responses: AI模型的回答列表 [{"modelId": "xxx", "content": "xxx"}, ...]
            instruction: 可选的指令前缀
            
        Returns:
            按质量排序后的回答列表，最优回答在前
        """
        # 懒加载机制：如果Ranker未加载，尝试重新加载
        if not await self._lazy_load_ranker():
            logger.error("❌ 无法加载Ranker，返回原始回答顺序")
            return responses
        
        if len(responses) <= 1:
            return responses
            
        try:
            logger.debug(f"🔍 开始对 {len(responses)} 个回答进行质量排序...")
            
            # 准备输入数据
            inputs = [query]
            candidates = [[resp["content"] for resp in responses]]
            instructions = [instruction] if instruction else None
            
            # 执行排序
            start_time = time.time()
            ranks = self.blender.rank(
                inputs=inputs,
                candidates=candidates,
                instructions=instructions,
                return_scores=False,
                batch_size=1
            )[0]  # 取第一个（也是唯一一个）问题的排序结果
            
            rank_time = time.time() - start_time
            logger.debug(f"✅ 排序完成 ({rank_time:.2f}s)")
            
            # 根据排序结果重新排列回答
            # 将numpy数组转换为列表以便使用index方法
            ranks_list = ranks.tolist() if hasattr(ranks, 'tolist') else list(ranks)
            ranked_responses = []
            for rank in range(1, len(responses) + 1):
                idx = ranks_list.index(rank)  # 找到排名为rank的回答索引
                response = responses[idx].copy()
                response["rank"] = rank
                response["quality_score"] = len(responses) - rank + 1  # 质量分数，越高越好
                ranked_responses.append(response)
            
            # 简化日志输出
            model_ranks = [f"{resp['modelId']}(排名{resp['rank']})" for resp in ranked_responses]
            logger.info(f"📊 排序结果: {model_ranks}")
            return ranked_responses
            
        except Exception as e:
            logger.error(f"❌ 排序失败: {str(e)}")
            # 排序失败时返回原始列表，添加默认排名
            for i, resp in enumerate(responses):
                resp["rank"] = i + 1
                resp["quality_score"] = len(responses) - i
            return responses
    
    async def fuse_responses(
        self,
        query: str,
        responses: List[Dict[str, Any]],
        instruction: Optional[str] = None,
        top_k: int = 3
    ) -> str:
        """
        融合多个AI回答生成最优答案
        
        智能策略:
        - 英文输入: 使用 GenFuser 进行高质量融合
        - 中文输入: 使用 DeepSeek API 进行专业中文融合
        
        Args:
            query: 用户的原始问题
            responses: AI模型的回答列表（应该已经排序）
            instruction: 可选的指令前缀
            top_k: 使用前k个最优回答进行融合
            
        Returns:
            融合生成的最优答案
        """
        if len(responses) <= 1:
            return responses[0]["content"] if responses else "抱歉，没有可用的回答。"
        
        # 选择前top_k个回答
        top_responses = responses[:top_k]
        
        # 检测语言并选择融合策略
        has_chinese = (self.contains_chinese(query) or 
                      any(self.contains_chinese(resp.get("content", "")) for resp in top_responses))
        
        if has_chinese:
            logger.info("🈳 检测到中文输入，使用 DeepSeek API 进行专业中文融合")
            return await self.call_deepseek_api(query, top_responses, instruction)
        else:
            logger.info("🔤 检测到英文输入，使用 GenFuser 进行高质量融合")
            return await self._genfuser_fusion(query, top_responses, instruction, top_k)
    
    async def _genfuser_fusion(
        self,
        query: str,
        top_responses: List[Dict[str, Any]],
        instruction: Optional[str] = None,
        top_k: int = 3
    ) -> str:
        """使用 GenFuser 进行英文融合（原有逻辑）"""
        
        # 懒加载机制：如果GenFuser未加载，尝试重新加载
        if not await self._lazy_load_fuser():
            logger.warning("⚠️ GenFuser加载失败，降级到简单融合")
            return await self._simple_fusion_from_responses(query, top_responses)
            
        try:
            logger.info(f"⚡ 开始 GenFuser 融合前 {len(top_responses)} 个最优回答...")
            
            # 准备输入数据
            inputs = [query]
            instructions = [instruction] if instruction else None
            candidates = [[resp["content"] for resp in top_responses]]
            
            # 临时修改fuser配置以支持更长的输入序列
            original_max_length = self.blender.fuser_config.max_length
            original_candidate_maxlength = self.blender.fuser_config.candidate_maxlength
            
            # 设置更大的输入处理长度限制
            self.blender.fuser_config.max_length = 2048  # 输入序列的最大长度
            self.blender.fuser_config.candidate_maxlength = 1024  # 单个候选回答的最大长度
            
            logger.info(f"📝 临时调整GenFuser配置: max_length={self.blender.fuser_config.max_length}, candidate_maxlength={self.blender.fuser_config.candidate_maxlength}")
            
            # 执行融合生成
            start_time = time.time()
            fused_results = self.blender.fuse(
                inputs=inputs,
                candidates=candidates,
                instructions=instructions,
                batch_size=1,
                candidate_max_length=1024
            )
            
            # 恢复原始配置
            self.blender.fuser_config.max_length = original_max_length
            self.blender.fuser_config.candidate_maxlength = original_candidate_maxlength
            
            fuse_time = time.time() - start_time
            fused_content = fused_results[0] if fused_results else "融合生成失败"
            
            logger.info(f"✅ GenFuser 融合完成 ({fuse_time:.2f}s)")
            logger.info(f"📝 融合结果长度: {len(fused_content)} 字符")
            
            # 检查生成内容质量
            if "?" in fused_content and fused_content.count("?") > len(fused_content) * 0.3:
                logger.warning("⚠️ 检测到大量问号，可能是解码问题，降级到简单融合")
                return await self._simple_fusion_from_responses(query, top_responses)
            
            return fused_content
            
        except Exception as e:
            logger.error(f"❌ GenFuser 融合失败: {str(e)}")
            return await self._simple_fusion_from_responses(query, top_responses)
    
    async def rank_and_fuse(
        self,
        query: str,
        responses: List[Dict[str, Any]],
        instruction: Optional[str] = None,
        top_k: int = 3
    ) -> Dict[str, Any]:
        """
        一体化排序和融合：先排序再融合
        
        智能策略:
        - 英文: PairRM排序 + GenFuser融合
        - 中文: PairRM排序 + DeepSeek API融合
        
        Args:
            query: 用户的原始问题
            responses: AI模型的回答列表
            instruction: 可选的指令前缀
            top_k: 用于融合的top-k回答数量
            
        Returns:
            包含排序结果和融合结果的字典
        """
        # 移除重复的初始化检查，由get_blender_service统一管理
        logger.debug(f"🔄 开始智能排序+融合处理...")
        start_time = time.time()
        
        # 检测语言
        has_chinese = (self.contains_chinese(query) or 
                      any(self.contains_chinese(resp.get("content", "")) for resp in responses))
        
        fusion_method = "deepseek_chinese" if has_chinese else "genfuser_english"
        logger.info(f"🌐 语言检测: {'中文' if has_chinese else '英文'}, 融合策略: {fusion_method}")
        
        try:
            # 1. 排序（PairRM对中英文都支持良好）
            ranked_responses = await self.rank_responses(query, responses, instruction)
            
            # 2. 融合（根据语言选择策略）
            fused_content = await self.fuse_responses(query, ranked_responses, instruction, top_k)
            
            total_time = time.time() - start_time
            
            result = {
                "fused_content": fused_content,
                "ranked_responses": ranked_responses,
                "best_response": ranked_responses[0] if ranked_responses else None,
                "processing_time": total_time,
                "models_used": [resp["modelId"] for resp in ranked_responses[:top_k]],
                "fusion_method": fusion_method,
                "language_detected": "chinese" if has_chinese else "english"
            }
            
            logger.info(f"🎯 智能处理完成 ({total_time:.2f}s)")
            return result
            
        except Exception as e:
            logger.error(f"❌ 智能处理失败: {str(e)}")
            raise e
    
    async def _simple_fusion_from_responses(self, query: str, responses: List[Dict[str, Any]]) -> str:
        """从响应对象列表进行简单融合的辅助方法"""
        # 转换为原有格式
        simple_responses = []
        for resp in responses:
            simple_resp = {
                "modelId": resp.get("modelId", "unknown"),
                "content": resp.get("content", "")
            }
            simple_responses.append(simple_resp)
        
        return await self._simple_fusion(query, simple_responses, len(responses))
    
    async def _simple_fusion(self, query: str, responses: List[Dict[str, Any]], top_k: int) -> str:
        """简单的文本融合作为备选方案"""
        logger.info("📝 使用简单文本融合作为备选方案...")
        
        if not responses:
            return "抱歉，没有可用的回答。"
        
        if len(responses) == 1:
            return responses[0]["content"]
        
        # 选择top-k回答
        top_responses = responses[:top_k]
        
        # 构建融合回答
        fusion_parts = []
        fusion_parts.append(f"基于 {len(top_responses)} 个AI模型的回答，为您提供以下综合答案：\n")
        
        # 如果有明显的最佳回答，以它为主
        best_response = top_responses[0]
        fusion_parts.append(f"**主要观点** (来源: {best_response['modelId']}):\n{best_response['content']}\n")
        
        # 如果有其他高质量回答，添加补充观点
        if len(top_responses) > 1:
            fusion_parts.append("**补充观点**:")
            for resp in top_responses[1:]:
                fusion_parts.append(f"- {resp['modelId']}: {resp['content'][:200]}{'...' if len(resp['content']) > 200 else ''}")
        
        return "\n".join(fusion_parts)

    async def _lazy_load_ranker(self) -> bool:
        """懒加载Ranker模型"""
        if self.ranker_loaded:
            return True
            
        try:
            logger.info("🔄 懒加载 PairRM Ranker...")
            if self.blender is None:
                self.blender = llm_blender.Blender()
            
            start_time = time.time()
            self.blender.loadranker(
                "llm-blender/PairRM",
                device="cpu"
            )
            ranker_time = time.time() - start_time
            self.ranker_loaded = True
            logger.info(f"✅ Ranker 懒加载成功 ({ranker_time:.2f}s)")
            return True
        except Exception as e:
            logger.error(f"❌ Ranker懒加载失败: {str(e)}")
            return False
    
    async def _lazy_load_fuser(self) -> bool:
        """懒加载GenFuser模型"""
        if self.fuser_loaded:
            return True
            
        try:
            logger.info("🔄 懒加载 GenFuser...")
            if self.blender is None:
                self.blender = llm_blender.Blender()
            
            start_time = time.time()
            self.blender.loadfuser(
                "llm-blender/gen_fuser_3b",
                device="cpu",
                local_files_only=True
            )
            fuser_time = time.time() - start_time
            self.fuser_loaded = True
            logger.info(f"✅ GenFuser 懒加载成功 ({fuser_time:.2f}s)")
            logger.info("📝 GenFuser 配置: 支持更长输入 (max_length=2048, candidate_max_length=512)")
            return True
        except Exception as e:
            logger.error(f"❌ GenFuser懒加载失败: {str(e)}")
            return False

# 全局服务实例
_blender_service = None
_service_lock = asyncio.Lock()  # 添加锁确保线程安全

async def get_blender_service() -> LLMBlenderService:
    """获取全局LLM-Blender服务实例（线程安全的单例模式）"""
    global _blender_service
    
    # 使用锁确保只有一个实例被创建
    async with _service_lock:
        if _blender_service is None:
            logger.info("🏗️ 创建新的 LLM-Blender 服务实例...")
            _blender_service = LLMBlenderService()
            await _blender_service.initialize()
            logger.info("✅ 全局 LLM-Blender 服务实例创建完成")
        else:
            logger.debug("♻️ 重用现有的 LLM-Blender 服务实例")
    
    return _blender_service

# 对外接口函数
async def get_advanced_fusion_response(
    query: str,
    responses: List[Dict[str, Any]], 
    instruction: Optional[str] = None,
    top_k: int = 3,
    fusion_method: str = "rank_and_fuse"
) -> Dict[str, Any]:
    """
    高级融合服务主入口
    
    Args:
        query: 用户问题
        responses: AI回答列表 [{"modelId": "xxx", "content": "xxx"}, ...]
        instruction: 可选指令
        top_k: 融合使用的回答数量
        fusion_method: 融合方法 ("rank_only", "fuse_only", "rank_and_fuse")
        
    Returns:
        融合结果字典
    """
    try:
        service = await get_blender_service()
        logger.debug(f"🔧 使用融合方法: {fusion_method}, top_k: {top_k}")
        
        if fusion_method == "rank_only":
            ranked = await service.rank_responses(query, responses, instruction)
            return {
                "fused_content": ranked[0]["content"] if ranked else "",
                "ranked_responses": ranked,
                "fusion_method": "rank_only"
            }
        elif fusion_method == "fuse_only":
            fused = await service.fuse_responses(query, responses, instruction, top_k)
            return {
                "fused_content": fused,
                "ranked_responses": responses,
                "fusion_method": "fuse_only"
            }
        else:  # rank_and_fuse
            return await service.rank_and_fuse(query, responses, instruction, top_k)
            
    except Exception as e:
        logger.error(f"❌ 高级融合服务失败: {str(e)}")
        # 降级到简单融合
        if responses:
            return {
                "fused_content": responses[0]["content"],
                "ranked_responses": responses,
                "fusion_method": "fallback",
                "error": str(e)
            }
        else:
            return {
                "fused_content": "抱歉，融合服务暂时不可用。",
                "ranked_responses": [],
                "fusion_method": "error",
                "error": str(e)
            } 