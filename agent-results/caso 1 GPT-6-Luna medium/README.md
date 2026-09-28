# Caso 1 — reanálisis GPT-6-Luna medium

Reanálisis de los 11 videos de licopodio entregados en `caso 1 peor`. El informe visual principal es [informe_reanalisis.html](informe_reanalisis.html).

## Resultado

El procesamiento automático produjo estimaciones exploratorias, pero ningún video superó conjuntamente los controles de linealidad, estabilidad del centro y límite de estabilidad. Los valores de `c` y `Q/m` de la tabla no deben interpretarse como mediciones confirmadas; el informe HTML documenta por qué.

## Archivos

- `analisis_reproducible.py`: detección, ajuste y generación de figuras. Para repetir el procesamiento, colocar los videos MP4 junto al script y ejecutar `python analisis_reproducible.py` con OpenCV, NumPy, SciPy, Matplotlib y Pillow instalados.
- `resultados_videos.csv` y `resultados_videos.json`: valores y diagnósticos por video.
- `fig_*.png`: ajustes diagnósticos individuales y resumen de `c`.
- `contact_sheet.jpg`: cuadros representativos.
- `informe_reanalisis.html`: decisiones, diferencias frente al informe original y límites de interpretación.

## Parámetros clave

Se muestrearon 40 cuadros equiespaciados por video, con umbral 40 en el canal rojo; umbrales 35 y 45 se usaron para sensibilidad. Se filtraron componentes con área 150–8000 px² y relación de aspecto ≥2,5. Se ajustó `L = cR` junto con el centro. `Q/m` se calculó solo condicionalmente usando `f = 50 Hz`, `V = 1175 V` y `r₀ = 8,90 mm`, porque la frecuencia y la amplitud de RF no están completas en el contexto suministrado.

Los videos originales no se incluyen en este directorio; tampoco se incluyen los PDFs de entrada.
