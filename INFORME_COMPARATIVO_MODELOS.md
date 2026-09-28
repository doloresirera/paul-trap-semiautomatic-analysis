# Comparación de cuatro casos: gpt-5.6-sol default y GPT-6-Luna medium

Este documento compara los análisis guardados en [`agent-results/`](agent-results/) para los cuatro casos de la trampa de Paul. Los nombres de los modelos corresponden a los **directorios del repositorio**. La comparación se basa en sus informes, tablas y figuras; no vuelve a procesar los videos.

También están disponibles una [síntesis ilustrada en PDF de cuatro páginas](agent-results/comparacion_4_casos_modelos.pdf) y su [versión HTML](agent-results/comparacion_4_casos_modelos.html).

## Cómo interpretar cada caso

### Caso 1: reproducir dos grupos del informe experimental

Sol muestrea 40 cuadros por video, mide la longitud de las trazas mediante una línea media cuadrática y resume `c = L/R` con una mediana. Asocia dos videos con los grupos originales y obtiene valores cercanos a los publicados: `8,78` frente a `8,7`, y `8,80` frente a `8,5`, todos en unidades de `10⁻⁴ C/kg`. La asociación de los archivos no puede demostrarse completamente porque el informe experimental no registra sus nombres. Además, el cálculo **usa como calibración los centros del informe**, de modo que el centro no se determinó de manera independiente. Véanse el [reporte](agent-results/caso-1-codex-reanalysis%20gpt-5.6-sol%20default/REPORTE_REANALISIS.md) y los [resultados por video](agent-results/caso-1-codex-reanalysis%20gpt-5.6-sol%20default/resultados_por_video.csv).

Luna mide las trazas por esqueletización y ajusta centro y pendiente simultáneamente. Los centros obtenidos varían demasiado y los ajustes muestran poca linealidad; **0 de 11 videos** cumple a la vez sus criterios de linealidad, estabilidad del centro y límite físico. Sus valores por video son diagnósticos, no mediciones aceptadas. Véanse el [informe](agent-results/caso%201%20GPT-6-Luna%20medium/informe_reanalisis.html) y la [tabla](agent-results/caso%201%20GPT-6-Luna%20medium/resultados_videos.csv).

La diferencia decisiva es **cómo se conoce el centro de la trampa**. Este caso no permite concluir que un algoritmo mida mejor `Q/m` en general: uno fija el centro a partir de información publicada y el otro intenta estimarlo con las trazas.

### Caso 2: partir de 21 videos y un contexto físico breve

Sol corrige el ancho óptico de las trazas, estima el nulo de RF por video, sigue componentes y analiza sus espectros. La mediana geométrica da `q = 0,200` (IC 95 % entre videos: `0,193–0,235`) y una conversión condicional `|Q|/m = 6,646 × 10⁻⁴ C/kg` (IC 95 %: `6,418–7,825 × 10⁻⁴ C/kg`). La frecuencia secular de `3,53 Hz` es una **predicción del modelo**: los picos observados no la confirman de forma independiente y robusta. Véanse el [reporte](agent-results/caso-2-codex-analysis%20gpt-5.6-sol%20default/REPORT.md) y el [resumen numérico](agent-results/caso-2-codex-analysis%20gpt-5.6-sol%20default/summary.json).

Luna usa una sola segmentación y aproxima la longitud mediante el eje principal de los píxeles de cada traza: `Lₚ꜀ₐ = √(12λ₁)`. Conserva seis videos después de sus filtros geométricos y reporta `Q/m = (6,5 ± 1,9) × 10⁻⁴ C/kg`; la dispersión entre videos domina esa incertidumbre. Esta longitud por PCA es simple de calcular, pero pierde información de curvatura. Véanse el [resumen](agent-results/caso%202%20GPT-6-Luna%20medium/README.md) y el [informe visual](agent-results/caso%202%20GPT-6-Luna%20medium/informe_reanalisis.html).

**Aquí está la comparación numérica más directa entre modelos:** los valores centrales de `Q/m` son similares. El intervalo de Sol es un IC 95 % entre videos; el `±` de Luna es la incertidumbre reportada por su propio procedimiento. Su solapamiento no equivale a una prueba controlada de igualdad entre métodos.

### Caso 3: detectar cuándo el ajuste no es defendible

