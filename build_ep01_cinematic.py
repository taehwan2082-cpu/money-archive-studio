from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
import re
import shutil
import struct
import subprocess
import wave

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_DIR = os.path.join(BASE_DIR, "raw_images")
EP1_DIR = os.path.join(BASE_DIR, "ep01_barings_kr")
ASSETS_DIR = os.path.join(EP1_DIR, "assets")
CLIPS_DIR = os.path.join(ASSETS_DIR, "clips_v4")
SFX_DIR = os.path.join(ASSETS_DIR, "sfx")
BGM_SRC_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "mystery-doc-studio", "ep01_kola_kr", "assets", "real_archive"))

os.makedirs(CLIPS_DIR, exist_ok=True)
os.makedirs(ASSETS_DIR, exist_ok=True)

LONG_MP3 = os.path.join(EP1_DIR, "ep01_longform_kr.mp3")
LONG_SRT = os.path.join(EP1_DIR, "ep01_longform_kr.srt")
SHORTS_MP3 = os.path.join(EP1_DIR, "ep01_shorts_kr.mp3")
SHORTS_SRT = os.path.join(EP1_DIR, "ep01_shorts_kr.srt")

OUT_FULL_MP4 = os.path.join(EP1_DIR, "머니아카이브_EP01_베어링스88888_9조증발_본편.mp4")
OUT_SHORTS_MP4 = os.path.join(EP1_DIR, "머니아카이브_EP01_베어링스88888_쇼츠_9x16.mp4")

SCENE_IMAGES = [
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
    "thumb_smiling_trader",
]


def prepare_images() -> dict:
    paths = {}
    for name in SCENE_IMAGES:
        for ext in (".png", ".jpg", ".jpeg", ".webp"):
            cand = os.path.join(RAW_DIR, name + ext)
            if os.path.exists(cand):
                paths[name] = cand
                break
        if name not in paths:
            raise FileNotFoundError(f"Missing required scene image for {name} in {RAW_DIR}")

    black_jpg = os.path.join(ASSETS_DIR, "blackout.jpg")
    if not os.path.exists(black_jpg):
        subprocess.run([
            "ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=#06080e:s=1920x1080:d=1",
            "-frames:v", "1", black_jpg
        ], check=True, capture_output=True)
    paths["blackout"] = black_jpg
    return paths


def parse_srt_file(srt_path: str):
    content = open(srt_path, "r", encoding="utf-8").read().strip()
    raw_blocks = re.split(r"\n\s*\n", content)
    entries = []

    def to_sec(t_str):
        t_str = t_str.strip().replace(",", ".")
        h, m, s = t_str.split(":")
        return int(h) * 3600 + int(m) * 60 + float(s)

    for b in raw_blocks:
        lines = [ln.strip() for ln in b.strip().splitlines() if ln.strip()]
        if len(lines) >= 3 and "-->" in lines[1]:
            idx = int(lines[0])
            s_str, e_str = lines[1].split("-->")
            start = to_sec(s_str)
            end = to_sec(e_str)
            text = " ".join(lines[2:])
            entries.append({"idx": idx, "start": start, "end": end, "text": text})
    return entries


def merge_into_sentences(entries: list[dict]) -> list[dict]:
    """If edge-tts emits WordBoundary or short chunks, group into clean sentence-level blocks (~3-8s)."""
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
        if e["text"].endswith((".", "?", "!", "다.", "요.", "죠.")) or (cur_e - cur_s >= 4.8 and len(joined) >= 24):
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
                samples = struct.unpack(f"<{len(raw_bytes)//2}h", raw_bytes)
                wav_cache[sfx_path] = samples

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


