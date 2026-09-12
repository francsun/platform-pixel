# 16×16 platform grammar

Two families. Same ink / hi / mid / shadow (/ deep) remap. Seeds in `tileset-training/`.

## Chunky (3×3)

Tiles: `tiles/platform0N_01` … `_09`. Assemble 48×48.

```text
01 corner-nw    02 edge-n     03 corner-ne
04 edge-w       05 center     06 edge-e
07 corner-sw    08 edge-s     09 corner-se
```

Corners only: `01` `03` `07` `09`. Middles extend: `02|02`, `05|05`, `08|08`, `04/04`, `06/06`.

| shape | seed | edge |
|---|---|---|
| `block` | `platform01_*` | 2px rounded corners, solid underside |
| `tufted` | `platform04_*` | underside tufts + `deep` |

Ink rails: `02` top, `04` left, `06` right; `08` bottom when `block`. `--outline fill` replaces those ink pixels with the inward inner color and leaves alpha unchanged.

## Tiny (1×3)

Tiles: `tiles_tiny/platform_tiny_0N_01` … `_03`. Assemble 48×16. Same 16×16 cell; body is a ~9px-tall strip inside the cell.

```text
01 cap-w    02 span (repeat to lengthen)    03 cap-e
```

Only `01` and `03` are ends. `02|02` grows the platform.

| shape | anchor | seed | body in the cell |
|---|---|---|---|
| `block` | `low` | `platform_tiny_01_*` | y=7..15, walk line at y=7 |
| `block` | `high` | `platform_tiny_02_*` | y=0..8, walk line at y=0 |
| `tufted` | `low` | `platform_tiny_03_*` | lower half, hanging tufts |
| `tufted` | `high` | `platform_tiny_04_*` | upper half, hanging tufts |

Tiny `01`/`02` share the clay palette; `03`/`04` share grass. Recolor with the same role hexes as chunky.

Do not require a full 16px side ink column on caps (rounded ends). Require the walk-side ink rail on `_02`.

## Atlas (one resource PNG)

All selected families go on **one** image. Grid is 16×16. Not a level.

Default pack (`family=all`, `shape=both`, `outline=both`): **flat and wavy undersides**, each with **black rim and inner-color rim**. One empty 16×16 cell between distinct platforms.

```text
row 0-2  chunky block ink | gap | chunky tufted ink | gap | chunky block fill | gap | chunky tufted fill
row 3    empty
row 4    tiny high ink block/tufted | gap | tiny high fill block/tufted
row 5    empty
row 6    tiny low  ink block/tufted | gap | tiny low  fill block/tufted
```

Sheet is 15×7 cells = 240×112. Gutters stay fully transparent. `fill` covers the outer black edge with the inner band (`hi` on the walk line, `shadow` on the underside).

## Cell

- 16×16 PNG, RGBA, nearest, no AA
- Typical 4 opaque colors; `tufted` may add `deep`
