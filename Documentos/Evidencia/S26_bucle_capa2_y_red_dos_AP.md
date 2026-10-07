# Un bucle de capa 2 duplicaba el 47 % del tráfico, y el `ping` decía 0 % de pérdida (7 de octubre)

Sesión de red con Jonny, desde el portátil y por SSH a los dos vehículos. Se montó una primera
versión de la topología de dos puntos de acceso de [`TOPOLOGIA_RED.md`](../TOPOLOGIA_RED.md) y se
verificó. **No se cambió ninguna configuración**: el equipo estaba haciendo pruebas y pidió dejar el
montaje como estaba para seguir en el laboratorio al día siguiente.

## Resultado

Se encontró y se resolvió un **bucle de capa 2** que entregaba cada paquete hasta tres veces. Con él
resuelto, el enlace entre los dos vehículos quedó en **3,75 ms de promedio con 0,51 ms de
variación**, que es lo mejor que ha medido el proyecto.

Quedan dos cosas abiertas, y una **no es de red**: el grafo de ROS de `amss-ez9n` no se forma, ni
siquiera consigo mismo.

---

## 1. El bucle

### 1.1 Lo que se veía, y por qué no lo delataba el `ping`

```
60 packets transmitted, 60 received, +24 duplicates, 0% packet loss
rtt min/avg/max/mdev = 2.566/32.989/180.919/48.419 ms
```

**`0 % de pérdida` y la red parecía sana.** Lo que no cuadraba eran los `+24 duplicates` y un pico de
181 ms contra un equipo de la propia LAN.

La duplicación era **específica del vehículo**, no general:

| Destino | Duplicados en 40 pings |
|---|---|
| Router `.1` | 0 |
| Otro equipo `.105` | 0 |
| **Vehículo `.104`** | **15 (37 %)** |

Y una petición llegó a responderse **tres veces** (`icmp_seq=3` ×3). Sin conflicto de IP: la MAC del
vehículo fue estable en cinco comprobaciones seguidas.

### 1.2 Cómo se probó que era un bucle, y no otra cosa

El vehículo no tiene `tcpdump`, así que se usaron **los contadores ICMP del kernel**
(`/proc/net/snmp`), leídos antes y después de un número exacto de pings:

| | |
|---|---|
| Peticiones **enviadas** desde el portátil | **100** |
| Peticiones **recibidas** por el vehículo | **147** |
| Respuestas emitidas por el vehículo | 147 |
| Lo que volvió al portátil | 99 + 48 duplicados = 147 |

**El vehículo se comporta bien**: responde una vez a cada petición que le llega. Es la red la que le
entrega cada petición hasta tres veces. Eso es un bucle de capa 2 **medido**, no deducido.

> Este método vale la pena recordarlo. Sin `tcpdump`, los contadores del kernel bastan para separar
> «me llegan respuestas de más» de «le llegan peticiones de más», que son fallos distintos.

### 1.3 El culpable

Un barrido de las redes en el aire lo mostró:

```
fhmesh_8C5FAD37AA40    8C-5F-AD-37-AA-46   ch36   señal 27
```

El FiberHome `AA` estaba emitiendo su **SSID de malla**, no el de un punto de acceso normal. Un nodo
de malla enlaza por aire con el otro nodo; si **además** está conectado por cable a la misma red,
tiene dos caminos y las tramas dan la vuelta por los dos.

Encaja con que los duplicados aparecieran y desaparecieran —la calidad del enlace de malla varía— y
con que el equipo estuviera lejos (señal 27).

Un vigilante de 5 minutos dejó la línea base antes de tocar nada: **duplicados en 20 de 24 muestras**,
con un pico del **100 %** (30 duplicados sobre 30 pings).

### 1.4 Resuelto

Tras la intervención de Jonny, con el `fhmesh_` ya fuera del aire:

| Destino | Recibidos | Duplicados | Pérdida |
|---|---|---|---|
| Router | 60 | **0** | 0 % |
| `amss-ez9n` | 60 | **0** | 0 % |
| `amss-jgm9` | 60 | **0** | 0 % |

## 2. La red, medida bien

Las primeras medidas daban promedios de 33 ms y picos de 205. **Estaban contaminadas por el propio
portátil**, que sigue en 2,4 GHz por el TP-Link, en la banda donde hay 33 redes compitiendo. Los
vehículos no pasan por ahí.

