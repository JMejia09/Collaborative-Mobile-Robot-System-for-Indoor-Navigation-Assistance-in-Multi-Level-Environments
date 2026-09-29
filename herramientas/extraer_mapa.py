#!/usr/bin/env python3
"""Escribe mapa.pgm y mapa.yaml a partir del ultimo /map de un bag.

    extraer_mapa.py <bag> <salida_sin_extension> [topico]

POR QUE EXISTE
--------------
'map_saver_cli' se suscribe a /map y se rinde a los 2 s -su plazo por
defecto-. slam_toolbox solo publica /map cuando hay actualizaciones, y al
detenerse el vehiculo dejan de llegar: el guardado falla con 'Failed to spin
map subscription' aunque el mapa este perfectamente construido. Paso el
2026-09-24 con una corrida de 6 m ya hecha.

Como el bag graba /map, el mapa se puede recuperar despues sin volver a
conducir. Esto ademas lo hace repetible: si hace falta cambiar un umbral, se
cambia aqui y no se repite la salida.

CONVENIO DE NAV2 PARA EL .pgm
-----------------------------
  ocupado (> occupied_thresh)  -> 0     negro
  libre   (< free_thresh)      -> 254   blanco
  desconocido o intermedio     -> 205   gris
La primera fila del PGM es la de ARRIBA, y en el OccupancyGrid la primera es
la de ABAJO: hay que invertirlas o el mapa sale reflejado.

free_thresh SE ESCRIBE 0,1 Y NO 0,25. Con 0,25 el valor 205 -que son 0,196 de
ocupacion- queda por debajo del umbral y map_server lee como LIBRE cada celda
que el mapa declara desconocida: Nav2 planificaria por donde nadie ha mirado.
Detectado el 2026-09-08.

BAG SIN CERRAR
--------------
Si el grabador no cierra -el 2026-09-29, con la red cargada, ignoro la senal de
cierre en amss-jgm9-, el .mcap queda sin su indice final ni metadata.yaml y
rosbag2 no lo abre. Entonces se recorre el fichero registro a registro, que es
como el formato permite leerlo sin indice, y se usan todos los mensajes que
alcanzaron a escribirse. Solo trozos sin comprimir, que es lo que graba
'ros2 bag record -s mcap' por defecto.
"""
import os
import struct
import sys

from rclpy.serialization import deserialize_message
from rosbag2_py import ConverterOptions, SequentialReader, StorageOptions
from nav_msgs.msg import OccupancyGrid

OCUPADO = 0.65
LIBRE = 0.1


def almacenamiento(ruta):
    meta = os.path.join(ruta, 'metadata.yaml')
    if os.path.isfile(meta):
        with open(meta) as f:
            for linea in f:
                if 'storage_identifier' in linea:
                    return linea.split(':', 1)[1].strip().strip('"\'')
    return 'mcap'


def leer_mcap_sin_indice(ruta):
    """Recorre un .mcap registro a registro y devuelve [(topico, datos), ...]."""
    if os.path.isdir(ruta):
        ruta = os.path.join(ruta, sorted(x for x in os.listdir(ruta) if x.endswith('.mcap'))[0])
    b = open(ruta, 'rb').read()
    if b[:8] != b'\x89MCAP0\r\n':
        raise RuntimeError('%s no es un fichero MCAP' % ruta)
    canales, mensajes = {}, []

    def cadena(buf, p):
        n = struct.unpack_from('<I', buf, p)[0]
        return buf[p + 4:p + 4 + n].decode(), p + 4 + n

    def registro(op, c):
        if op == 0x04:                                  # Channel
            cid = struct.unpack_from('<H', c, 0)[0]
            canales[cid], _ = cadena(c, 4)
        elif op == 0x05:                                # Message
            cid = struct.unpack_from('<H', c, 0)[0]
            mensajes.append((canales.get(cid), c[22:]))
        elif op == 0x06:                                # Chunk
            compresion, p = cadena(c, 28)
            if compresion:
                raise RuntimeError('trozo comprimido con %s: no soportado' % compresion)
            n = struct.unpack_from('<Q', c, p)[0]
            recorrer(c[p + 8:p + 8 + n])

    def recorrer(buf):
        p = 0
        while p + 9 <= len(buf):
            op, n = struct.unpack_from('<BQ', buf, p)
            if p + 9 + n > len(buf):
                break                                   # registro cortado al final
            registro(op, buf[p + 9:p + 9 + n])
            p += 9 + n

    recorrer(b[8:])
    return mensajes


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    bag, salida = sys.argv[1], sys.argv[2]
    topico = sys.argv[3] if len(sys.argv) > 3 else '/map'

    try:
        lector = SequentialReader()
        lector.open(StorageOptions(uri=bag, storage_id=almacenamiento(bag)),
                    ConverterOptions('', ''))
        registros = []
        while lector.has_next():
            top, datos, _ = lector.read_next()
            registros.append((top, datos))
    except RuntimeError:
        print('AVISO: rosbag2 no abre el bag (sin cerrar); se lee registro a registro')
        registros = leer_mcap_sin_indice(bag)

    ultimo = None
    total = 0
    for top, datos in registros:
        if top != topico:
            continue
        total += 1
        ultimo = deserialize_message(datos, OccupancyGrid)

    if ultimo is None:
        print("ERROR: el bag no trae ningun mensaje en '%s'" % topico)
        return 1

    an, al = ultimo.info.width, ultimo.info.height
    res = ultimo.info.resolution
    ox = ultimo.info.origin.position.x
    oy = ultimo.info.origin.position.y
    print('mensajes en %s: %d   ultimo: %d x %d celdas, %.3f m/celda'
          % (topico, total, an, al, res))

    filas = []
    for fila in range(al - 1, -1, -1):
        linea = bytearray()
        for col in range(an):
            v = ultimo.data[fila * an + col]
            if v < 0:
                linea.append(205)
            elif v >= OCUPADO * 100:
                linea.append(0)
            elif v <= LIBRE * 100:
                linea.append(254)
            else:
                linea.append(205)
        filas.append(bytes(linea))

    with open(salida + '.pgm', 'wb') as f:
        f.write(b'P5\n# mapa extraido de un bag por extraer_mapa.py\n')
        f.write(('%d %d\n255\n' % (an, al)).encode())
        for linea in filas:
            f.write(linea)

    with open(salida + '.yaml', 'w') as f:
        f.write('image: %s.pgm\n' % os.path.basename(salida))
        f.write('mode: trinary\n')
        f.write('resolution: %.6f\n' % res)
        f.write('origin: [%.6f, %.6f, 0.0]\n' % (ox, oy))
        f.write('negate: 0\n')
        f.write('occupied_thresh: %.2f\n' % OCUPADO)
        f.write('free_thresh: %.2f\n' % LIBRE)

    ocupadas = sum(1 for v in ultimo.data if v >= OCUPADO * 100)
    libres = sum(1 for v in ultimo.data if 0 <= v <= LIBRE * 100)
    print('escrito %s.pgm  (%d ocupadas, %d libres, %d desconocidas)'
          % (salida, ocupadas, libres, an * al - ocupadas - libres))
    return 0


if __name__ == '__main__':
    sys.exit(main())
