#!/usr/bin/env python3
"""Regression harness: score extractor output vs all ground-truth rounds.
Usage: python score.py <extractor_output.csv>   (needs photo_file, waistband, shorts_colors)"""
import csv, sys, glob, os
def norm(c):
    c=(c or "").lower()
    if "charcoal" in c or "black" in c or "bllack" in c: return "black"
    if "light-blue" in c or "light blue" in c or "turquoise" in c: return "lightblue"
    if "royal" in c or c.strip()=="blue": return "blue"
    if "purple" in c or "lavend" in c: return "purple"
    if "red" in c or "coral" in c or "maroon" in c: return "red"
    if "green" in c or "lime" in c: return "green"
    if "yellow" in c or "gold" in c: return "yellow"
    if "white" in c: return "white"
    if "navy" in c: return "navy"
    if "grey" in c or "gray" in c: return "gray"
    return c.split()[0] if c.strip() else ""
def primary(n):
    n=(n or "").lower()
    for c in ("black","white","blue","green","yellow","red","purple","orange","coral","maroon","turquoise","gold","grey","gray"):
        if c in n: return norm(c)
    return ""
gt = {}
for f in glob.glob(os.path.join(os.path.dirname(__file__),"ground_truth","round*_labels.csv")):
    rows = list(csv.reader(open(f)))
    hdr = rows[0]
    for r in rows[1:]:
        d = dict(zip(hdr,r)); gt[d.get("photo_file","")] = d
pred = {r["photo_file"]: r for r in csv.DictReader(open(sys.argv[1]))}
wb_h=wb_t=sh_h=sh_t=0
for f,d in gt.items():
    if f not in pred: continue
    b = norm(d.get("brock_waistband",""))
    m = norm(pred[f].get("waistband","") or pred[f].get("v24_waistband",""))
    if b: wb_t+=1; wb_h += (m==b)
    p = primary(d.get("brock_notes",""))
    if p:
        sh_t+=1
        mine = (pred[f].get("shorts_colors","") or pred[f].get("v24_shorts_colors","")).lower()
        sh_h += (p in norm(mine) or p in mine or (p=="black" and "charcoal" in mine)
                 or (p=="red" and ("maroon" in mine or "coral" in mine)) or (p=="yellow" and "gold" in mine))
print(f"waistband {wb_h}/{wb_t} = {wb_h/max(wb_t,1):.0%} | shorts primary {sh_h}/{sh_t} = {sh_h/max(sh_t,1):.0%} | matched labels: {len(set(gt)&set(pred))}")
