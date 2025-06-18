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
      credentials: 'include'
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
    const response = await fetch(`${API_BASE_URL}/models`, {
      credentials: 'include'
    });
    
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
      credentials: 'include'
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
export const sendMessage = async (message, modelIds, conversationId, onStream, onMultiModelStream) => {
  try {
    // 使用流式响应（单个或多个模型）
    if (onStream || onMultiModelStream) {
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
        credentials: 'include'
      });
      
      if (!response.ok) {
        throw new Error('Failed to send message');
      }
      
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let result = '';
      let hasContent = false;
      
      // 单个模型的处理逻辑
      if (modelIds.length === 1 && onStream) {
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
      // 多个模型的流式处理逻辑
      else if (modelIds.length > 1 && onMultiModelStream) {
        const modelResponses = {};
        let completedModels = 0;
        const totalModels = modelIds.length;
        
        // 显示开始提示
        onMultiModelStream({
          type: 'start',
          message: `正在并发调用 ${totalModels} 个模型...`,
          models: modelIds
        });
        
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          
          const chunk = decoder.decode(value, { stream: true });
          const lines = chunk.split('\n');
          
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const data = line.substring(6).trim();
              if (data === '[DONE]') continue;
              
              try {
                const json = JSON.parse(data);
                
                if (json.type === 'start') {
                  console.log('🚀 多模型并发开始:', json);
                  
                } else if (json.type === 'model_start') {
                  console.log(`🤔 模型 ${json.modelId} 开始思考`);
                  onMultiModelStream({
                    type: 'model_start',
                    modelId: json.modelId,
                    message: json.message
                  });
                  
                } else if (json.type === 'model_chunk') {
                  // 实时流式数据块
                  onMultiModelStream({
                    type: 'model_chunk',
                    modelId: json.modelId,
                    chunk: json.chunk,
                    accumulated: json.accumulated
                  });
                  
                } else if (json.type === 'model_complete') {
                  console.log(`✅ 模型 ${json.modelId} 完成响应`);
                  
                  // 保存模型响应
                  modelResponses[json.modelId] = {
                    modelId: json.modelId,
                    content: json.content,
                    status: json.status
                  };
                  
                  // 通知前端模型完成
                  onMultiModelStream({
                    type: 'model_complete',
                    modelId: json.modelId,
                    content: json.content,
                    status: json.status
                  });
                  
                } else if (json.type === 'all_complete') {
                  console.log('🎉 所有模型响应完成');
                  onMultiModelStream({
                    type: 'all_complete',
                    message: json.message,
                    responses: Object.values(modelResponses)
                  });
                }
              } catch (e) {
                console.log('Failed to parse multi-model SSE data:', e);
              }
            }
          }
        }
        
        return { responses: Object.values(modelResponses) };
      }
    } 
    // 兜底：非流式响应（不应该到达这里）
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
        credentials: 'include'
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

// 删除模型
export const deleteModel = async (modelId) => {
  try {
    const response = await fetch(`${API_BASE_URL}/models/${modelId}`, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include'
    });
    
    if (!response.ok) {
      throw new Error('Failed to delete model');
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error deleting model:', error);
    throw error;
  }
};

// 融合多个模型的回答
export const fusionResponses = async (responses, conversationId, userQuery = "请根据多个AI助手的回答，提供最优的综合答案。") => {
  try {
    console.log('🚀 开始调用融合API...');
    console.log('📊 输入参数:', { responses: responses.length, conversationId, userQuery });
    
    // 优先尝试高级融合API (LLM-Blender)
    try {
      console.log('🎯 尝试调用高级融合API...');
      const advancedResponse = await fetch(`${API_BASE_URL}/fusion/advanced`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: userQuery,
          responses,
          conversationId,
          fusionMethod: "rank_and_fuse",
          topK: Math.min(3, responses.length)
        }),
        credentials: 'include'
      });
      
      if (advancedResponse.ok) {
        const result = await advancedResponse.json();
        console.log('✅ 高级融合API调用成功:', result);
        return result;
      } else {
        const errorText = await advancedResponse.text();
        console.warn('⚠️ 高级融合API失败，尝试传统融合:', errorText);
      }
    } catch (advancedError) {
      console.warn('⚠️ 高级融合API异常，尝试传统融合:', advancedError);
    }
    
    // 降级到传统融合API
    console.log('🔄 调用传统融合API...');
    const response = await fetch(`${API_BASE_URL}/fusion`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        responses,
        conversationId,
      }),
      credentials: 'include'
    });
    
    if (!response.ok) {
      const errorText = await response.text();
      console.error('❌ 传统融合API也失败:', errorText);
      throw new Error(`融合API调用失败: ${response.status} - ${errorText}`);
    }
    
    const result = await response.json();
    console.log('✅ 传统融合API调用成功:', result);
    return result;
    
  } catch (error) {
    console.error('❌ 融合回答完全失败:', error);
    throw error;
  }
};

// 获取所有会话历史
export const getConversations = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/conversations`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include'
    });
    
    if (!response.ok) {
      throw new Error('Failed to fetch conversations');
    }
    
    const data = await response.json();
    return data.conversations || [];
  } catch (error) {
    console.error('Error fetching conversations:', error);
    throw error;
  }
};

// 获取单个会话详情
export const getConversationDetail = async (conversationId) => {
  try {
    const response = await fetch(`${API_BASE_URL}/conversations/${conversationId}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include'
    });
    
    if (!response.ok) {
      throw new Error('Failed to fetch conversation detail');
    }
    
    const data = await response.json();
    return data.conversation;
  } catch (error) {
    console.error('Error fetching conversation detail:', error);
    throw error;
  }
};

// 更新会话标题
export const updateConversationTitle = async (conversationId, title) => {
  try {
    const response = await fetch(`${API_BASE_URL}/conversations/${conversationId}/title`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ title }),
      credentials: 'include'
    });
    
    if (!response.ok) {
      throw new Error('Failed to update conversation title');
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error updating conversation title:', error);
    throw error;
  }
};

// 删除会话
export const deleteConversation = async (conversationId) => {
  try {
    const response = await fetch(`${API_BASE_URL}/conversations/${conversationId}`, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include'
    });
    
    if (!response.ok) {
      throw new Error('Failed to delete conversation');
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error deleting conversation:', error);
    throw error;
  }
};

// 分享会话
export const shareConversation = async (conversationId) => {
  try {
    const response = await fetch(`${API_BASE_URL}/conversations/${conversationId}/share`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include'
    });
    
    if (!response.ok) {
      throw new Error('Failed to share conversation');
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error sharing conversation:', error);
    throw error;
  }
};

// 获取分享的会话
export const getSharedConversation = async (shareId) => {
  try {
    const response = await fetch(`${API_BASE_URL}/shared/${shareId}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      }
    });
    
    if (!response.ok) {
      throw new Error('Failed to fetch shared conversation');
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error fetching shared conversation:', error);
    throw error;
  }
};

// 获取用户分享的所有会话
export const getUserSharedConversations = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/shared`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include'
    });
    
    if (!response.ok) {
      throw new Error('Failed to fetch shared conversations');
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error fetching shared conversations:', error);
    throw error;
  }
};

// 删除分享
export const deleteShare = async (shareId) => {
  try {
    const response = await fetch(`${API_BASE_URL}/shared/${shareId}`, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include'
    });
    
    if (!response.ok) {
      throw new Error('Failed to delete share');
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error deleting share:', error);
    throw error;
  }
};
