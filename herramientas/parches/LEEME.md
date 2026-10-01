# Parches a paquetes de terceros

## `rf2o_esperar_tf_laser.patch`

Parche a `rf2o_laser_odometry` ([MAPIRlab](https://github.com/MAPIRlab/rf2o_laser_odometry), commit
`b38c68e`), en `src/CLaserOdometry2DNode.cpp`.

rf2o lee la transformada `base_link → laser` una sola vez, con el primer barrido. Si en ese momento
la transformada no está publicada, sigue con una transformada vacía. En el DeepRacer el láser va
montado a 180°, así que con la transformada vacía la odometría sale invertida: el vehículo avanza y
`/odom` dice que retrocede. Pasó el 29 de septiembre en los dos vehículos. El 30 volvió a pasar en
`amss-jgm9`, con la tarjeta cargada, aun con el arranque de rf2o retrasado 8 s (ajuste 7 de
`nav2_hardware.launch.py`). Con el parche, rf2o descarta los barridos hasta que la transformada
existe y solo entonces se inicializa.

Evidencia: [`S25_pasillo_piso2_amss-jgm9.md`](../../Documentos/Evidencia/S25_pasillo_piso2_amss-jgm9.md) §2.

| Fuente `CLaserOdometry2DNode.cpp` | md5 (12 primeros) |
|---|---|
| Original | `83ccf806ee13` |
| Con el parche | `06cbdbe6c275` |

### Instalarlo en un vehículo

Cambiar la IP y el nombre por los del vehículo (`192.168.0.102` y `amss-ez9n`, o `192.168.0.104` y
`amss-jgm9`). Las órdenes se lanzan desde la raíz del repositorio, con el fuente parcheado del
portátil en `~/deepracer_sim_ws/src/rf2o_laser_odometry`.

1. Copiar el fuente, solo si el del vehículo es el original o ya tiene el parche:

   ```bash
   ssh deepracer@192.168.0.102 'test "$(hostname)" = amss-ez9n || exit 9; S=~/nav_ws/src/rf2o_laser_odometry/src/CLaserOdometry2DNode.cpp; case "$(md5sum $S | cut -c1-12)" in 83ccf806ee13|06cbdbe6c275) cat > $S; md5sum $S | cut -c1-12;; *) echo "FUENTE DISTINTA, no se toca"; exit 8;; esac' < ~/deepracer_sim_ws/src/rf2o_laser_odometry/src/CLaserOdometry2DNode.cpp
   ```

   Esperado: `06cbdbe6c275`. Si dice `FUENTE DISTINTA`, comparar a mano antes de seguir.

2. Compilar con Nav2 detenido (`CARRO=… bash herramientas/nav2_mapa_guardado.sh --parar`). `colcon
   build` puede dar el paquete por compilado sin recompilar, así que se compila en el directorio de
   construcción:

   ```bash
   ssh deepracer@192.168.0.102 'source /opt/ros/jazzy/setup.bash; cd ~/nav_ws/build/rf2o_laser_odometry && touch ~/nav_ws/src/rf2o_laser_odometry/src/CLaserOdometry2DNode.cpp && cmake --build . 2>&1 | tail -2 && cmp rf2o_laser_odometry_node ~/nav_ws/install/rf2o_laser_odometry/lib/rf2o_laser_odometry/rf2o_laser_odometry_node && echo "install = build"'
   ```

   Esperado: `Built target rf2o_laser_odometry` e `install = build` (el ejecutable de `install/` es
   un enlace al de `build/`), en unos 2 min.

3. Cierre: al arrancar Nav2, `/tmp/nav2_campo/launch.log` muestra
   `Laser odom [x,y,yaw]=[0.029130 0.000000 -3.141585]` en la primera línea de rf2o (el láser a
   2,9 cm del centro y girado 180°). Puede aparecer antes algún `"base_link" passed to
   lookupTransform`: con el parche solo indica que ese barrido se descartó y se reintenta con el
   siguiente.
