"""E/S de Excel y csv (archivos generados en las propias pruebas) y proceso por filas."""
import csv
import hashlib
import time

import openpyxl
import pytest
from openpyxl.styles import Font, PatternFill

from apoyo import ORACULO, leer_oraculo
from coordenadas.core.constantes import Metodo
from coordenadas.core.conversion import convertir_geo, convertir_utm
from coordenadas.io.csv_io import detectar_delimitador, leer_csv
from coordenadas.io.excel_io import letra_columna, listar_hojas, leer_filas, nombre_salida
from coordenadas.io.proceso import ConfigProceso, convertir_fila_archivo, procesar_archivo

T = Metodo.TABLA_IGM


def _sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _xlsx(ruta, filas, hoja="Puntos"):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = hoja
    for f in filas:
        ws.append(f)
    wb.create_sheet("Otra")["A1"] = "no tocar"
    wb.save(ruta)


# --------------------------------------------------------------------------- utilidades
def test_letras_y_nombre_salida(tmp_path):
    assert [letra_columna(i) for i in (0, 25, 26, 701, 702)] == ["A", "Z", "AA", "ZZ", "AAA"]
    assert nombre_salida(tmp_path / "datos.xlsx").name == "datos_convertido.xlsx"
    assert nombre_salida(tmp_path / "datos.xls").name == "datos_convertido.xlsx"
    assert nombre_salida(tmp_path / "datos.csv").name == "datos_convertido.csv"


@pytest.mark.parametrize("delim", [";", ",", "\t", "|"])
def test_delimitador(delim):
    txt = delim.join(["Nombre", "Lat", "Lon"]) + "\n" + delim.join(["P1", "-33.1", "-70.2"]) + "\n"
    assert detectar_delimitador(txt) == delim


@pytest.mark.parametrize("cod", ["utf-8-sig", "utf-8", "latin-1"])
def test_codificacion(tmp_path, cod):
    p = tmp_path / "a.csv"
    p.write_bytes("Nombre;Latitud\nÑuñoa;-33,45\n".encode(cod))
    fmt, filas = leer_csv(p)
    assert filas[1][0] == "Ñuñoa" and fmt.delimitador == ";"
    assert fmt.codificacion == ("latin-1" if cod == "latin-1" else "utf-8-sig")


# --------------------------------------------------------------------------- filas
def test_celdas_numericas_y_texto():
    cfg = ConfigProceso("utm", {"norte": 0, "este": 1, "zona": 2}, "PSAD56", metodo=T)
    a = convertir_fila_archivo([6297606.833, 346642.695, 19], cfg)
    b = convertir_fila_archivo(["6.297.606,833", "346.642,695", "19"], cfg)
    assert (a.norte, a.este) == (b.norte, b.este)
    # una celda NUMÉRICA 346.642 es 346.642 (no hay miles en un número): fuera de rango de Este
    with pytest.raises(Exception, match="Este"):
        convertir_fila_archivo([6297606.833, 346.642, 19], cfg)
    cfg_g = ConfigProceso("gms6", dict(lat_g=0, lat_m=1, lat_s=2, lon_g=3, lon_m=4, lon_s=5), "SIRGAS", metodo=T)
    r = convertir_fila_archivo([33, 27, 12.5, 70, 39, 0], cfg_g)
    assert r.lat == pytest.approx(-(33 + 27 / 60 + 12.5 / 3600))
    r2 = convertir_fila_archivo(["33 S", "27", "12,5", "-70", 39, None], cfg_g)
    assert (r2.lat, r2.lon) == (r.lat, r.lon)
    with pytest.raises(Exception, match="decimales"):
        convertir_fila_archivo([33.5, 0, 0, 70, 39, 0], cfg_g)


def test_datum_por_columna():
    cfg = ConfigProceso("dec", {"lat": 1, "lon": 2}, "SIRGAS", metodo=T, datum_fijo=None, col_datum=0)
    a = convertir_fila_archivo(["PSAD56", -33.45, -70.65], cfg)
    b = convertir_fila_archivo(["SAD69", -33.45, -70.65], cfg)
    assert a.datum_entrada == "PSAD56" and b.datum_entrada == "SAD69" and a.norte != b.norte
    with pytest.raises(Exception, match="desconocido"):
        convertir_fila_archivo(["WGS72", -33.45, -70.65], cfg)


