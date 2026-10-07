# Topología de red para el sitio nuevo — cómo debe quedar

**Fecha:** 2026-10-05 · **revisado el 2026-10-07**
**Estado:** **montado a medias.** Los dos puntos de acceso están en puente sobre la misma subred y
cada vehículo cuelga de uno distinto, que es la forma correcta. Faltan los pasos 2 (canales), 3 y 5
(SSID por piso), 6 (reservas) y 7-8 (cable entre plantas y la medida que cierra). Los pasos siguen
en orden y son seguros: en ninguno se queda un vehículo sin acceso.

> **Al día 2026-10-07.** Lo medido en la sesión de hoy está en
> [`S26_bucle_capa2_y_red_dos_AP.md`](Evidencia/S26_bucle_capa2_y_red_dos_AP.md). Dos cosas:
>
> - **Se encontró y se resolvió un bucle de capa 2** que entregaba cada paquete hasta tres veces
>   (47 % de amplificación) y que el `ping` no delataba, porque informaba `0 % de pérdida`. Lo
>   causaba un FiberHome en **modo malla** enlazando por aire mientras estaba también cableado. **El
>   modo malla no se usa en este montaje**, justamente por eso.
> - **El enlace vehículo↔vehículo quedó en 3,75 ms de promedio con 0,51 ms de variación**, la mejor
>   cifra del proyecto. Las latencias malas que se veían antes eran del portátil, que mide su propio
>   salto en 2,4 GHz y no el de los vehículos.
>
> **Pendiente y no es de red:** `amss-ez9n` no forma grafo de ROS, ni consigo mismo. Se reinicia
> primero y se vuelve a mirar (§3.2 de esa evidencia).
**Evidencia que lo sostiene:**
[`S26_red_5ghz_regulatorio.md`](Evidencia/S26_red_5ghz_regulatorio.md)

---

## 0. La idea, en una frase

**Una sola red, un solo DHCP, un solo dominio de difusión** —que es lo que DDS necesita para
descubrir—, con **un punto de acceso por piso en 5 GHz** y los dos unidos **por cable**, no por aire.

Los SSID distintos por piso no son redes distintas: son dos radios de la misma red. Sirven para que
cada vehículo quede fijado a su planta sin ambigüedad, y eso es legítimo aquí porque **ningún robot
cambia de nivel**: cada uno tiene un punto de acceso de casa, fijo, para siempre.

## 1. Cómo debe quedar

```
                    ┌─────────────────────────────┐
                    │   TP-Link TL-WR940N         │
                    │   router + DHCP             │
                    │   192.168.0.1/24            │
                    │   SSID DEEPRACER            │
                    │   2,4 GHz ch6  ← RESPALDO   │
                    └──────────┬──────────────────┘
                               │
                 ┌─────────────┴─────────────┐
              cable LAN                  cable LAN
              (mismo piso)              (entre pisos)
                 │                           │
      ┌──────────┴──────────┐     ┌──────────┴──────────┐
      │  FiberHome  PISO 4  │     │  FiberHome  PISO 3  │
      │  puente, DHCP OFF   │     │  puente, DHCP OFF   │
      │  5 GHz · ch36 · 40M │     │  5 GHz · ch44 · 40M │
      │  SSID DEEPRACER_P4  │     │  SSID DEEPRACER_P3  │
      └──────────┬──────────┘     └──────────┬──────────┘
                 │                           │
            vehículo piso 4             vehículo piso 3
```

### Por qué el TP-Link se queda

Durante la sesión se planteó quitarlo, y el argumento era la interferencia: tres radios apiladas en
los canales 3 y 5. **Ese argumento se agotó al pasar los vehículos a 5 GHz.** El TP-Link emite en
2422 MHz y los vehículos trabajan en 5180 MHz: bandas distintas, no se tocan.

Lo que se gana conservándolo es una red de seguridad que no cuesta nada: **los vehículos mantienen
`DEEPRACER` guardada**, así que si un FiberHome falla vuelven solos al TP-Link sin que nadie
intervenga. Y cambiar el router a once días del corte C-3 obliga a rehacer reservas, revisar `ufw` y
volver a medir, sin ganar un milisegundo.

Queda por revisar después del 16 de octubre, con calma. El argumento que le sigue en contra es que
es el punto único de fallo, y eso se mitiga teniéndolo a mano, no cambiándolo ahora.

## 2. Datos

| Vehículo | MAC de `mlan0` | IP que debe tener |
|---|---|---|
| `amss-ez9n` | `80:91:33:ed:8c:f3` | `192.168.0.102` |
| `amss-jgm9` | `80:91:33:f3:e6:ab` | `192.168.0.104` |

| Equipo | MAC base | Papel |
|---|---|---|
| TP-Link TL-WR940N | `60:32:B1:77:FB:CC` | router + DHCP + respaldo 2,4 GHz |
| FiberHome | `8C:5F:AD:37:AA:xx` | punto de acceso, un piso |
| FiberHome | `8C:5F:AD:37:D2:xx` | punto de acceso, el otro piso |

