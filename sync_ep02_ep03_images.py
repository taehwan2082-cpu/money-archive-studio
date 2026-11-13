import glob
import os
import shutil

BRAIN_DIR = r"C:\Users\USER\.gemini\antigravity\brain\3aeed358-b540-4b1f-a337-0d67ae30d615"
STUDIO_DIR = os.path.dirname(os.path.abspath(__file__))

EP02_PREFIXES = [
    "thumb_bill_hwang",
    "ep02_s01_manhattan_dawn_margin",
    "ep02_s02_bible_and_bloomberg",
    "ep02_s03_tiger_asia_sec_ban",
    "ep02_s04_family_office_loophole",
    "ep02_s05_trs_swap_illusion",
    "ep02_s06_viacom_rocket_bubble",
    "ep02_s07_viacom_offering_crack",
    "ep02_s08_secret_bankers_meeting",
    "ep02_s09_goldman_dawn_fire_sale",
    "ep02_s10_credit_suisse_collapse",
    "ep02_s11_manhattan_federal_court",
]

EP03_PREFIXES = [
    "thumb_jho_low",
    "ep03_s01_equanimity_superyacht",
    "ep03_s02_wharton_fake_prince",
    "ep03_s03_kuala_lumpur_1mdb_palace",
    "ep03_s04_shell_company_wire_transfer",
    "ep03_s05_goldman_bond_vault",
    "ep03_s06_vegas_hollywood_party",
    "ep03_s07_crystal_piano_diamonds",
    "ep03_s08_journalist_leaked_drive",
    "ep03_s09_mansion_cash_raid",
    "ep03_s10_doj_goldman_settlement",
    "ep03_s11_fugitive_shadow_macau",
]


def sync_set(ep_folder: str, prefixes: list[str]):
    dst_dir = os.path.join(STUDIO_DIR, ep_folder, "raw_images")
    os.makedirs(dst_dir, exist_ok=True)
    for pfx in prefixes:
        matches = sorted(glob.glob(os.path.join(BRAIN_DIR, f"{pfx}_*.*")))
        if not matches:
            raise FileNotFoundError(f"Missing generated image for {pfx} in {BRAIN_DIR}")
        src = matches[-1]
        dst = os.path.join(dst_dir, f"{pfx}.jpg")
        shutil.copyfile(src, dst)
    print(f"[SYNC OK] {len(prefixes)} images -> {dst_dir}")


if __name__ == "__main__":
    sync_set("ep02_archegos_kr", EP02_PREFIXES)
    sync_set("ep03_jholow_kr", EP03_PREFIXES)
