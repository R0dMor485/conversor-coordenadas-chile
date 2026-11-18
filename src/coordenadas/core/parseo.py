"""Lectura tolerante de coordenadas escritas a mano o pegadas desde otros programas.

Principios:
- Independiente de la configuración regional: el punto y la coma se interpretan aquí.
- Nada se adivina en silencio: si un texto admite dos lecturas válidas, es un error (ErrorAmbiguo).
- El signo o la letra de hemisferio explícitos siempre mandan; sin ellos, los valores positivos se
  interpretan como S y O si la opción ``positivos_sur_oeste`` está activa.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass

from .constantes import obtener_datum
from .errores import ErrorAmbiguo, ErrorEntrada, ErrorRango

# --------------------------------------------------------------------------- normalización
_REEMPLAZOS = {
    " ": " ", " ": " ", " ": " ", " ": " ", "\t": " ",
    "−": "-", "–": "-", "—": "-", "‐": "-", "‑": "-", "﹣": "-", "－": "-",
    "′": "'", "’": "'", "‘": "'", "´": "'", "`": "'",
    "″": '"', "”": '"', "“": '"',
    "º": "°", "˚": "°", "⁰": "°",
}


def normalizar(texto) -> str:
    if texto is None:
        return ""
    t = str(texto)
    for a, b in _REEMPLAZOS.items():
        t = t.replace(a, b)
    t = t.replace("''", '"')
    return re.sub(r"\s+", " ", t).strip()


# --------------------------------------------------------------------------- números
_RE_UNIDADES = re.compile(r"\s*(?:m|mt|mts|metros)\.?\s*$", re.IGNORECASE)


def _quitar_unidades(t: str) -> str:
    t = _RE_UNIDADES.sub("", t).strip()
    # el .exe escribía "7.956.582,773.  m.": punto final suelto tras la parte decimal
    if t.endswith((".", ",")) and len(t) > 1 and t[-2].isdigit():
        t = t[:-1]
    return t


def _agrupacion_valida(grupos: list[str]) -> bool:
    return (
        len(grupos) >= 2
        and 1 <= len(grupos[0]) <= 3
        and all(g.isdigit() for g in grupos)
        and all(len(g) == 3 for g in grupos[1:])
    )


def candidatos_numero(texto) -> list[float]:
    """Todas las lecturas numéricas posibles de un texto (separadores de miles y decimal).

    "6.318.026,543" -> [6318026.543]; "346.642" -> [346.642, 346642.0]; "12,5" -> [12.5].
    """
    t = _quitar_unidades(normalizar(texto))
    if not t:
        raise ErrorEntrada("Campo vacío.")
    signo = 1.0
    if t[0] in "+-":
        signo = -1.0 if t[0] == "-" else 1.0
        t = t[1:].strip()
    if not t or not re.fullmatch(r"[\d., ]+", t) or not re.search(r"\d", t):
        raise ErrorEntrada(f"«{texto}» no es un número.")
    if t[0] in ".,":
        t = "0" + t
    if t[-1] in ".,":
        raise ErrorEntrada(f"«{texto}» no es un número.")

    def ok(v: float) -> float:
        return signo * v

    if " " in t:
        # espacios solo como separador de miles: "6 318 026,543"
        m = re.fullmatch(r"(\d{1,3}(?: \d{3})+)(?:([.,])(\d+))?", t)
        if not m:
            raise ErrorEntrada(f"«{texto}» no es un número válido.")
        entero = int(m.group(1).replace(" ", ""))
        return [ok(entero + (float("0." + m.group(3)) if m.group(3) else 0.0))]

    puntos, comas = t.count("."), t.count(",")
    if puntos == 0 and comas == 0:
        return [ok(float(t))]
    if puntos and comas:
        dec = "." if t.rfind(".") > t.rfind(",") else ","
        mil = "," if dec == "." else "."
        if t.count(dec) != 1:
            raise ErrorEntrada(f"«{texto}» no es un número válido.")
        ent, frac = t.split(dec)
        if not _agrupacion_valida(ent.split(mil)) or not frac.isdigit():
            raise ErrorEntrada(f"«{texto}» tiene separadores de miles mal ubicados.")
        return [ok(float(ent.replace(mil, "") + "." + frac))]
    sep = "." if puntos else ","
    partes = t.split(sep)
    if len(partes) > 2:
        if not _agrupacion_valida(partes):
            raise ErrorEntrada(f"«{texto}» no es un número válido.")
        return [ok(float("".join(partes)))]
    a, b = partes
    cands = [ok(float(a + "." + b))]
    if 1 <= len(a) <= 3 and len(b) == 3 and not (a.startswith("0")):
        cands.append(ok(float(a + b)))
    return sorted(set(cands), key=abs)


def _fmt(v: float) -> str:
    return repr(float(v)).replace("e+", "e")


def parse_numero(texto, rango: tuple[float, float] | None = None, nombre: str = "valor") -> float:
    """Número con desambiguación de miles/decimal por magnitud (``rango`` cerrado)."""
    cands = candidatos_numero(texto)
    if rango is None:
        if len(cands) == 1:
            return cands[0]
        raise ErrorAmbiguo(f"«{texto}» es ambiguo: puede ser {' o '.join(_fmt(c) for c in cands)}.")
    lo, hi = rango
    dentro = [c for c in cands if lo <= c <= hi]
    if len(dentro) == 1:
        return dentro[0]
    if not dentro:
        raise ErrorRango(f"{nombre} «{texto}» fuera de rango ({_fmt(lo)} a {_fmt(hi)}).")
    raise ErrorAmbiguo(f"{nombre} «{texto}» es ambiguo: {' o '.join(_fmt(c) for c in dentro)}.")


# Rangos de magnitud para desambiguar separadores de miles en UTM (Chile continental).
RANGO_NORTE_CONTINENTAL = (3_700_000.0, 8_100_000.0)
RANGO_ESTE = (100_000.0, 900_000.0)
# Sin cambio de datum (rango ampliado) el Norte puede ser menor (Antártica).
RANGO_NORTE_AMPLIADO = (1_000_000.0, 10_000_000.0)


def parse_utm(texto, eje: str, ampliado: bool = False) -> float:
    """Norte o Este UTM. Los separadores de miles se desambiguan por magnitud; si el texto tiene
    una sola lectura posible, se acepta aunque esté fuera del rango típico (lo valida el núcleo)."""
    if eje not in ("norte", "este"):
        raise ValueError(eje)
    cands = candidatos_numero(texto)
    if len(cands) == 1:
        return cands[0]
    rango = RANGO_ESTE if eje == "este" else (RANGO_NORTE_AMPLIADO if ampliado else RANGO_NORTE_CONTINENTAL)
    return parse_numero(texto, rango, "Este" if eje == "este" else "Norte")


def parse_zona(texto) -> int:
    """Huso UTM: "19", "19S", "19 H", "huso 18". La letra (si hay) debe ser del hemisferio sur
    (bandas C–M) o "S" (sur)."""
    t = normalizar(texto).upper()
    if not t:
        raise ErrorEntrada("Falta el huso (zona).")
    t = re.sub(r"^(HUSO|ZONA|ZONE)\s*", "", t)
    if isinstance(texto, float) and texto.is_integer():
        t = str(int(texto))
    m = re.fullmatch(r"(\d{1,2})(?:[.,]0+)?\s*([A-Z]|SUR)?", t)
    if not m:
        raise ErrorEntrada(f"Huso «{texto}» no válido.")
    letra = m.group(2)
    if letra and not (letra in "CDEFGHJKLM" or letra in ("S", "SUR")):
        raise ErrorRango(f"Huso «{texto}»: la banda {letra} no es del hemisferio sur.")
    z = int(m.group(1))
    if not 1 <= z <= 60:
        raise ErrorRango(f"Huso {z} fuera de rango (1 a 60).")
    return z


# --------------------------------------------------------------------------- ángulos
@dataclass(frozen=True)
class Angulo:
    valor: float  # grados con signo (negativo al sur / oeste)
    eje: str | None  # "lat" o "lon" si lo indicó una letra; None si no
    explicito: bool  # hubo signo o letra de hemisferio
    forma: str  # "decimal", "gm" o "gms"


_HEMI = {
    "N": ("lat", 1), "NORTE": ("lat", 1), "S": ("lat", -1), "SUR": ("lat", -1),
    "E": ("lon", 1), "ESTE": ("lon", 1), "O": ("lon", -1), "OESTE": ("lon", -1), "W": ("lon", -1),
}
_MARCA = {
    "°": 0, "D": 0, "DEG": 0, "G": 0, "GR": 0,
    "'": 1, "M": 1, "MIN": 1,
    '"': 2, "SEG": 2, "SEC": 2,
}
_TOKEN = re.compile(r"\s*(?:(?P<num>\d+(?:[.,]\d+)?|[.,]\d+)|(?P<sym>[°'\"])|(?P<let>[A-Za-z]+)|(?P<sig>[+-]))")


def _decimal(txt: str) -> float:
    return float(txt.replace(",", "."))


def parse_angulo(texto, eje: str | None = None, positivos_sur_oeste: bool = True) -> Angulo:
    """Ángulo en grados decimales, grados-minutos o grados-minutos-segundos.

    Acepta "−33.4489", "33,4489 S", "33°26'56.04\\"S", "S 33 26 56,04", "33d26m56.04s",
    "70° 39′ 12″ O", "33 26.934 S" (grados y minutos decimales).
    Grados con decimales junto a minutos (o minutos con decimales junto a segundos) es error.
    """
    t = normalizar(texto)
    if not t:
        raise ErrorEntrada("Campo vacío.")
    pos = 0
    toks: list[tuple[str, str]] = []
    while pos < len(t):
        m = _TOKEN.match(t, pos)
        if not m or m.end() == pos:
            car = t[pos:].strip()[:1]
            raise ErrorEntrada(f"Carácter no válido «{car}» en «{texto}».")
        tipo = m.lastgroup
        toks.append((tipo, m.group(tipo)))
        pos = m.end()

    numeros: list[list] = []  # [texto, posición (0 g, 1 m, 2 s) o None]
    hemis: list[tuple[str, int]] = []
    signo = None
    hay_marca_min = False
    for i, (tipo, val) in enumerate(toks):
        previo = toks[i - 1] if i else None
        if tipo == "num":
            numeros.append([val, None])
        elif tipo == "sig":
            if signo is not None or numeros:
                raise ErrorEntrada(f"Signo mal ubicado en «{texto}».")
            signo = val
        elif tipo in ("sym", "let"):
            u = val.upper()
            pegado = previo is not None and previo[0] == "num" and numeros and numeros[-1][1] is None
            if u == "S" and pegado and hay_marca_min:
                numeros[-1][1] = 2  # "12.5s" tras "27m": marca de segundos
            elif u in _MARCA and pegado:
                numeros[-1][1] = _MARCA[u]
                if _MARCA[u] == 1:
                    hay_marca_min = True
            elif u in _HEMI:
                hemis.append(_HEMI[u])
            elif u in _MARCA or u == "S":
                raise ErrorEntrada(f"Marca «{val}» mal ubicada en «{texto}».")
            else:
                raise ErrorEntrada(f"Texto no válido «{val}» en «{texto}».")
    if not numeros:
        raise ErrorEntrada(f"«{texto}» no contiene un número.")
    if len(hemis) > 1:
        raise ErrorEntrada(f"Más de una letra de hemisferio en «{texto}».")
    if len(numeros) > 3:
        raise ErrorEntrada(f"Demasiados números en «{texto}».")
    # posiciones: marcas explícitas o, si no hay, en orden g, m, s
    if any(p is not None for _, p in numeros):
        sig = 0
        for n in numeros:
            if n[1] is None:
                n[1] = sig
            if n[1] < sig:
                raise ErrorEntrada(f"Orden de grados, minutos y segundos inválido en «{texto}».")
            sig = n[1] + 1
        if [n[1] for n in numeros] != list(range(len(numeros))):
            raise ErrorEntrada(f"Faltan los grados o los minutos en «{texto}».")
    partes = [n[0] for n in numeros]
    forma = ("decimal", "gm", "gms")[len(partes) - 1]
    tiene_dec = [bool(re.search(r"[.,]", p)) for p in partes]
    if len(partes) >= 2 and tiene_dec[0]:
        raise ErrorEntrada(f"Los grados no pueden tener decimales si se indican minutos («{texto}»).")
    if len(partes) == 3 and tiene_dec[1]:
        raise ErrorEntrada(f"Los minutos no pueden tener decimales si se indican segundos («{texto}»).")
    g = _decimal(partes[0])
    mi = _decimal(partes[1]) if len(partes) > 1 else 0.0
    se = _decimal(partes[2]) if len(partes) > 2 else 0.0
    if mi >= 60:
        raise ErrorRango(f"Minutos fuera de rango (deben ser menores que 60) en «{texto}».")
    if se >= 60:
        raise ErrorRango(f"Segundos fuera de rango (deben ser menores que 60) en «{texto}».")
    valor = g + mi / 60.0 + se / 3600.0

    eje_letra = None
    if hemis:
        eje_letra, s_letra = hemis[0]
        if eje and eje != eje_letra:
            nombre = "latitud" if eje == "lat" else "longitud"
            raise ErrorEntrada(f"La letra de hemisferio de «{texto}» no corresponde a una {nombre}.")
        if signo == "-" and s_letra > 0:
            raise ErrorEntrada(f"Signo negativo y hemisferio {'N' if eje_letra == 'lat' else 'E'} se contradicen en «{texto}».")
        if signo == "+" and s_letra < 0:
            raise ErrorEntrada(f"Signo positivo y hemisferio S/O se contradicen en «{texto}».")
        valor *= s_letra
    elif signo == "-":
        valor = -valor
    elif signo == "+":
        pass
    elif positivos_sur_oeste:
        valor = -valor
    eje_f = eje or eje_letra
    lim = 90.0 if eje_f == "lat" else 180.0
    if abs(valor) > lim:
        raise ErrorRango(f"«{texto}» fuera de rango (máximo {lim:.0f}°).")
    return Angulo(valor, eje_letra, bool(hemis) or signo is not None, forma)


def parse_gms_campos(
    grados, minutos, segundos, hemisferio: str, eje: str
) -> float:
    """Campos separados de la pestaña 1. Minutos y segundos vacíos valen 0.

    ``hemisferio``: "S"/"N" para latitud, "O"/"E" (o "W") para longitud.
    """
    g = normalizar(grados)
    if not g:
        raise ErrorEntrada("Faltan los grados.")
    negativo = False
    if g[0] in "+-":
        negativo = g[0] == "-"
        g = g[1:].strip()
    if not re.fullmatch(r"\d+", g):
        if re.fullmatch(r"\d+[.,]\d*|[.,]\d+", g):
            raise ErrorEntrada(f"Los grados no pueden tener decimales en formato GMS («{grados}»).")
        raise ErrorEntrada(f"Grados «{grados}» no válidos.")
    mi = normalizar(minutos) or "0"
    if not re.fullmatch(r"\d+", mi):
        if re.fullmatch(r"\d+[.,]\d*|[.,]\d+", mi):
            raise ErrorEntrada(f"Los minutos no pueden tener decimales en formato GMS («{minutos}»).")
        raise ErrorEntrada(f"Minutos «{minutos}» no válidos.")
    se = normalizar(segundos) or "0"
    if not re.fullmatch(r"\d+(?:[.,]\d+)?|[.,]\d+", se):
        raise ErrorEntrada(f"Segundos «{segundos}» no válidos.")
    gv, mv, sv = int(g), int(mi), _decimal(se)
    if mv >= 60:
        raise ErrorRango("Minutos fuera de rango (deben ser menores que 60).")
    if sv >= 60:
        raise ErrorRango("Segundos fuera de rango (deben ser menores que 60).")
    h = (hemisferio or "").strip().upper()
    validos = ("S", "N") if eje == "lat" else ("O", "W", "E")
    if h not in validos:
        raise ErrorEntrada("Indique el hemisferio.")
    sur_oeste = h in ("S", "O", "W")
    if negativo and not sur_oeste:
        raise ErrorEntrada("Signo negativo y hemisferio N/E se contradicen.")
    v = gv + mv / 60.0 + sv / 3600.0
    lim = 90.0 if eje == "lat" else 180.0
    if v > lim:
        raise ErrorRango(f"Grados fuera de rango (máximo {lim:.0f}°).")
    return -v if sur_oeste else v


# --------------------------------------------------------------------------- filas (masiva)
@dataclass(frozen=True)
class FilaInterpretada:
    tipo: str  # "geo" o "utm"
    a: float  # geo: latitud; utm: Norte
    b: float  # geo: longitud; utm: Este
    zona: int | None
    orden_invertido: bool
    nota: str = ""


# Rangos para detectar formato y orden (no son la validación final, que hace el núcleo).
DET_LAT_CONTINENTAL = (17.0, 56.0)
DET_LON_CONTINENTAL = (66.0, 77.0)
DET_LAT_AMPLIADA = (0.0, 80.0)
DET_LON_AMPLIADA = (50.0, 120.0)


def _parece_angulo(t: str) -> bool:
    return bool(re.search(r"[°'\"A-Za-z]", t)) or len(t.split()) in (2, 3) and not re.fullmatch(r"\d{1,3}(?: \d{3})+(?:[.,]\d+)?", t)


def interpretar_fila(c1, c2, zona="", cambio_datum: bool = True, positivos_sur_oeste: bool = True) -> FilaInterpretada:
    """Detecta formato (geográfico o UTM) y orden (lat/lon o Norte/Este) de una fila."""
    t1, t2 = normalizar(c1), normalizar(c2)
    if not t1 and not t2:
        raise ErrorEntrada("Fila vacía.")
    if not t1 or not t2:
        raise ErrorEntrada("Falta una de las dos coordenadas.")
    tz = normalizar(zona)

    geo_err = None
    a1 = a2 = None
    try:
        a1 = parse_angulo(t1, positivos_sur_oeste=positivos_sur_oeste)
        a2 = parse_angulo(t2, positivos_sur_oeste=positivos_sur_oeste)
    except (ErrorEntrada, ErrorRango) as e:
        geo_err = e
    es_angulo = _parece_angulo(t1) or _parece_angulo(t2)
    if es_angulo and geo_err is not None:
        if _parece_angulo(t1) != _parece_angulo(t2):
            otro = t2 if _parece_angulo(t1) else t1
            try:
                grande = any(abs(c) > 180 for c in candidatos_numero(otro))
            except ErrorEntrada:
                grande = False
            if grande:
                raise ErrorEntrada("Mezcla de formatos: una coordenada es geográfica y la otra parece UTM.")
        raise geo_err
    if a1 is not None and a2 is not None and (es_angulo or (abs(a1.valor) <= 180 and abs(a2.valor) <= 180)):
        return _fila_geo(a1, a2, cambio_datum)
    if es_angulo:
        raise ErrorEntrada("Mezcla de formatos: una coordenada es geográfica y la otra no.")
    return _fila_utm(t1, t2, tz, cambio_datum)


def _fila_geo(a1: Angulo, a2: Angulo, cambio: bool) -> FilaInterpretada:
    if a1.eje and a2.eje:
        if a1.eje == a2.eje:
            raise ErrorEntrada("Las dos coordenadas indican el mismo eje (dos latitudes o dos longitudes).")
        inv = a1.eje == "lon"
        nota = "Orden lon/lat indicado por las letras; se invirtió." if inv else ""
    elif a1.eje or a2.eje:
        inv = (a1.eje == "lon") or (a2.eje == "lat")
        nota = "Orden lon/lat indicado por la letra de hemisferio; se invirtió." if inv else ""
    else:
        dlat = DET_LAT_CONTINENTAL if cambio else DET_LAT_AMPLIADA
        dlon = DET_LON_CONTINENTAL if cambio else DET_LON_AMPLIADA

        def valido(lat: float, lon: float) -> bool:
            return lat <= 0 and lon <= 0 and dlat[0] <= -lat <= dlat[1] and dlon[0] <= -lon <= dlon[1]

        normal = valido(a1.valor, a2.valor)
        invertido = valido(a2.valor, a1.valor)
        if normal and invertido:
            raise ErrorAmbiguo("Orden ambiguo: ambos valores sirven como latitud y como longitud. Use letras N/S y E/O.")
        inv = invertido and not normal
        nota = "Orden lon/lat detectado por rango; se invirtió." if inv else ""
        # si ningún orden calza, se deja el orden dado y el núcleo informará el motivo exacto
    lat, lon = (a2.valor, a1.valor) if inv else (a1.valor, a2.valor)
    return FilaInterpretada("geo", lat, lon, None, inv, nota)


def _fila_utm(t1: str, t2: str, tz: str, cambio: bool) -> FilaInterpretada:
    c1 = candidatos_numero(t1)
    c2 = candidatos_numero(t2)
    rn = RANGO_NORTE_CONTINENTAL if cambio else RANGO_NORTE_AMPLIADO
    re_ = RANGO_ESTE
    opciones = set()
    for x in c1:
        for y in c2:
            if rn[0] <= x <= rn[1] and re_[0] <= y <= re_[1]:
                opciones.add((x, y, False))
            if rn[0] <= y <= rn[1] and re_[0] <= x <= re_[1]:
                opciones.add((y, x, True))
    if not opciones:
        raise ErrorRango(
            f"«{t1}» / «{t2}» no corresponden a Norte ({rn[0]:.0f}–{rn[1]:.0f} m) y Este "
            f"({re_[0]:.0f}–{re_[1]:.0f} m) en ningún orden."
        )
    if len(opciones) > 1:
        lect = "; ".join(f"N={n:.3f} E={e:.3f}" for n, e, _ in sorted(opciones))
        raise ErrorAmbiguo(f"Lectura ambigua de los separadores: {lect}.")
    n, e, inv = opciones.pop()
    if not tz:
        raise ErrorEntrada("Falta el huso (zona) para coordenadas UTM.")
    z = parse_zona(tz)
    nota = "Orden Este/Norte detectado por rango; se invirtió." if inv else ""
    return FilaInterpretada("utm", n, e, z, inv, nota)


# --------------------------------------------------------------------------- pegado
def _es_letra_hemi(tok: str) -> bool:
    return tok.upper() in _HEMI


def dividir_linea(linea: str) -> list[str]:
    """Divide una línea pegada en campos: tabulador, punto y coma, ", " o espacios."""
    if "\t" in linea:
        return [c.strip() for c in linea.rstrip("\r\n").split("\t")]
    s = linea.strip()
    if ";" in s:
        return [c.strip() for c in s.split(";")]
    if re.search(r",\s", s):
        return [c.strip() for c in re.split(r"\s*,\s+", s)]
    toks = s.split()
    if len(toks) <= 3:
        return toks
    # posible datum al inicio
    pref: list[str] = []
    try:
        obtener_datum(toks[0])
        pref, toks = [toks[0]], toks[1:]
        if len(toks) <= 3:
            return pref + toks
    except KeyError:
        pass
    if any(_es_letra_hemi(t) for t in toks):
        grupos: list[list[str]] = []
        if _es_letra_hemi(toks[0]):  # letra al inicio de cada grupo
            for t in toks:
                if _es_letra_hemi(t) or not grupos:
                    grupos.append([t])
                else:
                    grupos[-1].append(t)
        else:  # letra al final de cada grupo
            actual: list[str] = []
            for t in toks:
                actual.append(t)
                if _es_letra_hemi(t):
                    grupos.append(actual)
                    actual = []
            if actual:
                grupos.append(actual)
        return pref + [" ".join(g) for g in grupos]
    if all(re.fullmatch(r"[+-]?[\d.,]+", t) for t in toks):
        if len(toks) == 6:
            return pref + [" ".join(toks[:3]), " ".join(toks[3:])]
        if len(toks) == 7:
            return pref + [" ".join(toks[:3]), " ".join(toks[3:6]), toks[6]]
        if len(toks) == 4:
            return pref + [" ".join(toks[:2]), " ".join(toks[2:])]
    return pref + toks


def es_numero_finito(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)
