#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import struct
import zlib
from pathlib import Path


N = 624
M = 397
MATRIX_A = 0x9908B0DF
UPPER_MASK = 0x80000000
LOWER_MASK = 0x7FFFFFFF


class MT19937:
    def __init__(self, init_key):
        self.mt = [0] * N
        self.mti = N + 1
        self.mag01 = [0, MATRIX_A]
        self.init_by_array(init_key)

    def init_genrand(self, seed):
        self.mt[0] = seed & 0xFFFFFFFF
        for i in range(1, N):
            self.mt[i] = (
                1812433253 * (self.mt[i - 1] ^ (self.mt[i - 1] >> 30)) + i
            ) & 0xFFFFFFFF
        self.mti = N

    def init_by_array(self, init_key):
        self.init_genrand(19650218)
        i = 1
        j = 0
        for _ in range(max(N, len(init_key))):
            self.mt[i] = (
                self.mt[i]
                ^ (((self.mt[i - 1] ^ (self.mt[i - 1] >> 30)) * 1664525) & 0xFFFFFFFF)
            )
            self.mt[i] = (self.mt[i] + init_key[j] + j) & 0xFFFFFFFF
            i += 1
            j += 1
            if i >= N:
                self.mt[0] = self.mt[N - 1]
                i = 1
            if j >= len(init_key):
                j = 0
        for _ in range(N - 1):
            self.mt[i] = (
                self.mt[i]
                ^ (((self.mt[i - 1] ^ (self.mt[i - 1] >> 30)) * 1566083941) & 0xFFFFFFFF)
            )
            self.mt[i] = (self.mt[i] - i) & 0xFFFFFFFF
            i += 1
            if i >= N:
                self.mt[0] = self.mt[N - 1]
                i = 1
        self.mt[0] = 0x80000000

    def genrand_int32(self):
        if self.mti >= N:
            for kk in range(N - M):
                y = ((self.mt[kk] & UPPER_MASK) | (self.mt[kk + 1] & LOWER_MASK)) >> 1
                self.mt[kk] = (self.mt[kk + M] ^ self.mag01[self.mt[kk + 1] & 1] ^ y) & 0xFFFFFFFF
            for kk in range(N - M, N - 1):
                y = ((self.mt[kk] & UPPER_MASK) | (self.mt[kk + 1] & LOWER_MASK)) >> 1
                self.mt[kk] = (self.mt[kk + (M - N)] ^ self.mag01[self.mt[kk + 1] & 1] ^ y) & 0xFFFFFFFF
            y = ((self.mt[N - 1] & UPPER_MASK) | (self.mt[0] & LOWER_MASK)) >> 1
            self.mt[N - 1] = (self.mt[M - 1] ^ self.mag01[self.mt[0] & 1] ^ y) & 0xFFFFFFFF
            self.mti = 0

        y = self.mt[self.mti]
        self.mti += 1
        y ^= y >> 11
        y ^= (y << 7) & 0x9D2C5680
        y ^= (y << 15) & 0xEFC60000
        y ^= y >> 18
        return y & 0xFFFFFFFF


def marchive_key(seed, filename, key_length):
    digest = hashlib.md5((seed + filename.lower()).encode("utf-8")).digest()
    init_key = [struct.unpack_from("<I", digest, i * 4)[0] for i in range(4)]
    mt = MT19937(init_key)
    out = bytearray()
    while len(out) < key_length:
        out += struct.pack("<I", mt.genrand_int32())
    return out[:key_length]


def mdf_decompress(path, seed, key_length):
    data = Path(path).read_bytes()
    if data[:4] != b"mdf\x00":
        raise ValueError(f"{path} is not an mdf archive")
    expected_len = struct.unpack_from("<I", data, 4)[0]
    key = marchive_key(seed, Path(path).name, key_length)
    body = bytearray(data[8:])
    for i in range(len(body)):
        body[i] ^= key[i % len(key)]
    out = zlib.decompress(bytes(body))
    if len(out) != expected_len:
        raise ValueError(f"decompressed length mismatch: expected {expected_len}, got {len(out)}")
    return out


def mdf_compress(data, filename, seed, key_length, level=9):
    key = marchive_key(seed, Path(filename).name, key_length)
    body = bytearray(zlib.compress(data, level))
    for i in range(len(body)):
        body[i] ^= key[i % len(key)]
    return b"mdf\x00" + struct.pack("<I", len(data)) + bytes(body)


