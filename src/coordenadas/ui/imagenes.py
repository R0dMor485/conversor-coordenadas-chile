"""Imágenes de la interfaz dibujadas en el momento (bordes redondeados, indicadores e íconos).

Sin dependencias externas: cada imagen se rasteriza con funciones de distancia con signo y
antialiasing analítico, y se codifica como PNG RGBA (zlib) para ``tk.PhotoImage``, que conserva la
transparencia parcial. Las imágenes se generan al tamaño de la escala de pantalla vigente, así que
siempre son nítidas (100 %, 125 %, 150 %…). Las coordenadas de los íconos están en una cuadrícula
de 16 × 16 unidades y se escalan al tamaño pedido.
"""
from __future__ import annotations

import base64
import math
import struct
import zlib
from typing import Callable

Distancia = Callable[[float, float], float]


def rgb(color: str) -> tuple[int, int, int]:
    c = color.lstrip("#")
    return int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)


# --------------------------------------------------------------------------- distancias con signo
def caja(x0: float, y0: float, x1: float, y1: float, r: float = 0.0) -> Distancia:
    """Rectángulo [x0, x1] × [y0, y1] con esquinas de radio ``r`` (negativo = dentro)."""
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    hw, hh = (x1 - x0) / 2, (y1 - y0) / 2
    r = max(0.0, min(r, hw, hh))

    def d(x: float, y: float) -> float:
        qx = abs(x - cx) - (hw - r)
        qy = abs(y - cy) - (hh - r)
        return math.hypot(max(qx, 0.0), max(qy, 0.0)) + min(max(qx, qy), 0.0) - r

    return d


def circulo(cx: float, cy: float, r: float) -> Distancia:
    return lambda x, y: math.hypot(x - cx, y - cy) - r


def segmento(ax: float, ay: float, bx: float, by: float, grosor: float) -> Distancia:
    """Trazo recto de extremos redondeados."""
    dx, dy = bx - ax, by - ay
    l2 = dx * dx + dy * dy or 1e-9
    r = grosor / 2

    def d(x: float, y: float) -> float:
        t = max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / l2))
        return math.hypot(x - ax - t * dx, y - ay - t * dy) - r

    return d


def linea(puntos: list[tuple[float, float]], grosor: float) -> Distancia:
    segs = [segmento(*puntos[i], *puntos[i + 1], grosor) for i in range(len(puntos) - 1)]
    return lambda x, y: min(s(x, y) for s in segs)


def contorno(forma: Distancia, grosor: float) -> Distancia:
    """Banda de ``grosor`` por dentro del borde de ``forma``."""
    return lambda x, y: abs(forma(x, y) + grosor / 2) - grosor / 2


def trazo_centrado(forma: Distancia, grosor: float) -> Distancia:
    """Banda de ``grosor`` centrada en el borde de ``forma``."""
    return lambda x, y: abs(forma(x, y)) - grosor / 2


# --------------------------------------------------------------------------- lienzo RGBA
class Lienzo:
    """Lienzo RGBA con alfa premultiplicado (floats)."""

    def __init__(self, ancho: int, alto: int, fondo: str | None = None):
        self.w, self.h = max(1, int(ancho)), max(1, int(alto))
        self.p = [0.0] * (self.w * self.h * 4)
        if fondo:
            self.pintar(lambda x, y: -1e9, fondo)

    def pintar(self, dist: Distancia, color: str, alfa: float = 1.0) -> "Lienzo":
        r, g, b = rgb(color)
        p, w = self.p, self.w
        for y in range(self.h):
            fy = y + 0.5
            for x in range(w):
                cob = 0.5 - dist(x + 0.5, fy)
                if cob <= 0.0:
                    continue
                a = (1.0 if cob >= 1.0 else cob) * alfa
                k = 1.0 - a
                i = (y * w + x) * 4
                p[i] = r * a + p[i] * k
                p[i + 1] = g * a + p[i + 1] * k
                p[i + 2] = b * a + p[i + 2] * k
                p[i + 3] = a + p[i + 3] * k
        return self

    def borrar(self, dist: Distancia) -> "Lienzo":
        """Vuelve transparente lo que cubre ``dist``."""
        p, w = self.p, self.w
        for y in range(self.h):
            fy = y + 0.5
            for x in range(w):
                cob = 0.5 - dist(x + 0.5, fy)
                if cob <= 0.0:
                    continue
                k = 1.0 - (1.0 if cob >= 1.0 else cob)
                i = (y * w + x) * 4
                p[i] *= k
                p[i + 1] *= k
                p[i + 2] *= k
                p[i + 3] *= k
        return self

    def png(self) -> bytes:
        filas = bytearray()
        p, w = self.p, self.w
        for y in range(self.h):
            filas.append(0)
            for x in range(w):
                i = (y * w + x) * 4
                a = p[i + 3]
                if a <= 1e-6:
                    filas += b"\0\0\0\0"
                    continue
                filas += bytes((
                    min(255, int(p[i] / a + 0.5)), min(255, int(p[i + 1] / a + 0.5)),
                    min(255, int(p[i + 2] / a + 0.5)), min(255, int(a * 255 + 0.5)),
                ))

        def trozo(tipo: bytes, datos: bytes) -> bytes:
            return struct.pack(">I", len(datos)) + tipo + datos + struct.pack(">I", zlib.crc32(tipo + datos) & 0xFFFFFFFF)

        return (b"\x89PNG\r\n\x1a\n" + trozo(b"IHDR", struct.pack(">IIBBBBB", self.w, self.h, 8, 6, 0, 0, 0))
                + trozo(b"IDAT", zlib.compress(bytes(filas), 6)) + trozo(b"IEND", b""))

    def base64(self) -> str:
        return base64.b64encode(self.png()).decode("ascii")


