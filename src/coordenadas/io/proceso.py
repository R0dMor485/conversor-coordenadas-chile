"""Conversión de un archivo completo (pestaña 3), sin interfaz.

Formatos de coordenadas en el archivo:
  "dec"  Latitud y Longitud en grados decimales (2 columnas)
  "gms6" Grados, minutos y segundos en 6 columnas
  "gms2" GMS como texto en 2 columnas ("33°26'56.04\"S")
  "utm"  Norte, Este y Zona (columna o valor fijo)
Las celdas numéricas se usan tal cual (no hay ambigüedad de separadores); las de texto pasan por
core.parseo. Las filas con error no se convierten: el motivo queda en la columna Estado.
"""
from __future__ import annotations

import math
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from ..core import formato as F
from ..core.constantes import Metodo, obtener_datum
from ..core.conversion import Resultado, convertir_geo, convertir_utm, hay_cambio_datum
from ..core.errores import ErrorCoordenada, ErrorEntrada
from ..core.parseo import parse_angulo, parse_gms_campos, parse_utm, parse_zona
from .excel_io import ColumnaSalida, Salida, a_texto, contar_filas, escribir_copia, leer_filas, tipo_archivo

CAMPOS = {
    "dec": ("lat", "lon"),
    "gms6": ("lat_g", "lat_m", "lat_s", "lon_g", "lon_m", "lon_s"),
    "gms2": ("lat", "lon"),
    "utm": ("norte", "este", "zona"),
}


@dataclass
class ConfigProceso:
    formato: str
    columnas: dict  # campo -> índice de columna (0-based); "zona" puede faltar si hay zona_fija
    datum_salida: str
    formato_salida: str = "utm"  # "utm", "decimal" o "gms"
    zona_salida: int | None = None
    metodo: Metodo = Metodo.TABLA_IGM
    datum_fijo: str | None = "SIRGAS"
    col_datum: int | None = None
    zona_fija: int | None = None
    positivos_sur_oeste: bool = True
    decimales_utm: int = 0
    decimales_grados: int = 6
    separador_decimal: str = "."
    fila_encabezado: int | None = 0  # 0-based; None = sin encabezado


@dataclass
class Resumen:
    ok: int = 0
    error: int = 0
    vacias: int = 0
    cancelado: bool = False
    destino: Path | None = None
    errores_ejemplo: list = field(default_factory=list)  # (fila 1-based, motivo)


def _num(v) -> float | None:
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        if not math.isfinite(v):
            raise ErrorEntrada("Valor numérico no finito.")
        return float(v)
    return None


def _vacia(v) -> bool:
    return v is None or (isinstance(v, str) and not v.strip())


def _celda(fila: list, idx: int | None):
    if idx is None or idx >= len(fila):
        return None
    return fila[idx]


def _angulo(v, eje: str, positivos: bool, nombre: str) -> float:
    if _vacia(v):
        raise ErrorEntrada(f"{nombre}: celda vacía.")
    n = _num(v)
    if n is not None:
        if n < 0:
            return n
        return -n if positivos else n
    try:
        return parse_angulo(str(v), eje, positivos).valor
    except ErrorCoordenada as e:
        raise type(e)(f"{nombre}: {e.mensaje}") from None


def _gms6(g, m, s, eje: str, positivos: bool, nombre: str) -> float:
    if _vacia(g):
        raise ErrorEntrada(f"{nombre}: faltan los grados.")
    tg = a_texto(g).strip()
    negativo = tg.startswith("-") or tg.startswith("−")
    letra = tg[-1:].upper() if tg[-1:].isalpha() else ""
    if letra:
        tg = tg[:-1].strip()
    if letra in ("S", "N", "O", "W", "E"):
        h = letra
    elif negativo:
        h = "S" if eje == "lat" else "O"
    else:
        h = ("S" if eje == "lat" else "O") if positivos else ("N" if eje == "lat" else "E")
    try:
        return parse_gms_campos(tg, a_texto(m), a_texto(s), h, eje)
    except ErrorCoordenada as e:
        raise type(e)(f"{nombre}: {e.mensaje}") from None


