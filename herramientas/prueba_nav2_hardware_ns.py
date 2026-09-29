#!/usr/bin/env python3
"""El lanzador del vehiculo admite espacio de nombres sin cambiar el modo sin el.

POR QUE EXISTE
--------------
El bloque C de Documentos/PLAN_S25.md pone la pila del vehiculo bajo `/robotN`,
que es como la manda el coordinador. Su criterio de cierre en el escritorio es:
con `namespace:=robot2`, todos los nodos bajo `/robot2` y todos los marcos con
prefijo, y el modo sin espacio de nombres identico al de antes. Un marco sin
prefijar no da error en ninguna parte: el costmap se queda vacio o el
planificador no transforma la meta, y se ve en el pasillo, no aqui.

QUE COMPRUEBA
-------------
Ejecuta nav2_hardware.launch.py sobre un LaunchContext con slam y nav
encendidos, y lee lo que recibiria cada nodo: espacio de nombres, argumentos y
el contenido de sus ficheros de parametros.

  1. SIN ESPACIO DE NOMBRES, IGUAL QUE ANTES. Se lanza tambien la version del
     commit REFERENCIA, anterior al bloque C, y los dos lanzamientos tienen que
     coincidir nodo a nodo y parametro a parametro.
  2. CON `robot2`: todos los nodos bajo `/robot2`; los YAML anidados bajo
     `robot2`; las nueve claves de marco de Nav2 y las tres de slam_toolbox con
     prefijo, y ningun marco de Nav2 sin el; rf2o en `/robot2/odom` con marcos
     prefijados; `frame_prefix` en robot_state_publisher; la TF identidad
     `robot2/laser -> laser`, y el gestor con nombres relativos.

Uso, desde la raiz del repositorio y con ROS y el workspace sourceados:

    python3 herramientas/prueba_nav2_hardware_ns.py [ruta_al_lanzador]

Con la ruta de otro lanzador se comprueba que la prueba no es vacia: con la
version de REFERENCIA la parte 2 tiene que fallar.
"""
import importlib.util
import pathlib
import subprocess
import sys
import tempfile

import yaml

RAIZ = pathlib.Path(__file__).resolve().parents[1]
BRINGUP = RAIZ / 'Robot/aws-deepracer/deepracer_bringup'
LAUNCH = BRINGUP / 'launch/nav2_hardware.launch.py'
URDF = RAIZ / 'Robot/aws-deepracer/deepracer_description/models/urdf/deepracer_hardware.urdf'
# Ultimo commit con el lanzador anterior al bloque C.
REFERENCIA = '6ef1642'
NS = 'robot2'
TOPICO_SCAN = '/rplidar_ros/scan'

MARCOS_NAV2 = {
    ('bt_navigator', 'global_frame'): 'map',
    ('bt_navigator', 'robot_base_frame'): 'base_link',
    ('local_costmap.local_costmap', 'global_frame'): 'odom',
    ('local_costmap.local_costmap', 'robot_base_frame'): 'base_link',
    ('global_costmap.global_costmap', 'global_frame'): 'map',
    ('global_costmap.global_costmap', 'robot_base_frame'): 'base_link',
    ('behavior_server', 'local_frame'): 'odom',
    ('behavior_server', 'global_frame'): 'map',
    ('behavior_server', 'robot_base_frame'): 'base_link',
}
MARCOS_SLAM = {'odom_frame': 'odom', 'map_frame': 'map', 'base_frame': 'base_link'}
NODOS_NAV2 = {'controller_server', 'planner_server', 'behavior_server', 'bt_navigator'}


def cargar(ruta):
    # launch_ros escribe las listas de los diccionarios como tuplas de Python.
    with open(ruta) as f:
        return yaml.load(f, Loader=yaml.UnsafeLoader)


def lanzar(ruta_launch, ns):
    """Devuelve {nombre completo: {ejecutable, ns, args, params}} de cada nodo."""
    from launch import LaunchContext
    from launch.actions import DeclareLaunchArgument

    spec = importlib.util.spec_from_file_location('lanzador', ruta_launch)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    ld = modulo.generate_launch_description()
    contexto = LaunchContext()
    for entidad in ld.entities:
        if isinstance(entidad, DeclareLaunchArgument):
            entidad.execute(contexto)
    contexto.launch_configurations.update({
        'urdf': str(URDF),
        'params': str(BRINGUP / 'config/nav2_params_jazzy.yaml'),
        'slam_params': str(BRINGUP / 'config/slam_toolbox.yaml'),
        'behavior_trees': str(BRINGUP / 'behavior_trees'),
        'slam': 'true',
        'nav': 'true',
        'namespace': ns,
    })
    nodos = {}
    for accion in ld.entities[-1].execute(contexto):
        accion._perform_substitutions(contexto)
        ficheros = [cargar(p) for p, es in (accion._Node__expanded_parameter_arguments or [])
                    if es]
        nodos[accion.node_name] = {
            'ejecutable': accion.node_executable,
            'ns': accion.expanded_node_namespace,
            'args': accion._Node__arguments,
            'params': ficheros,
        }
    return nodos


def del_nodo(ficheros):
    """Parametros de un nodo lanzado con un diccionario (clave '/ns/nombre')."""
    assert len(ficheros) == 1
    return list(ficheros[0].values())[0]['ros__parameters']


def bajar(arbol, ruta):
    for clave in ruta.split('.'):
        arbol = arbol[clave]
    return arbol


