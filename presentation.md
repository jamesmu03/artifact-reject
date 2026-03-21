---
marp: true
theme: default
paginate: true
style: |
  section {
    font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
    background: #ffffff;
    color: #1a1a2e;
    font-size: 20px;
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
  th { background: #4a6cf7; color: #fff; padding: 0.4em 0.8em; text-align: left; }
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

Real-time signal cleaning for brain-computer interfaces

**Hack Duke · 2026**

---

# BCIs are only as good as their signal

Brain implants are changing medicine — restoring movement to paralyzed patients, treating epilepsy, enabling speech for ALS patients.

But the signal they record is *constantly* getting corrupted: a twitch, a power outlet, a loose wire.

**Every major player has this problem.**
Neuralink, Synchron, Blackrock, Neuropace — none of them have solved it in software.

> The entire field assumes someone else has figured out signal quality. Nobody has.

---

# The current fix is a blunt instrument

The standard approach: flag any window above a fixed amplitude cutoff.

In our tests, it **rejected 100% of windows** — including the clean ones.

It also *completely misses* electrical interference, which looks quiet in amplitude but destroys the signal spectrally.

> Labs are flying blind and throwing away good data at the same time.

---

# Our approach: two targeted detectors

<div class="columns">

<div>

**Adaptive amplitude**
Sets the threshold relative to each channel's own noise floor — no manual tuning, works across rigs and patients

</div>

<div>

**Spectral line noise**
Catches 60 Hz electrical interference that no amplitude-based filter can see

</div>

</div>

Drops in as a real-time tap on live neural data. **Built and running today.**

---

# Results

| | **artifact-reject** | Fixed threshold |
|--|--|--|
| Bad signal caught | **83%** | 0% |
| Good signal kept | **85%** | 0% |
| Works out of the box | ✅ | ❌ |

The standard filter threw away everything. Ours surgically removes only what's corrupted.

---

<!-- _class: title -->

# Thank You

`github.com/jamesmu/artifact-reject`

*Hack Duke · 2026*
