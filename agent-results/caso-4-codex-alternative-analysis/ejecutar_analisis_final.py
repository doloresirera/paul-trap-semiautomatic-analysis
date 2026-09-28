"""Reproduce el resultado alternativo usado en el informe comparativo."""

from pathlib import Path
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from analisis_alternativo import Config, extract_video, q_over_m


ROOT = Path(__file__).resolve().parent
VIDEOS = ROOT / "drive-download-20260926T014040Z-1-001"
OUT = ROOT / "resultado_final"

GROUPS = [
    {"group": "Grupo 1", "file": "WIN_20260624_15_07_04_Pro.mp4",
     "center": (281.4, 80.9), "center_sd": (5.8, 9.6), "original_c": 0.533,
     "original_c_error": 0.069, "original_qm": 8.7e-4, "original_qm_error": 1.0e-4},
    {"group": "Grupo 2", "file": "WIN_20260624_15_08_05_Pro.mp4",
     "center": (292.3, 71.2), "center_sd": (3.3, 9.9), "original_c": 0.524,
     "original_c_error": 0.060, "original_qm": 8.5e-4, "original_qm_error": 1.0e-4},
]


def select(data: pd.DataFrame, center: tuple[float, float]) -> pd.DataFrame:
    d = data.copy()
    d["radius_px"] = np.hypot(d.x_px-center[0], d.y_px-center[1])
    d["c_individual"] = d.length_px/d.radius_px
    relative_threshold_sensitivity = d.length_threshold_sd_px/d.length_px
    mask = ((d.c_individual > 0.10) & (d.c_individual < 0.908) &
            (d.radius_px > 35) & (relative_threshold_sensitivity < 0.30) &
            (d.mean_red > 48) & (d.area_px2 > 500) & (d.elongation > 6.0))
    return d.loc[mask].copy()


def threshold_cs(data: pd.DataFrame, center: tuple[float, float]) -> dict[str, float]:
    radius = np.hypot(data.x_px-center[0], data.y_px-center[1])
    ans = {}
    for col in sorted(c for c in data if c.startswith("length_t") and c[8:-3].isdigit()):
        vals = data[col]/radius
        vals = vals[np.isfinite(vals) & (vals > .1) & (vals < .908)]
        if len(vals): ans[col] = float(np.median(vals))
    return ans


def bootstrap(data: pd.DataFrame, group: dict, cfg: Config, n: int = 4000) -> np.ndarray:
    rng = np.random.default_rng(cfg.seed + (1 if group["group"].endswith("1") else 2))
    frames = data.frame.unique(); draws=[]
    x=data.x_px.to_numpy(); y=data.y_px.to_numpy(); L=data.length_px.to_numpy(); F=data.frame.to_numpy()
    for _ in range(n):
        chosen=rng.choice(frames,len(frames),replace=True)
        idx=np.concatenate([np.flatnonzero(F==f) for f in chosen])
        xc=rng.normal(group["center"][0],group["center_sd"][0])
        yc=rng.normal(group["center"][1],group["center_sd"][1])
        radius=np.hypot(x[idx]-xc,y[idx]-yc)
        draws.append(np.median(L[idx]/radius))
    return np.asarray(draws)


def group_figure(data: pd.DataFrame, group: dict, c: float, cdraw: np.ndarray, path: Path) -> None:
    fig,axes=plt.subplots(1,3,figsize=(14,4.1))
    ax=axes[0]; ax.scatter(data.x_px,data.y_px,c=data.c_individual,cmap="viridis",s=12,alpha=.55)
    ax.scatter(*group["center"],marker="x",s=100,c="red",lw=2); ax.invert_yaxis(); ax.set_aspect("equal")
    ax.set(xlabel="x [px]",ylabel="y [px]",title="Trazas automáticas aceptadas")
    ax=axes[1]; ax.scatter(data.radius_px,data.length_px,s=10,alpha=.4)
    rr=np.linspace(0,data.radius_px.max()*1.03,200); ax.plot(rr,c*rr,"k",lw=2)
    ax.set(xlabel="R [px]",ylabel="L área–perímetro [px]",title=f"mediana c = {c:.3f}")
    ax=axes[2]; ax.hist(data.c_individual,bins=20,alpha=.7,label="trazas"); ax.hist(cdraw,bins=30,density=True,alpha=.45,label="bootstrap")
    ax.axvline(c,c="k",lw=2); ax.set(xlabel="c",ylabel="frecuencia / densidad",title="Distribución y remuestreo"); ax.legend()
    fig.suptitle(group["group"]+" — "+group["file"]); fig.tight_layout(); fig.savefig(path,dpi=190); plt.close(fig)


def main() -> None:
    OUT.mkdir(exist_ok=True)
    cfg=Config(n_frames=80,bootstrap=0)
    rng=np.random.default_rng(cfg.seed+20); results=[]
    for group in GROUPS:
        raw,meta=extract_video(VIDEOS/group["file"],cfg); data=select(raw,group["center"])
        c=float(np.median(data.c_individual)); cdraw=bootstrap(data,group,cfg)
        tc=threshold_cs(data,group["center"])
        threshold_sd=float(np.std(list(tc.values()),ddof=1)) if len(tc)>1 else 0.0
        # El umbral es común a todas las trazas: se suma como corrimiento sistemático.
        cdraw += rng.normal(0,threshold_sd,len(cdraw))
        rdraw=rng.normal(cfg.r0,cfg.r0_sd,len(cdraw)); vdraw=rng.normal(cfg.voltage,cfg.voltage_sd,len(cdraw))
        qdraw=q_over_m(cdraw,rdraw,vdraw,cfg.frequency)
        result={**group,"n_raw":len(raw),"n_used":len(data),"n_frames":int(data.frame.nunique()),
                "c_alt":c,"c_boot_sd":float(np.std(cdraw,ddof=1)),"threshold_c_sd":threshold_sd,
                "c_p16":float(np.percentile(cdraw,16)),"c_p84":float(np.percentile(cdraw,84)),
                "qm_alt":float(np.median(qdraw)),"qm_sd":float(np.std(qdraw,ddof=1)),
                "qm_p16":float(np.percentile(qdraw,16)),"qm_p84":float(np.percentile(qdraw,84)),
                "delta_vs_original_percent":100*(float(np.median(qdraw))/group["original_qm"]-1),
                "threshold_results":json.dumps(tc),"fps":meta["fps"]}
        results.append(result); data.to_csv(OUT/f"trazas_{group['group'].replace(' ','_').lower()}.csv",index=False)
        group_figure(data,group,c,cdraw,OUT/f"figura_{group['group'].replace(' ','_').lower()}.png")
    table=pd.DataFrame(results); table.to_csv(OUT/"resultados.csv",index=False)
    print(table[["group","file","n_used","c_alt","c_boot_sd","qm_alt","qm_sd","delta_vs_original_percent"]].to_string(index=False))


if __name__ == "__main__": main()
