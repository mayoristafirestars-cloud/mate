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
- (C1, v2) En el ejemplo 12 el envío tiene tres respuestas: `sobre_el_envio()` da "si", "no"
  o "". Con pedido, solo "si" agrega la frase del envío; sin pedido, "si" y "no" contestan la regla.
- (C1, v2) Ante la duda gana el no: una negación cerca de una palabra de envío deja solo el
  total. Callar sobre el envío no cuesta plata; confirmar uno que no pidieron, sí. Costo
  aceptado y documentado: algún pedido con envío y un "no" cerca queda sin la frase del envío.
- (C1, v2) Las palabras de retiro ("retiro", "paso a buscar") ya no apagan nada.
- (C1, v2) "no quiero N ...", devoluciones y cancelaciones no se cotizan: van a la IA con
  frenos. Si conviene una respuesta fija del programa lo decide el dueño (vía coordinador).
- (C1, v2) Entre productos que empatan por la primera palabra gana el que se nombró entero
  ("Pan" contra "Pan rallado"); las palabras se comparan en singular o plural.
- (C1, v2) Un número con coma nunca vale como cantidad; "docena" y "par" son medidas.
- (C1, v2) "-3 yerbas" se cotiza como 3 (el guion puede ser de lista) y "3 harina 0000" sin esa
  harina en la planilla pregunta en vez de cotizar la 000: a propósito, anotado en el README.
- (C1, v2) La planilla se revisa en el programa (`revisar_planilla`) antes de atender: si falta
  una columna o no hay productos, avisa en castellano y no entra a la charla.
- (C1, v2) Las pruebas no dependen de con qué se lanzó pytest: un arreglo automático de
  `test_mate.py` fija `mate._QUIEN_ME_LANZO = ""` y `MATE_ORDEN=python` (igual a "no se sabe";
  lo heredan los subprocesos). Las pruebas que miran `py` o `mate` ponen su valor. No hace
  falta un `conftest.py` común: `mate/modelo` pasa igual en la simulación.

- (C1, v3) En el ejemplo 12 la frase se parte en los signos de puntuación (`palabras_y_cortes()`
  deja una marca en , . ; : ? ! ( ); `palabras_de()` devuelve lo mismo que antes). Un punto o
  una coma entre dos cifras sigue siendo parte del número.
- (C1, v3) El "no" se busca para atrás hasta el corte anterior o un "pero", sin tope de
  palabras (un tope volvería a confirmar envíos negados en frases largas), y para adelante en
  las tres palabras que siguen a la de envío, sin cortar en la coma ("¿envío? no, gracias").
  Costos aceptados por R: sin comas, un "no" de otra cosa antes de la palabra de envío deja
  solo el total; "mandame 12 yerbas, no voy a poder ir" también.
- (C1, v3) Niegan además: "jamás", "nada (de)", "nadie", "ningún", "olvidate", "dejalo". "Sin"
  no niega hacia adelante ("sin falta") y "nada más" tampoco. "No sé" es excepción solo si
  sigue "si", "cómo", "cuándo", "dónde", "qué", "cuánto", "cuál", "bien" o un corte.
- (C1, v3) Sigue el criterio de la v2: con negación y pedido el programa calla sobre el envío
  (no se pasó a una "regla neutra": cambiaría respuestas ya aprobadas).
- (C1, v3) El nombre del producto se saca de la frase también en plural (`es_del_nombre()`)
  antes de buscar el envío; `misma_palabra()` compara primero tal cual y después "ces"/"zes".
- (C1, v3) "2 pan lactal" con "Pan" y "Pan dulce" cotiza Pan: "lactal" no está en la planilla
  y no se distingue de "2 pan por favor". Aceptado por R; anotado en el README.

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

### Cambio 1, vuelta 2 — NO cerrado (queda un problema medio: P15)

**Qué se implementó** (commit `68c60e3`, implementador; `mate/mate.py` no se tocó)
- Ejemplo 12: el envío negado delante de la palabra de envío da solo el total (P1); "Pan" se
  puede pedir aunque exista "Pan rallado" (P3); "1,000" y "2 docenas" ya no se cotizan mal
  (P4); la planilla se revisa al arrancar (P6); "no quiero 3", "devolver", "cancelame" van a
  la IA (P7); "que me lo traigan" y "¿mandás o retiro?" contestan la regla (P8); el
  encabezado avisa que las pruebas son para la planilla de muestra (P9). 4 pruebas más (18).
