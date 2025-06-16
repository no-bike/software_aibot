# MongoDB 安装和使用指南

## 🚀 1. 安装 MongoDB

### 方法一：MongoDB Community Server（推荐）
1. 访问：https://www.mongodb.com/try/download/community
2. 选择 Windows 版本下载
3. 运行安装程序，选择 "Complete" 安装
4. 勾选 "Install MongoDB as a Service"
5. 勾选 "Install MongoDB Compass"（图形化界面）

### 方法二：使用 Docker（简单）
```bash
# 拉取 MongoDB 镜像
docker pull mongo:latest

# 运行 MongoDB 容器
docker run -d --name mongodb -p 27017:27017 -v mongodb_data:/data/db mongo:latest
```

## 🖥️ 2. MongoDB Compass 图形化界面使用

### 连接数据库
1. 打开 MongoDB Compass
2. 连接字符串：`mongodb://localhost:27017`
3. 点击 "Connect"

### 查看聊天数据
1. **数据库**: `chatbot_db`
2. **集合**: 
   - `conversations` - 存储会话信息
   - `messages` - 存储消息内容

### 常用操作
- **查看会话列表**: 点击 `conversations` 集合
- **查看消息**: 点击 `messages` 集合
- **搜索**: 使用 Filter 功能，例如：
  ```json
  {"conversation_id": "你的会话ID"}
  ```
- **删除数据**: 选中文档，点击删除图标

## 🔧 3. 启动应用

### 设置环境变量
编辑 `backend/.env` 文件：
```env
MONGODB_URL=mongodb://localhost:27017
MONGODB_DB_NAME=chatbot_db
```

### 启动后端
```bash
cd backend
python main.py
```

## 📊 4. 数据库结构

### conversations 集合结构
```json
{
  "_id": ObjectId("..."),
  "conversation_id": "会话唯一ID",
  "title": "会话标题",
  "models": ["使用的模型列表"],
  "created_at": "创建时间",
  "updated_at": "更新时间",
  "message_count": 消息数量
}
```

### messages 集合结构
```json
{
  "_id": ObjectId("..."),
  "conversation_id": "所属会话ID",
  "role": "user/assistant",
  "content": "消息内容",
  "model": "模型名称",
  "timestamp": "时间戳",
  "created_at": "创建时间"
}
```

## 🛠️ 5. 常见问题解决

### 连接失败
1. 确保 MongoDB 服务正在运行
2. 检查端口 27017 是否被占用
3. 确认防火墙设置

### 数据未保存
1. 检查日志输出
2. 确认环境变量设置正确
3. 检查 MongoDB 服务状态

### 性能优化
1. MongoDB Compass 中查看索引使用情况
2. 根据查询模式创建合适的索引
3. 定期清理过期数据

## 📋 6. MongoDB Compass 界面说明

### 主界面
- **左侧**: 数据库和集合列表
- **中间**: 文档浏览器
- **右侧**: 文档详情

### 查询功能
- **Filter**: 过滤条件
- **Project**: 选择显示字段
- **Sort**: 排序
- **Limit**: 限制结果数量

### 实用功能
- **Export**: 导出数据
- **Import**: 导入数据
- **Index**: 管理索引
- **Schema**: 查看数据结构

## 🎯 7. 开发调试技巧

### 查看最近的会话
```json
// 在 conversations 集合的 Filter 中输入
{"updated_at": {"$gte": "2025-06-15"}}
```

### 查看特定用户的消息
```json
// 在 messages 集合的 Filter 中输入
{"role": "user", "timestamp": {"$gte": "2025-06-15T00:00:00"}}
```

### 统计消息数量
点击 "Aggregations" 标签，创建聚合管道
