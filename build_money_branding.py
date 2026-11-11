import os
import shutil
import subprocess

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_DIR = os.path.join(BASE_DIR, "raw_images")
BRAND_DIR = os.path.join(BASE_DIR, "branding")
UPLOAD_STAGE_DIR = r"C:\Users\이태환\.gemini\antigravity\brain\f21565db-f075-40e3-b2c4-522024860a84\browser_sandbox\uploads"
os.makedirs(BRAND_DIR, exist_ok=True)
os.makedirs(UPLOAD_STAGE_DIR, exist_ok=True)


def build_branding():
    prof_src = os.path.join(RAW_DIR, "branding_profile_emblem.jpg")
    ban_src = os.path.join(RAW_DIR, "branding_banner_bg.jpg")

    prof_out = os.path.join(BRAND_DIR, "01_채널프로필_머니아카이브_800x800.png")
    subprocess.run([
        "ffmpeg", "-y", "-i", prof_src,
        "-vf", "scale=800:800:force_original_aspect_ratio=increase,crop=800:800",
        prof_out
    ], check=True, capture_output=True)

    wm_out = os.path.join(BRAND_DIR, "03_영상구독워터마크_150x150.png")
    subprocess.run([
        "ffmpeg", "-y", "-i", prof_src,
        "-vf", "scale=150:150:force_original_aspect_ratio=increase,crop=150:150",
        wm_out
    ], check=True, capture_output=True)

    ass_path = os.path.join(BRAND_DIR, "banner_kr.ass")
    ass_content = """[Script Info]
ScriptType: v4.00+
PlayResX: 2560
PlayResY: 1440
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: TopTag,Impact,38,&H0000D4FF,&H0000FFFF,&H00000000,&HB4000000,-1,0,0,0,100,100,7,0,1,4,2,5,100,100,0,1
Style: MainTitle,Malgun Gothic,126,&H00FFFFFF,&H0000FFFF,&H00000000,&HC8000000,-1,0,0,0,100,100,16,0,1,9,5,5,100,100,0,1
Style: SubTitle,Malgun Gothic,44,&H003830F0,&H0000FFFF,&H00000000,&HB4000000,-1,0,0,0,100,100,4,0,1,5,3,5,100,100,0,1
Style: DescLine,Malgun Gothic,34,&H00E8E8E8,&H0000FFFF,&H00000000,&H96000000,-1,0,0,0,100,100,2,0,3,10,0,5,100,100,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,0:00:05.00,TopTag,,0,0,0,,{\\pos(1280,555)}FINANCIAL THRILLER DOCUMENTARY
Dialogue: 0,0:00:00.00,0:00:05.00,MainTitle,,0,0,0,,{\\pos(1280,668)}머 니  아 카 이 브
Dialogue: 0,0:00:00.00,0:00:05.00,SubTitle,,0,0,0,,{\\pos(1280,786)}거대 기업의 몰락 · 희대의 금융 사건 · 자본의 그림자
Dialogue: 0,0,00:00.00,0:00:05.00,DescLine,,0,0,0,,{\\pos(1280,866)}  돈과 탐욕이 남긴 충격적인 실화 기록을 복원합니다  
"""
    # Fix typo in Dialogue line 4 timestamp format:
    ass_content = ass_content.replace("Dialogue: 0,0,00:00.00,", "Dialogue: 0,0:00:00.00,")
    with open(ass_path, "w", encoding="utf-8-sig") as f:
        f.write(ass_content)

    ass_esc = ass_path.replace("\\", "/").replace(":", "\\:")
    ban_out = os.path.join(BRAND_DIR, "02_한국채널_배너_머니아카이브_2560x1440.jpg")
    subprocess.run([
        "ffmpeg", "-y", "-i", ban_src,
        "-vf", (
            "scale=2560:1440:force_original_aspect_ratio=increase,crop=2560:1440,"
            "drawbox=x=0:y=485:w=2560:h=470:color=black@0.58:t=fill,"
            f"ass='{ass_esc}'"
        ),
        "-frames:v", "1", "-q:v", "2",
        ban_out
    ], check=True, capture_output=True)

    # Copy to browser_sandbox/uploads for YouTube Studio customization
    shutil.copyfile(prof_out, os.path.join(UPLOAD_STAGE_DIR, "money_archive_avatar.png"))
    shutil.copyfile(ban_out, os.path.join(UPLOAD_STAGE_DIR, "money_archive_banner.jpg"))
    print("Branding built & staged successfully:", prof_out, ban_out)


if __name__ == "__main__":
    build_branding()
