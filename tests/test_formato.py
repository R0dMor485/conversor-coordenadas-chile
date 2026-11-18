"""Formato de salida: sin miles, separador decimal configurable, redondeo solo al mostrar."""
import locale

import pytest

from coordenadas.core import formato as F
from coordenadas.core.conversion import convertir_geo


@pytest.mark.parametrize(
    "x,dec,sep,txt",
    [
        (6318026.5434, 3, ".", "6318026.543"),
        (6318026.5434, 3, ",", "6318026,543"),
        (6318026.5, 0, ".", "6318027"),  # mitad hacia arriba
        (346642.4999, 0, ".", "346642"),
        (2.675, 2, ".", "2.68"),  # sobre la representación decimal, no la binaria
        (1234567.0, 2, ",", "1234567,00"),
        (-0.0000001, 3, ".", "0.000"),  # nunca "-0"
        (-33.4489123456, 6, ".", "-33.448912"),
        (-70.6693, 6, ",", "-70,669300"),
        (12345678.9, 1, ".", "12345678.9"),
    ],
)
def test_numero(x, dec, sep, txt):
    assert F.numero(x, dec, sep) == txt


def test_sin_separador_de_miles_en_ningun_caso():
    for x in (1234.5, 6318026.543, 999999.9999, 10000000.0):
        for d in range(0, 7):
            for sep in (".", ","):
                t = F.numero(x, d, sep)
                assert t.count(sep) <= 1 and " " not in t and ("," not in t if sep == "." else "." not in t)


def test_independiente_del_locale():
    original = locale.setlocale(locale.LC_ALL)
    for nombre in ("es-CL", "Spanish_Chile", "de-DE", "German_Germany"):
        try:
            locale.setlocale(locale.LC_ALL, nombre)
            break
        except locale.Error:
            continue
    try:
        assert F.numero(6318026.5434, 3, ".") == "6318026.543"
        assert F.gms(-33.4489, "lat") == "33° 26' 56.0400\" S"
    finally:
        locale.setlocale(locale.LC_ALL, original)


@pytest.mark.parametrize(
    "v,eje,sep,txt",
    [
        (-33.4489, "lat", ".", "33° 26' 56.0400\" S"),
        (-33.4489, "lat", ",", "33° 26' 56,0400\" S"),
        (-70.6693, "lon", ".", "70° 40' 09.4800\" O".replace("09.", "9.")),
        (70.5, "lon", ".", "70° 30' 0.0000\" E"),
        (33.5, "lat", ".", "33° 30' 0.0000\" N"),
        (-(33 + 59 / 60 + 59.99996 / 3600), "lat", ".", "34° 00' 0.0000\" S"),  # acarreo
        (-(18 + 28 / 60 + 0.3791 / 3600), "lat", ".", "18° 28' 0.3791\" S"),
        (-0.0, "lat", ".", "0° 00' 0.0000\" N"),
    ],
)
def test_gms(v, eje, sep, txt):
    assert F.gms(v, eje, sep=sep) == txt


def test_redondeo_solo_al_mostrar():
    r = convertir_geo(-33.4489, -70.6693, "SIRGAS", "PSAD56")
    assert r.norte != round(r.norte, 3)  # el núcleo conserva la precisión completa
    assert F.numero(r.norte, 0) == str(int(F.redondear(r.norte, 0)))
    assert F.valor_redondeado(r.norte, 3) == float(F.numero(r.norte, 3))


def test_texto_tabulado():
    t = F.texto_tabulado([["1", "2"], ["3", None]], ["A", "B"])
    assert t == "A\tB\r\n1\t2\r\n3\t"
    assert F.texto_tabulado([["1", "2"]]) == "1\t2"
