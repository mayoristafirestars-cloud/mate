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

## Punto de partida

- Rama creada desde `main` en `7a4cf4f`.
- Pruebas: 789 pasan y 1 falla. La que falla (`test_estan_los_seis_ejemplos_graduales`) es
  conocida: el ejemplo 12, todavía sin commitear, tiene pocos comentarios. Es parte del cambio 1.

## Vueltas

(El integrador agrega acá una sección por vuelta: qué se hizo, qué encontraron el revisor y
el agente de pruebas, qué se corrigió, qué quedó pendiente y con qué evidencia.)
