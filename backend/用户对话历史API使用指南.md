# 基于用户的对话历史 API 使用示例

## 🔧 API 端点说明

### 1. 获取特定用户的会话列表
```
GET /api/users/{user_id}/conversations
```

**示例请求：**
```javascript
// 获取用户 "user123" 的所有会话
fetch('http://localhost:8000/api/users/user123/conversations')
  .then(response => response.json())
  .then(data => {
    console.log('用户会话列表:', data.conversations);
  });
```

**响应示例：**
```json
{
  "conversations": [
    {
      "id": "conv_20250615_001",
      "title": "关于AI的讨论",
      "models": ["deepseek-chat"],
      "createdAt": "2025-06-15T10:30:00",
      "messageCount": 5,
      "updatedAt": "2025-06-15T11:30:00",
      "userId": "user123"
    }
  ]
}
```

### 2. 获取特定用户的会话详情（包含消息）
```
GET /api/users/{user_id}/conversations/{conversation_id}
```

**示例请求：**
```javascript
// 获取用户 "user123" 的特定会话详情
fetch('http://localhost:8000/api/users/user123/conversations/conv_20250615_001')
  .then(response => response.json())
  .then(data => {
    console.log('会话详情:', data.conversation);
    console.log('消息列表:', data.conversation.messages);
  });
```

**响应示例：**
```json
{
  "conversation": {
    "id": "conv_20250615_001",
    "title": "关于AI的讨论",
    "models": ["deepseek-chat"],
    "createdAt": "2025-06-15T10:30:00",
    "userId": "user123",
    "messages": [
      {
        "role": "user",
        "content": "什么是人工智能？",
        "model": "",
        "timestamp": "2025-06-15T10:30:00"
      },
      {
        "role": "assistant",
        "content": "人工智能是...",
        "model": "deepseek-chat",
        "timestamp": "2025-06-15T10:30:15"
      }
    ]
  }
}
```

### 3. 发送消息（包含用户ID）
```
POST /api/chat
```

**示例请求：**
```javascript
// 发送消息时包含用户ID
fetch('http://localhost:8000/api/chat', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    message: "你好，AI助手！",
    modelIds: ["deepseek-chat"],
    conversationId: "conv_20250615_001",
    userId: "user123"  // 指定用户ID
  })
});
```

### 4. 删除特定用户的会话
```
DELETE /api/users/{user_id}/conversations/{conversation_id}
```

**示例请求：**
```javascript
// 删除用户 "user123" 的特定会话
fetch('http://localhost:8000/api/users/user123/conversations/conv_20250615_001', {
  method: 'DELETE'
})
.then(response => response.json())
.then(data => {
  console.log('删除结果:', data);
});
```

### 5. 获取用户统计信息
```
GET /api/users/{user_id}/stats
```

**示例请求：**
```javascript
// 获取用户统计信息
fetch('http://localhost:8000/api/users/user123/stats')
  .then(response => response.json())
  .then(data => {
    console.log('用户统计:', data.stats);
  });
```

**响应示例：**
```json
{
  "stats": {
    "userId": "user123",
    "conversationCount": 10,
    "totalMessages": 50,
    "lastActivity": "2025-06-15T11:30:00"
  }
}
```

## 🎨 前端集成示例

### React 组件示例
```javascript
import React, { useState, useEffect } from 'react';

const UserConversations = ({ userId }) => {
  const [conversations, setConversations] = useState([]);
  const [selectedConversation, setSelectedConversation] = useState(null);

  // 获取用户会话列表
  useEffect(() => {
    fetchUserConversations();
  }, [userId]);

  const fetchUserConversations = async () => {
    try {
      const response = await fetch(`/api/users/${userId}/conversations`);
      const data = await response.json();
      setConversations(data.conversations);
    } catch (error) {
      console.error('获取会话列表失败:', error);
    }
  };

  const fetchConversationDetail = async (conversationId) => {
    try {
      const response = await fetch(`/api/users/${userId}/conversations/${conversationId}`);
      const data = await response.json();
      setSelectedConversation(data.conversation);
    } catch (error) {
      console.error('获取会话详情失败:', error);
    }
  };

  const deleteConversation = async (conversationId) => {
    try {
      await fetch(`/api/users/${userId}/conversations/${conversationId}`, {
        method: 'DELETE'
      });
      // 刷新会话列表
      fetchUserConversations();
    } catch (error) {
      console.error('删除会话失败:', error);
    }
  };

  return (
    <div>
      <h2>用户 {userId} 的对话历史</h2>
      
      {/* 会话列表 */}
      <div className="conversations-list">
        {conversations.map(conv => (
          <div key={conv.id} className="conversation-item">
            <h3 onClick={() => fetchConversationDetail(conv.id)}>
              {conv.title}
            </h3>
            <p>消息数: {conv.messageCount}</p>
            <p>更新时间: {new Date(conv.updatedAt).toLocaleString()}</p>
            <button onClick={() => deleteConversation(conv.id)}>
              删除
            </button>
          </div>
        ))}
      </div>

      {/* 会话详情 */}
      {selectedConversation && (
        <div className="conversation-detail">
          <h3>{selectedConversation.title}</h3>
          <div className="messages">
            {selectedConversation.messages.map((msg, index) => (
              <div key={index} className={`message ${msg.role}`}>
                <strong>{msg.role}:</strong> {msg.content}
                <span className="timestamp">
                  {new Date(msg.timestamp).toLocaleString()}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default UserConversations;
```

### 使用组件
```javascript
// 在主应用中使用
function App() {
  const currentUserId = "user123"; // 从认证系统获取
  
  return (
    <div>
      <UserConversations userId={currentUserId} />
    </div>
  );
}
```

## 🔐 用户认证集成

如果您有用户认证系统，可以这样集成：

```javascript
// 从JWT token或session中获取用户ID
const getUserId = () => {
  const token = localStorage.getItem('authToken');
  if (token) {
    const decoded = jwt.decode(token);
    return decoded.userId;
  }
  return 'anonymous';
};

// 在发送消息时自动包含用户ID
const sendMessage = async (message, modelIds, conversationId) => {
  const userId = getUserId();
  
  const response = await fetch('/api/chat', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${localStorage.getItem('authToken')}`
    },
    body: JSON.stringify({
      message,
      modelIds,
      conversationId,
      userId
    })
  });
  
  return response.json();
};
```

## 🎯 使用场景

1. **多用户系统**: 每个用户只能看到自己的对话历史
2. **权限控制**: 确保用户只能访问自己的数据
3. **数据隔离**: 不同用户的数据完全分离
4. **用户统计**: 可以统计每个用户的使用情况
5. **数据导出**: 可以导出特定用户的所有对话记录
