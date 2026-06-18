from shared.domain import ControlledUnitary, GeneralizedToffoli, SinglyControlledUnitary, QuantumOperation

# Mapa que asocia el string del JSON con su clase de objeto correspondiente
OPERATION_MAPPING = {
    "controlled_unitary": ControlledUnitary,
    "generalized_toffoli": GeneralizedToffoli,
    "singy_controlled_unitary": SinglyControlledUnitary
}

def create_operation(op_data: dict) -> QuantumOperation:
    '''Instancia la clase específica basándose en el tipo.'''

    op_type = op_data.get("type")
    target_class = OPERATION_MAPPING.get(op_type)
    
    if not target_class:
        raise ValueError(f"Tipo de operación desconocido: {op_type}")
        
    return target_class(**op_data)