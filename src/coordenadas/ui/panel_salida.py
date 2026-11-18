"""Controles de salida comunes a las tres pestañas: datum y formato de salida.

La zona de salida (Automática / Forzar 18 / Forzar 19) es un ajuste global (diálogo Ajustes).
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable

from . import componentes as K
from ..core.constantes import ORDEN_DATUMS
from .comun import CLAVE_POR_ETIQUETA, ETIQUETA_POR_CLAVE, FORMATOS_SALIDA, combo_datum
from .tema import T, u


class PanelSalida(ttk.Frame):
    def __init__(self, padre, app, prefijo: str, al_cambiar: Callable[[], None], horizontal: bool = False,
                 datum_defecto: str = "SIRGAS", etiqueta_datum: str = "Datum", etiqueta_formato: str = "Formato",
                 con_formato: bool = True):
        super().__init__(padre, style="Blanco.TFrame")
        self.app = app
        self.ultimas = app.op.ultimas
        self.prefijo = prefijo
        self.al_cambiar = al_cambiar
        u_ = self.ultimas
        self.v_datum = tk.StringVar(value=ETIQUETA_POR_CLAVE.get(u_.get(f"{prefijo}datum_salida"),
                                                                  ETIQUETA_POR_CLAVE[datum_defecto]))
        fmt = u_.get(f"{prefijo}formato_salida")
        self.v_formato = tk.StringVar(value=fmt if fmt in dict(FORMATOS_SALIDA) else "utm")

        self.c_datum = K.CampoConError(self, etiqueta_datum)
        self.cb_datum = self.c_datum.agregar(combo_datum(self.c_datum.cuerpo, self.v_datum))
        self.cb_datum.grid(row=0, column=0, sticky="ew")
        self.cb_datum.bind("<<ComboboxSelected>>", lambda e: self._cambio(), add="+")
        self.con_formato = con_formato
        self.excluido: str | None = None
        self.c_formato = self.selector = None
        if con_formato:
            self.c_formato = K.CampoConError(self, etiqueta_formato)
            self.selector = K.SelectorSegmentado(self.c_formato.cuerpo, self.v_formato, FORMATOS_SALIDA, self._cambio)
            self.selector.grid(row=0, column=0, sticky="ew")
        else:
            self.v_formato.set("utm")  # pestañas de solo UTM
        if horizontal and con_formato:
            self.columnconfigure(0, weight=1, uniform="ps")
            self.columnconfigure(1, weight=1, uniform="ps")
            self.c_datum.grid(row=0, column=0, sticky="new", padx=(0, u(T.sep_campos)))
            self.c_formato.grid(row=0, column=1, sticky="new")
        else:
            self.columnconfigure(0, weight=1)
            self.c_datum.grid(row=0, column=0, sticky="ew", pady=(0, u(T.sep) if con_formato else 0))
            if con_formato:
                self.c_formato.grid(row=1, column=0, sticky="ew")

    def aplicar(self, datum: str | None = None, formato: str | None = None) -> None:
        """Fija datum y/o formato sin disparar el callback (cambios automáticos de la pestaña)."""
        if datum is not None:
            self.v_datum.set(ETIQUETA_POR_CLAVE[datum])
        if formato is not None and self.con_formato:
            self.v_formato.set(formato)

    def excluir(self, clave: str | None) -> bool:
        """Quita ``clave`` de las opciones de datum de salida (o restablece la lista con ``None``).
        Si el datum elegido era ese, pasa al primero disponible (WGS84, o PSAD56 si se excluye WGS84).
        Devuelve True si cambió el datum seleccionado."""
        self.excluido = clave
        claves = [k for k in ORDEN_DATUMS if k != clave]
        self.cb_datum.configure(values=[ETIQUETA_POR_CLAVE[k] for k in claves])
        if self.datum == clave:
            self.v_datum.set(ETIQUETA_POR_CLAVE[claves[0]])
            self.ultimas[f"{self.prefijo}datum_salida"] = self.datum
            return True
        return False

    def _cambio(self) -> None:
        self.ultimas[f"{self.prefijo}datum_salida"] = self.datum
        self.ultimas[f"{self.prefijo}formato_salida"] = self.formato
        self.al_cambiar()

    @property
    def datum(self) -> str:
        return CLAVE_POR_ETIQUETA[self.v_datum.get()]

    @property
    def formato(self) -> str:
        return self.v_formato.get()

    @property
    def zona(self) -> int | None:
        z = self.app.op.zona_salida
        return None if z == "auto" else int(z)