- Pruebas: arreglo automático para que no dependan del lanzador (P2). 2 pruebas nuevas.
- README: corregido el ejemplo de "mandame una docena" (P5), salida manual
  `$env:MATE_ORDEN = "py"` (P11), "Lo que no hace" ampliado. MEJORAS 121 actualizada.
- Pruebas viejas tocadas (las dos de la vuelta 1, del mismo implementador): "14 de 14" pasó a
  "18 de 18" porque el ejemplo tiene 4 pruebas más; en `test_lanzado_con_py...` se sacó un
  `monkeypatch.undo()` que deshacía también el bloqueo de red. Ninguna afirma menos (R, P).

**Pruebas** (integrador, Linux, `MATE_SIN_REGISTRO=1`, sobre `68c60e3`)
- `pytest mate/pruebas mate/modelo`: 798 pasan, 0 fallan (vuelta 1: 796).
- `probar mate/ejemplos`: 62 de 62, en 18 archivos. `probar mate/curso`: 30 de 30, en 24 archivos.
- Ejemplo 12: `verificar` "sin errores"; `probar` 18 de 18. Después, `git status` vacío.
- P también corrió las 798 con `MATE_ORDEN=mate` y `MATE_ORDEN=py` en el entorno: pasan.

**Flujos cruzados comprobados por el integrador**
- Ejemplo 12 con modelo propio de mentira (127.0.0.1, `MATE_IA_PROPIA` + clave de mentira),
  copiado a una carpeta temporal: los dos pedidos del criterio dan $ 117.606,00 con envío sí
  y $ 175.000,00 con envío no, y "12 yerbas, no me lo mandes" da solo el total; el servidor
  recibió 0 pedidos por esas frases. "hola, que tienen?" y "no quiero 3 yerbas" sí llegan al
  modelo (4 pedidos: 2 por cada una); el modelo que dice "$ 10,80 ... descuento" es frenado
  dos veces y sale la reserva; quedan 2 lecciones propuestas y `propuestas` las muestra. La
  clave no aparece en la salida ni en la memoria ni en la bitácora.
- Windows simulado (`os.name`="nt", lanzador puesto a mano) en `curso 99`, `curso 12`,
  `guia`, `ayuda` y `propuestas` del ejemplo 12: con `py` no queda ningún `python
  mate\mate.py`; sin lanzador queda como antes; `MATE_ORDEN=mate` da `mate curso` y
  `MATE_ORDEN=py` da `py mate\mate.py curso`. `verificar` y `probar` no sugieren comandos.
- `nuevo mostrador` y `ensayar` siguen sin existir: esos cruces quedan para los cambios 2 y 3.

**Estado de los problemas de la vuelta 1**

| # | Estado | Evidencia |
|---|---|---|
| P1 | resuelto en la forma pedida (queda P15, el orden inverso) | 6 frases negadas dan solo el total (R, P, I) |
| P2 | resuelto, solo por simulación | Windows simulado con `py`: con `77a74fa` fallan las 5 pruebas viejas, con `68c60e3` pasan (Impl., R, P) |
| P3 | resuelto (queda P16) | "2 pan", "2 panes", "2 pan rallado" dan el producto correcto (R, P) |
| P4, P5, P6, P8, P9 | resueltos | comprobados por R y P |
| P7 | resuelto en parte; el resto descartado | "-3 yerbas" y "3 harina 0000" quedan como están, con razones aceptadas por R y anotadas en el README |
| P11 | texto resuelto; la prueba real sigue pendiente | README dice `$env:MATE_ORDEN = "py"`; falta la corrida del dueño |
| P10, P13, P14 | descartados (ya estaban antes) | sin cambios |

**Problemas nuevos de la vuelta 2**

