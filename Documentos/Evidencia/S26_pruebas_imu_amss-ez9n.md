# Pruebas de la IMU en `amss-ez9n` (5 de octubre)

Registro de las siete pruebas de [`PRUEBAS_IMU.md`](../PRUEBAS_IMU.md) sobre la IMU de la tarjeta de
`amss-ez9n` (deepy), con [`herramientas/probar_imu.py`](../../herramientas/probar_imu.py), que lee el
sensor por el bus I2C sin instalar nada. Las corrió Santiago desde el portátil, por SSH, con el
vehículo sobre el suelo y las ruedas quietas; Claude preparó las pruebas y analizó las salidas.

## Resultado

La IMU funciona: es una Bosch BMI160 en el bus I2C 1, dirección 0x68, integrada en la tarjeta del
vehículo (Pegatron, modelo «AWS DeepRacer», procesador Intel Atom E3930). Las siete pruebas cumplen
su criterio. El giroscopio midió giros de 90° y 360° hechos a mano con un error de 0,2 % a 0,4 %, y
quieto no acumuló ni 0,05° en 60 s, una vez restado el sesgo medido justo antes.

| # | Prueba | Medido | Criterio | |
|---|---|---|---|---|
| 1 | Identidad | `CHIP_ID 0xd1`, `ERR_REG 0x00`, en reposo, ±2 g y ±2000 °/s | `0xd1` y sin errores | cumple |
| 2 | Despertar | `PMU_STATUS 0x14` | acelerómetro y giroscopio en modo normal | cumple |
| 3 | Reposo, 30 s | 2683 muestras (89 por segundo), ninguna repetida; módulo de la aceleración 10,008 m/s²; giroscopio con medias de 1,224, −0,294 y 0,648 °/s y desviaciones de 0,154, 0,187 y 0,056 °/s (x, y, z); 29,1 °C | 9,81 ± 0,3 m/s²; media < 3 °/s y desviación < 0,3 °/s | cumple |
| 4 | Inclinar | Nariz arriba: y de 0,4 a unos 5,3 m/s²; costado derecho arriba: x de 0,3 a −4,2 m/s² | cambian los ejes horizontales | cumple |
| 5 | 90° a la izquierda | z = −89,6° | −90° ± 5° | cumple |
| 6 | 90° a la derecha; una vuelta a la izquierda | z = +89,8°; z = −358,6° | ±90° ± 5°; −360° ± 10° | cumple |
| 7 | Deriva, 60 s quieto | z = 0,0° | menos de 5° | cumple |

## Orientación del sensor

| Eje del sensor | Apunta hacia | Evidencia |
|---|---|---|
| x | la izquierda | Con el costado derecho arriba, x bajó a −4,2 m/s² |
| y | adelante | Con la nariz arriba, y subió a unos 5,3 m/s² (unos 33°) |
| z | abajo | En reposo, z marca −9,99 m/s² |

Para la URDF, el marco de la IMU está girado 180° en roll y 90° en yaw respecto a `base_link`
(`rpy="3.1416 0 1.5708"`). Un giro del vehículo a la izquierda sale negativo en el giroscopio z.

En reposo, x e y marcan 0,35 y 0,42 m/s², una inclinación de unos 3° entre el sensor y la vertical
(suelo, montaje o desfase del sensor). Por eso, al girar sobre la vertical, una parte pequeña del
giro aparece en x e y (de 3° a 11° en las pruebas 5 y 6), sin efecto apreciable en z.

## Sesgo del giroscopio

| Corrida | x | y | z |
|---|---|---|---|
| Prueba 5 | 1,215 | −0,310 | 0,656 |
| Prueba 6a | 1,224 | −0,283 | 0,649 |
| Prueba 6b | 1,248 | −0,285 | 0,649 |
| Prueba 7 | 1,239 | −0,290 | 0,652 |

Valores en grados/s. El sesgo en z se mantuvo entre 0,649 y 0,656 °/s durante la sesión. Sin restarlo, el
rumbo acumularía unos 39° por minuto; restado, la prueba 7 no acumuló error apreciable.

## Lo que estas pruebas no cubren

- La vibración con los motores en marcha: el vehículo se giró siempre a mano.
- La variación del sesgo con la temperatura en una sesión larga.
- `amss-jgm9`: falta comprobar su IMU y repetir las pruebas.

## Para integrarla

1. Un controlador que publique `sensor_msgs/Imu` (el paquete de la comunidad, o un nodo propio
   sobre la misma lectura de `probar_imu.py`).
2. El marco `imu_link` en `deepracer_hardware.urdf`, con la orientación de arriba.
3. La calibración del sesgo con el vehículo quieto al arrancar.
4. El filtro EKF que combine la velocidad de giro con rf2o ([`PLAN_S26.md`](../PLAN_S26.md) §2.3), y
   las corridas con IMU y sin ella en el piso 4 (§3.2).
