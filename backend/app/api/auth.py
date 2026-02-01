from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlmodel import select
from passlib.context import CryptContext
from ..core.db import get_session
from ..db.models import User


router = APIRouter(prefix="/auth", tags=["auth"])
pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


class LoginReq(BaseModel):
    username: str
    password: str


class ConfigReq(BaseModel):
    user_id: int
    api_base_url: str | None = None
    api_key: str | None = None


@router.post("/login")
def login(body: LoginReq):
    with get_session() as s:
        u = s.exec(select(User).where(User.username == body.username)).first()
        if u is None or not pwd.verify(body.password, u.password_hash):
            raise HTTPException(status_code=401, detail="invalid credentials")
        return {"access_token": str(u.id), "user": {"id": u.id, "username": u.username, "role": u.role}}


@router.post("/config")
def update_config(body: ConfigReq):
    with get_session() as s:
        u = s.get(User, body.user_id)
        if u is None:
            raise HTTPException(status_code=404, detail="user not found")
        u.api_base_url = body.api_base_url
        u.api_key = body.api_key
        s.add(u)
        s.commit()
        return {"ok": True}