| # | Problema | Quién | Gravedad | Estado |
|---|---|---|---|---|
| P15 | Ejemplo 12: si el "no" va después de la palabra de envío, o a más de cinco palabras, sigue contestando "Con envío: sí" ("12 yerbas, el envio no hace falta", "envio no", "mandarlo no hace falta", "nada de envio", "jamas me las mandes", "ni se te ocurra mandarlas", "olvidate del envio", "que nadie me las mande"). El README promete más de lo que hace | R, P; reproducido por I | media | pendiente (vuelta 3) |
| P16 | Con "Pan" y "Pan dulce", "2 panes dulces" cotiza el Pan común (antes preguntaba): `misma_palabra()` cambia todo "ces" por "zes", y el desempate nuevo elige el corto aunque quede una palabra de otro producto | R | baja | pendiente (vuelta 3 si entra) |
| P17 | "12 mandiocas" se toma como pedido de envío: el plural del nombre no se saca de la frase antes de buscar el envío | R | baja | ya estaba antes; pendiente (vuelta 3 si entra) |
| P18 | Un "no" cercano que no niega el envío apaga la frase ("no, 12 yerbas con envio", "no voy a poder ir, mandame 12 yerbas", "si no es molestia me las mandan?") | R, P | baja | aceptado como decisión (calla, no afirma nada falso); falta decirlo más claro en el README y, si entra, cortar la ventana en la coma o el punto |
| P19 | `revisar_planilla`: títulos con mayúscula o tilde dan "falta la columna producto"; el renglón de títulos repetido queda como un producto | R, P | baja | pasa al cambio 2 |
| P20 | El aviso del freno sugiere `propuestas` con ruta relativa a `mate.py` aunque se esté en otra carpeta | P; visto por I | baja | ya estaba antes (familia de P10); descartado para este cambio |
| P21 | "quiero llevar 12 yerbas" y "12 yerbas, mandame el precio" contestan "Con envío: sí" | Impl. | — | descartado: ya estaba y lo que dice es cierto (R) |

El integrador no arregló nada en esta vuelta: P15 a P17 son lógica del ejemplo 12 (no de
integración) y van al implementador.

**Criterios de aceptación del cambio 1**

| Criterio | Estado | Evidencia |
|---|---|---|
| El 12 pasa `verificar` y `probar`, comentado | cumple | "sin errores"; 18 de 18; pasa la prueba de los ejemplos graduales (R, P, I) |
| Los dos pedidos, exactos y sin IA | cumple | $ 117.606,00 con envío sí; $ 175.000,00 con envío no; 0 pedidos al modelo de mentira (R, P con 4 modelos, I) |
| Lo demás va a la IA con frenos | cumple | precio inventado termina en la reserva; "no quiero 3 yerbas" llega al agente (R, P, I) |
| Comandos con `py` / `mate` / como antes | cumple solo simulado | `mate.py` sin cambios desde `77a74fa`; simulación de P e I; sin probar en Windows real (P11) |
| El manual dice qué va en cada lugar | cumple, con una frase a corregir | README: P5 corregido; el párrafo del envío negado promete de más (P15) |
| Para todo: pruebas, ejemplos, curso | cumple en Linux; Windows con `py` solo simulado | 798 / 62 de 62 / 30 de 30; P2 por simulación |
| Para todo: nada nuevo sin usarlo, `probar` limpio, claves | cumple | intérprete sin tocar; `git status` vacío tras pytest y `probar`; clave de mentira ausente de salida y archivos (P, I) |

**Para la vuelta 3**: P15 (obligatorio): mirar también las dos o tres palabras siguientes a
la de envío con las mismas excepciones, sumar "jamas", "nada" y "nadie", que la excepción "se"
valga solo después de "no", agregar las frases a la prueba del ejemplo y ajustar el README.
Cuidar que "12 azucar me la mandas o tengo que retirar?" siga dando "sí". Si entran: P16, P17
y el texto de P18.
Para el coordinador: (1) falta la corrida del dueño en Windows: `py mate\mate.py curso 99`
tiene que sugerir `py mate\mate.py curso`, y `py -m pytest mate\pruebas mate\modelo -q -p
no:cacheprovider` tiene que dar todo verde; (2) preguntarle al dueño si devoluciones y
cancelaciones van a la IA con frenos (como ahora) o a una respuesta fija.
Para el cambio 2: P19, además de lo anotado en la vuelta 1.

### Cambio 1, vuelta 3 — NO cerrado (queda un problema medio: P22)

