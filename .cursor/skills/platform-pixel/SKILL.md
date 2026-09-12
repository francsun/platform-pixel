---
name: platform-pixel
description: >-
  Build 16×16 pixel platform art from tileset-training seeds: chunky 3×3
  nine-slice, tiny 1×3 caps, flat and wavy undersides, ink outline or
  inner-color fill, packed on one atlas with 16×16 empty gutters. Use when the
  user mentions platform-pixel, platform tileset, platform_tiny, 平台砖, 九宫格,
  细平台, tileset-training, or asks for platform recolors / 边缘微变 / 平整下边缘
  / 去掉黑边 / snow platform. Output art files only; never a level, TileMap,
  or character sprite.
---

# Platform Pixel

Seeds live in `tileset-training/` (`tiles/` + `tiles_tiny/`). Identity is **family + shape + palette**, not a prompt. Winter example: `examples/snow/`.

Output platform art files only. Chunky middles (`_02` `_05` `_08`) and tiny `_02` can extend. Chunky corners are `01` `03` `07` `09`; tiny ends are `01` `03`. Default is both undersides and both outlines on one atlas: wavy/tufted and flat/block, with ink edge and inner-color edge, and a 16×16 empty cell between platforms. Tiny also picks high or low in the cell. Do not draw characters or rooms.

## 写死

- 不搭关卡、不铺 TileMap、不画角色
- 失败回换色或换外形，不 image_gen 重画砖
- 中间砖可延伸；角砖只放角
- 多平台可以在一张图上，格子仍是 16×16
- 除了生成下面边缘有波浪形的 platforms 之外，也生成下边缘为平整的 platforms
- 生成在同一张图片上，并且不同的 platforms 之间用 16×16 的空白区域隔开
- 一套保留最外侧黑色边缘，另一套用里层颜色覆盖黑边（不删像素、不改剪影）

Also locked:

- Cell 16×16. Delivery = sliced tiles + one atlas PNG. Not a room.
- Families: `chunky` (3×3) and `tiny` (1×3). Default `all` packs both on one sheet.
- Default `shape=both`: flat underside (`block`) and wavy underside (`tufted`). No third outline.
- Default `outline=both`: `ink` keeps the black rim; `fill` paints that rim with the inward inner color (`hi` on top, `shadow` on the bottom).
- Atlas gutter is one empty 16×16 cell between distinct platforms (horizontal and vertical).
- Recolor with `scripts/build.py`. Do not `generate2dsprite` / `image_gen` / `GenerateImage`.
- Nearest only. No Lanczos. No bbox-fit.

Grammar: [grammar.md](grammar.md). Palettes: [palettes.json](palettes.json).

## Commands

Run from this repo root. Defaults: `--shape both`, `--outline both`, `--family all`, 16×16 gutters.

```text
python .cursor/skills/platform-pixel/scripts/build.py --palette snow --out examples/snow
python .cursor/skills/platform-pixel/scripts/build.py --shape block --outline ink --palette clay --family chunky --out examples/clay
python .cursor/skills/platform-pixel/scripts/build.py --shape tufted --outline fill --palette grass --out examples/grass
python .cursor/skills/platform-pixel/scripts/build.py --palette custom --hi #AABBCC --mid #8899AA --shadow #445566 --ink #110A03 --out examples/custom
```

`--name` defaults to the output directory name. Custom palettes need `ink` `hi` `mid` `shadow`; add `--deep` for `tufted`. `--anchor high|low|both` applies to tiny only (default `both`). `--outline ink|fill|both` (default `both`).

Stop after `build`. Do not write engine scenes or slice a full map.

## Outputs to open

- `{out}/{name}.png` — atlas, 16×16 cells; default 15×7 (240×112) with 16×16 gutters
- `{out}/tiles/{name}_block_ink_01.png` … `{name}_tufted_fill_01.png` …
- `{out}/tiles_tiny/{name}_block_ink_high_01.png` … and matching fill / low strips
- `{out}/{name}.json` — shape, outline, palette, atlas slots

## Routing

| Need | Do |
|---|---|
| Winter / snow | `build.py --palette snow --out examples/snow` (see [examples/snow](../../../examples/snow)) |
| New colors | `--palette custom` plus hex roles |
| Only thick 3×3 | `--family chunky` |
| Only thin 1×3 | `--family tiny` |
| Several platforms on one PNG | default `--shape both --family all --outline both`; 16×16 gutter |
| 下边缘波浪 | `--shape tufted` |
| 下边缘平整 | `--shape block` |
| 保留黑边 | `--outline ink` |
| 用里层色盖住黑边 | `--outline fill` |
| New third silhouette | refuse |
| A playable room / 人物 | out of scope |

## Examples

### Snow (checked-in)

[`examples/snow/snow.png`](../../../examples/snow/snow.png) is the winter kit: icy `hi/mid/shadow`, chunky + tiny, flat + wavy, ink + fill.

```text
python .cursor/skills/platform-pixel/scripts/build.py --palette snow --out examples/snow
```

Open `examples/snow/snow.png`. Left pair keeps the black rim; right pair covers it with inner color. Do not regenerate tiles unless the user asked to rebuild.

### 换配色

```text
python .cursor/skills/platform-pixel/scripts/build.py --palette stone --out examples/stone
```

Same layout as snow. If the color is wrong, change palette hexes and rebuild.
