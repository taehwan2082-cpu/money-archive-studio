import asyncio
import json
import os
import subprocess
import sys
import edge_tts

sys.stdout.reconfigure(encoding="utf-8")
STUDIO_DIR = os.path.dirname(os.path.abspath(__file__))

# v3.0 Strict Duration Guards:
# - Longform audio >= 500.0s (8m 20s+) so final MP4 safely clears YouTube's 8m 00s mid-roll threshold
# - Shorts audio <= 46.5s (36~45s cliffhanger teaser, zero ending spoilers!)
MIN_LONGFORM_AUDIO_SEC = 500.0
MAX_SHORTS_AUDIO_SEC = 46.5


def get_audio_duration(path: str) -> float:
    cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", path]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return float(json.loads(res.stdout)["format"]["duration"])


def fmt_srt_time(ns_100: int) -> str:
    ms_total = int(ns_100 // 10000)
    hrs = ms_total // 3600000
    rem = ms_total % 3600000
    mins = rem // 60000
    rem = rem % 60000
    secs = rem // 1000
    ms = rem % 1000
    return f"{hrs:02d}:{mins:02d}:{secs:02d},{ms:03d}"


async def build_audio_and_srt(
    text: str,
    mp3_path: str,
    srt_path: str,
    voice: str = "ko-KR-InJoonNeural",
    rate: str = "+10%",
    pitch: str = "-2Hz",
) -> float:
    communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
    srt_entries = []
    idx = 1
    with open(mp3_path, "wb") as f:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] in ("SentenceBoundary", "WordBoundary"):
                start = fmt_srt_time(chunk["offset"])
                end = fmt_srt_time(chunk["offset"] + chunk["duration"])
                txt = chunk["text"].strip()
                if txt:
                    srt_entries.append(f"{idx}\n{start} --> {end}\n{txt}\n")
                    idx += 1
    with open(srt_path, "w", encoding="utf-8") as sf:
        sf.write("\n".join(srt_entries))
    dur = get_audio_duration(mp3_path)
    print(
        f"[OK] {os.path.basename(mp3_path)} ({dur:.1f}s, rate={rate}) | "
        f"{os.path.basename(srt_path)} ({len(srt_entries)} blocks)",
        flush=True,
    )
    return dur


async def process_episode(ep_folder: str, prefix: str = "", force: bool = False):
    ep_dir = os.path.join(STUDIO_DIR, ep_folder)
    if not prefix:
        prefix = ep_folder.split("_")[0]

    long_txt = open(os.path.join(ep_dir, "script_longform_kr.txt"), encoding="utf-8").read().strip()
    short_txt = open(os.path.join(ep_dir, "script_shorts_kr.txt"), encoding="utf-8").read().strip()

    short_chars = len("".join(short_txt.split()))
    if short_chars > 540:
        raise ValueError(
            f"[{ep_folder}] script_shorts_kr.txt non-whitespace length ({short_chars} chars) is too long! "
            f"Keep Shorts 36~45s (<= 540 chars) and cut at the cliffhanger without spoiling the ending."
        )

    long_mp3 = os.path.join(ep_dir, f"{prefix}_longform_kr.mp3")
    long_srt = os.path.join(ep_dir, f"{prefix}_longform_kr.srt")
    short_mp3 = os.path.join(ep_dir, f"{prefix}_shorts_kr.mp3")
    short_srt = os.path.join(ep_dir, f"{prefix}_shorts_kr.srt")

    if force or not (os.path.exists(long_mp3) and os.path.exists(long_srt) and os.path.getsize(long_srt) > 500):
        dur = await build_audio_and_srt(long_txt, long_mp3, long_srt, rate="+10%", pitch="-2Hz")
        for fallback_rate in ("+6%", "+3%"):
            if dur >= MIN_LONGFORM_AUDIO_SEC:
                break
            print(f"[{ep_folder}] Longform {dur:.1f}s < {MIN_LONGFORM_AUDIO_SEC:.0f}s -> re-synthesizing at {fallback_rate}", flush=True)
            dur = await build_audio_and_srt(long_txt, long_mp3, long_srt, rate=fallback_rate, pitch="-2Hz")
        if dur < 485.0:
            raise RuntimeError(
                f"[{ep_folder}] Longform audio ({dur:.1f}s) is still below 8m 05s (485s) mid-roll threshold! "
                f"Expand script_longform_kr.txt before rendering."
            )
    else:
        print(f"[SKIP] {os.path.basename(long_mp3)} already complete", flush=True)

    if force or not (os.path.exists(short_mp3) and os.path.exists(short_srt) and os.path.getsize(short_srt) > 100):
        s_dur = await build_audio_and_srt(short_txt, short_mp3, short_srt, rate="+18%", pitch="-1Hz")
        if s_dur > MAX_SHORTS_AUDIO_SEC:
            print(f"[{ep_folder}] Shorts {s_dur:.1f}s > {MAX_SHORTS_AUDIO_SEC:.1f}s -> tightening pace to +24%", flush=True)
            s_dur = await build_audio_and_srt(short_txt, short_mp3, short_srt, rate="+24%", pitch="-1Hz")
        if s_dur > 48.0:
            raise RuntimeError(
                f"[{ep_folder}] Shorts audio ({s_dur:.1f}s) exceeds v3.0 cliffhanger cap (48s)! Trim script_shorts_kr.txt."
            )
    else:
        print(f"[SKIP] {os.path.basename(short_mp3)} already complete", flush=True)


async def main():
    raw_args = sys.argv[1:]
    force = "--force" in raw_args
    targets = [a for a in raw_args if a != "--force"] or ["ep02_archegos_kr", "ep03_jholow_kr"]
    for folder in targets:
        await process_episode(folder, force=force)


if __name__ == "__main__":
    asyncio.run(main())
