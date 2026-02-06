# RiverAI - 河流岸线空间智能感知系统

[English](./README.md) | [中文](#chinese)

<a name="chinese"></a>

## 📖 项目简介

RiverAI 是一个基于大语言模型的河流岸线空间智能感知系统,集成了知识库检索、文档问答和智能工具调用功能。系统支持 PDF 文档自动解析与向量化存储,能够基于专业文献进行智能问答,并提供水体提取等专业工具。

### ✨ 核心特性

- 🤖 **智能对话系统**: 基于 DeepSeek/Qwen 等大模型的流式对话
- 📚 **知识库管理**: 自动解析 PDF 文档并构建向量知识库
- 🔍 **语义检索**: 基于 BGE 中文向量模型的文档检索
- 🛠️ **工具调用**: Agent 模式支持水体提取等专业工具
- 👥 **用户系统**: 完整的用户认证与会话管理
- 💬 **多会话管理**: 支持创建、切换和管理多个对话
- 🎨 **现代化 UI**: 基于 React + TailwindCSS 的响应式界面

## 🏗️ 技术架构

### 后端技术栈

- **框架**: FastAPI + Uvicorn
- **AI 框架**: Agno (Agent 编排框架)
- **数据库**: SQLite + SQLModel
- **向量数据库**: LanceDB
- **嵌入模型**: FastEmbed (BAAI/bge-small-zh-v1.5)
- **LLM 支持**: DeepSeek, DashScope (Qwen)

### 前端技术栈

- **框架**: React 19 + TypeScript
- **构建工具**: Vite
- **样式**: TailwindCSS 4
- **状态管理**: Zustand
- **路由**: React Router v7
- **Markdown 渲染**: react-markdown + remark-gfm
- **流式传输**: @microsoft/fetch-event-source

## 📦 安装部署

### 环境要求

- Python 3.9+
- Node.js 18+
- npm/yarn/pnpm

### 1. 克隆项目

```bash
git clone https://github.com/yourusername/rss.git
cd rss
```

### 2. 后端配置

```bash
cd backend

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install fastapi uvicorn sqlmodel passlib[bcrypt] python-dotenv
pip install agno lancedb fastembed
pip install sse-starlette pillow pypdf

# 配置环境变量
# 在 backend 目录创建 .env 文件
```

**`.env` 配置示例:**

```env
DEEPSEEK_API_KEY=your_deepseek_api_key
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
DEEPSEEK_MODEL=deepseek-chat

# 可选: DashScope (Qwen)
DASHSCOPE_API_KEY=your_dashscope_api_key
DASHSCOPE_MODEL=qwen3-vl-32b-instruct
```

### 3. 前端配置

```bash
cd frontend

# 安装依赖
npm install
# 或
pnpm install
```

### 4. 启动服务

**启动后端:**

```bash
cd backend
python main.py
# 后端运行在 http://localhost:8006
```

**启动前端:**

```bash
cd frontend
npm run dev
# 前端运行在 http://localhost:5175
```

## 🚀 使用指南

### 首次登录

- 默认管理员账号: `admin`
- 默认密码: `admin123`
- 登录后建议立即修改密码

### 上传文档

1. 将 PDF 文档放入 `backend/data/uploads/` 目录
2. 系统会自动检测并解析新文档
3. 文档内容将被向量化并存入知识库

### 对话模式

- **Chat 模式**: 纯对话模式,基于知识库回答问题
- **Agent 模式**: 启用工具调用,可执行水体提取等任务

### API 端点

- `POST /auth/login` - 用户登录
- `GET /chat/conversations` - 获取会话列表
- `POST /chat/send` - 发送消息
- `POST /chat/stream` - 流式对话
- `POST /upload/pdf` - 上传 PDF 文档

## 📁 项目结构

```
rss/
├── backend/                 # 后端服务
│   ├── app/
│   │   ├── agents/         # AI Agent 实现
│   │   │   ├── river_agent.py    # 主 Agent
│   │   │   └── memory.py         # 记忆管理
│   │   ├── api/            # API 路由
│   │   │   ├── auth.py           # 认证接口
│   │   │   ├── chat.py           # 对话接口
│   │   │   └── upload.py         # 文件上传
│   │   ├── core/           # 核心配置
│   │   │   ├── config.py         # 配置管理
│   │   │   └── db.py             # 数据库连接
│   │   ├── db/             # 数据模型
│   │   │   └── models.py         # SQLModel 模型
│   │   ├── tools/          # Agent 工具
│   │   │   └── water.py          # 水体提取工具
│   │   └── utils/          # 工具函数
│   ├── data/               # 数据目录
│   │   ├── uploads/              # PDF 上传目录
│   │   ├── lancedb/              # 向量数据库
│   │   └── models/               # 嵌入模型缓存
│   └── main.py             # 应用入口
├── frontend/               # 前端应用
│   ├── src/
│   │   ├── components/     # React 组件
│   │   │   ├── ChatArea.tsx      # 聊天区域
│   │   │   ├── Sidebar.tsx       # 侧边栏
│   │   │   └── ConfigPanel.tsx   # 配置面板
│   │   ├── pages/          # 页面组件
│   │   │   ├── LoginPage.tsx     # 登录页
│   │   │   └── ChatPage.tsx      # 聊天页
│   │   ├── lib/            # 工具库
│   │   │   ├── api.ts            # API 封装
│   │   │   ├── store.ts          # Zustand 状态
│   │   │   └── utils.ts          # 工具函数
│   │   ├── App.tsx         # 应用根组件
│   │   └── main.tsx        # 入口文件
│   ├── package.json
│   └── vite.config.ts
├── docs/                   # 文档资料
└── README.md
```

## 🔧 配置说明

### 模型配置

系统支持多种 LLM 提供商:

1. **DeepSeek**: 高性价比,支持函数调用
2. **DashScope (Qwen)**: 阿里云通义千问系列

在 `.env` 文件中配置相应的 API Key 和 Base URL。

### 嵌入模型

默认使用 `BAAI/bge-small-zh-v1.5` 中文嵌入模型,首次运行会自动下载到 `backend/data/models/` 目录。

### 数据库

- SQLite 数据库文件: `backend/data/riverai.sqlite`
- 向量数据库: `backend/data/lancedb/`

## 🛠️ 开发指南

### 后端开发

```bash
cd backend
# 开启热重载
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8006
```

### 前端开发

```bash
cd frontend
npm run dev
```

### 代码规范

- 后端: 遵循 PEP 8 规范
- 前端: 使用 ESLint 进行代码检查

## 📝 开发路线图

- [ ] 支持更多文档格式 (Word, Excel, Markdown)
- [ ] 增强水体提取算法
- [ ] 添加用户权限管理
- [ ] 支持多模态输入 (图片上传)
- [ ] 优化向量检索性能
- [ ] 添加对话导出功能
- [ ] Docker 容器化部署
- [ ] API 文档 (Swagger/OpenAPI)

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request!

1. Fork 本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## 🙏 致谢

- [Agno](https://github.com/agno-agi/agno) - AI Agent 框架
- [LanceDB](https://lancedb.com/) - 向量数据库
- [FastEmbed](https://github.com/qdrant/fastembed) - 嵌入模型
- [DeepSeek](https://www.deepseek.com/) - 大语言模型

## 📧 联系方式

如有问题或建议,请提交 Issue 或联系项目维护者。

---

**如果觉得有帮助,请给项目点个 Star ⭐**
