# Qué documento seguir

El repositorio tiene más de cuarenta documentos de procedimiento, y muchos se escribieron para una
sesión concreta que ya pasó. Leídos hoy, parecen igual de válidos que los vigentes, y no lo son: el
6 de octubre una guía de campo seguía recomendando una escala del puente con la que uno de los dos
vehículos no arranca. Este índice dice, para cada tarea, **qué documento seguir**, y para cada guía,
**si sigue vigente**.

**Regla:** una guía nueva entra en este índice en el mismo commit en que se crea, y una guía que
queda superada se marca aquí, no se borra.

*Estado al 2026-10-06.*

---

## 1. Por tarea

| Quiero… | Seguir | Y tener a mano |
|---|---|---|
| Instalar el proyecto en un equipo nuevo | [`README.md`](../README.md), pasos 1 a 6 | `herramientas/verificar_instalacion.sh` debe terminar en `0 fallan` |
| Correr el sistema completo en simulación: dos robots, coordinador, interfaz y una misión medida | [`GUIA_ARRANQUE.md`](GUIA_ARRANQUE.md) | [`GUIA_EJECUCION.md`](GUIA_EJECUCION.md) para diagnosticar una pieza suelta |
| Repetir la campaña de OE4 en simulación | [`RUNBOOK_CAMPANA.md`](RUNBOOK_CAMPANA.md) | [`PROTOCOLO_EXPERIMENTAL.md`](PROTOCOLO_EXPERIMENTAL.md) |
| Construir o verificar un mapa en simulación | [`guia_simulacion_slam.md`](guia_simulacion_slam.md) | — |
| Navegar un robot simulado sobre un mapa | [`guia_navegacion_nav2.md`](guia_navegacion_nav2.md) | — |
| Saber qué se hace esta semana con los vehículos, y en qué orden | [`PLAN_S26.md`](PLAN_S26.md) | [`ACTA_GO_NOGO.md`](ACTA_GO_NOGO.md) para las compuertas |
| Navegar un vehículo real en los pisos 3 y 4 | [`GUIA_PISOS_3_Y_4.md`](GUIA_PISOS_3_Y_4.md) | [`PLAN_S26.md`](PLAN_S26.md) §3 y §4 para las órdenes de esta semana |
| Montar la red entre los dos pisos | [`TOPOLOGIA_RED.md`](TOPOLOGIA_RED.md) | Procedimiento de RF-15 en [`HOJA_CAMPO_SEGUNDO_DEEPRACER.md`](HOJA_CAMPO_SEGUNDO_DEEPRACER.md) §5 |
| Comprobar la IMU de un vehículo | [`PRUEBAS_IMU.md`](PRUEBAS_IMU.md) | — |
| Entender por qué los dos vehículos no se pisan en la red | [`DISENO_AISLAMIENTO_DOS_CARROS.md`](DISENO_AISLAMIENTO_DOS_CARROS.md) | — |
| Conducir un vehículo con el mando | [`GUIA_TELEOP_MANDO.md`](GUIA_TELEOP_MANDO.md) | — |
| Capturar la evidencia de una prueba | [`HOJA_CAPTURA_S26.md`](HOJA_CAPTURA_S26.md) | Convención en [`Evidencia/README.md`](Evidencia/README.md) |
| Consultar las interfaces ROS 2 entre coordinador, agentes e interfaz | [`CONTRATO_INTERFACES.md`](CONTRATO_INTERFACES.md) | — |
| Saber dónde está el proyecto | [`ESTADO.md`](../ESTADO.md) | [`CRONOGRAMA_S17_S32.md`](CRONOGRAMA_S17_S32.md) |

---

## 2. Guías de campo de hardware

Son las que más envejecen, porque cada una se escribió para una salida concreta.

| Guía | Escrita para | Estado |
|---|---|---|
| [`GUIA_PISOS_3_Y_4.md`](GUIA_PISOS_3_Y_4.md) | El sitio de pruebas actual, desde el 2-oct | **Vigente** |
| [`TOPOLOGIA_RED.md`](TOPOLOGIA_RED.md) | La red de los pisos 3 y 4, desde el 5-oct | **Vigente** |
| [`PRUEBAS_IMU.md`](PRUEBAS_IMU.md) | La IMU de la tarjeta, desde el 5-oct | **Vigente** |
| [`GUIA_TELEOP_MANDO.md`](GUIA_TELEOP_MANDO.md) | Conducir con el mando, sin fecha de sesión | **Vigente** |
| [`HOJA_CAMPO_SEGUNDO_DEEPRACER.md`](HOJA_CAMPO_SEGUNDO_DEEPRACER.md) | La llegada del segundo vehículo, 11-sep | **Histórica como hoja de sesión.** Su §5, el procedimiento de RF-15, sigue vigente y lo usa `PLAN_S26` §2.4 |
| [`GUIA_CAMPANA_NAV2_HARDWARE.md`](GUIA_CAMPANA_NAV2_HARDWARE.md) | G-2 y G-3, 29-sep al 2-oct | **Histórica.** Para G-3 en los pisos 3 y 4, `PLAN_S26` §3.2. Ojo: recomienda la escala 0,9, que no sirve para racey |
| [`GUION_NAVEGACION_USTA.md`](GUION_NAVEGACION_USTA.md) | Navegar el piso 1 con el mapa del modelo, 25-sep | **Histórica.** El sitio cambió a los pisos 3 y 4 el 5-oct |
| [`GUION_NAV2_HARDWARE.md`](GUION_NAV2_HARDWARE.md) | Peldaños 4 a 7 de Nav2 sobre hardware, 24-sep | **Histórica.** Peldaños superados |
| [`GUION_CAMPO_PISO2.md`](GUION_CAMPO_PISO2.md) | Recorrido propio y mapa del piso 2, 24-sep | **Sustituida** para G-2 el 25-sep, como dice su cabecera |
| [`GUION_SALIDA_S24.md`](GUION_SALIDA_S24.md) | La salida del 23-sep | **Histórica** |
| [`GUION_RECTA_PELDANO2.md`](GUION_RECTA_PELDANO2.md) | La recta del peldaño 2, 23-sep | **Histórica.** G-2 quedó alcanzada el 2-oct |
| [`HOJA_CAMPO_G2.md`](HOJA_CAMPO_G2.md) | El G2 del pasillo, 3-sep (anterior al acta) | **Histórica.** No es la compuerta G-2 del acta |
| [`GUIA_PASADA_MAPEO.md`](GUIA_PASADA_MAPEO.md) | El mapa del pasillo para ese G2, 1-sep | **Histórica** |
| [`GUIA_PASADA_LOCALIZACION.md`](GUIA_PASADA_LOCALIZACION.md) | M1 y M2 de ese G2, 2-sep | **Histórica** |

Una guía histórica **no está mal**: es el registro de cómo se hizo una prueba, y por eso se
conserva. Lo que no se debe hacer es seguirla hoy sin contrastarla con la vigente, porque los
vehículos, el sitio y el código cambiaron desde que se escribió.

---

## 3. Planes semanales

`PLAN_S26.md` es el vigente. Los anteriores (`PLAN_S17_S18`, `PLAN_S19`, `PLAN_S20`, `PLAN_S22` y
`PLAN_S25`) y los planes de requisito (`PLAN_RF25`, `PLAN_RF28_CONFIRMACION`) son registro: dicen
qué se planeó y cómo se cumplió, y los cita la bitácora de [`ESTADO.md`](../ESTADO.md).
