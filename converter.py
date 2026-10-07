#
# converter.py
#

from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Optional

from atlas_writer import _parse_atlas, write_atlas_xml, is_rotated, rescale_sprites

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
    _mat_invert,
    _mat_mul,
    RegionAttachment,
    MeshAttachment,
    PointAttachment,
    NORMAL
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
        self.sprites: list[dict] = []
        self.fx = 1.0
        self.fy = 1.0


def _parse_pair(s: str) -> tuple[int, int]:
    parts = re.findall(r"-?\d+", s)
    if len(parts) >= 2:
        return int(parts[0]), int(parts[1])
    return 0, 0


def _actual_png_size(atlas_path: Path, image: str) -> Optional[tuple[int, int]]:
    img = atlas_path.parent / image
    if not img.exists():
        return None
    try:
        from PIL import Image

        with Image.open(img) as im:
            return im.size
    except Exception:
        return None


def parse_atlas(path: str | Path, *, rescale: bool = True) -> list[AtlasPage]:
    path = Path(path)
    raw_pages = _parse_atlas(path)
    pages: list[AtlasPage] = []
    for rp in raw_pages:
        page = AtlasPage(image=rp["image"])
        page.width = rp["width"]
        page.height = rp["height"]
        page.sprites = rp["sprites"]
        real = _actual_png_size(path, rp["image"]) if rescale else None
        if real and real != (page.width, page.height):
            fx, fy = real[0] / page.width, real[1] / page.height
            print(
                f"note: {rp['image']} is {real[0]}x{real[1]}, scaling to x{fx:.4f} y{fy:.4f}"
            )
            page.sprites = rescale_sprites(page.sprites, fx, fy)
            page.fx, page.fy = fx, fy
            page.width, page.height = real
        for s in page.sprites:
            xy = _parse_pair(s.get("xy", "0, 0"))
            size = _parse_pair(s.get("size", "0, 0"))
            orig = _parse_pair(s.get("orig", f"{size[0]},{size[1]}"))
            off = _parse_pair(s.get("offset", "0, 0"))
            page.regions[s["name"]] = AtlasRegion(
                s["name"],
                xy[0],
                xy[1],
                size[0],
                size[1],
                orig[0],
                orig[1],
                off[0],
                off[1],
                is_rotated(s),
            )
        pages.append(page)
    return pages


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


def _region_anchor(region: AtlasRegion) -> tuple[float, float]:
    return region.orig_w * 0.5, region.orig_h * 0.5


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


def emit_atlas_xml(
    out_path: str | Path, page: AtlasPage, *, hires: bool = False
) -> None:
    pivot_lookup: dict[str, tuple[float, float]] = {}
    for name in page.regions.keys():
        pivot_lookup[name] = (0.5, 0.5)
    write_atlas_xml(
        out_path,
        page.image,
        page.width,
        page.height,
        page.sprites,
        pivot_lookup,
    )


def _combine_color(slot_color, att):
    if att is None or isinstance(att, PointAttachment):
        return slot_color
    ac = getattr(att, "color", (255, 255, 255, 255))
    return tuple(int(round(s * a / 255.0)) for s, a in zip(slot_color, ac))


def spine_to_msm(
    spine_json: str | Path,
    spine_atlas: str | Path,
    out_bin: str | Path,
    out_xml: str | Path,
    *,
    anim_names: Optional[list[str]] = None,
    fps: float = 30.0,
    y_flip: bool = True,
    hires: bool = False,
    scale: Optional[float] = None,
    target_height: float = 200.0,
    canvas: int = 480,
    origin: tuple[float, float] = (240.0, 225.0),
    skin: Optional[str] = None,
    rev: int = 6,
) -> None:
    skel, data = load_skeleton(spine_json)

    skin_name = skin or ("a0" if skel.skin("a0") else "default")
    if skel.skin(skin_name) is None:
        print(f"warning: skin '{skin_name}' not found, using default")
        skin_name = "default"
    print(f"note: exporting skin '{skin_name}'")
    active_skin_obj = skel.skin(skin_name)
    skin_bones = set(active_skin_obj.bones) if active_skin_obj else set()

    active_bones: set[str] = set()
    for b in skel.bones:
        parent_ok = b.parent is None or b.parent in active_bones
        if parent_ok and (not b.skin_only or b.name in skin_bones):
            active_bones.add(b.name)
    bones = [b for b in skel.bones if b.name in active_bones]
    slots = [s for s in skel.slots if s.bone in active_bones]
    ik_bones = {n for c in skel.ik for n in c.bones}
    S = scale if scale else target_height / (skel.height or 1000.0)
    pages = parse_atlas(spine_atlas)
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
    for b in bones:
        bone_layer_id[b.name] = nid
        nid += 1
    for s in slots:
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

        samples = [
            sample_skeleton_at(skel, anim, t, active_skin=skin_name, fps=fps)
            for t in times
        ]

        bone_layers: list[dict] = []
        for bone in bones:
            anim_bone = (anim.get("bones", {}) or {}).get(bone.name)
            anim_bone = (anim.get("bones", {}) or {}).get(bone.name)
            frames = []
            prev_rot: Optional[float] = None
            for t, sample in zip(times, samples):
                if bone.name in ik_bones or bone.transform_mode != NORMAL:
                    world = sample["bones"][bone.name]
                    lm = (
                        _mat_mul(_mat_invert(sample["bones"][bone.parent]), world)
                        if bone.parent
                        else world
                    )
                    a, b_, c, d, e, f = lm
                else:
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

                if sx < 0.0:
                    sx = -sx
                    sy = -sy
                    rot += 180.0

                if y_flip:
                    py = -py
                    rot = -rot

                # Spine handles rotation WAY differently than MSM does
                # So we do whatever this monstrosity is
                if prev_rot is not None:
                    while rot - prev_rot > 180.0:
                        rot -= 360.0
                    while rot - prev_rot < -180.0:
                        rot += 360.0
                prev_rot = rot

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
        for slot in slots:
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

                if att is None:
                    r, g, b_, a = sst["color"]
                    frames.append(make_frame(t, opacity=0.0, rgb=(r, g, b_)))
                    continue

                r, g, b_, a = _combine_color(sst["color"], att)

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

                if (
                    isinstance(att, RegionAttachment)
                    and region is not None
                    and att.width > 0
                    and att.height > 0
                    and region.orig_w > 0
                    and region.orig_h > 0
                ):
                    asx *= att.width / region.orig_w
                    asy *= att.height / region.orig_h

                if region is not None and not have_anchor:
                    anchor_x, anchor_y = _region_anchor(region)
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

    write_bin(out_bin, source_entries, anims_out, rev=rev)
