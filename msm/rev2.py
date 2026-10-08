#
# rev2.py
# Taken from Aniviewer
#

from os.path import splitext
from json import load, dump
from binfile import BinFile
from typing import Self
from enum import Enum
from sys import argv


class Immediate(Enum):
    UNSET: int = -1
    SET: int = 0
    NONE: int = 1

    @classmethod
    def read(cls, bf: BinFile) -> Self:
        return cls(bf.readInt8())

    def write(self, bf: BinFile) -> None:
        bf.writeInt8(self.value)


class DataValue:
    def __init__(self, immediate: Immediate, value: float) -> None:
        self.immediate = immediate
        self.value = value

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        return cls(Immediate(data.get("immediate", 0)), data.get("value", 0.0))

    @classmethod
    def read(cls, bf: BinFile) -> Self:
        return cls(Immediate.read(bf), bf.readFloat())

    def to_dict(self) -> dict:
        return {"immediate": self.immediate.value, "value": self.value}

    def write(self, bf: BinFile) -> None:
        self.immediate.write(bf)
        bf.writeFloat(self.value)


class DataXY:
    def __init__(self, immediate: Immediate, x: float, y: float) -> None:
        self.immediate = immediate
        self.x = x
        self.y = y

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        return cls(
            Immediate(data.get("immediate", 0)), data.get("x", 0.0), data.get("y", 0.0)
        )

    @classmethod
    def read(cls, bf: BinFile) -> Self:
        return cls(Immediate.read(bf), bf.readFloat(), bf.readFloat())

    def to_dict(self) -> dict:
        return {"immediate": self.immediate.value, "x": self.x, "y": self.y}

    def write(self, bf: BinFile) -> None:
        self.immediate.write(bf)
        bf.writeFloat(self.x)
        bf.writeFloat(self.y)


class DataRect:
    def __init__(
        self, immediate: Immediate, x: float, y: float, w: float, h: float
    ) -> None:
        self.immediate = immediate
        self.x = x
        self.y = y
        self.w = w
        self.h = h

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        return cls(
            Immediate(data.get("immediate", 0)),
            data.get("x", 0.0),
            data.get("y", 0.0),
            data.get("w", 0.0),
            data.get("h", 0.0),
        )

    @classmethod
    def read(cls, bf: BinFile) -> Self:
        return cls(
            Immediate.read(bf),
            bf.readFloat(),
            bf.readFloat(),
            bf.readFloat(),
            bf.readFloat(),
        )

    def to_dict(self) -> dict:
        return {
            "immediate": self.immediate.value,
            "x": self.x,
            "y": self.y,
            "w": self.w,
            "h": self.h,
        }

    def write(self, bf: BinFile) -> None:
        self.immediate.write(bf)
        bf.writeFloat(self.x)
        bf.writeFloat(self.y)
        bf.writeFloat(self.w)
        bf.writeFloat(self.h)


class DataString:
    def __init__(self, immediate: Immediate, string: str) -> None:
        self.immediate = immediate
        self.string = string

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        return cls(Immediate(data.get("immediate", 0)), data.get("string", ""))

    @classmethod
    def read(cls, bf: BinFile) -> Self:
        return cls(Immediate.read(bf), bf.readString())

    def to_dict(self) -> dict:
        return {"immediate": self.immediate.value, "string": self.string}

    def write(self, bf: BinFile) -> None:
        self.immediate.write(bf)
        bf.writeString(self.string)


