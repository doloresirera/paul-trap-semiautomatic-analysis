# Informe comparativo de modelos y estrategias de análisis

## 1. Resumen ejecutivo

Este informe compara las ejecuciones de análisis asistido por IA documentadas en el repositorio sobre videos de esporas de licopodio confinadas en una trampa de Paul. 

Los modelos identificables son **Codex** y **GPT-6-Luna medium**. Tampoco se registran tiempos de respuesta, tokens consumidos, precios ni hardware de ejecución. Por ello, la dimensión “eficiencia” se evalúa únicamente mediante la complejidad del método, el grado de automatización, el número de pasadas y la cantidad de información geométrica conservada; no se presentan costos o latencias inventados.

La conclusión general es que los enfoques más complejos producen una cadena de inferencia más rica, mejores diagnósticos y, en los casos adecuados, resultados cuantitativos compatibles con el informe original. Sin embargo, la complejidad no resuelve por sí sola los problemas de identificabilidad: el análisis espectral de Caso 2 no obtuvo una frecuencia secular independiente robusta y el análisis full-frame de Caso 4 no produjo tracks físicamente aceptados. Los enfoques compactos, especialmente PCA, son atractivos para exploración y cribado rápido, pero pierden curvatura y aumentan la incertidumbre (`Q/m = (6,5 ± 1,9)×10⁻⁴ C/kg` frente a los valores del método más completo).

La recomendación es un flujo híbrido: usar métodos eficientes para inspección, selección de videos y diagnóstico; reservar el método geométrico completo y la revisión humana semiautomática para los conjuntos que superen controles de calidad; y exigir validación independiente antes de informar una magnitud física.

## 2. Metodología de evaluación

### Tareas científicas evaluadas

1. **Reproducción del análisis original (Caso 1).** Detección de trazas, estimación de `c`, conversión a `Q/m` y comparación con dos grupos del informe original a partir de 11 videos.
2. **Análisis autónomo desde videos crudos (Caso 2).** Segmentación, medición geométrica, tracking, análisis espectral e inferencia bajo un modelo cuadrupolar ideal sobre 21 videos.
3. **Reanálisis automático exploratorio (Caso 3).** Implementación reproducible del método `L = cR` con esqueletización, ajuste simultáneo del centro y `c`, bootstrap y criterios objetivos de descarte.
4. **Método alternativo área–perímetro (Caso 4).** Estimación de la longitud sin esqueletización, usando área y perímetro de la silueta; se comparó con el resultado original en dos grupos.
5. **Variantes eficientes o compactas.** En particular, el modelo PCA de momentos de imagen de GPT-6-Luna medium y las variantes automáticas de los Casos 1, 3 y 4.

### Criterios de comparación

- **Calidad y rigor científico:** coherencia física, trazabilidad de supuestos, controles de calidad, separación entre resultados confirmados y diagnósticos, y explicitación de incertidumbres.
- **Latencia y tiempo de respuesta:** no hay mediciones versionadas. Se informa como “no disponible”; el número de frames o pasadas se usa sólo como indicador de carga computacional del pipeline, no como tiempo de ejecución.
- **Eficiencia de recursos y costos:** no hay tokens, precios, hardware ni consumo registrados. Se compara la estructura algorítmica: una segmentación frente a múltiples umbrales, esqueletización, tracking, espectros y bootstrap.
- **Adherencia a instrucciones:** se observa si cada ejecución produjo código reproducible, tablas, figuras, criterios de descarte y una interpretación consistente con el alcance de los datos.

## 3. Matriz comparativa

