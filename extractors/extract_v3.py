#!/usr/bin/env python3
"""v3 - U2-Net person segmentation + GEOMETRIC garment region.
Person silhouette via rembg; garment located by position within the silhouette
(waist = first non-skin band below torso, hem = skin resumes), so prints whose
hue matches skin (the Keyon Harry case) are separated spatially, not by color.
Benchmarked 2026-07-08 vs all 73 labels: 67% waistband, 42% strict / 82% loose shorts
(gate 90/80 not cleared; see README for what was tried). Waist anchor requires the
non-skin band to persist ~2-7% of body height below the hit (arms crossing the torso
in transition poses otherwise fake the waist). Requires: pip install "rembg[cpu]" scikit-learn"""
import numpy as np, colorsys, os, sys
from PIL import Image
from sklearn.cluster import KMeans
from rembg import remove, new_session
REF = {"black":(12,12,14),"charcoal":(48,46,50),"white":(238,236,230),"gray":(130,130,132),
"navy":(22,32,72),"royal blue":(38,78,196),"light blue":(140,190,235),"teal":(0,138,138),
"green":(40,140,60),"lime":(160,220,50),"yellow":(230,205,40),"gold":(198,158,42),
"orange":(240,125,30),"coral":(248,105,88),"red":(198,32,36),"maroon":(112,24,44),
"pink":(240,105,180),"magenta":(198,32,140),"purple":(118,58,178),"lavender":(178,158,218),
"tan/bone":(210,190,160),"brown":(108,74,46)}
def nearest(rgb): return min(REF, key=lambda k: sum((int(a)-int(b))**2 for a,b in zip(REF[k],rgb)))

def rgb2hsv_arr(px):
    p = np.asarray(px, dtype=np.float32)/255.0
    mx = p.max(1); mn = p.min(1); d = mx-mn
    dd = np.where(d==0, 1, d)
    r,g,b = p[:,0], p[:,1], p[:,2]
    h = np.where(mx==r, ((g-b)/dd)%6, np.where(mx==g, (b-r)/dd+2, (r-g)/dd+4))/6.0
    return np.where(d==0, 0, h), np.where(mx>0, d/np.where(mx==0,1,mx), 0), mx

def analyze(path, session):
    im = Image.open(path).convert("RGB"); A = np.array(im); h,w = A.shape[:2]
    M = np.array(remove(im, session=session, only_mask=True)) > 128
    ys,xs = np.where(M)
    if len(ys) < h*w*0.03: return None
    top, bot = ys.min(), ys.max()
    band = (ys > top+(bot-top)*0.12) & (ys < top+(bot-top)*0.30)
    skin = np.median(A[ys[band], xs[band]], axis=0)
    sk_h, sk_s, sk_v = colorsys.rgb_to_hsv(*(skin/255))
    def skinlike(px):
        if not len(px): return np.zeros(0, bool)
        hh, ss, vv = rgb2hsv_arr(px)
        dh = np.minimum(np.abs(hh-sk_h), 1-np.abs(hh-sk_h))
        # NB: no v2.3-style shadow term here — it eats black waistbands (dark px have unstable hue)
        return (dh<0.06) & (np.abs(vv-sk_v)<0.30)
    def row_skinfrac(yy):
        sel = ys==yy
        if sel.sum() < 8: return None
        return skinlike(A[ys[sel], xs[sel]]).mean()
    waist = hem = first_cand = None
    step = max(2,(bot-top)//140)
    for yy in range(top+int((bot-top)*0.30), bot, step):
        frac = row_skinfrac(yy)
        if frac is None: continue
        if waist is None and frac < 0.45:
            if first_cand is None: first_cand = yy
            # persistence: a real waistband has garment continuing below it; an arm or
            # hand crossing the torso (common transition poses) gives skin back within
            # a few % of body height and must not anchor the waist
            probe = [row_skinfrac(py) for py in range(yy+int((bot-top)*0.02), yy+int((bot-top)*0.07), step)]
            probe = [p for p in probe if p is not None]
            if probe and np.median(probe) < 0.50: waist = yy
        elif waist and frac > 0.65 and yy > waist + (bot-top)*0.08: hem = yy; break
    if waist is None: waist = first_cand   # nothing persistent found: fall back to first candidate
    if waist is None: return None
    hem_eff = hem or waist + int((bot-top)*0.30)
    gsel = (ys >= waist) & (ys <= hem_eff)
    gys, gxs = ys[gsel], xs[gsel]
    gall = A[gys, gxs]
    # number disc: suppress bright pixels only in the central waist zone, not globally
    # (global white-drop was erasing white shorts)
    cx = np.median(gxs); span = max(int(gxs.max())-int(gxs.min()), 1)
    disc_white = (np.abs(gxs-cx) < 0.20*span) & (gys <= waist + 0.6*(hem_eff-waist)) & np.all(gall>195, axis=1)
    keepm = ~disc_white & ~skinlike(gall)   # skin exclusion: waist row can be up to 45% skin
    gpx = gall[keepm]
    wpx = gall[keepm & (gys <= waist + int((bot-top)*0.035))]
    res = {"photo_file":os.path.basename(path), "skin":nearest(skin),
           "waistband": nearest(np.median(wpx,axis=0)) if len(wpx)>30 else "UNREADABLE",
           "hem_pct_of_body": round((hem-top)/(bot-top),3) if hem else "", "shorts_colors":""}
    if len(gpx) >= 200:
        km = KMeans(n_clusters=4, n_init=4, random_state=0).fit(gpx[::3])
        cc = np.bincount(km.labels_, minlength=4)
        parts = []
        for i in np.argsort(-cc):
            s = cc[i]/cc.sum()
            if s>=0.10: parts.append(f"{nearest(km.cluster_centers_[i])}({s:.2f})")
        res["shorts_colors"] = " + ".join(parts)
    return res

if __name__ == "__main__":
    import csv
    session = new_session("u2net")
    out=[]
    for name in open(sys.argv[1]).read().split():
        r = analyze("top5_photos/"+name, session)
        if r: out.append(r)
        print(r)
    if out:
        with open("v3_output.csv","w",newline="") as f:
            w=csv.DictWriter(f,fieldnames=list(out[0].keys())); w.writeheader(); w.writerows(out)