# --------------------------------------------------------------------------- piezas de controles
def rect_redondeado(ancho: int, alto: int, radio: float, relleno: str | None, borde: str | None,
                    grosor: float = 1.0, lados: str = "izq,der") -> Lienzo:
    """Caja con borde. ``lados`` indica qué lados verticales son reales: "izq", "der" o ambos;
    el lado ausente se prolonga fuera del lienzo (piezas de un selector segmentado)."""
    ext = radio + 2
    x0 = 0.0 if "izq" in lados else -ext
    x1 = float(ancho) if "der" in lados else ancho + ext
    forma = caja(x0, 0.0, x1, float(alto), radio)
    lz = Lienzo(ancho, alto)
    if relleno:
        lz.pintar(forma, relleno)
    if borde and grosor > 0:
        lz.pintar(contorno(forma, grosor), borde)
    return lz


def escalar(puntos: list[tuple[float, float]], s: float) -> list[tuple[float, float]]:
    return [(x * s, y * s) for x, y in puntos]


def elipse(cx: float, cy: float, a: float, b: float) -> Distancia:
    """Distancia aproximada (primer orden) a una elipse de semiejes a, b: f / |grad f| con f = (x/a)² + (y/b)² - 1."""
    def d(x: float, y: float) -> float:
        dx, dy = x - cx, y - cy
        f = (dx / a) ** 2 + (dy / b) ** 2 - 1.0
        gn = math.hypot(2 * dx / (a * a), 2 * dy / (b * b))
        return f / gn if gn > 1e-9 else -min(a, b)

    return d


def icono_app(tam: int, color: str = "#FFFFFF", fondo: str = "#1F5FBF") -> Lienzo:
    """Ícono de la aplicación (ventana, barra de tareas y .exe): globo blanco sobre un cuadrado azul."""
    s = tam / 16.0
    g = max(1.15, 0.85 * s)  # grosor de trazo: nunca menor a ~1 px, para que se lea a 16 px
    lz = Lienzo(tam, tam)
    lz.pintar(caja(0.0, 0.0, float(tam), float(tam), 3.4 * s), fondo)
    lz.pintar(contorno(circulo(8 * s, 8 * s, 5.9 * s), g), color)
    lz.pintar(trazo_centrado(elipse(8 * s, 8 * s, 2.5 * s, 5.9 * s), g), color)  # meridiano
    lz.pintar(segmento(2.1 * s + g / 2, 8 * s, 13.9 * s - g / 2, 8 * s, g), color)  # ecuador
    if tam >= 24:  # paralelos: solo cuando hay píxeles de sobra
        for dy in (-2.8, 2.8):
            semi = (5.9 ** 2 - dy ** 2) ** 0.5
            lz.pintar(segmento((8 - semi) * s + g / 2, (8 + dy) * s, (8 + semi) * s - g / 2, (8 + dy) * s, g * 0.85), color)
    return lz


