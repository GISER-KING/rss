import os
from contextlib import asynccontextmanager
import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import select
from passlib.context import CryptContext

try:
    from backend.app.core.db import init_db, get_session
    from backend.app.core.config import UPLOADS_DIR, LANCEDB_DIR, DATA_DIR, API_BASE_URL, API_KEY
    from backend.app.db.models import User
    from backend.app.api.auth import router as auth_router
    from backend.app.api.chat import router as chat_router
    from backend.app.api.upload import router as upload_router
except ImportError:
    from app.core.db import init_db, get_session
    from app.core.config import UPLOADS_DIR, LANCEDB_DIR, DATA_DIR, API_BASE_URL, API_KEY
    from app.db.models import User
    from app.api.auth import router as auth_router
    from app.api.chat import router as chat_router
    from app.api.upload import router as upload_router

# Crypto context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Ensure directories exist and DB is initialized
    os.makedirs(UPLOADS_DIR.as_posix(), exist_ok=True)
    os.makedirs(LANCEDB_DIR.as_posix(), exist_ok=True)
    init_db()
    
    # Create default admin if not exists
    with get_session() as session:
        user = session.exec(select(User).where(User.username == "admin")).first()
        if not user:
            admin_user = User(
                username="admin",
                password_hash=pwd_context.hash("admin123"),
                role="admin",
                api_base_url=API_BASE_URL,
                api_key=API_KEY
            )
            session.add(admin_user)
            session.commit()
            print(f"✓ 创建默认管理员用户，使用模型: {API_BASE_URL}")
        else:
            # 更新现有用户的API配置
            if not user.api_base_url or not user.api_key:
                user.api_base_url = API_BASE_URL
                user.api_key = API_KEY
                session.add(user)
                session.commit()
                print(f"✓ 更新管理员用户API配置: {API_BASE_URL}")
    
    yield
    # Shutdown: (Cleanup if needed)

app = FastAPI(title="RiverAI Backend", lifespan=lifespan)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all for dev convenience, restrict in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static Files
app.mount("/files", StaticFiles(directory=DATA_DIR), name="files")

# Routes
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(upload_router)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8006, reload=True)
