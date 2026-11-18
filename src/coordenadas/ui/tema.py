"""Sistema visual de la interfaz: colores, fuentes, tamaños y estilos ttk.

Todo lo visual está centralizado aquí. Para cambiar un color, una fuente o un tamaño basta con
editar ``Paleta``, ``FUENTES`` o ``T``. Un modo oscuro se agregaría creando otra ``Paleta`` y
asignándola a ``C`` antes de ``aplicar`` (no implementado).

Base: tema sv-ttk (Sun Valley, modo claro, licencia MIT). Encima se definen elementos propios
(campos, botones, tarjetas, selector segmentado, pestañas, casillas…) dibujados por
``imagenes.py`` con los colores exactos de la maqueta, de modo que el acento es exactamente
#1F5FBF aunque sv-ttk use su propio azul (#005FB8) en sus imágenes.

Escala: los tamaños de ``T`` están en píxeles de diseño a 96 ppp (100 %); ``u()`` los convierte
a píxeles reales según ``tk scaling``. Las fuentes se definen en puntos y Tk las escala solo.
"""
from __future__ import annotations

import tkinter as tk
import tkinter.font as tkfont
from dataclasses import dataclass
from tkinter import ttk

from . import imagenes as im


# --------------------------------------------------------------------------- colores
@dataclass(frozen=True)
class Paleta:
    fondo: str = "#F3F5F8"  # ventana
    tarjeta: str = "#FFFFFF"
    borde_tarjeta: str = "#DADFE6"
    control: str = "#FFFFFF"
    borde_control: str = "#C3CAD5"
    borde_control_hover: str = "#A3ADBB"
    texto: str = "#1B1F24"
    texto_sec: str = "#5B6573"
    divisor: str = "#E3E7ED"
    divisor_fila: str = "#EEF1F5"
    acento: str = "#1F5FBF"
    acento_hover: str = "#1A53A8"
    acento_presionado: str = "#164791"
    acento_borde_foco: str = "#0F3672"
    acento_tinte: str = "#E4ECF7"  # acento al 12 % sobre blanco
    acento_deshabilitado: str = "#A5BCE0"
    error: str = "#B42318"
    exito: str = "#067647"
    aviso: str = "#9A6700"
    fondo_aviso: str = "#FFF4D6"
    fondo_error: str = "#FDECEA"
    deshab_fondo: str = "#F3F5F8"
    deshab_borde: str = "#DADFE6"
    deshab_texto: str = "#5B6573"
    hover: str = "#F5F7FA"
    presionado: str = "#EBEEF2"
    discreto_hover: str = "#E8ECF1"
    fila_alterna: str = "#F7F9FB"
    indicador: str = "#7A8494"  # borde de casillas y opciones sin marcar
    barra_estado: str = "#FFFFFF"


CLARO = Paleta()
C = CLARO  # paleta activa

# --------------------------------------------------------------------------- tamaños (px de diseño a 100 %)
class T:
    margen_h = 24
    margen_v = 20
    pad_tarjeta = 20
    sep = 16  # entre elementos
    sep_campos = 12  # entre campos de una fila
    sep_etiqueta = 6  # entre etiqueta y control
    alto_campo = 34
    alto_segmento = 32
    alto_fila_res = 52
    alto_copiar = 30
    alto_boton = 34
    alto_principal = 38
    alto_estado = 28
    radio_tarjeta = 8
    radio_control = 6
    grosor_error = 1.5
    grosor_foco = 1.5
    icono = 16
    indicador = 18
    alto_fila_cuadricula = 32
    alto_progreso = 4
    ventana_ancho = 880
    ventana_alto = 720
    ventana_min_ancho = 820
    ventana_min_alto = 680
    dialogo_ancho = 520
    dialogo_alto = 680


# --------------------------------------------------------------------------- fuentes
# (familias candidatas, tamaño en puntos, negrita si la familia no trae el peso).
# Equivalencias a 96 ppp: 20 px = 15 pt; 14 px ≈ 10,5 pt → 11; 13 px ≈ 9,75 pt → 10; 12 px = 9 pt;
# 22 px ≈ 16,5 pt → 16. Tk solo admite puntos enteros.
SANS = ("Segoe UI", "Tahoma", "Arial")
SANS_SEMI = ("Segoe UI Semibold",)
MONO = ("Cascadia Mono", "Consolas", "Courier New")
MONO_SEMI = ("Cascadia Mono SemiBold",)

