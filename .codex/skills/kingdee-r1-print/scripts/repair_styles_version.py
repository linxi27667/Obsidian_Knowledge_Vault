"""Recover only the known missing Styles version from an exported reference."""
import argparse
import hashlib
import json
from pathlib import Path
from xml.dom import minidom

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--source", required=True, type=Path)
    p.add_argument("--reference", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    a = p.parse_args()
    if a.output.resolve() in (a.source.resolve(), a.reference.resolve()):
        p.error("Write a candidate output; copy it over the source after validation if authorized.")
    original = minidom.parse(str(a.reference))
    source = minidom.parse(str(a.source))
    good = original.documentElement.getElementsByTagName("Styles")
    bad = source.documentElement.getElementsByTagName("Styles")
    if len(good) != 1 or len(bad) != 1 or not good[0].getAttribute("version"):
        p.error("Missing or ambiguous Styles version in the reference.")
    if bad[0].hasAttribute("version"):
        p.error("Source already has Styles version; diagnose the actual error instead.")
    bad[0].setAttribute("version", good[0].getAttribute("version"))
    raw = source.toxml(encoding="utf-8")
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_bytes(raw)
    print(json.dumps({"candidate": a.output.name, "styles_version": good[0].getAttribute("version"),
                      "sha256": hashlib.sha256(raw).hexdigest()}, ensure_ascii=False))

if __name__ == "__main__":
    main()
