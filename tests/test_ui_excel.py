"""Pestaña 3 (solo UTM) de punta a punta: abrir, asignar columnas, procesar en un hilo y resumen."""
import time

import openpyxl

from coordenadas.core.conversion import convertir_utm


def _esperar(app, tab, limite=60):
    t0 = time.time()
    while tab.hilo is not None and (tab.hilo.is_alive() or str(tab.b_convertir.cget("state")) == "disabled"):
        app.raiz.update()
        time.sleep(0.02)
        assert time.time() - t0 < limite


def _xlsx(ruta, datum_fila3="SAD69"):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Datos"
    ws.append(["Punto", "Datum", "Norte", "Este", "Huso"])
    ws.append(["A", "PSAD56", 6297980, 346826, 19])
    ws.append(["B", datum_fila3, "6.297.606,833", "346.642,695", "19"])
    ws.append(["C", "SIRGAS", "x", 1, 19])
    wb.save(ruta)


def test_pestana_excel_completa(app, tmp_path):
    p = tmp_path / "datos.xlsx"
    _xlsx(p)
    t = app.tabs[2]
    assert t.abrir(str(p))
    assert t.v_hoja.get() == "Datos" and t.v_destino.get().endswith("datos_convertido.xlsx")
    assert len(t.vista.get_children()) == 3
    assert t.v_col["norte"].get().startswith("C") and t.v_col["este"].get().startswith("D")
    assert t.v_col["zona"].get().startswith("E") and t.v_col_datum.get().startswith("B")
    t.v_datum_modo.set("columna")
    assert t.iniciar(confirmar=False)
    _esperar(app, t)
    r = t.ultimo_resumen
    assert (r.ok, r.error) == (2, 1)
    ws = openpyxl.load_workbook(tmp_path / "datos_convertido.xlsx")["Datos"]
    assert [ws.cell(1, c).value for c in range(6, 10)] == ["Norte WGS84", "Este WGS84", "Huso", "Estado"]
    esperado = convertir_utm(6297980, 346826, 19, "PSAD56", "SIRGAS")
    assert ws["F2"].value == round(esperado.norte) and ws["G2"].value == round(esperado.este) and ws["H2"].value == 19
    assert ws["I2"].value == "OK" and ws["I3"].value == "OK" and ws["I4"].value != "OK"
    assert "Filas OK: 2" in t.l_msg.cget("text")


def test_pestana_excel_datum_con_anios_y_huso_fijo(app, tmp_path):
    """1956 y 1969 valen como PSAD56 y SAD69 en la columna de datum; el huso puede ser un valor fijo."""
    p = tmp_path / "anios.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "D"
    ws.append(["Norte", "Este", "Datum"])
    ws.append([6318400, 337470, "1956"])
    ws.append([6318400, 337470, "PSAD56"])
    ws.append([6318400, 337470, ""])  # sin datum: error
    ws.append([6318400, 337470, 1956])  # celda numérica (así llegan los años desde Excel o un .xls)
    ws.append([6318400, 337470, 1956.0])
    ws.append([6318400, 337470, "WGS 1984"])
    wb.save(p)
    t = app.tabs[2]
    assert t.abrir(str(p))
    t.v_datum_modo.set("columna")
    t.v_zona_modo.set("fijo")
    t.v_zona_fija.set("19")
    assert t.iniciar(confirmar=False)
    _esperar(app, t)
    assert (t.ultimo_resumen.ok, t.ultimo_resumen.error) == (5, 1)
    out = openpyxl.load_workbook(tmp_path / "anios_convertido.xlsx")["D"]
    assert out["D2"].value == out["D3"].value == out["D5"].value == out["D6"].value == 6318027
    assert out["D7"].value == 6318400  # WGS 1984 -> mismo datum que la salida
    assert out["G4"].value == "Datum de entrada: celda vacía."


def test_pestana_excel_solo_utm_y_defaults(app, tmp_path):
    t = app.tabs[2]
    assert t.v_datum_in.get() == "PSAD56" and t.panel.v_datum.get() == "WGS84 / SIRGAS"
    assert t.panel.selector is None and t.panel.formato == "utm"  # sin selector de formato de salida
    assert not hasattr(t, "sel_formato") and not hasattr(t, "v_fmt")
    cfg = None
    p = tmp_path / "d.xlsx"
    _xlsx(p)
    t.abrir(str(p))
    cfg = t.config_proceso()
    assert cfg.formato == "utm" and cfg.formato_salida == "utm" and cfg.datum_fijo == "PSAD56"
    assert set(cfg.columnas) == {"norte", "este", "zona"}


def test_pestana_excel_no_ofrece_el_datum_de_entrada_como_salida(app):
    from coordenadas.ui.comun import CLAVE_POR_ETIQUETA

    t = app.tabs[2]
    claves = lambda: [CLAVE_POR_ETIQUETA[v] for v in t.panel.cb_datum.cget("values")]  # noqa: E731
    assert claves() == ["SIRGAS", "SAD69"]  # entrada fija PSAD56
    t.v_datum_in.set("WGS84 / SIRGAS")  # igual a la salida actual: la salida se mueve
    assert t.panel.v_datum.get() == "PSAD56" and claves() == ["PSAD56", "SAD69"]
    assert app.estado.mensaje == "Datum de salida cambiado a PSAD56"
    t.v_datum_modo.set("columna")  # con datum por columna no se excluye nada
    assert claves() == ["SIRGAS", "PSAD56", "SAD69"]


def test_pestana_excel_errores_de_configuracion(app, tmp_path):
    p = tmp_path / "d.xlsx"
    _xlsx(p)
    t = app.tabs[2]
    t.abrir(str(p))
    t.v_col["norte"].set("—")
    assert not t.iniciar(confirmar=False)  # Norte sin asignar
    assert "Asigne la columna de «Norte»" in t.l_msg.cget("text")
    t.abrir(str(p))
    t.v_destino.set(str(p))
    assert not t.iniciar(confirmar=False)
    assert "original" in t.l_msg.cget("text")
    assert not t.abrir(str(tmp_path / "no_existe.xlsx"))
