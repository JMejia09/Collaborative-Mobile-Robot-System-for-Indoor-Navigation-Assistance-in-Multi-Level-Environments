#!/bin/bash
# Mapea conduciendo: el vehiculo avanza una distancia y construye el mapa a la vez.
#
# USO (en el VEHICULO, y como root — ver abajo por que)
#     mapear_conduciendo.sh <metros> [m/s] [tope_segundos] [escala]
#
#     metros          distancia objetivo, medida contra la odometria de rf2o
#     m/s             velocidad mandada. Por defecto 0,5. Hasta el 2026-09-29 lo que
#                     quedaba por debajo de 0,40 salia como throttle CERO; desde
#                     entonces el puente lo sube a su escalon mas bajo, el mismo
#                     que da 0,5. Pedir menos no hace ir mas despacio
#     escala          max_speed_pct del puente (0,68 de fabrica). El 2026-09-29, en
#                     amss-jgm9, con 0,80 (throttle 0,5185) solo sono; con 0,90
#                     (throttle 0,6327) avanzo 2,9 m. Si no se da, se deja la que
#                     tenga el puente
#     tope_segundos   corte duro. A la velocidad real medida el 2026-09-24
#                     (0,15 a 0,26 m/s) seis metros tardan entre 25 y 45 s
#
# ANTES DE CORRER ESTO hay que haber copiado al vehiculo, EN EL MISMO
# DIRECTORIO que este guion, otros tres ficheros:
#     avanzar_y_detener.py   lanzar_bag.inc   slam_toolbox_carro.yaml
# Y ese directorio NO puede ser /tmp, que se vacia al reiniciar —el vehiculo
# reinicio solo en mitad de la sesion del 2026-09-24 y se llevo los guiones—.
# El guion de campo detalla la copia.
#
# POR QUE A BORDO Y NO SOBRE UN BAG
# ---------------------------------
# La via offline -grabar y levantar el mapa en el portatil con
# 'mapear_desde_bag.sh'- esta probada y es la que hay que preferir cuando el
# mapa se necesita en el escritorio. Aqui no sirve: el mapa hace falta EN EL
# VEHICULO para que Nav2 lo use acto seguido, y el portatil no puede
# mandarselo. Humble y Jazzy se descubren pero no intercambian datos: el
# 2026-09-24 el portatil listaba los topicos del carro y 'ros2 topic echo' no
# recibia un solo mensaje.
#
# Se graba el bag igualmente, con '/map' incluido, para poder rehacer el mapa
# despues sin volver al sitio.
#
# TODO CORRE COMO ROOT, Y NO ES OPCIONAL
# --------------------------------------
# 'deepracer-core.service' declara User=root, asi que 'rplidar_node' publica
# como root y 'servo_pkg' escucha como root. Los segmentos de memoria
# compartida de Fast DDS son de root con permisos 0644: un proceso que corra
# como 'deepracer' DESCUBRE pero no recibe, y no da ningun error —se queda
# esperando—. Medido el 2026-09-22 y confirmado el 2026-09-24.
#
# LA CADENA
#   rplidar_node (deepracer-core)  --> /rplidar_ros/scan
#   static_transform_publisher     --> TF base_link -> laser
#   rf2o_laser_odometry            --> /odom y TF odom -> base_link
#   sync_slam_toolbox_node         --> /map y TF map -> odom
#   cmdvel_to_servo_node           --> /cmd_vel a /ctrl_pkg/servo_msg
#   avanzar_y_detener.py           --> conduce y mide
#   extraer_mapa.py                --> mapa.pgm + mapa.yaml, desde el bag

# Sin 'set -u': los setup.bash de ROS leen variables no definidas y abortarian.
AQUI="$(cd "$(dirname "$0")" && pwd)"

# Particion del vehiculo (Documentos/DISENO_AISLAMIENTO_DOS_CARROS.md). Si esta
# instalada, este proceso TIENE que cargarla: sin ella no ve /rplidar_ros/scan ni
# /tf ni llega a los servos, y no da ningun error. Si no esta instalada -antes de
# aplicar el diseno, o en el portatil-, esto no hace nada.
[ -f /etc/deepracer-tesis/particion.xml ] && export FASTRTPS_DEFAULT_PROFILES_FILE=/etc/deepracer-tesis/particion.xml
source /opt/ros/jazzy/setup.bash
source /opt/aws/deepracer/lib/setup.bash
source ~deepracer/coordinacion_ws/install/setup.bash
source ~deepracer/nav_ws/install/setup.bash
source "$AQUI/lanzar_bag.inc"

