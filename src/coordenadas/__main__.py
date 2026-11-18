"""Punto de entrada: python -m coordenadas  (o Coordenadas.exe).

Opción oculta para verificar un ejecutable empaquetado sin interacción:
    Coordenadas.exe --autoprueba informe.json
Convierte puntos conocidos, escribe y relee un .xlsx y un .csv temporales, y deja el resultado en JSON.
"""
from __future__ import annotations

import json
import sys


def autoprueba(ruta_informe: str) -> int:
    import tempfile
    import time
    from pathlib import Path

    t0 = time.perf_counter()
    inf: dict = {"ok": False}
    try:
        import openpyxl
        import tkinter  # noqa: F401  (comprueba que Tcl/Tk viene en el paquete)

        from coordenadas import config
        from coordenadas.core.constantes import Metodo
        from coordenadas.core.conversion import convertir_geo
        from coordenadas.io.proceso import ConfigProceso, procesar_archivo

        r = convertir_geo(-33.4489, -70.6693, "SIRGAS", "PSAD56", Metodo.REPLICA_EXE)
        inf["santiago_psad56"] = [round(r.norte, 3), round(r.este, 3), r.zona]
        d = Path(tempfile.mkdtemp(prefix="coord_auto_"))
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "P"
        ws.append(["Lat", "Lon"])
        ws.append([-33.4489, -70.6693])
        wb.save(d / "a.xlsx")
        res = procesar_archivo(d / "a.xlsx", "P", d / "a_convertido.xlsx", ConfigProceso("dec", {"lat": 0, "lon": 1}, "SAD69"))
        inf["xlsx"] = [res.ok, res.error, openpyxl.load_workbook(d / "a_convertido.xlsx")["P"]["F2"].value]
        (d / "b.csv").write_text("lat;lon\n-33,4489;-70,6693\n", encoding="utf-8")
        res = procesar_archivo(d / "b.csv", "b", d / "b_convertido.csv", ConfigProceso("dec", {"lat": 0, "lon": 1}, "SAD69"))
        inf["csv"] = [res.ok, res.error, (d / "b_convertido.csv").read_text(encoding="utf-8-sig").splitlines()[1]]
        # tema: si faltan los archivos de sv-ttk en el paquete, tema.aplicar cae en "clam" sin avisar;
        # aquí se exige "sun-valley-light" para que un paquete sin tema no pase la verificación.
        from tkinter import ttk

        from coordenadas.ui import tema

        raiz = tkinter.Tk()
        raiz.withdraw()
        try:
            tema.aplicar(raiz)
            inf["tema"] = ttk.Style(raiz).theme_use()
            inf["fuente_texto"] = tema.fuente("texto").actual("family")
            inf["fuente_mono"] = tema.fuente("mono").actual("family")
            inf["escala"] = round(tema.escala(), 3)
        finally:
            raiz.destroy()
        inf["carpeta_aplicacion"] = str(config.carpeta_aplicacion())
        inf["config_escribible"] = config.guardar(config.cargar())
        inf["frozen"] = bool(getattr(sys, "frozen", False))
        inf["ok"] = res.ok == 1 and inf.get("tema") == "sun-valley-light"
    except Exception as e:  # noqa: BLE001
        inf["error"] = repr(e)
    inf["segundos"] = round(time.perf_counter() - t0, 3)
    with open(ruta_informe, "w", encoding="utf-8") as f:
        json.dump(inf, f, ensure_ascii=False, indent=1)
    return 0 if inf["ok"] else 1


def principal() -> None:
    if len(sys.argv) >= 3 and sys.argv[1] == "--autoprueba":
        sys.exit(autoprueba(sys.argv[2]))
    from coordenadas.ui.app import main

    main()


if __name__ == "__main__":
    principal()
