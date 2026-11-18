"""Cambio de datum: traslación geocéntrica de 3 parámetros por franjas de latitud.

- La franja se elige con la latitud de ENTRADA (en el datum de origen del paso).
- SIRGAS -> local usa (ΔX, ΔY, ΔZ); local -> SIRGAS usa los mismos valores con signo cambiado.
- PSAD56 <-> SAD69 se compone pasando por SIRGAS: dos pasos independientes, cada uno con
  h = 0 en su entrada (equivale a encadenar dos conversiones del programa original).
"""
from __future__ import annotations

from dataclasses import dataclass

from .constantes import DATUMS, FRANJAS, Franja, Metodo, grados_min
from .errores import ErrorSinParametros
from .geodesia import trasladar_geo


@dataclass(frozen=True)
class Paso:
    origen: str
    destino: str
    franja: Franja
    deltas: tuple[int, int, int]
    lat_entrada: float  # latitud con la que se eligió la franja


def _lat_texto(lat: float) -> str:
    s = abs(lat)
    tot = round(s * 3600.0, 2)
    g = int(tot // 3600)
    m = int((tot - g * 3600) // 60)
    seg = tot - g * 3600 - m * 60
    hemi = "S" if lat < 0 else "N"
    return f"{g}°{m:02d}′{seg:05.2f}″ {hemi}"


def rango_con_parametros(metodo: Metodo, datum_local: str) -> tuple[float, float]:
    """(mínimo, máximo) de latitud sur cubierta por las franjas del datum local."""
    fr = FRANJAS[metodo][datum_local]
    return min(f.inferior for f in fr), max(f.superior for f in fr)


def buscar_franja(metodo: Metodo, datum_local: str, lat: float) -> Franja:
    """Franja que contiene la latitud (grados, negativa al sur)."""
    s = -lat
    for f in FRANJAS[metodo][datum_local]:
        if f.contiene(s):
            return f
    lo, hi = rango_con_parametros(metodo, datum_local)
    raise ErrorSinParametros(
        f"No existen parámetros SIRGAS↔{datum_local} para la latitud {_lat_texto(lat)} "
        f"(con parámetros: {grados_min(lo)} S a {grados_min(hi)} S, método {metodo.etiqueta})."
    )


def _paso(lat: float, lon: float, origen: str, destino: str, metodo: Metodo) -> tuple[float, float, Paso]:
    if origen == "SIRGAS":
        f = buscar_franja(metodo, destino, lat)
        d = f.deltas
    else:
        f = buscar_franja(metodo, origen, lat)
        d = (-f.dx, -f.dy, -f.dz)
    la, lo, _h = trasladar_geo(lat, lon, DATUMS[origen].elipsoide, DATUMS[destino].elipsoide, d, h=0.0)
    return la, lo, Paso(origen, destino, f, d, lat)


def transformar(
    lat: float, lon: float, datum_entrada: str, datum_salida: str, metodo: Metodo
) -> tuple[float, float, tuple[Paso, ...]]:
    """Transforma geodésicas (grados, h = 0) entre datums. Devuelve (lat, lon, pasos)."""
    if datum_entrada == datum_salida:
        return lat, lon, ()
    if datum_entrada == "SIRGAS" or datum_salida == "SIRGAS":
        la, lo, p = _paso(lat, lon, datum_entrada, datum_salida, metodo)
        return la, lo, (p,)
    la1, lo1, p1 = _paso(lat, lon, datum_entrada, "SIRGAS", metodo)
    try:
        la2, lo2, p2 = _paso(la1, lo1, "SIRGAS", datum_salida, metodo)
    except ErrorSinParametros as e:
        raise ErrorSinParametros(
            f"Paso intermedio {datum_entrada}→SIRGAS→{datum_salida}: {e.mensaje}"
        ) from None
    return la2, lo2, (p1, p2)
