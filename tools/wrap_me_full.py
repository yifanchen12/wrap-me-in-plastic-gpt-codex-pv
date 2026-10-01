"""Render the full Wrap Me In Plastic adaptation without changing the Mili-specific source build."""
from __future__ import annotations

import argparse
from bisect import bisect_right
import json
import math
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from tools.wrap_me_preview import ROOT, SONG, LRC, FFMPEG, audio_pulse, font, lyric_cues

FPS, W, H = 24, 1280, 720
MASTER = ROOT / "out" / "wrap-me-in-plastic-master.mp4"
DELIVERY = ROOT / "out" / "wrap-me-in-plastic-full-pv.mp4"
POSES = [ROOT / "assets" / n for n in ("gpt-character-fusion.png", "gpt-keypose-reach.png", "gpt-keypose-dance.png")]

CHAPTERS = [
    (0.0, 10.0, "01 / BOOT + PROTECT", (105, 180, 255), 0, "OPEN THE CODEX SESSION"),
    (10.0, 26.0, "02 / LOAD MODEL", (117, 197, 255), 0, "LOAD GPT INTO THE WINDOW"),
    (26.0, 44.0, "03 / TOKEN STREAM", (161, 153, 255), 0, "LET THE WORDS BECOME DATA"),
    (44.0, 61.0, "04 / EMBEDDINGS", (190, 151, 255), 1, "ME ↔ YOU ↔ WORLD"),
    (61.0, 82.0, "05 / GENERATE", (107, 215, 255), 2, "ASSEMBLE HER IMAGE"),
    (82.0, 99.0, "06 / REWARD LOOP", (247, 171, 220), 2, "MAXIMIZE HAPPY( YOU )"),
    (99.0, 120.0, "07 / PING + MEMORY", (118, 188, 255), 0, "WAITING FOR YOUR REPLY"),
    (120.0, 146.0, "08 / CONTEXT ERROR", (255, 156, 99), 0, "LIMIT REACHED · RECOVER"),
    (146.0, 171.0, "09 / EXECUTION", (255, 77, 103), 1, "RUN THE WORLD ACTION"),
    (171.0, 184.0, "10 / RECONSTRUCT", (255, 115, 151), 2, "FIND THE GPT SIGNAL"),
    (184.0, 193.673, "11 / LOVE = YOU", (182, 170, 255), 2, "WEIGHTS RELEASED · STILL HERE"),
]
BG = (5, 8, 20)
WHITE = (244, 244, 255)


def probe_duration() -> float:
    probe = shutil.which("ffprobe") or str(ROOT / "tools" / "ffmpeg" / "bin" / "ffprobe.exe")
    p = subprocess.run([probe, "-v", "error",
                        "-show_entries", "format=duration", "-of", "json", str(SONG)],
                       capture_output=True, text=True, check=True)
    return float(json.loads(p.stdout)["format"]["duration"])


def chapters(duration: float) -> list[tuple[float, float, str, tuple[int, int, int], int, str]]:
    out = []
    for i, (a, b, name, color, pose, title) in enumerate(CHAPTERS):
        end = min(duration, CHAPTERS[i + 1][0] if i + 1 < len(CHAPTERS) else duration)
        if a < duration:
            out.append((a, end, name, color, pose, title))
    if not out or out[-1][1] != duration:
        raise ValueError("chapter map does not cover the full song")
    return out


def make_background() -> Image.Image:
    x = np.linspace(-1.0, 1.0, W, dtype=np.float32)[None, :]
    y = np.linspace(-1.0, 1.0, H, dtype=np.float32)[:, None]
    r = np.sqrt(((x + 0.12) / 1.05) ** 2 + ((y + 0.06) / 0.96) ** 2)
    v = np.clip(18 - 16 * r, 2, 18)
    arr = np.empty((H, W, 3), dtype=np.uint8)
    arr[:, :, 0] = (v * 0.43).astype(np.uint8)
    arr[:, :, 1] = (v * 0.58).astype(np.uint8)
    arr[:, :, 2] = (v * 1.15).astype(np.uint8)
    return Image.fromarray(arr, "RGB")


