"""Oráculo del .exe recorrido por la capa de parseo (textos tal como se escribieron en el .exe,
con coma decimal), incluidos los casos de entrada inválida (E18, E19, E22, E23, E25)."""
import pytest

from apoyo import HUSO_FORZADO_BORDES, OPCIONES, dif_m, leer_oraculo
from coordenadas.core.constantes import Metodo
from coordenadas.core.conversion import convertir_geo, convertir_utm
from coordenadas.core.errores import ErrorCoordenada, ErrorEntrada, ErrorRango
from coordenadas.core.parseo import parse_angulo, parse_gms_campos, parse_utm, parse_zona

R = Metodo.REPLICA_EXE


def _desde_texto(r):
    di, do = OPCIONES[r["opcion"]]
    v = r["entrada"].split("|")
    z = HUSO_FORZADO_BORDES.get(r["id"])
    if r["modo"] == "DEC":
        lat = parse_angulo(v[0], eje="lat").valor
        lon = parse_angulo(v[1], eje="lon").valor
        return convertir_geo(lat, lon, di, do, R, z)
    if r["modo"] == "GMS":
        lat = parse_gms_campos(v[0], v[1], v[2], "S", "lat")
        lon = parse_gms_campos(v[3], v[4], v[5], "O", "lon")
        return convertir_geo(lat, lon, di, do, R, z)
    return convertir_utm(parse_utm(v[0], "norte"), parse_utm(v[1], "este"), parse_zona(v[2]), di, do, R, z)


@pytest.mark.parametrize("r", [pytest.param(r, id=r["id"]) for r in leer_oraculo("bordes_escritorio.csv") + leer_oraculo("prueba_escritorio.csv")])
def test_oraculo_por_parseo(r):
    if r["id"] in ("E30", "E31"):
        pytest.skip("caso especial con prueba propia en test_golden_exe.py")
    if not r["out_norte"] or r["mensajes"] or r["id"] in ("E25", "E26", "E27", "E28", "E29"):
        with pytest.raises(ErrorCoordenada):
            _desde_texto(r)
        return
    res = _desde_texto(r)
    _, do = OPCIONES[r["opcion"]]
    assert res.zona == int(r["out_zona"])
    assert abs(res.norte - float(r["out_norte"])) <= 0.002
    assert abs(res.este - float(r["out_este"])) <= 0.002
    dn, de = dif_m(-float(r["out_lat_deg"]), -float(r["out_lon_deg"]), res.lat, res.lon, do)
    assert abs(dn) <= 0.003 and abs(de) <= 0.003


def test_e18_texto_no_numerico():
    with pytest.raises(ErrorEntrada):
        parse_angulo("abc", eje="lat")
    with pytest.raises(ErrorEntrada):
        parse_angulo("x70,5;", eje="lon")


def test_e19_campos_vacios():
    with pytest.raises(ErrorEntrada):
        parse_angulo("", eje="lat")


@pytest.mark.parametrize("m,s", [("27", "60"), ("60", "0")])
def test_e22_e23_minutos_o_segundos_60(m, s):
    with pytest.raises(ErrorRango):
        parse_gms_campos("33", m, s, "S", "lat")


def test_e24_59_9999_aceptado():
    assert parse_gms_campos("33", "27", "59,9999", "S", "lat") == pytest.approx(-(33 + 27 / 60 + 59.9999 / 3600))


def test_e25_grados_con_decimales_es_error():
    """El .exe truncaba 33,5° a 33° sin aviso; ahora es un error explícito."""
    with pytest.raises(ErrorEntrada, match="decimales"):
        parse_gms_campos("33,5", "0", "0", "S", "lat")


def test_salidas_del_exe_se_releen():
    """Los textos que mostraba el .exe ("7.956.582,773.  m.", " 18°  28'  28,8680\\"") se pueden
    pegar en la app nueva."""
    for r in leer_oraculo("c1_escritorio.csv"):
        if not r["out_norte_txt"]:
            continue
        assert parse_utm(r["out_norte_txt"], "norte") == pytest.approx(float(r["out_norte"]), abs=1e-6)
        assert parse_utm(r["out_este_txt"], "este") == pytest.approx(float(r["out_este"]), abs=1e-6)
        assert -parse_angulo(r["out_lat_txt"], eje="lat").valor == pytest.approx(float(r["out_lat_deg"]), abs=1e-9)
        assert -parse_angulo(r["out_lon_txt"], eje="lon").valor == pytest.approx(float(r["out_lon_deg"]), abs=1e-9)
