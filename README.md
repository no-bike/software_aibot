# AI Chat Application

这是一个基于 Electron 和 React 的 AI 聊天应用程序。

## 系统要求

- Node.js (推荐 v16 或更高版本)
- npm (通常随 Node.js 一起安装)

## 安装步骤

1. 克隆仓库
```bash
git clone [你的仓库URL]
cd [仓库目录名]
```

2. 安装依赖
```bash
npm install
```

## 运行应用

### 开发模式
```bash
npm run dev
```
这将启动开发服务器并运行 Electron 应用。

### 生产模式
```bash
# 构建应用
npm run build

# 运行应用
npm start
```

## 项目结构

- `src/` - React 前端源代码
- `public/` - 静态资源文件
- `main.js` - Electron 主进程文件
- `webpack.config.js` - Webpack 配置文件

## 配置说明

1. 首次运行时，需要在设置中添加 AI 模型配置：
   - 点击"设置"按钮
   - 添加新模型，填写以下信息：
     - 模型名称（例如：GPT-4）
     - API Key
     - API URL（可选，会根据模型类型自动设置默认值）

2. 支持的模型类型：
   - GPT 模型（默认 URL: https://api.openai.com/v1）
   - Claude 模型（默认 URL: https://api.anthropic.com）
   - 其他模型（默认 URL: https://api.example.com/v1）

## 常见问题

如果遇到问题，请确保：
1. Node.js 版本正确
2. 所有依赖都已正确安装
3. 开发服务器端口（3000）未被占用

## 构建应用

要构建可执行文件：
```bash
npm run package
```
构建完成后，可执行文件将在 `dist` 目录中生成。

## 技术栈

- Electron
- React
- Material-UI
- Webpack

## 功能特性

- 实时对话
- 对话历史管理
- 模型切换
- 标题编辑
- 历史记录搜索
- 新建对话 