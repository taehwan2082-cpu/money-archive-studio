import glob
import os
import shutil

BRAIN_DIR = r"C:\Users\이태환\.gemini\antigravity\brain\f21565db-f075-40e3-b2c4-522024860a84"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_DIR = os.path.join(BASE_DIR, "raw_images")
os.makedirs(RAW_DIR, exist_ok=True)

PREFIXES = [
    "branding_profile_emblem",
    "branding_banner_bg",
    "thumb_smiling_trader",
    "ch1_changi_airport_rain",
    "ch1_sorry_note_desk",
    "ch1_barings_london_bank",
    "ch2_jakarta_paper_mountain",
    "ch2_simex_trading_pit",
    "ch2_dual_key_desk",
    "ch3_account_88888_crt",
    "ch3_london_champagne_boardroom",
    "ch3_ignored_audit_report",
    "ch4_kobe_earthquake_1995",
    "ch4_nikkei_crash_panic",
    "ch4_frankfurt_arrest_stage",
    "ch5_paris_socgen_tower",
    "ch5_kerviel_ghost_terminal",
    "ch6_french_courtroom_gavel",
]

copied = 0
for pfx in PREFIXES:
    matches = sorted(glob.glob(os.path.join(BRAIN_DIR, f"{pfx}_*.*")))
    if not matches:
        raise FileNotFoundError(f"Could not find generated image for prefix: {pfx}")
    src = matches[-1]
    dst = os.path.join(RAW_DIR, f"{pfx}.jpg")
    shutil.copyfile(src, dst)
    copied += 1

print(f"Successfully synced {copied} generated images into {RAW_DIR}")
