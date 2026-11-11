import os
import sys
import asyncio
import edge_tts

sys.stdout.reconfigure(encoding='utf-8')
BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ep01_barings_kr")

def fmt_srt_time(ns_100):
    ms_total = int(ns_100 // 10000)
    hrs = ms_total // 3600000
    rem = ms_total % 3600000
    mins = rem // 60000
    rem = rem % 60000
    secs = rem // 1000
    ms = rem % 1000
    return f"{hrs:02d}:{mins:02d}:{secs:02d},{ms:03d}"

async def build_audio_and_srt(text, mp3_path, srt_path, voice="ko-KR-InJoonNeural", rate="+10%"):
    communicate = edge_tts.Communicate(text, voice, rate=rate)
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
    print(f"Generated: {mp3_path} ({os.path.getsize(mp3_path):,} bytes) & {srt_path} ({len(srt_entries)} subtitle blocks)")

async def main():
    long_txt = open(os.path.join(BASE_DIR, "script_longform_kr.txt"), encoding="utf-8").read()
    short_txt = open(os.path.join(BASE_DIR, "script_shorts_kr.txt"), encoding="utf-8").read()
    await build_audio_and_srt(
        long_txt,
        os.path.join(BASE_DIR, "ep01_longform_kr.mp3"),
        os.path.join(BASE_DIR, "ep01_longform_kr.srt")
    )
    await build_audio_and_srt(
        short_txt,
        os.path.join(BASE_DIR, "ep01_shorts_kr.mp3"),
        os.path.join(BASE_DIR, "ep01_shorts_kr.srt"),
        rate="+15%"
    )

if __name__ == "__main__":
    asyncio.run(main())