def classify_sentence_visual(text: str, progress: float, sent_idx: int) -> tuple[str, str, str]:
    """Maps each narration sentence to the ideal scene image, color tint, and optional bottom-left spec card."""
    if "창이 국제공항" in text or "말레이시아행 비행기" in text or "야반도주" in text:
        return "ch1_changi_airport_rain", "cold", "| 1995년 2월 23일 밤 · 싱가포르 창이 국제공항"
    if "죄송합니다" in text or "메모" in text:
        return "ch1_sorry_note_desk", "crimson_alert", "| 닉 리슨이 남긴 마지막 메모 : 'I'm sorry'"
    if "단돈 1파운드" in text or "1,700원" in text:
        return "blackout", "crimson_alert", "| 233년 대영제국 명문 은행 최종 매각가 : £1"
    if "베어링스 은행" in text and progress < 0.22:
        return "ch1_barings_london_bank", "sepia_archive", "| 1762년 설립 · 영국 왕실 주거래 '베어링스 은행'"
    if "13년 뒤 프랑스" in text or "70조 원을 베팅" in text and progress < 0.16:
        return "ch5_paris_socgen_tower", "cold", "| 1995 런던 3조 증발 -> 2008 파리 9조 증발"
    if "자카르타" in text or "1,700억" in text or "종이 주식" in text or "미장공 아들" in text:
        return "ch2_jakarta_paper_mountain", "sepia_archive", "| 1991 인도네시아 자카르타 지점 1억 파운드 서류 해결"
    if "프론트 오피스" in text or "백 오피스" in text or "두 개의 열쇠" in text or "심판 호루라기" in text:
        return "ch2_dual_key_desk", "crimson_alert", "| 치명적 내부통제 결함 : 주문(선수) + 정산(심판) 1인 독점"
    if "싱가포르" in text and ("선물" in text or "재킷" in text or "시멕스" in text):
        return "ch2_simex_trading_pit", "normal", "| 싱가포르 국제금융거래소 (SIMEX) 선물·옵션 객장"
    if "88888" in text or "유령 오류 수정" in text or "3천만 원" in text or "마틴게일" in text:
        return "ch3_account_88888_crt", "crimson_alert", "| 본사 보고에서 누락된 비밀 오류 계좌 '88888'"
    if "감사팀" in text and ("경고 보고서" in text or "서랍" in text or "뭉개" in text):
        return "ch3_ignored_audit_report", "crimson_alert", "| 1994년 여름 내부 감사 경고 보고서 묵살"
    if "샴페인" in text or "보너스" in text or "5분의 1" in text or "무패의 천재" in text:
        return "ch3_london_champagne_boardroom", "normal", "| 런던 본사의 착각 : '황금 알을 낳는 스타 트레이더'"
    if "고베" in text or "대지진" in text or "규모 7.3" in text:
        return "ch4_kobe_earthquake_1995", "crimson_alert", "| 1995년 1월 17일 05:46 · 규모 7.3 고베 대지진 발생"
    if "닛케이" in text or "증거금" in text or "75%" in text or "스트래들" in text or "3조 원" in text:
        return "ch4_nikkei_crash_panic", "crimson_alert", "| 닛케이 지수 폭락 & 본사 운영자금 75% 무제한 송금"
    if "프랑크푸르트" in text or "창이 교도소" in text or "로그 트레이더" in text or "강연료" in text:
        return "ch4_frankfurt_arrest_stage", "cold", "| 징역 4년 복역 후 베스트셀러 작가·강연자로 변신"
    if "소시에테 제네랄" in text or "제롬 케르비엘" in text or "그랑제콜" in text:
        return "ch5_paris_socgen_tower", "cold", "| 2008 프랑스 파리 · 140년 역사 '소시에테 제네랄' 은행"
    if "947번" in text or "유령 매도" in text or "500억 유로" in text or "사각지대" in text or "서브프라임" in text:
        return "ch5_kerviel_ghost_terminal", "cyan_lab", "| 가짜 헤지 계약 947건 · 단독 무단 베팅 70조 원"
    if "49억 유로" in text or "9조 원" in text and progress > 0.75:
        return "blackout", "crimson_alert", "| 단 3일간의 반대매매 확정 손실 : 약 7조~9조 원 (기네스 기록)"
    if "법원" in text or "74번" in text or "부당해고" in text or "배상 판결" in text:
        return "ch6_french_courtroom_gavel", "sepia_archive", "| 거래소 경고 74회 묵살 폭로 & 프랑스 대법원 배상 파기"

    # Fallback rotation by narrative phase so adjacent shots always stay fresh
    if progress < 0.20:
        pool = ["ch1_barings_london_bank", "thumb_smiling_trader", "ch1_changi_airport_rain"]
    elif progress < 0.38:
        pool = ["ch2_simex_trading_pit", "ch2_jakarta_paper_mountain", "ch2_dual_key_desk"]
    elif progress < 0.56:
        pool = ["ch3_account_88888_crt", "ch3_london_champagne_boardroom", "ch3_ignored_audit_report"]
    elif progress < 0.72:
        pool = ["ch4_nikkei_crash_panic", "ch4_kobe_earthquake_1995", "ch4_frankfurt_arrest_stage"]
    elif progress < 0.88:
        pool = ["ch5_kerviel_ghost_terminal", "ch5_paris_socgen_tower"]
    else:
        pool = ["ch6_french_courtroom_gavel", "ch1_barings_london_bank", "thumb_smiling_trader"]
    return pool[sent_idx % len(pool)], "normal", ""


