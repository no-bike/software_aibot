import React, { useState, useMemo, useEffect, useRef } from 'react';
import { 
  Box, 
  Container, 
  TextField, 
  Button, 
  Paper, 
  Typography,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  List,
  ListItem,
  ListItemText,
  Divider,
  IconButton,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  InputAdornment,
  Chip,
  Switch,
  FormControlLabel,
  keyframes,
  ThemeProvider,
  CssBaseline,
  AppBar,
  Toolbar,
  Snackbar,
  Alert,
  Avatar,
  Drawer,
  ListItemButton,
  ListItemIcon,
  CircularProgress,
  Menu,
  Fab
} from '@mui/material';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  Send as SendIcon,
  Add as AddIcon,
  Settings as SettingsIcon,
  DarkMode as DarkModeIcon,
  LightMode as LightModeIcon,
  Delete as DeleteIcon,
  Edit as EditIcon,
  Share as ShareIcon,
  Visibility as VisibilityIcon,
  ContentCopy as ContentCopyIcon,
  LightbulbOutlined as LightbulbIcon
} from '@mui/icons-material';
import HistoryIcon from '@mui/icons-material/History';
import SearchIcon from '@mui/icons-material/Search';
import ClearIcon from '@mui/icons-material/Clear';
import LogoutIcon from '@mui/icons-material/Logout';
import ShareListIcon from '@mui/icons-material/List';
import Settings from './components/Settings';
import Login from './components/Login';
import Register from './components/Register';
import darkTheme from './theme/darkTheme';
import lightTheme from './theme/lightTheme';
import { getModels, updateModelSelection, sendMessage as sendMessageToAPI, fusionResponses, getConversations, deleteConversation as deleteConversationAPI, getConversationDetail, updateConversationTitle, getUserSharedConversations, deleteShare } from './services/apiService';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import ShareDialog from './components/ShareDialog';
import SharedConversation from './components/SharedConversation';
import PromptHelper from './components/PromptHelper';

// 跳动点动画
const bounce = keyframes`
  0%, 60%, 100% {
    animation-timing-function: cubic-bezier(0.215, 0.610, 0.355, 1.000);
    transform: translateY(0);
  }
  30% {
    animation-timing-function: cubic-bezier(0.755, 0.050, 0.855, 0.060);
    transform: translateY(-8px);
  }
`;

// 跳动点组件
const TypingIndicator = () => (
  <Box
    sx={{
      display: 'flex',
      justifyContent: 'flex-start',
      mb: 2
    }}
  >
    <Paper
      sx={{
        p: 2,
        maxWidth: '70%',
        backgroundColor: 'grey.100',
        display: 'flex',
        alignItems: 'center',
        gap: 0.5
      }}
    >
      <Typography variant="body2" color="text.secondary" sx={{ mr: 1 }}>
        AI正在思考
      </Typography>
      {[0, 1, 2].map((index) => (
        <Box
          key={index}
          sx={{
            width: 6,
            height: 6,
            borderRadius: '50%',
            backgroundColor: 'primary.main',
            animation: `${bounce} 1.4s infinite`,
            animationDelay: `${index * 0.16}s`
          }}
        />
      ))}
    </Paper>
  </Box>
);

