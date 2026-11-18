"""Bordes del núcleo: husos, zona forzada, rangos, valores inválidos y composición de datums."""
import math
import random

import pytest

from apoyo import dif_m, proj_utm
from coordenadas.core.constantes import DATUMS, Metodo
from coordenadas.core.conversion import convertir_geo, convertir_utm
from coordenadas.core.errores import ErrorEntrada, ErrorRango, ErrorSinParametros
from coordenadas.core.transformacion import transformar
from coordenadas.core.utm import zona_estandar

T, R = Metodo.TABLA_IGM, Metodo.REPLICA_EXE


# --------------------------------------------------------------------------- husos
@pytest.mark.parametrize(
    "lon,zona",
    [(-72.0, 19), (-71.9999999, 19), (-72.0000001, 18), (-66.0, 20), (-65.9999, 20), (-66.0001, 19),
     (-78.0, 18), (-78.0001, 17), (-109.35, 12), (-105.4, 13), (-80.0, 17)],
)
def test_zona_estandar(lon, zona):
    assert zona_estandar(lon) == zona


def test_huso_de_salida_con_longitud_transformada():
    # SIRGAS 72°00′00.36″ O está en el huso 18, pero en PSAD56 queda al este de 72° -> huso 19 (oráculo E17).
    r = convertir_geo(-38.1234, -72.0001, "SIRGAS", "PSAD56", T)
    assert zona_estandar(-72.0001) == 18 and r.lon > -72.0 and r.zona == 19
    # Sentido contrario: PSAD56 al este de 72° que en SIRGAS queda al oeste -> huso 18.
    r = convertir_geo(-38.1234, -71.9990, "PSAD56", "SIRGAS", T)
    assert r.lon < -72.0 and r.zona == 18


# --------------------------------------------------------------------------- zona forzada
@pytest.mark.parametrize("zona", [18, 19])
@pytest.mark.parametrize("lon", [-66.5, -68.0, -69.0, -70.67, -71.5, -72.0, -73.5, -75.0, -76.9])
def test_zona_forzada_sin_espejado(zona, lon):
    """Con huso forzado el Este se calcula con la proyección real (sin espejado)."""
    r = convertir_geo(-33.4489, lon, "SIRGAS", "PSAD56", T, zona_salida=zona)
    e, n = proj_utm(DATUMS["PSAD56"].elipsoide, zona).transform(r.lon, r.lat)
    assert abs(r.este - e) <= 0.002 and abs(r.norte - n) <= 0.002
    assert (r.este > 500000) == (r.lon > zona * 6 - 183)
    assert r.zona == zona and r.zona_forzada


def test_zona_forzada_igual_a_automatica_cuando_coinciden():
    a = convertir_geo(-33.4489, -70.6693, "SIRGAS", "SAD69", T)
    f = convertir_geo(-33.4489, -70.6693, "SIRGAS", "SAD69", T, zona_salida=a.zona)
    assert (a.norte, a.este, a.zona) == (f.norte, f.este, f.zona)
    assert not a.zona_forzada and f.zona_forzada


def test_zona_forzada_demasiado_lejos():
    with pytest.raises(ErrorRango):
        convertir_geo(-27.12, -109.35, "SIRGAS", "SIRGAS", T, zona_salida=19)


# --------------------------------------------------------------------------- rangos
@pytest.mark.parametrize("lon", [-66.0, -77.0000001, -65.0, -80.0])
def test_longitud_fuera_de_chile_continental(lon):
    with pytest.raises(ErrorRango):
        convertir_geo(-33.0, lon, "SIRGAS", "PSAD56", T)


@pytest.mark.parametrize("lon", [-66.0000001, -77.0])
def test_longitud_limite_aceptada(lon):
    convertir_geo(-33.0, lon, "SIRGAS", "PSAD56", T)


@pytest.mark.parametrize("lat,lon", [(33.0, -70.0), (-33.0, 70.0)])
def test_hemisferio_norte_o_este(lat, lon):
    with pytest.raises(ErrorRango):
        convertir_geo(lat, lon, "SIRGAS", "SIRGAS", T)


def test_sin_cambio_de_datum_rango_ampliado():
    # Isla de Pascua (huso 12), Juan Fernández (17), Salas y Gómez (13), Antártica (huso 19/21)
    for lat, lon, z in [(-27.1127, -109.3497, 12), (-33.6375, -78.8497, 17), (-26.4667, -105.3667, 13),
                        (-62.2, -58.9, 21), (-79.9, -60.0, 21)]:
        r = convertir_geo(lat, lon, "SIRGAS", "SIRGAS", T)
        assert r.zona == z and r.pasos == ()
        assert r.lat == lat and r.lon == lon
        for d in ("PSAD56", "SAD69"):
            with pytest.raises(ErrorRango):
                convertir_geo(lat, lon, "SIRGAS", d, T)
    for lat, lon in [(-80.0001, -70.0), (-33.0, -120.0001), (-33.0, -49.9999)]:
        with pytest.raises(ErrorRango):
            convertir_geo(lat, lon, "SIRGAS", "SIRGAS", T)


