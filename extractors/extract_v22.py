#!/usr/bin/env python3
"""v2.2 — per-SHOW background model (Brock's proposal), structural waistband
detection, shadow-aware skin mask, per-field confidence percentages."""
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

def build_show_bg_models():
    """Pool edge strips across every photo of a show -> 5-cluster backdrop palette."""
    models = {}
    by_show = {}
    for f in glob.glob("top5_photos/*.jpg"):
        by_show.setdefault(show_of(os.path.basename(f)), []).append(f)
    for show, files in by_show.items():
        samples = []
        for f in files[::2]:  # every other photo is plenty
            A = np.array(Image.open(f).convert("RGB").resize((150,225)))
            h,w = A.shape[:2]
            samples.append(A[int(h*.10):int(h*.80), :int(w*.08)].reshape(-1,3))
            samples.append(A[int(h*.10):int(h*.80), int(w*.92):].reshape(-1,3))
            samples.append(A[:int(h*.10), :].reshape(-1,3))  # top strip = pure backdrop
        S = np.vstack(samples)
        km = KMeans(n_clusters=5, n_init=4, random_state=0).fit(S[::7])
        models[show] = km.cluster_centers_
    return models

def analyze(path, bgm):
    im = Image.open(path).convert("RGB"); w,h = im.size
    A = np.array(im)
    show = show_of(os.path.basename(path))
    bgcs = bgm[show]
    def bg_mask(px): return np.min(np.stack([dist(px,c) for c in bgcs]),axis=0) < 52
    # skin from torso, shadow-aware
    torso = A[int(h*.20):int(h*.34), int(w*.38):int(w*.62)].reshape(-1,3)
    t2 = torso[~bg_mask(torso)]; skin = np.median(t2 if len(t2)>50 else torso, axis=0)
    sk_h, sk_s, sk_v = colorsys.rgb_to_hsv(*(skin/255))
    def skin_mask(px):
        hsv = np.array([colorsys.rgb_to_hsv(*(p/255.0)) for p in px])
        dh = np.minimum(np.abs(hsv[:,0]-sk_h), 1-np.abs(hsv[:,0]-sk_h))
        core = (dh<0.05) & (np.abs(hsv[:,2]-sk_v)<0.24) & (np.abs(hsv[:,1]-sk_s)<0.28)
        shadow = (dh<0.06) & (hsv[:,2] > 0.25*sk_v) & (hsv[:,2] < 0.95*sk_v) & (hsv[:,1] > sk_s*0.6)
        return core | shadow
    # structural waistband: scan rows for skin->garment transition
    band_top = None
    for yy in np.arange(0.36, 0.55, 0.01):
        strip = A[int(h*yy):int(h*(yy+0.012)), int(w*.38):int(w*.62)].reshape(-1,3)
        strip = strip[~bg_mask(strip)]
        if len(strip) < 30: continue
        if skin_mask(strip).mean() < 0.35:
            band_top = yy; break
    wb_conf = 0
    wband = None
    if band_top:
        wb = A[int(h*band_top):int(h*(band_top+0.03)), int(w*.36):int(w*.64)].reshape(-1,3)
        wbk = wb[(~bg_mask(wb)) & (~skin_mask(wb))]
        if len(wbk) > 40:
            wband = np.median(wbk, axis=0); wb_conf = min(95, int(40 + 55*len(wbk)/len(wb)))
    # shorts: from waistband down
    y0 = (band_top + 0.03) if band_top else 0.47
    sh = A[int(h*y0):int(h*(y0+0.24)), int(w*.24):int(w*.76)].reshape(-1,3)
    m = (~bg_mask(sh)) & (~skin_mask(sh))
    keep = sh[m]
    res = {"file":os.path.basename(path), "bg_swatches":[nearest(c) for c in bgcs[:3]],
           "bg_rgb":[int(x) for x in bgcs[0]], "skin_rgb":[int(x) for x in skin],
           "waistband": nearest(wband) if wband is not None else "UNREADABLE",
           "wb_confidence": wb_conf, "shorts":[], "sh_confidence": 0}
    if len(keep) >= 150:
        km = KMeans(n_clusters=4, n_init=4, random_state=0).fit(keep)
        cc = np.bincount(km.labels_, minlength=4)
        for i in np.argsort(-cc):
            s = cc[i]/cc.sum()
            if s >= 0.12:
                res["shorts"].append((nearest(km.cluster_centers_[i]), round(float(s),2), [int(x) for x in km.cluster_centers_[i]]))
        margin = (max(cc)-sorted(cc)[-2])/cc.sum() if len(cc)>1 else 0
        res["sh_confidence"] = min(95, int(30 + 40*keep.shape[0]/sh.shape[0] + 60*m.mean()*0.5 + 20*margin))
    # archetype heuristic from cluster structure
    arch, aconf = "UNKNOWN", 20
    if res["shorts"]:
        top = res["shorts"][0]
        if top[1] >= 0.72: arch, aconf = "Solid + Trim", 55
        elif len(res["shorts"])>=2 and res["shorts"][0][1]<0.55 and res["shorts"][1][1]>0.25: arch, aconf = "Color-Block Panels", 40
        if top[0] in ("black","charcoal") and len(res["shorts"])>=2 and res["shorts"][1][0] in ("coral","red","orange","royal blue","light blue","green","lime","yellow","gold","white"):
            arch, aconf = "Energy/Element or Frame+Pattern over black", 35
    res["archetype_guess"], res["arch_confidence"] = arch, aconf
    return res, im

