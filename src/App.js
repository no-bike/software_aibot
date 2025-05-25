import React, { useState, useMemo } from 'react';
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
  InputAdornment
} from '@mui/material';
import SendIcon from '@mui/icons-material/Send';
import HistoryIcon from '@mui/icons-material/History';
import AddIcon from '@mui/icons-material/Add';
import DeleteIcon from '@mui/icons-material/Delete';
import EditIcon from '@mui/icons-material/Edit';
import SearchIcon from '@mui/icons-material/Search';
import ClearIcon from '@mui/icons-material/Clear';

const App = () => {
  const [message, setMessage] = useState('');
  const [conversations, setConversations] = useState([]);
  const [currentConversationId, setCurrentConversationId] = useState(null);
  const [selectedModel, setSelectedModel] = useState('gpt-3.5-turbo');
  const [showHistory, setShowHistory] = useState(true);
  const [editingConversation, setEditingConversation] = useState(null);
  const [editTitle, setEditTitle] = useState('');
  const [searchQuery, setSearchQuery] = useState('');

  const models = [
    { id: 'gpt-3.5-turbo', name: 'GPT-3.5 Turbo' },
    { id: 'gpt-4', name: 'GPT-4' },
    { id: 'claude-2', name: 'Claude 2' }
  ];

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
      model: selectedModel,
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
          // 如果是第一条消息，更新对话标题
          const updatedMessages = [...conv.messages, newMessage];
          const title = conv.messages.length === 0 ? message.slice(0, 30) + (message.length > 30 ? '...' : '') : conv.title;
          return {
            ...conv,
            title,
            messages: updatedMessages
          };
        }
        return conv;
      });
    });

    setMessage('');

    // TODO: Implement actual API call here
    const response = {
      role: 'assistant',
      content: 'This is a placeholder response. Implement actual API integration here.',
      timestamp: new Date().toISOString()
    };

    // 添加AI响应
    setConversations(prevConversations => {
      return prevConversations.map(conv => {
        if (conv.id === currentConversationId) {
          return {
            ...conv,
            messages: [...conv.messages, response]
          };
        }
        return conv;
      });
    });
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
      <Box sx={{ display: 'flex', height: '100%', gap: 2 }}>
        {/* Sidebar */}
        <Paper sx={{ width: 250, p: 2, display: 'flex', flexDirection: 'column' }}>
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
            <InputLabel>Model</InputLabel>
            <Select
              value={selectedModel}
              label="Model"
              onChange={(e) => setSelectedModel(e.target.value)}
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
              <List sx={{ overflow: 'auto' }}>
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
        </Paper>

        {/* Main Chat Area */}
        <Paper sx={{ flex: 1, p: 2, display: 'flex', flexDirection: 'column' }}>
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