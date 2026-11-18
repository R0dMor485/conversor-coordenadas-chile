"""U2: pestaña "Calcular Coordenadas", diálogo Ajustes y ajustes globales en las tres pestañas."""
import json
import time
import tkinter as tk

import pytest

from coordenadas.ui import app as modulo_app

REVISAR = "Revisa el campo marcado en rojo"


def _t1(app):
    return app.tabs[0]


def _caso_conocido(t):
    """PSAD56 → WGS84: N 6318400, E 337470, zona 19 → N 6318027, E 337287, zona 19 (0 decimales)."""
    t.v_datum_in.set("PSAD56")
    t.panel.v_datum.set("WGS84 / SIRGAS")
    t.panel._cambio()
    t.v_formato.set("utm")
    t._cambio_formato()
    t.v["norte"].set("6318400")
    t.v["este"].set("337470")
    t.v["zona"].set("19")
    return t.convertir()


def _botones_copiar(t):
    filas = [f.b_copiar for f in t.filas_res.values() if f.b_copiar is not None]
    return filas + [t.b_par_utm, t.b_par_dec, t.b_par_gms]


def _esperar(app, cond, limite=5.0):
    t0 = time.time()
    while not cond():
        app.raiz.update()
        time.sleep(0.01)
        assert time.time() - t0 < limite


# --------------------------------------------------------------------------- valores por defecto
def test_por_defecto_utm_en_entrada_y_salida(app):
    t = _t1(app)
    assert t.v_formato.get() == "utm" and t.panel.v_formato.get() == "utm"
    assert t.sel_formato.botones["utm"].instate(["selected"])
    assert t.panel.selector.botones["utm"].instate(["selected"])
    assert not t.sel_formato.botones["decimal"].instate(["selected"])
    assert t.f_utm.winfo_manager() and not t.f_dec.winfo_manager() and not t.f_gms.winfo_manager()
    assert app.estado.mensaje == "Listo"
    assert app.v_estado.get() == "Tabla IGM vigente · Precisión declarada ±5 m"
    assert t.l_ayuda_dec.cget("text") == "Los valores positivos se interpretan como S y O."


def test_sin_resultado_valores_vacios_y_copiar_deshabilitado(app):
    t = _t1(app)
    for f in t.filas_res.values():
        assert f.v_mostrar.get() == "—"
    for b in _botones_copiar(t):
        assert b.instate(["disabled"]), b
    app.raiz.clipboard_clear()
    app.raiz.clipboard_append("intacto")
    for b in _botones_copiar(t):
        b.invoke()  # deshabilitados: no hacen nada
    assert app.raiz.clipboard_get() == "intacto"


# --------------------------------------------------------------------------- conversión y copiado
def test_caso_conocido_psad56_a_wgs84(app):
    t = _t1(app)
    assert _caso_conocido(t)
    assert (t.o["norte"].get(), t.o["este"].get(), t.o["zona"].get()) == ("6318027", "337287", "19")
    assert t.filas_res["norte"].v_mostrar.get() == "6318027"
    assert app.estado.mensaje == "Conversión lista" and app.estado.tipo == "ok"
    assert not t.l_msg.winfo_manager()


