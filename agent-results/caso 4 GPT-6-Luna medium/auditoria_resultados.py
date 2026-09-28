"""Create the audited report from the full-frame analysis outputs.

This deliberately distinguishes direct image observables from model-dependent
quantities. The first pass produces exploratory spectral candidates, but this
script applies the conservative acceptance criteria documented in report.md.
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results"
FIG = OUT / "figures"

def main():
    m = pd.read_csv(OUT / "video_metadata.csv")
    d = pd.read_csv(OUT / "detections.csv")
    t = pd.read_csv(OUT / "tracks.csv")
    c = pd.read_csv(OUT / "centers.csv")
    pars = json.loads((OUT / "analysis_parameters.json").read_text(encoding="utf-8"))

    # High-confidence image detections. The full detections.csv is retained;
    # this subset is used for robust descriptive statistics.
    d["high_confidence"] = (d.area_px >= 100) & (d.path_length_px >= 20) & (d.peak_hp >= 60) & (d.aspect_ratio >= 1.5)
    q = d[d.high_confidence].copy()
    q.to_csv(OUT / "high_confidence_detections.csv", index=False)

    # Candidate frequencies are kept, but no track passes all physical-quality criteria.
    t["relative_sinusoid_residual"] = t.rms_residual_px / t.amp_px
    raw_spec = t[np.isfinite(t.f_peak_hz)].copy()
    accepted = raw_spec[(raw_spec.duration_track_s >= 5) &
                        (raw_spec.relative_sinusoid_residual <= 0.70) &
                        (raw_spec.f_peak_hz >= 3 * raw_spec.f_resolution_hz)].copy()
    raw_spec.to_csv(OUT / "spectral_candidates.csv", index=False)
    accepted.to_csv(OUT / "accepted_physical_tracks.csv", index=False)

    # Per-video descriptive table, including zero-detection frames in the mean.
    rows = []
    for _, row in m.iterrows():
        vid = int(row.video_id)
        sub = q[q.video_id == vid]
        counts = sub.groupby("frame").size().reindex(range(int(row.frames)), fill_value=0)
        rows.append({
            "video_id": vid, "video": row["name"],
            "frames": int(row.frames), "fps": row.fps, "duration_s": row.duration_s,
            "high_conf_detections": len(sub),
            "high_conf_mean_streaks_per_frame": counts.mean(),
            "high_conf_median_streaks_per_frame": counts.median(),
            "path_median_px": sub.path_length_px.median() if len(sub) else np.nan,
            "path_p05_px": sub.path_length_px.quantile(.05) if len(sub) else np.nan,
            "path_p95_px": sub.path_length_px.quantile(.95) if len(sub) else np.nan,
            "area_median_px": sub.area_px.median() if len(sub) else np.nan,
            "peak_median_hp": sub.peak_hp.median() if len(sub) else np.nan,
        })
    summary = pd.DataFrame(rows)
    summary.to_csv(OUT / "per_video_summary.csv", index=False)

    scale_mm_px = pars["mm_per_px_assumed"]
    fps = m.fps.median()
    stats = {
        "n_videos": int(len(m)), "n_frames": int(m.frames.sum()),
        "duration_s": float(m.duration_s.sum()), "fps_median": float(fps),
        "fps_sd_between_videos": float(m.fps.std()), "detections_all": int(len(d)),
        "detections_high_confidence": int(len(q)), "high_conf_fraction": float(len(q)/len(d)),
        "tracks_all": int(len(t)), "spectral_candidates_raw": int(len(raw_spec)),
        "spectral_tracks_accepted": int(len(accepted)),
        "path_p05_px": float(q.path_length_px.quantile(.05)),
        "path_median_px": float(q.path_length_px.median()),
        "path_p95_px": float(q.path_length_px.quantile(.95)),
        "chord_median_px": float(q.chord_px.median()),
        "area_median_px": float(q.area_px.median()),
        "scale_assumed_mm_px": scale_mm_px,
        "path_median_assumed_mm": float(q.path_length_px.median()*scale_mm_px),
        "path_p05_assumed_mm": float(q.path_length_px.quantile(.05)*scale_mm_px),
        "path_p95_assumed_mm": float(q.path_length_px.quantile(.95)*scale_mm_px),
        "speed_median_if_exposure_frame_mm_s": float(q.path_length_px.median()*scale_mm_px*fps),
        "speed_p05_if_exposure_frame_mm_s": float(q.path_length_px.quantile(.05)*scale_mm_px*fps),
        "speed_p95_if_exposure_frame_mm_s": float(q.path_length_px.quantile(.95)*scale_mm_px*fps),
        "center_fit_residual_min_px": float(c.center_fit_median_residual_px.min()),
        "center_fit_residual_median_px": float(c.center_fit_median_residual_px.median()),
        "center_fit_residual_max_px": float(c.center_fit_median_residual_px.max()),
    }
    (OUT / "final_summary.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")

    # Clean quantitative summary figure.
    fig, ax = plt.subplots(1, 3, figsize=(15, 4.5), constrained_layout=True)
    ax[0].plot(summary.video_id, summary.path_median_px, "o-", color="tab:red")
    ax[0].fill_between(summary.video_id, summary.path_p05_px, summary.path_p95_px, alpha=.2, color="tab:red")
    ax[0].set(xlabel="video id (chronological)", ylabel="streak length [px]", title="High-confidence streak length")
    ax[0].grid(alpha=.25)
    ax[1].bar(summary.video_id, summary.high_conf_mean_streaks_per_frame, color="tab:blue")
    ax[1].set(xlabel="video id", ylabel="mean streaks/frame", title="Detected occupancy")
    ax[1].grid(alpha=.25)
    ax[2].hist(q.path_length_px, bins=50, color="tab:green", alpha=.8)
    ax[2].axvline(q.path_length_px.median(), color="k", ls="--", label=f"median={q.path_length_px.median():.1f} px")
    ax[2].set(xlabel="streak length [px]", ylabel="detections", title="Pooled distribution")
    ax[2].legend(fontsize=8); ax[2].grid(alpha=.25)
    fig.savefig(FIG / "final_quantitative_summary.png", dpi=180); plt.close(fig)

    md = f"""# Análisis cuantitativo de micromoción en trampa de Paul

