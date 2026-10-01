"""Build the GPT x Codex / Wrap Me In Plastic adaptation with generated key-pose animation."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys

import build


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=min(4, max(1, (os.cpu_count() or 4) - 2)))
    parser.add_argument("--skip-pages", action="store_true", help="reuse existing chat screenshots")
    parser.add_argument("--skip-dancer", action="store_true", help="reuse existing generated dance caches")
    parser.add_argument("--duration", type=float, help="first N seconds for a preview")
    parser.add_argument("--output", type=Path, default=Path("out/publish/投稿成片-GPT-Codex-动画增强版.mp4"))
    args = parser.parse_args()
    local_bins = build.ROOT / "tools" / "ffmpeg" / "bin"
    if local_bins.exists():
        os.environ["PATH"] = str(local_bins) + os.pathsep + os.environ.get("PATH", "")
    for command in ("ffmpeg", "ffprobe", "node"):
        if not shutil.which(command):
            raise FileNotFoundError(f"Missing {command}: install it and add it to PATH")
    for path in (build.SONG, build.LRC, build.ROOT / "assets" / "gpt-dance-atlas.png"):
        if not path.exists():
            raise FileNotFoundError(f"Required input is missing: {path}")
    source_lrc = build.ROOT / "input" / "source-world-execute.lrc"
    source_cache = build.ROOT / "film" / "world_execute_word_timing_20260927" / "word_timeline.json"
    if not source_cache.exists():
        build.run([sys.executable, "tools/lyrics.py", "fetch", "--out", source_lrc])
        build.run([sys.executable, "tools/lyrics.py", "merge", "--lrc", source_lrc])
    if not args.skip_dancer:
        command = [sys.executable, "-B", "tools/gpt_sprite_dance.py", "--write-caches", "--workers", args.workers]
        if (build.ROOT / "film/tui_pv_world_execute_20260926/continuity_full_v2/cache/gpt_sprite_dance/grids.json").exists():
            command.append("--reuse")
        build.run(command, env=build.env())
    if not args.skip_pages:
        build.pages()
    command = [sys.executable, "-B", "tools/wrap_me_project.py", "--workers", args.workers,
               "--output", args.output]
    if args.duration is not None:
        command.extend(["--duration", args.duration])
    build.run(command, env=build.env())


if __name__ == "__main__":
    main()
