#
# binfile.py
# Taken from Aniviewer
#

from struct import Struct
from typing import BinaryIO, Optional, Callable
import os
import time

_S_B = Struct("<B")
_S_H = Struct("<H")
_S_I = Struct("<I")
_S_b = Struct("<b")
_S_h = Struct("<h")
_S_i = Struct("<i")
_S_f = Struct("<f")


class BinFile:
    WHENCE_START: int = 0
    WHENCE_CURRENT: int = 1
    WHENCE_END: int = 2
    INT8: int = 1
    INT16: int = 2
    INT32: int = 4
    FLOAT: int = 4
    CHUNK: int = 4
    progress_callback: Optional[Callable[[float], None]] = None

    def __init__(self, filename: str, write: bool = False) -> None:
        self.filename = filename
        self._write = write

        if write:
            self.fp: Optional[BinaryIO] = None
            self._buf: bytearray = bytearray()
            self._pos: int = 0
            self._size: int = 0
        else:
            self.fp = open(filename, "rb")
            self._buf = bytearray()
            self._pos = 0
            self._size = os.path.getsize(filename) if os.path.exists(filename) else 0

        self._last_progress_time: float = 0.0

    def tell(self) -> int:
        if self._write:
            return self._pos
        return self.fp.tell() # type: ignore[union-attr]

    def seek(self, offset: int, whence: int = 0) -> int:
        if self._write:
            if whence == BinFile.WHENCE_START:
                self._pos = offset
            elif whence == BinFile.WHENCE_CURRENT:
                self._pos += offset
            elif whence == BinFile.WHENCE_END:
                self._pos = len(self._buf) + offset
            if self._pos > len(self._buf):
                self._buf.extend(b"\x00" * (self._pos - len(self._buf)))
            return self._pos
        return self.fp.seek(offset, whence) # type: ignore[union-attr]

    def __alignSeek(self, size: int) -> int:
        if self._write:
            pos = self._pos
        else:
            pos = self.fp.tell() # type: ignore[union-attr]
        off = pos % size
        if off:
            return self.seek(size - off, BinFile.WHENCE_CURRENT)
        return pos

    def __stringSeek(self, string: str) -> int:
        off = len(string) % BinFile.CHUNK
        pad = (BinFile.CHUNK - off) if off != 0 else 4
        return self.seek(pad, BinFile.WHENCE_CURRENT)

    def close(self) -> None:
        if self._write:
            with open(self.filename, "wb") as f:
                f.write(self._buf)
        else:
            self.fp.close() # type: ignore[union-attr]

    def _raw_write(self, data: bytes) -> int:
        end = self._pos + len(data)
        if end > len(self._buf):
            self._buf.extend(b"\x00" * (end - len(self._buf)))
        self._buf[self._pos : end] = data
        self._pos = end
        return len(data)

    def read(self, size: int) -> bytes:
        self.__alignSeek(size)
        data = self.fp.read(size) # type: ignore[union-attr]
        self.__emit_progress()
        return data

    def __emit_progress(self) -> None:
        cb = BinFile.progress_callback
        if not cb or self._size <= 0 or self.fp is None:
            return
        now = time.perf_counter()
        if now - self._last_progress_time < 0.05:
            return
        self._last_progress_time = now
        try:
            pos = self.fp.tell()
            cb(min(1.0, max(0.0, pos / self._size)))
        except Exception:
            return

    def write(self, mode: str, val: int | float) -> int:
        match mode:
            case "b":
                size = BinFile.INT8
                s = _S_b
            case "B":
                size = BinFile.INT8
                s = _S_B
            case "h":
                size = BinFile.INT16
                s = _S_h
            case "H":
                size = BinFile.INT16
                s = _S_H
            case "i":
                size = BinFile.INT32
                s = _S_i
            case "I":
                size = BinFile.INT32
                s = _S_I
            case "f":
                size = BinFile.FLOAT
                s = _S_f
            case _:
                raise ValueError(f"Invalid mode: {mode}")

        self.__alignSeek(size)
        if self._write:
            return self._raw_write(s.pack(val))
        return self.fp.write(s.pack(val)) # type: ignore[union-attr]

    def readUInt8(self) -> int:
        return _S_B.unpack(self.read(BinFile.INT8))[0]

    def readUInt16(self) -> int:
        return _S_H.unpack(self.read(BinFile.INT16))[0]

    def readUInt32(self) -> int:
        return _S_I.unpack(self.read(BinFile.INT32))[0]

    def readInt8(self) -> int:
        return _S_b.unpack(self.read(BinFile.INT8))[0]

    def readInt16(self) -> int:
        return _S_h.unpack(self.read(BinFile.INT16))[0]

    def readInt32(self) -> int:
        return _S_i.unpack(self.read(BinFile.INT32))[0]

    def readFloat(self) -> float:
        return _S_f.unpack(self.read(BinFile.FLOAT))[0]

    def readString(self) -> str:
        string_len: int = self.readUInt32() - 1
        raw: bytes = self.fp.read(string_len) # type: ignore[union-attr]
        self.__emit_progress()
        try:
            string: str = raw.decode("ascii")
        except UnicodeDecodeError:
            string = raw.decode("ascii", errors="ignore")
        self.__stringSeek(string)
        return string

    def writeUInt8(self, val: int) -> int:
        return self.write("B", val)

    def writeUInt16(self, val: int) -> int:
        return self.write("H", val)

    def writeUInt32(self, val: int) -> int:
        return self.write("I", val)

    def writeInt8(self, val: int) -> int:
        return self.write("b", val)

    def writeInt16(self, val: int) -> int:
        return self.write("h", val)

    def writeInt32(self, val: int) -> int:
        return self.write("i", val)

    def writeFloat(self, val: float) -> int:
        return self.write("f", val)

    def writeString(self, string: str) -> int:
        self.writeUInt32(len(string) + 1)
        raw = string.encode("ascii")
        if self._write:
            self._raw_write(raw)
        else:
            self.fp.write(raw) # type: ignore[union-attr]
        self.__stringSeek(string)
        return len(raw)
