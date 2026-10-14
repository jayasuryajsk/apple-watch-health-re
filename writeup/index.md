---
title: "Reverse Engineering the Apple Watch's AFib Detector from Publicly Downloadable Firmware"
subtitle: "Inside Tellurium, Nebula, and the 189-model zoo shipped in watchOS 27"
date: 2026-10-15
---

# Reverse Engineering the Apple Watch's AFib Detector from Publicly Downloadable Firmware

*Inside Tellurium, Nebula, and the 189-model zoo shipped in watchOS 27*

Your Apple Watch runs a classifier that can tell you to go see a doctor about your heart.
It's FDA-cleared. Almost nobody has ever read its code. I didn't have to either —
it turns out Apple will ship it to anyone who asks their CDN nicely, and with the right
tools, the whole health-algorithm stack opens up like a book. This is what I found.

## The short version

Using nothing but publicly downloadable firmware (no hardware, no exploit, no developer
account), I extracted every system binary from watchOS 27.0.1 and mapped the algorithms
behind the Watch's health features. Highlights:

- **The AFib detector is a tachogram classifier, not an ECG analyzer.** Its input is
  240 consecutive beat-to-beat intervals — the RR series — which is why irregular-rhythm
  notifications work on watches *without* an ECG electrode.
- It's actually **two identical neural networks voting** — an ensemble Apple internally
  calls **"Tellurium"** (the service logs `Tellurium AFib probabilities from two models`).
- Each Tellurium net is a **399 KB multi-scale 1D CNN** — trained with TensorFlow 1.11,
  shipped essentially unchanged since watchOS 6 (2019). The FDA-cleared feature running
  on ~100 million wrists is a 2018-era model you could fit in a floppy disk image
  four hundred times over.
- The **sleep-apnea detector ("Nebula")** is a conv+LSTM network reading a
  300 × 65 × 3 overnight feature tensor.
- The optical heart sensor has a **neural front-end** (`dppg_to_features`): raw
  4-wavelength PPG goes in, a 256-dim physiological embedding comes out.
- The gait model has literal named outputs: `InitialContact`, `ToeOff`,
  `GroundContactTime` — your walking cycle, decomposed by an RNN.
- And a codename registry that reads like a periodic table: **Tellurium, Cassia,
  Nebula, Scandium, Kali, Lavender, Kappa, Brook, Willem, Windbreaker.**

## How the firmware was obtained (the unglamorous part)

Every iPhone and Watch update flows through Apple's public CDN. The same is true for
full restore images — IPSWs — which community indexes (AppleDB) catalog with checksums.
Downloading watchOS 27.0.1 for the Series 10 is a single `curl` to
`updates.cdn-apple.com`, no authentication. This is by design: Finder needs these
URLs to restore your device.

Two things made it non-trivial:

1. **A chunked downloader silently corrupted the first download.** File size matched
   exactly; a stalled chunk left a hole. The SHA-256 from AppleDB caught it. Lesson
   re-learned: always verify, single-stream if paranoid.
