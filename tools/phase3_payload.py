from __future__ import annotations

import base64
import hashlib
import io
import tarfile
from pathlib import Path

PAYLOAD_SHA256 = "67986c6f891cd43fba7f38ba5d4d624589e945ce528a8d824fe9fd1c4836debb"
PARTS_DIRECTORY = Path("tools/phase3_payload_parts")


def main() -> None:
    parts = sorted(PARTS_DIRECTORY.glob("part*"))
    if not parts:
        raise RuntimeError("Phase 3 payload parts are missing")
    encoded = "".join(path.read_text(encoding="utf-8").strip() for path in parts)
    data = base64.b64decode(encoded, validate=True)
    digest = hashlib.sha256(data).hexdigest()
    if digest != PAYLOAD_SHA256:
        raise RuntimeError(
            f"Phase 3 payload checksum mismatch: expected {PAYLOAD_SHA256}, got {digest}"
        )
    root = Path.cwd().resolve()
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
        for member in archive.getmembers():
            destination = (root / member.name).resolve()
            if root not in destination.parents and destination != root:
                raise RuntimeError(f"Unsafe payload path: {member.name}")
        archive.extractall(root)


if __name__ == "__main__":
    main()
