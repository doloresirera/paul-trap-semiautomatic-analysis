"""Quantitative video analysis of lycopodium particles in an RF Paul trap.

The script is deliberately self-contained and produces machine-readable tables,
diagnostic figures, and a Spanish report under ``results/``.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

import cv2
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment
from scipy.signal import find_peaks, welch


VIDEO_DIR = Path("drive-download-20260926T014040Z-1-001")
OUT = Path("results")
V_RF = 1175.0
F_RF = 50.0
R0 = 8.9e-3
OMEGA = 2 * np.pi * F_RF
DIAMETER = 30e-6


@dataclass
class Detection:
    frame: int
    x: float
    y: float
    major: float
    minor: float
    angle: float
    area: int
    intensity: float


def detect(frame: np.ndarray, frame_no: int) -> list[Detection]:
    """Segment red luminous traces and measure intensity-weighted PCA geometry."""
    red = frame[:, :, 2].astype(np.float32)
    background = cv2.GaussianBlur(red, (0, 0), 15)
    signal = np.clip(red - background, 0, None)
    positive = signal[signal > 0]
    if positive.size == 0:
        return []
    threshold = max(12.0, float(np.percentile(positive, 92)))
    mask = (signal >= threshold).astype(np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    n, labels, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
    out: list[Detection] = []
    for label in range(1, n):
        area = int(stats[label, cv2.CC_STAT_AREA])
        if not 12 <= area <= 6000:
            continue
        x0 = int(stats[label, cv2.CC_STAT_LEFT])
        y0 = int(stats[label, cv2.CC_STAT_TOP])
        width = int(stats[label, cv2.CC_STAT_WIDTH])
        height = int(stats[label, cv2.CC_STAT_HEIGHT])
        local_y, local_x = np.nonzero(labels[y0:y0 + height, x0:x0 + width] == label)
        xx = local_x + x0
        yy = local_y + y0
        weights = signal[yy, xx].astype(float) + 1e-6
        total = weights.sum()
        x = float(np.dot(xx, weights) / total)
        y = float(np.dot(yy, weights) / total)
        coords = np.column_stack((xx - x, yy - y))
        cov = (coords * weights[:, None]).T @ coords / total
        vals, vecs = np.linalg.eigh(cov)
        vals = np.maximum(vals, 0)
        v = vecs[:, 1]
        projection = coords @ v
        order = np.argsort(projection)
        p = projection[order]
        w = weights[order]
        cw = np.cumsum(w) / total
        lo = float(np.interp(0.02, cw, p))
        hi = float(np.interp(0.98, cw, p))
        major = max(hi - lo, 4 * math.sqrt(vals[1]))
        minor = 4 * math.sqrt(vals[0])
        if major < 3 or minor < 0.5:
            continue
        out.append(Detection(frame_no, x, y, major, minor,
                             float(math.atan2(v[1], v[0])), area, float(total)))
    return out


def fit_rf_null(df: pd.DataFrame) -> tuple[np.ndarray, float]:
    """Least-squares intersection of the major axes of elongated traces."""
    good = df[(df.elongation >= 2.0) & (df.major >= 10) & (df.area >= 20)].copy()
    # Keep one observation per approximate object/time window to limit over-weighting.
    good = good.iloc[::5]
    A = np.zeros((2, 2))
    b = np.zeros(2)
    for row in good.itertuples():
        v = np.array([math.cos(row.angle), math.sin(row.angle)])
        projector = np.eye(2) - np.outer(v, v)
        weight = min(row.major / max(row.minor, 1), 8.0)
        p = np.array([row.x, row.y])
        A += weight * projector
        b += weight * projector @ p
    null = np.linalg.solve(A, b)
    residuals = []
    for row in good.itertuples():
        v = np.array([math.cos(row.angle), math.sin(row.angle)])
        delta = null - np.array([row.x, row.y])
        residuals.append(abs(v[0] * delta[1] - v[1] * delta[0]))
    return null, float(np.median(residuals))


def trace_q_values(df: pd.DataFrame, null: np.ndarray) -> pd.DataFrame:
    dx = df.x.to_numpy() - null[0]
    dy = df.y.to_numpy() - null[1]
    radius = np.hypot(dx, dy)
    radial_angle = np.arctan2(dy, dx)
    delta = np.abs(np.arctan2(np.sin(df.angle - radial_angle),
                              np.cos(df.angle - radial_angle)))
    delta = np.minimum(delta, np.pi - delta)
    length = np.sqrt(np.maximum(df.major.to_numpy() ** 2 - df.minor.to_numpy() ** 2, 0))
    q = length / radius
    ans = df.copy()
    ans["radius_px"] = radius
    ans["radial_misalignment_deg"] = np.degrees(delta)
    ans["corrected_length_px"] = length
    ans["q_trace"] = q
    return ans[(ans.elongation >= 2) & (ans.area >= 20) &
               (ans.radius_px >= 20) & (ans.radial_misalignment_deg <= 30) &
               (ans.q_trace > 0.01) & (ans.q_trace < 1.2)]


def make_tracks(df: pd.DataFrame, fps: float, max_dist: float = 30.0) -> list[pd.DataFrame]:
    """Nearest-neighbour/Hungarian frame-to-frame tracks with a two-frame gap."""
    active: dict[int, tuple[int, np.ndarray, list[int]]] = {}
    finished: list[list[int]] = []
    next_id = 0
    for frame_no, group in df.groupby("frame", sort=True):
        inds = group.index.to_numpy()
        pts = group[["x", "y"]].to_numpy()
        stale = [key for key, (last, _, _) in active.items() if frame_no - last > 2]
        for key in stale:
            finished.append(active.pop(key)[2])
        keys = list(active)
        assigned_pts: set[int] = set()
        if keys and len(pts):
            prev = np.array([active[k][1] for k in keys])
            cost = np.linalg.norm(prev[:, None, :] - pts[None, :, :], axis=2)
            rows, cols = linear_sum_assignment(cost)
            for rr, cc in zip(rows, cols):
                if cost[rr, cc] <= max_dist:
                    key = keys[rr]
                    history = active[key][2]
                    history.append(int(inds[cc]))
                    active[key] = (int(frame_no), pts[cc], history)
                    assigned_pts.add(int(cc))
        for j, idx in enumerate(inds):
            if j not in assigned_pts:
                active[next_id] = (int(frame_no), pts[j], [int(idx)])
                next_id += 1
    finished.extend(v[2] for v in active.values())
    tracks = [df.loc[idx].sort_values("frame").copy() for idx in finished if len(idx) >= max(64, int(3 * fps))]
    return tracks


def track_spectrum(track: pd.DataFrame, fps: float) -> dict | None:
    frames = track.frame.to_numpy()
    if len(np.unique(frames)) != frames[-1] - frames[0] + 1:
        return None
    xy = track[["x", "y"]].to_numpy(copy=True)
    for column in range(2):
        xy[:, column] -= np.polyval(np.polyfit(frames, xy[:, column], 1), frames)
    cov = np.cov(xy.T)
    vals, vecs = np.linalg.eigh(cov)
    z = xy @ vecs[:, -1]
    nperseg = min(256, len(z))
    f, pxx = welch(z, fs=fps, nperseg=nperseg, detrend="linear")
    alias = abs(F_RF - round(F_RF / fps) * fps)
    allowed = (f >= 0.15) & (f <= min(10.0, fps / 2)) & (np.abs(f - alias) > 0.35)
    peaks, _ = find_peaks(np.where(allowed, pxx, 0))
    if not len(peaks):
        return None
    peak = peaks[np.argmax(pxx[peaks])]
    noise = np.median(pxx[allowed]) + 1e-12
    return {"f_sec_hz": float(f[peak]), "peak_snr": float(pxx[peak] / noise),
            "alias_rf_hz": float(alias), "duration_s": float((frames[-1] - frames[0]) / fps),
            "rms_px": float(np.std(z)), "frequencies": f, "psd": pxx}


def percentile_ci(values: np.ndarray, seed: int = 123, n: int = 5000) -> tuple[float, float, float]:
    values = np.asarray(values, float)
    values = values[np.isfinite(values)]
    rng = np.random.default_rng(seed)
    med = float(np.median(values))
    sims = np.median(rng.choice(values, (n, len(values)), replace=True), axis=1)
    lo, hi = np.percentile(sims, [2.5, 97.5])
    return med, float(lo), float(hi)


def main() -> None:
    OUT.mkdir(exist_ok=True)
    cache_dir = OUT / "cache"
    cache_dir.mkdir(exist_ok=True)
    videos = sorted(VIDEO_DIR.glob("*.mp4"))
    metadata = []
    all_detections = []
    spectra_rows = []
    representative_spectra = []
    for vid_no, path in enumerate(videos):
        cap = cv2.VideoCapture(str(path))
        fps = float(cap.get(cv2.CAP_PROP_FPS))
        count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cache_path = cache_dir / f"{path.stem}_detections.csv"
        rows = []
        frame_no = 0
        if cache_path.exists():
            df = pd.read_csv(cache_path)
        else:
            while True:
                ok, frame = cap.read()
                if not ok:
                    break
                for d in detect(frame, frame_no):
                    rows.append(vars(d))
                frame_no += 1
            df = pd.DataFrame(rows)
            df.to_csv(cache_path, index=False)
        cap.release()
        print(f"[{vid_no + 1:02d}/{len(videos)}] {path.name}: {len(df)} detecciones", flush=True)
        if df.empty:
            continue
        df["elongation"] = df.major / df.minor.clip(lower=0.1)
        df["video"] = path.name
        df["time_s"] = df.frame / fps
        all_detections.append(df)
        tracks = make_tracks(df, fps)
        for track_no, track in enumerate(tracks):
            spec = track_spectrum(track, fps)
            if spec and spec["peak_snr"] >= 5:
                spectra_rows.append({k: v for k, v in spec.items() if k not in ("frequencies", "psd")} |
                                    {"video": path.name, "track": track_no, "n": len(track)})
                if len(representative_spectra) < 12:
                    representative_spectra.append((path.name, spec))
        metadata.append({"video": path.name, "fps": fps, "frames": count,
                         "duration_s": count / fps, "width": width, "height": height,
                         "detections": len(df), "long_tracks": len(tracks),
                         "alias_50Hz_hz": abs(F_RF - round(F_RF / fps) * fps)})

    det = pd.concat(all_detections, ignore_index=True)
    # A per-video null absorbs small camera/trap shifts between recordings.
    null_rows = []
    q_parts = []
    for video_name, group in det.groupby("video"):
        local_null, local_resid = fit_rf_null(group)
        q_parts.append(trace_q_values(group, local_null))
        null_rows.append({"video": video_name, "null_x_px": local_null[0],
                          "null_y_px": local_null[1], "line_residual_px": local_resid})
    nulls = pd.DataFrame(null_rows)
    qdet = pd.concat(q_parts, ignore_index=True)
    # Global fit is retained only for the aggregate diagnostic panel.
    null, null_resid = fit_rf_null(det)
    video_q = qdet.groupby("video").q_trace.median().rename("q_trace_median")
    q_med, q_lo, q_hi = percentile_ci(video_q.to_numpy())
    qm = q_med * R0**2 * OMEGA**2 / (2 * V_RF)
    qm_lo = q_lo * R0**2 * OMEGA**2 / (2 * V_RF)
    qm_hi = q_hi * R0**2 * OMEGA**2 / (2 * V_RF)
    predicted_fsec = q_med * F_RF / (2 * math.sqrt(2))

    # A nominal image scale from the known diameter is useful only as an order-of-magnitude.
    widths = qdet.groupby("video").minor.median().to_numpy()
    width_med, width_lo, width_hi = percentile_ci(widths)
    um_per_px = 30.0 / width_med

    meta = pd.DataFrame(metadata)
    spectra = pd.DataFrame(spectra_rows)
    det.to_csv(OUT / "detections.csv", index=False)
    qdet.to_csv(OUT / "trace_measurements.csv", index=False)
    meta.to_csv(OUT / "video_metadata.csv", index=False)
    video_q.to_csv(OUT / "q_by_video.csv")
    nulls.to_csv(OUT / "rf_null_by_video.csv", index=False)
    spectra.to_csv(OUT / "track_frequencies.csv", index=False)

    # Summary plots.
    fig, axes = plt.subplots(2, 2, figsize=(13, 10), constrained_layout=True)
    ax = axes[0, 0]
    sample = qdet.sample(min(12000, len(qdet)), random_state=1)
    ax.scatter(sample.x, sample.y, s=2, alpha=.12)
    ax.scatter(*null, marker="x", s=100, c="red", label="nulo RF ajustado")
    ax.invert_yaxis(); ax.set_aspect("equal"); ax.legend(); ax.set_xlabel("x [px]"); ax.set_ylabel("y [px]")
    ax.set_title("Centroides aceptados y nulo de RF")
    ax = axes[0, 1]
    ax.hist(qdet.q_trace, bins=np.linspace(0, 1.0, 80), alpha=.7)
    ax.axvline(q_med, c="red", label=f"mediana entre videos = {q_med:.3f}")
    ax.set_xlabel("q de Mathieu (traza/radio)"); ax.set_ylabel("detecciones"); ax.legend()
    ax = axes[1, 0]
    ax.errorbar(range(len(video_q)), video_q.values, fmt="o")
    ax.axhline(q_med, c="red"); ax.set_xlabel("video"); ax.set_ylabel("q mediano")
    ax.set_title("Variación entre videos")
    ax = axes[1, 1]
    if not spectra.empty:
        ax.hist(spectra.f_sec_hz, bins=np.linspace(0, 10, 50), alpha=.75)
        ax.axvline(predicted_fsec, c="red", label="predicción desde q de trazas")
        ax.axvspan(meta.alias_50Hz_hz.min(), meta.alias_50Hz_hz.max(), alpha=.2, color="orange", label="alias de 50 Hz")
        ax.legend()
    ax.set_xlabel("frecuencia pico [Hz]"); ax.set_ylabel("tracks"); ax.set_title("Picos temporales no clasificados como alias")
    fig.savefig(OUT / "quantitative_summary.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 6), constrained_layout=True)
    for name, spec in representative_spectra:
        ax.semilogy(spec["frequencies"], spec["psd"], alpha=.55, label=name[13:21])
    ax.axvline(predicted_fsec, c="red", ls="--", label="f secular predicha")
    ax.axvspan(meta.alias_50Hz_hz.min(), meta.alias_50Hz_hz.max(), color="orange", alpha=.2, label="alias RF")
    ax.set_xlim(0, 10.8); ax.set_xlabel("frecuencia [Hz]"); ax.set_ylabel("PSD [px²/Hz]"); ax.legend(ncol=3, fontsize=8)
    fig.savefig(OUT / "track_spectra.png", dpi=180)
    plt.close(fig)

    summary = {"videos": len(meta), "frames": int(meta.frames.sum()), "duration_s": float(meta.duration_s.sum()),
               "fps_mean": float(meta.fps.mean()), "fps_sd": float(meta.fps.std()),
               "rf_null_px_global_diagnostic": [float(null[0]), float(null[1])],
               "rf_null_line_median_residual_px_global": null_resid,
               "rf_null_line_median_residual_px_between_videos": float(nulls.line_residual_px.median()),
               "q_trace": {"median": q_med, "ci95_low": q_lo, "ci95_high": q_hi, "n_videos": int(len(video_q)), "n_detections": int(len(qdet))},
               "charge_to_mass_C_per_kg": {"estimate": qm, "ci95_low": qm_lo, "ci95_high": qm_hi},
               "predicted_secular_frequency_hz": predicted_fsec,
               "minor_width_px": {"median": width_med, "ci95_low": width_lo, "ci95_high": width_hi},
               "nominal_scale_um_per_px": um_per_px,
               "frequency_tracks": int(len(spectra))}
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    write_report(summary, meta, spectra, video_q)


def write_report(s: dict, meta: pd.DataFrame, spectra: pd.DataFrame, video_q: pd.Series) -> None:
    q = s["q_trace"]; qm = s["charge_to_mass_C_per_kg"]
    mass_per_density = 4 * math.pi * (15e-6) ** 3 / 3
    charge_per_density = qm["estimate"] * mass_per_density
    elementary_per_density = charge_per_density / 1.602176634e-19
    if spectra.empty:
        freq_text = "No hubo tracks suficientemente largos y coherentes para una frecuencia independiente."
    else:
        good = spectra[spectra.peak_snr >= 8]
        near_prediction = (np.abs(spectra.f_sec_hz - s["predicted_secular_frequency_hz"]) <= 0.4).sum()
        freq_text = (f"Se obtuvieron {len(spectra)} picos de tracks (SNR≥5; {len(good)} con SNR≥8). "
                     f"Sólo {near_prediction} cae a ±0.4 Hz de la predicción geométrica; la mayoría está por debajo de 1 Hz "
                     f"y es compatible con deriva/no estacionariedad. No se identifica una frecuencia secular independiente y robusta.")
    text = f"""# Análisis cuantitativo de micromoción en una trampa de Paul

