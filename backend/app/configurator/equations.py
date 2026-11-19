"""Read and write the input variables in a SolidWorks equations.txt file.

Only the input lines are rewritten. Derived formulas, the file's encoding
(UTF-8, UTF-8 with BOM, UTF-16 or Windows ANSI) and line endings are kept.
"""
import re
from pathlib import Path


def _load(path: Path):
    raw = path.read_bytes()
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        enc = "utf-16"
    elif raw.startswith(b"\xef\xbb\xbf"):
        enc = "utf-8-sig"
    else:
        enc = "utf-8"
    try:
        return raw.decode(enc), enc
    except UnicodeDecodeError:
        return raw.decode("cp1252"), "cp1252"


def _pattern(name: str) -> str:
    # tolerates straight or curly quotes and extra whitespace
    return rf'^\s*(["“”]{name}["“”]\s*=\s*)([\d.]+)'


def read_values(path: Path, names: list[str]) -> dict[str, float]:
    text, _ = _load(path)
    out = {}
    for name in names:
        m = re.search(_pattern(name), text, re.M)
        if not m:
            raise ValueError(f'"{name}" not found. File starts with: {text[:60]!r}')
        out[name] = float(m.group(2))
    return out


def write_values(path: Path, values: dict[str, int]) -> None:
    text, enc = _load(path)
    for name, v in values.items():
        text, n = re.subn(_pattern(name), rf"\g<1>{v}", text, count=1, flags=re.M)
        if n != 1:
            raise ValueError(f'Could not update "{name}"')
    path.write_bytes(text.encode(enc))
