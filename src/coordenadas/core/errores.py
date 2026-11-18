"""Errores del núcleo. Todos llevan un mensaje en español apto para mostrar al usuario."""


class ErrorCoordenada(ValueError):
    """Base de los errores de conversión."""

    @property
    def mensaje(self) -> str:
        return str(self.args[0]) if self.args else self.__class__.__name__


class ErrorEntrada(ErrorCoordenada):
    """Texto o valor de entrada no interpretable (vacío, letras, formato inválido)."""


class ErrorRango(ErrorCoordenada):
    """Valor bien escrito pero fuera del rango admitido."""


class ErrorSinParametros(ErrorRango):
    """No existen parámetros de transformación para esa latitud."""


class ErrorAmbiguo(ErrorEntrada):
    """El texto admite más de una interpretación válida; no se adivina."""
