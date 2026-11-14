import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
import re
import struct
import subprocess
import sys
import wave

sys.stdout.reconfigure(encoding="utf-8")

STUDIO_DIR = os.path.dirname(os.path.abspath(__file__))
SFX_DIR = os.path.join(STUDIO_DIR, "ep01_barings_kr", "assets", "sfx")
BGM_SRC_DIR = os.path.abspath(
    os.path.join(STUDIO_DIR, "..", "mystery-doc-studio", "ep01_kola_kr", "assets", "real_archive")
)

MOTIONS = ["zoom_in", "pan_right", "zoom_out", "pan_left", "plunge_down", "rise_up"]

EPISODE_CONFIGS = {
    "ep02": {
        "dir_name": "ep02_archegos_kr",
        "out_long_mp4": "머니아카이브_EP02_빌황_아케고스28조증발_본편.mp4",
        "out_shorts_mp4": "머니아카이브_EP02_빌황_아케고스28조증발_쇼츠_9x16.mp4",
        "scene_images": [
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
        ],
        "shorts_hook_1": "단 48시간 만에 28조 증발!",
        "shorts_hook_2": "월가 은행 박살 낸 한국인의 정체",
        "shorts_visual_cycle": [
            "thumb_bill_hwang",
            "ep02_s01_manhattan_dawn_margin",
            "ep02_s02_bible_and_bloomberg",
            "ep02_s05_trs_swap_illusion",
            "ep02_s06_viacom_rocket_bubble",
            "ep02_s07_viacom_offering_crack",
            "ep02_s08_secret_bankers_meeting",
            "ep02_s09_goldman_dawn_fire_sale",
            "ep02_s10_credit_suisse_collapse",
            "ep02_s11_manhattan_federal_court",
        ],
        "chapters": [
            (0.00, 0.15, "48시간 28조 증발 미스터리"),
            (0.15, 0.34, "블랙리스트 퇴출과 패밀리 오피스 부활"),
            (0.34, 0.54, "월가 6대 은행을 속인 익명 파생상품 TRS"),
            (0.54, 0.69, "130조 레버리지 폭주와 유상증자 균열"),
            (0.69, 0.87, "목요일 밤의 배신 · 새벽 6시 폭탄 투매"),
            (0.87, 1.00, "167년 은행의 몰락과 징역 18년 심판"),
        ],
        "highlights": [
            r"\d[\d,\.]*\s*(?:조\s*원|천억\s*원|억\s*원|만\s*원|원|달러|시간|일|년|배|곳|%)",
            r"빌 황",
            r"황성국",
            r"아케고스",
            r"총수익스왑",
            r"TRS",
            r"패밀리 오피스",
            r"골드만삭스",
            r"모건스탠리",
            r"크레디트스위스",
            r"죄수의 딜레마",
        ],
    },
    "ep03": {
        "dir_name": "ep03_jholow_kr",
        "out_long_mp4": "머니아카이브_EP03_조로우_1MDB_6조횡령_본편.mp4",
        "out_shorts_mp4": "머니아카이브_EP03_조로우_1MDB_6조횡령_쇼츠_9x16.mp4",
        "scene_images": [
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
        ],
        "shorts_hook_1": "나랏돈 6조 통째로 털어서",
        "shorts_hook_2": "영화 찍고 증발한 27살 사기꾼!",
        "shorts_visual_cycle": [
            "thumb_jho_low",
            "ep03_s01_equanimity_superyacht",
            "ep03_s02_wharton_fake_prince",
            "ep03_s03_kuala_lumpur_1mdb_palace",
            "ep03_s04_shell_company_wire_transfer",
            "ep03_s05_goldman_bond_vault",
            "ep03_s06_vegas_hollywood_party",
            "ep03_s07_crystal_piano_diamonds",
            "ep03_s09_mansion_cash_raid",
            "ep03_s11_fugitive_shadow_macau",
        ],
        "chapters": [
            (0.00, 0.16, "아시아 개츠비와 나랏돈 6조의 비밀"),
            (0.16, 0.34, "와튼스쿨 가짜 왕자 작전과 1MDB 탄생"),
            (0.34, 0.56, "유령 계좌 '굿 스타'와 골드만삭스의 탐욕"),
            (0.56, 0.74, "울프 오브 월스트리트 · 광기의 6조 쇼핑"),
            (0.74, 0.90, "22만 건 폭로 · 버킨백 567개와 6조 벌금"),
            (0.90, 1.00, "총리는 감옥행, 증발한 주범 조 로우"),
        ],
        "highlights": [
            r"\d[\d,\.]*\s*(?:조\s*원|천억\s*원|억\s*원|만\s*원|원|달러|미터|건|개|점|년|세|살|배|%)",
            r"조 로우",
            r"1MDB",
            r"골드만삭스",
            r"굿 스타",
            r"나집 라작",
            r"에쿼니미티",
            r"울프 오브 월스트리트",
            r"미란다 커",
            r"적색수배",
        ],
    },
}


def prepare_images(ep_dir: str, scene_names: list[str]) -> dict:
    raw_dir = os.path.join(ep_dir, "raw_images")
    assets_dir = os.path.join(ep_dir, "assets")
    os.makedirs(assets_dir, exist_ok=True)
    paths = {}
    for name in scene_names:
        for ext in (".png", ".jpg", ".jpeg", ".webp"):
            cand = os.path.join(raw_dir, name + ext)
            if os.path.exists(cand) and os.path.getsize(cand) > 1000:
                paths[name] = cand
                break
        if name not in paths:
            raise FileNotFoundError(f"Missing required scene image '{name}' in {raw_dir}")

    black_jpg = os.path.join(assets_dir, "blackout.jpg")
    if not os.path.exists(black_jpg):
        subprocess.run(
            [
                "ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=#05070d:s=1920x1080:d=1",
                "-frames:v", "1", black_jpg,
            ],
            check=True,
            capture_output=True,
        )
    paths["blackout"] = black_jpg
    return paths


