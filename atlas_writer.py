#
# atlas_writer.py
#

import re
import xml.etree.ElementTree as ET
from pathlib import Path


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
        # otherwise it's a region block starting with the region name!!
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
    root = ET.Element(
        "TextureAtlas",
        {
            "imagePath": image_filename,
            "width": str(page_width),
            "height": str(page_height),
            "hires": "false",
        },
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
        px, py = pivot_lookup.get(s["name"], (0.5, 0.5))
        ET.SubElement(
            root,
            "sprite",
            {
                "n": s["name"],
                "x": str(x),
                "y": str(y),
                "w": str(w),
                "h": str(h),
                "pX": f"{px:.6f}",
                "pY": f"{1 - py:.6f}",
                "oX": str(ox),
                "oY": str(oy),
                "oW": str(ow),
                "oH": str(oh),
            },
        )
    ET.ElementTree(root).write(out_path, encoding="utf-8", xml_declaration=True)
