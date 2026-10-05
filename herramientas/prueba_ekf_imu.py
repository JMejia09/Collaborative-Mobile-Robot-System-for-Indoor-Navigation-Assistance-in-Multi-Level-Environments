#!/usr/bin/env python3
"""El EKF de imu:=true toma el avance de rf2o y el rumbo de la IMU, con datos sinteticos.

POR QUE EXISTE
--------------
Con `imu:=true`, `nav2_hardware.launch.py` pone un EKF de `robot_localization`
entre rf2o y Nav2 (Documentos/PLAN_S26.md §2.3). Lo que el filtro toma de cada
fuente lo deciden unas listas de quince booleanos en `parametros_ekf`, y un
error en ellas no da ningun aviso: el filtro arranca, publica `odom` y el rumbo
sale de donde no debe. El caso que importa es el rumbo de rf2o, que llega con
covarianza cero: si se fusionara, el filtro lo tomaria como exacto y la IMU no
pesaria nada. Esta prueba corre el filtro de verdad, sin vehiculo ni Gazebo.

QUE COMPRUEBA
-------------
Arranca `robot_state_publisher` con la URDF de hardware y el `ekf_node` con los
parametros de `parametros_ekf`, los dos bajo `/robot2`, y publica un rf2o y una
IMU sinteticos en cuatro fases:

  A. 3 s quieto.
  B. 4 s en recta a 0,5 m/s: rf2o avanza 2,0 m y la IMU no gira.
  C. 3 s girando a la izquierda a 30 grados/s y avanzando a 0,3 m/s. La IMU
     marca el giro (negativo en el z del sensor) y rf2o lo ignora: dice que
     sigue en recta. Un arco de 90 grados con radio 0,573 m acaba en
     (2,573, 0,573).
  D. 1 s quieto, para que el filtro termine de procesar el giro, y 3 s mas.

Y exige:
  1. En A, que el filtro no se mueva: menos de 1 cm y 1 grado.
  2. Al final de B, x = 2,00 m (+-5 cm), y = 0 y rumbo 0.
  3. Al final de C, rumbo de +90 grados (+-3): el rumbo sale de la IMU aunque
     rf2o diga 0. La posicion, cerca de (2,573, 0,573), porque el avance de
     rf2o se integra con el rumbo del filtro.
  4. En los ultimos 3 s de D, deriva menor de 1 cm y 0,5 grados.
  5. La TF `robot2/odom -> robot2/base_link` la publica el filtro y coincide
     con `/robot2/odom`.

Uso, desde la raiz del repositorio, con ROS sourceado (robot_localization
instalado):

    ROS_DOMAIN_ID=93 ROS_LOCALHOST_ONLY=1 python3 herramientas/prueba_ekf_imu.py
"""
import importlib.util
import math
import os
import pathlib
import signal
import subprocess
import sys
import tempfile
import time

import yaml

RAIZ = pathlib.Path(__file__).resolve().parents[1]
LAUNCH = RAIZ / 'Robot/aws-deepracer/deepracer_bringup/launch/nav2_hardware.launch.py'
URDF = RAIZ / 'Robot/aws-deepracer/deepracer_description/models/urdf/deepracer_hardware.urdf'
NS = 'robot2'
PASO = 0.02                  # 50 Hz, la frecuencia de la IMU
CADA_RF2O = 5                # rf2o a 10 Hz
FASES = (('A', 3.0, 0.0, 0.0), ('B', 4.0, 0.5, 0.0),
         ('C', 3.0, 0.3, math.radians(30.0)), ('D0', 1.0, 0.0, 0.0), ('D', 3.0, 0.0, 0.0))


def cargar_lanzador():
    spec = importlib.util.spec_from_file_location('lanzador', LAUNCH)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def yaw_de(q):
    return math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z))


