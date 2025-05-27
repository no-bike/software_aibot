# API 接口文档

## 基础信息
- 基础URL: `http://localhost:8000/api`
- 所有请求和响应均使用 JSON 格式
- 所有接口都支持 CORS，允许来自 `http://localhost:3000` 的请求

## 1. 模型管理接口

### 1.1 获取所有模型
```http
GET /api/models
```

**响应示例：**
```json
[
  {
    "id": "gpt-3.5-turbo",
    "name": "GPT-3.5 Turbo",
    "apiKey": "",
    "url": "https://api.openai.com/v1"
  },
  {
    "id": "gpt-4",
    "name": "GPT-4",
    "apiKey": "",
    "url": "https://api.openai.com/v1"
  }
]
```

### 1.2 添加新模型
```http
POST /api/models
```

**请求体：**
```json
{
  "id": "string",
  "name": "string",
  "apiKey": "string",
  "url": "string"
}
```

**响应示例：**
```json
{
  "id": "custom-model",
  "name": "Custom Model",
  "apiKey": "sk-...",
  "url": "https://api.example.com/v1"
}
```

**错误响应：**
- 400: Model ID already exists

### 1.3 更新模型选择
```http
POST /api/models/selection
```

**请求体：**
```json
["model-id-1", "model-id-2"]
```

**响应示例：**
```json
{
  "selected_models": ["model-id-1", "model-id-2"]
}
```

## 2. 聊天接口

### 2.1 发送消息
```http
POST /api/chat
```

**请求体：**
```json
{
  "message": "string",
  "modelIds": ["string"],
  "conversationId": "string" // 可选
}
```

**响应示例：**
```json
{
  "responses": [
    {
      "modelId": "gpt-3.5-turbo",
      "content": "This is a response from GPT-3.5 Turbo"
    },
    {
      "modelId": "gpt-4",
      "content": "This is a response from GPT-4"
    }
  ]
}
```

## 数据模型

### Model
```typescript
interface Model {
  id: string;
  name: string;
  apiKey: string;
  url: string;
}
```

### Message
```typescript
interface Message {
  content: string;
  role: string;
  timestamp: string;
}
```

### Conversation
```typescript
interface Conversation {
  id: string;
  title: string;
  messages: Message[];
  models: string[];
}
```

### ModelResponse
```typescript
interface ModelResponse {
  modelId: string;
  content: string;
}
```

### MessageRequest
```typescript
interface MessageRequest {
  message: string;
  modelIds: string[];
  conversationId?: string;
}
```

## 前端使用示例

### 获取模型列表
```javascript
const models = await getModels();
```

### 添加新模型
```javascript
const newModel = await addModel({
  id: "custom-model",
  name: "Custom Model",
  apiKey: "sk-...",
  url: "https://api.example.com/v1"
});
```

### 更新模型选择
```javascript
await updateModelSelection(["gpt-3.5-turbo", "gpt-4"]);
```

### 发送消息
```javascript
const response = await sendMessage(
  "Hello, how are you?",
  ["gpt-3.5-turbo", "gpt-4"],
  "conversation-123"
);
```

## 错误处理
所有接口在发生错误时会返回适当的 HTTP 状态码和错误信息。前端代码中已经包含了基本的错误处理逻辑，会通过 `console.error` 输出错误信息。

## 注意事项
1. 所有请求都需要设置 `Content-Type: application/json` 头
2. 模型 ID 必须是唯一的
3. 发送消息时，`modelIds` 数组不能为空
4. 所有时间戳使用 ISO 格式字符串 