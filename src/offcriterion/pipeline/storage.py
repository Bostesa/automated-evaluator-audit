"""Immutable raw-output storage for judge responses.

Guarantees, enforced at this layer and verified by tests:

* append-only JSONL per (judge, condition); a record for a call key that
  already exists is refused, never overwritten;
* after ``freeze()`` -- which writes a manifest of SHA-256 checksums -- all
  writes are refused permanently;
* analysis-stage code must call ``verify_frozen()`` before reading, so
  analysis can only ever see a checksummed, immutable store.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

_FREEZE_MANIFEST = "FROZEN.json"


class StorageError(RuntimeError):
    pass


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class RawScoreStore:
    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._seen: dict[Path, set[str]] = {}

    # -- writing -----------------------------------------------------------
    def _file(self, judge: str, condition: str) -> Path:
        safe = f"{judge}__{condition}".replace("/", "_")
        return self.root / f"scores__{safe}.jsonl"

    def _keys_in(self, path: Path) -> set[str]:
        if path not in self._seen:
            keys: set[str] = set()
            if path.exists():
                with path.open(encoding="utf-8") as f:
                    for line in f:
                        keys.add(json.loads(line)["essay_id_comp"])
            self._seen[path] = keys
        return self._seen[path]

    def append(
        self,
        *,
        judge: str,
        condition: str,
        essay_id_comp: str,
        prompt_sha256: str,
        raw_response: str,
        extra: dict[str, object] | None = None,
    ) -> None:
        if self.is_frozen():
            raise StorageError("store is frozen; no further writes are allowed")
        path = self._file(judge, condition)
        keys = self._keys_in(path)
        if essay_id_comp in keys:
            raise StorageError(
                f"raw output for {essay_id_comp!r} ({judge}, {condition}) "
                "already exists and must not be overwritten"
            )
        record = {
            "essay_id_comp": essay_id_comp,
            "judge": judge,
            "condition": condition,
            "prompt_sha256": prompt_sha256,
            "raw_response": raw_response,
        }
        if extra:
            for key, value in extra.items():
                record.setdefault(key, value)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, sort_keys=True) + "\n")
        keys.add(essay_id_comp)

    # -- freezing ----------------------------------------------------------
    def is_frozen(self) -> bool:
        return (self.root / _FREEZE_MANIFEST).exists()

    def freeze(self) -> None:
        if self.is_frozen():
            raise StorageError("store is already frozen")
        files = sorted(self.root.glob("scores__*.jsonl"))
        manifest = {
            "files": {p.name: _sha256_file(p) for p in files},
        }
        (self.root / _FREEZE_MANIFEST).write_text(
            json.dumps(manifest, indent=2, sort_keys=True)
        )

    def verify_frozen(self) -> None:
        """Raise unless the store is frozen and checksums still match."""
        if not self.is_frozen():
            raise StorageError(
                "analysis requires a frozen raw-score store; call freeze() "
                "after scoring is complete"
            )
        manifest = json.loads((self.root / _FREEZE_MANIFEST).read_text())
        for name, digest in manifest["files"].items():
            actual = _sha256_file(self.root / name)
            if actual != digest:
                raise StorageError(f"checksum mismatch for {name}: store was modified after freeze")

    # -- reading -----------------------------------------------------------
    def read(self, judge: str, condition: str) -> list[dict[str, str]]:
        self.verify_frozen()
        path = self._file(judge, condition)
        if not path.exists():
            return []
        with path.open(encoding="utf-8") as f:
            return [json.loads(line) for line in f]
