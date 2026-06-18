import numpy as np
import json

def two_levels_decompose(U: np.ndarray, dimensions: int) -> list:
    """Given a matrix U, return the two-level matrix decomposition.

    The decomposition is represented by an array of python dictionaries of the form:
        {
            "states" = [state1, state2], 
            "matrix" = Ui
        }
    """

    if U.shape[0] != U.shape[1]:
        raise ValueError("Non-square matrix")
    if U.shape[0] <= 1:
        raise ValueError("Unitary matrix should have dimensions >= 2")

    n = U.shape[0]

    # Total matrix count: n*(n-1)//2 + 1, stored at indices 1..n*(n-1)//2+1
    # Index 0 is left as None to preserve the same 1-based indexing as Octave
    total = n * (n - 1) // 2
    matrices = [None] * (total + 1)

    matrices_json = []

    A = U.astype(complex).copy()

    # Zero out the first column of A below the diagonal
    for i in range(2, n + 1):             # i = 2..n  (Octave 1-based)
        Ui = np.eye(n, dtype=complex)
        Ui_2by2 = np.eye(2, dtype = complex)
        a = A[0, 0]

        if abs(A[i - 1, 0]) > 1e-5:
            b = A[i - 1, 0]
            norm_ab = np.linalg.norm([a, b])
            Ui[0,     0    ] =  np.conj(a) / norm_ab
            Ui[i - 1, i - 1] = -a          / norm_ab
            Ui[0,     i - 1] =  np.conj(b) / norm_ab
            Ui[i - 1, 0    ] =  b          / norm_ab

            Ui_2by2[0, 0] =  np.conj(a) / norm_ab
            Ui_2by2[1, 1] = -a          / norm_ab
            Ui_2by2[0, 1] =  np.conj(b) / norm_ab
            Ui_2by2[1, 0] =  b          / norm_ab

        else:
            Ui[0, 0] = np.conj(a)

        json_Ui = {"states": [dimensions - n, dimensions - n + i - 1], "matrix": Ui_2by2}

        Mi = np.eye(dimensions, dtype=complex)
        Mi[dimensions - n : dimensions,
           dimensions - n : dimensions] = Ui

        matrices_json.append(json_Ui)
        matrices[i - 1] = Mi              # Octave: matrices(:,:, i-1)
        A = Ui @ A

    if n == 3:
        matrices_json.append({"states": [dimensions - 2, dimensions - 1], "matrix": A[1:, 1:].conj().T})

        Mi = np.eye(dimensions, dtype=complex)
        Mi[dimensions - 2 : dimensions,
           dimensions - 2 : dimensions] = A[1:, 1:].conj().T

        matrices[3] = Mi

        return matrices, matrices_json

    else:
        recursive_matrices, recursive_matrices_json = two_levels_decompose(A[1:, 1:], dimensions)

        # Map recursive index j -> current index (n-1)+j
        rec_count = len(recursive_matrices) - 1   # valid entries (index 0 is None)
        for j in range(1, rec_count + 1):
            matrices[n - 1 + j] = recursive_matrices[j]
            matrices_json.append(recursive_matrices_json[j-1])

    return matrices, matrices_json



def is_unitary(U, tol=1e-10):
    """Helper method to check if matrix U is unitary within a given tolerance"""
    U_dagger = U.conj().T
    identity = np.eye(U.shape[0])

    return np.allclose(U_dagger @ U, identity, atol=tol)



def complex_matrix_to_json(matrix):
    return [
        [
            {
                "real": float(x.real),
                "imag": float(x.imag)
            }
            for x in row
        ]
        for row in matrix
    ]



def toffoli_decomposition(state1: int, state2: int, qubit_count: int, U: np.ndarray):
    """Given a 2 by 2 matrix U and two states, return a JSON with the Toffoli decomposition"""

    bin_state1 = bin(state1)[2:]
    bin_state1 = list("0"*(qubit_count - len(bin_state1)) + bin_state1)   # Fill bin_state1 with zeros on the left

    bin_state2 = bin(state2)[2:]
    bin_state2 = list("0"*(qubit_count - len(bin_state2)) + bin_state2)  # Fill bin_state2 with zeros on the left

    circuit = {
        "qubit_count": qubit_count,
        "operations": []
    }

    current_state = bin_state1
    difference = [q for q in range(qubit_count) if current_state[q] != bin_state2[q]]
    while len(difference) > 1:

        q = difference[0]

        generalized_toffoli = {
            "type": "generalized_toffoli",
            "targets": [q],
            "controls": [
                {"qubit": t, "state": current_state[t]}
                for t in range(qubit_count) if t != q
            ],
            "unitary": {
                "matrix": [
                    [0, 1],
                    [1, 0]
                ]
            }
        }

        circuit["operations"].append(generalized_toffoli)

        # update current state:
        current_state[q] = str(1 - int(current_state[q]))

        difference = [q for q in range(qubit_count) if current_state[q] != bin_state2[q]]

    k = len(circuit["operations"])

    q = difference[0]
    controlled_U = {
        "type": "controlled_unitary",
        "targets": [q],
        "controls": [
            {"qubit": t, "state": current_state[t]}
            for t in range(qubit_count) if t != q
        ],
        "unitary": {
            "matrix":  complex_matrix_to_json(U)
        }
    }

    circuit["operations"].append(controlled_U)

    for i in range(k):
        circuit["operations"].append(circuit["operations"][k - i - 1])

    return circuit



def convert_1to2(U: np.ndarray, destination_file = None):
    """Given a circuit with abstraction level = 1, generate a circuit with abstraction level = 2."""

    if U.shape[0] != U.shape[1] or not is_unitary(U):
        raise ValueError("U must be a unitary square matrix")

    dimensions = U.shape[0]
    qubit_count = int(np.log2(dimensions))

    if (2**qubit_count != dimensions):
        raise ValueError("U must be a 2^n times 2^n matrix")

    _, matrices_json = two_levels_decompose(U, dimensions)

    circuit = {
        "abstraction_level": 2,
        "qubit_count": qubit_count,
        "ancilla_qubits": [],
        "operations": []
    }

    for matrix_json in matrices_json:
        sub_circuit = toffoli_decomposition(matrix_json["states"][0], matrix_json["states"][1], qubit_count, matrix_json["matrix"])
        append_sub_circuit(circuit, sub_circuit)

    if destination_file:
        with open(destination_file, "w") as f:
            json.dump(circuit, f, indent=2)

    return circuit



def append_sub_circuit(circuit, sub_circuit):
    """Append sub_circuit operations into circuit."""

    if (sub_circuit["qubit_count"] != circuit["qubit_count"]):
        raise ValueError("Both circuits must have the same number of qubits")

    for operation in sub_circuit["operations"]:
        circuit["operations"].append(operation)

