"""Lectura de .xlsx/.xls/.csv y escritura de la copia convertida.

- .xlsx: se leen los VALORES (data_only, también los calculados de fórmulas) en modo streaming, y la
  copia se escribe sobre el libro completo cargado de nuevo (conserva formato, fórmulas y otras hojas
  en lo que openpyxl permite). El original nunca se modifica.
- .xls (solo lectura, xlrd): la salida es un .xlsx nuevo con los valores de la hoja procesada.
- .csv: la salida es un .csv con la misma codificación y delimitador.
"""
from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterator

from .csv_io import FormatoCsv, escribir_csv, leer_csv

EXTENSIONES = (".xlsx", ".xlsm", ".xls", ".csv")


def tipo_archivo(ruta: str | Path) -> str:
    ext = Path(ruta).suffix.lower()
    if ext in (".xlsx", ".xlsm"):
        return "xlsx"
    if ext == ".xls":
        return "xls"
    if ext in (".csv", ".txt"):
        return "csv"
    raise ValueError(f"Tipo de archivo no admitido: {ext or '(sin extensión)'}")


def nombre_salida(ruta: str | Path) -> Path:
    """<nombre>_convertido.xlsx en la misma carpeta (o .csv si la entrada era csv)."""
    p = Path(ruta)
    ext = ".csv" if tipo_archivo(p) == "csv" else ".xlsx"
    return p.with_name(f"{p.stem}_convertido{ext}")


def letra_columna(i: int) -> str:
    """0 -> A, 25 -> Z, 26 -> AA."""
    s = ""
    i += 1
    while i:
        i, r = divmod(i - 1, 26)
        s = chr(65 + r) + s
    return s


def listar_hojas(ruta: str | Path) -> list[str]:
    t = tipo_archivo(ruta)
    if t == "csv":
        return [Path(ruta).stem]
    if t == "xls":
        import xlrd

        libro = xlrd.open_workbook(str(ruta), on_demand=True)
        try:
            return libro.sheet_names()
        finally:
            libro.release_resources()
    import openpyxl

    libro = openpyxl.load_workbook(ruta, read_only=True, data_only=True)
    try:
        return list(libro.sheetnames)
    finally:
        libro.close()


def _valor_xls(celda, datemode: int):
    import xlrd

    if celda.ctype in (xlrd.XL_CELL_EMPTY, xlrd.XL_CELL_BLANK):
        return None
    if celda.ctype == xlrd.XL_CELL_DATE:
        try:
            return xlrd.xldate.xldate_as_datetime(celda.value, datemode)
        except Exception:
            return celda.value
    if celda.ctype == xlrd.XL_CELL_ERROR:
        return None
    if celda.ctype == xlrd.XL_CELL_BOOLEAN:
        return bool(celda.value)
    return celda.value


def leer_filas(ruta: str | Path, hoja: str, max_filas: int | None = None) -> Iterator[list]:
    """Valores de las filas de la hoja (fila 1 primero). Celdas vacías = None."""
    t = tipo_archivo(ruta)
    if t == "csv":
        _, filas = leer_csv(ruta)
        for k, f in enumerate(filas):
            if max_filas is not None and k >= max_filas:
                return
            yield [v if v != "" else None for v in f]
        return
    if t == "xls":
        import xlrd

        libro = xlrd.open_workbook(str(ruta), on_demand=True)
        try:
            h = libro.sheet_by_name(hoja)
            n = h.nrows if max_filas is None else min(h.nrows, max_filas)
            for r in range(n):
                yield [_valor_xls(c, libro.datemode) for c in h.row(r)]
        finally:
            libro.release_resources()
        return
    import openpyxl

    libro = openpyxl.load_workbook(ruta, read_only=True, data_only=True)
    try:
        for k, fila in enumerate(libro[hoja].iter_rows(values_only=True)):
            if max_filas is not None and k >= max_filas:
                return
            yield list(fila)
    finally:
        libro.close()


def contar_filas(ruta: str | Path, hoja: str) -> int | None:
    """Cantidad aproximada de filas (para la barra de progreso), o None si no se sabe barato."""
    t = tipo_archivo(ruta)
    try:
        if t == "xlsx":
            import openpyxl

            libro = openpyxl.load_workbook(ruta, read_only=True, data_only=True)
            try:
                return libro[hoja].max_row
            finally:
                libro.close()
        if t == "xls":
            import xlrd

            libro = xlrd.open_workbook(str(ruta), on_demand=True)
            try:
                return libro.sheet_by_name(hoja).nrows
            finally:
                libro.release_resources()
    except Exception:
        return None
    return None


@dataclass
class ColumnaSalida:
    encabezado: str
    formato_numero: str | None = None  # p. ej. "0.000"; None = texto/general


@dataclass
class Salida:
    """Columnas nuevas y sus valores por fila de datos (índice 0-based de la fila en la hoja)."""

    columnas: list[ColumnaSalida]
    valores: dict[int, list] = field(default_factory=dict)


def escribir_copia(
    origen: str | Path,
    destino: str | Path,
    hoja: str,
    fila_encabezado: int | None,
    salida: Salida,
    formato_csv: FormatoCsv | None = None,
    avance: Callable[[str], None] | None = None,
) -> None:
    """Escribe una COPIA con las columnas nuevas al final. ``fila_encabezado`` es 0-based o None."""
    origen, destino = Path(origen), Path(destino)
    if origen.resolve() == destino.resolve():
        raise ValueError("El archivo de salida no puede ser el mismo que el de entrada.")
    t = tipo_archivo(origen)
    if t == "csv":
        fmt, filas = leer_csv(origen)
        fmt = formato_csv or fmt
        ancho = max((len(f) for f in filas), default=0)
        for i, f in enumerate(filas):
            f.extend([""] * (ancho - len(f)))
            if fila_encabezado is not None and i == fila_encabezado:
                f.extend(c.encabezado for c in salida.columnas)
            else:
                f.extend(salida.valores.get(i, [""] * len(salida.columnas)))
        escribir_csv(destino, filas, fmt)
        return
    import openpyxl

    if t == "xlsx":
        if avance:
            avance("Cargando el libro original para la copia…")
        libro = openpyxl.load_workbook(origen, keep_vba=False)
        ws = libro[hoja]
        primera_col = ws.max_column + 1
    else:  # xls -> xlsx con valores
        libro = openpyxl.Workbook()
        ws = libro.active
        ws.title = hoja[:31]
        primera_col = 1
        for fila in leer_filas(origen, hoja):
            ws.append([v for v in fila])
        primera_col = ws.max_column + 1
    if fila_encabezado is not None:
        for k, c in enumerate(salida.columnas):
            ws.cell(fila_encabezado + 1, primera_col + k, c.encabezado)
    if avance:
        avance("Escribiendo columnas nuevas…")
    for i, vals in salida.valores.items():
        for k, v in enumerate(vals):
            if v is None or v == "":
                continue
            celda = ws.cell(i + 1, primera_col + k, v)
            fmt = salida.columnas[k].formato_numero
            if fmt and isinstance(v, (int, float)):
                celda.number_format = fmt
    if avance:
        avance("Guardando la copia…")
    libro.save(destino)


def a_texto(v) -> str:
    """Valor de celda como texto, sin depender del locale."""
    if v is None:
        return ""
    if isinstance(v, bool):
        return str(v)
    if isinstance(v, float):
        return repr(v) if not v.is_integer() else str(int(v))
    if isinstance(v, (_dt.datetime, _dt.date)):
        return v.isoformat()
    return str(v)
