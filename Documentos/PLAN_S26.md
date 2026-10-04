# Plan de la semana 26 (5 al 9 de octubre)

La meta de la semana es llegar al viernes con la misión con relevo entre los pisos 3 y 4 sobre los
dos vehículos (compuerta G-5). La toma de datos se cierra el viernes 16, en el corte C-3 del
[acta](ACTA_GO_NOGO.md). Para llegar hay que dejar los vehículos estables (carga, escala, cámaras),
cerrar G-2 y G-3 y, si la tarjeta la tiene, integrar la IMU. Lo que se hizo la semana anterior está
en [`Entregable_semana_25.md`](Entregables/Entregable_semana_25.md).

Vehículos: `amss-ez9n` (deepy, 192.168.0.102) va en el piso 3 como `robot1`; `amss-jgm9` (racey,
192.168.0.104) va en el piso 4 como `robot2` y lleva el coordinador. Todas las órdenes se lanzan
desde la raíz del repositorio en el portátil.

## 0. La semana de un vistazo

| Día | Qué se hace | Quién | Vehículos | Al terminar el día |
|---|---|---|---|---|
| Lun 5, mañana | Acta: cambio de sitio y corte C-1. Correcciones de las herramientas de campo | Santiago y Claude | no | Acta al día; herramientas corregidas y probadas en simulación |
| Lun 5, tarde | Cámaras fuera, comprobar la IMU, copiar grabaciones, nivelar los dos vehículos | Santiago y Jonny | los dos | Se sabe si hay IMU; vehículos nivelados |
| Mar 6 | IMU funcionando y combinada con rf2o (si existe). Red entre los pisos 3 y 4 | Santiago y Claude; Jonny la red | los dos | La IMU publica en los dos vehículos; la red llega a los dos pisos |
| Mié 7 | Radio de giro. Corridas medidas en el piso 4 (y en el piso 3): cerrar G-2 y evaluar G-3 | Santiago y Jonny | uno cada vez | G-2 cerrada; G-3 evaluada con y sin IMU |
| Jue 8 | Coordinador en el vehículo, agentes en los dos, interfaz desde el teléfono; una misión en un solo piso | los dos | los dos | Misión en un piso pedida desde el teléfono, con registro |
| Vie 9 | G-5: misión del piso 3 al piso 4 con relevo. Corte semanal en la noche | los dos | los dos | G-5 intentada con registro; entregable de S26 |

Reglas de toda la semana:

- Los dos vehículos se tocan a la vez: lo que se instale en uno se instala en el otro el mismo día.
- No se navega hacia el borde de una escalera ni se pide una media vuelta a Nav2.
- Cada llegada se mide con flexómetro antes de tocar el vehículo.
- Las grabaciones y registros se copian al portátil, a `~/tesis_evidencia/`, al terminar cada corrida.

---

## 1. Lunes 5

### 1.1 · Acta: cambio de sitio y corte C-1 (mañana, Santiago con los directores)

| | |
|---|---|
| Objetivo | Dejar escrito qué pasa con el corte C-1 del 2 de octubre, en el que G-2 cumplió su criterio y G-3 no |
| Qué preguntar | (1) ¿El cambio de sitio a los pisos 3 y 4 movió la fecha de C-1? (2) Si la movió, ¿a cuándo? (3) Si no, ¿se aplica el NO-GO que prevé el acta? |
| Después | Claude redacta la entrada en la sección 6.1 del acta con lo acordado, el sitio nuevo y las cifras de G-2 (+3,3 % y −4,6 %) y G-3 (0,57 m y 0,62 m) |
| Cierre | Commit con el acta actualizada |

Si la respuesta es NO-GO, el resto de la semana cambia: la demostración física queda como pruebas
atómicas y el trabajo pasa al análisis y a la presentación. En ese caso se para aquí y se replanifica.

### 1.2 · Correcciones de las herramientas de campo (mañana, Claude)