def test_portapapeles_tras_cada_boton(app, monkeypatch):
    monkeypatch.setattr(modulo_app, "MS_TEMPORAL", 60)
    t = _t1(app)
    _caso_conocido(t)
    casos = [
        (t.filas_res["norte"].b_copiar, "6318027", "Norte copiado al portapapeles"),
        (t.filas_res["este"].b_copiar, "337287", "Este copiado al portapapeles"),
        (t.b_par_utm, "6318027\t337287", "Norte y Este copiados al portapapeles"),
    ]
    for boton, esperado, aviso in casos:
        assert not boton.instate(["disabled"])
        boton.invoke()
        assert app.raiz.clipboard_get() == esperado
        assert app.estado.mensaje == aviso and app.estado.tipo == "ok"
    _esperar(app, lambda: app.estado.mensaje == "Listo")  # vuelve a "Listo" tras el aviso temporal
    assert t.filas_res["zona"].b_copiar is None  # la zona no tiene botón
    # Decimal
    t.panel.v_formato.set("decimal")
    t.panel._cambio()
    lat, lon = t.o["lat"].get(), t.o["lon"].get()
    assert lat.startswith("-33.") and len(lat.split(".")[1]) == 6
    t.filas_res["lat"].b_copiar.invoke()
    assert app.raiz.clipboard_get() == lat and app.estado.mensaje == "Latitud copiada al portapapeles"
    t.filas_res["lon"].b_copiar.invoke()
    assert app.raiz.clipboard_get() == lon
    t.b_par_dec.invoke()
    assert app.raiz.clipboard_get() == f"{lat}, {lon}"
    # GMS
    t.panel.v_formato.set("gms")
    t.panel._cambio()
    glat, glon = t.o["glat"].get(), t.o["glon"].get()
    assert glat.endswith('" S') and glon.endswith('" O')
    t.filas_res["glat"].b_copiar.invoke()
    assert app.raiz.clipboard_get() == glat
    t.filas_res["glon"].b_copiar.invoke()
    assert app.raiz.clipboard_get() == glon
    t.b_par_gms.invoke()
    assert app.raiz.clipboard_get() == f"{glat}\t{glon}"
    assert app.estado.mensaje == "Latitud y longitud copiadas al portapapeles"


def test_enter_en_un_campo_convierte(app):
    t = _t1(app)
    t.v_datum_in.set("PSAD56")
    t.v["norte"].set("6318400")
    t.v["este"].set("337470")
    app.nb.select(0)
    t.ent["este"].focus_set()
    app._enter()
    assert t.resultado is not None


# --------------------------------------------------------------------------- errores en línea
@pytest.mark.parametrize("formato,campo,valores,mensaje", [
    ("utm", "norte", {"norte": "", "este": "337470"}, "Ingresa un valor."),
    ("utm", "norte", {"norte": "abc", "este": "337470"}, "Ingresa solo números."),
    ("utm", "norte", {"norte": "1000", "este": "337470"}, "Debe estar entre 3700000 y 8100000."),
    ("utm", "este", {"norte": "6318400", "este": "1337470"}, "Debe estar entre 100000 y 900000."),
    ("utm", "zona", {"norte": "6318400", "este": "337470", "zona": "21"}, "Debe ser 18 o 19."),
    ("decimal", "lon", {"lat": "-33.4", "lon": "-80"}, "Fuera del rango de Chile continental."),
    ("decimal", "lat", {"lat": "33.4", "lon": "70.6"}, None),  # control: positivos = S y O → sin error
    ("decimal", "lat", {"lat": "x", "lon": "70.6"}, "Ingresa solo números."),
    ("gms", "glat", {"lat_g": "", "lon_g": "70"}, "Ingresa un valor."),
    ("gms", "glon", {"lat_g": "33", "lon_g": "70", "lon_m": "75"}, "Los minutos deben ser menores que 60."),
])
def test_error_en_linea(app, formato, campo, valores, mensaje):
    t = _t1(app)
    assert _caso_conocido(t)  # hay un resultado previo
    t.v_formato.set(formato)
    t._cambio_formato()
    if formato != "utm":  # con cambio de datum rigen los rangos de Chile continental
        t.panel.v_datum.set("PSAD56")
        t.panel._cambio()
    for k, v in valores.items():
        t.v[k].set(v)
    ok = t.convertir()
    c = t.campos[campo]
    if mensaje is None:
        assert ok and c.error == ""
        return
    assert not ok
    assert c.error.strip() == mensaje
    assert str(c.l_etiqueta.cget("style")) == "EtiquetaError.TLabel"
    assert any(w.instate(["invalid"]) for w in c.controles)
    assert app.estado.mensaje == REVISAR and app.estado.tipo == "revisar"
    # la salida vuelve a "—" con los botones deshabilitados
    assert t.resultado is None
    assert all(f.v_mostrar.get() == "—" for f in t.filas_res.values())
    assert all(b.instate(["disabled"]) for b in _botones_copiar(t))
    # el error desaparece al editar el campo, y la barra vuelve a "Listo"
    clave = {"glat": "lat_g", "glon": "lon_m"}.get(campo, campo)
    t.v[clave].set("1")
    assert c.error == "" and not any(w.instate(["invalid"]) for w in c.controles)
    assert app.estado.mensaje == "Listo"