FUENTES: dict[str, tuple[tuple[str, ...], int, bool]] = {
    "titulo": (SANS_SEMI, 15, False),  # 20 px semibold
    "subtitulo": (SANS, 10, False),  # 13 px
    "seccion": (SANS_SEMI, 11, False),  # 14 px semibold
    "etiqueta": (SANS_SEMI, 9, False),  # 12 px "medium": Segoe UI no trae Medium; se usa Semibold
    "texto": (SANS, 11, False),  # 14 px (texto de campo)
    "texto_chico": (SANS, 10, False),  # 13 px (ayudas, errores en línea)
    "mono": (MONO, 11, False),  # números en campos
    "resultado": (MONO_SEMI, 16, True),  # 22 px semibold mono
    "resultado_chico": (MONO_SEMI, 12, True),  # GMS (16 px)
    "boton": (SANS_SEMI, 10, False),  # 13 px semibold
    "boton_principal": (SANS_SEMI, 11, False),  # 14 px semibold
    "pestana": (SANS_SEMI, 11, False),  # 14 px
    "estado": (SANS, 9, False),  # 12 px
    "cuadricula": (MONO, 9, False),  # 12 px
    "cuadricula_enc": (SANS_SEMI, 9, False),  # 12 px semibold
}

_escala = 1.0
_fuentes: dict[str, tkfont.Font] = {}
_imagenes: dict[str, tk.PhotoImage] = {}
_minimo: dict[str, tuple[int, int]] = {}  # tamaño natural de las piezas 9-slice ampliadas


def u(px: float) -> int:
    """Píxeles de diseño (100 %) → píxeles reales a la escala vigente."""
    return int(round(px * _escala))


def escala() -> float:
    return _escala


def fuente(nombre: str) -> tkfont.Font:
    return _fuentes[nombre]


def imagen(nombre: str) -> tk.PhotoImage:
    return _imagenes[nombre]


def _familia(raiz: tk.Misc, candidatas: tuple[str, ...]) -> str | None:
    disponibles = {f.lower(): f for f in tkfont.families(raiz)}
    for c in candidatas:
        if c.lower() in disponibles:
            return disponibles[c.lower()]
    return None


def _crear_fuentes(raiz: tk.Misc) -> None:
    for nombre, (familias, puntos, negrita) in FUENTES.items():
        fam = _familia(raiz, familias)
        peso = "normal"
        if fam is None:  # familia con peso no disponible: base + negrita
            base = MONO if familias in (MONO_SEMI,) else SANS
            fam = _familia(raiz, base) or "TkDefaultFont"
            peso = "bold"
        elif negrita and familias not in (MONO_SEMI, SANS_SEMI):
            peso = "bold"
        clave = f"Coord{nombre.capitalize()}"
        try:
            f = tkfont.Font(root=raiz, name=clave, exists=True)
            f.configure(family=fam, size=puntos, weight=peso)
        except tk.TclError:
            f = tkfont.Font(root=raiz, name=clave, family=fam, size=puntos, weight=peso)
        _fuentes[nombre] = f


def _img(raiz: tk.Misc, nombre: str, lienzo: im.Lienzo, borde=None, tam: tuple[int, int] | None = None) -> str:
    """Crea la imagen. Si es una pieza 9-slice (``borde``), la amplía a ``tam`` repitiendo bordes y
    centro: ttk repite en mosaico (no estira) la zona central, y un centro de 2 px obligaría a cientos
    de dibujos con transparencia por control (muy lento, sobre todo dentro de un Canvas)."""
    foto = tk.PhotoImage(master=raiz, data=lienzo.base64(), format="png")
    if borde is not None and tam is not None:
        izq, arr, der, aba = (borde,) * 4 if isinstance(borde, int) else borde
        w, h = foto.width(), foto.height()
        W, H = max(w, tam[0]), max(h, tam[1])
        grande = tk.PhotoImage(master=raiz, width=W, height=H)
        xs = ((0, izq, 0, izq), (izq, w - der, izq, W - der), (w - der, w, W - der, W))
        ys = ((0, arr, 0, arr), (arr, h - aba, arr, H - aba), (h - aba, h, H - aba, H))
        for sx0, sx1, dx0, dx1 in xs:
            for sy0, sy1, dy0, dy1 in ys:
                if sx1 > sx0 and sy1 > sy0 and dx1 > dx0 and dy1 > dy0:
                    grande.tk.call(grande, "copy", foto, "-from", sx0, sy0, sx1, sy1, "-to", dx0, dy0, dx1, dy1)
        _minimo[str(grande)] = (w, h)
        foto = grande
    _imagenes[nombre] = foto
    return str(foto)

TAM_CONTROL = (240, 64)


