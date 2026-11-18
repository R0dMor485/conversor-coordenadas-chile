"""Ventana principal: pestañas, barra de estado, ajustes globales y geometría recordada."""
from __future__ import annotations

import dataclasses
import re
import tkinter as tk
from pathlib import Path
from tkinter import ttk

from .. import config
from ..core.constantes import PRECISION_METODO_M, Metodo
from . import tema
from .comun import ETIQUETA_METODO
from .componentes import BarraEstado
from .tema import T, u

TITULO = "Conversor de Coordenadas"
NOMBRES_PESTANAS = ("Calcular Coordenadas", "Conversión masiva", "Archivo Excel")
# Del config.json solo se restauran los Ajustes y la geometría de la ventana: pestaña, datums, formatos
# y demás selecciones vuelven a sus valores por defecto en cada arranque.
CLAVES_VENTANA = ("ventana", "ventana_escala", "ventana_max")
MS_TEMPORAL = 4000  # mensajes de copiado: vuelven a "Listo" tras ~4 s
LIMITES_DECIMALES = {"decimales_utm": (0, 4), "decimales_grados": (0, 10)}


class App:
    def __init__(self, raiz: tk.Misc, ruta_config: Path | None = None):
        self.raiz = raiz
        self.ruta_config = ruta_config
        self.op = config.cargar(ruta_config)
        self.op.ultimas = {k: v for k, v in self.op.ultimas.items() if k in CLAVES_VENTANA}
        tema.aplicar(raiz)
        raiz.title(TITULO)
        raiz.configure(background=tema.C.fondo)
        self._icono()
        self._geom_normal: str | None = None
        self._geometria_inicial()

        self.estado = BarraEstado(raiz)
        self.estado.pack(side="bottom", fill="x")
        self.v_estado = self.estado.v_derecha  # texto del método (derecha)

        self.nb = ttk.Notebook(raiz, style="App.TNotebook")
        self.nb.pack(side="top", fill="both", expand=True)
        from .tab_excel import TabExcel
        from .tab_individual import TabIndividual
        from .tab_masiva import TabMasiva

        self.tabs = [TabIndividual(self.nb, self), TabMasiva(self.nb, self), TabExcel(self.nb, self)]
        for t, nombre in zip(self.tabs, NOMBRES_PESTANAS):
            self.nb.add(t, text=nombre)
        raiz.bind("<Return>", self._enter)
        raiz.bind("<KP_Enter>", self._enter)
        raiz.bind("<Configure>", self._ventana_cambio, add="+")
        raiz.protocol("WM_DELETE_WINDOW", self.cerrar)
        self._actualizar_metodo()

    # ------------------------------------------------------------------ ventana
    def _icono(self) -> None:
        try:
            from . import imagenes as im

            fotos = [tk.PhotoImage(master=self.raiz, data=im.icono_app(n).base64(), format="png") for n in (48, 32, 16)]
            self.raiz.iconphoto(True, *fotos)  # también para el diálogo
            self._fotos_icono = fotos
        except Exception:  # noqa: BLE001 - el ícono es opcional
            pass

    def _geometria_inicial(self) -> None:
        r = self.raiz
        ax, ay, aw, ah = area_trabajo(r)
        barra_titulo = u(40)
        wmin, hmin = min(u(T.ventana_min_ancho), aw - u(16)), min(u(T.ventana_min_alto), ah - barra_titulo)
        r.minsize(wmin, hmin)
        w, h = min(u(T.ventana_ancho), aw - u(16)), min(u(T.ventana_alto), ah - barra_titulo)
        x, y = ax + (aw - w) // 2, ay + max(0, (ah - h - barra_titulo) // 2)
        guardada = self.op.ultimas.get("ventana")
        esc = self.op.ultimas.get("ventana_escala")
        m = re.fullmatch(r"(\d+)x(\d+)([+-]-?\d+)([+-]-?\d+)", guardada) if isinstance(guardada, str) else None
        if m:
            f = tema.escala() / esc if isinstance(esc, (int, float)) and esc > 0 else 1.0
            f = 1.0 if abs(f - 1.0) < 0.01 else f  # misma escala: sin reescalar
            gw, gh = round(int(m.group(1)) * f), round(int(m.group(2)) * f)
            gx, gy = int(m.group(3)), int(m.group(4))
            if punto_visible(r, gx + u(60), gy + u(12)):
                w, h, x, y = max(wmin, min(gw, aw)), max(hmin, min(gh, ah)), gx, gy
        r.geometry(f"{w}x{h}+{x}+{y}")
        self._geom_normal = f"{w}x{h}+{x}+{y}"
        if self.op.ultimas.get("ventana_max") is True:
            try:
                r.state("zoomed")
            except tk.TclError:
                pass

    def _ventana_cambio(self, e) -> None:
        if e.widget is self.raiz:
            try:
                if self.raiz.state() == "normal":
                    self._geom_normal = self.raiz.geometry()
            except tk.TclError:
                pass

    def _guardar_geometria(self) -> None:
        try:
            maximizada = self.raiz.state() == "zoomed"
        except tk.TclError:
            maximizada = False
        geo = self._geom_normal if maximizada else self.raiz.geometry()
        if geo and not geo.startswith("1x1"):
            self.op.ultimas["ventana"] = geo
            self.op.ultimas["ventana_escala"] = round(tema.escala(), 4)
        self.op.ultimas["ventana_max"] = maximizada

    # ------------------------------------------------------------------ opciones globales
    def guardar_opciones(self) -> None:
        ultimas = {k: v for k, v in self.op.ultimas.items() if k in CLAVES_VENTANA}
        config.guardar(dataclasses.replace(self.op, ultimas=ultimas), self.ruta_config)  # si falla, sigue sin error

    def aplicar_ajustes(self, **cambios) -> None:
        """Aplica y guarda ajustes globales (los mismos campos de ``config.Opciones``)."""
        for k, v in cambios.items():
            if k == "metodo":
                v = Metodo(v).value
            elif k in LIMITES_DECIMALES:
                lo, hi = LIMITES_DECIMALES[k]
                v = int(v)
                if not lo <= v <= hi:
                    raise ValueError(f"{k} fuera de rango")
            elif k == "separador_decimal" and v not in (".", ","):
                raise ValueError(k)
            elif k == "zona_salida" and str(v) not in ("auto", "18", "19"):
                raise ValueError(k)
            elif k == "positivos_sur_oeste":
                v = bool(v)
            elif k not in ("zona_salida", "separador_decimal"):
                raise KeyError(k)
            setattr(self.op, k, str(v) if k == "zona_salida" else v)
        self.guardar_opciones()
        self._actualizar_metodo()
        for t in self.tabs:
            t.refrescar()

    def _actualizar_metodo(self) -> None:
        self.v_estado.set(f"{ETIQUETA_METODO[self.op.metodo]} · Precisión declarada ±{PRECISION_METODO_M:.0f} m")

    def abrir_ajustes(self, esperar: bool = True):
        from .dialogo_ajustes import DialogoAjustes

        return DialogoAjustes(self, esperar=esperar)

    # ------------------------------------------------------------------ mensajes
    def mensaje(self, texto: str, tipo: str = "info", temporal: bool = False) -> None:
        self.estado.mostrar(texto, tipo, MS_TEMPORAL if temporal else None)

    def estado_temporal(self, texto: str, ms: int = MS_TEMPORAL, tipo: str = "ok") -> None:
        self.estado.mostrar(texto, tipo, ms)

    # ------------------------------------------------------------------ eventos
    def _enter(self, e=None):
        try:
            foco = self.raiz.focus_get()
        except (KeyError, tk.TclError):
            foco = None
        if isinstance(foco, ttk.Button):
            foco.invoke()
            return "break"
        t = self.tabs[self.nb.index(self.nb.select())]
        if hasattr(t, "al_enter"):
            return t.al_enter()

    def cerrar(self) -> None:
        for t in self.tabs:
            if hasattr(t, "al_cerrar"):
                t.al_cerrar()
        self._guardar_geometria()
        self.guardar_opciones()
        self.raiz.destroy()


