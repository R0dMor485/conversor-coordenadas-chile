# Interfaz: sistema visual

La interfaz (`src/coordenadas/ui/`) usa Tkinter/ttk con el tema **sv-ttk** (Sun Valley, modo claro) y un
sistema visual propio centralizado en `ui/tema.py`. Las maquetas aprobadas están en `docs/maqueta/`; las
capturas de cada estado (100 %, 125 % y 150 %) en `docs/ui_capturas/`.

## Módulos

| Módulo | Contenido |
|---|---|
| `tema.py` | Paleta (`Paleta`, `C`), tamaños (`T`), fuentes (`FUENTES`), elementos dibujados y estilos ttk. `aplicar(raiz)` lo instala todo. |
| `imagenes.py` | Rasterizador sin dependencias (bordes redondeados, íconos, PNG RGBA con antialiasing). |
| `componentes.py` | `Tarjeta`, `SelectorSegmentado`, `CampoConError`, `FilaResultado`, `BarraEstado`, además de `Encabezado`, `AreaDesplazable`, `divisor`, `entrada`, `combo`, `boton`. |
| `dialogo_ajustes.py` | Diálogo modal "Ajustes" (método, zona de salida, formato de números, entrada). |
| `app.py` | Ventana principal: DPI, escala, geometría recordada, pestañas, barra de estado, `aplicar_ajustes()`. |
| `tab_individual.py`, `tab_masiva.py`, `tab_excel.py` | Las tres pestañas. |
| `panel_salida.py`, `comun.py` | Datum y formato de salida compartidos; etiquetas de datum y método. |

## Comportamiento por pestaña

**Valores por defecto y arranque.** En cada arranque la aplicación abre en la pestaña 1 con todo en sus valores
por defecto: del `config.json` solo se restauran los **Ajustes** (método, decimales, separador, huso de salida,
positivos como S y O) y el **tamaño y posición de la ventana**. Pestaña, datums, formatos, carpeta del último
archivo y valores escritos no se recuerdan (`app.CLAVES_VENTANA`).

**Pestaña 1 (Calcular Coordenadas).**
- UTM → UTM por defecto: datum de entrada **PSAD56**, de salida **WGS84**. Al elegir Decimal o GMS en la entrada:
  entrada WGS84 y salida UTM WGS84; al volver a UTM, se restablece PSAD56 → WGS84.
- Con entrada y salida en UTM, el datum de entrada **no se ofrece** en la lista de salida; si se elige como
  entrada el datum que estaba en la salida, la salida pasa a otro (WGS84, o PSAD56 si la entrada es WGS84) y la
  barra de estado lo avisa. Con salida decimal/GMS, o con entrada decimal/GMS, el mismo datum sí es válido (solo
  cambia el formato o se proyecta sin cambio de datum).
- "Copiar todo" copia `Norte ⇥ Este` (UTM) o `Latitud ⇥ Longitud` / `lat, lon` (decimal), sin huso ni datum.

**Pestaña 2 (Conversión masiva), solo UTM.** Se pega `Norte, Este, Huso, Datum` (tabulador, `;`, `, ` o espacios;
el datum es el resto de la línea). El datum de entrada se lee de **cada fila**: WGS84/SIRGAS/1984, PSAD56/1956,
SAD69/1969; sin datum o desconocido, la fila es un error ("Falta el datum."). Solo se elige el datum de salida
(WGS84 por defecto). Salida: `Norte WGS84`, `Este WGS84`, `Huso` y `Estado` (el nombre lleva el datum elegido).
Si Norte y Este vienen invertidos se corrigen y la fila queda en amarillo. Una fila con coordenadas geográficas es
un error ("Se esperan coordenadas UTM").

**Pestaña 3 (Archivo Excel), solo UTM.** Columnas de Norte, Este y Huso (columna o valor fijo) y datum de entrada
(uno para todo el archivo o una columna, con los mismos nombres y años). El archivo nuevo agrega `Norte WGS84`,
`Este WGS84`, `Huso` y `Estado` (el datum de salida da el nombre). Con datum de entrada fijo, ese datum no se ofrece
como salida.

`core/` e `io/` conservan el soporte de coordenadas geográficas; solo se quitó de la interfaz.

## Cómo cambiar colores, fuentes y tamaños

Todo está en `ui/tema.py`; no hay colores ni tamaños sueltos en las pestañas.

- **Colores**: editar los campos de `Paleta` (por ejemplo `acento`, `error`, `fondo`). Los elementos
  dibujados (campos, botones, selector, casillas, pestañas, progreso) se regeneran al arrancar con esos
  colores, así que no hay imágenes que rehacer a mano.
- **Fuentes**: editar `FUENTES`. Cada entrada es `(familias candidatas, tamaño en puntos, negrita)`; se
  usa la primera familia instalada (Segoe UI → Tahoma → Arial; Cascadia Mono → Consolas → Courier New).
