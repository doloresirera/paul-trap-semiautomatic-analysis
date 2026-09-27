# Relación carga-masa de esporas de licopodio en una trampa de Paul

Determinación de la relación carga-masa (Q/m) de partículas de licopodio
atrapadas en una trampa de Paul anular, a partir del análisis de la micromoción
registrada en video. Trabajo de la materia Laboratorio 4 — Licenciatura en Ciencias Físicas, 
Facultad de Ciencias Exactas y Naturales (FCEN), Universidad de Buenos Aires (UBA).

**Autoras:** Sirera María Dolores, Paseri Milagros, Benedetti Anna.

> **Nota.** Este es un trabajo de laboratorio de grado, no una herramienta
> terminada. El código y el enfoque se comparten como referencia para quien
> quiera abordar un problema similar. Los parámetros están ajustados a nuestro
> montaje experimental y deben readaptarse a cada caso (ver más abajo).
>
## **Extensión del proyecto**

Como proyecto final del curso "Investigación asistida por inteligencia artificial: aplicación en ondas gravitacionales" dictado por Matías Zaldarriaga en el segundo cuatrimestre del 2026, se utilizará el material de trabajo de este experimento para, en distinto niveles, probar cómo la IA reproduce o mejora el trabajo realizado.

## Idea del método

Una partícula atrapada en una trampa de Paul oscila rápidamente en torno a su
posición, lo que se denomina *micromoción*. La amplitud de esa oscilación es nula en el
centro de la trampa y crece de forma proporcional
a la distancia a ese centro. Como la cámara integra muchos ciclos de
micromoción durante la exposición de cada **frame**, cada partícula deja una
**traza** (una rayita) cuya longitud L es proporcional a su distancia R al
centro:

    L = c · R

El factor de proporcionalidad c (el parámetro de estabilidad de Mathieu) se
obtiene ajustando esta relación, y de él se despeja Q/m mediante
Q/m = c·r0²·Ω²/(4·V_AC), con Ω = 2πf. Como c = L/R es un cociente de dos
longitudes medidas sobre la misma imagen, el método **no requiere calibrar la
relación entre píxeles y milímetros**: cualquier factor de conversión se
cancela.

## Procesamiento, paso a paso

Sobre cada **frame** del video, el análisis realiza los siguientes pasos, 
que reproducen en código un flujo que primero se desarrolló manualmente en Fiji:

1. **Selección de canal de color.** Se separa la imagen en sus canales rojo,
   verde y azul y se trabaja con el que mejor distingue las trazas del fondo
   (en nuestro caso, el rojo).

2. **Umbralización (binarización).** Se marca como "traza" todo píxel más
   brillante que un umbral fijo, y como "fondo" el resto. El resultado es una
   imagen en blanco y negro donde quedan solo las trazas.

3. **Filtrado por forma y tamaño.** De las manchas resultantes se conservan
   solo las que tienen el tamaño (área) y la forma alargada (elongación)
   propios de una traza, descartando ruido, reflejos y fusiones de varias
   trazas.

4. **Esqueletización.** Cada traza se reduce a una línea de un píxel de ancho
   que recorre su eje central, para poder medir su longitud sin que influya su
   grosor.

5. **Medición de la longitud.** Se recorre ese esqueleto sumando las distancias
   entre píxeles, obteniendo la longitud de arco L de la traza (se mide el arco
   y no la línea recta entre extremos porque las trazas son curvas).

Este procesamiento es **semiautomático**: el programa propone las trazas
detectadas en cada cuadro y quien analiza acepta, descarta o corrige la
selección, **frame** por **frame**.

### Determinación del centro

El centro de la trampa no se marca a mano: se calcula. Conociendo la longitud y
la posición de muchas trazas, se busca (por ajuste de cuadrados mínimos) el
punto desde el cual todas las longitudes resultan proporcionales a sus
distancias. Ese punto es el centro, y con él se calcula la distancia R de cada
traza.

Para verificar que el centro es confiable se usa **bootstrap**: se recalcula el
centro muchas veces, cada vez usando solo una parte de las trazas elegidas al
azar, y se observa cuánto se mueve el resultado. Si el centro apenas se
desplaza, es confiable; si salta de un lado a otro, las trazas no lo
determinan bien y ese video se descarta.

### Incertidumbre

