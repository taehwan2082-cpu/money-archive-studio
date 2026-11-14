import glob
import json
import os
import subprocess
import sys

try:
    from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

sys.stdout.reconfigure(encoding="utf-8")

STUDIO_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_BLACK_HAN = os.path.join(STUDIO_DIR, "branding", "fonts", "BlackHanSans-Regular.ttf")
FONT_HEAVY = os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Windows\Fonts\NanumSquareNeo-eHv.ttf")
FONT_MALGUN_BOLD = r"C:\Windows\Fonts\malgunbd.ttf"

PALETTES = {
    "white": ((255, 255, 255), (225, 235, 250)),
    "yellow": ((255, 245, 75), (255, 185, 0)),
    "red": ((255, 95, 70), (225, 18, 18)),
    "cyan": ((135, 248, 255), (25, 185, 245)),
}


def render_thumb_ffmpeg_fallback(bg_path: str, out_jpg: str, top_tag: str, shock_badge: str, line1: str, line2: str):
    os.makedirs(os.path.dirname(out_jpg), exist_ok=True)
    ass_path = out_jpg + ".temp_thumb.ass"
    ass_content = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1280
PlayResY: 720
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: TopBadge,Malgun Gothic,38,&H00FFFFFF,&H0000FFFF,&H001814DF,&H001814DF,-1,0,0,0,100,100,1,0,3,13,0,7,38,38,34,1
Style: ShockBox,Malgun Gothic,42,&H0000DCFF,&H0000FFFF,&H00101018,&H00101018,-1,0,0,0,100,100,1,0,3,13,0,9,38,38,34,1
Style: MainWhite,Malgun Gothic,86,&H00FFFFFF,&H0000FFFF,&H00000000,&HD8000000,-1,0,0,0,100,100,-2,0,1,13,6,5,20,20,20,1
Style: MainYellow,Malgun Gothic,94,&H0000DCFF,&H0000FFFF,&H00000000,&HD8000000,-1,0,0,0,100,100,-2,0,1,14,7,5,20,20,20,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 2,0:00:00.00,0:00:05.00,TopBadge,,0,0,0,,  {top_tag}  
Dialogue: 2,0:00:00.00,0:00:05.00,ShockBox,,0,0,0,,  {shock_badge}  
Dialogue: 3,0:00:00.00,0:00:05.00,MainWhite,,0,0,0,,{{\\an5\\pos(640,518)}}{line1}
Dialogue: 4,0:00:00.00,0:00:05.00,MainYellow,,0,0,0,,{{\\an5\\pos(640,632)}}{line2}
"""
    with open(ass_path, "w", encoding="utf-8-sig") as f:
        f.write(ass_content)
    ass_esc = ass_path.replace("\\", "/").replace(":", "\\:")
    vf = (
        "scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,"
        "eq=contrast=1.12:saturation=1.18,vignette=PI/5.2,"
        f"ass='{ass_esc}'"
    )
    subprocess.run(
        ["ffmpeg", "-y", "-i", bg_path, "-vf", vf, "-frames:v", "1", "-q:v", "2", out_jpg],
        check=True,
        capture_output=True,
    )
    if os.path.exists(ass_path):
        os.remove(ass_path)
    print(f"[THUMB OK (FFmpeg)] {out_jpg} ({os.path.getsize(out_jpg):,} bytes)", flush=True)


def build_thumbnail_card(
    bg_path: str,
    out_jpg: str,
    top_tag: str,
    shock_badge: str,
    line1_segs: list[tuple[str, str]],
    line2_segs: list[tuple[str, str]],
):
    if not HAS_PIL:
        l1 = "".join(s[0] for s in line1_segs)
        l2 = "".join(s[0] for s in line2_segs)
        render_thumb_ffmpeg_fallback(bg_path, out_jpg, top_tag, shock_badge, l1, l2)
        return

    def get_font(size: int):
        for fp in (FONT_BLACK_HAN, FONT_HEAVY, FONT_MALGUN_BOLD):
            if os.path.exists(fp):
                return ImageFont.truetype(fp, size)
        return ImageFont.load_default()

    im = Image.open(bg_path).convert("RGB")
    target_w, target_h = 1280, 720
    scale = max(target_w / im.width, target_h / im.height)
    nw, nh = int(round(im.width * scale)), int(round(im.height * scale))
    im = im.resize((nw, nh), Image.Resampling.LANCZOS)
    lx = (nw - target_w) // 2
    ty = (nh - target_h) // 2
    im = im.crop((lx, ty, lx + target_w, ty + target_h))

    im = ImageEnhance.Contrast(im).enhance(1.16)
    im = ImageEnhance.Color(im).enhance(1.18)
    im = ImageEnhance.Sharpness(im).enhance(1.25)
    canvas = im.convert("RGBA")

    bot_h = 330
    grad = Image.new("L", (1, bot_h))
    for y in range(bot_h):
        grad.putpixel((0, y), max(0, min(255, int(238 * (y / max(1, bot_h - 1))))))
    grad_mask = grad.resize((target_w, bot_h))
    black_strip = Image.new("RGBA", (target_w, bot_h), (4, 6, 12, 255))
    bot_overlay = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 0))
    bot_overlay.paste(black_strip, (0, target_h - bot_h), grad_mask)
    canvas = Image.alpha_composite(canvas, bot_overlay)

    l1 = "".join(s[0] for s in line1_segs)
    l2 = "".join(s[0] for s in line2_segs)
    render_thumb_ffmpeg_fallback(bg_path, out_jpg, top_tag, shock_badge, l1, l2)


def build_from_queue(target_ep_id: str = ""):
    queue_path = os.path.join(STUDIO_DIR, "auto_pipeline", "episode_queue.json")
    if not os.path.exists(queue_path):
        return
    q = json.load(open(queue_path, "r", encoding="utf-8"))
    for item in q.get("episodes", []):
        ep_id = item.get("ep_id", "")
        if target_ep_id and ep_id != target_ep_id:
            continue
        if not item.get("thumb_top") or not item.get("thumb_bot"):
            continue
        ep_dir = os.path.join(STUDIO_DIR, ep_id)
        if not os.path.isdir(ep_dir):
            continue
        raw_dir = os.path.join(ep_dir, "raw_images")
        cands = (
            glob.glob(os.path.join(raw_dir, "*thumb*.jpg"))
            + glob.glob(os.path.join(raw_dir, "*thumb*.png"))
            + glob.glob(os.path.join(raw_dir, "*.jpg"))
        )
        if not cands:
            continue
        prefix = ep_id.split("_")[0].upper()
        out_jpg = os.path.join(ep_dir, f"{prefix}_썸네일_머니아카이브_1280x720.jpg")
        build_thumbnail_card(
            bg_path=cands[0],
            out_jpg=out_jpg,
            top_tag=item.get("thumb_badge", "#금융실화"),
            shock_badge=item.get("thumb_shock", "충격 실화!"),
            line1_segs=[(item["thumb_top"], "white")],
            line2_segs=[(item["thumb_bot"], "yellow")],
        )


def main():
    target_ep = sys.argv[1] if len(sys.argv) > 1 else ""
    if target_ep:
        build_from_queue(target_ep)
        return
    build_from_queue()


if __name__ == "__main__":
    main()
