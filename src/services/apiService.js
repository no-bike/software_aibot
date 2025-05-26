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
export const sendMessage = async (message, modelIds, conversationId) => {
  try {
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
  } catch (error) {
    console.error('Error sending message:', error);
    throw error;
  }
}; 