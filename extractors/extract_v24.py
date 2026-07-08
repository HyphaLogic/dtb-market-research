#!/usr/bin/env python3
"""v2.4 — Brock's reference-surface spec:
   Establish BACKGROUND + SKIN + FLOOR first, write all three out explicitly,
   then scan top-down: waistband first, work down until skin (legs) reappears."""
import numpy as np, colorsys, os, csv, glob, sys, json
from PIL import Image, ImageDraw
from sklearn.cluster import KMeans
REF = {"black":(12,12,14),"charcoal":(48,46,50),"white":(238,236,230),"gray":(130,130,132),
"navy":(22,32,72),"royal blue":(38,78,196),"light blue":(140,190,235),"teal":(0,138,138),
"green":(40,140,60),"lime":(160,220,50),"yellow":(230,205,40),"gold":(198,158,42),
"orange":(240,125,30),"coral":(248,105,88),"red":(198,32,36),"maroon":(112,24,44),
"pink":(240,105,180),"magenta":(198,32,140),"purple":(118,58,178),"lavender":(178,158,218),
"tan/bone":(210,190,160),"brown":(108,74,46)}
def nearest(rgb): return min(REF, key=lambda k: sum((int(a)-int(b))**2 for a,b in zip(REF[k],rgb)))
def dist(a,b): return np.sqrt(np.sum((np.asarray(a,float)-np.asarray(b,float))**2,axis=-1))
def show_of(fn): return fn.split("_")[0]

def build_models():
    bg, fl = {}, {}
    by = {}
    for f in glob.glob("top5_photos/*.jpg"):
        by.setdefault(show_of(os.path.basename(f)), []).append(f)
    for show, files in by.items():
        e, g = [], []
        for f in files[::2]:
            A = np.array(Image.open(f).convert("RGB").resize((150,225)))
            h,w = A.shape[:2]
            e += [A[int(h*.10):int(h*.72), :int(w*.08)].reshape(-1,3),
                  A[int(h*.10):int(h*.72), int(w*.92):].reshape(-1,3), A[:int(h*.08),:].reshape(-1,3)]
            g += [A[int(h*.90):, :].reshape(-1,3)]                     # FLOOR strip
        bg[show] = KMeans(n_clusters=5, n_init=3, random_state=0).fit(np.vstack(e)[::7]).cluster_centers_
        fl[show] = KMeans(n_clusters=3, n_init=3, random_state=0).fit(np.vstack(g)[::5]).cluster_centers_
    return bg, fl