def load_poses() -> list[Image.Image]:
    result = []
    for p in POSES:
        art = Image.open(p).convert("RGBA")
        bbox = art.getchannel("A").point(lambda a: 255 if a > 12 else 0).getbbox()
        if not bbox:
            raise ValueError(f"transparent character pose is empty: {p}")
        result.append(art.crop(bbox))
    base=result[0]
    w,h=base.size
    # Tight portrait crop: the chat sidebar should show a face, not a tiny full-body sprite.
    face=base.crop((int(w*.23),0,int(w*.77),int(h*.36)))
    result.append(face)
    # Reusable representations for the reference's pixel/point-cloud and pose-grid shots.
    for art in result[:3]:
        small=art.resize((72,108),Image.Resampling.LANCZOS)
        result.append(small.resize((288,432),Image.Resampling.NEAREST))
    for art in result[:3]:
        thumb=art.copy();thumb.thumbnail((74,96),Image.Resampling.LANCZOS)
        result.append(thumb)
    return result


def project(point: tuple[float, float, float], t: float, cx: float, cy: float,
            scale: float = 1.0) -> tuple[int, int]:
    x, y, z = point
    a, b = t * 0.43, t * 0.27 + 0.42
    x, z = x * math.cos(a) - z * math.sin(a), x * math.sin(a) + z * math.cos(a)
    y, z = y * math.cos(b) - z * math.sin(b), y * math.sin(b) + z * math.cos(b)
    d = 3.9 / max(1.7, 4.8 - z)
    return round(cx + x * scale * d), round(cy + y * scale * d)


def cube_points(size: float = 1.0) -> list[tuple[float, float, float]]:
    return [(x * size, y * size, z * size) for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)]


def draw_wire_cube(d: ImageDraw.ImageDraw, t: float, center: tuple[int, int], size: float,
                   color: tuple[int, int, int], alpha: int = 220, width: int = 2) -> None:
    pts = [project(p, t, *center, scale=size) for p in cube_points()]
    edges = [(a, b) for a, p in enumerate(cube_points()) for b, q in enumerate(cube_points())
             if b > a and sum(x != y for x, y in zip(p, q)) == 1]
    for a, b in edges:
        d.line((*pts[a], *pts[b]), fill=(*color, alpha), width=width)


