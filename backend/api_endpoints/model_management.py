#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模型管理API端点

提供模型列表、切换、状态查询等功能
"""

import logging
from flask import Blueprint, jsonify, request, Response
from services.model_registry import model_registry, auto_register_models, add_custom_model

logger = logging.getLogger(__name__)

# 创建蓝图
model_bp = Blueprint('model', __name__, url_prefix='/api/models')

# 初始化时自动注册所有模型
auto_register_models()

@model_bp.route('/list', methods=['GET'])
def get_models():
    """获取所有模型列表"""
    try:
        # 刷新模型可用性
        model_registry.refresh_model_availability()
        
        # 获取模型列表
        all_models = model_registry.get_all_models()
        available_models = model_registry.get_available_models()
        
        return jsonify({
            "success": True,
            "data": {
                "all_models": all_models,
                "available_models": available_models,
                "total_count": len(all_models),
                "available_count": len(available_models)
            }
        })
    except Exception as e:
        logger.error(f"获取模型列表失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@model_bp.route('/available', methods=['GET'])
def get_available_models():
    """获取可用模型列表"""
    try:
        model_registry.refresh_model_availability()
        available_models = model_registry.get_available_models()
        
        return jsonify({
            "success": True,
            "data": available_models
        })
    except Exception as e:
        logger.error(f"获取可用模型失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@model_bp.route('/status/<model_id>', methods=['GET'])
def get_model_status(model_id):
    """获取特定模型状态"""
    try:
        model_registry.refresh_model_availability()
        is_available = model_registry.is_model_available(model_id)
        service = model_registry.get_model_service(model_id)
        
        if not service:
            return jsonify({
                "success": False,
                "error": f"模型不存在: {model_id}"
            }), 404
        
        # 获取模型配置信息
        config = service.get_api_config()
        
        return jsonify({
            "success": True,
            "data": {
                "model_id": model_id,
                "available": is_available,
                "has_api_key": bool(config.get("api_key")),
                "has_api_base": bool(config.get("api_base")),
                "api_base": config.get("api_base", ""),
                "model_name": service.model_name
            }
        })
    except Exception as e:
        logger.error(f"获取模型状态失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@model_bp.route('/test/<model_id>', methods=['POST'])
def test_model(model_id):
    """测试模型连接"""
    try:
        data = request.get_json()
        test_message = data.get('message', '你好，请简单介绍一下自己。')
        
        service = model_registry.get_model_service(model_id)
        if not service:
            return jsonify({
                "success": False,
                "error": f"模型不存在: {model_id}"
            }), 404
        
        if not model_registry.is_model_available(model_id):
            return jsonify({
                "success": False,
                "error": f"模型不可用: {model_id}"
            }), 400
        
        # 测试非流式响应
        response = await model_registry.get_model_response(
            model_id, 
            test_message, 
            stream=False
        )
        
        return jsonify({
            "success": True,
            "data": {
                "model_id": model_id,
                "test_message": test_message,
                "response": response,
                "status": "连接正常"
            }
        })
        
    except Exception as e:
        logger.error(f"测试模型失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@model_bp.route('/add_custom', methods=['POST'])
def add_custom_model_endpoint():
    """添加自定义模型"""
    try:
        data = request.get_json()
        
        # 必需参数
        required_fields = ['model_id', 'api_key_env', 'api_base_env', 'display_name', 'model_name']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    "success": False,
                    "error": f"缺少必需参数: {field}"
                }), 400
        
        # 可选参数
        endpoint_path = data.get('endpoint_path', '/chat/completions')
        description = data.get('description', '')
        request_params = data.get('request_params', {})
        
        # 添加自定义模型
        add_custom_model(
            model_id=data['model_id'],
            api_key_env=data['api_key_env'],
            api_base_env=data['api_base_env'],
            display_name=data['display_name'],
            model_name=data['model_name'],
            endpoint_path=endpoint_path,
            description=description,
            **request_params
        )
        
        return jsonify({
            "success": True,
            "message": f"成功添加自定义模型: {data['display_name']}"
        })
        
    except Exception as e:
        logger.error(f"添加自定义模型失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@model_bp.route('/refresh', methods=['POST'])
def refresh_models():
    """刷新模型状态"""
    try:
        model_registry.refresh_model_availability()
        available_models = model_registry.get_available_models()
        
        return jsonify({
            "success": True,
            "message": "模型状态已刷新",
            "data": {
                "available_count": len(available_models),
                "available_models": available_models
            }
        })
    except Exception as e:
        logger.error(f"刷新模型状态失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# 统一的模型响应端点
@model_bp.route('/chat/<model_id>', methods=['POST'])
def chat_with_model(model_id):
    """与指定模型对话"""
    try:
        data = request.get_json()
        message = data.get('message', '')
        conversation_history = data.get('conversation_history', [])
        stream = data.get('stream', False)
        
        if not message:
            return jsonify({
                "success": False,
                "error": "消息不能为空"
            }), 400
        
        if stream:
            # 流式响应
            def generate():
                try:
                    async for chunk in model_registry.get_model_response(
                        model_id, message, conversation_history, stream=True
                    ):
                        yield f"data: {chunk}\n\n"
                except Exception as e:
                    yield f"data: {{'error': '{str(e)}'}}\n\n"
                finally:
                    yield "data: [DONE]\n\n"
            
            return Response(generate(), mimetype='text/event-stream')
        else:
            # 非流式响应
            response = await model_registry.get_model_response(
                model_id, message, conversation_history, stream=False
            )
            
            return jsonify({
                "success": True,
                "data": {
                    "model_id": model_id,
                    "response": response
                }
            })
            
    except Exception as e:
        logger.error(f"模型对话失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500 