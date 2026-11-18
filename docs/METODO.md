# Método de cálculo de Coordenadas

Aplicación que reemplaza a `Datum_datum.exe` (IGM, "Version 2.1, Agosto de 2005"). Conserva su método de
transformación y la estructura de pestañas; la entrada/salida es nueva. Fuentes de los valores:
la tabla oficial publicada por el IGM y las salidas del programa original (`oraculo/`).
Ningún código del .exe ni de la web se copió: solo valores y método.

Convención interna: latitud negativa al sur, longitud negativa al oeste, grados decimales, precisión completa
(el redondeo ocurre solo al mostrar o exportar).

## 1. Resumen

```
entrada (geo o UTM, datum A)
  └─ UTM → geo (Krüger inversa, elipsoide A)                [si la entrada es UTM]
geo A (h = 0) → XYZ (A) → + (ΔX, ΔY, ΔZ) de la franja → XYZ → geo B (iterativo, se descarta h)
  └─ geo B → UTM (Krüger, huso automático con la longitud transformada, o forzado)
```

- Traslación geocéntrica **exacta** de 3 parámetros, sin rotaciones ni escala, con parámetros enteros por
  franja de latitud (no Molodensky diferencial; el IGM lo llama "modelo de Molodensky" en sentido genérico).
- **Precisión declarada del método: ±5 m** (constante del IGM, el "Delta Error" del .exe). Se muestra solo en la
  barra de estado junto al método usado. No es un cálculo por punto.
- Altura: **h = 0** siempre (el .exe tampoco tenía altura).

## 2. Datums y elipsoides

| Datum | Elipsoide | a (m) | b (m) |
|---|---|---|---|
| SIRGAS-Chile / WGS84 | WGS84 / GRS80 | 6 378 137 | 6 356 752.3141 |
| PSAD56 | Internacional 1924 | 6 378 388 | 6 356 911.946 |
| SAD69 | GRS67 (Sudamericano 1969) | 6 378 160 | 6 356 774.719 |

Valores tal como están en el .exe (e² = (a² − b²)/a²). Diferencia con GRS80 exacto (b = 6 356 752.31414): < 0.1 mm.

## 3. Parámetros por franja

ΔX, ΔY, ΔZ en metros, sentido **SIRGAS → datum local**. El sentido inverso usa los mismos valores con signo
cambiado. La franja se elige con la **latitud de entrada** del paso (en el datum de origen), como en ambos
programas del IGM. Latitudes en grados sur.

### 3.1 "Tabla IGM vigente" (por defecto)

Fronteras de la tabla oficial publicada por el IGM, **continuas y sin huecos**. Regla:
**[inferior, superior)**, y el límite superior de la última franja es **inclusivo**.

| Datum | Franja | ΔX | ΔY | ΔZ |
|---|---|---|---|---|
| PSAD56 | [17°30′, 26°00′) | 302 | −272 | 360 |
| PSAD56 | [26°00′, 36°00′) | 328 | −340 | 329 |
| PSAD56 | [36°00′, 44°00′] | 352 | −403 | 287 |
| SAD69 | [17°30′, 32°00′) | 59 | 11 | 52 |
| SAD69 | [32°00′, 36°00′) | 64 | 0 | 32 |
| SAD69 | [36°00′, 44°00′) | 72 | −10 | 32 |
| SAD69 | [44°00′, 56°00′] | 79 | −13 | 14 |

La web del IGM (`core.js`) usa estos valores con franjas inclusivas y huecos de 1′ (26°00′–26°01′, etc.); aquí los
huecos se cierran con la regla anterior. Probado cada 1″ de 17°30′ a 56° (una y solo una franja por latitud).

### 3.2 "Réplica Datum_datum.exe"

Fronteras del binario (rutina `DELTAS`):

| Datum | Franja | ΔX | ΔY | ΔZ |
|---|---|---|---|---|
| PSAD56 | (17°, 26°) | 302 | −272 | 360 |
| PSAD56 | [26°, 36°) | 328 | −340 | 329 |
| PSAD56 | [36°, 44°) | 352 | −403 | 287 |
| SAD69 | (17°, 26°) | 59 | 11 | 52 |
| SAD69 | **[26°, 36°)** | 64 | 0 | 32 |
| SAD69 | [36°, 44°) | 72 | −10 | 32 |
| SAD69 | [44°, 56°] | 79 | −13 | 14 |

### 3.3 Fronteras exactas (qué parámetros se usan)

| Latitud sur | PSAD56 Tabla | PSAD56 Réplica | SAD69 Tabla | SAD69 Réplica |
|---|---|---|---|---|
| 17°00′ | sin parámetros | sin parámetros¹ | sin parámetros | sin parámetros¹ |
| 17°00′–17°30′ | sin parámetros | 302/−272/360 | sin parámetros | 59/11/52 |
| 26°00′ | 328/−340/329 | 328/−340/329 | 59/11/52 | **64/0/32** |
| 26°–32° | = | = | 59/11/52 | **64/0/32** (10–13 m de diferencia) |
| 32°00′ | 328/−340/329 | 328/−340/329 | 64/0/32 | 64/0/32 |
| 36°00′ | 352/−403/287 | 352/−403/287 | 72/−10/32 | 72/−10/32 |
| 44°00′ | 352/−403/287 | sin parámetros | 79/−13/14 | 79/−13/14 |
| 56°00′ | — | — | 79/−13/14 | 79/−13/14 |