# --------------------------------------------------------------------------- íconos (cuadrícula 16 × 16)
def icono(nombre: str, color: str, tam: int, color2: str = "#FFFFFF") -> Lienzo:
    s = tam / 16.0
    g = max(1.0, 1.5 * s)  # grosor de trazo
    lz = Lienzo(tam, tam)
    if nombre == "copiar":
        atras = caja(5.5 * s, 1.5 * s, 14.5 * s, 10.5 * s, 2.2 * s)
        frente = caja(1.5 * s, 5.5 * s, 10.5 * s, 14.5 * s, 2.2 * s)
        lz.pintar(contorno(atras, g * 0.9), color)
        lz.borrar(lambda x, y: frente(x, y) - g * 0.9)
        lz.pintar(contorno(frente, g * 0.9), color)
    elif nombre == "ajustes":
        lz.pintar(segmento(1.5 * s, 4.5 * s, 14.5 * s, 4.5 * s, g * 0.9), color)
        lz.pintar(segmento(1.5 * s, 11.5 * s, 14.5 * s, 11.5 * s, g * 0.9), color)
        for cx, cy in ((10.0, 4.5), (5.5, 11.5)):
            lz.borrar(circulo(cx * s, cy * s, 3.3 * s))
            lz.pintar(contorno(circulo(cx * s, cy * s, 2.6 * s), g * 0.9), color)
    elif nombre == "check":
        lz.pintar(linea(escalar([(2.5, 8.5), (6.2, 12.0), (13.5, 4.0)], s), g * 1.15), color)
    elif nombre == "alerta":  # círculo con "!"
        lz.pintar(contorno(circulo(8 * s, 8 * s, 7 * s), g * 0.95), color)
        lz.pintar(segmento(8 * s, 4.4 * s, 8 * s, 8.8 * s, g * 1.05), color)
        lz.pintar(circulo(8 * s, 11.4 * s, 0.95 * s * max(1.0, g / 1.5)), color)
    elif nombre == "aviso":  # triángulo con "!"
        tri = [(8.0, 1.6), (15.0, 14.2), (1.0, 14.2), (8.0, 1.6)]
        lz.pintar(linea(escalar(tri, s), g * 0.95), color)
        lz.pintar(segmento(8 * s, 6.0 * s, 8 * s, 9.6 * s, g * 1.05), color)
        lz.pintar(circulo(8 * s, 11.9 * s, 0.9 * s * max(1.0, g / 1.5)), color)
    elif nombre == "cruz":  # círculo con ✕
        lz.pintar(contorno(circulo(8 * s, 8 * s, 7 * s), g * 0.95), color)
        lz.pintar(segmento(5.4 * s, 5.4 * s, 10.6 * s, 10.6 * s, g), color)
        lz.pintar(segmento(10.6 * s, 5.4 * s, 5.4 * s, 10.6 * s, g), color)
    elif nombre == "abajo":
        lz.pintar(linea(escalar([(4.0, 6.0), (8.0, 10.0), (12.0, 6.0)], s), g), color)
    elif nombre == "arriba":
        lz.pintar(linea(escalar([(4.0, 10.0), (8.0, 6.0), (12.0, 10.0)], s), g), color)
    elif nombre == "carpeta":
        forma = caja(1.5 * s, 3.5 * s, 14.5 * s, 13.5 * s, 1.8 * s)
        lz.pintar(contorno(forma, g * 0.9), color)
        lz.pintar(segmento(1.5 * s, 6.2 * s, 14.5 * s, 6.2 * s, g * 0.9), color)
    elif nombre == "radio":
        lz.pintar(circulo(8 * s, 8 * s, 7.3 * s), color2)
        lz.pintar(contorno(circulo(8 * s, 8 * s, 7.3 * s), max(1.0, s)), color)
    elif nombre == "radio_sel":
        lz.pintar(circulo(8 * s, 8 * s, 7.3 * s), color2)
        lz.pintar(contorno(circulo(8 * s, 8 * s, 7.3 * s), max(1.5, 1.5 * s)), color)
        lz.pintar(circulo(8 * s, 8 * s, 3.6 * s), color)
    elif nombre == "casilla":
        forma = caja(1.0 * s, 1.0 * s, 15.0 * s, 15.0 * s, 3.2 * s)
        lz.pintar(forma, color2)
        lz.pintar(contorno(forma, max(1.0, s)), color)
    elif nombre == "casilla_sel":
        forma = caja(1.0 * s, 1.0 * s, 15.0 * s, 15.0 * s, 3.2 * s)
        lz.pintar(forma, color)
        lz.pintar(linea(escalar([(4.3, 8.3), (6.9, 10.9), (11.8, 5.4)], s), max(1.4, 1.6 * s)), color2)
    else:
        raise ValueError(nombre)
    return lz
