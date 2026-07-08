#!/usr/bin/env python3
import re, sys, subprocess
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
def get(url, out=None):
    cmd = ["curl","-sL","--compressed","-A",UA,url]
    if out: cmd += ["-o",out]
    r = subprocess.run(cmd, capture_output=True)
    return r.stdout.decode(errors="ignore") if not out else None

def main(url, prefix):
    h = get(url)
    pat = re.compile(r"MEN(?:'|&#039;)S PHYSIQUE(.*?)(?:MEN(?:'|&#039;)S CLASSIC|WOMEN(?:'|&#039;)S|FITNESS|FIGURE|BIKINI|FIT MODEL)", re.S)
    matches = list(pat.finditer(h))
    if not matches: print("NO MP"); return
    wpat = r'class ([a-z])</div>\s*<a[^>]*href="(https://[^"]+)"[^>]*>\s*<span>\s*1\s*</span>\s*([^<]+)</a>'
    winners = max((re.findall(wpat, m.group(1)) for m in matches), key=len)
    print(f"{len(winners)} class winners")
    for cls, curl_, name in winners:
        page = get(curl_)
        ids = sorted(set(int(i) for i in re.findall(r'thumb/(\d+)\.jpg', page)))
        cdir = re.search(r'images/contests/(\d+)', page)
        if not ids or not cdir: print(f"  {cls}: {name.strip()} NO PHOTOS"); continue
        fn = f"{prefix}_{cls.upper()}_{name.strip().replace(' ','_')}_{ids[0]}.jpg"
        get(f"https://contests.npcnewsonline.com/images/contests/{cdir.group(1)}/large/{ids[0]}.jpg", out=fn)
        print(f"  {cls.upper()}: {name.strip()} photos={len(ids)}")
if __name__ == "__main__": main(sys.argv[1], sys.argv[2])
