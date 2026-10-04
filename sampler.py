#
# sampler.py
#

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

NORMAL = 0
ONLY_TRANSLATION = 1
NO_ROTATION_OR_REFLECTION = 2
NO_SCALE = 3
NO_SCALE_OR_REFLECTION = 4

_TRANSFORM_MODE = {
    "normal": NORMAL,
    "onlyTranslation": ONLY_TRANSLATION,
    "noRotationOrReflection": NO_ROTATION_OR_REFLECTION,
    "noScale": NO_SCALE,
    "noScaleOrReflection": NO_SCALE_OR_REFLECTION,
}


@dataclass
class Bone:
    name: str
    parent: Optional[str]
    length: float = 0.0
    transform_mode: int = NORMAL
    skin_only: bool = False
    x: float = 0.0
    y: float = 0.0
    rotation: float = 0.0
    scale_x: float = 1.0
    scale_y: float = 1.0
    shear_x: float = 0.0
    shear_y: float = 0.0


@dataclass
class Slot:
    name: str
    bone: str
    attachment: Optional[str] = None
    color: tuple[int, int, int, int] = (255, 255, 255, 255)
    dark: Optional[tuple[int, int, int]] = None
    blend: str = "normal"


@dataclass
class RegionAttachment:
    name: str
    path: Optional[str] = None
    x: float = 0.0
    y: float = 0.0
    rotation: float = 0.0
    scale_x: float = 1.0
    scale_y: float = 1.0
    width: float = 0.0
    height: float = 0.0
    color: tuple[int, int, int, int] = (255, 255, 255, 255)


@dataclass
class MeshAttachment:
    name: str
    path: Optional[str] = None
    uv: list[float] = field(default_factory=list)  # 2 floats per vertex
    triangles: list[int] = field(default_factory=list)
    vertices: list[float] = field(
        default_factory=list
    )  # 2 or (n + 3*b) floats per vertex
    hull: int = 0
    edges: list[int] = field(default_factory=list)
    color: tuple[int, int, int, int] = (255, 255, 255, 255)
    width: float = 0.0
    height: float = 0.0
    parent: Optional[str] = None
    skin: Optional[str] = None

    @property
    def weighted(self) -> bool:
        return len(self.vertices) > 2 * (len(self.uv) // 2)


@dataclass
class PointAttachment:
    name: str
    x: float = 0.0
    y: float = 0.0
    rotation: float = 0.0
    color: tuple[int, int, int, int] = (241, 241, 0, 255)


@dataclass
class Skin:
    name: str
    attachments: dict[str, dict[str, Any]] = field(default_factory=dict)
    bones: list[str] = field(default_factory=list)
    ik: list[str] = field(default_factory=list)
    transform: list[str] = field(default_factory=list)
    path: list[str] = field(default_factory=list)


@dataclass
class IKConstraint:
    name: str
    bones: list[str]
    target: str
    order: int = 0
    mix: float = 1.0
    bend_positive: bool = True
    compress: bool = False
    stretch: bool = False
    uniform: bool = False


@dataclass
class Skeleton:
    width: float = 0.0
    height: float = 0.0
    x: float = 0.0
    y: float = 0.0
    version: str = ""
    bones: list[Bone] = field(default_factory=list)
    slots: list[Slot] = field(default_factory=list)
    skins: list[Skin] = field(default_factory=list)
    ik: list[IKConstraint] = field(default_factory=list)

    def bone(self, name: str) -> Optional[Bone]:
        for b in self.bones:
            if b.name == name:
                return b
        return None

    def skin(self, name: str) -> Optional[Skin]:
        for s in self.skins:
            if s.name == name:
                return s
        return None


def _parse_color(value: Any, default=(255, 255, 255, 255)) -> tuple[int, int, int, int]:
    if not isinstance(value, str) or len(value) < 6:
        return default
    v = value.strip()
    if len(v) == 6:
        v = v + "FF"
    elif len(v) == 8:
        pass
    return (int(v[0:2], 16), int(v[2:4], 16), int(v[4:6], 16), int(v[6:8], 16))


def _parse_dark_color(value: Any) -> Optional[tuple[int, int, int]]:
    if not isinstance(value, str) or len(value) < 6:
        return None
    return (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))