def _utm(v, eje: str, ampliado: bool) -> float:
    nombre = "Norte" if eje == "norte" else "Este"
    if _vacia(v):
        raise ErrorEntrada(f"{nombre}: celda vacía.")
    n = _num(v)
    if n is not None:
        return n
    try:
        return parse_utm(str(v), eje, ampliado)
    except ErrorCoordenada as e:
        raise type(e)(f"{nombre}: {e.mensaje}") from None


def _zona(v) -> int:
    if _vacia(v):
        raise ErrorEntrada("Huso: celda vacía.")
    n = _num(v)
    if n is not None:
        if not n.is_integer():
            raise ErrorEntrada(f"Huso «{a_texto(v)}» no es un número entero.")
        return int(n)
    try:
        return parse_zona(str(v))
    except ErrorCoordenada as e:
        raise type(e)(f"Huso: {e.mensaje}") from None


def fila_vacia(fila: list, cfg: ConfigProceso) -> bool:
    idx = [cfg.columnas.get(c) for c in CAMPOS[cfg.formato] if c in cfg.columnas]
    return all(_vacia(_celda(fila, i)) for i in idx)


def convertir_fila_archivo(fila: list, cfg: ConfigProceso) -> Resultado:
    """Convierte una fila de valores de celda. Lanza ErrorCoordenada con el motivo."""
    if cfg.col_datum is not None:
        dv = _celda(fila, cfg.col_datum)
        if _vacia(dv):
            raise ErrorEntrada("Datum de entrada: celda vacía.")
        try:
            datum_in = obtener_datum(a_texto(dv)).clave
        except KeyError:
            raise ErrorEntrada(f"Datum de entrada «{a_texto(dv)}» desconocido (use WGS84, PSAD56 o SAD69; también 1984, 1956 o 1969).") from None
    else:
        datum_in = cfg.datum_fijo or "SIRGAS"
    c = cfg.columnas
    pos = cfg.positivos_sur_oeste
    if cfg.formato == "dec":
        lat = _angulo(_celda(fila, c["lat"]), "lat", pos, "Latitud")
        lon = _angulo(_celda(fila, c["lon"]), "lon", pos, "Longitud")
    elif cfg.formato == "gms2":
        lat = _angulo(_celda(fila, c["lat"]), "lat", pos, "Latitud")
        lon = _angulo(_celda(fila, c["lon"]), "lon", pos, "Longitud")
    elif cfg.formato == "gms6":
        lat = _gms6(_celda(fila, c["lat_g"]), _celda(fila, c["lat_m"]), _celda(fila, c["lat_s"]), "lat", pos, "Latitud")
        lon = _gms6(_celda(fila, c["lon_g"]), _celda(fila, c["lon_m"]), _celda(fila, c["lon_s"]), "lon", pos, "Longitud")
    elif cfg.formato == "utm":
        ampliado = not hay_cambio_datum(datum_in, cfg.datum_salida)
        n = _utm(_celda(fila, c["norte"]), "norte", ampliado)
        e = _utm(_celda(fila, c["este"]), "este", ampliado)
        z = cfg.zona_fija if cfg.zona_fija is not None else _zona(_celda(fila, c.get("zona")))
        return convertir_utm(n, e, z, datum_in, cfg.datum_salida, cfg.metodo, cfg.zona_salida)
    else:
        raise ValueError(cfg.formato)
    return convertir_geo(lat, lon, datum_in, cfg.datum_salida, cfg.metodo, cfg.zona_salida)


