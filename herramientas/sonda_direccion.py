#!/usr/bin/env python3
"""Mueve SOLO la direccion del vehiculo, con la traccion en cero. Es la prueba A4 de PLAN_S25.md.

Se ejecuta EN EL VEHICULO, como root y con el perfil de particion si esta instalado:

    sudo -n bash -c 'source /opt/ros/jazzy/setup.bash && source /opt/aws/deepracer/lib/setup.bash && export FASTRTPS_DEFAULT_PROFILES_FILE=/etc/deepracer-tesis/particion.xml && python3 ~deepracer/tesis/sonda_direccion.py'

Sin el 'export' sirve para la otra mitad de A4: comprobar que una orden sin perfil no llega.

QUE HACE
--------
Un solo proceso publica todo el rato en /ctrl_pkg/servo_msg, a 20 Hz y en BEST_EFFORT, que es
como escucha servo_node. Espera hasta 10 s a emparejarse con algun suscriptor, dice cuantos
encontro, y entonces: centro 2 s, +0,6 3 s, -0,6 3 s, +0,6 3 s y centro 2 s. El throttle va
SIEMPRE en 0,0: con las ruedas en el aire la direccion no puede desplazar el vehiculo.

Al salir, por el motivo que sea -fin normal, Ctrl-C o el SIGTERM de 'timeout'-, publica cuarenta
mensajes en cero, porque servo_pkg conserva el ultimo valor recibido.

POR QUE NO 'ros2 topic pub'
---------------------------
Se probo el 2026-09-28: lanzar un 'ros2 topic pub' por cada posicion no sirve. Tarda 2 o 3 s en
arrancar y emparejar, y en ventanas de 3 s casi no llega nada al servo. Un proceso que publica
sin parar no tiene ese problema.
"""
import signal
import sys
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from rclpy.signals import SignalHandlerOptions

from deepracer_interfaces_pkg.msg import ServoCtrlMsg

TOPICO = '/ctrl_pkg/servo_msg'
HZ = 20.0
ESPERA_EMPAREJAR_S = 10.0
SECUENCIA = [(0.0, 2.0), (0.6, 3.0), (-0.6, 3.0), (0.6, 3.0), (0.0, 2.0)]


def main():
    # Sin el manejador de rclpy: si no, Ctrl-C apaga el contexto antes del 'finally' y los
    # ceros de salida no se publican.
    rclpy.init(signal_handler_options=SignalHandlerOptions.NO)
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    nodo = Node('sonda_direccion')
    qos = QoSProfile(depth=10, reliability=ReliabilityPolicy.BEST_EFFORT)
    pub = nodo.create_publisher(ServoCtrlMsg, TOPICO, qos)

    def enviar(angulo):
        m = ServoCtrlMsg()
        m.angle = float(angulo)
        m.throttle = 0.0
        pub.publish(m)

    try:
        t0 = time.monotonic()
        while pub.get_subscription_count() == 0 and time.monotonic() - t0 < ESPERA_EMPAREJAR_S:
            rclpy.spin_once(nodo, timeout_sec=0.1)
        n = pub.get_subscription_count()
        print('suscriptores emparejados en %s: %d%s' % (
            TOPICO, n, '' if n else '  (ninguno: la orden no llegara a nadie)'), flush=True)
        for angulo, duracion in SECUENCIA:
            print('  direccion %+.1f durante %.0f s' % (angulo, duracion), flush=True)
            fin = time.monotonic() + duracion
            while time.monotonic() < fin:
                enviar(angulo)
                time.sleep(1.0 / HZ)
    except KeyboardInterrupt:
        pass
    finally:
        for _ in range(40):
            enviar(0.0)
            time.sleep(0.02)
        print('terminado: direccion al centro y traccion en cero', flush=True)
        nodo.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
