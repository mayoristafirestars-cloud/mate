# Mate 🧉

Mate es un lenguaje de programación chico, con palabras en castellano, para armar **agentes**:
partes de un programa que reciben mensajes, consultan a una IA y contestan. Vos escribís las
reglas (qué precios puede nombrar, qué no puede prometer, cuánto puede gastar por día) y Mate
revisa cada respuesta de la IA antes de que salga.

Es un solo archivo de Python, sin nada más que instalar. Se escribe con el Bloc de notas y se
corre desde PowerShell.

## Empezar

1. Instalá Python: en la tienda Microsoft Store, buscá `Python Install Manager` y tocá
   "Instalar" (es el camino que hoy recomienda Python; el paso a paso está en el
   [manual](mate/README.md#instalarlo)). Si usás el instalador de antes, el `.exe` de
   `python.org/downloads`, marcá "Add python.exe to PATH".
2. Bajá este proyecto: botón verde **Code** y después **Download ZIP**. Extraelo.
3. Abrí PowerShell en la carpeta extraída y probá:

```
python mate\mate.py --version
python mate\mate.py correr mate\ejemplos\11_mostrador_con_frenos.mate --ia-simulada
python mate\mate.py curso
```

## Qué hay acá

| Carpeta | Qué es |
|---|---|
| `mate/` | El lenguaje (`mate.py`), el [manual](mate/README.md) y el instalador para Windows |
| `mate/curso/` | [Trece clases](mate/curso/README.md), de "hola" a un mostrador con IA y frenos y un equipo de agentes que se hablan |
| `mate/ejemplos/` | Programas terminados y comentados |
| `mate/modelo/` | [Adaptador](mate/modelo/README.md) para usar un modelo de IA propio |
| `mate/pruebas/` | Las pruebas del intérprete |
| `docs/` | La página de presentación |

## Para qué no sirve todavía

No atiende WhatsApp ni tiene página web propia: todo pasa en la ventana de PowerShell. Es un
proyecto nuevo, hecho por una persona con ayuda de IA, pensado para programas cortos y claros.
