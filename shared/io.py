import json
import numpy as np


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
