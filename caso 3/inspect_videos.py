"""Genera una hoja de contacto para inspeccion visual inicial (no realiza el analisis)."""
from pathlib import Path

import cv2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parent
videos = sorted(ROOT.glob("*.mp4"))
fig, axes = plt.subplots(len(videos), 5, figsize=(15, 2.6 * len(videos)))
for row, path in enumerate(videos):
    cap = cv2.VideoCapture(str(path))
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    for col, frac in enumerate((0.1, 0.3, 0.5, 0.7, 0.9)):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(frac * (n - 1)))
        ok, frame = cap.read()
        ax = axes[row, col]
        if ok:
            ax.imshow(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        ax.set_axis_off()
        if col == 0:
            ax.set_title(path.stem.replace("WhatsApp Video 2026-09-26 at ", ""), loc="left")
    cap.release()
fig.tight_layout()
fig.savefig(ROOT / "contact_sheet.png", dpi=130)
