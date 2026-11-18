r"""Capturas de la interfaz en cada estado, para revisión visual contra la especificación.

Uso:  .venv\Scripts\python tools\capturas_ui.py [100 125 150] [--solo t1_resultado,...]
Deja PNG en docs\ui_capturas\<estado>_<escala>.png. Simula el escalado de pantalla fijando
``tk scaling`` (proceso con DPI awareness de sistema); la ventana se muestra unos instantes.
"""
from __future__ import annotations

import ctypes
import ctypes.wintypes as wt
import subprocess
import sys
import tempfile
import time
import tkinter as tk
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))
SALIDA = RAIZ / "docs" / "ui_capturas"


def rect_ventana(hwnd: int) -> tuple[int, int, int, int]:
    r = wt.RECT()
    if ctypes.windll.dwmapi.DwmGetWindowAttribute(wt.HWND(hwnd), 9, ctypes.byref(r), ctypes.sizeof(r)) != 0:
        ctypes.windll.user32.GetWindowRect(wt.HWND(hwnd), ctypes.byref(r))
    return r.left, r.top, r.right, r.bottom


def capturar(ventana: tk.Misc, archivo: Path) -> None:
    from PIL import ImageGrab

    ventana.attributes("-topmost", True)
    ventana.lift()
    ventana.focus_force()
    ventana.update()
    time.sleep(0.6)
    ventana.update()
    hwnd = ctypes.windll.user32.GetParent(ventana.winfo_id()) or ventana.winfo_id()
    ImageGrab.grab(rect_ventana(hwnd), all_screens=True).save(archivo)


def xlsx_ejemplo(d: Path) -> Path:
    import openpyxl

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Puntos"
    ws.append(["Punto", "Datum", "Norte", "Este", "Huso"])
    ws.append(["P1", "PSAD56", 6318400, 337470, 19])
    ws.append(["P2", "PSAD56", 6297980, 346826, 19])
    ws.append(["P3", "SAD69", "6.297.606,833", "346.642,695", "19"])
    ws.append(["P4", "SIRGAS", "x", 1, 19])
    p = d / "puntos.xlsx"
    wb.save(p)
    return p


MINIMOS = {"t1_min": "t1_resultado", "t2_min": "t2_mixta", "t3_min": "t3_resumen"}  # a tamaño mínimo
ESTADOS = ["t1_vacio", "t1_resultado", "t1_error", "t1_nucleo", "t1_decimal", "t1_gms", "ajustes",
           "t2_vacia", "t2_una_fila", "t2_mixta", "t3_vacia", "t3_cargada", "t3_columnas", "t3_salida", "t3_resumen", "t1_min", "t2_min", "t3_min"]


