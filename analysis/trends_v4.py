#!/usr/bin/env python3
"""Trend analysis over the full v4 read of all 288 first-callout MP athletes.
Aggregates: shorts color frequency (weighted by coverage AND as presence),
waistband color, Frame/Base/Accent archetype distribution, color pairings, and
per-show/per-class breakdowns. Writes analysis/v4_trends.csv (long-form) and
prints a readable report.

Usage: python analysis/trends_v4.py <v4_output.csv>"""
import csv, os, re, sys
from collections import Counter, defaultdict

def parse_shorts(s):
    out = []
    for seg in (s or "").split("+"):
        m = re.match(r"\s*(.+?)\((0?\.\d+|1\.0+)\)", seg)
        if m: out.append((m.group(1).strip(), float(m.group(2))))
    return out

def arch_parts(a):
    p = [x.strip() for x in (a or "").split("+")]
    return (p + ["", "", ""])[:3]

here = os.path.dirname(__file__)
rows = list(csv.DictReader(open(sys.argv[1])))
mani = {r["photo_file"]: r for r in csv.DictReader(open(os.path.join(here, "..", "data", "photo_manifest.csv")))}
rows = [r for r in rows if not (r.get("notes") or "").startswith(("error", "refusal"))]
N = len(rows)

wb = Counter()
sh_presence = Counter()      # short counts as 1 for each color present
sh_weighted = Counter()      # sum of coverage across athletes
frame = Counter(); base = Counter(); accent = Counter()
pairs = Counter()            # unordered color pair co-occurrence in a single short
by_show_base = defaultdict(Counter)
n_colors = Counter()

for r in rows:
    wb[(r.get("waistband") or "?").strip()] += 1
    colors = parse_shorts(r.get("shorts_colors", ""))
    n_colors[len(colors)] += 1
    cset = [c for c, _ in colors]
    for c, cov in colors:
        sh_presence[c] += 1
        sh_weighted[c] += cov
    for i in range(len(cset)):
        for j in range(i+1, len(cset)):
            pairs[tuple(sorted((cset[i], cset[j])))] += 1
    f, b, a = arch_parts(r.get("archetype", ""))
    frame[f] += 1; base[b] += 1; accent[a] += 1
    show = mani.get(r["photo_file"], {}).get("show", "?")
    by_show_base[show][b] += 1

def pct(n): return f"{100*n/N:.0f}%"
def top(counter, k=12): return counter.most_common(k)

print(f"=== DTB Trend Analysis — v4 read of {N} first-callout MP athletes ===\n")
print("SHORTS COLOR — presence (share of athletes whose shorts include this color):")
for c, n in top(sh_presence): print(f"  {c:12} {n:3}  {pct(n)}")
print("\nSHORTS COLOR — coverage-weighted (total design real estate):")
tot = sum(sh_weighted.values()) or 1
for c, v in sh_weighted.most_common(12): print(f"  {c:12} {v:6.1f}  {100*v/tot:.0f}% of all short area")
print("\nWAISTBAND COLOR:")
for c, n in top(wb): print(f"  {c:12} {n:3}  {pct(n)}")
print("\nARCHETYPE — BASE (main treatment):")
for c, n in base.most_common(): print(f"  {c:16} {n:3}  {pct(n)}")
print("\nARCHETYPE — FRAME:")
for c, n in frame.most_common(): print(f"  {c:16} {n:3}  {pct(n)}")
print("\nARCHETYPE — ACCENT:")
for c, n in accent.most_common(): print(f"  {c:18} {n:3}  {pct(n)}")
print("\nDESIGN COMPLEXITY (# distinct colors in the shorts):")
for k in sorted(n_colors): print(f"  {k} color(s): {n_colors[k]:3}  {pct(n_colors[k])}")
print("\nTOP COLOR PAIRINGS (co-occur in the same short):")
for (a, b), n in pairs.most_common(12): print(f"  {a} + {b:12} {n:3}")

# long-form CSV for downstream use
with open(os.path.join(here, "v4_trends.csv"), "w", newline="") as f:
    w = csv.writer(f); w.writerow(["dimension", "value", "count", "pct_of_athletes"])
    for c, n in sh_presence.most_common(): w.writerow(["shorts_color_presence", c, n, round(100*n/N)])
    for c, n in wb.most_common(): w.writerow(["waistband", c, n, round(100*n/N)])
    for c, n in base.most_common(): w.writerow(["base", c, n, round(100*n/N)])
    for c, n in frame.most_common(): w.writerow(["frame", c, n, round(100*n/N)])
    for c, n in accent.most_common(): w.writerow(["accent", c, n, round(100*n/N)])
    for (a, b), n in pairs.most_common(30): w.writerow(["color_pair", f"{a}+{b}", n, round(100*n/N)])
print(f"\nwrote analysis/v4_trends.csv")
