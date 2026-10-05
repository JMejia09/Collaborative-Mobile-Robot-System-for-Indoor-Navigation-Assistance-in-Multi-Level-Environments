# Documento final — lo que falta por completar

**Última revisión:** 2026-10-05
**Estado del documento:** revisión parcial. El proyecto no ha cerrado: la toma de
datos termina el **viernes 16 de octubre** (corte C-3 del
[`ACTA_GO_NOGO.md`](../ACTA_GO_NOGO.md)).

Esta lista estaba dentro del PDF, en bloques «Nota para la revisión». Se sacaron
de ahí —no son texto del documento— pero los pendientes son reales y siguen
abiertos, así que viven aquí. El texto original sigue en los capítulos, apagado
con `\ustanotasrevisorfalse` en `main.tex`; se vuelve a ver borrando esa línea.

---

## 1. Datos institucionales · `capitulos/00-autoridades.tex` y `main.tex`

Tres datos que **no se deben transcribir de una plantilla**, porque cambian y una
equivocación se ve en la primera página.

| Qué | Qué dice hoy el documento | Qué hace falta |
|---|---|---|
| Autoridades académicas | `NOMBRES COMPLETOS` | Verificarlos en la fuente oficial de la Universidad |
| Grupo de investigación | «GED — Grupo de Estudio y Desarrollo en Robótica» | Confirmarlo. Es el nombre que llevan el anteproyecto y los ocho entregables semanales; si el oficial fuera «Investigación y Desarrollo», hay que corregirlo **en todos ellos**, no solo aquí |
| Línea de investigación | «Robótica y Sistemas Autónomos» | Confirmar la denominación exacta con el director |

## 2. Antecedente interno sin referencia · `capitulos/06-marco-referencial.tex`

El anteproyecto menciona un trabajo de la Universidad Santo Tomás sobre asistencia
a personas invidentes en la primera planta, atribuido a **Parra Buitrago (2021)**.
Allí se cita por nombre y año, pero **no figura en la bibliografía**.

No está en el §2.1 porque no se ha podido localizar la referencia completa. Es el
antecedente más próximo en contexto institucional y merece quedar bien citado.
**Falta:** la referencia, o el dato que permita completarla.

## 3. Marco legal y ambiental · `capitulos/06-marco-referencial.tex` §2.4 y §2.5

Están redactados **solo con lo que se pudo verificar**: las dos políticas CONPES
que ya citaba el anteproyecto y la NTC 1486, que la plantilla institucional
declara como su base.

Quedan tres puntos sin redactar, a propósito, porque una cita normativa mal hecha
es peor que un vacío señalado:

- accesibilidad en edificaciones,
- tratamiento de datos personales,
- uso del espectro.

**Falta decidir** cuáles de los tres aplican de verdad a un prototipo de este
alcance, y si las dos secciones se desarrollan por completo o basta con el
encuadre actual.

## 4. Dedicatoria · `capitulos/01-dedicatoria-agradecimientos.tex`

La escriben los autores, una página por autor. Está comentada con las
instrucciones para activarla: una página con el título y nada debajo es peor que
no ponerla. Los agradecimientos sí están escritos.

---

## 5. Apartados abiertos a la espera de datos

Estos no son pendientes de redacción sino de **medición**, y por eso van aparte.
Se dejaron **sin escribir a propósito**: redactarlos con las cifras de hoy
obligaría a corregirlos el 16 de octubre.

| Apartado | Qué falta para cerrarlo |
|---|---|
| **§4.2.2 La navegación y la precisión de llegada** | La compuerta **G-3**, que no se alcanzó en el corte C-1 y sigue abierta. La sección dice qué irá en ella y no adelanta ningún resultado |
| **Conclusión de OE2, mitad de llegada** | Lo mismo: G-3. La mitad de odometría ya está escrita |
| **Conclusión de OE4, mitad de llegada** | Lo mismo. La simulación y la odometría ya están cerradas y escritas |
| **Trabajos futuros** | La lista puede crecer con lo que arrojen las sesiones que faltan |

> **Cambió el 5 de octubre.** El acta de directores declaró **G-2 (odometría)
> ALCANZADA** con las medidas del 2 de octubre en el piso 4, y dejó **G-3
> (precisión de llegada) abierta**. Antes de esa resolución el §4.2 entero
> estaba sin redactar; ahora la mitad de odometría se reporta como resultado
> cerrado y solo queda abierta la de llegada.

Cada uno lleva en el PDF un bloque **«Apartado en curso»** que dice qué puede
cambiar y qué no. Esos bloques **sí son texto del documento** mientras el
proyecto siga abierto, al contrario que las notas de revisión. Se apagan todos de
golpe con `\ustanotasavancefalse` en `main.tex` cuando cierre.

### Lo que sí está cerrado y no se va a mover

Conviene tenerlo claro para no volver a tocarlo:

- La **campaña de simulación** (§4.1): treinta misiones sorteadas, veredicto
  válido, cero descartes, tasa de éxito superior al 70 % con 95 % de confianza.
  Corrió el 5 de septiembre.
- Las **limitaciones de la medición** (§4.3), que son de esa campaña.
- Las **conclusiones de OE1 y OE3**.
- La conclusión sobre el **objetivo general**, que descansa en la campaña de
  simulación.
- La **banda muerta de tracción** (§3.2.6): es una característica de la
  plataforma medida al integrar, no un resultado de la campaña, y por eso está
  en el capítulo de desarrollo y no en el de resultados.
- La **odometría del vehículo** (§4.2.1, compuerta G-2): declarada alcanzada por
  los directores el 5 de octubre, con error entre −4,6 % y +3,3 % sobre
  recorridos de 6,68 y 14,57 m en el piso 4. Era la única ruta crítica que el
  proyecto se reconocía desde septiembre.
