#!/usr/bin/env python3
"""Figuras de la sesion del 30-sep en el piso 2 (evidencia S25_pasillo_piso2_amss-jgm9).

Dibuja, desde Documentos/Evidencia/registros/S25_p2_amcl_corridas.csv:

  - S25_p2_recorridos_hall.png: los recorridos de AMCL de p2r_03, p2r_04 y p2r_05
    sobre el mapa corregido, con la pose final de AMCL y la medida con flexometro;
  - S25_p2_incertidumbre_amcl.png: la incertidumbre de AMCL de las tres corridas;
  - S25_p2r_04_dos_lecturas.png: las dos posiciones finales de p2r_04 que daban las
    medidas a la pared sur y a la norte sobre el mapa SIN corregir (commit
    MAPA_ANTES), que es la discrepancia que llevo a medir el ancho del hall.

Las posiciones medidas salen de las distancias del centro del vehiculo a las
paredes, tomadas con flexometro, y de las caras de las paredes en model.sdf.

Uso, desde la raiz del repositorio:

    python3 herramientas/figuras_s25_piso2.py [directorio_de_salida]
"""
import csv, io, math, pathlib, subprocess, sys
import numpy as np, yaml
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle
from PIL import Image

RAIZ = str(pathlib.Path(__file__).resolve().parents[1]) + '/'
MAPS = RAIZ + 'Robot/aws-deepracer/deepracer_bringup/maps/'
SALIDA_DIR = (sys.argv[1].rstrip('/') if len(sys.argv) > 1 else RAIZ + 'Documentos/Evidencia') + '/'
COLOR = {'p2r_03': '#2a78d6', 'p2r_04': '#eb6834', 'p2r_05': '#1baf7a'}
TINTA, TINTA2, GRIS = '#0b0b0b', '#52514e', '#8a8984'
# Caras de las paredes (model.sdf corregido): barrera de la escalera, pared sur, pared norte.
X_OESTE, Y_SUR, Y_NORTE, Y_NORTE_ANTES = -22.995, -11.145, -7.747, -6.907
REAL = {'p2r_04': (X_OESTE + 0.55, ((Y_SUR + 0.61) + (Y_NORTE - 2.77)) / 2),
        'p2r_05': (X_OESTE + 0.25, ((Y_SUR + 1.52) + (Y_NORTE - 1.86)) / 2)}
# Ultimo commit con el hall de 4,24 m (antes de la correccion del 30-sep).
MAPA_ANTES = '47b526d'
INICIO = {'p2r_03': 17.5, 'p2r_04': 17.2, 'p2r_05': 14.8}   # pose inicial publicada
FIN = {'p2r_03': 99, 'p2r_04': 46.6, 'p2r_05': 99}           # p2r_04: antes del salto

filas = list(csv.DictReader(open(RAIZ + 'Documentos/Evidencia/registros/S25_p2_amcl_corridas.csv')))
def serie(c, hasta=None):
    return [(float(f['t_s']), float(f['x_m']), float(f['y_m']), float(f['sigma_xy_m']))
            for f in filas if f['corrida'] == c and float(f['t_s']) >= INICIO[c]
            and float(f['t_s']) <= (hasta if hasta is not None else FIN[c])]

plt.rcParams.update({'font.size': 10, 'axes.edgecolor': GRIS, 'axes.labelcolor': TINTA2,
                     'xtick.color': TINTA2, 'ytick.color': TINTA2, 'text.color': TINTA})

# ---------- Figura 1: recorridos sobre el mapa corregido ----------
m = yaml.safe_load(open(MAPS + 'mundo_definitivo_piso2.yaml'))
img = np.array(Image.open(MAPS + 'mundo_definitivo_piso2.pgm')); res = m['resolution']
ox, oy = m['origin'][:2]; H, W = img.shape
fig, ax = plt.subplots(figsize=(10, 10.6))
ax.imshow(img, cmap='gray', extent=[ox, ox + W*res, oy, oy + H*res], origin='upper',
          vmin=0, vmax=255, alpha=0.5)
