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

real-time artifact rejection for brain-computer interfaces

**James Mu (Duke)** and **Derek Mu (CMU)**
*HackDuke 2026*

---

# The problem

![bg right:36% contain](assets/bci/synchron.png)

BCIs decode brain signals into commands — but artifacts corrupt the signal and cause wrong outputs.

> For a patient controlling a prosthetic, that failure matters.

---

# The gap

![bg right:35%](assets/bci/utah_array.jpg)

Z-score thresholding **misses 87% of artifacts.**

No standard solution exists across labs or devices.

---

# Our approach

- **MAD** — adaptive amplitude threshold, no recalibration
- **FFT** — catches 60 Hz line noise z-score misses

![w:820px](assets/approach.png)

---

# Results

| | artifact-reject | Baseline |
|--|--|--|
| Artifacts detected | **63%** | 13% |

**5× more caught.** Drop-in for Science Corp's Synapse.

![w:1000px](assets/results.png)

---

<!-- _class: title -->

# Live demo

BCI keyboard — with and without our filter.

---

<!-- _class: title -->

# Thank You

James Mu (Duke) · Derek Mu (CMU)

`github.com/jamesmu03/artifact-reject`

*HackDuke 2026*
