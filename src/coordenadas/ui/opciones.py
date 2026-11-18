"""Barra "Opciones" común a las pestañas."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable

from ..config import Opciones
from ..core.constantes import Metodo

ETIQUETAS_METODO = {m.etiqueta: m.value for m in Metodo}


class BarraOpciones(ttk.LabelFrame):
    def __init__(self, padre, op: Opciones, al_cambiar: Callable[[], None]):
        super().__init__(padre, text="Opciones", padding=(8, 4))
        self.op = op
        self.al_cambiar = al_cambiar
        self.v_metodo = tk.StringVar(value=Metodo(op.metodo).etiqueta)
        self.v_dec_utm = tk.StringVar(value=str(op.decimales_utm))
        self.v_dec_gr = tk.StringVar(value=str(op.decimales_grados))
        self.v_sep = tk.StringVar(value=op.separador_decimal)
        self.v_pos = tk.BooleanVar(value=op.positivos_sur_oeste)

        ttk.Label(self, text="Método:").grid(row=0, column=0, sticky="w")
        cb = ttk.Combobox(self, textvariable=self.v_metodo, values=list(ETIQUETAS_METODO), state="readonly", width=24)
        cb.grid(row=0, column=1, sticky="w", padx=(4, 16))
        cb.bind("<<ComboboxSelected>>", lambda e: self._leer())

        ttk.Label(self, text="Decimales UTM:").grid(row=0, column=2, sticky="w")
        s1 = ttk.Spinbox(self, from_=0, to=4, width=3, textvariable=self.v_dec_utm, command=self._leer, state="readonly")
        s1.grid(row=0, column=3, sticky="w", padx=(4, 16))
        ttk.Label(self, text="Decimales de grados:").grid(row=0, column=4, sticky="w")
        s2 = ttk.Spinbox(self, from_=0, to=10, width=3, textvariable=self.v_dec_gr, command=self._leer, state="readonly")
        s2.grid(row=0, column=5, sticky="w", padx=(4, 0))

        ttk.Label(self, text="Separador decimal al copiar y exportar:").grid(row=1, column=0, columnspan=2, sticky="w", pady=(4, 0))
        fr = ttk.Frame(self)
        fr.grid(row=1, column=2, columnspan=2, sticky="w", pady=(4, 0))
        ttk.Radiobutton(fr, text="Punto", value=".", variable=self.v_sep, command=self._leer).pack(side="left")
        ttk.Radiobutton(fr, text="Coma", value=",", variable=self.v_sep, command=self._leer).pack(side="left", padx=(6, 0))
        ttk.Checkbutton(
            self, text="Interpretar valores positivos como S y O", variable=self.v_pos, command=self._leer
        ).grid(row=1, column=4, columnspan=2, sticky="w", pady=(4, 0))

    def _leer(self) -> None:
        self.op.metodo = ETIQUETAS_METODO[self.v_metodo.get()]
        self.op.decimales_utm = int(self.v_dec_utm.get())
        self.op.decimales_grados = int(self.v_dec_gr.get())
        self.op.separador_decimal = self.v_sep.get()
        self.op.positivos_sur_oeste = bool(self.v_pos.get())
        self.al_cambiar()
