from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


class KnowledgeConfigurationError(RuntimeError):
    """Raised when knowledge ingestion credentials are missing."""


@dataclass(frozen=True)
class KnowledgeSettings:
    gemini_api_key: str
    gemini_embedding_model: str
    pinecone_api_key: str
    pinecone_index_name: str
    pinecone_host: str
    metadata_db_path: Path

    @classmethod
    def from_environment(cls) -> KnowledgeSettings:
        load_dotenv()
        values = {
            "GEMINI_API_KEY": os.getenv("GOOGLE_API_KEY", "").strip(),
            "GEMINI_EMBEDDING_MODEL": os.getenv("GEMINI_EMBEDDING_MODEL", "").strip(),
            "PINECONE_API_KEY": os.getenv("PINECONE_API_KEY", "").strip(),
            "PINECONE_INDEX_NAME": os.getenv("PINECONE_INDEX_NAME", "").strip(),
            "PINECONE_HOST": os.getenv("PINECONE_HOST", "").strip(),
        }
        missing = [name for name, value in values.items() if not value]
        if missing:
            raise KnowledgeConfigurationError(
                f"Missing required knowledge-base configuration: {', '.join(missing)}."
            )

        configured_db = os.getenv("KNOWLEDGE_DB_PATH", ".data/knowledge.sqlite3")
        db_path = Path(configured_db)
        if not db_path.is_absolute():
            db_path = Path(__file__).resolve().parents[3] / db_path

        return cls(
            gemini_api_key=values["GEMINI_API_KEY"],
            gemini_embedding_model=values["GEMINI_EMBEDDING_MODEL"],
            pinecone_api_key=values["PINECONE_API_KEY"],
            pinecone_index_name=values["PINECONE_INDEX_NAME"],
            pinecone_host=values["PINECONE_HOST"],
            metadata_db_path=db_path.resolve(),
        )


def metadata_db_path_from_environment() -> Path:
    load_dotenv()
    configured_db = Path(os.getenv("KNOWLEDGE_DB_PATH", ".data/knowledge.sqlite3"))
    if not configured_db.is_absolute():
        configured_db = Path(__file__).resolve().parents[3] / configured_db
    return configured_db.resolve()
