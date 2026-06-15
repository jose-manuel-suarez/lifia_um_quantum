import json
from typing import Union
import numpy as np
from convert._originals_adapter import delegate
from shared.io import json_matrix_to_numpy, write_json_file


_orig_convert = delegate("two_level_decomposition", "convert_1to2")


def convert(circuit_spec: Union[dict, str, np.ndarray], destination_file=None, ecosystem=None, logger=None):
    """
    Accepts a numpy unitary matrix or a spec containing a 'unitary' field with the same JSON format
    used elsewhere in the project.
    """
    if isinstance(circuit_spec, str):
        spec = json.loads(circuit_spec)
    else:
        spec = circuit_spec

    if isinstance(spec, np.ndarray):
        U = spec
    elif isinstance(spec, dict) and "unitary" in spec:
        U = json_matrix_to_numpy(spec["unitary"]["matrix"])
    elif isinstance(spec, dict) and "matrix" in spec:
        U = json_matrix_to_numpy(spec["matrix"])
    else:
        raise ValueError("Unsupported input for step_1to2: expected numpy array or dict with 'unitary' or 'matrix'.")

    if logger:
        logger.info("Invoking original two_level_decomposition.convert_1to2")

    circuit = _orig_convert(U, destination_file=None)

    if destination_file:
        write_json_file(circuit, destination_file)

    return circuit
