# Caso 2.2 — análisis eficiente de `Q/m` mediante momentos de imagen

Como extensión del análisis autónomo del Caso 2, se aplicó un nuevo estimador
geométrico a los videos disponibles. El resultado exploratorio fue

\[
\boxed{Q/m=(6,5\pm1,9)\times10^{-4}\ \mathrm{C/kg}}.
\]

El informe original da aproximadamente `8,6×10⁻⁴ C/kg` y el Caso 4,
basado en área–perímetro, `8,95×10⁻⁴ C/kg`. La diferencia se explica porque
PCA mide una longitud proyectada y pierde información sobre la curvatura.

## Modelo

Para cada componente conexa se calculó la matriz de covarianza de las
coordenadas de sus píxeles. Si `lambda_1` es el autovalor mayor,

`L_PCA = sqrt(12 lambda_1)`.

El factor 12 corresponde a la varianza longitudinal de una barra uniforme.
Después se ajustó robustamente

`L_PCA = c sqrt((x-xc)^2 + (y-yc)^2)`

para obtener el centro y `c`, y se convirtió mediante

`Q/m = c r0^2 (2 pi f)^2/(4 V)`.

## Eficiencia

Frente al Caso 4, el algoritmo usa una sola umbralización, no calcula
perímetros digitales ni cinco realizaciones del umbral, y utiliza 300
bootstrap en lugar de 4000 réplicas Monte Carlo. “Más eficiente” se refiere al
costo computacional y a la simplicidad del modelo, no a una precisión
automáticamente superior.

## Comparación y limitaciones

El modelo PCA es sensible a la curvatura, fusiones y trazas incompletas. La
dispersión entre videos domina la incertidumbre y varios videos no determinan
un centro estable. Por esto el resultado debe interpretarse como una prueba de
robustez del observable `L/R`, no como una sustitución metrológica definitiva.

La comparación exacta con los grupos de 86 y 113 trazas no es posible porque
las coordenadas intermedias de la selección manual original no están en el
repositorio.

## Archivos

- `analisis_modelo_eficiente.py`: implementación reproducible.
- `resultado_final/resultados_por_video.csv`: resultados por video.
- `resultado_final/detecciones.csv`: detecciones individuales.
- `resultado_final/*.png`: figuras del ajuste.
