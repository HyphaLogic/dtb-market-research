#!/usr/bin/env python3
"""Validate division assignment: slice contest page by division headers,
extract class winners per division, print MP list definitively."""
import re, subprocess, sys
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
def get(url):
    return subprocess.run(["curl","-sL","--compressed","-A",UA,url],
        capture_output=True).stdout.decode(errors="ignore")

HDRS = ["MEN&#039;S PHYSIQUE","MEN&#039;S CLASSIC PHYSIQUE","MEN&#039;S BODYBUILDING",
        "WOMEN&#039;S PHYSIQUE","WOMEN&#039;S BODYBUILDING","BIKINI","FIGURE","FITNESS",
        "WELLNESS","FIT MODEL"]
WPAT = re.compile(r'class ([a-z])</div>\s*<a[^>]*href="(https://[^"]+)"[^>]*>\s*<span>\s*1\s*</span>\s*([^<]+)</a>')

def divisions(html):
    # find ALL header occurrences with positions; keep those followed by winner markup before next header
    marks = sorted([(m.start(), h) for h in HDRS for m in re.finditer(re.escape(h), html)])
    out = {}
    for i,(pos,h) in enumerate(marks):
        end = marks[i+1][0] if i+1 < len(marks) else len(html)
        winners = WPAT.findall(html[pos:end])
        if winners:
            out.setdefault(h, []).extend(winners)
    return out

for url in sys.argv[1:]:
    print("="*10, url.split("/contests/")[1])
    d = divisions(get(url))
    for h, w in d.items():
        tag = "MP" if h=="MEN&#039;S PHYSIQUE" else ("MCP" if "CLASSIC" in h else h[:12])
        if tag in ("MP","MCP"):
            print(f" {tag}: " + ", ".join(f"{c.upper()}:{n.strip()}" for c,_,n in w))
