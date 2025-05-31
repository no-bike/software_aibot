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

## 3. 融合接口

### 3.1 传统融合
```http
POST /api/fusion
```

**请求体：**
```json
{
  "responses": [
    {
      "modelId": "string",
      "content": "string"
    }
  ],
  "conversationId": "string" // 可选
}
```

**响应示例：**
```json
{
  "fusedContent": "融合后的回答内容"
}
```

### 3.2 高级融合（LLM-Blender）
```http
POST /api/fusion/advanced
```

**请求体：**
```json
{
  "query": "用户的原始问题",
  "responses": [
    {
      "modelId": "deepseek-chat",
      "content": "DeepSeek的回答"
    },
    {
      "modelId": "sparkx1", 
      "content": "SparkX1的回答"
    }
  ],
  "fusionMethod": "rank_and_fuse", // 可选: "rank_only", "fuse_only", "rank_and_fuse"
  "topK": 3, // 可选: 用于融合的top-k回答数量
  "conversationId": "string" // 可选
}
```

**响应示例：**
```json
{
  "fusedContent": "基于LLM-Blender智能融合的最优回答",
  "rankedResponses": [
    {
      "modelId": "deepseek-chat",
      "content": "DeepSeek的回答",
      "rank": 1,
      "quality_score": 2
    },
    {
      "modelId": "sparkx1",
      "content": "SparkX1的回答", 
      "rank": 2,
      "quality_score": 1
    }
  ],
  "bestResponse": {
    "modelId": "deepseek-chat",
    "content": "DeepSeek的回答",
    "rank": 1,
    "quality_score": 2
  },
  "fusionMethod": "rank_and_fuse",
  "modelsUsed": ["deepseek-chat", "sparkx1"],
  "processingTime": 2.34,
  "error": null
}
```

**融合方法说明：**
- `rank_only`: 仅进行质量排序，返回排名最高的回答
- `fuse_only`: 仅进行生成融合，不排序  
- `rank_and_fuse`: 先排序再融合（推荐）

### 3.3 融合服务状态
```http
GET /api/fusion/status
```

**响应示例：**
```json
{
  "llm_blender_available": true,
  "ranker_loaded": true,
  "fuser_loaded": true,
  "is_initialized": true,
  "supported_methods": ["rank_only", "fuse_only", "rank_and_fuse"],
  "recommended_method": "rank_and_fuse"
}
```

**服务不可用时的响应：**
```json
{
  "llm_blender_available": false,
  "ranker_loaded": false,
  "fuser_loaded": false,
  "is_initialized": false,
  "error": "错误信息",
  "fallback_available": true,
  "supported_methods": ["traditional_fusion"]
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
  rank?: number; // 高级融合时的质量排名
  quality_score?: number; // 高级融合时的质量分数
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

### AdvancedFusionRequest
```typescript
interface AdvancedFusionRequest {
  query: string;
  responses: Array<{modelId: string, content: string}>;
  fusionMethod?: "rank_only" | "fuse_only" | "rank_and_fuse";
  topK?: number;
  conversationId?: string;
}
```

### AdvancedFusionResponse
```typescript
interface AdvancedFusionResponse {
  fusedContent: string;
  rankedResponses: ModelResponse[];
  bestResponse?: ModelResponse;
  fusionMethod: string;
  modelsUsed: string[];
  processingTime: number;
  error?: string;
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

### 传统融合
```javascript
const fusionResponse = await fetch('/api/fusion', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    responses: [
      {modelId: "deepseek-chat", content: "回答1"},
      {modelId: "sparkx1", content: "回答2"}
    ],
    conversationId: "conversation-123"
  })
});
```

### 高级融合（LLM-Blender）
```javascript
const advancedFusion = await fetch('/api/fusion/advanced', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    query: "用户的原始问题",
    responses: [
      {modelId: "deepseek-chat", content: "DeepSeek的回答"},
      {modelId: "sparkx1", content: "SparkX1的回答"}
    ],
    fusionMethod: "rank_and_fuse",
    topK: 3,
    conversationId: "conversation-123"
  })
});

const result = await advancedFusion.json();
console.log("融合结果:", result.fusedContent);
console.log("最佳回答:", result.bestResponse);
console.log("处理时间:", result.processingTime);
```

### 检查融合服务状态
```javascript
const status = await fetch('/api/fusion/status').then(res => res.json());
if (status.llm_blender_available) {
  console.log("LLM-Blender 可用，推荐方法:", status.recommended_method);
} else {
  console.log("降级到传统融合");
}
```

## 错误处理
所有接口在发生错误时会返回适当的 HTTP 状态码和错误信息。前端代码中已经包含了基本的错误处理逻辑，会通过 `console.error` 输出错误信息。

## LLM-Blender 特性
- **智能排序**: 使用PairRM模型对多个AI回答进行质量评估和排序
- **生成融合**: 使用GenFuser模型将最优回答融合生成更好的答案  
- **多种模式**: 支持仅排序、仅融合、排序+融合三种模式
- **自动降级**: 当LLM-Blender不可用时自动降级到传统融合方法
- **性能优化**: CPU模式运行，避免GPU依赖，适合生产环境部署

## 注意事项
1. 所有请求都需要设置 `Content-Type: application/json` 头
2. 模型 ID 必须是唯一的
3. 发送消息时，`modelIds` 数组不能为空
4. 所有时间戳使用 ISO 格式字符串
5. 高级融合需要安装LLM-Blender依赖，首次使用会自动下载模型文件（约1.7GB）
6. 推荐在生产环境中先调用 `/api/fusion/status` 检查服务状态 