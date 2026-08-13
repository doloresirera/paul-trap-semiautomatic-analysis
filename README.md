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
