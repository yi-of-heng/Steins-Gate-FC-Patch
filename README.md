# 8-BIT ADVENTURE STEINS;GATE English Case Patch Tools

Tools and notes for a small visual patch for `8-BIT ADVENTURE STEINS;GATE` on Nintendo Switch.

The patch changes the embedded NES text font from all-caps English to a more readable sentence-case style:

- Title prompt: `PRESS A` -> `Press A`
- Dialogue text: sentence starts stay uppercase, most other letters become lowercase
- Standalone `I` stays uppercase
- Original English wording and line breaks are not translated or rewritten

## Important

This repository does **not** contain the game, ROM data, `alldata.bin`, `alldata.psb.m`, XCI/NSP files, or a prebuilt Atmosphere package.

You need your own legally obtained copy of the game and extracted RomFS files to build the installable patch locally.

## Expected Local Files

The build script expects this workspace layout:

```text
romfs/alldata.bin
romfs/alldata.psb.m
m2_work/extracted/_manifest.json
m2_work/extracted/system/roms/steinsgate.nes
m2_work/extracted/system/roms/steinsgate.nes.m
tools/m2_archive.py
tools/create_lowercase_patch.py
```

After the files are in place, run:

```bash
python3 tools/create_lowercase_patch.py
```

The generated installable package will be:

```text
output/steinsgate_sentence_case_english.zip
```

Install by copying the `atmosphere` folder from the generated zip to the root of your SD card.

## Documentation

- [Build guide](docs/BUILD_PATCH.md)
- [Technical notes](docs/TECHNICAL_NOTES.md)
- [Release notes](docs/RELEASE_NOTES.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)

## Status

Tested with the base game identified as Title ID `0100E9F00B882000`.