def test_mensaje_del_nucleo_en_salida_y_barra(app):
    t = _t1(app)
    t.v_formato.set("decimal")
    t._cambio_formato()
    t.v["lat"].set("-60.5")
    t.v["lon"].set("-70")
    t.panel.v_datum.set("PSAD56")
    t.panel._cambio()
    assert not t.convertir()
    assert "No existen parámetros" in t.l_msg.cget("text") and t.l_msg.winfo_manager()
    assert "No existen parámetros" in app.estado.mensaje and app.estado.tipo == "error"
    assert all(c.error == "" for c in t.campos.values())


def test_limpiar(app):
    t = _t1(app)
    _caso_conocido(t)
    t.v["este"].set("1337470")
    t.convertir()
    assert t.campos["este"].error
    t.limpiar()
    assert t.v["norte"].get() == "" and t.v["este"].get() == "" and t.v["zona"].get() == "19"
    assert all(c.error == "" for c in t.campos.values())
    assert all(v.get() == "" for v in t.o.values()) and t.resultado is None
    assert all(b.instate(["disabled"]) for b in _botones_copiar(t))
    assert app.estado.mensaje == "Listo" and not t.l_msg.winfo_manager()


# --------------------------------------------------------------------------- diálogo Ajustes
def test_ajustes_se_aplican_solo_con_aceptar_y_se_guardan(app, tmp_path):
    ruta = tmp_path / "config.json"
    d = app.abrir_ajustes(esperar=False)
    assert d.title() == "Ajustes" and d.resizable() == (False, False)
    assert str(d.transient()) == str(app.raiz)
    d.v_metodo.set("replica_exe")
    d.v_zona.set("Forzar 18")
    d.v_dec_utm.set("2")
    d.v_dec_gr.set("8")
    d.v_sep.set(",")
    d.v_pos.set(False)
    # antes de Aceptar no cambia nada (ni en memoria ni en config.json)
    assert (app.op.metodo, app.op.zona_salida, app.op.decimales_utm) == ("tabla_igm", "auto", 0)
    if ruta.exists():
        assert json.loads(ruta.read_text(encoding="utf-8"))["decimales_utm"] == 0
    assert d.aceptar()
    assert not d.winfo_exists()
    op = app.op
    assert (op.metodo, op.zona_salida, op.decimales_utm, op.decimales_grados, op.separador_decimal,
            op.positivos_sur_oeste) == ("replica_exe", "18", 2, 8, ",", False)
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    assert (datos["metodo"], datos["zona_salida"], datos["decimales_utm"], datos["decimales_grados"],
            datos["separador_decimal"], datos["positivos_sur_oeste"]) == ("replica_exe", "18", 2, 8, ",", False)
    assert app.v_estado.get() == "Réplica de Datum_datum.exe · Precisión declarada ±5 m"
    assert _t1(app).l_ayuda_dec.cget("text") == "Usa signo negativo para S y O."
    # al reabrir, el diálogo muestra los valores vigentes
    d = app.abrir_ajustes(esperar=False)
    assert (d.v_metodo.get(), d.v_zona.get(), d.v_dec_utm.get(), d.v_sep.get(), d.v_pos.get()) == \
        ("replica_exe", "Forzar 18", "2", ",", False)
    d.cancelar()


