from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator


@dataclass(frozen=True)
class KnowledgeDocument:
    document_id: str
    filename: str
    title: str
    file_hash: str
    page_count: int
    created_at: str


class KnowledgeDocumentRepository:
    """Small SQLite catalog for curated knowledge documents."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connection() as connection:
            self._create_table(connection)
            columns = {
                row["name"]
                for row in connection.execute("PRAGMA table_info(knowledge_documents)")
            }
            if "subject" in columns or "chunk_count" in columns:
                self._migrate_legacy_table(connection)

    @staticmethod
    def _create_table(connection: sqlite3.Connection) -> None:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS knowledge_documents (
                document_id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                title TEXT NOT NULL,
                file_hash TEXT NOT NULL UNIQUE,
                page_count INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                status TEXT NOT NULL
            )
            """
        )

    @classmethod
    def _migrate_legacy_table(cls, connection: sqlite3.Connection) -> None:
        old_rows = connection.execute(
            """
            SELECT document_id, filename, file_hash, page_count, created_at, status
            FROM knowledge_documents
            """
        ).fetchall()
        connection.execute("DROP TABLE knowledge_documents")
        cls._create_table(connection)
        connection.executemany(
            """
            INSERT INTO knowledge_documents (
                document_id, filename, title, file_hash, page_count, created_at, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    row["document_id"],
                    row["filename"],
                    cls._title_from_filename(row["filename"]),
                    row["file_hash"],
                    row["page_count"],
                    row["created_at"],
                    row["status"],
                )
                for row in old_rows
            ],
        )

    @staticmethod
    def _title_from_filename(filename: str) -> str:
        name = filename.replace("\\", "/").rsplit("/", 1)[-1]
        return name.rsplit(".", 1)[0] or name

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.db_path, timeout=30)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def get_by_hash(self, file_hash: str) -> KnowledgeDocument | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM knowledge_documents WHERE file_hash = ?",
                (file_hash,),
            ).fetchone()
        return self._to_document(row) if row else None

    def create_processing(
        self,
        *,
        document_id: str,
        file_hash: str,
        filename: str,
        title: str,
        page_count: int,
        created_at: str,
    ) -> None:
        try:
            with self._connection() as connection:
                connection.execute(
                    """
                    INSERT INTO knowledge_documents (
                        document_id, filename, title, file_hash, page_count,
                        created_at, status
                    ) VALUES (?, ?, ?, ?, ?, ?, 'processing')
                    """,
                    (
                        document_id,
                        filename,
                        title,
                        file_hash,
                        page_count,
                        created_at,
                    ),
                )
        except sqlite3.IntegrityError:
            existing = self.get_by_hash(file_hash)
            if existing:
                raise DuplicateDocumentError(existing.document_id) from None
            raise

    def mark_ingested(self, document_id: str) -> None:
        with self._connection() as connection:
            connection.execute(
                """
                UPDATE knowledge_documents
                SET status = 'ingested'
                WHERE document_id = ?
                """,
                (document_id,),
            )

    def get(self, document_id: str) -> KnowledgeDocument | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM knowledge_documents WHERE document_id = ?",
                (document_id,),
            ).fetchone()
        return self._to_document(row) if row else None

    def list_ingested(self) -> list[KnowledgeDocument]:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT * FROM knowledge_documents WHERE status = 'ingested' ORDER BY created_at DESC"
            ).fetchall()
        return [self._to_document(row) for row in rows]

    def delete(self, document_id: str) -> None:
        with self._connection() as connection:
            connection.execute(
                "DELETE FROM knowledge_documents WHERE document_id = ?",
                (document_id,),
            )

    def is_ingested(self, document_id: str) -> bool:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT status FROM knowledge_documents WHERE document_id = ?",
                (document_id,),
            ).fetchone()
        return row is not None and row["status"] == "ingested"

    @staticmethod
    def _to_document(row: sqlite3.Row) -> KnowledgeDocument:
        return KnowledgeDocument(
            document_id=row["document_id"],
            filename=row["filename"],
            title=row["title"],
            file_hash=row["file_hash"],
            page_count=row["page_count"],
            created_at=row["created_at"],
        )


class DuplicateDocumentError(ValueError):
    def __init__(self, document_id: str) -> None:
        self.document_id = document_id
        super().__init__("This PDF has already been ingested.")
