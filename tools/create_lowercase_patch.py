#!/usr/bin/env python3
from __future__ import annotations

import shutil
import sys
import zipfile
import json
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.m2_archive import mdf_compress, mdf_decompress

ROOT = Path(__file__).resolve().parents[1]
BASE_NES = ROOT / "m2_work/extracted/system/roms/steinsgate.nes"
BASE_NES_M = ROOT / "m2_work/extracted/system/roms/steinsgate.nes.m"
BASE_ALDATA_BIN = ROOT / "romfs/alldata.bin"
BASE_ALDATA_PSBM = ROOT / "romfs/alldata.psb.m"
OUT_DIR = ROOT / "output/steinsgate_sentence_case_english"
TITLE_ID = "0100E9F00B882000"

CHR_TEXT_BANK = 0x11800
CHR_TITLE_BANK = 0x13800
TEXT_A_TILE = 0x1E
UPPER_A_TILE = 0x80

GLYPHS = {
    "a": ["00000000", "00000000", "00111000", "00000100", "00111100", "01000100", "00111100", "00000000"],
    "b": ["01000000", "01000000", "01011100", "01100010", "01000010", "01100010", "01011100", "00000000"],
    "c": ["00000000", "00000000", "00111100", "01000000", "01000000", "01000000", "00111100", "00000000"],
    "d": ["00000100", "00000100", "00110100", "01001100", "01000100", "01001100", "00110100", "00000000"],
    "e": ["00000000", "00000000", "00111000", "01000100", "01111000", "01000000", "00111100", "00000000"],
    "f": ["00011100", "00100000", "01110000", "00100000", "00100000", "00100000", "00100000", "00000000"],
    "g": ["00000000", "00000000", "00111100", "01000100", "00111100", "00000100", "00111000", "00000000"],
    "h": ["01000000", "01000000", "01011100", "01100010", "01000010", "01000010", "01000010", "00000000"],
    "i": ["00010000", "00000000", "00110000", "00010000", "00010000", "00010000", "00111000", "00000000"],
    "j": ["00001000", "00000000", "00011000", "00001000", "00001000", "01001000", "00110000", "00000000"],
    "k": ["01000000", "01000000", "01001000", "01010000", "01100000", "01010000", "01001000", "00000000"],
    "l": ["00110000", "00010000", "00010000", "00010000", "00010000", "00010000", "00111000", "00000000"],
    "m": ["00000000", "00000000", "01101100", "01010010", "01010010", "01010010", "01010010", "00000000"],
    "n": ["00000000", "00000000", "01011100", "01100010", "01000010", "01000010", "01000010", "00000000"],
    "o": ["00000000", "00000000", "00111000", "01000100", "01000100", "01000100", "00111000", "00000000"],
    "p": ["00000000", "00000000", "01011100", "01100010", "01011100", "01000000", "01000000", "00000000"],
    "q": ["00000000", "00000000", "00110100", "01001100", "00110100", "00000100", "00000110", "00000000"],
    "r": ["00000000", "00000000", "01011100", "01100010", "01000000", "01000000", "01000000", "00000000"],
    "s": ["00000000", "00000000", "00111100", "01000000", "00111000", "00000100", "01111000", "00000000"],
    "t": ["00100000", "00100000", "01110000", "00100000", "00100000", "00100010", "00011100", "00000000"],
    "u": ["00000000", "00000000", "01000010", "01000010", "01000010", "01000110", "00111010", "00000000"],
    "v": ["00000000", "00000000", "01000010", "01000010", "00100100", "00100100", "00011000", "00000000"],
    "w": ["00000000", "00000000", "01000010", "01010010", "01010010", "01010010", "00101100", "00000000"],
    "x": ["00000000", "00000000", "01000100", "00101000", "00010000", "00101000", "01000100", "00000000"],
    "y": ["00000000", "00000000", "01000010", "01000010", "00111110", "00000010", "00111100", "00000000"],
    "z": ["00000000", "00000000", "01111100", "00001000", "00010000", "00100000", "01111100", "00000000"],
}


def tile_bytes(rows: list[str]) -> bytes:
    plane = bytes(int(row, 2) for row in rows)
    return plane + plane


def chr_start(rom: bytes) -> int:
    return 16 + rom[4] * 0x4000


