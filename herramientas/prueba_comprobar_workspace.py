#!/usr/bin/env python3
"""Pruebas de comprobar_workspace.py. No necesitan ROS ni compilar nada.

Se arma un paquete y un workspace de mentira en una carpeta temporal y se juega
con las fechas de los archivos. Cubren las dos mitades del contrato: que detecte
el caso del 2026-10-06 (un ejecutable declarado y no instalado) y que NO avise
cuando editar un archivo ya enlazado no exige recompilar.

Uso:  python3 herramientas/prueba_comprobar_workspace.py
"""

import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from comprobar_workspace import (PAQUETES_DIR, carpetas_instaladas_en_share,
                                 ejecutables_declarados, paquetes, revisar)

FALLOS = []
ANTES = time.time() - 3600    # "cuando se compilo"
DESPUES = time.time()         # "lo que llego con el git pull"


def comprobar(nombre, condicion, detalle=""):
    if condicion:
        print(f"  ok   {nombre}")
    else:
        print(f"  FALLO {nombre} {detalle}")
        FALLOS.append(nombre)


def escribir(ruta, texto="", fecha=ANTES):
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with open(ruta, "w") as f:
        f.write(texto)
    os.utime(ruta, (fecha, fecha))


def xml_paquete(nombre, tipo):
    return (f"<package><name>{nombre}</name>"
            f"<export><build_type>{tipo}</build_type></export></package>")


SETUP = """setup(name='pkgpy', entry_points={'console_scripts': [
    'coordinador = pkgpy.coordinador:main',
    'agente = pkgpy.agente:main',
]})"""

CMAKE = """cmake_minimum_required(VERSION 3.5)
install(DIRECTORY launch config
  DESTINATION share/${PROJECT_NAME}
)
install(DIRECTORY include/ DESTINATION include)
"""


def paquete_python(raiz, ws, instalados):
    ruta = os.path.join(raiz, "pkgpy")
    escribir(os.path.join(ruta, "package.xml"), xml_paquete("pkgpy", "ament_python"))
    escribir(os.path.join(ruta, "setup.py"), SETUP)
    escribir(os.path.join(ruta, "pkgpy", "agente.py"))
    escribir(os.path.join(ws, "build", "pkgpy", "colcon_build.rc"), "0")
    for exe in instalados:
        escribir(os.path.join(ws, "install", "pkgpy", "lib", "pkgpy", exe))
    return ruta


def paquete_cmake(raiz, ws):
    ruta = os.path.join(raiz, "pkgcm")
    escribir(os.path.join(ruta, "package.xml"), xml_paquete("pkgcm", "ament_cmake"))
    escribir(os.path.join(ruta, "CMakeLists.txt"), CMAKE)
    escribir(os.path.join(ruta, "config", "params.yaml"))
    escribir(os.path.join(ruta, "launch", "sim.launch.py"))
    escribir(os.path.join(ruta, "include", "x.hpp"))
    escribir(os.path.join(ws, "build", "pkgcm", "colcon_build.rc"), "0")
    share = os.path.join(ws, "install", "pkgcm", "share", "pkgcm")
    escribir(os.path.join(share, "config", "params.yaml"))
    escribir(os.path.join(share, "launch", "sim.launch.py"))
    return ruta


