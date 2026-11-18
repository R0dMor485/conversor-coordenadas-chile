"""Pestaña 1: "Calcular Coordenadas" (un punto).

Validación por campo en la interfaz (mensajes cortos en línea) usando los mismos analizadores del
núcleo; los errores que no son de un campo (p. ej. sin parámetros para esa latitud) se muestran en la
barra de estado y arriba de la tarjeta Salida.
"""
from __future__ import annotations

import re
import tkinter as tk
from tkinter import ttk

from ..core import constantes as CT
from ..core.conversion import hay_cambio_datum
from ..core.errores import ErrorAmbiguo, ErrorCoordenada, ErrorRango
from ..core.parseo import (
    RANGO_ESTE, RANGO_NORTE_AMPLIADO, RANGO_NORTE_CONTINENTAL, parse_angulo, parse_gms_campos, parse_utm, parse_zona,
)
from ..core.servicio import convertir_formulario, separador_par, textos_resultado
from . import componentes as K
from . import tema
from .comun import CLAVE_POR_ETIQUETA, ETIQUETA_POR_CLAVE, FORMATOS_SALIDA, combo_datum, copiar
from .panel_salida import PanelSalida
from .tema import T, u

MSG_VACIO = "Ingresa un valor."
MSG_NUMEROS = "Ingresa solo números."
MSG_FUERA = "Fuera del rango de Chile continental."
MSG_FUERA_AMPLIADO = "Fuera del rango admitido sin cambio de datum."
MSG_REVISAR = "Revisa el campo marcado en rojo"
MSG_LISTA = "Conversión lista"
AYUDA_UTM = "Huso 18 o 19 (Chile continental)."
AYUDA_POSITIVOS = "Los valores positivos se interpretan como S y O."
AYUDA_SIGNO = "Usa signo negativo para S y O."

_SOLO_NUMERICO = re.compile(r"^[\s\d.,+\-]*$")
_ANGULO_PERMITIDO = re.compile(r"^[\s\d.,+\-°º'’\"”NSEOWnseow]*$")
_ENTERO = re.compile(r"^[+\-]?\s*\d+$")
_CON_DECIMALES = re.compile(r"^[+\-]?\s*(\d+[.,]\d*|[.,]\d+)$")
_SEGUNDOS = re.compile(r"^(\d+([.,]\d+)?|[.,]\d+)$")


def _msg_numero(texto: str, e: ErrorCoordenada) -> str:
    if isinstance(e, ErrorAmbiguo):
        return e.mensaje
    if not _SOLO_NUMERICO.match(texto) or not re.search(r"\d", texto):
        return MSG_NUMEROS
    return e.mensaje


