# Progreso de la construcción

Comando de pruebas: `.venv\Scripts\python.exe -m pytest -q` (desde la raíz del proyecto).

## F1 — Núcleo de cálculo (2026-11-17)

Módulos: `core/constantes.py`, `core/geodesia.py`, `core/utm.py` (Krüger 6.º orden),
`core/transformacion.py`, `core/conversion.py`, `core/errores.py`.

Resultado: **321 pruebas pasan, 7 omitidas** (5 casos del oráculo que dependen del parseo de texto,
cubiertos en F2, y 2 con prueba dedicada).

| Prueba | Casos | Resultado |
|---|---|---|
| Golden vs .exe (Réplica): `c1_escritorio`, `prueba_escritorio`, `bordes_escritorio` | 195 filas | máx. ΔN 0.59 mm, ΔE 0.83 mm, Δlat 1.53 mm, Δlon 1.39 mm; huso idéntico (tolerancias 2 mm / 3 mm) |
| Defectos corregidos del .exe | sin parámetros (16), fuera de límites (4), UTM sin validar (4), espejado del Este (E31), 72°00′ → huso 19 (E15) | error claro / valor correcto según PROJ |
| E30 (entrada UTM a 2.65° del MC) | 1 | la inversa UTM→geo del .exe tiene 3.0 cm de error ahí; la nuestra = PROJ; desde las geográficas del .exe la salida coincide a 0.3 mm |
| Tabla IGM vs Réplica (37 puntos × 4 sentidos) | 148 | idénticas salvo SAD69 26°–32° S (14 conversiones, 10–13 m) |
| Fronteras de franja (ambos métodos) y continuidad de la tabla (cada 1″ de 17°30′ a 56°) | — | sin huecos ni solapes |
| Contra una transcripción Python del `core.js` (no incluida; interior de franjas) | 1362 | máx. 1.9 mm lat/lon, 2.2 mm N/E (tolerancia 3 mm) |
| Contra **core.js original** ejecutado en V8 local (mini-racer) | 1362 | idéntico al modelo_web: máx. 1.9 / 2.2 mm. Confirma además que −33.45/−70.65 no da resultado en la web |
| PROJ geo↔UTM, 3 elipsoides × 5 husos, ±6° del MC, 0.5°–79.5° S | 22 500 + inversas | < 0.01 mm (tolerancia 2 mm) |
| Ida y vuelta geo→UTM→geo→UTM | 9 000 | < 0.01 mm (tolerancia 1 mm) |
| PROJ geocéntricas (geo↔XYZ, h −500…9000 m) | 6 000 | < 0.1 mm |
| PROJ `+towgs84` (traslación) por franja, ambos sentidos, ambos métodos, y cadena hasta UTM | 4 200 | ≤ 1 mm geo, ≤ 2 mm UTM |
| Composición PSAD56↔SAD69 = dos pasos por SIRGAS | 1 200 | idéntica |
| Ida y vuelta de datum (interior) | 4 000 | ≤ 6 mm (cierre inherente por h = 0); tolerancia 1 cm |
| Salto de franja en ida y vuelta junto a 32° S | 1 | documentado (≈ 10.6 m) |

## F2 — Parseo y formato (2026-11-17)

Módulos: `core/parseo.py`, `core/formato.py`.

Resultado: **547 pruebas pasan, 9 omitidas** (las omitidas son casos del oráculo con prueba dedicada en otro archivo).

| Prueba | Casos | Resultado |
|---|---|---|
| Números con miles/decimal (punto, coma, espacio, NBSP), salidas del .exe ("6.318.026,543.", "7.956.582,773.  m.") | 18 + 11 inválidos | OK; "346.642" es ambiguo sin rango y se resuelve por magnitud (Este 100 000–900 000) |
| Ángulos: decimal, GM, GMS con ° ' " ′ ″ ’ ” º '', d/m/s, letras N S E O W, signos, salida GMS del .exe (",3791") | 31 + 19 inválidos | OK; grados con decimales junto a minutos = error explícito |
| Campos GMS de la pestaña 1 | 5 + 11 inválidos | OK (E25: 33,5° ahora es error, el .exe truncaba) |
| Filas de la masiva: detección geo/UTM y orden (lat/lon, Norte/Este) | 12 + 9 errores | OK; orden invertido marcado; ambiguos y mezclas rechazados |
| División de líneas pegadas (tab, ";", ", ", espacios, GMS con espacios, datum inicial) | 14 | OK |
| Oráculo del .exe recorrido por el parseo (bordes + A7) | 47 | mismas tolerancias que F1; E18/E19/E22/E23/E25 rechazados con error claro |
| Releer las 134 salidas de texto del .exe (N/E y GMS) | 134 × 4 | exactas |
| Formato: sin miles, separador configurable, mitad hacia arriba, sin "−0", acarreo GMS, independiente del locale | 25 | OK |

