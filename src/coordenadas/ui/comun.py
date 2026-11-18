"""Utilidades compartidas por las pestañas."""
from __future__ import annotations

import tkinter as tk

from ..core.constantes import ORDEN_DATUMS, Metodo
from . import componentes as K
from .tema import C

# Nombres técnicos que muestra la interfaz (sin explicaciones).
ETIQUETA_POR_CLAVE = {"SIRGAS": "WGS84 / SIRGAS", "PSAD56": "PSAD56", "SAD69": "SAD69"}
ETIQUETAS_DATUM = [ETIQUETA_POR_CLAVE[k] for k in ORDEN_DATUMS]
CLAVE_POR_ETIQUETA = {v: k for k, v in ETIQUETA_POR_CLAVE.items()}
CLAVE_POR_ETIQUETA.update({k: k for k in ORDEN_DATUMS})  # también se acepta la clave

ETIQUETA_METODO = {Metodo.TABLA_IGM.value: "Tabla IGM vigente", Metodo.REPLICA_EXE.value: "Réplica de Datum_datum.exe"}
AYUDA_METODO = {
    Metodo.TABLA_IGM.value: "Franjas continuas según la tabla publicada por el IGM.",
    Metodo.REPLICA_EXE.value: "Reproduce el programa original. En SAD69 entre 26° y 32° S difiere 10–13 m.",
}
NOMBRE_CORTO = {"SIRGAS": "WGS84", "PSAD56": "PSAD56", "SAD69": "SAD69"}  # encabezados de columnas
FORMATOS_SALIDA = [("utm", "U.T.M."), ("decimal", "Decimal"), ("gms", "GMS")]

# Compatibilidad con módulos anteriores
COLOR_ERROR = C.error
COLOR_OK = C.exito
FONDO_AVISO = C.fondo_aviso
FONDO_ERROR = C.fondo_error


def clave_datum(etiqueta: str) -> str:
    return CLAVE_POR_ETIQUETA[etiqueta]


def combo_datum(padre, variable: tk.StringVar, **kw):
    if variable.get() in CLAVE_POR_ETIQUETA and variable.get() not in ETIQUETAS_DATUM:
        variable.set(ETIQUETA_POR_CLAVE[variable.get()])
    return K.combo(padre, variable, ETIQUETAS_DATUM, **kw)


def copiar(widget: tk.Misc, texto: str) -> None:
    """Copia al portapapeles. Tk en Windows convierte cada salto "\n" en "\r\n"; si el texto ya trae "\r\n"
    queda "\r\r\n" y Excel inserta una fila vacía entre cada fila. Por eso se normaliza a "\n"."""
    widget.clipboard_clear()
    widget.clipboard_append(texto.replace("\r\n", "\n").replace("\r", "\n"))
    widget.update_idletasks()
