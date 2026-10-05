#!/usr/bin/env python3
"""Pruebas de la IMU de la tarjeta del DeepRacer (Bosch BMI160), sin instalar nada.

Lee el sensor directamente por /dev/i2c-1 con la biblioteca estandar de Python:
no necesita smbus2 ni ningun paquete de ROS. Se corre en el VEHICULO y como root:

    sudo -n python3 ~/tesis/probar_imu.py identidad
    sudo -n python3 ~/tesis/probar_imu.py despertar
    sudo -n python3 ~/tesis/probar_imu.py reposo [segundos]
    sudo -n python3 ~/tesis/probar_imu.py inclinar [segundos]
    sudo -n python3 ~/tesis/probar_imu.py girar [segundos]

Las pruebas, lo que se espera de cada una y que hacer si falla estan en
Documentos/PRUEBAS_IMU.md.

LO QUE ESCRIBE EN EL SENSOR
---------------------------
Solo 'despertar' (y las pruebas que lo llaman) escribe: manda al registro CMD
(0x7E) las ordenes de modo normal del acelerometro (0x11) y del giroscopio (0x15).
No cambia rangos ni frecuencias, y el sensor vuelve a reposo al apagar el carro.

REGISTROS DE LA BMI160 QUE SE USAN (hoja de datos de Bosch)
------------------------------------------------------------
0x00 CHIP_ID (0xD1)   0x02 ERR_REG   0x03 PMU_STATUS
0x0C-0x11 giroscopio x, y, z   0x12-0x17 acelerometro x, y, z (int16, little endian)
0x20 temperatura (23 C + valor / 512)   0x41 ACC_RANGE   0x43 GYR_RANGE   0x7E CMD
"""
import fcntl
import math
import os
import struct
import sys
import time

BUS = '/dev/i2c-1'
DIRECCION = 0x68
# I2C_SLAVE_FORCE: el bus lo comparte la pila de AWS, que lee otros dispositivos.
I2C_SLAVE_FORCE = 0x0706
G = 9.80665
# LSB por g segun ACC_RANGE, y LSB por grado/s segun GYR_RANGE.
LSB_ACC = {0x03: 16384.0, 0x05: 8192.0, 0x08: 4096.0, 0x0C: 2048.0}
RANGO_ACC = {0x03: 2, 0x05: 4, 0x08: 8, 0x0C: 16}
LSB_GIR = {0: 16.4, 1: 32.8, 2: 65.6, 3: 131.2, 4: 262.4}
RANGO_GIR = {0: 2000, 1: 1000, 2: 500, 3: 250, 4: 125}
MODO_ACC = {0: 'reposo', 1: 'normal', 2: 'bajo consumo', 3: '?'}
MODO_GIR = {0: 'reposo', 1: 'normal', 2: '?', 3: 'arranque rapido'}


class BMI160:

    def __init__(self):
        self.f = os.open(BUS, os.O_RDWR)
        fcntl.ioctl(self.f, I2C_SLAVE_FORCE, DIRECCION)

    def leer(self, registro, n=1):
        os.write(self.f, bytes([registro]))
        return os.read(self.f, n)

    def escribir(self, registro, valor):
        os.write(self.f, bytes([registro, valor]))

    def pmu(self):
        p = self.leer(0x03)[0]
        return p, (p >> 4) & 3, (p >> 2) & 3

    def despertar(self):
        _, acc, gir = self.pmu()
        if acc != 1:
            self.escribir(0x7E, 0x11)
            time.sleep(0.05)
        if gir != 1:
            self.escribir(0x7E, 0x15)
            time.sleep(0.10)
        return self.pmu()

    def escalas(self):
        ra = self.leer(0x41)[0] & 0x0F
        rg = self.leer(0x43)[0] & 0x07
        return ra, rg, LSB_ACC.get(ra), LSB_GIR.get(rg)

    def datos(self, lsb_acc, lsb_gir):
        """Giroscopio en grados/s y acelerometro en m/s^2."""
        gx, gy, gz, ax, ay, az = struct.unpack('<6h', self.leer(0x0C, 12))
        return ((gx / lsb_gir, gy / lsb_gir, gz / lsb_gir),
                (ax / lsb_acc * G, ay / lsb_acc * G, az / lsb_acc * G))

    def temperatura(self):
        crudo = struct.unpack('<h', self.leer(0x20, 2))[0]
        return None if crudo == -32768 else 23.0 + crudo / 512.0


def media_y_desviacion(valores):
    m = sum(valores) / len(valores)
    return m, math.sqrt(sum((v - m) ** 2 for v in valores) / len(valores))


def identidad(s):
    chip = s.leer(0x00)[0]
    err = s.leer(0x02)[0]
    p, acc, gir = s.pmu()
    ra, rg, _, _ = s.escalas()
    print('CHIP_ID      : 0x%02x   (esperado 0xd1, BMI160)' % chip)
    print('ERR_REG      : 0x%02x   (esperado 0x00)' % err)
    print('PMU_STATUS   : 0x%02x   acelerometro %s, giroscopio %s'
          % (p, MODO_ACC[acc], MODO_GIR[gir]))
    print('rango acel.  : 0x%02x = +-%s g' % (ra, RANGO_ACC.get(ra, '?')))
    print('rango giro   : 0x%02x = +-%s grados/s' % (rg, RANGO_GIR.get(rg, '?')))
    return 0 if chip == 0xD1 else 1


