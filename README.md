# platform-pixel

An agent skill for [Cursor](https://cursor.com) and other tools that load `SKILL.md`. It remaps 16×16 platformer tiles from a JSON palette. Identity is **shape + palette**, not a prompt. It writes sliced tiles plus one atlas. It does not build levels or characters.

## Example: snow

[`examples/snow/`](examples/snow/) is a winter kit (icy highlight / packed snow / cold shadow). Default build packs thick 3×3 and thin 1×3 platforms, flat and wavy undersides, black rims and inner-color rims, with a 16×16 empty cell between groups.

![Snow platform atlas](examples/snow/snow.png)

Rebuild it:

```bash
python .cursor/skills/platform-pixel/scripts/build.py --palette snow --out examples/snow
```

## Install

```bash
git clone https://github.com/francsun/platform-pixel.git
cd platform-pixel
pip install -r requirements.txt
```

Copy the skill into the agent folder your tool reads:

```text
your-game/.cursor/skills/platform-pixel/   # Cursor
your-game/.codex/skills/platform-pixel/    # Codex
```

Keep this clone on disk. The script looks for `tileset-training/` here (or `PLATFORM_PIXEL_ROOT`). Then ask the agent for a snow platform or a new palette.

## What it outputs

| File | |
|---|---|
| `{name}.png` | Atlas on a 16×16 grid (default 240×112) |
| `tiles/*.png` | Chunky 3×3 slices |
| `tiles_tiny/*.png` | Tiny 1×3 slices |
| `{name}.json` | Palette, layout, slot roles |

Defaults: `--shape both` (flat + wavy), `--outline both` (ink rim + fill rim), `--family all` (chunky + tiny).

## Seeds

Training art lives in [`tileset-training/`](tileset-training/). Do not invent a third silhouette; recolor `block` / `tufted` only. Grammar: [`.cursor/skills/platform-pixel/grammar.md`](.cursor/skills/platform-pixel/grammar.md).
