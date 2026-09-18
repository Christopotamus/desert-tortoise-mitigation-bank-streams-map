#!/usr/bin/env python3
"""Trim context layers (counties, cities, highways, labels) out of the large KMZ files.

Usage: python3 tools/trim_kmz.py

Reads each source KMZ from the repo root and writes a "_lite" copy next to it.
The originals are never modified. Only the <Document> blocks named in DROP are
removed; everything else in doc.kml is passed through as-is.
"""
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SOURCES = [
    "Mojave_RUs_20220727_V1.kmz",
    "Mojave_Watersheds_20220727_V1.kmz",
]

# Top-level <Document> names that hold context layers, not service areas.
DROP = {"County", "County Labels", "Cities", "Road Label", "Highways"}

XSI_NS = 'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'

# The Google Earth export nests each layer as a <Document> exactly one tab deep.
DOC_OPEN = "\n\t<Document"
DOC_CLOSE = "\n\t</Document>"


def trim_kml(kml):
    """Return (trimmed kml text, list of dropped Document names)."""
    out = []
    dropped = []
    pos = 0
    while True:
        start = kml.find(DOC_OPEN, pos)
        if start == -1:
            out.append(kml[pos:])
            break
        end = kml.find(DOC_CLOSE, start)
        if end == -1:
            sys.exit("unbalanced <Document> block")
        end += len(DOC_CLOSE)
        block = kml[start:end]
        name = re.search(r"<name>(.*?)</name>", block, re.S).group(1)
        out.append(kml[pos:start])
        if name in DROP:
            dropped.append(name)
        else:
            out.append(block)
        pos = end
    trimmed = "".join(out)

    # The export uses xsi:schemaLocation without declaring xsi, which is not
    # well-formed XML and makes browser DOMParser reject the file.
    if "xsi:" in trimmed and XSI_NS not in trimmed:
        trimmed = trimmed.replace("<kml ", "<kml " + XSI_NS + " ", 1)
    return trimmed, dropped


def main():
    for name in SOURCES:
        src = ROOT / name
        dst = ROOT / (src.stem + "_lite.kmz")
        with zipfile.ZipFile(src) as zin:
            kml, dropped = trim_kml(zin.read("doc.kml").decode("utf-8"))
            missing = DROP - set(dropped)
            print(f"{name}: dropped {sorted(dropped)}"
                  + (f" (not present: {sorted(missing)})" if missing else ""))
            with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zout:
                zout.writestr("doc.kml", kml)
                for info in zin.infolist():
                    if info.filename != "doc.kml":
                        zout.writestr(info.filename, zin.read(info.filename))
        print(f"  {src.stat().st_size / 1024:,.0f} KB -> {dst.name} {dst.stat().st_size / 1024:,.0f} KB")


if __name__ == "__main__":
    main()
