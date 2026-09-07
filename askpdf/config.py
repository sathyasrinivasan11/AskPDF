"""Application configuration and safe local paths."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


PROJECT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_DIR / ".env")


def _positive_int(name: str, default: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError:
        return default
    return value if value > 0 else default


@dataclass(frozen=True)
class Settings:
    data_dir: Path = Path(os.getenv("ASKPDF_DATA_DIR", str(PROJECT_DIR / "data")))
    chat_model: str = os.getenv("ASKPDF_CHAT_MODEL", "gemini-2.0-flash")
    embedding_model: str = os.getenv(
        "ASKPDF_EMBEDDING_MODEL", "models/text-embedding-004"
    )
    top_k: int = _positive_int("ASKPDF_TOP_K", 6)
    chunk_size: int = _positive_int("ASKPDF_CHUNK_SIZE", 1200)
    chunk_overlap: int = _positive_int("ASKPDF_CHUNK_OVERLAP", 180)

    @property
    def documents_dir(self) -> Path:
        return self.data_dir / "documents"

    @property
    def sqlite_path(self) -> Path:
        return self.data_dir / "index" / "documents.sqlite3"

    @property
    def chroma_dir(self) -> Path:
        return self.data_dir / "index" / "chroma"

    def ensure_directories(self) -> None:
        self.documents_dir.mkdir(parents=True, exist_ok=True)
        self.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        self.chroma_dir.mkdir(parents=True, exist_ok=True)


settings = Settings()
