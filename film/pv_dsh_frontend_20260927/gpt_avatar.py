"""Shared face framing and neutral mosaics for the GPT training avatar."""
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageOps

EXPR = Path(__file__).resolve().parents[2] / "assets" / "gpt_expressions"
HEAD_BOX = (275, 0, 675, 400)
MAX_CELLS = 40


@lru_cache(maxsize=8)
def head(name="cheerful"):
    art = Image.open(EXPR / f"gpt-{name}.webp").convert("RGBA")
    background = Image.new("RGBA", art.size, (18, 18, 18, 255))
    background.alpha_composite(art)
    return ImageOps.grayscale(background.convert("RGB").crop(HEAD_BOX))


def mosaic(gray, cells):
    reduced = gray.resize((cells, cells), Image.Resampling.BOX)
    reduced = reduced.resize((MAX_CELLS, MAX_CELLS), Image.Resampling.NEAREST)
    return ImageOps.colorize(reduced, (16, 16, 16), (194, 194, 194)).convert("RGB")
