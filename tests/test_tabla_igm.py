"""Método "Tabla IGM vigente": fronteras, diferencias con la réplica y contraste con la web."""
import json
import math
import random

import pytest

from apoyo import OPCIONES, dif_m, js_web, modelo_web
from coordenadas.core.constantes import FRANJAS, Metodo
from coordenadas.core.conversion import convertir_geo
from coordenadas.core.errores import ErrorSinParametros
from coordenadas.core.transformacion import buscar_franja

T = Metodo.TABLA_IGM
R = Metodo.REPLICA_EXE

PUNTOS_C1 = [
    ("Arica", 18.4783, 70.3126), ("Putre", 18.1957, 69.5594), ("Iquique", 20.2141, 70.1524),
    ("Calama", 22.4567, 68.9293), ("Antofagasta", 23.6509, 70.3975), ("Taltal", 25.4053, 70.4857),
    ("Chanaral", 26.3479, 70.6224), ("Copiapo", 27.3668, 70.3323), ("Vallenar", 28.5708, 70.7581),
    ("LaSerena", 29.9027, 71.2519), ("Ovalle", 30.6014, 71.1997), ("Illapel", 31.6331, 71.1686),
    ("LosVilos", 31.9113, 71.5101), ("LaLigua", 32.4527, 71.2318), ("Valparaiso", 33.0472, 71.6127),
    ("Santiago", 33.4489, 70.6693), ("SanAntonio", 33.5933, 71.6217), ("Rancagua", 34.1708, 70.7444),
    ("Talca", 35.4264, 71.6554), ("Constitucion", 35.3331, 72.4122), ("Chillan", 36.6066, 72.1034),
    ("Concepcion", 36.8269, 73.0498), ("LosAngeles", 37.4697, 72.3537), ("Temuco", 38.7359, 72.5904),
    ("Valdivia", 39.8142, 73.2459), ("Osorno", 40.5739, 73.1335), ("PuertoMontt", 41.4693, 72.9424),
    ("Castro", 42.4823, 73.7624), ("Chaiten", 42.9167, 72.7083), ("Futaleufu", 43.1859, 71.8668),
    ("Coyhaique", 45.5712, 72.0685), ("Cochrane", 47.2536, 72.5735), ("VillaOHiggins", 48.4679, 72.5594),
    ("PuertoNatales", 51.7236, 72.5064), ("PuntaArenas", 53.1638, 70.9171), ("Porvenir", 53.2959, 70.3687),
    ("PuertoWilliams", 54.9352, 67.6164),
]


# --------------------------------------------------------------------------- fronteras
def test_tabla_continua_sin_huecos_ni_solapes():
    """Cada latitud del rango tiene exactamente una franja (regla [inferior, superior),
    con el límite superior final inclusivo)."""
    for datum, (lo, hi) in {"PSAD56": (17.5, 44.0), "SAD69": (17.5, 56.0)}.items():
        franjas = FRANJAS[T][datum]
        pasos = int(round((hi - lo) * 3600))  # cada 1″
        for i in range(pasos + 1):
            s = lo + i / 3600
            assert sum(f.contiene(s) for f in franjas) == 1, (datum, s)
        for s in (lo - 1e-9, hi + 1e-9, 0.0, 17.0, 60.0):
            assert sum(f.contiene(s) for f in franjas) == 0, (datum, s)


@pytest.mark.parametrize(
    "datum,s,esperado",
    [
        ("PSAD56", 17.5, (302, -272, 360)),
        ("PSAD56", 26.0 - 1e-9, (302, -272, 360)),
        ("PSAD56", 26.0, (328, -340, 329)),
        ("PSAD56", 36.0 - 1e-9, (328, -340, 329)),
        ("PSAD56", 36.0, (352, -403, 287)),
        ("PSAD56", 44.0, (352, -403, 287)),  # límite superior final inclusivo
        ("SAD69", 17.5, (59, 11, 52)),
        ("SAD69", 26.0, (59, 11, 52)),  # en la tabla oficial la frontera SAD69 es 32°, no 26°
        ("SAD69", 32.0 - 1e-9, (59, 11, 52)),
        ("SAD69", 32.0, (64, 0, 32)),
        ("SAD69", 36.0, (72, -10, 32)),
        ("SAD69", 44.0, (79, -13, 14)),
        ("SAD69", 56.0, (79, -13, 14)),
    ],
)
def test_fronteras_tabla(datum, s, esperado):
    assert buscar_franja(T, datum, -s).deltas == esperado


