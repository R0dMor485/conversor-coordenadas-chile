"""Pestaña 3: "Archivo Excel" (.xlsx, .csv y .xls de solo lectura).

Tres tarjetas en vertical (Archivo, Columnas, Salida), progreso en una barra delgada sobre la fila
inferior y resumen final en la propia pantalla (sin ventanas emergentes).
"""
from __future__ import annotations

import queue
import re
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, ttk

from ..io.excel_io import a_texto, leer_filas, letra_columna, listar_hojas, nombre_salida, tipo_archivo
from ..io.proceso import CAMPOS, ConfigProceso, procesar_archivo
from . import componentes as K
from . import tema
from .comun import CLAVE_POR_ETIQUETA, ETIQUETA_POR_CLAVE, combo_datum
from .panel_salida import PanelSalida
from .tema import T, u

FORMATO = "utm"  # esta pestaña solo trabaja con coordenadas UTM
ETIQ_CAMPO = {
    "lat": "Latitud", "lon": "Longitud", "lat_g": "Lat. grados", "lat_m": "Lat. minutos", "lat_s": "Lat. segundos",
    "lon_g": "Lon. grados", "lon_m": "Lon. minutos", "lon_s": "Lon. segundos", "norte": "Norte", "este": "Este", "zona": "Huso",
}
# Preselección por nombre de encabezado (visible y modificable en los combos).
PATRONES = {
    "lat": r"^(lat|latitud|latitude|y_?geo)\b", "lon": r"^(lon|long|longitud|longitude|x_?geo)\b",
    "norte": r"^(norte|n|y|north|northing|coord_?n)\b", "este": r"^(este|e|x|east|easting|coord_?e)\b",
    "zona": r"^(zona|huso|zone|uso)\b",
}
FILAS_VISTA = 10
SIN_COLUMNA = "—"


