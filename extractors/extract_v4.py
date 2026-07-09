#!/usr/bin/env python3
"""v4 — hybrid vision extractor. U2-Net silhouette + waist/hem geometry (from v3)
locate the board-short region; the cropped region is sent to the Claude API with a
structured-output schema that returns waistband color, ranked shorts colors, and the
Frame+Base+Accent archetype (registry/taxonomy.md). Written 2026-07-08 to break the
pixel-clustering plateau (v3 = 67% wb / 42% strict on the 73-label set).

Usage: python extractors/extract_v4.py <list.txt> [--model claude-opus-4-8] [--full]
  list.txt  : whitespace-separated photo filenames under top5_photos/
  --full    : send the whole photo instead of the segmentation crop (fallback path)
Requires: ANTHROPIC_API_KEY in env (or a .env in cwd), rembg[cpu], anthropic SDK.
Writes v4_output.csv with score.py-compatible columns (photo_file, waistband, shorts_colors)."""
import base64, csv, io, json, os, sys
import numpy as np
from PIL import Image
from rembg import remove, new_session
import anthropic

REF_COLORS = ["black","charcoal","white","gray","navy","royal blue","light blue","teal",
"green","lime","yellow","gold","orange","coral","red","maroon","pink","magenta",
"purple","lavender","tan/bone","brown"]
ARCH_FRAME = ["frame","reverse frame","no frame"]
ARCH_BASE  = ["solid","gradient","pattern","energy-element","graffiti"]
ARCH_ACCENT = ["block panels","trim/piping","graphic/silhouette","bands","none"]

SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "waistband": {"type": "string", "enum": REF_COLORS + ["unreadable"],
            "description": "Dominant color of the waistband (top band of the shorts). 'unreadable' only if the band is fully hidden."},
        "shorts_colors": {
            "type": "array",
            "items": {"type": "object", "additionalProperties": False,
                "properties": {
                    "color": {"type": "string", "enum": REF_COLORS},
                    "coverage": {"type": "number", "description": "Approx fraction of the shorts area, 0-1"}},
                "required": ["color", "coverage"]},
            "description": "Colors present in the shorts body, ordered by area (largest first)."},
        "frame": {"type": "string", "enum": ARCH_FRAME},
        "base":  {"type": "string", "enum": ARCH_BASE},
        "accent": {"type": "string", "enum": ARCH_ACCENT},
        "notes": {"type": "string", "description": "One short sentence describing the design."}},
    "required": ["waistband", "shorts_colors", "frame", "base", "accent", "notes"],
}

PROMPT = ("This image shows an NPC Men's Physique competitor's board shorts (posing trunks). "
    "Report only the SHORTS — ignore the stage backdrop, floor, skin, tan, and any competitor "
    "number disc. If the shorts have a gradient, list each color band in shorts_colors. "
    "WAISTBAND: report the color of the narrow horizontal band at the very TOP of the shorts "
    "ONLY — the strip the drawstring runs through. This band is very often a solid black "
    "regardless of the shorts body color; look specifically at that top strip and do not let "
    "the dominant body color bleed into this answer. If the top band is a different color from "
    "the body (e.g. black waistband over a teal short), report the BAND color. "
    "Also treat a black structural border/side-line as a 'frame' even when the body is one solid "
    "color. Use the archetype grammar: "
    "frame (a structural black border/waistband+side lines containing the design), "
    "base (the main treatment: solid/gradient/pattern/energy-element/graffiti), "
    "accent (secondary element: block panels/trim/graphic/bands/none).")

def load_dotenv():
    for p in (".env", os.path.join(os.path.dirname(__file__), "..", ".env")):
        if os.path.exists(p) and not os.environ.get("ANTHROPIC_API_KEY"):
            for line in open(p):
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

def garment_crop(path, session):
    """Return a PIL crop of the waist->hem garment region, or the center-body box on failure."""
    im = Image.open(path).convert("RGB"); w, h = im.size
    A = np.array(im)
    M = np.array(remove(im, session=session, only_mask=True)) > 128
    ys, xs = np.where(M)
    if len(ys) < h*w*0.03:
        return im.crop((int(w*.20), int(h*.40), int(w*.80), int(h*.75)))
    top, bot = int(ys.min()), int(ys.max())
    body = bot - top
    # waist ~ 40% down the silhouette, hem ~ 78%; widen x to the silhouette bounds + margin
    y0 = max(top + int(body*0.34), 0)
    y1 = min(top + int(body*0.82), h)
    xL = max(int(xs.min()) - int(w*0.03), 0)
    xR = min(int(xs.max()) + int(w*0.03), w)
    return im.crop((xL, y0, xR, y1))

def img_b64(im, max_edge=768):
    im = im.copy()
    im.thumbnail((max_edge, max_edge))
    buf = io.BytesIO(); im.save(buf, format="JPEG", quality=88)
    return base64.standard_b64encode(buf.getvalue()).decode()

def analyze(path, session, client, model, full=False):
    im = Image.open(path).convert("RGB") if full else garment_crop(path, session)
    resp = client.messages.create(
        model=model, max_tokens=1024,
        output_config={"format": {"type": "json_schema", "schema": SCHEMA}},
        messages=[{"role": "user", "content": [
            {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": img_b64(im)}},
            {"type": "text", "text": PROMPT}]}])
    if resp.stop_reason == "refusal":
        return {"photo_file": os.path.basename(path), "waistband": "unreadable",
                "shorts_colors": "", "archetype": "", "notes": "refusal"}
    data = json.loads(next(b.text for b in resp.content if b.type == "text"))
    shorts = " + ".join(f"{c['color']}({c['coverage']:.2f})" for c in data["shorts_colors"])
    return {"photo_file": os.path.basename(path), "waistband": data["waistband"],
            "shorts_colors": shorts,
            "archetype": f"{data['frame']} + {data['base']} + {data['accent']}",
            "notes": data.get("notes", "")}

if __name__ == "__main__":
    load_dotenv()
    args = sys.argv[1:]
    model = "claude-opus-4-8"; full = False; listfile = None
    i = 0
    while i < len(args):
        if args[i] == "--model": model = args[i+1]; i += 2
        elif args[i] == "--full": full = True; i += 1
        else: listfile = args[i]; i += 1
    if not listfile: sys.exit("usage: extract_v4.py <list.txt> [--model M] [--full]")
    session = None if full else new_session("u2net")
    client = anthropic.Anthropic()
    out = []
    for name in open(listfile).read().split():
        try:
            r = analyze("top5_photos/" + name, session, client, model, full)
        except Exception as e:
            r = {"photo_file": name, "waistband": "unreadable", "shorts_colors": "",
                 "archetype": "", "notes": f"error: {e}"}
        out.append(r); print(r["photo_file"], "| wb:", r["waistband"], "| shorts:", r["shorts_colors"], "|", r["archetype"])
    with open("v4_output.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["photo_file","waistband","shorts_colors","archetype","notes"])
        w.writeheader(); w.writerows(out)
    print(f"\nv4 ({model}{' full-photo' if full else ' crop'}) analyzed {len(out)} -> v4_output.csv")
