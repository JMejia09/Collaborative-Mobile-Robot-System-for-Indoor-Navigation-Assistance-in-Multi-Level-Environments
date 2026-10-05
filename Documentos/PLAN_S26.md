# Plan de la semana 26 (5 al 9 de octubre)

La meta de la semana es llegar al viernes con la misión con relevo entre los pisos 3 y 4 sobre los
dos vehículos (compuerta G-5). La toma de datos se cierra el viernes 16, en el corte C-3 del
[acta](ACTA_GO_NOGO.md). Para llegar hay que dejar los vehículos estables (carga, escala, cámaras),
cerrar G-3 e integrar la IMU de la tarjeta. Las pruebas de esta semana son más estrictas que las
anteriores. El vehículo encadena misiones sin que nadie lo reubique ni le vuelva a dar la pose
inicial. Entre una misión y la siguiente no vuelve a su escalera: el coordinador lo envía a recoger
al usuario desde donde quedó (§6.2 del [acta](ACTA_GO_NOGO.md)). Lo que se hizo la semana anterior
está en [`Entregable_semana_25.md`](Entregables/Entregable_semana_25.md).

Vehículos: `amss-ez9n` (deepy, 192.168.0.102) va en el piso 3 como `robot1`; `amss-jgm9` (racey,
192.168.0.104) va en el piso 4 como `robot2` y lleva el coordinador. Todas las órdenes se lanzan
desde la raíz del repositorio en el portátil.

## 0. La semana de un vistazo

| Día | Qué se hace | Quién | Vehículos | Al terminar el día |
|---|---|---|---|---|
| Lun 5, mañana | Acta: cambio de sitio y corte C-1. Correcciones de las herramientas de campo | Santiago y Claude | no | Acta al día; herramientas corregidas y probadas en simulación |
| Lun 5, tarde | Desactivar las cámaras, comprobar la IMU, copiar grabaciones, nivelar los dos vehículos | Santiago y Jonny | los dos | Se sabe si hay IMU; vehículos nivelados |
| Mar 6 | IMU funcionando y combinada con rf2o (si existe). Red entre los pisos 3 y 4 | Santiago y Claude; Jonny la red | los dos | La IMU publica en los dos vehículos; la red llega a los dos pisos |
| Mié 7 | Radio de giro. Misiones encadenadas en el piso 4 sin tocar el vehículo, con y sin IMU. Media vuelta para ir a recoger a un usuario | Santiago y Jonny | uno cada vez | G-3 evaluada; se sabe si el vehículo da media vuelta solo |
| Jue 8 | Coordinador en el vehículo, agentes en los dos, interfaz desde el teléfono; una misión en un solo piso | los dos | los dos | Misión en un piso pedida desde el teléfono, con registro |
| Vie 9 | G-5: misión del piso 3 al piso 4 con relevo, y una segunda misión encadenada sin tocar los vehículos. Corte semanal en la noche | los dos | los dos | G-5 intentada con registro; entregable de S26 |

Reglas de toda la semana:

- Los dos vehículos se tocan a la vez: lo que se instale en uno se instala en el otro el mismo día.
- No se navega hacia el borde de una escalera.
- Las medias vueltas solo se piden en los tramos anchos frente a los salones 301-302 y 401-402
  (de 3,1 a 3,2 m), con una persona junto al vehículo.
- Después de la primera salida, el vehículo no se toca ni se reubica entre misiones. Cada llegada se
  marca en el piso, junto al vehículo, y se mide desde esa marca.
- Cada llegada se mide con flexómetro antes de tocar el vehículo.
- Las grabaciones y registros se copian al portátil, a `~/tesis_evidencia/`, al terminar cada corrida.

---

## 1. Lunes 5

### 1.1 · Acta: cambio de sitio y corte C-1 (hecho)

Santiago habló con los directores el 5-oct. Sus respuestas están en el §6.2 del
[acta](ACTA_GO_NOGO.md), y G-2 (alcanzada) y G-3 (abierta) en su §4.1.

| Pregunta | Respuesta |
|---|---|
| Sitio | Se acepta el cambio a los pisos 3 y 4; los directores lo trataron también con los evaluadores |
| (1) a (3) Corte C-1 | Sin fecha nueva y sin NO-GO: organizar el trabajo para presentar a tiempo. La demostración con los vehículos sigue, G-3 queda abierta con 0,5 m y C-2 y C-3 no cambian |
| (4) Regreso automático | Solo al cancelar (RF-29), como hoy. Entre misiones el vehículo no vuelve: el coordinador lo envía a recoger al usuario desde donde quedó. El regreso tras una misión completada es opcional y sin prioridad |