# --------------------------------------------------------------------------- xlsx
def test_xlsx_copia_conserva_original_y_formato(tmp_path):
    p = tmp_path / "puntos.xlsx"
    _xlsx(p, [["Nombre", "Lat", "Lon", "Doble"], ["Santiago", -33.4489, -70.6693, None],
              ["Malo", "abc", -70.0, None], [None, None, None, None], ["Sur", 50, 72, None],
              ["Texto", "33°26'56.04\"S", "70°40'9.48\"O", None]])
    wb = openpyxl.load_workbook(p)
    ws = wb["Puntos"]
    ws["A1"].font = Font(bold=True)
    ws["A2"].fill = PatternFill("solid", fgColor="FFFF00")
    ws["D2"] = "=B2*2"
    wb.save(p)
    antes = _sha(p)
    cfg = ConfigProceso("dec", {"lat": 1, "lon": 2}, "PSAD56", metodo=T)
    destino = nombre_salida(p)
    res = procesar_archivo(p, "Puntos", destino, cfg)
    assert _sha(p) == antes  # el original no se toca
    assert (res.ok, res.error, res.vacias) == (2, 2, 1)
    wb2 = openpyxl.load_workbook(destino)
    ws2 = wb2["Puntos"]
    assert ws2["A1"].font.bold and ws2["A2"].fill.fgColor.rgb.endswith("FFFF00")
    assert ws2["D2"].value == "=B2*2"  # fórmula conservada
    assert wb2["Otra"]["A1"].value == "no tocar"
    assert [ws2.cell(1, c).value for c in range(5, 9)] == ["Norte PSAD56", "Este PSAD56", "Huso", "Estado"]
    r = convertir_geo(-33.4489, -70.6693, "SIRGAS", "PSAD56", T)
    assert ws2["E2"].value == round(r.norte) and isinstance(ws2["E2"].value, (int, float))  # numérico
    assert ws2["E2"].number_format == "0" and ws2["G2"].value == 19 and ws2["H2"].value == "OK"
    assert ws2["E3"].value is None and "abc" in ws2["H3"].value
    assert "parámetros" in ws2["H5"].value
    assert ws2["H6"].value == "OK" and abs(ws2["E6"].value - ws2["E2"].value) <= 1


def test_xlsx_formulas_se_leen_con_valor_calculado(tmp_path):
    """Un libro guardado por Excel trae el valor calculado de las fórmulas: se convierte ese valor."""
    p = tmp_path / "formulas.xlsx"
    _xlsx(p, [["Lat", "Lon"], [-33.4489, -70.6693]])
    # openpyxl no calcula fórmulas: simulamos un libro de Excel escribiendo el valor en caché a mano
    import zipfile

    with zipfile.ZipFile(p) as z:
        partes = {n: z.read(n) for n in z.namelist()}
    hoja = partes["xl/worksheets/sheet1.xml"].decode()
    hoja = hoja.replace('<c r="A2" t="n"><v>-33.4489</v></c>', '<c r="A2"><f>-33.4489*1</f><v>-33.4489</v></c>')
    assert "<f>" in hoja
    partes["xl/worksheets/sheet1.xml"] = hoja.encode()
    with zipfile.ZipFile(p, "w") as z:
        for n, d in partes.items():
            z.writestr(n, d)
    filas = list(leer_filas(p, "Puntos"))
    assert filas[1][0] == -33.4489
    res = procesar_archivo(p, "Puntos", tmp_path / "f_conv.xlsx", ConfigProceso("dec", {"lat": 0, "lon": 1}, "SAD69", metodo=T))
    assert res.ok == 1
    assert openpyxl.load_workbook(tmp_path / "f_conv.xlsx")["Puntos"]["A2"].value == "=-33.4489*1"


def test_xlsx_salida_decimal_y_gms(tmp_path):
    p = tmp_path / "u.xlsx"
    _xlsx(p, [["N", "E"], [6297606.833, 346642.695]])
    cfg = ConfigProceso("utm", {"norte": 0, "este": 1}, "SIRGAS", formato_salida="decimal", zona_fija=19,
                        datum_fijo="PSAD56", metodo=T, decimales_grados=6)
    procesar_archivo(p, "Puntos", tmp_path / "d.xlsx", cfg)
    ws = openpyxl.load_workbook(tmp_path / "d.xlsx")["Puntos"]
    r = convertir_utm(6297606.833, 346642.695, 19, "PSAD56", "SIRGAS", T)
    assert ws["C2"].value == round(r.lat, 6) and ws["C2"].number_format == "0.000000"
    cfg.formato_salida = "gms"
    cfg.separador_decimal = ","
    procesar_archivo(p, "Puntos", tmp_path / "g.xlsx", cfg)
    ws = openpyxl.load_workbook(tmp_path / "g.xlsx")["Puntos"]
    assert ws["C2"].value.endswith('" S') and "," in ws["C2"].value


def test_salida_no_puede_ser_el_original(tmp_path):
    p = tmp_path / "x.xlsx"
    _xlsx(p, [["Lat", "Lon"], [-33.0, -70.0]])
    with pytest.raises(ValueError):
        procesar_archivo(p, "Puntos", p, ConfigProceso("dec", {"lat": 0, "lon": 1}, "SAD69", metodo=T))


