#!/usr/bin/env python3
"""Round-6 validation set: pick the N easiest and N hardest v4 reads on UNLABELED
athletes, so Brock can verify both ends of v4's confidence range.

Easiness is judged from v4's own output shape (v4 has no numeric confidence, so we
infer it): a clean single-color solid with a decisive archetype and a readable
waistband is easy to verify and low-risk; a fragmented multi-color read, a
near-skin-tone dominant, an 'unreadable' waistband, or a gradient/pattern with a
thin dominant band is hard. Output columns mirror the round-5 review pack.

Usage: python benchmark/pick_v4_validation.py <v4_output.csv> <n_each> <out.csv>"""
import csv, os, re, sys

SKIN_ADJACENT = {"tan/bone", "brown", "coral"}

def parse_shorts(s):
    out = []
    for seg in (s or "").split("+"):
        m = re.match(r"\s*(.+?)\((0?\.\d+|1\.0+)\)", seg)
        if m: out.append((m.group(1).strip(), float(m.group(2))))
    return out

def hardness(row):
    """Higher = harder to verify / more likely to need a human eye."""
    score, why = 0.0, []
    wb = (row.get("waistband") or "").strip()
    shorts = parse_shorts(row.get("shorts_colors", ""))
    arch = (row.get("archetype") or "")
    if wb in ("", "unreadable"): score += 3; why.append("waistband unreadable")
    if not shorts: score += 3; why.append("no shorts colors")
    else:
        top_color, top_cov = shorts[0]
        if top_cov < 0.45: score += 2; why.append(f"no dominant color (top {top_cov:.2f})")
        if len(shorts) >= 4: score += 1.5; why.append("4+ colors")
        elif len(shorts) == 3: score += 0.5; why.append("3 colors")
        if top_color in SKIN_ADJACENT: score += 1.5; why.append(f"dominant near skin tone ({top_color})")
    if "pattern" in arch or "gradient" in arch or "graffiti" in arch:
        score += 1; why.append("pattern/gradient/graffiti base")
    if "energy-element" in arch: score += 0.5; why.append("energy-element")
    return score, "; ".join(why) or "clean solid read"

here = os.path.dirname(__file__)
v4 = list(csv.DictReader(open(sys.argv[1])))
n = int(sys.argv[2]); out_path = sys.argv[3]
labeled = set(open(os.path.join(here, "labeled_photos.txt")).read().split())
mani = {r["photo_file"]: r for r in csv.DictReader(open(os.path.join(here, "..", "data", "photo_manifest.csv")))}

scored = []
for r in v4:
    pf = r["photo_file"]
    if pf in labeled or pf not in mani: continue
    if (r.get("notes") or "").startswith(("error", "refusal")): continue
    h, why = hardness(r)
    scored.append((h, why, r))
scored.sort(key=lambda t: t[0])

easiest = scored[:n]
hardest = list(reversed(scored[-n:]))
picks = [("easy", h, w, r) for h, w, r in easiest] + [("hard", h, w, r) for h, w, r in hardest]

cols = ["bucket","difficulty_score","difficulty_reasons","photo_file","show","class","competitor",
        "gallery_url","v4_waistband","v4_shorts_colors","v4_archetype","v4_notes",
        "brock_waistband","brock_shorts","brock_archetype","brock_brand","brock_notes"]
with open(out_path, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=cols); w.writeheader()
    for bucket, h, why, r in picks:
        m = mani.get(r["photo_file"], {})
        w.writerow({"bucket": bucket, "difficulty_score": round(h, 1), "difficulty_reasons": why,
            "photo_file": r["photo_file"], "show": m.get("show",""), "class": m.get("class",""),
            "competitor": m.get("competitor",""), "gallery_url": m.get("gallery_url",""),
            "v4_waistband": r.get("waistband",""), "v4_shorts_colors": r.get("shorts_colors",""),
            "v4_archetype": r.get("archetype",""), "v4_notes": r.get("notes",""),
            "brock_waistband":"", "brock_shorts":"", "brock_archetype":"", "brock_brand":"", "brock_notes":""})
print(f"wrote {len(picks)} ({n} easy + {n} hard) to {out_path}")
for bucket, h, why, r in picks:
    print(f"  [{bucket}] {h:>4}  {r['photo_file'][:32]:32} wb={r.get('waistband',''):10} {r.get('shorts_colors','')[:44]}")