ax.set_xlim(-24.0, -13.3); ax.set_ylim(-11.9, -0.4); ax.set_aspect('equal')
ax.grid(color='#e4e3df', lw=0.6)
ax.plot([-23.37, -17.37], [Y_NORTE_ANTES, Y_NORTE_ANTES], ls=(0, (4, 3)), color=GRIS, lw=1.5)
ax.text(-23.3, Y_NORTE_ANTES + 0.18, 'cara de la pared norte antes de la correccion (hall de 4,24 m)',
        fontsize=8.5, color=TINTA2)
ax.text(-23.3, Y_NORTE + 0.22, 'pared norte corregida (hall de 3,40 m)', fontsize=8.5, color=TINTA2)

for c in ('p2r_03', 'p2r_04', 'p2r_05'):
    s = serie(c)
    ax.plot([p[1] for p in s], [p[2] for p in s], color=COLOR[c], lw=2, solid_capstyle='round')
    ax.plot(s[-1][1], s[-1][2], 'o', ms=9, mfc='white', mec=COLOR[c], mew=2, zorder=6)
for c, (x, y) in REAL.items():
    s = serie(c); ax_, ay = s[-1][1], s[-1][2]
    ax.plot([ax_, x], [ay, y], ls=':', color=COLOR[c], lw=1.5)
    ax.plot(x, y, 's', ms=9, color=COLOR[c], mec='white', mew=1.5, zorder=7)
    print(c, 'real (%.3f, %.3f)  AMCL final (%.3f, %.3f)  error AMCL %.2f m' % (x, y, ax_, ay, math.dist((x, y), (ax_, ay))))

# salto de AMCL de p2r_04 despues de la llegada
ax.plot(-16.854, -5.567, 'x', ms=10, mew=2.5, color=COLOR['p2r_04'])
ax.annotate('p2r_04: pose de AMCL tras el refresco\nposterior a la llegada', (-16.854, -5.567),
            (-20.9, -4.6), fontsize=8.5, color=TINTA2, arrowprops=dict(arrowstyle='->', color=GRIS))

# destinos
for (x, y, txt, dx, dy) in [(-14.96, -10.37, 'Salida IEEE', -1.3, -0.6),
                            (-14.87, -1.73, 'Lab. Sistemas 313', -2.4, 0.3),
                            (-21.50, -9.45, 'Escaleras', 0.22, -0.13)]:
    ax.plot(x, y, '*', ms=15, color=TINTA, mec='white', zorder=8)
    ax.text(x + dx, y + dy, txt, fontsize=9, color=TINTA, fontweight='bold')
ax.plot(-21.50, -9.03, '*', ms=12, mfc='white', mec=TINTA, zorder=8)

# rotulos directos
for c, x, y in (('p2r_03', -15.2, -6.6), ('p2r_04', -18.55, -8.75), ('p2r_05', -17.7, -10.85)):
    ax.plot([x - 0.45, x - 0.1], [y, y], color=COLOR[c], lw=3)
    ax.text(x, y, c, color=TINTA, fontsize=9.5, fontweight='bold', va='center')

leyenda = [Line2D([], [], color=COLOR[c], lw=2, label=c) for c in COLOR] + [
    Line2D([], [], ls='', marker='o', ms=8, mfc='white', mec=TINTA2, mew=2, label='pose final segun AMCL'),
    Line2D([], [], ls='', marker='s', ms=8, color=TINTA2, label='posicion final medida con flexometro'),
    Line2D([], [], ls='', marker='*', ms=12, color=TINTA, label='destino del catalogo (escaleras: meta corregida)'),
    Line2D([], [], ls='', marker='*', ms=11, mfc='white', mec=TINTA, label='meta de p2r_04, con el mapa sin corregir')]
ax.legend(handles=leyenda, loc='upper left', fontsize=8.5, framealpha=0.95)
ax.set_xlabel('x del mapa (m)'); ax.set_ylabel('y del mapa (m)')
ax.set_title('Piso 2, extremo oeste: recorridos de amss-jgm9 el 30 de septiembre', fontsize=11.5)
fig.tight_layout(); fig.savefig(SALIDA_DIR + 'S25_p2_recorridos_hall.png', dpi=130)