### 1.2 · Correcciones de las herramientas de campo (mañana, Claude)

| Tarea | Qué se corrige | Por qué |
|---|---|---|
| a | `corrida_nav2.py` publica velocidad cero antes de cerrar cuando se interrumpe | El 30-sep, al interrumpir una corrida, la orden de parada no salió (`publisher's context is invalid`) |
| b | `corrida_nav2.py` espera la confirmación de la meta como mucho 30 s | El 30-sep y el 2-oct la corrida se quedó esperando 10 min |
| c | `corrida_nav2.py` guarda la pose de AMCL en el instante en que Nav2 termina, antes de refrescarla | El 30-sep el refresco hizo saltar la pose 7,5 m y el informe dio una llegada falsa |
| d | `corrida_nav2.py` deja de imprimir «tolerancia de Nav2: 0,25» | Es un texto fijo; el margen real es 1,0 m |
| e | `lanzar_bag.inc` cierra el grabador con una interrupción y espera 10 s antes de matarlo | Con `SIGKILL` se pierde el final de la grabación (2-oct) |
| f | `nav2_mapa_guardado.sh` admite `ESCALA` (por defecto 0,9) y apaga `camera_node` y `sensor_fusion_node` antes de Nav2 | Con 0,9 racey no arranca y deepy va a 1,58 m/s; con la cámara y la fusión encendidas Nav2 se cayó (2-oct) |
| g | `corrida_nav2.py --sin-pose-inicial`: no publica la pose inicial y toma como salida la pose actual de AMCL | Para encadenar misiones sin volver a decirle a AMCL dónde está el vehículo, como en la operación real |

Prueba de cierre: `python3 herramientas/prueba_corrida_nav2.py`, que corre la herramienta contra un
Nav2 de mentira, sin Gazebo (el ensayo en Gazebo tumbó el portátil el 5-oct). Comprueba la corrida
normal, la encadenada, la interrupción con `SIGINT` y con `SIGTERM` y el límite de la confirmación.

> Estado, 5-oct: hecho. Las siete correcciones están en las herramientas, la prueba da 21 de 21 con la
> versión nueva y 15 fallos con la anterior (la interrupción reproduce el defecto del 30-sep), y el
> grabador cierra limpio con la interrupción. La versión nueva del CSV añade columnas: cada serie va
> en un fichero nuevo, `campana_s26_racey.csv` y `campana_s26_deepy.csv`.

### 1.3 · Desactivar las cámaras (tarde, en los dos vehículos)

Las cámaras se quedan conectadas, porque sin ellas el vehículo pierde su aspecto, y se desactivan por
software con una regla de `udev`: el sistema no autoriza los dispositivos `29fe:4d53` (GEO Semi
Condor), así que no crea los `/dev/video*` y la pila de AWS no las abre. La regla está en
[`config/90-tesis-camaras-desactivadas.rules`](../Robot/aws-deepracer/deepracer_bringup/config/90-tesis-camaras-desactivadas.rules),
sobrevive a los reinicios y se deshace borrando el archivo y reiniciando.

| Paso | Comando | Esperado |
|---|---|---|
| 1. Identificar | `ssh deepracer@192.168.0.104 "lsusb"` | Dos `29fe:4d53 GEO Semi Condor` (cámaras) y un `10c4:ea60 Silicon Labs CP210x` (LiDAR) |
| 2. Instalar la regla | `scp Robot/aws-deepracer/deepracer_bringup/config/90-tesis-camaras-desactivadas.rules deepracer@192.168.0.104:/tmp/` y `ssh deepracer@192.168.0.104 "sudo -n cp /tmp/90-tesis-camaras-desactivadas.rules /etc/udev/rules.d/"` | Sin salida |
| 3. Aplicarla sin reiniciar | `ssh deepracer@192.168.0.104 "sudo -n udevadm control --reload-rules && sudo -n udevadm trigger --action=add --subsystem-match=usb --attr-match=idVendor=29fe"` | Sin salida |
| 4. Comprobar | `ssh deepracer@192.168.0.104 "ls /dev/video*"` y la autorización en `/sys/bus/usb/devices/<puerto>/authorized` | Ningún `/dev/video`; `0` en los puertos de las cámaras y `1` en el del LiDAR |
| 5. El LiDAR sigue | `ros2 topic hz /rplidar_ros/scan`, como root y con la partición | Unos 7 Hz |

