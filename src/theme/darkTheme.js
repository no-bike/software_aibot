import { createTheme } from '@mui/material/styles';

const darkTheme = createTheme({
  palette: {
    mode: 'dark',
    primary: {
      main: '#4a9eff',
      light: '#7bb8ff',
      dark: '#2c7cd1',
      contrastText: '#ffffff',
    },
    secondary: {
      main: '#50fa7b',
      light: '#7dfb93',
      dark: '#3dd865',
      contrastText: '#000000',
    },
    error: {
      main: '#ff6b6b',
      light: '#ff9999',
      dark: '#cc5555',
    },
    warning: {
      main: '#ffa726',
      light: '#ffcc80',
      dark: '#ff8f00',
    },
    info: {
      main: '#29b6f6',
      light: '#73e8ff',
      dark: '#0086c3',
    },
    success: {
      main: '#66bb6a',
      light: '#98ee99',
      dark: '#338a3e',
    },
    background: {
      default: '#0d1117',
      paper: '#161b22',
    },
    surface: {
      main: '#21262d',
      light: '#30363d',
      dark: '#1c2128',
    },
    text: {
      primary: '#f0f6fc',
      secondary: '#8b949e',
      disabled: '#484f58',
    },
    divider: '#30363d',
    action: {
      active: '#f0f6fc',
      hover: 'rgba(240, 246, 252, 0.08)',
      selected: 'rgba(240, 246, 252, 0.12)',
      disabled: '#484f58',
      disabledBackground: '#21262d',
    },
  },
  typography: {
    fontFamily: [
      '-apple-system',
      'BlinkMacSystemFont',
      '"Segoe UI"',
      'Roboto',
      '"Helvetica Neue"',
      'Arial',
      'sans-serif',
    ].join(','),
    h1: {
      color: '#f0f6fc',
      fontWeight: 600,
    },
    h2: {
      color: '#f0f6fc',
      fontWeight: 600,
    },
    h3: {
      color: '#f0f6fc',
      fontWeight: 600,
    },
    h4: {
      color: '#f0f6fc',
      fontWeight: 600,
    },
    h5: {
      color: '#f0f6fc',
      fontWeight: 600,
    },
    h6: {
      color: '#f0f6fc',
      fontWeight: 600,
    },
    body1: {
      color: '#f0f6fc',
    },
    body2: {
      color: '#8b949e',
    },
    caption: {
      color: '#8b949e',
    },
  },
  shape: {
    borderRadius: 8,
  },
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        body: {
          backgroundColor: '#0d1117',
          color: '#f0f6fc',
          scrollbarColor: '#484f58 #21262d',
          '&::-webkit-scrollbar': {
            width: '8px',
            height: '8px',
          },
          '&::-webkit-scrollbar-track': {
            background: '#21262d',
          },
          '&::-webkit-scrollbar-thumb': {
            background: '#484f58',
            borderRadius: '4px',
            '&:hover': {
              background: '#6e7681',
            },
          },
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundColor: '#161b22',
          border: '1px solid #30363d',
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: 'none',
          borderRadius: '6px',
          fontWeight: 500,
        },
        contained: {
          backgroundColor: '#238636',
          color: '#ffffff',
          '&:hover': {
            backgroundColor: '#2ea043',
          },
        },
        outlined: {
          borderColor: '#30363d',
          color: '#f0f6fc',
          '&:hover': {
            borderColor: '#8b949e',
            backgroundColor: 'rgba(240, 246, 252, 0.08)',
          },
        },
      },
    },
    MuiTextField: {
      styleOverrides: {
        root: {
          '& .MuiOutlinedInput-root': {
            backgroundColor: '#0d1117',
            '& fieldset': {
              borderColor: '#30363d',
            },
            '&:hover fieldset': {
              borderColor: '#8b949e',
            },
            '&.Mui-focused fieldset': {
              borderColor: '#4a9eff',
            },
          },
          '& .MuiInputLabel-root': {
            color: '#8b949e',
            '&.Mui-focused': {
              color: '#4a9eff',
            },
          },
          '& .MuiOutlinedInput-input': {
            color: '#f0f6fc',
          },
        },
      },
    },
    MuiSelect: {
      styleOverrides: {
        root: {
          backgroundColor: '#0d1117',
          '& .MuiOutlinedInput-notchedOutline': {
            borderColor: '#30363d',
          },
          '&:hover .MuiOutlinedInput-notchedOutline': {
            borderColor: '#8b949e',
          },
          '&.Mui-focused .MuiOutlinedInput-notchedOutline': {
            borderColor: '#4a9eff',
          },
        },
      },
    },
    MuiMenuItem: {
      styleOverrides: {
        root: {
          backgroundColor: '#161b22',
          color: '#f0f6fc',
          '&:hover': {
            backgroundColor: '#21262d',
          },
          '&.Mui-selected': {
            backgroundColor: '#1f6feb',
            '&:hover': {
              backgroundColor: '#1a63d7',
            },
          },
        },
      },
    },
    MuiListItem: {
      styleOverrides: {
        root: {
          '&.Mui-selected': {
            backgroundColor: '#1f6feb',
            '&:hover': {
              backgroundColor: '#1a63d7',
            },
          },
          '&:hover': {
            backgroundColor: 'rgba(240, 246, 252, 0.08)',
          },
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          backgroundColor: '#21262d',
          color: '#f0f6fc',
          border: '1px solid #30363d',
        },
      },
    },
    MuiSwitch: {
      styleOverrides: {
        root: {
          '& .MuiSwitch-switchBase.Mui-checked': {
            color: '#4a9eff',
            '& + .MuiSwitch-track': {
              backgroundColor: '#4a9eff',
            },
          },
        },
        track: {
          backgroundColor: '#30363d',
        },
      },
    },
    MuiIconButton: {
      styleOverrides: {
        root: {
          color: '#8b949e',
          '&:hover': {
            backgroundColor: 'rgba(240, 246, 252, 0.08)',
            color: '#f0f6fc',
          },
        },
      },
    },
    MuiDialog: {
      styleOverrides: {
        paper: {
          backgroundColor: '#161b22',
          border: '1px solid #30363d',
        },
      },
    },
    MuiDialogTitle: {
      styleOverrides: {
        root: {
          color: '#f0f6fc',
          borderBottom: '1px solid #30363d',
        },
      },
    },
    MuiDialogContent: {
      styleOverrides: {
        root: {
          color: '#f0f6fc',
        },
      },
    },
    MuiTooltip: {
      styleOverrides: {
        tooltip: {
          backgroundColor: '#21262d',
          color: '#f0f6fc',
          border: '1px solid #30363d',
          fontSize: '0.75rem',
        },
        arrow: {
          color: '#21262d',
        },
      },
    },
  },
});

export default darkTheme;