| Caso / Tarea Científica | Modelo Complejo Utilizado | Modelo Eficiente Utilizado | Desempeño Científico | Diferencia en Tiempo/Costo | Modelo Recomendado y Justificación |
|---|---|---|---|---|---|
| Caso 1: reproducción del análisis original | Codex; detección, muestreo, ajuste, incertidumbres instrumentales y comparación con el informe | GPT-6-Luna medium; pipeline automático con reglas fijas | Codex reprodujo dos grupos con `Q/m = 8,78` y `8,80×10⁻⁴ C/kg`, próximos a `8,7` y `8,5×10⁻⁴`; Luna no validó ningún video conjuntamente | Latencia, tokens y costo no están registrados. Luna usa un flujo automático más compacto, pero la ausencia de validación impide equiparar resultados | Codex para resultados finales; Luna para cribado y diagnóstico inicial |
| Caso 2: análisis autónomo desde 21 videos | Codex; geometría, ajuste del nulo, tracking, Welch, exclusión de alias e inferencia física | GPT-6-Luna medium; una segmentación y longitud PCA `L = √(12λ₁)` | Codex obtuvo `q = 0,200` e `|Q|/m = 6,646×10⁻⁴ C/kg` bajo supuestos explícitos, pero no identificó espectralmente la frecuencia secular; Luna obtuvo `6,5 ± 1,9×10⁻⁴`, exploratorio y con mayor incertidumbre | No hay benchmark temporal ni económico. PCA evita contornos, esqueletización y cinco umbrales; conserva menos información geométrica | Luna para exploración rápida; Codex para auditoría física y análisis final |
| Caso 3: `L = cR` automático | Codex; esqueletización Zhang–Suen, longitud de arco, ajuste robusto y 250 bootstrap | GPT-6-Luna medium; reglas automáticas y 40 cuadros equiespaciados con sensibilidad de umbral | Ambos muestran que la automatización sin revisión humana no alcanza los criterios: Caso 3 aceptó 0/11 y Luna 0/21 | No hay tiempo/costo medido. La variante eficiente reduce revisión y muestreo, pero no supera la inestabilidad del centro | Ninguno como estimador final; usar el eficiente para detectar fallas y el complejo con revisión semiautomática |
| Caso 4: validación alternativa de longitud | Codex; área–perímetro, cinco umbrales, bootstrap por frames y Monte Carlo | GPT-6-Luna medium; pipeline full-frame con detección, tracking y espectros | El método área–perímetro produjo `8,99 ± 1,08` y `8,91 ± 1,07×10⁻⁴ C/kg`, diferencias de +3,3% y +4,8% frente al informe; la variante full-frame procesó 15.710 frames pero aceptó 0 tracks físicamente | No se registran tiempos ni costos. El método área–perímetro tiene más pasadas que PCA, mientras que full-frame añade tracking y espectros | Área–perímetro para validar `Q/m`; full-frame sólo como diagnóstico dinámico hasta mejorar la adquisición |
| Comparación transversal de adherencia y reproducibilidad | Codex documenta supuestos, limitaciones, incertidumbre y archivos reproducibles en los casos principales | GPT-6-Luna medium entrega pipelines y reportes, pero sus resultados son mayormente exploratorios o no validados | La adherencia es buena en ambos; la diferencia principal es el nivel de evidencia necesario para elevar un resultado a medición | No hay datos de tokens, latencia ni costo | Enrutamiento por riesgo científico, no sólo por tamaño del modelo |

## 4. Análisis detallado por caso de estudio

### Caso 1 — Reanálisis de 11 videos

**Descripción de la tarea.** Se pidió reproducir el análisis sin disponer del código original. El procedimiento debía detectar trazas, estimar `c`, propagar incertidumbres y asociar los videos con los dos grupos publicados.

**Modelo complejo: Codex.** El reanálisis identificó dos videos compatibles con los grupos del informe y obtuvo `c = 0,528 ± 0,022` y `0,529 ± 0,035`, con `Q/m = (8,78 ± 1,07)` y `(8,80 ± 1,16)×10⁻⁴ C/kg`. También explicitó que la asociación de nombres no era completamente demostrable, que el centro usado era condicional al informe, que había diferencias de tasa real de video, y que las observaciones repetidas no eran independientes. Esa cautela mejora el rigor, aunque impide llamarlo una reproducción ciega completa.

**Modelo eficiente: GPT-6-Luna medium.** Usó detección automática, 40 cuadros por video, umbral principal 40 y sensibilidad 35/45, ajuste de `L = cR` y filtros objetivos. El resultado fue exploratorio: ningún video superó simultáneamente linealidad, estabilidad del centro y límite de estabilidad. Su ventaja es el procedimiento simple y reproducible; su debilidad es que elimina la intervención semiautomática que el método original consideraba necesaria para corregir fragmentos, fusiones y reflejos.

