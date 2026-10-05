# Pruebas de la IMU del DeepRacer

Antes de integrar la IMU en la navegación hay que comprobar que funciona: que responde, que mide la
gravedad, que su giroscopio está quieto cuando el vehículo está quieto y que mide bien un giro
conocido. Las pruebas usan [`herramientas/probar_imu.py`](../herramientas/probar_imu.py), que lee el
sensor por el bus I2C con la biblioteca estándar de Python y no instala nada en el vehículo.

El sensor es una Bosch BMI160 en el bus I2C 1, dirección 0x68 (confirmada en `amss-ez9n` el 5-oct:
registro de identificación `0xd1`). Viene en reposo; la prueba 2 lo despierta escribiendo dos
órdenes en el propio sensor, que vuelve a reposo al apagar el vehículo.

## 0. Preparación

| | |
|---|---|
| Copiar el programa | `scp herramientas/probar_imu.py deepracer@192.168.0.102:~/tesis/` |
| Cómo se corre cada prueba | `ssh -t deepracer@192.168.0.102 "sudo -n python3 ~/tesis/probar_imu.py <prueba>"` |
| Vehículo | Encendido, sobre el suelo y en un lugar plano. Las ruedas no giran en ninguna prueba |

## 1. Las pruebas

| # | Prueba | Qué comprueba | Orden (`<prueba>`) | Resultado esperado | Si falla |
|---|---|---|---|---|---|
| 1 | Identidad | Que el chip es una BMI160 y no tiene errores | `identidad` | `CHIP_ID 0xd1`, `ERR_REG 0x00`, acelerómetro y giroscopio en reposo, rangos de ±2 g y ±2000 grados/s | Otro `CHIP_ID`: no es el chip esperado; parar y anotar |
| 2 | Despertar | Que el sensor obedece y pasa a medir | `despertar` | `PMU_STATUS 0x14` (los dos en modo normal) y `ERR_REG 0x00` | Si no pasa a normal, repetir; si sigue igual, el sensor no acepta órdenes |
| 3 | Reposo, 30 s | Gravedad, ruido, sesgo, frecuencia y temperatura con el vehículo quieto | `reposo 30` | Módulo de la aceleración 9,81 ± 0,3 m/s²; un eje cerca de ±9,8 y los otros dos por debajo de 0,5. Giroscopio con media menor de 3 grados/s y desviación menor de 0,3 en cada eje. 40 muestras por segundo o más, pocas lecturas idénticas seguidas, temperatura entre 20 y 50 °C | Módulo lejos de 9,81: rango mal leído o sensor dañado. Muchas lecturas idénticas: el dato no se actualiza |
| 4 | Inclinar, 20 s | Qué eje del sensor apunta hacia adelante, cuál a la izquierda y cuál arriba | `inclinar 20`, y durante la prueba: 3 s quieto, levantar la nariz unos 30° durante 3 s, bajar, levantar el costado derecho unos 30° (el vehículo se inclina a la izquierda) durante 3 s, bajar | En reposo, el eje vertical en unos ±9,8. Con la nariz arriba cambia el eje de adelante, unos 4,9 m/s²; con el costado arriba cambia el eje lateral | Si no cambia ningún eje, el dato no se actualiza |
| 5 | Giro de 90° | Que el giroscopio mide un giro conocido | `girar 15`: 3 s quieto, y después girar el vehículo a mano 90° a la izquierda sobre el suelo, despacio, usando la junta de las baldosas o una cinta como referencia | El eje vertical acumula unos +90° (o −90° si apunta hacia abajo), con 5° de error o menos; los otros dos, cerca de 0 | Más de 5° de error: repetir con más cuidado en el ángulo; si se repite, anotarlo, porque fija lo que puede aportar la IMU |
| 6 | Giro de 90° a la derecha y de 360° | Signo y escala en los dos sentidos | `girar 15` girando 90° a la derecha; después `girar 30` dando una vuelta completa | −90° ± 5° a la derecha; 360° ± 10° en la vuelta | Igual que la prueba 5 |
| 7 | Deriva, 60 s | Cuánto se desvía el ángulo integrado con el vehículo quieto | `girar 60`, sin tocar el vehículo | Menos de 5° en el eje vertical al final de los 60 s | Más deriva: el sesgo cambia y hay que calibrarlo más tiempo antes de usar el sensor |

## 2. Qué anotar

| Dato | Prueba |
|---|---|
| Media y desviación de cada eje, en reposo | 3 |
| Qué eje apunta adelante, cuál a la izquierda y cuál arriba, con su signo | 4 |
| Ángulo medido en cada giro y su error | 5 y 6 |
| Deriva en 60 s | 7 |
| Temperatura | 3 |

Con la orientación de los ejes (prueba 4) se escribe la posición del sensor en la URDF, y con el
sesgo y la deriva (pruebas 3 y 7) se fija la calibración del filtro que combinará la IMU con rf2o.
Las mismas pruebas se repiten en `amss-jgm9`.
