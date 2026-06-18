import json
import logging
from pathlib import Path
from typing import Optional, Union

def write_json_file(data: dict, destination_file: Optional[Union[str, Path]], logger: Optional[logging.Logger] = None) -> None:
    """Valida la ruta de destino y escribe un diccionario JSON."""
    log = logger or logging.getLogger(__name__)

    if not destination_file:
        log.warning("No destination file path was provided; process completed only in memory.")
        return

    try:
        out_path = Path(destination_file)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            
        log.info(f"Specification successfully saved to: {destination_file}")
        
    except Exception as e:
        log.error(f"Failed to write destination file at '{destination_file}': {str(e)}")


def get_project_root() -> Path:
    from pathlib import Path
    """Busca hacia arriba en el árbol de directorios hasta encontrar el ancla del proyecto."""
    current = Path(__file__).resolve()
    
    # Recorremos hacia arriba buscando un archivo indicador de la raíz
    for parent in [current] + list(current.parents):
        if (parent / ".git").exists() or (parent / ".env").exists():
            return parent
            
    # Si no encuentra nada, por defecto devuelve el padre del script actual
    return current.parent

def json_matrix_to_numpy():
    pass

def complex_matrix_to_json():
    pass
