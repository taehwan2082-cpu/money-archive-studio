from concurrent.futures import ThreadPoolExecutor, as_completed
import glob
import json
import os
import re
import struct
import subprocess
import sys
import wave

sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SFX_DIR = os.path.join(BASE_DIR, "ep01_barings_kr", "assets", "sfx")
BGM_WAV = os.path.join(BASE_DIR, "assets_shared", "finance_thriller_pulse_bgm.wav")
QUEUE_JSON = os.path.join(BASE_DIR, "auto_pipeline", "episode_queue.json")

MOTIONS = ["zoom_in", "pan_right", "zoom_out", "pan_left", "plunge_down", "rise_up"]


def ensure_audio_assets():
    if not os.path.exists(BGM_WAV):
        subprocess.run([sys.executable, os.path.join(BASE_DIR, "build_finance_bgm.py")], check=True)
    if not os.path.exists(os.path.join(SFX_DIR, "sfx_stamp_slam.wav")):
        subprocess.run([sys.executable, os.path.join(BASE_DIR, "build_finance_sfx.py")], check=True)


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
            entries.append({
                "idx": idx,
                "start": to_sec(s_str),
                "end": to_sec(e_str),
                "text": " ".join(lines[2:]),
            })
    return entries


def get_audio_duration(path: str) -> float:
    res = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", path],
        capture_output=True,
        text=True,
        check=True,
    )
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


def format_ass_time(seconds: float) -> str:
    seconds = max(0.0, seconds)
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def split_into_one_line_phrases(text: str, start: float, end: float, max_chars: int = 27) -> list[tuple[float, float, str]]:
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
            if w.endswith(",") or cur_len >= chunk_len:
                phrases.append(" ".join(cur_words))
                cur_words, cur_len = [], 0
    if cur_words:
        phrases.append(" ".join(cur_words))

    total_chars = sum(max(1, len(p)) for p in phrases)
    dur = max(0.2, end - start)
    out, cur_t = [], start
    for i, p in enumerate(phrases):
        nxt_t = end if i == len(phrases) - 1 else cur_t + dur * (max(1, len(p)) / total_chars)
        out.append((cur_t, nxt_t, p))
        cur_t = nxt_t
    return out


DEFAULT_HIGHLIGHTS = [
    r"\d[\d,\.]*\s*(?:조\s*\d[\d,]*억\s*개|조\s*원|억\s*원|천만\s*원|만\s*원|원|달러|유로|센트|개|년형|년|개월|시간|일|명|배|퍼센트|%)",
    r"루나", r"테라", r"권도형", r"FTX", r"샘 뱅크먼프리드", r"테라노스", r"엘리자베스 홈즈",
    r"엔론", r"위워크", r"아담 뉴먼", r"버니 매도프", r"와이어카드", r"루이싱커피", r"니콜라",
    r"죽음의 소용돌이", r"백도어", r"유령 계좌", r"분식회계", r"폰지 사기",
]


def colorize_keywords(line: str, extra_highlights: list[str] | None = None) -> str:
    pats = list(DEFAULT_HIGHLIGHTS) + (extra_highlights or [])
    combined = "(" + "|".join(pats) + ")"
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


def render_one_smooth_clip(task: tuple) -> tuple[str, str]:
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
        zp = f"zoompan=z='1.10':x='(iw-iw/zoom)*0.50':y='(ih-ih/zoom)*(0.16+0.68*(on/{fn_1}))':d={frames}:s=1920x1080:fps=24"
    elif motion_type == "rise_up":
        zp = f"zoompan=z='1.10':x='(iw-iw/zoom)*0.50':y='(ih-ih/zoom)*(0.84-0.68*(on/{fn_1}))':d={frames}:s=1920x1080:fps=24"
    else:
        zp = f"zoompan=z='1.0':x='0':y='0':d={frames}:s=1920x1080:fps=24"

    if tint == "cold":
        color_vf = "colorbalance=bs=0.09:rs=-0.03,eq=contrast=1.06"
    elif tint == "crimson_alert":
        color_vf = "colorbalance=rs=0.10:gs=-0.04:bs=-0.04,eq=contrast=1.08"
    elif tint == "cyan_lab":
        color_vf = "colorbalance=gs=0.05:bs=0.09:rs=-0.03,eq=contrast=1.06"
    else:
        color_vf = "eq=contrast=1.06:saturation=1.06"

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