- **Tamaños y espaciado**: editar la clase `T`. Están en píxeles de diseño a 100 % (96 ppp) y se escalan
  con `tema.u()` según `tk scaling`; nunca se usan píxeles fijos en las pestañas.

### Equivalencias de tipografía (píxeles a 96 ppp → puntos)

Tk solo admite puntos enteros, de modo que se eligió el entero más cercano.

| Uso | Especificación | Fuente usada |
|---|---|---|
| Título de pantalla | 20 px semibold | 15 pt Segoe UI Semibold |
| Subtítulo, ayudas, errores en línea | 13 px | 10 pt Segoe UI |
| Título de sección (tarjeta) | 14 px semibold | 11 pt Segoe UI Semibold (10,5 pt) |
| Etiqueta de campo | 12 px medium | 9 pt Segoe UI Semibold (Segoe UI no trae el peso Medium) |
| Texto de campo / números en campos | 14 px | 11 pt Segoe UI / Cascadia Mono (respaldo Consolas) |
| Resultado | 22 px semibold mono | 16 pt Cascadia Mono SemiBold (16,5 pt); GMS 12 pt |
| Botones | 13 px semibold (principal 14 px) | 10 pt (principal 11 pt) Segoe UI Semibold |
| Barra de estado | 12 px | 9 pt Segoe UI |
| Cuadrícula (pestaña 2) | 12 px | 9 pt mono; encabezado 9 pt semibold |

### Modo oscuro (preparado, no implementado)

La paleta está separada del código de las pestañas, pero hoy los módulos hacen `from .tema import C`, es
decir, toman la paleta al importarse. Para agregar el modo oscuro habría que: (1) definir otra `Paleta`;
(2) leer `tema.C` en el momento de uso en lugar de importar `C` (o hacer `C` mutable); (3) llamar a
`sv_ttk.set_theme("dark")` en `aplicar`. No se hizo ahora a propósito.

## Escalado de pantalla (DPI)

`app.main()` declara la aplicación "system DPI aware" **antes** de crear la raíz y ajusta `tk scaling` al
valor del sistema. No se usa el modo por monitor porque Tk 8.6 no atiende `WM_DPICHANGED`: al arrastrar la
ventana a un monitor con otra escala quedaría con el tamaño equivocado; con el modo de sistema Windows la
reescala en el segundo monitor. Las piezas dibujadas (`imagenes.py`) se generan al tamaño real de la escala
vigente, así que son nítidas a 100 %, 125 % y 150 %.

## Acento y sv-ttk

sv-ttk usa su propio azul (#005FB8) dentro de sus imágenes; el acento de la maqueta es #1F5FBF. Para
obtener exactamente ese color, los botones, el selector segmentado, las casillas y opciones, las pestañas y
la barra de progreso se dibujan con elementos propios (`tema._crear_elementos`) y sv-ttk queda como base
(menús, barras de desplazamiento, lista desplegable). Además, `tema.aplicar` desactiva el enlace de sv-ttk
a `<<ThemeChanged>>`, que de otro modo repinta todos los widgets con su paleta (#FAFAFA).

## Ventana y persistencia

Tamaño inicial 880×720, mínimo 820×680 (a la escala vigente). El tamaño, la posición y si estaba
maximizada se guardan en `config.json` (`ultimas.ventana`, `ultimas.ventana_max`); si el archivo no se puede
escribir, la aplicación sigue sin error. Si la posición guardada ya no cae en ningún monitor, se centra.
La barra de título es la nativa de Windows.

## Ícono

Globo blanco sobre un cuadrado azul (#1F5FBF), dibujado por `imagenes.icono_app`. Se usa en la ventana
(`iconphoto`) y en el `.exe`: `tools/crear_icono.py` genera `recursos/coordenadas.ico` (9 tamaños, de 16 a 256 px)
y `build.bat` lo incorpora con `--icon`. Para cambiar el diseño se edita `icono_app` y se vuelve a ejecutar
`tools/crear_icono.py` antes de construir. `app.identidad_barra_tareas` fija el AppUserModelID para que Windows
agrupe la ventana con su propio ícono. Windows guarda en caché el ícono de los accesos anclados: tras actualizar
hay que desanclar y volver a anclar.

## Licencias de terceros

**sv-ttk 2.6.1** — Sun Valley ttk theme, © rdbende, licencia **MIT** (texto en
`LICENCIAS_TERCEROS.txt`, que `build.bat` copia junto al ejecutable). Se declara en `requirements.txt` y
`build.bat` incluye sus archivos de tema con `--collect-data sv_ttk`. `--autoprueba` del ejecutable
comprueba que el tema `sun-valley-light` realmente carga: sin esos archivos la interfaz caería en el tema
"clam" sin avisar y la verificación fallaría.
