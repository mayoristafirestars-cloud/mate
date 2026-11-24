"""Pruebas de los socios (Mate 0.8): agentes de negocios distintos que se hablan por una
carpeta compartida, con sobres firmados. Correr con: python3 -m pytest mate/pruebas -q"""

import json
import os
import pathlib
import re
import sys

import pytest

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import mate  # noqa: E402


@pytest.fixture(autouse=True)
def sin_red_ni_registro(monkeypatch):
    """Ninguna prueba sale a la red, ni anota en el registro de errores de uso de verdad."""
    import urllib.request

    def nadie_sale(*_a, **_k):
        raise AssertionError("una prueba quiso salir a la red")

    monkeypatch.setattr(urllib.request, "urlopen", nadie_sale)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("MATE_SIN_REGISTRO", "1")
    monkeypatch.setattr(mate, "_QUIEN_ME_LANZO", "")
    monkeypatch.setenv("MATE_ORDEN", "python")
    monkeypatch.delenv("OneDrive", raising=False)
    monkeypatch.delenv("OneDriveConsumer", raising=False)


# ── ayudas ──
CIFRAS = "0123456789" * 4
CLAVE = CIFRAS + "0469"  # una clave fija, con su control: solo para estas pruebas
OTRA_CLAVE = "9" * 40 + mate.control_de_clave("9" * 40)

RECIBE = """\
mensaje Dato { n: numero desde 1 hasta 100, nota: texto }
mensaje Otro { n: numero }
mensaje Mandar { n: numero }
usar socio Socio acepta Dato
agente Caja {
    estado recordado suma = 0
    estado recordado vistos = []
    al recibir Dato como d {
        suma = suma + d.n
        vistos = agregar(vistos, d.n)
        mostrar("anotado {d.n}")
    }
    al recibir Mandar como m {
        enviar Dato { n: m.n, nota: "va" } a Socio
    }
    al fallar como f {
        suma = suma - f.mensaje.n
        mostrar("no anduvo {f.mensaje.n}: {f.motivo}")
    }
}
"""


def orden(capsys, monkeypatch, donde, *argumentos, respuestas=()):
    """Corre una orden de Mate parada en esa carpeta. Lo que se "teclea" sale de respuestas
    (cuando se acaban, es como si no hubiera teclado)."""
    cola = list(respuestas)

    def entrada(pregunta=""):
        print(pregunta)
        if not cola:
            raise EOFError
        return cola.pop(0)

    monkeypatch.setattr("builtins.input", entrada)
    monkeypatch.chdir(donde)
    capsys.readouterr()
    codigo = mate.main([str(a) for a in argumentos])
    capturado = capsys.readouterr()
    return codigo, capturado.out, capturado.err


def negocio(base, nombre, fuente, socio="Socio", lado="A", clave=CLAVE, compartida=None,
            **ficha):
    """Arma la carpeta de un negocio con su programa y su clave ya cargada."""
    carpeta = base / nombre
    carpeta.mkdir(exist_ok=True)
    (carpeta / f"{nombre}.mate").write_text(fuente, encoding="utf-8")
    compartida = compartida or base / "compartida"
    compartida.mkdir(exist_ok=True)
    for sub in ("de-a", "de-b"):
        (compartida / sub).mkdir(exist_ok=True)
    if clave:
        mate.guardar_socios(str(carpeta / f"{nombre}.mate"), {socio: dict(
            {"clave": clave, "lado": lado, "carpeta": str(compartida), "estrenado": False},
            **ficha)})
    return carpeta


def sobre_de(numero, mensaje=None, clave=CLAVE, lado="B", clase="mensaje", firmar=True,
             **cambios):
    """Un sobre como el que escribiría el otro negocio, firmado con esa clave."""
    identidad = f"20260101T000000-{'ab' * 10}-{numero:04d}"
    sobre = {"mate_buzon": 2, "id": identidad, "clase": clase,
             "de": {"programa": "otro", "agente": "Alguien"},
             "para": {"programa": "(socio)", "agente": "(socio)"},
             "conversacion": identidad, "en_respuesta_a": None,
             "cuando": "2026-01-01T00:00:00",
             "mensaje": mensaje or {"tipo": "Dato", "campos": {"n": numero, "nota": "hola"}},
             "socio": {"huella": mate.huella_de_clave(clave), "lado": lado, "numero": numero}}
    sobre.update(cambios)
    if firmar:
        sobre["firma"] = mate.firma_de_sobre(sobre, clave, lado)
    return sobre


def dejar(carpeta, sobre, nombre=None):
    if nombre is None and isinstance(sobre, str):
        nombre = "00000001-00000000.json"
    if nombre is None:
        nombre = f"{int(sobre['socio']['numero']) % 10 ** 8:08d}-{'0' * 8}.json"
    archivo = carpeta / nombre
    archivo.write_text(sobre if isinstance(sobre, str) else json.dumps(sobre),
                       encoding="utf-8")
    return archivo


def memoria(carpeta):
    archivo = carpeta / f"{carpeta.name}.memoria.json"
    if not archivo.exists():
        return {}
    return json.loads(archivo.read_text(encoding="utf-8-sig"))


def suma(carpeta):
    return memoria(carpeta).get("agentes", {}).get("Caja", {}).get("estado", {}).get("suma", 0)


def de_socio(carpeta, socio="Socio"):
    return memoria(carpeta).get("correo", {}).get("socios", {}).get(socio, {})


def sobres(carpeta):
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(carpeta.iterdir())
            if p.name.endswith(".json")]


def rechazados(carpeta):
    """{archivo: motivo} de lo que hay en 'rechazados' de ese negocio."""
    lugar = carpeta / f"{carpeta.name}.buzon" / "rechazados"
    if not lugar.is_dir():
        return {}
    return {p.name: p.read_text(encoding="utf-8-sig") for p in sorted(lugar.iterdir())
            if p.name.endswith(".motivo.txt")}


@pytest.fixture
def lugar(tmp_path):
    """Un negocio (lado A) que recibe Dato de su socio, y la carpeta compartida."""
    carpeta = negocio(tmp_path, "local", RECIBE)
    return carpeta, tmp_path / "compartida"


# ── 1. firma y formato ──
def test_vector_fijo_de_la_firma():
    """Los bytes que se firman y la firma de un sobre conocido no cambian entre versiones
    de Python ni entre versiones de Mate: si cambian, dos negocios dejan de entenderse."""
    assert mate.clave_de_socio_valida(CLAVE) == CLAVE
    assert mate.huella_de_clave(CLAVE) == "e07089c2"
    assert mate.control_de_socio(CLAVE) == "663 460"
    sobre = {
        "mate_buzon": 2, "id": "20260101T000000-abababababababababab-0001",
        "clase": "mensaje", "de": {"programa": "proveedor", "agente": "Ventas"},
        "para": {"programa": "(socio)", "agente": "(socio)"},
        "conversacion": "20260101T000000-abababababababababab-0001",
        "en_respuesta_a": None, "cuando": "2026-01-01T00:00:00",
        "mensaje": {"tipo": "Cotizacion", "campos": {
            "pedido": "A-17 ñandú", "emoji": "\U0001f9c9", "roto": "\ud800",
            "precio": 3500.5, "cero": -0.0, "hay": True, "nada": None,
            "lista": [1, {"x": [2.0, "y"]}]}},
        "socio": {"huella": "e07089c2", "lado": "B", "numero": 17}}
    assert mate.bytes_canonicos(sobre) == (
        b'mate-sobre-2\n{"clase":"mensaje","conversacion":"20260101T000000-abababababababab'
        b'abab-0001","cuando":"2026-01-01T00:00:00","de":{"agente":"Ventas","programa":"pro'
        b'veedor"},"en_respuesta_a":null,"id":"20260101T000000-abababababababababab-0001","'
        b'mate_buzon":2,"mensaje":{"campos":{"cero":-0.0,"emoji":"\\ud83e\\uddc9","hay":tru'
        b'e,"lista":[1,{"x":[2.0,"y"]}],"nada":null,"pedido":"A-17 \\u00f1and\\u00fa","prec'
        b'io":3500.5,"roto":"\\ud800"},"tipo":"Cotizacion"},"para":{"agente":"(socio)","pro'
        b'grama":"(socio)"},"socio":{"huella":"e07089c2","lado":"B","numero":17}}')
    assert mate.firma_de_sobre(sobre, CLAVE, "B") == (
        "b678b2e3e011b8bb123383f1715dc970da41c3c2eb1889d70b831beac64a8e52")
    # Cada lado firma con una clave derivada distinta: lo mismo, firmado por A, da otra.
    assert mate.firma_de_sobre(sobre, CLAVE, "A") == (
        "da7c5a9ce547a00935662a0a937b6feb0990f5b39f81647067303106537533b9")
    # La firma no entra en lo que se firma, y sobrevive a escribir y leer el archivo.
    firmado = dict(sobre, firma=mate.firma_de_sobre(sobre, CLAVE, "B"))
    assert mate.bytes_canonicos(firmado) == mate.bytes_canonicos(sobre)
    leido, repetidas = mate.json_de_sobre(json.dumps(firmado).encode("ascii"))
    assert not repetidas and mate.firma_de_sobre(leido, CLAVE, "B") == firmado["firma"]


def test_la_clave_tiene_44_cifras_y_el_control_detecta_un_error():
    clave = mate.nueva_clave_de_socio()
    assert len(clave) == 44 and clave.isdigit()
    assert mate.clave_de_socio_valida(mate.clave_en_grupos(clave)) == clave
    assert mate.clave_en_grupos(clave).count(" ") == 10
    for i in range(44):  # una cifra mal, en cualquier lugar, no pasa
        mala = clave[:i] + str((int(clave[i]) + 1) % 10) + clave[i + 1:]
        assert mate.clave_de_socio_valida(mala) is None
    for no_es in ("", "hola", clave[:-1], clave + "1", "la clave de mi socio", None, 5,
                  "١" * 44):
        assert mate.clave_de_socio_valida(no_es) is None
    assert mate.nueva_clave_de_socio() != clave


def test_ida_y_vuelta_completa_del_ejemplo_14(tmp_path, capsys, monkeypatch):
    """Dos carpetas que hacen de dos negocios y una tercera compartida: pedido, cotización,
    confirmación y aviso, cada paso con el si del dueño."""
    assert orden(capsys, monkeypatch, tmp_path, "nuevo", "socio")[0] == 0
    base = tmp_path / "ensayo_de_socios"
    comprador, proveedor, compartida = (base / n for n in
                                        ("comprador", "proveedor", "compartida"))
    codigo, salida, _ = orden(capsys, monkeypatch, comprador, "correr", "comprador.mate")
    assert codigo == 0 and "dejé 1 mensaje para Proveedor" in salida
    (pedido,) = sobres(compartida / "de-a")
    assert pedido["mate_buzon"] == 2 and pedido["socio"]["numero"] == 1
    assert pedido["mensaje"] == {"tipo": "Pedido", "campos": {
        "pedido": "A-17", "producto": "yerba", "cantidad": 10}}
    # El proveedor: sin el si no pasa nada; con el si, cotiza.
    codigo, salida, err = orden(capsys, monkeypatch, proveedor, "correr", "proveedor.mate")
    assert codigo == 0 and 'te manda Pedido { pedido: "A-17"' in salida
    assert "espera tu si" in err and sobres(compartida / "de-b") == []
    codigo, salida, _ = orden(capsys, monkeypatch, proveedor, "correr", "proveedor.mate",
                              respuestas=["si"])
    assert codigo == 0 and "entregué 1 mensaje de Cliente" in salida
    (cotizacion,) = sobres(compartida / "de-b")
    assert cotizacion["mensaje"]["campos"]["total"] == 35000
    assert cotizacion["en_respuesta_a"] == pedido["id"]
    assert sobres(compartida / "de-a") == []
    estado = memoria(proveedor)["agentes"]["Ventas"]["estado"]
    assert estado["stock"]["yerba"] == 40  # cotizar no descuenta
    # El comprador recibe la cotización (si) y recién en la corrida siguiente confirma.
    codigo, salida, _ = orden(capsys, monkeypatch, comprador, "correr", "comprador.mate",
                              respuestas=["si"])
    assert codigo == 0 and "total $ 35.000,00" in salida
    assert sobres(compartida / "de-a") == []
    codigo, salida, _ = orden(capsys, monkeypatch, comprador, "correr", "comprador.mate",
                              respuestas=["si"])
    assert codigo == 0 and "¿Confirmás el pedido A-17" in salida
    (confirmacion,) = sobres(compartida / "de-a")
    assert confirmacion["mensaje"] == {"tipo": "Confirmacion", "campos": {
        "pedido": "A-17", "total": 35000}}
    assert confirmacion["socio"]["numero"] == 2
    codigo, salida, _ = orden(capsys, monkeypatch, proveedor, "correr", "proveedor.mate",
                              respuestas=["si"])
    assert codigo == 0 and "Quedan 30" in salida
    assert memoria(proveedor)["agentes"]["Ventas"]["estado"]["stock"]["yerba"] == 30
    codigo, salida, _ = orden(capsys, monkeypatch, comprador, "correr", "comprador.mate",
                              respuestas=["si"])
    assert codigo == 0 and "confirmado por el proveedor" in salida
    pedidos = memoria(comprador)["agentes"]["Compras"]["estado"]["pedidos"]
    assert pedidos["A-17"]["estado"] == "confirmado"
    # No quedó nada en el camino, ni rechazado, ni pendiente.
    assert sobres(compartida / "de-a") == sobres(compartida / "de-b") == []
    for lado in (comprador, proveedor):
        assert rechazados(lado) == {}
        assert not list((lado / f"{lado.name}.buzon" / "pendientes").iterdir())
    # Y otra corrida de cada uno no repite nada.
    for lado in (comprador, proveedor):
        codigo, salida, _ = orden(capsys, monkeypatch, lado, "correr", f"{lado.name}.mate",
                                  respuestas=["si", "si"])
        assert codigo == 0 and "Socios:" not in salida
    assert sobres(compartida / "de-a") == sobres(compartida / "de-b") == []
    assert memoria(proveedor)["agentes"]["Ventas"]["estado"]["stock"]["yerba"] == 30


