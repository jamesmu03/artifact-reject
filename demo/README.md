# Artifact Rejection Demo

Interactive browser-based dashboard that replays pre-computed data from the real artifact rejection pipeline. No backend required — double-click and go (with a local server for JSON loading).

![Neural Signal Monitor Dashboard](https://img.shields.io/badge/status-working-brightgreen)

## What This Does

The demo visualises a real-time neural signal monitoring scenario:

- **Raw broadband signal** scrolls across the screen (channel 0, downsampled)
- **Artifact detection** highlights corrupted windows with red shading
- **Cleaned output** shows the same signal with detected artifacts blanked
- **Precision / Recall / Artifact count / Clean signal %** update live
- **BCI cursor speller** shows side-by-side comparison:
  - *Without rejection*: cursor jerks off-target during artifacts → wrong letters
  - *With rejection*: cursor stays on-target → correct spelling
- **Event log** shows each rejection event as it happens

Toggle artifact injection on/off to see the difference in real time.

## How It Works

```
generate_data.py                     index.html
┌─────────────────────┐              ┌────────────────────────┐
│ Imports real funcs   │   JSON      │ Loads JSON              │
│ from artifact_reject │─────────────│ 100ms tick loop         │
│ .py (MAD, FFT, etc) │  data_*.json│ Canvas rendering        │
│                      │             │ Stats + speller + log   │
│ Runs on synthetic    │             │ No detection logic —    │
│ data, dumps results  │             │ pure replay             │
└─────────────────────┘              └────────────────────────┘
```

**No code duplication.** `generate_data.py` imports `detect_mad`, `detect_60hz`, `detect_fixed_threshold`, and `inject_artifact` directly from `client/artifact_reject.py`. The HTML replays pre-computed results — zero detection logic in JavaScript.

## Quick Start

### 1. Generate data (one time)

```bash
cd demo/
python3 generate_data.py
```

This produces `data_clean.json` and `data_artifacts.json` (200 windows each). These are committed to the repo, so you can skip this step if they already exist.

**Requirements:** `numpy` (that's it — the detector functions are pure numpy, no synapse dependency).

### 2. Run the demo

```bash
cd demo/
python3 -m http.server 8000
```

Open [http://localhost:8000/index.html](http://localhost:8000/index.html) in your browser.

> **Why a local server?** `fetch()` doesn't work with `file://` protocol due to CORS restrictions. The one-liner Python server handles this.

### 3. Controls

| Action | How |
|--------|-----|
| Toggle artifact injection | Click the toggle switch in the sidebar, or press **`i`** |
| Watch the speller | Both grids spell the same words — the left (no rejection) makes errors, the right (with rejection) stays accurate |

## File Structure

```
demo/
├── README.md              ← You are here
├── generate_data.py       ← Imports real detectors, outputs JSON
├── data_clean.json        ← 200 windows, no injection (pre-generated)
├── data_artifacts.json    ← 200 windows, 30% injection (pre-generated)
└── index.html             ← The dashboard (loads JSON, renders everything)
```

## UI Components

| Component | Description |
|-----------|-------------|
| **Status bar** | Green pulsing dot, channel/sample-rate info, elapsed timer |
| **Artifact gallery** | Three static cards explaining spike, 60 Hz, and flatline artifacts |
| **Raw signal** | White trace on dark background, red shading on artifact windows |
| **Cleaned signal** | Green trace, artifact windows blanked to zero |
| **Stats sidebar** | Precision, Recall, Artifact count, Clean signal % (2×2 grid) |
| **Inject toggle** | Switches between clean and artifact datasets, resets stats |
| **Cursor speller** | Side-by-side BCI cursor grids spelling HELP, WATER, YES, PAIN |
| **Event log** | Scrolling bar showing recent rejection events |

## Data Format

Each JSON file is an array of window objects:

```json
{
  "window_index": 0,
  "signal_ch0": [0.12, -0.34, ...],
  "injected_type": null | "spike" | "flatline" | "60hz",
  "ours_hit": false,
  "mad_hit": false,
  "mad_channels": [],
  "fft_hit": false,
  "fft_ratio": 1.2,
  "fixed_hit": false,
  "fixed_channels": []
}
```

## Customisation

- **Longer playback:** Change `N_WINDOWS` in `generate_data.py` (e.g., 600 for 60 seconds)
- **Different injection rate:** Modify `INJECT_PROB` in `client/artifact_reject.py`
- **Target words:** Edit `TARGET_WORDS` array in `index.html`
- **Tick speed:** Change the `setInterval(tick, 100)` value (100ms = real-time matching the 100ms window)