def build_episode_v3(ep_folder: str):
    ensure_audio_assets()
    ep_dir = os.path.join(BASE_DIR, ep_folder)
    prefix = ep_folder.split("_")[0]
    assets_dir = os.path.join(ep_dir, "assets")
    clips_dir = os.path.join(assets_dir, "clips_v3")
    raw_dir = os.path.join(ep_dir, "raw_images")
    os.makedirs(clips_dir, exist_ok=True)

    # Load optional spec and upload config
    spec_path = os.path.join(ep_dir, "episode_spec.json")
    spec = json.load(open(spec_path, "r", encoding="utf-8")) if os.path.exists(spec_path) else {}
    cfg_path = os.path.join(ep_dir, f"{prefix}_upload_config.json")
    up_cfg = json.load(open(cfg_path, "r", encoding="utf-8")) if os.path.exists(cfg_path) else {}

    long_mp3 = os.path.join(ep_dir, f"{prefix}_longform_kr.mp3")
    long_srt = os.path.join(ep_dir, f"{prefix}_longform_kr.srt")
    shorts_mp3 = os.path.join(ep_dir, f"{prefix}_shorts_kr.mp3")
    shorts_srt = os.path.join(ep_dir, f"{prefix}_shorts_kr.srt")

    out_long_rel = up_cfg.get("longform", {}).get("video_file", f"{ep_folder}/머니아카이브_{prefix.upper()}_본편.mp4")
    out_shorts_rel = up_cfg.get("shorts", {}).get("video_file", f"{ep_folder}/머니아카이브_{prefix.upper()}_쇼츠_9x16.mp4")
    out_long_mp4 = os.path.join(BASE_DIR, out_long_rel) if not os.path.isabs(out_long_rel) else out_long_rel
    out_shorts_mp4 = os.path.join(BASE_DIR, out_shorts_rel) if not os.path.isabs(out_shorts_rel) else out_shorts_rel

    scene_files = sorted(
        [p for p in glob.glob(os.path.join(raw_dir, "*.*")) if p.lower().endswith((".jpg", ".jpeg", ".png", ".webp")) and "thumb" not in os.path.basename(p).lower()]
    )
    if not scene_files:
        scene_files = sorted([p for p in glob.glob(os.path.join(raw_dir, "*.*")) if p.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))])
    if not scene_files:
        raise FileNotFoundError(f"No scene images found in {raw_dir}")

    sentences = parse_srt_file(long_srt)
    total_dur = max(get_audio_duration(long_mp3), sentences[-1]["end"]) + 1.8
    if total_dur < 485.0:
        raise RuntimeError(f"[{ep_folder}] Longform duration ({total_dur:.1f}s) is below 485s mid-roll threshold!")

    tasks = []
    subclip_order = []
    sent_timings = []
    prev_end = 0.0
    tints = ["normal", "cold", "crimson_alert", "cyan_lab"]

    for i, s_obj in enumerate(sentences):
        seg_end = total_dur if i == len(sentences) - 1 else sentences[i + 1]["start"]
        full_dur = max(1.0, seg_end - prev_end)
        n_cuts = max(1, min(5, int(round(full_dur / 4.6))))
        cut_dur = full_dur / n_cuts
        tint = tints[i % len(tints)]
        sent_timings.append((i, prev_end, seg_end, full_dur, s_obj["text"]))
        for c_idx in range(n_cuts):
            img_p = scene_files[(i * 2 + c_idx) % len(scene_files)]
            cid = f"{i:03d}_{c_idx}"
            subclip_order.append(cid)
            tasks.append((clips_dir, cid, img_p, cut_dur, MOTIONS[(i + c_idx * 2) % len(MOTIONS)], tint))
        prev_end = seg_end

    print(f"[{ep_folder}] Rendering {len(tasks)} 4K Ken Burns clips...")
    clip_paths = {}
    with ThreadPoolExecutor(max_workers=4) as ex:
        futs = [ex.submit(render_one_smooth_clip, t) for t in tasks]
        for fut in as_completed(futs):
            cid, cp = fut.result()
            clip_paths[cid] = cp

    sfx_events = [(0.08, os.path.join(SFX_DIR, "sfx_deep_riser_boom.wav"), 0.78)]
    for i, seg_s, _, _, txt in sent_timings:
        if any(w in txt for w in ("파산", "증발", "0원", "휴지조각", "충격")):
            sfx_events.append((seg_s + 0.08, os.path.join(SFX_DIR, "sfx_stamp_slam.wav"), 0.85))
        elif any(w in txt for w in ("폭락", "투매", "뱅크런", "붕괴")):
            sfx_events.append((seg_s + 0.08, os.path.join(SFX_DIR, "sfx_market_crash_rumble.wav"), 0.82))
        elif any(w in txt for w in ("법원", "징역", "구속", "체포", "기소")):
            sfx_events.append((seg_s + 0.10, os.path.join(SFX_DIR, "sfx_court_gavel.wav"), 0.84))
        elif i > 0 and i % 12 == 0:
            sfx_events.append((seg_s + 0.05, os.path.join(SFX_DIR, "sfx_deep_riser_boom.wav"), 0.60))

    sfx_wav = os.path.join(assets_dir, f"{prefix}_sfx_timeline.wav")
    mix_sfx_timeline(total_dur, sfx_events, sfx_wav)

    master_m4a = os.path.join(assets_dir, f"{prefix}_master_audio.m4a")
    subprocess.run(
        [
            "ffmpeg", "-y", "-i", long_mp3,
            "-stream_loop", "-1", "-t", f"{total_dur:.2f}", "-i", BGM_WAV,
            "-i", sfx_wav,
            "-filter_complex", (
                "[0:a]volume=1.58,equalizer=f=3200:t=q:w=1.2:g=2.6[voice];"
                f"[1:a]volume=0.30,afade=t=in:st=0:d=2,afade=t=out:st={max(0.0, total_dur-4.5):.2f}:d=4.5[bgm];"
                "[2:a]lowpass=f=3800,volume=0.55[sfx];"
                "[voice][bgm][sfx]amix=inputs=3:duration=first:dropout_transition=2:normalize=0[aout]"
            ),
            "-map", "[aout]", "-t", f"{total_dur:.2f}",
            "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2", master_m4a,
        ],
        check=True,
        capture_output=True,
    )

    ass_path = os.path.join(assets_dir, f"{prefix}_master_overlay.ass")
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

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    with open(ass_path, "w", encoding="utf-8-sig") as f:
        f.write(ass_header)
        f.write(f"Dialogue: 2,0:00:00.00,{format_ass_time(total_dur)},TopRightBrand,,0,0,0,,머니 아카이브\n")
        pill_title = spec.get("top_pill", up_cfg.get("longform", {}).get("title", "머니 아카이브 금융 실화")[:28])
        f.write(
            f"Dialogue: 2,0:00:00.00,{format_ass_time(total_dur)},TopLeftPill,,0,0,0,,"
            f"  {{\\c&H002820F0&}}● /{{\\c&H00FFFFFF&}} {pill_title}  \n"
        )
        for s_obj in sentences:
            for p_s, p_e, phrase in split_into_one_line_phrases(s_obj["text"], s_obj["start"], s_obj["end"]):
                colored = colorize_keywords(phrase, spec.get("highlights"))
                sub_line = f"  {{\\c&H0000D4FF&}}▌{{\\c&H00FFFFFF&}} {colored}  "
                f.write(f"Dialogue: 4,{format_ass_time(p_s)},{format_ass_time(p_e)},DocSubOneLine,,0,0,0,,{sub_line}\n")

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
            "-c:v", "libx264", "-profile:v", "main", "-pix_fmt", "yuv420p",
            "-preset", "veryfast", "-crf", "19", "-c:a", "copy", "-movflags", "+faststart",
            out_long_mp4,
        ],
        check=True,
        capture_output=True,
    )
    print(f"[{ep_folder}] Longform rendered: {out_long_mp4}")

    # Render Full-Bleed 9:16 Shorts
    short_sents = parse_srt_file(shorts_srt)
    shorts_dur = min(58.5, max(get_audio_duration(shorts_mp3), short_sents[-1]["end"]) + 0.6)
    shorts_m4a = os.path.join(assets_dir, "shorts_master.m4a")
    subprocess.run(
        [
            "ffmpeg", "-y", "-i", shorts_mp3,
            "-stream_loop", "-1", "-t", f"{shorts_dur:.2f}", "-i", BGM_WAV,
            "-filter_complex", (
                "[0:a]volume=1.60,equalizer=f=3200:t=q:w=1.2:g=2.6[voice];"
                f"[1:a]volume=0.32,afade=t=out:st={max(0.0, shorts_dur-2.0):.2f}:d=2.0[bgm];"
                "[voice][bgm]amix=inputs=2:duration=first:dropout_transition=2:normalize=0[aout]"
            ),
            "-map", "[aout]", "-t", f"{shorts_dur:.2f}",
            "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2", shorts_m4a,
        ],
        check=True,
        capture_output=True,
    )

    shorts_concat = os.path.join(assets_dir, "shorts_concat.txt")
    with open(shorts_concat, "w", encoding="utf-8") as f:
        prev_t = 0.0
        c_idx = 0
        for idx_s, s_obj in enumerate(short_sents):
            seg_e = shorts_dur if idx_s == len(short_sents) - 1 else short_sents[idx_s + 1]["start"]
            full_d = max(0.8, seg_e - prev_t)
            prev_t = seg_e
            n_sub = max(2, int(round(full_d / 2.8)))
            sub_d = full_d / n_sub
            for _ in range(n_sub):
                ipath = scene_files[c_idx % len(scene_files)]
                sc_mp4 = os.path.join(clips_dir, f"sh_{c_idx:02d}.mp4")
                frames = max(20, int(round(sub_d * 24)))
                fn_1 = max(1, frames - 1)
                zp = f"zoompan=z='1.0+0.12*(on/{fn_1})':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s=1080x1920:fps=24"
                vf = (
                    "scale=2160:3840:force_original_aspect_ratio=increase,crop=2160:3840,"
                    f"{zp},eq=contrast=1.08:saturation=1.10,vignette=PI/5,format=yuv420p"
                )
                subprocess.run(
                    ["ffmpeg", "-y", "-i", ipath, "-vf", vf, "-t", f"{sub_d:.3f}", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "20", "-an", sc_mp4],
                    check=True,
                    capture_output=True,
                )
                f.write(f"file '{sc_mp4.replace(chr(92), '/')}'\n")
                c_idx += 1

    shorts_ass = os.path.join(assets_dir, "shorts_overlay.ass")
    hook1 = spec.get("shorts_hook_1", "사상 최악의 기업 사기 실화")
    hook2 = spec.get("shorts_hook_2", "머니 아카이브 단독 추적")
    shorts_ass_header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: TopBadge,Malgun Gothic,40,&H00FFFFFF,&H0000FFFF,&H001814DF,&H001814DF,-1,0,0,0,100,100,1,0,3,12,0,8,40,40,125,1
