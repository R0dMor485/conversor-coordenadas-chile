"""Pruebas "golden" contra el oráculo del programa original (oraculo/*.csv), método Réplica.

Tolerancias (no se aflojan): Norte/Este <= 2 mm, lat/lon <= 3 mm, huso idéntico.
Los casos que corresponden a defectos del .exe verifican el comportamiento CORREGIDO.
"""
import pytest

from apoyo import HUSO_FORZADO_BORDES, OPCIONES, dif_m, leer_oraculo, num, proj_utm
from coordenadas.core.constantes import DATUMS, Metodo
from coordenadas.core.conversion import convertir_geo, convertir_utm
from coordenadas.core.errores import ErrorRango, ErrorSinParametros

R = Metodo.REPLICA_EXE
TOL_NE = 0.002
TOL_GEO = 0.003

# Casos que dependen del parseo de texto: se prueban en test_parseo_golden.py.
CASOS_DE_PARSEO = {"E18", "E19", "E22", "E23", "E25"}
# Casos especiales con prueba propia más abajo.
CASOS_ESPECIALES = {"E30", "E31"}


def _filas():
    filas = []
    for archivo in ("c1_escritorio.csv", "prueba_escritorio.csv", "bordes_escritorio.csv"):
        for r in leer_oraculo(archivo):
            filas.append(pytest.param(r, id=r["id"]))
    return filas


def _convertir(r, metodo=R):
    di, do = OPCIONES[r["opcion"]]
    v = r["entrada"].split("|")
    zona = HUSO_FORZADO_BORDES.get(r["id"])
    if r["modo"] == "DEC":
        return convertir_geo(-num(v[0]), -num(v[1]), di, do, metodo, zona)
    if r["modo"] == "GMS":
        lat = -(num(v[0]) + num(v[1]) / 60 + num(v[2]) / 3600)
        lon = -(num(v[3]) + num(v[4]) / 60 + num(v[5]) / 3600)
        return convertir_geo(lat, lon, di, do, metodo, zona)
    return convertir_utm(num(v[0]), num(v[1]), int(v[2]), di, do, metodo, zona)


def _comparar(res, r):
    _, do = OPCIONES[r["opcion"]]
    assert res.zona == int(r["out_zona"])
    assert abs(res.norte - float(r["out_norte"])) <= TOL_NE
    assert abs(res.este - float(r["out_este"])) <= TOL_NE
    dn, de = dif_m(-float(r["out_lat_deg"]), -float(r["out_lon_deg"]), res.lat, res.lon, do)
    assert abs(dn) <= TOL_GEO and abs(de) <= TOL_GEO


@pytest.mark.parametrize("r", _filas())
def test_oraculo_exe(r):
    if r["id"] in CASOS_DE_PARSEO or r["id"] in CASOS_ESPECIALES:
        pytest.skip("cubierto por otra prueba")
    msg = r["mensajes"]
    if "No exixten Parametros" in msg:
        # Defecto corregido: el .exe avisaba y luego escribía resultados con Δ = 0.
        with pytest.raises(ErrorSinParametros):
            _convertir(r)
    elif "Fuera de Límites" in msg:
        with pytest.raises(ErrorRango):
            _convertir(r)
    elif r["modo"] == "UTM" and r["id"] in {"E26", "E27", "E28", "E29"}:
        # Defecto corregido: el .exe no validaba huso ni rango en la entrada UTM.
        with pytest.raises(ErrorRango):
            _convertir(r)
    else:
        assert not msg
        _comparar(_convertir(r), r)


def test_e30_utm_lejos_del_meridiano_central():
    """Entrada UTM huso 18, Este 746 642 m (2.65° del MC). La inversa UTM->geo del .exe
    (serie TM truncada) tiene ~3 cm de error ahí; la nuestra coincide con PROJ. Partiendo de las
    geográficas de entrada que el propio .exe calculó y mostró, la salida coincide a <= 2 mm."""
    r = next(x for x in leer_oraculo("bordes_escritorio.csv") if x["id"] == "E30")
    ell = DATUMS["SIRGAS"].elipsoide
    t = proj_utm(ell, 18)
    lon_p, lat_p = t.transform(746642.695, 6297606.833, direction="INVERSE")
    g = [num(x) for x in r["in_gms_mostrado"].split("|")]
    lat_exe = -(g[0] + g[1] / 60 + g[2] / 3600)
    lon_exe = -(g[3] + g[4] / 60 + g[5] / 3600)
    dn, de = dif_m(lat_p, lon_p, lat_exe, lon_exe)
    assert 0.02 < max(abs(dn), abs(de)) < 0.05  # error de la inversa del .exe (documentado)
    res = convertir_utm(6297606.833, 746642.695, 18, "SIRGAS", "PSAD56", R)
    dn, de = dif_m(lat_p, lon_p, res.lat_entrada, res.lon_entrada)
    assert abs(dn) <= 0.001 and abs(de) <= 0.001  # nuestra inversa = PROJ
    # Desde las geográficas del .exe, nuestra salida coincide con la del .exe.
    _comparar(convertir_geo(lat_exe, lon_exe, "SIRGAS", "PSAD56", R), r)


def test_e31_huso_forzado_sin_espejado():
    """E31: huso 18 forzado con λ = 70.67° O (al este del MC 75°). El .exe espejaba el Este
    (97 121 m); el valor correcto (PROJ) es 1 000 000 − 97 121 ≈ 902 879 m. El Norte no cambia."""
    r = next(x for x in leer_oraculo("bordes_escritorio.csv") if x["id"] == "E31")
    res = _convertir(r)
    assert res.zona == 18 and res.zona_forzada
    assert abs(res.norte - float(r["out_norte"])) <= TOL_NE
    assert abs(res.este - (1_000_000 - float(r["out_este"]))) <= TOL_NE
    e, n = proj_utm(DATUMS["PSAD56"].elipsoide, 18).transform(res.lon, res.lat)
    assert abs(res.este - e) <= TOL_NE and abs(res.norte - n) <= TOL_NE


def test_e15_72_oeste_exacto_es_huso_19():
    """λ = 72°00′00″ exacto: el .exe mostraba la UTM de entrada en huso 18; el estándar es 19."""
    from coordenadas.core.utm import zona_estandar

    assert zona_estandar(-72.0) == 19
    res = convertir_geo(-38.1234, -72.0, "SIRGAS", "SIRGAS", R)
    assert res.zona == 19


def test_cantidad_de_casos_comparados():
    """Asegura que el oráculo no quedó vacío por error."""
    n = sum(1 for a in ("c1_escritorio.csv", "prueba_escritorio.csv", "bordes_escritorio.csv") for _ in leer_oraculo(a))
    assert n == 148 + 10 + 37
