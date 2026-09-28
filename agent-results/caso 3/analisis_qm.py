"""Analisis reproducible de micromocion en una trampa de Paul anular.

Implementado desde cero a partir de readme_metodo.pdf. No usa resultados previos.
Genera CSV, figuras PNG y un informe HTML autocontenido por enlaces locales.
"""
from __future__ import annotations

import base64
import csv
import html
import math
from pathlib import Path

import cv2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import least_squares


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "resultados_qm"
FIG = OUT / "figuras"
OUT.mkdir(exist_ok=True)
FIG.mkdir(exist_ok=True)

# Constantes aportadas por la usuaria (SI)
VAC, S_VAC = 1175.0, 24.0
R0, S_R0 = 8.90e-3, 0.50e-3
FREQ, S_FREQ = 50.0, 0.0  # no se informo incertidumbre
OMEGA = 2 * np.pi * FREQ

# Decisiones de procesamiento, comunes a todos los videos
CHANNEL = 2                 # OpenCV BGR: 2 = rojo
THRESHOLD = 60
THRESHOLD_DELTAS = (-10, 0, 10)
SAMPLE_SECONDS = 1.0        # reduce pseudorreplicacion temporal
AREA_RANGE = (18, 1300)
ELONGATION_MIN = 2.0
MIN_SKELETON_LENGTH = 7.0
MAX_BRANCH_PIXELS = 5
RNG = np.random.default_rng(20260927)
N_BOOT = 400


def thin_zhang_suen(binary: np.ndarray) -> np.ndarray:
    """Esqueletizacion Zhang-Suen, implementada solo con NumPy."""
    im = (binary > 0).astype(np.uint8)
    changed = True
    while changed:
        changed = False
        for phase in (0, 1):
            p = np.pad(im, 1)
            p2, p3, p4 = p[:-2, 1:-1], p[:-2, 2:], p[1:-1, 2:]
            p5, p6, p7 = p[2:, 2:], p[2:, 1:-1], p[2:, :-2]
            p8, p9 = p[1:-1, :-2], p[:-2, :-2]
            neigh = [p2, p3, p4, p5, p6, p7, p8, p9]
            n = sum(neigh)
            seq = neigh + [p2]
            s = sum(((seq[i] == 0) & (seq[i + 1] == 1)) for i in range(8))
            if phase == 0:
                m1 = p2 * p4 * p6
                m2 = p4 * p6 * p8
            else:
                m1 = p2 * p4 * p8
                m2 = p2 * p6 * p8
            remove = (im == 1) & (n >= 2) & (n <= 6) & (s == 1) & (m1 == 0) & (m2 == 0)
            if np.any(remove):
                im[remove] = 0
                changed = True
    return im


def skeleton_metrics(sk: np.ndarray) -> tuple[float, int, int]:
    """Longitud de arco por suma de aristas 8-conexas, extremos y ramificaciones."""
    y, x = np.nonzero(sk)
    if len(x) < 2:
        return 0.0, 0, 0
    # Cada arista se cuenta una sola vez: derecha, abajo y dos diagonales hacia abajo.
    length = float(np.sum(sk[:, :-1] & sk[:, 1:]) + np.sum(sk[:-1, :] & sk[1:, :]))
    length += math.sqrt(2) * float(np.sum(sk[:-1, :-1] & sk[1:, 1:]) + np.sum(sk[:-1, 1:] & sk[1:, :-1]))
    p = np.pad(sk, 1)
    degree = sum(p[1+dy:1+dy+sk.shape[0], 1+dx:1+dx+sk.shape[1]]
                 for dy in (-1, 0, 1) for dx in (-1, 0, 1) if (dy, dx) != (0, 0))
    endpoints = int(np.sum(sk & (degree == 1)))
    branches = int(np.sum(sk & (degree > 2)))
    return length, endpoints, branches