`lsusb` sigue mostrando las cámaras: están conectadas, pero sin autorizar. `nivelar_carros.sh`
informa del estado en cada vehículo.

> Estado, 5-oct: hecho en `amss-ez9n`. Antes, `/dev/video0` a `/dev/video7`; después, ninguno;
> autorización `0 0 1` (cámaras en los puertos 1-4 y 1-6, LiDAR en el 1-3); LiDAR a 6,90 Hz. En
> `amss-jgm9`, lo mismo: las cámaras en los mismos puertos, `0 0 1` y LiDAR a 6,82 Hz.

### 1.4 · Comprobar la IMU (tarde, en los dos vehículos)

La documentación de AWS dice que la tarjeta trae acelerómetro y giroscopio; el paquete de la
comunidad lo lee como un Bosch BMI160 en el bus I2C 1, dirección 0x68. La orden lee el registro 0 del
sensor, que en el BMI160 vale `0xd1`, sin instalar nada en el vehículo.

| | |
|---|---|
| Comando | `bash herramientas/nivelar_carros.sh --imu` (los dos vehículos; si el bus está ocupado, reintenta solo con `I2C_SLAVE_FORCE`) |
| Esperado | En cada vehículo, la lista de buses con `/dev/i2c-1` y `IMU: el registro 0 en 0x68 vale 0xd1 (BMI160)` |
| Si falla | Probar a mano la dirección `0x69` y los otros buses de la lista, con la orden de la función `imu` del guion. Si ninguno responde `0xd1`, la tarjeta no tiene ese sensor accesible: la IMU pasa a trabajos futuros y el martes se dedica a G-5 |
| Cierre | `0xd1` en los dos vehículos, con el bus y la dirección anotados |

> Estado, 5-oct: hecho. Los dos vehículos tienen la BMI160 (`0xd1` en I2C 1, 0x68) y pasaron las
> pruebas de [`PRUEBAS_IMU.md`](PRUEBAS_IMU.md); solo el módulo de la aceleración de `amss-jgm9` queda
> fuera de su criterio, sin efecto en el giroscopio
> ([`S26_pruebas_imu.md`](Evidencia/S26_pruebas_imu.md)).

Si responde `0xd1`, se comprueba que el sensor mide bien con las siete pruebas de
[`PRUEBAS_IMU.md`](PRUEBAS_IMU.md) (identidad, gravedad, ruido, orientación de los ejes, giros de
90° y 360° y deriva), antes de integrarlo en la navegación.

### 1.5 · Copiar las grabaciones pendientes (tarde)

| | |
|---|---|
| Qué | De racey: `campana_p2r_01` a `campana_p2r_08`, `campana_p4r_01`, `campana_p4r_02`, los CSV `campana_p2_racey.csv` y `campana_p4_racey.csv`. De deepy: `campana_p4d_02` y `campana_p4_deepy.csv` |
| Comando | `ssh deepracer@192.168.0.104 "cd ~ && tar czf - campana_p2r_0* campana_p4r_0* campana_p*_racey.csv p2r_0*.log p4r_0*.log" > ~/tesis_evidencia/racey_2026-10-05.tgz`, y el equivalente con la .102 |
| Esperado | Un archivo de varios MB por vehículo, que se abre con `tar tzf` |
| Cierre | Los dos archivos en `~/tesis_evidencia/` |

### 1.6 · Nivelar los dos vehículos (tarde)

| | |
|---|---|
| Qué | Copiar a `~/tesis/` de los dos lo corregido en la §1.2 (`corrida_nav2.py`, `correr_corrida_nav2.sh`, `lanzar_bag.inc`), los mapas y el catálogo de los pisos 3 y 4, y el mapa corregido del piso 2 |
| Comando | `bash herramientas/nivelar_carros.sh --copiar`. Compara 21 archivos de `~/tesis/` con el md5 del repositorio, copia los que falten o difieran y vuelve a comparar. Informa además del parche de rf2o y de la partición instalada en `/etc` |
| Comprobación | `Los vehiculos estan nivelados con el repositorio.` Si avisa de la partición en `/etc`, se reinstala con el procedimiento del bloque A ([`DISENO_AISLAMIENTO_DOS_CARROS.md`](DISENO_AISLAMIENTO_DOS_CARROS.md)), no copiándola a mano |
| Si falla | Si un vehículo no responde, queda anotado y se cierra en cuanto vuelva a la red |
| Cierre | Ningún archivo distinto del repositorio en ninguno de los dos |

