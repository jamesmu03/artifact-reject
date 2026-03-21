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

## Usage

```bash
# Install dependencies (use a dedicated env)
pip install -r client/requirements.txt

# Start the Synapse simulator
synapse-sim --iface-ip 127.0.0.1

# Run the artifact rejection tap
python3 client/artifact_reject.py --device-ip 127.0.0.1
```

## Status

Working Python tap with amplitude and flatline artifact detection against the Synapse simulator.

---

*This README was one-shotted by Claude at the start of the hackathon.*
