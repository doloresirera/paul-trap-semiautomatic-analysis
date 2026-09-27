from pathlib import Path
import csv

import cv2
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import least_squares


ROOT = Path(__file__).resolve().parent


def skeletonize(binary: np.ndarray) -> np.ndarray:
    """Adelgazamiento Zhang-Suen, para no depender de scikit-image."""
    image = binary.astype(np.uint8).copy()
    changed = True
    while changed:
        changed = False
        for phase in (0, 1):
            p = np.pad(image, 1)
            p2 = p[:-2, 1:-1]
            p3 = p[:-2, 2:]
            p4 = p[1:-1, 2:]
            p5 = p[2:, 2:]
            p6 = p[2:, 1:-1]
            p7 = p[2:, :-2]
            p8 = p[1:-1, :-2]
            p9 = p[:-2, :-2]
            neigh = p2 + p3 + p4 + p5 + p6 + p7 + p8 + p9
            transitions = np.stack(
                [
                    (p2 == 0) & (p3 == 1), (p3 == 0) & (p4 == 1),
                    (p4 == 0) & (p5 == 1), (p5 == 0) & (p6 == 1),
                    (p6 == 0) & (p7 == 1), (p7 == 0) & (p8 == 1),
                    (p8 == 0) & (p9 == 1), (p9 == 0) & (p2 == 1),
                ], axis=0
            ).sum(axis=0)
            common = (image == 1) & (neigh >= 2) & (neigh <= 6) & (transitions == 1)
            if phase == 0:
                remove = common & ((p2 * p4 * p6) == 0) & ((p4 * p6 * p8) == 0)
            else:
                remove = common & ((p2 * p4 * p8) == 0) & ((p2 * p6 * p8) == 0)
            if np.any(remove):
                image[remove] = 0
                changed = True
    return image.astype(bool)


def video_metadata(path: Path) -> dict:
    cap = cv2.VideoCapture(str(path))
    fps = cap.get(cv2.CAP_PROP_FPS)
    frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()
    return {
        "fps": fps,
        "frames": frames,
        "seconds": frames / fps,
        "width": width,
        "height": height,
    }


def read_frame(path: Path, index: int) -> np.ndarray:
    cap = cv2.VideoCapture(str(path))
    cap.set(cv2.CAP_PROP_POS_FRAMES, index)
    ok, frame = cap.read()
    cap.release()
    if not ok:
        raise RuntimeError(f"No se pudo leer {path.name}, frame {index}")
    return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)


def make_overview(videos: list[Path]) -> None:
    fig, axes = plt.subplots(len(videos), 3, figsize=(12, 3.15 * len(videos)))
    for row, path in enumerate(videos):
        meta = video_metadata(path)
        indices = [int(meta["frames"] * q) for q in (0.2, 0.5, 0.8)]
        for ax, idx in zip(axes[row], indices):
            ax.imshow(read_frame(path, idx))
            ax.set_title(f"{path.stem[-11:]} | frame {idx}", fontsize=9)
            ax.axis("off")
    fig.tight_layout()
    fig.savefig(ROOT / "overview_videos.png", dpi=150)
    plt.close(fig)


def sampled_indices(frame_count: int, n: int = 40, seed: int = 20260926) -> np.ndarray:
    """Muestreo aleatorio estratificado: un frame por intervalo temporal."""
    rng = np.random.default_rng(seed)
    edges = np.linspace(0, frame_count, n + 1, dtype=int)
    return np.array([rng.integers(a, max(a + 1, b)) for a, b in zip(edges[:-1], edges[1:])])


