# shared/domain.py
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional

@dataclass
class ControlQubit:
    qubit: int
    state: int

class QuantumOperation(ABC):
    '''
    Clase base abstracta para todas las operaciones cuánticas del circuito.
    Obliga a cada operación a definir su propia regla de descomposición matemática
    a través de los distintos niveles de abstracción del artículo.
    '''

    """Nivel 1: Representado por cualquier matriz arbitraria unitaria (U)."""

    @abstractmethod
    def to_level_2(self, qubit_count: int) -> List["QuantumOperation"]:
        """Nivel 2: Reduce U a C^(n-1)(U) y Toffolis generalizadas."""
        pass

    @abstractmethod
    def to_level_3(self, qubit_count: int) -> List["QuantumOperation"]:
        """Nivel 3: Reduce controles múltiples de C^(n-1)(U) a C(U) usando una ancila."""
        pass

    @abstractmethod
    def to_level_4(self, qubit_count: int) -> List["QuantumOperation"]:
        """Nivel 4: Reduce recursivamente Toffolis generalizadas C^k(X) a Toffoli estándar C2(X)."""
        pass

    @abstractmethod
    def to_level_5(self, qubit_count: int) -> List["QuantumOperation"]:
        """Nivel 5: Descompone las compuertas C(U) en CNOTs y rotaciones (Ry, Rz, X)."""
        pass

    @abstractmethod
    def to_level_6(self, qubit_count: int) -> List["QuantumOperation"]:
        """Nivel 6: Máxima desagregación. Descompone la Toffoli estándar (C2(X)) en CNOT y 1-qubit."""
        pass

    def to_dict(self) -> dict:
        """Convierte la estructura y atributos del objeto a un diccionario JSON-friendly."""
        return asdict(self)


@dataclass
class GeneralizedToffoli(QuantumOperation):
    """Representa una compuerta Toffoli Generalizada C^k(X) con controles arbitrarios."""
    type: str
    targets: List[int]
    controls: List[ControlQubit]
    unitary: Dict[str, Any]

    def __post_init__(self):
        self.controls = [c if isinstance(c, ControlQubit) else ControlQubit(**c) for c in self.controls]

    def to_level_3(self, qubit_count: int) -> List[QuantumOperation]:
        # El Nivel 3 mantiene y soporta las Generalized Toffoli nativamente.
        return [self]

    def to_level_4(self, qubit_count: int) -> List[QuantumOperation]:
        # TODO: Implementar Teorema II.6 (Reducción recursiva de C^k(X) a C2(X) con ancilas)
        # Por el momento, si actúa como un placeholder, se retorna a sí misma.
        return [self]

    def to_level_5(self, qubit_count: int) -> List[QuantumOperation]:
        # Lógica no implementada aún para este objeto (Nivel 4 -> Nivel 5)
        return [self]

    def to_level_6(self, qubit_count: int) -> List[QuantumOperation]:
        # Lógica no implementada aún para este objeto (Nivel 5 -> Nivel 6)
        return [self]


@dataclass
class ControlledUnitary(QuantumOperation):
    """Representa una operación unitaria multicontrolada arbitraria C^(n-1)(U)."""
    type: str
    targets: List[int]
    controls: List[ControlQubit]
    unitary: Dict[str, Any]

    def __post_init__(self):
        self.controls = [c if isinstance(c, ControlQubit) else ControlQubit(**c) for c in self.controls]

    def to_level_3(self, qubit_count: int) -> List[QuantumOperation]:
        # Teorema II.5: Se descompone en el sándwich Toffoli Generalizada -> C(U) simple -> Toffoli Generalizada
        toffoli = GeneralizedToffoli(
            type="generalized_toffoli",
            targets=[qubit_count],  # Utiliza el qubit auxiliar (ancila)
            controls=self.controls,
            unitary={"matrix": [[0, 1], [1, 0]]}
        )
        
        singly_controlled = SinglyControlledUnitary(
            type="singy_controlled_unitary",
            targets=self.targets,
            controls=[ControlQubit(qubit=qubit_count, state=0)],
            unitary=self.unitary
        )
        
        return [toffoli, singly_controlled, toffoli]

    def to_level_4(self, qubit_count: int) -> List[QuantumOperation]:
        # Si se procesa desde este punto, primero pasa por L3 y luego reduce sus componentes a L4
        ops_l3 = self.to_level_3(qubit_count)
        ops_l4 = []
        for op in ops_l3:
            ops_l4.extend(op.to_level_4(qubit_count))
        return ops_l4

    def to_level_5(self, qubit_count: int) -> List[QuantumOperation]:
        # Encadena la transformación hacia el nivel 5 pasando jerárquicamente por el nivel anterior
        ops_l4 = self.to_level_4(qubit_count)
        ops_l5 = []
        for op in ops_l4:
            ops_l5.extend(op.to_level_5(qubit_count))
        return ops_l5

    def to_level_6(self, qubit_count: int) -> List[QuantumOperation]:
        # Encadena la transformación completa hasta el nivel 6
        ops_l5 = self.to_level_5(qubit_count)
        ops_l6 = []
        for op in ops_l5:
            ops_l6.extend(op.to_level_6(qubit_count))
        return ops_l6


@dataclass
class SinglyControlledUnitary(QuantumOperation):
    """Representa una compuerta unitaria controlada por un único qubit C(U)."""
    type: str
    targets: List[int]
    controls: List[ControlQubit]
    unitary: Dict[str, Any]

    def __post_init__(self):
        self.controls = [c if isinstance(c, ControlQubit) else ControlQubit(**c) for c in self.controls]

    def to_level_3(self, qubit_count: int) -> List[QuantumOperation]:
        # Ya cumple con las restricciones de Nivel 3
        return [self]

    def to_level_4(self, qubit_count: int) -> List[QuantumOperation]:
        # Ya cumple con las restricciones de Nivel 4 (Compuerta controlada estandarizada de baja aridad)
        return [self]

    def to_level_5(self, qubit_count: int) -> List[QuantumOperation]:
        # TODO: Implementar Teorema II.7 / Descomposición de C(U) usando CNOT y rotaciones (Ry, Rz, X)
        # Pendiente de implementación concreta. Retorna self provisoriamente.
        return [self]

    def to_level_6(self, qubit_count: int) -> List[QuantumOperation]:
        # Lógica no implementada aún para este objeto (Nivel 5 -> Nivel 6)
        return [self]


@dataclass
class QuantumCircuitSpec:
    """Contenedor semántico y DTO para el circuito cuántico completo en cualquier nivel."""
    abstraction_level: int
    qubit_count: int
    operations: List[QuantumOperation]
    ancilla_qubits: Optional[List[int]] = None

    @classmethod
    def from_dict(cls, data: dict) -> "QuantumCircuitSpec":
        """Factory method que parsea el JSON crudo delegando la instanciación a la factoría."""
        from shared.factory import create_operation  # Importación diferida para evitar ciclos
        ops = [create_operation(op) for op in data.get("operations", [])]
        return cls(
            abstraction_level=data["abstraction_level"],
            qubit_count=data["qubit_count"],
            operations=ops,
            ancilla_qubits=data.get("ancilla_qubits")
        )

    def to_dict(self) -> dict:
        """Exporta la especificación completa del circuito a un diccionario compatible con JSON."""
        return {
            "abstraction_level": self.abstraction_level,
            "qubit_count": self.qubit_count,
            "ancilla_qubits": self.ancilla_qubits if self.ancilla_qubits is not None else [],
            "operations": [op.to_dict() for op in self.operations]
        }