import json
import numpy as np

try:
    from qiskit import QuantumCircuit
    from qiskit.circuit.library import UnitaryGate, XGate
    QISKIT_AVAILABLE = True
except Exception:  # pragma: no cover - optional dependency
    QISKIT_AVAILABLE = False


def json_to_circuit_abstraction2(circuit_spec: dict | str) -> QuantumCircuit:
    if not QISKIT_AVAILABLE:
        raise ImportError("qiskit is not available in this environment")

    if isinstance(circuit_spec, str):
        spec = json.loads(circuit_spec)
    else:
        spec = circuit_spec

    n = spec["qubit_count"]
    qc = QuantumCircuit(n)

    for op in spec["operations"]:
        op_type = op["type"]
        targets = op["targets"]
        controls = op.get("controls", [])

        # Build ctrl_state bitmask (shared by both branches)
        ctrl_state = 0
        for i, ctrl in enumerate(controls):
            if ctrl["state"] == "1":
                ctrl_state |= (1 << i)
        ctrl_qubits = [c["qubit"] for c in controls]

        if op_type == "generalized_toffoli":
            gate = XGate()
            if controls:
                gate = gate.control(len(controls), ctrl_state=ctrl_state)
            qc.append(gate, ctrl_qubits + targets)

        else:
            raw = op["unitary"]["matrix"]
            matrix = np.array(
                [
                    [
                        (c["real"] + 1j * c["imag"] if isinstance(c, dict) else complex(c))
                        for c in row
                    ]
                    for row in raw
                ],
                dtype=complex,
            )
            gate = UnitaryGate(matrix)
            if controls:
                gate = gate.control(len(controls), ctrl_state=ctrl_state)
            qc.append(gate, ctrl_qubits + targets)

    return qc


def json_to_circuit_abstraction3(circuit_spec: dict | str) -> QuantumCircuit:
    if not QISKIT_AVAILABLE:
        raise ImportError("qiskit is not available in this environment")

    if isinstance(circuit_spec, str):
        spec = json.loads(circuit_spec)
    else:
        spec = circuit_spec

    n = spec["qubit_count"]
    total_qubits = n + len(spec.get("ancilla_qubits", []))
    qc = QuantumCircuit(total_qubits)

    for op in spec["operations"]:
        op_type = op["type"]
        targets = op["targets"]
        controls = op.get("controls", [])

        ctrl_state = 0
        for i, ctrl in enumerate(controls):
            if str(ctrl["state"]) == "1":
                ctrl_state |= (1 << i)
        ctrl_qubits = [c["qubit"] for c in controls]

        if op_type == "generalized_toffoli":
            gate = XGate()
            if controls:
                gate = gate.control(len(controls), ctrl_state=ctrl_state)
            qc.append(gate, ctrl_qubits + targets)

        elif op_type in ("singy_controlled_unitary", "singly_controlled_unitary", "controlled_unitary"):
            raw = op["unitary"]["matrix"]
            matrix = np.array(
                [
                    [
                        (c["real"] + 1j * c["imag"] if isinstance(c, dict) else complex(c))
                        for c in row
                    ]
                    for row in raw
                ],
                dtype=complex,
            )
            gate = UnitaryGate(matrix)
            if controls:
                gate = gate.control(len(controls), ctrl_state=ctrl_state)
            qc.append(gate, ctrl_qubits + targets)

        else:
            raise ValueError(f"Unknown operation type: {op_type}")

    return qc