def arrancar(directorio, nombre, paquete, ejecutable, parametros, extra=()):
    """Arranca el ejecutable directamente y en su propio grupo de procesos.

    Con `ros2 run`, terminar el proceso deja vivo al nodo hijo: un filtro de una
    corrida anterior seguia publicando en /robot2/odom y mezclaba sus valores con
    los de la corrida nueva (2026-10-05).
    """
    from ament_index_python.packages import get_package_prefix
    fichero = pathlib.Path(directorio) / f'{nombre}.yaml'
    fichero.write_text(yaml.safe_dump({f'/{NS}/{nombre}': {'ros__parameters': parametros}}))
    binario = pathlib.Path(get_package_prefix(paquete)) / 'lib' / paquete / ejecutable
    return subprocess.Popen(
        [str(binario), '--ros-args', '-r', f'__ns:=/{NS}',
         '-r', f'__node:={nombre}', '--params-file', str(fichero), *extra],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)





def main():
    os.environ.setdefault('ROS_DOMAIN_ID', '93')
    os.environ.setdefault('ROS_LOCALHOST_ONLY', '1')
    import rclpy
    from nav_msgs.msg import Odometry
    from rclpy.executors import SingleThreadedExecutor
    from rclpy.time import Time
    from sensor_msgs.msg import Imu
    from tf2_ros import Buffer, TransformListener

    ok, fallos = 0, []

    def exigir(condicion, mensaje):
        nonlocal ok
        if condicion:
            ok += 1
            print('  [OK ]', mensaje)
        else:
            fallos.append(mensaje)
            print('  [MAL]', mensaje)

    pre = f'{NS}/'
    parametros = cargar_lanzador().parametros_ekf(pre, NS)
    with tempfile.TemporaryDirectory() as directorio:
        procesos = [
            arrancar(directorio, 'robot_state_publisher', 'robot_state_publisher',
                     'robot_state_publisher',
                     {'robot_description': URDF.read_text(), 'frame_prefix': pre}),
            arrancar(directorio, 'ekf_filter_node', 'robot_localization', 'ekf_node', parametros,
                     ('-r', 'odometry/filtered:=odom')),
        ]
        rclpy.init()
        try:
            nodo = rclpy.create_node('prueba_ekf_imu')
            pub_rf2o = nodo.create_publisher(Odometry, f'/{NS}/odom_rf2o', 10)
            pub_imu = nodo.create_publisher(Imu, f'/{NS}/imu/data', 10)
            filtrado = []
            nodo.create_subscription(Odometry, f'/{NS}/odom', filtrado.append, 50)
            tf = Buffer()
            TransformListener(tf, nodo)
            ejecutor = SingleThreadedExecutor()
            ejecutor.add_node(nodo)

            # Espera a que el filtro este suscrito antes de empezar.
            limite = time.monotonic() + 20
            while (pub_rf2o.get_subscription_count() == 0 or pub_imu.get_subscription_count() == 0) \
                    and time.monotonic() < limite:
                ejecutor.spin_once(timeout_sec=0.1)
            exigir(pub_rf2o.get_subscription_count() > 0 and pub_imu.get_subscription_count() > 0,
                   'el EKF se suscribe a /%s/odom_rf2o y /%s/imu/data' % (NS, NS))
            publicadores = nodo.count_publishers(f'/{NS}/odom')
            exigir(publicadores == 1,
                   'en /%s/odom publica un solo filtro (%d publicadores)' % (NS, publicadores))

            # El avance de rf2o se integra con el reloj real y no por ciclo: el
            # ciclo no dura exactamente PASO, y rf2o avanzaria mas rapido que v.
            x_rf2o = 0.0
            final = {}
            tic = 0
            proximo = anterior = time.monotonic()
            for fase, duracion, v, w in FASES:
                fin = time.monotonic() + duracion
                while time.monotonic() < fin:
                    ahora = time.monotonic()
                    x_rf2o += v * (ahora - anterior)    # rf2o: siempre en recta, rumbo 0
                    anterior = ahora
                    sello = nodo.get_clock().now().to_msg()
                    m = Imu()
                    m.header.stamp = sello
                    m.header.frame_id = f'{pre}imu_link'
                    m.orientation_covariance[0] = -1.0
                    m.angular_velocity.z = -w            # z del sensor hacia abajo
                    m.angular_velocity_covariance = [1e-6, 0.0, 0.0, 0.0, 1e-6, 0.0, 0.0, 0.0, 1e-6]
                    m.linear_acceleration.z = -9.80665
                    m.linear_acceleration_covariance = [1e-3, 0.0, 0.0, 0.0, 1e-3, 0.0, 0.0, 0.0, 1e-3]
                    pub_imu.publish(m)
                    if tic % CADA_RF2O == 0:
                        o = Odometry()
                        o.header.stamp = sello
                        o.header.frame_id = f'{pre}odom'
                        o.child_frame_id = f'{pre}base_link'
                        o.pose.pose.position.x = x_rf2o
                        o.pose.pose.orientation.w = 1.0
                        pub_rf2o.publish(o)
                    tic += 1
                    proximo += PASO
                    while time.monotonic() < proximo:
                        ejecutor.spin_once(timeout_sec=max(0.0, proximo - time.monotonic()))
                # Se lee al cerrar la fase, sin dejar de publicar: si los sensores
                # callan, el filtro sigue extrapolando con la ultima velocidad.
                if not filtrado:
                    break
                p = filtrado[-1].pose.pose
                final[fase] = (p.position.x, p.position.y, math.degrees(yaw_de(p.orientation)))
                print('  fase %s: x=%.3f  y=%.3f  rumbo=%.1f grados' % ((fase,) + final[fase]))

            exigir(len(final) == len(FASES), 'el filtro publica /%s/odom en todas las fases' % NS)
            if len(final) == len(FASES):
                x, y, r = final['A']
                exigir(abs(x) < 0.01 and abs(y) < 0.01 and abs(r) < 1.0,
                       'A, quieto: el filtro no se mueve')
                x, y, r = final['B']
                exigir(abs(x - 2.0) < 0.05 and abs(y) < 0.02 and abs(r) < 1.0,
                       'B, recta de 2,0 m: x = %.3f m' % x)
                x, y, r = final['C']
                exigir(abs(r - 90.0) < 3.0,
                       'C, el rumbo sale de la IMU aunque rf2o diga 0: %.1f grados' % r)
                exigir(math.hypot(x - 2.573, y - 0.573) < 0.10,
                       'C, el avance de rf2o se integra con ese rumbo: (%.3f, %.3f), '
                       'se espera (2,573, 0,573)' % (x, y))
                x, y, r = final['D0']
                xd, yd, rd = final['D']
                exigir(math.hypot(xd - x, yd - y) < 0.01 and abs(rd - r) < 0.5,
                       'D, quieto 3 s: deriva de %.3f m y %.2f grados'
                       % (math.hypot(xd - x, yd - y), rd - r))
                try:
                    t = tf.lookup_transform(f'{pre}odom', f'{pre}base_link',
                                            Time()).transform
                    exigir(math.hypot(t.translation.x - xd, t.translation.y - yd) < 0.02 and
                           abs(math.degrees(yaw_de(t.rotation)) - rd) < 1.0,
                           'la TF %sodom -> %sbase_link la publica el filtro y coincide con '
                           '/%s/odom' % (pre, pre, NS))
                except Exception as error:  # noqa: BLE001 - cualquier fallo de tf2 es un fallo
                    exigir(False, 'no hay TF %sodom -> %sbase_link: %s' % (pre, pre, error))
            nodo.destroy_node()
        finally:
            rclpy.shutdown()
            for p in procesos:
                try:
                    os.killpg(p.pid, signal.SIGINT)
                except ProcessLookupError:
                    pass
            for p in procesos:
                try:
                    p.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    os.killpg(p.pid, signal.SIGKILL)
                    p.wait()

    print('=' * 62)
    if fallos:
        print(f'{len(fallos)} comprobaciones FALLAN de {ok + len(fallos)}')
        return 1
    print(f'Todas las comprobaciones pasan ({ok}).')
    return 0


if __name__ == '__main__':
    sys.exit(main())
