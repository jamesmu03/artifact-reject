#!/usr/bin/env python3
"""artifact_reject.py

Real-time artifact rejection tap for the Science Corp Synapse stack.

Pipeline:
  1. Rolling buffer  — accumulate 100ms windows of multi-channel broadband data
  2. Artifact inject — optionally corrupt windows with synthetic artifacts
  3. MAD detector    — our approach: adaptive, per-channel, window-based
  4. Threshold det.  — industry baseline: fixed amplitude cutoff

Usage:
    python3 artifact_reject.py [--device-ip 127.0.0.1] [--duration 10] [--inject]
"""

import argparse
import sys
import time
from collections import deque

import numpy as np
import synapse as syn
from synapse.api.datatype_pb2 import BroadbandFrame
from synapse.client.taps import Tap

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
SIMULATED_PERIPHERAL_ID = 100
TAP_NAME                = "broadband_source_sim"
SAMPLE_RATE_HZ          = 30_000
N_CHANNELS              = 32
WINDOW_MS               = 100                                        # detection window length
WINDOW_SAMPLES          = int(SAMPLE_RATE_HZ * WINDOW_MS / 1000)    # 3000 samples

# MAD detector
MAD_THRESHOLD           = 6.0    # flag channel if any sample > N * MAD

# Fixed threshold detector (industry baseline — 12-bit signal, max = 4095)
FIXED_THRESHOLD         = 3500   # flag if any sample exceeds this raw value

# Artifact injection
INJECT_PROB             = 0.30   # probability a window gets an artifact injected
SPIKE_AMPLITUDE         = 4000   # spike value (well above threshold)
NOISE_60HZ_AMPLITUDE    = 800    # 60 Hz sinusoidal noise amplitude


# ---------------------------------------------------------------------------
# Rolling buffer
# ---------------------------------------------------------------------------

class SignalBuffer:
    """Accumulates incoming single-sample frames into fixed-length windows.

    Shape: (n_channels, window_samples)
    Emits a complete window every `window_samples` frames.
    """

    def __init__(self, n_channels: int, window_samples: int):
        self.n_channels     = n_channels
        self.window_samples = window_samples
        self._buf           = deque()
        self._count         = 0

    def push(self, sample: np.ndarray) -> np.ndarray | None:
        """Push one (n_channels,) sample. Returns a window array when full, else None."""
        self._buf.append(sample)
        self._count += 1
        if self._count >= self.window_samples:
            window = np.stack(list(self._buf), axis=1)   # (n_channels, window_samples)
            self._buf.clear()
            self._count = 0
            return window
        return None


# ---------------------------------------------------------------------------
# Artifact injection
# ---------------------------------------------------------------------------

def inject_artifact(window: np.ndarray, rng: np.random.Generator) -> tuple[np.ndarray, str]:
    """Randomly corrupt a window with one of three artifact types.

    Returns (corrupted_window, artifact_type_label).
    """
    corrupted = window.copy()
    artifact_type = rng.choice(["spike", "flatline", "60hz"])

    if artifact_type == "spike":
        ch  = rng.integers(0, corrupted.shape[0])
        idx = rng.integers(0, corrupted.shape[1])
        corrupted[ch, idx] = SPIKE_AMPLITUDE

    elif artifact_type == "flatline":
        ch = rng.integers(0, corrupted.shape[0])
        corrupted[ch, :] = 0.0

    elif artifact_type == "60hz":
        t = np.arange(corrupted.shape[1]) / SAMPLE_RATE_HZ
        noise = NOISE_60HZ_AMPLITUDE * np.sin(2 * np.pi * 60 * t)
        corrupted += noise[np.newaxis, :]

    return corrupted, artifact_type


# ---------------------------------------------------------------------------
# Detectors
# ---------------------------------------------------------------------------

def detect_mad(window: np.ndarray, threshold: float = MAD_THRESHOLD) -> tuple[bool, list[int]]:
    """Our approach: adaptive per-channel MAD over the full window.

    Flags a channel if any sample exceeds median ± threshold * MAD.
    Returns (artifact_detected, flagged_channel_indices).
    """
    flagged = []
    for ch in range(window.shape[0]):
        signal = window[ch]
        median = np.median(signal)
        mad    = np.median(np.abs(signal - median))
        if mad == 0:
            # flat channel — check for true flatline separately
            if np.all(signal == signal[0]):
                flagged.append(ch)
            continue
        z = np.abs(signal - median) / mad
        if np.any(z > threshold):
            flagged.append(ch)
    return len(flagged) > 0, flagged