def _elemento(st: ttk.Style, nombre: str, img: str, *estados, **kw) -> None:
    """Elemento de imagen cuyo tamaño mínimo es el de la pieza original (no el de la ampliada)."""
    mw, mh = _minimo.get(img, (0, 0))
    if mw:
        kw.setdefault("width", mw)
        kw.setdefault("height", mh)
    st.element_create(nombre, "image", img, *estados, **kw)  # px de las piezas ampliadas de campos y botones


# --------------------------------------------------------------------------- elementos dibujados
def _caja(raiz, nombre, relleno, borde, grosor=1.0, radio=None, lados="izq,der", ampliar=TAM_CONTROL) -> str:
    r = u(radio if radio is not None else T.radio_control)
    lado = 2 * (r + 2) + 2
    lz = im.rect_redondeado(lado, lado, r, relleno, borde, grosor * _escala if grosor else 0, lados)
    return _img(raiz, nombre, lz, r + 2, ampliar)


def _crear_elementos(raiz: tk.Misc, st: ttk.Style) -> None:
    rc = u(T.radio_control)
    b = rc + 2  # borde no estirable de las piezas 9-slice
    g1 = max(1.0, 1.0 * _escala) / _escala  # 1 px real como mínimo

    # Tarjeta
    rt = u(T.radio_tarjeta)
    tarjeta = _caja(raiz, "tarjeta", C.tarjeta, C.borde_tarjeta, g1, T.radio_tarjeta, ampliar=(600, 500))
    _elemento(st, "Tarjeta.fondo", tarjeta, border=rt + 2, padding=0, sticky="nsew")

    # Campo (Entry / Combobox / Spinbox)
    campo = _caja(raiz, "campo", C.control, C.borde_control, g1)
    campo_h = _caja(raiz, "campo_h", C.control, C.borde_control_hover, g1)
    campo_f = _caja(raiz, "campo_f", C.control, C.acento, T.grosor_foco)
    campo_e = _caja(raiz, "campo_e", C.control, C.error, T.grosor_error)
    campo_d = _caja(raiz, "campo_d", C.deshab_fondo, C.deshab_borde, g1)
    _elemento(st, "Campo.field", campo, ("invalid", campo_e), ("disabled", campo_d),
                      ("focus", campo_f), ("hover", campo_h), border=b, padding=u(1), sticky="nsew")
    flecha = _img(raiz, "flecha_abajo", im.icono("abajo", C.texto_sec, u(T.icono)))
    flecha_d = _img(raiz, "flecha_abajo_d", im.icono("abajo", C.deshab_borde, u(T.icono)))
    _elemento(st, "Campo.arrow", flecha, ("disabled", flecha_d), width=u(34), sticky="")
    arriba = _img(raiz, "flecha_arriba_chica", im.icono("arriba", C.texto_sec, u(12)))
    abajo = _img(raiz, "flecha_abajo_chica", im.icono("abajo", C.texto_sec, u(12)))
    _elemento(st, "Campo.uparrow", arriba, width=u(26), sticky="")
    _elemento(st, "Campo.downarrow", abajo, width=u(26), sticky="")

    # Botones
    sec = _caja(raiz, "bsec", C.control, C.borde_control, g1)
    sec_h = _caja(raiz, "bsec_h", C.hover, C.borde_control_hover, g1)
    sec_p = _caja(raiz, "bsec_p", C.presionado, C.borde_control_hover, g1)
    sec_f = _caja(raiz, "bsec_f", C.control, C.acento, T.grosor_foco)
    sec_fh = _caja(raiz, "bsec_fh", C.hover, C.acento, T.grosor_foco)
    sec_d = _caja(raiz, "bsec_d", C.deshab_fondo, C.deshab_borde, g1)
    _elemento(st, "Secundario.button", sec, ("disabled", sec_d), ("pressed", sec_p),
                      ("focus active", sec_fh), ("active", sec_h), ("focus", sec_f), border=b, padding=0, sticky="nsew")
    pri = _caja(raiz, "bpri", C.acento, None)
    pri_h = _caja(raiz, "bpri_h", C.acento_hover, None)
    pri_p = _caja(raiz, "bpri_p", C.acento_presionado, None)
    pri_f = _caja(raiz, "bpri_f", C.acento, C.acento_borde_foco, 2.0)
    pri_fh = _caja(raiz, "bpri_fh", C.acento_hover, C.acento_borde_foco, 2.0)
    pri_d = _caja(raiz, "bpri_d", C.acento_deshabilitado, None)
    _elemento(st, "Principal.button", pri, ("disabled", pri_d), ("pressed", pri_p),
                      ("focus active", pri_fh), ("active", pri_h), ("focus", pri_f), border=b, padding=0, sticky="nsew")
    dis = _caja(raiz, "bdis", None, None)
    dis_h = _caja(raiz, "bdis_h", C.discreto_hover, None)
    dis_p = _caja(raiz, "bdis_p", C.presionado, None)
    dis_f = _caja(raiz, "bdis_f", None, C.acento, T.grosor_foco)
    _elemento(st, "Discreto.button", dis, ("pressed", dis_p), ("active", dis_h), ("focus", dis_f),
                      border=b, padding=0, sticky="nsew")

    # Selector segmentado: piezas izquierda / centro / derecha
    for pos, lados in (("izq", "izq"), ("cen", ""), ("der", "der")):
        def pieza(sufijo, relleno, borde=C.borde_control, grosor=g1, foco=False):
            lz = im.rect_redondeado(2 * b + 2, 2 * b + 2, rc, relleno, borde, grosor * _escala, lados)
            n = 2 * b + 2
            if pos != "der":  # divisor a la derecha
                lz.pintar(im.caja(n - max(1.0, _escala), 0, n, n), C.borde_control)
            if foco:  # anillo de foco por dentro de la pieza
                div = 0 if pos == "der" else max(1, u(1))
                interior = im.caja(u(2), u(2), n - u(2) - div, n - u(2), max(2, rc - 2))
                lz.pintar(im.contorno(interior, T.grosor_foco * _escala), C.acento)
            return _img(raiz, f"seg_{pos}_{sufijo}", lz, b, (160, 48))

        normal = pieza("n", C.control)
        hover = pieza("h", C.hover)
        sel = pieza("s", C.acento_tinte)
        sel_f = pieza("sf", C.acento_tinte, foco=True)
        foc = pieza("f", C.control, foco=True)
        dsel = pieza("ds", C.divisor_fila, C.deshab_borde)
        des = pieza("d", C.deshab_fondo, C.deshab_borde)
        _elemento(st, f"Seg{pos}.button", normal, ("disabled selected", dsel), ("disabled", des),
                          ("focus selected", sel_f), ("selected", sel), ("focus", foc), ("active", hover),
                          border=b, padding=0, sticky="nsew")

    # Opciones (radio) y casillas con el acento exacto
    ti = u(T.indicador)
    rad = _img(raiz, "radio", im.icono("radio", C.indicador, ti))
    rad_h = _img(raiz, "radio_h", im.icono("radio", C.texto_sec, ti, C.hover))
    rad_f = _img(raiz, "radio_f", im.icono("radio", C.acento, ti))
    rad_s = _img(raiz, "radio_s", im.icono("radio_sel", C.acento, ti))
    rad_sf = _img(raiz, "radio_sf", im.icono("radio_sel", C.acento_borde_foco, ti))
    rad_d = _img(raiz, "radio_d", im.icono("radio", C.deshab_borde, ti, C.deshab_fondo))
    rad_ds = _img(raiz, "radio_ds", im.icono("radio_sel", C.deshab_borde, ti, C.deshab_fondo))
    _elemento(st, "Opcion.indicator", rad, ("disabled selected", rad_ds), ("disabled", rad_d),
                      ("focus selected", rad_sf), ("selected", rad_s), ("focus", rad_f), ("active", rad_h),
                      width=ti + u(10), sticky="w")
    cas = _img(raiz, "casilla", im.icono("casilla", C.indicador, ti))
    cas_h = _img(raiz, "casilla_h", im.icono("casilla", C.texto_sec, ti, C.hover))
    cas_f = _img(raiz, "casilla_f", im.icono("casilla", C.acento, ti))
    cas_s = _img(raiz, "casilla_s", im.icono("casilla_sel", C.acento, ti))
    cas_sf = _img(raiz, "casilla_sf", im.icono("casilla_sel", C.acento_borde_foco, ti))
    cas_d = _img(raiz, "casilla_d", im.icono("casilla", C.deshab_borde, ti, C.deshab_fondo))
    _elemento(st, "Casilla.indicator", cas, ("disabled", cas_d), ("focus selected", cas_sf),
                      ("selected", cas_s), ("focus", cas_f), ("active", cas_h), width=ti + u(10), sticky="w")

    # Pestañas: texto con barra de acento debajo de la activa
    n = u(12)
    barra = im.Lienzo(n, n).pintar(im.caja(0, n - u(3), n, n + 2, u(1.5)), C.acento)
    bt = (u(5), u(5), u(5), u(4))
    vacia = _img(raiz, "pest", im.Lienzo(n, n), bt, (240, 64))
    sel = _img(raiz, "pest_s", barra, bt, (240, 64))
    foco = im.Lienzo(n, n).pintar(im.caja(0, n - u(3), n, n + 2, u(1.5)), C.acento)
    foco.pintar(im.contorno(im.caja(0, 0, n, n - u(4), u(4)), max(1.0, _escala)), C.texto)
    sel_f = _img(raiz, "pest_sf", foco, bt, (240, 64))
    _elemento(st, "Pestana.tab", vacia, ("focus selected", sel_f), ("selected", sel),
                      border=(u(5), u(5), u(5), u(4)), padding=0, sticky="nsew")
    cliente = im.Lienzo(5, 5, C.fondo).pintar(im.caja(-1, 0, 6, max(1.0, _escala)), C.divisor)
    _elemento(st, "Pestana.client", _img(raiz, "pest_cliente", cliente, 2, (1200, 900)), border=2, padding=0, sticky="nsew")

    # Cuadrícula: encabezado y marco
    enc = im.Lienzo(6, 6, C.fondo)
    enc.pintar(im.caja(-1, 6 - max(1.0, _escala), 7, 7), C.divisor)
    enc.pintar(im.caja(6 - max(1.0, _escala), u(0) + 1, 7, 5), C.divisor)
    _elemento(st, "Cuadricula.cell", _img(raiz, "cuad_enc", enc, 2, (300, 64)), border=2, padding=0, sticky="nsew")
    marco = _caja(raiz, "cuad_marco", C.tarjeta, C.borde_tarjeta, g1, ampliar=(900, 600))
    _elemento(st, "Cuadricula.field", marco, border=b, padding=max(1, u(1)), sticky="nsew")

    # Barra de progreso delgada
    rp = u(T.alto_progreso) / 2
    lp = u(T.alto_progreso) * 3
    bp = max(1, int(rp))
    canal = _img(raiz, "prog_canal", im.rect_redondeado(lp, u(T.alto_progreso), rp, C.divisor, None), (bp, 0, bp, 0), (1200, 1))
    barra_p = _img(raiz, "prog_barra", im.rect_redondeado(lp, u(T.alto_progreso), rp, C.acento, None), (bp, 0, bp, 0), (1200, 1))
    _elemento(st, "Delgada.trough", canal, border=(bp, 0, bp, 0), padding=0, sticky="ew")
    _elemento(st, "Delgada.pbar", barra_p, border=(bp, 0, bp, 0), padding=0, sticky="nsew")

    # Íconos sueltos (en etiquetas y botones)
    ti = u(T.icono)
    for nombre, color in (
        ("copiar", C.texto), ("copiar_d", C.deshab_texto), ("ajustes", C.texto), ("check", C.exito),
        ("alerta", C.error), ("aviso", C.error), ("aviso_ambar", C.aviso), ("cruz", C.error), ("carpeta", C.texto),
    ):
        forma = {"copiar_d": "copiar", "aviso_ambar": "aviso"}.get(nombre, nombre)
        _img(raiz, f"ic_{nombre}", im.icono(forma, color, ti))