Style: TopHook1,Malgun Gothic,68,&H00FFFFFF,&H0000FFFF,&H00000000,&HC0000000,-1,0,0,0,100,100,-2,0,1,11,5,8,40,40,205,1
Style: TopHook2,Malgun Gothic,74,&H0000DCFF,&H0000FFFF,&H00000000,&HC0000000,-1,0,0,0,100,100,-2,0,1,12,6,8,40,40,295,1
Style: ShortsSub,Malgun Gothic,62,&H00FFFFFF,&H0000FFFF,&H00000000,&HB0000000,-1,0,0,0,100,100,-1,0,1,10,5,2,55,120,480,1
Style: BrandBottom,Malgun Gothic,38,&H0000D4FF,&H0000FFFF,&H00000000,&H90000000,-1,0,0,0,100,100,2,0,1,6,3,2,40,120,390,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    with open(shorts_ass, "w", encoding="utf-8-sig") as f:
        f.write(shorts_ass_header)
        f.write(f"Dialogue: 2,0:00:00.00,{format_ass_time(shorts_dur)},TopBadge,,0,0,0,,  실화 경제다큐 · 머니 아카이브  \n")
        f.write(f"Dialogue: 3,0:00:00.00,{format_ass_time(shorts_dur)},TopHook1,,0,0,0,,{hook1}\n")
        f.write(f"Dialogue: 3,0:00:00.00,{format_ass_time(shorts_dur)},TopHook2,,0,0,0,,{hook2}\n")
        f.write(f"Dialogue: 2,0:00:00.00,{format_ass_time(shorts_dur)},BrandBottom,,0,0,0,,▼ 아래 [관련 동영상]에서 본편 결말 확인\n")
        for s_obj in short_sents:
            for p_s, p_e, phrase in split_into_one_line_phrases(s_obj["text"], s_obj["start"], s_obj["end"], max_chars=16):
                colored = colorize_keywords(phrase, spec.get("highlights"))
                f.write(f"Dialogue: 4,{format_ass_time(p_s)},{format_ass_time(p_e)},ShortsSub,,0,0,0,,{colored}\n")

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
    print(f"[{ep_folder}] Shorts rendered: {out_shorts_mp4}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python build_daily_episode_v3.py <ep_folder>")
        sys.exit(1)
    build_episode_v3(sys.argv[1])