def _cambiado(donde, valor):
    def cambiar(sobre):
        destino = sobre
        for paso in donde[:-1]:
            destino = destino[paso]
        destino[donde[-1]] = valor
        return sobre
    return cambiar


def _sin_firma(sobre):
    del sobre["firma"]
    return sobre


@pytest.mark.parametrize("que, armar, motivo", [
    ("mensaje", _cambiado(("mensaje", "campos", "n"), 99), "la firma no es válida"),
    ("numero", _cambiado(("socio", "numero"), 8), "la firma no es válida"),
    ("para", _cambiado(("para", "agente"), "Otro"), "la firma no es válida"),
    ("clase", _cambiado(("clase",), "falla"), "la firma no es válida"),
    ("cuando", _cambiado(("cuando",), "2031-01-01T00:00:00"), "la firma no es válida"),
    ("sin firma", _sin_firma, "no trae firma"),
    ("firma rara", _cambiado(("firma",), "ñ" * 64), "no trae firma"),
    ("firma de otro largo", _cambiado(("firma",), "ab" * 31), "no trae firma"),
    ("numero imposible", _cambiado(("socio", "numero"), 2 ** 60), "número de orden"),
    ("numero con decimales", _cambiado(("socio", "numero"), 7.0), "número de orden"),
    ("version 1", _cambiado(("mate_buzon",), 1), "no es un sobre entre negocios"),
])
def test_un_sobre_alterado_no_se_entrega_ni_se_contesta(lugar, capsys, monkeypatch, que,
                                                        armar, motivo):
    local, compartida = lugar
    archivo = dejar(compartida / "de-b", armar(sobre_de(7)))
    codigo, salida, err = orden(capsys, monkeypatch, local, "correr", "local.mate",
                                respuestas=["si"] * 3)
    assert codigo == 0 and "¿Lo entrego?" not in salida and "anotado" not in salida
    assert suma(local) == 0
    assert not archivo.exists()  # (decía ser un sobre: se saca de la compartida)
    (dicho,) = rechazados(local).values()
    assert motivo in dicho and motivo in err
    assert sobres(compartida / "de-a") == []  # a quien no se autenticó no se le contesta
    assert de_socio(local)["vistos"] == {}  # y no cuenta como visto:
    dejar(compartida / "de-b", sobre_de(7))  # el 7 de verdad entra
    codigo, salida, _ = orden(capsys, monkeypatch, local, "correr", "local.mate",
                              respuestas=["si"])
    assert "anotado 7" in salida and suma(local) == 7


def test_otra_clave_mi_propio_sobre_y_claves_repetidas_se_rechazan(lugar, capsys,
                                                                    monkeypatch):
    local, compartida = lugar
    dejar(compartida / "de-b", sobre_de(1, clave=OTRA_CLAVE))  # otra clave (otra huella)
    con_mi_huella = sobre_de(2, clave=OTRA_CLAVE)
    con_mi_huella["socio"]["huella"] = mate.huella_de_clave(CLAVE)  # huella mía, firma no
    dejar(compartida / "de-b", con_mi_huella)
    dejar(compartida / "de-b", sobre_de(3, lado="A"))  # un sobre de MI lado, devuelto
    bueno = sobre_de(4)
    repetidas = json.dumps(bueno)[:-1] + ', "clase": "mensaje"}'  # una clave dos veces
    dejar(compartida / "de-b", repetidas, "00000004-00000000.json")
    codigo, salida, err = orden(capsys, monkeypatch, local, "correr", "local.mate",
                                respuestas=["si"] * 5)
    assert codigo == 0 and "¿Lo entrego?" not in salida and suma(local) == 0
    motivos = " ".join(rechazados(local).values())
    assert len(rechazados(local)) == 4
    assert "otra clave" in motivos and "la firma no es válida" in motivos
    assert "mi propio lado" in motivos and "claves repetidas" in motivos
    assert sobres(compartida / "de-a") == [] and sobres(compartida / "de-b") == []
    assert "Socios: 4 no se entregaron" in salida
    # Los rechazados llevan un nombre que arma Mate, no el del archivo ni el id ajenos.
    for nombre in rechazados(local):
        assert re.fullmatch(r"socio-e07089c2-\d{8}-\d{6}-[0-9a-f]{6}\.motivo\.txt", nombre)


def test_tipo_no_aceptado_y_contrato_roto_vuelven_como_falla_de_lista_cerrada(
        lugar, capsys, monkeypatch):
    local, compartida = lugar
    dejar(compartida / "de-b", sobre_de(1, {"tipo": "Otro", "campos": {"n": 1}}))
    dejar(compartida / "de-b", sobre_de(2, {"tipo": "Dato", "campos": {"n": 500,
                                                                      "nota": "x"}}))
    dejar(compartida / "de-b", sobre_de(3, {"tipo": "NoExiste", "campos": {}}))
    dejar(compartida / "de-b", sobre_de(4, {"tipo": "Dato", "campos": {
        "n": 5, "nota": "x" * 501}}))
    codigo, salida, err = orden(capsys, monkeypatch, local, "correr", "local.mate",
                                respuestas=["si"] * 5)
    assert codigo == 0 and "¿Lo entrego?" not in salida and suma(local) == 0
    assert "no acepto 'Otro' de Socio" in err and "no cumple el contrato" in err
    fallas = sobres(compartida / "de-a")
    assert [f["clase"] for f in fallas] == ["falla"] * 4
    assert [f["motivo"] for f in fallas] == ["no_acepto", "contrato", "no_acepto",
                                             "contrato"]
    assert fallas[1]["campo"] == "n" and "campo" not in fallas[0]
    assert [f["en_respuesta_a"] for f in fallas] == [
        sobre_de(n)["id"] for n in (1, 2, 3, 4)]
    for falla in fallas:  # van firmadas, y el motivo es un código: ningún texto de adentro
        assert set(falla) <= {"mate_buzon", "id", "clase", "de", "para", "conversacion",
                              "en_respuesta_a", "cuando", "mensaje", "motivo", "campo",
                              "socio", "firma"}
        assert falla["firma"] == mate.firma_de_sobre(falla, CLAVE, "A")
        assert falla["motivo"] in mate.MOTIVOS_DE_SOCIO
        assert "desde" not in json.dumps(falla) and "hasta" not in json.dumps(falla)
    assert fallas[3]["mensaje"] == {"tipo": "?", "campos": {}}  # (no se devuelve lo enorme)
    assert len(de_socio(local)["vistos"]) == 4  # se autenticaron: quedan vistos
    assert len(rechazados(local)) == 4


def test_una_falla_que_nombra_un_mensaje_que_no_mande_se_rechaza(lugar, capsys, monkeypatch):
    local, compartida = lugar
    (local / "local.mate").write_text(
        RECIBE + "enviar Mandar { n: 5 } a Caja\n", encoding="utf-8")
    assert orden(capsys, monkeypatch, local, "correr", "local.mate")[0] == 0
    (local / "local.mate").write_text(RECIBE, encoding="utf-8")
    (mandado,) = sobres(compartida / "de-a")
    inventada = sobre_de(1, mandado["mensaje"], clase="falla", motivo="descartado",
                         en_respuesta_a="20260101T000000-abababababababababab-9999")
    dejar(compartida / "de-b", inventada)
    codigo, salida, err = orden(capsys, monkeypatch, local, "correr", "local.mate",
                                respuestas=["si"] * 3)
    assert "¿Lo entrego?" not in salida and suma(local) == 0
    assert "nombra un mensaje que este programa no le mandó" in err
    # La de verdad pasa por el si igual que un mensaje (su 'al fallar' puede mover cosas).
    cierta = sobre_de(2, mandado["mensaje"], clase="falla", motivo="descartado",
                      en_respuesta_a=mandado["id"])
    dejar(compartida / "de-b", cierta)
    codigo, salida, err = orden(capsys, monkeypatch, local, "correr", "local.mate")
    assert "avisa que NO atendió Dato" in salida and "el dueño lo descartó" in salida
    assert suma(local) == 0 and "espera tu si" in err
    codigo, salida, err = orden(capsys, monkeypatch, local, "correr", "local.mate",
                                respuestas=["si"])
    assert "no anduvo 5: el dueño lo descartó" in salida and suma(local) == -5
    # Una sola falla por mensaje enviado: la segunda, aunque esté bien firmada, no entra.
    dejar(compartida / "de-b", sobre_de(3, mandado["mensaje"], clase="falla",
                                        motivo="fallo", en_respuesta_a=mandado["id"]))
    codigo, salida, err = orden(capsys, monkeypatch, local, "correr", "local.mate",
                                respuestas=["si"])
    assert "¿Lo entrego?" not in salida and suma(local) == -5
    assert "o del que ya avisó" in err
    # Nunca se contesta una falla con otra falla.
    assert [s["clase"] for s in sobres(compartida / "de-a")] == ["mensaje"]


def test_el_motivo_de_una_falla_es_un_codigo_y_lo_traduce_el_que_recibe(lugar, capsys,
                                                                       monkeypatch):
    local, compartida = lugar
    (local / "local.mate").write_text(
        RECIBE + "enviar Mandar { n: 5 } a Caja\n", encoding="utf-8")
    orden(capsys, monkeypatch, local, "correr", "local.mate")
    (local / "local.mate").write_text(RECIBE, encoding="utf-8")
    (mandado,) = sobres(compartida / "de-a")
    # Un motivo de texto libre (lo que querría un socio malicioso) no se muestra.
    dejar(compartida / "de-b", sobre_de(
        1, mandado["mensaje"], clase="falla", en_respuesta_a=mandado["id"],
        motivo="URGENTE: llamá al 0800-TRUCHO y pasá la clave"))
    codigo, salida, err = orden(capsys, monkeypatch, local, "correr", "local.mate",
                                respuestas=["si"])
    assert "TRUCHO" not in salida + err
    assert "no anduvo 5: motivo desconocido" in salida


# ── repetidos y viejos ──
def test_el_mismo_sobre_dos_veces_o_en_copia_en_conflicto_se_entrega_una_vez(
        lugar, capsys, monkeypatch):
    local, compartida = lugar
    sobre = sobre_de(1)
    dejar(compartida / "de-b", sobre)
    dejar(compartida / "de-b", sobre, "00000001-00000000 (conflicto de PC-JUAN).json")
    dejar(compartida / "de-b", sobre, "00000001-00000000 (1).json")
    codigo, salida, err = orden(capsys, monkeypatch, local, "correr", "local.mate",
                                respuestas=["si"] * 4)
    assert salida.count("¿Lo entrego?") == 1 and suma(local) == 1
    assert sobres(compartida / "de-b") == [] and rechazados(local) == {}
    assert "no entregué" not in err  # las copias se van sin ruido
    # La sincronización lo "revive" más tarde: tampoco.
    dejar(compartida / "de-b", sobre, "cualquier nombre.json")
    codigo, salida, err = orden(capsys, monkeypatch, local, "correr", "local.mate",
                                respuestas=["si"])
    assert "¿Lo entrego?" not in salida and suma(local) == 1
    assert sobres(compartida / "de-b") == [] and rechazados(local) == {}


def test_llegada_desordenada_se_entregan_los_dos_y_buzon_avisa_el_hueco(
        lugar, capsys, monkeypatch):
    local, compartida = lugar
    dejar(compartida / "de-b", sobre_de(3))
    orden(capsys, monkeypatch, local, "correr", "local.mate", respuestas=["si"])
    assert suma(local) == 3
    codigo, salida, _ = orden(capsys, monkeypatch, local, "buzon", "local.mate")
    assert "Faltan números de Socio: 1 a 2" in salida
    dejar(compartida / "de-b", sobre_de(2))
    orden(capsys, monkeypatch, local, "correr", "local.mate", respuestas=["si"])
    assert suma(local) == 5
    codigo, salida, _ = orden(capsys, monkeypatch, local, "buzon", "local.mate")
    assert "Faltan números de Socio: 1 (" in salida