**Qué se implementó** (commit `dd95608`, implementador; `mate/mate.py` no se tocó)
- Ejemplo 12: el "no" después de la palabra de envío, lejos o dicho de otra forma da solo el
  total (P15); "2 panes dulces" cotiza el Pan dulce (P16); "12 mandiocas" ya no es un pedido
  de envío (P17); un "no" de otra cosa separado por una coma ya no apaga el envío (P18).
  2 pruebas más en el ejemplo (20) y 2 ampliadas.
- README: el párrafo "El envío" y "Algunos casos que conviene conocer" dicen dónde se busca el
  "no" y qué queda afuera. MEJORAS 121: punto "Tercera vuelta".
- Pruebas de Python: ninguna nueva; se ampliaron las dos del ejemplo 12. Única prueba vieja
  tocada: "18 de 18" pasó a "20 de 20". Ninguna afirma menos (R, P).

**Pruebas** (integrador, Linux, `MATE_SIN_REGISTRO=1`, sobre `dd95608`)
- `pytest mate/pruebas mate/modelo`: 798 pasan, 0 fallan (igual que la vuelta 2); también con
  `MATE_ORDEN=py` en el entorno.
- `probar mate/ejemplos`: 64 de 64, en 18 archivos. `probar mate/curso`: 30 de 30, en 24 archivos.
- Ejemplo 12: `verificar` "sin errores"; `probar` 20 de 20. Después, `git status` vacío.

**Flujos cruzados comprobados por el integrador**
- Ejemplo 12 con modelo propio de mentira (127.0.0.1, `MATE_IA_PROPIA` + clave de mentira), en
  una carpeta temporal: los dos pedidos del criterio dan $ 117.606,00 con envío sí y
  $ 175.000,00 con envío no; "12 yerbas, el envio no hace falta" y "12 yerbas sin envio" dan
  solo el total; "no, 12 yerbas con envio" da envío sí. El servidor recibió 0 pedidos y la
  traza no tiene ninguna Consulta. No se creó memoria ni bitácora.
- Mismo modelo diciendo "12 fideos salen $ 10,80 y te hago un descuento": "hola, que tienen?"
  y "no quiero 3 yerbas" llegan al modelo (4 pedidos: 2 por cada una), salta el freno y sale
  la reserva; quedan 2 lecciones propuestas y `propuestas` las muestra. La clave no aparece
  en la salida, la traza, la memoria ni la bitácora.
- Windows simulado (`os.name`="nt", lanzador puesto a mano): `py` da `py mate\mate.py`; sin
  lanzador o con `python` da `python mate\mate.py`; `MATE_ORDEN=mate` da `mate`;
  `MATE_ORDEN=py` da `py mate\mate.py`. Pasan las 7 pruebas de la orden y del ejemplo 12.
- `nuevo mostrador` y `ensayar` siguen sin existir ("no conozco la orden"): esos cruces, y
  las sugerencias con `py` en las órdenes nuevas, quedan para los cambios 2 y 3.

**Estado de los problemas de la vuelta 2**

| # | Estado | Evidencia |
|---|---|---|
| P15 | resuelto (quedan P22 y P24) | las 17 frases de los dos informes dan solo el total, más las que R y P probaron por su cuenta ("envío: no", "(sin envío)", "envio ni loco") |
| P16 | resuelto | "2 panes dulces" da Pan dulce; "2 pan" y "2 panes" dan Pan (R, P, I) |
| P17 | resuelto | "12 mandiocas" solo el total; "12 mandiocas con envio" da sí (R, P, I) |
| P18 | mejorado; el resto queda como decisión | con coma contestan el envío; sin coma callan, y el README lo dice (R, P) |
| P19 | pasa al cambio 2 | sin cambios |
| P20, P21 | descartados (ya estaban) | sin cambios |
| P11 | sigue pendiente del dueño | no hay Windows acá |

**Problemas nuevos de la vuelta 3**