def test_ajustes_cancelar_descarta(app):
    d = app.abrir_ajustes(esperar=False)
    d.v_dec_utm.set("3")
    d.v_sep.set(",")
    d.cancelar()
    assert not d.winfo_exists()
    assert app.op.decimales_utm == 0 and app.op.separador_decimal == "."


@pytest.mark.parametrize("clave,valor,mensaje", [
    ("decimales_grados", "12", "Debe estar entre 0 y 10."),
    ("decimales_utm", "5", "Debe estar entre 0 y 4."),
    ("decimales_utm", "-1", "Usa un entero entre 0 y 4."),
    ("decimales_utm", "x", "Usa un entero entre 0 y 4."),
    ("decimales_grados", "", "Ingresa un valor."),
])
def test_ajustes_valida_decimales_en_linea(app, clave, valor, mensaje):
    d = app.abrir_ajustes(esperar=False)
    cc, e, var = d.campos_dec[clave]
    var.set(valor)
    d.v_sep.set(",")
    assert not d.aceptar()
    assert d.winfo_exists() and cc.error.strip() == mensaje and e.instate(["invalid"])
    assert app.op.separador_decimal == "."  # nada se aplicó
    var.set("2")  # al corregir desaparece el error
    assert cc.error == ""
    d.cancelar()


def test_esc_cancela_y_enter_acepta(raiz_tk, tmp_path):
    """Con la ventana visible (las teclas van a la ventana con foco)."""
    from coordenadas.ui.app import App

    top = tk.Toplevel(raiz_tk)
    top.geometry("+40+40")
    a = App(top, ruta_config=tmp_path / "config.json")
    try:
        top.update()
        d = a.abrir_ajustes(esperar=False)
        d.update()
        d.focus_force()
        d.update()
        if d.focus_get() is None:
            pytest.skip("el entorno no permite dar el foco a una ventana (sin escritorio interactivo)")
        d.v_dec_utm.set("3")
        d.event_generate("<Escape>")
        assert not d.winfo_exists() and a.op.decimales_utm == 0
        d = a.abrir_ajustes(esperar=False)
        d.update()
        d.focus_force()
        d.update()
        d.v_dec_utm.set("2")
        d.event_generate("<Return>")
        assert not d.winfo_exists() and a.op.decimales_utm == 2
    finally:
        top.destroy()


# --------------------------------------------------------------------------- ajustes globales en las tres pestañas
def _esperar_excel(app, tab, limite=60):
    t0 = time.time()
    while tab.hilo is not None and (tab.hilo.is_alive() or str(tab.b_convertir.cget("state")) == "disabled"):
        app.raiz.update()
        time.sleep(0.02)
        assert time.time() - t0 < limite


def _csv_t3(app, tmp_path, texto, nombre="p.csv", datum_entrada="PSAD56", datum_salida="WGS84 / SIRGAS"):
    """Convierte un csv (Norte;Este;Huso) en la pestaña 3 y devuelve la primera fila de datos."""
    p = tmp_path / nombre
    p.write_text(texto, encoding="utf-8")
    t = app.tabs[2]
    assert t.abrir(str(p))
    t.v_datum_in.set(datum_entrada)
    t.panel.v_datum.set(datum_salida)
    assert t.iniciar(confirmar=False)
    _esperar_excel(app, t)
    linea = (tmp_path / nombre.replace(".csv", "_convertido.csv")).read_text(encoding="utf-8-sig").splitlines()[1]
    return linea.split(";")


def _t2_fila(app, texto, datum_salida="WGS84 / SIRGAS"):
    t = app.tabs[1]
    t.limpiar()
    t.panel.v_datum.set(datum_salida)
    t.panel._cambio()
    t.tree.focus("0")
    t.pegar(texto)
    return t.filas[0].res, [str(x) for x in t.tree.item("0", "values")]


CSV_UTM = "Norte;Este;Huso\n6318400;337470;19\n"