class DataFont:
    def __init__(
        self,
        immediate: Immediate,
        size: int,
        align: int,
        r: int,
        g: int,
        b: int,
        f_type: int,
        name: str,
        width: float,
        height: float,
    ) -> None:
        self.immediate = immediate
        self.size = size
        self.align = align
        self.r = r
        self.g = g
        self.b = b
        self.type = f_type
        self.name = name
        self.width = width
        self.height = height

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        return cls(
            Immediate(data.get("immediate", 0)),
            data.get("size", 0),
            data.get("align", 0),
            data.get("r", 255),
            data.get("g", 255),
            data.get("b", 255),
            data.get("type", 0),
            data.get("name", ""),
            data.get("width", 0.0),
            data.get("height", 0.0),
        )

    @classmethod
    def read(cls, bf: BinFile) -> Self:
        return cls(
            Immediate.read(bf),
            bf.readInt32(),
            bf.readUInt32(),
            bf.readUInt8(),
            bf.readUInt8(),
            bf.readUInt8(),
            bf.readUInt8(),
            bf.readString(),
            bf.readFloat(),
            bf.readFloat(),
        )

    def to_dict(self) -> dict:
        return {
            "immediate": self.immediate.value,
            "size": self.size,
            "align": self.align,
            "r": self.r,
            "g": self.g,
            "b": self.b,
            "type": self.type,
            "name": self.name,
            "width": self.width,
            "height": self.height,
        }

    def write(self, bf: BinFile) -> None:
        self.immediate.write(bf)
        bf.writeInt32(self.size)
        bf.writeUInt32(self.align)
        bf.writeUInt8(self.r)
        bf.writeUInt8(self.g)
        bf.writeUInt8(self.b)
        bf.writeUInt8(self.type)
        bf.writeString(self.name)
        bf.writeFloat(self.width)
        bf.writeFloat(self.height)


class Blend(Enum):
    NORMAL: int = 0
    ADDITIVE: int = 1
    SUBTRACTIVE: int = 2

    @classmethod
    def read(cls, bf: BinFile) -> Self:
        return cls(bf.readUInt32())

    def write(self, bf: BinFile) -> None:
        bf.writeUInt32(self.value)


class Frame:
    def __init__(
        self,
        time: float,
        mask: DataRect,
        anchor: DataXY,
        pos: DataXY,
        scale: DataXY,
        rotation: DataValue,
        opacity: DataValue,
        cell: DataXY,
        index: DataValue,
        depth: DataValue,
        sprite: DataString,
        font: DataFont,
    ) -> None:
        self.time = time
        self.mask = mask
        self.anchor = anchor
        self.pos = pos
        self.scale = scale
        self.rotation = rotation
        self.opacity = opacity
        self.cell = cell
        self.index = index
        self.depth = depth
        self.sprite = sprite
        self.font = font

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        return cls(
            data.get("time", 0.0),
            DataRect.from_dict(data.get("mask", {})),
            DataXY.from_dict(data.get("anchor", {})),
            DataXY.from_dict(data.get("pos", {})),
            DataXY.from_dict(data.get("scale", {})),
            DataValue.from_dict(data.get("rotation", {})),
            DataValue.from_dict(data.get("opacity", {})),
            DataXY.from_dict(data.get("cell", {})),
            DataValue.from_dict(data.get("index", {})),
            DataValue.from_dict(data.get("depth", {})),
            DataString.from_dict(data.get("sprite", {})),
            DataFont.from_dict(data.get("font", {})),
        )

    @classmethod
    def read(cls, bf: BinFile) -> Self:
        return cls(
            bf.readFloat(),
            DataRect.read(bf),
            DataXY.read(bf),
            DataXY.read(bf),
            DataXY.read(bf),
            DataValue.read(bf),
            DataValue.read(bf),
            DataXY.read(bf),
            DataValue.read(bf),
            DataValue.read(bf),
            DataString.read(bf),
            DataFont.read(bf),
        )

    def to_dict(self) -> dict:
        return {
            "time": self.time,
            "mask": self.mask.to_dict(),
            "anchor": self.anchor.to_dict(),
            "pos": self.pos.to_dict(),
            "scale": self.scale.to_dict(),
            "rotation": self.rotation.to_dict(),
            "opacity": self.opacity.to_dict(),
            "cell": self.cell.to_dict(),
            "index": self.index.to_dict(),
            "depth": self.depth.to_dict(),
            "sprite": self.sprite.to_dict(),
            "font": self.font.to_dict(),
        }

    def write(self, bf: BinFile) -> None:
        bf.writeFloat(self.time)
        self.mask.write(bf)
        self.anchor.write(bf)
        self.pos.write(bf)
        self.scale.write(bf)
        self.rotation.write(bf)
        self.opacity.write(bf)
        self.cell.write(bf)
        self.index.write(bf)
        self.depth.write(bf)
        self.sprite.write(bf)
        self.font.write(bf)


