import json
from typing import Optional
import logging
from shared.factory import create_operation
# Importación de tu librería auxiliar de I/O
from shared.io import write_json_file

def convert_2to3(circuit_spec: dict | str, destination_file: Optional[str] = None, logger: Optional[logging.Logger] = None) -> dict:
    '''
    Convert a quantum circuit specification from abstraction level 2 to abstraction level 3.
    Operando mediante estructuras de objetos polimórficos y delegando el I/O por completo.
    '''

    # Carga inicial del JSON
    raw_data = json.loads(circuit_spec) if isinstance(circuit_spec, str) else circuit_spec
    qubit_count = raw_data["qubit_count"]

    # Conversión de la lista de diccionarios JSON crudos a objetos polimórficos
    operations_objects = [create_operation(op) for op in raw_data.get("operations", [])]

    # Ejecución de la mutación polimórfica hacia Nivel 3
    level_3_operations = []
    for operation in operations_objects:
        transformed_ops = operation.to_level_3(qubit_count)
        level_3_operations.extend(transformed_ops)

    # Construir la estructura final del circuito como diccionario
    circuit_result = {
        "abstraction_level": 3,
        "qubit_count": qubit_count,
        "ancilla_qubits": [qubit_count],
        "operations": [op.to_dict() for op in level_3_operations]
    }

    write_json_file(circuit_result, destination_file, logger=logger)

    return circuit_result