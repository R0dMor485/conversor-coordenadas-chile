r"""Verifica los ejecutables empaquetados (F6).

Para dist\Coordenadas (onedir) y dist\onefile\Coordenadas.exe:
  1. Copia a una carpeta temporal nueva, fuera del proyecto y de .venv.
  2. Ejecuta --autoprueba con un entorno mínimo (PATH solo de Windows, sin VIRTUAL_ENV ni PYTHON*).
  3. Mide el tiempo de arranque hasta que la ventana es visible (1 arranque en frío + 3 en caliente).
  4. Informa tamaños. Resultado en build\verificacion.json.
"""
import ctypes
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import win32con
import win32gui
import win32process

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))
from coordenadas.core.constantes import Metodo  # noqa: E402
from coordenadas.core.conversion import convertir_geo  # noqa: E402

TITULO = "Conversor de Coordenadas"

try:  # coordenadas de ventana y de captura en píxeles reales (el .exe es "DPI aware")
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:  # noqa: BLE001
    pass


def tam(p: Path) -> int:
    return p.stat().st_size if p.is_file() else sum(f.stat().st_size for f in p.rglob("*") if f.is_file())


def entorno_minimo() -> dict:
    win = os.environ.get("SystemRoot", r"C:\Windows")
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith(("PYTHON", "VIRTUAL_ENV", "TCL", "TK"))}
    env["PATH"] = os.pathsep.join([str(Path(win) / "System32"), win])
    return env


def ventanas(titulo: str) -> list[int]:
    out = []

    def cb(h, _):
        if win32gui.IsWindowVisible(h) and win32gui.GetWindowText(h).startswith(titulo):
            out.append(h)
        return True

    win32gui.EnumWindows(cb, None)
    return out


def captura_ventana(hwnd: int, archivo: Path) -> None:
    """Captura solo el contenido de la ventana del .exe (PrintWindow), sin tocar nada más del escritorio."""
    import win32ui
    from PIL import Image

    izq, arr, der, aba = win32gui.GetWindowRect(hwnd)
    ancho, alto = der - izq, aba - arr
    hdc = win32gui.GetWindowDC(hwnd)
    dc_ventana = win32ui.CreateDCFromHandle(hdc)
    dc_mem = dc_ventana.CreateCompatibleDC()
    bmp = win32ui.CreateBitmap()
    bmp.CreateCompatibleBitmap(dc_ventana, ancho, alto)
    dc_mem.SelectObject(bmp)
    try:
        ctypes.windll.user32.PrintWindow(hwnd, dc_mem.GetSafeHdc(), 2)  # PW_RENDERFULLCONTENT
        datos = bmp.GetBitmapBits(True)
        Image.frombuffer("RGB", (ancho, alto), datos, "raw", "BGRX", 0, 1).save(archivo)
    finally:
        dc_mem.DeleteDC()
        dc_ventana.DeleteDC()
        win32gui.ReleaseDC(hwnd, hdc)
        win32gui.DeleteObject(bmp.GetHandle())


def arranque(exe: Path, cwd: Path, captura: Path | None = None) -> float:
    antes = set(ventanas(TITULO))
    t0 = time.perf_counter()
    p = subprocess.Popen([str(exe)], cwd=str(cwd), env=entorno_minimo())
    try:
        while time.perf_counter() - t0 < 60:
            nuevas = [h for h in ventanas(TITULO) if h not in antes]
            if nuevas:
                dt = time.perf_counter() - t0
                time.sleep(0.5)
                if captura is not None:
                    captura_ventana(nuevas[0], captura)
                for h in nuevas:
                    win32gui.PostMessage(h, win32con.WM_CLOSE, 0, 0)
                p.wait(20)
                return dt
            time.sleep(0.02)
        raise RuntimeError("la ventana no apareció en 60 s")
    finally:
        if p.poll() is None:
            p.kill()


def verificar(nombre: str, origen: Path, es_carpeta: bool) -> dict:
    tmp = Path(tempfile.mkdtemp(prefix=f"coord_{nombre}_"))
    assert RAIZ not in tmp.parents
    if es_carpeta:
        destino = tmp / "Coordenadas"
        shutil.copytree(origen, destino)
        exe = destino / "Coordenadas.exe"
    else:
        destino = tmp
        exe = tmp / "Coordenadas.exe"
        shutil.copy2(origen, exe)
    informe = tmp / "autoprueba.json"
    otra = Path(tempfile.mkdtemp(prefix="coord_cwd_"))  # directorio de trabajo distinto al del exe
    rc = subprocess.run([str(exe), "--autoprueba", str(informe)], cwd=str(otra), env=entorno_minimo(), timeout=120).returncode
    inf = json.loads(informe.read_text(encoding="utf-8"))
    esperado = convertir_geo(-33.4489, -70.6693, "SIRGAS", "PSAD56", Metodo.REPLICA_EXE)
    ok_valor = inf.get("santiago_psad56") == [round(esperado.norte, 3), round(esperado.este, 3), esperado.zona]
    ok_carpeta = Path(inf.get("carpeta_aplicacion", "")).resolve() == exe.parent.resolve()
    ok_config = (exe.parent / "config.json").exists() and inf.get("config_escribible") is True
    cap = RAIZ / "build" / f"exe_{nombre}.png"
    cap.parent.mkdir(exist_ok=True)
    tiempos = [arranque(exe, otra, cap if k == 0 else None) for k in range(4)]
    r = {
        "variante": nombre,
        "copia_en": str(exe),
        "autoprueba_rc": rc,
        "autoprueba": inf,
        "valor_igual_al_codigo_fuente": ok_valor,
        "config_junto_al_exe": ok_carpeta and ok_config,
        "captura": str(cap),
        "arranque_frio_s": round(tiempos[0], 2),
        "arranque_caliente_s": [round(t, 2) for t in tiempos[1:]],
        "tamano_MB": round(tam(origen) / 2**20, 1),
    }
    r["ok"] = rc == 0 and inf.get("ok") and ok_valor and r["config_junto_al_exe"]
    shutil.rmtree(tmp, ignore_errors=True)
    shutil.rmtree(otra, ignore_errors=True)
    return r


def main() -> int:
    res = [
        verificar("onedir", RAIZ / "dist" / "Coordenadas", True),
        verificar("onefile", RAIZ / "dist" / "onefile" / "Coordenadas.exe", False),
    ]
    z = RAIZ / "dist" / "Coordenadas.zip"
    salida = {"variantes": res, "zip_MB": round(tam(z) / 2**20, 1) if z.exists() else None}
    (RAIZ / "build").mkdir(exist_ok=True)
    (RAIZ / "build" / "verificacion.json").write_text(json.dumps(salida, ensure_ascii=False, indent=1), encoding="utf-8")
    for v in res:
        print(f"{v['variante']:8s} ok={v['ok']}  tamaño={v['tamano_MB']} MB  arranque frío={v['arranque_frio_s']} s  "
              f"caliente={v['arranque_caliente_s']} s")
    print("zip:", salida["zip_MB"], "MB")
    return 0 if all(v["ok"] for v in res) else 1


if __name__ == "__main__":
    sys.exit(main())
