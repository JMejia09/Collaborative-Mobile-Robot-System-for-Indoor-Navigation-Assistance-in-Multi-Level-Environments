#!/usr/bin/env python3
"""Publica la IMU de la tarjeta del DeepRacer (Bosch BMI160) como sensor_msgs/Imu.

Que es esto
-----------
El controlador de la IMU para la navegacion del vehiculo. Lee el sensor por
/dev/i2c-1 con la biblioteca estandar de Python, igual que
`herramientas/probar_imu.py`, con la que se probo el sensor en los dos vehiculos
el 2026-10-05 (Documentos/Evidencia/S26_pruebas_imu.md). No necesita smbus2 ni
ningun paquete que no venga con ROS, y por eso no hay que instalar nada en las
tarjetas, que no tienen internet.

Lo arranca `nav2_hardware.launch.py` con `imu:=true`, junto al filtro EKF que
combina su velocidad de giro con el avance de rf2o. Como el lanzador corre como
root, el nodo puede abrir /dev/i2c-1 (root:i2c, 660).

Lo que publica
--------------
`imu/data` (relativo: `/robot2/imu/data` con espacio de nombres), a
`frecuencia` Hz, en el marco `frame_id`:

- velocidad angular en rad/s, con el sesgo medido al arrancar ya restado;
- aceleracion lineal en m/s^2, tal como la da el sensor;
- sin orientacion: `orientation_covariance[0] = -1`, como pide sensor_msgs.

Los ejes son los del sensor, sin girar: x a la izquierda, y hacia adelante y z
hacia abajo (pruebas 3 y 4 de S26_pruebas_imu.md). El giro hasta `base_link` lo
pone la junta `imu_joint` de `deepracer_hardware.urdf`, y el EKF lo aplica con
la TF. Por eso un giro a la izquierda sale aqui negativo en z y positivo en el
rumbo del filtro.

La calibracion
--------------
Al arrancar mide el sesgo del giroscopio durante `calibracion_s` segundos con el
vehiculo quieto: 0,65 grados/s en z en `amss-ez9n` y 0,47 en `amss-jgm9`, que sin
restar acumularian de 28 a 39 grados por minuto. Si en ese tiempo el vehiculo se
mueve (desviacion del giroscopio por encima de `umbral_quieto` grados/s en algun
eje), repite la medida y no publica hasta tener una buena. Las varianzas medidas
en la calibracion van a las covarianzas del mensaje.

Si el sensor deja de responder, el nodo sigue vivo, avisa y no publica: el EKF
sin IMU deja de girar el rumbo, y por eso `nav2_mapa_guardado.sh` comprueba que
`imu/data` publique antes de dar Nav2 por arrancado.
"""
import fcntl
import math
import os
import statistics
import struct
import sys
import time

BUS = '/dev/i2c-1'
DIRECCION = 0x68
# I2C_SLAVE_FORCE: el bus lo comparte la pila de AWS, que lee otros dispositivos.
I2C_SLAVE_FORCE = 0x0706
CHIP_ID = 0xD1
G = 9.80665
# LSB por g segun ACC_RANGE, y LSB por grado/s segun GYR_RANGE (hoja de datos).
LSB_ACC = {0x03: 16384.0, 0x05: 8192.0, 0x08: 4096.0, 0x0C: 2048.0}
LSB_GIR = {0: 16.4, 1: 32.8, 2: 65.6, 3: 131.2, 4: 262.4}
# Varianza minima de cada eje: con varianza cero el EKF no pondera la medida.
VARIANZA_MINIMA = 1e-6
# Lecturas fallidas seguidas antes de pasar del aviso al error.
FALLOS_PARA_ERROR = 50


