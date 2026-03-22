#!/usr/bin/env python3
"""Generate pre-computed demo data from the real artifact rejection pipeline.

Uses the notebook's realistic signal generation, harder artifact injection,
and z-score baseline detector.
"""

import json
import sys
import numpy as np

sys.path.insert(0, "../client")
from artifact_reject import (
    SAMPLE_RATE_HZ, N_CHANNELS, WINDOW_SAMPLES,
    detect_mad, detect_60hz,
)

# --- Constants (matching notebook) ---
DOWNSAMPLE      = 15
N_WINDOWS       = 200   # 200 windows = 20 seconds of playback
INJECT_PROB     = 0.30
MAD_THRESHOLD   = 7.5   # notebook value: catches borderline spikes, occasional FPs
SIGNAL_STD      = 150
ALPHA_AMP       = 25
GAMMA_AMP       = 18
HARMONIC_AMP    = 20
TRANSIENT_AMP   = 450
SPIKE_AMPLITUDE = 900
NOISE_60HZ_AMP  = 150

RNG = np.random.default_rng(42)


# --- Functions (copied from notebook) ---

def pink_noise(n_samples: int, rng) -> np.ndarray:
    """Generate 1/f (pink) noise via frequency-domain shaping."""
    freqs = np.fft.rfftfreq(n_samples)
    freqs[0] = 1e-6
    filt = 1.0 / np.sqrt(freqs)
    filt[0] = 0
    white = rng.normal(0, 1, n_samples)
    shaped = np.fft.irfft(np.fft.rfft(white) * filt, n=n_samples)
    return shaped / shaped.std()


def generate_clean_signal(n_windows, rng):
    """Generate N windows of realistic synthetic neural broadband signal.

    Each window (N_CHANNELS, WINDOW_SAMPLES) contains:
      - 1/f pink noise backbone scaled to SIGNAL_STD
      - Occasional alpha (10 Hz) and gamma (40 Hz) oscillatory bursts
      - 50/70 Hz harmonic noise in ~35% of windows — raises FFT neighbor bins
        near 60 Hz, making line-noise detection harder
      - Sub-threshold transients that on quiet channels can push the MAD
        detector close to (or past) its firing threshold
    """
    t = np.arange(WINDOW_SAMPLES) / SAMPLE_RATE_HZ
    windows = []
    for _ in range(n_windows):
        sig = np.stack([
            pink_noise(WINDOW_SAMPLES, rng) * SIGNAL_STD
            for _ in range(N_CHANNELS)
        ], axis=0).astype(np.float32)

        if rng.random() < 0.6:
            amp = rng.uniform(0.5, 1.0) * ALPHA_AMP
            sig += (amp * np.sin(2 * np.pi * 10 * t + rng.uniform(0, 2*np.pi)))[np.newaxis, :]

        if rng.random() < 0.4:
            amp    = rng.uniform(0.5, 1.0) * GAMMA_AMP
            burst  = amp * np.sin(2 * np.pi * 40 * t + rng.uniform(0, 2*np.pi))
            ch_sel = rng.choice(N_CHANNELS, size=rng.integers(4, 12), replace=False)
            sig[ch_sel] += burst

        if rng.random() < 0.35:
            amp = rng.uniform(0.5, 1.0) * HARMONIC_AMP
            for freq in [50, 70]:
                sig += (amp * np.sin(2 * np.pi * freq * t + rng.uniform(0, 2*np.pi)))[np.newaxis, :]

        n_transients = rng.integers(3, 10)
        for _ in range(n_transients):
            ch    = rng.integers(0, N_CHANNELS)
            idx   = rng.integers(0, WINDOW_SAMPLES)
            amp   = rng.uniform(0.4, 1.0) * TRANSIENT_AMP * rng.choice([-1, 1])
            width = rng.integers(1, 4)
            sig[ch, idx:idx + width] += amp

        windows.append(sig)
    return np.stack(windows, axis=0)


