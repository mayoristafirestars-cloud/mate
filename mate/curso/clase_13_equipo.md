# Clase 13: Un equipo de agentes que se hablan

## Qué vas a lograr

Hasta la clase 12 había un solo agente, que le contestaba a una persona. Acá vas a armar
un equipo de tres agentes del mismo negocio que se reparten el trabajo hablándose entre
ellos: Ventas atiende el pedido, Deposito lleva el stock y Compras anota lo que hay que
reponer. Vas a ver la conversación entera con `--traza`, y vas a escribir un
`contrato conversacion`, que dice en qué orden se pueden hablar.

## El programa

Está en `mate\curso\clase_13_equipo.mate`:

    # Clase 13: un equipo de agentes que se hablan.
    # Hasta acá un agente le contestaba a una persona. Ahora son tres, y se reparten el
    # trabajo hablándose ENTRE ELLOS:
    #   - Ventas atiende el pedido y hace la cuenta. No sabe cuánto stock hay.
    #   - Deposito es el único que lleva el stock, y lo recuerda de una vez a la otra.
    #   - Compras anota lo que hay que reponer.
    # Cada uno guarda lo suyo: lo único que pasa de uno a otro son mensajes.

    # Todos los mensajes llevan 'charla': el nombre del pedido del que se está hablando.
    mensaje Pedido { charla: texto, producto: texto, cantidad: numero desde 1 } responde Venta
    mensaje Venta { charla: texto, respuesta: texto }
    mensaje Reservar { charla: texto, producto: texto, cantidad: numero } responde Reserva
    mensaje Reserva { charla: texto, alcanzo: logico, quedan: numero desde 0 }
    mensaje Reponer { charla: texto, producto: texto, quedan: numero } responde Anotado
    mensaje Anotado { charla: texto }

    # El orden en que se pueden hablar. Cada paso dice: estando en tal estado, quién le
    # habla a quién, con qué mensaje, y a qué estado se pasa. Lo que no está acá, no pasa.
    contrato conversacion {
        id: "charla",
        inicio: "llega_el_pedido",
        pasos: [
            { estado: "llega_el_pedido", evento: "pregunta", origen: "(programa)",
              destino: "Ventas", mensaje: "Pedido", sigue: "atiende_ventas" },
            { estado: "atiende_ventas", evento: "pregunta", origen: "Ventas",
              destino: "Deposito", mensaje: "Reservar", sigue: "reserva_deposito" },
            { estado: "reserva_deposito", evento: "pregunta", origen: "Deposito",
              destino: "Compras", mensaje: "Reponer", sigue: "anota_compras" },
            { estado: "anota_compras", evento: "respuesta", origen: "Compras",
              destino: "Deposito", mensaje: "Anotado", sigue: "reserva_deposito" },
            { estado: "reserva_deposito", evento: "respuesta", origen: "Deposito",
              destino: "Ventas", mensaje: "Reserva", sigue: "contesta_ventas" },
            { estado: "contesta_ventas", evento: "respuesta", origen: "Ventas",
              destino: "(programa)", mensaje: "Venta", sigue: "fin" }
        ]
    }

    agente Ventas {
        estado precios = { yerba: 3500, azucar: 1250.5 }

        al recibir Pedido como p {
            # El stock no es de Ventas: se lo pide a Deposito.
            sea reserva = preguntar Reservar {
                charla: p.charla, producto: p.producto, cantidad: p.cantidad,
            } a Deposito
            si no reserva.alcanzo {
                responder Venta {
                    charla: p.charla,
                    respuesta: "De {p.producto} quedan {reserva.quedan}: no llego a {p.cantidad}.",
                }
            }
            # La cuenta la hace el programa, con todos los centavos.
            sea total = pesos(p.cantidad * precios[p.producto])
            responder Venta {
                charla: p.charla,
                respuesta: "Anotado: {p.cantidad} de {p.producto}, total {total}.",
            }
        }
    }

    agente Deposito {
        # 'recordado': el stock no vuelve a empezar cada vez que se corre el programa.
        estado recordado stock = { yerba: 10, azucar: 6 }
        # Los productos por los que ya le avisó a Compras: avisa una sola vez.
        estado recordado ya_pedidos = []
        # Con menos unidades que estas, pide que repongan.
        estado stock_minimo = 5

        al recibir Reservar como r {
            sea hay = stock[r.producto]
            # No se vende lo que no hay.
            si r.cantidad > hay {
                responder Reserva { charla: r.charla, alcanzo: falso, quedan: hay }
            }
            stock[r.producto] = hay - r.cantidad
            sea quedan = stock[r.producto]
            si quedan < stock_minimo y no tiene(ya_pedidos, r.producto) {
                preguntar Reponer {
                    charla: r.charla, producto: r.producto, quedan: quedan,
                } a Compras
                ya_pedidos = agregar(ya_pedidos, r.producto)
            }
            responder Reserva { charla: r.charla, alcanzo: verdadero, quedan: quedan }
        }
    }

    agente Compras {
        estado recordado a_reponer = []

        al recibir Reponer como r {
            a_reponer = agregar(a_reponer, r.producto)
            mostrar("Compras: anoté que hay que reponer {r.producto} (quedan {r.quedan}).")
            responder Anotado { charla: r.charla }
        }
    }

    # Un pedido de un cliente: va a Ventas, que sabe con quién hablar.
    funcion pedir(charla, producto, cantidad) {
        sea venta = preguntar Pedido {
            charla: charla, producto: producto, cantidad: cantidad,
        } a Ventas
        mostrar("Ventas: {venta.respuesta}")
    }

    pedir("pedido-1", "yerba", 4)
    pedir("pedido-2", "yerba", 3)
    pedir("pedido-3", "yerba", 2)
    pedir("pedido-4", "yerba", 5)

    # En las pruebas no se usa lo recordado: cada una arranca con el stock de arriba.
    # mensajes_enviados("Reponer") da los mensajes de ese tipo que viajaron en la prueba.
    prueba "un pedido descuenta el stock de Deposito" {
        pedir("a", "azucar", 2)
        sea reservas = mensajes_enviados("Reservar")
        asegurar largo(reservas) == 1 y reservas[0].de == "Ventas" y reservas[0].a == "Deposito"
        # Quedaban 6: con 2 menos son 4, y por 5 ya no alcanza.
        sea venta = preguntar Pedido { charla: "b", producto: "azucar", cantidad: 5 } a Ventas
        asegurar venta.respuesta == "De azucar quedan 4: no llego a 5."
    }

    prueba "a Compras se le avisa una sola vez" {
        pedir("a", "yerba", 4)
        asegurar largo(mensajes_enviados("Reponer")) == 0
        pedir("b", "yerba", 3)
        pedir("c", "yerba", 2)
        asegurar largo(mensajes_enviados("Reponer")) == 1
    }

    prueba "el contrato no deja saltearse a Ventas" {
        # El programa no le puede pedir una reserva a Deposito: eso es de Ventas.
        asegurar falla {
            preguntar Reservar { charla: "a", producto: "yerba", cantidad: 1 } a Deposito
        }
    }

