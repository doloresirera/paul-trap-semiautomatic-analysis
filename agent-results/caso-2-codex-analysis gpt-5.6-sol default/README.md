# Caso 2 — análisis autónomo con Codex

Análisis independiente de 21 videos crudos de partículas de licopodio
confinadas en una trampa de Paul anular. Codex recibió únicamente los videos y
un archivo de contexto con los parámetros del montaje; no recibió código ni un
análisis humano previo.

El resultado principal, el modelo físico, las decisiones metodológicas, las
incertidumbres y las limitaciones están documentados en
[REPORT.md](REPORT.md).

## Resultado central

- Parámetro de Mathieu: `q = 0.200` (IC 95 % entre videos: 0.193–0.235).
- Relación carga/masa: `|Q|/m = 6.65×10⁻⁴ C kg⁻¹` bajo el modelo cuadrupolar
  ideal y tomando 1175 V como amplitud RF.
- Frecuencia secular predicha: `3.53 Hz`. No se obtuvo una confirmación
  espectral independiente robusta.

Estos valores dependen de la convención del voltaje, el tiempo de exposición,
la geometría real de los electrodos y la proyección bidimensional.

## Reproducir

1. Colocar los 21 videos `.mp4` en un directorio llamado
   `drive-download-20260926T014040Z-1-001` junto al script. Los videos no se
   incluyen en Git para mantener pequeño el repositorio.
2. Crear un entorno de Python e instalar `requirements.txt`.
3. Ejecutar `python analyze_experiment.py`.

El script usa semillas fijas y genera las tablas, figuras y el informe bajo
`results/`. Los CSV de detecciones cuadro a cuadro no se incluyen porque se
pueden regenerar y ocupan más de 50 MB; sí se incluyen los resultados agregados
y las figuras necesarias para auditar las conclusiones.