MOTIONS = ["zoom_in", "pan_right", "zoom_out", "pan_left", "plunge_down", "rise_up"]


def render_one_smooth_clip(task: tuple) -> tuple[str, str]:
    clip_id, img_path, dur, motion_type, tint = task
    out_mp4 = os.path.join(CLIPS_DIR, f"clip_{clip_id}.mp4")
    if os.path.exists(out_mp4) and os.path.getsize(out_mp4) > 8000:
        return clip_id, out_mp4

    frames = max(24, int(round(dur * 24)))
    d_str = f"{max(0.8, dur):.3f}"
    fn_1 = max(1, frames - 1)

    if motion_type == "zoom_in":
        zp = f"zoompan=z='1.0+0.11*(on/{fn_1})':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s=1920x1080:fps=24"
    elif motion_type == "zoom_out":
        zp = f"zoompan=z='1.11-0.11*(on/{fn_1})':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s=1920x1080:fps=24"
    elif motion_type == "pan_right":
        zp = f"zoompan=z='1.10':x='(iw-iw/zoom)*(0.20+0.60*(on/{fn_1}))':y='(ih-ih/zoom)*0.50':d={frames}:s=1920x1080:fps=24"
    elif motion_type == "pan_left":
        zp = f"zoompan=z='1.10':x='(iw-iw/zoom)*(0.80-0.60*(on/{fn_1}))':y='(ih-ih/zoom)*0.50':d={frames}:s=1920x1080:fps=24"
    elif motion_type == "plunge_down":
        zp = f"zoompan=z='1.10':x='(iw-iw/zoom)*0.50':y='(ih-ih/zoom)*(0.18+0.64*(on/{fn_1}))':d={frames}:s=1920x1080:fps=24"
    elif motion_type == "rise_up":
        zp = f"zoompan=z='1.10':x='(iw-iw/zoom)*0.50':y='(ih-ih/zoom)*(0.82-0.64*(on/{fn_1}))':d={frames}:s=1920x1080:fps=24"
    else:
        zp = f"zoompan=z='1.0':x='0':y='0':d={frames}:s=1920x1080:fps=24"

    if tint == "cold":
        color_vf = "colorbalance=bs=0.10:rs=-0.04,eq=contrast=1.06"
    elif tint == "crimson_alert":
        color_vf = "colorbalance=rs=0.11:gs=-0.04:bs=-0.04,eq=contrast=1.08"
    elif tint == "sepia_archive":
        color_vf = "colorchannelmixer=.393:.769:.189:0:.349:.686:.168:0:.272:.534:.131,eq=contrast=1.06"
    elif tint == "cyan_lab":
        color_vf = "colorbalance=gs=0.06:bs=0.10:rs=-0.04,eq=contrast=1.06"
    else:
        color_vf = "eq=contrast=1.05:saturation=1.05"

    vf = (
        f"scale=3840:2160:force_original_aspect_ratio=increase,crop=3840:2160,"
        f"{zp},{color_vf},format=yuv420p"
    )
    subprocess.run([
        "ffmpeg", "-y", "-i", img_path, "-vf", vf, "-t", d_str,
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "20", "-an", out_mp4
    ], check=True, capture_output=True)
    return clip_id, out_mp4


def format_ass_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def split_into_one_line_phrases(text: str, start: float, end: float) -> list[tuple[float, float, str]]:
    text = text.strip()
    if len(text) <= 28:
        return [(start, end, text)]
    words = text.split()
    target_chunks = 2 if len(text) <= 58 else 3
    chunk_len = len(text) / target_chunks
    phrases, cur_words, cur_len = [], [], 0
    for i, w in enumerate(words):
        cur_words.append(w)
        cur_len += len(w) + 1
        rem_words = len(words) - (i + 1)
        if len(phrases) < target_chunks - 1 and rem_words >= 2:
            if w.endswith(",") or cur_len >= chunk_len:
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


HIGHLIGHT_PATTERNS = [
    r"\d[\d,\.]*\s*(?:조\s*원|억\s*원|만\s*원|천만\s*원|원|파운드|달러|유로|년|세|살|시간|일|번|건|명|배|%)",
    r"88888",
    r"베어링스 은행",
    r"닉 리슨",
    r"고베 대지진",
    r"소시에테 제네랄",
    r"제롬 케르비엘",
    r"죄송합니다",
]