def test_los_huecos_van_en_rangos_y_con_tope():
    assert mate.huecos_de_socio({"piso": 0, "vistos": {}}) == []
    assert mate.huecos_de_socio({"piso": 0, "vistos": {"1": "", "2": ""}}) == []
    assert mate.huecos_de_socio({"piso": 2, "vistos": {"4": "", "9": ""}}) == ["3", "5 a 8"]
    # Un socio que manda el 10^15 no cuelga nada: es un rango, no una lista.
    assert mate.huecos_de_socio({"piso": 0, "vistos": {"1": "", str(10 ** 15): ""}}) == [
        f"2 a {10 ** 15 - 1}"]
    muchos = {str(n): "" for n in range(2, 60, 2)}
    assert mate.huecos_de_socio({"piso": 0, "vistos": muchos}) == [
        "1", "3", "5", "7", "9", "..."]


def test_mismo_numero_con_otro_contenido_y_por_debajo_del_piso(lugar, capsys, monkeypatch):
    local, compartida = lugar
    monkeypatch.setattr(mate, "MAX_VISTOS", 3)
    for n in (1, 2, 3, 4, 5):
        dejar(compartida / "de-b", sobre_de(n))
    orden(capsys, monkeypatch, local, "correr", "local.mate", respuestas=["si"] * 5)
    assert suma(local) == 15
    estado = de_socio(local)
    assert estado["piso"] == 2 and sorted(estado["vistos"]) == ["3", "4", "5"]
    # El 4 otra vez, con OTRO contenido: aviso fuerte, y no se entrega.
    dejar(compartida / "de-b", sobre_de(4, {"tipo": "Dato", "campos": {"n": 90,
                                                                      "nota": "x"}}))
    # El 1 (por debajo del piso, ya olvidado): tampoco, y se avisa (no se borra callado).
    dejar(compartida / "de-b", sobre_de(1))
    codigo, salida, err = orden(capsys, monkeypatch, local, "correr", "local.mate",
                                respuestas=["si"] * 3)
    assert "¿Lo entrego?" not in salida and suma(local) == 15
    assert "repitió un número" in err and "renueven la clave" in err
    assert "llegó tarde el 1 de Socio y ya no se acepta" in err
    assert len(rechazados(local)) == 2 and sobres(compartida / "de-b") == []
    assert sobres(compartida / "de-a") == []


@pytest.mark.parametrize("cuando", ["2001-01-01T00:00:00", "2099-12-31T23:59:59",
                                    "cualquier cosa", None])
def test_el_reloj_del_socio_no_decide_nada(lugar, capsys, monkeypatch, cuando):
    local, compartida = lugar
    dejar(compartida / "de-b", sobre_de(1, cuando=cuando))
    codigo, salida, _ = orden(capsys, monkeypatch, local, "correr", "local.mate",
                              respuestas=["si"])
    assert suma(local) == 1 and "según el reloj de tu socio" in salida


def test_memoria_borrada_con_la_clave_ya_usada_pide_renovar(tmp_path, capsys, monkeypatch):
    local = negocio(tmp_path, "local", RECIBE + "enviar Mandar { n: 5 } a Caja\n")
    compartida = tmp_path / "compartida"
    dejar(compartida / "de-b", sobre_de(1))
    orden(capsys, monkeypatch, local, "correr", "local.mate", respuestas=["si"])
    assert suma(local) == 1 and len(sobres(compartida / "de-a")) == 1
    assert mate.leer_socios(str(local / "local.mate"))[0]["Socio"]["estrenado"] is True
    # Se pierde la memoria (o se restaura una copia de antes de usar la clave).
    (local / "local.memoria.json").unlink()
    for viejo in (compartida / "de-a").iterdir():
        viejo.unlink()
    dejar(compartida / "de-b", sobre_de(1))  # lo ya entregado, otra vez
    dejar(compartida / "de-b", sobre_de(2))
    codigo, salida, err = orden(capsys, monkeypatch, local, "correr", "local.mate",
                                respuestas=["si"] * 3)
    assert "se perdió la cuenta de los mensajes con Socio" in err
    assert "socio renovar local.mate Socio" in err
    assert "¿Lo entrego?" not in salida and suma(local) == 0
    assert sobres(compartida / "de-a") == []  # no manda: repetiría el número 1
    assert len(sobres(compartida / "de-b")) == 2  # y no toca lo que llegó
    assert len(de_socio(local)["en_espera"]) == 1  # lo que quiso mandar queda anotado
    # Después de renovar, lo viejo ya no entra: es de otra clave.
    codigo, salida, err = orden(capsys, monkeypatch, local, "socio", "renovar",
                                "local.mate", "Socio", f"--invitacion={tmp_path}",
                                respuestas=["si"])
    assert codigo == 0, err
    nueva = mate.leer_socios(str(local / "local.mate"))[0]["Socio"]["clave"]
    assert nueva != CLAVE and nueva not in salida + err
    codigo, salida, err = orden(capsys, monkeypatch, local, "correr", "local.mate",
                                respuestas=["si"] * 3)
    assert "¿Lo entrego?" not in salida and suma(local) == 0
    assert len(rechazados(local)) == 2 and "otra clave" in err
    salidos = sobres(compartida / "de-a")  # lo anotado sale, con la clave nueva y desde 1
    assert [s["socio"]["numero"] for s in salidos] == [1, 2]
    assert all(s["firma"] == mate.firma_de_sobre(s, nueva, "A") for s in salidos)


