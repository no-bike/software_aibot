import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Paper,
  CircularProgress,
  Alert,
  Divider,
  Avatar,
  Chip,
  Container,
  IconButton,
  Tooltip
} from '@mui/material';
import {
  Person as PersonIcon,
  AccessTime as AccessTimeIcon,
  Share as ShareIcon
} from '@mui/icons-material';
import ReactMarkdown from 'react-markdown';
import { getSharedConversation } from '../services/apiService';

const SharedConversation = ({ shareId }) => {
  const [conversation, setConversation] = useState(null);
  const [sharedBy, setSharedBy] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchSharedConversation = async () => {
      try {
        const data = await getSharedConversation(shareId);
        setConversation(data.conversation);
        setSharedBy(data.sharedBy);
      } catch (error) {
        setError('获取分享的会话失败，请检查链接是否正确');
      } finally {
        setLoading(false);
      }
    };

    fetchSharedConversation();
  }, [shareId]);

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Box sx={{ mt: 4 }}>
        <Alert severity="error">{error}</Alert>
      </Box>
    );
  }

  if (!conversation) {
    return (
      <Box sx={{ mt: 4 }}>
        <Alert severity="info">未找到分享的会话</Alert>
      </Box>
    );
  }

  return (
    <Container maxWidth="md" sx={{ py: 4 }}>
      {/* 会话标题和分享信息 */}
      <Paper 
        elevation={0} 
        sx={{ 
          p: 3, 
          mb: 3, 
          backgroundColor: 'background.paper',
          borderRadius: 2,
          border: 1,
          borderColor: 'divider'
        }}
      >
        <Typography variant="h4" gutterBottom>
          {conversation.title || '分享的会话'}
        </Typography>
        
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mt: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Avatar sx={{ bgcolor: 'primary.main' }}>
              <PersonIcon />
            </Avatar>
            <Box>
              <Typography variant="subtitle2" color="text.secondary">
                分享者
              </Typography>
              <Typography variant="body1">
                {sharedBy?.username || '未知用户'}
              </Typography>
              {sharedBy?.email && (
                <Typography variant="caption" color="text.secondary">
                  {sharedBy.email}
                </Typography>
              )}
            </Box>
          </Box>
          
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <AccessTimeIcon color="action" />
            <Typography variant="body2" color="text.secondary">
              分享时间：{new Date(conversation.createdAt).toLocaleString()}
            </Typography>
          </Box>
        </Box>
      </Paper>
      
      {/* 会话内容 */}
      <Paper 
        elevation={0} 
        sx={{ 
          p: 3,
          backgroundColor: 'background.paper',
          borderRadius: 2,
          border: 1,
          borderColor: 'divider'
        }}
      >
        {conversation.messages.map((message, index) => (
          <Box key={index} sx={{ mb: 3 }}>
            <Box 
              sx={{ 
                display: 'flex', 
                alignItems: 'center', 
                gap: 1, 
                mb: 1,
                color: message.role === 'user' ? 'primary.main' : 'secondary.main'
              }}
            >
              <Chip
                icon={message.role === 'user' ? <PersonIcon /> : <ShareIcon />}
                label={message.role === 'user' ? '用户' : 'AI助手'}
                size="small"
                color={message.role === 'user' ? 'primary' : 'secondary'}
                variant="outlined"
              />
              {message.model && (
                <Chip
                  label={message.model}
                  size="small"
                  variant="outlined"
                />
              )}
            </Box>
            
            <Paper
              elevation={0}
              sx={{
                p: 2,
                backgroundColor: message.role === 'user' ? 'action.hover' : 'background.default',
                borderRadius: 2,
                border: 1,
                borderColor: 'divider'
              }}
            >
              <Box className="markdown-content">
                <ReactMarkdown>{message.content}</ReactMarkdown>
              </Box>
            </Paper>
          </Box>
        ))}
      </Paper>
    </Container>
  );
};

export default SharedConversation; 