¹ El .exe en 17°00′ exacto: PSAD56 avisa "No exixten Parametros" y escribe un resultado con Δ = 0; SAD69 cae en la
rama "por defecto" y usa 79/−13/14 (la franja de 44°–56°). Ambos son defectos; la réplica no da resultado en 17°00′.

### 3.4 Composición PSAD56 ↔ SAD69

No hay parámetros directos: se pasa por SIRGAS en **dos pasos independientes**, cada uno con h = 0 en su entrada
(equivale a encadenar dos conversiones del programa original). La franja del primer paso se elige con la latitud
de entrada (PSAD56 o SAD69) y la del segundo con la latitud SIRGAS intermedia. Si el paso intermedio cae fuera de
las franjas, el error lo indica. Probado: idéntico a encadenar los dos pasos (1 200 casos).

### 3.5 Propiedades de ida y vuelta (inherentes al método)

- Lejos de las fronteras, ida y vuelta de datum cierra a **≤ 6 mm** (no cero: cada paso descarta la altura de
  salida y la siguiente entrada usa h = 0, igual que el .exe). Probado con 4 000 puntos, tolerancia 1 cm.
- Junto a una frontera, la ida y la vuelta pueden usar franjas distintas (la latitud cambia de lado al transformar):
  p. ej. SIRGAS 32°00′00.6″ S → SAD69 usa 64/0/32 y la vuelta 59/11/52: **≈ 10.6 m**. Probado y documentado.

## 4. Proyección UTM

- Transversa de Mercator con la **serie de Krüger de 6.º orden** en n (forma de Karney 2011); inversa con la serie
  β y Newton para la latitud. k₀ = 0.9996, Falso Este 500 000 m, Falso Norte 10 000 000 m (solo hemisferio sur).
- Exactitud contra PROJ (pyproj 3.8, mismos a/b): < 0.01 mm en los tres elipsoides hasta ±6° del meridiano central
  y de 0.5° a 79.5° S. El .exe usaba una serie tipo TM 5-241 (≤ 2 mm en la directa; ver §7 para la inversa).
- **Huso automático**: bandas de 6° con el límite oeste inclusivo, `huso = ⌊(λ + 180)/6⌋ + 1`. **72°00′00″ O exacto →
  huso 19** (el .exe lo ponía en el 18). El huso de salida se calcula con la **longitud transformada** (un punto puede
  cambiar de huso al cambiar de datum; caso E17 del oráculo).
- **Zona forzada (18 o 19)**: proyección real sobre el meridiano central de esa zona (sin espejado). Se admite hasta
  9° del meridiano central (la serie sigue siendo exacta muy por encima de eso; el límite evita resultados sin sentido,
  como forzar huso 19 en Isla de Pascua).

## 5. Rangos admitidos

| Situación | Latitud | Longitud | Husos UTM de entrada |
|---|---|---|---|
| Con cambio de datum (Chile continental) | la de las franjas del método (§3) | más de 66° O y hasta 77° O (como el .exe: 66.0 rechazado, 77.0 aceptado) | 18 y 19 |
| Sin cambio de datum (mismo datum de entrada y salida; incluye islas y Antártica) | 0° a 80° S | 50° O a 120° O | 11 a 22 (huso general) |

- Solo hemisferio sur y longitudes oeste. Entradas UTM: Este 100 000–900 000 m, Norte > 0 y ≤ 10 000 000 m; luego
  se valida el rango geográfico del punto. Fuera de rango = mensaje claro (nunca un resultado).
- Ejemplos sin cambio de datum: Isla de Pascua (huso 12), Salas y Gómez (13), Juan Fernández (17), Antártica (21).

## 6. Geodésicas ↔ XYZ

`N = a/√(1 − e² sin²φ)`; `X = (N+h) cos φ cos λ`, `Y = (N+h) cos φ sin λ`, `Z = (N(1−e²)+h) sin φ`.
Inversa iterativa `φ = atan(Z / (p·(1 − e²N/(N+h))))` hasta una corrección ≤ **1e-12 rad** (el .exe paraba a 1e-10°).
Contra PROJ `geocent`: < 0.1 mm.

## 7. Diferencias con Datum_datum.exe (método Réplica)

Coincidencia con el oráculo (195 filas; `oraculo/*.csv`): **ΔN ≤ 0.59 mm, ΔE ≤ 0.83 mm, Δlat ≤ 1.5 mm, Δlon ≤ 1.4 mm,
huso idéntico**. Validación ampliada con el modo Excel del .exe (3 000 conversiones aleatorias, 750 por sentido,
17.02°–55.98° S y 66.05°–75.95° O): **ΔN/ΔE ≤ 0.52 mm** (el .exe escribe al milímetro) y **lat/lon ≤ 0.006 mm**, 3 000/3 000.

