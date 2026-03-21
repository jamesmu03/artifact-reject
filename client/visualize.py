#!/usr/bin/env python3
"""visualize.py

Real-time visualization of the artifact rejection pipeline.

Three-panel live plot:
  1. Raw signal — shows injected artifacts as red-shaded windows
  2. Ours (MAD+FFT) — artifact windows suppressed, clean signal preserved
  3. Fixed threshold — industry baseline, showing over-suppression on clean windows

Usage:
    python3 visualize.py [--device-ip 127.0.0.1] [--inject]
"""

import argparse
import queue
import sys
import threading

import matplotlib.pyplot as plt
import matplotlib.animation
import matplotlib.gridspec as gridspec
import numpy as np
# Import pipeline from sibling module
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from artifact_reject import (
    N_CHANNELS, WINDOW_SAMPLES, SAMPLE_RATE_HZ, INJECT_PROB,
    SignalBuffer, configure_device, parse_frame,
    inject_artifact, detect_mad, detect_60hz, detect_fixed_threshold,
)

# ---------------------------------------------------------------------------
# Viz config
# ---------------------------------------------------------------------------
DISPLAY_CH      = 0      # channel to plot
DISPLAY_WINDOWS = 40     # number of windows visible at once (~4 seconds)
DOWNSAMPLE      = 15     # plot every Nth sample (for performance)
REFRESH_MS      = 200    # matplotlib animation interval
DC_OFFSET       = 2048.0 # simulator 12-bit ADC midpoint; subtract to center signal

DISPLAY_SAMPLES = DISPLAY_WINDOWS * WINDOW_SAMPLES // DOWNSAMPLE

TAP_NAME = "broadband_source_sim"

# ---------------------------------------------------------------------------
# Shared state between tap thread and UI thread
# ---------------------------------------------------------------------------
data_q: queue.Queue = queue.Queue(maxsize=30)

# Rolling display buffers (one entry per downsampled sample)
raw_buf      = np.zeros(DISPLAY_SAMPLES)
ours_buf     = np.zeros(DISPLAY_SAMPLES)
fixed_buf    = np.zeros(DISPLAY_SAMPLES)
gt_buf       = np.zeros(DISPLAY_SAMPLES)   # 1 = ground-truth artifact window
ours_hit_buf = np.zeros(DISPLAY_SAMPLES)   # 1 = our detector fired
fix_hit_buf  = np.zeros(DISPLAY_SAMPLES)   # 1 = fixed threshold fired

# Stats
stats = {"ours_tp": 0, "ours_fp": 0, "ours_fn": 0, "fix_tp": 0, "fix_fp": 0, "fix_fn": 0, "total": 0}


# ---------------------------------------------------------------------------
# Tap worker (background thread)
# ---------------------------------------------------------------------------

def tap_worker(uri: str, inject: bool) -> None:
    import synapse as syn
    from synapse.client.taps import Tap

    rng    = np.random.default_rng()
    device = syn.Device(uri)
    configure_device(device)

    tap = Tap(uri)
    if not tap.connect(TAP_NAME):
        print(f"Failed to connect to tap '{TAP_NAME}'", file=sys.stderr)
        return

    buf = SignalBuffer(N_CHANNELS, WINDOW_SAMPLES)

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

            injected_type = None
            if inject and rng.random() < INJECT_PROB:
                window, injected_type = inject_artifact(window, rng)

            mad_hit,  _          = detect_mad(window)
            hz60_hit, _          = detect_60hz(window)
            ours_hit             = mad_hit or hz60_hit
            fixed_hit, _         = detect_fixed_threshold(window)
            ground_truth         = injected_type is not None

            data_q.put({
                "signal":       window[DISPLAY_CH],
                "injected":     injected_type,
                "ours_hit":     ours_hit,
                "fixed_hit":    fixed_hit,
                "ground_truth": ground_truth,
            })

    finally:
        tap.disconnect()
        device.stop()


