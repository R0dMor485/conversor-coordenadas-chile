"""Ejecuta la aplicación desde el código fuente (sin consola): pythonw run.pyw"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from coordenadas.ui.app import main  # noqa: E402

main()
