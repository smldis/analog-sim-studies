#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path


SRC = Path(__file__).resolve().parents[2] / "src"
if SRC.exists():
    sys.path.insert(0, str(SRC))

from sidecar_edits.render import main


if __name__ == "__main__":
    raise SystemExit(main())