# --------------------------------------------------------------------------- csv
@pytest.mark.parametrize("cod,delim,sep", [("utf-8-sig", ";", ","), ("latin-1", ",", "."), ("utf-8-sig", ",", ","), ("utf-8-sig", "\t", ".")])
def test_csv(tmp_path, cod, delim, sep):
    p = tmp_path / "p.csv"
    filas = [["Punto", "Norte", "Este", "Huso"], ["Ñandú", "6.297.606,833", "346.642,695", "19"], ["Mal", "x", "1", "19"]]
    with open(p, "w", encoding=cod, newline="") as f:
        csv.writer(f, delimiter=delim).writerows(filas)
    antes = _sha(p)
    cfg = ConfigProceso("utm", {"norte": 1, "este": 2, "zona": 3}, "SAD69", metodo=T, decimales_utm=3, separador_decimal=sep)
    destino = nombre_salida(p)
    res = procesar_archivo(p, "p", destino, cfg)
    assert _sha(p) == antes and (res.ok, res.error) == (1, 1)
    with open(destino, encoding=cod, newline="") as f:
        out = list(csv.reader(f, delimiter=delim))
    assert out[0][-4:] == ["Norte SAD69", "Este SAD69", "Huso", "Estado"]
    assert out[1][0] == "Ñandú" and out[1][-1] == "OK"
    r = convertir_utm(6297606.833, 346642.695, 19, "SIRGAS", "SAD69", T)
    assert out[1][4] == f"{r.norte:.3f}".replace(".", sep)  # texto con el separador elegido, sin miles
    assert out[2][4] == "" and out[2][-1]


# --------------------------------------------------------------------------- .xls real (oráculo)
def test_xls_del_oraculo():
    """oraculo/excel_prueba/c1_decimal.xls fue creado con Excel para el modo masivo del .exe."""
    p = ORACULO / "excel_prueba" / "c1_decimal.xls"
    assert listar_hojas(p) == ["Puntos"]
    filas = list(leer_filas(p, "Puntos"))
    assert len(filas) == 37 and filas[0][0] == "Arica"
    esperado = {r["id"].split("-")[1]: r for r in leer_oraculo("c1_escritorio.csv") if r["opcion"] == "SIRGAS_SAD69"}
    cfg = ConfigProceso("dec", {"lat": 1, "lon": 2}, "SAD69", metodo=Metodo.REPLICA_EXE, fila_encabezado=None)
    for f in filas:
        r = convertir_fila_archivo(f, cfg)
        e = esperado[f[0]]
        assert abs(r.norte - float(e["out_norte"])) <= 0.002 and abs(r.este - float(e["out_este"])) <= 0.002


def test_xls_a_xlsx(tmp_path):
    import shutil

    p = tmp_path / "c1.xls"
    shutil.copy(ORACULO / "excel_prueba" / "c1_decimal.xls", p)
    cfg = ConfigProceso("dec", {"lat": 1, "lon": 2}, "PSAD56", metodo=T, fila_encabezado=None)
    res = procesar_archivo(p, "Puntos", nombre_salida(p), cfg)
    assert res.ok == 30 and res.error == 7  # PSAD56 sin parámetros al sur de 44°
    ws = openpyxl.load_workbook(nombre_salida(p))["Puntos"]
    assert ws["A1"].value == "Arica" and isinstance(ws["D1"].value, (int, float)) and ws["G1"].value == "OK"


# --------------------------------------------------------------------------- volumen
def test_csv_100_mil_filas(tmp_path):
    p = tmp_path / "grande.csv"
    with open(p, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["id", "lat", "lon"])
        for i in range(100_000):
            w.writerow([i, f"{-18 - (i % 2500) * 0.01:.4f}".replace(".", ","), f"{-68 - (i % 700) * 0.01:.4f}".replace(".", ",")])
    t = time.time()
    res = procesar_archivo(p, "grande", tmp_path / "grande_convertido.csv", ConfigProceso("dec", {"lat": 1, "lon": 2}, "PSAD56", metodo=T))
    dt = time.time() - t
    assert res.ok + res.error == 100_000 and res.ok > 99_000
    assert dt < 120


@pytest.mark.lento
def test_xlsx_100_mil_filas(tmp_path):
    p = tmp_path / "grande.xlsx"
    wb = openpyxl.Workbook(write_only=True)
    ws = wb.create_sheet("Puntos")
    ws.append(["id", "lat", "lon"])
    for i in range(100_000):
        ws.append([i, -18 - (i % 2500) * 0.01, -68 - (i % 700) * 0.01])
    wb.save(p)
    avances = []
    t = time.time()
    res = procesar_archivo(p, "Puntos", tmp_path / "g.xlsx", ConfigProceso("dec", {"lat": 1, "lon": 2}, "SAD69", metodo=T),
                           avance=lambda fr, txt: avances.append(fr))
    dt = time.time() - t
    print(f"\n100 000 filas xlsx: {dt:.1f} s")
    assert res.ok == 100_000 and avances[-1] == 1.0
    assert dt < 300
