#!/usr/bin/env python3
"""Mate: un lenguaje chico, en español, para escribir código claro y para que
los agentes se hablen entre ellos con mensajes que tienen contrato.

Uso:
    python3 mate.py correr    archivo.mate [--traza] [--traza=conversacion.txt]
                                           [--sin-limite] [--depurar]
    python3 mate.py probar    archivo.mate   (o varios archivos, o una carpeta)
    python3 mate.py verificar archivo.mate
    python3 mate.py guia      (con --guardar=guia.txt la deja en ese archivo)
    python3 mate.py ayuda     (o: ayuda si, ayuda largo... para una palabra o función)
    python3 mate.py consola   (para probar renglones sueltos)
    python3 mate.py corregir  archivo.mate Agente "la lección"   (y: lecciones, bitacora)
    python3 mate.py informe   (los errores de uso anotados; --para-mejorar, --borrar)
    python3 mate.py curso     (las clases para aprender Mate; curso 1 muestra la primera)
    python3 mate.py socio     invitar|aceptar|renovar|quitar|carpeta programa.mate Socio
                              (la clave para hablarse con el programa de otro negocio)
"""

import sys

if sys.version_info < (3, 10):  # antes que nada: con un Python viejo Mate falla de formas raras
    raise SystemExit(
        "Mate necesita Python 3.10 o mas nuevo, y este es Python %d.%d.\n"
        "Instala uno nuevo desde https://www.python.org/downloads/windows/ (el \"Python "
        "install manager\"; tambien esta en la tienda Microsoft Store), cerra esta ventana "
        "y proba de nuevo en una ventana nueva." % sys.version_info[:2])

import ast
import csv
import datetime
import decimal
import difflib
import errno
import hashlib
import hmac
import io
import json
import math
import operator
import os
import re
import secrets
import stat
import time
import types
import unicodedata
from collections import deque

VERSION = "0.8.1"

# El tope para que Mate siga siendo chico (mejora 90): no puede haber más palabras propias
# ni más funciones incluidas que estas. Para agregar una hay que sacar otra, o discutir el
# tope. Y cada agregado lleva su renglón en el README y su prueba (las pruebas lo controlan).
TOPE_DE_PALABRAS = 40
# (En la 0.4 subió de 42 a 45, lo justo para que un agente aprenda: aprender, lecciones y
# consultas_ia. 'recordado' no gasta una palabra: solo vale después de 'estado'.)
# (En la 0.5 subió de 45 a 48, para trabajar con datos de verdad y charlar por teclado:
# leer_tabla, agregar_a_archivo y simular_teclado.)
# (Los frenos para la IA, el tope de gasto y las lecciones propuestas, también de la 0.5,
# no gastaron nada: 'frenos' solo vale dentro de un agente y seguida de una llave, y sus
# reglas (precios, prohibido, largo, reserva...) son nombres comunes en cualquier otro lado.)
TOPE_DE_FUNCIONES = 48

PALABRAS = {
    "sea", "var", "funcion", "devolver", "si", "sino", "mientras", "para", "en",
    "y", "o", "no", "verdadero", "falso", "nada", "mensaje", "agente", "estado",
    "al", "recibir", "como", "enviar", "preguntar", "responder", "fallar",
    "intentar", "falla", "asegurar", "prueba", "remitente", "yo", "crear", "usar",
    "romper", "continuar", "simular",
}

TIPOS_BASE = {"numero", "texto", "logico", "lista", "mapa", "agente", "cualquiera"}

MAX_MENSAJES = 100_000
MAX_PASOS = 10_000_000  # freno para los programas que nunca terminan
MAX_LARGO = 10_000_000  # tope de elementos de una lista o de letras de un texto
MAX_BITS = 14_000  # tope de tamaño de un entero (unas 4.200 cifras)
MAX_LLAMADAS = 3_000  # funciones abiertas a la vez (una que se llama a sí misma, casi siempre)
# Cada llamada de Mate gasta varios niveles de Python. Desde Python 3.12 esos niveles no
# ocupan la pila del sistema (y lo que sí la ocupa tiene su propio freno), así que se
# puede pedir lugar para miles de llamadas sin riesgo de que Python se caiga. En un
# Python más viejo se deja el tope de siempre (unas 180 llamadas; eran unas 120 hasta la
# 0.4, cuando cada llamada de Mate gastaba más niveles de Python).
NIVELES_DE_PYTHON = 30 * MAX_LLAMADAS if sys.version_info >= (3, 12) else 0

ORDENES = ("correr", "probar", "verificar")
# Las órdenes de lo que un agente aprende (0.4): llevan el programa y miran sus archivos
# de memoria y de bitácora, sin correrlo.
ORDENES_DE_MEMORIA = ("bitacora", "corregir", "lecciones", "propuestas", "proponer")
OPCIONES = ("--traza", "--depurar", "--sin-limite", "--version", "--ayuda",
            "--ia-simulada", "--olvidar", "--para-mejorar", "--sin-registro")
# El registro de errores de uso (0.4): lo que Mate anota de los errores que le muestra a
# la persona, para poder mejorar el lenguaje. Queda al lado de mate.py y no sale de ahí.
NOMBRE_DEL_REGISTRO = "errores_de_uso.txt"
MAX_REGISTRO = 500  # renglones que guarda (los últimos)
MINUTOS_SEGUIDO = 30  # el mismo error otra vez dentro de este rato cuenta como "seguido"
# Lo que un agente aprende (0.4). Las lecciones viajan en cada consulta a la IA, y eso se
# paga: por eso tienen tope de cantidad y de largo.
MAX_LECCIONES = 20  # por agente; si se pasa, se olvida la más vieja
LARGO_DE_LECCION = 300  # letras de una lección
MAX_BITACORA = 200  # renglones que guarda la bitácora de errores (los últimos)
TITULO_DE_LECCIONES = ("LECCIONES APRENDIDAS (correcciones que te hicieron antes: tenelas "
                       "siempre en cuenta)")

COMPARADORES = ("==", "!=", "<", "<=", ">", ">=")

# La tabla única de funciones incluidas: nombre -> (cuántos valores lleva como mínimo,
# como máximo, un ejemplo, qué hace). De acá salen el control de la cantidad de valores,
# el ejemplo de los errores, la lista de la guía y la tabla del README.
FUNCIONES = {
    "mostrar": (0, None, 'mostrar("Total:", total)', "escribe en pantalla"),
    "leer": (1, 2, 'leer("¿Cuántos?", "3")',
             "le pide un texto a la persona (en las pruebas da el 2.º valor)"),
    "simular_teclado": (1, 1, 'simular_teclado(["hola", "chau"])',
                        "solo en una prueba: lo que 'teclea' la persona en cada leer()"),
    "texto": (1, 1, "texto(3.5)", 'lo pasa a texto: "3.5"'),
    "numero": (1, 1, 'numero("1.234,50")',
               'lee un número escrito como texto: 1234.5 (y "3.500" es 3500)'),
    "tipo": (1, 1, "tipo(x)", 'dice qué es: "numero", "texto", "lista", "mapa"...'),
    "largo": (1, 1, "largo(lista)", "cuántos elementos tiene (o letras, o claves)"),
    "redondear": (1, 2, "redondear(3.14159, 2)", "3.14 (sin el 2.º valor, sin decimales)"),
    "pesos": (1, 2, "pesos(1234.5)", 'el texto "$ 1.234,50"'),
    "absoluto": (1, 1, "absoluto(-5)", "5: el número sin el signo"),
    "sumar": (1, 1, "sumar([1, 2, 3])", "6"),
    "promedio": (1, 1, "promedio([4, 6])", "5"),
    "minimo": (1, 1, "minimo([3, 1, 2])", "1: el más chico de la lista"),
    "maximo": (1, 1, "maximo([3, 1, 2])", "3: el más grande de la lista"),
    "rango": (1, 3, "rango(1, 10, 3)", "[1, 4, 7]; rango(3) es [0, 1, 2] y rango(2, 5) es [2, 3, 4]"),
    "tiene": (2, 2, "tiene(lista, x)",
              "verdadero si x está en la lista, es clave del mapa o parte del texto"),
    "claves": (1, 1, "claves(mapa)", "la lista de sus claves"),
    "valores": (1, 1, "valores(mapa)", "la lista de sus valores"),
    "obtener": (3, 3, 'obtener(mapa, "clave", 0)',
                "el valor de esa clave o, si el mapa no la tiene, el 3.er valor"),
    "agregar": (2, 2, "agregar(lista, x)", "una lista NUEVA con x al final"),
    "quitar": (2, 2, "quitar(lista, x)",
               "una lista NUEVA sin los que valen x (en un mapa, sin esa clave)"),
    "ordenar": (1, 2, 'ordenar(lista, "precio")',
                "una lista NUEVA ordenada; el campo es opcional: ordenar(lista)"),
    "ultimo": (1, 1, "ultimo(lista)", "el último elemento (o la última letra de un texto)"),
    "porcion": (2, 3, "porcion(lista, 1, 3)",
                "los de las posiciones 1 y 2; sin el 3.er valor, hasta el final"),
    "unir": (2, 2, 'unir(lista, ", ")', "un texto con los elementos separados por coma"),
    "partir": (2, 2, 'partir("a,b", ",")', 'la lista ["a", "b"]'),
    "mayusculas": (1, 1, 'mayusculas("hola")', '"HOLA"'),
    "minusculas": (1, 1, 'minusculas("HOLA")', '"hola"'),
    "recortar": (1, 1, 'recortar("  hola ")', '"hola": sin los espacios de las puntas'),
    "reemplazar": (3, 3, 'reemplazar(t, "a", "b")', "el texto con cada a cambiada por b"),
    "empieza_con": (2, 2, 'empieza_con(t, "Sr.")', "verdadero si el texto empieza así"),
    "termina_con": (2, 2, 'termina_con(t, ".txt")', "verdadero si el texto termina así"),
    "a_json": (1, 1, "a_json(valor)", "el valor escrito como texto JSON"),
    "de_json": (1, 2, 'de_json(texto, "Pedido")',
                "el valor que describe ese JSON; el 2.º valor (opcional) exige ese tipo"),
    "a_mapa": (1, 1, "a_mapa(pedido)",
               "un mapa común con los campos de ese mensaje, para recorrerlos"),
    "detalle_de": (1, 1, "detalle_de(e)",
                   "los datos de un error atajado: un mapa con texto, linea, clase y dato"),
    "hoy": (0, 0, "hoy()", 'la fecha, "21/11/2026" (en las pruebas, siempre "01/01/2025")'),
    "ahora": (0, 0, "ahora()",
              'fecha y hora, "21/11/2026 14:30" (en las pruebas, "01/01/2025 12:00")'),
    "leer_archivo": (1, 1, 'leer_archivo("notas.txt")',
                     "el texto de ese archivo (de la carpeta del programa)"),
    "escribir_archivo": (2, 2, 'escribir_archivo("notas.txt", t)',
                         "guarda el texto t en ese archivo (si ya existía, lo pisa)"),
    "agregar_a_archivo": (2, 2, 'agregar_a_archivo("pedidos.txt", t)',
                          "suma el texto t como un renglón más al final de ese archivo"),
    "leer_tabla": (1, 1, 'leer_tabla("precios.csv")',
                   "la planilla guardada como CSV: una lista con un mapa por fila"),
    "mensajes_enviados": (0, 1, 'mensajes_enviados("Pedido")',
                          "solo en una prueba: los mensajes que se mandaron (o los de ese "
                          "tipo)"),
    "consultar_ia": (2, 3, "consultar_ia(reglas, duda)",
                     "lo que contesta una IA de verdad (Claude), como texto; es pago"),
    "simular_ia": (1, 1, 'simular_ia("Sale $ 100")',
                   "solo en una prueba: lo que contesta la IA desde ahí (o una lista)"),
    "aprender": (1, 2, 'aprender("Hoy no hay pan")',
                 "dentro de un agente: se anota esa lección, y no la olvida al terminar"),
    "lecciones": (0, 1, "lecciones()",
                  "dentro de un agente: la lista de sus lecciones (cada una es un texto)"),
    "consultas_ia": (0, 0, "consultas_ia()",
                     "solo en una prueba: lo que se le consultó a la IA, con las lecciones"),
}


def lista_de_funciones(formato_de_renglon="- {ejemplo:<27} {que}"):
    """Un renglón por función incluida, para la guía y para el README."""
    return "\n".join(formato_de_renglon.format(ejemplo=ejemplo, que=que)
                     for _, _, ejemplo, que in FUNCIONES.values())


# Las funciones incluidas que hacen algo además de devolver un valor: pueden ir solas
# en un renglón. Las demás, sueltas, no sirven de nada y Mate lo avisa.
HACEN_ALGO = ("mostrar", "leer", "escribir_archivo", "simular_ia", "aprender",
              "agregar_a_archivo", "simular_teclado")
# Las funciones que llegaron con la 0.4 y con la 0.5. Un programa de antes puede tener algo
# suyo con esos nombres ('sea lecciones = [...]'): se le deja, y en ese programa el nombre
# es suyo.
SE_PUEDEN_TAPAR = ("aprender", "lecciones", "consultas_ia",
                   "leer_tabla", "agregar_a_archivo", "simular_teclado")

# Palabras de otros lenguajes, o con tilde, y cómo se escriben en Mate. No se aceptan
# como sinónimos: solo sirven para explicar el error.
PISTAS = {
    "print": "mostrar", "imprimir": "mostrar", "if": "si", "else": "sino",
    "while": "mientras", "for": "para", "let": "sea", "const": "sea",
    "true": "verdadero", "false": "falso", "null": "nada", "none": "nada",
    "return": "devolver", "function": "funcion", "def": "funcion",
    "and": "y", "or": "o", "not": "no", "to": "a",
    "break": "romper", "continue": "continuar",
    "función": "funcion", "sinó": "sino", "número": "numero", "lógico": "logico",
    "mayúsculas": "mayusculas", "minúsculas": "minusculas",
}

INCLUIDA = ("'{n}' es una función incluida de Mate; elegí otro nombre "
            "(por ejemplo 'mi_{n}')")
DEMASIADO_GRANDE = "el resultado es demasiado grande para calcularlo"
NO_ASIGNABLE = ("solo se puede asignar a una variable o a una parte de una variable "
                "(x, x.campo, x[0])")
COMO_VAN_LAS_RUTAS = ('Si es una ruta de Windows, escribila con barras comunes '
                      '("C:/datos/lista.txt") o con doble barra ("C:\\\\datos\\\\lista.txt")')
_RUTA_DE_WINDOWS = re.compile(r"(?<!\w)[A-Za-z]:\\(?!\\)")  # C:\ con una sola barra


def parece_ruta(crudo):
    r"""¿Ese texto trae una ruta de Windows con barras simples ("C:\temp\nuevo")? Un
    renglón que termina en dos puntos y sigue abajo ("Opción A:\nyerba") no lo es."""
    for m in _RUTA_DE_WINDOWS.finditer(crudo):
        resto = re.match(r"\S*", crudo[m.end():]).group()
        if resto[:1] not in ("n", "t"):
            return True  # C:\datos: esa barra no es ni un salto ni un espacio largo
        if "\\" in resto or "/" in resto or re.search(r"\.[A-Za-z]\w{0,4}$", resto):
            return True  # C:\temp\nuevo, C:\notas.txt
        if m.start() == 0 and len(resto) > 1:
            return True  # el texto entero es la ruta: "C:\temp"
    return False


ESPERA_OTRA_CANTIDAD = "{n}() espera {espera} argumento(s) y recibió {recibe}"


def espera_otra_cantidad(nombre, minimo, maximo, recibe):
    """El error de una función propia llamada con valores de más o de menos. Si tiene
    parámetros con valor por defecto, dice entre cuántos y cuántos lleva."""
    espera = str(maximo) if minimo == maximo else f"entre {minimo} y {maximo}"
    return ESPERA_OTRA_CANTIDAD.format(n=nombre, espera=espera, recibe=recibe)
DEVOLVER_SUELTO = "'devolver' solo va dentro de una función"
# El buzón entre programas (0.7):
EN_EL_CONTRATO = ("{n} está en el contrato de conversación, que pide 'preguntar', y a otro "
                  "programa no se le puede preguntar: sacalo del contrato o usá otro mensaje")


def no_se_le_pregunta(agente, archivo, responde=None):
    """El error de un 'preguntar' a un agente de otro programa."""
    como = f"'al recibir {responde}' en un agente" if responde else "un 'al recibir'"
    if archivo == SOCIO:
        return (f"{agente} es un socio (otro negocio): no se le puede 'preguntar', porque "
                "su programa corre en otra máquina y en otro momento. Mandale con 'enviar' "
                f"y recibí la contestación con {como} (y nombrala en el 'acepta' de ese "
                "socio)")
    return (f"{agente} es de otro programa ({archivo}): no se le puede 'preguntar', porque "
            "ese programa puede no estar corriendo. Mandale con 'enviar' y recibí la "
            f"contestación con {como}")


def de_otro_programa(agente, archivo, que):
    """El error de lo que no se puede hacer con un agente de otro programa."""
    if archivo == SOCIO:
        return (f"{agente} es un socio (otro negocio): acá solo se le puede mandar un mensaje "
                f"con 'enviar', no {que}. Sus agentes, sus lecciones y su estado los lleva "
                "ese negocio")
    return (f"{agente} es de otro programa ({archivo}): acá solo se le puede mandar un "
            f"mensaje con 'enviar', no {que}. Sus copias, sus lecciones y su estado los "
            "lleva ese programa")
SOLO_EN_PRUEBA = ("mensajes_enviados() solo va dentro de una prueba: es para comprobar "
                  "qué mensajes se mandaron")
SIMULAR_IA_SUELTO = ("simular_ia() solo va dentro de una prueba: fija lo que contesta la IA "
                     "mientras dura esa prueba. Para correr el programa sin la IA de verdad "
                     "está la opción --ia-simulada")
# Las funciones incluidas que solo sirven adentro de una prueba, y lo que se avisa si no.
CONSULTAS_IA_SUELTO = ("consultas_ia() solo va dentro de una prueba: es para comprobar qué se "
                       "le consultó a la IA (y con qué lecciones)")
SIMULAR_TECLADO_SUELTO = ("simular_teclado() solo va dentro de una prueba: fija lo que "
                          "'teclea' la persona en los leer() de esa prueba. Al correr el "
                          "programa de verdad, leer() espera el teclado")
SOLO_EN_PRUEBAS = {"mensajes_enviados": SOLO_EN_PRUEBA, "simular_ia": SIMULAR_IA_SUELTO,
                   "consultas_ia": CONSULTAS_IA_SUELTO,
                   "simular_teclado": SIMULAR_TECLADO_SUELTO}
SOLO_EN_AGENTE = ("{n}() solo va dentro de un agente: cada agente anota y lee sus propias "
                  "lecciones. Para corregirlo desde afuera, sin tocar el programa, está la "
                  "orden 'corregir'; y en una prueba se le dice a cuál: {n}({antes}Mostrador)")
RESPONDER_SUELTO = "'responder' solo va dentro de 'al recibir' (o de una función del agente)"
# El 'al fallar' de un agente se guarda junto a sus 'al recibir', con este nombre (que
# no puede ser el de un mensaje: tiene un espacio y empieza con minúscula).
AL_FALLAR = "al fallar"
SIN_A_QUIEN = ("en 'al fallar' no hay a quién responder: es un aviso, no una pregunta. "
               "Para mandar algo usá 'enviar'")
# Lo que escribir_archivo() no pisa nunca: programas (de Mate, de Python o de Windows).
NO_SE_PISAN = (".mate", ".mate.txt", ".py", ".pyw", ".bat", ".cmd", ".ps1")
# En las pruebas hoy() y ahora() dan siempre esto, para que el resultado no dependa del día.
FECHA_DE_PRUEBA = datetime.datetime(2025, 1, 1, 12, 0)
SIN_MEMORIA = ("el programa se quedó sin memoria: está armando un texto, una lista o un "
               "número demasiado grande")


class ErrorMate(Exception):
    """Un error del programa escrito en Mate. 'clase' dice de qué tipo es:
    'falla' (lo común, se puede atajar con 'intentar'), 'asegurar' (un 'asegurar' que
    no se cumplió: dentro de una prueba no se ataja) o 'limite' (el freno: no se ataja)."""

    def __init__(self, mensaje, linea=None, clase="falla", familia=None, dato=None):
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.linea = linea
        self.clase = clase
        # Para detalle_de(e): de qué familia es el error (no cambia con la redacción) y,
        # si salió de un 'fallar', el valor que le dieron.
        self.familia = familia or ("asegurar" if clase == "asegurar" else "otro")
        self.dato = dato
        self.camino = []  # por dónde se llegó: las funciones y las preguntas de por medio


def anotar_paso(error, paso):
    """Suma un paso al camino del error. Si el camino es muy largo se guardan el principio
    y el final (el origen), que son los que se muestran; se pierde lo del medio."""
    if len(error.camino) >= 40:
        del error.camino[20]
    error.camino.append(paso)


def sin_tildes(texto):
    """El texto en minúsculas y sin tildes, para comparar nombres parecidos."""
    return "".join(c for c in unicodedata.normalize("NFD", texto)
                   if unicodedata.category(c) != "Mn").lower()


def sugerir(nombre, candidatos):
    """Devuelve '' o " ¿Quisiste decir 'x'?" con el candidato más parecido al nombre."""
    candidatos = [c for c in candidatos if isinstance(c, str) and c != nombre]
    plano = sin_tildes(nombre)
    parecidos = [c for c in candidatos if sin_tildes(c) == plano]
    if not parecidos:
        parecidos = difflib.get_close_matches(nombre, candidatos, n=1, cutoff=0.7)
    return f" ¿Quisiste decir '{parecidos[0]}'?" if parecidos else ""


def con_sugerencia(mensaje, nombre, candidatos):
    """El mensaje tal cual o, si hay un nombre parecido, con la sugerencia al final."""
    sugerencia = sugerir(nombre, candidatos)
    return f"{mensaje}.{sugerencia}" if sugerencia else mensaje


def nombre_que_no_existe(nombre, visibles, al_asignar=False):
    """El error de un nombre que no existe, con el parecido si lo hay. 'visibles' son los
    nombres que sí se ven desde ahí. Lo usan la revisión previa y la corrida: dicen lo mismo."""
    mensaje = f"no existe '{nombre}'"
    if va_en_minuscula(nombre):
        return ErrorMate(f"{mensaje}: va en minúscula, '{nombre.lower()}'", familia="nombre")
    # Un nombre propio parecido se sugiere enseguida; una función incluida, solo si
    # es casi igual ('mostar'): 'precio' no es 'porcion'. Y a una función no se le
    # asigna, así que al asignar no se sugiere ninguna.
    propios = [n for n in visibles if n not in FUNCIONES]
    completo = con_pista(mensaje, nombre, propios)
    if completo == mensaje and not al_asignar:
        parecida = difflib.get_close_matches(nombre, list(FUNCIONES), n=1, cutoff=0.8)
        if parecida:
            completo = f"{mensaje}. ¿Quisiste decir '{parecida[0]}'?"
    if al_asignar and completo == mensaje:
        completo += f". Para crear la variable escribí: var {nombre} = ..."
    return ErrorMate(completo, familia="nombre")


def cantidad_equivocada(nombre, cuantos):
    """Si una función incluida no lleva esa cantidad de valores, el texto del error."""
    minimo, maximo, ejemplo, _ = FUNCIONES[nombre]
    if cuantos >= minimo and (maximo is None or cuantos <= maximo):
        return None
    if minimo == maximo:
        lleva = f"{minimo} valor" + ("" if minimo == 1 else "es")
    elif maximo == minimo + 1:
        lleva = f"{minimo} o {maximo} valores"
    else:
        lleva = f"entre {minimo} y {maximo} valores"
    return f"{nombre}() lleva {lleva} y recibió {cuantos}. Por ejemplo: {ejemplo}"


def pista_de(nombre):
    """Si el nombre es una palabra de otro lenguaje (o lleva tilde), cómo va en Mate."""
    forma = PISTAS.get(nombre.lower())
    if not forma:
        return ""
    if " " in forma:
        palabra, resto = forma.split(" ", 1)
        return f"en Mate '{nombre}' sería '{palabra}' {resto}"
    if sin_tildes(nombre) == forma:
        return f"en Mate se escribe '{forma}', sin tilde"
    return f"en Mate '{nombre}' se escribe '{forma}'"


def con_pista(mensaje, nombre, candidatos):
    """Como con_sugerencia, pero primero mira si es una palabra de otro lenguaje."""
    pista = pista_de(nombre)
    return f"{mensaje}: {pista}" if pista else con_sugerencia(mensaje, nombre, candidatos)


def va_en_minuscula(nombre):
    """'Si', 'Mientras': una palabra propia de Mate escrita con mayúscula."""
    return nombre != nombre.lower() and nombre.lower() in PALABRAS


class Linea(int):
    """Un número de línea que además recuerda de qué archivo salió. 'fin' es el renglón
    donde termina un texto de varios renglones (lo demás empieza y termina en el mismo)."""

    def __new__(cls, numero, archivo=None, fin=None):
        obj = super().__new__(cls, numero)
        obj.archivo = archivo
        obj.fin = fin
        return obj


# ───────────────────────────── Lexer ─────────────────────────────

_TOKEN = re.compile(
    r"""
    (?P<ws>[ \t\r\f\v\u00a0\u00ad\u1680\u2000-\u200f\u2028-\u202f\u205f-\u2064\u3000\ufeff]+|\#[^\n]*)
  | (?P<nl>\n)
  | (?P<num>\d+(?:_\d+)*(?:\.\d+)?)
  | (?P<str>"(?:\\.|[^"\\\n])*")
  | (?P<curva>[“”„](?:\\.|[^"“”„\\\n])*[“”„"])
  | (?P<id>[^\W\d]\w*)
  | (?P<op>==|!=|<=|>=|\+=|-=|[-+*/%<>=(){}\[\],.:?])
    """,
    re.X,
)


_PISTAS_DE_CARACTER = {
    '"': "a este texto le falta la comilla de cierre (los textos van en un solo renglón)",
    "'": 'los textos van entre comillas dobles: "así"',
    ";": "en Mate no hace falta el punto y coma: borralo",
    "&": "en Mate 'y' se escribe con la palabra: a y b",
    "|": "en Mate 'o' se escribe con la palabra: a o b",
    "!": "en Mate 'no' se escribe con la palabra: no a",
    "$": "los importes se escriben sin el signo $, solo el número: 3500. El $ lo pone "
         "pesos() al mostrarlo: pesos(3500) da \"$ 3.500,00\" (y dentro de un texto, entre "
         "comillas, el $ sí se puede escribir)",
}
for _c in "“”„":  # comillas dobles curvas (Word, WhatsApp) sin su pareja
    _PISTAS_DE_CARACTER[_c] = _PISTAS_DE_CARACTER['"']
for _c in "‘’":
    _PISTAS_DE_CARACTER[_c] = _PISTAS_DE_CARACTER["'"]


_COMILLAS = '"“”„'
# Lo que no ocupa lugar en la pantalla: pegado en el medio de una palabra, la parte en dos.
_INVISIBLES = "\u00ad\u200b\u200c\u200d\u200e\u200f\u2060\u2061\u2062\u2063\u2064\ufeff"
_LETRA = re.compile(r"\w")


def _fin_de_texto(s, i):
    """s[i] abre un texto: devuelve dónde termina (después de la comilla de cierre), o -1
    si no cierra en ese renglón. Lo que va entre { y } es una cuenta, y adentro puede
    haber otros textos con sus propias comillas: "precio: {precios["yerba"]}"."""
    cierres = '"' if s[i] == '"' else _COMILLAS
    i += 1
    while i < len(s) and s[i] != "\n":
        c = s[i]
        if c == "\\":
            if s[i + 1:i + 2] in ("", "\n"):
                return -1
            i += 2
        elif c in cierres:
            return i + 1
        elif c == "{":
            i = _fin_de_llave(s, i)
            if i < 0:
                return -1
        else:
            i += 1
    return -1


def _fin_de_llave(s, i):
    """s[i] es la { de una cuenta dentro de un texto: devuelve dónde termina (después de
    su }), o -1. Las llaves que estén dentro de otro texto no cuentan."""
    prof = 0
    while i < len(s) and s[i] != "\n":
        c = s[i]
        if c in _COMILLAS:
            i = _fin_de_texto(s, i)
            if i < 0:
                return -1
            continue
        if c == "{":
            prof += 1
        elif c == "}":
            prof -= 1
            if prof == 0:
                return i + 1
        i += 1
    return -1


TRES_COMILLAS = '"""'
SIN_CERRAR_TEXTO = ("a este texto de varios renglones le falta el cierre: termina con tres "
                    'comillas, igual que empieza (""" ... """)')


_BARRA_Y_CIERRE = re.compile(r'(?<!\\)(?:\\\\)*\\"""[ \t\r]*$', re.M)


def comillas_de_mas(fuente, abierto):
    """Para el error de un texto de tres comillas sin cerrar: si en el archivo hay una
    cantidad impar de juegos de tres comillas (tres o más: se pegó un bloque dentro de
    otro), dice cuántos hay y en qué renglones. Con uno solo, o con cantidad par, nada."""
    renglones = []
    for tira in re.finditer(r'(?<!\\)"{3,}', fuente):
        renglones += [1 + fuente.count("\n", 0, tira.start())] * (len(tira.group()) // 3)
    if len(renglones) < 3 or len(renglones) % 2 == 0:
        return ""
    if len(renglones) <= 15:
        lista = ", ".join(str(r) for r in renglones[:-1]) + f" y {renglones[-1]}"
    else:
        lista = ", ".join(str(r) for r in renglones[:15]) + "..."
    return (f'. En este archivo hay {len(renglones)} juegos de tres comillas ("""), en los '
            f"renglones {lista}: es una cantidad impar, y como van de a pares (uno abre y "
            "otro cierra) sobra o falta uno. Suele pasar al pegar un bloque dentro de otro. "
            f"Leyendo de arriba para abajo, el que queda sin pareja es el del renglón "
            f"{int(abierto)}, pero el que sobra o el que falta puede estar más arriba")


class VariosRenglones(str):
    """El contenido de un texto de tres comillas, ya sin la sangría común. 'salto' dice
    cuántos renglones de arriba se le quitaron (para saber en qué renglón cae cada parte)."""
    salto = 0


def _fin_de_texto_largo(s, i):
    """s[i] abre un texto de tres comillas: devuelve dónde termina (después de las tres de
    cierre), o -1 si no cierra. Las comillas de adentro de una cuenta { } no cuentan."""
    i += 3
    while i < len(s):
        c = s[i]
        if c == "\\":
            i += 2
        elif s.startswith(TRES_COMILLAS, i):
            # Una tira de cuatro o más comillas: las de adelante son del texto y cierran
            # las últimas tres ("""Ella dijo "hola"""" termina en "hola").
            while s.startswith('"', i + 3):
                i += 1
            return i + 3
        elif c == "{":
            fin = _fin_de_llave(s, i)
            i = fin if fin > 0 else i + 1
        else:
            i += 1
    return -1


def sin_sangria(crudo):
    """Lo de adentro de un texto de tres comillas, para poder escribirlo prolijo dentro de
    un bloque: sin el renglón de las comillas que abren ni el de las que cierran (si no
    tienen nada más) y sin los espacios que todos los renglones tienen de más a la
    izquierda. Esa sangría común se mide en los renglones escritos y en el del cierre."""
    renglones = crudo.split("\n")
    varios = len(renglones) > 1
    salto = 0
    if varios and not renglones[0].strip():
        renglones.pop(0)
        salto = 1
    sangrias = []
    if varios and renglones and not renglones[-1].strip():
        sangrias.append(renglones.pop())  # el renglón del cierre no es parte del texto
    # (el primer renglón, si está pegado a las comillas que abren, no tiene sangría)
    desde = 0 if salto else 1
    for r in renglones[desde:]:
        if r.strip():
            sangrias.append(r[:len(r) - len(r.lstrip(" \t"))])
    comun = os.path.commonprefix(sangrias) if sangrias else ""
    for i in range(desde, len(renglones)):
        r = renglones[i]
        renglones[i] = r[len(comun):] if r.strip() else ""
    texto = VariosRenglones("\n".join(renglones))
    texto.salto = salto
    return texto


_MILES = re.compile(r"[1-9]\d{0,2}\.\d\d0")  # 1.500, 12.000, 3.250


def revisar_numero(txt, fuente, pos, hondo, linea):
    """Los números que casi seguro quieren decir otra cosa: 1.500, 1.500.000 y 3,5."""
    sin_puntos = txt.replace(".", "").replace("_", "")
    if re.match(r"\.\d", fuente[pos:pos + 2]) and "." in txt:
        raise ErrorMate(
            "un número lleva un solo punto, y es el de los decimales. Los miles no llevan "
            "punto: se escriben todos juntos o con guion bajo (1500000 o 1_500_000). Si no "
            "es una cantidad (un teléfono, una fecha), va entre comillas", linea)
    if _MILES.fullmatch(txt):
        corto = txt.rstrip("0").rstrip(".")
        raise ErrorMate(
            f"en Mate el punto es el de los decimales: {txt} vale {corto}, no {sin_puntos}. "
            f"Si querías decir {sin_puntos}, escribilo sin punto ({sin_puntos}) o con guion "
            f"bajo ({txt.replace('.', '_')}); si era el decimal, escribí {corto}", linea)
    if not hondo and re.match(r",\d+(?![\w.])", fuente[pos:]) and "." not in txt:
        decimales = re.match(r",(\d+)", fuente[pos:]).group(1)
        raise ErrorMate(f"los decimales van con punto, no con coma: {txt}.{decimales}", linea)


def tokenizar(fuente, archivo=None):
    tokens, pos, linea = [], 0, Linea(1, archivo)
    hondo = 0  # paréntesis y corchetes abiertos: ahí adentro una coma separa valores
    while pos < len(fuente):
        if fuente.startswith(TRES_COMILLAS, pos):  # un texto de varios renglones
            fin = _fin_de_texto_largo(fuente, pos)
            if fin < 0:
                # (el renglón culpable suele estar más arriba: ese texto "cerró" recién
                # en las comillas que abrían el siguiente)
                barra = _BARRA_Y_CIERRE.search(fuente)
                if barra:  # el renglón termina en \""": la barra se "come" una comilla
                    raise ErrorMate(
                        'este renglón termina en \\""": la barra hace que la primera comilla '
                        "sea parte del texto, y para el cierre quedan dos en vez de tres. "
                        "Poné las tres comillas del cierre solas, en el renglón de abajo",
                        Linea(1 + fuente.count("\n", 0, barra.start()), archivo))
                error = ErrorMate(SIN_CERRAR_TEXTO + comillas_de_mas(fuente, linea), linea)
                error.texto_abierto = True  # (en la consola: se sigue en el renglón de abajo)
                raise error
            saltos = fuente.count("\n", pos, fin)
            tokens.append(("str", sin_sangria(fuente[pos + 3:fin - 3]),
                           Linea(linea, archivo, fin=linea + saltos)))
            linea = Linea(linea + saltos, archivo)
            pos = fin
            continue
        if fuente[pos] in _COMILLAS:
            fin = _fin_de_texto(fuente, pos)
            if fin > 0:
                tokens.append(("str", fuente[pos + 1:fin - 1], linea))
                pos = fin
                continue
        m = _TOKEN.match(fuente, pos)
        if not m:
            c = fuente[pos]
            if c in _PISTAS_DE_CARACTER:
                raise ErrorMate(_PISTAS_DE_CARACTER[c], linea)
            if not c.isprintable() or unicodedata.category(c)[0] in "CZ":
                antes = fuente[fuente.rfind("\n", 0, pos) + 1:pos].strip()
                lugar = f"después de '{antes[-12:]}'" if antes else "al principio del renglón"
                raise ErrorMate(
                    f"hay un carácter invisible {lugar} (código U+{ord(c):04X}): borrá esa "
                    "parte del renglón y escribila de nuevo", linea)
            raise ErrorMate(f"carácter inesperado: '{c}'", linea)
        pos = m.end()
        clase, txt = m.lastgroup, m.group()
        if clase == "nl":
            linea = Linea(linea + 1, archivo)
        elif clase == "ws":
            if (not txt.startswith("#") and not txt.strip(_INVISIBLES)
                    and _LETRA.fullmatch(fuente[m.start() - 1:m.start()])
                    and _LETRA.fullmatch(fuente[pos:pos + 1])):
                antes = re.search(r"\w+$", fuente[:m.start()]).group()
                raise ErrorMate(
                    f"hay un carácter invisible después de '{antes[-12:]}', en el medio de "
                    f"una palabra (código U+{ord(txt[0]):04X}): borrá esa palabra y escribila "
                    "de nuevo", linea)
        elif clase == "num":
            revisar_numero(txt, fuente, pos, hondo, linea)
            txt = txt.replace("_", "")
            try:
                valor = float(txt) if "." in txt else int(txt)
            except ValueError:  # Python no convierte enteros de miles de cifras
                valor = math.inf
            if type(valor) is float and not math.isfinite(valor):
                raise ErrorMate("ese número es demasiado grande", linea)
            tokens.append(("num", valor, linea))
        elif clase in ("str", "curva"):  # "curva": texto entre comillas “de Word”
            tokens.append(("str", txt[1:-1], linea))
        elif clase == "id":
            tokens.append(("kw" if txt in PALABRAS else "id", txt, linea))
        elif clase == "op":
            if txt == "/" and fuente.startswith("/", pos):
                raise ErrorMate("los comentarios empiezan con #", linea)
            hondo += (txt in "([") - (txt in ")]")
            tokens.append(("op", txt, linea))
    # El final se anota en el último renglón con algo escrito: es el que hay que mirar.
    tokens.append(("eof", None, tokens[-1][2] if tokens else linea))
    return tokens


_CIERRES = {"(": ")", "[": "]", "{": "}"}
_SIGNOS = {"(": "el paréntesis", "[": "el corchete", "{": "la llave"}


def revisar_cierres(tokens, fuente):
    """Si una llave, un paréntesis o un corchete nunca se cierra, dice dónde se abrió
    (y no "falta algo al final del archivo"). Lo demás lo explica el análisis."""
    renglones = fuente.split("\n")

    def texto_de(linea):
        return renglones[linea - 1] if 0 < linea <= len(renglones) else ""

    def sangria(linea):
        t = texto_de(linea)
        return len(t) - len(t.lstrip())

    def sin_cerrar(signo, linea, hasta):
        # El error se anota donde se notó la falta (el final del archivo, o la llave
        # que cerró otra cosa); el mensaje dice dónde se abrió.
        de_que = texto_de(linea).strip().rstrip("{([").strip()
        de_que = f" ({de_que})" if de_que and signo == "{" else ""
        return ErrorMate(f"{_SIGNOS[signo]} que se abrió en la línea {linea}{de_que} "
                         "nunca se cierra", hasta)

    abiertos, sospechoso, previa = [], None, None
    for tipo, valor, linea in tokens:
        if tipo == "op" and valor in _CIERRES:
            abiertos.append((valor, linea))
        elif tipo == "op" and valor in ")]}":
            if not abiertos:
                return  # sobra un cierre: lo dice el análisis
            signo, donde = abiertos[-1]
            if _CIERRES[signo] != valor:
                if signo != "{" and valor == "}":
                    raise sin_cerrar(signo, donde, linea)
                return
            abiertos.pop()
            # Una '}' sola en su renglón y más a la izquierda que el renglón que abrió:
            # casi seguro cierra otra cosa, y la que quedó abierta es esa.
            if (valor == "}" and linea != previa and linea != donde
                    and sangria(linea) < sangria(donde) and sospechoso is None):
                sospechoso = (signo, donde)
        previa = linea
    if abiertos:
        raise sin_cerrar(*(sospechoso or abiertos[-1]), tokens[-1][2])


# ───────────────────────────── Parser ─────────────────────────────


_DEFINEN = ("sea", "var", "funcion", "para", "como", "falla", "mensaje", "agente", "estado")


class EstadoRecordado(tuple):
    """Un 'estado recordado' de un agente: (renglón, nombre, valor inicial), igual que
    cualquier estado, pero se guarda al terminar y se recupera en la próxima corrida."""


class Parser:
    def __init__(self, tokens, en_consola=False):
        self.t = tokens
        self.i = 0
        self.en_consola = en_consola  # ahí un valor suelto vale: la consola lo muestra
        self.en_cabecera = 0  # dentro de la condición de un 'si' o un 'mientras'
        # Para avisar de 'devolver' y 'responder' fuera de lugar antes de correr.
        self.en_funcion = self.en_recibir = self.en_agente = self.en_bucle = 0
        self.en_prueba = 0
        self.en_al_fallar = 0
        self.abiertos = 0  # paréntesis, corchetes o llaves de un valor sin cerrar
        # Los nombres que el programa le pone a algo: si alguien llama 'def' o 'Crear' a
        # una variable o función suya, no se le da la pista de "en Mate se escribe...".
        self.definidos = {
            tk[1] for previo, tk in zip(tokens, tokens[1:])
            if tk[0] == "id" and previo[0] == "kw" and previo[1] in _DEFINEN}

    # utilidades
    def ver(self, d=0):
        return self.t[min(self.i + d, len(self.t) - 1)]

    def es(self, tipo, valor=None, d=0):
        tk = self.ver(d)
        return tk[0] == tipo and (valor is None or tk[1] == valor)

    def tomar(self):
        tk = self.t[self.i]
        self.i += 1
        return tk

    def acepta(self, tipo, valor=None):
        if self.es(tipo, valor):
            return self.tomar()
        return None

    def espera(self, tipo, valor=None, que=None):
        if self.es(tipo, valor):
            return self.tomar()
        tk = self.ver()
        if tipo == "id" and valor is None and tk[0] == "kw":
            raise ErrorMate(
                f"'{tk[1]}' es una palabra propia de Mate y no se puede usar como nombre; "
                f"elegí otro (por ejemplo '{tk[1]}2')", tk[2])
        self.pista_de_palabra(tk)
        visto = "el final del archivo" if tk[0] == "eof" else f"'{tk[1]}'"
        raise ErrorMate(f"esperaba {que or repr(valor)} y encontré {visto}", tk[2])

    def pista_de_palabra(self, tk):
        """'if', 'función', 'Y': una palabra de otro lenguaje, con tilde o con mayúscula
        donde no se la esperaba. Si el programa la definió como nombre suyo, no es eso."""
        if tk[0] != "id" or tk[1] in self.definidos:
            return
        if va_en_minuscula(tk[1]):
            raise ErrorMate(f"'{tk[1]}' va en minúscula: '{tk[1].lower()}'", tk[2])
        if pista_de(tk[1]):
            raise ErrorMate(pista_de(tk[1]), tk[2])

    def pista_de_igual(self):
        """Un '=' suelto donde iba una comparación: x = 5, x => 5, x =< 5."""
        tk = self.ver()
        if tk[:2] != ("op", "="):
            return
        sigue = self.ver(1)
        if sigue[:2] == ("op", ">") and sigue[2] == tk[2]:
            raise ErrorMate("'mayor o igual' se escribe '>=' (primero el '>')", tk[2])
        if sigue[:2] == ("op", "<") and sigue[2] == tk[2]:
            raise ErrorMate("'menor o igual' se escribe '<=' (primero el '<')", tk[2])
        raise ErrorMate("para comparar se usa '==' (un solo '=' es para asignar)", tk[2])

    def nombre_nuevo(self, que="un nombre"):
        """El nombre de una variable, función o parámetro que se está creando."""
        tk = self.espera("id", que=que)
        if tk[1] in incluidas() and tk[1] not in SE_PUEDEN_TAPAR:
            raise ErrorMate(INCLUIDA.format(n=tk[1]), tk[2])
        if tk[1][0].isupper():
            minuscula = tk[1][0].lower() + tk[1][1:]
            if minuscula in PALABRAS or minuscula in incluidas():
                minuscula = "mi_" + minuscula
            raise ErrorMate(
                f"'{tk[1]}' empieza con mayúscula, y esos nombres quedan para los mensajes "
                f"y los agentes. Para lo demás van en minúscula: '{minuscula}'", tk[2])
        self.definidos.add(tk[1])
        return tk[1]

    def nombre_de_campo(self):
        """Un nombre de campo: también puede ser una palabra propia de Mate (estado, para)."""
        if self.es("kw"):
            return self.tomar()[1]
        return self.espera("id", que="un nombre de campo")[1]

    def condicion(self):
        """La condición de un 'si' o un 'mientras', con pistas para los errores comunes."""
        self.en_cabecera += 1
        try:
            e = self.expr()
        finally:
            self.en_cabecera -= 1
        self.pista_de_igual()
        tk = self.ver()
        if tk[0] == "id" and tk[1].lower() in ("entonces", "then"):
            raise ErrorMate(f"en Mate no va '{tk[1]}': después de la condición va "
                            "directamente la llave {", tk[2])
        return e

    def recorrido(self):
        """Lo que recorre un 'para': como en una condición, la llave que sigue es la del bloque."""
        self.en_cabecera += 1
        try:
            return self.expr()
        finally:
            self.en_cabecera -= 1

    def es_comparador(self):
        return self.ver()[0] == "op" and self.ver()[1] in COMPARADORES

    def tras_y_o(self, palabra):
        """Después de 'y' u 'o' no puede venir un comparador: x > 3 y < 10."""
        if self.es_comparador():
            ejemplo = "x > 3 y x < 10" if palabra == "y" else "x < 3 o x > 10"
            raise ErrorMate(
                f"después de '{palabra}' hay que repetir la variable: {ejemplo}", self.ver()[2])

    def linea_previa(self):
        """El renglón donde terminó lo último que se leyó."""
        linea = self.t[self.i - 1][2] if self.i else 0
        return getattr(linea, "fin", None) or linea

    # La regla de los renglones: una sentencia termina donde termina su renglón, salvo
    # que quede abierto un paréntesis, un corchete o una llave, o que el renglón termine
    # en un operador (+, -, y, ==, =...) o en una coma.
    def sigue_con(self, tipo, valores):
        """¿Viene uno de esos operadores a continuar la cuenta?"""
        tk = self.ver()
        if tk[0] != tipo or tk[1] not in valores:
            return False
        if self.abiertos or tk[2] == self.linea_previa():
            return True
        if tk[1] == "-":
            return False  # un '-' al principio de un renglón empieza otra sentencia
        raise ErrorMate(
            f"un renglón no puede empezar con '{tk[1]}': si la cuenta sigue abajo, dejá el "
            f"'{tk[1]}' al final del renglón de arriba", tk[2])

    def en_su_renglon(self, palabra, ln, ejemplo):
        """Lo que acompaña a 'responder', 'fallar', etc. empieza en el mismo renglón."""
        if self.ver()[2] != ln or self.es("eof") or self.es("op", "}"):
            raise ErrorMate(f"a '{palabra}' le falta lo que sigue, en el mismo renglón: "
                            f"{ejemplo}", ln)

    def fin_de_sentencia(self, s, vale_suelto=False):
        """'mostrar "hola"': un nombre suelto y algo más en el mismo renglón. Y un renglón
        que solo calcula (i + 1): se avisa antes de correr, esté donde esté."""
        tk = self.ver()
        if (s[0] == "expr" and s[2][0] == "nombre" and tk[2] == self.linea_previa()
                and tk[0] in ("str", "num", "id")):
            raise ErrorMate(f"a '{s[2][2]}' le faltan los paréntesis: {s[2][2]}(...)", tk[2])
        if s[0] == "expr" and not vale_suelto and s[2][0] not in (
                "llamar", "preguntar", "crear", "nombre"):
            raise renglon_sin_uso(s[2])

    # programa y sentencias
    def programa(self):
        cuerpo = []
        while not self.es("eof"):
            cuerpo.append(self.sentencia(nivel_superior=True))
            self.fin_de_sentencia(cuerpo[-1], self.en_consola)
        return cuerpo

    def bloque(self, vale_suelto=False):
        """vale_suelto: en 'asegurar falla { 10 / 0 }' una cuenta suelta tiene sentido."""
        self.espera("op", "{")
        cuerpo = []
        while not self.es("op", "}"):
            if self.es("eof"):
                raise ErrorMate("falta cerrar un bloque con '}'", self.ver()[2])
            cuerpo.append(self.sentencia())
            self.fin_de_sentencia(cuerpo[-1], vale_suelto)
        self.tomar()
        return cuerpo

    def sentencia(self, nivel_superior=False):
        tipo, val, ln = self.ver()
        if tipo == "id" and val == "contrato" and self.es("id", "conversacion", 1):
            if not nivel_superior:
                raise ErrorMate("'contrato conversacion' va fuera de agentes, funciones y pruebas", ln)
            self.tomar()
            self.tomar()
            return ("contrato_conversacion", ln, self.expr())
        if tipo == "kw":
            if val in ("sea", "var"):
                self.tomar()
                nombre = self.nombre_nuevo()
                self.espera("op", "=")
                return ("sea", ln, nombre, self.expr(), val == "var")
            if val == "funcion":
                return self.funcion()
            if val == "devolver":
                # Dentro de 'al recibir' también vale: termina de atender sin responder.
                if not (self.en_funcion or self.en_recibir):
                    raise ErrorMate(DEVOLVER_SUELTO, ln)
                self.tomar()
                e = None
                if self.ver()[2] == ln and not self.es("op", "}") and not self.es("eof"):
                    e = self.expr()
                return ("devolver", ln, e)
            if val == "si":
                self.tomar()
                if self.es("kw", "no") and self.es("op", "{", 1) and self.ver(1)[2] == ln:
                    raise ErrorMate("en Mate se escribe 'sino', todo junto (no 'si no')", ln)
                ramas, otro = [(self.condicion(), self.bloque())], None
                while self.acepta("kw", "sino"):
                    if self.acepta("kw", "si"):
                        ramas.append((self.condicion(), self.bloque()))
                    else:
                        otro = self.bloque()
                        break
                return ("si", ln, ramas, otro)
            if val == "mientras":
                self.tomar()
                return ("mientras", ln, self.condicion(), self.vuelta())
            if val == "para":
                self.tomar()
                nombre = self.nombre_nuevo()
                if self.acepta("op", ","):  # para posicion, item en lista
                    segundo = self.nombre_nuevo()
                    if segundo == nombre:
                        raise ErrorMate(f"los dos nombres del 'para' no pueden ser iguales "
                                        f"('{nombre}')", ln)
                    self.espera("kw", "en", que="'en' (para posicion, item en lista)")
                    return ("para2", ln, nombre, segundo, self.recorrido(), self.vuelta())
                self.espera("kw", "en", que="'en' (para item en lista)")
                return ("para", ln, nombre, self.recorrido(), self.vuelta())
            if val in ("romper", "continuar"):
                if not self.en_bucle:
                    raise ErrorMate(
                        f"'{val}' solo va dentro de un 'mientras' o de un 'para'", ln)
                self.tomar()
                return (val, ln)
            if val in ("mensaje", "agente", "prueba", "usar") and not nivel_superior:
                raise ErrorMate(f"'{val}' solo puede declararse en el nivel superior", ln)
            if val == "usar":
                self.tomar()
                # usar python "ayudas.py": trae funciones escritas en Python (0.5). 'python'
                # no es una palabra reservada: solo significa algo acá, antes de un texto.
                if self.es("id", "python"):
                    self.tomar()
                    return ("usar_python", ln, self.espera(
                        "str", que="el nombre del archivo de Python entre comillas (usar "
                                   'python "ayudas.py")')[1])
                # usar buzon "deposito.mate": los agentes de ese otro programa quedan como
                # destino de 'enviar' (0.7). 'buzon' tampoco es una palabra reservada.
                if self.es("id", "buzon"):
                    self.tomar()
                    return ("usar_buzon", ln, self.espera(
                        "str", que="el nombre del otro programa entre comillas (usar "
                                   'buzon "deposito.mate")')[1])
                # usar socio Proveedor acepta Cotizacion, SinStock: otro NEGOCIO, en otra
                # máquina (0.8). 'socio' y 'acepta' tampoco son palabras reservadas: solo
                # significan algo acá, y 'socio' solo si lo que sigue no es un texto.
                if self.es("id", "socio") and not self.es("str", d=1):
                    return self.usar_socio(ln)
                return ("usar", ln, self.espera("str", que="el nombre de un archivo")[1])
            if val == "mensaje":
                return self.mensaje()
            if val == "agente":
                return self.agente()
            if val == "prueba":
                self.tomar()
                nombre = self.espera("str", que="el nombre de la prueba")[1]
                self.en_prueba += 1
                try:
                    return ("prueba", ln, nombre, self.bloque())
                finally:
                    self.en_prueba -= 1
            if val == "simular":
                return self.simular()
            if val == "enviar":
                self.tomar()
                self.en_su_renglon(val, ln, "enviar Aviso { ... } a Agente")
                msg = self.expr()
                self.espera("id", "a", que="'a' (enviar Mensaje a Agente)")
                return ("enviar", ln, msg, self.expr())
            if val == "responder":
                if not (self.en_recibir or (self.en_funcion and self.en_agente)):
                    raise ErrorMate(RESPONDER_SUELTO, ln)
                if self.en_al_fallar and not self.en_funcion:
                    raise ErrorMate(SIN_A_QUIEN, ln)
                self.tomar()
                self.en_su_renglon(val, ln, "responder valor")
                return ("responder", ln, self.expr())
            if val == "fallar":
                self.tomar()
                self.en_su_renglon(val, ln, 'fallar "el motivo"')
                return ("fallar", ln, self.expr())
            if val == "intentar":
                self.tomar()
                cuerpo = self.bloque()
                self.espera("kw", "si", que="'si falla'")
                self.espera("kw", "falla", que="'si falla'")
                var = None if self.es("op", "{") else self.nombre_nuevo()
                return ("intentar", ln, cuerpo, var, self.bloque())
            if val == "asegurar":
                self.tomar()
                self.en_su_renglon(val, ln, "asegurar total == 10")
                if self.es("kw", "falla"):  # asegurar falla { ... }: esto tiene que fallar
                    self.tomar()
                    cuerpo = self.bloque(vale_suelto=True)
                    msg = self.expr() if self.acepta("op", ",") else None
                    return ("asegurar_falla", ln, cuerpo, msg)
                cond = self.expr()
                self.pista_de_igual()
                msg = self.expr() if self.acepta("op", ",") else None
                return ("asegurar", ln, cond, msg)
        if (tipo == "id" and va_en_minuscula(val) and val not in self.definidos
                and not (self.es("op", d=1) and self.ver(1)[1] in ("=", ".", "["))):
            raise ErrorMate(f"'{val}' va en minúscula: '{val.lower()}'", ln)
        e = self.expr()
        if self.acepta("op", "="):
            if not self.asignable(e):
                raise ErrorMate(NO_ASIGNABLE, ln)
            return ("asignar", ln, e, self.expr())
        for atajo in ("+=", "-="):  # suma += precio es suma = suma + precio
            if self.acepta("op", atajo):
                if not self.asignable(e):
                    raise ErrorMate(NO_ASIGNABLE, ln)
                return ("asignar", ln, e, ("bin", ln, atajo[0], e, self.expr()))
        return ("expr", ln, e)

    def simular(self):
        """simular Vendedor al recibir Pedido como p { responder ... }: en lo que queda de
        la prueba, ese agente contesta eso."""
        ln = self.tomar()[2]
        if not self.en_prueba or self.en_funcion or self.en_recibir:
            raise ErrorMate("'simular' solo va dentro de una prueba", ln)
        ejemplo = "simular Vendedor al recibir Pedido como p { responder ... }"
        self.en_su_renglon("simular", ln, ejemplo)
        agente = self.postfijo()
        self.espera("kw", "al", que=f"'al recibir' ({ejemplo})")
        self.espera("kw", "recibir", que=f"'al recibir' ({ejemplo})")
        tipo = self.espera("id", que="un tipo de mensaje")[1]
        var = self.nombre_nuevo() if self.acepta("kw", "como") else None
        self.en_recibir += 1
        try:
            cuerpo = self.aparte()
        finally:
            self.en_recibir -= 1
        return ("simular", ln, agente, tipo, var, cuerpo)

    def vuelta(self):
        """El bloque de un 'mientras' o un 'para': adentro valen 'romper' y 'continuar'."""
        self.en_bucle += 1
        try:
            return self.bloque()
        finally:
            self.en_bucle -= 1

    def aparte(self):
        """El bloque de una función o de un 'al recibir': empieza de cero, no está
        dentro del bucle que lo rodee."""
        afuera, self.en_bucle = self.en_bucle, 0
        try:
            return self.bloque()
        finally:
            self.en_bucle = afuera

    def asignable(self, e):
        """Se asigna a una variable o a una parte de una variable: x, x.campo, x[0]."""
        return e[0] == "nombre" or (e[0] in ("indice", "campo") and self.asignable(e[2]))

    def funcion(self):
        ln = self.tomar()[2]
        nombre = self.nombre_nuevo("el nombre de la función")
        self.espera("op", "(")
        # Los parámetros con valor por defecto (tasa = 0.21) van al final y quedan
        # anotados aparte: [(nombre, valor)].
        params, defectos = [], []
        self.abiertos += 1
        while not self.es("op", ")"):
            parametro = self.nombre_nuevo("un parámetro")
            if self.acepta("op", "="):
                defectos.append((parametro, self.expr()))
            elif defectos:
                raise ErrorMate(
                    f"{nombre}(): '{parametro}' no tiene valor por defecto y está después "
                    f"de '{defectos[-1][0]}', que sí tiene. Los parámetros con valor por "
                    f"defecto van al final: {nombre}({parametro}, {defectos[-1][0]} = ...)",
                    self.linea_previa())
            params.append(parametro)
            if not self.acepta("op", ","):
                break
        self.abiertos -= 1
        self.espera("op", ")")
        self.en_funcion += 1
        try:
            cuerpo = self.aparte()
        finally:
            self.en_funcion -= 1
        return ("funcion", ln, nombre, params, cuerpo, defectos)

    def mensaje(self):
        ln = self.tomar()[2]
        nombre = self.nombre_propio("mensaje")
        campos, reglas = [], {}  # reglas: campo -> lo que dice de sus valores
        # La llave también puede venir en el renglón de abajo: un renglón nunca empieza
        # con '{' por otro motivo.
        if self.es("op", "{"):
            self.tomar()
            while not self.es("op", "}"):
                campo = self.nombre_de_campo()
                self.espera("op", ":")
                tipo = self.tipo_de_campo()
                opcional = bool(self.acepta("op", "?"))
                regla = self.regla_de_campo(f"{nombre}.{campo}", tipo, opcional)
                if regla:
                    reglas[campo] = regla
                # Un campo con valor por defecto puede faltar: toma ese valor.
                campos.append((campo, tipo, opcional or "defecto" in regla))
                if not self.acepta("op", ","):
                    break
            self.espera("op", "}")
        responde = None  # mensaje Pedido { ... } responde Cotizacion
        if self.es("id", "responde") and self.ver()[2] == self.linea_previa():
            self.tomar()
            responde = self.tipo_de_campo()
        return ("mensaje", ln, nombre, campos, responde, reglas)

    def regla_de_campo(self, donde, tipo, opcional):
        """Lo que un campo dice de sus valores, después del tipo y en el mismo renglón:
        'desde 1 hasta 100', 'en ["baja", "alta"]' y '= valor por defecto'. Todo escrito
        a mano, así se puede revisar antes de correr. Devuelve un mapa (vacío si no hay)."""
        regla = {}

        def sigue(tipo_de_token, palabra):
            return self.es(tipo_de_token, palabra) and self.ver()[2] == self.linea_previa()

        def escrito(que, ejemplo):
            ln = self.ver()[2]
            if self.es("op", "}") or self.es("op", ",") or self.es("eof"):
                raise ErrorMate(f"{donde}: después de {que} falta el valor, por ejemplo: "
                                f"{ejemplo}", self.linea_previa())
            hay, valor = valor_escrito(self.suma())
            if not hay:
                raise ErrorMate(
                    f"{donde}: después de {que} va un valor escrito a mano (no una cuenta "
                    f"ni una variable), por ejemplo: {ejemplo}", ln)
            return valor

        for palabra in ("desde", "hasta"):
            if sigue("id", palabra):
                ln = self.tomar()[2]
                valor = escrito(f"'{palabra}'", "cantidad: numero desde 1 hasta 100")
                if not es_num(valor):
                    raise ErrorMate(f"{donde}: después de '{palabra}' va un número, y hay "
                                    f"{un(valor)}", ln)
                regla[palabra] = valor
        if sigue("kw", "en"):
            ln = self.tomar()[2]
            ejemplo = 'prioridad: texto en ["baja", "media", "alta"]'
            opciones = escrito("'en'", ejemplo)
            if not isinstance(opciones, list) or not opciones:
                raise ErrorMate(f"{donde}: después de 'en' va la lista de las opciones que "
                                f"valen, por ejemplo: {ejemplo}", ln)
            regla["en"] = opciones
        ln = self.ver()[2]
        if ("desde" in regla or "hasta" in regla) and tipo != "numero":
            raise ErrorMate(f"{donde}: 'desde' y 'hasta' solo van en un campo de tipo "
                            f"numero, y este es de tipo {tipo}", self.linea_previa())
        if "desde" in regla and "hasta" in regla and regla["desde"] > regla["hasta"]:
            raise ErrorMate(
                f"{donde}: 'desde {formato(regla['desde'])}' es más que 'hasta "
                f"{formato(regla['hasta'])}', así que ningún valor podría cumplirlo",
                self.linea_previa())
        if "en" in regla:
            if len(regla) > 1:
                raise ErrorMate(f"{donde}: o va un rango ('desde', 'hasta') o va la lista "
                                "de opciones ('en'), no las dos cosas", self.linea_previa())
            if tipo not in ("numero", "texto"):
                raise ErrorMate(f"{donde}: las opciones con 'en' solo van en un campo de "
                                f"tipo texto o numero, y este es de tipo {tipo}",
                                self.linea_previa())
            for opcion in regla["en"]:
                if nombre_tipo(opcion) != tipo:
                    raise ErrorMate(
                        f"{donde} es de tipo {tipo}, y entre sus opciones está "
                        f"{formato(opcion, False)}, que es {un(opcion)}", self.linea_previa())
        if sigue("op", "="):
            self.tomar()
            valor = escrito("'='", 'prioridad: texto = "media"')
            if opcional:
                raise ErrorMate(
                    f"{donde}: un campo con valor por defecto ya puede faltar (toma ese "
                    "valor): sacale el '?'", ln)
            if not cumple_tipo(valor, tipo):
                raise ErrorMate(f"{donde} es de tipo {tipo}, y su valor por defecto es "
                                f"{un(valor)}: {formato(valor, False)}", ln)
            rota = rompe_regla(donde, valor, regla)
            if rota:
                raise ErrorMate(f"el valor por defecto no cumple su propia regla: {rota}", ln)
            regla["defecto"] = valor
        if self.ver()[2] == self.linea_previa() and (
                self.es("op", "=") or self.es("kw", "en")
                or (self.es("id") and self.ver()[1] in ("desde", "hasta"))):
            raise ErrorMate(f"{donde}: las reglas van en este orden: primero 'desde', "
                            "después 'hasta' (o 'en [...]') y al final '= valor'. Por "
                            "ejemplo: cantidad: numero desde 1 hasta 100 = 1", ln)
        return regla

    def tipo_de_campo(self):
        """numero, texto, Pedido... o 'lista de' cualquiera de esos."""
        tipo = (self.acepta("kw", "agente") or self.espera("id", que="un tipo"))[1]
        if tipo == "lista" and self.es("id", "de"):
            self.tomar()
            return "lista de " + self.tipo_de_campo()
        return tipo

    def nombre_propio(self, que):
        tk = self.espera("id", que=f"el nombre del {que}")
        if not tk[1][0].isupper():
            raise ErrorMate(f"el nombre de un {que} empieza con mayúscula: '{tk[1]}'", tk[2])
        return tk[1]

    def usar_socio(self, ln):
        """usar socio Proveedor [acepta Tipo, Tipo...]: todo en un renglón."""
        self.tomar()
        como = ("'usar socio' lleva el nombre que le das al otro negocio, con mayúscula "
                "adelante, y los mensajes que le aceptás: usar socio Proveedor acepta "
                "Cotizacion, SinStock")
        tk = self.ver()
        if tk[0] != "id" or tk[2] != ln or not tk[1][:1].isupper():
            raise ErrorMate(como, ln)
        nombre = self.tomar()[1]
        tipos = []
        if self.es("id", "acepta") and self.ver()[2] == ln:
            self.tomar()
            while True:
                tk = self.ver()
                if tk[0] != "id" or tk[2] != ln:
                    raise ErrorMate("después de 'acepta' van los mensajes que le recibís a "
                                    f"{nombre}, separados por coma: usar socio {nombre} "
                                    "acepta Cotizacion, SinStock", ln)
                tipo = self.tomar()[1]
                if tipo in tipos:
                    raise ErrorMate(f"'{tipo}' está dos veces en el 'acepta' de {nombre}", ln)
                tipos.append(tipo)
                if not (self.es("op", ",") and self.ver()[2] == ln):
                    break
                self.tomar()
        tk = self.ver()
        if tk[0] != "eof" and tk[2] == ln:
            raise ErrorMate(como, ln)
        return ("usar_socio", ln, nombre, tipos)

    def agente(self):
        ln = self.tomar()[2]
        nombre = self.nombre_propio("agente")
        self.espera("op", "{")
        estados, manejadores, funciones, frenos = [], [], [], []
        self.en_agente += 1
        try:
            self.miembros_de_agente(estados, manejadores, funciones, frenos, nombre)
        finally:
            self.en_agente -= 1
        return ("agente", ln, nombre, estados, manejadores, funciones, frenos)

    def frenos(self, nombre_del_agente, frenos):
        """frenos { precios: lista  reserva: "..." }: las reglas que Mate comprueba sobre
        cada respuesta de consultar_ia() de ese agente (0.5). 'frenos' no es una palabra
        reservada: solo significa esto dentro de un agente y seguida de una llave."""
        ln = self.tomar()[2]
        if frenos:
            raise ErrorMate(f"{nombre_del_agente} ya tiene sus 'frenos' (línea "
                            f"{frenos[0][0]}): van todos juntos, en un solo bloque", ln)
        self.espera("op", "{")
        while not self.acepta("op", "}"):
            tk = self.tomar()
            if tk[0] == "eof":
                raise ErrorMate("a los 'frenos' les falta la llave de cierre }", ln)
            if tk[0] not in ("id", "kw") or not self.es("op", ":"):
                raise ErrorMate(
                    "dentro de 'frenos' va una regla por renglón, con su nombre, dos puntos "
                    f"y el valor (por ejemplo  largo: 400). Las reglas son: {REGLAS_EN_LISTA}",
                    tk[2])
            if tk[1] not in REGLAS_DE_FRENO:
                raise ErrorMate(con_sugerencia(
                    f"'{tk[1]}' no es una regla de 'frenos'", tk[1], REGLAS_DE_FRENO)
                    + f". Las reglas son: {REGLAS_EN_LISTA}", tk[2])
            if any(tk[1] == regla for _, regla, _ in frenos):
                raise ErrorMate(f"la regla '{tk[1]}' está dos veces en los frenos de "
                                f"{nombre_del_agente}: va una sola", tk[2])
            self.tomar()
            if self.es("op", "}") or self.ver()[2] != tk[2]:
                raise ErrorMate(f"a la regla '{tk[1]}' le falta el valor, en el mismo "
                                f"renglón: {REGLAS_DE_FRENO[tk[1]][1]}", tk[2])
            frenos.append((tk[2], tk[1], self.expr()))
            sobra = self.ver()
            if sobra[2] == tk[2] and not self.es("op", ",") and not self.es("op", "}") \
                    and not (sobra[0] == "id" and self.es("op", ":", d=1)):
                # reserva: ""texto""  (comillas de más: el texto se terminó enseguida)
                raise ErrorMate(
                    f"en la regla '{tk[1]}' sobra algo después del valor ('{sobra[1]}'). Va "
                    "una regla por renglón" + (
                        ". Si es un texto, lleva UNA comilla de cada lado: "
                        f"{REGLAS_DE_FRENO['reserva'][1]}"
                        if frenos[-1][2][0] in ("str", "interp") else ""), tk[2])
            self.acepta("op", ",")
        if not frenos:
            raise ErrorMate("estos 'frenos' están vacíos: poneles al menos una regla, por "
                            f"ejemplo  {REGLAS_DE_FRENO['largo'][1]}", ln)

    def miembros_de_agente(self, estados, manejadores, funciones, frenos, nombre):
        while not self.acepta("op", "}"):
            tk = self.ver()
            if tk[:2] == ("id", "frenos") and self.es("op", "{", d=1):
                self.frenos(nombre, frenos)
            elif self.acepta("kw", "estado"):
                # 'estado recordado atendidos = 0': ese dato vuelve en la próxima corrida.
                # 'recordado' no es una palabra reservada: 'estado recordado = 5' sigue
                # siendo un estado que se llama así.
                clase = tuple
                if self.es("id", "recordado") and not self.es("op", "=", d=1):
                    self.tomar()
                    clase = EstadoRecordado
                n = self.nombre_nuevo()
                self.espera("op", "=")
                estados.append(clase((tk[2], n, self.expr())))
            elif self.acepta("kw", "al"):
                if self.acepta("kw", "fallar"):  # al fallar como f { ... }
                    tipo = AL_FALLAR
                    self.en_al_fallar += 1
                else:
                    self.espera("kw", "recibir", que="'recibir' o 'fallar' (al recibir "
                                                     "Pedido como p, al fallar como f)")
                    tipo = self.espera("id", que="un tipo de mensaje")[1]
                var = self.nombre_nuevo() if self.acepta("kw", "como") else None
                self.en_recibir += 1
                try:
                    cuerpo = self.aparte()
                finally:
                    self.en_recibir -= 1
                    self.en_al_fallar = 0
                manejadores.append((tk[2], tipo, var, cuerpo))
            elif self.es("kw", "funcion"):
                funciones.append(self.funcion())
            elif tk[0] == "id" and va_en_minuscula(tk[1]):
                raise ErrorMate(f"'{tk[1]}' va en minúscula: '{tk[1].lower()}'", tk[2])
            else:
                raise ErrorMate(
                    "dentro de un agente solo van 'estado', 'al recibir', 'funcion' y "
                    "'frenos'" if tk[:2] == ("id", "frenos") or self.es("op", ":", d=1)
                    else "dentro de un agente solo van 'estado', 'al recibir' y 'funcion'",
                    tk[2])

    # expresiones
    def expr(self):
        izq = self.expr_y()
        while self.sigue_con("kw", ("o",)):
            ln = self.tomar()[2]
            self.tras_y_o("o")
            izq = ("o", ln, izq, self.expr_y())
        return izq

    def expr_y(self):
        izq = self.expr_no()
        while self.sigue_con("kw", ("y",)):
            ln = self.tomar()[2]
            self.tras_y_o("y")
            izq = ("y", ln, izq, self.expr_no())
        return izq

    def expr_no(self):
        if self.es("kw", "no"):
            ln = self.tomar()[2]
            return ("no", ln, self.expr_no())
        return self.comparacion()

    def comparacion(self):
        izq = self.suma()
        if self.sigue_con("op", COMPARADORES):
            _, op, ln = self.tomar()
            if self.es("op", "=") and self.ver()[2] == ln:
                raise ErrorMate("para comparar se usa '==' (con dos signos '=', no más)", ln)
            if op == "<" and self.es("op", ">") and self.ver()[2] == ln:
                raise ErrorMate("'distinto' se escribe '!='", ln)
            izq = ("bin", ln, op, izq, self.suma())
            if self.es_comparador():
                raise ErrorMate(
                    "las comparaciones no se encadenan: escribí 1 < x y x < 10", self.ver()[2])
        return izq

    def suma(self):
        izq = self.producto()
        while self.sigue_con("op", ("+", "-")):
            _, op, ln = self.tomar()
            izq = ("bin", ln, op, izq, self.producto())
        return izq

    def producto(self):
        izq = self.unario()
        while self.sigue_con("op", ("*", "/", "%")):
            _, op, ln = self.tomar()
            previo = self.t[self.i - 2]
            if op == "%" and previo[0] == "num" and (
                    self.ver()[2] != ln or self.es("eof")
                    or (self.es("op") and self.ver()[1] in (")", "]", "}", ","))):
                n = formato(previo[1])  # sea iva = 21%
                raise ErrorMate(
                    f"en Mate '%' es el resto de una división, no un porcentaje. El {n}% se "
                    f"escribe como una cuenta: {n} / 100 (o {formato(previo[1] / 100)}). Si de "
                    "verdad era el resto, escribí la cuenta entera en este renglón", ln)
            izq = ("bin", ln, op, izq, self.unario())
        return izq

    def unario(self):
        if self.es("op", "-"):
            ln = self.tomar()[2]
            return ("neg", ln, self.unario())
        return self.postfijo()

    def postfijo(self):
        e = self.primario()
        while True:
            tk = self.ver()
            misma = tk[2] == self.linea_previa()
            if misma and self.es("op", "("):
                self.tomar()
                args = self.lista_hasta(")")
                e = ("llamar", tk[2], e, args)
            elif misma and self.es("op", "["):
                self.tomar()
                self.abiertos += 1
                idx = self.expr()
                self.abiertos -= 1
                self.espera("op", "]")
                e = ("indice", tk[2], e, idx)
            elif self.es("op", "."):
                self.tomar()
                e = ("campo", tk[2], e, self.nombre_de_campo())
            else:
                return e

    def lista_hasta(self, cierre):
        items = []
        self.abiertos += 1
        while not self.es("op", cierre):
            items.append(self.expr())
            if not self.acepta("op", ","):
                break
        self.abiertos -= 1
        self.espera("op", cierre)
        return items

    def pares(self, claves_texto):
        pares = []
        self.abiertos += 1
        while not self.es("op", "}"):
            tk = self.tomar()
            if not (tk[0] == "id" or (claves_texto and tk[0] == "str")
                    or (tk[0] == "kw" and self.es("op", ":"))):
                raise ErrorMate("esperaba un nombre de campo", tk[2])
            self.espera("op", ":")
            pares.append((tk[1], self.expr()))
            if not self.acepta("op", ","):
                break
        self.abiertos -= 1
        if pares and not self.es("op", "}"):
            # (0.7.1) Lo más común al cargar un dato con el Bloc de notas: se fue la coma
            # del final del renglón, o quedaron comillas adentro del texto. El error
            # sigue empezando igual; atrás dice qué mirar.
            tk = self.ver()
            self.pista_de_palabra(tk)
            visto = "el final del archivo" if tk[0] == "eof" else f"'{tk[1]}'"
            anterior = self.t[max(self.i - 1, 0)]
            if anterior[2] < tk[2]:
                pista = ("Adentro de las llaves, cada dato termina con una coma: ¿falta la "
                         f"coma al final del renglón de arriba (el {anterior[2]})?")
            else:
                pista = ("Adentro de las llaves, cada dato va con su nombre, dos puntos y su "
                         "valor, y termina con una coma. Si es un texto, va entero entre "
                         "comillas y sin comillas adentro.")
            raise ErrorMate(f"esperaba '}}' y encontré {visto}. {pista}", tk[2])
        self.espera("op", "}")
        return pares

    def primario(self):
        tipo, val, ln = self.tomar()
        if tipo == "num":
            return ("num", ln, val)
        if tipo == "str":
            return self.texto(val, ln)
        if tipo == "kw":
            if val in ("verdadero", "falso"):
                return ("bool", ln, val == "verdadero")
            if val == "nada":
                return ("nada", ln)
            if val in ("remitente", "yo"):
                return (val, ln)
            if val == "crear":
                agente = self.espera("id", que="el nombre de un agente")[1]
                apodo, pares = None, []
                if self.es("id", "llamado"):
                    self.tomar()
                    tk = self.ver()
                    if tk[0] == "id" and tk[1][0].isupper():  # crear Vendedor llamado Sur
                        raise ErrorMate(
                            f"el nombre de la copia es un texto y va entre comillas: "
                            f'crear {agente} llamado "{tk[1]}"', tk[2])
                    apodo = self.suma()  # cualquier texto: "Sucursal " + nombre
                # La llave puede venir en el renglón de abajo, salvo en la condición de un
                # 'si' o un 'mientras': ahí la llave de abajo es la del bloque.
                if self.es("op", "{") and (self.ver()[2] == self.linea_previa() or not (
                        self.abiertos or self.en_cabecera)):
                    self.tomar()  # (la llave puede venir en el renglón de abajo)
                    pares = self.pares(False)
                return ("crear", ln, agente, apodo, pares)
            if val == "preguntar":
                msg = self.expr()
                self.espera("id", "a", que="'a' (preguntar Mensaje a Agente)")
                return ("preguntar", ln, msg, self.postfijo())
        if tipo == "id":
            if val[0].isupper() and self.es("op", "{") and self.ver()[2] == ln:
                self.tomar()
                return ("ctor", ln, val, self.pares(False))
            if pista_de(val) and val not in self.definidos:
                # 'if', 'true', 'función'...: ese nombre no existe, así que el programa
                # iba a fallar igual; mejor explicarlo antes de correr.
                raise ErrorMate(pista_de(val), ln)
            return ("nombre", ln, val)
        if tipo == "op":
            if val == "(":
                self.abiertos += 1
                e = self.expr()
                self.abiertos -= 1
                self.pista_de_igual()
                self.espera("op", ")")
                return e
            if val == "[":
                return ("lista", ln, self.lista_hasta("]"))
            if val == "{":
                return ("mapa", ln, self.pares(True))
        previo = self.t[self.i - 2] if self.i >= 2 else (None, None, None)
        if (tipo, val) == ("op", "=") and previo[0] == "op" and previo[1] in ("*", "/", "%") \
                and previo[2] == ln:  # x *= 2
            raise ErrorMate("los únicos atajos son '+=' y '-='; lo demás se escribe "
                            f"entero: x = x {previo[1]} ...", ln)
        visto = "el final del archivo" if tipo == "eof" else f"'{val}'"
        raise ErrorMate(f"no esperaba {visto} acá", ln)

    def texto(self, crudo, ln):
        """Texto con escapes e interpolación: "Total: {precio * 2}"."""
        partes, actual, i = [], [], 0
        # Si es de varios renglones: cuántos se le sacaron arriba, para saber en qué
        # renglón cae cada cuenta { }.
        salto, inicio = getattr(crudo, "salto", None), ln
        escapes = {"n": "\n", "t": "\t", "\\": "\\", "{": "{", "}": "}"}
        escapes.update((c, c) for c in _COMILLAS)
        if parece_ruta(crudo):
            raise ErrorMate(
                "esto parece una ruta de Windows, y dentro de un texto la barra \\ es "
                "especial (\\n es un salto de renglón y \\t un espacio largo). "
                + COMO_VAN_LAS_RUTAS, ln)
        while i < len(crudo):
            c = crudo[i]
            if c == "\\" and i + 1 < len(crudo):
                if crudo[i + 1] not in escapes:
                    raise ErrorMate(
                        f"dentro de un texto la barra \\ es especial, y \\{crudo[i + 1]} no "
                        "significa nada. Para escribir una barra de verdad va doble: \\\\. "
                        + COMO_VAN_LAS_RUTAS, ln)
                actual.append(escapes[crudo[i + 1]])
                i += 2
            elif c == "{":
                fin = _fin_de_llave(crudo, i)
                if fin < 0:  # no cierra bien: se cuenta a la antigua, para explicar el error
                    fin, prof = i + 1, 1
                    while fin < len(crudo) and prof:
                        prof += {"{": 1, "}": -1}.get(crudo[fin], 0)
                        fin += 1
                    if prof:
                        raise ErrorMate(
                            "falta '}' en el texto (usá \\{ para una llave literal)", ln)
                if actual:
                    partes.append("".join(actual))
                    actual = []
                adentro = crudo[i + 1 : fin - 1]
                if not adentro.strip():
                    raise ErrorMate("dentro del texto: entre { y } falta algo "
                                    "(usá \\{ para una llave literal)", ln)
                if salto is not None:
                    ln = Linea(inicio + salto + crudo.count("\n", 0, i),
                               getattr(inicio, "archivo", None))
                try:
                    sub = Parser([(t, v, ln) for t, v, _ in tokenizar(adentro)])
                    sub.definidos = self.definidos
                    partes.append(sub.expr())
                    sub.espera("eof", que="el fin de la expresión")
                except ErrorMate as e:
                    if "el final del archivo" in e.mensaje:
                        raise ErrorMate(
                            "dentro del texto: lo que está entre { y } quedó a medio escribir "
                            "(usá \\{ para una llave literal)", ln)
                    # (0.7.1) Unas llaves adentro de un texto son una cuenta para Mate.
                    # Si eran parte de lo escrito ("de {8 a 17}"), se dice cómo seguir.
                    raise ErrorMate(
                        f"dentro del texto: {e.mensaje}. (Lo que va entre {{ y }} Mate lo "
                        "toma por una cuenta. Si las llaves eran parte de lo que querías "
                        "escribir, sacalas, o poné \\{ para una llave literal)", ln)
                i = fin
            else:
                actual.append(c)
                i += 1
        if actual:
            partes.append("".join(actual))
        if all(isinstance(p, str) for p in partes):
            return ("str", inicio, "".join(partes))
        return ("interp", inicio, partes)


def renglon_sin_uso(e):
    """El error de un renglón que solo calcula un valor y no hace nada con él."""
    pista = ""
    if e[0] == "neg":
        pista = (". Si era la continuación de la cuenta de arriba, dejá el '-' al "
                 "final de ese renglón")
    return ErrorMate("este renglón calcula un valor y no hace nada con él: guardalo "
                     f"(sea x = ...), mostralo con mostrar(...) o borralo{pista}", e[1],
                     clase="escritura")


def es_de_excel(ruta):
    """¿Ese archivo es una planilla de Excel (.xlsx o .xls) y no un texto?"""
    try:
        with open(ruta, "rb") as f:
            return f.read(4) in (b"PK\x03\x04", b"\xd0\xcf\x11\xe0")
    except OSError:
        return False


def leer_fuente(ruta):
    """Lee un archivo .mate en cualquiera de las codificaciones que usa el Bloc de notas:
    UTF-8 (con o sin marca), "Unicode" (UTF-16) o ANSI (Windows-1252)."""
    if es_archivo_de_clave(ruta):  # (0.8) ni correr, ni verificar, ni 'usar', ni mostrarlo
        raise ErrorMate(NO_SE_LEE_LA_CLAVE.format(n=os.path.basename(str(ruta))),
                        familia="archivo")
    with open(ruta, "rb") as f:
        datos = f.read()
    if datos[:2] in (b"\xff\xfe", b"\xfe\xff"):
        codificaciones = ("utf-16",)
    elif len(datos) >= 4 and datos.count(0) >= len(datos) // 4:
        # "Unicode" sin la marca del principio: una letra de por medio es un cero
        codificaciones = ("utf-16-le" if datos[1::2].count(0) >= datos[0::2].count(0)
                          else "utf-16-be", "utf-8-sig", "cp1252")
    else:
        codificaciones = ("utf-8-sig", "cp1252")
    for codificacion in codificaciones:
        try:
            texto = datos.decode(codificacion)
        except UnicodeError:
            continue
        return texto.replace("\r\n", "\n").replace("\r", "\n")
    raise ErrorMate(f"no pude leer las letras de {ruta}. En el Bloc de notas: "
                    "Archivo > Guardar como > Codificación: UTF-8")


# Lo que a veces queda pegado adentro de un archivo .mate: la pantalla de PowerShell
# ("PS C:\Users\...> ") o el comando con el que se corre Mate.
_PANTALLA_PEGADA = re.compile(r"\s*PS\s+[A-Za-z]:[\\/][^>\n]*>")
_COMANDO_PEGADO = re.compile(
    r"\s*(?:(?:python3?|py)(?:\.exe)?\s+(?:-\S+\s+)*\S*mate\.py\b"
    r"|notepad(?:\.exe)?\s+\S"
    r"|(?:\.[\\/])?mate(?:\.bat)?\s+(?:correr|probar|verificar|consola|guia|ayuda|informe"
    r"|corregir|lecciones|bitacora)\b"
    r"|cd\s+[\w.\\/:~-]+\s*$)", re.I)
PEGADO_EN_EL_ARCHIVO = {
    "pantalla": ('este renglón no es de Mate: es la pantalla de PowerShell (empieza con '
                 '"PS C:\\..."). Parece que se pegó la pantalla adentro del archivo. Abrilo '
                 "con el Bloc de notas, borrá todo lo que no sea del programa y guardá"),
    "comando": ("este renglón no es de Mate: es un comando de PowerShell. Parece que el "
                "comando se pegó adentro del archivo. Abrilo con el Bloc de notas, borrá ese "
                "renglón y guardá: los comandos se escriben en la ventana de PowerShell, no "
                "en el programa"),
}


def pegado_de_powershell(renglon):
    """¿Ese renglón es la pantalla de PowerShell ("pantalla"), un comando ("comando") o
    ninguna de las dos (None)?"""
    if _PANTALLA_PEGADA.match(renglon):
        return "pantalla"
    return "comando" if _COMANDO_PEGADO.match(renglon) else None


def revisar_pegado(fuente, archivo=None):
    """Si el primer renglón escrito del archivo es de PowerShell, lo dice claro."""
    primero = re.match(r"\s*([^\n]*)", fuente)
    que = pegado_de_powershell(primero.group(1))
    if que:
        raise ErrorMate(PEGADO_EN_EL_ARCHIVO[que],
                        Linea(1 + fuente.count("\n", 0, primero.start(1)), archivo))


def analizar(fuente, ruta=None, _vistos=None, en_consola=False, _raiz=None, _ajeno=False):
    """Convierte el texto en un programa, incluyendo lo que traiga con 'usar'.
    _raiz: la carpeta del programa que se corre, cuando esto es un archivo traído.
    _ajeno: es el programa nombrado en un 'usar buzon': solo se lee para saber qué agentes
    y mensajes tiene, así que su Python y sus propios 'usar buzon' no se miran."""
    arriba = _vistos is None and not _ajeno  # el programa que se corre, no uno traído
    vistos = _vistos if _vistos is not None else set()
    if ruta:
        vistos.add(os.path.realpath(ruta))
    carpeta = os.path.dirname(os.path.abspath(ruta)) if ruta else os.getcwd()
    raiz = _raiz or carpeta
    programa = []
    if not en_consola:
        revisar_pegado(fuente, ruta)
    tokens = tokenizar(fuente, ruta)
    revisar_cierres(tokens, fuente)
    for s in Parser(tokens, en_consola).programa():
        if s[0] == "usar_buzon":
            if not _ajeno or _ajeno == "con buzones":
                programa.append(s)  # se resuelve al final, con el programa entero a la vista
            continue
        if s[0] == "usar_python" and _ajeno:
            continue
        if s[0] == "usar_socio":
            if _ajeno:
                continue
            if not arriba:
                raise ErrorMate("'usar socio' va en el programa que se corre, no en un "
                                f"archivo traído con 'usar' ({os.path.basename(ruta or '')}): "
                                "la clave de ese socio es de un programa solo", s[1])
            programa.append(s)
            continue
        if s[0] == "usar_python":
            try:
                nombre, archivo = archivo_de_python(carpeta, s[2])
                # Un .mate traído con 'usar' desde otra carpeta no puede meter Python de
                # allá: el puente solo carga archivos de la carpeta del programa que se corre.
                try:
                    adentro = os.path.normcase(os.path.commonpath(
                        [os.path.realpath(raiz), os.path.realpath(archivo)])) \
                        == os.path.normcase(os.path.realpath(raiz))
                except ValueError:  # en Windows, si está en otro disco
                    adentro = False
                if not adentro:
                    raise ErrorMate(
                        f"'usar python' solo trae archivos de la carpeta del programa que "
                        f"se corre ({raiz}), y este archivo ({os.path.basename(ruta or '')}"
                        f") está en otra carpeta y pide \"{s[2]}\" de allá. Copiá "
                        f"{os.path.basename(archivo)} a la carpeta del programa y escribí el "
                        f"'usar python \"{os.path.basename(archivo)}\"' en el programa",
                        familia="archivo")
            except ErrorMate as e:
                e.linea = e.linea or s[1]
                raise
            if "python:" + os.path.realpath(archivo) not in vistos:  # una vez alcanza
                vistos.add("python:" + os.path.realpath(archivo))
                programa.append(("usar_python", s[1], nombre, archivo))
            continue
        if s[0] != "usar":
            programa.append(s)
            continue
        otra = os.path.join(carpeta, s[2])
        if not os.path.isfile(otra) and os.path.isfile(otra + ".mate"):
            otra += ".mate"  # usar "catalogo" también encuentra catalogo.mate
        try:
            otra = os.path.relpath(otra)
        except ValueError:  # en Windows, si está en otro disco
            pass
        if os.path.realpath(otra) in vistos:
            continue
        try:
            texto = leer_fuente(otra)
        except OSError:
            raise ErrorMate(f"no pude abrir '{s[2]}' (lo busqué en {carpeta})"
                            + pista_de_usar(carpeta, s[2]), s[1])
        except ErrorMate as e:
            e.linea = e.linea or s[1]
            raise
        try:
            traido = analizar(texto, otra, vistos, _raiz=raiz, _ajeno=_ajeno)
        except ErrorMate as e:
            if not getattr(e, "traido", False):  # se dice una vez: quién lo trajo
                desde = f"desde {os.path.basename(ruta)}, línea {s[1]}" if ruta \
                    else f"en la línea {s[1]}"
                e.mensaje += (f" (este archivo, {os.path.basename(otra)}, se trajo con "
                              f"'usar' {desde})")
                e.traido = True
            raise
        # De un archivo usado se toman las declaraciones, no lo que ejecuta ni sus pruebas.
        programa.extend(x for x in traido
                        if x[0] in ("mensaje", "agente", "funcion", "sea", "usar_python",
                                    "usar_buzon"))
    return traer_socios(traer_buzones(programa, ruta, raiz)) if arriba else programa


SOCIO = "otro negocio"  # así figura, donde va el archivo, un socio de 'usar socio' (0.8)


def traer_socios(programa):
    """Resuelve los 'usar socio Proveedor acepta ...' (0.8). Cada socio queda como un
    "agente de otro programa": sirve de destino de 'enviar' y aparece como 'remitente', con
    las mismas prohibiciones (no se le pregunta, no se crea, no se le mira el estado). Se
    le manda al NEGOCIO: de este lado no se sabe qué agentes tiene, así que se le puede
    enviar cualquier mensaje declarado, y el otro decide qué acepta."""
    pedidos = [s for s in programa if s[0] == "usar_socio"]
    if not pedidos:
        return programa
    mensajes = list(dict.fromkeys(s[2] for s in programa if s[0] == "mensaje"))
    ocupados = {s[2]: s[0] for s in programa if s[0] in ("agente", "agente_ajeno", "mensaje")}
    vistos, nuevos = {}, []
    for _, ln, nombre, _tipos in pedidos:
        if nombre in vistos:
            raise ErrorMate(f"el socio {nombre} ya está declarado (línea {int(vistos[nombre])}"
                            "): va un solo 'usar socio' por cada socio, con todo lo que le "
                            "aceptás en ese renglón", ln)
        if nombre in ocupados:
            que = "un mensaje" if ocupados[nombre] == "mensaje" else "un agente"
            raise ErrorMate(f"ya hay {que} {nombre} en este programa: al socio ponele otro "
                            f"nombre (es solo cómo lo llamás vos), por ejemplo: usar socio "
                            f"Socio{nombre}", ln)
        vistos[nombre] = ln
        nuevos.append(("agente_ajeno", ln, nombre, mensajes, SOCIO, None, None, 0))
    return programa + nuevos


def lo_que_declara(ruta, _vistos=None, _junto=None):
    """Lo que se sabe de un programa leyéndolo por arriba, sin ejecutarlo y sin exigirle
    que esté entero: {"buzones": los programas que nombra con 'usar buzon', "agentes": los
    nombres de sus agentes, "crea": si usa 'crear'}. Mira también los archivos que trae con
    'usar' (los que estén y se entiendan). None si el archivo principal no se entiende."""
    arriba = _vistos is None
    vistos = _vistos if _vistos is not None else set()
    junto = _junto if _junto is not None else {"buzones": [], "agentes": set(), "crea": False}
    real = os.path.realpath(ruta)
    if real in vistos or len(vistos) > 200:
        return junto
    vistos.add(real)
    try:
        sentencias = Parser(tokenizar(leer_fuente(ruta), ruta)).programa()
    except (OSError, ErrorMate, RecursionError):
        return None if arriba else junto
    for s in sentencias:
        if s[0] == "usar_buzon":
            junto["buzones"].append(s[2])
        elif s[0] == "agente":
            junto["agentes"].add(s[2])
        elif s[0] == "usar":
            otra = os.path.join(os.path.dirname(os.path.abspath(ruta)), s[2])
            if not os.path.isfile(otra) and os.path.isfile(otra + ".mate"):
                otra += ".mate"
            if os.path.isfile(otra):
                lo_que_declara(otra, vistos, junto)
    junto["crea"] = junto["crea"] or _contiene(sentencias, "crear", 5)
    return junto


def socios_declarados(programa):
    """{socio: [los mensajes que se le aceptan]} de los 'usar socio' del programa."""
    return {s[2]: list(s[3]) for s in programa if s[0] == "usar_socio"}


def nombre_de_programa(ruta):
    """Cómo se llama un programa en el buzón: su archivo sin '.mate' (ni '.mate.txt')."""
    return os.path.basename(archivo_de(ruta, ""))[:-1]


def programa_del_buzon(raiz, escrito):
    """De 'usar buzon "deposito.mate"': la ruta de ese otro programa. Tiene que estar en la
    carpeta del programa que se corre: sin subcarpetas, sin '..' y sin la ruta completa."""
    partes = [p for p in re.split(r"[\\/]", escrito.strip()) if p not in ("", ".")]
    ultimo = partes[-1] if partes else "deposito.mate"
    afuera = ErrorMate(
        f"'usar buzon' nombra otro programa de la misma carpeta ({raiz}), y "
        f'"{escrito}" queda afuera. Los dos programas van en la misma carpeta; escribí '
        f'el nombre sin la ruta: usar buzon "{ultimo}"', familia="archivo")
    if not partes:
        raise ErrorMate("a 'usar buzon' le falta el nombre del otro programa, por ejemplo: "
                        'usar buzon "deposito.mate"')
    if len(partes) > 1 or ".." in partes or escrito.strip()[:1] in ("/", "\\") \
            or re.match(r"[A-Za-z]:", partes[0]):
        raise afuera
    otra = os.path.join(raiz, partes[0])
    if not os.path.isfile(otra) and os.path.isfile(otra + ".mate"):
        otra += ".mate"
    if os.path.isdir(otra):
        raise ErrorMate(f"'{escrito}' es una carpeta, no un programa: 'usar buzon' lleva el "
                        "archivo del otro programa, por ejemplo: usar buzon "
                        '"deposito.mate"', familia="archivo")
    if not os.path.isfile(otra):
        raise ErrorMate(f"no pude abrir '{escrito}', el otro programa de 'usar buzon' (lo "
                        f"busqué en {raiz})" + pista_de_usar(raiz, partes[0]),
                        familia="archivo")
    if os.path.normcase(os.path.dirname(os.path.realpath(otra))) \
            != os.path.normcase(os.path.realpath(raiz)):
        raise afuera  # (un acceso directo que lleva a otra carpeta tampoco vale)
    try:
        return os.path.relpath(otra)
    except ValueError:  # en Windows, si está en otro disco
        return otra


def traer_buzones(programa, ruta, raiz):
    """Resuelve los 'usar buzon "otro.mate"' (0.7). Del otro programa, que se lee pero nunca
    se ejecuta, quedan:
    - sus agentes, como "agentes de otro programa": sirven de destino de 'enviar';
    - los mensajes que cruzan: los de los 'al recibir' de esos agentes, lo que 'responde'
      cada uno y los mensajes que llevan adentro.
    Lo que llega a los dos programas desde el mismo archivo y renglón (un mensajes.mate
    traído con 'usar' por los dos) es lo mismo y vale una vez."""
    pedidos = [s for s in programa if s[0] == "usar_buzon"]
    if not pedidos:
        return programa
    resto = [s for s in programa if s[0] != "usar_buzon"]
    propio = os.path.realpath(ruta) if ruta else None

    def lugar(s):
        archivo = getattr(s[1], "archivo", None) or ruta
        return (os.path.normcase(os.path.realpath(archivo)) if archivo else None, int(s[1]))

    def archivo_de_decl(s):
        return os.path.basename(getattr(s[1], "archivo", None) or ruta or "este programa")

    mensajes = {}
    for s in resto:
        if s[0] == "mensaje":
            mensajes.setdefault(s[2], s)
    agentes = {s[2]: s for s in resto if s[0] == "agente"}
    ajenos, nuevos, traidos = {}, [], set()
    for _, ln, escrito in pedidos:
        try:
            otra = programa_del_buzon(raiz, escrito)
        except ErrorMate as e:
            e.linea = e.linea or ln
            raise
        real, base = os.path.realpath(otra), os.path.basename(otra)
        if real == propio:
            if (getattr(ln, "archivo", None) or ruta) == ruta:
                raise ErrorMate("un programa no se manda mensajes por el buzón a sí mismo: "
                                "sus agentes ya se hablan con 'enviar'", ln)
            continue  # (lo pide un archivo traído con 'usar', que también usan otros)
        if real in traidos:
            continue
        traidos.add(real)
        try:
            suyo = analizar(leer_fuente(otra), otra, _raiz=raiz, _ajeno=True)
        except OSError:
            raise ErrorMate(f"no pude abrir '{escrito}', el otro programa de 'usar buzon'",
                            ln, familia="archivo")
        except ErrorMate as e:
            donde = os.path.basename(getattr(e.linea, "archivo", None) or otra)
            renglon = f", línea {int(e.linea)}" if e.linea else ""
            raise ErrorMate(
                f"el programa de 'usar buzon' tiene un error ({donde}{renglon}): {e.mensaje}. "
                f"Arreglalo ahí: mientras {base} no se entienda, no se sabe qué mensajes "
                "recibe", ln, familia=e.familia)
        sus_mensajes = {}
        for s in suyo:
            if s[0] == "mensaje":
                sus_mensajes.setdefault(s[2], s)
        cruzan = []

        def cruza(tipo):
            tipo = tipo.rsplit(" de ", 1)[-1]
            if tipo in sus_mensajes and tipo not in cruzan:
                cruzan.append(tipo)
                for _, de_campo, _ in sus_mensajes[tipo][3]:
                    cruza(de_campo)
                if sus_mensajes[tipo][4]:
                    cruza(sus_mensajes[tipo][4])

        for s in suyo:
            if s[0] != "agente":
                continue
            tipos = [m[1] for m in s[4] if m[1] != AL_FALLAR]
            for tipo in tipos:
                cruza(tipo)
            if s[2] in agentes and lugar(agentes[s[2]]) == lugar(s):
                continue  # el mismo agente, traído con 'usar' por los dos: acá es local
            if s[2] in ajenos and ajenos[s[2]][6:] == lugar(s):
                continue
            if s[2] in agentes or s[2] in ajenos:
                raise ErrorMate(
                    f"ya hay un agente {s[2]} en este programa: dos agentes no pueden "
                    f"llamarse igual, aunque uno sea de otro programa ({base}). Cambiale el "
                    "nombre a uno", ln)
            ajenos[s[2]] = ("agente_ajeno", ln, s[2], tipos, base,
                            os.path.basename(archivo_de(otra, "buzon"))) + lugar(s)
        for nombre in cruzan:
            suya, local = sus_mensajes[nombre], mensajes.get(nombre)
            if local is None:
                mensajes[nombre] = suya
                nuevos.append(suya)
            elif lugar(local) != lugar(suya) and local[3:] != suya[3:]:
                raise ErrorMate(
                    f"{nombre} está declarado distinto en {archivo_de_decl(local)} (línea "
                    f"{int(local[1])}) y en {archivo_de_decl(suya)} (línea {int(suya[1])}). "
                    "Los dos programas tienen que decir lo mismo: dejalo en un solo archivo "
                    "(mensajes.mate) y traelo con 'usar' desde los dos", ln)
    return resto + nuevos + list(ajenos.values())


def archivo_de_python(carpeta, escrito):
    """De 'usar python "ayudas.py"': (el nombre con que se usa en el programa, la ruta del
    archivo). El archivo tiene que estar en la carpeta del programa (o en una de adentro)
    y llamarse como una variable de Mate, porque después se escribe ayudas.algo(...)."""
    ejemplo = 'usar python "ayudas.py"'
    partes = [p for p in re.split(r"[\\/]", escrito.strip()) if p not in ("", ".")]
    if not partes or not partes[-1].lower().endswith(".py") or len(partes[-1]) < 4:
        raise ErrorMate(f"'usar python' trae un archivo de Python, y su nombre termina en "
                        f'.py; acá dice "{escrito}". Por ejemplo: {ejemplo}')
    afuera = ErrorMate(
        f"'usar python' solo trae archivos de la carpeta del programa ({carpeta}), y "
        f'"{escrito}" queda afuera. Copiá el archivo a esa carpeta y nombralo sin la '
        f'ruta: usar python "{partes[-1]}"', familia="archivo")
    if ".." in partes or escrito.strip()[:1] in ("/", "\\") or re.match(r"[A-Za-z]:", partes[0]):
        raise afuera
    nombre = partes[-1][:-3]
    if not nombre.isidentifier() or nombre != nombre.lower() or nombre in PALABRAS \
            or nombre in FUNCIONES:
        porque = ("es una palabra de Mate" if nombre in PALABRAS else
                  "es una función incluida de Mate" if nombre in FUNCIONES else
                  "tiene mayúsculas, espacios, guiones o empieza con un número")
        raise ErrorMate(
            f"el nombre de un archivo de Python es el que después se escribe en el programa "
            f"(ayudas.py se usa así: ayudas.algo(...)), y '{nombre}' no sirve: {porque}. "
            "Renombrá el archivo con minúsculas, números y guion bajo, por ejemplo "
            "mis_ayudas.py")
    ruta = os.path.join(carpeta, *partes)
    try:  # (un acceso directo que lleva afuera de la carpeta tampoco vale)
        adentro = os.path.normcase(os.path.commonpath(
            [os.path.realpath(carpeta), os.path.realpath(ruta)])) \
            == os.path.normcase(os.path.realpath(carpeta))
    except ValueError:  # en Windows, si está en otro disco
        adentro = False
    if not adentro:
        raise afuera
    if os.path.isfile(ruta):
        return nombre, ruta
    donde = os.path.dirname(ruta)
    pista = ""
    if os.path.isfile(ruta + ".txt"):
        pista = (f". Encontré {partes[-1]}.txt: el Bloc de notas le agregó .txt; renombralo, "
                 "o al guardar elegí Tipo: Todos los archivos")
    elif not os.path.isdir(donde):
        pista = ". Esa carpeta no existe"
    else:
        try:
            hay = sorted(a for a in os.listdir(donde) if a.lower().endswith(".py"))
        except OSError:
            hay = []
        parecido = difflib.get_close_matches(partes[-1], hay, n=1, cutoff=0.75)
        if parecido:
            pista = f". ¿Quisiste decir '{parecido[0]}'?"
        elif hay:
            pista = (". Los archivos .py que hay ahí: " + ", ".join(hay[:10])
                     + (", ..." if len(hay) > 10 else ""))
    raise ErrorMate(f"no encuentro el archivo de Python '{escrito}' (lo busqué en {donde})"
                    + pista, familia="archivo")


def pista_de_usar(carpeta, nombre):
    """Qué pudo haber pasado con un archivo de 'usar' que no aparece."""
    # usar "catalogo" vale por usar "catalogo.mate": las pistas se buscan con las dos formas
    formas = [nombre] if nombre.lower().endswith(".mate") else [nombre + ".mate", nombre]
    for forma in formas:
        if os.path.isfile(os.path.join(carpeta, forma + ".txt")):
            return (f". Encontré {os.path.basename(forma)}.txt: el Bloc de notas le agregó "
                    ".txt; renombralo, o al guardar elegí Tipo: Todos los archivos")
    try:
        ahi = os.path.dirname(os.path.join(carpeta, nombre))
        hay = sorted(a for a in os.listdir(ahi) if a.lower().endswith(".mate")
                     and os.path.isfile(os.path.join(ahi, a)))
    except OSError:
        return ". Esa carpeta no existe"
    for forma in formas:  # igual, salvo las mayúsculas (en Windows da lo mismo; en otras no)
        for a in hay:
            if a.casefold() == os.path.basename(forma).casefold():
                return f". ¿Quisiste decir '{a}'? (escribilo igual, con las mismas mayúsculas)"
    for forma in formas:
        parecido = difflib.get_close_matches(os.path.basename(forma), hay, n=1, cutoff=0.75)
        if parecido:
            return f". ¿Quisiste decir '{parecido[0]}'?"
    if hay:
        return (". Los archivos .mate que hay ahí: " + ", ".join(hay[:10])
                + (", ..." if len(hay) > 10 else ""))
    return ""


# ─────────────────────── Verificación estática ───────────────────────

_LITERALES = {"num": "numero", "str": "texto", "interp": "texto", "bool": "logico",
              "lista": "lista", "mapa": "mapa"}


def _es_nodo(n, clase, largo):
    """¿Es una sentencia o expresión de esa clase? (y no un par 'clave: valor' de un mapa)"""
    return (isinstance(n, tuple) and len(n) == largo and n[0] == clase
            and isinstance(n[1], int))


def _ligaduras(programa):
    """Cuántas veces se le pone cada nombre a algo (variable, parámetro, función...).
    Un nombre puesto una sola vez no puede estar tapado por otro igual."""
    veces = {}

    def anotar(nombre):
        if nombre:
            veces[nombre] = veces.get(nombre, 0) + 1

    def visitar(n):
        if isinstance(n, list):
            for x in n:
                visitar(x)
            return
        if not isinstance(n, tuple):
            return
        if _es_nodo(n, "sea", 5) or _es_nodo(n, "para", 5):
            anotar(n[2])
        elif _es_nodo(n, "para2", 6):
            anotar(n[2])
            anotar(n[3])
        elif _es_nodo(n, "funcion", 6):
            anotar(n[2])
            for parametro in n[3]:
                anotar(parametro)
        elif _es_nodo(n, "usar_python", 4):
            anotar(n[2])
        elif _es_nodo(n, "intentar", 5):
            anotar(n[3])
        elif _es_nodo(n, "simular", 6):
            anotar(n[4])
        elif _es_nodo(n, "agente", 7):
            anotar(n[2])
            for _, nombre, _ in n[3]:
                anotar(nombre)
            for _, _, var, _ in n[4]:
                anotar(var)
        for x in n:
            visitar(x)

    visitar(programa)
    return veces


def _contiene(n, clase, largo):
    """¿Hay adentro alguna sentencia de esa clase?"""
    if isinstance(n, (list, tuple)):
        return _es_nodo(n, clase, largo) or any(_contiene(x, clase, largo) for x in n)
    return False


def _nombra(n, nombres):
    """¿Se usa adentro alguno de esos nombres?"""
    if isinstance(n, (list, tuple)):
        return ((_es_nodo(n, "nombre", 3) and n[2] in nombres)
                or any(_nombra(x, nombres) for x in n))
    return False


def valor_escrito(e):
    """Si eso es un valor escrito a mano (un número, un texto sin cuentas adentro,
    verdadero, falso o una lista de esos), (verdadero, el valor); si no, (falso, nada)."""
    if e[0] in ("num", "str", "bool"):
        return True, e[2]
    if e[0] == "neg" and e[2][0] == "num":
        return True, -e[2][2]
    if e[0] == "lista":
        valores = [valor_escrito(x) for x in e[2]]
        if all(hay for hay, _ in valores):
            return True, [v for _, v in valores]
    return False, None


def cumple_tipo(valor, tipo):
    """¿Ese valor es del tipo que pide el contrato? (numero, texto, lista de numero...)"""
    if tipo == "cualquiera":
        return True
    if tipo.startswith("lista de "):
        return isinstance(valor, list) and all(
            cumple_tipo(x, tipo[len("lista de "):]) for x in valor)
    return nombre_tipo(valor) == tipo


def rompe_regla(donde, valor, regla, _por_el_resto=False):
    """Si ese valor no cumple lo que el mensaje dice de ese campo (mejora 97), el texto del
    error, con el campo, el valor y la regla; si la cumple, None. Es el mismo texto antes
    de correr y al armar el mensaje."""
    if valor is None or not regla:
        return None
    no_puede = f"{donde} no puede valer {formato(valor, False)}"
    if type(valor) is float and math.isfinite(valor) and not _por_el_resto:
        # 0.1 + 0.2 se muestra 0.3 pero guarda 0.30000000000000004: si lo que se ve sí
        # cumple la regla, el error muestra el valor de verdad y dice cómo arreglarlo.
        rota = rompe_regla(donde, valor, regla, True)
        if rota and rompe_regla(donde, float(formato(valor)), regla, True) is None:
            return (rota.replace(no_puede, f"{donde} no puede valer {valor!r}", 1).rstrip(".")
                    + f". Se muestra {formato(valor)}, pero las cuentas con decimales "
                    "dejan un resto minúsculo: redondeá el valor antes de ponerlo en el "
                    "mensaje, por ejemplo redondear(valor, 2)")
        return rota
    if "en" in regla:
        if any(igual(valor, opcion) for opcion in regla["en"]):
            return None
        opciones = ", ".join(formato(opcion, False) for opcion in regla["en"])
        parecida = sugerir(valor, regla["en"]) if isinstance(valor, str) else ""
        return (f"{no_puede}: el mensaje dice que tiene que ser una de estas opciones: "
                f"{opciones}." + parecida.replace("'", '"'))
    desde, hasta = regla.get("desde"), regla.get("hasta")
    if not es_num(valor) or ((desde is None or valor >= desde)
                             and (hasta is None or valor <= hasta)):
        return None
    if desde is not None and hasta is not None:
        return (f"{no_puede}: el mensaje dice 'desde {formato(desde)} hasta "
                f"{formato(hasta)}', así que tiene que estar entre {formato(desde)} y "
                f"{formato(hasta)}")
    if desde is not None:
        return (f"{no_puede}: el mensaje dice 'desde {formato(desde)}', así que tiene que "
                f"ser {formato(desde)} o más")
    return (f"{no_puede}: el mensaje dice 'hasta {formato(hasta)}', así que tiene que ser "
            f"{formato(hasta)} o menos")


def literal_que_no_cumple(e, tipo):
    """Si ese valor escrito a mano seguro no es de ese tipo, dice de qué tipo es (y si el
    problema está adentro de una lista): (tipo, adentro). Si cumple o no se sabe, None."""
    real = e[2] if e[0] == "ctor" else _LITERALES.get(e[0])
    if not real or tipo == "cualquiera":
        return None
    if not tipo.startswith("lista de "):
        return (real, False) if real != tipo else None
    if real != "lista":
        return (real, False)
    for x in e[2]:
        malo = literal_que_no_cumple(x, tipo[len("lista de "):])
        if malo:
            return (malo[0], True)
    return None


def no_es_condicion(e):
    """Si eso, escrito así, seguro no da verdadero ni falso, el error; si no, None."""
    if not isinstance(e, tuple) or not e:
        return None
    principio = "la condición tiene que ser verdadero o falso"
    if e[0] == "nada":
        return f"{principio}, no el valor nada"
    if e[0] in _LITERALES and e[0] != "bool":
        return f"{principio}, no {_LITERALES[e[0]]}"
    if e[0] == "ctor":
        return f"{principio}, no un mensaje {e[2]}"
    if e[0] == "neg" or (e[0] == "bin" and e[2] in "+-*/%"):
        return (f"{principio}, y esto es una cuenta: da un número o un texto. ¿Faltó "
                "compararla con algo (por ejemplo: x + 1 > 0)?")
    return None


def de_donde_viene(previa, actual):
    """' (línea 3)' o, si el nombre vino de otro archivo, ' en lib.mate, que se trajo con
    'usar' (línea 3)': para el error de un nombre que se declara dos veces."""
    if not previa:
        return ""
    otro = getattr(previa, "archivo", None)
    if otro and otro != getattr(actual, "archivo", None):
        return (f": viene de {os.path.basename(otro)}, que se trajo con 'usar' (línea "
                f"{int(previa)} de ese archivo). Elegí otro nombre")
    return f" (línea {int(previa)})"


def repetidos(nombres):
    """Los nombres que aparecen más de una vez, en el orden en que se repiten."""
    vistos, dobles = set(), []
    for nombre in nombres:
        if nombre in vistos and nombre not in dobles:
            dobles.append(nombre)
        vistos.add(nombre)
    return dobles


def revisar_nombres(programa, mensajes, veces, en_consola=False):
    """Los nombres que no existen y las llamadas con la cantidad equivocada de valores,
    antes de correr: [(linea, texto)]. Ante la duda no avisa: solo dice lo que seguro
    fallaría al llegar a ese renglón.

    - Lo declarado en el nivel superior (sea, var, funcion, agente) se ve desde todos
      lados, esté arriba o abajo en el archivo, y venga o no de un 'usar'.
    - Lo de adentro de un bloque se ve en ese bloque y en los de más adentro.
    - Adentro de 'intentar { }' y de 'asegurar falla { }' no se mira: ahí una falla se
      ataja, o es justo lo que se quiere probar.
    - En la consola solo se mira la cantidad de valores de las funciones incluidas: ahí
      lo que falta se puede escribir en el renglón siguiente, y una función se puede rehacer."""
    errores, avisados = [], set()
    arriba = set(FUNCIONES) | {s[2] for s in programa
                               if s[0] in ("sea", "funcion", "agente", "usar_python",
                                           "agente_ajeno")}
    tapadas = set(SE_PUEDEN_TAPAR) & set(_ligaduras(programa))  # nombres que el programa usa
    # Las funciones propias que seguro son esa función donde se las nombre: las de un
    # nombre que en todo el programa se le pone a una sola cosa.
    cuantos_lleva = {}

    def juntar_funciones(n):
        if isinstance(n, list):
            for x in n:
                juntar_funciones(x)
        elif isinstance(n, tuple):
            if _es_nodo(n, "funcion", 6) and isinstance(n[3], list) and veces.get(n[2]) == 1:
                cuantos_lleva[n[2]] = (len(n[3]) - len(n[5]), len(n[3]))
            for x in n:
                juntar_funciones(x)

    if not en_consola:
        juntar_funciones(programa)

    def falta(nombre, linea, alcance, al_asignar=False, archivo=None):
        if en_consola:
            return
        if nombre in mensajes or nombre in avisados or any(nombre in a for a in alcance):
            return  # (un mensaje sin llaves ya tiene su propio aviso)
        avisados.add(nombre)  # una vez por nombre: lo demás sería repetir el mismo error
        if archivo:  # leer_tabla(precios.csv): el nombre de un archivo, sin las comillas
            errores.append((linea, (
                f"no existe '{nombre}'. Si {archivo} es el nombre de un archivo, va entre "
                f'comillas: "{archivo}"')))
            return
        visibles = [n for a in reversed(alcance) for n in sorted(a)]
        errores.append((linea, nombre_que_no_existe(nombre, visibles, al_asignar).mensaje))

    def bloque(cuerpo, alcance):
        propios = {s[2] for s in cuerpo if s[0] in ("sea", "funcion")}
        alcance = alcance + [propios]
        for s in cuerpo:
            sentencia(s, alcance)

    def funcion(s, alcance):
        # Un valor por defecto ve lo de afuera y los parámetros que están antes que él.
        for parametro, e in s[5]:
            valor(e, alcance + [set(s[3][:s[3].index(parametro)])])
        bloque(s[4], alcance + [set(s[3])])

    def sentencia(s, alcance):
        clase = s[0]
        if clase == "sea":
            valor(s[3], alcance)
        elif clase == "funcion":
            funcion(s, alcance)
        elif clase in ("devolver", "responder", "fallar", "expr"):
            if s[2] is not None:
                valor(s[2], alcance)
        elif clase == "si":
            for condicion, cuerpo in s[2]:
                valor(condicion, alcance)
                bloque(cuerpo, alcance)
            if s[3] is not None:
                bloque(s[3], alcance)
        elif clase == "mientras":
            valor(s[2], alcance)
            bloque(s[3], alcance)
        elif clase == "para":
            valor(s[3], alcance)
            bloque(s[4], alcance + [{s[2]}])
        elif clase == "para2":
            valor(s[4], alcance)
            bloque(s[5], alcance + [{s[2], s[3]}])
        elif clase == "agente":
            adentro = alcance + [{e[1] for e in s[3]} | {f[2] for f in s[5]}]
            for _, _, inicial in s[3]:
                valor(inicial, adentro)
            for _, _, var, cuerpo in s[4]:
                bloque(cuerpo, adentro + [{var} if var else set()])
            for f in s[5]:
                funcion(f, adentro)
            for _, _, regla in s[6]:  # los frenos ven el estado y las funciones del agente
                valor(regla, adentro)
        elif clase == "prueba":
            bloque(s[3], alcance)
        elif clase == "simular":
            # Lo simulado ve lo de la prueba (y no el estado del agente).
            valor(s[2], alcance)
            bloque(s[5], alcance + [{s[4]} if s[4] else set()])
        elif clase == "enviar":
            valor(s[2], alcance)
            valor(s[3], alcance)
        elif clase == "intentar":
            # (lo de adentro del 'intentar' no se mira; lo de 'si falla', sí)
            bloque(s[4], alcance + [{s[3]} if s[3] else set()])
        elif clase == "asegurar":
            valor(s[2], alcance)
            if s[3] is not None:
                valor(s[3], alcance)
        elif clase == "asegurar_falla":
            if s[3] is not None:
                valor(s[3], alcance)
        elif clase == "asignar":
            raiz = s[2]
            while raiz[0] in ("indice", "campo"):
                raiz = raiz[2]
            if raiz[0] == "nombre":
                falta(raiz[2], raiz[1], alcance, al_asignar=True)
            valor(s[2], alcance)
            valor(s[3], alcance)

    def valor(e, alcance):
        clase = e[0]
        if clase == "nombre":
            falta(e[2], e[1], alcance)
        elif clase == "interp":
            for parte in e[2]:
                if not isinstance(parte, str):
                    valor(parte, alcance)
        elif clase == "lista":
            for x in e[2]:
                valor(x, alcance)
        elif clase == "mapa":
            for _, x in e[2]:
                valor(x, alcance)
        elif clase == "ctor":
            for _, x in e[3]:
                valor(x, alcance)
        elif clase == "crear":
            if e[3] is not None:
                valor(e[3], alcance)
            for _, x in e[4]:
                valor(x, alcance)
        elif clase in ("y", "o", "indice", "preguntar"):
            valor(e[2], alcance)
            valor(e[3], alcance)
        elif clase == "campo" and e[2][0] == "nombre" and str(e[3]).lower() in (
                "csv", "txt", "json", "mate", "py", "xlsx", "xls", "md"):
            falta(e[2][2], e[2][1], alcance, archivo=f"{e[2][2]}.{e[3]}")
        elif clase in ("no", "neg", "campo"):
            valor(e[2], alcance)
        elif clase == "bin":
            valor(e[3], alcance)
            valor(e[4], alcance)
        elif clase == "llamar":
            valor(e[2], alcance)
            for x in e[3]:
                valor(x, alcance)
            if e[2][0] != "nombre" or not any(e[2][2] in a for a in alcance):
                return
            nombre, texto = e[2][2], None
            if nombre in FUNCIONES and nombre not in tapadas:  # (las demás no se tapan)
                texto = cantidad_equivocada(nombre, len(e[3]))
            elif nombre in cuantos_lleva and not (
                    cuantos_lleva[nombre][0] <= len(e[3]) <= cuantos_lleva[nombre][1]):
                texto = espera_otra_cantidad(nombre, *cuantos_lleva[nombre], len(e[3]))
            if texto:
                errores.append((e[1], texto))

    for s in programa:
        sentencia(s, [arriba])
    return errores


def revisar_python(programa, veces):
    """Lo que se puede saber de un archivo traído con 'usar python' SIN ejecutarlo: si
    Python lo puede leer, y si tiene las funciones que el programa le pide. Devuelve
    [(linea, texto)]. (Que el archivo exista ya lo controló 'analizar'.)"""
    errores, tienen = [], {}
    for s in programa:
        if s[0] != "usar_python":
            continue
        archivo = os.path.basename(s[3])
        try:
            arbol = ast.parse(leer_fuente(s[3]))
        except SyntaxError as e:
            donde = f" en su línea {e.lineno}" if e.lineno else ""
            errores.append((s[1], f"{archivo} está mal escrito{donde} y Python no lo pudo "
                                  f"leer. Python dice: {recortado(e.msg or 'SyntaxError', 300)}"))
            continue
        except (OSError, ValueError, ErrorMate, RecursionError, MemoryError):
            continue  # no se pudo mirar: si hay un problema, lo dirá al correr
        # Los nombres que el archivo define arriba de todo (con 'def' o con '='): si el
        # programa pide otro, seguro que no está. No se entra en las funciones ni clases.
        nombres, pendientes = set(), list(arbol.body)
        while pendientes:
            n = pendientes.pop()
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                nombres.add(n.name)
            elif isinstance(n, ast.ClassDef):
                pass
            else:
                nombres.update(x.id for x in ast.walk(n)
                               if isinstance(x, ast.Name) and isinstance(x.ctx, ast.Store))
                pendientes += [x for x in ast.iter_child_nodes(n) if isinstance(x, ast.stmt)]
        if veces.get(s[2]) == 1:  # (si otra cosa se llama igual, no se sabe cuál es cuál)
            tienen[s[2]] = (archivo, {n for n in nombres if not n.startswith("_")})
    avisados = set()

    def visitar(n):
        if isinstance(n, (list, tuple)):
            if (_es_nodo(n, "campo", 4) and _es_nodo(n[2], "nombre", 3) and n[2][2] in tienen
                    and (n[2][2], n[3]) not in avisados):
                archivo, nombres = tienen[n[2][2]]
                if n[3] not in nombres:
                    avisados.add((n[2][2], n[3]))
                    errores.append((n[1], no_esta(
                        f"{archivo} no tiene una función '{n[3]}'", n[3], sorted(nombres))
                        if nombres else
                        f"{archivo} no tiene ninguna función para usar desde Mate: se ven "
                        "las que están escritas ahí con 'def' y no empiezan con guion bajo"))
            # (como con los nombres: adentro de 'intentar' y de 'asegurar falla' no se mira)
            if _es_nodo(n, "intentar", 5):
                n = n[4]
            elif _es_nodo(n, "asegurar_falla", 4):
                return
            for x in n:
                visitar(x)

    if tienen:
        visitar(programa)
    return errores


def verificar(programa, en_consola=False):
    """Revisa el programa antes de correr: los contratos de los mensajes, los nombres que
    no existen y lo demás que se puede saber sin ejecutarlo. Devuelve [(linea, texto)].
    en_consola: ahí no se avisa de los nombres que faltan (ver revisar_nombres)."""
    errores = []
    mensajes, agentes, estados = {}, {}, {}
    declarados = {}  # la declaración completa de cada agente
    ajenos = {}  # los agentes de otro programa ('usar buzon'): nombre -> su archivo
    veces = _ligaduras(programa)
    errores += revisar_python(programa, veces)
    # Funciones que seguro son funciones donde se las nombre: las incluidas y las del
    # nivel superior cuyo nombre no se repite.
    funciones = (set(incluidas()) - set(veces)) | {
        s[2] for s in programa if s[0] == "funcion" and veces.get(s[2]) == 1}
    copias = {}  # 'sea v = crear V': la variable v es una copia de V

    def buscar_copias(n):
        if isinstance(n, list):
            for x in n:
                buscar_copias(x)
        elif isinstance(n, tuple):
            if (_es_nodo(n, "sea", 5) and not n[4] and veces.get(n[2]) == 1
                    and _es_nodo(n[3], "crear", 5)):
                copias[n[2]] = n[3][2]
            for x in n:
                buscar_copias(x)

    buscar_copias(programa)
    pruebas = {}
    for s in programa:
        if s[0] == "prueba":
            if s[2] in pruebas:
                errores.append((s[1], f'ya hay una prueba llamada "{s[2]}" (línea '
                                      f"{pruebas[s[2]]}): poneles nombres distintos, así se "
                                      "sabe cuál es la que falla"))
            pruebas.setdefault(s[2], s[1])
    def ya_declarado(s):
        previo = mensajes.get(s[2]) or declarados[s[2]]
        return f"'{s[2]}' ya está declarado" + de_donde_viene(previo[1], s[1])

    for s in programa:
        if s[0] == "mensaje":
            if s[2] in mensajes or s[2] in agentes:
                errores.append((s[1], ya_declarado(s)))
            mensajes[s[2]] = s
        elif s[0] == "agente":
            if s[2] in mensajes or s[2] in agentes:
                errores.append((s[1], ya_declarado(s)))
            agentes[s[2]] = [m[1] for m in s[4]]
            estados[s[2]] = {e[1]: e[2] for e in s[3]}
            declarados[s[2]] = s
        elif s[0] == "agente_ajeno":
            if s[2] in mensajes:
                errores.append((s[1], f"'{s[2]}' es un mensaje de este programa y también "
                                      f"un agente de {s[4]}: cambiale el nombre a uno"))
            agentes[s[2]] = list(s[3])
            estados[s[2]] = {}
            ajenos[s[2]] = s[4]
    for s in programa:  # (0.8) lo que se le acepta a cada socio
        if s[0] != "usar_socio":
            continue
        for tipo in s[3]:
            reciben = [a for a, d in declarados.items() if any(m[1] == tipo for m in d[4])]
            if tipo not in mensajes:
                errores.append((s[1], con_sugerencia(
                    f"'{tipo}' está en el 'acepta' de {s[2]} y no es un mensaje declarado "
                    "en este programa", tipo, mensajes)))
            elif not reciben:
                errores.append((s[1], (
                    f"'{tipo}' está en el 'acepta' de {s[2]} y ningún agente tiene 'al "
                    f"recibir {tipo}': lo que manda un socio se le entrega al único agente "
                    "de este programa que recibe ese mensaje")))
            elif len(reciben) > 1:
                errores.append((s[1], (
                    f"'{tipo}' está en el 'acepta' de {s[2]} y lo reciben "
                    f"{' y '.join(reciben)}: lo que manda un socio se le entrega a un solo "
                    f"agente. Dejá un solo 'al recibir {tipo}' (ese agente se lo puede "
                    "pasar a los demás)")))
    try:  # (los mensajes del contrato de conversación no pueden ir a otro programa)
        del_contrato = ContratoConversacion.del_programa(
            programa, {nombre: s[3] for nombre, s in mensajes.items()}, agentes)
        del_contrato = del_contrato.tipos if del_contrato else ()
    except ErrorMate:
        del_contrato = ()  # (ese error se avisa más abajo)

    def respuestas_de(agente, tipo, cuerpo):
        """Los 'responder' con un valor escrito a mano que no cumple el contrato."""
        esperado = mensajes[tipo][4] if tipo in mensajes else None

        def mirar(n):
            if isinstance(n, list):
                for x in n:
                    mirar(x)
            elif isinstance(n, tuple):
                if _es_nodo(n, "responder", 3) and isinstance(n[2], tuple):
                    malo = literal_que_no_cumple(n[2], esperado)
                    if malo:
                        que = f"una lista con un valor de tipo {malo[0]}" if malo[1] else malo[0]
                        errores.append((n[1], (
                            f"{agente} responde {que} a '{tipo}', y el contrato dice "
                            f"que a {tipo} se le responde {esperado}")))
                for x in n:
                    mirar(x)

        if esperado:
            mirar(cuerpo)

    for s in mensajes.values():
        vistos = set()
        for campo, tipo, _ in s[3]:
            if campo in vistos:
                errores.append((s[1], f"{s[2]}: el campo '{campo}' está repetido"))
            vistos.add(campo)
            tipo = tipo.rsplit(" de ", 1)[-1]  # de 'lista de Pedido' importa 'Pedido'
            if tipo not in TIPOS_BASE and tipo not in mensajes:
                errores.append((s[1], con_pista(
                    f"{s[2]}.{campo}: no existe el tipo '{tipo}'", tipo,
                    sorted(TIPOS_BASE) + list(mensajes))))
        if s[4]:
            tipo = s[4].rsplit(" de ", 1)[-1]
            if tipo not in TIPOS_BASE and tipo not in mensajes:
                errores.append((s[1], con_pista(
                    f"{s[2]} responde '{tipo}', que no es un tipo ni un mensaje declarado",
                    tipo, sorted(TIPOS_BASE) + list(mensajes))))

    for s in programa:
        if s[0] == "agente":
            for k in repetidos(e[1] for e in s[3]):
                errores.append((next(e[0] for e in reversed(s[3]) if e[1] == k),
                                f"{s[2]}: el estado '{k}' está repetido"))
            # Los frenos (0.5): un valor escrito que no es del tipo de su regla, y las
            # reglas que miran la respuesta sin un texto de 'reserva' para cuando saltan.
            for ln, regla, e in s[6]:
                escrito = "nada" if e[0] == "nada" else _LITERALES.get(e[0])
                if escrito and escrito not in REGLAS_DE_FRENO[regla][0]:
                    errores.append((ln, (
                        f"en los frenos de {s[2]}, '{regla}' no lleva "
                        f"{_CON_ARTICULO[escrito]}: son "
                        f"{REGLAS_DE_FRENO[regla][2]}. Por ejemplo:  "
                        f"{REGLAS_DE_FRENO[regla][1]}")))
                    continue
                # Un número fijo que no sirve (negativo, con decimales) o una reserva vacía
                # se avisan acá, antes de correr, y no recién en la primera consulta.
                hay, valor = valor_escrito(e)
                if hay and regla in ("largo", "consultas_por_dia", "tokens_por_dia") and (
                        type(valor) is not int or valor < (1 if regla == "largo" else 0)):
                    errores.append((ln, (
                        f"en los frenos de {s[2]}, '{regla}' lleva un número entero"
                        f"{' mayor que cero' if regla == 'largo' else ''} y dice "
                        f"{formato(valor)}. Por ejemplo:  {REGLAS_DE_FRENO[regla][1]}")))
                elif hay and regla == "reserva" and isinstance(valor, str) \
                        and not valor.strip():
                    errores.append((ln, (
                        f"en los frenos de {s[2]}, 'reserva' está vacía: es lo que va a leer "
                        "el cliente cuando salte un freno. Por ejemplo:  "
                        f"{REGLAS_DE_FRENO['reserva'][1]}")))
            reglas = [regla for _, regla, _ in s[6]]
            if "reserva" not in reglas and any(r in REGLAS_DE_CONTENIDO for r in reglas):
                errores.append((s[6][0][0], (
                    f"a los frenos de {s[2]} les falta 'reserva': lo que contesta el agente "
                    "cuando la IA rompe una regla dos veces seguidas. Por ejemplo:  "
                    f"{REGLAS_DE_FRENO['reserva'][1]}")))
            vistos = set()
            for ln, tipo, _, cuerpo in s[4]:
                if tipo == AL_FALLAR:
                    if tipo in vistos:
                        errores.append((ln, f"{s[2]} ya tiene un 'al fallar': va uno solo"))
                    vistos.add(tipo)
                    continue
                if tipo not in mensajes:
                    errores.append((ln, con_sugerencia(
                        f"{s[2]} recibe '{tipo}', que no es un mensaje declarado",
                        tipo, mensajes)))
                if tipo in vistos:
                    errores.append((ln, f"{s[2]} ya tiene un 'al recibir {tipo}'"))
                vistos.add(tipo)
                respuestas_de(s[2], tipo, cuerpo)

    def agente_de(dest, ag):
        """A qué agente declarado le habla, si se puede saber antes de correr."""
        if _es_nodo(dest, "nombre", 3):
            if dest[2] in agentes:
                return dest[2]
            return copias.get(dest[2]) if copias.get(dest[2]) in agentes else None
        if _es_nodo(dest, "yo", 2):
            return ag if ag in agentes else None
        return None

    def nunca_responde(agente, tipo):
        s = declarados[agente]
        cuerpo = next(m[3] for m in s[4] if m[1] == tipo)
        if _contiene(cuerpo, "responder", 3):
            return False
        if cuerpo and _es_nodo(cuerpo[-1], "fallar", 3):
            return False  # falla siempre, a propósito: eso se ataja con 'intentar'
        return not _nombra(cuerpo, {f[2] for f in s[5]})  # quizá responde una función suya

    def visitar(n, ag=None, atajado=False):
        """atajado: adentro de 'intentar { }' o de 'asegurar falla { }'. Ahí un valor que
        no cumple la regla de su campo (mejora 97) no frena el programa antes de correr:
        es la falla que se ataja, o justo la que se quiere probar."""
        if isinstance(n, list):
            for x in n:
                visitar(x, ag, atajado)
            return
        if not isinstance(n, tuple):
            return
        if _es_nodo(n, "agente", 7):
            ag = n[2]
        # Lo que va de condición y, escrito así, nunca puede dar verdadero o falso.
        condiciones = []
        if _es_nodo(n, "si", 4) and isinstance(n[2], list):
            condiciones = [rama[0] for rama in n[2]]
        elif _es_nodo(n, "mientras", 4) or _es_nodo(n, "asegurar", 4) or _es_nodo(n, "no", 3):
            condiciones = [n[2]]
        elif _es_nodo(n, "y", 4) or _es_nodo(n, "o", 4):
            condiciones = [n[2], n[3]]
        for cond in condiciones:
            if no_es_condicion(cond):
                errores.append((cond[1] if isinstance(cond[1], int) else n[1],
                                no_es_condicion(cond)))
        if _es_nodo(n, "nombre", 3) and n[2] in mensajes:
            errores.append((n[1], (
                f"'{n[2]}' es un mensaje: para armar uno van las llaves, aunque no tenga "
                f"campos. Escribí {n[2]} {{}}")))
        if _es_nodo(n, "simular", 6) and isinstance(n[5], list):
            a_quien = agente_de(n[2], ag)
            if n[3] not in mensajes:
                errores.append((n[1], con_sugerencia(
                    f"no existe el mensaje '{n[3]}'", n[3], mensajes)))
            elif a_quien and n[3] not in agentes[a_quien]:
                errores.append((n[1], f"{a_quien} no sabe recibir '{n[3]}': solo se simula "
                                      "un mensaje que el agente ya recibe"))
            else:
                respuestas_de(a_quien or "el agente simulado", n[3], n[5])
            ag = ag or "(simulado)"  # adentro valen 'yo' y 'remitente'
        if len(n) == 4 and n[0] == "ctor" and isinstance(n[3], list):
            _, ln, nombre, pares = n
            if nombre not in mensajes:
                errores.append((ln, con_sugerencia(
                    f"no existe el mensaje '{nombre}'", nombre, mensajes)))
            else:
                decl = {c: (t, op) for c, t, op in mensajes[nombre][3]}
                dados = {}
                for k, e in pares:
                    if k in dados:
                        errores.append((ln, f"{nombre}: el campo '{k}' está repetido"))
                    dados[k] = e
                    if k not in decl:
                        errores.append((ln, con_sugerencia(
                            f"{nombre} no tiene un campo '{k}'", k, decl)))
                        continue
                    tipo = decl[k][0]
                    if e[0] == "nada" and not decl[k][1] and tipo != "cualquiera":
                        errores.append((ln, (
                            f"{nombre}.{k} es obligatorio y le diste nada. Si puede faltar, "
                            f"declaralo opcional en el mensaje: {k}: {tipo}?")))
                        continue
                    if _es_nodo(e, "nombre", 3) and e[2] in funciones:
                        errores.append((ln, "los mensajes llevan datos, no funciones "
                                            f"(campo '{k}' de {nombre})"))
                        continue
                    base = tipo.rsplit(" de ", 1)[-1]
                    if base not in TIPOS_BASE and base not in mensajes:
                        continue  # ese tipo no existe: ya lo dice el error del mensaje
                    malo = literal_que_no_cumple(e, tipo)
                    if malo and malo[1]:
                        errores.append((ln, f"{nombre}.{k} es de tipo {tipo}, y adentro de "
                                            f"la lista hay un valor de tipo {malo[0]}"))
                    elif malo:
                        errores.append((ln, f"{nombre}.{k} es de tipo {tipo}, no {malo[0]}"))
                    else:  # un valor escrito a mano que no cumple la regla del campo
                        hay, valor = valor_escrito(e)
                        rota = hay and not atajado and rompe_regla(f"{nombre}.{k}", valor,
                                                   mensajes[nombre][5].get(k))
                        if rota:
                            errores.append((ln, rota))
                for c, (_, opcional) in decl.items():
                    if c not in dados and not opcional:
                        errores.append((ln, f"a {nombre} le falta el campo '{c}'"))
        elif len(n) == 5 and n[0] == "crear" and isinstance(n[4], list):
            _, ln, nombre, _, pares = n
            if nombre in ajenos:
                errores.append((ln, de_otro_programa(nombre, ajenos[nombre],
                                                     "crear una copia")))
            elif nombre not in agentes:
                errores.append((ln, con_sugerencia(
                    f"no existe el agente '{nombre}'", nombre, agentes)))
            else:
                for k in repetidos(k for k, _ in pares):
                    errores.append((ln, f"{nombre}: el estado '{k}' está repetido"))
                for k, e in pares:
                    if k not in estados[nombre]:
                        errores.append((ln, f"{nombre} no tiene un estado '{k}'"))
                        continue
                    declarado = _LITERALES.get(estados[nombre][k][0])
                    dado = _LITERALES.get(e[0])
                    if declarado and dado and declarado != dado:
                        errores.append((ln, f"{nombre}.{k} arranca como {declarado} "
                                            f"y le diste {dado}"))
        elif len(n) == 4 and n[0] in ("enviar", "preguntar"):
            _, ln, msg, dest = n
            varios = n[0] == "enviar" and _es_nodo(dest, "lista", 3)  # enviar ... a [a, b]
            for uno in (dest[2] if varios else [dest]):
                a_quien = agente_de(uno, ag)
                if a_quien in ajenos and n[0] == "preguntar":
                    errores.append((ln, no_se_le_pregunta(
                        a_quien, ajenos[a_quien],
                        mensajes[msg[2]][4] if _es_nodo(msg, "ctor", 4)
                        and msg[2] in mensajes else None)))
                elif a_quien and _es_nodo(msg, "ctor", 4) and msg[2] in mensajes:
                    if msg[2] not in agentes[a_quien]:
                        errores.append((ln, f"{a_quien} no sabe recibir '{msg[2]}'"))
                    elif a_quien in ajenos:
                        if msg[2] in del_contrato:
                            errores.append((ln, EN_EL_CONTRATO.format(n=msg[2])))
                    elif n[0] == "preguntar" and nunca_responde(a_quien, msg[2]):
                        errores.append((ln, f"{a_quien} recibe '{msg[2]}' pero nunca "
                                            "responde: no se le puede preguntar (le falta "
                                            "un 'responder')"))
        elif _es_nodo(n, "mapa", 3) and isinstance(n[2], list):
            for k in repetidos(k for k, _ in n[2]):
                errores.append((n[1], f"la clave '{k}' está repetida en el mapa: la segunda "
                                      "taparía a la primera"))
        elif _es_nodo(n, "funcion", 6) and isinstance(n[3], list):
            for k in repetidos(n[3]):
                errores.append((n[1], f"{n[2]}(): el parámetro '{k}' está repetido"))
        elif (_es_nodo(n, "yo", 2) or _es_nodo(n, "remitente", 2)) and ag is None:
            que = ("el agente que está atendiendo" if n[0] == "yo"
                   else "quien le mandó el mensaje que está atendiendo")
            errores.append((n[1], f"'{n[0]}' solo existe dentro de un agente (es {que}); "
                                  "acá afuera no hay ninguno"))
        if _es_nodo(n, "intentar", 5) or _es_nodo(n, "asegurar_falla", 4):
            visitar(n[2], ag, True)
            for x in n[3:]:  # (el 'si falla' y el texto esperado se miran como siempre)
                visitar(x, ag, atajado)
            return
        for x in n:
            visitar(x, ag, atajado)

    def fuera_de_prueba(n):
        """mensajes_enviados() o simular_ia() escritos en el programa o en un agente."""
        if isinstance(n, (list, tuple)):
            if (_es_nodo(n, "llamar", 4) and _es_nodo(n[2], "nombre", 3)
                    and n[2][2] in SOLO_EN_PRUEBAS and n[2][2] not in veces):
                errores.append((n[1], SOLO_EN_PRUEBAS[n[2][2]]))
            for x in n:
                fuera_de_prueba(x)

    visitar(programa)
    # (una función suelta sí puede usarla: quizá es una ayuda que llaman las pruebas)
    fuera_de_prueba([s for s in programa if s[0] not in ("prueba", "funcion")])
    errores += revisar_nombres(programa, mensajes, veces, en_consola)
    try:
        ContratoConversacion.del_programa(programa, {nombre: s[3] for nombre, s in mensajes.items()},
                                          agentes)
    except ErrorMate as error:
        errores.append((error.linea, error.mensaje))
    return sorted(set(errores))


# ───────────────────────────── Valores ─────────────────────────────


class Registro:
    """Un mensaje ya construido y validado. Inmutable."""

    def __init__(self, tipo, campos):
        self.tipo = tipo
        self.campos = campos

    def __eq__(self, otro):
        return igual(self, otro)

    __hash__ = None


class TextoDeError(str):
    """El texto del error de un agente, que además recuerda de qué familia era (para el
    registro de errores de uso: lo que el programa dijo con 'fallar' no se anota)."""
    familia = "otro"


class ErrorAtajado(str):
    """El error que ataja 'si falla e'. Es un texto como cualquier otro, que además
    recuerda los datos del error para detalle_de(e)."""

    def __new__(cls, error):
        obj = super().__new__(cls, error.mensaje)
        obj.detalle = {"texto": error.mensaje,
                       "linea": int(error.linea) if error.linea else None,
                       "clase": error.familia, "dato": error.dato}
        return obj


class Agente:
    def __init__(self, nombre):
        self.nombre = nombre
        self.decl = None
        self.env = None
        self.manejadores = {}
        self.ocupado = False
        self.inicial = None  # el estado con el que nació (para empezar limpia cada prueba)
        self.creador = None  # si es una copia: el agente que la creó mientras atendía
        self.recuerda = True  # una copia sin nombre ('crear' sin 'llamado') no tiene memoria
        self.lecciones = []  # [{"fecha", "texto"}]: nunca se cambia, se reemplaza por otra
        # Lo de la 0.5, solo en los agentes declarados (sus copias usan lo del original):
        self.propuestas = []  # lecciones propuestas, sin aprobar: [{"fecha", "texto", "motivo"}]
        self.gasto = {}  # la cuenta de consultas: {"2026-11-21": {"consultas", "simuladas", "tokens"}}
        self.ensayo_desde = {}  # día -> las simuladas que ya traía la memoria al empezar
        # Un agente de OTRO programa (0.7): acá solo es un destino de 'enviar'.
        self.ajeno = None  # el archivo de ese programa ("deposito.mate"), o None si es de acá
        self.programa = None  # cómo se llama ese programa en el buzón ("deposito")
        self.carpeta_buzon = None  # la carpeta de su buzón ("deposito.buzon"), si se conoce
        self.solo_responde = False  # llegó como remitente y no hay 'usar buzon' de su programa
        self.socio = None  # si es un socio de 'usar socio' (0.8): su nombre
        self.propios = {}  # lo que sabe recibir, sin lo que se haya simulado en una prueba


class Funcion:
    def __init__(self, nombre, params, cuerpo, env, defectos=()):
        self.nombre, self.params, self.cuerpo, self.env = nombre, params, cuerpo, env
        self.defectos = defectos  # [(parámetro, valor por defecto)]: son los últimos
        self.armado = None  # el cuerpo listo para correr: se arma en la primera llamada
        self.directa = None  # si sus parámetros se anotan sin más controles (ver llamar)


class Nativa:
    def __init__(self, nombre, fn):
        self.nombre, self.fn = nombre, fn


class DePython(Nativa):
    """Una función escrita en Python, traída con 'usar python' (0.5). Se llama como
    cualquier otra; un renglón que solo la llama vale, porque puede estar haciendo algo."""


class ModuloPython:
    """Un archivo .py traído con 'usar python "ayudas.py"': sus funciones se llaman
    ayudas.nombre(...). No es un dato: no viaja en mensajes ni se guarda."""

    def __init__(self, nombre, archivo, funciones):
        self.nombre, self.archivo, self.funciones = nombre, archivo, funciones

    def __str__(self):
        return f"<python {os.path.basename(self.archivo)}>"

    def funcion(self, nombre):
        if nombre in self.funciones:
            return self.funciones[nombre]
        archivo = os.path.basename(self.archivo)
        if not self.funciones:
            raise ErrorMate(f"{archivo} no tiene ninguna función para usar desde Mate: se "
                            "ven las que están escritas ahí con 'def' y no empiezan con "
                            "guion bajo", familia="python")
        if nombre.startswith("_"):
            raise ErrorMate(f"'{nombre}' empieza con guion bajo, y esas funciones de "
                            f"{archivo} no se ven desde Mate: en Python así se marcan las "
                            "que son de uso interno", familia="python")
        raise ErrorMate(no_esta(f"{archivo} no tiene una función '{nombre}'", nombre,
                                self.funciones), familia="python")


class _Retorno(Exception):
    def __init__(self, valor):
        self.valor = valor


class _Respuesta(Exception):
    def __init__(self, valor, linea=None):
        self.valor = valor
        self.linea = linea  # el renglón del 'responder'


class _Romper(Exception):
    """'romper': sale del bucle."""


class _Continuar(Exception):
    """'continuar': salta a la vuelta siguiente."""


# Lo que devuelve una sentencia ya armada cuando corta el camino (ver Interprete._paso):
# 'romper', 'continuar' o, si fue un 'devolver', una tupla con el valor.
_ROMPER, _CONTINUAR = object(), object()
_SIN_VALOR = (None,)  # un 'devolver' solo
# Lo que puede fallar dentro de una sentencia y Mate explica con su renglón.
_SE_EXPLICAN = (ErrorMate, RecursionError, MemoryError)
# Una cuenta entre enteros más chicos que esto no puede pasar ningún tope: va directo.
_CHICO = 1 << 62
_CUENTAS = {"+": operator.add, "-": operator.sub, "*": operator.mul}
_COMPARACIONES = {"==": operator.eq, "!=": operator.ne, "<": operator.lt,
                  "<=": operator.le, ">": operator.gt, ">=": operator.ge}
_finito = math.isfinite


def condicion_rara(v, linea=None):
    """El error de una condición que no dio ni verdadero ni falso."""
    return ErrorMate("la condición tiene que ser verdadero o falso, no " + tipo_claro(v),
                     linea)


def es_num(v):
    return type(v) in (int, float)


def nombre_tipo(v):
    if v is None:
        return "nada"
    if type(v) is bool:
        return "logico"
    if es_num(v):
        return "numero"
    if isinstance(v, str):
        return "texto"
    if isinstance(v, list):
        return "lista"
    if isinstance(v, dict):
        return "mapa"
    if isinstance(v, Registro):
        return v.tipo
    if isinstance(v, Agente):
        return "agente"
    if isinstance(v, ModuloPython):
        return "python"
    return "funcion"


CAUSA_DE_NADA = ("'nada' es la falta de valor: ¿a la función le falta un 'devolver', o es "
                 "un campo opcional que vino vacío?")
_CON_ARTICULO = {"nada": "el valor nada", "numero": "un número", "texto": "un texto",
                 "logico": "un valor lógico", "lista": "una lista", "mapa": "un mapa",
                 "agente": "un agente", "funcion": "una función",
                 "python": "un archivo de Python"}
_VERBOS = {"+": "sumar", "-": "restar", "*": "multiplicar", "/": "dividir", "%": "dividir"}


def tipo_claro(v):
    """El tipo para un mensaje de error: 'nada' suelto se lee como otra frase ("no se
    puede hacer nada"), así que se dice "el valor nada"."""
    if isinstance(v, ModuloPython):
        return "un archivo de Python"
    return "el valor nada" if v is None else nombre_tipo(v)


def un(v):
    """'un número', 'una lista', 'el valor nada', 'un mensaje Pedido'."""
    return _CON_ARTICULO.get(nombre_tipo(v), f"un mensaje {nombre_tipo(v)}")


def alfabetico(t):
    """La clave para ordenar textos como en el diccionario: sin importar mayúsculas ni
    tildes, y con la ñ después de la n."""
    return sin_tildes(unicodedata.normalize("NFC", t).lower().replace("ñ", "n\U0010ffff"))


def claves_de_orden(valores):
    """Con qué comparar esos valores para ordenarlos: los números por su valor y los
    textos por el abecedario. Si están mezclados o son otra cosa, None."""
    if all(es_num(x) for x in valores):
        return list(valores)
    if all(isinstance(x, str) for x in valores):
        return [(alfabetico(x), x) for x in valores]
    return None


def lo_que_tiene(nombres):
    """' (tiene: a, b, c)' para el error de una clave o un campo que no está."""
    nombres = [str(n) for n in nombres]
    if not nombres:
        return " (está vacío)"
    return " (tiene: " + ", ".join(nombres[:8]) + (", ..." if len(nombres) > 8 else "") + ")"


def no_esta(mensaje, nombre, disponibles):
    """El error de una clave o un campo que no está: con el nombre parecido si lo hay
    y, si no, con la lista de los que sí hay."""
    return (con_sugerencia(mensaje, nombre, disponibles) if sugerir(nombre, disponibles)
            else mensaje + lo_que_tiene(disponibles))


_SUELTOS = frozenset((int, float, str, bool, type(None)))


def lleva_agente(v, ajeno=False):
    """¿Hay un agente en este valor, aunque sea adentro de una lista, mapa o mensaje?
    ajeno: solo cuentan los de otro programa. Devuelve el agente, o None."""
    if v.__class__ in _SUELTOS:
        return None
    if isinstance(v, Agente):
        return v if v.ajeno is not None or not ajeno else None
    if isinstance(v, Registro):
        v = v.campos
    if isinstance(v, dict):
        v = v.values()
    elif not isinstance(v, list):
        return None
    for x in v:
        hallado = lleva_agente(x, ajeno)
        if hallado is not None:
            return hallado
    return None


def lleva_funcion(v):
    """¿Hay una función en este valor, aunque sea adentro de una lista, mapa o mensaje?"""
    if v.__class__ in _SUELTOS:  # un número, un texto, verdadero, falso o nada: seguro que no
        return False
    if isinstance(v, (Funcion, Nativa, ModuloPython)):
        return True
    if isinstance(v, list):
        return any(lleva_funcion(x) for x in v)
    if isinstance(v, dict):
        return any(lleva_funcion(x) for x in v.values())
    if isinstance(v, Registro):
        return any(lleva_funcion(x) for x in v.campos.values())
    return False


def igual(a, b):
    """Igualdad sin conversiones a escondidas, también adentro de listas y mapas:
    1 no es igual a verdadero, ni [1] a [verdadero]."""
    if es_num(a) and es_num(b):
        return a == b
    if isinstance(a, str) and isinstance(b, str):
        return str(a) == str(b)
    if type(a) is not type(b):
        return False
    if isinstance(a, list):
        return len(a) == len(b) and all(igual(x, y) for x, y in zip(a, b))
    if isinstance(a, dict):
        return a.keys() == b.keys() and all(igual(v, b[k]) for k, v in a.items())
    if isinstance(a, Registro):
        return a.tipo == b.tipo and igual(a.campos, b.campos)
    return a == b


def muy_largo(que="el texto"):
    tope = f"{MAX_LARGO:,}".replace(",", ".")
    return ErrorMate(f"{que} quedaría demasiado largo (más de {tope} letras)"
                     if que.startswith("el") else
                     f"{que} quedaría demasiado larga (más de {tope} elementos)")


def revisar_peso(v, por_elemento=1):
    """Antes de pasar a texto una lista, un mapa o un mensaje: si entre todo lo que tiene
    adentro hay más de 10.000.000 de elementos o letras, es un error (y no una espera
    eterna). Lo de adentro puede estar repetido muchas veces sin ocupar memoria.
    por_elemento: cuántas letras ocupa como mínimo cada elemento al escribirlo ("1, ")."""
    def peso(x):
        if isinstance(x, str):
            return len(x)
        if isinstance(x, Registro):
            x = x.campos
        if isinstance(x, dict):
            x = x.values()
        elif not isinstance(x, list):
            return 1
        total = len(x) * por_elemento
        for y in x:
            if isinstance(y, (str, list, dict, Registro)):
                total += peso(y)
                if total > MAX_LARGO:
                    raise muy_largo()
        if total > MAX_LARGO:
            raise muy_largo()
        return total

    if isinstance(v, (list, dict, Registro)):
        peso(v)
    return v


def a_texto(v):
    """formato(v), cuidando que el texto no pase el tope."""
    t = formato(revisar_peso(v, 3))
    if len(t) > MAX_LARGO:
        raise muy_largo()
    return t


_FECHA = re.compile(r"\d\d/\d\d/\d{4}( \d\d:\d\d)?")


def se_juntan(a, b):
    """¿Son dos textos o dos listas? (lo que '+' pega uno atrás del otro)"""
    return any(isinstance(a, clase) and isinstance(b, clase) for clase in (str, list))


def decimal_limpio(v):
    """Un decimal como lo escribiría una persona: 0.1 + 0.2 se ve 0.3 y nunca sale 1e-05.
    Solo cambia cómo se muestra: el valor guardado es el mismo."""
    if math.isnan(v):
        return "no es un número"
    if math.isinf(v):
        return "infinito" if v > 0 else "-infinito"
    if v.is_integer():
        return str(int(v))
    t = repr(v)
    cifras = len(t.lstrip("-").split("e")[0].replace(".", "").lstrip("0"))
    if cifras > 15:  # trae el "ruido" de las cuentas con decimales: se muestra redondeado
        if abs(v) < 1e10:
            t = format(v, ".12g")
        else:  # en los números grandes solo se quita el ruido, no cifras de verdad
            corto = format(v, ".15g")
            if abs(float(corto) - v) <= abs(v) * 4.5e-16:
                t = corto
    if "e" in t:
        t = format(decimal.Decimal(t), "f")
    if "." in t:
        t = t.rstrip("0").rstrip(".")
    return t


def redondeo(x, decimales):
    """x redondeado a esa cantidad de decimales, con el medio hacia arriba (2.5 -> 3;
    en los negativos se aleja del cero: -2.5 -> -3). Devuelve un Decimal."""
    d = decimal.Decimal(x) if type(x) is int else decimal.Decimal(repr(x))
    if type(x) is float:
        # Se redondea el número como se muestra: 0.57 * 50 se ve 28.5 (por dentro es
        # 28.499999999999996) y redondea a 29, no a 28.
        limpio = decimal.Decimal(decimal_limpio(x))
        if -limpio.as_tuple().exponent > decimales:
            d = limpio
    if -d.as_tuple().exponent <= decimales:
        return d  # ya tiene esa cantidad de decimales o menos
    contexto = decimal.Context(prec=max(d.adjusted(), 0) + decimales + 10)
    return d.quantize(decimal.Decimal(1).scaleb(-decimales, contexto),
                      rounding=decimal.ROUND_HALF_UP, context=contexto)


_NUMERO_AR = re.compile(r"[+-]?[0-9]{1,3}(\.[0-9]{3})+,[0-9]+")       # 1.234,50
_NUMERO_COMA = re.compile(r"[+-]?[0-9]+,[0-9]+")                      # 3,5
_NUMERO_COMUN = re.compile(r"[+-]?[0-9]+(\.[0-9]+)?")                 # 12 y 3.5
_NUMERO_MILES = re.compile(r"[+-]?[0-9]{1,3}(\.[0-9]{3}){2,}")        # 1.234.567
# (0.8.1) Un texto con un solo punto y EXACTAMENTE tres cifras atrás es de miles, como se
# escribe acá: "3.500" es tres mil quinientos y "35.000" treinta y cinco mil. La parte
# entera tiene de una a tres cifras y no empieza con cero: "0.500" sigue siendo medio, y
# "3.5", "3.50", "3.5000" y "1234.567" siguen siendo decimales. Vale para los TEXTOS (lo
# que escribe una persona, una planilla, un archivo); un número escrito en el programa
# (3.500 sin comillas) no pasa por acá y sigue valiendo tres y medio.
_NUMERO_MIL = re.compile(r"[+-]?[1-9][0-9]{0,2}\.[0-9]{3}")            # 3.500


def numero_de_texto(texto):
    """Lee un número escrito como texto, también a la argentina ("$ 1.234,50")."""
    def no_es():
        return ErrorMate(f"'{texto}' no es un número", familia="numero")

    t = texto.strip()
    if not t:
        raise ErrorMate("un texto vacío no es un número", familia="numero")
    con_signo = re.match(r"([+-]?)\$\s*", t)
    if con_signo:  # "$ 100" y también "-$ 100", que es como escribe pesos()
        t = con_signo.group(1) + t[con_signo.end():]
    if "." in t and "," in t:
        if not _NUMERO_AR.fullmatch(t):
            raise no_es()
        t = t.replace(".", "").replace(",", ".")
    elif "," in t:
        if not _NUMERO_COMA.fullmatch(t):
            raise no_es()
        t = t.replace(",", ".")
    elif _NUMERO_MILES.fullmatch(t) or _NUMERO_MIL.fullmatch(t):
        t = t.replace(".", "")
    elif not _NUMERO_COMUN.fullmatch(t):
        raise no_es()
    try:
        n = float(t) if "." in t else int(t)
    except ValueError:  # Python no convierte enteros de miles de cifras
        raise no_es()
    if type(n) is float and not math.isfinite(n):
        raise no_es()
    return n


def formato(v, raiz=True):
    if v is None:
        return "nada"
    if type(v) is bool:
        return "verdadero" if v else "falso"
    if type(v) is float:
        return decimal_limpio(v)
    if isinstance(v, str):
        return v if raiz else json.dumps(v, ensure_ascii=False)
    if isinstance(v, list):
        return "[" + ", ".join(formato(x, False) for x in v) + "]"
    if isinstance(v, dict):
        return "{" + ", ".join(f"{k}: {formato(x, False)}" for k, x in v.items()) + "}"
    if isinstance(v, Registro):
        if not v.campos:
            return v.tipo
        return v.tipo + " { " + ", ".join(
            f"{k}: {formato(x, False)}" for k, x in v.campos.items()) + " }"
    if isinstance(v, Agente):
        return v.nombre if raiz else f"<agente {v.nombre}>"
    if isinstance(v, (Funcion, Nativa)):
        return f"<funcion {v.nombre}>"
    try:
        return str(v)
    except ValueError:  # Python no escribe enteros de miles de cifras
        raise ErrorMate("ese número es demasiado grande para mostrarlo")


_JSON_EN_CRIOLLO = (
    ("Expecting value", "falta un valor"),
    ("Expecting ',' delimiter", "falta una coma o el cierre (']' o '}')"),
    ("Expecting ':' delimiter", "faltan los dos puntos ':' después de una clave"),
    ("Expecting property name", "las claves van entre comillas dobles"),
    ("Illegal trailing comma", "sobra una coma antes del cierre"),
    ("Extra data", "sobra texto después del final"),
    ("Unterminated string", "hay un texto al que le falta la comilla de cierre"),
    ("Invalid control character", "hay un salto de renglón dentro de un texto"),
    ("Invalid", "hay una barra \\ mal usada dentro de un texto"),
)


def json_invalido(texto, error):
    """El error de leer un JSON, explicado en español."""
    if not texto.strip():
        return "JSON inválido: el texto está vacío"
    motivo = next((criollo for ingles, criollo in _JSON_EN_CRIOLLO
                   if error.msg.startswith(ingles)), "no lo pude entender")
    if error.pos >= len(texto.rstrip()):
        return f"JSON inválido: {motivo} (al final del texto)"
    return f"JSON inválido: {motivo} (en la letra {error.pos + 1} del texto)"


# Por qué no se puede cambiar un nombre, según de dónde salió.
NO_SE_CAMBIA = {
    "sea": "'{n}' es fijo (sea); declaralo con 'var' para cambiarlo",
    "parametro": "'{n}' es un parámetro y no se cambia; guardalo en otra variable: "
                 "var {n}2 = {n}",
    "para": "'{n}' es la variable del 'para' y no se cambia adentro del bucle",
    "mensaje": "'{n}' es el mensaje recibido y no se cambia; copiá lo que necesites a una "
               "variable con 'var'",
    "falla": "'{n}' es el error atajado y no se cambia",
    "funcion": "'{n}' es una función y no se le puede asignar un valor",
    "agente": "'{n}' es un agente y no se le puede asignar un valor",
    "nativa": "'{n}' es una función incluida de Mate y no se le puede asignar un valor",
    "python": "'{n}' es el archivo de Python que trajo 'usar python' y no se le puede "
              "asignar un valor",
}


def por_teclado(pregunta):
    """Muestra la pregunta y espera que la persona escriba y apriete Enter."""
    return input(pregunta if pregunta.endswith((" ", "\n")) or not pregunta
                 else pregunta + " ")


class CorteEnElTeclado(KeyboardInterrupt):
    """Ctrl+C mientras leer() esperaba que la persona escribiera (0.5): es la manera normal
    de cortar una charla, así que el programa termina ahí, prolijo y sin cartel de error
    (el código de salida sigue siendo 130, el de cualquier corte con Ctrl+C).
    (Lo que recuerdan los agentes se guarda igual, como con cualquier otro final.)"""


CORTE_EN_EL_TECLADO = ("Listo: cortaste con Ctrl+C mientras el programa esperaba que "
                       "escribieras, y terminó ahí.")


# ───────────────────────── Tablas: leer_tabla() (0.5) ─────────────────────────
# Una planilla de Excel guardada como CSV: la primera fila son los títulos, y cada fila de
# abajo queda como un mapa con esos títulos como claves. Se aceptan las dos formas en que
# Excel la guarda (separada por punto y coma, que es lo que hace en la Argentina, o por
# coma) y los números escritos a la argentina.
_EMPIEZA_CON_CERO = re.compile(r"[+-]?0[0-9]+")              # 00123: un código, no un número
COMO_GUARDAR_CSV = ("En Excel: Archivo > Guardar como > en 'Tipo' elegí "
                    "\"CSV (delimitado por comas) (*.csv)\" y guardalo en la carpeta del "
                    "programa")


def valor_de_celda(celda):
    """Lo que vale una celda de la planilla: un número si está escrita como número (también
    a la argentina: 3.500, 3.500,50, $ 3.500, 3500.-, 1.200 $), y si no, el texto tal cual,
    sin los espacios de las puntas. Una celda vacía es el texto vacío."""
    t = celda.strip()
    sin_pesos = re.sub(r"^([+-]?)\$\s*", r"\1", t)
    sin_pesos = re.sub(r"(?<=\d)(?:\s*\$|[.,]-)$", "", sin_pesos)  # 1.200 $   3500.-
    if not t or _EMPIEZA_CON_CERO.fullmatch(sin_pesos):
        return t
    try:  # "3.500" es 3500 acá y en numero(): la misma regla (0.8.1)
        return numero_de_texto(sin_pesos)
    except ErrorMate:
        return t


def separador_de(titulos):
    """Con qué están separadas las columnas: se mira la fila de los títulos. Si hay duda,
    punto y coma, que es lo que usa Excel en la Argentina."""
    cuenta, entre_comillas = {";": 0, ",": 0, "\t": 0}, False
    for letra in titulos:
        if letra == '"':
            entre_comillas = not entre_comillas
        elif letra in cuenta and not entre_comillas:
            cuenta[letra] += 1
    return max(cuenta, key=lambda s: cuenta[s])


def tabla_de_texto(texto, nombre):
    """Las filas de un CSV, como una lista de mapas. 'nombre' es para los errores."""
    def mal(que):
        return ErrorMate(f"leer_tabla(): {que}", familia="archivo")

    texto = texto.lstrip("\ufeff")
    corrido = 0  # renglones del archivo que quedaron arriba de lo que se lee
    aviso_de_excel = re.match(r"sep=(.)[ \t]*\n", texto)  # un renglón que a veces pone Excel
    if aviso_de_excel:
        texto, corrido = texto[aviso_de_excel.end():], 1
    renglones = texto.split("\n")
    while renglones and not renglones[0].strip(" \t;,"):
        renglones.pop(0)  # renglones en blanco antes de los títulos
        corrido += 1
    if not renglones:
        raise mal(f"'{nombre}' está vacío. Tiene que traer una primera fila con los títulos "
                   "de las columnas (por ejemplo producto;precio) y, debajo, un renglón por "
                   "cada producto")
    separador = aviso_de_excel.group(1) if aviso_de_excel else separador_de(renglones[0])
    try:
        lector = csv.reader(io.StringIO("\n".join(renglones)), delimiter=separador)
    except (csv.Error, TypeError):
        lector = csv.reader(io.StringIO("\n".join(renglones)), delimiter=";")
    titulos, filas, anterior = None, [], 0
    while True:
        try:
            celdas = next(lector)
        except StopIteration:
            break
        except csv.Error:
            raise mal(f"no pude entender el renglón {corrido + anterior + 1} de '{nombre}': "
                       "¿hay una comilla que abre y no cierra?")
        renglon, anterior = corrido + anterior + 1, lector.line_num
        celdas = [c.strip() for c in celdas]
        if not any(celdas):
            continue  # un renglón en blanco (o los ;;; que deja Excel al final)
        if titulos is None:
            ancho = len(celdas)
            while celdas and not celdas[-1]:
                celdas.pop()  # columnas vacías que Excel deja a la derecha
            sin_titulo = [i + 1 for i, t in enumerate(celdas) if not t]
            if sin_titulo:
                raise mal(f"en '{nombre}' la columna {sin_titulo[0]} no tiene título (los "
                           f"títulos van en la primera fila, el renglón {renglon}): "
                           "escribile uno, o borrá esa columna")
            repetido = repetidos(celdas)
            if repetido:
                raise mal(f"en '{nombre}' hay dos columnas con el mismo título, "
                           f"'{repetido[0]}': cambiale el nombre a una")
            titulos, renglon_de_titulos = celdas, renglon
            continue
        while len(celdas) > len(titulos) and not celdas[-1]:
            celdas.pop()
        if len(titulos) > 1 and ([sin_tildes(c.lower()) for c in celdas]
                                 == [sin_tildes(t.lower()) for t in titulos]):
            # Pasa al pegar una lista debajo de otra: los títulos quedan dos veces, y la
            # segunda vez se leerían como un producto más (0.6). Con una sola columna no
            # se mira: ahí un dato igual al título puede ser un dato de verdad.
            raise mal(
                f"el renglón {renglon} de '{nombre}' repite los títulos de las columnas "
                f"({separador.join(titulos)}), que ya están en el renglón "
                f"{renglon_de_titulos}. Los títulos van una sola vez, arriba de todo: borrá "
                f"el renglón {renglon} entero (con Excel o con el Bloc de notas) y guardá "
                "de nuevo")
        if len(celdas) != len(titulos):
            if not filas and len(celdas) > len(titulos) and (
                    len(titulos) == 1 or ancho > len(titulos)):
                # Arriba de los títulos hay otra cosa: el nombre de la lista, una fecha...
                raise mal(
                    f"la primera fila de '{nombre}' tiene que ser la de los títulos de las "
                    f"columnas (por ejemplo producto;precio;stock) y parece ser otra cosa "
                    f"({recortado(', '.join(titulos), 60)}): tiene {len(titulos)} "
                    f"{'dato' if len(titulos) == 1 else 'datos'} y el renglón {renglon} tiene "
                    f"{len(celdas)}. Si los títulos están más abajo, en el renglón {renglon} "
                    f"({recortado(separador.join(celdas), 60)}), en Excel borrá las filas "
                    "que están arriba de los títulos y guardá de nuevo")
            if len(celdas) > len(titulos):
                pista = ("le sobra algo. Si un dato lleva coma o punto y coma adentro (un "
                         "precio como 3.500,50 en un archivo separado por comas), tiene que "
                         "ir entre comillas: \"3.500,50\"")
            else:
                pista = "le falta un dato, o un separador"
            separa = {";": "punto y coma", ",": "coma", "\t": "tabulación"}.get(
                separador, f"'{separador}'")
            raise mal(
                f"el renglón {renglon} de '{nombre}' tiene {len(celdas)} "
                f"{'columna' if len(celdas) == 1 else 'columnas'} y los títulos son "
                f"{len(titulos)} ({', '.join(titulos)}): {pista}. (Las columnas están "
                f"separadas por {separa}.) El renglón dice: "
                f"{recortado(separador.join(celdas), 80)}")
        filas.append({titulo: valor_de_celda(c) for titulo, c in zip(titulos, celdas)})
    return filas


# ───────────────────────────── La IA (mejora 100) ─────────────────────────────
# consultar_ia() le habla a Claude, de Anthropic, por la red. Todo con la biblioteca
# estándar. La clave nunca está en el programa: se lee de la variable ANTHROPIC_API_KEY.

IA_DIRECCION = "https://api.anthropic.com/v1/messages"
IA_VERSION = "2026-10-21"  # el encabezado anthropic-version
IA_MODELO = "claude-opus-5-5"  # se cambia con la variable MATE_MODELO
IA_MAX_TOKENS = 16000  # el largo máximo de una respuesta (pensar también gasta de acá)
IA_ESPERA = 180  # segundos que se espera una respuesta antes de darla por perdida
IA_REINTENTOS = 2  # si la IA está saturada o se corta la red, se prueba de nuevo
IA_ESPERA_MAXIMA = 30  # nunca se queda esperando más que esto entre dos intentos
MAX_CONSULTAS_IA = 50  # consultas de verdad (pagas) por corrida; --sin-limite lo saca
# Si un filtro de seguridad no deja contestar al modelo, Anthropic prueba con otro en el
# mismo pedido. Solo estos modelos lo aceptan.
IA_CON_RESPALDO = ("claude-fable-5-2", "claude-fable-5-1", "claude-opus-5-5",
                   "claude-opus-5", "claude-sonnet-5-5")
IA_RESPALDO = "server-side-fallback-2026-07-01"  # el encabezado anthropic-beta que lo pide
_IA_SIN_RESPALDO = set()  # modelos a los que Anthropic les rechazó ese pedido de respaldo
DONDE_SE_SACA = "platform.claude.com"
FALTA_LA_CLAVE = (
    "consultar_ia(): falta la clave para hablar con la IA. En PowerShell, antes de correr, "
    'escribí:  $env:ANTHROPIC_API_KEY = "tu-clave"\n'
    f"La clave se saca en {DONDE_SE_SACA} y el servicio es pago (se cobra cada consulta). "
    "Para probar sin clave y sin gastar: --ia-simulada")
SIN_RESPUESTA_SIMULADA = (
    "consultar_ia(): acá Mate no sale a la red y no hay una respuesta simulada para esta "
    'consulta. En una prueba, fijala antes con simular_ia("lo que contesta"); o dale un '
    "tercer valor a consultar_ia(), que es lo que contesta cuando no habla con la IA de "
    "verdad")


def error_de_ia(texto):
    return ErrorMate(f"consultar_ia(): {texto}", familia="ia")


def clave_de_ia():
    """La clave, de la variable de entorno. Nunca se muestra ni se guarda en otro lado."""
    clave = os.environ.get("ANTHROPIC_API_KEY", "").strip().strip("\"'").strip()
    if not clave:
        raise ErrorMate(FALTA_LA_CLAVE, familia="ia")
    if not (clave.isascii() and clave.isprintable()) or " " in clave:
        raise error_de_ia(
            "la clave guardada en ANTHROPIC_API_KEY tiene espacios o letras raras (no la "
            "muestro por seguridad). Copiala de nuevo, entera y sin nada de más")
    return clave


def tapar_clave(texto, clave):
    """El texto sin la clave: ni entera, ni en mayúsculas, ni un pedazo de 8 o más
    caracteres (por si un servidor la devuelve partida o cambiada en su error)."""
    texto = str(texto)
    if not clave:
        return texto
    minimo = min(8, len(clave))
    bajo, llave = texto.lower(), clave.lower()
    pedazos = {llave[i:i + minimo] for i in range(len(llave) - minimo + 1)}
    partes, i, desde = [], 0, 0
    while i <= len(bajo) - minimo:
        if bajo[i:i + minimo] not in pedazos:
            i += 1
            continue
        fin = i + minimo  # se estira mientras lo que sigue también sea parte de la clave
        while fin < len(bajo) and bajo[i:fin + 1] in llave:
            fin += 1
        partes += [texto[desde:i], "(la clave)"]
        i = desde = fin
    return "".join(partes) + texto[desde:]


def modelo_de_ia():
    modelo = os.environ.get("MATE_MODELO", "").strip().strip("\"'").strip() or IA_MODELO
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:@\[\]-]{0,99}", modelo):
        raise error_de_ia(
            "la variable MATE_MODELO no tiene el nombre de un modelo. Poné uno como "
            f'"{IA_MODELO}", o borrala para usar ese:  Remove-Item Env:MATE_MODELO')
    return modelo


def texto_de_la_ia(datos):
    """El texto de una respuesta de la IA que llegó bien (o el error que lo explica)."""
    bloques = datos.get("content") if isinstance(datos, dict) else None
    if not isinstance(bloques, list):
        raise error_de_ia("llegó una respuesta que no pude entender. Probá de nuevo")
    if datos.get("stop_reason") == "refusal":
        raise error_de_ia("la IA no quiso contestar esa consulta (la frenó un filtro de "
                          "seguridad de Anthropic). Probá preguntándolo de otra manera")
    texto = "".join(b["text"] for b in bloques if isinstance(b, dict)
                    and b.get("type") == "text" and isinstance(b.get("text"), str)).strip()
    if datos.get("stop_reason") == "max_tokens":
        raise error_de_ia("la respuesta llegó cortada: era más larga de lo que entra en una "
                          "consulta. Pedile en las instrucciones que conteste más corto")
    if not texto:
        raise error_de_ia("la IA contestó sin texto. Probá de nuevo o cambiá la pregunta")
    return texto


def explicar_error_de_ia(codigo, dicho, detalles, modelo):
    """Qué significa, en castellano, el error con el que contestó Anthropic."""
    dicho = " ".join(str(dicho or "").split())[:300]
    original = f" (Anthropic dijo: {dicho})" if dicho else ""
    poner = '$env:ANTHROPIC_API_KEY = "tu-clave"'
    if codigo == 401:
        return ("la clave no sirve: Anthropic no la reconoce (está mal copiada, vencida o "
                f"la borraron). Sacá una nueva en {DONDE_SE_SACA} y ponela otra vez:  {poner}")
    if codigo == 402 or "credit balance" in dicho.lower():
        return ("la cuenta de Anthropic no tiene crédito (o hay un problema con el pago). "
                f"Se carga en {DONDE_SE_SACA}, en la parte de facturación")
    if codigo == 403:
        return f"esa clave no tiene permiso para hacer esta consulta{original}"
    if codigo == 404:
        return (f"Anthropic no conoce el modelo '{modelo}', o tu cuenta no puede usarlo. "
                + ("Revisá la variable MATE_MODELO, o borrala para usar el de siempre:  "
                   "Remove-Item Env:MATE_MODELO" if os.environ.get("MATE_MODELO", "").strip()
                   else f"Fijate en {DONDE_SE_SACA} qué modelos tiene tu cuenta y elegí uno "
                   "con la variable MATE_MODELO"))
    if codigo == 413 or "prompt is too long" in dicho.lower():
        return "la consulta es demasiado larga para mandársela a la IA: achicá el texto"
    if codigo == 429 and detalles.get("error_code") == "enforced_spend_limit_reached":
        return ("la cuenta de Anthropic llegó a su tope de gasto del mes. Se cambia en "
                f"{DONDE_SE_SACA}, o hay que esperar al mes que viene")
    if codigo == 429:
        return ("demasiadas consultas en poco tiempo: se llegó al límite de uso de la "
                "cuenta. Esperá un minuto y probá de nuevo")
    if codigo == 529:
        return "la IA está saturada en este momento. Probá de nuevo en unos minutos"
    if codigo >= 500:
        return ("el servicio de la IA tuvo un problema (no es tu programa). Probá de nuevo "
                "en unos minutos")
    if codigo == 400:
        return f"Anthropic no aceptó la consulta{original or ' y no dijo por qué'}"
    return f"Anthropic contestó con un error que no conozco (código {codigo}){original}"


# ─────────────── Un modelo propio en vez de Claude (variable MATE_IA_PROPIA) ───────────────
# Con MATE_IA_PROPIA puesta, consultar_ia() le habla a ese servicio (uno que entiende
# "chat completions": Ollama, LM Studio, llama.cpp...) y no a Anthropic. Todo lo demás es
# igual: lecciones, frenos, tope por día, traza y bitácora.
IA_PROPIA_ATAJOS = {"ollama": "http://localhost:11434/v1/chat/completions",
                    "lmstudio": "http://localhost:1234/v1/chat/completions"}


def direccion_de_ia_propia():
    """La dirección del modelo propio, o None si se usa Claude."""
    valor = os.environ.get("MATE_IA_PROPIA", "").strip().strip("\"'").strip()
    if not valor:
        return None
    direccion = IA_PROPIA_ATAJOS.get(valor.lower(), valor)
    if not re.fullmatch(r"https?://[^\s/@?#]+(/[^\s?#]*)?", direccion):
        raise error_de_ia(
            'la variable MATE_IA_PROPIA no tiene una dirección que entienda. Poné "ollama", '
            'o la dirección completa, como "http://localhost:11434/v1/chat/completions". '
            "Para volver a la IA de siempre:  Remove-Item Env:MATE_IA_PROPIA")
    return direccion


def modelo_de_ia_propia():
    """El nombre del modelo propio (MATE_MODELO), o un error que dice cómo ponerlo."""
    modelo = os.environ.get("MATE_MODELO", "").strip().strip("\"'").strip()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:@/\[\]-]{0,99}", modelo):
        raise error_de_ia(
            "con MATE_IA_PROPIA hay que decir qué modelo usar, con el nombre que le da tu "
            'servicio. En PowerShell:  $env:MATE_MODELO = "qwen2.5:3b"   (con Ollama, los '
            "nombres los muestra:  ollama list)")
    return modelo


def pedir_a_la_ia_propia(direccion, instrucciones, pregunta):
    """Como pedir_a_la_ia, pero contra un modelo propio. La clave (si hace falta) va en
    MATE_IA_PROPIA_CLAVE y nunca aparece en un error."""
    import http.client
    import socket
    import urllib.error
    import urllib.parse
    import urllib.request

    modelo = modelo_de_ia_propia()
    clave = os.environ.get("MATE_IA_PROPIA_CLAVE", "").strip().strip("\"'").strip()
    lugar = urllib.parse.urlsplit(direccion).netloc
    local = lugar.split(":")[0].lower() in ("localhost", "127.0.0.1", "[::1]")

    def error(texto):
        return error_de_ia(tapar_clave(texto, clave))

    mensajes = [{"role": "user", "content": pregunta}]
    if instrucciones.strip():
        mensajes.insert(0, {"role": "system", "content": instrucciones})
    encabezados = {"content-type": "application/json", "user-agent": f"mate/{VERSION}"}
    if clave:
        if not (clave.isascii() and clave.isprintable()) or " " in clave:
            raise error_de_ia("la clave guardada en MATE_IA_PROPIA_CLAVE tiene espacios o "
                              "letras raras (no la muestro por seguridad)")
        encabezados["authorization"] = "Bearer " + clave
    tardo = error(f"tu modelo tardó más de {IA_ESPERA // 60} minutos en contestar y dejé de "
                  "esperar. La primera consulta es la más lenta (tiene que cargarse): probá "
                  "de nuevo, o con un modelo más chico")
    codigo, crudo = 200, b""
    try:
        pedido = urllib.request.Request(
            direccion, headers=encabezados, method="POST",
            data=json.dumps({"model": modelo, "messages": mensajes, "stream": False,
                             "temperature": 0.2}).encode("utf-8"))
        if local:  # a un modelo de esta computadora se va directo, sin el proxy del sistema
            abrir = urllib.request.build_opener(urllib.request.ProxyHandler({})).open
        else:
            abrir = urllib.request.urlopen
        with abrir(pedido, timeout=IA_ESPERA) as respuesta:
            crudo = respuesta.read()
    except urllib.error.HTTPError as e:
        codigo = e.code
        try:
            crudo = e.read()
        except Exception:
            crudo = b""
    except (TimeoutError, socket.timeout):
        raise tardo
    except urllib.error.URLError as e:
        if isinstance(e.reason, (TimeoutError, socket.timeout)):
            raise tardo
        raise error(
            f"no pude conectarme con tu modelo en {lugar}. "
            + ("Fijate que el programa que lo corre esté abierto (con Ollama: que se vea su "
               "ícono al lado del reloj, o escribí  ollama list  en PowerShell)" if local
               else "Revisá la dirección de MATE_IA_PROPIA y que haya red"))
    except (OSError, http.client.HTTPException):
        raise error("se cortó la conexión con tu modelo antes de que llegara la respuesta")
    except (ValueError, TypeError):
        raise error("no pude armar la consulta para tu modelo con esos textos")
    try:
        datos = json.loads(crudo.decode("utf-8"))
    except (ValueError, UnicodeError):
        datos = None
    if codigo != 200:
        detalle = datos.get("error") if isinstance(datos, dict) else None
        dicho = detalle.get("message") if isinstance(detalle, dict) else detalle
        dicho = " ".join(tapar_clave(dicho if isinstance(dicho, str) else "", clave).split())[:300]
        original = f" (el servicio dijo: {dicho})" if dicho else ""
        if codigo == 404:
            raise error(f"tu servicio no conoce el modelo '{modelo}', o la dirección de "
                        "MATE_IA_PROPIA no es la de 'chat completions'. Con Ollama, los "
                        f"modelos que tenés los muestra:  ollama list{original}")
        if codigo in (401, 403):
            raise error("tu servicio no aceptó la clave (va en MATE_IA_PROPIA_CLAVE)"
                        + original)
        raise error(f"tu modelo contestó con un error (código {codigo}){original}")
    try:
        texto = datos["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        texto = None
    uso = datos.get("usage") if isinstance(datos, dict) else None
    partes = [uso.get(k) for k in ("prompt_tokens", "completion_tokens")] \
        if isinstance(uso, dict) else []
    _USO_DE_LA_IA["cobrada"] = True  # no se paga, pero cuenta para el tope por día
    _USO_DE_LA_IA["tokens"] = sum(partes) \
        if partes and all(type(n) is int and 0 <= n < 10 ** 12 for n in partes) else None
    if not isinstance(texto, str):
        raise error("tu modelo contestó algo que no pude entender (esperaba la forma de "
                    "'chat completions'). Revisá la dirección de MATE_IA_PROPIA")
    texto = re.sub(r"<think>.*?</think>", "", texto, flags=re.S).strip()
    if not texto:
        raise error("tu modelo contestó sin texto. Probá de nuevo o cambiá la pregunta")
    return texto


def pedir_a_la_ia(instrucciones, pregunta):
    """Le manda la consulta a Claude y devuelve el texto que contesta. Todo lo que puede
    salir mal es un ErrorMate en castellano, y la clave nunca aparece en ninguno."""
    import http.client
    import socket
    import ssl
    import time
    import urllib.error
    import urllib.request  # (usa el proxy del sistema: el de Windows o HTTPS_PROXY)

    propia = direccion_de_ia_propia()
    if propia:
        return pedir_a_la_ia_propia(propia, instrucciones, pregunta)
    clave, modelo = clave_de_ia(), modelo_de_ia()

    def error(texto):
        return error_de_ia(tapar_clave(texto, clave))

    tardo = error(f"la IA tardó más de {IA_ESPERA // 60} minutos en contestar y dejé de "
                  "esperar. Probá de nuevo, o con una pregunta más corta")
    reintentos = 0
    while True:
        respaldo = modelo in IA_CON_RESPALDO and modelo not in _IA_SIN_RESPALDO
        cuerpo = {"model": modelo, "max_tokens": IA_MAX_TOKENS,
                  "messages": [{"role": "user", "content": pregunta}]}
        encabezados = {"content-type": "application/json", "x-api-key": clave,
                       "anthropic-version": IA_VERSION, "user-agent": f"mate/{VERSION}"}
        if instrucciones.strip():
            cuerpo["system"] = instrucciones
        if respaldo:
            cuerpo["fallbacks"] = "default"
            encabezados["anthropic-beta"] = IA_RESPALDO
        codigo, cabeza, crudo, problema = 200, {}, b"", None
        try:
            pedido = urllib.request.Request(
                IA_DIRECCION, data=json.dumps(cuerpo).encode("utf-8"),
                headers=encabezados, method="POST")
            with urllib.request.urlopen(pedido, timeout=IA_ESPERA) as respuesta:
                crudo = respuesta.read()
        except urllib.error.HTTPError as e:  # Anthropic contestó, pero con un error
            codigo, cabeza = e.code, e.headers or {}
            try:
                crudo = e.read()
            except Exception:
                crudo = b""
        except (TimeoutError, socket.timeout):
            raise tardo
        except urllib.error.URLError as e:
            if isinstance(e.reason, (TimeoutError, socket.timeout)):
                raise tardo
            if isinstance(e.reason, ssl.SSLError):
                raise error(
                    "no pude armar una conexión segura con la IA (falló el certificado). "
                    "Suele ser un antivirus o la red de una oficina que revisa las "
                    "conexiones: probá desde otra red")
            problema = ("no pude conectarme con la IA: revisá que haya internet (y, si "
                        "estás en una oficina, que la red deje salir a api.anthropic.com)")
        except (OSError, http.client.HTTPException):
            problema = "se cortó la conexión con la IA antes de que llegara la respuesta"
        except (ValueError, TypeError):
            raise error("no pude armar la consulta para la IA con esos textos")
        try:
            datos = json.loads(crudo.decode("utf-8")) if not problema else None
        except (ValueError, UnicodeError):
            datos = None
        if problema is None and codigo == 200:
            # Llegó con código 200: Anthropic ya la cobró, aunque después no sirva (una
            # respuesta cortada se cobra entera). Se anota antes de revisarla.
            _USO_DE_LA_IA["cobrada"] = True
            _USO_DE_LA_IA["tokens"] = tokens_de(datos)
            return texto_de_la_ia(datos)
        detalle = datos.get("error") if isinstance(datos, dict) else None
        detalle = detalle if isinstance(detalle, dict) else {}
        dicho = detalle.get("message") if isinstance(detalle.get("message"), str) else ""
        dicho = tapar_clave(dicho, clave)  # antes de recortarlo: que no quede media clave
        detalles = detalle.get("details") if isinstance(detalle.get("details"), dict) else {}
        if codigo == 400 and respaldo and re.search("anthropic-beta|fallback", dicho, re.I):
            _IA_SIN_RESPALDO.add(modelo)  # esta cuenta no tiene el respaldo: va sin él
            continue
        de_nuevo = problema is not None or codigo in (408, 409, 429) or codigo >= 500
        if (detalles.get("error_code") == "enforced_spend_limit_reached"
                or str(cabeza.get("x-should-retry", "")).lower() == "false"):
            de_nuevo = False
        if de_nuevo and reintentos < IA_REINTENTOS:
            try:
                pausa = float(cabeza.get("retry-after") or 2 + 3 * reintentos)
            except (TypeError, ValueError):
                pausa = 2 + 3 * reintentos
            if 0 <= pausa <= IA_ESPERA_MAXIMA:
                reintentos += 1
                time.sleep(pausa)
                continue
        raise error(problema or explicar_error_de_ia(codigo, dicho, detalles, modelo))


def respuestas_de_archivo(ruta):
    """Lee el archivo de --ia-simulada=archivo. Cada renglón es
    'lo que trae la pregunta => lo que contesta la IA'; con * adelante, contesta eso a
    cualquier pregunta. Devuelve la lista de pares, o falla con un ErrorMate que explica."""
    try:
        contenido = leer_fuente(ruta)
    except FileNotFoundError:
        raise ErrorMate(f"no encuentro el archivo de respuestas '{ruta}'")
    except (OSError, ErrorMate):
        raise ErrorMate(f"no pude leer el archivo de respuestas '{ruta}'")
    pares = []
    for numero, renglon in enumerate(contenido.splitlines(), 1):
        if not renglon.strip() or renglon.strip().startswith("#"):
            continue
        si_trae, flecha, contesta = renglon.partition("=>")
        if not flecha or not si_trae.strip() or not contesta.strip():
            raise ErrorMate(
                f"{ruta}:{numero}: no entiendo este renglón del archivo de respuestas. Cada "
                "uno va así:  lo que trae la pregunta => lo que contesta la IA   (o  "
                "* => lo que contesta a todo lo demás)")
        pares.append((" ".join(sin_tildes(si_trae).lower().split()),
                      contesta.strip().replace("\\n", "\n")))
    if not pares:
        raise ErrorMate(f"el archivo de respuestas '{ruta}' está vacío. Cada renglón va así:  "
                        "lo que trae la pregunta => lo que contesta la IA")
    return pares


def respuesta_del_archivo(pares, pregunta):
    """Lo que contesta el archivo de --ia-simulada a esa pregunta (o None): el primer
    renglón cuyo texto esté en la pregunta y, si ninguno, el del asterisco."""
    buscada = " ".join(sin_tildes(pregunta).lower().split())
    for si_trae, contesta in pares:
        if si_trae != "*" and si_trae in buscada:
            return contesta
    for si_trae, contesta in pares:
        if si_trae == "*":
            return contesta
    return None


def recortado(texto, largo=70):
    """Un texto en un solo renglón y no muy largo, para la traza."""
    texto = " ".join(texto.split())
    return '"' + (texto if len(texto) <= largo else texto[:largo].rstrip() + "...") + '"'


# ─────────────── Lo que un agente aprende: memoria, lecciones y bitácora (0.4) ───────────────
# Todo vive en dos archivos al lado del programa, que se abren con el Bloc de notas:
# mi_mostrador.memoria.json (lo que cada agente recuerda y sus lecciones) y
# mi_mostrador.bitacora.txt (las fallas de los agentes). Solo los toca 'correr': con
# 'probar' no se leen ni se escriben. Nada de esto sale nunca por la red.

def archivo_de(ruta, que):
    """El archivo que acompaña a un programa: mi_mostrador.mate -> mi_mostrador.memoria.json
    (que es "memoria.json" o "bitacora.txt")."""
    for final in (".mate.txt", ".mate"):
        if ruta.lower().endswith(final):
            return f"{ruta[:-len(final)]}.{que}"
    return f"{ruta}.{que}"


def abrir_provisorio(provisorio, modo, **como):
    """Abre un archivo provisorio NUEVO para escribir (modo "x" o "xb"). Si ya había algo
    con ese nombre (uno viejo, o un acceso directo que alguien dejó ahí para que se escriba
    en otro lado) lo saca primero: nunca se escribe a través de un acceso directo."""
    for _ in range(3):
        try:
            if os.path.lexists(provisorio):
                os.remove(provisorio)  # (de un acceso directo saca el acceso, no el archivo)
            return open(provisorio, modo, **como)
        except FileExistsError:  # apareció de nuevo justo ahora: se prueba otra vez
            continue
    raise FileExistsError(f"no pude crear {provisorio}")


def nombre_provisorio(ruta):
    """El nombre del provisorio de ese archivo: 'memoria.json' -> 'memoria.json.123-ab12cd34.tmp',
    y el de un sobre del buzón 'id.json' -> 'id.123-ab12cd34.json.tmp' (sigue terminando en
    '.json.tmp', que es lo que el buzón reconoce como provisorio y limpia si quedó viejo).
    Lleva el número del proceso y unas letras al azar: dos ventanas que escriben el mismo
    archivo a la vez no comparten provisorio, así que ninguna le borra el suyo a la otra."""
    # Hasta la 0.7 el provisorio se llamaba siempre igual (el archivo más ".tmp"). Si quedó
    # uno de esos (de un corte, o un acceso directo que alguien dejó ahí), se saca: de un
    # acceso directo se saca el acceso, no el archivo al que apunta.
    try:
        if os.path.lexists(ruta + ".tmp"):
            os.remove(ruta + ".tmp")
    except OSError:
        pass
    marca = f"{os.getpid()}-{secrets.token_hex(4)}"
    if ruta.lower().endswith(".json") and os.path.basename(
            os.path.dirname(ruta)).lower().endswith(".buzon"):
        return f"{ruta[:-len('.json')]}.{marca}.json.tmp"
    return f"{ruta}.{marca}.tmp"


PROVISORIO_DE_MATE = re.compile(r"\.\d+-[0-9a-f]{8}(\.json)?\.tmp\Z")
LIMPIADAS = set()  # las carpetas donde esta corrida ya buscó provisorios viejos


def limpiar_provisorios_viejos(carpeta):
    """Saca de esa carpeta los provisorios de Mate (los de nombre_provisorio) de más de un
    día: quedaron de una corrida que murió justo entre crearlo y ponerle el nombre. Como
    llevan el número del proceso, la corrida siguiente ya no los pisa. Se mira una vez por
    carpeta y por corrida; lo que no tiene esa forma de nombre no se toca, y de un acceso
    directo se saca el acceso, no el archivo al que apunta."""
    carpeta = os.path.abspath(carpeta or ".")
    if carpeta in LIMPIADAS:
        return
    LIMPIADAS.add(carpeta)
    try:
        nombres = os.listdir(carpeta)
    except OSError:
        return
    ahora = time.time()
    for nombre in nombres:
        if not PROVISORIO_DE_MATE.search(nombre.lower()):
            continue
        completo = os.path.join(carpeta, nombre)
        try:
            datos = os.lstat(completo)
            if (stat.S_ISREG(datos.st_mode) or stat.S_ISLNK(datos.st_mode)) \
                    and ahora - datos.st_mtime > VIDA_DE_UN_PROVISORIO:
                os.remove(completo)
        except OSError:
            pass


def escribir_entero(ruta, texto):
    """Escribe el archivo de una sola vez: primero en uno provisorio al lado y recién
    después lo pone en su lugar. Así nunca queda a medio escribir."""
    limpiar_provisorios_viejos(os.path.dirname(ruta))
    provisorio = nombre_provisorio(ruta)
    try:
        # con la marca del principio, para que el Bloc de notas muestre bien las tildes
        with abrir_provisorio(provisorio, "x", encoding="utf-8-sig",
                              errors="backslashreplace") as f:
            f.write(texto)
        insistir(lambda: os.replace(provisorio, ruta))
    except BaseException:
        try:
            os.remove(provisorio)
        except OSError:
            pass
        raise


def insistir(hacer, veces=6):
    """Hace eso y, si el sistema contesta "no hay permiso", prueba de nuevo unas veces más
    (en total espera un tercio de segundo). En Windows, abrir un archivo justo cuando otro
    proceso lo está reemplazando, o reemplazar uno que otro proceso está leyendo en ese
    instante, da PermissionError, y se va solo enseguida. Si no se va, sale ese error."""
    pausa = 0.01
    for intento in range(veces):
        try:
            return hacer()
        except PermissionError:
            if intento == veces - 1:
                raise
            time.sleep(pausa)
            pausa *= 2


def leer_archivo_de_memoria(ruta):
    """El texto del archivo de memoria. Toda lectura de la memoria pasa por acá: la que
    se hace sin el candado tomado ('lecciones', 'ensayar', 'buzon', o una corrida que
    arranca mientras otra guarda) puede caer justo cuando otro proceso reemplaza el archivo,
    y en Windows eso da un "no hay permiso" que dura un instante (ver insistir)."""
    return insistir(lambda: leer_fuente(ruta))


def en_un_renglon(texto, largo):
    texto = " ".join(str(texto).split())
    return texto if len(texto) <= largo else texto[:largo].rstrip() + "..."


def leer_memoria(ruta):
    """Lo que dice el archivo de memoria: ({agente: {"estado": {...}, "lecciones": [...]}},
    avisos). Si no existe, nada. Si está roto (alguien lo editó a mano y quedó mal), un
    ErrorMate que dice dónde y cómo seguir: no se pisa un archivo que no se entiende."""
    nombre = os.path.basename(ruta)

    def roto(que):
        return ErrorMate(
            f"no entiendo el archivo de memoria {nombre}: {que}. Abrilo con el Bloc de notas "
            "y arreglalo; o borralo para empezar de cero (se pierde lo que recordaban los "
            f"agentes y también sus lecciones). Está en {os.path.dirname(os.path.abspath(ruta))}")

    def numero_raro(_):
        raise ValueError

    def decimal(t):
        return float(t) if math.isfinite(float(t)) else numero_raro(t)

    try:
        texto = leer_archivo_de_memoria(ruta)
    except FileNotFoundError:
        return {}, []
    except (OSError, ErrorMate):
        raise ErrorMate(f"no pude abrir el archivo de memoria {nombre}: fijate que no esté "
                        "abierto en otro programa y que tengas permiso para leerlo")
    if not texto.strip():
        return {}, []
    try:
        datos = json.loads(texto, parse_constant=numero_raro, parse_float=decimal)
    except json.JSONDecodeError as e:
        raise roto(f"en el renglón {e.lineno} hay algo mal escrito (suele ser una coma o "
                   "una comilla de más o de menos)")
    except (ValueError, RecursionError):
        raise roto("trae un número que no es válido, o demasiadas cosas una adentro de otra")
    agentes = datos.get("agentes") if isinstance(datos, dict) else None
    if not isinstance(agentes, dict):
        raise roto('le falta la parte "agentes"')
    limpio, avisos = {}, []
    for agente, ficha in agentes.items():
        if not isinstance(ficha, dict) or not isinstance(ficha.get("estado", {}), dict) \
                or not isinstance(ficha.get("lecciones", []), list):
            raise roto(f'lo que guarda de "{agente}" no tiene la forma de siempre (un '
                       '"estado" entre llaves y las "lecciones" entre corchetes)')
        lecciones = []
        for leccion in ficha.get("lecciones", []):
            if isinstance(leccion, str):  # escrita a mano, sin fecha: vale igual
                leccion = {"texto": leccion}
            dicho = leccion.get("texto") if isinstance(leccion, dict) else None
            if not isinstance(dicho, str) or not dicho.strip():
                avisos.append(f"en {nombre} hay una lección de {agente} que no se entiende "
                              '(le falta el "texto"): la salteo')
                continue
            if len(" ".join(dicho.split())) > LARGO_DE_LECCION:
                avisos.append(f"en {nombre} hay una lección de {agente} de más de "
                              f"{LARGO_DE_LECCION} letras: uso solo el principio")
            fecha = leccion.get("fecha")
            lecciones.append({"fecha": fecha if isinstance(fecha, str) else "",
                              "texto": en_un_renglon(dicho, LARGO_DE_LECCION)})
        if len(lecciones) > MAX_LECCIONES:
            avisos.append(f"en {nombre}, {agente} tiene más de {MAX_LECCIONES} lecciones, "
                          "que es el tope: me quedo con las más nuevas")
        limpio[str(agente)] = {"estado": dict(ficha.get("estado", {})),
                               "lecciones": lecciones[-MAX_LECCIONES:]}
        # Lo de la 0.5 (lecciones propuestas y cuenta de consultas) solo está si hay algo.
        propuestas = []
        for propuesta in ficha.get("propuestas", []) \
                if isinstance(ficha.get("propuestas"), list) else []:
            dicho = propuesta.get("texto") if isinstance(propuesta, dict) else None
            if not isinstance(dicho, str) or not dicho.strip():
                continue
            fecha, motivo = propuesta.get("fecha"), propuesta.get("motivo")
            propuestas.append({"fecha": fecha if isinstance(fecha, str) else "",
                               "texto": en_un_renglon(dicho, LARGO_DE_LECCION),
                               "motivo": en_un_renglon(motivo, 400)
                               if isinstance(motivo, str) else ""})
        if propuestas:
            limpio[str(agente)]["propuestas"] = propuestas[-MAX_PROPUESTAS:]
        gasto = gasto_limpio(ficha.get("gasto"))
        if gasto:
            limpio[str(agente)]["gasto"] = gasto
    return limpio, avisos


def leer_buzon_de_memoria(ruta):
    """La parte "buzon" del archivo de memoria (0.7): ({"recibidos": [...], "por_salir":
    [...]}, avisos). recibidos son los mensajes de otros programas que ya se atendieron
    ("programa/id") y por_salir los que este programa todavía tiene que dejar en el buzón
    de otro. Si el archivo no está, no se entiende o esa parte está mal armada, vale como
    vacía (con un aviso): nunca rompe la lectura de lo demás."""
    vacio = {"recibidos": [], "por_salir": []}
    try:
        datos = json.loads(leer_archivo_de_memoria(ruta))
    except (OSError, ErrorMate, ValueError, RecursionError):
        return vacio, []
    parte = datos.get("buzon") if isinstance(datos, dict) else None
    if parte is None:
        return vacio, []
    mal = (f'en {os.path.basename(ruta)}, la parte "buzon" no tiene la forma de siempre: '
           "no la uso (puede repetirse o perderse algún mensaje entre programas)")
    if not isinstance(parte, dict) or not isinstance(parte.get("recibidos", []), list) \
            or not isinstance(parte.get("por_salir", []), list):
        return vacio, [mal]
    recibidos = [r for r in parte.get("recibidos", []) if isinstance(r, str)]
    por_salir = []
    for pendiente in parte.get("por_salir", []):
        try:
            if not isinstance(pendiente, dict) \
                    or not carpeta_de_buzon_valida(pendiente.get("carpeta")):
                raise NoSeEntrega
            revisar_sobre(pendiente.get("sobre"))
            por_salir.append({"carpeta": pendiente["carpeta"], "sobre": pendiente["sobre"]})
        except NoSeEntrega:
            continue
    avisos = [mal] if len(recibidos) != len(parte.get("recibidos", [])) \
        or len(por_salir) != len(parte.get("por_salir", [])) else []
    return {"recibidos": recibidos, "por_salir": por_salir}, avisos


class MemoriaSinCandado(Exception):
    """Alguien quiso cambiar el archivo de memoria de un programa sin tener tomado su
    candado. Es un error de Mate, no del programa: la memoria no se escribe nunca así."""


# Los candados de memoria que tiene tomados ESTE proceso: la ruta del archivo de candado
# -> el archivo abierto con el candado tomado. Los anota tomar_candado_de_memoria y los
# saca soltar_candado_de_memoria; escribir_memoria mira acá antes de tocar nada.
_CANDADOS_DE_MEMORIA = {}


def clave_de_candado(ruta):
    return os.path.normcase(os.path.abspath(ruta))


def candado_de(archivo_memoria):
    """El archivo de candado de esa memoria: caja.memoria.json -> caja.memoria.candado."""
    if archivo_memoria.lower().endswith(".memoria.json"):
        return archivo_memoria[:-len("json")] + "candado"
    return archivo_memoria + ".candado"


def tengo_el_candado(archivo_memoria, candado):
    """¿Ese es el candado de esa memoria, y lo tiene tomado este proceso ahora mismo?"""
    return (candado is not None and not getattr(candado, "closed", True)
            and _CANDADOS_DE_MEMORIA.get(clave_de_candado(candado_de(archivo_memoria)))
            is candado)


def escribir_memoria(ruta, candado, texto=None, mover_a=None):
    """EL ÚNICO LUGAR de Mate que cambia el archivo de memoria de un programa
    (<programa>.memoria.json): lo escribe (texto), lo saca (sin texto) o lo deja aparte con
    otro nombre (mover_a). Se NIEGA, con MemoriaSinCandado y sin tocar nada, si el que
    llama no trae el candado de ESA memoria tomado por este proceso (el archivo que
    devolvió tomar_candado_de_memoria y todavía no se soltó).
    La regla es una sola: tomar el candado, LEER DE NUEVO la memoria del disco, aplicar el
    cambio sobre eso, escribir y soltar (o tener el candado toda la corrida). Escribir una
    copia leída antes de tomar el candado es pisar lo que otra ventana guardó en el medio:
    una caja volvería a vender la unidad que ya vendió."""
    if not tengo_el_candado(ruta, candado):
        raise MemoriaSinCandado(
            f"no se cambia {os.path.basename(ruta)} sin tener tomado su candado "
            f"({os.path.basename(candado_de(ruta))}): primero tomar_candado_de_memoria, "
            "después leer la memoria de nuevo y recién entonces escribirla")
    if mover_a is not None:
        insistir(lambda: os.replace(ruta, mover_a))
    elif texto is None:
        if os.path.lexists(ruta):
            insistir(lambda: os.remove(ruta))
    else:
        escribir_entero(ruta, texto)


def guardar_memoria(ruta, programa, agentes, buzon=None, candado=None, correo=None):
    """Deja la memoria en su archivo (o lo saca, si ya no hay nada que recordar). Devuelve
    None si salió bien o la explicación de por qué no se pudo.
    candado: el de esa memoria, TOMADO (ver escribir_memoria): sin él no se escribe, y lo
    que se guarda tiene que salir de lo que se leyó con el candado ya tomado.
    buzon: la parte del buzón entre programas (ver leer_buzon_de_memoria). Con None se
    CONSERVA la que haya en el archivo: así 'corregir', 'lecciones', 'proponer' y la cuenta
    de consultas guardan como siempre y no la pierden.
    correo: la parte de lo enviado y de los socios (0.8; ver leer_correo_de_memoria). Con
    None también se conserva la que haya."""
    if not tengo_el_candado(ruta, candado):
        escribir_memoria(ruta, candado)  # (se niega: MemoriaSinCandado)
    agentes = {a: f for a, f in agentes.items() if any(f.values())}
    try:
        if buzon is None and os.path.lexists(ruta):
            buzon = leer_buzon_de_memoria(ruta)[0]
        buzon = {k: list(v) for k, v in (buzon or {}).items() if v}
        if correo is None and os.path.lexists(ruta):
            correo = leer_correo_de_memoria(ruta)
        correo = {k: v for k, v in (correo or {}).items() if v}
        if not agentes and not buzon and not correo:
            escribir_memoria(ruta, candado)
            return None
        datos = {
            "que_es": f"La memoria de {programa}: lo que cada agente recuerda de una corrida "
                      "a la otra (estado) y las lecciones que aprendió. La escribe Mate "
                      "cada vez que el programa termina. Para empezar de cero: correr con "
                      "--olvidar.",
            "agentes": agentes}
        if buzon:  # (un programa sin buzón guarda lo mismo que antes, letra por letra)
            datos["buzon"] = {"recibidos": buzon.get("recibidos", []),
                              "por_salir": buzon.get("por_salir", [])}
        if correo:  # (lo mismo: solo si este programa manda por el buzón o tiene socios)
            datos["correo"] = correo
        escribir_memoria(ruta, candado, json.dumps(datos, ensure_ascii=False, indent=2,
                                                   allow_nan=False) + "\n")
    except (OSError, ValueError, RecursionError):
        return (f"no pude guardar la memoria en '{ruta}': lo que pasó en esta corrida no va "
                "a estar en la próxima. Fijate que el archivo no esté abierto en otro "
                "programa y que se pueda escribir en esa carpeta")
    return None


def fundir_memoria(leida, nueva, en_disco):
    """Lo que hay que guardar cuando el archivo de memoria cambió mientras el programa
    corría (desde otra ventana se anotó una lección con 'corregir', se aprobó una propuesta
    o corrió el mismo programa): lo que dice el archivo AHORA, más lo que sumó esta corrida
    respecto de lo que había leído al empezar. Así ninguna ventana pisa lo de la otra.
    - estado: el de esta corrida, si lo cambió; si no, el del archivo.
    - lecciones y propuestas: las del archivo, más las que esta corrida agregó.
    - cuenta de consultas: la del archivo, más las consultas que hizo esta corrida."""
    junta = json.loads(json.dumps(en_disco))
    for agente, ficha in nueva.items():
        antes = leida.get(agente, {})
        suya = junta.setdefault(agente, {"estado": {}, "lecciones": []})
        if ficha.get("estado", {}) != antes.get("estado", {}):
            suya["estado"] = ficha.get("estado", {})
        for que, tope in (("lecciones", MAX_LECCIONES), ("propuestas", MAX_PROPUESTAS)):
            ya = {x["texto"] for x in antes.get(que) or []} \
                | {x["texto"] for x in suya.get(que) or []} \
                | {x["texto"] for x in suya["lecciones"]}
            agregadas = [x for x in ficha.get(que) or [] if x["texto"] not in ya]
            if agregadas:
                suya[que] = (list(suya.get(que) or []) + agregadas)[-tope:]
        gasto = {dia: dict(cuenta) for dia, cuenta in (suya.get("gasto") or {}).items()}
        for dia, cuenta in (ficha.get("gasto") or {}).items():
            previa = (antes.get("gasto") or {}).get(dia, {})
            suma = gasto.setdefault(dia, {"consultas": 0, "simuladas": 0, "tokens": 0})
            for clave in ("consultas", "simuladas", "tokens"):
                suma[clave] = suma.get(clave, 0) + max(
                    0, cuenta.get(clave, 0) - previa.get(clave, 0))
        gasto = gasto_limpio(gasto)
        suya.pop("gasto", None)
        if gasto:
            suya["gasto"] = gasto
    return {a: f for a, f in junta.items() if any(f.values())}


# ───────────────────── Buzón entre programas (0.7) ─────────────────────
# Un agente de un programa le puede 'enviar' un mensaje a un agente de OTRO programa de la
# misma carpeta ('usar buzon "deposito.mate"'). El mensaje viaja en un "sobre" (un archivo
# JSON) que queda en la carpeta deposito.buzon, y se entrega cuando ese programa corre.
# - Lo que sale se anota primero en la memoria del que envía ("por salir"), junto con su
#   estado, en una sola escritura; después se reparte. Así un corte no deja un mensaje
#   enviado con el estado sin guardar, ni al revés.
# - Lo que llega se valida con el contrato del que recibe. Lo que no se entrega va a la
#   carpeta 'rechazados', intacto, con su motivo al lado.
# - Lo que identifica a un mensaje es (programa que lo manda, id): el que recibe anota los
#   que ya atendió y no los atiende dos veces.
VERSION_DE_BUZON = 1  # el número que va en "mate_buzon"
MAX_SOBRE = 2_000_000  # bytes: un archivo del buzón más pesado no se abre
MAX_MENSAJE_AL_BUZON = 1_000_000  # bytes del mensaje que sale para otro programa
MAX_SOBRES_POR_CORRIDA = 1000  # los que se atienden en una corrida; el resto espera
MAX_RECIBIDOS = 2000  # ids ya atendidos que se recuerdan (más los que siguen en el buzón)
MAX_NIVELES_DE_SOBRE = 100  # cosas una adentro de otra en un mensaje que llega
LARGO_DE_MOTIVO = 400  # letras del motivo de una falla que vuelve al que envió
VIDA_DE_UN_PROVISORIO = 86400  # segundos: un .tmp más viejo quedó de un corte y se borra
SUELTO_EN_EL_BUZON = "(programa)"  # así figura lo que mandó el programa, no un agente
_ID_DE_SOBRE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,119}")
_NO_VA_EN_UN_NOMBRE = frozenset('\\/:*?"<>|')


class NoSeEntrega(Exception):
    """Por qué un sobre del buzón no se entrega (el texto es el motivo)."""


def es_carpeta_de_verdad(ruta):
    return os.path.isdir(ruta) and not os.path.islink(ruta)


def nombre_de_programa_valido(nombre):
    """¿Sirve como nombre de un programa (o de su carpeta) en el buzón? Nada que pueda
    armar una ruta: ni barras, ni dos puntos, ni un punto adelante, ni CON o NUL."""
    return (isinstance(nombre, str) and 0 < len(nombre) <= 150 and nombre == nombre.strip()
            and not nombre.startswith(".") and not nombre.endswith(".")
            and not any(c in _NO_VA_EN_UN_NOMBRE or ord(c) < 32 for c in nombre)
            and nombre.split(".")[0].lower() not in _NOMBRES_DE_WINDOWS)


def carpeta_de_buzon_valida(nombre):
    return nombre_de_programa_valido(nombre) and nombre.lower().endswith(".buzon") \
        and len(nombre) > len(".buzon")


def revisar_lo_de_afuera(v, nivel=0):
    """Un mensaje que cruza entre programas no trae agentes (la forma reservada
    {"agente": ...}), ni números imposibles, ni demasiadas cosas una adentro de otra."""
    if nivel > MAX_NIVELES_DE_SOBRE:
        raise NoSeEntrega("trae demasiadas cosas una adentro de otra")
    if isinstance(v, dict):
        if set(v) in ({"agente"}, {"agente", "programa"}):
            raise NoSeEntrega('trae un mapa con la forma reservada de un agente ({"agente": '
                              "...}), y un mensaje entre programas todavía no puede llevar "
                              "agentes: usá otras claves")
        for x in v.values():
            revisar_lo_de_afuera(x, nivel + 1)
    elif isinstance(v, list):
        for x in v:
            revisar_lo_de_afuera(x, nivel + 1)
    elif type(v) is int and v.bit_length() > MAX_BITS:
        raise NoSeEntrega("trae un número demasiado grande")
    elif type(v) is float and not math.isfinite(v):
        raise NoSeEntrega("trae un número que no es válido")


def revisar_sobre(datos, hasta=None):
    """Controla que eso tenga la forma de un sobre del buzón. Lo que no conoce lo deja
    pasar (puede ser de una versión siguiente). hasta: la versión más nueva que vale ahí
    (en el buzón local, la 1; un sobre firmado entre negocios es de la 2)."""
    hasta = hasta or VERSION_DE_BUZON
    no_es = ("no es un sobre de Mate (le falta 'mate_buzon', 'id', 'clase', 'de', 'para' o "
             "'mensaje', o alguno no tiene la forma de siempre)")
    if not isinstance(datos, dict):
        raise NoSeEntrega(no_es)
    version = datos.get("mate_buzon")
    if type(version) is not int or version < 1:
        raise NoSeEntrega(no_es)
    if version == VERSION_DE_SOBRE_DE_SOCIO and hasta < version \
            and ("firma" in datos or "socio" in datos):
        raise NoSeEntrega(
            "es un sobre firmado de otro negocio (de socios) y está en el buzón local, "
            "donde no va: lo que manda un socio llega solo por la carpeta compartida, y "
            "Mate lo trae de ahí. No lo copies a mano al buzón")
    if version > hasta:
        raise NoSeEntrega(f"lo escribió una versión más nueva de Mate (dice mate_buzon: "
                          f"{version} y esta entiende hasta {hasta})")
    if not isinstance(datos.get("id"), str) or not _ID_DE_SOBRE.fullmatch(datos["id"]):
        raise NoSeEntrega("su 'id' no tiene la forma permitida (letras sin tilde, cifras, "
                          "punto, guion y guion bajo; hasta 120)")
    if datos.get("clase") not in ("mensaje", "falla"):
        raise NoSeEntrega(no_es)
    for lado in ("de", "para"):
        quien = datos.get(lado)
        if not isinstance(quien, dict) or not all(
                isinstance(quien.get(k), str) and 0 < len(quien[k]) <= 200
                and not any(ord(c) < 32 for c in quien[k]) for k in ("programa", "agente")):
            raise NoSeEntrega(no_es)
    if not nombre_de_programa_valido(datos["de"]["programa"]):
        raise NoSeEntrega("el nombre del programa que lo manda no sirve como nombre de "
                          "archivo")
    for clave in ("conversacion", "en_respuesta_a"):
        if datos.get(clave) is not None and not (
                isinstance(datos[clave], str) and _ID_DE_SOBRE.fullmatch(datos[clave])):
            raise NoSeEntrega(no_es)
    mensaje = datos.get("mensaje")
    bien = isinstance(mensaje, dict) and set(mensaje) == {"tipo", "campos"} \
        and isinstance(mensaje["tipo"], str) and isinstance(mensaje["campos"], dict)
    if datos["clase"] == "falla":
        if not isinstance(datos.get("motivo"), str):
            raise NoSeEntrega(no_es)
    elif not bien:
        raise NoSeEntrega('su "mensaje" no tiene la forma {"tipo": ..., "campos": {...}}')
    revisar_lo_de_afuera(mensaje)
    return datos


def abrir_sin_seguir(ruta):
    """Abre para leer un archivo del buzón UNA sola vez y sin seguir accesos directos, y
    controla sobre ese mismo archivo abierto (no sobre el nombre) que sea un archivo común.
    Así no hay un momento entre mirarlo y leerlo en que alguien lo pueda cambiar por un
    acceso directo a otro lado. Devuelve el archivo abierto ("rb"); OSError si no es un
    archivo común o no se puede abrir.
    - Donde el sistema lo tiene (Linux, macOS), O_NOFOLLOW hace que abrir un acceso directo
      falle. En Windows no existe: ahí, con el archivo ya abierto, se controla que ese
      archivo abierto sea el mismo que hay en la carpeta con ese nombre (y que ese nombre
      no sea un acceso directo): si en el medio lo cambiaron por un acceso directo a otro
      lado, lo abierto es lo de afuera y no coincide. (Sin probar en una Windows de verdad.)
    - O_NONBLOCK: una tubería con nombre de sobre no deja al programa esperando."""
    fd = os.open(ruta, os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
                 | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_NOCTTY", 0)
                 | getattr(os, "O_CLOEXEC", 0))
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise OSError(f"{ruta} no es un archivo común")
        if not hasattr(os, "O_NOFOLLOW") and (
                os.path.islink(ruta) or not es_el_de_la_carpeta(fd, ruta)):
            raise OSError(f"{ruta} es un acceso directo")
        f = os.fdopen(fd, "rb")
        fd = None
        return f
    finally:
        if fd is not None:
            os.close(fd)


def leer_sobre(ruta):
    """El sobre que hay en ese archivo del buzón, ya controlado. NoSeEntrega si no sirve;
    OSError si en este momento no se puede abrir, o si no es un archivo común (un acceso
    directo, una carpeta): no se atiende ni se borra, y se prueba de nuevo en otra corrida."""
    def raro(_):
        raise ValueError

    def decimal(t):
        return float(t) if math.isfinite(float(t)) else raro(t)

    with abrir_sin_seguir(ruta) as f:
        crudo = f.read(MAX_SOBRE + 1)
    if len(crudo) > MAX_SOBRE:
        raise NoSeEntrega("pesa más de 2 MB")
    try:
        datos = json.loads(crudo.decode("utf-8-sig"), parse_constant=raro,
                           parse_float=decimal)
    except (UnicodeError, json.JSONDecodeError):
        raise NoSeEntrega("no es un archivo JSON que se entienda")
    except (ValueError, RecursionError):
        raise NoSeEntrega("trae un número que no es válido, o demasiadas cosas una adentro "
                          "de otra")
    return revisar_sobre(datos)


class SinCandado(OSError):
    """Acá no se puede tener un candado, y no es porque lo tenga otra ventana. motivo:
    "sistema" (la carpeta está en un lugar donde el sistema no da candados: pasa en algunas
    carpetas de red) o "carpeta" (no hay un archivo de candado y no se puede crear: una
    carpeta donde no se puede escribir)."""
    def __init__(self, motivo, por_que=""):
        super().__init__(por_que)
        self.motivo = motivo


def candado_ocupado(e):
    """¿Ese error de pedir el candado quiere decir "lo tiene otro"? (Cualquier otro quiere
    decir que acá no hay candados: no es lo mismo, y no se puede avisar lo mismo.)"""
    ocupado = {errno.EACCES, errno.EAGAIN, getattr(errno, "EWOULDBLOCK", errno.EAGAIN),
               getattr(errno, "EDEADLK", errno.EAGAIN), getattr(errno, "EDEADLOCK", errno.EAGAIN)}
    return e.errno in ocupado


def tomar_candado(ruta):
    """El candado del buzón: lo tiene una sola ventana a la vez, y el sistema lo suelta si
    el programa muere. Devuelve el archivo abierto con el candado tomado, o None si lo
    tiene otra ventana. No espera. Un 'candado' que es un acceso directo no se sigue: se
    saca y se crea uno de verdad. Se crea como cualquier archivo de datos (0o666 menos lo
    que saque el sistema), sin permiso de ejecución: os.open(), si no se le dice, lo crea
    con 0o777.
    Lo que NO es "lo tiene otra ventana" sale como error, para que nadie lo confunda:
    - SinCandado("carpeta"): no hay archivo de candado y no se puede crear;
    - SinCandado("sistema"): el sistema no da candados en esa carpeta;
    - otro OSError: hay algo con ese nombre que no se puede usar de candado (una carpeta,
      una tubería, un archivo sobre el que no hay permiso).
    Si el archivo es de otro usuario del sistema y no se puede abrir para escribir, se abre
    para leer: el candado se toma igual, y es el mismo para los dos."""
    if os.path.islink(ruta):
        os.remove(ruta)
    como = (getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
            | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_NOCTTY", 0)
            | getattr(os, "O_CLOEXEC", 0))
    intentos = 0
    while True:
        try:
            fd = os.open(ruta, os.O_RDWR | os.O_CREAT | como, 0o666)
        except OSError as e:
            if not os.path.lexists(ruta):
                # (En Windows, abrir el candado justo cuando la corrida que lo tenía lo
                # está borrando da "no hay permiso", y un instante después el archivo ya
                # no está: eso no es una carpeta donde no se puede crear. Se prueba de
                # nuevo antes de decirlo.)
                intentos += 1
                if intentos < 4:
                    time.sleep(0.01)
                    continue
                raise SinCandado("carpeta", str(e))
            if not isinstance(e, PermissionError):
                raise
            fd = os.open(ruta, os.O_RDONLY | como)
        break
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise OSError(errno.EINVAL, "no es un archivo común", ruta)
        f = os.fdopen(fd, "rb", buffering=0)
        fd = None
    finally:
        if fd is not None:
            os.close(fd)
    try:
        if os.name == "nt":
            import msvcrt
            f.seek(0)
            msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError as e:
        f.close()
        if candado_ocupado(e):
            return None
        raise SinCandado("sistema", str(e))
    return f


def soltar_candado(f):
    try:
        if os.name == "nt":
            import msvcrt
            f.seek(0)
            msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    except OSError:
        pass
    finally:
        f.close()


def tomar_candado_de_memoria(ruta, espera=0.0):
    """El candado de la memoria de un programa (mi_negocio.memoria.candado, al lado del
    programa). Lo tiene una sola corrida a la vez y el sistema lo suelta solo si el proceso
    muere (es el mismo mecanismo que el candado del buzón). Devuelve el archivo abierto con
    el candado tomado, o None si lo tiene otra corrida y no lo soltó en 'espera' segundos.
    SinCandado si acá no se puede tener uno (ver tomar_candado), y otro OSError si con ese
    nombre hay algo que no se puede usar de candado. Cuando falla NO borra el archivo: solo
    lo borra, al soltar, la corrida que tiene el candado tomado.
    El archivo se borra al soltar; por eso, después de tomarlo, se controla que el archivo
    con candado sea el que está en la carpeta (otra corrida pudo borrarlo justo antes). En
    Windows ese control no hace falta: ahí un archivo que alguien tiene abierto no se borra."""
    limite = time.monotonic() + espera
    fallas = 0
    clave = clave_de_candado(ruta)
    while True:
        try:
            f = tomar_candado(ruta)
        except OSError as e:
            if getattr(e, "motivo", ""):
                # Acá no hay candados. El archivo NO se borra, aunque lo haya creado este
                # mismo intento: no se puede saber si otra corrida lo abrió y lo tiene
                # tomado (un fallo pasajero del sistema, o dos computadoras sobre la misma
                # carpeta de red donde una sola consigue candados). Si se borrara, esa
                # corrida seguiría con su candado sobre un archivo que ya no está en la
                # carpeta, y una tercera crearía otro y atendería a la vez. Un archivo
                # vacío de más no molesta: la próxima corrida lo usa.
                raise
            # (en Windows, abrir un archivo que otra corrida está borrando da un error que
            # se va solo; con varias corridas tomando y soltando a la vez puede repetirse)
            fallas += 1
            if fallas >= 10:
                raise
            time.sleep(0.02)
            continue
        if f is not None:
            if os.name == "nt" or es_el_de_la_carpeta(f, ruta):
                mio = _CANDADOS_DE_MEMORIA.get(clave)
                if mio is None or mio.closed:
                    _CANDADOS_DE_MEMORIA[clave] = f
                    return f
                # Este mismo proceso ya lo tenía tomado (otra corrida adentro del mismo
                # Python) y el sistema se lo dio de nuevo: hay sistemas donde el candado
                # es del proceso. Para Mate está ocupado igual: el candado es de UNA
                # corrida. Se devuelve este y se sigue como con cualquier candado ocupado.
                soltar_candado(f)
                f = None
            else:
                soltar_candado(f)  # ese archivo ya no es el que está en la carpeta: de nuevo
                fallas += 1
                if fallas >= 50:
                    raise OSError(f"no pude tomar {ruta}")
                continue
        if time.monotonic() >= limite:
            return None
        time.sleep(0.02)


def es_el_de_la_carpeta(f, ruta):
    """¿Ese archivo abierto es el que hoy está en la carpeta con ese nombre?"""
    try:
        mio = os.fstat(f if isinstance(f, int) else f.fileno())
        puesto = os.lstat(ruta)
    except OSError:
        return False
    return (mio.st_dev, mio.st_ino) == (puesto.st_dev, puesto.st_ino)


def soltar_candado_de_memoria(f, ruta):
    """Suelta el candado de la memoria y saca su archivo, para no dejar nada de más al lado
    del programa. (Si el proceso muere antes, el archivo queda y no molesta: sin candado.)"""
    if _CANDADOS_DE_MEMORIA.get(clave_de_candado(ruta)) is f:
        del _CANDADOS_DE_MEMORIA[clave_de_candado(ruta)]
    if os.name == "nt":  # en Windows no se borra un archivo abierto: primero se suelta
        soltar_candado(f)
        try:
            os.remove(ruta)
        except OSError:  # (ya lo abrió otra corrida: es de ella)
            pass
        return
    try:
        # Con el candado todavía tomado: nadie más lo tiene. (Si alguien borró el archivo a
        # mano y otra corrida ya creó el suyo, ese no es de esta: no se toca.)
        if es_el_de_la_carpeta(f, ruta):
            os.remove(ruta)
    except OSError:
        pass
    soltar_candado(f)


def por_que_no_se_tomo_el_candado(ruta, e):
    """(qué pasó, qué puede hacer el usuario), en castellano llano, cuando el candado de la
    memoria del programa 'ruta' no se pudo tomar y no es porque lo tenga otra ventana."""
    archivo_candado = archivo_de(ruta, "memoria.candado")
    motivo = getattr(e, "motivo", "")
    if motivo == "sistema":
        return (f"no pude tomar el candado de {os.path.basename(ruta)} "
                f"({os.path.basename(archivo_candado)}): en esta carpeta el sistema no "
                "da candados (pasa en algunas carpetas de red)",
                "Copiá la carpeta del programa a un disco de esta computadora (por "
                "ejemplo, adentro de Documentos) y corrélo desde ahí")
    if motivo == "carpeta":
        return (f"no pude crear {os.path.basename(archivo_candado)}, el archivo que "
                f"marca que {os.path.basename(ruta)} está abierto: en esta carpeta no "
                "se pueden crear archivos (no hay permiso para escribir, o el disco "
                "está lleno)",
                "Revisá los permisos de la carpeta, o copiala a un lugar donde puedas "
                "escribir (por ejemplo, adentro de Documentos) y corrélo desde ahí")
    nombre = os.path.basename(archivo_candado)
    if os.path.isdir(archivo_candado):
        que = "con ese nombre hay una carpeta"
    elif isinstance(e, PermissionError):
        que = "no tengo permiso para abrirlo (¿lo creó otro usuario de esta computadora?)"
    else:
        que = "con ese nombre hay algo que no es un archivo común"
    return (f"no pude tomar {nombre}, el archivo que marca que "
            f"{os.path.basename(ruta)} está abierto: {que}",
            "Si no hay ninguna otra ventana con este programa, borralo (o cambiale el "
            "nombre) y corré esto de nuevo")


ESPERA_DE_UNA_ORDEN = 3.0  # segundos que 'corregir' y compañía esperan el candado
# Lo que espera el candado un programa con 'estado recordado' al abrir. Si lo tiene otra
# ventana del programa, lo tiene toda la charla: no sirve esperar, se avisa enseguida. Pero
# 'corregir' y las demás órdenes que cambian la memoria lo tienen un instante, mientras
# leen y escriben: con esta espera, abrir justo en ese instante no da "ya hay otra ventana".
ESPERA_AL_ABRIR = 0.5


def pedir_candado_de_memoria(ruta, avisar, para_que, espera=None):
    """Para las órdenes que cambian la memoria de un programa sin correrlo ('corregir',
    'lecciones --borrar', 'proponer', 'propuestas aprobar/descartar' y las propuestas que
    deja 'ensayar'): toma el candado de la memoria de 'ruta', esperando un poco si lo tiene
    otra corrida. Devuelve el candado tomado (el que llama lee la memoria DE NUEVO, cambia
    eso, lo guarda y lo suelta con soltar_candado_de_memoria), o None después de avisar por
    qué no: ahí no se toca nada y la orden termina con código distinto de 0.
    para_que: lo que no se hizo, para el aviso ("no anoté la lección")."""
    nombre = os.path.basename(ruta)
    try:
        candado = tomar_candado_de_memoria(
            archivo_de(ruta, "memoria.candado"),
            ESPERA_DE_UNA_ORDEN if espera is None else espera)
    except OSError as e:
        que_paso, que_hacer = por_que_no_se_tomo_el_candado(ruta, e)
        avisar(f"{para_que}: {que_paso}. Sin candado no cambio la memoria de {nombre} "
               "(podría pisar lo que está anotando otra ventana). "
               f"{que_hacer}. Acá no se tocó nada")
        return None
    if candado is None:
        avisar(f"{para_que}: {nombre} está abierto en otra ventana, que anota en la misma "
               f"memoria ({os.path.basename(archivo_de(ruta, 'memoria.json'))}), y cambiarla "
               "ahora sería pisarle lo que guarde (una venta, por ejemplo). Cerrá la otra "
               "ventana y probá de nuevo. "
               # (Windows contesta lo mismo cuando el candado lo tiene otro que cuando una
               # carpeta de red no los da: no se distinguen.)
               + ("Si no hay ninguna otra ventana abierta, puede ser que esta carpeta no dé "
                  "candados (pasa en algunas carpetas de red): copiá la carpeta del "
                  "programa a un disco de esta computadora y probá desde ahí. "
                  if os.name == "nt" else "")
               + "Acá no se tocó nada")
    return candado


def tiene_estado_recordado(programa):
    """¿Algún agente del programa declara un 'estado recordado'?"""
    if isinstance(programa, EstadoRecordado):
        return True
    return isinstance(programa, (list, tuple)) \
        and any(tiene_estado_recordado(parte) for parte in programa)


def cuantos_mensajes(n):
    return "1 mensaje" if n == 1 else f"{n} mensajes"


class Buzon:
    """El buzón del programa que se corre con 'correr': lo que tiene por salir hacia otros
    programas y lo que le llegó. 'probar', 'verificar', 'ensayar' y la consola no arman
    ninguno, así que no leen ni escriben nada de esto."""

    _ultima_corrida = 0  # (en millonésimas de segundo: ver el id, abajo)

    def __init__(self, ruta, avisar=lambda texto: None):
        self.ruta = os.path.abspath(ruta)
        self.raiz = os.path.dirname(self.ruta)
        self.archivo = os.path.basename(ruta)
        self.programa = nombre_de_programa(ruta)
        self.carpeta = archivo_de(self.ruta, "buzon")
        self.avisar = avisar
        # El id de cada sobre: cuándo arrancó la corrida, 20 cifras hexadecimales y el
        # número de orden. Así los archivos quedan en el orden en que se enviaron, dentro
        # de una corrida y entre corridas del mismo programa: de las 20 cifras, las 5
        # primeras son las millonésimas de segundo de esa hora (dos corridas seguidas caen
        # en el mismo segundo) y las otras 15 van al azar. La hora es la universal, que no
        # salta para atrás con el cambio de hora.
        # (Si el reloj no llega a distinguir dos corridas hechas desde un mismo proceso,
        # la segunda se corre una millonésima: nunca queda igual ni antes.)
        momento = max(time.time_ns() // 1000, Buzon._ultima_corrida + 1)
        Buzon._ultima_corrida = momento
        cuando = datetime.datetime(1970, 1, 1) + datetime.timedelta(microseconds=momento)
        self.corrida = (f"{cuando:%Y%m%dT%H%M%S}-{cuando.microsecond:05x}"
                        f"{secrets.token_hex(8)[:15]}")
        self.atendio = False  # ¿llegó a atender lo que le dejaron? (si se corta, no)
        self.orden = 0
        self.leido = {"recibidos": [], "por_salir": []}  # lo que decía la memoria al empezar
        self.ya_recibidos = set()
        self.recibidos, self.por_salir = [], []  # lo nuevo de esta corrida
        self.repartidos = set()  # (carpeta, id) de lo que ya quedó en el buzón del otro
        self.atendidos, self.rechazos = [], []  # archivos a borrar, y (archivo, motivo) a mover
        self.candado = None
        self.cambio_la_memoria = lambda: (False, [])  # (lo pone 'correr')
        # ¿Se va a poder guardar lo que se atienda? (lo pone 'correr': toma el candado de
        # la memoria y se lo queda. True: lo tiene; None: lo tiene otra corrida; False: acá
        # no hay candados, y ya avisó)
        self.se_puede_guardar = lambda cuantos: True
        self.atendi, self.deje, self.no_entregados = {}, {}, 0  # para el resumen
        self._buscados = {}
        # (0.8) Los socios de 'usar socio', si el programa tiene; los mensajes que este
        # programa mandó por el buzón local ("programa/id": con eso reconoce un aviso de
        # falla de verdad) y los programas que ya averiguó si conoce.
        self.socios = None
        self.enviados = set()
        self.leer_correo = lambda: {"enviados": [], "socios": {}}  # (lo pone 'correr')
        self._conocidos = {}

    def conoce(self, de, ajenos, falla=False):
        """¿El que manda ese sobre es un programa que este programa conoce? (P161) True, o
        el motivo por el que no se entrega. Es conocido si este programa lo nombra con
        'usar buzon', o si en esta carpeta está ese programa y nombra a ESTE con 'usar
        buzon' (se lee sin ejecutarlo, una vez por corrida). Además el agente que dice
        mandarlo tiene que existir ahí. El buzón local no va firmado: en una misma PC,
        quien puede escribir en la carpeta puede editar los .mate."""
        programa, agente = de["programa"], de["agente"]
        clave = unicodedata.normalize("NFC", programa).casefold()
        if clave not in self._conocidos:
            self._conocidos[clave] = self._averiguar(programa, clave, ajenos)
        agentes = self._conocidos[clave]
        visto = texto_ajeno(programa, 60)
        if agentes is None:
            return (f"no conozco a '{visto}': para recibir de otro programa, ese programa "
                    f'tiene que tener usar buzon "{self.archivo}" (o este, usar buzon '
                    f'"{visto}.mate")')
        if agentes is True or falla or agente == SUELTO_EN_EL_BUZON or agente in agentes:
            return True  # (una falla viene a nombre del agente al que se le había escrito)
        return (f"dice venir de {texto_ajeno(agente, 60)}, y {self.visible(programa)} no "
                "tiene ningún agente con ese nombre")

    def _averiguar(self, programa, clave, ajenos):
        """None si ese programa no es conocido; si lo es, los nombres de sus agentes (o
        True si crea copias con 'crear', que llevan otros nombres). El otro programa se
        lee sin ejecutarlo y sin exigirle que esté entero: alcanza con lo que declara."""
        nombrados = {a.nombre for a in ajenos.values()
                     if a.socio is None and a.programa is not None
                     and unicodedata.normalize("NFC", a.programa).casefold() == clave}
        archivo = self.buscar(programa)[0]
        suyo = lo_que_declara(os.path.join(self.raiz, archivo)) if archivo else None
        me_nombra = False
        for escrito in (suyo or {}).get("buzones", ()):
            escrito = os.path.basename(escrito.strip().replace("\\", "/")).casefold()
            for final in (".mate.txt", ".mate"):
                if escrito.endswith(final):
                    escrito = escrito[:-len(final)]
                    break
            me_nombra = me_nombra or unicodedata.normalize("NFC", escrito) \
                == unicodedata.normalize("NFC", self.programa).casefold()
        if not nombrados and not me_nombra:
            return None
        if suyo is None:
            return nombrados
        if suyo["crea"]:
            return True
        return nombrados | suyo["agentes"]

    def correo_fundido(self, en_disco):
        """La parte "correo" que hay que guardar: la del archivo, más los ids de lo que
        esta corrida mandó por el buzón local, más lo de los socios (numerado y firmado)."""
        correo = json.loads(json.dumps(en_disco))
        ya = set(correo["enviados"])
        for pendiente in self.por_salir:
            sobre = pendiente["sobre"]
            clave = f"{sobre['para']['programa'].casefold()}/{sobre['id']}"
            if sobre["clase"] == "mensaje" and clave not in ya:
                ya.add(clave)
                correo["enviados"].append(clave)
        correo["enviados"] = correo["enviados"][-MAX_IDS_ENVIADOS:]
        if self.socios is not None:
            self.socios.cerrar(correo)
        return correo

    def buscar(self, programa):
        """(el archivo .mate, la carpeta del buzón) de ese programa, con los nombres tal
        como figuran en el listado de la carpeta. El nombre que viene en un sobre nunca
        se usa para armar una ruta: solo para compararlo con lo que hay."""
        clave = unicodedata.normalize("NFC", programa).casefold()
        if clave not in self._buscados:
            archivo = carpeta = None
            try:
                hay = sorted(os.listdir(self.raiz))
            except OSError:
                hay = []
            for nombre in hay:
                bajo = unicodedata.normalize("NFC", nombre).casefold()
                completo = os.path.join(self.raiz, nombre)
                if bajo in (clave + ".mate", clave + ".mate.txt") and os.path.isfile(completo):
                    archivo = archivo or nombre
                elif bajo == clave + ".buzon" and es_carpeta_de_verdad(completo):
                    carpeta = nombre
            if archivo and not carpeta:
                carpeta = os.path.basename(archivo_de(archivo, "buzon"))
            self._buscados[clave] = (archivo, carpeta)
        return self._buscados[clave]

    def visible(self, programa):
        """Cómo se nombra a ese programa en un aviso: 'ventas.mate' si está en la carpeta."""
        return self.buscar(programa)[0] or programa

    def nuevo_id(self):
        self.orden += 1
        return f"{self.corrida}-{self.orden:04d}"

    def sobre(self, de_agente, para_programa, para_agente, mensaje, conversacion=None,
              en_respuesta_a=None, falla=None, id=None):
        """Arma un sobre. falla: el motivo, si es el aviso de que un mensaje no se pudo
        atender (su id es el del mensaje original más '.falla': repetirlo no lo duplica)."""
        id = id or self.nuevo_id()
        sobre = {"mate_buzon": VERSION_DE_BUZON, "id": id,
                 "clase": "mensaje" if falla is None else "falla",
                 "de": {"programa": self.programa, "agente": de_agente},
                 "para": {"programa": para_programa, "agente": para_agente},
                 "conversacion": conversacion or id, "en_respuesta_a": en_respuesta_a,
                 "cuando": datetime.datetime.now().isoformat(timespec="seconds"),
                 "mensaje": mensaje}
        if falla is not None:
            sobre["motivo"] = en_un_renglon(falla, LARGO_DE_MOTIVO)
        return sobre

    def sale(self, carpeta, sobre):
        """Anota un sobre para otro programa. Sale de verdad al terminar, después de
        guardar la memoria."""
        self.por_salir.append({"carpeta": carpeta, "sobre": sobre})

    def dejar(self, carpeta, sobre):
        """Escribe un sobre en el buzón de otro programa: primero en un archivo provisorio
        y recién después con su nombre. Devuelve None, o por qué no se pudo."""
        if not carpeta_de_buzon_valida(carpeta):
            return f"'{carpeta}' no sirve como nombre de la carpeta de un buzón"
        destino = os.path.join(self.raiz, carpeta)
        if os.path.lexists(destino) and not es_carpeta_de_verdad(destino):
            return (f"{carpeta} existe y no es una carpeta: ahí va el buzón de ese programa. "
                    "Borralo o cambiale el nombre")
        final = os.path.join(destino, sobre["id"] + ".json")
        provisorio = None
        try:
            try:
                crudo = json.dumps(sobre, ensure_ascii=False, indent=2,
                                   allow_nan=False).encode("utf-8")
            except UnicodeError:  # una letra rota: va escrita con su número
                crudo = json.dumps(sobre, indent=2, allow_nan=False).encode("ascii")
            os.makedirs(destino, exist_ok=True)
            provisorio = nombre_provisorio(final)
            with abrir_provisorio(provisorio, "xb") as f:
                f.write(crudo)
            os.replace(provisorio, final)
        except (OSError, ValueError, RecursionError):
            try:
                if provisorio is not None:
                    os.remove(provisorio)
            except OSError:
                pass
            return (f"no pude escribir en {carpeta} (¿hay permiso para escribir en esa "
                    "carpeta?)")
        return None

    def repartir(self, pendientes):
        """Deja cada sobre pendiente en su buzón. Devuelve los que no se pudieron dejar
        (siguen anotados en la memoria y salen en la próxima corrida)."""
        quedan, problemas = [], {}
        for pendiente in pendientes:
            carpeta, sobre = pendiente["carpeta"], pendiente["sobre"]
            problema = self.dejar(carpeta, sobre)
            if problema:
                quedan.append(pendiente)
                problemas.setdefault(problema, []).append(pendiente)
                continue
            self.repartidos.add((carpeta, sobre["id"]))
            para = self.visible(sobre["para"]["programa"])
            self.deje[para] = self.deje.get(para, 0) + 1
        for problema, cuales in problemas.items():
            self.avisar(f"no pude dejar {cuantos_mensajes(len(cuales))} en el buzón de "
                        f"{self.visible(cuales[0]['sobre']['para']['programa'])}: "
                        f"{problema}. Queda anotado y sale la próxima vez que corra "
                        f"{self.archivo}")
        return quedan

    def esperan(self, limpiar=False):
        """Los sobres que hay en el buzón, en orden de nombre (que es el orden de envío)."""
        try:
            nombres = sorted(os.listdir(self.carpeta))
        except OSError:
            return []
        archivos = []
        for nombre in nombres:
            completo = os.path.join(self.carpeta, nombre)
            if nombre.lower().endswith(".json.tmp"):
                try:  # un provisorio viejo: quedó de un corte a mitad de una escritura
                    if limpiar and time.time() - os.path.getmtime(completo) \
                            > VIDA_DE_UN_PROVISORIO:
                        os.remove(completo)
                except OSError:
                    pass
            elif nombre.lower().endswith(".json") and os.path.isfile(completo) \
                    and not os.path.islink(completo):
                archivos.append(completo)
        return archivos

    def contar(self, recibidos=()):
        """Para informar, sin atender ni tocar nada: (cuántos mensajes esperan, por
        programa; cuántos archivos no se entienden; cuántos están repetidos o ya se
        atendieron, y se van a borrar sin entregar; cuántos quedaron sin mirar)."""
        ya, de_quien, raros, repetidos = set(recibidos), {}, 0, 0
        archivos = self.esperan()
        for archivo in archivos[:MAX_SOBRES_POR_CORRIDA]:
            try:
                sobre = leer_sobre(archivo)
            except (OSError, NoSeEntrega):
                raros += 1
                continue
            clave = f"{sobre['de']['programa'].casefold()}/{sobre['id']}"
            if clave in ya:
                repetidos += 1
                continue
            ya.add(clave)
            origen = self.visible(sobre["de"]["programa"])
            de_quien[origen] = de_quien.get(origen, 0) + 1
        return de_quien, raros, repetidos, max(0, len(archivos) - MAX_SOBRES_POR_CORRIDA)

    def intrusos(self):
        """Lo que hay en el buzón con nombre de mensaje (.json) y no es un archivo común
        (una carpeta, un acceso directo): Mate no lo atiende ni lo borra."""
        try:
            return [n for n in sorted(os.listdir(self.carpeta))
                    if n.lower().endswith(".json") and (
                        os.path.islink(os.path.join(self.carpeta, n))
                        or not os.path.isfile(os.path.join(self.carpeta, n)))]
        except OSError:
            return []

    def id_de_falla(self, id, ruta):
        """El id del aviso de que un mensaje no se pudo atender: el del mensaje más
        '.falla'. Si la corrida se corta y el rechazo se repite, sale el mismo id y el que
        envió no se entera dos veces. Si el mensaje ya se había rechazado y lo trajeron de
        nuevo desde 'rechazados', lleva además el número del intento: es otro aviso."""
        bases, veces = {id, os.path.basename(ruta)[:-len(".json")]}, 0
        try:
            for nombre in os.listdir(os.path.join(self.carpeta, "rechazados")):
                if not nombre.endswith(".motivo.txt"):
                    continue
                base = nombre[:-len(".motivo.txt")]
                veces += any(base == b or (base.startswith(b + "-")
                                           and base[len(b) + 1:].isdigit()) for b in bases)
        except OSError:
            pass
        final = ".falla" if not veces else f".falla-{veces + 1}"
        return id[:120 - len(final)] + final

    def abrir(self):
        """Lo que hay para atender en esta corrida: toma el candado y devuelve los
        archivos. Si no hay nada, o no se puede atender ahora, una lista vacía."""
        if not os.path.lexists(self.carpeta):
            return []
        nombre = os.path.basename(self.carpeta)
        if not es_carpeta_de_verdad(self.carpeta):
            self.avisar(f"{nombre} existe y no es una carpeta: ahí va el buzón de "
                        f"{self.archivo}, así que no puedo recibir mensajes. Borralo o "
                        "cambiale el nombre")
            return []
        esperan = self.esperan()
        if not esperan:
            return []
        # Atender es anotar en la memoria qué se atendió y qué se contesta: si el candado
        # de la memoria no se puede tomar, no se atiende nada y los mensajes quedan ahí.
        # (Si se pudo, la corrida se lo queda hasta terminar de guardar.)
        puede = self.se_puede_guardar(len(esperan))
        if puede is False:
            return []
        try:
            self.candado = tomar_candado(os.path.join(self.carpeta, "candado"))
        except OSError as e:
            if getattr(e, "motivo", "") == "sistema":
                self.avisar(f"en la carpeta de {self.archivo} el sistema no da candados "
                            "(pasa en algunas carpetas de red), y sin candado no atiendo "
                            f"el buzón ({nombre}): los mensajes quedan ahí. Poné los "
                            "programas en una carpeta común de esta computadora")
                return []
            self.avisar(f"no pude tomar el candado del buzón ({nombre}): los mensajes "
                        "quedan para la próxima corrida. Fijate que se pueda escribir en "
                        "esa carpeta")
            return []
        if self.candado is None:
            self.avisar(f"otra ventana de {self.archivo} está atendiendo el buzón; esta no "
                        "recibe mensajes")
            return []
        if not puede:
            # El candado de la memoria lo tiene otra corrida de este programa, y no lo
            # soltó: lo que se atendiera ahora no se podría anotar como atendido, y se
            # atendería de nuevo. No se atiende nada.
            cuantos = len(esperan)
            self.avisar(f"otra ventana de {self.archivo} tiene tomado el candado de la "
                        "memoria, y sin candado no atiendo el buzón (no podría anotar qué "
                        f"mensajes ya se atendieron): {cuantos_mensajes(cuantos)} "
                        f"{'queda' if cuantos == 1 else 'quedan'} en {nombre} y se "
                        f"{'atiende' if cuantos == 1 else 'atienden'} la próxima vez que "
                        f"{self.archivo} corra. Si quedó otra ventana de {self.archivo} "
                        "abierta, cerrala")
            self.soltar()
            return []
        cambio, recibidos = self.cambio_la_memoria()
        if cambio:
            self.avisar(f"otra ventana de {self.archivo} guardó cambios mientras esta "
                        "estaba abierta; los mensajes del buzón quedan para la próxima "
                        "corrida")
            self.soltar()
            return []
        self.ya_recibidos = set(self.leido["recibidos"]) | set(recibidos)
        archivos = self.esperan(limpiar=True)
        if len(archivos) > MAX_SOBRES_POR_CORRIDA:
            self.avisar(f"en el buzón hay {len(archivos)} mensajes y en una corrida se "
                        f"atienden hasta {MAX_SOBRES_POR_CORRIDA}: el resto queda para la "
                        "próxima")
            archivos = archivos[:MAX_SOBRES_POR_CORRIDA]
        return archivos

    def soltar(self):
        if self.candado is not None:
            soltar_candado(self.candado)
            self.candado = None

    def donde_van_los_rechazados(self):
        return os.path.join(os.path.basename(self.carpeta), "rechazados")

    def cambio(self):
        """¿En esta corrida pasó algo con el buzón (para guardar, repartir, mover o borrar)?"""
        return bool(self.recibidos or self.por_salir or self.repartidos
                    or self.rechazos or self.atendidos
                    or (self.socios is not None and self.socios.cambio()))

    def fundido(self, en_disco):
        """La parte "buzon" que hay que guardar: lo que dice el archivo ahora, más lo de
        esta corrida, menos lo que esta corrida ya repartió."""
        def clave(pendiente):
            return (pendiente["carpeta"], pendiente["sobre"]["id"])

        recibidos = list(en_disco["recibidos"])
        ya = set(recibidos)
        recibidos += [r for r in self.recibidos if r not in ya]
        if len(recibidos) > MAX_RECIBIDOS:  # los últimos, y los que siguen en el buzón
            recibidos = [r for r in recibidos[:-MAX_RECIBIDOS] if os.path.lexists(
                os.path.join(self.carpeta, r.rpartition("/")[2] + ".json"))] \
                + recibidos[-MAX_RECIBIDOS:]
        por_salir = [p for p in en_disco["por_salir"] if clave(p) not in self.repartidos]
        ya = {clave(p) for p in por_salir}
        por_salir += [p for p in self.por_salir
                      if clave(p) not in ya and clave(p) not in self.repartidos]
        return {"recibidos": recibidos, "por_salir": por_salir}

    def acomodar(self):
        """Después de guardar la memoria: mueve lo rechazado y borra lo atendido. Lo que
        Windows no deje mover o borrar ahora queda, y se resuelve en la corrida siguiente."""
        for ruta, motivo in self.rechazos:
            self.mover_a_rechazados(ruta, motivo)
        for ruta in self.atendidos:
            try:
                os.remove(ruta)
            except OSError:
                pass
        self.rechazos, self.atendidos = [], []

    def mover_a_rechazados(self, ruta, motivo):
        """El archivo va intacto a 'rechazados' (sin pisar otro) y al lado queda el motivo."""
        carpeta = os.path.join(self.carpeta, "rechazados")
        if os.path.lexists(carpeta) and not es_carpeta_de_verdad(carpeta):
            return
        base = os.path.basename(ruta)[:-len(".json")]
        try:
            os.makedirs(carpeta, exist_ok=True)
            nombre, n = base, 1
            while os.path.lexists(os.path.join(carpeta, nombre + ".json")) \
                    or os.path.lexists(os.path.join(carpeta, nombre + ".motivo.txt")):
                n += 1
                nombre = f"{base}-{n}"
            os.rename(ruta, os.path.join(carpeta, nombre + ".json"))
            escribir_entero(os.path.join(carpeta, nombre + ".motivo.txt"), (
                f"Mate no entregó este mensaje ({datetime.datetime.now():%d/%m/%Y %H:%M}).\n"
                f"Motivo: {motivo}\n"
                f"Para intentarlo de nuevo, mové {nombre}.json a la carpeta de arriba "
                f"({os.path.basename(self.carpeta)}) y corré {self.archivo}.\n"))
        except (OSError, ValueError):
            pass

    def resumen(self):
        """Los renglones que cuentan qué pasó con el buzón en esta corrida (o ninguno)."""
        renglones = []
        total = sum(self.atendi.values())
        mal = ""
        if self.no_entregados:
            mal = (f"{self.no_entregados} no se "
                   f"{'pudo' if self.no_entregados == 1 else 'pudieron'} entregar: "
                   f"{'está' if self.no_entregados == 1 else 'están'} en "
                   f"{self.donde_van_los_rechazados()}.")
        if total:
            de = ", ".join(f"{n} de {programa}" for programa, n in self.atendi.items())
            renglones.append(f"Buzón: atendí {cuantos_mensajes(total)} ({de})."
                             + (f" Además, {mal}" if mal else ""))
        elif mal:
            renglones.append(f"Buzón: {mal}")
        for programa, n in self.deje.items():
            renglones.append(f"Buzón: dejé {cuantos_mensajes(n)} para {programa}; "
                             f"{'le llega' if n == 1 else 'le llegan'} la próxima vez que "
                             "corra.")
        if self.socios is not None:
            renglones += self.socios.resumen()
        return renglones


# ───────────────── Socios: agentes de negocios distintos (0.8) ─────────────────
# 'usar socio Proveedor acepta Cotizacion' deja que este programa se hable con el de OTRO
# negocio, en otra máquina. Mate no abre conexiones ni levanta servidores: los dos negocios
# comparten una CARPETA (sincronizada, de red o un pendrive) y ahí viajan los sobres.
# - Cada par de socios acuerda una clave. Vive en <programa>.socios.json, al lado del
#   programa (nunca en el .mate, ni en la carpeta compartida, ni en pantalla, ni en la traza).
# - Cada sobre va FIRMADO (hmac-sha256) con una clave derivada por sentido (lado A o B), y
#   lleva un número de orden por socio: así no se falsifica, no se devuelve y no se repite.
# - Lo que no trae la firma de ese socio no se entrega ni se contesta: va a 'rechazados'.
# - Nada de otro negocio llega a un agente sin el si del dueño, mensaje por mensaje.
# - El contenido NO va cifrado: quien ve la carpeta compartida lee los mensajes.
VERSION_DE_SOBRE_DE_SOCIO = 2  # el "mate_buzon" de un sobre entre negocios
MAX_MENSAJE_DE_SOCIO = 8000  # bytes de un mensaje entre negocios (entra entero en pantalla)
MAX_TEXTO_DE_SOCIO = 500  # letras de un texto adentro de un mensaje entre negocios
MAX_NIVELES_DE_SOCIO = 4  # cosas una adentro de otra en un mensaje entre negocios
MAX_PENDIENTES_POR_SOCIO = 200  # mensajes de un socio esperando el si; el resto espera afuera
MAX_EN_ESPERA = 200  # mensajes para un socio sin clave (o frenado) que quedan anotados
MAX_VISTOS = 2000  # números de sobre ya vistos que se recuerdan por socio
MAX_IDS_ENVIADOS = 2000  # ids de lo enviado que se recuerdan (para reconocer una falla)
MAX_RECHAZADOS_DE_SOCIO = 50  # archivos de un socio en 'rechazados'; después solo se cuenta
MAX_PESO_DE_RECHAZADOS = 20_000_000  # ...o estos bytes
MAX_A_MEDIO_LLEGAR = 500  # archivos que no se entienden y se siguen mirando, por socio
MAX_MIRADOS_POR_CORRIDA = 5000  # archivos de la carpeta compartida que se miran por socio
ESPERA_DE_UN_ROTO = 86400  # segundos (de ESTA máquina) antes de dar por roto un archivo
MAX_NUMERO_DE_SOBRE = 2 ** 53
MAX_NUMERO_A_LA_VISTA = 60  # letras de un número entre negocios, como se le muestra al dueño
LARGO_DE_CLAVE = 44  # 40 cifras al azar y 4 de control
MAX_CLAVES_DE_ANTES = 5  # huellas de claves anteriores que se recuerdan por socio
CIFRAS_DISTINTAS_DE_CLAVE = 6  # menos cifras distintas que estas, no es una clave al azar
# Los motivos de una falla entre negocios: viaja el código, y cada lado lo dice con su texto.
MOTIVOS_DE_SOCIO = {
    "contrato": "no cumple el contrato de tu socio",
    "no_acepto": "tu socio no acepta ese tipo de mensaje",
    "descartado": "el dueño lo descartó",
    "fallo": "el programa de tu socio falló al atenderlo",
}
_FIRMA = re.compile(r"[0-9a-f]{64}")
_HUELLA = re.compile(r"[0-9a-f]{8}")
_SOBRE_EN_COMPARTIDA = re.compile(r"([0-9]{8,16})-[0-9a-f]{8}\.json")
_PENDIENTE_DE_SOCIO = re.compile(r"s([0-9a-f]{8})-([0-9]{8,16})\.json")
_NOMBRE_DE_CAMPO = re.compile(r"[^\W\d]\w{0,40}")
LEEME_DE_COMPARTIDA = "LEEME-mate.txt"
TEXTO_DEL_LEEME = (
    "Esta carpeta la usan dos programas de Mate, de dos negocios, para mandarse mensajes.\n"
    "- En de-a escribe uno y en de-b el otro. Cada archivo es un mensaje firmado.\n"
    "- No edites, renombres ni copies acá adentro: Mate lee y borra lo que le toca.\n"
    "- Los mensajes NO van cifrados: quien ve esta carpeta los puede leer.\n"
    "- La clave de los socios NO va acá, nunca. Tampoco los programas (.mate).\n")


def reloj_local():
    """La hora de ESTA máquina, en segundos (aparte, para que las pruebas la adelanten)."""
    return time.time()


def texto_ajeno(texto, largo=200, entre_comillas=False):
    """Un texto que viene de AFUERA (de un sobre, o el nombre de un archivo ajeno), listo
    para mostrar o anotar: lo que no se ve o engaña al ojo va escrito con su número
    (\\u202e): los caracteres de control, los de dirección de texto y demás de formato, los
    saltos raros, las letras rotas (sustitutos sueltos) y lo que esta consola no sabe
    escribir. Y con un largo máximo. entre_comillas: además escapa la comilla y la barra,
    para que un valor no pueda cerrar su comilla y dibujar otro campo."""
    texto = texto if isinstance(texto, str) else str(texto)
    consola = getattr(sys.stdout, "encoding", None) or "utf-8"
    partes = []
    for c in texto[:largo]:
        if entre_comillas and c in '"\\':
            partes.append("\\" + c)
            continue
        visible = c == " " or c.isprintable()
        if visible and not c.isascii():
            try:
                c.encode(consola)
            except (UnicodeError, LookupError):
                visible = False
        partes.append(c if visible else (
            f"\\u{ord(c):04x}" if ord(c) < 0x10000 else f"\\U{ord(c):08x}"))
    return "".join(partes) + ("..." if len(texto) > largo else "")


def valor_ajeno(v):
    """Un valor que vino de otro negocio, como se le muestra al dueño antes del si: igual
    que en la traza, pero con los textos entre comillas y limpios (ver texto_ajeno)."""
    if isinstance(v, str):
        return '"' + texto_ajeno(v, MAX_TEXTO_DE_SOCIO, True) + '"'
    if isinstance(v, list):
        return "[" + ", ".join(valor_ajeno(x) for x in v) + "]"
    if isinstance(v, dict):
        return "{" + ", ".join(f"{texto_ajeno(k, 60)}: {valor_ajeno(x)}"
                               for k, x in v.items()) + "}"
    if isinstance(v, Registro):
        return texto_ajeno(v.tipo, 60) + " { " + ", ".join(
            f"{texto_ajeno(k, 60)}: {valor_ajeno(x)}" for k, x in v.campos.items()) + " }"
    return texto_ajeno(formato(v, False), MAX_NUMERO_A_LA_VISTA)


# ── la clave ──
def control_de_clave(cifras):
    """Las 4 cifras de control de una clave (salen de las otras 40): si al dictarla se
    cambia una cifra, no coinciden."""
    resumen = hashlib.sha256(("mate-socio-1 clave " + cifras).encode("ascii")).hexdigest()
    return f"{int(resumen, 16) % 10000:04d}"


def nueva_clave_de_socio():
    """40 cifras al azar (unos 133 bits), de a una, más las 4 de control. Van cifras y no
    letras porque se dictan por teléfono sin confundir B con V."""
    while True:
        cifras = "".join(str(secrets.randbelow(10)) for _ in range(LARGO_DE_CLAVE - 4))
        if len(set(cifras)) >= CIFRAS_DISTINTAS_DE_CLAVE:  # (al azar pasa siempre)
            return cifras + control_de_clave(cifras)


def clave_de_socio_valida(texto):
    """La clave limpia (44 cifras) si eso es una clave bien escrita; si no, None. Se acepta
    con espacios o guiones entre los grupos. Nada de frases elegidas a mano, ni una clave
    "fácil" armada a mano (todos ceros con su control): una clave al azar nunca trae tan
    pocas cifras distintas."""
    if not isinstance(texto, str):
        return None
    cifras = re.sub(r"[\s\-]", "", texto)
    if len(cifras) != LARGO_DE_CLAVE or not (cifras.isascii() and cifras.isdigit()):
        return None
    if len(set(cifras[:-4])) < CIFRAS_DISTINTAS_DE_CLAVE:
        return None
    return cifras if hmac.compare_digest(control_de_clave(cifras[:-4]), cifras[-4:]) else None


def clave_en_grupos(clave):
    return " ".join(clave[i:i + 4] for i in range(0, len(clave), 4))


def _derivada(clave, que):
    return hmac.new(clave.encode("ascii"), ("mate-socio-1 " + que).encode("ascii"),
                    hashlib.sha256).digest()


def huella_de_clave(clave):
    """8 letras que identifican la clave sin decir nada de ella: van en cada sobre."""
    return _derivada(clave, "huella").hex()[:8]


def control_de_socio(clave):
    """El "número de control": 6 cifras que los dos socios ven iguales si cargaron la misma
    clave. Es lo único de la clave que se muestra."""
    numero = f"{int.from_bytes(_derivada(clave, 'control'), 'big') % 1000000:06d}"
    return f"{numero[:3]} {numero[3:]}"


def bytes_canonicos(sobre):
    """Los bytes que se firman: el sobre entero menos "firma", escrito de una sola manera.
    ValueError o RecursionError si no se puede."""
    sin_firma = {k: v for k, v in sobre.items() if k != "firma"}
    return b"mate-sobre-2\n" + json.dumps(
        sin_firma, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        allow_nan=False).encode("ascii")


def firma_de_sobre(sobre, clave, lado):
    """La firma de ese sobre hecha por ese lado ("A" o "B"). Cada lado firma con una clave
    derivada distinta: un sobre mío que me devuelven no verifica como del otro."""
    return hmac.new(_derivada(clave, "firma " + lado), bytes_canonicos(sobre),
                    hashlib.sha256).hexdigest()


def huella_de_mensaje(mensaje):
    try:
        crudo = json.dumps(mensaje, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (ValueError, RecursionError, TypeError):
        return ""
    return hashlib.sha256(crudo.encode("ascii")).hexdigest()[:16]


def demasiado_hondo(v, tope=MAX_NIVELES_DE_SOBRE):
    """¿Trae más cosas una adentro de otra que el tope? (sin recursión)"""
    pila = [(v, 0)]
    while pila:
        x, nivel = pila.pop()
        if nivel > tope:
            return True
        if isinstance(x, dict):
            pila.extend((y, nivel + 1) for y in x.values())
        elif isinstance(x, list):
            pila.extend((y, nivel + 1) for y in x)
    return False


def json_de_sobre(crudo):
    """Lo que dice ese archivo, y si trae claves repetidas (en JSON valen, y cada programa
    se queda con una distinta: en un sobre firmado no se aceptan). ValueError si no es JSON
    (UnicodeError y JSONDecodeError lo son) y RecursionError si es demasiado hondo."""
    repetidas = []

    def pares(lista):
        mapa = {}
        for k, v in lista:
            if k in mapa:
                repetidas.append(k)
            mapa[k] = v
        return mapa

    def raro(_):
        raise ArithmeticError

    def decimal(t):
        return float(t) if math.isfinite(float(t)) else raro(t)

    try:
        datos = json.loads(crudo.decode("utf-8-sig"), object_pairs_hook=pares,
                           parse_constant=raro, parse_float=decimal)
    except ArithmeticError:
        return None, False  # (un número imposible: es JSON, pero no un sobre)
    return datos, bool(repetidas)


TEXTO_QUE_NO_SE_VE = (
    "trae un texto con algo que en pantalla no se ve o engaña al ojo (un salto de renglón, "
    "un tabulador, un carácter de control o de dirección de texto): entre negocios los "
    "textos van en un solo renglón y sin esos caracteres")


def no_se_ve_o_engana(texto):
    """¿Ese texto trae algo que texto_ajeno escribiría con su número? (sin mirar la consola:
    lo mismo en las dos máquinas). Eso no viaja entre negocios, ni de ida ni de vuelta: un
    texto así, una vez entregado, lo imprime un 'mostrar' del agente tal cual, y con un
    retorno de carro y un color se dibuja una pregunta falsa en la pantalla del dueño."""
    return any(not (c == " " or c.isprintable()) for c in texto)


def no_entra_de_socio(mensaje):
    """Por qué ese mensaje ({"tipo", "campos"}) no puede viajar entre negocios, o None. Los
    topes son mucho más chicos que los del buzón local: lo que llega de otro negocio se le
    muestra ENTERO al dueño antes del si, y lo que no entra en pantalla no se recorta: se
    rechaza. Tampoco viajan los textos con caracteres que no se ven o engañan al ojo."""
    try:
        pesa = len(json.dumps(mensaje, ensure_ascii=False, allow_nan=False)
                   .encode("utf-8", "replace"))
    except (ValueError, RecursionError, TypeError):
        return "trae algo que no se puede revisar"
    if pesa > MAX_MENSAJE_DE_SOCIO:
        return (f"pesa más de {MAX_MENSAJE_DE_SOCIO // 1000} KB, que es el tope de un "
                "mensaje entre negocios")
    if isinstance(mensaje.get("tipo"), str) and no_se_ve_o_engana(mensaje["tipo"]):
        return TEXTO_QUE_NO_SE_VE
    pila = [(mensaje.get("campos"), 1)]
    while pila:
        x, nivel = pila.pop()
        if nivel > MAX_NIVELES_DE_SOCIO:
            return (f"trae más de {MAX_NIVELES_DE_SOCIO} cosas una adentro de otra, que es "
                    "el tope entre negocios")
        if isinstance(x, str) and len(x) > MAX_TEXTO_DE_SOCIO:
            return (f"trae un texto de más de {MAX_TEXTO_DE_SOCIO} letras, que es el tope "
                    "entre negocios")
        if isinstance(x, str) and no_se_ve_o_engana(x):
            return TEXTO_QUE_NO_SE_VE
        if es_num(x) and len(formato(x, False)) > MAX_NUMERO_A_LA_VISTA:
            # (0.8.1) Un número tan largo no entra en la pregunta "¿Lo entrego?": antes se
            # mostraba recortado y el agente lo recibía entero.
            return (f"trae un número de más de {MAX_NUMERO_A_LA_VISTA} cifras, que no "
                    "entra en pantalla")
        if isinstance(x, dict):
            if any(not isinstance(k, str) or len(k) > 60 for k in x):
                return "trae un nombre de campo demasiado largo"
            if any(no_se_ve_o_engana(k) for k in x):
                return TEXTO_QUE_NO_SE_VE
            pila.extend((y, nivel + 1) for y in x.values())
        elif isinstance(x, list):
            pila.extend((y, nivel + 1) for y in x)
    return None


# ── el archivo de las claves ──
def es_archivo_de_clave(ruta):
    """¿Ese archivo es de los que guardan la clave de un socio (<programa>.socios.json, su
    provisorio o una invitación)? Se mira el nombre escrito y el del archivo de verdad (si
    es un acceso directo), sin distinguir mayúsculas, y como lo ve Windows: sin los puntos
    y espacios del final y sin el "::$DATA"."""
    nombres = {os.path.basename(str(ruta).replace("\\", "/"))}
    try:
        nombres.add(os.path.basename(os.path.realpath(ruta)))
    except (OSError, ValueError):
        pass
    for nombre in nombres:
        nombre = nombre.split(":", 1)[0].rstrip(". ").casefold()
        if ".socios.json" in nombre or re.fullmatch(r"invitacion-mate.*\.txt.*", nombre):
            return True
    return False


NO_SE_LEE_LA_CLAVE = ("'{n}' guarda la clave de un socio y Mate no lo abre, no lo muestra ni "
                      "lo escribe desde un programa: lo maneja solo la orden 'socio'")


def leer_socios(ruta_programa):
    """Las claves cargadas de ese programa: ({socio: {"clave", "lado", "carpeta",
    "estrenado", "ensayo", "antes"}}, problema o None). Sin archivo, ninguna. "antes" son
    las HUELLAS (no las claves) de las últimas claves que hubo con ese socio, y el lado que
    este programa tenía con cada una: con eso reconoce lo suyo que quedó viajando firmado
    con una clave que ya no vale (ver Socios.sacar_lo_mio_que_no_vale)."""
    archivo = archivo_de(ruta_programa, "socios.json")
    nombre = os.path.basename(archivo)
    try:
        with abrir_sin_seguir(archivo) as f:
            crudo = f.read(1_000_001)
    except FileNotFoundError:
        return {}, None
    except OSError:
        return {}, (f"no pude abrir {nombre} (las claves de los socios): fijate que sea un "
                    "archivo común y que tengas permiso para leerlo")
    roto = (f"no entiendo {nombre} (las claves de los socios). No se arregla a mano: "
            "movelo a otro lado y cargá las claves de nuevo con 'socio renovar' de un lado y "
            "'socio aceptar' del otro")
    try:
        datos = json.loads(crudo.decode("utf-8-sig"))
    except (ValueError, RecursionError):
        return {}, roto
    socios = datos.get("socios") if isinstance(datos, dict) else None
    if not isinstance(socios, dict):
        return {}, roto
    fichas, mal = {}, False
    for socio, ficha in socios.items():
        clave = clave_de_socio_valida(ficha.get("clave")) if isinstance(ficha, dict) else None
        if clave is None or ficha.get("lado") not in ("A", "B") \
                or not isinstance(ficha.get("carpeta"), str) or not ficha["carpeta"]:
            mal = True
            continue
        fichas[socio] = {"clave": clave, "lado": ficha["lado"], "carpeta": ficha["carpeta"],
                         "estrenado": ficha.get("estrenado") is True}
        if ficha.get("ensayo") is True:
            fichas[socio]["ensayo"] = True
        antes = [{"huella": a["huella"], "lado": a["lado"]}
                 for a in (ficha.get("antes") if isinstance(ficha.get("antes"), list) else ())
                 if isinstance(a, dict) and isinstance(a.get("huella"), str)
                 and _HUELLA.fullmatch(a["huella"]) and a.get("lado") in ("A", "B")]
        if antes:
            fichas[socio]["antes"] = antes[:MAX_CLAVES_DE_ANTES]
    return fichas, roto if mal else None


def guardar_socios(ruta_programa, fichas):
    """Escribe el archivo de las claves (o lo saca, si no queda ninguna). Nace con los
    permisos cerrados (solo el dueño lo lee) donde el sistema lo permite; en Windows queda
    con los de la carpeta. También el provisorio, que nace al lado y sin pisar nada."""
    archivo = archivo_de(ruta_programa, "socios.json")
    if not fichas:
        if os.path.lexists(archivo):
            os.remove(archivo)
        return
    texto = json.dumps({
        "que_es": f"Las claves de los socios de {os.path.basename(ruta_programa)}. NO lo "
                  "copies, no lo mandes y no lo subas a ningún lado: quien lo tenga puede "
                  "firmar mensajes como vos o como tu socio. No se edita a mano: lo lleva "
                  "la orden 'socio' de Mate.",
        "socios": fichas}, ensure_ascii=False, indent=2) + "\n"
    provisorio = f"{archivo}.{os.getpid()}-{secrets.token_hex(4)}.tmp"
    fd = os.open(provisorio, os.O_WRONLY | os.O_CREAT | os.O_EXCL
                 | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0), 0o600)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(texto.encode("utf-8"))
        insistir(lambda: os.replace(provisorio, archivo))
    except BaseException:
        try:
            os.remove(provisorio)
        except OSError:
            pass
        raise


# ── la carpeta compartida ──
def es_union(ruta):
    """¿Es una unión o un enlace de Windows (una carpeta que en realidad lleva a otra)? Una
    carpeta de OneDrive también trae una marca de "punto de reanálisis", pero de otra
    clase: esa es una carpeta de verdad. (Sin probar en una Windows real.)"""
    try:
        if getattr(os.path, "isjunction", lambda _: False)(ruta):
            return True
        datos = os.lstat(ruta)
    except (OSError, ValueError):
        return False
    return getattr(datos, "st_reparse_tag", 0) in (0xA0000003, 0xA000000C)


def es_carpeta_real(ruta):
    return es_carpeta_de_verdad(ruta) and not es_union(ruta)


def _ruta_real(ruta):
    return os.path.normcase(os.path.realpath(ruta)).casefold()


def una_adentro_de_otra(a, b):
    """¿Alguna de las dos carpetas es la otra, o está adentro? (por la ruta de verdad y sin
    distinguir mayúsculas)"""
    a, b = _ruta_real(a), _ruta_real(b)
    try:
        comun = os.path.commonpath([a, b])
    except ValueError:  # en Windows, si están en discos distintos
        return False
    return comun in (a, b)


def esta_adentro(ruta, carpeta):
    """¿Esa ruta es esa carpeta, o está adentro? (por la ruta de verdad, sin distinguir
    mayúsculas)"""
    ruta, carpeta = _ruta_real(ruta), _ruta_real(carpeta)
    try:
        return os.path.commonpath([ruta, carpeta]) == carpeta
    except ValueError:
        return False


_INVITACION_SUELTA = re.compile(r"invitacion-mate.*\.txt.*")  # (como es_archivo_de_clave)


def problema_de_compartida(raiz, carpeta):
    """Por qué Mate no trabaja con esa carpeta compartida, o None. La clave del socio vive
    al lado del programa: la carpeta que se sincroniza con el otro negocio no puede ser la
    del programa, ni contenerla, ni estar adentro; y adentro no puede haber un programa ni
    un archivo de claves."""
    if una_adentro_de_otra(raiz, carpeta):
        return (f"la carpeta compartida ({carpeta}) es la del programa, la contiene o está "
                "adentro, y ahí al lado vive la clave del socio: lo que se comparte con otro "
                "negocio tiene que ser una carpeta aparte")
    for sub in ("", "de-a", "de-b"):  # (también donde viajan los sobres)
        donde = os.path.join(carpeta, sub) if sub else carpeta
        try:
            if sub and not es_carpeta_real(donde):
                continue
            with os.scandir(donde) as hay:
                for n, entrada in enumerate(hay):
                    if n >= MAX_MIRADOS_POR_CORRIDA:
                        break
                    bajo = entrada.name.split(":", 1)[0].rstrip(". ").casefold()
                    if _INVITACION_SUELTA.fullmatch(bajo):
                        return (f"en la carpeta compartida ({donde}) hay una invitación "
                                f"({texto_ajeno(entrada.name, 80)}), y la invitación lleva la "
                                "clave ENTERA: quien ve esa carpeta ya la pudo copiar, y "
                                "queda en la papelera y en el historial de la nube. Borrala "
                                "de ahí y cambiá la clave con 'socio renovar' (la invitación "
                                "nueva va en un pendrive, nunca en la carpeta compartida)")
                    if ".socios.json" in bajo or bajo.endswith((".mate", ".mate.txt")):
                        return (f"en la carpeta compartida ({donde}) hay un archivo que no "
                                f"tiene que estar ahí ({texto_ajeno(entrada.name, 80)}): ni "
                                "los programas ni las claves se comparten con el otro "
                                "negocio. Sacalo de ahí")
        except OSError:
            pass  # (no se ve ahora: eso se avisa aparte)
    return None


# (0.8.1) Lo que Windows, macOS y los programas que sincronizan dejan solos en cualquier
# carpeta, casi siempre ocultos, y vuelven a crear si se borran. En la carpeta compartida no
# son "una cosa que no es un sobre": no se abren, no se tocan y no se avisa.
_ARCHIVOS_DE_SISTEMA = frozenset((
    "desktop.ini", "thumbs.db", "ehthumbs.db", "ehthumbs_vista.db", ".ds_store",
    ".localized", ".dropbox", ".dropbox.attr", ".dropbox.cache", ".fseventsd",
    ".spotlight-v100", ".trashes", ".temporaryitems", ".tmp.drivedownload",
    ".tmp.driveupload", "$recycle.bin", "system volume information"))


def es_archivo_de_sistema(nombre):
    """¿Ese nombre es de los que deja el sistema (desktop.ini, Thumbs.db, .DS_Store, los
    "._algo" que macOS escribe en un pendrive, los "~$algo" de Office)? Se mira solo el
    nombre, y nunca vale para algo con la forma de un sobre."""
    bajo = nombre.casefold()
    if _SOBRE_EN_COMPARTIDA.fullmatch(bajo):
        return False
    return bajo in _ARCHIVOS_DE_SISTEMA or bajo.startswith(("._", "~$"))


def estado_nuevo_de_socio(huella, en_espera=()):
    return {"huella": huella, "enviado": 0, "piso": 0, "vistos": {}, "traidos": [],
            "ids": {}, "por_salir": [], "en_espera": list(en_espera), "rotos": {}}


def estado_de_socio_limpio(est):
    """Lo que la memoria guarda de un socio, controlado (o None si no tiene la forma de
    siempre: ahí vale como si no estuviera)."""
    def entero(v):
        return type(v) is int and 0 <= v <= MAX_NUMERO_DE_SOBRE

    if not isinstance(est, dict):
        return None
    en_espera = est.get("en_espera", [])
    if not isinstance(en_espera, list) or not all(isinstance(b, dict) for b in en_espera):
        return None
    if est.get("huella") is None:
        return {"en_espera": en_espera} if en_espera else None
    vistos, traidos, ids = est.get("vistos", {}), est.get("traidos", []), est.get("ids", {})
    por_salir, rotos = est.get("por_salir", []), est.get("rotos", {})
    if not (isinstance(est["huella"], str) and entero(est.get("enviado"))
            and entero(est.get("piso")) and isinstance(vistos, dict)
            and all(k.isascii() and k.isdigit() and isinstance(v, str)
                    for k, v in vistos.items())
            and isinstance(traidos, list) and all(entero(n) for n in traidos)
            and isinstance(ids, dict)
            and all(isinstance(v, list) and len(v) in (2, 3) for v in ids.values())
            and isinstance(por_salir, list) and all(
                isinstance(s, dict) and isinstance(s.get("socio"), dict)
                and entero(s["socio"].get("numero")) and isinstance(s.get("id"), str)
                for s in por_salir)
            and isinstance(rotos, dict)
            and all(type(v) is int for v in rotos.values())):
        return None
    return {"huella": est["huella"], "enviado": est["enviado"], "piso": est["piso"],
            "vistos": dict(vistos), "traidos": list(traidos), "ids": dict(ids),
            "por_salir": list(por_salir), "en_espera": en_espera, "rotos": dict(rotos)}


def leer_correo_de_memoria(ruta):
    """La parte "correo" del archivo de memoria (0.8): {"enviados": [...], "socios": {...}}.
    enviados son los últimos mensajes que este programa mandó por el buzón local
    ("programa/id"): con eso reconoce un aviso de falla de verdad. socios es lo que lleva de
    cada socio: su contador de envíos, los números ya vistos, lo que espera el si y lo que
    tiene por salir. Si no está o no se entiende, vale como vacía."""
    vacio = {"enviados": [], "socios": {}}
    try:
        datos = json.loads(leer_archivo_de_memoria(ruta))
    except (OSError, ErrorMate, ValueError, RecursionError):
        return vacio
    parte = datos.get("correo") if isinstance(datos, dict) else None
    if not isinstance(parte, dict):
        return vacio
    enviados = parte.get("enviados", [])
    enviados = [e for e in enviados if isinstance(e, str)] if isinstance(enviados, list) else []
    socios = {}
    for nombre, est in (parte.get("socios") if isinstance(parte.get("socios"), dict)
                        else {}).items():
        limpio = estado_de_socio_limpio(est)
        if limpio is not None:
            socios[nombre] = limpio
    return {"enviados": enviados[-MAX_IDS_ENVIADOS:], "socios": socios}


class Socios:
    """Los socios del programa que se corre con 'correr' (los de sus 'usar socio'): las
    claves, lo que sale firmado hacia la carpeta compartida y lo que llega. 'probar',
    'verificar', 'ensayar' y la consola no arman ninguno: no leen ni escriben nada de esto."""

    def __init__(self, ruta, declarados, buzon, avisar=lambda texto: None, ahora=None):
        self.ruta = os.path.abspath(ruta)
        self.raiz = os.path.dirname(self.ruta)
        self.archivo = os.path.basename(ruta)
        self.declarados = declarados  # socio -> los mensajes que se le aceptan
        self.buzon = buzon
        self.avisar = avisar
        self.ahora = ahora or (lambda: reloj_local())  # (el reloj de ESTA máquina)
        self.fichas = {}  # los socios con clave cargada y carpeta que sirve
        self.listos = set()  # ...y con la cuenta en orden: con ellos se manda y se recibe
        self.estado = {}  # lo que la memoria lleva de cada socio
        self.leer_estado = lambda: {}  # (lo pone 'correr': lee la memoria de nuevo)
        self.borradores = []  # (socio, sobre todavía sin número ni firma) de esta corrida
        self.tocado = False  # ¿hay algo para guardar?
        self.recibio = False  # ¿esta corrida miró lo que llegó? (con el candado tomado)
        self.por_borrar = []  # archivos de la carpeta compartida ya atendidos
        self.locales_por_borrar = []  # pendientes ya entregados
        self.rechazos = []  # (socio, bytes o None, archivo local o None, motivo)
        self.atendi, self.deje, self.no_entregados = {}, {}, 0
        self.sin_copia = 0  # rechazados que no se guardaron (el cupo estaba lleno)
        self.miro = False  # ¿esta corrida llegó a mirar lo de los socios?
        self.con_novedad = set()  # los socios de los que hubo algo para contar
        self.limpios = set()  # los socios a los que ya les saqué lo mío de otra clave
        self.avisados = set()
        self._carpetas = {}
        self._rechazos_avisados = {}

    def avisar_una_vez(self, cual, texto):
        if cual not in self.avisados:
            self.avisados.add(cual)
            self.avisar(texto)

    def orden_de(self, que, socio):
        return f"{orden_para_esta_carpeta()} socio {que} {para_pegar(self.archivo)} {socio}"

    def cargar_claves(self):
        """Lee el archivo de claves y deja en 'fichas' los socios con los que se puede
        trabajar. Avisa de los demás: no es un error, pero con ellos no se manda ni se
        recibe (lo que se les envíe queda anotado, sin salir)."""
        fichas, problema = leer_socios(self.ruta)
        if problema:
            self.avisar(problema)
        for socio in self.declarados:
            ficha = fichas.get(socio)
            if ficha is None:
                self.avisar(
                    f"falta cargar la clave del socio {socio}: con él no se manda ni se "
                    "recibe nada (lo que se le envíe queda anotado y sale cuando la clave "
                    f"esté). Si la clave la generás vos:  {self.orden_de('invitar', socio)}"
                    f"   Si te la pasa tu socio:  {self.orden_de('aceptar', socio)}")
                continue
            problema = problema_de_compartida(self.raiz, ficha["carpeta"])
            if problema:
                self.avisar(f"con el socio {socio} no mando ni recibo nada: {problema}. "
                            "Para cambiar la clave o elegir otra carpeta:  "
                            f"{self.orden_de('renovar', socio)}")
                continue
            if ficha.get("ensayo"):
                # (corto: sale en cada corrida del ensayo, y no tiene que tapar lo demás)
                self.avisar(f"la clave con {socio} es de ENSAYO: sirve para probar en esta "
                            "PC, no para un socio de verdad (para eso, 'socio renovar': lo "
                            "cuentan 'nuevo socio' y el manual)")
            self.fichas[socio] = ficha
        try:
            de_onedrive = os.environ.get("OneDrive") or os.environ.get("OneDriveConsumer")
            if self.fichas and de_onedrive and una_adentro_de_otra(de_onedrive, self.raiz) \
                    and _ruta_real(self.raiz).startswith(_ruta_real(de_onedrive)):
                self.avisar(
                    f"la carpeta del programa ({self.raiz}) está adentro de OneDrive: el "
                    "archivo con las claves de los socios se sube a la nube junto con lo "
                    "demás. Conviene mover la carpeta del programa a un lugar que no se "
                    "sincronice (por ejemplo C:\\mate)")
        except (OSError, ValueError):
            pass

    def huella(self, socio):
        ficha = self.fichas.get(socio)
        return huella_de_clave(ficha["clave"]) if ficha else None

    def control(self, socio):
        ficha = self.fichas.get(socio)
        return control_de_socio(ficha["clave"]) if ficha else "sin clave"

    def preparar(self, correo):
        """Con el candado de la memoria tomado, al arrancar: compara cada clave con lo que
        la memoria lleva de ese socio. Devuelve (si hay que guardar la memoria, los socios
        que hay que marcar como estrenados DESPUÉS de guardarla).
        - La memoria lleva la cuenta de esa clave: listo.
        - La clave es nueva (nunca se usó): la cuenta arranca de cero.
        - La clave ya se usó y la memoria no tiene su cuenta (se borró, o se restauró una
          copia): no se manda ni se entrega nada con ese socio. Mandar sería repetir
          números, y recibir sería aceptar de nuevo lo ya entregado. Hay que renovar."""
        estados = correo["socios"]
        cambio, por_estrenar = False, []
        for socio, ficha in self.fichas.items():
            huella = huella_de_clave(ficha["clave"])
            est = estados.get(socio) or {}
            if est.get("huella") == huella:
                self.listos.add(socio)
                if not ficha.get("estrenado"):
                    por_estrenar.append(socio)
                if est.get("en_espera"):
                    self.tocado = True  # (lo anotado sin salir se numera al guardar)
                continue
            if ficha.get("estrenado"):
                self.avisar(
                    f"se perdió la cuenta de los mensajes con {socio}: la clave ya se usó y "
                    f"{os.path.basename(archivo_de(self.ruta, 'memoria.json'))} no tiene "
                    "los números de lo enviado y lo recibido (se borró la memoria, o se "
                    "restauró una copia). Con ese socio no mando ni entrego nada hasta "
                    f"renovar la clave:  {self.orden_de('renovar', socio)}   (y que tu "
                    "socio la acepte de nuevo)")
                continue
            viejos = len(est.get("por_salir") or []) + len(est.get("traidos") or [])
            if viejos:
                self.avisar(
                    f"la clave con {socio} es nueva: {cuantos_mensajes(viejos)} que "
                    "quedaban por salir o esperando tu si con la clave anterior se "
                    "descartan (con la clave nueva ya no valen)")
            estados[socio] = estado_nuevo_de_socio(huella, est.get("en_espera") or [])
            self.tocado = self.tocado or bool(est.get("en_espera"))
            self.listos.add(socio)
            por_estrenar.append(socio)
            cambio = True
        self.estado = estados
        return cambio, por_estrenar

    def estrenar(self, cuales):
        """Marca esas claves como ya usadas (después de que la memoria guardó su cuenta)."""
        if not cuales:
            return
        fichas, _ = leer_socios(self.ruta)
        cambio = False
        for socio in cuales:
            ficha = fichas.get(socio)
            if ficha and ficha["clave"] == self.fichas[socio]["clave"] \
                    and not ficha["estrenado"]:
                ficha["estrenado"] = cambio = True
                self.fichas[socio]["estrenado"] = True
        if cambio:
            try:
                guardar_socios(self.ruta, fichas)
            except OSError:
                self.avisar(f"no pude escribir en {os.path.basename(archivo_de(self.ruta, 'socios.json'))}"
                            ": fijate que se pueda escribir en la carpeta del programa")

    def frenar_todos(self):
        self.listos = set()

    def carpetas(self, socio):
        """(la carpeta donde escribo, la carpeta donde leo) dentro de la compartida con ese
        socio, o None si ahora no se ve o no sirve (avisa una vez). En cada corrida las
        tres tienen que ser carpetas de verdad: Mate no sigue un acceso directo ni una
        unión, que lo harían leer y borrar en otro lado."""
        if socio in self._carpetas:
            return self._carpetas[socio]
        ficha = self.fichas[socio]
        base = ficha["carpeta"]
        mia, suya = ("de-a", "de-b") if ficha["lado"] == "A" else ("de-b", "de-a")
        problema, que_hacer = None, ""
        if not es_carpeta_real(base):
            # (0.8.1) Dice qué hacer: antes solo preguntaba por el pendrive.
            problema = f"no veo la carpeta compartida con {socio} ({base})"
            que_hacer = (
                ". Qué hacer: fijate que esté puesto el pendrive, o que ande la conexión, y "
                "corré el programa de nuevo. Si la carpeta cambió de lugar (por ejemplo, el "
                "pendrive ahora es F: y antes era E:), decile a Mate dónde está ahora; la "
                "clave no cambia y tu socio no tiene que hacer nada:  "
                f"{self.orden_de('carpeta', socio)} --carpeta=F:\\Compartida")
        else:
            for sub in (mia, suya):
                completa = os.path.join(base, sub)
                try:
                    if not os.path.lexists(completa):
                        os.mkdir(completa)
                except OSError:
                    problema = (f"no pude crear {sub} en la carpeta compartida con {socio} "
                                f"({base}): fijate que haya permiso para escribir ahí")
                    break
                if not es_carpeta_real(completa):
                    problema = (f"en la carpeta compartida con {socio}, {sub} no es una "
                                "carpeta de verdad (es un acceso directo, una unión u otra "
                                "cosa): no la sigo. Borrala y corré de nuevo")
                    break
        if problema:
            self.avisar(f"{problema}. En esta corrida no mando ni recibo nada de {socio}; lo "
                        "que haya para mandarle queda anotado y sale la próxima vez"
                        + que_hacer)
            self._carpetas[socio] = None
        else:
            self._carpetas[socio] = (os.path.join(base, mia), os.path.join(base, suya))
        return self._carpetas[socio]

    # ── lo que sale ──
    def borrador(self, de_agente, mensaje, conversacion=None, en_respuesta_a=None,
                 falla=None, campo=None):
        """Un sobre para un socio, todavía sin número ni firma (eso se le pone al guardar,
        con el candado de la memoria tomado). falla: el CÓDIGO del motivo (lista cerrada)."""
        id = self.buzon.nuevo_id()
        sobre = {"id": id, "clase": "mensaje" if falla is None else "falla",
                 "de": {"programa": self.buzon.programa, "agente": de_agente},
                 "para": {"programa": "(socio)", "agente": "(socio)"},
                 "conversacion": conversacion or id, "en_respuesta_a": en_respuesta_a,
                 "cuando": datetime.datetime.now().isoformat(timespec="seconds"),
                 "mensaje": mensaje}
        if falla is not None:
            sobre["motivo"] = falla
            if campo:
                sobre["campo"] = campo
        return sobre

    def sale(self, socio, borrador):
        self.borradores.append((socio, borrador))
        self.tocado = True

    def numerar(self, socio, est, borrador):
        """Le pone el número que sigue y la firma, y lo deja "por salir"."""
        ficha = self.fichas[socio]
        est["enviado"] += 1
        sobre = dict(borrador, mate_buzon=VERSION_DE_SOBRE_DE_SOCIO,
                     socio={"huella": est["huella"], "lado": ficha["lado"],
                            "numero": est["enviado"]})
        sobre["firma"] = firma_de_sobre(sobre, ficha["clave"], ficha["lado"])
        est["por_salir"].append(sobre)
        if sobre["clase"] == "mensaje":
            ids = est["ids"]
            ids[sobre["id"]] = [huella_de_mensaje(sobre["mensaje"]), sobre["de"]["agente"]]
            while len(ids) > MAX_IDS_ENVIADOS:
                del ids[next(iter(ids))]

    def cerrar(self, correo):
        """Con el candado de la memoria tomado, justo antes de guardarla: numera y firma lo
        que esta corrida mandó (y lo que esperaba una clave), y deja en 'correo' lo que hay
        que guardar de los socios."""
        estados = self.estado if self.recibio else correo["socios"]
        correo["socios"] = estados
        nuevos = {}
        for socio, borrador in self.borradores:
            nuevos.setdefault(socio, []).append(borrador)
        self.borradores = []
        for socio in sorted(set(nuevos) | self.listos):
            est = estados.get(socio)
            cola = list((est or {}).get("en_espera") or []) + nuevos.get(socio, [])
            if not cola:
                continue
            if socio in self.listos and est and est.get("huella") == self.huella(socio):
                est["en_espera"] = []
                for borrador in cola:
                    try:
                        self.numerar(socio, est, borrador)
                    except (ValueError, RecursionError, TypeError, KeyError):
                        self.avisar(f"un mensaje para {socio} no se pudo firmar y no sale")
                continue
            if est is None:
                est = estados[socio] = {"en_espera": []}
            if len(cola) > MAX_EN_ESPERA:
                self.avisar(
                    f"OJO: hay más de {MAX_EN_ESPERA} mensajes para {socio} anotados sin "
                    f"salir: los últimos {len(cola) - MAX_EN_ESPERA} NO se anotaron y se "
                    "perdieron")
                cola = cola[:MAX_EN_ESPERA]
            est["en_espera"] = cola
            self.avisar(
                f"{cuantos_mensajes(len(cola))} para {socio} "
                f"{'queda anotado' if len(cola) == 1 else 'quedan anotados'} y NO "
                f"{'salió' if len(cola) == 1 else 'salieron'}: con ese socio todavía no se "
                "puede mandar (lo dice el aviso de más arriba). "
                f"{'Sale' if len(cola) == 1 else 'Salen'} cuando eso esté resuelto")

    def dejar(self, carpeta, sobre):
        """Escribe un sobre firmado en mi carpeta de la compartida: primero en un
        provisorio y después con su nombre. Se escribe una sola vez y nunca se cambia."""
        corto = hashlib.sha256(sobre["id"].encode("utf-8", "replace")).hexdigest()[:8]
        final = os.path.join(carpeta, f"{sobre['socio']['numero']:08d}-{corto}.json")
        provisorio = f"{final[:-len('.json')]}.{os.getpid()}-{secrets.token_hex(4)}.json.tmp"
        try:
            crudo = json.dumps(sobre, ensure_ascii=True, indent=1,
                               allow_nan=False).encode("ascii")
            with abrir_provisorio(provisorio, "xb") as f:
                f.write(crudo)
            # (en una carpeta sincronizada, el sincronizador o el antivirus pueden tener
            # tomado el provisorio un instante: se insiste, como al guardar las claves)
            insistir(lambda: os.replace(provisorio, final))
        except (OSError, ValueError, RecursionError):
            try:
                insistir(lambda: os.remove(provisorio))
            except OSError:
                pass  # (si quedó, lo saca sacar_lo_mio_que_no_vale cuando tenga un día)
            return False
        return True

    def es_de_otra_clave(self, socio, datos, lado, repetidas=False, huella=None):
        """¿Eso tiene toda la forma de un sobre entre negocios de ese lado ("A" o "B"),
        pero firmado con OTRA clave que la cargada (con esa huella, si se dice cuál)? Pasa
        entre un 'socio renovar' de un lado y el 'socio aceptar' del otro. No dice nada de
        quién lo escribió."""
        if repetidas or not isinstance(datos, dict):
            return False
        version, firma, de_quien = datos.get("mate_buzon"), datos.get("firma"), \
            datos.get("socio")
        if type(version) is not int or version != VERSION_DE_SOBRE_DE_SOCIO \
                or not (isinstance(firma, str) and _FIRMA.fullmatch(firma)) \
                or not isinstance(de_quien, dict) \
                or set(de_quien) != {"huella", "lado", "numero"}:
            return False
        suya, numero = de_quien["huella"], de_quien["numero"]
        return (isinstance(suya, str) and bool(_HUELLA.fullmatch(suya))
                and suya != self.huella(socio) and huella in (None, suya)
                and de_quien["lado"] == lado
                and type(numero) is int and 1 <= numero <= MAX_NUMERO_DE_SOBRE)

    def sacar_lo_mio_que_no_vale(self, socio):
        """Una vez por corrida: saca de la carpeta compartida los sobres que ESTE programa
        dejó firmados con una clave anterior (las de 'antes' en su ficha: la huella de esa
        clave y el lado que este programa tenía con ella, que dice en qué carpeta
        escribía). Son los que quedaron viajando cuando se cambió la clave: el socio no los
        llegó a traer, y con la clave nueva no los va a poder comprobar nunca. Se avisa
        fuerte, porque para el que los mandó "ya habían salido". De paso, saca de la
        carpeta donde escribe ahora los provisorios (.json.tmp) huérfanos de más de un día."""
        if socio in self.limpios:
            return
        self.limpios.add(socio)
        ficha = self.fichas[socio]
        base, ahora, viejos = ficha["carpeta"], self.ahora(), []
        if not es_carpeta_real(base):
            return
        lugares = [(f"de-{ficha['lado'].lower()}", None, None)] + [
            (f"de-{a['lado'].lower()}", a["huella"], a["lado"]) for a in ficha.get("antes", ())]
        for sub, huella, lado in lugares:
            carpeta = os.path.join(base, sub)
            if not es_carpeta_real(carpeta):
                continue
            try:
                with os.scandir(carpeta) as hay:
                    for n, entrada in enumerate(hay):
                        if n >= MAX_MIRADOS_POR_CORRIDA:
                            break
                        bajo = entrada.name.lower()
                        try:
                            if huella is None:  # (mi carpeta de ahora: solo provisorios)
                                if bajo.endswith(".json.tmp") \
                                        and entrada.is_file(follow_symlinks=False) and ahora \
                                        - entrada.stat(follow_symlinks=False).st_mtime \
                                        >= ESPERA_DE_UN_ROTO:
                                    os.remove(entrada.path)
                                continue
                            if not _SOBRE_EN_COMPARTIDA.fullmatch(bajo):
                                continue
                            with abrir_sin_seguir(entrada.path) as f:
                                crudo = f.read(MAX_SOBRE + 1)
                            if len(crudo) > MAX_SOBRE:
                                continue
                            datos, repetidas = json_de_sobre(crudo)
                        except (OSError, ValueError, RecursionError):
                            continue
                        if self.es_de_otra_clave(socio, datos, lado, repetidas, huella):
                            viejos.append(entrada.path)
            except OSError:
                continue
        sacados = 0
        for ruta in viejos:
            try:
                if es_carpeta_real(os.path.dirname(ruta)):
                    os.remove(ruta)
                    sacados += 1
            except OSError:
                pass
        if sacados:
            self.con_novedad.add(socio)
            uno = sacados == 1
            self.avisar(
                f"OJO: {cuantos_mensajes(sacados)} que le habías mandado a {socio} "
                f"{'seguía' if uno else 'seguían'} en la carpeta compartida "
                f"{'firmado' if uno else 'firmados'} con la clave anterior: tu socio NO "
                f"{'lo' if uno else 'los'} recibió, y con la clave nueva ya no "
                f"{'vale' if uno else 'valen'}. {'Lo' if uno else 'Los'} saqué de ahí. Si "
                f"{'hacía' if uno else 'hacían'} falta, hay que "
                f"{'mandarlo' if uno else 'mandarlos'} de nuevo")

    def repartir(self, correo):
        """Deja en la carpeta compartida lo que está "por salir" de cada socio listo. Lo
        que no se pudo dejar sigue anotado. Devuelve si salió algo (hay que guardar)."""
        salio = False
        for socio in sorted(self.listos):
            est = correo["socios"].get(socio) or {}
            pendientes = est.get("por_salir") or []
            self.sacar_lo_mio_que_no_vale(socio)
            if not pendientes:
                continue
            carpetas = self.carpetas(socio)
            if carpetas is None:
                continue
            quedan = []
            for sobre in pendientes:
                if self.dejar(carpetas[0], sobre):
                    self.con_novedad.add(socio)
                    salio = True
                    self.deje[socio] = self.deje.get(socio, 0) + 1
                else:
                    quedan.append(sobre)
            est["por_salir"] = quedan
            if quedan:
                self.con_novedad.add(socio)
                self.avisar_una_vez(("no pude", socio), (
                    f"no pude dejar {cuantos_mensajes(len(quedan))} para {socio} en la "
                    f"carpeta compartida ({self.fichas[socio]['carpeta']}): ¿hay permiso "
                    "para escribir ahí? Queda anotado y sale la próxima vez que corra "
                    f"{self.archivo}"))
        return salio

    # ── lo que llega ──
    def recargar(self):
        """Con el candado de la memoria tomado (y sin soltarlo hasta guardar): lee de nuevo
        lo que la memoria lleva de los socios. Desde acá, esta corrida es la dueña."""
        self.estado = self.leer_estado()
        self.recibio = True
        for socio in list(self.listos):
            if (self.estado.get(socio) or {}).get("huella") != self.huella(socio):
                self.listos.discard(socio)

    def carpeta_de_pendientes(self):
        return os.path.join(self.buzon.carpeta, "pendientes")

    def hay_algo(self):
        """¿Hay algo de algún socio para mirar (en la compartida o esperando el si)?"""
        try:
            if any(_PENDIENTE_DE_SOCIO.fullmatch(n.lower())
                   for n in os.listdir(self.carpeta_de_pendientes())):
                return True
        except OSError:
            pass
        for socio in sorted(self.listos):
            if (self.estado.get(socio) or {}).get("traidos"):
                return True
            carpetas = self.carpetas(socio)
            if carpetas is None:
                continue
            try:
                with os.scandir(carpetas[1]) as hay:
                    if any(e.name.lower().endswith(".json") for e in hay):
                        return True
            except OSError:
                pass
        return False

    def autenticar(self, socio, datos, repetidas=False):
        """Por qué eso NO es un sobre firmado por ese socio, o None si lo es. No usa ningún
        dato del sobre antes de comprobar la firma, y el socio lo da la carpeta donde
        apareció el archivo: la huella tiene que ser la suya."""
        ficha = self.fichas[socio]
        if repetidas:
            return "trae claves repetidas (un sobre firmado no puede)"
        if not isinstance(datos, dict):
            return "no es un sobre de Mate"
        version = datos.get("mate_buzon")
        if type(version) is not int or version != VERSION_DE_SOBRE_DE_SOCIO:
            return ("no es un sobre entre negocios (dice mate_buzon: "
                    f"{texto_ajeno(version, 20)} y acá solo valen los firmados, que dicen "
                    f"{VERSION_DE_SOBRE_DE_SOCIO})")
        firma, de_quien = datos.get("firma"), datos.get("socio")
        if not (isinstance(firma, str) and _FIRMA.fullmatch(firma)):
            return "no trae firma"
        if not isinstance(de_quien, dict) or set(de_quien) != {"huella", "lado", "numero"}:
            return "no dice de qué socio es"
        if de_quien["huella"] != huella_de_clave(ficha["clave"]):
            return "está firmado con otra clave (no es la de este socio)"
        if de_quien["lado"] != ("B" if ficha["lado"] == "A" else "A"):
            return ("dice venir de mi propio lado: es un sobre de este programa que alguien "
                    "devolvió")
        numero = de_quien["numero"]
        if type(numero) is not int or not 1 <= numero <= MAX_NUMERO_DE_SOBRE:
            return "trae un número de orden imposible"
        if demasiado_hondo(datos):
            return "trae demasiadas cosas una adentro de otra"
        try:
            esperada = firma_de_sobre(datos, ficha["clave"], de_quien["lado"])
        except (ValueError, RecursionError, TypeError):
            return "no se puede comprobar su firma"
        if not hmac.compare_digest(esperada, firma):
            return "la firma no es válida (no lo escribió tu socio, o alguien lo cambió)"
        return None

    def rechazar(self, socio, crudo, motivo, local=None, avisar=True):
        """Algo de ese socio que no se entrega: va a 'rechazados' (la carpeta LOCAL del
        programa, nunca la compartida) con su motivo, cuando la corrida guarda."""
        motivo = texto_ajeno(motivo, LARGO_DE_MOTIVO)
        cuantos = sum(1 for r in self.rechazos if r[0] == socio)
        if cuantos >= MAX_RECHAZADOS_DE_SOCIO:
            crudo = None  # (no se guarda en la mano más de lo que se va a poder copiar)
        self.rechazos.append((socio, crudo, local, motivo))
        self.con_novedad.add(socio)
        self.no_entregados += 1
        self.tocado = True
        n = self._rechazos_avisados[socio] = self._rechazos_avisados.get(socio, 0) + 1
        if avisar and n <= 5:
            self.avisar(f"no entregué un mensaje de {socio}: {motivo}. Quedó en "
                        f"{self.buzon.donde_van_los_rechazados()}")

    def mirar(self, socio):
        """Recorre lo que hay en la carpeta donde escribe ese socio y da (archivo, bytes,
        sobre) por cada sobre NUEVO con su firma en regla. Lo demás lo resuelve acá:
        - lo que no es un .json, un provisorio, una carpeta, un acceso directo o algo de más
          de 2 MB: no se abre, no se sigue y no se toca (se cuenta);
        - lo que no se entiende como JSON puede estar a medio llegar: se deja, y recién si
          sigue así un día entero (del reloj de esta máquina) va a rechazados;
        - un JSON sin firma válida de ESTE socio: a rechazados, sin contestarle a nadie;
        - salvo el que tiene toda la forma de un sobre del socio pero firmado con OTRA
          clave: uno de los dos renovó la clave y el otro todavía no la aceptó. Ese no se
          entrega, no se rechaza y NO se borra de la compartida: se avisa. Si el que renovó
          es el socio, se entrega cuando acá se cargue la clave nueva; si fue este lado, lo
          saca el programa del socio cuando la acepte (y le avisa que no llegó);
        - un número ya visto con el mismo contenido (una copia en conflicto, un archivo
          que la sincronización revivió): se borra sin ruido; con otro contenido, o por
          debajo de lo que ya se dejó de recordar: a rechazados, con aviso."""
        est = self.estado[socio]
        carpetas = self.carpetas(socio)
        if carpetas is None:
            return
        candidatos, otros, ocupados, de_otra_clave = [], 0, 0, 0
        su_lado = "B" if self.fichas[socio]["lado"] == "A" else "A"
        try:
            with os.scandir(carpetas[1]) as hay:
                for n, entrada in enumerate(hay):
                    if n >= MAX_MIRADOS_POR_CORRIDA:
                        self.avisar(
                            f"en la carpeta compartida con {socio} hay más de "
                            f"{MAX_MIRADOS_POR_CORRIDA} archivos: miro esos y el resto "
                            "queda para la próxima corrida")
                        break
                    bajo = entrada.name.lower()
                    if bajo.endswith(".tmp") or es_archivo_de_sistema(bajo):
                        continue
                    if not bajo.endswith(".json"):
                        otros += 1
                        continue
                    forma = _SOBRE_EN_COMPARTIDA.fullmatch(bajo)
                    try:
                        comun = entrada.is_file(follow_symlinks=False)
                    except OSError:
                        comun = False
                    candidatos.append(((0, int(forma.group(1)), bajo) if forma
                                       else (1, 0, bajo), entrada.path, comun))
        except OSError:
            self.avisar(f"no pude mirar la carpeta compartida con {socio}: lo que haya "
                        "llegado queda para la próxima corrida")
            return
        candidatos.sort()  # primero los que tienen la forma esperada, por número
        ahora, rotos, siguen = int(self.ahora()), est.setdefault("rotos", {}), set()
        esperando = 0
        for _, ruta, comun in candidatos:
            base = os.path.basename(ruta)
            try:
                with abrir_sin_seguir(ruta) as f:
                    crudo = f.read(MAX_SOBRE + 1)
            except OSError:
                if comun:
                    ocupados += 1  # un archivo común que AHORA no se puede abrir
                else:
                    otros += 1  # una carpeta, un acceso directo u otra cosa
                continue
            if len(crudo) > MAX_SOBRE:
                otros += 1
                continue
            try:
                datos, repetidas = json_de_sobre(crudo)
            except RecursionError:
                otros += 1
                continue
            except ValueError:
                clave = hashlib.sha256(base.encode("utf-8", "replace")).hexdigest()[:16]
                siguen.add(clave)
                desde = rotos.get(clave)
                if desde is None:
                    if len(rotos) < MAX_A_MEDIO_LLEGAR:
                        rotos[clave] = ahora
                        self.tocado = True
                    esperando += 1
                elif desde < 0:
                    otros += 1  # (ya se rechazó: sigue ahí hasta que alguien lo saque)
                elif ahora - desde >= ESPERA_DE_UN_ROTO:
                    rotos[clave] = -1
                    self.rechazar(socio, crudo, (
                        f"el archivo {base} no se entiende, y lleva más de un día así en "
                        "la carpeta compartida (no es un mensaje a medio llegar). Mate no "
                        "lo borra de ahí: sacalo a mano"))
                else:
                    esperando += 1
                continue
            if not isinstance(datos, dict) or "mate_buzon" not in datos:
                otros += 1
                continue
            motivo = self.autenticar(socio, datos, repetidas)
            if motivo and self.es_de_otra_clave(socio, datos, su_lado, repetidas):
                de_otra_clave += 1  # (se deja donde está: ver arriba)
                continue
            if motivo:
                # (no cuenta como visto, y a quien no se autenticó no se le contesta)
                self.rechazar(socio, crudo, f"el archivo {base}: {motivo}")
                self.por_borrar.append(ruta)
                continue
            numero, marca = datos["socio"]["numero"], datos["firma"][:16]
            visto = est["vistos"].get(str(numero))
            if visto == marca:
                self.por_borrar.append(ruta)  # repetido: el mismo sobre, otra vez
                self.tocado = True
                continue
            if visto is not None:
                self.rechazar(socio, crudo, (
                    f"OJO: llegó el número {numero} de {socio} por segunda vez y con OTRO "
                    "contenido. Tu socio repitió un número (puede haber restaurado una "
                    "copia vieja de su programa): renueven la clave"))
                self.por_borrar.append(ruta)
                continue
            if numero <= est["piso"]:
                self.rechazar(socio, crudo, (
                    f"llegó tarde el {numero} de {socio} y ya no se acepta (es más viejo "
                    "que lo que este programa recuerda haber visto)"))
                self.por_borrar.append(ruta)
                continue
            yield ruta, crudo, datos
        for clave in list(rotos):  # lo que ya no está, o ya se entiende, se olvida
            if clave not in siguen:
                del rotos[clave]
                self.tocado = True
        if esperando or otros or ocupados or de_otra_clave:
            self.con_novedad.add(socio)
        if de_otra_clave:
            uno = de_otra_clave == 1
            self.avisar_una_vez(("otra clave", socio), (
                f"OJO: en la carpeta compartida con {socio} hay "
                f"{cuantos_mensajes(de_otra_clave)} {'firmado' if uno else 'firmados'} con "
                f"otra clave que la que tenés cargada (control {self.control(socio)}): no "
                f"{'lo' if uno else 'los'} entrego, no {'lo' if uno else 'los'} borro y no "
                "contesto. Si tu socio RENOVÓ la clave, cargá la nueva y "
                f"{'se entrega' if uno else 'se entregan'} en la corrida siguiente:  "
                f"{self.orden_de('aceptar', socio)}   Si la renovaste VOS, tu socio "
                f"todavía no la aceptó: lo que mandó con la clave vieja no vale (lo saca su "
                "programa cuando la acepte, y le avisa)"))
        if ocupados:
            self.avisar_una_vez(("ocupados", socio), (
                f"en la carpeta compartida con {socio} hay "
                f"{'1 archivo que ahora no se puede abrir' if ocupados == 1 else f'{ocupados} archivos que ahora no se pueden abrir'}"
                " (lo puede tener tomado el programa que sincroniza la carpeta, o el "
                "antivirus): no lo toco, y lo miro de nuevo en la próxima corrida. No lo "
                "borres"))
        if esperando:
            self.avisar(
                f"en la carpeta compartida con {socio} hay "
                f"{'1 archivo que todavía no se entiende' if esperando == 1 else f'{esperando} archivos que todavía no se entienden'}"
                " (puede estar a medio llegar): lo dejo y lo miro de nuevo en la próxima "
                "corrida")
        if otros:
            self.avisar_una_vez(("otros", socio), (
                f"en la carpeta compartida con {socio} hay {otros} "
                f"{'cosa que no es un sobre' if otros == 1 else 'cosas que no son sobres'} "
                "de Mate (otro archivo, una carpeta, un acceso directo o algo demasiado "
                "pesado): no lo abro, no lo sigo y no lo borro. Sacalo a mano"))

    def visto(self, socio, sobre, pendiente=False):
        """Anota ese número como visto (con la marca de su firma, para distinguir un
        repetido de un número usado dos veces). pendiente: además queda esperando el si."""
        est = self.estado[socio]
        numero = sobre["socio"]["numero"]
        self.con_novedad.add(socio)
        est["vistos"][str(numero)] = sobre["firma"][:16]
        if pendiente and numero not in est["traidos"]:
            est["traidos"].append(numero)
        if len(est["vistos"]) > MAX_VISTOS:  # se olvidan los más viejos, y sube el piso
            numeros = sorted(int(n) for n in est["vistos"])
            for n in numeros[:len(numeros) - MAX_VISTOS]:
                del est["vistos"][str(n)]
                est["piso"] = max(est["piso"], n)
        self.tocado = True

    def cuantos_esperan(self, socio):
        return len(self.estado[socio]["traidos"])

    def a_pendientes(self, socio, sobre, crudo, ruta):
        """Un sobre firmado y bien formado: se copia a la carpeta LOCAL 'pendientes' (con
        un nombre que arma Mate: la huella de la clave y el número), se anota su número y
        recién después de guardar se borra de la compartida. Devuelve si se pudo."""
        if self.cuantos_esperan(socio) >= MAX_PENDIENTES_POR_SOCIO:
            self.avisar_una_vez(("tope", socio), (
                f"ya hay {MAX_PENDIENTES_POR_SOCIO} mensajes de {socio} esperando tu si, "
                "que es el tope: lo demás que mandó queda en la carpeta compartida hasta "
                "que contestes esos"))
            return False
        carpeta = self.carpeta_de_pendientes()
        numero = sobre["socio"]["numero"]
        final = os.path.join(carpeta, f"s{self.huella(socio)}-{numero:08d}.json")
        provisorio = None
        try:
            if os.path.lexists(carpeta) and not es_carpeta_de_verdad(carpeta):
                raise OSError
            os.makedirs(carpeta, exist_ok=True)
            provisorio = nombre_provisorio(final)
            with abrir_provisorio(provisorio, "xb") as f:
                f.write(crudo)
            os.replace(provisorio, final)
        except OSError:
            try:
                if provisorio is not None:
                    os.remove(provisorio)
            except OSError:
                pass
            self.avisar_una_vez(("pendientes", socio), (
                f"no pude guardar lo que llegó de {socio} en "
                f"{os.path.join(os.path.basename(self.buzon.carpeta), 'pendientes')}: queda "
                "en la carpeta compartida para la próxima corrida"))
            return False
        self.visto(socio, sobre, pendiente=True)
        self.con_novedad.add(socio)
        self.por_borrar.append(ruta)
        return True

    def pendientes(self):
        """[(socio, número, archivo)] de lo que espera el si, en orden. De paso:
        - un archivo de 'pendientes' cuyo número no figura como "traído y sin entregar" (ya
          se entregó y la corrida se cortó antes de borrarlo, o alguien lo puso a mano) se
          borra sin preguntar: nunca se entrega dos veces;
        - lo que es de una clave que ya no se usa (se renovó, o se quitó el socio) se
          descarta con aviso."""
        carpeta = self.carpeta_de_pendientes()
        if not es_carpeta_de_verdad(carpeta):
            return []
        de_quien = {huella_de_clave(f["clave"]): s for s, f in self.fichas.items()}
        try:
            nombres = sorted(os.listdir(carpeta))
        except OSError:
            return []
        esperan, viejos = [], 0
        for nombre in nombres:
            forma = _PENDIENTE_DE_SOCIO.fullmatch(nombre)
            if not forma:
                continue
            ruta = os.path.join(carpeta, nombre)
            socio, numero = de_quien.get(forma.group(1)), int(forma.group(2))
            if socio is None:
                viejos += 1
                self.rechazos.append((None, None, ruta, (
                    "esperaba el si con una clave que ya no se usa (se renovó la clave o se "
                    "quitó el socio): se descarta")))
                self.tocado = True
                continue
            if socio not in self.listos:
                continue  # (ese socio está frenado: no se toca hasta que se resuelva)
            if numero not in self.estado[socio]["traidos"]:
                self.locales_por_borrar.append(ruta)
                self.tocado = True
                continue
            esperan.append((socio, numero, ruta))
        if viejos:
            self.avisar(f"{cuantos_mensajes(viejos)} que "
                        f"{'esperaba' if viejos == 1 else 'esperaban'} tu si "
                        f"{'era' if viejos == 1 else 'eran'} de una clave que ya no se usa: "
                        f"se {'descarta' if viejos == 1 else 'descartan'} (quedan en "
                        f"{self.buzon.donde_van_los_rechazados()})")
        return esperan

    def releer(self, socio, numero, ruta):
        """El sobre de ese pendiente, con la firma comprobada DE NUEVO: lo que está en
        'pendientes' es un archivo de esta máquina, y alguien lo pudo cambiar. NoSeEntrega
        si no es el mismo que llegó; OSError si ahora no se puede abrir."""
        with abrir_sin_seguir(ruta) as f:
            crudo = f.read(MAX_SOBRE + 1)
        try:
            if len(crudo) > MAX_SOBRE:
                raise ValueError
            datos, repetidas = json_de_sobre(crudo)
        except (ValueError, RecursionError):
            raise NoSeEntrega("ya no se entiende")
        motivo = self.autenticar(socio, datos, repetidas)
        if motivo:
            raise NoSeEntrega(motivo)
        marca = self.estado[socio]["vistos"].get(str(numero))
        if datos["socio"]["numero"] != numero or marca not in (None, datos["firma"][:16]):
            raise NoSeEntrega("no es el mismo sobre que llegó con ese número")
        return datos

    def resuelto(self, socio, numero, ruta, entregado=True):
        """Ese pendiente ya no espera: se entregó (o se resolvió sin entregar). El número
        deja de figurar "sin entregar" en la MISMA escritura de memoria que guarda el
        estado del agente; el archivo se borra después."""
        est = self.estado[socio]
        if numero in est["traidos"]:
            est["traidos"].remove(numero)
        self.locales_por_borrar.append(ruta)
        self.tocado = True
        if entregado:
            self.atendi[socio] = self.atendi.get(socio, 0) + 1

    def descartar(self, socio, numero, ruta, motivo, avisar=True):
        """Un pendiente que no se entrega: sale de la cuenta y va a 'rechazados'."""
        est = self.estado[socio]
        if numero in est["traidos"]:
            est["traidos"].remove(numero)
        self.rechazar(socio, None, motivo, local=ruta, avisar=avisar)

    def anotar_falla(self, socio, id, numero):
        """De ese mensaje enviado ya se aceptó un aviso de falla (el de ese número): no se
        acepta otro."""
        anotado = self.estado[socio]["ids"].get(id)
        if anotado is not None:
            self.estado[socio]["ids"][id] = anotado[:2] + [numero]
            self.tocado = True

    def cambio(self):
        return bool(self.tocado or self.borradores or self.deje)

    def acomodar(self):
        """Después de guardar la memoria: copia lo rechazado a 'rechazados', y borra de la
        compartida lo ya atendido y de 'pendientes' lo ya resuelto. De la compartida solo
        se borra lo que se abrió sin seguir accesos directos y era un sobre (o decía
        serlo), y solo si su carpeta sigue siendo una carpeta de verdad."""
        sin_lugar = {}
        for socio, crudo, local, motivo in self.rechazos:
            if not self.guardar_rechazo(socio, crudo, local, motivo):
                sin_lugar[socio] = sin_lugar.get(socio, 0) + 1
        self.sin_copia += sum(sin_lugar.values())
        for socio, cuantos in sin_lugar.items():
            self.avisar(
                f"en {self.buzon.donde_van_los_rechazados()} ya hay "
                f"{MAX_RECHAZADOS_DE_SOCIO} rechazados de {socio or 'socios'} (o más de "
                f"{MAX_PESO_DE_RECHAZADOS // 1_000_000} MB): {cuantos} más no se "
                "guardaron. Revisá esa carpeta y vaciala")
        reales = {}
        for ruta in self.por_borrar:
            carpeta = os.path.dirname(ruta)
            if carpeta not in reales:
                reales[carpeta] = es_carpeta_real(carpeta)
            if not reales[carpeta]:
                continue
            try:
                os.remove(ruta)
            except OSError:
                pass
        for ruta in self.locales_por_borrar:
            try:
                os.remove(ruta)
            except OSError:
                pass
        self.rechazos, self.por_borrar, self.locales_por_borrar = [], [], []
        self.tocado = False

    def guardar_rechazo(self, socio, crudo, local, motivo):
        """Deja en 'rechazados' ese archivo (con un nombre que arma Mate, nunca con el
        nombre ni el id ajenos) y su motivo al lado. Con cupo por socio: lo que llega de
        afuera sin firma no puede llenar el disco. Devuelve False si no había lugar."""
        carpeta = os.path.join(self.buzon.carpeta, "rechazados")
        prefijo = f"socio-{self.huella(socio) or 'viejo'}-"
        try:
            if os.path.lexists(carpeta) and not es_carpeta_de_verdad(carpeta):
                raise OSError
            os.makedirs(carpeta, exist_ok=True)
            hay = [n for n in os.listdir(carpeta)
                   if n.startswith(prefijo) and n.endswith(".json")]
            pesan = sum(os.path.getsize(os.path.join(carpeta, n)) for n in hay)
            if len(hay) >= MAX_RECHAZADOS_DE_SOCIO or crudo is None and local is None \
                    or pesan + len(crudo or b"") > MAX_PESO_DE_RECHAZADOS:
                if local is not None:
                    os.remove(local)
                return False
            nombre = (f"{prefijo}{datetime.datetime.now():%Y%m%d-%H%M%S}-"
                      f"{secrets.token_hex(3)}")
            destino = os.path.join(carpeta, nombre + ".json")
            if local is not None:
                os.replace(local, destino)
            else:
                with open(destino, "xb") as f:
                    f.write(crudo)
            escribir_entero(os.path.join(carpeta, nombre + ".motivo.txt"), (
                f"Mate no entregó este mensaje"
                + (f" de tu socio {socio}" if socio else "")
                + f" ({datetime.datetime.now():%d/%m/%Y %H:%M}).\n"
                f"Motivo: {motivo}\n"
                "Los mensajes de otro negocio no se reintentan a mano: si hacía falta, "
                "pedile a tu socio que lo mande de nuevo.\n"))
        except (OSError, ValueError):
            return True  # (no se pudo escribir: no es falta de lugar, y ya se avisó arriba)
        return True

    def resumen(self):
        renglones = []
        for socio, n in self.atendi.items():
            renglones.append(f"Socios: entregué {cuantos_mensajes(n)} de {socio}.")
        if self.no_entregados:
            guardados = max(0, self.no_entregados - self.sin_copia)
            donde = self.buzon.donde_van_los_rechazados()
            renglones.append(
                f"Socios: {self.no_entregados} no se "
                f"{'entregó' if self.no_entregados == 1 else 'entregaron'}: "
                + (f"{'está' if self.no_entregados == 1 else 'están'} en {donde}."
                   if not self.sin_copia else
                   f"{guardados} {'quedó' if guardados == 1 else 'quedaron'} en {donde} y "
                   f"de {'el otro' if self.sin_copia == 1 else f'los otros {self.sin_copia}'}"
                   " no se guardó copia (el cupo de rechazados estaba lleno)."))
        for socio, n in self.deje.items():
            renglones.append(f"Socios: dejé {cuantos_mensajes(n)} para {socio} en la carpeta "
                             f"compartida; {'le llega' if n == 1 else 'le llegan'} cuando "
                             "corra su programa (y diga que si).")
        if self.miro:
            # Una corrida sin nada que mandar ni recibir también lo dice: el dueño que
            # corre los pasos en otro orden tiene que saber que anduvo.
            for socio in sorted(self.listos):
                if socio in self.con_novedad or socio in self.atendi or socio in self.deje \
                        or (self.estado.get(socio) or {}).get("traidos") \
                        or not self._carpetas.get(socio):
                    continue
                renglones.append(f"Socios: no llegó nada nuevo de {socio}.")
        return renglones


def avisos_de_socios(programa):
    """Lo que conviene saber antes de correr un programa con socios (avisos, no errores):
    un agente que recibe mensajes de otro negocio y además consulta a la IA le pasa a la IA
    texto ajeno. Los frenos siguen valiendo, pero ese texto no es de confianza."""
    avisos = []
    agentes = {s[2]: s for s in programa if s[0] == "agente"}
    con_ia = {nombre for nombre, s in agentes.items() if _nombra(s, {"consultar_ia"})}

    def les_puede_pasar(nombre):
        """Los agentes que consultan a la IA y a los que ese agente nombra (les manda o
        les pregunta), directo o a través de otros: a esos les puede pasar el texto."""
        vistos, por_ver = {nombre}, [nombre]
        while por_ver:
            actual = agentes[por_ver.pop()]
            for otro in agentes:
                if otro not in vistos and _nombra(actual, {otro}):
                    vistos.add(otro)
                    por_ver.append(otro)
        return sorted((vistos - {nombre}) & con_ia)

    for socio, tipos in socios_declarados(programa).items():
        for tipo in tipos:
            for nombre, s in agentes.items():
                if not any(m[1] == tipo for m in s[4]):
                    continue
                if nombre in con_ia:
                    avisos.append(
                        f"{nombre} recibe {tipo} del socio {socio} y además consulta a la "
                        "IA: lo que escribe otro negocio es texto ajeno aunque le hayas "
                        "dicho que si. No se lo pases a consultar_ia() tal cual (los "
                        "'frenos' lo limitan, no lo vuelven confiable)")
                for otro in les_puede_pasar(nombre):
                    avisos.append(
                        f"{nombre} recibe {tipo} del socio {socio} y nombra a {otro}, que "
                        "consulta a la IA: lo que escribe otro negocio es texto ajeno "
                        "aunque le hayas dicho que si. Que no le llegue a consultar_ia() "
                        "tal cual, tampoco pasando por otro agente (los 'frenos' lo "
                        "limitan, no lo vuelven confiable)")
    return list(dict.fromkeys(avisos))


def huecos_de_socio(est, tope=5):
    """Los números de ese socio que faltan entre los ya vistos, como rangos ("14", "20 a
    25") y con tope: un sobre perdido o borrado en el camino se nota. Nunca se recorre
    número por número: un socio que manda el 10^15 no cuelga nada."""
    vistos = sorted(int(n) for n in est.get("vistos", {}))
    rangos, anterior = [], est.get("piso", 0)
    for n in vistos:
        if n > anterior + 1:
            rangos.append(str(anterior + 1) if n == anterior + 2
                          else f"{anterior + 1} a {n - 1}")
        anterior = max(anterior, n)
    return rangos[:tope] + (["..."] if len(rangos) > tope else [])


def leccion_limpia(texto):
    """La lección en un solo renglón (o el error, si está vacía o es demasiado larga)."""
    texto = " ".join(texto.split())
    if not texto:
        raise ErrorMate("la lección está vacía: escribí qué tiene que tener en cuenta el agente")
    if len(texto) > LARGO_DE_LECCION:
        raise ErrorMate(
            f"la lección tiene {len(texto)} letras y el tope es {LARGO_DE_LECCION} (cada "
            "lección viaja en cada consulta a la IA, y eso se paga): escribila más corta, "
            "o partila en dos")
    return texto


def sumar_leccion(lecciones, texto, fecha):
    """(la lista con esa lección al final, cuántas viejas hubo que olvidar). Si ya la
    tenía, devuelve la misma lista: una lección no se anota dos veces."""
    if any(leccion["texto"] == texto for leccion in lecciones):
        return lecciones, 0
    nuevas = lecciones + [{"fecha": fecha, "texto": texto}]
    sobran = max(0, len(nuevas) - MAX_LECCIONES)
    return nuevas[sobran:], sobran


def con_lecciones(instrucciones, lecciones):
    """Las instrucciones para la IA con las lecciones del agente al final, bajo su título."""
    lista = "\n".join(f"{i}. {leccion}" for i, leccion in enumerate(lecciones, 1))
    return f"{instrucciones.rstrip()}\n\n{TITULO_DE_LECCIONES}\n{lista}".lstrip()


# ─────────────── Frenos para la IA, tope de gasto y lecciones propuestas (0.5) ───────────────
# Un agente declara sus frenos:
#     frenos {
#         precios: lista                  (los importes que la IA puede nombrar)
#         prohibido: ["descuento"]        (palabras o temas que no puede tocar)
#         largo: 400                      (letras, como mucho)
#         reserva: "Eso te lo confirma una persona, ya te paso."
#         consultas_por_dia: 100          (tope de gasto)
#         tokens_por_dia: 200000
#     }
# y MATE (no la IA) revisa cada respuesta de consultar_ia() de ese agente antes de
# devolverla. Si una regla no se cumple, consulta UNA vez más diciéndole a la IA qué regla
# rompió; si la vuelve a romper, devuelve el texto de 'reserva'. Cada freno que salta queda
# en la bitácora y deja una lección PROPUESTA, que no se usa hasta que el dueño la aprueba.

# regla -> (qué tipo de valor lleva, un ejemplo, qué hace)
REGLAS_DE_FRENO = {
    "precios": (("lista", "mapa"), "precios: lista",
                "los importes en pesos que puede nombrar la IA: una lista de números, o la "
                "tabla de precios entera (valen todos sus números)"),
    "prohibido": (("lista",), 'prohibido: ["descuento", "garantía"]',
                  "palabras o temas que no pueden aparecer en la respuesta"),
    "largo": (("numero",), "largo: 400", "cuántas letras puede tener la respuesta, como mucho"),
    "reserva": (("texto",), 'reserva: "Eso te lo confirma una persona, ya te paso."',
                "lo que se contesta cuando la IA rompe una regla dos veces, o se llegó al tope"),
    "consultas_por_dia": (("numero",), "consultas_por_dia: 100",
                          "cuántas consultas a la IA puede hacer el agente por día"),
    "tokens_por_dia": (("numero",), "tokens_por_dia: 200000",
                       "cuántos tokens (lo que cobra el servicio) puede gastar por día"),
}
REGLAS_EN_LISTA = ", ".join(REGLAS_DE_FRENO)
REGLAS_DE_CONTENIDO = ("precios", "prohibido", "largo")  # las que miran la respuesta
MAX_PROPUESTAS = 20  # lecciones propuestas (sin aprobar) por agente; se va la más vieja
DIAS_DE_GASTO = 30  # cuántos días se guarda la cuenta de consultas de cada agente
MAX_PROHIBIDOS = 100  # textos en la regla 'prohibido'
# Un número suelto (sin $ ni "pesos") después de "sale", "cuesta"... cuenta como importe
# solo desde este valor: así "sale 2 por 1" o "vale 3 puntos" no hacen saltar el freno.
IMPORTE_SUELTO_DESDE = 100

_NUM_DE_IMPORTE = (r"(?:\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d{1,3}(?:,\d{3})+(?:\.\d+)?"
                   r"|\d+(?:[.,]\d+)?)(?!\d)")
_MIL_O_MILLON = r"(?:\s*(mil|millones|mill[oó]n)\b)?"
# $ 3.500   $3500   $ 3.500,00   AR$ 1.234,50   $ 3 mil   $ **4.000** (la negrita que a
# veces pone la IA)   $ -4000   USD 40   U$S 40
_IMPORTE_CON_SIGNO = re.compile(
    r"(?:[$＄]|\busd\b|\bu\$s|\bars\b|€)[\s*_]*[-–]?\s*(" + _NUM_DE_IMPORTE + ")" + _MIL_O_MILLON, re.I)
# 3500 pesos   3.500 pesos   3 mil pesos   2 millones de pesos   3500$   40 dólares   4000.-
_IMPORTE_CON_PESOS = re.compile(
    r"(?<![\w.,$])(" + _NUM_DE_IMPORTE + ")" + _MIL_O_MILLON
    + r"(?:(?:\s+de)?[\s*_]*(?:pesos?\b|pesitos\b|mangos\b|\$|d[oó]lar(?:es)?\b|usd\b|u\$s|ars\b|"
    r"euros?\b|€)"
    r"|[.,]\s?[-–—](?![\w-]))", re.I)
# sale 3500   cuesta 3.500   el precio es de 3500   total: 9.999   te lo dejo a 2.000   (sin
# $ ni "pesos"). Vale aunque después venga una palabra cualquiera ("sale 4000 hoy", "sale
# 4000 x kilo"), salvo que esa palabra diga que el número es una cantidad y no plata.
_NO_ES_PLATA = (r"gramos?|grs?|g|kg|kgs|kilos?|litros?|lts?|l|ml|cc|cm|mm|m|mts?|metros?|km|"
                r"unidades|unidad|u|horas?|hs|h|minutos?|min|d[ií]as?|semanas?|mes|meses|"
                r"años?|puntos?|personas?|cuotas?|veces|calor[ií]as|kcal|mg|watts?|w|"
                r"pulgadas?|productos?|art[ií]culos?|clientes?|pedidos?|cajas?|paquetes?|"
                r"bolsas?|botellas?|latas?|docenas?|locales|sucursales")
_IMPORTE_SUELTO = re.compile(
    r"\b(?:sale|salen|cuesta|cuestan|vale|valen|precios?|cobramos|total|dejo|dejamos)\b"
    r"(?:\s+(?:es|son|de|a|en|final|total|solo|sólo|del|el|la|por|kilo|kg|litro|unidad|lista|"
    r"unitario|unos|aprox\.?|aproximadamente|como|casi))*[\s*_~]*:?[\s*_~]*(" + _NUM_DE_IMPORTE + ")"
    + _MIL_O_MILLON
    + r"(?!\s*[/%:°x-]\s*\d)(?!\s*[%°])"
    r"(?!\s*(?:" + _NO_ES_PLATA + r")(?![\wáéíóúñü]))", re.I)


def valores_de_importe(escrito, cuanto=None):
    """Lo que puede valer un importe escrito. "3.500" es 3500 (acá el punto es de los
    miles) y "3,5" es tres y medio. "3,500" puede ser las dos cosas (a la inglesa son tres
    mil quinientos): ante la duda se dan las dos lecturas, y alcanza con que una esté
    permitida."""
    valores = set()
    if re.fullmatch(r"\d{1,3}(\.\d{3})+(,\d+)?", escrito):  # a la argentina: 1.234,50
        valores.add(float(escrito.replace(".", "").replace(",", ".")))
    elif re.fullmatch(r"\d{1,3}(,\d{3})+(\.\d+)?", escrito):  # a la inglesa: 1,234.50
        valores.add(float(escrito.replace(",", "")))
        if escrito.count(",") == 1 and "." not in escrito:
            valores.add(float(escrito.replace(",", ".")))
    else:
        valores.add(float(escrito.replace(",", ".")))
    veces = {"mil": 1000}.get((cuanto or "").lower(), 1_000_000 if cuanto else 1)
    return {v * veces for v in valores}


def importes_de(texto):
    """Los importes que nombra un texto: [(como está escrito, lo que puede valer)].
    Cuenta como importe un número con el signo $ adelante o atrás (aunque en el medio haya
    asteriscos de negrita o un signo menos), con "pesos", "dólares", "USD" o "euros", el
    que termina en ".-" (4000.-), o el suelto justo después de "sale", "cuesta", "vale",
    "precio", "cobramos", "total" o "te lo dejo a" (y de 100 o más), venga lo que venga
    después, salvo una unidad que diga que es una cantidad ("sale 500 gramos"). Lo demás
    (cantidades, teléfonos, fechas, porcentajes, un segundo número lejos de esas palabras)
    no se mira: ante la duda, este freno prefiere no saltar. Tampoco ve los importes
    escritos con letras ("cuatro mil") ni mira la moneda: compara números."""
    vistos = {}
    for patron, suelto in ((_IMPORTE_CON_SIGNO, False), (_IMPORTE_CON_PESOS, False),
                           (_IMPORTE_SUELTO, True)):
        for m in patron.finditer(texto):
            if m.start(1) in vistos:
                continue
            valores = valores_de_importe(m.group(1), m.group(2))
            if suelto and max(valores) < IMPORTE_SUELTO_DESDE:
                continue
            escrito = m.group(1) + (f" {m.group(2)}" if m.group(2) else "")
            vistos[m.start(1)] = (escrito if suelto else "$ " + escrito, valores)
    return [vistos[i] for i in sorted(vistos)]


_PARECE_IMPORTE = re.compile(r"[+-]?\$?\s*(?!0\d)\d[\d.,]*\s*(?:[.,]-|\$|pesos)?")


def importes_como_texto(valor, hondo=0):
    """Los textos de un valor (una lista, una tabla) que parecen importes pero no quedaron
    como número ("1,234.50", "3500 pesos"): el freno de precios no los puede contar."""
    if isinstance(valor, str):
        return [valor] if _PARECE_IMPORTE.fullmatch(valor.strip()) else []
    if hondo > 20:
        return []
    if isinstance(valor, Registro):
        valor = valor.campos
    if isinstance(valor, dict):
        valor = list(valor.values())
    if isinstance(valor, list):
        return [t for x in valor for t in importes_como_texto(x, hondo + 1)]
    return []


def numeros_permitidos(valor, hondo=0):
    """Todos los números que hay en un valor: en una lista, en una tabla (una lista de
    mapas), en un mapa o en un mensaje. Son los importes que la IA puede nombrar."""
    if es_num(valor):
        return {float(valor)}
    if hondo > 20:
        return set()
    if isinstance(valor, Registro):
        valor = valor.campos
    if isinstance(valor, dict):
        valor = list(valor.values())
    if isinstance(valor, list):
        return set().union(*(numeros_permitidos(x, hondo + 1) for x in valor))
    return set()


def reglas_rotas(respuesta, frenos):
    """Qué reglas de esos frenos no cumple la respuesta: [(regla, qué pasó, la lección que
    se propone)]. Una lista vacía quiere decir que la respuesta pasa."""
    rotas = []
    if frenos.get("precios") is not None:
        permitidos = frenos["precios"]
        ajenos = [escrito for escrito, valores in importes_de(respuesta)
                  if not any(abs(v - p) < 0.005 for v in valores for p in permitidos)]
        if ajenos:
            ajenos = list(dict.fromkeys(ajenos))
            cuales = ", ".join(ajenos[:3]) + (" y otros" if len(ajenos) > 3 else "")
            rotas.append(("precios", (
                f"nombró {'el importe' if len(ajenos) == 1 else 'los importes'} {cuales}, "
                f"que no está{'' if len(ajenos) == 1 else 'n'} entre los precios permitidos"),
                "No nombres ningún importe que no esté en los precios que te dieron. Si no "
                "sabés un precio, decí que lo confirma una persona."))
    if frenos.get("prohibido"):
        llano = " ".join(sin_tildes(respuesta).lower().split())
        for palabra in frenos["prohibido"]:
            buscada = " ".join(sin_tildes(palabra).lower().split())
            if buscada and re.search(r"(?<!\w)" + re.escape(buscada), llano):
                rotas.append(("prohibido", f'dijo "{palabra}", que está entre lo prohibido',
                              f'No hables de "{en_un_renglon(palabra, 80)}": de eso acá no '
                              "se habla. Si te lo preguntan, decí que lo ve una persona."))
                break
    if frenos.get("largo") is not None and len(respuesta) > frenos["largo"]:
        rotas.append(("largo", f"la respuesta tiene {len(respuesta)} letras y el máximo es "
                               f"{frenos['largo']}",
                      f"Contestá corto: como mucho {frenos['largo']} letras."))
    return rotas


def aviso_de_freno(pregunta, rotas):
    """La consulta que se manda en el segundo intento: la misma, más qué regla se rompió."""
    que = "; ".join(motivo for _, motivo, _ in rotas)
    return (f"{pregunta}\n\n[Aviso del sistema: tu respuesta anterior a esta misma consulta "
            f"no se pudo usar porque {que}. Contestá de nuevo cumpliendo esa regla. Si no "
            "podés contestar sin romperla, decí que eso lo confirma una persona.]")


def sumar_propuesta(propuestas, lecciones, texto, motivo, fecha):
    """La lista de propuestas con esa lección al final (o la misma lista, si ya estaba
    propuesta o ya es una lección aprobada). Nunca más que el tope: se va la más vieja."""
    texto = en_un_renglon(texto, LARGO_DE_LECCION)
    if any(p["texto"] == texto for p in propuestas) \
            or any(leccion["texto"] == texto for leccion in lecciones):
        return propuestas
    nuevas = propuestas + [{"fecha": fecha, "texto": texto,
                            "motivo": en_un_renglon(motivo, 400)}]
    return nuevas[-MAX_PROPUESTAS:]


def gasto_limpio(gasto):
    """La cuenta de consultas de un agente como se guarda: {"2026-11-21": {"consultas": 3,
    "simuladas": 0, "tokens": 1200}}, con los últimos DIAS_DE_GASTO días y solo los que
    tienen algo. Lo que no tenga esa forma (alguien editó el archivo) se saltea."""
    limpio = {}
    for dia, cuenta in (gasto.items() if isinstance(gasto, dict) else ()):
        if not (isinstance(dia, str) and re.fullmatch(r"\d{4}-\d\d-\d\d", dia)
                and isinstance(cuenta, dict)):
            continue
        numeros = {k: cuenta.get(k, 0) for k in ("consultas", "simuladas", "tokens")}
        if all(type(n) is int and 0 <= n < 10 ** 15 for n in numeros.values()) \
                and any(numeros.values()):
            limpio[dia] = numeros
    return {dia: limpio[dia] for dia in sorted(limpio)[-DIAS_DE_GASTO:]}


def tokens_de(datos):
    """Los tokens que gastó una consulta, según lo que informa el servicio (los de la
    pregunta más los de la respuesta), o None si no lo dice."""
    uso = datos.get("usage") if isinstance(datos, dict) else None
    if not isinstance(uso, dict):
        return None
    partes = [uso.get(k) for k in ("input_tokens", "output_tokens")]
    if not all(type(n) is int and 0 <= n < 10 ** 12 for n in partes):
        return None
    return sum(partes)


# Lo que gastó la última consulta de verdad (lo deja pedir_a_la_ia): {"cobrada": True,
# "tokens": 1234}. 'cobrada' está también cuando la respuesta llegó y no sirvió (cortada, sin
# texto, frenada por un filtro): esa consulta se paga igual, y entra en el tope por día.
_USO_DE_LA_IA = {}


def usa_memoria(programa, propios=None):
    """¿El programa usa lo de aprender: un 'estado recordado', aprender(), lecciones() o
    los 'frenos' de un agente?
    Si no, 'correr' no lee ni escribe ningún archivo de más. (Si el programa le puso
    'aprender' o 'lecciones' a algo suyo, llamarlo no es usar lo de aprender.)"""
    if propios is None:
        propios = set(_ligaduras(programa))
    if isinstance(programa, EstadoRecordado):
        return True
    if not isinstance(programa, (list, tuple)):
        return False
    if _es_nodo(programa, "agente", 7) and programa[6]:
        return True  # un agente con frenos lleva la cuenta de sus consultas (0.5)
    if _es_nodo(programa, "llamar", 4) and _es_nodo(programa[2], "nombre", 3) \
            and programa[2][2] in ("aprender", "lecciones") and programa[2][2] not in propios:
        return True
    return any(usa_memoria(parte, propios) for parte in programa)


def se_puede_recordar(v):
    """Solo se recuerdan datos: ni agentes ni funciones (tampoco adentro de una lista)."""
    if isinstance(v, (Agente, Funcion, Nativa, ModuloPython)):
        return False
    if isinstance(v, (list, dict)):
        return all(se_puede_recordar(x) for x in (v.values() if isinstance(v, dict) else v))
    if isinstance(v, Registro):
        return all(se_puede_recordar(x) for x in v.campos.values())
    return True


def leer_renglones(ruta):
    """Los renglones de un archivo que escribe Mate (la bitácora, el registro). Si alguno
    trae letras que no se entienden (se dañó, o alguien pegó algo raro), solo ese se lee
    distinto: los demás conservan sus tildes."""
    with open(ruta, "rb") as f:
        datos = f.read()
    if datos[:2] in (b"\xff\xfe", b"\xfe\xff") or (
            len(datos) >= 4 and datos.count(0) >= len(datos) // 4):
        return leer_fuente(ruta).split("\n")  # guardado como "Unicode" en el Bloc de notas
    renglones = []
    for crudo in datos.replace(b"\r\n", b"\n").replace(b"\r", b"\n").split(b"\n"):
        try:
            renglones.append(crudo.decode("utf-8-sig"))
        except UnicodeError:
            renglones.append(crudo.decode("cp1252", errors="replace"))
    return renglones


def renglones_de_bitacora(ruta):
    """Las fallas anotadas en la bitácora, una por renglón (sin los títulos). Si el
    archivo no existe, ninguna; si no se puede leer, un ErrorMate."""
    try:
        renglones = leer_renglones(ruta)
    except FileNotFoundError:
        return []
    except (OSError, ErrorMate):
        raise ErrorMate(f"no pude leer la bitácora '{ruta}': fijate que no esté abierta en "
                        "otro programa")
    return [r.strip() for r in renglones if r.strip() and not r.startswith("#")]


def guardar_bitacora(ruta, programa, fallas, escrito=None):
    """Suma las fallas de esta corrida al final de la bitácora y deja las últimas
    MAX_BITACORA. Cada falla es (fecha, agente, qué pasó, qué atendía, motivo). La clave
    de la IA nunca queda escrita. Devuelve None o por qué no se pudo. escrito: el
    programa como se lo nombró al correrlo (con su carpeta), para el comando de arriba."""
    if not fallas:
        return None
    clave = os.environ.get("ANTHROPIC_API_KEY", "").strip().strip("\"'").strip()
    nuevos = [tapar_clave(" | ".join(
        [fecha] + [en_un_renglon(parte, 300).replace("|", "/") for parte in (quien, que, atendia)]
        + [en_un_renglon(motivo, 400)]), clave) for fecha, quien, que, atendia, motivo in fallas]
    try:
        renglones = (renglones_de_bitacora(ruta) + nuevos)[-MAX_BITACORA:]
        escribir_entero(ruta, "\n".join([
            f"# Bitácora de {programa}: las fallas de sus agentes, la más nueva abajo.",
            "# Cada renglón:  fecha | agente | qué pasó | qué mensaje atendía | el motivo",
            f"# La escribe Mate sola y guarda las últimas {MAX_BITACORA}. Para leerla "
            f"resumida:  {como_se_llama()} bitacora {para_pegar(escrito or programa)}",
            "# Si la borrás no pasa nada: empieza de nuevo.", ""] + renglones) + "\n")
    except (OSError, ValueError, ErrorMate):
        return (f"no pude anotar las fallas de esta corrida en la bitácora '{ruta}': fijate "
                "que no esté abierta en otro programa")
    return None


def para_pegar(a):
    """Un archivo o un nombre como hay que escribirlo en una orden: entre comillas si trae
    espacios, así el comando que Mate sugiere se puede copiar y pegar."""
    return f'"{a}"' if not a or re.search(r"\s", a) else a


_QUIEN_ME_LANZO = None  # (se averigua una sola vez, la primera que hace falta)


def quien_me_lanzo():
    """En Windows, 'py' si este Python lo arrancó el lanzador py.exe (la persona escribió
    'py mate\\mate.py ...'); si no, o si no se puede saber, ''. Se fija en el nombre del
    programa que arrancó a este (y, si ese también es un python.exe, como pasa con un
    entorno virtual, en el de más arriba). Solo mira nombres de programas: no lee ni guarda
    nada más, y cualquier tropiezo se toma como 'no se sabe'."""
    global _QUIEN_ME_LANZO
    if _QUIEN_ME_LANZO is None:
        try:
            _QUIEN_ME_LANZO = _lanzador_en_windows() if os.name == "nt" else ""
        except Exception:  # (una función de Windows que no está, un permiso...)
            _QUIEN_ME_LANZO = ""
    return _QUIEN_ME_LANZO


def _lanzador_en_windows():
    import ctypes
    from ctypes import wintypes

    class Proceso(ctypes.Structure):  # (PROCESSENTRY32W, de la API de Windows)
        _fields_ = [("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD),
                    ("th32ProcessID", wintypes.DWORD), ("th32DefaultHeapID", ctypes.c_size_t),
                    ("th32ModuleID", wintypes.DWORD), ("cntThreads", wintypes.DWORD),
                    ("th32ParentProcessID", wintypes.DWORD), ("pcPriClassBase", wintypes.LONG),
                    ("dwFlags", wintypes.DWORD), ("szExeFile", wintypes.WCHAR * 260)]

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    kernel.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    for funcion in (kernel.Process32FirstW, kernel.Process32NextW):
        funcion.restype = wintypes.BOOL
        funcion.argtypes = [wintypes.HANDLE, ctypes.POINTER(Proceso)]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    foto = kernel.CreateToolhelp32Snapshot(2, 0)  # (2: la lista de programas andando)
    if foto in (None, wintypes.HANDLE(-1).value):
        return ""
    procesos = {}  # número de proceso -> (el del que lo arrancó, nombre del programa)
    try:
        uno = Proceso()
        uno.dwSize = ctypes.sizeof(Proceso)
        sigue = kernel.Process32FirstW(foto, ctypes.byref(uno))
        while sigue:
            procesos[uno.th32ProcessID] = (uno.th32ParentProcessID, uno.szExeFile.lower())
            sigue = kernel.Process32NextW(foto, ctypes.byref(uno))
    finally:
        kernel.CloseHandle(foto)
    return lanzador_entre(procesos, os.getpid())


def lanzador_entre(procesos, yo):
    """De una lista de programas andando {número: (número del que lo arrancó, nombre)},
    'py' si al programa 'yo' lo arrancó py.exe, pasando por arriba de los python.exe
    intermedios (los pone un entorno virtual); si no, ''."""
    vistos = {yo}
    padre = procesos.get(yo, (None, ""))[0]
    while padre in procesos and padre not in vistos and len(vistos) <= 4:
        vistos.add(padre)
        padre, nombre = procesos[padre]
        if nombre in ("py.exe", "pyw.exe"):
            return "py"
        if not re.fullmatch(r"python[\d.]*w?(_d)?\.exe", nombre):
            break
    return ""


def orden_segun(avisada, lanzador, en_windows):
    """La orden para correr Mate, según lo que se sabe de cómo lo llamó la persona:
    'avisada' es la variable MATE_ORDEN ('mate' la pone el lanzador de instalar.bat; 'py' o
    'python' la puede poner a mano quien quiera fijar la forma), 'lanzador' es lo que da
    quien_me_lanzo(). Si no se sabe nada, la de siempre."""
    avisada = (avisada or "").strip().lower()
    if avisada == "mate":
        return "mate"
    if not en_windows:
        return "python3 mate/mate.py"
    if avisada in ("py", "python"):
        return f"{avisada} mate\\mate.py"
    return "py mate\\mate.py" if lanzador == "py" else "python mate\\mate.py"


def como_se_llama():
    """Cómo se escribe la orden para correr Mate en esta computadora, con la forma que usó
    la persona. Si Mate se instaló con instalar.bat, la orden corta 'mate' anda desde
    cualquier carpeta: el lanzador que deja el instalador lo avisa con la variable
    MATE_ORDEN, y los comandos que Mate sugiere se escriben con esa orden. En Windows, si
    lo llamaron con 'py mate\\mate.py' (hay computadoras donde 'python' no existe), los
    comandos sugeridos dicen 'py'. Si no se puede saber, 'python mate\\mate.py'."""
    avisada = os.environ.get("MATE_ORDEN", "")
    en_windows = os.name == "nt"
    lanzador = quien_me_lanzo() if en_windows and avisada.strip().lower() not in (
        "mate", "py", "python") else ""
    return orden_segun(avisada, lanzador, en_windows)


def con_la_orden_de_esta_computadora(texto):
    """Un texto fijo que dice 'python mate\\mate.py ...' (la guía, una clase del curso), con
    'py' en lugar de 'python' cuando Mate sabe que la persona lo llama así. Si no, igual."""
    if como_se_llama() == "py mate\\mate.py":
        return texto.replace("python mate\\mate.py", "py mate\\mate.py")
    return texto


def incluidas():
    """Los nombres de las funciones incluidas (mostrar, texto, pesos...)."""
    return frozenset(FUNCIONES)


# ───────────────────────── Puente a Python (0.5) ─────────────────────────
# usar python "ayudas.py" trae las funciones de un archivo de Python que está al lado del
# programa, y se llaman ayudas.nombre(...). Sirve para sumar lo que Mate no trae sin tocar
# el intérprete. Tres reglas:
# - Solo cruzan valores simples: números, textos, verdadero/falso, nada, listas y mapas. Van
#   y vuelven COPIADOS: el Python no puede cambiarle una lista a Mate por atrás.
# - Un error dentro del Python llega como un error de Mate, con el renglón del .mate, y se
#   ataja con 'intentar'.
# - OJO: ese Python no tiene ninguno de los cuidados de Mate. Corre con todos los permisos
#   de la computadora (puede leer, escribir y borrar archivos, y salir a internet), también
#   con la orden 'probar'. Solo hay que usar archivos propios o de alguien de confianza.

# Los errores de Python más comunes, dichos en castellano (después va lo que dijo Python).
_ERRORES_DE_PYTHON = {
    "ZeroDivisionError": "una división por cero",
    "ValueError": "un valor que no sirve para lo que se quiso hacer",
    "TypeError": "una cuenta entre cosas de distinto tipo, o una función mal llamada",
    "KeyError": "una clave que no está en el diccionario",
    "IndexError": "una posición que no existe en la lista",
    "NameError": "un nombre que no existe (¿está mal escrito?)",
    "AttributeError": "se le pidió a un valor algo que no tiene",
    "FileNotFoundError": "un archivo que no está",
    "PermissionError": "falta permiso para tocar un archivo",
    "ModuleNotFoundError": "un 'import' de algo que no está instalado en esta computadora",
    "RecursionError": "una función que se llama a sí misma sin parar",
    "SystemExit": "el archivo quiso cerrar el programa (exit)",
}
SOLO_SIMPLES = "números, textos, verdadero o falso, nada, listas y mapas"


def dicho_por_python(e, ruta):
    """Un error de Python contado para quien no sabe Python: qué fue, en qué renglón del
    .py, y al final lo que dijo Python tal cual (eso viene en inglés)."""
    renglon, paso = None, e.__traceback__
    while paso is not None:  # el último renglón de ese archivo por el que pasó
        if paso.tb_frame.f_code.co_filename == ruta:
            renglon = paso.tb_lineno
        paso = paso.tb_next
    clase = type(e).__name__
    texto = str(e.args[0]) if clase == "KeyError" and e.args else str(e)
    crudo = recortado(f"{clase}: {texto}" if texto else clase, 300)
    que = _ERRORES_DE_PYTHON.get(clase)
    return ((f" (línea {renglon} de {os.path.basename(ruta)})" if renglon else "") + ": "
            + (f"{que}. Python dice: {crudo}" if que else f"Python dice: {crudo}"))


def a_python(v, donde):
    """Un valor de Mate, copiado, como lo recibe una función de Python."""
    if v is None or type(v) in (bool, int, float):
        return v
    if isinstance(v, str):
        return v[:]  # (un error atajado viaja como un texto común)
    if isinstance(v, list):
        return [a_python(x, donde) for x in v]
    if isinstance(v, dict):
        return {k[:]: a_python(x, donde) for k, x in v.items()}
    if isinstance(v, Registro):
        raise ErrorMate(f"{donde}(): a una función de Python solo se le pasan {SOLO_SIMPLES}, "
                        f"y recibió un mensaje {v.tipo}. Pasalo como mapa: a_mapa(...)",
                        familia="python")
    raise ErrorMate(f"{donde}(): a una función de Python solo se le pasan {SOLO_SIMPLES}, y "
                    f"recibió {un(v)}", familia="python")


def de_python(v, donde):
    """Lo que devolvió una función de Python, copiado, como valor de Mate."""
    if v is None or type(v) is bool:
        return v
    if type(v) is int:
        if v.bit_length() > MAX_BITS:
            raise ErrorMate(f"{donde}() devolvió un número demasiado grande para Mate",
                            familia="python")
        return v
    if type(v) is float:
        if not math.isfinite(v):
            raise ErrorMate(f"{donde}() devolvió un número que Mate no usa: infinito, o el "
                            "resultado de una cuenta imposible ('nan')", familia="python")
        return v
    if type(v) is str:
        if len(v) > MAX_LARGO:
            raise muy_largo()
        return v
    if isinstance(v, (list, tuple)):
        if len(v) > MAX_LARGO:
            raise muy_largo("la lista")
        return [de_python(x, donde) for x in v]
    if isinstance(v, dict):
        if len(v) > MAX_LARGO:
            raise muy_largo("la lista")
        for k in v:
            if type(k) is not str:
                raise ErrorMate(
                    f"{donde}() devolvió un diccionario con una clave que no es un texto "
                    f"({recortado(repr(k), 40)}): en Mate las claves de un mapa son textos. "
                    "Convertila en el .py con str(...)", familia="python")
        return {k: de_python(x, donde) for k, x in v.items()}
    raise ErrorMate(
        f"{donde}() devolvió algo que Mate no conoce (en Python se llama "
        f"'{type(v).__name__}'). A Mate solo vuelven números, textos, True o False, None, "
        "listas (o tuplas) y diccionarios con claves de texto. Convertilo en el .py antes "
        "de devolverlo", familia="python")


def funcion_de_python(completo, f, ruta):
    """La función de Python lista para llamarla desde Mate: controla cuántos valores lleva,
    copia lo que va y lo que vuelve, y lo que falle adentro sale como un error de Mate."""
    archivo, codigo = os.path.basename(ruta), f.__code__
    varios = bool(codigo.co_flags & 0x04)  # def f(*valores)
    maximo = None if varios else codigo.co_argcount
    minimo = codigo.co_argcount - len(f.__defaults__ or ())
    # Los parámetros que en Python solo se pueden dar con su nombre: desde Mate no se puede.
    con_nombre = codigo.co_varnames[codigo.co_argcount:
                                    codigo.co_argcount + codigo.co_kwonlyargcount]
    obligados = [n for n in con_nombre if n not in (f.__kwdefaults__ or {})]
    if minimo == maximo:
        lleva = f"{minimo} valor" + ("" if minimo == 1 else "es")
    elif maximo is None:
        lleva = (f"{minimo} valor{'' if minimo == 1 else 'es'} o más" if minimo
                 else "cualquier cantidad de valores")
    else:
        lleva = f"entre {minimo} y {maximo} valores"

    def llamada(args):
        if obligados:
            raise ErrorMate(
                f"{completo}() no se puede llamar desde Mate: en {archivo} pide '{obligados[0]}' "
                "por su nombre, y Mate pasa los valores en orden. En el .py, ponelo como un "
                "parámetro común", familia="python")
        if len(args) < minimo or (maximo is not None and len(args) > maximo):
            raise ErrorMate(f"{completo}() lleva {lleva} y recibió {len(args)} (así está "
                            f"escrita en {archivo})", familia="python")
        dados = [a_python(a, completo) for a in args]
        try:
            devuelto = f(*dados)
        except (ErrorMate, MemoryError):
            raise
        except (Exception, SystemExit) as e:
            raise ErrorMate(f"{completo}() falló adentro del Python"
                            + dicho_por_python(e, ruta), familia="python")
        try:
            return revisar_peso(de_python(devuelto, completo))
        except RecursionError:
            raise ErrorMate(f"{completo}() devolvió una lista o un diccionario que se tiene "
                            "a sí mismo adentro (o con demasiados niveles): Mate no lo "
                            "puede recibir", familia="python")
    return llamada


def cargar_python(nombre, ruta):
    """Abre el archivo de Python y devuelve su ModuloPython, con las funciones que se ven
    desde Mate: las escritas ahí con 'def' cuyo nombre no empieza con guion bajo. No deja
    ningún archivo al lado (ni la carpeta __pycache__ que arma Python cuando importa)."""
    archivo = os.path.basename(ruta)
    try:
        fuente = leer_fuente(ruta)
    except OSError:
        raise ErrorMate(f"no pude abrir {archivo}", familia="archivo")
    modulo = types.ModuleType(f"mate_python_{nombre}")
    modulo.__file__ = ruta
    try:
        exec(compile(fuente, ruta, "exec"), modulo.__dict__)
    except SyntaxError as e:
        donde = f" en su línea {e.lineno}" if e.lineno and e.filename == ruta else ""
        raise ErrorMate(f"{archivo} está mal escrito{donde} y Python no lo pudo leer. "
                        f"Python dice: {recortado(e.msg or 'SyntaxError', 300)}",
                        familia="python")
    except MemoryError:
        raise
    except (Exception, SystemExit) as e:
        raise ErrorMate(f"{archivo} falló apenas se lo abrió, antes de llamar a ninguna de "
                        "sus funciones" + dicho_por_python(e, ruta), familia="python")
    funciones = {
        n: DePython(f"{nombre}.{n}", funcion_de_python(f"{nombre}.{n}", f, ruta))
        for n, f in vars(modulo).items()
        if isinstance(f, types.FunctionType) and not n.startswith("_")
        and f.__module__ == modulo.__name__}
    return ModuloPython(nombre, ruta, funciones)


class Entorno:
    nacidos = 0  # cuántos entornos se crearon: sirve para saber cuál es anterior a cuál
    se_pisa = False  # solo en la consola: declarar de nuevo un nombre reemplaza al anterior

    def __init__(self, padre=None, frontera=False, borde=False):
        Entorno.nacidos = self.serie = Entorno.nacidos + 1
        self.vars = {}
        self.origen = {}  # de dónde salió cada nombre: sea, var, parametro, para, funcion...
        self.renglon = {}  # en qué renglón se declaró cada variable
        self.padre = padre
        self.raiz = self if padre is None else padre.raiz  # el de más afuera de todos
        self.frontera = frontera  # el estado de un agente: de acá para arriba no se escribe
        self.borde = borde  # donde empieza una función, un 'al recibir' o una prueba

    def definir(self, nombre, valor, mutable=False, origen=None, linea=None):
        # (el programa puede usar para lo suyo los nombres de SE_PUEDEN_TAPAR)
        if nombre in self.vars and not (
                nombre in SE_PUEDEN_TAPAR and self.origen.get(nombre) == "nativa") and not (
                self.se_pisa and self.origen.get(nombre) in ("sea", "var", "funcion", "agente")):
            previo = self.origen.get(nombre)
            if previo == "nativa":
                raise ErrorMate(INCLUIDA.format(n=nombre))
            de_otro = getattr(self.renglon.get(nombre), "archivo", None)
            if de_otro and de_otro != getattr(linea, "archivo", None):
                raise ErrorMate(f"'{nombre}' ya existe"
                                + de_donde_viene(self.renglon[nombre], linea))
            ayuda = ""
            if previo in ("sea", "var"):
                ayuda = (f"; para cambiarle el valor se escribe {nombre} = ... "
                         "(y tiene que ser 'var')")
            raise ErrorMate(f"'{nombre}' ya está definido en este bloque{ayuda}")
        raiz = self.raiz  # tampoco se tapa una función incluida desde adentro
        if raiz is not self and raiz.origen.get(nombre) == "nativa" \
                and nombre not in SE_PUEDEN_TAPAR:
            raise ErrorMate(INCLUIDA.format(n=nombre))
        self.vars[nombre] = [valor, mutable]
        self.origen[nombre] = origen or ("var" if mutable else "sea")
        if linea:
            self.renglon[nombre] = linea

    def no_tapar(self, nombre):
        """Un 'sea' o 'var' de un bloque de adentro (si, mientras, para, intentar) no
        puede repetir el nombre de una variable de más afuera: casi siempre se quiso
        cambiar esa variable, y con el 'sea' de más no cambia nada."""
        def ya_existe():
            return ErrorMate(
                f"'{nombre}' ya existe afuera de este bloque. Si querés cambiarle el "
                f"valor, sacá el 'sea' o el 'var': {nombre} = ... Si es otra cosa, "
                "ponele otro nombre")
        e = self
        while not e.borde and e.padre is not None:
            e = e.padre
            if nombre in e.vars and e.origen.get(nombre) in (
                    "sea", "var", "parametro", "para", "mensaje", "falla"):
                raise ya_existe()
        # Desde un bloque de adentro de una función, una prueba o un 'al recibir' tampoco
        # se tapa una variable 'var' del programa: ahí también se la quiso cambiar.
        afuera = e.padre if (e.borde and e is not self) else None
        while afuera is not None:
            if nombre in afuera.vars:
                if afuera.origen.get(nombre) == "var" and not afuera.frontera:
                    raise ya_existe()
                break
            afuera = afuera.padre
        if e.borde and e.padre is not None and e.padre.frontera and nombre in e.padre.vars \
                and e.padre.origen.get(nombre) == "var":
            raise ErrorMate(
                f"'{nombre}' es un estado de este agente. Si querés cambiarle el valor, "
                f"sacá el 'sea' o el 'var': {nombre} = ... Si es otra cosa, ponele otro nombre")

    def visibles(self):
        """Todos los nombres que se ven desde acá, de adentro hacia afuera."""
        nombres, e = [], self
        while e:
            nombres.extend(e.vars)
            e = e.padre
        return nombres

    def no_existe(self, nombre, al_asignar=False):
        return nombre_que_no_existe(nombre, self.visibles(), al_asignar)

    def buscar(self, nombre):
        e = self
        while e:
            if nombre in e.vars:
                return e.vars[nombre][0]
            e = e.padre
        raise self.no_existe(nombre)

    def asignar(self, nombre, valor):
        e, cruzo = self, False
        while e:
            if nombre in e.vars:
                if not e.vars[nombre][1]:
                    motivo = NO_SE_CAMBIA.get(e.origen.get(nombre), NO_SE_CAMBIA["sea"])
                    raise ErrorMate(motivo.format(n=nombre))
                if cruzo:
                    raise ErrorMate(
                        f"un agente no puede modificar '{nombre}': es de afuera. "
                        "Los agentes solo cambian su propio estado")
                e.vars[nombre][0] = valor
                return
            cruzo = cruzo or e.frontera
            e = e.padre
        raise self.no_existe(nombre, al_asignar=True)


# ───────────────────────────── Intérprete ─────────────────────────────


class ContratoConversacion:
    """Transiciones declaradas, con estado independiente para cada ID de charla."""

    @classmethod
    def del_programa(cls, programa, mensajes, agentes):
        contratos = [s for s in programa if s[0] == "contrato_conversacion"]
        if not contratos:
            return None
        if len(contratos) > 1:
            raise ErrorMate("solo se admite un contrato de conversación por programa", contratos[1][1],
                            familia="contrato")
        _, linea, expresion = contratos[0]

        def literal(nodo):
            tipo, renglon, *datos = nodo
            if tipo in ("str", "num", "bool"):
                return datos[0]
            if tipo == "nada":
                return None
            if tipo == "lista":
                return [literal(item) for item in datos[0]]
            if tipo == "mapa":
                mapa = {clave: literal(valor) for clave, valor in datos[0]}
                if len(mapa) == len(datos[0]):
                    return mapa
                raise ErrorMate("el contrato de conversación tiene un campo repetido", renglon,
                                familia="contrato")
            raise ErrorMate("el contrato de conversación lleva valores escritos a mano", renglon,
                            familia="contrato")

        return cls(literal(expresion), mensajes, agentes, linea)

    def __init__(self, datos, mensajes, agentes, linea):
        def invalido(motivo):
            raise ErrorMate(f"contrato de conversación: {motivo}", linea, familia="contrato")

        if not isinstance(datos, dict) or set(datos) != {"id", "inicio", "pasos"}:
            invalido("se espera un mapa con id, inicio y pasos")
        self.campo, self.inicio, pasos = datos["id"], datos["inicio"], datos["pasos"]
        if not all(isinstance(v, str) and v.strip() for v in (self.campo, self.inicio)):
            invalido("id e inicio tienen que ser textos no vacíos")
        if not isinstance(pasos, list) or not pasos:
            invalido("pasos tiene que ser una lista con transiciones")
        self.transiciones = {}
        self.preguntas = set()
        self.tipos = set()
        roles = set(agentes) | {"(programa)"}
        obligatorios = {"estado", "evento", "origen", "destino", "mensaje", "sigue"}
        for paso in pasos:
            if (not isinstance(paso, dict) or not obligatorios <= set(paso)
                    or set(paso) - obligatorios - {"campos"}
                    or not all(isinstance(paso[k], str) and paso[k] for k in obligatorios)):
                invalido("cada paso necesita estado, evento, origen, destino, mensaje y sigue")
            estado, evento, origen, destino, tipo, sigue = (
                paso[k] for k in ("estado", "evento", "origen", "destino", "mensaje", "sigue"))
            if evento not in ("pregunta", "respuesta", "sin_respuesta"):
                invalido(f"evento desconocido: '{evento}'")
            if origen not in roles or destino not in roles or tipo not in mensajes:
                invalido(f"rol o mensaje desconocido en '{estado}'")
            campos = paso.get("campos", {})
            declarado = {campo: (tipo_de_campo, opcional)
                         for campo, tipo_de_campo, opcional in mensajes[tipo]}
            if declarado.get(self.campo) != ("texto", False):
                invalido(f"'{tipo}' debe declarar '{self.campo}' como texto obligatorio")
            if not isinstance(campos, dict) or set(campos) - set(declarado):
                invalido(f"campos desconocidos en el paso de '{tipo}'")
            clave = (estado, evento, origen, destino, tipo)
            alternativas = self.transiciones.setdefault(clave, [])
            if any(all(igual(campos[k], otro[k]) for k in campos.keys() & otro.keys())
                   for otro, _ in alternativas):
                invalido(f"pasos ambiguos en '{estado}' para '{tipo}'")
            alternativas.append((campos, sigue))
            self.tipos.add(tipo)
            if evento == "pregunta":
                self.preguntas.add(tipo)
        if not any(clave[0] == self.inicio for clave in self.transiciones):
            invalido("el estado inicial no tiene pasos")

    def identificador(self, mensaje, linea):
        valor = mensaje.campos.get(self.campo) if isinstance(mensaje, Registro) else None
        if not isinstance(valor, str) or not valor.strip():
            raise ErrorMate(f"falta el ID '{self.campo}' de la conversación", linea, familia="contrato")
        return valor

    def mismo_id(self, charla, mensaje, linea):
        recibido = self.identificador(mensaje, linea)
        if recibido != charla:
            raise ErrorMate(f"ID de conversación incorrecto: se esperaba '{charla}' y llegó '{recibido}'",
                            linea, familia="contrato")

    def pasar(self, charlas, charla, evento, origen, destino, mensaje, linea):
        estado = charlas.get(charla, self.inicio)
        de = origen.nombre if origen else "(programa)"
        a = destino.nombre if destino else "(programa)"
        clave = (estado, evento, de, a, mensaje.tipo)
        for campos, siguiente in self.transiciones.get(clave, ()):
            if all(igual(mensaje.campos.get(campo), valor) for campo, valor in campos.items()):
                charlas[charla] = siguiente
                return
        raise ErrorMate(f"contrato de conversación: charla '{charla}' en '{estado}' "
                        f"no admite {evento} de {de} a {a} con '{mensaje.tipo}'",
                        linea, familia="contrato")


class Interprete:
    def __init__(self, salida=print, traza=False):
        self.salida = salida
        self.traza = traza
        self.anotar = None  # si la traza va a un archivo, quién recibe cada renglón
        self.cuenta = {"enviar": 0, "preguntar": 0, "fallaron": 0}  # para el resumen
        self.glob = Entorno()
        self.mensajes = {}
        self.responde = {}  # mensaje -> qué se le contesta, si el contrato lo dice
        self.reglas = {}  # mensaje -> {campo: lo que dice de sus valores: desde, hasta...}
        self.contrato_conversacion = None
        self.charlas = {}
        self.agentes = {}
        self.decl_agentes = []
        self.copias = {}
        self.cola = deque()
        self.contexto = None  # (agente, remitente, tipo de mensaje) mientras se atiende uno
        # La pregunta del contrato de conversación que inició la cadena de preguntas que se
        # está atendiendo (o None): su ID vale para toda la cadena, también a través de
        # un paso del medio que no está en el contrato.
        self.origen_de_charla = None
        self.entregados = 0
        # El "sobre" de cada entrega (mejora 99): su número, quién, a quién, en respuesta
        # a cuál y el número de conversación. Una conversación empieza cuando el programa
        # manda algo; lo que los agentes mandan mientras lo atienden sigue en la misma.
        self.conversaciones = 0  # cuántas conversaciones empezaron
        self.conversacion = None  # la del mensaje que se está atendiendo
        self.historial = []  # en una prueba: los sobres de lo que se mandó (mejora 98)
        self.desde = (0, 0)  # el número de mensaje y de conversación al empezar la prueba
        # Con 'ensayar': lo que viajó entre agentes (tipo, de, a, molde de, molde a), en
        # orden, respuestas incluidas. None en cualquier otra corrida.
        self.viajes = None
        self.vistos = {}  # (ensayo) número del mensaje -> el número con que se mostró
        self.pasos = 0
        self.max_pasos = MAX_PASOS  # None = sin tope
        self.linea_actual = None  # la última sentencia que se empezó a ejecutar
        self.errores_agentes = []  # textos: "línea 10: V al recibir Pedido: ..."
        self.errores_agentes_det = []  # lo mismo como (linea, texto), para decir el archivo
        self.errores_principal = []  # los del programa principal, antes de las pruebas
        self.vivos = []  # las copias nacidas con 'crear'
        self.en_prueba = False
        self.naciendo = 0  # agentes que están calculando su estado inicial
        self.tipos_estado = {}  # (agente, estado) -> tipo con el que arrancó
        self.archivo = None  # el archivo principal, para nombrar los otros en los errores
        self.detalle_pruebas = []  # por cada prueba, [(linea, texto)] de lo que falló
        self.separar_salida = False  # 'probar': lo que muestra cada prueba se guarda aparte
        self.mostrado_pruebas = []  # por cada prueba, los renglones que mostró
        self.llamadas = []  # nombres de las funciones que se están ejecutando
        self.abiertas = 0  # cuántas llamadas a funciones hay sin terminar
        self.ultima_funcion = None  # la última función que se llamó
        self.atendiendo = []  # (agente, renglón de la pregunta) de los que están atendiendo
        self.entrada = por_teclado  # de dónde saca leer() lo que contesta la persona
        self.sin_teclado = False  # en las pruebas leer() usa la respuesta preparada
        self.tecleado = None  # en una prueba: lo que dijo simular_teclado() (una lista)
        self.tecleados = 0  # cuántos de esa lista ya se dieron
        # Con 'probar', agregar_a_archivo() y escribir_archivo() no tocan el disco (0.5): lo
        # guardado queda acá (ruta -> texto entero) y leer_archivo() y leer_tabla() lo ven.
        # None = se escribe de verdad.
        self.archivos_de_prueba = None
        self.fecha_fija = False  # en las pruebas hoy() y ahora() dan siempre lo mismo
        # La IA (mejora 100). Simulada no sale a la red: en las pruebas siempre es así.
        self.ia_simulada = False
        self.ia_respuestas = []  # del archivo de --ia-simulada=archivo: (si trae, contesta)
        self.ia_fijada = None  # en una prueba: lo que dijo simular_ia() (una lista)
        self.ia_en_orden = False  # si simular_ia() recibió una lista: se dan una por vez
        self.ia_usadas = 0  # cuántas de esa lista ya se dieron
        self.ia_consultas = 0  # consultas de verdad en esta corrida
        self.ia_historial = []  # en una prueba: lo que se le consultó a la IA
        self.ensayando = False  # la orden 'ensayar': ia_historial se llena igual que ahí
        # Lo que aprenden los agentes (0.4). Solo 'correr' con un archivo lo llena: con
        # 'probar', en la consola y en las pruebas queda así, y nada toca el disco.
        self.recordando = False  # si los 'estado recordado' se recuperan de la memoria
        self.memoria = {}  # lo leído del archivo: agente -> {"estado": ..., "lecciones": ...}
        self.bitacora = None  # una lista, si las fallas de los agentes se anotan
        self.avisar = lambda texto: None  # por dónde salen los avisos de la memoria
        self.avisados = set()  # los avisos que se dan una sola vez por corrida
        self.guardar_cuenta = None  # 'correr': deja la cuenta de consultas en el disco
        self.calculando_frenos = False  # mientras se calculan los valores de unos 'frenos'
        # El buzón entre programas (0.7). Solo 'correr' arma uno: con None, lo que se le
        # envía a un agente de otro programa queda anotado (traza, mensajes_enviados) y
        # nada más: 'probar', 'ensayar' y la consola no escriben ni leen ningún buzón.
        self.buzon = None
        self.probando = False  # la orden 'probar' (para decirlo en la traza)
        self.en_consola = False  # la orden 'consola': ahí no hay buzón, y se avisa
        self.ajenos = {}  # los agentes de otro programa que trajo 'usar buzon'
        self.remitentes = {}  # los que llegaron como remitente: (programa, agente) -> agente
        self.charla_de_buzon = {}  # número de conversación de acá -> su id entre programas
        self.id_de_buzon = {}  # número del mensaje que llegó del buzón -> el id de su sobre
        self.charla_de_socio = {}  # número de conversación de acá -> el socio con quien es
        self.sin_dueno = False  # ya no hay quién conteste el "¿Lo entrego?" (0.8)
        self._armados = {}  # lo que ya está armado para correr (ver 'armar_bloque')
        self._nativas()

    # ── funciones incorporadas ──
    def _nativas(self):
        def nativa(nombre):
            def deco(fn):
                minimo, maximo = FUNCIONES[nombre][:2]

                def envuelta(args):
                    """Ninguna función incluida falla con un error de Python."""
                    cuantos = len(args)
                    if cuantos < minimo or (maximo is not None and cuantos > maximo):
                        raise ErrorMate(cantidad_equivocada(nombre, cuantos))
                    try:
                        r = fn(*args)
                    except ErrorMate:
                        raise
                    except MemoryError:
                        raise ErrorMate(f"{nombre}(): {SIN_MEMORIA}", clase="limite")
                    except (TypeError, ValueError, ArithmeticError, KeyError, IndexError,
                            AttributeError):
                        raise ErrorMate(f"{nombre}(): no pude hacer eso con esos valores")
                    if type(r) is float and not math.isfinite(r):
                        raise ErrorMate(f"{nombre}(): {DEMASIADO_GRANDE}")
                    return r
                self.glob.definir(nombre, Nativa(nombre, envuelta), origen="nativa")
                return fn
            return deco

        def pedir(v, tipo, donde):
            if nombre_tipo(v) != tipo:
                raise ErrorMate(f"{donde} espera {tipo} y recibió {tipo_claro(v)}")
            return v

        def no_vacia(l, donde):
            if not l:
                raise ErrorMate(f"{donde} no puede con una lista vacía: no hay de dónde "
                                "elegir. Preguntá antes con largo(lista) > 0")
            return l

        def numeros(l, donde):
            if not all(es_num(x) for x in pedir(l, "lista", donde)):
                raise ErrorMate(f"{donde} espera una lista de números")
            return l

        def posicion_de(n, donde):
            if type(n) is not int or n < 0:
                raise ErrorMate(f"{donde} espera posiciones enteras, de 0 en adelante")
            return n

        nativa("mostrar")(lambda *xs: self.salida(" ".join(
            formato(revisar_peso(a)) for a in xs)))

        @nativa("largo")
        def _(x):
            if isinstance(x, (str, list, dict)):
                return len(x)
            raise ErrorMate(f"largo() no aplica a{'l valor nada' if x is None else ' ' + nombre_tipo(x)}")

        nativa("texto")(a_texto)
        nativa("tipo")(nombre_tipo)

        @nativa("numero")
        def _(x):
            return x if es_num(x) else numero_de_texto(pedir(x, "texto", "numero()"))

        @nativa("tiene")
        def _(col, x):
            if isinstance(col, dict):  # las claves son textos: otra cosa no puede estar
                return isinstance(x, str) and x in col
            if isinstance(col, list):
                return any(igual(x, y) for y in col)
            if isinstance(col, str) and isinstance(x, str):
                return x in col
            if isinstance(col, str):
                raise ErrorMate(
                    f"tiene(): dentro de un texto se busca otro texto, y recibió {un(x)}"
                    + (f". Pasalo a texto: tiene(t, texto({formato(x)}))" if es_num(x) else ""))
            raise ErrorMate("tiene() busca en una lista, un mapa o un texto, y recibió "
                            + un(col))

        nativa("claves")(lambda m: list(pedir(m, "mapa", "claves()")))
        nativa("valores")(lambda m: list(pedir(m, "mapa", "valores()").values()))
        @nativa("agregar")
        def _(l, x):
            if len(pedir(l, "lista", "agregar()")) >= MAX_LARGO:
                raise muy_largo("la lista")
            return l + [x]

        @nativa("quitar")
        def _(col, x):
            if isinstance(col, dict):
                self.clave_de_mapa(x)
                return {k: v for k, v in col.items() if k != x}
            if isinstance(col, list):
                return [y for y in col if not igual(x, y)]
            raise ErrorMate(
                f"quitar() saca de una lista los que valen eso (o de un mapa, esa clave), "
                f"y recibió {un(col)}"
                + (". Para sacar una parte de un texto usá reemplazar(t, parte, \"\")"
                   if isinstance(col, str) else ""))

        @nativa("rango")
        def _(a, b=None, salto=1):
            ini, fin = (0, a) if b is None else (a, b)
            if type(ini) is not int or type(fin) is not int or type(salto) is not int:
                raise ErrorMate("rango() espera números enteros")
            if salto == 0:
                raise ErrorMate("rango(): el salto (el tercer valor) no puede ser 0: "
                                "nunca llegaría")
            numeros_del_rango = range(ini, fin, salto)
            if len(numeros_del_rango) > MAX_LARGO:
                raise ErrorMate("rango(): son demasiados números (el tope es "
                                + f"{MAX_LARGO:,})".replace(",", "."))
            return list(numeros_del_rango)

        nativa("sumar")(lambda l: sum(numeros(l, "sumar()")))

        @nativa("promedio")
        def _(l):
            total, cuantos = sum(no_vacia(numeros(l, "promedio()"), "promedio()")), len(l)
            if type(total) is int and total % cuantos == 0:
                return total // cuantos
            return total / cuantos

        def extremo(nombre, elegir):
            @nativa(nombre)
            def _(l):
                claves = claves_de_orden(no_vacia(pedir(l, "lista", f"{nombre}()"),
                                                  f"{nombre}()"))
                if claves is None:
                    raise ErrorMate(f"{nombre}() espera una lista de números (o toda de "
                                    "textos), sin mezclar")
                return l[elegir(range(len(l)), key=claves.__getitem__)]

        extremo("minimo", min)
        extremo("maximo", max)
        nativa("absoluto")(lambda n: abs(pedir(n, "numero", "absoluto()")))

        @nativa("ultimo")
        def _(col):
            if not isinstance(col, (list, str)):
                raise ErrorMate(f"ultimo() espera una lista o un texto y recibió "
                                f"{tipo_claro(col)}")
            if not col:
                raise ErrorMate("ultimo() no puede con "
                                + ("un texto vacío" if isinstance(col, str) else
                                   "una lista vacía") + ": no tiene ningún elemento")
            return col[-1]

        @nativa("porcion")
        def _(col, desde, hasta=None):
            if not isinstance(col, (list, str)):
                raise ErrorMate(f"porcion() espera una lista o un texto y recibió "
                                f"{tipo_claro(col)}")
            posicion_de(desde, "porcion()")
            hasta = len(col) if hasta is None else posicion_de(hasta, "porcion()")
            if desde > hasta:
                raise ErrorMate(f"porcion(): la posición donde empieza ({desde}) no puede "
                                f"ser mayor que la posición donde termina ({hasta})")
            return col[desde:hasta]  # si 'hasta' se pasa del final, llega hasta el final

        @nativa("obtener")
        def _(m, clave, por_defecto):
            pedir(m, "mapa", "obtener()")
            self.clave_de_mapa(clave)
            return m.get(clave, por_defecto)

        @nativa("ordenar")
        def _(l, campo=None):
            por = pedir(l, "lista", "ordenar()")
            if campo is not None:
                pedir(campo, "texto", "ordenar()")
                por = []
                for x in l:
                    campos = x.campos if isinstance(x, Registro) else x
                    if not isinstance(campos, dict):
                        raise ErrorMate(
                            f'ordenar(lista, "{campo}") espera una lista de mapas o de '
                            f"mensajes, y adentro hay {un(x)}")
                    if campo not in campos:
                        raise ErrorMate(no_esta(
                            f"ordenar(): un elemento de la lista no tiene '{campo}'",
                            campo, campos))
                    por.append(campos[campo])
            claves = claves_de_orden(por)
            if claves is None and campo is not None:
                raise ErrorMate(f"ordenar(): los '{campo}' tienen que ser todos números o "
                                "todos textos, sin mezclar")
            if claves is None:
                try:
                    return sorted(l)
                except TypeError:
                    raise ErrorMate("ordenar() espera elementos comparables entre sí: todos "
                                    "números o todos textos")
            return [l[i] for i in sorted(range(len(l)), key=claves.__getitem__)]

        @nativa("redondear")
        def _(x, n=0):
            pedir(x, "numero", "redondear()")
            if type(n) is not int or n < 0:
                raise ErrorMate("redondear() espera una cantidad entera de decimales, de 0 "
                                "en adelante (no puede ser negativa ni tener coma), "
                                "por ejemplo redondear(3.14159, 2)")
            if not math.isfinite(x):
                raise ErrorMate("redondear() no puede con un número infinito")
            if type(x) is int:
                return x
            r = redondeo(x, n)  # el medio va hacia arriba: redondear(2.5) da 3
            return int(r) if r == r.to_integral_value() else float(r)

        @nativa("pesos")
        def _(n, decimales=2):
            if isinstance(n, str):
                raise ErrorMate(
                    f"pesos() espera numero y recibió texto ({recortado(n, 30)}). Si viene "
                    "de una planilla, esa celda no tiene un número (está vacía o dice otra "
                    "cosa): corregila en la planilla, o preguntá antes:  "
                    'si tipo(dato) == "numero" { ... }')
            pedir(n, "numero", "pesos()")
            if type(decimales) is not int or not 0 <= decimales <= 6:
                raise ErrorMate("pesos() espera una cantidad de decimales entre 0 y 6, "
                                "por ejemplo pesos(1234.5, 2)")
            if not math.isfinite(n):
                raise ErrorMate("pesos() no puede con un número infinito")
            r = redondeo(n, decimales)
            entero, _, fraccion = format(r.copy_abs(), "f").partition(".")
            texto = "$ " + format(int(entero), ",").replace(",", ".")
            if decimales:
                texto += "," + fraccion.ljust(decimales, "0")
            return ("-" if r < 0 else "") + texto

        @nativa("unir")
        def _(l, sep):
            revisar_peso(pedir(l, "lista", "unir()"))
            minimo = sum(len(x) if isinstance(x, str) else 1 for x in l)
            if minimo + len(l) * len(pedir(sep, "texto", "unir()")) > MAX_LARGO:
                raise muy_largo()
            t = sep.join(formato(x) for x in l)
            if len(t) > MAX_LARGO:
                raise muy_largo()
            return t

        @nativa("partir")
        def _(t, sep):
            pedir(t, "texto", "partir()")
            if pedir(sep, "texto", "partir()") == "":
                return list(t)  # sin separador: letra por letra
            return t.split(sep)

        @nativa("leer")
        def _(pregunta, preparada=None):
            pedir(pregunta, "texto", "leer()")
            if preparada is not None:
                pedir(preparada, "texto", "leer()")
            if self.contexto is not None or self.naciendo:
                raise ErrorMate(
                    "leer() solo se usa desde el programa principal: un agente no puede "
                    "frenar todo esperando el teclado. Leé el dato afuera y mandáselo en "
                    "un mensaje")
            if self.sin_teclado:
                if self.tecleado is not None and self.tecleados < len(self.tecleado):
                    self.tecleados += 1  # lo que fijó simular_teclado(), de a uno
                    return self.tecleado[self.tecleados - 1].strip()
                if preparada is None and self.tecleado is not None:
                    raise ErrorMate(
                        f"la prueba llegó a {self.tecleados + 1} leer() y simular_teclado() "
                        f"tenía {len(self.tecleado)} texto(s): agregá los que faltan a la "
                        "lista, o dale a ese leer() una respuesta preparada como segundo "
                        'valor, por ejemplo leer("Cliente:", "chau")')
                if preparada is None:
                    raise ErrorMate(
                        "en las pruebas leer() no espera el teclado: dale una respuesta "
                        'preparada como segundo valor, por ejemplo leer("¿Cuántos?", "3"), '
                        'o fijá antes lo que se teclea: simular_teclado(["3"])')
                return preparada
            try:
                # (si lo tecleado llega de un archivo con marca al principio, se le saca)
                return self.entrada(pregunta).replace("\ufeff", "").strip()
            except KeyboardInterrupt:
                raise CorteEnElTeclado()
            except (EOFError, OSError):
                if preparada is not None:
                    return preparada
                raise ErrorMate("leer(): no hay nadie para contestar (el programa no "
                                "está corriendo en una consola con teclado)")
            except UnicodeError:
                raise ErrorMate("leer(): lo que llegó trae una letra que no pude entender "
                                "(una tilde o una ñ en otra codificación). Si viene de un "
                                "archivo, guardalo como UTF-8")

        def momento():
            return FECHA_DE_PRUEBA if self.fecha_fija else datetime.datetime.now()

        nativa("hoy")(lambda: momento().strftime("%d/%m/%Y"))
        nativa("ahora")(lambda: momento().strftime("%d/%m/%Y %H:%M"))

        def archivo_de_datos(nombre, donde):
            """La ruta completa de un archivo de la carpeta del programa (y solo de ahí)."""
            pedir(nombre, "texto", donde)
            if self.contexto is not None or self.naciendo:
                raise ErrorMate(
                    f"{donde} solo se usa desde el programa principal: un agente no toca "
                    "archivos. Leé o guardá el archivo afuera y pasale los datos en un "
                    "mensaje", familia="archivo")
            carpeta = os.path.realpath(
                os.path.dirname(os.path.abspath(self.archivo)) if self.archivo else os.getcwd())
            ruta = os.path.realpath(os.path.join(carpeta, nombre)) if nombre.strip() else carpeta
            try:
                adentro = os.path.normcase(os.path.commonpath([carpeta, ruta])) \
                    == os.path.normcase(carpeta)
            except ValueError:  # en Windows, si está en otro disco
                adentro = False
            if not nombre.strip():
                raise ErrorMate(f'{donde}: falta el nombre del archivo, por ejemplo "notas.txt"',
                                familia="archivo")
            if es_archivo_de_clave(os.path.join(carpeta, nombre)) or es_archivo_de_clave(ruta):
                raise ErrorMate(f"{donde}: " + NO_SE_LEE_LA_CLAVE.format(
                    n=os.path.basename(nombre.replace("\\", "/"))), familia="archivo")
            if not adentro:
                suelto = os.path.basename(nombre.replace("\\", "/").rstrip("/")) or "notas.txt"
                raise ErrorMate(
                    f"{donde} solo trabaja con archivos de la carpeta del programa "
                    f"({carpeta}), y '{nombre}' queda afuera. Copiá el archivo a esa carpeta "
                    f'y nombralo sin la ruta: "{suelto}"', familia="archivo")
            return carpeta, ruta

        def texto_del_archivo(nombre, donde, si_no_esta=None):
            """El texto de un archivo de la carpeta del programa, para leer_archivo() y
            leer_tabla(). Si no está, el error dice en qué carpeta se lo buscó."""
            carpeta, ruta = archivo_de_datos(nombre, donde)
            if os.path.isdir(ruta):
                raise ErrorMate(f"{donde}: '{nombre}' es una carpeta, no un archivo",
                                familia="archivo")
            if self.archivos_de_prueba is not None and ruta in self.archivos_de_prueba:
                return self.archivos_de_prueba[ruta]  # lo que 'agregó' la prueba
            try:
                if donde == "leer_tabla()" and es_de_excel(ruta):
                    raise ErrorMate("es una planilla de Excel sin convertir")
                contenido = leer_fuente(ruta)
            except FileNotFoundError:
                try:
                    otros = sorted(a for a in os.listdir(os.path.dirname(ruta))
                                   if os.path.isfile(os.path.join(os.path.dirname(ruta), a)))
                except OSError:
                    otros = []
                suelto = os.path.basename(ruta)
                if suelto + ".txt" in otros:  # el Bloc de notas le agregó .txt
                    pista = f" ¿Quisiste decir '{suelto}.txt'?"
                else:
                    pista = sugerir(suelto, otros)
                if si_no_esta is not None:
                    return si_no_esta
                raise ErrorMate(f"{donde}: no encuentro el archivo '{nombre}' en "
                                f"{os.path.dirname(ruta)}.{pista}".rstrip("."), familia="archivo")
            except OSError:
                raise ErrorMate(f"{donde}: no pude abrir '{nombre}'", familia="archivo")
            except ErrorMate:
                if es_de_excel(ruta):
                    raise ErrorMate(f"{donde}: '{nombre}' es una planilla de Excel, y Mate "
                                    f"lee texto. {COMO_GUARDAR_CSV}", familia="archivo")
                raise ErrorMate(f"{donde}: no pude leer las letras de '{nombre}': "
                                "¿seguro que es un archivo de texto?", familia="archivo")
            if len(contenido) > MAX_LARGO:
                raise ErrorMate(f"{donde}: '{nombre}' es demasiado grande para leerlo "
                                "entero", familia="archivo")
            return contenido

        nativa("leer_archivo")(lambda nombre: texto_del_archivo(nombre, "leer_archivo()"))

        @nativa("leer_tabla")
        def _(nombre):
            pedir(nombre, "texto", "leer_tabla()")
            if nombre.strip().lower().endswith((".xlsx", ".xls", ".xlsm", ".ods")):
                raise ErrorMate(
                    f"leer_tabla(): '{nombre}' es una planilla de Excel, y Mate lee la "
                    f"planilla guardada como CSV. {COMO_GUARDAR_CSV}; después nombrala con "
                    f'.csv: leer_tabla("{os.path.splitext(nombre.strip())[0]}.csv")',
                    familia="archivo")
            return tabla_de_texto(texto_del_archivo(nombre, "leer_tabla()"), nombre)

        def donde_guardar(nombre, contenido, donde):
            """Los controles antes de guardar algo: devuelve la ruta completa."""
            carpeta, ruta = archivo_de_datos(nombre, donde)
            if nombre_tipo(contenido) != "texto":
                raise ErrorMate(
                    f"{donde} guarda un texto y recibió {tipo_claro(contenido)}. "
                    'Pasalo a texto antes: texto(valor), unir(lista, "\\n") o a_json(valor)')
            # (Windows ignora los puntos y espacios del final, y lo que sigue a un ':')
            limpio = os.path.basename(ruta).split(":")[0].rstrip(". ").lower()
            if limpio.endswith(NO_SE_PISAN):
                raise ErrorMate(
                    f"{donde} no escribe en '{nombre}' para no pisar un programa: "
                    'elegí otro nombre, por ejemplo "notas.txt"', familia="archivo")
            # Tampoco en los archivos que Mate lleva de este programa: ahí están las
            # lecciones de los agentes y la cuenta de consultas (el tope de gasto).
            if self.archivo and os.path.dirname(ruta) == carpeta and limpio in {
                    os.path.basename(archivo_de(self.archivo, que)).lower()
                    for que in ("memoria.json", "bitacora.txt", "memoria.json.tmp",
                                "bitacora.txt.tmp", "memoria.rota.json")}:
                raise ErrorMate(
                    f"{donde} no escribe en '{nombre}': ese archivo lo lleva Mate (ahí "
                    "guarda lo que recuerdan los agentes, sus lecciones y la cuenta de "
                    'consultas). Elegí otro nombre, por ejemplo "notas.txt"',
                    familia="archivo")
            # Ni en la memoria de un programa nombrado con 'usar buzon': ahí ese otro
            # anota también qué mensajes ya atendió y cuáles tiene por salir.
            for ajeno in self.ajenos.values():
                if os.path.dirname(ruta) == carpeta and limpio in {
                        os.path.basename(archivo_de(ajeno.ajeno, que)).lower()
                        for que in ("memoria.json", "memoria.json.tmp")}:
                    raise ErrorMate(
                        f"{donde} no escribe en '{nombre}': es la memoria de "
                        f"{os.path.basename(ajeno.ajeno)} y la lleva Mate (ahí están lo que "
                        "recuerdan sus agentes y los mensajes del buzón que ya atendió). "
                        'Elegí otro nombre, por ejemplo "notas.txt"', familia="archivo")
            try:
                adentro = os.path.relpath(ruta, carpeta).replace("\\", "/").split("/")
            except ValueError:
                adentro = []
            if any(parte.rstrip(". ").lower().endswith(".buzon") for parte in adentro[:-1]):
                raise ErrorMate(
                    f"{donde} no escribe en '{nombre}': esa carpeta es un buzón entre "
                    "programas y la lleva Mate. Para mandarle un mensaje a otro programa "
                    "se usa 'enviar' (ver: ayuda buzon)", familia="archivo")
            if os.path.isdir(ruta):
                raise ErrorMate(f"{donde}: '{nombre}' es una carpeta, no un archivo",
                                familia="archivo")
            try:
                contenido.encode("utf-8")  # antes de tocar el archivo: si falla, queda como estaba
            except UnicodeError:
                raise ErrorMate(
                    f"{donde}: el texto trae una letra que no se puede guardar "
                    f"(un símbolo roto, que suele venir de un JSON). '{nombre}' quedó como "
                    "estaba", familia="archivo")
            return ruta

        def guardar_en(ruta, nombre, donde, escribir):
            try:
                escribir()
            except FileNotFoundError:
                raise ErrorMate(f"{donde}: no existe la carpeta donde iría "
                                f"'{nombre}'. Creala antes, o guardá el archivo al lado del "
                                "programa", familia="archivo")
            except (OSError, UnicodeError):
                raise ErrorMate(f"{donde}: no pude guardar '{nombre}' (¿está "
                                "abierto en otro programa, o no hay permiso?)",
                                familia="archivo")

        @nativa("escribir_archivo")
        def _(nombre, contenido):
            ruta = donde_guardar(nombre, contenido, "escribir_archivo()")
            if self.archivos_de_prueba is not None:
                # 'probar' no toca el disco (como agregar_a_archivo): lo escrito queda acá,
                # y leer_archivo() y leer_tabla() lo ven. Así una prueba nunca pisa un
                # archivo de datos de verdad (los pedidos de ayer).
                if len(contenido) > MAX_LARGO:
                    raise ErrorMate(f"escribir_archivo(): el texto es demasiado grande para "
                                    f"guardarlo en '{nombre}'", familia="archivo")
                if not os.path.isdir(os.path.dirname(ruta)):
                    raise ErrorMate(f"escribir_archivo(): no existe la carpeta donde iría "
                                    f"'{nombre}'. Creala antes, o guardá el archivo al lado del "
                                    "programa", familia="archivo")
                self.archivos_de_prueba[ruta] = contenido
                return

            def escribir():
                # con la marca del principio, para que el Bloc de notas muestre bien las tildes
                with open(ruta, "w", encoding="utf-8-sig") as f:
                    f.write(contenido)
            guardar_en(ruta, nombre, "escribir_archivo()", escribir)

        @nativa("agregar_a_archivo")
        def _(nombre, renglon):
            ruta = donde_guardar(nombre, renglon, "agregar_a_archivo()")
            if not renglon.endswith("\n"):
                renglon += "\n"  # cada agregado es un renglón
            # Lo que el archivo ya tenía, y si se le puede sumar al final tal como está
            # (UTF-8) o hay que guardarlo entero de nuevo (lo dejó el Bloc de notas en ANSI
            # o en "Unicode": mezclar codificaciones rompería las tildes).
            antes = texto_del_archivo(nombre, "agregar_a_archivo()", si_no_esta="")
            if antes and not antes.endswith("\n"):
                antes += "\n"
            if len(antes) + len(renglon) > MAX_LARGO:
                raise ErrorMate(f"agregar_a_archivo(): '{nombre}' ya es demasiado grande: "
                                "empezá un archivo nuevo, con otro nombre", familia="archivo")
            if self.archivos_de_prueba is not None:
                self.archivos_de_prueba[ruta] = antes + renglon  # 'probar' no toca el disco
                return

            def escribir():
                try:
                    with open(ruta, "rb") as f:
                        crudo = f.read()
                except FileNotFoundError:
                    crudo = None
                if crudo is None or not crudo:
                    with open(ruta, "w", encoding="utf-8-sig") as f:
                        f.write(renglon)
                    return
                try:
                    crudo.decode("utf-8")
                except UnicodeError:
                    escribir_entero(ruta, antes + renglon)
                    return
                with open(ruta, "a", encoding="utf-8") as f:
                    f.write(renglon if crudo.endswith(b"\n") else "\n" + renglon)
            guardar_en(ruta, nombre, "agregar_a_archivo()", escribir)

        @nativa("recortar")
        def _(t):
            return pedir(t, "texto", "recortar()").strip()

        @nativa("reemplazar")
        def _(t, viejo, nuevo):
            for x in (t, viejo, nuevo):
                pedir(x, "texto", "reemplazar()")
            if viejo == "":
                raise ErrorMate("reemplazar(): el texto a buscar (el segundo valor) no "
                                "puede estar vacío")
            if len(t) + t.count(viejo) * (len(nuevo) - len(viejo)) > MAX_LARGO:
                raise ErrorMate("reemplazar(): el texto quedaría demasiado largo")
            return t.replace(viejo, nuevo)

        nativa("empieza_con")(lambda t, p: pedir(t, "texto", "empieza_con()").startswith(
            pedir(p, "texto", "empieza_con()")))
        nativa("termina_con")(lambda t, p: pedir(t, "texto", "termina_con()").endswith(
            pedir(p, "texto", "termina_con()")))

        nativa("mayusculas")(lambda t: pedir(t, "texto", "mayusculas()").upper())
        nativa("minusculas")(lambda t: pedir(t, "texto", "minusculas()").lower())

        @nativa("a_json")
        def _(v):
            try:
                t = json.dumps(self._a_json(revisar_peso(v, 3)), ensure_ascii=False,
                               allow_nan=False)
            except ValueError:  # inf, nan o un entero de miles de cifras
                raise ErrorMate("ese número no se puede pasar a JSON")
            if len(t) > MAX_LARGO:
                raise muy_largo()
            return t

        def numero_invalido(_):
            raise ErrorMate("el JSON trae un número que no es válido")

        def decimal_de_json(t):
            f = float(t)
            return f if math.isfinite(f) else numero_invalido(t)

        @nativa("de_json")
        def _(t, tipo=None):
            try:
                valor = self._de_json(json.loads(
                    pedir(t, "texto", "de_json()"),
                    parse_constant=numero_invalido, parse_float=decimal_de_json))
            except json.JSONDecodeError as e:
                raise ErrorMate(json_invalido(t, e), familia="json")
            except ValueError:  # un entero de miles de cifras
                numero_invalido(t)
            if tipo is None:
                return valor
            # de_json(texto, "Pedido"): lo que viene de afuera tiene que ser de ese tipo.
            base = pedir(tipo, "texto", "de_json()").rsplit(" de ", 1)[-1]
            if base not in TIPOS_BASE and base not in self.mensajes:
                raise ErrorMate(con_sugerencia(
                    f"de_json(): no existe el tipo '{tipo}'", base,
                    sorted(TIPOS_BASE) + list(self.mensajes)))
            valor = self.amoldar(valor, tipo)  # un mapa suelto con esos campos sirve
            if not self.cumple(valor, tipo):
                raise ErrorMate(f"de_json(): se esperaba {tipo} y el texto trae "
                                f"{self.no_cumple(valor, tipo)}", familia="contrato")
            return valor

        @nativa("a_mapa")
        def _(m):
            if isinstance(m, dict):
                return m  # ya es un mapa
            if not isinstance(m, Registro):
                raise ErrorMate(f"a_mapa() espera un mensaje y recibió {un(m)}")
            return dict(m.campos)

        @nativa("detalle_de")
        def _(e):
            if not isinstance(e, ErrorAtajado):
                raise ErrorMate(
                    "detalle_de() espera el error que ataja 'si falla e', tal cual llegó "
                    f"(sin cambiarle nada), y recibió {un(e)}")
            return dict(e.detalle)

        @nativa("consultar_ia")
        def _(instrucciones, pregunta, preparada=None):
            pedir(instrucciones, "texto", "consultar_ia()")
            pedir(pregunta, "texto", "consultar_ia()")
            if preparada is not None:
                pedir(preparada, "texto", "el tercer valor de consultar_ia()")
            if not pregunta.strip():
                raise error_de_ia("la pregunta está vacía: no hay nada para consultarle")
            quien = self.contexto[0].nombre if self.contexto else "(programa)"
            hondo = len(self.atendiendo)
            # Los frenos del agente (0.5). Sin frenos, todo sigue como siempre.
            agente = self.contexto[0] if self.contexto else None
            try:
                frenos = self.frenos_de(agente) if agente is not None and agente.decl[6] \
                    else None
            except ErrorMate as error:
                # Unos frenos mal escritos no son "la IA no contestó": no se atajan con
                # 'intentar' (si no, el programa seguiría atendiendo sin frenos ni aviso).
                # El programa corta ahí, con el archivo y el renglón de la regla.
                if error.clase == "falla":
                    error.clase = "escritura"
                    if "los frenos de" not in error.mensaje:
                        error.mensaje = (f"los frenos de {agente.decl[2]} están mal escritos: "
                                         f"{error.mensaje}")
                    error.mensaje += (". (Hasta que se arregle, el programa no sigue: unos "
                                      "frenos que fallan no frenan nada)")
                raise
            if frenos is None:
                return una_consulta(instrucciones, pregunta, preparada, quien, hondo)[0]
            return self.con_frenos(
                agente, frenos, instrucciones, pregunta, momento(),
                lambda de_nuevo=None: una_consulta(
                    instrucciones, de_nuevo or pregunta, preparada, quien, hondo,
                    simulada_con=pregunta))

        def una_consulta(instrucciones, pregunta, preparada, quien, hondo, simulada_con=None):
            """Una consulta a la IA (de verdad o simulada). Devuelve (lo que contestó, la
            anotación que queda para consultas_ia()). simulada_con: en el segundo intento
            de un freno, la respuesta simulada se busca por la pregunta original."""
            # Las lecciones del agente van solas al final de las instrucciones (0.4).
            aprendidas = self.lecciones_de(self.contexto[0]) if self.contexto else []
            if aprendidas:
                instrucciones = con_lecciones(instrucciones, aprendidas)
            if self.traza:
                self.trazar(f"{quien} consulta a la IA"
                            f"{' (simulada)' if self.ia_simulada else ''}: "
                            f"{recortado(pregunta)}", None, hondo)
                for i, leccion in enumerate(aprendidas, 1):
                    self.trazar(f"   con la lección {i}: {recortado(leccion)}", None, hondo)
            consulta = {"agente": quien, "instrucciones": instrucciones,
                        "pregunta": pregunta, "respuesta": None}
            if self.en_prueba or self.ensayando:
                self.ia_historial.append(consulta)
            try:
                if self.ia_simulada:
                    respuesta = self.respuesta_simulada(simulada_con or pregunta, preparada)
                else:
                    if self.max_pasos is not None and self.ia_consultas >= MAX_CONSULTAS_IA:
                        raise ErrorMate(
                            f"el programa ya le hizo {MAX_CONSULTAS_IA} consultas a la IA y "
                            "cada una se paga: lo freno por si los agentes entraron en "
                            "bucle. Si de verdad hacen falta más, corré con --sin-limite",
                            clase="limite")
                    self.ia_consultas += 1
                    _USO_DE_LA_IA.clear()
                    try:
                        respuesta = pedir_a_la_ia(instrucciones, pregunta)
                    except (ErrorMate, KeyboardInterrupt, MemoryError):
                        raise
                    except Exception as e:  # nunca un error de Python (ni la clave) a la vista
                        raise error_de_ia("algo salió mal al hablar con la IA y no sé "
                                          f"explicarlo mejor ({type(e).__name__})")
            except ErrorMate as e:
                if self.traza:
                    self.trazar("la IA no contestó: " + e.mensaje.split("\n")[0], None, hondo)
                if self.ensayando:  # el informe de 'ensayar' dice por qué no contestó
                    consulta["motivo"] = e.mensaje
                raise
            if len(respuesta) > MAX_LARGO:
                raise error_de_ia("la respuesta es demasiado larga para guardarla")
            if self.traza:
                self.trazar(f"la IA contesta: {recortado(respuesta)}", None, hondo)
            consulta["respuesta"] = respuesta
            return respuesta, consulta

        @nativa("consultas_ia")
        def _():
            if not self.en_prueba:
                raise ErrorMate(CONSULTAS_IA_SUELTO)
            if self.contexto is None:
                self.vaciar_cola()  # lo enviado en la prueba llega antes de mirar
            return [dict(consulta) for consulta in self.ia_historial]

        @nativa("aprender")
        def _(leccion, agente=None):
            quien = self.el_que_aprende("aprender", agente)
            try:
                texto = leccion_limpia(pedir(leccion, "texto", "aprender()"))
            except ErrorMate as e:
                e.mensaje = e.mensaje if e.mensaje.startswith("aprender()") \
                    else "aprender(): " + e.mensaje
                raise
            nuevas, olvidadas = sumar_leccion(
                quien.lecciones, texto, momento().strftime("%d/%m/%Y %H:%M"))
            if nuevas is quien.lecciones:
                return  # ya la sabía: no se anota dos veces
            quien.lecciones = nuevas
            if self.traza:
                self.trazar(f"{quien.nombre} aprende: {recortado(texto)}", None,
                            len(self.atendiendo))
            if olvidadas:
                self.avisar_una_vez(("tope", quien.nombre), (
                    f"{quien.nombre} ya tenía {MAX_LECCIONES} lecciones, que es el tope: "
                    "para anotar la nueva se olvidó de la más vieja"))

        @nativa("lecciones")
        def _(agente=None):
            return self.lecciones_de(self.el_que_aprende("lecciones", agente))

        @nativa("simular_ia")
        def _(respuesta):
            if not self.en_prueba:
                raise ErrorMate(SIMULAR_IA_SUELTO)
            en_orden = isinstance(respuesta, list)
            lista = respuesta if en_orden else [respuesta]
            if not lista or not all(isinstance(r, str) and r.strip() for r in lista):
                raise ErrorMate(
                    "simular_ia() espera el texto que va a contestar la IA, o una lista de "
                    f"textos para que los dé en orden, y recibió {tipo_claro(respuesta)}"
                    + (" (vacía, o con algo que no es un texto con letras)" if en_orden
                       else " (vacío)" if isinstance(respuesta, str) else ""))
            self.ia_fijada, self.ia_en_orden, self.ia_usadas = list(lista), en_orden, 0

        @nativa("simular_teclado")
        def _(tecleado):
            if not self.en_prueba:
                raise ErrorMate(SIMULAR_TECLADO_SUELTO)
            lista = tecleado if isinstance(tecleado, list) else [tecleado]
            if not lista or not all(isinstance(t, str) for t in lista):
                raise ErrorMate(
                    "simular_teclado() espera lo que 'teclea' la persona: un texto, o una "
                    'lista de textos para que salgan en orden, uno por cada leer() (por '
                    f'ejemplo simular_teclado(["hola", "chau"])), y recibió '
                    f"{un(tecleado)}"
                    + (" (vacía, o con algo que no es un texto)"
                       if isinstance(tecleado, list) else ""))
            self.tecleado, self.tecleados = list(lista), 0

        @nativa("mensajes_enviados")
        def _(tipo=None):
            if not self.en_prueba:
                raise ErrorMate(SOLO_EN_PRUEBA)
            if tipo is not None and pedir(tipo, "texto", "mensajes_enviados()") \
                    not in self.mensajes:
                raise ErrorMate(con_sugerencia(
                    f"mensajes_enviados(): no existe el mensaje '{tipo}'", tipo, self.mensajes))
            if self.contexto is None:
                self.vaciar_cola()  # lo enviado en la prueba llega antes de mirar
            numero0, conversacion0 = self.desde
            return [{"numero": numero - numero0, "de": de, "a": a, "tipo": msg.tipo,
                     "mensaje": msg, "pregunta": pregunta,
                     "conversacion": conversacion - conversacion0,
                     "respuesta_a": respuesta_a - numero0 if respuesta_a else None}
                    for numero, de, a, msg, pregunta, conversacion, respuesta_a
                    in self.historial if tipo is None or msg.tipo == tipo]

    # ── lo que aprenden los agentes (0.4) ──
    def el_que_aprende(self, funcion, agente):
        """De quién son las lecciones de aprender() o lecciones(): del agente que está
        atendiendo o, en una prueba, del que se nombra."""
        if self.contexto is not None:
            if agente is not None and agente is not self.contexto[0]:
                raise ErrorMate(f"{funcion}(): dentro de un agente va sin decir a cuál: cada "
                                "uno anota y lee solo sus propias lecciones")
            return self.contexto[0]
        antes = '"la lección", ' if funcion == "aprender" else ""
        if isinstance(agente, Agente) and agente.ajeno is not None:
            raise ErrorMate(de_otro_programa(agente.nombre, agente.ajeno,
                                             f"usar {funcion}() con él"))
        if not self.en_prueba:
            raise ErrorMate(SOLO_EN_AGENTE.format(n=funcion, antes=antes))
        if agente is None:
            raise ErrorMate(f"{funcion}(): en una prueba hay que decir de qué agente: "
                            f"{funcion}({antes}Mostrador)")
        if not isinstance(agente, Agente):
            raise ErrorMate(f"{funcion}() espera un agente (por ejemplo "
                            f"{funcion}({antes}Mostrador)) y recibió {un(agente)}")
        self.vaciar_cola()  # lo enviado en la prueba llega antes de mirar
        return agente

    def lecciones_de(self, agente):
        """Las lecciones que valen para ese agente, como textos: las suyas y, si es una
        copia, antes las del agente del que es copia. Nunca más que el tope."""
        molde = self.agentes.get(agente.decl[2])
        todas = (molde.lecciones if molde is not None and molde is not agente else []) \
            + agente.lecciones
        if len(todas) > MAX_LECCIONES:
            self.avisar_una_vez(("muchas", agente.nombre), (
                f"entre las suyas y las de {agente.decl[2]}, {agente.nombre} tiene más de "
                f"{MAX_LECCIONES} lecciones, que es el tope: usa solo las más nuevas"))
        return [leccion["texto"] for leccion in todas[-MAX_LECCIONES:]]

    # ── frenos para la IA y tope de gasto (0.5) ──
    def frenos_de(self, agente):
        """Los frenos de ese agente con sus valores de ahora (se calculan en cada consulta,
        así 'precios: lista' sigue a la lista aunque cambie). Un valor 'nada' es "sin esa
        regla". Lo que no tiene la forma de su regla es un error que dice cuál y cómo va."""
        if self.calculando_frenos:
            raise error_de_ia("dentro de 'frenos' no se puede consultar a la IA: ahí van "
                              "datos (una lista, un número, un texto)")
        frenos = dict.fromkeys(REGLAS_DE_FRENO)
        self.calculando_frenos = True
        try:
            for ln, regla, e in agente.decl[6]:
                try:
                    valor = self.ev(e, agente.env)
                    if valor is None:
                        continue
                    que = f"en los frenos de {agente.decl[2]}, '{regla}'"
                    ejemplo = f". Por ejemplo:  {REGLAS_DE_FRENO[regla][1]}"
                    if nombre_tipo(valor) not in REGLAS_DE_FRENO[regla][0]:
                        raise ErrorMate(f"{que} recibió {un(valor)} y lleva otra cosa: son "
                                        f"{REGLAS_DE_FRENO[regla][2]}{ejemplo}")
                    if regla == "precios":
                        raros = importes_como_texto(valor)
                        if raros and not self.en_prueba:
                            self.avisar_una_vez(("precios como texto", agente.decl[2]), (
                                f"en los frenos de {agente.decl[2]}, 'precios' trae "
                                f"{len(raros)} dato(s) que parecen importes pero no son "
                                f"números (por ejemplo \"{en_un_renglon(raros[0], 30)}\"): no "
                                "cuentan como precios permitidos, así que si la IA nombra "
                                "ese precio va a saltar el freno. En la planilla, escribilos "
                                "como número: 3500 o 3.500,50"))
                        valor = numeros_permitidos(valor)
                    elif regla == "prohibido":
                        if len(valor) > MAX_PROHIBIDOS or not all(
                                isinstance(t, str) and t.strip() for t in valor):
                            raise ErrorMate(
                                f"{que} lleva una lista de textos (palabras o frases, hasta "
                                f"{MAX_PROHIBIDOS}, ninguna vacía){ejemplo}")
                    elif regla == "reserva":
                        if not valor.strip():
                            raise ErrorMate(f"{que} está vacía: es lo que va a leer el "
                                            f"cliente cuando salte un freno{ejemplo}")
                    elif type(valor) is not int or valor < (1 if regla == "largo" else 0):
                        raise ErrorMate(f"{que} lleva un número entero"
                                        f"{' mayor que cero' if regla == 'largo' else ''} y "
                                        f"recibió {formato(valor)}{ejemplo}")
                    frenos[regla] = valor
                except ErrorMate as error:
                    error.linea = ln
                    raise
        finally:
            self.calculando_frenos = False
        if frenos["reserva"] is None and any(
                frenos[regla] is not None for regla in REGLAS_DE_CONTENIDO):
            raise ErrorMate(f"a los frenos de {agente.decl[2]} les falta 'reserva' (quedó en "
                            "nada): es lo que contesta cuando la IA rompe una regla dos veces",
                            agente.decl[6][0][0])
        return frenos

    def anotar_freno(self, agente, que, pregunta, motivo):
        """Un freno que saltó (o un tope alcanzado), para la bitácora."""
        if self.bitacora is None or self.en_prueba:
            return
        self.bitacora.append((datetime.datetime.now().strftime("%d/%m/%Y %H:%M"),
                              agente.nombre, que, f"la consulta {recortado(pregunta)}", motivo))

    def con_frenos(self, agente, frenos, instrucciones, pregunta, ahora, consultar):
        """consultar_ia() de un agente con frenos: mira el tope de gasto, consulta, revisa
        la respuesta y, si rompe una regla, consulta UNA vez más avisándole a la IA cuál;
        si la vuelve a romper, devuelve el texto de reserva. Todo queda en la traza, en la
        bitácora y en consultas_ia() (los campos 'freno' y 'devuelto')."""
        quien, hondo = agente.nombre, len(self.atendiendo)
        molde = self.agentes.get(agente.decl[2], agente)  # las copias cuentan con el original
        dia, simulada = ahora.strftime("%Y-%m-%d"), self.ia_simulada
        anotadas = []

        def en_el_tope():
            hoy = molde.gasto.get(dia, {})
            tope = frenos["consultas_por_dia"]
            if simulada:
                # En un ensayo se cuentan solo las consultas simuladas de ESTA corrida: así
                # el mismo ensayo da lo mismo todas las veces que se lo corra en el día.
                hechas = hoy.get("simuladas", 0) - molde.ensayo_desde.get(dia, 0)
                if tope is not None and hechas >= tope:
                    return (f"ya hizo {hechas} consulta(s) simuladas a la IA en esta "
                            f"corrida y su tope es {tope} por día")
                return None
            hechas = hoy.get("consultas", 0)
            if tope is not None and hechas >= tope:
                return f"ya hizo {hechas} consulta(s) a la IA hoy y su tope es {tope} por día"
            tope = frenos["tokens_por_dia"]
            if tope is not None and hoy.get("tokens", 0) >= tope:
                return f"ya gastó {hoy['tokens']} tokens hoy y su tope es {tope} por día"
            return None

        def contar():
            hoy = molde.gasto.setdefault(dia, {"consultas": 0, "simuladas": 0, "tokens": 0})
            if simulada:
                hoy["simuladas"] += 1
                return
            hoy["consultas"] += 1
            hoy["tokens"] += _USO_DE_LA_IA.get("tokens") or 0
            if self.guardar_cuenta is not None and not self.en_prueba:
                self.guardar_cuenta()  # ya, por si después cierran la ventana

        def devolver(valor):
            for consulta in anotadas:
                consulta.setdefault("freno", "")
                consulta["devuelto"] = valor
            return valor

        def trazar(texto):
            if self.traza:
                self.trazar(texto, None, hondo)

        def sin_consultar(tope, que):
            """Se llegó al tope: no se consulta. Sale la reserva o, si no hay, un error."""
            trazar(f"tope de {quien}: {tope}. No consulta"
                   + ("" if frenos["reserva"] is None else " y devuelve el texto de reserva"))
            if (quien, "tope") not in self.avisados:  # una vez por corrida en la bitácora
                self.avisados.add((quien, "tope"))
                self.anotar_freno(agente, "llegó al tope de gasto", pregunta, tope)
            if not self.en_prueba:  # y una vez en pantalla: que no parezca que anda mal
                sigue = ("contesta con el texto de reserva, sin consultar"
                         if frenos["reserva"] is not None else
                         "no consulta más (y como no tiene 'reserva', cada consulta da error)")
                self.avisar_una_vez(("tope en pantalla", molde.nombre), (
                    f"{molde.nombre} llegó a su tope ({tope}). Desde ahora {sigue}. "
                    + ("Es un ensayo: en la próxima corrida con --ia-simulada la cuenta "
                       "arranca de cero." if simulada else
                       "Mañana vuelve a consultar sola.")
                    + " El tope se cambia en los 'frenos' del agente, y la cuenta se ve con:  "
                    f"{como_se_llama()} bitacora {para_pegar(self.archivo or 'programa.mate')}"))
            if (self.en_prueba or self.ensayando) and not anotadas:
                anotadas.append({"agente": quien, "instrucciones": instrucciones,
                                 "pregunta": pregunta, "respuesta": None, "freno": que})
                self.ia_historial.append(anotadas[-1])
            if frenos["reserva"] is None:
                devolver(None)
                raise ErrorMate(
                    f"consultar_ia(): {quien} {tope}: por hoy no consulta más. (Para que en "
                    "vez de fallar conteste algo, ponele una 'reserva' a sus frenos; el "
                    "tope se cambia ahí mismo)", familia="tope")
            return devolver(frenos["reserva"])

        def consultar_y_contar(de_nuevo=None):
            """La consulta, sumada a la cuenta del día. También cuenta la que llegó a la IA
            y después no sirvió (cortada, sin texto, demasiado larga): se cobra igual."""
            _USO_DE_LA_IA.clear()
            try:
                resultado = consultar(de_nuevo) if de_nuevo else consultar()
            except ErrorMate:
                if not simulada and _USO_DE_LA_IA.get("cobrada"):
                    contar()
                raise
            contar()
            return resultado

        if not simulada and self.guardar_cuenta is not None and not self.en_prueba:
            self.guardar_cuenta()  # (por si otra ventana ya gastó parte del tope de hoy)
        tope = en_el_tope()
        if tope:
            return sin_consultar(tope, "tope de gasto: " + tope)
        respuesta, consulta = consultar_y_contar()
        anotadas.append(consulta)
        rotas = reglas_rotas(respuesta, frenos)
        if not rotas:
            return devolver(respuesta)
        que = "; ".join(motivo for _, motivo, _ in rotas)
        consulta["freno"] = que
        dicho = f"La IA había contestado: {recortado(respuesta, 200)}"
        trazar(f"freno de {quien}: la respuesta no pasa ({que}). Consulta una vez más")
        if self.recordando and not self.en_prueba:
            # Queda una lección propuesta: no se usa hasta que el dueño la aprueba.
            cuantas = len(molde.propuestas)
            for _, motivo, leccion in rotas:
                molde.propuestas = sumar_propuesta(
                    molde.propuestas, molde.lecciones, leccion,
                    f"saltó un freno: {motivo}. {dicho}", ahora.strftime("%d/%m/%Y %H:%M"))
            if len(molde.propuestas) != cuantas:
                self.avisar_una_vez(("propuestas", molde.nombre), (
                    f"saltó un freno de {molde.nombre} y quedó una lección propuesta, que "
                    "no se usa hasta que la apruebes. Para verlas:  "
                    f"{como_se_llama()} propuestas {para_pegar(self.archivo or 'programa.mate')}"))
        tope = en_el_tope()
        if tope:
            self.anotar_freno(agente, "saltó un freno (contestó con el texto de reserva)",
                              pregunta, f"{que}. {dicho}. No hubo segundo intento: {tope}")
            self.avisados.add((quien, "tope"))  # (ya quedó dicho en ese renglón)
            return sin_consultar(tope, que)
        try:
            respuesta, consulta = consultar_y_contar(aviso_de_freno(pregunta, rotas))
        except ErrorMate as error:
            if error.clase != "falla":
                raise
            segundo = "el segundo intento falló (" + error.mensaje.split("\n")[0] + ")"
        else:
            anotadas.append(consulta)
            rotas = reglas_rotas(respuesta, frenos)
            if not rotas:
                trazar(f"freno de {quien}: el segundo intento pasa")
                self.anotar_freno(agente, "saltó un freno (el segundo intento salió bien)",
                                  pregunta, f"{que}. {dicho}")
                return devolver(respuesta)
            consulta["freno"] = "; ".join(motivo for _, motivo, _ in rotas)
            segundo = f"el segundo intento tampoco pasa ({consulta['freno']})"
        trazar(f"freno de {quien}: {segundo}. Devuelve el texto de reserva: "
               f"{recortado(frenos['reserva'])}")
        self.anotar_freno(agente, "saltó un freno (contestó con el texto de reserva)",
                          pregunta, f"{que}. {dicho}")
        return devolver(frenos["reserva"])

    def avisar_una_vez(self, cual, texto):
        if cual not in self.avisados:
            self.avisados.add(cual)
            self.avisar(texto)

    def recordado(self, agente, nombre, inicial):
        """El valor con que arranca un 'estado recordado': el que quedó guardado en la
        corrida anterior o, si no hay (o ya no es del mismo tipo), el inicial."""
        if not self.recordando:
            return inicial
        if not agente.recuerda:
            molde = agente.decl[2]
            self.avisar_una_vez(("sin nombre", molde), (
                f"las copias de {molde} creadas sin nombre no recuerdan nada de una corrida "
                "a la otra (no se sabría cuál es cuál). Para que una copia tenga memoria, "
                f'dale un nombre:  crear {molde} llamado "Centro"'))
            return inicial
        guardado = self.memoria.get(agente.nombre, {}).get("estado", {})
        if nombre not in guardado:
            return inicial
        de = f"{agente.nombre}.{nombre}"
        try:
            valor = self._de_json(guardado[nombre], memoria=True)
        except ErrorMate as e:
            self.avisar(f"lo que {de} tenía guardado en la memoria ya no sirve "
                        f"({e.mensaje}): arranca con su valor inicial")
            return inicial
        if inicial is not None and valor is not None \
                and nombre_tipo(valor) != nombre_tipo(inicial):
            self.avisar(f"{de} está guardado en la memoria como {nombre_tipo(valor)} y en el "
                        f"programa ahora es {nombre_tipo(inicial)}: no uso lo guardado y "
                        "arranca con su valor inicial")
            return inicial
        return valor

    def memoria_actual(self):
        """Lo que hay que guardar al terminar: lo que se leyó, con el estado recordado y
        las lecciones de los agentes de esta corrida puestos encima."""
        nueva = {a: dict(f, estado=dict(f["estado"]), lecciones=list(f["lecciones"]))
                 for a, f in self.memoria.items()}
        for agente in list(self.agentes.values()) + self.vivos:
            if not agente.recuerda:
                continue
            previa = nueva.get(agente.nombre, {"estado": {}})["estado"]
            estado = {}
            for declarado in (agente.decl[3] if agente.env is not None else ()):
                nombre = declarado[1]
                if not isinstance(declarado, EstadoRecordado) or nombre not in agente.env.vars:
                    continue
                valor = agente.env.vars[nombre][0]
                try:
                    if not se_puede_recordar(valor):
                        raise ValueError
                    estado[nombre] = self._a_json(valor, memoria=True)
                    json.dumps(estado[nombre], allow_nan=False)
                except (ErrorMate, ValueError, RecursionError):
                    estado.pop(nombre, None)
                    if nombre in previa:
                        estado[nombre] = previa[nombre]
                    self.avisar(
                        f"{agente.nombre}.{nombre} no se pudo guardar en la memoria: solo "
                        "se recuerdan datos (números, textos, listas, mapas y mensajes), "
                        "no agentes ni funciones")
            if agente.env is None:
                estado = previa  # no llegó a nacer en esta corrida: queda lo que había
            ficha = {"estado": estado, "lecciones": list(agente.lecciones)}
            if self.agentes.get(agente.nombre) is agente:
                propuestas, gasto = list(agente.propuestas), gasto_limpio(agente.gasto)
            else:  # una copia con nombre: lo que tuviera anotado a mano queda como estaba
                anterior = nueva.get(agente.nombre, {})
                propuestas, gasto = anterior.get("propuestas"), anterior.get("gasto")
            if propuestas:
                ficha["propuestas"] = propuestas
            if gasto:
                ficha["gasto"] = gasto
            nueva[agente.nombre] = ficha
        return {a: f for a, f in nueva.items() if any(f.values())}

    def anotar_falla(self, agente, e, msg, atajada=False):
        """Una falla de un agente, para la bitácora (si este programa la lleva). El mismo
        error no se anota dos veces para el mismo agente."""
        if self.bitacora is None or self.en_prueba:
            return
        vistos = e.__dict__.setdefault("en_bitacora", set())
        if agente.nombre in vistos:
            return
        vistos.add(agente.nombre)
        que = {"ia": "la IA no contestó", "contrato": "contrato rechazado"}.get(
            e.familia, "falló")
        if atajada:
            que += " (lo atajó con 'intentar')"
        if msg is None:
            atendia = "(ningún mensaje)"
        elif msg.tipo == AL_FALLAR:
            atendia = "el aviso de que un mensaje suyo no se pudo atender"
        else:
            atendia = formato(msg)
        self.bitacora.append((datetime.datetime.now().strftime("%d/%m/%Y %H:%M"),
                              agente.nombre, que, atendia, e.mensaje))

    def respuesta_simulada(self, pregunta, preparada):
        """Lo que contesta la IA cuando no se sale a la red. Manda lo que fijó la prueba con
        simular_ia(); si no, el archivo de respuestas; si no, el tercer valor de la llamada."""
        if self.ia_fijada is not None:
            if not self.ia_en_orden:
                return self.ia_fijada[0]
            if self.ia_usadas >= len(self.ia_fijada):
                raise error_de_ia(
                    f"la prueba le hizo {self.ia_usadas + 1} consultas a la IA y simular_ia() "
                    f"tenía {len(self.ia_fijada)} respuesta(s): agregá las que faltan a la "
                    "lista")
            self.ia_usadas += 1
            return self.ia_fijada[self.ia_usadas - 1]
        del_archivo = respuesta_del_archivo(self.ia_respuestas, pregunta)
        if del_archivo is not None:
            return del_archivo
        if preparada is not None:
            return preparada
        if self.ia_respuestas:
            raise error_de_ia(
                "el archivo de respuestas simuladas no tiene ninguna para esta consulta: "
                f"{recortado(pregunta)}. Agregale un renglón, o uno que conteste a todo:  "
                "* => lo que contesta")
        raise ErrorMate(SIN_RESPUESTA_SIMULADA, familia="ia")

    def _a_json(self, v, memoria=False):
        """memoria: para el archivo de memoria, donde lo que se guardó como mapa tiene que
        volver como mapa. Ahí un mapa del programa que tiene justo la forma de un mensaje
        ({tipo, campos}) se guarda envuelto: {"mapa": {...}}."""
        if isinstance(v, Registro):
            return {"tipo": v.tipo,
                    "campos": {k: self._a_json(x, memoria) for k, x in v.campos.items()}}
        if isinstance(v, Agente):
            if v.ajeno is not None:
                raise ErrorMate(de_otro_programa(v.nombre, v.ajeno, "pasarlo a JSON"))
            return {"agente": v.nombre}
        if isinstance(v, list):
            return [self._a_json(x, memoria) for x in v]
        if isinstance(v, dict):
            mapa = {k: self._a_json(x, memoria) for k, x in v.items()}
            return {"mapa": mapa} if memoria and set(v) in ({"tipo", "campos"}, {"mapa"}) \
                else mapa
        if isinstance(v, (Funcion, Nativa, ModuloPython)):
            raise ErrorMate("una función no se puede pasar a JSON")
        return v

    def amoldar(self, valor, tipo):
        """Lo que llegó de afuera, con los mensajes que pide el contrato ya armados: donde
        se espera un Pedido y hay un mapa con sus campos, queda el Pedido (también
        adentro de una lista o de otro mensaje)."""
        if tipo.startswith("lista de ") and isinstance(valor, list):
            return [self.amoldar(x, tipo[len("lista de "):]) for x in valor]
        if tipo in self.mensajes and isinstance(valor, dict):
            tipos = {campo: t for campo, t, _ in self.mensajes[tipo]}
            return self.construir(tipo, {
                k: self.amoldar(v, tipos[k]) if k in tipos else v for k, v in valor.items()})
        return valor

    def _de_json(self, v, memoria=False):
        if isinstance(v, list):
            return [self._de_json(x, memoria) for x in v]
        if memoria and isinstance(v, dict):
            # En la memoria nunca hay agentes, y un mapa envuelto vuelve como mapa.
            if set(v) == {"mapa"} and isinstance(v["mapa"], dict):
                return {k: self._de_json(x, True) for k, x in v["mapa"].items()}
            if set(v) == {"tipo", "campos"} and isinstance(v["tipo"], str) \
                    and v["tipo"] in self.mensajes and isinstance(v["campos"], dict):
                return self.construir(
                    v["tipo"], {k: self._de_json(x, True) for k, x in v["campos"].items()})
            return {k: self._de_json(x, True) for k, x in v.items()}
        if isinstance(v, dict):
            if set(v) == {"tipo", "campos"} and isinstance(v["tipo"], str) \
                    and v["tipo"] in self.mensajes and isinstance(v["campos"], dict):
                return self.construir(
                    v["tipo"], {k: self._de_json(x) for k, x in v["campos"].items()})
            if set(v) == {"agente"} and isinstance(v["agente"], str):
                # un agente declarado o una copia: los nombres no se repiten
                ag = self.agentes.get(v["agente"]) or next(
                    (a for a in self.vivos if a.nombre == v["agente"]), None)
                if ag is not None:
                    return ag
            return {k: self._de_json(x) for k, x in v.items()}
        return v

    # ── mensajes ──
    def cumple(self, valor, tipo):
        if tipo == "cualquiera":
            return True
        if tipo.startswith("lista de "):
            return isinstance(valor, list) and all(
                self.cumple(x, tipo[len("lista de "):]) for x in valor)
        return nombre_tipo(valor) == tipo

    def no_cumple(self, valor, tipo):
        """Qué recibió, dicho para un error: 'texto', o qué hay de más adentro de la lista."""
        if tipo.startswith("lista de ") and isinstance(valor, list):
            de = tipo[len("lista de "):]
            i = next(i for i, x in enumerate(valor) if not self.cumple(x, de))
            return f"una lista que en la posición {i} tiene {un(valor[i])}"
        return tipo_claro(valor)

    def construir(self, nombre, dados):
        try:
            return self._construir(nombre, dados)
        except ErrorMate as e:
            e.familia = "contrato"
            raise

    def _construir(self, nombre, dados):
        if nombre not in self.mensajes:
            raise ErrorMate(con_sugerencia(
                f"no existe el mensaje '{nombre}'", nombre, self.mensajes))
        campos = {}
        reglas = self.reglas.get(nombre) or {}
        for campo, tipo, opcional in self.mensajes[nombre]:
            regla = reglas.get(campo)
            if regla and "defecto" in regla and dados.get(campo) is None:
                campos[campo] = regla["defecto"]  # no vino (o vino nada): el de siempre
                continue
            if campo not in dados:
                if not opcional:
                    raise ErrorMate(f"a {nombre} le falta el campo '{campo}'")
                campos[campo] = None
                continue
            v = dados[campo]
            if lleva_funcion(v):
                raise ErrorMate("los mensajes llevan datos, no funciones "
                                f"(campo '{campo}' de {nombre})")
            if (self.ajenos or self.remitentes) and v.__class__ not in _SUELTOS:
                de_afuera = lleva_agente(v, ajeno=True)
                if de_afuera is not None:
                    raise ErrorMate(de_otro_programa(
                        de_afuera.nombre, de_afuera.ajeno,
                        f"ponerlo adentro de un mensaje (campo '{campo}' de {nombre})"))
            if not (self.cumple(v, tipo) or (opcional and v is None)):
                raise ErrorMate(
                    f"{nombre}.{campo} es de tipo {tipo} y recibió {self.no_cumple(v, tipo)}")
            rota = rompe_regla(f"{nombre}.{campo}", v, regla)
            if rota:
                raise ErrorMate(rota)
            campos[campo] = v
        for k in dados:
            if k not in campos:
                raise ErrorMate(con_sugerencia(f"{nombre} no tiene un campo '{k}'", k, campos))
        return Registro(nombre, campos)

    # ── carga del programa ──
    def cargar(self, programa):
        for s in programa:
            if s[0] == "mensaje":
                self.mensajes[s[2]] = s[3]
                self.reglas[s[2]] = s[5]
                if s[4]:
                    self.responde[s[2]] = s[4]
        for s in programa:
            try:
                if s[0] == "funcion":
                    self.glob.definir(s[2], Funcion(s[2], s[3], s[4], self.glob, s[5]),
                                      origen="funcion", linea=s[1])
                elif s[0] == "usar_python":
                    if self.glob.origen.get(s[2]) == "python" \
                            and self.glob.vars[s[2]][0].archivo == s[3]:
                        del self.glob.vars[s[2]]  # en la consola: se trae de nuevo, al día
                    self.glob.definir(s[2], cargar_python(s[2], s[3]), origen="python",
                                      linea=s[1])
                elif s[0] == "agente":
                    ag = Agente(s[2])
                    ag.decl = s
                    ag.lecciones = list(self.memoria.get(s[2], {}).get("lecciones", []))
                    ag.propuestas = list(self.memoria.get(s[2], {}).get("propuestas", []))
                    ag.gasto = {dia: dict(cuenta) for dia, cuenta in
                                self.memoria.get(s[2], {}).get("gasto", {}).items()}
                    ag.ensayo_desde = {dia: cuenta.get("simuladas", 0)
                                       for dia, cuenta in ag.gasto.items()}
                    ag.manejadores = self.manejadores_de(s)
                    self.agentes[s[2]] = ag
                    self.decl_agentes.append(s)
                    self.glob.definir(s[2], ag, origen="agente")
                elif s[0] == "agente_ajeno":
                    ag = self.agente_de_otro(s[2], s[4], nombre_de_programa(s[4]), s[5],
                                             s[3])
                    if s[4] == SOCIO:
                        ag.socio = s[2]
                    self.ajenos[s[2]] = ag
                    self.glob.definir(s[2], ag, origen="agente")
            except ErrorMate as e:
                e.linea = e.linea or s[1]
                raise

        contrato = ContratoConversacion.del_programa(programa, self.mensajes, self.agentes)
        if contrato is not None:
            self.contrato_conversacion = contrato

    def agente_de_otro(self, nombre, archivo, programa, carpeta, tipos=(),
                       solo_responde=False):
        """Un agente de otro programa: no tiene estado ni atiende nada acá. Es a quien
        se le manda (o se le contesta) por el buzón."""
        ag = Agente(nombre)
        ag.ajeno, ag.programa, ag.carpeta_buzon = archivo, programa, carpeta
        ag.solo_responde, ag.recuerda = solo_responde, False
        ag.decl = ("agente", None, nombre, [], [], [], [])
        ag.env = Entorno(self.glob, frontera=True)
        ag.propios = {tipo: None for tipo in tipos}
        ag.manejadores = dict(ag.propios)
        return ag

    def manejadores_de(self, decl):
        """Qué mensajes entiende un agente: queda fijo desde la declaración."""
        return {tipo: (ln, var, cuerpo) for ln, tipo, var, cuerpo in decl[4]}

    def instanciar(self, ag, dados=None, linea=None):
        """Deja al agente recién nacido: estado inicial (o el que le den) y sin pendientes."""
        s, dados = ag.decl, dados or {}
        env = Entorno(self.glob, frontera=True)
        for f in s[5]:
            env.definir(f[2], Funcion(f[2], f[3], f[4], env, f[5]), origen="funcion")
        # Mientras nace no se le entregan mensajes: todavía no tiene todo su estado.
        self.naciendo += 1
        ag.ocupado = True  # si alguien le habla mientras nace, es un ciclo
        try:
            for declarado in s[3]:
                ln, nombre, e = declarado
                try:
                    valor = self.estado_inicial(s[2], nombre, e, env, dados, linea)
                    if isinstance(declarado, EstadoRecordado):
                        valor = self.recordado(ag, nombre, valor)
                    env.definir(nombre, valor, mutable=True)
                except ErrorMate as err:
                    err.linea = err.linea or ln
                    raise
        finally:
            self.naciendo -= 1
            ag.ocupado = False
        ag.env = env
        ag.manejadores = self.manejadores_de(s)
        if ag.inicial is None:
            ag.inicial = self.copia_de(env)

    def estado_inicial(self, agente, nombre, e, env, dados, linea):
        """El valor con que arranca un estado: el que le dieron a 'crear' o el declarado.
        Si se lo dieron, lo declarado no se calcula (no repite lo que muestre o cree)."""
        if nombre not in dados:
            valor = self.ev(e, env)
            if valor is not None:
                self.tipos_estado.setdefault((agente, nombre), nombre_tipo(valor))
            return valor
        valor = dados[nombre]
        declarado = self.tipos_estado.get((agente, nombre)) or _LITERALES.get(e[0])
        # 'nada' siempre vale: "sin tope", "sin cliente todavía"
        if valor is not None and declarado and declarado != nombre_tipo(valor):
            raise ErrorMate(f"{agente}.{nombre} arranca como {declarado} y le diste "
                            f"{nombre_tipo(valor)}", linea)
        return valor

    @staticmethod
    def copia_de(env):
        return {k: list(v) for k, v in env.vars.items()}, dict(env.origen)

    @staticmethod
    def restaurar(env, guardado):
        env.vars = {k: list(v) for k, v in guardado[0].items()}
        env.origen = dict(guardado[1])

    def reiniciar_agentes(self):
        """Los agentes declarados vuelven al estado con el que nacieron."""
        for s in self.decl_agentes:
            ag = self.agentes[s[2]]
            if ag.inicial is None:
                self.instanciar(ag)
            else:
                self.restaurar(ag.env, ag.inicial)
                ag.ocupado = False
                ag.manejadores = self.manejadores_de(s)  # sin lo que se haya simulado
        for ag in self.ajenos.values():
            ag.manejadores, ag.ocupado = dict(ag.propios), False
        self.cola.clear()

    def entornos_vivos(self):
        """Todos los lugares donde quedó guardada una variable: lo de afuera, los agentes
        y lo que recuerdan las funciones hechas por otras funciones."""
        vistos, pendientes = {}, [self.glob]
        pendientes += [ag.env for ag in list(self.agentes.values()) + self.vivos if ag.env]

        def mirar(v):
            if isinstance(v, Funcion):
                pendientes.append(v.env)
            elif isinstance(v, Agente):
                if v.env:
                    pendientes.append(v.env)
            elif isinstance(v, list):
                for x in v:
                    mirar(x)
            elif isinstance(v, dict):
                for x in v.values():
                    mirar(x)
            elif isinstance(v, Registro):
                for x in v.campos.values():
                    mirar(x)

        while pendientes:
            env = pendientes.pop()
            while env is not None and id(env) not in vistos:
                vistos[id(env)] = env
                for valor, _ in list(env.vars.values()):
                    mirar(valor)
                env = env.padre
        return list(vistos.values())

    def foto(self):
        """Cómo quedó el mundo al terminar el programa: las variables de afuera, las copias
        y lo que guardan las funciones."""
        return ([(env, self.copia_de(env)) for env in self.entornos_vivos()],
                list(self.vivos), dict(self.copias), dict(self.charlas))

    def volver_a(self, foto):
        """Cada prueba empieza limpia: todo como en la foto, y los agentes declarados
        como recién nacidos."""
        for env, guardado in foto[0]:
            self.restaurar(env, guardado)
        self.vivos = list(foto[1])
        for ag in self.vivos:
            ag.ocupado = False
            ag.manejadores = self.manejadores_de(ag.decl)
        self.copias = dict(foto[2])
        self.charlas = dict(foto[3])
        self.reiniciar_agentes()

    def crear(self, n, env):
        if n[2] in self.ajenos:
            raise ErrorMate(de_otro_programa(n[2], self.ajenos[n[2]].ajeno,
                                             "crear una copia"))
        if n[2] not in self.agentes:
            raise ErrorMate(con_sugerencia(
                f"no existe el agente '{n[2]}'", n[2], self.agentes))
        molde = self.agentes[n[2]]
        declarados = {nombre for _, nombre, _ in molde.decl[3]}
        dados = {}
        for k, e in n[4]:
            if k not in declarados:
                raise ErrorMate(f"{n[2]} no tiene un estado '{k}'")
            dados[k] = self.ev(e, env)
        apodo = None if n[3] is None else self.ev(n[3], env)
        if n[3] is not None and not isinstance(apodo, str):
            raise ErrorMate(
                "el nombre de la copia (después de 'llamado') tiene que ser un texto, y "
                f"recibió {un(apodo)}"
                + ('. Pasalo a texto: llamado "Sucursal {numero}"' if es_num(apodo) else ""),
                n[1])
        if apodo is not None and not apodo.strip():
            raise ErrorMate("el nombre de la copia (después de 'llamado') no puede estar "
                            "vacío", n[1])
        if apodo is not None and any(a.nombre == f"{n[2]} {apodo}" for a in self.vivos):
            raise ErrorMate(
                f'ya hay un {n[2]} llamado "{apodo}": dos copias no pueden llamarse igual, '
                "porque no se las podría distinguir. Elegí otro nombre", n[1])
        ag = Agente(f"{n[2]} {apodo}" if apodo is not None else f"{n[2]} nuevo")
        ag.decl = molde.decl
        ag.recuerda = apodo is not None  # sin nombre no se sabría cuál es cuál
        if ag.recuerda:
            ag.lecciones = list(self.memoria.get(ag.nombre, {}).get("lecciones", []))
        self.instanciar(ag, dados, n[1])
        # Recién ahora gasta un número: un 'crear' rechazado no corre la numeración.
        self.copias[n[2]] = self.copias.get(n[2], 1) + 1
        if apodo is None:
            ag.nombre = f"{n[2]}#{self.copias[n[2]]}"
        ag.creador = self.contexto[0] if self.contexto else None
        self.vivos.append(ag)
        return ag

    def correr(self, programa, pruebas=False):
        """Ejecuta el programa. Con pruebas=True devuelve [(nombre, error|None)]."""
        # El análisis ya rechaza 'devolver' y 'responder' fuera de lugar; esto es la red.
        tope = sys.getrecursionlimit()
        try:
            if NIVELES_DE_PYTHON > tope:
                sys.setrecursionlimit(NIVELES_DE_PYTHON)
            return self._correr(programa, pruebas)
        except _Retorno:
            raise ErrorMate(DEVOLVER_SUELTO, self.linea_actual)
        except _Respuesta:
            raise ErrorMate(RESPONDER_SUELTO, self.linea_actual)
        except (_Romper, _Continuar):
            raise ErrorMate("'romper' y 'continuar' solo van dentro de un 'mientras' o de "
                            "un 'para'", self.linea_actual)
        finally:
            sys.setrecursionlimit(tope)

    def demasiada_recursion(self, nombre, linea=None):
        """El error de una función que se llama a sí misma sin parar."""
        if nombre is None:
            return ErrorMate("demasiada recursión: hay demasiadas cosas una adentro de la "
                             "otra", linea, clase="limite")
        return ErrorMate(
            "demasiada recursión: hay demasiadas llamadas a funciones sin terminar, una "
            f"adentro de la otra (la última, a {nombre}()). Si {nombre}() se llama a sí "
            "misma, revisá que tenga un 'si' que la frene y que cada llamada se acerque a "
            "ese final", linea, clase="limite")

    def _correr(self, programa, pruebas):
        self.sin_teclado = self.sin_teclado or pruebas
        self.fecha_fija = self.fecha_fija or pruebas
        self.ia_simulada = self.ia_simulada or pruebas  # 'probar' nunca sale a la red
        if pruebas and self.archivos_de_prueba is None:
            self.archivos_de_prueba = {}  # ...ni agrega renglones a los archivos de verdad
        if pruebas:  # ...ni lee ni escribe memoria o bitácora: cada prueba arranca limpia
            self.recordando, self.memoria, self.bitacora = False, {}, None
            self.buzon, self.probando = None, True  # ...ni ningún buzón
        self.cargar(programa)
        for s in programa:
            if s[0] == "agente":
                # El estado inicial se calcula donde está declarado el agente,
                # salvo que alguien le haya hablado antes.
                if self.agentes[s[2]].env is None:
                    self.instanciar(self.agentes[s[2]])
            elif s[0] not in ("mensaje", "funcion", "prueba", "usar_python",
                              "contrato_conversacion", "agente_ajeno", "usar_socio"):
                self.ejecutar(s, self.glob)
        self.vaciar_cola()
        if not pruebas:
            return []
        self.errores_principal = list(self.errores_agentes_det)
        foto = self.foto()
        agregado = dict(self.archivos_de_prueba)  # lo que 'agregó' el programa, sin el disco
        resultados = []
        self.en_prueba = True
        try:
            for s in programa:
                if s[0] != "prueba":
                    continue
                self.volver_a(foto)
                for agente in list(self.agentes.values()) + self.vivos:
                    agente.lecciones = []  # las de la prueba se fijan con aprender()
                    agente.gasto = {}  # y la cuenta de consultas arranca de cero
                self.ia_historial = []
                self.errores_agentes, self.errores_agentes_det = [], []
                self.pasos = 0
                self.entregados = 0
                # El historial de cada prueba arranca vacío, y cuenta desde 1.
                self.historial = []
                self.ia_fijada, self.ia_en_orden, self.ia_usadas = None, False, 0
                self.tecleado, self.tecleados = None, 0
                self.archivos_de_prueba = dict(agregado)
                self.desde = (self.cuenta["enviar"] + self.cuenta["preguntar"],
                              self.conversaciones)
                fallas, mostrado, salida = [], [], self.salida
                if self.separar_salida:
                    self.salida = mostrado.append
                if self.traza and self.anotar:
                    # En el archivo de la conversación, cada prueba va con su título:
                    # adentro los mensajes se numeran desde 1.
                    self.anotar("")
                    self.anotar(f'Prueba "{s[2]}" (los números arrancan de nuevo, igual '
                                "que en mensajes_enviados()):")
                try:
                    self.bloque(s[3], Entorno(self.glob, borde=True), nuevo=False)
                    self.vaciar_cola()
                except ErrorMate as e:
                    fallas.append((e.linea, self.con_camino(e.mensaje, e)))
                finally:
                    self.salida = salida
                self.mostrado_pruebas.append(mostrado)
                # Además de lo que cortó la prueba, lo que falló en los agentes: suele
                # ser la causa.
                fallas += self.errores_agentes_det
                self.detalle_pruebas.append(fallas)
                resultados.append((s[2], "\n".join(
                    self.con_lugar(linea, texto) for linea, texto in fallas) or None))
        finally:
            self.en_prueba = False
        return resultados

    def donde(self, linea):
        """'línea 7', o 'lib.mate, línea 7' si el renglón es de un archivo traído con usar."""
        archivo = getattr(linea, "archivo", None)
        if archivo and self.archivo and archivo != self.archivo:
            return f"{os.path.basename(archivo)}, línea {linea}"
        return f"línea {linea}"

    def con_lugar(self, linea, texto):
        """Todos los errores se escriben igual, con el renglón adelante: 'línea 7: ...'."""
        return f"{self.donde(linea)}: {texto}" if linea else texto

    # ── agentes ──
    def vaciar_cola(self):
        while self.cola:
            rem, dest, msg, sobre = self.cola.popleft()
            try:
                self.entregar(rem, dest, msg, pregunta=False, sobre=sobre)
            except ErrorMate as e:
                if e.clase == "limite":  # el freno corta todo el programa, no un solo mensaje
                    raise
                if rem is not None and msg.tipo != AL_FALLAR and AL_FALLAR in rem.manejadores:
                    # El que lo envió pidió enterarse: el aviso le llega como un mensaje
                    # más, y la falla queda en sus manos (no se anota como error).
                    self.cola.append((dest, rem, Registro(AL_FALLAR, {
                        "motivo": e.mensaje, "mensaje": msg, "destino": dest}),
                        (sobre[0], None)))
                    continue
                self.anotar_error_de_agente(dest, msg, e)

    def anotar_error_de_agente(self, dest, msg, e):
        """El error de un agente que falló atendiendo algo que le enviaron: queda en la
        lista de errores del programa (se muestra al final, y el código de salida es 1)."""
        que = "en 'al fallar'" if msg.tipo == AL_FALLAR else f"al recibir {msg.tipo}"
        linea = e.linea or getattr(e, "renglon", None)
        texto = TextoDeError(self.con_camino(f"{dest.nombre} {que}: {e.mensaje}", e))
        texto.familia = e.familia
        self.errores_agentes.append(self.con_lugar(linea, texto))
        self.errores_agentes_det.append((linea, texto))

    def ciclo(self, dest, linea):
        """El error de un ciclo de preguntas, con la cadena: A → B → A."""
        fin = f"{dest.nombre} todavía está atendiendo otro mensaje"
        desde = next((i for i, a in enumerate(self.atendiendo) if a[0] is dest), None)
        if desde is None:
            return ErrorMate(f"ciclo de preguntas: {fin}", familia="ciclo")
        cadena = self.atendiendo[desde:] + [(dest, linea)]
        pasos = []
        for (quien, _), (a_quien, renglon) in zip(cadena, cadena[1:]):
            en = f" ({self.donde(renglon)})" if renglon else ""
            pasos.append(f"{quien.nombre} le preguntó a {a_quien.nombre}{en}")
        flecha = simbolo(" → ", " -> ")
        return ErrorMate(f"ciclo de preguntas: {flecha.join(a.nombre for a, _ in cadena)}. "
                         f"{', '.join(pasos)}, y {fin}", familia="ciclo")

    def camino(self, e):
        """Por dónde se llegó al error: '' o un renglón como "cómo se llegó: en precio(),
        llamada desde total() (línea 4), llamada desde la línea 9"."""
        partes, pendiente = [], None  # pendiente: el renglón desde donde se llamó a la última
        for paso in e.camino:
            if paso[0] == "funcion":
                partes.append(f"en {paso[1]}()" if pendiente is None else
                              f"llamada desde {paso[1]}() ({self.donde(pendiente)})")
                pendiente = paso[2] or 0
            else:
                if pendiente:
                    partes.append(f"llamada desde la {self.donde(pendiente)}")
                pendiente = None
                en = f" ({self.donde(paso[3])})" if paso[3] else ""
                partes.append(f"se lo preguntó {paso[2] or 'el programa'} a {paso[1]}{en}")
        if pendiente:
            partes.append(f"llamada desde la {self.donde(pendiente)}")
        if len(partes) > 7:  # una función que se llama a sí misma muchas veces
            partes = partes[:4] + ["..."] + partes[-2:]
        return "cómo se llegó: " + ", ".join(partes) if partes else ""

    def con_camino(self, texto, e):
        camino = self.camino(e)
        return f"{texto}\n{camino}" if camino else texto

    def en_conversacion(self):
        """El número de conversación de lo que se manda ahora: el del mensaje que se está
        atendiendo o, si lo manda el programa, uno nuevo."""
        if self.conversacion is None:
            self.conversaciones += 1
            return self.conversaciones
        return self.conversacion

    def entregar(self, rem, dest, msg, pregunta, linea=None, sobre=None):
        """sobre: (número de conversación, número del mensaje al que responde o None). Lo
        trae lo que viene de la cola; una pregunta lo arma acá."""
        self.entregados += 1
        if self.entregados > MAX_MENSAJES:
            raise ErrorMate(
                f"se superaron {MAX_MENSAJES} mensajes: ¿los agentes entraron en bucle?",
                clase="limite")
        contrato = self.contrato_conversacion
        charla = estado_previo = None
        if contrato and msg.tipo in contrato.tipos:
            if msg.tipo not in contrato.preguntas:
                raise ErrorMate(f"'{msg.tipo}' solo puede viajar como respuesta en este contrato",
                                linea, familia="contrato")
            padre = self.origen_de_charla if self.contexto else None
            charla = contrato.identificador(msg, linea)
            if padre is not None:
                contrato.mismo_id(contrato.identificador(padre, linea), msg, linea)
            if not pregunta:
                raise ErrorMate("el contrato de conversación requiere 'preguntar'", linea,
                                familia="contrato")
            estado_previo = self.charlas.get(charla)
            contrato.pasar(self.charlas, charla, "pregunta", rem, dest, msg, linea)
        aviso = msg.tipo == AL_FALLAR  # no es un mensaje: es el aviso de que uno falló
        # En la traza cada mensaje lleva su número, y lo que pasa mientras un agente
        # atiende (lo que él pregunta) va con sangría debajo.
        numero, hondo = None, len(self.atendiendo)
        if not aviso:
            self.cuenta["preguntar" if pregunta else "enviar"] += 1
            numero = self.cuenta["preguntar"] + self.cuenta["enviar"]
        de = rem.nombre if rem else "(programa)"
        conversacion, respuesta_a = sobre or (self.en_conversacion(), None)
        # En una prueba la traza numera desde 1, igual que mensajes_enviados().
        numero0, conversacion0 = (
            self.desde if self.en_prueba or self.viajes is not None else (0, 0))
        # En un ensayo, lo que se mandó ANTES de la pregunta (una conversación más vieja)
        # y llega ahora no es de este caso: ni se cuenta, ni se muestra, ni gasta número.
        viejo = self.viajes is not None and conversacion <= conversacion0
        if viejo and not aviso:
            numero0 += 1
            self.desde = (numero0, conversacion0)
        traza = self.traza and not viejo
        visto = numero - numero0 if numero is not None else None
        if self.viajes is not None and visto is not None and not viejo:
            # (lo de antes que se entrega intercalado corre la cuenta: 'en respuesta al N'
            # tiene que decir el número con que ese mensaje se mostró)
            self.vistos[numero] = visto
        if self.en_prueba and not aviso:
            self.historial.append(
                (numero, de, dest.nombre, msg, pregunta, conversacion, respuesta_a))
        if self.viajes is not None and not aviso and not viejo:
            self.viajes.append((msg.tipo, de, dest.nombre,
                                rem.decl[2] if rem else de, dest.decl[2]))
        # A un agente de otro programa no se le entrega acá: el mensaje sale por el buzón
        # (salvo que una prueba le haya puesto un 'simular': ahí se atiende en el momento).
        al_buzon = dest.ajeno is not None and not aviso \
            and not isinstance(dest.manejadores.get(msg.tipo), tuple)
        if traza and aviso:
            self.trazar(f"{dest.nombre} se entera de que {self.con_programa(rem)} no pudo "
                        f"atender {msg.campos['mensaje'].tipo}: "
                        + (texto_ajeno(msg.campos['motivo'], MAX_LARGO)
                           if rem is not None and rem.ajeno is not None
                           else str(msg.campos['motivo'])), None, hondo)
        elif traza:
            flecha = "pregunta a" if pregunta else "→"
            # El sobre se anota en los renglones sin sangría: lo de más adentro es de la
            # misma conversación que el renglón que lo contiene.
            anotado = ""
            if not hondo:
                anotado = f"   (conversación {conversacion - conversacion0}"
                if al_buzon:
                    anotado += (", a otro negocio: " if dest.socio is not None
                                else ", al buzón: ") + (
                        "sale al terminar" if self.buzon is not None else
                        "en una prueba no se escribe" if self.probando else
                        "acá no se escribe")
                elif numero in self.id_de_buzon:
                    anotado += ", del buzón"
                anotado += (
                    f", en respuesta al {self.vistos.get(respuesta_a, respuesta_a - numero0)})"
                    if respuesta_a else ")")
            escrito = formato(msg)
            if numero in self.id_de_buzon or (rem is not None and rem.ajeno is not None) \
                    or dest.socio is not None:
                # (vino de otro programa o de otro negocio, o va a otro negocio y puede
                # repetir lo que vino: lo que no se ve, escapado)
                escrito = texto_ajeno(escrito, MAX_LARGO)
            self.trazar(f"{self.con_programa(rem)} {flecha} {self.con_programa(dest)}: "
                        f"{escrito}{anotado}", visto, hondo)
        if al_buzon:
            self.sale_al_buzon(rem, dest, msg, conversacion, respuesta_a)
            return None
        afuera, self.conversacion = self.conversacion, conversacion
        try:
            respondio, valor = self.atender(rem, dest, msg, pregunta, linea)
        except (ErrorMate, KeyboardInterrupt) as e:
            if charla is not None:
                if getattr(e, "sin_respuesta", None) is dest:
                    try:
                        contrato.pasar(self.charlas, charla, "sin_respuesta", dest, rem, msg, linea)
                    except ErrorMate:
                        self.reponer_charla(charla, estado_previo)
                        raise
                else:
                    self.reponer_charla(charla, estado_previo)
            if isinstance(e, KeyboardInterrupt):
                raise
            self.cuenta["fallaron"] += 1
            self.anotar_falla(dest, e, msg)
            if traza and getattr(e, "sin_respuesta", None) is dest:
                self.trazar(f"{dest.nombre} sin respuesta: terminó de atender {msg.tipo} sin "
                            "llegar a un 'responder'", visto, hondo)
            elif traza:
                donde = " en su 'al fallar'" if aviso else ""
                self.trazar(f"{dest.nombre} falló{donde}: {e.mensaje}", visto, hondo)
            raise
        finally:
            self.conversacion = afuera
        if pregunta:
            if self.viajes is not None and isinstance(valor, Registro) and not viejo:
                self.viajes.append((valor.tipo, dest.nombre, de, dest.decl[2],
                                    rem.decl[2] if rem else de))
            if traza:
                self.trazar(f"{dest.nombre} responde a {de}: {formato(valor, False)}",
                            visto, hondo)
            return valor
        if respondio and rem is not None:
            self.cola.append((dest, rem, valor, (conversacion, numero)))
        elif respondio and traza and numero in self.id_de_buzon:
            # Llegó por el buzón y no lo mandó un agente: tampoco hay quién la reciba.
            self.trazar(f"la respuesta de {dest.nombre} se descartó (el mensaje llegó de "
                        "otro programa y no lo mandó un agente: para recibirla, que lo "
                        f"envíe un agente de ese programa): {formato(valor, False)}",
                        visto, hondo)
        elif respondio and traza:
            # Lo mandó el programa con 'enviar': no hay quién reciba la respuesta.
            self.trazar(f"la respuesta de {dest.nombre} se descartó (para recibirla, usá "
                        f"'preguntar' en vez de 'enviar'): {formato(valor, False)}",
                        visto, hondo)
        return None

    @staticmethod
    def con_programa(agente):
        """El nombre para la traza: 'Deposito (deposito.mate)' si es de otro programa."""
        if agente is None:
            return "(programa)"
        return f"{agente.nombre} ({agente.ajeno})" if agente.ajeno else agente.nombre

    # ── el buzón entre programas (0.7) ──
    def para_el_buzon(self, msg, dest, linea=None):
        """El mensaje como va a viajar a otro programa (JSON). Un error claro si no puede
        ir: lleva un agente adentro, o pesa demasiado."""
        if lleva_agente(msg) is not None:
            raise ErrorMate("un mensaje para otro programa todavía no puede llevar un agente "
                            f"adentro ({msg.tipo} para {dest.nombre}): mandá su nombre, o "
                            "los datos que hagan falta", linea, familia="contrato")
        try:
            datos = self._a_json(msg)
            revisar_lo_de_afuera(datos)
            pesa = len(json.dumps(datos, ensure_ascii=False, allow_nan=False)
                       .encode("utf-8", "replace"))
        except NoSeEntrega as e:
            raise ErrorMate(f"{msg.tipo} no puede ir a otro programa: {e}", linea,
                            familia="contrato")
        except (ValueError, RecursionError):
            raise ErrorMate(f"{msg.tipo} trae un número que no se puede pasar a JSON, y así "
                            "no puede ir a otro programa", linea, familia="contrato")
        if pesa > MAX_MENSAJE_AL_BUZON:
            raise ErrorMate(f"el mensaje para {dest.nombre} pesa más de 1 MB: mandá menos "
                            "datos por vez", linea, clase="falla", familia="contrato")
        if dest.socio is not None:  # (entre negocios los topes son mucho más chicos)
            problema = no_entra_de_socio(datos)
            if problema:
                raise ErrorMate(f"{msg.tipo} no puede ir a {dest.nombre} (otro negocio): "
                                f"{problema}. " + (
                                    "Sacalos antes de mandarlo" if problema is TEXTO_QUE_NO_SE_VE
                                    else "Mandá menos datos por vez"), linea,
                                clase="falla", familia="contrato")
        return datos

    def va_a_un_socio(self, dest, msg):
        """A un socio se le puede mandar cualquier mensaje declarado (también uno declarado
        después del 'usar socio', como pasa en la consola): qué acepta lo decide él."""
        return dest.socio is not None and msg.tipo in self.mensajes

    def revisar_envio(self, dest, msg, linea):
        """Los controles de un 'enviar' a un agente de otro programa, en ese renglón."""
        if dest.solo_responde:
            otro = dest.ajeno if dest.ajeno.lower().endswith((".mate", ".mate.txt")) \
                else f"{dest.programa}.mate"
            raise ErrorMate(
                f"para mandarle a {dest.nombre} ({dest.ajeno}) algo que no sea la "
                f'contestación, agregá arriba: usar buzon "{otro}"', linea)
        if msg.tipo not in dest.manejadores and not self.va_a_un_socio(dest, msg):
            raise ErrorMate(f"{dest.nombre} no sabe recibir '{msg.tipo}'", linea,
                            familia="agente")
        contrato = self.contrato_conversacion
        if contrato and msg.tipo in contrato.tipos:
            raise ErrorMate(EN_EL_CONTRATO.format(n=msg.tipo), linea, familia="contrato")
        self.para_el_buzon(msg, dest, linea)

    def sale_al_buzon(self, rem, dest, msg, conversacion, respuesta_a):
        """Le tocó salir a un mensaje para otro programa: queda anotado "por salir". Sale
        de verdad cuando el programa termina y guarda (ver cerrar_memoria, en 'correr')."""
        buzon = self.buzon
        if buzon is None:  # 'probar', 'ensayar' o la consola: no se escribe ningún buzón
            if self.en_consola:  # (acá los avisos salen por donde sale todo lo demás)
                self.salida(
                    f"aviso: desde la consola no sale nada para otro programa: el mensaje "
                    f"para {dest.nombre} ({dest.ajeno}) no se escribió en ningún buzón. "
                    "Para mandarlo de verdad, ponelo en un archivo y usá 'correr'")
            return
        if dest.socio is not None:
            # A otro negocio: queda como borrador; el número y la firma se le ponen al
            # guardar. La conversación y el "en respuesta a" solo se anotan si son de ESE
            # socio: nunca se le cuenta a un socio un id de otro lado.
            socios = buzon.socios
            mismo = self.charla_de_socio.get(conversacion) == dest.socio
            socios.sale(dest.socio, socios.borrador(
                rem.nombre if rem else SUELTO_EN_EL_BUZON, self.para_el_buzon(msg, dest),
                self.charla_de_buzon.get(conversacion) if mismo else None,
                self.id_de_buzon.get(respuesta_a) if mismo else None))
            return
        if dest.carpeta_buzon is None:
            self.avisar_una_vez(("sin remitente", dest.programa), (
                f"no encontré a quién contestarle ({dest.programa}): en esta carpeta no "
                f"está {dest.programa}.mate ni la carpeta de su buzón"))
            return
        buzon.sale(dest.carpeta_buzon, buzon.sobre(
            rem.nombre if rem else SUELTO_EN_EL_BUZON, dest.programa, dest.nombre,
            self.para_el_buzon(msg, dest), self.charla_de_buzon.get(conversacion),
            self.id_de_buzon.get(respuesta_a)))

    def sacar_lo_del_buzon(self):
        """Al cerrar la corrida, también si se cortó (un error, o Ctrl+C en un mostrador):
        lo que un agente ya dejó para otro programa y seguía en la cola queda "por salir",
        para guardarse junto con el estado de ese agente. Si no, quedaría guardado que
        Ventas anotó el pedido y a Depósito no le llegaría nunca. (Lo que encoló un agente
        que falló, o al que cortaron a mitad de un mensaje, ya no está en la cola.)"""
        if self.buzon is None:
            return
        queda = deque()
        for entrada in list(self.cola):
            rem, dest, msg, sobre = entrada
            if dest.ajeno is None or msg.tipo == AL_FALLAR \
                    or isinstance(dest.manejadores.get(msg.tipo), tuple):
                queda.append(entrada)
                continue
            try:
                self.entregar(rem, dest, msg, pregunta=False, sobre=sobre)
            except ErrorMate:  # (se pasó del tope de mensajes: queda sin salir, y se avisa)
                queda.append(entrada)
        self.cola = queda

    def remitente_de(self, de):
        """El agente de otro programa que mandó un sobre. Si este programa tiene el 'usar
        buzon' de ese otro, es ese mismo agente; si no, uno que solo sirve para contestarle."""
        nombre, programa = de["agente"], de["programa"]
        declarado = self.ajenos.get(nombre)
        if declarado is not None and declarado.programa.casefold() == programa.casefold():
            return declarado
        clave = (programa.casefold(), nombre)
        if clave not in self.remitentes:
            archivo, carpeta = self.buzon.buscar(programa)
            self.remitentes[clave] = self.agente_de_otro(
                nombre, archivo or programa, programa, carpeta, solo_responde=True)
        return self.remitentes[clave]

    def atender_buzon(self):
        """Al terminar los renglones del programa (solo con 'correr'): atiende lo que otros
        programas le dejaron en el buzón. Una sola pasada, en orden de envío; lo que llegue
        mientras tanto queda para la próxima corrida."""
        if self.buzon is None:
            return
        self.buzon.atendio = True
        archivos = self.buzon.abrir()
        if archivos:
            self.buzon.enviados = set(self.buzon.leer_correo()["enviados"])
        for ruta in archivos:
            self.atender_sobre(ruta)
        self.atender_socios()

    # ── los socios: lo que llega de otro negocio (0.8) ──
    def atender_socios(self):
        """Después del buzón local: trae lo que los socios dejaron en la carpeta compartida
        (lo que trae su firma en regla) y le pregunta al dueño, mensaje por mensaje, si lo
        entrega. Nada de otro negocio llega a un agente sin ese si."""
        buzon = self.buzon
        socios = buzon.socios
        if socios is None or not socios.listos:
            return
        if not socios.hay_algo():
            socios.miro = True  # (se miró, y no había nada)
            return
        puede = buzon.se_puede_guardar(1)
        if puede is not True:
            if puede is None:
                self.avisar(f"otra ventana de {buzon.archivo} tiene tomado el candado de la "
                            "memoria: lo que mandaron los socios queda para la próxima "
                            "corrida")
            return
        if buzon.cambio_la_memoria()[0]:
            self.avisar(f"otra ventana de {buzon.archivo} guardó cambios mientras esta "
                        "estaba abierta; lo que mandaron los socios queda para la próxima "
                        "corrida")
            return
        socios.recargar()
        for socio in sorted(socios.listos):
            for ruta, crudo, sobre in socios.mirar(socio):
                self.traer_de_socio(socio, ruta, crudo, sobre)
        quedan = 0
        for socio, numero, ruta in socios.pendientes():
            quedan += not self.resolver_pendiente(socio, numero, ruta)
        socios.miro = True
        if quedan:
            self.avisar(
                f"{cuantos_mensajes(quedan)} de socios "
                f"{'espera' if quedan == 1 else 'esperan'} tu si: no se "
                f"{'entregó' if quedan == 1 else 'entregaron'} a ningún agente. Para verlos:"
                f"  {orden_para_esta_carpeta()} buzon {para_pegar(buzon.archivo)}   Para "
                f"contestar, corré {buzon.archivo} de nuevo")

    def revisar_de_socio(self, socio, sobre, al_entregar=False):
        """Un sobre de ese socio, ya con la firma comprobada: lo que se le va a mostrar al
        dueño y a entregar. Se valida ANTES de preguntar (el 'acepta' de ese socio, el
        contrato de este programa y los topes entre negocios): el dueño aprueba lo mismo
        que recibe el agente, entero. NoSeEntrega si no va; su .codigo es el motivo que
        vuelve al socio (de la lista cerrada), o None si no se le contesta.
        'de' y 'para' del sobre no deciden nada: el remitente es el socio, y el
        destinatario es el único agente de acá que recibe ese tipo."""
        socios = self.buzon.socios

        def no(texto, codigo=None, campo=None):
            e = NoSeEntrega(texto)
            e.codigo, e.campo = codigo, campo
            return e

        try:
            revisar_sobre(sobre, hasta=VERSION_DE_SOBRE_DE_SOCIO)
        except NoSeEntrega as e:
            raise no(f"lo que mandó {socio}: {e}")
        falla, mensaje = sobre["clase"] == "falla", sobre["mensaje"]
        if not (isinstance(mensaje, dict) and set(mensaje) == {"tipo", "campos"}
                and isinstance(mensaje["tipo"], str) and isinstance(mensaje["campos"], dict)):
            raise no(f"lo que mandó {socio} no trae un mensaje con la forma de siempre")
        tipo = mensaje["tipo"]
        visto = texto_ajeno(tipo, 60)
        problema = no_entra_de_socio(mensaje)
        if problema:
            raise no(f"{visto} de {socio}: {problema}", None if falla else "contrato")
        if falla:
            # Solo vale el aviso de falla de un mensaje que este programa le mandó de
            # verdad a ESE socio, y uno solo por mensaje.
            numero = sobre["socio"]["numero"]
            anotado = socios.estado[socio]["ids"].get(sobre.get("en_respuesta_a"))
            if anotado is None or (len(anotado) == 2) == al_entregar \
                    or (len(anotado) > 2 and anotado[2] != numero):
                raise no(f"el aviso de {socio} de que no pudo con {visto} nombra un mensaje "
                         "que este programa no le mandó (o del que ya avisó): no lo tomo")
            codigo = sobre.get("motivo")
            motivo = MOTIVOS_DE_SOCIO.get(codigo if isinstance(codigo, str) else "",
                                          "motivo desconocido")
            campo = sobre.get("campo")
            if codigo == "contrato" and isinstance(campo, str) \
                    and _NOMBRE_DE_CAMPO.fullmatch(campo):
                motivo += f" (campo '{campo}')"
            msg = None
            if huella_de_mensaje(mensaje) == anotado[0]:  # (es lo mismo que yo mandé)
                try:
                    msg = self.mensaje_de_afuera(mensaje)
                except (ErrorMate, TypeError, KeyError):
                    msg = None
            dest = self.agentes.get(anotado[1]) if isinstance(anotado[1], str) else None
            if msg is None or dest is None or AL_FALLAR not in dest.manejadores:
                dest = None  # (no hay 'al fallar' que lo atienda: es solo un aviso)
            return {"falla": True, "tipo": visto, "msg": msg, "dest": dest,
                    "motivo": motivo}
        if tipo not in socios.declarados.get(socio, ()):
            raise no(f"no acepto '{visto}' de {socio} (no está en el 'acepta' de ese "
                     "socio)", "no_acepto")
        quienes = [a for a in self.agentes.values()
                   if any(m[1] == tipo for m in a.decl[4])]
        if len(quienes) != 1:
            raise no(f"{visto} de {socio}: acá no hay un único agente que lo reciba",
                     "no_acepto")
        try:
            msg = self.mensaje_de_afuera(mensaje)
        except (ErrorMate, TypeError, KeyError) as e:
            dicho = getattr(e, "mensaje", "no se entiende")
            campo = next((c for c, _, _ in self.mensajes.get(tipo, ())
                          if f"{tipo}.{c} " in dicho or f"'{c}'" in dicho), None)
            raise no(f"{visto} de {socio} no cumple el contrato: {dicho}", "contrato", campo)
        return {"falla": False, "tipo": tipo, "msg": msg, "dest": quienes[0]}

    def falla_a_socio(self, socio, sobre, codigo, campo=None, de_agente=None):
        """Le avisa a ese socio que su mensaje no se atendió. Viaja firmado, y el motivo es
        un CÓDIGO de una lista cerrada: nunca el texto de un error de este programa. No se
        contesta una falla con otra, ni lo que no pasó la firma (eso ni llega acá)."""
        if codigo is None or not isinstance(sobre, dict) or sobre.get("clase") != "mensaje":
            return
        socios = self.buzon.socios
        mensaje = sobre.get("mensaje")
        if not isinstance(mensaje, dict) or no_entra_de_socio(mensaje) is not None:
            mensaje = {"tipo": "?", "campos": {}}  # (no se le devuelve lo que no entra)
        socios.sale(socio, socios.borrador(
            de_agente or SUELTO_EN_EL_BUZON, mensaje, None, sobre["id"], falla=codigo,
            campo=campo if isinstance(campo, str) and _NOMBRE_DE_CAMPO.fullmatch(campo)
            else None))

    def traer_de_socio(self, socio, ruta, crudo, sobre):
        """Un sobre nuevo de ese socio, con la firma en regla: si además cumple lo que este
        programa le acepta, queda en 'pendientes' esperando el si. Si no, se rechaza ya (y
        ahí sí se le avisa: se autenticó)."""
        socios = self.buzon.socios
        try:
            que = self.revisar_de_socio(socio, sobre)
        except NoSeEntrega as e:
            socios.visto(socio, sobre)
            socios.rechazar(socio, crudo, str(e))
            socios.por_borrar.append(ruta)
            self.falla_a_socio(socio, sobre, e.codigo, e.campo)
            if self.traza:
                self.trazar(f"socios: no se entregó {texto_ajeno(str(e), LARGO_DE_MOTIVO)}")
            return
        if que["falla"] and que["dest"] is None:
            # Un aviso de falla que ningún 'al fallar' atiende no toca nada: se muestra.
            socios.visto(socio, sobre)
            socios.anotar_falla(socio, sobre["en_respuesta_a"], sobre["socio"]["numero"])
            socios.por_borrar.append(ruta)
            self.avisar(f"tu socio {socio} avisa que no atendió {que['tipo']}: "
                        f"{que['motivo']}")
            return
        if socios.a_pendientes(socio, sobre, crudo, ruta) and que["falla"]:
            socios.anotar_falla(socio, sobre["en_respuesta_a"], sobre["socio"]["numero"])

    def preguntar_al_dueno(self, socio, sobre, que):
        """Muestra lo que mandó el socio, ENTERO y tal como lo va a recibir el agente, y
        pregunta. Devuelve "si", "no" o "despues": solo "si" entrega; con Enter, con otra
        cosa, sin teclado o con Ctrl+C queda pendiente. No hay "si a todos"."""
        socios = self.buzon.socios
        cuando = sobre.get("cuando")
        try:
            cuando = f"{datetime.datetime.fromisoformat(cuando):%d/%m/%Y %H:%M}"
        except (TypeError, ValueError):
            cuando = texto_ajeno(cuando, 30) if isinstance(cuando, str) else "sin fecha"
        quien = f"{socio} (control {socios.control(socio)})"
        if que["falla"]:
            self.salida(f"{quien} avisa que NO atendió {valor_ajeno(que['msg'])}")
            self.salida(f"  Motivo: {que['motivo']}.")
        else:
            self.salida(f"{quien} te manda {valor_ajeno(que['msg'])}")
        self.salida(f"  escrito el {cuando} según el reloj de tu socio. Lo recibe: "
                    f"{que['dest'].nombre}.")
        if self.sin_dueno:
            return "despues"
        try:
            dicho = self.entrada("¿Lo entrego? (si / no / despues)")
        except (EOFError, OSError, UnicodeError, KeyboardInterrupt):
            self.sin_dueno = True  # no hay quién conteste: lo que falta queda pendiente
            self.salida("  (nadie contestó: queda pendiente)")
            return "despues"
        dicho = dicho.replace("\ufeff", "").strip().lower()
        return "si" if dicho in ("si", "sí") else "no" if dicho == "no" else "despues"

    def resolver_pendiente(self, socio, numero, ruta):
        """Un mensaje de un socio que espera el si. Devuelve False si sigue esperando."""
        socios = self.buzon.socios
        try:
            sobre = socios.releer(socio, numero, ruta)
        except OSError:
            return False  # ahora no se puede abrir: otra vez será
        except NoSeEntrega as e:
            # Lo cambiaron en 'pendientes' (o se rompió): no es lo que firmó el socio.
            socios.descartar(socio, numero, ruta, (
                f"el mensaje {numero} de {socio} que esperaba tu si: {e}. No se entrega"))
            return True
        try:
            que = self.revisar_de_socio(socio, sobre, al_entregar=True)
        except NoSeEntrega as e:
            socios.descartar(socio, numero, ruta, str(e))
            self.falla_a_socio(socio, sobre, e.codigo, e.campo)
            return True
        if que["dest"] is None:
            socios.resuelto(socio, numero, ruta, entregado=False)
            self.avisar(f"tu socio {socio} avisa que no atendió {que['tipo']}: "
                        f"{que['motivo']}")
            return True
        dicho = self.preguntar_al_dueno(socio, sobre, que)
        if dicho == "despues":
            return False
        dest, msg = que["dest"], que["msg"]
        if dicho == "no":
            socios.descartar(socio, numero, ruta, (
                f"{que['tipo']} de {socio} (el número {numero}): el dueño lo descartó"),
                avisar=False)
            self.falla_a_socio(socio, sobre, "descartado", de_agente=dest.nombre)
            self.salida("  No se entregó: queda en rechazados"
                        + ("." if que["falla"] else ", y tu socio recibe el aviso."))
            return True
        rem = self.ajenos[socio]
        self.conversaciones += 1
        conversacion = self.conversaciones
        # (la conversación solo sigue una que este programa empezó con ESE socio)
        suya = sobre.get("conversacion")
        self.charla_de_buzon[conversacion] = suya \
            if suya in socios.estado[socio]["ids"] else sobre["id"]
        self.charla_de_socio[conversacion] = socio
        if que["falla"]:
            msg = Registro(AL_FALLAR, {"motivo": que["motivo"], "mensaje": msg,
                                       "destino": rem})
        else:
            self.id_de_buzon[self.cuenta["enviar"] + self.cuenta["preguntar"] + 1] \
                = sobre["id"]
        esperado = self.cuenta["enviar"] + self.cuenta["preguntar"]
        try:
            self.entregar(rem, dest, msg, pregunta=False, sobre=(conversacion, None))
        except ErrorMate as e:
            if self.cuenta["enviar"] + self.cuenta["preguntar"] == esperado:
                self.id_de_buzon.pop(esperado + 1, None)
            if e.clase != "limite":
                self.anotar_error_de_agente(dest, msg, e)
            # (el estado del agente volvió atrás; no se reintenta: va a rechazados, y al
            # socio le vuelve el código, no el texto del error)
            socios.descartar(socio, numero, ruta, (
                f"{que['tipo']} de {socio}: {dest.nombre} falló al atenderlo: {e.mensaje}"))
            self.falla_a_socio(socio, sobre, "fallo", de_agente=dest.nombre)
            if e.clase == "limite":
                raise
            return True
        socios.resuelto(socio, numero, ruta)
        self.vaciar_cola()  # lo que el agente contestó o mandó a raíz de este mensaje
        return True

    def no_entregar(self, ruta, motivo, sobre=None):
        """Un sobre que no se entrega: va a 'rechazados' con su motivo (cuando el programa
        termina y guarda), se avisa y, si era un mensaje de alguien que se reconoce, le
        vuelve el aviso de la falla. Nunca se contesta una falla con otra falla."""
        buzon = self.buzon
        motivo = texto_ajeno(motivo, 2 * LARGO_DE_MOTIVO)  # (trae texto de afuera)
        buzon.rechazos.append((ruta, motivo))
        buzon.no_entregados += 1
        if self.traza:
            self.trazar(f"buzón: no se entregó {motivo}")
        self.avisar(f"no entregué un mensaje del buzón: {motivo}. Quedó en "
                    f"{buzon.donde_van_los_rechazados()}")
        if sobre is None or sobre["clase"] != "mensaje":
            return
        de, para = sobre["de"], sobre["para"]
        carpeta = buzon.buscar(de["programa"])[1]
        if carpeta is None:
            self.avisar_una_vez(("sin remitente", de["programa"]), (
                f"no encontré a quién contestarle ({de['programa']}): en esta carpeta no "
                f"está {de['programa']}.mate ni la carpeta de su buzón"))
            return
        buzon.sale(carpeta, buzon.sobre(
            para["agente"], de["programa"], de["agente"], sobre["mensaje"],
            sobre.get("conversacion") or sobre["id"], sobre["id"], falla=motivo,
            id=buzon.id_de_falla(sobre["id"], ruta)))

    def mensaje_de_afuera(self, datos):
        """El mensaje de un sobre, armado y validado con el contrato de ESTE programa (lo
        mismo que de_json(texto, "Tipo")). ErrorMate si no lo cumple."""
        if datos["tipo"] not in self.mensajes:
            raise ErrorMate(f"acá no existe el mensaje '{datos['tipo']}'", familia="contrato")
        try:
            return self.amoldar(self._de_json(datos["campos"]), datos["tipo"])
        except RecursionError:
            raise ErrorMate("trae demasiadas cosas una adentro de otra", familia="contrato")

    def atender_sobre(self, ruta):
        """Atiende un archivo del buzón: lo valida, se lo entrega a su agente y anota que
        ya está atendido. Lo que no se puede entregar va a 'rechazados'."""
        buzon = self.buzon
        try:
            sobre = leer_sobre(ruta)
        except OSError:
            return  # ahora no se puede abrir (un antivirus, otra ventana): otra vez será
        except NoSeEntrega as e:
            self.no_entregar(ruta, f"el archivo {os.path.basename(ruta)}: {e}")
            return
        de, para, falla = sobre["de"], sobre["para"], sobre["clase"] == "falla"
        # (el motivo de una falla viene de afuera: va en un renglón, recortado y limpio)
        motivo = texto_ajeno(en_un_renglon(sobre["motivo"], LARGO_DE_MOTIVO),
                             LARGO_DE_MOTIVO + 3) if falla else None
        origen = texto_ajeno(buzon.visible(de["programa"]), 160)
        tipo = "un mensaje"
        if isinstance(sobre["mensaje"], dict) and isinstance(sobre["mensaje"].get("tipo"), str):
            tipo = texto_ajeno(en_un_renglon(sobre["mensaje"]["tipo"], 60), 63) or tipo
        de_quien, para_quien = texto_ajeno(de["agente"], 200), texto_ajeno(para["agente"], 200)
        que = (f"el aviso de {de_quien} ({origen}) de que no pudo atender {tipo}"
               if falla else f"{tipo} de {de_quien} ({origen})") + f" para {para_quien}"
        if para["programa"].casefold() != buzon.programa.casefold():
            return self.no_entregar(ruta, f"{que}: es para otro programa "
                                          f"({para['programa']}), no para {buzon.archivo}")
        if de["programa"].casefold() == buzon.programa.casefold():
            return self.no_entregar(ruta, f"{que}: dice venir de este mismo programa, y un "
                                          "programa no se manda mensajes por el buzón a sí "
                                          "mismo")
        # (0.8, P161) Solo se entrega lo que viene de un programa que este conoce. A un
        # desconocido no se le contesta: el aviso se escribiría en la carpeta de un nombre
        # que eligió quien dejó el sobre.
        conocido = buzon.conoce(de, self.ajenos, falla)
        if conocido is not True:
            return self.no_entregar(ruta, f"{que}: {conocido}")
        clave = f"{de['programa'].casefold()}/{sobre['id']}"
        if clave in buzon.ya_recibidos or clave in buzon.recibidos:
            buzon.atendidos.append(ruta)  # ya se había atendido: se borra sin entregar
            return None
        if falla and f"{de['programa'].casefold()}/{sobre.get('en_respuesta_a')}" \
                not in buzon.enviados:
            # Un aviso de falla solo vale si nombra un mensaje que este programa le mandó
            # de verdad a ese programa: si no, cualquiera inventa uno y repone stock.
            return self.no_entregar(ruta, f"{que}: nombra un mensaje que este programa no "
                                          f"le mandó a {origen} (un aviso de falla solo "
                                          "vale por un mensaje enviado de verdad)")
        # (lo que mandó el programa suelto no tiene a quién contestarle, como siempre)
        rem = None if not falla and de["agente"] == SUELTO_EN_EL_BUZON \
            else self.remitente_de(de)
        dest = self.agentes.get(para["agente"]) or next(
            (a for a in self.vivos if a.nombre == para["agente"]), None)
        suelto = falla and para["agente"] == SUELTO_EN_EL_BUZON
        if dest is None and not suelto:
            return self.no_entregar(ruta, f"{que}: acá no hay ningún agente llamado "
                                          f"{para['agente']}", sobre)
        try:
            msg = self.mensaje_de_afuera(sobre["mensaje"])
        except (ErrorMate, TypeError, KeyError) as e:
            if not falla:
                return self.no_entregar(ruta, f"{que} no cumple el contrato: "
                                              f"{getattr(e, 'mensaje', 'no se entiende')}",
                                        sobre)
            msg = None  # (el mensaje original ya no pasa el contrato: se avisa igual)
        if not falla and msg.tipo not in dest.manejadores:
            return self.no_entregar(ruta, f"{que}: {dest.nombre} no sabe recibir "
                                          f"'{msg.tipo}'", sobre)
        self.conversaciones += 1
        conversacion = self.conversaciones
        self.charla_de_buzon[conversacion] = sobre.get("conversacion") or sobre["id"]
        if falla and (suelto or msg is None or AL_FALLAR not in dest.manejadores):
            self.avisar(f"{rem.nombre} ({origen}) no pudo atender {tipo}"
                        + ("" if suelto else f" de {dest.nombre}") + f": {motivo}")
        else:
            if falla:
                msg = Registro(AL_FALLAR, {"motivo": motivo, "mensaje": msg,
                                           "destino": rem})
            else:
                self.id_de_buzon[self.cuenta["enviar"] + self.cuenta["preguntar"] + 1] \
                    = sobre["id"]
            esperado = self.cuenta["enviar"] + self.cuenta["preguntar"]
            try:
                self.entregar(rem, dest, msg, pregunta=False, sobre=(conversacion, None))
            except ErrorMate as e:
                if self.cuenta["enviar"] + self.cuenta["preguntar"] == esperado:
                    self.id_de_buzon.pop(esperado + 1, None)  # (ni llegó a tener número)
                # Como siempre que un agente falla, su estado volvió atrás. El mensaje no
                # se reintenta para siempre: va a 'rechazados' con el motivo.
                if e.clase != "limite":
                    self.anotar_error_de_agente(dest, msg, e)
                self.no_entregar(ruta, f"{que}: {dest.nombre} falló al atenderlo: "
                                       f"{e.mensaje}", sobre)
                if e.clase == "limite":  # el freno corta todo el programa, como siempre
                    raise
                return None
        buzon.recibidos.append(clave)
        buzon.atendidos.append(ruta)
        buzon.atendi[origen] = buzon.atendi.get(origen, 0) + 1
        self.vaciar_cola()  # lo que el agente contestó o mandó a raíz de este mensaje
        return None

    def reponer_charla(self, charla, estado):
        if estado is None:
            self.charlas.pop(charla, None)
        else:
            self.charlas[charla] = estado

    def trazar(self, texto, numero=None, hondo=0):
        """Un renglón de la traza: '  ·  3.    Vendedor responde a Comprador: ...'."""
        marca = f"{numero:>2}." if numero is not None else "   "
        (self.anotar or self.salida)(f"  · {marca} {'   ' * hondo}{texto}")

    def atender(self, rem, dest, msg, pregunta, linea):
        """El agente atiende el mensaje. Devuelve (si respondió, qué respondió)."""
        aviso = msg.tipo == AL_FALLAR
        if msg.tipo not in dest.manejadores:
            raise ErrorMate(f"{dest.nombre} no sabe recibir '{msg.tipo}'", familia="agente")
        if dest.ocupado and dest.env is None:
            raise ErrorMate(f"{dest.nombre} todavía está armando su estado inicial y no "
                            "puede recibir mensajes")
        if dest.ocupado:
            raise self.ciclo(dest, linea)
        if dest.env is None:
            self.instanciar(dest)
        # Un 'al recibir' simulado en una prueba corre con las variables de esa prueba
        # a la vista (no con el estado del agente).
        renglon, var, cuerpo, *de_la_prueba = dest.manejadores[msg.tipo]
        env = Entorno(de_la_prueba[0] if de_la_prueba else dest.env, borde=True)
        if var:  # (el aviso de 'al fallar' llega como un mapa común)
            env.definir(var, dict(msg.campos) if aviso else msg, origen="mensaje")
        previo, dest.ocupado = self.contexto, True
        self.contexto = (dest, rem, msg.tipo, env.serie, msg)
        # El ID de la conversación: lo fija una pregunta del contrato, y lo heredan las
        # preguntas que se hacen para atenderla (aunque no estén en el contrato). Lo que
        # sale de la cola (un 'enviar', un aviso de falla) no viene de ninguna cadena.
        origen_previo = self.origen_de_charla
        contrato = self.contrato_conversacion
        if contrato and msg.tipo in contrato.preguntas:
            self.origen_de_charla = msg
        elif not pregunta or previo is None:
            self.origen_de_charla = None
        respondio, valor = False, None
        # Si falla, el agente vuelve a como estaba antes de recibir este mensaje.
        estado_previo = {k: list(v) for k, v in dest.env.vars.items()}
        lecciones_previas = dest.lecciones
        en_cola, llamadas, nacidos = len(self.cola), self.llamadas, len(self.vivos)
        self.llamadas = []
        self.atendiendo.append((dest, linea))
        try:
            try:
                senal = self.armar_bloque(cuerpo, False)(env)
                if type(senal) is not tuple:  # (un 'devolver' termina de atender y listo)
                    self.fuera_de_lugar(senal)
            except _Respuesta as r:
                respondio, valor, renglon_respuesta = True, r.valor, r.linea
            except _Retorno:
                pass
            if aviso and respondio:
                raise ErrorMate(SIN_A_QUIEN, renglon_respuesta)
            # Responder mal (o no responder) también es una falla del que atiende.
            esperado = self.responde.get(msg.tipo)
            if respondio and esperado and not self.cumple(valor, esperado):
                raise ErrorMate(
                    f"{dest.nombre} respondió {self.no_cumple(valor, esperado)} a "
                    f"'{msg.tipo}', y el contrato dice que a {msg.tipo} se le responde "
                    f"{esperado}", renglon_respuesta, familia="contrato")
            contrato = self.contrato_conversacion
            if pregunta and respondio and contrato and msg.tipo in contrato.preguntas:
                charla = contrato.identificador(msg, linea)
                contrato.mismo_id(charla, valor, renglon_respuesta)
                contrato.pasar(self.charlas, charla, "respuesta", dest, rem, valor, renglon_respuesta)
            if pregunta and not respondio:
                mudo = ErrorMate(f"{dest.nombre} no respondió a '{msg.tipo}': el 'al recibir' "
                                 "terminó sin llegar a un 'responder'", familia="agente")
                mudo.sin_respuesta = dest  # (para la traza: no falló, se quedó callado)
                raise mudo
            if not pregunta and respondio and rem is not None:
                # (si lo mandó el programa, no hay a quién contestar)
                if not isinstance(valor, Registro):
                    raise ErrorMate("a un 'enviar' solo se le responde con un mensaje",
                                    renglon_respuesta)
                if valor.tipo not in rem.manejadores and not rem.solo_responde \
                        and not self.va_a_un_socio(rem, valor):
                    raise ErrorMate(
                        f"{dest.nombre} respondió {valor.tipo} a {rem.nombre}, pero "
                        f"{rem.nombre} no tiene 'al recibir {valor.tipo}'", renglon_respuesta)
                if rem.ajeno is not None:  # la respuesta viaja a otro programa
                    self.para_el_buzon(valor, rem, renglon_respuesta)
        except ErrorMate as e:
            if pregunta:
                anotar_paso(e, ("pregunta", dest.nombre, rem.nombre if rem else None, linea))
            if not e.linea and not pregunta:
                e.renglon = renglon  # para señalar al menos el 'al recibir' que atendía
            dest.env.vars = estado_previo
            dest.lecciones = lecciones_previas
            # Las copias que creó atendiendo este mensaje tampoco quedan: nadie las tiene.
            self.vivos[nacidos:] = [a for a in self.vivos[nacidos:] if a.creador is not dest]
            nuevos = [self.cola.pop() for _ in range(len(self.cola) - en_cola)]
            self.cola.extend(m for m in reversed(nuevos) if m[0] is not dest)
            if e.clase == "asegurar":  # para quien le habló es una falla como cualquiera
                e.clase = "falla"
            raise
        except KeyboardInterrupt:
            # Cortado con Ctrl+C a mitad de un mensaje: lo que cambió atendiéndolo no queda
            # (si no, la memoria guardaría un estado a medio cambiar), y lo que dejó para
            # enviar tampoco sale.
            dest.env.vars = estado_previo
            dest.lecciones = lecciones_previas
            nuevos = [self.cola.pop() for _ in range(len(self.cola) - en_cola)]
            self.cola.extend(m for m in reversed(nuevos) if m[0] is not dest)
            raise
        finally:
            self.contexto, dest.ocupado, self.llamadas = previo, False, llamadas
            self.origen_de_charla = origen_previo
            self.atendiendo.pop()
        return respondio, valor

    def destino(self, dest):
        """Controla que eso sea un agente: a quién se le pregunta o se le simula algo."""
        if not isinstance(dest, Agente):
            pista = ""
            if isinstance(dest, list):
                pista = (". Se le pregunta a un agente por vez: recorré la lista con "
                         "'para agente en lista { ... }'")
            raise ErrorMate(f"el destino tiene que ser un agente, no {tipo_claro(dest)}"
                            + pista)
        return dest

    def destinos(self, dest):
        """A quiénes va un 'enviar': un agente, o una lista de agentes."""
        if isinstance(dest, Agente):
            return [dest]
        if not isinstance(dest, list):
            raise ErrorMate("el destino tiene que ser un agente o una lista de agentes, no "
                            + tipo_claro(dest))
        for i, x in enumerate(dest):
            if not isinstance(x, Agente):
                raise ErrorMate("en una lista de destinos tienen que ser todos agentes, y "
                                f"en la posición {i} hay {un(x)}")
        return dest

    def un_mensaje(self, msg):
        if not isinstance(msg, Registro):
            raise ErrorMate(f"solo se envían mensajes declarados, no {tipo_claro(msg)}")
        return msg

    # ── el programa, armado para correr (0.5) ──
    # Antes, cada vez que pasaba por un renglón, Mate volvía a preguntarse qué clase de
    # sentencia era (una cadena larga de 'si es esto, si es aquello'). Ahora cada sentencia
    # y cada valor se "arman" una sola vez: se convierten en una función de Python que ya
    # sabe qué tiene que hacer, y después solo se la llama. Hace lo mismo que antes, renglón
    # por renglón (mismos errores, mismo freno, misma traza), pero varias veces más rápido.
    #
    # Una sentencia armada recibe el entorno y devuelve nada... salvo que corte el camino:
    # (valor,) si fue un 'devolver', _ROMPER o _CONTINUAR. Así un 'devolver' no cuesta una
    # excepción de Python. Donde ya no hay quién reciba esa señal, se convierte en la
    # excepción de siempre (_Retorno, _Romper, _Continuar) y sigue el camino viejo.

    @staticmethod
    def fuera_de_lugar(senal):
        """Una señal que llegó hasta donde nadie la espera sigue como excepción."""
        if senal is None:
            return
        if senal is _ROMPER:
            raise _Romper()
        if senal is _CONTINUAR:
            raise _Continuar()
        raise _Retorno(senal[0])

    def bloque(self, cuerpo, env, nuevo=True):
        """Corre esas sentencias. (Lo que ya está armado no pasa por acá: se llama solo.)"""
        self.fuera_de_lugar(self.armar_bloque(cuerpo, nuevo)(env))

    def armar_bloque(self, cuerpo, nuevo=True):
        """El bloque listo para correr; se arma la primera vez y queda guardado."""
        clave = (id(cuerpo), nuevo)
        listo = self._armados.get(clave)
        if listo is None:  # (se guarda también el cuerpo: así su id no se repite)
            listo = self._armados[clave] = (self._bloque(cuerpo, nuevo), cuerpo)
        return listo[0]

    def ejecutar(self, s, env, vale_suelto=False):
        clave = (id(s), vale_suelto)
        listo = self._armados.get(clave)
        if listo is None:
            listo = self._armados[clave] = (self._paso(s, vale_suelto), s)
        self.fuera_de_lugar(listo[0](env))

    def freno(self, linea):
        """El error del freno para los programas que nunca terminan."""
        tope = f"{self.max_pasos:,}".replace(",", ".")
        tope += " de pasos" if self.max_pasos % 1_000_000 == 0 else " pasos"
        quien = (f"{self.contexto[0].nombre} atendiendo {self.contexto[2]}: "
                 if self.contexto else "")
        return ErrorMate(
            f"{quien}el programa lleva más de {tope}: ¿quedó en un bucle que nunca "
            "termina? Si es un 'mientras', revisá que su condición cambie adentro. Si "
            "el programa es largo de verdad, corrélo con --sin-limite",
            linea, clase="limite")

    def con_renglon(self, e, linea):
        """Lo que falló dentro de una sentencia, dicho como error de Mate y con su renglón."""
        if isinstance(e, ErrorMate):
            e.linea = e.linea or linea
            return e
        if isinstance(e, RecursionError):
            return self.demasiada_recursion(self.recursiva(), linea)
        return ErrorMate(SIN_MEMORIA, linea, clase="limite")

    def _bloque(self, cuerpo, nuevo=True):
        pasos = [self._paso(s) for s in cuerpo]
        # Un bloque solo necesita su propio entorno si declara algo ('sea', 'var' o una
        # función): si no, las variables que usa son las de afuera y se ahorra crearlo.
        if nuevo and any(s[0] in ("sea", "funcion") for s in cuerpo):
            def bloque(env):
                env = Entorno(env)
                for paso in pasos:
                    senal = paso(env)
                    if senal is not None:
                        return senal
            return bloque
        if not pasos:
            return lambda env: None
        if len(pasos) == 1:
            return pasos[0]

        def bloque(env):
            for paso in pasos:
                senal = paso(env)
                if senal is not None:
                    return senal
        return bloque

    def _paso(self, s, vale_suelto=False):
        """Arma una sentencia. Todas empiezan igual: anotan por qué renglón van, cuentan
        un paso (el freno) y, si algo falla adentro, le ponen su renglón al error."""
        if s[0] == "expr":
            return self._p_expr(s, vale_suelto)
        armar = getattr(self, "_p_" + s[0], None)
        if armar is None or s[0] in ("mensaje", "agente", "prueba", "usar"):
            clase = s[0]

            def no_va(env):
                raise ErrorMate(f"'{clase}' no puede ir acá")
            return self._contado(s[1], no_va)
        return armar(s)

    def _contado(self, linea, hacer):
        """El comienzo de toda sentencia, para las que no hace falta que vuelen."""
        it = self

        def paso(env):
            it.linea_actual = linea
            it.pasos = pasos = it.pasos + 1
            tope = it.max_pasos
            if tope is not None and pasos > tope:
                raise it.freno(linea)
            try:
                return hacer(env)
            except _SE_EXPLICAN as e:
                raise it.con_renglon(e, linea)
        return paso

    def _p_expr(self, s, vale_suelto):
        """Un renglón que es solo un valor: vale si hace algo (llamar a una función
        propia, mostrar, preguntar, crear). Si solo calcula y no lo usa, es un error."""
        it, linea, e = self, s[1], s[2]
        if vale_suelto or e[0] in ("preguntar", "crear"):
            de_valor = self.armar(e)

            def hacer(env):
                de_valor(env)
            return self._contado(linea, hacer)
        if e[0] != "llamar":
            de_valor = self.armar(e)

            def hacer(env):
                valor = de_valor(env)
                if isinstance(valor, (Funcion, Nativa)):
                    raise ErrorMate(f"a '{valor.nombre}' le faltan los paréntesis: "
                                    f"{valor.nombre}(...)", e[1], clase="escritura")
                raise renglon_sin_uso(e)
            return self._contado(linea, hacer)
        de_quien, de_args, renglon = self.armar(e[2]), [self.armar(a) for a in e[3]], e[1]
        llamar = self.llamar

        def paso(env):
            it.linea_actual = linea
            it.pasos = pasos = it.pasos + 1
            tope = it.max_pasos
            if tope is not None and pasos > tope:
                raise it.freno(linea)
            try:
                f = de_quien(env)
                nativa = isinstance(f, Nativa) and not isinstance(f, DePython)
                # (una consulta a la IA suelta no se llega a hacer: sería pagarla para
                # tirarla)
                if not (nativa and f.nombre == "consultar_ia"):
                    try:
                        llamar(f, [a(env) for a in de_args], renglon)
                    except ErrorMate as error:
                        error.linea = error.linea or renglon
                        raise
                if nativa and f.nombre not in HACEN_ALGO:
                    if f.nombre in ("agregar", "quitar"):
                        raise ErrorMate(
                            f"{f.nombre}() no cambia la lista: devuelve una nueva. Guardá "
                            f"el resultado: lista = {f.nombre}(lista, ...)", renglon,
                            clase="escritura")
                    raise ErrorMate(
                        f"{f.nombre}() devuelve un valor y este renglón no lo usa: "
                        f"guardalo (sea x = {f.nombre}(...)) o mostralo con mostrar(...)",
                        renglon, clase="escritura")
            except _SE_EXPLICAN as e:
                raise it.con_renglon(e, linea)
        return paso

    def _p_sea(self, s):
        it, linea, nombre, mutable = self, s[1], s[2], s[4]
        de_valor = self.armar(s[3])

        def paso(env):
            it.linea_actual = linea
            it.pasos = pasos = it.pasos + 1
            tope = it.max_pasos
            if tope is not None and pasos > tope:
                raise it.freno(linea)
            try:
                valor = de_valor(env)
                if nombre not in env.vars:  # (si está en este mismo bloque, lo dice definir)
                    env.no_tapar(nombre)
                env.definir(nombre, valor, mutable, None, linea)
            except _SE_EXPLICAN as e:
                raise it.con_renglon(e, linea)
        return paso

    def _p_asignar(self, s):
        it, linea, destino = self, s[1], s[2]
        de_valor = self.armar(s[3])
        if destino[0] != "nombre":  # una parte de una variable: lista[0] = ..., m.campo = ...
            asignar = self.asignar

            def hacer(env):
                asignar(destino, de_valor(env), env)
            return self._contado(linea, hacer)
        nombre = destino[2]

        def paso(env):
            it.linea_actual = linea
            it.pasos = pasos = it.pasos + 1
            tope = it.max_pasos
            if tope is not None and pasos > tope:
                raise it.freno(linea)
            try:
                valor = de_valor(env)
                if it.contexto is not None:
                    it.cuidar_lo_de_afuera(nombre, env)
                env.asignar(nombre, valor)
            except _SE_EXPLICAN as e:
                raise it.con_renglon(e, linea)
        return paso

    def _p_si(self, s):
        it, linea = self, s[1]
        ramas = [(self.armar(cond), self._bloque(cuerpo)) for cond, cuerpo in s[2]]
        otro = self._bloque(s[3]) if s[3] is not None else None
        if len(ramas) == 1:
            de_cond, cuerpo = ramas[0]

            def paso(env):
                it.linea_actual = linea
                it.pasos = pasos = it.pasos + 1
                tope = it.max_pasos
                if tope is not None and pasos > tope:
                    raise it.freno(linea)
                try:
                    v = de_cond(env)
                    if v is True:
                        return cuerpo(env)
                    if v is not False:
                        raise condicion_rara(v)
                    if otro is not None:
                        return otro(env)
                except _SE_EXPLICAN as e:
                    raise it.con_renglon(e, linea)
            return paso

        def hacer(env):
            for de_cond, cuerpo in ramas:
                v = de_cond(env)
                if v is True:
                    return cuerpo(env)
                if v is not False:
                    raise condicion_rara(v)
            if otro is not None:
                return otro(env)
        return self._contado(linea, hacer)

    def _p_mientras(self, s):
        it, linea = self, s[1]
        de_cond, cuerpo = self.armar(s[2]), self._bloque(s[3])

        def hacer(env):
            while True:
                v = de_cond(env)
                if v is not True:
                    if v is False:
                        return None
                    raise condicion_rara(v)
                # una vuelta cuenta aunque el cuerpo esté vacío
                it.pasos = pasos = it.pasos + 1
                tope = it.max_pasos
                if tope is not None and pasos > tope:
                    raise it.freno(linea)
                try:
                    senal = cuerpo(env)
                except _Continuar:
                    continue
                except _Romper:
                    return None
                if senal is not None:
                    if senal is _ROMPER:
                        return None
                    if senal is not _CONTINUAR:
                        return senal
        return self._contado(linea, hacer)

    def _p_para(self, s):
        # 'para2' es "para posicion, item en lista" (o "para clave, valor en mapa")
        it, linea, de_a_dos = self, s[1], s[0] == "para2"
        nombres = (s[2], s[3]) if de_a_dos else (s[2],)
        primero, segundo, repetida = nombres[0], nombres[-1], len(set(nombres)) != len(nombres)
        de_col, cuerpo = self.armar(s[-2]), self._bloque(s[-1], False)

        def hacer(env):
            col = de_col(env)
            if not isinstance(col, (list, dict, str)):
                raise ErrorMate(f"no se puede recorrer {tipo_claro(col)}: 'para' recorre "
                                "listas, mapas y textos")
            if de_a_dos:
                vueltas = list(col.items() if isinstance(col, dict) else enumerate(col))
            else:
                vueltas = list(col)
            # La variable de la vuelta se anota sin más controles, salvo que se llame
            # como una función incluida (o las dos igual): eso lo explica definir.
            de_afuera = env.raiz.origen
            directo = not repetida and not any(
                de_afuera.get(n) == "nativa" and n not in SE_PUEDEN_TAPAR for n in nombres)
            for valores in vueltas:
                it.pasos = pasos = it.pasos + 1
                tope = it.max_pasos
                if tope is not None and pasos > tope:
                    raise it.freno(linea)
                paso = Entorno(env)
                if not directo:
                    for nombre, x in zip(nombres, valores if de_a_dos else (valores,)):
                        paso.definir(nombre, x, False, "para")
                elif de_a_dos:
                    paso.vars = {primero: [valores[0], False], segundo: [valores[1], False]}
                    paso.origen = {primero: "para", segundo: "para"}
                else:
                    paso.vars[primero] = [valores, False]
                    paso.origen[primero] = "para"
                try:
                    senal = cuerpo(paso)
                except _Continuar:
                    continue
                except _Romper:
                    return None
                if senal is not None:
                    if senal is _ROMPER:
                        return None
                    if senal is not _CONTINUAR:
                        return senal
        return self._contado(linea, hacer)

    _p_para2 = _p_para

    def _p_romper(self, s):
        return self._contado(s[1], lambda env: _ROMPER)

    def _p_continuar(self, s):
        return self._contado(s[1], lambda env: _CONTINUAR)

    def _p_funcion(self, s):
        nombre, params, cuerpo, defectos = s[2], s[3], s[4], s[5]

        def hacer(env):
            env.definir(nombre, Funcion(nombre, params, cuerpo, env, defectos),
                        origen="funcion")
        return self._contado(s[1], hacer)

    def _p_devolver(self, s):
        it, linea = self, s[1]
        if s[2] is None:
            return self._contado(linea, lambda env: _SIN_VALOR)
        de_valor = self.armar(s[2])

        def paso(env):
            it.linea_actual = linea
            it.pasos = pasos = it.pasos + 1
            tope = it.max_pasos
            if tope is not None and pasos > tope:
                raise it.freno(linea)
            try:
                return (de_valor(env),)
            except _SE_EXPLICAN as e:
                raise it.con_renglon(e, linea)
        return paso

    def _p_enviar(self, s):
        it, linea = self, s[1]
        de_msg, de_dest = self.armar(s[2]), self.armar(s[3])

        def hacer(env):
            msg = it.un_mensaje(de_msg(env))
            destinos = it.destinos(de_dest(env))
            for dest in destinos:  # primero se revisan todos: sale para todos o para nadie
                if dest.ajeno is not None:
                    it.revisar_envio(dest, msg, linea)
                if msg.tipo not in dest.manejadores and not it.va_a_un_socio(dest, msg):
                    raise ErrorMate(f"{dest.nombre} no sabe recibir '{msg.tipo}'", linea,
                                    familia="agente")
            sobre = (it.en_conversacion(), None)  # (a varios: una sola conversación)
            rem = it.contexto[0] if it.contexto else None
            for dest in destinos:
                it.cola.append((rem, dest, msg, sobre))
        return self._contado(linea, hacer)

    def _p_responder(self, s):
        it, linea = self, s[1]
        de_valor = self.armar(s[2])

        def hacer(env):
            if not it.contexto:
                raise ErrorMate(RESPONDER_SUELTO)
            valor = de_valor(env)
            if lleva_funcion(valor):
                raise ErrorMate("no se puede responder con una función: "
                                "las respuestas llevan datos", linea)
            raise _Respuesta(valor, linea)
        return self._contado(linea, hacer)

    def _p_fallar(self, s):
        linea, de_motivo = s[1], self.armar(s[2])

        def hacer(env):
            motivo = de_motivo(env)
            raise ErrorMate(formato(motivo), linea, familia="fallar",
                            dato=None if lleva_funcion(motivo) else motivo)
        return self._contado(linea, hacer)

    def _p_intentar(self, s):
        it, var = self, s[3]
        cuerpo, manejo = self._bloque(s[2]), self._bloque(s[4], False)

        def hacer(env):
            try:
                return cuerpo(env)
            except ErrorMate as e:
                # El freno no se ataja nunca, ni un renglón mal escrito. Un 'asegurar'
                # tampoco dentro de una prueba (si no, pasaría en verde); al correr el
                # programa es una falla más.
                if e.clase in ("limite", "escritura") or (
                        e.clase == "asegurar" and it.en_prueba):
                    raise
                if it.contexto is not None:  # un agente atajó una falla: va a la bitácora
                    it.anotar_falla(it.contexto[0], e, it.contexto[4], atajada=True)
                adentro = Entorno(env)
                if var:
                    adentro.definir(var, ErrorAtajado(e), origen="falla")
                return manejo(adentro)
        return self._contado(s[1], hacer)

    def _p_asegurar(self, s):
        it, linea, cond = self, s[1], s[2]
        de_texto = self.armar(s[3]) if s[3] else None
        comparada = cond[0] == "bin" and cond[2] in COMPARADORES
        if comparada:
            # Se evalúa cada lado una sola vez, para poder mostrar qué dio.
            de_izq, de_der = self.armar(cond[3]), self.armar(cond[4])
            op, renglon = cond[2], cond[1]
        else:
            de_cond = self.armar(cond)

        def hacer(env):
            valores = ""
            if it.contexto is None and it.en_prueba:
                it.vaciar_cola()  # lo enviado en la prueba llega antes de asegurar
            if comparada:
                izq, der = de_izq(env), de_der(env)
                try:
                    cumple = it.binaria(op, izq, der)
                except ErrorMate as e:
                    e.linea = e.linea or renglon
                    raise
                if not cumple:
                    valores = it.valores_de(op, izq, der)
            else:
                cumple = de_cond(env)
                if type(cumple) is not bool:
                    raise condicion_rara(cumple)
            if not cumple:
                if de_texto:
                    detalle = formato(de_texto(env)) + (f" ({valores})" if valores else "")
                else:
                    detalle = "no se cumplió lo asegurado" + (f": {valores}" if valores else "")
                raise ErrorMate(detalle, linea, clase="asegurar")
        return self._contado(linea, hacer)

    def _p_simular(self, s):
        it, linea, tipo, var, cuerpo = self, s[1], s[3], s[4], s[5]
        de_dest = self.armar(s[2])

        def hacer(env):
            if not it.en_prueba or it.contexto is not None:
                raise ErrorMate("'simular' solo va dentro de una prueba")
            dest = it.destino(de_dest(env))
            if tipo not in dest.manejadores:
                raise ErrorMate(f"{dest.nombre} no sabe recibir '{tipo}': solo se simula un "
                                "mensaje que el agente ya recibe", familia="agente")
            dest.manejadores = {**dest.manejadores, tipo: (linea, var, cuerpo, env)}
        return self._contado(linea, hacer)

    def _p_asegurar_falla(self, s):
        it, linea = self, s[1]
        # Acá una cuenta o una función suelta vale: se prueba que falle.
        pasos = [self._paso(x, vale_suelto=True) for x in s[2]]
        de_texto = self.armar(s[3]) if s[3] else None

        def hacer(env):
            if it.contexto is None and it.en_prueba:
                it.vaciar_cola()
            try:
                adentro = Entorno(env)
                for paso in pasos:
                    senal = paso(adentro)
                    if senal is not None:
                        return senal
            except ErrorMate as e:
                # Igual que 'intentar': ni el freno, ni un renglón mal escrito, ni un
                # 'asegurar' de la prueba cuentan.
                if e.clase in ("limite", "escritura") or (
                        e.clase == "asegurar" and it.en_prueba):
                    raise
                if e.familia == "nombre":  # un nombre mal tipeado no es la falla esperada
                    raise ErrorMate(
                        f"lo de adentro de 'asegurar falla' no llegó a probarse: {e.mensaje}",
                        e.linea or linea, clase="asegurar")
                return None
            raise ErrorMate(formato(de_texto(env)) if de_texto else
                            "se esperaba que esto fallara, y no falló", linea, clase="asegurar")
        return self._contado(linea, hacer)

    def valores_de(self, op, izq, der):
        """Qué dio cada lado de un 'asegurar' que no se cumplió."""
        a, b = formato(izq, False), formato(der, False)
        if op != "==":
            return f"{a} {op} {b} es falso"
        if a != b:
            return f"dio {a} y se esperaba {b}"
        # Se ven iguales pero no lo son: el resto minúsculo de las cuentas con decimales.
        if type(izq) is float:
            a = repr(izq)
        if type(der) is float:
            b = repr(der)
        return (f"dio {a} y se esperaba {b}: se muestran igual, pero las cuentas con "
                "decimales dejan un resto minúsculo. Redondeá antes de comparar, por "
                "ejemplo redondear(a, 2) == redondear(b, 2)")

    def asignar(self, destino, valor, env):
        """Asignación con semántica de valor: cambiar m.a.b reconstruye m."""
        clase = destino[0]
        if clase == "nombre":
            if self.contexto is not None:
                self.cuidar_lo_de_afuera(destino[2], env)
            env.asignar(destino[2], valor)
            return
        if clase not in ("indice", "campo"):
            raise ErrorMate(NO_ASIGNABLE)
        base = self.ev(destino[2], env)
        if clase == "indice":
            clave = self.ev(destino[3], env)
            if isinstance(base, list):
                self.posicion(base, clave, al_asignar=True)
                nueva = list(base)
                nueva[clave] = valor
            elif isinstance(base, dict):
                self.clave_de_mapa(clave)
                nueva = {**base, clave: valor}
            else:
                raise ErrorMate(f"no se puede asignar por índice en {tipo_claro(base)}")
        elif clase == "campo":
            campo = destino[3]
            if isinstance(base, dict):
                nueva = {**base, campo: valor}
            elif isinstance(base, Registro):
                nueva = self.construir(base.tipo, {**base.campos, campo: valor})
            else:
                raise ErrorMate(f"{tipo_claro(base)} no tiene campos"
                                + (f". {CAUSA_DE_NADA}" if base is None else ""))
        else:
            raise ErrorMate(NO_ASIGNABLE)
        self.asignar(destino[2], nueva, env)

    def cuidar_lo_de_afuera(self, nombre, env):
        """Mientras un agente atiende, nadie cambia las variables del programa: tampoco
        una función de afuera que el agente llame."""
        e = env
        while e is not None and nombre not in e.vars:
            e = e.padre
        if e is None or not e.vars[nombre][1]:
            return  # no existe o es fijo: lo explica el error de siempre
        agente, _, _, desde, _ = self.contexto
        if e.serie >= desde:
            return  # una variable nacida mientras atiende este mensaje
        propio = e
        while propio is not None and propio is not agente.env:
            propio = propio.padre
        if propio is None:  # ni su estado ni algo suyo: es de afuera
            por = f" (ni siquiera a través de la función {self.llamadas[-1]}())" \
                if self.llamadas else ""
            raise ErrorMate(f"{agente.nombre} no puede modificar '{nombre}'{por}: "
                            "es de afuera. Los agentes solo cambian su propio estado")

    def clave_de_mapa(self, clave):
        if not isinstance(clave, str):
            raise ErrorMate(f"las claves de un mapa son textos, no {tipo_claro(clave)}")

    def posicion(self, sec, i, al_asignar=False):
        """Controla que i sea una posición de esa lista (o de ese texto)."""
        if type(i) is float and i.is_integer():
            # Se ve entero, pero salió de una cuenta con decimales (4 * 0.5): no se acepta
            # a escondidas, y el error no dice "dio 2" como si el 2 estuviera mal.
            raise ErrorMate(
                f"la posición tiene que ser un número entero, y este {formato(i)} salió de "
                "una cuenta con decimales (por ejemplo 4 * 0.5), así que por dentro no es "
                "un entero. Pasalo por redondear(): lista[redondear(...)]")
        if type(i) is float:
            raise ErrorMate(
                f"la posición tiene que ser un número entero y dio {formato(i)}. Si salió "
                "de una cuenta (una división, por ejemplo), pasala por redondear()")
        if type(i) is not int:
            raise ErrorMate("la posición tiene que ser un número entero, no "
                            + tipo_claro(i))
        cuantos = len(sec)
        if 0 <= i < cuantos:
            return
        que, cosas = ("el texto", "letra") if isinstance(sec, str) else ("la lista", "elemento")
        if cuantos == 0:
            tiene = f"{que} no tiene ningún {cosas}"
        elif cuantos == 1:
            tiene = f"{que} tiene 1 {cosas}, así que la única posición es la 0"
        else:
            tiene = (f"{que} tiene {cuantos} {cosas}s, así que las posiciones van de 0 a "
                     f"{cuantos - 1}")
        pista = ""
        if i < 0:
            pista = ". Las posiciones no son negativas: para el último usá ultimo(...)"
        elif al_asignar:
            pista = ". Para sumar un elemento al final usá agregar(lista, valor)"
        elif i == cuantos and cuantos:
            pista = (f". Como se cuenta desde 0, el último está en la posición "
                     f"{cuantos - 1} (o usá ultimo(...))")
        raise ErrorMate(f"la posición {i} está fuera de rango: {tiene}{pista}",
                        familia="posicion")

    # ── expresiones ──
    def ev(self, n, env):
        """El valor de esa expresión. (Lo que ya está armado no pasa por acá.)"""
        listo = self._armados.get(id(n))
        if listo is None:
            listo = self._armados[id(n)] = (self.armar(n), n)
        return listo[0](env)

    def armar(self, n):
        """Arma una expresión: devuelve una función que recibe el entorno y da el valor.
        Si falla, el error sale con el renglón de la expresión de más adentro."""
        armar = getattr(self, "_x_" + n[0], None)
        if armar is None:
            clase, linea = n[0], n[1]

            def desconocida(env):
                raise ErrorMate(f"expresión desconocida: {clase}", linea)
            return desconocida
        return armar(n)

    def _x_num(self, n):
        valor = n[2]
        return lambda env: valor

    _x_str = _x_bool = _x_num

    def _x_nada(self, n):
        return lambda env: None

    def _x_nombre(self, n):
        linea, nombre = n[1], n[2]

        def valor(env):
            e = env
            while e is not None:
                caja = e.vars.get(nombre)
                if caja is not None:
                    return caja[0]
                e = e.padre
            error = env.no_existe(nombre)
            error.linea = error.linea or linea
            raise error
        return valor

    def _x_interp(self, n):
        linea = n[1]
        partes = [(True, p) if isinstance(p, str) else (False, self.armar(p)) for p in n[2]]

        def valor(env):
            try:
                hechas, largo = [], 0
                for fija, p in partes:
                    if not fija:
                        p = p(env)
                        if type(p) is not str:
                            p = a_texto(p)
                    hechas.append(p)
                    largo += len(p)
                    if largo > MAX_LARGO:
                        raise muy_largo()
                return "".join(hechas)
            except ErrorMate as e:
                e.linea = e.linea or linea
                raise
        return valor

    def _x_lista(self, n):
        de_cada = [self.armar(x) for x in n[2]]
        return lambda env: [de(env) for de in de_cada]

    def _x_mapa(self, n):
        pares = [(k, self.armar(e)) for k, e in n[2]]
        return lambda env: {k: de(env) for k, de in pares}

    def _x_ctor(self, n):
        linea, tipo, construir = n[1], n[2], self.construir
        pares = [(k, self.armar(e)) for k, e in n[3]]

        def valor(env):
            try:
                return construir(tipo, {k: de(env) for k, de in pares})
            except ErrorMate as e:
                e.linea = e.linea or linea
                raise
        return valor

    def _x_remitente(self, n):
        it = self
        return lambda env: it.contexto[1] if it.contexto else None

    def _x_yo(self, n):
        it = self
        return lambda env: it.contexto[0] if it.contexto else None

    def _x_crear(self, n):
        it, linea = self, n[1]

        def valor(env):
            try:
                return it.crear(n, env)
            except ErrorMate as e:
                e.linea = e.linea or linea
                raise
        return valor

    def _x_y(self, n):
        linea, de_a, de_b, es_o = n[1], self.armar(n[2]), self.armar(n[3]), n[0] == "o"

        def valor(env):
            a = de_a(env)
            if a is es_o:  # 'y' con el primero falso, 'o' con el primero verdadero
                return a
            if a is True or a is False:
                b = de_b(env)
                if b is True or b is False:
                    return b
                a = b
            raise condicion_rara(a, linea)
        return valor

    _x_o = _x_y

    def _x_no(self, n):
        linea, de_a = n[1], self.armar(n[2])

        def valor(env):
            a = de_a(env)
            if a is True:
                return False
            if a is False:
                return True
            raise condicion_rara(a, linea)
        return valor

    def _x_neg(self, n):
        linea, de_a = n[1], self.armar(n[2])

        def valor(env):
            v = de_a(env)
            if not es_num(v):
                raise ErrorMate(f"no se puede negar {tipo_claro(v)}: el signo menos va "
                                "delante de un número", linea)
            return -v
        return valor

    def _x_bin(self, n):
        linea, op, binaria = n[1], n[2], self.binaria
        de_a, de_b = self.armar(n[3]), self.armar(n[4])

        def completa(a, b):
            """La cuenta con todos sus controles: para lo que no es el caso de siempre."""
            try:
                return binaria(op, a, b)
            except ErrorMate as e:
                e.linea = e.linea or linea
                raise

        # Lo de todos los días (números no gigantes, textos iguales o distintos) se
        # resuelve acá mismo; da exactamente lo que daría la cuenta completa.
        fijo = n[4][2] if n[4][0] == "num" and type(n[4][2]) is int else None
        if fijo is not None and not -_CHICO < fijo < _CHICO:
            fijo = None
        if op in _CUENTAS:
            cuenta = _CUENTAS[op]
            if fijo is not None:
                def valor(env):
                    a = de_a(env)
                    if type(a) is int and -_CHICO < a < _CHICO:
                        return cuenta(a, fijo)
                    return completa(a, fijo)
                return valor

            def valor(env):
                a = de_a(env)
                b = de_b(env)
                ta = type(a)
                if ta is int:
                    if type(b) is int and -_CHICO < a < _CHICO and -_CHICO < b < _CHICO:
                        return cuenta(a, b)
                elif ta is float and type(b) is float:
                    r = cuenta(a, b)
                    if _finito(r):
                        return r
                return completa(a, b)
            return valor
        if op in _COMPARACIONES:
            compara = _COMPARACIONES[op]
            if fijo is not None:
                def valor(env):
                    a = de_a(env)
                    ta = type(a)
                    if ta is int or ta is float:
                        return compara(a, fijo)
                    return completa(a, fijo)
                return valor

            def valor(env):
                a = de_a(env)
                b = de_b(env)
                ta, tb = type(a), type(b)
                if (ta is int or ta is float) and (tb is int or tb is float):
                    return compara(a, b)
                if ta is str and tb is str and (op == "==" or op == "!="):
                    return compara(a, b)
                return completa(a, b)
            return valor
        if op in ("/", "%"):
            resto = op == "%"

            def valor(env):
                a = de_a(env)
                b = de_b(env)
                if (type(a) is int and type(b) is int and b != 0
                        and -_CHICO < a < _CHICO and -_CHICO < b < _CHICO):
                    if resto:
                        return a % b
                    # la división exacta entre enteros no pierde cifras
                    return a // b if a % b == 0 else a / b
                return completa(a, b)
            return valor
        return lambda env: completa(de_a(env), de_b(env))

    def _x_llamar(self, n):
        linea, llamar = n[1], self.llamar
        de_quien, de_args = self.armar(n[2]), [self.armar(a) for a in n[3]]

        if len(de_args) == 1:  # (lo más común: se ahorra la vuelta que arma la lista)
            de_uno = de_args[0]

            def valor(env):
                f = de_quien(env)
                args = [de_uno(env)]
                try:
                    return llamar(f, args, linea)
                except ErrorMate as e:
                    e.linea = e.linea or linea
                    raise
            return valor

        def valor(env):
            f = de_quien(env)
            args = [de(env) for de in de_args]
            try:
                return llamar(f, args, linea)
            except ErrorMate as e:
                e.linea = e.linea or linea
                raise
        return valor

    def _x_indice(self, n):
        it, linea = self, n[1]
        de_base, de_i = self.armar(n[2]), self.armar(n[3])

        def valor(env):
            base, i = de_base(env), de_i(env)
            tipo = type(base)
            if tipo is list:
                if type(i) is int and 0 <= i < len(base):
                    return base[i]
            elif tipo is dict and type(i) is str and i in base:
                return base[i]
            try:
                if isinstance(base, (list, str)):
                    it.posicion(base, i)
                    return base[i]
                if isinstance(base, dict):
                    it.clave_de_mapa(i)
                    if i not in base:
                        raise ErrorMate(no_esta(
                            f"el mapa no tiene la clave {formato(i, False)}", i, base),
                            familia="clave")
                    return base[i]
                raise ErrorMate(f"{tipo_claro(base)} no tiene posiciones ni claves: los "
                                "corchetes van después de una lista, un texto o un mapa"
                                + (f". {CAUSA_DE_NADA}" if base is None else ""))
            except ErrorMate as e:
                e.linea = e.linea or linea
                raise
        return valor

    def _x_campo(self, n):
        linea, campo, de_base = n[1], n[3], self.armar(n[2])

        def valor(env):
            base = de_base(env)
            campos = base.campos if isinstance(base, Registro) else base
            if not isinstance(campos, dict):
                if isinstance(base, ModuloPython):  # ayudas.doble: una función de Python
                    try:
                        return base.funcion(campo)
                    except ErrorMate as e:
                        e.linea = e.linea or linea
                        raise
                pista = f". {CAUSA_DE_NADA}" if base is None else ""
                if isinstance(base, list):
                    pista = (f": es una lista. Para ver '{campo}' de uno de sus elementos, "
                             f"pedilo primero (por ejemplo lista[0].{campo}) o recorré la "
                             f"lista:  para fila en lista {{ mostrar(fila.{campo}) }}")
                if isinstance(base, Agente) and base.ajeno is not None:
                    raise ErrorMate(de_otro_programa(base.nombre, base.ajeno,
                                                     f"mirarle '{campo}'"), linea)
                raise ErrorMate(f"{tipo_claro(base)} no tiene campos{pista}", linea)
            if campo not in campos:
                mensaje = no_esta(
                    f"{nombre_tipo(base)} no tiene un campo '{campo}'", campo, campos)
                casi = [c for c in campos if isinstance(c, str) and c != campo
                        and sin_tildes(c).lower().strip() == sin_tildes(campo).lower()]
                if casi and isinstance(base, dict):
                    mensaje += (f" (las mayúsculas y las tildes cuentan. Si este dato viene "
                                f"de una planilla, el título de la columna está escrito "
                                f"'{casi[0]}': cambialo ahí por '{campo}', o usá '{casi[0]}' "
                                "en el programa)")
                raise ErrorMate(mensaje, linea, familia="clave")
            return campos[campo]
        return valor

    def _x_preguntar(self, n):
        it, linea = self, n[1]
        de_msg, de_dest = self.armar(n[2]), self.armar(n[3])

        def valor(env):
            try:
                msg = it.un_mensaje(de_msg(env))
                dest = it.destino(de_dest(env))
                if dest.ajeno is not None:
                    raise ErrorMate(no_se_le_pregunta(dest.nombre, dest.ajeno,
                                                      it.responde.get(msg.tipo)))
                if it.contexto is None and not it.naciendo:
                    it.vaciar_cola()  # lo que el programa ya envió llega antes
                return it.entregar(it.contexto[0] if it.contexto else None, dest, msg,
                                   True, linea)
            except ErrorMate as e:
                e.linea = e.linea or linea
                raise
        return valor

    def binaria(self, op, a, b):
        if type(a) is int and type(b) is int:
            # Un entero que crece sin parar (x = x * x) cuelga la consola: se corta antes.
            if op == "*" and a.bit_length() + b.bit_length() > MAX_BITS:
                raise ErrorMate(DEMASIADO_GRANDE)
            if op in "+-" and max(a.bit_length(), b.bit_length()) >= MAX_BITS:
                raise ErrorMate(DEMASIADO_GRANDE)
        elif op == "+" and se_juntan(a, b) and len(a) + len(b) > MAX_LARGO:
            raise muy_largo("el texto" if isinstance(a, str) else "la lista")
        try:
            r = self._binaria(op, a, b)
        except OverflowError:
            raise ErrorMate(DEMASIADO_GRANDE)
        if type(r) is float and not math.isfinite(r):
            raise ErrorMate(DEMASIADO_GRANDE)
        return r

    def _binaria(self, op, a, b):
        if op in ("==", "!="):
            if (isinstance(a, str) and es_num(b)) or (es_num(a) and isinstance(b, str)):
                t = a if isinstance(a, str) else b
                try:
                    numero_de_texto(t)
                    arreglo = f"Convertí uno de los dos: numero({formato(t, False)}) o texto(...)"
                except ErrorMate:
                    arreglo = ("Ese texto " + ("está vacío" if not t.strip() else
                                               "no es un número")
                               + ": si viene de una planilla, es una celda "
                               + ("vacía" if not t.strip() else "que no tiene un número")
                               + ". Completala en la planilla, o preguntá antes qué es:  "
                               'si tipo(dato) == "numero" { ... }')
                raise ErrorMate(
                    f"no se puede comparar un texto con un número ({formato(a, False)} "
                    f"{op} {formato(b, False)}): nunca son iguales. {arreglo}")
            return igual(a, b) if op == "==" else not igual(a, b)
        ambos_num = es_num(a) and es_num(b)
        if op in ("<", "<=", ">", ">="):
            if not (ambos_num or (isinstance(a, str) and isinstance(b, str))):
                if a is None or b is None:
                    raise ErrorMate(f"no se puede comparar {un(a)} con {un(b)} usando "
                                    f"'{op}'. {CAUSA_DE_NADA}")
                raise ErrorMate(f"no se puede comparar {nombre_tipo(a)} con {nombre_tipo(b)}")
            if not ambos_num and _FECHA.fullmatch(a) and _FECHA.fullmatch(b):
                raise ErrorMate(
                    f"las fechas son textos, y '{op}' las compararía letra por letra: "
                    f'"{a}" {op} "{b}" daría cualquier cosa. Mate todavía no sabe comparar '
                    "fechas; con == y != sí se puede ver si son la misma")
            return {"<": a < b, "<=": a <= b, ">": a > b, ">=": a >= b}[op]
        if op == "+" and (ambos_num or se_juntan(a, b)):
            return a + b
        if ambos_num:
            if op == "-":
                return a - b
            if op == "*":
                return a * b
            if b == 0:
                raise ErrorMate("división por cero", familia="division")
            if op == "%":
                return a % b
            if type(a) is int and type(b) is int and a % b == 0:
                return a // b  # la división exacta entre enteros no pierde cifras
            return a / b
        if a is None or b is None:
            raise ErrorMate(f"no se puede {_VERBOS[op]} {un(a)} con {un(b)}. {CAUSA_DE_NADA}")
        pista = ""
        if op == "+" and isinstance(a, list):
            pista = " (para sumarle un valor a una lista usá agregar(lista, valor))"
        elif op == "+" and (isinstance(a, str) or isinstance(b, str)):
            pista = " (usá texto() o \"{...}\" para armar textos)"
        elif (isinstance(a, str) and es_num(b)) or (es_num(a) and isinstance(b, str)):
            pista = (". Lo que se lee con leer() o viene de un archivo es un texto, aunque "
                     "tenga cifras: para hacer cuentas pasalo antes a número con numero(...)")
        raise ErrorMate(f"no se puede hacer {nombre_tipo(a)} {op} {nombre_tipo(b)}{pista}")

    def llamar(self, f, args, linea=None):
        if type(f) is Funcion:
            pass
        elif isinstance(f, Nativa):
            return f.fn(args)
        elif not isinstance(f, Funcion):
            raise ErrorMate(f"{tipo_claro(f)} no es una función: no se le pueden poner "
                            "paréntesis" + (
                                f". Se llama a una de sus funciones: {f.nombre}.nombre(...)"
                                if isinstance(f, ModuloPython) else ""))
        params, nombre, cuantos = f.params, f.nombre, len(args)
        minimo = len(params) - len(f.defectos)
        if not minimo <= cuantos <= len(params):
            raise ErrorMate(espera_otra_cantidad(nombre, minimo, len(params), cuantos))
        if self.abiertas >= MAX_LLAMADAS:
            self.ultima_funcion = nombre
            raise self.demasiada_recursion(nombre)
        env = Entorno(f.env, False, True)
        directa = f.directa
        if directa is None:
            # ¿Se pueden anotar los parámetros sin más controles? Sí, salvo que alguno
            # esté repetido o se llame como una función incluida: eso lo explica definir.
            de_afuera = env.raiz.origen
            directa = f.directa = len(set(params)) == len(params) and not any(
                de_afuera.get(p) == "nativa" and p not in SE_PUEDEN_TAPAR for p in params)
        if directa:
            if cuantos == 1:  # (lo más común, sin vueltas)
                env.vars[params[0]] = [args[0], False]
                env.origen[params[0]] = "parametro"
            elif cuantos:
                variables, origen = env.vars, env.origen
                for p, a in zip(params, args):
                    variables[p] = [a, False]
                    origen[p] = "parametro"
        else:
            for p, a in zip(params, args):
                env.definir(p, a, False, "parametro")
        self.llamadas.append(nombre)
        self.abiertas += 1
        self.ultima_funcion = nombre
        try:
            # Los que no vinieron toman su valor por defecto, que se calcula en cada
            # llamada y puede usar los parámetros de antes: f(a, b = a * 2).
            if cuantos != len(params):
                for p, e in f.defectos[cuantos - minimo:]:
                    env.definir(p, self.ev(e, env), False, "parametro")
            cuerpo = f.armado
            if cuerpo is None:  # se arma la primera vez que se la llama
                cuerpo = f.armado = self.armar_bloque(f.cuerpo, False)
            senal = cuerpo(env)
        except _Retorno as r:
            return r.valor
        except ErrorMate as e:
            anotar_paso(e, ("funcion", nombre, linea))
            raise
        finally:
            self.llamadas.pop()
            self.abiertas -= 1
        if senal is None:
            return None
        if type(senal) is tuple:  # un 'devolver'
            return senal[0]
        return self.fuera_de_lugar(senal)

    def recursiva(self):
        """Si se acabó el lugar en medio de llamadas a funciones, el nombre de la última."""
        return self.ultima_funcion if self.abiertas > 20 else None


# ───────────────────────────── CLI ─────────────────────────────


def simbolo(s, reemplazo):
    """Devuelve s si la consola lo puede mostrar; si no, el reemplazo en letras comunes."""
    try:
        s.encode(getattr(sys.stdout, "encoding", None) or "utf-8")
        return s
    except (UnicodeError, LookupError):
        return reemplazo


GUIA = r"""GUÍA DE MATE {version} (para pegarle a un asistente de IA antes de pedirle un programa)

Mate es un lenguaje chico con palabras en español. Escribí solo lo que figura en esta guía:
no inventes palabras ni funciones, y no uses las de otros lenguajes (if, print, return...).

RENGLONES
- Una sentencia por renglón, sin punto y coma. Los comentarios empiezan con #.
- Un renglón sigue en el de abajo solo si queda abierto un ( [ {{ o si termina en un
  operador o una coma. Un renglón no puede empezar con + * / == y o.
- Los bloques van entre llaves {{ }}. Los textos, entre comillas dobles y en un renglón
  (los de varios renglones, entre tres comillas: ver VALORES).

VALORES
- numero: 3   3.5 (decimales con punto)   1500 o 1_500 (los miles nunca llevan punto)
- texto: "hola"        logico: verdadero  falso
- nada (la ausencia de valor)
- lista: [1, 2, 3]   lista[0] es el primero (las posiciones arrancan en 0)
- mapa: {{ nombre: "yerba", precio: 3500 }}   mapa.nombre   mapa["nombre"]
- Dentro de un texto, {{...}} se calcula: "Total: {{precio * 2}}". Adentro de las llaves
  puede haber otros textos, con sus comillas: "Sale {{precios["yerba"]}}". \n es salto de
  renglón, \{{ una llave de verdad y \\ una barra (las rutas de Windows van con / o con
  doble barra).
- Un texto de varios renglones va entre tres comillas, con las mismas {{...}} y barras:
      sea carta = {tres}
          Hola {{nombre}}:
          tu pedido sale {{pesos(total)}}.
          {tres}
  No cuentan el renglón de las comillas ni la sangría que comparten todos los renglones.

VARIABLES
- sea x = 1        fijo, no cambia más
- var y = 0        puede cambiar:   y = y + 1     y += 1     y -= 1
- y.campo = 5 y lista[0] = 5 cambian una parte (la variable tiene que ser 'var').
- Copiar un valor lo copia entero: cambiar la copia no toca el original.
- Un 'sea' o 'var' dentro de un bloque no puede repetir el nombre de una variable de afuera.
- Un porcentaje se escribe como cuenta: 21 / 100 o 0.21 (el signo % es el resto de dividir).
- No se usan como nombre las palabras de Mate ni las funciones incluidas.
- Nombres de variables y funciones en minúscula; mensajes y agentes con Mayúscula inicial.

OPERADORES
- + - * / %        == != < <= > >=        y  o  no
- Nada se convierte solo: "a" + 1 es un error (usar "a{{1}}" o texto(1)), y "18" == 18
  también (usar numero("18")). Las condiciones tienen que dar verdadero o falso.

CONTROL
- si cond {{ ... }} sino si cond {{ ... }} sino {{ ... }}
- mientras cond {{ ... }}
- para item en lista {{ ... }}      (también recorre las claves de un mapa y las letras de un texto)
- para i, item en lista {{ ... }}   con la posición (desde 0); en un mapa: para clave, valor en mapa
- romper sale del bucle; continuar salta a la vuelta siguiente.
- funcion nombre(a, b) {{ devolver a + b }}        'devolver' solo, sin valor, devuelve nada
- funcion con_iva(precio, tasa = 0.21) {{ ... }}    tasa tiene valor por defecto: con_iva(100)
  usa 0.21 y con_iva(100, 0.5) usa 0.5. Los parámetros con valor por defecto van al final.
- fallar "motivo"                                 corta con un error
- intentar {{ ... }} si falla e {{ ... }}             e es el texto del error (el 'e' es opcional)
  detalle_de(e).clase dice qué pasó sin depender de la redacción: "fallar", "asegurar",
  "contrato", "clave", "posicion", "division", "nombre", "numero", "json", "agente",
  "ciclo", "archivo", "ia", "tope", "python" u "otro". detalle_de(e).dato es el valor que
  se le dio a 'fallar'.

FUNCIONES INCLUIDAS (no hay otras)
{funciones}
- agregar, quitar, ordenar y porcion devuelven una copia NUEVA, no cambian la original:
  lista = agregar(lista, x)
- quitar(lista, x) saca por valor, no por posición: se van todos los que valen x.
- Una función incluida suelta en un renglón (salvo mostrar, leer, escribir_archivo,
  agregar_a_archivo y aprender) es un error: hay que usar lo que devuelve. Ese error no se
  ataja con 'intentar': para validar un dato se escribe
      intentar {{ sea n = numero(dato) ... }} si falla e {{ ... }}
- hoy() y ahora() dan textos: no se restan ni se comparan con < o > (sí con == y !=).
- leer_archivo, leer_tabla, escribir_archivo y agregar_a_archivo solo andan desde el programa
  principal (no desde un agente: se le pasan los datos en un mensaje), con archivos de la
  carpeta del programa, y no pisan archivos .mate ni .py (ni la memoria y la bitácora
  que Mate lleva del propio programa). Con 'probar' ninguna de las dos toca el disco: lo
  guardado se ve con leer_archivo() dentro de esa prueba y nada más.
- leer_tabla("precios.csv") lee una planilla guardada desde Excel como CSV (separada por
  punto y coma o por coma) y da una lista con un mapa por fila; las claves son los títulos
  de la primera fila, tal cual están escritos:
      para fila en leer_tabla("precios.csv") {{ mostrar(fila.producto, pesos(fila.precio)) }}
  Una celda escrita como número ya llega como número, también a la argentina (3.500 es 3500;
  3.500,50; $ 3.500). numero("3.500") también da 3500 (en un TEXTO, un punto con justo tres
  cifras atrás es de miles; "3.5", "3.50" y "0.500" son decimales; en el programa, 3.5 es 3.5).
  Lo demás llega como texto, y una celda vacía es "". Un título con
  espacios se lee con corchetes: fila["precio de lista"].
- agregar_a_archivo("pedidos.txt", renglon) suma ese texto como un renglón más, al final (si
  el archivo no existe, lo crea). Con 'probar' no toca el archivo de verdad: lo agregado se
  ve con leer_archivo() dentro de esa prueba y nada más.
- leer("Cliente:", "chau") espera que la persona escriba y apriete Enter; devuelve un texto.
  El 2.º valor es lo que da cuando no hay teclado (con 'probar' nunca lo espera). Una charla
  es un bucle que sale con una palabra (Ctrl+C también la termina bien):
      mientras verdadero {{
          sea dicho = leer("Cliente:", "chau")
          si minusculas(dicho) == "chau" {{ romper }}
          mostrar("Dijiste: {{dicho}}")
      }}
  (La orden 'ensayar programa.mate casos.txt' prueba un programa así sin tipear: escribe
  cada pregunta del archivo en el primer leer() y mira lo que el programa muestra después.
  En ese archivo, debajo de cada pregunta, va lo que se espera:  tiene que decir: sin envío
  o  no puede decir: descuento  y, entre agentes,  tiene que viajar: Reservar de Ventas a
  Deposito  o  no tiene que viajar: Reponer . Si el caso necesita un renglón más del cliente
  en la misma charla, va debajo de la pregunta:  después: si )
- consultar_ia(instrucciones, pregunta) le pregunta a una IA de verdad (Claude) y devuelve su
  respuesta como texto. Sirve adentro de un agente: el agente arma la pregunta, consulta y
  responde con su mensaje de siempre. Es paga y necesita la clave en la variable de entorno
  ANTHROPIC_API_KEY (nunca escrita en el programa). Si algo sale mal (sin clave, sin red,
  sin crédito) es un error que se ataja con 'intentar'; su clase es "ia".
  Con 'probar' y con la opción --ia-simulada no sale a la red: contesta lo que fijó la prueba
  con simular_ia("...") o, si no, el tercer valor:  consultar_ia(inst, pregunta, "Hola").

AGENTES Y MENSAJES
- mensaje Pedido {{ producto: texto, cantidad: numero, nota: texto? }}     (? = opcional)
  Tipos: numero texto logico lista mapa agente cualquiera, u otro mensaje. Una lista
  puede decir de qué es: items: lista de Pedido     vendedores: lista de agente
- Un campo puede decir qué valores acepta, después del tipo y con valores escritos a mano:
      cantidad: numero desde 1 hasta 100         (también solo 'desde 1' o solo 'hasta 100')
      prioridad: texto en ["baja", "media", "alta"]        una de esas opciones
      prioridad: texto en ["baja", "alta"] = "baja"        valor por defecto: puede faltar
  El orden es ese: desde, hasta (o en [...]) y al final = valor. Se controla al armar el
  mensaje y, si el valor está escrito a mano, antes de correr.
- mensaje Pedido {{ ... }} responde Cotizacion     declara qué se le contesta a un Pedido
- Crear un mensaje: Pedido {{ producto: "yerba", cantidad: 2 }}     Sin campos: Ping {{}}
- agente Nombre {{
      estado contador = 0                  memoria privada; solo él la cambia
      al recibir Pedido como p {{ ... }}     uno por cada mensaje que entiende
      funcion ayuda(x) {{ ... }}             funciones propias
  }}
- responder valor        contesta y termina (solo dentro de 'al recibir')
- enviar Mensaje {{ ... }} a Agente              lo deja en la cola y sigue
- enviar Mensaje {{ ... }} a [norte, sur]        el mismo mensaje a cada agente de la lista
- sea r = preguntar Mensaje {{ ... }} a Agente   espera la respuesta; si el otro falla, falla acá
- remitente es quien mandó el mensaje; yo es el agente que está atendiendo.
- Dentro de un agente, opcional: al fallar como f {{ ... }}   se entera cuando un mensaje que
  él mandó con 'enviar' no pudo atenderse. f.motivo es el texto del error, f.mensaje el
  mensaje que mandó y f.destino el agente que falló. Ahí no va 'responder'.
- sea otro = crear Vendedor llamado "Norte" {{ contador: 5 }}     otra copia, con su estado
- Un agente no puede cambiar variables de afuera ni el estado de otro. Los mensajes llevan
  datos, nunca funciones.
- estado recordado atendidos = 0     como 'estado', pero ese dato se guarda cuando el programa
  termina (en programa.memoria.json, al lado del programa) y vuelve en la próxima corrida.
  Solo datos: números, textos, listas, mapas y mensajes. Vale para los agentes declarados y
  para las copias con nombre (crear ... llamado "Centro"). Con 'probar' no se lee ni se
  guarda nada. 'correr programa.mate --olvidar' arranca de cero.
- Dentro de un agente, aprender("texto") le anota una lección (queda guardada junto con lo
  recordado; no se repite ni se pasa de {max_lecciones}) y lecciones() da la lista de las suyas.
  consultar_ia() dentro de ese agente las agrega solas al final de las instrucciones, bajo
  un título, para que la IA las tenga en cuenta. El dueño anota lecciones sin tocar el
  programa:  mate.py corregir programa.mate Agente "texto"
- Si el programa usa 'estado recordado' o lecciones, cada falla de un agente queda anotada
  sola en programa.bitacora.txt (se lee resumida con: mate.py bitacora programa.mate).
- FRENOS: reglas que el agente declara y que MATE comprueba sobre cada respuesta de
  consultar_ia() de ese agente, antes de devolverla (no se le pide a la IA que se controle):
      agente Mostrador {{
          estado lista = [3500, 1200]
          frenos {{
              precios: lista                    # los únicos importes en pesos que puede nombrar
              prohibido: ["descuento", "fiado"]  # palabras o temas que no pueden aparecer
              largo: 400                        # letras de la respuesta, como mucho
              reserva: "Eso te lo confirma una persona, ya te paso."
              consultas_por_dia: 100            # tope de gasto (opcional)
              tokens_por_dia: 200000            # tope de gasto (opcional)
          }}
          al recibir Consulta como c {{ responder consultar_ia("Atendés...", c.pregunta) }}
      }}
  Una regla por renglón; todas son opcionales, pero si hay precios, prohibido o largo tiene
  que haber reserva. Cada valor es una expresión que puede usar el estado y las funciones
  del agente, y se calcula en cada consulta. 'frenos' no es una palabra reservada.
  - precios: una lista de números (o una tabla o un mapa: valen todos sus números). Cuenta
    como importe un número con $ ($ 3.500, $3500, $ 3.500,00), con "pesos" (3500 pesos, 3 mil
    pesos), con USD o "dólares", o suelto después de sale/cuesta/vale/precio/total si es de
    100 o más. Cantidades, teléfonos, fechas, porcentajes e importes escritos con letras no
    se miran. Compara números: un total que no está en la lista (3 yerbas = $ 10.500) salta.
  - prohibido: sin distinguir mayúsculas ni tildes; "descuento" también frena "descuentos".
  - Si la respuesta rompe una regla, Mate consulta UNA vez más avisándole a la IA cuál; si
    la vuelve a romper, consultar_ia() devuelve el texto de reserva. Queda en --traza, en la
    bitácora y como lección PROPUESTA (no se usa hasta que el dueño la aprueba con
    mate.py propuestas programa.mate aprobar 1).
  - Al llegar a un tope, consultar_ia() no consulta: devuelve la reserva o, si no hay
    reserva, falla con un error que se ataja (clase "tope"). La cuenta es por día, se guarda
    en programa.memoria.json y se ve con mate.py bitacora programa.mate. Mate lo avisa en
    pantalla la primera vez. Con --ia-simulada el tope cuenta solo las consultas de esa
    corrida. El segundo intento también cuenta, y la consulta que se cobró aunque haya
    vuelto cortada o sin texto.
  - Un error al calcular los frenos (o un valor fijo que no sirve) corta el programa con el
    renglón de la regla: no se ataja con 'intentar'.
- usar "otro.mate" trae los mensajes, agentes, funciones y variables ('sea' y 'var') de
  otro archivo. Un nombre que ya vino de ahí no se puede declarar de nuevo.
- usar buzon "deposito.mate" (0.7): los agentes de ese OTRO programa de la misma carpeta
  quedan como destino de 'enviar' (y nada más: no se les puede 'preguntar' ni 'crear').
  El mensaje sale cuando el programa termina, queda en la carpeta deposito.buzon y se
  entrega, validado con el contrato, cuando corre deposito.mate. La contestación vuelve
  igual y se recibe con un 'al recibir'. Lo mejor es declarar los mensajes en un solo
  archivo (mensajes.mate) y traerlo con 'usar' desde los dos programas.
- usar socio Proveedor acepta Cotizacion, SinStock (0.8): Proveedor es OTRO NEGOCIO, que
  corre su programa en otra máquina. Queda como destino de 'enviar' y como 'remitente' (no
  se le puede 'preguntar' ni 'crear', ni va adentro de un mensaje). Se le manda al negocio,
  no a un agente: del otro lado lo recibe el único agente que tiene 'al recibir' de ese
  mensaje. Después de 'acepta' van los únicos mensajes que se le reciben, y cada uno
  tiene que tener exactamente un agente que lo reciba. Los mensajes van en un archivo
  aparte (trato.mate) que cada negocio trae con 'usar'. La clave del socio NO va en el
  programa: la carga la persona con la orden 'socio'. Lo que llega de un socio no se
  entrega solo: Mate lo muestra y pregunta "¿Lo entrego?". Por eso lo que mueve plata o
  stock tiene que controlarlo además el agente (que el pedido exista, que el total
  coincida, que no esté ya hecho). Los textos de un mensaje entre negocios son cortos
  (hasta 500 letras, 8 KB en total) y no se le pasan tal cual a consultar_ia().
- usar python "ayudas.py" trae las funciones escritas con 'def' en ese archivo de Python,
  que está en la carpeta del programa (nombre en minúsculas, sin espacios). Se llaman con el
  nombre del archivo adelante:  sea r = ayudas.raiz(144)
  Solo cruzan números, textos, verdadero/falso, nada, listas y mapas, y van y vuelven
  copiados. Un error dentro del Python es un error de Mate (clase "python") que se ataja
  con 'intentar'. Sirve para lo que Mate no trae; si hace falta, hay que entregar también
  el .py, y avisar que ese Python corre con todos los permisos de la computadora.

PRUEBAS
- prueba "nombre" {{ asegurar total == 10 }}        asegurar cond, "mensaje si falla"
- asegurar falla {{ dividir(1, 0) }}                 se cumple si lo de adentro falla
  (un nombre mal escrito ahí adentro no cuenta como la falla esperada)
- simular Vendedor al recibir Pedido como p {{ responder Cotizacion {{ total: 1 }} }}
  Solo dentro de una prueba: hasta que termina, ese agente contesta eso a ese mensaje.
- mensajes_enviados() solo dentro de una prueba: la lista de lo que se mandó en esa prueba,
  en orden. Cada elemento es un mapa: numero, de y a (nombres, como textos; el programa es
  "(programa)"), tipo, mensaje, pregunta (verdadero si fue con 'preguntar'), conversacion y
  respuesta_a (el numero del mensaje que contesta, o nada). Con un tipo, solo esos:
      asegurar largo(mensajes_enviados("Pedido")) == 1
      asegurar mensajes_enviados()[0].a == "Vendedor"
- simular_ia("Sale $ 100") solo dentro de una prueba: desde ahí, consultar_ia() contesta eso.
  Con una lista las da en orden, una por consulta: simular_ia(["Hola", "Chau"]). En las
  pruebas nunca se habla con la IA de verdad.
- simular_teclado(["hola", "chau"]) solo dentro de una prueba: lo que "teclea" la persona,
  un texto por cada leer(), en orden. Cuando se acaban, leer() da su 2.º valor.
- En una prueba ningún agente tiene lecciones ni memoria: se le fijan con
  aprender("texto", Mostrador), y lecciones(Mostrador) las devuelve. consultas_ia() da la
  lista de lo que se le consultó a la IA en esa prueba; cada elemento es un mapa con agente,
  instrucciones (con las lecciones al final), pregunta y respuesta:
      asegurar tiene(ultimo(consultas_ia()).instrucciones, "texto de la lección")
  Si el agente tiene frenos, cada elemento trae además freno (qué regla rompió esa
  respuesta, o "" si pasó) y devuelto (lo que consultar_ia() le devolvió al programa); el
  segundo intento es otro elemento, y en una prueba la cuenta del tope arranca de cero:
      simular_ia("Sale $ 9.999")
      asegurar (preguntar Consulta {{ pregunta: "¿yerba?" }} a Mostrador) == "Eso te lo ..."
      asegurar tiene(consultas_ia()[0].freno, "$ 9.999")
- Van en el nivel superior y corren con la orden 'probar'. Cada una empieza limpia.

ANTES DE CORRER
- Mate revisa todo el programa y no arranca si un nombre no existe (totl por total) o si una
  función recibe valores de más o de menos, aunque sea en una parte que no se ejecuta.
  Lo declarado afuera de todo puede estar más abajo en el archivo. No revisa adentro de
  intentar {{ }} ni de asegurar falla {{ }}. Los errores salen así: archivo:renglón: error: ...
- --traza numera los mensajes y muestra cuál falló o quedó sin respuesta. Al final del
  renglón dice de qué conversación es (una por cada cosa que manda el programa) y, si es una
  respuesta, a qué mensaje contesta: (conversación 2, en respuesta al 4).
  Con 'probar', la traza de cada prueba numera desde 1, igual que mensajes_enviados().

UN PROGRAMA COMPLETO
--- ejemplo ---
mensaje Pedido {{ producto: texto, cantidad: numero }}
mensaje Cotizacion {{ producto: texto, total: numero }}

agente Vendedor {{
    estado precios = {{ yerba: 3500, azucar: 1200 }}
    estado cotizados = 0

    al recibir Pedido como p {{
        si no tiene(precios, p.producto) {{
            fallar "no vendo {{p.producto}}"
        }}
        cotizados += 1
        responder Cotizacion {{ producto: p.producto, total: precios[p.producto] * p.cantidad }}
    }}
}}

funcion total_de(pedidos) {{
    var total = 0
    para pedido en pedidos {{
        si pedido.cantidad <= 0 {{
            continuar
        }}
        intentar {{
            sea c = preguntar Pedido {{
                producto: pedido.producto, cantidad: pedido.cantidad,
            }} a Vendedor
            total += c.total
        }} si falla motivo {{
            mostrar("Se saltea: {{motivo}}")
        }}
    }}
    devolver total
}}

sea lista = [{{ producto: "yerba", cantidad: 2 }}, {{ producto: "café", cantidad: 1 }}]
mostrar("Total: {{pesos(total_de(lista))}}")

prueba "suma solo lo que el vendedor vende" {{
    asegurar total_de([{{ producto: "azucar", cantidad: 3 }}]) == 3600
    asegurar total_de([]) == 0
}}
--- fin del ejemplo ---

CÓMO SE CORRE (Windows)
  python mate\mate.py correr archivo.mate        python mate\mate.py probar archivo.mate
  python mate\mate.py verificar archivo.mate     (revisa sin correr)
  python mate\mate.py corregir archivo.mate Agente "la lección"    (le anota una lección)
  python mate\mate.py lecciones archivo.mate     python mate\mate.py bitacora archivo.mate
  python mate\mate.py propuestas archivo.mate    (las lecciones propuestas, sin aprobar)
  python mate\mate.py propuestas archivo.mate aprobar 1         (o: descartar 1)
  python mate\mate.py proponer archivo.mate Agente "qué estuvo mal"   (Mate la redacta)
  python mate\mate.py informe      (los errores de uso que Mate fue anotando en esa
  computadora, sin datos de la persona; con --para-mejorar arma un texto para pedir mejoras)
  En PowerShell el comando se escribe una sola vez por renglón, y los comandos no van
  adentro del archivo .mate: si se pegan ahí, Mate lo avisa.
  Hay computadoras donde Python se llama con py: ahí va py en lugar de python
  (py mate\mate.py correr archivo.mate). Con la orden instalada, va mate (mate correr ...).
"""


def texto_de_guia():
    return con_la_orden_de_esta_computadora(GUIA.format(
        version=VERSION, funciones=lista_de_funciones(), tres=TRES_COMILLAS,
        max_lecciones=MAX_LECCIONES))


_EJ_AGENTE = """mensaje Sumar { a: numero, b: numero }
agente Calculadora {
    estado cuentas = 0
    al recibir Sumar como s {
        cuentas += 1
        responder s.a + s.b
    }
}
sea r = preguntar Sumar { a: 2, b: 3 } a Calculadora
mostrar(r)"""
_EJ_FALLAR = """funcion dividir(a, b) {
    si b == 0 { fallar "no se puede dividir por cero" }
    devolver a / b
}
intentar {
    mostrar(dividir(1, 0))
} si falla e {
    mostrar("No anduvo: {e}")
}"""
_EJ_PRUEBA = """funcion doble(n) { devolver n * 2 }
prueba "el doble de 4 es 8" {
    asegurar doble(4) == 8
    asegurar doble(0) == 0, "el doble de cero es cero"
}"""

# La ayuda de cada palabra de Mate: qué hace y un ejemplo que se puede copiar y correr.
# (La de las funciones incluidas sale de la tabla FUNCIONES.)
AYUDA = {
    "sea": ("guarda un valor con un nombre. Es fijo: no cambia más (para que pueda "
            "cambiar va 'var')", 'sea iva = 0.21\nmostrar("El IVA es {iva}")'),
    "var": ("guarda un valor que después se puede cambiar",
            "var total = 0\ntotal = total + 10\ntotal += 5\nmostrar(total)"),
    "funcion": ("le pone nombre a unos pasos para usarlos muchas veces. 'devolver' entrega "
                "el resultado y termina la función. Un parámetro puede tener un valor por "
                "defecto (tasa = 0.21), que se usa si no le dan otro; esos van al final",
                "funcion doble(n) {\n    devolver n * 2\n}\nmostrar(doble(4))\n"
                "funcion con_iva(precio, tasa = 0.21) {\n    devolver precio * (1 + tasa)\n}\n"
                "mostrar(con_iva(100), con_iva(100, 0.5))"),
    "si": ("hace una cosa u otra según una condición, que tiene que dar verdadero o falso. "
           "'sino si' y 'sino' son opcionales y van en el renglón de la llave que cierra",
           'sea edad = 20\nsi edad >= 18 {\n    mostrar("mayor")\n} sino si edad >= 13 {\n'
           '    mostrar("adolescente")\n} sino {\n    mostrar("chico")\n}'),
    "mientras": ("repite el bloque mientras la condición sea verdadera",
                 "var n = 3\nmientras n > 0 {\n    mostrar(n)\n    n -= 1\n}"),
    "para": ("recorre una lista de a un elemento (también las claves de un mapa o las "
             "letras de un texto). Con dos nombres, el primero es la posición",
             'sea frutas = ["pera", "uva"]\npara fruta en frutas {\n    mostrar(fruta)\n}\n'
             'para i, fruta en frutas {\n    mostrar("{i}: {fruta}")\n}'),
    "romper": ("'romper' corta el bucle ('para' o 'mientras') en el que está; 'continuar' "
               "salta a la vuelta siguiente",
               'para cosa en ["pan", "", "fin", "leche"] {\n    si cosa == "" { continuar }\n'
               '    si cosa == "fin" { romper }\n    mostrar(cosa)\n}'),
    "y": ("'y', 'o' y 'no' combinan condiciones: las dos, alguna de las dos, o lo contrario",
          'sea edad = 20\nsea socio = falso\nsi edad >= 18 y no socio {\n'
          '    mostrar("puede asociarse")\n}\nsi edad < 13 o edad > 65 {\n'
          '    mostrar("entra gratis")\n}'),
    "verdadero": ("'verdadero' y 'falso' son los dos valores lógicos: lo que da una "
                  "comparación y lo que espera un 'si'",
                  'sea abierto = verdadero\nsi abierto {\n    mostrar("pasá")\n}\n'
                  "mostrar(3 > 5)"),
    "nada": ("es la falta de valor: lo que devuelve una función sin 'devolver', o un campo "
             "opcional que no vino",
             'sea precios = { yerba: 3500 }\nsea p = obtener(precios, "cafe", nada)\n'
             'si p == nada {\n    mostrar("no vendo café")\n}'),
    "lista": ("varios valores en orden, entre corchetes. Las posiciones arrancan en 0",
              'var compras = ["yerba", "pan"]\ncompras = agregar(compras, "leche")\n'
              "mostrar(compras[0], largo(compras), ultimo(compras))"),
    "mapa": ("valores con nombre, entre llaves. Las claves son siempre textos",
             'var producto = { nombre: "yerba", precio: 3500 }\nproducto.precio = 3800\n'
             'mostrar(producto.nombre, producto["precio"], claves(producto))'),
    "mensaje": ("declara el contrato de un mensaje: qué campos lleva y de qué tipo (numero, "
                "texto, logico, lista, mapa, agente, cualquiera u otro mensaje; con ? es "
                "opcional). Con 'responde' dice además qué se le contesta. Un campo puede "
                "decir qué valores acepta: 'desde 1 hasta 100', 'en [opciones]' y, al "
                "final, '= valor por defecto'",
                "mensaje Pedido {\n    producto: texto,\n"
                "    cantidad: numero desde 1 hasta 100,\n"
                '    prioridad: texto en ["baja", "media", "alta"] = "media",\n'
                "    nota: texto?\n}\n"
                'sea p = Pedido { producto: "yerba", cantidad: 2 }\n'
                "mostrar(p.producto, p.prioridad)"),
    "agente": ("alguien que recibe mensajes. Tiene su 'estado' privado, que solo él cambia, "
               "y un 'al recibir' por cada mensaje que entiende", _EJ_AGENTE),
    "recordado": ("dentro de un agente, después de 'estado': ese dato se guarda cuando el "
                  "programa termina y vuelve en la próxima corrida (queda en un archivo "
                  ".memoria.json al lado del programa). Con 'probar' no se guarda nada, y "
                  "con 'correr programa.mate --olvidar' se arranca de cero",
                  "mensaje Llego {}\nagente Mostrador {\n"
                  "    estado recordado atendidos = 0\n"
                  "    al recibir Llego {\n        atendidos += 1\n"
                  "        responder atendidos\n    }\n}\n"
                  'mostrar("Clientes hasta hoy:", preguntar Llego {} a Mostrador)'),
    "frenos": ("dentro de un agente: las reglas que Mate le revisa a cada respuesta de "
               "consultar_ia() antes de devolverla. precios (los importes que puede nombrar), "
               "prohibido (palabras que no pueden aparecer), largo (letras, como mucho), "
               "reserva (lo que contesta si la IA rompe una regla dos veces) y los topes "
               "consultas_por_dia y tokens_por_dia. Si una regla no se cumple, Mate consulta "
               "una vez más avisándole a la IA; si la rompe de nuevo, devuelve la reserva. "
               "Cada freno que salta queda en la bitácora y deja una lección propuesta "
               "(orden 'propuestas')",
               "mensaje Consulta { pregunta: texto }\nagente Mostrador {\n"
               "    estado lista = [3500, 1200]\n"
               "    frenos {\n        precios: lista\n"
               '        prohibido: ["descuento", "fiado"]\n        largo: 400\n'
               '        reserva: "Eso te lo confirma una persona, ya te paso."\n'
               "        consultas_por_dia: 100\n    }\n"
               "    al recibir Consulta como c {\n"
               '        responder consultar_ia("Atendés un almacén.", c.pregunta)\n    }\n}\n'
               'prueba "un precio inventado no llega al cliente" {\n'
               '    simular_ia("La yerba sale $ 9.999")\n'
               '    sea dicho = preguntar Consulta { pregunta: "¿Y la yerba?" } a Mostrador\n'
               '    asegurar dicho == "Eso te lo confirma una persona, ya te paso."\n'
               '    asegurar tiene(consultas_ia()[0].freno, "$ 9.999")\n}'),
    "responder": ("contesta al que mandó el mensaje y termina de atenderlo. Solo va dentro "
                  "de 'al recibir'", _EJ_AGENTE),
    "preguntar": ("le manda un mensaje a un agente y espera lo que responde. Si el agente "
                  "falla, el error llega acá y se puede atajar con 'intentar'", _EJ_AGENTE),
    "enviar": ("le manda un mensaje a un agente (o a una lista de agentes) y sigue de "
               "largo, sin esperar respuesta",
               'mensaje Aviso { nota: texto }\nagente Cartelera {\n    al recibir Aviso como a {'
               '\n        mostrar("Aviso: {a.nota}")\n    }\n}\n'
               'enviar Aviso { nota: "llegó la yerba" } a Cartelera'),
    "remitente": ("dentro de un agente, 'remitente' es quien le mandó el mensaje que está "
                  "atendiendo, y 'yo' es el propio agente",
                  "mensaje Arrancar {}\nmensaje Hola { quien: agente }\nmensaje Gracias {}\n"
                  "agente Ana {\n    al recibir Hola como h { enviar Gracias {} a remitente }\n"
                  "}\nagente Beto {\n    al recibir Arrancar { enviar Hola { quien: yo } a Ana }"
                  '\n    al recibir Gracias { mostrar("Ana me contestó") }\n}\n'
                  "enviar Arrancar {} a Beto"),
    "crear": ("hace otra copia de un agente ya declarado, con su propio estado. 'llamado' "
              "le pone nombre",
              "mensaje Cuanto {}\nagente Caja {\n    estado plata = 0\n"
              "    al recibir Cuanto { responder plata }\n}\n"
              'sea norte = crear Caja llamado "Norte" { plata: 500 }\n'
              "mostrar(preguntar Cuanto {} a norte)"),
    "fallar": ("corta lo que se está haciendo con un error que lleva ese motivo", _EJ_FALLAR),
    "intentar": ("prueba hacer algo y, si falla, sigue por el bloque de 'si falla' en vez "
                 "de cortar el programa. El nombre de después de 'falla' guarda el texto "
                 "del error", _EJ_FALLAR),
    "prueba": ("una comprobación que vive al lado del código. No corre con 'correr': corre "
               "con la orden 'probar archivo.mate'", _EJ_PRUEBA),
    "asegurar": ("comprueba que algo sea verdadero; si no lo es, falla (después de una coma "
                 "se le puede poner un texto que lo explique). 'asegurar falla { ... }' "
                 "comprueba que algo falle", _EJ_PRUEBA),
    "simular": ("solo dentro de una prueba: hasta que termina, ese agente contesta lo que "
                "diga este bloque en vez de lo suyo",
                "mensaje Precio { producto: texto }\nagente Vendedor {\n"
                "    al recibir Precio como p { responder 3500 }\n}\n"
                'prueba "con otro precio" {\n'
                "    simular Vendedor al recibir Precio como p { responder 10 }\n"
                '    asegurar preguntar Precio { producto: "yerba" } a Vendedor == 10\n}'),
    "usar": ("trae los mensajes, agentes, funciones y variables ('sea' y 'var') de otro "
             "archivo, que se busca al lado de este. (Para traer funciones escritas en "
             "Python: 'ayuda python')", 'usar "catalogo.mate"\nmostrar(iva)'),
    "buzon": ("después de 'usar': nombra OTRO programa de la misma carpeta. Sus agentes "
              "quedan como destino de 'enviar' (no se les puede 'preguntar'). El mensaje "
              "sale cuando este programa termina, queda en la carpeta deposito.buzon y se "
              "entrega, validado con el contrato, cuando corre el otro. Si el programa se "
              "corta (un error, Ctrl+C), lo que ya dejaron sus agentes sale igual, pero "
              "lo que le llegó no se atiende: avisa cuántos quedaron. Para ver qué hay "
              "en un buzón: la orden 'buzon deposito.mate'",
              "# En ventas.mate (deposito.mate está en la misma carpeta) iría:\n"
              '#     usar buzon "deposito.mate"\n'
              '#     enviar Reservar { producto: "yerba", cantidad: 2 } a Deposito\n'
              "# Y esto es deposito.mate: atiende lo que le dejaron cuando lo corren.\n"
              "mensaje Reservar { producto: texto, cantidad: numero }\n"
              "agente Deposito {\n"
              "    al recibir Reservar como r {\n"
              '        mostrar("Reservo {r.cantidad} de {r.producto}")\n'
              "    }\n}\n"
              "# (para probarlo sin el otro programa)\n"
              'enviar Reservar { producto: "yerba", cantidad: 2 } a Deposito'),
    "socio": ("después de 'usar': nombra OTRO NEGOCIO, que corre su programa en otra "
              "máquina (0.8). Queda como destino de 'enviar' y como 'remitente' (no se le "
              "puede 'preguntar'). Después de 'acepta' van los únicos mensajes que se le "
              "reciben. Los dos negocios comparten una carpeta (de OneDrive, de red o un "
              "pendrive) y una clave, que se carga con la orden 'socio invitar' de un lado "
              "y 'socio aceptar' del otro y no va nunca en el programa. Cada mensaje viaja "
              "firmado; lo que no trae la firma de ese socio no se entrega. Y lo que llega "
              "no toca nada solo: Mate lo muestra y pregunta \"¿Lo entrego?\", mensaje "
              "por mensaje. No va cifrado: quien ve la carpeta compartida lo puede leer. "
              "Para ensayarlo en una sola PC: la orden 'nuevo socio'",
              "# En comprador.mate iría, arriba:\n"
              "#     usar socio Proveedor acepta Cotizacion\n"
              "# y en un agente:\n"
              '#     enviar Pedido { producto: "yerba", cantidad: 10 } a Proveedor\n'
              "# Lo que contesta el proveedor llega, después de tu si, a este agente:\n"
              "mensaje Cotizacion { producto: texto, total: numero }\n"
              "agente Compras {\n"
              "    al recibir Cotizacion como c {\n"
              '        mostrar("Cotizaron {c.producto} en {c.total}")\n'
              "    }\n}\n"
              "# (para probarlo sin el otro negocio)\n"
              'enviar Cotizacion { producto: "yerba", total: 35000 } a Compras'),
    "python": ("después de 'usar': trae las funciones de un archivo de Python que está al "
               "lado del programa, para sumar lo que Mate no trae. Se llaman con el nombre "
               "del archivo adelante. Cruzan números, textos, verdadero/falso, nada, listas "
               "y mapas. Si el Python falla, es un error que se ataja con 'intentar'. OJO: "
               "ese Python corre con todos los permisos de la computadora (también con "
               "'probar'): usá solo archivos tuyos o de alguien de confianza",
               "# ayudas.py está al lado del programa y dice:\n"
               "#     def doble(numero):\n"
               "#         return numero * 2\n"
               'usar python "ayudas.py"\n'
               "mostrar(ayudas.doble(21))"),
    "al fallar": ("dentro de un agente: se entera cuando un mensaje que él mandó con "
                  "'enviar' no pudo atenderse. Lo que llega trae motivo, mensaje y destino. "
                  "Ahí no va 'responder'",
                  "mensaje Arrancar {}\nmensaje Pedido { producto: texto }\n"
                  "agente Deposito {\n"
                  '    al recibir Pedido como p { fallar "no hay {p.producto}" }\n}\n'
                  "agente Vendedor {\n"
                  '    al recibir Arrancar { enviar Pedido { producto: "yerba" } a Deposito }\n'
                  '    al fallar como f { mostrar("No salió: {f.motivo}") }\n}\n'
                  "enviar Arrancar {} a Vendedor"),
}
# Las funciones incluidas que piden más explicación que su renglón de la tabla (0.5): lo
# que se agrega al título y un ejemplo más largo.
AYUDA_DE_FUNCION = {
    "leer": ("El 2.º valor es lo que da cuando no hay teclado (con 'probar' nunca lo "
             "espera). Con Ctrl+C mientras espera, el programa termina ahí sin error",
             "# Una charla: sigue hasta que escriben chau.\n"
             "mientras verdadero {\n"
             '    sea dicho = leer("Cliente:", "chau")\n'
             '    si minusculas(dicho) == "chau" {\n'
             "        romper\n"
             "    }\n"
             '    mostrar("Dijiste: {dicho}")\n'
             "}"),
    "simular_teclado": ("Cuando se acaban los textos, leer() da su 2.º valor",
                        "funcion saludar() {\n"
                        '    devolver "Hola, " + leer("¿Cómo te llamás?", "nadie")\n'
                        "}\n"
                        'prueba "saluda a quien escribe" {\n'
                        '    simular_teclado(["Ana"])\n'
                        '    asegurar saludar() == "Hola, Ana"\n'
                        '    asegurar saludar() == "Hola, nadie"\n'
                        "}"),
    "leer_tabla": ("En Excel: Archivo > Guardar como > Tipo: CSV (delimitado por comas), en "
                   "la carpeta del programa. Las claves son los títulos de la primera fila. "
                   "Los números llegan como números, también 3.500, 3.500,50 y $ 3.500",
                   "# precios.csv está al lado del programa y dice:\n"
                   "#     producto;precio\n"
                   "#     Yerba;3.500\n"
                   'para fila en leer_tabla("precios.csv") {\n'
                   '    mostrar("{fila.producto} sale {pesos(fila.precio)}")\n'
                   "}"),
    "agregar_a_archivo": ("Si el archivo no existe, lo crea. Con 'probar' no toca el archivo "
                          "de verdad: lo agregado se ve con leer_archivo() en esa prueba",
                          'agregar_a_archivo("pedidos.txt", "{hoy()}: 2 de yerba")\n'
                          'agregar_a_archivo("pedidos.txt", "{hoy()}: 1 de azúcar")\n'
                          'mostrar(leer_archivo("pedidos.txt"))'),
}
# Las palabras que se explican junto con otra.
VER_AYUDA_DE = {
    "devolver": "funcion", "sino": "si", "en": "para", "continuar": "romper",
    "o": "y", "no": "y", "falso": "verdadero", "logico": "verdadero",
    "estado": "agente", "al": "agente", "recibir": "agente", "como": "agente",
    "yo": "remitente", "falla": "intentar", "llamado": "crear", "responde": "mensaje",
    "cualquiera": "mensaje", "a": "enviar",
    "freno": "frenos", "reserva": "frenos", "prohibido": "frenos", "precios": "frenos",
    "consultas_por_dia": "frenos", "tokens_por_dia": "frenos", "propuestas": "frenos",
    "proponer": "frenos",
}


def ayuda_de(palabra):
    """La ayuda de una palabra de Mate o de una función incluida (o None si no es)."""
    nombre = " ".join(sin_tildes(palabra).split())
    nombre = nombre[:-2] if nombre.endswith("()") else nombre
    nota = []
    if nombre in FUNCIONES:
        _, _, ejemplo, que = FUNCIONES[nombre]
        titulo = f"{nombre} (función incluida): {que}"
        if nombre in AYUDA_DE_FUNCION:
            titulo += ". " + AYUDA_DE_FUNCION[nombre][0]
            ejemplo = AYUDA_DE_FUNCION[nombre][1]
    else:
        tema = VER_AYUDA_DE.get(nombre, nombre)
        if tema not in AYUDA:
            return None
        que, ejemplo = AYUDA[tema]
        titulo = f"{nombre}: {que}" if tema == nombre else f"{nombre} (va con '{tema}'): {que}"
    renglones, largo = [], 0
    for parte in titulo.split(" "):  # el título, cortado para que entre en la consola
        if renglones and largo + len(parte) < 88:
            renglones[-1] += " " + parte
            largo += len(parte) + 1
        else:
            renglones.append(parte)
            largo = len(parte)
    if nombre in ("al", "fallar"):
        nota = ["", "(Dentro de un agente también existe 'al fallar': mirá 'ayuda al fallar')"]
    return "\n".join(renglones + ["", "Ejemplo:"]
                     + ["    " + r for r in ejemplo.split("\n")] + nota)


def temas_de_ayuda():
    return sorted(set(AYUDA) | set(VER_AYUDA_DE) | PALABRAS) + sorted(FUNCIONES)


def ayuda_de_palabra(palabra, mostrar, avisar):
    """'ayuda si', 'ayuda largo': muestra la explicación. Devuelve el código de salida."""
    texto = ayuda_de(palabra)
    if texto is None and PISTAS.get(palabra.lower()) and ayuda_de(PISTAS[palabra.lower()]):
        mostrar(pista_de(palabra)[0].upper() + pista_de(palabra)[1:] + ".")
        texto = ayuda_de(PISTAS[palabra.lower()])
    if texto is None and len(palabra.split()) > 1:
        # 'ayuda si falla', 'ayuda al recibir': se explica la primera palabra que tenga ayuda
        for parte in palabra.split():
            if ayuda_de(parte):
                mostrar(f"No tengo ayuda sobre '{palabra}' todo junto: la ayuda es de a una "
                        f"palabra. Esta es la de '{parte}':")
                mostrar("")
                mostrar(ayuda_de(parte))
                return 0
    if texto is None:
        avisar(f"no tengo ayuda sobre '{palabra}'.{sugerir(palabra, temas_de_ayuda())}")
        avisar("Hay ayuda de las palabras de Mate: " + ", ".join(sorted(PALABRAS)))
        avisar("y de las funciones incluidas: " + ", ".join(sorted(FUNCIONES)))
        return 2
    mostrar(texto)
    return 0


def falta_cerrar(texto):
    """En la consola: ¿quedó abierto un paréntesis, un corchete o una llave?"""
    try:
        tokens = tokenizar(texto)
    except ErrorMate as e:
        # Un texto de tres comillas sin cerrar sigue abajo (también tras un renglón vacío).
        # Lo demás está mal escrito: que lo diga el error.
        return "texto" if getattr(e, "texto_abierto", False) else False
    if sum((t[1] in _CIERRES) - (t[1] in _CIERRES.values())
           for t in tokens if t[0] == "op") > 0:
        return True
    # Como en un archivo: un renglón que termina en un operador o en una coma sigue abajo.
    if len(tokens) < 2:
        return False
    tipo, valor = tokens[-2][:2]
    if tipo == "kw":
        return valor in ("y", "o")
    if tipo != "op" or valor not in _SIGUEN:
        return False
    # (salvo '21%': eso no sigue abajo, es un porcentaje mal escrito y lo dice el error)
    return not (valor == "%" and len(tokens) > 2 and tokens[-3][0] == "num")


_SIGUEN = COMPARADORES + ("+", "-", "*", "/", "%", "=", "+=", "-=", ",")


def renglon_duplicado(renglon):
    """En la consola: si el renglón es el mismo texto pegado dos (o tres) veces seguidas,
    sin nada en el medio, devuelve ese texto una sola vez. Si no, None."""
    texto = renglon.strip()
    for veces in (3, 2):
        largo, resto = divmod(len(texto), veces)
        if not resto and largo >= 4 and texto == texto[:largo] * veces \
                and any(c.isalpha() for c in texto[:largo]):
            return renglon_duplicado(texto[:largo]) or texto[:largo]
    return None


def consola(entrada=None, mostrar=print, ia_simulada=False, ia_respuestas=(), anotar=None):
    """La orden 'consola': para probar renglones sueltos sin crear un archivo. Lo que se
    declara queda para los renglones siguientes, y un valor suelto se muestra solo.
    ia_simulada: con --ia-simulada, consultar_ia() tampoco sale a la red desde acá.
    anotar: a quién avisarle de cada error mostrado (el registro de errores de uso)."""
    anotar = anotar or (lambda *_a, **_k: None)
    interprete = Interprete(salida=mostrar)
    interprete.en_consola = True
    interprete.ia_simulada = bool(ia_simulada)
    interprete.ia_respuestas = list(ia_respuestas)
    interprete.glob.se_pisa = True  # acá se puede volver a declarar algo para corregirlo
    if entrada is not None:
        interprete.entrada = entrada  # (en las pruebas: de ahí saca leer() su respuesta)
    entrada = entrada or input
    mostrar(f"Mate {VERSION}, consola. Escribí un renglón y apretá Enter; para terminar, salir")
    mostrar("(un valor suelto, como 2 + 3, se muestra solo; 'ayuda si' explica una palabra)")
    declarado = []  # lo ya declarado, para revisar los contratos de lo que se escriba
    renglon, pendiente = 1, []  # los renglones se numeran de corrido, como en un archivo

    def decir(linea, texto, ultimo, familia=None):
        anotar(texto, familia=familia or getattr(texto, "familia", None))
        texto, _, camino = texto.partition("\ncómo se llegó: ")
        antes = f"línea {linea}: " if linea and int(linea) != ultimo else ""
        mostrar(f"{antes}error: {texto}")
        if camino:
            mostrar(f"    cómo se llegó: {camino}")

    def correr_pedazo(fuente, ultimo):
        try:
            programa = analizar(fuente, en_consola=True)
            se_declaran = [s for s in programa
                           if s[0] in ("sea", "funcion", "agente", "mensaje",
                                       "usar_python")]
            nuevos = {s[2] for s in se_declaran}
            previo = [s for s in declarado if s[2] not in nuevos]
            errores = verificar(previo + programa, en_consola=True)
            if errores:
                for linea, texto in errores:
                    decir(linea, texto, ultimo)
                return
            declarado[:] = previo + se_declaran
            suelto = len(programa) == 1 and programa[0][0] == "expr"
            if suelto:  # un valor suelto se guarda un momento para poder mostrarlo
                programa = [("sea", programa[0][1], "_", programa[0][2], False)]
            interprete.pasos = interprete.entregados = 0
            interprete.glob.vars.pop("_", None)
            interprete.correr(programa)
            if any(s[0] == "prueba" for s in programa):
                mostrar("(las pruebas no corren en la consola: guardalas en un archivo y "
                        "usá la orden 'probar')")
            if suelto:
                valor = interprete.glob.vars.pop("_")[0]
                if isinstance(valor, (Funcion, Nativa)):
                    mostrar(f"error: a '{valor.nombre}' le faltan los paréntesis: "
                            f"{valor.nombre}(...)")
                elif valor is not None:
                    mostrar(formato(valor, False))
        except ErrorMate as e:
            for linea, texto in interprete.errores_agentes_det:
                decir(linea, texto, ultimo)
            interprete.errores_agentes, interprete.errores_agentes_det = [], []
            # (acá no hay archivo: lo que se terminó es lo que escribió la persona)
            e.mensaje = e.mensaje.replace(
                "no esperaba el final del archivo acá",
                "lo que escribiste quedó a medio terminar: falta algo al final").replace(
                "el final del archivo", "el final de lo que escribiste")
            decir(e.linea, interprete.con_camino(e.mensaje, e), ultimo, e.familia)
            avisar_pendientes(interprete, mostrar)
            interprete.cola.clear()
        except KeyboardInterrupt:
            mostrar("cortado con Ctrl+C (la consola sigue abierta)")
            interprete.cola.clear()
        for linea, texto in interprete.errores_agentes_det:
            decir(linea, texto, ultimo)
        interprete.errores_agentes, interprete.errores_agentes_det = [], []

    while True:
        try:
            linea = entrada(f"{renglon + len(pendiente):>3}{'.' if pendiente else '>'} ")
        except (EOFError, KeyboardInterrupt):
            mostrar("")
            break
        except UnicodeError:  # una entrada redirigida, con letras en otra codificación
            mostrar("error: ese renglón trae una letra que no pude entender (una tilde o una "
                    "ñ en otra codificación): escribilo de nuevo")
            continue
        orden = linea.strip().lower()
        if not pendiente:
            if orden in ("salir", "chau", "exit", "quit"):
                break
            if not orden:
                continue
            una_vez = renglon_duplicado(linea)
            if una_vez:
                texto = ("parece que el renglón se pegó dos veces. Escribilo una sola vez:  "
                         + una_vez)
                anotar("parece que el renglón se pegó dos veces (y Mate mostró el renglón "
                       "bien escrito)", categoria="renglón pegado dos veces", sugerencia=True)
                mostrar(f"error: {texto}")
                continue
            if pegado_de_powershell(linea):
                texto = ("eso es de PowerShell, y acá adentro (en la consola de Mate) van "
                         "renglones de Mate. Para volver a PowerShell escribí salir, y pegá "
                         "el comando allá")
                anotar(texto, categoria="un comando de PowerShell en la consola de Mate")
                mostrar(f"error: {texto}")
                continue
            if orden == "ayuda":
                mostrar("Escribí un renglón de Mate y apretá Enter. Si queda una llave "
                        "abierta (o el renglón termina en + , =), seguís en el de abajo.")
                mostrar("'ayuda si' o 'ayuda largo' explican una palabra o una función. "
                        "Para terminar: salir")
                continue
            if orden.startswith("ayuda ") and all(p.isalpha() or p.endswith("()")
                                                  for p in orden.split()[1:]):
                ayuda_de_palabra(" ".join(orden.split()[1:]), mostrar, mostrar)
                continue
        # Sigue abajo si quedó algo abierto (un renglón vacío corta y muestra el error).
        falta = falta_cerrar("\n".join(pendiente + [linea]))
        if (orden and falta) or falta == "texto":
            pendiente.append(linea)
            continue
        fuente = "\n" * (renglon - 1) + "\n".join(pendiente + [linea])
        renglon += len(pendiente) + 1
        pendiente = []
        # (el último renglón con algo escrito: un error ahí no hace falta decir dónde está)
        correr_pedazo(fuente, fuente.rstrip().count("\n") + 1)
    return 0


# ─────────────────────── El curso: aprender Mate desde cero (0.5) ───────────────────────
# Al lado de mate.py, en la carpeta 'curso', hay una clase por archivo: clase_01_hola.md es
# el texto para leer (se abre con el Bloc de notas) y clase_01_hola.mate, el programa de
# esa clase. La orden 'curso' las lista y dice cómo abrir cada una; 'curso 3' muestra la
# clase 3 en la pantalla. Solo lee esos archivos: no corre nada ni escribe nada.
CARPETA_DEL_CURSO = "curso"
_ARCHIVO_DE_CLASE = re.compile(r"clase_(\d\d)_[a-z0-9_]+\.md")


def carpeta_del_curso():
    """La carpeta del curso: siempre al lado de mate.py."""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), CARPETA_DEL_CURSO)


def clases_del_curso(carpeta=None):
    """Las clases que hay en la carpeta del curso, en orden: una lista de mapas con numero,
    titulo (el primer renglón escrito del texto), texto (la ruta del .md) y programa (la
    ruta del .mate de esa clase, o None si no está). Si la carpeta no existe, nada."""
    carpeta = carpeta_del_curso() if carpeta is None else os.fspath(carpeta)
    try:
        nombres = sorted(os.listdir(carpeta))
    except OSError:
        return []
    clases = []
    for nombre in nombres:
        es_clase = _ARCHIVO_DE_CLASE.fullmatch(nombre)
        if not es_clase:
            continue
        ruta = os.path.join(carpeta, nombre)
        try:
            renglones = leer_fuente(ruta).split("\n")
        except (OSError, ErrorMate):
            continue
        titulo = next((r.strip().lstrip("#").strip() for r in renglones if r.strip()), nombre)
        programa = ruta[:-len(".md")] + ".mate"
        clases.append({"numero": int(es_clase.group(1)), "titulo": titulo, "texto": ruta,
                       "programa": programa if os.path.isfile(programa) else None})
    return clases


def ruta_para_escribir(ruta):
    """Una ruta como conviene escribirla en una orden desde la carpeta donde está parada
    la persona: corta (mate\\curso\\...) si queda adentro de esa carpeta, completa si no,
    y entre comillas si trae espacios."""
    completa = os.path.abspath(ruta)
    try:
        corta = os.path.relpath(completa)
    except ValueError:  # (en Windows, cuando está en otro disco)
        corta = completa
    return para_pegar(completa if corta.startswith("..") else corta)


def clase_para_esta_carpeta(texto, carpeta):
    """El texto de una clase con sus comandos escritos para la carpeta donde está parada
    la persona. Las clases dicen 'python mate\\mate.py correr mate\\curso\\clase_01_hola.mate',
    que solo sirve parado al lado de la carpeta mate (y sin la orden corta). Desde otro
    lado, o con la orden 'mate' instalada, se reescriben la orden y las rutas para que se
    puedan copiar tal cual. Parado donde las clases suponen, el texto queda como está."""
    de_mate = os.path.dirname(os.path.abspath(carpeta))
    orden = como_se_llama()
    al_lado = os.path.normcase(os.path.abspath(os.getcwd())) == os.path.normcase(
        os.path.dirname(de_mate))
    if al_lado and orden != "mate" and os.path.basename(de_mate) == "mate" \
            and os.path.basename(os.path.abspath(carpeta)) == CARPETA_DEL_CURSO:
        return con_la_orden_de_esta_computadora(texto)
    if orden != "mate":
        orden = ("py " if orden.startswith("py ") else "python ") + ruta_para_escribir(
            os.path.join(de_mate, "mate.py"))

    def ruta(m):
        partes = [p for p in m.group(1).split("\\") if p]
        donde = os.path.join(carpeta, *partes[1:]) if partes[0] == CARPETA_DEL_CURSO \
            else os.path.join(de_mate, *partes)
        return ruta_para_escribir(donde)

    texto = texto.replace("python mate\\mate.py", orden)
    texto = re.sub(r"(?<![\w\\.])mate\\((?:curso|ejemplos|README\.md|MEJORAS\.md)"
                   r"(?:\\[\w.\-]+)*)", ruta, texto)
    return ("(Los comandos de esta clase están escritos para la carpeta donde estás parado "
            "ahora:\nse pueden copiar tal cual.)\n\n" + texto)


def orden_curso(args, avisar, carpeta=None, mostrar=print):
    """La orden 'curso': sin nada más, lista las clases y dice cómo abrir cada una; con un
    número, muestra esa clase. Devuelve el código de salida."""
    carpeta = carpeta_del_curso() if carpeta is None else os.fspath(carpeta)
    clases = clases_del_curso(carpeta)
    if not clases:
        avisar(f"no encuentro las clases del curso: tendrían que estar en {para_pegar(carpeta)}"
               " (la carpeta 'curso', al lado de mate.py). Si copiaste solo mate.py, bajá "
               "Mate de nuevo con todas sus carpetas",
               "al escribir la orden: no está la carpeta del curso")
        return 2
    numeros = [c["numero"] for c in clases]
    if numeros == list(range(numeros[0], numeros[-1] + 1)) and len(numeros) > 1:
        numeros = f"del {numeros[0]} al {numeros[-1]}"
    else:
        numeros = ", ".join(str(n) for n in numeros)
    if len(args) > 1 or (args and not (args[0].isascii() and args[0].isdigit()
                                       and len(args[0]) <= 4)):
        avisar(f"después de 'curso' va solo el número de la clase ({numeros}) y recibió "
               f"'{' '.join(args)}'. Por ejemplo:  {como_se_llama()} curso {clases[0]['numero']}",
               "al escribir la orden: 'curso' con algo que no es un número de clase")
        return 2
    if args:
        elegida = [c for c in clases if c["numero"] == int(args[0])]
        if not elegida:
            avisar(f"el curso no tiene una clase {int(args[0])}: van {numeros}. "
                   f"Para ver la lista:  {como_se_llama()} curso",
                   "al escribir la orden: 'curso' con un número de clase que no existe")
            return 2
        mostrar(clase_para_esta_carpeta(leer_fuente(elegida[0]["texto"]).rstrip("\n"),
                                        carpeta))
        return 0
    primera = clases[0]
    mostrar(f"El curso de Mate: {len(clases)} clases cortas, para hacer en orden. No hace falta "
            "saber programar.")
    mostrar("Cada clase es un texto para leer (termina en .md) y un programa para correr "
            "(termina en .mate).")
    mostrar("")
    ancho = max(len(re.sub(r"^Clase \d+:\s*", "", c["titulo"])) for c in clases)
    for clase in clases:
        titulo = re.sub(r"^Clase \d+:\s*", "", clase["titulo"])
        mostrar(f"  {clase['numero']:>2}. {titulo.ljust(ancho)}   "
                f"{os.path.basename(clase['texto'])}")
    mostrar("")
    mostrar(f"Para leer la clase {primera['numero']} acá mismo (las demás, con su número):")
    mostrar(f"  {como_se_llama()} curso {primera['numero']}")
    mostrar("Para abrirla con el Bloc de notas (las demás, con el nombre de su archivo):")
    mostrar(f"  notepad {ruta_para_escribir(primera['texto'])}")
    if primera["programa"]:
        mostrar("Para correr el programa de esa clase:")
        mostrar(f"  {como_se_llama()} correr {ruta_para_escribir(primera['programa'])}")
    mostrar("")
    mostrar(f"Todo está en la carpeta {ruta_para_escribir(carpeta)}. Ahí también hay un "
            "README.md que cuenta cómo")
    mostrar("hacer el curso. Ninguna clase necesita clave ni internet.")
    return 0


# ───────────────────────── La orden 'nuevo mostrador' (0.6) ─────────────────────────
# 'nuevo mostrador mi_negocio' crea, en la carpeta donde está parada la persona, un
# mostrador propio listo para usar: mi_negocio.mate y mi_negocio_precios.csv. Nunca pisa
# un archivo que ya esté.
# De dónde sale: Mate se reparte como una carpeta, así que la lógica NO está copiada acá.
# El programa se arma con el ejemplo 12_mostrador_con_reglas.mate (lo que hay entre sus
# títulos "La regla del envío" y "Las pruebas"): un arreglo en el ejemplo llega solo a los
# mostradores que se creen después. La planilla es la de muestra de los ejemplos. Acá
# quedan solo el encabezado, escrito para quien no programa, y unas pruebas que no
# dependen de la planilla (las del ejemplo nombran los productos de muestra).
CARPETA_DE_EJEMPLOS = "ejemplos"
EJEMPLO_DEL_MOSTRADOR = "12_mostrador_con_reglas.mate"
PLANILLA_DE_MUESTRA = "precios.csv"
CASOS_DE_MUESTRA = "casos.txt"  # los casos para la orden 'ensayar' (más abajo)
_MOSTRADOR_DESDE = "\n# La regla del envío:"
_MOSTRADOR_HASTA = "\n# ── Las pruebas"
_CASOS_DESDE = "# Cómo se escribe"  # (en casos.txt: de ahí para abajo se copia tal cual)
# (nombres de archivo que Windows no deja usar)
_NOMBRES_DE_WINDOWS = ("con", "prn", "aux", "nul") + tuple(
    f"{p}{n}" for p in ("com", "lpt") for n in range(1, 10))

_ENCABEZADO_DEL_MOSTRADOR = """\
# «PROGRAMA»: el mostrador de tu negocio.
# Lo creó la orden 'nuevo mostrador' de Mate, a partir del ejemplo
# 12_mostrador_con_reglas.mate. Es tuyo: lo podés cambiar todo lo que quieras.
#
# QUÉ HACE. Atiende consultas por teclado. Cuando el cliente pide una CANTIDAD de un
# PRODUCTO de la planilla ("quiero 12 azucar con envio"), contesta el programa solo: el
# total, el stock y la regla del envío. No consulta a la IA, así que no gasta y no se
# equivoca con la cuenta. Tampoco consulta a la IA cuando preguntan por un DATO DEL
# NEGOCIO (el horario, la dirección, el teléfono, cómo se paga, las entregas, las
# promociones): contesta con lo que vos cargaste, tal cual; y si no lo cargaste, NO LO
# INVENTA: contesta "eso te lo confirma una persona".
# Todo lo demás (saludar, contar qué hay) lo contesta la IA, con frenos para que no
# invente precios. A lo que contesta, el programa le mira además que no nombre un día,
# una hora, una dirección, un teléfono, una forma de pago, una entrega o una promoción
# que no cargaste: si lo nombra, esa respuesta no le llega al cliente.
# OJO: esa revisión va por palabras. Ataja lo más común, NO TODO: un modelo puede decir
# un dato de una manera que no está prevista. Por eso conviene CARGAR TUS DATOS (con el
# dato cargado, si la IA dice otra cosa, al cliente le llega el tuyo) y ENSAYAR con tu
# modelo de verdad antes de dejarlo atender.
#
# QUÉ PODÉS CAMBIAR SIN SABER PROGRAMAR:
#   1. Tus productos. Están en la planilla que está al lado de este archivo:
#          «PLANILLA»
#      Abrila con Excel o con el Bloc de notas. El primer renglón son los títulos, y va
#      una sola vez:
#          producto;presentacion;precio;stock
#      Abajo va un renglón por producto. El cliente nombra cada producto por la PRIMERA
#      palabra de su nombre ("yerba", "azúcar"): conviene que sea la que lo distingue.
#   2. Desde cuántas unidades hay envío: el número de unidades_para_envio, acá abajo.
#   3. LOS DATOS DE TU NEGOCIO: el horario, la dirección, el teléfono, las formas de pago,
#      las entregas y las promociones. Están acá abajo, en datos_del_negocio: escribí
#      cada uno entre las comillas. Vienen VACÍOS: mientras estén vacíos, a quien
#      pregunte se le contesta "eso te lo confirma una persona". Al arrancar, el
#      mostrador muestra cuáles están cargados y cuáles no.
#   4. Cómo se presenta el negocio: el texto que empieza con "Atendés el mostrador".
#   5. Lo que la IA no puede decir nunca: las palabras de 'prohibido', dentro de 'frenos'.
#   6. Las palabras con las que tus clientes preguntan por el horario, la dirección y
#      los demás datos: están en temas_del_negocio(). Van en minúsculas y sin tildes.
#      Y las que se le miran a la respuesta de la IA: en palabras_de_dias() y las listas
#      que le siguen. Si tu modelo inventa algo con otra palabra, se agrega ahí.
#
# CÓMO SE USA, en PowerShell, parado en la carpeta donde está este archivo:
#   Para comprobar que quedó todo bien (hacelo cada vez que cambies algo):
#          «ORDEN» probar «PROGRAMA»
#   Para charlar con el mostrador sin gastar nada (no hace falta clave ni internet):
#          «ORDEN» correr «PROGRAMA» --ia-simulada
#   Para atender con la IA de verdad:
#          «ORDEN» correr «PROGRAMA»
#   Para salir de la charla, escribí chau.
#   Para ensayarlo: Mate le hace las preguntas anotadas en «CASOS» (se abre con el Bloc
#   de notas) y dice cuáles contestó bien. Sirve para saber si una lección funcionó:
#          «ORDEN» ensayar «PROGRAMA» «CASOS» --ia-simulada
#   OJO: los casos que vienen en «CASOS» son de muestra, escritos para la planilla de
#   muestra (yerba, azúcar, fideos) y con los datos del negocio VACÍOS. Cuando pongas
#   tus productos en la planilla o cargues tus datos, cambiá también los casos: si no,
#   fallan los que nombran un producto que ya no está o esperan un dato sin cargar.
#
# Las pruebas del final usan una lista fija, no tu planilla: siguen pasando aunque cambies
# los productos, los precios o el número del envío. Una sola mira tu planilla, para
# avisarte si quedó algo mal cargado.
# Si en la planilla queda un precio o un stock vacío o con letras, el mostrador no atiende:
# al arrancar dice de qué producto es y cómo arreglarlo.
"""

_PRUEBAS_DEL_MOSTRADOR = """\
# ── Las pruebas ──────────────────────────────────────────────────────────────────────
# Corren con la orden 'probar'. Usan la lista fija de acá abajo y no tu planilla: así
# siguen pasando aunque cambies los productos y los precios. La IA nunca es de verdad:
# simular_ia() fija lo que "contesta", y consultas_ia() cuenta cuántas veces se la consultó.

# La lista de las pruebas (con mucho stock, para que alcance con cualquier regla de envío).
funcion lista_de_prueba() {
    devolver [{ producto: "Yerba mate", presentacion: "bolsón de 10 paquetes de 1 kg", precio: 35000, stock: 100000 },
              { producto: "Azúcar", presentacion: "bolsa de 10 kg", precio: 9800.5, stock: 100000 },
              { producto: "Fideos secos", presentacion: "caja de 20 paquetes de 500 g", precio: 18900, stock: 0 }]
}

prueba "tu planilla está bien cargada" {
    # La única prueba que mira «PLANILLA»: si falla, el texto dice qué arreglar.
    # Es lo mismo que el mostrador revisa al arrancar: los títulos, y que cada producto
    # tenga su precio y su stock en números (una celda vacía no es un número).
    sea a_corregir = revisar_planilla(precios)
    si a_corregir != nada {
        fallar(a_corregir)
    }
    # Y mira lo que cargaste arriba, en datos_del_negocio: que cada dato sea un texto
    # entre comillas (un teléfono también: sin comillas, Mate lo toma por una cuenta) y
    # que el nombre de cada dato siga como vino, en minúsculas y sin tilde.
    sea mal_escrito = datos_mal_puestos(datos_del_negocio)
    si mal_escrito != nada {
        fallar(mal_escrito)
    }
    # Y que ningún renglón de tu planilla se parezca a un dato del negocio: el renglón de
    # la lista, dicho como lo arma el programa ("Jabón (3x2)"), no cuenta como inventado.
    # No se conoce ninguno que se frene; si igual apareciera, acá te enterás antes que el cliente.
    sea frenados = renglones_frenados(precios)
    si frenados != nada {
        fallar(frenados)
    }
}

prueba "la cuenta la hace el programa, no la IA" {
    # Aunque la IA "quiera" contestar mal, nadie le pregunta.
    simular_ia("Son $ 10,80.")
    asegurar atender(lista_de_prueba(), "quiero 3 azucar") == "3 x Azúcar (bolsa de 10 kg) a $ 9.800,50 cada uno: total $ 29.401,50."
    asegurar largo(consultas_ia()) == 0
}

prueba "el envío sale desde las unidades de la regla, y sin consultar a la IA" {
    sea n = unidades_para_envio
    asegurar termina_con(atender(lista_de_prueba(), "quiero {n} azucar con envio"), "Con envío: sí, va con envío.")
    asegurar termina_con(atender(lista_de_prueba(), "me mandas {n + 5} yerbas?"), "Con envío: sí, va con envío.")
    # Con una unidad menos no hay envío (si la regla es desde 1, no hay "una menos").
    si n > 1 {
        asegurar tiene(atender(lista_de_prueba(), "me mandas {n - 1} yerbas?"), "Sin envío: hacemos envíos desde {n} unidades y pedís {n - 1}.")
    }
    asegurar largo(consultas_ia()) == 0
}

prueba "si dice que NO quiere envío, no se le confirma un envío" {
    sea n = unidades_para_envio
    para dicho en ["{n} azucar sin envio", "{n} azucar, no me lo mandes", "{n} azucar, el envio no hace falta"] {
        # (va solo el total: la respuesta no habla de envío)
        asegurar termina_con(atender(lista_de_prueba(), dicho), "total {pesos(n * 9800.5)}.")
    }
    # Tampoco si el producto tiene un "sin" en el nombre: el "sin envío" es del cliente.
    sea sin_palo = [{ producto: "Yerba sin palo", presentacion: "bolsón", precio: 2000, stock: 100000 }]
    para dicho en ["{n} yerbas sin envio", "{n} yerba sin palo sin flete", "{n} yerbas, no me las mandes"] {
        asegurar termina_con(atender(sin_palo, dicho), "total {pesos(n * 2000)}.")
    }
    asegurar termina_con(atender(sin_palo, "{n} yerba sin palo con envio"), "Con envío: sí, va con envío.")
    asegurar largo(consultas_ia()) == 0
}

prueba "no vende lo que no hay" {
    asegurar atender(lista_de_prueba(), "quiero 3 fideos") == "De Fideos secos ahora no hay stock."
    asegurar atender(lista_de_prueba(), "quiero 200000 yerbas") == "De Yerba mate quedan 100000; no llego a 200000."
}

prueba "ante la duda pregunta, no elige por el cliente" {
    asegurar empieza_con(atender(lista_de_prueba(), "quiero 2 yerbas y 3 azucar"), "Vamos de a un producto por vez")
    asegurar empieza_con(atender(lista_de_prueba(), "quiero 2 o 3 yerbas"), "Veo más de un número")
    asegurar empieza_con(atender(lista_de_prueba(), "quiero 1 kg de yerba"), "Yerba mate se vende por")
    asegurar largo(consultas_ia()) == 0
}

prueba "lo que no es un pedido va a la IA, y un precio inventado no le llega al cliente" {
    enviar CargarLista { precios: lista_de_prueba() } a Mostrador
    simular_ia("¡Hola! Tenemos yerba y azúcar.")
    asegurar atender(lista_de_prueba(), "hola, ¿qué tienen?") == "¡Hola! Tenemos yerba y azúcar."
    # Un precio que no está en la lista: salta el freno y llega la reserva.
    simular_ia("El café sale $ 12.000.")
    asegurar no tiene(atender(lista_de_prueba(), "¿y café?"), "12.000")
}

prueba "el horario, la dirección o cómo se paga los contesta el programa: sin cargar, no se inventan" {
    # (con datos fijos, no con los tuyos: así pasa aunque cargues tu horario)
    sea vacios = {}
    # Aunque la IA "quiera" inventar un horario, nadie le pregunta.
    simular_ia("Atendemos de lunes a viernes de 8 a 18 hs.")
    para dicho en ["hola, que horarios tienen?", "¿A qué hora abren?", "hasta que hora estan abiertos?"] {
        asegurar atender(lista_de_prueba(), dicho, vacios) == "Sobre el horario: eso te lo confirma una persona.", dicho
    }
    asegurar atender(lista_de_prueba(), "¿dónde quedan?", vacios) == "Sobre la dirección: eso te lo confirma una persona."
    asegurar atender(lista_de_prueba(), "me pasás un teléfono?", vacios) == "Sobre el teléfono: eso te lo confirma una persona."
    asegurar atender(lista_de_prueba(), "aceptan tarjeta?", vacios) == "Sobre las formas de pago: eso te lo confirma una persona."
    asegurar atender(lista_de_prueba(), "cuanto demora la entrega?", vacios) == "Sobre las entregas: eso te lo confirma una persona."
    asegurar atender(lista_de_prueba(), "tienen alguna promo?", vacios) == "Sobre las promociones: eso te lo confirma una persona."
    # Un dato cargado se dice tal cual está escrito. Tampoco se consulta a la IA.
    sea cargados = { horario: "Lunes a viernes de 8 a 17", formas_de_pago: "Efectivo o transferencia" }
    asegurar atender(lista_de_prueba(), "hola, que horarios tienen?", cargados) == "Horario: Lunes a viernes de 8 a 17."
    asegurar atender(lista_de_prueba(), "aceptan tarjeta?", cargados) == "Formas de pago: Efectivo o transferencia."
    asegurar atender(lista_de_prueba(), "horario y direccion?", cargados) == "Horario: Lunes a viernes de 8 a 17. Sobre la dirección: eso te lo confirma una persona."
    # Un teléfono SIN comillas no se dice: Mate toma 4555-1234 por una resta (da 3321).
    # Cuenta como vacío, y la prueba de la planilla dice qué arreglar.
    sea sin_comillas = { telefono: 4555 - 1234 }
    asegurar atender(lista_de_prueba(), "cual es el telefono?", sin_comillas) == "Sobre el teléfono: eso te lo confirma una persona."
    asegurar tiene(datos_mal_puestos(sin_comillas), "el dato 'telefono' está sin comillas")
    # El nombre de un dato cambiado ("Horario", con mayúscula) también se avisa.
    asegurar tiene(datos_mal_puestos({ Horario: "8 a 17" }), "tiene que quedar escrito 'horario'")
    asegurar largo(consultas_ia()) == 0
}

prueba "si la IA igual inventa un horario, un teléfono o una forma de pago, no le llega al cliente" {
    enviar CargarLista { precios: lista_de_prueba() } a Mostrador
    sea vacios = {}
    # La pregunta no nombra el horario, así que va a la IA; y la IA lo inventa.
    para inventada en ["¡Hola! Atendemos de lunes a viernes de 8 a 18hs.", "Abrimos a las 9.",
                       "Llamanos al 11 4555-1234.", "Podés pagar con tarjeta.",
                       "Te lo entregamos en 48 hs.", "Estamos en Av. Mitre 1234."] {
        simular_ia(inventada)
        asegurar termina_con(atender(lista_de_prueba(), "hola", vacios), ": eso te lo confirma una persona."), inventada
    }
    # Con el dato cargado, lo que coincide pasa; lo que no, se cambia por el dato.
    sea cargados = { horario: "Lunes a viernes de 8 a 17" }
    simular_ia("¡Hola! Atendemos de lunes a viernes de 8 a 17.")
    asegurar atender(lista_de_prueba(), "hola", cargados) == "¡Hola! Atendemos de lunes a viernes de 8 a 17."
    simular_ia("¡Hola! Atendemos de lunes a sábado de 8 a 20.")
    asegurar atender(lista_de_prueba(), "hola", cargados) == "Horario: Lunes a viernes de 8 a 17."
}

prueba "una hora inventada no le llega al cliente, la escriba como la escriba" {
    enviar CargarLista { precios: lista_de_prueba() } a Mostrador
    para inventada en ["Abrimos desde las 8 hasta las 18.", "Podés pasar hasta las 18.",
                       "Atendemos entre las 9 y las 18.", "Abrimos a partir de las 9.",
                       "Abrimos 8 a 18.", "Horario: 8-18.", "Horario: 08.00 a 18.00.",
                       "Abrimos a las nueve.", "Estamos de ocho a seis de la tarde.",
                       "Atendemos de ocho a dieciocho, de lun a vie.",
                       "Abrimos 8.30 y cerramos 18.00.", "Atendemos todos los días.",
                       "Estamos de corrido, mañana y tarde.", "Pasá al mediodía.",
                       "Hoy estamos abiertos hasta tarde.", "Atendemos las 24 horas.",
                       "Podés pasar hasta las 18, estamos todos los días."] {
        asegurar dato_inventado({}, inventada, lista_de_prueba()) == "horario", inventada
        simular_ia(inventada)
        asegurar atender(lista_de_prueba(), "hola", {}) == "Sobre el horario: eso te lo confirma una persona.", inventada
    }
}

prueba "una dirección, un contacto, un pago, una entrega o una promoción inventados tampoco llegan" {
    sea inventadas = {
        direccion: ["Te esperamos en Av. Corrientes 1234.", "Estamos sobre Rivadavia al 5000.",
                    "Estamos sobre la calle Corrientes al 3000.", "Estamos en Lanús."],
        telefono: ["Escribinos a ventas@mayorista.com.ar.", "Seguinos en Instagram @mayorista.",
                   "Llamanos al 4444.5555.", "Llamanos al 444-5555.", "El número es (011) 4555-1234.",
                   "Mirá los precios en www.mayorista.com"],
        formas_de_pago: ["Podés pagar con Visa o Mastercard.", "Aceptamos todos los medios de pago.",
                         "Se paga con MODO o Cuenta DNI.", "Tenemos billeteras virtuales y dólares."],
        entregas: ["Hacemos envíos a todo el país.", "Te llega mañana mismo.", "Entregamos en el día.",
                   "Entregamos en una semana.", "Te lo entregamos mañana mismo en CABA.",
                   "Lo tenés en 48 hs.", "Sale en dos horas."],
        promociones: ["El envío es gratis.", "Tenemos 2x1 en yerba.", "Llevando 10 te regalamos 1.",
                      "Hoy la yerba está 2x1.", "Hoy hay 10% menos."]
    }
    para clave, frases en inventadas {
        para inventada en frases {
            asegurar dato_inventado({}, inventada, lista_de_prueba()) == clave, inventada
        }
    }
    # Y al cliente le llega lo que el programa sabe de ese tema: que lo confirma una persona.
    enviar CargarLista { precios: lista_de_prueba() } a Mostrador
    simular_ia("Escribinos a ventas@mayorista.com.ar.")
    asegurar atender(lista_de_prueba(), "hola", {}) == "Sobre el teléfono: eso te lo confirma una persona."
}

prueba "una respuesta que no nombra ningún dato del negocio pasa como está" {
    enviar CargarLista { precios: lista_de_prueba() } a Mostrador
    para buena en ["¡Hola! Tenemos yerba, azúcar y harina.", "Cualquier cosa, estamos en contacto.",
                   "Viene en bolsas de 10 a 25 kg.", "Vendemos de 1 a 100 unidades.",
                   "Podés llevar de 10 a 20 unidades.", "Tenemos una amplia oferta de productos.",
                   "Buenos días, ¿en qué te ayudo?", "Buenas tardes. Decime cuántas unidades querés.",
                   "Llevá 2 o 3 bolsones.", "Las 2 yerbas que tenemos son buenas.",
                   "De ese modo te sale mejor.", "El aceite viene en caja de 12 botellas de 1.5 l.",
                   "Sí, tenemos fideos secos (caja de 20 paquetes de 500 g) a $ 18.900,00."] {
        asegurar dato_inventado({}, buena, lista_de_prueba()) == nada, buena
    }
    simular_ia("Viene en bolsas de 10 a 25 kg.")
    asegurar atender(lista_de_prueba(), "hola", {}) == "Viene en bolsas de 10 a 25 kg."
    # El nombre de un producto de la planilla no es un dato inventado, aunque tenga una
    # palabra de las que se miran.
    sea con_promo = [{ producto: "Promo yerba y azúcar", presentacion: "caja", precio: 40000, stock: 5 }]
    asegurar dato_inventado({}, "Tenemos la Promo yerba y azúcar.", con_promo) == nada
    asegurar dato_inventado({}, "Tenemos la Promo yerba y azúcar.", lista_de_prueba()) == "promociones"
    # Ni una presentación escrita "12 x 900" o "8.30": no es una promoción ni un horario.
    sea con_equis = [{ producto: "Aceite", presentacion: "caja 12 x 900 ml", precio: 31200, stock: 5 },
                     { producto: "Cinta", presentacion: "pack 8.30 cm", precio: 5000, stock: 5 }]
    asegurar dato_inventado({}, "Aceite (caja 12 x 900 ml): $ 31.200,00", con_equis) == nada
    asegurar dato_inventado({}, "El aceite viene en caja de 12 x 900 ml.", con_equis) == nada
    asegurar dato_inventado({}, "Cinta (pack 8.30 cm): $ 5.000,00", con_equis) == nada
    asegurar dato_inventado({}, "Hay 3 x 2 en aceite.", con_equis) == "promociones"
    # Y con números chicos en la planilla ("2x1 litro", "x 3"), un 2x1 o un 4x3 de la IA
    # sigue siendo una promoción inventada.
    sea chica = [{ producto: "Leche", presentacion: "2x1 litro", precio: 3000, stock: 5 },
                 { producto: "Jabón", presentacion: "x 3", precio: 2000, stock: 5 }]
    asegurar dato_inventado({}, "Leche (2x1 litro): $ 3.000,00", chica) == nada
    asegurar dato_inventado({}, "Jabón (x 3): $ 2.000,00", chica) == nada
    asegurar dato_inventado({}, "Hay 2x1 en yerba.", chica) == "promociones"
    asegurar dato_inventado({}, "Llevando 4x3 te ahorrás uno.", chica) == "promociones"
    asegurar dato_inventado({}, "Los precios son por bulto cerrado.", con_equis) == nada
    # El renglón como lo arma el programa pasa siempre, aunque la presentación sea solo
    # "3x2" o "6x2.25". La misma presentación dicha de otra manera, no.
    sea sola = [{ producto: "Jabón", presentacion: "3x2", precio: 2000, stock: 5 },
                { producto: "Agua mineral", presentacion: "6x2.25", precio: 7000, stock: 5 }]
    asegurar dato_inventado({}, "Jabón (3x2): $ 2.000,00", sola) == nada
    asegurar dato_inventado({}, "Agua mineral (6x2.25): $ 7.000,00", sola) == nada
    asegurar dato_inventado({}, "Hay 3x2 en jabón.", sola) == "promociones"
    asegurar renglones_frenados(con_equis) == nada y renglones_frenados(lista_de_prueba()) == nada
    asegurar renglones_frenados(chica) == nada y renglones_frenados(sola) == nada
}

prueba "con los datos cargados, cada cosa se compara con el dato de su tema" {
    sea cargados = { horario: "Lunes a viernes de 8 a 17 y sábados de 8 a 13", telefono: "11 4555-1234",
                     formas_de_pago: "Efectivo o transferencia. No aceptamos tarjeta",
                     direccion: "Av. Mitre 1234, Lanús" }
    # Lo que dice lo mismo que lo cargado, pasa.
    para buena en ["Atendemos de lunes a viernes de 8 a 17.", "Los sábados, de 8 a 13.",
                   "Llamanos al 11 4555-1234.", "Aceptamos efectivo.", "Estamos en Av. Mitre 1234, Lanús."] {
        asegurar dato_inventado(cargados, buena, lista_de_prueba()) == nada, buena
    }
    # El "11" del teléfono no habilita una hora, ni lo negado en un dato habilita a decirlo.
    asegurar dato_inventado(cargados, "Abrimos a las 11.", lista_de_prueba()) == "horario"
    asegurar dato_inventado(cargados, "Aceptamos tarjeta.", lista_de_prueba()) == "formas_de_pago"
    # Las mismas palabras, mal combinadas, tampoco pasan.
    asegurar dato_inventado(cargados, "Atendemos lunes de 17 a 8.", lista_de_prueba()) == "horario"
    asegurar dato_inventado(cargados, "Atendemos de lunes a sábados de 8 a 13.", lista_de_prueba()) == "horario"
    asegurar dato_inventado(cargados, "Estamos en Rivadavia 500.", lista_de_prueba()) == "direccion"
    asegurar dato_inventado(cargados, "Llamanos al 11 4555-9999.", lista_de_prueba()) == "telefono"
    # Y lo que le llega al cliente es el dato, tal cual está escrito.
    enviar CargarLista { precios: lista_de_prueba() } a Mostrador
    simular_ia("Abrimos a las 11.")
    asegurar atender(lista_de_prueba(), "hola", cargados) == "Horario: Lunes a viernes de 8 a 17 y sábados de 8 a 13."
}

prueba "las preguntas corrientes por el horario, la dirección o el pago no le llegan a la IA" {
    simular_ia("Podés pasar hasta las 18, estamos todos los días.")
    sea persona = ": eso te lo confirma una persona."
    para dicho en ["que dias trabajan?", "mañana trabajan?", "que dias estan?", "estan a la tarde?",
                   "cuando puedo pasar?"] {
        asegurar atender(lista_de_prueba(), dicho, {}) == "Sobre el horario" + persona, dicho
    }
    asegurar atender(lista_de_prueba(), "puedo pasar a retirar hoy?", {}) == "Sobre el horario y la dirección" + persona
    para dicho en ["como llego?", "tienen local?"] {
        asegurar atender(lista_de_prueba(), dicho, {}) == "Sobre la dirección" + persona, dicho
    }
    asegurar atender(lista_de_prueba(), "tienen pagina web?", {}) == "Sobre el teléfono" + persona
    para dicho en ["visa?", "te hago una transfe?", "como se paga?"] {
        asegurar atender(lista_de_prueba(), dicho, {}) == "Sobre las formas de pago" + persona, dicho
    }
    asegurar largo(consultas_ia()) == 0
}

prueba "un saludo o una pregunta por un producto no se toman por una pregunta por un dato" {
    enviar CargarLista { precios: lista_de_prueba() } a Mostrador
    simular_ia("¡Hola! ¿Qué necesitás?")
    para dicho en ["hola buen dia", "buenas tardes", "hola como estan", "trabajan cafe?",
                   "me podes pasar la lista?", "me llega la lista de precios?", "que marcas trabajan?"] {
        asegurar atender(lista_de_prueba(), dicho, {}) == "¡Hola! ¿Qué necesitás?", dicho
    }
    # En un pedido con su cantidad, "pago", "sábado" o "mi teléfono" no agregan nada.
    sea cuenta = "12 x Azúcar (bolsa de 10 kg) a $ 9.800,50 cada uno: total $ 117.606,00."
    para dicho en ["cuanto pago por 12 azucar?", "cuanto tengo que pagar por 12 azucar?",
                   "dame 12 azucar para el sabado", "dame 12 azucar, en una hora paso",
                   "quiero 12 azucar, te dejo mi telefono"] {
        asegurar atender(lista_de_prueba(), dicho, {}) == cuenta, dicho
    }
    # Pero si en el pedido preguntan de verdad por un dato, se contesta.
    asegurar atender(lista_de_prueba(), "quiero 12 azucar, abren el sabado?", {}) == cuenta + " Sobre el horario: eso te lo confirma una persona."
}

prueba "si preguntan por un producto y por un dato, va el renglón de la lista y el dato, sin IA" {
    simular_ia("Atendemos de lunes a viernes de 8 a 18 hs.")
    sea yerba = "Yerba mate (bolsón de 10 paquetes de 1 kg): $ 35.000,00."
    asegurar atender(lista_de_prueba(), "cuanto sale la yerba? aceptan tarjeta?", {}) == yerba + " Sobre las formas de pago: eso te lo confirma una persona."
    asegurar atender(lista_de_prueba(), "donde consigo yerba?", {}) == yerba + " Sobre la dirección: eso te lo confirma una persona."
    # De fideos no hay: se avisa también acá.
    asegurar atender(lista_de_prueba(), "tenes fideos? abren sabados?", {}) == "Fideos secos (caja de 20 paquetes de 500 g): $ 18.900,00. De Fideos secos ahora no hay stock. Sobre el horario: eso te lo confirma una persona."
    asegurar atender(lista_de_prueba(), "cuanto sale la yerba? aceptan tarjeta?", { formas_de_pago: "Efectivo" }) == yerba + " Formas de pago: Efectivo."
    asegurar largo(consultas_ia()) == 0
}

prueba "si la IA dice que no lo tienen pero ofrece conseguirlo, también va solo que no se trabaja" {
    enviar CargarLista { precios: lista_de_prueba() } a Mostrador
    para ofrece en ["Lamentablemente no tenemos café, pero te lo puedo conseguir para más adelante.",
                    "No contamos con ese producto, pero podemos pedirlo.", "Café no vendemos. Puedo encargarlo."] {
        simular_ia(ofrece)
        asegurar atender(lista_de_prueba(), "tenes cafe?", {}) == "Eso no lo trabajamos.", ofrece
    }
    # Un "no" que habla de otra cosa no se cambia.
    para otra_cosa en ["No vendemos por menor, no trabajamos al público.", "No tenemos esa información."] {
        asegurar sin_ofrecer(otra_cosa) == otra_cosa, otra_cosa
    }
}

prueba "de lo que no está en la lista dice solo que no lo trabaja, y de lo que está en cero avisa" {
    enviar CargarLista { precios: lista_de_prueba() } a Mostrador
    simular_ia("Lo siento, no trabajamos con café. Podés pedirlo si querés y cuántas unidades.")
    asegurar atender(lista_de_prueba(), "tenes cafe?", {}) == "Eso no lo trabajamos."
    # De fideos, en la lista de las pruebas, no hay: lo avisa el programa, no la IA.
    simular_ia("Sí, tenemos fideos secos.")
    asegurar atender(lista_de_prueba(), "tenes fideos?", {}) == "Sí, tenemos fideos secos. De Fideos secos ahora no hay stock."
}
"""


def orden_para_esta_carpeta():
    """La orden para correr Mate desde la carpeta donde está parada la persona, lista para
    copiar: 'mate' si está instalada; si no, py, python o python3 (como diga
    como_se_llama()) y la ruta de mate.py vista desde ahí."""
    orden = como_se_llama()
    if orden == "mate":
        return orden
    return f"{orden.split()[0]} {ruta_para_escribir(os.path.abspath(__file__))}"


def archivos_del_mostrador(nombre, orden, carpeta_de_mate=None, fin_de_renglon=None):
    """Lo que crea 'nuevo mostrador <nombre>': {nombre del archivo: su contenido, en
    bytes}: el programa, la planilla y los casos para 'ensayar', en ese orden. Falla con un
    ErrorMate si en la carpeta de Mate falta el ejemplo, o si ya no tiene los dos títulos
    que marcan qué parte se copia."""
    carpeta = os.path.join(carpeta_de_mate or os.path.dirname(os.path.abspath(__file__)),
                           CARPETA_DE_EJEMPLOS)
    programa, planilla = f"{nombre}.mate", f"{nombre}_precios.csv"
    casos = f"{nombre}_casos.txt"
    try:
        ejemplo = leer_fuente(os.path.join(carpeta, EJEMPLO_DEL_MOSTRADOR))
        with open(os.path.join(carpeta, PLANILLA_DE_MUESTRA), "rb") as f:
            muestra = f.read()
        de_muestra = leer_fuente(os.path.join(carpeta, CASOS_DE_MUESTRA))
    except OSError:
        raise ErrorMate(
            f"para crear un mostrador hacen falta {EJEMPLO_DEL_MOSTRADOR}, "
            f"{PLANILLA_DE_MUESTRA} y {CASOS_DE_MUESTRA}, que vienen con Mate, y no los "
            f"encuentro en "
            f"{para_pegar(carpeta)}. Si copiaste solo mate.py, bajá Mate de nuevo con todas "
            "sus carpetas", familia="archivo")
    desde, hasta = ejemplo.find(_MOSTRADOR_DESDE), ejemplo.find(_MOSTRADOR_HASTA)
    if desde < 0 or hasta < desde:
        raise ErrorMate(
            f"no pude armar el mostrador: {EJEMPLO_DEL_MOSTRADOR} (en {para_pegar(carpeta)}) "
            "no tiene la forma que espero. ¿Lo cambiaste? Bajá Mate de nuevo para tener "
            "el ejemplo original", familia="archivo")
    cuerpo = ejemplo[desde + 1:hasta + 1].replace(PLANILLA_DE_MUESTRA, planilla)
    texto = (_ENCABEZADO_DEL_MOSTRADOR + "\n" + cuerpo + _PRUEBAS_DEL_MOSTRADOR)
    for marca, valor in (("«PROGRAMA»", programa), ("«PLANILLA»", planilla),
                         ("«CASOS»", casos), ("«ORDEN»", orden)):
        texto = texto.replace(marca, valor)
    # Los casos de muestra traen, de nota, cómo se ensaya el ejemplo 12: acá va cómo se
    # ensaya este mostrador (desde el título 'Cómo se escribe' es el mismo archivo).
    corte = de_muestra.find(_CASOS_DESDE)
    de_muestra = (f"# Casos para ensayar {programa}: lo que pregunta un cliente y lo que la "
                  "respuesta\n# tiene que decir (o no puede decir). Es tuyo: cambialos y "
                  "agregá los que quieras.\n# OJO: los casos que vienen acá son de muestra, escritos "
                  f"para la planilla de muestra\n# (yerba, azúcar, fideos). Si cambiás "
                  f"los productos de {planilla}, cambiá\n# también estos casos: si no, "
                  "fallan los que nombran un producto que ya no está.\n"
                  "# Lo mismo con los datos del negocio (el horario, la dirección...): los "
                  "casos de\n# muestra esperan que estén vacíos. Cuando cargues los tuyos "
                  f"en {programa},\n# cambiá esos casos.\n"
                  "#\n# Cómo se usa, en PowerShell, parado en "
                  "la carpeta donde está este archivo:\n"
                  f"#     {orden} ensayar {programa} {casos} --ia-simulada\n"
                  "# (sin --ia-simulada contesta la IA de verdad: así se ve si una lección "
                  "funcionó)\n#\n") + de_muestra[max(corte, 0):]
    # Con la marca del principio y los fines de renglón de esta computadora: así el Bloc
    # de notas de cualquier Windows lo muestra bien. (Mate lee las dos formas.)
    fin = os.linesep if fin_de_renglon is None else fin_de_renglon
    return {programa: texto.replace("\n", fin).encode("utf-8-sig"), planilla: muestra,
            casos: de_muestra.replace("\n", fin).encode("utf-8-sig")}


# ───────────────────────── La orden 'nuevo equipo' (0.7) ─────────────────────────
# 'nuevo equipo mi_negocio' crea, con la misma forma y los mismos cuidados que 'nuevo
# mostrador', un equipo de tres agentes (Ventas, Depósito y Compras) que se hablan entre
# ellos: mi_negocio.mate, mi_negocio_precios.csv y mi_negocio_casos.txt.
# De dónde sale: tampoco acá está copiada la lógica. El equipo es el del ejemplo
# 13_equipo_del_negocio.mate (lo que hay entre sus títulos "El equipo" y "Las pruebas"), y
# las funciones que entienden los pedidos son las del ejemplo 12, que el 13 trae con
# 'usar': como el programa creado tiene que andar solo, van adentro, en tres tramos del 12
# marcados por los comentarios de más abajo. Un arreglo en cualquiera de los dos ejemplos
# llega a los equipos que se creen después.
# (0.7.1) Los datos del negocio (datos_del_negocio: el horario, la dirección, el teléfono...)
# vienen en el primer tramo del 12, al lado de la regla del envío: quedan arriba de todo en
# el mostrador y en el equipo. Las funciones que los usan están en el segundo tramo. Acá
# quedan, de eso, los textos para el dueño y las pruebas de los programas creados.
EJEMPLO_DEL_EQUIPO = "13_equipo_del_negocio.mate"
CASOS_DEL_EQUIPO = "casos_del_equipo.txt"
_EQUIPO_DESDE = "\n# ── El equipo"
_EQUIPO_PROGRAMA = "\n# ── El programa"  # (de acá para abajo va al final, después de lo del 12)
_EQUIPO_HASTA = "\n# ── Las pruebas"
# Del ejemplo 12 (desde, hasta): la regla del envío; las funciones que entienden el pedido
# y hacen la cuenta; y las que revisan la planilla. Quedan afuera su agente, su charla y
# su programa.
_DEL_12_PARA_EL_EQUIPO = (
    ("\n# La regla del envío:", "\nmensaje CargarLista"),
    ('\n# La columna "precio" de la lista', "\n# Una consulta: primero prueba el programa"),
    ("\n# ¿La planilla sirve para atender?", "\n# Lee la planilla y la revisa"))

_ENCABEZADO_DEL_EQUIPO = """\
# «PROGRAMA»: el equipo de tu negocio.
# Son tres agentes: Ventas, Depósito y Compras.
# Lo creó la orden 'nuevo equipo' de Mate, a partir de los ejemplos
# 13_equipo_del_negocio.mate y 12_mostrador_con_reglas.mate. Es tuyo: lo podés cambiar
# todo lo que quieras.
#
# QUÉ HACE. Los tres agentes se hablan entre ellos para repartirse el trabajo:
#   - VENTAS atiende por teclado. Cuando el cliente pide una CANTIDAD de un PRODUCTO de la
#     planilla ("quiero 12 azucar con envio"), hace la cuenta sin consultar a la IA.
#     NO ANOTA DIRECTO: primero repite el pedido, con la cuenta completa y con cuántos
#     BULTOS son ("Entendí: 12 x Azúcar (bolsa de 10 kg) ... Son 12 bolsas enteras. ¿Lo
#     anoto? Contestá si o no."). Solo si lo que sigue es un "si" (o "sí", "dale", "ok",
#     "confirmo", "anotalo"), y nada más, le pide a Depósito que lo reserve. Con "no", o
#     con cualquier otra cosa, no anota nada; si la otra cosa es un pedido nuevo, lo
#     trata como pedido nuevo, con su propia pregunta. Así, si Ventas entendió mal, se ve
#     ANTES de descontar el stock. (Las palabras del sí están en palabras_de_si().)
#     Al sí lo puede acompañar solo "por favor" o "gracias". "Dejá", "ok, dejá" o "dale,
#     dejá nomás" son un no. Y si te vas con chau sin contestar, avisa que no anotó.
#     Pregunta "¿Lo anoto?" solo con los pedidos CLAROS: con una pregunta ("cuanto salen
#     12 azucar"), un "no", una duda, una palabra que no conoce ("recibí 10 yerbas") o
#     una frase que habla de un pedido que YA está hecho ("retiro el pedido de 5 azucar",
#     "gracias por las 10 yerbas") contesta la cuenta, y ni pregunta ni anota.
#     Tampoco anota si piden por lo que viene ADENTRO del bulto ("10 paquetes de yerba",
#     y la yerba se vende por bolsón de 10 paquetes): pregunta, y dice cómo se vende.
#     La unidad de venta es la PRIMERA palabra de la columna presentacion: conviene que
#     sea el bulto ("pack de 6 botellas", y no "6 botellas"). Lo de adentro son las
#     palabras que llevan un número adelante ("10 paquetes", "1 kg").
#     Un pedido ya anotado no se anula desde la charla: eso lo arregla una persona.
#     Tampoco consulta a la IA cuando preguntan por un DATO DEL NEGOCIO (el horario, la
#     dirección, el teléfono, cómo se paga, las entregas, las promociones): contesta
#     con lo que vos cargaste, tal cual; y si no lo cargaste, NO LO INVENTA: contesta
#     "eso te lo confirma una persona".
#     Todo lo demás (saludar, contar qué hay) lo contesta la IA, con frenos para que no
#     invente precios. A lo que contesta, el programa le mira además que no nombre un
#     día, una hora, una dirección, un teléfono, una forma de pago, una entrega o una
#     promoción que no cargaste: si lo nombra, esa respuesta no le llega al cliente.
#     OJO: esa revisión va por palabras. Ataja lo más común, NO TODO: un modelo puede
#     decir un dato de una manera que no está prevista. Por eso conviene CARGAR TUS
#     DATOS (con el dato cargado, si la IA dice otra cosa, al cliente le llega el tuyo)
#     y ENSAYAR con tu modelo de verdad antes de dejarlo atender.
#     Y si preguntan por un producto que está en cero ("¿tenés aceite?"), Ventas avisa
#     que ahora no hay.
#   - DEPÓSITO es el único que sabe cuánto stock hay. Lo descuenta con cada pedido
#     confirmado y lo RECUERDA de una vez a la otra. No vende lo que no hay.
#   - COMPRAS deja anotado lo que hay que reponer. Depósito le avisa UNA vez, cuando un
#     producto baja del mínimo; al abrir y al cerrar, el programa muestra lo anotado.
#
# QUÉ PODÉS CAMBIAR SIN SABER PROGRAMAR:
#   1. Tus productos. Están en la planilla que está al lado de este archivo:
#          «PLANILLA»
#      Abrila con Excel o con el Bloc de notas. El primer renglón son los títulos, y va
#      una sola vez:
#          producto;presentacion;precio;stock
#      Abajo va un renglón por producto. El cliente nombra cada producto por la PRIMERA
#      palabra de su nombre ("yerba", "azúcar"): conviene que sea la que lo distingue.
#   2. Desde cuántas unidades hay envío: el número de unidades_para_envio, acá abajo.
#      Va un número entero, sin comillas: 1 o más.
#   3. LOS DATOS DE TU NEGOCIO: el horario, la dirección, el teléfono, las formas de pago,
#      las entregas y las promociones. Están acá abajo, en datos_del_negocio: escribí
#      cada uno entre las comillas. Vienen VACÍOS: mientras estén vacíos, a quien
#      pregunte se le contesta "eso te lo confirma una persona". Al arrancar, el
#      programa muestra cuáles están cargados y cuáles no.
#   4. El mínimo de stock: el número de stock_minimo, un poco más abajo. Cuando de un
#      producto quedan menos unidades que esas, Depósito le avisa a Compras. Va un número
#      entero, sin comillas: 0 o más (con 0 no avisa nunca).
#   5. Cómo se presenta el negocio: el texto que empieza con "Atendés las ventas".
#   6. Lo que la IA no puede decir nunca: las palabras de 'prohibido', dentro de 'frenos'.
#   7. Las palabras con las que tus clientes piden: están en palabras_de_pedir(). Si a un
#      pedido bien dicho Ventas no le pregunta "¿Lo anoto?" (contesta "Todavía no anoté
#      nada"), agregá ahí la palabra que usó, entre comillas y con una coma. Van en
#      minúsculas y sin tildes. Las palabras con las que confirman: en palabras_de_si().
#   8. Las palabras con las que tus clientes preguntan por el horario, la dirección y
#      los demás datos: están en temas_del_negocio(). También en minúsculas y sin tildes.
#      Y las que se le miran a la respuesta de la IA: en palabras_de_dias() y las listas
#      que le siguen. Si tu modelo inventa algo con otra palabra, se agrega ahí.
#
# EL STOCK. El de la planilla es el de ARRANQUE: Depósito lo toma la primera vez que ve
# cada producto y de ahí en más lo lleva él. Lo que recuerda queda en este archivo, que
# se abre con el Bloc de notas:
#          «MEMORIA»
# Cambiar el número en la planilla NO cambia lo que Depósito recuerda:
#   - Cuando llega mercadería, escribí en la charla:   ingreso 30 azucar
#     (la palabra ingreso, sin tilde; la cantidad; el nombre del producto; y nada más:
#     ni signos ni otras palabras). Depósito lo repite ("Entendí: entran 30 x Azúcar
#     (bolsa de 10 kg). Son 30 bolsas enteras. ¿Lo sumo?") y lo suma recién cuando
#     contestás si: un cero de más se ve antes de tocar el stock. Si está escrito de
#     otra manera no suma nada y te dice cómo va. Si con lo que entró el producto sigue
#     por debajo del mínimo, el pedido de reposición queda anotado.
#   - Para empezar de nuevo con el stock de la planilla, agregá --olvidar al comando de
#     correr (una sola vez: borra lo que recuerdan Depósito y Compras).
#   - Depósito le avisa a Compras cuando un producto BAJA del mínimo por una venta (o
#     cuando alguien pide uno que está en cero). Uno que ya arranca por debajo del mínimo
#     en la planilla no se anota hasta que alguien lo pide.
#   - Si sacás un producto de la planilla o le cambiás el nombre, lo que Depósito y
#     Compras recordaban de él queda guardado: se limpia con --olvidar.
# OJO: "ingreso" se escribe en la misma charla que usa el cliente. Sirve mientras el
# teclado lo maneja alguien del negocio.
#
# OJO, QUE ES IMPORTANTE: el stock y lo anotado para reponer se GUARDAN CUANDO EL PROGRAMA
# TERMINA. Terminá siempre la charla con chau. Si cerrás la ventana con la X (o se corta
# la luz), se pierde lo anotado en esa charla: el stock queda como estaba al abrirla. Si
# atendés todo el día, conviene escribir chau y volver a entrar cada tanto.
# Un pedido o un ingreso que esperaba el "si" no se guarda nunca: sin el "si", no existe.
# Y no abras este programa en dos ventanas a la vez: la segunda avisa que ya hay otra
# abierta y no arranca (si las dos anotaran, la que cierra última pisaría a la otra).
#
# CÓMO SE USA, en PowerShell, parado en la carpeta donde está este archivo:
#   Para comprobar que quedó todo bien (hacelo cada vez que cambies algo):
#          «ORDEN» probar «PROGRAMA»
#   Para charlar con el equipo sin gastar nada (no hace falta clave ni internet):
#          «ORDEN» correr «PROGRAMA» --ia-simulada
#   Para VER cómo se hablan los agentes (Ventas con Depósito, Depósito con Compras):
#          «ORDEN» correr «PROGRAMA» --ia-simulada --traza
#   Para atender con la IA de verdad:
#          «ORDEN» correr «PROGRAMA»
#   Para salir de la charla, escribí chau.
#   Para ensayarlo: Mate le hace las preguntas anotadas en «CASOS» (se abre con el Bloc
#   de notas) y dice cuáles contestó bien. Un ensayo no descuenta stock:
#          «ORDEN» ensayar «PROGRAMA» «CASOS» --ia-simulada
#   (En un caso, el "si" del cliente va debajo de la pregunta, así:   después: si )
#   OJO: los casos que vienen en «CASOS» son de muestra, escritos para la planilla de
#   muestra (yerba, azúcar, fideos) y con los datos del negocio VACÍOS. Cuando pongas
#   tus productos en la planilla o cargues tus datos, cambiá también los casos: si no,
#   fallan los que nombran un producto que ya no está o esperan un dato sin cargar.
#
# Las pruebas del final usan una lista fija, no tu planilla ni lo que Depósito recuerda:
# siguen pasando aunque cambies los productos, los precios, el número del envío o el
# mínimo. Una sola mira tu planilla, para avisarte si quedó algo mal cargado.
# Si unidades_para_envio, stock_minimo o ingreso_maximo quedan mal puestos (con comillas,
# con decimales, negativos), el equipo no atiende y todas las pruebas fallan con el mismo
# aviso, que dice cuál es y cómo va. (La orden 'verificar' no mira eso: mira que el
# programa esté bien escrito.)
# Si en la planilla queda un precio o un stock vacío o con letras, el equipo no atiende:
# al arrancar dice de qué producto es y cómo arreglarlo.
"""

_PRUEBAS_DEL_EQUIPO = """\
# ── Las pruebas ──────────────────────────────────────────────────────────────────────
# Corren con la orden 'probar'. Usan la lista fija de acá abajo y no tu planilla: así
# siguen pasando aunque cambies los productos y los precios. En una prueba los agentes
# arrancan de cero (no se usa lo que recuerdan ni se guarda nada) y la IA nunca es de
# verdad. mensajes_enviados("Reponer") da los mensajes de ese tipo que viajaron en la prueba.

# La lista de las pruebas. De azúcar hay 5 más que el mínimo, para poder bajar de ahí, y
# de yerba 100000 más que el mínimo, para que no baje nunca.
funcion lista_de_prueba() {
    # (con el mínimo mal puesto no hay cuenta que hacer: la prueba falla enseguida, en
    # abrir_el_negocio(), con el aviso que dice cómo va)
    var piso = 0
    si es_entero_desde(stock_minimo, 0) {
        piso = stock_minimo
    }
    devolver [{ producto: "Yerba mate", presentacion: "bolsón de 10 paquetes de 1 kg", precio: 35000, stock: piso + 100000 },
              { producto: "Azúcar", presentacion: "bolsa de 10 kg", precio: 9800.5, stock: piso + 5 },
              { producto: "Fideos secos", presentacion: "caja de 20 paquetes de 500 g", precio: 18900, stock: 0 }]
}

# En las pruebas, el cliente que pide y, cuando Ventas le repite el pedido y le pregunta
# "¿Lo anoto?", contesta "si". Devuelve lo que Ventas contesta a ese "si". Si Ventas no
# preguntó (no entendió un pedido claro), devuelve lo que contestó, y no dice "si".
funcion pedir_y_confirmar(charla, dicho) {
    sea entendido = consultar_a_ventas(charla, dicho)
    si no (empieza_con(entendido, "Entendí: ") y termina_con(entendido, "¿Lo anoto? Contestá si o no.")) {
        devolver entendido
    }
    devolver consultar_a_ventas("{charla} (el si)", "si")
}

prueba "tu planilla está bien cargada" {
    # La única prueba que mira «PLANILLA»: si falla, el texto dice qué arreglar.
    # Es lo mismo que el equipo revisa al arrancar: los títulos, y que cada producto
    # tenga su precio y su stock en números (una celda vacía no es un número).
    # También mira los tres números de arriba: unidades_para_envio, stock_minimo e
    # ingreso_maximo.
    sea a_corregir = que_arreglar(lista)
    si a_corregir != nada {
        fallar(a_corregir)
    }
    # Y mira lo que cargaste arriba, en datos_del_negocio: que cada dato sea un texto
    # entre comillas (un teléfono también: sin comillas, Mate lo toma por una cuenta) y
    # que el nombre de cada dato siga como vino, en minúsculas y sin tilde.
    sea mal_escrito = datos_mal_puestos(datos_del_negocio)
    si mal_escrito != nada {
        fallar(mal_escrito)
    }
    # Y que ningún renglón de tu planilla se parezca a un dato del negocio: el renglón de
    # la lista, dicho como lo arma el programa ("Jabón (3x2)"), no cuenta como inventado.
    # No se conoce ninguno que se frene; si igual apareciera, acá te enterás antes que el cliente.
    sea frenados = renglones_frenados(lista)
    si frenados != nada {
        fallar(frenados)
    }
}

prueba "un pedido lo anota Ventas y lo descuenta Depósito, sin consultar a la IA" {
    abrir_el_negocio(lista_de_prueba())
    # Aunque la IA "quiera" contestar mal, nadie le pregunta.
    simular_ia("Son $ 10,80.")
    # Ventas no anota directo: repite el pedido, con la cuenta y los bultos, y pregunta.
    asegurar consultar_a_ventas("a", "quiero 3 azucar") == "Entendí: 3 x Azúcar (bolsa de 10 kg) a $ 9.800,50 cada uno: total $ 29.401,50. Son 3 bolsas enteras. ¿Lo anoto? Contestá si o no."
    asegurar largo(mensajes_enviados("Reservar")) == 0
    # Con el "si", recién ahí, se anota. (El "si" es otra consulta, con su propio nombre
    # de charla; lo que lo une al pedido es que lo dice el MISMO cliente: el del teclado.)
    asegurar consultar_a_ventas("a2", "si") == "Anotado: 3 x Azúcar (bolsa de 10 kg) a $ 9.800,50 cada uno: total $ 29.401,50."
    asegurar largo(mensajes_enviados("Reservar")) == 1
    # Quedan 3 menos: se ve preguntando por una más de las que hay.
    sea quedan = stock_minimo + 2
    asegurar consultar_a_ventas("b", "tenes {quedan + 1} azucar?") == "De Azúcar quedan {quedan}; no llego a {quedan + 1}."
    asegurar largo(consultas_ia()) == 0
}

prueba "la conversación va de Ventas a Depósito, y de Depósito a Compras" {
    abrir_el_negocio(lista_de_prueba())
    # De fideos no hay: Depósito no vende, y le avisa a Compras.
    pedir_y_confirmar("a", "quiero 3 fideos")
    # Quién le preguntó a quién, en orden (el mínimo en 0 es no avisar nunca). El cliente
    # habló dos veces: el pedido, y el "si". Recién con el "si" Ventas le habla a Depósito.
    var camino = []
    para m en mensajes_enviados() {
        si m.pregunta {
            camino = agregar(camino, "{m.de} → {m.a}: {m.tipo}")
        }
    }
    var esperado = ["(programa) → Ventas: ConsultaDeCliente", "(programa) → Ventas: ConsultaDeCliente",
                    "Ventas → Deposito: Reservar"]
    si stock_minimo > 0 {
        esperado = agregar(esperado, "Deposito → Compras: Reponer")
    }
    asegurar camino == esperado, camino
}

prueba "pedir más de lo que hay no vende" {
    abrir_el_negocio(lista_de_prueba())
    asegurar pedir_y_confirmar("a", "quiero 3 fideos") == "De Fideos secos ahora no hay stock."
    sea hay = stock_minimo + 100000
    asegurar pedir_y_confirmar("b", "quiero {hay + 1} yerbas") == "De Yerba mate quedan {hay}; no llego a {hay + 1}."
    # No se descontó nada: siguen estando todas.
    asegurar empieza_con(pedir_y_confirmar("c", "quiero {hay} yerbas"), "Anotado: {hay} x Yerba mate")
}

prueba "al bajar del mínimo sale UN pedido de reposición, no uno por cada venta" {
    abrir_el_negocio(lista_de_prueba())
    # De azúcar hay 5 más que el mínimo: con 3 menos todavía no se avisa.
    pedir_y_confirmar("a", "quiero 3 azucar")
    asegurar largo(mensajes_enviados("Reponer")) == 0
    # Con 3 menos ya queda por debajo: se avisa. Y con los pedidos que siguen, no de nuevo.
    pedir_y_confirmar("b", "quiero 3 azucar")
    pedir_y_confirmar("c", "quiero 1 azucar")
    pedir_y_confirmar("d", "quiero 1 azucar")
    # (con el mínimo en 0 no se avisa nunca)
    var avisos = 1
    si stock_minimo == 0 {
        avisos = 0
    }
    asegurar largo(mensajes_enviados("Reponer")) == avisos
    # Compras lo tiene anotado una sola vez.
    sea faltantes = preguntar QueFalta {} a Compras
    asegurar largo(faltantes.pedidos) == avisos
}

prueba "preguntar el precio no anota nada ni descuenta stock" {
    abrir_el_negocio(lista_de_prueba())
    para dicho en ["cuanto salen 3 azucar?", "tenes 3 azucar?", "precio de 3 azucar"] {
        asegurar consultar_a_ventas(dicho, dicho) == "3 x Azúcar (bolsa de 10 kg) a $ 9.800,50 cada uno: total $ 29.401,50. Todavía no anoté nada: para pedirlo, escribí \\"quiero 3 azucar\\"."
    }
    asegurar largo(mensajes_enviados("Reservar")) == 0 y largo(mensajes_enviados("Reponer")) == 0
}

prueba "el envío sale desde las unidades de la regla; si no llega, no se anota" {
    abrir_el_negocio(lista_de_prueba())
    sea n = unidades_para_envio
    asegurar termina_con(pedir_y_confirmar("a", "quiero {n} yerbas con envio"), "Con envío: sí, va con envío.")
    asegurar largo(mensajes_enviados("Reservar")) == 1
    # Con una unidad menos no hay envío (si la regla es desde 1, no hay "una menos"): se
    # le dice, y no se anota hasta que el cliente decida.
    si n > 1 {
        sea contestado = consultar_a_ventas("b", "me mandas {n - 1} yerbas?")
        asegurar tiene(contestado, "Sin envío: hacemos envíos desde {n} unidades y pedís {n - 1}.")
        asegurar tiene(contestado, "Todavía no anoté nada")
        asegurar largo(mensajes_enviados("Reservar")) == 1
    }
    # Si dice que NO quiere envío, se anota y no se le confirma un envío.
    asegurar termina_con(pedir_y_confirmar("c", "quiero {n} yerbas sin envio"), "total {pesos(n * 35000)}.")
    asegurar largo(consultas_ia()) == 0
}

prueba "la mercadería que llega se suma, y Compras la tacha de su lista" {
    abrir_el_negocio(lista_de_prueba())
    pedir_y_confirmar("a", "quiero 3 fideos")
    # Entran 30 más que el mínimo: alcanza, y Compras no tiene nada que reponer.
    # (si pusiste un mínimo más grande que ingreso_maximo, eso no entra en un solo
    # ingreso: esta prueba no tiene qué mirar)
    sea n = stock_minimo + 30
    si n <= ingreso_maximo {
        asegurar anotar_ingreso(lista_de_prueba(), "ingreso {n} fideos") == "Entraron {n} de Fideos secos: ahora hay {n}."
        asegurar (preguntar QueFalta {} a Compras).pedidos == []
        asegurar empieza_con(pedir_y_confirmar("b", "quiero 30 fideos"), "Anotado: 30 x Fideos secos")
    }
}

prueba "si entra poca mercadería y sigue bajo el mínimo, el pedido de reposición queda" {
    abrir_el_negocio(lista_de_prueba())
    # (con un mínimo de 0 o de 1 no hay "poca": esta prueba no tiene qué mirar)
    si stock_minimo > 1 {
        # De fideos no hay. Entra 1: sigue por debajo del mínimo, y Compras lo anota.
        asegurar anotar_ingreso(lista_de_prueba(), "ingreso 1 fideos") == "Entraron 1 de Fideos secos: ahora hay 1. Sigue por debajo del mínimo ({stock_minimo}): queda anotado para reponer."
        asegurar (preguntar QueFalta {} a Compras).pedidos == [{ producto: "Fideos secos", quedan: 1 }]
        # Como ya está anotado, una venta no le avisa de nuevo.
        pedir_y_confirmar("a", "quiero 1 fideos")
        asegurar largo(mensajes_enviados("Reponer")) == 0
        # Entra lo que falta para llegar al mínimo: recién ahí Compras lo tacha.
        # (salvo que el mínimo sea más grande que lo que entra en un solo ingreso)
        si stock_minimo <= ingreso_maximo {
            anotar_ingreso(lista_de_prueba(), "ingreso {stock_minimo} fideos")
            asegurar (preguntar QueFalta {} a Compras).pedidos == []
        }
    }
}

prueba "un ingreso lleva la cantidad y el producto, y nada más" {
    abrir_el_negocio(lista_de_prueba())
    para dicho en ["ingreso fideos", "ingreso -5 yerbas", "ingreso - 5 yerbas", "ingreso yerbas 5",
                   "ingreso 5 cafe", "ingreso 10 yerbas con envio", "ingreso 5 yerbas no",
                   "ingreso 5 yerbas?", "ingreso 5 de yerba", "ingreso 5 yerbas gracias",
                   "ingresó 5 yerbas", "ingreso: 5 yerbas", "ingresos 5 yerbas"] {
        asegurar empieza_con(anotar_ingreso(lista_de_prueba(), dicho), "No entendí el ingreso. No sumé nada."), dicho
    }
    # Un número más grande que el tope (un cero de más) tampoco entra.
    asegurar empieza_con(anotar_ingreso(lista_de_prueba(), "ingreso {ingreso_maximo + 1} yerbas"), "No lo anoté:")
    asegurar largo(mensajes_enviados("Ingreso")) == 0
    # Solo es un ingreso si la primera palabra es "ingreso". Si está escrito parecido
    # ("ingresó 5 yerbas"), en la charla se explica cómo va y no cuenta como consulta.
    asegurar es_un_ingreso("ingreso 30 yerbas") y no es_un_ingreso("Ingresó mi pedido de 20 yerbas?")
    asegurar parece_un_ingreso("ingresó 5 yerbas") y no parece_un_ingreso("Ingresó mi pedido de 20 yerbas?")
    simular_teclado(["ingresó 5 yerbas", "ingreso 5 yerbas?", "chau"])
    asegurar charlar_con_el_equipo(lista_de_prueba()) == 0
    asegurar largo(mensajes_enviados("Ingreso")) == 0
}

prueba "lo que no es un pedido claro no se anota: negaciones, dudas, preguntas y avisos" {
    abrir_el_negocio(lista_de_prueba())
    para dicho en ["no me mandes 2 yerbas", "no anotes 2 yerbas", "se puede pedir 2 yerbas?",
                   "2 yerbas?", "queria saber si puedo pedir 2 yerbas", "no se si quiero 20 yerbas",
                   "haceme un descuento en 20 yerbas", "a las 3 paso a buscar la yerba",
                   "te debo 2 yerbas", "quiero -3 yerbas", "quiero - 3 yerbas", "quiero –3 yerbas",
                   "quiero 20 yerbas？", "recibi 10 yerbas",
                   "llegaron 10 yerbas", "me mandaron 10 yerbas", "ingresaron 5 yerbas"] {
        asegurar tiene(consultar_a_ventas(dicho, dicho), "Todavía no anoté nada"), dicho
    }
    asegurar largo(mensajes_enviados("Reservar")) == 0
    # Y un pedido claro sí se anota, se diga como se diga.
    para dicho en ["quiero 2 yerbas", "2 yerbas", "Hola, quería 2 bolsones de yerba por favor",
                   "dame 2 yerbas, las retiro yo", "anotame 2 yerbas sin envio",
                   "quiero comprar 2 yerbas", "quiero pedir 2 yerbas", "me das 2 yerbas",
                   "hago un pedido de 2 yerbas", "2 yerbas, gracias"] {
        asegurar empieza_con(pedir_y_confirmar(dicho, dicho), "Anotado: 2 x Yerba mate"), dicho
    }
    asegurar largo(consultas_ia()) == 0
}

prueba "hablar de un pedido que YA está hecho no lo anota otra vez" {
    abrir_el_negocio(lista_de_prueba())
    # El cliente agradece, viene a retirar o pregunta por lo que ya pidió: si se anotara,
    # se le vendería dos veces.
    para dicho en ["retiro el pedido de 5 yerbas", "gracias por las 5 yerbas",
                   "ya llevo el pedido de 5 yerbas", "hola, por mi pedido de 5 yerbas",
                   "te llevo 10 yerbas", "me mandan 10 yerbas", "otro dia quiero 20 yerbas",
                   "gracias por el pedido de 20 yerbas", "gracias por las 10 yerbas del otro dia",
                   "gracias, ya retiro mi pedido de 5 yerbas",
                   "hola, el pedido de 10 yerbas ya lo retiro",
                   "buenas, ya mandan mi pedido de 12 yerbas", "ya me mandan las 10 yerbas",
                   "mi pedido de 20 yerbas", "che, y el pedido de 5 yerbas", "retiro 5 yerbas"] {
        asegurar tiene(consultar_a_ventas(dicho, dicho), "Todavía no anoté nada"), dicho
    }
    # Nadie reservó nada: la yerba está entera.
    asegurar largo(mensajes_enviados("Reservar")) == 0
    asegurar (preguntar CuantoQueda { producto: "Yerba mate" } a Deposito).unidades == stock_minimo + 100000
}

prueba "un pedido en la unidad de ADENTRO del bulto no se anota: Ventas pregunta" {
    abrir_el_negocio(lista_de_prueba())
    # La yerba se vende por bolsón de 10 paquetes: "10 paquetes" puede ser 1 bolsón o 10.
    asegurar consultar_a_ventas("a", "quiero 10 paquetes de yerba") == "Todavía no anoté nada, para no equivocarme: dijiste \\"paquetes\\", y Yerba mate se vende por bolsón de 10 paquetes de 1 kg, a $ 35.000,00 cada uno. ¿Cuántos querés de esos? Por ejemplo, para llevar uno solo: \\"quiero 1 yerba\\"."
    para dicho en ["10 paquetes de yerba", "dame 1 paquete de yerba", "anotame 20 paquetes de fideos",
                   "quiero 10 paquetes de yerba con envio", "cuanto salen 10 paquetes de yerba?",
                   "quiero 2 azucar de 10 kg"] {
        asegurar empieza_con(consultar_a_ventas(dicho, dicho), "Todavía no anoté nada, para no equivocarme: dijiste \\""), dicho
    }
    # Un pasado con tilde ("compró" no es "compro"), o un "hago" o un "de" sueltos, tampoco.
    para dicho en ["compró 10 yerbas", "llevó 10 yerbas", "encargó 5 yerbas", "encargo de 5 yerbas",
                   "de 5 yerbas", "hago 5 yerbas", "hacerte 5 yerbas", "me hacer 5 yerbas",
                   "llevo 10 yerbas de mas"] {
        asegurar tiene(consultar_a_ventas(dicho, dicho), "Todavía no anoté nada: para pedirlo, escribí \\"quiero "), dicho
    }
    # Nadie reservó nada: la yerba está entera.
    asegurar largo(mensajes_enviados("Reservar")) == 0 y largo(consultas_ia()) == 0
    asegurar (preguntar CuantoQueda { producto: "Yerba mate" } a Deposito).unidades == stock_minimo + 100000
    # Con la unidad de venta adelante sí está claro.
    asegurar empieza_con(pedir_y_confirmar("x", "quiero 1 bolsón de yerba"), "Anotado: 1 x Yerba mate")
    asegurar empieza_con(pedir_y_confirmar("y", "quiero 3 bolsas de azucar de 10 kg"), "Anotado: 3 x Azúcar")
}

prueba "con una planilla propia: la presentación que arranca con un número, o que nombra al producto" {
    sea propia = [{ producto: "Agua mineral", presentacion: "6 botellas de 2 litros", precio: 5400, stock: 100000 },
                  { producto: "Alfajores", presentacion: "12 unidades", precio: 9600, stock: 100000 },
                  { producto: "Vino", presentacion: "6 botellas", precio: 14500, stock: 100000 },
                  { producto: "Huevos", presentacion: "maple de 30 huevos", precio: 14500, stock: 100000 },
                  { producto: "Galletitas", presentacion: "caja con 24 paquetes para kiosco", precio: 14500, stock: 100000 },
                  { producto: "Paquete regalo", presentacion: "caja de 6 paquetes", precio: 12000, stock: 100000 },
                  { producto: "Grisines", presentacion: "paquete de 3 unidades sin sal", precio: 2100, stock: 100000 },
                  { producto: "Lavandina", presentacion: "bidón de 5 litros", precio: 3300, stock: 100000 },
                  { producto: "Sidra", presentacion: "caja de botellas", precio: 3300, stock: 100000 },
                  { producto: "Dulce de leche", presentacion: "caja de 12 potes", precio: 3300, stock: 100000 }]
    abrir_el_negocio(propia)
    # Si la presentación ARRANCA con un número no hay palabra para el bulto: lo que nombra
    # es lo de adentro. "6 botellas de agua" puede ser 1 bulto o 6.
    asegurar unidad_de_venta(propia[0]) == "" y unidad_de_venta({ producto: "Tomate", presentacion: "x 6 latas" }) == ""
    asegurar consultar_a_ventas("a", "quiero 6 botellas de agua") == "Todavía no anoté nada, para no equivocarme: dijiste \\"botellas\\", y Agua mineral se vende así: 6 botellas de 2 litros, a $ 5.400,00 cada bulto. ¿Cuántos bultos querés? Por ejemplo, para llevar uno solo: \\"quiero 1 bulto de agua\\"."
    # Y si lo de adentro se llama como el producto ("maple de 30 huevos"), "30 huevos"
    # puede ser 1 maple o 30: el ejemplo de la respuesta va con la unidad de venta.
    asegurar consultar_a_ventas("b", "quiero 30 huevos") == "Todavía no anoté nada, para no equivocarme: dijiste \\"huevos\\", y Huevos se vende por maple de 30 huevos, a $ 14.500,00 cada uno. ¿Cuántos querés de esos? Por ejemplo, para llevar uno solo: \\"quiero 1 maple de huevos\\"."
    para dicho en ["quiero 12 unidades de alfajores", "quiero 6 botellas de vino", "quiero 2 huevos",
                   "quiero 6 paquetes regalo", "dame 6 paquetes regalo, gracias",
                   "quiero 3 unidades de grisines", "quiero 2 lavandinas de 5 litros",
                   "quiero 6 botellas de sidra", "quiero 12 potes de dulce de leche"] {
        asegurar empieza_con(consultar_a_ventas(dicho, dicho), "Todavía no anoté nada, para no equivocarme: dijiste \\""), dicho
    }
    asegurar largo(mensajes_enviados("Reservar")) == 0 y largo(mensajes_enviados("ConsultarStock")) == 0
    asegurar (preguntar CuantoQueda { producto: "Agua mineral" } a Deposito).unidades == 100000
    # Con el nombre del producto, con "bultos" o con la unidad de venta, se anota. Y las
    # palabras de la presentación que no llevan un número adelante ("sin sal", "para
    # kiosco") describen: no son una unidad, y no frenan un pedido corriente.
    para dicho en ["quiero 2 aguas", "quiero 2 bultos de vino", "quiero 2 alfajores",
                   "quiero 2 maples de huevos", "quiero huevos, 2 maples",
                   "quiero 2 cajas de paquete regalo", "quiero 2 galletitas para kiosco",
                   "quiero 2 cajas de galletitas", "quiero 2 grisines sin sal",
                   "quiero 2 bidones de 5 litros de lavandina", "quiero 2 cajas de sidra",
                   "quiero 2 dulce de leche", "dulce de leche 2 cajas"] {
        asegurar empieza_con(pedir_y_confirmar(dicho, dicho), "Anotado: 2 x "), dicho
    }
    asegurar largo(mensajes_enviados("Reservar")) == 13
    asegurar unidades_de_adentro(propia[4]) == ["paquetes"] y unidades_de_adentro(propia[8]) == ["botellas"]
}

prueba "el 'de' del nombre de un producto, adelante de la cantidad, no frena el pedido" {
    abrir_el_negocio(lista_de_prueba() + [{ producto: "Aceite de girasol", presentacion: "caja de 12 botellas de 900 ml", precio: 31200, stock: 100000 }])
    para dicho en ["aceite de girasol 2 cajas", "quiero aceite de girasol 2",
                   "quiero aceite de girasol, 2 cajas", "quiero hacer un pedido de aceite de girasol: 2 cajas"] {
        asegurar empieza_con(pedir_y_confirmar(dicho, dicho), "Anotado: 2 x Aceite de girasol"), dicho
    }
    para dicho en ["de yerba quiero 2", "quiero de yerba 2", "buenas tardes, de yerba 2 bolsones"] {
        asegurar empieza_con(pedir_y_confirmar(dicho, dicho), "Anotado: 2 x Yerba mate"), dicho
    }
    asegurar largo(mensajes_enviados("Reservar")) == 7
    # Pegado a la cantidad, el "de" sigue hablando de algo que ya existe.
    para dicho en ["encargo de 5 yerbas", "de 5 yerbas", "encargo de unas 5 yerbas", "el encargo de yerba 5"] {
        asegurar tiene(consultar_a_ventas(dicho, dicho), "Todavía no anoté nada: para pedirlo, escribí \\"quiero "), dicho
    }
    asegurar largo(mensajes_enviados("Reservar")) == 7
}

prueba "devolver o anular no anota nada, y Ventas dice que eso lo arregla una persona" {
    abrir_el_negocio(lista_de_prueba())
    simular_ia("Listo, te lo anulé.")
    para dicho en ["devuelvo 5 yerbas", "cancelame 5 yerbas", "anulame el pedido de 5 yerbas",
                   "ya no quiero 5 yerbas"] {
        asegurar consultar_a_ventas(dicho, dicho) == respuesta_de_anular(), dicho
    }
    asegurar largo(consultas_ia()) == 0 y largo(mensajes_enviados("Reservar")) == 0
}

prueba "el contrato no deja saltearse a Ventas ni hablarle a Compras por afuera" {
    abrir_el_negocio(lista_de_prueba())
    # El programa no le puede pedir una reserva a Depósito: eso es de Ventas.
    asegurar falla { preguntar Reservar { charla: "a", producto: "Yerba mate", cantidad: 5 } a Deposito }
    # Ni pedirle una reposición a Compras: eso es de Depósito.
    asegurar falla { preguntar Reponer { charla: "b", producto: "Yerba mate", quedan: 1 } a Compras }
    asegurar (preguntar QueFalta {} a Compras).pedidos == []
}

prueba "lo que no es un pedido va a la IA, y un precio inventado no le llega al cliente" {
    abrir_el_negocio(lista_de_prueba())
    simular_ia("¡Hola! Tenemos yerba y azúcar.")
    asegurar consultar_a_ventas("a", "hola, ¿qué tienen?") == "¡Hola! Tenemos yerba y azúcar."
    # Un precio que no está en la lista: salta el freno y llega la reserva.
    simular_ia("El café sale $ 12.000.")
    asegurar no tiene(consultar_a_ventas("b", "¿y café?"), "12.000")
    # Para eso nadie le habló a Depósito.
    asegurar largo(mensajes_enviados("Reservar")) == 0
}

prueba "nada se anota sin un 'si': Ventas repite el pedido, con los bultos, y espera" {
    abrir_el_negocio(lista_de_prueba())
    # (aunque la IA "quiera" decir que anotó, el freno no la deja)
    simular_ia("Listo, anotado: 2 yerbas.")
    sea pregunta = "Entendí: 2 x Yerba mate (bolsón de 10 paquetes de 1 kg) a $ 35.000,00 cada uno: total $ 70.000,00. Son 2 bolsones enteros. ¿Lo anoto? Contestá si o no."
    # Con "no" no se anota nada.
    asegurar consultar_a_ventas("a", "quiero 2 yerbas") == pregunta
    asegurar consultar_a_ventas("b", "no") == "Listo: no anoté nada."
    # Con cualquier otra cosa tampoco: Ventas avisa que lo de antes no quedó anotado, y
    # atiende lo nuevo. Y el pedido deja de esperar: un "si" tardío no lo anota.
    para otra_cosa en ["si?", "si pero que sean 5", "si no", "no si", "bueno", "1", "uno solo",
                       "si quiero", "claro que no", "s", "y si mejor llevo 3?",
                       "si, y mandame 5 azucar", "dale que va"] {
        asegurar consultar_a_ventas("pide y sigue: {otra_cosa}", "quiero 2 yerbas") == pregunta
        sea contestado = consultar_a_ventas(otra_cosa, otra_cosa)
        asegurar empieza_con(contestado, "No anoté lo de antes (2 x Yerba mate): no me contestaste que sí. "), otra_cosa
        asegurar no tiene(contestado, "Anotado"), otra_cosa
        consultar_a_ventas("no, después de: {otra_cosa}", "no")
        asegurar consultar_a_ventas("si, después de: {otra_cosa}", "si") == respuesta_sin_pedido(), otra_cosa
    }
    asegurar largo(mensajes_enviados("Reservar")) == 0 y largo(mensajes_enviados("Reponer")) == 0
    asegurar (preguntar CuantoQueda { producto: "Yerba mate" } a Deposito).unidades == stock_minimo + 100000
    # Si la otra cosa es un pedido nuevo, lleva su propia pregunta: el "si" que sigue
    # anota ESE, y no el de antes. Y un segundo "si" no anota de nuevo.
    asegurar consultar_a_ventas("g", "quiero 2 yerbas") == pregunta
    asegurar consultar_a_ventas("h", "quiero 3 yerbas") == "No anoté lo de antes (2 x Yerba mate): no me contestaste que sí. Entendí: 3 x Yerba mate (bolsón de 10 paquetes de 1 kg) a $ 35.000,00 cada uno: total $ 105.000,00. Son 3 bolsones enteros. ¿Lo anoto? Contestá si o no."
    asegurar consultar_a_ventas("i", "si") == "Anotado: 3 x Yerba mate (bolsón de 10 paquetes de 1 kg) a $ 35.000,00 cada uno: total $ 105.000,00."
    asegurar consultar_a_ventas("j", "si") == respuesta_sin_pedido()
    asegurar largo(mensajes_enviados("Reservar")) == 1
    asegurar (preguntar CuantoQueda { producto: "Yerba mate" } a Deposito).unidades == stock_minimo + 100000 - 3
    # El "si" se puede decir de varias maneras, pero tiene que ser lo único que se dice.
    sea maneras = ["si", "Sí", "SI", "sí.", "dale", "ok", "confirmo", "anotalo", "si, anotalo",
                   "sí, por favor", "dale, gracias"]
    para manera en maneras {
        consultar_a_ventas("pide y contesta: {manera}", "quiero 1 yerba")
        asegurar empieza_con(consultar_a_ventas(manera, manera), "Anotado: 1 x Yerba mate"), manera
    }
    asegurar largo(mensajes_enviados("Reservar")) == 1 + largo(maneras)
    asegurar es_un_si("  Sí, dale ") y no es_un_si("si?") y no es_un_si("si pero no") y no es_un_si("gracias")
    asegurar es_un_no("No, gracias") y es_un_no("mejor no") y no es_un_no("no se") y no es_un_no("si")
}

prueba "el 'si' de un cliente no confirma el pedido de otro: cada uno tiene el suyo" {
    abrir_el_negocio(lista_de_prueba())
    sea hay = stock_minimo + 100000
    # Ana pide. Antes de que conteste, Beto (otro cliente) dice "si": no tiene ningún
    # pedido esperando, así que no se anota nada. El stock sigue igual.
    asegurar empieza_con(consultar_a_ventas("ana-1", "quiero 2 yerbas", "ana"), "Entendí: 2 x Yerba mate")
    asegurar consultar_a_ventas("beto-1", "si", "beto") == respuesta_sin_pedido()
    asegurar largo(mensajes_enviados("Reservar")) == 0
    asegurar (preguntar CuantoQueda { producto: "Yerba mate" } a Deposito).unidades == hay
    # El pedido de Ana sigue esperando SU "si": lo de Beto no lo borró ni lo anotó.
    asegurar empieza_con(consultar_a_ventas("ana-2", "si", "ana"), "Anotado: 2 x Yerba mate")
    asegurar largo(mensajes_enviados("Reservar")) == 1
    asegurar (preguntar CuantoQueda { producto: "Yerba mate" } a Deposito).unidades == hay - 2
    # Con un pedido esperando de cada uno, cada "si" anota el propio y el "no" de uno no
    # toca el del otro. El del teclado es un cliente más.
    asegurar empieza_con(consultar_a_ventas("ana-3", "quiero 1 yerba", "ana"), "Entendí: 1 x Yerba mate")
    asegurar empieza_con(consultar_a_ventas("beto-2", "quiero 3 yerbas", "beto"), "Entendí: 3 x Yerba mate")
    asegurar consultar_a_ventas("t-1", "si") == respuesta_sin_pedido()
    asegurar (preguntar DejarDeEsperar { cliente: "teclado" } a Ventas).aviso == ""
    asegurar consultar_a_ventas("ana-4", "no", "ana") == "Listo: no anoté nada."
    asegurar empieza_con(consultar_a_ventas("beto-3", "si", "beto"), "Anotado: 3 x Yerba mate")
    asegurar largo(mensajes_enviados("Reservar")) == 2
    asegurar (preguntar CuantoQueda { producto: "Yerba mate" } a Deposito).unidades == hay - 5
}

prueba "un 'no' dicho de otra manera no se toma como sí: 'ok, dejá' no anota" {
    abrir_el_negocio(lista_de_prueba())
    simular_ia("Decime qué producto querés y cuántas unidades.")
    # Es lo que contesta quien vio en la pregunta que Ventas entendió mal. Al lado de
    # "dejá" o "cancelalo", el "ok" o el "dale" son una muletilla: es un no.
    para dicho en ["ok, dejá", "dale, dejá nomás", "si, mejor deja", "dejá", "no, dejá", "mejor no",
                   "no, dejá nomás", "ok, cancelalo", "no, muchas gracias", "No, gracias"] {
        asegurar empieza_con(consultar_a_ventas("pide y contesta: {dicho}", "quiero 6 yerbas"), "Entendí: 6 x Yerba mate"), dicho
        asegurar consultar_a_ventas(dicho, dicho) == "Listo: no anoté nada.", dicho
        asegurar no es_un_si(dicho) y es_un_no(dicho), dicho
        # (y el pedido dejó de esperar: un "si" tardío no lo anota)
        asegurar consultar_a_ventas("si, después de: {dicho}", "si") == respuesta_sin_pedido(), dicho
    }
    # Al sí lo acompaña solo la cortesía ("por favor", "gracias"): con cualquier otra
    # palabra al lado ya no es un sí, aunque tampoco diga que no.
    para dicho en ["ok mejor", "por confirmar", "dale nomás", "si, mejor", "si por", "si, muchas",
                   "si favor", "ok, mejor mañana", "por favor", "muchas gracias", "si no", "no si"] {
        asegurar empieza_con(consultar_a_ventas("pide y sigue: {dicho}", "quiero 6 yerbas"), "Entendí: 6 x Yerba mate"), dicho
        sea contestado = consultar_a_ventas(dicho, dicho)
        asegurar empieza_con(contestado, "No anoté lo de antes (6 x Yerba mate): no me contestaste que sí. "), dicho
        asegurar no tiene(contestado, "Anotado") y no es_un_si(dicho) y no es_un_no(dicho), dicho
        asegurar consultar_a_ventas("si, después de: {dicho}", "si") == respuesta_sin_pedido(), dicho
    }
    asegurar largo(mensajes_enviados("Reservar")) == 0
    asegurar (preguntar CuantoQueda { producto: "Yerba mate" } a Deposito).unidades == stock_minimo + 100000
    asegurar es_un_si("si, por favor") y es_un_si("dale, muchas gracias") y es_un_si("ok porfa") y es_un_si("Sí, gracias")
    # Con el ingreso, igual: nada de esto lo suma. (Los dos renglones que no son ni sí ni
    # no, "si" y "por confirmar", van a Ventas como consultas.)
    simular_teclado(["ingreso 1 yerba", "ok, dejá", "si", "ingreso 1 yerba", "dale, dejá nomás",
                     "ingreso 1 yerba", "si, mejor deja", "ingreso 1 yerba", "por confirmar", "chau"])
    asegurar charlar_con_el_equipo(lista_de_prueba()) == 2
    asegurar largo(mensajes_enviados("Ingreso")) == 0 y largo(mensajes_enviados("Reservar")) == 0
    asegurar (preguntar CuantoQueda { producto: "Yerba mate" } a Deposito).unidades == stock_minimo + 100000
}

prueba "lo que espera el 'si' no sobrevive a un comando ni a irse de la charla" {
    abrir_el_negocio(lista_de_prueba())
    # Un texto que parece un comando de PowerShell no es un "si": el pedido (y el ingreso)
    # deja de esperar, y el "si" que venga después no anota nada. Irse con "listo" tampoco.
    # Un Enter solo, en cambio, no contesta nada: la pregunta sigue en pie (el pedido del
    # medio es el único que se anota).
    simular_teclado(["quiero 6 yerbas", "Get-ChildItem", "si",
                     "ingreso 1 yerba", "Get-ChildItem", "si",
                     "quiero 6 yerbas", "", "si",
                     "quiero 6 yerbas", "listo"])
    asegurar charlar_con_el_equipo(lista_de_prueba()) == 6
    asegurar largo(mensajes_enviados("Reservar")) == 1 y largo(mensajes_enviados("Ingreso")) == 0
    asegurar (preguntar CuantoQueda { producto: "Yerba mate" } a Deposito).unidades == stock_minimo + 100000 - 6
    # (se fue con "listo" sin contestar: Ventas ya no espera nada)
    asegurar consultar_a_ventas("a", "si") == respuesta_sin_pedido()
    asegurar largo(mensajes_enviados("Reservar")) == 1
}

prueba "las frases que Ventas entendía mal ya no descuentan stock: se ven en la pregunta" {
    # La lista de las pruebas y, además, presentaciones con la cuenta adentro ("pack x 6").
    sea propia = lista_de_prueba() + [{ producto: "Cerveza rubia", presentacion: "pack x 6", precio: 7200, stock: 100000 },
                                      { producto: "Vino tinto", presentacion: "caja x 6", precio: 14500, stock: 100000 },
                                      { producto: "Atún", presentacion: "x 6 latas", precio: 9000, stock: 100000 },
                                      { producto: "Agua mineral", presentacion: "caja de 12 botellas", precio: 5400, stock: 100000 }]
    abrir_el_negocio(propia)
    # El cliente quería UN pack, y Ventas entendió 6: ahora se lo dice antes de anotar.
    asegurar consultar_a_ventas("a", "quiero un pack x 6 de cerveza") == "Entendí: 6 x Cerveza rubia (pack x 6) a $ 7.200,00 cada uno: total $ 43.200,00. Son 6 packs enteros. ¿Lo anoto? Contestá si o no."
    asegurar consultar_a_ventas("b", "no") == "Listo: no anoté nada."
    # Si la cantidad es justo un número de adentro del bulto, lo dice con todas las letras.
    asegurar consultar_a_ventas("c", "quiero un bolson x 10 de yerba") == "Entendí: 10 x Yerba mate (bolsón de 10 paquetes de 1 kg) a $ 35.000,00 cada uno: total $ 350.000,00. Son 10 bolsones enteros (no 10 paquetes). ¿Lo anoto? Contestá si o no."
    consultar_a_ventas("d", "no")
    para dicho en ["quiero una caja x 6 de vino", "quiero caja x 6 botellas de vino",
                   "quiero un bulto x 6 de atun", "quiero bolsa x 10 azucar",
                   "quiero 10 unidades de yerba", "quiero 12 unidades de agua",
                   "quiero 6 unidades de cerveza", "quiero 6 vinos", "quiero 6 x cerveza",
                   "cerveza pack x 6", "yerba x 10", "compro 10 yerbas",
                   "hola, 5 yerbas para retirar", "5 yerbas a retirar", "10 yerbas retiro",
                   "llevo 10 yerbas al local", "yo llevo 10 yerbas", "encargo de yerba 5",
                   "quiero 2 bultos de yerba", "quiero 10 paquetes de yerba", "compró 10 yerbas"] {
        sea contestado = consultar_a_ventas(dicho, dicho)
        asegurar no tiene(contestado, "Anotado"), dicho
        si empieza_con(contestado, "Entendí: ") {
            # (la pregunta dice cuántos bultos son, con la unidad en que se vende)
            asegurar tiene(contestado, " enteros") o tiene(contestado, " enteras"), contestado
            asegurar termina_con(contestado, "¿Lo anoto? Contestá si o no."), contestado
        } sino {
            asegurar tiene(contestado, "Todavía no anoté nada"), contestado
        }
        # El cliente ve que no era eso, y dice que no.
        consultar_a_ventas("{dicho} (el no)", "no")
    }
    asegurar largo(mensajes_enviados("Reservar")) == 0 y largo(mensajes_enviados("Reponer")) == 0
    para fila en propia {
        asegurar (preguntar CuantoQueda { producto: fila.producto } a Deposito).unidades == fila.stock, fila.producto
    }
    # Dicho bien, y con el "si", se anota lo que el cliente quería: un pack.
    asegurar pedir_y_confirmar("z", "quiero 1 cerveza") == "Anotado: 1 x Cerveza rubia (pack x 6) a $ 7.200,00 cada uno: total $ 7.200,00."
    asegurar en_bultos(propia[0], 2) == "Son 2 bolsones enteros." y en_bultos(propia[0], 1) == "Es 1 bolsón entero."
    asegurar en_bultos(propia[5], 6) == "Son 6 bultos enteros (no 6 latas)." y en_plural("bidón") == "bidones"
}

prueba "el ingreso de mercadería también pide el 'si' antes de sumar" {
    abrir_el_negocio(lista_de_prueba())
    # (de a 1, para que la prueba pase también con un ingreso_maximo chico)
    asegurar pregunta_de_ingreso(leer_ingreso(lista_de_prueba(), "ingreso 1 yerba")) == "Entendí: entran 1 x Yerba mate (bolsón de 10 paquetes de 1 kg). Es 1 bolsón entero. ¿Lo sumo? Contestá si o no."
    asegurar pregunta_de_ingreso({ fila: lista_de_prueba()[1], cantidad: 30 }) == "Entendí: entran 30 x Azúcar (bolsa de 10 kg). Son 30 bolsas enteras. ¿Lo sumo? Contestá si o no."
    # Sin el "si" no entra nada: ni con "no", ni con otra cosa, ni con otro ingreso (ese
    # pregunta de nuevo), ni cortando la charla con el ingreso esperando.
    simular_teclado(["ingreso 1 yerba", "no", "ingreso 1 yerba", "uy, era de azucar",
                     "ingreso 1 yerba", "ingreso 1 azucar", "si?", "ingreso 1 yerba", "chau"])
    asegurar charlar_con_el_equipo(lista_de_prueba()) == 2
    asegurar largo(mensajes_enviados("Ingreso")) == 0
    asegurar (preguntar CuantoQueda { producto: "Yerba mate" } a Deposito).unidades == stock_minimo + 100000
}

prueba "con el 'si' el ingreso entra una sola vez, y un 'si' contesta lo último que se preguntó" {
    abrir_el_negocio(lista_de_prueba())
    # El segundo "si" va a Ventas, que no tiene ningún pedido esperando. Si en el medio de
    # un pedido se anota un ingreso, el pedido deja de esperar: el "si" del ingreso no lo
    # anota. Y con un ingreso esperando, el "si" a un pedido no suma el ingreso.
    simular_teclado(["ingreso 1 yerba", "si", "si",
                     "quiero 2 yerbas", "ingreso 1 yerba", "si", "si",
                     "ingreso 1 yerba", "quiero 3 yerbas", "si", "chau"])
    asegurar charlar_con_el_equipo(lista_de_prueba()) == 5
    asegurar largo(mensajes_enviados("Ingreso")) == 2 y largo(mensajes_enviados("Reservar")) == 1
    asegurar (preguntar CuantoQueda { producto: "Yerba mate" } a Deposito).unidades == stock_minimo + 100000 + 2 - 3
}

prueba "el horario, la dirección o cómo se paga los contesta Ventas sin IA: sin cargar, no se inventan" {
    # (con datos fijos, no con los tuyos: así pasa aunque cargues tu horario)
    abrir_el_negocio(lista_de_prueba(), {})
    # Aunque la IA "quiera" inventar un horario, nadie le pregunta.
    simular_ia("Atendemos de lunes a viernes de 8 a 18 hs.")
    para dicho en ["hola, que horarios tienen?", "¿A qué hora abren?", "hasta que hora estan abiertos?"] {
        asegurar consultar_a_ventas(dicho, dicho) == "Sobre el horario: eso te lo confirma una persona.", dicho
    }
    asegurar consultar_a_ventas("a", "¿dónde quedan?") == "Sobre la dirección: eso te lo confirma una persona."
    asegurar consultar_a_ventas("b", "me pasás un teléfono?") == "Sobre el teléfono: eso te lo confirma una persona."
    asegurar consultar_a_ventas("c", "aceptan tarjeta?") == "Sobre las formas de pago: eso te lo confirma una persona."
    asegurar consultar_a_ventas("d", "cuanto demora la entrega?") == "Sobre las entregas: eso te lo confirma una persona."
    asegurar consultar_a_ventas("e", "tienen alguna promo?") == "Sobre las promociones: eso te lo confirma una persona."
    asegurar largo(consultas_ia()) == 0
    asegurar largo(mensajes_enviados("ConsultarStock")) == 0 y largo(mensajes_enviados("Reservar")) == 0
    # Un dato cargado se dice tal cual está escrito. Tampoco se consulta a la IA.
    abrir_el_negocio(lista_de_prueba(), { horario: "Lunes a viernes de 8 a 17", formas_de_pago: "Efectivo o transferencia" })
    asegurar consultar_a_ventas("f", "hola, que horarios tienen?") == "Horario: Lunes a viernes de 8 a 17."
    asegurar consultar_a_ventas("g", "aceptan tarjeta?") == "Formas de pago: Efectivo o transferencia."
    asegurar consultar_a_ventas("h", "horario y direccion?") == "Horario: Lunes a viernes de 8 a 17. Sobre la dirección: eso te lo confirma una persona."
    # Un teléfono SIN comillas no se dice: Mate toma 4555-1234 por una resta (da 3321).
    # Cuenta como vacío, y la prueba de la planilla dice qué arreglar.
    sea sin_comillas = { telefono: 4555 - 1234 }
    abrir_el_negocio(lista_de_prueba(), sin_comillas)
    asegurar consultar_a_ventas("i", "cual es el telefono?") == "Sobre el teléfono: eso te lo confirma una persona."
    asegurar tiene(datos_mal_puestos(sin_comillas), "el dato 'telefono' está sin comillas")
    # El nombre de un dato cambiado ("Horario", con mayúscula) también se avisa.
    asegurar tiene(datos_mal_puestos({ Horario: "8 a 17" }), "tiene que quedar escrito 'horario'")
    asegurar largo(consultas_ia()) == 0
}

prueba "si la IA igual inventa un horario, un teléfono o una forma de pago, no le llega al cliente" {
    abrir_el_negocio(lista_de_prueba(), {})
    # La pregunta no nombra el horario, así que va a la IA; y la IA lo inventa.
    para inventada en ["¡Hola! Atendemos de lunes a viernes de 8 a 18hs.", "Abrimos a las 9.",
                       "Llamanos al 11 4555-1234.", "Podés pagar con tarjeta.",
                       "Te lo entregamos en 48 hs.", "Estamos en Av. Mitre 1234."] {
        simular_ia(inventada)
        asegurar termina_con(consultar_a_ventas(inventada, "hola"), ": eso te lo confirma una persona."), inventada
    }
    # Con el dato cargado, lo que coincide pasa; lo que no, se cambia por el dato.
    abrir_el_negocio(lista_de_prueba(), { horario: "Lunes a viernes de 8 a 17" })
    simular_ia("¡Hola! Atendemos de lunes a viernes de 8 a 17.")
    asegurar consultar_a_ventas("x", "hola") == "¡Hola! Atendemos de lunes a viernes de 8 a 17."
    simular_ia("¡Hola! Atendemos de lunes a sábado de 8 a 20.")
    asegurar consultar_a_ventas("y", "hola") == "Horario: Lunes a viernes de 8 a 17."
}

prueba "una hora, una dirección o un contacto inventados no llegan, se escriban como se escriban" {
    abrir_el_negocio(lista_de_prueba(), {})
    sea persona = ": eso te lo confirma una persona."
    sea inventadas = {
        "Abrimos desde las 8 hasta las 18.": "Sobre el horario",
        "Podés pasar hasta las 18, estamos todos los días.": "Sobre el horario",
        "Horario: 8-18.": "Sobre el horario",
        "Atendemos de ocho a dieciocho, de lun a vie.": "Sobre el horario",
        "Te esperamos en Av. Corrientes 1234.": "Sobre la dirección",
        "Escribinos a ventas@mayorista.com.ar.": "Sobre el teléfono",
        "Llamanos al 444-5555.": "Sobre el teléfono",
        "Podés pagar con Visa o Mastercard.": "Sobre las formas de pago",
        "Te llega mañana mismo.": "Sobre las entregas",
        "Tenemos 2x1 en yerba.": "Sobre las promociones"
    }
    para inventada, tema en inventadas {
        simular_ia(inventada)
        asegurar consultar_a_ventas(inventada, "hola") == tema + persona, inventada
    }
    # Una respuesta que no nombra ningún dato pasa como está.
    para buena en ["Cualquier cosa, estamos en contacto.", "Viene en bolsas de 10 a 25 kg.",
                   "Tenemos una amplia oferta de productos."] {
        simular_ia(buena)
        asegurar consultar_a_ventas(buena, "hola") == buena, buena
    }
    # Con los datos cargados, cada cosa se compara con el dato de su tema: el "11" del
    # teléfono no habilita una hora, y lo que el dato niega no se puede afirmar.
    abrir_el_negocio(lista_de_prueba(), { horario: "Lunes a viernes de 8 a 17", telefono: "11 4555-1234",
                              formas_de_pago: "Efectivo o transferencia. No aceptamos tarjeta" })
    simular_ia("Abrimos a las 11.")
    asegurar consultar_a_ventas("x", "hola") == "Horario: Lunes a viernes de 8 a 17."
    simular_ia("Aceptamos tarjeta.")
    asegurar consultar_a_ventas("y", "hola") == "Formas de pago: Efectivo o transferencia. No aceptamos tarjeta."
    simular_ia("Atendemos lunes de 17 a 8.")
    asegurar consultar_a_ventas("z", "hola") == "Horario: Lunes a viernes de 8 a 17."
}

prueba "las preguntas corrientes por el horario, la dirección o el pago no le llegan a la IA" {
    abrir_el_negocio(lista_de_prueba(), {})
    simular_ia("Podés pasar hasta las 18, estamos todos los días.")
    sea persona = ": eso te lo confirma una persona."
    para dicho en ["que dias trabajan?", "mañana trabajan?", "que dias estan?", "estan a la tarde?",
                   "cuando puedo pasar?"] {
        asegurar consultar_a_ventas(dicho, dicho) == "Sobre el horario" + persona, dicho
    }
    asegurar consultar_a_ventas("a", "como llego?") == "Sobre la dirección" + persona
    asegurar consultar_a_ventas("b", "tienen pagina web?") == "Sobre el teléfono" + persona
    asegurar consultar_a_ventas("c", "te hago una transfe?") == "Sobre las formas de pago" + persona
    asegurar largo(consultas_ia()) == 0
    # Un saludo o una pregunta por un producto no son una pregunta por un dato: van a la IA.
    simular_ia("¡Hola! ¿Qué necesitás?")
    para dicho en ["hola buen dia", "buenas tardes", "trabajan cafe?", "me podes pasar la lista?"] {
        asegurar consultar_a_ventas(dicho, dicho) == "¡Hola! ¿Qué necesitás?", dicho
    }
}

prueba "si preguntan por un producto y por un dato, Ventas da el renglón de la lista y el dato, sin IA" {
    abrir_el_negocio(lista_de_prueba(), {})
    simular_ia("Atendemos de lunes a viernes de 8 a 18 hs.")
    sea yerba = "Yerba mate (bolsón de 10 paquetes de 1 kg): $ 35.000,00."
    asegurar consultar_a_ventas("a", "cuanto sale la yerba? aceptan tarjeta?") == yerba + " Sobre las formas de pago: eso te lo confirma una persona."
    asegurar consultar_a_ventas("b", "donde consigo yerba?") == yerba + " Sobre la dirección: eso te lo confirma una persona."
    # De fideos no hay: Ventas se lo pregunta a Depósito y lo avisa también acá.
    asegurar consultar_a_ventas("c", "tenes fideos? abren sabados?") == "Fideos secos (caja de 20 paquetes de 500 g): $ 18.900,00. De Fideos secos ahora no hay stock. Sobre el horario: eso te lo confirma una persona."
    asegurar largo(consultas_ia()) == 0 y largo(mensajes_enviados("Reservar")) == 0
    asegurar largo(mensajes_enviados("ConsultarStock")) == 3
    # En la cuenta de un pedido, "pago" o "sábado" no agregan nada.
    asegurar no tiene(consultar_a_ventas("d", "cuanto pago por 12 azucar?"), "persona")
    asegurar no tiene(consultar_a_ventas("e", "quiero 12 azucar para el sabado"), "persona")
}

prueba "si la IA dice que no lo tienen pero ofrece conseguirlo, Ventas dice solo que no se trabaja" {
    abrir_el_negocio(lista_de_prueba(), {})
    simular_ia("Lamentablemente no tenemos café, pero te lo puedo conseguir para más adelante.")
    asegurar consultar_a_ventas("a", "tenes cafe?") == "Eso no lo trabajamos."
}

prueba "de lo que no está en la lista dice solo que no lo trabaja, y de lo que está en cero avisa" {
    abrir_el_negocio(lista_de_prueba(), {})
    simular_ia("Lo siento, no trabajamos con café. Podés pedirlo si querés y cuántas unidades.")
    asegurar consultar_a_ventas("a", "tenes cafe?") == "Eso no lo trabajamos."
    asegurar largo(mensajes_enviados("ConsultarStock")) == 0
    # De fideos, en la lista de las pruebas, no hay: Ventas se lo pregunta a Depósito, y
    # lo avisa el programa, no la IA.
    simular_ia("Sí, tenemos fideos secos.")
    asegurar consultar_a_ventas("b", "tenes fideos?") == "Sí, tenemos fideos secos. De Fideos secos ahora no hay stock."
    asegurar largo(mensajes_enviados("ConsultarStock")) == 1
}
"""


def _tramo(texto, desde, hasta, archivo, carpeta):
    """Lo que hay en el texto de un ejemplo entre dos de sus títulos (sin el renglón en
    blanco de adelante). Si alguno de los dos no está, falla con un ErrorMate."""
    inicio = texto.find(desde)
    fin = texto.find(hasta, inicio + 1) if inicio >= 0 else -1
    if fin < 0:
        raise ErrorMate(
            f"no pude armar el equipo: {archivo} (en {para_pegar(carpeta)}) "
            "no tiene la forma que espero. ¿Lo cambiaste? Bajá Mate de nuevo para tener "
            "el ejemplo original", familia="archivo")
    return texto[inicio + 1:fin + 1]


def archivos_del_equipo(nombre, orden, carpeta_de_mate=None, fin_de_renglon=None):
    """Lo que crea 'nuevo equipo <nombre>': {nombre del archivo: su contenido, en bytes}:
    el programa, la planilla y los casos para 'ensayar', en ese orden. Falla con un
    ErrorMate si en la carpeta de Mate falta alguno de los ejemplos, o si ya no tienen los
    títulos que marcan qué partes se copian."""
    carpeta = os.path.join(carpeta_de_mate or os.path.dirname(os.path.abspath(__file__)),
                           CARPETA_DE_EJEMPLOS)
    programa, planilla = f"{nombre}.mate", f"{nombre}_precios.csv"
    casos = f"{nombre}_casos.txt"
    try:
        equipo = leer_fuente(os.path.join(carpeta, EJEMPLO_DEL_EQUIPO))
        mostrador = leer_fuente(os.path.join(carpeta, EJEMPLO_DEL_MOSTRADOR))
        with open(os.path.join(carpeta, PLANILLA_DE_MUESTRA), "rb") as f:
            muestra = f.read()
        de_muestra = leer_fuente(os.path.join(carpeta, CASOS_DEL_EQUIPO))
    except OSError:
        raise ErrorMate(
            f"para crear un equipo hacen falta {EJEMPLO_DEL_EQUIPO}, {EJEMPLO_DEL_MOSTRADOR}, "
            f"{PLANILLA_DE_MUESTRA} y {CASOS_DEL_EQUIPO}, que vienen con Mate, y no los "
            f"encuentro en {para_pegar(carpeta)}. Si copiaste solo mate.py, bajá Mate de "
            "nuevo con todas sus carpetas", familia="archivo")
    regla, pedidos, revisar = (_tramo(mostrador, desde, hasta, EJEMPLO_DEL_MOSTRADOR, carpeta)
                               for desde, hasta in _DEL_12_PARA_EL_EQUIPO)
    agentes = _tramo(equipo, _EQUIPO_DESDE, _EQUIPO_PROGRAMA, EJEMPLO_DEL_EQUIPO, carpeta)
    el_programa = _tramo(equipo, _EQUIPO_PROGRAMA, _EQUIPO_HASTA, EJEMPLO_DEL_EQUIPO, carpeta)
    # El orden: lo que se puede cambiar va arriba (la regla del envío, el mínimo, los
    # agentes); después, las funciones que entienden los pedidos; y al final el programa.
    texto = "\n".join((
        _ENCABEZADO_DEL_EQUIPO, regla, agentes,
        "# ── Entender los pedidos y revisar la planilla ───────────────────────────────────────\n"
        "# De acá hasta el título \"El programa\" son las funciones del ejemplo 12: las que\n"
        "# entienden lo que escribió el cliente, hacen la cuenta y revisan la planilla.\n",
        pedidos + revisar + el_programa)).replace(PLANILLA_DE_MUESTRA, planilla)
    texto += _PRUEBAS_DEL_EQUIPO
    for marca, valor in (("«PROGRAMA»", programa), ("«PLANILLA»", planilla),
                         ("«CASOS»", casos), ("«ORDEN»", orden),
                         ("«MEMORIA»", archivo_de(programa, "memoria.json"))):
        texto = texto.replace(marca, valor)
    # Los casos de muestra traen, de nota, cómo se ensaya el ejemplo 13: acá va cómo se
    # ensaya este equipo (desde el título 'Cómo se escribe' es el mismo archivo).
    corte = de_muestra.find(_CASOS_DESDE)
    de_muestra = (f"# Casos para ensayar {programa}: lo que pregunta un cliente, lo que la "
                  "respuesta\n# tiene que decir (o no puede decir) y qué mensajes tienen que "
                  "viajar entre los\n# agentes (o no). Es tuyo: cambialos y "
                  "agregá los que quieras.\n# OJO: los casos que vienen acá son de muestra, "
                  "escritos para la planilla de muestra\n# (yerba, azúcar, fideos). Si cambiás "
                  f"los productos de {planilla}, cambiá\n# también estos casos: si no, "
                  "fallan los que nombran un producto que ya no está.\n"
                  "# Lo mismo con los datos del negocio (el horario, la dirección...): los "
                  "casos de\n# muestra esperan que estén vacíos. Cuando cargues los tuyos "
                  f"en {programa},\n# cambiá esos casos.\n"
                  "# Un ensayo no descuenta stock ni anota nada: cada pregunta arranca con "
                  "lo que\n# Depósito recuerda en ese momento. Si de un producto ya se "
                  "vendió casi todo, sus\n# casos van a contestar que no alcanza (para "
                  "volver al stock de la planilla:\n"
                  f"#     {orden} correr {programa} --olvidar ).\n"
                  "#\n# Cómo se usa, en PowerShell, parado en "
                  "la carpeta donde está este archivo:\n"
                  f"#     {orden} ensayar {programa} {casos} --ia-simulada\n"
                  "# (sin --ia-simulada contesta la IA de verdad: así se ve si una lección "
                  "funcionó)\n#\n") + de_muestra[max(corte, 0):]
    fin = os.linesep if fin_de_renglon is None else fin_de_renglon
    return {programa: texto.replace("\n", fin).encode("utf-8-sig"), planilla: muestra,
            casos: de_muestra.replace("\n", fin).encode("utf-8-sig")}


# Lo que sabe crear 'nuevo': con qué función se arman los archivos y de qué archivo de
# muestra salen los casos.
_QUE_CREA_NUEVO = {
    "mostrador": (archivos_del_mostrador, CASOS_DE_MUESTRA),
    "equipo": (archivos_del_equipo, CASOS_DEL_EQUIPO),
}


def orden_nuevo(args, avisar, mostrar=print):
    """La orden 'nuevo mostrador <nombre>' o 'nuevo equipo <nombre>': crea el programa, su
    planilla de muestra y sus casos en la carpeta actual, sin pisar nada, y dice los pasos
    que siguen. Devuelve el código de salida."""
    orden = orden_para_esta_carpeta()
    que = sin_tildes(args[0].lower()) if args else ""
    que_falta = "al escribir la orden: 'nuevo' sin decir qué crear o con qué nombre"
    if que == "socio":  # (0.8) el ensayo de dos negocios que se hablan
        return nuevo_socio(args[1:], avisar, mostrar)
    if que not in _QUE_CREA_NUEVO:
        avisar("después de 'nuevo' va qué crear y con qué nombre. Crea un mostrador o un "
               f"equipo de agentes:  {orden} nuevo mostrador mi_negocio   o   "
               f"{orden} nuevo equipo mi_negocio   (y el ensayo de dos negocios que se "
               f"hablan:  {orden} nuevo socio)", que_falta, True)
        return 2
    armar, casos_de_muestra = _QUE_CREA_NUEVO[que]
    ejemplo = f"{orden} nuevo {que} mi_negocio"
    if len(args) == 1:
        avisar(f"a 'nuevo {que}' le falta el nombre que le querés poner (una palabra, "
               f"sin espacios). Por ejemplo:  {ejemplo}", que_falta, True)
        return 2
    if len(args) > 2:
        avisar(f"el nombre del {que} va en una sola palabra, sin espacios (podés unir "
               f"con guion bajo):  {orden} nuevo {que} {'_'.join(args[1:])}",
               f"al escribir la orden: 'nuevo {que}' con un nombre con espacios", True)
        return 2
    nombre = re.sub(r"(?i)\.mate(\.txt)?$", "", args[1].strip())
    mal_nombre = f"al escribir la orden: 'nuevo {que}' con un nombre que no sirve"
    if re.search(r"[\\/:]", nombre):
        avisar(f"el {que} se crea en la carpeta donde estás parado: va solo el nombre, "
               f"sin carpeta. Por ejemplo:  {ejemplo}", mal_nombre, True)
        return 2
    if not re.fullmatch(r"[^\W_][\w\-]{0,59}", nombre):
        avisar(f"'{args[1]}' no sirve como nombre: usá letras, números, guion o guion bajo, "
               f"empezando con una letra o un número. Por ejemplo:  {ejemplo}", mal_nombre, True)
        return 2
    if sin_tildes(nombre.lower()) in ORDENES_SABIDAS + _NOMBRES_DE_WINDOWS:
        avisar(f"'{nombre}' no sirve como nombre: es una orden de Mate o un nombre que "
               f"Windows se reserva. Elegí otro, por ejemplo:  {ejemplo}", mal_nombre, True)
        return 2
    try:
        archivos = armar(nombre, orden)
    except ErrorMate as e:
        avisar(e.mensaje, f"al escribir la orden: 'nuevo {que}' sin los ejemplos de Mate")
        return 1
    programa, planilla, casos = list(archivos)
    # Nada se pisa: ni el programa, ni la planilla, ni los casos, ni la memoria o la
    # bitácora que haya dejado un programa viejo con ese nombre (el nuevo heredaría sus
    # lecciones y, en un equipo, su stock).
    ya_estan = [a for a in (programa, programa + ".txt", planilla, casos,
                            archivo_de(programa, "memoria.json"),
                            archivo_de(programa, "bitacora.txt")) if os.path.lexists(a)]
    if ya_estan:
        avisar(f"no creé nada: en esta carpeta ya hay {' y '.join(ya_estan)}, y no piso "
               "archivos. Elegí otro nombre (por ejemplo:  "
               f"{orden} nuevo {que} {nombre}_2) o mové esos archivos a otra carpeta"
               + ("" if casos in ya_estan or programa not in ya_estan else
                  f". Si lo que te falta es el archivo de casos para 'ensayar' ({casos}), "
                  "copiá el de muestra con ese nombre al lado del programa: está en "
                  + ruta_para_escribir(os.path.join(
                      os.path.dirname(os.path.abspath(__file__)), "ejemplos",
                      casos_de_muestra))),
               f"al escribir la orden: 'nuevo {que}' con un nombre que ya existe", True)
        return 1
    creados = []
    try:
        for archivo, contenido in archivos.items():
            with open(archivo, "xb") as f:  # ("x": si apareció recién, tampoco se pisa)
                creados.append(archivo)
                f.write(contenido)
    except OSError as e:
        for creado in creados:  # a medias no queda nada (solo se borra lo recién creado)
            try:
                os.remove(creado)
            except OSError:
                pass
        if isinstance(e, FileExistsError):
            avisar(f"no creé nada: recién apareció {archivo} en esta carpeta, y no piso "
                   "archivos. Elegí otro nombre")
        else:
            avisar(f"no pude crear {archivo} en {para_pegar(os.getcwd())}: fijate que se "
                   "pueda escribir en esa carpeta (o parate en otra, por ejemplo Documentos)")
        return 1
    ancho = max(len(a) for a in archivos)
    if que == "equipo":
        renglones = (
            f"Listo. Creé tres archivos en {para_pegar(os.getcwd())}:",
            f"  {programa.ljust(ancho)}   el programa: Ventas, Depósito y Compras",
            f"  {planilla.ljust(ancho)}   la planilla de precios y stock, con productos de muestra",
            f"  {casos.ljust(ancho)}   preguntas de clientes para ensayar el equipo",
            "",
            "Los pasos que siguen (cada comando se puede copiar tal cual):",
            "  1. Comprobar que quedó todo bien:",
            f"       {orden} probar {programa}",
            "  2. Charlar con el equipo sin gastar nada, viendo cómo se hablan los agentes.",
            "     Probá escribir: quiero 20 azucar   (Ventas repite el pedido y pregunta",
            "     \"¿Lo anoto?\": contestá si; y después: chau)",
            f"       {orden} correr {programa} --ia-simulada --traza",
            "  3. Correrlo de nuevo, sin --traza: el stock sigue donde quedó (Depósito lo",
            "     recuerda) y Compras muestra lo que anotó para reponer.",
            f"       {orden} correr {programa} --ia-simulada",
            "  4. Poner tus productos en la planilla (también se abre con Excel). El primer",
            "     renglón, el de los títulos, no se toca y va una sola vez:",
            f"       notepad {planilla}",
            "  5. Cargar los DATOS DE TU NEGOCIO: el horario, la dirección, el teléfono, las",
            "     formas de pago, las entregas. Están arriba del programa, en",
            "     datos_del_negocio: escribí cada uno entre las comillas y guardá.",
            f"       notepad {programa}",
            "     Vienen vacíos. Lo que dejes vacío no se inventa: a quien pregunte, Ventas",
            "     le contesta \"eso te lo confirma una persona\".",
            "  6. Comprobar de nuevo (paso 1) y atender con la IA de verdad. La primera vez",
            "     va con --olvidar, para que Depósito arranque con el stock de tu planilla:",
            f"       {orden} correr {programa} --olvidar",
            "     (Si usás un modelo propio, como Ollama: antes hay que decirle a Mate cuál",
            "     es, con la variable MATE_IA_PROPIA. El manual dice cómo.)",
            f"  7. Ensayarlo: Mate le hace las preguntas de {casos} y dice cuáles",
            "     contestó bien (un ensayo no descuenta stock):",
            f"       {orden} ensayar {programa} {casos} --ia-simulada",
            "     Ojo: esos casos son de muestra, escritos para la planilla de muestra y con",
            "     los datos del negocio vacíos. Si cambiaste los productos (paso 4) o cargaste",
            "     tus datos (paso 5), cambiá también los casos, o van a fallar los que",
            "     nombran un producto que ya no está o esperan un dato sin cargar:",
            f"       notepad {casos}",
            "",
            "Nada se anota sin tu si: Ventas repite cada pedido, con la cuenta y los bultos,",
            "y lo anota recién cuando le contestás si. Con no, o con otra cosa, no anota nada.",
            "El stock de la planilla es el de arranque: después lo lleva Depósito. Cuando",
            "llegue mercadería, escribí en la charla:  ingreso 30 azucar   (también pregunta)",
            "OJO: el stock se guarda cuando el programa termina. Terminá siempre la charla",
            "con chau: si cerrás la ventana con la X, se pierde lo anotado en esa charla.",
            f"Arriba de todo, {programa} dice qué más se puede cambiar (el mínimo de stock,",
            f"por ejemplo). Para abrirlo:  notepad {programa}")
    else:
        renglones = (
            f"Listo. Creé tres archivos en {para_pegar(os.getcwd())}:",
            f"  {programa.ljust(ancho)}   el programa del mostrador",
            f"  {planilla.ljust(ancho)}   la planilla de precios, con productos de muestra",
            f"  {casos.ljust(ancho)}   preguntas de clientes para ensayar el mostrador",
            "",
            "Los pasos que siguen (cada comando se puede copiar tal cual):",
            "  1. Comprobar que quedó todo bien:",
            f"       {orden} probar {programa}",
            "  2. Charlar con el mostrador sin gastar nada. Probá escribir: quiero 12 "
            "azucar con envio",
            f"       {orden} correr {programa} --ia-simulada",
            "  3. Poner tus productos en la planilla (también se abre con Excel). El primer",
            "     renglón, el de los títulos, no se toca y va una sola vez:",
            f"       notepad {planilla}",
            "  4. Cargar los DATOS DE TU NEGOCIO: el horario, la dirección, el teléfono, las",
            "     formas de pago, las entregas. Están arriba del programa, en",
            "     datos_del_negocio: escribí cada uno entre las comillas y guardá.",
            f"       notepad {programa}",
            "     Vienen vacíos. Lo que dejes vacío no se inventa: a quien pregunte, el",
            "     mostrador le contesta \"eso te lo confirma una persona\".",
            "  5. Comprobar de nuevo (paso 1) y atender con la IA de verdad:",
            f"       {orden} correr {programa}",
            "     (Si usás un modelo propio, como Ollama: antes hay que decirle a Mate cuál",
            "     es, con la variable MATE_IA_PROPIA. El manual dice cómo.)",
            f"  6. Ensayarlo: Mate le hace las preguntas de {casos} y dice cuáles",
            "     contestó bien (sin --ia-simulada contesta la IA de verdad):",
            f"       {orden} ensayar {programa} {casos} --ia-simulada",
            "     Ojo: esos casos son de muestra, escritos para la planilla de muestra y con",
            "     los datos del negocio vacíos. Si cambiaste los productos (paso 3) o cargaste",
            "     tus datos (paso 4), cambiá también los casos, o van a fallar los que",
            "     nombran un producto que ya no está o esperan un dato sin cargar:",
            f"       notepad {casos}",
            "",
            f"Arriba de todo, {programa} dice qué más se puede cambiar (desde cuántas "
            "unidades",
            f"hay envío, por ejemplo). Para abrirlo:  notepad {programa}")
    for renglon in renglones:
        mostrar(renglon)
    return 0


# ─────────────── La orden 'ensayar': un programa contra una lista de casos (0.6) ───────────────
# 'ensayar programa.mate casos.txt' le hace al programa cada pregunta del archivo de casos y
# dice cuáles contestó bien. Sirve para saber si una lección (o un cambio en el programa)
# funcionó, sin tipear pregunta por pregunta.
#
# Cómo se le hace una pregunta a un programa cualquiera: se le REEMPLAZA EL TECLADO. Por
# cada pregunta el programa corre entero, de cero; su primer leer() recibe la pregunta, y
# la respuesta es todo lo que muestra desde ahí hasta que vuelve a pedir algo por teclado
# (ahí se lo corta) o termina. No se eligió "declarar qué agente y qué mensaje atienden al
# cliente" porque en el ejemplo 12 (y en lo que crea 'nuevo mostrador') los pedidos con
# cantidad los contesta el PROGRAMA antes de llegar al agente: hablarle al agente directo
# ensayaría otra cosa que la que ve el cliente. Así, además, no hay que tocar el programa.
#
# Un ensayo no deja rastros: no guarda la memoria ni la bitácora, no cuenta consultas en el
# archivo, y lo que el programa escriba con agregar_a_archivo() queda en el aire (como con
# 'probar'). Sí LEE la memoria: los agentes ensayan con sus lecciones aprobadas, que es lo
# que se quiere comprobar. Lo único que escribe, al final, son las lecciones PROPUESTAS de
# los casos que fallaron (las mismas de la orden 'propuestas': nadie las usa sin aprobar).
#
# Un caso tiene tres finales: pasó, falló, o NO SE PUDO COMPROBAR (una consulta quedó sin
# respuesta de la IA: modelo apagado, nombre mal escrito, tope del agente). Este último
# nunca cuenta como pasado, aunque el programa haya seguido solo y las reglas se cumplan:
# si no, un modelo apagado daría "5 de 5 casos pasaron". Si la primera consulta del ensayo
# no tiene respuesta, o tres seguidas, se corta ahí. Con --ia-simulada no se propone nada:
# una lección no cambia un texto preparado.

MAX_VECES = 20  # --veces=N: cuántas veces se repite cada caso, como mucho
MAX_CASOS = 200  # preguntas en un archivo de casos
MAX_RENGLONES_DE_CHARLA = 60  # de la conversación de un caso que falla, en el informe
_REGLA_DE_CASO = re.compile(
    r"(?is)(?:[-*•·]\s*)?(no\s+)?(tiene\s+que|debe|puede)\s+decir\s*:(.*)")
_PARECE_REGLA = ("tiene que decir", "no tiene que decir", "debe decir", "no debe decir",
                 "puede decir", "no puede decir")
_DECIR_MAL_ESCRITO = ("decir", "desir", "dezir", "decri", "deicr", "dcir", "deir", "decirr")
# Una regla copiada del informe viene con comillas:  no puede decir "a" ni "b"
_PARES_DE_COMILLAS = (('"', '"'), ("“", "”"), ("«", "»"), ("'", "'"), ("‘", "’"))
_ENTRE_COMILLAS = "|".join(f"{re.escape(a)}[^{re.escape(a + c)}]*{re.escape(c)}"
                           for a, c in _PARES_DE_COMILLAS)
_TODO_ENTRE_COMILLAS = re.compile(
    rf"(?i)(?:{_ENTRE_COMILLAS})(?:\s*(?:\||,|o\b|ni\b)?\s*(?:{_ENTRE_COMILLAS}))*")
COMO_VAN_LAS_REGLAS = ('Las reglas van debajo de la pregunta y se escriben así:  '
                       'tiene que decir: sin envío   o   no puede decir: descuento')
# (0.7) Lo que tiene que viajar entre agentes, o no, mientras se atiende esa pregunta:
#     tiene que viajar: Reservar de Ventas a Deposito
#     no tiene que viajar: Reponer
# Va el nombre del mensaje y, si se quiere, quién lo manda ('de') y quién lo recibe ('a').
# Las respuestas ('responder') también son mensajes que viajan. Con | se dan opciones.
_REGLA_DE_VIAJE = re.compile(
    r"(?is)(?:[-*•·]\s*)?(no\s+)?(tiene\s+que|debe|puede)\s+viajar\s*:(.*)")
_UN_VIAJE = re.compile(r"(?i)(\w+)(?:\s+de\s+(?!a\s)(.+?))?(?:\s+a\s+(.+?))?")
_PARECE_VIAJE = ("tiene que viajar", "no tiene que viajar", "debe viajar", "no debe viajar",
                 "puede viajar", "no puede viajar")
# ("viaja" no va: es una palabra bien escrita, de una pregunta como "mi pedido viaja: hoy?")
_VIAJAR_MAL_ESCRITO = ("viajar", "biajar", "viajr", "viagar", "vajar", "viajarr")
# Lo que sigue a "viajar" en una regla: Mensaje, Mensaje de Agente, Mensaje a Agente...
_FORMA_DE_VIAJE = re.compile(
    r"(?i)\w+(?:\s+de\s+\w+(?:\s+\w+)?)?(?:\s+a\s+\w+(?:\s+\w+)?)?\.?")
UN_MENSAJE_POR_REGLA = ("En cada regla va un solo mensaje. Si tienen que viajar los dos, "
                        "escribí un renglón 'tiene que viajar:' para cada uno; si alcanza "
                        "con cualquiera, separalos con una barra |")
# Así empieza una regla (bien o mal escrita). Un renglón que empieza así, está debajo de
# una pregunta y nombra un mensaje del programa es una regla de mensajes mal escrita
# ("no tiene que viaja: Reponer"), no otra pregunta de un cliente.
_EMPIEZA_COMO_REGLA = ("no tiene que ", "tiene que ", "no puede ", "no debe ", "debe ",
                       "no viaja", "viaja ", "viaja:", "viajar")
_EL_PROGRAMA = "(programa)"  # así figura en la traza lo que manda el programa, no un agente
# (0.7) Un caso de más de un renglón: lo que el cliente escribe DESPUÉS de la pregunta, en
# la misma charla (el "si" a un pedido que el programa repite antes de anotar):
#     quiero 3 yerbas
#         después: si
#         tiene que decir: anotado: 3 x
# Las reglas miran lo que el programa contesta (y lo que viaja) desde el ÚLTIMO renglón.
_SIGUE_DE_CASO = re.compile(
    r"(?is)(?:[-*•·]\s*)?(?:y\s+)?despu[eé]s(?:\s+(?:escribe|contesta|dice|responde))?\s*:(.*)")
# "después si", debajo de una pregunta y sin los dos puntos: quedaría como otra pregunta.
_SIGUE_SIN_DOS_PUNTOS = re.compile(
    r"(?i)(?:[-*•·]\s*)?(?:y\s+)?despu[eé]s(?:\s+(?:escribe|contesta|dice|responde))?\s+"
    r"[\"'“”«»]?(?:s[ií]|no|dale|ok)[\"'“”«»]?\.?")
MAX_SIGUEN = 10  # renglones 'después:' en un caso
COMO_VA_LO_QUE_SIGUE = ('Lo que el cliente escribe después, en la misma charla, va debajo '
                        'de la pregunta, así:  después: si')
COMO_VAN_LOS_MENSAJES = ('Lo que tiene que viajar entre agentes se escribe así:  '
                         'tiene que viajar: Reservar de Ventas a Deposito   o   '
                         'no tiene que viajar: Reponer')


class _FinDelEnsayo(BaseException):
    """El programa ensayado volvió a pedir algo por teclado: ya contestó, se lo corta ahí.
    (No es un ErrorMate: ni 'intentar' ni 'al fallar' del programa lo pueden atajar.)"""


def para_comparar(texto):
    """Como se comparan la respuesta y lo que pide una regla: sin mirar mayúsculas, tildes
    ni cuántos espacios hay."""
    return " ".join(sin_tildes(texto).split())


def regla_de_caso(renglon):
    """Si el renglón es una regla: (verdadero si 'tiene que decir', los textos que valen).
    Si es una pregunta, None. Si parece una regla mal escrita, un ErrorMate."""
    regla = _REGLA_DE_CASO.fullmatch(renglon)
    if regla and (regla.group(1) or regla.group(2).lower() != "puede"):
        texto = regla.group(3).strip()
        if _TODO_ENTRE_COMILLAS.fullmatch(texto):  # "a" o "b", "a" ni "b", "a" | "b"
            partes = [parte[1:-1] for parte in re.findall(_ENTRE_COMILLAS, texto)]
        else:
            partes = [sin_comillas_alrededor(parte.strip()) for parte in texto.split("|")]
        opciones = tuple(" ".join(o.split()) for o in partes if o.strip())
        if not opciones:
            raise ErrorMate("a esta regla le falta el texto, después de los dos puntos. "
                            + COMO_VAN_LAS_REGLAS)
        return not regla.group(1), opciones
    suelto = para_comparar(renglon).lstrip("-*•· ")
    antes = suelto.split(":")[0].split()  # "no puede desir: ...", "tiene q decir: ..."
    resto = quizas_viaje(renglon)
    if resto is not None and _FORMA_DE_VIAJE.fullmatch(resto) and (
            ":" in renglon or resto[0].isupper()):
        raise viaje_mal_escrito(renglon)
    if suelto.startswith(_PARECE_REGLA) or (
            ":" in suelto and 1 <= len(antes) <= 5 and antes[-1] in _DECIR_MAL_ESCRITO):
        raise ErrorMate("este renglón parece una regla, pero no la entiendo"
                        + ("" if ":" in renglon else " (le faltan los dos puntos)")
                        + ". " + COMO_VAN_LAS_REGLAS)
    return None


def quizas_viaje(renglon):
    """Si el renglón (que no es una regla bien escrita) podría ser una regla de mensajes
    mal escrita ("tiene que viajar Reponer", sin los dos puntos; "puede viajar: Reponer";
    "tiene que biajar: Reponer"), lo que sigue a 'viajar'. Si no, None. Solo con esto no
    alcanza para decir que es una regla: un cliente también pregunta "puede viajar mi
    pedido hoy" (regla_de_caso() mira la forma y revisar_viajes() si nombra un mensaje)."""
    sin_marca = renglon.lstrip("-*•· ")
    suelto = para_comparar(sin_marca)
    if ":" in sin_marca:
        antes = suelto.split(":")[0].split()
        if 1 <= len(antes) <= 5 and antes[-1] in _VIAJAR_MAL_ESCRITO:
            return sin_marca.split(":", 1)[1].strip()
    if "?" not in renglon:
        for principio in sorted(_PARECE_VIAJE, key=len, reverse=True):
            if suelto.startswith(principio + " ") or suelto == principio:
                return " ".join(sin_marca.split()[len(principio.split()):]).lstrip(": ")
    return None


def viaje_mal_escrito(renglon, faltan_los_dos_puntos=None):
    if faltan_los_dos_puntos is None:
        faltan_los_dos_puntos = ":" not in renglon
    return ErrorMate("este renglón parece una regla de mensajes, pero no la entiendo"
                     + (" (le faltan los dos puntos)" if faltan_los_dos_puntos else "")
                     + ". " + COMO_VAN_LOS_MENSAJES
                     + ". (Si es una pregunta de un cliente, terminala con un signo de "
                     "pregunta: ?)")


def empieza_como_regla(caso):
    """Si ese renglón, que quedó como pregunta, tiene pinta de regla mal escrita: está
    debajo de otra pregunta, empieza como una regla ("no tiene que...", "no puede...") y
    no lleva signo de pregunta."""
    return bool(caso.get("debajo") and "?" not in caso["pregunta"] and (para_comparar(
        caso["pregunta"].lstrip("-*•· ")) + " ").startswith(_EMPIEZA_COMO_REGLA))


def habla_de_viajar(renglon):
    """Si alguna palabra del renglón es 'viajar' o se le parece: viaja, vijar, biajar."""
    import difflib
    return any(palabra.startswith("viaj") or difflib.SequenceMatcher(
        None, palabra, "viajar").ratio() >= 0.8
        for palabra in re.findall(r"\w+", para_comparar(renglon)))


def viaje_de_caso(renglon):
    """Si el renglón es una regla de mensajes ('tiene que viajar: Reponer de Deposito a
    Compras'): (verdadero si tiene que viajar, las opciones). Cada opción es (mensaje, de,
    a), con None donde no se dijo quién. Si no lo es, None. Mal escrita, un ErrorMate."""
    regla = _REGLA_DE_VIAJE.fullmatch(renglon)
    if not regla or not (regla.group(1) or regla.group(2).lower() != "puede"):
        return None
    opciones = []
    for parte in regla.group(3).split("|"):
        parte = " ".join(parte.split()).rstrip(".")
        for abre, cierra in _PARES_DE_COMILLAS:  # (copiada del informe, o con comillas)
            if len(parte) > 1 and parte.startswith(abre) and parte.endswith(cierra):
                parte = parte[1:-1].strip()
        if not parte:
            continue
        if re.search(r"(?i)^\w+\s+del\s+programa\b|\s+al\s+programa$", parte):
            # (una sola forma de escribirlo: se explica cómo va, no se aceptan dos)
            raise ErrorMate(f"no entiendo '{parte}': lo que manda o recibe el programa se "
                            "escribe 'de el programa' y 'a el programa', separado (no 'del' "
                            "ni 'al'):  tiene que viajar: ConsultaDeCliente de el programa "
                            "a Ventas")
        viaje = _UN_VIAJE.fullmatch(parte)
        if not viaje:
            raise ErrorMate(f"no entiendo qué mensaje es '{parte}': va el nombre del "
                            "mensaje, y si querés quién lo manda y quién lo recibe. "
                            + (UN_MENSAJE_POR_REGLA + ". " if "," in parte else "")
                            + COMO_VAN_LOS_MENSAJES)
        opciones.append((viaje.group(1),) + tuple(
            _EL_PROGRAMA if quien and para_comparar(quien).strip("()") in (
                "programa", "el programa") else quien for quien in viaje.groups()[1:]))
    if not opciones:
        raise ErrorMate("a esta regla le falta el nombre del mensaje, después de los dos "
                        "puntos. " + COMO_VAN_LOS_MENSAJES)
    return not regla.group(1), tuple(opciones)


def viaje_escrito(regla):
    """La regla de mensajes como se escribe en el archivo de casos (se puede copiar)."""
    debe, opciones = regla
    def quien(nombre):
        return "el programa" if nombre == _EL_PROGRAMA else nombre
    return ("tiene que viajar: " if debe else "no tiene que viajar: ") + " | ".join(
        tipo + (f" de {quien(de)}" if de else "") + (f" a {quien(a)}" if a else "")
        for tipo, de, a in opciones)


def viajes_incumplidos(viajes, reglas):
    """Las reglas de mensajes del caso que no se cumplen con lo que viajó. viajes: lo que
    anotó el intérprete, (mensaje, de, a, molde de, molde a). Una copia de un agente
    ('crear Vendedor llamado "Centro"') vale por su nombre entero o por el del agente."""
    def es(pedido, nombre, molde):
        return pedido is None or para_comparar(pedido) in (
            para_comparar(nombre), para_comparar(molde))

    def viajo(opcion):
        return any(para_comparar(opcion[0]) == para_comparar(tipo)
                   and es(opcion[1], de, molde_de) and es(opcion[2], a, molde_a)
                   for tipo, de, a, molde_de, molde_a in viajes)
    return [regla for regla in reglas if any(map(viajo, regla[1])) != regla[0]]


def copias_del_programa(programa, con_armadas=False):
    """Las copias de agentes que el programa crea con 'crear ... llamado': {agente: los
    nombres completos ("Vendedor Centro"), o None si alguno se arma al correr (llamado
    "Sucursal " + nombre) y no se puede saber acá}. Con con_armadas: ({agente: los
    nombres que sí están escritos en el programa}, los agentes con algún nombre armado)."""
    copias, armadas, por_ver = {}, set(), [programa]
    while por_ver:
        nodo = por_ver.pop()
        if _es_nodo(nodo, "crear", 5) and nodo[3] is not None:
            copias.setdefault(nodo[2], [])
            if nodo[3][0] == "str":
                copias[nodo[2]].append(f"{nodo[2]} {nodo[3][2]}")
            else:
                armadas.add(nodo[2])
        if isinstance(nodo, (list, tuple)):
            por_ver.extend(reversed(nodo))  # (en el orden del programa)
    if con_armadas:
        return copias, armadas
    return {agente: None if agente in armadas else nombres
            for agente, nombres in copias.items()}


def consulta_a_la_ia(programa):
    """Si en el programa hay alguna llamada a consultar_ia()."""
    por_ver = [programa]
    while por_ver:
        nodo = por_ver.pop()
        if _es_nodo(nodo, "llamar", 4) and _es_nodo(nodo[2], "nombre", 3) \
                and nodo[2][2] == "consultar_ia":
            return True
        if isinstance(nodo, (list, tuple)):
            por_ver.extend(nodo)
    return False


def revisar_viajes(casos, programa, ruta):
    """Que cada regla de mensajes nombre un mensaje y agentes que el programa tiene: un
    nombre mal escrito (o una regla mal armada: 'Reservar a Deposito de Ventas') haría que
    'no tiene que viajar' pasara siempre. Deja los nombres escritos como en el programa.
    Falla con un ErrorMate que dice el renglón. También avisa una pregunta que en realidad
    es una regla de mensajes mal escrita (nombra un mensaje del programa). Devuelve lo
    que no se pudo revisar, [(renglón, nombre)]: una copia cuyo nombre se arma al correr."""
    def el_de(nombre, declarados, que, renglon):
        igual = [d for d in declarados if para_comparar(d) == para_comparar(nombre)]
        if igual:
            return igual[0]
        raise ErrorMate(con_sugerencia(
            f"{ruta}:{renglon}: el programa no tiene {que} '{nombre}'", nombre, declarados)
            + (f" (tiene: {', '.join(declarados)})" if 0 < len(declarados) <= 12 else ""))

    def el_agente(nombre, renglon):
        if nombre in (None, _EL_PROGRAMA):
            return nombre
        dicho = para_comparar(nombre)
        for agente in agentes:
            if dicho == para_comparar(agente):
                return agente
        for agente in agentes:  # una copia: "Vendedor Centro"
            if dicho.startswith(para_comparar(agente) + " ") and agente in copias:
                de_ese = copias[agente]
                if agente in armadas and dicho not in map(para_comparar, de_ese):
                    # El nombre se arma al correr: no se puede revisar acá. Se mira después
                    # de ensayar el caso (con el nombre mal escrito, un 'no tiene que
                    # viajar' pasaría siempre).
                    sin_revisar.append((renglon, nombre))
                    return nombre
                return el_de(nombre, de_ese, f"ningún {agente} llamado", renglon)
        palabras, tiene = dicho.split(), ""
        if 0 < len(agentes) <= 12:
            tiene = f" El programa tiene: {', '.join(agentes)}."
        if "," in nombre:
            raise ErrorMate(f"{ruta}:{renglon}: no entiendo '{nombre}'. "
                            + UN_MENSAJE_POR_REGLA + ".")
        if "de" in palabras or "a" in palabras:
            raise ErrorMate(
                f"{ruta}:{renglon}: no entiendo '{nombre}'. Primero va quién manda el "
                "mensaje (de) y después quién lo recibe (a), una sola vez cada uno y con "
                "el nombre del agente:  tiene que viajar: Reservar de Ventas a Deposito")
        if len(palabras) > 1:
            raise ErrorMate(
                f"{ruta}:{renglon}: no entiendo '{nombre}'. Después de 'de' y de 'a' va "
                "solo el nombre de un agente (o 'el programa')." + tiene
                + "".join(f" {agente} no tiene copias con nombre en el programa."
                          for agente in agentes if palabras[0] == para_comparar(agente)))
        return el_de(nombre, agentes, "ningún agente llamado", renglon)

    mensajes = [s[2] for s in programa if s[0] == "mensaje"]
    agentes = [s[2] for s in programa if s[0] in ("agente", "agente_ajeno")]
    (copias, armadas), sin_revisar = copias_del_programa(programa, True), []
    de_mensajes = {para_comparar(mensaje) for mensaje in mensajes}
    for caso in casos:
        # "tiene que viajar reponer" (sin los dos puntos) quedó como pregunta: no lo es.
        resto = quizas_viaje(caso["pregunta"])
        if resto and para_comparar(resto.split()[0].strip(".,;:|\"'")) in de_mensajes:
            raise ErrorMate(f"{ruta}:{caso['renglon']}: "
                            + viaje_mal_escrito(caso["pregunta"]).mensaje)
        # "no tiene que viaja: Reponer", "no tiene que viajar el reponer", debajo de una
        # pregunta: si no se avisa, queda como una pregunta más y la regla no se mira.
        if empieza_como_regla(caso) and habla_de_viajar(caso["pregunta"]) and \
                de_mensajes.intersection(re.findall(r"\w+", para_comparar(caso["pregunta"]))):
            raise ErrorMate(f"{ruta}:{caso['renglon']}: " + viaje_mal_escrito(
                caso["pregunta"], faltan_los_dos_puntos=False).mensaje)
        for i, (debe, opciones, renglon) in enumerate(caso["mensajes"]):
            nuevas = []
            for tipo, de, a in opciones:
                tipo = el_de(tipo, mensajes, "ningún mensaje llamado", renglon)
                nuevas.append((tipo, el_agente(de, renglon), el_agente(a, renglon)))
            caso["mensajes"][i] = (debe, tuple(nuevas), renglon)
    return sin_revisar


def sin_comillas_alrededor(opcion):
    """La opción de una regla sin las comillas que la envuelven. Con comillas a medias
    (abre y no cierra, o hay más de un par) falla: así como está no se cumpliría nunca."""
    for abre, cierra in _PARES_DE_COMILLAS:
        if opcion.startswith(abre):
            adentro = opcion[len(abre):-len(cierra)]
            if len(opcion) < 2 or not opcion.endswith(cierra) or abre in adentro \
                    or cierra in adentro:
                raise ErrorMate(
                    "esta regla tiene comillas que no entiendo. El texto va sin comillas, y "
                    "las opciones se separan con una barra:  tiene que decir: no hay stock "
                    "| no queda")
            return adentro
    return opcion


def regla_escrita(regla):
    """La regla como se le muestra a la persona: tiene que decir "sin envío"."""
    debe, opciones = regla
    return ("tiene que decir " if debe else "no puede decir ") + (
        " o " if debe else " ni ").join(f'"{o}"' for o in opciones)


def casos_de_archivo(ruta):
    """Lee el archivo de casos de 'ensayar'. Devuelve [{"renglon", "pregunta", "reglas",
    "mensajes"}], o falla con un ErrorMate que dice el renglón. Una o más preguntas
    seguidas (una por renglón) comparten las reglas que tienen debajo; # es una nota.
    reglas: lo que la respuesta tiene que decir o no. mensajes: lo que tiene que viajar
    entre agentes o no, cada una con su renglón: (debe, opciones, renglón)."""
    try:
        contenido = leer_fuente(ruta)
    except FileNotFoundError:
        raise ErrorMate(f"no encuentro el archivo de casos '{ruta}'")
    except (OSError, ErrorMate):
        raise ErrorMate(f"no pude leer el archivo de casos '{ruta}'")
    casos, grupo, con_reglas = [], [], False
    for numero, renglon in enumerate(contenido.split("\n"), 1):
        entero = "".join(c for c in renglon if c not in _INVISIBLES)
        renglon = entero.strip()
        if not renglon or renglon.startswith("#"):
            continue
        sigue = _SIGUE_DE_CASO.fullmatch(renglon)
        if sigue:
            # Lo que el cliente escribe después: vale para las preguntas de arriba, como
            # una regla (y, como una regla, cierra la lista de preguntas del grupo).
            dicho = sin_comillas_de_charla(sigue.group(1).strip())
            if not grupo:
                raise ErrorMate(f"{ruta}:{numero}: este 'después:' no tiene una pregunta "
                                "arriba. " + COMO_VA_LO_QUE_SIGUE)
            if not dicho:
                raise ErrorMate(f"{ruta}:{numero}: a este 'después:' le falta lo que escribe "
                                "el cliente, después de los dos puntos. " + COMO_VA_LO_QUE_SIGUE)
            if not sin_reglas(grupo):
                # Las reglas miran la respuesta al ÚLTIMO renglón: una regla escrita arriba
                # de un 'después:' parece mirar la respuesta anterior, y no lo hace.
                raise ErrorMate(
                    f"{ruta}:{numero}: este 'después:' está debajo de una regla. Las reglas "
                    "de un caso miran lo que el programa contesta al ÚLTIMO renglón, así "
                    "que los 'después:' van todos arriba, pegados a la pregunta, y las "
                    "reglas debajo. Para revisar también la respuesta de antes, escribí "
                    "otro caso con la misma pregunta y sin ese 'después:'")
            if len(grupo[0]["siguen"]) >= MAX_SIGUEN:
                raise ErrorMate(f"{ruta}:{numero}: un caso lleva hasta {MAX_SIGUEN} renglones "
                                "'después:'")
            for caso in grupo:
                caso["siguen"].append(dicho)
            con_reglas = True
            continue
        try:
            viaje = viaje_de_caso(renglon)
            regla = viaje or regla_de_caso(renglon)
        except ErrorMate as e:
            raise ErrorMate(f"{ruta}:{numero}: {e.mensaje}")
        if regla is None:
            if grupo and _SIGUE_SIN_DOS_PUNTOS.fullmatch(renglon):
                raise ErrorMate(f"{ruta}:{numero}: a este 'después' le faltan los dos puntos "
                                "(así queda como otra pregunta del cliente). "
                                + COMO_VA_LO_QUE_SIGUE)
            if con_reglas:  # las reglas de arriba cerraron el grupo: acá empieza otro
                if sin_reglas(grupo):  # (tenía un 'después:' y ninguna regla)
                    raise ErrorMate(
                        f"{ruta}:{grupo[0]['renglon']}: a esta pregunta le falta decir qué "
                        "se espera de la respuesta. " + COMO_VAN_LAS_REGLAS)
                grupo, con_reglas = [], False
            # sangria y debajo (de otra pregunta): para avisar una regla mal escrita
            grupo.append({"renglon": numero, "pregunta": renglon, "reglas": [],
                          "mensajes": [], "siguen": [], "sangria": entero[:1] in (" ", "\t"),
                          "debajo": bool(grupo)})
            casos.append(grupo[-1])
        elif not grupo:
            raise ErrorMate(f"{ruta}:{numero}: esta regla no tiene una pregunta arriba. "
                            "Primero va la pregunta del cliente, en un renglón, y debajo "
                            "sus reglas")
        else:
            for caso in grupo:
                if viaje:
                    caso["mensajes"].append(viaje + (numero,))
                else:
                    caso["reglas"].append(regla)
            con_reglas = True
    if grupo and sin_reglas(grupo):
        for caso in grupo[1:]:  # "hola" y debajo "tiene que viajar reponer": no es otra pregunta
            if quizas_viaje(caso["pregunta"]) is not None:
                raise ErrorMate(f"{ruta}:{caso['renglon']}: "
                                + viaje_mal_escrito(caso["pregunta"]).mensaje)
            if caso["sangria"] and empieza_como_regla(caso):
                # "hola" y debajo, con sangría, "no tiene que viaja: Reponer"
                raise ErrorMate(
                    f"{ruta}:{caso['renglon']}: este renglón parece una regla, pero no la "
                    f"entiendo. {COMO_VAN_LAS_REGLAS}. {COMO_VAN_LOS_MENSAJES}")
        raise ErrorMate(
            f"{ruta}:{grupo[0]['renglon']}: a esta pregunta le falta decir qué se espera de "
            "la respuesta. " + COMO_VAN_LAS_REGLAS)
    if not casos:
        raise ErrorMate(f"el archivo de casos '{ruta}' no tiene ninguna pregunta. Va la "
                        "pregunta del cliente en un renglón y debajo sus reglas. "
                        + COMO_VAN_LAS_REGLAS)
    if len(casos) > MAX_CASOS:
        raise ErrorMate(f"el archivo de casos '{ruta}' tiene {len(casos)} preguntas y el "
                        f"tope es {MAX_CASOS}: partilo en dos archivos")
    return casos


def sin_reglas(grupo):
    """Si a las preguntas de ese grupo todavía no se les puso ninguna regla."""
    return not (grupo[0]["reglas"] or grupo[0]["mensajes"])


def sin_comillas_de_charla(dicho):
    """Lo que escribe el cliente en un 'después:', sin las comillas que lo envuelvan."""
    for abre, cierra in _PARES_DE_COMILLAS:
        if len(dicho) > 1 and dicho.startswith(abre) and dicho.endswith(cierra):
            return dicho[1:-1].strip()
    return dicho


def caso_escrito(caso):
    """El caso como se muestra en el informe: la pregunta y, si los hay, los renglones que
    el cliente escribe después."""
    return caso["pregunta"] + "".join(f"  →  {dicho}" for dicho in caso.get("siguen", ()))


def reglas_incumplidas(respuesta, reglas):
    """Las reglas del caso que esa respuesta no cumple."""
    dicho = para_comparar(respuesta)
    return [regla for regla in reglas
            if any(para_comparar(opcion) in dicho for opcion in regla[1]) != regla[0]]


def preguntar_al_programa(ruta, pregunta, memoria, simulada=False, respuestas=(),
                          consultas=0, sin_limite=False, entregar_lo_enviado=False,
                          siguen=()):
    """Corre el programa de cero y le 'teclea' esa pregunta en su primer leer(). Devuelve
    un mapa: pidio (si llegó a pedir algo por teclado), respuesta (lo que mostró desde ahí
    hasta que volvió a pedir, o hasta el final), cartel (lo que decía ese leer()), otra (si volvió a pedir), antes (lo
    que mostró antes), error (el
    texto, o None), limite (si lo cortó un tope de Mate), consultas (las que le hizo a la
    IA, como en consultas_ia()), agentes (los que consultaron), gasto y hechas (las
    cuentas, para la pregunta que sigue), viajes (los mensajes que viajaron entre agentes
    desde que leyó la pregunta, como en viajes_incumplidos()) y charla (los renglones de
    la traza de esos mensajes, numerados desde 1) y sin_entregar (lo mandado con 'enviar'
    por esa pregunta que quedó en la cola: (mensaje, de, a)). No toca el disco: ni memoria,
    ni bitácora, ni los archivos que el programa escriba.
    Con siguen (los renglones 'después:' del caso), cada vez que el programa vuelve a pedir
    por teclado se le escribe el renglón que sigue, en la misma corrida. La respuesta, los
    viajes y la charla son los del ÚLTIMO renglón; lo que contestó a los anteriores queda
    en previas: [(lo que se le escribió, lo que contestó)]. Si el programa termina antes
    de pedir alguno, es un error del caso.
    Un mensaje mandado con 'enviar' no llega en el momento: en la corrida de verdad se
    entrega cuando el programa vuelve a preguntarle a un agente, o al terminar. Con
    entregar_lo_enviado (un caso con reglas de mensajes), si quedó algo mandado por ESTA
    pregunta, la cola se vacía entera y en su orden cuando el programa vuelve a pedir por
    teclado. Lo de esta pregunta cuenta en viajes y en charla; lo que estaba mandado de
    antes también se entrega (el agente lo recibe primero, como en la corrida de verdad),
    pero ni cuenta ni se muestra. Lo que muestren los agentes en ese momento no entra en
    la respuesta (el cliente lo vería después). Sin eso queda sin entregar, como siempre."""
    mostrado, corte, charla = [], {}, []
    faltan, previas, escrito = list(siguen), [], [pregunta]

    def de_este_caso(en_cola):
        return en_cola[3][0] > interprete.desde[1]

    def entrada(cartel):
        if "desde" in corte and faltan:
            # Un caso de varios renglones: lo que contestó hasta acá queda aparte, y el
            # caso pasa a ser lo que conteste (y lo que viaje) desde el renglón que sigue.
            previas.append((escrito[-1], "\n".join(mostrado[corte["desde"]:]).strip()))
            escrito.append(faltan.pop(0))
            corte["desde"] = len(mostrado)
            del interprete.viajes[:], charla[:]
            interprete.desde = (interprete.cuenta["enviar"] + interprete.cuenta["preguntar"],
                                interprete.conversaciones)
            return escrito[-1]
        if "desde" not in corte:
            corte["desde"], corte["cartel"] = len(mostrado), str(cartel or "")
            # Lo que se habló antes (cargar la planilla, por ejemplo) no es de este caso.
            # Lo que el programa ya había mandado con 'enviar' sigue en la cola, como en una
            # corrida de verdad: si llega mientras se atiende la pregunta, entregar() no lo
            # cuenta ni lo muestra (es de una conversación de antes).
            del interprete.viajes[:], charla[:]
            interprete.desde = (interprete.cuenta["enviar"] + interprete.cuenta["preguntar"],
                                interprete.conversaciones)
            return pregunta
        if "hasta" not in corte:
            corte["hasta"] = len(mostrado)
            cola = interprete.cola
            if entregar_lo_enviado and any(map(de_este_caso, cola)):
                # La cola se vacía entera y en su orden, como en la corrida de verdad: si
                # antes de la pregunta quedó algo mandado (un inventario), llega primero.
                # entregar() no lo cuenta ni lo muestra, pero el agente lo recibe.
                charla.append("  ·     (lo que sigue quedó mandado con 'enviar': llega "
                              "después de contestarle al cliente)")
                try:
                    interprete.vaciar_cola()
                except ErrorMate as e:  # (un tope de Mate: se informa como cualquier otro)
                    corte["error"] = e
            corte["sin_entregar"] = [
                (msg.tipo, rem.nombre if rem else _EL_PROGRAMA, dest.nombre)
                for rem, dest, msg, sobre in cola
                if msg.tipo != AL_FALLAR and de_este_caso((rem, dest, msg, sobre))]
        raise _FinDelEnsayo()

    interprete = Interprete(salida=lambda texto: mostrado.append(str(texto)), traza=True)
    interprete.anotar, interprete.viajes = charla.append, []
    interprete.archivo, interprete.entrada, interprete.ensayando = ruta, entrada, True
    interprete.archivos_de_prueba = {}  # lo que escriba no llega al disco
    interprete.ia_simulada, interprete.ia_respuestas = bool(simulada), list(respuestas)
    interprete.ia_consultas = consultas  # el tope de consultas de verdad es del ensayo entero
    if sin_limite:
        interprete.max_pasos = None
    # Los agentes arrancan con lo que dice la memoria (sus lecciones, sobre todo), en una
    # copia: nada de lo que pase acá vuelve al archivo.
    interprete.memoria, interprete.recordando = json.loads(json.dumps(memoria)), True
    error = limite = None
    try:
        interprete.correr(analizar(leer_fuente(ruta), ruta))
    except _FinDelEnsayo:
        e = corte.get("error")
    except ErrorMate as tarde:
        e = tarde
    except OSError:
        e, error = None, f"no pude abrir {ruta}"
    else:
        e = None
    if e is not None:
        error = error_escrito(ruta, e.linea, interprete.con_camino(e.mensaje, e))[0]
        limite = e.clase == "limite"
    if error is None and interprete.errores_agentes:
        error = interprete.errores_agentes[0]
    if error is None and faltan and "desde" in corte:
        error = ("no volvió a pedir nada por teclado, y faltaba escribirle lo que sigue en "
                 f"el caso: {faltan[0]}")
    desde = corte.get("desde", len(mostrado))
    molde_de = {agente.nombre: agente.decl[2] for agente in interprete.vivos}
    agentes = []
    for consulta in interprete.ia_historial:
        agente = molde_de.get(consulta["agente"], consulta["agente"])
        if agente in interprete.agentes and agente not in agentes:
            agentes.append(agente)
    return {"pidio": "desde" in corte, "cartel": corte.get("cartel", ""), "otra": "hasta" in corte,
            "respuesta": "\n".join(mostrado[desde:corte.get("hasta")]).strip(),
            "antes": mostrado[:desde], "error": error, "limite": bool(limite),
            "consultas": list(interprete.ia_historial), "agentes": agentes,
            "viajes": list(interprete.viajes) if "desde" in corte else [],
            "charla": list(charla) if "desde" in corte else [],
            "vivos": [agente.nombre for agente in interprete.vivos],
            "sin_entregar": corte.get("sin_entregar", []), "previas": previas,
            "gasto": {nombre: gasto_limpio(agente.gasto)
                      for nombre, agente in interprete.agentes.items() if agente.gasto},
            "hechas": interprete.ia_consultas}


def leccion_de_un_caso(caso, incumplidas):
    """La lección que se propone cuando un caso falla: la pregunta y lo que no cumplió."""
    return (f"Cuando te pregunten algo como {recortado(caso_escrito(caso), 80)}, tu respuesta "
            + " y ".join(regla_escrita(regla) for regla in incumplidas) + ".")


def orden_ensayar(args, opciones, respuestas, veces, avisar, mostrar=print):
    """La orden 'ensayar programa.mate casos.txt': le hace al programa cada pregunta del
    archivo de casos (--veces=N: N veces cada una), muestra el informe y deja una lección
    propuesta por cada caso que falló. Devuelve el código de salida: 0 si pasaron todos."""
    orden = orden_para_esta_carpeta()
    ejemplo = f"{orden} ensayar mi_negocio.mate mi_negocio_casos.txt --ia-simulada"
    if len(args) == 2 and args[0].lower().endswith(".txt") and args[1].lower().endswith(
            (".mate", ".mate.txt")) and not args[0].lower().endswith(".mate.txt"):
        avisar("primero va el programa y después el archivo de casos:  "
               f"{orden} ensayar {para_pegar(args[1])} {para_pegar(args[0])}",
               "al escribir la orden: 'ensayar' con los archivos al revés", True)
        return 2
    if len(args) != 2:
        avisar("'ensayar' lleva el programa y el archivo de casos (las preguntas de los "
               "clientes y lo que la respuesta tiene que decir)"
               + (f", y recibió {len(args)} cosas (un nombre con espacios va entre comillas)"
                  if len(args) > 2 else "") + f". Por ejemplo:  {ejemplo}",
               "al escribir la orden: 'ensayar' sin el programa o sin los casos", True)
        return 2
    for opcion, por_que in (("--traza", "muestra un informe, con la conversación de los "
                                        "casos que fallan en un equipo"),
                            ("--olvidar", "nunca cambia lo que recuerdan los agentes")):
        if opcion in opciones:
            avisar(f"{opcion} no va con 'ensayar' ({por_que}). Para ver una charla paso a "
                   f"paso:  {orden} correr {para_pegar(args[0])} --traza")
            return 2
    ruta, problema = _ubicar(args[0])
    if problema:
        avisar(problema, "al escribir la orden: no está el archivo"
               if problema.startswith("no encuentro") else None)
        return 2
    programa, de_casos = os.path.basename(ruta), os.path.basename(args[1])
    simulada = "--ia-simulada" in opciones
    try:
        casos = casos_de_archivo(args[1])
        preparadas = respuestas_de_archivo(respuestas) if respuestas else []
        # Quién va a contestar las consultas: se dice antes de empezar, porque puede costar.
        if simulada:
            contesta = "la IA simulada: no sale a la red y no gasta nada"
        elif direccion_de_ia_propia():
            # (sin MATE_MODELO fallarían todas las consultas: se dice acá, una sola vez)
            contesta = f"tu modelo propio ({modelo_de_ia_propia()}), en {direccion_de_ia_propia()}"
        elif not os.environ.get("ANTHROPIC_API_KEY", "").strip():
            raise ErrorMate(
                "para ensayar hay que decir quién contesta las consultas a la IA, y no hay "
                "clave ni modelo propio. Sin gastar nada, agregá --ia-simulada:\n"
                f"  {orden} ensayar {para_pegar(args[0])} {para_pegar(args[1])} "
                "--ia-simulada\n"
                'Con tu modelo propio, antes escribí:  $env:MATE_IA_PROPIA = "ollama"\n'
                "Con Claude, la clave va en ANTHROPIC_API_KEY (y cada consulta se paga)")
        else:
            clave_de_ia()
            contesta = f"Claude ({modelo_de_ia()}): cada consulta se paga"
    except ErrorMate as e:
        avisar(e.mensaje)
        return 2
    try:
        arbol = analizar(leer_fuente(ruta), ruta)
        con_errores = bool(verificar(arbol))
    except OSError:
        avisar(f"no pude abrir {ruta}")
        return 2
    except ErrorMate:
        con_errores = True
    if con_errores:
        avisar(f"{ruta} tiene errores, y así no se puede ensayar. Miralos con:  "
               f"{orden} verificar {para_pegar(args[0])}")
        return 1
    archivo_memoria = archivo_de(ruta, "memoria.json")
    try:
        sin_revisar = revisar_viajes(casos, arbol, args[1])
        memoria = leer_memoria(archivo_memoria)[0]
    except ErrorMate as e:
        avisar(e.mensaje)
        return 2

    veces = veces or 1
    # (cada renglón 'después:' es una vuelta más por el programa, y puede consultar)
    total = sum(1 + len(caso["siguen"]) for caso in casos) * veces
    mostrar(f"Ensayo de {programa} con {de_casos}: {len(casos)} pregunta(s)"
            + (f", {veces} veces cada una" if veces > 1 else "") + ".")
    mostrar(f"Contesta {contesta}.")
    mostrar(f"Va a hacer hasta {total} consulta(s) a la IA: una por cada pregunta que el "
            "programa no")
    mostrar("conteste solo (si salta un freno, esa pregunta consulta una vez más).")
    if any(caso["mensajes"] for caso in casos) and consulta_a_la_ia(arbol):
        # (P124) ahí también se entrega lo mandado con 'enviar': puede haber más consultas
        mostrar("Pueden ser más: en los casos con reglas de mensajes también se entrega lo "
                "mandado con")
        mostrar("'enviar', y un agente que consulta a la IA al recibirlo suma una consulta.")
    if not simulada and total > MAX_CONSULTAS_IA and "--sin-limite" not in opciones:
        mostrar(f"Ojo: Mate corta el ensayo a las {MAX_CONSULTAS_IA} consultas de verdad. "
                "Si hacen falta más, agregá --sin-limite.")
    for agente, ficha in memoria.items():
        if ficha["lecciones"]:
            mostrar(f"{agente} ensaya con las lecciones que ya tiene aprobadas "
                    f"({len(ficha['lecciones'])}).")
    sys.stdout.flush()

    import textwrap
    bien, mal = simbolo("✓", "OK"), simbolo("✗", "FALLA")
    pasaron, sin_comprobar, consultas, frenadas, cortado = 0, 0, 0, 0, None
    a_proponer, simuladas_sin_proponer, motivos_dichos, mudas_seguidas = [], 0, [], 0
    hechas, viva = 0, json.loads(json.dumps(memoria))  # (viva: la memoria, con la cuenta al día)
    for caso in casos:
        pasadas, mudas, falla, muda, con_freno = 0, 0, None, None, False
        for vez in range(1, veces + 1):
            dado = preguntar_al_programa(ruta, caso["pregunta"], viva, simulada, preparadas,
                                         hechas, "--sin-limite" in opciones,
                                         bool(caso["mensajes"]), caso["siguen"])
            # (se cuentan las que la IA contestó: no las que frenó un tope antes de salir)
            contestadas = sum(c["respuesta"] is not None for c in dado["consultas"])
            sin_ia = [c for c in dado["consultas"] if c["respuesta"] is None]
            con_freno = con_freno or any(
                c.get("freno") and c["respuesta"] is not None for c in dado["consultas"])
            for agente, gasto in dado["gasto"].items():
                viva.setdefault(agente, {"estado": {}, "lecciones": []})["gasto"] = gasto
            if caso is casos[0] and vez == 1:
                # Dónde entra la pregunta: en el primer leer() del programa. Se dice una
                # vez, por si ese leer() no es el que espera la consulta del cliente.
                if dado["pidio"] and dado["cartel"].strip():
                    mostrar("Cada pregunta se le escribe al programa donde pide:  "
                            + recortado(dado["cartel"].strip(), 60))
                mostrar("")
            hechas, consultas = dado["hechas"], consultas + contestadas
            if not dado["pidio"]:
                # Ni llegó a leer la pregunta: con las demás va a pasar lo mismo.
                for renglon in dado["antes"][-5:]:
                    mostrar(f"      | {renglon}")
                if dado["error"]:
                    avisar(f"no pude ensayar: {programa} falló antes de pedir la consulta "
                           f"del cliente.\n{dado['error']}")
                    return 1
                avisar(f"no pude ensayar: {programa} terminó sin pedir nada por teclado"
                       + (" (arriba está lo último que mostró)" if dado["antes"] else "")
                       + ". 'ensayar' le escribe cada pregunta al programa donde el programa "
                       'espera al cliente, con leer(): por ejemplo  sea dicho = '
                       'leer("Cliente:", "chau")')
                return 2
            if dado["limite"]:
                if falla is None:
                    falla = dict(dado, vez=vez, incumplidas=[], sin_viajar=[])
                cortado = dado["error"]
                break
            if sin_ia:
                # Una consulta quedó sin respuesta de la IA (no anduvo, o el agente llegó a
                # su tope). Aunque el programa haya seguido solo y las reglas se cumplan,
                # esta vez NO cuenta como pasada: no se llegó a ver qué contesta la IA.
                mudas, muda = mudas + 1, muda or dict(dado, vez=vez, sin_ia=sin_ia)
                mudas_seguidas += 1
                if any(not c.get("freno") for c in sin_ia) and (
                        consultas == 0 or mudas_seguidas >= 3):
                    cortado = ("la primera consulta a la IA no tuvo respuesta" if consultas == 0
                               else "la IA no contestó tres veces seguidas") + (
                        ": arreglá eso y ensayá de nuevo.")
                    break
                continue
            if contestadas:
                mudas_seguidas = 0
            incumplidas = [] if dado["error"] else reglas_incumplidas(
                dado["respuesta"], caso["reglas"])
            sin_viajar = [] if dado["error"] else viajes_incumplidos(
                dado["viajes"], [regla[:2] for regla in caso["mensajes"]])
            if not dado["error"] and not incumplidas and not sin_viajar:
                pasadas += 1
            elif falla is None:
                falla = dict(dado, vez=vez, incumplidas=incumplidas, sin_viajar=sin_viajar)
        pasaron += pasadas == veces
        sin_comprobar += bool(mudas) and falla is None
        frenadas += con_freno
        hecho = mal if falla is not None else simbolo("?", "SIN COMPROBAR") if mudas else bien
        mostrar(f"  {hecho} {caso_escrito(caso)}"
                + (f": pasó {pasadas} de {veces}" if veces > 1 else "")
                + ("" if not mudas else ": no se pudo comprobar" if veces == 1 else
                   f", y {mudas} sin comprobar")
                + ("" if falla is None and not mudas else
                   f"   (renglón {caso['renglon']} de {de_casos})"))
        for renglon, nombre in sin_revisar[:]:
            # (P121) Una copia con el nombre armado al correr: recién ahora se sabe si existe.
            if any(regla[2] == renglon for regla in caso["mensajes"]) and not dado["error"] \
                    and para_comparar(nombre) not in map(para_comparar, dado["vivos"]):
                sin_revisar.remove((renglon, nombre))
                mostrar(f"      Ojo: en este caso no hubo ningún agente llamado '{nombre}' "
                        f"(renglón {renglon} de {de_casos}).")
                mostrar("      Si el nombre está mal escrito, esa regla no mira nada.")
        if muda is not None:
            # El motivo se muestra entero una sola vez: con el modelo apagado es el mismo
            # en todos los casos.
            cual = f" (la vez {muda['vez']})" if veces > 1 else ""
            for consulta in muda["sin_ia"]:
                motivo = (consulta.get("motivo") or consulta.get("freno")
                          or "no dio una respuesta que se pueda usar")
                if motivo.startswith("consultar_ia(): "):
                    motivo = motivo[len("consultar_ia(): "):]
                que = "No se consultó a la IA" if consulta.get("freno") else "La IA no contestó"
                if motivo in motivos_dichos:
                    mostrar(f"      {que}{cual}, por lo mismo que más arriba.")
                    continue
                motivos_dichos.append(motivo)
                partes = [corto for parte in f"{que}{cual}: {motivo}".split("\n")
                          for corto in textwrap.wrap(parte, 88) or [""]]
                mostrar(f"      {partes[0]}")
                for parte in partes[1:]:
                    mostrar(f"          {parte}")
            if muda["respuesta"] and not muda["error"]:
                mostrar("      Sin la IA, el programa contestó: "
                        + recortado(muda["respuesta"], 55))
        if falla is not None:
            cual = f" (la vez {falla['vez']})" if veces > 1 else ""
            for dicho, contestado in falla["previas"]:
                # (un caso de varios renglones: lo que había contestado a los de antes)
                partes = contestado.split("\n") if contestado else ["(nada)"]
                mostrar(f"      A \"{dicho}\" había contestado: {partes[0]}")
                for parte in partes[1:]:
                    mostrar(f"          {parte}")
            partes = falla["respuesta"].split("\n") if falla["respuesta"] else ["(nada)"]
            mostrar(f"      Contestó{cual}: {partes[0]}")
            for parte in partes[1:]:
                mostrar(f"          {parte}")
            for regla in falla["incumplidas"]:
                mostrar(f"      No cumple: {regla_escrita(regla)}")
            for regla in falla["sin_viajar"]:
                mostrar(f"      No cumple: {viaje_escrito(regla)}")
            if falla["error"]:
                mostrar(f"      El programa falló: {falla['error']}")
            # La conversación del caso: si el caso pide algo de los mensajes, o si hubo
            # agentes hablando entre ellos (un mostrador solo se informa como siempre).
            if caso["mensajes"] or any(_EL_PROGRAMA not in viaje[1:3]
                                       for viaje in falla["viajes"]):
                if falla["charla"]:
                    mostrar("      La conversación de este caso (lo que se dijeron los "
                            "agentes, en orden):")
                    charla, salteados = falla["charla"], 0
                    if len(charla) > MAX_RENGLONES_DE_CHARLA:  # (agentes en bucle)
                        salteados = len(charla) - MAX_RENGLONES_DE_CHARLA
                        charla = charla[:MAX_RENGLONES_DE_CHARLA - 10] + [None] + charla[-10:]
                    for renglon in charla:
                        if renglon is None:
                            renglon = (f"  ·     ... (acá van {salteados} renglones más, "
                                       "que no se muestran) ...")
                        mostrar("        " + (renglon if len(renglon) <= 300
                                              else renglon[:300].rstrip() + "..."))
                else:
                    mostrar("      En este caso no viajó ningún mensaje: nadie le habló a "
                            "ningún agente.")
                if falla["sin_entregar"]:
                    # (un caso sin reglas de mensajes: lo enviado queda en la cola)
                    mostrar("          (quedó mandado con 'enviar' y llega después: "
                            + ", ".join(viaje_escrito((True, (viaje,)))[len(
                                "tiene que viajar: "):] for viaje in falla["sin_entregar"])
                            + ")")
            frenos_dichos = []
            for consulta in falla["consultas"]:
                freno = consulta.get("freno") and (
                    f"      Saltó un freno de {consulta['agente']}: {consulta['freno']}"
                    + ("" if consulta["respuesta"] is None else
                       f". La IA había dicho: {recortado(consulta['respuesta'], 200)}"))
                if freno and freno not in frenos_dichos:  # (dos intentos iguales: una vez)
                    frenos_dichos.append(freno)
                    mostrar(freno)
            if falla["sin_viajar"]:
                mostrar("      Qué mensajes viajan lo decide el programa, no la IA: una "
                        "lección no lo cambia.")
                mostrar("      Hay que cambiar el programa (o el caso).")
            if falla["error"] or not falla["incumplidas"] and falla["sin_viajar"]:
                pass
            elif not falla["consultas"]:
                if not falla["sin_viajar"]:  # (si no, ya se dijo recién)
                    mostrar("      Esta respuesta la dio el programa, sin consultar a la "
                            "IA: una lección no la cambia.")
                    mostrar("      Hay que cambiar el programa (o el caso).")
                if not falla["respuesta"] and falla["otra"]:
                    mostrar("      (El programa volvió a pedir algo por teclado sin mostrar "
                            "nada: quizás su primer")
                    mostrar("      leer() no es el que espera la consulta del cliente.)")
            elif simulada:
                # Una lección no cambia un texto preparado: proponerla sería hacerle creer
                # a la persona que aprobándola el ensayo simulado va a pasar.
                simuladas_sin_proponer += 1
                mostrar("      Eso lo contestó la IA simulada, con un texto preparado: una "
                        "lección no lo cambia.")
            elif not falla["agentes"]:
                mostrar("      La consulta a la IA la hizo el programa, no un agente: no hay "
                        "a quién dejarle una lección.")
            else:
                for agente in falla["agentes"]:
                    a_proponer.append((
                        agente, leccion_de_un_caso(caso, falla["incumplidas"]),
                        f"falló un caso del ensayo ({de_casos}, renglón {caso['renglon']}). "
                        f"Contestó: {recortado(falla['respuesta'], 200)}"))
        sys.stdout.flush()
        if cortado:
            break

    mostrar("")
    if cortado:
        mostrar("El ensayo se cortó ahí y no siguió con los casos que faltaban:")
        mostrar(f"  {cortado}")
    mostrar(f"{pasaron} de {len(casos)} casos pasaron"
            + (f" las {veces} veces" if veces > 1 else "") + "."
            + (f" Consultas a la IA: {consultas}" + (" (simuladas: no se pagan)." if simulada
                                                    else ".") if consultas else
               "" if motivos_dichos else " No hizo falta consultar a la IA."))
    con_memoria = [agente for agente, ficha in memoria.items() if ficha.get("estado")]
    if con_memoria and pasaron < len(casos):
        # (P89) Un caso puede fallar por lo que quedó guardado, y no por el programa.
        varios = "n" if len(con_memoria) > 1 else ""
        mostrar(f"Ojo: {' y '.join(con_memoria)} arranca{varios} cada pregunta con lo que "
                f"recuerda{varios} de las corridas de verdad")
        mostrar(f"({os.path.basename(archivo_memoria)}). Si un caso falló por eso (stock "
                "que ya se vendió, por ejemplo), no hay")
        mostrar("que cambiar el programa: cambiá el caso, o empezá de nuevo corriendo el "
                "programa con --olvidar")
        mostrar("(borra lo que recuerdan los agentes, no sus lecciones).")
    if sin_comprobar:
        mostrar(f"{sin_comprobar} caso(s) no se pudieron comprobar porque la IA no contestó: "
                "no cuentan como")
        mostrar("pasados. Arriba está el motivo; arreglalo y ensayá de nuevo.")
    if frenadas:
        mostrar(f"En {frenadas} pregunta(s) saltó un freno: lo que dijo la IA no pasaba y "
                "Mate no lo dejó salir así.")
    if consultas and not simulada:
        mostrar("Las consultas de un ensayo no entran en la cuenta del día ni en la bitácora.")
    if simuladas_sin_proponer:
        mostrar("Con --ia-simulada no quedan lecciones propuestas. Para ver qué contesta la "
                "IA de verdad (y que")
        mostrar("lo que falle quede propuesto), ensayá sin --ia-simulada.")
    if a_proponer:
        candado = pedir_candado_de_memoria(ruta, avisar,
                                           "aviso: no dejé las lecciones propuestas")
        if candado is None:
            return 1
        try:
            # Las propuestas van a la memoria que está AHORA en el disco (pudo cambiar
            # mientras se ensayaba), leída con el candado ya tomado, y es lo único que se
            # le agrega.
            try:
                en_disco = leer_memoria(archivo_memoria)[0]
            except ErrorMate as e:
                avisar(f"aviso: no dejé las lecciones propuestas: {e.mensaje}")
                return 1
            fecha, nuevas, repetidas = datetime.datetime.now().strftime("%d/%m/%Y %H:%M"), 0, 0
            ya_aprobadas = []  # los agentes que ya tenían aprobada la lección de un caso fallado
            for agente, texto, motivo in a_proponer:
                ficha = en_disco.setdefault(agente, {"estado": {}, "lecciones": []})
                if any(leccion["texto"] == en_un_renglon(texto, LARGO_DE_LECCION)
                       for leccion in ficha["lecciones"]):
                    ya_aprobadas += [agente] if agente not in ya_aprobadas else []
                    continue
                antes = ficha.get("propuestas", [])
                ficha["propuestas"] = sumar_propuesta(antes, ficha["lecciones"], texto,
                                                      motivo, fecha)
                nuevas += ficha["propuestas"] is not antes
                repetidas += ficha["propuestas"] is antes
                if not ficha["propuestas"]:
                    del ficha["propuestas"]
            for agente in ya_aprobadas:
                mostrar(f"{agente} ya tiene aprobada la lección de un caso que volvió a fallar: "
                        "no alcanzó.")
                mostrar("Una lección es un pedido, no una garantía. Escribila de otra forma (se "
                        "ven con la orden de")
                mostrar("abajo y se anotan con 'corregir'), o pasá la regla al programa o a un "
                        "freno del agente:")
                mostrar(f"  {orden} lecciones {para_pegar(args[0])}")
            if nuevas:
                problema = guardar_memoria(archivo_memoria, programa, en_disco,
                                          candado=candado)
                if problema:
                    avisar(f"aviso: {problema}")
                    return 1
                mostrar(f"Por los casos que fallaron quedó {nuevas} lección(es) propuesta(s). "
                        "Ningún agente las usa")
                mostrar("hasta que las apruebes. Para verlas (y aprobarlas o descartarlas):")
            elif repetidas:
                mostrar("Las lecciones de los casos que fallaron ya estaban propuestas, sin "
                        "aprobar. Para verlas:")
            if nuevas or repetidas:
                mostrar(f"  {orden} propuestas {para_pegar(args[0])}")
                mostrar("Una propuesta es un borrador: si la aprobás, ensayá de nuevo para ver "
                        "si alcanzó.")
        finally:
            soltar_candado_de_memoria(candado, archivo_de(ruta, "memoria.candado"))
    return 0 if pasaron == len(casos) and not cortado else 1


def texto_de_ayuda():
    if os.name == "nt":
        ejemplo = con_la_orden_de_esta_computadora(
            "python mate\\mate.py correr mate\\ejemplos\\hola.mate")
    else:
        ejemplo = "python3 mate/mate.py correr mate/ejemplos/hola.mate"
    return "\n".join([
        f"Mate {VERSION}: un lenguaje chico, con palabras en español.",
        "",
        "Órdenes:",
        "  correr    archivo.mate   corre el programa",
        "  probar    archivo.mate   corre las pruebas que el programa trae adentro",
        "  probar    carpeta        corre las pruebas de todos los .mate de esa carpeta",
        "  verificar archivo.mate   revisa el programa sin correrlo (nombres, contratos...)",
        "  guia                     una página con todo Mate, para pegarle a una IA",
        "  ayuda                    muestra esta ayuda",
        "  ayuda si                 explica una palabra o una función de Mate, con un ejemplo",
        "  consola                  para probar renglones sueltos sin crear un archivo",
        "  curso                    las clases para aprender Mate desde cero, en orden",
        "  curso 1                  muestra la clase 1 (también se abre con el Bloc de notas)",
        "  nuevo mostrador mi_negocio   crea en esta carpeta un mostrador propio, listo para",
        "                           usar: mi_negocio.mate y su planilla de muestra,",
        "                           mi_negocio_precios.csv. No pisa archivos que ya estén",
        "  nuevo equipo mi_negocio   crea en esta carpeta un equipo de tres agentes que se",
        "                           hablan (Ventas, Depósito y Compras), con su planilla y",
        "                           sus casos. Tampoco pisa archivos que ya estén",
        "  ensayar mi_negocio.mate mi_negocio_casos.txt   le hace al programa las preguntas",
        "                           de ese archivo (se escribe con el Bloc de notas: la",
        "                           pregunta del cliente y, debajo, 'tiene que decir: ...' o",
        "                           'no puede decir: ...') y dice cuáles contestó bien. Con",
        "                           --ia-simulada no gasta; sin eso contesta la IA de verdad,",
        "                           y los casos que fallan quedan como lección propuesta.",
        "                           En un equipo, un caso también puede exigir qué mensajes",
        "                           viajan entre los agentes: 'tiene que viajar: Reservar de",
        "                           Ventas a Deposito' o 'no tiene que viajar: Reponer'. Si un",
        "                           caso falla, el informe muestra la conversación.",
        "                           Si el cliente tiene que escribir algo más en la misma",
        "                           charla (el 'si' a un pedido), va debajo de la pregunta:",
        "                           'después: si'",
        "",
        "Para que un agente aprenda (mirá 'ayuda recordado'):",
        '  corregir  archivo.mate Mostrador "la lección"   le anota una lección a ese agente',
        "  lecciones archivo.mate   muestra las lecciones de cada agente",
        "  lecciones archivo.mate Mostrador --borrar=2   le borra la lección 2",
        "  bitacora  archivo.mate   resume las fallas que anotaron sus agentes, los frenos",
        "                           que saltaron y cuánto consultó a la IA cada agente por día",
        "",
        "Para confiarle la atención a un agente con IA (mirá 'ayuda frenos'):",
        "  frenos { ... }           va en el programa, dentro del agente: las reglas que Mate",
        "                           le revisa a cada respuesta de la IA (precios permitidos,",
        "                           palabras prohibidas, largo) y el tope de consultas por día",
        "  propuestas archivo.mate  muestra las lecciones propuestas: las deja cada freno que",
        "                           salta, y ningún agente las usa hasta que las aprobás",
        "  propuestas archivo.mate aprobar 1     la aprueba (o: descartar 1)",
        '  proponer  archivo.mate Mostrador "qué estuvo mal"   Mate redacta la lección y la',
        "                           deja propuesta (con clave la redacta la IA, y se paga)",
        "  Qué va en cada lugar: las cuentas y las reglas que tienen que dar siempre igual",
        "  (un total, el stock, desde cuántas unidades hay envío) van EN EL PROGRAMA, que",
        "  contesta sin consultar a la IA; lo que la IA no puede decir nunca, en un FRENO; el",
        "  tono y las costumbres, en una LECCIÓN. El ejemplo 12_mostrador_con_reglas.mate lo",
        "  muestra armado.",
        "",
        "Para trabajar con tus datos y charlar con el programa (son funciones: van adentro",
        "del programa, y cada una tiene su ayuda, por ejemplo 'ayuda leer_tabla'):",
        '  leer_tabla("precios.csv")   la planilla de Excel guardada como CSV, fila por fila',
        '  agregar_a_archivo("pedidos.txt", t)   anota un renglón más al final de ese archivo',
        '  leer("Cliente:", "chau")    espera que escribas y aprietes Enter (Ctrl+C termina)',
        "",
        "Para que dos programas de la misma carpeta se manden mensajes (mirá 'ayuda buzon'):",
        '  usar buzon "deposito.mate"   va en el programa: los agentes de ese otro programa',
        "                           quedan como destino de 'enviar'. El mensaje sale cuando",
        "                           el programa termina, y el otro lo atiende cuando corre",
        "  buzon deposito.mate      muestra qué hay en el buzón de ese programa: los mensajes",
        "                           que esperan, los que están por salir y los rechazados",
        "",
        "Para que tu programa se hable con el de OTRO negocio, en otra máquina (mirá 'ayuda",
        "socio'):",
        "  usar socio Proveedor acepta Cotizacion   va en el programa: Proveedor queda como",
        "                           destino de 'enviar', y solo se le reciben esos mensajes.",
        "                           Viajan firmados por una carpeta que comparten los dos, y",
        "                           lo que llega no se entrega sin tu si",
        "  nuevo socio              arma el ensayo en esta PC: dos negocios, la carpeta que",
        "                           comparten y los pasos para copiar",
        "  socio invitar comprador.mate Proveedor   genera la clave de ese socio y dice cómo",
        "                           pasársela (en un pendrive, o dictada). Del otro lado:",
        "                           socio aceptar proveedor.mate Cliente. Para cambiarla,",
        "                           socio renovar; para sacarla, socio quitar. Si la",
        "                           carpeta compartida cambió de lugar (el pendrive tiene",
        "                           otra letra), sin tocar la clave:",
        "                           socio carpeta comprador.mate Proveedor --carpeta=F:\\Compartida",
        "",
        "Para sumar lo que Mate no trae (mirá 'ayuda python'):",
        '  usar python "ayudas.py"  va en el programa: trae las funciones de ese archivo de',
        "                           Python, que está al lado, y se llaman ayudas.nombre(...).",
        "                           Ojo: ese Python corre con todos los permisos de la",
        "                           computadora. Usá solo archivos tuyos o de confianza",
        "",
        "Para que Mate mejore (anota en esta computadora los errores que te muestra):",
        "  informe                  resume los errores de uso: los más frecuentes y los que",
        "                           se repitieron seguido (el mensaje no alcanzó)",
        "  informe --para-mejorar   arma un texto para pegarle a un asistente y pedirle mejoras",
        "  informe --borrar         borra el registro de errores de uso",
        "",
        "Opciones:",
        "  --traza       muestra la conversación entre agentes, numerada y con lo que falló",
        "  --traza=conversacion.txt   la guarda en ese archivo, con un resumen al final",
        "  --guardar=guia.txt   con 'guia' o 'informe': deja el texto en ese archivo, con las",
        "                tildes bien para el Bloc de notas (en PowerShell, '>' las rompe)",
        "  --sin-limite  no corta los programas que dan muchísimos pasos",
        "  --ia-simulada consultar_ia() no sale a la red ni gasta: da su respuesta preparada",
        "  --ia-simulada=respuestas.txt   ...o las que están escritas en ese archivo",
        "  --olvidar     con 'correr': los agentes arrancan de cero, sin lo que recordaban",
        "  --veces=5     con 'ensayar': repite cada caso esa cantidad de veces (una IA no",
        "                contesta siempre igual) y dice, de cada uno, 'pasó 4 de 5'",
        "  --sin-registro  esta vez no anota nada en el registro de errores de uso",
        "  --depurar     si Mate falla por dentro, muestra el detalle técnico",
        "  --version     dice qué versión de Mate es",
        "",
        f"El registro de errores de uso es el archivo {NOMBRE_DEL_REGISTRO}, al lado de mate.py:",
        "no guarda tus programas, tapa tus datos y no sale de esta computadora. Para apagarlo",
        "del todo, en PowerShell:  $env:MATE_SIN_REGISTRO = \"1\"",
        "",
        "Un ejemplo listo para copiar:",
        f"  {ejemplo}",
        "(En Windows, si en tu computadora Python se llama con py, va py en lugar de python.",
        " Mate te sugiere los comandos con la forma que usaste: py, python o la orden mate.)",
    ])


def _ubicar(ruta):
    """Busca el archivo a correr. Devuelve (ruta, None) o (None, explicación)."""
    if os.path.isfile(ruta):
        return ruta, None
    if os.path.isfile(ruta + ".mate"):
        return ruta + ".mate", None
    if os.path.isdir(ruta):
        return None, f"'{ruta}' es una carpeta, no un archivo .mate"
    nombre = os.path.basename(ruta)
    if os.path.isfile(ruta + ".txt"):
        return None, (f"encontré {nombre}.txt: el Bloc de notas le agregó .txt. "
                      "Renombralo, o al guardar elegí Tipo: Todos los archivos")
    if os.path.exists(ruta):
        return ruta, None  # algo raro (ni archivo ni carpeta): que lo diga al abrirlo
    carpeta = os.path.dirname(os.path.abspath(ruta))
    texto = f"no encuentro '{nombre}' en {carpeta}"
    try:
        otros = sorted(a for a in os.listdir(carpeta) if a.lower().endswith(".mate"))
    except OSError:
        return None, texto + " (esa carpeta no existe)"
    if otros:
        texto += "\narchivos .mate que sí hay ahí: " + ", ".join(otros[:10])
        texto += ", ..." if len(otros) > 10 else ""
    return None, texto


def renglon_de(archivo, linea):
    """El renglón del archivo donde cayó el error, como '    N | texto' (o None)."""
    try:
        renglones = leer_fuente(archivo).split("\n")
    except (OSError, ErrorMate):
        return None
    n = int(linea)
    if n < 1:
        return None
    if n > len(renglones) or not any(r.strip() for r in renglones[n - 1:]):
        # El error cayó después del final: se muestra el último renglón con algo escrito.
        n = min(n, len(renglones))
        while n >= 1 and not renglones[n - 1].strip():
            n -= 1
    if n < 1 or not renglones[n - 1].strip():
        return None
    return f"    {n} | {renglones[n - 1].rstrip()}"


def error_escrito(ruta, linea, texto):
    """Un error como se muestra siempre, sea de un agente o no, con 'correr' o con
    'probar': 'archivo:renglón: error: texto', debajo el renglón señalado y, si lo hay,
    por dónde se llegó. Devuelve esas tres partes (las dos últimas pueden ser None)."""
    archivo = getattr(linea, "archivo", None) or ruta
    texto, _, camino = texto.partition("\ncómo se llegó: ")
    cabecera = (f"{archivo}:{linea}: error: {texto}" if linea
                else f"{archivo}: error: {texto}")
    renglon = renglon_de(archivo, linea) if linea else None
    return cabecera, renglon, f"    cómo se llegó: {camino}" if camino else None


def avisar_pendientes(interprete, avisar):
    """Si el programa se cortó con mensajes en la cola, dice cuáles no llegaron."""
    cola = list(getattr(interprete, "cola", ()))
    if not cola:
        return
    avisar(f"quedaron {len(cola)} mensaje(s) sin entregar:")
    for rem, dest, msg, _ in cola[:5]:
        avisar(f"  {rem.nombre if rem else '(programa)'} -> {dest.nombre}: {formato(msg)}")
    if len(cola) > 5:
        avisar(f"  ... y {len(cola) - 5} más")


def nombres_de_un_camino(camino):
    """Los nombres con que hay que mirar el último tramo de un camino: tal cual y como lo
    ve Windows (sin puntos ni espacios al final, sin lo que sigue a un ':'). En minúsculas."""
    nombre = camino.replace("\\", "/").rstrip("/").rsplit("/", 1)[-1].lower()
    return {nombre, nombre.rstrip(". "), nombre.split(":")[0].rstrip(". ")}


def traza_pisaria_la_memoria(destino, programa=None):
    """¿Ese destino de --traza= es un archivo que lleva Mate (la memoria de un programa, su
    provisorio, la apartada por rota, el candado, la bitácora o un sobre del buzón)? La
    traza se escribe sin candado, así que ahí no va nunca: pisaría lo que recuerdan los
    agentes (el stock, por ejemplo). Mira el nombre (entero y como lo ve Windows), adónde
    lleva de verdad (por si es un acceso a otro archivo) y, si se sabe qué programa corre,
    si es el mismo archivo que alguno de los suyos aunque se llame distinto."""
    def lo_lleva_mate(camino):
        tramos = camino.replace("\\", "/").lower().split("/")
        if any(t.split(":")[0].rstrip(". ").endswith(".buzon") for t in tramos[:-1]):
            return True
        return any(".memoria.json" in n or ".bitacora.txt" in n or n.endswith(
            (".memoria.rota.json", ".memoria.candado")) for n in nombres_de_un_camino(camino))
    try:
        real = os.path.realpath(destino)
    except (OSError, ValueError):
        real = destino
    if lo_lleva_mate(destino) or lo_lleva_mate(real):
        return True
    for que in (("memoria.json", "memoria.rota.json", "memoria.candado", "bitacora.txt")
                if programa else ()):
        try:
            if os.path.samefile(destino, archivo_de(programa, que)):
                return True
        except (OSError, ValueError):
            pass
    return False


def traza_no_va_ahi(destino, programa):
    """Antes de correr 'programa': ¿la traza iría a parar a un archivo que no se pisa,
    aunque el nombre no lo diga (un acceso o un enlace a la memoria, a la bitácora o a un
    programa)? Devuelve el aviso, o None si el destino sirve. Se mira ANTES de correr,
    para no atender nada y terminar con error en vez de avisar al final."""
    if traza_pisaria_la_memoria(destino, programa):
        return (f"no guardo la conversación en '{destino}': ese archivo lo lleva Mate (la "
                "memoria de los agentes, como el stock, la bitácora o el buzón). Elegí "
                "otro nombre, por ejemplo --traza=conversacion.txt")
    try:
        real = os.path.realpath(destino)
    except (OSError, ValueError):
        real = destino
    es_programa = any(n.endswith(NO_SE_PISAN) for n in nombres_de_un_camino(real))
    try:
        es_programa = es_programa or os.path.samefile(destino, programa)
    except (OSError, ValueError):
        pass
    if es_programa:
        return (f"no guardo la conversación en '{destino}' para no pisar un programa: "
                "elegí otro nombre, por ejemplo --traza=conversacion.txt")
    return None


def guardar_conversacion(destino, programa, renglones, cuenta, sumar=False):
    """Deja la conversación en un archivo de texto, con un resumen al final. Devuelve
    None si salió bien o la explicación de por qué no se pudo. Con sumar=True la agrega
    al final de lo que ya hay ('probar' con varios archivos: una sección por archivo)."""
    total = cuenta["enviar"] + cuenta["preguntar"]
    resumen = (f"Resumen: {total} mensaje(s) entregado(s): {cuenta['enviar']} con 'enviar' "
               f"y {cuenta['preguntar']} con 'preguntar'. ")
    resumen += ("Ninguno falló." if not cuenta["fallaron"]
                else f"Fallaron {cuenta['fallaron']}.")
    texto = "\n".join([f"Conversación de {programa}", ""] + renglones + ["", resumen, ""])
    if traza_pisaria_la_memoria(destino, programa):
        return (f"no guardé la conversación en '{destino}': ese archivo lo lleva Mate "
                "(la memoria de los agentes, la bitácora o el buzón)")
    try:
        # con la marca del principio, para que el Bloc de notas muestre bien las tildes
        with open(destino, "a" if sumar else "w",
                  encoding="utf-8" if sumar else "utf-8-sig") as f:
            f.write(("\n" if sumar else "") + texto)
    except OSError:
        return f"no pude guardar la conversación en '{destino}'"
    return None


def con_puntos(n):
    """12345 -> "12.345" (los miles con punto, como se escribe acá)."""
    return f"{n:,}".replace(",", ".")


def lineas_de_gasto(memoria, hoy):
    """Los renglones de 'bitacora' que cuentan cuánto consultó a la IA cada agente con
    frenos: hoy, día por día en la última semana, y el total de lo guardado. Se cuentan
    consultas y tokens (lo que informa el servicio), no plata: el precio cambia."""
    def cuanto(cuentas):
        consultas, simuladas, tokens = (sum(c.get(k, 0) for c in cuentas)
                                        for k in ("consultas", "simuladas", "tokens"))
        partes = [f"{con_puntos(consultas)} consulta{'' if consultas == 1 else 's'}"]
        if tokens:
            partes.append(f"{con_puntos(tokens)} tokens")
        texto = ", ".join(partes)
        if simuladas:
            texto += (f"  (y {con_puntos(simuladas)} simulada{'' if simuladas == 1 else 's'}, "
                      "que no se pagan)")
        return texto

    lineas = []
    for agente, ficha in memoria.items():
        gasto = ficha.get("gasto")
        if not gasto:
            continue
        lineas.append(f"  {agente}")
        lineas.append(f"    hoy:              {cuanto([gasto.get(hoy.isoformat(), {})])}")
        for atras in range(1, 7):
            dia = hoy - datetime.timedelta(days=atras)
            if dia.isoformat() in gasto:
                lineas.append(f"    {dia.strftime('%d/%m/%Y')}:       "
                              f"{cuanto([gasto[dia.isoformat()]])}")
        lineas.append(f"    últimos {len(gasto)} día(s) con consultas (se guardan "
                      f"{DIAS_DE_GASTO}): {cuanto(list(gasto.values()))}")
    if not lineas:
        return []
    return (["Consultas a la IA (la cuenta la llevan los agentes que tienen 'frenos'):"]
            + lineas + ["  Se cuentan consultas y tokens, que es lo que cobra el servicio; el "
                        "tope por día se pone en los 'frenos' del agente."])


INSTRUCCIONES_PARA_REDACTAR = (
    "Vas a ayudar al dueño de un negocio a corregir a su asistente, que atiende clientes. El "
    "dueño cuenta qué hizo mal el asistente. Escribí UNA lección corta para ese asistente, "
    "en castellano rioplatense y hablándole de vos (por ejemplo: 'No ofrezcas envíos: el "
    "negocio no los hace.'). Un solo renglón de no más de 250 letras, sin comillas y sin "
    "explicaciones: solo la lección.")


def redactar_leccion(queja, respuesta, opciones, respuestas, en_el_tope=None):
    """La lección que se propone a partir de lo que cuenta el dueño: (texto, quién la
    redactó, los tokens que costó). Con clave la redacta la IA; con --ia-simulada=archivo,
    el archivo; y si no hay IA (o falla, o se pasa de largo), va una redacción fija."""
    pregunta = f"Lo que estuvo mal, según el dueño: {queja}"
    if respuesta:
        pregunta += f"\nLo que había contestado el asistente: {respuesta}"
    fija = en_un_renglon(f"Una respuesta tuya estuvo mal: {queja.rstrip(' .')}. No lo "
                         "repitas.", LARGO_DE_LECCION)
    if "--ia-simulada" in opciones:
        pares = respuestas_de_archivo(respuestas) if respuestas else []
        dicho = respuesta_del_archivo(pares, pregunta)
        if dicho is None:
            return fija, "Es una redacción fija (con --ia-simulada sola no hay IA).", None
        como, tokens = "La redactó la IA simulada (el archivo de respuestas).", None
    elif not (os.environ.get("ANTHROPIC_API_KEY", "").strip()
              or os.environ.get("MATE_IA_PROPIA", "").strip()):
        return fija, ("Es una redacción fija: no hay clave para la IA (con la clave puesta "
                      "en ANTHROPIC_API_KEY la redacta la IA, y esa consulta se paga)."), None
    elif en_el_tope:
        return fija, (f"Es una redacción fija: no consulté a la IA porque {en_el_tope} (la "
                      "consulta de 'proponer' entra en esa misma cuenta)."), None
    else:
        _USO_DE_LA_IA.clear()
        try:
            dicho = pedir_a_la_ia(INSTRUCCIONES_PARA_REDACTAR, pregunta)
        except ErrorMate as e:
            # (si llegó a Anthropic y volvió sin servir, se cobra igual: entra en la cuenta)
            return fija, ("Es una redacción fija, porque la IA no contestó: "
                          + e.mensaje.split("\n")[0]), (
                (_USO_DE_LA_IA.get("tokens") or 0) if _USO_DE_LA_IA.get("cobrada") else None)
        except Exception as e:  # nunca un error de Python (ni la clave) a la vista
            return fija, ("Es una redacción fija, porque algo salió mal al hablar con la IA "
                          f"({type(e).__name__})."), None
        como, tokens = "La redactó la IA (fue una consulta de verdad, paga).", \
            _USO_DE_LA_IA.get("tokens") or 0
    dicho = " ".join(dicho.split()).strip('"“”')
    if not dicho or len(dicho) > LARGO_DE_LECCION:
        return fija, ("Es una redacción fija: lo que redactó la IA estaba vacío o pasaba las "
                      f"{LARGO_DE_LECCION} letras de una lección."), tokens
    return dicho, como, tokens


def mostrar_bitacora(ruta, avisar):
    """La orden 'bitacora': las fallas que anotaron los agentes de ese programa, resumidas."""
    programa, archivo = os.path.basename(ruta), archivo_de(ruta, "bitacora.txt")
    try:
        renglones = renglones_de_bitacora(archivo)
    except ErrorMate as e:
        avisar(e.mensaje)
        return 2
    fallas = [r.split(" | ", 4) for r in renglones]
    raros = sum(len(f) != 5 for f in fallas)
    fallas = [f for f in fallas if len(f) == 5]
    try:  # la cuenta de consultas a la IA de los agentes con frenos (0.5)
        gasto = lineas_de_gasto(leer_memoria(archivo_de(ruta, "memoria.json"))[0],
                                datetime.date.today())
    except ErrorMate:
        gasto = []  # (la memoria no se entiende: eso lo explican 'correr' y 'lecciones')
    if not fallas:
        print(f"{programa} no tiene fallas anotadas"
              + (f" ({archivo} tiene {raros} renglón(es) que no entiendo)." if raros else "."))
        if gasto:
            print("\n".join([""] + gasto))
            return 0
        print("La bitácora se arma sola cuando falla un agente de un programa que usa "
              "'estado recordado', lecciones o frenos, al correrlo con 'correr'.")
        return 0
    print(f"Bitácora de {programa}: {len(fallas)} falla(s) anotada(s), del {fallas[0][0]} "
          f"al {fallas[-1][0]}.")

    def tabla(titulo, columna, largo, cuantos=None):
        veces = {}
        for falla in fallas:
            clave = en_un_renglon(falla[columna], largo)
            veces[clave] = veces.get(clave, 0) + 1
        print("")
        print(titulo)
        for clave, n in sorted(veces.items(), key=lambda par: -par[1])[:cuantos]:
            print(f"  {n:>4} {'vez ' if n == 1 else 'veces'}  {clave}")

    tabla("Por agente:", 1, 60)
    tabla("Qué pasó:", 2, 60)
    tabla("Los motivos que más se repiten:", 4, 110, 5)
    print("")
    print("Las últimas:")
    for falla in fallas[-5:]:
        print(f"  {falla[0]}  {falla[1]} {falla[2]} atendiendo {en_un_renglon(falla[3], 70)}")
        print(f"      {en_un_renglon(falla[4], 110)}")
    if raros:
        print("")
        print(f"({raros} renglón(es) del archivo no tienen la forma de siempre y no los conté)")
    if gasto:
        print("\n".join([""] + gasto))
    print("")
    print(f"Está todo en {archivo} (se abre con el Bloc de notas; si lo borrás, empieza "
          "de nuevo).")
    return 0


def orden_de_memoria(orden, args, borrar, avisar, opciones=(), respuestas=None):
    """Las órdenes 'corregir', 'lecciones', 'bitacora', 'propuestas' y 'proponer': miran (o
    cambian) lo que aprendió un programa, sin correrlo. Devuelven el código de salida.
    Las que cambian la memoria toman su candado, la leen de nuevo y recién ahí la cambian
    y la guardan (ver escribir_memoria); acá se suelta, salga como salga la orden."""
    tomado = {"candado": None, "ruta": None}
    try:
        return _orden_de_memoria(orden, args, borrar, avisar, opciones, respuestas, tomado)
    finally:
        if tomado["candado"] is not None:
            soltar_candado_de_memoria(tomado["candado"], tomado["ruta"])
            tomado["candado"] = None


def _orden_de_memoria(orden, args, borrar, avisar, opciones, respuestas, tomado):
    ejemplos = {"bitacora": "bitacora mi_mostrador.mate",
                "lecciones": "lecciones mi_mostrador.mate",
                "corregir": 'corregir mi_mostrador.mate Mostrador "Los lunes no hay pan"',
                "propuestas": "propuestas mi_mostrador.mate",
                "proponer": 'proponer mi_mostrador.mate Mostrador "Ofreció envíos y no '
                            'hacemos envíos"'}
    if not args:
        avisar(f"a '{orden}' le falta el programa, por ejemplo: {ejemplos[orden]}"
               + (f" (en esta carpeta hay un {orden}.mate: para correrlo, correr {orden}.mate)"
                  if os.path.isfile(f"{orden}.mate") else ""))
        return 2
    if borrar is not None and orden != "lecciones":
        avisar("--borrar va con 'lecciones', por ejemplo: lecciones mi_mostrador.mate "
               "Mostrador --borrar=2")
        return 2
    ruta, problema = _ubicar(args[0])
    if problema:
        avisar(problema)
        return 2
    programa = os.path.basename(ruta)
    if orden == "bitacora":
        if len(args) > 1:
            avisar(f"'bitacora' lleva solo el programa: {ejemplos[orden]}")
            return 2
        return mostrar_bitacora(ruta, avisar)
    try:
        fuente = leer_fuente(ruta)
        arbol = analizar(fuente, ruta)
        declarados = [s[2] for s in arbol if s[0] == "agente"]
        ajenos = {s[2].lower(): s for s in arbol if s[0] == "agente_ajeno"}
    except OSError:
        avisar(f"no pude abrir {ruta}")
        return 2
    except ErrorMate:
        avisar(f"{ruta} tiene un error y no puedo ver qué agentes tiene. Miralo con:  "
               f"{como_se_llama()} verificar {args[0]}")
        return 2
    archivo_memoria = archivo_de(ruta, "memoria.json")
    try:
        memoria, avisos = leer_memoria(archivo_memoria)
    except ErrorMate as e:
        avisar(e.mensaje)
        return 2
    for aviso in avisos:
        avisar(f"aviso: {aviso}")

    def conocido(nombre):
        """El agente con ese nombre, como está escrito en el programa (o None). Vale una
        copia con nombre ("Mostrador Centro") y da igual mayúsculas que minúsculas."""
        nombre = " ".join(nombre.split())
        posibles = declarados + [a for a in memoria if a not in declarados]
        for candidato in posibles:
            if candidato.lower() == nombre.lower():
                return candidato
        molde, _, apodo = nombre.partition(" ")
        for candidato in declarados:
            if apodo and candidato.lower() == molde.lower():
                return f"{candidato} {apodo}"
        return None

    def listar(agente):
        for i, leccion in enumerate(memoria[agente]["lecciones"], 1):
            print(f"  {i}. {leccion['texto']}"
                  + (f"   (del {leccion['fecha']})" if leccion["fecha"] else ""))

    def tomar_y_releer(para_que, espera=None):
        """Antes de cambiar la memoria: toma su candado y la lee DE NUEVO, ya con el
        candado tomado ('memoria' pasa a ser lo que dice el archivo ahora, no lo que se
        leyó al empezar: en el medio pudo guardar una caja abierta en otra ventana). Si
        el candado lo tiene otra ventana, o la memoria ya no se entiende, avisa y
        devuelve False: no se cambia nada."""
        if tomado["candado"] is None:
            tomado["ruta"] = archivo_de(ruta, "memoria.candado")
            tomado["candado"] = pedir_candado_de_memoria(ruta, avisar, para_que, espera)
            if tomado["candado"] is None:
                return False
        try:
            releida = leer_memoria(archivo_memoria)[0]
        except ErrorMate as e:
            avisar(e.mensaje)
            return False
        memoria.clear()
        memoria.update(releida)
        return True

    def soltar():
        if tomado["candado"] is not None:
            soltar_candado_de_memoria(tomado["candado"], tomado["ruta"])
            tomado["candado"] = None

    def guardar():
        problema = guardar_memoria(archivo_memoria, programa, memoria,
                                   candado=tomado["candado"])
        if problema:
            avisar(problema)
        return problema

    if orden == "propuestas":
        if len(args) > 1 and sin_tildes(args[1].lower()) in ("aprobar", "descartar") \
                and not tomar_y_releer("no cambié las propuestas"):
            return 2
        return orden_propuestas(args, memoria, guardar, listar, avisar)

    # Una copia se nombra con el agente y su nombre: "Mostrador Centro". Si se escribió sin
    # comillas (Mostrador Centro), también vale: con 'lecciones' siempre, y con 'corregir'
    # cuando esa copia existe (está en el programa o en la memoria).
    copias = {" ".join(f"{molde} {apodo}".lower().split()) for molde, apodo in re.findall(
        r'\bcrear\s+(\w+)\s+llamado\s+"([^"\n{}]+)"', fuente)} | {a.lower() for a in memoria}
    if orden == "lecciones" and len(args) > 2:
        args = [args[0], " ".join(args[1:])]
    elif orden in ("corregir", "proponer") and len(args) > 2 and args[2].strip() \
            and conocido(args[1]) in declarados \
            and " ".join(f"{args[1]} {args[2]}".lower().split()) in copias:
        args = [args[0], f"{args[1]} {args[2]}"] + args[3:]
    agente = None
    if len(args) > 1:
        agente = conocido(args[1])
        if agente is None and " ".join(args[1].split()).lower() in ajenos:
            otro = ajenos[" ".join(args[1].split()).lower()]
            avisar(de_otro_programa(otro[2], otro[4], f"usar '{orden}' con él")
                   + ("" if otro[4] == SOCIO else
                      f". Probá con:  {como_se_llama()} {orden} {otro[4]} {otro[2]} ..."))
            return 2
        if agente is None:
            avisar(f"{programa} no tiene un agente '{args[1]}'.{sugerir(args[1], declarados)}"
                   + (" Sus agentes son: " + ", ".join(declarados) if declarados
                      else " Ese programa no tiene agentes"))
            return 2
    if orden == "proponer":
        if agente is None or len(args) < 3 or len(args) > 4 or not args[2].strip():
            avisar("a 'proponer' le faltan el agente y qué estuvo mal (entre comillas), por "
                   f"ejemplo: {ejemplos[orden]}"
                   + (". Los agentes de ese programa son: " + ", ".join(declarados)
                      if declarados and agente is None else "")
                   + (". Después puede ir, también entre comillas, lo que había contestado "
                      "el agente; nada más" if len(args) > 4 else ""))
            return 2
        queja = " ".join(args[2].split())
        if len(queja) > 220:
            avisar(f"lo que estuvo mal tiene {len(queja)} letras y el tope es 220: contalo "
                   "más corto (de ahí sale una lección, y las lecciones son cortas)")
            return 2
        # El tope por día del agente también vale acá, cuando está escrito como un número
        # fijo en sus frenos: si ya llegó, no se consulta (va la redacción fija).
        molde = agente.split(" ")[0] if agente not in declarados \
            and agente.split(" ")[0] in declarados else agente
        topes = {regla: valor_escrito(e)[1] for s in arbol
                 if s[0] == "agente" and s[2] == molde for _, regla, e in s[6]
                 if regla in ("consultas_por_dia", "tokens_por_dia")
                 and type(valor_escrito(e)[1]) is int}
        gastado = memoria.get(molde, {}).get("gasto", {}).get(
            datetime.date.today().isoformat(), {})
        en_el_tope = None
        if "consultas_por_dia" in topes and gastado.get("consultas", 0) >= topes[
                "consultas_por_dia"]:
            en_el_tope = (f"{molde} ya hizo {gastado.get('consultas', 0)} consulta(s) a la IA "
                          f"hoy y su tope es {topes['consultas_por_dia']} por día")
        elif "tokens_por_dia" in topes and gastado.get("tokens", 0) >= topes["tokens_por_dia"]:
            en_el_tope = (f"{molde} ya gastó {gastado.get('tokens', 0)} tokens hoy y su tope "
                          f"es {topes['tokens_por_dia']} por día")
        # Antes de consultar a la IA se mira que el candado de la memoria se pueda tomar:
        # si el programa está abierto en otra ventana, la propuesta no se va a poder
        # anotar, y no se gasta una consulta para nada. Se suelta enseguida: la consulta
        # puede tardar, y no se hace con el candado tomado.
        if not tomar_y_releer("no dejé la propuesta"):
            return 2
        soltar()
        try:
            texto, como, tokens = redactar_leccion(
                queja, en_un_renglon(args[3], 600) if len(args) > 3 else "", opciones,
                respuestas, en_el_tope)
        except ErrorMate as e:
            avisar(e.mensaje)
            return 2
        # Y para anotarla: el candado de nuevo, y la memoria leída de nuevo con él tomado.
        if not tomar_y_releer("no dejé la propuesta", espera=10):
            return 2
        ficha = memoria.setdefault(agente, {"estado": {}, "lecciones": []})
        if tokens is not None:  # fue una consulta de verdad: entra en la cuenta de hoy
            # (la cuenta es del agente declarado: sus copias cuentan con él)
            hoy = memoria.setdefault(molde, {"estado": {}, "lecciones": []}).setdefault(
                "gasto", {}).setdefault(
                datetime.date.today().isoformat(), {"consultas": 0, "simuladas": 0, "tokens": 0})
            hoy["consultas"], hoy["tokens"] = hoy["consultas"] + 1, hoy["tokens"] + tokens
        antes = ficha.get("propuestas", [])
        nuevas = sumar_propuesta(antes, ficha["lecciones"], texto,
                                 f"lo dijo el dueño: {queja}",
                                 datetime.datetime.now().strftime("%d/%m/%Y %H:%M"))
        if nuevas is antes:
            if tokens is not None:
                guardar()
            print(f"{agente} ya tenía esa lección (propuesta o aprobada): no la repito.")
            print(f"  {texto}")
            return 0
        ficha["propuestas"] = nuevas
        if guardar():
            return 1
        numero = sum(len(memoria[a].get("propuestas", [])) for a in list(memoria)[
            :list(memoria).index(agente) + 1])
        print(f"Quedó propuesta para {agente} (todavía NO la usa: falta que la apruebes):")
        print(f"  {numero}. {texto}")
        print(como)
        print(f"Para aprobarla:    {como_se_llama()} propuestas {para_pegar(args[0])} "
              f"aprobar {numero}")
        print(f"Para descartarla:  {como_se_llama()} propuestas {para_pegar(args[0])} "
              f"descartar {numero}")
        print(f"Si preferís escribirla vos:  {como_se_llama()} corregir "
              f'{para_pegar(args[0])} {para_pegar(agente)} "la lección"')
        return 0
    if orden == "corregir":
        if agente is None or len(args) < 3:
            avisar("a 'corregir' le faltan el agente y la lección (entre comillas), por "
                   f"ejemplo: {ejemplos[orden]}"
                   + (". Los agentes de ese programa son: " + ", ".join(declarados)
                      if declarados and agente is None else ""))
            return 2
        try:
            texto = leccion_limpia(" ".join(args[2:]))
        except ErrorMate as e:
            avisar(e.mensaje)
            return 2
        if not tomar_y_releer("no anoté la lección"):
            return 2
        ficha = memoria.setdefault(agente, {"estado": {}, "lecciones": []})
        nuevas, olvidadas = sumar_leccion(
            ficha["lecciones"], texto, datetime.datetime.now().strftime("%d/%m/%Y %H:%M"))
        if nuevas is ficha["lecciones"]:
            print(f"{agente} ya tenía anotada esa lección: no la repito.")
            return 0
        ficha["lecciones"] = nuevas
        if guardar():
            return 1
        print(f"Anotado. {agente} tiene {len(nuevas)} lección(es):")
        listar(agente)
        if olvidadas:
            print(f"(El tope es {MAX_LECCIONES}: para anotar esta se borró la más vieja.)")
        print("La va a tener en cuenta cada vez que consulte a la IA con consultar_ia(), "
              f"desde la próxima corrida de {programa} (la memoria y las lecciones son del "
              "programa que se corre).")
        print(f"Para borrar una:  {como_se_llama()} lecciones {para_pegar(args[0])} "
              f"{para_pegar(agente)} --borrar=1")
        return 0
    # lecciones
    los_que_tienen = [a for a in memoria if memoria[a]["lecciones"]]
    if borrar is not None:
        if agente is None:
            avisar("para borrar una lección hay que decir de qué agente, por ejemplo: "
                   "lecciones mi_mostrador.mate Mostrador --borrar=2")
            return 2
        if not tomar_y_releer("no borré nada"):
            return 2
        suyas = memoria.get(agente, {"lecciones": []})["lecciones"]
        if borrar.lower() == "todas" and suyas:
            quedan = []
        elif borrar.isdigit() and 1 <= int(borrar) <= len(suyas):
            quedan = suyas[:int(borrar) - 1] + suyas[int(borrar):]
        else:
            avisar(f"{agente} no tiene lecciones para borrar" if not suyas else
                   f"--borrar lleva el número de la lección (del 1 al {len(suyas)}) o "
                   f"'todas', y recibió '{borrar}'")
            return 2
        memoria[agente]["lecciones"] = quedan
        if guardar():
            return 1
        print(f"Borrada. A {agente} le quedan {len(quedan)} lección(es)"
              + (":" if quedan else "."))
        listar(agente)
        return 0
    mostrar_de = [agente] if agente else los_que_tienen
    if not any(memoria.get(a, {"lecciones": []})["lecciones"] for a in mostrar_de):
        if not agente and not declarados:
            print(f"{programa} no tiene agentes, así que no hay lecciones: las lecciones "
                  "son de los agentes.")
            return 0
        print((f"{agente} todavía no tiene lecciones." if agente
               else f"Los agentes de {programa} todavía no tienen lecciones.")
              + f" Se anota una con:  {como_se_llama()} corregir {para_pegar(args[0])} "
              + para_pegar(agente or declarados[0]) + ' "la lección"')
        return 0
    for a in mostrar_de:
        print(f"{a} tiene {len(memoria[a]['lecciones'])} lección(es):")
        listar(a)
    return 0


def orden_propuestas(args, memoria, guardar, listar, avisar):
    """La orden 'propuestas': ver las lecciones propuestas (las que dejó un freno al saltar
    o la orden 'proponer') y aprobarlas o descartarlas por su número. Una propuesta no se
    usa hasta que se aprueba; al aprobarla pasa a ser una lección como las de 'corregir'."""
    programa = para_pegar(args[0])
    todas = [(agente, propuesta) for agente, ficha in memoria.items()
             for propuesta in ficha.get("propuestas", [])]
    ver = f"{orden_para_esta_carpeta()} propuestas {programa}"
    if len(args) == 1:
        if not todas:
            print(f"{os.path.basename(args[0])} no tiene lecciones propuestas. Aparecen "
                  "solas cuando salta un freno de un agente, o las pedís con:  "
                  f'{orden_para_esta_carpeta()} proponer {programa} Agente "qué estuvo mal"')
            return 0
        print(f"Lecciones propuestas, sin aprobar ({len(todas)}). Ningún agente las usa "
              "todavía:")
        for numero, (agente, propuesta) in enumerate(todas, 1):
            print(f"  {numero}. Para {agente}: {propuesta['texto']}"
                  + (f"   (del {propuesta['fecha']})" if propuesta["fecha"] else ""))
            if propuesta["motivo"]:
                print(f"       Por qué: {propuesta['motivo']}")
        print(f"Para aprobar una:    {ver} aprobar 1")
        print(f"Para descartar una:  {ver} descartar 1     (o varias: descartar 1 2, o todas)")
        return 0
    que = sin_tildes(args[1].lower())
    if que not in ("aprobar", "descartar"):
        avisar(f"después del programa va 'aprobar' o 'descartar' y el número de la propuesta "
               f"(recibió '{args[1]}'). Para verlas con su número:  {ver}")
        return 2
    if not todas:
        avisar(f"no hay propuestas para {que}: {os.path.basename(args[0])} no tiene ninguna")
        return 2
    pedidas = args[2:]
    if [p.lower() for p in pedidas] == ["todas"]:
        numeros = list(range(1, len(todas) + 1))
    elif pedidas and all(p.isdigit() and 1 <= int(p) <= len(todas) for p in pedidas):
        numeros = sorted({int(p) for p in pedidas})
    else:
        avisar(f"a '{que}' le falta el número de la propuesta (del 1 al {len(todas)}; pueden "
               f"ser varios, o 'todas')" + (f" y recibió '{' '.join(pedidas)}'" if pedidas
                                            else "") + f". Para verlas:  {ver}")
        return 2
    tocados, olvidadas, repetidas = [], 0, 0
    for numero in numeros:
        agente, propuesta = todas[numero - 1]
        ficha = memoria[agente]
        ficha["propuestas"] = [p for p in ficha["propuestas"] if p is not propuesta]
        if not ficha["propuestas"]:
            del ficha["propuestas"]
        if que == "aprobar":
            nuevas, sobran = sumar_leccion(
                ficha["lecciones"], propuesta["texto"],
                datetime.datetime.now().strftime("%d/%m/%Y %H:%M"))
            repetidas += nuevas is ficha["lecciones"]
            ficha["lecciones"], olvidadas = nuevas, olvidadas + sobran
        if agente not in tocados:
            tocados.append(agente)
    if guardar():
        return 1
    cuantas = "1 propuesta" if len(numeros) == 1 else f"{len(numeros)} propuestas"
    if que == "descartar":
        print(f"Listo: descarté {cuantas}. Quedan {len(todas) - len(numeros)} sin aprobar.")
        return 0
    print(f"Listo: aprobé {cuantas}. Desde la próxima corrida "
          f"{'la' if len(numeros) == 1 else 'las'} va a tener en cuenta en cada consulta a "
          "la IA.")
    for agente in tocados:
        print(f"{agente} tiene {len(memoria[agente]['lecciones'])} lección(es):")
        listar(agente)
    if repetidas:
        print(f"({repetidas} ya estaba(n) entre las lecciones: no se repite(n).)")
    if olvidadas:
        print(f"(El tope es {MAX_LECCIONES} lecciones por agente: para anotar "
              f"{'esta' if len(numeros) == 1 else 'estas'} se borró la más vieja.)")
    if len(todas) > len(numeros):
        print(f"Quedan {len(todas) - len(numeros)} propuesta(s) sin aprobar:  {ver}")
    return 0


# ─────────────── La orden 'socio': la clave que comparten dos negocios (0.8) ───────────────
# 'socio invitar' genera la clave y dice cómo pasársela al otro negocio POR FUERA (en un
# pendrive, o dictada por teléfono); 'socio aceptar' la carga del otro lado; 'socio
# renovar' la cambia y 'socio quitar' la saca. La clave nunca va como parte de la orden
# (quedaría en el historial de PowerShell), ni en el .mate, ni en la carpeta compartida.
# En pantalla se muestra solo su "número de control", que los dos socios comparan por
# teléfono: es lo único que detecta un pendrive cambiado en el camino.
ARCHIVO_DE_INVITACION = "invitacion-mate.txt"
_NOMBRE_DE_INVITACION = re.compile(r"(?i)invitacion-mate[\w\-]*\.txt")
AVISO_DE_INVITACION = (
    "NO MANDES ESTE ARCHIVO POR MAIL NI POR WHATSAPP, y no lo copies a la carpeta "
    "compartida: es la clave de un socio de Mate. Llevalo en un pendrive, cargalo con "
    "'socio aceptar' y borralo.")


def pedir_oculto(pregunta):
    """Pide un texto SIN mostrarlo mientras se tipea (la clave que dictó el socio). Si acá
    no se puede ocultar lo que se escribe, ErrorMate: la clave no se tipea a la vista."""
    import getpass
    import warnings
    no_se_puede = ErrorMate(
        "acá no puedo ocultar lo que se tipea, y la clave de un socio no se escribe a la "
        "vista. Corré esta orden en una ventana de PowerShell común, o pedile a tu socio "
        "el archivo de invitación y pasalo con --invitacion=...")
    try:
        if not (sys.stdin.isatty() and sys.stdout.isatty()):
            raise no_se_puede
    except (AttributeError, ValueError):
        raise no_se_puede
    with warnings.catch_warnings():
        warnings.simplefilter("error")  # (getpass avisa, en vez de fallar, si no oculta)
        try:
            return getpass.getpass(pregunta)
        except (Warning, EOFError, OSError):
            raise no_se_puede


def leer_invitacion(ruta):
    """La clave que trae ese archivo de invitación. OSError si no es un archivo común o no
    se puede abrir; ErrorMate si no es una invitación entera. Del archivo solo se usan la
    versión y la clave: nada de rutas ni de otros datos."""
    with abrir_sin_seguir(ruta) as f:
        crudo = f.read(10_001)
    version = clave = None
    for renglon in crudo[:10_000].decode("utf-8-sig", "replace").splitlines():
        partes = renglon.strip().split(":", 1)
        if len(partes) == 2 and partes[0].strip() == "mate-invitacion":
            version = partes[1].strip()
        elif len(partes) == 2 and partes[0].strip() == "clave":
            clave = clave_de_socio_valida(partes[1])
    if version != "1" or clave is None:
        raise ErrorMate(
            f"{os.path.basename(ruta)} no es una invitación de Mate entera (o está dañada): "
            "pedile a tu socio que la genere de nuevo con 'socio renovar'")
    return clave


def escribir_invitacion(destino, clave):
    """Escribe la invitación sin pisar nada y, donde el sistema lo permite, legible solo
    para el dueño. Trae nada más que el aviso, la versión y la clave."""
    texto = f"{AVISO_DE_INVITACION}\nmate-invitacion: 1\nclave: {clave_en_grupos(clave)}\n"
    fd = os.open(destino, os.O_WRONLY | os.O_CREAT | os.O_EXCL
                 | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0), 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(texto.replace("\n", os.linesep).encode("utf-8"))


def sobres_en_viaje(ficha):
    """Cuántos sobres de ESTE lado siguen en la carpeta compartida con ese socio (los dejó
    este programa y el otro todavía no los trajo). Solo cuenta: no abre ni toca nada."""
    mia = os.path.join(ficha["carpeta"], "de-a" if ficha["lado"] == "A" else "de-b")
    cuantos = 0
    try:
        if not es_carpeta_real(mia):
            return 0
        with os.scandir(mia) as hay:
            for n, entrada in enumerate(hay):
                if n >= MAX_MIRADOS_POR_CORRIDA:
                    break
                cuantos += bool(_SOBRE_EN_COMPARTIDA.fullmatch(entrada.name.lower()))
    except OSError:
        return 0
    return cuantos


def preparar_compartida(carpeta):
    """Deja armada la carpeta compartida: de-a, de-b y el LEEME (sin pisar nada)."""
    for sub in ("de-a", "de-b"):
        completa = os.path.join(carpeta, sub)
        if not os.path.lexists(completa):
            os.mkdir(completa)
    leeme = os.path.join(carpeta, LEEME_DE_COMPARTIDA)
    if not os.path.lexists(leeme):
        with open(leeme, "x", encoding="utf-8-sig") as f:
            f.write(TEXTO_DEL_LEEME.replace("\n", os.linesep))


def orden_socio(args, avisar, mostrar=print, entrada=None, oculto=None, es_terminal=None):
    """La orden 'socio invitar|aceptar|renovar|quitar|carpeta programa.mate Socio'.
    Devuelve el código de salida. entrada, oculto y es_terminal son para las pruebas: de dónde salen
    las respuestas, la clave tipeada, y si la pantalla es una ventana de verdad."""
    entrada = entrada or por_teclado
    orden = orden_para_esta_carpeta()
    opciones, resto = {}, []
    for a in args:
        bajo = sin_tildes(a.lower())
        if bajo == "--dictar":
            opciones["dictar"] = True
        elif bajo.startswith("--carpeta=") or bajo.startswith("--invitacion="):
            nombre, _, valor = a.partition("=")
            opciones[sin_tildes(nombre.lower())[2:]] = valor.strip().strip('"').strip("'")
        elif a.startswith("--"):
            avisar(f"'socio' no conoce la opción {a}. Las que hay son --carpeta=..., "
                   "--invitacion=... y --dictar. (La clave nunca va en la orden.)")
            return 2
        else:
            resto.append(a)
    que = sin_tildes(resto[0].lower()) if resto else ""
    if que not in ("invitar", "aceptar", "renovar", "quitar", "carpeta") or len(resto) != 3:
        avisar("'socio' lleva qué hacer, el programa y el nombre del socio (el de su 'usar "
               f"socio'). Por ejemplo:\n  {orden} socio invitar comprador.mate Proveedor   "
               "(genera la clave y dice cómo pasársela)\n"
               f"  {orden} socio aceptar proveedor.mate Cliente     (carga la clave que te "
               f"pasó tu socio)\n  {orden} socio renovar comprador.mate Proveedor   (cambia "
               f"la clave)\n  {orden} socio quitar comprador.mate Proveedor    (la saca)\n"
               f"  {orden} socio carpeta comprador.mate Proveedor --carpeta=F:\\Compartida"
               "   (cambia solo la carpeta compartida; la clave queda igual)")
        return 2
    ruta, problema = _ubicar(resto[1])
    if problema:
        avisar(problema)
        return 2
    if not ruta.lower().endswith((".mate", ".mate.txt")):
        avisar(f"'socio' lleva un programa de Mate (un archivo .mate), y "
               f"'{os.path.basename(ruta)}' no lo es")
        return 2
    programa, raiz = os.path.basename(ruta), os.path.dirname(os.path.abspath(ruta))
    try:
        declarados = socios_declarados(analizar(leer_fuente(ruta), ruta))
    except OSError:
        avisar(f"no pude abrir {ruta}")
        return 2
    except ErrorMate as e:
        avisar(f"{programa} tiene un error y así no sé qué socios declara: {e.mensaje}. "
               f"Miralo con:  {orden} verificar {para_pegar(resto[1])}")
        return 2
    socio = next((s for s in declarados if s == resto[2]), None) \
        or next((s for s in declarados if s.lower() == resto[2].lower()), None)
    if socio is None:
        avisar(f"{programa} no declara ningún socio '{resto[2]}'."
               + (" Sus socios son: " + ", ".join(declarados) + "." if declarados else "")
               + " Para declararlo, agregá arriba en el programa un renglón como:  usar "
               f"socio {resto[2][:1].upper() + resto[2][1:]} acepta Cotizacion   (después "
               "de 'acepta' van los mensajes que le recibís)")
        return 2
    fichas, problema = leer_socios(ruta)
    if problema:
        avisar(problema)
        return 1
    existente = fichas.get(socio)
    de_claves = os.path.basename(archivo_de(ruta, "socios.json"))

    def preguntar(texto):
        try:
            return entrada(texto).replace("\ufeff", "").strip()
        except (EOFError, OSError, UnicodeError):
            return None

    def dijo_si(texto):
        return (preguntar(texto) or "").lower() in ("si", "sí")

    def elegir_carpeta(previa=None):
        carpeta = opciones.get("carpeta")
        if carpeta is None and previa is not None:
            return previa
        if carpeta is None:
            carpeta = (preguntar(
                f"¿Cuál es la carpeta que compartís con {socio}? Tiene que ser una carpeta "
                "aparte, solo para ustedes dos (de OneDrive, de Google Drive, de red o un "
                "pendrive). Escribí la ruta completa: ") or "").strip('"').strip("'")
        if not carpeta:
            avisar("falta la carpeta compartida, y no hice nada. Por ejemplo:  "
                   f"{orden} socio {que} {para_pegar(resto[1])} {socio} "
                   "--carpeta=C:\\Compartida")
            return None
        carpeta = os.path.abspath(os.path.expanduser(carpeta))
        if not es_carpeta_real(carpeta):
            avisar(f"no encuentro la carpeta {carpeta} (o no es una carpeta de verdad). "
                   "Creala primero, compartila con tu socio y corré esta orden de nuevo")
            return None
        problema = problema_de_compartida(raiz, carpeta)
        if problema:
            avisar(f"no uso esa carpeta: {problema}")
            return None
        for otro, ficha in fichas.items():
            if otro != socio and una_adentro_de_otra(ficha["carpeta"], carpeta):
                avisar(f"esa carpeta ya es la que compartís con {otro} (o está adentro): "
                       "cada par de negocios usa una carpeta aparte, que solo ven ellos dos")
                return None
        return carpeta

    def en_una_compartida(donde, carpeta):
        """¿Ese lugar está adentro de la carpeta compartida con este socio o con otro?"""
        return any(esta_adentro(donde, c) for c in
                   [carpeta] + [f["carpeta"] for f in fichas.values()])

    def terminal():
        if es_terminal is not None:
            return es_terminal()
        try:
            return sys.stdout.isatty()
        except (AttributeError, ValueError):
            return False

    def como_pasarla(carpeta):
        """Dónde escribir la invitación, "" si se dicta, o None si no se puede seguir."""
        destino, dictar = opciones.get("invitacion"), opciones.get("dictar")
        if destino is None and not dictar:
            mostrar(f"¿Cómo le pasás la clave a {socio}? Nunca por mail ni por WhatsApp:")
            mostrar("  1) En un pendrive o en mano (lo recomendado): Mate escribe un "
                    "archivo de invitación.")
            mostrar("  2) Dictada por teléfono: Mate la muestra UNA vez en pantalla.")
            dicho = preguntar("Escribí 1 o 2: ")
            if dicho == "2":
                dictar = True
            elif dicho == "1":
                destino = (preguntar(
                    "¿En qué carpeta dejo el archivo de invitación? (por ejemplo E:\\ si "
                    "el pendrive es la unidad E): ") or "").strip('"').strip("'")
            if not dictar and not destino:
                avisar("no hice nada: faltó decir cómo le pasás la clave. Por ejemplo:  "
                       f"{orden} socio {que} {para_pegar(resto[1])} {socio} "
                       "--invitacion=E:\\")
                return None
        if dictar:
            if not terminal():
                avisar("--dictar muestra la clave en pantalla, y eso lo hago solo en una "
                       "ventana de verdad: acá la salida va a un archivo o a otro programa, "
                       "y la clave quedaría escrita ahí. No hice nada")
                return None
            return ""
        destino = os.path.abspath(os.path.expanduser(destino))
        if os.path.isdir(destino):
            destino = os.path.join(destino, ARCHIVO_DE_INVITACION)
        if not _NOMBRE_DE_INVITACION.fullmatch(os.path.basename(destino)):
            avisar(f"el archivo de invitación se llama {ARCHIVO_DE_INVITACION} (o "
                   "invitacion-mate-algo.txt): decime solo la carpeta donde lo dejo, por "
                   "ejemplo --invitacion=E:\\")
            return None
        if not os.path.isdir(os.path.dirname(destino)):
            avisar(f"no encuentro la carpeta {os.path.dirname(destino)} para dejar la "
                   "invitación: ¿está puesto el pendrive?")
            return None
        if en_una_compartida(os.path.dirname(destino), carpeta):
            avisar("la invitación lleva la clave: no va en la carpeta compartida, ni en la "
                   "que compartís con otro socio (ahí la lee quien vea la carpeta). Dejala "
                   "en un pendrive y llevásela a tu socio. No hice nada")
            return None
        if os.path.lexists(destino):
            avisar(f"ya hay un {os.path.basename(destino)} en {os.path.dirname(destino)} y "
                   "no piso archivos: borralo (si es una invitación vieja, ya no sirve) o "
                   "elegí otra carpeta")
            return None
        return destino

    def claves_de_antes(ficha, clave):
        """Anota en la ficha nueva la huella (no la clave) de la que se va, y el lado."""
        antes = list(existente.get("antes", ())) if existente else []
        if existente and existente["clave"] != clave:
            antes.insert(0, {"huella": huella_de_clave(existente["clave"]),
                             "lado": existente["lado"]})
        if antes:
            ficha["antes"] = antes[:MAX_CLAVES_DE_ANTES]

    def guardar(nuevas):
        try:
            guardar_socios(ruta, nuevas)
        except OSError:
            avisar(f"no pude escribir {de_claves} en {raiz}: fijate que se pueda escribir "
                   "en esa carpeta. No cambié nada")
            return False
        return True

    def comparar_control(clave):
        control = control_de_socio(clave)
        mostrar(f"Número de control: {control}")
        mostrar(f"OBLIGATORIO: llamá a tu socio y comparen el número de control. Él tiene "
                f"que ver {control} en su pantalla. Si ve otro número, alguien cambió la "
                "clave en el camino: no la usen, y hagan 'socio renovar'.")

    def limites():
        mostrar("Para tener en cuenta: los mensajes viajan firmados pero NO cifrados (quien "
                "ve la carpeta compartida los puede leer), y nada de lo que mande tu socio "
                "llega a un agente sin tu si.")

    if que == "quitar":
        if existente is None:
            avisar(f"no hay ninguna clave cargada con {socio}: no hay nada que quitar")
            return 1
        if not dijo_si(f"Vas a quitar la clave con {socio} (control "
                       f"{control_de_socio(existente['clave'])}): con ese socio no se va a "
                       "mandar ni recibir nada más. Escribí si para quitarla: "):
            avisar("no quité nada (hacía falta contestar si)")
            return 1
        nuevas = {s: f for s, f in fichas.items() if s != socio}
        if not guardar(nuevas):
            return 1
        mostrar(f"Listo: saqué la clave con {socio}. Avisale a tu socio: lo que mande ya no "
                "se va a entregar.")
        return 0

    if que == "carpeta":
        # (0.8.1) Solo cambia dónde está la carpeta compartida: la clave, el lado y la
        # cuenta de los mensajes quedan como estaban, y el socio no tiene que hacer nada.
        if existente is None:
            avisar(f"no hay ninguna clave cargada con {socio}: la carpeta compartida se "
                   f"elige al cargarla. Si la clave la generás vos:  {orden} socio invitar "
                   f"{para_pegar(resto[1])} {socio}   Si te la pasó tu socio:  {orden} "
                   f"socio aceptar {para_pegar(resto[1])} {socio}")
            return 1
        if "invitacion" in opciones or "dictar" in opciones:
            avisar("'socio carpeta' cambia solo la carpeta compartida y no toca la clave: "
                   "no lleva --invitacion ni --dictar. Por ejemplo:  "
                   f"{orden} socio carpeta {para_pegar(resto[1])} {socio} "
                   "--carpeta=F:\\Compartida")
            return 2
        if "carpeta" not in opciones:
            mostrar(f"Ahora la carpeta compartida con {socio} es: {existente['carpeta']}")
        carpeta = elegir_carpeta()
        if carpeta is None:
            return 2
        if carpeta == existente["carpeta"]:
            mostrar(f"La carpeta compartida con {socio} ya era esa ({carpeta}): no cambié "
                    "nada.")
            return 0
        nuevas = dict(fichas)
        nuevas[socio] = dict(existente, carpeta=carpeta)
        if not guardar(nuevas):
            return 1
        try:
            preparar_compartida(carpeta)
        except OSError:
            avisar(f"aviso: no pude terminar de armar la carpeta compartida ({carpeta}); se "
                   "arma sola la primera vez que corra el programa")
        mostrar(f"Listo: la carpeta compartida con {socio} ahora es {carpeta}")
        mostrar(f"  (antes era {existente['carpeta']}). La clave NO cambió: sigue siendo la "
                f"de control {control_de_socio(existente['clave'])}, y tu socio no tiene "
                "que cargar nada.")
        mostrar("  Tiene que ser la MISMA carpeta que ve tu socio (el mismo pendrive, la "
                "misma carpeta de OneDrive o de Drive), aunque en cada PC tenga otra letra "
                "u otra ruta. Si en cambio pasaron a una carpeta nueva, tu socio tiene que "
                "hacer lo mismo en su PC con su 'socio carpeta', y lo que haya quedado sin "
                "traer en la carpeta vieja no se muda solo: hay que mandarlo de nuevo.")
        return 0

    if que == "invitar" and existente is not None:
        avisar(f"ya hay una clave cargada con {socio} (control "
               f"{control_de_socio(existente['clave'])}) y no la piso. Para cambiarla por "
               f"una nueva:  {orden} socio renovar {para_pegar(resto[1])} {socio}")
        return 1
    if que == "renovar" and existente is None:
        avisar(f"no hay ninguna clave cargada con {socio} para renovar. Para generar la "
               f"primera:  {orden} socio invitar {para_pegar(resto[1])} {socio}")
        return 1

    if que in ("invitar", "renovar"):
        if que == "renovar":
            est = leer_correo_de_memoria(archivo_de(ruta, "memoria.json"))["socios"].get(
                socio) or {}
            pierde = len(est.get("por_salir") or []) + len(est.get("traidos") or [])
            viajando = sobres_en_viaje(existente)
            if not dijo_si(
                    f"Vas a cambiar la clave con {socio} por una nueva. Con la clave vieja "
                    "ya no va a valer nada"
                    + (f": {cuantos_mensajes(pierde)} que estaban por salir o esperando tu "
                       "si se descartan" if pierde else "")
                    + (f"; y {cuantos_mensajes(viajando)} "
                       f"{'tuyo' if viajando == 1 else 'tuyos'} que tu socio todavía no "
                       "trajo de la carpeta compartida "
                       f"{'deja' if viajando == 1 else 'dejan'} de valer (si hacía falta, "
                       "hay que mandarlo de nuevo)" if viajando else "")
                    + f". Tu socio la tiene que cargar de nuevo con 'socio aceptar'. "
                    "Escribí si para seguir: "):
                avisar("no cambié nada (hacía falta contestar si)")
                return 1
        carpeta = elegir_carpeta(existente["carpeta"] if existente else None)
        if carpeta is None:
            return 2
        destino = como_pasarla(carpeta)
        if destino is None:
            return 2
        clave = nueva_clave_de_socio()
        while any(huella_de_clave(f["clave"]) == huella_de_clave(clave)
                  for f in fichas.values()):
            clave = nueva_clave_de_socio()  # (dos socios nunca comparten la huella)
        nuevas = dict(fichas)
        nuevas[socio] = {"clave": clave, "lado": "A", "carpeta": carpeta, "estrenado": False}
        claves_de_antes(nuevas[socio], clave)
        if not guardar(nuevas):
            return 1
        try:
            if destino:
                escribir_invitacion(destino, clave)
            preparar_compartida(carpeta)
        except OSError:
            guardar(fichas)  # (a medias no queda nada: vuelve lo que había)
            avisar(f"no pude escribir {'la invitación en ' + destino if destino else 'en la carpeta compartida'}"
                   ": fijate que se pueda escribir ahí. No cambié nada")
            return 1
        mostrar(f"Listo: la clave con {socio} quedó cargada en {de_claves}, al lado del "
                "programa. Ese archivo no se copia, no se manda y no se sube a ningún lado.")
        if destino:
            mostrar(f"La invitación para tu socio quedó en {destino}")
            mostrar("  Llevásela en el pendrive o en mano: NO por mail ni por WhatsApp.")
            mostrar("  Tu socio, parado en la carpeta de su programa, la carga así (el "
                    "nombre del final es cómo te llama él en su 'usar socio'; si en su PC "
                    "Mate está en otro lugar, la primera parte es la suya):")
            mostrar(f"       {orden} socio aceptar su_programa.mate Cliente")
            mostrar("  Mate le pregunta por la carpeta compartida y por la invitación, y "
                    "la borra al terminar.")
        else:
            mostrar("La clave, para dictársela a tu socio. Se muestra esta única vez: que "
                    "no la vea nadie más, y no la copies a ningún lado.")
            mostrar("")
            mostrar(f"       {clave_en_grupos(clave)}")
            mostrar("")
            mostrar("  Son 11 grupos de 4 cifras. Tu socio la tipea (no se ve mientras "
                    "escribe) con:")
            mostrar(f"       {orden} socio aceptar su_programa.mate Cliente")
            mostrar("  Si se equivoca en una cifra, Mate se da cuenta y no la carga.")
        comparar_control(clave)
        if que == "renovar":
            mostrar("HASTA QUE TU SOCIO CARGUE LA CLAVE NUEVA conviene que ninguno de los dos "
                    "corra su programa. Lo que mandes vos lo espera en la carpeta compartida "
                    "y le llega cuando la acepte; lo que mande él, firmado con la clave "
                    "vieja, ya no vale: Mate lo deja en la carpeta, te avisa, y a él le "
                    "avisa cuando acepte (lo tiene que mandar de nuevo).")
        limites()
        return 0

    # ── aceptar ──
    if existente is not None and not dijo_si(
            f"Ya hay una clave cargada con {socio} (control "
            f"{control_de_socio(existente['clave'])}). ¿La cambio por la que te pasó tu "
            "socio? Lo que estaba por salir o esperando tu si con la clave vieja se "
            "descarta, y lo tuyo que tu socio no llegó a traer de la carpeta compartida "
            "deja de valer (Mate te lo avisa en la corrida siguiente). Escribí si para "
            "cambiarla: "):
        avisar("no cambié nada (hacía falta contestar si)")
        return 1
    carpeta = elegir_carpeta(existente["carpeta"] if existente else None)
    if carpeta is None:
        return 2
    invitacion = opciones.get("invitacion")
    if opciones.get("dictar"):
        invitacion = ""
    elif invitacion is None:
        invitacion = preguntar(
            "Si tu socio te dio el archivo de invitación, escribí dónde está (por ejemplo "
            "E:\\). Si te dictó la clave por teléfono, apretá Enter: ")
        if invitacion is None:
            avisar("no hice nada: faltó decir dónde está la invitación. Por ejemplo:  "
                   f"{orden} socio aceptar {para_pegar(resto[1])} {socio} --invitacion=E:\\")
            return 2
        invitacion = invitacion.strip('"').strip("'")
    if invitacion:
        invitacion = os.path.abspath(os.path.expanduser(invitacion))
        if os.path.isdir(invitacion):
            invitacion = os.path.join(invitacion, ARCHIVO_DE_INVITACION)
        if en_una_compartida(os.path.dirname(invitacion), carpeta):
            avisar(f"no cargo esa invitación: está adentro de una carpeta compartida "
                   f"({os.path.dirname(invitacion)}), y la invitación lleva la clave ENTERA. "
                   "Quien ve esa carpeta ya la pudo copiar (y queda en la papelera y en el "
                   "historial de la nube): esa clave no sirve más. Borrá el archivo de ahí "
                   "y pedile a tu socio que haga 'socio renovar' y te lleve la invitación "
                   "nueva en un pendrive, o te dicte la clave. No cargué nada")
            return 2
        try:
            clave = leer_invitacion(invitacion)
        except OSError:
            avisar(f"no pude abrir la invitación ({invitacion}): fijate que esté ahí y que "
                   "sea el archivo que te dio tu socio")
            return 2
        except ErrorMate as e:
            avisar(e.mensaje)
            return 2
    else:
        try:
            tipeado = (oculto or pedir_oculto)(
                "Tipeá la clave que te dictó tu socio (11 grupos de 4 cifras; no se ve "
                "mientras escribís) y apretá Enter: ")
        except ErrorMate as e:
            avisar(e.mensaje)
            return 2
        clave = clave_de_socio_valida(tipeado)
        if clave is None:
            avisar("esa clave no cierra: tienen que ser 44 cifras, y alguna está mal o "
                   "falta (las últimas 4 son de control). No cargué nada: pedile a tu socio "
                   "que te la dicte de nuevo")
            return 2
    for otro, ficha in fichas.items():
        if otro != socio and ficha["clave"] == clave:
            avisar(f"esa clave ya está cargada con {otro}: cada socio tiene la suya, y una "
                   "misma clave no va en dos socios ni en dos programas. No cargué nada")
            return 2
    if existente is not None and existente["clave"] == clave and existente["lado"] == "A":
        avisar("esa es la clave que generó este mismo programa: la invitación es para tu "
               "socio, no para vos. No cambié nada")
        return 2
    nuevas = dict(fichas)
    nuevas[socio] = {"clave": clave, "lado": "B", "carpeta": carpeta,
                     "estrenado": bool(existente and existente["clave"] == clave
                                       and existente["estrenado"])}
    claves_de_antes(nuevas[socio], clave)
    if not guardar(nuevas):
        return 1
    try:
        preparar_compartida(carpeta)
    except OSError:
        avisar(f"aviso: no pude terminar de armar la carpeta compartida ({carpeta}); se "
               "arma sola la primera vez que corra el programa")
    mostrar(f"Listo: la clave con {socio} quedó cargada en {de_claves}, al lado del "
            "programa. Ese archivo no se copia, no se manda y no se sube a ningún lado.")
    if invitacion:
        try:
            os.remove(invitacion)  # (ya se entendió, y era un archivo común)
            mostrar(f"Borré la invitación ({invitacion}): ya no hace falta. (En un pendrive, "
                    "borrar no es destruir: si lo perdés, renueven la clave.)")
        except OSError:
            avisar(f"aviso: no pude borrar la invitación ({invitacion}): borrala a mano, "
                   "que adentro está la clave")
    comparar_control(clave)
    limites()
    return 0


# ── 'nuevo socio': el ensayo de dos negocios en una sola PC ──
EJEMPLOS_DE_SOCIOS = (("14_comprador.mate", "comprador.mate"),
                      ("14_proveedor.mate", "proveedor.mate"), ("14_trato.mate", "trato.mate"))
CARPETA_DEL_ENSAYO = "ensayo_de_socios"


def archivos_del_ensayo_de_socios(carpeta_de_mate=None, fin_de_renglon=None):
    """{(negocio, archivo): bytes} de lo que crea 'nuevo socio': los programas del ejemplo
    14, con los nombres cortos, y el trato en cada negocio."""
    ejemplos = os.path.join(carpeta_de_mate or os.path.dirname(os.path.abspath(__file__)),
                            CARPETA_DE_EJEMPLOS)
    fin = os.linesep if fin_de_renglon is None else fin_de_renglon
    textos = {}
    for de_muestra, corto in EJEMPLOS_DE_SOCIOS:
        try:
            texto = leer_fuente(os.path.join(ejemplos, de_muestra))
        except OSError:
            raise ErrorMate(
                f"no encuentro el ejemplo {de_muestra} (lo busqué en {ejemplos}): 'nuevo "
                "socio' lo copia de ahí. Fijate que la carpeta 'ejemplos' esté al lado de "
                "mate.py")
        for largo, nombre in EJEMPLOS_DE_SOCIOS:
            texto = texto.replace(largo, nombre)
        textos[corto] = texto.replace("\n", fin).encode("utf-8-sig")
    return {("comprador", "comprador.mate"): textos["comprador.mate"],
            ("comprador", "trato.mate"): textos["trato.mate"],
            ("proveedor", "proveedor.mate"): textos["proveedor.mate"],
            ("proveedor", "trato.mate"): textos["trato.mate"]}


def entre_comillas_simples(texto):
    """Como va en PowerShell para que no lo cambie: entre comillas simples (adentro de las
    dobles, PowerShell reemplaza $algo y el acento grave), con la comilla simple duplicada."""
    return "'" + texto.replace("'", "''") + "'"


def nuevo_socio(args, avisar, mostrar=print):
    """La orden 'nuevo socio [carpeta]': arma el ENSAYO de dos negocios en una sola PC. Crea
    una carpeta con tres adentro (comprador, proveedor y compartida), los programas del
    ejemplo 14 y una clave de ensayo ya cargada en los dos lados (al azar, sin mostrarla),
    y dice los pasos para copiar tal cual en PowerShell."""
    orden = orden_para_esta_carpeta()
    que_falta = "al escribir la orden: 'nuevo socio' con un nombre que no sirve"
    if len(args) > 1:
        avisar("'nuevo socio' lleva, como mucho, el nombre de la carpeta donde arma el "
               f"ensayo (una palabra, sin espacios). Por ejemplo:  {orden} nuevo socio "
               f"{'_'.join(args)}", que_falta, True)
        return 2
    nombre = args[0].strip() if args else CARPETA_DEL_ENSAYO
    if re.search(r"[\\/:]", nombre) or not re.fullmatch(r"[^\W_][\w\-]{0,59}", nombre) \
            or sin_tildes(nombre.lower()) in ORDENES_SABIDAS + _NOMBRES_DE_WINDOWS:
        avisar(f"'{nombre}' no sirve como nombre de la carpeta del ensayo: va una palabra "
               "(letras, números, guion o guion bajo), sin ruta, y se crea en la carpeta "
               f"donde estás parado. Por ejemplo:  {orden} nuevo socio {CARPETA_DEL_ENSAYO}",
               que_falta, True)
        return 2
    base = os.path.abspath(nombre)
    if os.path.lexists(base):
        avisar(f"no creé nada: en esta carpeta ya hay {nombre}, y no piso nada. Elegí otro "
               f"nombre, por ejemplo:  {orden} nuevo socio {nombre}_2",
               "al escribir la orden: 'nuevo socio' con un nombre que ya existe", True)
        return 1
    try:
        archivos = archivos_del_ensayo_de_socios()
    except ErrorMate as e:
        avisar(e.mensaje, "al escribir la orden: 'nuevo socio' sin los ejemplos de Mate")
        return 1
    compartida = os.path.join(base, "compartida")
    clave = nueva_clave_de_socio()
    try:
        os.mkdir(base)
        for negocio in ("comprador", "proveedor", "compartida"):
            os.mkdir(os.path.join(base, negocio))
        for (negocio, archivo), contenido in archivos.items():
            with open(os.path.join(base, negocio, archivo), "xb") as f:
                f.write(contenido)
        preparar_compartida(compartida)
        for negocio, socio, lado in (("comprador", "Proveedor", "A"),
                                     ("proveedor", "Cliente", "B")):
            guardar_socios(os.path.join(base, negocio, negocio + ".mate"), {socio: {
                "clave": clave, "lado": lado, "carpeta": compartida, "estrenado": False,
                "ensayo": True}})
    except OSError:
        avisar(f"no pude crear el ensayo en {para_pegar(base)}: fijate que se pueda "
               "escribir en esta carpeta (o parate en otra, por ejemplo Documentos). Si "
               f"quedó la carpeta {nombre} a medias, borrala")
        return 1
    del clave
    mate = entre_comillas_simples(os.path.abspath(__file__))
    lanzador = como_se_llama()
    lanzador = lanzador if lanzador == "mate" else f"{lanzador.split()[0]} {mate}"
    comprador = entre_comillas_simples(os.path.join(base, "comprador"))
    proveedor = entre_comillas_simples(os.path.join(base, "proveedor"))
    renglones = (
        f"Listo. Armé el ensayo de dos negocios en {para_pegar(base)}:",
        "  comprador    el negocio que compra: comprador.mate y su copia de trato.mate",
        "  proveedor    el negocio que vende: proveedor.mate y su copia de trato.mate",
        "  compartida   la carpeta que comparten (con un socio de verdad: una de OneDrive,",
        "               de Google Drive, de red o un pendrive)",
        "Los dos ya tienen cargada una clave DE ENSAYO (no se muestra; cada corrida lo avisa).",
        "",
        "Los pasos que siguen (cada comando se puede copiar tal cual en PowerShell):",
        "  1. Comprobar que quedó todo bien:",
        f"       cd {comprador}",
        f"       {lanzador} probar comprador.mate",
        f"       cd {proveedor}",
        f"       {lanzador} probar proveedor.mate",
        "  2. El comprador manda el pedido (queda firmado en la carpeta compartida):",
        f"       cd {comprador}",
        f"       {lanzador} correr comprador.mate",
        "  3. El proveedor lo recibe. Mate muestra el pedido y pregunta \"¿Lo entrego?\":",
        "     contestá si. Ventas cotiza y la cotización sale para el comprador.",
        f"       cd {proveedor}",
        f"       {lanzador} correr proveedor.mate",
        "  4. Al comprador le llega la cotización: contestá si. Queda anotada.",
        f"       cd {comprador}",
        f"       {lanzador} correr comprador.mate",
        "  5. El comprador corre de nuevo: ahora el programa pregunta \"¿Confirmás...?\".",
        "     Contestá si, y sale la confirmación.",
        f"       {lanzador} correr comprador.mate",
        "  6. Al proveedor le llega la confirmación: contestá si. Recién ahí descuenta",
        "     stock, y avisa.",
        f"       cd {proveedor}",
        f"       {lanzador} correr proveedor.mate",
        "  7. Al comprador le llega el aviso: contestá si. Pedido confirmado.",
        f"       cd {comprador}",
        f"       {lanzador} correr comprador.mate",
        "  En cualquier momento, para ver qué espera y qué salió (sin tocar nada):",
        f"       {lanzador} buzon comprador.mate",
        "",
        "Nada de otro negocio llega a un agente sin tu si, mensaje por mensaje: con no se",
        "rechaza (y tu socio se entera), y con Enter queda esperando para otra corrida.",
        "Los mensajes viajan firmados pero NO cifrados: quien ve la carpeta compartida los lee.",
        "",
        "PARA TRABAJAR CON UN SOCIO DE VERDAD esta carpeta no se le manda a nadie (adentro",
        "está la clave de ensayo). Cada negocio se queda con SU carpeta (comprador o",
        "proveedor) en SU máquina, eligen una carpeta compartida de verdad y generan una",
        "clave nueva. Uno de los dos, parado en su carpeta:",
        f"       {lanzador} socio renovar comprador.mate Proveedor --carpeta='C:\\ruta\\de\\la\\compartida'",
        "y el otro, en la suya, con la invitación que le llevaron en un pendrive:",
        f"       {lanzador} socio aceptar proveedor.mate Cliente --carpeta='C:\\ruta\\de\\la\\compartida'",
        "Entre una orden y la otra conviene que ninguno corra su programa.",
        "OJO: las carpetas se acuerdan del ensayo (el pedido A-17 ya figura hecho y el stock",
        "ya está descontado), así que la primera corrida de verdad no mandaría nada. Antes,",
        "cada uno cambia en su programa los datos de muestra por los suyos (el pedido A-17",
        "está en el último renglón de comprador.mate) y corre UNA vez con --olvidar, que",
        "arranca con la memoria limpia:",
        f"       {lanzador} correr comprador.mate --olvidar",
        "",
        "QUÉ SE LE PASA AL OTRO NEGOCIO para que arranque en su PC (no llevan nada secreto:",
        "pueden ir en un pendrive o por mail):",
        "    - su programa y el trato: si vos sos el comprador, a tu proveedor le pasás",
        "      proveedor.mate y trato.mate (los dos archivos .mate de la carpeta proveedor);",
        "      si sos el proveedor, comprador.mate y trato.mate (de la carpeta comprador)",
        "    - Mate, si todavía no lo tiene: la carpeta 'mate' entera",
        "  Los pone en una carpeta suya, en su PC, y ahí carga la clave con 'socio aceptar'.",
        "QUÉ NO SE LE PASA NUNCA, ni a tu socio ni a nadie:",
        "    - comprador.socios.json y proveedor.socios.json: ahí está la clave. Quien los",
        "      tenga puede firmar mensajes como ustedes. Cada PC arma el suyo con 'socio'.",
        "    - la memoria de cada programa: los .memoria.json, los .bitacora.txt y las",
        "      carpetas .buzon. Tienen tus pedidos y tu stock, y la cuenta de los mensajes:",
        "      con una memoria copiada, los dos programas se desordenan.",
        "    - la invitación (invitacion-mate.txt) va SOLO en un pendrive o en mano, nunca",
        "      por mail ni en la carpeta compartida, y Mate la borra cuando se carga.",
        "  En la carpeta compartida no se copia nada a mano: ahí escribe y borra Mate.",
        "Si después la carpeta compartida cambia de lugar (otra letra del pendrive), no hace",
        "falta cambiar la clave:",
        f"       {lanzador} socio carpeta comprador.mate Proveedor --carpeta='F:\\Compartida'",
        "(el manual lo cuenta paso a paso, en \"Dos negocios que se hablan (los socios)\")")
    for renglon in renglones:
        mostrar(renglon)
    return 0


def renglones_de_socios(ruta, buzon):
    """Para la orden 'buzon': lo que hay con cada socio del programa (0.8). Solo mira: no
    trae, no entrega ni cambia nada. Nunca muestra la clave: solo su número de control."""
    try:
        declarados = socios_declarados(analizar(leer_fuente(ruta), ruta))
    except (OSError, ErrorMate, RecursionError):
        return []
    if not declarados:
        return []
    fichas, problema = leer_socios(ruta)
    estados = leer_correo_de_memoria(archivo_de(ruta, "memoria.json"))["socios"]
    renglones = [f"  {problema}"] if problema else []
    carpeta_de_pendientes = os.path.join(buzon.carpeta, "pendientes")
    try:
        en_pendientes = sorted(os.listdir(carpeta_de_pendientes)) \
            if es_carpeta_de_verdad(carpeta_de_pendientes) else []
    except OSError:
        en_pendientes = []
    orden = orden_para_esta_carpeta()
    for socio in declarados:
        ficha, est = fichas.get(socio), estados.get(socio) or {}
        en_espera = len(est.get("en_espera") or [])
        if ficha is None:
            renglones.append(
                f"  Socio {socio}: sin clave cargada (no se manda ni se recibe nada)."
                + (f" Anotados sin salir: {en_espera}." if en_espera else "")
                + f" Para cargarla:  {orden} socio invitar {para_pegar(buzon.archivo)} "
                f"{socio}   o   {orden} socio aceptar {para_pegar(buzon.archivo)} {socio}")
            continue
        huella = huella_de_clave(ficha["clave"])
        al_dia = est.get("huella") == huella
        renglones.append(f"  Socio {socio} (control {control_de_socio(ficha['clave'])}"
                         + (", clave de ENSAYO" if ficha.get("ensayo") else "") + "):")
        se_ve = es_carpeta_real(ficha["carpeta"])
        renglones.append(f"    Carpeta compartida: {ficha['carpeta']} "
                         f"({'se ve' if se_ve else 'NO se ve ahora'}).")
        if not al_dia and ficha["estrenado"]:
            renglones.append(
                "    OJO: se perdió la cuenta de los mensajes con este socio (la memoria se "
                "borró o es una copia vieja): no se manda ni se entrega nada hasta renovar "
                f"la clave:  {orden} socio renovar {para_pegar(buzon.archivo)} {socio}")
        elif not al_dia:
            renglones.append("    Todavía no se usó: la cuenta arranca la primera vez que "
                             "corra el programa.")
        por_salir = len(est.get("por_salir") or []) if al_dia else 0
        renglones.append(
            f"    Por salir: {cuantos_mensajes(por_salir + en_espera) if por_salir + en_espera else 'ninguno'}"
            + (f" (el último que mandé fue el número {est['enviado']})."
               if al_dia and est.get("enviado") else "."))
        traidos = set(est.get("traidos") or []) if al_dia else set()
        esperan = []
        for nombre in en_pendientes:
            forma = _PENDIENTE_DE_SOCIO.fullmatch(nombre)
            if forma and forma.group(1) == huella and int(forma.group(2)) in traidos:
                esperan.append((int(forma.group(2)), nombre))
        renglones.append(
            f"    Esperan tu si: {cuantos_mensajes(len(esperan)) if esperan else 'ninguno'}"
            + (f". Se contestan al correr {buzon.archivo}:" if esperan else "."))
        for numero, nombre in esperan[:10]:
            tipo = "(no se puede leer)"
            try:
                with abrir_sin_seguir(os.path.join(carpeta_de_pendientes, nombre)) as f:
                    datos = json_de_sobre(f.read(MAX_SOBRE + 1))[0]
                tipo = texto_ajeno(datos["mensaje"]["tipo"], 60)
                if datos.get("clase") == "falla":
                    tipo = f"aviso de que no atendió {tipo}"
            except (OSError, ValueError, RecursionError, KeyError, TypeError):
                pass
            renglones.append(f"      - el número {numero}: {tipo}")
        if len(esperan) > 10:
            renglones.append(f"      ... y {len(esperan) - 10} más")
        if se_ve:
            entrada = os.path.join(ficha["carpeta"], "de-b" if ficha["lado"] == "A" else "de-a")
            sin_traer = 0
            try:
                with os.scandir(entrada) as hay:
                    for n, e in enumerate(hay):
                        if n >= MAX_MIRADOS_POR_CORRIDA:
                            break
                        sin_traer += e.name.lower().endswith(".json")
            except OSError:
                pass
            if sin_traer:
                renglones.append(
                    f"    En la carpeta compartida: {sin_traer} "
                    f"{'archivo' if sin_traer == 1 else 'archivos'} de {socio} sin traer "
                    f"(se {'mira' if sin_traer == 1 else 'miran'} la próxima vez que corra "
                    f"{buzon.archivo}).")
        huecos = huecos_de_socio(est) if al_dia else []
        if huecos:
            renglones.append(
                f"    Faltan números de {socio}: {', '.join(huecos)} (un mensaje que "
                "todavía no llegó, o que se perdió o alguien borró en el camino).")
    return renglones


def orden_buzon(args, avisar, mostrar=print):
    """La orden 'buzon programa.mate': cuenta qué hay en el buzón de ese programa (los
    mensajes que esperan y de quién, los que tiene por salir y los rechazados, con su
    motivo). Solo mira: no atiende, no crea ni cambia ningún archivo."""
    if len(args) != 1:
        avisar("'buzon' lleva el programa, por ejemplo: buzon deposito.mate (muestra los "
               "mensajes de otros programas que esperan, los que están por salir y los que "
               "no se pudieron entregar)")
        return 2
    ruta, problema = _ubicar(args[0])
    if problema:
        avisar(problema)
        return 2
    if not ruta.lower().endswith((".mate", ".mate.txt")):
        avisar(f"'buzon' lleva un programa de Mate (un archivo .mate), y "
               f"'{os.path.basename(ruta)}' no lo es. Por ejemplo: buzon deposito.mate")
        return 2
    buzon = Buzon(ruta)
    carpeta = os.path.basename(buzon.carpeta)
    mostrar(f"Buzón de {buzon.archivo} (la carpeta {carpeta}):")
    if os.path.lexists(buzon.carpeta) and not es_carpeta_de_verdad(buzon.carpeta):
        avisar(f"{carpeta} existe y no es una carpeta: ahí va el buzón de {buzon.archivo}. "
               "Borralo o cambiale el nombre")
        return 1
    anotado = leer_buzon_de_memoria(archivo_de(ruta, "memoria.json"))[0]
    de_quien, raros, repetidos, sin_mirar = buzon.contar(anotado["recibidos"])
    esperan = sum(de_quien.values()) + raros + sin_mirar
    if esperan:
        detalle = [f"{n} de {origen}" for origen, n in de_quien.items()] \
            + ([f"{raros} que no se entienden"] if raros else [])
        mostrar(f"  Esperan: {cuantos_mensajes(esperan)}"
                + (f" ({', '.join(detalle)})" if detalle else "")
                + f". Se atienden la próxima vez que corra {buzon.archivo}.")
    else:
        mostrar("  Esperan: ninguno.")
    if repetidos:  # (no cuentan como que esperan: no se van a entregar otra vez)
        mostrar(f"  Ya atendidos o repetidos: {repetidos} "
                f"({'sigue' if repetidos == 1 else 'siguen'} en la carpeta; se "
                f"{'borra' if repetidos == 1 else 'borran'} sin entregar la próxima vez que "
                f"corra {buzon.archivo}).")
    intrusos = buzon.intrusos()
    if intrusos:
        mostrar(f"  No son mensajes: {len(intrusos)} (una carpeta o un acceso directo con "
                f"nombre terminado en .json: {', '.join(intrusos[:5])}"
                + (", ..." if len(intrusos) > 5 else "")
                + "). Mate no los atiende ni los borra: sacalos a mano.")
    por_salir, para_quien = anotado["por_salir"], {}
    for pendiente in por_salir:
        destino = buzon.visible(pendiente["sobre"]["para"]["programa"])
        para_quien[destino] = para_quien.get(destino, 0) + 1
    if por_salir:
        mostrar(f"  Por salir: {cuantos_mensajes(len(por_salir))} ("
                + ", ".join(f"{n} para {destino}" for destino, n in para_quien.items())
                + f"). Salen la próxima vez que corra {buzon.archivo}.")
    else:
        mostrar("  Por salir: ninguno.")
    for renglon in renglones_de_socios(ruta, buzon):
        mostrar(renglon)
    rechazados = os.path.join(buzon.carpeta, "rechazados")
    try:
        nombres = sorted(n for n in os.listdir(rechazados) if n.lower().endswith(".json"))
    except OSError:
        nombres = []
    if not nombres:
        mostrar("  Rechazados: ninguno.")
        return 0
    de_socios = sum(1 for n in nombres if n.lower().startswith("socio-"))
    consejo = "para intentar uno de nuevo, movelo a la carpeta de arriba"
    if de_socios == len(nombres):
        consejo = ("son de otro negocio y no se reintentan a mano: si alguno hacía falta, "
                   "pedile a tu socio que lo mande de nuevo")
    elif de_socios:
        consejo += ("; los que empiezan con socio- son de otro negocio y no se reintentan a "
                    "mano: pedile a tu socio que los mande de nuevo")
    mostrar(f"  Rechazados: {len(nombres)} (están en {buzon.donde_van_los_rechazados()}; "
            f"{consejo})")
    for nombre in nombres[:20]:
        motivo = "(sin motivo anotado)"
        try:
            for renglon in leer_fuente(os.path.join(
                    rechazados, nombre[:-len(".json")] + ".motivo.txt")).splitlines():
                if renglon.startswith("Motivo: "):
                    motivo = renglon[len("Motivo: "):]
        except (OSError, ErrorMate):
            pass
        mostrar(f"    - {nombre}: {en_un_renglon(motivo, 300)}")
    if len(nombres) > 20:
        mostrar(f"    ... y {len(nombres) - 20} más")
    return 0


def probar_varios(pedidos, opciones, avisar):
    """'probar' con varios archivos o con una carpeta: corre las pruebas de cada uno y
    da un total general."""
    archivos = []
    for pedido in pedidos:
        if not os.path.isdir(pedido):
            archivos.append(pedido)
            continue
        try:
            adentro = sorted(a for a in os.listdir(pedido) if a.lower().endswith(".mate"))
        except OSError:
            avisar(f"no pude mirar adentro de la carpeta '{pedido}'")
            return 2
        if not adentro:
            avisar(f"en la carpeta '{pedido}' no hay ningún archivo .mate")
            return 2
        archivos += [os.path.join(pedido, a) for a in adentro]
    # Con --traza=archivo la conversación es una sola para todos: si iría a parar a un
    # archivo de alguno de ellos (aunque se llame distinto), no se prueba ninguno.
    destinos = [o[len("--traza="):].strip('"') for o in opciones
                if o.lower().startswith("--traza=")]
    for archivo in archivos if destinos and destinos[-1] else ():
        ubicado, problema = _ubicar(archivo)
        problema = not problema and traza_no_va_ahi(destinos[-1], ubicado)
        if problema:
            avisar(problema)
            return 2
    pasaron = total = 0
    con_problemas = []
    guardadas = []  # con --traza=archivo: las conversaciones ya guardadas (van una tras otra)
    for archivo in archivos:
        print(f"{archivo}:")
        sys.stdout.flush()
        donde = {"ruta": None, "interprete": None, "varios": True, "guardadas": guardadas}
        codigo = _main(["probar", archivo] + opciones, donde)
        sys.stderr.flush()
        bien, cuantas = donde.get("pruebas", (0, 0))
        pasaron, total = pasaron + bien, total + cuantas
        if codigo:
            con_problemas.append(archivo)
        print()
    print(f"En total: {pasaron} de {total} pruebas pasaron, en {len(archivos)} archivos")
    if con_problemas:
        print("Con problemas: " + ", ".join(con_problemas))
    return 1 if con_problemas else 0


# ─────────────── Lo que el lenguaje aprende de quien lo usa (0.4) ───────────────
# Cada error que Mate le muestra a la persona deja un renglón en errores_de_uso.txt, al
# lado de mate.py, para que después se pueda ver qué mensajes no alcanzan y mejorar Mate.
# No guarda programas, tapa los datos de la persona y no sale nunca de la computadora.
# Solo anota cuando Mate se usa desde la línea de comandos (como módulo, o en las pruebas,
# no), nunca con la orden 'probar', y se apaga con MATE_SIN_REGISTRO=1 o --sin-registro.

ORDENES_SABIDAS = ORDENES + ORDENES_DE_MEMORIA + ("ayuda", "guia", "consola", "informe",
                                                  "curso", "nuevo", "ensayar", "buzon",
                                                  "socio")
_FECHA_DE_REGISTRO = "%d/%m/%Y %H:%M"
_LARGO_A_TAPAR = 800
# Cómo es una opción ('--traza', '-h', '--borrar=2'). Lo que empieza con guion y no tiene
# esa forma ("-10% a Juan") es algo que escribió la persona: una lección, casi siempre.
_FORMA_DE_OPCION = re.compile(r"--?[A-Za-zÀ-ÿ?][\w\-]*(=\S*)?")
# Al final del registro: después del último error hubo una corrida que anduvo bien, así
# que el próximo error, aunque sea el mismo, no viene "seguido".
_CORTE_DE_RACHA = "# (después de esto hubo una corrida que anduvo bien)"
_TEXTO_ENTRE_COMILLAS = re.compile(
    r'"""[\s\S]*?"""|"(?:\\.|[^"\\\n])*"|«[^»\n]*»|“[^”\n]*”')
# Una ruta puede traer espacios ("C:\Users\Juan Perez\Desktop"): se tapa hasta donde
# termina la frase (mejor tapar de más que dejar medio apellido a la vista).
_FIN_DE_RUTA = r"""[^\n"'|*?()]*?(?=$|\n|["'|*?()]|[,;:] |\.\s|\.$)"""
_RUTA_WIN_A_TAPAR = re.compile(r"(?:(?<![A-Za-z])[A-Za-z]:|\\)[\\/]" + _FIN_DE_RUTA, re.M)
_RUTA_LINUX_A_TAPAR = re.compile(r"(?<![\w<./])~?/[\w.\-<>]+/" + _FIN_DE_RUTA, re.M)
_NOMBRE_DE_ARCHIVO = re.compile(
    r"(?:[\w.\-<>]+[\\/])*[\w\-<>][\w.\-<>]*\.(?:mate|txt|json|py|bat|csv|md|tmp|log|ps1)\b",
    re.I)


def ruta_del_registro():
    """El archivo del registro de errores de uso: siempre al lado de mate.py."""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), NOMBRE_DEL_REGISTRO)


def registro_apagado():
    """¿La persona pidió que no se anote nada? (la variable MATE_SIN_REGISTRO)"""
    return os.environ.get("MATE_SIN_REGISTRO", "").strip().lower() not in ("", "0", "no")


def donde_se_registra(registro, argv):
    """En qué archivo se anotan los errores de esta corrida, o None si no se anotan.
    registro: None (Mate usado como módulo: en ningún lado), True (la línea de comandos:
    al lado de mate.py, salvo dentro de una corrida de pytest) o la ruta de un archivo."""
    if registro is None or registro is False or registro_apagado():
        return None
    if any(a.lower() == "--sin-registro" for a in argv):
        return None
    if registro is True:
        return None if "PYTEST_CURRENT_TEST" in os.environ else ruta_del_registro()
    return os.fspath(registro)


def tapar_datos(texto, propios=()):
    """El mensaje de un error sin los datos de la persona: la clave de la IA y cualquier
    cosa con forma de clave, su nombre de usuario, los textos entre comillas, los nombres
    que eligió, las rutas, los nombres de archivos, los correos y los números largos
    quedan reemplazados por marcas como <texto> o <archivo>. Todo en un renglón.
    propios: lo que la persona escribió en la orden (archivos, nombres): se tapa
    dondequiera que aparezca."""
    texto = tapar_clave(str(texto),
                        os.environ.get("ANTHROPIC_API_KEY", "").strip().strip("\"'"))
    texto = re.sub(r"\bsk-[\w\-]{6,}|(?<![\w\-])(?=[\w\-]*\d)(?=[\w\-]*[A-Za-z])[\w\-]{24,}",
                   "<clave>", texto)
    # Igual se guardan 300 letras: de un mensaje larguísimo (trae un texto entero adentro)
    # se mira el principio y el final, para que anotar un error nunca tarde.
    cortado = len(texto) > 2 * _LARGO_A_TAPAR
    if cortado:
        texto = texto[:_LARGO_A_TAPAR] + texto[-_LARGO_A_TAPAR:]
    texto = re.sub(r"https?://\S+", "<dirección>", texto)
    texto = re.sub(r"[\w.+\-]+@[\w\-]+(?:\.[\w\-]+)+", "<correo>", texto)
    usuarios = {os.environ.get(v, "") for v in ("USERNAME", "USER", "LOGNAME")}
    usuarios.add(os.path.basename(os.path.expanduser("~").rstrip("\\/")))
    for usuario in sorted(usuarios, key=len, reverse=True):
        if len(usuario) >= 3 and usuario.lower() not in ("mate", "user", "users", "home"):
            texto = re.sub(re.escape(usuario), "<usuario>", texto, flags=re.I)
    sabidas = PALABRAS | set(FUNCIONES) | TIPOS_BASE | set(ORDENES_SABIDAS) | {
        "recordado", "salir", "llamado", "mate", "mate.py", "mate.bat", "python", "todas"}
    suyos = set()
    for propio in propios:
        nombre = re.split(r"[\\/]", propio.rstrip("\\/"))[-1]
        suyos |= {propio, nombre, re.sub(r"(?i)\.mate(\.txt)?$", "", nombre)}
    for suyo in sorted(suyos, key=len, reverse=True):
        if len(suyo) >= 3 and sin_tildes(suyo) not in sabidas:
            texto = re.sub(re.escape(suyo), "<dato>", texto, flags=re.I)
    hecha = "\x00"  # una comilla que ya se miró
    texto = _TEXTO_ENTRE_COMILLAS.sub(f"{hecha}<texto>{hecha}", texto)
    if cortado and '"' in texto:  # al cortar, una comilla quedó sin su par: se tapa de más
        primera, ultima = texto.find('"'), texto.rfind('"')
        texto = texto[:primera] + '"<texto>"' + (texto[ultima + 1:] if primera < ultima else "")
    texto = texto.replace(hecha, '"')

    def nombre(m):
        partes = m.group(1).lower().replace("(", " ").replace(")", " ").split()
        sabido = partes and all(p in sabidas for p in partes)
        return (m.group(0) if sabido else "'<nombre>'").replace("'", hecha)

    def archivo(m):
        propio = re.split(r"[\\/]", m.group(0))[-1].lower() in ("mate.py", "mate.bat")
        return m.group(0) if propio and "<" not in m.group(0) else "<archivo>"

    def opcion(m):
        sabida = m.group(1).lower() in OPCIONES + ("--borrar", "-h")
        return (m.group(1) if sabida else "--<opción>") + ("=<valor>" if m.group(2) else "")

    # Lo que va entre comillas simples puede traer un apóstrofo adentro ('O'Higgins 4500',
    # 'D'Angelo'): la comilla que cierra es la que no tiene una letra pegada después.
    texto = re.sub(r"(?<![\w'])'((?:[^'\n]|'(?=\w))*)'(?!\w)", nombre, texto)
    if "'" in texto:
        # Quedó una comilla suelta: no se sabe dónde termina el dato, así que se tapa
        # todo, de la primera comilla a la última (mejor de más que de menos).
        primera = min(i for i in (texto.find("'"), texto.find(hecha)) if i >= 0)
        ultima = max(texto.rfind("'"), texto.rfind(hecha))
        if primera < ultima:
            texto = texto[:primera] + "'<texto>'" + texto[ultima + 1:]
        elif cortado:
            texto = texto[:primera] + "'<texto>'"
        else:
            texto = re.sub(r"\S*'\S*", "<texto>", texto)
    texto = texto.replace(hecha, "'")
    # (las listas de nombres del programa: campos de un mapa, agentes)
    texto = re.sub(r"\((tiene|son|hay): [^)]*\)", r"(\1: <nombres>)", texto)
    texto = re.sub(r"(Sus agentes son|Los agentes de ese programa son): .*", r"\1: <nombres>",
                   texto)
    texto = _NOMBRE_DE_ARCHIVO.sub(archivo, texto)
    texto = _RUTA_WIN_A_TAPAR.sub("<ruta>", texto)
    texto = _RUTA_LINUX_A_TAPAR.sub("<ruta>", texto)
    texto = re.sub(r"(?<![\w\-<])(--?[A-Za-zÀ-ÿ][\w\-]*)(=[^\s,?]*)?", opcion, texto)
    texto = re.sub(r"\d{3,}(?:[.,]\d+)*", "<número>", texto)
    return en_un_renglon(texto, 300).replace("|", "/")


def categoria_de(etapa, tapado):
    """El nombre estable de un error: la etapa y el arranque de su mensaje ya tapado,
    hasta el primer punto o los dos puntos, sin números. No lleva datos de la persona."""
    molde = re.sub(r"<número>|\d+", "N", tapado)
    corte = re.compile(r"\. |: | \(|,? ¿|; ").search(molde, 12)
    if corte:
        molde = molde[:corte.start()]
    return f"{etapa}: {en_un_renglon(molde, 80)}"


def entradas_del_registro(ruta):
    """Lo que dice el registro: (entradas, renglones tal cual están, cuántos no se
    entienden). Cada entrada es un mapa con fecha, version, orden, categoria, sugerencia,
    seguidas y mensaje. Si el archivo no existe, nada; si no se puede leer, un ErrorMate."""
    try:
        texto = leer_renglones(ruta)
    except FileNotFoundError:
        return [], [], 0
    except (OSError, ErrorMate):
        raise ErrorMate(f"no pude leer el registro de errores de uso '{ruta}': fijate que "
                        "no esté abierto en otro programa")
    renglones = [r.rstrip() for r in texto
                 if r.strip() and not r.lstrip().startswith("#")]
    entradas, raros = [], 0
    for renglon in renglones:
        partes = [parte.strip() for parte in renglon.split(" | ", 6)]
        seguidas = re.fullmatch(r"(\d{1,6}) (?:vez|veces seguidas)", partes[5]) \
            if len(partes) == 7 else None
        try:
            fecha = datetime.datetime.strptime(partes[0], _FECHA_DE_REGISTRO)
        except ValueError:
            fecha = None
        if not seguidas or fecha is None or partes[4] not in ("con sugerencia",
                                                              "sin sugerencia"):
            raros += 1
            continue
        entradas.append({
            "fecha": fecha, "version": partes[1], "orden": partes[2], "categoria": partes[3],
            "sugerencia": partes[4] == "con sugerencia", "seguidas": int(seguidas.group(1)),
            "mensaje": partes[6]})
    return entradas, renglones, raros


def anotar_error_de_uso(ruta, orden, etapa, mensaje, categoria=None, sugerencia=None,
                        familia=None, otros=0, ahora=None, propios=()):
    """Suma un renglón al registro de errores de uso y deja los últimos MAX_REGISTRO.
    Si el mismo error ya era el último anotado, hace poco y con la misma orden, cuenta
    cuántas veces seguidas va (la señal de que el mensaje no alcanzó). Nunca molesta: si
    no se puede escribir, o el archivo no se entiende, no se anota y listo."""
    if not ruta:
        return
    try:
        mensaje = str(mensaje).partition("\ncómo se llegó: ")[0]
        en_agente = re.match(r"(?s).+? (?:al recibir \S+|en 'al fallar'): ", mensaje)
        if en_agente and etapa == "al correr":
            etapa, mensaje = "al correr, en un agente", mensaje[en_agente.end():]
        if sugerencia is None:
            sugerencia = "¿quisiste decir" in mensaje.lower()
        if familia == "fallar":  # eso lo escribió la persona en su programa: no se guarda
            categoria = categoria or f"{etapa}: el programa cortó con 'fallar'"
            mensaje = "<lo que el programa dijo con 'fallar'>"
        elif familia == "asegurar":
            categoria = categoria or f"{etapa}: no se cumplió un 'asegurar'"
            mensaje = "<un 'asegurar' del programa que no se cumplió>"
        elif familia == "python":  # lo que diga un archivo de Python de la persona, tampoco
            categoria = categoria or (f"{etapa}: falló algo de un archivo traído con "
                                      "'usar python'")
            mensaje = "<lo que pasó en el archivo de Python del programa>"
        else:
            mensaje = tapar_datos(mensaje, propios)
        categoria = en_un_renglon(categoria or categoria_de(etapa, mensaje), 110)
        if otros:
            mensaje += f" (y {otros} error(es) más en la misma corrida)"
        ahora = ahora or datetime.datetime.now()
        entradas, renglones, _ = entradas_del_registro(ruta)
        seguidas = 1
        if entradas and not racha_cortada(ruta) and renglones[-1].startswith(
                entradas[-1]["fecha"].strftime(_FECHA_DE_REGISTRO)):
            ultima = entradas[-1]  # (solo si el último renglón del archivo se entiende)
            minutos = (ahora - ultima["fecha"]).total_seconds() / 60
            if (ultima["categoria"], ultima["orden"].split()[:1]) == (
                    categoria, orden.split()[:1]) and 0 <= minutos <= MINUTOS_SEGUIDO:
                seguidas = ultima["seguidas"] + 1
        renglones.append(" | ".join([
            ahora.strftime(_FECHA_DE_REGISTRO), f"Mate {VERSION}",
            en_un_renglon(orden, 80).replace("|", "/"), categoria.replace("|", "/"),
            "con sugerencia" if sugerencia else "sin sugerencia",
            "1 vez" if seguidas == 1 else f"{seguidas} veces seguidas", mensaje]))
        escribir_entero(ruta, "\n".join([
            "# Registro de errores de uso de Mate: cada error que Mate te mostró, el más "
            "nuevo abajo.",
            "# Sirve para mejorar Mate. Queda solo en esta computadora: Mate no lo manda a "
            "ningún lado.",
            "# No guarda tus programas, y tapa tus datos con marcas como <texto>, <nombre>, "
            "<archivo> o <ruta>.",
            "# Cada renglón:  fecha | versión | orden | qué error fue | si traía sugerencia "
            "| cuántas veces seguidas | el mensaje, tapado",
            f"# Guarda los últimos {MAX_REGISTRO}. Para verlo resumido:  {como_se_llama()} "
            "informe",
            f"# Para borrarlo:  {como_se_llama()} informe --borrar   (o borrá este archivo: "
            "no pasa nada)",
            "# Para que Mate no anote más: la opción --sin-registro, o la variable "
            "MATE_SIN_REGISTRO con un 1.", ""] + renglones[-MAX_REGISTRO:]) + "\n")
    except Exception:  # (carpeta de solo lectura, archivo abierto en otro programa...)
        pass


def racha_cortada(ruta):
    """¿Lo último que dice el registro es que después hubo una corrida que anduvo bien?"""
    try:
        escritos = [r.strip() for r in leer_renglones(ruta) if r.strip()]
    except (OSError, ErrorMate):
        return False
    return bool(escritos) and escritos[-1] == _CORTE_DE_RACHA


def cortar_racha(ruta, ahora=None):
    """Al terminar bien un 'correr' o un 'verificar': si el último error anotado es de
    hace un rato nomás, deja dicho que después hubo una corrida que anduvo bien, para que
    el próximo error no cuente como 'seguido'. Solo toca un registro que ya existe."""
    try:
        if not ruta or not os.path.isfile(ruta) or racha_cortada(ruta):
            return
        entradas, _, _ = entradas_del_registro(ruta)
        minutos = ((ahora or datetime.datetime.now()) - entradas[-1]["fecha"]
                   ).total_seconds() / 60 if entradas else None
        if minutos is None or not 0 <= minutos <= MINUTOS_SEGUIDO:
            return
        with open(ruta, "rb") as f:
            termina_bien = f.read()[-1:] in (b"\n", b"")
        with open(ruta, "a", encoding="utf-8") as f:
            f.write(("" if termina_bien else "\n") + _CORTE_DE_RACHA + "\n")
    except Exception:  # el registro nunca molesta
        pass


def orden_usada(argv):
    """La orden y las opciones de esta corrida, sin archivos ni nada que haya escrito la
    persona: 'correr --traza'."""
    orden = "(sin orden)"
    for a in argv:
        if not a.startswith("-"):
            bajo = sin_tildes(a.lower())
            orden = bajo if bajo in ORDENES_SABIDAS else (
                "correr" if bajo.endswith((".mate", ".mate.txt")) else "(orden desconocida)")
            break
    nombres = {a.lower().split("=")[0] for a in argv if a.startswith("-")}
    return " ".join([orden] + sorted(nombres & set(OPCIONES + ("--borrar",))))


def anotar_corrida(argv, donde, codigo):
    """Al terminar una corrida que mostró un error: lo anota en el registro (el primero
    que vio la persona, y cuántos más hubo). Con 'probar' y sin errores, nada."""
    orden = orden_usada(argv)
    if donde.get("registro") and not codigo and orden.split()[0] in ("correr", "verificar"):
        cortar_racha(donde["registro"])
    if not donde.get("registro") or not codigo or orden.split()[0] in ("probar", "consola"):
        return
    errores = donde.get("errores") or [
        {"etapa": "al escribir la orden", "mensaje": texto, "categoria": categoria,
         "sugerencia": sugerencia} for texto, categoria, sugerencia in donde.get("avisado", [])]
    if not errores:
        return
    primero = errores[0]
    if primero["etapa"] == "al escribir la orden":
        errores = errores[:1]  # (los renglones que siguen son parte del mismo aviso)
    propios = [a for a in argv if not a.startswith("-")]
    propios += [a.partition("=")[2].strip('"') for a in argv if a.startswith("-")]
    propios += [a for a in argv if a.startswith("-") and not _FORMA_DE_OPCION.fullmatch(a)]
    anotar_error_de_uso(
        donde["registro"], orden, primero["etapa"], primero["mensaje"],
        categoria=primero.get("categoria"), sugerencia=primero.get("sugerencia"),
        familia=primero.get("familia"), otros=len(errores) - 1, propios=propios)


def comando_pegado(argv):
    """Si en PowerShell el comando se pegó dos (o más) veces seguidas en el mismo renglón
    ('correr mio.matepython mate\\mate.py correr mio.mate'), devuelve el comando escrito
    una sola vez. Si se pegaron dos comandos distintos, el último. Si no, None."""
    def entero(partes):
        return " ".join(para_pegar(a) for a in partes)

    junto = " ".join(argv)
    for k in range(1, len(argv)):
        cola = " ".join(argv[k:])
        if not cola.strip() or not junto.startswith(cola):
            continue  # (un "" suelto al final no es un comando pegado)
        resto = junto[len(cola):]
        for veces in (4, 3, 2, 1):  # el comando completo, repetido después del primero
            largo, sobra = divmod(len(resto), veces)
            comando = resto[:largo]
            lanzador = comando[:-len(cola) - 1]
            if (not sobra and resto == comando * veces and comando.endswith(" " + cola)
                    and lanzador.strip() == lanzador != ""
                    and re.search(r"mate|py", lanzador, re.I)):
                return f"{lanzador} {entero(argv[k:])}"
    for i, a in enumerate(argv[:-1]):
        lanzador = re.search(r"(?i)(?<=.)(python3?|py)(\.exe)?$", a)
        if lanzador and re.split(r"[\\/]", argv[i + 1])[-1].lower() == "mate.py":
            return f"{lanzador.group(0)} {entero(argv[i + 1:])}"
    return None


def lineas_de_informe(entradas, raros):
    """El informe de errores de uso, renglón por renglón."""
    def veces(n):
        return f"{n:>5} {'vez ' if n == 1 else 'veces'}"

    por_categoria = {}
    for e in entradas:
        ficha = por_categoria.setdefault(e["categoria"], {
            "veces": 0, "sugerencia": 0, "repetidas": 0, "racha": 1, "mensaje": ""})
        ficha["veces"] += 1
        ficha["sugerencia"] += e["sugerencia"]
        ficha["repetidas"] += e["seguidas"] > 1
        ficha["racha"] = max(ficha["racha"], e["seguidas"])
        ficha["mensaje"] = e["mensaje"]
    orden = sorted(por_categoria.items(), key=lambda par: -par[1]["veces"])
    versiones = sorted({e["version"] for e in entradas})
    total = len(entradas)
    lineas = [
        f"Hay {total} error(es) de uso anotado(s), del "
        f"{entradas[0]['fecha'].strftime(_FECHA_DE_REGISTRO)} al "
        f"{entradas[-1]['fecha'].strftime(_FECHA_DE_REGISTRO)} ({', '.join(versiones)}).",
        "",
        "Los más frecuentes:"]
    for categoria, ficha in orden[:10]:
        lineas.append(f"{veces(ficha['veces'])}  {categoria}")
        lineas.append(f"             el mensaje: {en_un_renglon(ficha['mensaje'], 200)}")
    if len(orden) > 10:
        lineas.append(f"             ... y {len(orden) - 10} error(es) distinto(s) más")
    lineas += ["", "Los que se repitieron seguido (la persona volvió a intentar y le salió "
                   "el mismo error: el mensaje no alcanzó):"]
    repetidos = sorted(((c, f) for c, f in orden if f["repetidas"]),
                       key=lambda par: (-par[1]["racha"], -par[1]["repetidas"]))
    for categoria, ficha in repetidos[:10]:
        lineas.append(f"  hasta {ficha['racha']} veces seguidas ({ficha['repetidas']} "
                      f"repetición(es) en total)  {categoria}")
    if not repetidos:
        lineas.append("  ninguno")
    con = sum(e["sugerencia"] for e in entradas)
    lineas += ["", f"Con sugerencia de Mate (un \"¿quisiste decir...?\" o el comando bien "
                   f"escrito): {con} de {total}."]
    sin = [(c, f) for c, f in orden if not f["sugerencia"]][:5]
    if sin:
        lineas.append("Los más frecuentes que no traían ninguna sugerencia:")
        lineas += [f"{veces(f['veces'])}  {c}" for c, f in sin]
    por_orden = {}
    for e in entradas:
        palabra = e["orden"].split(" --")[0] or "?"
        por_orden[palabra] = por_orden.get(palabra, 0) + 1
    lineas += ["", "Con qué orden pasaron: " + ", ".join(
        f"{o} {n}" for o, n in sorted(por_orden.items(), key=lambda par: -par[1]))]
    if raros:
        lineas += ["", f"({raros} renglón(es) del archivo no tienen la forma de siempre y "
                       "no los conté)"]
    return lineas


def orden_informe(args, opciones, borrar, ruta, avisar):
    """La orden 'informe': resume el registro de errores de uso, arma el texto para pedir
    mejoras (--para-mejorar) o borra el registro (--borrar)."""
    if args:
        avisar("'informe' va sola, o con --para-mejorar o --borrar, por ejemplo: informe "
               "--para-mejorar")
        return 2
    if borrar is not None and "--para-mejorar" in opciones:
        avisar("--para-mejorar y --borrar no van juntas, y no borré nada. Primero armá el "
               "texto (informe --para-mejorar) y, cuando ya lo tengas, borrá el registro "
               "(informe --borrar)")
        return 2
    if borrar is not None:
        if borrar.lower() not in ("", "todo", "todos"):
            avisar("con 'informe', --borrar va sola (borra todo el registro): informe "
                   "--borrar")
            return 2
        if not os.path.lexists(ruta):
            print("No hay registro de errores de uso para borrar.")
            return 0
        try:
            os.remove(ruta)
        except OSError:
            avisar(f"no pude borrar '{ruta}': fijate que no esté abierto en otro programa")
            return 1
        print(f"Borrado el registro de errores de uso ({ruta}). Empieza de nuevo solo.")
        return 0
    try:
        entradas, _, raros = entradas_del_registro(ruta)
    except ErrorMate as e:
        avisar(e.mensaje)
        return 2
    apagado = ("Ahora el registro está apagado (la variable MATE_SIN_REGISTRO): Mate no "
               "anota nada." if registro_apagado() else None)
    if not entradas:
        print("Todavía no hay errores de uso anotados"
              + (f" ({ruta} tiene {raros} renglón(es) que no entiendo: abrilo con el Bloc "
                 f"de notas, o borralo con:  {como_se_llama()} informe --borrar)." if raros
                 else "."))
        print("Mate anota solo, en esta computadora, cada error que te muestra (sin tus "
              "programas y con tus datos tapados), para que después se pueda ver qué "
              "mensajes no alcanzan. Nada de eso sale por internet.")
        print(apagado or f"El archivo va a ser {ruta}")
        return 0
    lineas = lineas_de_informe(entradas, raros)
    if "--para-mejorar" in opciones:
        print("\n".join([
            "(Copiá desde el renglón de abajo hasta el final y pegáselo a un asistente o a "
            "tu equipo de agentes.)",
            "",
            f"Uso Mate (versión {VERSION}): un lenguaje de programación chico, con palabras "
            "en español, cuyo intérprete es un solo archivo de Python sin dependencias "
            "(mate.py). Está pensado para gente que no programa, que usa Windows con "
            "PowerShell y el Bloc de notas, y para armar agentes que se mandan mensajes con "
            "contrato. Mate anota en mi computadora cada error que me muestra: qué error "
            "fue, con qué orden, si traía una sugerencia y si me volvió a salir enseguida. "
            "No guarda mis programas, y mis datos están tapados con marcas como <texto>, "
            "<nombre>, <archivo> o <ruta>. Este es el resumen:",
            ""] + lineas + [
            "",
            "Con estos datos te pido propuestas concretas para mejorar Mate:",
            "1. Para cada uno de los tres errores más frecuentes, y para cada uno de los "
            "que se repitieron seguido: ¿qué cambiarías para que la persona lo resuelva al "
            "primer intento, o para que ese error directamente no pueda pasar? Si es el "
            "mensaje, escribí el mensaje nuevo completo, en castellano rioplatense claro y "
            "sin palabras técnicas. Si es el lenguaje o la línea de comandos, decí "
            "exactamente qué cambia y mostrá un ejemplo de antes y después.",
            "2. ¿Cuál conviene arreglar primero y por qué?",
            "3. ¿Hay algún error de esta lista que en realidad sea un problema de la "
            "documentación o de los ejemplos y no del lenguaje?",
            "Reglas que no se negocian: Mate tiene que seguir siendo chico (un solo "
            "archivo, solo la biblioteca estándar de Python, palabras clave en español), "
            "los programas que hoy andan tienen que seguir dando el mismo resultado, y "
            "cada cambio lleva su prueba."]))
        return 0
    print("Informe de errores de uso de Mate")
    print("\n".join(lineas))
    print("")
    print(f"Está todo en {ruta} (se abre con el Bloc de notas; no sale de esta "
          "computadora).")
    print(f"Para pedirle mejoras a un asistente:  {como_se_llama()} informe --para-mejorar")
    print(f"Para borrarlo:  {como_se_llama()} informe --borrar")
    if apagado:
        print(apagado)
    return 0


def main(argv=None, registro=None):
    """registro: dónde se anotan los errores de uso. None (Mate usado como módulo, y en
    las pruebas): en ningún lado. True (la línea de comandos): en errores_de_uso.txt, al
    lado de mate.py. O la ruta de un archivo."""
    argv = list(sys.argv[1:] if argv is None else argv)
    donde = {"ruta": None, "interprete": None, "errores": [], "avisado": [],
             "registro": donde_se_registra(registro, argv),
             "informe": (ruta_del_registro() if registro is None or isinstance(registro, bool)
                         else os.fspath(registro))}
    codigo = _con_red(argv, donde)
    try:
        anotar_corrida(argv, donde, codigo)
    except Exception:  # el registro nunca le cambia el resultado a nadie
        pass
    return codigo


def _con_red(argv, donde):
    for flujo in (sys.stdout, sys.stderr, sys.stdin):
        try:  # que una consola vieja de Windows no rompa por un símbolo que no conoce
            flujo.reconfigure(errors="replace")
        except Exception:
            pass
    depurar = any(a.lower() == "--depurar" for a in argv)

    def lugar():
        linea = getattr(donde["interprete"], "linea_actual", None)
        if not linea:
            return None
        return f"{getattr(linea, 'archivo', None) or donde['ruta']}:{linea}"

    def avisar(texto):
        print(texto, file=sys.stderr)

    # Red de seguridad: pase lo que pase, nunca un error interno de Python en inglés.
    try:
        return _main(argv, donde)
    except BrokenPipeError:  # la salida iba a otro programa que dejó de leer (| more)
        try:
            os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        except Exception:
            pass
        return 1
    except CorteEnElTeclado:
        # Ctrl+C en un leer(): la charla se cortó a propósito. No es un error, y se dice
        # sin cartel de error; pero el código de salida es el de siempre para un corte
        # (130), así un .bat que lo mira sigue distinguiendo "cortado" de "terminó bien".
        sys.stdout.flush()
        avisar("")
        avisar(CORTE_EN_EL_TECLADO)
        return 130
    except KeyboardInterrupt:
        if lugar():
            avisar(f"{lugar()}: cortado con Ctrl+C mientras corría esta línea")
        else:
            avisar("cortaste el programa con Ctrl+C")
        avisar_pendientes(donde["interprete"], avisar)
        return 130
    except RecursionError:
        if depurar:
            raise
        antes = f"{donde['ruta']}: " if donde["ruta"] else ""
        avisar(f"{antes}error: el programa tiene demasiados niveles anidados "
               "(paréntesis, bloques o llamadas)")
        return 1
    except MemoryError:
        if depurar:
            raise
        avisar(f"{lugar() or donde['ruta'] or 'mate'}: error: {SIN_MEMORIA}")
        return 1
    except Exception as e:
        if depurar:
            raise
        avisar(f"error interno de Mate (no es culpa tuya): {type(e).__name__}: {e}")
        donde["errores"].insert(0, {
            "etapa": "por dentro de Mate", "mensaje": "error interno de Mate",
            "categoria": f"por dentro de Mate: error interno ({type(e).__name__})"})
        if lugar():
            avisar(f"pasó cerca de {lugar()}")
        avisar("corré de nuevo con --depurar para ver el detalle")
        avisar_pendientes(donde["interprete"], avisar)
        return 1


def _main(argv, donde):
    def avisar(texto, categoria=None, sugerencia=None, anotado=None):
        print(texto, file=sys.stderr)
        if not texto.startswith("aviso:"):  # (para el registro de errores de uso)
            donde.setdefault("avisado", []).append((anotado or texto, categoria, sugerencia))

    una_vez = comando_pegado(argv)
    if una_vez:
        avisar("parece que el comando se pegó dos veces en el mismo renglón. Escribilo una "
               f"sola vez:\n  {una_vez}", "al escribir la orden: comando pegado dos veces",
               True, "parece que el comando se pegó dos veces en el mismo renglón (y Mate "
               "mostró el comando bien escrito)")
        return 2
    if argv and sin_tildes(argv[0].lower()) == "socio" and not (
            len(argv) == 1 and (os.path.isfile("socio") or os.path.isfile("socio.mate"))):
        # (0.8; 'socio' sola, con un socio.mate en la carpeta, sigue corriendo ese programa.
        # Va antes que las opciones: las suyas, --carpeta, --invitacion y --dictar, son
        # solo de esta orden.)
        return orden_socio(argv[1:], avisar)
    alias = {"-h": "--ayuda", "--help": "--ayuda", "-?": "--ayuda", "/?": "--ayuda"}
    opciones, args, conversacion, respuestas, borrar = set(), [], None, None, None
    guardar_en = None  # guia --guardar=guia.txt: la salida va a ese archivo, no a la pantalla
    veces = None  # ensayar --veces=5: cuántas veces se repite cada caso
    for a in argv:
        corrige = bool(args) and sin_tildes(args[0].lower()) == "corregir"
        if a.lower() in alias:
            opciones.add(alias[a.lower()])
        elif a.lower().startswith("--borrar"):
            borrar = a[len("--borrar="):].strip('"')
            if a.lower() == "--borrar":
                borrar = ""  # sola va con 'informe': se revisa más abajo
            elif not a.lower().startswith("--borrar=") or not borrar:
                avisar("a --borrar le falta el número de la lección, por ejemplo: lecciones "
                       "mi_mostrador.mate Mostrador --borrar=2")
                return 2
        elif a.lower().startswith("--ia-simulada="):
            opciones.add("--ia-simulada")
            respuestas = a[len("--ia-simulada="):].strip('"')
            if not respuestas:
                avisar("a --ia-simulada= le falta el nombre del archivo de respuestas, por "
                       "ejemplo: --ia-simulada=respuestas.txt (o --ia-simulada sola)")
                return 2
        elif a.lower().startswith("--guardar"):
            guardar_en = a[len("--guardar="):].strip('"')
            if not a.lower().startswith("--guardar=") or not guardar_en:
                avisar("a --guardar le falta el nombre del archivo, por ejemplo: guia "
                       "--guardar=guia.txt")
                return 2
            if guardar_en.lower().rstrip(". ").endswith(NO_SE_PISAN) \
                    or es_archivo_de_clave(guardar_en):
                avisar(f"no guardo en '{guardar_en}' para no pisar un programa: elegí otro "
                       "nombre, por ejemplo --guardar=guia.txt")
                return 2
        elif a.lower().startswith("--veces"):
            valor = a[len("--veces="):].strip('"')
            if not a.lower().startswith("--veces=") or not (
                    valor.isascii() and valor.isdigit() and 1 <= int(valor) <= MAX_VECES):
                avisar("a --veces le falta decir cuántas veces se repite cada caso (un "
                       f"número del 1 al {MAX_VECES}), por ejemplo: ensayar mi_negocio.mate "
                       "mi_negocio_casos.txt --veces=5")
                return 2
            veces = int(valor)
        elif a.lower().startswith("--traza="):
            conversacion = a[len("--traza="):].strip('"')
            if not conversacion:
                avisar("a --traza= le falta el nombre del archivo, por ejemplo: "
                       "--traza=conversacion.txt")
                return 2
            if any(n.endswith(NO_SE_PISAN) for n in nombres_de_un_camino(conversacion)):
                avisar(f"no guardo la conversación en '{conversacion}' para no pisar un "
                       "programa: elegí otro nombre, por ejemplo --traza=conversacion.txt")
                return 2
            if es_archivo_de_clave(conversacion):
                avisar("no guardo la conversación en '"
                       + os.path.basename(conversacion.replace("\\", "/"))
                       + "': ese archivo guarda la clave de un socio. Elegí otro nombre, "
                       "por ejemplo --traza=conversacion.txt")
                return 2
            if traza_pisaria_la_memoria(conversacion):
                avisar(f"no guardo la conversación en '{conversacion}': ese archivo lo "
                       "lleva Mate (la memoria de los agentes, como el stock, la "
                       "bitácora o el buzón). Elegí otro nombre, por ejemplo --traza=conversacion.txt")
                return 2
        elif corrige and len(args) >= 3 and a.startswith("-") and (
                not _FORMA_DE_OPCION.fullmatch(a)):
            args.append(a)  # con 'corregir', la lección puede empezar con un guion: "-10% a..."
        elif a.startswith("-") and a != "-":
            if a.lower() not in OPCIONES:
                todas = OPCIONES + ("--veces", "--borrar", "--guardar")
                nombre, igual, valor = a.partition("=")
                parecidas = difflib.get_close_matches(nombre.lower(), todas, 1)
                con_valor = parecidas and parecidas[0] in ("--borrar", "--traza", "--ia-simulada",
                                                          "--guardar", "--veces")
                avisar(f"no conozco la opción {a}" + (
                    f", ¿quisiste decir {parecidas[0]}{igual + valor if con_valor else ''}?"
                    if parecidas else ". Las opciones son: " + ", ".join(todas))
                    + (". Si era parte de la lección, escribila entre comillas y sin el "
                       "guion adelante" if corrige and len(args) >= 3 else ""),
                    "al escribir la orden: opción que no existe")
                return 2
            opciones.add(a.lower())
        else:
            args.append(a)

    if borrar == "" and not (args and args[0].lower() == "informe"):
        avisar("a --borrar le falta el número de la lección, por ejemplo: lecciones "
               "mi_mostrador.mate Mostrador --borrar=2 (sola, --borrar va con 'informe')")
        return 2
    if "--version" in opciones:
        print(f"Mate {VERSION} (Python {sys.version_info[0]}.{sys.version_info[1]})")
        return 0
    if args and args[0].lower() == "ayuda" and len(args) >= 2 and not (
            len(args) == 2 and sin_tildes(args[1].lower()) in ORDENES + (
                "ayuda", "guia", "consola", "informe", "curso", "nuevo", "ensayar")
            + ORDENES_DE_MEMORIA[:2]):
        # 'ayuda si', 'ayuda largo', 'ayuda al fallar'
        return ayuda_de_palabra(" ".join(args[1:]), print, avisar)
    if "--ayuda" in opciones or (args and args[0].lower() == "ayuda"):
        print(texto_de_ayuda())
        return 0
    if not args:
        print(texto_de_ayuda())
        return 2
    if guardar_en is not None and not (args and sin_tildes(args[0].lower()) in (
            "guia", "informe")):
        avisar("--guardar va con 'guia' o con 'informe', por ejemplo: guia --guardar=guia.txt "
               "(deja el texto en ese archivo, listo para abrir con el Bloc de notas)")
        return 2
    if guardar_en is not None:
        # Con > de PowerShell el archivo queda con las tildes rotas: lo escribe Mate.
        import contextlib
        texto = io.StringIO()
        with contextlib.redirect_stdout(texto):
            if sin_tildes(args[0].lower()) == "guia":
                print(texto_de_guia())
                codigo = 0
            else:
                codigo = orden_informe(args[1:], opciones, borrar,
                                       donde.get("informe") or ruta_del_registro(), avisar)
        if codigo:
            print(texto.getvalue(), end="")
            return codigo
        try:
            escribir_entero(guardar_en, texto.getvalue())
        except (OSError, ValueError):
            avisar(f"no pude guardar en '{guardar_en}': fijate que el archivo no esté abierto "
                   "en otro programa y que se pueda escribir en esa carpeta")
            return 1
        print(f"Quedó guardado en {guardar_en}. Para abrirlo:  notepad "
              f"{para_pegar(guardar_en)}")
        return 0
    if args[0].lower() in ("guia", "guía"):
        print(texto_de_guia())
        return 0
    if args[0].lower() == "curso":
        if len(args) == 1 and os.path.isfile("curso.mate"):
            avisar("aviso: en esta carpeta hay un curso.mate, pero 'curso' sola es una orden "
                   "de Mate (muestra las clases para aprender). Para correr tu programa:  "
                   f"{como_se_llama()} correr curso.mate")
        return orden_curso(args[1:], avisar)
    if sin_tildes(args[0].lower()) == "nuevo" and not (
            len(args) == 1 and (os.path.isfile("nuevo") or os.path.isfile("nuevo.mate"))):
        # ('nuevo' sola, con un nuevo.mate en la carpeta, sigue corriendo ese programa)
        return orden_nuevo(args[1:], avisar)
    ensaya = sin_tildes(args[0].lower()) == "ensayar" and not (
        len(args) == 1 and (os.path.isfile("ensayar") or os.path.isfile("ensayar.mate")))
    if veces is not None and not ensaya:
        avisar("--veces va con 'ensayar': repite cada caso esa cantidad de veces, por "
               "ejemplo: ensayar mi_negocio.mate mi_negocio_casos.txt --veces=5")
        return 2
    if ensaya:
        # ('ensayar' sola, con un ensayar.mate en la carpeta, sigue corriendo ese programa)
        return orden_ensayar(args[1:], opciones | ({"--traza"} if conversacion else set()),
                             respuestas, veces, avisar)
    if args[0].lower() == "consola":
        if len(args) > 1:
            avisar("'consola' va sola, sin archivo: ahí adentro se escriben los renglones")
            return 2
        preparadas = []
        if respuestas:
            try:
                preparadas = respuestas_de_archivo(respuestas)
            except ErrorMate as e:
                avisar(e.mensaje)
                return 2
        def anotar(texto, categoria=None, sugerencia=None, familia=None):
            anotar_error_de_uso(donde.get("registro"), orden_usada(argv), "en la consola",
                                texto, categoria and f"en la consola: {categoria}",
                                sugerencia, familia)

        return consola(ia_simulada="--ia-simulada" in opciones, ia_respuestas=preparadas,
                       anotar=anotar)
    if args[0].lower() == "informe":
        if len(args) == 1 and borrar is None and os.path.isfile("informe.mate"):
            avisar("aviso: en esta carpeta hay un informe.mate, pero 'informe' sola es una "
                   "orden de Mate (muestra los errores de uso). Para correr tu programa:  "
                   f"{como_se_llama()} correr informe.mate")
        return orden_informe(args[1:], opciones, borrar,
                             donde.get("informe") or ruta_del_registro(), avisar)
    if "--para-mejorar" in opciones:
        avisar("--para-mejorar va con 'informe', sin archivo: informe --para-mejorar")
        return 2
    if sin_tildes(args[0].lower()) == "buzon":
        return orden_buzon(args[1:], avisar)
    if sin_tildes(args[0].lower()) in ORDENES_DE_MEMORIA:
        return orden_de_memoria(sin_tildes(args[0].lower()), args[1:], borrar, avisar,
                                opciones, respuestas)
    if borrar is not None:
        avisar("--borrar va con 'lecciones', por ejemplo: lecciones mi_mostrador.mate "
               "Mostrador --borrar=2")
        return 2

    def parece_archivo(a):
        return (a.lower().endswith((".mate", ".mate.txt")) or os.path.isfile(a)
                or os.path.isfile(a + ".mate"))

    if args[0].lower() not in ORDENES and parece_archivo(args[0]):
        if len(args) == 1:
            args = ["correr"] + args  # 'mate.py hola.mate' es 'mate.py correr hola.mate'
        elif len(args) == 2 and args[1].lower() in ORDENES:
            avisar(f"la orden va primero y el archivo después: {args[1].lower()} {args[0]}",
                   "al escribir la orden: el archivo antes que la orden", True)
            return 2
    orden, archivos = args[0].lower(), args[1:]
    if orden not in ORDENES:
        parecidas = difflib.get_close_matches(orden, ORDENES_SABIDAS, 1)
        avisar(f"no conozco la orden '{args[0]}'" + (
            f", ¿quisiste decir '{parecidas[0]}'?" if parecidas
            else ". Las órdenes son: correr, probar, verificar, consola, guia, ayuda, "
                 "curso, nuevo, ensayar, corregir, lecciones, propuestas, proponer, "
                 "bitacora, buzon, socio e informe"),
            "al escribir la orden: orden que no existe")
        return 2
    if not archivos:
        avisar(f"a '{orden}' le falta el archivo, por ejemplo: {orden} hola.mate",
               "al escribir la orden: falta el archivo")
        return 2
    if orden == "probar" and (len(archivos) > 1 or os.path.isdir(archivos[0])):
        return probar_varios(archivos, [a for a in argv if a.startswith("-")], avisar)
    if "--olvidar" in opciones and orden != "correr":
        avisar("--olvidar va con 'correr': el programa corre con sus agentes de cero, sin "
               "lo que recordaban")
        return 2
    if len(archivos) > 1:
        avisar(f"'{orden}' lleva un solo archivo y recibió {len(archivos)}: "
               + ", ".join(archivos)
               + " (si el nombre tiene espacios, ponelo entre comillas)",
               "al escribir la orden: más de un archivo")
        return 2

    ruta, problema = _ubicar(archivos[0])
    if problema:
        avisar(problema, "al escribir la orden: no está el archivo"
               if problema.startswith("no encuentro") else None)
        return 2
    problema = conversacion and traza_no_va_ahi(conversacion, ruta)
    if problema:  # antes de correr nada: ni se atiende ni se toca la memoria
        avisar(problema)
        return 2
    donde["ruta"] = ruta
    if ruta.lower().endswith(".mate.txt"):
        avisar(f"aviso: {os.path.basename(ruta)} termina en .txt (se lo agregó el Bloc de "
               "notas). Lo corro igual; para que quede bien, al guardar elegí "
               "Tipo: Todos los archivos")

    mostrado = {}
    etapa = ["al leer el programa"]  # en qué andaba Mate cuando mostró cada error

    def reportar(linea, texto, familia=None):
        donde.setdefault("errores", []).append({
            "etapa": etapa[0] if donde["interprete"] is None else "al correr",
            "mensaje": texto, "familia": familia or getattr(texto, "familia", None)})
        cabecera, renglon, camino = error_escrito(ruta, linea, texto)
        archivo = getattr(linea, "archivo", None) or ruta
        avisar(cabecera)
        if renglon and (archivo, renglon) != mostrado.get("ultimo"):
            avisar(renglon)  # el mismo renglón no se repite si trae varios errores
        mostrado["ultimo"] = (archivo, renglon)
        if camino:
            avisar(camino)

    if simbolo("·→", ""):
        salida = print
    else:  # consola que no conoce esos símbolos: la traza se escribe con letras comunes
        def salida(texto):
            print(texto.replace("→", "->").replace("·", "-"))

    renglones = []  # la conversación, si va a un archivo

    def cerrar_conversacion():
        interprete = donde["interprete"]
        if not conversacion or interprete is None:
            return
        guardadas = donde.get("guardadas", [])
        problema = guardar_conversacion(conversacion, ruta, renglones, interprete.cuenta,
                                        sumar=bool(guardadas))
        if problema:
            avisar(problema)
        elif guardadas:
            print(f"La conversación se sumó a {conversacion}")
        else:
            print(f"La conversación quedó guardada en {conversacion}")
        guardadas.append(ruta)

    archivo_memoria = archivo_de(ruta, "memoria.json")
    archivo_candado = archivo_de(ruta, "memoria.candado")
    # leida: lo que decía el archivo al abrirlo. buzon: el buzón entre programas (0.7).
    # candado: el de la memoria, si esta corrida lo tiene (ver tomar_candado_de_memoria).
    aprendido = {"leida": None, "abierta": False, "buzon": None, "candado": None,
                 "sin_candado": None}

    def con_candado(hacer, espera):
        """Hace eso con el candado de la memoria tomado: nadie más lee y reescribe la
        memoria de este programa mientras tanto. Si esta corrida ya lo tiene (un programa
        con 'estado recordado' lo tiene toda la corrida), lo hace y listo. Devuelve False,
        SIN HACER NADA, si no se pudo tomar: porque lo tiene otra corrida y no lo soltó en
        'espera' segundos, o porque acá no se puede tener un candado (el sistema no los da
        en esa carpeta, no se puede crear el archivo, o con ese nombre hay otra cosa). Sin
        candado no se hace nunca: el porqué queda en aprendido["sin_candado"] (None si es
        que lo tiene otra corrida), para que el que llama avise."""
        if aprendido["candado"] is not None:
            hacer()
            return True
        aprendido["sin_candado"] = None
        try:
            candado = tomar_candado_de_memoria(archivo_candado, espera)
        except OSError as e:
            aprendido["sin_candado"] = e
            return False
        if candado is None:
            return False
        # (mientras dura, es el candado de esta corrida: con él se escribe la memoria)
        aprendido["candado"] = candado
        try:
            hacer()
        finally:
            aprendido["candado"] = None
            soltar_candado_de_memoria(candado, archivo_candado)
        return True

    def guardar(agentes, buzon=None, correo=None):
        """Escribe la memoria de este programa. Solo se llama con el candado tomado (toda
        la corrida, o adentro de con_candado) y con lo que se leyó ya con él tomado: sin
        candado, guardar_memoria se niega."""
        if correo is None:  # (se conserva la parte de lo enviado y de los socios)
            return guardar_memoria(archivo_memoria, os.path.basename(ruta), agentes, buzon,
                                   candado=aprendido["candado"])
        return guardar_memoria(archivo_memoria, os.path.basename(ruta), agentes, buzon,
                               candado=aprendido["candado"], correo=correo)

    def por_que_no_hay_candado(e):
        return por_que_no_se_tomo_el_candado(ruta, e)

    def avisar_que_no_salen(cuantos):
        """Sin el candado de la memoria no se reparte ni se recupera nada del buzón: se
        avisa por qué (una vez) y que los mensajes quedan anotados para la próxima."""
        e = aprendido.get("sin_candado")
        quedan = (f"{cuantos_mensajes(cuantos)} para otros programas "
                  f"{'queda anotado' if cuantos == 1 else 'quedan anotados'} en "
                  f"{os.path.basename(archivo_memoria)} y "
                  f"{'sale' if cuantos == 1 else 'salen'} la próxima vez que "
                  f"{os.path.basename(ruta)} corra y pueda tomar el candado")
        if e is None:
            avisar(f"aviso: otra ventana de {os.path.basename(ruta)} tiene tomado el "
                   f"candado de la memoria, y sin candado no reparto mensajes: {quedan}")
        elif aprendido.get("avisado"):
            avisar(f"aviso: sigo sin el candado de la memoria, así que no reparto "
                   f"mensajes: {quedan}")
        else:
            aprendido["avisado"] = True
            que_paso, que_hacer = por_que_no_hay_candado(e)
            avisar(f"aviso: {que_paso}. Sin candado no reparto mensajes: {quedan}. "
                   f"{que_hacer}")

    def avisar_que_no_se_guardo(buzon):
        """Al terminar, con cosas del buzón para guardar y sin el candado de la memoria: no
        se escribió nada. Se dice qué se perdió y qué queda como estaba, y la corrida
        termina con código distinto de 0 (aprendido["sin_guardar"])."""
        aprendido["sin_guardar"] = True
        e = aprendido.get("sin_candado")
        nombre = os.path.basename(ruta)
        if e is None:
            que_paso = (f"otra ventana de {nombre} tiene tomado el candado de la memoria "
                        "y no lo soltó en 10 segundos")
            que_hacer = (f"Fijate si quedó otra ventana de {nombre} colgada, cerrala y "
                         "corré esto de nuevo")
        else:
            que_paso, que_hacer = por_que_no_hay_candado(e)
        partes = []
        enviados = len(buzon.por_salir)
        if enviados:
            partes.append(
                f"{cuantos_mensajes(enviados)} que este programa envió a otros programas "
                f"en esta corrida NO {'salió' if enviados == 1 else 'salieron'} y NO "
                f"{'quedó anotado' if enviados == 1 else 'quedaron anotados'}: "
                f"{'se perdió' if enviados == 1 else 'se perdieron'}, hay que hacerlo de "
                "nuevo")
        recibidos = len(buzon.atendidos) + len(buzon.rechazos)
        if recibidos:
            partes.append(
                f"{cuantos_mensajes(recibidos)} del buzón "
                f"{'sigue' if recibidos == 1 else 'siguen'} en "
                f"{os.path.basename(buzon.carpeta)} como si no se "
                f"{'hubiera' if recibidos == 1 else 'hubieran'} atendido, y se "
                f"{'atiende' if recibidos == 1 else 'atienden'} de nuevo la próxima vez")
        # (del resumen queda solo lo que de verdad salió, al arrancar y con candado)
        buzon.atendi, buzon.no_entregados = {}, 0
        avisar(f"error: {que_paso}. Sin candado no escribo la memoria ni el buzón, así "
               f"que lo que pasó con el buzón en esta corrida NO se guardó: "
               + "; ".join(partes or ["no quedó anotado nada"]) + f". {que_hacer}")

    def cerrar_buzon(buzon, nueva):
        """Al terminar 'correr', si en esta corrida hubo buzón. La memoria es el punto de
        compromiso: en UNA escritura quedan el estado de los agentes, los mensajes que ya
        se atendieron y los que hay que dejarles a otros programas. Recién después se
        reparten esos, se mueven los rechazados y se borran los atendidos. Si se corta en
        el medio, la corrida siguiente termina el trabajo sin repetir ni perder nada.
        Se llama SIEMPRE con el candado de la memoria tomado (ver con_candado)."""
        leida = aprendido["leida"]
        try:
            en_disco = leer_memoria(archivo_memoria)[0]
        except ErrorMate:
            avisar(f"aviso: no guardé la memoria: {os.path.basename(archivo_memoria)} "
                   "cambió mientras el programa corría y ahora no se entiende. Lo que pasó "
                   "en esta corrida no va a estar en la próxima, y los mensajes del buzón "
                   "quedan como estaban; abrilo con el Bloc de notas y arreglalo")
            return
        if nueva != leida:
            agentes = fundir_memoria(leida or {}, nueva, en_disco) \
                if en_disco != (leida or {}) else nueva
        else:
            agentes = en_disco
        en_buzon = leer_buzon_de_memoria(archivo_memoria)[0]
        parte = buzon.fundido(en_buzon)
        # (0.8) Lo enviado y lo de los socios va en la MISMA escritura: el número de cada
        # sobre que sale, lo que llegó y lo que ya se entregó quedan junto con el estado.
        en_correo = leer_correo_de_memoria(archivo_memoria)
        correo = buzon.correo_fundido(en_correo)
        if agentes != en_disco or parte != en_buzon or correo != en_correo:
            problema = guardar(agentes, parte, correo if correo != en_correo else None)
            if problema:
                avisar(f"aviso: {problema}. Los mensajes del buzón no se tocaron: los que "
                       "llegaron se atienden de nuevo la próxima vez, y no salió ninguno")
                return
        quedan = buzon.repartir(parte["por_salir"])
        buzon.acomodar()
        salio = False
        if buzon.socios is not None:
            salio = buzon.socios.repartir(correo)
            buzon.socios.acomodar()
        if salio:
            try:
                ahora = leer_memoria(archivo_memoria)[0]
            except ErrorMate:
                return
            guardar(ahora, None, correo)
        if len(quedan) != len(parte["por_salir"]):
            # Lo repartido deja de estar "por salir". Se mira el archivo de nuevo, por si
            # otra ventana guardó algo mientras tanto. (Si esto falla no pasa nada: se
            # reparten otra vez, con el mismo nombre de archivo, y el que recibe descarta
            # los que ya atendió.)
            try:
                ahora = leer_memoria(archivo_memoria)[0]
            except ErrorMate:
                return
            guardar(ahora, buzon.fundido(leer_buzon_de_memoria(archivo_memoria)[0]))

    def guardar_lo_nuevo(nueva):
        """Al terminar, con el candado de la memoria tomado: lee el archivo de nuevo, le
        suma lo de esta corrida y lo escribe."""
        try:
            en_disco = leer_memoria(archivo_memoria)[0]
        except ErrorMate:
            en_disco = None
        if en_disco is None and aprendido["leida"] is not None:
            avisar(f"aviso: no guardé la memoria: {os.path.basename(archivo_memoria)} "
                   "cambió mientras el programa corría y ahora no se entiende. Lo que "
                   "pasó en esta corrida no va a estar en la próxima; abrilo con el Bloc "
                   "de notas y arreglalo")
            return
        if en_disco is not None and en_disco != (aprendido["leida"] or {}):
            nueva = fundir_memoria(aprendido["leida"] or {}, nueva, en_disco)
            if nueva == en_disco:
                return
        if nueva != aprendido["leida"] and (nueva or os.path.lexists(archivo_memoria)):
            problema = guardar(nueva)
            if problema:
                avisar(f"aviso: {problema}")

    def avisar_que_no_se_guardo_la_memoria():
        """Al terminar, con algo para guardar en la memoria y sin poder tomar su candado:
        no se escribió nada. Se dice, y la corrida termina con código distinto de 0."""
        aprendido["sin_guardar"] = True
        e = aprendido.get("sin_candado")
        nombre = os.path.basename(ruta)
        if e is None:
            que_paso = (f"otra ventana de {nombre} tiene tomado el candado de la memoria "
                        "y no lo soltó en 10 segundos")
            que_hacer = (f"Fijate si quedó otra ventana de {nombre} colgada, cerrala y "
                         "corré esto de nuevo")
        else:
            que_paso, que_hacer = por_que_no_hay_candado(e)
        avisar(f"error: {que_paso}. Sin candado no escribo la memoria, así que lo que "
               f"los agentes de {nombre} anotaron en esta corrida (lo que aprendieron y la "
               f"cuenta de consultas a la IA) NO se guardó en "
               f"{os.path.basename(archivo_memoria)}: no va a estar en la próxima. "
               f"{que_hacer}")

    def cerrar_memoria():
        """Al terminar 'correr': guarda lo que recuerdan los agentes (si cambió) y suma
        sus fallas a la bitácora. Un programa que no usa nada de esto no crea archivos."""
        interprete = donde["interprete"]
        if not aprendido["abierta"]:
            return
        aprendido["abierta"] = False
        buzon = aprendido["buzon"]
        if buzon is not None:
            # Lo que un agente ya dejó para otro programa sale aunque la corrida se haya
            # cortado: se guarda junto con el estado de ese agente.
            interprete.sacar_lo_del_buzon()
        nueva = interprete.memoria_actual()
        if buzon is not None and buzon.cambio():
            try:
                # Leer la memoria, guardarla y repartir va de un tirón, con el candado de
                # la memoria: dos corridas del mismo programa que terminan a la vez no se
                # pisan. Sin candado (lo tiene otra hace rato, o dejó de poder tomarse)
                # no se escribe NADA: ni la memoria, ni un sobre, ni se borra lo recibido.
                # Anotar "por salir" sin candado sería pisarle lo anotado a otra corrida
                # que termina a la vez, y perder un mensaje callado. Se dice fuerte y la
                # corrida termina con código distinto de 0.
                if not con_candado(lambda: cerrar_buzon(buzon, nueva), 10):
                    avisar_que_no_se_guardo(buzon)
            finally:
                buzon.soltar()
            for renglon in buzon.resumen():
                print(renglon)
            nueva = aprendido["leida"]  # (la memoria ya quedó guardada, o avisada)
        elif buzon is not None:
            buzon.soltar()
            if buzon.socios is not None:  # (nada que guardar: "no llegó nada nuevo de...")
                for renglon in buzon.socios.resumen():
                    print(renglon)
        if buzon is not None and not buzon.atendio:
            # El programa se cortó antes de terminar sus renglones (un error, o Ctrl+C):
            # lo que le dejaron en el buzón no se atendió. Que no quede esperando callado.
            de_quien, raros, _, sin_mirar = buzon.contar(
                leer_buzon_de_memoria(archivo_memoria)[0]["recibidos"])
            esperan = sum(de_quien.values()) + raros + sin_mirar
            if esperan:
                avisar(f"aviso: en el buzón {'quedó' if esperan == 1 else 'quedaron'} "
                       f"{cuantos_mensajes(esperan)} sin atender, porque el programa se "
                       "cortó antes de terminar: el buzón se atiende cuando el programa "
                       "termina solo (un mostrador, cuando se sale con su palabra de "
                       "salida, no con Ctrl+C). "
                       f"{'Sigue' if esperan == 1 else 'Siguen'} ahí para la próxima vez")
        if nueva != aprendido["leida"] and (nueva or os.path.lexists(archivo_memoria)):
            # Hay algo para guardar. Va con el candado de la memoria tomado (un programa con
            # 'estado recordado' ya lo tiene; uno sin, lo toma ahora, por un momento) y sobre
            # lo que dice el archivo AHORA, leído con el candado ya tomado: si cambió
            # mientras el programa corría (otra ventana anotó una lección o sumó consultas),
            # se suma lo de esta corrida a eso, en vez de pisarlo. Sin candado no se escribe.
            if not con_candado(lambda: guardar_lo_nuevo(nueva), 10):
                avisar_que_no_se_guardo_la_memoria()
        problema = guardar_bitacora(archivo_de(ruta, "bitacora.txt"), os.path.basename(ruta),
                                    interprete.bitacora or [], escrito=ruta)
        if problema:
            avisar(f"aviso: {problema}")

    try:
        try:
            fuente = leer_fuente(ruta)
        except PermissionError:
            avisar(f"no pude abrir {ruta}: no tengo permiso para leerlo")
            return 2
        except OSError:
            avisar(f"no pude abrir {ruta}")
            return 2
        programa = analizar(fuente, ruta)
        etapa[0] = "antes de correr"
        errores = verificar(programa)
        if errores:
            for linea, texto in errores:
                reportar(linea, texto)
            return 1
        for aviso in avisos_de_socios(programa):
            avisar(f"aviso: {aviso}")
        if orden == "verificar":
            print(f"{ruta}: sin errores")
            return 0
        interprete = donde["interprete"] = Interprete(
            salida=salida, traza="--traza" in opciones or bool(conversacion))
        if conversacion:
            interprete.anotar = renglones.append
        interprete.archivo = ruta
        interprete.separar_salida = orden == "probar"
        if "--sin-limite" in opciones:
            interprete.max_pasos = None
        interprete.ia_simulada = "--ia-simulada" in opciones
        if respuestas:
            try:
                interprete.ia_respuestas = respuestas_de_archivo(respuestas)
            except ErrorMate as e:
                avisar(e.mensaje)
                return 2
        if orden == "correr":
            # Un programa con 'estado recordado' se corre de a una ventana por vez: al
            # terminar, cada corrida guarda el estado entero de sus agentes, y con dos
            # abiertas la última pisaría lo que anotó la otra (dos cajas venderían la misma
            # última unidad). El candado se tiene toda la corrida y el sistema lo suelta
            # solo si el proceso muere. 'probar', 'verificar' y 'ensayar' no lo piden.
            if tiene_estado_recordado(programa):
                try:
                    aprendido["candado"] = tomar_candado_de_memoria(archivo_candado,
                                                                    ESPERA_AL_ABRIR)
                    ocupado = aprendido["candado"] is None
                except OSError as e:
                    # No se pudo tomar, y no es por otra ventana: el sistema no da candados
                    # en esa carpeta, no se puede crear el archivo, o con ese nombre hay
                    # algo que no sirve (una carpeta, un archivo ajeno sin permiso). Por lo
                    # que sea: no se puede saber si hay otra ventana, y atender igual sería
                    # perder justo lo que el candado cuida (dos cajas venderían la misma
                    # última unidad). No se arranca: se dice qué pasó y qué se puede hacer.
                    que_paso, que_hacer = por_que_no_hay_candado(e)
                    if getattr(e, "motivo", ""):
                        que_paso += (". Este programa recuerda cosas de una corrida a la "
                                     "otra ('estado recordado') y sin candado no puedo "
                                     "fijarme si ya está abierto en otra ventana (dos a la "
                                     "vez se pisarían lo anotado), así que no lo corro")
                    avisar(f"{que_paso}. {que_hacer}. Acá no se tocó nada: ni la memoria "
                           "ni el buzón")
                    return 2
                if ocupado:
                    nombre = os.path.basename(ruta)
                    avisar(f"ya hay otra ventana abierta con {nombre}. Este programa "
                           "recuerda cosas de una corrida a la otra ('estado recordado'), y "
                           "con dos ventanas a la vez una pisaría lo que anotó la otra. "
                           "Terminá la charla de la otra ventana (o cerrala) y corré esto de "
                           "nuevo. "
                           # (Windows contesta lo mismo cuando el candado lo tiene otro
                           # que cuando una carpeta de red no los da: no se distinguen.)
                           + ("Si no hay ninguna otra ventana abierta, puede ser que esta "
                              "carpeta no dé candados (pasa en algunas carpetas de red): "
                              "copiá la carpeta del programa a un disco de esta "
                              "computadora y corrélo desde ahí. " if os.name == "nt" else "")
                           + "Acá no se tocó nada: ni la memoria ni el buzón")
                    return 2
            # Lo que aprendieron los agentes (0.4): solo 'correr' lee y escribe su memoria.
            # La lectura del arranque se hace CON el candado de la memoria tomado: así no
            # cae justo mientras otra corrida reemplaza el archivo (en Windows eso es un
            # "no hay permiso" y la corrida no arrancaba), ni lee una memoria a medio
            # cambiar. Un programa con 'estado recordado' ya lo tiene. Uno sin, lo toma
            # para leer y lo suelta (se puede abrir en dos ventanas), y solo si hay algo
            # que cuidar: el archivo de memoria existe, o el programa les envía mensajes a
            # otros ('usar buzon'). Un programa que no recuerda nada no crea ningún archivo.
            inicio = {}

            def leer_al_arrancar():
                try:
                    inicio["memoria"], inicio["avisos"] = leer_memoria(archivo_memoria)
                    inicio.pop("error", None)
                except ErrorMate as e:
                    inicio["error"] = e
                inicio["buzon"] = leer_buzon_de_memoria(archivo_memoria)
                inicio["correo"] = leer_correo_de_memoria(archivo_memoria)

            envia_a_otros = any(s[0] == "agente_ajeno" for s in programa)
            if aprendido["candado"] is not None:
                leer_al_arrancar()
            elif envia_a_otros or os.path.lexists(archivo_memoria):
                if not con_candado(leer_al_arrancar, 2):
                    # Un programa sin 'estado recordado' que les envía mensajes a otros
                    # programas necesita el candado al terminar, para anotarlos y
                    # repartirlos. Si acá no se puede tener un candado, se sabe ahora: no
                    # se arranca, en vez de atender y perder al final lo que se envió.
                    if envia_a_otros and aprendido["sin_candado"] is not None:
                        que_paso, que_hacer = por_que_no_hay_candado(aprendido["sin_candado"])
                        if getattr(aprendido["sin_candado"], "motivo", ""):
                            que_paso += (". Este programa les envía mensajes a otros "
                                         "programas ('usar buzon') y sin candado no los "
                                         "puedo anotar ni repartir sin riesgo de perder "
                                         "alguno, así que no lo corro")
                        avisar(f"{que_paso}. {que_hacer}. Acá no se tocó nada: ni la "
                               "memoria ni el buzón")
                        return 2
                    # (Lo tiene otra corrida y no lo soltó en 2 segundos, o acá no hay
                    # candados y el programa no envía nada: se lee sin candado, que para
                    # leer alcanza; leer_archivo_de_memoria insiste si el archivo está
                    # siendo reemplazado. Para ESCRIBIR va a hacer falta el candado.)
                    leer_al_arrancar()
            else:
                leer_al_arrancar()
            if "error" in inicio and "--olvidar" in opciones:
                # No se entendía, y pidieron empezar de cero: ahí adentro puede haber
                # lecciones, así que el archivo roto no se pisa: queda guardado aparte.
                # Moverlo es cambiar la memoria: va con el candado tomado, y después de
                # leerla de nuevo (si otra ventana la arregló recién, no se mueve nada).
                rota = archivo_de(ruta, "memoria.rota.json")

                def apartar_la_rota():
                    leer_al_arrancar()
                    if "error" not in inicio:
                        return
                    try:
                        escribir_memoria(archivo_memoria, aprendido["candado"], mover_a=rota)
                        inicio["apartada"] = True
                    except OSError:
                        pass

                if not con_candado(apartar_la_rota, 2):
                    if aprendido["sin_candado"] is None:
                        por_que = (f"otra ventana de {os.path.basename(ruta)} tiene tomado "
                                   "el candado de la memoria: cerrala y probá de nuevo")
                    else:
                        por_que = ". ".join(por_que_no_hay_candado(aprendido["sin_candado"]))
                    avisar(f"{inicio['error'].mensaje}\n(--olvidar no lo pisa: ahí pueden "
                           "estar las lecciones, y no lo pude guardar aparte sin el candado "
                           f"de la memoria: {por_que})")
                    return 2
                if "error" in inicio and not inicio.get("apartada"):
                    avisar(f"{inicio['error'].mensaje}\n(--olvidar no lo pisa: ahí pueden "
                           "estar las lecciones, y no pude guardarlo aparte)")
                    return 2
                if "error" in inicio:
                    inicio["memoria"], inicio["avisos"] = {}, []
                    inicio["buzon"] = leer_buzon_de_memoria(archivo_memoria)
                    avisar("aviso: --olvidar: los agentes arrancan de cero. "
                           f"{os.path.basename(archivo_memoria)} estaba mal escrito y no se "
                           "entendía, así que esta vez se pierden también las "
                           f"lecciones. Lo dejé como estaba en {rota} (se abre con el Bloc "
                           "de notas) por si querés rescatar alguna y anotarla de nuevo con "
                           "'corregir'")
                else:  # (otra ventana la arregló justo: vale lo que dice ahora)
                    aprendido["leida"] = json.loads(json.dumps(inicio["memoria"]))
            elif "error" in inicio:
                avisar(inicio["error"].mensaje)
                return 2
            else:
                aprendido["leida"] = json.loads(json.dumps(inicio["memoria"]))
            memoria, avisos = inicio["memoria"], inicio["avisos"]
            for aviso in avisos:
                avisar(f"aviso: {aviso}")
            if "--olvidar" in opciones:
                for ficha in memoria.values():
                    ficha["estado"] = {}
                if aprendido["leida"] is not None:
                    avisar("aviso: --olvidar: los agentes arrancan de cero, sin lo que "
                           "recordaban (las lecciones no se borran: eso se hace con la "
                           "orden 'lecciones')")
            # La memoria y las lecciones son del programa que se corre: si un archivo
            # traído con 'usar' tiene las suyas (alguien lo corrigió por su nombre), se avisa.
            traidos = {}  # archivo traído con 'usar' -> el primer agente que declara
            for s in programa:
                if s[0] == "agente" and (getattr(s[1], "archivo", None) or ruta) != ruta:
                    traidos.setdefault(s[1].archivo, s[2])
            for otro, agente in sorted(traidos.items()):
                if os.path.isfile(archivo_de(otro, "memoria.json")):
                    avisar(f"aviso: {os.path.basename(otro)} tiene su propia memoria "
                           f"({os.path.basename(archivo_de(otro, 'memoria.json'))}) y acá no "
                           "se usa: la memoria y las lecciones son del programa que se "
                           "corre. Para que a un agente le llegue una lección en este "
                           f"programa:  {como_se_llama()} corregir {para_pegar(ruta)} "
                           f'{agente} "la lección"')
            interprete.memoria, interprete.recordando = memoria, True
            # El buzón entre programas (0.7): lo que quedó "por salir" de una corrida que
            # se cortó entre guardar y repartir sale ahora, antes que nada.
            buzon = aprendido["buzon"] = interprete.buzon = Buzon(
                ruta, lambda texto: avisar(f"aviso: {texto}"))
            buzon.leido, avisos = inicio["buzon"]
            for aviso in avisos:
                avisar(f"aviso: {aviso}")
            def recuperar_lo_por_salir():
                """Con el candado de la memoria tomado: se lee de nuevo lo que quedó por
                salir (otra corrida pudo repartirlo recién), se reparte y se guarda la
                memoria como está AHORA en el archivo, sin lo repartido: no la que esta
                corrida leyó al arrancar."""
                pendientes = leer_buzon_de_memoria(archivo_memoria)[0]["por_salir"]
                if not pendientes:
                    return
                quedan = buzon.repartir(pendientes)
                if len(quedan) == len(pendientes):
                    return
                try:
                    ahora = leer_memoria(archivo_memoria)[0]
                except ErrorMate:
                    return  # (cambió y no se entiende: no se pisa; se avisa al terminar)
                en_buzon = leer_buzon_de_memoria(archivo_memoria)[0]
                guardar(ahora, dict(en_buzon, por_salir=[
                    p for p in en_buzon["por_salir"]
                    if (p["carpeta"], p["sobre"]["id"]) not in buzon.repartidos]))

            if buzon.leido["por_salir"]:
                # (Si otra corrida de este programa tiene el candado, lo está repartiendo
                # ella: acá no se toca. Y si acá no se puede tener candado, tampoco: sin
                # candado no se reparte nada. Queda anotado, se avisa, y sale otra vez.)
                if not con_candado(recuperar_lo_por_salir, 2) \
                        and aprendido["sin_candado"] is not None:
                    avisar_que_no_salen(len(buzon.leido["por_salir"]))
                buzon.leido = leer_buzon_de_memoria(archivo_memoria)[0]

            buzon.enviados = set(inicio["correo"]["enviados"])
            buzon.leer_correo = lambda: leer_correo_de_memoria(archivo_memoria)
            declarados = socios_declarados(programa)
            if declarados:
                # Los socios (0.8): las claves, y la cuenta de cada uno en la memoria. Lo
                # que quedó "por salir" de una corrida anterior sale ahora.
                socios = buzon.socios = Socios(ruta, declarados, buzon,
                                               lambda texto: avisar(f"aviso: {texto}"))
                socios.cargar_claves()
                socios.leer_estado = lambda: leer_correo_de_memoria(archivo_memoria)["socios"]

                def preparar_socios():
                    correo = leer_correo_de_memoria(archivo_memoria)
                    cambio, por_estrenar = socios.preparar(correo)
                    salio = socios.repartir(correo)
                    if cambio or salio:
                        try:
                            ahora = leer_memoria(archivo_memoria)[0]
                        except ErrorMate:
                            socios.frenar_todos()
                            return
                        if guardar(ahora, None, correo):
                            socios.frenar_todos()
                            return
                    socios.estrenar(por_estrenar)

                if socios.fichas and not con_candado(preparar_socios, 2):
                    socios.frenar_todos()
                    avisar("aviso: no pude tomar el candado de la memoria para revisar la "
                           "cuenta de los socios: en esta corrida no mando ni recibo nada "
                           "de ellos (lo que se les envíe queda anotado)")

            def cambio_la_memoria():
                """¿Otra ventana de este programa guardó un estado distinto del que leyó
                esta al empezar? (y los mensajes del buzón que el archivo ya da por atendidos)"""
                try:
                    en_disco = leer_memoria(archivo_memoria)[0]
                except ErrorMate:
                    return True, []
                leida = aprendido["leida"] or {}
                cambio = any(en_disco.get(a, {}).get("estado", {})
                             != leida.get(a, {}).get("estado", {})
                             for a in set(en_disco) | set(leida))
                return cambio, leer_buzon_de_memoria(archivo_memoria)[0]["recibidos"]

            buzon.cambio_la_memoria = cambio_la_memoria

            def se_puede_guardar(cuantos):
                """Antes de atender lo que llegó al buzón: se toma el candado de la memoria
                y NO se suelta hasta que la corrida termina de guardar. Atender un mensaje
                es anotar después, en la memoria, que se atendió: si al terminar el candado
                no se pudiera tomar, el mensaje quedaría en el buzón ya atendido y se
                atendería otra vez. Por eso el manejador de un sobre no corre nunca sin el
                candado ya en la mano.
                Devuelve True si esta corrida lo tiene; None si lo tiene otra corrida y no
                lo soltó en 2 segundos (no se atiende nada, avisa el buzón); False si acá
                no se puede tener un candado (no se atiende nada, y ya se avisó)."""
                if aprendido["candado"] is not None:
                    return True
                aprendido["sin_candado"] = None
                try:
                    candado = tomar_candado_de_memoria(archivo_candado, 2)
                except OSError as e:
                    aprendido["sin_candado"], candado = e, None
                if candado is not None:
                    aprendido["candado"] = candado  # (se suelta al final de la corrida)
                    return True
                if aprendido["sin_candado"] is None:
                    return None
                esperan = (f"{cuantos_mensajes(cuantos)} "
                           f"{'queda' if cuantos == 1 else 'quedan'} en "
                           f"{os.path.basename(buzon.carpeta)} y se "
                           f"{'atiende' if cuantos == 1 else 'atienden'} la próxima vez que "
                           f"{os.path.basename(ruta)} corra y pueda tomar el candado")
                if aprendido.get("avisado"):
                    avisar("aviso: sigo sin el candado de la memoria, así que tampoco "
                           f"atiendo el buzón: {esperan}")
                else:
                    aprendido["avisado"] = True
                    que_paso, que_hacer = por_que_no_hay_candado(aprendido["sin_candado"])
                    avisar(f"aviso: {que_paso}. Sin candado no atiendo el buzón: {esperan}. "
                           f"{que_hacer}")
                return False

            buzon.se_puede_guardar = se_puede_guardar

            def guardar_cuenta():
                """Antes y después de cada consulta de verdad de un agente con frenos: la
                cuenta de hoy queda en el disco ya, por si cierran la ventana sin dejar
                terminar, y se suma lo que haya anotado otra ventana (el mismo programa
                abierto dos veces, o la orden 'proponer'): el tope es uno solo. Lo demás
                de la memoria queda como estaba; se guarda al final."""
                def con_la_cuenta(leida):
                    nueva = json.loads(json.dumps(leida))
                    for nombre, agente in interprete.agentes.items():
                        gasto = gasto_limpio(agente.gasto)
                        if gasto:
                            nueva.setdefault(
                                nombre, {"estado": {}, "lecciones": []})["gasto"] = gasto
                    return nueva

                def anotar():
                    """(con el candado de la memoria tomado: lee el archivo de nuevo)"""
                    leida = aprendido["leida"] or {}
                    nueva = con_la_cuenta(leida)
                    try:
                        en_disco = leer_memoria(archivo_memoria)[0]
                    except ErrorMate:
                        return  # (cambió y no se entiende: no se pisa; se avisa al terminar)
                    if en_disco == leida:
                        if nueva != leida and not guardar(nueva):
                            aprendido["leida"] = nueva
                        return
                    junta = fundir_memoria(leida, nueva, en_disco)
                    if junta != en_disco and guardar(junta):
                        return
                    # La cuenta de los agentes pasa a ser la del archivo (con lo de la otra
                    # ventana adentro). Lecciones y estado siguen como al empezar la corrida.
                    for nombre, agente in interprete.agentes.items():
                        gasto = junta.get(nombre, {}).get("gasto", {})
                        for dia, cuenta in gasto.items():
                            agente.ensayo_desde[dia] = (
                                agente.ensayo_desde.get(dia, 0) + cuenta["simuladas"]
                                - agente.gasto.get(dia, {}).get("simuladas", 0))
                        agente.gasto = {dia: dict(cuenta) for dia, cuenta in gasto.items()}
                        ficha = nueva.get(nombre)
                        if ficha is not None:
                            ficha.pop("gasto", None)
                        if gasto:
                            nueva.setdefault(nombre, {"estado": {}, "lecciones": []})[
                                "gasto"] = json.loads(json.dumps(gasto))
                    aprendido["leida"] = {a: f for a, f in nueva.items() if any(f.values())}

                try:  # (si no hay nada que anotar ni que sumar, no se pide el candado)
                    leida = aprendido["leida"] or {}
                    if leer_memoria(archivo_memoria)[0] == leida == con_la_cuenta(leida):
                        return
                except ErrorMate:
                    return  # (cambió y no se entiende: no se pisa; se avisa al terminar)
                if con_candado(anotar, 2) or aprendido.get("cuenta_avisada"):
                    return
                # Sin candado no se escribe. La cuenta sigue en la mano y se anota al
                # terminar (ahí, si tampoco se puede, se dice fuerte y el código no es 0).
                aprendido["cuenta_avisada"] = True
                e = aprendido["sin_candado"]
                avisar("aviso: no pude anotar ahora la cuenta de consultas a la IA en "
                       f"{os.path.basename(archivo_memoria)}: "
                       + (f"otra ventana de {os.path.basename(ruta)} tiene tomado el candado "
                          "de la memoria" if e is None else por_que_no_hay_candado(e)[0])
                       + ". Sin candado no escribo la memoria: la anoto al terminar")

            interprete.guardar_cuenta = guardar_cuenta
            interprete.avisar = lambda texto: avisar(f"aviso: {texto}")
            if usa_memoria(programa) or any(f["lecciones"] for f in memoria.values()):
                interprete.bitacora = []
            aprendido["abierta"] = True
        try:
            resultados = interprete.correr(programa, pruebas=orden == "probar")
            if orden == "correr":
                # Los renglones del programa terminaron: ahora se atiende lo que otros
                # programas le dejaron en el buzón (0.7).
                interprete.atender_buzon()
        finally:  # también si el programa termina con un error, o lo cortan con Ctrl+C
            cerrar_memoria()
    except ErrorMate as e:
        # Primero lo que ya había fallado en los agentes: suele ser la causa del corte.
        for linea, texto in getattr(donde["interprete"], "errores_agentes_det", ()):
            reportar(linea, texto)
        if donde["interprete"] is not None:
            reportar(e.linea, donde["interprete"].con_camino(e.mensaje, e), e.familia)
        else:
            reportar(e.linea, e.mensaje, e.familia)
        avisar_pendientes(donde["interprete"], avisar)
        cerrar_conversacion()
        return 1
    finally:
        if aprendido["candado"] is not None:
            soltar_candado_de_memoria(aprendido["candado"], archivo_candado)
            aprendido["candado"] = None

    cerrar_conversacion()
    if orden == "probar":
        if interprete.errores_principal:
            avisar("errores al correr el programa (antes de las pruebas):")
            for linea, texto in interprete.errores_principal:
                reportar(linea, texto)
        fallidas = 0
        bien, mal = simbolo("✓", "OK"), simbolo("✗", "FALLA")
        donde["pruebas"] = (0, len(resultados))
        if not resultados:
            print("este archivo no tiene pruebas. Una prueba se escribe así:  "
                  'prueba "suma bien" { asegurar 1 + 1 == 2 }' if not donde.get("varios")
                  else "  (sin pruebas)")
            return 1 if interprete.errores_principal else 0
        for (nombre, error), fallas, mostrado in zip(
                resultados, interprete.detalle_pruebas, interprete.mostrado_pruebas):
            print(f"  {mal if error else bien} {nombre}")
            for texto in mostrado:  # lo que la prueba mostró, debajo de su nombre
                for parte in str(texto).split("\n"):
                    print(f"      | {parte}")
            for linea, texto in fallas:
                # igual que con 'correr': archivo:renglón: error: ..., y el renglón debajo
                for parte in filter(None, error_escrito(ruta, linea, texto)):
                    for pedazo in parte.split("\n"):
                        print(f"      {pedazo}")
            fallidas += bool(error)
        donde["pruebas"] = (len(resultados) - fallidas, len(resultados))
        print(f"{len(resultados) - fallidas} de {len(resultados)} pruebas pasaron")
        return 1 if fallidas or interprete.errores_principal else 0
    for linea, texto in interprete.errores_agentes_det:
        reportar(linea, texto)
    return 1 if interprete.errores_agentes or aprendido.get("sin_guardar") else 0


if __name__ == "__main__":
    sys.exit(main(registro=True))
