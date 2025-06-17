# MongoDB模型配置管理系统使用指南

## 🎯 系统概述

我们已经成功将模型配置管理系统集成到现有的MongoDB数据库中，实现了用户模型配置的持久化存储。系统会在后端服务重启后自动恢复用户的模型配置。

## 📊 数据库结构

### user_models 集合结构
```json
{
  "_id": ObjectId("..."),
  "model_id": "用户定义的模型ID",
  "user_id": "用户ID（支持多用户）",
  "name": "模型显示名称",
  "api_key": "API密钥",
  "api_base": "API基础URL",
  "model_type": "模型类型（custom/openai/anthropic等）",
  "description": "模型描述",
  "max_tokens": 4000,
  "temperature": 0.7,
  "stream_support": true,
  "is_active": true,
  "created_at": "2025-01-15T10:30:00+08:00",
  "updated_at": "2025-01-15T10:30:00+08:00",
  "config_version": "1.0"
}
```

## 🚀 功能特性

### 1. 自动持久化
- ✅ 用户添加模型时自动保存到MongoDB
- ✅ 支持多用户隔离，每个用户只能访问自己的模型配置
- ✅ 软删除机制，删除的模型标记为 `is_active: false`

### 2. 启动时恢复
- ✅ 后端服务启动时自动从MongoDB恢复模型配置
- ✅ 自动设置环境变量（`{MODEL_ID}_API_KEY`, `{MODEL_ID}_API_BASE`）
- ✅ 与BaseModelService架构无缝集成

### 3. 数据库索引优化
```javascript
// 创建的索引
db.user_models.createIndex({"model_id": 1}, {unique: true})
db.user_models.createIndex({"user_id": 1})
db.user_models.createIndex({"user_id": 1, "created_at": -1})
db.user_models.createIndex({"created_at": 1})
db.user_models.createIndex({"updated_at": 1})
db.user_models.createIndex({"is_active": 1})
```

## 🔧 API端点

### 基础模型管理
- `GET /api/models` - 获取用户的所有模型（包括数据库中的）
- `POST /api/models` - 添加新模型（自动保存到数据库）
- `DELETE /api/models/{model_id}` - 删除模型（从数据库软删除）

### 高级模型管理
- `GET /api/models/{model_id}` - 获取指定模型配置
- `PUT /api/models/{model_id}` - 更新模型配置
- `GET /api/models/statistics` - 获取用户模型统计信息
- `GET /api/models/export` - 导出用户的所有模型配置
- `POST /api/models/import` - 导入模型配置

## 📝 使用示例

### 1. 添加新模型
```javascript
// 前端调用
const response = await fetch('http://localhost:8000/api/models', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  credentials: 'include', // 包含用户cookie
  body: JSON.stringify({
    id: 'my_custom_gpt',
    name: '我的自定义GPT',
    apiKey: 'sk-xxxxxxxxxx',
    url: 'https://api.openai.com/v1'
  })
});

// 响应
{
  "id": "my_custom_gpt",
  "name": "我的自定义GPT",
  "apiKey": "sk-xxxxxxxxxx",
  "url": "https://api.openai.com/v1",
  "registered_to_base_service": true,
  "saved_to_database": true,
  "message": "模型已成功添加、保存到数据库并注册到服务系统"
}
```

### 2. 获取模型列表
```javascript
// 前端调用
const response = await fetch('http://localhost:8000/api/models', {
  credentials: 'include'
});

// 响应包含数据库中的模型
[
  {
    "id": "my_custom_gpt",
    "name": "我的自定义GPT",
    "apiKey": "***hidden***",
    "url": "https://api.openai.com/v1",
    "available": true,
    "source": "database",
    "type": "custom",
    "createdAt": "2025-01-15T10:30:00+08:00",
    "updatedAt": "2025-01-15T10:30:00+08:00"
  }
]
```

### 3. 获取模型统计
```javascript
// 前端调用
const response = await fetch('http://localhost:8000/api/models/statistics', {
  credentials: 'include'
});

// 响应
{
  "user_id": "user123",
  "active_models": 3,
  "total_models": 5,
  "by_type": {
    "custom": 2,
    "openai": 1
  },
  "generated_at": "2025-01-15T10:30:00+08:00"
}
```

### 4. 导出模型配置
```javascript
// 前端调用
const response = await fetch('http://localhost:8000/api/models/export', {
  credentials: 'include'
});

// 响应
{
  "export_version": "1.0",
  "user_id": "user123",
  "exported_at": "2025-01-15T10:30:00+08:00",
  "model_count": 3,
  "models": [...]
}
```

## 🔄 系统集成

### 与现有系统的兼容性
1. **传统模型字典**: 保持向后兼容，新模型同时保存到内存和数据库
2. **BaseModelService**: 自动注册到统一的模型服务架构
3. **环境变量**: 自动设置和恢复API密钥等环境变量
4. **用户系统**: 支持多用户隔离，基于cookie中的user_id

### 启动流程
1. 连接MongoDB数据库
2. 创建必要的索引
3. 恢复默认用户的模型配置到环境变量
4. 启动FastAPI服务

## 🛠️ 开发和调试

### 查看数据库中的模型配置
```javascript
// 在MongoDB Compass中查询
db.user_models.find({"user_id": "default_user", "is_active": true})
```

### 手动恢复环境变量
```python
# 在Python中
from services.mongodb_service import mongodb_service
import asyncio

async def restore_env():
    await mongodb_service.connect()
    env_vars = await mongodb_service.restore_models_to_environment("default_user")
    print(f"恢复了 {len(env_vars)} 个环境变量")

asyncio.run(restore_env())
```

### 查看日志
```bash
# 启动后端时查看日志
cd software_aibot/backend
python main.py

# 查找模型相关日志
# ✅ 从MongoDB获取到 X 个用户模型
# ✅ 模型配置已保存到MongoDB: model_id for user: user_id
# ✅ 已恢复 X 个模型环境变量
```

## 📋 最佳实践

### 1. 数据备份
- 定期导出用户模型配置
- 使用MongoDB的备份功能

### 2. 性能优化
- 利用已创建的索引进行高效查询
- 定期清理软删除的模型配置

### 3. 安全性
- API密钥在前端显示时使用 `***hidden***` 掩码
- 支持用户级别的访问控制

### 4. 扩展性
- 支持模型配置版本控制（config_version字段）
- 可以轻松添加新的模型属性

## 🎉 总结

MongoDB模型配置管理系统为用户提供了：
- **持久化存储**: 模型配置在服务重启后不会丢失
- **多用户支持**: 每个用户拥有独立的模型配置空间
- **无缝集成**: 与现有的BaseModelService架构完美融合
- **丰富的API**: 提供完整的CRUD操作和统计功能
- **数据安全**: 软删除机制和用户隔离保证数据安全

现在您可以放心地添加自定义模型，系统会自动处理所有的持久化和恢复工作！ 