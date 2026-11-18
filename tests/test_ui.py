"""Pruebas de la interfaz (ventana real de Tk, sin interacción humana)."""
import json
import tkinter as tk

import pytest

from coordenadas import config
from coordenadas.core.constantes import Metodo




def _t1(app):
    return app.tabs[0]


def test_valores_por_defecto(app):
    t = _t1(app)
    assert t.v_formato.get() == "utm"  # U.T.M. marcado por defecto
    assert app.op.metodo == Metodo.TABLA_IGM.value
    assert app.op.decimales_utm == 0 and app.op.decimales_grados == 6
    assert app.op.separador_decimal == "." and app.op.positivos_sur_oeste
    assert "Tabla IGM vigente" in app.v_estado.get() and "±5 m" in app.v_estado.get()


def test_convertir_utm_a_utm(app):
    t = _t1(app)
    t.v["norte"].set("6.297.606,833")
    t.v["este"].set("346642,695")
    t.v["zona"].set("19")
    t.convertir()
    assert t.resultado is not None
    assert t.o["norte"].get().isdigit() and t.o["zona"].get() == "19"
    assert "." not in t.o["norte"].get()  # 0 decimales por defecto, sin miles
    t._copiar_ne()
    assert app.raiz.clipboard_get() == f"{t.o['norte'].get()}\t{t.o['este'].get()}"


def test_convertir_decimal_y_formatos_de_salida(app):
    t = _t1(app)
    t.v_formato.set("decimal")
    t._cambio_formato()
    t.v["lat"].set("33,4489")
    t.v["lon"].set("70.6693")
    t.panel.v_formato.set("decimal")
    t.panel._cambio()
    t.convertir()
    lat = t.o["lat"].get()
    assert lat.startswith("-33.") and len(lat.split(".")[1]) == 6
    t._copiar_latlon()
    assert app.raiz.clipboard_get() == f"{lat}, {t.o['lon'].get()}"
    t.panel.v_formato.set("gms")
    t.panel._cambio()
    assert t.o["glat"].get().endswith('" S') and t.o["glon"].get().endswith('" O')
    # separador decimal coma
    app.aplicar_ajustes(separador_decimal=",")  # antes: barra de opciones; ahora diálogo Ajustes
    t.panel.v_formato.set("decimal")
    t.panel._cambio()
    assert "," in t.o["lat"].get()
    t._copiar_latlon()
    assert "; " in app.raiz.clipboard_get()


def test_gms_con_grados_decimales_da_error_no_bloqueante(app):
    t = _t1(app)
    t.v_formato.set("gms")
    t._cambio_formato()
    for k, v in {"lat_g": "33,5", "lat_m": "0", "lat_s": "0", "lon_g": "70", "lon_m": "39", "lon_s": "0"}.items():
        t.v[k].set(v)
    t.convertir()
    assert t.resultado is None and "decimales" in t.campos["glat"].error  # error en línea del campo


def test_sin_parametros_mensaje_claro(app):
    t = _t1(app)
    t.v_formato.set("decimal")
    t._cambio_formato()
    t.v["lat"].set("50")
    t.v["lon"].set("72")
    t.panel.v_datum.set("PSAD56")
    t.panel._cambio()
    t.convertir()
    assert t.resultado is None and "No existen parámetros" in t.l_msg.cget("text")
    assert t.o["norte"].get() == ""  # nunca resultado basura


def test_zona_forzada_y_metodo(app):
    t = _t1(app)
    t.v_formato.set("decimal")
    t._cambio_formato()
    t.v["lat"].set("-33.4489")
    t.v["lon"].set("-70.6693")
    t.panel.v_datum.set("PSAD56")
    app.aplicar_ajustes(zona_salida="18")  # zona de salida: ajuste global
    t.panel._cambio()
    t.convertir()
    assert t.o["zona"].get() == "18" and int(t.o["este"].get()) > 900000  # sin espejado
    # cambiar de método recalcula; SAD69 en 33° S no cambia entre métodos, en 30° S sí
    t.panel.v_datum.set("SAD69")
    app.aplicar_ajustes(zona_salida="auto")
    t.v["lat"].set("-30.6014")
    t.panel._cambio()
    n_tabla = t.o["norte"].get()
    app.aplicar_ajustes(metodo=Metodo.REPLICA_EXE)
    assert "Réplica" in app.v_estado.get()
    assert abs(int(t.o["norte"].get()) - int(n_tabla)) >= 9


def test_enter_convierte(app):
    t = _t1(app)
    t.v["norte"].set("6297606")
    t.v["este"].set("346642")
    app.nb.select(0)
    app._enter()
    assert t.resultado is not None


def test_opciones_se_guardan(app, tmp_path):
    app.aplicar_ajustes(decimales_utm=3)
    datos = json.loads((tmp_path / "config.json").read_text(encoding="utf-8"))
    assert datos["decimales_utm"] == 3


# --------------------------------------------------------------------------- config
def test_config_danado_o_ausente(tmp_path):
    p = tmp_path / "config.json"
    assert config.cargar(p) == config.Opciones()
    p.write_text("{no es json", encoding="utf-8")
    assert config.cargar(p) == config.Opciones()
    p.write_text(json.dumps({"metodo": "otro", "decimales_utm": 99, "separador_decimal": ";", "positivos_sur_oeste": "si"}), encoding="utf-8")
    assert config.cargar(p) == config.Opciones()


def test_config_ida_y_vuelta(tmp_path):
    p = tmp_path / "config.json"
    op = config.Opciones(metodo="replica_exe", decimales_utm=2, decimales_grados=8, separador_decimal=",",
                         positivos_sur_oeste=False, ultimas={"a": "b"})
    assert config.guardar(op, p)
    assert config.cargar(p) == op


def test_config_no_escribible_no_falla(tmp_path):
    assert config.guardar(config.Opciones(), tmp_path / "no_existe" / "config.json") is False
