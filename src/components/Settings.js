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
} from '@mui/material';
import { Delete as DeleteIcon, Add as AddIcon } from '@mui/icons-material';

const Settings = ({ onClose }) => {
  const [models, setModels] = useState([]);
  const [newModel, setNewModel] = useState({ name: '', apiKey: '' });
  const [openDialog, setOpenDialog] = useState(false);

  useEffect(() => {
    // 从localStorage加载已保存的模型
    const savedModels = JSON.parse(localStorage.getItem('aiModels') || '[]');
    setModels(savedModels);
  }, []);

  const handleAddModel = () => {
    if (newModel.name && newModel.apiKey) {
      // 生成一个唯一的id，使用模型名称的小写形式，将空格替换为连字符
      const modelId = newModel.name.toLowerCase().replace(/\s+/g, '-');
      const modelWithId = {
        ...newModel,
        id: modelId
      };
      
      const updatedModels = [...models, modelWithId];
      setModels(updatedModels);
      localStorage.setItem('aiModels', JSON.stringify(updatedModels));
      setNewModel({ name: '', apiKey: '', id: '' });
      setOpenDialog(false);
    }
  };

  const handleDeleteModel = (index) => {
    const updatedModels = models.filter((_, i) => i !== index);
    setModels(updatedModels);
    localStorage.setItem('aiModels', JSON.stringify(updatedModels));
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
          />
          <TextField
            margin="dense"
            label="API Key"
            fullWidth
            value={newModel.apiKey}
            onChange={(e) => setNewModel({ ...newModel, apiKey: e.target.value })}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenDialog(false)}>取消</Button>
          <Button onClick={handleAddModel} variant="contained">
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
    </Box>
  );
};

export default Settings; 