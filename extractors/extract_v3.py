#!/usr/bin/env python3
"""v3 - U2-Net person segmentation + GEOMETRIC garment region.
Person silhouette via rembg; garment located by position within the silhouette
(waist = first non-skin band below torso, hem = skin resumes), so prints whose
hue matches skin (the Keyon Harry case) are separated spatially, not by color.
Probe-validated 2026-07-08 (Edwards green-gradient exact match); NOT yet
benchmarked on the full label set. Requires: pip install rembg onnxruntime scikit-learn"""
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
        hsv = np.array([colorsys.rgb_to_hsv(*(p/255.0)) for p in px])
        dh = np.minimum(np.abs(hsv[:,0]-sk_h), 1-np.abs(hsv[:,0]-sk_h))
        return (dh<0.06) & (np.abs(hsv[:,2]-sk_v)<0.30)
    waist = hem = None
    step = max(2,(bot-top)//140)
    for yy in range(top+int((bot-top)*0.30), bot, step):
        sel = ys==yy
        if sel.sum() < 8: continue
        frac = skinlike(A[ys[sel], xs[sel]]).mean()
        if waist is None and frac < 0.45: waist = yy
        elif waist and frac > 0.65 and yy > waist + (bot-top)*0.08: hem = yy; break
    if waist is None: return None
    gsel = (ys >= waist) & (ys <= (hem or waist + int((bot-top)*0.30)))
    gpx = A[ys[gsel], xs[gsel]]; gpx = gpx[~np.all(gpx>200, axis=1)]
    wb_sel = (ys >= waist) & (ys <= waist + int((bot-top)*0.035))
    wpx = A[ys[wb_sel], xs[wb_sel]]; wpx = wpx[~np.all(wpx>200,axis=1)]
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