Lo nuevo, parte por parte:

- **Tres agentes, cada uno con lo suyo.** Ventas tiene los precios, Deposito el stock y
  Compras su lista. Ningún agente puede leer ni cambiar el `estado` de otro: si Ventas
  quiere saber si alcanza, se lo tiene que **preguntar** a Deposito con un mensaje. Así
  el stock se descuenta en un solo lugar, y no puede haber dos cuentas distintas.
- **Un agente le pregunta a otro** igual que el programa le pregunta a un agente: con
  `preguntar ... a Deposito`, dentro de su `al recibir`. Y ese otro puede, antes de
  contestar, preguntarle a un tercero (Deposito a Compras).
- **`charla`** es el nombre del pedido del que se está hablando. Va en todos los
  mensajes, para que no se mezclen dos pedidos. Cada pedido lleva un nombre distinto.
- **`contrato conversacion`** dice el orden. Cada paso se lee así: "estando en
  `atiende_ventas`, Ventas le puede preguntar a Deposito con un `Reservar`, y se pasa a
  `reserva_deposito`". `(programa)` es el programa mismo (acá, el cliente). Lo que no
  está escrito en un paso no puede pasar: Mate lo frena con un error.
- **`estado recordado`** (clase 11) en Deposito y en Compras: el stock y lo anotado no
  vuelven a empezar cada vez que corrés el programa.
