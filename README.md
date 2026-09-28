# Charge-to-mass ratio of lycopodium spores in a Paul trap

Determination of the charge-to-mass ratio (Q/m) of lycopodium particles
trapped in an annular Paul trap, from the analysis of micromotion recorded on
video. Coursework for Laboratorio 4 — Physics degree (Licenciatura en Ciencias
Físicas), Facultad de Ciencias Exactas y Naturales (FCEN), University of Buenos
Aires (UBA).

**Authors:** Sirera María Dolores, Paseri Milagros, Benedetti Anna.

> **Note.** This is an undergraduate lab project, not a finished tool. The code
> and approach are shared as a reference for anyone tackling a similar problem.
> The parameters are tuned to our experimental setup and must be re-adapted to
> each case (see below).
>
## **Project extension**

As the final project for the course "AI-assisted research: application to gravitational waves," taught by Matías Zaldarriaga in the second semester of 2026, the material from this experiment is used to test, at different levels, how AI reproduces or improves on the work carried out.

## The idea behind the method

A particle trapped in a Paul trap oscillates rapidly about its position, a
motion known as *micromotion*. The amplitude of this oscillation is zero at the
center of the trap and grows in proportion to the distance from that center.
Since the camera integrates many micromotion cycles during the exposure of each
frame, every particle leaves a **streak** whose length L is proportional to its
distance R from the center:

    L = c · R

The proportionality factor c (the Mathieu stability parameter) is obtained by
fitting this relation, and from it Q/m is derived via
Q/m = c·r0²·Ω²/(4·V_AC), with Ω = 2πf. Since c = L/R is a ratio of two lengths
measured on the same image, the method **does not require calibrating the
pixel-to-millimeter relation**: any conversion factor cancels out.

## Processing, step by step

For each frame of the video, the analysis performs the following steps, which
reproduce in code a workflow first developed manually in Fiji:

1. **Color channel selection.** The image is split into its red, green and blue
   channels, and the one that best separates the streaks from the background is
   used (in our case, red).

2. **Thresholding (binarization).** Every pixel brighter than a fixed threshold
   is marked as "streak" and the rest as "background". The result is a
   black-and-white image containing only the streaks.

3. **Filtering by shape and size.** Only the blobs with the size (area) and
   elongated shape typical of a streak are kept, discarding noise, reflections
   and fusions of several streaks.

4. **Skeletonization.** Each streak is reduced to a one-pixel-wide line running
   along its central axis, so its length can be measured independently of its
   thickness.

5. **Length measurement.** This skeleton is traversed, summing the distances
   between pixels, to obtain the arc length L of the streak (the arc is measured
   rather than the straight line between endpoints because the streaks are
   curved).

This processing is **semi-automatic**: the program proposes the streaks
detected in each frame, and the analyst accepts, discards or corrects the
selection, frame by frame.

### Determining the center

The center of the trap is not marked by hand: it is computed. Given the length
and position of many streaks, a least-squares fit finds the point from which
all lengths turn out proportional to their distances. That point is the center,
and it is used to compute the distance R of each streak.

To verify that the center is reliable, **bootstrap** is used: the center is
recomputed many times, each time using only a random subset of the streaks, and
the spread of the result is observed. If the center barely shifts, it is
reliable; if it jumps around, the streaks do not constrain it well and that
video is discarded.

### Uncertainty

The measurement error of each streak combines three sources: the choice of
threshold (affects the measured length), the skeletonization (slightly trims the
endpoints), and the uncertainty in the center position (affects the distance R).

## Example: what we work on

The `ejemplos/` folder contains some frames from a video, with the raw
micromotion streaks and with the detected skeleton overlaid, to illustrate the
input of the analysis.

<!-- Uncomment and adjust the filenames once you upload the images:
![Raw frame](ejemplos/frame_crudo.png)
![Detected streaks](ejemplos/frame_detectado.png)
-->

## Adapting it to your own images

The following parameters are specific to each setup and should **not** be copied
as-is, but chosen by looking at your own images:

- **Color channel.** The one that best separates your streaks from the
  background, depending on your illumination color.
- **Binarization threshold.** The most sensitive parameter: it directly affects
  the measured length. Choose it based on the brightness of your images and keep
  it **fixed** across all frames and videos.
- **Minimum and maximum area.**
- **Minimum elongation.**
- **Physical constants** (V_AC, frequency, r0). From your experimental setup.

### Recommendations

- Validate the center (bootstrap) before trusting any result.
- You need streaks spread out in angle and over a wide range of distances R.
- Values of c above the stability limit (~0.908) usually indicate a
  mislocated center, not badly measured streaks.
- Not every video is usable; discarding by objective criteria is part of the
  method.

## Environment

Python 3.13.9 (Anaconda), with OpenCV 4.13.0, NumPy 2.3.5, SciPy 1.16.3,
pandas 2.3.3, scikit-image 0.25.2 and Matplotlib 3.10.6.

## Results