def analyze(path, BG, FL):
    im = Image.open(path).convert("RGB"); w,h = im.size
    A = np.array(im).astype(np.int16)
    show = show_of(os.path.basename(path))
    bgcs, flcs = np.array(BG[show]), np.array(FL[show])
    bthr = np.where(bgcs.mean(axis=1)<60, 26.0, 52.0)
    fthr = np.where(flcs.mean(axis=1)<60, 26.0, 48.0)
    def ref_mask(px):
        Db = np.stack([dist(px,c) for c in bgcs]); Df = np.stack([dist(px,c) for c in flcs])
        return np.any(Db<bthr[:,None],axis=0) | np.any(Df<fthr[:,None],axis=0)
    def warm(px): return (px[:,0]>px[:,1]) & (px[:,1]>=px[:,2]-10) & (px[:,0]>70)
    skin=None
    for (ya,yb,xa,xb) in [(.20,.34,.38,.62),(.16,.28,.35,.65),(.24,.42,.30,.70)]:
        t = A[int(h*ya):int(h*yb), int(w*xa):int(w*xb)].reshape(-1,3)
        t = t[~ref_mask(t)]; t = t[warm(t)]
        if len(t)>80:
            skin = np.median(t,axis=0); break
    if skin is None:
        t = A[int(h*.20):int(h*.34), int(w*.38):int(w*.62)].reshape(-1,3)
        skin = np.median(t,axis=0)
    sk_h, sk_s, sk_v = colorsys.rgb_to_hsv(*(np.clip(skin,0,255)/255))
    def skin_mask(px):
        hsv = np.array([colorsys.rgb_to_hsv(*(np.clip(p,0,255)/255.0)) for p in px]) if len(px) else np.zeros((0,3))
        if not len(px): return np.zeros(0,bool)
        dh = np.minimum(np.abs(hsv[:,0]-sk_h),1-np.abs(hsv[:,0]-sk_h))
        core = (dh<0.06)&(np.abs(hsv[:,2]-sk_v)<0.26)&(np.abs(hsv[:,1]-sk_s)<0.30)
        shadow = (dh<0.07)&(hsv[:,2]>0.22*sk_v)&(hsv[:,2]<0.95*sk_v)&(hsv[:,1]>sk_s*0.5)
        return core|shadow
    # TOP-DOWN scan (Brock's spec): find waistband = first garment band below torso; hem = skin resumes
    band_top = hem = None; state = "skin"
    for yy in np.arange(0.34, 0.80, 0.008):
        strip = A[int(h*yy):int(h*(yy+0.010)), int(w*.36):int(w*.64)].reshape(-1,3)
        strip = strip[~ref_mask(strip)]
        if len(strip) < 25: continue
        sfrac = skin_mask(strip).mean()
        if state=="skin" and sfrac < 0.40: band_top = yy; state="garment"
        elif state=="garment" and sfrac > 0.62 and yy > (band_top or 0)+0.10: hem = yy; break
    res = {"file":os.path.basename(path),
        "background_colors":" / ".join(dict.fromkeys(nearest(c) for c in bgcs)),
        "skin_color": f"{nearest(skin)} rgb{tuple(int(x) for x in skin)}",
        "floor_colors":" / ".join(dict.fromkeys(nearest(c) for c in flcs)),
        "waistband":"UNREADABLE","wb_confidence":0,"shorts":[],"sh_confidence":0,
        "hem_y_pct": round(hem*100,1) if hem else "", "skin_rgb":[int(x) for x in skin]}
    if band_top:
        wb = A[int(h*band_top):int(h*(band_top+0.028)), int(w*.34):int(w*.66)].reshape(-1,3)
        wbk = wb[(~ref_mask(wb)) & (~skin_mask(wb)) & ~np.all(wb>195,axis=1)]  # drop disc whites
        if len(wbk)>40:
            res["waistband"] = nearest(np.median(wbk,axis=0))
            res["wb_confidence"] = min(90,int(30+55*len(wbk)/len(wb)))
        y0 = band_top+0.03; y1 = min(hem if hem else band_top+0.26, band_top+0.30)
        sh = A[int(h*y0):int(h*y1), int(w*.24):int(w*.76)].reshape(-1,3)
        keep = sh[(~ref_mask(sh)) & (~skin_mask(sh))]
        if len(keep)>=150:
            km = KMeans(n_clusters=4,n_init=4,random_state=0).fit(keep)
            cc = np.bincount(km.labels_,minlength=4)
            for i in np.argsort(-cc):
                s = cc[i]/cc.sum()
                if s>=0.10: res["shorts"].append((nearest(km.cluster_centers_[i]),round(float(s),2),[int(x) for x in km.cluster_centers_[i]]))
            res["sh_confidence"] = min(90,int(25+55*len(keep)/len(sh)+10*len(res["shorts"])))
    return res, im

if __name__=="__main__":
    BG, FL = build_models()
    out=[]
    for name in open(sys.argv[1]).read().split():
        r,_ = analyze("top5_photos/"+name, BG, FL)
        out.append(r)
        print(r["file"],"| bg:",r["background_colors"],"| skin:",r["skin_color"],"| floor:",r["floor_colors"],
              "| wb:",f"{r['waistband']}({r['wb_confidence']}%)","| shorts:"," + ".join(f"{c}({s})" for c,s,_ in r["shorts"]),
              "| hem_y:",r["hem_y_pct"])
