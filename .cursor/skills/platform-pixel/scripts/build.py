#!/usr/bin/env python3
"""16x16 platform tiles: remap chunky 3x3 and tiny 1x3 seeds onto one atlas.

Seeds and QA stay 16x16. --cell 32/64 is nearest integer scale only.
Never Lanczos. Never emit a level.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path

from PIL import Image

CELL = 16
ALLOWED_CELLS = (16, 32, 64)
GUTTER_CELLS = 1  # one empty output cell between distinct platforms
CHUNKY_SLOTS = tuple(range(1, 10))
TINY_SLOTS = tuple(range(1, 4))
OPAQUE_MIN = 16
INK_HINT = (17, 10, 3)

# family, shape [, anchor] -> (subdir, file prefix, slot count)
CHUNKY_SEEDS = {
    "block": ("tiles", "platform01"),
    "tufted": ("tiles", "platform04"),
}
TINY_SEEDS = {
    ("block", "low"): ("tiles_tiny", "platform_tiny_01"),
    ("block", "high"): ("tiles_tiny", "platform_tiny_02"),
    ("tufted", "low"): ("tiles_tiny", "platform_tiny_03"),
    ("tufted", "high"): ("tiles_tiny", "platform_tiny_04"),
}

HERE = Path(__file__).resolve().parent
SKILL_DIR = HERE.parent


def parse_hex(value: str) -> tuple[int, int, int]:
    h = value.strip().lstrip("#")
    if len(h) != 6:
        raise SystemExit(f"expected #RRGGBB, got {value!r}")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def hex_rgb(rgb: tuple[int, int, int]) -> str:
    return "#%02X%02X%02X" % rgb


def nn_integer(im: Image.Image, scale: int) -> Image.Image:
    if scale < 1 or int(scale) != scale:
        raise SystemExit("only positive integer nearest-neighbor scale is allowed")
    if scale == 1:
        return im.copy()
    return im.resize((im.width * scale, im.height * scale), Image.NEAREST)


def scale_tiles(tiles: dict[int, Image.Image], scale: int) -> dict[int, Image.Image]:
    return {slot: nn_integer(im, scale) for slot, im in tiles.items()}


def luma(rgb: tuple[int, int, int]) -> float:
    r, g, b = rgb
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def rel(path: Path, root: Path) -> str:
    path = path.resolve()
    try:
        return path.relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def find_repo(explicit: Path | None) -> Path:
    if explicit:
        return explicit.resolve()
    env = os.environ.get("PLATFORM_PIXEL_ROOT")
    starts = [Path.cwd(), SKILL_DIR, Path.cwd().parent / "platform-pixel"]
    if env:
        starts.insert(0, Path(env))
    for start in starts:
        for parent in [start, *start.parents]:
            if (parent / "tileset-training" / "tiles").is_dir():
                return parent.resolve()
    raise SystemExit("cannot find tileset-training/tiles; pass --repo or set PLATFORM_PIXEL_ROOT")


def load_named_palettes() -> dict:
    path = SKILL_DIR / "palettes.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    return data["palettes"]


def opaque_colors(im: Image.Image) -> dict[tuple[int, int, int], int]:
    counts: dict[tuple[int, int, int], int] = {}
    for r, g, b, a in im.convert("RGBA").getdata():
        if a < OPAQUE_MIN:
            continue
        rgb = (r, g, b)
        counts[rgb] = counts.get(rgb, 0) + 1
    return counts


def assign_roles(counts: dict[tuple[int, int, int], int]) -> dict[str, tuple[int, int, int]]:
    if not counts:
        raise SystemExit("seed has no opaque pixels")
    colors = list(counts)
    ink = min(
        colors,
        key=lambda c: (
            abs(c[0] - INK_HINT[0]) + abs(c[1] - INK_HINT[1]) + abs(c[2] - INK_HINT[2]),
            luma(c),
        ),
    )
    rest = [c for c in colors if c != ink]
    if not rest:
        raise SystemExit("seed has only ink")
    mid = max(rest, key=lambda c: counts[c])
    rest = [c for c in rest if c != mid]
    roles = {"ink": ink, "mid": mid}
    if not rest:
        return roles
    hi = max(rest, key=luma)
    rest = [c for c in rest if c != hi]
    roles["hi"] = hi
    if not rest:
        return roles
    rest_sorted = sorted(rest, key=luma)
    if len(rest_sorted) == 1:
        roles["shadow"] = rest_sorted[0]
        return roles
    roles["deep"] = rest_sorted[0]
    roles["shadow"] = rest_sorted[-1]
    return roles


def target_roles(args: argparse.Namespace, named: dict) -> dict[str, tuple[int, int, int]]:
    if args.palette != "custom":
        if args.palette not in named:
            raise SystemExit(f"unknown palette {args.palette!r}; choose {sorted(named)} or custom")
        src = named[args.palette]
        return {k: parse_hex(v) for k, v in src.items()}
    missing = [r for r in ("ink", "hi", "mid", "shadow") if not getattr(args, r)]
    if missing:
        raise SystemExit(f"custom palette needs --{' --'.join(missing)}")
    out = {
        "ink": parse_hex(args.ink),
        "hi": parse_hex(args.hi),
        "mid": parse_hex(args.mid),
        "shadow": parse_hex(args.shadow),
    }
    if args.deep:
        out["deep"] = parse_hex(args.deep)
    return out


def remap_image(
    im: Image.Image, mapping: dict[tuple[int, int, int], tuple[int, int, int]]
) -> Image.Image:
    src = im.convert("RGBA")
    pixels: list[tuple[int, int, int, int]] = []
    for r, g, b, a in src.getdata():
        if a < OPAQUE_MIN:
            pixels.append((0, 0, 0, 0))
            continue
        mapped = mapping.get((r, g, b))
        if mapped is None:
            nearest = min(
                mapping,
                key=lambda c: (r - c[0]) ** 2 + (g - c[1]) ** 2 + (b - c[2]) ** 2,
            )
            mapped = mapping[nearest]
        pr, pg, pb = mapped
        pixels.append((pr, pg, pb, 255))
    out = Image.new("RGBA", src.size)
    out.putdata(pixels)
    return out


def load_seed_tiles(tiles_dir: Path, prefix: str, slots: tuple[int, ...]) -> dict[int, Image.Image]:
    tiles: dict[int, Image.Image] = {}
    for slot in slots:
        path = tiles_dir / f"{prefix}_{slot:02d}.png"
        if not path.is_file():
            raise SystemExit(f"missing seed tile {path}")
        im = Image.open(path).convert("RGBA")
        if im.size != (CELL, CELL):
            raise SystemExit(f"{path.name} is {im.size}, want {CELL}x{CELL}")
        tiles[slot] = im
    return tiles


def seed_role_map(tiles: dict[int, Image.Image]) -> dict[str, tuple[int, int, int]]:
    merged: dict[tuple[int, int, int], int] = {}
    for im in tiles.values():
        for rgb, n in opaque_colors(im).items():
            merged[rgb] = merged.get(rgb, 0) + n
    return assign_roles(merged)


def build_mapping(
    seed_roles: dict[str, tuple[int, int, int]],
    dest_roles: dict[str, tuple[int, int, int]],
) -> dict[tuple[int, int, int], tuple[int, int, int]]:
    mapping: dict[tuple[int, int, int], tuple[int, int, int]] = {}
    fallback = dest_roles.get("shadow") or dest_roles["mid"]
    for role, rgb in seed_roles.items():
        mapping[rgb] = dest_roles.get(role, dest_roles.get("shadow", fallback))
    return mapping


def is_ink(px: tuple[int, int, int, int], ink: tuple[int, int, int]) -> bool:
    r, g, b, a = px
    if a < OPAQUE_MIN:
        return False
    return (r, g, b) == ink


def count_ink(im: Image.Image, ink: tuple[int, int, int]) -> int:
    return sum(1 for p in im.convert("RGBA").getdata() if is_ink(p, ink))


def cover_ink(im: Image.Image, ink: tuple[int, int, int]) -> Image.Image:
    """Replace the outer ink ring with the adjacent inner fill color. Alpha stays."""
    src = im.convert("RGBA")
    w, h = src.size
    pix = [list(p) for p in src.getdata()]

    def at(x: int, y: int) -> list[int]:
        return pix[y * w + x]

    def is_ink_px(p: list[int]) -> bool:
        return p[3] >= OPAQUE_MIN and (p[0], p[1], p[2]) == ink

    def is_fill_px(p: list[int]) -> bool:
        return p[3] >= OPAQUE_MIN and (p[0], p[1], p[2]) != ink

    changed = True
    while changed:
        changed = False
        updates: list[tuple[int, int, tuple[int, int, int]]] = []
        for y in range(h):
            for x in range(w):
                if not is_ink_px(at(x, y)):
                    continue
                neighbors: list[tuple[int, int, int]] = []
                for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < w and 0 <= ny < h and is_fill_px(at(nx, ny)):
                        neighbors.append((at(nx, ny)[0], at(nx, ny)[1], at(nx, ny)[2]))
                if not neighbors:
                    continue
                fill = Counter(neighbors).most_common(1)[0][0]
                updates.append((x, y, fill))
        for x, y, fill in updates:
            pix[y * w + x] = [fill[0], fill[1], fill[2], 255]
            changed = True

    fills = [
        (x, y, (at(x, y)[0], at(x, y)[1], at(x, y)[2]))
        for y in range(h)
        for x in range(w)
        if is_fill_px(at(x, y))
    ]
    for y in range(h):
        for x in range(w):
            if not is_ink_px(at(x, y)) or not fills:
                continue
            _nx, _ny, col = min(fills, key=lambda t: (t[0] - x) ** 2 + (t[1] - y) ** 2)
            pix[y * w + x] = [col[0], col[1], col[2], 255]

    out = Image.new("RGBA", (w, h))
    out.putdata([tuple(p) for p in pix])
    return out


def apply_outline(
    tiles: dict[int, Image.Image], outline: str, ink: tuple[int, int, int]
) -> dict[int, Image.Image]:
    if outline == "ink":
        return {slot: im.copy() for slot, im in tiles.items()}
    if outline == "fill":
        return {slot: cover_ink(im, ink) for slot, im in tiles.items()}
    raise SystemExit(f"unknown outline {outline!r}")


def first_opaque_row(im: Image.Image) -> int | None:
    for y in range(im.height):
        for x in range(im.width):
            if im.getpixel((x, y))[3] >= OPAQUE_MIN:
                return y
    return None


def qa_chunky(
    tiles: dict[int, Image.Image],
    shape: str,
    ink: tuple[int, int, int],
    outline: str,
) -> list[str]:
    fails: list[str] = []
    for slot, im in tiles.items():
        if im.size != (CELL, CELL):
            fails.append(f"chunky _{slot:02d} size {im.size}")
        if outline == "fill" and count_ink(im, ink) > 0:
            fails.append(f"chunky _{slot:02d} still has ink after fill")
    if outline == "ink":
        top = list(tiles[2].getdata())[:CELL]
        if sum(is_ink(p, ink) for p in top) != CELL:
            fails.append("chunky _02 top ink rail incomplete")
        left = [tiles[4].getpixel((0, y)) for y in range(CELL)]
        if sum(is_ink(p, ink) for p in left) != CELL:
            fails.append("chunky _04 left ink rail incomplete")
        right = [tiles[6].getpixel((CELL - 1, y)) for y in range(CELL)]
        if sum(is_ink(p, ink) for p in right) != CELL:
            fails.append("chunky _06 right ink rail incomplete")
        if shape == "block":
            bot = [tiles[8].getpixel((x, CELL - 1)) for x in range(CELL)]
            if sum(is_ink(p, ink) for p in bot) != CELL:
                fails.append("chunky _08 bottom ink rail incomplete")
    for slot in (1, 3, 7, 9):
        alpha = sum(1 for *_, a in tiles[slot].getdata() if a < OPAQUE_MIN)
        if alpha < 1:
            fails.append(f"chunky _{slot:02d} corner has no transparent pixels")
    return fails


def qa_tiny(
    tiles: dict[int, Image.Image],
    shape: str,
    anchor: str,
    ink: tuple[int, int, int],
    outline: str,
) -> list[str]:
    fails: list[str] = []
    for slot, im in tiles.items():
        if im.size != (CELL, CELL):
            fails.append(f"tiny-{anchor} _{slot:02d} size {im.size}")
        if outline == "fill" and count_ink(im, ink) > 0:
            fails.append(f"tiny-{anchor} _{slot:02d} still has ink after fill")
    mid = tiles[2]
    walk = 0 if anchor == "high" else first_opaque_row(mid)
    if walk is None:
        fails.append(f"tiny-{anchor} _02 is empty")
        return fails
    row = [mid.getpixel((x, walk)) for x in range(CELL)]
    if outline == "ink":
        if sum(is_ink(p, ink) for p in row) != CELL:
            fails.append(f"tiny-{anchor} _02 walk ink rail incomplete (y={walk})")
        if shape == "block":
            bot_y = CELL - 1 if anchor == "low" else 8
            bot = [mid.getpixel((x, bot_y)) for x in range(CELL)]
            if sum(is_ink(p, ink) for p in bot) != CELL:
                fails.append(f"tiny-{anchor} _02 underside ink rail incomplete (y={bot_y})")
    else:
        if sum(1 for p in row if p[3] >= OPAQUE_MIN) != CELL:
            fails.append(f"tiny-{anchor} _02 walk row is not solid after fill (y={walk})")
    for slot in (1, 3):
        alpha = sum(1 for *_, a in tiles[slot].getdata() if a < OPAQUE_MIN)
        if alpha < 1:
            fails.append(f"tiny-{anchor} _{slot:02d} cap has no transparent pixels")
    return fails


def remap_group(
    tiles: dict[int, Image.Image], dest: dict[str, tuple[int, int, int]]
) -> dict[int, Image.Image]:
    mapping = build_mapping(seed_role_map(tiles), dest)
    return {slot: remap_image(im, mapping) for slot, im in tiles.items()}


def paste_group(
    atlas: Image.Image,
    tiles: dict[int, Image.Image],
    col0: int,
    row0: int,
    cols: int,
    cell: int,
) -> None:
    for slot, im in tiles.items():
        if im.size != (cell, cell):
            raise SystemExit(f"tile _{slot:02d} is {im.size}, want {cell}x{cell}")
        idx = slot - 1
        x = (col0 + idx % cols) * cell
        y = (row0 + idx // cols) * cell
        atlas.paste(im, (x, y))


def pack_bands(bands: list[list[dict]]) -> list[dict]:
    """Place platform groups with one empty output cell between them."""
    placed: list[dict] = []
    row = 0
    for band in bands:
        if not band:
            continue
        if placed:
            row += GUTTER_CELLS
        col = 0
        band_h = max(g["rows"] for g in band)
        for i, g in enumerate(band):
            if i:
                col += GUTTER_CELLS
            g["col"] = col
            g["row"] = row
            col += g["cols"]
            placed.append(g)
        row += band_h
    return placed


def selected_shapes(value: str) -> list[str]:
    if value == "both":
        return ["block", "tufted"]
    if value in ("block", "tufted"):
        return [value]
    raise SystemExit("--shape must be block, tufted, or both")


def selected_families(value: str) -> list[str]:
    if value == "all":
        return ["chunky", "tiny"]
    if value in ("chunky", "tiny"):
        return [value]
    raise SystemExit("--family must be chunky, tiny, or all")


def selected_outlines(value: str) -> list[str]:
    if value == "both":
        return ["ink", "fill"]
    if value in ("ink", "fill"):
        return [value]
    raise SystemExit("--outline must be ink, fill, or both")


def selected_anchors(value: str) -> list[str]:
    if value == "both":
        return ["high", "low"]
    if value in ("high", "low"):
        return [value]
    raise SystemExit("--anchor must be high, low, or both")


def cmd_build(args: argparse.Namespace) -> int:
    repo = find_repo(args.repo)
    training = repo / "tileset-training"
    dest = target_roles(args, load_named_palettes())
    shapes = selected_shapes(args.shape)
    families = selected_families(args.family)
    anchors = selected_anchors(args.anchor)
    outlines = selected_outlines(args.outline)
    out_cell = args.cell
    if out_cell not in ALLOWED_CELLS:
        raise SystemExit("--cell must be 16, 32, or 64")
    scale = out_cell // CELL

    bands: list[list[dict]] = []
    if "chunky" in families:
        band: list[dict] = []
        for outline in outlines:
            for shape in shapes:
                sub, prefix = CHUNKY_SEEDS[shape]
                seeds = load_seed_tiles(training / sub, prefix, CHUNKY_SLOTS)
                tiles = apply_outline(remap_group(seeds, dest), outline, dest["ink"])
                fails = qa_chunky(tiles, shape, dest["ink"], outline)
                if fails:
                    raise SystemExit("QA failed:\n  " + "\n  ".join(fails))
                band.append(
                    {
                        "id": f"chunky-{shape}-{outline}",
                        "family": "chunky",
                        "shape": shape,
                        "outline": outline,
                        "tiles": scale_tiles(tiles, scale),
                        "cols": 3,
                        "rows": 3,
                        "seed": prefix,
                    }
                )
        bands.append(band)
    if "tiny" in families:
        for anchor in anchors:
            band = []
            for outline in outlines:
                for shape in shapes:
                    sub, prefix = TINY_SEEDS[(shape, anchor)]
                    seeds = load_seed_tiles(training / sub, prefix, TINY_SLOTS)
                    tiles = apply_outline(remap_group(seeds, dest), outline, dest["ink"])
                    fails = qa_tiny(tiles, shape, anchor, dest["ink"], outline)
                    if fails:
                        raise SystemExit("QA failed:\n  " + "\n  ".join(fails))
                    band.append(
                        {
                            "id": f"tiny-{shape}-{anchor}-{outline}",
                            "family": "tiny",
                            "shape": shape,
                            "anchor": anchor,
                            "outline": outline,
                            "tiles": scale_tiles(tiles, scale),
                            "cols": 3,
                            "rows": 1,
                            "seed": prefix,
                        }
                    )
            bands.append(band)

    groups = pack_bands(bands)
    if not groups:
        raise SystemExit("nothing to build")

    max_col = max(g["col"] + g["cols"] for g in groups)
    max_row = max(g["row"] + g["rows"] for g in groups)
    atlas = Image.new("RGBA", (max_col * out_cell, max_row * out_cell), (0, 0, 0, 0))
    for g in groups:
        paste_group(atlas, g["tiles"], g["col"], g["row"], g["cols"], out_cell)

    out_dir = args.out.resolve()
    name = args.name or out_dir.name
    out_dir.mkdir(parents=True, exist_ok=True)
    atlas_path = out_dir / f"{name}.png"
    atlas.save(atlas_path)

    outputs = {"atlas": rel(atlas_path, repo)}
    layout = []
    for g in groups:
        bits = [name]
        if len(shapes) > 1:
            bits.append(g["shape"])
        if len(outlines) > 1:
            bits.append(g["outline"])
        if g["family"] == "tiny":
            bits.append(g["anchor"])
        prefix = "_".join(bits)
        if g["family"] == "chunky":
            tile_dir = out_dir / "tiles"
        else:
            tile_dir = out_dir / "tiles_tiny"
        tile_dir.mkdir(parents=True, exist_ok=True)
        for slot, im in g["tiles"].items():
            path = tile_dir / f"{prefix}_{slot:02d}.png"
            im.save(path)
            outputs[f"{g['id']}_{slot:02d}"] = rel(path, repo)
        layout.append(
            {
                "id": g["id"],
                "family": g["family"],
                "shape": g["shape"],
                "outline": g["outline"],
                "anchor": g.get("anchor"),
                "seed": g["seed"],
                "cell": [g["col"], g["row"], g["cols"], g["rows"]],
            }
        )

    manifest = {
        "name": name,
        "cell": out_cell,
        "source_cell": CELL,
        "scale": scale,
        "resample": "nearest",
        "shape": args.shape,
        "family": args.family,
        "anchor": args.anchor,
        "outline": args.outline,
        "palette": args.palette,
        "colors": {role: hex_rgb(rgb) for role, rgb in dest.items()},
        "atlas": {
            "width": atlas.width,
            "height": atlas.height,
            "gutter_cells": GUTTER_CELLS,
            "gutter_px": GUTTER_CELLS * out_cell,
            "layout": layout,
        },
        "extend": {
            "chunky_corners_only": ["01", "03", "07", "09"],
            "chunky_horizontal": ["02", "05", "08"],
            "chunky_vertical": ["04", "05", "06"],
            "tiny_caps_only": ["01", "03"],
            "tiny_horizontal": ["02"],
        },
        "outputs": outputs,
    }
    man_path = out_dir / f"{name}.json"
    man_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(atlas_path)
    print(man_path)
    for key in sorted(k for k in outputs if k != "atlas"):
        print(outputs[key])
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Remap 16x16 platform seeds into an atlas (optional nearest 32/64)"
    )
    p.add_argument("--shape", default="both", help="block|tufted|both (default both: flat + wavy underside)")
    p.add_argument("--palette", required=True, help="named palette or custom")
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--name", help="file prefix (default: output directory name)")
    p.add_argument("--family", default="all", help="chunky|tiny|all (default all)")
    p.add_argument("--anchor", default="both", help="high|low|both for tiny (default both)")
    p.add_argument("--outline", default="both", help="ink|fill|both (default both: black edge + inner-color edge)")
    p.add_argument(
        "--cell",
        type=int,
        default=16,
        choices=list(ALLOWED_CELLS),
        help="output cell 16, 32, or 64 (32/64 = nearest x2/x4 of 16 seeds)",
    )
    p.add_argument("--repo", type=Path)
    p.add_argument("--ink")
    p.add_argument("--hi")
    p.add_argument("--mid")
    p.add_argument("--shadow")
    p.add_argument("--deep")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return cmd_build(args)


if __name__ == "__main__":
    sys.exit(main())
