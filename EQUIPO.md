# Registro del equipo — Mate 0.6

Este archivo es el registro compartido del equipo de agentes. Cada agente lo lee antes de
empezar. Lo actualiza el integrador al cerrar cada vuelta, con lo que informaron los demás.

## Alcance

Tres cambios, sacados de lo que le pasó al dueño al usar Mate en su computadora (Windows,
PowerShell 5.1, Python llamado con `py`, modelo local por `MATE_IA_PROPIA`):

| # | Cambio | Problema real que resuelve |
|---|---|---|
| 1 | Mostrador con reglas en el programa, y comandos sugeridos con `py` | La IA dijo que 12 fideos salían $ 10,80 y negó un envío que correspondía; Mate sugiere `python ...` y en esa máquina no existe |
| 2 | Orden `nuevo mostrador <nombre>` | Hubo que copiar un ejemplo y una planilla a mano; quedó el renglón de títulos repetido |
| 3 | Orden `ensayar programa.mate casos.txt` | No hay forma de saber si una lección funcionó sin tipear pregunta por pregunta |

## Criterios de aceptación

**Cambio 1**
- `12_mostrador_con_reglas.mate` pasa `verificar` y `probar`, y está comentado como los demás.
- Con la planilla de muestra: "quiero 12 azucar con envio" da el total exacto y envío sí; "me mandas 5 yerbas?" da envío no; ninguna de las dos consulta a la IA.
- Lo que no es un pedido con cantidad va a la IA, con frenos.
- Lanzado con `py`, los comandos que Mate sugiere dicen `py mate\mate.py ...`; con la orden instalada, `mate ...`; si no se sabe, como hasta ahora.
- El manual dice qué va en una lección, qué en un freno y qué en el programa.

**Cambio 2**
- `nuevo mostrador mi_negocio` crea el programa y la planilla en la carpeta actual, y ambos pasan `verificar` y `probar` sin tocarlos.
- Si algún archivo ya existe, no pisa nada y lo dice.
- Sigue andando si se cambian los productos de la planilla.
- Una planilla con el renglón de títulos repetido da un error que dice qué renglón borrar.

**Cambio 3**
- `ensayar` corre los casos de un archivo de texto y muestra cuántos pasaron y, de cada uno que falló, la pregunta, la respuesta y la regla incumplida.
- Funciona con `--ia-simulada`, con un modelo propio y con Claude; avisa antes cuántas consultas va a hacer.
- `--veces=N` repite cada caso e informa "pasó 4 de 5".
- No cambia la memoria del programa. Los casos que fallan quedan como lección propuesta.
- Anda con el ejemplo 12 y con lo que crea `nuevo mostrador`.

**Para todo**
- Un programa que no usa lo nuevo se comporta igual y no crea archivos.
- `probar` no toca la red, el teclado ni archivos reales de memoria, bitácora o registro.
- Ninguna clave aparece en archivos, trazas ni errores.
- Pasan todas las pruebas, `probar mate/ejemplos` y `probar mate/curso`.

## Equipo y límites

| Rol | Qué hace | Qué puede tocar |
|---|---|---|
| Coordinador (sesión principal) | Define alcance y criterios, lanza las vueltas, decide la integración final | Este archivo; mezclas entre ramas |
| Implementador | Programa el cambio y dice cómo verificarlo | Todo `mate/` y `docs/`, en la rama `equipo/mate-0.6` |
| Revisor independiente | Lee el código real y exige correcciones | Nada del repositorio (solo copias temporales) |
| Agente de pruebas | Usa lo nuevo como una persona que no programa | Nada del repositorio (solo copias temporales) |
| Integrador | Corre todo junto, comprueba flujos que cruzan cambios, actualiza este registro | Este archivo; arreglos de integración mínimos |
| Especialista en seguridad | Revisa el conjunto al final: claves, archivos, red | Nada del repositorio |

Todo el intérprete es un solo archivo (`mate/mate.py`), así que los cambios van **en serie**,
uno por vez, y nunca dos agentes escriben a la vez. El revisor y el agente de pruebas sí
trabajan en paralelo, porque no escriben en el repositorio.

Nadie aprueba su propio código: un cambio se cierra cuando el revisor y el agente de pruebas
no tienen problemas de gravedad alta ni media.

Los agentes no pueden hablarse mientras trabajan: se comunican por los informes que se pasan
entre vuelta y vuelta, y por este registro.

## Decisiones técnicas