- **Avisar una sola vez.** Deposito anota en `ya_pedidos` los productos por los que ya
  le avisó a Compras. Sin eso, le avisaría con cada venta.

## Cómo se corre

    python mate\mate.py correr mate\curso\clase_13_equipo.mate

## Lo que tiene que salir

La primera vez:

    Ventas: Anotado: 4 de yerba, total $ 14.000,00.
    Compras: anoté que hay que reponer yerba (quedan 3).
    Ventas: Anotado: 3 de yerba, total $ 10.500,00.
    Ventas: Anotado: 2 de yerba, total $ 7.000,00.
    Ventas: De yerba quedan 1: no llego a 5.

Había 10 de yerba. Con el primer pedido quedan 6; con el segundo quedan 3, que es menos
que el mínimo (5), y Deposito le avisa a Compras. Con el tercero quedan 1 y **no** le
avisa de nuevo. El cuarto pide 5 y no hay: no se vende.

Corrélo de nuevo, con el mismo comando. Deposito se acuerda de que queda 1:

    Ventas: De yerba quedan 1: no llego a 4.
    Ventas: De yerba quedan 1: no llego a 3.
    Ventas: De yerba quedan 1: no llego a 2.
    Ventas: De yerba quedan 1: no llego a 5.

Lo que recuerdan está en `mate\curso\clase_13_equipo.memoria.json` (se abre con el Bloc
de notas). Para volver a empezar con el stock del programa, agregá `--olvidar`:

    python mate\mate.py correr mate\curso\clase_13_equipo.mate --olvidar

### Ver cómo se hablan: `--traza`

    python mate\mate.py correr mate\curso\clase_13_equipo.mate --olvidar --traza

