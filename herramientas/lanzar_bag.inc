# Arranque y cierre de un bag que SI cierra. Se incluye con 'source'.
#
# POR QUE HACE FALTA UN FICHERO PARA ESTO
# ---------------------------------------
# Un bag de rosbag2 solo vuelca su indice al cerrarse LIMPIAMENTE, con SIGINT.
# Matado de cualquier otra forma deja un '.mcap' sin 'metadata.yaml', y ese bag
# no se puede reproducir ni leer: los datos estan ahi y son inalcanzables.
#
# EL FALLO QUE ESTO EVITA, MEDIDO EL 2026-09-24
# ---------------------------------------------
# Un shell NO INTERACTIVO pone SIGINT y SIGQUIT en SIG_IGN a todo lo que lanza
# en segundo plano, y esa disposicion sobrevive al exec. El grabador nacia
# SORDO a la señal: 'kill -INT' no hacia absolutamente nada y el guion se
# quedaba esperando un 'metadata.yaml' que no iba a llegar. Dos corridas
# seguidas quedaron con el bag ilegible antes de entenderlo.
#
# 'trap - INT' NO lo arregla, y fue el primer intento fallido: 'trap -'
# restaura la disposicion HEREDADA por el shell, que es precisamente SIG_IGN.
# Lo que si sirve es 'set -m': con control de trabajos activo, cada proceso de
# fondo nace en su propio grupo y con las disposiciones por defecto.
#
# Por que 'timeout -s INT' si funcionaba: alli el grabador corria en primer
# plano, donde el shell no toca las disposiciones. Sigue siendo valido cuando
# se conoce de antemano cuanto va a durar la grabacion.
#
# USO
#     source "$(dirname "$0")/lanzar_bag.inc"
#     arrancar_bag ~deepracer/mi_bag /rplidar_ros/scan /odom
#     ... lo que sea ...
#     cerrar_bag

# Particion del vehiculo (Documentos/DISENO_AISLAMIENTO_DOS_CARROS.md). Si esta
# instalada, este proceso TIENE que cargarla: sin ella no ve /rplidar_ros/scan ni
# /tf ni llega a los servos, y no da ningun error. Si no esta instalada -antes de
# aplicar el diseno, o en el portatil-, esto no hace nada.
[ -f /etc/deepracer-tesis/particion.xml ] && export FASTRTPS_DEFAULT_PROFILES_FILE=/etc/deepracer-tesis/particion.xml

arrancar_bag() {
    local destino="$1"; shift
    set -m
    ros2 bag record -s mcap -o "$destino" $* > /tmp/bag.log 2>&1 &
    BAG_PID=$!
    set +m
    BAG_DESTINO="$destino"
    sleep 4
}

cerrar_bag() {
    [ -n "${BAG_PID:-}" ] || return 0
    # Primero SIGINT, que es el cierre limpio. Si en 25 s no aparece
    # 'metadata.yaml', SIGTERM, que rosbag2 tambien atiende cerrando el fichero,
    # y 10 s mas. Solo despues SIGKILL: con el, el .mcap pierde el ultimo bloque
    # que tenia en memoria, y las grabaciones del 2-oct terminaban metros antes
    # que la corrida. Se envia al grupo (el grabador lo encabeza por 'set -m').
    kill -INT -- "-$BAG_PID" 2>/dev/null || kill -INT "$BAG_PID" 2>/dev/null
    local i
    for i in $(seq 25); do
        [ -f "$BAG_DESTINO/metadata.yaml" ] && break
        sleep 1
    done
    if [ ! -f "$BAG_DESTINO/metadata.yaml" ] && kill -0 "$BAG_PID" 2>/dev/null; then
        echo "AVISO: el grabador no cerro con SIGINT; se le manda SIGTERM"
        kill -TERM -- "-$BAG_PID" 2>/dev/null || kill -TERM "$BAG_PID" 2>/dev/null
        for i in $(seq 10); do
            [ -f "$BAG_DESTINO/metadata.yaml" ] && break
            sleep 1
        done
    fi
    chown -R deepracer:deepracer "$BAG_DESTINO" 2>/dev/null
    if [ -f "$BAG_DESTINO/metadata.yaml" ]; then
        # Se imprime la CUENTA y no solo el nombre del fichero. Un bag con
        # metadata pero con 'message_count: 0' es el sintoma de haber grabado
        # con el usuario equivocado: 'rplidar_node' publica como root y un
        # 'ros2' que corra como 'deepracer' descubre pero no recibe, sin dar
        # error. Se comprueba aqui porque en campo nadie lo mira.
        grep 'message_count' "$BAG_DESTINO/metadata.yaml" | head -4
    else
        # Se termina a la fuerza para que no quede grabando: el 2026-09-29, en
        # amss-jgm9, dos grabadores ignoraron la senal y seguian vivos minutos
        # despues. 'extraer_mapa.py' recupera el mapa de un .mcap sin cerrar.
        kill -9 "$BAG_PID" 2>/dev/null
        pkill -9 -f "[r]os2 bag record -s mcap -o $BAG_DESTINO" 2>/dev/null
        echo "AVISO: el bag no cerro; queda sin metadata.yaml (extraer_mapa.py lo lee igual)"
    fi
}
