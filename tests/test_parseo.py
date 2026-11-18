"""Parseo tolerante de textos reales (core.parseo)."""
import pytest

from coordenadas.core.errores import ErrorAmbiguo, ErrorEntrada, ErrorRango
from coordenadas.core.parseo import (
    candidatos_numero,
    dividir_linea,
    interpretar_fila,
    parse_angulo,
    parse_gms_campos,
    parse_numero,
    parse_utm,
    parse_zona,
)

LAT = -(33 + 26 / 60 + 56.04 / 3600)


# --------------------------------------------------------------------------- números
@pytest.mark.parametrize(
    "texto,esperado",
    [
        ("6318026.543", [6318026.543]),
        ("6318026,543", [6318026.543]),
        ("6.318.026,543", [6318026.543]),
        ("6.318.026,543.", [6318026.543]),  # salida del .exe: punto final suelto
        ("7.956.582,773.  m.", [7956582.773]),  # salida completa del .exe
        ("6,318,026.543", [6318026.543]),
        ("6 318 026,543", [6318026.543]),
        ("6 318 026,5", [6318026.5]),
        ("6.318.026", [6318026.0]),
        ("346.642", [346.642, 346642.0]),
        ("346,642", [346.642, 346642.0]),
        ("346642,5", [346642.5]),
        ("0,500", [0.5]),
        (",5", [0.5]),
        ("-12,5", [-12.5]),
        ("−12.5", [-12.5]),
        ("+7", [7.0]),
        ("361.598,528 m", [361598.528]),
    ],
)
def test_candidatos_numero(texto, esperado):
    assert candidatos_numero(texto) == esperado


@pytest.mark.parametrize("texto", ["", "  ", "abc", "1,2,3,4", "6.31.026", "1.234.5678", "12a", "1..2", "6 31 026", "x70,5;", "1,234.5,6"])
def test_numero_invalido(texto):
    with pytest.raises(ErrorEntrada):
        candidatos_numero(texto)


def test_parse_numero_desambigua_por_magnitud():
    assert parse_numero("346.642", (100_000, 900_000)) == 346642.0
    assert parse_numero("346.642", (0, 1000)) == 346.642
    with pytest.raises(ErrorAmbiguo):
        parse_numero("346.642")
    with pytest.raises(ErrorRango):
        parse_numero("5.000", (100_000, 900_000))


@pytest.mark.parametrize(
    "texto,eje,esperado",
    [
        ("6.318.026,543", "norte", 6318026.543),
        ("6.318.026,543.", "norte", 6318026.543),
        ("6318026", "norte", 6318026.0),
        ("346.642", "este", 346642.0),
        ("346,642", "este", 346642.0),
        ("346642.695", "este", 346642.695),
        ("2.000.000", "norte", 2000000.0),  # lectura única aunque fuera del rango típico
    ],
)
def test_parse_utm(texto, eje, esperado):
    assert parse_utm(texto, eje) == esperado


@pytest.mark.parametrize("texto,z", [("19", 19), ("18 ", 18), ("19S", 19), ("19 H", 19), ("huso 18", 18), ("19.0", 19), (19.0, 19), ("Zona 19J", 19)])
def test_zona(texto, z):
    assert parse_zona(texto) == z


@pytest.mark.parametrize("texto", ["", "abc", "19X", "19N", "61", "0", "18,5"])
def test_zona_invalida(texto):
    with pytest.raises((ErrorEntrada, ErrorRango)):
        parse_zona(texto)