METROS="${1:-6.0}"
VELOCIDAD="${2:-0.5}"
TOPE="${3:-90}"
ESCALA="${4:-}"
SALIDA=~deepracer/mapeo_$(date +%H%M%S)

mkdir -p "$SALIDA"

limpiar() {
    pkill -9 -f rf2o_laser_odometry 2>/dev/null
    pkill -9 -f static_transform_publisher 2>/dev/null
    pkill -9 -f sync_slam_toolbox_node 2>/dev/null
    sleep 1
}
trap limpiar EXIT

echo "== limpiando restos =="
limpiar

# Sin barridos no hay odometria, ni mapa, ni parada por laser: mas vale no
# arrancar. Lo publica 'deepracer-core', pero una corrida anterior pudo
# dejarlo tocado.
echo "== comprobando el LiDAR =="
# Con el tipo explicito: sin el, 'ros2 topic echo' sale al instante con «Could not
# determine the type» si el descubrimiento aun no encontro el topico -recien
# encendidos los carros, con los dos en la red-, sin esperar al 'timeout'. Paso el
# 2026-09-29 con el LiDAR publicando a 7,6 Hz.
# Se juzga por la salida y no por el codigo de retorno: con la red cargada el
# 'echo' recibe el barrido pero tarda en cerrarse, el 'timeout' lo corta y el
# codigo es 124 aunque el LiDAR este bien. Paso el 2026-09-29 en amss-ez9n. El
# '---' lo imprime 'ros2 topic echo' al final de cada mensaje recibido.
timeout 15 ros2 topic echo /rplidar_ros/scan sensor_msgs/msg/LaserScan \
    --field header.frame_id --qos-reliability best_effort --once > /tmp/frame.txt 2>&1
if ! grep -q '^---$' /tmp/frame.txt; then
    echo "ABORTA: /rplidar_ros/scan no publica. Revisa deepracer-core."
    cat /tmp/frame.txt
    exit 5
fi
echo "   frame del barrido: $(head -1 /tmp/frame.txt)"

