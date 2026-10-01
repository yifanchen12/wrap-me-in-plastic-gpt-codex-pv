"""Assemble generated key poses into the existing RGBA and glyph dance caches."""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
from functools import lru_cache
import json
import math
import os
from pathlib import Path
import shutil
import subprocess

import numpy as np
from PIL import Image, ImageDraw

import placeholder_h3 as old
from wrap_me_preview import FFMPEG, font

ATLAS = Path(os.environ.get("GPT_SPRITE_ATLAS", old.ROOT / "assets" / "gpt-dance-atlas.png"))
WORK = old.V2 / "cache" / "gpt_sprite_dance"
LOOP = 88
SEQUENCES = {
    "dance": list(range(12)),
    "turn": [0, 5, 6, 7, 8, 0],
    "open": [0, 1, 2, 8, 2, 0],
    "fold": [2, 4, 10, 0],
    "reach": [0, 8, 9, 9, 10],
    "release": [9, 10, 10, 10],
    "quiet": [0, 10, 10, 10],
}
FAMILIES = {"turn": "turn", "open": "open", "present": "open", "sweep": "turn",
            "fold": "fold", "cup": "fold", "tense": "fold", "reach": "reach",
            "release": "release", "settle": "quiet", "inspect": "quiet", "bow": "quiet",
            "W10": "release"}


@lru_cache(maxsize=1)
def sprites():
    atlas = Image.open(ATLAS).convert("RGBA")
    if atlas.getchannel("A").getextrema()[0] >= 100:
        raise ValueError("The sprite atlas must have a genuine transparent background")
    cells, bounds = [], []
    for i in range(12):
        col, row = i % 4, i // 4
        tile = atlas.crop((round(col * atlas.width / 4), round(row * atlas.height / 3),
                           round((col + 1) * atlas.width / 4), round((row + 1) * atlas.height / 3)))
        box = tile.getchannel("A").point(lambda a: 255 if a >= 80 else 0).getbbox()
        if not box or box[3] - box[1] < tile.height * .45:
            raise ValueError(f"Sprite cell {i + 1} is empty or cropped incorrectly")
        cells.append(tile)
        bounds.append(box)
    scale = old.HEIGHT / max(b[3] - b[1] for b in bounds)
    frames = []
    for tile, box in zip(cells, bounds):
        cut = tile.crop(box)
        cut = cut.resize((round(cut.width * scale), round(cut.height * scale)), Image.Resampling.LANCZOS)
        canvas = Image.new("RGBA", old.SIZE)
        xy = (round(old.AXIS_X + (box[0] - tile.width / 2) * scale), old.FOOT_Y - cut.height)
        canvas.alpha_composite(cut, xy)
        frames.append(canvas)
    return frames


def motion(image, phase, quiet):
    strength = .28 if quiet else 1.0
    sway = strength * 7 * math.sin(phase * math.tau)
    dip = strength * .018 * (max(0, math.cos(phase * 4 * math.tau))) ** 2
    width, height = old.SIZE

    def source(x, y):
        yy = old.FOOT_Y - (old.FOOT_Y - y) / (1 - dip)
        upper = max(0, (old.FOOT_Y - yy) / old.HEIGHT)
        cloth = max(0, min(1, (yy - 240) / 200)) * min(1, abs(x - old.AXIS_X) / 90)
        wave = strength * cloth * 8 * math.sin(phase * math.tau - yy * .025)
        return x - sway * upper ** 1.4 - wave, yy

    mesh = []
    for y in range(0, height, 6):
        end = min(height, y + 6)
        mesh.append(((0, y, width, end), (*source(0, y), *source(0, end),
                                        *source(width, end), *source(width, y))))
    return image.transform(old.SIZE, Image.Transform.MESH, mesh, Image.Resampling.BICUBIC)


def pose(family, frame):
    phase = frame / (LOOP - 1)
    sequence = SEQUENCES[family]
    at = phase * (len(sequence) - 1)
    before = min(len(sequence) - 2, int(at))
    u = min(1.0, at - before)
    left, right = (sprites()[sequence[before + k]] for k in (0, 1))
    # One opaque source per glyph cell avoids a pair of translucent bodies.
    y, x = np.mgrid[:45, :70]
    noise = ((x * 17 + y * 31) % 97) / 97
    distance = np.clip(np.hypot((x - 38) / 38, (y - 25) / 26), 0, 1)
    a = np.asarray(left.getchannel("A").resize((70, 45), Image.Resampling.BOX)) > 90
    b = np.asarray(right.getchannel("A").resize((70, 45), Image.Resampling.BOX)) > 90
    threshold = np.where(a & ~b, 1 - distance, np.where(b & ~a, distance, noise))
    threshold = .08 + .84 * threshold
    mask = Image.fromarray(np.uint8(u >= threshold) * 255).resize(old.SIZE, Image.Resampling.NEAREST)
    image = Image.composite(right, left, mask)
    return motion(image, phase * 2, family in ("quiet", "release"))


def render_one(task):
    family, n = task
    image = pose(family, n)
    colors = np.asarray(image).copy()
    colors[:, :, :3] = np.uint8((colors[:, :, :3] / 255.0) ** 2.3 * 255)
    image = Image.fromarray(colors)
    folder = WORK / family
    folder.mkdir(parents=True, exist_ok=True)
    image.save(folder / f"{n:03}.png")
    tracer = old._tracer()
    alpha = image.getchannel("A")
    grid = tracer.trace(image, ["b" if a >= 80 else "" for a in alpha.tobytes()], [(-100, -100, ":")])
    return family, n, {"art": grid.art, "shade": grid.shade, "part": grid.part}


