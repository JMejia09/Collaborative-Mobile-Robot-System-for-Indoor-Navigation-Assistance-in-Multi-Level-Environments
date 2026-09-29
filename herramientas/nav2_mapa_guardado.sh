#!/usr/bin/env bash
# Levanta Nav2 sobre un MAPA GUARDADO en el vehiculo y lo deja listo para navegar.
#
# POR QUE EXISTE Y POR QUE EL ORDEN IMPORTA
# -----------------------------------------
# Los costmaps de Nav2 leen /map **al configurarse**. Si map_server no esta
# ACTIVO en ese instante, la capa estatica queda vacia y el planificador aborta
# con "Start occupied" en CUALQUIER meta, apuntando al punto de partida en vez
# de a la causa. Costo la noche del 2026-09-24 encontrarlo. Ver el §3.1 de
# Documentos/GUION_NAVEGACION_USTA.md.
#
# El orden que este guion impone, y que no es negociable:
#   1. puente cmdvel_to_servo   (el launch NO lo arranca; sin el, Nav2
#                                planifica y el carro no se mueve, sin error)
#   2. set_max_speed 0.9        (con 0.68 de fabrica, linear.x 0.50 sale a
#                                throttle 0.4247 y el carro no arranca)
#   3. map_server + ACTIVAR     (antes del paso 5, o el paso 5 no sirve)
#   4. amcl + ACTIVAR + pose
#   5. el launch con slam:=false nav:=true
#
# TRES PARAMETROS QUE HAY QUE SOBREESCRIBIR
# -----------------------------------------
# El bloque amcl de nav2_params_jazzy.yaml se conserva -lo dice su propio
# comentario- solo para que la prueba de no divergencia compare los dos
# archivos enteros, asi que trae valores de simulacion:
#   use_sim_time  True -> false            (no hay /clock en el vehiculo)
#   yaml_filename mapa de simulacion -> el mapa real
#   scan_topic    'scan' -> /rplidar_ros/scan
# Ninguno da error si se deja mal: AMCL calla y el planificador aborta.
#
# LO QUE NO HACE, A PROPOSITO
# ---------------------------
# NO manda la meta. Ese es el instante en que el vehiculo se mueve solo, y lo
# dispara una persona mirando el carro. Al terminar imprime el comando.
#
# USO
#     CARRO=192.168.0.102 MAPA=/home/deepracer/tesis/mapa.yaml bash nav2_mapa_guardado.sh   (ruta fija del vehiculo)
#     NS=robot2 CARRO=192.168.0.102 MAPA=... bash nav2_mapa_guardado.sh   (bloque C: todo bajo /robot2)
#     bash nav2_mapa_guardado.sh --estado
#     bash nav2_mapa_guardado.sh --parar
#
# REQUISITO: clave SSH instalada (ssh-copy-id deepracer@<IP>).

set -uo pipefail

CARRO="${CARRO:-192.168.0.102}"
USUARIO=deepracer
# Rutas del VEHICULO, no del portatil: van absolutas porque la tilde no se
# expande dentro de 'urdf:=~deepracer/...' (solo al principio de palabra).
D=/home/deepracer/tesis   # ruta fija del vehiculo
MAPA="${MAPA:-/home/deepracer/mapeo_235028/mapa.yaml}"   # ruta fija del vehiculo
POSE_X="${POSE_X:-1.0}"
POSE_Y="${POSE_Y:-0.0}"
LOGS=/tmp/nav2_campo

# Espacio de nombres (bloque C de Documentos/PLAN_S25.md). Vacio, que es el valor
# por defecto, deja cada orden exactamente como antes: los tres prefijos de abajo
# se reducen a la cadena vacia. Con NS=robot2 todo cuelga de /robot2 y los marcos
# propios llevan 'robot2/'; el lanzador hace lo mismo con 'namespace:=robot2'.
NS="${NS:-}"
NS="${NS#/}"
P="${NS:+/$NS}"                          # prefijo de topicos y servicios: /robot2
F="${NS:+$NS/}"                          # prefijo de marcos: robot2/
ARGS_NS="${NS:+-r __ns:=/$NS}"           # para 'ros2 run'

