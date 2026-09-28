# Caso 2.2 — modelo eficiente basado en momentos de imagen (PCA)

Este caso extiende conceptualmente el Caso 2: utiliza los mismos videos y el
flujo de análisis autónomo, pero cambia el estimador geométrico. La longitud
de cada traza se estima a partir del autovalor principal de sus píxeles, sin
esqueletización, contornos ni perímetros.

El resultado exploratorio es `Q/m = (6,5 ± 1,9) × 10⁻⁴ C/kg`.

El modelo es computacionalmente más eficiente que el del Caso 4 porque usa una
sola segmentación, una covarianza por componente y 300 remuestreos bootstrap;
no calcula cinco umbrales, perímetros digitales ni 4000 réplicas Monte Carlo.
Esto reduce el costo, pero no garantiza una incertidumbre menor.

El informe detallado está en [REPORTE_MODELO_EFICIENTE.md](REPORTE_MODELO_EFICIENTE.md).
