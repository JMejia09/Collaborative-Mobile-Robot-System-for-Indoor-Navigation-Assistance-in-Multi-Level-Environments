# Cómo compilar el documento final

## El atajo: un solo comando

```bash
bash herramientas/armar_documento.sh --zip --pdf
```

Hace tres cosas de una vez:

- **`DocumentoFinal_COMPLETO.tex`** — todo el documento en UN archivo, con los
  capítulos ya insertados. Sirve para leerlo entero de una sentada, o para
  pegarlo en Overleaf sin subir la carpeta. Cada bloque dice de qué archivo
  viene: **si editas ahí, el cambio se pierde al regenerar**.
- **`DocumentoFinal_overleaf.zip`** — la forma correcta de llevarlo a Overleaf:
  *New Project → Upload Project → ese .zip*. Copiar y pegar `main.tex` a secas
  **no funciona**, porque sus `\input` apuntan a archivos que allí no existen y
  el documento sale vacío sin decir por qué.
- **`main.pdf`** — compilado y verificado, con el número de páginas y los
  errores si los hay.

## En este portátil (ya está instalado)

```bash
cd Documentos/DocumentoFinal
pdflatex main && biber main && pdflatex main && pdflatex main
```

Las cuatro pasadas hacen falta: la primera recoge las citas, `biber` resuelve la
bibliografía, y las dos últimas cuadran índice, referencias cruzadas y números
de página. **Es `biber`, no `bibtex`** — biblatex con backend biber.

El PDF sale en `main.pdf` y no se versiona: se regenera.

## Qué se instaló

```bash
sudo apt install -y texlive-latex-recommended texlive-latex-extra \
                    texlive-lang-spanish texlive-fonts-recommended \
                    texlive-bibtex-extra biber
```

Opcional, para unidades bien compuestas (`\SI{0,412}{\meter}`) y coma decimal:

```bash
sudo apt install texlive-science
```

Sin él el documento compila igual; solo avisa de que `\SI` y `\num` no están.

## En Overleaf, si algún día hace falta

Subir la carpeta `DocumentoFinal/` completa a un proyecto nuevo y compilar
`main.tex` con pdfLaTeX. Overleaf ejecuta `biber` solo.

## Estado de la última compilación verificada

2026-09-28: **25 páginas, tamaño carta, sin errores ni avisos pendientes.**
Margen izquierdo medido sobre el PDF: 3,0 cm, conforme a la NTC 1486.