class Layer:
    def __init__(
        self,
        name: str,
        parent: str,
        l_id: int,
        l_type: int,
        src: int,
        blend: Blend,
        frames: list[Frame],
    ) -> None:
        self.name = name
        self.parent = parent
        self.id = l_id
        self.type = l_type
        self.src = src
        self.blend = blend
        self.frames = frames

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        return cls(
            data.get("name", ""),
            data.get("parent", "-1"),
            data.get("id", 0),
            data.get("type", 1),
            data.get("src", 0),
            Blend(data.get("blend", Blend.NORMAL)),
            [Frame.from_dict(frame) for frame in data.get("frames", [])],
        )

    @classmethod
    def read(cls, bf: BinFile) -> Self:
        return cls(
            bf.readString(),
            bf.readString(),
            bf.readUInt32(),
            bf.readInt32(),
            bf.readUInt32(),
            Blend.read(bf),
            [Frame.read(bf) for _ in range(bf.readUInt32())],
        )

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "parent": self.parent,
            "id": self.id,
            "type": self.type,
            "src": self.src,
            "blend": self.blend.value,
            "frames": [frame.to_dict() for frame in self.frames],
        }

    def write(self, bf: BinFile) -> None:
        bf.writeString(self.name)
        bf.writeString(self.parent)
        bf.writeUInt32(self.id)
        bf.writeInt32(self.type)
        bf.writeUInt32(self.src)
        self.blend.write(bf)
        bf.writeUInt32(len(self.frames))
        [frame.write(bf) for frame in self.frames]


class Animation:
    def __init__(
        self,
        name: str,
        width: int,
        height: int,
        loop_offset: float,
        centered: int,
        layers: list[Layer],
    ) -> None:
        self.name = name
        self.width = width
        self.height = height
        self.loop_offset = loop_offset
        self.centered = centered
        self.layers = layers

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        return cls(
            data.get("name", ""),
            data.get("width", 0),
            data.get("height", 0),
            data.get("loop_offset", 0.0),
            data.get("centered", 0),
            [Layer.from_dict(layer) for layer in data.get("layers", [])],
        )

    @classmethod
    def read(cls, bf: BinFile) -> Self:
        return cls(
            bf.readString(),
            bf.readUInt16(),
            bf.readUInt16(),
            bf.readFloat(),
            bf.readUInt32(),
            [Layer.read(bf) for _ in range(bf.readUInt32())],
        )

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "width": self.width,
            "height": self.height,
            "loop_offset": self.loop_offset,
            "centered": self.centered,
            "layers": [layer.to_dict() for layer in self.layers],
        }

    def write(self, bf: BinFile) -> None:
        bf.writeString(self.name)
        bf.writeUInt16(self.width)
        bf.writeUInt16(self.height)
        bf.writeFloat(self.loop_offset)
        bf.writeUInt32(self.centered)
        bf.writeUInt32(len(self.layers))
        [layer.write(bf) for layer in self.layers]


class Source:
    def __init__(self, src: str, _id: int, width: int, height: int) -> None:
        self.src = src
        self.id = _id
        self.width = width
        self.height = height

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        return cls(
            data.get("src", ""),
            data.get("id", 0),
            data.get("width", 0),
            data.get("height", 0),
        )

    @classmethod
    def read(cls, bf: BinFile) -> Self:
        src: str = bf.readString()
        _id: int = bf.readUInt16()
        w: int = bf.readUInt16()
        h: int = bf.readUInt16()
        return cls(src, _id, w, h)

    def to_dict(self) -> dict:
        return {
            "src": self.src,
            "id": self.id,
            "width": self.width,
            "height": self.height,
        }

    def write(self, bf: BinFile) -> None:
        bf.writeString(self.src)
        bf.writeUInt16(self.id)
        bf.writeUInt16(self.width)
        bf.writeUInt16(self.height)


