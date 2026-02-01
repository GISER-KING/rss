import json
from typing import Any, Dict
from sqlmodel import select
from ..core.db import get_session
from ..db.models import SessionState


class SQLiteSessionMemory:
    def __init__(self, namespace: str = "default"):
        self.namespace = namespace

    def _key(self, session_id: str) -> str:
        return f"{self.namespace}:{session_id}"

    def load(self, session_id: str) -> Dict[str, Any]:
        with get_session() as s:
            k = self._key(session_id)
            row = s.exec(select(SessionState).where(SessionState.session_id == k)).first()
            if row is None:
                return {}
            try:
                return json.loads(row.state_json)
            except Exception:
                return {}

    def save(self, session_id: str, state: Dict[str, Any]) -> None:
        payload = json.dumps(state, ensure_ascii=False)
        with get_session() as s:
            k = self._key(session_id)
            row = s.exec(select(SessionState).where(SessionState.session_id == k)).first()
            if row is None:
                row = SessionState(session_id=k, state_json=payload)
                s.add(row)
            else:
                row.state_json = payload
            s.commit()