class TabExcel(ttk.Frame):
    mostrar_dialogos = False  # compatibilidad: el resumen ya no usa ventanas emergentes

    def __init__(self, padre, app):
        super().__init__(padre, style="TFrame")
        self.app = app
        u_ = app.op.ultimas
        self.columnas: list[str] = []
        self.hilo: threading.Thread | None = None
        self.cola: queue.Queue = queue.Queue()
        self.cancelar = threading.Event()
        self.ultimo_resumen = None
        self._reemplazo_ok: str | None = None  # destino cuyo reemplazo ya se confirmó
        mh, mv, sep, sc = u(T.margen_h), u(T.margen_v), u(T.sep), u(T.sep_campos)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        K.Encabezado(self, "Archivo Excel", "Convierte las coordenadas de una planilla en una copia nueva.") \
            .grid(row=0, column=0, sticky="ew", padx=mh, pady=(mv, u(12)))
        self.area = K.AreaDesplazable(self)
        self.area.grid(row=1, column=0, sticky="nsew")
        cont = self.area.interior
        cont.columnconfigure(0, weight=1)

        # ------------------------------------------------------------- tarjeta Archivo
        ta = K.Tarjeta(cont, "Archivo")
        ta.grid(row=0, column=0, sticky="ew", padx=mh)
        ca = ta.cuerpo
        ca.columnconfigure(0, weight=1, uniform="arch")
        ca.columnconfigure(1, weight=1, uniform="arch")
        self.v_ruta = tk.StringVar()
        c = K.CampoConError(ca, "Archivo de coordenadas")
        c.grid(row=0, column=0, columnspan=2, sticky="ew")
        c.cuerpo.columnconfigure(0, weight=1)
        self.e_ruta = c.agregar(K.entrada(c.cuerpo, self.v_ruta), self.v_ruta)
        self.e_ruta.grid(row=0, column=0, sticky="ew")
        self.b_examinar = K.boton(c.cuerpo, "Examinar…", self.examinar, "Tarjeta.TButton", icono="carpeta")
        self.b_examinar.grid(row=0, column=1, padx=(sc, 0))
        self.v_hoja = tk.StringVar()
        c = K.CampoConError(ca, "Hoja")
        self.cb_hoja = c.agregar(K.combo(c.cuerpo, self.v_hoja, []))
        self.cb_hoja.grid(row=0, column=0, sticky="ew")
        self.cb_hoja.bind("<<ComboboxSelected>>", lambda e: self.cargar_vista(), add="+")
        c.grid(row=1, column=0, sticky="ew", padx=(0, sc // 2), pady=(sep, 0))
        self.v_enc = tk.StringVar(value="1")
        c = K.CampoConError(ca, "Fila de encabezado (0 = sin encabezado)")
        self.sp_enc = ttk.Spinbox(c.cuerpo, from_=0, to=50, textvariable=self.v_enc, command=self.cargar_vista,
                                  style="Campo.TSpinbox", font=tema.fuente("mono"), width=6)
        c.agregar(self.sp_enc)
        self.sp_enc.grid(row=0, column=0, sticky="w")
        self.sp_enc.bind("<Return>", lambda e: (self.cargar_vista(), "break")[1])
        c.grid(row=1, column=1, sticky="ew", padx=(sc // 2, 0), pady=(sep, 0))

        # ------------------------------------------------------------- tarjeta Columnas
        tcol = K.Tarjeta(cont, "Columnas")
        tcol.grid(row=1, column=0, sticky="ew", padx=mh, pady=(sep, 0))
        cc = tcol.cuerpo
        ttk.Label(cc, text="Coordenadas UTM: asigna la columna de Norte, Este y Huso.", style="Ayuda.TLabel").grid(
            row=0, column=0, sticky="w")
        self.f_campos = ttk.Frame(cc, style="Blanco.TFrame")
        self.f_campos.grid(row=2, column=0, sticky="ew", pady=(sep, 0))
        for k in range(3):
            self.f_campos.columnconfigure(k, weight=1, uniform="cols")
        self.v_col: dict[str, tk.StringVar] = {k: tk.StringVar(value=SIN_COLUMNA) for k in ETIQ_CAMPO}
        self.v_zona_modo = tk.StringVar(value="columna")
        self.v_zona_fija = tk.StringVar(value="19")

        K.divisor(cc).grid(row=3, column=0, sticky="ew", pady=(sep, sep))
        self.v_datum_modo = tk.StringVar(value="fijo")
        self.v_datum_in = tk.StringVar(value=ETIQUETA_POR_CLAVE.get(u_.get("t3_datum_entrada"), ETIQUETA_POR_CLAVE["PSAD56"]))
        self.v_col_datum = tk.StringVar(value=SIN_COLUMNA)
        fd = ttk.Frame(cc, style="Blanco.TFrame")
        fd.grid(row=4, column=0, sticky="ew")
        fd.columnconfigure(0, weight=1, uniform="dat")
        fd.columnconfigure(1, weight=1, uniform="dat")
        ttk.Label(fd, text="Datum de entrada", style="Etiqueta.TLabel").grid(row=0, column=0, columnspan=2, sticky="w")
        ttk.Radiobutton(fd, text="Uno para todo el archivo", value="fijo", variable=self.v_datum_modo,
                        style="Opcion.TRadiobutton").grid(row=1, column=0, sticky="w", pady=(u(4), 0))
        ttk.Radiobutton(fd, text="Columna del archivo", value="columna", variable=self.v_datum_modo,
                        style="Opcion.TRadiobutton").grid(row=1, column=1, sticky="w", padx=(sc, 0), pady=(u(4), 0))
        self.cb_datum_fijo = combo_datum(fd, self.v_datum_in)
        self.cb_datum_fijo.grid(row=2, column=0, sticky="ew", pady=(u(6), 0))
        self.cb_datum_fijo.bind("<<ComboboxSelected>>", lambda e: self.v_datum_modo.set("fijo"), add="+")
        self.cb_col_datum = K.combo(fd, self.v_col_datum, [])
        self.cb_col_datum.grid(row=2, column=1, sticky="ew", padx=(sc, 0), pady=(u(6), 0))
        self.cb_col_datum.bind("<<ComboboxSelected>>", lambda e: self.v_datum_modo.set("columna"), add="+")

        K.divisor(cc).grid(row=5, column=0, sticky="ew", pady=(sep, sep))
        ttk.Label(cc, text="Vista previa", style="Etiqueta.TLabel").grid(row=6, column=0, sticky="w", pady=(0, u(6)))
        marco = ttk.Frame(cc, style="Blanco.TFrame")
        marco.grid(row=7, column=0, sticky="ew")
        marco.columnconfigure(0, weight=1)
        self.vista = ttk.Treeview(marco, show="headings", height=4, style="Cuadricula.Treeview")
        sx = ttk.Scrollbar(marco, orient="horizontal", command=self.vista.xview)
        self.vista.configure(xscrollcommand=sx.set)
        self.vista.grid(row=0, column=0, sticky="ew")
        sx.grid(row=1, column=0, sticky="ew")
        self.vista.tag_configure("alterna", background=tema.C.fila_alterna)

        # ------------------------------------------------------------- tarjeta Salida
        ts = K.Tarjeta(cont, "Salida")
        ts.grid(row=2, column=0, sticky="ew", padx=mh, pady=(sep, 0))
        cs = ts.cuerpo
        self.panel = PanelSalida(cs, app, "t3_", self.app.guardar_opciones, con_formato=False,
                                 etiqueta_datum="Datum de salida")
        self.panel.grid(row=0, column=0, sticky="ew")
        self.v_destino = tk.StringVar()
        c = K.CampoConError(cs, "Copia de salida")
        c.grid(row=1, column=0, sticky="ew", pady=(sep, 0))
        c.cuerpo.columnconfigure(0, weight=1)
        self.e_destino = c.agregar(K.entrada(c.cuerpo, self.v_destino), self.v_destino)
        self.e_destino.grid(row=0, column=0, sticky="ew")
        self.b_destino = K.boton(c.cuerpo, "Cambiar…", self.elegir_destino, "Tarjeta.TButton")
        self.b_destino.grid(row=0, column=1, padx=(sc, 0))
        self.v_destino.trace_add("write", lambda *a: setattr(self, "_reemplazo_ok", None))

        # ------------------------------------------------------------- resumen, progreso y fila inferior
        self.f_resumen = ttk.Frame(self, style="TFrame")
        self.f_resumen.grid(row=2, column=0, sticky="ew", padx=mh, pady=(sep, 0))
        self.f_resumen.columnconfigure(0, weight=1)
        self.l_msg = ttk.Label(self.f_resumen, text="", style="Fondo.TLabel", justify="left", anchor="nw", compound="left")
        self.l_msg.grid(row=0, column=0, sticky="ew")
        self.f_resumen.bind("<Configure>", self._ajustar_resumen, add="+")
        self.f_resumen.grid_remove()
        self.barra = ttk.Progressbar(self, mode="determinate", maximum=1.0, style="Delgada.Horizontal.TProgressbar")
        self.barra.grid(row=3, column=0, sticky="ew", padx=mh, pady=(sep, 0))
        fa = ttk.Frame(self, style="TFrame")
        fa.grid(row=4, column=0, sticky="ew", padx=mh, pady=(u(12), u(16)))
        self.b_ajustes = K.boton(fa, "Ajustes", self.app.abrir_ajustes, "Discreto.TButton", icono="ajustes")
        self.b_ajustes.pack(side="left")
        self.b_convertir = K.boton(fa, "Convertir", self.iniciar, "Principal.TButton")
        self.b_cancelar = K.boton(fa, "Cancelar", self.cancelar.set, "Secundario.TButton", state="disabled")
        self.b_convertir.pack(side="right")
        self.b_cancelar.pack(side="right", padx=(0, sc))
        self.b_cancelar.lower(self.b_convertir)

        self._construir_campos()
        # el datum de salida no puede ser el de entrada cuando este es uno para todo el archivo
        self.v_datum_in.trace_add("write", lambda *a: self._actualizar_exclusion())
        self.v_datum_modo.trace_add("write", lambda *a: self._actualizar_exclusion())
        self._actualizar_exclusion()

    # ------------------------------------------------------------------ mensajes
    def _ajustar_resumen(self, e) -> None:
        ancho = max(u(120), e.width - u(T.icono) - u(12))
        if abs(int(str(self.l_msg.cget("wraplength") or 0)) - ancho) > 1:
            self.l_msg.configure(wraplength=ancho)

    def _mensaje(self, texto: str, tipo="ok", estado: str | None = None) -> None:
        """Mensaje en la pantalla (resumen) y, en la barra de estado, ``estado`` o la primera línea."""
        if tipo is True:
            tipo = "error"
        elif tipo is False:
            tipo = "ok"
        estilo, icono = {
            "ok": ("FondoOk.TLabel", "ic_check"), "error": ("FondoError.TLabel", "ic_cruz"),
            "aviso": ("FondoAviso.TLabel", "ic_aviso_ambar"), "info": ("Fondo.TLabel", ""),
        }[tipo]
        self.l_msg.configure(text=texto, style=estilo, image=tema.imagen(icono) if icono else "")
        if texto:
            self.f_resumen.grid()
        else:
            self.f_resumen.grid_remove()
        self.app.mensaje(estado if estado is not None else texto.splitlines()[0] if texto else "Listo",
                         {"error": "error", "ok": "ok", "aviso": "aviso", "info": "info"}[tipo])

    # ------------------------------------------------------------------ archivo y vista previa
    def examinar(self) -> None:
        inicial = self.app.op.ultimas.get("t3_carpeta") or None
        ruta = filedialog.askopenfilename(
            parent=self, title="Abrir archivo de coordenadas", initialdir=inicial,
            filetypes=[("Excel o csv", "*.xlsx *.xlsm *.xls *.csv"), ("Excel", "*.xlsx *.xlsm *.xls"), ("csv", "*.csv"), ("Todos", "*.*")],
        )
        if ruta:
            self.abrir(ruta)

    def abrir(self, ruta: str) -> bool:
        try:
            tipo_archivo(ruta)
            hojas = listar_hojas(ruta)
        except Exception as e:  # archivo dañado, protegido, tipo no admitido…
            self._mensaje(f"No se pudo abrir el archivo: {e}", "error")
            return False
        self.v_ruta.set(ruta)
        self.app.op.ultimas["t3_carpeta"] = str(Path(ruta).parent)
        self.app.guardar_opciones()
        self.cb_hoja.configure(values=hojas)
        self.v_hoja.set(hojas[0] if hojas else "")
        self.v_destino.set(str(nombre_salida(ruta)))
        aviso = " (.xls: la copia se guarda como .xlsx con valores)" if tipo_archivo(ruta) == "xls" else ""
        self.cargar_vista()
        if aviso:
            self._mensaje(f"Archivo abierto{aviso}.", "aviso", estado=f"Archivo abierto: {Path(ruta).name}")
        else:  # solo la barra de estado: no se ocupa espacio de pantalla con un bloque de resumen
            self._mensaje("", "info", estado=f"Archivo abierto: {Path(ruta).name}")
            self.app.mensaje(f"Archivo abierto: {Path(ruta).name}", "ok")
        return True

    def _fila_enc(self) -> int | None:
        try:
            n = int(self.v_enc.get())
        except ValueError:
            n = 1
        return None if n <= 0 else n - 1

    def cargar_vista(self) -> None:
        ruta, hoja = self.v_ruta.get(), self.v_hoja.get()
        if not ruta or not hoja:
            return
        enc = self._fila_enc()
        try:
            filas = list(leer_filas(ruta, hoja, max_filas=(enc or 0) + 1 + FILAS_VISTA))
        except Exception as e:
            self._mensaje(f"No se pudo leer la hoja: {e}", "error")
            return
        ancho = max((len(f) for f in filas), default=0)
        while ancho and all(len(f) < ancho or f[ancho - 1] is None for f in filas):
            ancho -= 1  # sin columnas vacías al final
        cab = filas[enc] if enc is not None and enc < len(filas) else []
        self.columnas = []
        for i in range(ancho):
            nombre = a_texto(cab[i]).strip() if i < len(cab) else ""
            self.columnas.append(f"{letra_columna(i)} — {nombre}" if nombre else f"Columna {letra_columna(i)}")
        datos = filas[(enc + 1) if enc is not None else 0:]
        ids = [f"c{i}" for i in range(ancho)]
        self.vista.configure(columns=ids)
        for i, c in enumerate(ids):
            self.vista.heading(c, text=self.columnas[i], anchor="w")
            self.vista.column(c, width=u(110), minwidth=u(80), stretch=True, anchor="w")
        self.vista.delete(*self.vista.get_children())
        for k, f in enumerate(datos[:FILAS_VISTA]):
            self.vista.insert("", "end", values=[a_texto(f[i]) if i < len(f) else "" for i in range(ancho)],
                              tags=("alterna",) if k % 2 else ())
        valores = [SIN_COLUMNA] + self.columnas
        for cb in self._combos_columnas():
            cb.configure(values=valores)
        self.cb_col_datum.configure(values=valores)
        self._preseleccionar(cab)

    def _preseleccionar(self, cab: list) -> None:
        nombres = [a_texto(c).strip().lower() for c in cab]
        usados = set()
        for campo, patron in PATRONES.items():
            for i, n in enumerate(nombres):
                if i not in usados and n and re.search(patron, n):
                    self.v_col[campo].set(self.columnas[i])
                    usados.add(i)
                    break
            else:
                if self.v_col[campo].get() not in self.columnas:
                    self.v_col[campo].set(SIN_COLUMNA)
        for i, n in enumerate(nombres):
            if n.startswith("datum"):
                self.v_col_datum.set(self.columnas[i])

    # ------------------------------------------------------------------ campos según formato
    def _combos_columnas(self) -> list[ttk.Combobox]:
        return list(getattr(self, "_cbs", []))

    def _actualizar_exclusion(self) -> None:
        excluido = CLAVE_POR_ETIQUETA[self.v_datum_in.get()] if self.v_datum_modo.get() == "fijo" else None
        if self.panel.excluir(excluido):
            self.app.estado_temporal(f"Datum de salida cambiado a {self.panel.v_datum.get()}", tipo="info")
            self.app.guardar_opciones()

    def _construir_campos(self) -> None:
        for w in self.f_campos.winfo_children():
            w.destroy()
        fmt = FORMATO
        valores = [SIN_COLUMNA] + self.columnas
        campos = [c for c in CAMPOS[fmt] if c != "zona"]
        self._cbs = []
        sc = u(T.sep_campos)
        for k, campo in enumerate(campos):
            fila, col = divmod(k, 3)
            c = K.CampoConError(self.f_campos, ETIQ_CAMPO[campo])
            cb = c.agregar(K.combo(c.cuerpo, self.v_col[campo], valores))
            cb.grid(row=0, column=0, sticky="ew")
            c.grid(row=fila, column=col, sticky="new", padx=(0 if col == 0 else sc // 2, 0 if col == 2 else sc // 2),
                   pady=(0 if fila == 0 else u(T.sep), 0))
            self._cbs.append(cb)
        if fmt == "utm":
            fz = ttk.Frame(self.f_campos, style="Blanco.TFrame")
            fz.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(u(T.sep), 0))
            fz.columnconfigure(0, weight=1, uniform="zn")
            fz.columnconfigure(1, weight=1, uniform="zn")
            fz.columnconfigure(2, weight=1, uniform="zn")
            ttk.Label(fz, text="Huso", style="Etiqueta.TLabel").grid(row=0, column=0, columnspan=3, sticky="w")
            ttk.Radiobutton(fz, text="Columna", value="columna", variable=self.v_zona_modo,
                            style="Opcion.TRadiobutton").grid(row=1, column=0, sticky="w", pady=(u(4), 0))
            ttk.Radiobutton(fz, text="Valor fijo", value="fijo", variable=self.v_zona_modo,
                            style="Opcion.TRadiobutton").grid(row=1, column=1, sticky="w", pady=(u(4), 0), padx=(sc, 0))
            cbz = K.combo(fz, self.v_col["zona"], valores)
            cbz.grid(row=2, column=0, sticky="ew", pady=(u(6), 0), padx=(0, sc // 2))
            cbz.bind("<<ComboboxSelected>>", lambda e: self.v_zona_modo.set("columna"), add="+")
            self._cbs.append(cbz)
            cf = K.combo(fz, self.v_zona_fija, ["18", "19"], editable=True, mono=True)
            cf.grid(row=2, column=1, sticky="ew", pady=(u(6), 0), padx=(sc // 2, 0))
            cf.bind("<<ComboboxSelected>>", lambda e: self.v_zona_modo.set("fijo"), add="+")

    # ------------------------------------------------------------------ configuración del proceso
    def _indice(self, etiqueta: str) -> int | None:
        return self.columnas.index(etiqueta) if etiqueta in self.columnas else None

    def config_proceso(self) -> ConfigProceso:
        """Arma la configuración desde los controles. Lanza ValueError con un mensaje claro."""
        fmt = FORMATO
        cols = {}
        for campo in CAMPOS[fmt]:
            if campo == "zona" and self.v_zona_modo.get() == "fijo":
                continue
            idx = self._indice(self.v_col[campo].get())
            if idx is None:
                raise ValueError(f"Asigne la columna de «{ETIQ_CAMPO[campo]}».")
            cols[campo] = idx
        if len(set(cols.values())) != len(cols):
            raise ValueError("Hay una misma columna asignada a dos campos.")
        zona_fija = None
        if fmt == "utm" and self.v_zona_modo.get() == "fijo":
            try:
                zona_fija = int(self.v_zona_fija.get())
            except ValueError:
                raise ValueError("Huso fijo inválido.") from None
        col_datum = None
        datum_fijo = CLAVE_POR_ETIQUETA[self.v_datum_in.get()]
        if self.v_datum_modo.get() == "columna":
            col_datum = self._indice(self.v_col_datum.get())
            if col_datum is None:
                raise ValueError("Asigne la columna de datum de entrada.")
            datum_fijo = None
        op = self.app.op
        return ConfigProceso(
            formato=fmt, columnas=cols, datum_salida=self.panel.datum, formato_salida=self.panel.formato,
            zona_salida=self.panel.zona, metodo=op.metodo_enum, datum_fijo=datum_fijo, col_datum=col_datum,
            zona_fija=zona_fija, positivos_sur_oeste=op.positivos_sur_oeste, decimales_utm=op.decimales_utm,
            decimales_grados=op.decimales_grados, separador_decimal=op.separador_decimal, fila_encabezado=self._fila_enc(),
        )

    def elegir_destino(self) -> None:
        if not self.v_ruta.get():
            self._mensaje("Primero elige un archivo.", "aviso")
            return
        actual = Path(self.v_destino.get() or nombre_salida(self.v_ruta.get()))
        ext = actual.suffix
        ruta = filedialog.asksaveasfilename(
            parent=self, title="Guardar copia convertida como", initialdir=str(actual.parent), initialfile=actual.name,
            defaultextension=ext, filetypes=[("csv" if ext == ".csv" else "Excel", f"*{ext}")],
        )
        if ruta:
            self.v_destino.set(ruta)
            self._reemplazo_ok = ruta  # el selector de archivos ya pidió confirmar el reemplazo

    # ------------------------------------------------------------------ ejecución en hilo
    def iniciar(self, confirmar: bool = True) -> bool:
        if self.hilo and self.hilo.is_alive():
            return False
        origen, hoja, destino = self.v_ruta.get(), self.v_hoja.get(), self.v_destino.get()
        if not origen or not hoja:
            self._mensaje("Elige un archivo y una hoja.", "error")
            return False
        try:
            cfg = self.config_proceso()
        except ValueError as e:
            self._mensaje(str(e), "error")
            return False
        destino = destino or str(nombre_salida(origen))
        if Path(destino).resolve() == Path(origen).resolve():
            self._mensaje("La copia de salida no puede ser el archivo original.", "error")
            return False
        if confirmar and Path(destino).exists() and self._reemplazo_ok != destino:
            # confirmación en pantalla (sin ventana emergente): se pide pulsar Convertir otra vez
            self._reemplazo_ok = destino
            self._mensaje(f"Ya existe {Path(destino).name}. Pulsa Convertir otra vez para reemplazarlo "
                          "o cambia la copia de salida.", "aviso")
            return False
        self.app.op.ultimas["t3_datum_entrada"] = CLAVE_POR_ETIQUETA[self.v_datum_in.get()]
        self.app.guardar_opciones()
        self.cancelar.clear()
        self.b_convertir.configure(state="disabled")
        self.b_cancelar.configure(state="normal")
        self.barra.configure(mode="determinate", value=0)
        self._mensaje("Procesando…", "info")

        def trabajo():
            try:
                r = procesar_archivo(origen, hoja, destino, cfg, avance=lambda fr, t: self.cola.put(("avance", fr, t)), cancelar=self.cancelar)
                self.cola.put(("fin", r, None))
            except PermissionError:
                self.cola.put(("error", f"No se pudo escribir {destino}: ¿está abierto en Excel?", None))
            except Exception as e:  # noqa: BLE001 - se informa al usuario
                self.cola.put(("error", f"Error al procesar: {e}", None))

        self.hilo = threading.Thread(target=trabajo, daemon=True)
        self.hilo.start()
        self.after(100, self._sondear)
        return True

    def _sondear(self) -> None:
        fin = None
        try:
            while True:
                msg = self.cola.get_nowait()
                if msg[0] == "avance":
                    _, fr, txt = msg
                    if fr is None:
                        if str(self.barra.cget("mode")) != "indeterminate":
                            self.barra.configure(mode="indeterminate")
                            self.barra.start(15)
                    else:
                        if str(self.barra.cget("mode")) == "indeterminate":
                            self.barra.stop()
                            self.barra.configure(mode="determinate")
                        self.barra.configure(value=fr)
                    self.app.mensaje(txt, "info")
                else:
                    fin = msg
        except queue.Empty:
            pass
        if fin is None:
            self.after(100, self._sondear)
            return
        self.barra.stop()
        self.barra.configure(mode="determinate", value=0)
        self.b_convertir.configure(state="normal")
        self.b_cancelar.configure(state="disabled")
        if fin[0] == "error":
            self._mensaje(fin[1], "error")
            self.ultimo_resumen = None
            return
        r = fin[1]
        self.ultimo_resumen = r
        if r.cancelado:
            self._mensaje("Proceso cancelado. No se escribió la copia.", "aviso")
            return
        self.barra.configure(value=1.0)
        lineas = [f"Copia guardada: {Path(r.destino).name}",
                  f"Filas OK: {r.ok} · Filas con error: {r.error}"
                  + (f" · Filas vacías omitidas: {r.vacias}" if r.vacias else "")]
        lineas += [f"Fila {n}: {m}" for n, m in r.errores_ejemplo[:2]]
        self._mensaje("\n".join(lineas), "error" if r.error and not r.ok else ("aviso" if r.error else "ok"),
                      estado=f"Copia guardada: {Path(r.destino).name}")

    def refrescar(self) -> None:
        pass

    def al_cerrar(self) -> None:
        self.cancelar.set()
