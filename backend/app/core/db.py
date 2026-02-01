from sqlmodel import SQLModel, create_engine, Session
from .config import DB_URL, DATA_DIR
from pathlib import Path

engine = create_engine(DB_URL, echo=False)

def init_db() -> None:
    Path(DATA_DIR).mkdir(parents=True, exist_ok=True)
    SQLModel.metadata.create_all(engine)

def get_session() -> Session:
    return Session(engine)

