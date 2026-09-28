from pathlib import Path
import csv, html

root=Path(__file__).parent
rows=list(csv.DictReader((root/'resultados_videos.csv').open(encoding='utf8')))
def f(x, n=3):
    try:return f'{float(x):.{n}g}'
    except:return x
trs=[]
for r in rows:
    estado='No validado: '+r.get('usable','False')
    trs.append('<tr><td>'+html.escape(r['video'])+'</td><td>'+r['N']+'</td><td>'+f(r['c'])+' ± '+f(r['c_unc'])+'</td><td>'+f(r['Q_m'],3)+' ± '+f(r['Q_m_unc'],3)+'</td><td>'+f(r['ci_sd'])+'</td><td>'+f(r['cx_sd'])+' / '+f(r['cy_sd'])+' px</td><td>'+estado+'</td></tr>')
figs=[]
for p in sorted((root/'figuras').glob('*.png')):
    figs.append(f'<figure><img loading="lazy" src="figuras/{html.escape(p.name)}"><figcaption>{html.escape(p.stem)}: ajuste L=cR e histograma de c_i.</figcaption></figure>')
doc='''<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Caso 3 — reanálisis GPT-6-Luna</title><style>:root{--ink:#1f2933;--muted:#52606d;--paper:#f6f7f9;--card:#fff;--accent:#176b68;--line:#d9e2ec}*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:16px/1.55 system-ui,Segoe UI,sans-serif}main{max-width:1200px;margin:auto;padding:30px 22px 64px}h1,h2{line-height:1.2}h1{font-size:2rem}h2{margin-top:2.1rem;color:var(--accent)}.lead{font-size:1.12rem;color:var(--muted)}.callout{background:#fff8e7;border-left:5px solid #cf8b22;padding:15px 18px;margin:18px 0}.card{background:var(--card);padding:18px;border:1px solid var(--line);border-radius:10px;margin:18px 0}table{border-collapse:collapse;width:100%;font-size:.9rem;background:white}th,td{padding:9px 8px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}th{background:#edf3f4;position:sticky;top:0}.scroll{overflow:auto}img{max-width:100%;height:auto}figure{margin:0;background:white;border:1px solid var(--line);border-radius:8px;padding:10px}figcaption{font-size:.88rem;color:var(--muted)}.gallery{display:grid;grid-template-columns:repeat(auto-fit,minmax(440px,1fr));gap:14px}code{background:#edf2f7;padding:2px 5px;border-radius:4px}</style></head><body><main>
<h1>Reanálisis de videos de micromoción — Caso 3</h1><p class="lead">Trampa de Paul anular · esporas de licopodio · análisis reproducible GPT-6-Luna medium</p>
<div class="callout"><strong>Resultado principal:</strong> se procesaron 21 videos. Ninguno superó simultáneamente los controles de cantidad de trazas, estabilidad bootstrap del centro y límite de estabilidad <i>c</i>&lt;0,908. Los valores de la tabla son diagnósticos exploratorios y no mediciones confirmadas de Q/m.</div>
<h2>Comparación por video</h2><p>Se muestran todos los ajustes obtenidos, aun cuando fueron descartados. La dispersión del centro está expresada como desviación bootstrap en x/y.</p><div class="scroll"><table><thead><tr><th>Video</th><th>Trazas</th><th>c ± error</th><th>Q/m ± error (C/kg)</th><th>σ(c_i)</th><th>σ centro (px)</th><th>Estado</th></tr></thead><tbody>'''+''.join(trs)+'''</tbody></table></div>
<h2>Qué hice</h2><div class="card"><ol><li>Tomé un cuadro cada 30 frames y trabajé con el canal rojo.</li><li>Usé umbral fijo 20, apertura morfológica 3×3, área 18–2200 px², bounding box menor que 20000 px² y elongación mínima 2.</li><li>Esqueleticé con Zhang–Suen y medí longitud de arco de 8-conectividad.</li><li>Ajusté simultáneamente <code>L=cR</code> y el centro mediante mínimos cuadrados robustos.</li><li>Usé 250 remuestras bootstrap del centro y sensibilidad con umbrales 15 y 25.</li><li>Convertí condicionalmente mediante <code>Q/m = c r0² (2πf)²/(4 VAC)</code>, con VAC=1175 V, f=50 Hz y r0=8,9 mm.</li></ol></div>
<h2>Criterios de descarte y límites</h2><div class="card"><p>Se requerían al menos 20 trazas, desviación bootstrap menor que 10 px en ambas coordenadas y 0&lt;c&lt;0,908. Los centros inestables hacen que R y c no estén identificados. Por eso no se seleccionó artificialmente un “mejor” video ni se usó la tabla de resultados del README como entrada. Para obtener una medición física haría falta la revisión semiautomática, cuadro por cuadro, de reflejos, fusiones y trazas falsas que el README describe pero no especifica.</p></div>
<h2>Figuras por video</h2><div class="gallery">'''+''.join(figs)+'''</div>
<h2>Archivos para reproducir</h2><p><a href="analisis_reproducible.py">Código</a> · <a href="resultados_videos.csv">CSV</a> · <a href="decisiones.csv">Decisiones</a> · <a href="parametros.json">Parámetros</a></p>
</main></body></html>'''
(root/'informe_reanalisis.html').write_text(doc,encoding='utf8')
