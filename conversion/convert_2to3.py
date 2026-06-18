import numpy as np
import json

def convert_2to3(circuit_spec: dict | str, destination_file = None):
    '''
    Convert a quantum circuit specification from abstraction level 2 to abstraction level 3.
    This conversion transforms multicontrolled unitary operations into a sequence of generalized toffoli and controlled unitary operations.
    Parameters:
        circuit_spec (dict | str): The quantum circuit specification at abstraction level 2.
        destination_file (str, optional): The file path to save the converted specification.

    Returns:
        dict: The converted quantum circuit specification at abstraction level 3.
    '''

    if isinstance(circuit_spec, str):
        spec = json.loads(circuit_spec)
    else:
        spec = circuit_spec

    qubit_count = spec["qubit_count"]

    # Transform multicontrolled U to toffoli and controlled U:
    circuit = {
        "abstraction_level": 3,
        "qubit_count": qubit_count,
        "ancilla_qubits": [qubit_count],
        "operations": []
    }

    for operation in spec["operations"]:
        if operation["type"] == "controlled_unitary":

            generalized_toffoli = {
            "type": "generalized_toffoli",
            "targets": [qubit_count],
            "controls": operation["controls"],
            "unitary": {
                "matrix": [
                    [0, 1],
                    [1, 0]
                ]
                }
            }

            controlled_unitary = {
                "type": "singy_controlled_unitary",
                "targets": operation["targets"],
                "controls": [
                    {"qubit": qubit_count, "state": 0}
                ],
                "unitary": operation["unitary"]
            }

            circuit["operations"].append(generalized_toffoli)
            circuit["operations"].append(controlled_unitary)
            circuit["operations"].append(generalized_toffoli)

        elif operation["type"] == "generalized_toffoli":

            circuit["operations"].append(operation)


    if destination_file:
        with open(destination_file, "w") as f:
            json.dump(circuit, f, indent=2)

    return circuit