# Los tres 'source' que hacen falta, en una sola cadena reutilizable.
# La particion del vehiculo, si esta instalada: sin ella, tras aplicar
# Documentos/DISENO_AISLAMIENTO_DOS_CARROS.md, nada de lo que se lanza ve el laser
# ni llega a los servos. Si no esta, no hace nada.
FUENTES='[ -f /etc/deepracer-tesis/particion.xml ] && export FASTRTPS_DEFAULT_PROFILES_FILE=/etc/deepracer-tesis/particion.xml; source /opt/ros/jazzy/setup.bash && source /home/deepracer/nav_ws/install/setup.bash'   # ruta fija del vehiculo
FUENTES_PUENTE='[ -f /etc/deepracer-tesis/particion.xml ] && export FASTRTPS_DEFAULT_PROFILES_FILE=/etc/deepracer-tesis/particion.xml; source /opt/ros/jazzy/setup.bash && source /home/deepracer/coordinacion_ws/install/setup.bash'   # ruta fija del vehiculo

rojo()  { printf '\033[31m%s\033[0m\n' "$*"; }
verde() { printf '\033[32m%s\033[0m\n' "$*"; }
info()  { printf '\033[36m==\033[0m %s\n' "$*"; }

# Ejecuta una orden en el carro, como root y con ROS cargado.
en_carro() {
  ssh -o BatchMode=yes -o ConnectTimeout=8 "$USUARIO@$CARRO" "sudo -n bash -s" <<< "$1" 2>&1
}

# Lanza algo en segundo plano en el carro, que sobreviva al cierre del ssh.
lanzar_en_carro() {
  local nombre="$1" orden="$2"
  ssh -o BatchMode=yes "$USUARIO@$CARRO" "sudo -n bash -s" <<ORDEN >/dev/null 2>&1
mkdir -p $LOGS
setsid nohup bash -c '$orden' > $LOGS/$nombre.log 2>&1 < /dev/null &
ORDEN
}

comprobar_acceso() {
  if ! ssh -o BatchMode=yes -o ConnectTimeout=8 "$USUARIO@$CARRO" true 2>/dev/null; then
    rojo "No hay acceso sin contrasena a $USUARIO@$CARRO."
    echo "   Instala la clave una sola vez:"
    echo "     ssh-keygen -t ed25519 -N \"\" -f ~/.ssh/id_ed25519 2>/dev/null; ssh-copy-id $USUARIO@$CARRO"
    exit 1
  fi
}

# ---------------------------------------------------------------- estado ---
estado() {
  info "procesos en el carro"
  en_carro "ps -eo user,pid,cmd | grep -E '[c]mdvel_to_servo|[r]f2o|[s]lam_toolbox|[c]ontroller_server|[p]lanner_server|[r]obot_state_publisher' || echo '  (nada vivo)'"
  echo
  info "quien escucha $P/cmd_vel"
  en_carro "$FUENTES && timeout 15 ros2 topic info $P/cmd_vel --verbose 2>/dev/null | grep -E 'Publisher count|Subscription count' || echo '  (sin respuesta)'"
  echo
  info "estado de slam_toolbox"
  en_carro "$FUENTES && timeout 15 ros2 service call $P/slam_toolbox/get_state lifecycle_msgs/srv/GetState \"{}\" 2>/dev/null | tail -2 || echo '  (sin respuesta)'"
}

# ----------------------------------------------------------------- parar ---
parar() {
  info "matando la cadena"
  # Por nombre de ejecutable, NUNCA con 'pkill -f' sobre el patron completo:
  # el patron coincide tambien con la propia linea de sudo y se mata a si mismo.
  en_carro "for p in cmdvel_to_serv rf2o_laser_odom sync_slam_toolb robot_state_pub controller_serv planner_server bt_navigator behavior_server waypoint_follow lifecycle_manag map_server amcl; do pkill -9 \$p 2>/dev/null; done; pkill -9 -f nav2_hardware.launch 2>/dev/null; true"
  sleep 2
  verde "listo. Comprueba con: bash $0 --estado"
}

