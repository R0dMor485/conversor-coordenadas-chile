"""Utilidades de prueba: lectura del oráculo, distancias y oráculos independientes (PROJ, JS web)."""
from __future__ import annotations

import csv
import importlib
import sys
from functools import lru_cache
from pathlib import Path

from coordenadas.core.constantes import DATUMS
from coordenadas.core.geodesia import distancia_aprox_m

RAIZ = Path(__file__).resolve().parents[1]
ORACULO = RAIZ / "oraculo"

OPCIONES = {
    "SIRGAS_PSAD56": ("SIRGAS", "PSAD56"),
    "SIRGAS_SAD69": ("SIRGAS", "SAD69"),
    "PSAD56_SIRGAS": ("PSAD56", "SIRGAS"),
    "SAD69_SIRGAS": ("SAD69", "SIRGAS"),
}

# Husos forzados ("Forzar Zonas", control oculto) usados en la fase de reconocimiento.
HUSO_FORZADO_BORDES = {"E31": 18, "E32": 18, "E33": 19, "E34": 19}


def num(texto: str) -> float:
    return float(texto.replace(",", "."))


def leer_oraculo(nombre: str) -> list[dict]:
    with open(ORACULO / nombre, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))


def dif_m(lat1, lon1, lat2, lon2, datum="SIRGAS") -> tuple[float, float]:
    """(ΔNorte, ΔEste) en metros entre dos geodésicas cercanas."""
    return distancia_aprox_m(lat1, lon1, lat2, lon2, DATUMS[datum].elipsoide)


# --------------------------------------------------------------------------- PROJ
def proj_utm(ell, zona: int):
    from pyproj import CRS, Transformer

    geo = CRS.from_proj4(f"+proj=longlat +a={ell.a} +b={ell.b} +no_defs")
    utm = CRS.from_proj4(f"+proj=utm +zone={zona} +south +a={ell.a} +b={ell.b} +units=m +no_defs")
    return Transformer.from_crs(geo, utm, always_xy=True)


# --------------------------------------------------------------------------- web
@lru_cache(maxsize=1)
def modelo_web():
    """tools/modelo_web.py (transcripción Python del core.js, de la fase de reconocimiento).
    Es opcional: en la copia pública del proyecto no se incluye y las pruebas que lo usan se omiten."""
    import pytest

    if not (RAIZ / "tools" / "modelo_web.py").exists():
        pytest.skip("tools/modelo_web.py no está en esta copia del proyecto")
    sys.path.insert(0, str(RAIZ / "tools"))
    return importlib.import_module("modelo_web")


@lru_cache(maxsize=1)
def js_web():
    """Contexto V8 (mini-racer) con el core.js ORIGINAL descargado del IGM, o None."""
    try:
        from py_mini_racer import MiniRacer
    except Exception:  # pragma: no cover
        return None
    ruta = RAIZ / "docs" / "web" / "TransformadorDatum" / "scripts" / "igm" / "core.js"
    if not ruta.exists():  # pragma: no cover
        return None
    ctx = MiniRacer()
    # Sustitutos mínimos de jQuery y console: el archivo registra un manejador de formulario al cargarse.
    ctx.eval(
        "var console={log:function(){}};"
        "var $=function(){return {submit:function(){},each:function(){},val:function(){return ''},"
        "attr:function(){return ''}}};"
    )
    ctx.eval(ruta.read_text(encoding="utf-8"))
    # Igual que la función Decimal() de la página, pero devolviendo el resultado en vez de pintarlo.
    ctx.eval(
        "function calc(lat,lon,o,f){try{var g=decimalAGeodesica(lat,lon);"
        "var r=gradosMinutosSegundos(g.latitud.grado,g.latitud.minuto,round(g.latitud.segundo,3),"
        "g.latitud.orientacion,g.longitud.grado,g.longitud.minuto,round(g.longitud.segundo,3),"
        "g.longitud.orientacion,0,o,f);return JSON.stringify(r);}catch(e){return null;}}"
    )
    return ctx
