from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")
DOMAINS = ("photo", "art_painting", "cartoon", "sketch")
CLASSES = ("dog", "elephant", "giraffe", "guitar", "horse", "house", "person")
CONDITIONS = ("fixed_hidden", "fixed_visible", "adaptive_hidden", "adaptive_visible", "calibration_visible")
SPURIOUS_AXES = ("background", "palette", "lighting", "texture", "viewpoint", "crop", "composition")


class ContractError(ValueError):
    """Raised when a run or review record violates a frozen contract."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def fingerprint(path: Path, label: str | None = None) -> dict[str, Any]:
    return {"path": label or path.as_posix(), "sha256": sha256_file(path), "bytes": path.stat().st_size}


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def atomic_write_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    except BaseException:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise


def atomic_write_json(path: Path, value: Any) -> None:
    atomic_write_bytes(path, json.dumps(value, indent=2, ensure_ascii=False).encode("utf-8") + b"\n")


def write_jsonl(path: Path, records: Iterable[dict[str, Any]]) -> str:
    payload = b"".join(canonical_json(record) + b"\n" for record in records)
    atomic_write_bytes(path, payload)
    return sha256_bytes(payload)


def validate_run_id(run_id: str) -> None:
    if not RUN_ID_RE.fullmatch(run_id):
        raise ContractError("run_id must start with a letter or digit and contain only letters, digits, '.', '_' or '-'")


def resolve_inside(root: Path, relative: str) -> Path:
    root = root.resolve()
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ContractError(f"path escapes allowed root: {relative}") from exc
    return candidate

