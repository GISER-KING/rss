# RiverAI - Intelligent River Shoreline Spatial Perception System

[English](#english) | [中文](./README.zh-CN.md)

<a name="english"></a>

## 📖 Overview

RiverAI is an intelligent river shoreline spatial perception system powered by Large Language Models (LLMs). It integrates knowledge base retrieval, document Q&A, and intelligent tool invocation capabilities. The system supports automatic PDF document parsing and vectorization, enabling intelligent Q&A based on professional literature and providing specialized tools such as water body extraction.

### ✨ Key Features

- 🤖 **Intelligent Dialogue System**: Streaming conversations powered by DeepSeek/Qwen LLMs
- 📚 **Knowledge Base Management**: Automatic PDF parsing and vector knowledge base construction
- 🔍 **Semantic Search**: Document retrieval based on BGE Chinese embedding model
- 🛠️ **Tool Invocation**: Agent mode supports specialized tools like water body extraction
- 👥 **User System**: Complete user authentication and session management
- 💬 **Multi-Session Management**: Support for creating, switching, and managing multiple conversations
- 🎨 **Modern UI**: Responsive interface built with React + TailwindCSS

## 🏗️ Technology Stack

### Backend

- **Framework**: FastAPI + Uvicorn
- **AI Framework**: Agno (Agent orchestration framework)
- **Database**: SQLite + SQLModel
- **Vector Database**: LanceDB
- **Embedding Model**: FastEmbed (BAAI/bge-small-zh-v1.5)
- **LLM Support**: DeepSeek, DashScope (Qwen)

### Frontend

- **Framework**: React 19 + TypeScript
- **Build Tool**: Vite
- **Styling**: TailwindCSS 4
- **State Management**: Zustand
- **Routing**: React Router v7
- **Markdown Rendering**: react-markdown + remark-gfm
- **Streaming**: @microsoft/fetch-event-source

## 📦 Installation

### Prerequisites

- Python 3.9+
- Node.js 18+
- npm/yarn/pnpm

### 1. Clone Repository

```bash
git clone https://github.com/yourusername/rss.git
cd rss
```

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install fastapi uvicorn sqlmodel passlib[bcrypt] python-dotenv
pip install agno lancedb fastembed
pip install sse-starlette pillow pypdf

# Configure environment variables
# Create .env file in backend directory
```

**`.env` Configuration Example:**

```env
DEEPSEEK_API_KEY=your_deepseek_api_key
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
DEEPSEEK_MODEL=deepseek-chat

# Optional: DashScope (Qwen)
DASHSCOPE_API_KEY=your_dashscope_api_key
DASHSCOPE_MODEL=qwen3-vl-32b-instruct
```

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install
# or
pnpm install
```

### 4. Start Services

**Start Backend:**

```bash
cd backend
python main.py
# Backend runs at http://localhost:8006
```

**Start Frontend:**

```bash
cd frontend
npm run dev
# Frontend runs at http://localhost:5175
```

## 🚀 Usage Guide

### First Login

- Default admin account: `admin`
- Default password: `admin123`
- It's recommended to change the password immediately after login

### Upload Documents

1. Place PDF documents in `backend/data/uploads/` directory
2. The system will automatically detect and parse new documents
3. Document content will be vectorized and stored in the knowledge base

### Conversation Modes

- **Chat Mode**: Pure conversation mode, answers questions based on knowledge base
- **Agent Mode**: Enables tool invocation for tasks like water body extraction

### API Endpoints

- `POST /auth/login` - User login
- `GET /chat/conversations` - Get conversation list
- `POST /chat/send` - Send message
- `POST /chat/stream` - Streaming conversation
- `POST /upload/pdf` - Upload PDF document

## 📁 Project Structure

```
rss/
├── backend/                 # Backend service
│   ├── app/
│   │   ├── agents/         # AI Agent implementation
│   │   │   ├── river_agent.py    # Main Agent
│   │   │   └── memory.py         # Memory management
│   │   ├── api/            # API routes
│   │   │   ├── auth.py           # Authentication
│   │   │   ├── chat.py           # Chat interface
│   │   │   └── upload.py         # File upload
│   │   ├── core/           # Core configuration
│   │   │   ├── config.py         # Config management
│   │   │   └── db.py             # Database connection
│   │   ├── db/             # Data models
│   │   │   └── models.py         # SQLModel models
│   │   ├── tools/          # Agent tools
│   │   │   └── water.py          # Water extraction tool
│   │   └── utils/          # Utility functions
│   ├── data/               # Data directory
│   │   ├── uploads/              # PDF upload directory
│   │   ├── lancedb/              # Vector database
│   │   └── models/               # Embedding model cache
│   └── main.py             # Application entry
├── frontend/               # Frontend application
│   ├── src/
│   │   ├── components/     # React components
│   │   │   ├── ChatArea.tsx      # Chat area
│   │   │   ├── Sidebar.tsx       # Sidebar
│   │   │   └── ConfigPanel.tsx   # Config panel
│   │   ├── pages/          # Page components
│   │   │   ├── LoginPage.tsx     # Login page
│   │   │   └── ChatPage.tsx      # Chat page
│   │   ├── lib/            # Utility library
│   │   │   ├── api.ts            # API wrapper
│   │   │   ├── store.ts          # Zustand state
│   │   │   └── utils.ts          # Utility functions
│   │   ├── App.tsx         # App root component
│   │   └── main.tsx        # Entry file
│   ├── package.json
│   └── vite.config.ts
├── docs/                   # Documentation
└── README.md
```

## 🔧 Configuration

### Model Configuration

The system supports multiple LLM providers:

1. **DeepSeek**: Cost-effective, supports function calling
2. **DashScope (Qwen)**: Alibaba Cloud Tongyi Qianwen series

Configure the corresponding API Key and Base URL in the `.env` file.

### Embedding Model

Uses `BAAI/bge-small-zh-v1.5` Chinese embedding model by default. It will be automatically downloaded to `backend/data/models/` on first run.

### Database

- SQLite database file: `backend/data/riverai.sqlite`
- Vector database: `backend/data/lancedb/`

## 🛠️ Development Guide

### Backend Development

```bash
cd backend
# Enable hot reload
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8006
```

### Frontend Development

```bash
cd frontend
npm run dev
```

### Code Standards

- Backend: Follow PEP 8 guidelines
- Frontend: Use ESLint for code linting

## 📝 Roadmap

- [ ] Support more document formats (Word, Excel, Markdown)
- [ ] Enhanced water body extraction algorithm
- [ ] Add user permission management
- [ ] Support multimodal input (image upload)
- [ ] Optimize vector retrieval performance
- [ ] Add conversation export functionality
- [ ] Docker deployment support
- [ ] API documentation with Swagger/OpenAPI

## 🤝 Contributing

Issues and Pull Requests are welcome!

1. Fork the project
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details

## 🙏 Acknowledgments

- [Agno](https://github.com/agno-agi/agno) - AI Agent framework
- [LanceDB](https://lancedb.com/) - Vector database
- [FastEmbed](https://github.com/qdrant/fastembed) - Embedding model
- [DeepSeek](https://www.deepseek.com/) - Large Language Model

## 📧 Contact

For questions or suggestions, please open an issue or contact the maintainers.

---

**Star ⭐ this repository if you find it helpful!**
