#!/usr/bin/env python3
"""Collect: (1) winner URLs per show/class, (2) comparison lineup photos for every MP class, all shows."""
import re, subprocess, os, csv
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
def get(url, out=None):
    cmd = ["curl","-sL","--compressed","-A",UA,url]
    if out: cmd += ["-o",out]
    r = subprocess.run(cmd, capture_output=True)
    return r.stdout.decode(errors="ignore") if not out else None

SHOWS = {
 "2026 NPC Junior Nationals": "https://contests.npcnewsonline.com/contests/2026/npc_junior_nationals",
 "2026 NPC Junior USA": "https://contests.npcnewsonline.com/contests/2026/npc_junior_usa",
 "2025 NPC Nationals": "https://contests.npcnewsonline.com/contests/2025/npc_national_championships",
 "2025 NPC North American": "https://contests.npcnewsonline.com/contests/2025/npc_north_american_championships",
 "2025 NPC USA Championships": "https://contests.npcnewsonline.com/contests/2025/npc_usa_championships",
 "2025 NPC Universe": "https://contests.npcnewsonline.com/contests/2025/npc_universe",
}
WPAT = re.compile(r'class ([a-z])</div>\s*<a[^>]*href="(https://[^"]+)"[^>]*>\s*<span>\s*1\s*</span>\s*([^<]+)</a>')
os.makedirs("comparisons", exist_ok=True)
urls_rows, cmp_rows = [], []
for show, url in SHOWS.items():
    h = get(url)
    # winner URLs: pick largest block of class-winner matches that excludes women's bleed
    # slice strictly between MEN'S PHYSIQUE header and MEN'S CLASSIC / WOMEN'S headers with negative lookbehind for WO
    mp = None
    for m in re.finditer(r"(?<!WO)MEN&#039;S PHYSIQUE", h):
        end = len(h)
        nxt = re.search(r"MEN&#039;S CLASSIC|WOMEN&#039;S|FITNESS|FIGURE|BIKINI|FIT MODEL|WELLNESS", h[m.end():])
        if nxt: end = m.end() + nxt.start()
        found = WPAT.findall(h[m.end():end])
        if found and (mp is None or len(found) > len(mp)): mp = found
    for cls, wurl, name in (mp or []):
        urls_rows.append({"show":show,"class":cls.upper(),"competitor":name.strip(),"gallery_url":wurl})
    # comparison galleries
    comps = sorted(set(re.findall(r'href="(https://[^"]+comparisons?-mp?hysique-class-([a-z])[^"]*)"', h)))
    for curl_, cls in comps:
        page = get(curl_)
        thumbs = sorted(set(re.findall(r'https://[^"]+/thumb/\d+\.jpg', page)))[:2]
        for t in thumbs:
            large = t.replace("/thumb/","/large/")
            fn = f"comparisons/{show.replace(' ','_')}_class{cls.upper()}_{os.path.basename(t)}"
            get(large, out=fn)
            cmp_rows.append({"show":show,"class":cls.upper(),"lineup_photo":os.path.basename(fn),"source_gallery":curl_})
with open("winner_urls.csv","w",newline="") as f:
    w = csv.DictWriter(f, fieldnames=["show","class","competitor","gallery_url"]); w.writeheader(); w.writerows(urls_rows)
with open("comparisons_index.csv","w",newline="") as f:
    w = csv.DictWriter(f, fieldnames=["show","class","lineup_photo","source_gallery"]); w.writeheader(); w.writerows(cmp_rows)
print("winner urls:", len(urls_rows), "| comparison photos:", len(cmp_rows))
from collections import Counter
print(Counter(r["show"] for r in cmp_rows))
