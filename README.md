# Coordenadas

Conversor de datum y coordenadas para Chile (SIRGAS-Chile/WGS84, PSAD56, SAD69) que reemplaza a
`Datum_datum.exe` del IGM. Mismo método (traslación de 3 parámetros por franjas de latitud), dos variantes
seleccionables ("Tabla IGM vigente" y "Réplica Datum_datum.exe"), y tres pestañas: un punto (UTM, decimal o GMS),
conversión masiva (pegar/copiar) y archivos Excel/csv, estas dos solo con coordenadas UTM. Detalle del método y diferencias: [docs/METODO.md](docs/METODO.md).
La interfaz (tema sv-ttk y sistema visual propio, escalado de pantalla, diálogo Ajustes) está descrita en
[docs/INTERFAZ.md](docs/INTERFAZ.md), con las capturas de cada estado en `docs/ui_capturas/`.

## Ejecutar desde el código

Requiere Python 3.12 en `.venv`:

```bat
py -3.12 -m venv .venv
.venv\Scripts\pip install -r requirements-dev.txt
.venv\Scripts\pythonw run.pyw
```

(o `.venv\Scripts\python -m coordenadas` con `src` en `PYTHONPATH`). Los ajustes (diálogo **Ajustes**) y el
tamaño y posición de la ventana se guardan en `config.json` junto al ejecutable (o en la raíz del proyecto al
ejecutar desde el código); si no se puede escribir, la aplicación sigue sin error.

## Probar

```bat
.venv\Scripts\python -m pytest -q                       & rem todo salvo volumen (~10 s)
.venv\Scripts\python -m pytest -q -m "lento or not lento" & rem incluye 100 000 filas xlsx (~40 s)
```

Incluye pruebas golden contra salidas del programa original (`oraculo/`), contra PROJ (pyproj) y de la interfaz. Resultados por fase: [docs/progreso.md](docs/progreso.md).

## Construir

```bat
build.bat              & rem pruebas + dist\Coordenadas\ (carpeta) + dist\Coordenadas.zip + dist\onefile\Coordenadas.exe
build.bat sinpruebas
```

`build.bat` termina verificando ambos ejecutables copiados a una carpeta temporal fuera del proyecto, con un PATH
mínimo (`tools\verificar_exe.py`, informe en `build\verificacion.json`): la autoprueba exige que el tema
`sun-valley-light` cargue desde el paquete, y se guarda una captura de la ventana del .exe. El tema sv-ttk
(licencia MIT) viaja con `--collect-data sv_ttk`; `LICENCIAS_TERCEROS.txt` se copia junto a los ejecutables.

## Licencia y aviso

Código bajo licencia **MIT** (archivo `LICENSE`); las licencias de los componentes de terceros que se empaquetan
están en `LICENCIAS_TERCEROS.txt`.

Esta herramienta es un proyecto personal y **no oficial**: no tiene relación con el Instituto Geográfico Militar
(IGM) ni con SIRGAS-Chile. La precisión declarada del método es de ±5 m y se entrega sin garantía de ningún tipo;
verifica los resultados antes de usarlos en trabajos con valor técnico o legal.

## Estructura

```
src/coordenadas/core/   constantes, geodesia, utm, transformacion, conversion, parseo, formato, servicio (sin tkinter)
src/coordenadas/io/     csv_io, excel_io, proceso
src/coordenadas/ui/     app, tema, componentes, imagenes, dialogo_ajustes, panel_salida, comun, tab_*
tests/                  pruebas (pytest)
docs/                   METODO.md, INTERFAZ.md, progreso.md, maqueta/ y ui_capturas/
oraculo/                salidas del programa original usadas como referencia
tools/                  ícono, capturas de la interfaz y verificación del .exe
```
