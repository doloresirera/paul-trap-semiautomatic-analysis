"""Reconstruction reproducible del análisis de micromoción.

Uso: python analisis.py
Genera resultados.csv, decisiones.csv y figuras/*.png.
"""
from pathlib import Path
import json, math
import cv2
import numpy as np
from scipy.optimize import least_squares
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path('drive-download-20260926T014040Z-1-001'); OUT=Path('resultados'); OUT.mkdir(exist_ok=True); (OUT/'figuras').mkdir(exist_ok=True)
THRESH=20                 # rojo > umbral, fijo en todos los videos/frames
STEP=30                   # separar cuadros para no contar la misma traza repetidamente
AREA=(18,2200); ELONG=2.0

def zhang_suen(im):
    a=(im>0).astype(np.uint8); changed=True
    while changed:
        changed=False
        for phase in (0,1):
            p=np.pad(a,1); P=[p[:-2,1:-1],p[:-2,2:],p[1:-1,2:],p[2:,2:],p[2:,1:-1],p[2:,:-2],p[1:-1,:-2],p[:-2,:-2]]
            B=sum(P); A=sum(((P[k]==0)&(P[(k+1)%8]==1)) for k in range(8))
            if phase==0: m=(a==1)&(B>=2)&(B<=6)&(A==1)&((P[0]*P[2]*P[4])==0)&((P[2]*P[4]*P[6])==0)
            else: m=(a==1)&(B>=2)&(B<=6)&(A==1)&((P[0]*P[2]*P[6])==0)&((P[0]*P[4]*P[6])==0)
            if np.any(m): a[m]=0; changed=True
    return a

def component_measure(mask, x0,y0):
    ys,xs=np.where(mask)
    if len(xs)<2:return None
    X=np.column_stack((xs,ys)).astype(float); cen=X.mean(0); cov=np.cov(X.T) if len(X)>2 else np.eye(2)
    ev=np.linalg.eigvalsh(cov); elong=math.sqrt(max(ev[1],1e-9)/max(ev[0],1e-9))
    sk=zhang_suen(mask.astype(np.uint8)); yy,xx=np.where(sk)
    if len(xx)<2:return None
    # Longitud de arco del esqueleto: suma de vecinos de 8-conectividad.
    s={(int(y),int(x)) for y,x in zip(yy,xx)}; length=0.
    for y,x in s:
        for dy,dx,w in ((0,1,1),(1,0,1),(1,1,2**.5),(1,-1,2**.5)):
            if (y+dy,x+dx) in s:length += w
    if length<=0:return None
    return cen+x0, length, elong

def extract(video):
    cap=cv2.VideoCapture(str(video)); n=int(cap.get(cv2.CAP_PROP_FRAME_COUNT)); pts=[]
    for k in range(0,n,STEP):
        cap.set(cv2.CAP_PROP_POS_FRAMES,k); ok,fr=cap.read()
        if not ok: continue
        red=fr[:,:,2]; bw=(red>THRESH).astype(np.uint8)
        # eliminar ruido aislado, sin unir trazas próximas
        bw=cv2.morphologyEx(bw,cv2.MORPH_OPEN,np.ones((3,3),np.uint8))
        num, lab, stats, cents=cv2.connectedComponentsWithStats(bw,8)
        for j in range(1,num):
            area=stats[j,cv2.CC_STAT_AREA]
            if not (AREA[0]<=area<=AREA[1]):continue
            x,y,w,h=stats[j,:4]; m=(lab[y:y+h,x:x+w]==j)
            if w*h>20000: continue
            q=component_measure(m,x,y)
            if q is None or q[2]<ELONG or q[1]<5:continue
            cen,L,elong=q; pts.append((cen[0],cen[1],L,k,area,elong))
    cap.release(); return np.array(pts,float)

def fit(d):
    xy=d[:,:2]; L=d[:,2]
    def fun(p): return L-p[0]*np.hypot(xy[:,0]-p[1],xy[:,1]-p[2])
    p0=[.5,xy[:,0].mean(),xy[:,1].mean()]
    r=least_squares(fun,p0,bounds=([0, -2000,-2000],[2,3000,3000]),loss='soft_l1',f_scale=3,max_nfev=3000)
    c,cx,cy=r.x; ci=L/np.hypot(xy[:,0]-cx,xy[:,1]-cy)
    return r.x,ci,r.fun

