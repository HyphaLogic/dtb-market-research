#!/usr/bin/env python3
"""v2.3 — fixes from round-2 ground truth:
   (1) luminance-scaled bg threshold so spotlit BLACK shorts survive black-backdrop masking
   (2) competitor number-disc detection -> waistband anchor + disc pixel suppression
   (3) wider shadow-skin mask (brown/tan leak)"""
import numpy as np, colorsys, os, csv, glob, sys, json
from PIL import Image, ImageDraw
from sklearn.cluster import KMeans
REF = {"black":(12,12,14),"charcoal":(48,46,50),"white":(238,236,230),"gray":(130,130,132),
"navy":(22,32,72),"royal blue":(38,78,196),"light blue":(140,190,235),"teal":(0,138,138),
"green":(40,140,60),"lime":(160,220,50),"yellow":(230,205,40),"gold":(198,158,42),
"orange":(240,125,30),"coral":(248,105,88),"red":(198,32,36),"maroon":(112,24,44),
"pink":(240,105,180),"magenta":(198,32,140),"purple":(118,58,178),"lavender":(178,158,218),
"tan/bone":(210,190,160),"brown":(108,74,46)}
def nearest(rgb): return min(REF, key=lambda k: sum((int(a)-int(b))**2 for a,b in zip(REF[k], rgb)))
def dist(a,b): return np.sqrt(np.sum((np.asarray(a,float)-np.asarray(b,float))**2, axis=-1))
def show_of(fn): return fn.split("_")[0]

def analyze(path, bgm):
    im = Image.open(path).convert("RGB"); w,h = im.size
    A = np.array(im).astype(np.int16)
    bgcs = np.array(bgm[show_of(os.path.basename(path))])
    lum = bgcs.mean(axis=1)
    thr = np.where(lum < 60, 26.0, 52.0)          # tight radius for dark bg clusters
    def bg_mask(px):
        D = np.stack([dist(px,c) for c in bgcs])   # (k, n)
        return np.any(D < thr[:,None], axis=0)
    torso = A[int(h*.20):int(h*.34), int(w*.38):int(w*.62)].reshape(-1,3)
    t2 = torso[~bg_mask(torso)]; skin = np.median(t2 if len(t2)>50 else torso, axis=0)
    sk_h, sk_s, sk_v = colorsys.rgb_to_hsv(*(np.clip(skin,0,255)/255))
    def skin_mask(px):
        hsv = np.array([colorsys.rgb_to_hsv(*(np.clip(p,0,255)/255.0)) for p in px])
        dh = np.minimum(np.abs(hsv[:,0]-sk_h), 1-np.abs(hsv[:,0]-sk_h))
        core = (dh<0.06) & (np.abs(hsv[:,2]-sk_v)<0.26) & (np.abs(hsv[:,1]-sk_s)<0.30)
        shadow = (dh<0.07) & (hsv[:,2]>0.22*sk_v) & (hsv[:,2]<0.95*sk_v) & (hsv[:,1]>sk_s*0.5)
        return core | shadow
    # number-disc detection: brightest blob near waist center
    win = A[int(h*.38):int(h*.58), int(w*.30):int(w*.70)]
    bright = np.argwhere(np.all(win>195, axis=2))
    disc_y = disc_box = None; wb_src = "structural"
    if len(bright) > 120:
        cy, cx = bright.mean(axis=0)
        spread = bright.std(axis=0).mean()
        if spread < win.shape[0]*0.22:            # compact blob = disc
            disc_y = 0.38 + (cy/ h) * 1.0 * (win.shape[0]/win.shape[0]) * (0.58-0.38) if False else 0.38 + cy/h  # cy already in px of win
            disc_y = 0.38 + cy/ (h)               # win starts at .38h
            disc_box = (int(w*.30+cx-w*.055), int(h*disc_y-h*.028), int(w*.30+cx+w*.055), int(h*disc_y+h*.028))
            wb_src = "disc-anchored"
    def not_disc(px_idx_shape, y0f, x0f):
        return None
    # waistband sample
    wb_conf = 0; wband = None
    band_y = disc_y if disc_y else None
    if band_y is None:
        for yy in np.arange(0.36, 0.55, 0.01):
            strip = A[int(h*yy):int(h*(yy+0.012)), int(w*.38):int(w*.62)].reshape(-1,3)
            strip = strip[~bg_mask(strip)]
            if len(strip)>=30 and skin_mask(strip).mean() < 0.35: band_y = yy+0.01; break
    if band_y:
        y0,y1 = int(h*(band_y-0.012)), int(h*(band_y+0.022))
        seg = A[y0:y1, int(w*.30):int(w*.70)]
        px = seg.reshape(-1,3)
        keepm = (~bg_mask(px)) & (~skin_mask(px))
        if disc_box:
            xs = np.tile(np.arange(int(w*.30),int(w*.70)), seg.shape[0])
            ys = np.repeat(np.arange(y0,y1), seg.shape[1])
            keepm &= ~((xs>=disc_box[0])&(xs<=disc_box[2])&(ys>=disc_box[1])&(ys<=disc_box[3]))
            px2 = px[keepm & ~np.all(px>190,axis=1)]   # also drop residual disc whites
        else:
            px2 = px[keepm]
        if len(px2) > 40:
            wband = np.median(px2, axis=0)
            wb_conf = min(92, int(35 + 40*len(px2)/len(px) + (15 if wb_src=="disc-anchored" else 0)))
    y0f = (band_y + 0.025) if band_y else 0.47
    sh_seg = A[int(h*y0f):int(h*(y0f+0.24)), int(w*.24):int(w*.76)]
    px = sh_seg.reshape(-1,3)
    keepm = (~bg_mask(px)) & (~skin_mask(px))
    if disc_box:
        xs = np.tile(np.arange(int(w*.24),int(w*.76)), sh_seg.shape[0])
        ys = np.repeat(np.arange(int(h*y0f),int(h*y0f)+sh_seg.shape[0]), sh_seg.shape[1])
        keepm &= ~((xs>=disc_box[0])&(xs<=disc_box[2])&(ys>=disc_box[1])&(ys<=disc_box[3]))
    keep = px[keepm]
    res = {"file":os.path.basename(path),"skin_rgb":[int(x) for x in skin],
           "waistband":nearest(wband) if wband is not None else "UNREADABLE",
           "wb_confidence":wb_conf,"wb_source":wb_src,"shorts":[],"sh_confidence":0}
    if len(keep)>=150:
        km = KMeans(n_clusters=4, n_init=4, random_state=0).fit(keep)
        cc = np.bincount(km.labels_, minlength=4)
        for i in np.argsort(-cc):
            s = cc[i]/cc.sum()
            if s>=0.10: res["shorts"].append((nearest(km.cluster_centers_[i]), round(float(s),2), [int(x) for x in km.cluster_centers_[i]]))
        res["sh_confidence"] = min(92, int(28 + 55*keepm.mean() + 12*len(res["shorts"])))
    return res, im
if __name__ == "__main__":
    bgm = json.load(open("show_bg_models.json"))
    out=[]
    for name in open(sys.argv[1]).read().split():
        res,_ = analyze("top5_photos/"+name, bgm)
        out.append(res)
    for r in out:
        print(r["file"], "| wb:", r["waistband"], f"({r['wb_confidence']}%,{r['wb_source']})", "|", " + ".join(f"{c}({s})" for c,s,_ in r["shorts"]))