# --------------------------------------------------------------------------- pantalla (Windows)
def area_trabajo(r: tk.Misc) -> tuple[int, int, int, int]:
    """Área de trabajo del monitor principal (sin la barra de tareas): x, y, ancho, alto."""
    try:
        import ctypes
        from ctypes import wintypes

        rect = wintypes.RECT()
        if ctypes.windll.user32.SystemParametersInfoW(0x30, 0, ctypes.byref(rect), 0):  # SPI_GETWORKAREA
            return rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top
    except Exception:  # noqa: BLE001
        pass
    return 0, 0, r.winfo_screenwidth(), r.winfo_screenheight() - 48


def punto_visible(r: tk.Misc, x: int, y: int) -> bool:
    """¿El punto está en algún monitor conectado? (para no abrir la ventana fuera de pantalla)."""
    try:
        import ctypes
        from ctypes import wintypes

        return bool(ctypes.windll.user32.MonitorFromPoint(wintypes.POINT(x, y), 0))  # MONITOR_DEFAULTTONULL
    except Exception:  # noqa: BLE001
        return 0 <= x < r.winfo_screenwidth() and 0 <= y < r.winfo_screenheight()


def preparar_dpi() -> None:
    """Escalado de pantalla nítido. Debe llamarse ANTES de crear la ventana raíz.

    Se declara "system DPI aware": Tk 8.6 no reajusta la interfaz al pasar a un monitor con otra
    escala (no atiende WM_DPICHANGED), así que el modo por monitor dejaría la ventana del tamaño
    equivocado en el segundo monitor; con el modo de sistema Windows la reescala allí.
    """
    try:
        import ctypes

        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)  # PROCESS_SYSTEM_DPI_AWARE
        except Exception:  # noqa: BLE001 - Windows antiguos
            ctypes.windll.user32.SetProcessDPIAware()
    except Exception:  # noqa: BLE001 - no Windows
        pass


def identidad_barra_tareas() -> None:
    """Identidad propia para la barra de tareas: así Windows agrupa la ventana con su propio ícono y no con
    el de Python (relevante al ejecutar desde el código con pythonw)."""
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Coordenadas.ConversorDeCoordenadas")
    except Exception:  # noqa: BLE001 - no Windows o versión antigua
        pass


def ajustar_tk_scaling(raiz: tk.Misc) -> None:
    """``tk scaling`` = ppp del sistema / 72 (puntos tipográficos a píxeles)."""
    try:
        import ctypes

        ppp = ctypes.windll.user32.GetDpiForSystem()
    except Exception:  # noqa: BLE001
        ppp = raiz.winfo_fpixels("1i")
    if ppp and ppp > 0:
        raiz.tk.call("tk", "scaling", ppp / 72.0)


_dpi_nitido = preparar_dpi  # nombre anterior


def main() -> None:
    preparar_dpi()
    identidad_barra_tareas()
    raiz = tk.Tk()
    ajustar_tk_scaling(raiz)
    App(raiz)
    raiz.mainloop()
