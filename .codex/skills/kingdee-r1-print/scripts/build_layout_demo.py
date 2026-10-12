"""Build a static layout Demo from a known valid Kingdee export and JSON layout."""
import argparse
import copy
import hashlib
import json
import xml.etree.ElementTree as ET
from pathlib import Path

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--source", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    p.add_argument("--layout", type=Path, default=Path(__file__).resolve().parents[1]/"assets"/"operation-demo-layout.json")
    a = p.parse_args()
    if a.source.resolve() == a.output.resolve():
        p.error("Output must be a candidate file, not the source.")
    raw = a.source.read_bytes()
    root = ET.fromstring(raw)
    layout = json.loads(a.layout.read_text(encoding="utf-8"))
    styles = root.find("Styles")
    if root.tag != "DocRoot" or styles is None or not styles.get("version"):
        p.error("Use an exported, valid DocRoot template with Styles@version.")
    base = root.find("Styles/Style")
    if base is None:
        p.error("Source has no reference style.")
    base = copy.deepcopy(base)
    sources_before = ET.tostring(root.find("DataSources"), encoding="unicode")
    style_attrs = dict(styles.attrib)
    styles.clear()
    styles.attrib.update(style_attrs)
    for sid, spec in layout["styles"].items():
        style = copy.deepcopy(base)
        style.set("id", sid)
        style.find("Font").set("size", str(spec["size"]))
        alignment = style.find("Alignment")
        alignment.set("horizontal", spec["horizontal"])
        alignment.set("vertical", "middle")
        alignment.set("wrapText", str(spec["wrap"]))
        alignment.set("padding", "2,2,2,2")
        for border in style.findall("Borders/Border"):
            bordered = spec["bordered"] and border.get("position") in ("left","right","top","bottom")
            border.set("lineStyle", "Single" if bordered else "NullLine")
        styles.append(style)
    report = root.find("Report")
    report_attrs = dict(report.attrib)
    report.clear()
    report.attrib.update(report_attrs)
    page_spec = layout["page"]
    page = ET.SubElement(report, "Page", id="page1", width=str(page_spec["width"]), height=str(page_spec["height"]))
    objects = ET.SubElement(page, "Sub-objects")
    ids = set()
    for spec in layout["controls"]:
        if spec["id"] in ids:
            p.error("Duplicate control ID")
        ids.add(spec["id"])
        x,y,w,h = (spec[k] for k in ("x","y","width","height"))
        if min(x,y) < 0 or min(w,h) <= 0 or x+w > page_spec["width"] or y+h > page_spec["height"]:
            p.error("Control outside fixed page: " + spec["id"])
        if spec["styleId"] not in layout["styles"]:
            p.error("Unknown style: " + spec["id"])
        attrs = {k: str(spec[k]) for k in ("id","styleId","x","y","width","height")}
        tag = spec["type"]
        if tag == "Text":
            attrs["whiteSpaceIgnoreBarCode"] = "False"
        elif tag == "Barcode":
            attrs.update(EncodeType=spec.get("EncodeType", "Qrcode"), BarcodeAlign="Center", LabelLocation="BottomCenter")
        else:
            p.error("Static Demo builder supports only Text and Barcode")
        obj = ET.SubElement(objects, tag, **attrs)
        ET.SubElement(obj, "Data").text = spec["text"]
    paper = root.find("PrintInfo/PaperSetup")
    paper.find("Paper").text = page_spec["paper"]
    paper.find("Orientation").text = page_spec["orientation"]
    paper.find("PageMargin").attrib.update({k:str(v) for k,v in page_spec["margin"].items()})
    paper.find("Header").attrib.update(height="0", margin="0")
    paper.find("Footer").attrib.update(height="0", margin="0")
    if ET.tostring(root.find("DataSources"), encoding="unicode") != sources_before:
        raise RuntimeError("Unexpected data-source mutation")
    ET.indent(root, space="  ")
    data = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_bytes(data)
    print(json.dumps({"candidate": a.output.name, "controls": len(ids), "mode": "static-demo",
                      "styles_version": styles.get("version"), "sha256": hashlib.sha256(data).hexdigest()},
                     ensure_ascii=False))

if __name__ == "__main__":
    main()
