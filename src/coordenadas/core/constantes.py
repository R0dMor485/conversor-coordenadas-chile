"""Constantes del método: elipsoides, datums, franjas de parámetros y límites.

Fuente de los valores: la tabla oficial publicada por el IGM (traslaciones y franjas, docs/METODO.md §3) y las
elipsoides (docs/METODO.md §2), contrastadas con las salidas del programa Datum_datum.exe.
Convención interna: latitud negativa al sur, longitud negativa al oeste, en grados.
Las franjas se expresan en grados de latitud SUR (valor positivo), como en la tabla del IGM.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum


# --------------------------------------------------------------------------- elipsoides
@dataclass(frozen=True)
class Elipsoide:
    nombre: str
    a: float  # semieje mayor (m)
    b: float  # semieje menor (m)

    @property
    def e2(self) -> float:
        """Primera excentricidad al cuadrado, (a² − b²)/a² (como en el .exe)."""
        return (self.a * self.a - self.b * self.b) / (self.a * self.a)

    @property
    def f(self) -> float:
        return (self.a - self.b) / self.a

    @property
    def n(self) -> float:
        """Tercer aplanamiento (a − b)/(a + b), base de la serie de Krüger."""
        return (self.a - self.b) / (self.a + self.b)


# Valores tal como están en Datum_datum.exe (módulo Parametros, VA 0x427590).
WGS84 = Elipsoide("WGS84 / GRS80", 6378137.0, 6356752.3141)
INTERNACIONAL_1924 = Elipsoide("Internacional 1924", 6378388.0, 6356911.946)
GRS67 = Elipsoide("GRS67 (Sudamericano 1969)", 6378160.0, 6356774.719)


# --------------------------------------------------------------------------- datums
@dataclass(frozen=True)
class Datum:
    clave: str
    nombre: str
    elipsoide: Elipsoide


SIRGAS = Datum("SIRGAS", "SIRGAS-Chile / WGS84", WGS84)
PSAD56 = Datum("PSAD56", "PSAD56", INTERNACIONAL_1924)
SAD69 = Datum("SAD69", "SAD69", GRS67)

DATUMS: dict[str, Datum] = {d.clave: d for d in (SIRGAS, PSAD56, SAD69)}
ORDEN_DATUMS = ("SIRGAS", "PSAD56", "SAD69")


def obtener_datum(clave: str) -> Datum:
    """Devuelve el datum por su clave (acepta sinónimos habituales)."""
    k = (clave or "").strip().upper().replace("-", "").replace(" ", "").replace("_", "")
    sinonimos = {
        "SIRGAS": "SIRGAS", "SIRGASCHILE": "SIRGAS", "WGS84": "SIRGAS", "WGS": "SIRGAS",
        "GRS80": "SIRGAS", "SIRGASCHILEWGS84": "SIRGAS", "SIRGAS/WGS84": "SIRGAS",
        "SIRGASCHILE/WGS84": "SIRGAS", "SIRGAS(WGS84)": "SIRGAS",
        "PSAD56": "PSAD56", "PSAD": "PSAD56", "PSAD1956": "PSAD56",
        "SAD69": "SAD69", "SAD": "SAD69", "SAD1969": "SAD69",
        "1984": "SIRGAS", "1956": "PSAD56", "1969": "SAD69", "WGS1984": "SIRGAS",  # año del datum como alternativa
    }
    if k not in sinonimos:
        raise KeyError(f"Datum desconocido: {clave!r}")
    return DATUMS[sinonimos[k]]


# --------------------------------------------------------------------------- métodos
class Metodo(str, Enum):
    TABLA_IGM = "tabla_igm"
    REPLICA_EXE = "replica_exe"

    @property
    def etiqueta(self) -> str:
        return {"tabla_igm": "Tabla IGM vigente", "replica_exe": "Réplica Datum_datum.exe"}[self.value]


# Precisión declarada del método (constante del IGM; "Delta Error" del .exe).
PRECISION_METODO_M = 5.0


# --------------------------------------------------------------------------- franjas
@dataclass(frozen=True)
class Franja:
    """Franja de latitud (grados SUR, positivos) con su traslación SIRGAS → datum local.

    Pertenencia: ``inferior <= s < superior``; los extremos se ajustan con
    ``incluye_inferior`` / ``incluye_superior``.
    """

    datum: str
    inferior: float
    superior: float
    dx: int
    dy: int
    dz: int
    incluye_inferior: bool = True
    incluye_superior: bool = False

    def contiene(self, s: float) -> bool:
        if s < self.inferior or s > self.superior:
            return False
        if s == self.inferior and not self.incluye_inferior:
            return False
        if s == self.superior and not self.incluye_superior:
            return False
        return True

    @property
    def deltas(self) -> tuple[int, int, int]:
        return (self.dx, self.dy, self.dz)

    def describir(self) -> str:
        izq = "[" if self.incluye_inferior else "("
        der = "]" if self.incluye_superior else ")"
        return f"{izq}{grados_min(self.inferior)}, {grados_min(self.superior)}{der} S"


def grados_min(s: float) -> str:
    """26.5 -> "26°30′" (solo para mensajes y documentación)."""
    g = int(s)
    m = round((s - g) * 60)
    return f"{g}°{m:02d}′"


# Valores ΔX, ΔY, ΔZ (SIRGAS → datum local; el sentido inverso usa los mismos con signo cambiado).
_P56 = [(302, -272, 360), (328, -340, 329), (352, -403, 287)]
_S69 = [(59, 11, 52), (64, 0, 32), (72, -10, 32), (79, -13, 14)]

# "Tabla IGM vigente": fronteras de la tabla oficial, continuas y sin huecos.
# Regla: [inferior, superior), y el límite superior de la última franja es inclusivo.
FRANJAS_TABLA_IGM: dict[str, tuple[Franja, ...]] = {
    "PSAD56": (
        Franja("PSAD56", 17.5, 26.0, *_P56[0]),
        Franja("PSAD56", 26.0, 36.0, *_P56[1]),
        Franja("PSAD56", 36.0, 44.0, *_P56[2], incluye_superior=True),
    ),
    "SAD69": (
        Franja("SAD69", 17.5, 32.0, *_S69[0]),
        Franja("SAD69", 32.0, 36.0, *_S69[1]),
        Franja("SAD69", 36.0, 44.0, *_S69[2]),
        Franja("SAD69", 44.0, 56.0, *_S69[3], incluye_superior=True),
    ),
}

# "Réplica Datum_datum.exe": fronteras del binario (DELTAS, VA 0x442A40):
#   17 < s < 26, 26 <= s < 36, 36 <= s < 44 y (solo SAD69) 44 <= s <= 56.
# El .exe asigna además a SAD69 la última franja para s <= 17 (rama "por defecto");
# aquí s = 17 exacto queda sin parámetros, igual que en PSAD56 (ver docs/METODO.md).
FRANJAS_REPLICA_EXE: dict[str, tuple[Franja, ...]] = {
    "PSAD56": (
        Franja("PSAD56", 17.0, 26.0, *_P56[0], incluye_inferior=False),
        Franja("PSAD56", 26.0, 36.0, *_P56[1]),
        Franja("PSAD56", 36.0, 44.0, *_P56[2]),
    ),
    "SAD69": (
        Franja("SAD69", 17.0, 26.0, *_S69[0], incluye_inferior=False),
        Franja("SAD69", 26.0, 36.0, *_S69[1]),
        Franja("SAD69", 36.0, 44.0, *_S69[2]),
        Franja("SAD69", 44.0, 56.0, *_S69[3], incluye_superior=True),
    ),
}

FRANJAS: dict[Metodo, dict[str, tuple[Franja, ...]]] = {
    Metodo.TABLA_IGM: FRANJAS_TABLA_IGM,
    Metodo.REPLICA_EXE: FRANJAS_REPLICA_EXE,
}


# --------------------------------------------------------------------------- límites
# Con cambio de datum (Chile continental): longitud 66° O < λ <= 77° O, como el .exe
# (66.0 rechazado, 77.0 aceptado). La latitud la limitan las franjas.
LON_CONTINENTAL_OESTE_MIN = 66.0  # exclusivo
LON_CONTINENTAL_OESTE_MAX = 77.0  # inclusivo

# Sin cambio de datum: rango ampliado (incluye Isla de Pascua, Salas y Gómez, Juan Fernández,
# San Félix y el Territorio Chileno Antártico). Solo hemisferio sur.
LAT_AMPLIADA_SUR_MIN = 0.0
LAT_AMPLIADA_SUR_MAX = 80.0
LON_AMPLIADA_OESTE_MIN = 50.0
LON_AMPLIADA_OESTE_MAX = 120.0

# Husos admitidos en entradas UTM.
HUSOS_CONTINENTALES = (18, 19)
HUSO_AMPLIADO_MIN = 11
HUSO_AMPLIADO_MAX = 22

# Rangos de Este y Norte admitidos en entradas UTM (hemisferio sur).
ESTE_MIN = 100_000.0
ESTE_MAX = 900_000.0
NORTE_MIN = 0.0  # exclusivo
NORTE_MAX = 10_000_000.0  # inclusivo (ecuador)

# Distancia máxima al meridiano central al forzar el huso de salida.
MAX_DIST_MC_FORZADO = 9.0

# UTM
K0 = 0.9996
FALSO_ESTE = 500_000.0
FALSO_NORTE_SUR = 10_000_000.0

RAD = math.pi / 180.0