---

## 2. Martes 6

Si el lunes la IMU no respondió, este día se salta la §2.1 a §2.3 y se adelanta el jueves.

### 2.1 · El controlador de la IMU en los dos vehículos

| | |
|---|---|
| Objetivo | Que cada vehículo publique `sensor_msgs/Imu` con el BMI160 |
| Pasos | (1) En el portátil, `git clone https://github.com/larsll/larsll-deepracer-imu-pkg` y revisar que el paquete compile en Jazzy (es Python, escrito para Foxy). (2) Copiarlo a `~/nav_ws/src/` de los dos. (3) Instalar `smbus2` y `BMI160-i2c`: si los vehículos no tienen internet, descargarlos en el portátil con `pip download smbus2 BMI160-i2c -d ~/ruedas` y copiarlos. (4) Compilar con `colcon build --packages-select imu_pkg` |
| Esperado | El nodo publica a 25 Hz o más (`ros2 topic hz` sobre su tópico, con el perfil de la partición) |
| Si falla | Si el paquete no compila o el sensor no responde en 2 h, la IMU pasa a trabajos futuros |
| Cierre | Las lecturas llegan en los dos vehículos |

### 2.2 · Orientación de los ejes y calibración

| Prueba | Cómo | Esperado |
|---|---|---|
| Gravedad | Vehículo quieto en el suelo, 10 s de lecturas | El eje vertical marca unos +9,8 m/s² |
| Sentido del giro | Girar el vehículo a mano 90° a la izquierda | La velocidad de giro en z sale positiva (convención de ROS) |
| Sesgo del giroscopio | Vehículo quieto 60 s | Anotar la media de la velocidad de giro en z; es el valor a restar |

Con esto se añade a `deepracer_hardware.urdf` el marco `imu_link` con la posición y la orientación
del sensor, medidas sobre el vehículo.

### 2.3 · Combinar la IMU con rf2o (EKF)

| | |
|---|---|
| Objetivo | Que la odometría del vehículo use el giroscopio para el rumbo y rf2o para el avance |
| Cómo | `robot_localization` (paquete `ros-jazzy-robot-localization`) con un filtro EKF: de rf2o toma la posición y el rumbo como diferencias; de la IMU, la velocidad de giro en z. rf2o deja de publicar la transformada `odom → base_link` y la publica el filtro. Va en `nav2_hardware.launch.py` con el argumento `imu:=true`, para poder correr con IMU y sin ella |
| Esperado | Con el vehículo quieto, `odom → base_link` no deriva más de 1 cm ni 1° en 60 s |
| Si falla | Se corre sin IMU (`imu:=false`), como hasta ahora |
| Cierre | Los dos vehículos arrancan Nav2 con `imu:=true` |

### 2.4 · Red entre los pisos 3 y 4 (Jonny)

| | |
|---|---|
| Montaje | Repetidores en modo punto de acceso, con cable al router; mismo nombre de red y contraseña; DHCP apagado en los repetidores; canales 1, 6 y 11 |
| Prueba | El procedimiento de RF-15 de [`HOJA_CAMPO_SEGUNDO_DEEPRACER.md`](HOJA_CAMPO_SEGUNDO_DEEPRACER.md), con un vehículo en cada piso, en los puntos de salida |
| Esperado | `CUMPLE` del medidor, y los dos vehículos responden al ping desde cualquier punto de su pasillo |
| Si falla | Acercar o mover los repetidores; si no hay cobertura en todo el pasillo, se eligen rutas dentro de la cobertura |
| Cierre | `CUMPLE` con los vehículos en pisos distintos |

---

## 3. Miércoles 7

### 3.1 · Radio de giro de los dos vehículos