- Rama de trabajo: `equipo/mate-0.6`. No se sube nada a `main` sin aprobación del dueño.
- Otra IA (Codex) sube cambios a `main`: no se reordena ni reescribe código que no haga falta.
- (C1) Para saber si lo llamaron con `py` se mira el proceso padre en Windows (lista de
  procesos por `ctypes`, una sola vez y solo al sugerir un comando). Cualquier falla = "no se
  sabe" = `python mate\mate.py`, como antes. Fuera de Windows no se mira nada.
- (C1) La decisión está en funciones puras, probables desde Linux: `orden_segun(avisada,
  lanzador, en_windows)` y `lanzador_entre(procesos, yo)` (sube hasta 4 niveles y solo
  atraviesa `python*.exe`).
- (C1) `MATE_ORDEN` acepta `mate`, y ahora también `py` y `python` (salida manual si la
  detección falla; solo tienen efecto en Windows). Otros valores se ignoran.
- (C1) `con_la_orden_de_esta_computadora(texto)` cambia `python mate\mate.py` por `py ...` en
  guía, ayuda y clases solo cuando la orden detectada es `py`; si no, el texto queda idéntico.
- (C1) El ejemplo 12 es Mate común: no se tocó el intérprete. `numero("1.000")` da 1 (ya era
  así) y no se cambia; el ejemplo trata el punto de miles a mano.
- (C1) En el ejemplo 12, ante la duda el programa pregunta en vez de elegir: dos productos o
  dos cantidades en una frase se piden de a uno; un número se clasifica por lo que lo rodea
  (`$` = plata, medida atrás = medida, parte del nombre del producto, o cantidad).
- (C1) No se agrega "envío" a `prohibido` en los frenos: mandaría casi todo a la reserva.
- (C1) El pedido de varios productos en una frase queda fuera de alcance: falta que el dueño
  defina la regla de envío para pedido mixto. Lo decide el coordinador.

## Punto de partida

- Rama creada desde `main` en `7a4cf4f`.
- Pruebas: 789 pasan y 1 falla. La que falla (`test_estan_los_seis_ejemplos_graduales`) es
  conocida: el ejemplo 12, todavía sin commitear, tiene pocos comentarios. Es parte del cambio 1.

## Vueltas

(El integrador agrega acá una sección por vuelta: qué se hizo, qué encontraron el revisor y
el agente de pruebas, qué se corrigió, qué quedó pendiente y con qué evidencia.)

### Cambio 1, vuelta 1 — NO cerrado (revisor y agente de pruebas no aprobaron)

**Qué se implementó** (commit `77a74fa`, implementador)
- Ejemplo `12_mostrador_con_reglas.mate` terminado y comentado: producto, cantidad, total y
  envío los resuelve el programa; lo demás va a la IA con frenos.
- `como_se_llama()` detecta `py` en Windows; guía, ayuda y clases del curso se reescriben con
  `py`. Aclaración de `py` en README, curso/README, docs/index.html e `instalar.bat quitar`.
- README: sección "Qué va en una lección, qué en un freno y qué en el programa". MEJORAS 121.
- 6 pruebas nuevas. Única prueba vieja tocada: la lista de ejemplos graduales suma el 12.

**Pruebas** (integrador, Linux, `MATE_SIN_REGISTRO=1`, sobre `77a74fa`)
- `pytest mate/pruebas mate/modelo`: 796 pasan, 0 fallan (partida: 789 y 1 falla; esa ahora pasa).
- `probar mate/ejemplos`: 58 de 58, en 18 archivos. `probar mate/curso`: 30 de 30, en 24 archivos.
- Después de todo eso `git status` queda vacío: `probar` no dejó archivos.

**Flujos cruzados comprobados por el integrador**
- Ejemplo 12 con modelo propio de mentira (127.0.0.1, `MATE_IA_PROPIA` + clave de mentira):
  los dos pedidos del criterio dan total y envío correctos y el servidor no recibe nada por
  ellos; "hola" sí llega al modelo; el modelo que dice "$ 10,80" es frenado dos veces y sale
  la reserva; queda la lección propuesta y `propuestas` la muestra. La clave no aparece en la
  salida, la traza, la memoria ni la bitácora.
- Windows simulado (`os.name`="nt", lanzador puesto a mano) en `curso`, `curso 99`,
  `curso 12`, `guia`, `ayuda` y `propuestas`: con `py` no queda ningún `python mate\mate.py`;
  sin lanzador queda como antes; con `MATE_ORDEN=mate` dicen `mate` (salvo guía y ayuda, P10).
- `nuevo mostrador` y `ensayar` todavía no existen: esos cruces quedan para los cambios 2 y 3.

