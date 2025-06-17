import React, { useState, useEffect, useRef } from 'react';
import {
  Box,
  Paper,
  Typography,
  TextField,
  Button,
  List,
  ListItem,
  ListItemText,
  ListItemButton,
  Chip,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Divider,
  IconButton,
  Tooltip,
  Grid,
  Card,
  CardContent,
  Autocomplete,
  Fab
} from '@mui/material';
import {
  ExpandMore as ExpandMoreIcon,
  LightbulbOutlined as LightbulbIcon,
  AutoAwesome as AutoAwesomeIcon,
  ContentCopy as CopyIcon,
  Add as AddIcon,
  Close as CloseIcon,
  Search as SearchIcon
} from '@mui/icons-material';

const PromptHelper = ({ open, onClose, onApplyPrompt, userInput, setUserInput }) => {
  const [categories, setCategories] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [suggestions, setSuggestions] = useState([]);
  const [autoCompletions, setAutoCompletions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedTemplate, setSelectedTemplate] = useState(null);
  const [placeholders, setPlaceholders] = useState({});
  const [searchQuery, setSearchQuery] = useState('');
  const [expandedAccordion, setExpandedAccordion] = useState('templates');

  const inputRef = useRef(null);

  // 获取分类列表
  useEffect(() => {
    fetchCategories();
    fetchAllTemplates();
  }, []);

  // 根据用户输入获取智能建议
  useEffect(() => {
    if (userInput && userInput.trim().length > 3) {
      const debounceTimer = setTimeout(() => {
        fetchSuggestions(userInput);
      }, 500);
      return () => clearTimeout(debounceTimer);
    } else {
      setSuggestions([]);
    }
  }, [userInput]);

  const fetchCategories = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/prompts/categories', {
        credentials: 'include'
      });
      const data = await response.json();
      setCategories(['全部', ...data.categories]);
    } catch (error) {
      console.error('获取分类失败:', error);
    }
  };

  const fetchAllTemplates = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/prompts/templates', {
        credentials: 'include'
      });
      const data = await response.json();
      setTemplates(data.templates);
    } catch (error) {
      console.error('获取模板失败:', error);
    }
  };

  const fetchSuggestions = async (input) => {
    try {
      setLoading(true);
      const response = await fetch('http://localhost:8000/api/prompts/suggest', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({ user_input: input, limit: 5 })
      });
      const data = await response.json();
      setSuggestions(data.suggestions || []);
    } catch (error) {
      console.error('获取建议失败:', error);
      setSuggestions([]);
    } finally {
      setLoading(false);
    }
  };

  const fetchAutoCompletions = async (partialInput) => {
    try {
      const response = await fetch('http://localhost:8000/api/prompts/autocomplete', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({ partial_input: partialInput })
      });
      const data = await response.json();
      setAutoCompletions(data.completions || []);
    } catch (error) {
      console.error('获取自动补全失败:', error);
      setAutoCompletions([]);
    }
  };

  const applyTemplate = async (templateId, placeholderValues = {}) => {
    try {
      setLoading(true);
      const response = await fetch('http://localhost:8000/api/prompts/apply', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
          template_id: templateId,
          user_input: userInput,
          placeholders: placeholderValues
        })
      });
      const data = await response.json();
      if (data.applied_prompt) {
        setUserInput(data.applied_prompt);
        onApplyPrompt(data.applied_prompt);
        onClose();
      }
    } catch (error) {
      console.error('应用模板失败:', error);
    } finally {
      setLoading(false);
    }
  };

  // 过滤模板
  const filteredTemplates = templates.filter(template => {
    const matchesCategory = selectedCategory === 'all' || selectedCategory === '全部' || template.category === selectedCategory;
    const matchesSearch = !searchQuery || 
      template.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      template.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
      template.keywords?.some(keyword => keyword.toLowerCase().includes(searchQuery.toLowerCase()));
    return matchesCategory && matchesSearch;
  });

  const handleTemplateSelect = (template) => {
    // 检查模板是否有占位符
    const placeholderMatches = template.template.match(/{{\{([^}]+)\}\}}/g);
    if (placeholderMatches && placeholderMatches.length > 0) {
      setSelectedTemplate(template);
      const initialPlaceholders = {};
      placeholderMatches.forEach(match => {
        const key = match.replace(/[{}]/g, '');
        initialPlaceholders[key] = '';
      });
      setPlaceholders(initialPlaceholders);
    } else {
      // 直接应用模板
      applyTemplate(template.id);
    }
  };

  const handlePlaceholderSubmit = () => {
    if (selectedTemplate) {
      applyTemplate(selectedTemplate.id, placeholders);
      setSelectedTemplate(null);
      setPlaceholders({});
    }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
  };

  return (
    <>
      <Dialog 
        open={open} 
        onClose={onClose} 
        maxWidth="md" 
        fullWidth
        PaperProps={{
          sx: { 
            height: '80vh', 
            display: 'flex', 
            flexDirection: 'column',
            '& .MuiDialogTitle-root': {
              borderBottom: 'none',
            }
          }
        }}
      >
        <DialogTitle sx={{ pb: 2, pt: 3, borderBottom: 'none' }}>
          <Box display="flex" alignItems="center" gap={1}>
            <LightbulbIcon color="primary" />
            <Typography variant="h6">智能提示词助手</Typography>
          </Box>
        </DialogTitle>
        
        <DialogContent sx={{ 
          flex: 1, 
          overflow: 'hidden', 
          pt: 1, 
          '&.MuiDialogContent-root': { 
            paddingTop: '8px',
            borderTop: 'none'
          } 
        }}>
          <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column', gap: 2 }}>
            
            {/* 搜索和筛选 */}
            <Box display="flex" gap={2} alignItems="center" sx={{ mb: 1, mt: 0 }}>
              <TextField
                label="搜索模板"
                variant="outlined"
                size="small"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                InputProps={{
                  endAdornment: <SearchIcon color="action" />
                }}
                sx={{ flex: 1 }}
              />
              <FormControl size="small" sx={{ minWidth: 100, zIndex: 1 }}>
                <InputLabel 
                  id="category-select-label" 
                  sx={{ 
                    zIndex: 1000,
                    color: 'text.secondary',
                    backgroundColor: 'transparent',
                    '&.Mui-focused': {
                      color: 'text.secondary',
                      zIndex: 1000
                    },
                    '&.MuiInputLabel-shrink': {
                      color: 'text.secondary',
                      zIndex: 1000,
                      backgroundColor: 'white',
                      paddingX: 0.5
                    }
                  }}
                >
                  分类
                </InputLabel>
                <Select
                  labelId="category-select-label"
                  value={selectedCategory}
                  onChange={(e) => setSelectedCategory(e.target.value)}
                  label="分类"
                  sx={{
                    width: 100,
                    zIndex: 1,
                    '& .MuiInputLabel-root': {
                      fontSize: '0.875rem',
                      zIndex: 1000,
                    },
                    '& .MuiSelect-select': {
                      fontSize: '0.875rem',
                      paddingRight: '24px !important',
                      zIndex: 1
                    },
                    '& .MuiOutlinedInput-notchedOutline': {
                      borderColor: 'rgba(0, 0, 0, 0.23)',
                      zIndex: 1
                    },
                    '& .MuiInputBase-root': {
                      zIndex: 1
                    }
                  }}
                  MenuProps={{
                    PaperProps: {
                      sx: { zIndex: 9999 }
                    }
                  }}
                >
                  {categories.map(category => (
                    <MenuItem key={category} value={category} sx={{ fontSize: '0.875rem' }}>
                      {category}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Box>

            <Box sx={{ flex: 1, overflow: 'auto' }}>
              {/* 智能建议 */}
              {suggestions.length > 0 && (
                <Accordion 
                  expanded={expandedAccordion === 'suggestions'}
                  onChange={() => setExpandedAccordion(expandedAccordion === 'suggestions' ? '' : 'suggestions')}
                >
                  <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                    <Box display="flex" alignItems="center" gap={1}>
                      <AutoAwesomeIcon color="secondary" />
                      <Typography>智能建议 ({suggestions.length})</Typography>
                    </Box>
                  </AccordionSummary>
                  <AccordionDetails>
                    <Grid container spacing={2}>
                      {suggestions.map((suggestion, index) => (
                        <Grid item xs={12} sm={6} key={index}>
                          <Card 
                            variant="outlined" 
                            sx={{ 
                              cursor: 'pointer',
                              '&:hover': { boxShadow: 2 }
                            }}
                            onClick={() => handleTemplateSelect(suggestion)}
                          >
                            <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
                              <Typography variant="subtitle2" gutterBottom>
                                {suggestion.title}
                              </Typography>
                              <Typography variant="body2" color="text.secondary" noWrap>
                                {suggestion.description}
                              </Typography>
                              <Box mt={1}>
                                <Chip 
                                  label={suggestion.category} 
                                  size="small" 
                                  color="primary" 
                                  variant="outlined"
                                />
                                <Chip 
                                  label={`${suggestion.relevance_score}% 匹配`} 
                                  size="small" 
                                  color="secondary" 
                                  variant="outlined"
                                  sx={{ ml: 1 }}
                                />
                              </Box>
                            </CardContent>
                          </Card>
                        </Grid>
                      ))}
                    </Grid>
                  </AccordionDetails>
                </Accordion>
              )}

              {/* 模板列表 */}
              <Accordion 
                expanded={expandedAccordion === 'templates'}
                onChange={() => setExpandedAccordion(expandedAccordion === 'templates' ? '' : 'templates')}
              >
                <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                  <Typography>提示词模板 ({filteredTemplates.length})</Typography>
                </AccordionSummary>
                <AccordionDetails>
                  <Grid container spacing={2}>
                    {filteredTemplates.map((template) => (
                      <Grid item xs={12} sm={6} key={template.id}>
                        <Card 
                          variant="outlined" 
                          sx={{ 
                            cursor: 'pointer',
                            '&:hover': { boxShadow: 2 }
                          }}
                          onClick={() => handleTemplateSelect(template)}
                        >
                          <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
                            <Box display="flex" justifyContent="space-between" alignItems="start">
                              <Box flex={1}>
                                <Typography variant="subtitle2" gutterBottom>
                                  {template.title}
                                </Typography>
                                <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                                  {template.description}
                                </Typography>
                                <Box display="flex" flexWrap="wrap" gap={0.5}>
                                  <Chip 
                                    label={template.category} 
                                    size="small" 
                                    color="primary" 
                                    variant="outlined"
                                  />
                                  {template.keywords?.slice(0, 2).map((keyword, idx) => (
                                    <Chip 
                                      key={idx}
                                      label={keyword} 
                                      size="small" 
                                      variant="outlined"
                                    />
                                  ))}
                                </Box>
                              </Box>
                              <IconButton 
                                size="small" 
                                onClick={(e) => {
                                  e.stopPropagation();
                                  copyToClipboard(template.template);
                                }}
                              >
                                <CopyIcon fontSize="small" />
                              </IconButton>
                            </Box>
                          </CardContent>
                        </Card>
                      </Grid>
                    ))}
                  </Grid>
                </AccordionDetails>
              </Accordion>
            </Box>
          </Box>
        </DialogContent>
        
        <DialogActions>
          <Button onClick={onClose}>关闭</Button>
        </DialogActions>
      </Dialog>

      {/* 占位符填写对话框 */}
      <Dialog open={!!selectedTemplate} onClose={() => setSelectedTemplate(null)} maxWidth="sm" fullWidth>
        <DialogTitle>填写模板参数</DialogTitle>
        <DialogContent>
          {selectedTemplate && (
            <Box sx={{ mt: 2 }}>
              <Typography variant="body2" color="text.secondary" gutterBottom>
                {selectedTemplate.description}
              </Typography>
              <Divider sx={{ my: 2 }} />
              {Object.keys(placeholders).map((key) => (
                <TextField
                  key={key}
                  label={key}
                  fullWidth
                  margin="normal"
                  value={placeholders[key]}
                  onChange={(e) => setPlaceholders(prev => ({ ...prev, [key]: e.target.value }))}
                  placeholder={`请输入 ${key}`}
                />
              ))}
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setSelectedTemplate(null)}>取消</Button>
          <Button 
            onClick={handlePlaceholderSubmit} 
            variant="contained"
            disabled={Object.values(placeholders).some(value => !value.trim())}
          >
            应用模板
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
};

export default PromptHelper; 