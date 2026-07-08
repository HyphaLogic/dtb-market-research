#!/usr/bin/env python3
"""Rebuild top5_photos/ from photo_manifest.csv (photos NOT stored in repo - copyright)."""
import csv, os, re, subprocess, time
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
os.makedirs("top5_photos", exist_ok=True)
def get(url, out=None):
    cmd = ["curl","-sL","--compressed","-A",UA,url]
    if out: cmd += ["-o",out]
    r = subprocess.run(cmd, capture_output=True)
    return r.stdout.decode(errors="ignore") if not out else None
for r in csv.DictReader(open(os.path.join(os.path.dirname(__file__),"photo_manifest.csv"))):
    dest = "top5_photos/"+r["photo_file"]
    if not r["photo_file"] or os.path.exists(dest): continue
    page = get(r["gallery_url"]); time.sleep(0.15)
    thumbs = sorted(set(re.findall(r'https://[^"]+/thumb/\d+\.jpg', page)))
    if thumbs: get(thumbs[0].replace("/thumb/","/large/"), out=dest)
print("done")