def skeleton_length(skel: np.ndarray) -> tuple[float, int, int]:
    """Longitud 8-conexa; devuelve longitud, extremos y nodos ramificados."""
    yy, xx = np.nonzero(skel)
    pixels = set(zip(yy.tolist(), xx.tolist()))
    length = 0.0
    degrees = []
    forward = [(0, 1, 1.0), (1, -1, np.sqrt(2)), (1, 0, 1.0), (1, 1, np.sqrt(2))]
    all_neigh = [(dy, dx) for dy in (-1, 0, 1) for dx in (-1, 0, 1) if (dy, dx) != (0, 0)]
    for y, x in pixels:
        degrees.append(sum((y + dy, x + dx) in pixels for dy, dx in all_neigh))
        for dy, dx, weight in forward:
            if (y + dy, x + dx) in pixels:
                length += weight
    endpoints = sum(d == 1 for d in degrees)
    branches = sum(d > 2 for d in degrees)
    return length, endpoints, branches


def centerline_length(xs: np.ndarray, ys: np.ndarray) -> float:
    """Longitud de una línea media cuadrática sobre el eje principal."""
    points = np.column_stack((xs, ys)).astype(float)
    mean = points.mean(axis=0)
    eigval, eigvec = np.linalg.eigh(np.cov((points - mean).T))
    major = eigvec[:, np.argmax(eigval)]
    minor = eigvec[:, np.argmin(eigval)]
    u = (points - mean) @ major
    v = (points - mean) @ minor
    coef = np.polyfit(u, v, 2)
    grid = np.linspace(u.min(), u.max(), max(50, int(np.ptp(u) * 2)))
    transverse = np.polyval(coef, grid)
    centers = mean + np.outer(grid, major) + np.outer(transverse, minor)
    return float(np.linalg.norm(np.diff(centers, axis=0), axis=1).sum())


def detect_frame(rgb: np.ndarray, threshold: int = 40, method: str = "skeleton") -> list[dict]:
    red = rgb[:, :, 0]
    binary = (red > threshold).astype(np.uint8)
    count, labels, stats, centroids = cv2.connectedComponentsWithStats(binary, 8)
    found = []
    h, w = binary.shape
    for label in range(1, count):
        x, y, bw, bh, area = stats[label]
        if not 150 <= area <= 8000:
            continue
        ys, xs = np.nonzero(labels == label)
        cov = np.cov(np.vstack((xs, ys)))
        eig, vec = np.linalg.eigh(cov)
        elongation = np.sqrt(max(eig[-1], 1e-9) / max(eig[0], 1e-9))
        if elongation < 2.5:
            continue
        # Un objeto cortado por el cuadro no permite medir su longitud completa.
        if x <= 1 or y <= 1 or x + bw >= w - 1 or y + bh >= h - 1:
            continue
        if method == "skeleton":
            crop = labels[y : y + bh, x : x + bw] == label
            skel = skeletonize(crop)
            skel_len, endpoints, branches = skeleton_length(skel)
            length = skel_len
        else:
            endpoints = branches = 0
            length = centerline_length(xs, ys)
        if length < 10:
            continue
        if method == "skeleton" and (endpoints > 5 or branches > max(12, 0.08 * skel.sum())):
            continue
        cx, cy = centroids[label]
        found.append(
            {
                "x": float(cx),
                "y": float(cy),
                "L": float(length),
                "area": float(area),
                "elongation": float(elongation),
                "endpoints": endpoints,
                "branches": branches,
                "ux": float(vec[0, -1]),
                "uy": float(vec[1, -1]),
            }
        )
    return found


def collect_video(path: Path, threshold: int = 40, method: str = "skeleton") -> tuple[list[dict], list[int]]:
    meta = video_metadata(path)
    indices = sampled_indices(meta["frames"])
    cap = cv2.VideoCapture(str(path))
    records = []
    for idx in indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(idx))
        ok, bgr = cap.read()
        if not ok:
            continue
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        for item in detect_frame(rgb, threshold, method):
            item.update(frame=int(idx))
            records.append(item)
    cap.release()
    return records, indices.tolist()