| | |
|---|---|
| Objetivo | Darle al planificador el radio de giro real (hoy supone 0,35 m) |
| Cómo | Con el control manual de la consola web del vehículo, dirección a tope y avance lento hasta cerrar un círculo; marcar el centro de las ruedas traseras en dos puntos opuestos y medir el diámetro. Se mide girando a la izquierda y a la derecha, en cada vehículo |
| Después | Poner el mayor de los radios en `minimum_turning_radius` de `nav2_params_jazzy.yaml` |
| Cierre | Cuatro medidas anotadas y el valor en el YAML |

### 3.2 · Misiones encadenadas en el piso 4, sin tocar el vehículo

El vehículo sale una vez de la salida medida y recorre tres tramos seguidos hacia el norte, sin media
vuelta. Entre un tramo y el siguiente nadie lo toca ni le vuelve a dar la pose inicial. Así se mide
lo mismo que el 2-oct (avance y llegada), y además si el error se acumula de una misión a la
siguiente.

| Tramo | De | A | Distancia |
|---|---|---|---|
| 1 | Salida frente a las escaleras (24,45, 1,21) | Salón 403 (17,22, 2,06) | 7,23 m |
| 2 | Llegada del tramo 1 | Salón 402 (9,31, 2,15) | 7,91 m |
| 3 | Llegada del tramo 2 | Salón 401 (6,20, 2,03) | 3,11 m |

| Paso | Qué | Comando o acción | Esperado | Cierre |
|---|---|---|---|---|
| 1 | Colocar el vehículo | Centro a 1,00 m de la pared sur y a 1,25 m de la pared este, mirando al norte | — | Vehículo en la salida |
| 2 | Arrancar Nav2 en racey, con IMU si quedó lista el martes | `CARRO=192.168.0.104 MAPA=/home/deepracer/tesis/piso4.yaml POSE_X=24.45 POSE_Y=1.21 POSE_YAW=3.1416 ESCALA=1.0 bash herramientas/nav2_mapa_guardado.sh   # ruta fija del vehiculo` | `Managed nodes are active` en 3 a 5 min | Nav2 activo |
| 3 | Comprobar las rutas sin mover el vehículo | `compute_path_to_pose` a los tres salones (§4.3 de [`GUIA_PISOS_3_Y_4.md`](GUIA_PISOS_3_Y_4.md)) | `SUCCEEDED` | Tres rutas |
| 4 | Tramo 1, con la pose inicial | `ssh deepracer@192.168.0.104 "sudo -n bash ~deepracer/tesis/correr_corrida_nav2.sh p4r_04 --salida 24.45 1.21 3.1416 --meta 17.22 2.06 3.1416 --mapa /home/deepracer/tesis/piso4.yaml --csv ~deepracer/campana_s26_racey.csv"` (ruta fija del vehículo) | Fila en el CSV | Marca en el piso junto al centro del vehículo; avance desde la salida y distancia a la pared oeste |
| 5 | Tramo 2, sin pose inicial | La misma orden con `p4r_05`, `--sin-pose-inicial` en lugar de `--salida` y `--meta 9.31 2.15 3.1416` | Fila en el CSV; AMCL no se reinicia | Marca nueva; avance medido de marca a marca y distancia a la pared oeste |
| 6 | Tramo 3, sin pose inicial | Igual, `p4r_06` y `--meta 6.20 2.03 3.1416` | Igual | Igual |
| 7 | La misma cadena con deepy | `CARRO=192.168.0.102`, `ESCALA=0.85`, ids `p4d_03` a `p4d_05` y `campana_s26_deepy.csv` | Igual | Igual |

Si la IMU quedó lista, cada vehículo hace la cadena dos veces: primero sin IMU y con margen de 1,0 m,
y después con IMU y margen de 0,5 m. El margen se cambia en `nav2_hardware.launch.py` (ajuste 8).

Odometría: error de 10 % o menos en los tramos de 5 m o más (tramos 1 y 2), medido de marca a
marca. G-2 ya está alcanzada; esto la confirma en misiones encadenadas. Cierre de G-3: llegada a
0,5 m o menos. Se anota además si el error de
llegada crece del tramo 1 al 3.

Punto de decisión a las 12:00. Si la IMU no mejora la llegada en las cadenas de la mañana, se quita
(`imu:=false`) y se sigue con el margen de 1,0 m. G-3 se reporta con su cifra.

### 3.3 · Media vuelta para ir a recoger a un usuario