def components(frame: np.ndarray, threshold: int) -> list[dict]:
    red = frame[:, :, CHANNEL]
    mask = (red > threshold).astype(np.uint8)
    # Cierra agujeros de un pixel, sin dilatar de manera sostenida los extremos.
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    n, labels, stats, centroids = cv2.connectedComponentsWithStats(mask, 8)
    found = []
    for lab in range(1, n):
        x, y, w, h, area = stats[lab]
        if not (AREA_RANGE[0] <= area <= AREA_RANGE[1]):
            continue
        yy, xx = np.nonzero(labels == lab)
        pts = np.column_stack((xx, yy)).astype(float)
        cov = np.cov(pts, rowvar=False)
        eig = np.linalg.eigvalsh(cov)
        elong = math.sqrt(max(eig[-1], 1e-9) / max(eig[0], 1e-9))
        if elong < ELONGATION_MIN:
            continue
        roi = (labels[y:y+h, x:x+w] == lab).astype(np.uint8)
        sk = thin_zhang_suen(roi)
        length, endpoints, branches = skeleton_metrics(sk)
        if length < MIN_SKELETON_LENGTH or branches > MAX_BRANCH_PIXELS or endpoints > 4:
            continue
        found.append(dict(x=float(centroids[lab][0]), y=float(centroids[lab][1]),
                          L=length, area=int(area), elongation=elong,
                          endpoints=endpoints, branches=branches,
                          bbox=(int(x), int(y), int(w), int(h))))
    return found


def match_thresholds(nominal: list[dict], alternatives: list[list[dict]]) -> list[dict]:
    """Asigna a cada deteccion nominal su homologa espacial en T+-10."""
    out = []
    for d in nominal:
        lengths = [d["L"]]
        for alt in alternatives:
            if not alt:
                continue
            dist = np.array([math.hypot(a["x"] - d["x"], a["y"] - d["y"]) for a in alt])
            j = int(np.argmin(dist))
            if dist[j] <= max(6.0, 0.25 * d["L"]):
                lengths.append(alt[j]["L"])
        z = dict(d)
        z["sigma_L"] = max(1.0, (max(lengths) - min(lengths)) / 2 if len(lengths) > 1 else 2.0)
        z["threshold_matches"] = len(lengths)
        out.append(z)
    return out


def fit_center(data: list[dict], robust: bool = True, initial=None):
    x = np.array([d["x"] for d in data]); y = np.array([d["y"] for d in data])
    L = np.array([d["L"] for d in data]); sL = np.array([d["sigma_L"] for d in data])
    if initial is None:
        initial = np.array([np.median(x), np.median(y) + 80, 0.25])
    def residual(p):
        R = np.hypot(x - p[0], y - p[1])
        return (L - p[2] * R) / np.maximum(sL, 1.0)
    # El nulo debe estar dentro del campo filmado; permitir centros arbitrariamente
    # lejanos vuelve casi degenerados c y la distancia cuando solo se ve un arco.
    result = least_squares(residual, initial, bounds=([0, 0, .005], [639, 479, 2.0]),
                           loss="soft_l1" if robust else "linear", f_scale=1.5, max_nfev=3000)
    return result.x, result


def bootstrap_by_frame(data: list[dict], p0: np.ndarray):
    frames = np.unique([d["frame"] for d in data])
    vals = []
    for _ in range(N_BOOT):
        chosen = RNG.choice(frames, size=len(frames), replace=True)
        sample = []
        for new_group, fr in enumerate(chosen):
            for d in data:
                if d["frame"] == fr:
                    z = dict(d); z["frame"] = new_group; sample.append(z)
        try:
            p, res = fit_center(sample, robust=True, initial=p0)
            if res.success and np.all(np.isfinite(p)):
                vals.append(p)
        except Exception:
            pass
    return np.asarray(vals)


