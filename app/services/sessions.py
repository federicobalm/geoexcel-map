import json
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pandas as pd

from app.config import settings
from app.errors import AppError


class SessionStore:
    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir

    def ensure_dirs(self) -> None:
        settings.data_dir.mkdir(parents=True, exist_ok=True)
        settings.export_dir.mkdir(parents=True, exist_ok=True)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def cleanup_expired(self) -> None:
        cutoff = datetime.now(UTC) - timedelta(hours=settings.session_ttl_hours)
        if not self.base_dir.exists():
            return
        for session_dir in self.base_dir.iterdir():
            metadata_path = session_dir / "metadata.json"
            if not metadata_path.exists():
                shutil.rmtree(session_dir, ignore_errors=True)
                continue
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            created_at = datetime.fromisoformat(metadata["created_at"])
            if created_at < cutoff:
                shutil.rmtree(session_dir, ignore_errors=True)

    def create(self, filename: str, dataframe: pd.DataFrame, metadata: dict) -> str:
        session_id = uuid4().hex
        session_dir = self.base_dir / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        dataframe.to_json(session_dir / "data.json", orient="records", force_ascii=False)
        full_metadata = {
            "session_id": session_id,
            "filename": filename,
            "created_at": datetime.now(UTC).isoformat(),
            **metadata,
        }
        (session_dir / "metadata.json").write_text(json.dumps(full_metadata, ensure_ascii=False, indent=2), encoding="utf-8")
        return session_id

    def _session_dir(self, session_id: str) -> Path:
        session_dir = self.base_dir / session_id
        if not session_dir.exists():
            raise AppError("La sesion no existe o expiro. Vuelve a cargar el archivo.", status_code=404)
        return session_dir

    def load_dataframe(self, session_id: str) -> pd.DataFrame:
        session_dir = self._session_dir(session_id)
        data_path = session_dir / "data.json"
        if not data_path.exists():
            raise AppError("La sesion no existe o expiro. Vuelve a cargar el archivo.", status_code=404)
        return pd.read_json(data_path)

    def load_metadata(self, session_id: str) -> dict:
        session_dir = self._session_dir(session_id)
        metadata_path = session_dir / "metadata.json"
        if not metadata_path.exists():
            raise AppError("La sesion no existe o expiro. Vuelve a cargar el archivo.", status_code=404)
        return json.loads(metadata_path.read_text(encoding="utf-8"))


session_store = SessionStore(settings.session_dir)
