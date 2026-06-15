import json
import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit.library import UnitaryGate, XGate

def json_to_circuit_abstraction2(circuit_spec: dict | str) -> QuantumCircuit:
    if isinstance(circuit_spec, str):
        spec = json.loads(circuit_spec)
    else:
        spec = circuit_spec

    n = spec["qubit_count"]
    qc = QuantumCircuit(n)

    for op in spec["operations"]:
        """Backward-compat shim: re-export circuit builders from shared.circuits."""

        from shared.circuits import json_to_circuit_abstraction2, json_to_circuit_abstraction3

        __all__ = ["json_to_circuit_abstraction2", "json_to_circuit_abstraction3"]