class BinAnim:
    REV: int = 2

    def __init__(self, sources: list[Source], anims: list[Animation]) -> None:
        self.sources: list[Source] = sources
        self.anims: list[Animation] = anims

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        rev: int = data.get("rev", 0)
        if rev != BinAnim.REV:
            raise Exception(f"Rev {rev} not supported!")
        return cls(
            [Source.from_dict(source) for source in data.get("sources", [])],
            [Animation.from_dict(anim) for anim in data.get("anims", [])],
        )

    @classmethod
    def from_json(cls, filename: str) -> Self:
        with open(filename, "r") as f:
            return cls.from_dict(load(f))

    @classmethod
    def from_file(cls, filename: str) -> Self:
        bf: BinFile = BinFile(filename)
        self: BinAnim = cls(
            [Source.read(bf) for _ in range(bf.readUInt32())],
            [Animation.read(bf) for _ in range(bf.readUInt32())],
        )
        bf.close()
        return self

    def save(self, filename: str) -> None:
        bf: BinFile = BinFile(filename, True)
        bf.writeUInt32(len(self.sources))
        [source.write(bf) for source in self.sources]
        bf.writeUInt32(len(self.anims))
        [anim.write(bf) for anim in self.anims]
        bf.close()

    def to_dict(self) -> dict:
        return {
            "rev": BinAnim.REV,
            "sources": [source.to_dict() for source in self.sources],
            "anims": [anim.to_dict() for anim in self.anims],
        }

    def to_json(self, filename: str) -> None:
        with open(filename, "w") as f:
            dump(self.to_dict(), f, indent=2)


def main() -> None:
    usage: str = (
        f"usages:\n\t"
        f"rev{BinAnim.REV}-2-json d file.bin\n\t"
        f"rev{BinAnim.REV}-2-json b file.json"
    )
    if len(argv) < 3:
        return print(usage)
    mode: str = argv[1]
    filename: str = argv[2]
    file: str
    ext: str
    file, ext = splitext(filename)

    match mode:
        case "d":
            anim: BinAnim = BinAnim.from_file(filename)
            anim.to_json(f"{file}.json")
        case "b":
            anim: BinAnim = BinAnim.from_json(filename)
            anim.save(f"{file}.bin")
        case _:
            print(usage)


from msm._common import (
    IMM_UNSET,
    _BLEND_OLD_TO_REV6,
    _BLEND_REV6_TO_OLD,
    _empty_pos,
    _empty_scale,
    _empty_val,
    _empty_str,
    _empty_rgb,
    _empty_rect,
    _empty_font,
    _coerce_bool_immediate,
)

REV = 2


def _rev2_frame_to_rev6(frame: "Frame") -> dict:
    return {
        "time": float(frame.time),
        "pos": frame.pos.to_dict(),
        "scale": frame.scale.to_dict(),
        "rotation": frame.rotation.to_dict(),
        "opacity": frame.opacity.to_dict(),
        "sprite": frame.sprite.to_dict(),
        "rgb": _empty_rgb(),
    }


def _rev2_layer_to_rev6(layer: "Layer", name_to_id: dict[str, int]) -> dict:
    parent_name = (layer.parent or "").strip()
    if parent_name in ("", "-1"):
        parent_id = -1
    elif ":" in parent_name and parent_name.split(":", 1)[0].lstrip("-").isdigit():
        parent_id = int(parent_name.split(":", 1)[0])
    else:
        parent_id = name_to_id.get(parent_name, -1)

    return {
        "name": layer.name,
        "type": int(layer.type),
        "blend": _BLEND_OLD_TO_REV6.get(int(layer.blend.value), 0),
        "parent": int(parent_id),
        "id": int(layer.id),
        "src": int(layer.src),
        "width": 0,
        "height": 0,
        "anchor_x": 0.0,
        "anchor_y": 0.0,
        "unk": "",
        "frames": [_rev2_frame_to_rev6(f) for f in layer.frames],
    }


def _rev2_anim_to_rev6(anim: "Animation") -> dict:
    name_to_id: dict[str, int] = {l.name: int(l.id) for l in anim.layers}
    return {
        "name": anim.name,
        "width": int(anim.width),
        "height": int(anim.height),
        "loop_offset": float(anim.loop_offset),
        "centered": int(anim.centered),
        "layers": [_rev2_layer_to_rev6(l, name_to_id) for l in anim.layers],
        "clone_layers": [],
    }


def load_bin(path: str) -> dict:
    obj = BinAnim.from_file(path)
    return {
        "rev": 6,
        "blend_version": 2,
        "sources": [s.to_dict() for s in obj.sources],
        "anims": [_rev2_anim_to_rev6(a) for a in obj.anims],
    }


_BLEND_REV6_TO_REV2 = dict(_BLEND_REV6_TO_OLD)
_BLEND_REV6_TO_REV2[7] = 1