La medida que importa es **entre los dos vehículos**, y no involucra al portátil:

```
8 enviados, 8 recibidos, 0 % de pérdida
min 3,235 · promedio 3,753 · max 4,659 · jitter 0,512 ms
```

**Es la mejor cifra que ha medido el proyecto.** Para comparar: RF-15 en septiembre dio 7,61 ms de
mediana, y la de 5 GHz del 5 de octubre, 5,99 ms.

> **Lección de método:** medir desde el portátil mide el peor enlace de la cadena, que es el del
> portátil. RF-15 está escrito como vehículo↔vehículo por esta razón exacta, y conviene no sustituir
> esa pareja por comodidad.

También se comprobó, y **descarta** tres sospechas:

| Comprobación | Resultado |
|---|---|
| Multidifusión `.102` → `.104` | ✅ llega |
| Multidifusión `.104` → `.102` | ✅ llega |
| Reglas de `ufw` en los dos | ✅ `192.168.0.0/24 # DDS tesis` presente |
| `ping` vehículo↔vehículo | ✅ 8/8, 0 % |

*(Se sospechó de `ufw` por un error propio: un `head -4` truncó la salida y escondió las reglas. Las
reglas estaban bien desde el principio.)*

## 3. Lo que queda abierto

### 3.1 Los dos puntos de acceso están en el mismo canal

| Vehículo | Punto de acceso | Canal |
|---|---|---|
| `amss-ez9n` | `CLARO_WIFIA40` | **36** |
| `amss-jgm9` | `DEEPRACER PRO-5G` | **36** |

Comparten aire. Hay que separarlos a **36 y 44 con ancho de 40 MHz** (§4 de `TOPOLOGIA_RED.md`:
con 80 MHz un canal en el 36 ocupa hasta el 48 y se pisarían enteros).

### 3.2 `amss-ez9n` no forma grafo de ROS — y esto no es de red

| | `amss-ez9n` (.102) | `amss-jgm9` (.104) |
|---|---|---|
| `deepracer-core` | activo | activo |
| Procesos ROS | 23 | corriendo |
| `ros2 node list` | **vacío** | ve la pila de Nav2 completa |
| Ve sus **propios** tópicos | **no** | sí (`/rf15/ping`, `/rf15/pong`) |

`.102` no ve ni sus propios nodos. Se comprobó con 30 s de espera, **como `root`**, y **con
`--no-daemon`** para esquivar la caché del CLI. Los procesos están corriendo, la memoria sobra y
`/dev/shm` está al 1 %.

**Hipótesis, sin confirmar:** ese vehículo cambió de red mientras sus nodos corrían, y los
participantes de DDS quedaron atados a una dirección que ya no existe. El descubrimiento falla en
silencio. **La prueba barata es reiniciarlo**, y no se hizo porque el equipo estaba usando los
vehículos.

**Esto es lo que hizo fallar la medida de RF-15 de hoy** (`SIN_DATOS`, 600 enviados y 0 recibidos).
No fue la red: fue que `.102` no podía hablar DDS con nadie, ni consigo mismo.

### 3.3 Nombres de nodo duplicados en el grafo

Al listar nodos desde `.104` apareció:

```
WARNING: Be aware that there are nodes in the graph that share an exact name
```

Los dos vehículos están publicando nodos con el mismo nombre en el mismo dominio. Es lo que el
espacio de nombres `/<ns>/` debería separar, y es una de las mitades que RF-12 tiene pendiente sobre
hardware. Queda anotado; no se tocó.

## 4. Para la sesión de mañana, en el laboratorio

1. Reiniciar `amss-ez9n` y volver a mirar `ros2 node list`. Si se arregla, confirma el §3.2.
2. Separar los canales a 36 y 44, con 40 MHz.
3. SSID por piso y fijar cada vehículo al suyo, sin borrar `DEEPRACER`.
4. Reservas de DHCP por MAC (`.102` y `.104`).
5. Repetir RF-15 vehículo↔vehículo. **Con la red en 3,75 ms debería dar `CUMPLE` con mucho margen.**
6. Y lo que cierra la tarea §2.4 del plan: repetirlo **con un vehículo en cada piso**, con el cable
   entre plantas puesto.
