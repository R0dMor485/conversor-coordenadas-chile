"""Opciones de la aplicación y su persistencia en config.json (junto al ejecutable).

Si el archivo no existe, está dañado o no se puede escribir, la aplicación sigue con los valores
por defecto, sin errores.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .core.constantes import Metodo


@dataclass
class Opciones:
    metodo: str = Metodo.TABLA_IGM.value
    decimales_utm: int = 0
    decimales_grados: int = 6
    separador_decimal: str = "."
    positivos_sur_oeste: bool = True
    zona_salida: str = "auto"  # "auto", "18" o "19" (global para las tres pestañas)
    ultimas: dict = field(default_factory=dict)  # últimas selecciones de la interfaz

    @property
    def metodo_enum(self) -> Metodo:
        return Metodo(self.metodo)


def carpeta_aplicacion() -> Path:
    """Carpeta del ejecutable (empaquetado) o raíz del proyecto (desde el código)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def ruta_config() -> Path:
    return carpeta_aplicacion() / "config.json"


def _validar(datos: dict) -> Opciones:
    op = Opciones()
    if datos.get("metodo") in {m.value for m in Metodo}:
        op.metodo = datos["metodo"]
    for nombre, lo, hi in (("decimales_utm", 0, 4), ("decimales_grados", 0, 10)):
        v = datos.get(nombre)
        if isinstance(v, int) and not isinstance(v, bool) and lo <= v <= hi:
            setattr(op, nombre, v)
    if datos.get("separador_decimal") in (".", ","):
        op.separador_decimal = datos["separador_decimal"]
    if isinstance(datos.get("positivos_sur_oeste"), bool):
        op.positivos_sur_oeste = datos["positivos_sur_oeste"]
    if datos.get("zona_salida") in ("auto", "18", "19"):
        op.zona_salida = datos["zona_salida"]
    if isinstance(datos.get("ultimas"), dict):
        op.ultimas = {str(k): v for k, v in datos["ultimas"].items() if isinstance(v, (str, int, float, bool))}
    return op


def cargar(ruta: Path | None = None) -> Opciones:
    ruta = ruta or ruta_config()
    try:
        with open(ruta, encoding="utf-8") as f:
            datos = json.load(f)
        if not isinstance(datos, dict):
            return Opciones()
        return _validar(datos)
    except (OSError, ValueError):
        return Opciones()


def guardar(op: Opciones, ruta: Path | None = None) -> bool:
    """Escribe config.json de forma atómica. Devuelve False si no se pudo (sin lanzar)."""
    ruta = ruta or ruta_config()
    try:
        fd, tmp = tempfile.mkstemp(prefix=".config-", suffix=".tmp", dir=str(ruta.parent))
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(asdict(op), f, ensure_ascii=False, indent=2)
        os.replace(tmp, ruta)
        return True
    except OSError:
        try:
            os.unlink(tmp)  # type: ignore[possibly-undefined]
        except Exception:
            pass
        return False
