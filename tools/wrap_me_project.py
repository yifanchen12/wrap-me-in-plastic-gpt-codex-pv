"""Adapt the source project's V2 + DSH renderer to the supplied Wrap Me In Plastic track."""
from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
DSH = ROOT / "film" / "pv_dsh_frontend_20260927"
MMD = ROOT / "film" / "mmd_motion_eval_20260927"
SONG = ROOT / "input" / "song.mp3"
OUT = ROOT / "out"
FPS, W, H = 24, 1280, 720
sys.path.insert(0, str(ROOT / "tools"))
from wrap_me_preview import FFMPEG, font, lyric_cues, audio_pulse  # noqa: E402
from wrap_me_full import chapters, probe_duration  # noqa: E402


def source_frame(target_t: float, target_duration: float, source_duration: float) -> int:
    return round(target_t * source_duration / target_duration * FPS)


def lyric_band(frame: Image.Image, t: float, cues, envelope, accents, chapter_map) -> Image.Image:
    from bisect import bisect_right

    idx = min(len(cues) - 1, max(0, bisect_right([c[0] for c in cues], t) - 1))
    cue_t, english, chinese = cues[idx]
    next_t = cues[idx + 1][0] if idx + 1 < len(cues) else chapter_map[-1][1]
    p = min(1.0, max(0.0, (t - cue_t) / max(0.2, next_t - cue_t)))
    shown = english[:max(1, round(len(english) * min(1.0, p * 2.15)))]
    level = float(envelope[min(len(envelope) - 1, max(0, int(t / 0.02)))]) if len(envelope) else 0.0
    accent = max((math.exp(-((t - x) / 0.08) ** 2) for x in accents), default=0.0)
    chapter = next((c for c in reversed(chapter_map) if t >= c[0]), chapter_map[0])
    color = chapter[3] if 120 <= t < 184 else (230, 230, 230)

    frame = frame.convert("RGB")
    d = ImageDraw.Draw(frame)
    d.rectangle((0, 610, W, H), fill=(8, 8, 8))
    d.line((0, 610, W, 610), fill=(*color, 230), width=2)
    d.text((24, 618), "stdout · tokens  //  GPT × CODEX", font=font("consola.ttf", 11), fill=(*color, 235))
    for j in range(76):
        x = 340 + j * 9
        h = 2 + int(12 * abs(math.sin(j * 0.57 + t * 2.9)) * (0.25 + min(1.0, level * 2)))
        d.line((x, 629 - h, x, 629), fill=(*color, 100 + int(accent * 130)), width=2)
    d.text((1112, 618), f"{int(t // 60):02d}:{t % 60:05.2f}", font=font("consola.ttf", 11), fill=(*color, 235))
    d.text((27, 643), "> " + shown, font=font("consolab.ttf", 16 if len(english) < 70 else 14), fill=(244, 244, 255))
    if chinese:
        d.text((29, 675), chinese, font=font("msyh.ttc", 13), fill=(*color, 235))
    d.text((1113, 680), f"{int(p * 100):03d}% · lyric sync", font=font("consola.ttf", 9), fill=(154, 154, 154))
    if accent > 0.72:
        d.rectangle((0, 0, W, 2), fill=(*color, min(210, int(accent * 180))))
    return frame


def worker(start: int, end: int, temp: Path, data_path: Path) -> Path:
    data = json.loads(data_path.read_text(encoding="utf-8"))
    env = dict(os.environ, PYTHONUTF8="1")
    shim = str(DSH / "gpu_shim")
    env["PYTHONPATH"] = os.pathsep.join(p for p in (shim, env.get("PYTHONPATH", "")) if p)
    sys.path.insert(0, str(MMD))
    sys.path.insert(0, str(DSH))
    import dsh_her

    v2, _ = dsh_her.install()
    dsh_her.FPS = FPS
    cues = [tuple(x) for x in data["cues"]]
    accents = data["accents"]
    envelope = data["envelope"]
    chapter_map = [tuple(x) for x in data["chapters"]]
    duration, source_duration = data["duration"], data["source_duration"]
    import dancer
    from bisect import bisect_right
    cue_times = [cue[0] for cue in cues]

    def character_text(source_t):
        target_t = source_t * duration / source_duration
        at = max(0, min(len(cues) - 1, bisect_right(cue_times, target_t) - 1))
        return (" / ".join(cue[1] for cue in cues[at:at + 3]).replace(" ", "·")
                or "GPT·CODEX") + "·//·"

    dancer._text_at = character_text

    target = temp / f"seg-{start:06d}.mp4"
    cmd = [FFMPEG, "-v", "error", "-y", "-f", "rawvideo", "-pixel_format", "rgb24",
           "-video_size", f"{W}x{H}", "-framerate", str(FPS), "-i", "pipe:0", "-an",
           "-c:v", "libx264", "-threads", "1", "-preset", "fast", "-crf", "17",
           "-pix_fmt", "yuv420p", str(target)]
    enc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    try:
        for n in range(start, end):
            t = n / FPS
            src_n = source_frame(t, duration, source_duration)
            src_t = src_n / FPS
            dsh_her.CUR[0] = src_t
            frame = dsh_her.finish(v2.frame(src_n), src_t)
            enc.stdin.write(lyric_band(frame, t, cues, envelope, accents, chapter_map).tobytes())
            if (n - start) % 240 == 0:
                print(f"worker {start}: frame {n}/{end}", flush=True)
        enc.stdin.close()
    finally:
        if enc.stdin and not enc.stdin.closed:
            enc.stdin.close()
    if enc.wait() != 0:
        raise RuntimeError(f"FFmpeg failed for segment starting at frame {start}")
    return target