**Breakpoint.** El modelo eficiente falla cuando la selección de componentes requiere interpretación frame a frame o cuando el centro no queda identificado por la cobertura angular. El modelo complejo resulta innecesario si el objetivo es sólo localizar videos problemáticos o generar figuras diagnósticas.

### Caso 2 — Análisis autónomo geométrico y espectral

**Descripción de la tarea.** A partir de 21 videos y un contexto físico breve, se debía construir una cadena autónoma de detección, tracking, estimación geométrica y análisis de frecuencia.

**Modelo complejo: Codex.** El pipeline calculó un `q` geométrico de `0,200` con IC bootstrap entre videos `0,193–0,235` y una conversión condicional `|Q|/m = 6,646×10⁻⁴ C/kg`. Incorporó corrección de ancho óptico, ajuste del nulo por video, seguimiento con asignación húngara y análisis de Welch. El punto fuerte es la separación explícita entre resultado geométrico, predicción de `3,53 Hz` y evidencia espectral: sólo un pico quedó cerca de la predicción y no se aceptó una identificación independiente robusta. Las debilidades son las dependencias del voltaje, exposición, geometría real, proyección 3D y escala.

**Modelo eficiente: GPT-6-Luna medium.** Estimó la longitud por PCA de los píxeles de cada componente, evitando esqueletización, contornos, perímetros y cinco realizaciones de umbral. Retuvo seis videos y obtuvo `Q/m = (6,5 ± 1,9)×10⁻⁴ C/kg`. El método es conceptualmente claro y computacionalmente compacto, pero la PCA representa bien una elongación aproximadamente recta y pierde curvatura; la dispersión entre videos domina la incertidumbre.

**Breakpoint.** PCA deja de ser suficiente cuando la curvatura de la traza, el ancho variable o los componentes fusionados contienen información relevante. Codex es innecesario para una primera estimación geométrica o para descartar videos antes de un análisis profundo.

### Caso 3 — Reanálisis automático exploratorio

**Descripción de la tarea.** Se implementó el método escrito con canal rojo, umbral fijo, filtrado por área y elongación, esqueletización, longitud de arco, ajuste robusto del centro y bootstrap.

**Modelo complejo: Codex.** Sobre 11 videos detectó 519 trazas, pero no aceptó ningún video para una estimación final. Los motivos fueron centros inestables, baja cobertura angular y valores de `R²` insuficientes. Esta decisión es científicamente adecuada: evita convertir diagnósticos inestables en una medición.

**Modelo eficiente: GPT-6-Luna medium.** Aplicó reglas automáticas a 21 videos, con un cuadro cada 30 frames, umbral 20, esqueletización Zhang–Suen y 250 remuestras bootstrap. Tampoco obtuvo videos aceptados. Su principal aporte es hacer visibles los fallos de manera reproducible; no reemplaza la revisión de trazas que el protocolo original delegaba a una persona.

**Breakpoint.** Ambos enfoques chocan con un problema de datos y diseño experimental, no sólo de capacidad de modelo: sin distribución angular suficiente y sin centro estable, aumentar la complejidad no identifica `c`. El modelo eficiente es preferible para control de calidad masivo; el complejo sólo se justifica después de corregir detecciones y adquirir mejores videos.

### Caso 4 — Método área–perímetro y pipeline full-frame

**Descripción de la tarea.** Se exploró una medición alternativa de la longitud y, en otra variante, una cadena full-frame con tracking y análisis espectral.

**Modelo complejo: método área–perímetro de Codex.** Para una traza tubular se usó `L = 1/2√(P² − 4πA)`, con cinco umbrales, controles de área, elongación, sensibilidad, distancia al centro y rango de `L/R`. El resultado fue compatible con el informe original, con diferencias +3,3% y +4,8%. La validación sintética y la propagación Monte Carlo son fortalezas. Las limitaciones están bien delimitadas: fusiones, cruces, ramificaciones y pixelado violan el modelo; además, los centros publicados se usaron como calibración geométrica.

**Modelo eficiente / variante GPT-6-Luna medium.** El pipeline full-frame procesó 21 videos, 15.710 frames y 176.526 componentes; conservó 79.243 trazas de alta confianza y generó 10.433 tracks. Sin embargo, ninguno superó simultáneamente duración, ajuste sinusoidal y resolución, por lo que no se informó `q` ni `Q/m` como medición. Aunque no es “eficiente” en volumen de datos, sí es una variante de decisión automática y de alta cobertura; su costo algorítmico crece por tracking y espectros.

