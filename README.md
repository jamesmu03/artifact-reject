# artifact-reject

HackDuke hackathon project by **James Mu** (Duke) and **Derek Mu** (CMU).

## Background: How Neurotech Works

Neurotech systems record electrical activity from the brain and nervous system to enable applications like brain-computer interfaces (BCIs), neural prosthetics, and neurofeedback.

At a high level, the stack looks like this:

1. **Sensors** — electrodes placed on or in the brain (EEG, ECoG, Utah array, etc.) pick up tiny electrical signals, on the order of microvolts.
2. **Amplification & ADC** — a hardware front-end amplifies the signal and digitizes it at high sample rates (often 1–30 kHz).
3. **Signal processing** — the raw digital signal is filtered, decomposed, and analyzed to extract meaningful features (spike sorting, band power, event-related potentials, etc.).
4. **Decoding** — machine learning models map neural features to intended actions, states, or outputs.
5. **Feedback / actuation** — the decoded output drives some downstream effect: a cursor, a prosthetic limb, a stimulation pulse, a UI event.

### The artifact problem

Neural signals are extremely weak and easily corrupted. Common artifact sources include:

- **Motion artifacts** — cable movement, electrode shift, or subject movement coupling mechanical noise into the signal
- **EMG contamination** — muscle activity (jaw clench, eye blink) overlaps spectrally with neural bands
- **Line noise** — 60 Hz (or 50 Hz) electrical interference from power lines and equipment
- **Amplifier saturation** — large transients that rail the ADC and corrupt surrounding samples
- **Stimulation artifacts** — if the system delivers electrical stimulation, the pulse bleeds into the recording

Downstream decoders trained on clean data fail badly when artifacts go undetected. Artifact rejection is therefore a critical step before any meaningful analysis can happen.

### The hardware-first gap

The biggest names in neurotech have poured enormous resources into the electrode and hardware layer — but the signal chain software has lagged behind:

- **Neuralink** is pushing the frontier on implant miniaturization and electrode count, but their public focus is almost entirely on the device itself
- **Synchron** has made huge strides getting a stent-based BCI through clinical trials, yet artifact handling in naturalistic, ambulatory conditions remains an open problem
- **Blackrock Neurotech** supplies the gold-standard Utah array used in most academic BCIs, but artifact rejection is largely left to individual research groups to figure out
- **Neuropace** and other closed-loop neuromodulation companies deal with stimulation artifacts constantly — and still rely on relatively crude blanking strategies

The pattern is consistent: companies race to improve hardware SNR, but the software that cleans and validates the signal is underdeveloped, fragmented, and rarely productized. A robust, reusable artifact rejection layer would benefit the entire ecosystem.

## Idea

Build a real-time artifact rejection module that sits in the signal processing pipeline, automatically detects and suppresses artifacts, and passes clean neural data downstream.

## Approach

Building this as a **tap** for the [Science Corp Synapse](https://science.xyz) tech stack. A tap intercepts the live data stream in the Synapse pipeline, applies artifact detection and rejection logic, and forwards the cleaned signal to downstream consumers — with no changes required to the rest of the stack.

### Detection pipeline

We run two detectors in parallel on each 100ms window of broadband data:

1. **MAD (Median Absolute Deviation)** — adaptive, per-channel amplitude detector. Flags a channel if any sample exceeds `threshold × MAD` from the channel median. Catches saturating spikes and flatlined (disconnected) electrodes. Unlike a fixed threshold, MAD scales automatically with the signal's own noise floor — no recalibration needed across different rigs or subjects.

2. **FFT 60 Hz detector** — spectral detector for line noise. Computes the mean FFT magnitude across all channels and flags the window if the 60 Hz bin power exceeds 5× the average power of neighboring bins. Catches sinusoidal interference that amplitude detectors miss entirely.

### Baseline comparison

We compare against the standard approach: a **per-channel z-score baseline** (5σ threshold). If any sample exceeds 5 standard deviations from the channel mean, reject the window. Simple, fast, widely used — but brittle. It requires the signal to have stable variance, completely misses flatlines (std → 0), and cannot detect 60 Hz noise at all.

## Results

On synthetic Gaussian neural signal (32 channels, 30 kHz, std=150 μV) with 18% of windows corrupted:

| Detector | Precision | Recall | Clean signal preserved |
|---|---|---|---|
| **Ours (MAD + FFT)** | **83%** | **63%** | **85%** |
| Z-score baseline (5σ) | 50% | 13% | 95% |

Our method catches 5× more artifacts while preserving 85% of clean signal. Built as a tap for **Science Corp's Synapse** — the emerging industry standard for neural data pipelines — so it works out of the box for any lab or device running on Synapse, with no changes to the recording setup.

## Usage

### Live tap (requires Synapse simulator)

```bash
# Install dependencies
pip install -r client/requirements.txt

# Start the Synapse simulator
synapse-sim --iface-ip 127.0.0.1

# Run the artifact rejection tap (terminal output)
python3 client/artifact_reject.py --device-ip 127.0.0.1

# Or use the one-command launcher
./run.sh            # live visualization, no artifacts
./run.sh --inject   # live visualization with injected artifacts
./run.sh --cli      # terminal output only (no plot window)
```

### Demo notebook (no simulator needed)

The notebook runs entirely locally on synthetic data — no Synapse device or simulator required.

```bash
# Install dependencies (Jupyter + numpy + matplotlib)
pip install jupyter numpy matplotlib

# Open the notebook
jupyter notebook notebook/demo.ipynb
```

> **Note:** The notebook imports detector functions from `client/artifact_reject.py`, which in turn imports the `synapse` Python package. Install it with:
> ```bash
> pip install science-synapse
> ```
> Or follow the [synapse-python setup instructions](https://github.com/sciencecorp/synapse-python) to install from source.

## Contributors

**James Mu** (Duke University) — Signal processing pipeline, artifact detection algorithms (MAD + FFT), Synapse tap integration, synthetic data generation, baseline comparison, Jupyter notebook analysis.

**Derek Mu** (Carnegie Mellon University) — Browser-based demo UI, finger-tracking keyboard visualization, data pipeline for demo replay.
