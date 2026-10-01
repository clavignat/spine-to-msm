#
# writer.py
#

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from rev6_2_json import BinAnim  # type: ignore

IMMEDIATE_SET = 0
IMMEDIATE_NONE = 1
IMMEDIATE_UNSET = -1

BLEND_STANDARD = 0
BLEND_ADDITIVE = 2
BLEND_MULTIPLY = 6
BLEND_SCREEN = 7

SPINE_BLEND_MAP = {
    "normal": BLEND_STANDARD,
    "additive": BLEND_ADDITIVE,
    "multiply": BLEND_MULTIPLY,
    "screen": BLEND_SCREEN,
}


def make_source(src: str, src_id: int = 0, width: int = 0, height: int = 0) -> dict:
    return {"src": src, "id": src_id, "width": width, "height": height}


def make_frame(
    time: float,
    *,
    pos: tuple[float, float] | None = None,
    scale: tuple[float, float] | None = None,
    rotation: float | None = None,
    opacity: float | None = None,
    sprite: str | None = None,
    rgb: tuple[int, int, int] | None = None,
) -> dict[str, Any]:
    def xy(v):
        if v is None:
            return {"immediate": IMMEDIATE_UNSET, "x": 0.0, "y": 0.0}
        return {"immediate": IMMEDIATE_SET, "x": float(v[0]), "y": float(v[1])}

    def val(v, default=0.0):
        if v is None:
            return {"immediate": IMMEDIATE_UNSET, "value": default}
        return {"immediate": IMMEDIATE_SET, "value": float(v)}

    sprite_d = (
        {"immediate": IMMEDIATE_SET, "string": sprite}
        if sprite is not None
        else {"immediate": IMMEDIATE_UNSET, "string": ""}
    )
    rgb_d = (
        {
            "immediate": IMMEDIATE_SET,
            "red": int(rgb[0]),
            "green": int(rgb[1]),
            "blue": int(rgb[2]),
        }
        if rgb is not None
        else {"immediate": IMMEDIATE_UNSET, "red": 255, "green": 255, "blue": 255}
    )

    return {
        "time": float(time),
        "pos": xy(pos),
        "scale": xy(scale),
        "rotation": val(rotation),
        "opacity": val(opacity, 100.0),
        "sprite": sprite_d,
        "rgb": rgb_d,
    }


def make_layer(
    *,
    name: str,
    layer_id: int,
    parent: int = -1,
    src: int = 0,
    blend: int = BLEND_STANDARD,
    anchor: tuple[float, float] = (0.0, 0.0),
    frames: list[dict],
    layer_type: int = 1,
    width: int = 0,
    height: int = 0,
) -> dict[str, Any]:
    return {
        "name": name,
        "type": layer_type,
        "blend": int(blend),
        "parent": int(parent),
        "id": int(layer_id),
        "src": int(src),
        "width": int(width),
        "height": int(height),
        "anchor_x": float(anchor[0]),
        "anchor_y": float(anchor[1]),
        "unk": "",
        "frames": frames,
    }


def make_animation(
    *,
    name: str,
    width: int,
    height: int,
    layers: list[dict],
    loop_offset: float = -1.0,
    centered: int = 1,
) -> dict[str, Any]:
    return {
        "name": name,
        "width": int(width),
        "height": int(height),
        "loop_offset": float(loop_offset),
        "centered": int(centered),
        "layers": layers,
        "clone_layers": [],
    }


def write_bin(
    output_path: str | Path,
    sources: list[dict],
    anims: list[dict],
) -> None:
    payload = {"rev": 6, "blend_version": 2, "sources": sources, "anims": anims}
    BinAnim.from_dict(payload).save(str(output_path))
