# Technical Notes

## Archive Format

The Switch release stores the embedded NES ROM at:

```text
system/roms/steinsgate.nes.m
```

inside an M2 archive described by:

```text
alldata.psb.m
```

The `.m` files use an `mdf` container: zlib-compressed data XORed with a key derived from the file name and seed.

Known parameters used by the script:

```text
seed: 25G/xpvTbsb+6
key length: 64
title id: 0100E9F00B882000
```

## NES Layout

The base NES ROM has:

```text
PRG size: 0x80000
CHR start: 0x80010
text CHR bank: 0x11800
title prompt CHR bank: 0x13800
```

The original visible alphabet maps:

```text
A-Z: tile 0x1e through 0x37
0-9: tile 0x14 through 0x1d
```

The patch stores uppercase backups at:

```text
A-Z uppercase backup: tile 0x80 through 0x99
```

## Script Handling

The script does not perform broad byte replacement over the full ROM. It finds candidate text spans bounded by `FC ... FE`, then only accepts spans made of known text, punctuation, line, and inline control codes.

Accepted text spans are rewritten so:

- the first visible letter in a text span is uppercase
- letters after `.`, `?`, or `!` are uppercase
- standalone `I` stays uppercase
- other letters display through the lowercase tile set

This avoids touching unrelated code or data.

