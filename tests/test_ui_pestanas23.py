"""Estilo y estructura de las pestañas "Conversión masiva" y "Archivo Excel" (ambas solo UTM)."""
import time
import tkinter as tk
from tkinter import ttk

import openpyxl
import pytest

from coordenadas.ui import tema
from coordenadas.ui.tema import C


def _esperar(app, tab, limite=60):
    t0 = time.time()
    while tab.hilo is not None and (tab.hilo.is_alive() or str(tab.b_convertir.cget("state")) == "disabled"):
        app.raiz.update()
        time.sleep(0.02)
        assert time.time() - t0 < limite


def _xlsx(ruta):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Puntos"
    ws.append(["Punto", "Datum", "Norte", "Este", "Huso"])
    ws.append(["P1", "PSAD56", 6318400, 337470, 19])
    ws.append(["P2", "SIRGAS", "x", 1, 19])
    wb.save(ruta)


def _textos(widget):
    """Textos de todas las etiquetas y botones bajo ``widget``."""
    out = []
    for w in widget.winfo_children():
        try:
            out.append(str(w.cget("text")))
        except tk.TclError:
            pass
        out += _textos(w)
    return out


# --------------------------------------------------------------------------- pestaña 2
def test_t2_encabezado_y_controles(app):
    t = app.tabs[1]
    textos = _textos(t)
    assert "Conversión masiva" in textos and "Pega varias coordenadas y conviértelas a la vez." in textos
    assert "Datum de salida" in textos
    # solo UTM y datum de entrada leído de cada fila: no hay selector de datum de entrada ni de formato
    assert not any("Datum de entrada" in x or "Formato" in x or "Decimal" in x or "GMS" in x for x in textos)
    assert t.panel.selector is None and t.panel.formato == "utm"
    assert t.panel.v_datum.get() == "WGS84 / SIRGAS"  # salida por defecto
    assert [b.cget("text").strip() for b in (t.b_ajustes, t.b_limpiar, t.b_copiar, t.b_convertir)] == \
        ["Ajustes", "Limpiar", "Copiar resultados", "Convertir"]
    assert str(t.b_convertir.cget("style")) == "Principal.TButton" and str(t.b_limpiar.cget("style")) == "Secundario.TButton"
    assert not hasattr(t.panel, "v_zona")  # el huso de salida es un ajuste global


def test_t2_columnas_norte_este_huso_datum(app):
    t = app.tabs[1]
    enc = [t.tree.heading(c, "text") for c in t.tree.cget("columns")]
    assert enc == ["N°", "Norte", "Este", "Huso", "Datum", "Norte WGS84", "Este WGS84", "Huso", "Estado"]
    assert "Zona" not in enc
    t.panel.v_datum.set("PSAD56")
    t.panel._cambio()
    assert [t.tree.heading(c, "text") for c in ("r1", "r2", "r3")] == ["Norte PSAD56", "Este PSAD56", "Huso"]


def test_t2_estilos_de_la_cuadricula(app):
    t = app.tabs[1]
    assert str(t.tree.cget("style")) == "Cuadricula.Treeview"
    assert ttk.Style(app.raiz).lookup("Cuadricula.Treeview", "rowheight") in (str(tema.u(32)), tema.u(32))
    assert str(t.tree.tag_configure("aviso", "background")) == C.fondo_aviso
    assert str(t.tree.tag_configure("error", "background")) == C.fondo_error
    assert str(t.tree.tag_configure("alterna", "background")) == C.fila_alterna
    assert ttk.Style(app.raiz).lookup("Cuadricula.Treeview.Heading", "background").upper() == C.fondo
    assert tema.fuente("cuadricula").actual("family") in ("Cascadia Mono", "Consolas", "Courier New")


def test_t2_filas_con_aviso_error_y_estado_con_icono(app):
    t = app.tabs[1]
    t.tree.focus("0")
    t.pegar("6318400\t337470\t19\tPSAD56\n337470\t6318400\t19\tPSAD56\n6318400\t337470\t19\t\n6318400\t337470\t19\tNAD27\n")
    estado = [str(t.tree.item(str(i), "values")[8]) for i in range(4)]
    assert estado[0] == "✓ OK" and estado[1].startswith("⚠ ") and estado[2] == "✕ Falta el datum."
    assert estado[3].startswith("✕ Datum «NAD27» desconocido")
    assert t.tree.item("0", "tags") == ""  # fila par sin aviso: fondo blanco
    assert t.tree.item("1", "tags") == ("aviso",)
    assert t.tree.item("2", "tags") == ("error",)
    # filas impares sin resultado ni aviso: color alterno
    assert t.tree.item("5", "tags") == ("alterna",) and t.tree.item("6", "tags") == ""
    # el texto copiado no lleva los íconos
    t.tree.selection_set("0")
    assert t.texto_resultados(False).split("\r\n")[0].endswith("\tOK")


