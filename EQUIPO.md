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

- (C2) La plantilla del mostrador no vive dos veces: `nuevo mostrador` arma el programa al
  momento con el ejemplo 12 (lo que hay entre los títulos `# La regla del envío:` y
  `# ── Las pruebas`, cambiando `precios.csv` por `<nombre>_precios.csv`) y copia tal cual
  `ejemplos/precios.csv`. En `mate.py` quedan solo el encabezado y 7 pruebas. Costo: la orden
  necesita la carpeta `ejemplos` (si falta lo dice, código 1) y esos dos títulos no se tocan;
  lo cuida `test_nuevo_mostrador_copia_la_logica_del_ejemplo_12_sin_cambiarla`.
- (C2) Un mostrador creado es una copia fija: no recibe los arreglos posteriores del ejemplo 12.
- (C2) La planilla se llama `<nombre>_precios.csv` (no choca con un `precios.csv` que ya
  esté, y dos mostradores conviven). Falta el visto bueno del dueño.
- (C2) Las 7 pruebas del programa creado usan una lista fija y `unidades_para_envio`: pasan
  con cualquier planilla y cualquier número de envío. Una sola mira la planilla del dueño.
- (C2) Nunca pisa: se niega si existe el programa, `<nombre>.mate.txt`, la planilla, o la
  memoria o la bitácora de un programa viejo con ese nombre. Crea en modo exclusivo; si
  falla el segundo archivo borra solo el primero recién creado.
- (C2) El `.mate` creado va en UTF-8 con la marca del principio y los fines de renglón del
  sistema (CRLF en Windows), para el Bloc de notas.
- (C2) Los comandos sugeridos por `nuevo mostrador` (y los del encabezado del programa, fijos
  al crearlo) llevan la ruta de `mate.py` vista desde la carpeta actual
  (`orden_para_esta_carpeta()`: reutiliza `como_se_llama()` y `ruta_para_escribir()`). El
  resto de los avisos sigue con `mate\mate.py` relativo (P20).
- (C2) Nombre válido: una palabra de hasta 60 letras, números, guion o guion bajo, que empiece
  con letra o número; no valen rutas, órdenes de Mate ni nombres reservados de Windows.
  `nuevo` sola con un `nuevo.mate` en la carpeta sigue corriendo ese programa.
