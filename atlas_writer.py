#
# atlas_writer.py
#

import re
import sys
from pathlib import Path

HEADER = """<?xml version="1.0" encoding="UTF-8"?>
<!-- Created with TexturePacker http://www.codeandweb.com/texturepacker-->
<!-- $TexturePacker:SmartUpdate:8565276fa92a4fe44581a02a006430e2:16b7ee99a48be8f1944cd7c457cfda09:442a3893a89de7a83bd8103f362c1668$ -->
<!--Format:
n  => name of the sprite
x  => sprite x pos in texture
y  => sprite y pos in texture
w  => sprite width (may be trimmed)
h  => sprite height (may be trimmed)
pX => x pos of the pivot point (relative to sprite width)
pY => y pos of the pivot point (relative to sprite height)
oX => sprite's x-corner offset (only available if trimmed)
oY => sprite's y-corner offset (only available if trimmed)
oW => sprite's original width (only available if trimmed)
oH => sprite's original height (only available if trimmed)
r => 'y' only set if sprite is rotated
with polygon mode enabled:
vertices   => points in sprite coordinate system (x0,y0,x1,y1,x2,y2, ...)
verticesUV => points in sheet coordinate system (x0,y0,x1,y1,x2,y2, ...)
triangles  => sprite triangulation, 3 vertex indices per triangle
-->
"""

_IMG_EXT = re.compile(r"\.(png|jpe?g|webp|avif)$", re.I)
_PAGE_KEYS = {"size", "format", "filter", "repeat", "pma", "scale"}


def rotation_degrees(value: str | None) -> int:
    v = (value or "false").strip().lower()
    if v == "true":
        return 90
    if v == "false":
        return 0
    try:
        return int(float(v)) % 360
    except ValueError:
        return 0


def is_rotated(sprite: dict) -> bool:
    return rotation_degrees(sprite.get("rotate")) in (90, 270)


def _parse_atlas(path: str | Path) -> list[dict]:
    lines = Path(path).read_text().splitlines()
    pages: list[dict] = []
    cur_page = None
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        if _IMG_EXT.search(line):
            cur_page = {"image": line, "sprites": [], "width": 0, "height": 0}
            pages.append(cur_page)
            i += 1
            continue
        if cur_page is None:
            i += 1
            continue
        if ":" in line:
            key, _, val = line.partition(":")
            key = key.strip().lower()
            val = val.strip()
            if key == "size":
                w, h = re.findall(r"\d+", line)
                cur_page["width"], cur_page["height"] = int(w), int(h)
                i += 1
                continue
            # otherwise it's a region block starting with the region name!!
            if key in _PAGE_KEYS:
                i += 1
                continue
        name = line
        entry = {"name": name}
        i += 1
        while (
            i < len(lines)
            and lines[i].strip()
            and ":" in lines[i]
            and not _IMG_EXT.search(lines[i].strip())
        ):
            kv = lines[i].strip()
            k, v = kv.split(":", 1)
            entry[k.strip()] = v.strip()
            i += 1
        cur_page["sprites"].append(entry)
    return pages


def _pair(s: str, default: tuple[int, int] = (0, 0)) -> tuple[int, int]:
    parts = re.findall(r"-?\d+", s or "")
    if len(parts) >= 2:
        return int(parts[0]), int(parts[1])
    return default


def rescale_sprites(sprites: list[dict], fx: float, fy: float) -> list[dict]:
    out: list[dict] = []
    for s in sprites:
        n = dict(s)
        x, y = _pair(s.get("xy", "0, 0"))
        w, h = _pair(s.get("size", "0, 0"))
        ow, oh = _pair(s.get("orig", f"{w}, {h}"), (w, h))
        ox, oy = _pair(s.get("offset", "0, 0"))
        ax, ay = (fy, fx) if is_rotated(s) else (fx, fy)
        n["xy"] = f"{round(x * fx)}, {round(y * fy)}"
        n["size"] = f"{max(1, round(w * ax))}, {max(1, round(h * ay))}"
        n["orig"] = f"{max(1, round(ow * ax))}, {max(1, round(oh * ay))}"
        n["offset"] = f"{round(ox * ax)}, {round(oy * ay)}"
        out.append(n)
    return out


def write_atlas_xml(
    out_path: str | Path,
    image_filename: str,
    page_width: int,
    page_height: int,
    sprites: list[dict],
    pivot_lookup: dict[str, tuple[float, float]],
) -> None:
    lines: list[str] = []
    lines.append(
        f'<TextureAtlas imagePath="gfx/monsters/{image_filename}" '
        f'width="{page_width}" height="{page_height}" hires="false">'
    )
    for s in sprites:
        x, y = _pair(s.get("xy", "0, 0"))
        w, h = _pair(s.get("size", "0, 0"))
        ow, oh = _pair(s.get("orig", f"{w}, {h}"), (w, h))
        off_x, off_y = _pair(s.get("offset", "0, 0"))

        deg = rotation_degrees(s.get("rotate"))
        if deg == 180:
            print(
                f"warning: '{s['name']}' has rotate: 180 (unrotated)",
                file=sys.stderr,
            )
        rotated = deg in (90, 270)

        ox = off_x
        oy = oh - h - off_y

        px, py = pivot_lookup.get(s["name"], (0.5, 0.5))
        r_attr = ' r="y"' if rotated else ""
        lines.append(
            f'    <sprite n="{s["name"]}" x="{x}" y="{y}" w="{w}" h="{h}" '
            f'pX="{px:.6f}" pY="{1 - py:.6f}" oX="{ox}" oY="{oy}" '
            f'oW="{ow}" oH="{oh}"{r_attr} />'
        )
    lines.append("</TextureAtlas>")
    lines.append("")

    Path(out_path).write_text(HEADER + "\n".join(lines), encoding="utf-8")
