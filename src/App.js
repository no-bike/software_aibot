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
  ThemeProvider,
  CssBaseline,
  AppBar,
  Toolbar,
  Snackbar,
  Alert
} from '@mui/material';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import SendIcon from '@mui/icons-material/Send';
import HistoryIcon from '@mui/icons-material/History';
import AddIcon from '@mui/icons-material/Add';
import DeleteIcon from '@mui/icons-material/Delete';
import EditIcon from '@mui/icons-material/Edit';
import SearchIcon from '@mui/icons-material/Search';
import ClearIcon from '@mui/icons-material/Clear';
import SettingsIcon from '@mui/icons-material/Settings';
import DarkModeIcon from '@mui/icons-material/DarkMode';
import LightModeIcon from '@mui/icons-material/LightMode';
import LogoutIcon from '@mui/icons-material/Logout';
import ShareIcon from '@mui/icons-material/Share';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import ShareListIcon from '@mui/icons-material/List';
import VisibilityIcon from '@mui/icons-material/Visibility';
import Settings from './components/Settings';
import Login from './components/Login';
import Register from './components/Register';
import darkTheme from './theme/darkTheme';
import lightTheme from './theme/lightTheme';
import { getModels, updateModelSelection, sendMessage as sendMessageToAPI, fusionResponses, getConversations, deleteConversation as deleteConversationAPI, getConversationDetail, updateConversationTitle, getUserSharedConversations, deleteShare } from './services/apiService';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import ShareDialog from './components/ShareDialog';
import SharedConversation from './components/SharedConversation';

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
  const [isDarkMode, setIsDarkMode] = useState(true);
  const messagesEndRef = useRef(null);
  const [showShareDialog, setShowShareDialog] = useState(false);
  const [showSharedList, setShowSharedList] = useState(false);
  const [showViewSharedDialog, setShowViewSharedDialog] = useState(false);
  const [sharedConversations, setSharedConversations] = useState([]);
  const [sharedLink, setSharedLink] = useState('');
  const [sharedError, setSharedError] = useState('');
  const [deleteError, setDeleteError] = useState('');

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

  const [streamingContent, setStreamingContent] = useState('');

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
    }
  };  const deleteConversation = async (conversationId) => {
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
                    )}                <Box className="messages-container" sx={{ flex: 1, overflow: 'auto', mb: 2 }}>
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
                            ><Paper
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
                                            <pre style={{margin: 0}}>                                          <code 
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
                                      return (                                    <code 
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
                            )}                            <Typography variant="caption" color="text.secondary">
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
                    </Box>

                    <Box sx={{ display: 'flex', gap: 1 }}>
                      <TextField
                        fullWidth
                        multiline
                        maxRows={4}
                        value={message}
                        onChange={(e) => setMessage(e.target.value)}
                        placeholder="输入消息..."
                        onKeyPress={(e) => {
                          if (e.key === 'Enter' && !e.shiftKey) {
                            e.preventDefault();
                            handleSend();
                          }
                        }}
                      />
                      <Button
                        variant="contained"
                        onClick={handleSend}
                        disabled={!message.trim() || loading}
                        endIcon={<SendIcon />}
                      >
                        发送
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
            <Button onClick={saveEditTitle} variant="contained">Save</Button>          </DialogActions>
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
      </Box>
    </ThemeProvider>
  );
};

// 主应用组件
const App = () => {
  const [isLogin, setIsLogin] = useState(false);
  const [isRegister, setIsRegister] = useState(false);
  const { user } = useAuth();

  // 检查URL是否包含分享ID
  const shareId = window.location.pathname.split('/shared/')[1];

  if (shareId) {
    return <SharedConversation shareId={shareId} />;
  }

  if (!user) {
    if (isRegister) {
      return <Register onRegisterSuccess={() => setIsRegister(false)} />;
    }
    return <Login onLoginSuccess={() => setIsLogin(true)} />;
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