## Resumen ejecutivo

Se analizaron **{s['videos']} videos**, **{s['frames']} cuadros** y **{s['duration_s']:.1f} s** de registro. La tasa media fue {s['fps_mean']:.4f} ± {s['fps_sd']:.4f} fps. El análisis geométrico de las trazas da un parámetro de Mathieu

**q = {q['median']:.3f} (IC 95% bootstrap entre videos: {q['ci95_low']:.3f}–{q['ci95_high']:.3f})**,

y, bajo el modelo cuadrupolar ideal y tomando 1175 V como amplitud (no pico-a-pico),

**|Q|/m = {qm['estimate']:.3e} C kg⁻¹ (IC 95%: {qm['ci95_low']:.3e}–{qm['ci95_high']:.3e} C kg⁻¹)**.

La frecuencia secular de pequeña amplitud predicha es **{s['predicted_secular_frequency_hz']:.2f} Hz**. Estas magnitudes son *estimaciones dependientes del modelo*: la geometría exacta, convención de voltaje, tiempo de exposición y proyección 3D no están documentados en los archivos.

## Datos y resultados observables

- Resolución: 640×480 px; codec H.264.
- Duración por video: {meta.duration_s.min():.2f}–{meta.duration_s.max():.2f} s.
- El nulo de RF se ajustó por separado en cada video para absorber desplazamientos de cámara. El residuo perpendicular mediano entre videos es {s['rf_null_line_median_residual_px_between_videos']:.1f} px. El ajuste global mostrado sólo como diagnóstico queda en x={s['rf_null_px_global_diagnostic'][0]:.1f} px, y={s['rf_null_px_global_diagnostic'][1]:.1f} px.
- Ancho transversal mediano de las trazas: {s['minor_width_px']['median']:.2f} px (IC bootstrap entre videos {s['minor_width_px']['ci95_low']:.2f}–{s['minor_width_px']['ci95_high']:.2f} px).
- Si se fuerza el diámetro nominal de 30 µm como regla, la escala resulta {s['nominal_scale_um_per_px']:.2f} µm/px. Es sólo orientativa: desenfoque, PSF y profundidad de campo ensanchan la imagen.
- {freq_text}