def write_tile(rom: bytearray, bank: int, tile: int, ch: str) -> None:
    start = chr_start(rom) + bank + tile * 16
    rom[start : start + 16] = tile_bytes(GLYPHS[ch])


def apply_lowercase_tiles(rom: bytearray) -> None:
    source = bytes(rom)
    for i, ch in enumerate("abcdefghijklmnopqrstuvwxyz"):
        upper_start = chr_start(rom) + CHR_TEXT_BANK + (TEXT_A_TILE + i) * 16
        spare_start = chr_start(rom) + CHR_TEXT_BANK + (UPPER_A_TILE + i) * 16
        rom[spare_start : spare_start + 16] = source[upper_start : upper_start + 16]
        write_tile(rom, CHR_TEXT_BANK, TEXT_A_TILE + i, ch)

    title_source = bytes(rom)
    for tile in (0x30, 0x34):
        start = chr_start(rom) + CHR_TITLE_BANK + tile * 16
        rom[start : start + 16] = title_source[start : start + 16]
    for tile, ch in {
        0x31: "r",
        0x32: "e",
        0x33: "s",
    }.items():
        write_tile(rom, CHR_TITLE_BANK, tile, ch)


def apply_sentence_case_text(rom: bytearray) -> int:
    letter_min = TEXT_A_TILE
    letter_max = TEXT_A_TILE + 25
    sentence_end = {0x03, 0x3B, 0x3C}  # . ? !
    valid_text_codes = (
        set(range(0x14, 0x1E))
        | set(range(letter_min, letter_max + 1))
        | {0x00, 0x03, 0x05, 0x06, 0x07, 0x0A, 0x0B, 0x38, 0x3A, 0x3B, 0x3C, 0x3D, 0x3E, 0xF9, 0xFF}
    )
    prg_end = 16 + rom[4] * 0x4000
    changed = 0

    def is_letter(value: int) -> bool:
        return letter_min <= value <= letter_max

    spans: list[tuple[int, int]] = []
    for marker in range(0x40000, prg_end):
        if rom[marker] != 0xFC:
            continue
        try:
            end = rom.index(0xFE, marker + 1, min(marker + 240, prg_end))
        except ValueError:
            continue
        span = rom[marker + 1 : end]
        if len(span) < 4:
            continue
        if sum(is_letter(value) for value in span) < 4:
            continue
        if any(value not in valid_text_codes for value in span):
            continue
        spans.append((marker + 1, end))

    for start, end in spans:
        capitalize_next = True
        for i in range(start, end):
            value = rom[i]
            if is_letter(value):
                prev_value = rom[i - 1] if i else 0
                next_value = rom[i + 1] if i + 1 < len(rom) else 0
                is_i_word = value == TEXT_A_TILE + 8 and (
                    prev_value in {0x00, 0xF9, 0xFC, 0x3A, 0x0A, 0x0B}
                    and (next_value in {0x00, 0xF9, 0xFE, 0x03, 0x3A, 0x3B, 0x3C, 0x38})
                )
                if capitalize_next or is_i_word:
                    rom[i] = UPPER_A_TILE + (value - TEXT_A_TILE)
                    changed += 1
                capitalize_next = False
                continue
            if value in sentence_end:
                capitalize_next = True
    return changed


def render_preview(rom: bytes, path: Path) -> None:
    scale = 4
    tile = 8
    cols = 26
    rows = 2
    image = Image.new("RGB", (cols * tile * scale, rows * tile * scale), "black")
    draw = ImageDraw.Draw(image)
    start = chr_start(rom) + CHR_TEXT_BANK

    for row, tile_base in enumerate((UPPER_A_TILE, TEXT_A_TILE)):
        for i in range(cols):
            data = rom[start + (tile_base + i) * 16 : start + (tile_base + i + 1) * 16]
            for y, bits in enumerate(data[:8]):
                for x in range(8):
                    if bits & (1 << (7 - x)):
                        x0 = (i * tile + x) * scale
                        y0 = (row * tile + y) * scale
                        draw.rectangle((x0, y0, x0 + scale - 1, y0 + scale - 1), fill="white")
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)


