#!/usr/bin/env python3
"""Mide en el vehiculo, con un solo proceso, /odom y la IMU durante unos segundos.

Uso (en el vehiculo, como root y con la particion):

    python3 ~deepracer/tesis/medir_odom_imu.py 60 [--ns robot2] [--cada 5]

Espera el primer /odom (hasta 30 s) y desde ahi mide durante los segundos
pedidos, en un solo proceso, la odometria del filtro (/odom) y la de rf2o sola
(/odom_rf2o, que solo existe con imu:=true). Imprime, para cada una:

- su frecuencia, y la de imu/data;
- la pose al principio y al final, cuanto se movio el vehiculo y cuanto giro,
  acumulando el giro (no salta al pasar por +-180 grados);
- el giro que integra la IMU por su cuenta, en el eje z del sensor y sin
  pasar por la URDF: sirve para separar un fallo del sensor de uno del filtro;
- el rumbo cada --cada segundos, para ver cuando ocurrio un giro.

Sirve para las pruebas de la §2.3 de Documentos/PLAN_S26.md: la deriva con el
vehiculo quieto y el giro de 90 grados a mano.

POR QUE UN SOLO PROCESO. 'ros2 topic echo' y 'ros2 topic hz' arrancan cada uno
un interprete de Python con todo el CLI de ROS, y en la tarjeta de dos nucleos
ocupan uno entero un par de segundos. El 2026-10-05, en amss-jgm9, eso disparo
los avisos 'Failed to meet update rate' del filtro, y la primera lectura de
'echo --once' fallo porque el topico aun no estaba descubierto. Por lo mismo,
el filtro y rf2o se miden en el mismo proceso: dos mediciones simultaneas
tardaron mas de 15 s en descubrir los topicos y abortaron.
"""
import argparse
import math
import sys
import time


HUECO_IMU_S = 0.2


def yaw_de(q):
    return math.atan2(2.0 * (q.w * q.z + q.x * q.y), 1.0 - 2.0 * (q.y * q.y + q.z * q.z))


def normalizar(a):
    return math.atan2(math.sin(a), math.cos(a))


def resumen(nombre, od, cada):
    """Lineas de resultado de una odometria: [(t, x, y, rumbo), ...]."""
    if len(od) < 2:
        return [f'{nombre}: sin datos ({len(od)} mensajes)']
    dur = od[-1][0] - od[0][0]
    t0, x0, y0, r0 = od[0]
    _, x1, y1, r1 = od[-1]
    giro, acumulado, siguiente, marcas = 0.0, 0.0, t0, []
    for a_, b in zip(od, od[1:]):
        giro += normalizar(b[3] - a_[3])
        if b[0] >= siguiente:
            marcas.append(f'{b[0] - t0:4.0f}s:{math.degrees(giro):+6.1f}')
            siguiente += cada
    return [f'{nombre}: {(len(od) - 1) / dur:.1f} Hz ({len(od)} mensajes)',
            f'  inicio: x={x0:+.3f}  y={y0:+.3f}  rumbo={math.degrees(r0):+.2f} grados',
            f'  final:  x={x1:+.3f}  y={y1:+.3f}  rumbo={math.degrees(r1):+.2f} grados',
            f'  desplazamiento: {math.hypot(x1 - x0, y1 - y0):.3f} m   '
            f'giro: {math.degrees(giro):+.2f} grados',
            '  giro acumulado: ' + '  '.join(marcas)]


def main():
    p = argparse.ArgumentParser(description='Mide /odom, /odom_rf2o e imu/data durante unos segundos.')
    p.add_argument('segundos', type=float)
    p.add_argument('--ns', default='', help="espacio de nombres, p. ej. 'robot2'")
    p.add_argument('--cada', type=float, default=5.0, help='giro acumulado cada tantos segundos')
    a = p.parse_args()
    pre = f'/{a.ns.strip("/")}' if a.ns.strip('/') else ''

    import rclpy
    from nav_msgs.msg import Odometry
    from sensor_msgs.msg import Imu

    rclpy.init()
    nodo = rclpy.create_node('medir_odom_imu')
    datos = {'odom': [], 'odom_rf2o': []}
    estado = {'n_imu': 0, 'giro_imu': 0.0, 't_imu': None, 'huecos': 0, 't_huecos': 0.0}

    def guardar(lista):
        def on_odom(m):
            lista.append((time.monotonic(), m.pose.pose.position.x,
                          m.pose.pose.position.y, yaw_de(m.pose.pose.orientation)))
        return on_odom

    def on_imu(m):
        # Con el sello del mensaje y no con la hora de llegada: con la tarjeta
        # cargada los mensajes llegan a rachas, y el 2026-10-05 dos mediciones
        # simultaneas del mismo giro integradas con la llegada diferian en 5 grados.
        sello = m.header.stamp.sec + m.header.stamp.nanosec * 1e-9
        if 'inicio' in estado:
            if estado['t_imu'] is not None:
                dt = sello - estado['t_imu']
                # Mas de 0,2 s entre dos mensajes (cinco periodos a 25 Hz) es un
                # hueco: este proceso no alcanzo a leerlos. Integrar a traves de
                # el falsea el giro; el 2026-10-05 dio -29,8 grados en un giro de
                # 90 que el filtro, con los mismos datos, midio en +88,4.
                if dt > HUECO_IMU_S:
                    estado['huecos'] += 1
                    estado['t_huecos'] += dt
                estado['giro_imu'] += m.angular_velocity.z * dt
            estado['n_imu'] += 1
        estado['t_imu'] = sello

    for topico, lista in datos.items():
        nodo.create_subscription(Odometry, f'{pre}/{topico}', guardar(lista), 50)
    nodo.create_subscription(Imu, f'{pre}/imu/data', on_imu, 50)

    limite = time.monotonic() + 30.0
    while not datos['odom'] and time.monotonic() < limite:
        rclpy.spin_once(nodo, timeout_sec=0.1)
    if not datos['odom']:
        print(f'ABORTA: no llega {pre}/odom en 30 s. ¿Esta el lanzador vivo?')
        return 1
    for lista in datos.values():
        lista.clear()
    estado['inicio'] = time.monotonic()
    print(f'midiendo {a.segundos:.0f} s...', flush=True)
    fin = estado['inicio'] + a.segundos
    while time.monotonic() < fin:
        rclpy.spin_once(nodo, timeout_sec=0.1)
    nodo.destroy_node()
    rclpy.shutdown()

    for topico, lista in datos.items():
        print('\n'.join(resumen(f'{pre}/{topico}', lista, a.cada)))
    print(f'{pre}/imu/data: {estado["n_imu"] / a.segundos:.1f} Hz; giro integrado por la IMU '
          f'(z del sensor, que apunta abajo): {math.degrees(estado["giro_imu"]):+.2f} grados')
    if estado['huecos']:
        print(f'  AVISO: {estado["huecos"]} hueco(s) en la IMU ({estado["t_huecos"]:.1f} s en '
              f'total): esta herramienta no alcanzo a leer todos los mensajes y su giro '
              f'integrado no es fiable. El filtro lee los suyos aparte.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