| Caso | .exe | App | Motivo |
|---|---|---|---|
| Sin parámetros (PSAD56 ≥ 44°, 17°00′ exacto) | avisa y escribe resultados con Δ = 0 ("72° 60' ,0000"") | error claro, sin resultado | defecto corregido |
| Huso forzado al este del meridiano central | Este espejado (E31: 97 121 m) | proyección real (902 879 m); Norte igual | defecto corregido |
| 72°00′00″ O exacto | huso 18 | huso 19 | convención estándar |
| Entrada UTM | sin validar huso ni rango (huso 17, Este 846 642, Norte 12 000 000 → resultados espurios) | husos 18/19 (o 11–22 sin cambio de datum), Este y Norte acotados, rango geográfico | defecto corregido |
| Entrada UTM lejos del meridiano central | inversa UTM→geo con ~3 cm de error a 2.65° del MC (E30) | inversa exacta (= PROJ) | precisión; partiendo de las geográficas del .exe la salida coincide a 0.3 mm |
| GMS con grados decimales (33,5°) | trunca a 33° sin aviso | error explícito | defecto corregido |
| SAD69 en 17°00′ exacto | usa 79/−13/14 (rama por defecto) | sin parámetros | defecto corregido |
| Longitud en el modo Excel | solo escribe filas con λ < 76° O | hasta 77° O, como el modo individual del .exe | coherencia entre modos |
| Configuración regional | depende de la coma decimal; en Excel escribe números sin decimales en es-CL | parseo y formato propios; celdas numéricas | defecto corregido |
| Entrada | solo valores positivos (S/O implícitos) | signos, letras N S E O W, GMS en texto, miles/decimal con punto o coma | ampliación |

## 8. Diferencias con la web del IGM (TransformadorDatum, `core.js`)

Contraste ejecutado durante el desarrollo contra el `core.js` de la web del IGM (corrido en V8 local, sin red) y
contra una transcripción Python del mismo; esos archivos no se incluyen en este repositorio.
En el interior de las franjas (1 362 conversiones): **≤ 1.9 mm en lat/lon y ≤ 2.2 mm en N/E** (por los redondeos
de la web: entrada a 0.001″, salida a 0.0001″ y UTM recalculada desde los GMS redondeados).

| Caso | Web | App |
|---|---|---|
| Huecos de 1′ entre franjas y < 17°30′ | sin resultado (y quedan en pantalla los anteriores) | fronteras continuas |
| Entradas decimales "redondas" (−33.45/−70.65) | sin resultado (NaN); confirmado ejecutando `core.js` | se convierten |
| Fronteras exactas 26°00′ (PSAD56), 32°00′ (SAD69), 36°00′, 44°00′ | franja inferior (inclusiva) | franja superior ([inferior, superior)) |
| e² y b redondeados, XYZ→geo de Bowring, serie UTM truncada | < 0.1 mm a 3° del MC | serie exacta |
| Altura en GMS | sí | no (h = 0) |

## 9. Entrada y salida (decisiones)

- **Independiente de la configuración regional**: el punto y la coma se interpretan en `core/parseo.py`; la salida
  usa el separador elegido en Ajustes (punto por defecto). Ningún número lleva separador de miles.
- **Positivos como S y O** (opción, activada por defecto). El signo o la letra explícitos siempre mandan
  ("+33" es norte; "33 S" es sur aunque la opción esté apagada).
- **Miles y decimal en UTM**: "6.318.026,543" → 6 318 026.543. Si un texto admite dos lecturas ("346.642"), se
  decide por magnitud (Norte 3.7–8.1 millones, Este 100 000–900 000); si ambas o ninguna sirven → error. Una celda
  **numérica** de Excel se usa tal cual (no tiene ambigüedad).
- **GMS**: grados con decimales junto a minutos (o minutos con decimales junto a segundos) = error explícito.
  Minutos y segundos deben ser < 60 (59.9999″ se acepta). Se acepta grados-minutos decimales ("33 26.934 S").
- **Conversión masiva y archivos** (solo UTM en la interfaz): cada fila trae Norte, Este, Huso y Datum de entrada
  (WGS84/SIRGAS/1984, PSAD56/1956, SAD69/1969); sin datum o con uno desconocido es un error. Los rangos (Norte
  3.7–8.1 millones, Este 100 000–900 000) detectan Norte/Este invertidos: la fila queda en amarillo; lo ambiguo o
  fuera de rango, en rojo con el motivo, sin convertir. El núcleo conserva la detección de coordenadas geográficas
  (lat/lon por rango y letras N/S/E/O), que la interfaz ya no usa.
- **Redondeo** solo al mostrar o exportar, "mitad hacia arriba" sobre la representación decimal del número.
  Decimales por defecto: UTM 0, grados decimales 6, segundos GMS 4 (0.0001″ ≈ 3 mm).
- **"Copiar lat, lon"**: separa con ", " (punto decimal) o "; " (coma decimal). "Copiar Norte y Este": tabulador.