def main():
    print("== 1. Lectura de lo que el codigo declara ==")
    coord = os.path.join(PAQUETES_DIR, "coordinacion", "setup.py")
    comprobar("lee los ejecutables reales de coordinacion",
              sorted(ejecutables_declarados(coord)) == ["agente", "coordinador"],
              str(ejecutables_declarados(coord)))
    bringup = os.path.join(PAQUETES_DIR, "deepracer_bringup", "CMakeLists.txt")
    comprobar("lee las carpetas reales que instala deepracer_bringup",
              carpetas_instaladas_en_share(bringup)
              == ["launch", "config", "maps", "behavior_trees"],
              str(carpetas_instaladas_en_share(bringup)))
    nombres = sorted(n for n, _, _ in paquetes(PAQUETES_DIR))
    comprobar("encuentra los 8 paquetes del repositorio", len(nombres) == 8, str(nombres))

    with tempfile.TemporaryDirectory() as tmp:
        raiz, ws = os.path.join(tmp, "src"), os.path.join(tmp, "ws")

        print("\n== 2. Python: el caso del 2026-10-06 ==")
        ruta = paquete_python(raiz, ws, ["coordinador"])
        m = revisar("pkgpy", ruta, "ament_python", ws)
        comprobar("detecta el ejecutable declarado y no instalado",
                  any("'agente'" in x for x in m), str(m))
        comprobar("no acusa al que si esta instalado",
                  not any("'coordinador'" in x for x in m), str(m))

        escribir(os.path.join(ws, "install", "pkgpy", "lib", "pkgpy", "agente"))
        comprobar("al dia cuando los dos estan instalados",
                  revisar("pkgpy", ruta, "ament_python", ws) == [])

        escribir(os.path.join(ruta, "pkgpy", "agente.py"), "editado", DESPUES)
        comprobar("NO avisa por editar un modulo .py (esta enlazado)",
                  revisar("pkgpy", ruta, "ament_python", ws) == [])

        escribir(os.path.join(ruta, "setup.py"), SETUP, DESPUES)
        m = revisar("pkgpy", ruta, "ament_python", ws)
        comprobar("avisa si setup.py cambio despues de compilar",
                  any("setup.py" in x for x in m), str(m))

        print("\n== 3. CMake: carpetas instaladas en share/ ==")
        ruta = paquete_cmake(raiz, ws)
        comprobar("al dia recien compilado", revisar("pkgcm", ruta, "ament_cmake", ws) == [])

        escribir(os.path.join(ruta, "config", "params.yaml"), "editado", DESPUES)
        comprobar("NO avisa por editar un .yaml ya instalado (esta enlazado)",
                  revisar("pkgcm", ruta, "ament_cmake", ws) == [])

        escribir(os.path.join(ruta, "config", "piso4.yaml"), "", DESPUES)
        m = revisar("pkgcm", ruta, "ament_cmake", ws)
        comprobar("avisa de un archivo nuevo en una carpeta que se instala",
                  any("piso4.yaml" in x for x in m), str(m))

        escribir(os.path.join(ruta, "include", "nuevo.hpp"), "", DESPUES)
        m = revisar("pkgcm", ruta, "ament_cmake", ws)
        comprobar("una cabecera C++ cambiada si exige recompilar",
                  any("nuevo.hpp" in x for x in m), str(m))

        print("\n== 4. Estado de la compilacion ==")
        os.remove(os.path.join(ws, "build", "pkgcm", "colcon_build.rc"))
        comprobar("detecta un paquete nunca compilado",
                  revisar("pkgcm", ruta, "ament_cmake", ws)
                  == ["nunca se ha compilado en este workspace"])
        escribir(os.path.join(ws, "build", "pkgcm", "colcon_build.rc"), "1", DESPUES)
        comprobar("detecta una compilacion fallida",
                  revisar("pkgcm", ruta, "ament_cmake", ws) == ["su ultima compilacion fallo"])

        print("\n== 5. Descubrimiento de paquetes ==")
        escribir(os.path.join(raiz, "ignorado", "package.xml"), xml_paquete("ignorado", "ament_cmake"))
        escribir(os.path.join(raiz, "ignorado", "COLCON_IGNORE"))
        comprobar("respeta COLCON_IGNORE, igual que colcon",
                  "ignorado" not in [os.path.basename(r) for _, r, _ in paquetes(raiz)])

    print()
    if FALLOS:
        print(f"{len(FALLOS)} comprobaciones fallan.")
        sys.exit(1)
    print("Todas las comprobaciones pasan.")


if __name__ == "__main__":
    main()