if __name__ == "__main__":
    bgm = build_show_bg_models()
    json.dump({k:[[int(x) for x in c] for c in v] for k,v in bgm.items()}, open("show_bg_models.json","w"))
    os.makedirs("review_v22", exist_ok=True)
    out=[]
    for name in open(sys.argv[1]).read().split():
        res, im = analyze("top5_photos/"+name, bgm)
        w,h = im.size
        crop = im.crop((int(w*.12), int(h*.10), int(w*.88), int(h*.82))).resize((300,320))
        canvas = Image.new("RGB",(300,410),(24,24,26)); canvas.paste(crop,(0,0))
        d = ImageDraw.Draw(canvas); x=4; y=326
        for rgb,label in [(res["bg_rgb"],"bg"),(res["skin_rgb"],"skin")]+[(rgb,f"{int(s*100)}%") for _,s,rgb in res["shorts"][:3]]:
            d.rectangle([x,y,x+52,y+30],fill=tuple(rgb)); d.text((x,y+33),label,fill=(235,235,235)); x+=58
        d.text((4,384), f"wb:{res['waistband']}({res['wb_confidence']}%) "+"+".join(c for c,_,_ in res["shorts"][:2])+f" ({res['sh_confidence']}%)", fill=(245,245,245))
        canvas.save("review_v22/"+name, quality=90)
        out.append({"photo_file":name,
            "v22_show_backdrop_palette":" / ".join(res["bg_swatches"]),
            "v22_waistband":res["waistband"],"v22_waistband_confidence_pct":res["wb_confidence"],
            "v22_shorts_colors":" + ".join(f"{c}({s})" for c,s,_ in res["shorts"]) or "UNREADABLE",
            "v22_shorts_confidence_pct":res["sh_confidence"],
            "v22_archetype_guess":res["archetype_guess"],"v22_archetype_confidence_pct":res["arch_confidence"],
            "brock_waistband":"","brock_shorts":"","brock_archetype":"","brock_brand":"","brock_notes":""})
    with open("review_sample_v22.csv","w",newline="") as f:
        wr=csv.DictWriter(f,fieldnames=list(out[0].keys())); wr.writeheader(); wr.writerows(out)
    print("v2.2 analyzed", len(out))
