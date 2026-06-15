"""Registry for ecosystem capabilities.

This is a lightweight mapping that can be extended with adapters that perform
real validation (e.g., trying to build a `QuantumCircuit`), but for now it
provides a configurable max supported abstraction level per ecosystem name.
"""

_MAP = {
    "QISKIT": 3,
    "DEFAULT": 2,
}


def max_supported(ecosystem_name: str) -> int:
    return _MAP.get(ecosystem_name.upper(), _MAP["DEFAULT"])


def supports(ecosystem_name: str, level: int) -> bool:
    return level <= max_supported(ecosystem_name)