Sol implementa un análisis automático del método `L = cR` sobre **11 videos**. Detecta 519 trazas, pero ningún video cumple simultáneamente sus controles de cobertura angular, estabilidad del centro y calidad del ajuste. Por eso muestra `Q/m` individuales sólo como diagnósticos. Véanse el [resumen](agent-results/caso%203%20gpt-5.6-sol%20default/README.md) y la [tabla por video](agent-results/caso%203%20gpt-5.6-sol%20default/resultados_qm/resumen_videos.csv).

Luna aplica esqueletización Zhang–Suen, ajuste robusto de centro y `c`, y remuestreo bootstrap sobre **21 videos**. Ninguno supera a la vez cantidad mínima de trazas, estabilidad del centro y límite de estabilidad de `c`. Véanse el [resumen](agent-results/caso%203%20GPT-6-Luna%20medium/README.md) y las [decisiones por video](agent-results/caso%203%20GPT-6-Luna%20medium/decisiones.csv).

La coincidencia válida es **la decisión de no informar una medición final**. Al cambiar el conjunto de entrada, las cifras de trazas, distribuciones de `c` y tasas de descarte no constituyen una comparación video a video.

### Caso 4: longitud geométrica frente a señal espectral

Sol selecciona los dos videos vinculados a los grupos del informe y calcula la longitud a partir del área `A` y el perímetro `P` de cada silueta tubular: `L = ½√(P² − 4πA)`. Repite la segmentación con cinco umbrales y propaga las incertidumbres por cuadros y parámetros instrumentales. Obtiene `(8,99 ± 1,08)` y `(8,91 ± 1,07) × 10⁻⁴ C/kg`, a `+3,3 %` y `+4,8 %` de los grupos publicados. **Los centros geométricos también proceden del informe original**. Véanse el [reporte](agent-results/caso-4-codex-alternative-analysis%20gpt-5.6-sol%20default/REPORTE_METODO_ALTERNATIVO.md) y los [resultados](agent-results/caso-4-codex-alternative-analysis%20gpt-5.6-sol%20default/resultados.csv).

Luna procesa los **15.710 cuadros** de los 21 videos y busca una frecuencia secular en trayectorias seguidas automáticamente. De 1.036 candidatos preliminares, **ninguno** pasa simultáneamente los controles de duración, ajuste sinusoidal y resolución. En consecuencia, no convierte esos candidatos a `q` ni a `Q/m` finales. Véanse el [resumen](agent-results/caso%204%20GPT-6-Luna%20medium/README.md) y el [informe](agent-results/caso%204%20GPT-6-Luna%20medium/informe_reanalisis.html).

Los dos análisis **no estiman la misma magnitud con el mismo procedimiento**. El resultado geométrico condicionado de Sol no queda refutado por la falta de una señal espectral aceptada en Luna; esta última sí muestra que la evidencia dinámica disponible no sostiene una confirmación independiente.

## Límites comunes

- **Conversión física condicional.** Los análisis emplean una frecuencia RF de `50 Hz`, una tensión nominal de `1175 V` y un radio de `8,9 mm` bajo un modelo de campo ideal. La convención de amplitud de tensión, la geometría real de los electrodos y la exposición de la cámara pueden modificar `Q/m`.
- **Centro e imagen.** Una cobertura angular escasa permite que centros y pendientes diferentes ajusten trazas parecidas. La cámara registra una proyección bidimensional; el ancho óptico, las fusiones y la fragmentación alteran la longitud medida.
- **Observaciones repetidas.** Varias trazas pueden pertenecer a la misma partícula en cuadros diferentes. Remuestrear trazas como si fueran partículas independientes subestimaría la incertidumbre.
- **Alcance de la comparación.** Los casos 1 y 4 de Sol usan centros publicados; en el caso 3 cambian los videos; y en el caso 4 cambia la pregunta física. No corresponde promediar los cuatro valores ni ordenar los modelos por «exactitud» a partir de esta tabla.
- **Costo y velocidad.** El repositorio no conserva tiempos de ejecución, tokens, precios ni hardware comparables. Una menor cantidad de umbrales o pasos describe el algoritmo, pero no demuestra un menor costo o latencia del modelo.

## Conclusión

El **caso 2** muestra valores centrales de `Q/m` cercanos con dos formas diferentes de medir las trazas, aunque sigue pendiente la calibración física y la validación espectral. En el **caso 3**, ambos análisis rechazan un resultado final, sobre conjuntos de datos distintos. En los **casos 1 y 4**, los valores de Sol concuerdan con el informe experimental bajo centros geométricos tomados de ese mismo informe; Luna aplica controles o una prueba dinámica diferentes y no informa un `Q/m` final.