# ---------------------------------------------------------------------------
# Plot update
# ---------------------------------------------------------------------------

def update_stats(ground_truth: bool, ours_hit: bool, fixed_hit: bool) -> None:
    stats["total"] += 1
    if ground_truth:
        if ours_hit:  stats["ours_tp"] += 1
        else:         stats["ours_fn"] += 1
        if fixed_hit: stats["fix_tp"]  += 1
        else:         stats["fix_fn"]  += 1
    else:
        if ours_hit:  stats["ours_fp"] += 1
        if fixed_hit: stats["fix_fp"]  += 1


def precision(tp: int, fp: int) -> str:
    return f"{tp/(tp+fp)*100:.0f}%" if (tp + fp) > 0 else "—"

def recall(tp: int, fn: int) -> str:
    return f"{tp/(tp+fn)*100:.0f}%" if (tp + fn) > 0 else "—"


def make_update(lines, spans, axes):
    raw_line, ours_line, fixed_line = lines
    raw_ax, ours_ax, fixed_ax = axes

    def update(_frame):
        global raw_buf, ours_buf, fixed_buf, gt_buf, ours_hit_buf, fix_hit_buf

        # Drain the queue
        changed = False
        while not data_q.empty():
            try:
                item = data_q.get_nowait()
            except queue.Empty:
                break

            signal      = item["signal"]
            ours_hit    = item["ours_hit"]
            fixed_hit   = item["fixed_hit"]
            ground_truth = item["ground_truth"]

            update_stats(ground_truth, ours_hit, fixed_hit)

            # Downsample and remove DC offset so signal is centered at zero
            ds = signal[::DOWNSAMPLE] - DC_OFFSET
            n  = len(ds)

            # Shift buffers left
            raw_buf      = np.roll(raw_buf,      -n)
            ours_buf     = np.roll(ours_buf,     -n)
            fixed_buf    = np.roll(fixed_buf,    -n)
            gt_buf       = np.roll(gt_buf,       -n)
            ours_hit_buf = np.roll(ours_hit_buf, -n)
            fix_hit_buf  = np.roll(fix_hit_buf,  -n)

            raw_buf[-n:]      = ds
            gt_buf[-n:]       = 1.0 if ground_truth else 0.0
            ours_hit_buf[-n:] = 1.0 if ours_hit else 0.0
            fix_hit_buf[-n:]  = 1.0 if fixed_hit else 0.0

            # Our cleaned output: zero artifact windows
            ours_buf[-n:] = 0.0 if ours_hit else ds

            # Fixed threshold cleaned output: zero when it fires
            fixed_buf[-n:] = 0.0 if fixed_hit else ds

            changed = True

        if not changed:
            return lines

        x = np.arange(DISPLAY_SAMPLES)

        # Update waveforms
        raw_line.set_data(x, raw_buf)
        ours_line.set_data(x, ours_buf)
        fixed_line.set_data(x, fixed_buf)

        # Redraw background shading — remove old spans
        for ax, span_list in zip(axes, spans):
            for sp in span_list:
                sp.remove()
            span_list.clear()

        # Find artifact windows and shade them
        win_ds = WINDOW_SAMPLES // DOWNSAMPLE
        for w in range(DISPLAY_WINDOWS):
            start = w * win_ds
            end   = start + win_ds

            if np.any(gt_buf[start:end] > 0):
                spans[0].append(raw_ax.axvspan(start, end, color="#e74c3c", alpha=0.25))
            if np.any(ours_hit_buf[start:end] > 0):
                spans[1].append(ours_ax.axvspan(start, end, color="#e74c3c", alpha=0.15))
            if np.any(fix_hit_buf[start:end] > 0):
                spans[2].append(fixed_ax.axvspan(start, end, color="#e74c3c", alpha=0.25))

        # Update titles with live stats
        tp, fp, fn = stats["ours_tp"], stats["ours_fp"], stats["ours_fn"]
        raw_ax.set_title(
            f"Raw Signal (channel {DISPLAY_CH})  —  "
            f"{'Injection ON' if args.inject else 'No injection'}",
            color="white", fontsize=11
        )
        ours_ax.set_title(
            f"Ours (MAD + FFT)  |  "
            f"TP={tp}  FP={fp}  FN={fn}  Precision={precision(tp, fp)}  Recall={recall(tp, fn)}",
            color="#2ecc71", fontsize=11
        )
        ftp, ffp, ffn = stats["fix_tp"], stats["fix_fp"], stats["fix_fn"]
        fixed_ax.set_title(
            f"Fixed Threshold  |  "
            f"TP={ftp}  FP={ffp}  FN={ffn}  Precision={precision(ftp, ffp)}  Recall={recall(ftp, ffn)}",
            color="#e74c3c", fontsize=11
        )

        return lines

    return update


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(description="Artifact rejection live visualization")
    parser.add_argument("--device-ip", default="127.0.0.1")
    parser.add_argument("--inject", action="store_true",
                        help="Inject synthetic artifacts into the signal")
    return parser.parse_args()