Con el radio de giro real ya en el planificador (§3.1), el vehículo va del Salón 401, donde terminó
la cadena, a la salida frente a las escaleras. Es lo que pasa cuando el coordinador lo envía a
recoger a un usuario que está al sur. Para eso da media vuelta en el tramo ancho frente a los salones
401 y 402 (de 3,1 a 3,2 m).

| Paso | Qué | Comando o acción | Esperado | Cierre |
|---|---|---|---|---|
| 1 | Pedir la meta al sur, sin tocar el vehículo | La orden del tramo 2 con `p4r_07`, `--sin-pose-inicial` y `--meta 24.45 1.21 0.0` | Nav2 traza una maniobra con marcha atrás en el tramo ancho y vuelve hacia el sur | Una persona junto al vehículo durante la maniobra |
| 2 | Si no gira | Una meta intermedia en el tramo ancho mirando al sur: `--meta 8.00 1.70 0.0`, y después la de la escalera | El vehículo queda mirando al sur | — |
| 3 | Medir | Del centro del vehículo a la pared sur y a la pared este | Cerca de 1,00 m y 1,25 m | Número de maniobras, recuperaciones, tiempo y error de llegada anotados |

Si la media vuelta no sale ni con la meta intermedia, queda como limitación declarada de un
vehículo Ackermann en pasillos de 2,3 m. En ese caso G-5 se hace en la variante sin media vuelta
(§5.1).

### 3.4 · Una corrida en el piso 3 con deepy

Salida: frente a las escaleras y mirando al norte, con el centro del vehículo a 3,23 m de la pared sur
y a 1,26 m de la pared este. En el mapa es (22,10, 1,06). Meta: Salón 302 (9,31, 2,21). Es la primera
vez que un vehículo navega en el piso 3; sirve para comprobar el mapa antes de G-5.

---

## 4. Jueves 8

### 4.1 · El coordinador reconoce los pisos 3 y 4 (decisión del equipo)

El coordinador solo declara los niveles 1 y 2 (`robot_nivel_1` y `robot_nivel_2` en
`coordinador.py`). Con el catálogo de los pisos 3 y 4 no encuentra robot y la misión no se
planifica. Son cuatro líneas en un archivo congelado desde el 18 de septiembre: se aplica solo si el
equipo lo aprueba, y la decisión queda en la bitácora de `ESTADO.md`.

| | |
|---|---|
| Cambio | Declarar `robot_nivel_3` y `robot_nivel_4` y añadirlos a la asignación |
| Prueba | `prueba_planificador.py` y `prueba_agente.py`, más las 90 combinaciones del catálogo `puntos_interes_pisos34.yaml` con la asignación `{3: robot1, 4: robot2}` |
| Cierre | Todas las pruebas pasan y el coordinador está copiado y compilado en los dos vehículos |

### 4.2 · Coordinador, agentes e interfaz en los vehículos

| Paso | Qué | Comando | Esperado |
|---|---|---|---|
| 1 | Copiar y compilar el coordinador en los dos | `scp -r Robot/aws-deepracer/coordinacion deepracer@192.168.0.104:~/coordinacion_ws/src/` y `ssh deepracer@192.168.0.104 "source /opt/ros/jazzy/setup.bash && cd ~/coordinacion_ws && colcon build --packages-select coordinacion"`; igual con la .102 | md5 de `coordinador.py` igual en el repositorio y en los dos |
| 2 | `rosbridge` en racey | `ssh deepracer@192.168.0.104 "source /opt/ros/jazzy/setup.bash; ros2 pkg list \| grep rosbridge_server"` | `rosbridge_server` |
| 3 | Nav2 con espacio de nombres en los dos | `NS=robot1` en deepy (piso 3) y `NS=robot2` en racey (piso 4), con su mapa y su salida | `Managed nodes are active` en los dos |
| 4 | Un agente en cada vehículo, con la partición | `ros2 run coordinacion agente --ros-args -r __ns:=/robot2 -p nivel:=4` en racey y `-r __ns:=/robot1 -p nivel:=3` en deepy | `/robot1/estado` y `/robot2/estado` a 2 Hz |
| 5 | Coordinador y `rosbridge` en racey | El coordinador con `-p condicion:=hardware -p ruta_puntos:=<catálogo de los pisos 3 y 4 en el vehículo> -p robot_nivel_3:=robot1 -p robot_nivel_4:=robot2 -p ruta_registros:=~deepracer/registros`, y `ros2 launch rosbridge_server rosbridge_websocket_launch.xml send_action_goals_in_new_thread:=true` | El coordinador escribe `condicion 'hardware': la llegada se acepta a 0.5 m o menos` |
| 6 | La interfaz desde el teléfono | En el portátil, `python3 -m http.server 8000 --directory interfaz_web`; en el teléfono, conectado a la red de los vehículos, `http://<IP del portátil>:8000/?ws=192.168.0.104:9090` | La interfaz muestra los dos robots |

