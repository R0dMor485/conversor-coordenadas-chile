@echo off
rem ===========================================================================
rem  Construye Coordenadas.exe (portable) desde cero.
rem    1) pruebas   2) onedir -> dist\Coordenadas\   3) zip   4) onefile -> dist\onefile\
rem  Requisitos: .venv con Python 3.12 y requirements-dev.txt instalados.
rem  Uso: build.bat            (todo)
rem       build.bat sinpruebas (omite las pruebas)
rem ===========================================================================
setlocal
cd /d "%~dp0"
set PY=.venv\Scripts\python.exe
if not exist "%PY%" (
  echo No se encuentra %PY%. Cree el entorno: py -3.12 -m venv .venv ^&^& .venv\Scripts\pip install -r requirements-dev.txt
  exit /b 1
)
set PYTHONUTF8=1

if /i not "%~1"=="sinpruebas" (
  echo === Pruebas ===
  "%PY%" -m pytest -q -m "lento or not lento" || (echo PRUEBAS FALLIDAS: no se construye. & exit /b 1)
)

set EXCL=--exclude-module numpy --exclude-module pandas --exclude-module PIL --exclude-module pyproj ^
 --exclude-module py_mini_racer --exclude-module pytest --exclude-module _pytest --exclude-module win32com ^
 --exclude-module pythoncom --exclude-module pywintypes --exclude-module pywinauto --exclude-module comtypes ^
 --exclude-module capstone --exclude-module pefile --exclude-module requests --exclude-module bs4 ^
 --exclude-module lxml --exclude-module pypdf --exclude-module IPython --exclude-module matplotlib

set COMUN=--noconfirm --clean --windowed --paths src --workpath build\pyi --specpath build\pyi ^
 --collect-submodules coordenadas --collect-data sv_ttk --icon "%~dp0recursos\coordenadas.ico" %EXCL%

echo === onedir ===
if exist dist\Coordenadas rmdir /s /q dist\Coordenadas
"%PY%" -m PyInstaller %COMUN% --onedir --name Coordenadas --distpath dist src\coordenadas\__main__.py || exit /b 1

copy /y LICENCIAS_TERCEROS.txt dist\Coordenadas\ >nul
copy /y LICENSE dist\Coordenadas\ >nul
echo === zip ===
if exist dist\Coordenadas.zip del /q dist\Coordenadas.zip
powershell -NoProfile -Command "Compress-Archive -Path 'dist\Coordenadas' -DestinationPath 'dist\Coordenadas.zip'" || exit /b 1

echo === onefile ===
if exist dist\onefile rmdir /s /q dist\onefile
"%PY%" -m PyInstaller %COMUN% --onefile --name Coordenadas --distpath dist\onefile src\coordenadas\__main__.py || exit /b 1

copy /y LICENCIAS_TERCEROS.txt dist\onefile\ >nul
copy /y LICENSE dist\onefile\ >nul
echo === Verificacion (copia fuera del proyecto, autoprueba y tiempo de arranque) ===
"%PY%" tools\verificar_exe.py || exit /b 1

echo.
echo Listo:
echo   dist\Coordenadas\Coordenadas.exe   (carpeta portable)
echo   dist\Coordenadas.zip
echo   dist\onefile\Coordenadas.exe       (un solo archivo)
endlocal
