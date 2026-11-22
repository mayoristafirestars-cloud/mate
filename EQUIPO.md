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

### Vuelta de cierre — cerrada (R y P aprobaron; quedan solo problemas bajos)

Una vuelta corta sobre lo que el "Estado final" dejaba abierto: los dos medios (P22 y P29) y
dos bajos (P68 y P49). Toca los cambios 1 y 2 a la vez, porque los dos arreglos van al
ejemplo 12 y a la copia que hace `nuevo mostrador`.

**Qué se arregló** (commit `e78f2e9`, implementador; toca el ejemplo 12, `mate.py`,
`test_mate.py`, README, MEJORAS 121 y 123 y `docs/index.html`)
- **P22** (ejemplo 12 y mostradores creados): con un producto que tiene "sin", "no", "ni" o
  "nada" en el nombre, "12 yerbas sin envio" o "no me lo mandes" ya no contestan "Con envío:
  sí". Una palabra de negación cuenta como parte del nombre solo si atrás viene la palabra
  que le sigue en el nombre ("sin palo"); si no, es del cliente y niega el envío. Funciones
  nuevas: `las_que_niegan()`, `puede_negar()`, `dicha_del_nombre()`; `es_del_nombre()` cambió
  de parámetros.
- P22, cambio de comportamiento: la misma regla se usa para contar cuántas palabras del
  nombre dijo el cliente. Con "Yerba mate" y "Yerba sin palo" en la planilla, "12 yerbas sin
  envio" ahora pregunta "Tengo más de uno..." (antes cotizaba la "sin palo" y confirmaba el
  envío). Con una sola yerba cotiza esa, sin envío.
- **P29** (ejemplo 12 y mostradores creados): `revisar_planilla()` revisa todos los renglones
  con la función nueva `celdas_mal_cargadas()`. Con un precio o stock vacío o con texto el
  mostrador no atiende y dice al arrancar: "Mostrador: así no puedo atender. En precios.csv,
  el precio de 'Azúcar' no es un número: está vacío (es el producto número 2 de la lista)..."
  y cómo arreglarlo. Muestra hasta 5 avisos y dice cuántos más hay. Se eligió frenar el
  arranque, no saltear el renglón. Dice "producto número N" y el nombre, no el renglón del
  archivo, porque `leer_tabla` saltea los renglones en blanco.
- **P68** (`mate.py`): el encabezado de `<nombre>_casos.txt`, el paso 5 de `nuevo mostrador`
  y el encabezado del programa creado avisan que los casos son para la planilla de muestra y
  que hay que cambiarlos si se cambia la planilla. El archivo de casos tiene 3 renglones más:
  "tenes cafe?" pasó del renglón 40 al **43**.
- **P49**: `VERSION = "0.6"`. El README dice "Versión 0.6.", tiene "Qué cambió en la 0.6"
  (antes de la de la 0.5, que queda como historia) y "Límites de la versión 0.6";
  `docs/index.html` dice "Mate 0.6".
- De paso, **P35**: la prueba "tu planilla está bien cargada" del mostrador creado usa la
  misma `revisar_planilla()` del arranque y muestra el aviso una sola vez.
- Pruebas: 2 nuevas en el ejemplo 12 (de 20 a 22) y 5 en `test_mate.py`. Pruebas viejas
  tocadas: la de versión (0.5 pasa a 0.6 y afirma más), "20 de 20" pasa a "22 de 22", y
  "renglón 40" pasa a "renglón 43". Ninguna se sacó ni afirma menos (R y P miraron los
  renglones borrados).

**Quién revisó y quién probó**

| Quién | Veredicto | Cómo trabajó |
|---|---|---|
| Revisor independiente (R) | **aprueba**: ningún problema alto ni medio; 5 bajos (uno era "falta anotar la vuelta acá") | leyó `git diff f181ff2..e78f2e9`; corrió todo en una copia temporal propia, que borró; repositorio sin tocar |
| Agente de pruebas (P) | **aprueba**: ningún problema alto ni medio; 8 bajos (2 nuevos, 6 ya estaban) | copia propia del repositorio en `e78f2e9`; usó el mostrador creado como el dueño; repositorio sin tocar |
| Integrador (I) | no aprueba ni desaprueba: corrió todo junto y anotó | sin tocar código ni pruebas; en este commit solo cambia este archivo |

**Evidencia**
- P22 (R): ejemplo 12 viejo contra nuevo, planilla de 13 productos (Yerba sin palo,
  Galletitas sin sal, Arroz no se pasa, Fideos sin TACC, Pan sin sal, Cerveza sin alcohol,
  Agua sin gas, Jugo nada...) y 39 frases. El viejo decía "Con envío: sí" a "12 yerbas sin
  envio", "12 yerba mate sin envio", "12 yerba sin palo sin flete", "12 arroz no me lo
  mandes" y otras cuatro; el nuevo da solo el total o pregunta cuál. Con la planilla de
  muestra, 147 frases de las pruebas dan respuestas idénticas con el código viejo y el nuevo.
- P22 (P): más de 170 frases en planillas difíciles; ninguna frase negada contestó "Con
  envío: sí", salvo "s/envio" (P77, ya pasaba con cualquier planilla). Sobre 66 frases
  comparadas con la versión anterior cambiaron 17: 16 eran "sí" falsos y 1 es P71. Con la
  planilla de muestra, 40 frases dan exactamente lo mismo que antes ($ 117.606,00 con envío
  sí; $ 175.000,00 sin envío).
- P22: el "sin" del nombre no apaga un envío pedido: "12 yerba sin palo con envio",
  "mandame 12 yerba sin palo", "12 cerveza sin alcohol con envio", "12 pan no blanco con
  envio" dan "Con envío: sí" (R, P). Las tres frases pedidas en "Para la vuelta 4" están en
  la prueba del ejemplo y en `test_mate.py` (R).