def fit_center(records: list[dict], robust: bool = False) -> dict:
    x = np.array([r["x"] for r in records])
    y = np.array([r["y"] for r in records])
    length = np.array([r["L"] for r in records])

    def residual(par):
        xc, yc, c = par
        radius = np.hypot(x - xc, y - yc)
        return length - c * radius

    starts = [
        [np.median(x), max(0, np.percentile(y, 5) - 30), 0.5],
        [280, 75, 0.5],
        [320, 0, 0.5],
        [np.mean(x), 240, 0.5],
    ]
    fits = [
        least_squares(
            residual,
            start,
            bounds=([0, -240, 0.02], [640, 480, 1.5]),
            loss="soft_l1" if robust else "linear",
            f_scale=8,
        )
        for start in starts
    ]
    fit = min(fits, key=lambda f: np.sum(residual(f.x) ** 2))
    xc, yc, slope = fit.x
    radius = np.hypot(x - xc, y - yc)
    ci = length / radius
    pred = slope * radius
    ss_res = np.sum((length - pred) ** 2)
    ss_tot = np.sum((length - np.mean(length)) ** 2)
    angles = np.unwrap(np.sort(np.arctan2(y - yc, x - xc)))
    gaps = np.diff(np.r_[angles, angles[0] + 2 * np.pi])
    coverage = 360 - np.degrees(np.max(gaps))
    return {
        "xc": xc,
        "yc": yc,
        "slope": slope,
        "R": radius,
        "ci": ci,
        "mean_c": float(np.mean(ci)),
        "sd_c": float(np.std(ci, ddof=1)),
        "r2": 1 - ss_res / ss_tot,
        "coverage": coverage,
        "residual": length - pred,
    }


def analyze_all(videos: list[Path]) -> None:
    rows = []
    for path in videos:
        records, indices = collect_video(path)
        if len(records) < 6:
            rows.append({"video": path.name, "n": len(records)})
            continue
        result = fit_center(records)
        rows.append(
            {
                "video": path.name,
                "n": len(records),
                "xc": result["xc"],
                "yc": result["yc"],
                "c_fit": result["slope"],
                "c_mean": result["mean_c"],
                "sd_c": result["sd_c"],
                "r2": result["r2"],
                "coverage_deg": result["coverage"],
            }
        )
    fields = ["video", "n", "xc", "yc", "c_fit", "c_mean", "sd_c", "r2", "coverage_deg"]
    with (ROOT / "screening_all_videos.csv").open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    for row in rows:
        print(row)


def robust_records(path: Path, threshold: int = 26) -> list[dict]:
    records, _ = collect_video(path, threshold, "centerline")
    # Al bajar el umbral para unir segmentos, el área de fondo de cada objeto
    # crece; 250 px evita reintroducir fragmentos que a t=40 apenas superan 150.
    return [r for r in records if r["area"] >= 250]


def c_values(records: list[dict], center: tuple[float, float]) -> np.ndarray:
    return np.array([r["L"] / np.hypot(r["x"] - center[0], r["y"] - center[1]) for r in records])


def frame_bootstrap(records: list[dict], center: tuple[float, float], draws: int = 1000) -> float:
    rng = np.random.default_rng(1701)
    frames = np.unique([r["frame"] for r in records])
    values = []
    by_frame = {f: [r for r in records if r["frame"] == f] for f in frames}
    for _ in range(draws):
        picked = rng.choice(frames, len(frames), replace=True)
        sample = [r for f in picked for r in by_frame[f]]
        values.append(np.median(c_values(sample, center)))
    return float(np.std(values, ddof=1))


