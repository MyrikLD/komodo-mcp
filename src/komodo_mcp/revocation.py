import json
import logging
import time
from pathlib import Path

logger = logging.getLogger(__name__)

REVOCATION_FILE = "revoked_tokens.json"


class RevocationStore:
    """Keeps track of revoked token pairs.

    Tokens are stateless JWTs — nothing about them is stored server side — so a
    revocation only sticks if it is written down somewhere. When ``path`` is
    given, the store persists to that JSON file and therefore survives a
    restart. Without a writable path it degrades to memory-only: revocations are
    forgotten on restart and tokens stay valid until they expire on their own.
    """

    def __init__(self, path: Path | None = None) -> None:
        self._path = path
        self._entries: dict[str, float] = {}
        if path is not None:
            self._load()

    def is_revoked(self, key: str) -> bool:
        expires_at = self._entries.get(key)
        if expires_at is None:
            return False
        if expires_at < time.time():
            del self._entries[key]
            return False
        return True

    def revoke(self, key: str, expires_at: float) -> None:
        self._prune()
        self._entries[key] = expires_at
        self._save()

    # ------------------------------------------------------------------

    def _prune(self) -> None:
        now = time.time()
        self._entries = {k: v for k, v in self._entries.items() if v > now}

    def _load(self) -> None:
        assert self._path is not None
        try:
            raw = json.loads(self._path.read_text())
        except FileNotFoundError:
            return
        except (OSError, ValueError) as exc:
            logger.warning("revocation store unreadable (%s): %s", self._path, exc)
            return
        now = time.time()
        self._entries = {str(k): float(v) for k, v in raw.items() if float(v) > now}
        logger.info(
            "revocation store loaded: %d entries from %s",
            len(self._entries),
            self._path,
        )

    def _save(self) -> None:
        if self._path is None:
            return
        tmp = self._path.with_suffix(".tmp")
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            tmp.write_text(json.dumps(self._entries))
            tmp.replace(self._path)
        except OSError as exc:
            logger.warning(
                "revocation store not writable (%s): %s — "
                "revocations will be lost on restart",
                self._path,
                exc,
            )
            self._path = None
