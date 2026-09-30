#
# converter.py
#

from __future__ import annotations

import math
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional

from writer import (
    make_source,
    make_frame,
    make_layer,
    make_animation,
    write_bin,
    SPINE_BLEND_MAP,
    BLEND_STANDARD,
)
from sampler import (
    load_skeleton,
    sample_skeleton_at,
    _bone_local_matrix,
    _local_pose,
    RegionAttachment,
    MeshAttachment,
    PointAttachment,
)


class AtlasRegion:
    __slots__ = (
        "name",
        "x",
        "y",
        "w",
        "h",
        "orig_w",
        "orig_h",
        "offset_x",
        "offset_y",
        "rotated",
    )

    def __init__(self, name, x, y, w, h, orig_w, orig_h, off_x, off_y, rot):
        self.name = name
        self.x, self.y = x, y
        self.w, self.h = w, h
        self.orig_w, self.orig_h = orig_w, orig_h
        self.offset_x, self.offset_y = off_x, off_y
        self.rotated = rot


class AtlasPage:
    def __init__(self, image: str):
        self.image = image
        self.width = 0
        self.height = 0
        self.regions: dict[str, AtlasRegion] = {}


_IMG_EXT = re.compile(r"\.(png|jpe?g|webp|avif)$", re.I)


def _parse_pair(s: str) -> tuple[int, int]:
    parts = re.findall(r"-?\d+", s)
    if len(parts) >= 2:
        return int(parts[0]), int(parts[1])
    return 0, 0


def parse_spine_atlas(path: str | Path) -> list[AtlasPage]:
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()

    pages: list[AtlasPage] = []
    page: Optional[AtlasPage] = None
    region: Optional[dict] = None

    def flush_region():
        nonlocal region
        if region is None or page is None:
            region = None
            return
        name = region.get("name")
        if not name:
            region = None
            return
        size = region.get("size", (0, 0))
        orig = region.get("orig", size)
        off = region.get("offset", (0, 0))
        xy = region.get("xy", (0, 0))
        page.regions[name] = AtlasRegion(
            name,
            int(xy[0]),
            int(xy[1]),
            int(size[0]),
            int(size[1]),
            int(orig[0]),
            int(orig[1]),
            int(off[0]),
            int(off[1]),
            bool(region.get("rotate", False)),
        )
        region = None

    for raw in lines:
        if not raw.strip():
            continue

        if ":" in raw:
            key, _, value = raw.partition(":")
            key = key.strip().lower()
            value = value.strip()
            if region is not None:
                if key == "rotate":
                    region["rotate"] = value.lower() == "true"
                elif key == "xy":
                    region["xy"] = _parse_pair(value)
                elif key == "size":
                    region["size"] = _parse_pair(value)
                elif key == "orig":
                    region["orig"] = _parse_pair(value)
                elif key == "offset":
                    region["offset"] = _parse_pair(value)
            elif page is not None:
                if key == "size":
                    w, h = _parse_pair(value)
                    page.width, page.height = w, h
            continue

        if _IMG_EXT.search(raw):
            flush_region()
            page = AtlasPage(image=raw.strip())
            pages.append(page)
            continue

        flush_region()
        if page is not None:
            region = {"name": raw.strip()}

    flush_region()
    return pages


def emit_atlas_xml(
    out_path: str | Path, page: AtlasPage, *, hires: bool = False
) -> None:
    root = ET.Element(
        "TextureAtlas",
        {
            "imagePath": page.image,
            "width": str(page.width),
            "height": str(page.height),
            "hires": "true" if hires else "false",
        },
    )
    for r in page.regions.values():
        attrib = {
            "n": r.name,
            "x": str(r.x),
            "y": str(r.y),
            "w": str(r.w),
            "h": str(r.h),
            "pX": "0.5",
            "pY": "0.5",
            "oX": str(r.offset_x),
            "oY": str(r.offset_y),
            "oW": str(r.orig_w),
            "oH": str(r.orig_h),
        }
        if r.rotated:
            attrib["r"] = "y"
        ET.SubElement(root, "sprite", attrib)

    def indent(e, lvl=0):
        pad = "\n" + "    " * lvl
        if len(e):
            if not e.text or not e.text.strip():
                e.text = pad + "    "
            for c in e:
                indent(c, lvl + 1)
            if not e.tail or not e.tail.strip():
                e.tail = pad
        else:
            if lvl and (not e.tail or not e.tail.strip()):
                e.tail = pad

    indent(root)
    ET.ElementTree(root).write(out_path, encoding="utf-8", xml_declaration=True)