def update_manifest_size(new_size: int) -> bytes:
    manifest = mdf_decompress(BASE_ALDATA_PSBM, "25G/xpvTbsb+6", 64)
    old_size = len(BASE_NES_M.read_bytes())
    old = old_size.to_bytes(3, "little")
    new = new_size.to_bytes(3, "little")
    hits = []
    start = 0
    while True:
        hit = manifest.find(old, start)
        if hit < 0:
            break
        hits.append(hit)
        start = hit + 1
    if len(hits) != 1:
        raise RuntimeError(f"expected one archive size field for steinsgate.nes.m, found {len(hits)}")
    manifest = bytearray(manifest)
    manifest[hits[0] : hits[0] + 3] = new
    return mdf_compress(bytes(manifest), "alldata.psb.m", "25G/xpvTbsb+6", 64)


def write_package(patched_nesm: bytes) -> Path:
    content_dir = OUT_DIR / "atmosphere/contents" / TITLE_ID / "romfs"
    content_dir.mkdir(parents=True, exist_ok=True)

    aldata = bytearray(BASE_ALDATA_BIN.read_bytes())
    manifest_path = ROOT / "m2_work/extracted/_manifest.json"

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    off, size = manifest["file_info"]["system/roms/steinsgate.nes.m"]
    next_offsets = sorted(v[0] for v in manifest["file_info"].values() if v[0] > off)
    next_off = next_offsets[0] if next_offsets else len(aldata)
    if off + len(patched_nesm) > next_off:
        raise RuntimeError(
            f"patched steinsgate.nes.m ends at {off + len(patched_nesm)}, "
            f"but next archive file starts at {next_off}"
        )
    write_size = max(size, len(patched_nesm))
    aldata[off : off + write_size] = patched_nesm + b"\x00" * (write_size - len(patched_nesm))

    (content_dir / "alldata.bin").write_bytes(aldata)
    if len(patched_nesm) == size:
        shutil.copy2(BASE_ALDATA_PSBM, content_dir / "alldata.psb.m")
    else:
        (content_dir / "alldata.psb.m").write_bytes(update_manifest_size(len(patched_nesm)))

    readme = OUT_DIR / "README.txt"
    readme.write_text(
        "8-BIT ADVENTURE STEINS;GATE sentence-case English patch\n\n"
        "Content: changes the built-in NES text font to mostly lowercase, while "
        "sentence starts and standalone I stay uppercase.\n"
        "Install: copy the atmosphere folder to the SD card root.\n"
        f"Title ID: {TITLE_ID}\n",
        encoding="utf-8",
    )

    zip_path = ROOT / "output/steinsgate_sentence_case_english.zip"
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(OUT_DIR.rglob("*")):
            if path.is_file():
                zf.write(path, path.relative_to(OUT_DIR))
    return zip_path


def main() -> int:
    rom = bytearray(BASE_NES.read_bytes())
    apply_lowercase_tiles(rom)
    changed = apply_sentence_case_text(rom)

    work_rom = ROOT / "m2_work/steinsgate_sentence_case_english.nes"
    work_rom.write_bytes(rom)
    render_preview(rom, ROOT / "m2_work/sentence_case_english_font_preview.png")

    patched_nesm = mdf_compress(bytes(rom), "steinsgate.nes.m", "25G/xpvTbsb+6", 64)
    original_size = len(BASE_NES_M.read_bytes())
    if len(patched_nesm) <= original_size:
        padded = patched_nesm + b"\x00" * (original_size - len(patched_nesm))
        decompressed = mdf_decompress_bytes(padded, "steinsgate.nes.m", mdf_decompress)
        if decompressed != bytes(rom):
            raise RuntimeError("padded mdf verification failed")
        zip_path = write_package(padded)
    else:
        zip_path = write_package(patched_nesm)

    print(f"wrote {work_rom}")
    print(f"sentence-start letters patched: {changed}")
    print(f"wrote {ROOT / 'm2_work/sentence_case_english_font_preview.png'}")
    print(f"wrote {zip_path}")
    return 0


def mdf_decompress_bytes(data: bytes, filename: str, mdf_decompress_func) -> bytes:
    temp = ROOT / "m2_work/.lowercase_verify.nes.m"
    try:
        temp.write_bytes(data)
        verify_path = temp.with_name(filename)
        if verify_path.exists():
            verify_path.unlink()
        temp.rename(verify_path)
        return mdf_decompress_func(verify_path, "25G/xpvTbsb+6", 64)
    finally:
        path = ROOT / "m2_work" / filename
        if path.exists():
            path.unlink()
        if temp.exists():
            temp.unlink()


if __name__ == "__main__":
    raise SystemExit(main())
