#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能提示词服务

提供预定义的提示词模板、智能补全建议和自定义提示词管理功能
"""

import re
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class PromptService:
    """智能提示词服务类"""
    
    def __init__(self):
        """初始化提示词服务"""
        self.prompt_templates = self._load_prompt_templates()
        self.categories = list(self.prompt_templates.keys())
        
    def _load_prompt_templates(self) -> Dict[str, List[Dict[str, Any]]]:
        """加载预定义的提示词模板"""
        return {
            "写作助手": [
                {
                    "id": "writing_essay",
                    "title": "学术论文写作",
                    "description": "帮助撰写结构化的学术论文",
                    "template": "请帮我写一篇关于【主题】的学术论文。要求：\n1. 包含引言、主体、结论三个部分\n2. 论证逻辑清晰，有理有据\n3. 引用相关研究和数据\n4. 字数约【字数】字\n5. 学术风格严谨\n\n具体要求：{user_input}",
                    "placeholders": ["主题", "字数"],
                    "example": "请帮我写一篇关于人工智能在教育中应用的学术论文..."
                },
                {
                    "id": "writing_creative",
                    "title": "创意文案",
                    "description": "创作吸引人的营销文案或创意内容",
                    "template": "请为【产品/服务】创作一个【类型】。要求：\n1. 吸引目标受众【目标受众】\n2. 突出核心卖点【卖点】\n3. 风格【风格】\n4. 字数控制在【字数】字以内\n\n详细描述：{user_input}",
                    "placeholders": ["产品/服务", "类型", "目标受众", "卖点", "风格", "字数"],
                    "example": "请为智能手表创作一个营销文案..."
                },
                {
                    "id": "writing_report",
                    "title": "报告总结",
                    "description": "生成专业的报告或总结文档",
                    "template": "请帮我写一份【报告类型】，主题是【主题】。要求：\n1. 结构清晰，包含目录\n2. 数据分析客观准确\n3. 结论建议具体可行\n4. 格式专业规范\n\n具体内容和要求：{user_input}",
                    "placeholders": ["报告类型", "主题"],
                    "example": "请帮我写一份市场调研报告，主题是智能家居市场..."
                }
            ],
            "编程助手": [
                {
                    "id": "code_review",
                    "title": "代码审查",
                    "description": "审查代码质量、性能和安全性",
                    "template": "请审查以下【编程语言】代码，重点关注：\n1. 代码质量和可读性\n2. 性能优化建议\n3. 安全性问题\n4. 最佳实践遵循\n5. 潜在的bug和改进建议\n\n代码内容：\n```{user_input}```",
                    "placeholders": ["编程语言"],
                    "example": "请审查以下Python代码..."
                },
                {
                    "id": "code_debug",
                    "title": "代码调试",
                    "description": "帮助发现和修复代码中的错误",
                    "template": "我的【编程语言】代码遇到了【问题类型】问题。请帮助：\n1. 分析问题原因\n2. 提供修复方案\n3. 给出正确的代码实现\n4. 解释修改的原理\n\n错误描述：【错误描述】\n\n代码：\n```{user_input}```",
                    "placeholders": ["编程语言", "问题类型", "错误描述"],
                    "example": "我的Python代码遇到了运行时错误..."
                },
                {
                    "id": "code_optimize",
                    "title": "代码优化",
                    "description": "优化代码性能和结构",
                    "template": "请优化以下【编程语言】代码，目标：\n1. 提高执行效率\n2. 减少内存占用\n3. 改善代码结构\n4. 增强可维护性\n\n优化重点：【优化重点】\n\n原始代码：\n```{user_input}```",
                    "placeholders": ["编程语言", "优化重点"],
                    "example": "请优化以下Python代码的性能..."
                }
            ],
            "学习辅导": [
                {
                    "id": "explain_concept",
                    "title": "概念解释",
                    "description": "深入解释复杂概念或原理",
                    "template": "请详细解释【学科】中的【概念名称】概念。要求：\n1. 从基础开始，循序渐进\n2. 使用通俗易懂的语言\n3. 提供具体例子说明\n4. 指出常见误区\n5. 适合【学习水平】水平的学习者\n\n具体问题：{user_input}",
                    "placeholders": ["学科", "概念名称", "学习水平"],
                    "example": "请详细解释物理学中的量子纠缠概念..."
                },
                {
                    "id": "solve_problem",
                    "title": "问题求解",
                    "description": "逐步解决学习中的具体问题",
                    "template": "请帮我解决这个【学科】问题，要求：\n1. 详细的解题步骤\n2. 解释每一步的原理\n3. 指出关键思路和方法\n4. 提供类似题目的练习建议\n\n问题描述：{user_input}",
                    "placeholders": ["学科"],
                    "example": "请帮我解决这个数学微积分问题..."
                },
                {
                    "id": "study_plan",
                    "title": "学习计划",
                    "description": "制定个性化的学习计划",
                    "template": "请为我制定【学科/技能】的学习计划。背景信息：\n- 当前水平：【当前水平】\n- 目标水平：【目标水平】\n- 可用时间：【时间安排】\n- 学习偏好：【学习偏好】\n\n具体要求：{user_input}",
                    "placeholders": ["学科/技能", "当前水平", "目标水平", "时间安排", "学习偏好"],
                    "example": "请为我制定Python编程的学习计划..."
                }
            ],
            "分析推理": [
                {
                    "id": "data_analysis",
                    "title": "数据分析",
                    "description": "分析数据趋势和模式",
                    "template": "请分析以下【数据类型】数据，重点关注：\n1. 数据趋势和模式\n2. 异常值和特殊情况\n3. 相关性分析\n4. 预测和建议\n5. 可视化建议\n\n数据背景：【数据背景】\n\n数据内容：{user_input}",
                    "placeholders": ["数据类型", "数据背景"],
                    "example": "请分析以下销售数据的趋势..."
                },
                {
                    "id": "logical_reasoning",
                    "title": "逻辑推理",
                    "description": "进行逻辑分析和推理",
                    "template": "请对以下【问题类型】进行逻辑分析，要求：\n1. 理清逻辑关系\n2. 识别关键假设\n3. 分析论证过程\n4. 指出可能的逻辑漏洞\n5. 给出结论和建议\n\n问题描述：{user_input}",
                    "placeholders": ["问题类型"],
                    "example": "请对以下商业决策进行逻辑分析..."
                },
                {
                    "id": "compare_analysis",
                    "title": "对比分析",
                    "description": "比较分析不同选项或方案",
                    "template": "请对比分析【对比对象】，分析维度包括：\n1. 【维度1】\n2. 【维度2】\n3. 【维度3】\n4. 综合评估和建议\n\n详细要求：{user_input}",
                    "placeholders": ["对比对象", "维度1", "维度2", "维度3"],
                    "example": "请对比分析iOS和Android开发平台..."
                }
            ],
            "商务沟通": [
                {
                    "id": "email_formal",
                    "title": "商务邮件",
                    "description": "撰写专业的商务邮件",
                    "template": "请帮我写一封【邮件类型】邮件，收件人是【收件人】。要求：\n1. 语言正式且礼貌\n2. 结构清晰条理\n3. 目的明确具体\n4. 包含必要的行动呼吁\n\n邮件内容和背景：{user_input}",
                    "placeholders": ["邮件类型", "收件人"],
                    "example": "请帮我写一封项目进度汇报邮件..."
                },
                {
                    "id": "presentation",
                    "title": "演示文稿",
                    "description": "创建演示文稿大纲和内容",
                    "template": "请帮我创建【主题】的演示文稿大纲，时长【时长】分钟，面向【听众】。包括：\n1. 开场白和自我介绍\n2. 主要内容结构\n3. 关键观点和论据\n4. 视觉化建议\n5. 结尾和Q&A准备\n\n具体要求：{user_input}",
                    "placeholders": ["主题", "时长", "听众"],
                    "example": "请帮我创建AI技术应用的演示文稿..."
                },
                {
                    "id": "proposal",
                    "title": "商业提案",
                    "description": "撰写商业提案或方案",
                    "template": "请帮我写一份【提案类型】提案，包含：\n1. 问题分析和机会识别\n2. 解决方案描述\n3. 实施计划和时间线\n4. 预算和资源需求\n5. 预期收益和风险评估\n\n背景和要求：{user_input}",
                    "placeholders": ["提案类型"],
                    "example": "请帮我写一份数字化转型的商业提案..."
                }
            ],
            "创意设计": [
                {
                    "id": "brainstorm",
                    "title": "头脑风暴",
                    "description": "产生创新想法和解决方案",
                    "template": "请为【问题/挑战】进行头脑风暴，要求：\n1. 产生多样化的创意想法\n2. 从不同角度思考问题\n3. 包含创新和传统的解决方案\n4. 评估每个想法的可行性\n5. 推荐最佳的3-5个方案\n\n具体情况：{user_input}",
                    "placeholders": ["问题/挑战"],
                    "example": "请为提高用户活跃度的问题进行头脑风暴..."
                },
                {
                    "id": "design_concept",
                    "title": "设计概念",
                    "description": "生成设计理念和概念方案",
                    "template": "请为【设计项目】提供设计概念，要求：\n1. 明确设计目标和用户需求\n2. 提出创新的设计理念\n3. 描述视觉风格和元素\n4. 考虑用户体验和功能性\n5. 提供实现建议\n\n项目详情：{user_input}",
                    "placeholders": ["设计项目"],
                    "example": "请为移动应用界面提供设计概念..."
                },
                {
                    "id": "story_creation",
                    "title": "故事创作",
                    "description": "创作引人入胜的故事内容",
                    "template": "请创作一个【故事类型】故事，要求：\n1. 主题：【主题】\n2. 目标受众：【受众】\n3. 风格：【风格】\n4. 长度：【长度】\n5. 包含引人入胜的情节和角色\n\n创作要求：{user_input}",
                    "placeholders": ["故事类型", "主题", "受众", "风格", "长度"],
                    "example": "请创作一个科幻短篇故事..."
                }
            ]
        }
    
    def get_categories(self) -> List[str]:
        """获取所有提示词分类"""
        return self.categories
    
    def get_templates_by_category(self, category: str) -> List[Dict[str, Any]]:
        """根据分类获取提示词模板"""
        return self.prompt_templates.get(category, [])
    
    def get_template_by_id(self, template_id: str) -> Optional[Dict[str, Any]]:
        """根据ID获取特定的提示词模板"""
        for category_templates in self.prompt_templates.values():
            for template in category_templates:
                if template["id"] == template_id:
                    return template
        return None
    
    def apply_template(self, template_id: str, user_input: str, placeholders: Dict[str, str] = None) -> str:
        """应用提示词模板生成完整的提示"""
        template = self.get_template_by_id(template_id)
        if not template:
            return user_input
        
        prompt = template["template"].format(user_input=user_input)
        
        # 替换占位符
        if placeholders:
            for placeholder, value in placeholders.items():
                prompt = prompt.replace(f"【{placeholder}】", value)
        
        return prompt
    
    def suggest_prompts(self, user_input: str, limit: int = 5) -> List[Dict[str, Any]]:
        """基于用户输入智能建议相关的提示词模板"""
        if not user_input.strip():
            return []
        
        input_lower = user_input.lower()
        suggestions = []
        
        # 关键词映射
        keyword_mapping = {
            "写作": ["写", "文章", "文案", "论文", "报告", "总结"],
            "编程助手": ["代码", "编程", "bug", "错误", "优化", "程序", "算法", "python", "java", "javascript"],
            "学习辅导": ["学习", "解释", "概念", "原理", "问题", "作业", "考试", "理解"],
            "分析推理": ["分析", "数据", "趋势", "比较", "评估", "推理", "逻辑"],
            "商务沟通": ["邮件", "商务", "会议", "提案", "演示", "沟通", "商业"],
            "创意设计": ["创意", "设计", "想法", "创新", "头脑风暴", "故事", "创作"]
        }
        
        # 为每个模板计算相关性得分
        for category, templates in self.prompt_templates.items():
            for template in templates:
                score = 0
                
                # 检查分类关键词匹配
                category_keywords = keyword_mapping.get(category, [])
                for keyword in category_keywords:
                    if keyword in input_lower:
                        score += 2
                
                # 检查模板标题和描述匹配
                if any(word in input_lower for word in template["title"].lower().split()):
                    score += 3
                
                if any(word in input_lower for word in template["description"].lower().split()):
                    score += 1
                
                # 检查模板内容关键词匹配
                template_content = template["template"].lower()
                common_words = set(input_lower.split()) & set(template_content.split())
                score += len(common_words) * 0.5
                
                if score > 0:
                    suggestions.append({
                        "template": template,
                        "category": category,
                        "score": score,
                        "reason": self._generate_suggestion_reason(template, input_lower)
                    })
        
        # 按得分排序并返回前limit个
        suggestions.sort(key=lambda x: x["score"], reverse=True)
        return suggestions[:limit]
    
    def _generate_suggestion_reason(self, template: Dict[str, Any], user_input: str) -> str:
        """生成建议理由"""
        title = template["title"]
        description = template["description"]
        
        reasons = []
        if "写" in user_input or "文" in user_input:
            if "写作" in title or "文案" in title:
                reasons.append("适合写作任务")
        
        if "代码" in user_input or "编程" in user_input:
            if "代码" in title:
                reasons.append("专门用于编程相关任务")
        
        if "学习" in user_input or "解释" in user_input:
            if "解释" in title or "学习" in title:
                reasons.append("帮助学习和理解")
        
        if "分析" in user_input:
            if "分析" in title:
                reasons.append("提供深入分析")
        
        if not reasons:
            reasons.append(f"可以帮助{description}")
        
        return "、".join(reasons)
    
    def get_auto_completions(self, partial_input: str) -> List[str]:
        """获取自动补全建议"""
        if len(partial_input) < 2:
            return []
        
        completions = []
        input_lower = partial_input.lower()
        
        # 智能补全模板 - 基于常见的用户输入模式
        completion_templates = [
            # 写作相关
            {
                "patterns": ["如何写", "写一", "怎么写", "写作"],
                "completions": [
                    "如何写一篇高质量的学术论文，包含研究方法和引用格式？",
                    "如何写一份吸引人的商业计划书？",
                    "如何写一篇引人入胜的小说或故事？",
                    "如何写一份专业的工作总结报告？",
                    "如何写一篇有说服力的文案？"
                ]
            },
            # 学习相关  
            {
                "patterns": ["如何学", "学习", "怎么学"],
                "completions": [
                    "如何学习编程，从零基础到高级开发者？",
                    "如何学习一门新的外语？",
                    "如何学习数据科学和机器学习？",
                    "如何学习设计软件和创意技能？"
                ]
            },
            # 分析相关
            {
                "patterns": ["分析", "如何分析", "怎么分析"],
                "completions": [
                    "请分析这个商业案例的成功因素",
                    "请分析当前市场趋势和机会",
                    "请分析这段代码的性能问题",
                    "请分析用户需求和痛点"
                ]
            },
            # 解决问题
            {
                "patterns": ["如何解决", "解决", "怎么解决"],
                "completions": [
                    "如何解决团队沟通效率低的问题？",
                    "如何解决项目进度延迟的问题？",
                    "如何解决技术难题和编程错误？"
                ]
            },
            # 制定计划
            {
                "patterns": ["制定", "计划", "如何制定"],
                "completions": [
                    "请帮我制定一个完整的学习计划",
                    "请帮我制定项目实施方案和时间表",
                    "请帮我制定营销推广策略"
                ]
            },
            # 编程相关
            {
                "patterns": ["代码", "编程", "程序"],
                "completions": [
                    "请帮我优化这段代码的性能",
                    "请解释这个编程概念和原理",
                    "请帮我调试这个程序错误",
                    "请推荐最佳的编程实践方法"
                ]
            },
            # 通用问答
            {
                "patterns": ["什么是", "是什么", "解释"],
                "completions": [
                    "请详细解释这个概念的含义和应用",
                    "请解释这个技术原理和工作机制",
                    "请解释这个商业模式的优势"
                ]
            }
        ]
        
        # 找到匹配的模板
        for template in completion_templates:
            for pattern in template["patterns"]:
                if pattern in input_lower:
                    for completion in template["completions"]:
                        if completion not in completions:
                            completions.append(completion)
                    break  # 找到一个匹配的模式就够了
        
        # 如果没有找到匹配的模板，提供一些通用补全
        if not completions:
            general_completions = [
                "请帮我分析这个问题的解决方案",
                "请详细解释这个概念",
                "请提供相关的建议和指导",
                "请帮我优化和改进这个内容"
            ]
            completions.extend(general_completions)
        
        # 基于已有模板的智能匹配
        for category, templates in self.prompt_templates.items():
            for template in templates:
                template_title = template["title"].lower()
                template_desc = template["description"].lower()
                
                # 如果用户输入与模板标题或描述相关，提供基于模板的补全
                input_words = set(input_lower.split())
                title_words = set(template_title.split())
                desc_words = set(template_desc.split())
                
                if input_words & (title_words | desc_words):
                    suggestion = f"请{template['description']}：{template['example']}"
                    if suggestion not in completions:
                        completions.append(suggestion)
        
        # 去重并限制数量
        unique_completions = []
        for comp in completions:
            if comp not in unique_completions:
                unique_completions.append(comp)
        
        return unique_completions[:8]  # 限制返回数量
    
    def get_intelligent_completions(self, partial_input: str) -> List[str]:
        """获取智能补全建议（基于Transformer和N-gram混合模型）"""
        try:
            # 优先使用高级Transformer混合服务
            from .intelligent_completion_service import get_advanced_intelligent_completions
            return get_advanced_intelligent_completions(partial_input, max_completions=5)
        except Exception as e:
            logger.error(f"高级智能补全服务出错: {e}")
            # 降级到模板匹配
            return self.get_auto_completions(partial_input)
    
    def get_word_predictions(self, context: str, top_k: int = 8) -> List[Dict[str, any]]:
        """获取下一个词的概率预测（基于Transformer和N-gram混合模型）"""
        try:
            # 优先使用高级Transformer混合服务
            from .intelligent_completion_service import get_advanced_word_predictions
            return get_advanced_word_predictions(context, top_k=top_k)
        except Exception as e:
            logger.error(f"高级词汇预测服务出错: {e}")
            # 降级到原始N-gram服务
            try:
                from .intelligent_completion_service import get_intelligent_completion_service
                service = get_intelligent_completion_service()
                return service.get_word_predictions_with_probabilities(context, top_k=top_k)
            except Exception as e2:
                logger.error(f"词汇预测服务完全失败: {e2}")
                return []

# 全局提示词服务实例
_prompt_service_instance = None

def get_prompt_service() -> PromptService:
    """获取全局提示词服务实例"""
    global _prompt_service_instance
    if _prompt_service_instance is None:
        _prompt_service_instance = PromptService()
        logger.info("✅ 提示词服务初始化完成")
    return _prompt_service_instance 