- (C2) El error de títulos repetidos está en `leer_tabla` (vale para todo programa): solo con
  dos columnas o más y si TODAS las celdas coinciden con los títulos, sin mirar mayúsculas ni
  tildes. Cambio de comportamiento a propósito, anotado en el README ("Qué cambió y puede
  frenar un programa viejo").
- (C2) En el ejemplo 12, `revisar_planilla` dice qué título está mal escrito (P19) y
  `nombres_muy_cortos` avisa, sin impedir atender, si un producto empieza con una palabra de
  1 o 2 letras ("Té").

- (C3) `ensayar` le reemplaza el teclado al programa: por cada pregunta el programa corre
  entero y de cero en un intérprete nuevo, su primer `leer()` recibe la pregunta y la
  respuesta es lo que muestra hasta que vuelve a pedir algo por teclado (ahí se lo corta con
  `_FinDelEnsayo`, que hereda de `BaseException` y el programa no puede atajar) o termina. No
  se le habla al agente directo: en el ejemplo 12 los pedidos con cantidad los contesta el
  programa antes de llegar al agente. Límite aceptado: si el primer `leer()` no es la
  consulta del cliente, la pregunta cae en el lugar equivocado (P44).
- (C3) Un ensayo lee la memoria (ensaya con las lecciones aprobadas) y nunca la guarda: ni
  memoria, ni bitácora, ni cuenta del día. Lo que el programa escribe en archivos no llega al
  disco (`archivos_de_prueba`, igual que `probar`). Lo único que se agrega al archivo de
  memoria son las propuestas, al final. Las consultas de verdad de un ensayo no quedan en la
  cuenta del día ni en `bitacora` (aceptado por R; falta decirlo en el informe final).
- (C3) Dentro del ensayo valen el tope por día del agente y el de 50 consultas de verdad por
  corrida, contados para el ensayo entero; al llegar a 50 se corta y lo dice.
- (C3) Único cambio en el intérprete: el atributo `ensayando` (nace en falso); dos
  condiciones `en_prueba` pasaron a `en_prueba or ensayando` para anotar `ia_historial`.
- (C3) Lección propuesta: una por caso fallado y por agente que consultó, con redacción fija
  (no gasta consultas), con `sumar_propuesta`; no se repite si ya está propuesta o aprobada.
  No se propone si contestó el programa sin la IA, si la IA no llegó a contestar o si la
  consulta no la hizo un agente.
- (C3) Las reglas se comparan buscando el texto dentro de la respuesta, sin mayúsculas,
  tildes ni espacios de más; `|` separa opciones. "no puede decir: hay envío" salta con "no
  hay envío": avisado en el README y en `casos.txt`.
- (C3) Archivo de casos: la pregunta en un renglón y debajo `tiene que decir:` / `no puede
  decir:` (también `debe decir:`, `no debe decir:`, `no tiene que decir:`); varias preguntas
  seguidas comparten las reglas de abajo; `#` es una nota; tope de 200 preguntas. Una regla
  sin los dos puntos es un error con su renglón.
- (C3) `ensayar` exige que haya quién conteste (`--ia-simulada`, `MATE_IA_PROPIA` o la clave)
  antes de empezar; con Claude avisa "cada consulta se paga" y arranca sin pedir confirmación
  (aceptado por R). `--veces` va de 1 a 20; `--traza` y `--olvidar` se rechazan.
- (C3) Los casos de muestra viven en `ejemplos/casos.txt`; `nuevo mostrador` crea
  `<nombre>_casos.txt` copiándolo desde el título "Cómo se escribe" (`_CASOS_DESDE`), con un
  encabezado propio. El caso "tenes cafe?" lleva solo reglas `no puede decir` para pasar con
  `--ia-simulada`; la regla exigente queda como nota (ver P39: hoy eso deja pasar un modelo apagado).
- (C3) `ensayar` sola con un `ensayar.mate` en la carpeta sigue corriendo ese programa.

- (C3, v2) Un caso tiene tres finales: pasó (`✓`), falló (`✗`) o "no se pudo comprobar" (`?`,
  ASCII). "Sin comprobar" es por corrida: si CUALQUIER consulta de esa corrida quedó sin
  respuesta, no se evalúan las reglas y no cuenta como pasada, aunque el programa haya seguido
  solo. Con `--veces`: alguna vez sin comprobar y ninguna fallada = `?`; si además falló
  alguna = `✗`. En los dos casos el código es 1. Reemplaza lo anotado arriba sobre P39.
- (C3, v2) El tope por día del agente también deja el caso sin comprobar ("No se consultó a
  la IA: tope de gasto..."), en vez de evaluar el texto de reserva. No corta el ensayo.
  Aceptado por R; falta que el resumen lo distinga (P53).
- (C3, v2) Corte: si la primera consulta del ensayo no tiene respuesta, o tres corridas
  seguidas, el ensayo se corta y lo dice. Una corrida que contesta el programa solo no
  reinicia la cuenta (aceptado por R, P56). El motivo se muestra entero una vez; después,
  "por lo mismo que más arriba".
- (C3, v2) Segundo cambio en el intérprete: dentro de `if self.ensayando` se guarda el texto
  del error en la anotación de la consulta (`motivo`). Fuera de un ensayo y en `probar` no
  cambia nada. El texto pasa por los mismos errores que ya tapan la clave.
- (C3, v2) Con `MATE_IA_PROPIA` y sin `MATE_MODELO` el ensayo no empieza (código 2). La
  validación quedó en una sola función, `modelo_de_ia_propia()`, que usa también
  `pedir_a_la_ia_propia`.
- (C3, v2) Con `--ia-simulada` no se dejan lecciones propuestas (una lección no cambia un
  texto preparado) y lo dice. Las pruebas de propuestas usan la IA de mentira (`ia`).
- (C3, v2) Comillas en las reglas: si todo el texto son tramos entre comillas separados por
  `|`, coma, `o` o `ni`, cada tramo es una opción; si no, se parte por `|` y se saca el par
  de comillas que envuelve cada opción (rectas, tipográficas, « » y simples). `"a" y "b"`, las
  comillas a medias y una opción que abre comilla y no cierra dan error con renglón. Sin
  comillas todo sigue igual (`si o no` es un solo texto). Constante: `_PARES_DE_COMILLAS`
  (`_COMILLAS` ya era del analizador).
- (C3, v2) Regla mal tipeada: si antes de los dos puntos hay de 1 a 5 palabras y la última es
  "decir" o una forma mal escrita (desir, dezir, decri, deicr, dcir, deir, decirr), es un
  error con su renglón. Costo aceptado: una pregunta de cliente con "decir:" también (P54).
  Una regla con guion o asterisco de lista adelante se acepta.
- (C3, v2) Si la lección del caso ya está aprobada y el caso vuelve a fallar, el informe dice
  que no alcanzó y manda a `lecciones`, no a `propuestas`.
- (C3, v2) `propuestas` sugiere sus tres órdenes con `orden_para_esta_carpeta()`. El aviso
  del freno, `lecciones`, `corregir` y `bitacora` siguen con la ruta relativa (resto de P20).
- (C3, v2) `nuevo mostrador` sobre un mostrador sin archivo de casos no lo crea: dice de
  dónde copiarlo (sigue valiendo "nunca toca una carpeta donde ya está el programa").
- (C3, v2) El informe dice dónde entra la pregunta ("Cada pregunta se le escribe al programa
  donde pide: ..."); sale después de la primera corrida, que es cuando se sabe qué `leer()` es.
- (C3, v2) Las pruebas que miden el ancho de un renglón con la ruta de `mate.py` la acortan
  antes de medir: no dependen de en qué carpeta esté Mate.

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

### Cambio 2, vuelta 1 — NO cerrado (el revisor no aprobó: queda un problema medio, P29)

**Qué se implementó** (commit `b0b253f`, implementador)
- Orden `nuevo mostrador <nombre>`: crea `<nombre>.mate` y `<nombre>_precios.csv` en la
  carpeta actual, sin pisar nada, y muestra 4 pasos con los comandos enteros (`py`, `python`
  o `mate`, y la ruta de `mate.py` que sirve desde ahí). `nuevo` entra en `ORDENES_SABIDAS`.
- `leer_tabla`: error nuevo si un renglón repite los títulos; dice qué renglón borrar.
- Ejemplo 12: aviso de título mal escrito (P19) y de nombre muy corto ("Té"). Sigue en 20 de 20.
- README, `ayuda`, clase 12 del curso, encabezado del ejemplo 12, MEJORAS 122.
- 28 pruebas nuevas. Ninguna prueba vieja modificada (R).
- No se tocó: `docs/index.html`, la `guia`, `VERSION` (sigue en 0.5).

**Pruebas** (integrador, Linux, `MATE_SIN_REGISTRO=1`, sobre `b0b253f`)
- `pytest mate/pruebas mate/modelo`: 826 pasan, 0 fallan (vuelta anterior: 798); también 826
  con `MATE_ORDEN=py`. Solo con Python 3.13 (no hay pytest para 3.11 y 3.12; 3.10 y 3.14 no están).
- `probar mate/ejemplos`: 64 de 64, en 18 archivos (también con 3.11 y 3.12).
  `probar mate/curso`: 30 de 30, en 24 archivos. Ejemplo 12: "sin errores" y 20 de 20.
- El filtro de lo nuevo (`-k "nuevo or mostrador_creado or titulos or no_confunde"`) da 41, no
  los 42 del informe del implementador (R, P, I). Después de todo, `git status` vacío.

**Flujos cruzados comprobados por el integrador** (en carpetas temporales)
- `nuevo mostrador mi_negocio` en carpeta vacía: código 0, quedan solo los dos archivos;
  `verificar` "sin errores"; `probar` 7 de 7 (también con 3.11 y 3.12) y no deja archivos.
- Mostrador creado con modelo propio de mentira (127.0.0.1, `MATE_IA_PROPIA` + clave de
  mentira): los dos pedidos del cambio 1 dan $ 117.606,00 con envío sí y $ 175.000,00 sin
  envío, con 0 pedidos al servidor y sin crear memoria ni bitácora. Con el modelo diciendo
  "12 fideos salen $ 10,80 y te hago un descuento": "hola, que tienen?" llega (2 pedidos),
  salta el freno, sale la reserva y `propuestas` muestra 2 lecciones. La clave no aparece en
  la salida ni en ningún archivo de la carpeta. Lo mismo con el ejemplo 12 copiado.
- Sugerencias: Windows simulado (`os.name`="nt") con lanzador `py` o `MATE_ORDEN=py` da
  `py <ruta de mate.py>`; sin lanzador, `python <ruta>`; `MATE_ORDEN=mate` da `mate probar
  otro.mate`, en los pasos y en el encabezado del programa. Con `py` simulado la orden
  entera crea el mostrador, sus 3 comandos dicen `py ...` y pasa 7 de 7.
- `nuebo` sugiere `nuevo`; `nuevo` sola y el nombre repetido avisan con códigos 2 y 1; con
  memoria y bitácora ya creadas por `correr`, repetir la orden las nombra y no crea nada.
- Títulos repetidos en un mostrador creado: `correr` y `probar` dicen "borrá el renglón 3 entero".
- `ensayar` todavía no existe ("no conozco la orden", y la lista ya incluye `nuevo`): ese
  cruce queda para el cambio 3.

**Problemas** (R = revisor, P = agente de pruebas, I = integrador)

| # | Problema | Quién | Gravedad | Estado |
|---|---|---|---|---|
| P29 | Mostrador creado (y ejemplo 12): con un precio o stock vacío o con texto en la planilla, arranca como si nada y se corta con un error técnico (`pesos() espera numero...`) en la primera consulta que va a la IA. Solo `probar` lo avisa (6 de 7) | R; reproducido por I | media | pendiente (vuelta 2, obligatorio): que `revisar_planilla` lo diga al arrancar nombrando el producto, con la misma función que usa la prueba "tu planilla está bien cargada", más una prueba de `correr` con precio vacío. Ya estaba en el ejemplo 12 |
| P22 | Los mostradores creados heredan P22 ("Yerba sin palo": "12 yerbas sin envio" confirma el envío) y, por ser copias fijas, no reciben el arreglo. Las 7 pruebas no lo detectan | R, P; reproducido por I | media (R) / baja (P) | pendiente en el cambio 1 (vuelta 4). Para el coordinador: cerrarlo antes de que el dueño cree su mostrador, o avisarle que lo cree de nuevo |
| P20 | El aviso del freno y `propuestas` sugieren `python3 mate/mate.py ...` relativo, que no sirve desde la carpeta del mostrador; `nuevo mostrador` ahí mismo da la ruta completa | P; reproducido por I | baja | ya estaba antes; ahora se nota más. Pendiente para el implementador: usar `orden_para_esta_carpeta()` en esos avisos. I no lo arregló: `como_se_llama()` se usa en 28 lugares y hay pruebas que afirman el texto actual |
| P30 | Títulos repetidos con una columna de más o de menos: sale el error viejo de cantidad de columnas, sin decir que son los títulos | R | baja | pendiente (vuelta 2 si entra) |
| P31 | Una tabla con títulos numéricos y un renglón de datos igual (`1;2;3`) ahora da error | R | baja | aceptado: raro y documentado. Si se toca: no mirar cuando todos los títulos son números |
| P32 | Un nombre de más de 60 letras da un aviso que no dice que es por largo | R | baja | pendiente (vuelta 2 si entra) |
| P33 | "nuevo mostrador x" escrito en la charla sin `py` o `mate` adelante se manda a la IA (con `mate nuevo ...` sí se reconoce como comando); con `--ia-simulada` contesta "Decime el nombre del producto..." | P; visto por I | baja | pendiente, no exigido |
| P34 | La planilla "de muestra" es `ejemplos/precios.csv` como esté: si el dueño la editó, el mostrador nace con eso y puede no pasar `probar` (lo mismo con el ejemplo 12 editado) | P | baja | pendiente, no exigido: que la orden avise si la muestra no se puede leer |
| P35 | La prueba "tu planilla está bien cargada" muestra el aviso dos veces cuando falla ("dio ... y se esperaba nada") | P, R | baja | pendiente (se puede resolver junto con P29) |
| P36 | El informe del implementador dice 42 pruebas con el filtro y son 41 | R, P, I | baja | resuelto acá: el número correcto es 41 |
| P37 | Hay un `mate/errores_de_uso.txt` en el repositorio real (22/11 00:48, anterior al commit, dos renglones de "orden que no existe" con el nombre tapado): alguien corrió Mate sin `MATE_SIN_REGISTRO=1` | R; revisado por I | baja | descartado: git lo ignora (`mate/.gitignore`), no lo generan las pruebas ni `probar` (mismo md5 antes y después de todo) y no tiene datos. Recordatorio: correr siempre con `MATE_SIN_REGISTRO=1` |
| P38 | `orden_para_esta_carpeta` repite tres renglones de `clase_para_esta_carpeta` | R | — | descartado: no hace falta tocarlo (R) |
| P11 | `py`, las barras invertidas, los CRLF y el Bloc de notas siguen probados solo simulados | R, P, I | baja | pendiente del dueño: `py mate\mate.py nuevo mostrador mi_negocio` y copiar los 4 pasos |

El integrador no arregló nada en esta vuelta: P29 es lógica del ejemplo 12 y pide revisión
independiente; P20 no es chico (28 usos y pruebas que afirman el texto).

**Criterios de aceptación del cambio 2**

| Criterio | Estado | Evidencia |
|---|---|---|
| Crea programa y planilla, y pasan `verificar` y `probar` sin tocarlos | cumple | código 0, dos archivos, "sin errores", 7 de 7, sin archivos nuevos (R, P, I); también con ruta con espacios, nombres con tilde y eñe, CRLF simulado |
| Si algo ya existe, no pisa y lo dice | cumple | código 1, nombra lo que encontró, md5 iguales (P); con solo el programa, solo la planilla o solo la memoria (R, P); con memoria y bitácora reales (I) |
| Sigue andando con otros productos | cumple, con reserva | Tornillo/Martillo: 7 de 7, $ 54.000,00 con envío y $ 36.001,50 (R, P); envío en 1, 3, 24 y 500: 7 de 7. Reserva: precio vacío (P29) y productos con "sin" en el nombre (P22) |
| Títulos repetidos: error que dice qué renglón borrar | cumple | "borrá el renglón 3 entero" en `correr` y `probar` (R, P, I); con `sep=`, blancos, comas, tabulador, comillas, cp1252 (R, P) |
| Decidir dónde vive la plantilla y anotarlo | cumple | MEJORAS 122, comentario en `mate.py`, encabezado del ejemplo 12 y "Decisiones técnicas" de este registro |
| Para todo: pruebas, ejemplos, curso | cumple en Linux; Windows solo simulado | 826 / 64 de 64 / 30 de 30 |
| Para todo: nada nuevo sin usarlo, `probar` limpio, claves | cumple | `git status` vacío tras pytest y `probar`; `probar` del mostrador no deja archivos; clave de mentira ausente de salida y archivos (P, I). Único cambio para programas viejos: el error de títulos repetidos, a propósito |

**Para la vuelta 2**: P29 (obligatorio). Si entran: P30, P32, P35 y P20.
Para el coordinador: (1) orden de trabajo: la vuelta 4 del cambio 1 (P22) parte de `b0b253f`
y no cambia los títulos `# La regla del envío:` y `# ── Las pruebas` del ejemplo 12; conviene
cerrarla antes de que el dueño cree su mostrador; (2) preguntarle al dueño si está bien
`<nombre>_precios.csv` y que los mostradores ya creados no se actualicen solos; (3) sigue
pendiente su corrida en Windows, ahora también con `py mate\mate.py nuevo mostrador mi_negocio`.
Para el cambio 3: `ensayar` tiene que andar con lo que crea `nuevo mostrador`; `correr` deja
`<nombre>.memoria.json` y `.bitacora.txt` al lado (comportamiento de siempre), y `ensayar` no
debe cambiarlos. Sugerir sus comandos con `orden_para_esta_carpeta()`.

### Cambio 3, vuelta 1 — NO cerrado (quedan dos problemas medios: P39 y P40)

**Qué se implementó** (commit `32d50ae`, implementador)
- Orden `ensayar programa.mate casos.txt`: le hace al programa cada pregunta del archivo y
  muestra cuántos casos pasaron y, de cada uno que falló, la pregunta con su renglón, lo que
  contestó y la regla que no cumplió. Código 0 si pasan todos, 1 si alguno falla, 2 si la
  orden o el archivo están mal escritos. `ensayar` entra en `ORDENES_SABIDAS`.
- Anda con `--ia-simulada` (también `=archivo`), `MATE_IA_PROPIA` y Claude; antes de la
  primera consulta dice quién contesta y hasta cuántas consultas puede hacer.
- `--veces=N` (1 a 20): "pasó 4 de 5"; un caso pasa solo si pasó todas las veces.
- No guarda memoria ni bitácora; los casos que fallan quedan como lección propuesta.
- `mate/ejemplos/casos.txt` con las cinco preguntas reales del dueño. `nuevo mostrador` crea
  además `<nombre>_casos.txt` y suma el paso 5 "Ensayarlo".
- README, `ayuda`, una línea en la `guia`, clase 12 del curso, encabezado del ejemplo 12 (3
  renglones de comentario), MEJORAS 123.
- 38 pruebas nuevas. Pruebas viejas tocadas (ninguna afirma menos; R y P lo confirmaron):
  `test_el_ejemplo_del_agente_que_aprende` (exceptúa `casos.txt`), tres de `nuevo mostrador`
  (tres archivos en vez de dos) y `test_una_opcion_parecida_a_borrar_se_sugiere` (la lista de
  opciones ahora incluye `--veces`).
- No se tocó: `docs/index.html`, `curso/README.md`, `VERSION` (sigue en 0.5; el README ya dice 0.6).

**Pruebas** (integrador, Linux, `MATE_SIN_REGISTRO=1`, sobre `32d50ae`)
- `pytest mate/pruebas mate/modelo`: 864 pasan, 0 fallan (vuelta anterior: 826). Python 3.13.
- `probar mate/ejemplos`: 64 de 64, en 18 archivos. `probar mate/curso`: 30 de 30, en 24 archivos.
- Después de todo, `git status --short` vacío; no hay memoria ni bitácora en `mate/ejemplos`.

**Flujos cruzados comprobados por el integrador** (en carpetas temporales)
- `nuevo mostrador mi_negocio` en carpeta vacía y el comando del paso 5 tal cual: 5 de 5,
  código 0, la carpeta sigue con sus 3 archivos; `verificar` "sin errores", `probar` 7 de 7.
- Mostrador creado con modelo propio de mentira (127.0.0.1, `MATE_IA_PROPIA` + `MATE_MODELO`
  + clave de mentira): con memoria ya creada por `correr`, un ensayo de 5 de 5 deja el mismo
  md5 (88147b50...). Con el modelo diciendo "Si, tenemos cafe a buen precio." y `--veces=2`:
  `✗ tenes cafe?: pasó 0 de 2`, 4 de 5, código 1, una sola propuesta visible con
  `propuestas`. La clave no aparece en la salida ni en ningún archivo de la carpeta.
- Ejemplo 12 real con ese modelo de mentira: 5 de 5, 1 consulta, y no deja archivos en
  `mate/ejemplos` (`git status --ignored` igual que antes).
- Lección aprobada (`propuestas ... aprobar 1`) y ensayo de nuevo: la lección viaja en el
  pedido al modelo; el caso sigue fallando y el mensaje manda a `propuestas` (P41).
- Sugerencias con `py` (Windows simulado, lanzador `py`): `ensayar` sin quién conteste,
  `ensayar` sola, el aviso de propuestas y el paso 5 de `nuevo mostrador` dicen
  `py <ruta de mate.py> ...`; el encabezado de `kiosco_casos.txt` y el de `kiosco.mate`
  también. Con `MATE_ORDEN=mate`: `mate ensayar ...`. `ensallar` sugiere `ensayar`.
- `ensayar` del ejemplo 12 con `--ia-simulada` también da 5 de 5 con Python 3.11 y 3.12.
- Reproducidos por el integrador: P39 (modelo apagado: 5 de 5 y código 0), P40 (regla con
  comillas pasa siempre), P41 y P20.

**Problemas** (R = revisor, P = agente de pruebas, I = integrador)

| # | Problema | Quién | Gravedad | Estado |
|---|---|---|---|---|
| P39 | Si el modelo no contesta (apagado, 404 por `MATE_MODELO` mal escrito), con los casos de muestra el ensayo da "5 de 5 casos pasaron" y código 0; el motivo no se muestra. El mostrador ataja la falla y "tenes cafe?" solo tiene reglas `no puede decir` | R (media), P (baja); reproducido por I | media | pendiente (vuelta 2, obligatorio): un caso cuya consulta quedó sin respuesta no cuenta como pasado, se marca aparte ("no se pudo ensayar: la IA no contestó") con el motivo una vez y código distinto de 0; mejor, cortar al primer fallo de conexión o configuración. Con prueba contra 127.0.0.1 apagado o con 404 |
| P40 | Una regla escrita con comillas, como las muestra el informe y la lección propuesta, no funciona: `no puede decir: "decime"` pasa siempre y `tiene que decir: "sin envío"` no se cumple nunca | P; reproducido por I | media | pendiente (vuelta 2, obligatorio): en `regla_de_caso`, sacar las comillas que envuelven cada opción (rectas y tipográficas) o dar error con renglón; con prueba |
| P41 | Si la lección ya fue aprobada y el caso sigue fallando, el informe manda a `propuestas`, donde ya no está | R; reproducido por I | baja | pendiente: decir que ya está aprobada y no alcanzó (cambiarla con `lecciones` o `corregir`, o pasar la regla al programa o a un freno) |
| P42 | Con `MATE_IA_PROPIA` y sin `MATE_MODELO` el ensayo arranca y repite el mismo error en cada caso | R | baja | pendiente (junto con P39): revisarlo antes de empezar, código 2 |
| P43 | Con `--ia-simulada` también deja lecciones propuestas, que no cambian un texto fijo | R | baja | pendiente: no proponer y decirlo, o aclarar que hay que ensayar con la IA de verdad (decisión de R a la pregunta 4 del implementador) |
| P44 | Programa cuyo primer `leer()` no es la consulta: la pregunta cae ahí; da "Contestó: (nada)" o pasa por casualidad, sin aviso | R, P | baja | aceptado como límite; pendiente decirlo en el manual con esas palabras y, si entra, avisar cuando no mostró nada entre el primer `leer` y el segundo |
| P45 | Una regla mal tipeada ("no puede desir:", "tiene q decir:", "- tiene que decir:") se toma como una pregunta más y gasta una consulta; el error puede apuntar al renglón equivocado | P | baja | pendiente (vuelta 2 si entra): avisar "parece una regla" con su renglón |
| P46 | Con `--veces` y un freno, el renglón "Saltó un freno..." sale repetido y el resumen cuenta corridas como preguntas | P | baja | pendiente (vuelta 2 si entra) |
| P47 | Los mostradores creados antes de este cambio no tienen `_casos.txt` y `nuevo mostrador` no dice cómo conseguirlo | P, R | baja | pendiente: una línea en el README (copiar `mate\ejemplos\casos.txt` al lado del mostrador) |
| P48 | El informe final no dice que las consultas de verdad del ensayo no quedan en la cuenta del día ni en `bitacora` | R | baja | pendiente: agregar el renglón. La decisión de no contarlas queda (criterio "no cambia la memoria") |
| P20 | `propuestas` sigue sugiriendo `python3 mate/mate.py ... aprobar 1` relativo, y ahora `ensayar` manda ahí al dueño | R, P; reproducido por I | baja | ya estaba antes; pesa más. Pendiente para el implementador (`orden_para_esta_carpeta()`). I no lo arregló por lo mismo que en el cambio 2 |
| P49 | `VERSION` sigue en 0.5 y el README ya dice "(0.6)" | R | baja | pendiente del coordinador, al integrar |
| P50 | Al probar con una clave falsa de Claude, la copia del revisor hizo un pedido real a Anthropic, que lo rechazó | R | — | descartado: sin costo y sin datos del dueño. Recordatorio: para Claude usar la IA de mentira de las pruebas o cambiar `IA_DIRECCION` |
| P51 | Con Ctrl+C a mitad de un ensayo no se guardan las propuestas de los casos ya fallados; los frenos que saltan en un ensayo no dejan su propia propuesta | implementador | baja | aceptado: anotado en MEJORAS 123 como lo que quedó afuera |
| P11 | `py`, PowerShell 5.1 y el Bloc de notas siguen probados solo simulados; tampoco se probó contra Claude ni un Ollama de verdad; Python 3.10 y 3.14 no están en la máquina | R, P, I | baja | pendiente del dueño |

El integrador no arregló nada en esta vuelta: P39 y P40 cambian qué cuenta como caso pasado y
cómo se lee una regla, y piden revisión independiente.
Dudas del implementador ya contestadas por R: `_FinDelEnsayo` no se puede atajar (probado con
`leer` dentro de `intentar ... si falla`); arrancar con Claude sin confirmar está bien; la
redacción fija de la lección sirve como borrador.

**Criterios de aceptación del cambio 3**

| Criterio | Estado | Evidencia |
|---|---|---|
| Corre los casos y muestra cuántos pasaron y, de cada uno que falló, pregunta, respuesta y regla | cumple, con reserva | `✗ tenes cafe?   (renglón 39 ...)`, "Contestó: ...", "No cumple: ...", 4 de 5, código 1 (R, P, I); archivos CRLF, cp1252, UTF-16 y con marca; errores con renglón y código 2 (R, P). Reserva: reglas con comillas (P40) |
| Anda con `--ia-simulada`, modelo propio y Claude; avisa antes cuántas consultas | no cumple (R) / cumple (P) | Arranca con las tres y avisa antes; el tope de 50 corta en 50 pedidos exactos (P); Claude solo con la IA de mentira. No cumple cuando el modelo propio no contesta: 5 de 5 y código 0 (P39) |
| `--veces=N` informa "pasó 4 de 5" | cumple | "pasó 0 de 2", "pasó 2 de 5", "pasó 20 de 20" (R, P, I); `-k paso_4_de_5`; `--veces` mal escrito o con otra orden: código 2 |
| No cambia la memoria; los casos que fallan quedan propuestos | cumple | md5 de memoria y bitácora iguales tras ensayos con consultas de verdad (R, P, I); sin memoria previa no la crea si pasan todos; una sola propuesta por caso, no se duplica; lo que escribe el programa no llega al disco |
| Anda con el ejemplo 12 y con lo que crea `nuevo mostrador` | cumple | 5 de 5 en los dos, sin tocarlos y sin archivos nuevos (R, P, I); también con carpeta con espacios y nombres con tilde (P) |
| Para todo: pruebas, ejemplos, curso | cumple en Linux; Windows solo simulado | 864 / 64 de 64 / 30 de 30 |
| Para todo: nada nuevo sin usarlo, `probar` limpio, claves | cumple | `git status` vacío tras pytest, `probar` y `ensayar`; solo dos condiciones cambian en el intérprete; clave de mentira ausente de salida y archivos (R, P, I) |

**Para la vuelta 2**: P39 y P40 (obligatorios). Si entran: P42, P41, P43, P45, P46, P47, P48,
P44 y P20.
Para el coordinador: (1) `VERSION` (P49); (2) siguen abiertos P22 (cambio 1) y P29 (cambio 2),
y los mostradores ya creados no reciben esos arreglos ni el archivo de casos; (3) sigue
pendiente la corrida del dueño en Windows, ahora también con
`py mate\mate.py ensayar mi_negocio.mate mi_negocio_casos.txt --ia-simulada` y con su Ollama.

### Cambio 3, vuelta 2 — cerrado (R y P aprobaron; quedan solo problemas bajos)

**Qué se implementó** (commit `0e200b0`, implementador; toca `mate.py`, `test_mate.py`,
README, MEJORAS 123 y `ejemplos/casos.txt`)
- P39: un caso cuya consulta quedó sin respuesta ya no pasa: se marca `? ...: no se pudo
  comprobar`, con el motivo una vez, código 1, y el ensayo se corta si falla la primera
  consulta o tres seguidas.
- P40: las reglas con comillas, como las muestra el informe, se leen bien; las comillas a
  medias dan error con renglón.
- P42 (sin `MATE_MODELO`: código 2, un aviso), P41 (lección ya aprobada: "no alcanzó" y la
  orden `lecciones`), P43 (`--ia-simulada` no propone), P45 (regla mal tipeada: error con su
  renglón), P46 (el freno sale una vez; el resumen cuenta preguntas), P44 (dice dónde entra
  la pregunta y avisa si el programa volvió a pedir sin mostrar nada), P47 (de dónde copiar
  los casos), P48 (renglón de la cuenta del día), P20 solo en `propuestas`.
- 15 pruebas nuevas. Pruebas viejas cambiadas (ninguna afirma menos; R revisó todos los
  renglones borrados): tres de propuestas pasaron de `--ia-simulada` a la IA de mentira
  (P43); dos esperan `? ... no se pudo comprobar` en vez de `✗` (P39); la de Claude espera
  como último renglón el aviso de la cuenta del día (P48).
- El archivo de casos de muestra ganó un renglón de nota: "tenes cafe?" pasó del renglón 39
  al 40.

**Arreglo del integrador** (en este commit)
- P52: `test_ensayar_muestra_cada_caso_que_fallo_y_lo_deja_propuesto` medía el ancho de un
  renglón que lleva la ruta de `mate.py` y fallaba con Mate en una carpeta honda. Ahora
  acorta esa ruta antes de medir y comprueba aparte que el renglón de `lecciones` esté. No
  afirma menos. Evidencia: copia de `0e200b0` en una ruta larga, esa prueba falla; con la
  prueba arreglada, 879 pasan ahí y 879 en `/home/user/mate`.

**Pruebas** (integrador, Linux, Python 3.13, `MATE_SIN_REGISTRO=1`)
- `pytest mate/pruebas mate/modelo`: 879 pasan, 0 fallan (vuelta anterior: 864).
- `probar mate/ejemplos`: 64 de 64, en 18 archivos. `probar mate/curso`: 30 de 30, en 24 archivos.
- `git status --short` vacío después de todo (antes del arreglo de P52); no hay memoria ni
  bitácora en `mate/ejemplos`.

**Flujos cruzados comprobados por el integrador** (carpetas temporales, servidores de mentira
en 127.0.0.1)
- `nuevo mostrador mi_negocio` en carpeta vacía: `verificar` "sin errores", `probar` 7 de 7,
  y el comando del paso 5 da 5 de 5, código 0; la carpeta sigue con 3 archivos.
- Ese mostrador con el modelo apagado (`127.0.0.1:9`): `? tenes cafe?: no se pudo comprobar`,
  motivo, "El ensayo se cortó ahí", 4 de 5, código 1, 3 archivos. Con 404 y clave de
  mentira: igual, y la clave sale como "(la clave)"; no está en la salida ni en archivos.
- Sin `MATE_MODELO`: un solo aviso, código 2.
- Modelo que contesta bien: 5 de 5, código 0, sin archivos nuevos. Modelo que dice "Si,
  tenemos cafe a buen precio.": 4 de 5, código 1, una propuesta; con `--veces=2` "pasó 0 de
  2" y la memoria queda con el mismo md5 (1d7c50d2...). `propuestas` da la orden de aprobar
  con la ruta completa. Después de `aprobar 1`, el ensayo deja el md5 igual (3c68c4d1...),
  dice "ya tiene aprobada... no alcanzó" y da la orden `lecciones`; la lección viaja en el
  pedido al modelo.
- Ejemplo 12 real con el modelo de mentira: 5 de 5; con el modelo apagado: 4 de 5 y código
  1. En los dos, `git status --ignored` igual que antes.
- Sugerencias con `py` (Windows simulado, lanzador `py`): `ensayar` sin quién conteste, el
  aviso de propuestas, las dos órdenes de `propuestas`, la orden `lecciones` del caso ya
  aprobado y el `nuevo mostrador` que no pisa dicen `py <ruta de mate.py> ...`. Con
  `MATE_ORDEN=mate`: `mate proponer ...`.
- `--ia-simulada=r.txt` con una respuesta mala: el caso falla, "no quedan lecciones
  propuestas" y no se crea memoria.

**Problemas** (R = revisor, P = agente de pruebas, I = integrador)

| # | Problema | Quién | Gravedad | Estado |
|---|---|---|---|---|
| P39 | Modelo que no contesta daba 5 de 5 | R, P (v1) | media | resuelto: apagado, 404, 500, respuesta sin texto, falla intermitente y corte a la tercera (R, P, I) |
| P40 | Reglas con comillas | P (v1) | media | resuelto: 45 formas de regla (R); rectas, tipográficas, « » y simples (P) |
| P41 | Lección ya aprobada mandaba a `propuestas` | R (v1) | baja | resuelto (R, P, I) |
| P42 | Sin `MATE_MODELO` repetía el error en cada caso | R (v1) | baja | resuelto: código 2, un aviso. Queda el prefijo (P55) |
| P43 | `--ia-simulada` dejaba propuestas | R (v1) | baja | resuelto (R, P, I) |
| P44 | Primer `leer()` que no es la consulta | R, P (v1) | baja | límite aceptado; resuelto el aviso: informe, pista y README |
| P45 | Regla mal tipeada tomada como pregunta | P (v1) | baja | resuelto; efecto lateral en P54 |
| P46 | Freno repetido con `--veces` | P (v1) | baja | resuelto (P; R solo por su prueba) |
| P47 | Mostradores viejos sin archivo de casos | P, R (v1) | baja | resuelto: aviso en `nuevo mostrador` y README |
| P48 | Faltaba decir que el ensayo no entra en la cuenta del día | R (v1) | baja | resuelto; roza con P53 |
| P20 | Órdenes sugeridas con ruta relativa | R, P | baja | resuelto en `propuestas`. Pendiente en el aviso del freno, `lecciones`, `corregir` y `bitacora`; R pide empezar por `lecciones` y `corregir`. No traba |
| P52 | Una prueba nueva dependía del largo de la ruta donde está Mate (878 en vez de 879) | R, P | baja | resuelto por I en este commit |
| P53 | Caso sin comprobar por el tope del día: el resumen culpa a la IA, no dice que se sube con `consultas_por_dia`, y se lee contradictorio con "no entran en la cuenta del día" | R | baja | pendiente para el implementador |
| P54 | Una pregunta de cliente con "decir:" ("me podes decir: tenes cafe?") da error de regla | R, P | baja | corte aceptado; pendiente agregar al error "si es una pregunta del cliente, sacale los dos puntos" |
| P55 | El aviso de que falta `MATE_MODELO` empieza con `consultar_ia(): ` | R, P; visto por I | baja | pendiente para el implementador |
| P56 | "Tres veces seguidas" también cuenta fallas separadas por casos que no consultan | R (leyendo el código) | baja | aceptado como está; no se armó un caso que corte de más |
| P57 | El comentario de `preguntar_al_programa` quedó con un renglón mal cortado | R | baja | pendiente, de prolijidad |
| P58 | `no puede decir: rebaja ni decime` (sin comillas) es un solo texto y pasa siempre; el informe muestra las reglas con `ni` y `o` | P | baja | pendiente: avisar, sin frenar, cuando una regla sin comillas ni barra lleva ` ni ` u ` o ` |
| P59 | Una comilla suelta al final (`decime"`) pasa sin aviso; al principio sí da error | P | baja | pendiente. Ojo: `tele de 32"` tiene que seguir valiendo |
| P60 | La carpeta temporal es compartida: P y otro agente se pisaron carpetas y un servidor de prueba | P | — | nada en el repositorio. Para el coordinador: una carpeta propia por agente |
| P49 | `VERSION` sigue en 0.5 y el README dice 0.6 | R (v1) | baja | pendiente del coordinador |
| P11 | Sin Windows real, sin Claude ni Ollama de verdad; pytest solo con Python 3.13 (3.11 y 3.12 no tienen pytest en esta máquina; 3.10 y 3.14 no están) | R, P, I | baja | pendiente del dueño |

Dudas del implementador ya contestadas por R: el tope del día como "sin comprobar" está bien
(falta P53); el corte a las tres está bien; no hace falta "N casos no se corrieron"; el error
en `"a" y "b"` es la decisión correcta. Para el especialista en seguridad: confirmar que
ningún `e.mensaje` de `consultar_ia` puede traer la clave, porque ahora se muestra en el
informe (R probó el modelo propio con la clave devuelta en un 500; la rama de Claude no).

**Criterios de aceptación del cambio 3**

| Criterio | Estado | Evidencia |
|---|---|---|
| Corre los casos y muestra cuántos pasaron y, de cada uno que falló, pregunta, respuesta y regla | cumple | `✗ tenes cafe?   (renglón 40 ...)`, "Contestó: ...", "No cumple: ...", 4 de 5, código 1 (R, P, I); `no puede decir: "decime"` da 0 de 1 (R, P); regla mal tipeada: error con su renglón, código 2 |
| Anda con `--ia-simulada`, modelo propio y Claude; avisa antes cuántas consultas | cumple | Simulada 5 de 5; modelo de mentira 5 de 5; apagado o 404: `?`, 4 de 5, código 1 (R, P, I). Claude solo de mentira: avisa antes y corta en 50 pedidos (P) |
| `--veces=N` informa "pasó 4 de 5" | cumple | "pasó 0 de 2" (R, I), "pasó 3 de 5" (P), "pasó 0 de 3, y 1 sin comprobar" (R); `-k paso_4_de_5` sin cambios |
| No cambia la memoria; los casos que fallan quedan propuestos | cumple | md5 igual al repetir y después de aprobar (R, P, I); una sola propuesta; con simulada, apagado o 404 no se crea memoria |
| Anda con el ejemplo 12 y con lo que crea `nuevo mostrador` | cumple | 5 de 5 en los dos, sin archivos nuevos (R, P, I) |
| Para todo: pruebas, ejemplos, curso | cumple en Linux; Windows solo simulado | 879 / 64 de 64 / 30 de 30 |
| Para todo: nada nuevo sin usarlo, `probar` limpio, claves | cumple | Una línea nueva en el intérprete, solo con `ensayando`; `git status` vacío tras pytest, `probar` y `ensayar`; clave de mentira ausente de salida y archivos (R, P, I) |

**Lo que queda**: P53, P54, P55, P57, P58, P59 y el resto de P20, todos bajos; entran en una
vuelta corta o junto con lo pendiente de los cambios 1 y 2.
Para el coordinador: (1) `VERSION` (P49); (2) siguen abiertos P22 (cambio 1) y P29 (cambio 2);
(3) revisión de seguridad del conjunto, con la pregunta de arriba; (4) la corrida del dueño en
Windows, con `py mate\mate.py ensayar mi_negocio.mate mi_negocio_casos.txt` y su Ollama
prendido y apagado; (5) una carpeta temporal por agente (P60).
