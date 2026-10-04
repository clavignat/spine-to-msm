#
# dispatch.py
#

from __future__ import annotations
import argparse
from pathlib import Path
from typing import Protocol

from msm import rev2, rev6


class RevModule(Protocol):
    REV: int

    def load_bin(self, path: str) -> dict: ...
    def save_bin(self, payload: dict, path: str) -> None: ...


REVS: dict[int, RevModule] = {2: rev2, 6: rev6}


def detect_rev(path: str) -> int:
    for rev in (6, 2):
        try:
            REVS[rev].load_bin(path)
            return rev
        except Exception:
            continue
    raise RuntimeError(f"Could not detect rev for {path}")
