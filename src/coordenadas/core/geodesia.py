"""Geodésicas <-> cartesianas geocéntricas (XYZ) y traslación de 3 parámetros."""
from __future__ import annotations

import math

from .constantes import Elipsoide

# Criterio de convergencia de XYZ -> geodésicas (radianes).
TOLERANCIA_RAD = 1e-12
MAX_ITERACIONES = 60


def geo_a_xyz(lat: float, lon: float, h: float, ell: Elipsoide) -> tuple[float, float, float]:
    """Latitud/longitud en grados y altura elipsoidal en metros -> X, Y, Z (m)."""
    phi = math.radians(lat)
    lam = math.radians(lon)
    e2 = ell.e2
    s = math.sin(phi)
    n = ell.a / math.sqrt(1.0 - e2 * s * s)
    c = math.cos(phi)
    return (
        (n + h) * c * math.cos(lam),
        (n + h) * c * math.sin(lam),
        (n * (1.0 - e2) + h) * s,
    )


def xyz_a_geo(x: float, y: float, z: float, ell: Elipsoide) -> tuple[float, float, float]:
    """X, Y, Z (m) -> latitud, longitud (grados) y altura elipsoidal (m).

    Iteración clásica φ = atan(Z / (p·(1 − e²·N/(N+h)))) hasta que la corrección sea
    menor o igual que 1e-12 rad (el .exe se detiene a 1e-10°, ≈ 1.7e-12 rad).
    """
    a, e2 = ell.a, ell.e2
    p = math.hypot(x, y)
    lon = math.degrees(math.atan2(y, x))
    if p == 0.0:
        lat = 90.0 if z >= 0 else -90.0
        return lat, lon, abs(z) - ell.b
    phi = math.atan2(z, p * (1.0 - e2))
    for _ in range(MAX_ITERACIONES):
        s = math.sin(phi)
        n = a / math.sqrt(1.0 - e2 * s * s)
        c = math.cos(phi)
        if abs(c) > 1e-3:
            h = p / c - n
        else:  # cerca del polo, forma estable
            h = z / s - n * (1.0 - e2)
        nuevo = math.atan2(z, p * (1.0 - e2 * n / (n + h)))
        if abs(nuevo - phi) <= TOLERANCIA_RAD:
            phi = nuevo
            break
        phi = nuevo
    else:  # pragma: no cover - no ocurre con datos terrestres
        raise ArithmeticError("XYZ -> geodésicas no convergió")
    s = math.sin(phi)
    n = a / math.sqrt(1.0 - e2 * s * s)
    c = math.cos(phi)
    h = p / c - n if abs(c) > 1e-3 else z / s - n * (1.0 - e2)
    return math.degrees(phi), lon, h


def trasladar_geo(
    lat: float,
    lon: float,
    origen: Elipsoide,
    destino: Elipsoide,
    deltas: tuple[float, float, float],
    h: float = 0.0,
) -> tuple[float, float, float]:
    """Traslación geocéntrica exacta de 3 parámetros: geo (h) -> XYZ -> +Δ -> geo.

    Devuelve (lat, lon, h) en el elipsoide destino.
    """
    x, y, z = geo_a_xyz(lat, lon, h, origen)
    dx, dy, dz = deltas
    return xyz_a_geo(x + dx, y + dy, z + dz, destino)


def radios(lat: float, ell: Elipsoide) -> tuple[float, float]:
    """Radios de curvatura (meridiano M, primer vertical N) en metros."""
    s = math.sin(math.radians(lat))
    w = 1.0 - ell.e2 * s * s
    return ell.a * (1.0 - ell.e2) / w ** 1.5, ell.a / math.sqrt(w)


def distancia_aprox_m(lat1: float, lon1: float, lat2: float, lon2: float, ell: Elipsoide) -> tuple[float, float]:
    """Diferencia (Norte, Este) aproximada en metros entre dos puntos cercanos."""
    m, n = radios((lat1 + lat2) / 2.0, ell)
    dn = math.radians(lat2 - lat1) * m
    de = math.radians(lon2 - lon1) * n * math.cos(math.radians((lat1 + lat2) / 2.0))
    return dn, de
