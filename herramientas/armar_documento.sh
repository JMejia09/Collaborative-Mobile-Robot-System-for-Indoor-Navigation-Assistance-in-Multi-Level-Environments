#!/usr/bin/env bash
# Arma el documento final en UN SOLO archivo, y opcionalmente un .zip para Overleaf.
#
# POR QUE EXISTE
# --------------
# El documento vive partido en Documentos/DocumentoFinal/capitulos/*.tex para que
# dos personas escriban a la vez sin pisarse y para que cada cambio se vea en el
# diff de git. Eso esta bien para trabajar, pero rompe dos cosas:
#
#   - Copiar y pegar main.tex en Overleaf: los \input apuntan a archivos que
#     alli no existen, y el documento sale vacio sin decir por que.
#   - Leerlo entero de una sentada, que es lo que hace falta para revisarlo.
#
# Este guion resuelve las dos. NO sustituye a los archivos por capitulo: los
# lee y produce una copia plana. La fuente sigue siendo capitulos/.
#
# USO
#     bash herramientas/armar_documento.sh            # genera el .tex de una pieza
#     bash herramientas/armar_documento.sh --zip      # ademas el .zip de Overleaf
#     bash herramientas/armar_documento.sh --pdf      # ademas compila y verifica
#
# SALIDAS (ninguna se versiona: se regeneran)
#     Documentos/DocumentoFinal/DocumentoFinal_COMPLETO.tex
#     Documentos/DocumentoFinal/DocumentoFinal_overleaf.zip

set -uo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$REPO/Documentos/DocumentoFinal"
SALIDA="$DOC/DocumentoFinal_COMPLETO.tex"

cd "$DOC" || { echo "No existe $DOC"; exit 1; }

# ---------------------------------------------------------------- aplanar ---
# Se sustituye cada \input{capitulos/xx} por el contenido del archivo, con una
# marca que dice de donde salio. La marca importa: sin ella, quien edite el
# archivo plano no sabe que fichero de verdad hay que tocar.
python3 - "$SALIDA" <<'PY'
import re, sys, io, os
salida = sys.argv[1]
main = io.open('main.tex', encoding='utf-8').read()

def traer(m):
    ruta = m.group(1)
    if not ruta.endswith('.tex'):
        ruta += '.tex'
    if not os.path.exists(ruta):
        return "%% FALTA EL ARCHIVO: %s\n" % ruta
    cuerpo = io.open(ruta, encoding='utf-8').read().rstrip()
    barra = "%" + "="*70
    return ("\n%s\n%%  DESDE: %s\n"
            "%%  Si editas aqui, el cambio se PIERDE al regenerar.\n"
            "%%  La fuente de verdad es ese archivo.\n%s\n\n%s\n"
            % (barra, ruta, barra, cuerpo))

plano = re.sub(r'\\input\{([^}]+)\}', traer, main)

cabecera = (
 "%% " + "="*70 + "\n"
 "%%  DOCUMENTO FINAL EN UNA SOLA PIEZA — GENERADO, NO EDITAR\n"
 "%%\n"
 "%%  Lo produce herramientas/armar_documento.sh a partir de main.tex y de\n"
 "%%  Documentos/DocumentoFinal/capitulos/*.tex. Sirve para dos cosas:\n"
 "%%    1. leerlo entero de una sentada, para revisar\n"
 "%%    2. pegarlo en Overleaf sin tener que subir la carpeta\n"
 "%%\n"
 "%%  CUALQUIER CAMBIO QUE HAGAS AQUI SE PIERDE al regenerar. Para que un\n"
 "%%  cambio dure, editalo en el capitulo correspondiente: cada bloque de\n"
 "%%  abajo dice de que archivo viene.\n"
 "%%\n"
 "%%  OJO EN OVERLEAF: este archivo necesita ademas dos cosas de la carpeta,\n"
 "%%  que no viajan en un copiar y pegar:\n"
 "%%    - usta-proyecto-grado.sty   (el formato)\n"
 "%%    - imagenes/logo_usta.png    (la portada)\n"
 "%%    - referencias.bib           (la bibliografia)\n"
 "%%  Para eso esta la opcion --zip, que los mete todos.\n"
 "%% " + "="*70 + "\n\n")

io.open(salida, 'w', encoding='utf-8').write(cabecera + plano)
n = len(plano.splitlines())
print("  %s  (%d lineas)" % (os.path.basename(salida), n))
PY

# ------------------------------------------------------------------- zip ---
if [[ "${1:-}" == "--zip" || "${2:-}" == "--zip" ]]; then
  ZIP="$DOC/DocumentoFinal_overleaf.zip"
  rm -f "$ZIP"
  zip -q -r "$ZIP" main.tex usta-proyecto-grado.sty referencias.bib \
      capitulos imagenes -x '*.aux' '*.log' >/dev/null
  echo "  $(basename "$ZIP")  ($(du -h "$ZIP" | cut -f1))"
  echo
  echo "  En Overleaf: New Project -> Upload Project -> ese .zip."
  echo "  Compila main.tex. Overleaf ejecuta biber solo."
fi

# ------------------------------------------------------------------- pdf ---
if [[ "${1:-}" == "--pdf" || "${2:-}" == "--pdf" ]]; then
  echo
  echo "  compilando..."
  pdflatex -interaction=nonstopmode main.tex >/dev/null 2>&1
  biber main >/dev/null 2>&1
  pdflatex -interaction=nonstopmode main.tex >/dev/null 2>&1
  pdflatex -interaction=nonstopmode main.tex >/tmp/armar_doc.log 2>&1
  if [[ -f main.pdf ]]; then
    echo "  main.pdf  ($(pdfinfo main.pdf | awk '/Pages/{print $2}') paginas)"
    err=$(grep -c "^! " /tmp/armar_doc.log)
    [[ "$err" -eq 0 ]] && echo "  sin errores" || { echo "  $err ERRORES:"; grep "^! " /tmp/armar_doc.log | head -5; }
  else
    echo "  NO se produjo PDF. Mira /tmp/armar_doc.log"
  fi
fi
