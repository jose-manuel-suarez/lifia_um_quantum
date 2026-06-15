# lifia_um_quantum

Breve: herramientas para convertir una matriz unitaria arbitraria `U` en una evolución de circuito cuántico a través de niveles de abstracción (1..6). El proyecto define conversores, un workflow que encadena pasos y utilidades para trabajar con ecosistemas objetivo (ej. Qiskit).

## Estructura principal

- `convert/` — Wrappers y puntos de entrada para cada conversor (`step_1to2.py`, `step_2to3.py`, ...). Los wrappers delegan a las implementaciones preservadas en `originals/`.
- `originals/` — Implementaciones originales e inmutables de las transformaciones (mantenidas aquí para paridad).
- `shared/` — Utilidades comunes: I/O, logger, config, adaptadores a ecosistemas (`shared/circuits.py`).
- `tools/` — Scripts auxiliares (ej. `tools/verify_parity.py`).
- `workflow.py` — Runner que lee `.env` y encadena los conversores hasta el nivel máximo deseado, escribiendo intermediarios en `out/`.
- `abstraction2.json`, `abstraction3.json` — Ejemplos de salida en niveles 2 y 3.
- `tests.ipynb` — Notebook con pruebas / ejemplos (no modificado automáticamente).
- `.env-example`, `.env` — Configuración del flujo.
- `requirements.txt`, `.gitignore` — Dependencias y exclusiones.

## Propósito y principios

- Mantener las implementaciones originales intactas en `originals/`.
- Ofrecer wrappers en `convert/` para exponer una API consistente `convert(circuit_spec, destination_file=None, ecosystem=None, logger=None)`.

## Requisitos mínimos

- Python 3.10+ (las anotaciones de tipo en el código usan la sintaxis `X | Y`).
- Instalar dependencias:

```bash
# Sitúate en la raíz del proyecto antes de ejecutar los comandos (ruta relativa):
cd ./lifia_um_quantum

# Crear entorno virtual e instalar dependencias
python -m venv .venv
# Windows — activar el entorno
.venv\Scripts\activate
pip install -r requirements.txt
```

## Uso rápido

- Configurar variables en `.env` (o copiar `.env-example`). Parámetros principales:
    - `ECOSYSTEM`: Nombre del ecosistema objetivo (ej. `QISKIT`).
    - `INPUT_FILE`: Ruta al archivo de entrada JSON o especificación (ej. `abstraction2.json`).
    - `INPUT_LEVEL`: Nivel de abstracción inicial (1..6). Si se omite, se lee desde el `abstraction_level` en el archivo de entrada.
    - `OUTPUT_DIR`: Directorio base donde se guardan los resultados. Por cada ejecución se crea un subdirectorio con etiqueta de tiempo `DD_MM_YY_HH_MM`.
    - `LOG_FILE`: Ruta del archivo de log (opcional).

Ejemplo mínimo en `.env`:

```
ECOSYSTEM=QISKIT
INPUT_FILE=abstraction2.json
INPUT_LEVEL=2
OUTPUT_DIR=out
LOG_FILE=workflow.log
```

### Ejecutar el workflow

El runner crea por cada ejecución un subdirectorio dentro de `OUTPUT_DIR` con la etiqueta de tiempo en formato `DD_MM_YY_HH_MM` (por ejemplo `23_06_26_15_42`) y guarda en ese subdirectorio los archivos `abstraction3.json`, `abstraction4.json`, ... según se generen.

Ejecutar sin crear entorno virtual (usa el intérprete actual):

```bash
# Sitúate en la raíz del proyecto antes de ejecutar (ruta relativa)
cd ./lifia_um_quantum
python workflow.py
```

Crear un entorno virtual, instalar dependencias y ejecutar el workflow dentro de él:

```bash
# Sitúate en la raíz del proyecto antes de ejecutar
cd C:\Users\PC\desarrollo\lifia_um_quantum
python workflow.py --bootstrap
```

Al finalizar, el `summary` incluirá la ruta base y la ruta del subdirectorio de la ejecución.

### Verificación de paridad

Comprobar que los wrappers preservan exactamente las transformaciones originales:

```bash
# Sitúate en la raíz del proyecto antes de ejecutar (ruta relativa)
cd ./lifia_um_quantum
python -m tools.verify_parity
```

## Llamar a un conversor directamente

Ejemplo mínimo desde Python para ejecutar solo un paso:

```python
from convert import get_converter
import json

spec = json.load(open('abstraction2.json'))
conv = get_converter(2, 3)
out = conv.convert(spec)
print(out['abstraction_level'])
```

## Notas sobre desarrollo

- Los archivos originales están en `originals/` — por favor **no** editarlos directamente si se quiere preservar la trazabilidad. Los wrappers en `convert/` delegan a esas implementaciones.
- Para extender: añadir `convert/step_4to5.py` y `convert/step_5to6.py` reales, o implementar adaptadores por ecosistema en `shared/ecosystems.py`.
- El notebook `tests.ipynb` sirve para exploración interactiva; puede actualizarse con ejemplos de invocación del workflow.

## Próximos pasos sugeridos

- Implementar conversores reales `4->5` y `5->6`.
- Añadir tests automatizados (pytest) que ejecuten el workflow sobre matrices pequeñas y validen unitariedad final.