args = parse_args()


def main():
    import synapse as syn

    uri = f"{args.device_ip}:647"

    # Verify device is reachable
    device_check = syn.Device(uri)
    if device_check.info() is None:
        print(f"Could not connect to device at {uri}", file=sys.stderr)
        sys.exit(1)

    # Start tap thread
    t = threading.Thread(target=tap_worker, args=(uri, args.inject), daemon=True)
    t.start()

    # Build figure
    plt.style.use("dark_background")
    fig = plt.figure(figsize=(14, 8))
    fig.patch.set_facecolor("#0d1117")
    fig.suptitle("Artifact-Reject  |  Real-time Neural Signal Cleaning",
                 color="white", fontsize=13, fontweight="bold", y=0.98)

    gs = gridspec.GridSpec(3, 1, hspace=0.55)
    raw_ax   = fig.add_subplot(gs[0])
    ours_ax  = fig.add_subplot(gs[1])
    fixed_ax = fig.add_subplot(gs[2])

    axes = [raw_ax, ours_ax, fixed_ax]
    colors = ["#ecf0f1", "#2ecc71", "#e67e22"]
    labels = ["Raw", "Ours (MAD+FFT)", "Fixed Threshold"]

    # X-axis: each display sample = DOWNSAMPLE / SAMPLE_RATE_HZ seconds
    ms_per_sample = DOWNSAMPLE / SAMPLE_RATE_HZ * 1000        # 0.5 ms per display sample
    tick_interval_s = 1.0
    tick_positions = np.arange(0, DISPLAY_SAMPLES + 1, int(tick_interval_s * 1000 / ms_per_sample))
    tick_labels = [f"{int((DISPLAY_SAMPLES - p) * ms_per_sample / 1000)}s" for p in tick_positions]
    tick_labels[-1] = "now"

    lines = []
    for i, (ax, color, label) in enumerate(zip(axes, colors, labels)):
        ax.set_facecolor("#161b22")
        ax.tick_params(colors="#555")
        for spine in ax.spines.values():
            spine.set_edgecolor("#30363d")
        ax.set_xlim(0, DISPLAY_SAMPLES)
        ax.set_ylim(-2500, 2500)
        ax.set_ylabel("μV", fontsize=9, color="#777")
        if i < 2:
            ax.set_xticks([])
        else:
            ax.set_xticks(tick_positions)
            ax.set_xticklabels(tick_labels, fontsize=8, color="#777")
        line, = ax.plot([], [], color=color, linewidth=0.8, label=label)
        lines.append(line)

    # Span storage (mutable lists so update() can clear and refill)
    spans = [[], [], []]

    update_fn = make_update(lines, spans, axes)

    ani = matplotlib.animation.FuncAnimation(
        fig, update_fn, interval=REFRESH_MS, blit=False, cache_frame_data=False
    )

    plt.show()


if __name__ == "__main__":
    main()
