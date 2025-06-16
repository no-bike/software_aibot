import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Paper,
  CircularProgress,
  Alert,
  Divider
} from '@mui/material';
import ReactMarkdown from 'react-markdown';
import { getSharedConversation } from '../services/apiService';

const SharedConversation = ({ shareId }) => {
  const [conversation, setConversation] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchSharedConversation = async () => {
      try {
        const data = await getSharedConversation(shareId);
        setConversation(data.conversation);
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
    <Box sx={{ maxWidth: 800, mx: 'auto', p: 3 }}>
      <Typography variant="h4" gutterBottom>
        {conversation.title || '分享的会话'}
      </Typography>
      <Divider sx={{ mb: 3 }} />
      
      {conversation.messages.map((message, index) => (
        <Paper
          key={index}
          elevation={1}
          sx={{
            p: 2,
            mb: 2,
            backgroundColor: message.role === 'user' ? '#f5f5f5' : '#ffffff',
            borderRadius: 2
          }}
        >
          <Typography
            variant="subtitle2"
            color="text.secondary"
            gutterBottom
          >
            {message.role === 'user' ? '用户' : 'AI助手'}
          </Typography>
          <Box className="markdown-content">
            <ReactMarkdown>{message.content}</ReactMarkdown>
          </Box>
        </Paper>
      ))}
    </Box>
  );
};

export default SharedConversation; 