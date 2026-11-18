"""U1: tema (sv-ttk + estilos propios), escala, imágenes, componentes y ventana base."""
import json
import struct
import time
import tkinter as tk
import zlib
from tkinter import ttk

from coordenadas.ui import componentes as K
from coordenadas.ui import imagenes as im
from coordenadas.ui import tema


def test_tema_sv_ttk_y_estilos(app):
    st = ttk.Style(app.raiz)
    assert st.theme_use() == "sun-valley-light"
    for estilo in ("Tarjeta.TFrame", "Campo.TEntry", "Campo.TCombobox", "Principal.TButton", "Secundario.TButton",
                   "Segizq.TRadiobutton", "Casilla.TCheckbutton", "App.TNotebook", "Cuadricula.Treeview"):
        assert st.layout(estilo), estilo
    assert st.lookup("TFrame", "background").upper() == tema.C.fondo
    assert st.lookup("Tarjeta.TFrame", "background").upper() == tema.C.tarjeta
    assert st.lookup("Principal.TButton", "foreground").upper() == "#FFFFFF"
    assert tema.C.acento == "#1F5FBF"  # acento exacto (elementos propios, no el azul de sv-ttk)


def test_etiquetas_no_heredan_paleta_de_sv_ttk(app):
    """tk_setPalette de sv-ttk no debe pisar el fondo/color de las etiquetas ttk."""
    app.raiz.update_idletasks()
    t1 = app.tabs[0]
    titulo = t1.grid_slaves(row=0)[0].l_titulo
    assert str(titulo.cget("background")) == "" and str(titulo.cget("foreground")) == ""


def test_escala_y_fuentes(app):
    f = tema.escala()
    assert abs(f - float(app.raiz.tk.call("tk", "scaling")) * 72 / 96) < 1e-9
    assert tema.u(100) == round(100 * f)
    familias = {n: tema.fuente(n).actual("family") for n in ("titulo", "texto", "mono", "resultado")}
    import tkinter.font as tkfont

    disponibles = set(tkfont.families(app.raiz))
    if "Segoe UI Semibold" in disponibles:
        assert familias["titulo"] == "Segoe UI Semibold"
    if "Segoe UI" in disponibles:
        assert familias["texto"] == "Segoe UI"
    if "Cascadia Mono" in disponibles:
        assert familias["mono"] == "Cascadia Mono"
    assert tema.fuente("titulo").actual("size") == 15 and tema.fuente("resultado").actual("size") == 16


def test_png_rgba_valido():
    lz = im.rect_redondeado(20, 20, 6, "#FFFFFF", "#C3CAD5")
    datos = lz.png()
    assert datos[:8] == b"\x89PNG\r\n\x1a\n"
    ancho, alto = struct.unpack(">II", datos[16:24])
    assert (ancho, alto) == (20, 20)
    i = datos.index(b"IDAT")
    largo = struct.unpack(">I", datos[i - 4:i])[0]
    crudo = zlib.decompress(datos[i + 4:i + 4 + largo])
    fila = lambda y: crudo[y * (1 + 80) + 1:(y + 1) * (1 + 80)]  # noqa: E731
    assert fila(0)[3] == 0  # esquina transparente (radio 6)
    assert fila(10)[40:44] == b"\xff\xff\xff\xff"  # centro blanco opaco


def test_iconos_se_dibujan():
    for nombre in ("copiar", "ajustes", "check", "alerta", "aviso", "cruz", "abajo", "radio_sel", "casilla_sel"):
        lz = im.icono(nombre, "#1F5FBF", 16)
        assert any(lz.p[i + 3] > 0.5 for i in range(0, len(lz.p), 4)), nombre


def test_ventana_base(app):
    r = app.raiz
    assert r.title() == "Conversor de Coordenadas"
    assert [app.nb.tab(i, "text") for i in range(3)] == ["Calcular Coordenadas", "Conversión masiva", "Archivo Excel"]
    wmin, hmin = r.minsize()
    assert wmin >= min(tema.u(820), r.winfo_screenwidth() - tema.u(16)) - 1
    assert hmin >= min(tema.u(680), r.winfo_screenheight() - tema.u(120)) - 1
    assert r.resizable() == (True, True)
    assert app.estado.mensaje == "Listo"
    assert app.v_estado.get() == "Tabla IGM vigente · Precisión declarada ±5 m"


