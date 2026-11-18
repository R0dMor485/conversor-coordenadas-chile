"""Pestaña 2 (conversión masiva) y lógica de pegado."""
import tkinter as tk

import pytest

from coordenadas.core.constantes import Metodo
from coordenadas.core.servicio import convertir_fila, interpretar_pegado, textos_fila

T = Metodo.TABLA_IGM


def test_interpretar_pegado():
    texto = (
        "Lat\tLon\r\n"  # encabezado: se omite
        "-33.4489\t-70.6693\r\n"
        "\r\n"
        "PSAD56;6.297.980;346.826;19\n"
        "SAD69 33 26 56 S 70 40 9 W\n"
        "-70,6693, -33,4489\n"  # no aplica ", " (no hay espacio tras la primera coma decimal)
        "6297606 346642 19\n"
    )
    f = interpretar_pegado(texto)
    assert [(x.datum, x.c1, x.c2, x.zona) for x in f] == [
        (None, "-33.4489", "-70.6693", ""),
        ("PSAD56", "6.297.980", "346.826", "19"),
        ("SAD69", "33 26 56 S", "70 40 9 W", ""),
        (None, "-70,6693", "-33,4489", ""),
        (None, "6297606", "346642", "19"),
    ]


def test_convertir_fila_niveles():
    ok = convertir_fila("-33.4489", "-70.6693", "", "SIRGAS", "PSAD56", T)
    assert ok.nivel == "ok" and ok.estado == "OK"
    inv = convertir_fila("-70.6693", "-33.4489", "", "SIRGAS", "PSAD56", T)
    assert inv.nivel == "aviso" and "invirtió" in inv.estado
    assert (inv.resultado.norte, inv.resultado.este) == (ok.resultado.norte, ok.resultado.este)
    err = convertir_fila("-50", "-72", "", "SIRGAS", "PSAD56", T)
    assert err.nivel == "error" and err.resultado is None and "parámetros" in err.estado
    assert textos_fila(err, "utm") == ["", "", ""]
    amb = convertir_fila("-60", "-70", "", "SIRGAS", "SIRGAS", T)
    assert amb.nivel == "error" and "ambiguo" in amb.estado.lower()




def test_cuadricula_inicial_y_agregar(app):
    t = app.tabs[1]
    assert len(t.filas) == 30 and len(t.tree.get_children()) == 30
    t.agregar_fila()
    assert len(t.filas) == 31


def test_pegar_colorear_y_copiar(app):
    t = app.tabs[1]
    texto = ("6318400\t337470\t19\tPSAD56\n"            # 0 OK
             "337470\t6318400\t19\tPSAD56\n"            # 1 aviso: Este/Norte invertidos
             "6318400\t337470\t19\t\n"                  # 2 error: falta el datum
             "abc\t337470\t19\tPSAD56\n"                # 3 error: texto no válido
             "6.297.606,833\t346.642,695\t19\tWGS84\n"  # 4 OK: mismo datum que la salida
             )
    t.tree.focus("0")
    assert t.pegar(texto) == 5
    tags = [t.tree.item(str(i), "tags") for i in range(5)]
    assert tags[0] == "" and tags[1] == ("aviso",) and tags[2] == ("error",) and tags[3] == ("error",) and tags[4] == ""
    v0 = t.tree.item("0", "values")
    assert [str(x) for x in v0[5:8]] == ["6318027", "337287", "19"]  # PSAD56 -> WGS84 (salida por defecto)
    assert str(t.tree.item("2", "values")[8]) == "✕ Falta el datum."
    assert "OK" in t.l_resumen.cget("text") and "3 OK" not in t.l_resumen.cget("text")
    t.tree.selection_set("0")
    txt = t.texto_resultados(encabezados=True)
    lineas = txt.split("\r\n")
    assert lineas[0] == "Norte WGS84\tEste WGS84\tHuso\tEstado"
    assert len(lineas) == 6 and lineas[3].startswith("\t\t\t")  # fila con error: sin valores
    assert lineas[3].endswith("Falta el datum.")
    assert t.texto_resultados(encabezados=False).split("\r\n")[0] == "6318027\t337287\t19\tOK"
    t.copiar_resultados()
    assert app.raiz.clipboard_get().startswith("Norte WGS84\tEste WGS84")


