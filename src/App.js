import React, { useState, useMemo, useEffect } from 'react';
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
  FormControlLabel
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
import Settings from './components/Settings';
import { getModels, updateModelSelection, sendMessage as sendMessageToAPI } from './services/apiService';

const App = () => {
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
      id: Date.now(),
      title: 'New Conversation',
      messages: [],
      models: selectedModels,
      createdAt: new Date().toISOString()
    };
    setConversations([newConversation, ...conversations]);
    setCurrentConversationId(newConversation.id);
  };

  const handleSend = async () => {
    if (!message.trim()) return;

    const newMessage = {
      role: 'user',
      content: message,
      timestamp: new Date().toISOString()
    };

    // 如果是新对话，创建对话
    if (!currentConversationId) {
      createNewConversation();
    }

    // 更新对话
    setConversations(prevConversations => {
      return prevConversations.map(conv => {
        if (conv.id === currentConversationId) {
          const updatedMessages = [...conv.messages, newMessage];
          const title = conv.messages.length === 0 ? message.slice(0, 30) + (message.length > 30 ? '...' : '') : conv.title;
          return {
            ...conv,
            title,
            messages: updatedMessages,
            models: selectedModels
          };
        }
        return conv;
      });
    });

    setMessage('');

    try {
      // 调用API发送消息
      const response = await sendMessageToAPI(message, selectedModels, currentConversationId);
      
      let aiMessages;
      if (mergeResponses && response.responses.length > 1) {
        // 合并所有回答
        const mergedContent = response.responses.map(r => r.content).join('\n\n---\n\n');
        aiMessages = [{
          role: 'assistant',
          content: mergedContent,
          model: 'merged',
          timestamp: new Date().toISOString()
        }];
      } else {
        // 分别显示每个模型的回答
        aiMessages = response.responses.map(response => ({
          role: 'assistant',
          content: response.content,
          model: response.modelId,
          timestamp: new Date().toISOString()
        }));
      }

      setConversations(prevConversations => {
        return prevConversations.map(conv => {
          if (conv.id === currentConversationId) {
            return {
              ...conv,
              messages: [...conv.messages, ...aiMessages]
            };
          }
          return conv;
        });
      });
    } catch (error) {
      console.error('Error sending message:', error);
      // 添加错误提示
      const errorMessage = {
        role: 'assistant',
        content: `Error: ${error.message || 'Failed to get response'}`,
        model: 'error',
        timestamp: new Date().toISOString()
      };
      
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
  };

  const deleteConversation = (conversationId) => {
    setConversations(prevConversations => 
      prevConversations.filter(conv => conv.id !== conversationId)
    );
    if (currentConversationId === conversationId) {
      setCurrentConversationId(null);
    }
  };

  const handleEditTitle = (conversation) => {
    setEditingConversation(conversation);
    setEditTitle(conversation.title);
  };

  const saveEditTitle = () => {
    if (editingConversation && editTitle.trim()) {
      setConversations(prevConversations => 
        prevConversations.map(conv => 
          conv.id === editingConversation.id 
            ? { ...conv, title: editTitle.trim() }
            : conv
        )
      );
    }
    setEditingConversation(null);
    setEditTitle('');
  };

  const getCurrentConversation = () => {
    return conversations.find(conv => conv.id === currentConversationId) || { messages: [] };
  };

  const handleModelsUpdate = (updatedModels) => {
    setModels(updatedModels);
    // 如果当前没有选中的模型，选择第一个
    if (selectedModels.length === 0 && updatedModels.length > 0) {
      setSelectedModels([updatedModels[0].id]);
    }
  };

  return (
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
                        onClick={() => setCurrentConversationId(conv.id)}
                        secondaryAction={
                          <Box>
                            <Tooltip title="Edit Title">
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
                            <Tooltip title="Delete Conversation">
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
            
            {/* 设置按钮放在左下角 */}
            <Box sx={{ mt: 'auto', pt: 2, borderTop: 1, borderColor: 'divider' }}>
              <Button
                fullWidth
                variant="outlined"
                startIcon={<SettingsIcon />}
                onClick={() => setShowSettings(true)}
              >
                设置
              </Button>
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

                <Box sx={{ flex: 1, overflow: 'auto', mb: 2 }}>
                  {getCurrentConversation().messages.map((msg, index) => (
                    <Box
                      key={index}
                      sx={{
                        display: 'flex',
                        justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
                        mb: 2
                      }}
                    >
                      <Paper
                        sx={{
                          p: 2,
                          maxWidth: '70%',
                          backgroundColor: msg.role === 'user' 
                            ? 'primary.light' 
                            : msg.model === 'error'
                              ? 'error.light'
                              : 'grey.100'
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
                            '& pre': { 
                              backgroundColor: 'rgba(0, 0, 0, 0.05)',
                              padding: '1rem',
                              borderRadius: '4px',
                              overflowX: 'auto'
                            },
                            '& code': {
                              backgroundColor: 'rgba(0, 0, 0, 0.05)',
                              padding: '0.2rem 0.4rem',
                              borderRadius: '3px',
                              fontSize: '0.9em'
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
                                  return !inline ? (
                                    <pre>
                                      <code className={match ? `language-${match[1]}` : ''} {...props}>
                                        {children}
                                      </code>
                                    </pre>
                                  ) : (
                                    <code className={className} {...props}>
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
                          {new Date(msg.timestamp).toLocaleTimeString()}
                        </Typography>
                      </Paper>
                    </Box>
                  ))}
                </Box>

                <Box sx={{ display: 'flex', gap: 1 }}>
                  <TextField
                    fullWidth
                    variant="outlined"
                    placeholder="Type your message..."
                    value={message}
                    onChange={(e) => setMessage(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && handleSend()}
                  />
                  <Button
                    variant="contained"
                    endIcon={<SendIcon />}
                    onClick={handleSend}
                  >
                    Send
                  </Button>
                </Box>
              </>
            )}
          </Paper>
        </Box>
      )}

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
    </Container>
  );
};

export default App; 