def test_global_decimales_y_separador_en_las_tres_pestanas(app, tmp_path):
    app.aplicar_ajustes(decimales_utm=2, separador_decimal=",")
    t = _t1(app)
    _caso_conocido(t)
    n = t.o["norte"].get()
    assert n.split(",")[0] in ("6318026", "6318027") and len(n.split(",")[1]) == 2
    res, vals = _t2_fila(app, "6318400\t337470\t19\tPSAD56\n")
    assert res.nivel == "ok" and "," in vals[5] and len(vals[5].split(",")[1]) == 2
    fila = _csv_t3(app, tmp_path, CSV_UTM)
    assert "," in fila[3] and len(fila[3].split(",")[1]) == 2 and fila[-1] == "OK"


def test_global_positivos_como_sur_y_oeste_en_la_pestana_1(app):
    """Las pestañas 2 y 3 son solo UTM; este ajuste afecta a las coordenadas geográficas de la pestaña 1."""
    t = _t1(app)
    t.v_formato.set("decimal")
    t._cambio_formato()
    t.v["lat"].set("33.4489")
    t.v["lon"].set("70.6693")
    assert t.convertir() and t.resultado.lat < 0 and t.resultado.lon < 0
    app.aplicar_ajustes(positivos_sur_oeste=False)
    assert t.resultado is None and t.campos["lat"].error  # se recalculó: ahora es hemisferio norte
    assert t.l_ayuda_dec.cget("text") == "Usa signo negativo para S y O."


def test_global_zona_forzada_en_las_tres_pestanas(app, tmp_path):
    t = _t1(app)
    _caso_conocido(t)
    assert t.o["zona"].get() == "19"
    app.aplicar_ajustes(zona_salida="18")
    assert t.o["zona"].get() == "18" and int(t.o["este"].get()) > 800000  # recalculado en el huso 18
    res, vals = _t2_fila(app, "6318400\t337470\t19\tPSAD56\n")
    assert vals[7] == "18"
    fila = _csv_t3(app, tmp_path, CSV_UTM)
    assert fila[5] == "18"
    app.aplicar_ajustes(zona_salida="auto")
    assert t.o["zona"].get() == "19"


# --------------------------------------------------------------------------- valores por defecto, reglas de datum y reinicio
def _claves(cb):
    from coordenadas.ui.comun import CLAVE_POR_ETIQUETA

    return [CLAVE_POR_ETIQUETA[v] for v in cb.cget("values")]


def test_defaults_psad56_a_wgs84_y_exclusion_del_mismo_datum(app):
    t = _t1(app)
    assert t.v_datum_in.get() == "PSAD56" and t.panel.v_datum.get() == "WGS84 / SIRGAS"
    assert _claves(t.panel.cb_datum) == ["SIRGAS", "SAD69"]  # PSAD56 no se ofrece en la salida (UTM → UTM)
    # otro datum de entrada: la lista de salida se ajusta
    t.v_datum_in.set("SAD69")
    t._cambio_entrada()
    assert _claves(t.panel.cb_datum) == ["SIRGAS", "PSAD56"] and t.panel.v_datum.get() == "WGS84 / SIRGAS"
    assert app.estado.mensaje == "Listo"  # la salida no cambió: sin aviso


def test_entrada_igual_a_la_salida_cambia_la_salida(app):
    t = _t1(app)
    t.v_datum_in.set("WGS84 / SIRGAS")  # justo el datum de salida actual
    t._cambio_entrada()
    assert t.panel.v_datum.get() == "PSAD56" and _claves(t.panel.cb_datum) == ["PSAD56", "SAD69"]
    assert app.estado.mensaje == "Datum de salida cambiado a PSAD56" and app.estado.tipo == "info"


