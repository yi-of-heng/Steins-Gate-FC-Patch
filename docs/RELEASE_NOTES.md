# Release Notes

## v1.0.0

Initial public tool release for the English sentence-case patch.

### Changes

- Adds lowercase 8x8 glyphs for the embedded NES text font.
- Preserves uppercase sentence starts.
- Preserves standalone `I`.
- Updates the title prompt to `Press A`.
- Leaves the original English script wording and line breaks intact.

### Validation

The generated patch was checked by:

- building `output/steinsgate_sentence_case_english.zip`
- verifying the updated `alldata.psb.m` manifest points to the recompressed NES payload
- decompressing the packaged `steinsgate.nes.m` back to the patched NES ROM
- booting the patched NES ROM in jsnes and checking the title screen and opening text

