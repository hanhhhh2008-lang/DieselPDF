from __future__ import annotations

import contextlib
import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Tuple
from uuid import UUID

from dieselpdf.domain.dataset import JsonlEnvelope, RecordType
from dieselpdf.persistence.sqlite import DatasetRepository


@dataclass(frozen=True, slots=True)
class JsonlExportReport:
    path: Path
    project_id: UUID
    record_count: int
    sha256: str
    counts: Dict[str, int]


@dataclass(frozen=True, slots=True)
class JsonlImportReport:
    path: Path
    record_count: int
    sha256: str
    inserted_counts: Dict[str, int]


def export_project_jsonl(
    repository: DatasetRepository,
    project_id: UUID,
    path: Path,
) -> JsonlExportReport:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_path = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        text=True,
    )
    counts: Dict[str, int] = {}
    record_count = 0
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            for record_type, model in repository.snapshot_records(project_id):
                envelope = JsonlEnvelope(
                    record_type=record_type,
                    payload=model.model_dump(mode="json", exclude_none=True),
                )
                handle.write(envelope.model_dump_json(exclude_none=True))
                handle.write("\n")
                record_count += 1
                counts[record_type.value] = counts.get(record_type.value, 0) + 1
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
    except Exception:
        with contextlib.suppress(OSError):
            os.unlink(temporary_path)
        raise
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return JsonlExportReport(path, project_id, record_count, digest, counts)


def read_jsonl(path: Path) -> Tuple[JsonlEnvelope, ...]:
    path = Path(path)
    envelopes = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                envelopes.append(JsonlEnvelope.model_validate_json(line))
            except Exception as exc:
                raise ValueError(f"invalid JSONL record at line {line_number}: {exc}") from exc
    if not envelopes:
        raise ValueError("JSONL file contains no records")
    return tuple(envelopes)


def import_project_jsonl(
    repository: DatasetRepository,
    path: Path,
    *,
    duplicate_policy: str = "error",
) -> JsonlImportReport:
    path = Path(path)
    envelopes = read_jsonl(path)
    project_records = [
        envelope for envelope in envelopes if envelope.record_type is RecordType.PROJECT
    ]
    if len(project_records) != 1:
        raise ValueError("JSONL snapshot must contain exactly one project record")
    inserted = repository.restore_snapshot(
        envelopes,
        duplicate_policy=duplicate_policy,
    )
    return JsonlImportReport(
        path=path,
        record_count=len(envelopes),
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        inserted_counts=inserted,
    )
