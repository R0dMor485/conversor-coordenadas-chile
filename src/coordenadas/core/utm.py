"""Proyección transversa de Mercator (UTM) con la serie de Krüger de 6.º orden en n.

Referencia del método: Krüger (1912); coeficientes en la forma de Karney (2011),
"Transverse Mercator with an accuracy of a few nanometers", J. Geodesy 85:475–485.
Exactitud de la serie de 6.º orden: del orden de nanómetros dentro de ~4000 km del
meridiano central, muy por debajo de lo necesario aquí.

Parámetros UTM: k0 = 0.9996, Falso Este 500 000 m, Falso Norte 10 000 000 m en el sur.
Esta aplicación trabaja solo en el hemisferio sur.
"""
from __future__ import annotations

import math
from functools import lru_cache

from .constantes import FALSO_ESTE, FALSO_NORTE_SUR, K0, Elipsoide


def meridiano_central(zona: int) -> float:
    return zona * 6.0 - 183.0


def zona_estandar(lon: float) -> int:
    """Huso UTM estándar para una longitud en grados (−180..180).

    Bandas de 6° con el límite oeste inclusivo: λ = −72°00′00″ pertenece al huso 19
    (el .exe lo asignaba al 18).
    """
    if not -180.0 <= lon <= 180.0:
        raise ValueError(f"Longitud fuera de rango: {lon}")
    z = int(math.floor((lon + 180.0) / 6.0)) + 1
    return min(max(z, 1), 60)


@lru_cache(maxsize=None)
def _coeficientes(a: float, b: float) -> tuple[float, tuple[float, ...], tuple[float, ...], float]:
    n = (a - b) / (a + b)
    n2, n3, n4, n5, n6 = n * n, n ** 3, n ** 4, n ** 5, n ** 6
    radio = a / (1.0 + n) * (1.0 + n2 / 4.0 + n4 / 64.0 + n6 / 256.0)
    alfa = (
        n / 2 - 2 * n2 / 3 + 5 * n3 / 16 + 41 * n4 / 180 - 127 * n5 / 288 + 7891 * n6 / 37800,
        13 * n2 / 48 - 3 * n3 / 5 + 557 * n4 / 1440 + 281 * n5 / 630 - 1983433 * n6 / 1935360,
        61 * n3 / 240 - 103 * n4 / 140 + 15061 * n5 / 26880 + 167603 * n6 / 181440,
        49561 * n4 / 161280 - 179 * n5 / 168 + 6601661 * n6 / 7257600,
        34729 * n5 / 80640 - 3418889 * n6 / 1995840,
        212378941 * n6 / 319334400,
    )
    beta = (
        n / 2 - 2 * n2 / 3 + 37 * n3 / 96 - n4 / 360 - 81 * n5 / 512 + 96199 * n6 / 604800,
        n2 / 48 + n3 / 15 - 437 * n4 / 1440 + 46 * n5 / 105 - 1118711 * n6 / 3870720,
        17 * n3 / 480 - 37 * n4 / 840 - 209 * n5 / 4480 + 5569 * n6 / 90720,
        4397 * n4 / 161280 - 11 * n5 / 504 - 830251 * n6 / 7257600,
        4583 * n5 / 161280 - 108847 * n6 / 3991680,
        20648693 * n6 / 638668800,
    )
    e = math.sqrt((a * a - b * b) / (a * a))
    return radio, alfa, beta, e


def geo_a_tm(lat: float, lon: float, lon0: float, ell: Elipsoide) -> tuple[float, float]:
    """Geodésicas (grados) -> (x, y) transversa de Mercator sin k0 ni falsos orígenes (m)."""
    radio, alfa, _, e = _coeficientes(ell.a, ell.b)
    phi = math.radians(lat)
    dlam = math.radians(lon - lon0)
    s = math.sin(phi)
    # latitud conforme: t = tan χ
    t = math.sinh(math.atanh(s) - e * math.atanh(e * s))
    xi_p = math.atan2(t, math.cos(dlam))
    eta_p = math.atanh(math.sin(dlam) / math.sqrt(1.0 + t * t))
    xi, eta = xi_p, eta_p
    for j, aj in enumerate(alfa, start=1):
        xi += aj * math.sin(2 * j * xi_p) * math.cosh(2 * j * eta_p)
        eta += aj * math.cos(2 * j * xi_p) * math.sinh(2 * j * eta_p)
    return radio * eta, radio * xi


def tm_a_geo(x: float, y: float, lon0: float, ell: Elipsoide) -> tuple[float, float]:
    """(x, y) transversa de Mercator sin k0 ni falsos orígenes -> geodésicas (grados)."""
    radio, _, beta, e = _coeficientes(ell.a, ell.b)
    xi = y / radio
    eta = x / radio
    xi_p, eta_p = xi, eta
    for j, bj in enumerate(beta, start=1):
        xi_p -= bj * math.sin(2 * j * xi) * math.cosh(2 * j * eta)
        eta_p -= bj * math.cos(2 * j * xi) * math.sinh(2 * j * eta)
    sh = math.sinh(eta_p)
    c = math.cos(xi_p)
    tau_p = math.sin(xi_p) / math.hypot(sh, c)  # tan de la latitud conforme
    dlam = math.atan2(sh, c)
    # latitud geodésica a partir de la conforme (Newton, Karney 2011 ec. 19-21)
    e2 = e * e
    tau = tau_p
    for _ in range(10):
        sig = math.sinh(e * math.atanh(e * tau / math.sqrt(1.0 + tau * tau)))
        tau_i = tau * math.sqrt(1.0 + sig * sig) - sig * math.sqrt(1.0 + tau * tau)
        d = (tau_p - tau_i) / math.sqrt(1.0 + tau_i * tau_i) * (1.0 + (1.0 - e2) * tau * tau) / (
            (1.0 - e2) * math.sqrt(1.0 + tau * tau)
        )
        tau += d
        if abs(d) <= 1e-15 * max(1.0, abs(tau)):
            break
    return math.degrees(math.atan(tau)), lon0 + math.degrees(dlam)


def geo_a_utm(lat: float, lon: float, zona: int, ell: Elipsoide) -> tuple[float, float]:
    """Geodésicas (grados, hemisferio sur) -> (Norte, Este) en el huso dado."""
    x, y = geo_a_tm(lat, lon, meridiano_central(zona), ell)
    return FALSO_NORTE_SUR + K0 * y, FALSO_ESTE + K0 * x


def utm_a_geo(norte: float, este: float, zona: int, ell: Elipsoide) -> tuple[float, float]:
    """(Norte, Este) en el huso dado (hemisferio sur) -> (lat, lon) en grados."""
    x = (este - FALSO_ESTE) / K0
    y = (norte - FALSO_NORTE_SUR) / K0
    return tm_a_geo(x, y, meridiano_central(zona), ell)
