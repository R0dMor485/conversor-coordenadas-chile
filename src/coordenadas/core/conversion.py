"""API de alto nivel: valida la entrada, cambia de datum y proyecta a UTM.

Toda la precisión se conserva; el redondeo ocurre solo al mostrar o exportar (core.formato).
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from . import constantes as C
from .constantes import DATUMS, Metodo
from .errores import ErrorEntrada, ErrorRango
from .transformacion import Paso, transformar
from .utm import geo_a_utm, meridiano_central, utm_a_geo, zona_estandar


@dataclass(frozen=True)
class Resultado:
    lat: float  # grados, negativa al sur (datum de salida)
    lon: float  # grados, negativa al oeste (datum de salida)
    norte: float
    este: float
    zona: int
    zona_forzada: bool
    datum_entrada: str
    datum_salida: str
    metodo: Metodo
    lat_entrada: float  # geodésicas de entrada (datum de entrada)
    lon_entrada: float
    pasos: tuple[Paso, ...] = ()


def hay_cambio_datum(datum_entrada: str, datum_salida: str) -> bool:
    return datum_entrada != datum_salida


def _finito(*vals: float) -> None:
    for v in vals:
        if v is None or not isinstance(v, (int, float)) or not math.isfinite(v):
            raise ErrorEntrada("Valor numérico inválido.")


def validar_geo(lat: float, lon: float, cambio_datum: bool) -> None:
    """Comprueba hemisferio y rango geográfico. La latitud con cambio de datum la
    acotan las franjas (se valida al transformar)."""
    _finito(lat, lon)
    if lat > 0:
        raise ErrorRango("Latitud en el hemisferio norte: esta aplicación trabaja solo en el hemisferio sur.")
    if lon > 0:
        raise ErrorRango("Longitud al este de Greenwich: esta aplicación trabaja solo con longitudes oeste.")
    s, w = -lat, -lon
    if cambio_datum:
        if not (C.LON_CONTINENTAL_OESTE_MIN < w <= C.LON_CONTINENTAL_OESTE_MAX):
            raise ErrorRango(
                f"Longitud {w:.6f}° O fuera de Chile continental: con cambio de datum se admite "
                f"más de {C.LON_CONTINENTAL_OESTE_MIN:.0f}° O y hasta {C.LON_CONTINENTAL_OESTE_MAX:.0f}° O."
            )
    else:
        if not (C.LAT_AMPLIADA_SUR_MIN <= s <= C.LAT_AMPLIADA_SUR_MAX):
            raise ErrorRango(
                f"Latitud {s:.6f}° S fuera del rango admitido sin cambio de datum "
                f"({C.LAT_AMPLIADA_SUR_MIN:.0f}° S a {C.LAT_AMPLIADA_SUR_MAX:.0f}° S)."
            )
        if not (C.LON_AMPLIADA_OESTE_MIN <= w <= C.LON_AMPLIADA_OESTE_MAX):
            raise ErrorRango(
                f"Longitud {w:.6f}° O fuera del rango admitido sin cambio de datum "
                f"({C.LON_AMPLIADA_OESTE_MIN:.0f}° O a {C.LON_AMPLIADA_OESTE_MAX:.0f}° O)."
            )


def validar_utm(norte: float, este: float, zona: int, cambio_datum: bool) -> None:
    _finito(norte, este)
    if not isinstance(zona, int) or isinstance(zona, bool):
        raise ErrorEntrada("El huso debe ser un número entero.")
    if cambio_datum:
        if zona not in C.HUSOS_CONTINENTALES:
            raise ErrorRango(f"Huso {zona} no válido: con cambio de datum solo se admiten los husos 18 y 19.")
    elif not (C.HUSO_AMPLIADO_MIN <= zona <= C.HUSO_AMPLIADO_MAX):
        raise ErrorRango(
            f"Huso {zona} no válido: sin cambio de datum se admiten los husos "
            f"{C.HUSO_AMPLIADO_MIN} a {C.HUSO_AMPLIADO_MAX}."
        )
    if not (C.ESTE_MIN <= este <= C.ESTE_MAX):
        raise ErrorRango(f"Este {este:.3f} m fuera de rango ({C.ESTE_MIN:.0f} a {C.ESTE_MAX:.0f} m).")
    if not (C.NORTE_MIN < norte <= C.NORTE_MAX):
        raise ErrorRango(
            f"Norte {norte:.3f} m fuera de rango (mayor que {C.NORTE_MIN:.0f} y hasta "
            f"{C.NORTE_MAX:.0f} m, hemisferio sur)."
        )


def _proyectar(lat: float, lon: float, datum: str, zona_salida: int | None) -> tuple[float, float, int, bool]:
    ell = DATUMS[datum].elipsoide
    if zona_salida is None:
        z = zona_estandar(lon)
        forzada = False
    else:
        if not isinstance(zona_salida, int) or not 1 <= zona_salida <= 60:
            raise ErrorEntrada(f"Huso de salida inválido: {zona_salida!r}")
        z = zona_salida
        forzada = True
        dist = abs(lon - meridiano_central(z))
        if dist > C.MAX_DIST_MC_FORZADO:
            raise ErrorRango(
                f"El punto está a {dist:.2f}° del meridiano central del huso {z}; "
                f"al forzar el huso se admite hasta {C.MAX_DIST_MC_FORZADO:.0f}°."
            )
    n, e = geo_a_utm(lat, lon, z, ell)
    return n, e, z, forzada


def _comprobar_datum(clave: str) -> None:
    if clave not in DATUMS:
        raise ErrorEntrada(f"Datum desconocido: {clave!r}")


def convertir_geo(
    lat: float,
    lon: float,
    datum_entrada: str,
    datum_salida: str,
    metodo: Metodo = Metodo.TABLA_IGM,
    zona_salida: int | None = None,
) -> Resultado:
    """Geodésicas (grados con signo, h = 0) en el datum de entrada -> Resultado."""
    _comprobar_datum(datum_entrada)
    _comprobar_datum(datum_salida)
    metodo = Metodo(metodo)
    validar_geo(lat, lon, hay_cambio_datum(datum_entrada, datum_salida))
    la, lo, pasos = transformar(lat, lon, datum_entrada, datum_salida, metodo)
    n, e, z, forzada = _proyectar(la, lo, datum_salida, zona_salida)
    return Resultado(la, lo, n, e, z, forzada, datum_entrada, datum_salida, metodo, lat, lon, pasos)


def convertir_utm(
    norte: float,
    este: float,
    zona: int,
    datum_entrada: str,
    datum_salida: str,
    metodo: Metodo = Metodo.TABLA_IGM,
    zona_salida: int | None = None,
) -> Resultado:
    """UTM (hemisferio sur) en el datum de entrada -> Resultado."""
    _comprobar_datum(datum_entrada)
    _comprobar_datum(datum_salida)
    cambio = hay_cambio_datum(datum_entrada, datum_salida)
    validar_utm(norte, este, zona, cambio)
    lat, lon = utm_a_geo(norte, este, zona, DATUMS[datum_entrada].elipsoide)
    return convertir_geo(lat, lon, datum_entrada, datum_salida, metodo, zona_salida)