def colorize_keywords(line: str) -> str:
    combined = "(" + "|".join(HIGHLIGHT_PATTERNS) + ")"
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


def build_ep01_masterpiece():
    img_paths = prepare_images()
    raw_entries = parse_srt_file(LONG_SRT)
    sentences = merge_into_sentences(raw_entries)
    total_dur = max(get_audio_duration(LONG_MP3), sentences[-1]["end"]) + 1.8
    print(f"Total Longform Audio Duration: {total_dur:.1f}s ({total_dur/60:.2f} min), {len(sentences)} sentence blocks.")

    tasks = []
    subclip_order = []
    sent_timings = []
    prev_end = 0.0
    prev_img_key = ""

    alt_keys = [k for k in SCENE_IMAGES if k != "thumb_smiling_trader"]

    for i, s_obj in enumerate(sentences):
        seg_end = total_dur if i == len(sentences) - 1 else sentences[i + 1]["start"]
        full_dur = max(1.0, seg_end - prev_end)
        prog = prev_end / total_dur
        img_key, tint, spec_card = classify_sentence_visual(s_obj["text"], prog, i)

        if img_key == prev_img_key and img_key != "blackout":
            img_key = alt_keys[(i * 3 + 1) % len(alt_keys)]

        sent_timings.append((i, prev_end, seg_end, full_dur, s_obj["text"], img_key, spec_card))

        if img_key == "blackout":
            clip_id = f"{i:03d}_0"
            subclip_order.append(clip_id)
            tasks.append((clip_id, img_paths["blackout"], full_dur, "static_hold", tint))
        elif full_dur >= 6.2:
            second_key = alt_keys[(alt_keys.index(img_key) + 1) % len(alt_keys)] if img_key in alt_keys else alt_keys[i % len(alt_keys)]
            half = full_dur / 2.0
            c0, c1 = f"{i:03d}_0", f"{i:03d}_1"
            subclip_order.extend([c0, c1])
            tasks.append((c0, img_paths[img_key], half, MOTIONS[i % len(MOTIONS)], tint))
            tasks.append((c1, img_paths[second_key], half, MOTIONS[(i + 2) % len(MOTIONS)], tint))
            img_key = second_key
        else:
            clip_id = f"{i:03d}_0"
            subclip_order.append(clip_id)
            tasks.append((clip_id, img_paths[img_key], full_dur, MOTIONS[i % len(MOTIONS)], tint))

        prev_img_key = img_key
        prev_end = seg_end

    print(f"Rendering {len(tasks)} smooth 4K Ken Burns clips in parallel...")
    clip_paths = {}
    with ThreadPoolExecutor(max_workers=4) as ex:
        futs = [ex.submit(render_one_smooth_clip, t) for t in tasks]
        for fut in as_completed(futs):
            cid, c_path = fut.result()
            clip_paths[cid] = c_path
    print("All video clips rendered!")

    # Build 3-Act Dark Orchestral Thriller BGM Suite
    bgm_1 = os.path.join(BGM_SRC_DIR, "classic_horror_1.mp3")
    bgm_2 = os.path.join(BGM_SRC_DIR, "oppressive_gloom.mp3")
    bgm_3 = os.path.join(BGM_SRC_DIR, "giant_wyrm.mp3")
    part_dur = int(total_dur / 3) + 6
    bgm_suite_wav = os.path.join(ASSETS_DIR, "ep01_bgm_suite.wav")
    subprocess.run([
        "ffmpeg", "-y",
        "-stream_loop", "-1", "-t", str(part_dur), "-i", bgm_1,
        "-stream_loop", "-1", "-t", str(part_dur), "-i", bgm_2,
        "-stream_loop", "-1", "-t", str(part_dur), "-i", bgm_3,
        "-filter_complex", (
            f"[0:a]afade=t=in:st=0:d=2,afade=t=out:st={part_dur-4}:d=4[a0];"
            f"[1:a]afade=t=in:st=0:d=3,afade=t=out:st={part_dur-4}:d=4[a1];"
            f"[2:a]afade=t=in:st=0:d=3,afade=t=out:st={part_dur-5}:d=5[a2];"
            "[a0][a1][a2]concat=n=3:v=0:a=1[bgm_full]"
        ),
        "-map", "[bgm_full]", "-t", f"{total_dur:.2f}", "-ar", "44100", "-ac", "2", bgm_suite_wav
    ], check=True, capture_output=True)

    # Dynamic SFX Trigger Events matched to exact narration timestamps!
    sfx_events = [(0.10, os.path.join(SFX_DIR, "sfx_deep_riser_boom.wav"), 0.72)]
    for i, seg_s, seg_e, _, txt, img_key, _ in sent_timings:
        if "죄송합니다" in txt:
            sfx_events.append((seg_s + 0.1, os.path.join(SFX_DIR, "sfx_stamp_slam.wav"), 0.80))
        elif img_key == "blackout":
            sfx_events.append((seg_s + 0.05, os.path.join(SFX_DIR, "sfx_stamp_slam.wav"), 0.92))
        elif "88888" in txt and any(w in txt for w in ("개설", "입력한", "비밀 계좌")):
            sfx_events.append((seg_s + 0.2, os.path.join(SFX_DIR, "sfx_crt_88888_beep.wav"), 0.82))
        elif "고베 대지진" in txt or "규모 7.3" in txt:
            sfx_events.append((seg_s + 0.05, os.path.join(SFX_DIR, "sfx_market_crash_rumble.wav"), 0.88))
        elif "500억 유로" in txt or "70조 원" in txt:
            sfx_events.append((seg_s + 0.1, os.path.join(SFX_DIR, "sfx_trading_bell_panic.wav"), 0.78))
        elif "대법원" in txt or "배상 판결" in txt:
            sfx_events.append((seg_s + 0.15, os.path.join(SFX_DIR, "sfx_court_gavel.wav"), 0.85))
        elif i > 0 and i % 14 == 0:
            sfx_events.append((seg_s + 0.05, os.path.join(SFX_DIR, "sfx_deep_riser_boom.wav"), 0.62))

    sfx_wav = os.path.join(ASSETS_DIR, "ep01_sfx_timeline.wav")
    mix_sfx_timeline(total_dur, sfx_events, sfx_wav)

    master_m4a = os.path.join(ASSETS_DIR, "ep01_master_audio.m4a")
    subprocess.run([
        "ffmpeg", "-y",
        "-i", LONG_MP3, "-i", bgm_suite_wav, "-i", sfx_wav,
        "-filter_complex", (
            "[0:a]volume=1.55,equalizer=f=3200:t=q:w=1.2:g=2.6[voice];"
            "[1:a]volume=0.34[bgm];"
            "[2:a]lowpass=f=3800,volume=0.56[sfx];"
            "[voice][bgm][sfx]amix=inputs=3:duration=first:dropout_transition=2:normalize=0[aout]"
        ),
        "-map", "[aout]", "-t", f"{total_dur:.2f}",
        "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2", master_m4a
    ], check=True, capture_output=True)

    # Generate Rich Broadcast Documentary ASS Overlay (Subtitles + Live Financial HUDs + Slam Cards)
    ass_path = os.path.join(ASSETS_DIR, "ep01_master_overlay.ass")
    ass_header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: DocSubOneLine,Malgun Gothic,52,&H00FFFFFF,&H0000FFFF,&H58000000,&H58000000,-1,0,0,0,100,100,1,0,3,14,0,2,50,50,42,1