## Resultado principal

Se procesaron **{stats['n_videos']} videos**, **{stats['n_frames']:,} frames** y **{stats['duration_s']:.1f} s** nominales, con 640×480 px y {stats['fps_median']:.4f} ± {stats['fps_sd_between_videos']:.4f} Hz entre archivos. Se detectaron {stats['detections_all']:,} componentes y {stats['detections_high_confidence']:,} trazas de alta confianza ({100*stats['high_conf_fraction']:.1f}%).

Las magnitudes que sí quedan establecidas por los datos son la geometría de las trazas en píxeles, su evolución frame a frame y la estadística de ocupación. El largo de traza de alta confianza es **{stats['path_median_px']:.2f} px** (P05–P95: {stats['path_p05_px']:.2f}–{stats['path_p95_px']:.2f} px); la cuerda mediana es {stats['chord_median_px']:.2f} px y el área mediana {stats['area_median_px']:.0f} px². Ver [resumen cuantitativo](figures/final_quantitative_summary.png) y [detecciones de ejemplo](figures/detections_examples.png).

## Cómo se procesó

- Se leyó cada MP4 con OpenCV. La frecuencia efectiva del contenedor fue usada para construir el eje temporal: mediana {stats['fps_median']:.4f} Hz.
- Se extrajo el canal rojo, se restó un fondo gaussiano σ={pars['bg_sigma_px']:g} px y se umbraló a {pars['hp_threshold']} cuentas. Se cerraron huecos de 3×3 px y se descartaron componentes de área menor que {pars['min_area_px']} px.
- Para cada componente se calculó centroide ponderado, eje principal por PCA, ancho transversal, orientación, cuerda y línea central. La línea central se obtuvo por bins a lo largo del eje principal y conserva curvatura; sus atributos están en [detections.csv](detections.csv).
- Se intentó asociar centroides mediante asignación húngara, distancia máxima {pars['max_link_px']:g} px y hasta {pars['max_gap_frames']} frames perdidos. Hay 10.433 tracks; se conservan también los tracks cortos y sus limitaciones.
- La máscara de alta confianza usada para estadística descriptiva exige área ≥100 px², longitud ≥20 px, pico del residuo ≥60 y aspect ratio ≥1,5. El CSV completo no se elimina: [high_confidence_detections.csv](high_confidence_detections.csv).

## Longitudes y velocidades: qué es medible

La longitud observada es una distancia recorrida/integrada durante la exposición. Si `s` es la escala lineal y τ el tiempo de exposición:

`distancia durante la exposición = L_px · s`,   `velocidad media ≈ L_px · s / τ`.

No hay tiempo de exposición ni regla en los MP4. Por lo tanto, el valor absoluto no está calibrado. Solo como traducción **condicional**, se adoptó `s = r0/P95`, con `r0=8,9 mm` y P95 del radio de extremo de las trazas; da `s={scale_mm_px:.5f} mm/px`. Bajo esa hipótesis, la longitud mediana sería {stats['path_median_assumed_mm']:.3f} mm (P05–P95: {stats['path_p05_assumed_mm']:.3f}–{stats['path_p95_assumed_mm']:.3f} mm) por exposición.

