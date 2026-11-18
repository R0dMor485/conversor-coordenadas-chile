"""Formateo de resultados: independiente de la configuración regional y sin separador de miles.

El núcleo trabaja con precisión completa; el redondeo ocurre solo aquí (al mostrar o exportar),
con redondeo "mitad hacia arriba" sobre la representación decimal más corta del número.
"""
from __future__ import annotations

import math
from decimal import ROUND_HALF_UP, Decimal

DECIMALES_SEGUNDOS = 4  # GMS: 0.0001″ ≈ 3 mm, como el programa original


def redondear(x: float, decimales: int) -> Decimal:
    if not math.isfinite(x):
        raise ValueError("valor no finito")
    q = Decimal(1).scaleb(-decimales) if decimales > 0 else Decimal(1)
    d = Decimal(repr(float(x))).quantize(q, rounding=ROUND_HALF_UP)
    if d == 0:
        d = abs(d)  # nunca "-0"
    return d


def valor_redondeado(x: float, decimales: int) -> float:
    """Valor numérico redondeado (para celdas numéricas de Excel)."""
    return float(redondear(x, decimales))


def numero(x: float, decimales: int, sep: str = ".") -> str:
    """Número sin separador de miles; ``sep`` es el separador decimal ("." o ",")."""
    if sep not in (".", ","):
        raise ValueError("separador decimal inválido")
    s = format(redondear(x, decimales), "f")
    return s.replace(".", sep) if sep != "." else s


def grados_decimales(v: float, decimales: int = 6, sep: str = ".") -> str:
    """Grados decimales con signo (negativo al sur / oeste)."""
    return numero(v, decimales, sep)


def gms_partes(v: float, dec_seg: int = DECIMALES_SEGUNDOS) -> tuple[int, int, Decimal, bool]:
    """(grados, minutos, segundos redondeados, negativo), con el acarreo resuelto
    (59.99996″ -> 0″ del minuto siguiente)."""
    neg = v < 0
    seg_tot = redondear(abs(v) * 3600.0, dec_seg)
    g = int(seg_tot // 3600)
    resto = seg_tot - g * 3600
    m = int(resto // 60)
    s = resto - m * 60
    if seg_tot == 0:
        neg = False
    return g, m, s, neg


def gms(v: float, eje: str, dec_seg: int = DECIMALES_SEGUNDOS, sep: str = ".") -> str:
    """Texto GMS: 33° 27' 12.3456" S  /  70° 39' 0.0000" O."""
    g, m, s, neg = gms_partes(v, dec_seg)
    if eje == "lat":
        h = "S" if neg else "N"
    else:
        h = "O" if neg else "E"
    st = format(s.quantize(Decimal(1).scaleb(-dec_seg)) if dec_seg > 0 else s.quantize(Decimal(1)), "f")
    if sep == ",":
        st = st.replace(".", ",")
    return f"{g}° {m:02d}' {st}\" {h}"


def texto_tabulado(filas: list[list[str]], encabezados: list[str] | None = None) -> str:
    """Filas como texto separado por tabuladores (para el portapapeles)."""
    lineas = []
    if encabezados:
        lineas.append("\t".join(encabezados))
    for f in filas:
        lineas.append("\t".join("" if c is None else str(c) for c in f))
    return "\r\n".join(lineas)