Style: TopLeftPill,Malgun Gothic,32,&H00FFFFFF,&H0000FFFF,&H55000000,&H55000000,-1,0,0,0,100,100,1,0,3,10,0,7,42,42,32,1
Style: TopRightBrand,Malgun Gothic,34,&H0000D4FF,&H0000FFFF,&H00000000,&H00000000,-1,0,0,0,100,100,2,0,1,4,2,9,45,45,32,1
Style: LiveTelemetryHUD,Malgun Gothic,29,&H0000DFFF,&H0000FFFF,&H58000000,&H58000000,-1,0,0,0,100,100,1,0,3,9,0,9,45,45,86,1
Style: SpecCard,Malgun Gothic,31,&H00E8E8E8,&H0000FFFF,&H58000000,&H58000000,-1,0,0,0,100,100,1,0,3,10,0,1,45,45,128,1
Style: GiantRedSlam,Malgun Gothic,145,&H00221CF0,&H0000FFFF,&H00000000,&H00000000,-1,0,0,0,100,100,4,0,1,12,6,5,40,40,40,1
Style: GiantSubLabel,Malgun Gothic,46,&H0000DFFF,&H0000FFFF,&H00000000,&H00000000,-1,0,0,0,100,100,2,0,1,5,2,5,40,40,40,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    with open(ass_path, "w", encoding="utf-8-sig") as f:
        f.write(ass_header)
        f.write(f"Dialogue: 2,0:00:00.00,{format_ass_time(total_dur)},TopRightBrand,,0,0,0,,머니 아카이브\n")

        # Chapter Top-Left Topic Pills mapped by timeline progress
        chapter_defs = [
            (0.00, 0.16, "233년 왕실 은행 파산 미스터리"),
            (0.16, 0.36, "고졸 해결사와 치명적 겸직 함정"),
            (0.36, 0.56, "비밀계좌 '88888'과 눈먼 임원들"),
            (0.56, 0.72, "고베 대지진 · 3조 증발과 아이러니"),
            (0.72, 0.88, "[2부] 제롬 케르비엘 · 70조 유령 도박"),
            (0.88, 1.00, "3일 만에 9조 증발 · 법정 대반전"),
        ]
        for r0, r1, ch_title in chapter_defs:
            f.write(
                f"Dialogue: 2,{format_ass_time(total_dur*r0)},{format_ass_time(total_dur*r1)},TopLeftPill,,0,0,0,,"
                f"  {{\\c&H002820F0&}}● /{{\\c&H00FFFFFF&}} {ch_title}  \n"
            )

        # Spec cards & Giant Blackout Slam Cards
        shown_cards = set()
        for i, seg_s, seg_e, full_dur, txt, img_key, spec_card in sent_timings:
            s_str, e_str = format_ass_time(seg_s), format_ass_time(seg_e)
            if spec_card and spec_card not in shown_cards:
                shown_cards.add(spec_card)
                card_end = format_ass_time(min(seg_e - 0.1, seg_s + 6.0))
                formatted_card = f"  {{\\c&H002820F0&}}▌{{\\c&H00E8E8E8&}}{spec_card[1:]}  "
                f.write(f"Dialogue: 2,{s_str},{card_end},SpecCard,,0,0,0,,{{\\fad(180,250)}}{formatted_card}\n")

            if img_key == "blackout":
                if "1파운드" in txt or "1,700원" in txt:
                    f.write(
                        f"Dialogue: 4,{s_str},{e_str},GiantRedSlam,,0,0,0,,"
                        f"{{\\pos(960,465)\\fscx135\\fscy135\\t(0,220,\\fscx100\\fscy100)\\fad(60,250)}}매각가 £1 (1,700원)\n"
                    )
                    f.write(
                        f"Dialogue: 4,{s_str},{e_str},GiantSubLabel,,0,0,0,,"
                        f"{{\\pos(960,625)\\fad(200,250)}}233년 대영제국 왕실 은행의 최후\n"
                    )
                else:
                    f.write(
                        f"Dialogue: 4,{s_str},{e_str},GiantRedSlam,,0,0,0,,"
                        f"{{\\pos(960,465)\\fscx135\\fscy135\\t(0,220,\\fscx100\\fscy100)\\fad(60,250)}}-9,000,000,000,000원\n"
                    )
                    f.write(
                        f"Dialogue: 4,{s_str},{e_str},GiantSubLabel,,0,0,0,,"
                        f"{{\\pos(960,625)\\fad(200,250)}}단 3일 만에 증발한 인류 역사상 개인 최대 금융 손실\n"
                    )

        # Animated Live Financial Debt Counter HUD (Account 88888 spiral: 36% ~ 66% of timeline)
        hud1_s, hud1_e = total_dur * 0.36, total_dur * 0.66
        steps1 = 60
        dt1 = (hud1_e - hud1_s) / steps1
        for st in range(steps1):
            t0, t1 = hud1_s + st * dt1, hud1_s + (st + 1) * dt1
            prog = (st + 1) / steps1
            debt_eok = int(0.3 + 29999.7 * (prog ** 2.4))
            filled = min(10, max(1, int(prog * 10)))
            bar = "█" * filled + "░" * (10 - filled)
            disp = f"-{debt_eok:,}억 원" if debt_eok < 10000 else f"-{debt_eok/10000:.2f}조 원"
            f.write(
                f"Dialogue: 2,{format_ass_time(t0)},{format_ass_time(t1)},LiveTelemetryHUD,,0,0,0,,"
                f"  📉 {{\\c&H00FFFFFF&}}비밀계좌 88888 누적 손실 : {{\\c&H002820F0&}}{disp} {bar}  \n"
            )

        # Animated Live Kerviel Ghost Position Counter HUD (74% ~ 90% of timeline)
        hud2_s, hud2_e = total_dur * 0.74, total_dur * 0.90
        steps2 = 45
        dt2 = (hud2_e - hud2_s) / steps2
        for st in range(steps2):
            t0, t1 = hud2_s + st * dt2, hud2_s + (st + 1) * dt2
            prog = (st + 1) / steps2
            bet_jo = round(1.0 + 69.0 * (prog ** 1.6), 1)
            ghost_cnt = int(12 + 935 * prog)
            f.write(
                f"Dialogue: 2,{format_ass_time(t0)},{format_ass_time(t1)},LiveTelemetryHUD,,0,0,0,,"
                f"  ⚠️ {{\\c&H00FFFFFF&}}케르비엘 무단 베팅 : {{\\c&H0000DFFF&}}{bet_jo}조 원 {{\\c&H002820F0&}}(유령거래 {ghost_cnt}건)  \n"
            )

        # Crisp 1-line broadcast subtitles
        for _, seg_s, seg_e, _, txt, _, _ in sent_timings:
            # Use actual narration speech end from sentence object
            pass
        for s_obj in sentences:
            for p_s, p_e, phrase in split_into_one_line_phrases(s_obj["text"], s_obj["start"], s_obj["end"]):
                colored = colorize_keywords(phrase)
                sub_line = f"  {{\\c&H0000D4FF&}}▌{{\\c&H00FFFFFF&}} {colored}  "
                f.write(f"Dialogue: 3,{format_ass_time(p_s)},{format_ass_time(p_e)},DocSubOneLine,,0,0,0,,{sub_line}\n")

    clips_txt = os.path.join(ASSETS_DIR, "clips_concat.txt")
    with open(clips_txt, "w", encoding="utf-8") as f:
        for cid in subclip_order:
            f.write(f"file '{clip_paths[cid].replace(chr(92), '/')}'\n")

    ass_esc = ass_path.replace("\\", "/").replace(":", "\\:")
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", clips_txt, "-i", master_m4a,
        "-vf", f"ass='{ass_esc}',format=yuv420p",
        "-map", "0:v", "-map", "1:a", "-t", f"{total_dur:.2f}",
        "-c:v", "libx264", "-profile:v", "main", "-pix_fmt", "yuv420p",
        "-preset", "veryfast", "-crf", "19", "-c:a", "copy", "-movflags", "+faststart",
        OUT_FULL_MP4
    ], check=True, capture_output=True)
    print("SUCCESS! Full 16:9 Documentary Rendered:", OUT_FULL_MP4)

    # === Build 9:16 Vertical Shorts Video ===
    short_raw = parse_srt_file(SHORTS_SRT)
    short_sents = merge_into_sentences(short_raw)
    shorts_dur = max(get_audio_duration(SHORTS_MP3), short_sents[-1]["end"]) + 0.8

    shorts_sfx = [
        (0.05, os.path.join(SFX_DIR, "sfx_stamp_slam.wav"), 0.85),
        (10.0, os.path.join(SFX_DIR, "sfx_crt_88888_beep.wav"), 0.80),
        (28.0, os.path.join(SFX_DIR, "sfx_market_crash_rumble.wav"), 0.85),
        (45.0, os.path.join(SFX_DIR, "sfx_deep_riser_boom.wav"), 0.78),
    ]
    shorts_sfx_wav = os.path.join(ASSETS_DIR, "shorts_sfx.wav")
    mix_sfx_timeline(shorts_dur, shorts_sfx, shorts_sfx_wav)

    shorts_m4a = os.path.join(ASSETS_DIR, "shorts_master.m4a")
    subprocess.run([
        "ffmpeg", "-y", "-i", SHORTS_MP3, "-stream_loop", "-1", "-i", bgm_1, "-i", shorts_sfx_wav,
        "-filter_complex", (
            "[0:a]volume=1.55,equalizer=f=3200:t=q:w=1.2:g=2.6[voice];"
            "[1:a]volume=0.36[bgm];"
            "[2:a]lowpass=f=3800,volume=0.55[sfx];"
            "[voice][bgm][sfx]amix=inputs=3:duration=first:dropout_transition=2:normalize=0[aout]"
        ),
        "-map", "[aout]", "-t", f"{shorts_dur:.2f}",
        "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2", shorts_m4a
    ], check=True, capture_output=True)

    shorts_visual_keys = [
        "thumb_smiling_trader", "ch3_account_88888_crt", "ch2_dual_key_desk",
        "ch3_london_champagne_boardroom", "ch4_kobe_earthquake_1995",
        "ch4_frankfurt_arrest_stage", "ch5_kerviel_ghost_terminal", "ch6_french_courtroom_gavel"
    ]
    shorts_concat = os.path.join(ASSETS_DIR, "shorts_concat.txt")
    with open(shorts_concat, "w", encoding="utf-8") as f:
        prev_t = 0.0
        for idx_s, s_obj in enumerate(short_sents):
            seg_e = shorts_dur if idx_s == len(short_sents) - 1 else short_sents[idx_s + 1]["start"]
            dur = max(0.8, seg_e - prev_t)
            prev_t = seg_e
            vkey = shorts_visual_keys[idx_s % len(shorts_visual_keys)]
            sc_mp4 = os.path.join(CLIPS_DIR, f"shorts_v_{idx_s:02d}.mp4")
            frames = max(24, int(round(dur * 24)))
            fn_1 = max(1, frames - 1)
            subprocess.run([
                "ffmpeg", "-y", "-i", img_paths[vkey],
                "-vf", (
                    "scale=2160:2160:force_original_aspect_ratio=increase,crop=2160:2160,"
                    f"zoompan=z='1.0+0.10*(on/{fn_1})':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s=1080x1080:fps=24,"
                    "pad=1080:1920:0:420:color=#070a10,format=yuv420p"
                ),
                "-t", f"{dur:.3f}", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "20", "-an", sc_mp4
            ], check=True, capture_output=True)
            f.write(f"file '{sc_mp4.replace(chr(92), '/')}'\n")

    shorts_ass = os.path.join(ASSETS_DIR, "shorts_overlay.ass")
    shorts_ass_header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: TopHook1,Malgun Gothic,66,&H00FFFFFF,&H0000FFFF,&H00000000,&H00000000,-1,0,0,0,100,100,-1,0,1,8,4,8,40,40,145,1
