# Caso 4 — método alternativo área–perímetro

Codex recibió el informe del laboratorio y los 21 videos crudos con el
objetivo de proponer un método distinto para estimar la relación carga–masa.
A diferencia del análisis original, las trazas no se esqueletizan: su longitud
se obtiene a partir del área `A` y el perímetro `P` de una silueta tubular:

```text
L = 1/2 sqrt(P² - 4πA).
```

El reporte completo, la comparación crítica y la discusión de incertidumbres
están en [REPORTE_METODO_ALTERNATIVO.md](REPORTE_METODO_ALTERNATIVO.md).

## Resultado central

| Grupo | c alternativo | Q/m alternativo [C/kg] | Diferencia con el informe |
|---|---:|---:|---:|
| 1 | 0,539 ± 0,020 | (8,99 ± 1,08)×10⁻⁴ | +3,3 % |
| 2 | 0,535 ± 0,020 | (8,91 ± 1,07)×10⁻⁴ | +4,8 % |

Ambos resultados son compatibles con los valores del informe. La dispersión
traza a traza es sensible a los criterios de segmentación, por lo que no puede
atribuirse enteramente a diferencias físicas entre esporas.

## Reproducir

1. Colocar los 21 videos `.mp4` en un directorio
   `drive-download-20260926T014040Z-1-001` junto a los scripts, o ajustar la
   constante `VIDEOS` en `ejecutar_analisis_final.py`.
2. Instalar las dependencias con `pip install -r requirements.txt`.
3. Ejecutar `python ejecutar_analisis_final.py`.

Los videos y el PDF original no se duplican en Git. Las tablas de trazas, los
resultados agregados y las figuras finales sí están incluidos.
