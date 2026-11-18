"""Pestaña 2: "Conversión masiva" (solo UTM; lista editable, sin archivos).

Cada fila trae Norte, Este, Huso y Datum de entrada (el datum se lee de la propia fila: no hay selector);
solo el datum de salida se elige. Salida: Norte, Este, Huso y Estado.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from ..core.formato import texto_tabulado
from ..core.servicio import ResultadoFila, convertir_fila_utm, interpretar_pegado_utm, textos_fila
from . import componentes as K
from . import tema
from .comun import NOMBRE_CORTO, copiar
from .panel_salida import PanelSalida
from .tema import C, T, u

FILAS_INICIALES = 30
COLUMNAS = ("n", "norte", "este", "huso", "datum", "r1", "r2", "r3", "estado")
EDITABLES = ("norte", "este", "huso", "datum")
ANCHOS = {"n": 32, "norte": 108, "este": 96, "huso": 48, "datum": 84, "r1": 104, "r2": 100, "r3": 48, "estado": 120}
NUMERICAS = ("r1", "r2", "norte", "este")
CENTRADAS = ("n", "huso", "r3")
SIMBOLO = {"ok": "✓", "aviso": "⚠", "error": "✕"}
TEXTO_AYUDA = ("Pega tus coordenadas desde Excel con Ctrl+V.\n"
               "Columnas: Norte, Este, Huso y Datum (WGS84 o 1984, PSAD56 o 1956, SAD69 o 1969).")
TEXTO_TECLAS = "Doble clic o F2 edita · Enter baja · Tab avanza · Supr borra · Ctrl+V pega · Ctrl+C copia resultados"
TEXTO_SALIDA = "Cada fila trae su datum de entrada; aquí eliges solo el de salida."


def _plural(n: int, singular: str, plural: str) -> str:
    return f"{n} {singular if n == 1 else plural}"


class Fila:
    __slots__ = ("norte", "este", "huso", "datum", "res")

    def __init__(self):
        self.norte = self.este = self.huso = self.datum = ""
        self.res: ResultadoFila | None = None

    def vacia(self) -> bool:
        return not (self.norte.strip() or self.este.strip() or self.huso.strip())


class TabMasiva(ttk.Frame):
    def __init__(self, padre, app):
        super().__init__(padre, style="TFrame")
        self.app = app
        self.filas: list[Fila] = []
        self.col_actual = "norte"
        self.editor = None
        mh, mv, sep, sc = u(T.margen_h), u(T.margen_v), u(T.sep), u(T.sep_campos)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        K.Encabezado(self, "Conversión masiva", "Pega varias coordenadas y conviértelas a la vez.") \
            .grid(row=0, column=0, sticky="ew", padx=mh, pady=(mv, u(12)))
        self.area = K.AreaDesplazable(self)
        self.area.grid(row=1, column=0, sticky="nsew")
        cont = self.area.interior
        cont.columnconfigure(0, weight=1)
        cont.rowconfigure(1, weight=1)

        # ------------------------------------------------------------- datum de salida
        tc = K.Tarjeta(cont)
        tc.grid(row=0, column=0, sticky="ew", padx=mh)
        cb = tc.cuerpo
        cb.columnconfigure(0, weight=1, uniform="c2")
        cb.columnconfigure(1, weight=2, uniform="c2")
        self.panel = PanelSalida(cb, app, "t2_", self._cambio_salida, con_formato=False,
                                 etiqueta_datum="Datum de salida")
        self.panel.grid(row=0, column=0, sticky="new", padx=(0, sc))
        ttk.Label(cb, text=TEXTO_SALIDA, style="Ayuda.TLabel", justify="left", wraplength=u(470)) \
            .grid(row=0, column=1, sticky="sw", pady=(0, u(8)))

        # ------------------------------------------------------------- cuadrícula
        tg = K.Tarjeta(cont)
        tg.grid(row=1, column=0, sticky="nsew", padx=mh, pady=(sep, 0))
        cg = tg.cuerpo
        cg.rowconfigure(1, weight=1)
        barra = ttk.Frame(cg, style="Blanco.TFrame")
        barra.grid(row=0, column=0, sticky="ew", pady=(0, u(10)))
        barra.columnconfigure(1, weight=1)
        self.v_enc = tk.BooleanVar(value=bool(app.op.ultimas.get("t2_encabezados", True)))
        ttk.Checkbutton(barra, text="Copiar con encabezados", variable=self.v_enc, command=self._guardar_enc,
                        style="Casilla.TCheckbutton").grid(row=0, column=0, sticky="w")
        self.b_agregar = K.boton(barra, "Agregar fila", self.agregar_fila, "Tarjeta.TButton")
        self.b_pegar = K.boton(barra, "Pegar", self.pegar, "Tarjeta.TButton")
        self.l_resumen = ttk.Label(barra, text="", style="Ayuda.TLabel")
        self.l_resumen.grid(row=0, column=1, sticky="e", padx=(sc, 0))
        self.b_pegar.grid(row=0, column=2, padx=(sc, 0))
        self.b_agregar.grid(row=0, column=3, padx=(sc, 0))

        marco = ttk.Frame(cg, style="Blanco.TFrame")
        marco.grid(row=1, column=0, sticky="nsew")
        self.tree = ttk.Treeview(marco, columns=COLUMNAS, show="headings", selectmode="extended", height=4,
                                 style="Cuadricula.Treeview")
        sy = ttk.Scrollbar(marco, orient="vertical", command=self.tree.yview)
        sx = ttk.Scrollbar(marco, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=sy.set, xscrollcommand=sx.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        sy.grid(row=0, column=1, sticky="ns")
        sx.grid(row=1, column=0, sticky="ew")
        marco.rowconfigure(0, weight=1)
        marco.columnconfigure(0, weight=1)
        for col in COLUMNAS:
            self.tree.column(col, width=u(ANCHOS[col]), minwidth=u(ANCHOS[col] // 2 if col == "estado" else ANCHOS[col]),
                             stretch=(col == "estado"), anchor=self._ancho_columna(col))
        self.tree.tag_configure("alterna", background=C.fila_alterna)
        self.tree.tag_configure("aviso", background=C.fondo_aviso, foreground=C.aviso)
        self.tree.tag_configure("error", background=C.fondo_error, foreground=C.error)
        self.l_vacia = ttk.Label(self.tree, text=TEXTO_AYUDA, style="CuadriculaVacia.TLabel", anchor="center",
                                 justify="center")
        self.tree.bind("<Configure>", lambda e: self._ayuda_vacia(), add="+")
        self.l_vacia.bind("<Button-1>", self._clic_ayuda)
        self.l_vacia.bind("<Double-1>", self._clic_ayuda)

        pie = ttk.Frame(cg, style="Blanco.TFrame")
        pie.grid(row=2, column=0, sticky="ew", pady=(u(10), 0))
        pie.columnconfigure(0, weight=1)
        self.l_detalle = ttk.Label(pie, text=TEXTO_TECLAS, style="Ayuda.TLabel")
        self.l_detalle.grid(row=0, column=0, sticky="w")

        # ------------------------------------------------------------- fila inferior
        fa = ttk.Frame(self, style="TFrame")
        fa.grid(row=2, column=0, sticky="ew", padx=mh, pady=(u(12), u(16)))
        self.b_ajustes = K.boton(fa, "Ajustes", self.app.abrir_ajustes, "Discreto.TButton", icono="ajustes")
        self.b_ajustes.pack(side="left")
        self.b_convertir = K.boton(fa, "Convertir", self.convertir_todo, "Principal.TButton")
        self.b_copiar = K.boton(fa, "Copiar resultados", self.copiar_resultados, "Secundario.TButton", icono="copiar")
        self.b_limpiar = K.boton(fa, "Limpiar", self.limpiar, "Secundario.TButton")
        self.b_convertir.pack(side="right")
        self.b_copiar.pack(side="right", padx=(0, sc))
        self.b_limpiar.pack(side="right", padx=(0, sc))
        self.b_limpiar.lower(self.b_copiar)  # tabulación: Ajustes, Limpiar, Copiar resultados, Convertir
        self.b_copiar.lower(self.b_convertir)

        self.tree.bind("<Double-1>", self._doble_clic)
        self.tree.bind("<Button-1>", self._clic, add="+")
        self.tree.bind("<F2>", lambda e: self._editar_actual())
        self.tree.bind("<Return>", lambda e: (self._editar_actual(), "break")[1])
        self.tree.bind("<Delete>", lambda e: self.borrar_seleccion())
        self.tree.bind("<Control-v>", lambda e: (self.pegar(), "break")[1])
        self.tree.bind("<Control-V>", lambda e: (self.pegar(), "break")[1])
        self.tree.bind("<Control-c>", lambda e: (self.copiar_resultados(), "break")[1])
        self.tree.bind("<Control-C>", lambda e: (self.copiar_resultados(), "break")[1])
        self.tree.bind("<Key>", self._tecla)
        self.tree.bind("<<TreeviewSelect>>", lambda e: self._detalle())

        for _ in range(FILAS_INICIALES):
            self._nueva_fila()
        self._encabezados()
        self.tree.selection_set("0")
        self.tree.focus("0")
        self._ayuda_vacia()

    @staticmethod
    def _ancho_columna(col: str) -> str:
        return "center" if col in CENTRADAS else ("e" if col in NUMERICAS else "w")

    # ------------------------------------------------------------------ datos
    @staticmethod
    def _tags(i: int, f: Fila) -> tuple:
        nivel = None if f.res is None else f.res.nivel
        if nivel in ("aviso", "error"):
            return (nivel,)
        return ("alterna",) if i % 2 else ()

    def _nueva_fila(self) -> None:
        self.filas.append(Fila())
        i = len(self.filas) - 1
        self.tree.insert("", "end", iid=str(i), values=self._valores(i), tags=self._tags(i, self.filas[i]))

    def agregar_fila(self) -> None:
        self._nueva_fila()
        iid = str(len(self.filas) - 1)
        self.tree.see(iid)
        self.tree.selection_set(iid)
        self.tree.focus(iid)

    def _valores(self, i: int) -> tuple:
        f = self.filas[i]
        op = self.app.op
        r = textos_fila(f.res, "utm", op.decimales_utm, op.decimales_grados, op.separador_decimal)
        estado = "" if f.res is None else f"{SIMBOLO[f.res.nivel]} {f.res.estado}"
        return (i + 1, f.norte, f.este, f.huso, f.datum, *r, estado)

    def _pintar_fila(self, i: int) -> None:
        self.tree.item(str(i), values=self._valores(i), tags=self._tags(i, self.filas[i]))

    def _convertir_fila(self, i: int) -> None:
        f = self.filas[i]
        op = self.app.op
        if f.vacia():
            f.res = None
        else:
            f.res = convertir_fila_utm(f.norte, f.este, f.huso, f.datum, self.panel.datum, op.metodo_enum,
                                       self.panel.zona)
        self._pintar_fila(i)

    def convertir_todo(self) -> None:
        self._cerrar_editor(guardar=True)
        for i in range(len(self.filas)):
            self._convertir_fila(i)
        self._resumen()
        niveles = [f.res.nivel for f in self.filas if f.res is not None]
        if not niveles:
            self.app.mensaje("No hay coordenadas para convertir", "aviso", temporal=True)
        elif niveles.count("error"):
            self.app.mensaje(f"Conversión lista · {niveles.count('error')} con error (ver columna Estado)", "aviso")
        else:
            self.app.mensaje("Conversión lista", "ok")

    def _resumen(self) -> None:
        n = [f.res.nivel for f in self.filas if f.res is not None]
        self._ayuda_vacia()
        if not n:
            self.l_resumen.configure(text="")
            return
        self.l_resumen.configure(
            text=" · ".join([_plural(len(n), "fila", "filas"), f"{n.count('ok')} OK",
                             _plural(n.count("aviso"), "aviso", "avisos"), _plural(n.count("error"), "error", "errores")])
        )

    def _detalle(self) -> None:
        foco = self.tree.focus()
        f = self.filas[int(foco)] if foco else None
        if f is None or f.res is None:
            self.l_detalle.configure(text=TEXTO_TECLAS)  # sin fila con resultado: recordatorio de teclas
            return
        self.l_detalle.configure(text=f"Fila {int(foco) + 1}: {f.res.estado}")

    def _nombres_salida(self) -> list[str]:
        d = NOMBRE_CORTO[self.panel.datum]
        return [f"Norte {d}", f"Este {d}", "Huso"]

    def _encabezados(self) -> None:
        r1, r2, r3 = self._nombres_salida()
        for c, t in zip(COLUMNAS, ("N°", "Norte", "Este", "Huso", "Datum", r1, r2, r3, "Estado")):
            self.tree.heading(c, text=t, anchor=self._ancho_columna(c))

    # ------------------------------------------------------------------ texto de ayuda con la cuadrícula vacía
    def _ayuda_vacia(self) -> None:
        vacia = all(f.vacia() for f in self.filas) and self.editor is None
        if not vacia:
            self.l_vacia.place_forget()
            return
        caja = self.tree.bbox("0")
        y0 = caja[1] if caja else u(30)
        self.l_vacia.place(x=1, y=y0, relwidth=1.0, width=-2, relheight=1.0, height=-(y0 + 1))

    def _clic_ayuda(self, e) -> None:
        """Un clic sobre el texto de ayuda equivale a un clic en la primera fila."""
        self.tree.focus_set()
        self.tree.selection_set("0")
        self.tree.focus("0")
        self.editar(0, self.col_actual)

    # ------------------------------------------------------------------ eventos de opciones
    def _cambio_salida(self) -> None:
        self.app.guardar_opciones()
        self._encabezados()
        self.convertir_todo()

    def _guardar_enc(self) -> None:
        self.app.op.ultimas["t2_encabezados"] = bool(self.v_enc.get())
        self.app.guardar_opciones()

    def refrescar(self) -> None:
        if any(f.res is not None for f in self.filas):
            self.convertir_todo()

    def al_enter(self):
        return None  # Enter se usa para editar celdas

    # ------------------------------------------------------------------ edición
    def _clic(self, e) -> None:
        col = self.tree.identify_column(e.x)
        try:
            nombre = COLUMNAS[int(col[1:]) - 1]
        except (ValueError, IndexError):
            return
        if nombre in EDITABLES:
            self.col_actual = nombre

    def _doble_clic(self, e):
        item = self.tree.identify_row(e.y)
        self._clic(e)
        if item:
            self.editar(int(item), self.col_actual)
        return "break"

    def _editar_actual(self) -> None:
        item = self.tree.focus()
        if item:
            self.editar(int(item), self.col_actual)

    def _tecla(self, e):
        if e.char and e.char.isprintable() and not (e.state & 0x4) and self.tree.focus():
            self.editar(int(self.tree.focus()), self.col_actual, inicial=e.char)
            return "break"
        return None

    def editar(self, i: int, col: str, inicial: str | None = None) -> None:
        self._cerrar_editor(guardar=True)
        iid = str(i)
        self.tree.see(iid)
        self.tree.update_idletasks()
        bbox = self.tree.bbox(iid, f"#{COLUMNAS.index(col) + 1}")
        if not bbox:
            return
        x, y, w, h = bbox
        f = self.filas[i]
        var = tk.StringVar(value=getattr(f, col) if inicial is None else inicial)
        ed = ttk.Entry(self.tree, textvariable=var, style="Celda.TEntry", font=tema.fuente("cuadricula"))
        ed.icursor("end")
        if inicial is None:
            ed.select_range(0, "end")
        ed.place(x=x, y=y, width=w, height=h)
        ed.focus_set()
        self.editor = (ed, var, i, col)
        self.l_vacia.place_forget()
        ed.bind("<Return>", lambda e: (self._mover(1, 0), "break")[1])
        ed.bind("<KP_Enter>", lambda e: (self._mover(1, 0), "break")[1])
        ed.bind("<Tab>", lambda e: (self._mover(0, 1), "break")[1])
        ed.bind("<Shift-Tab>", lambda e: (self._mover(0, -1), "break")[1])
        ed.bind("<Escape>", lambda e: (self._cerrar_editor(guardar=False), self.tree.focus_set(), "break")[2])
        ed.bind("<Up>", lambda e: (self._mover(-1, 0), "break")[1])
        ed.bind("<Down>", lambda e: (self._mover(1, 0), "break")[1])
        ed.bind("<FocusOut>", lambda e: self._cerrar_editor(guardar=True))
        ed.bind("<Control-v>", self._pegar_en_editor)
        ed.bind("<Control-V>", self._pegar_en_editor)

    def _pegar_en_editor(self, e):
        try:
            texto = self.clipboard_get()
        except tk.TclError:
            return "break"
        if "\n" in texto.strip() or "\t" in texto:
            i = self.editor[2]
            self._cerrar_editor(guardar=False)
            self.pegar(texto, desde=i)
            return "break"
        return None  # pegado normal dentro de la celda

    def _cerrar_editor(self, guardar: bool) -> None:
        if not self.editor:
            return
        ed, var, i, col = self.editor
        self.editor = None
        if guardar:
            setattr(self.filas[i], col, var.get().strip())
            self._convertir_fila(i)
            self._resumen()
            self._detalle()
        ed.destroy()
        self._ayuda_vacia()

    def _mover(self, dfila: int, dcol: int) -> None:
        _, _, i, col = self.editor
        self._cerrar_editor(guardar=True)
        k = EDITABLES.index(col) + dcol
        if k >= len(EDITABLES):
            k, dfila = 0, 1
        elif k < 0:
            k, dfila = len(EDITABLES) - 1, -1
        i2 = i + dfila
        if i2 >= len(self.filas):
            self._nueva_fila()
        i2 = max(0, i2)
        self.col_actual = EDITABLES[k]
        self.tree.selection_set(str(i2))
        self.tree.focus(str(i2))
        if dcol:
            self.editar(i2, self.col_actual)
        else:
            self.tree.see(str(i2))
            self.tree.focus_set()

    def borrar_seleccion(self) -> None:
        for iid in self.tree.selection():
            i = int(iid)
            f = self.filas[i]
            f.norte = f.este = f.huso = f.datum = ""
            self._convertir_fila(i)
        self._resumen()

    # ------------------------------------------------------------------ portapapeles
    def pegar(self, texto: str | None = None, desde: int | None = None) -> int:
        """Pega filas (Norte, Este, Huso, Datum) desde el portapapeles (o ``texto``) a partir de la fila
        seleccionada."""
        self._cerrar_editor(guardar=True)
        if texto is None:
            try:
                texto = self.clipboard_get()
            except tk.TclError:
                self.app.estado_temporal("El portapapeles no contiene coordenadas", tipo="aviso")
                return 0
        filas = interpretar_pegado_utm(texto)
        if not filas:
            self.app.estado_temporal("El portapapeles no contiene coordenadas", tipo="aviso")
            return 0
        if desde is None:
            foco = self.tree.focus()
            desde = int(foco) if foco else 0
        while len(self.filas) < desde + len(filas):
            self._nueva_fila()
        for k, p in enumerate(filas):
            f = self.filas[desde + k]
            f.norte, f.este, f.huso, f.datum = p.norte, p.este, p.huso, p.datum
            self._convertir_fila(desde + k)
        self._resumen()
        self.tree.see(str(desde + len(filas) - 1))
        self.tree.see(str(desde))
        self.app.estado_temporal("1 fila pegada" if len(filas) == 1 else f"{len(filas)} filas pegadas")
        return len(filas)

    def texto_resultados(self, encabezados: bool) -> str:
        sel = sorted(int(i) for i in self.tree.selection())
        if len(sel) > 1:
            indices = sel
        else:
            usados = [i for i, f in enumerate(self.filas) if not f.vacia()]
            indices = list(range(usados[-1] + 1)) if usados else []
        op = self.app.op
        filas = []
        for i in indices:
            f = self.filas[i]
            r = textos_fila(f.res, "utm", op.decimales_utm, op.decimales_grados, op.separador_decimal)
            filas.append(r + ["" if f.res is None else f.res.estado])
        return texto_tabulado(filas, self._nombres_salida() + ["Estado"] if encabezados else None)

    def copiar_resultados(self) -> None:
        self._cerrar_editor(guardar=True)
        texto = self.texto_resultados(bool(self.v_enc.get()))
        if texto:
            copiar(self, texto)
            self.app.estado_temporal("Resultados copiados al portapapeles")
        else:
            self.app.estado_temporal("No hay resultados para copiar", tipo="aviso")

    def limpiar(self) -> None:
        self._cerrar_editor(guardar=False)
        self.tree.delete(*self.tree.get_children())
        self.filas.clear()
        for _ in range(FILAS_INICIALES):
            self._nueva_fila()
        self._resumen()
        self._detalle()
        self.tree.selection_set("0")
        self.tree.focus("0")
        self.app.estado.listo()