# --------------------------------------------------------------------------- estilos
def _pad_vertical(nombre_fuente: str, alto: int, extra: int = 0) -> int:
    lin = fuente(nombre_fuente).metrics("linespace")
    return max(0, (alto - lin - extra) // 2)


def _crear_estilos(raiz: tk.Misc, st: ttk.Style) -> None:
    F = fuente
    st.configure(".", background=C.fondo, foreground=C.texto, font=F("texto"), focuscolor=C.acento,
                 selectbackground=C.acento_tinte, selectforeground=C.texto, troughcolor=C.fondo)
    st.configure("TFrame", background=C.fondo)
    st.configure("TLabel", background=C.fondo, foreground=C.texto, font=F("texto"))
    st.configure("Tarjeta.TFrame", background=C.tarjeta)
    st.layout("Tarjeta.TFrame", [("Tarjeta.fondo", {"sticky": "nsew"})])
    st.configure("Blanco.TFrame", background=C.tarjeta)
    st.configure("Estado.TFrame", background=C.barra_estado)
    st.configure("Pie.TFrame", background=C.fondo)

    # Textos sobre el fondo de la ventana
    st.configure("Titulo.TLabel", font=F("titulo"), foreground=C.texto, background=C.fondo)
    st.configure("Subtitulo.TLabel", font=F("subtitulo"), foreground=C.texto_sec, background=C.fondo)
    st.configure("Fondo.TLabel", font=F("texto_chico"), foreground=C.texto_sec, background=C.fondo)
    st.configure("FondoError.TLabel", font=F("texto_chico"), foreground=C.error, background=C.fondo)
    st.configure("FondoOk.TLabel", font=F("texto_chico"), foreground=C.exito, background=C.fondo)
    st.configure("FondoAviso.TLabel", font=F("texto_chico"), foreground=C.aviso, background=C.fondo)
    # Textos dentro de tarjetas
    blanco = {"background": C.tarjeta}
    st.configure("Tarjeta.TLabel", font=F("texto"), foreground=C.texto, **blanco)
    st.configure("TarjetaError.TLabel", font=F("texto"), foreground=C.error, **blanco)
    st.configure("Seccion.TLabel", font=F("seccion"), foreground=C.texto, **blanco)
    st.configure("Etiqueta.TLabel", font=F("etiqueta"), foreground=C.texto_sec, **blanco)
    st.configure("EtiquetaError.TLabel", font=F("etiqueta"), foreground=C.error, **blanco)
    st.configure("Ayuda.TLabel", font=F("texto_chico"), foreground=C.texto_sec, **blanco)
    st.configure("ErrorCampo.TLabel", font=F("texto_chico"), foreground=C.error, **blanco)
    st.configure("Simbolo.TLabel", font=F("mono"), foreground=C.texto_sec, **blanco)
    st.configure("ResNombre.TLabel", font=F("texto_chico"), foreground=C.texto_sec, **blanco)
    st.configure("ResValor.TLabel", font=F("resultado"), foreground=C.texto, **blanco)
    st.configure("ResValorChico.TLabel", font=F("resultado_chico"), foreground=C.texto, **blanco)
    st.configure("Opcion.TLabel", font=F("texto"), foreground=C.texto, **blanco)
    # Barra de estado
    est = {"background": C.barra_estado, "font": F("estado")}
    st.configure("Estado.TLabel", foreground=C.texto, **est)
    st.configure("EstadoOk.TLabel", foreground=C.exito, **est)
    st.configure("EstadoError.TLabel", foreground=C.error, **est)
    st.configure("EstadoAviso.TLabel", foreground=C.aviso, **est)
    st.configure("EstadoSec.TLabel", foreground=C.texto_sec, **est)

    # Campos
    pad_h = u(11)
    pv = _pad_vertical("texto", u(T.alto_campo), 2 * max(1, u(1)))
    st.layout("Campo.TEntry", [("Campo.field", {"sticky": "nsew", "children": [
        ("Entry.padding", {"sticky": "nsew", "children": [("Entry.textarea", {"sticky": "nsew"})]})]})])
    st.configure("Campo.TEntry", padding=(pad_h, pv, pad_h, pv), foreground=C.texto, fieldbackground=C.control,
                 background=C.tarjeta, insertcolor=C.texto, insertwidth=max(1, u(1)),
                 selectbackground=C.acento_tinte, selectforeground=C.texto)
    st.map("Campo.TEntry", foreground=[("disabled", C.deshab_texto)])
    st.layout("Campo.TCombobox", [("Campo.field", {"sticky": "nsew", "children": [
        ("Campo.arrow", {"side": "right", "sticky": "ns"}),
        ("Combobox.padding", {"sticky": "nsew", "children": [("Combobox.textarea", {"sticky": "nsew"})]})]})])
    st.configure("Campo.TCombobox", padding=(pad_h, pv, 0, pv), foreground=C.texto, fieldbackground=C.control,
                 background=C.tarjeta, arrowsize=u(12), insertcolor=C.texto)
    st.map("Campo.TCombobox", foreground=[("disabled", C.deshab_texto)], fieldbackground=[("readonly", C.control)],
           selectbackground=[("readonly", C.control), ("!readonly", C.acento_tinte)],
           selectforeground=[("readonly", C.texto), ("!readonly", C.texto)])
    st.layout("Campo.TSpinbox", [("Campo.field", {"sticky": "nsew", "children": [
        ("null", {"side": "right", "sticky": "ns", "children": [
            ("Campo.uparrow", {"side": "top", "sticky": "nsew"}),
            ("Campo.downarrow", {"side": "bottom", "sticky": "nsew"})]}),
        ("Spinbox.padding", {"sticky": "nsew", "children": [("Spinbox.textarea", {"sticky": "nsew"})]})]})])
    st.configure("Campo.TSpinbox", padding=(pad_h, pv, 0, pv), foreground=C.texto, fieldbackground=C.control,
                 background=C.tarjeta, insertcolor=C.texto)
    # Editores de celda de la cuadrícula (compactos: caben en filas de 32 px)
    pc = max(1, u(1))
    st.layout("Celda.TEntry", st.layout("Campo.TEntry"))
    st.configure("Celda.TEntry", padding=(u(6), pc, u(6), pc), foreground=C.texto, fieldbackground=C.control,
                 background=C.tarjeta, insertcolor=C.texto, selectbackground=C.acento_tinte, selectforeground=C.texto)
    st.layout("Celda.TCombobox", st.layout("Campo.TCombobox"))
    st.configure("Celda.TCombobox", padding=(u(6), pc, 0, pc), foreground=C.texto, fieldbackground=C.control,
                 background=C.tarjeta, arrowsize=u(12))
    st.map("Celda.TCombobox", fieldbackground=[("readonly", C.control)],
           selectbackground=[("readonly", C.control)], selectforeground=[("readonly", C.texto)])
    # Lista desplegable de los combos
    raiz.option_add("*TCombobox*Listbox.font", F("texto"))
    raiz.option_add("*TCombobox*Listbox.background", C.control)
    raiz.option_add("*TCombobox*Listbox.foreground", C.texto)
    raiz.option_add("*TCombobox*Listbox.selectBackground", C.acento_tinte)
    raiz.option_add("*TCombobox*Listbox.selectForeground", C.texto)
    raiz.option_add("*TCombobox*Listbox.borderWidth", 0)

    # Botones
    def boton(estilo, elemento, fnt, alto, fondo, color, color_dis, pad_x):
        pvb = _pad_vertical(fnt, u(alto))
        st.layout(estilo, [(elemento, {"sticky": "nsew", "children": [
            ("Button.padding", {"sticky": "nsew", "children": [("Button.label", {"sticky": "nsew"})]})]})])
        st.configure(estilo, font=F(fnt), padding=(u(pad_x), pvb, u(pad_x), pvb), background=fondo,
                     foreground=color, anchor="center", relief="flat", borderwidth=0)
        st.map(estilo, foreground=[("disabled", color_dis)], background=[("!disabled", fondo)])

    boton("Principal.TButton", "Principal.button", "boton_principal", T.alto_principal, C.fondo, "#FFFFFF", "#FFFFFF", 24)
    boton("Secundario.TButton", "Secundario.button", "boton", T.alto_principal, C.fondo, C.texto, C.deshab_texto, 20)
    boton("Discreto.TButton", "Discreto.button", "boton", T.alto_principal, C.fondo, C.texto, C.deshab_texto, 12)
    boton("Copiar.TButton", "Secundario.button", "boton", T.alto_copiar, C.tarjeta, C.texto, C.deshab_texto, 12)
    boton("Tarjeta.TButton", "Secundario.button", "boton", T.alto_campo, C.tarjeta, C.texto, C.deshab_texto, 16)
    boton("Dialogo.Principal.TButton", "Principal.button", "boton_principal", T.alto_principal, C.fondo, "#FFFFFF",
          "#FFFFFF", 24)
    for e in ("Copiar.TButton", "Tarjeta.TButton", "Discreto.TButton", "Secundario.TButton"):
        st.configure(e, compound="left")

    # Selector segmentado
    for pos in ("izq", "cen", "der"):
        estilo = f"Seg{pos}.TRadiobutton"
        pvs = _pad_vertical("boton", u(T.alto_segmento))
        st.layout(estilo, [(f"Seg{pos}.button", {"sticky": "nsew", "children": [
            ("Radiobutton.padding", {"sticky": "nsew", "children": [("Radiobutton.label", {"sticky": ""})]})]})])
        st.configure(estilo, font=F("boton"), padding=(u(8), pvs, u(8), pvs), background=C.tarjeta,
                     foreground=C.texto, anchor="center")
        st.map(estilo, foreground=[("disabled", C.deshab_texto), ("selected", C.acento)],
               background=[("!disabled", C.tarjeta)])

    # Opciones y casillas
    for estilo, ind, base in (("Opcion.TRadiobutton", "Opcion.indicator", "Radiobutton"),
                              ("Casilla.TCheckbutton", "Casilla.indicator", "Checkbutton")):
        st.layout(estilo, [(f"{base}.padding", {"sticky": "nsew", "children": [
            (ind, {"side": "left", "sticky": ""}),
            (f"{base}.label", {"side": "left", "sticky": "w"})]})])
        st.configure(estilo, font=F("texto"), background=C.tarjeta, foreground=C.texto, padding=(0, u(4)))
        st.map(estilo, foreground=[("disabled", C.deshab_texto)], background=[("!disabled", C.tarjeta)])

    # Pestañas
    st.layout("App.TNotebook", [("Pestana.client", {"sticky": "nsew"})])
    st.configure("App.TNotebook", background=C.fondo, tabmargins=(u(T.margen_h), u(8), u(T.margen_h), 0),
                 padding=(0, max(1, u(1)), 0, 0), borderwidth=0)
    st.layout("App.TNotebook.Tab", [("Pestana.tab", {"sticky": "nsew", "children": [
        ("Notebook.padding", {"side": "top", "sticky": "nsew", "children": [
            ("Notebook.label", {"side": "top", "sticky": ""})]})]})])
    st.configure("App.TNotebook.Tab", font=F("pestana"), padding=(u(16), u(10), u(16), u(12)),
                 background=C.fondo, foreground=C.texto_sec, focuscolor=C.acento)
    st.map("App.TNotebook.Tab", foreground=[("selected", C.acento), ("active", C.texto)],
           background=[("!disabled", C.fondo)], expand=[("selected", (0, 0, 0, 0))])

    # Cuadrícula
    st.layout("Cuadricula.Treeview", [("Cuadricula.field", {"sticky": "nsew", "children": [
        ("Treeview.padding", {"sticky": "nsew", "children": [("Treeview.treearea", {"sticky": "nsew"})]})]})])
    st.configure("Cuadricula.Treeview", background=C.tarjeta, fieldbackground=C.tarjeta, foreground=C.texto,
                 font=F("cuadricula"), rowheight=u(T.alto_fila_cuadricula), borderwidth=0, padding=0)
    st.map("Cuadricula.Treeview", background=[("selected", C.acento_tinte)], foreground=[("selected", C.texto)])
    st.layout("Cuadricula.Treeview.Heading", [("Cuadricula.cell", {"sticky": "nsew", "children": [
        ("Treeheading.padding", {"sticky": "nsew", "children": [
            ("Treeheading.image", {"side": "right", "sticky": ""}),
            ("Treeheading.text", {"sticky": "we"})]})]})])
    st.configure("CuadriculaVacia.TLabel", font=F("texto"), foreground=C.texto_sec, background=C.tarjeta)
    st.configure("Cuadricula.Treeview.Heading", font=F("cuadricula_enc"), foreground=C.texto_sec,
                 background=C.fondo, padding=(u(8), u(6)), relief="flat")
    st.map("Cuadricula.Treeview.Heading", background=[("!disabled", C.fondo)], foreground=[("!disabled", C.texto_sec)])

    # Progreso delgado
    st.layout("Delgada.Horizontal.TProgressbar", [("Delgada.trough", {"sticky": "nsew", "children": [
        ("Delgada.pbar", {"side": "left", "sticky": "ns"})]})])
    st.configure("Delgada.Horizontal.TProgressbar", thickness=u(T.alto_progreso), background=C.fondo,
                 troughcolor=C.fondo, borderwidth=0)

    st.configure("Vertical.TScrollbar", background=C.fondo)
    st.configure("Horizontal.TScrollbar", background=C.fondo)


# --------------------------------------------------------------------------- aplicación
def ajustar_escala(raiz: tk.Misc) -> float:
    """Factor respecto de 100 % (96 ppp) según ``tk scaling`` (pixeles por punto)."""
    return float(raiz.tk.call("tk", "scaling")) * 72.0 / 96.0


def aplicar(raiz: tk.Misc) -> None:
    """Aplica sv-ttk (claro) y los estilos propios. Idempotente por intérprete y escala."""
    global _escala
    principal = raiz._root()  # type: ignore[attr-defined]
    esc = ajustar_escala(principal)
    if getattr(principal, "_coord_tema", None) == esc:
        return
    _escala = esc
    try:
        import sv_ttk

        sv_ttk.set_theme("light", principal)
        principal.update_idletasks()  # deja correr <<ThemeChanged>> de sv-ttk antes de ajustar
        # sv-ttk vuelve a llamar a tk_setPalette en cada <<ThemeChanged>> (que ttk emite también al
        # crear estilos) y recolorea todos los widgets; los colores ya están en los estilos propios.
        principal.bind_class(principal.winfo_class(), "<<ThemeChanged>>", "")
    except Exception:  # noqa: BLE001 - sin sv-ttk se sigue con "clam" y los elementos propios
        ttk.Style(principal).theme_use("clam")
    # sv-ttk llama a tk_setPalette, que deja *background/*foreground en la base de opciones; las
    # ttk.Label lo tomarían como opción propia y anularían el estilo. Se vacían para TLabel.
    for opcion in ("background", "foreground"):
        principal.option_add(f"*TLabel.{opcion}", "", "userDefault")
    st = ttk.Style(principal)
    _crear_fuentes(principal)
    _crear_elementos(principal, st)
    _crear_estilos(principal, st)
    principal._coord_tema = esc  # type: ignore[attr-defined]