def load_skeleton(json_path: str | Path) -> tuple[Skeleton, dict]:
    data = json.loads(Path(json_path).read_text(encoding="utf-8"))
    skel = Skeleton()

    s = data.get("skeleton", {})
    skel.width = float(s.get("width", 0.0))
    skel.height = float(s.get("height", 0.0))
    skel.x = float(s.get("x", 0.0))
    skel.y = float(s.get("y", 0.0))
    skel.version = str(s.get("spine", ""))

    for b in data.get("bones", []):
        skel.bones.append(
            Bone(
                name=b["name"],
                parent=b.get("parent"),
                length=float(b.get("length", 0.0)),
                transform_mode=_TRANSFORM_MODE.get(
                    b.get("transform", "normal"), NORMAL
                ),
                skin_only=bool(b.get("skin", False)),
                x=float(b.get("x", 0.0)),
                y=float(b.get("y", 0.0)),
                rotation=float(b.get("rotation", 0.0)),
                scale_x=float(b.get("scaleX", 1.0)),
                scale_y=float(b.get("scaleY", 1.0)),
                shear_x=float(b.get("shearX", 0.0)),
                shear_y=float(b.get("shearY", 0.0)),
            )
        )

    for s in data.get("slots", []):
        skel.slots.append(
            Slot(
                name=s["name"],
                bone=s["bone"],
                attachment=s.get("attachment"),
                color=_parse_color(s.get("color", "FFFFFFFF")),
                dark=_parse_dark_color(s.get("dark")),
                blend=s.get("blend", "normal"),
            )
        )

    for skin_data in data.get("skins", []) or []:
        skin = Skin(name=skin_data.get("name", "default"))
        atts = skin_data.get("attachments", {}) or {}
        for slot_name, slot_atts in atts.items():
            parsed: dict[str, Any] = {}
            for att_name, att in (slot_atts or {}).items():
                parsed[att_name] = _parse_attachment(att_name, att)
            skin.attachments[slot_name] = parsed
        skin.bones = list(skin_data.get("bones", []) or [])
        skin.ik = list(skin_data.get("ik", []) or [])
        skin.transform = list(skin_data.get("transform", []) or [])
        skin.path = list(skin_data.get("path", []) or [])
        skel.skins.append(skin)

    for ik in data.get("ik", []) or []:
        skel.ik.append(
            IKConstraint(
                name=ik["name"],
                bones=list(ik.get("bones", []) or []),
                target=ik.get("target", ""),
                order=int(ik.get("order", 0)),
                mix=float(ik.get("mix", 1.0)),
                bend_positive=bool(ik.get("bendPositive", True)),
                compress=bool(ik.get("compress", False)),
                stretch=bool(ik.get("stretch", False)),
                uniform=bool(ik.get("uniform", False)),
            )
        )

    return skel, data


