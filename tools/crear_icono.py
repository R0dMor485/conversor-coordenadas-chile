r"""Genera recursos\coordenadas.ico (ícono del .exe y de la barra de tareas) con el mismo dibujo del ícono
de la ventana (ui/imagenes.py). Uso:  .venv\Scripts\python tools\crear_icono.py"""
import io
import sys
from pathlib import Path

from PIL import Image

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))
from coordenadas.ui import imagenes as im  # noqa: E402

TAMANOS = (256, 128, 64, 48, 40, 32, 24, 20, 16)


def main() -> None:
    destino = RAIZ / "recursos" / "coordenadas.ico"
    destino.parent.mkdir(exist_ok=True)
    imgs = [Image.open(io.BytesIO(im.icono_app(n).png())).convert("RGBA") for n in TAMANOS]
    imgs[0].save(destino, format="ICO", sizes=[(n, n) for n in TAMANOS], append_images=imgs[1:])
    ico = Image.open(destino)
    print(destino, "->", sorted(ico.info.get("sizes", [])))


if __name__ == "__main__":
    main()