def test_mismo_datum_psad56_usa_su_elipsoide():
    r = convertir_geo(-33.45, -70.65, "PSAD56", "PSAD56", T)
    e, n = proj_utm(DATUMS["PSAD56"].elipsoide, 19).transform(-70.65, -33.45)
    assert abs(r.norte - n) < 1e-6 and abs(r.este - e) < 1e-6


# --------------------------------------------------------------------------- valores inválidos
@pytest.mark.parametrize("lat,lon", [(math.nan, -70.0), (-33.0, math.inf), (None, -70.0)])
def test_valores_no_finitos(lat, lon):
    with pytest.raises(ErrorEntrada):
        convertir_geo(lat, lon, "SIRGAS", "PSAD56", T)


@pytest.mark.parametrize(
    "n,e,z,cambio",
    [
        (6297606.833, 346642.695, 17, True),  # huso fuera de Chile continental
        (6297606.833, 346642.695, 20, True),
        (6297606.833, 346642.695, 23, False),  # fuera del rango ampliado
        (6297606.833, 99999.0, 19, True),
        (6297606.833, 900001.0, 19, True),
        (12000000.0, 346642.695, 19, True),
        (0.0, 346642.695, 19, False),
        (-5.0, 346642.695, 19, False),
        (6297606.833, 846642.695, 19, True),  # λ = 65.27° O: fuera de Chile continental
    ],
)
def test_utm_invalido(n, e, z, cambio):
    with pytest.raises(ErrorRango):
        convertir_utm(n, e, z, "SIRGAS", "PSAD56" if cambio else "SIRGAS", T)


def test_utm_huso_no_entero():
    with pytest.raises(ErrorEntrada):
        convertir_utm(6297606.833, 346642.695, 19.0, "SIRGAS", "PSAD56", T)


def test_datum_desconocido():
    with pytest.raises(ErrorEntrada):
        convertir_geo(-33.0, -70.0, "WGS72", "PSAD56", T)


# --------------------------------------------------------------------------- composición
def _interior(rnd):
    while True:
        s = rnd.uniform(17.6, 43.9)
        if min(abs(s - f) for f in (26.0, 32.0, 36.0)) > 0.02:
            return -s, -rnd.uniform(66.1, 76.9)


@pytest.mark.parametrize("metodo", list(Metodo))
def test_psad56_sad69_pasa_por_sirgas(metodo):
    rnd = random.Random(21)
    for _ in range(300):
        lat, lon = _interior(rnd)
        for a, b in (("PSAD56", "SAD69"), ("SAD69", "PSAD56")):
            r = convertir_geo(lat, lon, a, b, metodo)
            l1, o1, p1 = transformar(lat, lon, a, "SIRGAS", metodo)
            l2, o2, p2 = transformar(l1, o1, "SIRGAS", b, metodo)
            assert (r.lat, r.lon) == (l2, o2)
            assert [p.destino for p in r.pasos] == ["SIRGAS", b]
            assert r.pasos[0].deltas == tuple(-v for v in p1[0].franja.deltas)
            assert r.pasos[1].deltas == p2[0].franja.deltas


@pytest.mark.parametrize("metodo", list(Metodo))
@pytest.mark.parametrize("a,b", [("PSAD56", "SAD69"), ("SAD69", "PSAD56"), ("SIRGAS", "PSAD56"), ("SIRGAS", "SAD69")])
def test_ida_y_vuelta_de_datum(metodo, a, b):
    """Cierre de ida y vuelta lejos de las fronteras de franja. No es cero por diseño: cada paso
    descarta la altura de salida (h = 0 en la entrada siguiente), igual que el .exe. Máximo
    observado ≈ 6 mm; se exige <= 1 cm."""
    rnd = random.Random(33)
    peor = 0.0
    for _ in range(500):
        lat, lon = _interior(rnd)
        r = convertir_geo(lat, lon, a, b, metodo)
        v = convertir_geo(r.lat, r.lon, b, a, metodo)
        dn, de = dif_m(lat, lon, v.lat, v.lon, a)
        peor = max(peor, abs(dn), abs(de))
    assert peor <= 0.010


def test_salto_de_franja_en_ida_y_vuelta_documentado():
    """La franja se elige con la latitud de entrada: un punto SIRGAS justo al sur de 32° usa la
    franja 32–36 de SAD69, pero su latitud SAD69 cae al norte de 32° y la vuelta usa la franja
    17°30′–32°: la ida y vuelta no cierra (≈ 10.6 m). Comportamiento inherente al método."""
    lat, lon = -32.00017589895052, -70.82741377813275
    r = convertir_geo(lat, lon, "SIRGAS", "SAD69", T)
    assert r.pasos[0].deltas == (64, 0, 32) and r.lat > -32.0
    v = convertir_geo(r.lat, r.lon, "SAD69", "SIRGAS", T)
    assert v.pasos[0].deltas == (-59, -11, -52)
    dn, de = dif_m(lat, lon, v.lat, v.lon)
    assert 10.0 < math.hypot(dn, de) < 11.0


def test_composicion_falla_en_paso_intermedio():
    # PSAD56 al sur de 44° (Tabla): sin parámetros en el primer paso.
    with pytest.raises(ErrorSinParametros):
        convertir_geo(-44.5, -72.0, "SAD69", "PSAD56", T)
    with pytest.raises(ErrorSinParametros):
        convertir_geo(-44.5, -72.0, "PSAD56", "SAD69", T)
