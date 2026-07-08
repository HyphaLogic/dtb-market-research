#!/usr/bin/env python3
"""Collect top-5 (first callouts) for every MP class, all 2025-2026 national shows.
Outputs: all_athletes.csv + downloads 1 front photo per athlete."""
import re, subprocess, os, csv, time
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
def get(url, out=None):
    cmd = ["curl","-sL","--compressed","-A",UA,url]
    if out: cmd += ["-o",out]
    r = subprocess.run(cmd, capture_output=True)
    return r.stdout.decode(errors="ignore") if not out else None

SHOWS = {
 "2026 NPC Junior Nationals": ("jrnats26","https://contests.npcnewsonline.com/contests/2026/npc_junior_nationals"),
 "2026 NPC Junior USA": ("jrusa26","https://contests.npcnewsonline.com/contests/2026/npc_junior_usa"),
 "2025 NPC Nationals": ("nats25","https://contests.npcnewsonline.com/contests/2025/npc_national_championships"),
 "2025 NPC North American": ("noram25","https://contests.npcnewsonline.com/contests/2025/npc_north_american_championships"),
 "2025 NPC USA Championships": ("usa25","https://contests.npcnewsonline.com/contests/2025/npc_usa_championships"),
 "2025 NPC Universe": ("univ25","https://contests.npcnewsonline.com/contests/2025/npc_universe"),
 "2025 NPC Teen Collegiate Masters": ("tcm25","https://contests.npcnewsonline.com/contests/2025/npc_teen_collegiate_masters_nationals"),
 "2025 NPC Junior Nationals": ("jrnats25","https://contests.npcnewsonline.com/contests/2025/npc_junior_nationals"),
 "2025 NPC Junior USA": ("jrusa25","https://contests.npcnewsonline.com/contests/2025/npc_junior_usa"),
}
APAT = re.compile(r'<a data-parent="class-([a-z])"[^>]*href="(https://[^"]+)"[^>]*>\s*<span>\s*(\d+)\s*</span>\s*([^<]+)</a>')
os.makedirs("top5_photos", exist_ok=True)
rows = []
for show,(pfx,url) in SHOWS.items():
    h = get(url)
    if not h or "PHYSIQUE" not in h.upper():
        print(f"SKIP {show} (no page)"); continue
    # take MP block: largest header slice not preceded by WO
    best = []
    for m in re.finditer(r"(?<!WO)MEN&#039;S PHYSIQUE", h):
        nxt = re.search(r"MEN&#039;S CLASSIC|WOMEN&#039;S|FITNESS|FIGURE|BIKINI|FIT MODEL|WELLNESS", h[m.end():])
        end = m.end()+nxt.start() if nxt else len(h)
        found = APAT.findall(h[m.end():end])
        if len(found) > len(best): best = found
    kept = [f for f in best if int(f[2]) <= 5]
    print(f"{show}: {len(kept)} top-5 athletes across {len(set(f[0] for f in kept))} classes")
    for cls, aurl, place, name in kept:
        rows.append({"show":show,"class":cls.upper(),"place":place,"competitor":name.strip(),
                     "gallery_url":aurl,"photo_file":"","division_check":"pending"})
# photo download pass
for r in rows:
    pfx = SHOWS[r["show"]][0]
    page = get(r["gallery_url"]); time.sleep(0.15)
    thumbs = sorted(set(re.findall(r'https://[^"]+/thumb/\d+\.jpg', page)))
    if not thumbs: continue
    t = thumbs[0]
    fn = f"top5_photos/{pfx}_{r['class']}_{r['place']}_{r['competitor'].replace(' ','_')}.jpg"
    get(t.replace("/thumb/","/large/"), out=fn)
    r["photo_file"] = os.path.basename(fn)
with open("all_athletes_top5.csv","w",newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
print("TOTAL rows:", len(rows), "| photos:", len(os.listdir("top5_photos")))