# ---------- Figura 2: incertidumbre de AMCL ----------
fig, ax = plt.subplots(figsize=(9, 4.6))
for c in ('p2r_03', 'p2r_04', 'p2r_05'):
    s = serie(c, hasta=999)
    t = [p[0] - INICIO[c] for p in s]; sg = [p[3] for p in s]
    ax.plot(t, sg, color=COLOR[c], lw=2, marker='o', ms=4)
    ax.text(t[-1] + 0.6, sg[-1], c, color=TINTA, fontsize=9.5, fontweight='bold', va='center')
ax.axhline(0.20, color=GRIS, lw=1, ls=(0, (4, 3)))
ax.text(36.5, 0.27, 'umbral para iniciar una corrida (0,20 m)', fontsize=8.5, color=TINTA2)
ax.annotate('p2r_04: salto de AMCL tras la llegada', (29.8, 3.24), (14, 3.05), fontsize=8.5,
            color=TINTA2, arrowprops=dict(arrowstyle='->', color=GRIS))
ax.set_xlim(0, 60); ax.set_ylim(0, 3.6)
ax.set_xlabel('tiempo desde la pose inicial (s)'); ax.set_ylabel('incertidumbre de AMCL (m)')
ax.spines[['top', 'right']].set_visible(False); ax.grid(axis='y', color='#e4e3df', lw=0.6)
ax.set_title('Incertidumbre de posicion de AMCL en las tres corridas medidas', fontsize=11.5)
fig.tight_layout(); fig.savefig(SALIDA_DIR + 'S25_p2_incertidumbre_amcl.png', dpi=130)

# ---------- Figura 3: las dos lecturas de p2r_04 sobre el mapa sin corregir ----------
RUTA_PGM = 'Robot/aws-deepracer/deepracer_bringup/maps/mundo_definitivo_piso2.pgm'
viejo = np.array(Image.open(io.BytesIO(subprocess.check_output(
    ['git', 'show', f'{MAPA_ANTES}:{RUTA_PGM}'], cwd=RAIZ))))
META_ANTES = (-21.50, -9.03)
A = (X_OESTE + 0.55, Y_SUR + 0.61)            # con la medida a la pared sur
B = (X_OESTE + 0.55, Y_NORTE_ANTES - 2.77)    # con la medida a la pared norte
fig, ax = plt.subplots(figsize=(12, 8.6))
ax.imshow(viejo, cmap='gray', extent=[ox, ox + viejo.shape[1]*res, oy, oy + viejo.shape[0]*res],
          origin='upper', vmin=0, vmax=255, alpha=0.5)
ax.set_xlim(-24.0, -13.3); ax.set_ylim(-11.9, -4.6); ax.set_aspect('equal')
ax.grid(color='#e4e3df', lw=0.6)
caja = dict(boxstyle='round', fc='white', ec=GRIS)
ax.text(-20.2, Y_NORTE_ANTES + 0.35, f'pared norte del modelo (y = {Y_NORTE_ANTES:.2f})'.replace('.', ','),
        ha='center', fontsize=10, fontweight='bold', bbox=caja)
ax.text(-19.0, Y_SUR - 0.45, f'pared sur, la del IEEE (y = {Y_SUR:.2f})'.replace('.', ','),
        ha='center', fontsize=10, fontweight='bold', bbox=caja)
ax.text(X_OESTE - 0.5, -9.0, 'escalera\n(pared oeste)', rotation=90, ha='center', va='center',
        fontsize=10, fontweight='bold', bbox=caja)
ax.annotate('', xy=(-13.75, -5.3), xytext=(-13.75, -6.3), arrowprops=dict(arrowstyle='-|>', lw=2.5, color=TINTA))
ax.text(-13.75, -5.05, 'N', fontsize=15, fontweight='bold', ha='center')

s4 = serie('p2r_04')
ax.plot([p[1] for p in s4], [p[2] for p in s4], color=COLOR['p2r_04'], lw=2,
        label='recorrido segun AMCL')
