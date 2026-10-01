"""Render a 45-second GPT x Codex PV study for the supplied Wrap Me In Plastic LRC/MP3."""
from __future__ import annotations

from functools import lru_cache
import math
import re
import shutil
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
DURATION, FPS, W, H = 45.0, 24, 1280, 720
SONG = ROOT / "input" / "song.mp3"
LRC = ROOT / "input" / "lyrics.lrc"
CHAR = ROOT / "assets" / "gpt-character-fusion.png"
OUT = ROOT / "out" / "wrap-me-in-plastic-preview.mp4"
FFMPEG = shutil.which("ffmpeg") or str(ROOT / "tools" / "ffmpeg" / "bin" / "ffmpeg.exe")
TAG = re.compile(r"^\s*((?:\[\d+:\d+(?:[.:]\d+)?\]\s*)+)(.*)$")
TIME = re.compile(r"\[(\d+):(\d+)(?:[.:](\d+))?\]")

BG = (7, 11, 25)
CYAN = (116, 222, 255)
VIOLET = (197, 166, 255)
WHITE = (242, 241, 255)


@lru_cache(maxsize=32)
def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    path = Path("C:/Windows/Fonts") / name
    return ImageFont.truetype(str(path), size)


def lyric_cues(duration: float = DURATION) -> list[tuple[float, str, str]]:
    rows = []
    for raw in LRC.read_text(encoding="utf-8-sig").splitlines():
        match = TAG.match(raw)
        if not match:
            continue
        body = " ".join(match.group(2).split())
        if not body or body.lower().startswith(("wrap me in plastic -", "lyrics by", "composed by")):
            continue
        tags = [(int(m[1]) * 60 + int(m[2]) + float("0." + m[3]) if m[3] else
                 int(m[1]) * 60 + int(m[2])) for m in TIME.finditer(match.group(1))]
        for t in tags:
            # Keep trailing translation rows even when their timestamp falls just
            # beyond the audio endpoint; this LRC stamps translations at the
            # following English cue, including the final line.
            rows.append((t, body))
    cues: list[list] = []
    for t, body in rows:
        if re.search(r"[A-Za-z]", body):
            if t < duration:
                cues.append([t, body, ""])
        elif re.search(r"[\u3400-\u9fff]", body) and cues and not cues[-1][2]:
            # In this LRC the translation is stamped at the next English cue; pair in file order.
            cues[-1][2] = body
    cues = [tuple(cue) for cue in cues]
    if not cues:
        raise ValueError(f"No timed bilingual lyric lines found in {LRC}")
    return cues