![Resumen cuantitativo](quantitative_summary.png)

![Espectros de tracks](track_spectra.png)

## Modelo y ecuaciones

Para un cuadrupolo ideal sin componente DC se usa la ecuación de Mathieu. Con Ω=2πf_RF,

`q = 2 Q V_RF / (m r0² Ω²)`.

En la aproximación |q|≪1, `x(t) ≈ u(t)[1 − (q/2) cos(Ωt)]`. La excursión pico-a-pico de micromovimiento es entonces `L ≈ |q| |u|`; por eso cada detección entrega `q_i = L_i/r_i`. Se corrigió el ancho óptico mediante `L_i = sqrt(major_i² − minor_i²)`. Sólo se aceptaron trazas alargadas, con r≥20 px, desalineación radial ≤30° y 0.01<q<1.2. La mediana se calculó primero por video y el IC remuestreando videos completos, para no tratar miles de cuadros correlacionados como observaciones independientes.

La conversión es `|Q|/m = q r0² Ω²/(2 V_RF)`. La frecuencia secular aproximada es `f_sec ≈ |q| f_RF/(2 sqrt(2))`.

## Procesamiento y decisiones metodológicas

1. Se tomó el canal rojo, se restó un fondo gaussiano local (σ=15 px) y se aplicó umbral adaptativo.
2. Los componentes conexos se describieron por centroide ponderado por intensidad y PCA ponderado; los percentiles 2–98% sobre el eje mayor definen la longitud robusta.
3. El nulo se ajustó minimizando las distancias perpendiculares a los ejes mayores de trazas alargadas.
4. Los centroides se enlazaron con asignación húngara (máximo 30 px/cuadro, hueco máximo 2 cuadros). Los espectros usan Welch y excluyen ±0.35 Hz alrededor del alias esperado de 50 Hz, situado cerca de 7.1 Hz por el muestreo de ~21.45 fps.