def un_estado(estado: str, escala: int) -> None:
    from coordenadas.ui.app import App, preparar_dpi

    preparar_dpi()
    raiz = tk.Tk()
    raiz.tk.call("tk", "scaling", 96 * escala / 100 / 72)
    # carpeta con ruta neutra (sin el nombre del usuario): la ruta del archivo aparece en las capturas
    base = Path("C:/Users/Public/Documents/coordenadas_capturas")
    base.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="capt_", dir=str(base)))
    a = App(raiz, ruta_config=tmp / "config.json")
    raiz.geometry("+20+20")
    t1, t2, t3 = a.tabs
    destino = SALIDA / f"{estado}_{escala}.png"
    minimo = estado in MINIMOS
    estado = MINIMOS.get(estado, estado)
    # fondo gris a pantalla completa detrás de la ventana: ningún borde de la captura muestra el escritorio
    fondo = tk.Toplevel(raiz)
    fondo.overrideredirect(True)
    fondo.configure(background="#808080")
    fondo.geometry(f"{raiz.winfo_screenwidth()}x{raiz.winfo_screenheight()}+0+0")
    fondo.attributes("-topmost", True)
    fondo.update()
    ventana = raiz
    if estado.startswith("t1"):
        a.nb.select(0)
        t1.v_datum_in.set("PSAD56")
        t1.panel.v_datum.set("WGS84 / SIRGAS")
        if estado == "t1_resultado":
            t1.v["norte"].set("6318400"); t1.v["este"].set("337470"); t1.v["zona"].set("19")
            t1.convertir(); t1._copiar_norte()
        elif estado == "t1_error":
            t1.v["norte"].set("6318400"); t1.v["este"].set("1337470"); t1.convertir()
        elif estado == "t1_nucleo":
            t1.v_formato.set("decimal"); t1._cambio_formato()
            t1.panel.v_datum.set("PSAD56"); t1.panel._cambio()  # con cambio de datum: sin parámetros a 60.5° S
            t1.v["lat"].set("-60.5"); t1.v["lon"].set("-70"); t1.convertir()
        elif estado == "t1_decimal":
            t1.v_formato.set("decimal"); t1._cambio_formato()
            t1.v["lat"].set("33.4489"); t1.v["lon"].set("70.6693")
            t1.panel.v_formato.set("decimal"); t1.panel._cambio(); t1.convertir()
        elif estado == "t1_gms":
            t1.v_formato.set("gms"); t1._cambio_formato()
            for k, v in {"lat_g": "33", "lat_m": "26", "lat_s": "56.04", "lon_g": "70", "lon_m": "40", "lon_s": "",
                         "lon_h": "O"}.items():
                t1.v[k].set(v)
            t1.v["lon_m"].set("6x")
            t1.panel.v_formato.set("gms"); t1.panel._cambio(); t1.convertir()
            t1.v["lon_m"].set("40"); t1.convertir()
    elif estado == "ajustes":
        raiz.update()
        ventana = a.abrir_ajustes(esperar=False)
        ventana.deiconify()
        ventana.campos_dec["decimales_grados"][2].set("12")
        ventana._validar()
    elif estado.startswith("t2"):
        a.nb.select(1)
        if estado == "t2_una_fila":
            t2.pegar("6318400\t337470\t19\tPSAD56\n")
        elif estado == "t2_mixta":
            t2.pegar("6318400\t337470\t19\tPSAD56\n337470\t6318400\t19\tPSAD56\n6318400\t337470\t19\t\n"
                     "6318400\t337470\t19\tNAD27\n6.297.606,833\t346.642,695\t19\tWGS84\n6318400\t337470\t19\t1956\n"
                     "6297980\t346826\t19\tSAD69\n")
            t2.tree.selection_set("1"); t2.tree.focus("1")
    elif estado.startswith("t3"):
        a.nb.select(2)
        if estado in ("t3_cargada", "t3_columnas", "t3_salida", "t3_resumen"):
            t3.abrir(str(xlsx_ejemplo(tmp)))
            t3.v_datum_modo.set("columna")
        if estado in ("t3_columnas", "t3_salida"):
            raiz.update()
            t3.area.lienzo.yview_moveto(0.42 if estado == "t3_columnas" else 1.0)
        if estado == "t3_resumen":
            t3.iniciar(confirmar=False)
            t0 = time.time()
            while t3.hilo.is_alive() or str(t3.b_convertir.cget("state")) == "disabled":
                raiz.update(); time.sleep(0.02)
                if time.time() - t0 > 30:
                    break
    if minimo:
        raiz.update()
        raiz.geometry("{}x{}".format(*raiz.minsize()))
    capturar(ventana, destino)
    raiz.destroy()
    print(destino.name)


def main() -> None:
    args = sys.argv[1:]
    if args and args[0] == "--hijo":
        un_estado(args[1], int(args[2]))
        return
    solo = None
    if "--solo" in args:
        i = args.index("--solo")
        solo = args[i + 1].split(",")
        args = args[:i] + args[i + 2:]
    escalas = [int(x) for x in args] or [100, 125, 150]
    SALIDA.mkdir(parents=True, exist_ok=True)
    for esc in escalas:
        for est in solo or ESTADOS:
            subprocess.run([sys.executable, __file__, "--hijo", est, str(esc)], check=False)


if __name__ == "__main__":
    main()