## F3 — Interfaz: ventana, opciones y pestaña 1 (2026-11-17)

Módulos: `config.py` (config.json junto al ejecutable, escritura atómica, sin error si no se puede),
`core/servicio.py` (conversión desde textos y textos de salida, sin tkinter), `ui/app.py`,
`ui/opciones.py`, `ui/panel_salida.py`, `ui/tab_individual.py`, `ui/comun.py`.

Resultado: **558 pruebas pasan, 9 omitidas**. Nuevas (11, `tests/test_ui.py`, con la ventana real de Tk):
valores por defecto (U.T.M., Tabla IGM, 0/6 decimales, punto, positivos = S/O, barra de estado con
método y ±5 m); UTM con miles → UTM; decimal → decimal/GMS; "Copiar Norte y Este" (tabulador) y
"Copiar lat, lon" (", " con punto y "; " con coma decimal) verificados en el portapapeles; GMS con grados
decimales → mensaje no bloqueante; sin parámetros → mensaje claro y salida vacía; zona forzada 18 sin
espejado; cambio de método recalcula (SAD69 30.6° S cambia ≥ 9 m); Enter convierte; opciones guardadas;
config.json dañado, inválido o no escribible.
Revisión visual con captura (`build/capturas/t1.png`, no versionada).

## F4 — Pestaña 2 "Conversión masiva" (2026-11-17)

Módulos: `ui/tab_masiva.py` (Treeview con editor superpuesto: doble clic/F2/escribir, Enter baja, Tab
avanza, Supr borra, Ctrl+V/Ctrl+C), y en `core/servicio.py`: `convertir_fila`, `interpretar_pegado`, `textos_fila`.

Resultado: **565 pruebas pasan, 9 omitidas**. Nuevas (7, `tests/test_masiva.py`): pegado con encabezado,
líneas vacías, tabulador, ";", espacios, GMS con espacios y datum por línea; niveles OK / amarillo (orden
corregido) / rojo (sin parámetros, texto inválido, ambiguo) sin convertir lo inválido; 30 filas iniciales y
"Agregar fila"; pegado que amplía la cuadrícula; datum por fila; copia tabulada con y sin encabezados (filas con
error quedan vacías con su motivo); cambio de formato/separador recalcula; edición de celdas por teclado.
Revisión visual con captura (`build/capturas/t2.png`).

## F5 — Pestaña 3 "Calcular Archivo Excel" (2026-11-17)

Módulos: `io/csv_io.py` (codificación utf-8-sig / latin-1, delimitador ; , tab |), `io/excel_io.py`
(lectura streaming con data_only; copia sobre el libro completo; .xls con xlrd → .xlsx de valores),
`io/proceso.py` (conversión por fila desde celdas numéricas o de texto, resumen), `ui/tab_excel.py`
(vista previa, asignación de columnas por encabezado, datum fijo o por columna, hilo + barra de progreso + cancelar).

Resultado: **589 pruebas pasan, 9 omitidas** (incluida la de volumen, `-m lento`). Nuevas (24):
delimitadores y codificaciones; celda numérica 346.642 ≠ texto "346.642" (sin ambigüedad en números);
GMS en 6 columnas con letra/signo; datum por columna (desconocido → error); xlsx: original intacto (SHA-256),
negrita/relleno/fórmula y otra hoja conservados, columnas nuevas numéricas con formato "0"/"0.000000",
Estado con motivo, filas vacías omitidas; valor calculado de fórmulas (caché) leído con data_only;
salida decimal y GMS (texto con coma); salida = original rechazada; csv en 4 combinaciones de codificación,
delimitador y separador decimal; **.xls real del oráculo** (`c1_decimal.xls`, 37 filas, Réplica ≤ 2 mm vs .exe) y
.xls → .xlsx; pestaña completa de punta a punta en la ventana real (hilo, resumen) y errores de configuración.