Two sets of particles with a reliable center were analyzed:

| | Video 1 | Video 2 |
|---|---|---|
| N (streaks) | 86 | 113 |
| c | 0.53 ± 0.07 | 0.52 ± 0.06 |
| Q/m [C/kg] | (8.7 ± 1.0)×10⁻⁴ | (8.5 ± 1.0)×10⁻⁴ |
| Measurement error | 13 % | 11 % |
| σ (spread of c_i) | 0.09 | 0.08 |

## Case 1: reanalysis by an AI agent

As part of an evaluation of AI tools, Codex was given the report and 11 raw
videos and asked to reproduce the analysis without access to the original
code. The results, methodological decisions, figures, tabulated data, and
reproducible script are available in
[`agent-results/caso-1-codex-reanalysis/`](agent-results/caso-1-codex-reanalysis/REPORTE_REANALISIS.md).

This is an independent implementation rather than a replacement for the
original semi-automatic analysis. In particular, it documents differences
caused by manual streak correction, frame-level resampling, and propagation of
instrumental uncertainties.

A didactic explanation of the errors, assumptions, and improvements is
available as an [HTML document](agent-results/caso-1-codex-reanalysis/CASO_1_ERRORES_Y_MEJORAS.html).

## Case 2: autonomous analysis from raw videos

In a second evaluation, Codex was given 21 raw videos and only a short
experimental context containing the RF voltage and frequency, trap radius,
and nominal particle size. The agent autonomously developed the image
processing, tracking, spectral analysis, and physical inference pipeline.

The complete report, reproducible code, aggregate results, and figures are in
[`agent-results/caso-2-codex-analysis/`](agent-results/caso-2-codex-analysis/REPORT.md).

The analysis obtains `q = 0.200` (95% CI: 0.193–0.235) and, under an ideal
quadrupole model, `|Q|/m = 6.65×10⁻⁴ C kg⁻¹`. The `3.53 Hz` secular frequency
is a model prediction rather than an independent spectral identification. The
report explicitly separates statistical error from systematic uncertainties
due to exposure time, electrode geometry, voltage convention, and camera
projection.

### Case 2 — GPT-6-Luna medium

An analogous report using the efficient PCA image-moment model is available in
[`agent-results/caso 2 GPT-6-Luna medium/`](agent-results/caso%202%20GPT-6-Luna%20medium/informe_reanalisis.html). It reports the per-video results, the six retained videos, the generated figures, and the comparison with the original analysis.

## Case 3: automatic exploratory reanalysis

The [`agent-results/caso 3/`](agent-results/caso%203/) folder contains an independent implementation built from the written method and the raw videos. It includes the physical and methodological context, Python analysis code, detected-streak tables, diagnostic plots, and a final HTML report. The raw videos are not stored in the repository.

This run uses reproducible automatic rules for streak selection instead of the frame-by-frame human validation required by the original semi-automatic workflow. None of the videos passed all the predefined fit and center-stability criteria, so the per-video Q/m values are reported only as diagnostics and no combined physical result is claimed. Manual review of the proposed detections would be required to complete a faithful semi-automatic reanalysis.

## Case 4: alternative area–perimeter method

For this evaluation, Codex received the original report and all 21 raw videos
and was asked to develop a different method for calculating `Q/m`. Instead of
skeletonizing each streak, the alternative analysis estimates its length from
the segmented area and perimeter, applies reproducible automatic quality cuts,
and propagates uncertainty with frame-level bootstrap and Monte Carlo.

The full report, reproducible code, trace-level tables, and figures are in
[`agent-results/caso-4-codex-alternative-analysis/`](agent-results/caso-4-codex-alternative-analysis/REPORTE_METODO_ALTERNATIVO.md).

The method obtains `Q/m = (8.99 ± 1.08)×10⁻⁴ C kg⁻¹` for group 1 and
`Q/m = (8.91 ± 1.07)×10⁻⁴ C kg⁻¹` for group 2. The differences from the
original report, `+3.3%` and `+4.8%`, are not statistically significant.

## Case 2.2: efficient alternative model linked to Case 2

This repository also includes a follow-up to Case 2 using the same autonomous
analysis setting and raw videos, but with a more computationally efficient
geometric model. Instead of calculating contours,
perimeters, and five threshold realizations, it uses one segmentation and
estimates each streak length from the principal eigenvalue of the pixel
covariance matrix. It avoids skeletonization and pixel-graph traversal.

The exploratory result is `Q/m = (6.5 Â± 1.9)Ã—10â»â´ C kgâ»Â¹`. The larger
uncertainty is expected: PCA loses curvature information and the video-to-video
spread dominates the error. “More efficient” refers to computational cost and
model simplicity, not automatically higher accuracy.

The report, reproducible code, tables, and figures are available in
[`agent-results/caso-2.2-codex-efficient-pca-analysis/`](agent-results/caso-2.2-codex-efficient-pca-analysis/REPORTE_MODELO_EFICIENTE.md).