class BMI160:
    """Acceso por registros al BMI160 (los mismos de probar_imu.py)."""

    def __init__(self, bus=BUS):
        self.f = os.open(bus, os.O_RDWR)
        fcntl.ioctl(self.f, I2C_SLAVE_FORCE, DIRECCION)

    def leer(self, registro, n=1):
        os.write(self.f, bytes([registro]))
        return os.read(self.f, n)

    def escribir(self, registro, valor):
        os.write(self.f, bytes([registro, valor]))

    def preparar(self):
        """Comprueba el chip, lo pone en modo normal y devuelve (LSB/g, LSB/grado/s)."""
        chip = self.leer(0x00)[0]
        if chip != CHIP_ID:
            raise RuntimeError('CHIP_ID 0x%02x, se esperaba 0x%02x (BMI160)' % (chip, CHIP_ID))
        pmu = self.leer(0x03)[0]
        if (pmu >> 4) & 3 != 1:
            self.escribir(0x7E, 0x11)
            time.sleep(0.05)
        if (pmu >> 2) & 3 != 1:
            self.escribir(0x7E, 0x15)
            time.sleep(0.10)
        pmu = self.leer(0x03)[0]
        if ((pmu >> 4) & 3, (pmu >> 2) & 3) != (1, 1):
            raise RuntimeError('el sensor no paso a modo normal (PMU_STATUS 0x%02x)' % pmu)
        ra = self.leer(0x41)[0] & 0x0F
        rg = self.leer(0x43)[0] & 0x07
        if ra not in LSB_ACC or rg not in LSB_GIR:
            raise RuntimeError('rango no reconocido: ACC_RANGE 0x%02x, GYR_RANGE 0x%02x' % (ra, rg))
        return LSB_ACC[ra], LSB_GIR[rg]

    def crudo(self):
        """Giroscopio x, y, z y acelerometro x, y, z, en cuentas del sensor."""
        return struct.unpack('<6h', self.leer(0x0C, 12))


def a_si(crudo, lsb_acc, lsb_gir):
    """Cuentas -> (velocidad angular en rad/s, aceleracion en m/s^2), ejes del sensor."""
    gx, gy, gz, ax, ay, az = crudo
    k = math.pi / 180.0 / lsb_gir
    return ((gx * k, gy * k, gz * k),
            (ax / lsb_acc * G, ay / lsb_acc * G, az / lsb_acc * G))


def calibrar(muestras, umbral_quieto_rad):
    """Sesgo y varianzas de una serie de muestras (giro, aceleracion) en reposo.

    Devuelve (sesgo, varianza_giro, varianza_acel, quieto). `quieto` es falso si
    algun eje del giroscopio se desvia mas de `umbral_quieto_rad`: el vehiculo se
    movio y el sesgo medido no vale.
    """
    giro = [[m[0][i] for m in muestras] for i in range(3)]
    acel = [[m[1][i] for m in muestras] for i in range(3)]
    sesgo = tuple(statistics.fmean(e) for e in giro)
    desv = [statistics.pstdev(e) for e in giro]
    var_giro = tuple(max(d * d, VARIANZA_MINIMA) for d in desv)
    var_acel = tuple(max(statistics.pvariance(e), VARIANZA_MINIMA) for e in acel)
    return sesgo, var_giro, var_acel, max(desv) <= umbral_quieto_rad


def diagonal(v):
    return [v[0], 0.0, 0.0, 0.0, v[1], 0.0, 0.0, 0.0, v[2]]