Volumen: **100 000 filas csv en 3.6 s (incluida la generación del archivo); 100 000 filas xlsx en 23–27 s** (leer, convertir, copiar el libro y guardar;
pico de memoria medido aparte ≈ 300 MB).

## F6 — Empaquetado portable (2026-11-17)

`build.bat` (pruebas → PyInstaller onedir → zip → onefile → verificación) y `tools/verificar_exe.py`: copia cada
variante a una carpeta temporal fuera del proyecto y de `.venv`, la ejecuta con PATH solo de Windows (sin
VIRTUAL_ENV/PYTHON*/TCL/TK) y desde otro directorio de trabajo, corre `Coordenadas.exe --autoprueba` (conversión,
xlsx y csv de ida y vuelta, config.json junto al exe) y mide el arranque hasta que la ventana es visible.

| Variante | Tamaño | Arranque (1.º / siguientes) | Autoprueba |
|---|---|---|---|
| onedir `dist\Coordenadas\Coordenadas.exe` | 26.5 MB (carpeta) · zip 11.5 MB | 0.48 s / 0.25 s | OK, valores = código fuente, config.json junto al exe |
| onefile `dist\onefile\Coordenadas.exe` | 11.5 MB | 1.08 s / 1.06–1.12 s | OK (config.json junto al exe, no en la carpeta temporal de extracción) |

El paquete contiene solo Python, Tcl/Tk, openpyxl, xlrd y la app (numpy, pyproj, mini-racer, pytest y pywin32 excluidos).

**Validación ampliada (opcional) con el .exe en modo Excel** (script no incluido en este repositorio, ~1 min de .exe):
750 puntos aleatorios por sentido × 4 = **3 000 conversiones, todas comparadas**: ΔN/ΔE ≤ 0.52 mm, Δlat/Δlon ≤ 0.006 mm
(resolución 1e-10° del modo Excel), tras el arreglo de escala por configuración regional (÷1e10, ÷1e3) con control de
plausibilidad (0 anómalos). Hallazgo nuevo: el modo Excel del .exe deja **sin salida las filas con longitud > 76° O**
(constante −76 del binario), aunque el modo individual acepta hasta 77°; la muestra final usa 66.05°–75.95° O.
Detalle por punto en `oraculo/ampliada_*.csv`; archivos del .exe en `oraculo/excel_prueba/ampliada/`.

Suite final: ver la última línea de este archivo.

**Suite final (2026-11-17): 589 pruebas pasan, 9 omitidas** (`pytest -m "lento or not lento"`, 40 s). Las 9 omitidas son
filas del oráculo que tienen una prueba dedicada en otro archivo (no hay omisiones por falta de herramientas).

## U1–U5 — Rediseño de la interfaz (2026-11-17/18)

Solo `src/coordenadas/ui/` (más `config.zona_salida`, que ahora es un ajuste global). `core/` e `io/` sin
cambios; ninguna tolerancia modificada. Detalle del sistema visual: [INTERFAZ.md](INTERFAZ.md); maquetas en
`maqueta/`; capturas de 18 estados a 100 %, 125 % y 150 % en `ui_capturas/` (`tools/capturas_ui.py`).

- **U1** tema sv-ttk + estilos propios (`tema.py`, `imagenes.py`), componentes (`componentes.py`), DPI y escala,
  ventana redimensionable con tamaño/posición recordados. Se corrigieron dos problemas encontrados al dibujar:
  piezas 9-slice de 2 px hacían que un `update()` tardara ~30 s (se amplían a un tamaño de mosaico); y el
  mensaje de error realimentaba el ancho del campo (bucle de geometría con la ventana oculta).
- **U2** pestaña 1 y `dialogo_ajustes.py` (28 pruebas nuevas).
- **U3** pestañas 2 y 3 con el mismo sistema (11 pruebas nuevas). La confirmación de reemplazo de un archivo
  existente pasó de ventana emergente a aviso en pantalla.
