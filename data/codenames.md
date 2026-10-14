# Apple Watch health-stack codename registry

Decoded from watchOS 27.0.1 (24R365) static analysis, October 2026. Each entry lists
the evidence so it can be independently verified. Incomplete by construction —
additions welcome via issues/PRs.

| Codename | Subsystem | Evidence |
|---|---|---|
| Tellurium (`Te_`) | AFib tachogram classifier family (2-model ensemble) | `HRATelluriumAnalyzer` class; service string "Tellurium AFib probabilities from two models"; `Te_c3seuakuh8`/`Te_tjejjxf8q3` bundles in `HRAClassifierService.xpc` |
| Cassia | ECG waveform analyzer family | `HRAAlgorithmCassiaDelegate` class alongside `HRAWaveformProcessor` |
| Nebula | Sleep-apnea / breathing-disturbance model | `NebulaBDModel.mlmodelc` in `BreathingAlgorithmsWatchInternal.framework`; `HKSHBreathingDisturbanceAnalysis` strings in SleepHealth |
| Scandium | SpO2 / blood-oxygen PPG processor | `Scandium::ScandiumPPG::SpO2Result` (C++ symbols); `SCProcessor ... forWindbreaker:` |
| Windbreaker | Sensor-stack mode flag in Scandium init | `initWithStartPacket:...forWindbreaker:hardwareModel:` selector |
| Kali | Wrist-temperature service | `PROGRAM:KaliAlgorithmService PROJECT:HealthLite-457.1`; TEMP_SAMPLE_FREQUENCY/TBC publish-range strings |
| Willem | Sub-algorithm inside Kali | "Event extends over Kali session end, do not apply Willem" |
| Lavender | Sleep-session predictor state machine | "Lavender predicted session start,end"; "sleep focus to ML wake" transitions |
| Kappa | Crash detection | `CMMsl::KappaCrashResult` C++ symbol |
| CMMsl | CoreMotion sensor library (fall detect, wrist detect, gestures) | `CMMsl::FallSnippet`, `FallDetectionReplay`, `WatchOnWristState` |
| Brook | Always-on motion gate detector | `BrookDetector.framework` + 115-feature MLP |
| Seymour | Fitness+ (workout video) stack | `Seymour*` framework family |
| Kali/Lavender/HRV | HealthLite daemon family | `PROJECT:HealthLite-457.1` program banners |
