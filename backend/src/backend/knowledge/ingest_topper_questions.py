from __future__ import annotations

import argparse
import csv
import hashlib
import json
import logging
import os
import random
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

from langchain_google_genai import GoogleGenerativeAIEmbeddings

from backend.knowledge.config import KnowledgeSettings
from backend.knowledge.embeddings import (
    KNOWLEDGE_EMBEDDING_DIMENSION,
    create_knowledge_embeddings,
)
from backend.knowledge.pinecone_store import PineconeVectorStore

logger = logging.getLogger("topper-question-ingestion")
DEFAULT_NAMESPACE = "topper-questions"
PINECONE_METADATA_MAX_BYTES = 40_000
EMBEDDING_REQUEST_BATCH_SIZE = 100
DEFAULT_REQUEST_DELAY_SECONDS = 65.0
MAX_EMBEDDING_RETRIES = 5
INITIAL_RETRY_DELAY_SECONDS = 1.0
MAX_RETRY_DELAY_SECONDS = 60.0


@dataclass
class IngestionStats:
    rows_read: int = 0
    upserted: int = 0
    skipped_empty_question: int = 0
    skipped_malformed: int = 0
    skipped_oversized_metadata: int = 0
    embedding_failures: int = 0
    upsert_failures: int = 0
    retries: int = 0


class CheckpointError(RuntimeError):
    """Raised when an ingestion checkpoint cannot safely be resumed."""


class BatchIngestionError(RuntimeError):
    """Raised when a batch fails and cannot be checkpointed."""


class _RequestPacer:
    def __init__(self, delay_seconds: float) -> None:
        self._delay_seconds = max(0.0, delay_seconds)
        self._last_request_finished: float | None = None

    def wait(self) -> None:
        if self._last_request_finished is None:
            return
        remaining = self._delay_seconds - (time.monotonic() - self._last_request_finished)
        if remaining > 0:
            time.sleep(remaining)

    def mark_finished(self) -> None:
        self._last_request_finished = time.monotonic()


def _exception_chain(error: BaseException):
    current: BaseException | None = error
    while current is not None:
        yield current
        current = current.__cause__ or current.__context__


def _http_status(error: BaseException) -> int | None:
    for cause in _exception_chain(error):
        code = getattr(cause, "code", None)
        if isinstance(code, int):
            return code
        response = getattr(cause, "response", None)
        status_code = getattr(response, "status_code", None)
        if isinstance(status_code, int):
            return status_code
    return None


def _is_transient_embedding_error(error: BaseException) -> bool:
    status = _http_status(error)
    if status in {408, 425, 429, 500, 502, 503, 504}:
        return True
    if status is not None:
        return False

    transient_names = (
        "timeout",
        "connection",
        "connecterror",
        "networkerror",
        "remoteprotocol",
        "servererror",
    )
    return any(
        any(marker in type(cause).__name__.lower() for marker in transient_names)
        for cause in _exception_chain(error)
    )


def _retry_after_seconds(error: BaseException) -> float | None:
    for cause in _exception_chain(error):
        response = getattr(cause, "response", None)
        headers = getattr(response, "headers", None)
        if not headers:
            continue
        retry_after = headers.get("Retry-After")
        if retry_after is None:
            continue
        try:
            return max(0.0, float(retry_after))
        except (TypeError, ValueError):
            try:
                retry_at = parsedate_to_datetime(str(retry_after))
                if retry_at.tzinfo is None:
                    retry_at = retry_at.replace(tzinfo=timezone.utc)
                return max(0.0, (retry_at - datetime.now(timezone.utc)).total_seconds())
            except (TypeError, ValueError, OverflowError):
                continue
    return None


def _csv_fingerprint(csv_path: Path) -> str:
    digest = hashlib.sha256()
    with csv_path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _checkpoint_path(csv_path: Path, configured_path: Path | None) -> Path:
    if configured_path is not None:
        return configured_path
    return csv_path.with_name(f"{csv_path.name}.checkpoint.json")


