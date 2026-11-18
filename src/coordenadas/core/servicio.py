"""Conversión desde textos (formulario, fila de la lista o celda de archivo) y textos de salida.

Capa sin interfaz: la usan las tres pestañas y las pruebas.
"""
from __future__ import annotations

from dataclasses import dataclass

from . import formato as F
from .constantes import Metodo, grados_min
from .conversion import Resultado, convertir_geo, convertir_utm, hay_cambio_datum
from .errores import ErrorCoordenada, ErrorEntrada
from .parseo import interpretar_fila, parse_angulo, parse_gms_campos, parse_utm, parse_zona

FORMATOS = ("utm", "decimal", "gms")


def _campo(nombre: str, fn, *args, **kw):
    try:
        return fn(*args, **kw)
    except ErrorCoordenada as e:
        raise type(e)(f"{nombre}: {e.mensaje}") from None


def convertir_formulario(
    formato: str,
    campos: dict,
    datum_entrada: str,
    datum_salida: str,
    metodo: Metodo,
    zona_salida: int | None = None,
    positivos_sur_oeste: bool = True,
) -> Resultado:
    """Pestaña 1. ``campos`` según el formato:
    utm: norte, este, zona · decimal: lat, lon · gms: lat_g, lat_m, lat_s, lat_h, lon_g, lon_m, lon_s, lon_h.
    """
    ampliado = not hay_cambio_datum(datum_entrada, datum_salida)
    if formato == "utm":
        n = _campo("Norte", parse_utm, campos.get("norte"), "norte", ampliado)
        e = _campo("Este", parse_utm, campos.get("este"), "este", ampliado)
        z = _campo("Zona", parse_zona, campos.get("zona"))
        return convertir_utm(n, e, z, datum_entrada, datum_salida, metodo, zona_salida)
    if formato == "decimal":
        lat = _campo("Latitud", parse_angulo, campos.get("lat"), "lat", positivos_sur_oeste).valor
        lon = _campo("Longitud", parse_angulo, campos.get("lon"), "lon", positivos_sur_oeste).valor
        return convertir_geo(lat, lon, datum_entrada, datum_salida, metodo, zona_salida)
    if formato == "gms":
        lat = _campo("Latitud", parse_gms_campos, campos.get("lat_g"), campos.get("lat_m"), campos.get("lat_s"), campos.get("lat_h"), "lat")
        lon = _campo("Longitud", parse_gms_campos, campos.get("lon_g"), campos.get("lon_m"), campos.get("lon_s"), campos.get("lon_h"), "lon")
        return convertir_geo(lat, lon, datum_entrada, datum_salida, metodo, zona_salida)
    raise ValueError(formato)


@dataclass(frozen=True)
class ResultadoFila:
    resultado: Resultado | None
    estado: str  # "OK", aviso o motivo del error
    nivel: str  # "ok", "aviso" (amarillo) o "error" (rojo)


def convertir_fila(
    c1, c2, zona, datum_entrada: str, datum_salida: str, metodo: Metodo,
    zona_salida: int | None = None, positivos_sur_oeste: bool = True,
) -> ResultadoFila:
    """Pestaña 2: detección automática de formato y orden. Nunca lanza ErrorCoordenada."""
    try:
        f = interpretar_fila(c1, c2, zona, hay_cambio_datum(datum_entrada, datum_salida), positivos_sur_oeste)
        if f.tipo == "geo":
            r = convertir_geo(f.a, f.b, datum_entrada, datum_salida, metodo, zona_salida)
        else:
            r = convertir_utm(f.a, f.b, f.zona, datum_entrada, datum_salida, metodo, zona_salida)
    except ErrorCoordenada as e:
        return ResultadoFila(None, e.mensaje, "error")
    if f.orden_invertido:
        return ResultadoFila(r, f.nota, "aviso")
    return ResultadoFila(r, "OK", "ok")


def convertir_fila_utm(
    norte, este, huso, datum_texto, datum_salida: str, metodo: Metodo,
    zona_salida: int | None = None,
) -> ResultadoFila:
    """Conversión masiva (solo UTM): el datum de entrada se lee de la propia fila.
    Nunca lanza ErrorCoordenada. Sin datum o con un datum desconocido la fila es un error."""
    from .constantes import obtener_datum

    try:
        texto = str(datum_texto or "").strip()
        if not texto:
            raise ErrorEntrada("Falta el datum.")
        try:
            datum_in = obtener_datum(texto).clave
        except KeyError:
            raise ErrorEntrada(f"Datum «{texto}» desconocido (use WGS84, PSAD56 o SAD69).") from None
        f = interpretar_fila(norte, este, huso, hay_cambio_datum(datum_in, datum_salida))
        if f.tipo != "utm":
            raise ErrorEntrada("Se esperan coordenadas UTM (Norte y Este).")
        r = convertir_utm(f.a, f.b, f.zona, datum_in, datum_salida, metodo, zona_salida)
    except ErrorCoordenada as e:
        return ResultadoFila(None, e.mensaje, "error")
    if f.orden_invertido:
        return ResultadoFila(r, f.nota, "aviso")
    return ResultadoFila(r, "OK", "ok")


