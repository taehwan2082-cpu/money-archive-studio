import math
import os
import random
import struct
import wave

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EP1_DIR = os.path.join(BASE_DIR, "ep01_barings_kr")
ASSETS_DIR = os.path.join(EP1_DIR, "assets")
SFX_DIR = os.path.join(ASSETS_DIR, "sfx")
os.makedirs(SFX_DIR, exist_ok=True)

SR = 44100


def save_wav(path: str, samples: list[float], gain: float = 0.9):
    peak = max((abs(x) for x in samples), default=1.0)
    if peak < 1e-6:
        peak = 1.0
    scale = (32767.0 * gain) / peak
    buf = bytearray()
    for s in samples:
        v = max(-32767, min(32767, int(s * scale)))
        buf.extend(struct.pack("<h", v))
    with wave.open(path, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes(bytes(buf))


def make_deep_riser_boom(path: str):
    """Suspense riser + dark financial thriller sub-bass braam (3.4s)"""
    n = int(3.4 * SR)
    rng = random.Random(101)
    out = []
    phase = 0.0
    for i in range(n):
        t = i / SR
        if t < 1.5:
            prog = (t / 1.5) ** 2.2
            freq = 50.0 + 360.0 * prog
            phase += 2 * math.pi * freq / SR
            riser = math.sin(phase) * prog * 0.72 + rng.uniform(-1, 1) * (prog ** 3) * 0.30
            out.append(riser)
        else:
            bt = t - 1.5
            f_boom = 30.0 + 48.0 * math.exp(-bt * 8.0)
            boom = math.sin(2 * math.pi * f_boom * bt) * math.exp(-bt * 1.8) * 1.45
            braam = (
                0.50 * math.sin(2 * math.pi * 65.41 * bt)
                + 0.35 * math.sin(2 * math.pi * 130.81 * bt)
                + 0.20 * math.sin(2 * math.pi * 196.00 * bt)
            ) * math.exp(-bt * 2.2)
            hit = rng.uniform(-1, 1) * math.exp(-bt * 20.0) * 0.55
            out.append(boom + braam + hit)
    save_wav(path, out, gain=0.92)


def make_stamp_slam(path: str):
    """Heavy metallic bank stamp / £1 bankruptcy seal impact (2.5s)"""
    n = int(2.5 * SR)
    rng = random.Random(202)
    out = []
    for i in range(n):
        t = i / SR
        f_sub = 30.0 + 60.0 * math.exp(-t * 10.0)
        sub = math.sin(2 * math.pi * f_sub * t) * math.exp(-t * 2.4) * 1.4
        clang = (
            0.42 * math.sin(2 * math.pi * 210.0 * t) * math.exp(-t * 6.5)
            + 0.30 * math.sin(2 * math.pi * 385.0 * t) * math.exp(-t * 9.0)
            + 0.22 * math.sin(2 * math.pi * 710.0 * t) * math.exp(-t * 13.0)
        )
        noise = rng.uniform(-1, 1) * math.exp(-t * 26.0) * 0.95
        out.append(sub + clang + noise)
    save_wav(path, out, gain=0.95)


def make_crt_88888_beep(path: str):
    """5 mechanical keystrokes ('8-8-8-8-8') + retro CRT terminal confirmation beep (2.6s)"""
    n = int(2.6 * SR)
    rng = random.Random(303)
    out = [0.0] * n
    key_times = [0.10, 0.32, 0.54, 0.76, 0.98]
    for kt in key_times:
        s_idx = int(kt * SR)
        for j in range(int(0.06 * SR)):
            if s_idx + j < n:
                 dt = j / SR
                 click = rng.uniform(-1, 1) * math.exp(-dt * 95.0) * 0.9 + math.sin(2 * math.pi * 1250 * dt) * math.exp(-dt * 70.0) * 0.5
                 out[s_idx + j] += click
    beep_start = int(1.30 * SR)
    for j in range(int(0.85 * SR)):
        if beep_start + j < n:
            dt = j / SR
            env = math.exp(-dt * 3.2)
            beep = (0.55 * math.sin(2 * math.pi * 880.0 * dt) + 0.25 * math.sin(2 * math.pi * 1760.0 * dt)) * env
            out[beep_start + j] += beep
    save_wav(path, out, gain=0.85)


def make_market_crash_rumble(path: str):
    """Earthquake tremor + violent stock crash downward pitch plunge (3.8s)"""
    n = int(3.8 * SR)
    rng = random.Random(404)
    out = []
    lp = 0.0
    phase = 0.0
    for i in range(n):
        t = i / SR
        env = min(1.0, t / 0.12) * math.exp(-max(0.0, t - 1.2) * 0.85)
        raw = rng.uniform(-1, 1)
        lp = 0.90 * lp + 0.10 * raw
        f_drop = max(26.0, 140.0 - 32.0 * t)
        phase += 2 * math.pi * f_drop / SR
        sub = math.sin(phase) * 0.95
        out.append(env * (lp * 1.1 + sub))
    save_wav(path, out, gain=0.92)


def make_trading_bell_panic(path: str):
    """Urgent exchange brass bell + warning alert pulse (3.0s)"""
    n = int(3.0 * SR)
    out = []
    for i in range(n):
        t = i / SR
        strike = (t % 0.22)
        bell_env = math.exp(-strike * 14.0) if t < 1.54 else math.exp(-(t - 1.54) * 3.0)
        bell = (
            0.50 * math.sin(2 * math.pi * 1046.5 * t)
            + 0.35 * math.sin(2 * math.pi * 1568.0 * t)
            + 0.25 * math.sin(2 * math.pi * 2217.5 * t)
        ) * bell_env * 0.65
        low_pulse = math.sin(2 * math.pi * 55.0 * t) * math.exp(-t * 1.1) * 0.5
        out.append(bell + low_pulse)
    save_wav(path, out, gain=0.85)


def make_court_gavel(path: str):
    """Double wooden judge gavel strike with hall reverb (2.4s)"""
    n = int(2.4 * SR)
    rng = random.Random(606)
    out = [0.0] * n
    for hit_t in (0.08, 0.52):
        s_idx = int(hit_t * SR)
        for j in range(int(1.2 * SR)):
            if s_idx + j < n:
                dt = j / SR
                wood = (
                    0.75 * math.sin(2 * math.pi * 165.0 * dt) * math.exp(-dt * 18.0)
                    + 0.55 * math.sin(2 * math.pi * 340.0 * dt) * math.exp(-dt * 25.0)
                    + rng.uniform(-1, 1) * math.exp(-dt * 40.0) * 0.85
                )
                reverb = rng.uniform(-1, 1) * math.exp(-dt * 3.8) * 0.12
                out[s_idx + j] += wood + reverb
    save_wav(path, out, gain=0.92)


if __name__ == "__main__":
    make_deep_riser_boom(os.path.join(SFX_DIR, "sfx_deep_riser_boom.wav"))
    make_stamp_slam(os.path.join(SFX_DIR, "sfx_stamp_slam.wav"))
    make_crt_88888_beep(os.path.join(SFX_DIR, "sfx_crt_88888_beep.wav"))
    make_market_crash_rumble(os.path.join(SFX_DIR, "sfx_market_crash_rumble.wav"))
    make_trading_bell_panic(os.path.join(SFX_DIR, "sfx_trading_bell_panic.wav"))
    make_court_gavel(os.path.join(SFX_DIR, "sfx_court_gavel.wav"))
    print("Generated all 6 custom financial thriller SFX WAV files in:", SFX_DIR)
