#!/usr/bin/env python3
"""Dice si el workspace de colcon esta al dia con el codigo del repositorio.

Uso:
    python3 herramientas/comprobar_workspace.py [--ws ~/deepracer_sim_ws] [--silencioso]

Sale con 0 si todo esta al dia y con 1 si hay que recompilar, diciendo que
paquete y por que. Solo usa la biblioteca estandar: se puede llamar antes de
cargar ROS, y por eso lo usa robot.sh antes de lanzar nada.

POR QUE EXISTE
--------------
El 2026-10-06, despues de un 'git pull', 'robot.sh robot1 nav2' murio con
«executable 'agente' not found on the libexec directory». El ejecutable se habia
declarado en setup.py el 7-sep y el workspace se compilo por ultima vez el 4-sep.
Nada aviso antes: verificar_instalacion.sh comprobaba que EXISTIERA un workspace
compilado, no que estuviera AL DIA, y el error aparecio dentro de un launch,
acusando a un ejecutable en vez de a la compilacion.

QUE CUENTA COMO DESACTUALIZADO, Y QUE NO
----------------------------------------
Con 'colcon build --symlink-install' casi todo se enlaza, asi que editar un .py,
un .yaml o un launch YA INSTALADO no exige recompilar. Avisar en esos casos seria
una falsa alarma, y una comprobacion que avisa de mas acaba ignorada. Solo cuenta:

  1. Un paquete que nunca se compilo, o cuya ultima compilacion fallo.
  2. Un archivo que define la compilacion modificado despues de ella:
     package.xml, setup.py, setup.cfg, CMakeLists.txt, mensajes y C/C++.
  3. Algo que el codigo declara y la instalacion no tiene: un ejecutable de
     'console_scripts' sin instalar, o un archivo nuevo dentro de una carpeta que
     el CMakeLists instala en share/. Este es el caso del 6-oct.

La fecha de la ultima compilacion de cada paquete es la de
build/<paquete>/colcon_build.rc, que colcon reescribe en cada compilacion. Un
'git pull' deja con la hora del pull los archivos que cambia, asi que lo que
llego despues de compilar queda mas nuevo que esa marca.
"""
import argparse
import os
import re
import sys
import xml.etree.ElementTree as ET

REPO = os.path.realpath(os.path.join(os.path.dirname(__file__), ".."))
PAQUETES_DIR = os.path.join(REPO, "Robot", "aws-deepracer")

DEFINEN_COMPILACION = {"package.xml", "setup.py", "setup.cfg", "CMakeLists.txt"}
EXT_COMPILADAS = (".msg", ".srv", ".action", ".c", ".cc", ".cpp", ".h", ".hpp")
IGNORAR_DIRS = {"__pycache__", ".pytest_cache", "test", ".git"}


def paquetes(raiz):
    """(nombre, ruta, tipo) de cada package.xml bajo raiz, como los ve colcon."""
    for dirpath, dirnames, filenames in os.walk(raiz):
        if "COLCON_IGNORE" in filenames:
            dirnames[:] = []
            continue
        dirnames[:] = [d for d in dirnames if d not in IGNORAR_DIRS]
        if "package.xml" in filenames:
            xml = ET.parse(os.path.join(dirpath, "package.xml")).getroot()
            nombre = xml.findtext("name").strip()
            tipo = (xml.findtext("export/build_type") or "ament_cmake").strip()
            yield nombre, dirpath, tipo
            dirnames[:] = []   # un paquete no contiene otro


def archivos(ruta):
    for dirpath, dirnames, filenames in os.walk(ruta):
        dirnames[:] = [d for d in dirnames if d not in IGNORAR_DIRS]
        for f in filenames:
            if not f.endswith(".pyc"):
                yield os.path.join(dirpath, f)


def ejecutables_declarados(setup_py):
    """Nombres de 'console_scripts' en un setup.py, sin importarlo."""
    texto = open(setup_py, encoding="utf-8").read()
    bloque = re.search(r"console_scripts['\"]\s*:\s*\[(.*?)\]", texto, re.S)
    if not bloque:
        return []
    return re.findall(r"['\"]\s*([\w.-]+)\s*=\s*[\w.]+\s*:\s*\w+", bloque.group(1))


