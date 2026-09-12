---
name: platform-pixel
description: >-
  Build pixel platform art from 16×16 tileset-training seeds: chunky 3×3
  nine-slice, tiny 1×3 caps, flat and wavy undersides, ink outline or
  inner-color fill, packed on one atlas with one empty-cell gutter. Delivery
  cell is 16, 32, or 64 (32/64 = nearest integer scale of the 16 seeds). Use
  when the user mentions platform-pixel, platform tileset, platform_tiny,
  tileset-training, nine-slice platforms, thin platforms, snow platform, 32px
  or 64px tiles, or asks for platform recolors, a wavy underside, a flat
  underside, or covering the black rim. Output art files only; never a level,
  TileMap, or character sprite.
---

# Platform Pixel

Seeds live in `tileset-training/` (`tiles/` + `tiles_tiny/`). Identity is **family + shape + palette**, not a prompt. Winter example: `examples/snow/`.

Output platform art files only. Chunky middles (`_02` `_05` `_08`) and tiny `_02` can extend. Chunky corners are `01` `03` `07` `09`; tiny ends are `01` `03`. Default is both undersides and both outlines on one atlas: wavy/tufted and flat/block, with ink edge and inner-color edge, and one empty output cell between platforms. Tiny also picks high or low in the cell. Seeds stay 16×16; `--cell 32` / `--cell 64` nearest-scale after QA. Do not draw characters or rooms.

## Hard locks

- Do not build levels, TileMaps, or characters.
- On failure, swap palette or shape. Do not `image_gen` a new tile.
- Middle tiles may extend. Corner tiles only go on corners.
- Several platforms may share one atlas. Seed cells stay 16×16.
- Default pack includes both a wavy underside and a flat underside.
- Pack them on one image. Separate distinct platforms with one empty output cell.
- One set keeps the outer black rim (`ink`). The other covers that rim with the inward inner color (`fill`) without deleting pixels or changing the silhouette.
- Delivery may use `--cell 16|32|64`. 32 and 64 are nearest ×2 / ×4 of the 16 seeds, not a new silhouette.
- Seeds and QA stay 16×16. Delivery cell is `--cell 16` (default), `32`, or `64`.
- `--cell 32` / `--cell 64` = nearest-neighbor integer scale after QA (`Image.NEAREST` ×2 / ×4). Same silhouette, fatter pixels. Not native 32/64 redraws.
- Delivery = sliced tiles + one atlas PNG. Not a room.
- Families: `chunky` (3×3) and `tiny` (1×3). Default `all` packs both on one sheet.
- Default `shape=both`: flat underside (`block`) and wavy underside (`tufted`). No third outline.
- Default `outline=both`: `ink` keeps the black rim; `fill` paints that rim with the inward inner color (`hi` on top, `shadow` on the bottom).
- Atlas gutter is one empty **output** cell (16 / 32 / 64 px) between distinct platforms.
- Recolor with `scripts/build.py`. Do not `generate2dsprite` / `image_gen` / `GenerateImage`.
- Nearest only. No Lanczos. No bilinear. No bbox-fit.

Grammar: [grammar.md](grammar.md). Palettes: [palettes.json](palettes.json).

## Commands

Run from this repo root. Defaults: `--shape both`, `--outline both`, `--family all`, `--cell 16`, one-cell gutters.

```text
python .cursor/skills/platform-pixel/scripts/build.py --palette snow --out examples/snow
python .cursor/skills/platform-pixel/scripts/build.py --palette snow --cell 32 --out examples/snow-32
python .cursor/skills/platform-pixel/scripts/build.py --palette snow --cell 64 --out examples/snow-64
python .cursor/skills/platform-pixel/scripts/build.py --shape block --outline ink --palette clay --family chunky --out examples/clay
python .cursor/skills/platform-pixel/scripts/build.py --shape tufted --outline fill --palette grass --out examples/grass
python .cursor/skills/platform-pixel/scripts/build.py --palette custom --hi #AABBCC --mid #8899AA --shadow #445566 --ink #110A03 --out examples/custom
```

`--name` defaults to the output directory name. Custom palettes need `ink` `hi` `mid` `shadow`; add `--deep` for `tufted`. `--anchor high|low|both` applies to tiny only (default `both`). `--outline ink|fill|both` (default `both`). `--cell 16|32|64` (default `16`).

Stop after `build`. Do not write engine scenes or slice a full map.

## Outputs to open

- `{out}/{name}.png` — atlas; default 15×7 cells (240×112 at `--cell 16`, 480×224 at `32`, 960×448 at `64`) with one-cell gutters
- `{out}/tiles/{name}_block_ink_01.png` … `{name}_tufted_fill_01.png` …
- `{out}/tiles_tiny/{name}_block_ink_high_01.png` … and matching fill / low strips
- `{out}/{name}.json` — shape, outline, palette, atlas slots

## Routing

| Need | Do |
|---|---|
| Winter / snow | `build.py --palette snow --out examples/snow` (see [examples/snow](../../../examples/snow)) |
| 32px / 64px tiles | `--cell 32` or `--cell 64` (nearest from 16 seeds; own `--out` folder) |
| New colors | `--palette custom` plus hex roles |
| Only thick 3×3 | `--family chunky` |
| Only thin 1×3 | `--family tiny` |
| Several platforms on one PNG | default `--shape both --family all --outline both`; one-cell gutter |
| Wavy underside | `--shape tufted` |
| Flat underside | `--shape block` |
| Keep the black rim | `--outline ink` |
| Cover the black rim with inner color | `--outline fill` |
| New third silhouette | refuse |
| A playable room / character | out of scope |

## Examples

### Snow (checked-in)

[`examples/snow/snow.png`](../../../examples/snow/snow.png) is the winter kit: icy `hi/mid/shadow`, chunky + tiny, flat + wavy, ink + fill.

```text
python .cursor/skills/platform-pixel/scripts/build.py --palette snow --out examples/snow
```

Open `examples/snow/snow.png`. Left pair keeps the black rim; right pair covers it with inner color. Do not regenerate tiles unless the user asked to rebuild.

For 32px or 64px delivery (nearest ×2 / ×4 of the same seeds), use a separate `--out` folder:

```text
python .cursor/skills/platform-pixel/scripts/build.py --palette snow --cell 32 --out examples/snow-32
```

### Recolor

```text
python .cursor/skills/platform-pixel/scripts/build.py --palette stone --out examples/stone
```

Same layout as snow. If the color is wrong, change palette hexes and rebuild.