Style: TopHook2,Malgun Gothic,72,&H0000E8FF,&H0000FFFF,&H00000000,&H00000000,-1,0,0,0,100,100,-1,0,1,9,4,8,40,40,235,1
Style: ShortsSub,Malgun Gothic,56,&H00FFFFFF,&H0000FFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,8,3,2,55,55,270,1
Style: BrandBottom,Malgun Gothic,36,&H0000D4FF,&H0000FFFF,&H00000000,&H00000000,-1,0,0,0,100,100,3,0,1,4,0,2,40,40,120,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    with open(shorts_ass, "w", encoding="utf-8-sig") as f:
        f.write(shorts_ass_header)
        f.write(f"Dialogue: 2,0:00:00.00,{format_ass_time(shorts_dur)},TopHook1,,0,0,0,,233년 영국 왕실 은행을\n")
        f.write(f"Dialogue: 2,0:00:00.00,{format_ass_time(shorts_dur)},TopHook2,,0,0,0,,1,700원에 파산시킨 신입?!\n")
        f.write(f"Dialogue: 2,0:00:00.00,{format_ass_time(shorts_dur)},BrandBottom,,0,0,0,,머니 아카이브 | 풀버전 본편 확인\n")
        for s_obj in short_sents:
            for p_s, p_e, phrase in split_into_one_line_phrases(s_obj["text"], s_obj["start"], s_obj["end"]):
                colored = colorize_keywords(phrase)
                f.write(f"Dialogue: 3,{format_ass_time(p_s)},{format_ass_time(p_e)},ShortsSub,,0,0,0,,{colored}\n")

    shorts_ass_esc = shorts_ass.replace("\\", "/").replace(":", "\\:")
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", shorts_concat, "-i", shorts_m4a,
        "-vf", f"ass='{shorts_ass_esc}',format=yuv420p",
        "-map", "0:v", "-map", "1:a", "-t", f"{shorts_dur:.2f}",
        "-c:v", "libx264", "-profile:v", "main", "-pix_fmt", "yuv420p",
        "-preset", "veryfast", "-crf", "19", "-c:a", "copy", "-movflags", "+faststart",
        OUT_SHORTS_MP4
    ], check=True, capture_output=True)
    print("SUCCESS! Vertical 9:16 Shorts Rendered:", OUT_SHORTS_MP4)


if __name__ == "__main__":
    build_ep01_masterpiece()