Muestra cada mensaje, con su número. Esto es lo que sale para el segundo pedido (acá los
renglones largos están cortados en dos para que entren):

      ·  3. (programa) pregunta a Ventas: Pedido { charla: "pedido-2", producto: "yerba",
            cantidad: 3 }   (conversación 2)
      ·  4.    Ventas pregunta a Deposito: Reservar { charla: "pedido-2", producto: "yerba",
               cantidad: 3 }
      ·  5.       Deposito pregunta a Compras: Reponer { charla: "pedido-2",
                  producto: "yerba", quedan: 3 }
    Compras: anoté que hay que reponer yerba (quedan 3).
      ·  5.       Compras responde a Deposito: Anotado { charla: "pedido-2" }
      ·  4.    Deposito responde a Ventas: Reserva { charla: "pedido-2", alcanzo: verdadero,
               quedan: 3 }
      ·  3. Ventas responde a (programa): Venta { charla: "pedido-2", respuesta: "Anotado:
            3 de yerba, total $ 10.500,00." }
    Ventas: Anotado: 3 de yerba, total $ 10.500,00.

La sangría muestra quién está esperando a quién: el programa espera a Ventas, Ventas
espera a Deposito y Deposito espera a Compras. Las respuestas vuelven en el orden
inverso. Es el camino que dice el contrato.

### Las pruebas

    python mate\mate.py probar mate\curso\clase_13_equipo.mate

      ✓ un pedido descuenta el stock de Deposito
      ✓ a Compras se le avisa una sola vez
      ✓ el contrato no deja saltearse a Ventas
    3 de 3 pruebas pasaron

(Debajo de cada prueba Mate muestra, con una barra `|` adelante, lo que el programa mostró
mientras la corría.) En una prueba no se usa lo recordado: cada una arranca con el stock
que dice el programa. `mensajes_enviados("Reponer")` da los mensajes de ese tipo que
viajaron en la prueba: así se comprueba que a Compras se le avisó una vez y no tres.

## El error más común

Usar el mismo nombre de `charla` para dos pedidos. Pasa al copiar un renglón y cambiarle
solo la cantidad:

    pedir("pedido-1", "yerba", 4)
    pedir("pedido-1", "yerba", 3)

    clase_13_equipo.mate:99: error: contrato de conversación: charla 'pedido-1' en 'fin' no
    admite pregunta de (programa) a Ventas con 'Pedido'

El contrato lleva la cuenta de cada charla por su nombre. La charla `pedido-1` ya llegó
al estado `fin` con el primer pedido, y en `fin` no hay ningún paso: no admite nada más.
Se arregla poniéndole a cada pedido un nombre distinto (`pedido-2`).

El mismo error, con otro estado, sale si alguien se saltea un paso. Por ejemplo, si el
programa le pide la reserva a Deposito sin pasar por Ventas:

    charla 'pedido-1' en 'llega_el_pedido' no admite pregunta de (programa) a Deposito con
    'Reservar'

El error dice en qué estado estaba la charla, quién le quiso hablar a quién y con qué
mensaje. Con eso se busca el paso que falta en el contrato, o el renglón del programa
que habló fuera de orden.

## Ejercicio

Copiá el programa en tu archivo de práctica y hacé que a Deposito le pueda llegar
mercadería: un mensaje `Ingreso` con el producto y la cantidad, que se suma al stock.
Después de un ingreso, si el producto vuelve a bajar del mínimo, a Compras se le tiene
que avisar otra vez. (Pista: `quitar(ya_pedidos, i.producto)` saca ese producto de la
lista. `Ingreso` no es parte de un pedido: no lleva `charla` ni va en el contrato, y se
manda con `enviar`.)

## Solución

Está en `mate\curso\clase_13_solucion.mate`:

    # Clase 13, ejercicio resuelto: llega mercadería. Deposito la suma a su stock y se
    # olvida de que ya había avisado, así que si el producto vuelve a bajar del mínimo le
    # avisa a Compras otra vez. Lo nuevo: el mensaje Ingreso, su 'al recibir' en Deposito,
    # los dos renglones del final del programa y la última prueba.

    # Todos los mensajes llevan 'charla': el nombre del pedido del que se está hablando.
    mensaje Pedido { charla: texto, producto: texto, cantidad: numero desde 1 } responde Venta
    mensaje Venta { charla: texto, respuesta: texto }
    mensaje Reservar { charla: texto, producto: texto, cantidad: numero } responde Reserva
    mensaje Reserva { charla: texto, alcanzo: logico, quedan: numero desde 0 }
    mensaje Reponer { charla: texto, producto: texto, quedan: numero } responde Anotado
    mensaje Anotado { charla: texto }
    # Ingreso no lleva 'charla' ni está en el contrato de abajo: no es parte de un pedido.
    mensaje Ingreso { producto: texto, cantidad: numero desde 1 }

    # El orden en que se pueden hablar. Cada paso dice: estando en tal estado, quién le
    # habla a quién, con qué mensaje, y a qué estado se pasa. Lo que no está acá, no pasa.
    contrato conversacion {
        id: "charla",
        inicio: "llega_el_pedido",
        pasos: [
            { estado: "llega_el_pedido", evento: "pregunta", origen: "(programa)",
              destino: "Ventas", mensaje: "Pedido", sigue: "atiende_ventas" },
            { estado: "atiende_ventas", evento: "pregunta", origen: "Ventas",
              destino: "Deposito", mensaje: "Reservar", sigue: "reserva_deposito" },
            { estado: "reserva_deposito", evento: "pregunta", origen: "Deposito",
              destino: "Compras", mensaje: "Reponer", sigue: "anota_compras" },
            { estado: "anota_compras", evento: "respuesta", origen: "Compras",
              destino: "Deposito", mensaje: "Anotado", sigue: "reserva_deposito" },
            { estado: "reserva_deposito", evento: "respuesta", origen: "Deposito",
              destino: "Ventas", mensaje: "Reserva", sigue: "contesta_ventas" },
            { estado: "contesta_ventas", evento: "respuesta", origen: "Ventas",
              destino: "(programa)", mensaje: "Venta", sigue: "fin" }
        ]
    }

    agente Ventas {
        estado precios = { yerba: 3500, azucar: 1250.5 }

        al recibir Pedido como p {
            # El stock no es de Ventas: se lo pide a Deposito.
            sea reserva = preguntar Reservar {
                charla: p.charla, producto: p.producto, cantidad: p.cantidad,
            } a Deposito
            si no reserva.alcanzo {
                responder Venta {
                    charla: p.charla,
                    respuesta: "De {p.producto} quedan {reserva.quedan}: no llego a {p.cantidad}.",
                }
            }
            # La cuenta la hace el programa, con todos los centavos.
            sea total = pesos(p.cantidad * precios[p.producto])
            responder Venta {
                charla: p.charla,
                respuesta: "Anotado: {p.cantidad} de {p.producto}, total {total}.",
            }
        }
    }

    agente Deposito {
        # 'recordado': el stock no vuelve a empezar cada vez que se corre el programa.
        estado recordado stock = { yerba: 10, azucar: 6 }
        # Los productos por los que ya le avisó a Compras: avisa una sola vez.
        estado recordado ya_pedidos = []
        # Con menos unidades que estas, pide que repongan.
        estado stock_minimo = 5

        al recibir Reservar como r {
            sea hay = stock[r.producto]
            # No se vende lo que no hay.
            si r.cantidad > hay {
                responder Reserva { charla: r.charla, alcanzo: falso, quedan: hay }
            }
            stock[r.producto] = hay - r.cantidad
            sea quedan = stock[r.producto]
            si quedan < stock_minimo y no tiene(ya_pedidos, r.producto) {
                preguntar Reponer {
                    charla: r.charla, producto: r.producto, quedan: quedan,
                } a Compras
                ya_pedidos = agregar(ya_pedidos, r.producto)
            }
            responder Reserva { charla: r.charla, alcanzo: verdadero, quedan: quedan }
        }

        # Llegó mercadería: se suma, y el aviso a Compras queda libre para la próxima.
        al recibir Ingreso como i {
            stock[i.producto] = stock[i.producto] + i.cantidad
            ya_pedidos = quitar(ya_pedidos, i.producto)
            sea hay = stock[i.producto]
            mostrar("Deposito: entraron {i.cantidad} de {i.producto}, ahora hay {hay}.")
        }
    }

    agente Compras {
        estado recordado a_reponer = []

        al recibir Reponer como r {
            a_reponer = agregar(a_reponer, r.producto)
            mostrar("Compras: anoté que hay que reponer {r.producto} (quedan {r.quedan}).")
            responder Anotado { charla: r.charla }
        }
    }

    # Un pedido de un cliente: va a Ventas, que sabe con quién hablar.
    funcion pedir(charla, producto, cantidad) {
        sea venta = preguntar Pedido {
            charla: charla, producto: producto, cantidad: cantidad,
        } a Ventas
        mostrar("Ventas: {venta.respuesta}")
    }

    pedir("pedido-1", "yerba", 4)
    pedir("pedido-2", "yerba", 3)
    pedir("pedido-3", "yerba", 2)
    pedir("pedido-4", "yerba", 5)
    enviar Ingreso { producto: "yerba", cantidad: 20 } a Deposito
    pedir("pedido-5", "yerba", 5)

    # En las pruebas no se usa lo recordado: cada una arranca con el stock de arriba.
    # mensajes_enviados("Reponer") da los mensajes de ese tipo que viajaron en la prueba.
    prueba "un pedido descuenta el stock de Deposito" {
        pedir("a", "azucar", 2)
        sea reservas = mensajes_enviados("Reservar")
        asegurar largo(reservas) == 1 y reservas[0].de == "Ventas" y reservas[0].a == "Deposito"
        # Quedaban 6: con 2 menos son 4, y por 5 ya no alcanza.
        sea venta = preguntar Pedido { charla: "b", producto: "azucar", cantidad: 5 } a Ventas
        asegurar venta.respuesta == "De azucar quedan 4: no llego a 5."
    }

    prueba "a Compras se le avisa una sola vez" {
        pedir("a", "yerba", 4)
        asegurar largo(mensajes_enviados("Reponer")) == 0
        pedir("b", "yerba", 3)
        pedir("c", "yerba", 2)
        asegurar largo(mensajes_enviados("Reponer")) == 1
    }

    prueba "el contrato no deja saltearse a Ventas" {
        # El programa no le puede pedir una reserva a Deposito: eso es de Ventas.
        asegurar falla {
            preguntar Reservar { charla: "a", producto: "yerba", cantidad: 1 } a Deposito
        }
    }

    prueba "después de un ingreso se puede volver a avisar a Compras" {
        pedir("a", "yerba", 7)
        enviar Ingreso { producto: "yerba", cantidad: 20 } a Deposito
        # Hay 23: con 19 menos quedan 4, otra vez por debajo del mínimo.
        pedir("b", "yerba", 19)
        asegurar largo(mensajes_enviados("Reponer")) == 2
    }

Al correrlo (con `--olvidar`, si ya lo habías corrido), salen dos renglones más al final:

    Ventas: Anotado: 4 de yerba, total $ 14.000,00.
    Compras: anoté que hay que reponer yerba (quedan 3).
    Ventas: Anotado: 3 de yerba, total $ 10.500,00.
    Ventas: Anotado: 2 de yerba, total $ 7.000,00.
    Ventas: De yerba quedan 1: no llego a 5.
    Deposito: entraron 20 de yerba, ahora hay 21.
    Ventas: Anotado: 5 de yerba, total $ 17.500,00.

## Y ahora

Terminaste el curso. Para seguir:

- El equipo completo está en `mate\ejemplos\13_equipo_del_negocio.mate`: los mismos tres
  agentes, pero Ventas charla por teclado, lee tu planilla de precios, entiende pedidos
  como "quiero 12 azucar con envio" (con las funciones del ejemplo 12) y usa la IA, con
  frenos, solo para lo que no es un pedido.
  Un aviso para cuando lo uses: lo que recuerdan los agentes se guarda cuando el
  programa termina. Terminá siempre la charla con chau: si cerrás la ventana con la X,
  se pierde lo anotado en esa charla.
- Para armar ese equipo para tu negocio no hace falta copiar archivos: parado en la
  carpeta donde lo quieras tener, la orden `nuevo equipo mi_negocio` (después de
  `python mate\mate.py`, como las demás) crea el programa, su planilla de muestra y sus
  casos para `ensayar`, y te dice los pasos que siguen. No pisa archivos que ya estén.
- `mate\README.md` lo explica en "Un equipo propio", y en "Contrato de conversación"
  está todo lo que puede decir un contrato.
- `python mate\mate.py ayuda` muestra todas las órdenes, y `python mate\mate.py guia`
  imprime una página con todo el lenguaje para pegarle a un asistente de IA.
