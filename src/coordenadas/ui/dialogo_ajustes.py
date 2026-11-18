"""Diálogo modal "Ajustes": método, zona de salida, formato de números y entrada.

Los cambios se aplican y guardan en config.json solo con Aceptar (Enter); Cancelar o Esc los
descarta. Los ajustes son globales: valen para las tres pestañas, el copiado y la exportación.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from ..core.constantes import Metodo
from . import componentes as K
from .app import LIMITES_DECIMALES
from .comun import AYUDA_METODO, ETIQUETA_METODO
from .tema import C, T, u

ZONAS = {"auto": "Automática", "18": "Forzar 18", "19": "Forzar 19"}


class DialogoAjustes(tk.Toplevel):
    def __init__(self, app, esperar: bool = True):
        super().__init__(app.raiz)
        self.withdraw()
        self.app = app
        self.aceptado = False
        op = app.op
        self.title("Ajustes")
        self.configure(background=C.tarjeta)
        self.resizable(False, False)
        self.transient(app.raiz)

        self.v_metodo = tk.StringVar(value=op.metodo)
        self.v_zona = tk.StringVar(value=ZONAS.get(op.zona_salida, ZONAS["auto"]))
        self.v_dec_utm = tk.StringVar(value=str(op.decimales_utm))
        self.v_dec_gr = tk.StringVar(value=str(op.decimales_grados))
        self.v_sep = tk.StringVar(value=op.separador_decimal)
        self.v_pos = tk.BooleanVar(value=op.positivos_sur_oeste)

        ph, sep = u(24), u(T.sep)
        cuerpo = ttk.Frame(self, style="Blanco.TFrame", padding=(ph, u(22), ph, u(16)))
        cuerpo.pack(side="top", fill="both", expand=True)
        cuerpo.columnconfigure(0, weight=1)
        fila = [0]

        def seccion(titulo: str, primera: bool = False) -> None:
            if not primera:
                K.divisor(cuerpo).grid(row=fila[0], column=0, columnspan=2, sticky="ew", pady=(u(14), u(16)))
                fila[0] += 1
            ttk.Label(cuerpo, text=titulo, style="Seccion.TLabel").grid(row=fila[0], column=0, columnspan=2, sticky="w",
                                                                         pady=(0, u(10)))
            fila[0] += 1

        # 1. Método
        seccion("Método de transformación", primera=True)
        for m in (Metodo.TABLA_IGM, Metodo.REPLICA_EXE):
            rb = ttk.Radiobutton(cuerpo, text=ETIQUETA_METODO[m.value], value=m.value, variable=self.v_metodo,
                                 style="Opcion.TRadiobutton")
            rb.grid(row=fila[0], column=0, columnspan=2, sticky="w")
            ttk.Label(cuerpo, text=AYUDA_METODO[m.value], style="Ayuda.TLabel", wraplength=u(T.dialogo_ancho - 90),
                      justify="left").grid(row=fila[0] + 1, column=0, columnspan=2, sticky="w",
                                           padx=(u(T.indicador) + u(10), 0), pady=(0, u(6)))
            fila[0] += 2

        # 2. Zona de salida
        seccion("Huso de salida")
        ttk.Label(cuerpo, text="Automática usa la longitud ya transformada.", style="Ayuda.TLabel", wraplength=u(260),
                  justify="left").grid(row=fila[0], column=0, sticky="w")
        self.cb_zona = K.combo(cuerpo, self.v_zona, list(ZONAS.values()), width=14)
        self.cb_zona.grid(row=fila[0], column=1, sticky="e")
        fila[0] += 1

        # 3. Formato de números
        seccion("Formato de números")
        self.campos_dec = {}
        for clave, texto, var in (("decimales_utm", "Decimales en U.T.M.", self.v_dec_utm),
                                  ("decimales_grados", "Decimales en grados decimales", self.v_dec_gr)):
            etiqueta = ttk.Label(cuerpo, text=texto, style="Tarjeta.TLabel")
            etiqueta.grid(row=fila[0], column=0, sticky="nw", pady=(u(6), u(10)))
            cc = K.CampoConError(cuerpo, None)
            cc.l_etiqueta, cc.estilo_etiqueta = etiqueta, ("Tarjeta.TLabel", "TarjetaError.TLabel")
            e = cc.agregar(K.entrada(cc.cuerpo, var, mono=True, width=4, justify="right"), var)
            e.grid(row=0, column=0, sticky="e")
            cc.l_error.configure(wraplength=u(260))
            cc.cuerpo.unbind("<Configure>")
            cc.grid(row=fila[0], column=1, sticky="e", pady=(0, u(10)))
            self.campos_dec[clave] = (cc, e, var)
            fila[0] += 1
        ttk.Label(cuerpo, text="Separador decimal", style="Tarjeta.TLabel").grid(row=fila[0], column=0, sticky="w")
        self.sel_sep = K.SelectorSegmentado(cuerpo, self.v_sep, [(".", "Punto"), (",", "Coma")])
        self.sel_sep.grid(row=fila[0], column=1, sticky="e", ipadx=u(30))
        fila[0] += 1

        # 4. Entrada
        seccion("Entrada")
        ttk.Checkbutton(cuerpo, text="Interpretar valores positivos como S y O", variable=self.v_pos,
                        style="Casilla.TCheckbutton").grid(row=fila[0], column=0, columnspan=2, sticky="w")
        fila[0] += 1

        # Pie
        K.divisor(self, C.divisor).pack(side="top", fill="x")
        pie = ttk.Frame(self, style="Pie.TFrame", padding=(ph, u(16)))
        pie.pack(side="bottom", fill="x")
        self.b_cancelar = K.boton(pie, "Cancelar", self.cancelar, "Secundario.TButton")
        self.b_aceptar = K.boton(pie, "Aceptar", self.aceptar, "Principal.TButton")
        self.b_aceptar.pack(side="right")
        self.b_cancelar.pack(side="right", padx=(0, u(T.sep_campos)))
        self.b_cancelar.lower(self.b_aceptar)

        self.bind("<Escape>", lambda e: self.cancelar())
        self.bind("<Return>", self._enter)
        self.bind("<KP_Enter>", self._enter)
        self.protocol("WM_DELETE_WINDOW", self.cancelar)

        self._centrar()
        try:
            if app.raiz.winfo_viewable():
                self.deiconify()
                self.grab_set()
            self.focus_set()
        except tk.TclError:
            pass
        if esperar:
            self.wait_window()

    def _centrar(self) -> None:
        w, h = u(T.dialogo_ancho), u(T.dialogo_alto)
        self.update_idletasks()
        h = max(h, self.winfo_reqheight())
        r = self.app.raiz
        x = r.winfo_rootx() + (r.winfo_width() - w) // 2
        y = r.winfo_rooty() + (r.winfo_height() - h) // 2 - u(20)
        self.geometry(f"{w}x{h}+{max(0, x)}+{max(0, y)}")

    def _enter(self, e=None):
        foco = self.focus_get()
        if foco is self.b_cancelar:
            self.cancelar()
        else:
            self.aceptar()
        return "break"

    def _validar(self) -> dict | None:
        valores = {}
        ok = True
        for clave, (cc, e, var) in self.campos_dec.items():
            lo, hi = LIMITES_DECIMALES[clave]
            t = var.get().strip()
            if not t:
                cc.mostrar_error("Ingresa un valor.")
                ok = False
            elif not t.isdigit():
                cc.mostrar_error(f"Usa un entero entre {lo} y {hi}.")
                ok = False
            elif not lo <= int(t) <= hi:
                cc.mostrar_error(f"Debe estar entre {lo} y {hi}.")
                ok = False
            else:
                valores[clave] = int(t)
        return valores if ok else None

    def aceptar(self) -> bool:
        dec = self._validar()
        if dec is None:
            return False
        zona = {v: k for k, v in ZONAS.items()}[self.v_zona.get()]
        self.app.aplicar_ajustes(metodo=self.v_metodo.get(), zona_salida=zona, separador_decimal=self.v_sep.get(),
                                 positivos_sur_oeste=bool(self.v_pos.get()), **dec)
        self.aceptado = True
        self._cerrar()
        return True

    def cancelar(self) -> None:
        self._cerrar()

    def _cerrar(self) -> None:
        try:
            self.grab_release()
        except tk.TclError:
            pass
        self.destroy()