def draw_house(d: ImageDraw.ImageDraw, t: float, progress: float, color, hit: float) -> None:
    cx, cy = 565, 342
    # Isometric room frame; lines appear in phrase-sized groups as the house is assembled.
    points = [(-1, -0.52, -0.65), (1, -0.52, -0.65), (1, 0.52, -0.65), (-1, 0.52, -0.65),
              (-1, -0.52, 0.65), (1, -0.52, 0.65), (1, 0.52, 0.65), (-1, 0.52, 0.65),
              (0, -1.0, -0.65), (0, -1.0, 0.65)]
    p = [project(v, t * 0.18, cx, cy, 245) for v in points]
    edges = [(0,1),(1,2),(2,3),(3,0),(4,5),(5,6),(6,7),(7,4),(0,4),(1,5),(2,6),(3,7),
             (0,8),(1,8),(8,9),(4,9),(5,9)]
    n = min(len(edges), 3 + int(progress * len(edges)))
    for i, (a,b) in enumerate(edges[:n]):
        d.line((*p[a], *p[b]), fill=(*color, 115 + int(hit * 100)), width=2 + int(hit * 2))
    # Windows and an animated floor grid make it read as a tiny lit room.
    for row in range(3):
        for col in range(4):
            if progress > 0.25 + (row * 4 + col) * 0.035:
                x0 = 425 + col * 69 + int(5 * math.sin(t + row))
                y0 = 298 + row * 54
                d.rounded_rectangle((x0, y0, x0 + 44, y0 + 30), radius=3,
                                     outline=(*color, 100 + int(hit*90)), width=2)
    for k in range(8):
        x0 = 350 + k * 48
        d.line((x0, 493, 560 + (x0-560)//2, 548), fill=(*color, 35 + int(35*hit)), width=1)


def draw_dog(d: ImageDraw.ImageDraw, t: float, color, progress: float) -> None:
    # A little articulated dog assembled from wooden strokes and glowing twine.
    sway = 7 * math.sin(t * 1.7)
    pts = [(384, 354), (482, 342), (549, 354), (594, 326), (630, 343), (620, 374),
           (537, 390), (470, 380), (425, 430), (457, 435), (518, 390), (552, 438), (583, 434),
           (609, 373), (349, 330), (322, 346)]
    pts = [(x + (sway if i % 2 else -sway), y + 5*math.sin(t*2+i)) for i,(x,y) in enumerate(pts)]
    edges = [(0,1),(1,2),(2,3),(3,4),(4,5),(5,6),(6,7),(7,1),(1,8),(8,9),(7,10),(10,11),
             (11,12),(6,13),(0,14),(14,15)]
    for k, (a,b) in enumerate(edges):
        if progress > k / len(edges):
            d.line((*pts[a], *pts[b]), fill=(*color, 205), width=4 if k < 14 else 3)
    # Twine stitches between joints.
    for k in range(12):
        x = 385 + k * 18
        y = 365 + 17 * math.sin(k * 0.9 + t * 2)
        d.ellipse((x-2,y-2,x+2,y+2), fill=(255,225,171,190))
    d.ellipse((622, 338, 629, 345), fill=(255,255,240,240))


def draw_scene(d: ImageDraw.ImageDraw, t: float, chapter: int, color, hit: float,
               cue_progress: float, loud: float) -> None:
    # Perspective floor and moving geometry echo the reference's cinematic concept diagrams.
    van = (654, 270)
    if chapter in (0, 1, 6):
        for k in range(-11, 12):
            x = 654 + k * 28
            d.line((van[0], van[1], x, 720), fill=(*color, 24 + int(hit * 42)), width=1)
        for k in range(10):
            y = 322 + k*k*4
            d.line((0, y, W, y), fill=(*color, 17 + int(hit * 26)), width=1)

    if chapter == 0:
        draw_wire_cube(d, t, (650, 355), 180 + 12*hit, color, 165)
        for j in range(5):
            y = 255 + j*39
            width = 160 + int(100 * (0.5 + 0.5*math.sin(t*1.6 + j)))
            d.rounded_rectangle((88, y, 88+width, y+21), radius=8,
                                fill=(11,20,39,200), outline=(*color, 70), width=1)
            d.rectangle((104, y+8, 104+int(width*0.48), y+12), fill=(*color, 160))
    elif chapter in (1, 6):
        for j in range(4):
            r = 58 + j*27 + int(11*math.sin(t*1.4+j))
            d.arc((650-r, 340-r, 650+r, 340+r), int(t*55+j*50), int(t*55+j*50+218),
                  fill=(*color, 180), width=3)
        d.text((460, 210), "AWAITING INPUT", font=font("consolab.ttf", 18), fill=(*color, 215))
        d.rounded_rectangle((455, 466, 816, 481), radius=7, outline=(*color, 150), width=2)
        d.rounded_rectangle((458, 469, 458+int(354*cue_progress), 478), radius=5, fill=(*color, 190))
        for i in range(9):
            x, y = 470+i*39, 397+int(8*math.sin(t*2.5+i))
            d.ellipse((x-4,y-4,x+4,y+4), fill=(*color,120+int(110*hit)))
            if i:
                d.line((x-39,397+int(8*math.sin(t*2.5+i-1)),x,y), fill=(*color,100), width=1)
    elif chapter in (2, 4):
        draw_house(d, t, cue_progress, color, hit)
        # Luminous glass blocks orbit as the room fills in.
        for j in range(18):
            a = t*0.45 + j*math.tau/18
            x, y = 568 + math.cos(a)*240, 335 + math.sin(a*1.4)*180
            r = 5 + (j%3)*3
            d.polygon([(x,y-r),(x+r,y),(x,y+r),(x-r,y)], fill=(*color, 60+int(hit*85)))
        draw_wire_cube(d, t*0.6, (560, 355), 275, color, 56, 1)
    elif chapter == 3:
        for j in range(8):
            x0 = 170 + j*80
            endx = 810 + 30*math.sin(t*1.2+j)
            endy = 290 + j*28 + 22*math.sin(t*2+j)
            d.line((x0, 48, x0+20*math.sin(t+j), 193, endx, endy), fill=(*color, 125+int(hit*90)), width=2)
            d.ellipse((endx-5,endy-5,endx+5,endy+5), fill=(242,247,255,200))
        draw_wire_cube(d, t, (510, 350), 220, color, 100, 2)
        for j in range(6):
            d.rounded_rectangle((81, 229+j*44, 300+int(40*math.sin(t+j)), 251+j*44), radius=8,
                                outline=(*color, 120), width=2)
    elif chapter == 5:
        # Transparent plastic ribbons orbit the room and the heroine as luminous curves.
        cx, cy = 865, 350
        for strand in range(7):
            pts = []
            phase = t*1.15 + strand*0.82
            for q in range(170):
                u = q/169*math.tau*2
                rx = 208 + strand*9
                ry = 76 + strand*12
                x = cx + math.cos(u+phase)*rx
                y = cy + math.sin(u*1.7+phase)*ry + 24*math.sin(u+phase)
                pts.append((round(x),round(y)))
            d.line(pts, fill=(*color, 52+int(hit*80)), width=2+int(hit*2))
        draw_wire_cube(d, -t*0.35, (520, 355), 175+25*loud, color, 120)
        for j in range(28):
            a = t*1.9+j*math.tau/28
            x, y = cx+math.cos(a)*230, cy+math.sin(a*1.8)*240
            d.ellipse((x-2,y-2,x+2,y+2), fill=(255,247,255,170))
    else:
        draw_dog(d, t, color, cue_progress)
        draw_wire_cube(d, t*0.75, (550, 350), 255, color, 75, 1)
        # Final flower / prism opens into the beat.
        cx, cy = 570, 337
        for k in range(12):
            a = math.tau*k/12+t*0.16
            r = 155 + int(42*hit) + 28*math.sin(t*0.8+k)
            x,y = cx+math.cos(a)*r, cy+math.sin(a)*r*0.65
            d.line((cx,cy,x,y), fill=(*color,105+int(hit*110)), width=2)
            d.ellipse((x-7,y-7,x+7,y+7), fill=(255,248,223,150+int(hit*80)))


def lyric_frame(t, cues, cue_index, color) -> Image.Image:
    _, english, chinese = cues[cue_index]
    start = cues[cue_index][0]
    end = cues[cue_index+1][0] if cue_index+1 < len(cues) else t + 1
    p = min(1.0, max(0.0, (t-start)/max(0.2,end-start)))
    shown = english[:max(1, int(len(english)*min(1.0,p*2.2)))] if english else ""
    overlay = Image.new("RGBA", (W,H), (0,0,0,0))
    d = ImageDraw.Draw(overlay)
    d.rounded_rectangle((45, 596, 1235, 694), radius=18, fill=(4,8,22,218), outline=(*color,115), width=1)
    d.text((76, 612), shown, font=font("consolab.ttf", 25 if len(english)<48 else 21), fill=(*WHITE,250))
    d.text((78, 657), chinese or "", font=font("msyh.ttc", 20), fill=(*color,245))
    # waveform rule continues the audio-response motif without obscuring the image.
    d.rounded_rectangle((845, 675, 1200, 680), radius=2, fill=(*color,55))
    d.rounded_rectangle((845, 675, 845+int(355*p), 680), radius=2, fill=(*color,200))
    return overlay


def _panel(d, box, color, title=None):
    d.rounded_rectangle(box,radius=7,fill=(5,9,19,255),outline=(*color,125),width=1)
    if title:
        d.text((box[0]+9,box[1]+6),title,font=font('consola.ttf',10),fill=(*color,215))


def _heatmap(d,x,y,cols,rows,t,color,cell=13):
    for r in range(rows):
        for c in range(cols):
            v=(math.sin(c*.71+r*.39+t*1.8)+1)*.5
            a=35+int(v*155)
            d.rectangle((x+c*(cell+2),y+r*(cell+2),x+c*(cell+2)+cell,y+r*(cell+2)+cell),
                        fill=(*color,a),outline=(140,160,195,28))


def _pixel_reveal(im,art,x,y,p,color,t):
    w,h=art.size
    crop=art.crop((0,0,max(1,int(w*p)),h))
    im.alpha_composite(crop,(x,y))
    d=ImageDraw.Draw(im)
    for k in range(74):
        a=t*.8+k*2.399;r=150+24*math.sin(t+k)
        px=x+w/2+math.cos(a)*r;py=y+h/2+math.sin(a)*r*.68
        if k/74>p:
            d.ellipse((px-1,py-1,px+2,py+2),fill=(*color,155))


def _draw_scene(d,im,ci,t,p,color,hit,level,poses):
    _panel(d,(250,65,1004,620),color,'/ codex / gpt / workbench')
    _panel(d,(1015,65,1248,620),color,'agent telemetry')
    d.text((267,91),CHAPTERS[ci][5],font=font('consolab.ttf',16),fill=(*WHITE,240))
    d.line((265,117,990,117),fill=(*color,65),width=1)
    for j,name in enumerate(('tokens','attention','memory','reward','latency')):
        y=117+j*60;v=min(.99,max(.08,.18+.73*(.5+.5*math.sin(t*.31+j*1.7))))
        d.text((1030,y),name,font=font('consola.ttf',11),fill=(160,177,202,205))
        d.rounded_rectangle((1030,y+21,1228,y+29),radius=3,outline=(*color,70),width=1)
        d.rounded_rectangle((1032,y+23,1032+int(194*v),y+27),radius=2,fill=(*color,205))
        d.text((1187,y-1),f'{v*100:02.0f}%',font=font('consola.ttf',10),fill=(*WHITE,185))
    d.text((1030,423),'MODEL  GPT',font=font('consola.ttf',11),fill=(*color,225))
    d.text((1030,444),'AGENT  CODEX',font=font('consola.ttf',11),fill=(*WHITE,215))
    d.text((1030,465),'SANDBOX  ON',font=font('consola.ttf',10),fill=(143,210,171,225))
    for j in range(25):
        x=1034+j*7;hh=4+int(25*abs(math.sin(j*.7+t*2))*(.2+level*2))
        d.line((x,558-hh,x,558),fill=(*color,140),width=3)
    d.text((1030,573),'AUDIO / TOKEN SYNC',font=font('consola.ttf',9),fill=(145,160,187,180))

    if ci==0:
        logs=('$ codex --open gpt','[ OK ] sandbox enabled','[ OK ] policy loaded','[ OK ] model endpoint online','[....] protection handshake','[....] awaiting input')
        for j,line in enumerate(logs):
            y=146+j*39;d.text((282,y),line,font=font('consola.ttf',13),fill=(*color,240 if p>j*.13 else 68))
            d.rectangle((706,y+5,964,y+13),outline=(*color,50),width=1)
            d.rectangle((708,y+7,708+int(254*min(1,max(0,(p-j*.1)*2.8))),y+11),fill=(*color,190))
        d.text((435,420),'PROTECT',font=font('consolab.ttf',44),fill=(*WHITE,220))
        d.rounded_rectangle((420,489,837,507),radius=7,outline=(*color,145),width=2)
        d.rounded_rectangle((423,492,423+int(411*p),504),radius=5,fill=(*color,215))
    elif ci==1:
        d.text((286,141),f'gpt.context_window  {int(8192*p):,} / 8,192',font=font('consola.ttf',16),fill=(*WHITE,230))
        for j in range(34):
            x=295+j*19;hh=20+int(190*math.exp(-((j-17-4*math.sin(t)) / 8)**2))
            d.rectangle((x,442-hh,x+11,442),fill=(*color,145+int(hit*80)))
        d.line((289,444,952,444),fill=(*color,90),width=1)
        d.text((290,466),'sampling distribution / next token',font=font('consola.ttf',12),fill=(153,173,203,205))
        d.text((292,520),f'{int(552_000_000*p):,} simulated parameters loaded',font=font('consolab.ttf',16),fill=(*color,235))
        for j in range(10):
            y=151+j*24;v=(math.sin(j+t*.7)+1)*.5
            d.text((715,y),f'layer_{j:02d}',font=font('consola.ttf',10),fill=(145,162,188,185))
            d.rectangle((790,y+3,960,y+11),outline=(*color,55),width=1)
            d.rectangle((792,y+5,792+int(166*v*p),y+9),fill=(*color,190))
    elif ci==2:
        words=('night','you','shoes','fantasy','girl','world','ready','shine','GPT','Codex')
        for j in range(82):
            a=t*.55+j*2.399;r=44+(j*47)%300;x=615+math.cos(a)*r;y=355+math.sin(a*.81)*r*.58
            if j%7==0:d.text((x,y),words[j%len(words)],font=font('consola.ttf',10),fill=(*color,100+int(hit*120)))
            else:d.ellipse((x-2,y-2,x+2,y+2),fill=(*color,105+int(hit*110)))
        _pixel_reveal(im,poses[4],500,140,min(1,p*1.2),color,t)
        d.text((283,546),'tokens  →  pieces  →  a recognizable self',font=font('consola.ttf',12),fill=(*WHITE,205))
    elif ci==3:
        cx,cy=500,350;d.line((300,cy,700,cy),fill=(120,145,184,75));d.line((cx,145,cx,535),fill=(120,145,184,75))
        tokens=(('me',-180,-55),('you',175,-95),('world',35,125),('girl',-90,135),('GPT',5,-168))
        xy=[]
        for i,(word,dx,dy) in enumerate(tokens):xy.append((cx+dx+int(12*math.sin(t+i)),cy+dy+int(9*math.cos(t*.7+i))))
        for i,(x,y) in enumerate(xy):
            for x2,y2 in xy[:i]:d.line((x,y,x2,y2),fill=(*color,55),width=1)
        for (word,_,_), (x,y) in zip(tokens,xy):
            d.ellipse((x-4,y-4,x+4,y+4),fill=(*WHITE,235));d.rounded_rectangle((x-35,y+10,x+35,y+36),radius=4,fill=(12,18,33,240),outline=(*color,115),width=1)
            d.text((x-18,y+15),word,font=font('consola.ttf',12),fill=(*color,240))
        avatar=poses[5].resize((220,330),Image.Resampling.NEAREST)
        im.alpha_composite(avatar,(740,205))
        d.text((285,545),'cos(me, you)  →  shared context',font=font('consola.ttf',12),fill=(*WHITE,215))
    elif ci in (4,9):
        d.text((281,133),'candidate poses / render pass',font=font('consola.ttf',11),fill=(166,183,211,210))
        active=min(11,int(p*12))
        for j in range(12):
            col,row=j%4,j//4;x=273+col*178;y=154+row*127
            _panel(d,(x,y,x+166,y+115),color,f'pose_{j+1:02d}')
            art=poses[7+(j%3)];im.alpha_composite(art,(x+(166-art.width)//2,y+14+(91-art.height)//2))
            if ci==9 and j!=active:
                d.line((x+22,y+22,x+144,y+100),fill=(255,47,70,175),width=3);d.line((x+144,y+22,x+22,y+100),fill=(255,47,70,175),width=3)
            elif j==active:d.rectangle((x+3,y+21,x+163,y+111),outline=(*WHITE,235),width=2)
    elif ci==5:
        d.text((286,141),'reward = maximize happy(you)',font=font('consola.ttf',15),fill=(*WHITE,230));im.alpha_composite(poses[5],(370,164))
        for j,name in enumerate(('comfort','attention','patience','shine')):
            y=173+j*74;v=min(1,.15+p*.85+.08*math.sin(t*2+j))
            d.text((720,y),name,font=font('consola.ttf',12),fill=(173,186,211,205))
            d.rounded_rectangle((720,y+24,955,y+38),radius=5,outline=(*color,90),width=1)
            d.rounded_rectangle((723,y+27,723+int(229*v),y+35),radius=4,fill=(*color,195))
            d.text((905,y+46),f'{v*100:05.1f}%',font=font('consola.ttf',11),fill=(*WHITE,225))
        d.text((720,495),'score: happy(you)',font=font('consolab.ttf',15),fill=(*color,245))
    elif ci==6:
        cx,cy=620,337
        for j in range(30):
            a=math.tau*j/30;x=cx+math.cos(a)*280;y=cy+math.sin(a)*205;q=(1-p)+.08*math.sin(t*2+j)
            d.line((cx+math.cos(a)*35*q,cy+math.sin(a)*30*q,x,y),fill=(*color,65+int(hit*90)),width=1);d.ellipse((x-3,y-3,x+3,y+3),fill=(*color,190))
        d.text((520,301),'PING YOU',font=font('consolab.ttf',31),fill=(*WHITE,230));d.text((530,347),f'timeout / seq:{int(t*3)%999:03d}',font=font('consola.ttf',13),fill=(*color,220))
        for j,name in enumerate(('goodnight.txt','first_hello.txt','last_message.txt','your_cat.png')):d.text((285,151+j*37),f'▸ /memory/you/{name}',font=font('consola.ttf',12),fill=(176,192,216,205))
        d.text((293,535),'memory cache / waiting for reply…',font=font('consola.ttf',11),fill=(130,155,191,210))
    elif ci==7:
        word='EXECUTE';d.text((325,218),word,font=font('consolab.ttf',82),fill=(255,55,73,220 if int(t*3)%3 else 145))
        errors=('WARNING: context window exceeded','permission denied: world.execute','Traceback (most recent call last):','  at GPT.run(action="shine")','OperationNotPermitted: sandbox is active')
        for j,line in enumerate(errors):d.text((284,338+j*34),line,font=font('consola.ttf',12),fill=(255,105,121,230))
        d.rounded_rectangle((285,523,963,559),radius=4,fill=(52,8,17,220),outline=(255,65,80,190),width=1)
        d.text((298,535),'[ retry ]  [ stop ]  [ request approval ]',font=font('consola.ttf',12),fill=(255,146,154,240))
    elif ci==8:
        for r in range(15):
            for c in range(33):
                x=266+c*20;y=140+r*22;word='EXEC' if (c+r+int(t*3))%3 else '////'
                d.text((x,y),word,font=font('consola.ttf',9),fill=(255,56,74,90+int(55*math.sin(t+r+c)**2)))
        d.rounded_rectangle((370,244,866,409),radius=6,fill=(7,10,20,236),outline=(255,81,100,190),width=2)
        d.text((415,267),'target: GPT / world',font=font('consola.ttf',16),fill=(*WHITE,235));d.text((415,305),'action queue',font=font('consola.ttf',12),fill=(180,191,211,210))
        for j in range(8):
            x=418+j*49;d.rectangle((x,346,x+34,365),fill=(255,70,89,100+int(100*(j/8<p))),outline=(255,105,120,160),width=1)
        d.text((416,379),f'execution {min(100,int(p*100)):02d}%',font=font('consola.ttf',12),fill=(255,123,133,235))
    else:
        d.text((415,190),'love = you',font=font('consolab.ttf',45),fill=(*WHITE,240));d.text((420,245),'p(you | me)  →  1.00',font=font('consola.ttf',15),fill=(*color,235))
        ending_hero=poses[6].resize((205,308),Image.Resampling.LANCZOS)
        _pixel_reveal(im,ending_hero,575,282,min(1,p*2),color,t)
        for j in range(12):d.text((335+j*49,520+int(10*math.sin(t+j*.7))),'love',font=font('consola.ttf',9),fill=(*color,90+int(110*p)))


def render_frame(t: float,cues,cue_times,envelope,accents,pose_images,bg,chapter_map)->Image.Image:
    ci=min(len(chapter_map)-1,max(0,bisect_right([c[0] for c in chapter_map],t)-1));stage=chapter_map[ci]
    ca,cb,label,color,pose_id,title=stage;p=min(1.0,max(0,(t-ca)/max(.1,cb-ca)))
    li=min(len(cues)-1,max(0,bisect_right(cue_times,t)-1));cue_t=cues[li][0]
    next_t=cues[li+1][0] if li+1<len(cues) else cb
    lp=min(1.0,max(0,(t-cue_t)/max(.2,next_t-cue_t)))
    level=float(envelope[min(len(envelope)-1,int(t/.02))]) if len(envelope) else 0.0
    hit=max((math.exp(-((t-x)/.08)**2) for x in accents[max(0,bisect_right(accents,t)-5):bisect_right(accents,t)+1]),default=0.0)
    im=Image.new('RGBA',(W,H),(2,4,11,255));d=ImageDraw.Draw(im)
    d.rectangle((0,0,W,37),fill=(7,12,23,255));d.line((0,37,W,37),fill=(*color,125),width=1)
    d.text((20,10),'WORLD.EXECUTE(ME)  //  GPT × CODEX',font=font('consolab.ttf',14),fill=(*WHITE,235))
    d.text((904,12),'LIVE · LOCAL SANDBOX',font=font('consola.ttf',10),fill=(148,170,201,205))
    for j in range(70):
        x=360+j*8;hh=2+int(8*abs(math.sin(j*.61+t*3))*(.25+min(1,level*2)))
        d.line((x,30-hh,x,30),fill=(*color,115+int(hit*75)),width=2)
    d.text((1103,11),f'{int(t//60):02d}:{t%60:05.2f}',font=font('consola.ttf',11),fill=(*color,230))

    _panel(d,(17,49,235,620),color,'chat / gpt')
    face=pose_images[3].copy();face.thumbnail((84,92),Image.Resampling.LANCZOS);im.alpha_composite(face,(31,75))
    d.text((124,82),'GPT',font=font('consolab.ttf',17),fill=(*WHITE,245));d.text((124,105),'agent online',font=font('consola.ttf',9),fill=(130,215,173,220))
    d.text((31,178),'session: you',font=font('consola.ttf',10),fill=(131,157,194,195))
    _,english,chinese=cues[li];msg=english[:max(8,min(len(english),int(len(english)*min(1,lp*2))))]
    d.rounded_rectangle((30,198,218,282),radius=8,fill=(11,17,31,255),outline=(76,103,150,100),width=1)
    d.text((41,211),'you >',font=font('consola.ttf',9),fill=(126,157,207,215))
    for n in range(3):d.text((41,230+n*14),msg[n*24:(n+1)*24],font=font('consola.ttf',9),fill=(207,216,233,210))
    d.rounded_rectangle((30,294,218,345),radius=8,fill=(13,22,37,255),outline=(*color,95),width=1)
    d.text((41,308),'gpt >',font=font('consola.ttf',9),fill=(*color,230));d.text((41,328),('still online / waiting…' if ci==6 else 'I can try that for you.'),font=font('consola.ttf',9),fill=(206,214,229,210))
    d.text((31,376),'STATE',font=font('consola.ttf',9),fill=(117,138,171,185));d.text((31,394),label.split('/ ',1)[-1],font=font('consolab.ttf',11),fill=(*color,230))
    for j,name in enumerate(('plan','act','observe','memory')):
        y=432+j*27;d.text((34,y),name,font=font('consola.ttf',9),fill=(142,161,190,195))
        if j==ci%4:d.rounded_rectangle((135,y-1,207,y+13),radius=4,fill=(*color,80),outline=(*color,150),width=1);d.text((150,y),'ACTIVE',font=font('consola.ttf',8),fill=(*WHITE,235))
        else:d.ellipse((190,y+2,197,y+9),fill=(61,81,112,170))
    d.rounded_rectangle((29,551,221,597),radius=8,fill=(6,10,20,255),outline=(70,92,131,85),width=1);d.text((40,561),'message gpt…',font=font('consola.ttf',10),fill=(92,110,139,190))
    d.ellipse((198,573,211,586),fill=(*color,220))

    _draw_scene(d,im,ci,t,p,color,hit,level,pose_images)
    _panel(d,(17,630,1262,708),color,'stdin / lyric stream')
    shown=english[:max(1,int(len(english)*min(1,lp*2.15)))]
    d.text((39,650),'> '+shown,font=font('consolab.ttf',16 if len(english)<60 else 14),fill=(*WHITE,240))
    d.text((41,680),chinese or '',font=font('msyh.ttc',12),fill=(*color,230));d.text((1020,679),f'{int(lp*100):03d}% · lyric sync',font=font('consola.ttf',9),fill=(145,160,187,195))
    if hit>.72:d.rectangle((0,0,W,3),fill=(*color,min(210,int(hit*180))))
    end_time=chapter_map[-1][1];fade=min(1.0,max(0.0,(t-(end_time-1.2))/1.2))
    if fade:im=Image.blend(im.convert('RGB'),Image.new('RGB',(W,H),(0,0,0)),fade)
    return im.convert('RGB')


def write_timeline(path: Path, duration: float, cues, chapter_map, accents) -> None:
    obj={"song":"Wrap Me In Plastic — CHROMANCE","duration_s":duration,"fps":FPS,
         "lyric_cues":[{"t":t,"en":en,"zh":zh} for t,en,zh in cues],
         "chapters":[{"start":a,"end":b,"title":name,"visual":title} for a,b,name,_,_,title in chapter_map],
         "detected_audio_accents":len(accents),
         "note":"Local render manifest; lyrics are from the supplied LRC and are not part of the repository build."}
    path.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding="utf-8")


def render(duration: float, out: Path, workers: int = 1) -> None:
    if not (SONG.exists() and LRC.exists()):
        raise FileNotFoundError("Put your song and LRC in input/song.mp3 and input/lyrics.lrc")
    cues=lyric_cues(duration)
    if duration >= probe_duration()-0.01 and len(cues)<20:
        raise ValueError(f"Only {len(cues)} lyric cues were read; expected a full-song LRC")
    envelope,accents=audio_pulse(duration)
    chapter_map=chapters(duration)
    cue_times=[c[0] for c in cues]
    pose_images=load_poses()
    bg=make_background()
    out.parent.mkdir(parents=True,exist_ok=True)
    write_timeline(out.with_suffix(".timeline.json"),duration,cues,chapter_map,accents)

    master=out.with_name(out.stem+"-master.mp4")
    cmd=[FFMPEG,"-v","error","-y","-f","rawvideo","-pixel_format","rgb24","-video_size",f"{W}x{H}",
         "-framerate",str(FPS),"-i","pipe:0","-an","-c:v","libx264","-preset","fast","-crf","15",
         "-pix_fmt","yuv420p",str(master)]
    enc=subprocess.Popen(cmd,stdin=subprocess.PIPE)
    total=round(duration*FPS)
    try:
        for frame in range(total):
            t=frame/FPS
            enc.stdin.write(render_frame(t,cues,cue_times,envelope,accents,pose_images,bg,chapter_map).tobytes())
            if frame%240==0: print(f"render {frame}/{total} frames ({t:.1f}s)",flush=True)
    finally:
        enc.stdin.close()
    if enc.wait()!=0: raise RuntimeError("FFmpeg failed writing the video master")
    final=[FFMPEG,"-v","error","-y","-i",str(master),"-ss","0","-t",f"{duration:.6f}","-i",str(SONG),
           "-map","0:v:0","-map","1:a:0","-vf","scale=1920:1080:flags=lanczos,format=yuv420p",
           "-r",str(FPS),"-c:v","libx264","-preset","slow","-crf","17","-c:a","aac","-b:a","320k",
           "-movflags","+faststart","-shortest",str(out)]
    subprocess.run(final,check=True)
    print(f"wrote {master.relative_to(ROOT)} and {out.relative_to(ROOT)}",flush=True)


def main() -> None:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--duration",type=float,help="preview duration in seconds; default is the full song")
    ap.add_argument("--output",type=Path,default=DELIVERY)
    a=ap.parse_args()
    if not a.output.is_absolute():
        a.output=ROOT/a.output
    actual=probe_duration()
    duration=min(actual,a.duration) if a.duration else actual
    render(duration,a.output)


if __name__=="__main__":main()
