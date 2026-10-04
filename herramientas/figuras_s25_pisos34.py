#!/usr/bin/env python3
"""Figura de la sesion del 2-oct en el piso 4 (evidencia S25_pisos34_campo.md).

Dibuja, sobre el mapa del piso 4, los recorridos de AMCL de p4r_03 y p4d_01
(Documentos/Evidencia/registros/S25_p4_amcl_corridas.csv), la pose final que dio
AMCL al terminar cada corrida y la posicion final medida con flexometro.

Las grabaciones se cortan antes del final de la corrida (el grabador se cerro con
SIGKILL y se perdio el ultimo bloque del .mcap), asi que el trazo de AMCL termina
antes que el recorrido; la pose final de AMCL sale de la fila del CSV de la
campana, que escribe la propia herramienta.

Uso, desde la raiz del repositorio:

    python3 herramientas/figuras_s25_pisos34.py [directorio_de_salida]
"""
import csv, math, pathlib, sys
import numpy as np, yaml
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from PIL import Image

RAIZ = pathlib.Path(__file__).resolve().parents[1]
MAPA = RAIZ / 'Robot/aws-deepracer/deepracer_bringup/maps/piso4.yaml'
SALIDA_DIR = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else RAIZ / 'Documentos/Evidencia'
COLOR = {'p4r_03': '#2a78d6', 'p4d_01': '#eb6834'}
TINTA, TINTA2, GRIS = '#0b0b0b', '#52514e', '#8a8984'
# Salida, meta, pose final de AMCL (CSV de la campana) y posicion medida.
CORRIDAS = {
    'p4r_03': dict(salida=(24.39, 1.23), meta=(17.22, 2.06), amcl=(17.963, 2.015),
                   real=(24.39 - 6.68, 1.68), rotulo='p4r_03, amss-jgm9: Salon 403'),
    'p4d_01': dict(salida=(24.45, 1.21), meta=(9.31, 2.15), amcl=(10.256, 2.001),
                   real=(24.45 - 14.57, 2.20), rotulo='p4d_01, amss-ez9n: Salon 402'),
}

filas = list(csv.DictReader(open(RAIZ / 'Documentos/Evidencia/registros/S25_p4_amcl_corridas.csv')))
m = yaml.safe_load(open(MAPA)); im = np.array(Image.open(MAPA.with_suffix('.pgm')))
ox, oy = m['origin'][:2]; res = m['resolution']; H, W = im.shape

plt.rcParams.update({'font.size': 10, 'axes.edgecolor': GRIS, 'axes.labelcolor': TINTA2,
                     'xtick.color': TINTA2, 'ytick.color': TINTA2})
fig, ax = plt.subplots(figsize=(15, 5.4))
ax.imshow(im, cmap='gray', extent=[ox, ox + W*res, oy, oy + H*res], origin='upper', alpha=0.5)
for c, d in CORRIDAS.items():
    # Desde la pose inicial de la corrida: las muestras anteriores son del arranque.
    s = [(float(f['x_m']), float(f['y_m'])) for f in filas
         if f['corrida'] == c and float(f['sigma_xy_m']) < 0.3 or
         (f['corrida'] == c and math.dist((float(f['x_m']), float(f['y_m'])), d['salida']) > 0.5)]
    s = [p for p in s if p[0] <= d['salida'][0] + 0.3]
    ax.plot([p[0] for p in s], [p[1] for p in s], color=COLOR[c], lw=2)
    # Tramo que la grabacion perdio: del ultimo punto grabado a la pose final de AMCL.
    ax.plot([s[-1][0], d['amcl'][0]], [s[-1][1], d['amcl'][1]], color=COLOR[c], lw=1.5, ls=(0, (3, 3)))
    ax.plot(*d['salida'], 'o', ms=10, color=COLOR[c], mec='white', mew=1.5, zorder=6)
    ax.plot(*d['meta'], '*', ms=17, color=TINTA, mec='white', zorder=6)
    ax.plot(*d['amcl'], 'o', ms=9, mfc='white', mec=COLOR[c], mew=2, zorder=7)
    ax.plot(*d['real'], 's', ms=9, color=COLOR[c], mec='white', mew=1.5, zorder=8)
    ax.plot([d['real'][0], d['meta'][0]], [d['real'][1], d['meta'][1]], ls=':', color=COLOR[c], lw=1.5)
    err = math.dist(d['real'], d['meta'])
    ax.text(d['meta'][0], 3.75, '%s\nllegada a %s m' % (d['rotulo'], ('%.2f' % err).replace('.', ',')),
            ha='center', fontsize=9, color=TINTA)
ax.text(0.3, 1.0, 'FONDO\nNORTE', fontsize=9, fontweight='bold'); ax.text(26.0, 1.0, 'pared\nSUR', fontsize=9, fontweight='bold')
ax.text(21.0, -0.75, 'pared OESTE: ascensor y escaleras', fontsize=8.5, color=TINTA2, ha='center')
ax.text(13.2, 1.0, 'discontinua: tramo final que la grabacion\nperdio (el .mcap se cerro con SIGKILL)', fontsize=8.5, color=TINTA2, ha='center')
leyenda = [Line2D([], [], color=COLOR[c], lw=2, label=c) for c in COLOR] + [
    Line2D([], [], ls='', marker='o', ms=8, color=TINTA2, mec='white', label='salida'),
    Line2D([], [], ls='', marker='*', ms=12, color=TINTA, label='meta'),
    Line2D([], [], ls='', marker='o', ms=8, mfc='white', mec=TINTA2, mew=2, label='pose final segun AMCL'),
    Line2D([], [], ls='', marker='s', ms=8, color=TINTA2, label='posicion final medida con flexometro')]
ax.legend(handles=leyenda, loc='lower left', fontsize=8.5, ncol=3, framealpha=0.95)
ax.set_xlim(-1.2, 27.4); ax.set_ylim(-1.5, 4.5); ax.set_aspect('equal')
ax.set_xlabel('x del mapa (m), a lo largo del pasillo'); ax.set_ylabel('y (m)')
ax.set_title('Piso 4, 2 de octubre: corridas medidas con flexometro', fontsize=11.5)
fig.tight_layout(); fig.savefig(SALIDA_DIR / 'S25_p4_corridas_piso4.png', dpi=120)
for c, d in CORRIDAS.items():
    print(c, 'llegada %.2f m' % math.dist(d['real'], d['meta']), 'AMCL frente al real %.2f m' % math.dist(d['real'], d['amcl']))