@pytest.mark.parametrize(
    "datum,s", [("PSAD56", 17.5 - 1e-9), ("PSAD56", 44.0 + 1e-9), ("SAD69", 17.4999), ("SAD69", 56.0001)]
)
def test_fuera_de_tabla(datum, s):
    with pytest.raises(ErrorSinParametros):
        buscar_franja(T, datum, -s)


@pytest.mark.parametrize(
    "datum,s,esperado",
    [
        ("PSAD56", 17.0 + 1e-9, (302, -272, 360)),
        ("PSAD56", 26.0, (328, -340, 329)),
        ("PSAD56", 36.0, (352, -403, 287)),
        ("PSAD56", 44.0 - 1e-9, (352, -403, 287)),
        ("SAD69", 17.0 + 1e-9, (59, 11, 52)),
        ("SAD69", 26.0 - 1e-9, (59, 11, 52)),
        ("SAD69", 26.0, (64, 0, 32)),
        ("SAD69", 44.0, (79, -13, 14)),
        ("SAD69", 56.0, (79, -13, 14)),
    ],
)
def test_fronteras_replica(datum, s, esperado):
    assert buscar_franja(R, datum, -s).deltas == esperado


@pytest.mark.parametrize("datum,s", [("PSAD56", 17.0), ("PSAD56", 44.0), ("SAD69", 17.0), ("SAD69", 56.0001)])
def test_fuera_de_replica(datum, s):
    with pytest.raises(ErrorSinParametros):
        buscar_franja(R, datum, -s)


# --------------------------------------------------------------------------- tabla vs réplica
def test_tabla_igual_a_replica_salvo_sad69_26_32():
    """Ambos métodos coinciden salvo SAD69 entre 26° y 32° S, donde difieren 10–13 m."""
    n_igual = n_dif = 0
    for _, la, lo in PUNTOS_C1:
        for op, (di, do) in OPCIONES.items():
            try:
                rt = convertir_geo(-la, -lo, di, do, T)
                rr = convertir_geo(-la, -lo, di, do, R)
            except ErrorSinParametros:
                # PSAD56 al sur de 44°: sin parámetros en ambos métodos
                assert "PSAD56" in op and la > 44
                for m in (T, R):
                    with pytest.raises(ErrorSinParametros):
                        convertir_geo(-la, -lo, di, do, m)
                continue
            dn, de = rt.norte - rr.norte, rt.este - rr.este
            d = math.hypot(dn, de)
            if "SAD69" in op and 26.0 <= la < 32.0:
                assert 10.0 <= d <= 13.0, (op, la, d)
                n_dif += 1
            else:
                assert d < 1e-6, (op, la, d)
                assert rt.zona == rr.zona
                n_igual += 1
    assert n_dif == 7 * 2 and n_igual == 148 - 14 - 14


def test_diferencias_de_borde_tabla_vs_replica():
    # 17°00′–17°30′: la réplica tiene parámetros, la tabla no.
    convertir_geo(-17.2, -70.1, "SIRGAS", "PSAD56", R)
    with pytest.raises(ErrorSinParametros):
        convertir_geo(-17.2, -70.1, "SIRGAS", "PSAD56", T)
    # PSAD56 en 44°00′ exacto: la tabla lo incluye, la réplica no.
    convertir_geo(-44.0, -72.1234, "SIRGAS", "PSAD56", T)
    with pytest.raises(ErrorSinParametros):
        convertir_geo(-44.0, -72.1234, "SIRGAS", "PSAD56", R)


