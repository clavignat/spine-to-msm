#
# atlas_writer.py
#

import re
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


def parse_spine_atlas(path: str | Path) -> list[dict]:
    lines = Path(path).read_text().splitlines()
    pages: list[dict] = []
    cur_page = None
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        if line.endswith(".png") or line.endswith(".webp"):
            cur_page = {"image": line, "sprites": [], "width": 0, "height": 0}
            pages.append(cur_page)
            i += 1
            continue
        if line.startswith("size:") and cur_page is not None:
            w, h = re.findall(r"\d+", line)
            cur_page["width"], cur_page["height"] = int(w), int(h)
            i += 1
            continue
        if cur_page is None:
            i += 1
            continue
        name = line
        entry = {"name": name}
        i += 1
        while (
            i < len(lines)
            and lines[i].strip()
            and not lines[i].strip().endswith(".png")
        ):
            kv = lines[i].strip()
            if ":" in kv:
                key, val = kv.split(":", 1)
                entry[key.strip()] = val.strip()
            i += 1
        cur_page["sprites"].append(entry)
    return pages


def write_msm_atlas_xml(
    out_path: str | Path,
    image_filename: str,
    page_width: int,
    page_height: int,
    sprites: list[dict],
    pivot_lookup: dict[str, tuple[float, float]],
) -> None:
    lines: list[str] = []
    lines.append(
        f'<TextureAtlas imagePath="gfx/monsters/{image_filename}" width="{page_width}" height="{page_height}" hires="false">'
    )
    for s in sprites:
        xy = s.get("xy", "0, 0").split(",")
        sz = s.get("size", "0, 0").split(",")
        orig = s.get("orig", f"{sz[0]},{sz[1]}").split(",")
        offset = s.get("offset", "0, 0").split(",")
        x, y = int(xy[0]), int(xy[1])
        w, h = int(sz[0]), int(sz[1])
        ow, oh = int(orig[0]), int(orig[1])
        ox, oy = int(offset[0]), int(offset[1])
        rotated = s.get("rotate", "false").strip().lower() == "true"
        if rotated:
            w, h = h, w
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
