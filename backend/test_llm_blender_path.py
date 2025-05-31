#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试LLM-Blender路径调整是否成功
"""

import asyncio
import sys
import os
from pathlib import Path

# 添加当前路径到sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def test_llm_blender_path():
    """测试LLM-Blender路径和导入"""
    print("🧪 测试LLM-Blender路径调整...")
    print("=" * 60)
    
    try:
        # 1. 测试路径导入
        print("1️⃣ 测试服务导入...")
        from services.llm_blender_service import get_blender_service
        print("✅ 服务导入成功")
        
        # 2. 测试服务初始化
        print("\n2️⃣ 测试服务初始化...")
        service = await get_blender_service()
        print("✅ 服务实例创建成功")
        
        # 3. 检查服务状态
        print("\n3️⃣ 检查服务状态...")
        print(f"📊 初始化状态: {'✅ 已初始化' if service.is_initialized else '❌ 未初始化'}")
        print(f"📊 Ranker状态: {'✅ 已加载' if service.ranker_loaded else '❌ 未加载'}")
        print(f"📊 Fuser状态: {'✅ 已加载' if service.fuser_loaded else '❌ 未加载'}")
        
        # 4. 简单功能测试（如果Ranker已加载）
        if service.ranker_loaded:
            print("\n4️⃣ 测试基础功能...")
            test_query = "什么是机器学习？"
            test_responses = [
                {"modelId": "test1", "content": "机器学习是人工智能的一个分支"},
                {"modelId": "test2", "content": "机器学习是让计算机从数据中学习的技术"}
            ]
            
            # 测试排序功能
            ranked_responses = await service.rank_responses(test_query, test_responses)
            print(f"✅ 排序功能测试成功，处理了{len(ranked_responses)}个回答")
            
            # 显示排序结果
            for i, resp in enumerate(ranked_responses):
                print(f"   排名{i+1}: {resp['modelId']} (质量分数: {resp.get('quality_score', 'N/A')})")
        
        print("\n" + "=" * 60)
        print("🎉 LLM-Blender路径调整成功！服务运行正常")
        print("=" * 60)
        
        return True
        
    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        print("💡 请检查LLM-Blender是否正确放置在services目录下")
        return False
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        print(f"详细错误: {type(e).__name__}: {str(e)}")
        return False

async def main():
    """主函数"""
    print("🚀 开始LLM-Blender路径测试...")
    
    # 显示当前路径信息
    current_file = Path(__file__)
    services_dir = current_file.parent / "services"
    llm_blender_dir = services_dir / "LLM-Blender"
    
    print(f"📂 当前文件: {current_file}")
    print(f"📂 services目录: {services_dir}")
    print(f"📂 LLM-Blender目录: {llm_blender_dir}")
    print(f"🔍 LLM-Blender存在: {'✅' if llm_blender_dir.exists() else '❌'}")
    
    if llm_blender_dir.exists():
        # 列出LLM-Blender目录内容
        try:
            contents = list(llm_blender_dir.iterdir())
            print(f"📋 LLM-Blender内容: {[item.name for item in contents[:5]]}{'...' if len(contents) > 5 else ''}")
        except Exception as e:
            print(f"⚠️ 无法读取LLM-Blender目录: {e}")
    
    print("\n" + "=" * 60)
    
    # 运行测试
    success = await test_llm_blender_path()
    
    if success:
        print("\n💡 接下来可以:")
        print("   1. 运行完整的后端服务: python run.py")
        print("   2. 测试智能融合功能")
        print("   3. 启动前端服务")
    else:
        print("\n💡 建议检查:")
        print("   1. LLM-Blender文件夹是否在services目录下")
        print("   2. LLM-Blender内部结构是否完整")
        print("   3. Python环境依赖是否正确安装")

if __name__ == "__main__":
    asyncio.run(main()) 