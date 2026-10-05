#!/usr/bin/env python3
"""El nodo de la IMU publica bien sin la tarjeta: unidades, sesgo, calibracion y fallos.

POR QUE EXISTE
--------------
`imu_bmi160.py` (deepracer_bringup/scripts) da al EKF la velocidad de giro del
vehiculo. Si convierte mal las unidades, no resta el sesgo o lo mide con el
vehiculo en movimiento, el rumbo del filtro se tuerce sin ningun error a la
vista: Nav2 sigue planificando sobre una odometria girada. En el vehiculo eso se
ve tarde, en el pasillo. Aqui se prueba con un sensor falso que responde como el
BMI160 medido el 2026-10-05 (Documentos/Evidencia/S26_pruebas_imu.md).

QUE COMPRUEBA
-------------
  1. Unidades: cuentas del sensor a rad/s y m/s^2 con los rangos de fabrica.
  2. Calibracion: el sesgo es la media en reposo; un vehiculo que se mueve no
     pasa por quieto; la varianza no baja de su minimo.
  3. El nodo, con el sensor falso: calibra, publica `imu/data` en `imu_link` a
     unos 50 Hz, con el sesgo restado (un giro de -10 grados/s sale -10), sin
     orientacion y con covarianzas positivas.
  4. Si el sensor deja de responder, el nodo no publica y no se cae; al volver,
     publica otra vez.
  5. Si el vehiculo gira durante la calibracion, la repite y el sesgo sale del
     intento quieto.
  6. Sin sensor (un bus que no existe), el programa sale con codigo 1 y lo dice.

Uso, desde la raiz del repositorio, con ROS sourceado:

    ROS_DOMAIN_ID=93 ROS_LOCALHOST_ONLY=1 python3 herramientas/prueba_imu_bmi160.py
"""
import importlib.util
import math
import pathlib
import statistics
import subprocess
import sys
import time

RAIZ = pathlib.Path(__file__).resolve().parents[1]
NODO = RAIZ / 'Robot/aws-deepracer/deepracer_bringup/scripts/imu_bmi160.py'

spec = importlib.util.spec_from_file_location('imu_bmi160', NODO)
imu = importlib.util.module_from_spec(spec)
spec.loader.exec_module(imu)

# Sesgo en cuentas, del orden del medido en amss-ez9n (1,22 / -0,29 / 0,65 grados/s).
SESGO = (20, -5, 11)
GRAVEDAD_Z = -16384          # z hacia abajo: -1 g en reposo
GIRO_IZQUIERDA = -164        # -10 grados/s en el z del sensor (16,4 LSB por grado/s)


class SensorFalso:
    """Responde como el BMI160: sesgo, un poco de ruido y la fase que pida la prueba."""

    def __init__(self, mover_primeras=0):
        self.n = 0
        self.fase = 'quieto'
        self.mover_primeras = mover_primeras

    def preparar(self):
        return 16384.0, 16.4

    def crudo(self):
        self.n += 1
        if self.fase == 'fallar':
            raise OSError(121, 'Remote I/O error')
        ruido = 1 if self.n % 2 else -1
        gx, gy, gz = (s + ruido for s in SESGO)
        if self.n <= self.mover_primeras:
            gz += 300        # alguien gira el vehiculo a mano, en un solo sentido
        if self.fase == 'girar':
            gz += GIRO_IZQUIERDA
        return gx, gy, gz, 300 + ruido, -200, GRAVEDAD_Z