def _find_page_and_region(pages, att_name: str, att_path: Optional[str]):
    candidates: list[str] = []
    for c in (att_path, att_name):
        if c:
            candidates.append(c)
            if "/" in c:
                candidates.append(c.rsplit("/", 1)[-1])
    for i, page in enumerate(pages):
        for c in candidates:
            if c in page.regions:
                return i, page.regions[c]
    return None, None


def _decompose_local_matrix(a, b, c, d, e, f):
    rot = math.degrees(math.atan2(b, a))
    sx = math.hypot(a, b)
    det = a * d - b * c
    sy = math.hypot(c, d)
    if det < 0:
        sy = -sy
    return (e, f), rot, (sx, sy)


def _timeline_max_time(entries) -> float:
    mx = 0.0
    if isinstance(entries, dict):
        t = entries.get("time")
        if isinstance(t, (int, float)):
            mx = max(mx, float(t))
        for v in entries.values():
            mx = max(mx, _timeline_max_time(v))
    elif isinstance(entries, list):
        for v in entries:
            mx = max(mx, _timeline_max_time(v))
    return mx


def _animation_duration(anim: dict) -> float:
    explicit = anim.get("duration")
    if isinstance(explicit, (int, float)) and explicit > 0:
        return float(explicit)
    mx = 0.0
    for key in (
        "bones",
        "slots",
        "ik",
        "transform",
        "path",
        "deform",
        "draworder",
        "events",
    ):
        if key in anim:
            mx = max(mx, _timeline_max_time(anim[key]))
    return mx