def test_geometria_se_recuerda(raiz_tk, tmp_path):
    from coordenadas.ui.app import App

    top = tk.Toplevel(raiz_tk)
    top.withdraw()
    a = App(top, ruta_config=tmp_path / "config.json")
    top.geometry(f"{tema.u(900)}x{tema.u(740)}+60+50")
    top.update_idletasks()
    a.cerrar()
    datos = json.loads((tmp_path / "config.json").read_text(encoding="utf-8"))
    assert datos["ultimas"]["ventana"].startswith(f"{tema.u(900)}x{tema.u(740)}")
    top = tk.Toplevel(raiz_tk)
    top.withdraw()
    App(top, ruta_config=tmp_path / "config.json")
    top.update_idletasks()
    assert top.geometry().startswith(f"{tema.u(900)}x{tema.u(740)}")
    top.destroy()


def test_config_no_escribible_no_impide_abrir_ni_cerrar(raiz_tk, tmp_path):
    from coordenadas.ui.app import App

    top = tk.Toplevel(raiz_tk)
    top.withdraw()
    a = App(top, ruta_config=tmp_path / "no_existe" / "config.json")
    a.aplicar_ajustes(decimales_utm=2)
    a.cerrar()  # sin excepción


def test_dibujo_rapido(raiz_tk, tmp_path):
    """Regresión: piezas 9-slice pequeñas hacían que un update() tardara ~30 s."""
    from coordenadas.ui.app import App

    top = tk.Toplevel(raiz_tk)
    top.withdraw()
    App(top, ruta_config=tmp_path / "c.json")
    t0 = time.perf_counter()
    top.update()
    assert time.perf_counter() - t0 < 3.0
    top.destroy()


# --------------------------------------------------------------------------- componentes
def test_selector_segmentado(app):
    v = tk.StringVar(value="utm")
    llamadas = []
    s = K.SelectorSegmentado(app.raiz, v, [("utm", "U.T.M."), ("decimal", "Decimal"), ("gms", "GMS")],
                             lambda: llamadas.append(v.get()))
    assert s.botones["utm"].instate(["selected"]) and not s.botones["gms"].instate(["selected"])
    assert str(s.botones["utm"].cget("takefocus")) == "1" and str(s.botones["gms"].cget("takefocus")) == "0"
    s._mover(1)
    assert v.get() == "decimal" and llamadas == ["decimal"]
    s._mover(5)
    assert v.get() == "gms"
    v.set("utm")
    assert str(s.botones["utm"].cget("takefocus")) == "1"


def test_campo_con_error(app):
    v = tk.StringVar()
    avisos = []
    c = K.CampoConError(app.raiz, "Norte (m)", al_editar=lambda: avisos.append(1))
    e = c.agregar(K.entrada(c.cuerpo, v, mono=True), v)
    c.mostrar_error("Ingresa un valor.")
    assert c.error.strip() == "Ingresa un valor." and e.instate(["invalid"])
    assert str(c.l_etiqueta.cget("style")) == "EtiquetaError.TLabel"
    v.set("1")  # editar quita el error
    assert c.error == "" and not e.instate(["invalid"]) and avisos == [1]
    assert str(c.l_etiqueta.cget("style")) == "Etiqueta.TLabel"


def test_fila_resultado(app):
    v = tk.StringVar()
    f = K.FilaResultado(app.raiz, "Norte", v, lambda: None)
    assert f.v_mostrar.get() == "—" and f.b_copiar.instate(["disabled"])
    v.set("6318027")
    assert f.v_mostrar.get() == "6318027" and not f.b_copiar.instate(["disabled"])


def test_barra_estado_temporal(app):
    b = app.estado
    b.mostrar("Norte copiado al portapapeles", "ok", 50)
    assert b.mensaje == "Norte copiado al portapapeles" and b.tipo == "ok"
    t0 = time.time()
    while b.mensaje != "Listo" and time.time() - t0 < 3:
        app.raiz.update()
        time.sleep(0.01)
    assert b.mensaje == "Listo" and b.tipo == "info"