def main():
    ruta_launch = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else LAUNCH
    ok, fallos = 0, []

    def exigir(condicion, mensaje):
        nonlocal ok
        if condicion:
            ok += 1
        else:
            fallos.append(mensaje)

    # 1. Sin espacio de nombres, igual que la version de referencia.
    try:
        texto = subprocess.run(
            ['git', 'show', f'{REFERENCIA}:{LAUNCH.relative_to(RAIZ)}'], cwd=RAIZ,
            capture_output=True, text=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        print(f'[OMI] no se pudo leer {REFERENCIA} con git: no se compara con la referencia')
    else:
        with tempfile.NamedTemporaryFile('w', suffix='.launch.py', delete=False) as f:
            f.write(texto)
        antes, ahora = lanzar(f.name, ''), lanzar(ruta_launch, '')
        exigir(set(antes) == set(ahora),
               f'sin espacio de nombres cambian los nodos: {sorted(set(antes) ^ set(ahora))}')
        for nombre in sorted(set(antes) & set(ahora)):
            exigir(antes[nombre] == ahora[nombre],
                   f'sin espacio de nombres cambia {nombre}')
        # launch_ros marca asi un nodo sin espacio de nombres: no le pasa '__ns'.
        from launch_ros.actions import Node
        exigir(all(n['ns'] == Node.UNSPECIFIED_NODE_NAMESPACE for n in ahora.values()),
               'sin espacio de nombres algun nodo recibe uno')

    # 2. Con espacio de nombres.
    try:
        con_ns(lanzar(ruta_launch, NS), exigir)
    except (KeyError, IndexError, ValueError, TypeError) as error:
        fallos.append(f'con {NS} la estructura no es la esperada ({error!r})')

    print('=' * 62)
    if fallos:
        for f in fallos:
            print('  [MAL]', f)
        print(f'{len(fallos)} comprobaciones FALLAN de {ok + len(fallos)}')
        return 1
    print(f'Todas las comprobaciones pasan ({ok}).')
    return 0


def con_ns(nodos, exigir):
    """Comprobaciones de la parte 2 sobre los nodos lanzados con NS."""
    exigir(all(n['ns'] == f'/{NS}' for n in nodos.values()),
           f"nodos fuera de /{NS}: {[k for k, n in nodos.items() if n['ns'] != '/' + NS]}")

    por_ejecutable = {n['ejecutable']: n for n in nodos.values()}
    rsp = del_nodo(por_ejecutable['robot_state_publisher']['params'])
    exigir(rsp.get('frame_prefix') == f'{NS}/', f"frame_prefix es {rsp.get('frame_prefix')!r}")

    rf2o = del_nodo(por_ejecutable['rf2o_laser_odometry_node']['params'])
    exigir(rf2o['odom_topic'] == f'/{NS}/odom', f"rf2o publica en {rf2o['odom_topic']!r}")
    exigir(rf2o['base_frame_id'] == f'{NS}/base_link' and rf2o['odom_frame_id'] == f'{NS}/odom',
           'rf2o sin marcos prefijados')
    exigir(rf2o['laser_scan_topic'] == TOPICO_SCAN, f"rf2o lee {rf2o['laser_scan_topic']!r}")

    tf = por_ejecutable.get('static_transform_publisher')
    exigir(tf is not None, 'falta la TF identidad del laser')
    if tf:
        args = tf['args']
        exigir(args[args.index('--frame-id') + 1] == f'{NS}/laser' and
               args[args.index('--child-frame-id') + 1] == 'laser',
               f'la TF identidad no es {NS}/laser -> laser: {args}')

    for ejecutable in NODOS_NAV2:
        (yaml_nav2,) = por_ejecutable[ejecutable]['params']
        exigir(list(yaml_nav2) == [NS], f'el YAML de {ejecutable} no esta anidado bajo {NS}')
    arbol = por_ejecutable['controller_server']['params'][0][NS]
    for (nodo, clave), marco in MARCOS_NAV2.items():
        valor = bajar(arbol, nodo)['ros__parameters'][clave]
        exigir(valor == f'{NS}/{marco}', f'{nodo}.{clave} vale {valor!r}')
    sueltos = [f'{nodo}.{clave}' for nodo in ('bt_navigator', 'behavior_server',
                                              'local_costmap.local_costmap',
                                              'global_costmap.global_costmap')
               for clave, valor in bajar(arbol, nodo)['ros__parameters'].items()
               if 'frame' in clave and valor in ('map', 'odom', 'base_link')]
    exigir(not sueltos, f'marcos de Nav2 sin prefijo: {sueltos}')
    for capa in ('local_costmap.local_costmap.ros__parameters.voxel_layer',
                 'global_costmap.global_costmap.ros__parameters.obstacle_layer'):
        exigir(bajar(arbol, capa)['scan']['topic'] == TOPICO_SCAN, f'{capa} no lee el laser')
    exigir(arbol['controller_server']['ros__parameters']['controller_frequency'] == 10.0,
           'el controlador no quedo a 10 Hz')

    (yaml_slam,) = por_ejecutable['sync_slam_toolbox_node']['params']
    slam = yaml_slam.get(NS, {}).get('slam_toolbox', {}).get('ros__parameters', {})
    for clave, marco in MARCOS_SLAM.items():
        exigir(slam.get(clave) == f'{NS}/{marco}', f'slam_toolbox.{clave} vale {slam.get(clave)!r}')

    gestor = del_nodo(por_ejecutable['lifecycle_manager']['params'])
    exigir(all(not n.startswith('/') for n in gestor['node_names']),
           'el gestor lleva nombres absolutos: no encontraria los nodos del espacio de nombres')
    exigir(gestor['bond_timeout'] == 20.0, 'el latido del gestor no es 20 s')


if __name__ == '__main__':
    sys.exit(main())