def bootstrap(d,seed=1234):
    rng=np.random.default_rng(seed); centers=[]; cs=[]; n=len(d)
    for _ in range(250):
        z=d[rng.integers(0,n,n)]
        p,_,_=fit(z); cs.append(p[0]); centers.append(p[1:])
    return np.asarray(cs),np.asarray(centers)

def figure(name,d,p,ci):
    xy=d[:,:2]; L=d[:,2]; c,cx,cy=p; R=np.hypot(xy[:,0]-cx,xy[:,1]-cy)
    fig,ax=plt.subplots(1,2,figsize=(10,4));
    ax[0].scatter(R,L,s=10,alpha=.65); xx=np.linspace(0,max(R)*1.05,100); ax[0].plot(xx,c*xx,'r-',label=f'L={c:.3f} R'); ax[0].set(xlabel='R [px]',ylabel='L [px]',title=name); ax[0].legend()
    ax[1].hist(ci,bins='auto',color='steelblue',alpha=.85); ax[1].axvline(c,color='r'); ax[1].set(xlabel='c_i=L_i/R_i',ylabel='cuentas',title=f'{len(ci)} trazas')
    fig.tight_layout(); fig.savefig(OUT/'figuras'/f'{name}.png',dpi=160); plt.close(fig)

def main():
    rows=[]; decisions=[]
    for video in sorted(ROOT.glob('*.mp4')):
        d=extract(video)
        if len(d)>=8:
            p,ci,res=fit(d); cs,cent=bootstrap(d)
            # Usable: >=20 trazas, centro estable (<10 px en cada coordenada), c within Mathieu stability.
            center_sd=np.std(cent,axis=0); usable=(len(d)>=20 and np.max(center_sd)<10 and 0<p[0]<.908)
            # incertidumbre total: bootstrap de c + threshold ±5 y error de extremos ±1 px.
            vals=[]
            for th in (THRESH-5,THRESH+5):
                old=globals()['THRESH']; globals()['THRESH']=th; dd=extract(video); globals()['THRESH']=old
                if len(dd)>=8: vals.append(fit(dd)[0][0])
            sig_boot=np.std(cs); sig_thr=np.std(vals) if len(vals)>1 else np.nan
            sig=np.sqrt(sig_boot**2+(0 if np.isnan(sig_thr) else sig_thr**2)+(.5/max(np.median(d[:,2]),1))**2)
            vac=1175.; f=50.; r0=.0089; omega=2*np.pi*f; qm=p[0]*r0*r0*omega*omega/(4*vac); sqm=qm*sig/p[0]
            name=video.stem; figure(name,d,p,ci)
            rows.append(dict(video=name,N=len(d),c=p[0],c_unc=sig,Q_m=qm,Q_m_unc=sqm,ci_sd=np.std(ci),cx=p[1],cy=p[2],cx_sd=center_sd[0],cy_sd=center_sd[1],usable=usable,threshold=THRESH))
            decisions.append(dict(video=name,usable=usable,reason=('ok' if usable else 'N<20, centro inestable o c fuera de rango'),N=len(d),center_sd_px=float(max(center_sd)),c=float(p[0])))
        else: decisions.append(dict(video=video.stem,usable=False,reason='menos de 8 trazas',N=len(d)))
    import csv
    for fn,rows0 in [('resultados.csv',rows),('decisiones.csv',decisions)]:
        if rows0:
            with open(OUT/fn,'w',newline='',encoding='utf8') as f:
                w=csv.DictWriter(f,fieldnames=rows0[0].keys()); w.writeheader(); w.writerows(rows0)
    (OUT/'parametros.json').write_text(json.dumps({'threshold_red':THRESH,'frame_step':STEP,'area_px':AREA,'elongation_min':ELONG,'V_AC_V':1175,'frequency_Hz':50,'r0_m':.0089},indent=2),encoding='utf8')
if __name__=='__main__': main()