El error de medición de cada traza combina tres fuentes: la elección del umbral
(afecta la longitud medida), la esqueletización (recorta levemente los
extremos) y la incertidumbre en la posición del centro (afecta la distancia R).

## Ejemplo: sobre qué se trabaja

En `ejemplos/` hay algunos **frames** de un video, con las trazas de micromoción
sin procesar y con el esqueleto detectado superpuesto, para ilustrar la entrada
del análisis.

<!-- Descomentá y ajustá los nombres cuando subas las imágenes:
![Cuadro crudo](ejemplos/frame_crudo.png)
![Trazas detectadas](ejemplos/frame_detectado.png)
-->

## Cómo adaptarlo a tus propias imágenes

Los siguientes parámetros son específicos de cada montaje y **no** deben
copiarse tal cual, sino elegirse mirando tus propias imágenes:

- **Canal de color.** El que mejor separe tus trazas del fondo, según el color
  de tu iluminación.
- **Umbral de binarización.** El parámetro más sensible: afecta directamente la
  longitud medida. Elegilo según el brillo de tus imágenes y mantenelo **fijo**
  para todos los cuadros y videos.
- **Área mínima y máxima.**
- **Elongación mínima.** 
- **Constantes físicas** (V_AC, frecuencia, r0). De tu montaje experimental.

### Recomendaciones

- Validá el centro (bootstrap) antes de confiar en cualquier resultado.
- Necesitás trazas repartidas en ángulo y en un rango amplio de distancias R.
- Valores de c mayores al límite de estabilidad (~0,908) suelen indicar un
  centro mal ubicado, no trazas mal medidas.
- No todos los videos sirven; descartar por criterios objetivos es parte del
  método.

## Entorno

Python 3.13.9 (Anaconda), con OpenCV 4.13.0, NumPy 2.3.5, SciPy 1.16.3,
pandas 2.3.3, scikit-image 0.25.2 y Matplotlib 3.10.6.

## Resultados obtenidos

Se analizaron dos conjuntos de partículas con centro confiable:

| | Video 1 | Video 2 |
|---|---|---|
| N (trazas) | 86 | 113 |
| c | 0,53 ± 0,07 | 0,52 ± 0,06 |
| Q/m [C/kg] | (8,7 ± 1,0)×10⁻⁴ | (8,5 ± 1,0)×10⁻⁴ |
| Error de medición | 13 % | 11 % |
| σ (dispersión de c_i) | 0,09 | 0,08 |

## Caso 1: reanálisis con un agente de IA

Como parte de una evaluación de herramientas de IA, se entregaron el informe y
11 videos crudos a Codex para que reprodujera el análisis sin disponer del
código original. El resultado, las decisiones metodológicas, las figuras, los
datos tabulados y el script reproducible están en
[`agent-results/caso-1-codex-reanalysis/`](agent-results/caso-1-codex-reanalysis/REPORTE_REANALISIS.md).

Este reanálisis es una implementación independiente y no reemplaza el análisis
semiautomático original. En particular, documenta las diferencias producidas
por la corrección manual de trazas, el remuestreo por frame y la propagación de
incertidumbres instrumentales.

La explicación didáctica de los errores, supuestos y mejoras está disponible
como [documento HTML](agent-results/caso-1-codex-reanalysis/CASO_1_ERRORES_Y_MEJORAS.html).

## Caso 2: análisis autónomo desde videos crudos

En una segunda evaluación se entregaron a Codex 21 videos crudos y solamente
un breve contexto experimental con la tensión RF, la frecuencia, el radio de
la trampa y el tamaño nominal de las partículas. El agente desarrolló de forma
autónoma el procesamiento de imágenes, el seguimiento, el análisis espectral y
la inferencia física.

El reporte completo, el código reproducible, los resultados agregados y las
figuras están en
[`agent-results/caso-2-codex-analysis/`](agent-results/caso-2-codex-analysis/REPORT.md).

El análisis obtiene `q = 0,200` (IC 95 %: 0,193–0,235) y, bajo un modelo
cuadrupolar ideal, `|Q|/m = 6,65×10⁻⁴ C kg⁻¹`. La frecuencia secular de
`3,53 Hz` es una predicción del modelo y no una identificación espectral
independiente. El reporte distingue explícitamente los errores estadísticos de
las incertidumbres sistemáticas asociadas con la exposición, la geometría, la
convención del voltaje y la proyección de la cámara.