def analyze_video(path: Path) -> tuple[dict, list[dict]]:
    cap = cv2.VideoCapture(str(path))
    fps = cap.get(cv2.CAP_PROP_FPS); nframes = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    # Se omite 5% en ambos extremos por movimientos al iniciar/detener la filmacion.
    indices = np.arange(int(.05*nframes), int(.95*nframes), max(1, int(round(SAMPLE_SECONDS*fps))))
    # La filmacion es a mano: registramos rotacion+traslacion contra el cuadro
    # central antes de medir. ECC tolera cambios globales de brillo mejor que
    # correlacionar mascaras binarias.
    ref_idx = int(.5*nframes)
    cap.set(cv2.CAP_PROP_POS_FRAMES, ref_idx); ok_ref, ref_frame = cap.read()
    if not ok_ref:
        cap.release()
        return dict(video=path.name, fps=fps, duration=nframes/fps,
                    sampled_frames=len(indices), detections=0, usable=False,
                    reason="no se pudo leer cuadro de referencia", n_boot=0), []
    ref_gray = cv2.GaussianBlur(ref_frame[:,:,CHANNEL].astype(np.float32)/255.0, (9,9), 0)
    data = []; registration_failures = 0
    for idx in indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(idx)); ok, frame = cap.read()
        if not ok: continue
        mov_gray = cv2.GaussianBlur(frame[:,:,CHANNEL].astype(np.float32)/255.0, (9,9), 0)
        warp = np.eye(2,3,dtype=np.float32)
        try:
            _, warp = cv2.findTransformECC(ref_gray, mov_gray, warp, cv2.MOTION_EUCLIDEAN,
                                            (cv2.TERM_CRITERIA_EPS|cv2.TERM_CRITERIA_COUNT, 120, 1e-6),
                                            None, 3)
            aligned = cv2.warpAffine(frame, warp, (frame.shape[1],frame.shape[0]),
                                     flags=cv2.INTER_LINEAR|cv2.WARP_INVERSE_MAP,
                                     borderMode=cv2.BORDER_CONSTANT)
        except cv2.error:
            registration_failures += 1
            continue
        sets = {t: components(aligned, t) for t in (THRESHOLD-10, THRESHOLD, THRESHOLD+10)}
        matched = match_thresholds(sets[THRESHOLD], [sets[THRESHOLD-10], sets[THRESHOLD+10]])
        for d in matched:
            d.update(frame=int(idx), time=float(idx/fps), video=path.name)
        data.extend(matched)
    cap.release()
    summary = dict(video=path.name, fps=fps, duration=nframes/fps, sampled_frames=len(indices),
                   registration_failures=registration_failures, detections=len(data))
    if len(data) < 8:
        summary.update(usable=False, reason="menos de 8 detecciones", n_boot=0)
        return summary, data
    p, fit = fit_center(data)
    x0, y0, c = p
    for d in data:
        d["R"] = math.hypot(d["x"]-x0, d["y"]-y0)
        d["c_i"] = d["L"] / d["R"] if d["R"] else np.nan
        d["residual"] = d["L"] - c*d["R"]
    boot = bootstrap_by_frame(data, p)
    R = np.array([d["R"] for d in data]); L = np.array([d["L"] for d in data])
    angles = np.unwrap(np.sort(np.arctan2([d["y"]-y0 for d in data], [d["x"]-x0 for d in data])))
    angle_span = float(np.degrees(angles[-1]-angles[0])) if len(angles)>1 else 0
    # Menor arco que contiene todos los puntos (evita salto -pi/pi).
    rawang = np.sort(np.mod(np.arctan2([d["y"]-y0 for d in data], [d["x"]-x0 for d in data]), 2*np.pi))
    gaps = np.diff(np.r_[rawang, rawang[0]+2*np.pi]); angle_span = float(np.degrees(2*np.pi-gaps.max()))
    ss_res=np.sum((L-c*R)**2); ss_tot=np.sum((L-L.mean())**2); r2=1-ss_res/ss_tot if ss_tot else np.nan
    center_sd = float(np.hypot(np.std(boot[:,0],ddof=1),np.std(boot[:,1],ddof=1))) if len(boot)>10 else np.inf
    sc = float(np.std(boot[:,2],ddof=1)) if len(boot)>10 else np.inf
    # Criterios establecidos antes de ver Q/m.
    reasons=[]
    if len(data)<30: reasons.append("<30 detecciones")
    if len(np.unique([d['frame'] for d in data]))<8: reasons.append("<8 cuadros con trazas")
    if np.ptp(R)<35: reasons.append("rango radial <35 px")
    if angle_span<50: reasons.append("cobertura angular <50 grados")
    if center_sd>30: reasons.append("centro bootstrap inestable (>30 px)")
    if not np.isfinite(r2) or r2<0.35: reasons.append("R2 <0,35")
    usable=not reasons
    factor=R0**2*OMEGA**2/(4*VAC)
    qm=c*factor
    # Independencia entre incertidumbre estadistica de c y parametros instrumentales.
    rel_instr=math.sqrt((2*S_R0/R0)**2+(S_VAC/VAC)**2+(2*S_FREQ/FREQ if FREQ else 0)**2)
    sqm=abs(qm)*math.sqrt((sc/c)**2+rel_instr**2) if np.isfinite(sc) else np.inf
    summary.update(x0=x0,y0=y0,c=c,sigma_c=sc,qm=qm,sigma_qm=sqm,r2=r2,
                   center_boot_sd=center_sd,n_boot=len(boot),r_span=float(np.ptp(R)),
                   angle_span=angle_span,usable=usable,reason="; ".join(reasons) if reasons else "cumple todos los criterios")
    return summary,data


