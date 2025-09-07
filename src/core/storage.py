from __future__ import annotations
import duckdb, os
from pathlib import Path

ART = Path("artifacts")
ART.mkdir(exist_ok=True)

con = duckdb.connect(database=":memory:")

def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
