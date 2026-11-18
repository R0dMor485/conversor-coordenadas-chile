import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))
sys.path.insert(0, str(RAIZ / "tests"))

import tkinter as tk  # noqa: E402

import pytest  # noqa: E402


@pytest.fixture(scope="session")
def raiz_tk():
    try:
        r = tk.Tk()
    except tk.TclError as e:  # pragma: no cover
        pytest.skip(f"Tk no disponible: {e}")
    r.withdraw()
    yield r
    r.destroy()


@pytest.fixture
def app(raiz_tk, tmp_path):
    """Ventana real de la aplicación (Toplevel oculta) con config.json temporal."""
    from coordenadas.ui.app import App

    top = tk.Toplevel(raiz_tk)
    top.withdraw()
    a = App(top, ruta_config=tmp_path / "config.json")
    yield a
    top.destroy()
