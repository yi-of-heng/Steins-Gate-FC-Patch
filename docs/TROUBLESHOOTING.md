# Troubleshooting

## `ModuleNotFoundError: No module named 'PIL'`

Install Pillow:

```bash
python3 -m pip install pillow
```

The patch logic itself does not need Pillow, but the script uses it to render a preview image.

## `expected one archive size field`

The script could not find the expected original `steinsgate.nes.m` size in `alldata.psb.m`.

Make sure the extracted files match the supported base game release.

## Gray Screen Or Boot Failure

Use a freshly extracted base game RomFS and rebuild the patch.

The script is intended to run from clean original files, not from previously patched `alldata.bin` or `steinsgate.nes`.

## Patch Does Not Appear In Game

Check that the generated folder is copied exactly as:

```text
SD:/atmosphere/contents/0100E9F00B882000/romfs/alldata.bin
SD:/atmosphere/contents/0100E9F00B882000/romfs/alldata.psb.m
```

Also confirm that Atmosphere's layeredfs/RomFS override support is enabled.

