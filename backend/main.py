import os
from contextlib import asynccontextmanager
import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import select
from passlib.context import CryptContext

from backend.app.core.db import init_db, get_session
from backend.app.core.config import UPLOADS_DIR, LANCEDB_DIR, DATA_DIR
from backend.app.db.models import User
from backend.app.api.auth import router as auth_router
from backend.app.api.chat import router as chat_router
from backend.app.api.upload import router as upload_router

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
                role="admin"
            )
            session.add(admin_user)
            session.commit()
    
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
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8006, reload=True)