## Limitaciones e incertidumbres no incluidas en el IC estadístico

- **Voltaje:** si 1175 V es pico-a-pico y no amplitud, |Q|/m se duplica. Si es RMS, cambia por 1/√2 respecto de la convención adoptada.
- **Exposición:** `q=L/r` supone que la exposición cubre al menos un período RF (20 ms). Sin metadata de shutter, una exposición menor subestima L y q.
- **Geometría:** se asumió el factor de campo cuadrupolar ideal asociado a r0=8.9 mm. Electrodos anulares reales requieren un factor geométrico obtenido por simulación/calibración.
- **Proyección:** la cámara mide 2D; movimiento fuera del plano y perspectiva sesgan longitudes y radios.
- **Escala espacial:** no hay patrón métrico visible. No se reportan velocidades o amplitudes absolutas como mediciones; la escala basada en 30 µm es nominal.
- **Carga individual:** los videos permiten Q/m, no Q y m por separado. Para convertir habría que conocer densidad/masa de cada espora; además la dispersión de tamaño domina el error.
- **Conversión paramétrica a carga:** para una esfera de 30 µm, `m = {mass_per_density:.3e} ρ kg` (ρ en kg/m³) y el resultado central implica `|Q| = {charge_per_density:.3e} ρ C = {elementary_per_density:.1f} ρ cargas elementales`. Por ejemplo, si ρ=1000 kg/m³: m≈14.1 ng, |Q|≈{charge_per_density*1e18:.2f} fC≈{elementary_per_density*1000:.2e} e. Este ejemplo no es una medición porque no se conoce la densidad efectiva de cada espora.
- **Signo:** la dinámica observada da |Q|/m, no el signo de Q.

## Archivos reproducibles

- `analyze_experiment.py`: pipeline completo.
- `video_metadata.csv`, `detections.csv`, `trace_measurements.csv`: datos derivados.
- `q_by_video.csv`, `rf_null_by_video.csv`, `track_frequencies.csv`, `summary.json`: resultados numéricos.
- `contact_sheet.png` y `sequence_*.png`: inspección visual.

Ejecutar con Python 3.12 y `numpy scipy pandas matplotlib opencv-python-headless`: `python analyze_experiment.py`.
"""
    (OUT / "REPORT.md").write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
