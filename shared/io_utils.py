# shared/io.py
import json
import numpy as np
import logging
from pathlib import Path
from typing import Optional
from typing import Optional, Union

print("--- CARGANDO SHARED/IO.PY CON PARAMETRO LOGGER ---")
def write_json_file(data: dict, destination_file: Optional[Union[str, Path]], logger: Optional[logging.Logger] = None) -> None:
    """
    Valida la ruta de destino y escribe un diccionario JSON.
    Controla de forma interna las excepciones y los logs del estado de la escritura.
    """
    
    # Garantizar un logger activo para el módulo si no se provee uno
    log = logger or logging.getLogger(__name__)

    if not destination_file:
        log.warning("No destination file path was provided; process completed only in memory.")
        return

    try:
        out_path = Path(destination_file)
        # Asegura que los directorios padres existan antes de escribir
        out_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            
        log.info(f"Specification successfully saved to: {destination_file}")
        
    except Exception as e:
        log.error(f"Failed to write destination file at '{destination_file}': {str(e)}")


def json_matrix_to_numpy(raw):
    """Convert the project's JSON complex-matrix format to a numpy array."""
    return np.array(
        [
            [
                (c["real"] + 1j * c["imag"]) if isinstance(c, dict) else complex(c)
                for c in row
            ]
            for row in raw
        ],
        dtype=complex,
    )


def complex_matrix_to_json(matrix):
    return [
        [
            {"real": float(x.real), "imag": float(x.imag)}
            for x in row
        ]
        for row in matrix
    ]


def write_json_file(obj, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