def test_t2_texto_de_ayuda_si_esta_vacia(app):
    t = app.tabs[1]
    app.raiz.update_idletasks()
    assert t.l_vacia.cget("text").startswith("Pega tus coordenadas desde Excel con Ctrl+V.")
    assert "Norte, Este, Huso y Datum" in t.l_vacia.cget("text")
    assert t.l_vacia.winfo_manager() == "place"
    t.pegar("6318400\t337470\t19\tPSAD56\n")
    assert t.l_vacia.winfo_manager() == ""
    t.limpiar()
    assert t.l_vacia.winfo_manager() == "place"


def test_t2_mensajes_en_barra_de_estado_sin_ventanas(app, monkeypatch):
    from tkinter import messagebox

    for nombre in ("showinfo", "showwarning", "showerror", "askyesno", "askokcancel"):
        monkeypatch.setattr(messagebox, nombre, lambda *a, **k: pytest.fail("ventana emergente"))
    t = app.tabs[1]
    t.convertir_todo()
    assert app.estado.mensaje == "No hay coordenadas para convertir" and app.estado.tipo == "aviso"
    t.pegar("sin numeros\n")
    assert app.estado.mensaje == "El portapapeles no contiene coordenadas" and app.estado.tipo == "aviso"
    t.pegar("6318400\t337470\t19\tPSAD56\n")
    assert app.estado.mensaje == "1 fila pegada" and app.estado.tipo == "ok"
    t.convertir_todo()
    assert app.estado.mensaje == "Conversión lista" and app.estado.tipo == "ok"
    t.copiar_resultados()
    assert app.estado.mensaje == "Resultados copiados al portapapeles" and app.estado.tipo == "ok"
    t.pegar("6318400\t337470\t19\t\n", desde=1)
    t.convertir_todo()
    assert "1 con error" in app.estado.mensaje and app.estado.tipo == "aviso"
    t.limpiar()
    assert app.estado.mensaje == "Listo"


def test_t2_copiar_resultados_sin_filas_vacias_en_el_portapapeles(app):
    """Regresión: Tk convierte cada salto en CRLF; con "\r\n" quedaba "\r\r\n" y Excel insertaba una fila vacía
    entre cada fila (empezando por la que sigue al encabezado). Se lee el portapapeles real de Windows."""
    win32clipboard = pytest.importorskip("win32clipboard")
    t = app.tabs[1]
    t.tree.focus("0")
    t.pegar("6318400\t337470\t19\tPSAD56\n6297980\t346826\t19\tSAD69\n")
    t.copiar_resultados()
    app.raiz.update()
    win32clipboard.OpenClipboard()
    try:
        crudo = win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
    finally:
        win32clipboard.CloseClipboard()
    assert "\r\r" not in crudo
    lineas = crudo.split("\r\n")
    assert len(lineas) == 3 and all(lineas)  # encabezado + 2 filas, ninguna vacía
    assert lineas[0] == "Norte WGS84\tEste WGS84\tHuso\tEstado" and lineas[1].endswith("\tOK")


def test_icono_de_la_aplicacion(app):
    from pathlib import Path

    ico = Path(__file__).resolve().parents[1] / "recursos" / "coordenadas.ico"
    assert ico.is_file() and ico.read_bytes()[:4] == b"\x00\x00\x01\x00"  # cabecera ICO
    from PIL import Image

    tam = Image.open(ico).info["sizes"]
    assert {(16, 16), (32, 32), (48, 48), (256, 256)} <= set(tam)
    assert getattr(app, "_fotos_icono", None) and app.raiz.iconphoto  # ícono de la ventana


def test_t2_una_sola_fila(app):
    t = app.tabs[1]
    t.tree.focus("0")
    t.pegar("6318400\t337470\t19\tPSAD56\n")
    v = t.tree.item("0", "values")
    assert [str(x) for x in v[1:5]] == ["6318400", "337470", "19", "PSAD56"] and str(v[8]) == "✓ OK"
    assert t.l_resumen.cget("text") == "1 fila · 1 OK · 0 avisos · 0 errores"