| Tarea | Qué se corrige | Por qué |
|---|---|---|
| a | `corrida_nav2.py` publica velocidad cero antes de cerrar cuando se interrumpe | El 30-sep, al interrumpir una corrida, la orden de parada no salió (`publisher's context is invalid`) |
| b | `corrida_nav2.py` espera la confirmación de la meta como mucho 30 s | El 30-sep y el 2-oct la corrida se quedó esperando 10 min |
| c | `corrida_nav2.py` guarda la pose de AMCL en el instante en que Nav2 termina, antes de refrescarla | El 30-sep el refresco hizo saltar la pose 7,5 m y el informe dio una llegada falsa |
| d | `corrida_nav2.py` deja de imprimir «tolerancia de Nav2: 0,25» | Es un texto fijo; el margen real es 1,0 m |
| e | `lanzar_bag.inc` cierra el grabador con una interrupción y espera 10 s antes de matarlo | Con `SIGKILL` se pierde el final de la grabación (2-oct) |
| f | `nav2_mapa_guardado.sh` admite `ESCALA` (por defecto 0,9) y apaga `camera_node` y `sensor_fusion_node` antes de Nav2 | Con 0,9 racey no arranca y deepy va a 1,58 m/s; con la cámara y la fusión encendidas Nav2 se cayó (2-oct) |

Prueba de cierre: el ensayo en simulación de la §9 de
[`GUIA_CAMPANA_NAV2_HARDWARE.md`](GUIA_CAMPANA_NAV2_HARDWARE.md), interrumpiendo una corrida a la
mitad. Esperado: el vehículo simulado se detiene y la grabación se abre completa. Si falla, no se
copian las herramientas a los vehículos y se corre con las de la semana pasada.

### 1.3 · Desconectar las cámaras (tarde, en los dos vehículos)

| | |
|---|---|
| Acción | Retirar las dos cámaras de los puertos USB de cada vehículo |
| Comprobación | `ssh deepracer@192.168.0.102 "ls /dev/video* 2>&1"`, y lo mismo con la .104 |
| Esperado | `No such file or directory` en los dos |
| Si falla | Si sigue apareciendo un `/dev/video`, hay otra cámara conectada: revisar los puertos |
| Cierre | Ningún `/dev/video` en los dos vehículos |

### 1.4 · Comprobar la IMU (tarde, en los dos vehículos)

La documentación de AWS dice que la tarjeta trae acelerómetro y giroscopio; el paquete de la
comunidad lo lee como un Bosch BMI160 en el bus I2C 1, dirección 0x68. La orden lee el registro 0 del
sensor, que en el BMI160 vale `0xd1`, sin instalar nada en el vehículo.

| | |
|---|---|
| Comando | `ssh deepracer@192.168.0.102 "ls /dev/i2c-*; sudo -n python3 -c \"import fcntl,os; f=os.open('/dev/i2c-1',os.O_RDWR); fcntl.ioctl(f,0x0703,0x68); os.write(f,bytes([0])); print(hex(os.read(f,1)[0]))\""` |
| Esperado | La lista de buses incluye `/dev/i2c-1`, y la segunda línea dice `0xd1` |
| Si falla | Si dice `Device or resource busy`, otro programa usa el bus: repetir con `0x0706` en lugar de `0x0703`. Probar también la dirección `0x69` y los otros buses de la lista. Si ninguno responde `0xd1`, la tarjeta no tiene ese sensor accesible: la IMU pasa a trabajos futuros y el martes se dedica a G-5 |
| Cierre | `0xd1` en los dos vehículos, con el bus y la dirección anotados |

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
| Qué | Copiar a `~/tesis/` de los dos lo corregido en la §1.2 (`corrida_nav2.py`, `correr_corrida_nav2.sh`, `lanzar_bag.inc`), el mapa corregido del piso 2 y los archivos de partición del repositorio |
| Comprobación | El md5 de cada archivo de `~/tesis/` igual al del repositorio, en los dos |
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

### 3.2 · Corridas del piso 4 para G-2 y G-3

Salida (la misma del 2-oct): el centro del vehículo a 1,00 m de la pared sur y a 1,25 m de la pared
este, mirando al norte.

