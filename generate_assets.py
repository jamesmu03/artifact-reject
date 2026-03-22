#!/usr/bin/env python3
"""Generate presentation assets (PNG plots) from pre-generated demo data."""

import json, sys, os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'client'))
from artifact_reject import SAMPLE_RATE_HZ, WINDOW_SAMPLES

DATA_DIR = os.path.join(os.path.dirname(__file__), 'demo')
OUT_DIR  = os.path.join(os.path.dirname(__file__), 'assets')
os.makedirs(OUT_DIR, exist_ok=True)

art_data = json.load(open(os.path.join(DATA_DIR, 'data_artifacts.json')))

N = 40  # windows to show
BG  = '#0d1117'
AX  = '#161b22'
RED = '#e74c3c'

# Derive samples-per-window from actual data (demo data is downsampled for display)
SAMPLES_PER_WIN = len(art_data[0]['signal_ch0'])
WIN_DURATION_MS = 100  # each window is 100 ms

# ── helpers ──────────────────────────────────────────────────────────────────

def shade_artifacts(ax, windows, start=0):
    for i, w in enumerate(windows[start:start+N], start):
        if w['injected_type']:
            x0 = (i - start) * WIN_DURATION_MS
            x1 = x0 + WIN_DURATION_MS
            ax.axvspan(x0, x1, color=RED, alpha=0.30)

def make_signal(windows, key, start=0):
    return np.concatenate([w[key] for w in windows[start:start+N]])

def time_axis(n_windows):
    return np.linspace(0, n_windows * WIN_DURATION_MS, n_windows * SAMPLES_PER_WIN, endpoint=False)

# ── Figure 1: results — ours vs baseline comparison ─────────────────────────

def fig_results():
    # Two panels only: ours vs baseline (raw implied by context)
    fig, axes = plt.subplots(2, 1, figsize=(8, 2.8), sharex=True)
    fig.patch.set_facecolor(BG)

    ours = np.concatenate([
        np.zeros(SAMPLES_PER_WIN) if w['ours_hit'] else w['signal_ch0']
        for w in art_data[:N]
    ])
    base = np.concatenate([
        np.zeros(SAMPLES_PER_WIN) if w['baseline_hit'] else w['signal_ch0']
        for w in art_data[:N]
    ])
    t = time_axis(N)

    panels = [
        (ours, '#2ecc71', 'artifact-reject (MAD + FFT)  —  63% caught'),
        (base, '#e8956d', 'Z-score baseline (5σ)  —  13% caught'),
    ]

    for ax, (sig, color, title) in zip(axes, panels):
        ax.set_facecolor(AX)
        ax.plot(t, sig, color=color, linewidth=0.8, rasterized=True)
        shade_artifacts(ax, art_data)
        ax.set_title(title, color=color, fontsize=9, pad=3, loc='left')
        ax.set_xlim(t[0], t[-1])
        ax.set_ylabel('μV', color='#8b949e', fontsize=8)
        ax.tick_params(colors='#8b949e', labelsize=7)
        for spine in ax.spines.values():
            spine.set_edgecolor('#30363d')

    axes[-1].set_xlabel('Time (ms)', color='#8b949e', fontsize=9)

    fig.tight_layout(h_pad=0.4, pad=0.5)
    path = os.path.join(OUT_DIR, 'results.png')
    fig.savefig(path, dpi=120, bbox_inches='tight', facecolor=BG)
    plt.close(fig)
    print(f'Saved {path}')

# ── Figure 3: approach — pipeline diagram ────────────────────────────────────

def fig_approach():
    fig, ax = plt.subplots(figsize=(8, 2.4))
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)
    ax.set_xlim(0, 10); ax.set_ylim(0, 4); ax.axis('off')

    BLUE = '#4a6cf7'; GREEN = '#2ecc71'; GRAY = '#8b949e'
    BOX  = dict(boxstyle='round,pad=0.5', facecolor='#21262d', edgecolor=BLUE, linewidth=1.5)
    ARR  = dict(arrowstyle='->', color=GRAY, lw=1.5)

    boxes = [
        (1.0, 2.0, 'Raw neural\nsignal'),
        (3.8, 2.9, 'MAD\ndetector'),
        (3.8, 1.1, 'FFT 60 Hz\ndetector'),
        (6.8, 2.0, 'OR gate'),
        (8.9, 2.0, 'Blanked\noutput'),
    ]
    for x, y, label in boxes:
        color = GREEN if 'Blanked' in label else BLUE
        ax.text(x, y, label, ha='center', va='center', fontsize=11,
                color='#ecf0f1', bbox=dict(boxstyle='round,pad=0.5',
                facecolor='#21262d', edgecolor=color, linewidth=1.5))

    # arrows
    arrows = [
        (1.55, 2.0, 3.15, 2.9),   # raw → MAD
        (1.55, 2.0, 3.15, 1.1),   # raw → FFT
        (4.55, 2.9, 6.25, 2.1),   # MAD → OR
        (4.55, 1.1, 6.25, 1.9),   # FFT → OR
        (7.4,  2.0, 8.25, 2.0),   # OR → output
    ]
    for x0, y0, x1, y1 in arrows:
        ax.annotate('', xy=(x1, y1), xytext=(x0, y0),
                    arrowprops=dict(arrowstyle='->', color=GRAY, lw=1.5))

    ax.text(5.0, 0.35, '100 ms windows · real-time · no recalibration',
            ha='center', va='center', fontsize=10, color=GRAY, style='italic')

    fig.tight_layout()
    path = os.path.join(OUT_DIR, 'approach.png')
    fig.savefig(path, dpi=120, bbox_inches='tight', facecolor=BG)
    plt.close(fig)
    print(f'Saved {path}')


if __name__ == '__main__':
    fig_results()
    fig_approach()
    print('Done.')