**Problemas** (R = revisor, P = agente de pruebas, I = integrador)

| # | Problema | Quién | Gravedad | Estado |
|---|---|---|---|---|
| P1 | Ejemplo 12: envío negado con otras palabras ("no me lo mandes", "no necesito envío", "no hace falta") contesta "Con envío: sí" | R, P | media | pendiente (vuelta 2) |
| P2 | En Windows con `py -m pytest` fallarían 5 pruebas viejas que buscan `python mate\mate.py` fijo (simulado). Arreglo pedido: que las pruebas fijen `_QUIEN_ME_LANZO` y `MATE_ORDEN`, también en los subprocess, sin tocar lo que afirman | R, P | media | pendiente (vuelta 2) |
| P3 | Ejemplo 12: "Pan" no se puede pedir si existe "Pan rallado" (círculo "decime cuál") | P | media | pendiente (vuelta 2) |
| P4 | "1,000 yerbas" cotiza 1 unidad; "2 docenas de yerba" cotiza 2 | R, P | baja | pendiente |
| P5 | README dice que "mandame una docena" va a la IA y lo contesta el programa | R | baja | pendiente |
| P6 | Planilla sin columna `stock`: error técnico en el primer pedido, no al cargar | R | baja | pendiente (importa para cambio 2) |
| P7 | "no quiero 3 yerbas", "devolver 3", "-3 yerbas" se cotizan; "3 harina 0000" da "veo más de un número" | R | baja | pendiente (al menos anotarlo en "Lo que no hace") |
| P8 | "que me lo traigan" y "¿mandás o retiro?" no dicen nada del envío | P | baja | pendiente |
| P9 | Las 14 pruebas del ejemplo 12 dependen de la planilla de muestra (con otra: 2 de 14) | P | baja | pendiente: avisarlo en el encabezado; tenerlo en cuenta en cambio 2 |
| P10 | Con `MATE_ORDEN=mate`, `ayuda` y `guia` siguen diciendo `python mate\mate.py`; `curso` desde otra carpeta sugiere ruta relativa | P | baja | ya estaba antes; descartado para este cambio |
| P11 | La detección real de `py.exe` no se ejecutó en una Windows (¿PyManager?) | R, P, I | baja | pendiente: lo prueba el dueño (`py mate\mate.py curso 99`). Falta decir en el README la salida manual `MATE_ORDEN=py` |
| P12 | Falsos positivos seguros ("mandame la lista de precios" contesta la regla del envío; "12 yerbas para el 15/12" pregunta) | Impl. | — | descartado: aceptables por seguros (R) |
| P13 | Un modelo que contesta en inglés pasa sin freno | P | baja | ya estaba antes (ejemplo 11); descartado acá |
| P14 | `numero("1.000")` da 1 | Impl. | — | ya estaba antes; mejora aparte |

El integrador no arregló nada en esta vuelta: P1 a P3 tocan la lógica del ejemplo y las
pruebas, y van al implementador.

**Criterios de aceptación del cambio 1**

| Criterio | Estado | Evidencia |
|---|---|---|
| El 12 pasa `verificar` y `probar`, comentado | cumple | "sin errores"; 14 de 14; pasa `test_estan_los_seis_ejemplos_graduales` |
| Los dos pedidos, exactos y sin IA | cumple | $ 117.606,00 con envío sí; $ 175.000,00 con envío no; el modelo de mentira no recibió pedidos por ellos (R, P, I) |
| Lo demás va a la IA con frenos | cumple | precio inventado y total mal calculado terminan en la reserva (P, I) |
| Comandos con `py` / `mate` / como antes | cumple solo simulado | pruebas `orden_segun`, `lanzador_entre`, `lanzado_con_py`; sin probar en Windows real (P11) |
| El manual dice qué va en cada lugar | cumple | README, sección nueva; detalle a corregir en P5 |
| Para todo: pruebas, ejemplos, curso | cumple en Linux; no en Windows con `py` | 796 / 58 de 58 / 30 de 30; ver P2 |
| Para todo: nada nuevo sin usarlo, `probar` limpio, claves | cumple | `git status` vacío tras `probar`; clave de mentira ausente de salida y archivos |

**Para la vuelta 2**: P1, P2 y P3 (obligatorios); P4 a P9 y la línea del README de P11 si entran.
Para el cambio 2: avisar al cargar la planilla si faltan columnas, si hay títulos repetidos o
si la primera palabra de un producto es muy corta ("Té"); el ejemplo reconoce cada producto
por la primera palabra del nombre. Para quien cierre la 0.6: `VERSION` sigue en 0.5.