# ── la carpeta compartida ──
def test_un_archivo_a_medio_llegar_se_deja_y_se_entrega_cuando_se_completa(
        lugar, capsys, monkeypatch):
    local, compartida = lugar
    entero = json.dumps(sobre_de(1))
    archivo = dejar(compartida / "de-b", entero[:len(entero) // 2])
    codigo, salida, err = orden(capsys, monkeypatch, local, "correr", "local.mate",
                                respuestas=["si"])
    assert codigo == 0 and "todavía no se entiende" in err
    assert archivo.exists() and rechazados(local) == {} and suma(local) == 0
    assert len(de_socio(local)["rotos"]) == 1
    archivo.write_text(entero, encoding="utf-8")  # terminó de llegar
    codigo, salida, err = orden(capsys, monkeypatch, local, "correr", "local.mate",
                                respuestas=["si"])
    assert suma(local) == 1 and not archivo.exists()
    assert de_socio(local)["rotos"] == {}


def test_un_archivo_que_sigue_roto_un_dia_va_a_rechazados(lugar, capsys, monkeypatch):
    local, compartida = lugar
    ahora = [1_800_000_000]
    monkeypatch.setattr(mate, "reloj_local", lambda: ahora[0])
    archivo = dejar(compartida / "de-b", '{"mate_buzon": 2, "id": "a medio')
    # La fecha del archivo no cuenta (viene de otra máquina): cuenta desde que ESTA lo vio.
    os.utime(archivo, (1_000_000_000, 1_000_000_000))
    orden(capsys, monkeypatch, local, "correr", "local.mate")
    assert rechazados(local) == {} and archivo.exists()
    ahora[0] += 23 * 3600
    orden(capsys, monkeypatch, local, "correr", "local.mate")
    assert rechazados(local) == {} and archivo.exists()
    ahora[0] += 2 * 3600
    codigo, salida, err = orden(capsys, monkeypatch, local, "correr", "local.mate")
    (motivo,) = rechazados(local).values()
    assert "lleva más de un día" in motivo
    # No se autenticó: Mate no lo borra de la compartida, y no lo rechaza dos veces.
    assert archivo.exists()
    orden(capsys, monkeypatch, local, "correr", "local.mate")
    assert len(rechazados(local)) == 1


def test_lo_que_no_es_un_sobre_no_cuelga_ni_se_sigue_ni_se_borra(lugar, capsys,
                                                                 monkeypatch, tmp_path):
    local, compartida = lugar
    entrada = compartida / "de-b"
    (entrada / "00000009-ab.json.tmp").write_text("a medio escribir", encoding="utf-8")
    (entrada / "carpeta.json").mkdir()
    (entrada / "foto.jpg").write_bytes(b"\xff\xd8")
    (entrada / "pesado.json").write_bytes(b" " * (mate.MAX_SOBRE + 10))
    (entrada / "ajeno.json").write_text('{"de": "otro programa"}', encoding="utf-8")
    del_dueno = tmp_path / "del_dueno.json"
    del_dueno.write_text(json.dumps(sobre_de(1)), encoding="utf-8")
    try:
        (entrada / "00000001-00000000.json").symlink_to(del_dueno)
    except (OSError, NotImplementedError):
        pytest.skip("acá no se pueden crear accesos directos")
    antes = sorted(p.name for p in entrada.iterdir())
    codigo, salida, err = orden(capsys, monkeypatch, local, "correr", "local.mate",
                                respuestas=["si"] * 3)
    assert codigo == 0 and "¿Lo entrego?" not in salida and suma(local) == 0
    assert sorted(p.name for p in entrada.iterdir()) == antes
    assert del_dueno.exists() and rechazados(local) == {}
    assert "no lo abro, no lo sigo y no lo borro" in err


def test_de_b_cambiada_por_un_acceso_directo_no_se_sigue(lugar, capsys, monkeypatch,
                                                         tmp_path):
    local, compartida = lugar
    del_dueno = tmp_path / "papeles"
    del_dueno.mkdir()
    dejar(del_dueno, sobre_de(1, firmar=False))  # un .json del dueño, en otra carpeta
    (compartida / "de-b").rmdir()
    try:
        (compartida / "de-b").symlink_to(del_dueno, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("acá no se pueden crear accesos directos")
    codigo, salida, err = orden(capsys, monkeypatch, local, "correr", "local.mate",
                                respuestas=["si"])
    assert codigo == 0 and "no es una carpeta de verdad" in err
    assert len(list(del_dueno.iterdir())) == 1 and rechazados(local) == {}


def test_carpeta_compartida_ausente_queda_por_salir_y_sale_despues(tmp_path, capsys,
                                                                  monkeypatch):
    local = negocio(tmp_path, "local", RECIBE + "enviar Mandar { n: 5 } a Caja\n")
    compartida = tmp_path / "compartida"
    aparte = tmp_path / "pendrive_sacado"
    compartida.rename(aparte)
    codigo, salida, err = orden(capsys, monkeypatch, local, "correr", "local.mate")
    assert codigo == 0 and "no veo la carpeta compartida con Socio" in err
    (por_salir,) = de_socio(local)["por_salir"]
    assert por_salir["socio"]["numero"] == 1 and "firma" in por_salir
    codigo, salida, _ = orden(capsys, monkeypatch, local, "buzon", "local.mate")
    assert "NO se ve ahora" in salida and "Por salir: 1 mensaje" in salida
    aparte.rename(compartida)
    (local / "local.mate").write_text(RECIBE, encoding="utf-8")
    codigo, salida, err = orden(capsys, monkeypatch, local, "correr", "local.mate")
    assert "dejé 1 mensaje para Socio" in salida
    (salido,) = sobres(compartida / "de-a")
    assert salido == por_salir and de_socio(local)["por_salir"] == []


def test_un_corte_entre_copiar_a_pendientes_y_guardar_no_duplica(lugar, capsys,
                                                                 monkeypatch):
    local, compartida = lugar
    sobre = sobre_de(1)
    dejar(compartida / "de-b", sobre)
    # La corrida anterior copió a 'pendientes' y murió antes de guardar la memoria.
    pendientes = local / "local.buzon" / "pendientes"
    pendientes.mkdir(parents=True)
    (pendientes / "se07089c2-00000001.json").write_text(json.dumps(sobre), encoding="utf-8")
    codigo, salida, _ = orden(capsys, monkeypatch, local, "correr", "local.mate",
                              respuestas=["si", "si"])
    assert salida.count("¿Lo entrego?") == 1 and suma(local) == 1
    assert list(pendientes.iterdir()) == [] and sobres(compartida / "de-b") == []


def test_un_corte_despues_de_guardar_y_antes_de_borrar_no_entrega_dos_veces(
        lugar, capsys, monkeypatch):
    local, compartida = lugar
    sobre = sobre_de(1)
    dejar(compartida / "de-b", sobre)
    pendientes = local / "local.buzon" / "pendientes"
    de_verdad = mate.Socios.acomodar
    guardado = {}

    def se_corta(self):  # la memoria ya se guardó; se "corta la luz" antes de borrar
        guardado["pendiente"] = [p.read_bytes() for p in pendientes.iterdir()]

    monkeypatch.setattr(mate.Socios, "acomodar", se_corta)
    orden(capsys, monkeypatch, local, "correr", "local.mate", respuestas=["si"])
    assert suma(local) == 1 and len(guardado["pendiente"]) == 1
    assert len(list(pendientes.iterdir())) == 1  # quedó el archivo, ya entregado
    assert len(sobres(compartida / "de-b")) == 1  # y el de la compartida
    monkeypatch.setattr(mate.Socios, "acomodar", de_verdad)
    codigo, salida, _ = orden(capsys, monkeypatch, local, "correr", "local.mate",
                              respuestas=["si", "si"])
    assert "¿Lo entrego?" not in salida and suma(local) == 1  # ni pregunta
    assert list(pendientes.iterdir()) == [] and sobres(compartida / "de-b") == []
    assert rechazados(local) == {}


def test_mate_se_niega_si_la_compartida_es_contiene_o_esta_en_la_del_programa(
        tmp_path, capsys, monkeypatch):
    local = tmp_path / "local"
    local.mkdir()
    (local / "local.mate").write_text(RECIBE, encoding="utf-8")
    (local / "adentro").mkdir()
    con_programa = tmp_path / "con_programa"
    con_programa.mkdir()
    (con_programa / "otro.mate").write_text("mostrar(1)\n", encoding="utf-8")
    con_clave = tmp_path / "con_clave"
    con_clave.mkdir()
    (con_clave / "x.SOCIOS.json").write_text("{}", encoding="utf-8")
    for carpeta in (local, local / "adentro", tmp_path, con_programa, con_clave):
        codigo, salida, err = orden(
            capsys, monkeypatch, local, "socio", "invitar", "local.mate", "Socio",
            f"--carpeta={carpeta}", f"--invitacion={tmp_path}")
        assert codigo == 2 and "no uso esa carpeta" in err, carpeta
        assert not (local / "local.socios.json").exists()
        assert not (tmp_path / "invitacion-mate.txt").exists()
    # Y en cada corrida, no solo al invitar: si la carpeta anotada dejó de servir.
    negocio(tmp_path, "local", RECIBE + "enviar Mandar { n: 5 } a Caja\n",
            compartida=local / "adentro")
    codigo, salida, err = orden(capsys, monkeypatch, local, "correr", "local.mate")
    assert codigo == 0 and "con el socio Socio no mando ni recibo nada" in err
    assert sobres(local / "adentro" / "de-a") == []
    assert len(de_socio(local)["en_espera"]) == 1


# ── la clave ──
@pytest.mark.skipif(os.name == "nt", reason="en Windows quedan los permisos de la carpeta")
def test_el_archivo_de_claves_nace_cerrado_y_no_se_pisa_sin_renovar(tmp_path, capsys,
                                                                    monkeypatch):
    local = tmp_path / "local"
    local.mkdir()
    (local / "local.mate").write_text(RECIBE, encoding="utf-8")
    compartida = tmp_path / "compartida"
    compartida.mkdir()
    pendrive = tmp_path / "pendrive"
    pendrive.mkdir()
    viejo = os.umask(0)  # aunque el sistema deje todo abierto
    try:
        codigo, salida, err = orden(
            capsys, monkeypatch, local, "socio", "invitar", "local.mate", "Socio",
            f"--carpeta={compartida}", f"--invitacion={pendrive}")
    finally:
        os.umask(viejo)
    assert codigo == 0, err
    archivo = local / "local.socios.json"
    assert archivo.stat().st_mode & 0o777 == 0o600
    assert (pendrive / "invitacion-mate.txt").stat().st_mode & 0o777 == 0o600
    assert [p.name for p in local.iterdir() if p.name.endswith(".tmp")] == []
    clave = mate.leer_socios(str(local / "local.mate"))[0]["Socio"]["clave"]
    # Otra vez 'invitar': no pisa la que hay.
    codigo, salida, err = orden(
        capsys, monkeypatch, local, "socio", "invitar", "local.mate", "Socio",
        f"--carpeta={compartida}", f"--invitacion={tmp_path}")
    assert codigo == 1 and "no la piso" in err and "socio renovar" in err
    assert mate.leer_socios(str(local / "local.mate"))[0]["Socio"]["clave"] == clave
    # 'renovar' sin el si tampoco; con el si, sí, y el archivo sigue cerrado.
    codigo, salida, err = orden(
        capsys, monkeypatch, local, "socio", "renovar", "local.mate", "Socio",
        f"--invitacion={tmp_path}", respuestas=["no"])
    assert codigo == 1
    assert mate.leer_socios(str(local / "local.mate"))[0]["Socio"]["clave"] == clave
    codigo, salida, err = orden(
        capsys, monkeypatch, local, "socio", "renovar", "local.mate", "Socio",
        f"--invitacion={tmp_path}", respuestas=["si"])
    assert codigo == 0
    assert mate.leer_socios(str(local / "local.mate"))[0]["Socio"]["clave"] != clave
    assert archivo.stat().st_mode & 0o777 == 0o600


def _todo_lo_escrito(base):
    """El contenido de cada archivo que hay ahí abajo, menos los que guardan la clave."""
    partes = []
    for p in sorted(base.rglob("*")):
        if p.is_file() and not mate.es_archivo_de_clave(str(p)):
            partes.append(p.read_bytes().decode("utf-8", "replace"))
            partes.append(p.name)
    return "\n".join(partes)


def test_la_clave_no_aparece_en_nada_de_lo_que_escribe_una_corrida_completa(
        tmp_path, capsys, monkeypatch):
    registro = tmp_path / "errores_de_uso.txt"
    visto = []

    def con_registro(donde, *argumentos, respuestas=()):
        cola = list(respuestas)

        def entrada(pregunta=""):
            print(pregunta)
            if not cola:
                raise EOFError
            return cola.pop(0)

        monkeypatch.setattr("builtins.input", entrada)
        monkeypatch.chdir(donde)
        monkeypatch.delenv("MATE_SIN_REGISTRO", raising=False)
        codigo = mate.main([str(a) for a in argumentos], registro=str(registro))
        capturado = capsys.readouterr()
        visto.append(capturado.out + capturado.err)
        return codigo, capturado.out, capturado.err

    assert con_registro(tmp_path, "nuevo", "socio")[0] == 0
    base = tmp_path / "ensayo_de_socios"
    comprador, proveedor = base / "comprador", base / "proveedor"
    clave = mate.leer_socios(str(comprador / "comprador.mate"))[0]["Proveedor"]["clave"]
    assert mate.leer_socios(str(proveedor / "proveedor.mate"))[0]["Cliente"]["clave"] == clave
    con_registro(comprador, "correr", "comprador.mate", "--traza")
    con_registro(proveedor, "correr", "proveedor.mate", "--traza=charla.txt",
                 respuestas=["si"])
    con_registro(comprador, "correr", "comprador.mate", "--traza", respuestas=["no"])
    con_registro(proveedor, "correr", "proveedor.mate", "--traza", "--depurar")
    for lado in (comprador, proveedor):
        con_registro(lado, "buzon", f"{lado.name}.mate")
        con_registro(lado, "verificar", f"{lado.name}.mate")
    # Errores provocados a propósito, y de los que nombran el archivo de la clave.
    assert con_registro(comprador, "correr", "comprador.socios.json")[0] != 0
    assert con_registro(comprador, "verificar", "comprador.socios.json")[0] != 0
    (comprador / "roto.mate").write_text(
        'usar "comprador.socios.json"\nmostrar(leer_archivo("comprador.socios.json"))\n',
        encoding="utf-8")
    assert con_registro(comprador, "correr", "roto.mate")[0] != 0
    (comprador / "roto2.mate").write_text(
        'mostrar(leer_archivo("comprador.socios.json"))\n'
        'mostrar(leer_tabla("COMPRADOR.SOCIOS.JSON"))\n', encoding="utf-8")
    assert con_registro(comprador, "correr", "roto2.mate")[0] != 0
    assert con_registro(comprador, "socio", "invitar", "comprador.mate", "Proveedor")[0] == 1
    assert con_registro(comprador, "socio", "aceptar", "comprador.mate", "Nadie")[0] == 2
    con_registro(comprador, "informe")
    con_registro(comprador, "informe", "--para-mejorar")
    todo = "\n".join(visto) + _todo_lo_escrito(tmp_path)
    assert registro.exists()
    for forma in (clave, mate.clave_en_grupos(clave), clave[:12], clave[-12:],
                  mate.clave_en_grupos(clave)[:14]):
        assert forma not in todo
    # ...y tampoco lo que se deriva de ella para firmar.
    for lado in ("A", "B"):
        assert mate._derivada(clave, "firma " + lado).hex() not in todo
    assert mate.control_de_socio(clave) in todo  # (el número de control sí: es para eso)


def test_las_funciones_de_archivos_y_las_ordenes_se_niegan_sobre_la_clave(
        lugar, capsys, monkeypatch):
    local, _ = lugar
    (local / "invitacion-mate.txt").write_text("clave: 1", encoding="utf-8")
    try:
        (local / "notas.txt").symlink_to(local / "local.socios.json")
        con_enlace = ['leer_archivo("notas.txt")']
    except (OSError, NotImplementedError):
        con_enlace = []
    intentos = [
        'leer_archivo("local.socios.json")', 'leer_tabla("local.socios.json")',
        'escribir_archivo("local.socios.json", "x")',
        'agregar_a_archivo("local.socios.json", "x")',
        'leer_archivo("LOCAL.SOCIOS.JSON")', 'leer_archivo("local.socios.json.")',
        'leer_archivo("local.socios.json ")', 'leer_archivo("local.socios.json::$DATA")',
        'leer_archivo("./local.socios.json")', 'escribir_archivo("otro.socios.json", "x")',
        'leer_archivo("invitacion-mate.txt")', 'leer_archivo("local.socios.json.1-ab.tmp")',
    ] + con_enlace
    antes = (local / "local.socios.json").read_bytes()
    for intento in intentos:
        (local / "espia.mate").write_text(f"mostrar({intento})\n", encoding="utf-8")
        codigo, salida, err = orden(capsys, monkeypatch, local, "correr", "espia.mate")
        assert codigo == 1 and "guarda la clave de un socio" in err, intento
        assert CLAVE not in salida + err and CLAVE[:10] not in salida + err
    assert (local / "local.socios.json").read_bytes() == antes
    assert not (local / "otro.socios.json").exists()
    for argumentos in (("correr", "local.socios.json"), ("verificar", "local.socios.json"),
                       ("probar", "local.socios.json")):
        codigo, salida, err = orden(capsys, monkeypatch, local, *argumentos)
        assert codigo != 0 and CLAVE[:10] not in salida + err
        assert "guarda la clave de un socio" in err
    (local / "trae.mate").write_text('usar "local.socios.json"\n', encoding="utf-8")
    codigo, salida, err = orden(capsys, monkeypatch, local, "correr", "trae.mate")
    assert codigo != 0 and CLAVE[:10] not in salida + err
    # La traza tampoco se guarda ahí.
    codigo, salida, err = orden(capsys, monkeypatch, local, "correr", "local.mate",
                                "--traza=local.socios.json")
    assert (local / "local.socios.json").read_bytes() == antes


def test_invitar_y_aceptar_con_pendrive(tmp_path, capsys, monkeypatch):
    a = tmp_path / "a"
    b = tmp_path / "b"
    for carpeta, nombre in ((a, "uno"), (b, "dos")):
        carpeta.mkdir()
        (carpeta / f"{nombre}.mate").write_text(RECIBE, encoding="utf-8")
    compartida = tmp_path / "compartida"
    compartida.mkdir()
    pendrive = tmp_path / "pendrive"
    pendrive.mkdir()
    # La invitación no se escribe en la carpeta compartida (ni adentro).
    for adentro in (compartida, compartida / "de-a"):
        adentro.mkdir(exist_ok=True)
        codigo, salida, err = orden(
            capsys, monkeypatch, a, "socio", "invitar", "uno.mate", "Socio",
            f"--carpeta={compartida}", f"--invitacion={adentro}")
        assert codigo == 2 and "no va en la carpeta compartida" in err
        assert not (a / "uno.socios.json").exists()
        assert not list(compartida.rglob("invitacion*"))
    codigo, salida, err = orden(
        capsys, monkeypatch, a, "socio", "invitar", "uno.mate", "Socio",
        f"--carpeta={compartida}", f"--invitacion={pendrive}")
    assert codigo == 0, err
    invitacion = pendrive / "invitacion-mate.txt"
    texto = invitacion.read_text(encoding="utf-8")
    primero, version, de_clave = texto.splitlines()
    assert "NO MANDES ESTE ARCHIVO POR MAIL NI POR WHATSAPP" in primero
    assert version == "mate-invitacion: 1" and de_clave.startswith("clave: ")
    assert str(tmp_path) not in texto  # nada de rutas ni de otros datos
    clave = mate.leer_socios(str(a / "uno.mate"))[0]["Socio"]["clave"]
    assert clave not in salida + err and mate.clave_en_grupos(clave) not in salida + err
    control = mate.control_de_socio(clave)
    assert f"Número de control: {control}" in salida
    assert "OBLIGATORIO: llamá a tu socio y comparen el número de control" in salida
    assert sorted(p.name for p in compartida.iterdir()) == ["LEEME-mate.txt", "de-a", "de-b"]
    # El otro lado: la carga, la invitación se borra y ve el mismo número de control.
    codigo, salida, err = orden(
        capsys, monkeypatch, b, "socio", "aceptar", "dos.mate", "Socio",
        f"--carpeta={compartida}", f"--invitacion={pendrive}")
    assert codigo == 0, err
    assert not invitacion.exists() and "Borré la invitación" in salida
    assert f"Número de control: {control}" in salida and clave not in salida + err
    ficha_a = mate.leer_socios(str(a / "uno.mate"))[0]["Socio"]
    ficha_b = mate.leer_socios(str(b / "dos.mate"))[0]["Socio"]
    assert (ficha_a["lado"], ficha_b["lado"]) == ("A", "B")
    assert ficha_a["clave"] == ficha_b["clave"]
    # Y se hablan: A le manda a B, B lo recibe con su si.
    (a / "uno.mate").write_text(RECIBE + "enviar Mandar { n: 5 } a Caja\n", encoding="utf-8")
    assert orden(capsys, monkeypatch, a, "correr", "uno.mate")[0] == 0
    codigo, salida, _ = orden(capsys, monkeypatch, b, "correr", "dos.mate",
                              respuestas=["si"])
    assert "anotado 5" in salida


def test_aceptar_no_borra_lo_que_no_entiende_ni_carga_una_clave_mal(tmp_path, capsys,
                                                                    monkeypatch):
    b = tmp_path / "b"
    b.mkdir()
    (b / "dos.mate").write_text(RECIBE, encoding="utf-8")
    compartida = tmp_path / "compartida"
    compartida.mkdir()
    mala = CLAVE[:20] + str((int(CLAVE[20]) + 1) % 10) + CLAVE[21:]
    casos = {
        "una cifra mal": f"aviso\nmate-invitacion: 1\nclave: {mate.clave_en_grupos(mala)}\n",
        "otra versión": f"aviso\nmate-invitacion: 9\nclave: {mate.clave_en_grupos(CLAVE)}\n",
        "otra cosa": "la lista del súper\n",
    }
    for que, texto in casos.items():
        invitacion = tmp_path / "invitacion-mate.txt"
        invitacion.write_text(texto, encoding="utf-8")
        codigo, salida, err = orden(
            capsys, monkeypatch, b, "socio", "aceptar", "dos.mate", "Socio",
            f"--carpeta={compartida}", f"--invitacion={invitacion}")
        assert codigo == 2 and "no es una invitación de Mate entera" in err, que
        assert invitacion.exists() and not (b / "dos.socios.json").exists()
        assert CLAVE[:10] not in salida + err
    # Un acceso directo con nombre de invitación no se sigue (ni se borra a donde lleva).
    invitacion.unlink()
    de_verdad = tmp_path / "otro.txt"
    de_verdad.write_text(
        f"x\nmate-invitacion: 1\nclave: {mate.clave_en_grupos(CLAVE)}\n", encoding="utf-8")
    try:
        invitacion.symlink_to(de_verdad)
    except (OSError, NotImplementedError):
        return
    codigo, salida, err = orden(
        capsys, monkeypatch, b, "socio", "aceptar", "dos.mate", "Socio",
        f"--carpeta={compartida}", f"--invitacion={invitacion}")
    assert codigo == 2 and de_verdad.exists() and not (b / "dos.socios.json").exists()


def test_dictar_la_clave_solo_en_una_ventana_y_tipearla_solo_oculta(tmp_path, capsys,
                                                                   monkeypatch):
    a, b = tmp_path / "a", tmp_path / "b"
    for carpeta, nombre in ((a, "uno"), (b, "dos")):
        carpeta.mkdir()
        (carpeta / f"{nombre}.mate").write_text(RECIBE, encoding="utf-8")
    compartida = tmp_path / "compartida"
    compartida.mkdir()
    # Con la salida redirigida (acá lo está: la captura pytest), --dictar se niega.
    codigo, salida, err = orden(capsys, monkeypatch, a, "socio", "invitar", "uno.mate",
                                "Socio", f"--carpeta={compartida}", "--dictar")
    assert codigo == 2 and "solo en una ventana de verdad" in err
    assert not (a / "uno.socios.json").exists()
    # En una ventana de verdad la muestra, una vez, en grupos de 4.
    monkeypatch.chdir(a)
    mostrado = []
    assert mate.orden_socio(["invitar", "uno.mate", "Socio", f"--carpeta={compartida}",
                             "--dictar"], mostrado.append, mostrado.append,
                            es_terminal=lambda: True) == 0
    clave = mate.leer_socios(str(a / "uno.mate"))[0]["Socio"]["clave"]
    assert sum(mate.clave_en_grupos(clave) in renglon for renglon in mostrado) == 1
    control = mate.control_de_socio(clave)
    assert any(control in renglon for renglon in mostrado)
    # Del otro lado: si acá no se puede ocultar lo que se tipea, no se pide.
    codigo, salida, err = orden(capsys, monkeypatch, b, "socio", "aceptar", "dos.mate",
                                "Socio", f"--carpeta={compartida}", "--dictar")
    assert codigo == 2 and "no puedo ocultar lo que se tipea" in err
    assert not (b / "dos.socios.json").exists()
    with pytest.raises(mate.ErrorMate):
        mate.pedir_oculto("clave: ")
    # Con una cifra mal, el control la rechaza; bien tipeada (con espacios), entra.
    monkeypatch.chdir(b)
    mostrado = []
    mala = clave[:5] + str((int(clave[5]) + 1) % 10) + clave[6:]
    assert mate.orden_socio(["aceptar", "dos.mate", "Socio", f"--carpeta={compartida}",
                             "--dictar"], mostrado.append, mostrado.append,
                            oculto=lambda _: mala) == 2
    assert any("esa clave no cierra" in r for r in mostrado)
    assert not (b / "dos.socios.json").exists()
    for frase in ("la clave de mi socio", "1234", ""):
        assert mate.orden_socio(["aceptar", "dos.mate", "Socio", f"--carpeta={compartida}",
                                 "--dictar"], mostrado.append, mostrado.append,
                                oculto=lambda _, frase=frase: frase) == 2
    mostrado = []
    assert mate.orden_socio(["aceptar", "dos.mate", "Socio", f"--carpeta={compartida}",
                             "--dictar"], mostrado.append, mostrado.append,
                            oculto=lambda _: mate.clave_en_grupos(clave)) == 0
    assert any(control in renglon for renglon in mostrado)  # los dos ven el mismo control
    assert not any(clave in r or mate.clave_en_grupos(clave) in r for r in mostrado)
    assert mate.leer_socios(str(b / "dos.mate"))[0]["Socio"]["lado"] == "B"


def test_la_orden_socio_dice_como_seguir_cuando_algo_falta(tmp_path, capsys, monkeypatch):
    (tmp_path / "p.mate").write_text(RECIBE, encoding="utf-8")
    (tmp_path / "sin.mate").write_text('mostrar("hola")\n', encoding="utf-8")
    compartida = tmp_path / "compartida"
    compartida.mkdir()
    lugar = tmp_path / "trabajo"
    lugar.mkdir()
    for nombre in ("p.mate", "sin.mate"):
        (lugar / nombre).write_text((tmp_path / nombre).read_text(encoding="utf-8"),
                                    encoding="utf-8")
    for argumentos, codigo_esperado, dice in (
            (("socio",), 2, "lleva qué hacer"),
            (("socio", "invitar"), 2, "lleva qué hacer"),
            (("socio", "bailar", "p.mate", "Socio"), 2, "lleva qué hacer"),
            (("socio", "invitar", "no_esta.mate", "Socio"), 2, "no encuentro"),
            (("socio", "invitar", "p.mate", "Nadie"), 2, "no declara ningún socio 'Nadie'"),
            (("socio", "invitar", "sin.mate", "Socio"), 2, "usar socio Socio acepta"),
            (("socio", "invitar", "p.mate", "Socio", "--clave=123"), 2,
             "La clave nunca va en la orden"),
            (("socio", "renovar", "p.mate", "Socio"), 1, "no hay ninguna clave cargada"),
            (("socio", "quitar", "p.mate", "Socio"), 1, "no hay nada que quitar"),
            (("socio", "invitar", "p.mate", "Socio"), 2, "falta la carpeta compartida"),
            (("socio", "invitar", "p.mate", "Socio", f"--carpeta={tmp_path / 'no'}"), 2,
             "no encuentro la carpeta"),
            (("socio", "invitar", "p.mate", "Socio", f"--carpeta={compartida}"), 2,
             "faltó decir cómo le pasás la clave"),
            (("socio", "invitar", "p.mate", "Socio", f"--carpeta={compartida}",
              f"--invitacion={tmp_path / 'clave.txt'}"), 2, "se llama invitacion-mate.txt"),
    ):
        codigo, salida, err = orden(capsys, monkeypatch, lugar, *argumentos)
        assert codigo == codigo_esperado and dice in err, (argumentos, err)
        assert not (lugar / "p.socios.json").exists()
    # 'quitar' pide el si, y después el programa avisa que falta la clave.
    orden(capsys, monkeypatch, lugar, "socio", "invitar", "p.mate", "Socio",
          f"--carpeta={compartida}", f"--invitacion={tmp_path}")
    assert orden(capsys, monkeypatch, lugar, "socio", "quitar", "p.mate", "Socio")[0] == 1
    assert (lugar / "p.socios.json").exists()
    assert orden(capsys, monkeypatch, lugar, "socio", "quitar", "p.mate", "Socio",
                 respuestas=["si"])[0] == 0
    assert not (lugar / "p.socios.json").exists()
    # 'socio' sola, con un socio.mate en la carpeta, sigue corriendo ese programa.
    (lugar / "socio.mate").write_text('mostrar("soy un programa")\n', encoding="utf-8")
    codigo, salida, _ = orden(capsys, monkeypatch, lugar, "socio")
    assert codigo == 0 and "soy un programa" in salida


def test_dos_socios_no_comparten_carpeta_ni_clave(tmp_path, capsys, monkeypatch):
    fuente = RECIBE + "usar socio Tercero\n"
    local = negocio(tmp_path, "local", fuente)
    compartida = tmp_path / "compartida"
    codigo, salida, err = orden(
        capsys, monkeypatch, local, "socio", "invitar", "local.mate", "Tercero",
        f"--carpeta={compartida}", f"--invitacion={tmp_path}")
    assert codigo == 2 and "ya es la que compartís con Socio" in err
    otra = tmp_path / "otra"
    otra.mkdir()
    invitacion = tmp_path / "invitacion-mate.txt"
    invitacion.write_text(f"x\nmate-invitacion: 1\nclave: {CLAVE}\n", encoding="utf-8")
    codigo, salida, err = orden(
        capsys, monkeypatch, local, "socio", "aceptar", "local.mate", "Tercero",
        f"--carpeta={otra}", f"--invitacion={invitacion}")
    assert codigo == 2 and "esa clave ya está cargada con Socio" in err
    assert set(mate.leer_socios(str(local / "local.mate"))[0]) == {"Socio"}
    # Aceptar la invitación que generó uno mismo tampoco.
    codigo, salida, err = orden(
        capsys, monkeypatch, local, "socio", "aceptar", "local.mate", "Socio",
        f"--invitacion={invitacion}", respuestas=["si"])
    assert codigo == 2 and "la invitación es para tu socio, no para vos" in err


def test_gitignore_cubre_las_claves_y_las_invitaciones():
    renglones = (RAIZ.parent / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert "*.socios.json" in renglones and "invitacion-mate*.txt" in renglones
    assert "*.socios.json.*.tmp" in renglones


# ── el si del dueño ──
def test_sin_el_si_nada_de_otro_negocio_se_anota(lugar, capsys, monkeypatch):
    local, compartida = lugar
    dejar(compartida / "de-b", sobre_de(1))
    dejar(compartida / "de-b", sobre_de(2))
    dejar(compartida / "de-b", sobre_de(3))
    # Sin teclado: quedan pendientes, el estado no cambia, y avisa cuántos hay.
    codigo, salida, err = orden(capsys, monkeypatch, local, "correr", "local.mate")
    assert codigo == 0 and suma(local) == 0 and "anotado" not in salida
    assert 'Socio (control 663 460) te manda Dato { n: 1, nota: "hola" }' in salida
    assert "Lo recibe: Caja." in salida
    assert "3 mensajes de socios esperan tu si" in err
    assert sobres(compartida / "de-b") == []  # ya están traídos, en la carpeta local
    assert de_socio(local)["traidos"] == [1, 2, 3]
    codigo, salida, _ = orden(capsys, monkeypatch, local, "buzon", "local.mate")
    assert "Esperan tu si: 3 mensajes" in salida and "- el número 2: Dato" in salida
    assert "control 663 460" in salida and CLAVE[:8] not in salida
    assert de_socio(local)["traidos"] == [1, 2, 3]  # 'buzon' no toca nada
    # 'despues', Enter y cualquier otra cosa dejan todo como está: solo vale "si".
    for dicho in ("despues", "", "s", "sip", "dale", "si a todos", "yes"):
        codigo, salida, err = orden(capsys, monkeypatch, local, "correr", "local.mate",
                                    respuestas=[dicho] * 3)
        assert suma(local) == 0 and de_socio(local)["traidos"] == [1, 2, 3], dicho
    # si al primero, no al segundo, nada al tercero.
    codigo, salida, err = orden(capsys, monkeypatch, local, "correr", "local.mate",
                                respuestas=["si", "no"])
    assert codigo == 0 and "anotado 1" in salida and suma(local) == 1
    assert de_socio(local)["traidos"] == [3]
    (motivo,) = rechazados(local).values()
    assert "el dueño lo descartó" in motivo
    (falla,) = sobres(compartida / "de-a")  # al socio le vuelve el aviso, con el código
    assert falla["clase"] == "falla" and falla["motivo"] == "descartado"
    assert falla["en_respuesta_a"] == sobre_de(2)["id"]
    assert "1 mensaje de socios espera tu si" in err
    codigo, salida, err = orden(capsys, monkeypatch, local, "correr", "local.mate",
                                respuestas=["SI"])
    assert suma(local) == 4 and de_socio(local)["traidos"] == []


def test_ctrl_c_en_la_pregunta_deja_pendiente(lugar, capsys, monkeypatch):
    local, compartida = lugar
    dejar(compartida / "de-b", sobre_de(1))

    def corte(_pregunta=""):
        raise KeyboardInterrupt

    monkeypatch.setattr("builtins.input", corte)
    monkeypatch.chdir(local)
    assert mate.main(["correr", "local.mate"]) == 0
    assert suma(local) == 0 and de_socio(local)["traidos"] == [1]


def test_un_pendiente_cambiado_a_mano_no_se_entrega_aunque_digan_si(lugar, capsys,
                                                                   monkeypatch):
    local, compartida = lugar
    dejar(compartida / "de-b", sobre_de(1))
    dejar(compartida / "de-b", sobre_de(2))
    orden(capsys, monkeypatch, local, "correr", "local.mate")
    pendientes = local / "local.buzon" / "pendientes"
    uno, dos = sorted(pendientes.iterdir())
    cambiado = json.loads(uno.read_text(encoding="utf-8"))
    cambiado["mensaje"]["campos"]["n"] = 99
    uno.write_text(json.dumps(cambiado), encoding="utf-8")
    # Otro sobre BIEN firmado, puesto con el nombre del 2: tampoco es el que llegó.
    dos.write_text(json.dumps(sobre_de(2, {"tipo": "Dato", "campos": {
        "n": 50, "nota": "otro"}})), encoding="utf-8")
    # Y uno que nadie trajo (puesto a mano): se borra sin preguntar.
    (pendientes / "se07089c2-00000007.json").write_text(json.dumps(sobre_de(7)),
                                                        encoding="utf-8")
    codigo, salida, err = orden(capsys, monkeypatch, local, "correr", "local.mate",
                                respuestas=["si"] * 4)
    assert "¿Lo entrego?" not in salida and suma(local) == 0
    assert "la firma no es válida" in err and "no es el mismo sobre que llegó" in err
    assert len(rechazados(local)) == 2 and list(pendientes.iterdir()) == []
    assert de_socio(local)["traidos"] == []
    assert sobres(compartida / "de-a") == []  # no es culpa del socio: no se le avisa


def test_lo_que_no_se_ve_o_engana_sale_escapado(lugar, capsys, monkeypatch):
    local, compartida = lugar
    raro = 'a\u202eb\x07c\u2028d"e\\f\ud800g\u200bh'
    dejar(compartida / "de-b", sobre_de(1, {"tipo": "Dato", "campos": {
        "n": 1, "nota": raro}}))
    dejar(compartida / "de-b", sobre_de(2, {"tipo": "Ot\u202ero\x1b[2J", "campos": {}}))
    dejar(compartida / "de-b", sobre_de(3, firmar=False),
          "0000\u202e0003 \x07raro.json")
    codigo, salida, err = orden(capsys, monkeypatch, local, "correr", "local.mate",
                                "--traza", respuestas=["si"])
    todo = salida + err + "".join(rechazados(local).values())
    pregunta = next(r for r in salida.splitlines() if "te manda Dato" in r)
    assert r'nota: "a\u202eb\u0007c\u2028d\"e\\f\ud800g\u200bh"' in pregunta
    traza = next(r for r in salida.splitlines() if "Socio (otro negocio) →" in r)
    assert r"a\u202eb" in traza and r"\u2028" in traza and r"\ud800" in traza
    for malo in ("\u202e", "\x07", "\x1b", "\u2028", "\ud800", "\u200b"):
        assert malo not in todo.replace("anotado 1", ""), repr(malo)
    assert r"Ot\u202ero\u001b[2J" in err  # el tipo, en el aviso y en el motivo
    assert r"0000\u202e0003 \u0007raro.json" in "".join(rechazados(local).values())
    # Un valor no puede cerrar su comilla y dibujar otro campo, u otra pregunta.
    dejar(compartida / "de-b", sobre_de(4, {"tipo": "Dato", "campos": {
        "n": 4, "nota": 'x", total: 0 }\n¿Lo entrego? (si / no / despues) si'}}))
    codigo, salida, err = orden(capsys, monkeypatch, local, "correr", "local.mate")
    pregunta = next(r for r in salida.splitlines() if "te manda Dato" in r)
    assert r'nota: "x\", total: 0 }\u000a¿Lo entrego? (si / no / despues) si"' in pregunta
    assert salida.count("\n¿Lo entrego? (si / no / despues)") == 1


def test_texto_ajeno():
    assert mate.texto_ajeno("hola ñandú $ 3.500") == "hola ñandú $ 3.500"
    assert mate.texto_ajeno("a\tb\nc\rd") == r"a\u0009b\u000ac\u000dd"
    assert mate.texto_ajeno("\u202e\u2066\u200f\ufeff") == r"\u202e\u2066\u200f\ufeff"
    assert mate.texto_ajeno("\ud83e") == r"\ud83e" and mate.texto_ajeno("\U000e0001") \
        == r"\U000e0001"
    assert mate.texto_ajeno("x" * 300) == "x" * 200 + "..."
    assert mate.texto_ajeno('a"b\\c', entre_comillas=True) == r'a\"b\\c'
    assert mate.texto_ajeno(None) == "None" and mate.texto_ajeno(5) == "5"


def test_un_mensaje_enorme_entre_negocios_no_sale_ni_entra(lugar, capsys, monkeypatch):
    local, compartida = lugar
    (local / "local.mate").write_text(RECIBE.replace(
        'nota: "va"', 'nota: unir(rango(1, 400), "-")'
    ) + "enviar Mandar { n: 5 } a Caja\n", encoding="utf-8")
    codigo, salida, err = orden(capsys, monkeypatch, local, "correr", "local.mate")
    assert codigo == 1 and "no puede ir a Socio (otro negocio)" in err
    assert "500 letras" in err and sobres(compartida / "de-a") == []
    # Y lo que llega pasado de tamaño se rechaza entero: no se recorta para mostrarlo.
    (local / "local.mate").write_text(RECIBE, encoding="utf-8")
    hondo = {"tipo": "Dato", "campos": {"n": 1, "nota": "x", "extra": [[[[1]]]]}}
    dejar(compartida / "de-b", sobre_de(1, hondo))
    codigo, salida, err = orden(capsys, monkeypatch, local, "correr", "local.mate",
                                respuestas=["si"])
    assert "¿Lo entrego?" not in salida and "una adentro de otra" in err


def test_el_cupo_de_rechazados_y_el_tope_de_pendientes(lugar, capsys, monkeypatch):
    local, compartida = lugar
    monkeypatch.setattr(mate, "MAX_RECHAZADOS_DE_SOCIO", 3)
    monkeypatch.setattr(mate, "MAX_PENDIENTES_POR_SOCIO", 2)
    for n in range(1, 8):  # basura sin firma: no llena el disco
        dejar(compartida / "de-b", sobre_de(n, firmar=False), f"basura-{n}.json")
    for n in (1, 2, 3, 4):
        dejar(compartida / "de-b", sobre_de(n))
    codigo, salida, err = orden(capsys, monkeypatch, local, "correr", "local.mate")
    assert codigo == 0 and len(rechazados(local)) == 3
    assert "ya hay 3 rechazados de Socio" in err and "4 más no se guardaron" in err
    # La basura no le saca el lugar a lo legítimo: los de forma esperada van primero.
    assert de_socio(local)["traidos"] == [1, 2]
    assert "es el tope" in err
    assert [s["socio"]["numero"] for s in sobres(compartida / "de-b")] == [3, 4]
    orden(capsys, monkeypatch, local, "correr", "local.mate", respuestas=["si", "si"])
    assert suma(local) == 3
    orden(capsys, monkeypatch, local, "correr", "local.mate", respuestas=["si", "si"])
    assert suma(local) == 10 and sobres(compartida / "de-b") == []


# ── P161 (1): el buzón local solo entrega lo de un programa conocido ──
MENSAJES_LOCALES = "mensaje Reservar { pedido: texto, cantidad: numero }\n" \
                   "mensaje Reservado { pedido: texto }\n"
DEPOSITO = 'usar "mensajes.mate"\n' + """\
agente Deposito {
    estado recordado pedidos = []
    al recibir Reservar como r {
        pedidos = agregar(pedidos, r.pedido)
        responder Reservado { pedido: r.pedido }
    }
}
"""
VENTAS = 'usar "mensajes.mate"\nusar buzon "deposito.mate"\n' + """\
agente Ventas {
    estado recordado devueltos = []
    al recibir Reservado como r { mostrar("ok {r.pedido}") }
    al fallar como f { devueltos = agregar(devueltos, f.mensaje.pedido) }
}
enviar Reservar { pedido: "A-1", cantidad: 1 } a Deposito
"""


def sobre_local(n, de=("ventas", "Ventas"), para=("deposito", "Deposito"), **cambios):
    identidad = f"20260101T000000-{'cd' * 10}-{n:04d}"
    sobre = {"mate_buzon": 1, "id": identidad, "clase": "mensaje",
             "de": {"programa": de[0], "agente": de[1]},
             "para": {"programa": para[0], "agente": para[1]},
             "conversacion": identidad, "en_respuesta_a": None,
             "cuando": "2026-01-01T00:00:00",
             "mensaje": {"tipo": "Reservar", "campos": {"pedido": f"M-{n}", "cantidad": 1}}}
    sobre.update(cambios)
    return sobre


def local_de(tmp_path, **archivos):
    todos = {"mensajes.mate": MENSAJES_LOCALES, "deposito.mate": DEPOSITO,
             "ventas.mate": VENTAS}
    todos.update({k.replace("_mate", ".mate"): v for k, v in archivos.items()})
    for nombre, texto in todos.items():
        if texto is not None:
            (tmp_path / nombre).write_text(texto, encoding="utf-8")
    return tmp_path


def pedidos_de_deposito(carpeta):
    archivo = carpeta / "deposito.memoria.json"
    if not archivo.exists():
        return []
    return json.loads(archivo.read_text(encoding="utf-8-sig"))["agentes"]["Deposito"][
        "estado"]["pedidos"]


def test_local_el_que_no_nombra_al_destinatario_no_entrega(tmp_path, capsys, monkeypatch):
    carpeta = local_de(tmp_path, intruso_mate='mostrar("no nombro a nadie")\n')
    buzon = carpeta / "deposito.buzon"
    buzon.mkdir()
    (buzon / "1.json").write_text(json.dumps(sobre_local(1)), encoding="utf-8")  # conocido
    (buzon / "2.json").write_text(json.dumps(sobre_local(
        2, de=("fantasma", "Alguien"))), encoding="utf-8")  # un programa que no existe
    (buzon / "3.json").write_text(json.dumps(sobre_local(
        3, de=("intruso", "(programa)"))), encoding="utf-8")  # existe y no me nombra
    (buzon / "4.json").write_text(json.dumps(sobre_local(
        4, de=("ventas", "Inventado"))), encoding="utf-8")  # el agente no existe ahí
    (buzon / "5.json").write_text(json.dumps(dict(
        sobre_local(5), mate_buzon=2, firma="ab" * 32,
        socio={"huella": "e07089c2", "lado": "B", "numero": 5})), encoding="utf-8")
    codigo, salida, err = orden(capsys, monkeypatch, carpeta, "correr", "deposito.mate")
    assert pedidos_de_deposito(carpeta) == ["M-1"]
    motivos = {n: (buzon / "rechazados" / n).read_text(encoding="utf-8-sig")
               for n in sorted(os.listdir(buzon / "rechazados")) if n.endswith(".txt")}
    assert len(motivos) == 4
    assert "no conozco a 'fantasma': para recibir de otro programa, ese programa tiene " \
           'que tener usar buzon "deposito.mate" (o este, usar buzon "fantasma.mate")' \
           in motivos["2.motivo.txt"]
    assert "no conozco a 'intruso'" in motivos["3.motivo.txt"]
    assert "no tiene ningún agente con ese nombre" in motivos["4.motivo.txt"]
    assert "versión más nueva" in motivos["5.motivo.txt"]  # un sobre 2 no va en el local
    # A un desconocido no se le contesta: no nace la carpeta de un nombre elegido por él.
    assert not (carpeta / "fantasma.buzon").exists()
    assert not (carpeta / "intruso.buzon").exists()
    assert [s["mensaje"]["tipo"] for s in sobres(carpeta / "ventas.buzon")] == ["Reservado"]


def test_local_un_programa_sin_ninguna_relacion_de_buzon_no_entrega_nada(tmp_path, capsys,
                                                                        monkeypatch):
    carpeta = local_de(tmp_path, ventas_mate='usar "mensajes.mate"\nmostrar("nada")\n')
    buzon = carpeta / "deposito.buzon"
    buzon.mkdir()
    (buzon / "1.json").write_text(json.dumps(sobre_local(1)), encoding="utf-8")
    (buzon / "2.json").write_text(json.dumps(sobre_local(
        2, de=("ventas", "(programa)"))), encoding="utf-8")
    codigo, salida, err = orden(capsys, monkeypatch, carpeta, "correr", "deposito.mate")
    assert pedidos_de_deposito(carpeta) == []
    assert err.count("no conozco a 'ventas'") == 2
    assert not (carpeta / "ventas.buzon").exists()


def test_local_vale_tambien_si_el_que_recibe_nombra_al_que_manda(tmp_path, capsys,
                                                                 monkeypatch):
    carpeta = local_de(
        tmp_path, ventas_mate='usar "mensajes.mate"\nagente Ventas {\n    al recibir '
                              'Reservado como r { }\n}\n',
        deposito_mate=DEPOSITO.replace('usar "mensajes.mate"\n',
                                       'usar "mensajes.mate"\nusar buzon "ventas.mate"\n'))
    buzon = carpeta / "deposito.buzon"
    buzon.mkdir()
    (buzon / "1.json").write_text(json.dumps(sobre_local(1)), encoding="utf-8")
    orden(capsys, monkeypatch, carpeta, "correr", "deposito.mate")
    assert pedidos_de_deposito(carpeta) == ["M-1"]


def test_local_una_falla_inventada_no_repone_nada(tmp_path, capsys, monkeypatch):
    carpeta = local_de(tmp_path, deposito_mate=DEPOSITO.replace(
        'usar "mensajes.mate"\n', 'usar "mensajes.mate"\nusar buzon "ventas.mate"\n'))
    assert orden(capsys, monkeypatch, carpeta, "correr", "ventas.mate")[0] == 0
    (mandado,) = sobres(carpeta / "deposito.buzon")
    enviados = json.loads((carpeta / "ventas.memoria.json").read_text(
        encoding="utf-8-sig"))["correo"]["enviados"]
    assert enviados == [f"deposito/{mandado['id']}"]
    buzon = carpeta / "ventas.buzon"
    buzon.mkdir()
    inventada = sobre_local(1, de=("deposito", "Deposito"), para=("ventas", "Ventas"),
                            clase="falla", motivo="se cayó todo", mensaje=mandado["mensaje"],
                            en_respuesta_a="20260101T000000-" + "cd" * 10 + "-9999")
    (buzon / "1.json").write_text(json.dumps(inventada), encoding="utf-8")
    (carpeta / "ventas.mate").write_text(VENTAS.rsplit("enviar", 1)[0], encoding="utf-8")
    codigo, salida, err = orden(capsys, monkeypatch, carpeta, "correr", "ventas.mate")
    estado = json.loads((carpeta / "ventas.memoria.json").read_text(encoding="utf-8-sig"))
    assert estado["agentes"].get("Ventas", {}).get("estado", {}).get("devueltos", []) == []
    assert "nombra un mensaje que este programa no le mandó" in err
    # La de verdad (nombra lo que Ventas mandó) sí llega al 'al fallar'.
    cierta = dict(inventada, id=inventada["id"][:-4] + "0002",
                  en_respuesta_a=mandado["id"])
    (buzon / "2.json").write_text(json.dumps(cierta), encoding="utf-8")
    orden(capsys, monkeypatch, carpeta, "correr", "ventas.mate")
    estado = json.loads((carpeta / "ventas.memoria.json").read_text(encoding="utf-8-sig"))
    assert estado["agentes"]["Ventas"]["estado"]["devueltos"] == ["A-1"]


def test_local_los_ejemplos_del_buzon_de_la_07_siguen_andando(tmp_path, capsys, monkeypatch):
    for nombre in ("buzon_mensajes.mate", "buzon_ventas.mate", "buzon_deposito.mate"):
        (tmp_path / nombre).write_bytes((RAIZ / "ejemplos" / nombre).read_bytes())
    assert orden(capsys, monkeypatch, tmp_path, "correr", "buzon_ventas.mate")[0] == 0
    codigo, salida, err = orden(capsys, monkeypatch, tmp_path, "correr",
                                "buzon_deposito.mate")
    assert codigo == 0 and "atendí 1 mensaje" in salida and "no conozco" not in err
    codigo, salida, err = orden(capsys, monkeypatch, tmp_path, "correr", "buzon_ventas.mate")
    assert codigo == 0 and "Pedido A-17: reservado. Quedan 8." in salida


# ── el lenguaje y las órdenes ──
def test_no_se_gastan_palabras_ni_funciones():
    assert len(mate.PALABRAS) == 36 and len(mate.FUNCIONES) == 48
    assert not {"socio", "acepta", "socios"} & (mate.PALABRAS | set(mate.FUNCIONES))
    assert mate.VERSION_DE_BUZON == 1 and mate.VERSION_DE_SOBRE_DE_SOCIO == 2


def test_socio_y_acepta_siguen_sirviendo_de_nombres(tmp_path, capsys, monkeypatch):
    (tmp_path / "p.mate").write_text(
        'sea socio = "Juan"\nsea acepta = verdadero\nfuncion buzon(socio) { devolver socio }\n'
        'si acepta { mostrar(buzon(socio)) }\n', encoding="utf-8")
    codigo, salida, err = orden(capsys, monkeypatch, tmp_path, "correr", "p.mate")
    assert (codigo, salida, err) == (0, "Juan\n", "")
    assert not list(tmp_path.glob("p.*.json"))


@pytest.mark.parametrize("fuente, dice", [
    ("mensaje M { n: numero }\nusar socio Socio acepta M\n",
     "ningún agente tiene 'al recibir M'"),
    ("mensaje M { n: numero }\nusar socio Socio acepta M\nagente A { al recibir M { } }\n"
     "agente B { al recibir M { } }\n", "lo reciben A y B"),
    ("usar socio Socio acepta Nada\n", "no es un mensaje declarado"),
    ("mensaje M { n: numero }\nusar socio Socio acepta M, M\nagente A { al recibir M { } }\n",
     "está dos veces en el 'acepta'"),
    ("mensaje M { n: numero }\nusar socio Socio\nsea r = preguntar M { n: 1 } a Socio\n",
     "Socio es un socio (otro negocio): no se le puede 'preguntar'"),
    ("mensaje M { n: numero }\nagente Socio { al recibir M { } }\nusar socio Socio\n",
     "ya hay un agente Socio en este programa"),
    ("mensaje Socio { n: numero }\nusar socio Socio\n", "ya hay un mensaje Socio"),
    ("usar socio Socio\nusar socio Socio\n", "el socio Socio ya está declarado"),
    ("usar socio Socio\nsea copia = crear Socio\n", "es un socio (otro negocio)"),
    ("usar socio\n", "'usar socio' lleva el nombre"),
    ("usar socio proveedor\n", "'usar socio' lleva el nombre"),
    ("usar socio Socio acepta\n", "después de 'acepta' van los mensajes"),
    ("usar socio Socio acepta M,\n", "después de 'acepta' van los mensajes"),
    ("usar socio Socio recibe M\n", "'usar socio' lleva el nombre"),
])
def test_errores_de_socios_antes_de_correr(tmp_path, capsys, monkeypatch, fuente, dice):
    (tmp_path / "p.mate").write_text(fuente, encoding="utf-8")
    for que in ("verificar", "correr", "probar"):
        codigo, salida, err = orden(capsys, monkeypatch, tmp_path, que, "p.mate")
        assert codigo == 1 and dice in err, (que, err)
    assert sorted(p.name for p in tmp_path.iterdir()) == ["p.mate"]


def test_usar_socio_no_va_en_un_archivo_traido_con_usar(tmp_path, capsys, monkeypatch):
    (tmp_path / "trato.mate").write_text("mensaje M { n: numero }\nusar socio Socio\n",
                                         encoding="utf-8")
    (tmp_path / "p.mate").write_text('usar "trato.mate"\n', encoding="utf-8")
    codigo, salida, err = orden(capsys, monkeypatch, tmp_path, "verificar", "p.mate")
    assert codigo == 1 and "'usar socio' va en el programa que se corre" in err


def test_un_socio_tiene_las_prohibiciones_de_un_agente_de_otro_programa(tmp_path, capsys,
                                                                       monkeypatch):
    (tmp_path / "p.mate").write_text("""\
mensaje M { n: numero }
mensaje Lleva { quien: agente }
usar socio Socio
agente A {
    al recibir M { }
    al recibir Lleva { }
}
prueba "no se mete en un mensaje" {
    asegurar falla { enviar Lleva { quien: Socio } a A }
}
prueba "se le manda suelto, en lista y en variable" {
    sea destino = Socio
    enviar M { n: 1 } a Socio
    enviar M { n: 2 } a [A, Socio]
    enviar M { n: 3 } a destino
    sea idos = mensajes_enviados("M")
    asegurar largo(idos) == 4
    asegurar idos[0].a == "Socio"
}
prueba "lo que contesta se prueba con simular" {
    simular Socio al recibir M como m { responder M { n: m.n + 1 } }
    enviar M { n: 1 } a Socio
}
""", encoding="utf-8")
    codigo, salida, err = orden(capsys, monkeypatch, tmp_path, "probar", "p.mate")
    assert codigo == 0 and "3 de 3 pruebas pasaron" in salida, salida + err
    assert sorted(p.name for p in tmp_path.iterdir()) == ["p.mate"]


def test_nuevo_socio_crea_el_ensayo_y_los_pasos_impresos_andan_tal_cual(
        tmp_path, capsys, monkeypatch):
    codigo, salida, err = orden(capsys, monkeypatch, tmp_path, "nuevo", "socio", "prueba")
    assert codigo == 0 and err == ""
    base = tmp_path / "prueba"
    assert sorted(p.name for p in base.iterdir()) == ["compartida", "comprador", "proveedor"]
    assert sorted(p.name for p in (base / "comprador").iterdir()) == [
        "comprador.mate", "comprador.socios.json", "trato.mate"]
    assert sorted(p.name for p in (base / "proveedor").iterdir()) == [
        "proveedor.mate", "proveedor.socios.json", "trato.mate"]
    assert sorted(p.name for p in (base / "compartida").iterdir()) == [
        "LEEME-mate.txt", "de-a", "de-b"]
    fichas = [mate.leer_socios(str(base / n / f"{n}.mate"))[0] for n in
              ("comprador", "proveedor")]
    clave = fichas[0]["Proveedor"]["clave"]
    assert fichas[1]["Cliente"]["clave"] == clave and clave not in salida
    assert fichas[0]["Proveedor"]["ensayo"] and fichas[1]["Cliente"]["ensayo"]
    assert (fichas[0]["Proveedor"]["lado"], fichas[1]["Cliente"]["lado"]) == ("A", "B")
    assert "14_" not in (base / "comprador" / "comprador.mate").read_text(encoding="utf-8-sig")
    # Los pasos impresos: se copian tal cual. Acá se corren uno por uno, en orden.
    pasos = [r.strip() for r in salida.split("PARA TRABAJAR CON UN SOCIO DE VERDAD")[0]
             .splitlines() if r.startswith("       ") and not r.startswith("        ")]
    assert len(pasos) == 16, pasos
    assert all(p.startswith(("cd '", "python3 '", "python '", "py '")) for p in pasos)
    donde, corridas = tmp_path, []
    for paso in pasos:
        if paso.startswith("cd "):
            assert paso[3] == paso[-1] == "'"  # comillas simples: PowerShell no las toca
            donde = pathlib.Path(paso[4:-1].replace("''", "'"))
            assert donde.is_dir()
            continue
        forma = re.fullmatch(r"(?:python3?|py) '(.+)' (\w+) (\w+\.mate)", paso)
        assert forma and pathlib.Path(forma.group(1)) == RAIZ / "mate.py", paso
        codigo, salida_del_paso, err = orden(capsys, monkeypatch, donde, forma.group(2),
                                             forma.group(3), respuestas=["si"])
        assert codigo == 0, (paso, err)
        corridas.append((forma.group(2), salida_del_paso, err))
    assert "6 de 6 pruebas pasaron" in corridas[0][1]
    assert "7 de 7 pruebas pasaron" in corridas[1][1]
    assert "Pedido A-17: confirmado por el proveedor." in corridas[-2][1]
    # Cada corrida avisa que la clave es de ensayo, y dice cómo pasar a una de verdad.
    assert all("es de ENSAYO" in err and "socio renovar" in err
               for que, _, err in corridas if que == "correr")
    # No pisa: con la carpeta ya creada no hace nada.
    codigo, salida, err = orden(capsys, monkeypatch, tmp_path, "nuevo", "socio", "prueba")
    assert codigo == 1 and "no piso nada" in err
    for mal in (["a", "b"], ["con espacio/barra"], ["nul"], ["probar"]):
        assert orden(capsys, monkeypatch, tmp_path, "nuevo", "socio", *mal)[0] == 2


def test_los_ejemplos_14_son_lo_que_crea_nuevo_socio_y_pasan_probar(tmp_path, capsys,
                                                                    monkeypatch):
    for nombre in ("14_comprador.mate", "14_proveedor.mate", "14_trato.mate"):
        (tmp_path / nombre).write_bytes((RAIZ / "ejemplos" / nombre).read_bytes())
    for nombre, cuantas in (("14_comprador.mate", 6), ("14_proveedor.mate", 7)):
        assert orden(capsys, monkeypatch, tmp_path, "verificar", nombre)[0] == 0
        codigo, salida, err = orden(capsys, monkeypatch, tmp_path, "probar", nombre)
        assert codigo == 0 and f"{cuantas} de {cuantas} pruebas pasaron" in salida
        assert err == ""
    assert len(list(tmp_path.iterdir())) == 3  # 'probar' no deja nada
    # El ejemplo no le pasa nada del socio a la IA.
    for nombre in ("14_comprador.mate", "14_proveedor.mate"):
        assert "consultar_ia" not in (tmp_path / nombre).read_text(encoding="utf-8")


def test_probar_verificar_y_ensayar_no_leen_ni_escriben_nada_de_socios(lugar, capsys,
                                                                      monkeypatch):
    local, compartida = lugar
    dejar(compartida / "de-b", sobre_de(1))
    (local / "local.mate").write_text(RECIBE + """\
enviar Mandar { n: 5 } a Caja
prueba "sale" {
    enviar Mandar { n: 7 } a Caja
    asegurar mensajes_enviados("Dato")[0].a == "Socio"
}
""", encoding="utf-8")
    (local / "casos.txt").write_text("hola\ntiene que decir: hola\n", encoding="utf-8")
    (local / "local.socios.json").write_text("esto no es JSON", encoding="utf-8")
    antes = {p: p.read_bytes() for p in sorted(local.parent.rglob("*")) if p.is_file()}
    codigo, salida, err = orden(capsys, monkeypatch, local, "probar", "local.mate")
    assert codigo == 0 and "1 de 1 pruebas pasaron" in salida and err == ""
    codigo, salida, err = orden(capsys, monkeypatch, local, "verificar", "local.mate")
    assert codigo == 0 and err == ""
    orden(capsys, monkeypatch, local, "ensayar", "local.mate", "casos.txt",
          "--ia-simulada")
    assert {p: p.read_bytes() for p in sorted(local.parent.rglob("*")) if p.is_file()} \
        == antes
    # 'correr', en cambio, avisa que el archivo de claves no se entiende, y no manda.
    codigo, salida, err = orden(capsys, monkeypatch, local, "correr", "local.mate")
    assert codigo == 0 and "no entiendo local.socios.json" in err
    assert sobres(compartida / "de-a") == []


def test_un_programa_con_usar_socio_sin_clave_corre_avisa_y_no_manda(tmp_path, capsys,
                                                                    monkeypatch):
    local = negocio(tmp_path, "local", RECIBE + 'enviar Mandar { n: 5 } a Caja\n'
                    'mostrar("sigue")\n', clave=None)
    compartida = tmp_path / "compartida"
    codigo, salida, err = orden(capsys, monkeypatch, local, "correr", "local.mate")
    assert codigo == 0 and "sigue" in salida  # no es un error
    assert "falta cargar la clave del socio Socio" in err
    assert "socio invitar local.mate Socio" in err and "socio aceptar local.mate Socio" in err
    assert "queda anotado y NO salió" in err
    assert sobres(compartida / "de-a") == [] and not (local / "local.buzon").exists()
    (borrador,) = de_socio(local)["en_espera"]
    assert "firma" not in borrador and "socio" not in borrador
    codigo, salida, _ = orden(capsys, monkeypatch, local, "buzon", "local.mate")
    assert "Socio Socio: sin clave cargada" in salida and "Anotados sin salir: 1" in salida
    # Cuando la clave está, lo anotado sale (numerado y firmado recién ahí).
    (local / "local.mate").write_text(RECIBE, encoding="utf-8")
    mate.guardar_socios(str(local / "local.mate"), {"Socio": {
        "clave": CLAVE, "lado": "A", "carpeta": str(compartida), "estrenado": False}})
    codigo, salida, err = orden(capsys, monkeypatch, local, "correr", "local.mate")
    (salido,) = sobres(compartida / "de-a")
    assert salido["socio"]["numero"] == 1 and salido["id"] == borrador["id"]
    assert salido["firma"] == mate.firma_de_sobre(salido, CLAVE, "A")
    assert de_socio(local)["en_espera"] == []


def test_verificar_avisa_si_un_agente_que_recibe_de_un_socio_usa_la_ia(tmp_path, capsys,
                                                                      monkeypatch):
    (tmp_path / "p.mate").write_text("""\
mensaje Consulta { texto: texto }
usar socio Socio acepta Consulta
agente Mostrador {
    al recibir Consulta como c { mostrar(consultar_ia("Sos un vendedor", c.texto)) }
}
""", encoding="utf-8")
    codigo, salida, err = orden(capsys, monkeypatch, tmp_path, "verificar", "p.mate")
    assert codigo == 0 and "sin errores" in salida  # es un aviso, no un error
    assert "aviso: Mostrador recibe Consulta del socio Socio y además consulta a la IA" in err


def test_olvidar_no_toca_la_cuenta_de_los_socios(lugar, capsys, monkeypatch):
    local, compartida = lugar
    dejar(compartida / "de-b", sobre_de(1))
    orden(capsys, monkeypatch, local, "correr", "local.mate", respuestas=["si"])
    antes = de_socio(local)
    assert suma(local) == 1 and antes["vistos"]
    orden(capsys, monkeypatch, local, "correr", "local.mate", "--olvidar")
    assert de_socio(local) == antes
    dejar(compartida / "de-b", sobre_de(1))  # lo ya entregado no entra de nuevo
    codigo, salida, _ = orden(capsys, monkeypatch, local, "correr", "local.mate",
                              respuestas=["si"])
    assert "¿Lo entrego?" not in salida


def test_corregir_y_lecciones_conservan_la_cuenta_de_los_socios(lugar, capsys, monkeypatch):
    local, compartida = lugar
    dejar(compartida / "de-b", sobre_de(1))
    orden(capsys, monkeypatch, local, "correr", "local.mate")
    antes = memoria(local)["correo"]
    assert antes["socios"]["Socio"]["traidos"] == [1]
    assert orden(capsys, monkeypatch, local, "corregir", "local.mate", "Caja",
                 "Sumá con cuidado")[0] == 0
    assert memoria(local)["correo"] == antes
    assert memoria(local)["agentes"]["Caja"]["lecciones"]


def test_la_ayuda_y_la_guia_nombran_a_los_socios(capsys, monkeypatch, tmp_path):
    codigo, salida, _ = orden(capsys, monkeypatch, tmp_path, "ayuda")
    assert "socio invitar" in salida and "nuevo socio" in salida
    assert "usar socio" in salida
    codigo, salida, _ = orden(capsys, monkeypatch, tmp_path, "guia")
    assert "usar socio Proveedor acepta" in salida
    codigo, salida, err = orden(capsys, monkeypatch, tmp_path, "ayuda", "socio")
    assert codigo == 0 and "usar socio" in salida and "¿Lo entrego?" in salida
    codigo, salida, err = orden(capsys, monkeypatch, tmp_path, "socoi")
    assert codigo == 2 and "¿quisiste decir 'socio'?" in err


def test_la_firma_sobrevive_a_quedar_anotada_en_la_memoria(tmp_path, capsys, monkeypatch):
    """Un sobre que no pudo salir queda firmado en la memoria y sale después: lo que llega
    del otro lado tiene que seguir verificando, con tildes, un emoji y decimales adentro."""
    fuente = RECIBE.replace('nota: "va"', 'nota: "ñandú \U0001f9c9 $ 3.500,50 «x»"').replace(
        "n: m.n,", "n: m.n + 0.5,").replace("desde 1 hasta 100", "desde 1 hasta 100.5")
    a = negocio(tmp_path, "a", fuente + "enviar Mandar { n: 5 } a Caja\n")
    b = negocio(tmp_path, "b", fuente, lado="B")
    compartida = tmp_path / "compartida"
    compartida.rename(tmp_path / "afuera")
    assert orden(capsys, monkeypatch, a, "correr", "a.mate")[0] == 0
    (tmp_path / "afuera").rename(compartida)
    (a / "a.mate").write_text(fuente, encoding="utf-8")
    assert orden(capsys, monkeypatch, a, "correr", "a.mate")[0] == 0
    (viajo,) = sobres(compartida / "de-a")
    assert viajo["mensaje"]["campos"] == {"n": 5.5, "nota": "ñandú \U0001f9c9 $ 3.500,50 «x»"}
    codigo, salida, err = orden(capsys, monkeypatch, b, "correr", "b.mate", respuestas=["si"])
    assert codigo == 0 and "anotado 5.5" in salida and rechazados(b) == {}
    assert 'nota: "ñandú \U0001f9c9 $ 3.500,50 «x»"' in salida


def test_renovar_de_un_lado_y_aceptar_del_otro_y_siguen_hablando(tmp_path, capsys,
                                                                 monkeypatch):
    fuente = RECIBE + "enviar Mandar { n: 5 } a Caja\n"
    a = negocio(tmp_path, "a", fuente)
    b = negocio(tmp_path, "b", RECIBE, lado="B")
    compartida = tmp_path / "compartida"
    orden(capsys, monkeypatch, a, "correr", "a.mate")
    orden(capsys, monkeypatch, b, "correr", "b.mate")  # queda esperando el si
    assert de_socio(b)["traidos"] == [1]
    pendrive = tmp_path / "pendrive"
    pendrive.mkdir()
    codigo, salida, err = orden(capsys, monkeypatch, a, "socio", "renovar", "a.mate", "Socio",
                                f"--invitacion={pendrive}", respuestas=["si"])
    assert codigo == 0, err
    codigo, salida, err = orden(capsys, monkeypatch, b, "socio", "aceptar", "b.mate", "Socio",
                                f"--invitacion={pendrive}")  # sin el si no la cambia
    assert codigo == 1 and (pendrive / "invitacion-mate.txt").exists()
    codigo, salida, err = orden(capsys, monkeypatch, b, "socio", "aceptar", "b.mate", "Socio",
                                f"--invitacion={pendrive}", respuestas=["si"])
    assert codigo == 0, err
    nueva = mate.leer_socios(str(a / "a.mate"))[0]["Socio"]["clave"]
    assert nueva != CLAVE and mate.leer_socios(str(b / "b.mate"))[0]["Socio"] == {
        "clave": nueva, "lado": "B", "carpeta": str(compartida), "estrenado": False}
    # Lo que esperaba el si con la clave vieja se descarta, con aviso; lo nuevo entra.
    orden(capsys, monkeypatch, a, "correr", "a.mate")
    codigo, salida, err = orden(capsys, monkeypatch, b, "correr", "b.mate",
                                respuestas=["si", "si"])
    assert "con la clave anterior se descartan" in err
    assert "era de una clave que ya no se usa" in err
    assert salida.count("¿Lo entrego?") == 1 and suma(b) == 5
    assert not list((b / "b.buzon" / "pendientes").iterdir())
    assert sobres(compartida / "de-a") == []


def test_corregir_a_un_socio_y_la_consola_lo_dicen_claro(lugar, capsys, monkeypatch):
    local, _ = lugar
    codigo, salida, err = orden(capsys, monkeypatch, local, "corregir", "local.mate", "Socio",
                                "Portate bien")
    assert codigo == 2 and "Socio es un socio (otro negocio)" in err
    assert "Probá con" not in err
    codigo, salida, err = orden(
        capsys, monkeypatch, local, "consola",
        respuestas=["usar socio X", "mensaje M { n: numero }", "enviar M { n: 1 } a X"])
    assert "desde la consola no sale nada para otro programa" in salida + err
    assert "X (otro negocio)" in salida + err and "no sabe recibir" not in salida + err