def inject_artifact(window, rng):
    """Inject a synthetic artifact into a window.

    Key differences from client/artifact_reject.py:
    - Spike amplitude: 900 μV (borderline MAD detection)
    - 60 Hz noise: 150 μV with ±3 Hz frequency jitter (spectral leakage)
    """
    corrupted = window.copy()
    artifact_type = rng.choice(['spike', 'flatline', '60hz'])
    t = np.arange(WINDOW_SAMPLES) / SAMPLE_RATE_HZ

    if artifact_type == 'spike':
        ch = rng.integers(0, N_CHANNELS)
        idx = rng.integers(0, WINDOW_SAMPLES)
        corrupted[ch, idx] = SPIKE_AMPLITUDE

    elif artifact_type == 'flatline':
        ch = rng.integers(0, N_CHANNELS)
        corrupted[ch, :] = 0.0

    elif artifact_type == '60hz':
        freq = 60 + rng.uniform(-3, 3)  # ±3 Hz jitter
        noise = NOISE_60HZ_AMP * np.sin(2 * np.pi * freq * t)
        corrupted += noise[np.newaxis, :]

    return corrupted, artifact_type


def detect_zscore(window, threshold=5.0):
    """Baseline detector: per-channel z-score with a fixed threshold.

    Failure modes:
    - Flatlines: std → 0, z-score undefined → silently missed
    - 60 Hz noise: inflates σ across all samples, keeping z-scores below threshold
    - Masking: broad artifacts inflate σ, reducing z-scores of corrupted samples
    """
    flagged = []
    for ch in range(window.shape[0]):
        signal = window[ch]
        std = signal.std()
        if std == 0:
            continue  # flatline → missed
        z = np.abs(signal - signal.mean()) / std
        if np.any(z > threshold):
            flagged.append(ch)
    return len(flagged) > 0, flagged


def generate_dataset(inject: bool) -> list[dict]:
    clean_windows = generate_clean_signal(N_WINDOWS, RNG)
    results = []

    for i in range(N_WINDOWS):
        window = clean_windows[i].copy()

        injected_type = None
        if inject and RNG.random() < INJECT_PROB:
            window, injected_type = inject_artifact(window, RNG)

        # Our detectors
        mad_hit, mad_chs = detect_mad(window, threshold=MAD_THRESHOLD)
        fft_hit, fft_ratio = detect_60hz(window)
        ours_hit = mad_hit or fft_hit

        # Baseline detector (z-score, from notebook)
        baseline_hit, baseline_chs = detect_zscore(window)

        # Downsample channel 0 for display
        signal_ch0 = window[0, ::DOWNSAMPLE].tolist()

        results.append({
            "window_index": i,
            "signal_ch0": [round(v, 2) for v in signal_ch0],
            "injected_type": injected_type,
            "ours_hit": bool(ours_hit),
            "mad_hit": bool(mad_hit),
            "mad_channels": mad_chs,
            "fft_hit": bool(fft_hit),
            "fft_ratio": round(float(fft_ratio), 2),
            "baseline_hit": bool(baseline_hit),
            "baseline_channels": baseline_chs,
        })
    return results


if __name__ == "__main__":
    clean_data = generate_dataset(inject=False)
    artifact_data = generate_dataset(inject=True)

    with open("data_clean.json", "w") as f:
        json.dump(clean_data, f)
    with open("data_artifacts.json", "w") as f:
        json.dump(artifact_data, f)

    # Print stats to verify non-100% results
    injected = [w for w in artifact_data if w["injected_type"] is not None]
    ours_tp = sum(1 for w in injected if w["ours_hit"])
    ours_fp = sum(1 for w in artifact_data if w["ours_hit"] and w["injected_type"] is None)
    base_tp = sum(1 for w in injected if w["baseline_hit"])
    base_fp = sum(1 for w in artifact_data if w["baseline_hit"] and w["injected_type"] is None)

    n_inj = len(injected)
    print(f"Generated {N_WINDOWS} windows each. {n_inj} injected in artifact set.")
    print(f"Ours:     TP={ours_tp} FP={ours_fp} Precision={ours_tp/(ours_tp+ours_fp):.1%} Recall={ours_tp/n_inj:.1%}")
    print(f"Baseline: TP={base_tp} FP={base_fp} Precision={base_tp/(base_tp+base_fp) if (base_tp+base_fp) > 0 else 0:.1%} Recall={base_tp/n_inj:.1%}")