def final_analysis(videos: list[Path]) -> list[dict]:
    center = (286.85, 76.05)  # promedio de los dos centros publicados
    rng = np.random.default_rng(314159)
    factor = (8.90e-3) ** 2 * (2 * np.pi * 50) ** 2 / (4 * 1175)
    factor_rel_error = np.hypot(2 * 0.50 / 8.90, 24 / 1175)
    rows = []
    cached = {}
    for path in videos:
        variants = {}
        for threshold in (24, 26, 28):
            variants[threshold] = robust_records(path, threshold)
        records = variants[26]
        ci = c_values(records, center)
        c = float(np.median(ci))
        boot = frame_bootstrap(records, center)
        threshold_cs = [float(np.median(c_values(variants[t], center))) for t in (24, 26, 28)]
        threshold_error = (max(threshold_cs) - min(threshold_cs)) / 2
        center_cs = []
        for _ in range(1000):
            shifted = (center[0] + rng.normal(0, 5), center[1] + rng.normal(0, 10))
            center_cs.append(np.median(c_values(records, shifted)))
        center_error = float(np.std(center_cs, ddof=1))
        c_error = float(np.sqrt(boot**2 + threshold_error**2 + center_error**2))
        qm = factor * c
        qm_error = qm * np.hypot(c_error / c, factor_rel_error)
        rows.append(
            {
                "video": path.stem.replace("WhatsApp Video 2026-09-26 at ", ""),
                "n": len(records), "c": c, "c_error": c_error,
                "c_sd": float(np.std(ci, ddof=1)), "frame_boot": boot,
                "threshold_error": threshold_error, "center_error": center_error,
                "qm_C_kg": qm, "qm_error_C_kg": qm_error,
            }
        )
        cached[path.name] = records

    fields = list(rows[0])
    with (ROOT / "resultados_por_video.csv").open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader(); writer.writerows(rows)

    labels = [r["video"].replace(" PM", "") for r in rows]
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), sharex=True)
    xx = np.arange(len(rows))
    ax1.errorbar(xx, [r["c"] for r in rows], yerr=[r["c_error"] for r in rows], fmt="o", capsize=3)
    ax1.axhline(0.908, color="tab:red", ls="--", label="límite de estabilidad")
    ax1.axhspan(0.464, 0.602, color="tab:green", alpha=.12, label="grupo 1 publicado")
    ax1.set_ylabel("c"); ax1.grid(alpha=.25); ax1.legend(fontsize=8)
    ax2.errorbar(xx, np.array([r["qm_C_kg"] for r in rows]) * 1e4,
                 yerr=np.array([r["qm_error_C_kg"] for r in rows]) * 1e4, fmt="o", capsize=3)
    ax2.set_ylabel(r"Q/m [$10^{-4}$ C/kg]"); ax2.set_xticks(xx, labels, rotation=45, ha="right")
    ax2.grid(alpha=.25); fig.tight_layout(); fig.savefig(ROOT / "resultados_por_video.png", dpi=180); plt.close(fig)

    chosen = [videos[2], videos[9]]
    fig, axes = plt.subplots(2, 2, figsize=(10, 8))
    for row_idx, path in enumerate(chosen):
        rec = cached[path.name]; ci = c_values(rec, center); radius = np.array([np.hypot(r["x"]-center[0], r["y"]-center[1]) for r in rec]); length = np.array([r["L"] for r in rec]); cmed=np.median(ci)
        axes[row_idx, 0].hist(ci, bins=18, color="tab:blue", alpha=.75)
        axes[row_idx, 0].axvline(cmed, color="k", ls="--", label=f"mediana={cmed:.3f}")
        axes[row_idx, 0].set_xlabel("c_i=L_i/R_i"); axes[row_idx, 0].set_ylabel("conteo"); axes[row_idx, 0].legend()
        axes[row_idx, 1].scatter(radius, length, s=12, alpha=.55)
        grid=np.linspace(0,radius.max(),100); axes[row_idx,1].plot(grid,cmed*grid,'k--',label=f"L={cmed:.3f}R")
        axes[row_idx,1].set_xlabel("R [px]"); axes[row_idx,1].set_ylabel("L [px]"); axes[row_idx,1].legend()
        axes[row_idx,0].set_title(path.stem[-11:]); axes[row_idx,1].set_title(path.stem[-11:])
    fig.tight_layout(); fig.savefig(ROOT / "diagnostico_dos_videos.png", dpi=180); plt.close(fig)
    return rows


if __name__ == "__main__":
    files = sorted(ROOT.glob("*.mp4"))
    if not (ROOT / "overview_videos.png").exists():
        make_overview(files)
    rows = final_analysis(files)
    for row in rows:
        print(row)