ax.plot(-21.225, -9.097, 'o', ms=9, mfc='white', mec=COLOR['p2r_04'], mew=2, zorder=6)
ax.annotate('AMCL cuando Nav2 dio la meta\npor alcanzada (incertidumbre 2,4 m)', (-21.225, -9.097),
            (-20.3, -7.95), fontsize=9, color=TINTA2, arrowprops=dict(arrowstyle='->', color=GRIS))
ax.plot(-16.854, -5.567, 'x', ms=11, mew=2.5, color=COLOR['p2r_04'])
ax.annotate('salto de AMCL tras la llegada\n(no es el vehiculo)', (-16.854, -5.567), (-16.6, -5.0),
            fontsize=9, color=TINTA2, arrowprops=dict(arrowstyle='->', color=GRIS))
ax.plot(-14.96, -10.37, 'o', ms=10, color=TINTA, mec='white', zorder=6)
ax.text(-16.3, -10.05, 'salida IEEE\n(mirando al oeste)', fontsize=9, color=TINTA)
ax.plot(*META_ANTES, '*', ms=20, color=TINTA, mec='white', zorder=7,
        label='meta de p2r_04: 1,50 m de la escalera, centrada en el hall del modelo')
ax.add_patch(plt.Circle(META_ANTES, 0.5, fill=False, ls=(0, (4, 3)), color=TINTA2, lw=1.3,
                        label='0,5 m alrededor de la meta (tolerancia de G-3)'))

def vehiculo(c, color, rotulo):
    ax.add_patch(Rectangle((c[0] - 0.1, c[1] - 0.2), 0.2, 0.4, fc=color, ec=TINTA, lw=1.2, zorder=8))
    ax.annotate('', xy=(c[0], c[1] - 0.45), xytext=c, arrowprops=dict(arrowstyle='-|>', lw=2, color=TINTA), zorder=9)
    ax.text(c[0] + 0.55, c[1] - 0.05, rotulo, fontsize=9.5, fontweight='bold', color=TINTA, zorder=9)
vehiculo(A, '#4a3aa7', 'A: con los 0,61 m a la pared sur\n    error %s m' % ('%.2f' % math.dist(A, META_ANTES)).replace('.', ','))
vehiculo(B, '#e87ba4', 'B: con los 2,77 m a la pared norte\n    error %s m' % ('%.2f' % math.dist(B, META_ANTES)).replace('.', ','))

def cota(p, q, txt, dx, dy):
    ax.annotate('', xy=q, xytext=p, arrowprops=dict(arrowstyle='<->', color=TINTA2, lw=1.3))
    ax.text((p[0] + q[0]) / 2 + dx, (p[1] + q[1]) / 2 + dy, txt, fontsize=9, color=TINTA, fontweight='bold')
cota((X_OESTE, -10.05), (A[0], -10.05), '0,55', -0.2, 0.1)
cota((A[0] + 0.3, Y_SUR), (A[0] + 0.3, A[1]), '0,61', 0.05, -0.05)
cota((B[0] + 0.3, Y_NORTE_ANTES), (B[0] + 0.3, B[1]), '2,77', 0.05, 0.3)
ancho = Y_NORTE_ANTES - Y_SUR
def coma(v):
    return ('%.2f' % v).replace('.', ',')
ax.text(-17.2, -9.6, f'Ancho del hall en el modelo: {coma(ancho)} m\n'
                     f'Sur + norte medidos: 0,61 + 2,77 = 3,38 m\n'
                     f'Faltan {coma(ancho - 3.38)} m: por eso A y B no coinciden.', fontsize=9.5, bbox=caja)
ax.set_title('p2r_04 (IEEE -> Escaleras): las dos lecturas de la posicion final sobre el mapa sin corregir',
             fontsize=11.5)
ax.set_xlabel('x del mapa (m)'); ax.set_ylabel('y del mapa (m)')
ax.legend(loc='upper left', fontsize=9)
fig.tight_layout(); fig.savefig(SALIDA_DIR + 'S25_p2r_04_dos_lecturas.png', dpi=120)
print('A', A, round(math.dist(A, META_ANTES), 2), 'B', B, round(math.dist(B, META_ANTES), 2))
