"""Lectura y escritura de csv con detección de codificación y delimitador."""
from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from pathlib import Path

DELIMITADORES = (";", ",", "\t", "|")


@dataclass(frozen=True)
class FormatoCsv:
    codificacion: str  # "utf-8-sig" o "latin-1"
    delimitador: str


def detectar_codificacion(datos: bytes) -> str:
    """utf-8 (con o sin BOM) si decodifica sin errores; si no, latin-1 (conserva los bytes)."""
    try:
        datos.decode("utf-8")
        return "utf-8-sig"
    except UnicodeDecodeError:
        return "latin-1"


def detectar_delimitador(texto: str) -> str:
    muestra = "\n".join(texto.splitlines()[:50])
    try:
        return csv.Sniffer().sniff(muestra, delimiters="".join(DELIMITADORES)).delimiter
    except csv.Error:
        pass
    # alternativa: el delimitador que aparece el mismo número de veces (>0) en más líneas
    lineas = [l for l in muestra.splitlines() if l.strip()]
    mejor, puntaje = ";", -1
    for d in DELIMITADORES:
        cuentas = [l.count(d) for l in lineas]
        if not cuentas or max(cuentas) == 0:
            continue
        moda = max(set(cuentas), key=cuentas.count)
        p = cuentas.count(moda) if moda > 0 else 0
        if p > puntaje:
            mejor, puntaje = d, p
    return mejor


def leer_csv(ruta: str | Path) -> tuple[FormatoCsv, list[list[str]]]:
    datos = Path(ruta).read_bytes()
    cod = detectar_codificacion(datos)
    texto = datos.decode(cod)
    delim = detectar_delimitador(texto)
    filas = list(csv.reader(io.StringIO(texto, newline=""), delimiter=delim))
    return FormatoCsv(cod, delim), filas


def escribir_csv(ruta: str | Path, filas: list[list], formato: FormatoCsv) -> None:
    with open(ruta, "w", encoding=formato.codificacion, newline="", errors="replace") as f:
        w = csv.writer(f, delimiter=formato.delimitador, lineterminator="\r\n")
        for fila in filas:
            w.writerow(["" if v is None else v for v in fila])