def render(output: Path, duration: float, workers: int) -> None:
    if not SONG.exists():
        raise FileNotFoundError(f"Missing target song: {SONG}")
    original_lrc = ROOT / "film" / "ai_mascot_mv_world_execute_20260926" / "audio" / "lyrics_synced.lrc"
    source_words = ROOT / "film" / "world_execute_word_timing_20260927" / "word_timeline.json"
    if not original_lrc.exists() or not source_words.exists():
        raise FileNotFoundError("The project's own `python tools/lyrics.py fetch` and `merge` caches are required first.")
    frames_dir = DSH / "dsh_frames"
    if not frames_dir.exists() or len(list(frames_dir.glob("*.png"))) < 4800:
        raise FileNotFoundError("Project DSH pages are missing; run `python build.py pages` first.")

    full_duration = probe_duration()
    duration = min(duration, full_duration)
    cues = lyric_cues(full_duration)
    envelope, accents = audio_pulse(duration)
    chapter_map = chapters(full_duration)
    source_duration = 211.91
    total = round(duration * FPS)
    output.parent.mkdir(parents=True, exist_ok=True)
    manifest = output.with_suffix(".timeline.json")
    obj = {"song": "Wrap Me In Plastic — CHROMANCE", "duration_s": duration, "fps": FPS,
           "lyric_cues": [{"t": t, "en": en, "zh": zh} for t, en, zh in cues],
           "chapters": [{"start": a, "end": b, "title": n, "visual": title} for a, b, n, _, _, title in chapter_map],
           "renderer": "repository continuity_full_v2 + DSH project renderer",
           "source_clock": {"duration_s": source_duration, "target_duration_s": full_duration,
                            "mapping": "linear source-time adaptation"},
           "persona": {"character": "GPT", "model": "6-Astra", "workspace": "Codex",
                       "symbol": "Western white dragon", "palette": "graphite and white",
                       "reasoning_ui": "GPT collapsed thinking status"}}
    manifest.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")

    with tempfile.TemporaryDirectory(prefix="wrap-me-project-", dir=OUT) as tmp:
        temp = Path(tmp)
        data_path = temp / "render-data.json"
        data_path.write_text(json.dumps({"cues": cues, "accents": accents, "envelope": envelope.tolist(),
                                        "chapters": chapter_map, "duration": full_duration,
                                        "source_duration": source_duration}, ensure_ascii=False), encoding="utf-8")
        bounds = [total * k // workers for k in range(workers + 1)]
        procs = []
        for i in range(workers):
            cmd = [sys.executable, "-B", str(Path(__file__).resolve()), "--worker",
                   str(bounds[i]), str(bounds[i + 1]), str(temp), str(data_path)]
            env = dict(os.environ, PYTHONUTF8="1", PYTHONPATH=os.pathsep.join(
                p for p in (str(DSH / "gpu_shim"), os.environ.get("PYTHONPATH", "")) if p))
            procs.append(subprocess.Popen(cmd, cwd=ROOT, env=env))
        codes = [p.wait() for p in procs]
        if any(codes):
            raise RuntimeError(f"Render workers failed: {codes}")

        listing = temp / "segments.txt"
        segments = [temp / f"seg-{bounds[i]:06d}.mp4" for i in range(workers)]
        listing.write_text("".join(f"file '{p.as_posix()}'\n" for p in segments), encoding="utf-8")
        master = output.with_name(output.stem + "-master.mp4")
        subprocess.run([FFMPEG, "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(listing),
                        "-c", "copy", str(master)], check=True)
        subprocess.run([FFMPEG, "-v", "error", "-y", "-i", str(master), "-i", str(SONG),
                        "-map", "0:v:0", "-map", "1:a:0", "-t", f"{duration:.6f}",
                        "-vf", "scale=1920:1080:flags=lanczos,format=yuv420p", "-r", str(FPS),
                        "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-c:a", "aac", "-b:a", "320k",
                        "-movflags", "+faststart", "-shortest", str(output)], check=True)
    print(f"wrote {master} and {output}", flush=True)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=ROOT / "out" / "wrap-me-in-plastic-project-engine.mp4")
    ap.add_argument("--duration", type=float, help="render only the first N seconds for a review sample")
    ap.add_argument("--workers", type=int, default=min(4, max(1, (os.cpu_count() or 4) - 2)))
    ap.add_argument("--worker", nargs=4, metavar=("START", "END", "TEMP", "DATA"), help=argparse.SUPPRESS)
    a = ap.parse_args()
    if a.worker:
        worker(int(a.worker[0]), int(a.worker[1]), Path(a.worker[2]), Path(a.worker[3]))
        return
    duration = min(a.duration, probe_duration()) if a.duration else probe_duration()
    render(a.output if a.output.is_absolute() else ROOT / a.output, duration, max(1, a.workers))


if __name__ == "__main__":
    main()