def audio_pulse(duration: float = DURATION) -> tuple[np.ndarray, list[float]]:
    pcm = subprocess.run(
        [FFMPEG, "-v", "error", "-i", str(SONG), "-t", str(duration), "-vn", "-ac", "1",
         "-ar", "12000", "-f", "s16le", "pipe:1"], check=True, capture_output=True).stdout
    samples = np.frombuffer(pcm[:len(pcm) // 2 * 2], dtype="<i2").astype(np.float32) / 32768.0
    hop = 240  # 20 ms envelope
    usable = len(samples) // hop * hop
    rms = np.sqrt(np.mean(samples[:usable].reshape(-1, hop) ** 2, axis=1) + 1e-9)
    smooth = np.convolve(rms, np.ones(5) / 5, mode="same")
    rise = np.maximum(0, smooth - np.roll(smooth, 3))
    rise[:3] = 0
    threshold = max(float(np.quantile(rise, 0.82)), float(np.mean(rise) + 0.6 * np.std(rise)))
    peaks = []
    last = -99
    for i in range(2, len(rise) - 2):
        if rise[i] >= threshold and rise[i] >= max(rise[i - 2:i]) and rise[i] > max(rise[i + 1:i + 3]):
            t = i * 0.02
            if t - last >= 0.28:
                peaks.append(t)
                last = t
    return smooth, peaks


def fit_character() -> Image.Image:
    image = Image.open(CHAR).convert("RGBA")
    alpha = image.getchannel("A")
    box = alpha.getbbox()
    image = image.crop(box)
    image.thumbnail((520, 710), Image.Resampling.LANCZOS)
    return image


def draw_frame(t: float, cues: list[tuple[float, str, str]], levels: np.ndarray,
               hits: list[float], character: Image.Image) -> Image.Image:
    idx = min(len(cues) - 1, max(0, next((i for i, cue in enumerate(cues) if cue[0] > t), len(cues)) - 1))
    cue_t, english, chinese = cues[idx]
    next_t = cues[idx + 1][0] if idx + 1 < len(cues) else DURATION
    level = float(levels[min(len(levels) - 1, int(t / 0.02))]) if len(levels) else 0
    hit = max((math.exp(-((t - x) / 0.075) ** 2) for x in hits), default=0)
    section = sum(t >= mark for mark in (11, 22, 32, 40))
    accent = [CYAN, VIOLET, (117, 245, 211), (255, 184, 224), (255, 213, 150)][section]

    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im, "RGBA")
    # Drifting parallax grid and a soft holographic halo establish depth behind the heroine.
    gx, gy = int(t * 11) % 48, int(t * 7) % 48
    for x in range(-48 + gx, W + 48, 48):
        d.line((x, 0, x, H), fill=(accent[0], accent[1], accent[2], 15), width=1)
    for y in range(-48 + gy, H + 48, 48):
        d.line((0, y, W, y), fill=(accent[0], accent[1], accent[2], 15), width=1)
    fx = Image.new("RGBA", (W, H))
    fd = ImageDraw.Draw(fx, "RGBA")
    halo_x, halo_y = 1000 + int(10 * math.sin(t * 0.7)), 348
    halo_r = 138 + int(13 * math.sin(t * 1.5)) + int(26 * hit)
    for ring in range(3):
        r = halo_r + ring * 25
        fd.ellipse((halo_x-r, halo_y-r, halo_x+r, halo_y+r), outline=(*accent, max(28, 100 - ring * 23)), width=2)
    # Digital motes drift at different speeds; audio hits stretch them into short light trails.
    for j in range(68):
        x0 = 724 + (j * 89) % 600
        y0 = (j * 137) % 720
        speed = 14 + (j % 7) * 9
        x = 724 + (x0 - 724 + int(t * speed)) % 600
        y = (y0 + int(t * (9 + j % 13))) % 720
        radius = 1 + (j % 3 == 0)
        alpha = 48 + int(90 * (0.5 + 0.5 * math.sin(t * 2 + j))) + int(hit * 70)
        fd.ellipse((x-radius, y-radius, x+radius, y+radius), fill=(*accent, alpha))
        if hit > 0.3 and j % 3 == 0:
            fd.line((x, y, x-10-int(hit*12), y-18-int(hit*17)), fill=(*WHITE, int(hit*115)), width=2)
    glow = fx.filter(ImageFilter.GaussianBlur(18))
    im = Image.alpha_composite(im.convert("RGBA"), glow)
    im = Image.alpha_composite(im, fx)
    d = ImageDraw.Draw(im, "RGBA")
    d.rectangle((0, 0, W, 7), fill=(*accent, int(90 + 110 * hit)))
    d.text((55, 32), "GPT  ×  CODEX", font=font("consolab.ttf", 24), fill=(*WHITE, 245))
    d.text((55, 69), "A WINDOW INTO HER WORLD   /   CHROMANCE", font=font("consola.ttf", 14), fill=(*accent, 235))
    d.text((1115, 38), f"{int(t // 60):02d}:{t % 60:05.2f}", font=font("consola.ttf", 17), fill=(*WHITE, 220))

    # Code pane: each lyric phrase is a new scene cue; signal peaks pulse the trace.
    pane = (54, 127, 724, 586)
    d.rounded_rectangle(pane, radius=20, fill=(9, 16, 35, 238), outline=(*accent, 140), width=2)
    d.rounded_rectangle((74, 147, 704, 194), radius=11, fill=(18, 27, 52, 245))
    d.ellipse((91, 163, 105, 177), fill=(255, 119, 151, 230))
    d.ellipse((115, 163, 129, 177), fill=(255, 209, 113, 230))
    d.ellipse((139, 163, 153, 177), fill=(105, 231, 183, 230))
    d.text((179, 160), f"/codex/gpt/session_{section + 1:02d}.py", font=font("consola.ttf", 17), fill=(197, 208, 236, 255))

    code = [
        ("01", "async def meet_you():"),
        ("02", "    await open_the_window()"),
        ("03", "    world = await codex.boot()"),
        ("04", "    gpt.look_up()  # online"),
    ]
    yy = 224
    for no, text in code:
        d.text((92, yy), no, font=font("consola.ttf", 17), fill=(108, 128, 164, 220))
        d.text((139, yy), text, font=font("consola.ttf", 19), fill=(*accent, 238))
        yy += 33
    trace_y = 373
    d.line((91, trace_y + 25, 681, trace_y + 25), fill=(110, 139, 174, 62), width=1)
    points = []
    count = 100
    phase = t * 3.3
    for j in range(count):
        x = 94 + j * 5.8
        amp = 8 + 16 * level + 13 * hit
        y = trace_y + 25 + math.sin(j * 0.34 - phase) * amp * (0.3 + 0.7 * math.sin(j * 0.11) ** 2)
        points.append((x, y))
    d.line(points, fill=(*accent, 230), width=3)
    d.text((92, 414), "AUDIO → MOTION", font=font("consolab.ttf", 14), fill=(155, 178, 210, 220))
    # Phrase timing progress is visible and follows the LRC timestamps.
    progress = min(1.0, max(0.0, (t - cue_t) / max(0.15, next_t - cue_t)))
    d.rounded_rectangle((92, 449, 686, 455), radius=3, fill=(89, 105, 139, 90))
    d.rounded_rectangle((92, 449, 92 + int(594 * progress), 455), radius=3, fill=(*accent, 220))
    d.text((92, 478), "// LYRICS FOLLOW THE RECORDING", font=font("consola.ttf", 14), fill=(147, 162, 191, 225))
    d.text((92, 520), f"BEAT PULSE  {int(hit * 100):03d}%", font=font("consola.ttf", 14), fill=(*accent, 225))
    d.text((92, 548), f"PHRASE      {idx + 1:02d} / {len(cues):02d}", font=font("consola.ttf", 14), fill=(174, 188, 213, 225))

    # Phrase cuts alternate wide, medium, and close framing; the still gets a small reactive camera move.
    shot = idx % 4
    scale = (0.93, 1.03, 1.13, 1.0)[shot] + 0.012 * math.sin(t * 1.7) + 0.025 * hit + 0.01 * min(1, level * 3)
    cw, ch = int(character.width * scale), int(character.height * scale)
    hero = character.resize((cw, ch), Image.Resampling.LANCZOS)
    x = (790, 825, 747, 775)[shot] + int(8 * math.sin(t * 0.72) - 13 * hit)
    y = (11, -9, -68, 20)[shot] + int(9 * math.sin(t * 1.15))
    im_rgba = im.convert("RGBA")
    im_rgba.alpha_composite(hero, (x, y))
    im = im_rgba.convert("RGB")
    d = ImageDraw.Draw(im, "RGBA")
    # A brief horizontal tear marks lyric-driven cuts, then clears before the subtitle appears.
    cut_age = t - cue_t
    if 0 <= cut_age < 0.13:
        tear = int((1 - cut_age / 0.13) * 15)
        for y0 in (246, 402, 538):
            band = im.crop((0, y0, W, y0 + 5))
            im.paste(band.crop((tear, 0, W, 5)), (0, y0))
        d = ImageDraw.Draw(im, "RGBA")
        d.rectangle((0, 245, W, 247), fill=(*accent, int((1-cut_age/0.13)*90)))
    # Fine CRT scanlines; the lyric card is drawn after this so both languages stay crisp.
    for y0 in range(2, H, 4):
        d.line((0, y0, W, y0), fill=(174, 199, 255, 10), width=1)
    # Lyric card takes the lower left, clear of the character silhouette.
    d.rounded_rectangle((54, 607, 1223, 695), radius=18, fill=(7, 12, 28, 226), outline=(*accent, 115), width=1)
    en_font = font("consolab.ttf", 25 if len(english) < 37 else 21)
    d.text((82, 620), english or "…", font=en_font, fill=(*WHITE, 255))
    d.text((84, 661), chinese or "", font=font("msyh.ttc", 19), fill=(*accent, 250))
    # One short flash at a detected onset keeps the motion linked to this recording.
    if hit > 0.55:
        d.rectangle((0, 0, W, H), fill=(accent[0], accent[1], accent[2], int(7 * hit)))
    return im


def main() -> None:
    for p in (SONG, LRC, CHAR):
        if not p.exists():
            raise FileNotFoundError(p)
    cues = lyric_cues()
    levels, hits = audio_pulse()
    character = fit_character()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    cmd = [FFMPEG, "-v", "error", "-y", "-f", "rawvideo", "-pixel_format", "rgb24", "-video_size",
           f"{W}x{H}", "-framerate", str(FPS), "-i", "pipe:0", "-ss", "0", "-t", str(DURATION),
           "-i", str(SONG), "-map", "0:v:0", "-map", "1:a:0", "-t", str(DURATION), "-c:v", "libx264",
           "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
           "-movflags", "+faststart", str(OUT)]
    encoder = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    try:
        for frame in range(round(DURATION * FPS)):
            t = frame / FPS
            encoder.stdin.write(draw_frame(t, cues, levels, hits, character).tobytes())
    finally:
        encoder.stdin.close()
    if encoder.wait() != 0:
        raise RuntimeError("FFmpeg failed while encoding the preview")
    print(f"wrote {OUT.relative_to(ROOT)} ({DURATION:g}s, {len(cues)} lyric cues, {len(hits)} detected audio accents)")


if __name__ == "__main__":
    main()
