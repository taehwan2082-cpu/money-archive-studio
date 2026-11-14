import os
import sys
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

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


def get_font(size: int) -> ImageFont.FreeTypeFont:
    for fp in (FONT_BLACK_HAN, FONT_HEAVY, FONT_MALGUN_BOLD):
        if os.path.exists(fp):
            return ImageFont.truetype(fp, size)
    return ImageFont.load_default()


def make_vertical_gradient_mask(w: int, h: int, top_alpha: int, bot_alpha: int) -> Image.Image:
    grad = Image.new("L", (1, h))
    for y in range(h):
        a = int(top_alpha + (bot_alpha - top_alpha) * (y / max(1, h - 1)))
        grad.putpixel((0, y), max(0, min(255, a)))
    return grad.resize((w, h))


def render_3d_gradient_line(
    canvas: Image.Image,
    y_top: int,
    segments: list[tuple[str, str]],
    font_size: int,
    stroke_width: int = 13,
) -> Image.Image:
    w, h = canvas.size
    font = get_font(font_size)
    dummy = ImageDraw.Draw(Image.new("RGBA", (10, 10)))

    metrics = []
    total_w = 0.0
    for txt, pal_key in segments:
        adv = dummy.textlength(txt, font=font)
        bb = dummy.textbbox((0, 0), txt, font=font, stroke_width=stroke_width)
        metrics.append((txt, pal_key, adv, bb))
        total_w += adv

    # Auto-shrink slightly if wider than 1210px
    if total_w > 1210:
        font_size = int(font_size * (1200 / total_w))
        font = get_font(font_size)
        metrics = []
        total_w = 0.0
        for txt, pal_key in segments:
            adv = dummy.textlength(txt, font=font)
            bb = dummy.textbbox((0, 0), txt, font=font, stroke_width=stroke_width)
            metrics.append((txt, pal_key, adv, bb))
            total_w += adv

    start_x = (w - int(total_w)) // 2

    shadow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    stroke = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    fill_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))

    ds = ImageDraw.Draw(shadow)
    dk = ImageDraw.Draw(stroke)

    cur_x = float(start_x)
    for txt, pal_key, adv, bb in metrics:
        ix = int(round(cur_x))
        ds.text(
            (ix, y_top + 10),
            txt,
            font=font,
            fill=(0, 0, 0, 240),
            stroke_width=stroke_width + 6,
            stroke_fill=(0, 0, 0, 240),
        )
        for depth in range(8, 0, -1):
            dk.text(
                (ix + depth // 2, y_top + depth),
                txt,
                font=font,
                fill=(8, 10, 16, 255),
                stroke_width=stroke_width,
                stroke_fill=(8, 10, 16, 255),
            )
        dk.text(
            (ix, y_top),
            txt,
            font=font,
            fill=(0, 0, 0, 255),
            stroke_width=stroke_width,
            stroke_fill=(0, 0, 0, 255),
        )

        # Gradient interior fill
        mask = Image.new("L", (w, h), 0)
        dm = ImageDraw.Draw(mask)
        dm.text((ix, y_top), txt, font=font, fill=255)

        c_top, c_bot = PALETTES[pal_key]
        gh = max(20, bb[3] - bb[1])
        grad_strip = Image.new("RGBA", (w, gh))
        for gy in range(gh):
            r = int(c_top[0] + (c_bot[0] - c_top[0]) * (gy / max(1, gh - 1)))
            g = int(c_top[1] + (c_bot[1] - c_top[1]) * (gy / max(1, gh - 1)))
            b = int(c_top[2] + (c_bot[2] - c_top[2]) * (gy / max(1, gh - 1)))
            ImageDraw.Draw(grad_strip).line([(0, gy), (w, gy)], fill=(r, g, b, 255))

        color_full = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        color_full.paste(grad_strip, (0, max(0, y_top + bb[1])))
        seg_filled = Image.composite(color_full, Image.new("RGBA", (w, h), (0, 0, 0, 0)), mask)
        fill_layer = Image.alpha_composite(fill_layer, seg_filled)
        cur_x += adv

    shadow = shadow.filter(ImageFilter.GaussianBlur(9))
    out = Image.alpha_composite(canvas, shadow)
    out = Image.alpha_composite(out, stroke)
    return Image.alpha_composite(out, fill_layer)


def draw_top_badge(canvas: Image.Image, text: str, x: int = 34, y: int = 28) -> Image.Image:
    font = get_font(40)
    d = ImageDraw.Draw(canvas)
    bb = d.textbbox((0, 0), text, font=font)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    pad_x, pad_y = 24, 14
    box = (x, y, x + tw + pad_x * 2, y + th + pad_y * 2)

    overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    do = ImageDraw.Draw(overlay)
    do.rounded_rectangle(box, radius=12, fill=(185, 16, 20, 242), outline=(255, 225, 65, 255), width=4)
    do.text((x + pad_x, y + pad_y - bb[1]), text, font=font, fill=(255, 248, 120, 255), stroke_width=3, stroke_fill=(0, 0, 0, 220))
    return Image.alpha_composite(canvas, overlay)


def draw_shock_callout_box(canvas: Image.Image, text: str, right_x: int = 1244, y: int = 34) -> Image.Image:
    font = get_font(52)
    d = ImageDraw.Draw(canvas)
    bb = d.textbbox((0, 0), text, font=font)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    pad_x, pad_y = 26, 15
    x1 = right_x - (tw + pad_x * 2)
    box = (x1, y, right_x, y + th + pad_y * 2)

    glow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    dg = ImageDraw.Draw(glow)
    dg.rounded_rectangle((box[0] - 6, box[1] - 6, box[2] + 6, box[3] + 6), radius=18, fill=(255, 30, 15, 150))
    glow = glow.filter(ImageFilter.GaussianBlur(10))

    fg = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    df = ImageDraw.Draw(fg)
    df.rounded_rectangle(box, radius=14, fill=(14, 16, 24, 238), outline=(255, 65, 45, 255), width=5)
    df.text(
        (x1 + pad_x, y + pad_y - bb[1]),
        text,
        font=font,
        fill=(255, 240, 65, 255),
        stroke_width=5,
        stroke_fill=(0, 0, 0, 255),
    )
    out = Image.alpha_composite(canvas, glow)
    return Image.alpha_composite(out, fg)


def build_thumbnail_card(
    bg_path: str,
    out_jpg: str,
    top_tag: str,
    shock_badge: str,
    line1_segs: list[tuple[str, str]],
    line2_segs: list[tuple[str, str]],
):
    im = Image.open(bg_path).convert("RGB")
    # Center-crop/resize to 1280x720
    target_w, target_h = 1280, 720
    scale = max(target_w / im.width, target_h / im.height)
    nw, nh = int(round(im.width * scale)), int(round(im.height * scale))
    im = im.resize((nw, nh), Image.Resampling.LANCZOS)
    lx = (nw - target_w) // 2
    ty = (nh - target_h) // 2
    im = im.crop((lx, ty, lx + target_w, ty + target_h))

    # Boost contrast & color pop
    im = ImageEnhance.Contrast(im).enhance(1.16)
    im = ImageEnhance.Color(im).enhance(1.18)
    im = ImageEnhance.Sharpness(im).enhance(1.25)
    canvas = im.convert("RGBA")

    # Smooth bottom cinematic gradient for crystal-clear headline legibility
    bot_h = 330
    grad_mask = make_vertical_gradient_mask(target_w, bot_h, 0, 238)
    black_strip = Image.new("RGBA", (target_w, bot_h), (4, 6, 12, 255))
    bot_overlay = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 0))
    bot_overlay.paste(black_strip, (0, target_h - bot_h), grad_mask)
    canvas = Image.alpha_composite(canvas, bot_overlay)

    # Top badge + numeric shock callout
    canvas = draw_top_badge(canvas, top_tag)
    canvas = draw_shock_callout_box(canvas, shock_badge)

    # Giant 2-line 3D extruded viral headlines
    canvas = render_3d_gradient_line(canvas, y_top=458, segments=line1_segs, font_size=98, stroke_width=13)
    canvas = render_3d_gradient_line(canvas, y_top=578, segments=line2_segs, font_size=106, stroke_width=14)

    os.makedirs(os.path.dirname(out_jpg), exist_ok=True)
    canvas.convert("RGB").save(out_jpg, "JPEG", quality=95, subsampling=0)
    print(f"[THUMB OK] {out_jpg} ({os.path.getsize(out_jpg):,} bytes)", flush=True)