def save_figures(s: dict, data: list[dict]):
    stem = Path(s["video"]).stem.replace("WhatsApp Video 2026-09-26 at ", "").replace(" ", "_").replace(".", "-")
    R=np.array([d["R"] for d in data]); L=np.array([d["L"] for d in data]); ci=np.array([d["c_i"] for d in data])
    fig,ax=plt.subplots(figsize=(6.6,4.6)); ax.scatter(R,L,s=17,alpha=.55,label="trazas")
    rr=np.linspace(0,max(R)*1.05,200); ax.plot(rr,s["c"]*rr,"#b2182b",lw=2,label=f"L = ({s['c']:.4f}) R")
    ax.set(xlabel="R (px)",ylabel="L (px)",title=f"{stem}: ajuste L = cR; R² = {s['r2']:.3f}")
    ax.grid(alpha=.25); ax.legend(); fig.tight_layout(); fitname=f"ajuste_{stem}.png"; fig.savefig(FIG/fitname,dpi=170); plt.close(fig)
    fig,ax=plt.subplots(figsize=(6.6,4.6)); bins=max(6,min(25,int(np.sqrt(len(ci)))))
    ax.hist(ci[np.isfinite(ci)],bins=bins,color="#2166ac",alpha=.8,edgecolor="white"); ax.axvline(s["c"],color="#b2182b",lw=2,label=f"c ajuste = {s['c']:.4f}")
    ax.set(xlabel=r"$c_i=L_i/R_i$",ylabel="Frecuencia",title=f"{stem}: distribución de $c_i$")
    ax.grid(axis="y",alpha=.25); ax.legend(); fig.tight_layout(); histname=f"histograma_{stem}.png"; fig.savefig(FIG/histname,dpi=170); plt.close(fig)
    return fitname,histname


def fmt(x, digits=3):
    return "—" if x is None or not np.isfinite(x) else f"{x:.{digits}g}"