def _load_checkpoint(
    *,
    path: Path,
    fingerprint: str,
    namespace: str,
    reset: bool,
) -> int:
    if reset and path.exists():
        path.unlink()
        logger.info("Removed checkpoint %s; starting from the first data row.", path)
    if not path.exists():
        return 2

    try:
        checkpoint = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise CheckpointError(
            f"Checkpoint {path} cannot be read. Fix or reset it before resuming."
        ) from error
    if not isinstance(checkpoint, dict):
        raise CheckpointError(
            f"Checkpoint {path} has an invalid format. Fix or reset it before resuming."
        )

    if checkpoint.get("csv_fingerprint") != fingerprint:
        raise CheckpointError(
            f"CSV fingerprint does not match checkpoint {path}; refusing to resume. "
            "Use --reset-checkpoint only if you intend to restart this CSV from the beginning."
        )
    if checkpoint.get("namespace") != namespace:
        raise CheckpointError(
            f"Checkpoint {path} belongs to namespace {checkpoint.get('namespace')!r}, "
            f"not {namespace!r}; use the original namespace or reset the checkpoint."
        )
    next_csv_row = checkpoint.get("next_csv_row")
    if not isinstance(next_csv_row, int) or next_csv_row < 2:
        raise CheckpointError(
            f"Checkpoint {path} has an invalid next_csv_row; fix or reset it before resuming."
        )
    return next_csv_row


