"""Validación independiente con PROJ (pyproj). pyproj se usa SOLO en las pruebas."""
import random

import pytest
from pyproj import CRS, Transformer

from apoyo import dif_m, proj_utm
from coordenadas.core.constantes import DATUMS, GRS67, INTERNACIONAL_1924, WGS84, Metodo
from coordenadas.core.conversion import convertir_geo
from coordenadas.core.geodesia import geo_a_xyz, xyz_a_geo
from coordenadas.core.utm import geo_a_utm, meridiano_central, utm_a_geo

ELIPSOIDES = [WGS84, INTERNACIONAL_1924, GRS67]
ZONAS = [12, 17, 18, 19, 20]


@pytest.mark.parametrize("ell", ELIPSOIDES, ids=lambda e: e.nombre)
@pytest.mark.parametrize("zona", ZONAS)
def test_geo_utm_contra_proj(ell, zona):
    t = proj_utm(ell, zona)
    rnd = random.Random(zona * 1000 + int(ell.a))
    for _ in range(1500):
        lat = -rnd.uniform(0.5, 79.5)
        lon = meridiano_central(zona) + rnd.uniform(-6.0, 6.0)
        n, e = geo_a_utm(lat, lon, zona, ell)
        pe, pn = t.transform(lon, lat)
        assert abs(n - pn) <= 0.002 and abs(e - pe) <= 0.002
        # inversa contra PROJ
        la2, lo2 = utm_a_geo(pn, pe, zona, ell)
        plo, pla = t.transform(pe, pn, direction="INVERSE")
        dn, de = dif_m(pla, plo, la2, lo2)
        assert abs(dn) <= 0.002 and abs(de) <= 0.002


@pytest.mark.parametrize("ell", ELIPSOIDES, ids=lambda e: e.nombre)
def test_ida_y_vuelta_utm(ell):
    rnd = random.Random(int(ell.b))
    for _ in range(3000):
        zona = rnd.choice(ZONAS)
        lat = -rnd.uniform(0.5, 79.5)
        lon = meridiano_central(zona) + rnd.uniform(-6.0, 6.0)
        n, e = geo_a_utm(lat, lon, zona, ell)
        la2, lo2 = utm_a_geo(n, e, zona, ell)
        dn, de = dif_m(lat, lon, la2, lo2)
        assert abs(dn) <= 0.001 and abs(de) <= 0.001
        n3, e3 = geo_a_utm(la2, lo2, zona, ell)
        assert abs(n3 - n) <= 0.001 and abs(e3 - e) <= 0.001


@pytest.mark.parametrize("ell", ELIPSOIDES, ids=lambda e: e.nombre)
def test_xyz_contra_proj(ell):
    geo = CRS.from_proj4(f"+proj=longlat +a={ell.a} +b={ell.b} +no_defs")
    cart = CRS.from_proj4(f"+proj=geocent +a={ell.a} +b={ell.b} +units=m +no_defs")
    t = Transformer.from_crs(geo, cart, always_xy=True)
    rnd = random.Random(3)
    for _ in range(2000):
        lat, lon, h = -rnd.uniform(0, 89.9), -rnd.uniform(0, 180), rnd.uniform(-500, 9000)
        x, y, z = geo_a_xyz(lat, lon, h, ell)
        px, py, pz = t.transform(lon, lat, h)
        assert max(abs(x - px), abs(y - py), abs(z - pz)) <= 0.001
        la2, lo2, h2 = xyz_a_geo(px, py, pz, ell)
        plo, pla, ph = t.transform(px, py, pz, direction="INVERSE")
        dn, de = dif_m(pla, plo, la2, lo2)
        assert abs(dn) <= 0.0001 and abs(de) <= 0.0001 and abs(h2 - ph) <= 0.0001


def _proj_datum(clave, deltas_a_sirgas):
    e = DATUMS[clave].elipsoide
    dx, dy, dz = deltas_a_sirgas
    return CRS.from_proj4(f"+proj=longlat +a={e.a} +b={e.b} +towgs84={dx},{dy},{dz},0,0,0,0 +no_defs")


@pytest.mark.parametrize("metodo", list(Metodo))
@pytest.mark.parametrize("local", ["PSAD56", "SAD69"])
def test_cambio_de_datum_contra_proj_helmert(metodo, local):
    """La traslación de 3 parámetros (h = 0) comparada con PROJ +towgs84, franja por franja,
    en los dos sentidos, y la cadena completa hasta UTM."""
    from coordenadas.core.constantes import FRANJAS

    rnd = random.Random(5)
    sirgas = _proj_datum("SIRGAS", (0, 0, 0))
    for f in FRANJAS[metodo][local]:
        local_crs = _proj_datum(local, (-f.dx, -f.dy, -f.dz))
        ida = Transformer.from_crs(sirgas, local_crs, always_xy=True)
        vuelta = Transformer.from_crs(local_crs, sirgas, always_xy=True)
        for _ in range(150):
            s = rnd.uniform(f.inferior + 0.01, f.superior - 0.01)
            w = rnd.uniform(66.1, 76.9)
            for di, do, t in (("SIRGAS", local, ida), (local, "SIRGAS", vuelta)):
                r = convertir_geo(-s, -w, di, do, metodo)
                plo, pla = t.transform(-w, -s)
                dn, de = dif_m(pla, plo, r.lat, r.lon, do)
                assert abs(dn) <= 0.001 and abs(de) <= 0.001
                pe, pn = proj_utm(DATUMS[do].elipsoide, r.zona).transform(plo, pla)
                assert abs(r.norte - pn) <= 0.002 and abs(r.este - pe) <= 0.002