def crear_nodo(sensor=None):
    """Crea el nodo. `sensor` permite probarlo sin la tarjeta (prueba_imu_bmi160.py)."""
    from rclpy.node import Node
    from sensor_msgs.msg import Imu

    class NodoImu(Node):

        def __init__(self):
            super().__init__('imu_bmi160')
            self.frame_id = self.declare_parameter('frame_id', 'imu_link').value
            # 25 Hz y no 50: el 2026-10-05, a 50 Hz, el nodo ocupaba el 12 % de un
            # nucleo de la tarjeta y no pasaba de 31 Hz. El vehiculo gira a unas
            # decenas de grados/s, y el filtro corre a 15 Hz: 25 muestras sobran.
            frecuencia = float(self.declare_parameter('frecuencia', 25.0).value)
            self.calibracion_s = float(self.declare_parameter('calibracion_s', 3.0).value)
            self.umbral_quieto = math.radians(
                float(self.declare_parameter('umbral_quieto', 0.5).value))
            self.bus = self.declare_parameter('bus', BUS).value
            self.sensor = sensor if sensor is not None else BMI160(self.bus)
            self.lsb_acc, self.lsb_gir = self.sensor.preparar()
            self.pub = self.create_publisher(Imu, 'imu/data', 10)
            self.fallos = 0
            self.calibrado = False
            self.periodo = 1.0 / frecuencia
            self.get_logger().info(
                'BMI160 en %s 0x%02x; calibrando %.1f s con el vehiculo quieto'
                % (self.bus, DIRECCION, self.calibracion_s))
            self.calibrar()
            self.create_timer(self.periodo, self.publicar)

        def leer(self):
            return a_si(self.sensor.crudo(), self.lsb_acc, self.lsb_gir)

        def calibrar(self):
            intento = 0
            while True:
                intento += 1
                muestras = []
                t0 = time.monotonic()
                while time.monotonic() - t0 < self.calibracion_s:
                    try:
                        muestras.append(self.leer())
                    except OSError:
                        pass
                    time.sleep(0.01)
                if len(muestras) < 10:
                    self.get_logger().warn('calibracion %d: solo %d lecturas; se repite'
                                           % (intento, len(muestras)))
                    continue
                sesgo, var_giro, var_acel, quieto = calibrar(muestras, self.umbral_quieto)
                if quieto:
                    break
                self.get_logger().warn(
                    'calibracion %d: el vehiculo se movio (desviacion del giroscopio mayor de '
                    '%.2f grados/s); se repite. No lo toque.'
                    % (intento, math.degrees(self.umbral_quieto)))
            self.sesgo = sesgo
            # El mensaje se arma una vez y en cada publicacion solo se cambian el
            # sello y las lecturas: crearlo y convertir las covarianzas en cada
            # ciclo era la mayor parte del costo del nodo en la tarjeta.
            self.msg = Imu()
            self.msg.header.frame_id = self.frame_id
            self.msg.orientation_covariance[0] = -1.0
            self.msg.angular_velocity_covariance = diagonal(var_giro)
            self.msg.linear_acceleration_covariance = diagonal(var_acel)
            self.calibrado = True
            self.get_logger().info(
                'sesgo del giroscopio x=%.3f y=%.3f z=%.3f grados/s con %d lecturas; publicando '
                'imu/data en %s' % (*(math.degrees(s) for s in sesgo), len(muestras),
                                    self.frame_id))

        def publicar(self):
            try:
                giro, acel = self.leer()
            except OSError as error:
                self.fallos += 1
                if self.fallos == FALLOS_PARA_ERROR:
                    self.get_logger().error('%d lecturas fallidas seguidas del BMI160 (%s): '
                                            'no se publica la IMU' % (self.fallos, error))
                elif self.fallos < FALLOS_PARA_ERROR:
                    self.get_logger().warn('lectura del BMI160 fallida: %s' % error,
                                           throttle_duration_sec=5.0)
                return
            if self.fallos >= FALLOS_PARA_ERROR:
                self.get_logger().info('el BMI160 vuelve a responder')
            self.fallos = 0
            m, s = self.msg, self.sesgo
            m.header.stamp = self.get_clock().now().to_msg()
            w, a = m.angular_velocity, m.linear_acceleration
            w.x, w.y, w.z = giro[0] - s[0], giro[1] - s[1], giro[2] - s[2]
            a.x, a.y, a.z = acel
            self.pub.publish(m)

    return NodoImu()


def main():
    import rclpy
    rclpy.init(args=sys.argv)
    try:
        nodo = crear_nodo()
    except (OSError, RuntimeError) as error:
        print('imu_bmi160: no se pudo iniciar el BMI160: %s' % error, file=sys.stderr)
        rclpy.shutdown()
        return 1
    try:
        rclpy.spin(nodo)
    except KeyboardInterrupt:
        pass
    finally:
        nodo.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    return 0


if __name__ == '__main__':
    sys.exit(main())
