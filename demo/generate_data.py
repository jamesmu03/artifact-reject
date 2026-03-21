#!/usr/bin/env python3
"""Generate pre-computed demo data from the real artifact rejection pipeline.

Imports the actual detectors from client/artifact_reject.py, runs them on
synthetic broadband data, and outputs JSON files for the demo UI.
"""

import json
import sys
import numpy as np

sys.path.insert(0, "../client")
from artifact_reject import (
    SAMPLE_RATE_HZ, N_CHANNELS, WINDOW_SAMPLES, INJECT_PROB,
    MAD_THRESHOLD, FIXED_THRESHOLD, SPECTRAL_60HZ_RATIO,
    inject_artifact, detect_mad, detect_60hz, detect_fixed_threshold,
)

DOWNSAMPLE = 15
N_WINDOWS = 200
RNG = np.random.default_rng(42)  # Fixed seed for reproducibility


DEMO_MAD_THRESHOLD = 8.0  # Higher than pipeline default (6.0) to avoid Gaussian-tail FPs on synthetic data


def generate_dataset(inject: bool) -> list[dict]:
    results = []
    for i in range(N_WINDOWS):
        # Generate synthetic broadband window — clip to ±4σ to avoid extreme tails
        window = RNG.normal(0, 150, size=(N_CHANNELS, WINDOW_SAMPLES)).astype(np.float32)
        window = np.clip(window, -600, 600)

        injected_type = None
        if inject and RNG.random() < INJECT_PROB:
            window, injected_type = inject_artifact(window, RNG)

        # Run detectors (use higher MAD threshold for synthetic data)
        mad_hit, mad_chs = detect_mad(window, threshold=DEMO_MAD_THRESHOLD)
        fft_hit, fft_ratio = detect_60hz(window)
        fixed_hit, fixed_chs = detect_fixed_threshold(window)

        # Downsample channel 0 for display
        signal_ch0 = window[0, ::DOWNSAMPLE].tolist()

        results.append({
            "window_index": i,
            "signal_ch0": [round(v, 2) for v in signal_ch0],
            "injected_type": injected_type,
            "ours_hit": bool(mad_hit or fft_hit),
            "mad_hit": bool(mad_hit),
            "mad_channels": mad_chs,
            "fft_hit": bool(fft_hit),
            "fft_ratio": round(float(fft_ratio), 2),
            "fixed_hit": bool(fixed_hit),
            "fixed_channels": fixed_chs,
        })
    return results


if __name__ == "__main__":
    # Generate both datasets
    clean_data = generate_dataset(inject=False)
    artifact_data = generate_dataset(inject=True)

    with open("data_clean.json", "w") as f:
        json.dump(clean_data, f)

    with open("data_artifacts.json", "w") as f:
        json.dump(artifact_data, f)

    print(f"Generated {N_WINDOWS} windows each for clean and artifact datasets.")

    # Quick stats
    clean_hits = sum(1 for w in clean_data if w["ours_hit"])
    artifact_hits = sum(1 for w in artifact_data if w["ours_hit"])
    injected = sum(1 for w in artifact_data if w["injected_type"] is not None)
    print(f"Clean dataset: {clean_hits} detections out of {N_WINDOWS} windows")
    print(f"Artifact dataset: {artifact_hits} detections out of {N_WINDOWS} windows ({injected} injected)")
