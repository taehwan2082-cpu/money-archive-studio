import asyncio
import os
import sys
import edge_tts

sys.stdout.reconfigure(encoding="utf-8")
STUDIO_DIR = os.path.dirname(os.path.abspath(__file__))


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
    rate: str = "+12%",
    pitch: str = "-2Hz",
):
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
    print(
        f"[OK] {os.path.basename(mp3_path)} ({os.path.getsize(mp3_path):,} bytes) | "
        f"{os.path.basename(srt_path)} ({len(srt_entries)} blocks)",
        flush=True,
    )


async def process_episode(ep_folder: str, prefix: str):
    ep_dir = os.path.join(STUDIO_DIR, ep_folder)
    long_txt = open(os.path.join(ep_dir, "script_longform_kr.txt"), encoding="utf-8").read()
    short_txt = open(os.path.join(ep_dir, "script_shorts_kr.txt"), encoding="utf-8").read()

    long_mp3 = os.path.join(ep_dir, f"{prefix}_longform_kr.mp3")
    long_srt = os.path.join(ep_dir, f"{prefix}_longform_kr.srt")
    short_mp3 = os.path.join(ep_dir, f"{prefix}_shorts_kr.mp3")
    short_srt = os.path.join(ep_dir, f"{prefix}_shorts_kr.srt")

    if not (os.path.exists(long_mp3) and os.path.exists(long_srt) and os.path.getsize(long_srt) > 500):
        await build_audio_and_srt(long_txt, long_mp3, long_srt, rate="+12%", pitch="-2Hz")
    else:
        print(f"[SKIP] {os.path.basename(long_mp3)} already complete", flush=True)

    if not (os.path.exists(short_mp3) and os.path.exists(short_srt) and os.path.getsize(short_srt) > 100):
        await build_audio_and_srt(short_txt, short_mp3, short_srt, rate="+18%", pitch="-1Hz")
    else:
        print(f"[SKIP] {os.path.basename(short_mp3)} already complete", flush=True)


async def main():
    await process_episode("ep02_archegos_kr", "ep02")
    await process_episode("ep03_jholow_kr", "ep03")


if __name__ == "__main__":
    asyncio.run(main())
