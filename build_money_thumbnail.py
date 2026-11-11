import os
import subprocess

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_DIR = os.path.join(BASE_DIR, "raw_images")
EP1_DIR = os.path.join(BASE_DIR, "ep01_barings_kr")
ASSETS_DIR = os.path.join(EP1_DIR, "assets")
os.makedirs(ASSETS_DIR, exist_ok=True)


def build_ep01_thumbnail():
    bg_src = os.path.join(RAW_DIR, "thumb_smiling_trader.jpg")
    ass_path = os.path.join(ASSETS_DIR, "thumb_ep01.ass")

    # Benchmarked against 3.39M & 662K view Korean financial outlier thumbnails:
    # Top-left hashtag badge + smiling trader irony + giant 2-line white/yellow high-contrast copy at bottom!
    ass_content = """[Script Info]
ScriptType: v4.00+
PlayResX: 1280
PlayResY: 720
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: TopBadge,Malgun Gothic,42,&H0000F0FF,&H0000FFFF,&H001818B0,&HDC1818B0,-1,0,0,0,100,100,1,0,3,12,0,7,38,38,34,1
Style: Line1White,Malgun Gothic,98,&H00FFFFFF,&H0000FFFF,&H00000000,&HF0000000,-1,0,0,0,103,100,-2,0,1,12,5,5,20,20,0,1
Style: Line2Yellow,Malgun Gothic,108,&H0000E8FF,&H0000FFFF,&H00000000,&HF0000000,-1,0,0,0,104,100,-2,0,1,13,6,5,20,20,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 1,0:00:00.00,0:00:05.00,TopBadge,,0,0,0,,  #역대최악_금융사고  
Dialogue: 1,0:00:00.00,0:00:05.00,Line1White,,0,0,0,,{\\pos(640,530)}233년 왕실 은행 박살 낸
Dialogue: 1,0:00:00.00,0:00:05.00,Line2Yellow,,0,0,0,,{\\pos(640,646)}28살 고졸 신입의 최후!
"""
    with open(ass_path, "w", encoding="utf-8-sig") as f:
        f.write(ass_content)

    ass_esc = ass_path.replace("\\", "/").replace(":", "\\:")
    out_jpg = os.path.join(EP1_DIR, "EP01_썸네일_머니아카이브_1280x720.jpg")
    subprocess.run([
        "ffmpeg", "-y", "-i", bg_src,
        "-vf", (
            "scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,"
            "drawbox=x=0:y=455:w=1280:h=265:color=black@0.55:t=fill,"
            "eq=contrast=1.10:saturation=1.12,"
            f"ass='{ass_esc}'"
        ),
        "-frames:v", "1", "-q:v", "2",
        out_jpg
    ], check=True, capture_output=True)
    print("Created Outlier-Benchmarked EP01 Thumbnail:", out_jpg)


if __name__ == "__main__":
    build_ep01_thumbnail()
