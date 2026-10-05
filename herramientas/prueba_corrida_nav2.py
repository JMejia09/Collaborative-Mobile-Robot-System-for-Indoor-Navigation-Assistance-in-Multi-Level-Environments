#!/usr/bin/env python3
"""Prueba de corrida_nav2.py contra un Nav2 de mentira, sin Gazebo ni vehiculo.

POR QUE EXISTE
--------------
Tres defectos de corrida_nav2.py aparecieron en campo y no en el escritorio:

  - al interrumpirla, la orden de parada no salia ('publisher's context is
    invalid', 30-sep): rclpy cerraba el contexto antes de 'parar()';
  - si Nav2 no confirmaba la meta, esperaba sin plazo (10 min el 30-sep y el
    2-oct);
  - no habia forma de encadenar misiones sin volver a dar la pose inicial.

Probarlos en Gazebo cuesta varios minutos por caso y el 5-oct tumbo el
portatil. Aqui un nodo de mentira hace de AMCL, de rf2o y de servidor de
NavigateToPose, y la herramienta corre de verdad contra el.

QUE COMPRUEBA
-------------
  1. Corrida normal con --salida: termina en 0 y la fila del CSV trae la pose de
     AMCL al terminar y 'pose_inicial' = si.
  2. --sin-pose-inicial: no publica /initialpose y la fila dice 'no'.
  3. SIGINT con el vehiculo en marcha: cancela la meta, publica ceros en
     /cmd_vel, sale con 130 y sin traza de error.
  4. SIGTERM: lo mismo.
  5. Nav2 que no confirma la meta: aborta con el codigo 8 antes de 45 s.

Uso, desde la raiz del repositorio y con ROS sourceado:

    python3 herramientas/prueba_corrida_nav2.py [ruta_a_otra_version]

Con la version anterior a octubre de 2026 tiene que fallar: asi se comprueba que
la prueba no es vacia.
"""
import csv
import os
import pathlib
import signal
import subprocess
import sys
import tempfile
import threading
import time

import rclpy
from geometry_msgs.msg import PoseWithCovarianceStamped, Twist
from nav2_msgs.action import NavigateToPose
from nav_msgs.msg import Odometry
from rclpy.action import ActionServer, CancelResponse, GoalResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from rclpy.qos import QoSDurabilityPolicy, QoSProfile, QoSReliabilityPolicy
from std_srvs.srv import Empty

RAIZ = pathlib.Path(__file__).resolve().parents[1]
# Con una ruta como argumento se prueba otra version (la anterior tiene que fallar).
HERRAMIENTA = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else RAIZ / 'herramientas/corrida_nav2.py'
NS = '/falso'


class Nav2Falso(Node):
    """AMCL, odometria y NavigateToPose minimos. 'mudo' no confirma las metas."""

    def __init__(self):
        super().__init__('nav2_falso')
        self.mudo = False
        self.x = 0.0
        self.cancelaciones = 0
        self.poses_iniciales = 0
        self.ceros_tras_cancelar = 0
        self.cancelada = False
        grupo = ReentrantCallbackGroup()
        qos = QoSProfile(depth=1, durability=QoSDurabilityPolicy.TRANSIENT_LOCAL,
                         reliability=QoSReliabilityPolicy.RELIABLE)
        self.pub_amcl = self.create_publisher(PoseWithCovarianceStamped, NS + '/amcl_pose', qos)
        self.pub_odom = self.create_publisher(Odometry, NS + '/odom', 10)
        self.create_subscription(PoseWithCovarianceStamped, NS + '/initialpose',
                                 self.al_recibir_pose, 10, callback_group=grupo)
        self.create_subscription(Twist, NS + '/cmd_vel', self.al_recibir_cmd, 10,
                                 callback_group=grupo)
        self.create_service(Empty, NS + '/request_nomotion_update',
                            lambda req, res: res, callback_group=grupo)
        self.servidor = ActionServer(self, NavigateToPose, NS + '/navigate_to_pose',
                                     execute_callback=self.ejecutar,
                                     goal_callback=self.al_recibir_meta,
                                     cancel_callback=self.al_cancelar,
                                     callback_group=grupo)
        self.create_timer(0.1, self.publicar, callback_group=grupo)

    def publicar(self):
        a = PoseWithCovarianceStamped()
        a.header.frame_id = 'map'
        a.pose.pose.position.x = self.x
        a.pose.pose.orientation.w = 1.0
        a.pose.covariance[0] = a.pose.covariance[7] = 0.05 ** 2
        self.pub_amcl.publish(a)
        o = Odometry()
        o.pose.pose.position.x = self.x
        o.pose.pose.orientation.w = 1.0
        self.pub_odom.publish(o)

    def al_recibir_pose(self, m):
        self.poses_iniciales += 1

    def al_recibir_cmd(self, m):
        if self.cancelada and m.linear.x == 0.0 and m.angular.z == 0.0:
            self.ceros_tras_cancelar += 1

    def al_recibir_meta(self, meta):
        if self.mudo:
            time.sleep(45.0)  # no confirma: la herramienta tiene que rendirse antes
        return GoalResponse.ACCEPT

    def al_cancelar(self, meta):
        self.cancelaciones += 1
        self.cancelada = True
        return CancelResponse.ACCEPT

    def ejecutar(self, meta):
        # Avanza 0,5 m/s hasta la meta, con 20 s de tope, o hasta que la cancelen.
        destino = meta.request.pose.pose.position.x
        fin = time.time() + 20.0
        while time.time() < fin and self.x < destino:
            if meta.is_cancel_requested:
                meta.canceled()
                return NavigateToPose.Result()
            self.x += 0.05
            time.sleep(0.1)
        meta.succeed()
        return NavigateToPose.Result()


