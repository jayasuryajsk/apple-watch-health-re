#!/usr/bin/env python3
"""espresso_dump.py — architecture summary for compiled CoreML (.mlmodelc) bundles.

Compiled CoreML models ship as directories containing model.espresso.net (a JSON
layer graph), model.espresso.shape, model.espresso.weights and metadata.json.
This tool prints a human-readable architecture table + training provenance.

Usage:
    python3 espresso_dump.py /path/to/Model.mlmodelc [more paths or a parent dir]
    python3 espresso_dump.py --json /path/to/Model.mlmodelc

Standard library only. For analysis of firmware you are licensed to run.
"""

import json
import os
import re
import sys
from collections import Counter

INTERESTING = ("convolution", "inner_product", "rnn_arch", "pool", "softmax_nd", "convolution_dilated")


def tf_short(name: str) -> str:
    """Collapse original TF node paths, e.g. FE/Multi_Scale_Convolution1D_1_..._5 -> MSC-1.conv(k5)."""
    m = re.match(r"FE/Multi_Scale_Convolution1D_(\d+)_convolution1D_(\d+)_(\d+)", name)
    if m:
        return f"MSC-{m.group(1)}.conv{m.group(2)}(k{m.group(3)})"
    return name.rsplit("/", 1)[-1][:36]


def dump(path: str) -> dict:
    net = json.load(open(os.path.join(path, "model.espresso.net")))
    meta = json.load(open(os.path.join(path, "metadata.json")))[0]
    layers = net.get("layers", [])
    hist = Counter(l["type"] for l in layers)

    rows = []
    for l in layers:
        t = l["type"]
        if t == "convolution":
            rows.append(("conv", tf_short(l.get("name", "?")), l.get("C", "?"), f"{l.get('Nx','?')}x{l.get('Ny','?')}"))
        elif t == "inner_product":
            rows.append(("fc", l.get("name", "?")[:40], l.get("C", "?"), ""))
        elif t == "rnn_arch":
            rows.append(("rnn", l.get("name", "?")[:40], "", f"mode={l.get('mode', '?')}"))
        elif t == "pool":
            rows.append(("pool", l.get("name", "?")[:40], "", f"k={l.get('Nx', '?')}"))

    ud = meta.get("userDefinedMetadata", {})
    info = {
        "model": os.path.basename(path),
        "weights_kb": os.path.getsize(os.path.join(path, "model.espresso.weights")) // 1024,
        "inputs": [(i["name"], i.get("shape"), i.get("dataType")) for i in meta.get("inputSchema", [])],
        "outputs": [(o["name"], o.get("shape")) for o in meta.get("outputSchema", [])],
        "layer_histogram": dict(hist),
        "layers": rows,
        "trained_with": ud.get("com.github.apple.coremltools.source", "?"),
        "coremltools": ud.get("com.github.apple.coremltools.version", "?"),
        "mldb_token": ud.get("mldb_token", ""),
    }
    return info


def render(info: dict):
    print(f"\n{'=' * 66}\n{info['model']}  ({info['weights_kb']} KB weights)")
    for n, s, t in info["inputs"]:
        print(f"  IN : {n:32s} shape={s} {t}")
    for n, s in info["outputs"]:
        print(f"  OUT: {n}")
    print(f"  trained: {info['trained_with']} via coremltools {info['coremltools']}")
    if info["mldb_token"]:
        print(f"  mldb token: {info['mldb_token']}")
    print(f"  layers: {info['layer_histogram']}")
    for kind, name, c, extra in info["layers"]:
        cfield = f"C={c}" if c not in ("", "?") else ""
        print(f"    {kind:5s} {name:38s} {cfield:>7s} {extra}")


def main():
    args = sys.argv[1:]
    as_json = "--json" in args
    targets = []
    for a in args:
        if a == "--json":
            continue
        if os.path.isdir(a) and not a.endswith(".mlmodelc"):
            targets += [os.path.join(a, d) for d in sorted(os.listdir(a)) if d.endswith(".mlmodelc")]
        else:
            targets.append(a)
    infos = [dump(t) for t in targets]
    if as_json:
        json.dump(infos, sys.stdout, indent=1)
    else:
        for i in infos:
            render(i)


if __name__ == "__main__":
    main()