class PsbReader:
    def __init__(self, data):
        self.data = data
        self.pos = 0
        if self.read(4) != b"PSB\x00":
            raise ValueError("not a PSB file")
        self.version = self.u16()
        self.flags = self.u16()
        if self.flags:
            raise NotImplementedError(f"filtered PSB flags are not supported: {self.flags}")
        self.keys_offsets_off = self.u32()
        self.keys_blob_off = self.u32()
        self.strings_offsets_off = self.u32()
        self.strings_blob_off = self.u32()
        self.streams_offsets_off = self.u32()
        self.streams_sizes_off = self.u32()
        self.streams_blob_off = self.u32()
        self.root_off = self.u32()
        if self.version >= 3:
            self.checksum = self.u32()
        if self.version >= 4:
            self.bstreams_offsets_off = self.u32()
            self.bstreams_sizes_off = self.u32()
            self.bstreams_blob_off = self.u32()
        self.keys = self.load_keys()
        self.strings_offsets = self.read_uint_array_at(self.strings_offsets_off)
        self.streams_offsets = self.read_uint_array_at(self.streams_offsets_off)
        self.streams_sizes = self.read_uint_array_at(self.streams_sizes_off)

    def read(self, n):
        chunk = self.data[self.pos : self.pos + n]
        if len(chunk) != n:
            raise EOFError("unexpected end of PSB")
        self.pos += n
        return chunk

    def seek(self, pos):
        self.pos = pos

    def u8(self):
        return self.read(1)[0]

    def i8(self):
        return struct.unpack("<b", self.read(1))[0]

    def u16(self):
        return struct.unpack("<H", self.read(2))[0]

    def i16(self):
        return struct.unpack("<h", self.read(2))[0]

    def u32(self):
        return struct.unpack("<I", self.read(4))[0]

    def i32(self):
        return struct.unpack("<i", self.read(4))[0]

    def i64(self):
        return struct.unpack("<q", self.read(8))[0]

    def read_uint_payload(self, type_id):
        if type_id == 13:
            return self.u8()
        if type_id == 14:
            return self.u16()
        if type_id == 15:
            return self.u16() | (self.u8() << 16)
        if type_id == 16:
            return self.u32()
        raise ValueError(f"bad uint type {type_id}")

    def read_uint_array(self):
        count_type = self.u8()
        count = self.read_uint_payload(count_type)
        value_type = self.u8()
        return [self.read_uint_payload(value_type) for _ in range(count)]

    def read_uint_array_at(self, offset):
        old = self.pos
        self.seek(offset)
        arr = self.read_uint_array()
        self.seek(old)
        return arr

    def read_cstring_at(self, offset):
        end = self.data.index(0, offset)
        return self.data[offset:end].decode("utf-8")

    def load_keys(self):
        if self.version == 1:
            offsets = self.read_uint_array_at(self.keys_offsets_off)
            return [self.read_cstring_at(self.keys_blob_off + off) for off in offsets]

        old = self.pos
        self.seek(self.keys_blob_off)
        value_offsets = self.read_uint_array()
        tree = self.read_uint_array()
        tails = self.read_uint_array()
        self.seek(old)
        keys = []
        for tail in tails:
            buf = bytearray()
            current = tree[tail]
            while current != 0:
                parent = tree[current]
                buf.append((current - value_offsets[parent]) & 0xFF)
                current = parent
            keys.append(bytes(reversed(buf)).decode("utf-8"))
        return keys

    def token(self):
        type_id = self.u8()
        if type_id == 1:
            return None
        if type_id == 2:
            return True
        if type_id == 3:
            return False
        if type_id == 4:
            return 0
        if type_id == 5:
            return self.i8()
        if type_id == 6:
            return self.i16()
        if type_id == 7:
            return self.u16() | (self.i8() << 16)
        if type_id == 8:
            return self.i32()
        if type_id == 9:
            return self.u32() | (self.i8() << 32)
        if type_id == 10:
            return self.u32() | (self.i16() << 32)
        if type_id == 11:
            return self.u32() | (self.u16() << 32) | (self.i8() << 48)
        if type_id == 12:
            return self.i64()
        if 13 <= type_id <= 16:
            return self.read_uint_payload(type_id)
        if 21 <= type_id <= 24:
            index = self.read_uint_payload(type_id - 8)
            return self.read_cstring_at(self.strings_blob_off + self.strings_offsets[index])
        if 25 <= type_id <= 28:
            index = self.read_uint_payload(type_id - 12)
            off = self.streams_blob_off + self.streams_offsets[index]
            size = self.streams_sizes[index]
            return {"__stream__": index, "size": size, "data": self.data[off : off + size]}
        if type_id == 29:
            return 0.0
        if type_id == 30:
            return struct.unpack("<f", self.read(4))[0]
        if type_id == 31:
            return struct.unpack("<d", self.read(8))[0]
        if type_id == 32:
            return self.token_array()
        if type_id == 33:
            return self.obj()
        raise ValueError(f"unsupported token type {type_id} at {self.pos - 1:#x}")

    def token_array(self):
        offsets = self.read_uint_array()
        base = self.pos
        out = []
        old = self.pos
        for off in offsets:
            self.seek(base + off)
            out.append(self.token())
        self.seek(old)
        return out

    def obj(self):
        out = {}
        if self.version == 1:
            offsets = self.read_uint_array()
            base = self.pos
            old = self.pos
            for off in offsets:
                self.seek(base + off)
                key_type = self.u8()
                key = self.keys[self.read_uint_payload(key_type - 4)]
                out[key] = self.token()
            self.seek(old)
            return out

        key_indexes = self.read_uint_array()
        offsets = self.read_uint_array()
        base = self.pos
        old = self.pos
        for key_index, off in zip(key_indexes, offsets):
            self.seek(base + off)
            out[self.keys[key_index]] = self.token()
        self.seek(old)
        return out

    def root(self):
        self.seek(self.root_off)
        return self.token()


def extract_archive(psbm_path, bin_path, out_dir, seed, key_length):
    psb = mdf_decompress(psbm_path, seed, key_length)
    reader = PsbReader(psb)
    root = reader.root()
    if root.get("object_type", root.get("id")) != "archive":
        raise ValueError("PSB manifest is not an archive")
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "_manifest.json").write_text(json.dumps(root, ensure_ascii=False, indent=2), encoding="utf-8")
    body = Path(bin_path).read_bytes()
    for name, (off, size) in root["file_info"].items():
        out_path = out_dir / name
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(body[off : off + size])
    return root


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    ext = sub.add_parser("extract")
    ext.add_argument("psbm")
    ext.add_argument("bin")
    ext.add_argument("out_dir")
    ext.add_argument("--seed", default="25G/xpvTbsb+6")
    ext.add_argument("--key-length", type=int, default=64)
    args = parser.parse_args()

    if args.cmd == "extract":
        root = extract_archive(args.psbm, args.bin, args.out_dir, args.seed, args.key_length)
        print(f"extracted {len(root['file_info'])} files to {args.out_dir}")


if __name__ == "__main__":
    main()