- P29 (R, P): precio vacío, con texto ("consultar", "si", "x", "N/A", "#¡REF!", "14500
  pesos"), stock vacío o con texto: el mostrador no entra a la charla y da el aviso con el
  nombre del producto; no sale ningún error de `pesos()`, con y sin `--ia-simulada`. Siguen
  valiendo "$35.000.-", "35.000$", "$ 1.234.567,89" y stock "1.000". Con renglones en blanco
  en el medio el número de producto sale bien.
- Mostrador recién creado (R, P): tres archivos, `verificar` "sin errores", `probar` 7 de 7,
  `ensayar` 5 de 5. Hereda P22 y P29; con un precio vacío `probar` da 6 de 7 con el aviso
  una sola vez. Su lógica es la del ejemplo 12: solo cambia el nombre de la planilla (P).
- P68 (R, P): los tres avisos están; con la planilla cambiada `ensayar` da 3 de 5, que es lo
  que ahora se avisa. P49 (R, P): `--version` dice "Mate 0.6"; README y `docs/index.html`
  coinciden. El README coincide con lo que hace el programa, salvo la promesa algo amplia
  del "sin" en el nombre (P70).

**Pruebas** (integrador, Linux, Python 3.13.18, `MATE_SIN_REGISTRO=1`, sobre `e78f2e9`)
- `python3 -m pytest mate/pruebas mate/modelo -q -p no:cacheprovider`: 883 pasan, 0 fallan
  (antes 879).
- `probar mate/ejemplos`: 66 de 66, en 18 archivos (antes 64). `probar mate/curso`: 30 de 30,
  en 24 archivos. Ejemplo 12 solo: 22 de 22.
- Los mismos números dieron el implementador, R y P, cada uno en su copia. Después de las
  tres corridas `git status --short` quedó vacío.

**Comprobado de nuevo por el integrador** (carpeta temporal propia, `--ia-simulada`)
- `nuevo mostrador mi_negocio`: tres archivos, `verificar` "sin errores", `probar` 7 de 7,
  `ensayar` 5 de 5; el paso 5 trae el "Ojo: esos casos son de muestra..."; "tenes cafe?"
  está en el renglón 43 del archivo creado (y sigue en el 42 de `mate/ejemplos/casos.txt`).
- Planilla con Yerba mate, Yerba sin palo y Azúcar: "12 yerbas sin envio" pregunta cuál;
  "12 yerba mate sin envio" da $ 420.000,00 sin frase de envío; "12 yerba sin palo sin
  flete" da $ 42.000,00 sin frase de envío; "12 yerba sin palo con envio" da envío sí; "12
  azucar no me lo mandes" da $ 117.606,00 sin frase de envío.
- Planilla con el precio del azúcar vacío: el aviso "así no puedo atender..." nombra
  `mi_negocio_precios.csv` y 'Azúcar', no atiende, `probar` da 6 de 7, y `ensayar` muestra
  el aviso y después "no pude ensayar: ..." (P72). La carpeta sigue con 3 archivos.
- No se repitieron en esta vuelta los flujos con un modelo de mentira ni la revisión de
  seguridad: valen los del cierre anterior, sobre `5ef3e8f`. El commit `e78f2e9` no pasó
  por el especialista en seguridad (en `mate.py` cambia `VERSION` y los textos que escribe
  `nuevo mostrador`).

**Estado de los problemas que entraron en la vuelta**

| # | Estado | Evidencia |
|---|---|---|
| P22 | resuelto (quedan P70 y P71, bajos) | R: 39 frases en 13 productos; P: más de 170 frases; I: las tres frases de "Para la vuelta 4" |
| P29 | resuelto (quedan P72, P73 y P78, bajos) | R, P, I: aviso al arrancar con el nombre del producto, sin error de `pesos()` |
| P68 | resuelto | R, P, I: encabezado de los casos, paso 5 y encabezado del programa |
| P49 | resuelto | R, P, I: "Mate 0.6" en `--version`, README y `docs/index.html` |
| P35 | resuelto de paso | R, P, I: el aviso sale una sola vez; 6 de 7 |

**Problemas que quedan de esta vuelta** (todos bajos; R = revisor, P = agente de pruebas,
Impl. = lo avisó el implementador)

| # | Problema | Quién | Gravedad | ¿Ya estaba? | Estado |
|---|---|---|---|---|---|
| P70 | Resto de P22: si el nombre trae un "no" seguido de una palabra que el cliente también usa para negar, se confirma el envío. Con "Arroz no se pasa", "12 arroz no se molesten en mandarlo" contesta "Con envío: sí". Con "sin palo", "sin sal", "sin TACC", "sin alcohol" o "sin gas" no pasa. El README ("Vale igual si el producto tiene una de esas palabras en el nombre") promete un poco de más | R | baja | sí | pendiente: **dice algo falso**, aunque con un nombre raro. Como mínimo, anotarlo en el README |
| P71 | Pedidos CON envío que quedan sin la frase del envío (solo el total): cuando el nombre termina en una palabra de negación ("Jugo nada", "Dulce de nada") o el cliente saltea o mete una palabra ("12 yerba sin el palo con envio", "12 quesos sin lactosa con envio" con "Queso sin TACC ni lactosa"). Antes daban "sí" | R, P, Impl. | baja | no | aceptado como decisión (ante la duda gana el no: calla, no dice nada falso). Pendiente: decirlo en el README y afirmarlo en una prueba |
| P72 | Con la planilla mal cargada, `ensayar` muestra el aviso claro y después un texto técnico ("no pude ensayar: ... terminó sin pedir nada por teclado ... leer() ..."), código 2; una prueba lo afirma. `correr` termina con código 0 cuando el mostrador se niega a atender. En el ejemplo 12 (no en un mostrador creado) `probar` con la planilla rota muestra el aviso y después 11 pruebas falladas, una con el viejo "pesos() espera numero..." | R, P, Impl.; visto por I | baja | no | pendiente. Lo ve el dueño, nunca el cliente. Es un cambio en `ensayar` |
| P73 | La revisión de la planilla solo mira que precio y stock sean números: un precio negativo se cotiza ("total -$ 105.000,00"), un precio 0 cotiza "$ 0,00", un stock "2,5" pasa, y un producto sin nombre se carga igual (o da el aviso "el precio de '' no es un número") | R, P, Impl. | baja | sí | pendiente. El total negativo sí llega al cliente |
| P74 | Con "Agua sin gas" y "Agua con gas" en la planilla, "12 agua sin gas con envio" contesta "Tengo más de uno... Decime cuál, con el nombre completo" aunque ya lo dijo (el "con" de "con envio" se toma del otro producto). Anda con "mandame 12 agua sin gas" | P | baja | sí | pendiente, no exigido: no dice nada falso |
| P75 | Si un producto EMPIEZA con "Sin" o "No" ("Sin TACC premezcla", "No me olvides"), casi cualquier pedido con "sin envio" o "no me lo mandes" contesta "Vamos de a un producto por vez". Para "No ..." el mostrador avisa al arrancar; para "Sin ..." no | P | baja | sí | pendiente, no exigido: deja de cotizar, no dice nada falso |
| P76 | Si el nombre de un producto incluye el de otro ("Gaseosa sin azúcar" y "Azúcar"), "12 gaseosas sin azucar con envio" contesta "Vamos de a un producto por vez". Anda con "12 gaseosas con envio" | P | baja | sí | pendiente, no exigido |
| P77 | "12 yerbas s/envio" contesta "Con envío: sí". Pasa con cualquier planilla, también la de muestra | P | baja | sí | pendiente: **dice algo falso**. Sumar "s/" a las negaciones o anotarlo en el manual |
| P78 | Un renglón con columnas de menos o de más ("Azúcar;bolsa"): el programa no arranca y sale el error de `leer_tabla`, que dice bien qué renglón es, pero con forma de error técnico y código 1; no es el aviso "así no puedo atender" | P; R lo vio y no lo contó | baja | sí | pendiente, no exigido: lo ve el dueño al arrancar |
| — | Este registro no tenía anotada la vuelta | R | baja | no | resuelto en este commit |

**Lo que el implementador dejó afuera a propósito**: los bajos P23, P24, P27, el resto de
P20 y los de seguridad P61 a P67; un mostrador creado antes de `e78f2e9` es una copia fija y
no recibe los arreglos (el dueño tiene que crearlo de nuevo); en el README quedan párrafos
que nombran la 0.5 como historia; nada probado en Windows real ni con Claude u Ollama de
verdad.

## Estado final

**Estado de hoy** (integrador, después de la vuelta de cierre, sobre `e78f2e9`; rama
`equipo/mate-0.6`, sin subir nada). Más abajo queda, como historia, el cierre anterior sobre
`5ef3e8f`: donde no coincidan, vale lo de acá arriba.

| Cambio | Vueltas | Estado | Quién aprobó | Qué queda |
|---|---|---|---|---|
| 1. Mostrador con reglas y comandos con `py` | 3 + cierre | **aprobado** | R y P, en la vuelta de cierre | solo bajos. P22 resuelto. Dos casos todavía dicen "Con envío: sí" a un pedido negado: P70 (nombre raro) y P77 ("s/envio") |
| 2. Orden `nuevo mostrador` | 1 + cierre | **aprobado** (ya sin reserva) | R y P, en la vuelta de cierre | solo bajos. P29 y P68 resueltos; los mostradores nuevos heredan los arreglos |
| 3. Orden `ensayar` | 2 | **aprobado** | R y P | solo bajos |
| Seguridad del conjunto | 1 | **aprobado sobre `5ef3e8f`** | especialista en seguridad | 7 bajos. No se repitió sobre `e78f2e9` |
| Versión | cierre | **0.6** | R y P | P49 resuelto |

No queda ningún problema alto ni medio abierto. Con eso se cumple la regla de este registro
para los tres cambios. La decisión de integrar la rama sigue siendo del coordinador.

**Números de las pruebas de hoy** (integrador, Linux, Python 3.13.18, `MATE_SIN_REGISTRO=1`,
sobre `e78f2e9`)

| Comando | Resultado | Cierre anterior (`5ef3e8f`) | Punto de partida (`7a4cf4f`) |
|---|---|---|---|
| `python3 -m pytest mate/pruebas mate/modelo -q -p no:cacheprovider` | 883 pasan, 0 fallan | 879 pasan, 0 fallan | 789 pasan, 1 falla (conocida) |
| `python3 mate/mate.py probar mate/ejemplos` | 66 de 66, en 18 archivos | 64 de 64, en 18 archivos | — |
| `python3 mate/mate.py probar mate/curso` | 30 de 30, en 24 archivos | 30 de 30, en 24 archivos | — |

Después de las tres corridas `git status --short` quedó vacío. Sin correr: Windows real,
Python 3.10, 3.11, 3.12 y 3.14 con pytest, Claude y Ollama de verdad.

**Pendientes de hoy**

Medios: ninguno.

Bajos que conviene mirar primero, porque el cliente ve algo que no es cierto:
- **P77**: "12 yerbas s/envio" contesta "Con envío: sí", con cualquier planilla.
- **P70**: con un producto como "Arroz no se pasa", "12 arroz no se molesten en mandarlo"
  contesta "Con envío: sí".
- **P73**: un precio negativo en la planilla se cotiza con total negativo.

Bajos que siguen abiertos (ninguno traba):
- Cambio 1: P23, P24, P27; P70, P71, P74, P75, P76, P77; P11 (nada probado en una Windows
  real).
- Cambio 2: P30, P32, P33, P34; P72, P73, P78; P31 aceptado. (P35 resuelto.)
- Cambio 3: P53, P54, P55, P57, P58, P59; P56 aceptado.
- Los tres: P20 (el aviso del freno, `lecciones`, `corregir` y `bitacora` sugieren
  `mate/mate.py` relativo).
- Seguridad: P61 a P67.

Para el coordinador y el dueño:
1. Decidir la integración de la rama: ya no hay medios abiertos.
2. Si el dueño ya creó su mostrador antes de `e78f2e9`, tiene que crearlo de nuevo: es una
   copia fija y no recibe los arreglos de P22 y P29.
3. La corrida del dueño en Windows sigue sin hacerse: `py mate\mate.py curso 99` (tiene que
   sugerir `py mate\mate.py curso`), `py -m pytest mate\pruebas mate\modelo -q -p
   no:cacheprovider`, `py mate\mate.py nuevo mostrador mi_negocio` con sus pasos, y `ensayar`
   con su Ollama prendido y apagado.
4. Decisiones del dueño que faltan: si está bien `<nombre>_precios.csv`; si devoluciones y
   cancelaciones van a la IA con frenos o a una respuesta fija; la regla de envío para un
   pedido con varios productos.
5. Anotar o resolver la excepción de P65 (`probar` y el adaptador de `mate/modelo`).
6. Si se quiere, una pasada del especialista en seguridad sobre `e78f2e9`.

Aclaraciones a lo escrito más abajo y en las vueltas:
- "tenes cafe?" está hoy en el renglón **43** del archivo que crea `nuevo mostrador` (era el
  40 hasta `e78f2e9`) y en el 42 de `mate/ejemplos/casos.txt`.
- El ejemplo 12 tiene hoy 22 pruebas (eran 20).
- `VERSION` es `"0.6"` y el README dice "Versión 0.6.".
- En "El flujo completo del dueño" de más abajo, "12 yerbas sin envio" con "Yerba sin palo"
  en la planilla ya no contesta "Con envío: sí"; y con un precio vacío el mostrador ya no se
  corta en "hola": avisa al arrancar.

### Cierre anterior, sobre `5ef3e8f` (historia: antes de la vuelta de cierre)

Cierre del integrador sobre `5ef3e8f` (rama `equipo/mate-0.6`, sin subir nada). En este commit
solo cambia este archivo: el integrador no tocó código ni pruebas en el cierre.

**Qué quedó aprobado y por quién**

| Cambio | Vueltas | Estado | Quién aprobó | Qué lo frena |
|---|---|---|---|---|
| 1. Mostrador con reglas y comandos con `py` | 3 | **NO aprobado** | nadie: R no aprobó la vuelta 3 | P22 (medio): con un producto "sin palo", "sin sal" o parecido, "12 yerbas sin envio" contesta "Con envío: sí". No hubo vuelta 4 |
| 2. Orden `nuevo mostrador` | 1 | **aprobado con reserva** | P aprobó. R no aprobó en su vuelta (P29); el coordinador lo dio por aprobado porque P29 y P22 ya estaban en el ejemplo 12 antes de este cambio | P29 (medio) y P22 siguen abiertos y los mostradores creados los heredan. No hubo vuelta 2 |
| 3. Orden `ensayar` | 2 | **aprobado** | R y P | solo problemas bajos |
| Seguridad del conjunto | 1 | **aprobado** | especialista en seguridad | ningún problema alto ni medio; 7 bajos |

Ojo con el cambio 2: la regla de este registro dice que un cambio se cierra cuando R y P no
tienen problemas medios, y P29 sigue ahí. Queda anotado como "aprobado con reserva" para que
el coordinador y el dueño lo decidan sabiendo eso; no es un cierre limpio.

**Números de las pruebas** (integrador, Linux, Python 3.13.18, `MATE_SIN_REGISTRO=1`, sobre `5ef3e8f`)

| Comando | Resultado | Punto de partida (`7a4cf4f`) |
|---|---|---|
| `python3 -m pytest mate/pruebas mate/modelo -q -p no:cacheprovider` | 879 pasan, 0 fallan | 789 pasan, 1 falla (conocida) |
| `python3 mate/mate.py probar mate/ejemplos` | 64 de 64, en 18 archivos | — |
| `python3 mate/mate.py probar mate/curso` | 30 de 30, en 24 archivos | — |

Después de las tres corridas `git status --short` quedó vacío y `mate/errores_de_uso.txt`
(ignorado por git, P37) tiene el mismo md5 que antes (`25cb241d...`). Ninguna falla, ni vieja
ni nueva. Sin correr: Windows real, Python 3.10, 3.11, 3.12 y 3.14 con pytest, Claude y Ollama
de verdad.

**El flujo completo del dueño, de punta a punta** (integrador, carpeta temporal propia,
modelo de mentira en 127.0.0.1)

| Paso | Qué dio |
|---|---|
| `nuevo mostrador mi_negocio` | código 0, tres archivos; `verificar` "sin errores"; `probar` 7 de 7 |
| Cambiar la planilla (Tornillo, Martillo, Clavos sin stock, Yerba sin palo) | `probar` 7 de 7 |
| `correr mi_negocio.mate --ia-simulada` | "12 tornillos con envio": $ 54.000,00 y envío sí; "2 martillos": $ 24.001,00 y sin envío; "5 clavos": no hay stock; "hola, que tienen?": respuesta simulada. **"12 yerbas sin envio": "Con envío: sí" (P22, sigue)** |
| `corregir mi_negocio.mate Mostrador "..."` | "Anotado", 1 lección; `lecciones` la muestra |
| `ensayar` con los casos de muestra y la planilla cambiada, `--ia-simulada` | 3 de 5, código 1: dos casos nombran azúcar y fideos, que ya no están en la planilla (P68, nuevo) |
| `ensayar` con casos escritos para esa planilla, `--veces=2`, contra un modelo que dice "Si, tenemos cafe a $ 5.000 ... descuento" | "Mostrador ensaya con las lecciones que ya tiene aprobadas (1)"; `✗ tenes cafe?: pasó 0 de 2`; salta el freno y sale la reserva; 3 de 4, código 1; 4 pedidos al servidor, todos con la lección adentro; queda 1 propuesta; lecciones y cuenta del día sin cambios |
| `propuestas mi_negocio.mate` | muestra la propuesta y las órdenes de aprobar y descartar con la ruta completa |
| `propuestas ... aprobar 1` y ensayar de nuevo | 2 lecciones; "ya tiene aprobada la lección de un caso que volvió a fallar: no alcanzó"; la memoria queda con el mismo md5 |

La clave de mentira (`MATE_IA_PROPIA_CLAVE`) llegó al servidor en el encabezado y no aparece
en la pantalla ni en ningún archivo de la carpeta. P29 reproducido de nuevo: con un precio
vacío el mostrador arranca y se corta en "hola" con `pesos() espera numero...`.

**Resultado de seguridad** (especialista; todo en copias, 879 pasan, repositorio sin tocar)

Aprobado. Sin problemas altos ni medios. Respuesta a la pregunta de R: ningún error de
`consultar_ia()` trae la clave, tampoco por la rama de Claude (probado con un servidor local
que la devuelve en un 400 y un 403: sale "(la clave)").

Comprobado y bien: `nuevo mostrador` no sale de la carpeta, no pisa y no sigue enlaces;
`ensayar` no deja en disco lo que escribe el programa, rechaza `--traza=` y `--guardar=` y
corta en 50 pedidos exactos; el texto del cliente o del modelo no se interpreta en ningún
lado; `probar`, `verificar` y `ensayar --ia-simulada` hicieron 0 pedidos con `MATE_IA_PROPIA`
y la clave puestas; en `mate.py` solo `pedir_a_la_ia` y `pedir_a_la_ia_propia` abren
conexiones; una dirección con usuario y contraseña se rechaza sin mostrarla.

| # | Problema de seguridad | Gravedad | ¿Ya estaba? | Estado |
|---|---|---|---|---|
| P61 | `nuevo mostrador` acepta `COM¹`, `lpt²` y parecidos, que Windows también reserva (`com1` sí se rechaza) | baja | no | pendiente: aceptar solo números comunes o sumarlos a `_NOMBRES_DE_WINDOWS` |
| P62 | Si el programa corta con `fallar` antes del primer `leer()`, `ensayar` anota ese texto en `errores_de_uso.txt`; `correr` lo tapa | baja | no | pendiente: pasar un texto sin el error como cuarto valor de ese `avisar()` |
| P63 | `ensayar` muestra entera la dirección de `MATE_IA_PROPIA` ("Contesta tu modelo propio (...), en ...") | baja | no | pendiente: mostrar solo el servidor. Con Ollama local no cambia nada |
| P64 | Si el modelo propio contesta con una redirección 302, la clave viaja al otro servidor y su respuesta se toma como buena | baja | sí | pendiente: no seguir redirecciones en las dos funciones de la IA. Al dueño hoy no lo toca (Ollama local no usa clave) |
| P65 | Con el adaptador de `mate/modelo` y `MATE_MODELO_PROPIO_URL` puesta, `probar` sale a la red con la clave si la prueba no simula | baja | sí | pendiente del coordinador. **Es una excepción a "`probar` no toca la red"** (criterio "Para todo"): hoy solo la avisa `mate/modelo/README.md`. No pasa con `MATE_IA_PROPIA`, que es lo que usa el dueño. La rama no tocó `mate/modelo` |
| P66 | Lo que contesta el modelo llega con códigos de control a la pantalla, y ahora también queda guardado en la propuesta que deja `ensayar` | baja | sí (lo de guardarlo es nuevo) | pendiente: sacar los caracteres de control antes de mostrar o guardar |
| P67 | El tapado de la clave no cubre una clave deformada por el servidor ni una respuesta 200 que la repita; la bitácora y el registro solo tapan `ANTHROPIC_API_KEY` | baja | sí | aceptable; segunda barrera barata: tapar también `MATE_IA_PROPIA_CLAVE` ahí |

No se pudo comprobar: Windows real (nombres reservados, enlaces y Bloc de notas solo
simulados), Claude y Ollama de verdad.

**Qué quedó pendiente o con riesgo**

Medios (hay que resolverlos o decidirlos antes de que el dueño use su mostrador con clientes):
- **P22** (cambio 1; lo heredan los mostradores creados): un "sin envío" o "no me lo mandes"
  se toma como envío confirmado si algún producto nombrado tiene "sin", "no", "ni" o "nada"
  en el nombre. El arreglo pedido está en "Para la vuelta 4" del cambio 1.
- **P29** (cambio 2 y ejemplo 12): un precio o stock vacío o con texto corta el programa en
  la primera consulta que va a la IA, con un error técnico. Solo `probar` lo avisa antes.
- Los dos arreglos van al ejemplo 12, y un mostrador ya creado es una copia fija: el dueño
  tiene que crear el suyo **después** de esos arreglos, o crearlo de nuevo.

Nuevo del cierre (integrador):
- **P68** (baja, cruce de los cambios 2 y 3): los casos de muestra hablan de yerba, azúcar,
  fideos y café. Si el dueño cambia la planilla (paso 3) y después ensaya (paso 5), fallan
  los casos de los productos que sacó, con "Hay que cambiar el programa (o el caso)". El
  encabezado de `<nombre>_casos.txt` no avisa que esos casos son para la planilla de muestra.
  Pendiente para el implementador: un renglón en el encabezado y en el paso 5. I no lo
  arregló: cambia el número de renglón que afirman varias pruebas y nadie lo revisaría después.
- **P69** (—): el especialista en seguridad borró y volvió a crear una carpeta `copia` en la
  carpeta temporal compartida antes de ver que era compartida (misma familia que P60). Nada
  en el repositorio. Para el coordinador: una carpeta temporal por agente.

Bajos que siguen abiertos (ninguno traba):
- Cambio 1: P23, P24, P27; P11 (nada probado en una Windows real).
- Cambio 2: P30, P32, P33, P34, P35; P31 aceptado.
- Cambio 3: P53, P54, P55, P57, P58, P59; P56 aceptado.
- Los tres: P20 (el aviso del freno, `lecciones`, `corregir` y `bitacora` sugieren
  `mate/mate.py` relativo; visto otra vez en el cierre: `corregir` dice
  `python3 mate/mate.py lecciones ...` desde la carpeta del mostrador).
- Seguridad: P61 a P67.

Para el coordinador y el dueño:
1. Decidir si la rama se integra con P22 y P29 abiertos o si antes va una vuelta más.
2. `VERSION` sigue en `"0.5"` y el README dice "Versión 0.5" arriba y "(0.6)" en lo nuevo (P49).
3. La corrida del dueño en Windows sigue sin hacerse: `py mate\mate.py curso 99` (tiene que
   sugerir `py mate\mate.py curso`), `py -m pytest mate\pruebas mate\modelo -q -p
   no:cacheprovider`, `py mate\mate.py nuevo mostrador mi_negocio` con sus pasos, y `ensayar`
   con su Ollama prendido y apagado.
4. Decisiones del dueño que faltan: si está bien `<nombre>_precios.csv`; si devoluciones y
   cancelaciones van a la IA con frenos o a una respuesta fija; la regla de envío para un
   pedido con varios productos.
5. Anotar o resolver la excepción de P65.

**El registro contra el código** (revisado por el integrador en el cierre)

Coinciden con `mate.py`: nombre de hasta 60 letras, `MAX_VECES` 20, `MAX_CASOS` 200,
`_CASOS_DESDE`, `_NOMBRES_DE_WINDOWS`, `_PARES_DE_COMILLAS`, `_FinDelEnsayo`,
`modelo_de_ia_propia()`, `orden_para_esta_carpeta()` y el atributo `ensayando` (tres usos:
las dos condiciones `en_prueba or ensayando` y el guardado de `motivo`). MEJORAS tiene las
entradas 121, 122 y 123. Aclaraciones a lo escrito más arriba:
- "tenes cafe?" está en el renglón 40 del archivo que crea `nuevo mostrador` y en el 42 de
  `mate/ejemplos/casos.txt` (el encabezado es distinto). Donde este registro dice "renglón
  40" habla del archivo creado.
- Criterio "Para todo: `probar` no toca la red": vale para `consultar_ia()`; no para el
  adaptador de `mate/modelo` (P65, ya estaba en `main`).
- "Decisiones técnicas" dice que con `ensayar` se rechazan `--traza` y `--olvidar`; también
  se rechaza `--guardar=` (comprobado por seguridad).
- El título "Cambio 2, vuelta 1 — NO cerrado" queda como historia de esa vuelta; el estado
  de hoy es el de la tabla de arriba.

---

# Mate 0.7 — agentes de un mismo negocio que se reparten el trabajo (rumbo A)

Pedido del dueño: Mate tiene que ser un lenguaje para que los **agentes hablen entre sí**, no
solo un agente que le contesta a una persona. Orden elegido por el dueño: primero A (agentes
de un mismo negocio), después B (agentes de negocios distintos, entre máquinas). B NO entra acá.

## Alcance de la 0.7

1. **Equipo del negocio (ejemplo 13 y `nuevo equipo <nombre>`)**: tres agentes, Ventas,
   Depósito y Compras, que se hablan con mensajes con contrato y un `contrato conversacion`.
   Ventas da la cara al cliente (charla por teclado, IA con frenos solo para lo que no es un
   pedido). Depósito es el único dueño del stock (`estado recordado`) y lo descuenta. Compras
   recibe el pedido de reposición cuando un producto baja del mínimo y lo deja anotado.
   Las cuentas, el stock y las reglas las resuelve el programa, como en el ejemplo 12.
2. **Ensayar la conversación entre agentes**: en el archivo de casos de `ensayar` se puede
   exigir qué mensajes tienen que viajar entre agentes (y cuáles no) para una pregunta del
   cliente, además de lo que se le contesta. El informe muestra la conversación de un caso que falla.
3. **Buzón entre programas (la base de B)**: un agente de un programa le puede `enviar` un
   mensaje a un agente de OTRO programa de la misma PC. El mensaje queda en un buzón (archivo)
   y se entrega, validando el contrato, cuando ese otro programa corre. Sin funciones incluidas
   nuevas si se puede (el cupo está en 48 de 48) y sin red. Lleva una etapa de diseño revisada
   antes de programar.

## Criterios de aceptación de la 0.7

Para todo: pasan todas las pruebas que ya había, sin sacar ni aflojar ninguna; `probar`,
`verificar` y `--ia-simulada` no tocan la red; ninguna clave en archivos; los topes de palabras
y funciones se respetan o el cambio se justifica acá; README, `ayuda` y MEJORAS al día; cada
agente del equipo trabaja en una carpeta temporal PROPIA (mktemp -d), nunca compartida.

- Cambio 1: `nuevo equipo mi_negocio` crea los archivos, pasa `verificar` y `probar`; con
  `--traza` se ve Ventas → Depósito → Compras; un pedido descuenta stock y el stock sobrevive
  entre corridas; pedir más de lo que hay no vende; al bajar del mínimo sale UN pedido de
  reposición (no uno por cada venta); ningún agente toca el estado de otro.
- Cambio 2: un caso puede decir "tiene que viajar X de A a B" y "no tiene que viajar X";
  falla con un mensaje claro que muestra la conversación; los casos viejos siguen andando igual.
- Cambio 3: dos programas en la misma carpeta; el primero envía, termina, y al correr el
  segundo el mensaje llega una sola vez; un mensaje que no cumple el contrato del destino no se
  entrega y queda avisado sin cortar el programa; el buzón no se pierde si el programa se corta;
  `probar` no escribe buzones de verdad.

## Vueltas de la 0.7

### Cambio 1: equipo del negocio (ejemplo 13 y orden nuevo equipo), vuelta 1 — NO cerrado

Revisor y agente de pruebas no aprobaron. Quedan cuatro problemas medios: P79, P80, P81 y P82.

**Qué se hizo** (commit `931d0f6`, implementador; local, sin push, sin tocar `main`)
- Ejemplo `mate/ejemplos/13_equipo_del_negocio.mate`: agentes Ventas, Deposito y Compras, 15
  mensajes con contrato y un `contrato conversacion` de 10 pasos. Trae 14 pruebas.
- Ventas charla por teclado y reusa la lógica de pedidos del ejemplo 12 con `usar`; la IA,
  con frenos, queda solo para lo que no es un pedido.
- Deposito es el único dueño del stock (`estado recordado`): descuenta, no vende lo que no
  hay, y el stock queda de una corrida a la otra.
- Compras recibe UN pedido de reposición cuando un producto baja de `stock_minimo` (10) y lo
  deja anotado; el programa lo muestra al abrir y al cerrar.
- Con `--traza` se ve Ventas pregunta a Deposito y Deposito pregunta a Compras; el contrato
  frena al programa si le habla directo a Deposito o a Compras.
- Orden `nuevo equipo <nombre>` (la misma función `orden_nuevo` que `nuevo mostrador`): crea
  `<nombre>.mate`, `<nombre>_precios.csv` y `<nombre>_casos.txt`, no pisa nada (tampoco una
  memoria vieja) y no deja nada a medias. El programa creado anda solo, sin `usar`, con 10 pruebas.
- `mate/ejemplos/casos_del_equipo.txt`: 8 preguntas de muestra para `ensayar`.
- Clase 13 del curso (`clase_13_equipo.md`, `.mate` y solución); el curso pasa a trece clases.
- README (sección "Un equipo propio: nuevo equipo"), `ayuda`, MEJORAS 124, `docs/index.html`.
- 17 funciones de prueba nuevas (28 casos). Pruebas viejas tocadas solo para extenderlas
  (ejemplos hasta el 13, trece clases, 26 archivos en el curso, `curso 14`,
  `casos_del_equipo.txt` permitido); R confirmó que ninguna afirma menos.
- No se tocó el lenguaje: siguen 36 palabras y 48 funciones incluidas. `VERSION` sigue en 0.6.

**Quién revisó y quién probó**: revisor (R) y agente de pruebas (P), cada uno sobre una copia
en una carpeta temporal propia. Integrador (I): las tres corridas y este registro; no tocó
código ni pruebas.

**Veredictos**: R **no aprueba** (dos medios: P79 y P80). P **no aprueba** (tres medios: P80,
P81 y P82). Cambio 1 **NO cerrado**.

**Pruebas** (integrador, Linux, `MATE_SIN_REGISTRO=1`, sobre `931d0f6`, Python 3.13)
- `pytest mate/pruebas mate/modelo`: 913 pasan, 0 fallan (R y P dieron el mismo
  número en esta misma ruta).
- `probar mate/ejemplos`: 80 de 80, en 19 archivos. `probar mate/curso`: 37 de 37, en 26 archivos.
- Después de todo, `git status --short` vacío.
- Reproducido por I: P82. Con el repositorio copiado a una ruta más larga
  (`<carpeta temporal>/repositorio_copiado`), `-k test_nuevo_equipo_crea_el_programa` da 1 falla
  (`test_mate.py:12116`). O sea: los 913 valen en esta ruta.
- P corrió en Python 3.10, 3.11, 3.12, 3.13 y 3.14: `nuevo equipo` + `verificar` + `probar`
  (10 de 10) + `correr` + `ensayar` (8 de 8) + `probar` ejemplos y curso, todo bien. pytest
  completo solo en 3.13. Nadie probó en una Windows de verdad.

**Criterios de aceptación del cambio 1**

| Criterio | Estado | Evidencia |
|---|---|---|
| `nuevo equipo mi_negocio` crea los archivos, pasa `verificar` y `probar` | cumple | 3 archivos, "sin errores", 10 de 10, `ensayar --ia-simulada` 8 de 8 (R, P); nombres raros, rutas con espacios, no pisa, no deja a medias (P) |
| Con `--traza` se ve Ventas → Depósito → Compras | cumple | "Ventas pregunta a Deposito: Reservar", "Deposito pregunta a Compras: Reponer" (R, P) |
| Un pedido descuenta stock y el stock sobrevive entre corridas | cumple, con reserva | 25 → 2 → `ingreso 30` → 30 saliendo con chau, fin de entrada o Ctrl+C (R, P). No se guarda si se cierra la ventana o se corta el proceso (P80) |
| Pedir más de lo que hay no vende | cumple | "De Yerba mate quedan 40; no llego a 100.", stock intacto (R, P) |
| Al bajar del mínimo sale UN pedido de reposición | cumple, con reserva | un solo Reponer; no se repite en la venta ni en la corrida siguiente (R, P). Tras un ingreso parcial queda bajo el mínimo y sin pedido (P79) |
| Ningún agente toca el estado de otro | cumple | `Deposito.stock` desde Compras da "agente no tiene campos"; el contrato frena al programa (R, P) |
| Para todo: pruebas que ya había, sin aflojar | cumple en esta ruta | 913 / 80 de 80 / 37 de 37; falla una prueba nueva según la carpeta (P82) |
| Para todo: topes, red, claves, README/`ayuda`/MEJORAS | cumple, con pendientes bajos | 36 palabras y 48 funciones; `probar` y `ensayar` no cambian la memoria (mismo md5); sin claves ni datos personales (P). README: P80, P92 |

**Problemas** (R = revisor, P = agente de pruebas, I = integrador)

| # | Problema | Quién | Gravedad | ¿Ya estaba? | Estado |
|---|---|---|---|---|---|
| P79 | Un `ingreso` PARCIAL borra el pedido de reposición aunque el producto siga bajo el mínimo: Azúcar en 4 (mínimo 10), Compras con la lista vacía, y no se vuelve a pedir hasta otra venta. "al recibir Ingreso" de Deposito siempre tacha y manda `Llego` | R (media), P (baja) | media | no | pendiente (vuelta 2, obligatorio): tachar en Compras solo si el stock quedó en el mínimo o más; si no, dejar el pedido con el número nuevo. Con prueba en el ejemplo y en `_PRUEBAS_DEL_EQUIPO` |
| P80 | Las ventas "Anotado" se pierden si la charla no termina con chau o Ctrl+C (cerrar la ventana con la X, corte de luz): la memoria se escribe recién al terminar. Ni el encabezado del 13, ni el del programa creado, ni los pasos de `nuevo equipo`, ni "Un equipo propio" del README lo avisan | R, P | media | el mecanismo sí; usarlo como libro de stock y no avisarlo, no | pendiente (vuelta 2, obligatorio): avisarlo en esos cuatro lugares. Guardar después de cada consulta toca el lenguaje: ver decisiones |
| P81 | Ventas anota, y Depósito descuenta sin forma de anular, frases que no son un pedido: "no me mandes 2 arroz", "se puede pedir 2 aceite?", "2 azucar?", "haceme un descuento en 20 yerba", "a las 3 paso a buscar la yerba", "quiero saber si puedo llevar 20 azucar". Lo peor: "recibi 10 yerba" o "llegaron 10 fideos" VENDEN 10. Contradice "ante la duda no se anota" | P (media), R (baja) | media | no (en el 12 solo daba una cuenta) | pendiente (vuelta 2, obligatorio): anotar solo con palabras claras de pedido y sin negación, pregunta ni duda; lo demás da la cuenta y "Todavía no anoté nada". Con pruebas de estas frases |
| P82 | `test_nuevo_equipo_crea_el_programa_la_planilla_y_los_casos_listos_para_usar` exige renglones de hasta 110 caracteres y el renglón de `ensayar` lleva la ruta completa de `mate.py`: con el repositorio en una ruta más larga falla (912 de 913) | P; reproducido por I | media | no | pendiente (vuelta 2, obligatorio): que la prueba no dependa de la ruta, sin aflojar lo que cuida (medir sin la ruta, o correr con una ruta fija) |
| P83 | `ingreso` acepta de más: una pregunta que empieza con "Ingresó..." suma stock; `ingreso -5 azucar` suma 5; un número enorme entra sin preguntar; `ingreso 10 fideos con envio` entra igual | R, P | baja | no | pendiente (vuelta 2 si entra): exigir "ingreso" exacto seguido del número, rechazar el menos y un número disparatado |
| P84 | Compras muestra "(quedan 5)" con el número del momento del aviso aunque ya queden 2 | R | baja | no | pendiente: "quedaban 5 cuando se pidió", o preguntarle a Depósito el stock de hoy |
| P85 | Un producto que ARRANCA bajo el mínimo en la planilla (Aceite: 8) no genera pedido hasta que alguien lo pide; el README no lo dice | R, P | baja | no | pendiente: decirlo en el README o avisar a Compras en `Inventario` |
| P86 | Correr el ejemplo 13 en su lugar deja `13_equipo_del_negocio.memoria.json` en `mate/ejemplos` y con eso falla `test_el_ejemplo_del_agente_que_aprende` | R, P | baja | sí (pasaba con el ejemplo 8); ahora hay un ejemplo más cuyo uso documentado lo provoca | pendiente: que README y encabezado manden a copiarlo o a usar `nuevo equipo` |
| P87 | Dos ventanas con el mismo equipo: la que termina última pisa el stock de la otra. El README lo dice para `estado recordado` en general, no en la parte del equipo | P | baja | sí | pendiente: una línea en "Un equipo propio" (junto con P80) |
| P88 | Un producto sacado o renombrado en la planilla deja su stock y su pedido de reposición para siempre; `ingreso` ya no lo tacha; solo `--olvidar`, que borra todo | P, implementador | baja | no | pendiente (si entra): limpiar lo que ya no está en la planilla, o decirlo en el README |
| P89 | `ensayar` usa el stock que Depósito recuerda: con la yerba casi vendida fallan 5 de 8 casos de muestra y el informe dice "Hay que cambiar el programa (o el caso)" | P, R, implementador | baja | no | pasa al cambio 2 (ensayar la conversación entre agentes) |
| P90 | Números que el encabezado invita a cambiar y rompen: `unidades_para_envio = 0` (9 de 10), `stock_minimo = 2.5`; `stock_minimo = -5` o "diez" pasan `verificar` y cortan al correr con un error técnico | P | baja | no | pendiente (si entra): decir en el encabezado qué valores valen y dar un mensaje simple |
| P91 | Planilla y memoria: stock con decimales contesta "quedan 0.5" (con punto); dos renglones con el mismo producto comparten stock; memoria editada a mano con texto corta la charla; "quiero -3 azucar" anota 3 | P | baja | no | pendiente (si entra) |
| P92 | `VERSION` sigue en 0.6; el README dice "once programas cortos" con trece filas en la tabla (tres pruebas viejas exigen la frase) | R, implementador | baja | la frase sí | `VERSION`: al cierre de la 0.7. La frase: pendiente, cambiando frase y pruebas juntas sin aflojarlas |
| P93 | `ingreso` lo puede escribir cualquiera con el teclado; un solo mínimo para todos los productos; un producto por pedido; sin anulación de un pedido anotado | implementador | baja | no | aceptado como límite de la 0.7; está avisado en ejemplo, programa creado y README |
| P94 | Quedaron cuatro o cinco carpetas temporales del implementador en `/tmp` (un control bloqueó el borrado); solo copias de ejemplos y memorias de prueba | implementador | — | — | las borra quien las creó o el dueño; nadie más las toca |
| P11 | Sin probar en una Windows de verdad (`py`, PowerShell, Bloc de notas) | R, P, I | baja | sí | pendiente del dueño |

No verificado por nadie: una falla real de Compras (solo la simulada de la prueba) y el
contenido de la clase 13 más allá de que sus pruebas pasan.

**Decisiones técnicas nuevas**
- `responder_pedido()` del ejemplo 12 se partió en `leer_pedido()`, `falta_stock()` y
  `cuenta_del_pedido()`; el 12 contesta igual y sus 22 pruebas no cambiaron.
- El ejemplo 13 trae esa lógica con `usar` en vez de copiarla. Costo: viene el agente
  Mostrador del 12 sin usarse y los nombres del 13 esquivan los del 12.
- Pedido y pregunta se distinguen: un pedido se anota ("Anotado: ..."), una pregunta da la
  cuenta y dice "Todavía no anoté nada". La regla "ante la duda no se anota" queda, y hoy no
  se cumple (P81).
- El stock de la planilla es solo el de arranque; la mercadería entra por la charla con
  `ingreso 30 azucar` y `--olvidar` vuelve a la planilla.
- Deposito le pregunta a Compras dentro del contrato y marca "ya avisé" recién cuando Compras
  contesta; si Compras falla, la venta no se cae y se reintenta con el pedido siguiente.
  También avisa si piden un producto que está en cero.
- Cada consulta del cliente lleva su propia charla (`consulta-1`, `consulta-2`...) y el
  contrato termina en `fin`. La carga inicial, `Ingreso`, `Llego` y `QueFalta` van fuera del contrato.
- `nuevo equipo` depende de siete títulos de los ejemplos 12 y 13; si alguno cambia, falla con
  "no tiene la forma que espero" (con pruebas) y los dos ejemplos lo avisan en su encabezado.
- `nuevo` a secas dice ahora "Crea un mostrador o un equipo de agentes".
- La clase 13 no usa teclado ni IA, para que lo que "tiene que salir" sea exacto.
- Integrador, sobre P80: en la vuelta 2 va el arreglo mínimo (avisar). Guardar lo recordado
  después de cada consulta cambia el intérprete para todos los programas con `estado
  recordado`; no se hace sin una propuesta escrita acá y revisada por R. Queda anotado como
  candidato antes de cerrar la 0.7, porque un mostrador queda abierto todo el día.
- Integrador: no arregló nada en esta vuelta; P79, P81 y P82 cambian comportamiento o pruebas
  y piden revisión independiente.

**Para la vuelta 2**: P79, P80 (aviso), P81 y P82 (obligatorios). Si entran: P83, P84, P85,
P86, P87, P88, P90, P91 y la frase de P92. P89 pasa al cambio 2.

### Cambio 1: equipo del negocio (ejemplo 13 y orden nuevo equipo), vuelta 2 — NO cerrado

Revisor y agente de pruebas no aprobaron. Queda un problema medio: P81, arreglado a medias.
P79, P80 (el aviso) y P82 quedaron resueltos.

**Qué se hizo** (commit `0123b06`, implementador; local, sin push, sin tocar `main` ni este
archivo). Tocó el ejemplo 13, `mate.py`, `test_mate.py`, README, MEJORAS y `clase_13_equipo.md`.
- P81: Ventas anota solo un "pedido claro". `es_pedido_claro()` mira la frase palabra por
  palabra y, además de la cantidad y el producto, acepta solo las palabras de
  `palabras_de_un_pedido()`. Las 18 frases de la vuelta 1 ya no descuentan. Se quitó
  `pregunta_el_precio()`. Quedó a medias: ver P81 en la tabla.
- P79: un ingreso que deja el producto bajo el mínimo ya no borra el pedido de reposición.
  Depósito manda `SigueFaltando` y Compras lo deja con el número nuevo; se tacha recién cuando
  el stock llega al mínimo. Con prueba en el ejemplo, en `_PRUEBAS_DEL_EQUIPO` y en pytest.
- P80, arreglo mínimo: el aviso "terminá siempre con chau; si cerrás la ventana con la X se
  pierde lo anotado en esa charla" está en el encabezado del 13, en el del programa creado, en
  los pasos de `nuevo equipo`, en el README, en la clase 13 y en un renglón al abrir la charla.
  Una prueba lo exige.
- P82: la prueba del ancho mide con la ruta de `mate.py` reemplazada y con un tope más justo
  (86 en vez de 110); hay una prueba nueva con un `mate.py` en una ruta muy larga.
- P83: `ingreso` es más estricto: primera palabra "ingreso" sin tilde, después la cantidad sin
  signo, sin envío y hasta `ingreso_maximo` (100000) por vez. Todavía acepta de más: ver P83.
- P84: lo que hay que reponer se muestra con lo que queda hoy; el programa se lo pregunta a
  Depósito con `CuantoQueda` / `Queda`.
- P90 y parte de P91: `que_arreglar()` avisa en castellano, antes de atender, un `stock_minimo`
  o un `unidades_para_envio` mal puestos y un stock con decimales en la planilla. "quiero -3
  azucar" ya no anota.
- P85, P86, P87 y P88: resueltos solo con texto (README y encabezados).
- P92: el README dice "trece programas"; las tres pruebas viejas exigen ahora esa frase.
- El ejemplo 13 pasa de 14 a 20 pruebas y el equipo creado de 10 a 13. MEJORAS 124 lleva una
  nota de esta vuelta. No se tocó el lenguaje: siguen 36 palabras y 48 funciones incluidas.

**No se hizo** (declarado por el implementador): P80 de fondo (guardar después de cada
consulta); P85, P87 y P88 en el código; el resto de P91 (dos renglones con el mismo producto,
memoria editada a mano); P86 (solo avisado); P89 (pasa al cambio 2); `VERSION` sigue en 0.6.

**Quién revisó y quién probó**: revisor (R) y agente de pruebas (P), cada uno sobre una copia
en una carpeta temporal propia. Integrador (I): las tres corridas y este registro; no tocó
código ni pruebas.

**Veredictos**: R **no aprueba** (un medio: P81). P **no aprueba** (un medio: P81). Cambio 1
**NO cerrado**.

**Pruebas** (integrador, Linux, `MATE_SIN_REGISTRO=1`, sobre `0123b06`, Python 3.13.18)
- `pytest mate/pruebas mate/modelo`: 925 pasan, 0 fallan (antes 913). Implementador, R y P
  dieron el mismo número; R lo corrió además desde una ruta distinta y más larga.
- `probar mate/ejemplos`: 86 de 86, en 19 archivos. `probar mate/curso`: 37 de 37, en 26 archivos.
- Después de todo, `git status --short` vacío.
- Reproducido por I, en una carpeta temporal propia (ya borrada), sobre un equipo creado con
  `nuevo equipo`: "gracias por las 10 yerbas" contesta "Anotado" y deja la yerba en 30 (de 40);
  "retiro el pedido de 5 yerbas" contesta "Anotado" y la deja en 35. "recibi 10 yerba", de la
  vuelta 1, ya no anota (queda en 40).
- R y P corrieron en Python 3.11 y 3.12: `probar` de ejemplos (86 de 86) y el equipo creado
  (13 de 13); P además `verificar`, `correr`, `ensayar` (8 de 8) y el curso (37 de 37). En esta
  vuelta nadie corrió en 3.10 ni en 3.14 (no están en la máquina). pytest completo solo en
  3.13. Nadie probó en una Windows de verdad.
- Pruebas viejas tocadas (R y P revisaron los renglones quitados): solo valores esperados
  ("14 de 14" a "20 de 20", "10 de 10" a "13 de 13", "(quedan 5)" a "(quedan 2)" y "(quedan 2)"
  a "(quedan 1)" por P84, "once" a "trece programas cortos") y la del ancho (de 110 con ruta a
  86 sin ruta). Ninguna se quitó ni afirma menos.

**Criterios de aceptación del cambio 1**

| Criterio | Estado | Evidencia |
|---|---|---|
| `nuevo equipo mi_negocio` crea los archivos, pasa `verificar` y `probar` | cumple | 3 archivos, "sin errores", 13 de 13, `ensayar --ia-simulada` 8 de 8 (R, P); carpeta con espacios, nombres raros, no pisa archivos ni una memoria vieja (P) |
| Con `--traza` se ve Ventas → Depósito → Compras | cumple | "Ventas pregunta a Deposito: Reservar", "Deposito pregunta a Compras: Reponer", "Compras responde a Deposito: Anotado" (R, P) |
| Un pedido descuenta stock y el stock sobrevive entre corridas | cumple, con reservas | 25 → 2 y la corrida siguiente arranca con 2 (R, P). Se guarda con chau, fin de entrada o Ctrl+C; con la X o un corte no (P80 de fondo, ahora avisado). Además descuenta frases que no son un pedido nuevo (P81) |
| Pedir más de lo que hay no vende | cumple | "De Yerba mate quedan 40; no llego a 100", stock intacto; sin stock lo dice (R, P) |
| Al bajar del mínimo sale UN pedido de reposición | cumple | un solo Reponer, no se repite; tras un ingreso parcial queda anotado con el número nuevo y se tacha al llegar al mínimo (P79 resuelto; R, P) |
| Ningún agente toca el estado de otro | cumple | `Deposito.stock` desde el programa da "agente no tiene campos"; el contrato frena Reservar y Reponer directos (P); los mensajes nuevos llevan contrato (R) |
| Para todo: pruebas que ya había, sin aflojar | cumple | 925 / 86 de 86 / 37 de 37; ya no depende de la carpeta (P82), salvo una ruta con espacios (P99) |
| Para todo: topes, red, claves, README/`ayuda`/MEJORAS | cumple, con pendientes bajos | 36 palabras y 48 funciones; `probar` y `ensayar` no cambian la memoria (mismo md5); sin clave avisa y sigue (P). README promete de más en `ingreso` (P83) y en "ante la duda no se anota" (P81) |

**Problemas** (R = revisor, P = agente de pruebas, I = integrador)

| # | Problema | Quién | Gravedad | ¿Ya estaba? | Estado |
|---|---|---|---|---|---|
| P81 | A medias. Ventas sigue anotando, y Depósito descontando sin forma de anular, frases que hablan de un pedido YA hecho o que no piden nada, armadas solo con palabras de la lista permitida ("gracias", "por", "pedido", "retiro", "llevo", "mandan", "ya", "otro", "dia"): "gracias por las 10 yerbas", "retiro el pedido de 5 azucar", "ya llevo el pedido de 5 azucar", "hola, por mi pedido de 5 azucar", "mi pedido de 20 azucar", "ya me mandan los 10 arroz", "te llevo 10 yerbas", "otro dia quiero 20 azucar". El cliente que viene a retirar lo que ya pidió lo vende dos veces. Las 18 frases de la vuelta 1 sí quedaron bien | R, P; reproducido por I | media | no | pendiente (vuelta 3, obligatorio): sacar de `palabras_de_un_pedido()` las que hablan de un pedido que ya existe o no piden nada, o exigir un verbo de pedir; con estas frases como prueba |
| P95 | El menos solo se detecta pegado al número y con guion común: "quiero - 3 azucar" y "quiero –3 azucar" (raya larga) anotan 3; "quiero 20 azucar？" (signo de pregunta ancho) anota | R | baja | no | pendiente (vuelta 3 si entra, va con P81) |
| P83 | Resto. README y mensaje dicen "cantidad y producto, y nada más", pero "ingreso 5 yerbas no", "ingreso 5 yerbas?", "ingreso 5 de yerba" e "ingreso 30 azucar gracias" suman. "ingresó 30 azucar" (con tilde, como corrige un celular), "ingreso: 30 azucar" e "ingresos 30 azucar" van a Ventas como consulta, sin explicar cómo se escribe. Lo demás quedó bien (menos, tope, envío, dos números) | R, P | baja | no | pendiente (vuelta 3 si entra): rechazar cualquier palabra de más y explicar el ingreso cuando la primera palabra se parece a "ingreso" |
| P96 | Pedidos corrientes con un verbo fuera de la lista no se anotan: "quiero comprar 20 azucar", "quiero pedir 20 azucar", "me das 5 yerbas", "pasame 5 yerbas", "necesito 12 arroz para mañana con envio". Contesta la cuenta y cómo pedirlo: se equivoca para el lado seguro. Aparte, "devuelvo 5 yerbas" o "anulame el pedido de 5 yerbas" no descuentan (bien) pero contestan solo el renglón de la lista, sin decir que no se anotó ni que un pedido no se anula desde la charla | R, P | baja | no | pendiente (vuelta 3 si entra): agregar los infinitivos y verbos comunes; una respuesta clara para devolver o anular |
| P97 | `ingreso_maximo` se puede cambiar arriba y `que_arreglar()` no lo revisa: con un texto pasa `verificar`, atiende y corta la charla al primer ingreso con un error técnico (se pierde lo vendido en esa charla). Tampoco hay tope para `stock_minimo`: con 1000000 fallan 2 de 13 pruebas del programa creado, contra lo que dice el README | R | baja | no | pendiente (si entra) |
| P98 | Con `unidades_para_envio = "10"` el aviso dice "sin comillas. Ahora dice: 10": no muestra las comillas y confunde | R | baja | no | pendiente (si entra) |
| P99 | Con el repositorio en una ruta con ESPACIOS fallan 5 pruebas de pytest (2 de `nuevo equipo` y 3 que ya había de `nuevo mostrador` / `ensayar`): arman el comando esperado sin comillas y el programa, bien, lo muestra entre comillas. Es defecto de las pruebas; `nuevo equipo` en una carpeta con espacios anda. No es P82: en una ruta larga sin espacios pasan las 95 | P | baja | sí (3 de las 5) | pendiente (si entra): que las pruebas armen el comando igual que el programa, sin aflojarlas |
| P100 | Con `stock_minimo` mal puesto (-5, "diez", verdadero, nada) `verificar` sigue diciendo "sin errores" y `probar` da 0 de 13: la primera prueba avisa claro y las otras 12 muestran un error técnico. Con 2.5 da 9 de 13. `correr` sí avisa bien y no atiende | P | baja | no | pendiente (si entra) |
| P101 | Un renglón del encabezado del programa creado se pasa del ancho porque lleva adentro el nombre del archivo de memoria; con un nombre largo se pasa más | P | baja | no | pendiente (prolijidad) |
| P79 | Ingreso parcial borraba el pedido de reposición | R, P | media | no | **resuelto** (R y P lo comprobaron) |
| P80 | Lo anotado se pierde si la charla no termina con chau o Ctrl+C | R, P | media | el mecanismo sí | aviso: **resuelto** (seis lugares y al abrir la charla). De fondo: pendiente, con SIGTERM o la X se sigue perdiendo (P lo comprobó); necesita propuesta escrita y revisada antes de tocar el intérprete |
| P82 | La prueba del ancho dependía de la carpeta | R, P | media | no | **resuelto** (925 desde otra ruta más larga) |
| P84 | Compras mostraba el número del día del aviso | R, P | baja | no | **resuelto** |
| P85 | Un producto que arranca bajo el mínimo no genera pedido hasta que alguien lo pide | R, P | baja | no | solo avisado (README y encabezado). Avisar a Compras al cargar rompía dos pruebas existentes del ejemplo |
| P86 | Correr el 13 en su lugar deja la memoria en `mate/ejemplos` y rompe otra prueba | R, P | baja | sí | solo avisado; README y ejemplo mandan a usar `nuevo equipo` |
| P87 | Dos ventanas a la vez se pisan | P | baja | sí | solo avisado |
| P88 | Un producto sacado de la planilla deja su stock y su pedido hasta `--olvidar` | P | baja | no | solo avisado (P lo volvió a ver) |
| P89 | `ensayar` depende del stock recordado | P, R | baja | no | sin tocar; pasa al cambio 2 |
| P90 | Números de arriba mal puestos cortaban con un error técnico | P | baja | no | **resuelto** al correr; lo que queda es P97, P98 y P100 |
| P91 | Planilla y memoria | P | baja | no | decimales y "quiero -3 azucar": resueltos. Quedan: dos renglones con el mismo producto comparten stock; memoria editada a mano con texto corta la charla |
| P92 | `VERSION` en 0.6; "once programas cortos" | R | baja | la frase sí | la frase: **resuelta**. `VERSION`: al cierre de la 0.7 |
| P94 | Carpetas temporales del implementador en `/tmp`: en esta vuelta quedaron cuatro (dos sin nombre anotado); un control bloqueó el borrado y no lo forzó. Solo copias de ejemplos y memorias de prueba | implementador | — | — | las borra quien las creó o el dueño; nadie más las toca |
| P11 | Sin probar en una Windows de verdad (`py`, PowerShell, Bloc de notas) | R, P, I | baja | sí | pendiente del dueño |

No verificado por nadie en esta vuelta: Python 3.10 y 3.14, pytest completo fuera de 3.13,
Windows, una falla real de Compras y el contenido de la clase 13 más allá de sus pruebas.

**Decisiones técnicas nuevas**
- P81 por lista de palabras permitidas, no prohibidas: si se equivoca, no descuenta. Costo: un
  pedido dicho con una palabra fuera de la lista no se anota; contesta la cuenta y cómo pedirlo
  ("quiero 12 azucar"). El dueño puede agregar palabras en `palabras_de_un_pedido()`. La lista
  de hoy tiene palabras de más (P81) y le faltan verbos comunes (P96).
- Las palabras de envío aceptadas en un pedido son una lista fija (mandame, envio, flete...) y
  no todo lo que empieza con "mand": así "me mandaron 10 fideos" no se anota.
- P84: se le pregunta a Depósito el stock de hoy, en vez de cambiar el texto a "quedaban". Por
  eso cambió el número esperado en dos pruebas.
- `SigueFaltando`, `Llego`, `CuantoQueda` y `Queda` van fuera del contrato de conversación,
  como ya iban `Ingreso` y `QueFalta`: no llevan el campo `charla`.
- `que_arreglar()` y `es_entero_desde()` están bajo el título "El programa" del ejemplo 13, no
  bajo "El equipo": su mensaje nombra la planilla y el tramo de los agentes se copia tal cual
  al programa creado.
- En `_PRUEBAS_DEL_EQUIPO` la prueba del ingreso usa `stock_minimo + 30` y la del ingreso
  parcial se saltea con mínimo 0 o 1, para que pasen con cualquier mínimo válido.
- `ingreso_maximo` (100000) es un número nuevo que el dueño puede cambiar arriba (ver P97).
- Integrador: no arregló nada en esta vuelta. P81 cambia comportamiento y pruebas y pide
  revisión independiente. P80 de fondo sigue esperando una propuesta escrita acá.

**Para la vuelta 3**: P81 (obligatorio), con las frases de R y P como prueba. Si entran, y
conviene porque tocan el mismo tramo: P95, P83 y P96. Después: P97, P98, P99, P100 y P101.
P89 pasa al cambio 2. El orden del dueño sigue igual: primero A, después B; nada de B todavía.

### Cambio 1: equipo del negocio (ejemplo 13 y orden nuevo equipo), vuelta 3 — NO cerrado

El revisor aprobó; el agente de pruebas no. Queda un problema medio nuevo: P102 (un pedido
dicho en la unidad de adentro de la presentación se anota como bultos enteros). Todo lo que
esta vuelta tenía que arreglar (P81, P83, P95 a P101) quedó resuelto; de P81 quedan restos bajos.

**Qué se hizo** (commit `dfcea28`, implementador; local, sin push, sin tocar `main` ni este
archivo). Tocó el ejemplo 13, `mate.py`, `test_mate.py`, README y MEJORAS.
- P81: `es_pedido_claro()` ya no usa una lista única. Son cuatro listas con reglas distintas:
  `palabras_de_pedir()`, `palabras_sueltas()`, `palabras_que_acompanan()` (adelante de la
  cantidad piden una palabra de pedir) y `palabras_de_como_se_lleva()` (envío, retiro,
  artículos, "gracias": valen solo DESPUÉS de la cantidad). Salieron "ya", "mandan" y
  "lleven"; "pedido" vale solo en "hago/hacer un pedido", "por" solo en "por favor", "dia"
  solo en "buen dia"; "te/le llevo" no anota. Las 17 frases de R y P (y 16 más de la misma
  familia) contestan "Todavía no anoté nada" y dejan el stock intacto, en el ejemplo y en el
  equipo creado.
- P95: `trae_un_menos()` detecta el menos con espacio y con raya larga o media; el signo de
  pregunta ancho cuenta como pregunta.
- P96: se anotan "quiero comprar/pedir 20 azucar", "me das", "pasame", "hago un pedido de" y
  "me llevo". Devolver, anular, cancelar o "ya no quiero" tienen respuesta propia del
  programa, sin IA y sin tocar Depósito: "No anoté nada. Y si es por un pedido que ya está
  anotado: desde esta charla no se anula ni se devuelve, eso lo arregla una persona del negocio."
- P83 (resto): `anotar_ingreso()` acepta solo "ingreso", la cantidad y palabras del NOMBRE del
  producto; rechaza signos, punto final, "de", "no" y "gracias". `parece_un_ingreso()`, nueva:
  "ingresó 30 azucar", "ingreso: 30 azucar" e "ingresos 30 azucar" explican cómo se escribe en
  vez de ir a Ventas. "Ingresó mi pedido...?" e "ingresaron 5 fideos" siguen yendo a Ventas.
- P97, P98 y P100: `numeros_mal_puestos()` revisa `unidades_para_envio`, `stock_minimo` e
  `ingreso_maximo`; un texto se muestra con comillas ("Ahora dice: "10" (con comillas: hay que
  sacarlas)"); `abrir_el_negocio()` no abre con uno mal puesto, así que `probar` da 0 de 15 con
  el mismo aviso en castellano en las 15. Las pruebas del equipo creado pasan con
  `stock_minimo` 0, 1, 37 y 1000000 y con `ingreso_maximo` 1.
- P99: las 7 aserciones de `nuevo mostrador`, `nuevo equipo` y `ensayar` que armaban el
  comando con la ruta sin comillas usan ahora `mate.para_pegar` (ayudante `MATE_PY`).
- P101: en el encabezado del programa creado el archivo de memoria va solo en su renglón.
  Prueba nueva con un nombre de 45 letras.
- El ejemplo 13 pasa de 20 a 26 pruebas y el equipo creado de 13 a 15; en pytest, 7 funciones
  nuevas (13 casos) y 3 parámetros más en la de números mal puestos. README ("Un equipo
  propio") y MEJORAS 124 al día. No se tocó el lenguaje: siguen 36 palabras y 48 funciones.

**No se hizo** (declarado por el implementador): P80 de fondo (guardar después de cada
consulta; solo avisado); `verificar` sigue diciendo "sin errores" con un número de arriba mal
puesto (mitad de P100); P85, P86, P87, P88 y el resto de P91 (solo avisados); un pedido con una
palabra fuera de las listas no se anota ("necesito 12 arroz para mañana con envio", "quiero
llevar 5 azucar"); dos renglones del encabezado que nombran el archivo de casos se pasan del
ancho con un nombre largo (están igual en `nuevo mostrador`); no tocó la clase 13 ni
`docs/index.html`; `VERSION` sigue en 0.6; P89 pasa al cambio 2. Borró sus tres carpetas
temporales de esta vuelta; no tocó las de vueltas anteriores (P94).

**Quién revisó y quién probó**: revisor (R) y agente de pruebas (P), cada uno sobre una copia
en una carpeta temporal propia, ya borrada. Integrador (I): las tres corridas y este registro;
no tocó código ni pruebas.

**Veredictos**: R **aprueba** (ocho problemas, todos bajos). P **no aprueba** (un medio: P102;
siete bajos). Cambio 1 **NO cerrado**.

**Pruebas** (integrador, Linux, `MATE_SIN_REGISTRO=1`, sobre `dfcea28`, Python 3.13.18)
- `pytest mate/pruebas mate/modelo`: 938 pasan, 0 fallan (antes 925). Implementador, R y P
  dieron el mismo número.
- `probar mate/ejemplos`: 92 de 92, en 19 archivos. `probar mate/curso`: 37 de 37, en 26 archivos.
- Después de todo, `git status --short` vacío.
- Reproducido por I, en una carpeta temporal propia (ya borrada), sobre un equipo creado con
  `nuevo equipo`: "quiero 10 paquetes de yerba" contesta "Anotado: 10 x Yerba mate (bolsón de
  10 paquetes de 1 kg) ... total $ 350.000,00" y "quiero 6 botellas de aceite" anota 6 cajas;
  la memoria queda con Yerba mate 30 (de 40) y Aceite 2 (de 8). "quiero 1 kg de yerba" no
  anota ("Decime cuántos querés"). También "compró 10 yerbas" contesta "Anotado" (P103).
- R y P, con el repositorio copiado a una ruta con espacios: `-k 'equipo or mostrador or
  nuevo'` da 106 pasan, 0 fallan (antes fallaban 5; P99).
- Implementador, R y P en Python 3.11 y 3.12: `probar` de ejemplos (92 de 92), curso (37 de
  37) y equipo creado (`verificar`, 15 de 15, `ensayar` 8 de 8). Nadie corrió en 3.10 ni en
  3.14 (no están en la máquina). pytest completo solo en 3.13. Nadie probó en una Windows de verdad.
- Pruebas viejas tocadas (R y P revisaron los renglones quitados entre `2708898` y `dfcea28`):
  conteos ("20 de 20" a "26 de 26", "13 de 13" a "15 de 15"); "Ahora dice: diez" pasó a exigir
  el texto con comillas; las 7 rutas de `mate.py` se arman como las arma el programa; en
  `_PRUEBAS_DEL_EQUIPO` la del ingreso mal escrito se renombró, lleva más frases y exige "No
  entendí el ingreso. No sumé nada."; el número enorme usa `ingreso_maximo + 1`. Ninguna se
  quitó ni afirma menos.

**Criterios de aceptación del cambio 1**

| Criterio | Estado | Evidencia |
|---|---|---|
| `nuevo equipo mi_negocio` crea los archivos, pasa `verificar` y `probar` | cumple | 3 archivos, "sin errores", 15 de 15, `ensayar --ia-simulada` 8 de 8 (R, P); carpeta con espacios, nombres raros, no pisa archivos ni una memoria vieja, no deja nada a medias (P) |
| Con `--traza` se ve Ventas → Depósito → Compras | cumple | "Ventas pregunta a Deposito: Reservar", "Deposito pregunta a Compras: Reponer", "Compras responde a Deposito: Anotado" (R, P) |
| Un pedido descuenta stock y el stock sobrevive entre corridas | cumple, con reservas | 25 → 2 y la corrida siguiente arranca con 2; se guarda con chau, fin de entrada o Ctrl+C (P). Con la X o un corte no (P80 de fondo, avisado). Descuenta de más cuando el pedido viene en la unidad de adentro (P102) |
| Pedir más de lo que hay no vende | cumple | "De Yerba mate quedan 40; no llego a 100.", stock intacto; sin stock lo dice (P) |
| Al bajar del mínimo sale UN pedido de reposición | cumple | 5 ventas en una corrida dan 2 Reponer, uno por producto; en la corrida siguiente, 0; el ingreso parcial lo deja con el número nuevo (P). El segundo pedido no manda otro Reponer (R) |
| Ningún agente toca el estado de otro | cumple | `Deposito.stock` desde el programa da "agente no tiene campos"; el contrato frena Reservar y Reponer directos (R, P); lo nuevo son funciones del programa (R) |
| Para todo: pruebas que ya había, sin aflojar | cumple | 938 / 92 de 92 / 37 de 37; pasan también desde una ruta con espacios (P99) |
| Para todo: topes, red, claves, README/`ayuda`/MEJORAS | cumple, con pendientes bajos | 36 palabras y 48 funciones; `probar` y `ensayar` no cambian la memoria (mismo md5); sin clave avisa y sigue (P). README: falta el matiz del retiro detrás de la cantidad (P104) y promete de más con el número del envío (P110) |

**Problemas** (R = revisor, P = agente de pruebas, I = integrador)

| # | Problema | Quién | Gravedad | ¿Ya estaba? | Estado |
|---|---|---|---|---|---|
| P102 | Un pedido dicho en la unidad de ADENTRO de la presentación se anota como bultos enteros y descuenta stock sin forma de anular: "quiero 10 paquetes de yerba" anota 10 bolsones de 10 paquetes ($ 350.000,00; el cliente quería 1) y "quiero 6 botellas de aceite" anota 6 cajas de 12. Con una planilla propia pasa igual. `es_pedido_claro()` acepta como palabra del producto TODAS las de la presentación, no solo la unidad en que se vende. El ejemplo 12 trata el caso hermano como duda ("quiero 1 kg de yerba" no anota) y el README promete "ante la duda no se anota" | P; reproducido por I | media | sí (desde la vuelta 2, `0123b06`; nadie lo había reportado. En el 12 solo daba una cuenta) | pendiente (vuelta 4, obligatorio): de la presentación aceptar solo la primera palabra (la unidad de venta), o no anotar si atrás de la cantidad viene una palabra de la presentación que no es la primera; con estas frases como prueba en el ejemplo y en `_PRUEBAS_DEL_EQUIPO` |
| P103 | Resto de P81: sin tilde, un pasado en tercera persona queda igual a una palabra de pedir: "compró 10 yerbas", "llevó 10 yerbas" y "encargó 5 yerbas" anotan; también "encargo de 5 yerbas" y "de 5 yerbas". Algunas palabras de pedir valen solas: "hago 5 yerbas", "hacerte 5 yerbas", "me hacer 5 yerbas" ("hago", "hacer", "hacerte" y "haceme" no exigen "un pedido" atrás) y "llevo 10 yerbas de mas". Con sujeto ("mi socio llevó 10 yerbas", "se llevó 5 yerbas") no anotan | R, P; "compró" reproducido por I | baja | no | pendiente (vuelta 4 si entra, va con P102): exigir "un pedido" después de "hago/hacer/haceme", no aceptar "de" suelto adelante; estas frases como prueba |
| P104 | Resto de P81: con la cantidad adelante y solo palabras de retiro detrás se anota: "hola, 5 yerbas para retirar", "5 yerbas a retirar", "10 yerbas retiro". Es la regla elegida ("5 yerbas, las retiro yo" es un pedido con retiro), pero quien viene a buscar lo ya pedido y lo dice así compra dos veces. El README afirma sin matiz "El cliente que viene a retirar lo que pidió no lo compra dos veces". "retiro 5 yerbas", "vengo a retirar 5 yerbas" y "5 yerbas del pedido" no anotan | R, P | baja | sí | pendiente: como mínimo decir en el README que vale cuando el retiro o el artículo van ADELANTE de la cantidad |
| P105 | "llevo 10 yerbas al local" o "yo llevo 10 yerbas", dicho por quien TRAE mercadería, se anota como venta (solo se frenó "te/le/se llevo"). Ambiguo de por sí: "llevo 10 yerbas" es también la forma normal de comprar | R | baja | sí | aceptado como límite, salvo que el dueño diga otra cosa |
| P106 | La respuesta de anular no alcanza a "5 yerbas no gracias" ni a "cambiame 5 yerbas" (no anotan, pero contestan la cuenta y cómo pedirlo), y le llega a "no quiero nada mas, gracias" (el cliente que se despide). `es_otra_cosa()` del ejemplo 12 mira solo "no quiero/necesito/llevo" y los arranques devol/devuelv/cancel/anul | R, P | baja | sí | pendiente (si entra) |
| P107 | `ingreso` desparejo, sin sumar nunca de más: "ingreso 5.0 azucar" deja el stock guardado como 30.0; "ingreso cinco azucar" suma 5 e "ingreso treinta azucar" no se entiende; "ingreso 05" suma 5; con tabulaciones (pegado desde Excel) no entra; "ingreso 5 mate" no entra aunque "mate" es parte de "Yerba mate" | R, P | baja | el 5.0, no; el resto, sí | pendiente (si entra): aceptar solo cifras enteras y guardar un entero |
| P108 | Mercadería que llega escrita con otro verbo va a Ventas y confunde al dueño: "llegaron 30 azucar", "entraron 30 azucar", "ingresar 30 azucar" o "30 azucar ingreso" contestan "De Azúcar quedan 25; no llego a 30." sin explicar cómo se anota un ingreso. No suma ni descuenta | P | baja | sí | pendiente (si entra): que `parece_un_ingreso()` mire también esos verbos |
| P109 | Producto con un número en el nombre ("Gaseosa cola 2 litros"): si la cantidad es ese mismo número, "ingreso 2 gaseosa" contesta "No entendí el ingreso" sin decir por qué (con el nombre completo entra) y "quiero 2 gaseosas" contesta solo el renglón de la lista. La parte del pedido viene del ejemplo 12 | P | baja | sí | pendiente (si entra) |
| P110 | El encabezado del programa creado dice que las pruebas pasan aunque cambies el número del envío; con `unidades_para_envio` más grande que el stock de la lista de prueba (200000) falla 1 de 15 con un error técnico. Con 1, 2, 500 y 1000 pasan las 15. Con 1 dice "Hacemos envíos desde 1 unidades" | R, P | baja | sí | pendiente (prolijidad) |
| P111 | Pedidos corrientes con una muletilla no se anotan: "dale, quiero 5 yerbas", "si, quiero 5 yerbas", "bueno dame 5 yerbas", "mejor dame 5 yerbas", "dame 5 yerbas nomas", "otras 5 yerbas", "quiero una yerba"; tampoco "necesito 12 arroz para mañana con envio" ni "quiero llevar 5 azucar". Contestan la cuenta y cómo pedirlo. Agregando "dale" y "ok" en `palabras_de_pedir()` se anotan y las 15 pruebas siguen pasando (P lo probó) | P, implementador | baja | sí | aceptado: se equivoca para el lado seguro y el encabezado dice dónde agregar palabras |
| P81 | Ventas anotaba frases de un pedido YA hecho o que no piden nada | R, P | media | no | **resuelto** (las 8 frases de la vuelta 2 y las de la vuelta 1, cada una en corrida limpia; unas 100 frases más de R y unas 190 de P). Restos bajos: P103 y P104 |
| P83 | `ingreso` aceptaba palabras de más | R, P | baja | no | **resuelto** (45 frases de R, 54 de P). Restos: P107 y P108 |
| P95 | Menos con espacio o raya, signo de pregunta ancho | R | baja | no | **resuelto** |
| P96 | Verbos comunes fuera de la lista; devolver o anular sin respuesta clara | R, P | baja | no | **resuelto**. Restos: P106 y P111 |
| P97 | `ingreso_maximo` sin revisar; `stock_minimo` muy grande rompía pruebas | R | baja | no | **resuelto** |
| P98 | El aviso no mostraba las comillas | R | baja | no | **resuelto** |
| P99 | Cinco pruebas fallaban en una ruta con espacios | P | baja | sí (3 de las 5) | **resuelto** (106 de 106) |
| P100 | `probar` mostraba errores técnicos con un número mal puesto | P | baja | no | `probar`: **resuelto** (0 de 15 con el mismo aviso en castellano). `verificar` sigue diciendo "sin errores": aceptado, lo avisan README y encabezado (R) |
| P101 | Renglón del encabezado pasado del ancho por el archivo de memoria | P | baja | no | **resuelto**. Quedan los dos renglones del archivo de casos, iguales en `nuevo mostrador` |
| P80 | Lo anotado se pierde con la X, un corte o SIGTERM | R, P | baja hoy (avisado) | el mecanismo sí | de fondo: pendiente; nadie lo volvió a probar en esta vuelta. Sigue esperando la propuesta escrita acá antes de tocar el intérprete |
| P85, P86, P87, P88 | Producto que arranca bajo el mínimo; memoria en `mate/ejemplos`; dos ventanas; producto sacado de la planilla | R, P | baja | ver vueltas 1 y 2 | solo avisados, sin cambio |
| P89 | `ensayar` depende del stock recordado | P, R | baja | no | sin tocar; pasa al cambio 2 |
| P91 | Planilla y memoria | P | baja | no | quedan: dos renglones con el mismo producto; memoria editada a mano con un texto corta la charla con un error técnico (P lo volvió a ver) |
| P92 | `VERSION` en 0.6 | R | baja | — | al cierre de la 0.7 |
| P94 | Carpetas temporales de vueltas anteriores en `/tmp` | implementador | — | — | las de esta vuelta las borró quien las creó; las viejas las borra quien las creó o el dueño |
| P11 | Sin probar en una Windows de verdad (`py`, PowerShell, Bloc de notas) | R, P, I | baja | sí | pendiente del dueño |

No verificado por nadie en esta vuelta: Windows, Python 3.10 y 3.14, pytest completo fuera de
3.13, una falla real de Compras, la IA de verdad (sin clave ni red), cerrar la ventana con la
X y el contenido de la clase 13 más allá de sus pruebas.

**Decisiones técnicas nuevas**
- P81 por posición además de por lista: las palabras de envío, de retiro y los artículos valen
  solo después de la cantidad. Un artículo o un "retiro" adelante ("los 10 arroz", "retiro 5
  yerbas") habla de algo que ya existe. Se descartó prohibir palabras sueltas: siempre aparece otra.
- Se sigue equivocando para el lado seguro: "quiero las 5 yerbas", "dame las 5 yerbas" o
  "retiro 5 yerbas" no se anotan. El dueño agrega palabras en `palabras_de_pedir()`; lo dicen
  el encabezado (punto 6) y el README.
- "manden", "envien" y "traigan" quedan como palabras de pedir (P sugería sacarlas): son
  imperativos al vendedor y "manden 12 azucar a casa" se anota.
- Devolver o anular usa `entender(...).otra_cosa` del ejemplo 12, sin duplicar la lista de
  palabras, y contesta el programa antes de llegar a la IA; alcanza a "quiero devolver un
  producto" sin cantidad.
- `parece_un_ingreso()` mira solo "ingreso" o "ingresos" (ya sin tilde ni signos) seguido de un
  número: "ingresaron 5 fideos" sigue yendo a Ventas, para no cambiar lo que afirma la prueba vieja.
- El ingreso rechaza también el punto final y "de" ("ingreso 5 de yerba"): el README promete
  "y nada más" y el mensaje dice cómo va.
- No hay tope para `stock_minimo`: las pruebas del equipo creado son paramétricas (yerba =
  mínimo + 100000) y las dos de ingreso se saltean, con un comentario, el tramo que necesita
  meter más que `ingreso_maximo` de una vez.
- `numeros_mal_puestos()` y `como_esta_escrito()` van bajo "El programa" del ejemplo 13, junto
  a `que_arreglar()`; `abrir_el_negocio()` (bajo "El equipo") las llama. Se copian las dos
  partes al programa creado.
- No se agregaron "mañana" ni "hoy": el equipo no guarda fechas y diría "Anotado" sin la fecha.
- Integrador: no arregló nada en esta vuelta. P102 cambia qué se anota y pide prueba y
  revisión independiente. Aunque ya estaba y R aprobó, frena el cierre: saca stock y cobra diez
  veces lo pedido sin forma de anular, contra "ante la duda no se anota". P80 de fondo sigue
  esperando una propuesta escrita acá.

**Para la vuelta 4**: P102 (obligatorio), con las frases de P como prueba. Si entran, porque
tocan el mismo tramo: P103 y el matiz del README de P104. Después: P106, P107, P108, P109 y
P110. P89 pasa al cambio 2. El orden del dueño sigue igual: primero A, después B; nada de B todavía.

### Cambio 2: ensayar la conversación entre agentes, vuelta 1 — NO cerrado

Revisor y agente de pruebas no aprobaron. Quedan tres problemas medios nuevos: P112 (un
`enviar` hecho mientras se atiende la pregunta no cuenta como que viajó), P113 (una regla de
mensajes mal armada pasa en silencio) y P114 (un caso viejo cambia de resultado). El camino
normal del criterio se cumple.

Nota del integrador: el cambio 1 sigue NO cerrado (queda P102, vuelta 4 pendiente). Este
cambio se hizo encima igual; los dos son parte de A y nada de B se empezó.

**Qué se hizo** (commit `3510471`, implementador; local, sin push, sin tocar `main` ni este
archivo). Tocó `mate.py`, `test_mate.py`, `casos_del_equipo.txt`, README y MEJORAS.
- Formato nuevo en el archivo de casos de `ensayar`, debajo de la pregunta y junto a `tiene
  que decir:` / `no puede decir:`: `tiene que viajar: Reservar de Ventas a Deposito` y `no
  tiene que viajar: Reponer`. Va el nombre del mensaje y, optativos, `de` quién y `a` quién;
  con `|` se dan opciones; da igual mayúsculas y tildes; también valen `debe viajar`, `no debe
  viajar` y `no puede viajar`; el programa se escribe `el programa`.
- Cuenta como "viajó" lo entregado entre agentes desde que el programa lee la pregunta hasta
  que vuelve a pedir por teclado: `preguntar`, `enviar` y las respuestas (`responder`). Lo de
  antes de la pregunta no cuenta. Hoy esto no se cumple del todo con `enviar`: ver P112.
- Antes de ensayar se revisa que cada mensaje y agente nombrado exista en el programa (incluye
  lo traído con `usar`); si no, sale con código 2 y un error con archivo:renglón y sugerencia
  ("casos.txt:3: el programa no tiene ningún mensaje llamado 'Reponr'. ¿Quisiste decir
  'Reponer'?"). Una regla mal escrita (sin dos puntos, `puede viajar:`, `biajar`) se avisa en
  su renglón. Deja pasar otras: ver P113.
- Cuando un caso falla, el informe muestra "No cumple: tiene que viajar: ..." (como va en el
  archivo) y "La conversación de este caso", con los renglones de la traza de esa pregunta
  numerados desde 1 y recortados a 300 letras. Sale si el caso tiene reglas de mensajes o si
  en esa pregunta se hablaron dos agentes.
- Un caso que falla por los mensajes no deja lección propuesta por eso: el informe dice "Qué
  mensajes viajan lo decide el programa, no la IA"; si además falló una regla de "decir", la
  lección nombra solo esa.
- Casos viejos: `caso['reglas']` conserva su forma y las reglas de mensajes van aparte en
  `caso['mensajes']`; el informe de un mostrador de un solo agente no cambió (una prueba lo fija).
- `mate/ejemplos/casos_del_equipo.txt` usa el formato nuevo: explicación en "Cómo se escribe",
  reglas de mensajes en todos los casos y un caso nuevo ("quiero 20 azucar": Depósito le pide
  la reposición a Compras). Pasan a ser 9 casos; `nuevo equipo` copia ese archivo.
- README (sección nueva "Ensayar la conversación de un equipo", con el informe real de un caso
  que falla; fila en "Qué se está sumando para la 0.7"), `ayuda`, `guia`, MEJORAS 125 y el
  aviso de "`--traza` no va con `ensayar`" reescrito.
- 17 pruebas nuevas (con las parametrizadas) al final de `test_mate.py`.
- No se tocó el lenguaje: siguen 36 palabras y 48 funciones incluidas.

**No se hizo** (declarado por el implementador): exigir el orden de los mensajes, cuántas
veces viaja uno o mirar sus campos (a propósito, anotado en MEJORAS 125); `--traza` con
`ensayar` sigue rechazado; no tocó la clase 13 ni el encabezado del ejemplo 13; no probó en
Windows, en Python 3.10 a 3.13 ni contra una IA de verdad; después del último retoque (el
texto del aviso de `--traza`) corrió solo las 54 pruebas de ensayar/conversación (R, P e I
corrieron todo sobre el commit final). Además borró
`mate/ejemplos/13_equipo_del_negocio.memoria.json`, que había dejado él mismo al correr el
ejemplo 13 en su lugar (archivo ignorado por git; es P86): si ya existía de antes con otro
contenido, se perdió.

**Quién revisó y quién probó**: revisor (R) y agente de pruebas (P), cada uno sobre una copia
en una carpeta temporal propia. Integrador (I): las tres corridas y este registro; no tocó
código ni pruebas.

**Veredictos**: R **no aprueba** (dos medios: P112 y P113; cuatro bajos). P **no aprueba**
(dos medios: P113 y P114; cinco bajos). Cambio 2 **NO cerrado**.

**Pruebas** (integrador, Linux, `MATE_SIN_REGISTRO=1`, sobre `3510471`, Python 3.13.18)
- `pytest mate/pruebas mate/modelo`: 955 pasan, 0 fallan (antes 938). Implementador, R y P
  dieron el mismo número.
- `probar mate/ejemplos`: 92 de 92, en 19 archivos. `probar mate/curso`: 37 de 37, en 26 archivos.
- Después de todo, `git status --short` vacío y ninguna memoria en `mate/ejemplos`.
- Reproducido por I, en una carpeta temporal propia (ya borrada), sobre un equipo creado con
  `nuevo equipo`: `ensayar` con los casos de muestra da 9 de 9. P112: "ingreso 30 azucar" con
  `no tiene que viajar: Llego` da "1 de 1 casos pasaron", y la misma pregunta corrida con
  `--traza` muestra "Deposito → Compras: Llego". P113: "quiero 3 yerbas" con `no tiene que
  viajar: Reservar a Deposito de Ventas` y `no tiene que viajar: Reservar de Ventas a` da "1 de
  1 casos pasaron". P115: "mi hijo viaja: quiero 3 yerbas" corta con "este renglón parece una
  regla de mensajes". I no reprodujo P114 (lo hicieron R y P, cada uno con un programa propio,
  comparando con el `mate.py` de `HEAD~1`).
- Pruebas viejas tocadas (R revisó los renglones quitados): solo "8 de 8 casos pasaron" pasó a
  "9 de 9" en `test_el_equipo_creado_se_puede_abrir_con_el_bloc_de_notas_y_se_ensaya_sin_tocar_el_stock`,
  porque los casos de muestra son nueve. Ninguna se quitó ni afirma menos.
- Todo con el Python 3.13 de la máquina. Nadie corrió en 3.10, 3.11, 3.12 ni 3.14, ni en una
  Windows de verdad, ni contra una IA real.

**Criterios de aceptación del cambio 2**

| Criterio | Estado | Evidencia |
|---|---|---|
| Un caso puede decir "tiene que viajar X de A a B" y "no tiene que viajar X" | cumple en el camino normal, con reservas | 9 de 9 con los casos de muestra; mayúsculas, tildes, comillas, `el programa`, `\|`, solo `de` o solo `a`, copias de agentes, BOM + CRLF + tabuladores, `--veces=3` (R, P). No ve lo mandado con `enviar` durante la pregunta (P112); una regla mal armada con "no" pasa siempre (P113) |
| Falla con un mensaje claro que muestra la conversación | cumple, con reservas | código 1, "No cumple: ..." y la conversación numerada desde 1; con el equipo roto (`stock_minimo = 0`) coincide con el informe del README; un agente que falla se ve en la conversación (R, P). Con un `enviar` en cola dice "no viajó ningún mensaje" (P112); con una regla mal armada no explica que está mal escrita (P113) |
| Los casos viejos siguen andando igual | no cumple del todo | los ejemplos 10, 11 y 12 con `casos.txt` dan el mismo informe con `HEAD~1` y con `HEAD` (diff de P). Cambian: un programa que hace `enviar` antes de leer (P114) y una pregunta con "viaja:" o que empieza con "tiene que viajar" (P115) |
| Para todo: pruebas que ya había, sin aflojar | cumple | 955 / 92 de 92 / 37 de 37; una sola prueba vieja tocada, por el conteo |
| Para todo: topes, red, claves, README/`ayuda`/MEJORAS | cumple, con pendientes | 36 palabras y 48 funciones; `ensayar` no cambia la memoria (mismo md5, P); sin claves. README y MEJORAS 125 prometen de más: "`enviar` cuenta" (P112) y "un nombre mal escrito no pasa en silencio" (P113) |

**Problemas** (R = revisor, P = agente de pruebas, I = integrador)

| # | Problema | Quién | Gravedad | ¿Ya estaba? | Estado |
|---|---|---|---|---|---|
| P112 | Un mensaje mandado con `enviar` MIENTRAS se atiende la pregunta no cuenta como que viajó: queda en la cola y el ensayo corta el programa cuando vuelve a pedir por teclado, antes de entregarlo. `tiene que viajar: Llego de Deposito a Compras` falla con el programa bien, y `no tiene que viajar: Llego` (o `SigueFaltando`) pasa SIEMPRE. Pasa en el ejemplo 13 y en `nuevo equipo` (Ingreso → `enviar Llego` a Compras). Con un `enviar` del programa principal el informe dice además "En este caso no viajó ningún mensaje: nadie le habló a ningún agente". MEJORAS 125 dice que `enviar` cuenta; el README no avisa | R (media), P (baja); reproducido por I | media | no | pendiente (vuelta 2, obligatorio): al segundo `leer()`, antes de cortar, entregar lo que quedó en cola y contarlo; con prueba (el caso de `ingreso` del equipo). Como mínimo, no dejar pasar en silencio un "no tiene que viajar" de un mensaje que quedó en cola |
| P113 | La revisión de nombres (`revisar_viajes`) deja pasar reglas mal armadas, y con "no tiene que viajar" pasan siempre: orden al revés (`Reservar a Deposito de Ventas`), sin destino (`Reservar de Ventas a`), `de Ventas a Deposito y Reserva`, `de Ventas hacia Deposito`, `de Ventas zzz a Deposito`, `a Vendedor Oeste` (copia que no existe). Todo lo que sigue a `de`/`a` se toma como nombre del agente y se acepta si EMPIEZA con el nombre de un agente y un espacio (el atajo para copias), aunque el programa no cree copias. Con "tiene que viajar" el caso falla sin explicar que la regla está mal escrita. README y MEJORAS 125 prometen lo contrario | R, P; reproducido por I | media | no | pendiente (vuelta 2, obligatorio): aceptar "Agente Algo" solo si el programa crea esa copia (o validar contra los nombres reales); error con renglón para el orden invertido y para `de X a` sin destino; con estas reglas como prueba |
| P114 | Un caso viejo (sin reglas de mensajes) que pasaba ahora falla: lo que el programa mandó con `enviar` antes de la pregunta se entrega al leerla, y lo que el agente muestre al recibirlo entra en "Contestó" de todas las preguntas. En la corrida de verdad ese texto sale recién al final, después de chau, así que el ensayo ya no refleja lo que ve el cliente. Alcance angosto: programa que hace `enviar` suelto antes del primer `leer()`, agente que muestra al recibir, pregunta que no llega a un `preguntar`. Sin prueba que lo fije | P (media), R (baja); cada uno lo reprodujo contra `HEAD~1` | media | no | pendiente (vuelta 2, obligatorio): que un caso sin reglas de mensajes conteste igual que en `HEAD~1` (por ejemplo, no contar lo de antes sin adelantar su entrega); con el caso de P como prueba. Va junto con P112: los dos tocan cuándo se vacía la cola |
| P115 | Una pregunta de cliente que ya valía ahora corta el ensayo con código 2 ("este renglón parece una regla de mensajes"): con "viaja" antes de los dos puntos ("mi hijo viaja: quiero 3 yerbas", "el pedido viaja: hoy o mañana?") o que empieza con "puede viajar" / "tiene que viajar" sin signo de pregunta. "viaja" es una palabra correcta, no un error de tipeo | R, P; reproducido por I | baja | no | pendiente (vuelta 2 si entra): sacar "viaja" de `_VIAJAR_MAL_ESCRITO`; tratar como regla solo un renglón con sangría debajo de una pregunta |
| P116 | Varios mensajes separados con coma en un renglón dan un error que no orienta: "el programa no tiene ningún agente llamado 'Ventas, Reserva de Deposito'". No dice que va un mensaje por renglón (o con `\|`) | P | baja | no | pendiente (vuelta 2 si entra, va con P113) |
| P117 | El informe escribe "(programa)" en "No cumple: tiene que viajar: Encargo de (programa) a Coordinador"; README y casos enseñan "el programa". Copiado tal cual se vuelve a leer bien | P | baja | no | pendiente (prolijidad) |
| P89 | `ensayar` usa el stock que Depósito recuerda. Sin tocar: solo está avisado en el encabezado de los casos. Con el formato nuevo fallan también las reglas de mensajes: después de vender de verdad 20 de azúcar, los casos de muestra dan 8 de 9 y el informe cierra con "Hay que cambiar el programa (o el caso)", cuando la causa es la memoria | R, P | baja | sí (cambio 1; se había pasado a este cambio y el implementador no lo nombra) | pendiente (vuelta 2 si entra): ensayar sin leer la memoria, o avisar en el informe cuando el programa tiene memoria guardada |
| P118 | No se puede exigir el orden de los mensajes, cuántas veces viaja uno ni mirar sus campos | implementador, R | baja | — | aceptado como límite de la 0.7; anotado en MEJORAS 125 |
| P86 | Correr el ejemplo 13 en su lugar deja la memoria en `mate/ejemplos`: le pasó al implementador en esta vuelta y la borró | implementador | baja | sí | solo avisado, sin cambio |
| P11 | Sin probar en una Windows de verdad (`py`, PowerShell, Bloc de notas) | R, P, I | baja | sí | pendiente del dueño |

Siguen abiertos del cambio 1, sin cambio en esta vuelta: P102 (medio, vuelta 4 obligatoria),
P103 a P111, P80 de fondo, P85, P87, P88, P91, P92 y P94.

No verificado por nadie en esta vuelta: Windows, Python 3.10, 3.11, 3.12 y 3.14, la IA de
verdad (la lección propuesta real queda cubierta solo por las pruebas con el servicio de
mentira) y si la memoria que borró el implementador tenía algo de antes.

**Decisiones técnicas nuevas**
- Las respuestas (`responder`) cuentan como mensajes que viajan: en la traza son un renglón
  más, y sería confuso que `tiene que viajar: Reserva de Deposito a Ventas` fallara teniéndolo
  a la vista.
- Los nombres se validan contra el programa antes de ensayar, sin correrlo ni gastar
  consultas, para que un "no tiene que viajar" con el nombre mal escrito no pase siempre. Hoy
  la validación tiene un agujero (P113).
- La conversación se muestra solo en casos que fallan, y solo si el caso tiene reglas de
  mensajes o se hablaron dos agentes: así el informe de un mostrador de un solo agente queda
  igual que en la 0.6.
- Durante un ensayo, lo que el programa había mandado con `enviar` antes de la pregunta se
  entrega justo al leerla, para que no figure como mensaje del caso. Esta decisión es la causa
  de P114 y queda a revisar en la vuelta 2, junto con P112.
- Un renglón que empieza con "puede viajar..." y lleva signo de pregunta se toma como pregunta
  de cliente, no como regla mal escrita. Sin el signo, corta (P115).
- Se agregó un caso a los de muestra del equipo (9 en vez de 8) en lugar de solo sumar reglas:
  ninguno mostraba a Depósito hablándole a Compras.
- No se agregó ninguna palabra ni función incluida: el cambio es solo en el archivo de casos y
  en el informe.
- Integrador: toma la gravedad más alta cuando R y P no coinciden (P112 y P114 quedan medios).
  No arregló nada en esta vuelta: los tres medios cambian comportamiento y piden prueba y
  revisión independiente.

**Para la vuelta 2 del cambio 2**: P112, P113 y P114 (obligatorios), con los casos de R y P
como prueba. Si entran, porque tocan el mismo tramo: P115, P116, P117 y P89. Sigue pendiente
la vuelta 4 del cambio 1 (P102). El orden del dueño sigue igual: primero A, después B; nada de
B todavía.

### Cambio 2: ensayar la conversación entre agentes, vuelta 2 — NO cerrado

Revisor y agente de pruebas no aprobaron. Queda UN problema medio nuevo, que los dos
encontraron por separado: P119 (al entregar lo mandado con `enviar` por la pregunta, el ensayo
se saltea lo que el programa había mandado antes y seguía en la cola; el agente recibe los
mensajes en otro orden que en la corrida de verdad). Los tres medios de la vuelta 1 (P112, P113
y P114) quedan resueltos en los caminos del registro, y también P116 y P117.

Nota del integrador: el cambio 1 sigue NO cerrado (queda P102, vuelta 4 pendiente). Nada de B
se empezó: el orden del dueño sigue siendo primero A, después B.

**Qué se hizo** (commit `4b7f812`, implementador; local, sin push, sin tocar `main` ni este
archivo). Tocó `mate.py`, `test_mate.py`, `casos_del_equipo.txt`, README y MEJORAS.
- P112: en un caso con reglas de mensajes, cuando el programa vuelve a pedir por teclado se
  entrega lo que quedó mandado con `enviar` por esa pregunta y cuenta como que viajó. En la
  conversación va debajo del renglón "lo que sigue quedó mandado con 'enviar': llega después de
  contestarle al cliente". Lo que muestren los agentes en esa entrega no entra en la respuesta.
  También anda con un `enviar` del programa principal.
- P114: lo mandado con `enviar` antes de la pregunta ya no se adelanta. Si llega mientras se
  atiende la pregunta, no se cuenta ni se muestra. Un caso sin reglas de mensajes no entrega
  nada de más. El caso de P de la vuelta 1 (`cadena.mate`) vuelve a dar 1 de 1 y quedó como prueba.
- P113: después de `de` y de `a` vale solo el nombre exacto de un agente, `el programa` o una
  copia que el programa crea con `crear ... llamado "..."`. Cortan con código 2 y renglón el
  orden al revés, la regla sin destino, `y Reserva`, `hacia`, `zzz`, los paréntesis y la copia
  que no existe, con `tiene que viajar` y con `no tiene que viajar`.
- P116: dos mensajes separados con coma dan un error que dice que va un mensaje por regla.
- P115: se sacó "viaja" de la lista de errores de tipeo; las tres preguntas del registro
  vuelven a ser preguntas. Se toma por regla mal escrita lo que tiene forma de regla.
- P117: el informe escribe "el programa" en "No cumple", como enseñan el README y los casos.
- P89: cuando algún caso falla y los agentes tienen algo recordado, el informe termina con un
  aviso ("Ojo: ... arrancan cada pregunta con lo que recuerdan...") que nombra `--olvidar`. Si
  todos pasan no dice nada.
- Casos de muestra del equipo (y los que crea `nuevo equipo`): se sumó "ingreso 30 azucar" con
  reglas sobre Ingreso, Llego y SigueFaltando. Ahora son 10. El encabezado explica `el
  programa` y "un mensaje por regla".
- 38 pruebas nuevas (con las parametrizadas) al final de `test_mate.py`.
- README (sección "Ensayar la conversación de un equipo") y MEJORAS 125 (nota de la vuelta 2).
  No se tocó el lenguaje: siguen 36 palabras y 48 funciones incluidas.

**No se hizo** (declarado por el implementador): probar en una Windows de verdad ni contra una
IA real; `pytest` completo solo en 3.13 (las otras versiones no tienen pytest instalado; en
3.10, 3.11, 3.12 y 3.14 corrió `nuevo equipo`, `probar`, `ensayar` con los casos de muestra y
`probar` de ejemplos, y en 3.10 y 3.14 también el curso); sigue sin poder exigirse orden,
cantidad ni campos (P118); P89 quedó como aviso, no como arreglo; una copia cuyo nombre se arma
al correr no se revisa antes de ensayar (dicho en el README; ver P121); el "en respuesta al N"
puede quedar corrido (P122); un caso sin reglas de mensajes con un solo agente no muestra el
renglón de lo mandado con `enviar` (P126); no tocó `ayuda`, la guía, la clase 13 ni el
encabezado del ejemplo 13. Además dejó cosas fuera del repositorio: instaló Python 3.10 y 3.14
con `uv python install` (quedaron en la carpeta de uv del usuario) y dejó en `/tmp` varias
carpetas temporales propias con copias de ejemplos (P127).

**Quién revisó y quién probó**: revisor (R) y agente de pruebas (P), cada uno sobre una copia
del commit `4b7f812` en una carpeta temporal propia, ya borrada. Integrador (I): las tres
corridas, dos reproducciones y este registro; no tocó código ni pruebas.

**Veredictos**: R **no aprueba** (un medio: P119; seis bajos). P **no aprueba** (un medio:
P119; siete bajos). Cambio 2 **NO cerrado**.

**Pruebas** (integrador, Linux, `MATE_SIN_REGISTRO=1`, sobre `4b7f812`, Python 3.13.18)
- `pytest mate/pruebas mate/modelo`: 993 pasan, 0 fallan (antes 955). Implementador, R y P
  dieron el mismo número.
- `probar mate/ejemplos`: 92 de 92, en 19 archivos. `probar mate/curso`: 37 de 37, en 26 archivos.
- Después de todo, `git status --short` vacío y ninguna memoria en `mate/ejemplos`.
- Reproducido por I, en una carpeta temporal propia (ya borrada):
  - Equipo creado con `nuevo equipo`: `ensayar` con los casos de muestra da 10 de 10. P112
    arreglado: "ingreso 30 azucar" con `no tiene que viajar: Llego` da 0 de 1 y muestra
    "Deposito → Compras: Llego" debajo del renglón de lo mandado con `enviar`.
  - P119, con el programa de P (`enviar Inventario { stock: 40 }` antes del primer `leer()` y
    `enviar Ingreso { cantidad: 30 }` por la pregunta): `correr --traza` muestra "Deposito →
    Compras: Bien { quedan: 70 }"; `ensayar` da 0 de 1, muestra "Deposito → Compras: Falta {
    quedan: 30 }" y dice "Hay que cambiar el programa (o el caso)".
  - P120: "hola" con `no tiene que viaja: Reponer` y `no puede decir: zzz` da "2 de 2 casos
    pasaron" y gasta 2 consultas.
- R y P compararon contra el `mate.py` anterior al cambio 2 (commit `5433170`): los ejemplos
  10, 11 y 12 con `casos.txt` (P también con `--veces=3`) y el 13 con los casos viejos dan el
  mismo informe (diff vacío).
- Pruebas viejas tocadas (R revisó los renglones quitados): solo conteos de los casos de
  muestra ("9 de 9" pasó a "10 de 10", "8 de 9" a "9 de 10" y `len == 9` a 10). Ninguna se
  quitó ni afirma menos.
- Otras versiones: P corrió con Python 3.10.20 y 3.14.6 el ejemplo 13 con
  `casos_del_equipo.txt` (10 de 10) y sus casos propios, con el mismo resultado que en 3.13. El
  implementador declara 3.10, 3.11, 3.12 y 3.14 sin pytest. I y R corrieron solo con 3.13.
  Nadie corrió `pytest` fuera de 3.13, ni en una Windows de verdad, ni contra una IA real.

**Criterios de aceptación del cambio 2**

| Criterio | Estado | Evidencia |
|---|---|---|
| Un caso puede decir "tiene que viajar X de A a B" y "no tiene que viajar X" | cumple en el camino normal; no cumple en un caso angosto | 10 de 10 con los casos de muestra; lo mandado con `enviar` por la pregunta cuenta (P112: R, P, I); 25 reglas mal armadas (R) y 27 (P) cortan con archivo:renglón (P113, P116); copias con `de`, tildes y ñ en el nombre andan. Falla si quedó algo mandado antes de la pregunta: `no tiene que viajar: Llego` pasa aunque Llego viaja de verdad (P119) |
| Falla con un mensaje claro que muestra la conversación | cumple, con una reserva | código 1, "No cumple: ..." con `el programa` (P117), conversación numerada; el informe del README con `stock_minimo = 0` se reproduce igual (P). En P119 la conversación que muestra no es la de la corrida de verdad |
| Los casos viejos siguen andando igual | cumple, con un resto bajo | diff vacío contra `5433170` en los ejemplos 10, 11, 12 y 13 (R, P); el programa de P con `enviar` antes de leer vuelve a dar lo mismo que antes del cambio (P114). Resto: cuatro preguntas raras con forma de regla siguen cortando (P115) |
| Para todo: pruebas que ya había, sin aflojar | cumple | 993 / 92 de 92 / 37 de 37; pruebas viejas tocadas solo en el conteo de casos de muestra |
| Para todo: topes, red, claves, README/`ayuda`/MEJORAS | cumple, con pendientes | 36 palabras y 48 funciones; `ensayar` no cambia ni crea la memoria (mismo md5: R, P); sin claves ni datos personales en el diff. README y MEJORAS 125 no dicen que lo mandado antes no se entrega (P119) y prometen tomar por regla mal escrita lo que "nombra un mensaje del programa" (P120) |

**Problemas** (R = revisor, P = agente de pruebas, I = integrador)

| # | Problema | Quién | Gravedad | ¿Ya estaba? | Estado |
|---|---|---|---|---|---|
| P119 | En un caso con reglas de mensajes, la entrega de lo mandado con `enviar` se hace FUERA DE ORDEN cuando en la cola todavía hay algo mandado antes de la pregunta: `preguntar_al_programa()` aparta lo de antes, entrega solo lo de la pregunta y vuelve a poner lo de antes. En la corrida de verdad llega primero lo de antes. Si eso prepara al agente (un inventario mandado con `enviar`), el ensayo muestra una conversación que no ocurre: con el programa bien fallan `tiene que viajar: Llego de Deposito a Compras` y `no tiene que viajar: SigueFaltando`, y `no tiene que viajar: Llego` PASA aunque Llego viaja (falso aprobado, la misma clase que P112). Si el agente comprueba con `asegurar` que ya recibió el inventario, el ensayo dice "El programa falló". Alcance angosto: programa que prepara un agente con `enviar` antes del primer `leer()`, sin un `preguntar` en el medio, y pregunta que se atiende con otro `enviar`. No afecta al ejemplo 13 ni a `nuevo equipo`. La prueba `test_un_caso_viejo_contesta_igual...` fija "ni se entrega" sin mirar el orden; README y MEJORAS 125 no lo avisan | R, P (cada uno con un programa propio); reproducido por I | media | no (nace del arreglo de P112 y P114) | pendiente (vuelta 3, obligatorio): no apartar lo de antes; entregarlo en su orden sin contarlo ni mostrarlo. Con los programas de R y de P como prueba, comparando con `correr --traza` |
| P120 | Una regla de mensajes con la palabra clave mal escrita pasa en silencio como una pregunta más cuando debajo hay otras reglas: `no tiene que viaja: Reponer` (cortaba en la vuelta 1; se perdió al arreglar P115), `no tiene que viajar el reponer`, `no tiene que viajar; Reponer`, `no tiene que vijar: Reponer`, `no viaja: Reponer`. El informe la lista como "✓ no tiene que viaja: Reponer", cuenta un caso de más y gasta una consulta. El README promete avisar lo que "nombra un mensaje del programa". Si es la única regla del caso corta, pero señala el renglón de la pregunta. La misma clase ya existía en la 0.6 con `no puede dice:` | R, P; reproducido por I | baja | en parte (`viaja:` es retroceso de esta vuelta) | pendiente (vuelta 3 si entra): avisar un renglón con sangría, debajo de una pregunta, que empieza con "no tiene que", "tiene que", "no puede" o "debe" y nombra un mensaje del programa |
| P115 | Resto: siguen cortando con código 2 preguntas que valían antes del cambio 2: "Tiene que viajar Juan", "debe viajar Pedido a Rosario", "el pedido tiene que viajar: hoy", "tiene que viajar: hoy". Las tres del registro ya dan igual que antes; P probó 30 renglones de clientes que hablan de viajar y 23 siguen siendo preguntas | R | baja | no | resuelto en lo del registro; el resto queda aceptado (son preguntas raras para un mostrador y el error dice el renglón). Va contra P120: aflojar acá abre más reglas mal escritas en silencio |
| P121 | Si el programa tiene UN `crear Agente llamado <algo que no es texto fijo>` (aunque esté en una función que nunca se llama), cualquier cosa que empiece con el nombre de ese agente pasa la revisión: `no tiene que viajar: Pedido a Vendedor Centro y Caja` da 1 de 1. El README avisa el límite de la copia con nombre armado, pero no que apaga la revisión para todas las copias de ese agente | R | baja | no | pendiente (vuelta 3 si entra): como mínimo decirlo en el README; mejor, avisar en el informe que esa regla no se pudo revisar |
| P122 | El "en respuesta al N" de la conversación del informe queda corrido en uno cuando un mensaje de antes de la pregunta se entrega intercalado. Qué mensajes se cuentan está bien | implementador (declarado), P (reproducido); R no lo reprodujo | baja | no | pendiente (vuelta 3 si entra; toca el mismo tramo que P119) |
| P123 | Si dos agentes entran en bucle con `enviar`, un caso con reglas de mensajes no se cuelga (corta con "se superaron 100000 mensajes"), pero el informe vuelca la conversación entera: 100.015 renglones, 6,6 MB. No hay tope de cantidad de renglones | P | baja | no | pendiente (vuelta 3 si entra): mostrar los primeros y los últimos renglones y decir cuántos se saltearon |
| P124 | La cuenta que se anuncia antes de ensayar ("hasta N consultas a la IA: una por cada pregunta") se queda corta cuando un agente consulta a la IA al recibir un `enviar` que ahora se entrega: con 2 preguntas anuncia "hasta 2" y hace 4. Con la IA de verdad cada una se paga | P | baja | no | pendiente (vuelta 3 si entra): ajustar el texto del anuncio para los casos con reglas de mensajes |
| P125 | Errores poco claros, todos con código 2: `Reservar del programa a Ventas` no sugiere "de el programa"; una copia llamada "a" o un agente llamado A no se pueden nombrar después de `de` | P | baja | no | pendiente (prolijidad): aceptar "del programa" |
| P126 | Un caso de equipo SIN reglas de mensajes que falla y donde habló un solo agente no muestra ni la conversación ni el renglón de lo mandado con `enviar` | implementador (declarado), P | baja | no | aceptado: así el informe de un solo agente queda como en la 0.6; el README lo dice |
| P127 | El implementador dejó cosas fuera del repositorio: Python 3.10 y 3.14 instalados con `uv python install` en la carpeta de uv del usuario, y varias carpetas temporales propias en `/tmp` | implementador (declarado) | baja | no | avisado al dueño; I no borró nada porque no las creó. Para adelante: cada agente borra sus carpetas al terminar |
| P112 | Lo mandado con `enviar` mientras se atiende la pregunta no contaba | R, P, I | media | — | resuelto en el camino del registro (ejemplo 13, `nuevo equipo`, `enviar` del programa y en cadena). Su resto es P119 |
| P113 | Reglas mal armadas pasaban en silencio | R, P | media | — | resuelto (25 reglas de R y 27 de P cortan con renglón). Resto bajo: P121 |
| P114 | Un caso viejo cambiaba de resultado | R, P | media | — | resuelto (diff vacío contra `5433170`; con prueba) |
| P116 | Dos mensajes con coma daban un error que no orientaba | P | baja | — | resuelto ("En cada regla va un solo mensaje") |
| P117 | El informe escribía "(programa)" en "No cumple" | P | baja | — | resuelto |
| P89 | `ensayar` arranca con el stock que Depósito recuerda, no con el de la planilla: después de vender de verdad, los casos de muestra dan 9 de 10. Ahora el informe termina con el aviso y nombra `--olvidar`; si todos los casos pasan no dice nada | R, P | baja | sí (cambio 1) | aceptado como aviso (R y P lo dan por bueno para esta vuelta) |
| P118 | No se puede exigir el orden de los mensajes, cuántas veces viaja uno ni mirar sus campos | implementador | baja | sí | aceptado como límite de la 0.7 |
| P11 | Sin probar en una Windows de verdad (`py`, PowerShell, Bloc de notas) ni contra una IA real | implementador, R, P, I | baja | sí | pendiente del dueño |

Siguen abiertos del cambio 1, sin cambio en esta vuelta: P102 (medio, vuelta 4 obligatoria),
P103 a P111, P80 de fondo, P85, P86, P87, P88, P91, P92 y P94.

No verificado por nadie en esta vuelta: Windows, la IA de verdad, y `pytest` completo en
Python 3.10, 3.11, 3.12 y 3.14 (en esas versiones solo se corrieron `probar` y `ensayar`).

**Decisiones técnicas nuevas**
- La entrega de lo mandado con `enviar` se hace solo en casos con reglas de mensajes. Así un
  caso viejo da exactamente lo mismo que antes del cambio 2: sin consultas, errores ni textos
  nuevos por una entrega que antes no ocurría.
- Lo que un agente muestra al recibir un `enviar` entregado después de contestar no entra en
  `tiene que decir` ni en `no puede decir`: en la corrida de verdad el cliente lo ve después.
- Si un agente falla al recibir ese `enviar`, el caso con reglas de mensajes falla con "El
  programa falló". El mismo caso sin reglas de mensajes no lo entrega y pasa como siempre.
- Lo "de antes de la pregunta" se reconoce por el número de conversación del mensaje: no se
  cuenta, no se muestra y no gasta número. Hoy además se aparta de la cola al entregar lo de
  la pregunta; esa parte es la causa de P119 y se revierte en la vuelta 3 (se entrega en su
  orden, sin contar ni mostrar). `leer()` adentro de un agente está prohibido por el lenguaje,
  así que el filtro no deja afuera mensajes de un agente que lee del teclado (R).
- No se usa la sangría para decidir si un renglón es una regla mal escrita (lo sugería el
  registro de la vuelta 1): pruebas viejas exigen error en renglones sin sangría. Se decide por
  la forma del renglón. Consecuencia: P120.
- El orden invertido (`a X de Y`) da error en vez de aceptarse: un nombre de copia puede llevar
  "de" adentro y aceptar los dos órdenes sería ambiguo.
- El aviso de memoria (P89) sale también en un mostrador de un solo agente con estado
  recordado cuando un caso falla. Es un renglón al final; no cambia qué casos pasan.
- Integrador: P119 queda medio (R y P coinciden) porque da un falso aprobado de "no tiene que
  viajar" y contradice el criterio "el ensayo muestra la conversación". No arregló nada en esta
  vuelta: el arreglo cambia cuándo se vacía la cola y pide prueba y revisión independiente.

**Para la vuelta 3 del cambio 2**: P119 (obligatorio), con los programas de R y P como
prueba. Si entran, porque tocan el mismo tramo: P122, P120, P121, P123, P124 y P125. Sigue
pendiente la vuelta 4 del cambio 1 (P102). Primero A, después B; nada de B todavía.

### Cambio 2: ensayar la conversación entre agentes, vuelta 3 — cerrado

Revisor y agente de pruebas aprobaron. P119, el medio que quedaba, está arreglado: los dos lo
comprobaron por separado, cada uno con programas propios y comparando con `correr --traza`.
Nadie encontró problemas altos ni medios. Quedan solo bajos (tabla de abajo).

Nota del integrador: el cambio 1 sigue NO cerrado (queda P102, vuelta 4 pendiente). Nada de B
se empezó: el orden del dueño sigue siendo primero A, después B.

**Qué se hizo** (commit `5e07572`, implementador; local, sin push, sin tocar `main` ni este
archivo). Tocó `mate.py`, `test_mate.py`, README y MEJORAS.
- P119: `preguntar_al_programa()` ya no aparta lo mandado antes de la pregunta. La cola se
  vacía entera y en su orden: lo de antes llega primero y el agente lo recibe, pero no se
  cuenta ni se muestra. Con el programa de R (Inventario 50 + Ingreso 5) el ensayo ve `Llego`,
  igual que la corrida de verdad; con el de P ve `Bien { quedan: 70 }`. La variante con
  `asegurar` ya no da "El programa falló". `no tiene que viajar: Llego` ahora falla, como
  corresponde.
- P122: "en respuesta al N" usa el número con que se mostró el mensaje (`Interprete.vistos`).
- P120: un renglón debajo de otra pregunta, que empieza como regla, tiene una palabra parecida
  a "viajar" y nombra un mensaje del programa, corta con código 2 en su renglón (`viaja:`,
  `viajar el reponer`, `viajar;`, `viajar.`, `vijar:`, `no viaja:`). Si es la única regla del
  caso y tiene sangría, el error señala ese renglón y no el de la pregunta (también `no puede
  dice: descuento`). Queda un resto: ver P120 en la tabla.
- P121: las copias con nombre fijo se revisan aunque el programa tenga otra con nombre armado
  al correr. La que no se puede saber antes se compara, después de ensayar el caso, con los
  agentes que hubo; si no hubo ninguno, el informe avisa debajo del caso ("Ojo: en este caso no
  hubo ningún agente llamado ..."). Es un aviso: el caso igual cuenta como pasado.
- P123: la conversación del informe muestra 60 renglones como mucho (los primeros 50, los
  últimos 10 y cuántos se saltean). El caso del bucle pasa de 100.015 renglones a 75.
- P124: si hay casos con reglas de mensajes y el programa llama a `consultar_ia()`, el anuncio
  agrega "Pueden ser más: ...". El número sigue siendo "hasta N".
- P125: `del programa` y `al programa` dan un error que dice cómo va (`de el programa`, `a el
  programa`).
- El error de "este renglón parece una regla de mensajes" ahora termina diciendo la salida:
  si es una pregunta de un cliente, terminarla con `?`.
- 12 funciones de prueba nuevas (21 casos) en `test_mate.py`, entre ellas los programas de R y
  de P para P119 comparados con la traza de una corrida de verdad.
- README (sección "Ensayar la conversación de un equipo") y MEJORAS 125 ("Nota de la vuelta
  3"). No se tocó el lenguaje: ni palabras ni funciones incluidas nuevas.

**No se hizo** (declarado por el implementador): no sumó casos al ejemplo 13 ni a
`casos_del_equipo.txt`, aunque la tarea lo pedía (los arreglos no tocan ese programa y un caso
más cambia el "10 de 10" que fijan pruebas viejas; las pruebas nuevas están en `test_mate.py`);
el resto de P115 sigue cortando; P125 a medias (una copia llamada "a" o un agente llamado A);
P126 y P89 quedan como estaban; para P124 no probó el caso de `consultar_ia()` en un archivo
traído con `usar` (R y P lo probaron: el anuncio sale); `pytest` completo solo en Python 3.13;
nada en Windows ni contra una IA de verdad; no actualizó `docs/index.html` ni `ayuda`; no borró
los Python 3.10 y 3.14 de la carpeta de uv (P127), porque no los creó en esta vuelta.

**Quién revisó y quién probó**: revisor (R) y agente de pruebas (P), cada uno sobre una copia
del commit `5e07572` en una carpeta temporal propia, ya borrada. Integrador (I): las tres
corridas y este registro; no tocó código ni pruebas y en esta vuelta no reprodujo casos a mano.

**Veredictos**: R **aprueba** (seis bajos). P **aprueba** (ocho bajos). Cambio 2 **cerrado**.

**Pruebas** (integrador, Linux, `MATE_SIN_REGISTRO=1`, sobre `5e07572`, Python 3.13.18)
- `pytest mate/pruebas mate/modelo`: 1014 pasan, 0 fallan (antes 993). Implementador, R y P
  dieron el mismo número.
- `probar mate/ejemplos`: 92 de 92, en 19 archivos. `probar mate/curso`: 37 de 37, en 26 archivos.
- Después de las corridas, `git status --short` vacío.
- Pruebas viejas (R miró el diff): el único renglón quitado de `test_mate.py` es un comentario
  ("ni se entrega"); lo demás son 392 renglones agregados. Ninguna se quitó ni afirma menos.
- P119 (R y P, no I): R, con dos `enviar Carga` antes del `leer()` y un `enviar Pedir` por la
  pregunta, ve "Dep → Jefe: Listo { quedan: 5 }" igual que `--traza`. P, con el programa de R
  más `asegurar`: `tiene que viajar: Llego de Deposito a Compras` y `no tiene que viajar:
  SigueFaltando` dan 1 de 1; `no tiene que viajar: Llego` da 0 de 1 con código 1 y la
  conversación de verdad; con `--veces=3`, 3 de 3. P probó además hijos y nietos mandados con
  `enviar`, un `preguntar` hecho por lo de antes, un programa que lee una sola vez, y la cola
  con solo cosas de antes (no se entrega nada y `tiene que viajar: Inventario` falla).
- P122 (P): con mensajes de antes y de la pregunta intercalados, el informe numera 1 a 14 y
  cada "en respuesta al N" señala el renglón correcto. R lo leyó en el código.
- P120, P121, P123, P124 y P125: ejecutados por R y P (bucle: 75 renglones, 1,8 s; con 60
  renglones no se saltea nada y con 61 se saltea 1).
- Casos viejos: R comparó el informe de `HEAD~1` con el de `HEAD`: idéntico para `nuevo equipo`
  (10 de 10); en los ejemplos 12 (5 de 5) y 13 (10 de 10) solo se agregan los dos renglones
  "Pueden ser más" del anuncio. P comparó contra `5433170` (anterior al cambio 2): ejemplos 10,
  11 y 12 con `casos.txt` (también `--veces=2`) y el 13 con los casos viejos, diff vacío.
- Como el dueño (P): `nuevo equipo mi_negocio` crea 3 archivos; `verificar` sin errores;
  `probar` 15 de 15; `ensayar` 10 de 10; con memoria (azúcar en 5) da 9 de 10 y el aviso de
  `--olvidar`; el md5 de la memoria no cambia al ensayar. Nombres con ñ y tildes, BOM, fin de
  línea de Windows y tabulaciones andan.
- Otras versiones: R corrió con Python 3.10, 3.11, 3.12 y 3.14 `ensayar` (10 de 10 y su
  programa de P119) y `probar mate/ejemplos` (92 de 92). P, con 3.10.20 y 3.14.6, lo mismo.
  Nadie corrió `pytest` fuera de 3.13, ni en una Windows de verdad, ni contra una IA real.

**Criterios de aceptación del cambio 2**

| Criterio | Estado | Evidencia |
|---|---|---|
| Un caso puede decir "tiene que viajar X de A a B" y "no tiene que viajar X" | cumple | 10 de 10 con los casos de muestra; cumple también con lo mandado con `enviar` antes y durante la pregunta (P119: R y P, con pruebas nuevas contra la traza de verdad) |
| Falla con un mensaje claro que muestra la conversación | cumple, con una reserva baja | código 1, "No cumple: ...", conversación numerada con "en respuesta al N" correcto (P122) y tope de 60 renglones (P123). Reserva: si falla un mensaje de antes de la pregunta, ese mensaje no se ve en la conversación (P128) |
| Los casos viejos siguen andando igual | cumple, con un resto bajo | diff vacío contra `5433170` (P) y contra `HEAD~1` salvo el anuncio (R). Resto: preguntas raras con forma de regla siguen cortando (P115) y puede haber un falso aviso angosto (P129) |
| Para todo: pruebas que ya había, sin aflojar | cumple | 1014 / 92 de 92 / 37 de 37; en pruebas viejas solo cambió un comentario |
| Para todo: topes, red, claves, README/`ayuda`/MEJORAS | cumple, con pendientes | sin palabras ni funciones incluidas nuevas, las pruebas de topes pasan; `ensayar` no cambia la memoria (P); sin claves ni datos personales en el diff (R). README leído contra el código (R) y MEJORAS 125 al día; `ayuda` y `docs/index.html` no cuentan nada de esta vuelta (P133) |

**Problemas** (R = revisor, P = agente de pruebas, I = integrador)

| # | Problema | Quién | Gravedad | ¿Ya estaba? | Estado |
|---|---|---|---|---|---|
| P119 | La entrega de lo mandado con `enviar` se hacía fuera de orden cuando quedaba algo de antes de la pregunta | R, P | media | — | resuelto (la cola se vacía entera y en orden; programas de R y P como prueba) |
| P122 | "en respuesta al N" corrido en uno | P | baja | — | resuelto |
| P121 | Una copia con nombre armado al correr apagaba la revisión de todas las copias de ese agente | R | baja | — | resuelto con aviso en el informe. Resto: P130 |
| P123 | El informe volcaba la conversación entera de un bucle | P | baja | — | resuelto (60 renglones como mucho). Resto: P131 |
| P124 | El anuncio de consultas se quedaba corto | P | baja | — | resuelto en el texto ("Pueden ser más"); el número sigue siendo "hasta N" |
| P120 | Resto: una regla de mensajes mal escrita sigue pasando en silencio como una pregunta más (el informe cuenta un caso de más y la regla no se mira) en dos casos. (a) Va DESPUÉS de una regla bien escrita y antes de otra: `tiene que decir: hola` / `no tiene que viaja: Reponer` / `no puede decir: zzz` da "2 pregunta(s)". (b) Usa otro verbo, no una falta de tipeo de "viajar": `no tiene que mandar: Reponer`, `tiene que mandar: Reponer`, `no tiene que salir: Reponer` dan 2 de 2. Lo mismo `no puede dice: descuento` con otra regla después (clase de la 0.6). El README dice "debajo de otra pregunta", así que no promete de más | R (a), P (b) | baja | sí | pendiente (prolijidad): usar la sangría también cuando ya hubo reglas en el grupo (el dato ya se guarda) |
| P128 | Con el arreglo de P119, un caso con reglas de mensajes puede fallar con "El programa falló: ... al recibir X" por un mensaje mandado ANTES de la pregunta, y la conversación del informe no muestra ese mensaje. El resultado es fiel (la corrida de verdad también falla, código 1), pero cuesta ubicar de dónde sale. El README no lo dice | R, P (cada uno con un programa propio) | baja | no | pendiente: decir en el informe o en el README que el error puede venir de algo mandado antes de la pregunta |
| P129 | Posible falso aviso nuevo de P120: una pregunta de cliente sin `?`, debajo de otra pregunta, que empieza con "tiene que", "no puede" o "debe", tiene una palabra parecida a "viajar" y nombra un mensaje del programa ("no puede ser que el viaje del pedido tarde tanto", con un mensaje Pedido) cortaría con código 2. Muy angosto y el error dice la salida | R (leído en el código, no ejecutado) | baja | no | aceptado; sin verificar |
| P130 | El aviso de P121 ("Ojo: en este caso no hubo ningún agente llamado ...") sale DOS veces debajo de la primera pregunta y ninguna debajo de la segunda cuando dos preguntas comparten las reglas. R lo vio además, leyendo el código, para una copia que figura como `de` y como `a` en la misma regla | P (ejecutado), R (leído) | baja | no | pendiente (prolijidad) |
| P131 | El renglón del medio dice "acá van 1 renglones más" con 61 renglones (falta el singular) | R | baja | no | pendiente (prolijidad) |
| P132 | Con `--ia-simulada`, un caso con reglas de mensajes queda "? no se pudo comprobar" y corta el ensayo ("0 de 2 casos pasaron") si un agente consulta a la IA sin tercer valor al recibir un `enviar` que ahora se entrega; el mismo caso sin reglas de mensajes pasa. El informe no dice que la consulta que falló es la de la entrega y repite "La IA no contestó, por lo mismo que más arriba" debajo del motivo | P | baja | sí | pendiente (prolijidad): decir en el informe cuál consulta falló |
| P115 | Resto sin cambio: "Tiene que viajar Juan", "debe viajar Pedido a Rosario" y "el pedido tiene que viajar: hoy" siguen cortando; con `?` al final pasan, como ahora dice el error. "tiene que viajar: hoy?" corta igual: ahí la salida que propone el error no sirve | implementador (declarado), P | baja | sí | aceptado (aflojar va contra P120) |
| P125 | Resto: con un agente llamado A o una copia llamada "a", `tiene que viajar: HijoNuevo de A a B` corta con "no entiendo qué mensaje es ...", sin decir que el problema es el nombre | implementador (declarado), P | baja | sí | lo de `del programa` resuelto; el resto queda pendiente (prolijidad) |
| P133 | Documentación a medias: `docs/index.html` no nombra "tiene que viajar" y VERSION sigue en 0.6; `ayuda` explica las reglas de mensajes (lo básico está en `ayuda ensayar`) pero nada de esta vuelta. Tampoco se sumaron casos al ejemplo 13 ni a `casos_del_equipo.txt` | implementador (declarado), R, P | baja | sí | pendiente para el cierre de la 0.7 |
| P126 | Caso sin reglas de mensajes donde habló un solo agente: no muestra la conversación | — | baja | sí | aceptado, sin cambio |
| P89 | El ensayo arranca con lo que los agentes recuerdan | — | baja | sí | aceptado como aviso, sin cambio (P lo volvió a ver: 9 de 10 con memoria) |
| P118 | No se puede exigir orden, cantidad ni campos | — | baja | sí | aceptado como límite de la 0.7 |
| P127 | Python 3.10 y 3.14 en la carpeta de uv del usuario, de la vuelta 2 | implementador (declarado) | baja | sí | sin cambio; avisado al dueño. En esta vuelta cada agente borró su carpeta temporal |
| P11 | Sin probar en una Windows de verdad (`py`, PowerShell, Bloc de notas) ni contra una IA real | implementador, R, P, I | baja | sí | pendiente del dueño |

Siguen abiertos del cambio 1, sin cambio en esta vuelta: P102 (medio, vuelta 4 obligatoria),
P103 a P111, P80 de fondo, P85, P86, P87, P88, P91, P92 y P94.

No verificado por nadie en esta vuelta: Windows, la IA de verdad, `pytest` completo en Python
3.10, 3.11, 3.12 y 3.14 (ahí solo `probar` y `ensayar`), y P129 (solo leído en el código).

**Decisiones técnicas nuevas**
- La cola se vacía entera solo si quedó algo mandado por ESTA pregunta. Si hay únicamente
  cosas de antes, no se entrega nada, como en la vuelta 2. Lo que deriva de un mensaje viejo
  hereda su conversación y no se cuenta ni se muestra. Reemplaza la decisión de la vuelta 2 de
  apartar lo de antes (causa de P119).
- Para tomar un renglón por regla de mensajes mal escrita no alcanza con que empiece como regla
  y nombre un mensaje ("no puede ser, ya está anotado" daba falso aviso con un mensaje
  Anotado): además tiene que tener una palabra parecida a "viajar" (empieza con "viaj" o
  parecido 0,8 o más con `difflib`). Un renglón con `?` siempre es pregunta. Consecuencia: el
  resto (b) de P120.
- La sangría se usa solo en el caso sin ninguna regla bien escrita al final del archivo, donde
  todavía no se conoce el programa. Los errores viejos que valen sin sangría no cambian.
- `del programa` no se acepta como sinónimo, por la regla del README "una sola forma de
  escribir cada cosa": da un error que muestra la forma correcta. (El registro de la vuelta 2
  proponía aceptarlo.)
- `copias_del_programa()` devuelve lo mismo de siempre por defecto (una prueba vieja lo fija);
  la forma nueva sale con un segundo argumento.
- El tope de la conversación es `MAX_RENGLONES_DE_CHARLA = 60`, solo al mostrar; la
  conversación se sigue guardando entera en memoria.
- El aviso de la copia con nombre armado (P121) es un aviso, no un error: el caso cuenta como
  pasado.
- Integrador: el cambio 2 se cierra porque R y P aprueban, los tres criterios cumplen y no hay
  problemas altos ni medios. Los bajos nuevos (P128 a P133) y los restos de P120, P115 y P125
  no frenan el cierre; van a la vuelta de cierre de la 0.7 si entran.

**Lo que sigue**: vuelta 4 del cambio 1 (P102, obligatorio). Después el cambio 3 (buzón entre
programas), que empieza por la etapa de diseño revisada. Primero A, después B; nada de B todavía.

### Cambio 3: buzón entre programas, vuelta 1 — NO cerrado

Revisor y agente de pruebas NO aprobaron. Los cuatro criterios de aceptación del cambio 3 se
cumplen en el caso común, pero quedan dos problemas medios: P134 (el README promete un orden
que no se cumple entre corridas del mismo segundo) y P135 (al cerrar un mostrador con Ctrl+C se
pierde, sin aviso, el último mensaje para el otro programa). Nadie encontró problemas altos.

Notas del integrador:
- El cambio 1 sigue NO cerrado: en este archivo no hay registro de la vuelta 4 (P102, medio),
  que el registro anterior daba como obligatoria ANTES de empezar el cambio 3. El cambio 3 se
  programó igual. Queda pendiente y avisado al dueño.
- El alcance pide "una etapa de diseño revisada antes de programar". El implementador dice que
  trabajó "según el diseño aprobado" y habla de "los 39 puntos de aceptación del diseño", pero
  ese diseño y su revisión no están registrados en este archivo ni en un commit de la rama. No
  pude comprobar qué decía el diseño; lo que acá figura como "lo dice el diseño" es palabra del
  implementador.
- Esto es la base de B, no B: sigue todo en una misma PC, sin red. El orden del dueño no
  cambia: primero A, después B.

**Qué se hizo** (commit `1dc9de8`, implementador; local, sin push, sin tocar `main` ni este
archivo). Tocó `mate.py` (+1257 renglones), `test_mate.py` (+1500), README, MEJORAS y tres
ejemplos nuevos.
- Lenguaje: `usar buzon "otro.mate"`, sin gastar cupo (siguen 36 palabras y 48 funciones). Trae
  los agentes del otro programa como destino de `enviar` y los mensajes que cruzan, sin
  ejecutarlo ni cargar su Python. Los errores salen antes de correr, con su renglón.
- Un agente de otro programa sirve para `enviar`, `simular` y mostrar su nombre. `preguntar`,
  `crear`, `a_json`, `corregir` y ponerlo adentro de un mensaje dan error claro (para
  `aprender` y `lecciones`, ver P145).
- Salida: lo enviado se anota "por salir" y se guarda en la memoria junto con el estado y los
  recibidos, en una sola escritura; después se reparte en `otro.buzon` (archivo provisorio +
  `os.replace`). Lo que quedó pendiente de un corte sale al arrancar la corrida siguiente.
- Entrega: solo con `correr`, al terminar los renglones, en una pasada y con tope de 1000
  sobres. Se valida con el contrato del que recibe y lo repetido se descarta por (programa,
  id). Sale un renglón de resumen solo si hubo buzón.
- Rechazos: el archivo va intacto a `rechazados` con su `.motivo.txt`, con aviso y sin cambiar
  el código de salida. Al que envió le vuelve un sobre de falla, que llega a su `al fallar` (o
  sale como aviso). Una falla nunca genera otra. Si el agente falla o salta un límite al
  atender, el mensaje también va a `rechazados`.
- Dos ventanas: candado del sistema sin esperar (`msvcrt.locking` / `fcntl.flock`) y relectura
  de la memoria con el candado tomado; si otra ventana guardó otro estado, no atiende y avisa.
- Memoria: función interna nueva `leer_buzon_de_memoria`; `guardar_memoria(ruta, programa,
  agentes, buzon=None)` conserva la parte "buzon" cuando no se la pasan (`corregir`,
  `lecciones`, `proponer`, la cuenta de consultas y `--olvidar` no la pierden). Una memoria sin
  buzón se escribe igual que antes.
- `probar`, `verificar` y `ensayar` no leen ni escriben buzones ni memoria. `--traza` marca "al
  buzón: sale al terminar", "del buzón" y lo no entregado. Orden nueva de solo lectura:
  `mate.py buzon programa.mate`.
- Seguridad: los nombres de un sobre nunca arman una ruta (el programa se busca en el listado
  de la carpeta); se rechaza la forma reservada de agente en cualquier profundidad;
  `escribir_archivo` y `agregar_a_archivo` no escriben dentro de una carpeta `.buzon`; mensaje
  saliente de hasta 1 MB y sin agentes adentro.
- Ejemplos nuevos con pruebas adentro: `buzon_ventas.mate`, `buzon_deposito.mate` y
  `buzon_mensajes.mate`.
- 44 funciones de prueba nuevas (62 casos con las parametrizadas), prefijo `test_buzon_`, cada
  una en su `tmp_path`: entre ellas, kill del que recibe y del que envía, Ctrl+C entre dos
  mensajes, cadena de tres programas, dos emisores a la vez y dos ventanas del mismo destino.
- Documentación: sección nueva "Dos programas que se hablan: el buzón" en el README, con los
  límites declarados; fila en "Qué se está sumando para la 0.7" y en la tabla de órdenes; nota
  en "El tope" y en "Límites"; `ayuda buzon`; mejora 126 en MEJORAS.

**No se hizo** (declarado por el implementador): nada en Windows (el candado con
`msvcrt.locking` no se probó, y la prueba de Ctrl+C se saltea ahí porque manda SIGINT);
`pytest` completo solo en Python 3.13; el orden entre dos corridas del mismo emisor en el
mismo segundo no está asegurado (es P134); no sumó `*.buzon` ni `*.memoria.json` al
`.gitignore`; no tocó `VERSION` (sigue en 0.6), ni el curso, ni el README de la raíz. Queda
afuera lo que, según él, el diseño ya dejaba afuera: quedarse escuchando, firmar sobres,
vencimiento, limpiar `rechazados`, agentes dentro de un mensaje entre programas, recortar el
motivo de una falla y carpetas sincronizadas.

**Quién revisó y quién probó**: revisor (R) y agente de pruebas (P), cada uno sobre una copia
del commit `1dc9de8` en una carpeta temporal propia de `mktemp -d`, ya borrada. Integrador (I):
las tres corridas, unas pocas comprobaciones de lectura y este registro; no tocó código ni
pruebas y no reprodujo a mano los casos de R y P.

**Veredictos**: R **no aprueba** (un medio, ocho bajos). P **no aprueba** (un medio, ocho
bajos). Cambio 3 **NO cerrado**.

**Pruebas** (integrador, Linux, `MATE_SIN_REGISTRO=1`, sobre `1dc9de8`, Python 3.13.18)
- `pytest mate/pruebas mate/modelo`: 1079 pasan, 0 fallan, en 113 s (antes 1014).
  Implementador, R y P dieron el mismo número (R y P: 121 s).
- `probar mate/ejemplos`: 99 de 99, en 22 archivos (antes 92 de 92 en 19). `probar
  mate/curso`: 37 de 37, en 26 archivos.
- Después de las corridas, `git status --short` vacío.
- Pruebas viejas (I, R y P): el diff de `mate/pruebas` y `mate/modelo` entre `b144dda` y
  `1dc9de8` agrega 1500 renglones y no quita ninguno. Ninguna prueba se sacó ni se aflojó.
- I contó 44 `def test_buzon_` (el implementador dice 62 pruebas: son los casos, contando las
  parametrizadas, según R). I vio en el README la frase del orden (línea 1064) y la fila
  suelta de la tabla (línea 2868).
- Topes (R): `len(PALABRAS)` = 36 y `len(FUNCIONES)` = 48; `buzon` sigue sirviendo como nombre
  de variable y de función (R y P).
- Ida y vuelta (R y P): con los ejemplos y con programas propios, la ida, la contestación y la
  vuelta andan; correr de nuevo no repite nada; un sobre ya atendido copiado con otro nombre
  se descarta sin entregar y el stock no cambia.
- Contrato (R y P): un sobre con cantidad 500 (R) y uno con 80 tras bajar el tope a 50 (P)
  fueron a `rechazados` con su `.motivo.txt`, con aviso, código 0, los demás atendidos y el
  sobre de falla de vuelta. P repuso el contrato, movió el `.json` a la carpeta de arriba y se
  atendió.
- Sobres rotos o escritos a mano (P, 23 casos: basura, vacío, 3 MB, 100.000 corchetes, id
  `../../etc`, programa `../../x`, enlace a `/etc/passwd`, nombre con ESC, etc.): código 0, 16
  a `rechazados` con motivo claro, nada escrito fuera de la carpeta, sin colgarse. Una memoria
  con "por_salir" manipulado se descarta con aviso y no escribe afuera.
- Cortes (R y P): con `os._exit` entre guardar y repartir, del lado del que recibe y del que
  envía (R), y con `kill -9` y Ctrl+C a mitad de la entrega (P), la corrida siguiente atiende
  lo que faltaba una sola vez y el stock no se descuenta dos veces. La excepción es P135.
- `probar` no escribe (R y P): P comparó la suma md5 de toda la carpeta antes y después, en
  carpeta limpia y con buzones llenos: `probar`, `verificar`, `ensayar --ia-simulada`,
  `consola`, `buzon`, `lecciones`, `bitacora` y `propuestas` no cambian ni crean nada.
- Dos ventanas (P): la segunda de Depósito avisa y no repite nada; dos de Ventas a la vez no
  pierden mensajes ni "recibidos". Solo en Linux.
- Otros (P): 1200 mensajes en una corrida (atiende 1000, avisa, los 200 restantes en la
  siguiente, en orden y sin repetir); cadena de tres programas; dos programas que se nombran
  mutuamente; nombres con espacios, ñ y paréntesis; mensaje de más de 1 MB frenado; memoria
  rota (no corre, código 2, y los mensajes siguen esperando).
- Otras versiones: P corrió la ida y vuelta del ejemplo, sus pruebas, la orden `buzon` y un
  rechazo por contrato en Python 3.10.20, 3.11.18, 3.12.3 y 3.14.6. R solo comprobó la
  sintaxis de `mate.py` en 3.10 a 3.12. Nadie corrió `pytest` fuera de 3.13.

**Criterios de aceptación del cambio 3**

| Criterio | Estado | Evidencia |
|---|---|---|
| El primero envía, termina, y al correr el segundo el mensaje llega una sola vez | cumple, con una reserva media | R y P, con los ejemplos y con programas propios; lo repetido se descarta. Reserva: el orden que promete el README no se cumple entre corridas del mismo segundo (P134) |
| Un mensaje que no cumple el contrato del destino no se entrega y queda avisado sin cortar | cumple | R y P: va a `rechazados` con motivo, aviso, código 0, los demás se atienden y al que envió le vuelve la falla |
| El buzón no se pierde si el programa se corta | cumple del lado del que recibe; NO cumple en un caso del que envía | `kill -9`, `os._exit` y Ctrl+C a mitad de la entrega: bien (R y P). Mostrador cerrado con Ctrl+C: el último mensaje se pierde con el estado ya guardado (P135, P) |
| `probar` no escribe buzones de verdad | cumple | R (no aparece ninguna carpeta `.buzon` ni memoria) y P (md5 de toda la carpeta) |
| Para todo: pruebas que ya había, sin aflojar | cumple | 1079 / 99 de 99 / 37 de 37; 0 renglones quitados en pruebas |
| Para todo: topes, red, claves | cumple | 36 palabras y 48 funciones; sin red; el Python del otro programa no se carga (R y P) |
| Para todo: README, `ayuda` y MEJORAS al día | cumple a medias | sección nueva, `ayuda buzon` y mejora 126; pero el README promete el orden (P134), no avisa lo de Ctrl+C (P135, P137) y tiene una fila suelta (P138) |
| Una etapa de diseño revisada antes de programar | sin registro | no figura en este archivo ni en la rama (nota del integrador) |

**Problemas** (R = revisor, P = agente de pruebas, I = integrador)

| # | Problema | Quién | Gravedad | ¿Ya estaba? | Estado |
|---|---|---|---|---|---|
| P134 | El README ("Dos programas que se hablan: el buzón") dice que el orden está asegurado entre los mensajes de un mismo programa, y no es así entre corridas del mismo segundo: el id del sobre arranca con la hora al segundo y sigue con cifras al azar. R lo reprodujo: 6 corridas seguidas llegaron 3, 4, 1, 2, 5, 6. Pasa con un `.bat` o repitiendo el comando rápido. Además usa la hora local: si el reloj se atrasa, también se invierte. La prueba de orden espera 1,1 s entre corridas y por eso no lo ve | R (reproducido); implementador y P (declarado) | media | no | pendiente, obligatorio: que el id ordene de verdad (hora UTC con microsegundos o un contador en la parte "buzon" de la memoria), con una prueba sin espera; como mínimo, corregir la frase del README |
| P135 | Un mostrador que se cierra con Ctrl+C pierde, sin aviso, el mensaje para el otro programa del último pedido: Ventas contesta "Anotado A-2" y guarda su estado (A-1 y A-2), pero en el buzón de Depósito queda solo A-1 y "Por salir" dice "ninguno". El `enviar` queda en la cola interna hasta el próximo `preguntar` o el fin del programa, y Ctrl+C en `leer()` guarda la memoria sin vaciar esa cola. Con un error del programa pasa lo mismo, pero ahí sale "quedaron 1 mensaje(s) sin entregar". Con `chau` o fin de entrada sale bien. Choca con "el buzón no se pierde si el programa se corta" y con el README. El mecanismo de la cola ya estaba (en un solo programa también se pierde); lo nuevo es que deja a dos programas con datos distintos, y Ctrl+C es una salida que el README da como normal | P (reproducido, con receta completa) | media | no (la cola sí; el efecto entre dos programas es nuevo) | pendiente, obligatorio: que lo encolado para otro programa quede "por salir" antes de guardar, o no guardar el estado de ese pedido; con prueba |
| P136 | Correr el ejemplo del buzón donde está, como indican su encabezado y el README, deja `buzon_ventas.memoria.json`, `buzon_deposito.memoria.json` y las carpetas `.buzon` en `mate/ejemplos`; con eso falla la prueba vieja `test_el_ejemplo_del_agente_que_aprende`. Es P86 con un ejemplo más. `*.buzon` y `*.memoria.json` tampoco están en `.gitignore` | R, P (los dos lo corrieron en una copia); implementador (declarado lo del `.gitignore`) | baja | sí, la clase (P86); el ejemplo es nuevo | pendiente: que README y encabezado manden a copiar los tres archivos a una carpeta propia, y sumar los dos patrones al `.gitignore` |
| P137 | Un mostrador que se cierra con Ctrl+C no atiende su buzón (`atender_buzon` corre solo si los renglones terminan sin corte) y no avisa que quedaron mensajes esperando. El README dice "manda y recibe recién al salir con chau" pero no que con Ctrl+C no recibe: quien siempre sale así no recibe nunca | R (leído en el código, no ejecutado) | baja | no | pendiente: avisar al salir cuántos mensajes quedaron esperando, y decirlo en el README. Va junto con P135 |
| P138 | La fila nueva de la tabla "Qué se está sumando para la 0.7" del README (línea 2868) quedó separada de la tabla por un renglón en blanco: se ve como texto suelto con barras | R; I lo vio en el archivo | baja | no | pendiente (prolijidad) |
| P139 | En `consola`, `usar buzon "b.mate"` seguido de `enviar ... a B` no escribe nada y no avisa: el mensaje se pierde en silencio. La traza dice "acá no se escribe", pero sin `--traza` no se ve | R | baja | no | pendiente: un aviso en la consola |
| P140 | Si un mensaje rechazado se reintenta (moviéndolo de `rechazados` a la carpeta de arriba) y vuelve a fallar, el segundo aviso de falla lleva el mismo id; si el que envió ya atendió el primero, lo descarta como repetido y no se entera | R (deducido del código, no corrido hasta el final) | baja | no | pendiente; sin verificar |
| P141 | La orden `buzon programa.mate` cuenta de más: muestra como "Esperan" sobres ya atendidos que quedaron en la carpeta tras un corte (R) o copias repetidas que al correr se borran sin atender (P). Con `buzon efecto.py` contesta "la carpeta efecto.py.buzon" en vez de decir que no es un `.mate`. Un enlace o una carpeta terminados en `.json` quedan en el buzón para siempre, sin aviso | R, P | baja | no | pendiente (prolijidad) |
| P142 | `escribir_archivo` desde el programa principal puede pisar la memoria de OTRO programa de la carpeta (`escribir_archivo("depo.memoria.json", "hola")`); la protección cubre solo la memoria propia. El hueco ya existía, pero ahora ese archivo guarda también lo atendido y lo por salir del buzón del otro | R | baja | sí (pesa más desde este cambio) | pendiente: proteger los `*.memoria.json` de los programas nombrados con `usar buzon`, o decirlo en el README |
| P143 | El ejemplo `buzon_ventas.mate` deja "esperando" con "A-17" para siempre: cada corrida vuelve a mandar A-17, Depósito lo reconoce como repetido y hace `devolver` sin contestar | P | baja | no | pendiente: arreglar el ejemplo |
| P144 | Con `--traza`, cuando el que mandó fue el programa suelto de otro programa, la traza aconseja "para recibirla, usá 'preguntar' en vez de 'enviar'", y a otro programa no se le puede preguntar | P | baja | no | pendiente (texto) |
| P145 | `lecciones(Deposito)` y `aprender(Deposito, ...)` con un agente de otro programa pasan `verificar` y al correr dan el error general ("solo va dentro de un agente..."), no el de "es de otro programa". `Deposito.stock` da "agente no tiene campos". El implementador lo declaró como "error claro" | P | baja | no | pendiente (texto del error) |
| P146 | Errores de `usar buzon` mejorables: con el nombre en otras mayúsculas (en Linux) no sugiere el archivo correcto; si el nombre es una carpeta dice "¿Quisiste decir 'carp.mate'?" con el mismo nombre | P | baja | no | pendiente (prolijidad) |
| P147 | El motivo de un aviso de falla escrito a mano llega a la pantalla con sus saltos de renglón (en los nombres de agente sí se rechazan los caracteres de control). Además, el aviso de falla puede llegar antes o después que las contestaciones buenas de la misma corrida, porque su id es el del mensaje original | P | baja | no | pendiente: limpiar el motivo al mostrarlo; el orden va con P134 |
| P148 | La suite completa tarda 113 a 122 s (el bombardeo suma los tres ejemplos nuevos): queda al borde de un tope de 120 s | implementador (declarado), R, P, I | baja | no | avisado; correr con un tope más largo |
| P149 | El candado de Windows (`msvcrt.locking`), mover a `rechazados` con archivos abiertos y las pruebas de dos procesos solo corrieron en Linux; la prueba de Ctrl+C se saltea en Windows. `pytest` completo, solo en Python 3.13 | implementador (declarado), R, P | baja | sí (es P11, con piezas nuevas que dependen del sistema) | pendiente del dueño: correr con `py` las dos pruebas de dos procesos (abajo) |
| P133 | `VERSION` sigue en 0.6; el curso y el README de la raíz no cuentan el buzón | implementador (declarado) | baja | sí | pendiente para el cierre de la 0.7 |
| P11 | Sin probar en una Windows de verdad (`py`, PowerShell, Bloc de notas) ni contra una IA real | implementador, R, P, I | baja | sí | pendiente del dueño |

Siguen abiertos de antes, sin cambio en esta vuelta: del cambio 1, P102 (medio, vuelta 4
obligatoria y sin registro), P103 a P111, P80 de fondo, P85, P86, P87, P88, P91, P92 y P94; del
cambio 2, P120, P128 a P132, P115, P125 y P127.

No verificado por nadie en esta vuelta: Windows (candado, `rechazados`, `py`); `pytest`
completo en Python 3.10, 3.11, 3.12 y 3.14; P137 y P140 (solo leídos en el código); el diseño
contra el que se dice haber programado. Para el dueño, en Windows:
`py -m pytest mate\pruebas -k "test_buzon_dos_programas_que_envian_a_la_vez_al_mismo_buzon or test_buzon_dos_ventanas_del_mismo_programa_a_la_vez"`.

**Decisiones técnicas nuevas** (del implementador, salvo la última)
- `usar buzon` no gasta cupo: `buzon` no es palabra reservada (sigue sirviendo como nombre) y
  no hay funciones incluidas nuevas. La orden `buzon` es de solo lectura.
- Los errores de `usar buzon` (archivo que falta, fuera de la carpeta, error adentro del otro,
  a sí mismo, agente repetido, mensaje declarado distinto) salen al analizar el programa, no
  en `verificar()`: se ve uno por vez, con su renglón, en `verificar`, `correr` y `probar`.
- Un mensaje que cruza declarado en dos lugares pero idéntico (mismos campos, reglas y
  `responde`) no es choque; solo es error si difiere.
- Si un archivo traído con `usar` por los dos programas contiene el `usar buzon` de uno de
  ellos, ese programa lo ignora en silencio; el error "a sí mismo" sale solo si está escrito
  en el propio archivo.
- Un mensaje rechazado por contrato cuyo original tampoco pasa el contrato del que envió
  vuelve como "aviso:" y no dispara `al fallar`. Por eso la prueba de `al fallar` usa un
  rechazo por agente inexistente.
- Lo que mandó el programa suelto llega sin remitente: la contestación se descarta, como hoy
  (ver P144).
- Cuando salta un límite atendiendo un mensaje del buzón, además de ir a `rechazados` y cortar
  el programa, vuelve el sobre de falla.
- `deposito.buzon` como archivo común se trata como aviso, no como error con código 1: del
  lado del que envía el mensaje queda "por salir" y sale cuando se arregla; del lado del que
  recibe avisa y no atiende.
- El candado se toma solo si hay algún `.json` esperando; el archivo `candado` queda en la
  carpeta del buzón.
- La clave de "recibidos" lleva el nombre del programa en minúsculas (`casefold`), para que en
  Windows "Ventas" y "ventas" sean el mismo.
- El último guardado (sacar lo repartido de "por salir") relee la memoria del disco en vez de
  reusar lo que tenía en mano, para no pisar lo que otra ventana haya guardado.
- Nombres de agente con caracteres de control en un sobre se rechazan, y el tipo de mensaje
  se recorta a 60 letras en los avisos (el motivo de una falla no se limpia: P147).
- El id del sobre arranca con la hora local al segundo y sigue con 20 cifras al azar. Es la
  causa de P134; hay que cambiarla en la vuelta 2.
- El ejemplo de `ayuda buzon` es un programa que corre solo (la parte de `usar buzon` va en
  comentarios), para no tocar la prueba vieja que ejecuta todos los ejemplos de la ayuda. Los
  ejemplos se llaman `buzon_*.mate`, sin número, para no alterar la prueba de los ejemplos
  graduales 01 a 13.
- Las pruebas usan `tmp_path` de pytest como carpeta propia de cada una.
- Integrador: el cambio 3 NO se cierra. R y P no aprueban y hay dos medios (P134 y P135). P135
  se cuenta como medio aunque la cola ya existiera, porque rompe un criterio de aceptación en
  una salida que el README da como normal. Los bajos no frenan el cierre.

**Lo que sigue**: vuelta 2 del cambio 3, con P134 y P135 obligatorios (cada uno con su
prueba) y, si entran, P136 a P139 y P143. Sigue pendiente la vuelta 4 del cambio 1 (P102) y
dejar registrado el diseño del buzón. Primero A, después B; nada de B todavía.

### Cambio 3: buzón entre programas, vuelta 2 — cerrado

Revisor y agente de pruebas aprobaron. Los dos problemas medios de la vuelta 1 (P134, el orden
entre corridas seguidas, y P135, el corte que perdía el último mensaje) quedaron resueltos y
con prueba. Nadie encontró problemas altos ni medios; quedan solo bajos.

Notas del integrador:
- El cambio 1 sigue NO cerrado: la vuelta 4 (P102, medio) sigue sin registro en este archivo.
  Cerrar el cambio 3 no cierra la 0.7.
- El diseño del buzón y su revisión siguen sin estar registrados acá ni en la rama. En esta
  vuelta el implementador se aparta de "el punto 4.4 del diseño": no pude leer ese punto, es
  palabra suya.
- Esto sigue siendo la base de B, no B: todo en una misma PC, sin red. El orden del dueño no
  cambia: primero A, después B.
- Windows sigue sin probar (P149), y ahí se saltean las pruebas de Ctrl+C, que son justo las
  de P135. El cierre vale para lo probado en Linux.

**Qué se hizo** (commit `c0f294e`, implementador; local, sin push, sin tocar `main` ni este
archivo). Tocó `mate.py` (+181, -26 renglones), `test_mate.py` (+368, -0), README, MEJORAS,
`buzon_ventas.mate`, `buzon_deposito.mate` y `.gitignore`.
- P134: el id del sobre conserva la forma fecha, 20 cifras hexadecimales y número, pero usa la
  hora universal y las 5 primeras cifras son las millonésimas de segundo (las otras 15, al
  azar). Prueba nueva sin espera (8 corridas en un mismo proceso y 3 en procesos separados).
  El README ya no promete de más: dice qué puede desordenar.
- P135: al cerrar la corrida, también con error o Ctrl+C, lo que un agente ya dejó para otro
  programa y seguía en la cola pasa a "por salir" y se guarda junto con su estado. Lo que
  encoló un agente cortado con Ctrl+C a mitad de un mensaje se deshace junto con su estado.
  Tres pruebas nuevas.
- P137: un programa que se corta sin atender su buzón avisa cuántos mensajes quedaron
  esperando. README y `ayuda buzon` dicen que con Ctrl+C manda pero no recibe.
- P136 y P143: el encabezado del ejemplo y el README mandan a copiar los tres archivos a una
  carpeta propia; `*.buzon/` y `*.memoria.json` entraron al `.gitignore`. Ventas ya no manda
  dos veces el mismo pedido, así que `esperando` queda vacío (con prueba).
- P138: la fila del buzón quedó pegada a su tabla en el README.
- P139: en la consola, un `enviar` a otro programa avisa que no se escribió ningún buzón.
- P140: el aviso de falla de un mensaje reintentado desde `rechazados` lleva el número del
  intento (`.falla-2`, `.falla-3`). Si el rechazo se repite por un corte, el id no cambia.
- P141: la orden `buzon` muestra aparte lo ya atendido o repetido, avisa de carpetas o enlaces
  terminados en `.json` y rechaza un archivo que no es `.mate`.
- P142: `escribir_archivo` y `agregar_a_archivo` no pisan la memoria de un programa nombrado
  con `usar buzon`.
- P144, P145, P146 y la primera mitad de P147 (textos): la traza ya no aconseja `preguntar`
  cuando el mensaje vino de otro programa sin agente; `lecciones(Deposito)`, `aprender(...,
  Deposito)` y `Deposito.stock` dicen que el agente es de otro programa; `usar buzon` sugiere
  el archivo cuando difieren las mayúsculas y dice "es una carpeta" cuando lo es; el motivo de
  una falla sale en un renglón y recortado.
- Documentación: README (sección del buzón y límites), `ayuda buzon` y MEJORAS 126 con la nota
  de la vuelta 2. 14 funciones de prueba nuevas (17 casos) y una prueba más en el ejemplo.

**No se hizo** (declarado por el implementador): nada en Windows (candado, paso a `rechazados`,
`py`; las tres pruebas nuevas de Ctrl+C se saltean ahí); `pytest` completo solo en Python 3.13;
el orden puede fallar si el reloj de la PC se atrasa entre dos corridas o con dos ventanas del
mismo programa (declarado en el README; no hay contador en la memoria); la segunda mitad de
P147 (el aviso de falla puede adelantarse a las contestaciones buenas) quedó solo en el README;
P137 quedó en aviso (un mostrador cerrado con Ctrl+C sigue sin atender su buzón); P142 no cubre
la memoria de un programa que no se nombra con `usar buzon`; hueco de P140 si al reintentar se
mueve también el `.motivo.txt`; P136 es solo texto y `.gitignore`; no tocó `VERSION`, el curso
ni el README de la raíz (P133).

**Quién revisó y quién probó**: revisor (R) y agente de pruebas (P), cada uno sobre una copia
del commit `c0f294e` en una carpeta temporal propia. Integrador (I): las tres corridas, unas
pocas comprobaciones de lectura y este registro; no tocó código ni pruebas y no reprodujo a
mano los casos de R y P.

**Veredictos**: R **aprueba** (cinco bajos). P **aprueba** (seis bajos). Cambio 3 **cerrado**.

**Pruebas** (integrador, Linux, `MATE_SIN_REGISTRO=1`, sobre `c0f294e`, Python 3.13.18)
- `pytest mate/pruebas mate/modelo`: 1096 pasan, 0 fallan, en 112 s (antes 1079).
  Implementador, R y P dieron el mismo número (115, 116 y 117 s).
- `probar mate/ejemplos`: 100 de 100, en 22 archivos (antes 99 de 99). `probar mate/curso`: 37
  de 37, en 26 archivos.
- Después de las corridas, `git status --short` vacío y ninguna memoria ni carpeta `.buzon` en
  `mate/ejemplos` (lo miré con `ls`, porque ahora el `.gitignore` las tapa: P153).
- Pruebas viejas (I, R y P): el diff de `mate/pruebas` y `mate/modelo` entre `1dc9de8` y
  `c0f294e` agrega 368 renglones y no quita ninguno. Ninguna prueba se sacó ni se aflojó.
- Topes (R): las pruebas de topes pasan y el diff no agrega palabras ni funciones incluidas.
- P134 (R y P): 12 corridas seguidas en procesos separados llegaron 1 a 12 en orden, y las
  contestaciones también. P lo repitió con 25 corridas en Python 3.10, 3.11, 3.12 y 3.14.
- P135 (R y P): con error del programa después de que un agente dejó un mensaje, el mensaje
  sale y el estado se guarda. Con Ctrl+C esperando el teclado sale "Buzón: dejé 2 mensajes
  para deposito.mate", el buzón tiene los 2 y Ventas guarda A-1 y A-2. Ctrl+C a mitad de un
  mensaje: ese mensaje se deshace (estado y envío) y el anterior sale.
- El buzón no se pierde (R y P): `kill -9` del mostrador no guarda ni manda nada (coherente).
  Ctrl+C mientras Depósito atendía 7 mensajes: guardó 3 con sus contestaciones, los otros 4
  siguieron en el buzón y se atendieron una sola vez en la corrida siguiente (stock 50, 47,
  43).
- P137 (P): Ventas cerrado con Ctrl+C con 2 contestaciones esperando avisa y las atiende en la
  corrida siguiente. También avisa si Depósito se corta porque falta su planilla.
- Contrato (P): cantidad 500, archivo que no es JSON, mensaje mal formado y agente
  inexistente: cada uno con su aviso, a `rechazados` con `.motivo.txt`, el mensaje bueno se
  atiende, código 0, y al que envió le vuelve la falla.
- P140 (R y P): reintentos desde `rechazados` mandan `.falla-2` y `.falla-3` y el que envió se
  entera cada vez (R: tres veces).
- P142 (R): `escribir_archivo` rechaza `deposito.memoria.json` con otras mayúsculas, `./`,
  `sub/../`, `.tmp` y con espacio o punto al final. P139, P141, P145 y P146 comprobados por P.
- `probar` no escribe (P): `probar`, `verificar` y `ensayar --ia-simulada` (con un "tiene que
  viajar: Reservar de Ventas a Deposito") no crearon ni cambiaron buzones ni memoria.
- Ejemplo (R y P): copiado a una carpeta propia, ventas, depósito, ventas da "dejé 1 mensaje",
  "atendí 1 mensaje" y "Pedido A-17: reservado. Quedan 8."; repetir no manda ni descuenta nada.
- Otros (P): planilla CSV cambiada entre corridas y `vendidos` recordado; `--traza` marca "al
  buzón", "del buzón" y "en respuesta al 1"; nombres con espacios, ñ, comillas, emoji y salto
  de renglón; memoria rota del que recibe; `deposito.buzon` tapado por un archivo; bombardeo
  con una ventana por programa (3 que envían y Depósito, 12 rondas, 36 pedidos): nada perdido
  ni repetido, en orden.
- "Ningún agente toca el estado de otro" (R): al cortar a mitad de un mensaje vuelve atrás solo
  el estado del agente que atendía y salen de la cola solo los mensajes que él encoló.
- Otras versiones: P corrió `probar mate/ejemplos` (100 de 100) y sus casos en 3.10, 3.11, 3.12
  y 3.14; R, una prueba corta en 3.11 y 3.12. Nadie corrió `pytest` fuera de 3.13.

**Criterios de aceptación del cambio 3**

| Criterio | Estado | Evidencia |
|---|---|---|
| El primero envía, termina, y al correr el segundo el mensaje llega una sola vez | cumple | R y P, con el ejemplo y con programas propios; el orden entre corridas seguidas ahora se cumple (P134) |
| Un mensaje que no cumple el contrato del destino no se entrega y queda avisado sin cortar | cumple | P: cuatro clases de sobre malo, a `rechazados` con motivo, aviso, código 0 |
| El buzón no se pierde si el programa se corta | cumple en Linux | R y P: error, Ctrl+C del que envía y del que recibe, `kill -9`. Reservas bajas: P152 (cola interna entre agentes del mismo programa) y P156 (varias ventanas del mismo programa). Sin probar en Windows (P149) |
| `probar` no escribe buzones de verdad | cumple | P |
| Para todo: pruebas que ya había, sin aflojar | cumple | 1096 / 100 de 100 / 37 de 37; 0 renglones quitados en pruebas |
| Para todo: topes, red, claves | cumple | R: pruebas de topes y diff sin palabras ni funciones nuevas; P: sin claves ni datos personales en el diff |
| Para todo: README, `ayuda` y MEJORAS al día | cumple, con dos imprecisiones bajas | R los leyó contra el código: P150 y P151 |
| Una etapa de diseño revisada antes de programar | sin registro | sigue sin figurar en este archivo ni en la rama |

**Problemas** (R = revisor, P = agente de pruebas, I = integrador)

| # | Problema | Quién | Gravedad | ¿Ya estaba? | Estado |
|---|---|---|---|---|---|
| P134 | El orden prometido no se cumplía entre corridas del mismo segundo | R y P (verificado) | media | no (vuelta 1) | resuelto, con prueba. Queda declarado en el README: puede fallar si el reloj se atrasa o con dos ventanas del mismo programa |
| P135 | Un mostrador cerrado con Ctrl+C perdía el último mensaje para el otro programa | R y P (verificado) | media | no (vuelta 1) | resuelto, con tres pruebas (que se saltean en Windows) |
| P136 | Correr el ejemplo del buzón dentro de `mate/ejemplos` deja la memoria ahí y rompe `test_el_ejemplo_del_agente_que_aprende` | implementador, R, P | baja | sí (P86) | a medias: solo texto y `.gitignore`; ver P153 |
| P137 | Un mostrador cerrado con Ctrl+C no atiende su buzón | P (verificado el aviso) | baja | no (vuelta 1) | a medias: ahora avisa y está en el README; sigue sin atender. Ver P151 |
| P138 | Fila suelta en la tabla del README | implementador | baja | no (vuelta 1) | resuelto |
| P139 | En la consola, `enviar` a otro programa se perdía en silencio | R, P | baja | no (vuelta 1) | resuelto (avisa en cada `enviar`) |
| P140 | El segundo aviso de falla de un reintento se descartaba como repetido | R, P | baja | no (vuelta 1) | resuelto, con un hueco: si al reintentar se borra o mueve también el `.motivo.txt`, el aviso repite el id `.falla` y se descarta callado (P lo reprodujo) |
| P141 | La orden `buzon` contaba de más y aceptaba un archivo que no es `.mate` | P | baja | no (vuelta 1) | resuelto; queda P157 |
| P142 | `escribir_archivo` podía pisar la memoria de otro programa | R | baja | sí | a medias: cubre los programas nombrados con `usar buzon`; el resto está dicho en el README |
| P143 | El ejemplo dejaba `esperando` con A-17 para siempre | R, P | baja | no (vuelta 1) | resuelto, con prueba |
| P144, P145, P146 | Textos de la traza y de los errores | P | baja | no (vuelta 1) | resueltos; de P146 queda P157 |
| P147 | Motivo de una falla con saltos de renglón; el aviso de falla puede adelantarse a las contestaciones | P | baja | no (vuelta 1) | a medias: el motivo sale en un renglón y recortado (queda P154); el orden del aviso quedó solo declarado en el README |
| P148 | La suite tarda 112 a 117 s, al borde de un tope de 120 s | implementador, R, P, I | baja | sí | avisado; correr con un tope más largo |
| P149 | Sin probar en Windows: candado `msvcrt.locking`, paso a `rechazados`, `py`; las pruebas de Ctrl+C se saltean ahí. `pytest` completo, solo en Python 3.13 | implementador, R, P | baja | sí | pendiente del dueño (comando abajo) |
| P150 | README, `ayuda buzon` e informe dicen que al cortarse sale "lo que sus agentes ya habían dejado", pero también sale lo que mandó el programa suelto con `enviar` (sin agente). Antes una corrida que fallaba no mandaba nada; ahora cada intento fallido deja un mensaje. Es defendible y avisa "Buzón: dejé 1 mensaje", pero no está escrito ni tiene prueba | R (reproducido) | baja | no | pendiente: escribirlo y sumar una prueba |
| P151 | El aviso de P137 sale solo si el programa se corta ANTES de empezar a atender el buzón. Con Ctrl+C mientras lo atiende no dice cuántos quedaron, y el README lo afirma sin matices. No se pierde nada | R (reproducido) | baja | no | pendiente (aviso o texto) |
| P152 | Con Ctrl+C, lo que estaba en la cola interna para OTRO agente del mismo programa se pierde sin aviso: el mensaje que se estaba atendiendo no figura en "quedaron N mensaje(s) sin entregar" (R), y con Ctrl+C esperando el teclado no sale ningún aviso (P: Caja no cobra A-2 y `caja-A-2` no sale, con Ventas ya guardado) | R, P (reproducido, con receta) | baja | sí (la cola interna ya se perdía) | pendiente |
| P153 | El `.gitignore` ahora tapa `*.memoria.json` y `*.buzon/` en todo el repositorio: una memoria que quede en `mate/ejemplos` ya no aparece en `git status` y sigue rompiendo la prueba de P136 | R | baja | no | pendiente: limitar el patrón o resolver P136 de fondo |
| P154 | El motivo de un aviso de falla deja pasar el carácter de escape (ESC): un sobre escrito a mano puede cambiar colores o mover el cursor en la pantalla del que recibe | P (reproducido) | baja | no | pendiente: sacar los caracteres de control del motivo |
| P155 | `correr --ia-simulada deposito.mate` atiende el buzón de verdad: si el agente consulta a la IA sin tercer valor, todos los mensajes fallan, van a `rechazados` y vuelve un aviso por cada uno. Se recupera moviendo los archivos; el README no lo avisa en la sección del buzón | P (reproducido) | baja | sí | pendiente: avisarlo en el README o no atender el buzón con IA simulada |
| P156 | Varias ventanas del MISMO programa que envía, terminando a la vez: algunas no pueden guardar la memoria y su mensaje no sale (4 de 36 en el bombardeo de P). Avisa, pero el README no dice que se puede perder un envío | P (reproducido) | baja | sí | pendiente (texto del README, como mínimo) |
| P157 | La orden `buzon noexiste.mate` lista una carpeta `carp.mate` entre los archivos que sí hay; `usar buzon "carp"` con una carpeta `carp.mate` dice "no pude abrir" en vez de "es una carpeta" | P | baja | sí | pendiente (prolijidad) |
| P133 | `VERSION` sigue en 0.6 (`ayuda` y la consola dicen "Mate 0.6"); el curso y el README de la raíz no cuentan el buzón | implementador, R, P | baja | sí | pendiente para el cierre de la 0.7 |
| P11 | Sin probar en una Windows de verdad ni contra una IA real | todos | baja | sí | pendiente del dueño |

Siguen abiertos de antes, sin cambio en esta vuelta: del cambio 1, P102 (medio, vuelta 4
obligatoria y sin registro), P103 a P111, P80 de fondo, P85, P86, P87, P88, P91, P92 y P94; del
cambio 2, P120, P128 a P132, P115, P125 y P127.

No verificado por nadie en esta vuelta: Windows (candado, `rechazados`, `py`, Ctrl+C); `pytest`
completo en Python 3.10, 3.11, 3.12 y 3.14; el diseño contra el que se dice haber programado.
Para el dueño, en Windows:
`py -m pytest mate\pruebas -k "test_buzon_dos_programas_que_envian_a_la_vez_al_mismo_buzon or test_buzon_dos_ventanas_del_mismo_programa_a_la_vez"`.

**Decisiones técnicas nuevas** (del implementador, salvo la última)
- Lo que queda en la cola para otro programa ahora SALE al cerrar la corrida (el implementador
  dice que se aparta del punto 4.4 del diseño, porque P135 era obligatorio). Solo pasa lo de
  agentes que terminaron bien su mensaje, y también lo del programa suelto (P150). Lo que
  queda para agentes del mismo programa sigue como antes.
- Ctrl+C a mitad de un mensaje saca de la cola lo que ese agente había encolado, igual que ya
  pasaba con un error. Antes solo volvía atrás el estado.
- El id conserva la forma de la vuelta 1 para no tocar la prueba vieja que la fija: hora
  universal, millonésimas en las 5 primeras cifras hexadecimales y 15 cifras al azar (60 bits)
  en vez de 20. Reemplaza la decisión de la vuelta 1 (hora local al segundo).
- Dentro de un mismo proceso, dos buzones nunca llevan la misma hora: el segundo se corre una
  millonésima.
- El id de la falla sigue siendo `<id>.falla` la primera vez (protege el corte entre guardar y
  mover); el número de intento se saca de los `.motivo.txt` que ya hay en `rechazados`.
- P143 se arregló del lado de Ventas; Depósito queda igual, sin cambiar pruebas del ejemplo.
- La pista de mayúsculas quedó en `pista_de_usar`, que comparte `usar`: también `usar
  "CATALOGO.MATE"` sugiere el archivo bien escrito y ya no sugiere carpetas.
- La prueba vieja de orden queda con su espera de 1,1 s; se sumó una nueva sin espera.
- El aviso de la consola sale por la salida común y se repite en cada `enviar` a otro programa.
- Integrador: el cambio 3 se cierra. R y P aprueban y no quedan altos ni medios. Los bajos
  (P136, P137, P140, P142, P147 a medias y P150 a P157) no frenan el cierre.

**Lo que sigue**: la vuelta 4 del cambio 1 (P102, medio), que es lo único que impide cerrar la
0.7; dejar registrado el diseño del buzón; la prueba del dueño en Windows (P149); y para el
cierre, P133 (`VERSION`, curso y README de la raíz). Primero A, después B; nada de B todavía.

### Cambio 1, vuelta de cierre — NO cerrado (queda un problema medio: P162)

Es la vuelta 4 del equipo del negocio (ejemplo 13 y `nuevo equipo`). El revisor aprobó; el
agente de pruebas no. Todo lo que la vuelta tenía que arreglar quedó resuelto y verificado por
los dos: P102 (obligatorio), P103 y P159. Lo que frena es un problema medio de la misma familia
que P102, encontrado en esta vuelta y que ya estaba: P162 (repetir la presentación con "x N",
"quiero un pack x 6 de cerveza", anota N bultos). Por eso el cambio 1 sigue sin cerrar,
`VERSION` sigue en `"0.6"` y no se tocó nada del cierre de verdad.

**Qué se hizo** (implementador, dos commits locales, `88e353c` y `ea475e7`; sin push, sin tocar
`main`, `VERSION` ni este archivo). Tocó el ejemplo 13, `mate.py` (`_ENCABEZADO_DEL_EQUIPO`,
`_PRUEBAS_DEL_EQUIPO` y el candado del buzón), `test_mate.py`, `casos_del_equipo.txt`, README
y MEJORAS.
- P102: un pedido dicho en la unidad de ADENTRO del bulto ya no se anota ni descuenta. "quiero
  10 paquetes de yerba" y "quiero 6 botellas de aceite" contestan 'Todavía no anoté nada, para
  no equivocarme: dijiste "paquetes", y Yerba mate se vende por bolsón de 10 paquetes de 1 kg,
  a $ 35.000,00 cada uno. ¿Cuántos querés de esos? Por ejemplo, para llevar uno solo: "quiero 1
  yerba".' Con `--traza` no viaja `Reservar` ni `ConsultarStock`.
- Lo de adentro del bulto se define por el número: función nueva `unidades_de_adentro(fila)`,
  que devuelve las palabras de la presentación que llevan un número adelante ("10 paquetes",
  "1 kg", "30 huevos"). Si la presentación no trae ningún número ("caja de botellas") queda la
  regla anterior (todo lo que no es la primera palabra), salteando además las palabras de
  `palabras_de_como_se_lleva()` y `palabras_que_acompanan()`.
- Resto de P102, presentación que arranca con un número ("6 botellas de 2 litros", "12
  unidades", "x 6 latas"): `unidad_de_venta()` devuelve "" y Ventas pregunta con un texto
  propio, 'se vende así: 6 botellas de 2 litros, a $ 5.400,00 cada bulto. ¿Cuántos bultos
  querés? Por ejemplo... "quiero 1 bulto de agua"'. "quiero 2 aguas" y "quiero 2 bultos de
  vino" anotan.
- Producto que se llama como lo de adentro ("Huevos; maple de 30 huevos"): "quiero 30 huevos" y
  "quiero 2 huevos" preguntan, y el ejemplo de la respuesta va con la unidad ("quiero 1 maple
  de huevos", que anota). Con "Paquete regalo; caja de 6 paquetes", "quiero 6 paquetes regalo"
  pregunta y "quiero 2 cajas de paquete regalo" anota.
- Las palabras que describen no frenan: "quiero 3 galletitas sin sal" (presentación "paquete de
  3 unidades sin sal") y "quiero 12 bizcochos para llevar" anotan; "quiero 24 paquetes de
  bizcochos" pregunta.
- P103: un pasado en tercera persona con tilde ("compró/llevó/encargó 10 yerbas") no anota;
  "hago", "hacer", "hacerte" y "haceme" piden "un pedido" atrás; "llevo 10 yerbas de mas" no
  anota. El "de" adelante de la cantidad frena solo si va PEGADO a ella, salteando
  "un/unas/otras" ("encargo de 5 yerbas", "de 5 yerbas", "encargo de unas 5 yerbas"). La primera
  versión (`88e353c`) frenaba cualquier "de" adelante y dejó de anotar siete pedidos legítimos
  que el revisor encontró ("aceite de girasol 3 cajas", "quiero aceite de girasol 3", "quiero
  aceite de girasol, 3 cajas", "quiero hacer un pedido de aceite de girasol: 2 cajas", "de
  yerba quiero 2", "quiero de azucar 12", "buenas tardes, de azucar 12 bolsas"); `ea475e7` lo
  corrigió y las siete anotan otra vez.
- P159: el archivo `candado` del buzón se crea con `os.open(..., 0o666)`, sin permiso de
  ejecución.
- Pruebas agregadas: dos en el ejemplo 13 (una planilla propia con 10 presentaciones raras; el
  "de" del nombre del producto), las mismas dos en `_PRUEBAS_DEL_EQUIPO`, las de pytest (las
  ocho frases del "de" cada una en corrida limpia, en el ejemplo y en el equipo creado; la
  planilla del revisor con el stock intacto; las palabras que describen) y dos casos nuevos en
  `casos_del_equipo.txt` ("quiero 10 paquetes de yerba" y "quiero 6 botellas de aceite", con
  "no tiene que viajar: Reservar | ConsultarStock"). El ejemplo 13 pasa de 26 a 30 pruebas, el
  equipo creado de 15 a 18 y los casos de ensayo de 10 a 12.
- README, MEJORAS y el encabezado del equipo creado cuentan la regla del "de" pegado, que lo de
  adentro es lo que lleva un número adelante, y los límites (presentación que arranca con
  número, producto que se llama como lo de adentro, presentación sin números, abreviaturas y
  diminutivos). No se tocó el lenguaje.

**No se hizo** (declarado por el implementador): retomar el pedido con "1" o "uno solo" después
de la pregunta de Ventas (pediría guardar la charla entre consultas; es P165); "compro 10
yerbas" sin tilde sigue anotando (sin la tilde no se distingue de un pedido); "quiero 2
unidades de yerba" y "quiero 2 bultos de yerba" siguen anotando 2 bolsones (P163); las
abreviaturas y diminutivos ("10 paq", "6 botellitas") reciben la cuenta por bultos y no la
pregunta nueva (P167); una pregunta de precio en la unidad de adentro ("cuanto salen 10
paquetes de yerba?") sigue contestando la pregunta de la unidad y no la cuenta (lo afirma una
prueba de la primera mitad de la vuelta); el ejemplo 12 sigue cotizando 10 bolsones para
"quiero 10 paquetes de yerba" (no anota ni descuenta; no se tocó); una medida escrita con
letras más allá de doce no cuenta como número; y P170. No tocó P104 a P111, P80 de fondo ni
`VERSION`. Borró su carpeta temporal propia.

**Quién revisó y quién probó**: revisor (R) y agente de pruebas (P), cada uno sobre una copia
del repositorio en una carpeta propia de `mktemp -d`, ya borrada, los dos sobre `ea475e7`.
Integrador de cierre (I): las tres corridas, un recorrido corto en una carpeta propia (ya
borrada) y este registro; no tocó código, pruebas ni `VERSION`.

**Veredictos**: R **aprueba** (cinco apuntes, todos bajos; uno es un límite de su propia
verificación). P **no aprueba** (un medio: P162; seis bajos). Altos: ninguno. Cambio 1 **NO
cerrado**. P aclara que todo lo pedido en la tarea (P102, P103, P159) está cumplido y que el
NO es por P162, que queda fuera de la letra de P102 (no nombra una unidad de adentro) pero
hace el mismo daño.

**Pruebas** (integrador, Linux, `MATE_SIN_REGISTRO=1`, sobre `ea475e7`, Python 3.13.18)
- `python3 -m pytest mate/pruebas mate/modelo -q -p no:cacheprovider`: 1110 pasan, 0 fallan
  (161 s; antes 1100). P dio el mismo número. El implementador y R informan 1092, que es solo
  `mate/pruebas/test_mate.py`; R declara que no corrió `mate/modelo`.
- `probar mate/ejemplos`: 104 de 104, en 22 archivos (antes 100). `probar mate/curso`: 37 de
  37, en 26 archivos.
- Después de las tres corridas, `git status --short` vacío, y en `mate/ejemplos` ninguna
  memoria ni carpeta `.buzon`.
- Recorrido de I sobre un equipo recién creado con `nuevo equipo mi_negocio`: `verificar` "sin
  errores", `probar` 18 de 18, `ensayar --ia-simulada` 12 de 12. Cada frase en corrida limpia,
  mirando la memoria guardada: "quiero 10 paquetes de yerba" y "quiero 6 botellas de aceite"
  preguntan y dejan Yerba mate 40 y Aceite 8 (**P102 resuelto**); "compró 10 yerbas" no anota
  (P103); "aceite de girasol 3 cajas" anota 3 cajas (8 a 5) y sale el `Reponer`. **P162
  reproducido**: "quiero un bolson x 10 de yerba" contesta "Anotado: 10 x Yerba mate (bolsón
  de 10 paquetes de 1 kg)... total $ 350.000,00" y la memoria queda con Yerba mate 30.
  También P163 ("quiero 10 unidades de yerba" anota 10, quedan 30) y P104 ("hola, 5 yerbas
  para retirar" anota 5, quedan 35). Buzón: después de `buzon_ventas` / `buzon_deposito` /
  `buzon_ventas` los dos archivos `candado` quedan `-rw-r--r--` (**P159 resuelto**) y llega
  "Pedido A-17: reservado. Quedan 8."
- R: `probar mate/ejemplos` 104 de 104 y curso 37 de 37; comparó unas 200 frases, una por una,
  contra el código anterior a la vuelta: todos los cambios de conducta van de anotar a
  preguntar, salvo las siete frases del "de" que `ea475e7` repone. Planillas con presentaciones
  raras ("12", "x 12", "caja de", "bolsa 5kg", "tira 100u", vacía) no cortan el programa:
  `verificar` sin errores y 18 de 18.
- P: unas 230 frases por tubería con `--ia-simulada`, cada una en corrida limpia, 115 con la
  planilla de muestra y 121 con una propia de 10 productos; unas 60 en la unidad de adentro
  (con mayúsculas, signos, pegado al número, otros verbos, saludo y envío) no anotan ni
  descuentan. Charla de 6 consultas con `--traza`: Ventas → Depósito → Compras, UN solo
  `Reponer` para azúcar (20 y después 5), la memoria queda Yerba 39 y Azúcar 0, la corrida
  siguiente arranca con "Compras: hay que reponer Azúcar (quedan 0)"; `probar` y `ensayar` no
  cambian la memoria (mismo md5).
- Pruebas viejas tocadas (R y P, y I miró el diff de `e3d228e` a `ea475e7` en `mate/pruebas`,
  `mate/modelo` y `casos_del_equipo.txt`): los 13 renglones quitados son solo conteos que
  subieron ("26 de 26" a "30 de 30", "15 de 15" a "18 de 18", "0 de 15" a "0 de 18", 10 casos a
  12, "9 de 10" a "11 de 12"). Ninguna prueba se quitó ni afirma menos.

**Criterios de aceptación del cambio 1**

| Criterio | Estado | Evidencia |
|---|---|---|
| `nuevo equipo mi_negocio` crea los archivos, pasa `verificar` y `probar` | cumple | 3 archivos, "sin errores", 18 de 18, `ensayar --ia-simulada` 12 de 12 (R, P, I) |
| Con `--traza` se ve Ventas → Depósito → Compras | cumple | `Reservar`, `Reponer`, `Anotado`, `Reserva` (P) |
| Un pedido descuenta stock y el stock sobrevive entre corridas | cumple, con reservas | 40 a 39 y sobrevive a la corrida siguiente (R, P). Ya no descuenta de más con la unidad de adentro (P102 resuelto). Sigue descontando de más si el cliente repite la presentación con "x N" (**P162**) o dice "N unidades" (P163). Con la X o un corte se pierde lo anotado (P80 de fondo, avisado) |
| Pedir más de lo que hay no vende | cumple | "quiero 100 harina" y "quiero 500 aguas" no venden (P) |
| Al bajar del mínimo sale UN pedido de reposición | cumple | un solo `Reponer` para azúcar con dos ventas (P) |
| Ningún agente toca el estado de otro | cumple | sin cambios en esta vuelta; lo nuevo son funciones del programa |
| Para todo: pruebas que ya había, sin aflojar | cumple | 1110 / 104 de 104 / 37 de 37; solo subieron conteos |
| Para todo: topes, red, claves, README/`ayuda`/MEJORAS | cumple, con pendientes bajos | no se tocó el lenguaje; README leído contra la conducta (R). Falta avisar la forma "caja x 6" (P164) y "quiero 2 bultos de huevos" pregunta aunque el README dice que con "bultos" se pide (P166). El matiz del retiro (P104) sigue sin escribir |

**Problemas** (R = revisor, P = agente de pruebas, I = integrador)

| # | Problema | Quién | Gravedad | ¿Ya estaba? | Estado |
|---|---|---|---|---|---|
| P162 | Si el cliente repite la presentación con "x N", el número de ADENTRO del bulto se toma como cantidad de bultos, se anota y descuenta stock: con la planilla de muestra y en el ejemplo 13, "quiero un bolson x 10 de yerba" anota 10 bolsones ($ 350.000,00; stock 40 a 30) y "quiero bolsa x 10 azucar" anota 10 bolsas. Con una planilla propia, "quiero un pack x 6 de cerveza" (presentación "pack x 6") anota 6 packs ($ 43.200,00 en vez de $ 7.200,00; 50 a 44); "quiero una caja x 6 de vino" y "quiero caja x 6 botellas de vino" anotan 6 cajas y disparan `Reponer`; "quiero un bulto x 6 de atun" ("x 6 latas") anota 6. Causa: "x" está en `palabras_sueltas()` y en `palabras_de_union()`, "un/una" no cuentan como número, y `unidad_de_adentro()` devuelve nada apenas ve la unidad de venta. La misma frase con "de" ("quiero un pack de 6 de cerveza") NO anota. Es el mismo daño que P102 (cobra 6 o 10 veces lo pedido, sin forma de anular), "pack x 6" es una presentación corriente y el README no lo avisa | P; reproducido por I | media | sí (con el `mate.py` de `e3d228e` da lo mismo) | **pendiente (vuelta 5, obligatorio)**. Arreglo sugerido por P: no anotar si adelante de la cantidad va la unidad de venta o "un/una", o si la cantidad va pegada detrás de "x" y coincide con un número de la presentación; con estas frases como prueba en el ejemplo 13 y en `_PRUEBAS_DEL_EQUIPO` |
| P163 | "quiero N unidades de X" se anota como N bultos aunque el bulto traiga varias unidades: con la muestra "quiero 10 unidades de yerba" anota 10 bolsones ($ 350.000,00); "quiero 12 unidades de agua" con "caja de 12 botellas" anota 12 cajas; "quiero 6 unidades de cerveza" con "pack x 6" anota 6 packs. "unidades" y "bultos" están en `palabras_sueltas()`. Si la presentación dice "unidades" ("caja de 12 unidades") sí pregunta. El programa usa "unidades" para decir bultos ("envíos desde 10 unidades") | P, implementador; reproducido por I | baja | sí | pendiente: lo decide el dueño (¿preguntar cuando la presentación trae un número?). Va con P162 |
| P164 | Presentación que trae la cuenta sin un sustantivo detrás ("caja x 6", "paquete x 100", "x 12", "12", "tira 100u"): lo de adentro es el propio producto y el pedido se anota como bultos enteros ("quiero 6 vinos" anota 6 cajas, "quiero 100 servilletas" anota 100 paquetes, $ 120.000,00). También "cerveza x 6", "quiero 6 x cerveza", "cerveza pack x 6", "yerba x 10" anotan N bultos. Ambiguo de por sí: tiene la misma forma que "quiero 12 azucar". El README avisa de la presentación que arranca con número, no de esta forma | R, P | baja | sí | pendiente: como mínimo avisarlo en el README; va con P162 |
| P165 | Después de la pregunta de Ventas, contestar solo "1" o "uno solo" no retoma el pedido (va a la IA: "Decime el nombre del producto y cuántas unidades querés"). Hay que escribir el ejemplo que da la respuesta ("quiero 1 yerba"), que sí anota. No descuenta nada de más | R, implementador | baja | sí | aceptado como límite: Ventas no guarda la charla entre consultas |
| P166 | Pedidos bien dichos que no se anotan (lado seguro, no tocan stock): "quiero 2 cajas de 12 botellas de agua" y "quiero 1 caja de agua, 12 botellas" ("Veo más de un número"); "quiero 5 yerbas de 1 kg", "quiero 2 arroz de 30 kg", "quiero 2 aceites de 900 ml" (preguntan por la medida: antes de `88e353c` anotaban; con la unidad adelante, "quiero 2 bolsas de arroz de 30 kg", anotan); "quiero 2 bultos de huevos" con "maple de 30 huevos" pregunta, aunque el README dice que con "bultos" se pide; "quiero 3 bolsitas de papas"; "quiero 1 maple" sin el producto | P, R, implementador | baja | no (es de esta vuelta) | aceptado como decisión (ver abajo), salvo el renglón del README sobre "bultos" con un producto que se llama como lo de adentro: pendiente |
| P167 | Abreviaturas y diminutivos de la unidad de adentro ("10 paq de yerba", "6 botellitas de aceite", "10 kilitos de azucar", "6 latas de cerveza" con "pack x 6") no reciben la pregunta nueva sino la cuenta por bultos enteros: "10 x Yerba mate ... total $ 350.000,00. Todavía no anoté nada: para pedirlo, escribí "quiero 10 yerba"". No anotan ni descuentan, pero la respuesta empuja a pedir 10 bolsones. Avisado en el README | P, R, implementador | baja | sí | pendiente (si entra) |
| P168 | "encargo de yerba 5" anota ("encargo" es palabra de pedir y el "de" no va pegado a la cantidad); "el encargo de yerba 5" y "encargo de 5 yerbas" no. Consecuencia de la regla del "de" pegado | R | baja | sí | aceptado como límite |
| P169 | Con una presentación vacía la respuesta muestra paréntesis vacíos: "Anotado: 10 x Servilletas () a $ 800,00 cada uno". Anota y descuenta bien | P | baja | sí | pendiente (prolijidad) |
| P170 | En una planilla con dos productos que comparten una palabra ("Paquete regalo" y unas galletitas por "paquete"), "quiero 24 paquetes de galletitas" contesta "Vamos de a un producto por vez" en vez de la pregunta de la unidad. Viene de `leer_pedido()` del ejemplo 12; no anota | implementador | baja | sí | pendiente (si entra) |
| P102 | Un pedido dicho en la unidad de adentro de la presentación se anotaba como bultos enteros | P (vuelta 3) | media | sí | **resuelto** en sus frases y unas 60 más, en el ejemplo 13 y en el equipo creado (R, P, I). De la misma familia quedan P162 (medio), P163, P164 y P167 |
| P103 | Pasados en tercera persona, "de" suelto adelante y "hago/hacer" sin "un pedido" anotaban | R, P (vuelta 3) | baja | no | **resuelto** (R, P). Resto: "compro 10 yerbas" sin tilde anota (aceptado: es también la forma de pedir en primera persona) y P168 |
| P159 | El `candado` del buzón se creaba con permiso de ejecución | seguridad | baja | no | **resuelto**: 0644 con umask 0022 (P, I, mirando el archivo; R solo por el código y las pruebas: en su corrida no encontró el archivo) |
| P104 | "hola, 5 yerbas para retirar" anota 5 y descuenta (40 a 35) | R, P (vuelta 3) | baja | sí | sigue igual, reproducido por P e I; no era tarea de esta vuelta. El matiz del README sigue pendiente |
| P105 a P111, P80 de fondo, P85 a P88, P91, P94 | ver la vuelta 3 | — | baja | — | sin cambio; nadie los volvió a mirar en esta vuelta |

No verificado por nadie en esta vuelta: Windows, otra versión de Python que la 3.13, la IA de
verdad, cerrar la ventana con la X. R no corrió `pytest` de `mate/modelo`.

**Decisiones técnicas nuevas**
- Lo de adentro del bulto es lo que lleva un NÚMERO adelante en la presentación. Se descartó
  "todo lo que no es la primera palabra" como regla general (la propuesta de la vuelta 3)
  porque frenaba las palabras que describen ("sin sal", "para kiosco"); queda solo para la
  presentación sin ningún número.
- Si la presentación arranca con un número no hay unidad de venta: la palabra para pedir es
  "bulto" y la respuesta lo dice con un ejemplo.
- Ante la unidad de adentro, Ventas pregunta con un texto propio del programa y un ejemplo que
  anota; no viaja nada a Depósito y no se consulta a la IA.
- **Nombrar una medida sin la unidad de venta pregunta en vez de anotar** ("quiero 2 azucar de
  10 kg", "quiero 2 lavandinas de 5 litros", "quiero 2 yerbas de 1 kg", "quiero 5 yerbas en
  paquetes"). Antes de `88e353c` anotaba. Es un cambio de conducta hacia el lado seguro,
  afirmado en las pruebas y avisado en el README; con la unidad adelante ("quiero 2 bolsas de
  arroz de 30 kg") anota. Queda como decisión, salvo que el dueño diga otra cosa.
- El "de" adelante de la cantidad frena solo pegado a ella (salteando "un/unas/otras"). No se
  mira si el "de" es del nombre del producto, porque "de yerba quiero 2" no lo es y también es
  un pedido. Se descartó frenar cualquier "de" adelante: rompía siete pedidos legítimos.
- "bultos" y "unidades" siguen siendo palabras sueltas que anotan: "bultos" es ahora la forma
  de pedir que da la respuesta cuando la presentación arranca con un número (por eso P163 no
  se tocó sin decisión del dueño).
- Una pregunta de precio en la unidad de adentro contesta la pregunta de la unidad y no la
  cuenta: no se cambió porque lo afirma una prueba.
- Integrador: no arregló nada. P162 cambia qué se anota y pide prueba y revisión
  independiente. Aunque ya estaba y R aprobó, frena el cierre por el mismo motivo que P102 en
  la vuelta 3: saca stock y cobra de más sin forma de anular, contra "ante la duda no se
  anota", y la tabla de arriba se armó con P102 como vara. Si el dueño decide que P162 no
  frena (es la objeción de un solo agente y está fuera de la letra de P102), lo que queda para
  cerrar es solo el cierre de verdad (`VERSION`, README, P133).

**Para la vuelta 5**: P162 (obligatorio), con las frases de P como prueba. Si entran, porque
tocan el mismo tramo: P163 (con la decisión del dueño), el aviso de P164 en el README, el
renglón de "bultos" de P166 y el matiz del README de P104. Después: P167, P169, P170 y los
bajos de la vuelta 3 (P106 a P110). El orden del dueño sigue igual: primero A, después B; nada
de B todavía.

## Diseño del buzón (resumen)

El alcance pedía una etapa de diseño revisada antes de programar el cambio 3, y esa etapa no
quedó registrada. **Esto no es ese registro**: es un resumen armado después, por el integrador
de cierre, leyendo el README ("Dos programas que se hablan: el buzón") y `mate/mate.py` (el
tramo "Buzón entre programas (0.7)") sobre `ea475e7`. Dice qué decisiones tiene hoy el buzón;
no dice quién las revisó antes de programar ni qué alternativas se discutieron, porque eso no
está escrito en ningún lado. Lo que se probó de cada una está en las vueltas del cambio 3.

- **Sin red y sin nada que instalar.** Un mensaje para otro programa es un archivo; se entrega
  cuando ese otro programa corre. Solo entre programas de la **misma carpeta** (sin
  subcarpetas ni rutas). Es la base de B, pero B (entre máquinas) no está empezado.
- **Sin gastar cupo del lenguaje.** Se escribe `usar buzon "deposito.mate"`. `buzon` no es una
  palabra reservada: solo significa algo después de `usar` (como `python`). No hay funciones
  incluidas nuevas (siguen 36 palabras y 48 funciones). Se manda con el `enviar` de siempre.
- **El otro programa se lee, nunca se ejecuta.** De él se toman sus agentes, lo que cada uno
  sabe recibir y los mensajes que cruzan; no se carga su Python ni se miran sus funciones,
  variables, estado ni pruebas. Dos programas pueden nombrarse mutuamente; uno no se manda a sí
  mismo. Si un mensaje que cruza está declarado distinto en cada programa, el error sale antes
  de correr.
- **Solo `enviar`, no `preguntar`.** El otro programa puede no estar corriendo; la contestación
  se recibe con un `al recibir`. Tampoco se puede `crear` una copia de un agente ajeno, usar
  `aprender`, `lecciones` o `a_json` con él, mirarle el estado ni ponerlo adentro de un mensaje.
  `responder` le contesta al remitente por su buzón sin necesidad de `usar buzon`.
- **Dónde queda.** El buzón de `deposito.mate` es la carpeta `deposito.buzon`, al lado del
  programa: un archivo `.json` por mensaje (el "sobre"), la carpeta `rechazados` y un archivo
  `candado`. El sobre lleva `mate_buzon` (versión del formato, hoy 1), `id`, `clase`
  ("mensaje" o "falla"), `de` y `para` (programa y agente), `conversacion`, `en_respuesta_a` y
  el mensaje como `{"tipo", "campos"}`. Lo que el sobre trae de más se deja pasar (puede ser de
  una versión siguiente); uno con una versión más nueva no se entrega.
- **Cuándo sale y cuándo se atiende.** Lo que sale se anota primero en la memoria del que envía
  (parte `"buzon"`, "por salir") junto con el estado de sus agentes, **en una sola
  escritura**; recién después se reparte. Así un corte no deja un mensaje enviado con el estado
  sin guardar, ni al revés. Lo que llegó se atiende cuando el programa termina sus renglones.
  Con un error o Ctrl+C sale igual lo ya dejado, y lo que llegó queda esperando con un aviso;
  con la X no sale ni se guarda nada.
- **Una sola vez.** Lo que identifica a un mensaje es (programa que lo manda, id). El que
  recibe anota los que ya atendió (hasta 2000, más los que sigan en la carpeta) y no los
  atiende dos veces aunque el archivo siga ahí después de un corte.
- **Se escribe sin dejar archivos a medias**: primero un provisorio `.tmp` y después se le pone
  el nombre. Un provisorio de más de un día quedó de un corte y se borra.
- **Una ventana por vez.** El `candado` lo toma una sola ventana, sin esperar (`flock` en
  Linux, `msvcrt.locking` en Windows), y el sistema lo suelta si el programa muere. Si lo tiene
  otra ventana, esta avisa y deja los mensajes para la próxima corrida.
- **Nunca se confía en lo que hay en el buzón.** El contrato se controla dos veces: al enviar y
  al llegar, con el contrato del que recibe. Lo que no se puede entregar (no cumple el
  contrato, el agente no existe, no es un sobre) **no corta el programa**: se avisa, se sigue
  con los demás y el archivo va intacto a `rechazados` con un `.motivo.txt`. Si el agente falla
  atendiendo un mensaje válido, también va a `rechazados`: no se reintenta para siempre.
- **El que envió se entera.** Un rechazo vuelve como un sobre de clase "falla" y llega al
  `al fallar` del agente que lo mandó (o sale como `aviso:`). Una falla nunca se contesta con
  otra. El motivo se corta en 400 letras.
- **Topes y forma de lo que llega**: un sobre de más de 2 MB no se abre; un mensaje que sale no
  pasa de 1 MB; hasta 1000 sobres por corrida (el resto espera); hasta 100 niveles de cosas una
  adentro de otra; nada de números no finitos ni enormes; un mensaje entre programas no lleva
  agentes. El id y los nombres de programa y de carpeta no pueden armar una ruta (ni barras, ni
  dos puntos, ni punto adelante, ni nombres reservados de Windows).
- **Accesos directos** (del arreglo de seguridad, P158 y P159): Mate no escribe a través de un
  acceso directo dejado adentro del buzón (ni en los `.tmp` ni en el `candado`): lo saca y crea
  un archivo de verdad; una carpeta que es un enlace no vale como buzón. El `candado` se crea
  como archivo de datos, sin permiso de ejecución. `escribir_archivo` y `agregar_a_archivo` no
  escriben dentro de una carpeta `.buzon` ni en la memoria de un programa nombrado con
  `usar buzon`.
- **Solo `correr` usa el buzón.** `probar`, `ensayar`, `verificar` y la `consola` no leen ni
  escriben ninguno. En una prueba lo enviado se ve con `mensajes_enviados()` y el otro agente
  se reemplaza con `simular`. `correr --ia-simulada` sí escribe buzones de verdad (P155). La
  orden `buzon programa.mate` solo mira. `corregir`, `lecciones` y `--olvidar` no tocan la
  parte `"buzon"` de la memoria.
- **Lo que el diseño deja abierto** (ya está en las tablas): se entrega cualquier sobre aunque
  el programa no haya pedido buzón ni conozca al remitente (P161 (1), **antes de B**);
  caracteres de control de un sobre escrito a mano llegan a la pantalla (P154, P161 (2));
  `rechazados` no se limpia (P161 (4)); con varias ventanas del mismo programa se puede perder
  un envío (P156); una "junction" de Windows en Python 3.10 y 3.11 (P160); y nada de esto se
  corrió en una Windows de verdad (P149).

## Estado final de la 0.7

**Estado de hoy** (integrador de cierre, sobre `ea475e7`; rama `equipo/mate-0.7`, todo en
commits locales, sin subir nada y sin tocar `main`). Desde el estado anterior hubo dos commits
de código del implementador (`88e353c` y `ea475e7`, la vuelta de cierre del cambio 1). El
integrador no tocó código, pruebas ni `VERSION`: corrió las tres corridas, hizo un recorrido
corto en una carpeta temporal propia y escribió esto. El estado anterior queda más abajo, como
historia.

**La 0.7 sigue SIN cerrar.** La vuelta de cierre arregló lo que frenaba (P102), y también P103
y P159, pero el agente de pruebas no aprobó: encontró un problema medio de la misma familia,
P162 ("quiero un pack x 6 de cerveza" anota 6 packs; "quiero un bolson x 10 de yerba" anota 10
bolsones). Ya estaba antes de la vuelta, pero hace el mismo daño que P102. Por eso `VERSION`
sigue en `"0.6"`, el README sigue diciendo "Qué se está sumando para la 0.7" y "Límites de la
versión 0.6", y la prueba que afirma el número de versión no se tocó.

| Cambio | Vueltas | Estado | Quién aprobó | Qué lo frena |
|---|---|---|---|---|
| 1. Equipo del negocio (ejemplo 13 y `nuevo equipo`) | 4 (tres más la de cierre) | **NO aprobado** | R aprueba; P no | **P162 (medio)**: repetir la presentación con "x N" anota N bultos y descuenta stock. Falta la vuelta 5. P102, P103 y P159 quedaron resueltos. Además, bajos: los de la vuelta 3 que siguen (P104 a P111 y los de fondo) y P163 a P170 |
| 2. Ensayar la conversación entre agentes | 3 | **aprobado** | R y P | nada; 14 bajos |
| 3. Buzón entre programas (la base de B) | 2 | **aprobado** | R y P | nada; bajos. El diseño tiene ahora un resumen armado después ("Diseño del buzón (resumen)", arriba); la revisión ANTES de programar que pedía el alcance sigue sin registro |
| Seguridad del conjunto | 2 pasadas | **aprobado sobre `e3d228e`** | especialista en seguridad | nada. P159 resuelto en la vuelta de cierre; quedan P160 y P161. Los dos commits nuevos no pasaron por el especialista (tocan el ejemplo 13, las pruebas, la documentación y, de `mate.py`, el texto del equipo creado y el modo del `candado`) |
| Versión | — | **sigue en 0.6** | — | espera a que cierre el cambio 1 (P133) |

Sobre el orden del dueño (primero A, después B): lo hecho es A más la base de B (el buzón, en
una misma PC y sin red). De B no se hizo nada, y no corresponde empezarlo hasta cerrar A.

**Números de las pruebas** (integrador, Linux, Python 3.13.18, `MATE_SIN_REGISTRO=1`, sobre
`ea475e7`)

| Comando | Hoy (`ea475e7`) | Estado anterior (`e3d228e`) | Punto de partida de la 0.7 (`e78f2e9`) |
|---|---|---|---|
| `python3 -m pytest mate/pruebas mate/modelo -q -p no:cacheprovider` | 1110 pasan, 0 fallan (161 s) | 1100 pasan, 0 fallan | 883 pasan, 0 fallan |
| `python3 mate/mate.py probar mate/ejemplos` | 104 de 104, en 22 archivos | 100 de 100, en 22 archivos | 66 de 66, en 18 archivos |
| `python3 mate/mate.py probar mate/curso` | 37 de 37, en 26 archivos | 37 de 37, en 26 archivos | 30 de 30, en 24 archivos |

Después de las tres corridas `git status --short` quedó vacío y en `mate/ejemplos` no quedó
ninguna memoria ni carpeta `.buzon`. El equipo creado con `nuevo equipo` da `probar` 18 de 18
(antes 15) y `ensayar --ia-simulada` 12 de 12 (antes 10); el ejemplo 13, 30 de 30 (antes 26).
Los renglones de prueba quitados entre `e3d228e` y `ea475e7` son 13 y son solo conteos que
subieron (lo miraron R, P y yo). La batería tarda cerca de 160 s: hay que correrla con un tope
largo (P148). El "1092" que informan el implementador y R es solo `mate/pruebas/test_mate.py`.

**Recorrido de hoy** (integrador, carpeta propia de `mktemp -d`, ya borrada; cada frase en
corrida limpia, mirando la memoria guardada)

| Frase, sobre un equipo recién creado | Qué dio |
|---|---|
| `quiero 10 paquetes de yerba` | "Todavía no anoté nada, para no equivocarme: dijiste "paquetes", y Yerba mate se vende por bolsón de 10 paquetes de 1 kg...". Yerba mate queda en 40: **P102 resuelto** |
| `quiero 6 botellas de aceite` | lo mismo con "botellas"; Aceite queda en 8 |
| `aceite de girasol 3 cajas` | "Anotado: 3 x Aceite de girasol", 8 a 5, y "Compras: hay que reponer Aceite de girasol (quedan 5)" |
| `compró 10 yerbas` | da la cuenta, "Todavía no anoté nada"; stock intacto (P103) |
| `quiero un bolson x 10 de yerba` | "Anotado: 10 x Yerba mate (bolsón de 10 paquetes de 1 kg)... total $ 350.000,00"; Yerba mate queda en 30: **P162 reproducido** |
| `quiero 10 unidades de yerba` | anota 10 bolsones, queda 30 (P163) |
| `hola, 5 yerbas para retirar` | anota 5, queda 35 (P104, sigue igual) |
| Buzón: `buzon_ventas`, `buzon_deposito`, `buzon_ventas` | "Pedido A-17: reservado. Quedan 8."; los dos `candado` quedan `-rw-r--r--` (P159 resuelto) |

El recorrido largo del dueño (la charla de 7 consultas, la segunda corrida, `ensayar` con
memoria vieja, el buzón paso a paso) está en el estado anterior, abajo; hoy los conteos son 18
de 18 y 12 de 12 donde ahí dice 15 de 15 y 10 de 10, y el paso "P102 reproducido" ya no pasa.

**Pendientes, por gravedad**

Altos: ninguno.

Medios (uno, y frena la 0.7):
- **P162**, cambio 1: si el cliente repite la presentación con "x N" ("quiero un pack x 6 de
  cerveza", "quiero una caja x 6 de vino", "quiero un bolson x 10 de yerba", "quiero bolsa x 10
  azucar"), el número de adentro del bulto se anota como cantidad de bultos y descuenta stock,
  sin forma de anular. Pasa con la planilla de muestra y en el ejemplo 13. Ya estaba en
  `e3d228e`. Arreglo sugerido por P: no anotar si adelante de la cantidad va la unidad de venta
  o "un/una", o si la cantidad va pegada detrás de "x" y coincide con un número de la
  presentación. Necesita vuelta 5 con R y P, y las frases como prueba en el ejemplo 13 y en el
  equipo que crea `nuevo equipo`. Un equipo ya creado es una copia fija: después del arreglo
  hay que crearlo de nuevo (vale también para el arreglo de P102 de hoy).

Para decidir el dueño:
- Si P162 frena o no. R aprobó, el problema ya estaba y queda fuera de la letra de P102; P no
  aprobó porque el daño es el mismo. El integrador lo dejó frenando, con la misma vara que se
  usó para P102.
- P163: "quiero 10 unidades de yerba" anota 10 bolsones. El programa usa "unidades" para decir
  bultos; ¿tiene que preguntar cuando la presentación trae un número?
- La decisión nueva de esta vuelta: nombrar una medida sin la unidad de venta ("quiero 2 azucar
  de 10 kg", "quiero 2 yerbas de 1 kg") ahora pregunta en vez de anotar.

Bajos que conviene mirar primero:
- P161 (1): cualquier sobre se entrega; antes de B.
- P163, P164 y P167, de la familia de P102: "N unidades", la presentación "caja x 6" sin
  sustantivo ("quiero 6 vinos" anota 6 cajas) y las abreviaturas ("10 paq de yerba" no anota,
  pero la respuesta empuja a pedir 10 bolsones).
- P104 y P105: "5 yerbas para retirar" y "llevo 10 yerbas al local" se anotan como venta.
  (P103 quedó resuelto; resta "compro 10 yerbas" sin tilde, aceptado.)
- P166: el README dice que con "bultos" se pide y "quiero 2 bultos de huevos" (presentación
  "maple de 30 huevos") pregunta.
- P154 y P161 (2): caracteres de control de un sobre escrito a mano llegan a la pantalla.
- P152 y P156: con Ctrl+C se pierde sin aviso lo que estaba en la cola para otro agente del
  mismo programa; con varias ventanas del mismo programa se puede perder un envío.
- P153 y P136: el `.gitignore` tapa una memoria olvidada en `mate/ejemplos`, que rompe una prueba.
- P133: `VERSION`, `ayuda`, el curso y el README de la raíz no cuentan todavía la 0.7 (queda
  para el cierre de verdad).

Los demás bajos abiertos (ninguno traba):
- Cambio 1: P106 a P111, P165, P168, P169, P170, P80 de fondo, P85, P86, P87, P88, P91, P92, P94.
- Cambio 2: P115, P120, P125, P127, P128 a P132.
- Cambio 3: P137, P140, P142 y P147 a medias; P148, P150, P151, P155, P157.
- Seguridad: P160 y el resto de P161.
- De todos: P11 y P149 (Windows y una IA de verdad).
- Sin registro: la revisión del diseño del buzón antes de programar. El resumen de arriba
  cuenta las decisiones que hoy tiene el buzón, armado después desde el README y el código.

Resueltos desde el estado anterior: P102 (medio), P103 y P159.

**Lo que no se pudo probar**
- **Windows de verdad**: nada de la 0.7 se corrió ahí. En particular el candado
  (`msvcrt.locking`), el paso a `rechazados`, los comandos con `py`, Ctrl+C (esas pruebas se
  saltean en Windows) y P160.
- **Ollama y Claude de verdad**: todo fue con `--ia-simulada`. No se sabe cómo contesta una IA
  real a lo que Ventas le deriva, ni cuánto gasta.
- `pytest` completo en otra versión de Python que la 3.13. En esta vuelta nadie corrió nada
  fuera de 3.13.
- Cerrar la ventana con la X.

**Para el dueño, en Windows**: valen los mismos comandos del estado anterior, abajo. Cambia que
`probar mi_negocio.mate` da 18 de 18 y `ensayar` 12 de 12 sobre un equipo recién creado. En la
charla, `quiero 10 paquetes de yerba` ahora tiene que preguntar y no anotar; para ver P162,
`quiero un bolson x 10 de yerba`. `ayuda` va a decir "Mate 0.6": es lo esperado hoy.

**Lo que sigue**: la vuelta 5 del cambio 1 (P162, con P163, P164, P166 y P104 si entran y con
lo que el dueño decida); después, el cierre de verdad: `VERSION` a 0.7, "Qué cambió en la
0.7", "Límites de la versión 0.7", la prueba del número de versión y P133. Recién ahí, y con
P161 (1) resuelto, B.

### Estado anterior, sobre `e3d228e` (historia: antes de la vuelta de cierre del cambio 1)

**Estado de hoy** (integrador de cierre, sobre `e3d228e`; rama `equipo/mate-0.7`, 16 commits
locales más este registro, sin subir nada y sin tocar `main`). El integrador no tocó código ni
pruebas en este cierre: corrió las tres corridas, hizo el recorrido del dueño en una carpeta
temporal propia y escribió esto.

**La 0.7 NO queda cerrada.** Dos de los tres cambios y la seguridad están aprobados, pero el
cambio 1 tiene un problema medio abierto (P102). Por eso `VERSION` sigue en `"0.6"`, el README
sigue diciendo "Qué se está sumando para la 0.7" y "Límites de la versión 0.6", y la prueba
que afirma el número de versión no se tocó. La regla era pasar a 0.7 solo con todo aprobado.

| Cambio | Vueltas | Estado | Quién aprobó | Qué lo frena |
|---|---|---|---|---|
| 1. Equipo del negocio (ejemplo 13 y `nuevo equipo`) | 3 | **NO aprobado** | R aprueba; P no | **P102 (medio)**: un pedido dicho en la unidad de adentro de la presentación se anota como bultos enteros. Falta la vuelta 4. Además 15 bajos |
| 2. Ensayar la conversación entre agentes | 3 | **aprobado** | R y P | nada; 14 bajos |
| 3. Buzón entre programas (la base de B) | 2 | **aprobado** | R y P | nada; 11 bajos. El diseño revisado antes de programar sigue sin registro acá |
| Seguridad del conjunto | 2 pasadas | **aprobado sobre `e3d228e`** | especialista en seguridad | nada; quedan bajos (P159 a P161) |
| Versión | — | **sigue en 0.6** | — | espera a que cierre el cambio 1 (P133) |

Sobre el orden del dueño (primero A, después B): lo hecho es A más la base de B (el buzón, en
una misma PC y sin red). De B no se hizo nada, y no corresponde empezarlo hasta cerrar A.

**Números de las pruebas** (integrador, Linux, Python 3.13.18, `MATE_SIN_REGISTRO=1`, sobre
`e3d228e`)

| Comando | Hoy | Punto de partida de la 0.7 (`e78f2e9`) |
|---|---|---|
| `python3 -m pytest mate/pruebas mate/modelo -q -p no:cacheprovider` | 1100 pasan, 0 fallan (109 s) | 883 pasan, 0 fallan |
| `python3 mate/mate.py probar mate/ejemplos` | 100 de 100, en 22 archivos | 66 de 66, en 18 archivos |
| `python3 mate/mate.py probar mate/curso` | 37 de 37, en 26 archivos | 30 de 30, en 24 archivos |

Por el camino: 938 después del cambio 1, 1014 después del 2, 1096 después del 3 y 1100 con las
cuatro pruebas del arreglo de seguridad. Después de las tres corridas `git status --short`
quedó vacío y en `mate/ejemplos` no quedó ninguna memoria ni carpeta `.buzon` (mirado con `ls`,
porque el `.gitignore` las tapa: P153). Las vueltas registran que ningún renglón de prueba se
sacó ni se aflojó; yo no repetí ese diff completo en este cierre. La batería tarda cerca de
110 s: hay que correrla con un tope largo (P148).

**El recorrido del dueño** (integrador, en una carpeta propia creada con `mktemp -d` y borrada
al terminar; siempre con `MATE_SIN_REGISTRO=1`)

| Paso | Qué dio |
|---|---|
| `nuevo equipo mi_negocio` | creó `mi_negocio.mate`, `mi_negocio_precios.csv` y `mi_negocio_casos.txt` y mostró los seis pasos que siguen. Repetido con el mismo nombre: "no creé nada... no piso archivos" |
| `verificar mi_negocio.mate` | "sin errores" |
| `probar mi_negocio.mate` | 15 de 15 |
| `correr mi_negocio.mate --ia-simulada --traza`, 7 consultas y `chau` | "quiero 20 azucar": Ventas → Depósito → Compras (`Reservar`, `Reponer`, `Anotado`, `Reserva`), quedan 5. "quiero 3 yerbas": anotado, $ 105.000,00, sin `Reponer`. "quiero 5 azucar": anotado, quedan 0 y NO sale otro `Reponer`. "quiero 100 harina": "De Harina 000 quedan 12; no llego a 100", no vende. "cuanto salen 3 yerbas?": da la cuenta, "Todavía no anoté nada", solo `ConsultarStock`. "tenes cafe?": va a la IA simulada, sin tocar Depósito. Al cerrar: "Compras: hay que reponer Azúcar (quedan 0)" |
| La misma corrida, **P102 reproducido** | "quiero 10 paquetes de yerba" contestó "Anotado: 10 x Yerba mate (bolsón de 10 paquetes de 1 kg)... total $ 350.000,00" y descontó 10 bolsones (el cliente pedía 1) |
| `correr mi_negocio.mate --ia-simulada` de nuevo | arranca con "Compras: hay que reponer Azúcar (quedan 0)"; "quiero 1 azucar": "De Azúcar ahora no hay stock"; "quiero 2 yerbas": anotado; "ingreso 30 azucar": "Entraron 30 de Azúcar: ahora hay 30". La memoria quedó con yerba 25, azúcar 30 y la lista de Compras vacía: el stock se acuerda |
| `ensayar mi_negocio.mate mi_negocio_casos.txt --ia-simulada` | 9 de 10. Falla "quiero 20 azucar" porque con 30 en stock ya no baja del mínimo y no viaja `Reponer`; el informe muestra la conversación y explica que es por lo que Depósito recuerda, y que se arregla con el caso o con `--olvidar`. La memoria no cambió (mismo md5 antes y después) |
| `ensayar` sobre un equipo recién creado (`nuevo equipo recien`) | 10 de 10 |
| Buzón: copié `buzon_ventas.mate`, `buzon_deposito.mate` y `buzon_mensajes.mate` a una subcarpeta; `correr buzon_ventas.mate` | "Buzón: dejé 1 mensaje para buzon_deposito.mate; le llega la próxima vez que corra." |
| `correr buzon_deposito.mate` | "Buzón: atendí 1 mensaje (1 de buzon_ventas.mate)." y dejó 1 para Ventas |
| `correr buzon_ventas.mate` | "Pedido A-17: reservado. Quedan 8." y "Buzón: atendí 1 mensaje" |
| Los dos de nuevo | no mandan ni atienden nada: el mensaje llegó una sola vez |
| `buzon buzon_deposito.mate` | "Esperan: ninguno. Por salir: ninguno. Rechazados: ninguno." |
| `probar` en esa subcarpeta | 8 de 8 en 3 archivos |

No repetí en este recorrido: el sobre que no cumple el contrato, los cortes con Ctrl+C ni las
recetas de seguridad. Eso lo probaron R, P y el especialista en sus vueltas.

**Seguridad** (especialista, dos pasadas; **aprueba**)
- P158 (medio, **resuelto** en `e3d228e`): el buzón escribía a través de un acceso directo
  plantado adentro (los provisorios `.tmp` del motivo y del aviso de falla), y podía pisar un
  archivo de afuera. El especialista repitió las dos recetas: el archivo de afuera quedó
  intacto. Lo mismo para un `candado` que es un enlace roto (en Linux). Las cuatro pruebas
  nuevas fallan con el `mate.py` anterior y pasan con el nuevo. El commit toca `mate.py` (27
  renglones), README (4) y agrega 106 renglones de prueba sin sacar ninguno.
- P159 (bajo, nuevo): el archivo `candado` ahora se crea con permiso de ejecución (0755 en vez
  de 0644) porque `os.open` no recibe el modo. Lo vi en mi recorrido (`-rwxr-xr-x`). Está
  vacío y en Windows no cambia nada; se arregla pasando `0o666`.
- P160 (bajo, ya estaba, **no verificado**, solo leído): en Windows con Python 3.10 y 3.11,
  `es_carpeta_de_verdad()` no reconoce una "junction". Si `<programa>.buzon\rechazados` lo
  fuera, los sobres rechazados se crearían en otra carpeta (no pisa nada). La oración nueva
  del README sobre accesos directos queda un poco más amplia que lo probado.
- P161 (bajos, ya estaban, sin tocar ni volver a reproducir): (1) se entrega cualquier sobre
  aunque el programa no haya pedido buzón ni conozca al remitente — **hay que resolverlo antes
  de empezar B**; (2) caracteres de control en `tipo` y `motivo` salen crudos en la terminal y
  en el `.motivo.txt` (va con P154); (3) nombres reservados de Windows en el id de un sobre y
  en `nuevo equipo`; (4) `rechazados` no se limpia y el aviso de falla copia el mensaje entero;
  (5) falta decir en el README que `correr --ia-simulada` sí escribe buzones de verdad (P155).
- Una diferencia que no pude aclarar: el especialista informa "1082 passed" para la batería
  completa y a mí me da 1100 sobre el mismo commit. No dice sobre qué carpetas corrió.

**Pendientes, por gravedad**

Altos: ninguno.

Medios (uno, y frena la 0.7):
- **P102**, cambio 1: "quiero 10 paquetes de yerba" anota 10 bolsones de 10 paquetes y
  descuenta stock, sin forma de anular; "quiero 6 botellas de aceite" anota 6 cajas de 12.
  Arreglo propuesto en la vuelta 3: de la presentación aceptar solo la unidad de venta, o no
  anotar ante la duda. Necesita vuelta 4 con R y P, y las frases como prueba en el ejemplo 13
  y en el equipo que crea `nuevo equipo`. Un equipo ya creado es una copia fija: después del
  arreglo hay que crearlo de nuevo.

Bajos que conviene mirar primero:
- P161 (1): cualquier sobre se entrega; antes de B.
- P103, P104 y P105: frases que se anotan como venta sin serlo ("compró 10 yerbas", "5 yerbas
  para retirar", "llevo 10 yerbas al local"). Van con P102, porque también descuentan stock.
- P154 y P161 (2): caracteres de control de un sobre escrito a mano llegan a la pantalla.
- P152 y P156: con Ctrl+C se pierde sin aviso lo que estaba en la cola para otro agente del
  mismo programa; con varias ventanas del mismo programa se puede perder un envío.
- P153 y P136: el `.gitignore` tapa una memoria olvidada en `mate/ejemplos`, que rompe una prueba.
- P133: `VERSION`, `ayuda`, el curso y el README de la raíz no cuentan todavía la 0.7 (queda
  para el cierre de verdad).

Los demás bajos abiertos (ninguno traba):
- Cambio 1: P106 a P111, P80 de fondo, P85, P86, P87, P88, P91, P92, P94.
- Cambio 2: P115, P120, P125, P127, P128 a P132.
- Cambio 3: P137, P140, P142 y P147 a medias; P148, P150, P151, P155, P157.
- Seguridad: P159, P160 y el resto de P161.
- De todos: P11 y P149 (Windows y una IA de verdad).
- Sin registro: el diseño del buzón y su revisión, que el alcance pedía antes de programar.

**Lo que no se pudo probar**
- **Windows de verdad**: nada de la 0.7 se corrió ahí. En particular el candado
  (`msvcrt.locking`), el paso a `rechazados`, los comandos con `py`, Ctrl+C (esas pruebas se
  saltean en Windows) y P160.
- **Ollama y Claude de verdad**: todo fue con `--ia-simulada`. No se sabe cómo contesta una IA
  real a lo que Ventas le deriva, ni cuánto gasta.
- `pytest` completo en Python 3.10, 3.11, 3.12 y 3.14: solo se corrió en 3.13 (P corrió
  `probar` y sus casos en las otras).

**Para el dueño, en Windows** (parado en la carpeta que tiene adentro a `mate`; para los
pasos del equipo conviene una carpeta de trabajo aparte y poner la ruta completa de `mate.py`)

```
py mate\mate.py ayuda
py -m pytest mate\pruebas mate\modelo -q -p no:cacheprovider
py mate\mate.py probar mate\ejemplos
py mate\mate.py probar mate\curso
py mate\mate.py nuevo equipo mi_negocio
py mate\mate.py verificar mi_negocio.mate
py mate\mate.py probar mi_negocio.mate
py mate\mate.py correr mi_negocio.mate --ia-simulada --traza
py mate\mate.py correr mi_negocio.mate --ia-simulada
py mate\mate.py ensayar mi_negocio.mate mi_negocio_casos.txt --ia-simulada
py mate\mate.py correr buzon_ventas.mate
py mate\mate.py correr buzon_deposito.mate
py mate\mate.py correr buzon_ventas.mate
py mate\mate.py buzon buzon_deposito.mate
```

En la charla: `quiero 20 azucar`, `quiero 3 yerbas`, `quiero 100 harina`, `chau`; y en la
segunda corrida `ingreso 30 azucar`. Para ver P102: `quiero 10 paquetes de yerba`. Para el
buzón, copiar antes `buzon_ventas.mate`, `buzon_deposito.mate` y `buzon_mensajes.mate` de
`mate\ejemplos` a la carpeta de trabajo. `ayuda` va a decir "Mate 0.6": es lo esperado hoy.

**Lo que sigue**: la vuelta 4 del cambio 1 (P102, con P103 a P105 si entran); después, el
cierre de verdad: `VERSION` a 0.7, "Qué cambió en la 0.7", "Límites de la versión 0.7", la
prueba del número de versión y P133. Recién ahí, y con P161 (1) resuelto, B.