# --------------------------------------------------------------------------- ángulos
@pytest.mark.parametrize(
    "texto,valor,eje,forma",
    [
        ("-33.4489", -33.4489, None, "decimal"),
        ("33.4489", -33.4489, None, "decimal"),  # positivo = S/O (opción por defecto)
        ("33,4489", -33.4489, None, "decimal"),
        ("33,4489 S", -33.4489, "lat", "decimal"),
        ("S 33.4489", -33.4489, "lat", "decimal"),
        ("33.4489S", -33.4489, "lat", "decimal"),
        ("−33,4489", -33.4489, None, "decimal"),
        ("+33.4489", 33.4489, None, "decimal"),
        ("33.4489 N", 33.4489, "lat", "decimal"),
        ("70.6693 O", -70.6693, "lon", "decimal"),
        ("70.6693 W", -70.6693, "lon", "decimal"),
        ("70.6693 E", 70.6693, "lon", "decimal"),
        ("33°26'56.04\"S", LAT, "lat", "gms"),
        ("33° 26' 56.04\" S", LAT, "lat", "gms"),
        ("33º26'56,04''S", LAT, "lat", "gms"),
        ("33°26′56.04″ S", LAT, "lat", "gms"),
        ("33°26’56.04” S", LAT, "lat", "gms"),
        ("S 33 26 56,04", LAT, "lat", "gms"),
        ("33 26 56.04", LAT, None, "gms"),
        ("-33 26 56.04", LAT, None, "gms"),
        ("33d26m56.04s", LAT, None, "gms"),
        ("33d 26m 56.04s S", LAT, "lat", "gms"),
        ("33D26M56.04S", LAT, None, "gms"),
        ("33 26 56.04 S", LAT, "lat", "gms"),
        ("33°26'S", -(33 + 26 / 60), "lat", "gm"),
        ("33 26.934 S", -(33 + 26.934 / 60), "lat", "gm"),
        ("33°", -33.0, None, "decimal"),
        ("70°39'0\"O", -(70 + 39 / 60), "lon", "gms"),
        (" 18°  28'  28,8680\"", -(18 + 28 / 60 + 28.868 / 3600), None, "gms"),  # salida del .exe
        (" 70°  18'  ,3791\"", -(70 + 18 / 60 + 0.3791 / 3600), None, "gms"),  # segundos < 1 sin cero
        ("33° 27' 59,9999\" S", -(33 + 27 / 60 + 59.9999 / 3600), "lat", "gms"),
    ],
)
def test_angulos(texto, valor, eje, forma):
    a = parse_angulo(texto)
    assert a.valor == pytest.approx(valor, abs=1e-12)
    assert a.eje == eje and a.forma == forma


def test_positivos_como_norte_si_la_opcion_esta_apagada():
    assert parse_angulo("33.45", positivos_sur_oeste=False).valor == 33.45
    assert parse_angulo("33.45 S", positivos_sur_oeste=False).valor == -33.45
    assert parse_angulo("-33.45", positivos_sur_oeste=False).valor == -33.45


@pytest.mark.parametrize(
    "texto,error",
    [
        ("", ErrorEntrada),
        ("abc", ErrorEntrada),
        ("33,5° 10'", ErrorEntrada),  # grados con decimales + minutos: error explícito
        ("33.5 0 0", ErrorEntrada),
        ("33 27.5 12", ErrorEntrada),  # minutos con decimales + segundos
        ("33 60 0", ErrorRango),
        ("33 27 60", ErrorRango),
        ("33°60'", ErrorRango),
        ("-33 N", ErrorEntrada),  # signo y letra se contradicen
        ("+33 S", ErrorEntrada),
        ("33 S N", ErrorEntrada),
        ("33 27 12 10", ErrorEntrada),
        ("27'12\"", ErrorEntrada),  # faltan grados
        ("33°12\"", ErrorEntrada),  # faltan minutos
        ("181", ErrorRango),
        ("33 - 27", ErrorEntrada),
        ("33;27", ErrorEntrada),
        ("x70,5;", ErrorEntrada),
        ("33.27.12", ErrorEntrada),
    ],
)
def test_angulos_invalidos(texto, error):
    with pytest.raises(error):
        parse_angulo(texto)


def test_eje_incorrecto():
    with pytest.raises(ErrorEntrada):
        parse_angulo("70.5 O", eje="lat")
    with pytest.raises(ErrorRango):
        parse_angulo("95", eje="lat")


# --------------------------------------------------------------------------- campos GMS
def test_gms_campos():
    assert parse_gms_campos("33", "26", "56,04", "S", "lat") == pytest.approx(LAT, abs=1e-12)
    assert parse_gms_campos("33", "", "", "S", "lat") == -33.0
    assert parse_gms_campos("70", "39", "0", "O", "lon") == -(70 + 39 / 60)
    assert parse_gms_campos("70", "39", "0", "E", "lon") == 70 + 39 / 60
    assert parse_gms_campos("33", "27", "59.9999", "S", "lat") < 0


@pytest.mark.parametrize(
    "g,m,s,h,eje,error",
    [
        ("33,5", "0", "0", "S", "lat", ErrorEntrada),  # .exe truncaba a 33°: ahora error
        ("33.5", "0", "0", "S", "lat", ErrorEntrada),
        ("33", "27,5", "0", "S", "lat", ErrorEntrada),
        ("33", "60", "0", "S", "lat", ErrorRango),
        ("33", "27", "60", "S", "lat", ErrorRango),
        ("", "27", "0", "S", "lat", ErrorEntrada),
        ("abc", "27", "0", "S", "lat", ErrorEntrada),
        ("-33", "27", "0", "N", "lat", ErrorEntrada),
        ("91", "0", "0", "S", "lat", ErrorRango),
        ("33", "27", "0", "", "lat", ErrorEntrada),
        ("33", "27", "0", "O", "lat", ErrorEntrada),
    ],
)
def test_gms_campos_invalidos(g, m, s, h, eje, error):
    with pytest.raises(error):
        parse_gms_campos(g, m, s, h, eje)


