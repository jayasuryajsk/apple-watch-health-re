# Reproduction guide

Everything in the writeup derives from public firmware and open tooling.
Tested on macOS arm64 (Apple Silicon), October 2026.

## 0. Tooling

```bash
brew install blacktop/tap/ipsw    # firmware download/extract/mount/class-dump toolkit
```

## 1. Obtain firmware (no account required)

```bash
# Locate latest watchOS restore IPSW + expected SHA-256
ipsw download appledb --os watchOS --latest --release --device Watch7,1 --json

# Download single-stream and VERIFY (a chunked download once left a hole
# in a size-correct file — the checksum caught it)
curl -O "https://updates.cdn-apple.com/.../Watch7,1_27.0.1_24R365_Restore.ipsw"
shasum -a 256 Watch7,1_27.0.1_24R365_Restore.ipsw
```

Note: OTA payloads are AEA-wrapped archives the tooling can't always parse;
the full restore IPSW is the reliable path. The system volume inside it is
also AEA (`.dmg.aea`) — `ipsw` decrypts it transparently.

## 2. Extract everything

```bash
# dyld shared cache (~needs ~14 GB temp; point TMPDIR at a big disk)
TMPDIR=/big/disk/tmp ipsw extract --dyld Watch7,1_27.0.1_24R365_Restore.ipsw

# all 3,034 binaries as standalone Mach-Os
ipsw dyld extract <cache_dir>/dyld_shared_cache_arm64e --all -o alldylibs
```

## 3. Interfaces and filesystem

```bash
# ObjC class-dump straight from the cache
ipsw class-dump <cache_dir>/dyld_shared_cache_arm64e \
  /System/Library/PrivateFrameworks/HeartRhythmAlgorithms.framework/HeartRhythmAlgorithms

# mount the full system volume (AEA decryption; takes ~15 min)
ipsw mount fs Watch7,1_27.0.1_24R365_Restore.ipsw
```

## 4. Models

Find compiled CoreML bundles and decode them:

```bash
find <mountpoint> -name "*.mlmodelc" -type d | tee models.txt
python3 tools/espresso_dump.py /path/to/Te_c3seuakuh8.mlmodelc
```

## Storage notes

Peak working set is ~20 GB (IPSW 5.5 + decrypted DMG 8 + caches). An external
drive works fine. `strings <binary> | grep ...` is reliable on the extracted
slices; recursive `grep -r` over them is not.

## Legal

Restore IPSWs are freely distributed by Apple to the public. This analysis is
for research/interoperability. Do not redistribute Apple binaries or weights;
publish analysis only.