def parse_srt_file(srt_path: str) -> list[dict]:
    content = open(srt_path, "r", encoding="utf-8").read().strip()
    raw_blocks = re.split(r"\n\s*\n", content)
    entries = []

    def to_sec(t_str: str) -> float:
        t_str = t_str.strip().replace(",", ".")
        h, m, s = t_str.split(":")
        return int(h) * 3600 + int(m) * 60 + float(s)

    for b in raw_blocks:
        lines = [ln.strip() for ln in b.strip().splitlines() if ln.strip()]
        if len(lines) >= 3 and "-->" in lines[1]:
            idx = int(lines[0])
            s_str, e_str = lines[1].split("-->")
            entries.append(
                {
                    "idx": idx,
                    "start": to_sec(s_str),
                    "end": to_sec(e_str),
                    "text": " ".join(lines[2:]),
                }
            )
    return entries


def merge_into_sentences(entries: list[dict]) -> list[dict]:
    if not entries:
        return []
    avg_dur = sum(e["end"] - e["start"] for e in entries) / len(entries)
    if avg_dur >= 2.2:
        return entries

    merged = []
    cur_words = []
    cur_s = entries[0]["start"]
    cur_e = entries[0]["end"]
    idx = 1
    for e in entries:
        if not cur_words:
            cur_s = e["start"]
        cur_words.append(e["text"])
        cur_e = e["end"]
        joined = " ".join(cur_words)
        if e["text"].endswith((".", "?", "!", "다.", "요.", "죠.")) or (
            cur_e - cur_s >= 4.5 and len(joined) >= 22
        ):
            merged.append({"idx": idx, "start": cur_s, "end": cur_e, "text": joined})
            idx += 1
            cur_words = []
    if cur_words:
        merged.append({"idx": idx, "start": cur_s, "end": cur_e, "text": " ".join(cur_words)})
    return merged


def get_audio_duration(path: str) -> float:
    cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", path]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return float(json.loads(res.stdout)["format"]["duration"])


