const API_BASE_URL = 'http://localhost:8000/api';

// 添加新模型
export const addModel = async (model) => {
  try {
    const response = await fetch(`${API_BASE_URL}/models`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(model),
    });
    
    if (!response.ok) {
      throw new Error('Failed to add model');
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error adding model:', error);
    throw error;
  }
};

// 获取所有模型
export const getModels = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/models`);
    
    if (!response.ok) {
      throw new Error('Failed to fetch models');
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error fetching models:', error);
    throw error;
  }
};

// 更新模型选择
export const updateModelSelection = async (modelIds) => {
  try {
    const response = await fetch(`${API_BASE_URL}/models/selection`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(modelIds),
    });
    
    if (!response.ok) {
      throw new Error('Failed to update model selection');
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error updating model selection:', error);
    throw error;
  }
};

// 发送消息并获取回答
export const sendMessage = async (message, modelIds, conversationId, onStream) => {
  try {
    // 单个模型时使用流式响应
    if (modelIds.length === 1 && onStream) {
      const response = await fetch(`${API_BASE_URL}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message,
          modelIds,
          conversationId,
        }),
      });
      
      if (!response.ok) {
        throw new Error('Failed to send message');
      }
      
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let result = '';
      let hasContent = false;
      
      // 显示思考中提示
      onStream("思考中...");
      
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        const chunk = decoder.decode(value, { stream: true });
        // 解析SSE格式数据
        const lines = chunk.split('\n');
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.substring(6).trim();
            if (data === '[DONE]') continue;
            
            try {
              const json = JSON.parse(data);
              if (json.choices && json.choices[0].delta.content) {
                const content = json.choices[0].delta.content;
                result += content;
                if (!hasContent && content.trim()) {
                  hasContent = true;
                  // 第一次收到有效内容时清空思考中提示
                  onStream(content);
                } else {
                  onStream(content);
                }
              }
            } catch (e) {
              console.log('Failed to parse SSE data:', e);
            }
          }
        }
      }
      
      return { responses: [{ modelId: modelIds[0], content: result }] };
    } 
    // 多个模型时保持原样
    else {
      const response = await fetch(`${API_BASE_URL}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message,
          modelIds,
          conversationId,
        }),
      });
      
      if (!response.ok) {
        throw new Error('Failed to send message');
      }
      
      return await response.json();
    }
  } catch (error) {
    console.error('Error sending message:', error);
    throw error;
  }
};

// 融合多个模型的回答
export const fusionResponses = async (responses, conversationId) => {
  try {
    const response = await fetch(`${API_BASE_URL}/fusion`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        responses,
        conversationId,
      }),
    });
    
    if (!response.ok) {
      throw new Error('Failed to fusion responses');
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error fusion responses:', error);
    throw error;
  }
};