2. **The system volume is now an Apple Encrypted Archive** (`.dmg.aea`). The excellent
   open-source [`ipsw`](https://github.com/blacktop/ipsw) toolchain decrypts these
   transparently — this is not DRM, it's integrity packaging, and the tools handle it.

From there: extract the dyld shared cache, pull **all 3,034 system binaries** out as
standalone Mach-O files, and mount the full filesystem. The entire watchOS codebase,
greppable.

## Finding the heart

The first hint was a framework named with suspicious confidence:
`HeartRhythmAlgorithms.framework`. Inside it, an XPC service:

```
HRAClassifierService.xpc/
├── HRAClassifierService          (the daemon)
├── Te_c3seuakuh8.mlmodelc        (compiled CoreML model)
└── Te_tjejjxf8q3.mlmodelc        (compiled CoreML model)
```

Strings in the daemon settle the naming question immediately:

```
Tellurium AFib probabilities from two models:
Te_c3seuakuh8
Te_tjejjxf8q3
```

And the Objective-C interface (via class-dump) settles the input question:

```
@protocol HRATachogramClassifierXPCProtocol
- (void)classifyTachograms:(... /* tachogram */)reply:(...);
```

A **tachogram** — the sequence of RR intervals between heartbeats. Not a waveform.
The watch measures intervals optically, builds the tachogram, and the classifier
decides whether the *rhythm* is irregular. The ECG app's waveform analysis is a
separate pipeline (`HRAWaveformProcessor` + `HRAAlgorithmCassiaDelegate` — the
"Cassia" family), running only where there's an electrode.

## Tellurium, dissected

Compiled CoreML bundles carry their architecture in the open (`model.espresso.net`
is JSON) along with training provenance in `metadata.json`:

| | |
|---|---|
| Input | `Float32 [1, 240, 1]` — 240-entry tachogram |
| Output | `RHYTHM_TYPE_HEAD/FC_1/fully_connected/BiasAdd` |
| Architecture | 28 × 1D convolutions, multi-scale kernels {1,3,5,7}, channels 8→16→32, 3 max-pool stages, residual elementwise pairs, final FC |
| Weights | 399 KB per model (two models, identical architecture) |
| Trained with | `tensorflow==1.11.0`, converted with coremltools `4.0b2` |
| Availability floor | watchOS 6.0 — shipping since 2019 |

Two details worth pausing on:

**The ensemble.** Both models are architecturally identical, take the same input, and
their AFib probabilities are combined by the service. Same architecture, different
training runs — a classic robustness play, presumably part of what gave Apple the
confidence to seek FDA clearance. (The AFib History feature — the 7-day burden
estimate — separately exposes `burdenPercentage` with a
`burdenPercentageWasClampedToLowerBound` flag. Clamping exists, and it's documented
in the API surface.)

**The age.** TensorFlow 1.11 is from 2018. coremltools 4.0b2 from 2020. The
availability metadata says watchOS 6. Whatever network protects wrists today has
roots seven years old. That's not a scandal — it's how certified medical software
works: you don't retrain what you've validated. But it's a perspective check on
the industry's obsession with scale: a state-of-the-art-2018 network, 399 KB,
ensemble-of-two, FDA-cleared, on 100M+ devices.

## The rest of the body

The same sweep across the system volume:

**Nebula — sleep apnea.** `BreathingAlgorithmsWatchInternal.framework` ships
`NebulaBDModel`: five parallel 5×9 convolutions → two LSTM layers → three FC heads,
consuming a `[1, 300, 65, 3]` tensor — 300 timesteps × 65 engineered features × 3
channels of overnight signals. Trained in PyTorch 2.0. This is the model behind the
FDA-cleared breathing-disturbance notifications.

**The optical sensor's neural front-end.** `AppleElementsAlgorithms.framework`
contains `dppg_to_features`: input `[1, 1, 64, 4]` (64 samples of 4-wavelength PPG —
the raw multi-LED optical signal), output `[1, 1, 256]` — a learned embedding that
the downstream heart-rate and oxygenation algorithms consume. The "sensor fusion"
layer is itself a neural network.

**Gait.** `CoreMotionModels.framework` ships `CMGaitEventsRegression`, an RNN over
`[1, 128, 6]` (accel + gyro) with named regression outputs: `InitialContact`,
`ToeOff`, `GroundContactTime`. That's the walking-steadiness feature's skeleton.

**Temperature and sleep scheduling.** The element-codename scheme extends through
the "HealthLite" daemon family: **Kali** is the wrist-temperature service (thermal
coexistence thresholds, battery-compensated publishing, a sub-algorithm named
"Willem"), and **Lavender** is the sleep-session state machine that predicts when
your sleep session starts and ends.

**Fall and crash detection.** A C++ namespace called `CMMsl` (Core Motion Sensor
Library) contains `FallSnippet` (the input window), `FallDetectionReplay` (a replay
harness for recorded fall sequences), and `KappaCrashResult` — crash detection's
codename. The classifier itself loads through `CoreMotionFDNML`, which resolves
CoreML models *by name at runtime* — the fall model isn't sitting in the image as a
plain `.mlmodelc`, and hunting its provisioning path is an open thread.

## The zoo

watchOS 27 ships **189 compiled CoreML models**. Beyond the biometric nine:
twenty-plus battery degradation and time-to-empty predictors, cellular throughput
forecasting, WiFi stall detection, a genuine attention transformer for head-gesture
(nod/shake) recognition, and more. On-device ML is roughly an order of magnitude
more pervasive than any public documentation suggests — and almost none of it is
reachable by third-party apps. It's an invisible operating system of tiny models.

## What this doesn't tell us

Honesty section, because a writeup without limits is marketing:

- I did not (and won't) publish Apple's binaries or raw weights. Everything here is
  *about* the models — architecture, interfaces, provenance — not the models
  themselves.
- Architecture is not evaluation. Knowing Tellurium is a 28-layer CNN says nothing
  about its sensitivity on real patients. Nothing here is a clinical claim.
- Training data, thresholds applied *after* the classifier (the escalation logic
  that decides when to actually alert), and the server-side components remain
  unread — the escalation logic is the next target.

## Reproduce it

Everything above came from public artifacts and open tools:

```bash
# 1. Fetch firmware (SHA-256 verify against AppleDB!)
ipsw download appledb --os watchOS --latest --release --device Watch7,1 --json
curl -O <url> && shasum -a 256 Watch7,1_*_Restore.ipsw

# 2. All system binaries
ipsw extract --dyld Watch7,1_27.0.1_24R365_Restore.ipsw
ipsw dyld extract dyld_shared_cache_arm64e --all -o alldylibs

# 3. Interfaces
ipsw class-dump dyld_shared_cache_arm64e \
  /System/Library/PrivateFrameworks/HeartRhythmAlgorithms.framework/HeartRhythmAlgorithms

# 4. Full filesystem (AEA decryption handled transparently)
ipsw mount fs Watch7,1_27.0.1_24R365_Restore.ipsw
```

Model decoding is a hundred lines of Python against the espresso JSON — script in
[this repo](../tools/espresso_dump.py).

## Thanks and threads

Open questions I'd love help with: the fall-detection model's provisioning path,
the Cassia ECG pipeline's implementation, and whether the Te_ twins differ in
training data or just seeds. The codename registry is surely incomplete.

*Analysis performed on firmware I'm licensed to run, for interoperability and
research purposes. No Apple code, weights, or assets are redistributed here.*
