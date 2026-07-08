#!/usr/bin/env python3
"""Rank UNLABELED photos by how hard they are for the automation to read and
emit a review CSV (machine guesses + blank brock_* columns) for ground-truth labeling.
Usage: python benchmark/pick_hard_cases.py <v3_output.csv> <v24_output.csv> <n> <out.csv>
Difficulty signals: v3 segmentation failure, UNREADABLE waistband (either extractor),
v3-vs-v2.4 disagreement on waistband or top shorts cluster, no dominant color cluster,
shorts color adjacent to skin tone, black shorts against a black backdrop, low v2.4 confidence."""
import csv, sys, os, re
sys.path.insert(0, os.path.dirname(__file__))
from score import norm, pred_top_cluster

def top_share(sh):
    m = re.search(r'\((0\.\d+)\)', sh or "")
    return float(m.group(1)) if m else 0.0

v3  = {r["photo_file"]: r for r in csv.DictReader(open(sys.argv[1]))}
v24 = {r["photo_file"]: r for r in csv.DictReader(open(sys.argv[2]))}
n, out_path = int(sys.argv[3]), sys.argv[4]
here = os.path.dirname(__file__)
labeled = set(open(os.path.join(here,"labeled_photos.txt")).read().split())
mani = {r["photo_file"]: r for r in csv.DictReader(open(os.path.join(here,"..","data","photo_manifest.csv")))}

rows = []
for pf, m in mani.items():
    if pf in labeled: continue
    a, b = v3.get(pf), v24.get(pf)
    score, why = 0.0, []
    if a is None:
        score += 3; why.append("v3 segmentation/waist failed")
    else:
        if a["waistband"] == "UNREADABLE": score += 2; why.append("v3 waistband unreadable")
        if not a["hem_pct_of_body"]: score += 1; why.append("v3 hem not found")
        if top_share(a["shorts_colors"]) < 0.40 and a["shorts_colors"]:
            score += 1.5; why.append("no dominant color cluster")
        if norm(a["skin"]) and pred_top_cluster(a["shorts_colors"]) in ("tan/bone","brown","red") \
           or (a["shorts_colors"] and pred_top_cluster(a["shorts_colors"]) == norm(a["skin"])):
            score += 1.5; why.append("shorts color near skin tone")
    if b is None:
        score += 2; why.append("v24 missing")
    else:
        if b["waistband"] == "UNREADABLE": score += 2; why.append("v24 waistband unreadable")
        if int(b["wb_confidence"] or 0) < 40: score += 1; why.append("v24 low wb confidence")
        if int(b["sh_confidence"] or 0) < 50: score += 1; why.append("v24 low shorts confidence")
        if "black" in (b["background_colors"] or "") and \
           (pred_top_cluster(b["shorts_colors"]) == "black" or (a and pred_top_cluster(a["shorts_colors"]) == "black")):
            score += 1.5; why.append("black-on-black")
    if a and b:
        if a["waistband"] != "UNREADABLE" and b["waistband"] != "UNREADABLE" \
           and norm(a["waistband"]) != norm(b["waistband"]):
            score += 2; why.append(f"waistband disagreement (v3:{a['waistband']} vs v24:{b['waistband']})")
        if a["shorts_colors"] and b["shorts_colors"] \
           and pred_top_cluster(a["shorts_colors"]) != pred_top_cluster(b["shorts_colors"]):
            score += 2; why.append(f"top-color disagreement (v3:{pred_top_cluster(a['shorts_colors'])} vs v24:{pred_top_cluster(b['shorts_colors'])})")
    rows.append({"photo_file": pf, "show": m.get("show",""), "class": m.get("class",""),
        "competitor": m.get("competitor",""), "gallery_url": m.get("gallery_url",""),
        "difficulty_score": round(score,1), "difficulty_reasons": "; ".join(why),
        "v3_waistband": a["waistband"] if a else "NO READ",
        "v3_shorts_colors": a["shorts_colors"] if a else "NO READ",
        "v3_skin": a["skin"] if a else "",
        "v24_background": b["background_colors"] if b else "", "v24_floor": b["floor_colors"] if b else "",
        "v24_waistband": b["waistband"] if b else "NO READ",
        "v24_shorts_colors": b["shorts_colors"] if b else "NO READ",
        "brock_waistband":"", "brock_shorts":"", "brock_archetype":"", "brock_brand":"", "brock_notes":""})

rows.sort(key=lambda r: -r["difficulty_score"])
with open(out_path, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows[:n])
print(f"wrote {min(n,len(rows))} of {len(rows)} unlabeled photos to {out_path}")
for r in rows[:n]:
    print(f"  {r['difficulty_score']:>4}  {r['photo_file']}  [{r['difficulty_reasons']}]")