def _parse_attachment(name: str, att: dict) -> Any:
    a_type = att.get("type", "region")
    path = att.get("path")
    color = _parse_color(att.get("color", "FFFFFFFF"))
    if a_type in (None, "region"):
        return RegionAttachment(
            name=name,
            path=path,
            x=float(att.get("x", 0.0)),
            y=float(att.get("y", 0.0)),
            rotation=float(att.get("rotation", 0.0)),
            scale_x=float(att.get("scaleX", 1.0)),
            scale_y=float(att.get("scaleY", 1.0)),
            width=float(att.get("width", 0.0)),
            height=float(att.get("height", 0.0)),
            color=color,
        )
    if a_type == "mesh":
        return MeshAttachment(
            name=name,
            path=path,
            uv=list(att.get("uvs", []) or []),
            triangles=list(att.get("triangles", []) or []),
            vertices=list(att.get("vertices", []) or []),
            hull=int(att.get("hull", 0)),
            edges=list(att.get("edges", []) or []),
            color=color,
            width=float(att.get("width", 0.0)),
            height=float(att.get("height", 0.0)),
        )
    if a_type == "linkedmesh":
        return MeshAttachment(
            name=name,
            path=path,
            parent=att.get("parent"),
            skin=att.get("skin"),
            color=color,
            width=float(att.get("width", 0.0)),
            height=float(att.get("height", 0.0)),
        )
    if a_type == "point":
        return PointAttachment(
            name=name,
            x=float(att.get("x", 0.0)),
            y=float(att.get("y", 0.0)),
            rotation=float(att.get("rotation", 0.0)),
            color=_parse_color(att.get("color", "F1F100FF")),
        )
    return None


def _bezier_ease(f: float, cx1: float, cy1: float, cx2: float, cy2: float) -> float:
    if f <= 0.0:
        return 0.0
    if f >= 1.0:
        return 1.0
    u = f
    for _ in range(8):
        omu = 1.0 - u
        bx = 3.0 * omu * omu * u * cx1 + 3.0 * omu * u * u * cx2 + u * u * u
        diff = bx - f
        if abs(diff) < 1e-6:
            break
        dbx = (
            3.0 * omu * omu * cx1
            + 6.0 * omu * u * (cx2 - cx1)
            + 3.0 * u * u * (1.0 - cx2)
        )
        if abs(dbx) < 1e-8:
            break
        u -= diff / dbx
        u = max(0.0, min(1.0, u))
    omu = 1.0 - u
    return 3.0 * omu * omu * u * cy1 + 3.0 * omu * u * u * cy2 + u * u * u


def _read_curve(kf: dict) -> tuple[str, Optional[tuple[float, float, float, float]]]:
    if "curve" not in kf:
        return "linear", None
    c = kf["curve"]
    if isinstance(c, str):
        if c == "stepped":
            return "stepped", None
        return "linear", None
    if isinstance(c, list) and len(c) >= 4:
        return "bezier", (float(c[0]), float(c[1]), float(c[2]), float(c[3]))
    if isinstance(c, (int, float)):
        cx1 = float(c)
        cy1 = float(kf.get("c2", 0.0))
        cx2 = float(kf.get("c3", 1.0))
        cy2 = float(kf.get("c4", 1.0))
        return "bezier", (cx1, cy1, cx2, cy2)
    return "linear", None


def _eval_channel(
    keys: list[dict], field: str, t: float, default: float = 0.0
) -> float:
    if not keys:
        return default
    if t <= float(keys[0].get("time", 0.0)):
        return float(keys[0].get(field, default))

    prev = keys[0]
    for kf in keys[1:]:
        kf_time = float(kf.get("time", 0.0))
        if kf_time >= t:
            t0 = float(prev.get("time", 0.0))
            t1 = kf_time
            v0 = float(prev.get(field, default))
            v1 = float(kf.get(field, default))
            kind, ctrl = _read_curve(prev)
            if kind == "stepped":
                return v0
            if t1 <= t0:
                return v1
            f = (t - t0) / (t1 - t0)
            if kind == "bezier" and ctrl is not None:
                f = _bezier_ease(f, *ctrl)
            return v0 + (v1 - v0) * f
        prev = kf
    return float(prev.get(field, default))


