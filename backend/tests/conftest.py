from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("AI_PROVIDER", "mock")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