def main():
    ok, fallos = 0, []

    def exigir(condicion, mensaje):
        nonlocal ok
        if condicion:
            ok += 1
            print('  [OK ]', mensaje)
        else:
            fallos.append(mensaje)
            print('  [MAL]', mensaje)

    print('1. Unidades')
    giro, acel = imu.a_si((164, -164, 0, 0, 0, -16384), 16384.0, 16.4)
    exigir(abs(giro[0] - math.radians(10)) < 1e-9 and abs(giro[1] + math.radians(10)) < 1e-9,
           '164 cuentas con +-2000 grados/s son 10 grados/s = %.5f rad/s' % giro[0])
    exigir(abs(acel[2] + 9.80665) < 1e-9, '-16384 cuentas con +-2 g son -9,80665 m/s^2')

    print('2. Calibracion')
    quietas = [imu.a_si((20 + (1 if i % 2 else -1), -5, 11, 0, 0, -16384), 16384.0, 16.4)
               for i in range(100)]
    sesgo, var_giro, var_acel, quieto = imu.calibrar(quietas, math.radians(0.5))
    exigir(quieto and abs(math.degrees(sesgo[2]) - 11 / 16.4) < 1e-9,
           'en reposo el sesgo es la media: z = %.3f grados/s' % math.degrees(sesgo[2]))
    exigir(min(var_giro + var_acel) >= imu.VARIANZA_MINIMA,
           'ninguna varianza baja de %g' % imu.VARIANZA_MINIMA)
    movidas = [imu.a_si((20, -5, 11 + (300 if i % 2 else -300), 0, 0, -16384), 16384.0, 16.4)
               for i in range(100)]
    exigir(not imu.calibrar(movidas, math.radians(0.5))[3],
           'un giroscopio que oscila 18 grados/s no pasa por quieto')

    import rclpy
    from rclpy.executors import SingleThreadedExecutor
    from sensor_msgs.msg import Imu
    rclpy.init(args=['--ros-args', '-p', 'calibracion_s:=0.4'])
    try:
        print('3. El nodo con el sensor falso')
        falso = SensorFalso()
        t0 = time.monotonic()
        nodo = imu.crear_nodo(falso)
        exigir(nodo.calibrado and time.monotonic() - t0 >= 0.4,
               'calibra antes de publicar (%.2f s)' % (time.monotonic() - t0))
        oyente = rclpy.create_node('oyente_imu')
        recibidos = []
        oyente.create_subscription(Imu, 'imu/data', recibidos.append, 50)
        ejecutor = SingleThreadedExecutor()
        ejecutor.add_node(nodo)
        ejecutor.add_node(oyente)

        def girar(segundos):
            fin = time.monotonic() + segundos
            while time.monotonic() < fin:
                ejecutor.spin_once(timeout_sec=0.01)

        girar(0.5)
        falso.fase = 'girar'
        recibidos.clear()
        girar(1.0)
        n = len(recibidos)
        exigir(40 <= n <= 60, '%d mensajes en 1 s (se esperan unos 50)' % n)
        if n:
            m = recibidos[-1]
            z = statistics.fmean([math.degrees(r.angular_velocity.z) for r in recibidos])
            exigir(abs(z + 10.0) < 0.1,
                   'un giro a la izquierda de -10 grados/s sale %.3f, con el sesgo restado' % z)
            exigir(all(abs(math.degrees(r.angular_velocity.x)) < 0.1 for r in recibidos),
                   'en x solo queda el ruido: el sesgo de 1,22 grados/s se resto')
            exigir(m.header.frame_id == 'imu_link', 'marco %r' % m.header.frame_id)
            exigir(m.orientation_covariance[0] == -1.0, 'sin orientacion (covarianza[0] = -1)')
            exigir(m.angular_velocity_covariance[8] > 0 and m.linear_acceleration_covariance[8] > 0,
                   'covarianzas de giro y aceleracion positivas')
            exigir(abs(m.linear_acceleration.z + 9.80665) < 0.01,
                   'la aceleracion en z sale %.3f m/s^2, sin girar ni restar' % m.linear_acceleration.z)
            sellos = [r.header.stamp.sec + r.header.stamp.nanosec * 1e-9 for r in recibidos]
            exigir(all(b > a for a, b in zip(sellos, sellos[1:])), 'sellos de tiempo crecientes')

        print('4. El sensor deja de responder')
        falso.fase = 'fallar'
        girar(0.1)
        recibidos.clear()
        girar(0.5)
        exigir(not recibidos, 'sin respuesta del sensor no se publica (%d mensajes)' % len(recibidos))
        falso.fase = 'girar'
        girar(0.5)
        exigir(len(recibidos) >= 15, 'al volver el sensor se publica otra vez (%d en 0,5 s)'
               % len(recibidos))
        ejecutor.shutdown()
        nodo.destroy_node()

        print('5. El vehiculo gira durante la calibracion')
        falso = SensorFalso(mover_primeras=20)
        nodo = imu.crear_nodo(falso)
        # Si aceptara el primer intento, el sesgo en z saldria cerca de 10 grados/s.
        exigir(abs(math.degrees(nodo.sesgo[2]) - 11 / 16.4) < 0.05,
               'descarta el intento con giro: sesgo z = %.3f grados/s (%d lecturas)'
               % (math.degrees(nodo.sesgo[2]), falso.n))
        nodo.destroy_node()
        oyente.destroy_node()
    finally:
        rclpy.shutdown()

    print('6. Sin sensor')
    r = subprocess.run([sys.executable, str(NODO), '--ros-args', '-p', 'bus:=/no/existe/i2c-1'],
                       capture_output=True, text=True, timeout=30)
    exigir(r.returncode == 1 and 'no se pudo iniciar el BMI160' in r.stderr,
           'sale con codigo %d y lo dice' % r.returncode)

    print('=' * 62)
    if fallos:
        print(f'{len(fallos)} comprobaciones FALLAN de {ok + len(fallos)}')
        return 1
    print(f'Todas las comprobaciones pasan ({ok}).')
    return 0


if __name__ == '__main__':
    sys.exit(main())