class TabIndividual(ttk.Frame):
    def __init__(self, padre, app):
        super().__init__(padre, style="TFrame")
        self.app = app
        u_ = app.op.ultimas
        self.resultado = None
        mh, mv, sep, sc = u(T.margen_h), u(T.margen_v), u(T.sep), u(T.sep_campos)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        K.Encabezado(self, "Convertir coordenadas", "Transformación de datum y proyección UTM para Chile continental.") \
            .grid(row=0, column=0, sticky="ew", padx=mh, pady=(mv, u(12)))
        self.area = K.AreaDesplazable(self)
        self.area.grid(row=1, column=0, sticky="nsew")
        cont = self.area.interior
        cont.columnconfigure(0, weight=1, uniform="tarjetas")
        cont.columnconfigure(1, weight=1, uniform="tarjetas")
        cont.rowconfigure(0, weight=1)

        # ------------------------------------------------------------- Entrada
        self.v_formato = tk.StringVar(value=u_.get("t1_formato_entrada") if u_.get("t1_formato_entrada") in ("utm", "decimal", "gms") else "utm")
        self.v_datum_in = tk.StringVar(value=ETIQUETA_POR_CLAVE.get(u_.get("t1_datum_entrada"), ETIQUETA_POR_CLAVE["PSAD56"]))
        self.v = {k: tk.StringVar() for k in ("norte", "este", "lat", "lon", "lat_g", "lat_m", "lat_s", "lon_g", "lon_m", "lon_s")}
        zona = str(u_.get("t1_zona_entrada", "19"))
        self.v["zona"] = tk.StringVar(value=zona if zona in ("18", "19") else "19")
        self.v["lat_h"] = tk.StringVar(value="S")
        self.v["lon_h"] = tk.StringVar(value="O")

        te = K.Tarjeta(cont, "Entrada")
        te.grid(row=0, column=0, sticky="nsew", padx=(mh, sep // 2))
        ce = te.cuerpo
        c = K.CampoConError(ce, "Datum")
        self.cb_datum_in = c.agregar(combo_datum(c.cuerpo, self.v_datum_in))
        self.cb_datum_in.grid(row=0, column=0, sticky="ew")
        self.cb_datum_in.bind("<<ComboboxSelected>>", lambda e: self._cambio_entrada(), add="+")
        c.grid(row=0, column=0, sticky="ew", pady=(0, sep))
        c = K.CampoConError(ce, "Formato")
        self.sel_formato = K.SelectorSegmentado(c.cuerpo, self.v_formato, FORMATOS_SALIDA, self._cambio_formato)
        self.sel_formato.grid(row=0, column=0, sticky="ew")
        c.grid(row=1, column=0, sticky="ew", pady=(0, sep))
        self.cuerpo = ttk.Frame(ce, style="Blanco.TFrame")
        self.cuerpo.grid(row=2, column=0, sticky="ew")
        self.cuerpo.columnconfigure(0, weight=1)
        self.campos: dict[str, K.CampoConError] = {}
        self.ent: dict[str, ttk.Widget] = {}

        def campo(padre, clave, etiqueta, mono=True):
            cc = K.CampoConError(padre, etiqueta, al_editar=self._error_corregido)
            e = cc.agregar(K.entrada(cc.cuerpo, self.v[clave], mono=mono), self.v[clave])
            e.grid(row=0, column=0, sticky="ew")
            self.campos[clave], self.ent[clave] = cc, e
            return cc

        def dos_columnas(f):
            f.columnconfigure(0, weight=1, uniform="c2")
            f.columnconfigure(1, weight=1, uniform="c2")

        # U.T.M.
        self.f_utm = ttk.Frame(self.cuerpo, style="Blanco.TFrame")
        dos_columnas(self.f_utm)
        campo(self.f_utm, "norte", "Norte (m)").grid(row=0, column=0, sticky="new", padx=(0, sc // 2))
        campo(self.f_utm, "este", "Este (m)").grid(row=0, column=1, sticky="new", padx=(sc // 2, 0))
        cz = K.CampoConError(self.f_utm, "Huso", al_editar=self._error_corregido)
        self.cb_zona = cz.agregar(K.combo(cz.cuerpo, self.v["zona"], ["18", "19"], editable=True, mono=True), self.v["zona"])
        self.cb_zona.grid(row=0, column=0, sticky="ew")
        self.campos["zona"], self.ent["zona"] = cz, self.cb_zona
        cz.grid(row=1, column=0, sticky="new", padx=(0, sc // 2), pady=(sep, 0))
        ttk.Label(self.f_utm, text=AYUDA_UTM, style="Ayuda.TLabel").grid(row=2, column=0, columnspan=2, sticky="w", pady=(sep, 0))

        # Decimal
        self.f_dec = ttk.Frame(self.cuerpo, style="Blanco.TFrame")
        dos_columnas(self.f_dec)
        campo(self.f_dec, "lat", "Latitud").grid(row=0, column=0, sticky="new", padx=(0, sc // 2))
        campo(self.f_dec, "lon", "Longitud").grid(row=0, column=1, sticky="new", padx=(sc // 2, 0))
        self.l_ayuda_dec = ttk.Label(self.f_dec, style="Ayuda.TLabel", justify="left")
        self.l_ayuda_dec.grid(row=1, column=0, columnspan=2, sticky="w", pady=(sep, 0))

        # GMS: grados, minutos, segundos y hemisferio por fila
        self.f_gms = ttk.Frame(self.cuerpo, style="Blanco.TFrame")
        self.f_gms.columnconfigure(0, weight=1)
        for fila, (eje, nombre, hemis) in enumerate((("lat", "Latitud", ("S", "N")), ("lon", "Longitud", ("O", "E")))):
            cc = K.CampoConError(self.f_gms, nombre, al_editar=self._error_corregido)
            cc.grid(row=fila, column=0, sticky="ew", pady=(0 if fila == 0 else sep, 0))
            col = 0
            for parte, simb, peso in (("g", "°", 3), ("m", "'", 2), ("s", '"', 4)):
                clave = f"{eje}_{parte}"
                e = cc.agregar(K.entrada(cc.cuerpo, self.v[clave], mono=True, width=2), self.v[clave])
                e.grid(row=0, column=col, sticky="ew")
                cc.cuerpo.columnconfigure(col, weight=peso, uniform=None)
                ttk.Label(cc.cuerpo, text=simb, style="Simbolo.TLabel").grid(row=0, column=col + 1, sticky="w", padx=(u(3), u(8)))
                self.ent[clave] = e
                col += 2
            h = cc.agregar(K.combo(cc.cuerpo, self.v[f"{eje}_h"], hemis, mono=True, width=2), self.v[f"{eje}_h"])
            h.grid(row=0, column=col, sticky="e")
            self.ent[f"{eje}_h"] = h
            self.campos[f"g{eje}"] = cc
        self.l_ayuda_gms = ttk.Label(self.f_gms, style="Ayuda.TLabel", justify="left")
        self.l_ayuda_gms.grid(row=2, column=0, sticky="w", pady=(sep, 0))

        # ------------------------------------------------------------- Salida
        ts = K.Tarjeta(cont, "Salida")
        ts.grid(row=0, column=1, sticky="nsew", padx=(sep // 2, mh))
        cs = ts.cuerpo
        self.l_msg = ttk.Label(cs, text="", style="ErrorCampo.TLabel", image=tema.imagen("ic_cruz"), compound="left",
                               justify="left", anchor="nw")
        self.panel = PanelSalida(cs, app, "t1_", self._cambio_salida)
        # ancho tomado del panel (hermano), no de la tarjeta, para no realimentar la geometría
        self.panel.bind("<Configure>", lambda e: self.l_msg.configure(wraplength=max(u(80), e.width - u(28))), add="+")
        self.panel.grid(row=1, column=0, sticky="ew")
        K.divisor(cs).grid(row=2, column=0, sticky="ew", pady=(sep, 0))
        self.res = ttk.Frame(cs, style="Blanco.TFrame")
        self.res.grid(row=3, column=0, sticky="nsew")
        self.res.columnconfigure(0, weight=1)
        self.o = {k: tk.StringVar() for k in ("norte", "este", "zona", "lat", "lon", "glat", "glon")}
        self.filas_res: dict[str, K.FilaResultado] = {}

        def bloque(filas, chica, texto_par, accion_par):
            f = ttk.Frame(self.res, style="Blanco.TFrame")
            f.columnconfigure(0, weight=1)
            for i, (clave, nombre, accion) in enumerate(filas):
                fila = K.FilaResultado(f, nombre, self.o[clave], accion, chica=chica, linea=i < len(filas) - 1)
                fila.grid(row=i, column=0, sticky="ew")
                self.filas_res[clave] = fila
            b = K.boton(f, texto_par, accion_par, "Tarjeta.TButton", icono="copiar")
            b.grid(row=len(filas), column=0, sticky="ew", pady=(sep, 0))
            return f, b

        self.r_utm, self.b_par_utm = bloque(
            [("norte", "Norte", self._copiar_norte), ("este", "Este", self._copiar_este), ("zona", "Huso", None)],
            False, "Copiar todo", self._copiar_ne)
        self.r_dec, self.b_par_dec = bloque(
            [("lat", "Latitud", self._copiar_lat), ("lon", "Longitud", self._copiar_lon)], False, "Copiar todo",
            self._copiar_latlon)
        self.r_gms, self.b_par_gms = bloque(
            [("glat", "Latitud", self._copiar_glat), ("glon", "Longitud", self._copiar_glon)], True,
            "Copiar todo", self._copiar_gms)

        # ------------------------------------------------------------- fila inferior
        fa = ttk.Frame(self, style="TFrame")
        fa.grid(row=2, column=0, sticky="ew", padx=mh, pady=(u(12), u(16)))
        self.b_ajustes = K.boton(fa, "Ajustes", self.app.abrir_ajustes, "Discreto.TButton", icono="ajustes")
        self.b_ajustes.pack(side="left")
        self.b_convertir = K.boton(fa, "Convertir", self.convertir, "Principal.TButton")
        self.b_limpiar = K.boton(fa, "Limpiar", self.limpiar, "Secundario.TButton")
        self.b_convertir.pack(side="right")
        self.b_limpiar.pack(side="right", padx=(0, sc))
        self.b_limpiar.lower(self.b_convertir)  # orden de tabulación: Ajustes, Limpiar, Convertir

        self._cambio_formato(guardar=False)
        self._actualizar_exclusion(avisar=False)
        self._sin_resultado()
        self.refrescar()

    # ------------------------------------------------------------------ selección y opciones
    @property
    def datum_entrada(self) -> str:
        return CLAVE_POR_ETIQUETA[self.v_datum_in.get()]

    def _guardar_sel(self) -> None:
        u_ = self.app.op.ultimas
        u_["t1_formato_entrada"] = self.v_formato.get()
        u_["t1_datum_entrada"] = self.datum_entrada
        z = self.v["zona"].get().strip()
        if z in ("18", "19"):
            u_["t1_zona_entrada"] = z
        self.app.guardar_opciones()

    def _cambio_formato(self, guardar: bool = True) -> None:
        for f in (self.f_utm, self.f_dec, self.f_gms):
            f.grid_remove()
        {"utm": self.f_utm, "decimal": self.f_dec, "gms": self.f_gms}[self.v_formato.get()].grid(row=0, column=0, sticky="ew")
        self._limpiar_errores()
        if guardar:
            # valores por defecto según el formato de entrada: UTM → PSAD56 a WGS84 (UTM);
            # decimal o GMS → entrada WGS84 y salida UTM WGS84
            self.v_datum_in.set(ETIQUETA_POR_CLAVE["PSAD56" if self.v_formato.get() == "utm" else "SIRGAS"])
            self.panel.aplicar(datum="SIRGAS", formato="utm")
            self._actualizar_exclusion(avisar=False)
            self._sin_resultado()
            self._guardar_sel()
            self.app.estado.listo()

    def _actualizar_exclusion(self, avisar: bool = True) -> bool:
        """Con entrada y salida en UTM el datum de salida no puede ser el de entrada (no habría cambio);
        con salida decimal o GMS, o entrada decimal o GMS (UTM del mismo datum), sí. Devuelve True si
        hubo que cambiar el datum de salida."""
        ambos_utm = self.v_formato.get() == "utm" and self.panel.formato == "utm"
        cambio = self.panel.excluir(self.datum_entrada if ambos_utm else None)
        if cambio and avisar:
            self.app.estado_temporal(f"Datum de salida cambiado a {self.panel.v_datum.get()}", tipo="info")
        return cambio

    def _cambio_entrada(self) -> None:
        """Se eligió otro datum de entrada."""
        self._guardar_sel()
        if self._actualizar_exclusion():
            self.panel._cambio()

    def _cambio_salida(self) -> None:
        self._actualizar_exclusion()
        self.app.guardar_opciones()
        if self.resultado is not None:
            self.convertir()
        else:
            self._pintar()

    def refrescar(self) -> None:
        """Llamado al cambiar los ajustes globales."""
        ayuda = AYUDA_POSITIVOS if self.app.op.positivos_sur_oeste else AYUDA_SIGNO
        self.l_ayuda_dec.configure(text=ayuda)
        self.l_ayuda_gms.configure(text=ayuda)
        if self.resultado is not None:
            self.convertir()
        else:
            self._pintar()

    def al_enter(self) -> None:
        self.convertir()

    def _campos(self) -> dict:
        return {k: v.get() for k, v in self.v.items()}

    # ------------------------------------------------------------------ validación por campo
    def _limpiar_errores(self) -> None:
        for c in self.campos.values():
            c.limpiar_error(avisar=False)
        if self.app.estado.tipo == "revisar":
            self.app.estado.listo()

    def _error_corregido(self) -> None:
        if self.app.estado.tipo == "revisar" and not any(c.error for c in self.campos.values()):
            self.app.estado.listo()

    def _rango_geo(self, eje: str, valor: float, cambio: bool) -> str | None:
        if valor > 0:
            return MSG_FUERA if cambio else MSG_FUERA_AMPLIADO
        g = -valor
        if eje == "lat":
            if not cambio and not (CT.LAT_AMPLIADA_SUR_MIN <= g <= CT.LAT_AMPLIADA_SUR_MAX):
                return MSG_FUERA_AMPLIADO
            return None  # con cambio de datum la latitud la acotan las franjas (mensaje del núcleo)
        if cambio:
            return None if CT.LON_CONTINENTAL_OESTE_MIN < g <= CT.LON_CONTINENTAL_OESTE_MAX else MSG_FUERA
        return None if CT.LON_AMPLIADA_OESTE_MIN <= g <= CT.LON_AMPLIADA_OESTE_MAX else MSG_FUERA_AMPLIADO

    def _validar_utm(self, cambio: bool) -> list:
        errores = []
        for eje in ("norte", "este"):
            t = self.v[eje].get()
            lo, hi = RANGO_ESTE if eje == "este" else (RANGO_NORTE_CONTINENTAL if cambio else RANGO_NORTE_AMPLIADO)
            rango = f"Debe estar entre {lo:.0f} y {hi:.0f}."
            if not t.strip():
                errores.append((eje, MSG_VACIO))
                continue
            try:
                valor = parse_utm(t, eje, not cambio)
            except ErrorRango:
                errores.append((eje, rango))
                continue
            except ErrorCoordenada as e:
                errores.append((eje, _msg_numero(t, e)))
                continue
            if not lo <= valor <= hi:
                errores.append((eje, rango))
        t = self.v["zona"].get()
        if not t.strip():
            errores.append(("zona", MSG_VACIO))
        else:
            try:
                z = parse_zona(t)
                if cambio and z not in CT.HUSOS_CONTINENTALES:
                    errores.append(("zona", "Debe ser 18 o 19."))
                elif not cambio and not CT.HUSO_AMPLIADO_MIN <= z <= CT.HUSO_AMPLIADO_MAX:
                    errores.append(("zona", f"Debe estar entre {CT.HUSO_AMPLIADO_MIN} y {CT.HUSO_AMPLIADO_MAX}."))
            except ErrorCoordenada as e:
                errores.append(("zona", MSG_NUMEROS if not re.search(r"\d", t) else e.mensaje))
        return [(self.campos[k], m, [self.ent[k]]) for k, m in errores]

    def _validar_decimal(self, cambio: bool) -> list:
        errores = []
        for eje in ("lat", "lon"):
            t = self.v[eje].get()
            msg = None
            if not t.strip():
                msg = MSG_VACIO
            else:
                try:
                    a = parse_angulo(t, eje, self.app.op.positivos_sur_oeste)
                    msg = self._rango_geo(eje, a.valor, cambio)
                except ErrorRango:
                    msg = MSG_FUERA if cambio else MSG_FUERA_AMPLIADO
                except ErrorCoordenada as e:
                    msg = MSG_NUMEROS if not _ANGULO_PERMITIDO.match(t) or not re.search(r"\d", t) else e.mensaje
            if msg:
                errores.append((self.campos[eje], msg, [self.ent[eje]]))
        return errores

    def _validar_gms(self, cambio: bool) -> list:
        errores = []
        for eje in ("lat", "lon"):
            g, m, s = (self.v[f"{eje}_{p}"].get().strip() for p in "gms")
            eg, em, es = (self.ent[f"{eje}_{p}"] for p in "gms")
            err = None
            if not g:
                err = (MSG_VACIO, eg)
            elif _CON_DECIMALES.match(g):
                err = ("Los grados no pueden tener decimales en formato GMS.", eg)
            elif not _ENTERO.match(g):
                err = (MSG_NUMEROS, eg)
            elif m and _CON_DECIMALES.match(m):
                err = ("Los minutos no pueden tener decimales en formato GMS.", em)
            elif m and not m.isdigit():
                err = (MSG_NUMEROS, em)
            elif m and int(m) >= 60:
                err = ("Los minutos deben ser menores que 60.", em)
            elif s and not _SEGUNDOS.match(s):
                err = (MSG_NUMEROS, es)
            elif s and float(s.replace(",", ".")) >= 60:
                err = ("Los segundos deben ser menores que 60.", es)
            else:
                try:
                    v = parse_gms_campos(g, m, s, self.v[f"{eje}_h"].get(), eje)
                    fuera = self._rango_geo(eje, v, cambio)
                    if fuera:
                        err = (fuera, eg)
                except ErrorRango:
                    err = (MSG_FUERA if cambio else MSG_FUERA_AMPLIADO, eg)
                except ErrorCoordenada as e:
                    err = (e.mensaje, eg)
            if err:
                errores.append((self.campos[f"g{eje}"], err[0], [err[1]]))
        return errores

    # ------------------------------------------------------------------ conversión
    def convertir(self) -> bool:
        op = self.app.op
        self._guardar_sel()
        self._limpiar_errores()
        self._mensaje_nucleo("")
        fmt = self.v_formato.get()
        datum_in, datum_out = self.datum_entrada, self.panel.datum
        errores = getattr(self, f"_validar_{fmt}")(hay_cambio_datum(datum_in, datum_out))
        if errores:
            self._sin_resultado()
            for campo, msg, widgets in errores:
                campo.mostrar_error(msg, widgets)
            self.app.mensaje(MSG_REVISAR, "revisar")
            try:
                self.area.ver(errores[0][0])
            except tk.TclError:
                pass
            return False
        try:
            r = convertir_formulario(fmt, self._campos(), datum_in, datum_out, op.metodo_enum, self.panel.zona,
                                     op.positivos_sur_oeste)
        except ErrorCoordenada as e:
            self._sin_resultado()
            self._mensaje_nucleo(e.mensaje)
            self.app.mensaje(e.mensaje, "error")
            return False
        self.resultado = r
        self._pintar()
        self.app.mensaje(MSG_LISTA, "ok")
        return True

    def _mensaje_nucleo(self, texto: str) -> None:
        if texto:
            self.l_msg.configure(text=f" {texto}")
            self.l_msg.grid(row=0, column=0, sticky="ew", pady=(0, u(T.sep)))
        else:
            self.l_msg.configure(text="")
            self.l_msg.grid_remove()

    def _sin_resultado(self) -> None:
        self.resultado = None
        for v in self.o.values():
            v.set("")
        self._pintar()

    def _pintar(self) -> None:
        fmt = self.panel.formato
        for f in (self.r_utm, self.r_dec, self.r_gms):
            f.grid_remove()
        {"utm": self.r_utm, "decimal": self.r_dec, "gms": self.r_gms}[fmt].grid(row=0, column=0, sticky="new", pady=(u(4), 0))
        r = self.resultado
        if r is not None:
            op = self.app.op
            t = textos_resultado(r, fmt, op.decimales_utm, op.decimales_grados, op.separador_decimal)
            if fmt == "utm":
                self.o["norte"].set(t["norte"]); self.o["este"].set(t["este"]); self.o["zona"].set(t["zona"])
            elif fmt == "decimal":
                self.o["lat"].set(t["lat"]); self.o["lon"].set(t["lon"])
            else:
                self.o["glat"].set(t["lat"]); self.o["glon"].set(t["lon"])
        for b, clave in ((self.b_par_utm, "norte"), (self.b_par_dec, "lat"), (self.b_par_gms, "glat")):
            b.state(["!disabled"] if self.o[clave].get() else ["disabled"])

    # ------------------------------------------------------------------ copiar
    def _copiar(self, texto: str, aviso: str = "Copiado al portapapeles") -> None:
        if texto:
            copiar(self, texto)
            self.app.mensaje(aviso, "ok", temporal=True)

    def _copiar_norte(self) -> None:
        self._copiar(self.o["norte"].get(), "Norte copiado al portapapeles")

    def _copiar_este(self) -> None:
        self._copiar(self.o["este"].get(), "Este copiado al portapapeles")

    def _copiar_ne(self) -> None:
        if self.o["norte"].get():
            self._copiar(f"{self.o['norte'].get()}\t{self.o['este'].get()}", "Norte y Este copiados al portapapeles")

    def _copiar_lat(self) -> None:
        self._copiar(self.o["lat"].get(), "Latitud copiada al portapapeles")

    def _copiar_lon(self) -> None:
        self._copiar(self.o["lon"].get(), "Longitud copiada al portapapeles")

    def _copiar_latlon(self) -> None:
        if self.o["lat"].get():
            self._copiar(f"{self.o['lat'].get()}{separador_par(self.app.op.separador_decimal)}{self.o['lon'].get()}",
                         "Latitud y longitud copiadas al portapapeles")

    def _copiar_glat(self) -> None:
        self._copiar(self.o["glat"].get(), "Latitud copiada al portapapeles")

    def _copiar_glon(self) -> None:
        self._copiar(self.o["glon"].get(), "Longitud copiada al portapapeles")

    def _copiar_gms(self) -> None:
        if self.o["glat"].get():
            self._copiar(f"{self.o['glat'].get()}\t{self.o['glon'].get()}", "Latitud y longitud copiadas al portapapeles")

    # ------------------------------------------------------------------ limpiar
    def limpiar(self) -> None:
        for k, v in self.v.items():
            if k not in ("zona", "lat_h", "lon_h"):
                v.set("")
        self._limpiar_errores()
        self._mensaje_nucleo("")
        self._sin_resultado()
        self.app.estado.listo()
