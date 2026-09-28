"""Análisis automático alternativo de estelas en una trampa de Paul.

La longitud se estima con área y perímetro de la silueta (modelo cápsula), sin
esqueletización. El centro y c se obtienen con regresión robusta; la incertidumbre
se calcula por bootstrap de frames y Monte Carlo de los parámetros instrumentales.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, asdict
from pathlib import Path

import cv2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.optimize import least_squares


@dataclass
class Config:
    n_frames: int = 80
    threshold: int = 40
    area_min: float = 150.0
    area_max: float = 8000.0
    elongation_min: float = 2.5
    border: int = 4
    thresholds_length: tuple[int, ...] = (32, 36, 40, 44, 48)
    bootstrap: int = 500
    seed: int = 20260927
    voltage: float = 1175.0
    voltage_sd: float = 24.0
    r0: float = 8.90e-3
    r0_sd: float = 0.50e-3
    frequency: float = 50.0


def capsule_length(area: float, perimeter: float) -> float:
    """Longitud del eje de una cápsula: P=2L+pi*w, A=L*w+pi*w²/4."""
    return 0.5 * np.sqrt(max(perimeter * perimeter - 4 * np.pi * area, 0.0))


def contour_features(contour: np.ndarray) -> tuple[float, float, float, float, float, float, float]:
    area = cv2.contourArea(contour)
    perimeter = cv2.arcLength(contour, True)
    moments = cv2.moments(contour)
    if moments["m00"] <= 0:
        return (np.nan,) * 7
    x = moments["m10"] / moments["m00"]
    y = moments["m01"] / moments["m00"]
    cov = np.array([[moments["mu20"], moments["mu11"]],
                    [moments["mu11"], moments["mu02"]]], dtype=float) / moments["m00"]
    vals, vecs = np.linalg.eigh(cov)
    elong = np.sqrt(max(vals[-1], 1e-9) / max(vals[0], 1e-9))
    ux, uy = vecs[:, -1]
    return x, y, area, perimeter, elong, ux, uy


def component_at_point(contours: list[np.ndarray], x: float, y: float) -> np.ndarray | None:
    containing = [c for c in contours if cv2.pointPolygonTest(c, (x, y), False) >= 0]
    if not containing:
        return None
    return max(containing, key=cv2.contourArea)


def extract_video(path: Path, cfg: Config) -> tuple[pd.DataFrame, dict]:
    cap = cv2.VideoCapture(str(path))
    n_total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = float(cap.get(cv2.CAP_PROP_FPS))
    indices = np.unique(np.linspace(0, max(n_total - 1, 0), cfg.n_frames, dtype=int))
    rows: list[dict] = []
    for frame_id in indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(frame_id))
        ok, bgr = cap.read()
        if not ok:
            continue
        red = bgr[:, :, 2]
        base = (red >= cfg.threshold).astype(np.uint8) * 255
        contours, _ = cv2.findContours(base, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_TC89_KCOS)
        contours_by_threshold = {}
        for threshold in cfg.thresholds_length:
            binary = (red >= threshold).astype(np.uint8) * 255
            contours_by_threshold[threshold], _ = cv2.findContours(
                binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_TC89_KCOS)
        h, w = red.shape
        for contour in contours:
            x, y, area, perimeter, elong, ux, uy = contour_features(contour)
            if not np.isfinite(x) or not (cfg.area_min <= area <= cfg.area_max):
                continue
            bx, by, bw, bh = cv2.boundingRect(contour)
            if elong < cfg.elongation_min or min(bx, by, w - bx - bw, h - by - bh) < cfg.border:
                continue
            local_mask = np.zeros((bh, bw), np.uint8)
            shifted = contour - np.array([[[bx, by]]], dtype=contour.dtype)
            cv2.drawContours(local_mask, [shifted], -1, 255, -1)
            mean_red = float(cv2.mean(red[by:by+bh, bx:bx+bw], mask=local_mask)[0])
            lengths = []
            lengths_by_threshold = {}
            for threshold in cfg.thresholds_length:
                candidate = component_at_point(contours_by_threshold[threshold], x, y)
                if candidate is None:
                    continue
                a = cv2.contourArea(candidate)
                p = cv2.arcLength(candidate, True)
                if 0.45 * area <= a <= 2.2 * area:
                    value = capsule_length(a, p)
                    lengths.append(value)
                    lengths_by_threshold[f"length_t{threshold}_px"] = value
            if len(lengths) < 3:
                continue
            length = float(np.median(lengths))
            length_sd = float(1.4826 * np.median(np.abs(np.asarray(lengths) - length)))
            if length < 8 or length > 350:
                continue
            rows.append({"video": path.name, "frame": frame_id, "time_s": frame_id / fps,
                         "x_px": x, "y_px": y, "length_px": length,
                         "length_threshold_sd_px": max(length_sd, 0.75),
                         "area_px2": area, "perimeter_px": perimeter, "elongation": elong})
            rows[-1].update({"axis_x": ux, "axis_y": uy, "mean_red": mean_red})
            rows[-1].update(lengths_by_threshold)
    cap.release()
    return pd.DataFrame(rows), {"fps": fps, "frames": n_total, "duration_s": n_total / fps}


def fit_center(data: pd.DataFrame, start: np.ndarray | None = None) -> tuple[np.ndarray, np.ndarray]:
    x = data.x_px.to_numpy(); y = data.y_px.to_numpy(); length = data.length_px.to_numpy()
    if start is None:
        start = np.array([300.0, 70.0, 0.5])
    ux=data.axis_x.to_numpy(); uy=data.axis_y.to_numpy()
    def line_res(center: np.ndarray) -> np.ndarray:
        # Las estelas observadas son tangentes al arco de micromovimiento: el
        # radio hacia el nulo de RF es, por tanto, normal a su eje principal.
        return ux * (center[0] - x) + uy * (center[1] - y)
    center = least_squares(line_res, start[:2], loss="soft_l1", f_scale=8.0,
                           bounds=([0, -150], [640, 300]), max_nfev=3000).x
    line_raw=line_res(center); line_mad=1.4826*np.median(np.abs(line_raw-np.median(line_raw)))
    keep=np.abs(line_raw-np.median(line_raw)) <= max(2.8*line_mad,12.0)
    if keep.sum() >= 8:
        center=least_squares(lambda z: line_res(z)[keep],center,loss="soft_l1",f_scale=5.0,
                             bounds=([0,-150],[640,300]),max_nfev=3000).x
    radius=np.hypot(x-center[0],y-center[1])
    slope=float(np.sum(radius[keep]*length[keep])/np.sum(radius[keep]**2))
    raw=length-slope*radius; mad=1.4826*np.median(np.abs(raw[keep]-np.median(raw[keep])))
    keep &= np.abs(raw-np.median(raw[keep])) <= max(2.8*mad,6.0)
    if keep.sum() >= 8:
        slope=float(least_squares(lambda z:(length[keep]-z[0]*radius[keep])/4.0,[slope],
                                  loss="soft_l1",f_scale=1.5,bounds=([0.03],[1.2])).x[0])
    return np.array([center[0],center[1],slope]),keep


def diagnostics(data: pd.DataFrame, params: np.ndarray, keep: np.ndarray) -> dict:
    d = data.loc[keep].copy()
    radius = np.hypot(d.x_px - params[0], d.y_px - params[1])
    pred = params[2] * radius
    resid = d.length_px.to_numpy() - pred
    ss_res = float(np.sum(resid ** 2)); ss_tot = float(np.sum((d.length_px - d.length_px.mean()) ** 2))
    angles = np.unwrap(np.sort(np.arctan2(d.y_px - params[1], d.x_px - params[0])))
    coverage = float(np.degrees(angles[-1] - angles[0])) if len(angles) else 0.0
    return {"n": int(len(d)), "xc_px": params[0], "yc_px": params[1], "c": params[2],
            "r2": 1 - ss_res / ss_tot if ss_tot else np.nan,
            "residual_mad_px": 1.4826 * float(np.median(np.abs(resid - np.median(resid)))),
            "angular_coverage_deg": coverage}


def bootstrap_frames(data: pd.DataFrame, params: np.ndarray, cfg: Config) -> np.ndarray:
    rng = np.random.default_rng(cfg.seed)
    frames = data.frame.unique()
    out = []
    for _ in range(cfg.bootstrap):
        chosen = rng.choice(frames, len(frames), replace=True)
        pieces = [data[data.frame == f] for f in chosen]
        sample = pd.concat(pieces, ignore_index=True)
        try:
            p, _ = fit_center(sample, params)
            out.append(p)
        except Exception:
            pass
    return np.asarray(out)


def q_over_m(c: np.ndarray | float, r0: np.ndarray | float, voltage: np.ndarray | float,
             frequency: float) -> np.ndarray | float:
    return c * r0 ** 2 * (2 * np.pi * frequency) ** 2 / (4 * voltage)


def save_video_figure(data: pd.DataFrame, params: np.ndarray, boot: np.ndarray, keep: np.ndarray,
                      out: Path, label: str) -> None:
    d = data.loc[keep].copy()
    radius = np.hypot(d.x_px - params[0], d.y_px - params[1])
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.2))
    ax = axes[0]
    ax.scatter(data.x_px, data.y_px, s=7, alpha=.18, color="0.5", label="detectadas")
    ax.scatter(d.x_px, d.y_px, s=9, alpha=.45, color="#d62728", label="usadas")
    if len(boot): ax.scatter(boot[:, 0], boot[:, 1], s=4, alpha=.08, color="#1f77b4")
    ax.scatter(params[0], params[1], marker="x", s=90, color="black", label="centro")
    ax.invert_yaxis(); ax.set_aspect("equal"); ax.set_xlabel("x [px]"); ax.set_ylabel("y [px]"); ax.legend(fontsize=8)
    ax = axes[1]
    ax.errorbar(radius, d.length_px, yerr=d.length_threshold_sd_px, fmt=".", ms=3, alpha=.45, color="#d62728")
    rr = np.linspace(0, max(radius) * 1.03, 200); ax.plot(rr, params[2] * rr, color="black", lw=2)
    ax.set(xlabel="R [px]", ylabel="L por área-perímetro [px]", title=f"c = {params[2]:.3f}")
    ax = axes[2]
    ci = d.length_px.to_numpy() / radius
    ax.hist(ci, bins="auto", color="#d62728", alpha=.7); ax.axvline(params[2], color="black", lw=2)
    ax.set(xlabel="c individual = L/R", ylabel="cuentas")
    fig.suptitle(label); fig.tight_layout(); fig.savefig(out, dpi=180); plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--videos", type=Path, default=Path("drive-download-20260926T014040Z-1-001"))
    parser.add_argument("--out", type=Path, default=Path("resultados_alternativos"))
    parser.add_argument("--frames", type=int, default=80)
    parser.add_argument("--bootstrap", type=int, default=500)
    args = parser.parse_args()
    cfg = Config(n_frames=args.frames, bootstrap=args.bootstrap)
    args.out.mkdir(parents=True, exist_ok=True)
    all_rows=[]; summaries=[]; meta={}
    rng=np.random.default_rng(cfg.seed + 1)
    for path in sorted(args.videos.glob("*.mp4")):
        data, video_meta = extract_video(path, cfg)
        if len(data) < 12:
            summaries.append({"video": path.name, "n": len(data), "status": "insuficiente"}); continue
        params, keep = fit_center(data)
        boot = bootstrap_frames(data.loc[keep], params, cfg)
        diag = diagnostics(data, params, keep); diag.update({"video": path.name, "status": "ok"})
        if len(boot):
            diag.update({"c_boot_sd": float(np.std(boot[:,2], ddof=1)),
                         "xc_boot_sd_px": float(np.std(boot[:,0], ddof=1)),
                         "yc_boot_sd_px": float(np.std(boot[:,1], ddof=1))})
            cdraw=rng.choice(boot[:,2], 30000, replace=True)
        else:
            cdraw=np.full(30000, params[2])
        rdraw=rng.normal(cfg.r0,cfg.r0_sd,len(cdraw)); vdraw=rng.normal(cfg.voltage,cfg.voltage_sd,len(cdraw))
        qdraw=q_over_m(cdraw,rdraw,vdraw,cfg.frequency)
        diag.update({"q_over_m": float(np.median(qdraw)), "q_over_m_sd": float(np.std(qdraw,ddof=1)),
                     "q_over_m_p16": float(np.percentile(qdraw,16)), "q_over_m_p84": float(np.percentile(qdraw,84))})
        summaries.append(diag); data.assign(used=keep).to_csv(args.out/f"trazas_{path.stem}.csv",index=False)
        save_video_figure(data,params,boot,keep,args.out/f"diagnostico_{path.stem}.png",path.stem)
        all_rows.append(data.assign(used=keep)); meta[path.name]=video_meta
        print(path.name, json.dumps(diag, ensure_ascii=False))
    pd.DataFrame(summaries).to_csv(args.out/"resumen_videos.csv",index=False)
    if all_rows: pd.concat(all_rows,ignore_index=True).to_csv(args.out/"todas_las_trazas.csv",index=False)
    (args.out/"configuracion.json").write_text(json.dumps({"config":asdict(cfg),"videos":meta},indent=2),encoding="utf-8")


if __name__ == "__main__":
    main()