def correr(args, csv_ruta, interrumpir=None, espera_meta=2.0):
    """Lanza la herramienta; si se pide, le manda una senal con la meta en curso."""
    orden = [sys.executable, '-u', str(HERRAMIENTA), '--ns', NS, '--csv', csv_ruta,
             '--tope', '25'] + args
    p = subprocess.Popen(orden, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    salida = []
    if interrumpir is not None:
        # Se lee hasta ver la meta enviada, y se interrumpe con el vehiculo en marcha.
        for linea in p.stdout:
            salida.append(linea)
            if '== meta' in linea:
                time.sleep(espera_meta)
                p.send_signal(interrumpir)
                break
    try:
        resto, _ = p.communicate(timeout=60)
    except subprocess.TimeoutExpired:
        # Una version que espera sin plazo se queda aqui: se mata y se marca.
        p.kill()
        resto, _ = p.communicate()
        return None, ''.join(salida) + resto + '\n(colgada: matada a los 60 s)'
    return p.returncode, ''.join(salida) + resto


def ultima_fila(csv_ruta):
    with open(csv_ruta, newline='') as f:
        return list(csv.DictReader(f))[-1]


def main():
    ok, fallos = 0, []

    def exigir(condicion, mensaje):
        nonlocal ok
        if condicion:
            ok += 1
        else:
            fallos.append(mensaje)

    rclpy.init()
    falso = Nav2Falso()
    ejecutor = MultiThreadedExecutor(num_threads=6)
    ejecutor.add_node(falso)
    hilo = threading.Thread(target=ejecutor.spin, daemon=True)
    hilo.start()
    time.sleep(1.0)
    carpeta = tempfile.mkdtemp(prefix='prueba_corrida_')
    csv_ruta = os.path.join(carpeta, 'corridas.csv')

    try:
        # 1. Corrida normal, con pose inicial.
        codigo, texto = correr(['--salida', '0', '0', '0', '--meta', '1.0', '0', '0',
                                '--corrida', 'normal'], csv_ruta)
        fila = ultima_fila(csv_ruta) if os.path.exists(csv_ruta) else {}
        exigir(codigo == 0, f'1. la corrida normal sale con {codigo}:\n{texto}')
        exigir(fila.get('pose_inicial') == 'si', f"1. pose_inicial = {fila.get('pose_inicial')!r}")
        exigir(fila.get('amcl_fin_x', '') != '', '1. falta la pose de AMCL al terminar')
        exigir(falso.poses_iniciales > 0, '1. no llego ninguna pose inicial')
        exigir('tolerancia de Nav2: 0,25' not in texto, '1. sigue el texto fijo de la tolerancia')

        # 2. Encadenada: sin pose inicial.
        antes = falso.poses_iniciales
        codigo, texto = correr(['--sin-pose-inicial', '--meta', '2.0', '0', '0',
                                '--corrida', 'encadenada'], csv_ruta)
        fila = ultima_fila(csv_ruta)
        exigir(codigo == 0, f'2. la encadenada sale con {codigo}:\n{texto}')
        exigir(falso.poses_iniciales == antes, '2. publico /initialpose con --sin-pose-inicial')
        exigir(fila.get('pose_inicial') == 'no', f"2. pose_inicial = {fila.get('pose_inicial')!r}")

        # 3 y 4. Interrupcion con la meta en curso: SIGINT y SIGTERM.
        for numero, senal, nombre in ((3, signal.SIGINT, 'SIGINT'), (4, signal.SIGTERM, 'SIGTERM')):
            falso.cancelada = False
            falso.ceros_tras_cancelar = 0
            cancel_antes = falso.cancelaciones
            meta_x = falso.x + 10.0
            # Con --salida y no --sin-pose-inicial, para que la version anterior
            # de la herramienta falle por la interrupcion y no por la opcion.
            codigo, texto = correr(['--salida', str(falso.x), '0', '0', '--meta', str(meta_x),
                                    '0', '0', '--corrida', nombre], csv_ruta, interrumpir=senal)
            time.sleep(0.5)
            exigir(codigo == 130, f'{numero}. con {nombre} sale con {codigo}:\n{texto}')
            exigir('INTERRUMPIDO' in texto, f'{numero}. con {nombre} no avisa de la interrupcion')
            exigir('Traceback' not in texto and 'context is invalid' not in texto,
                   f'{numero}. con {nombre} hay una traza de error:\n{texto}')
            exigir(falso.cancelaciones > cancel_antes, f'{numero}. con {nombre} no cancelo la meta')
            exigir(falso.ceros_tras_cancelar > 0,
                   f'{numero}. con {nombre} no llegaron ceros a /cmd_vel tras cancelar')

        # 5. Nav2 que no confirma la meta.
        falso.mudo = True
        t0 = time.time()
        codigo, texto = correr(['--salida', str(falso.x), '0', '0', '--meta', str(falso.x + 1.0),
                                '0', '0', '--corrida', 'mudo'], csv_ruta)
        duracion = time.time() - t0
        falso.mudo = False
        exigir(codigo == 8, f'5. con Nav2 mudo sale con {codigo}:\n{texto}')
        exigir(duracion < 45.0, f'5. tardo {duracion:.0f} s en rendirse')
        exigir('no confirmo la meta' in texto, '5. no explica por que aborta')
    finally:
        ejecutor.shutdown()
        falso.destroy_node()
        rclpy.try_shutdown()

    print('=' * 62)
    if fallos:
        for f in fallos:
            print('  [MAL]', f)
        print(f'{len(fallos)} comprobaciones FALLAN de {ok + len(fallos)}')
        return 1
    print(f'Todas las comprobaciones pasan ({ok}).')
    return 0


if __name__ == '__main__':
    sys.exit(main())