### 4.3 · Una misión dentro de un solo piso

| | |
|---|---|
| Qué | Desde el teléfono, una misión en el piso 4: de las escaleras al Salón 402. El vehículo sale de donde quedó, sin reubicarlo: el coordinador primero lo manda al origen («El robot va hacia… Espere allí») |
| Esperado | racey llega; la interfaz muestra el avance y el final |
| Cierre | El registro de la misión, compuesto con `componer_registro.py --banco fisico` |

---

## 5. Viernes 9

### 5.1 · G-5: misión del piso 3 al piso 4 con relevo

Cada misión empieza con el robot del origen yendo, desde donde esté, hasta el salón de origen. Si va
hacia el norte, después tiene que dar media vuelta para guiar al usuario hacia las escaleras. Por eso
hay dos variantes, y la que se corre depende del resultado del miércoles (§3.3).

| Variante | Disposición inicial | Cuándo |
|---|---|---|
| A, con regreso | deepy en su escalera del piso 3, mirando al norte; racey en su escalera del piso 4, mirando al norte | Si la media vuelta funcionó el miércoles |
| B, sin media vuelta | deepy al norte del salón de origen, mirando al sur; racey en su escalera del piso 4, mirando al norte | Si la media vuelta no funcionó |

| | |
|---|---|
| Misión | Desde el teléfono: origen el Salón 302 y destino el Salón 402 |
| Esperado | deepy va al origen y guía hasta las escaleras del piso 3; la interfaz pide subir y confirmar la llegada al piso 4; racey guía desde las escaleras del piso 4 hasta el Salón 402 |
| Segunda misión | Sin tocar los vehículos, otra misión desde el teléfono; cada robot sale de donde quedó (§6.2 del acta). En la variante B, una que no pide media vuelta: en el piso 4, del Salón 402 al Salón 401. En la variante A, la que el equipo elija con lo medido el miércoles |
| Medidas | Llegada de cada vehículo con flexómetro, desde marcas en el piso; la grabación de los dos |
| Si falla | Anotar en qué fase falló y por qué; se repite el lunes 12 |
| Cierre | Los registros de las dos misiones compuestos y validados: G-5 alcanzada |

### 5.2 · Corte semanal (noche)

`ESTADO.md` al día, entregable de S26 en `.md` y `.tex`, y commit, con la batería completa antes del
push.

---

## 6. Lo que no se hace esta semana

| Qué | Por qué |
|---|---|
| Medias vueltas fuera de los tramos anchos | Con 2,3 m de pasillo no caben con la configuración actual (2-oct) |
| Regreso automático tras una misión completada | Opcional y sin prioridad (§6.2 del acta). Entre misiones el vehículo no vuelve a su escalera |
| Navegar hacia el borde de una escalera | Se suspendió el 30-sep; las metas de las escaleras quedan centradas en el pasillo |
| La campaña de RF-27 | Necesita G-5. Va en la semana 27, con cierre de datos el viernes 16 |
| La IMU en la simulación | Solo si sobra tiempo; si no, queda como limitación declarada |

## 7. Riesgos y salidas

| Si pasa | Qué se hace |
|---|---|
| La IMU no existe o no funciona el martes | Se sigue sin ella y el martes pasa a preparar G-5 |
| La red no cubre los dos pisos | Rutas dentro de la cobertura; el coordinador sigue en racey |
| La media vuelta no sale ni con la meta intermedia | G-5 en la variante B; el regreso automático queda como limitación declarada |
| G-5 no sale el viernes | Se repite el lunes 12. Si tampoco sale, el cronograma prevé bajar a un vehículo real y uno simulado (sección 9 de [`CRONOGRAMA_S17_S32.md`](CRONOGRAMA_S17_S32.md)) |
| Un vehículo se queda sin batería | Cargar las dos baterías (cómputo y tracción) cada noche; llevar el cargador a la sesión |