# --------------------------------------------------------------------------- filas
@pytest.mark.parametrize(
    "c1,c2,z,tipo,a,b,inv",
    [
        ("-33.4489", "-70.6693", "", "geo", -33.4489, -70.6693, False),
        ("-70.6693", "-33.4489", "", "geo", -33.4489, -70.6693, True),  # orden lon/lat
        ("33,4489", "70,6693", "", "geo", -33.4489, -70.6693, False),
        ("70,6693", "33,4489", "", "geo", -33.4489, -70.6693, True),
        ("33°26'56.04\"S", "70°40'9.48\"O", "", "geo", LAT, -(70 + 40 / 60 + 9.48 / 3600), False),
        ("70°40'9.48\"W", "33°26'56.04\"S", "", "geo", LAT, -(70 + 40 / 60 + 9.48 / 3600), True),
        ("70.6693 O", "33.4489", "", "geo", -33.4489, -70.6693, True),
        ("6.318.026,543", "346.642,695", "19", "utm", 6318026.543, 346642.695, False),
        ("6.318.026,543.", "346.642,695.", "19", "utm", 6318026.543, 346642.695, False),
        ("346.642", "6.318.026", "19", "utm", 6318026.0, 346642.0, True),  # orden Este/Norte
        ("6318026.543", "346642.695", "18S", "utm", 6318026.543, 346642.695, False),
        ("6318026", "346,642", "19", "utm", 6318026.0, 346642.0, False),
    ],
)
def test_interpretar_fila(c1, c2, z, tipo, a, b, inv):
    f = interpretar_fila(c1, c2, z, cambio_datum=True)
    assert f.tipo == tipo and f.orden_invertido == inv
    assert f.a == pytest.approx(a, abs=1e-9) and f.b == pytest.approx(b, abs=1e-9)
    assert bool(f.nota) == inv


@pytest.mark.parametrize(
    "c1,c2,z,cambio,error",
    [
        ("", "", "", True, ErrorEntrada),
        ("-33.4", "", "", True, ErrorEntrada),
        ("6318026", "346642", "", True, ErrorEntrada),  # falta el huso
        ("-60", "-70", "", False, ErrorAmbiguo),  # sin cambio de datum ambos órdenes sirven
        ("33 S", "34 S", "", True, ErrorEntrada),  # dos latitudes
        ("33°S", "6318026", "19", True, ErrorEntrada),  # mezcla
        ("123", "456", "19", True, ErrorRango),  # ni geo ni UTM
        ("abc", "70", "", True, ErrorEntrada),
        ("33 60 0", "70", "", True, ErrorRango),
    ],
)
def test_interpretar_fila_errores(c1, c2, z, cambio, error):
    with pytest.raises(error):
        interpretar_fila(c1, c2, z, cambio_datum=cambio)


def test_fila_fuera_de_rango_mantiene_orden():
    """Si ningún orden calza, se respeta el orden dado (el núcleo dará el motivo exacto)."""
    f = interpretar_fila("-10", "-72", "", cambio_datum=True)
    assert (f.a, f.b, f.orden_invertido) == (-10, -72, False)


# --------------------------------------------------------------------------- pegado
@pytest.mark.parametrize(
    "linea,campos",
    [
        ("-33.4489\t-70.6693", ["-33.4489", "-70.6693"]),
        ("6.318.026,543\t346.642,695\t19\r\n", ["6.318.026,543", "346.642,695", "19"]),
        ("-33,4489;-70,6693", ["-33,4489", "-70,6693"]),
        ("-33.4489 -70.6693", ["-33.4489", "-70.6693"]),
        ("-33.4489, -70.6693", ["-33.4489", "-70.6693"]),
        ("6318026.543 346642.695 19", ["6318026.543", "346642.695", "19"]),
        ("33 26 56.04 S 70 40 9.48 O", ["33 26 56.04 S", "70 40 9.48 O"]),
        ("S 33 26 56.04 O 70 40 9.48", ["S 33 26 56.04", "O 70 40 9.48"]),
        ("33 26 56.04 70 40 9.48", ["33 26 56.04", "70 40 9.48"]),
        ("33 26.934 70 40.158", ["33 26.934", "70 40.158"]),
        ("PSAD56 -33.4489 -70.6693", ["PSAD56", "-33.4489", "-70.6693"]),
        ("SAD69 33 26 56 S 70 40 9 W", ["SAD69", "33 26 56 S", "70 40 9 W"]),
        ("33°26'56.04\"S 70°40'9.48\"W", ["33°26'56.04\"S", "70°40'9.48\"W"]),
        ("a\t\tb", ["a", "", "b"]),
    ],
)
def test_dividir_linea(linea, campos):
    assert dividir_linea(linea) == campos