def detect_fixed_threshold(window: np.ndarray, threshold: float = FIXED_THRESHOLD) -> tuple[bool, list[int]]:
    """Industry baseline: fixed amplitude cutoff.

    Flags a channel if any sample exceeds the threshold.
    Returns (artifact_detected, flagged_channel_indices).
    """
    flagged = [ch for ch in range(window.shape[0]) if np.any(np.abs(window[ch]) > threshold)]
    return len(flagged) > 0, flagged


# ---------------------------------------------------------------------------
# Device setup
# ---------------------------------------------------------------------------

def configure_device(device: syn.Device) -> None:
    channels = [
        syn.Channel(id=i, electrode_id=i * 2, reference_id=i * 2 + 1)
        for i in range(N_CHANNELS)
    ]
    broadband = syn.BroadbandSource(
        peripheral_id=SIMULATED_PERIPHERAL_ID,
        sample_rate_hz=SAMPLE_RATE_HZ,
        bit_width=12,
        gain=20.0,
        signal=syn.SignalConfig(
            electrode=syn.ElectrodeConfig(
                channels=channels,
                low_cutoff_hz=500.0,
                high_cutoff_hz=6000.0,
            )
        ),
    )
    config = syn.Config()
    config.add_node(broadband)
    device.configure(config)
    device.start()


def parse_frame(raw: bytes) -> np.ndarray | None:
    """Deserialize a BroadbandFrame → (n_channels,) sample array."""
    frame = BroadbandFrame()
    frame.ParseFromString(raw)
    if not frame.frame_data:
        return None
    return np.array(frame.frame_data, dtype=np.float32)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Synapse artifact rejection tap")
    parser.add_argument("--device-ip", default="127.0.0.1")
    parser.add_argument("--duration",  type=float, default=10,
                        help="Run for N seconds (default: 10)")
    parser.add_argument("--inject",    action="store_true",
                        help="Randomly inject synthetic artifacts into windows")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    uri  = f"{args.device_ip}:647"
    rng  = np.random.default_rng()

    device = syn.Device(uri)
    if device.info() is None:
        print(f"Could not connect to device at {uri}", file=sys.stderr)
        sys.exit(1)

    print(f"Connected to {uri}. Configuring...")
    configure_device(device)

    tap = Tap(uri)
    if not tap.connect(TAP_NAME):
        print(f"Failed to connect to tap '{TAP_NAME}'", file=sys.stderr)
        device.stop()
        sys.exit(1)

    print(f"Streaming '{TAP_NAME}' | window={WINDOW_MS}ms | inject={args.inject}\n")
    print(f"{'Win':>5}  {'Injected':<10}  {'MAD':^14}  {'Threshold':^14}  {'Agreement'}")
    print("-" * 65)

    buf = SignalBuffer(N_CHANNELS, WINDOW_SAMPLES)

    # Comparison counters
    total = mad_tp = mad_fp = thresh_tp = thresh_fp = 0
    start = time.time()

    try:
        while True:
            raw = tap.read()
            if not raw:
                continue

            sample = parse_frame(raw)
            if sample is None:
                continue

            window = buf.push(sample)
            if window is None:
                continue

            # Artifact injection
            injected_type = None
            if args.inject and rng.random() < INJECT_PROB:
                window, injected_type = inject_artifact(window, rng)

            # Run both detectors
            mad_hit,   mad_chs   = detect_mad(window)
            fixed_hit, fixed_chs = detect_fixed_threshold(window)

            total += 1
            ground_truth = injected_type is not None

            if ground_truth:
                if mad_hit:   mad_tp   += 1
                if fixed_hit: thresh_tp += 1
            else:
                if mad_hit:   mad_fp   += 1
                if fixed_hit: thresh_fp += 1

            injected_label = injected_type or "—"
            mad_label      = f"{'HIT' if mad_hit else 'miss'} (ch={mad_chs})" if mad_hit else "miss"
            fixed_label    = f"{'HIT' if fixed_hit else 'miss'} (ch={fixed_chs})" if fixed_hit else "miss"
            agree          = "✓" if mad_hit == fixed_hit else "✗ differ"

            print(f"{total:>5}  {injected_label:<10}  {mad_label:<14}  {fixed_label:<14}  {agree}")

            if (time.time() - start) >= args.duration:
                break

    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        tap.disconnect()
        device.stop()

    # Summary
    print("\n" + "=" * 65)
    print(f"Windows evaluated: {total}  |  Injection rate: {INJECT_PROB*100:.0f}%")
    print(f"\n{'Detector':<20} {'True Pos':>10} {'False Pos':>10}")
    print(f"{'MAD (ours)':<20} {mad_tp:>10} {mad_fp:>10}")
    print(f"{'Fixed threshold':<20} {thresh_tp:>10} {thresh_fp:>10}")


if __name__ == "__main__":
    main()