def main():
    # 1. EP01 v3 Upgraded Documentary Object Thumbnail (Zero fake AI smiling face -> Secret 88888 CRT Terminal!)
    ep01_bg = os.path.join(STUDIO_DIR, "raw_images", "ch3_account_88888_crt.jpg")
    if os.path.exists(ep01_bg):
        build_thumbnail_card(
            bg_path=ep01_bg,
            out_jpg=os.path.join(STUDIO_DIR, "ep01_barings_kr", "EP01_썸네일_v2_머니아카이브_1280x720.jpg"),
            top_tag="#비밀계좌88888_실화",
            shock_badge="왕실은행 1,700원 파산!",
            line1_segs=[("실수 3천만 원 ", "white"), ("숨기려다", "yellow")],
            line2_segs=[("233년 은행 박살 낸 신입!", "red")],
        )

    # 2. EP02 Bill Hwang & Archegos Thumbnail
    ep02_bg = os.path.join(STUDIO_DIR, "ep02_archegos_kr", "raw_images", "thumb_bill_hwang.jpg")
    if os.path.exists(ep02_bg):
        build_thumbnail_card(
            bg_path=ep02_bg,
            out_jpg=os.path.join(STUDIO_DIR, "ep02_archegos_kr", "EP02_썸네일_머니아카이브_1280x720.jpg"),
            top_tag="#월가충격_아케고스",
            shock_badge="48시간 -28조 증발!",
            line1_segs=[("단 이틀 만에 ", "white"), ("28조 날린", "red")],
            line2_segs=[("월가 속인 한국인의 최후!", "yellow")],
        )

    # 3. EP03 Jho Low & 1MDB Thumbnail
    ep03_bg = os.path.join(STUDIO_DIR, "ep03_jholow_kr", "raw_images", "thumb_jho_low.jpg")
    if os.path.exists(ep03_bg):
        build_thumbnail_card(
            bg_path=ep03_bg,
            out_jpg=os.path.join(STUDIO_DIR, "ep03_jholow_kr", "EP03_썸네일_머니아카이브_1280x720.jpg"),
            top_tag="#나랏돈6조_희대의사기",
            shock_badge="국고 -6조 원 증발!",
            line1_segs=[("나랏돈 6조 털어 ", "white"), ("영화 찍고", "red")],
            line2_segs=[("증발한 27살 사기꾼!", "yellow")],
        )


if __name__ == "__main__":
    main()
