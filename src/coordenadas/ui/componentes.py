"""Componentes reutilizables de la interfaz (sobre los estilos de ``tema``)."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable, Iterable

from . import tema
from .tema import C, T, u

MSG_LISTO = "Listo"


# --------------------------------------------------------------------------- piezas simples
class Encabezado(ttk.Frame):
    """Título de pantalla (20 px semibold) con subtítulo (13 px, color secundario)."""

    def __init__(self, padre, titulo: str, subtitulo: str = ""):
        super().__init__(padre, style="TFrame")
        self.l_titulo = ttk.Label(self, text=titulo, style="Titulo.TLabel")
        self.l_titulo.pack(anchor="w")
        if subtitulo:
            self.l_subtitulo = ttk.Label(self, text=subtitulo, style="Subtitulo.TLabel")
            self.l_subtitulo.pack(anchor="w", pady=(u(2), 0))


def divisor(padre, color: str | None = None) -> tk.Frame:
    """Línea horizontal de 1 px (color de divisor por defecto)."""
    return tk.Frame(padre, height=max(1, u(1)), background=color or C.divisor, borderwidth=0, highlightthickness=0)


class Tarjeta(ttk.Frame):
    """Contenedor blanco con borde y esquinas redondeadas. El contenido va en ``cuerpo``."""

    def __init__(self, padre, titulo: str | None = None, padding: int | None = None):
        p = u(T.pad_tarjeta) if padding is None else padding
        super().__init__(padre, style="Tarjeta.TFrame", padding=p)
        self.columnconfigure(0, weight=1)
        fila = 0
        if titulo:
            self.l_titulo = ttk.Label(self, text=titulo, style="Seccion.TLabel")
            self.l_titulo.grid(row=0, column=0, sticky="w", pady=(0, u(T.sep)))
            fila = 1
        self.cuerpo = ttk.Frame(self, style="Blanco.TFrame")
        self.cuerpo.grid(row=fila, column=0, sticky="nsew")
        self.rowconfigure(fila, weight=1)
        self.cuerpo.columnconfigure(0, weight=1)


def entrada(padre, variable: tk.StringVar, mono: bool = False, **kw) -> ttk.Entry:
    return ttk.Entry(padre, textvariable=variable, style="Campo.TEntry",
                     font=tema.fuente("mono" if mono else "texto"), **kw)


def combo(padre, variable: tk.StringVar, valores: Iterable[str], editable: bool = False, mono: bool = False,
          **kw) -> ttk.Combobox:
    cb = ttk.Combobox(padre, textvariable=variable, values=list(valores), style="Campo.TCombobox",
                      state="normal" if editable else "readonly", font=tema.fuente("mono" if mono else "texto"), **kw)
    if not editable:
        cb.bind("<<ComboboxSelected>>", lambda e: cb.selection_clear(), add="+")
    return cb


def boton(padre, texto: str, comando, estilo: str = "Secundario.TButton", icono: str | None = None, **kw) -> ttk.Button:
    if icono:
        kw["image"] = (tema.imagen(f"ic_{icono}"), "disabled", tema.imagen(f"ic_{icono}_d")) \
            if f"ic_{icono}_d" in tema._imagenes else tema.imagen(f"ic_{icono}")
        kw.setdefault("compound", "left")
        texto = f" {texto}"
    return ttk.Button(padre, text=texto, command=comando, style=estilo, **kw)


# --------------------------------------------------------------------------- selector segmentado
class SelectorSegmentado(ttk.Frame):
    """Opciones excluyentes de igual ancho en un solo control. Una sola parada de tabulación
    (la opción marcada); las flechas izquierda/derecha cambian la selección."""

    def __init__(self, padre, variable: tk.StringVar, opciones: list[tuple[str, str]],
                 al_cambiar: Callable[[], None] | None = None, fondo: str = "Blanco.TFrame"):
        super().__init__(padre, style=fondo)
        self.variable = variable
        self.al_cambiar = al_cambiar
        self.botones: dict[str, ttk.Radiobutton] = {}
        n = len(opciones)
        for i, (valor, texto) in enumerate(opciones):
            pos = "izq" if i == 0 else ("der" if i == n - 1 else "cen")
            rb = ttk.Radiobutton(self, text=texto, value=valor, variable=variable, style=f"Seg{pos}.TRadiobutton",
                                 command=self._elegido)
            rb.grid(row=0, column=i, sticky="nsew")
            rb.bind("<Left>", lambda e: self._mover(-1))
            rb.bind("<Right>", lambda e: self._mover(1))
            self.columnconfigure(i, weight=1, uniform=f"seg{id(self)}")
            self.botones[valor] = rb
        self._traza = variable.trace_add("write", lambda *a: self._foco_en_marcada())
        self.bind("<Destroy>", self._al_destruir, add="+")
        self._foco_en_marcada()

    def _al_destruir(self, e) -> None:
        if e.widget is self:
            try:
                self.variable.trace_remove("write", self._traza)
            except tk.TclError:
                pass

    def _foco_en_marcada(self) -> None:
        actual = self.variable.get()
        for valor, rb in self.botones.items():
            rb.configure(takefocus=(valor == actual) or (actual not in self.botones and rb is next(iter(self.botones.values()))))

    def _elegido(self) -> None:
        self._foco_en_marcada()
        if self.al_cambiar:
            self.al_cambiar()

    def _mover(self, paso: int) -> str:
        valores = list(self.botones)
        actual = self.variable.get()
        i = valores.index(actual) if actual in valores else 0
        j = max(0, min(len(valores) - 1, i + paso))
        if j != i:
            self.variable.set(valores[j])
            self.botones[valores[j]].focus_set()
            self._elegido()
        return "break"


# --------------------------------------------------------------------------- campo con error en línea
class CampoConError(ttk.Frame):
    """Etiqueta encima del control (o grupo de controles en ``cuerpo``) y, debajo, un ícono con
    un mensaje corto en rojo cuando hay error. El error desaparece al editar."""

    def __init__(self, padre, etiqueta: str | None, al_editar: Callable[[], None] | None = None):
        super().__init__(padre, style="Blanco.TFrame")
        self.columnconfigure(0, weight=1)
        self.al_editar = al_editar
        self.estilo_etiqueta = ("Etiqueta.TLabel", "EtiquetaError.TLabel")  # (normal, con error)
        self.controles: list[tk.Widget] = []
        self._marcados: list[tk.Widget] = []
        self.l_etiqueta = ttk.Label(self, text=etiqueta or "", style="Etiqueta.TLabel")
        if etiqueta:
            self.l_etiqueta.grid(row=0, column=0, sticky="w", pady=(0, u(T.sep_etiqueta)))
        self.cuerpo = ttk.Frame(self, style="Blanco.TFrame")
        self.cuerpo.grid(row=1, column=0, sticky="ew")
        self.cuerpo.columnconfigure(0, weight=1)
        self.l_error = ttk.Label(self, text="", style="ErrorCampo.TLabel", image=tema.imagen("ic_alerta"),
                                 compound="left", justify="left", anchor="nw")
        # El ancho del mensaje se toma de los controles (no del propio campo): así el mensaje no
        # realimenta el ancho del campo (bucle de geometría con la ventana oculta o minimizada).
        self.cuerpo.bind("<Configure>", self._ajustar_ancho, add="+")

    def agregar(self, widget: tk.Widget, variable: tk.Variable | None = None) -> tk.Widget:
        self.controles.append(widget)
        if variable is not None:
            variable.trace_add("write", lambda *a: self._editado())
        return widget

    def _ajustar_ancho(self, e) -> None:
        ancho = max(u(60), e.width - u(T.icono) - u(12))
        if abs(int(str(self.l_error.cget("wraplength") or 0)) - ancho) > 1:
            self.l_error.configure(wraplength=ancho)

    @property
    def error(self) -> str:
        return str(self.l_error.cget("text")) if self.l_error.winfo_manager() else ""

    def mostrar_error(self, mensaje: str, widgets: Iterable[tk.Widget] | None = None) -> None:
        self.limpiar_error(avisar=False)
        self._marcados = list(widgets) if widgets is not None else list(self.controles)
        for w in self._marcados:
            w.state(["invalid"])
        self.l_etiqueta.configure(style=self.estilo_etiqueta[1])
        self.l_error.configure(text=f" {mensaje}")
        self.l_error.grid(row=2, column=0, sticky="ew", pady=(u(6), 0))

    def limpiar_error(self, avisar: bool = True) -> None:
        tenia = bool(self.l_error.winfo_manager())
        for w in self._marcados:
            try:
                w.state(["!invalid"])
            except tk.TclError:
                pass
        self._marcados = []
        self.l_etiqueta.configure(style=self.estilo_etiqueta[0])
        self.l_error.grid_remove()
        self.l_error.configure(text="")
        if tenia and avisar and self.al_editar:
            self.al_editar()

    def _editado(self) -> None:
        if self.l_error.winfo_manager():
            self.limpiar_error()


# --------------------------------------------------------------------------- fila de resultado
class FilaResultado(ttk.Frame):
    """Nombre, valor grande en monoespaciada y, si corresponde, botón "Copiar". Sin valor muestra
    "—" y el botón queda deshabilitado."""

    VACIO = "—"

    def __init__(self, padre, nombre: str, variable: tk.StringVar, al_copiar: Callable[[], None] | None = None,
                 chica: bool = False, linea: bool = True):
        super().__init__(padre, style="Blanco.TFrame")
        self.variable = variable
        self.chica = chica
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, minsize=u(T.alto_fila_res))
        self.l_nombre = ttk.Label(self, text=nombre, style="ResNombre.TLabel", width=0)
        self.l_nombre.grid(row=0, column=0, sticky="w")
        self.columnconfigure(0, minsize=u(76) if not chica else u(84))
        self.v_mostrar = tk.StringVar(value=self.VACIO)
        self.l_valor = ttk.Label(self, textvariable=self.v_mostrar,
                                 style="ResValorChico.TLabel" if chica else "ResValor.TLabel")
        self.l_valor.grid(row=0, column=1, sticky="w")
        self.b_copiar = None
        if al_copiar is not None:
            self.b_copiar = boton(self, "Copiar", al_copiar, "Copiar.TButton", icono="copiar")
            self.b_copiar.grid(row=0, column=2, sticky="e", padx=(u(8), 0))
        if linea:
            divisor(self, C.divisor_fila).grid(row=1, column=0, columnspan=3, sticky="ew")
        variable.trace_add("write", lambda *a: self._actualizar())
        self.bind("<Configure>", lambda e: self._ajustar_fuente(), add="+")
        self._actualizar()

    @property
    def texto(self) -> str:
        return self.variable.get()

    def _actualizar(self) -> None:
        valor = self.variable.get()
        self.v_mostrar.set(valor if valor else self.VACIO)
        if self.b_copiar is not None:
            self.b_copiar.state(["!disabled"] if valor else ["disabled"])
        self._ajustar_fuente()

    def _ajustar_fuente(self) -> None:
        """Usa la fuente menor si el valor no cabe en el espacio disponible."""
        if self.chica:
            return
        ancho = self.winfo_width()
        if ancho <= 1:
            return
        disp = ancho - self.grid_bbox(0, 0)[2] - (self.b_copiar.winfo_reqwidth() + u(8) if self.b_copiar else 0) - u(4)
        cabe = tema.fuente("resultado").measure(self.v_mostrar.get()) <= disp
        estilo = "ResValor.TLabel" if cabe else "ResValorChico.TLabel"
        if str(self.l_valor.cget("style")) != estilo:
            self.l_valor.configure(style=estilo)


# --------------------------------------------------------------------------- barra de estado
class BarraEstado(ttk.Frame):
    """Mensaje a la izquierda (con ícono según el tipo) y texto fijo a la derecha."""

    ESTILOS = {
        "info": ("Estado.TLabel", ""),
        "ok": ("EstadoOk.TLabel", "ic_check"),
        "error": ("EstadoError.TLabel", "ic_cruz"),
        "revisar": ("EstadoError.TLabel", "ic_aviso"),
        "aviso": ("EstadoAviso.TLabel", "ic_aviso_ambar"),
    }

    def __init__(self, padre):
        super().__init__(padre, style="Estado.TFrame", height=u(T.alto_estado))
        self.grid_propagate(False)
        self.pack_propagate(False)
        divisor(self).place(x=0, y=0, relwidth=1.0)
        self.v_mensaje = tk.StringVar(value=MSG_LISTO)
        self.v_derecha = tk.StringVar()
        self.tipo = "info"
        self._texto = MSG_LISTO
        self.l_derecha = ttk.Label(self, textvariable=self.v_derecha, style="EstadoSec.TLabel")
        self.l_derecha.pack(side="right", padx=(u(8), u(16)))
        self.l_visible = ttk.Label(self, text=MSG_LISTO, style="Estado.TLabel", compound="left", anchor="w")
        self.l_visible.pack(side="left", fill="x", expand=True, padx=(u(16), u(8)))
        self.l_mensaje = self.l_visible
        self.bind("<Configure>", lambda e: self._recortar(), add="+")
        self.v_derecha.trace_add("write", lambda *a: self.after_idle(self._recortar))
        self._id = None

    def _recortar(self) -> None:
        """Muestra el mensaje completo o recortado con "…" para no tapar el texto de la derecha."""
        try:
            disp = self.winfo_width() - self.l_derecha.winfo_reqwidth() - u(16 + 8 + 8 + 16) - u(T.icono + 4)
        except tk.TclError:
            return
        texto = self.v_mensaje.get()
        f = tema.fuente("estado")
        if disp > 0 and f.measure(texto) > disp:
            while texto and f.measure(texto + "…") > disp:
                texto = texto[:-1]
            texto = texto.rstrip() + "…"
        self.l_visible.configure(text=texto)

    def mostrar(self, texto: str, tipo: str = "info", temporal_ms: int | None = None) -> None:
        estilo, img = self.ESTILOS.get(tipo, self.ESTILOS["info"])
        self.tipo = tipo
        self.v_mensaje.set(f" {texto}" if img else texto)
        self.l_visible.configure(style=estilo, image=tema.imagen(img) if img else "")
        self._recortar()
        if self._id is not None:
            try:
                self.after_cancel(self._id)
            except tk.TclError:
                pass
            self._id = None
        if temporal_ms:
            self._id = self.after(temporal_ms, self.listo)

    def listo(self) -> None:
        self._id = None
        self.mostrar(MSG_LISTO)

    @property
    def mensaje(self) -> str:
        return self.v_mensaje.get().strip()


# --------------------------------------------------------------------------- área con desplazamiento
class AreaDesplazable(ttk.Frame):
    """Contenido que se desplaza en vertical solo si no cabe (escalado alto o ventana baja).
    Si sobra alto, el contenido se estira para ocuparlo. El contenido va en ``interior``."""

    def __init__(self, padre):
        super().__init__(padre, style="TFrame")
        self.lienzo = tk.Canvas(self, background=C.fondo, highlightthickness=0, borderwidth=0)
        self.barra = ttk.Scrollbar(self, orient="vertical", command=self.lienzo.yview)
        self.lienzo.configure(yscrollcommand=self.barra.set)
        self.lienzo.grid(row=0, column=0, sticky="nsew")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self._soporte = ttk.Frame(self.lienzo, style="TFrame")
        self._soporte.columnconfigure(0, weight=1)
        self._soporte.rowconfigure(0, weight=1)
        self.interior = ttk.Frame(self._soporte, style="TFrame")
        self.interior.grid(row=0, column=0, sticky="nsew")
        self._item = self.lienzo.create_window(0, 0, window=self._soporte, anchor="nw")
        self.lienzo.bind("<Configure>", self._lienzo_cambio, add="+")
        self._soporte.bind("<Configure>", lambda e: self._actualizar(), add="+")
        self.winfo_toplevel().bind_all("<MouseWheel>", self._rueda, add="+")

    def _lienzo_cambio(self, e) -> None:
        self.lienzo.itemconfigure(self._item, width=e.width)
        self._soporte.rowconfigure(0, minsize=e.height)
        self._actualizar()

    def _actualizar(self) -> None:
        alto = self._soporte.winfo_reqheight()
        visible = self.lienzo.winfo_height()
        self.lienzo.configure(scrollregion=(0, 0, self.lienzo.winfo_width(), max(alto, visible)))
        necesita = alto > visible + 1 and visible > 1
        if necesita and not self.barra.winfo_manager():
            self.barra.grid(row=0, column=1, sticky="ns")
        elif not necesita and self.barra.winfo_manager():
            self.barra.grid_remove()
            self.lienzo.yview_moveto(0)

    def _rueda(self, e) -> None:
        try:
            if not self.winfo_exists() or not self.barra.winfo_manager():
                return
            w = self.winfo_containing(e.x_root, e.y_root)
        except (tk.TclError, KeyError):
            return
        while w is not None:
            if isinstance(w, (ttk.Treeview, tk.Listbox, tk.Text)):
                return
            if w is self:
                self.lienzo.yview_scroll(int(-e.delta / 120) or (-1 if e.delta > 0 else 1), "units")
                return
            w = w.master

    def ver(self, widget: tk.Widget) -> None:
        """Desplaza para que ``widget`` quede visible."""
        self.update_idletasks()
        alto = max(1, self._soporte.winfo_height())
        y = widget.winfo_rooty() - self._soporte.winfo_rooty()
        visible = self.lienzo.winfo_height()
        arriba = self.lienzo.canvasy(0)
        if y < arriba or y + widget.winfo_height() > arriba + visible:
            self.lienzo.yview_moveto(max(0.0, (y - u(T.sep)) / alto))
