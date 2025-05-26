import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  TextField,
  Button,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Paper,
  Alert,
  Snackbar
} from '@mui/material';
import { Delete as DeleteIcon, Add as AddIcon } from '@mui/icons-material';
import { addModel, getModels } from '../services/apiService';

const Settings = ({ onClose }) => {
  const [models, setModels] = useState([]);
  const [newModel, setNewModel] = useState({ name: '', apiKey: '', id: '' });
  const [openDialog, setOpenDialog] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadModels();
  }, []);

  const loadModels = async () => {
    try {
      const savedModels = await getModels();
      setModels(savedModels);
    } catch (error) {
      setError('Failed to load models');
    }
  };

  const handleAddModel = async () => {
    if (newModel.name && newModel.apiKey) {
      setLoading(true);
      try {
        // 生成一个唯一的id，使用模型名称的小写形式，将空格替换为连字符
        const modelId = newModel.name.toLowerCase().replace(/\s+/g, '-');
        const modelWithId = {
          ...newModel,
          id: modelId
        };
        
        await addModel(modelWithId);
        await loadModels(); // 重新加载模型列表
        setNewModel({ name: '', apiKey: '', id: '' });
        setOpenDialog(false);
      } catch (error) {
        setError('Failed to add model');
      } finally {
        setLoading(false);
      }
    }
  };

  const handleDeleteModel = async (index) => {
    try {
      const modelToDelete = models[index];
      // TODO: 添加删除模型的API调用
      const updatedModels = models.filter((_, i) => i !== index);
      setModels(updatedModels);
    } catch (error) {
      setError('Failed to delete model');
    }
  };

  return (
    <Box sx={{ p: 3, maxWidth: 600, margin: '0 auto' }}>
      <Typography variant="h5" gutterBottom>
        设置
      </Typography>
      
      <Paper sx={{ p: 2, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          AI模型管理
        </Typography>
        
        <List>
          {models.map((model, index) => (
            <ListItem key={index}>
              <ListItemText
                primary={model.name}
                secondary={`API Key: ${model.apiKey.substring(0, 4)}...${model.apiKey.substring(model.apiKey.length - 4)}`}
              />
              <ListItemSecondaryAction>
                <IconButton edge="end" onClick={() => handleDeleteModel(index)}>
                  <DeleteIcon />
                </IconButton>
              </ListItemSecondaryAction>
            </ListItem>
          ))}
        </List>

        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => setOpenDialog(true)}
          sx={{ mt: 2 }}
          disabled={loading}
        >
          添加新模型
        </Button>
      </Paper>

      <Dialog open={openDialog} onClose={() => setOpenDialog(false)}>
        <DialogTitle>添加新模型</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label="模型名称"
            fullWidth
            value={newModel.name}
            onChange={(e) => setNewModel({ ...newModel, name: e.target.value })}
            helperText="模型名称将用于显示在下拉菜单中"
            disabled={loading}
          />
          <TextField
            margin="dense"
            label="API Key"
            fullWidth
            value={newModel.apiKey}
            onChange={(e) => setNewModel({ ...newModel, apiKey: e.target.value })}
            helperText="输入模型的API密钥"
            disabled={loading}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenDialog(false)} disabled={loading}>取消</Button>
          <Button onClick={handleAddModel} variant="contained" disabled={loading}>
            添加
          </Button>
        </DialogActions>
      </Dialog>

      <Button
        variant="contained"
        color="primary"
        onClick={onClose}
        sx={{ mt: 2 }}
      >
        返回
      </Button>

      <Snackbar
        open={!!error}
        autoHideDuration={6000}
        onClose={() => setError('')}
      >
        <Alert onClose={() => setError('')} severity="error">
          {error}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default Settings; 