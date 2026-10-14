# apple-watch-health-re

Binary-level reverse engineering of the Apple Watch's health algorithms, from
publicly downloadable watchOS 27.0.1 firmware. No exploits, no hardware, no
accounts — just public firmware images, open tooling, and a lot of `strings`.

**Read the writeup: [writeup/index.md](writeup/index.md)**

## Headline findings

- The FDA-cleared **AFib detector** ("Tellurium") is a **tachogram** (RR-interval)
  classifier — a two-model ensemble of 399 KB multi-scale 1D CNNs, trained with
  TensorFlow 1.11 and shipping since watchOS 6 (2019).
- The **sleep-apnea detector** ("Nebula") is a conv+LSTM over a 300×65×3 overnight
  feature tensor.
- The optical heart sensor's front-end (`dppg_to_features`) is itself a neural net:
  4-wavelength PPG in, 256-dim physiological embedding out.
- The gait model exposes named outputs: `InitialContact`, `ToeOff`, `GroundContactTime`.
- **189 compiled CoreML models** ship in a watchOS restore image.
- An internal codename registry (Tellurium, Cassia, Nebula, Scandium, Kali,
  Lavender, Kappa, Brook, Willem, Windbreaker, CMMsl) — see
  [data/codenames.md](data/codenames.md).

## Repository layout

| Path | Contents |
|---|---|
| `writeup/index.md` | The full writeup (blog-post form) |
| `tools/espresso_dump.py` | Architecture decoder for compiled CoreML bundles (stdlib-only Python) |
| `tools/REPRODUCE.md` | Exact command trail, from firmware download to class-dumps |
| `data/codenames.md` | Codename registry with evidence |

## Scope & ethics

Analysis of freely-distributed firmware for research and interoperability, on
platforms we're licensed to run. **No Apple binaries, weights, or assets are
redistributed in this repository** — only original analysis, derived metadata
(architectures, symbol/interface names), and tooling. Nothing here is a clinical
evaluation; no safety claims are made or implied about any device or algorithm.

## License

Text and tooling: MIT. Apple trademarks and any referenced artifacts belong to Apple.
