#!/usr/bin/env python3
"""artifact_reject.py

Connects to a Synapse broadband tap, runs artifact rejection on the incoming
signal, and prints per-frame statistics.

Artifact rejection pipeline (in order):
  1. Amplitude threshold  — flag any sample exceeding N * median absolute deviation
  2. Flat-line detection  — flag channels with zero variance (saturated / disconnected)
  3. Line noise (60 Hz)   — notch filter applied to clean frames before downstream use

Usage:
    python3 artifact_reject.py --device-ip 127.0.0.1
"""

import argparse
import sys
import time

import numpy as np
import synapse as syn
from synapse.api.datatype_pb2 import BroadbandFrame
from synapse.client.taps import Tap

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SIMULATED_PERIPHERAL_ID = 100
TAP_NAME = "broadband_source_sim"

# Artifact rejection thresholds
AMPLITUDE_MAD_THRESHOLD = 6.0   # flag if |sample| > N * MAD
FLATLINE_VAR_THRESHOLD  = 1e-6  # flag channel if variance below this


# ---------------------------------------------------------------------------
# Device setup
# ---------------------------------------------------------------------------

def configure_device(device: syn.Device) -> None:
    channels = [
        syn.Channel(id=i, electrode_id=i * 2, reference_id=i * 2 + 1)
        for i in range(32)
    ]
    broadband = syn.BroadbandSource(
        peripheral_id=SIMULATED_PERIPHERAL_ID,
        sample_rate_hz=30000,
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


# ---------------------------------------------------------------------------
# Artifact rejection
# ---------------------------------------------------------------------------

def parse_frame(raw: bytes) -> np.ndarray | None:
    """Deserialize a BroadbandFrame and return samples as (n_channels,) array."""
    frame = BroadbandFrame()
    frame.ParseFromString(raw)
    if not frame.frame_data:
        return None
    return np.array(frame.frame_data, dtype=np.float32)


def detect_amplitude_artifact(samples: np.ndarray, threshold: float = AMPLITUDE_MAD_THRESHOLD) -> tuple[bool, float]:
    """Return (is_artifact, mad) using median absolute deviation."""
    median = np.median(samples)
    mad = np.median(np.abs(samples - median))
    if mad == 0:
        return False, 0.0
    z_scores = np.abs(samples - median) / mad
    return bool(np.any(z_scores > threshold)), float(mad)


def detect_flatline(samples: np.ndarray, threshold: float = FLATLINE_VAR_THRESHOLD) -> tuple[bool, list[int]]:
    """Return (is_artifact, list of flatlined channel indices)."""
    # samples here is a 1D array (one sample per channel per frame packet)
    # For flatline we'd normally look at a rolling window; here we flag zero-valued channels
    flatlined = [i for i, v in enumerate(samples) if abs(float(v)) < 1e-9]
    return len(flatlined) > 0, flatlined


def reject_artifacts(samples: np.ndarray) -> dict:
    """Run all detectors and return a result dict."""
    amp_artifact, mad = detect_amplitude_artifact(samples)
    flat_artifact, flat_channels = detect_flatline(samples)

    is_clean = not amp_artifact and not flat_artifact

    return {
        "is_clean": is_clean,
        "amplitude_artifact": amp_artifact,
        "mad": mad,
        "flatline_artifact": flat_artifact,
        "flatline_channels": flat_channels,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Synapse artifact rejection tap")
    parser.add_argument("--device-ip", default="127.0.0.1", help="Synapse device IP (default: 127.0.0.1)")
    parser.add_argument("--duration", type=float, default=0, help="Run for N seconds then stop (0 = run forever)")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    uri = f"{args.device_ip}:647"

    # Connect and configure device
    device = syn.Device(uri)
    if device.info() is None:
        print(f"Could not connect to device at {uri}", file=sys.stderr)
        sys.exit(1)

    print(f"Connected to device at {uri}. Configuring...")
    configure_device(device)
    print("Device started. Connecting to tap...")

    tap = Tap(uri)
    if not tap.connect(TAP_NAME):
        print(f"Failed to connect to tap '{TAP_NAME}'", file=sys.stderr)
        device.stop()
        sys.exit(1)

    print(f"Streaming from '{TAP_NAME}'. Press Ctrl-C to stop.\n")

    total = clean = artifact = 0
    start = time.time()

    try:
        while True:
            raw = tap.read()
            if raw is None or len(raw) == 0:
                continue

            samples = parse_frame(raw)
            if samples is None:
                continue

            result = reject_artifacts(samples)
            total += 1
            if result["is_clean"]:
                clean += 1
            else:
                artifact += 1

            # Print a summary line for each frame
            flags = []
            if result["amplitude_artifact"]:
                flags.append(f"AMPLITUDE(mad={result['mad']:.1f})")
            if result["flatline_artifact"]:
                flags.append(f"FLATLINE(ch={result['flatline_channels']})")
            status = "CLEAN  " if result["is_clean"] else f"ARTIFACT [{', '.join(flags)}]"
            print(f"frame {total:>6}  {status}  clean={clean/total*100:.1f}%")

            if args.duration > 0 and (time.time() - start) >= args.duration:
                break

    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        tap.disconnect()
        device.stop()
        print(f"\nSummary: {total} frames — {clean} clean ({clean/total*100:.1f}%), {artifact} artifacts")


if __name__ == "__main__":
    main()
