"""Incrementing export IDs: IPT001, IPT002, ...

The counter file holds the last ID number used (a single integer). A number is only
used up when an export succeeds, so failed exports never skip a number.

Default location: <Model Vault storage root>/Configurator/export_counter.txt, i.e. inside
the data folder set in backend/.env, so it is backed up with the models and never in git.
Override with CONFIGURATOR_EXPORT_COUNTER_FILE in backend/configurator.env.
"""
import threading
from contextlib import contextmanager
from pathlib import Path

from ..config import settings as vault_settings
from .settings import settings

PREFIX = "IPT"
_lock = threading.Lock()  # one export at a time takes a number, so numbers are never reused


def counter_file() -> Path:
    return settings.export_counter_file or (
        vault_settings.storage_root / "Configurator" / "export_counter.txt"
    )


def format_id(n: int) -> str:
    """1 -> IPT001; grows past 3 digits automatically (IPT1000)."""
    return f"{PREFIX}{n:03d}"


def _last_used() -> int:
    path = counter_file()
    if not path.exists():
        return 0
    text = path.read_text(encoding="utf-8").strip()
    if not text.isdigit():
        # Never silently restart numbering: that could repeat IDs already handed out.
        raise RuntimeError(f"Export counter file is not a number: {path}")
    return int(text)


def peek_next() -> str:
    """The ID the next successful export will get (for display on the page)."""
    return format_id(_last_used() + 1)


@contextmanager
def reserve():
    """Yield the next export ID; record it as used only if the block finishes without error."""
    with _lock:
        n = _last_used() + 1
        yield format_id(n)
        path = counter_file()
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(f"{n}\n", encoding="utf-8")
        tmp.replace(path)  # atomic swap, so a crash never leaves a half-written counter
