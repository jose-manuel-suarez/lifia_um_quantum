# conversion/step_3to4.py
import json
from typing import Optional
import logging
from shared.factory import create_operation
from shared.io_utils import write_json_file

def convert_3to4(circuit_spec: dict | str, destination_file: Optional[str] = None, logger: Optional[logging.Logger] = None) -> dict:
    '''
    Convert a quantum circuit specification from abstraction level 3 to abstraction level 4.
    Muta las operaciones del circuito utilizando polimorfismo orientado a objetos.
    '''

    # Carga inicial del JSON de entrada (Nivel 3)
    raw_data = json.loads(circuit_spec) if isinstance(circuit_spec, str) else circuit_spec
    qubit_count = raw_data["qubit_count"]
    ancilla_qubits = raw_data.get("ancilla_qubits", [])

    # Convertir la lista de operaciones crudas a objetos del dominio polimórficos
    operations_objects = [create_operation(op) for op in raw_data.get("operations", [])]

    # Ejecutar la mutación hacia el Nivel 4 delegando la lógica en cada objeto
    level_4_operations = []
    for operation in operations_objects:
        transformed_ops = operation.to_level_4(qubit_count)
        level_4_operations.extend(transformed_ops)

    # Construir la estructura final del circuito para el Nivel 4
    circuit_result = {
        "abstraction_level": 4,
        "qubit_count": qubit_count,
        "ancilla_qubits": ancilla_qubits,  # Mantiene las ancillas asignadas o se procesan según tu criterio
        "operations": [op.to_dict() for op in level_4_operations]
    }

    # 5. Guardado seguro e independiente controlado internamente por la librería auxiliar de I/O
    write_json_file(circuit_result, destination_file, logger=logger)

    return circuit_result