- **U4** `build.bat` con `--collect-data sv_ttk`; `--autoprueba` exige `tema == sun-valley-light`;
  `tools/verificar_exe.py` espera el título nuevo y captura la ventana del .exe (PrintWindow).
- **U5** documentación.

Suite: **641 pruebas pasan, 9 omitidas** (589 originales + 52 nuevas: 13 en `test_ui_tema.py`, 28 en
`test_ui_pestana1.py`, 11 en `test_ui_pestanas23.py`). 5 pruebas originales se adaptaron sin cambiar lo que
verifican (`test_ui.py`: formatos de salida, GMS con decimales, zona forzada y método, opciones guardadas;
`test_masiva.py`: formato y opciones recalculan): la barra de opciones y la zona por pestaña ya no existen
(ahora `app.aplicar_ajustes`) y el error de un campo GMS se lee en el campo, no en una etiqueta general.

| Variante | Antes (F6) | Ahora | Autoprueba |
|---|---|---|---|
| onedir `dist\Coordenadas\Coordenadas.exe` | 26.5 MB · zip 11.5 MB · arranque 0.48 s / 0.25 s | 26.6 MB · zip 11.6 MB · 0.38 s / 0.38–0.40 s | OK, tema `sun-valley-light`, Segoe UI + Cascadia Mono |
| onefile `dist\onefile\Coordenadas.exe` | 11.5 MB · 1.08 s / 1.06–1.12 s | 11.6 MB · 1.42 s / 1.46–1.50 s | OK, mismo informe |

(Dos construcciones seguidas dieron 0.31–0.34 s y 1.09–1.23 s: el arranque varía ±0.1–0.3 s entre ejecuciones; el
dibujo de las imágenes del tema añade ~0.1–0.3 s.)

## U6 — Ajustes tras la primera prueba del usuario (2026-11-18)

Cambios pedidos y aprobados: valores por defecto PSAD56 → WGS84 (UTM) y WGS84 → UTM WGS84 (decimal/GMS); el datum
de entrada no se ofrece como salida (UTM → UTM); al reabrir solo se conservan los Ajustes y la ventana; "Copiar
todo" (Norte, Este); sin "Hemisferio sur."; "Zona" → "Huso"; **pestañas 2 y 3 solo UTM**; en masiva, entrada
`Norte, Este, Huso, Datum` con el datum leído de cada fila y salida `Norte WGS84, Este WGS84, Huso, Estado`; en
Excel, columnas nuevas `Norte WGS84, Este WGS84, Huso, Estado`; datums también como 1984, 1956 y 1969.

Cambios fuera de `ui/` (mínimos y aditivos): `core/constantes.py` (3 alias de datum), `core/servicio.py`
(`convertir_fila_utm` e `interpretar_pegado_utm`; no se modificó ninguna función existente) e `io/proceso.py` (la
columna "Zona X" pasa a "Huso", SIRGAS se nombra "WGS84" en los encabezados, mensajes "Huso"). Ninguna tolerancia.
Pruebas modificadas por la nueva especificación: `test_archivos.py` (2 encabezados "Huso"), la parte de interfaz de
`test_masiva.py`, `test_ui_excel.py`, `test_ui_pestana1.py` y `test_ui_pestanas23.py`; las pruebas de `core/` siguen
intactas. Las celdas numéricas de datum (1956 o 1956.0, como llegan desde Excel o un .xls) también se reconocen. Detalle en `INTERFAZ.md`.

Correcciones posteriores: (1) al copiar resultados de la conversión masiva Excel mostraba una fila vacía entre cada
fila: Tk convierte "\n" en CRLF y el texto ya traía "\r\n", de modo que quedaba "\r\r\n" (ahora `comun.copiar`
normaliza; prueba de regresión que lee el portapapeles real de Windows); (2) ícono propio (`recursos/coordenadas.ico`,
`tools/crear_icono.py`, `--icon` en `build.bat`) en lugar del de PyInstaller.

Suite tras U6: **653 pruebas pasan, 9 omitidas**. Ejecutables reconstruidos y verificados (autoprueba con tema
`sun-valley-light`): onedir 26.6 MB (zip 11.6 MB), arranque 0.32 s; onefile 11.6 MB, arranque 1.2–1.5 s (última construcción: 0.32 s y 1.25 s).