def prepare(workers):
    WORK.mkdir(parents=True, exist_ok=True)
    grids = {name: [None] * LOOP for name in SEQUENCES}
    tasks = [(family, n) for family in SEQUENCES for n in range(LOOP)]
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for family, n, grid in pool.map(render_one, tasks, chunksize=4):
            grids[family][n] = grid
    (WORK / "grids.json").write_text(json.dumps(grids), encoding="utf-8")
    print(f"Prepared {len(tasks)} animated pose frames", flush=True)
    return grids


def preview(grids):
    output = old.ROOT / "out" / "publish" / "GPT-像素舞蹈试片.mp4"
    output.parent.mkdir(parents=True, exist_ok=True)
    tracer = old._tracer()
    import dancer
    dancer._text_at = lambda t: "gpt·codex·6-astra·white-dragon·//·"
    encoder = subprocess.Popen([FFMPEG, "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                                "-s", "1280x720", "-r", "24", "-i", "pipe:0", "-an",
                                "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p",
                                "-movflags", "+faststart", str(output)], stdin=subprocess.PIPE)
    try:
        for frame in range(288):
            t = frame / 24
            family = "dance" if t < 7.4 else "turn" if t < 9.7 else "reach"
            if family == "dance":
                n = round((t % 3.7) / 3.7 * (LOOP - 1))
            else:
                start, duration = (7.4, 2.3) if family == "turn" else (9.7, 2.3)
                n = min(LOOP - 1, round((t - start) / duration * (LOOP - 1)))
            canvas = Image.new("RGB", (1280, 720), (16, 16, 16))
            draw = ImageDraw.Draw(canvas)
            draw.text((35, 22), "GPT x CODEX  /  KEYFRAME DANCE STUDY", font=font("consolab.ttf", 22), fill=(230, 230, 230))
            image = Image.open(WORK / family / f"{n:03}.png").convert("RGBA")
            pixels = image.resize((70, 90), Image.Resampling.BOX).resize(old.SIZE, Image.Resampling.NEAREST)
            canvas.paste(pixels, (75, 110), pixels)
            data = grids[family][n]
            glyph = dancer.draw(tracer.rig.Frame(data["art"], data["shade"], data["part"]), t, "blue")
            glyph = glyph.resize((466, 600), Image.Resampling.NEAREST)
            canvas.paste(glyph, (620, 100), glyph)
            draw.text((35, 665), f"{family.upper()}  /  {t:05.2f}s  /  KEY POSES + PIXEL MORPH", font=font("consola.ttf", 17), fill=(170, 170, 170))
            encoder.stdin.write(canvas.tobytes())
        encoder.stdin.close()
    finally:
        if encoder.stdin and not encoder.stdin.closed:
            encoder.stdin.close()
    if encoder.wait():
        raise RuntimeError("Could not encode the sprite preview")
    print(output, flush=True)


def write_caches(grids):
    anchors = old.anchors()
    for cache in json.loads(old.TAKES.read_text(encoding="utf-8"))["caches"]:
        folder = old.ROOT / cache["folder"]
        prior = folder / old.MARK
        ours = set(json.loads(prior.read_text(encoding="utf-8"))["takes"]) if prior.exists() else set()
        written = []
        for take, spec in cache["takes"].items():
            if old.state(folder, take, spec, ours) == "present":
                print(f"Preserved external take: {take}", flush=True)
                continue
            family = FAMILIES.get(take, "dance")
            def pick(i):
                if family == "dance":
                    t0, a, rate = anchors.get(take) or (old.FIRST_BEAT, 0.0, 1.0)
                    source_t = t0 + (i / old.FPS - a) * rate
                    phase = ((source_t - old.FIRST_BEAT) / old.BEAT / 8) % 1
                    return round(phase * (LOOP - 1))
                return min(LOOP - 1, round(i / (spec["frames"] - 1) * (LOOP - 1)))
            frames = [dict(frame=i, **grids[family][pick(i)]) for i in range(spec["frames"])]
            (folder / f"{take}.json").write_text(json.dumps(frames), encoding="utf-8")
            rgba = folder / "rgba" / take
            rgba.mkdir(parents=True, exist_ok=True)
            for i in old.indices(spec["rgba"]):
                target = rgba / f"{i:03}.png"
                target.unlink(missing_ok=True)
                source = WORK / family / f"{pick(i):03}.png"
                try:
                    os.link(source, target)
                except OSError:
                    shutil.copyfile(source, target)
            written.append(take)
        prior.write_text(json.dumps({"about": "Generated GPT key-pose animation; built by tools/gpt_sprite_dance.py",
                                     "takes": sorted(ours | set(written))}, indent=1), encoding="utf-8")
        print(f"Installed {len(written)} animated takes in {cache['folder']}", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-caches", action="store_true")
    parser.add_argument("--workers", type=int, default=min(6, os.cpu_count() or 1))
    parser.add_argument("--reuse", action="store_true")
    parser.add_argument("--atlas", type=Path, help="use a different 4-by-3 transparent key-pose atlas")
    args = parser.parse_args()
    if args.atlas:
        global ATLAS
        ATLAS = args.atlas.resolve()
        os.environ["GPT_SPRITE_ATLAS"] = str(ATLAS)
    grids = json.loads((WORK / "grids.json").read_text(encoding="utf-8")) if args.reuse else prepare(max(1, args.workers))
    preview(grids)
    if args.write_caches:
        write_caches(grids)


if __name__ == "__main__":
    main()
