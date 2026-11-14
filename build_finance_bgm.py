import math
import os
import struct
import wave


def build_financial_thriller_bgm(out_wav: str, duration_sec: float = 96.0, sr: int = 44100):
    """Synthesizes a sleek, modern Bloomberg/Netflix-style Dark Electronic Financial Thriller BGM loop
    (deep sub-bass heartbeat pulse + crisp ticking synth clock + tense C-minor atmospheric pad progression).
    """
    n_samples = int(duration_sec * sr)
    buf = bytearray()

    # 4-chord dark financial thriller progression (Cm -> Abmaj7 -> Fm -> Gsus4/G)
    # Each chord lasts 8 seconds (32s cycle x 3 = 96s seamless loop!)
    chords = [
        (65.41, [130.81, 155.56, 196.00, 293.66]),  # Cm9
        (51.91, [103.83, 155.56, 196.00, 246.94]),  # Abmaj7
        (43.65, [87.31, 130.81, 174.61, 207.65]),   # Fm7
        (49.00, [98.00, 146.83, 196.00, 233.08]),   # Gm7 / tense dominant
    ]

    bpm = 105.0
    beat_dur = 60.0 / bpm
    sixteenth = beat_dur / 4.0

    for i in range(n_samples):
        t = i / sr
        chord_idx = int((t / 8.0)) % 4
        bass_freq, pad_freqs = chords[chord_idx]

        # 1. Warm dark atmospheric pad (smooth detuned sine/triangle blend, zero harshness)
        pad = 0.0
        chord_local_t = t % 8.0
        chord_env = min(1.0, chord_local_t / 1.2) * min(1.0, (8.0 - chord_local_t) / 1.2)
        for idx_f, pf in enumerate(pad_freqs):
            lfo = 1.0 + 0.002 * math.sin(2.0 * math.pi * (0.25 + 0.07 * idx_f) * t)
            pad += math.sin(2.0 * math.pi * pf * lfo * t) * (0.055 / (1.0 + 0.2 * idx_f))
        pad *= chord_env

        # 2. Deep cinematic sub-bass pulse on beats (Hans Zimmer / Dark Finance documentary feel)
        beat_pos = (t % beat_dur) / beat_dur
        sub_env = math.exp(-5.5 * beat_pos)
        sub = math.sin(2.0 * math.pi * bass_freq * t) * 0.22 * sub_env
        sub += math.sin(2.0 * math.pi * (bass_freq * 2.0) * t) * 0.06 * (sub_env ** 1.5)

        # 3. Subtle tense ticking 16th-note pulse (gives momentum & retention energy!)
        step_idx = int(t / sixteenth) % 16
        step_pos = (t % sixteenth) / sixteenth
        accent = 1.0 if step_idx in (0, 3, 6, 8, 11, 14) else 0.42
        # Act escalation: slightly more energetic pulse in second half of cycle
        act_gain = 0.85 + 0.25 * math.sin(2.0 * math.pi * t / 32.0)
        tick_env = math.exp(-26.0 * step_pos)
        tick_freq = pad_freqs[step_idx % len(pad_freqs)] * 2.0
        tick = math.sin(2.0 * math.pi * tick_freq * t) * 0.048 * accent * act_gain * tick_env

        # Seamless loop fade at very edges (first/last 0.5s)
        master_env = 1.0
        if t < 0.5:
            master_env = t / 0.5
        elif t > duration_sec - 0.5:
            master_env = (duration_sec - t) / 0.5

        val = (pad + sub + tick) * master_env
        sample_int = max(-32000, min(32000, int(val * 32767)))
        # Stereo with subtle width on pad
        val_r = (pad * 0.94 - tick * 0.85 + sub) * master_env
        sample_r = max(-32000, min(32000, int(val_r * 32767)))
        buf.extend(struct.pack("<hh", sample_int, sample_r))

    os.makedirs(os.path.dirname(out_wav), exist_ok=True)
    with wave.open(out_wav, "w") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(bytes(buf))
    print(f"Synthesized sleek financial thriller BGM: {out_wav} ({os.path.getsize(out_wav):,} bytes)")


if __name__ == "__main__":
    base = os.path.dirname(os.path.abspath(__file__))
    build_financial_thriller_bgm(os.path.join(base, "assets_shared", "finance_thriller_pulse_bgm.wav"), duration_sec=64.0)
