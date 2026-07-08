#!/usr/bin/env python3
"""Regression harness: score extractor output vs all ground-truth rounds.
Usage: python score.py <extractor_output.csv>   (needs photo_file, waistband, shorts_colors)
Shorts ground truth: primary color = first slash-segment of brock_shorts where that
column is populated and color-like (rounds 3-4); otherwise first color word in
brock_notes by fixed priority (rounds 1-2 legacy behavior).
Reports strict (predicted top cluster == label primary) and loose (label primary
appears anywhere in prediction); gate on strict."""
import csv, sys, glob, os, re
def norm(c):
    c=(c or "").lower()
    if "charcoal" in c or "black" in c or "bllack" in c: return "black"
    if "light-blue" in c or "light blue" in c or "baby-blue" in c or "baby blue" in c or "turquoise" in c: return "lightblue"
    if "navy" in c: return "navy"
    if "royal" in c or c.strip()=="blue": return "blue"
    if "purple" in c or "lavend" in c: return "purple"
    if "red" in c or "coral" in c or "maroon" in c: return "red"
    if "green" in c or "lime" in c: return "green"
    if "yellow" in c or "gold" in c: return "yellow"
    if "white" in c: return "white"
    if "grey" in c or "gray" in c: return "gray"
    return c.split()[0] if c.strip() else ""
def primary(n):
    n=(n or "").lower()
    for c in ("black","white","blue","green","yellow","red","purple","orange","coral","maroon","turquoise","gold","grey","gray"):
        if c in n: return norm(c)
    return ""
COLORWORD = re.compile(r'^(black|charcoal|bllack|white|grey|gray|blue|navy|royal|light.?blue|baby.?blue|turquoise|teal|green|lime|dark.?green|yellow|gold|red|coral|maroon|pink|magenta|purple|lavend\w*|orange|brown|tan|bone)', re.I)
def gt_shorts_primary(d):
    bs = (d.get("brock_shorts") or "").strip()
    if bs:
        first = re.split(r'[/+,]', bs)[0].strip()
        if COLORWORD.match(first): return norm(first), "column"
    return primary(d.get("brock_notes","")), "notes"
def pred_fields(row):
    wb = row.get("waistband","") or row.get("v24_waistband","")
    sh = row.get("shorts_colors","") or row.get("v24_shorts_colors","")
    return wb, sh
def pred_top_cluster(sh):
    seg = re.split(r'[+]', sh)[0]
    return norm(re.sub(r'\(.*', '', seg).strip())

def main(pred_csv):
    gt = {}
    for f in sorted(glob.glob(os.path.join(os.path.dirname(__file__),"ground_truth","round*_labels.csv"))):
        rnd = os.path.basename(f).split("_")[0]
        rows = list(csv.reader(open(f)))
        hdr = rows[0]
        for r in rows[1:]:
            d = dict(zip(hdr,r)); d["_round"]=rnd; gt[d.get("photo_file","")] = d
    pred = {r["photo_file"]: r for r in csv.DictReader(open(pred_csv))}

    stats = {}   # round -> [wb_hit, wb_tot, strict_hit, loose_hit, sh_tot, notes_derived]
    matched = 0
    for f,d in gt.items():
        if f not in pred: continue
        matched += 1
        s = stats.setdefault(d["_round"], [0,0,0,0,0,0])
        wb_pred, sh_pred = pred_fields(pred[f])
        b = norm(d.get("brock_waistband",""))
        if b:
            s[1]+=1; s[0] += (norm(wb_pred)==b)
        p, src = gt_shorts_primary(d)
        if p:
            s[4]+=1; s[5]+= (src=="notes")
            mine = sh_pred.lower()
            s[2] += (pred_top_cluster(sh_pred)==p)
            s[3] += (p in norm(mine) or p in mine or (p=="black" and "charcoal" in mine)
                     or (p=="red" and ("maroon" in mine or "coral" in mine)) or (p=="yellow" and "gold" in mine))

    T = [0,0,0,0,0,0]
    for rnd in sorted(stats):
        s = stats[rnd]
        T = [a+b for a,b in zip(T,s)]
        print(f"{rnd}: waistband {s[0]}/{s[1]} = {s[0]/max(s[1],1):.0%} | "
              f"shorts strict {s[2]}/{s[4]} = {s[2]/max(s[4],1):.0%} | loose {s[3]}/{s[4]} = {s[3]/max(s[4],1):.0%}"
              f"{'  [gt from notes: %d/%d]' % (s[5],s[4]) if s[5] else ''}")
    print(f"TOTAL: waistband {T[0]}/{T[1]} = {T[0]/max(T[1],1):.0%} | "
          f"shorts strict {T[2]}/{T[4]} = {T[2]/max(T[4],1):.0%} | loose {T[3]}/{T[4]} = {T[3]/max(T[4],1):.0%} | "
          f"matched labels: {matched}  (gate: 90% waistband / 80% shorts strict)")

if __name__ == "__main__":
    main(sys.argv[1])
