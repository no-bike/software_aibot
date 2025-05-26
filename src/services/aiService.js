// 从localStorage获取模型配置
const getModelConfig = (modelId) => {
  const models = JSON.parse(localStorage.getItem('aiModels') || '[]');
  return models.find(model => model.id === modelId);
};

// 发送消息到AI模型
export const sendMessage = async (modelId, messages) => {
  const modelConfig = getModelConfig(modelId);
  
  if (!modelConfig) {
    throw new Error('Model configuration not found');
  }

  // 根据不同模型类型构建不同的API请求
  switch (modelId) {
    case 'gpt-3.5-turbo':
    case 'gpt-4':
      return sendToOpenAI(modelConfig.apiKey, modelId, messages);
    case 'claude-2':
      return sendToClaude(modelConfig.apiKey, messages);
    default:
      // 对于自定义模型，使用通用API调用
      return sendToCustomModel(modelConfig.apiKey, modelId, messages);
  }
};

// OpenAI API调用
const sendToOpenAI = async (apiKey, model, messages) => {
  const response = await fetch('https://api.openai.com/v1/chat/completions', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${apiKey}`
    },
    body: JSON.stringify({
      model: model,
      messages: messages.map(msg => ({
        role: msg.role,
        content: msg.content
      }))
    })
  });

  if (!response.ok) {
    throw new Error('OpenAI API request failed');
  }

  const data = await response.json();
  return data.choices[0].message.content;
};

// Claude API调用
const sendToClaude = async (apiKey, messages) => {
  const response = await fetch('https://api.anthropic.com/v1/messages', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'x-api-key': apiKey,
      'anthropic-version': '2023-06-01'
    },
    body: JSON.stringify({
      model: 'claude-2',
      messages: messages.map(msg => ({
        role: msg.role,
        content: msg.content
      }))
    })
  });

  if (!response.ok) {
    throw new Error('Claude API request failed');
  }

  const data = await response.json();
  return data.content[0].text;
};

// 自定义模型API调用
const sendToCustomModel = async (apiKey, modelId, messages) => {
  // 这里可以根据自定义模型的API规范进行实现
  // 示例实现：
  const response = await fetch('YOUR_CUSTOM_API_ENDPOINT', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${apiKey}`
    },
    body: JSON.stringify({
      model: modelId,
      messages: messages
    })
  });

  if (!response.ok) {
    throw new Error('Custom model API request failed');
  }

  const data = await response.json();
  return data.response;
}; 