# --------------------------------------------------------------------------- contraste web
def _puntos_interiores(n=400, semilla=7):
    """Puntos con 4 decimales (la web redondea la entrada a 0.001″) lejos de las fronteras."""
    rnd = random.Random(semilla)
    fronteras = (17.5, 26.0, 32.0, 36.0, 44.0, 56.0)
    out = []
    while len(out) < n:
        la = round(rnd.uniform(17.55, 55.95), 4)
        lo = round(rnd.uniform(66.3, 76.9), 4)
        if min(abs(la - f) for f in fronteras) < 0.02:
            continue
        # evita segundos "redondos": la web falla (NaN) si el resto de segundos es < 1e-6
        if abs((la * 3600) % 1) < 1e-3 or abs((lo * 3600) % 1) < 1e-3:
            continue
        out.append((la, lo))
    return out


def _web_a_grados(r):
    lat = abs(r["lat"]["grado"]) + r["lat"]["minuto"] / 60 + r["lat"]["segundo"] / 3600
    lon = abs(r["lon"]["grado"]) + r["lon"]["minuto"] / 60 + r["lon"]["segundo"] / 3600
    return -lat, -lon


def test_contra_modelo_web():
    W = modelo_web()
    n = 0
    for la, lo in _puntos_interiores():
        for op, (di, do) in OPCIONES.items():
            if "PSAD56" in op and la > 44:
                continue
            w = W.decimal(op, -la, -lo)
            if any(math.isnan(x) for x in (w["lat"]["segundo"], w["lon"]["segundo"])):
                continue
            r = convertir_geo(-la, -lo, di, do, T)
            wl, wo = _web_a_grados(w)
            dn, de = dif_m(wl, wo, r.lat, r.lon, do)
            assert abs(dn) <= 0.003 and abs(de) <= 0.003, (op, la, lo, dn, de)
            assert abs(w["utm"]["norte"] - r.norte) <= 0.003
            assert abs(w["utm"]["este"] - r.este) <= 0.003
            assert w["utm"]["huso"] == r.zona
            n += 1
    assert n > 1000


def test_contra_core_js_original():
    ctx = js_web()
    if ctx is None:
        pytest.skip("mini-racer o el core.js original no están disponibles (el core.js no se incluye en la copia pública)")
    nombres = {"SIRGAS": "WSG84", "PSAD56": "PSAD56", "SAD69": "SAD69"}
    n = 0
    for la, lo in _puntos_interiores(250, semilla=11):
        for op, (di, do) in OPCIONES.items():
            if "PSAD56" in op and la > 44:
                continue
            txt = ctx.call("calc", -la, -lo, nombres[di], nombres[do])
            if txt is None:
                continue
            w = json.loads(txt)
            if w["latitud"]["segundo"] is None or w["longitud"]["segundo"] is None:
                continue
            r = convertir_geo(-la, -lo, di, do, T)
            wl = -(abs(w["latitud"]["grado"]) + w["latitud"]["minuto"] / 60 + w["latitud"]["segundo"] / 3600)
            wo = -(abs(w["longitud"]["grado"]) + w["longitud"]["minuto"] / 60 + w["longitud"]["segundo"] / 3600)
            dn, de = dif_m(wl, wo, r.lat, r.lon, do)
            assert abs(dn) <= 0.003 and abs(de) <= 0.003, (op, la, lo, dn, de)
            assert abs(w["utm"]["norte"] - r.norte) <= 0.003
            assert abs(w["utm"]["este"] - r.este) <= 0.003
            assert w["utm"]["huso"] == r.zona
            n += 1
    assert n > 600


def test_core_js_falla_con_entradas_redondas():
    """Documenta el defecto web: −33.45/−70.65 no produce resultado en el core.js original.
    La app nueva sí lo convierte."""
    ctx = js_web()
    if ctx is None:
        pytest.skip("mini-racer o el core.js original no están disponibles (el core.js no se incluye en la copia pública)")
    assert ctx.call("calc", -33.45, -70.65, "WSG84", "PSAD56") is None
    convertir_geo(-33.45, -70.65, "SIRGAS", "PSAD56", T)