def _rgb_factor(rgb: dict | None) -> float:
    return 1.0


def _rev6_frame_to_rev2(
    frame: dict,
    anchor: tuple[float, float] = (0.0, 0.0),
    first: bool = True,
    animated_sprite: bool = False,
) -> dict:
    opacity = dict(frame.get("opacity", _empty_val(100.0)))
    factor = _rgb_factor(frame.get("rgb"))
    if factor != 1.0 and "value" in opacity:
        opacity["value"] = float(opacity["value"]) * factor

    if first:
        anchor_d = {"immediate": 0, "x": float(anchor[0]), "y": float(anchor[1])}
    else:
        anchor_d = {"immediate": IMM_UNSET, "x": 0.0, "y": 0.0}
    sprite = dict(frame.get("sprite", _empty_str()))

    if animated_sprite and int(sprite.get("immediate", IMM_UNSET)) == 0:
        sprite["immediate"] = 1
    return {
        "time": float(frame.get("time", 0.0)),
        "mask": _empty_rect(),
        "anchor": anchor_d,
        "pos": frame.get("pos", _empty_pos()),
        "scale": frame.get("scale", _empty_scale()),
        "rotation": frame.get("rotation", _empty_val(0.0)),
        "opacity": opacity,
        "cell": _empty_pos(),
        "index": _empty_val(0.0),
        "depth": _empty_val(0.0),
        "sprite": sprite,
        "font": _empty_font(),
    }


def _unique_layer_names(layers: list[dict]) -> dict[int, str]:
    seen: dict[str, int] = {}
    out: dict[int, str] = {}
    for l in layers:
        lid = int(l.get("id", 0))
        name = l.get("name", "")
        if name in seen:
            seen[name] += 1
            new = f"{name}_{lid}"
            while new in seen:
                new += "_"
            seen[new] = 0
            out[lid] = new
        else:
            seen[name] = 0
            out[lid] = name
    return out


def _rev6_layer_to_rev2(
    layer: dict, new_id: int, id_map: dict[int, int], names: dict[int, str]
) -> dict:
    old_id = int(layer.get("id", 0))
    parent_old = int(layer.get("parent", -1))
    if parent_old != -1 and parent_old in id_map:
        pid = id_map[parent_old]
        parent = f"{pid}:{names[parent_old]}"
    else:
        parent = "-1"
    anchor = (float(layer.get("anchor_x", 0.0)), float(layer.get("anchor_y", 0.0)))
    frames = layer.get("frames", [])
    sprites = {
        f["sprite"].get("string")
        for f in frames
        if int(f.get("sprite", {}).get("immediate", IMM_UNSET)) == 0
    }
    animated = len(sprites) > 1

    return {
        "name": names[old_id],
        "parent": parent,
        "id": new_id,
        "type": int(layer.get("type", 1)),
        "src": int(layer.get("src", 0)),
        "blend": _BLEND_REV6_TO_REV2.get(int(layer.get("blend", 0)), 0),
        "frames": [
            _rev6_frame_to_rev2(f, anchor, i == 0, animated)
            for i, f in enumerate(frames)
        ],
    }


def _rev6_anim_to_rev2(anim: dict) -> "Animation":
    layers_in = anim.get("layers", []) or []
    names = _unique_layer_names(layers_in)
    id_map = {int(l.get("id", 0)): i for i, l in enumerate(layers_in)}
    return Animation.from_dict(
        {
            "name": anim.get("name", ""),
            "width": int(anim.get("width", 0)),
            "height": int(anim.get("height", 0)),
            "loop_offset": float(anim.get("loop_offset", 0.0)),
            "centered": int(anim.get("centered", 0)),
            "layers": [
                _rev6_layer_to_rev2(l, i, id_map, names)
                for i, l in enumerate(layers_in)
            ],
        }
    )


def save_bin(payload: dict, path: str) -> None:
    obj = BinAnim(
        sources=[
            Source(s.get("src", ""), int(s.get("id", 0)), 0, 0)
            for s in payload.get("sources", [])
        ],
        anims=[_rev6_anim_to_rev2(a) for a in payload.get("anims", [])],
    )
    obj.save(path)


if __name__ == "__main__":
    main()