def columnas_salida(cfg: ConfigProceso) -> list[ColumnaSalida]:
    d = cfg.datum_salida
    clave = obtener_datum(d).clave
    nombre = "WGS84" if clave == "SIRGAS" else clave  # nombre usado en los encabezados
    if cfg.formato_salida == "utm":
        fmt = "0" if cfg.decimales_utm == 0 else "0." + "0" * cfg.decimales_utm
        return [ColumnaSalida(f"Norte {nombre}", fmt), ColumnaSalida(f"Este {nombre}", fmt),
                ColumnaSalida("Huso", "0"), ColumnaSalida("Estado")]
    if cfg.formato_salida == "decimal":
        fmt = "0" if cfg.decimales_grados == 0 else "0." + "0" * cfg.decimales_grados
        return [ColumnaSalida(f"Latitud {nombre}", fmt), ColumnaSalida(f"Longitud {nombre}", fmt), ColumnaSalida("Estado")]
    return [ColumnaSalida(f"Latitud {nombre}"), ColumnaSalida(f"Longitud {nombre}"), ColumnaSalida("Estado")]


def valores_salida(r: Resultado, cfg: ConfigProceso, como_texto: bool) -> list:
    """Valores de las columnas nuevas (sin Estado). Números redondeados solo aquí."""
    sep = cfg.separador_decimal
    if cfg.formato_salida == "utm":
        if como_texto:
            return [F.numero(r.norte, cfg.decimales_utm, sep), F.numero(r.este, cfg.decimales_utm, sep), str(r.zona)]
        return [F.valor_redondeado(r.norte, cfg.decimales_utm), F.valor_redondeado(r.este, cfg.decimales_utm), r.zona]
    if cfg.formato_salida == "decimal":
        if como_texto:
            return [F.grados_decimales(r.lat, cfg.decimales_grados, sep), F.grados_decimales(r.lon, cfg.decimales_grados, sep)]
        return [F.valor_redondeado(r.lat, cfg.decimales_grados), F.valor_redondeado(r.lon, cfg.decimales_grados)]
    return [F.gms(r.lat, "lat", sep=sep), F.gms(r.lon, "lon", sep=sep)]


def procesar_archivo(
    origen: str | Path,
    hoja: str,
    destino: str | Path,
    cfg: ConfigProceso,
    avance: Callable[[float | None, str], None] | None = None,
    cancelar: threading.Event | None = None,
) -> Resumen:
    """Lee, convierte y escribe la copia. ``avance(fraccion|None, texto)``."""
    origen, destino = Path(origen), Path(destino)
    como_texto = tipo_archivo(origen) == "csv"
    cols = columnas_salida(cfg)
    n_vals = len(cols) - 1
    salida = Salida(cols)
    res = Resumen(destino=destino)
    total = contar_filas(origen, hoja)

    def av(fr, txt):
        if avance:
            avance(fr, txt)

    av(0.0, "Leyendo y convirtiendo…")
    for i, fila in enumerate(leer_filas(origen, hoja)):
        if cancelar is not None and cancelar.is_set():
            res.cancelado = True
            return res
        if cfg.fila_encabezado is not None and i <= cfg.fila_encabezado:
            continue
        if fila_vacia(fila, cfg):
            res.vacias += 1
            continue
        try:
            r = convertir_fila_archivo(fila, cfg)
            salida.valores[i] = valores_salida(r, cfg, como_texto) + ["OK"]
            res.ok += 1
        except ErrorCoordenada as e:
            salida.valores[i] = [""] * n_vals + [e.mensaje]
            res.error += 1
            if len(res.errores_ejemplo) < 20:
                res.errores_ejemplo.append((i + 1, e.mensaje))
        if i % 500 == 0:
            av(min(0.9, 0.9 * i / total) if total else None, f"Fila {i + 1}" + (f" de {total}" if total else ""))
    if cancelar is not None and cancelar.is_set():
        res.cancelado = True
        return res
    escribir_copia(origen, destino, hoja, cfg.fila_encabezado, salida, avance=lambda t: av(0.92, t))
    av(1.0, "Listo.")
    return res
