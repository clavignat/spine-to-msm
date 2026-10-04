#
# _common.py
#

from __future__ import annotations
from typing import Any, Optional

IMM_UNSET = -1
IMM_SET = 0

_BLEND_OLD_TO_REV6 = {
    0: 0,
    1: 2,
    2: 6,
}

_BLEND_REV6_TO_OLD = {
    0: 0,
    1: 0,
    2: 1,
    3: 0,
    4: 0,
    5: 0,
    6: 2,
    7: 0,
}


def _imm_dict(immediate: int = IMM_UNSET, **fields) -> dict:
    d = {"immediate": int(immediate)}
    d.update(fields)
    return d


def _empty_pos() -> dict:
    return _imm_dict(IMM_UNSET, x=0.0, y=0.0)


def _empty_scale() -> dict:
    return _imm_dict(IMM_UNSET, x=1.0, y=1.0)


def _empty_val(v=0.0) -> dict:
    return _imm_dict(IMM_UNSET, value=float(v))


def _empty_str() -> dict:
    return _imm_dict(IMM_UNSET, string="")


def _empty_rgb() -> dict:
    return _imm_dict(IMM_UNSET, red=255, green=255, blue=255)


def _empty_rect() -> dict:
    return _imm_dict(IMM_UNSET, x=0.0, y=0.0, w=0.0, h=0.0)


def _empty_font() -> dict:
    return _imm_dict(
        IMM_UNSET,
        size=0,
        align=0,
        r=255,
        g=255,
        b=255,
        type=0,
        name="",
        width=0.0,
        height=0.0,
    )


def _coerce_bool_immediate(value: Any, default: int = IMM_UNSET) -> int:
    try:
        v = int(value)
    except (TypeError, ValueError):
        return default
    return v if v in (-1, 0, 1) else default