def _eval_xy(
    keys: list[dict], t: float, default: tuple[float, float] = (0.0, 0.0)
) -> tuple[float, float]:
    if not keys:
        return default
    if t <= float(keys[0].get("time", 0.0)):
        return (
            float(keys[0].get("x", default[0])),
            float(keys[0].get("y", default[1])),
        )
    prev = keys[0]
    for kf in keys[1:]:
        kf_time = float(kf.get("time", 0.0))
        if kf_time >= t:
            t0 = float(prev.get("time", 0.0))
            t1 = kf_time
            v0x = float(prev.get("x", default[0]))
            v0y = float(prev.get("y", default[1]))
            v1x = float(kf.get("x", default[0]))
            v1y = float(kf.get("y", default[1]))
            kind, ctrl = _read_curve(prev)
            if kind == "stepped":
                return v0x, v0y
            if t1 <= t0:
                return v1x, v1y
            f = (t - t0) / (t1 - t0)
            if kind == "bezier" and ctrl is not None:
                f = _bezier_ease(f, *ctrl)
            return (
                v0x + (v1x - v0x) * f,
                v0y + (v1y - v0y) * f,
            )
        prev = kf
    return (
        float(prev.get("x", default[0])),
        float(prev.get("y", default[1])),
    )


def _eval_color(
    keys: list[dict],
    t: float,
    default: tuple[int, int, int, int] = (255, 255, 255, 255),
) -> tuple[int, int, int, int]:
    if not keys:
        return default
    if t <= float(keys[0].get("time", 0.0)):
        return _parse_color(keys[0].get("color", "FFFFFFFF"), default)

    prev = keys[0]
    for kf in keys[1:]:
        kf_time = float(kf.get("time", 0.0))
        if kf_time >= t:
            t0 = float(prev.get("time", 0.0))
            t1 = kf_time
            c0 = _parse_color(prev.get("color", "FFFFFFFF"), default)
            c1 = _parse_color(kf.get("color", "FFFFFFFF"), default)
            kind, ctrl = _read_curve(prev)
            if kind == "stepped":
                return c0
            if t1 <= t0:
                return c1
            f = (t - t0) / (t1 - t0)
            if kind == "bezier" and ctrl is not None:
                f = _bezier_ease(f, *ctrl)
            return tuple(int(round(a + (b - a) * f)) for a, b in zip(c0, c1))  # type: ignore[return-value]
        prev = kf
    return _parse_color(prev.get("color", "FFFFFFFF"), default)