def carpetas_instaladas_en_share(cmakelists):
    """Carpetas de install(DIRECTORY ... DESTINATION share/${PROJECT_NAME})."""
    texto = " ".join(open(cmakelists, encoding="utf-8").read().split())
    carpetas = []
    for orden in re.findall(r"install\s*\(\s*DIRECTORY\s+([^)]*)\)", texto):
        if not re.search(r"DESTINATION\s+share/\$\{PROJECT_NAME\}", orden):
            continue
        antes = orden.split("DESTINATION")[0].split()
        carpetas += [c.rstrip("/") for c in antes if not c.isupper()]
    return carpetas


def revisar(nombre, ruta, tipo, ws):
    """Lista de motivos por los que 'nombre' necesita recompilarse (vacia = al dia)."""
    marca = os.path.join(ws, "build", nombre, "colcon_build.rc")
    if not os.path.exists(marca):
        return ["nunca se ha compilado en este workspace"]
    if open(marca).read().strip() not in ("", "0"):
        return ["su ultima compilacion fallo"]
    compilado = os.path.getmtime(marca)
    motivos = []

    for f in archivos(ruta):
        base = os.path.basename(f)
        if (base in DEFINEN_COMPILACION or base.endswith(EXT_COMPILADAS)) \
                and os.path.getmtime(f) > compilado:
            motivos.append(f"cambio despues de compilar: {os.path.relpath(f, ruta)}")

    instalado = os.path.join(ws, "install", nombre)
    if tipo == "ament_python" and os.path.exists(os.path.join(ruta, "setup.py")):
        for exe in ejecutables_declarados(os.path.join(ruta, "setup.py")):
            if not os.path.exists(os.path.join(instalado, "lib", nombre, exe)):
                motivos.append(f"el ejecutable '{exe}' esta en setup.py y no instalado")
    if tipo == "ament_cmake" and os.path.exists(os.path.join(ruta, "CMakeLists.txt")):
        share = os.path.join(instalado, "share", nombre)
        for carpeta in carpetas_instaladas_en_share(os.path.join(ruta, "CMakeLists.txt")):
            origen = os.path.join(ruta, carpeta)
            for f in archivos(origen) if os.path.isdir(origen) else []:
                rel = os.path.relpath(f, ruta)
                if not os.path.lexists(os.path.join(share, rel)):
                    motivos.append(f"archivo nuevo sin instalar: {rel}")
    return motivos


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--ws", default=os.environ.get("DEEPRACER_WS",
                                                   os.path.expanduser("~/deepracer_sim_ws")))
    ap.add_argument("--silencioso", action="store_true",
                    help="no imprimir nada si todo esta al dia")
    args = ap.parse_args()
    ws = os.path.realpath(os.path.expanduser(args.ws))

    desactualizados = {}
    total = 0
    for nombre, ruta, tipo in sorted(paquetes(PAQUETES_DIR)):
        total += 1
        motivos = revisar(nombre, ruta, tipo, ws)
        if motivos:
            desactualizados[nombre] = motivos

    if not desactualizados:
        if not args.silencioso:
            print(f"Workspace al dia: {total} paquetes compilados despues de su ultimo cambio.")
        return 0

    print(f"EL WORKSPACE ESTA DESACTUALIZADO: {len(desactualizados)} de {total} paquetes "
          f"no corresponden al codigo del repositorio.", file=sys.stderr)
    for nombre, motivos in desactualizados.items():
        print(f"  {nombre}:", file=sys.stderr)
        for m in motivos[:4]:
            print(f"    - {m}", file=sys.stderr)
        if len(motivos) > 4:
            print(f"    - ... y {len(motivos) - 4} mas", file=sys.stderr)
    print(f"\nRecompilar (tarda menos de un minuto):\n  cd {args.ws} && colcon build "
          f"--symlink-install", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