**La subred tiene que seguir siendo `192.168.0.0/24`.** No es estética: las reglas de `ufw` de los
vehículos están abiertas por rango (`sudo ufw allow from 192.168.0.0/24`). Si la subred cambia, el
cortafuegos bloquea DDS y deja la firma engañosa de *ping perfecto, grafo ROS vacío*.

## 3. Pasos, en este orden

### Paso 1 · Reiniciar el FiberHome `DEEPRACER PRO`

El `8C:5F:AD:37:D2:xx`. Su configuración es resto del montaje de malla que no funcionó, y
**probablemente tiene su propia red** —no se pudo verificar, el intento de conexión se agotó—.

Botón de reinicio, 10 s. Queda como `CLARO_WIFI…`. Ningún vehículo está en él, así que no rompe nada.

> El otro FiberHome ya se reinició el 5 de octubre y **levantó usable, sin quedarse esperando
> aprovisionamiento de Claro.** Ese era el riesgo y quedó descartado.

### Paso 2 · Ese equipo pasa a ser el punto de acceso del piso 3

Entrar a `192.168.10.1` con las credenciales de la etiqueta:

| Ajuste | Valor |
|---|---|
| Modo | **punto de acceso / puente** |
| DHCP | **apagado** |
| SSID 5 GHz | `DEEPRACER_P3` |
| Canal 5 GHz | **44**, fijo |
| Ancho | **40 MHz** |
| 2,4 GHz | apagada |
| Aislamiento de clientes | **apagado** |

Cable desde su puerto **LAN** a un puerto **LAN** del TP-Link. Nunca al WAN.

**Comprobar:** debe aparecer con una IP `192.168.0.x`. Si sale con otra subred, el DHCP no quedó
apagado.

> **El indicador verde no se va a encender, y está bien.** El LED sigue el puerto WAN, que en modo
> puente queda sin usar. Mide algo que aquí no se quiere.

### Paso 3 · Pasar el vehículo del piso 3 a su red

Añadirle `DEEPRACER_P3` **sin borrar `DEEPRACER`**, y comprobar con un reinicio que levanta solo.

### Paso 4 · El otro FiberHome, punto de acceso del piso 4

El `8C:5F:AD:37:AA:xx`, que ya está en puente y funcionando:

| Ajuste | Valor |
|---|---|
| SSID 5 GHz | `DEEPRACER_P4` |
| Canal 5 GHz | **36**, fijo |
| Ancho | **40 MHz** |
| 2,4 GHz | apagada |
| Aislamiento de clientes | **apagado** |
| DHCP | sigue apagado |

> Al cambiarle el SSID los vehículos se caen de la red actual. **No pasa nada:** tienen `DEEPRACER`
> guardada y vuelven solos al TP-Link.

### Paso 5 · Pasar el vehículo del piso 4

Igual que el paso 3, con `DEEPRACER_P4`.

### Paso 6 · Reservas de DHCP en el TP-Link

En `192.168.0.1`, fijar por MAC las dos direcciones de la tabla del §2.

Esto evita que los vehículos se muevan de IP —ya pasó: las guías dicen `.100` y `.102`, hoy están en
`.102` y `.104`— y mata la trampa del `deepracer.local` ambiguo con dos vehículos en la red.

De paso, mover su 2,4 GHz del canal 3 al **6**, que estaba menos cargado.

### Paso 7 · El cable entre pisos

Puerto **LAN** del FiberHome del piso 3 a un puerto **LAN** del TP-Link.

**Prueba:** desconectar ese cable. El punto de acceso del piso 3 debe quedarse sin red. Si sigue
funcionando, está enlazando por aire y hay que forzar el cableado.

### Paso 8 · Medir en el sitio real

Con cada vehículo en su piso, `medir_latencia_red.py` entre los dos. **Esa medida es la que vale**
para RF-15 en el documento; la del 5 de octubre se tomó con los dos en el mismo punto de acceso y en
la misma sala, y solo sirve de línea base.

## 4. Por qué 40 MHz y no 80

El enlace de prueba negoció **80 MHz**. Un canal de 80 MHz en el 36 ocupa **del 36 al 48 completo**,
así que el segundo punto de acceso en el 44 quedaría dentro del primero y se pisarían enteros.

Con 40 MHz, el 36 cubre 36-40 y el 44 cubre 44-48: separación limpia. No se pierde nada que importe
—40 MHz son unos 400 Mbit/s y el tráfico del proyecto son mensajes de control más un barrido de
LiDAR—. **Separación limpia vale más que caudal que no se va a usar.**

## 5. Por qué el orden es ese

**En ningún paso se queda un vehículo sin red**, porque `DEEPRACER` sigue guardada en los dos de
principio a fin. Si algo sale mal, el TP-Link los recupera solo.

Es la misma disciplina del resto del proyecto: no se sierra la rama donde uno está sentado, y el plan
B se deja montado antes de necesitarlo.