cat > /tmp/rf2o.yaml <<'YAML'
/**:
  ros__parameters:
    laser_scan_topic: /rplidar_ros/scan
    odom_topic: /odom
    publish_tf: true
    base_frame_id: base_link
    odom_frame_id: odom
    init_pose_from_topic: ''
    freq: 20.0
    use_sim_time: false
YAML

# base_link -> laser compuesto del vehiculo real: el URDF cuelga el sensor de
# 'chassis', no de 'base_link', y hay que componer los dos saltos.
#   base_link -> chassis  z = 0,023249
#   chassis   -> laser    xyz = 0,02913  0  0,16145   rpy = 0 0 3,1416
# Compuesto da x = 0,02913, z = 0,184699, yaw = pi. yaw = pi en cuaternio es
# (x,y,z,w) = (0,0,1,0). Copiar el 0,16145 del xacro sin componer el chassis
# deja el sensor 23 mm bajo, y olvidar el yaw construye el mapa 180 grados
# girado respecto al que AMCL vera despues: el emparejamiento no cerraria y
# nada diria por que.
echo "== TF del sensor, rf2o y slam_toolbox =="
nohup ros2 run tf2_ros static_transform_publisher \
    --x 0.02913 --y 0 --z 0.184699 --qx 0 --qy 0 --qz 1 --qw 0 \
    --frame-id base_link --child-frame-id laser > "$SALIDA/tf.log" 2>&1 &
nohup ros2 run rf2o_laser_odometry rf2o_laser_odometry_node \
    --ros-args --params-file /tmp/rf2o.yaml > "$SALIDA/rf2o.log" 2>&1 &
sleep 5
nohup ros2 run slam_toolbox sync_slam_toolbox_node \
    --ros-args --params-file "$AQUI/slam_toolbox_carro.yaml" > "$SALIDA/slam.log" 2>&1 &
sleep 8

# EN JAZZY slam_toolbox ES UN NODO DE CICLO DE VIDA y nace 'unconfigured': no
# publica /map, no construye nada, y su log se queda en una sola linea. No da
# ningun error. En Humble no lo es, y por eso 'mapear_desde_bag.sh' funciona en
# el portatil sin hacer nada de esto. Ya estaba anotado en GUION_NAV2_HARDWARE
# §3; costo una corrida entera de mapeo el 2026-09-24 por no haberlo leido.
echo "== activando slam_toolbox (ciclo de vida) =="
# Con reintentos: 'ros2 lifecycle set' falla al instante («Node not found») si el
# descubrimiento aun no encontro el nodo, y con los dos carros encendidos tarda
# mas. Paso el 2026-09-29: el nodo vivo y el estado en 'unconfigured'. Hasta 30 s
# por paso.
for paso in configure activate; do
    for intento in 1 2 3 4 5 6 7 8 9 10; do
        ESTADO_SLAM="$(ros2 lifecycle get /slam_toolbox 2>&1 | head -1)"
        case "$paso:$ESTADO_SLAM" in
            configure:inactive*|configure:active*|activate:active*) break ;;
        esac
        ros2 lifecycle set /slam_toolbox $paso > /dev/null 2>&1
        sleep 3
    done
done
ESTADO_SLAM="$(ros2 lifecycle get /slam_toolbox 2>&1 | head -1)"
echo "   estado: $ESTADO_SLAM"
case "$ESTADO_SLAM" in
    active*) ;;
    *) echo "ABORTA: slam_toolbox no quedo activo, no habria mapa que guardar."
       echo "        El vehiculo no se ha movido."
       exit 4 ;;
esac

# Este nodo no lo arranca nadie: no es parte de deepracer-core. Y si el
# vehiculo reinicia, desaparece. Sin el no hay '/cmd_vel' que valga.
if ! ps -eo args | grep -q '[c]mdvel_to_servo_pkg/cmdvel_to_servo_node'; then
    echo "== arrancando cmdvel_to_servo_node =="
    nohup ros2 run cmdvel_to_servo_pkg cmdvel_to_servo_node \
        > /tmp/cmdvel.log 2>&1 &
    sleep 6
fi

if [ -n "$ESCALA" ]; then
    echo "== escala de velocidad: $ESCALA =="
    # La peticion puede llegar aunque la respuesta no vuelva: el 2026-09-29, en
    # amss-ez9n, el puente registro 'Incoming request: max_speed_pct: 0.8' tres veces
    # y el cliente no recibio ninguna respuesta. Por eso vale como confirmacion la
    # ultima peticion que el puente escribio en su log. Se compara como numero: el
    # puente escribe el float32, y 0,90 sale 0.8999...
    escala_en_log() {
        local u
        u="$(grep -o 'Incoming request: max_speed_pct: [0-9.]*' /tmp/cmdvel.log 2>/dev/null | tail -1 | awk '{print $NF}')"
        [ -n "$u" ] && awk -v u="$u" -v e="$ESCALA" 'BEGIN { exit !((u - e) ^ 2 < 1e-6) }'
    }
    # Con reintentos: recien arrancado el puente, con la red cargada, el servicio
    # tardo mas de 30 s en descubrirse y la llamada murio con «rcl node's context
    # is invalid» (amss-jgm9, 2026-09-29). El log se mira antes de cada intento
    # para no agotarlos cuando la escala ya esta puesta.
    R=""
    for intento in 1 2 3 4; do
        if escala_en_log; then
            R="error=0 (confirmado en /tmp/cmdvel.log)"
            break
        fi
        R="$(timeout 20 ros2 service call /set_max_speed deepracer_interfaces_pkg/srv/NavThrottleSrv "{throttle: $ESCALA}" 2>&1 | tail -1)"
        case "$R" in *error=0*) break ;; esac
        echo "   intento $intento: el puente aun no responde"
    done
    case "$R" in
        *error=0*) ;;
        *) escala_en_log && R="error=0 (confirmado en /tmp/cmdvel.log; la respuesta no llego)" ;;
    esac
    echo "   $R"
    case "$R" in
        *error=0*) ;;
        *) echo "ABORTA: no se pudo fijar la escala. El vehiculo no se ha movido."; exit 6 ;;
    esac
fi

echo "== grabando bag =="
arrancar_bag "$SALIDA/bag" /rplidar_ros/scan /odom /map

echo "== conduciendo $METROS m =="
python3 "$AQUI/avanzar_y_detener.py" "$METROS" "$VELOCIDAD" "$TOPE"
ESTADO=$?

echo "== dejando cerrar el ultimo barrido =="
sleep 8

cerrar_bag

# NO se usa 'map_saver_cli'. Se rinde a los 2 s -su plazo por defecto- y
# slam_toolbox deja de publicar /map en cuanto el vehiculo se detiene, asi que
# el guardado falla con 'Failed to spin map subscription' aunque el mapa este
# perfectamente construido. Paso el 2026-09-24 con una corrida de 6 m ya hecha.
# El mapa se saca del bag, que ademas lo hace repetible sin volver al sitio.
echo "== extrayendo el mapa del bag =="
python3 "$AQUI/extraer_mapa.py" "$SALIDA/bag" "$SALIDA/mapa"

chown -R deepracer:deepracer "$SALIDA" 2>/dev/null

echo "== resultado en $SALIDA =="
ls -la "$SALIDA"

exit $ESTADO