// 将主应用内容包装在一个新组件中
const MainApp = () => {
  const { user, logout } = useAuth();
  const [message, setMessage] = useState('');
  const [conversations, setConversations] = useState([]);
  const [currentConversationId, setCurrentConversationId] = useState(null);
  const [selectedModels, setSelectedModels] = useState([]);
  const [showHistory, setShowHistory] = useState(true);
  const [editingConversation, setEditingConversation] = useState(null);
  const [editTitle, setEditTitle] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [showSettings, setShowSettings] = useState(false);
  const [models, setModels] = useState([]);
  const [mergeResponses, setMergeResponses] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isLoadingResponse, setIsLoadingResponse] = useState(false);
  const [isCompletionLoading, setIsCompletionLoading] = useState(false);
  const [isDarkMode, setIsDarkMode] = useState(true);
  const messagesEndRef = useRef(null);
  const [streamingContent, setStreamingContent] = useState('');
  const [showShareDialog, setShowShareDialog] = useState(false);
  const [showSharedList, setShowSharedList] = useState(false);
  const [showViewSharedDialog, setShowViewSharedDialog] = useState(false);
  const [sharedConversations, setSharedConversations] = useState([]);
  const [sharedLink, setSharedLink] = useState('');
  const [sharedError, setSharedError] = useState('');
  const [deleteError, setDeleteError] = useState('');
  const [shareDialogOpen, setShareDialogOpen] = useState(false);
  const [shareUrl, setShareUrl] = useState('');
  const [isSharedView, setIsSharedView] = useState(false);
  const [sharedConversation, setSharedConversation] = useState(null);
  const [promptHelperOpen, setPromptHelperOpen] = useState(false);
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [userMessage, setUserMessage] = useState('');
  const [autoCompletions, setAutoCompletions] = useState([]);
  const [selectedCompletionIndex, setSelectedCompletionIndex] = useState(-1);
  const [showCompletions, setShowCompletions] = useState(false);
  const [completionMode, setCompletionMode] = useState('transformer'); // 'transformer', 'intelligent' 或 'template'
  const inputRef = useRef(null);
  const debounceTimerRef = useRef(null);

  // 新增：Transformer模型相关状态
  const [availableModels, setAvailableModels] = useState({});
  const [currentModel, setCurrentModel] = useState('auto');
  const [modelStatus, setModelStatus] = useState(null);
  const [modelLoading, setModelLoading] = useState(false);

  // 从API加载模型列表
  useEffect(() => {
    const loadModels = async () => {
      try {
        setLoading(true);
        setError(null);
        const savedModels = await getModels();
        setModels(savedModels);
        
        // 如果当前没有选中的模型，选择第一个
        if (selectedModels.length === 0 && savedModels.length > 0) {
          setSelectedModels([savedModels[0].id]);
        }
      } catch (error) {
        console.error('Error loading models:', error);
        setError('Failed to load models. Please try again later.');
      } finally {
        setLoading(false);
      }
    };

    loadModels();
  }, []);

  // 当模型选择变化时，通知后端
  useEffect(() => {
    const updateSelection = async () => {
      if (selectedModels.length > 0) {
        try {
          await updateModelSelection(selectedModels);
        } catch (error) {
          console.error('Error updating model selection:', error);
        }
      }
    };

    updateSelection();
  }, [selectedModels]);

  // 加载会话历史
  useEffect(() => {
    const loadConversations = async () => {
      try {
        const savedConversations = await getConversations();
        console.log('Loaded conversations from server:', savedConversations);
        setConversations(savedConversations);
      } catch (error) {
        console.error('Error loading conversations:', error);
        // 如果加载失败，保持空数组，不影响新会话的创建
      }
    };

    loadConversations();
  }, []);

  // 使用 useMemo 优化搜索性能
  const filteredConversations = useMemo(() => {
    if (!searchQuery.trim()) return conversations;
    
    const query = searchQuery.toLowerCase().trim();
    return conversations.filter(conv => 
      conv.title.toLowerCase().includes(query)
    );
  }, [conversations, searchQuery]);

  const createNewConversation = () => {
    const newConversation = {
      id: Date.now().toString(),  // 确保ID是字符串类型
      title: 'New Conversation',
      messages: [],
      models: selectedModels,
      createdAt: new Date().toISOString()
    };
    setConversations(prevConversations => [newConversation, ...prevConversations]);
    return newConversation.id;  // 返回新创建的对话ID
  };

  // 选择并加载会话详情
  const selectConversation = async (conversationId) => {
    try {
      console.log('Selecting conversation:', conversationId);
      
      // 先设置当前会话ID，避免在加载过程中UI显示异常
      setCurrentConversationId(conversationId);
      
      const conversationDetail = await getConversationDetail(conversationId);
      console.log('Loaded conversation detail:', conversationDetail);
      
      if (!conversationDetail) {
        console.warn('No conversation detail received');
        return;
      }
      
      // 更新conversations状态，将加载的消息合并到对应的会话中
      setConversations(prevConversations => {
        return prevConversations.map(conv => {
          if (conv.id === conversationId) {
            return {
              ...conv,
              messages: conversationDetail.messages || [],
              title: conversationDetail.title || conv.title,
              models: conversationDetail.models || conv.models
            };
          }
          return conv;
        });
      });
    } catch (error) {
      console.error('Error loading conversation detail:', error);
      // 如果加载失败，仍然设置当前会话ID，允许用户继续对话
      setCurrentConversationId(conversationId);
    }
  };

  const handleSend = async () => {
    if (!message.trim()) return;
    
    // 如果没有选择模型，显示错误
    if (selectedModels.length === 0) {
      const errorMessage = {
        role: 'assistant',
        content: '错误: 请先选择至少一个AI模型',
        model: 'error',
        timestamp: new Date().toISOString()
      };
      
      if (currentConversationId) {
        setConversations(prevConversations => {
          return prevConversations.map(conv => {
            if (conv.id === currentConversationId) {
              return {
                ...conv,
                messages: [...conv.messages, errorMessage]
              };
            }
            return conv;
          });
        });
      }
      return;
    }

    const currentMessage = message;
    setMessage('');  // 清空输入框
    setIsLoadingResponse(true); // 开始加载状态
    setStreamingContent(''); // 重置流式内容

    // 确保有对话ID
    let conversationId = currentConversationId;
    if (!conversationId) {
      conversationId = createNewConversation();
      setCurrentConversationId(conversationId);
    }

    // 创建用户消息
    const newMessage = {
      role: 'user',
      content: currentMessage,
      timestamp: new Date().toISOString()
    };

    // 立即更新对话
    setConversations(prevConversations => {
      return prevConversations.map(conv => {
        if (conv.id === conversationId) {
          return {
            ...conv,
            title: conv.messages.length === 0 ? currentMessage.slice(0, 30) + (currentMessage.length > 30 ? '...' : '') : conv.title,
            messages: [...conv.messages, newMessage],
            models: selectedModels
          };
        }
        return conv;
      });
    });

    try {
      console.log('发送消息:', {
        message: currentMessage,
        modelIds: selectedModels,
        conversationId: conversationId
      });

      // 单个模型时使用流式响应
      if (selectedModels.length === 1) {
        // 创建临时AI消息用于流式显示
        const tempAiMessage = {
          role: 'assistant',
          content: '',
          model: selectedModels[0],
          timestamp: new Date().toISOString()
        };

        // 先添加临时消息
        setConversations(prevConversations => {
          return prevConversations.map(conv => {
            if (conv.id === conversationId) {
              return {
                ...conv,
                messages: [...conv.messages, tempAiMessage]
              };
            }
            return conv;
          });
        });

        // 调用API发送消息（流式）
        const response = await sendMessageToAPI(
          currentMessage, 
          selectedModels, 
          conversationId,
          (chunk) => {
            setStreamingContent(prev => {
              const newContent = prev + chunk;
              // 更新临时消息内容
              setConversations(prevConversations => {
                return prevConversations.map(conv => {
                  if (conv.id === conversationId) {
                    const messages = [...conv.messages];
                    const lastMessage = messages[messages.length - 1];
                    if (lastMessage.role === 'assistant') {
                      messages[messages.length - 1] = {
                        ...lastMessage,
                        content: newContent
                      };
                    }
                    return {
                      ...conv,
                      messages: messages
                    };
                  }
                  return conv;
                });
              });
              return newContent;
            });
          }
        );

        // 流式结束后，确保最终内容正确
        if (response && response.responses && response.responses[0]) {
          setConversations(prevConversations => {
            return prevConversations.map(conv => {
              if (conv.id === conversationId) {
                const messages = [...conv.messages];
                const lastMessage = messages[messages.length - 1];
                if (lastMessage.role === 'assistant') {
                  messages[messages.length - 1] = {
                    ...lastMessage,
                    content: response.responses[0].content
                  };
                }
                return {
                  ...conv,
                  messages: messages
                };
              }
              return conv;
            });
          });
        }
      } 
      // 多个模型时保持原样
      else {
        // 调用API发送消息（非流式）
        const response = await sendMessageToAPI(currentMessage, selectedModels, conversationId);
        console.log('收到API响应:', response);

        if (!response || !response.responses) {
          throw new Error('服务器返回的响应格式不正确');
        }
        
        let aiMessages;
        if (mergeResponses && response.responses.length > 1) {
          try {
            // 调用融合API
            const fusionResult = await fusionResponses(response.responses, conversationId);
            aiMessages = [{
              role: 'assistant',
              content: fusionResult.fusedContent,
              model: 'fusion',
              timestamp: new Date().toISOString()
            }];
          } catch (fusionError) {
            console.error('融合回答失败:', fusionError);
            // 如果融合失败，回退到分别显示每个模型的回答
            aiMessages = response.responses.map(response => ({
              role: 'assistant',
              content: response.content,
              model: response.modelId,
              timestamp: new Date().toISOString()
            }));
          }
        } else {
          // 分别显示每个模型的回答
          aiMessages = response.responses.map(response => ({
            role: 'assistant',
            content: response.content,
            model: response.modelId,
            timestamp: new Date().toISOString()
          }));
        }

        console.log('处理后的AI消息:', aiMessages);

        // 更新对话内容
        setConversations(prevConversations => {
          return prevConversations.map(conv => {
            if (conv.id === conversationId) {
              const updatedMessages = [...conv.messages, ...aiMessages];
              return {
                ...conv,
                messages: updatedMessages
              };
            }
            return conv;
          });
        });
      }
    } catch (error) {
      console.error('发送消息时出错:', error);
      
      // 添加错误提示
      const errorMessage = {
        role: 'assistant',
        content: `错误: ${error.message || '无法获取AI响应'}`,
        model: 'error',
        timestamp: new Date().toISOString()
      };
      
      setConversations(prevConversations => {
        return prevConversations.map(conv => {
          if (conv.id === conversationId) {
            return {
              ...conv,
              messages: [...conv.messages, errorMessage]
            };
          }
          return conv;
        });
      });
    } finally {
      setIsLoadingResponse(false); // 结束加载状态
    }
  };

  const deleteConversation = async (conversationId) => {
    try {
      // 调用后端API删除会话
      await deleteConversationAPI(conversationId);
      console.log('Conversation deleted from server:', conversationId);
      
      // 从本地状态中删除
      setConversations(prevConversations => 
        prevConversations.filter(conv => conv.id !== conversationId)
      );
      
      // 如果删除的是当前会话，清除当前会话ID
      if (currentConversationId === conversationId) {
        setCurrentConversationId(null);
      }
    } catch (error) {
      console.error('Error deleting conversation:', error);
      // 如果API调用失败，仍然从本地删除（用户体验优先）
      setConversations(prevConversations => 
        prevConversations.filter(conv => conv.id !== conversationId)
      );
      if (currentConversationId === conversationId) {
        setCurrentConversationId(null);
      }
    }
  };

  const handleEditTitle = (conversation) => {
    setEditingConversation(conversation);
    setEditTitle(conversation.title);
  };

  const saveEditTitle = async () => {
    if (editingConversation && editTitle.trim()) {
      try {
        // 调用后端API更新标题
        await updateConversationTitle(editingConversation.id, editTitle.trim());
        console.log('Conversation title updated on server:', editingConversation.id);
        
        // 更新本地状态
        setConversations(prevConversations => 
          prevConversations.map(conv => 
            conv.id === editingConversation.id 
              ? { ...conv, title: editTitle.trim() }
              : conv
          )
        );
      } catch (error) {
        console.error('Error updating conversation title:', error);
        // 如果API调用失败，仍然在本地更新（用户体验优先）
        setConversations(prevConversations => 
          prevConversations.map(conv => 
            conv.id === editingConversation.id 
              ? { ...conv, title: editTitle.trim() }
              : conv
          )
        );
      }
    }
    setEditingConversation(null);
    setEditTitle('');
  };

  const getCurrentConversation = () => {
    return conversations.find(conv => conv.id === currentConversationId) || { messages: [] };
  };

  // 当消息变化时自动滚动到底部
  useEffect(() => {
    const container = document.querySelector('.messages-container');
    if (container) {
      container.scrollTo({
        top: container.scrollHeight,
        behavior: 'smooth'
      });
    }
  }, [currentConversationId, conversations]);

  const handleModelsUpdate = (updatedModels) => {
    setModels(updatedModels);
    // 如果当前没有选中的模型，选择第一个
    if (selectedModels.length === 0 && updatedModels.length > 0) {
      setSelectedModels([updatedModels[0].id]);
    }
  };

  // 加载分享的会话列表
  useEffect(() => {
    const loadSharedConversations = async () => {
      try {
        const data = await getUserSharedConversations();
        setSharedConversations(data.sharedConversations || []);
      } catch (error) {
        console.error('Error loading shared conversations:', error);
      }
    };

    if (showSharedList) {
      loadSharedConversations();
    }
  }, [showSharedList]);

  // 处理查看分享的会话
  const handleViewShared = async () => {
    if (!sharedLink.trim()) {
      setSharedError('请输入分享链接');
      return;
    }

    try {
      // 从链接中提取分享ID
      const shareId = sharedLink.split('/shared/')[1];
      if (!shareId) {
        setSharedError('无效的分享链接');
        return;
      }

      // 在新窗口打开分享的会话
      window.open(`/shared/${shareId}`, '_blank');
      setShowViewSharedDialog(false);
      setSharedLink('');
      setSharedError('');
    } catch (error) {
      setSharedError('无法打开分享的会话');
    }
  };

  // 处理删除分享
  const handleDeleteShare = async (shareId) => {
    try {
      await deleteShare(shareId);
      // 重新加载分享列表
      const data = await getUserSharedConversations();
      setSharedConversations(data.sharedConversations || []);
    } catch (error) {
      setDeleteError('删除分享失败，请稍后重试');
    }
  };

  // 处理分享功能
  const handleShare = async () => {
    if (messages.length === 0) {
      setError('没有对话内容可分享');
      return;
    }

    try {
      setIsLoading(true);
      
      const response = await fetch('http://localhost:8000/api/conversations/share', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({ messages })
      });

      if (response.ok) {
        const data = await response.json();
        setShareUrl(`${window.location.origin}/shared/${data.share_id}`);
        setShareDialogOpen(true);
      } else {
        const errorData = await response.json();
        setError(errorData.detail || '分享失败');
      }
    } catch (err) {
      setError('网络错误，请检查连接');
    } finally {
      setIsLoading(false);
    }
  };

  // 新增：获取可用模型列表
  const fetchAvailableModels = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/models/transformer/available', {
        credentials: 'include'
      });
      if (response.ok) {
        const data = await response.json();
        setAvailableModels(data.available_models || {});
      }
    } catch (error) {
      console.error('获取模型列表失败:', error);
    }
  };

  // 新增：获取模型状态
  const fetchModelStatus = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/models/transformer/status', {
        credentials: 'include'
      });
      if (response.ok) {
        const data = await response.json();
        setModelStatus(data.status);
      }
    } catch (error) {
      console.error('获取模型状态失败:', error);
    }
  };

  // 新增：切换模型
  const switchModel = async (modelKey) => {
    setModelLoading(true);
    try {
      const response = await fetch('http://localhost:8000/api/models/transformer/switch', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({ model_key: modelKey })
      });
      
      if (response.ok) {
        const result = await response.json();
        setCurrentModel(modelKey);
        console.log('模型切换成功:', result.model_info);
        
        // 刷新模型状态
        await fetchModelStatus();
      } else {
        console.error('模型切换失败');
      }
    } catch (error) {
      console.error('切换模型时出错:', error);
    } finally {
      setModelLoading(false);
    }
  };

  // 组件加载时获取模型信息
  useEffect(() => {
    fetchAvailableModels();
    fetchModelStatus();
  }, []);

  const getAutocomplete = async (partial_input) => {
    try {
      setIsCompletionLoading(true);
      let endpoint = '';
      
      // 根据模式选择不同的API端点
      switch (completionMode) {
        case 'transformer':
          endpoint = 'http://localhost:8000/api/prompts/advanced-autocomplete';
          break;
        case 'intelligent':
          endpoint = 'http://localhost:8000/api/prompts/intelligent-autocomplete';
          break;
        case 'template':
          endpoint = 'http://localhost:8000/api/prompts/template-autocomplete';
          break;
        default:
          endpoint = 'http://localhost:8000/api/prompts/advanced-autocomplete';
      }

      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({ 
          partial_input: partial_input,
          max_completions: 5
        })
      });
      
      if (response.ok) {
        const data = await response.json();
        setAutoCompletions(data.completions || []);
        setShowCompletions(data.completions && data.completions.length > 0);
      }
    } catch (error) {
      console.error('自动补全失败:', error);
      setAutoCompletions([]);
      setShowCompletions(false);
    } finally {
      setIsCompletionLoading(false);
    }
  };



  // 处理键盘事件（包括Tab键自动补全）
  const handleKeyDown = async (e) => {
    console.log('⌨️ Key pressed:', e.key);
    
    // Tab键自动补全
    if (e.key === 'Tab') {
      e.preventDefault();
      console.log('🔄 Tab key pressed!', { 
        showCompletions, 
        autoCompletions: autoCompletions.length,
        completionMode 
      });
      
      if (showCompletions && autoCompletions.length > 0) {
        // 应用选中的或第一个完整补全
        const selectedCompletion = selectedCompletionIndex >= 0 
          ? autoCompletions[selectedCompletionIndex] 
          : autoCompletions[0];
        console.log('✅ Applying completion:', selectedCompletion);
        setMessage(selectedCompletion);
        setShowCompletions(false);
        setSelectedCompletionIndex(-1);
      } else {
        // 如果没有补全建议，获取当前输入的补全
        console.log('🔍 No completions shown, fetching for:', message);
        getAutocomplete(message);
      }
      return;
    }

    // 方向键导航补全列表
    if (showCompletions && autoCompletions.length > 0) {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedCompletionIndex(prev => 
          prev < autoCompletions.length - 1 ? prev + 1 : 0
        );
        return;
      }
      
      if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedCompletionIndex(prev => 
          prev > 0 ? prev - 1 : autoCompletions.length - 1
        );
        return;
      }

      // Enter键选择当前高亮的补全
      if (e.key === 'Enter' && selectedCompletionIndex >= 0) {
        e.preventDefault();
        setMessage(autoCompletions[selectedCompletionIndex]);
        setShowCompletions(false);
        setSelectedCompletionIndex(-1);
        return;
      }

      // Escape键关闭补全列表
      if (e.key === 'Escape') {
        setShowCompletions(false);
        setSelectedCompletionIndex(-1);
        return;
      }
    }

    // 原有的Enter键发送消息逻辑
    if (e.key === 'Enter' && !e.shiftKey && !isLoadingResponse) {
      e.preventDefault();
      handleSend();
    }
  };

  // 处理输入变化
  const handleMessageChange = (e) => {
    const value = e.target.value;
    console.log('📝 用户输入变化:', value);
    setMessage(value);
    
    // 清除之前的自动补全防抖定时器
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
      console.log('🔄 清除之前的自动补全防抖定时器');
    }
    
    // 如果输入为空，立即清除所有补全
    if (value.length === 0) {
      setShowCompletions(false);
      setAutoCompletions([]);
      console.log('🧹 输入为空，清除所有补全');
      return;
    }
    
    // 只处理自动补全（完整句子补全），词汇预测由useEffect处理
    if (value.length >= 3) {  // 至少3个字符才触发自动补全
      debounceTimerRef.current = setTimeout(() => {
        console.log('⏰ 自动补全防抖触发 (1秒延迟):', value);
        getAutocomplete(value);
      }, 1000);  // 1秒延迟
    } else {
      // 输入长度不足时，清除自动补全
      setShowCompletions(false);
      setAutoCompletions([]);
      console.log('🧹 输入长度不足3字符，清除自动补全');
    }
  };

  // 处理提示词应用
  const handleApplyPrompt = (appliedPrompt) => {
    setMessage(appliedPrompt);
    setShowCompletions(false);
    setAutoCompletions([]);
    // 可以选择自动聚焦到输入框
    if (inputRef.current) {
      inputRef.current.focus();
    }
  };

  return (
    <ThemeProvider theme={isDarkMode ? darkTheme : lightTheme}>
      <CssBaseline />
      <Box sx={{ display: 'flex', flexDirection: 'column', height: '100vh' }}>
        <AppBar position="static">
          <Toolbar>
            <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
              AI 助手
            </Typography>
            {user && (
              <Typography variant="body2" color="inherit" sx={{ mr: 2 }}>
                用户名: {user.username || '未知'}
              </Typography>
            )}
            <Tooltip title="查看分享的会话">
              <IconButton color="inherit" onClick={() => setShowViewSharedDialog(true)}>
                <VisibilityIcon />
              </IconButton>
            </Tooltip>
            <Tooltip title="我的分享列表">
              <IconButton color="inherit" onClick={() => setShowSharedList(true)}>
                <ShareListIcon />
              </IconButton>
            </Tooltip>
            <IconButton color="inherit" onClick={logout}>
              <LogoutIcon />
            </IconButton>
          </Toolbar>
        </AppBar>

        <Container maxWidth="lg" sx={{ height: '100vh', py: 2 }}>
          {showSettings ? (
            <Settings 
              onClose={() => setShowSettings(false)} 
              onModelsUpdate={handleModelsUpdate}
            />
          ) : (
            <Box sx={{ display: 'flex', height: '100%', gap: 2 }}>
              {/* Sidebar */}
              <Paper sx={{ width: 250, p: 2, display: 'flex', flexDirection: 'column', position: 'relative' }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                  <Button
                    variant="outlined"
                    startIcon={<HistoryIcon />}
                    onClick={() => setShowHistory(!showHistory)}
                  >
                    {showHistory ? 'Hide History' : 'Show History'}
                  </Button>
                  <Tooltip title="New Conversation">
                    <IconButton onClick={createNewConversation} color="primary">
                      <AddIcon />
                    </IconButton>
                  </Tooltip>
                </Box>

                <FormControl fullWidth sx={{ mb: 2 }}>
                  <InputLabel>Models</InputLabel>
                  <Select
                    multiple
                    value={selectedModels}
                    label="Models"
                    onChange={(e) => setSelectedModels(e.target.value)}
                    renderValue={(selected) => (
                      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                        {selected.map((value) => (
                          <Chip 
                            key={value} 
                            label={models.find(m => m.id === value)?.name || value}
                            size="small"
                          />
                        ))}
                      </Box>
                    )}
                    disabled={loading}
                  >
                    {loading ? (
                      <MenuItem disabled>
                        <Typography variant="body2" color="text.secondary">
                          Loading models...
                        </Typography>
                      </MenuItem>
                    ) : error ? (
                      <MenuItem disabled>
                        <Typography variant="body2" color="error">
                          {error}
                        </Typography>
                      </MenuItem>
                    ) : models.length === 0 ? (
                      <MenuItem disabled>
                        <Typography variant="body2" color="text.secondary">
                          No models available
                        </Typography>
                      </MenuItem>
                    ) : (
                      models.map((model) => (
                        <MenuItem key={model.id} value={model.id}>
                          {model.name}
                        </MenuItem>
                      ))
                    )}
                  </Select>
                </FormControl>

                {showHistory && (
                  <>
                    <TextField
                      fullWidth
                      size="small"
                      placeholder="Search conversations..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      sx={{ mb: 2 }}
                      InputProps={{
                        startAdornment: (
                          <InputAdornment position="start">
                            <SearchIcon fontSize="small" />
                          </InputAdornment>
                        ),
                        endAdornment: searchQuery && (
                          <InputAdornment position="end">
                            <IconButton
                              size="small"
                              onClick={() => setSearchQuery('')}
                            >
                              <ClearIcon fontSize="small" />
                            </IconButton>
                          </InputAdornment>
                        )
                      }}
                    />
                    <List sx={{ overflow: 'auto', flex: 1 }}>
                      {filteredConversations.map((conv) => (
                        <React.Fragment key={conv.id}>
                          <ListItem
                            button
                            selected={currentConversationId === conv.id}
                            onClick={() => selectConversation(conv.id)}
                            secondaryAction={
                              <Box>
                                <Tooltip title="分享会话">
                                  <IconButton
                                    edge="end"
                                    aria-label="share"
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      setCurrentConversationId(conv.id);
                                      setShowShareDialog(true);
                                    }}
                                    size="small"
                                  >
                                    <ShareIcon fontSize="small" />
                                  </IconButton>
                                </Tooltip>
                                <Tooltip title="编辑标题">
                                  <IconButton
                                    edge="end"
                                    aria-label="edit"
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      handleEditTitle(conv);
                                    }}
                                    size="small"
                                  >
                                    <EditIcon fontSize="small" />
                                  </IconButton>
                                </Tooltip>
                                <Tooltip title="删除会话">
                                  <IconButton 
                                    edge="end" 
                                    aria-label="delete"
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      deleteConversation(conv.id);
                                    }}
                                    size="small"
                                  >
                                    <DeleteIcon fontSize="small" />
                                  </IconButton>
                                </Tooltip>
                              </Box>
                            }
                          >
                            <ListItemText
                              primary={conv.title}
                              secondary={new Date(conv.createdAt).toLocaleDateString()}
                            />
                          </ListItem>
                          <Divider />
                        </React.Fragment>
                      ))}
                      {filteredConversations.length === 0 && (
                        <ListItem>
                          <ListItemText
                            primary="No conversations found"
                            sx={{ textAlign: 'center', color: 'text.secondary' }}
                          />
                        </ListItem>
                      )}
                    </List>
                  </>
                )}

                  {/* 设置和主题切换按钮放在左下角 */}
                <Box sx={{ mt: 'auto', pt: 2, borderTop: 1, borderColor: 'divider' }}>
                  <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
                    <Button
                      fullWidth
                      variant="outlined"
                      startIcon={<SettingsIcon />}
                      onClick={() => setShowSettings(true)}
                    >
                      设置
                    </Button>
                    <Tooltip title={isDarkMode ? '切换到亮色主题' : '切换到深色主题'}>
                      <IconButton
                        onClick={() => setIsDarkMode(!isDarkMode)}
                        color="primary"
                        sx={{ 
                          border: 1, 
                          borderColor: 'divider',
                          '&:hover': {
                            borderColor: 'primary.main'
                          }
                        }}
                      >
                        {isDarkMode ? <LightModeIcon /> : <DarkModeIcon />}
                      </IconButton>
                    </Tooltip>
                  </Box>
                </Box>
              </Paper>

              {/* Main Chat Area */}
              <Paper sx={{ flex: 1, p: 2, display: 'flex', flexDirection: 'column' }}>
                {loading ? (
                  <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
                    <Typography variant="body1" color="text.secondary">
                      Loading models...
                    </Typography>
                  </Box>
                ) : error ? (
                  <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
                    <Typography variant="body1" color="error">
                      {error}
                    </Typography>
                  </Box>
                ) : (
                  <>
                    {/* 添加融合回答的切换按钮 */}
                    {selectedModels.length > 1 && (
                      <Box sx={{ mb: 2, display: 'flex', alignItems: 'center', justifyContent: 'flex-end' }}>
                        <FormControlLabel
                          control={
                            <Switch
                              checked={mergeResponses}
                              onChange={(e) => setMergeResponses(e.target.checked)}
                              color="primary"
                            />
                          }
                          label={
                            <Typography variant="body2" color="text.secondary">
                              融合回答
                            </Typography>
                          }
                        />
                      </Box>
                    )}

                    <Box className="messages-container" sx={{ flex: 1, overflow: 'auto', mb: 2 }}>
                      {getCurrentConversation().messages && getCurrentConversation().messages.length > 0 ? (
                        getCurrentConversation().messages.map((msg, index) => {
                          // 安全检查：确保消息对象存在且有必要的属性
                          if (!msg || typeof msg !== 'object') {
                            console.warn('Invalid message object at index:', index, msg);
                            return null;
                          }
                          
                          return (
                            <Box
                              key={`${currentConversationId}-${index}`}
                              sx={{
                                display: 'flex',
                                justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
                                mb: 2
                              }}
                            >
                              <Paper
                            className={
                              msg.role === 'user' 
                                ? 'user-message' 
                                : msg.model === 'error'
                                  ? 'error-message'
                                  : 'assistant-message'
                            }
                            sx={{
                              p: 2,
                              maxWidth: '70%',
                              backgroundColor: msg.role === 'user' 
                                ? 'transparent' 
                                : msg.model === 'error'
                                  ? 'transparent'
                                  : 'transparent'
                            }}
                          >
                            {msg.role === 'user' ? (
                              <Typography 
                                variant="body1" 
                                sx={{ 
                                  whiteSpace: 'pre-wrap',
                                  wordBreak: 'break-word'
                                }}
                              >
                                {msg.content}
                              </Typography>
                            ) : (
                              <Box sx={{ 
                                '& .code-block': {
                                  margin: '1rem 0'
                                },
                                '& pre': { 
                                  backgroundColor: 'transparent',
                                  padding: 0,
                                  margin: 0
                                },
                                '& code': {
                                  backgroundColor: 'transparent',
                                  padding: 0
                                },
                                '& p': {
                                  margin: '0.5rem 0'
                                },
                                '& ul, & ol': {
                                  margin: '0.5rem 0',
                                  paddingLeft: '1.5rem'
                                },
                                '& table': {
                                  borderCollapse: 'collapse',
                                  width: '100%',
                                  margin: '0.5rem 0'
                                },
                                '& th, & td': {
                                  border: '1px solid #ddd',
                                  padding: '0.5rem',
                                  textAlign: 'left'
                                },
                                '& th': {
                                  backgroundColor: 'rgba(0, 0, 0, 0.05)'
                                },
                                '& blockquote': {
                                  borderLeft: '4px solid #ddd',
                                  margin: '0.5rem 0',
                                  padding: '0.5rem 0 0.5rem 1rem',
                                  color: 'text.secondary'
                                }
                              }}>
                                <ReactMarkdown 
                                  remarkPlugins={[remarkGfm]}
                                  components={{
                                    code: ({node, inline, className, children, ...props}) => {
                                      const match = /language-(\w+)/.exec(className || '');
                                      if (inline) {
                                        return (
                                          <code className={className} {...props}>
                                            {children}
                                          </code>
                                        );
                                      }
                                      
                                      // 检查是否为多行代码
                                      const isMultiLine = String(children).includes('\n');
                                      
                                      if (isMultiLine) {
                                        const handleCopy = () => {
                                          navigator.clipboard.writeText(String(children));
                                        };
                                        
                                        return (
                                          <div className="code-block" style={{display: 'block'}}>
                                            <button className="copy-btn" onClick={handleCopy}>
                                              复制
                                            </button>
                                                <pre style={{margin: 0}}>
                                                  <code 
                                                className={match ? `language-${match[1]}` : ''} 
                                                style={{
                                                  backgroundColor: '#0d1117',
                                                  color: '#4a9eff',
                                                  padding: '16px 20px',
                                                  borderRadius: '12px',
                                                  fontFamily: 'JetBrains Mono, Fira Code, Consolas, monospace',
                                                  fontSize: '14px',
                                                  lineHeight: '1.8',
                                                  display: 'block',
                                                  width: '100%',
                                                  boxSizing: 'border-box',
                                                  border: '1px solid #30363d',
                                                  whiteSpace: 'pre-wrap',
                                                  wordBreak: 'break-word',
                                                  overflow: 'auto',
                                                  margin: '12px 0',
                                                  boxShadow: '0 4px 8px rgba(0, 0, 0, 0.3)',
                                                }}
                                                {...props}
                                              >
                                                {children}
                                              </code>
                                            </pre>
                                          </div>
                                        );
                                      }
                                      
                                      // 单行代码简单显示
                                          return (
                                            <code 
                                          className={match ? `language-${match[1]}` : ''} 
                                          style={{
                                            backgroundColor: 'rgba(116, 199, 236, 0.2)',
                                            color: '#74c7ec',
                                            padding: '2px 6px',
                                            borderRadius: '4px',
                                            fontFamily: 'JetBrains Mono, Consolas, monospace',
                                            fontSize: '0.9em'
                                          }}
                                          {...props}
                                        >
                                          {children}
                                        </code>
                                      );
                                    }
                                  }}
                                >
                                  {msg.content}
                                </ReactMarkdown>
                              </Box>
                            )}
                            {msg.model && (
                              <Typography 
                                variant="caption" 
                                color="text.secondary" 
                                sx={{ 
                                  display: 'block', 
                                  mt: 1,
                                  color: msg.model === 'error' ? 'error.main' : 'text.secondary'
                                }}
                              >
                                {msg.model === 'merged' 
                                  ? '融合回答' 
                                  : msg.model === 'error'
                                    ? '错误'
                                    : `Model: ${models.find(m => m.id === msg.model)?.name || msg.model}`}
                              </Typography>
                                )}
                                <Typography variant="caption" color="text.secondary">
                              {msg.timestamp && new Date(msg.timestamp).toLocaleTimeString()}
                            </Typography>
                          </Paper>
                        </Box>
                          );
                        }).filter(Boolean) // 过滤掉null值
                      ) : (
                        <Typography variant="body2" color="text.secondary" sx={{ textAlign: 'center', py: 4 }}>
                          暂无消息记录
                        </Typography>
                      )}
                  
                  {/* 显示加载指示器 */}
                  {isLoadingResponse && <TypingIndicator />}
                </Box>

                    <Box sx={{ display: 'flex', gap: 1, position: 'relative' }}>
                      <Box sx={{ flex: 1, position: 'relative' }}>
                        {/* 补全模式切换按钮 */}
                        <Box sx={{ display: 'flex', gap: 1, mb: 1 }}>
                          <Chip
                            label="🤖 Transformer补全"
                            size="small"
                            color={completionMode === 'transformer' ? 'primary' : 'default'}
                            onClick={() => setCompletionMode('transformer')}
                            clickable
                          />
                          <Chip
                            label="🧠 智能补全"
                            size="small"
                            color={completionMode === 'intelligent' ? 'primary' : 'default'}
                            onClick={() => setCompletionMode('intelligent')}
                            clickable
                          />
                          <Chip
                            label="📝 模板补全"
                            size="small"
                            color={completionMode === 'template' ? 'primary' : 'default'}
                            onClick={() => setCompletionMode('template')}
                            clickable
                          />
                          {completionMode === 'transformer' && (
                            <Typography variant="caption" color="text.secondary" sx={{ alignSelf: 'center', ml: 1 }}>
                              基于预训练Transformer模型
                            </Typography>
                          )}
                          {completionMode === 'intelligent' && (
                            <Typography variant="caption" color="text.secondary" sx={{ alignSelf: 'center', ml: 1 }}>
                              基于N-gram语言模型
                            </Typography>
                          )}
                        </Box>
                        
                  <TextField
                    fullWidth
                          multiline
                          maxRows={4}
                    value={message}
                          onChange={handleMessageChange}
                          onKeyDown={handleKeyDown}
                          placeholder={
                            completionMode === 'transformer' 
                              ? "输入消息... (Tab键AI智能补全)" 
                              : completionMode === 'intelligent' 
                                ? "输入消息... (Tab键补全下一个词)" 
                                : "输入消息... (Tab键补全整句)"
                          }
                    disabled={isLoadingResponse}
                          inputRef={inputRef}
                          InputProps={{
                            endAdornment: (
                              <Box sx={{ display: 'flex', gap: 0.5 }}>
                                <Tooltip title="智能提示词助手">
                                  <IconButton
                                    size="small"
                                    onClick={() => setPromptHelperOpen(true)}
                                    sx={{ color: 'primary.main' }}
                                  >
                                    <LightbulbIcon />
                                  </IconButton>
                                </Tooltip>
                              </Box>
                            )
                          }}
                        />
                        

                        
                        {/* 自动补全下拉列表 */}
                        {console.log('🎨 Rendering autocomplete:', { showCompletions, autoCompletions: autoCompletions.length })}
                        {showCompletions && autoCompletions.length > 0 && (
                          <Paper
                            sx={{
                              position: 'absolute',
                              top: '100%',
                              left: 0,
                              right: 0,
                              zIndex: 1000,
                              maxHeight: 200,
                              overflow: 'auto',
                              mt: 0.5,
                              border: 1,
                              borderColor: 'divider'
                            }}
                          >
                            <List dense>
                              {autoCompletions.map((completion, index) => (
                                <ListItem
                                  key={index}
                                  button
                                  selected={index === selectedCompletionIndex}
                                  onClick={() => {
                                    setMessage(completion);
                                    setShowCompletions(false);
                                    setSelectedCompletionIndex(-1);
                                    if (inputRef.current) {
                                      inputRef.current.focus();
                                    }
                                  }}
                                  sx={{
                                    '&.Mui-selected': {
                                      backgroundColor: 'primary.light',
                                      color: 'primary.contrastText',
                                      '&:hover': {
                                        backgroundColor: 'primary.main',
                                      }
                                    }
                                  }}
                                >
                                  <ListItemText
                                    primary={completion}
                                    primaryTypographyProps={{
                                      style: {
                                        whiteSpace: 'nowrap',
                                        overflow: 'hidden',
                                        textOverflow: 'ellipsis'
                                      }
                                    }}
                                  />
                                </ListItem>
                              ))}
                            </List>
                            <Box sx={{ p: 1, backgroundColor: 'grey.50', borderTop: 1, borderColor: 'divider' }}>
                              <Typography variant="caption" color="text.secondary">
                                💡 使用 ↑↓ 导航，Tab/Enter 选择完整补全，Esc 关闭
                              </Typography>
                            </Box>
                          </Paper>
                        )}
                      </Box>
                      
                      <Button
                        variant="contained"
                        onClick={handleSend}
                        disabled={isLoadingResponse || !message.trim()}
                        endIcon={<SendIcon />}
                      >
                        {isLoadingResponse ? '发送中...' : '发送'}
                      </Button>
                    </Box>
                  </>
                )}
              </Paper>
            </Box>
          )}
        </Container>

        {/* Edit Title Dialog */}
        <Dialog 
          open={Boolean(editingConversation)} 
          onClose={() => setEditingConversation(null)}
          maxWidth="sm"
          fullWidth
        >
          <DialogTitle>Edit Conversation Title</DialogTitle>
          <DialogContent>
            <TextField
              autoFocus
              margin="dense"
              label="Title"
              fullWidth
              value={editTitle}
              onChange={(e) => setEditTitle(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && saveEditTitle()}
            />
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setEditingConversation(null)}>Cancel</Button>
            <Button onClick={saveEditTitle} variant="contained">Save</Button>
          </DialogActions>
        </Dialog>

        {/* 分享对话框 */}
        <ShareDialog
          open={showShareDialog}
          onClose={() => setShowShareDialog(false)}
          conversationId={currentConversationId}
        />

        {/* 分享列表对话框 */}
        <Dialog
          open={showSharedList}
          onClose={() => setShowSharedList(false)}
          maxWidth="md"
          fullWidth
        >
          <DialogTitle>我的分享</DialogTitle>
          <DialogContent>
            <List>
              {sharedConversations.map((shared) => (
                <ListItem
                  key={shared.id}
                  secondaryAction={
                    <Box>
                      <Tooltip title="复制链接">
                        <IconButton
                          edge="end"
                          onClick={() => {
                            const shareUrl = `${window.location.origin}/shared/${shared.id}`;
                            navigator.clipboard.writeText(shareUrl)
                              .then(() => {
                                // 显示复制成功提示
                                setSharedError('链接已复制到剪贴板');
                                // 3秒后清除提示
                                setTimeout(() => setSharedError(''), 3000);
                              })
                              .catch(() => {
                                // 显示复制失败提示
                                setSharedError('复制失败，请手动复制');
                                // 3秒后清除提示
                                setTimeout(() => setSharedError(''), 3000);
                              });
                          }}
                        >
                          <ContentCopyIcon />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="删除分享">
                        <IconButton
                          edge="end"
                          onClick={() => handleDeleteShare(shared.id)}
                          sx={{ ml: 1 }}
                        >
                          <DeleteIcon />
                        </IconButton>
                      </Tooltip>
                    </Box>
                  }
                >
                  <ListItemText
                    primary={shared.title || '未命名会话'}
                    secondary={`分享时间: ${new Date(shared.createdAt).toLocaleString()}`}
                  />
                </ListItem>
              ))}
              {sharedConversations.length === 0 && (
                <ListItem>
                  <ListItemText
                    primary="暂无分享的会话"
                    sx={{ textAlign: 'center', color: 'text.secondary' }}
                  />
                </ListItem>
              )}
            </List>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setShowSharedList(false)}>关闭</Button>
          </DialogActions>
        </Dialog>

        {/* 查看分享会话对话框 */}
        <Dialog
          open={showViewSharedDialog}
          onClose={() => {
            setShowViewSharedDialog(false);
            setSharedLink('');
            setSharedError('');
          }}
          maxWidth="sm"
          fullWidth
        >
          <DialogTitle sx={{ 
            display: 'flex', 
            alignItems: 'center', 
            gap: 1,
            borderBottom: 1,
            borderColor: 'divider',
            pb: 2
          }}>
            <VisibilityIcon color="primary" />
            查看分享的会话
          </DialogTitle>
          <DialogContent>
            <Box sx={{ mt: 2 }}>
              <Paper 
                elevation={0} 
                sx={{ 
                  p: 3,
                  backgroundColor: 'background.default',
                  borderRadius: 2
                }}
              >
                <Typography variant="subtitle1" gutterBottom>
                  输入分享链接
                </Typography>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                  <TextField
                    fullWidth
                    value={sharedLink}
                    onChange={(e) => setSharedLink(e.target.value)}
                    placeholder="请输入分享链接"
                    error={!!sharedError}
                    helperText={sharedError}
                    sx={{
                      '& .MuiOutlinedInput-root': {
                        backgroundColor: 'background.paper'
                      }
                    }}
                  />
                </Box>
                <Typography variant="body2" color="text.secondary">
                  输入其他用户分享的会话链接，即可查看会话内容
                </Typography>
              </Paper>
            </Box>
          </DialogContent>
          <DialogActions sx={{ px: 3, py: 2, borderTop: 1, borderColor: 'divider' }}>
            <Button 
              onClick={() => {
                setShowViewSharedDialog(false);
                setSharedLink('');
                setSharedError('');
              }} 
              variant="outlined"
            >
              取消
            </Button>
            <Button 
              onClick={handleViewShared} 
              variant="contained"
              disabled={!sharedLink.trim()}
            >
              查看
            </Button>
          </DialogActions>
        </Dialog>

        {/* 删除错误提示 */}
        <Snackbar
          open={!!deleteError}
          autoHideDuration={6000}
          onClose={() => setDeleteError('')}
        >
          <Alert onClose={() => setDeleteError('')} severity="error">
            {deleteError}
          </Alert>
        </Snackbar>

        {/* 智能提示词助手 */}
        <PromptHelper
          open={promptHelperOpen}
          onClose={() => setPromptHelperOpen(false)}
          onApplyPrompt={handleApplyPrompt}
          userInput={message}
          setUserInput={setMessage}
        />
      </Box>
    </ThemeProvider>
  );
};

// 主应用组件
const App = () => {
  const [showLogin, setShowLogin] = useState(true);
  const { user } = useAuth();

  // 检查URL是否包含分享ID
  const shareId = window.location.pathname.split('/shared/')[1];

  if (shareId) {
    return <SharedConversation shareId={shareId} />;
  }

  if (!user) {
  return showLogin ? (
      <Login onLoginSuccess={() => setShowLogin(false)} />
  ) : (
      <Register onRegisterSuccess={() => setShowLogin(true)} />
  );
  }

  return <MainApp />;
};

// 包装整个应用
const AppWithAuth = () => (
  <AuthProvider>
    <App />
  </AuthProvider>
);

export default AppWithAuth;