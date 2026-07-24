from __future__ import annotations

import re
import uuid


_STABLE_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]{1,31}_[0-9a-f]{32}$")
_NAMESPACE = uuid.UUID("a76e626a-cd33-4ef8-890a-3889a40f647d")


def _normalise_prefix(prefix: str) -> str:
    if not isinstance(prefix, str):
        raise TypeError("prefix must be a string")
    value = prefix.strip().lower().replace("-", "_")
    if not re.fullmatch(r"[a-z][a-z0-9_]{1,31}", value):
        raise ValueError("prefix must contain 2-32 lowercase letters, digits, or underscores")
    return value


def new_stable_id(prefix: str) -> str:
    """Create a durable opaque ID whose prefix communicates record kind."""
    return f"{_normalise_prefix(prefix)}_{uuid.uuid4().hex}"


def deterministic_stable_id(prefix: str, *source_parts: object) -> str:
    """Create a repeatable ID for immutable import provenance."""
    if not source_parts:
        raise ValueError("at least one source part is required")
    seed = "\x1f".join(str(part) for part in source_parts)
    return f"{_normalise_prefix(prefix)}_{uuid.uuid5(_NAMESPACE, seed).hex}"


def validate_stable_id(value: str) -> str:
    if not isinstance(value, str):
        raise TypeError("stable ID must be a string")
    result = value.strip()
    if not _STABLE_ID_PATTERN.fullmatch(result):
        raise ValueError(f"invalid Diesel stable ID: {value!r}")
    return result