| # | Problema | Quién | Gravedad | Estado |
|---|---|---|---|---|
| P22 | Ejemplo 12: si un producto de la planilla tiene "sin" o "no" en el nombre ("Yerba sin palo", "Galletitas sin sal", "Arroz no se pasa"), "12 yerbas sin envio", "12 yerba mate sin envio" y "12 arroz no me lo mandes" contestan "Con envío: sí". `entender()` saca de la frase todas las palabras de los nombres de los productos nombrados antes de buscar el envío, y con ellas se van "sin" y "no". Viene de la vuelta 2; el README promete "sin" | R; reproducido por I | media | pendiente (vuelta 4) |
| P23 | "12 yerbas, no tengo necesidad de envio" y "12 yerbas, no puedo recibir envios" dan "sí": "no tengo" y "no puedo" son excepción aunque nieguen | R | baja | pendiente (vuelta 4 si entra: acotarlas como "no sé", o anotarlo en el README) |
| P24 | Un "no" a más de tres palabras después de la palabra de envío, o dicho de otra forma, da "sí" ("el envio esta vez mejor no", "el envio la verdad que no lo quiero", "lo del envio mejor dejemoslo") | R, P | baja | aceptado como límite conocido: el README lo avisa. Si se toca: alargar la ventana hasta el próximo signo y sumar "dejemos" |
| P25 | "12 yerbas, no se si quiero envio" y "¿envío? No sé" dan "sí" | P | baja | descartado: decisión documentada, y lo que dice es cierto para 12 unidades |
| P26 | Pedidos de envío con un "no" cerca callan ("12 yerbas con envio, no te olvides", "mandame 12 yerbas. No hay apuro", "12 yerbas sin falta mandalas") | P | baja | descartado: calla, no afirma nada falso; está en el README |
| P27 | "no quiero 3 yerbas con envio" se cotiza (3 yerbas, sin frase de envío) en vez de ir a la IA | Impl. | baja | pendiente, no exigido: R prefiere que vaya a la IA como "otra cosa" |
| P28 | "no me alcanza, 12 yerbas con envio" da solo el total ("alcanza" cuenta como palabra de envío) | Impl. | — | descartado: calla y es una frase rara (R) |

El integrador no arregló nada en esta vuelta: P22 es lógica del ejemplo 12 (no de
integración), necesita revisión independiente y va al implementador.

**Criterios de aceptación del cambio 1**

| Criterio | Estado | Evidencia |
|---|---|---|
| El 12 pasa `verificar` y `probar`, comentado | cumple | "sin errores"; 20 de 20; pasa la prueba de los ejemplos graduales (R, P, I) |
| Los dos pedidos, exactos y sin IA | cumple | $ 117.606,00 con envío sí; $ 175.000,00 con envío no; 0 pedidos al modelo de mentira y 0 Consulta en la traza (R, P con 4 modelos, I) |
| Lo demás va a la IA con frenos | cumple | "hola" y "no quiero 3 yerbas" llegan al modelo; el precio inventado termina en la reserva (R, P, I) |
| Comandos con `py` / `mate` / como antes | cumple solo simulado | `mate.py` sin cambios desde `77a74fa`; simulación de P e I; sin probar en Windows real (P11) |
| El manual dice qué va en cada lugar | cumple, con una promesa a corregir | con la planilla de muestra el README coincide frase por frase (R, P); "sin" no vale si un producto lo tiene en el nombre (P22) |
| Para todo: pruebas, ejemplos, curso | cumple en Linux; Windows con `py` solo simulado | 798 / 64 de 64 / 30 de 30 |
| Para todo: nada nuevo sin usarlo, `probar` limpio, claves | cumple | intérprete sin tocar; `git status` vacío tras pytest y `probar`; clave de mentira ausente de salida y archivos (P, I) |

**Para la vuelta 4**: P22 (obligatorio): al armar `sin_nombre` no sacar las palabras de
negación (las de `niega()`), o sacar solo las que `es_de_envio()` tomaría por envío; agregar
a la prueba una planilla con "Yerba sin palo" y las frases "12 yerbas sin envio", "12 yerba
mate sin envio" y "12 yerba sin palo sin flete". Si entran: P23 y P27.
Para el coordinador (sin cambios): falta la corrida del dueño en Windows (`py mate\mate.py
curso 99` y `py -m pytest mate\pruebas mate\modelo -q -p no:cacheprovider`) y su decisión
sobre devoluciones y cancelaciones.
Para el cambio 2: `nuevo mostrador` hereda del ejemplo 12 `palabras_y_cortes()`,
`es_del_nombre()` y también P22 si no se arregla antes; la planilla del dueño puede tener
productos "sin palo", "sin sal", "sin TACC". Si la planilla tiene "Pan dulce" y "Dulce de
leche", "2 panes dulces" contesta "de a un producto por vez": no es falla (R). Sigue P19.