# --------------------------------------------------------------- arrancar ---
# Enciende una pieza de ciclo de vida: la lanza, la configura (1) y la activa (3).
encender_lifecycle() {
  local nodo="$1" orden="$2"
  lanzar_en_carro "$nodo" "$orden"
  sleep 8
  en_carro "$FUENTES && timeout 20 ros2 service call $P/$nodo/change_state lifecycle_msgs/srv/ChangeState \"{transition: {id: 1}}\"" >/dev/null
  sleep 3
  en_carro "$FUENTES && timeout 20 ros2 service call $P/$nodo/change_state lifecycle_msgs/srv/ChangeState \"{transition: {id: 3}}\"" >/dev/null
  sleep 3
  local e
  e=$(en_carro "$FUENTES && timeout 20 ros2 service call $P/$nodo/get_state lifecycle_msgs/srv/GetState \"{}\" 2>/dev/null | tail -2")
  if echo "$e" | grep -q "id=3"; then verde "   $nodo ACTIVO"; return 0
  else rojo "   $nodo NO quedo activo. Mira $LOGS/$nodo.log"; echo "$e"; return 1; fi
}

arrancar() {
  info "0/6 · limpiando restos"
  en_carro "for p in cmdvel_to_serv rf2o_laser_odom sync_slam_toolb robot_state_pub controller_serv planner_server bt_navigator behavior_server waypoint_follow lifecycle_manag map_server amcl; do pkill -9 \$p 2>/dev/null; done; pkill -9 -f nav2_hardware.launch 2>/dev/null; true" >/dev/null
  sleep 3

  info "1/6 · el laser publica?"
  local scan
  # 'average rate' sale en la linea 1 o en la 2, segun 'hz' imprima antes o no el
  # aviso «does not appear to be published yet». Tomar siempre la linea 2 aborto
  # con el laser a 9,9 Hz (amss-jgm9, 2026-09-29).
  scan=$(en_carro "$FUENTES && timeout 20 ros2 topic hz /rplidar_ros/scan 2>/dev/null | head -4 | grep -m1 'average rate'")
  if echo "$scan" | grep -q "average rate"; then verde "   $scan"
  else rojo "   el laser NO publica. sudo systemctl restart deepracer-core, espera 30 s"; exit 1; fi

  info "2/6 · el puente (el launch NO lo arranca)"
  # La suscripcion del puente es absoluta ('/cmd_vel'): el espacio de nombres no
  # la alcanza, y sin el remapeo los dos puentes escucharian el mismo topico.
  lanzar_en_carro puente "$FUENTES_PUENTE && ros2 run cmdvel_to_servo_pkg cmdvel_to_servo_node${NS:+ --ros-args $ARGS_NS -r /cmd_vel:=$P/cmd_vel}"
  sleep 6
  local esc
  esc=$(en_carro "$FUENTES_PUENTE && timeout 20 ros2 service call $P/set_max_speed deepracer_interfaces_pkg/srv/NavThrottleSrv \"{throttle: 0.9}\" 2>/dev/null | tail -2")
  echo "$esc" | grep -q "error=0" && verde "   escala 0.9 puesta" || rojo "   la escala NO se puso; el carro no arrancara"

  info "3/6 · map_server con $MAPA (use_sim_time=false)"
  en_carro "test -f $MAPA" >/dev/null 2>&1 || { rojo "   el mapa no existe en el carro: $MAPA"; exit 1; }
  encender_lifecycle map_server "$FUENTES && ros2 run nav2_map_server map_server --ros-args${ARGS_NS:+ $ARGS_NS} -p use_sim_time:=false -p yaml_filename:=$MAPA -p frame_id:=${F}map" || exit 1

  info "4/6 · amcl (use_sim_time=false, scan_topic=/rplidar_ros/scan)"
  local params_amcl=$D/nav2_params_jazzy.yaml marcos_amcl=""
  if [ -n "$NS" ]; then
    # El YAML tiene claves sueltas ('amcl:') que solo casan con el nodo '/amcl'.
    # Bajo /robot2 hay que anidarlo, como hace 'root_key' en el lanzador.
    params_amcl=$LOGS/nav2_params_$NS.yaml
    en_carro "mkdir -p $LOGS && python3 -c \"import yaml; d = yaml.safe_load(open('$D/nav2_params_jazzy.yaml')); yaml.safe_dump({'$NS': d}, open('$params_amcl', 'w'))\"" >/dev/null
    marcos_amcl="-p base_frame_id:=${F}base_link -p odom_frame_id:=${F}odom -p global_frame_id:=${F}map"
  fi
  encender_lifecycle amcl "$FUENTES && ros2 run nav2_amcl amcl --ros-args${ARGS_NS:+ $ARGS_NS} --params-file $params_amcl -p use_sim_time:=false -p scan_topic:=/rplidar_ros/scan${marcos_amcl:+ $marcos_amcl}" || exit 1

  info "5/6 · el launch, AHORA que /map ya esta activo"
  lanzar_en_carro launch "$FUENTES && ros2 launch $D/nav2_hardware.launch.py slam:=false nav:=true urdf:=$D/deepracer_hardware.urdf params:=$D/nav2_params_jazzy.yaml slam_params:=$D/slam_toolbox.yaml behavior_trees:=$D/behavior_trees${NS:+ namespace:=$NS}"
  echo "   esperando 55 s a que configuren los costmaps..."
  sleep 55

  info "6/6 · pose inicial en ($POSE_X, $POSE_Y) y comprobaciones"
  en_carro "$FUENTES && timeout 15 ros2 topic pub --once $P/initialpose geometry_msgs/msg/PoseWithCovarianceStamped \"{header: {frame_id: ${F}map}, pose: {pose: {position: {x: $POSE_X, y: $POSE_Y, z: 0.0}, orientation: {w: 1.0}}, covariance: [0.25,0,0,0,0,0, 0,0.25,0,0,0,0, 0,0,0,0,0,0, 0,0,0,0,0,0, 0,0,0,0,0,0, 0,0,0,0,0,0.07]}}\"" >/dev/null
  sleep 4
  for n in map_server amcl planner_server controller_server bt_navigator behavior_server; do
    printf "   %-20s %s\n" "$n" "$(en_carro "$FUENTES && timeout 8 ros2 service call $P/$n/get_state lifecycle_msgs/srv/GetState \"{}\" 2>/dev/null | grep -o \"label='[a-z]*'\" | tail -1")"
  done
  local subs
  subs=$(en_carro "$FUENTES && timeout 20 ros2 topic info $P/cmd_vel 2>/dev/null | grep -c 'Subscription count: 1'")
  [ "${subs:-0}" -ge 1 ] && verde "   alguien escucha $P/cmd_vel" || rojo "   NADIE escucha $P/cmd_vel"

  echo
  verde "=================== CADENA LISTA ==================="
  cat <<AYUDA

  PRUEBA EL PLAN SIN MOVER EL CARRO (esto es lo que ahorra la tarde):
    ssh $USUARIO@$CARRO "sudo -n bash -c '$FUENTES && ros2 action send_goal $P/compute_path_to_pose nav2_msgs/action/ComputePathToPose \"{goal: {header: {frame_id: ${F}map}, pose: {position: {x: 6.0, y: 0.0, z: 0.0}, orientation: {w: 1.0}}}, use_start: false}\"'"

  SUCCEEDED = el planificador puede. ABORTED = mira el log del planner_server:
    ssh $USUARIO@$CARRO "sudo -n grep planner_server $LOGS/launch.log | tail -5"
  "Start occupied" = la salida cae en celda no libre: mueve el carro o corrige la pose.

  GRABA, y despues manda la meta:
    ssh $USUARIO@$CARRO "sudo -n bash -c '$FUENTES && cd ~deepracer && timeout -s INT 150 ros2 bag record -s mcap -o nav2_usta_01 /rplidar_ros/scan $P/odom $P/cmd_vel /tf /tf_static $P/plan $P/map $P/amcl_pose; chown -R deepracer:deepracer ~deepracer/nav2_usta_01'"

  LA META (el script NO la manda: la mandas tu mirando el carro):
    ssh $USUARIO@$CARRO "sudo -n bash -c '$FUENTES && ros2 action send_goal --feedback $P/navigate_to_pose nav2_msgs/action/NavigateToPose \"{pose: {header: {frame_id: ${F}map}, pose: {position: {x: 6.0, y: 0.0, z: 0.0}, orientation: {w: 1.0}}}}\"'"

  PARADA DE EMERGENCIA (el carro deja de recibir traccion):
    ssh $USUARIO@$CARRO "sudo -n pkill -9 cmdvel_to_serv"

  El carro VA A SOBREPASAR la meta ~0.4 m. Esta explicado y medido: la banda
  muerta obliga a aproximarse a 0.40 m/s. Anota el error, no lo ajustes.

AYUDA
}

case "${1:-}" in
  --parar)  comprobar_acceso; parar ;;
  --estado) comprobar_acceso; estado ;;
  "")       comprobar_acceso; arrancar ;;
  *)        echo "uso: $0 [--parar|--estado]"; exit 1 ;;
esac