def _mat_invert(m: Mat2x3) -> Mat2x3:
    a, b, c, d, e, f = m
    det = a * d - b * c
    if det == 0.0:
        return (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
    inv = 1.0 / det
    ia = d * inv
    ib = -b * inv
    ic = -c * inv
    id = a * inv
    ie = -(ia * e + ic * f)
    if_ = -(ib * e + id * f)
    return (ia, ib, ic, id, ie, if_)


def _mat_apply(m: Mat2x3, x: float, y: float) -> tuple[float, float]:
    a, b, c, d, e, f = m
    return (a * x + c * y + e, b * x + d * y + f)


def _world_rotation_of(m: Mat2x3) -> float:
    a, b, _, _, _, _ = m
    return math.degrees(math.atan2(b, a))


def _bone_local_from_world(
    bone: Bone,
    parent_world: Optional[Mat2x3],
    world: Mat2x3,
    pose: dict[str, float],
) -> Mat2x3:
    if parent_world is None:
        return world

    px, py = _mat_apply(_mat_invert(parent_world), world[4], world[5])
    parent_rot = _world_rotation_of(parent_world)
    local_rot = _world_rotation_of(world) - parent_rot
    return _bone_local_matrix(
        bone,
        px,
        py,
        local_rot,
        pose["scale_x"],
        pose["scale_y"],
        pose["shear_x"],
        pose["shear_y"],
    )


def _ik_apply(
    ik: IKConstraint,
    bones_by_name: dict[str, Bone],
    world: dict[str, Mat2x3],
    local_pose: dict[str, dict[str, float]],
) -> None:
    if len(ik.bones) != 2:
        return

    b0 = bones_by_name.get(ik.bones[0])
    b1 = bones_by_name.get(ik.bones[1])
    target_bone = bones_by_name.get(ik.target)
    if b0 is None or b1 is None or target_bone is None:
        return

    parent_name = b0.parent
    if parent_name is None or parent_name not in world:
        return

    parent_world = world[parent_name]
    inv_parent = _mat_invert(parent_world)

    tx, ty = _mat_apply(inv_parent, world[ik.target][4], world[ik.target][5])

    bone0_origin = _mat_apply(inv_parent, world[b0.name][4], world[b0.name][5])

    dx = tx - bone0_origin[0]
    dy = ty - bone0_origin[1]
    dist = math.hypot(dx, dy)

    len0 = b0.length
    len1 = b1.length
    if len0 <= 0.0 or len1 <= 0.0 or dist < 1e-6:
        return

    min_dist = abs(len0 - len1)
    max_dist = len0 + len1
    if not ik.stretch:
        dist = max(min_dist + 1e-6, min(max_dist - 1e-6, dist))

    cos_a0 = (len0 * len0 + dist * dist - len1 * len1) / (2.0 * len0 * dist)
    cos_a0 = max(-1.0, min(1.0, cos_a0))
    a0 = math.acos(cos_a0)

    cos_a1 = (len0 * len0 + len1 * len1 - dist * dist) / (2.0 * len0 * len1)
    cos_a1 = max(-1.0, min(1.0, cos_a1))
    a1 = math.acos(cos_a1)

    base_angle = math.atan2(dy, dx)

    if ik.bend_positive:
        r0_local = base_angle - a0
    else:
        r0_local = base_angle + a0

    if ik.bend_positive:
        r1_local = r0_local + (math.pi - a1)
    else:
        r1_local = r0_local - (math.pi - a1)

    parent_rot = _world_rotation_of(parent_world)
    world0_deg = math.degrees(r0_local) + parent_rot
    world1_deg = math.degrees(r1_local) + parent_rot

    bone0_world_pos = (world[b0.name][4], world[b0.name][5])

    p0 = local_pose[b0.name]
    a0w = math.radians(world0_deg)
    cos0, sin0 = math.cos(a0w), math.sin(a0w)
    sx0, sy0 = p0["scale_x"], p0["scale_y"]
    world[b0.name] = (
        cos0 * sx0,
        sin0 * sx0,
        -sin0 * sy0,
        cos0 * sy0,
        bone0_world_pos[0],
        bone0_world_pos[1],
    )

    tip_x = bone0_world_pos[0] + math.cos(a0w) * len0 * sx0
    tip_y = bone0_world_pos[1] + math.sin(a0w) * len0 * sx0

    p1 = local_pose[b1.name]
    a1w = math.radians(world1_deg)
    cos1, sin1 = math.cos(a1w), math.sin(a1w)
    sx1, sy1 = p1["scale_x"], p1["scale_y"]
    world[b1.name] = (
        cos1 * sx1,
        sin1 * sx1,
        -sin1 * sy1,
        cos1 * sy1,
        tip_x,
        tip_y,
    )


def _eval_attachment(keys: list[dict], t: float, fps: float = 30.0) -> Optional[str]:
    if not keys:
        return None

    def snap(kf: dict) -> float:
        raw = float(kf.get("time", 0.0))
        return round(raw * fps) / fps

    if t < snap(keys[0]):
        return None
    cur: Optional[str] = keys[0].get("name")
    for kf in keys:
        if snap(kf) <= t:
            cur = kf.get("name")
        else:
            break
    return cur


def _eval_draworder(keys: list[dict], t: float) -> Optional[list[dict]]:
    if not keys:
        return None
    cur: Optional[list[dict]] = None
    for kf in keys:
        if float(kf.get("time", 0.0)) <= t:
            cur = kf.get("offsets")
        else:
            break
    return cur


Mat2x3 = tuple[float, float, float, float, float, float]


def _mat_mul(p: Mat2x3, c: Mat2x3) -> Mat2x3:
    pa, pb, pc, pd, pe, pf = p
    ca, cb, cc, cd, ce, cf = c
    return (
        pa * ca + pc * cb,
        pb * ca + pd * cb,
        pa * cc + pc * cd,
        pb * cc + pd * cd,
        pa * ce + pc * cf + pe,
        pb * ce + pd * cf + pf,
    )


def _bone_local_matrix(
    bone: Bone,
    px: float,
    py: float,
    rot: float,
    sx: float,
    sy: float,
    shx: float,
    shy: float,
) -> Mat2x3:
    rad_y = math.radians(rot + shy)  # rotation + shearY
    rad_x = math.radians(rot + shx)  # rotation + shearX
    cos_y = math.cos(rad_y)
    sin_y = math.sin(rad_y)
    cos_x = math.cos(rad_x)
    sin_x = math.sin(rad_x)
    a = cos_y * sx
    b = sin_y * sx
    c = -sin_x * sy
    d = cos_x * sy
    return (a, b, c, d, px, py)


def _apply_transform_mode(parent: Mat2x3, child: Mat2x3, mode: int) -> Mat2x3:
    if mode == NORMAL:
        return _mat_mul(parent, child)

    pa, pb, pc, pd, pe, pf = parent
    ca, cb, cc, cd, ce, cf = child

    if mode == ONLY_TRANSLATION:
        return (ca, cb, cc, cd, pa * ce + pc * cf + pe, pb * ce + pd * cf + pf)

    if mode == NO_ROTATION_OR_REFLECTION:
        scale_x = math.hypot(pa, pb)
        scale_y = math.hypot(pc, pd)
        det = pa * pd - pb * pc
        if det < 0:
            scale_y = -scale_y
        return (
            ca * scale_x,
            cb * scale_x,
            cc * scale_y,
            cd * scale_y,
            pa * ce + pc * cf + pe,
            pb * ce + pd * cf + pf,
        )

    if mode == NO_SCALE:
        norm_x = math.hypot(pa, pb) or 1.0
        norm_y = math.hypot(pc, pd) or 1.0
        ra, rb = pa / norm_x, pb / norm_x
        rc, rd = pc / norm_y, pd / norm_y
        return (
            ra * ca + rc * cb,
            rb * ca + rd * cb,
            ra * cc + rc * cd,
            rb * cc + rd * cd,
            pa * ce + pc * cf + pe,
            pb * ce + pd * cf + pf,
        )

    if mode == NO_SCALE_OR_REFLECTION:
        norm_x = math.hypot(pa, pb) or 1.0
        norm_y = math.hypot(pc, pd) or 1.0
        ra, rb = pa / norm_x, pb / norm_x
        rc, rd = pc / norm_y, pd / norm_y
        return (
            ra * ca + rc * cb,
            rb * ca + rd * cb,
            ra * cc + rc * cd,
            rb * cc + rd * cd,
            pa * ce + pc * cf + pe,
            pb * ce + pd * cf + pf,
        )

    return _mat_mul(parent, child)


def _local_pose(bone: Bone, anim_bone: Optional[dict], t: float) -> dict[str, float]:
    pose = {
        "x": bone.x,
        "y": bone.y,
        "rotation": bone.rotation,
        "scale_x": bone.scale_x,
        "scale_y": bone.scale_y,
        "shear_x": bone.shear_x,
        "shear_y": bone.shear_y,
    }
    if not anim_bone:
        return pose

    if "rotate" in anim_bone:
        pose["rotation"] += _eval_channel(anim_bone["rotate"], "angle", t, 0.0)
    if "translate" in anim_bone:
        tx, ty = _eval_xy(anim_bone["translate"], t, (0.0, 0.0))
        pose["x"] += tx
        pose["y"] += ty
    if "scale" in anim_bone:
        sx, sy = _eval_xy(anim_bone["scale"], t, (1.0, 1.0))
        pose["scale_x"] *= sx
        pose["scale_y"] *= sy
    if "shear" in anim_bone:
        shx, shy = _eval_xy(anim_bone["shear"], t, (0.0, 0.0))
        pose["shear_x"] += shx
        pose["shear_y"] += shy
    return pose


def sample_skeleton_at(
    skel: Skeleton,
    anim: dict,
    t: float,
    *,
    active_skin: Optional[str] = None,
    fps: float = 30.0,
) -> dict[str, Any]:
    bones_by_name = {b.name: b for b in skel.bones}
    anim_bones = anim.get("bones", {}) or {}

    local_pose: dict[str, dict[str, float]] = {}
    for bone in skel.bones:
        local_pose[bone.name] = _local_pose(bone, anim_bones.get(bone.name), t)

    world: dict[str, Mat2x3] = {}
    for bone in skel.bones:
        p = local_pose[bone.name]
        lm = _bone_local_matrix(
            bone,
            p["x"],
            p["y"],
            p["rotation"],
            p["scale_x"],
            p["scale_y"],
            p["shear_x"],
            p["shear_y"],
        )
        if bone.parent and bone.parent in world:
            world[bone.name] = _apply_transform_mode(
                world[bone.parent], lm, bone.transform_mode
            )
        else:
            world[bone.name] = lm

    if skel.ik:
        for ik in sorted(skel.ik, key=lambda c: c.order):
            _ik_apply(ik, bones_by_name, world, local_pose)

    skin = skel.skin(active_skin) if active_skin else None
    if skin is None:
        skin = skel.skin("default")
    if skin is None and skel.skins:
        skin = skel.skins[0]

    default_skin = skel.skin("default")

    anim_slots = anim.get("slots", {}) or {}
    slot_states: dict[str, dict[str, Any]] = {}
    for slot in skel.slots:
        att_name = slot.attachment
        color = slot.color
        anim_slot = anim_slots.get(slot.name, {})
        if "attachment" in anim_slot:
            swapped = _eval_attachment(anim_slot["attachment"], t, fps=fps)
            if swapped is not None:
                att_name = swapped or None
        if "color" in anim_slot:
            color = _eval_color(anim_slot["color"], t, color)
        if "twoColor" in anim_slot:
            twokeys = anim_slot["twoColor"]
            if twokeys:
                cur = twokeys[0]
                for kf in twokeys:
                    if float(kf.get("time", 0.0)) <= t:
                        cur = kf
                    else:
                        break
                if "light" in cur:
                    color = _parse_color(cur["light"], color)

        att_obj = None
        if att_name:
            for sk in (skin, default_skin):
                if sk and slot.name in sk.attachments:
                    att_obj = sk.attachments[slot.name].get(att_name)
                    if att_obj is not None:
                        break

        slot_states[slot.name] = {
            "bone": slot.bone,
            "attachment": att_name,
            "attachment_obj": att_obj,
            "color": color,
            "blend": slot.blend,
            "world": world.get(slot.bone, (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)),
        }

    draworder_keys = anim.get("draworder", []) or []
    offsets = _eval_draworder(draworder_keys, t)
    if offsets:
        order = [s.name for s in skel.slots]
        for off in offsets:
            slot_name = off.get("slot")
            delta = int(off.get("offset", 0))
            if slot_name in order:
                order.remove(slot_name)
                new_index = max(
                    0,
                    min(
                        len(order),
                        (
                            order.index(slot_name) + delta
                            if slot_name in order
                            else len(order)
                        ),
                    ),
                )
                orig_idx = next(
                    (i for i, n in enumerate(order) if n == slot_name), len(order)
                )
                order.insert(max(0, min(len(order), orig_idx + delta)), slot_name)
        if len(order) != len(skel.slots):
            order = [s.name for s in skel.slots]
    else:
        order = [s.name for s in skel.slots]

    return {"bones": world, "slots": slot_states, "draworder": order}
