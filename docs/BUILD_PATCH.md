# Build Guide

This project builds a local Atmosphere RomFS override package from your own extracted game files.

## Requirements

- Python 3
- Pillow for preview image generation
- Extracted game RomFS containing `alldata.bin` and `alldata.psb.m`
- Extracted archive contents under `m2_work/extracted`

The script uses `tools/m2_archive.py` to decrypt/decompress and recompress the M2 archive format used by this game.

## Build

From the project root:

```bash
python3 tools/create_lowercase_patch.py
```

Expected output:

```text
m2_work/steinsgate_sentence_case_english.nes
m2_work/sentence_case_english_font_preview.png
output/steinsgate_sentence_case_english.zip
```

## Install

Open `output/steinsgate_sentence_case_english.zip` and copy:

```text
atmosphere/
```

to the root of your SD card.

## What The Patch Changes

- Replaces the original text font's visible `A-Z` glyphs with lowercase glyphs.
- Copies the original uppercase glyphs into unused CHR tiles.
- Repoints confirmed script sentence starts to those uppercase tiles.
- Updates the `system/roms/steinsgate.nes.m` size entry inside `alldata.psb.m` if recompression produces a larger file.

It does not translate the game.