def textos_resultado(r: Resultado, formato: str, decimales_utm: int = 0, decimales_grados: int = 6, sep: str = ".") -> dict:
    """Textos listos para mostrar o copiar (sin separador de miles)."""
    if formato == "utm":
        return {"norte": F.numero(r.norte, decimales_utm, sep), "este": F.numero(r.este, decimales_utm, sep), "zona": str(r.zona)}
    if formato == "decimal":
        return {"lat": F.grados_decimales(r.lat, decimales_grados, sep), "lon": F.grados_decimales(r.lon, decimales_grados, sep)}
    if formato == "gms":
        return {"lat": F.gms(r.lat, "lat", sep=sep), "lon": F.gms(r.lon, "lon", sep=sep)}
    raise ValueError(formato)


def separador_par(sep_decimal: str) -> str:
    """Separador entre dos valores en una sola línea ("lat, lon"); con coma decimal se usa "; "."""
    return ", " if sep_decimal == "." else "; "


def descripcion_pasos(r: Resultado) -> str:
    if not r.pasos:
        return f"Sin cambio de datum ({r.datum_entrada}); solo cambio de formato."
    partes = []
    for p in r.pasos:
        dx, dy, dz = p.deltas
        partes.append(
            f"{p.origen}→{p.destino}: franja {grados_min(p.franja.inferior)}–{grados_min(p.franja.superior)} S, "
            f"ΔX={dx} ΔY={dy} ΔZ={dz} m"
        )
    return " · ".join(partes)


# --------------------------------------------------------------------------- pegado (pestaña 2)
@dataclass(frozen=True)
class FilaPegada:
    datum: str | None  # clave de datum si la línea lo traía; None = usar el de la fila/por defecto
    c1: str
    c2: str
    zona: str


def interpretar_pegado(texto: str) -> list[FilaPegada]:
    """Convierte el texto del portapapeles en filas (datum opcional, coord. 1, coord. 2, zona).

    Separadores admitidos: tabulador, punto y coma, ", " o espacios. Las líneas vacías y las de
    encabezado (sin ningún dígito) se omiten.
    """
    from .constantes import obtener_datum
    from .parseo import dividir_linea

    filas: list[FilaPegada] = []
    for linea in texto.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if not linea.strip():
            continue
        campos = dividir_linea(linea)
        datum = None
        if campos:
            try:
                datum = obtener_datum(campos[0]).clave
                campos = campos[1:]
            except KeyError:
                pass
        if not any(ch.isdigit() for ch in "".join(campos)):
            continue  # encabezado
        campos = (campos + ["", "", ""])[:3] if len(campos) <= 3 else campos[:2] + [" ".join(campos[2:])]
        filas.append(FilaPegada(datum, campos[0], campos[1], campos[2]))
    return filas


@dataclass(frozen=True)
class FilaPegadaUtm:
    norte: str
    este: str
    huso: str
    datum: str


def interpretar_pegado_utm(texto: str) -> list[FilaPegadaUtm]:
    """Filas pegadas con el orden Norte, Este, Huso, Datum (tabulador, punto y coma, ", " o espacios).
    El datum es el resto de la línea (admite "WGS 84"). Se omiten líneas vacías y encabezados."""
    from .parseo import dividir_linea

    filas: list[FilaPegadaUtm] = []
    for linea in texto.splitlines():
        if not linea.strip():
            continue
        # tabulador, ";" o ", " separan campos (conservan los vacíos); si no, se separa por espacios
        campos = dividir_linea(linea) if ("\t" in linea or ";" in linea or ", " in linea) else linea.split()
        if not any(ch.isdigit() for ch in "".join(campos[:3])):
            continue  # encabezado
        campos = campos + [""] * (4 - len(campos)) if len(campos) < 4 else campos[:3] + [" ".join(campos[3:])]
        filas.append(FilaPegadaUtm(*campos[:4]))
    return filas


ENCABEZADOS = {"utm": ["Norte", "Este", "Zona"], "decimal": ["Latitud", "Longitud", ""], "gms": ["Latitud", "Longitud", ""]}


def textos_fila(rf: ResultadoFila | None, formato: str, decimales_utm: int = 0, decimales_grados: int = 6, sep: str = ".") -> list[str]:
    """Tres columnas de resultado (Norte, Este, Zona o Latitud, Longitud, "")."""
    if rf is None or rf.resultado is None:
        return ["", "", ""]
    t = textos_resultado(rf.resultado, formato, decimales_utm, decimales_grados, sep)
    if formato == "utm":
        return [t["norte"], t["este"], t["zona"]]
    return [t["lat"], t["lon"], ""]