def despertar(s):
    p, acc, gir = s.despertar()
    print('PMU_STATUS tras despertar: 0x%02x   acelerometro %s, giroscopio %s'
          % (p, MODO_ACC[acc], MODO_GIR[gir]))
    print('esperado 0x14: los dos en modo normal')
    print('ERR_REG: 0x%02x   (esperado 0x00)' % s.leer(0x02)[0])
    return 0 if (acc, gir) == (1, 1) else 1


def preparar(s):
    s.despertar()
    _, _, la, lg = s.escalas()
    if la is None or lg is None:
        print('ABORTA: rango no reconocido; corre «identidad» y revisa los registros 0x41 y 0x43')
        sys.exit(2)
    return la, lg


def reposo(s, segundos):
    la, lg = preparar(s)
    print('Vehiculo QUIETO y sobre el suelo. Midiendo %.0f s...' % segundos, flush=True)
    giro, acel, repetidas, previa = [], [], 0, None
    t0 = time.time()
    while time.time() - t0 < segundos:
        g, a = s.datos(la, lg)
        if (g, a) == previa:
            repetidas += 1
        previa = (g, a)
        giro.append(g)
        acel.append(a)
        time.sleep(0.01)
    n = len(giro)
    print('muestras: %d en %.1f s = %.0f por segundo  (esperado: 40 o mas)'
          % (n, segundos, n / segundos))
    print('lecturas identicas seguidas: %d de %d  (esperado: pocas; muchas = dato congelado)'
          % (repetidas, n))
    print('\nACELEROMETRO (m/s^2)        media     desv.')
    for i, eje in enumerate('xyz'):
        m, d = media_y_desviacion([a[i] for a in acel])
        print('  %s                      %8.3f  %8.3f' % (eje, m, d))
    modulo = [math.sqrt(sum(c * c for c in a)) for a in acel]
    m, d = media_y_desviacion(modulo)
    print('  |a| (modulo)           %8.3f  %8.3f   (esperado 9,81 +- 0,3)' % (m, d))
    print('\nGIROSCOPIO (grados/s)       media     desv.')
    for i, eje in enumerate('xyz'):
        m, d = media_y_desviacion([g[i] for g in giro])
        print('  %s                      %8.3f  %8.3f' % (eje, m, d))
    print('  esperado: |media| < 3 (sesgo de fabrica) y desv. < 0,3 en cada eje')
    t = s.temperatura()
    print('\nTEMPERATURA del sensor: %s  (esperado: entre 20 y 50 C)'
          % ('no disponible' if t is None else '%.1f C' % t))
    return 0


def inclinar(s, segundos):
    la, lg = preparar(s)
    print('Cada 0,5 s: aceleracion en x, y, z (m/s^2). Inclina el vehiculo despacio.', flush=True)
    t0 = time.time()
    while time.time() - t0 < segundos:
        _, a = s.datos(la, lg)
        print('  t=%5.1f s   x=%7.2f   y=%7.2f   z=%7.2f' % ((time.time() - t0,) + a), flush=True)
        time.sleep(0.5)
    return 0


def girar(s, segundos):
    la, lg = preparar(s)
    print('1) QUIETO 3 s, para medir el sesgo del giroscopio...', flush=True)
    muestras = []
    t0 = time.time()
    while time.time() - t0 < 3.0:
        muestras.append(s.datos(la, lg)[0])
        time.sleep(0.01)
    sesgo = [sum(g[i] for g in muestras) / len(muestras) for i in range(3)]
    print('   sesgo x=%.3f  y=%.3f  z=%.3f grados/s' % tuple(sesgo))
    print('2) AHORA gira el vehiculo sobre el suelo. Durante %.0f s se integra el giro:' % segundos,
          flush=True)
    angulo = [0.0, 0.0, 0.0]
    t0 = time.time()
    previo = t0
    proximo = t0 + 0.5
    while time.time() - t0 < segundos:
        g, _ = s.datos(la, lg)
        ahora = time.time()
        dt = ahora - previo
        previo = ahora
        for i in range(3):
            angulo[i] += (g[i] - sesgo[i]) * dt
        if ahora >= proximo:
            print('  t=%5.1f s   giro acumulado  x=%7.1f   y=%7.1f   z=%7.1f grados'
                  % ((ahora - t0,) + tuple(angulo)), flush=True)
            proximo += 0.5
        time.sleep(0.005)
    print('\nRESULTADO: x=%.1f  y=%.1f  z=%.1f grados' % tuple(angulo))
    print('esperado: el eje vertical da el angulo girado (+ a la izquierda si apunta hacia arriba),')
    print('con 5 grados de error o menos en 90, y los otros dos ejes cerca de 0')
    return 0


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ('identidad', 'despertar', 'reposo', 'inclinar', 'girar'):
        print(__doc__.split('LO QUE ESCRIBE')[0])
        return 2
    prueba = sys.argv[1]
    segundos = float(sys.argv[2]) if len(sys.argv) > 2 else {'reposo': 30, 'inclinar': 20, 'girar': 15}.get(prueba, 0)
    s = BMI160()
    return {'identidad': lambda: identidad(s),
            'despertar': lambda: despertar(s),
            'reposo': lambda: reposo(s, segundos),
            'inclinar': lambda: inclinar(s, segundos),
            'girar': lambda: girar(s, segundos)}[prueba]()


if __name__ == '__main__':
    sys.exit(main())