def mix_sfx_timeline(total_dur: float, sfx_events: list[tuple[float, str, float]], out_wav: str):
    total_samples = int(total_dur * 44100)
    acc = [0] * total_samples
    wav_cache = {}
    for _, sfx_path, _ in sfx_events:
        if sfx_path not in wav_cache and os.path.exists(sfx_path):
            with wave.open(sfx_path, "r") as wf:
                raw_bytes = wf.readframes(wf.getnframes())
                wav_cache[sfx_path] = struct.unpack(f"<{len(raw_bytes)//2}h", raw_bytes)

    for start_sec, sfx_path, vol in sfx_events:
        if sfx_path not in wav_cache:
            continue
        samples = wav_cache[sfx_path]
        start_idx = max(0, int(start_sec * 44100))
        end_idx = min(total_samples, start_idx + len(samples))
        for i in range(start_idx, end_idx):
            acc[i] += int(samples[i - start_idx] * vol)

    buf = bytearray()
    for v in acc:
        buf.extend(struct.pack("<h", max(-32767, min(32767, v))))

    with wave.open(out_wav, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(44100)
        wf.writeframes(bytes(buf))


def classify_ep02_visual(text: str, progress: float, sent_idx: int) -> tuple[str, str, str, tuple[str, str] | None]:
    if "단 48시간" in text and progress < 0.05:
        return (
            "blackout",
            "crimson_alert",
            "| 2021년 3월 뉴욕 · 인류 역사상 최단기간 개인 최대 파산",
            ("48시간 -28조 원 증발", "인류 금융사 최단기간 개인 자산 소멸 기록"),
        )
    if "성경책" in text or "도시락" in text or "황성국" in text:
        return "ep02_s02_bible_and_bloomberg", "normal", "| 독실한 신앙인 얼굴 뒤에 숨겨진 130조 원의 승부사", None
    if "타이거 아시아" in text or "내부자 거래" in text or "블랙리스트" in text:
        return "ep02_s03_tiger_asia_sec_ban", "sepia_archive", "| 2012년 내부자 거래 적발 및 월가 블랙리스트 등재", None
    if "패밀리 오피스" in text or "공시할 의무가 면제" in text or "투명 인간" in text:
        return "ep02_s04_family_office_loophole", "cold", "| 규제 사각지대 '패밀리 오피스' : 보유 지분 공시 의무 면제", None
    if "총수익스왑" in text or "TRS" in text or "은행 명의로" in text or "여섯 은행이 똑같은" in text:
        return "ep02_s05_trs_swap_illusion", "cyan_lab", "| 장외 파생상품 '총수익스왑(TRS)' : 6대 은행 동시 익명 레버리지", None
    if "3배나 수직 폭등" in text or "1,000억 달러" in text or "자가발전 바벨탑" in text:
        return "ep02_s06_viacom_rocket_bubble", "normal", "| 비아콤CBS 주가 3배 폭등 & 총 포지션 약 130조 원 도달", None
    if "유상증자" in text or "자유낙하" in text or "전 재산 전멸" in text:
        return "ep02_s07_viacom_offering_crack", "crimson_alert", "| 2021년 3월 22일 비아콤CBS 30억 달러 유상증자 직격탄", None
    if "목요일 저녁" in text or "죄수의 딜레마" in text or "신사협정" in text or "비상 대책반" in text:
        return "ep02_s08_secret_bankers_meeting", "cold", "| 3월 25일 밤 6대 투자은행 긴급 회동과 '죄수의 딜레마'", None
    if "새벽 6시" in text or "블록딜" in text or "폭탄 투매" in text:
        return "ep02_s09_goldman_dawn_fire_sale", "crimson_alert", "| 3월 26일 06:00 · 골드만삭스·모건스탠리 개장 전 기습 투매", None
    if "약 7조 원이라는 치명상" in text or ("55억 달러" in text and "크레디트스위스" in text):
        return (
            "blackout",
            "crimson_alert",
            "| 뒤통수 맞은 크레디트스위스 단일 손실 : -7조 원 ($5.5B)",
            ("-7,000,000,000,000원", "167년 역사 크레디트스위스를 침몰시킨 결정타"),
        )
    if "크레디트스위스" in text or "167년" in text or "UBS" in text:
        return "ep02_s10_credit_suisse_collapse", "cold", "| 167년 스위스 명문 은행 크레디트스위스 결국 UBS에 강제 인수", None
    if "연방 검찰" in text or "징역 18년" in text or "뉴욕 연방법원" in text:
        return "ep02_s11_manhattan_federal_court", "sepia_archive", "| 2024 뉴욕 연방법원 징역 18년형 및 대규모 몰수 선고", None

    pool = [
        "ep02_s01_manhattan_dawn_margin",
        "thumb_bill_hwang",
        "ep02_s04_family_office_loophole",
        "ep02_s05_trs_swap_illusion",
        "ep02_s06_viacom_rocket_bubble",
        "ep02_s08_secret_bankers_meeting",
        "ep02_s09_goldman_dawn_fire_sale",
        "ep02_s10_credit_suisse_collapse",
    ]
    return pool[sent_idx % len(pool)], "normal", "", None


def classify_ep03_visual(text: str, progress: float, sent_idx: int) -> tuple[str, str, str, tuple[str, str] | None]:
    if "요트" in text or "에쿼니미티" in text:
        return "ep03_s01_equanimity_superyacht", "cold", "| 나랏돈 3,300억 원으로 구입한 91m 초호화 요트 '에쿼니미티'", None
    if "약 6조 원을 빼돌린" in text and progress < 0.16:
        return (
            "blackout",
            "crimson_alert",
            "| 말레이시아 국부펀드 1MDB 횡령 규모 : $4.5B (약 6조 원)",
            ("나랏돈 -6조 원 증발!", "인류 역사상 최대 국부펀드 강탈 스캔들"),
        )
    if "와튼스쿨" in text or "오일머니" in text or "로스마" in text:
        return "ep03_s02_wharton_fake_prince", "sepia_archive", "| 와튼스쿨 인맥 작전 : 빌린 요트로 중동 왕족·총리 가문 포섭", None
    if "나집 라작" in text and ("총리 자리" in text or "서명 하나로" in text):
        return "ep03_s03_kuala_lumpur_1mdb_palace", "cold", "| 2009년 말레이시아 총리 직속 국부펀드 '1MDB' 설립", None
    if "굿 스타" in text or "페이퍼컴퍼니" in text or "유령 회사" in text:
        return "ep03_s04_shell_company_wire_transfer", "cyan_lab", "| 스위스 유령 계좌 'Good Star'로 첫날 9,000억 원 불법 이체", None
    if "골드만삭스" in text and ("수수료" in text or "채권" in text or "7,800억" in text):
        return "ep03_s05_goldman_bond_vault", "crimson_alert", "| 골드만삭스 8.5조 채권 발행 대행 · 수수료 약 7,800억 원 수취", None
    if "울프 오브 월스트리트" in text or "디카프리오" in text or "패리스 힐튼" in text:
        return "ep03_s06_vegas_hollywood_party", "normal", "| 횡령한 나랏돈으로 할리우드 영화 제작 및 라스베이거스 파티", None
    if "투명" in text or "피아노" in text or "다이아몬드" in text:
        return "ep03_s07_crystal_piano_diamonds", "normal", "| 미란다 커 100억 다이아몬드 & 투명 크리스털 피아노 선물", None
    if "22만 건" in text or "하드디스크" in text or "월스트리트저널" in text:
        return "ep03_s08_journalist_leaked_drive", "cyan_lab", "| 2015년 내부 고발 이메일 22만 건 유출로 전모 폭로", None
    if "버킨백" in text or "567개" in text or "여행 가방" in text:
        return "ep03_s09_mansion_cash_raid", "crimson_alert", "| 나집 전 총리 자택 압수수색 : 명품 가방 567개·보석 1만 2천 점", None
    if "법무부" in text or "합의금" in text or ("벌금" in text and "골드만삭스" in text):
        return (
            "ep03_s10_doj_goldman_settlement",
            "sepia_archive",
            "| 미국 법무부 철퇴 : 골드만삭스 약 6조 원대 사상 최대 벌금 합의",
            None,
        )
    if "적색수배" in text or "가짜 신분" in text or "마카오" in text or "감옥 밖" in text:
        return "ep03_s11_fugitive_shadow_macau", "cold", "| 인터폴 적색수배 주범 조 로우 : 현재까지 미검거 행방불명", None

    pool = [
        "thumb_jho_low",
        "ep03_s03_kuala_lumpur_1mdb_palace",
        "ep03_s04_shell_company_wire_transfer",
        "ep03_s05_goldman_bond_vault",
        "ep03_s06_vegas_hollywood_party",
        "ep03_s08_journalist_leaked_drive",
        "ep03_s10_doj_goldman_settlement",
        "ep03_s11_fugitive_shadow_macau",
    ]
    return pool[sent_idx % len(pool)], "normal", "", None


def render_one_16x9_clip(task: tuple) -> tuple[str, str]:
    clips_dir, clip_id, img_path, dur, motion_type, tint = task
    out_mp4 = os.path.join(clips_dir, f"clip_{clip_id}.mp4")
    if os.path.exists(out_mp4) and os.path.getsize(out_mp4) > 8000:
        return clip_id, out_mp4

    frames = max(24, int(round(dur * 24)))
    d_str = f"{max(0.8, dur):.3f}"
    fn_1 = max(1, frames - 1)

    if motion_type == "zoom_in":
        zp = f"zoompan=z='1.0+0.12*(on/{fn_1})':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s=1920x1080:fps=24"
    elif motion_type == "zoom_out":
        zp = f"zoompan=z='1.12-0.12*(on/{fn_1})':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s=1920x1080:fps=24"
    elif motion_type == "pan_right":
        zp = f"zoompan=z='1.10':x='(iw-iw/zoom)*(0.18+0.64*(on/{fn_1}))':y='(ih-ih/zoom)*0.50':d={frames}:s=1920x1080:fps=24"
    elif motion_type == "pan_left":
        zp = f"zoompan=z='1.10':x='(iw-iw/zoom)*(0.82-0.64*(on/{fn_1}))':y='(ih-ih/zoom)*0.50':d={frames}:s=1920x1080:fps=24"
    elif motion_type == "plunge_down":
        zp = f"zoompan=z='1.10':x='(iw-iw/zoom)*0.50':y='(ih-ih/zoom)*(0.18+0.64*(on/{fn_1}))':d={frames}:s=1920x1080:fps=24"
    elif motion_type == "rise_up":
        zp = f"zoompan=z='1.10':x='(iw-iw/zoom)*0.50':y='(ih-ih/zoom)*(0.82-0.64*(on/{fn_1}))':d={frames}:s=1920x1080:fps=24"
    else:
        zp = f"zoompan=z='1.0':x='0':y='0':d={frames}:s=1920x1080:fps=24"

    if tint == "cold":
        color_vf = "colorbalance=bs=0.10:rs=-0.04,eq=contrast=1.07"
    elif tint == "crimson_alert":
        color_vf = "colorbalance=rs=0.11:gs=-0.04:bs=-0.04,eq=contrast=1.08"
    elif tint == "sepia_archive":
        color_vf = "colorchannelmixer=.393:.769:.189:0:.349:.686:.168:0:.272:.534:.131,eq=contrast=1.06"
    elif tint == "cyan_lab":
        color_vf = "colorbalance=gs=0.06:bs=0.10:rs=-0.04,eq=contrast=1.07"
    else:
        color_vf = "eq=contrast=1.06:saturation=1.07"

    vf = (
        f"scale=3840:2160:force_original_aspect_ratio=increase,crop=3840:2160,"
        f"{zp},{color_vf},format=yuv420p"
    )
    subprocess.run(
        [
            "ffmpeg", "-y", "-i", img_path, "-vf", vf, "-t", d_str,
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "20", "-an", out_mp4,
        ],
        check=True,
        capture_output=True,
    )
    return clip_id, out_mp4


def format_ass_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def split_into_phrases(text: str, start: float, end: float, max_chars: int = 26) -> list[tuple[float, float, str]]:
    text = text.strip()
    if len(text) <= max_chars:
        return [(start, end, text)]
    words = text.split()
    target_chunks = max(2, int((len(text) + max_chars - 1) // max_chars))
    chunk_len = len(text) / target_chunks
    phrases, cur_words, cur_len = [], [], 0
    for i, w in enumerate(words):
        cur_words.append(w)
        cur_len += len(w) + 1
        rem_words = len(words) - (i + 1)
        if len(phrases) < target_chunks - 1 and rem_words >= 2:
            if w.endswith((",", "!", "?")) or cur_len >= chunk_len:
                phrases.append(" ".join(cur_words))
                cur_words, cur_len = [], 0
    if cur_words:
        phrases.append(" ".join(cur_words))

    total_chars = sum(max(1, len(p)) for p in phrases)
    dur = end - start
    out, cur_t = [], start
    for i, p in enumerate(phrases):
        nxt_t = end if i == len(phrases) - 1 else cur_t + dur * (max(1, len(p)) / total_chars)
        out.append((cur_t, nxt_t, p))
        cur_t = nxt_t
    return out


def colorize_keywords(line: str, patterns: list[str]) -> str:
    combined = "(" + "|".join(patterns) + ")"
    parts = re.split(combined, line)
    out = []
    for idx, p in enumerate(parts):
        if not p:
            continue
        if idx % 2 == 1:
            out.append(f"{{\\c&H0000DFFF&}}{p}{{\\c&H00FFFFFF&}}")
        else:
            out.append(p)
    return "".join(out)


def build_episode(ep_key: str, allow_legacy_len: bool = False):
    cfg = EPISODE_CONFIGS[ep_key]
    ep_dir = os.path.join(STUDIO_DIR, cfg["dir_name"])
    assets_dir = os.path.join(ep_dir, "assets")
    clips_dir = os.path.join(assets_dir, "clips_v2")
    os.makedirs(clips_dir, exist_ok=True)

    img_paths = prepare_images(ep_dir, cfg["scene_images"])
    long_mp3 = os.path.join(ep_dir, f"{ep_key}_longform_kr.mp3")
    long_srt = os.path.join(ep_dir, f"{ep_key}_longform_kr.srt")
    shorts_mp3 = os.path.join(ep_dir, f"{ep_key}_shorts_kr.mp3")
    shorts_srt = os.path.join(ep_dir, f"{ep_key}_shorts_kr.srt")

    out_full_mp4 = os.path.join(ep_dir, cfg["out_long_mp4"])
    out_shorts_mp4 = os.path.join(ep_dir, cfg["out_shorts_mp4"])

    raw_entries = parse_srt_file(long_srt)
    sentences = merge_into_sentences(raw_entries)
    total_dur = max(get_audio_duration(long_mp3), sentences[-1]["end"]) + 1.8
    if not allow_legacy_len and total_dur < 485.0:
        raise RuntimeError(
            f"[{ep_key.upper()}] Longform duration ({total_dur:.1f}s) is below v3.0 mid-roll minimum (485.0s / 8m 05s)!"
        )
    print(f"[{ep_key.upper()}] Longform Duration: {total_dur:.1f}s ({total_dur/60:.2f}m), {len(sentences)} sentences", flush=True)

    tasks = []
    subclip_order = []
    sent_timings = []
    prev_end = 0.0
    prev_img_key = ""
    alt_keys = [k for k in cfg["scene_images"] if not k.startswith("thumb_")]
    classifier = classify_ep02_visual if ep_key == "ep02" else classify_ep03_visual

    for i, s_obj in enumerate(sentences):
        seg_end = total_dur if i == len(sentences) - 1 else sentences[i + 1]["start"]
        full_dur = max(1.0, seg_end - prev_end)
        prog = prev_end / total_dur
        img_key, tint, spec_card, slam_pair = classifier(s_obj["text"], prog, i)

        if img_key == prev_img_key and img_key != "blackout":
            img_key = alt_keys[(i * 3 + 1) % len(alt_keys)]

        sent_timings.append((i, prev_end, seg_end, full_dur, s_obj["text"], img_key, spec_card, slam_pair))

        if img_key == "blackout":
            cid = f"{i:03d}_0"
            subclip_order.append(cid)
            tasks.append((clips_dir, cid, img_paths["blackout"], full_dur, "static_hold", tint))
        elif full_dur >= 5.6:
            second_key = (
                alt_keys[(alt_keys.index(img_key) + 1) % len(alt_keys)]
                if img_key in alt_keys
                else alt_keys[i % len(alt_keys)]
            )
            half = full_dur / 2.0
            c0, c1 = f"{i:03d}_0", f"{i:03d}_1"
            subclip_order.extend([c0, c1])
            tasks.append((clips_dir, c0, img_paths[img_key], half, MOTIONS[i % len(MOTIONS)], tint))
            tasks.append((clips_dir, c1, img_paths[second_key], half, MOTIONS[(i + 2) % len(MOTIONS)], tint))
            img_key = second_key
        else:
            cid = f"{i:03d}_0"
            subclip_order.append(cid)
            tasks.append((clips_dir, cid, img_paths[img_key], full_dur, MOTIONS[i % len(MOTIONS)], tint))

        prev_img_key = img_key
        prev_end = seg_end

    print(f"[{ep_key.upper()}] Rendering {len(tasks)} smooth 16:9 clips in parallel...", flush=True)
    clip_paths = {}
    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = [ex.submit(render_one_16x9_clip, t) for t in tasks]
        for fut in as_completed(futs):
            cid, c_path = fut.result()
            clip_paths[cid] = c_path

    bgm_1 = os.path.join(BGM_SRC_DIR, "classic_horror_1.mp3")
    bgm_2 = os.path.join(BGM_SRC_DIR, "oppressive_gloom.mp3")
    bgm_3 = os.path.join(BGM_SRC_DIR, "giant_wyrm.mp3")
    part_dur = int(total_dur / 3) + 6
    bgm_suite_wav = os.path.join(assets_dir, f"{ep_key}_bgm_suite.wav")
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-stream_loop", "-1", "-t", str(part_dur), "-i", bgm_1,
            "-stream_loop", "-1", "-t", str(part_dur), "-i", bgm_2,
            "-stream_loop", "-1", "-t", str(part_dur), "-i", bgm_3,
            "-filter_complex",
            (
                f"[0:a]afade=t=in:st=0:d=2,afade=t=out:st={part_dur-4}:d=4[a0];"
                f"[1:a]afade=t=in:st=0:d=3,afade=t=out:st={part_dur-4}:d=4[a1];"
                f"[2:a]afade=t=in:st=0:d=3,afade=t=out:st={part_dur-5}:d=5[a2];"
                "[a0][a1][a2]concat=n=3:v=0:a=1[bgm_full]"
            ),
            "-map", "[bgm_full]", "-t", f"{total_dur:.2f}", "-ar", "44100", "-ac", "2", bgm_suite_wav,
        ],
        check=True,
        capture_output=True,
    )

    sfx_events = [(0.08, os.path.join(SFX_DIR, "sfx_deep_riser_boom.wav"), 0.75)]
    for r0, _, _ in cfg["chapters"][1:]:
        sfx_events.append((total_dur * r0, os.path.join(SFX_DIR, "sfx_deep_riser_boom.wav"), 0.65))

    for i, seg_s, _, _, txt, img_key, _, _ in sent_timings:
        if img_key == "blackout":
            sfx_events.append((seg_s + 0.05, os.path.join(SFX_DIR, "sfx_stamp_slam.wav"), 0.92))
        elif any(w in txt for w in ("총수익스왑", "굿 스타", "22만 건", "블랙리스트")):
            sfx_events.append((seg_s + 0.15, os.path.join(SFX_DIR, "sfx_crt_88888_beep.wav"), 0.80))
        elif any(w in txt for w in ("자유낙하", "폭탄 투매", "유상증자", "압수")):
            sfx_events.append((seg_s + 0.05, os.path.join(SFX_DIR, "sfx_market_crash_rumble.wav"), 0.86))
        elif any(w in txt for w in ("새벽 6시", "130조", "7,800억", "65억 달러")):
            sfx_events.append((seg_s + 0.10, os.path.join(SFX_DIR, "sfx_trading_bell_panic.wav"), 0.78))
        elif any(w in txt for w in ("징역 18년", "법무부", "수감")):
            sfx_events.append((seg_s + 0.12, os.path.join(SFX_DIR, "sfx_court_gavel.wav"), 0.85))

    sfx_wav = os.path.join(assets_dir, f"{ep_key}_sfx_timeline.wav")
    mix_sfx_timeline(total_dur, sfx_events, sfx_wav)

    master_m4a = os.path.join(assets_dir, f"{ep_key}_master_audio.m4a")
    subprocess.run(
        [
            "ffmpeg", "-y", "-i", long_mp3, "-i", bgm_suite_wav, "-i", sfx_wav,
            "-filter_complex",
            (
                "[0:a]volume=1.58,equalizer=f=3200:t=q:w=1.2:g=2.8[voice];"
                "[1:a]volume=0.32[bgm];"
                "[2:a]lowpass=f=3800,volume=0.56[sfx];"
                "[voice][bgm][sfx]amix=inputs=3:duration=first:dropout_transition=2:normalize=0[aout]"
            ),
            "-map", "[aout]", "-t", f"{total_dur:.2f}",
            "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2", master_m4a,
        ],
        check=True,
        capture_output=True,
    )

    ass_path = os.path.join(assets_dir, f"{ep_key}_master_overlay.ass")
    ass_header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: DocSubOneLine,Malgun Gothic,56,&H00FFFFFF,&H0000FFFF,&H64000000,&H64000000,-1,0,0,0,100,100,1,0,3,15,0,2,50,50,46,1
Style: TopLeftPill,Malgun Gothic,33,&H00FFFFFF,&H0000FFFF,&H60000000,&H60000000,-1,0,0,0,100,100,1,0,3,10,0,7,42,42,32,1
Style: TopRightBrand,Malgun Gothic,34,&H0000D4FF,&H0000FFFF,&H00000000,&H00000000,-1,0,0,0,100,100,2,0,1,4,2,9,45,45,32,1
Style: LiveTelemetryHUD,Malgun Gothic,30,&H0000DFFF,&H0000FFFF,&H60000000,&H60000000,-1,0,0,0,100,100,1,0,3,9,0,9,45,45,86,1
Style: SpecCard,Malgun Gothic,32,&H00F0F0F0,&H0000FFFF,&H60000000,&H60000000,-1,0,0,0,100,100,1,0,3,10,0,1,45,45,134,1
Style: GiantRedSlam,Malgun Gothic,138,&H00221CF0,&H0000FFFF,&H00000000,&H00000000,-1,0,0,0,100,100,3,0,1,12,6,5,40,40,40,1
Style: GiantSubLabel,Malgun Gothic,46,&H0000DFFF,&H0000FFFF,&H00000000,&H00000000,-1,0,0,0,100,100,2,0,1,5,2,5,40,40,40,1
Style: SubOutroBanner,Malgun Gothic,36,&H0000E8FF,&H0000FFFF,&H8810141E,&H8810141E,-1,0,0,0,100,100,1,0,3,12,0,8,60,60,140,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    with open(ass_path, "w", encoding="utf-8-sig") as f:
        f.write(ass_header)
        f.write(f"Dialogue: 2,0:00:00.00,{format_ass_time(total_dur)},TopRightBrand,,0,0,0,,머니 아카이브\n")

        for ch_idx, (r0, r1, ch_title) in enumerate(cfg["chapters"], start=1):
            f.write(
                f"Dialogue: 2,{format_ass_time(total_dur*r0)},{format_ass_time(total_dur*r1)},TopLeftPill,,0,0,0,,"
                f"  {{\\c&H002820F0&}}● ACT {ch_idx} /{{\\c&H00FFFFFF&}} {ch_title}  \n"
            )

        shown_cards = set()
        for i, seg_s, seg_e, _, txt, img_key, spec_card, slam_pair in sent_timings:
            s_str, e_str = format_ass_time(seg_s), format_ass_time(seg_e)
            if spec_card and spec_card not in shown_cards:
                shown_cards.add(spec_card)
                card_end = format_ass_time(min(seg_e - 0.1, seg_s + 6.2))
                formatted_card = f"  {{\\c&H002820F0&}}▌{{\\c&H00F0F0F0&}}{spec_card[1:]}  "
                f.write(f"Dialogue: 2,{s_str},{card_end},SpecCard,,0,0,0,,{{\\fad(180,250)}}{formatted_card}\n")

            if img_key == "blackout" and slam_pair:
                big_txt, sub_txt = slam_pair
                f.write(
                    f"Dialogue: 4,{s_str},{e_str},GiantRedSlam,,0,0,0,,"
                    f"{{\\pos(960,465)\\fscx135\\fscy135\\t(0,220,\\fscx100\\fscy100)\\fad(60,250)}}{big_txt}\n"
                )
                f.write(
                    f"Dialogue: 4,{s_str},{e_str},GiantSubLabel,,0,0,0,,"
                    f"{{\\pos(960,625)\\fad(200,250)}}{sub_txt}\n"
                )

        # Live Financial Telemetry HUDs
        if ep_key == "ep02":
            h1_s, h1_e = total_dur * 0.35, total_dur * 0.62
            steps = 50
            dt = (h1_e - h1_s) / steps
            for st in range(steps):
                t0, t1 = h1_s + st * dt, h1_s + (st + 1) * dt
                p = (st + 1) / steps
                lev_jo = round(13.0 + 117.0 * (p ** 1.5), 1)
                f.write(
                    f"Dialogue: 2,{format_ass_time(t0)},{format_ass_time(t1)},LiveTelemetryHUD,,0,0,0,,"
                    f"  ⚠️ {{\\c&H00FFFFFF&}}아케고스 익명 레버리지 : {{\\c&H0000DFFF&}}{lev_jo}조 원 {{\\c&H002820F0&}}(6대 은행 스왑)  \n"
                )
            h2_s, h2_e = total_dur * 0.64, total_dur * 0.88
            dt2 = (h2_e - h2_s) / steps
            for st in range(steps):
                t0, t1 = h2_s + st * dt2, h2_s + (st + 1) * dt2
                p = (st + 1) / steps
                loss_jo = round(0.5 + 27.5 * (p ** 1.8), 2)
                filled = min(10, max(1, int(p * 10)))
                bar = "█" * filled + "░" * (10 - filled)
                f.write(
                    f"Dialogue: 2,{format_ass_time(t0)},{format_ass_time(t1)},LiveTelemetryHUD,,0,0,0,,"
                    f"  📉 {{\\c&H00FFFFFF&}}48시간 증발 순자산 : {{\\c&H002820F0&}}-{loss_jo:.2f}조 원 {bar}  \n"
                )
        else:
            h1_s, h1_e = total_dur * 0.32, total_dur * 0.72
            steps = 55
            dt = (h1_e - h1_s) / steps
            for st in range(steps):
                t0, t1 = h1_s + st * dt, h1_s + (st + 1) * dt
                p = (st + 1) / steps
                stolen_eok = int(9000 + 51000 * (p ** 1.5))
                disp = f"-{stolen_eok:,}억 원" if stolen_eok < 10000 else f"-{stolen_eok/10000:.2f}조 원"
                filled = min(10, max(1, int(p * 10)))
                bar = "█" * filled + "░" * (10 - filled)
                f.write(
                    f"Dialogue: 2,{format_ass_time(t0)},{format_ass_time(t1)},LiveTelemetryHUD,,0,0,0,,"
                    f"  💸 {{\\c&H00FFFFFF&}}1MDB 국부펀드 유출액 : {{\\c&H002820F0&}}{disp} {bar}  \n"
                )

        for s_obj in sentences:
            for p_s, p_e, phrase in split_into_phrases(s_obj["text"], s_obj["start"], s_obj["end"], max_chars=27):
                colored = colorize_keywords(phrase, cfg["highlights"])
                sub_line = f"  {{\\c&H0000D4FF&}}▌{{\\c&H00FFFFFF&}} {colored}  "
                f.write(
                    f"Dialogue: 3,{format_ass_time(p_s)},{format_ass_time(p_e)},DocSubOneLine,,0,0,0,,{sub_line}\n"
                )

        outro_s = format_ass_time(max(0.0, total_dur - 11.0))
        outro_e = format_ass_time(max(0.5, total_dur - 0.5))
        f.write(
            f"Dialogue: 4,{outro_s},{outro_e},SubOutroBanner,,0,0,0,,"
            f"{{\\fad(250,250)}}  🔔 금융·비즈니스 실화 [머니 아카이브] 구독 · 좋아요는 다음 추적에 큰 힘이 됩니다  \n"
        )

    clips_txt = os.path.join(assets_dir, "clips_concat.txt")
    with open(clips_txt, "w", encoding="utf-8") as f:
        for cid in subclip_order:
            f.write(f"file '{clip_paths[cid].replace(chr(92), '/')}'\n")

    ass_esc = ass_path.replace("\\", "/").replace(":", "\\:")
    subprocess.run(
        [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", clips_txt, "-i", master_m4a,
            "-vf", f"ass='{ass_esc}',format=yuv420p",
            "-map", "0:v", "-map", "1:a", "-t", f"{total_dur:.2f}",
            "-c:v", "libx264", "-profile:v", "high", "-pix_fmt", "yuv420p",
            "-preset", "veryfast", "-crf", "19", "-maxrate", "5500k", "-bufsize", "11000k",
            "-c:a", "copy", "-movflags", "+faststart",
            out_full_mp4,
        ],
        check=True,
        capture_output=True,
    )
    print(f"[{ep_key.upper()}] SUCCESS Full 16:9 Rendered: {out_full_mp4}", flush=True)

    # =========================================================================
    # Build v3 9:16 FULL-BLEED SAFE-ZONE CLIFFHANGER SHORTS (1080x1920, Zero Black Bars!)
    # =========================================================================
    short_raw = parse_srt_file(shorts_srt)
    short_sents = merge_into_sentences(short_raw)
    shorts_dur = max(get_audio_duration(shorts_mp3), short_sents[-1]["end"]) + 0.7
    if not allow_legacy_len and shorts_dur > 48.5:
        raise RuntimeError(
            f"[{ep_key.upper()}] Shorts duration ({shorts_dur:.1f}s) exceeds v3.0 cliffhanger cap (48.5s)! "
            f"Cut right before the ending reveal (36~45s) or pass --allow-legacy-len for legacy EP02/EP03."
        )

    shorts_sfx = [
        (0.03, os.path.join(SFX_DIR, "sfx_stamp_slam.wav"), 0.90),
        (9.50, os.path.join(SFX_DIR, "sfx_crt_88888_beep.wav"), 0.80),
        (24.0, os.path.join(SFX_DIR, "sfx_market_crash_rumble.wav"), 0.85),
        (max(30.0, shorts_dur - 12.0), os.path.join(SFX_DIR, "sfx_deep_riser_boom.wav"), 0.80),
    ]
    shorts_sfx_wav = os.path.join(assets_dir, f"{ep_key}_shorts_sfx.wav")
    mix_sfx_timeline(shorts_dur, shorts_sfx, shorts_sfx_wav)

    shorts_m4a = os.path.join(assets_dir, f"{ep_key}_shorts_master.m4a")
    subprocess.run(
        [
            "ffmpeg", "-y", "-i", shorts_mp3, "-stream_loop", "-1", "-i", bgm_1, "-i", shorts_sfx_wav,
            "-filter_complex",
            (
                "[0:a]volume=1.62,equalizer=f=3200:t=q:w=1.2:g=2.8[voice];"
                "[1:a]volume=0.34[bgm];"
                "[2:a]lowpass=f=3800,volume=0.56[sfx];"
                "[voice][bgm][sfx]amix=inputs=3:duration=first:dropout_transition=2:normalize=0[aout]"
            ),
            "-map", "[aout]", "-t", f"{shorts_dur:.2f}",
            "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2", shorts_m4a,
        ],
        check=True,
        capture_output=True,
    )

    vcycle = cfg["shorts_visual_cycle"]
    shorts_concat = os.path.join(assets_dir, "shorts_concat.txt")
    with open(shorts_concat, "w", encoding="utf-8") as f:
        prev_t = 0.0
        for idx_s, s_obj in enumerate(short_sents):
            seg_e = shorts_dur if idx_s == len(short_sents) - 1 else short_sents[idx_s + 1]["start"]
            dur = max(0.8, seg_e - prev_t)
            prev_t = seg_e

            # Split long shorts sentences (>5.0s) into 2 rapid cuts so visual pace beats swipe-away!
            sub_cuts = [(dur / 2.0, 0), (dur / 2.0, 1)] if dur >= 5.0 else [(dur, 0)]
            for cut_dur, sub_idx in sub_cuts:
                vkey = vcycle[(idx_s * 2 + sub_idx) % len(vcycle)]
                sc_mp4 = os.path.join(clips_dir, f"shorts_v2_{idx_s:02d}_{sub_idx}.mp4")
                frames = max(24, int(round(cut_dur * 24)))
                fn_1 = max(1, frames - 1)
                if (idx_s + sub_idx) % 2 == 0:
                    zp_s = f"zoompan=z='1.0+0.11*(on/{fn_1})':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s=1080x1920:fps=24"
                else:
                    zp_s = f"zoompan=z='1.11-0.09*(on/{fn_1})':x='(iw-iw/zoom)*(0.30+0.40*(on/{fn_1}))':y='ih/2-(ih/zoom/2)':d={frames}:s=1080x1920:fps=24"

                subprocess.run(
                    [
                        "ffmpeg", "-y", "-i", img_paths[vkey],
                        "-vf",
                        (
                            "scale=2160:3840:force_original_aspect_ratio=increase,crop=2160:3840,"
                            f"{zp_s},"
                            "eq=contrast=1.08:saturation=1.10,"
                            "drawbox=x=0:y=0:w=1080:h=285:color=black@0.54:t=fill,"
                            "drawbox=x=0:y=1240:w=1080:h=680:color=black@0.48:t=fill,"
                            "format=yuv420p"
                        ),
                        "-t", f"{cut_dur:.3f}",
                        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "20", "-an", sc_mp4,
                    ],
                    check=True,
                    capture_output=True,
                )
                f.write(f"file '{sc_mp4.replace(chr(92), '/')}'\n")

    shorts_ass = os.path.join(assets_dir, "shorts_v2_overlay.ass")
    # Strict YouTube Shorts Safe Zone:
    # - Top Hook sits high (y=82 & y=162) above auto-CC box
    # - Subtitles sit in safe lower-middle reading zone (MarginV=520 => y=1400), never colliding with handle/title/related video (y=1520..1920)
    # - MarginR=135 clears right-side Like/Comment/Share buttons!
    shorts_ass_header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: TopHook1,Malgun Gothic,58,&H00FFFFFF,&H0000FFFF,&H00000000,&H00000000,-1,0,0,0,100,100,-1,0,1,8,4,8,45,45,82,1
Style: TopHook2,Malgun Gothic,64,&H0000E8FF,&H0000FFFF,&H00000000,&H00000000,-1,0,0,0,100,100,-1,0,1,9,4,8,45,45,160,1
Style: ShortsSub,Malgun Gothic,64,&H00FFFFFF,&H0000FFFF,&H78000000,&H78000000,-1,0,0,0,100,100,0,0,3,14,0,2,65,135,525,1
Style: RelatedCTA,Malgun Gothic,44,&H0000F0FF,&H0000FFFF,&H881414B4,&H881414B4,-1,0,0,0,100,100,1,0,3,12,0,2,65,135,435,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    with open(shorts_ass, "w", encoding="utf-8-sig") as f:
        f.write(shorts_ass_header)
        f.write(f"Dialogue: 2,0:00:00.00,{format_ass_time(shorts_dur)},TopHook1,,0,0,0,,{cfg['shorts_hook_1']}\n")
        f.write(f"Dialogue: 2,0:00:00.00,{format_ass_time(shorts_dur)},TopHook2,,0,0,0,,{cfg['shorts_hook_2']}\n")
        cta_start = max(0.0, shorts_dur - 7.5)
        f.write(
            f"Dialogue: 4,{format_ass_time(cta_start)},{format_ass_time(shorts_dur)},RelatedCTA,,0,0,0,,"
            f"  ▼ 아래 [관련 동영상]에서 결말 확인 · 구독하기 ▼  \n"
        )
        for s_obj in short_sents:
            for p_s, p_e, phrase in split_into_phrases(s_obj["text"], s_obj["start"], s_obj["end"], max_chars=16):
                colored = colorize_keywords(phrase, cfg["highlights"])
                f.write(f"Dialogue: 3,{format_ass_time(p_s)},{format_ass_time(p_e)},ShortsSub,,0,0,0,,  {colored}  \n")

    shorts_ass_esc = shorts_ass.replace("\\", "/").replace(":", "\\:")
    subprocess.run(
        [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", shorts_concat, "-i", shorts_m4a,
            "-vf", f"ass='{shorts_ass_esc}',format=yuv420p",
            "-map", "0:v", "-map", "1:a", "-t", f"{shorts_dur:.2f}",
            "-c:v", "libx264", "-profile:v", "main", "-pix_fmt", "yuv420p",
            "-preset", "veryfast", "-crf", "19", "-c:a", "copy", "-movflags", "+faststart",
            out_shorts_mp4,
        ],
        check=True,
        capture_output=True,
    )
    print(f"[{ep_key.upper()}] SUCCESS Full-Bleed Safe-Zone 9:16 Shorts Rendered: {out_shorts_mp4}", flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ep", choices=["ep02", "ep03", "both"], default="ep03")
    parser.add_argument("--allow-legacy-len", action="store_true")
    args = parser.parse_args()

    if args.ep in ("ep02", "both"):
        build_episode("ep02", allow_legacy_len=args.allow_legacy_len)
    if args.ep in ("ep03", "both"):
        build_episode("ep03", allow_legacy_len=args.allow_legacy_len)


if __name__ == "__main__":
    main()