def _write_checkpoint(
    *,
    path: Path,
    fingerprint: str,
    namespace: str,
    next_csv_row: int,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    content = {
        "csv_fingerprint": fingerprint,
        "namespace": namespace,
        "next_csv_row": next_csv_row,
    }
    try:
        with temporary_path.open("w", encoding="utf-8") as handle:
            json.dump(content, handle, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def _embed_request_with_retry(
    *,
    question_texts: list[str],
    provider: GoogleGenerativeAIEmbeddings,
    request_pacer: _RequestPacer,
    stats: IngestionStats,
    first_row_number: int,
) -> list[list[float]]:
    for attempt in range(1, MAX_EMBEDDING_RETRIES + 2):
        request_pacer.wait()
        try:
            values = provider.embed_documents(
                question_texts,
                task_type="RETRIEVAL_DOCUMENT",
                batch_size=EMBEDDING_REQUEST_BATCH_SIZE,
            )
        except Exception as error:
            request_pacer.mark_finished()
            if not _is_transient_embedding_error(error) or attempt > MAX_EMBEDDING_RETRIES:
                raise

            retry_number = attempt
            backoff_cap = min(
                MAX_RETRY_DELAY_SECONDS,
                INITIAL_RETRY_DELAY_SECONDS * (2 ** (retry_number - 1)),
            )
            backoff = random.uniform(0.0, backoff_cap)
            retry_after = _retry_after_seconds(error)
            delay = max(backoff, retry_after or 0.0)
            stats.retries += 1
            logger.warning(
                "Embedding retry %d/%d at CSV row %d after HTTP %s; waiting %.1fs.",
                retry_number,
                MAX_EMBEDDING_RETRIES,
                first_row_number,
                _http_status(error) or "transient error",
                delay,
            )
            time.sleep(delay)
        else:
            request_pacer.mark_finished()
            return values

    raise RuntimeError("Embedding retries exhausted.")


def _positive_batch_size(value: str) -> int:
    try:
        batch_size = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("batch size must be an integer") from error
    if not 1 <= batch_size <= 100:
        raise argparse.ArgumentTypeError("batch size must be between 1 and 100")
    return batch_size


def _question_vector_id(question: str, url: str) -> str:
    identity = json.dumps(
        [question.strip(), url.strip()],
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return f"topper-question-{hashlib.sha256(identity.encode('utf-8')).hexdigest()}"


def _pinecone_metadata(row: dict[str | None, str | None]) -> dict[str, str]:
    """Map CSV strings to Pinecone-safe metadata without losing source text."""
    metadata: dict[str, str] = {}
    for column, value in row.items():
        if not isinstance(column, str) or value is None or value == "":
            continue
        key = {"question": "question_text", "url": "question_url"}.get(column, column)
        metadata[key] = value
    return metadata


def _process_batch(
    *,
    batch: list[tuple[int, str, str, dict[str, str]]],
    embeddings: GoogleGenerativeAIEmbeddings,
    vectors: PineconeVectorStore,
    stats: IngestionStats,
    request_pacer: _RequestPacer,
) -> bool:
    if not batch:
        return True

    pinecone_vectors = []
    invalid_embedding = False
    question_texts = [question for _, question, _, _ in batch]
    # Match LangChain's own count/token batching so each invocation below is one
    # actual Gemini embed_content request, even if 100 rows split on token limits.
    request_batches = GoogleGenerativeAIEmbeddings._prepare_batches(
        question_texts,
        EMBEDDING_REQUEST_BATCH_SIZE,
    )
    offset = 0
    for request_texts in request_batches:
        request_rows = batch[offset : offset + len(request_texts)]
        offset += len(request_texts)
        try:
            values = _embed_request_with_retry(
                question_texts=request_texts,
                provider=embeddings,
                request_pacer=request_pacer,
                stats=stats,
                first_row_number=request_rows[0][0],
            )
        except Exception as error:
            stats.embedding_failures += len(request_rows)
            logger.error(
                "Embedding failed at CSV row %d (%d rows): %s.",
                request_rows[0][0],
                len(request_rows),
                type(error).__name__,
            )
            return False

        if len(values) != len(request_rows):
            stats.embedding_failures += len(request_rows)
            logger.error(
                "Embedding provider returned %d vectors for %d rows at CSV row %d.",
                len(values),
                len(request_rows),
                request_rows[0][0],
            )
            return False

        for (row_number, _, vector_id, metadata), value in zip(request_rows, values, strict=True):
            if len(value) != KNOWLEDGE_EMBEDDING_DIMENSION:
                stats.embedding_failures += 1
                logger.error(
                    "Embedding for CSV row %d has dimension %d; expected %d.",
                    row_number,
                    len(value),
                    KNOWLEDGE_EMBEDDING_DIMENSION,
                )
                invalid_embedding = True
                continue
            pinecone_vectors.append({"id": vector_id, "values": value, "metadata": metadata})

    if invalid_embedding or not pinecone_vectors:
        return False

    try:
        vectors.upsert(pinecone_vectors)
    except Exception as error:
        stats.upsert_failures += len(pinecone_vectors)
        logger.error(
            "Pinecone upsert failed for batch starting at CSV row %d (%d vectors): %s",
            batch[0][0],
            len(pinecone_vectors),
            type(error).__name__,
        )
        return False

    stats.upserted += len(pinecone_vectors)
    return True


def ingest_csv(
    csv_path: Path,
    *,
    namespace: str = DEFAULT_NAMESPACE,
    batch_size: int = 100,
    request_delay_seconds: float = DEFAULT_REQUEST_DELAY_SECONDS,
    checkpoint_file: Path | None = None,
    reset_checkpoint: bool = False,
) -> IngestionStats:
    if not 1 <= batch_size <= 100:
        raise ValueError("batch_size must be between 1 and 100")
    if request_delay_seconds < 0:
        raise ValueError("request_delay_seconds cannot be negative")

    started_at = time.monotonic()
    fingerprint = _csv_fingerprint(csv_path)
    checkpoint_path = _checkpoint_path(csv_path, checkpoint_file)
    if checkpoint_path.resolve() == csv_path.resolve():
        raise ValueError("Checkpoint path must not overwrite the CSV file.")
    next_csv_row = _load_checkpoint(
        path=checkpoint_path,
        fingerprint=fingerprint,
        namespace=namespace,
        reset=reset_checkpoint,
    )
    settings = KnowledgeSettings.from_environment()
    embedding_provider = create_knowledge_embeddings(settings)
    vector_store = PineconeVectorStore(
        api_key=settings.pinecone_api_key,
        index_name=settings.pinecone_index_name,
        host=settings.pinecone_host,
        namespace=namespace,
    )
    stats = IngestionStats()
    request_pacer = _RequestPacer(request_delay_seconds)
    batch: list[tuple[int, str, str, dict[str, str]]] = []

    logger.info(
        "Reading CSV %s; namespace=%s; resume_row=%d; checkpoint=%s; request_delay=%.1fs",
        csv_path,
        namespace,
        next_csv_row,
        checkpoint_path,
        request_delay_seconds,
    )
    last_csv_row = 1

    def process_and_checkpoint_batch() -> None:
        nonlocal next_csv_row
        if not batch:
            return
        if not _process_batch(
            batch=batch,
            embeddings=embedding_provider,
            vectors=vector_store,
            stats=stats,
            request_pacer=request_pacer,
        ):
            raise BatchIngestionError(
                f"Batch failed; checkpoint remains at CSV row {next_csv_row}. "
                "Rerun the command to retry this batch."
            )

        next_csv_row = batch[-1][0] + 1
        _write_checkpoint(
            path=checkpoint_path,
            fingerprint=fingerprint,
            namespace=namespace,
            next_csv_row=next_csv_row,
        )
        batch.clear()
        logger.info(
            "Progress: next_row=%d uploaded=%d retries=%d embedding_failures=%d "
            "upsert_failures=%d elapsed=%.1fs",
            next_csv_row,
            stats.upserted,
            stats.retries,
            stats.embedding_failures,
            stats.upsert_failures,
            time.monotonic() - started_at,
        )

    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or "question" not in reader.fieldnames:
            raise ValueError("The CSV must have a 'question' column.")

        for row_number, row in enumerate(reader, start=2):
            last_csv_row = row_number
            if row_number < next_csv_row:
                continue
            stats.rows_read += 1
            question = row.get("question")
            if question is None or not question.strip():
                stats.skipped_empty_question += 1
                continue
            if None in row:
                stats.skipped_malformed += 1
                logger.warning("Skipping malformed CSV row %d with extra fields.", row_number)
                continue

            url = row.get("url") or ""
            metadata = _pinecone_metadata(row)
            metadata["question_text"] = question
            if "url" in row and row["url"] is not None:
                metadata["question_url"] = row["url"]
            metadata_size = len(json.dumps(metadata, ensure_ascii=False).encode("utf-8"))
            if metadata_size > PINECONE_METADATA_MAX_BYTES:
                stats.skipped_oversized_metadata += 1
                logger.warning("Skipping CSV row %d: Pinecone metadata exceeds 40 KB.", row_number)
                continue

            batch.append((row_number, question.strip(), _question_vector_id(question, url), metadata))
            if len(batch) >= batch_size:
                process_and_checkpoint_batch()

    if next_csv_row > last_csv_row + 1:
        raise CheckpointError(
            f"Checkpoint {checkpoint_path} resumes beyond the end of this CSV; "
            "fix or reset the checkpoint before resuming."
        )
    process_and_checkpoint_batch()
    completed_next_row = last_csv_row + 1
    if completed_next_row > next_csv_row:
        next_csv_row = completed_next_row
        _write_checkpoint(
            path=checkpoint_path,
            fingerprint=fingerprint,
            namespace=namespace,
            next_csv_row=next_csv_row,
        )
    logger.info(
        "Finished: next_row=%d read=%d uploaded=%d retries=%d skipped_empty=%d skipped_malformed=%d "
        "skipped_oversized_metadata=%d embedding_failures=%d upsert_failures=%d elapsed=%.1fs",
        next_csv_row,
        stats.rows_read,
        stats.upserted,
        stats.retries,
        stats.skipped_empty_question,
        stats.skipped_malformed,
        stats.skipped_oversized_metadata,
        stats.embedding_failures,
        stats.upsert_failures,
        time.monotonic() - started_at,
    )
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Embed topper questions from a CSV and upsert them into Pinecone."
    )
    parser.add_argument("csv_path", type=Path, help="Path to the topper-question CSV file.")
    parser.add_argument(
        "--namespace",
        default=os.getenv("TOPPER_QUESTIONS_NAMESPACE", DEFAULT_NAMESPACE),
        help=f"Pinecone namespace (default: {DEFAULT_NAMESPACE}, or TOPPER_QUESTIONS_NAMESPACE).",
    )
    parser.add_argument(
        "--batch-size",
        type=_positive_batch_size,
        default=100,
        help="Rows per embedding/upsert batch (1-100; default: 100).",
    )
    parser.add_argument(
        "--request-delay",
        type=float,
        default=float(DEFAULT_REQUEST_DELAY_SECONDS),
        help="Seconds to wait between Gemini embedding API requests (default: 65).",
    )
    parser.add_argument(
        "--checkpoint",
        type=Path,
        help="Checkpoint file path (default: <csv_path>.checkpoint.json).",
    )
    parser.add_argument(
        "--reset-checkpoint",
        action="store_true",
        help="Delete the checkpoint and start processing from the beginning.",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    if not args.csv_path.is_file():
        parser.error(f"CSV file does not exist: {args.csv_path}")

    try:
        if args.request_delay < 0:
            parser.error("--request-delay cannot be negative")
        ingest_csv(
            args.csv_path,
            namespace=args.namespace,
            batch_size=args.batch_size,
            request_delay_seconds=args.request_delay,
            checkpoint_file=args.checkpoint,
            reset_checkpoint=args.reset_checkpoint,
        )
    except KeyboardInterrupt:
        checkpoint_path = _checkpoint_path(args.csv_path, args.checkpoint)
        logger.warning(
            "Interrupted. Completed batches are checkpointed at %s; rerun the same command to resume.",
            checkpoint_path,
        )
        raise SystemExit(130)
    except (CheckpointError, BatchIngestionError) as error:
        logger.error("%s", error)
        raise SystemExit(1) from error
    except Exception as error:
        logger.error("Ingestion stopped: %s", type(error).__name__)
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