Si además se fuerza τ=1/fps, que es la exposición máxima compatible con un frame rate continuo y no un dato del archivo, la velocidad mínima correspondiente sería {stats['speed_median_if_exposure_frame_mm_s']:.1f} mm/s (P05–P95: {stats['speed_p05_if_exposure_frame_mm_s']:.1f}–{stats['speed_p95_if_exposure_frame_mm_s']:.1f} mm/s). Para otra exposición, esos valores se multiplican por `(1/fps)/τ`.

## Búsqueda de frecuencia secular

Se calcularon periodogramas de x(t) e y(t) para 1.036 tracks suficientemente largos para el algoritmo preliminar. La frecuencia del pico bruto tiene mediana 0,364 Hz y resolución mediana 0,311 Hz; la mayoría de los picos cae en el primer bin o en trayectorias con cambios de componente. La figura [track_spectra.png](figures/track_spectra.png) muestra el problema. Los caminos de los candidatos largos se inspeccionan en [candidate_track_paths.png](figures/candidate_track_paths.png).

Con el filtro conservador duración ≥5 s, residuo sinusoidal/RMS de ajuste ≤0,70 y pico separado al menos 3 bins de resolución, quedan **{stats['spectral_tracks_accepted']} tracks aceptables**. Por eso no se reporta una frecuencia secular físicamente identificada; los picos están disponibles en [spectral_candidates.csv](spectral_candidates.csv) como candidatos exploratorios, no como mediciones.

## Modelo de trampa de Paul y por qué no se obtiene Q/m aquí

Para el modelo ideal usado como referencia:

`x¨ + [Q V_AC/(m r0²)] cos(Ωt) x = 0`

`q = 2 Q V_AC/(m r0² Ω²)`

En el límite q pequeño, a=0:

`ω_sec ≈ |q| Ω/(2√2)`,   `|q| = 2√2 f_sec/f_RF`,

`|Q/m| = |q| r0² Ω²/(2 V_AC)`.

Con los datos suministrados, `V_AC=1175 V`, `f_RF=50 Hz`, `r0=8,9 mm`, el factor de conversión sería `Q/m = 0,00332669·q C/kg`, si el voltaje es amplitud de pico y la convención geométrica coincide con la ecuación anterior. Pero como no hay una frecuencia secular aceptada, **no hay una estimación defendible de q, Q/m, carga, rigidez k, energía o temperatura**.

Si en un futuro se obtiene una frecuencia fiable, puede usarse `m=ρπd³/6` con diámetro aproximado 30 µm, pero la densidad, forma, carga y orientación 3D de la espora no están medidas. La carga resultaría proporcional a `ρ d³`; la rigidez sería `k=m(2π f_sec)²`. También debe aclararse si 1175 V es RMS o pico, porque eso introduce un factor de √2 o 2 según la definición usada.

## Centro geométrico y limitaciones

Se ajustó exploratoriamente un punto a los ejes de las trazas para cada video. El residuo mediano entre rectas está entre {stats['center_fit_residual_min_px']:.1f} y {stats['center_fit_residual_max_px']:.1f} px (mediana global {stats['center_fit_residual_median_px']:.1f} px), demasiado grande para identificarlo sin ambigüedad como nulo de RF. [centers.csv](centers.csv) se entrega como diagnóstico, pero no se usan sus radios/alineamientos para afirmar una simetría de la trampa.

La cámara muestrea a ~21,46 Hz, por debajo de Nyquist para la excitación de 50 Hz: la micromoción RF no puede resolverse como serie temporal. La exposición, la escala px/mm, la densidad, la carga y la geometría 3D requieren datos adicionales. Componentes fusionadas, cruces, reflejos y background residual pueden sesgar áreas, longitudes y tracking.

## Archivos y reproducibilidad

- [video_metadata.csv](video_metadata.csv), [per_video_summary.csv](per_video_summary.csv): inventario y estadística por video.
- [detections.csv](detections.csv), [high_confidence_detections.csv](high_confidence_detections.csv): datos por traza/frame.
- [tracks.csv](tracks.csv), [spectral_candidates.csv](spectral_candidates.csv), [accepted_physical_tracks.csv](accepted_physical_tracks.csv): asociaciones y diagnóstico espectral.
- [physical_estimates.csv](physical_estimates.csv): conversiones Mathieu **condicionales** del primer pase; no deben interpretarse como resultados aceptados.
- [scripts/analyze_trap.py](../scripts/analyze_trap.py): pipeline completo; [scripts/finalize_report.py](../scripts/finalize_report.py): auditoría y reporte final.

Para repetir desde los videos: `python scripts/analyze_trap.py`; para regenerar este informe con los CSV existentes: `python scripts/finalize_report.py`.
"""
    (OUT / "report.md").write_text(md, encoding="utf-8")
    print(f"high_conf={len(q)} raw_spectral={len(raw_spec)} accepted={len(accepted)}")

if __name__ == "__main__":
    main()