def test_pegar_amplia_filas_y_datum_por_fila(app):
    t = app.tabs[1]
    t.tree.focus("28")
    t.pegar("6318400\t337470\t19\tPSAD56\n6318400\t337470\t19\tSAD69\n6318400\t337470\t19\t1956\n")
    assert len(t.filas) == 31
    assert [t.filas[i].datum for i in (28, 29, 30)] == ["PSAD56", "SAD69", "1956"]
    n = [t.filas[i].res.resultado.norte for i in (28, 29, 30)]
    assert round(n[0], 3) == round(n[2], 3) and round(n[0], 3) != round(n[1], 3)  # 1956 = PSAD56; SAD69 difiere


def test_datum_de_salida_y_ajustes_recalculan(app):
    t = app.tabs[1]
    t.pegar("6318400\t337470\t19\tPSAD56\n")
    assert t.tree.heading("r1", "text") == "Norte WGS84" and t.tree.heading("r3", "text") == "Huso"
    assert t.panel.selector is None and t.panel.formato == "utm"  # solo UTM: sin selector de formato
    assert str(t.tree.item("0", "values")[5]) == "6318027"
    t.panel.v_datum.set("SAD69")
    t.panel._cambio()
    assert t.tree.heading("r1", "text") == "Norte SAD69"
    assert str(t.tree.item("0", "values")[5]) != "6318027"
    assert t.texto_resultados(True).split("\r\n")[0] == "Norte SAD69\tEste SAD69\tHuso\tEstado"
    app.aplicar_ajustes(separador_decimal=",", decimales_utm=2)
    assert "," in str(t.tree.item("0", "values")[5])


def test_edicion_de_celda(app):
    t = app.tabs[1]
    t.editar(0, "norte", inicial="6318400")
    t._mover(0, 1)  # Tab: pasa a Este
    ed, var, i, col = t.editor
    assert (i, col) == (0, "este")
    var.set("337470")
    t._mover(0, 1)
    t.editor[1].set("19")
    t._mover(0, 1)  # Huso -> Datum
    assert t.editor[3] == "datum"
    t.editor[1].set("PSAD56")
    t._mover(1, 0)  # Enter: confirma y baja
    assert t.filas[0].res is not None and t.filas[0].res.nivel == "ok"
    assert str(t.tree.item("0", "values")[5]) == "6318027"
    t.tree.selection_set("0")
    t.borrar_seleccion()
    assert t.filas[0].res is None and t.filas[0].vacia()


# --------------------------------------------------------------------------- núcleo: filas UTM con datum propio
def test_pegado_utm_orden_norte_este_huso_datum():
    from coordenadas.core.servicio import interpretar_pegado_utm as ip

    f = ip("Norte\tEste\tHuso\tDatum\n6318400\t337470\t19\tPSAD56\n6.297.606,833;346.642,695;19;WGS 84\n"
           "337470 6318400 19 1956\n\n6318400\t337470\t19\n")
    assert [(x.norte, x.este, x.huso, x.datum) for x in f] == [
        ("6318400", "337470", "19", "PSAD56"), ("6.297.606,833", "346.642,695", "19", "WGS 84"),
        ("337470", "6318400", "19", "1956"), ("6318400", "337470", "19", "")]


def test_fila_utm_datum_leido_de_la_fila():
    from coordenadas.core.servicio import convertir_fila_utm as cf

    ok = cf("6318400", "337470", "19", "PSAD56", "SIRGAS", T)
    assert ok.nivel == "ok" and (round(ok.resultado.norte), round(ok.resultado.este), ok.resultado.zona) == (6318027, 337287, 19)
    for alias in ("1956", "psad-56", " PSAD56 "):
        assert round(cf("6318400", "337470", "19", alias, "SIRGAS", T).resultado.norte) == 6318027
    assert round(cf("6318400", "337470", "19", "1984", "SIRGAS", T).resultado.norte) == 6318400  # mismo datum
    assert round(cf("6318400", "337470", "19", "WGS 1984", "SIRGAS", T).resultado.norte) == 6318400
    assert round(cf("6318400", "337470", "19", "1969", "SIRGAS", T).resultado.norte) != 6318027
    assert cf("6318400", "337470", "19", "", "SIRGAS", T).estado == "Falta el datum."
    assert "desconocido" in cf("6318400", "337470", "19", "NAD27", "SIRGAS", T).estado
    assert "huso" in cf("6318400", "337470", "", "PSAD56", "SIRGAS", T).estado.lower()
    assert "UTM" in cf("-33.4489", "-70.6693", "19", "PSAD56", "SIRGAS", T).estado  # no se aceptan geográficas
    inv = cf("337470", "6318400", "19", "PSAD56", "SIRGAS", T)
    assert inv.nivel == "aviso" and round(inv.resultado.norte) == 6318027