def test_defaults_al_cambiar_el_formato_de_entrada(app):
    t = _t1(app)
    t.v_datum_in.set("SAD69")
    t._cambio_entrada()
    for fmt in ("decimal", "gms"):
        t.v_formato.set(fmt)
        t._cambio_formato()
        # entrada WGS84 y salida UTM WGS84: el mismo datum es válido (solo cambia el formato)
        assert t.v_datum_in.get() == "WGS84 / SIRGAS" and t.panel.v_datum.get() == "WGS84 / SIRGAS"
        assert t.panel.formato == "utm" and _claves(t.panel.cb_datum) == ["SIRGAS", "PSAD56", "SAD69"]
    t.v_formato.set("utm")
    t._cambio_formato()
    assert t.v_datum_in.get() == "PSAD56" and t.panel.v_datum.get() == "WGS84 / SIRGAS"
    assert _claves(t.panel.cb_datum) == ["SIRGAS", "SAD69"]


def test_salida_decimal_admite_el_mismo_datum_y_utm_lo_excluye(app):
    t = _t1(app)  # entrada UTM PSAD56
    t.panel.v_formato.set("decimal")
    t.panel._cambio()
    assert _claves(t.panel.cb_datum) == ["SIRGAS", "PSAD56", "SAD69"]  # lat/lon en PSAD56 es válido
    t.panel.v_datum.set("PSAD56")
    t.panel._cambio()
    t.panel.v_formato.set("utm")  # UTM → UTM con el mismo datum: se mueve a otro
    t.panel._cambio()
    assert t.panel.v_datum.get() == "WGS84 / SIRGAS" and _claves(t.panel.cb_datum) == ["SIRGAS", "SAD69"]


def test_copiar_todo_y_ayuda_sin_hemisferio(app):
    t = _t1(app)
    assert [b.cget("text").strip() for b in (t.b_par_utm, t.b_par_dec, t.b_par_gms)] == ["Copiar todo"] * 3
    textos = [str(w.cget("text")) for w in t.f_utm.winfo_children() if "text" in w.keys()]
    assert "Huso 18 o 19 (Chile continental)." in textos and not any("Hemisferio" in x for x in textos)
    _caso_conocido(t)
    t.b_par_utm.invoke()
    assert app.raiz.clipboard_get() == "6318027\t337287"  # sin huso ni datum
    assert t.filas_res["zona"].l_nombre.cget("text") == "Huso"


def test_al_reabrir_solo_se_conservan_los_ajustes_y_la_ventana(raiz_tk, tmp_path):
    from coordenadas import config
    from coordenadas.ui.app import App

    ruta = tmp_path / "config.json"
    config.guardar(config.Opciones(decimales_utm=2, separador_decimal=",", zona_salida="18", ultimas={
        "pestana": 2, "t1_datum_entrada": "SAD69", "t1_formato_entrada": "gms", "t2_datum_salida": "PSAD56",
        "t3_carpeta": "C:/otra", "ventana": "900x700+30+30", "ventana_escala": 1.0}), ruta)
    top = tk.Toplevel(raiz_tk)
    top.withdraw()
    a = App(top, ruta_config=ruta)
    try:
        assert a.nb.index(a.nb.select()) == 0  # siempre abre en la pestaña 1
        t = a.tabs[0]
        assert t.v_formato.get() == "utm" and t.v_datum_in.get() == "PSAD56" and t.panel.v_datum.get() == "WGS84 / SIRGAS"
        assert a.tabs[1].panel.v_datum.get() == "WGS84 / SIRGAS"
        assert (a.op.decimales_utm, a.op.separador_decimal, a.op.zona_salida) == (2, ",", "18")  # Ajustes se mantienen
        assert "ventana" in a.op.ultimas and "pestana" not in a.op.ultimas
        a.nb.select(2)
        t.v["norte"].set("1")
        a.cerrar()
        datos = json.loads(ruta.read_text(encoding="utf-8"))
        assert set(datos["ultimas"]) <= {"ventana", "ventana_escala", "ventana_max"}
        assert datos["decimales_utm"] == 2
    finally:
        try:
            top.destroy()
        except tk.TclError:
            pass
