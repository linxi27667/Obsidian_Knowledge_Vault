"""Preflight Kingdee r1-print XML without pretending to verify business fields."""
import argparse
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

def validate(path):
    root = ET.parse(path).getroot()
    errors, warnings = [], []
    if root.tag != "DocRoot":
        errors.append("Root must be DocRoot")
    for tag in ("Parameters", "DataSources", "Styles", "Layers", "Report", "PrintInfo"):
        if root.find(tag) is None:
            errors.append("Missing root section: " + tag)
    styles = root.find("Styles")
    if styles is None or not styles.get("version"):
        errors.append("Missing Styles@version: native StyleParser.Upgrade can throw NullReferenceException")
    style_ids = [s.get("id") for s in root.findall("Styles/Style")]
    if len(style_ids) != len(set(style_ids)) or None in style_ids:
        errors.append("Style IDs missing or duplicated")
    ids = [e.get("id") for e in root.findall(".//Report//*[@id]")]
    if len(ids) != len(set(ids)):
        errors.append("Duplicate report IDs")
    sources = {e.get("name") for e in root.findall("DataSources/Reference")}
    controls = []
    for page in root.findall("Report/Page"):
        try:
            pw, ph = float(page.get("width")), float(page.get("height"))
        except (TypeError, ValueError):
            errors.append("Invalid page size")
            continue
        for control in page.findall("Sub-objects/*"):
            controls.append(control)
            if control.get("styleId") not in style_ids:
                errors.append("Unknown style for " + str(control.get("id")))
            try:
                x,y,w,h = (float(control.get(k)) for k in ("x","y","width","height"))
                if x < 0 or y < 0 or w <= 0 or h <= 0 or x+w > pw or y+h > ph:
                    warnings.append("Outside fixed page or nonpositive size: " + str(control.get("id")))
            except (TypeError, ValueError):
                warnings.append("Nonstandard geometry, inspect native control: " + str(control.get("id")))
    bindings = []
    for data in root.findall(".//Report//Data"):
        if data.get("dataSource") and data.get("dataSource") not in sources:
            errors.append("Data refers to unknown dataSource " + data.get("dataSource"))
        if data.get("bindField"):
            bindings.append({"dataSource": data.get("dataSource"), "bindField": data.get("bindField")})
    return {"file": Path(path).name, "passed": not errors, "controls": len(controls),
            "styles_version": styles.get("version") if styles is not None else None,
            "bindings_need_business_metadata": bindings, "errors": errors, "warnings": warnings}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("templates", nargs="+", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    results = []
    for path in args.templates:
        try:
            results.append(validate(path))
        except (OSError, ET.ParseError) as exc:
            results.append({"file": path.name, "passed": False, "errors": [str(exc)]})
    output = json.dumps(results, ensure_ascii=False, indent=2)
    print(output)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(output + "\n", encoding="utf-8")
    return 0 if all(r["passed"] for r in results) else 1

if __name__ == "__main__":
    sys.exit(main())