| Paso | Qué | Comando o acción | Esperado | Cierre |
|---|---|---|---|---|
| 1 | Arrancar Nav2 en racey, con IMU si quedó lista el martes | `CARRO=192.168.0.104 MAPA=/home/deepracer/tesis/piso4.yaml POSE_X=24.45 POSE_Y=1.21 POSE_YAW=3.1416 ESCALA=1.0 bash herramientas/nav2_mapa_guardado.sh   # ruta fija del vehiculo` | `Managed nodes are active` en 3 a 5 min | Nav2 activo |
| 2 | Comprobar la ruta sin mover el vehículo | `compute_path_to_pose` a cada meta (§4.3 de [`GUIA_PISOS_3_Y_4.md`](GUIA_PISOS_3_Y_4.md)) | `SUCCEEDED` | Rutas a los salones 403, 402 y 401 |
| 3 | Tres corridas | `ssh deepracer@192.168.0.104 "sudo -n bash ~deepracer/tesis/correr_corrida_nav2.sh p4r_04 --salida 24.45 1.21 3.1416 --meta 9.31 2.15 3.1416 --mapa /home/deepracer/tesis/piso4.yaml --csv ~deepracer/campana_p4_racey.csv"` (ruta fija del vehículo), y `p4r_05`, `p4r_06` | Una fila en el CSV por corrida | Las tres medidas: avance (desde la pared sur, menos 1,00 m) y distancia a la pared oeste |
| 4 | Lo mismo con deepy, ids `p4d_03` a `p4d_05` | Con `CARRO=192.168.0.102`, `ESCALA=0.85` y su CSV | Igual | Igual |

Si la IMU quedó lista, cada vehículo corre primero sin IMU y con margen de 1,0 m, y después con IMU y
margen de 0,5 m, para poder compararlos. El margen se cambia en `nav2_hardware.launch.py` (ajuste 8).

Cierre de G-2: error de rf2o, o del filtro con IMU, de 10 % o menos en todas las corridas medidas.
Cierre de G-3: llegada a 0,5 m o menos, medida con flexómetro.

Punto de decisión a las 12:00. Si la IMU no mejora la llegada en las corridas de la mañana, se quita
(`imu:=false`) y se sigue con el margen de 1,0 m. G-3 se reporta con su cifra.

### 3.3 · Una corrida en el piso 3 con deepy

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
| Qué | Desde el teléfono, una misión en el piso 4: de las escaleras al Salón 402 |
| Esperado | racey llega; la interfaz muestra el avance y el final |
| Cierre | El registro de la misión, compuesto con `componer_registro.py --banco fisico` |

---

## 5. Viernes 9

### 5.1 · G-5: misión del piso 3 al piso 4 con relevo

| | |
|---|---|
| Disposición | deepy en el piso 3, junto al salón de origen y mirando hacia las escaleras (al sur). racey en el piso 4, en la salida frente a las escaleras y mirando al norte |
| Misión | Desde el teléfono: origen un salón del piso 3 (por ejemplo, el 302) y destino un salón del piso 4 (por ejemplo, el 402) |
| Esperado | deepy guía hasta las escaleras del piso 3; la interfaz pide subir y confirmar la llegada al piso 4; racey guía desde las escaleras del piso 4 hasta el destino |
| Medidas | Llegada de cada vehículo con flexómetro; la grabación de los dos |
| Si falla | Anotar en qué fase falló y por qué; se repite el lunes 12 |
| Cierre | El registro de la misión compuesto y validado: G-5 alcanzada |

### 5.2 · Corte semanal (noche)

`ESTADO.md` al día, entregable de S26 en `.md` y `.tex`, y commit, con la batería completa antes del
push.

---

## 6. Lo que no se hace esta semana

| Qué | Por qué |
|---|---|
| Medias vueltas con Nav2 | No caben en estos pasillos con la configuración actual (2-oct). Los vehículos se colocan mirando hacia su destino |
| Navegar hacia el borde de una escalera | Se suspendió el 30-sep; las metas de las escaleras quedan centradas en el pasillo |
| La campaña de RF-27 | Necesita G-5. Va en la semana 27, con cierre de datos el viernes 16 |
| La IMU en la simulación | Solo si sobra tiempo; si no, queda como limitación declarada |

## 7. Riesgos y salidas

| Si pasa | Qué se hace |
|---|---|
| El corte C-1 se mantiene y se declara NO-GO | Se para la demostración física y se replanifica hacia el análisis y la presentación (§1.1) |
| La IMU no existe o no funciona el martes | Se sigue sin ella y el martes pasa a preparar G-5 |
| La red no cubre los dos pisos | Rutas dentro de la cobertura; el coordinador sigue en racey |
| G-5 no sale el viernes | Se repite el lunes 12. Si tampoco sale, el cronograma prevé bajar a un vehículo real y uno simulado (sección 9 de [`CRONOGRAMA_S17_S32.md`](CRONOGRAMA_S17_S32.md)) |
| Un vehículo se queda sin batería | Cargar las dos baterías (cómputo y tracción) cada noche; llevar el cargador a la sesión |
