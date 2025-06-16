import React, { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  Box,
  Typography,
  IconButton,
  Snackbar,
  Alert,
  Paper,
  Tooltip
} from '@mui/material';
import { ContentCopy as CopyIcon, Share as ShareIcon } from '@mui/icons-material';
import { shareConversation } from '../services/apiService';

const ShareDialog = ({ open, onClose, conversationId }) => {
  const [shareLink, setShareLink] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [copySuccess, setCopySuccess] = useState(false);

  const handleShare = async () => {
    setLoading(true);
    try {
      const result = await shareConversation(conversationId);
      const shareUrl = `${window.location.origin}/shared/${result.shareId}`;
      setShareLink(shareUrl);
    } catch (error) {
      setError('分享失败，请稍后重试');
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(shareLink);
    setCopySuccess(true);
  };

  const handleClose = () => {
    setShareLink('');
    setError('');
    setCopySuccess(false);
    onClose();
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
      <DialogTitle sx={{ 
        display: 'flex', 
        alignItems: 'center', 
        gap: 1,
        borderBottom: 1,
        borderColor: 'divider',
        pb: 2
      }}>
        <ShareIcon color="primary" />
        分享会话
      </DialogTitle>
      <DialogContent>
        <Box sx={{ mt: 2 }}>
          {!shareLink ? (
            <Paper 
              elevation={0} 
              sx={{ 
                p: 3, 
                textAlign: 'center',
                backgroundColor: 'background.default',
                borderRadius: 2
              }}
            >
              <ShareIcon sx={{ fontSize: 48, color: 'primary.main', mb: 2 }} />
              <Typography variant="h6" gutterBottom>
                生成分享链接
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                生成链接后，其他用户可以通过此链接查看您的会话内容
              </Typography>
              <Button
                variant="contained"
                onClick={handleShare}
                disabled={loading}
                startIcon={<ShareIcon />}
                size="large"
              >
                {loading ? '生成中...' : '生成分享链接'}
              </Button>
            </Paper>
          ) : (
            <Paper 
              elevation={0} 
              sx={{ 
                p: 3,
                backgroundColor: 'background.default',
                borderRadius: 2
              }}
            >
              <Typography variant="subtitle1" gutterBottom>
                分享链接已生成
              </Typography>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                <TextField
                  fullWidth
                  value={shareLink}
                  variant="outlined"
                  InputProps={{
                    readOnly: true,
                  }}
                  sx={{
                    '& .MuiOutlinedInput-root': {
                      backgroundColor: 'background.paper'
                    }
                  }}
                />
                <Tooltip title="复制链接">
                  <IconButton 
                    onClick={handleCopy} 
                    color="primary"
                    sx={{ 
                      border: 1,
                      borderColor: 'divider',
                      '&:hover': {
                        borderColor: 'primary.main'
                      }
                    }}
                  >
                    <CopyIcon />
                  </IconButton>
                </Tooltip>
              </Box>
              <Typography variant="body2" color="text.secondary">
                复制此链接并分享给其他用户，他们可以通过此链接查看您的会话内容
              </Typography>
            </Paper>
          )}
        </Box>
      </DialogContent>
      <DialogActions sx={{ px: 3, py: 2, borderTop: 1, borderColor: 'divider' }}>
        <Button onClick={handleClose} variant="outlined">
          关闭
        </Button>
      </DialogActions>

      <Snackbar
        open={!!error}
        autoHideDuration={6000}
        onClose={() => setError('')}
      >
        <Alert onClose={() => setError('')} severity="error">
          {error}
        </Alert>
      </Snackbar>

      <Snackbar
        open={copySuccess}
        autoHideDuration={2000}
        onClose={() => setCopySuccess(false)}
      >
        <Alert onClose={() => setCopySuccess(false)} severity="success">
          链接已复制到剪贴板
        </Alert>
      </Snackbar>
    </Dialog>
  );
};

export default ShareDialog; 