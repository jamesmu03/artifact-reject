---
marp: true
theme: default
paginate: true
style: |
  section {
    font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
    background: #ffffff;
    color: #1a1a2e;
    font-size: 24px;
    padding: 40px 60px;
  }
  h1 {
    color: #1a1a2e;
    font-size: 1.9em;
    border-bottom: 2px solid #4a6cf7;
    padding-bottom: 0.2em;
    margin-bottom: 0.5em;
  }
  strong { color: #1a6ef5; }
  em { color: #e05c2a; }
  ul { padding-left: 1.3em; }
  ul li { margin: 0.45em 0; }
  blockquote {
    background: #f0f3ff;
    border-left: 4px solid #4a6cf7;
    color: #2d3a8c;
    padding: 0.4em 0.9em;
    margin: 0.6em 0;
    font-style: normal;
  }
  blockquote p { margin: 0; }
  table { border-collapse: collapse; width: 100%; font-size: 0.95em; }
  th { background: #4a6cf7; color: #fff; padding: 0.4em 0.8em; text-align: left; font-weight: normal; }
  td { border: 1px solid #d0d8ff; padding: 0.4em 0.8em; }
  tr:nth-child(even) td { background: #f5f7ff; }
  .columns {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1.5em;
  }
  .columns > div {
    background: #f5f7ff;
    border-radius: 6px;
    padding: 0.8em 1em;
  }
  section.title {
    text-align: center;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    background: #f5f7ff;
  }
  section.title h1 { font-size: 3em; border: none; }
  section.title p { color: #555e7a; font-size: 1.1em; margin: 0.3em 0; }
---

<!-- _class: title -->

# artifact-reject

Real-time artifact rejection for brain-computer interfaces

**Hack Duke · 2026**

---

# The problem

BCIs restore movement, speech, and independence to patients with paralysis, ALS, and epilepsy.

They work by decoding electrical signals from the brain — signals that are easily corrupted by muscle activity, movement, or electrical interference.

> When corrupted data reaches the decoder, it produces the wrong command. For a patient controlling a prosthetic or communication device, that failure matters.

---

# Why it's still a problem

Hardware has improved — better electrodes, better shielding. But real-time software artifact rejection in the signal pipeline is still fragmented and lab-specific.

The standard software approach — a per-channel z-score threshold — **misses 87% of artifacts** and can't detect power line interference at all.

Every lab recalibrates manually. No standard solution exists across devices or patients.

**Science Corp's Synapse is building the industry-standard neural data pipeline. We're building the artifact rejection layer for it.**

---

# Our approach

Two detectors running in real time on every 100ms window:

- **Adaptive amplitude detector** — threshold scales with each channel's own noise floor, no recalibration needed across patients or sessions
- **Spectral line noise detector** — catches 60 Hz interference that amplitude checks cannot see

Detected windows are blanked before reaching the decoder — a neutral output is always safer than a wrong one.

---

# Results

| | artifact-reject | Z-score baseline (5σ) |
|--|--|--|
| Artifacts detected | **83%** | 13% |
| Clean signal preserved | **85%** | 95% |

6× more artifacts caught. Built as a tap for **Science Corp's Synapse** — the emerging industry standard for neural data pipelines — so it works out of the box for any lab or device running on Synapse, with no changes to the recording setup.

---

<!-- _class: title -->

# Live demo

See what artifact rejection feels like —
control a BCI keyboard with your finger,
with and without our filter.

---

<!-- _class: title -->

# Thank You

James Mu (Duke) · Derek Mu (CMU)

`github.com/jamesmu/artifact-reject`

Drop-in artifact rejection for the Synapse neural interface platform.
Zero configuration. Real-time. Open source.

*Hack Duke · 2026*