# --------------------------------------------------------------------------- pestaña 3
def test_t3_estructura_en_tres_tarjetas(app):
    t = app.tabs[2]
    textos = _textos(t)
    assert "Archivo Excel" in textos and "Convierte las coordenadas de una planilla en una copia nueva." in textos
    for titulo in ("Archivo", "Columnas", "Salida"):
        assert titulo in textos
    # solo UTM: nada de coordenadas geográficas ni de "Zona"
    assert not any(x in textos for x in ("Latitud", "Longitud", "Decimal", "GMS", "Formato de salida", "Zona"))
    assert {"Norte", "Este", "Huso", "Datum de salida"} <= set(textos)
    assert [b.cget("text").strip() for b in (t.b_ajustes, t.b_cancelar, t.b_convertir)] == ["Ajustes", "Cancelar", "Convertir"]
    assert str(t.barra.cget("style")) == "Delgada.Horizontal.TProgressbar"
    assert t.barra.grid_info()["row"] < t.b_convertir.master.grid_info()["row"]  # el progreso va sobre la fila inferior
    assert str(t.vista.cget("style")) == "Cuadricula.Treeview"
    assert t.b_cancelar.instate(["disabled"])


def test_t3_resumen_en_pantalla_y_estado_con_archivo_guardado(app, tmp_path, monkeypatch):
    from tkinter import messagebox

    for nombre in ("showinfo", "showwarning", "showerror", "askyesno"):
        monkeypatch.setattr(messagebox, nombre, lambda *a, **k: pytest.fail("ventana emergente"))
    p = tmp_path / "datos.xlsx"
    _xlsx(p)
    t = app.tabs[2]
    assert t.abrir(str(p))
    assert app.estado.mensaje == "Archivo abierto: datos.xlsx" and app.estado.tipo == "ok"
    assert not t.f_resumen.winfo_manager()  # "Archivo abierto" no ocupa un bloque de la pantalla
    t.v_datum_modo.set("columna")
    assert t.iniciar(confirmar=False)
    _esperar(app, t)
    texto = t.l_msg.cget("text")
    assert "Copia guardada: datos_convertido.xlsx" in texto and "Filas OK: 1 · Filas con error: 1" in texto
    assert "Fila 3:" in texto
    assert t.f_resumen.winfo_manager() == "grid"
    assert app.estado.mensaje == "Copia guardada: datos_convertido.xlsx"
    assert t.b_convertir.instate(["!disabled"]) and t.b_cancelar.instate(["disabled"])
    ws = openpyxl.load_workbook(tmp_path / "datos_convertido.xlsx")["Puntos"]
    assert [ws.cell(1, c).value for c in range(6, 10)] == ["Norte WGS84", "Este WGS84", "Huso", "Estado"]


def test_t3_errores_de_configuracion_en_pantalla_y_barra(app, tmp_path):
    p = tmp_path / "d.xlsx"
    _xlsx(p)
    t = app.tabs[2]
    t.abrir(str(p))
    t.v_col["este"].set("—")
    assert not t.iniciar(confirmar=False)
    assert "Asigne la columna de «Este»" in t.l_msg.cget("text") and app.estado.tipo == "error"
    assert t.f_resumen.winfo_manager() == "grid"


def test_t3_reemplazo_se_confirma_en_pantalla_sin_ventana(app, tmp_path, monkeypatch):
    from tkinter import messagebox

    monkeypatch.setattr(messagebox, "askyesno", lambda *a, **k: pytest.fail("ventana emergente"))
    p = tmp_path / "datos.xlsx"
    _xlsx(p)
    t = app.tabs[2]
    t.abrir(str(p))
    t.v_datum_modo.set("columna")
    assert t.iniciar(confirmar=False)
    _esperar(app, t)
    assert (tmp_path / "datos_convertido.xlsx").exists()
    # segunda ejecución: el destino ya existe → pide confirmar en pantalla; la segunda pulsación reemplaza
    assert not t.iniciar()
    assert "Ya existe" in t.l_msg.cget("text") and app.estado.tipo == "aviso"
    assert t.iniciar()
    _esperar(app, t)
    assert t.ultimo_resumen.ok == 1
    # cambiar el destino invalida la confirmación
    t.v_destino.set(str(tmp_path / "otro.xlsx"))
    assert t._reemplazo_ok is None


def test_ajustes_en_las_tres_pestanas_abre_el_mismo_dialogo(app):
    from coordenadas.ui.dialogo_ajustes import DialogoAjustes

    abiertos = []

    def cerrar():  # el diálogo es modal (wait_window): se cierra desde un temporizador
        for w in app.raiz.winfo_children():
            if isinstance(w, DialogoAjustes):
                abiertos.append(w.title())
                w.cancelar()

    for t in app.tabs:
        assert str(t.b_ajustes.cget("style")) == "Discreto.TButton"
        app.raiz.after(100, cerrar)
        t.b_ajustes.invoke()
    assert abiertos == ["Ajustes"] * 3