def spine_to_msm(
    spine_json: str | Path,
    spine_atlas: str | Path,
    out_bin: str | Path,
    out_xml: str | Path,
    *,
    anim_names: Optional[list[str]] = None,
    fps: float = 24.0,
    y_flip: bool = True,
    hires: bool = False,
    scale: Optional[float] = None,
    target_height: float = 200.0,
    canvas: int = 480,
    origin: tuple[float, float] = (240.0, 225.0),
) -> None:
    skel, data = load_skeleton(spine_json)
    S = scale if scale else target_height / (skel.height or 1000.0)
    pages = parse_spine_atlas(spine_atlas)
    if not pages:
        raise RuntimeError(f"No pages found in atlas: {spine_atlas}")

    out_xml_path = Path(out_xml)
    source_entries: list[dict] = []
    page_to_src: dict[int, int] = {}

    if len(pages) == 1:
        emit_atlas_xml(out_xml_path, pages[0], hires=hires)
        source_entries.append(
            make_source(out_xml_path.name, 0, pages[0].width, pages[0].height)
        )
        page_to_src[0] = 0
    else:
        for i, page in enumerate(pages):
            xml_path = out_xml_path.with_name(
                f"{out_xml_path.stem}_page{i}{out_xml_path.suffix}"
            )
            emit_atlas_xml(xml_path, page, hires=hires)
            source_entries.append(
                make_source(xml_path.name, i, page.width, page.height)
            )
            page_to_src[i] = i

    bone_layer_id: dict[str, int] = {}
    slot_layer_id: dict[str, int] = {}
    nid = 0
    for b in skel.bones:
        bone_layer_id[b.name] = nid
        nid += 1
    for s in skel.slots:
        slot_layer_id[s.name] = nid
        nid += 1

    animations = data.get("animations", {}) or {}
    targets = anim_names or list(animations.keys())

    anims_out: list[dict] = []

    for anim_name in targets:
        anim = animations.get(anim_name)
        if anim is None:
            continue

        duration = _animation_duration(anim)
        n_frames = max(1, int(round(duration * fps)) + 1)
        times = [i / fps for i in range(n_frames)]
        if times[-1] < duration - 1e-9:
            times.append(duration)

        samples = [sample_skeleton_at(skel, anim, t) for t in times]

        bone_layers: list[dict] = []
        for bone in skel.bones:
            anim_bone = (anim.get("bones", {}) or {}).get(bone.name)
            frames = []
            for t in times:
                pose = _local_pose(bone, anim_bone, t)
                a, b_, c, d, e, f = _bone_local_matrix(
                    bone,
                    pose["x"],
                    pose["y"],
                    pose["rotation"],
                    pose["scale_x"],
                    pose["scale_y"],
                    pose["shear_x"],
                    pose["shear_y"],
                )
                (px, py), rot, (sx, sy) = _decompose_local_matrix(a, b_, c, d, e, f)
                if y_flip:
                    py = -py
                    rot = -rot
                if not bone.parent:
                    px = origin[0] + px * S
                    py = origin[1] + py * S
                    sx *= S
                    sy *= S
                frames.append(
                    make_frame(
                        t,
                        pos=(px, py),
                        scale=(sx * 100.0, sy * 100.0),
                        rotation=rot,
                        opacity=100.0,
                    )
                )
            parent_id = bone_layer_id[bone.parent] if bone.parent else -1
            bone_layers.append(
                make_layer(
                    name=bone.name,
                    layer_id=bone_layer_id[bone.name],
                    parent=parent_id,
                    anchor=(0.0, 0.0),
                    frames=frames,
                )
            )

        slot_layers: list[dict] = []
        for slot in skel.slots:
            frames = []
            last_sprite: Optional[str] = None
            anchor_x = 0.0
            anchor_y = 0.0
            have_anchor = False
            src_index = 0

            for t, sample in zip(times, samples):
                sst = sample["slots"][slot.name]
                att = sst["attachment_obj"]
                att_name = sst["attachment"]
                r, g, b_, a = sst["color"]

                if att is None:
                    frames.append(
                        make_frame(
                            t,
                            opacity=0.0,
                            rgb=(r, g, b_),
                        )
                    )
                    continue

                if isinstance(att, (RegionAttachment, PointAttachment)):
                    ax, ay = att.x, att.y
                    arot = att.rotation
                    asx, asy = att.scale_x, att.scale_y  # type: ignore
                elif isinstance(att, MeshAttachment):
                    ax = ay = arot = 0.0
                    asx = asy = 1.0
                else:
                    ax = ay = arot = 0.0
                    asx = asy = 1.0

                px, py = (ax, -ay) if y_flip else (ax, ay)
                rot = -arot if y_flip else arot

                page_idx, region = _find_page_and_region(
                    pages,
                    att_name or "",
                    getattr(att, "path", None),
                )

                if region is not None and not have_anchor:
                    anchor_x = region.offset_x + region.w * 0.5
                    anchor_y = region.offset_y + region.h * 0.5
                    have_anchor = True
                if page_idx is not None:
                    src_index = page_to_src[page_idx]

                sprite_arg: Optional[str] = None
                resolved_name = (
                    region.name if region else (getattr(att, "path", None) or att_name)
                )
                if resolved_name and resolved_name != last_sprite:
                    sprite_arg = resolved_name
                    last_sprite = resolved_name

                opacity = 100.0 * (a / 255.0)

                frames.append(
                    make_frame(
                        t,
                        pos=(px, py),
                        scale=(asx * 100.0, asy * 100.0),
                        rotation=rot,
                        opacity=opacity,
                        sprite=sprite_arg,
                        rgb=(r, g, b_),
                    )
                )

            blend = SPINE_BLEND_MAP.get(slot.blend, BLEND_STANDARD)

            slot_layers.append(
                make_layer(
                    name=slot.name,
                    layer_id=slot_layer_id[slot.name],
                    parent=bone_layer_id[slot.bone],
                    anchor=(anchor_x, anchor_y),
                    blend=blend,
                    src=src_index,
                    frames=frames,
                )
            )

        # Boo gaa gaa
        slot_layers.reverse()

        anims_out.append(
            make_animation(
                name=anim_name,
                width=canvas,
                height=canvas,
                layers=bone_layers + slot_layers,
                centered=1,
            )
        )

    write_bin(out_bin, source_entries, anims_out)