**Breakpoint.** La estrategia full-frame falla como inferencia dinámica cuando la frecuencia de cámara (~21,46 Hz) no permite resolver adecuadamente la excitación de 50 Hz y cuando los tracks no tienen duración o resolución suficientes. El área–perímetro resulta innecesario para un cribado rápido, pero es más adecuado para validar una magnitud geométrica en los dos grupos relevantes.

## 5. Recomendaciones y flujo de trabajo híbrido

### Cuándo usar un modelo eficiente

- Clasificar videos por calidad, detectar fondos, saturación, fusiones y cobertura angular.
- Producir un primer valor geométrico o una visualización diagnóstica.
- Aplicar una medición PCA cuando las trazas son aproximadamente rectas y se necesita un resultado exploratorio.
- Generar tablas reproducibles para decidir qué subconjunto merece análisis profundo.

El resultado debe etiquetarse como exploratorio mientras no supere controles de centro, linealidad, estabilidad y sensibilidad.

### Cuándo escalar a un modelo avanzado

- Cuando se requiere propagar incertidumbres instrumentales y sistemáticas.
- Cuando las trazas son curvas, fragmentadas o de ancho variable.
- Cuando se necesita comparar métodos independientes, revisar supuestos físicos o justificar un descarte.
- Cuando un resultado se va a presentar como medición científica y no sólo como diagnóstico.

### Arquitectura propuesta de prompt routing

```text
Datos crudos
    ↓
Modelo eficiente: inspección + segmentación + métricas de calidad
    ↓
¿Centro estable, cobertura angular suficiente y trazas válidas?
    ├─ No → reporte diagnóstico y solicitud de mejores datos/revisión humana
    └─ Sí
         ↓
Modelo avanzado: medición completa + incertidumbres + controles físicos
         ↓
Método independiente de validación (área–perímetro o revisión semiautomática)
         ↓
¿Resultados compatibles y supuestos documentados?
    ├─ No → mantener como exploratorio y auditar causas
    └─ Sí → informe final de Q/m con limitaciones
```

El enrutamiento debería incluir en el prompt los criterios de salida: no informar magnitudes confirmadas si el centro es inestable, si el resultado depende de un supuesto no medido o si la validación espectral no es independiente. También debería exigir que cada ejecución entregue código, parámetros, tablas, figuras, semillas aleatorias y una lista de resultados rechazados.

## 6. Limitaciones del benchmark

- No se conservaron los prompts originales ni el documento de Google Drive “PF CURSO IA” dentro del repositorio analizado.
- No hay mediciones comparables de latencia, tokens, precio, memoria, GPU/CPU o número de llamadas al modelo.
- No aparecen ejecuciones de GPT-4o, Claude 3.5 Sonnet, Claude 3 Haiku, Llama 3 70B, Llama 3 8B ni Phi-3; no es válido atribuirles desempeño a partir de este repositorio.
- “Complejo” y “eficiente” se usan aquí como categorías metodológicas y documentales, no como una clasificación oficial de capacidad de modelos.
- Varias ejecuciones dependen de centros publicados, supuestos de voltaje y videos que contienen observaciones repetidas de las mismas partículas.

## Fuentes internas

- [README principal](README.es.md)
- [Caso 1 — reanálisis Codex](agent-results/caso-1-codex-reanalysis/REPORTE_REANALISIS.md)
- [Caso 2 — análisis autónomo Codex](agent-results/caso-2-codex-analysis/REPORT.md)
- [Caso 2 — modelo PCA eficiente](agent-results/caso%202%20GPT-6-Luna%20medium/README.md)
- [Caso 3 — análisis automático](agent-results/caso%203/README.md)
- [Caso 3 — variante GPT-6-Luna medium](agent-results/caso%203%20GPT-6-Luna%20medium/README.md)
- [Caso 4 — método área–perímetro](agent-results/caso-4-codex-alternative-analysis/REPORTE_METODO_ALTERNATIVO.md)
- [Caso 4 — variante full-frame GPT-6-Luna medium](agent-results/caso%204%20GPT-6-Luna%20medium/README.md)