def write_outputs(summaries, detections):
    skeys=sorted(set().union(*(s.keys() for s in summaries)))
    with open(OUT/"resumen_videos.csv","w",newline="",encoding="utf-8-sig") as f:
        w=csv.DictWriter(f,fieldnames=skeys); w.writeheader(); w.writerows(summaries)
    if detections:
        dkeys=sorted(set().union(*(d.keys() for d in detections)))
        with open(OUT/"trazas_detectadas.csv","w",newline="",encoding="utf-8-sig") as f:
            w=csv.DictWriter(f,fieldnames=dkeys); w.writeheader(); w.writerows(detections)
    usable=[s for s in summaries if s.get("usable")]
    rows=[]
    for s in summaries:
        status="UTILIZABLE" if s.get("usable") else "DESCARTADO"
        rows.append(f"<tr><td>{html.escape(s['video'])}</td><td class='{status.lower()}'>{status}</td><td>{s['detections']}</td><td>{fmt(s.get('c'),4)} ± {fmt(s.get('sigma_c'),2)}</td><td>{fmt(s.get('qm'),4)} ± {fmt(s.get('sigma_qm'),2)}</td><td>{fmt(s.get('r2'))}</td><td>{fmt(s.get('center_boot_sd'))}</td><td>{html.escape(s.get('reason',''))}</td></tr>")
    cards=[]
    for s in usable:
        cards.append(f"<section><h3>{html.escape(s['video'])}</h3><p><b>c = {s['c']:.4f} ± {s['sigma_c']:.4f}</b>; <b>Q/m = ({s['qm']:.4g} ± {s['sigma_qm']:.2g}) C/kg</b>. Centro ({s['x0']:.1f}, {s['y0']:.1f}) px; dispersión bootstrap {s['center_boot_sd']:.1f} px.</p><div class='figs'><figure><img src='figuras/{s['fit_fig']}'><figcaption>Ajuste robusto conjunto.</figcaption></figure><figure><img src='figuras/{s['hist_fig']}'><figcaption>Cocientes individuales, diagnóstico (no estimador final).</figcaption></figure></div></section>")
    formula_factor=R0**2*OMEGA**2/(4*VAC)
    report=f"""<!doctype html><html lang='es'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width'><title>Análisis Q/m — trampa de Paul</title><style>
body{{font:16px/1.5 system-ui,sans-serif;max-width:1180px;margin:auto;padding:2rem;color:#20242a}}h1,h2{{color:#17365d}}table{{border-collapse:collapse;width:100%;font-size:13px}}th,td{{border:1px solid #ccd3da;padding:.45rem;vertical-align:top}}th{{background:#edf3f8}}.utilizable{{color:#087830;font-weight:bold}}.descartado{{color:#a32626;font-weight:bold}}.figs{{display:grid;grid-template-columns:1fr 1fr;gap:1rem}}img{{width:100%}}figure{{margin:0}}code{{background:#eef1f4;padding:.1rem .3rem}}.warn{{background:#fff4d6;border-left:5px solid #e2a400;padding:1rem}}@media(max-width:750px){{.figs{{grid-template-columns:1fr}}}}</style></head><body>
<h1>Relación carga–masa de esporas de licopodio</h1><p>Informe generado por <code>analisis_qm.py</code> a partir de los 11 videos crudos, reconstruyendo el método de los PDF. El análisis no importa ni copia resultados preexistentes.</p>
<h2>Resultado ejecutivo</h2>{('<p>Se aceptaron <b>'+str(len(usable))+'</b> de '+str(len(summaries))+' videos mediante criterios fijados en el código.</p>') if usable else '<p class="warn"><b>Ningún video superó todos los criterios objetivos.</b> No se fuerza un Q/m final.</p>'}
<table><thead><tr><th>Video</th><th>Decisión</th><th>N trazas</th><th>c</th><th>Q/m (C/kg)</th><th>R²</th><th>σ centro (px)</th><th>Razón</th></tr></thead><tbody>{''.join(rows)}</tbody></table>
<h2>Método y decisiones</h2><ol><li>Se usa el canal rojo y un umbral fijo T={THRESHOLD} en todos los cuadros. La sensibilidad se evalúa con T=50 y 70; la semidiferencia de longitudes asignadas se incorpora como σ<sub>L</sub> (piso 1 px).</li><li>Se muestrea cada {SAMPLE_SECONDS} s y se elimina el 5% inicial/final. Esto reduce cuadros casi duplicados y movimientos de operación.</li><li>Tras cierre morfológico 3×3, se retienen componentes con área {AREA_RANGE[0]}–{AREA_RANGE[1]} px², elongación ≥{ELONGATION_MIN}, longitud ≥{MIN_SKELETON_LENGTH} px y poca ramificación. La esqueletización Zhang–Suen y la suma de enlaces rectos/diagonales miden el arco.</li><li>Se ajustan simultáneamente (x₀,y₀,c) en L=c·sqrt((x−x₀)²+(y−y₀)²), ponderando por σ<sub>L</sub> y usando pérdida robusta soft-L1.</li><li>La incertidumbre de c y la estabilidad del centro se obtienen con {N_BOOT} remuestreos <i>por cuadro</i>. Así las trazas del mismo cuadro permanecen agrupadas.</li><li>Criterios de uso: ≥30 trazas, ≥8 cuadros, rango radial ≥35 px, cobertura angular ≥50°, dispersión bootstrap del centro ≤30 px y R²≥0,35.</li></ol>
<h2>Conversión a Q/m e incertidumbre</h2><p>Se aplicó exactamente la expresión del README: Q/m = c r₀² Ω²/(4V<sub>AC</sub>), Ω=2πf. Datos: V<sub>AC</sub>=({VAC:.0f}±{S_VAC:.0f}) V, r₀=({R0*1e3:.2f}±{S_R0*1e3:.2f}) mm y f={FREQ:.0f} Hz. El factor es {formula_factor:.6g} (C/kg)/unidad de c.</p><p>Se propagó σ²<sub>Q/m</sub>/(Q/m)²=(σ<sub>c</sub>/c)²+(2σ<sub>r₀</sub>/r₀)²+(σ<sub>V</sub>/V)². No se incluyó error de frecuencia porque no fue informado. La incertidumbre instrumental relativa independiente de c es {math.sqrt((2*S_R0/R0)**2+(S_VAC/VAC)**2)*100:.1f}% y está dominada por r₀.</p>
<p class='warn'><b>Convención eléctrica:</b> el cálculo supone que los 1175 V corresponden al V<sub>AC</sub> definido en la fórmula del README. Si el valor suministrado fuera RMS o pico a pico mientras la derivación usa amplitud pico, Q/m debe corregirse por el factor de conversión correspondiente.</p>
<h2>Resultados aceptados y figuras</h2>{''.join(cards) if cards else '<p>No hay figuras de resultados aceptados; las métricas completas quedan en el CSV.</p>'}
<h2>Limitaciones y conclusión</h2><p>El método mide c sin calibración espacial porque L/R es adimensional. La mayor limitación es que la selección originalmente descrita como semiautomática se hizo aquí mediante reglas reproducibles, sin corrección manual cuadro a cuadro. Reflejos, trazas fusionadas y cambios fuertes de exposición se controlaron por morfología, ajuste robusto y criterios de descarte, pero pueden dejar sesgo residual. Los histogramas de cᵢ sirven para visualizar dispersión y colas; el valor reportado proviene del ajuste global con centro común.</p><p>Archivos auditables: <a href='resumen_videos.csv'>resumen por video</a>, <a href='trazas_detectadas.csv'>todas las trazas</a> y <a href='../analisis_qm.py'>código fuente</a>.</p></body></html>"""
    (OUT/"informe_resultados.html").write_text(report,encoding="utf-8")


def main():
    summaries=[]; all_detections=[]
    for path in sorted(ROOT.glob("*.mp4")):
        print("Procesando",path.name,flush=True)
        s,data=analyze_video(path)
        summaries.append(s); all_detections.extend(data)
        print(" ",s.get("usable"),s.get("reason"),"N=",len(data),"c=",s.get("c"),flush=True)
    for s in summaries:
        if s.get("c") is not None:
            data=[d for d in all_detections if d["video"]==s["video"]]
            s["fit_fig"],s["hist_fig"]=save_figures(s,data)
    write_outputs(summaries,all_detections)
    print("Listo:",OUT/"informe_resultados.html")


if __name__ == "__main__":
    main()
