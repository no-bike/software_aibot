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
import SendIcon from '@mui/icons-material/Send';
import HistoryIcon from '@mui/icons-material/History';
import AddIcon from '@mui/icons-material/Add';
import DeleteIcon from '@mui/icons-material/Delete';
import EditIcon from '@mui/icons-material/Edit';
import SearchIcon from '@mui/icons-material/Search';
import ClearIcon from '@mui/icons-material/Clear';
import SettingsIcon from '@mui/icons-material/Settings';
import Settings from './components/Settings';
import { sendMessage } from './services/aiService';

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

  // 从localStorage加载模型列表
  useEffect(() => {
    const loadModels = () => {
      const savedModels = JSON.parse(localStorage.getItem('aiModels') || '[]');
      if (savedModels.length > 0) {
        setModels(savedModels);
        // 如果当前没有选中的模型，选择第一个
        if (selectedModels.length === 0 && savedModels.length > 0) {
          setSelectedModels([savedModels[0].id]);
        }
      } else {
        // 如果没有保存的模型，设置默认模型
        const defaultModels = [
          { id: 'gpt-3.5-turbo', name: 'GPT-3.5 Turbo', apiKey: '' },
          { id: 'gpt-4', name: 'GPT-4', apiKey: '' },
          { id: 'claude-2', name: 'Claude 2', apiKey: '' }
        ];
        setModels(defaultModels);
        setSelectedModels(['gpt-3.5-turbo']);
      }
    };

    // 初始加载
    loadModels();

    // 监听localStorage变化
    const handleStorageChange = (e) => {
      if (e.key === 'aiModels') {
        loadModels();
      }
    };

    window.addEventListener('storage', handleStorageChange);
    return () => window.removeEventListener('storage', handleStorageChange);
  }, []);

  // 当模型列表变化时，确保选中的模型仍然有效
  useEffect(() => {
    if (models.length > 0) {
      const validSelectedModels = selectedModels.filter(modelId => 
        models.find(model => model.id === modelId)
      );
      if (validSelectedModels.length === 0) {
        setSelectedModels([models[0].id]);
      } else if (validSelectedModels.length !== selectedModels.length) {
        setSelectedModels(validSelectedModels);
      }
    }
  }, [models, selectedModels]);

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
      const currentConversation = getCurrentConversation();
      const messages = currentConversation.messages;

      // 调用AI服务
      const responses = await Promise.all(
        selectedModels.map(modelId => sendMessage(modelId, messages))
      );

      let aiMessages;
      if (mergeResponses && responses.length > 1) {
        // 合并所有回答
        const mergedContent = responses.join('\n\n---\n\n');
        aiMessages = [{
          role: 'assistant',
          content: mergedContent,
          model: 'merged',
          timestamp: new Date().toISOString()
        }];
      } else {
        // 分别显示每个模型的回答
        aiMessages = responses.map((response, index) => ({
          role: 'assistant',
          content: response,
          model: selectedModels[index],
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

  return (
    <Container maxWidth="lg" sx={{ height: '100vh', py: 2 }}>
      {showSettings ? (
        <Settings onClose={() => setShowSettings(false)} />
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
              >
                {models.map((model) => (
                  <MenuItem key={model.id} value={model.id}>
                    {model.name}
                  </MenuItem>
                ))}
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
                      backgroundColor: msg.role === 'user' ? 'primary.light' : 'grey.100'
                    }}
                  >
                    <Typography variant="body1">{msg.content}</Typography>
                    {msg.model && (
                      <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1 }}>
                        {msg.model === 'merged' ? '融合回答' : `Model: ${models.find(m => m.id === msg.model)?.name || msg.model}`}
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