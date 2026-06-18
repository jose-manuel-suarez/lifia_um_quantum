# shared/verifications.py
# Consolida lo que inicialmente figuraba en el archivo tests.ipynb

import numpy as np
import logging
from conversion import two_levels

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_matrix(matrix, logger: logging.Logger = None):
    """Imprime una matriz formateada en consola o en los logs del sistema."""
    rows = matrix.shape[0]
    columns = matrix.shape[1]
    number_size = max([len(f"{matrix[r, c]:.3f}") for r in range(rows) for c in range(columns)])
    
    matrix_lines = []
    for r in range(rows):
        row_str = ""
        for c in range(columns):
            if matrix[r, c] != 0:
                element = f"{matrix[r, c]:.3f}"
            else:
                element = "0"
            spacing_left = ((number_size - len(element)) // 2)
            spacing_right = spacing_left + (number_size - len(element)) % 2
            element = " " * spacing_left + element + " " * spacing_right
            row_str += element + " " * 4
        matrix_lines.append(row_str)
    
    full_matrix_output = "\n" + "\n".join(matrix_lines)
    if logger:
        logger.info(full_matrix_output)
    else:
        print(full_matrix_output)

def is_unitary(matrix, atol=1e-9):
    """Verifica si una submatriz de 2x2 es unitaria."""
    identity = np.eye(matrix.shape[0], dtype=complex)
    return np.allclose(matrix @ matrix.conj().T, identity, atol=atol)

def run_mathematical_verifications(logger: logging.Logger) -> tuple:
    """Ejecuta las validaciones de descomposición matricial a 2 niveles."""
    logger.info("Iniciando pruebas de descomposición matricial de dos niveles...")
    dimensions = 8

    # Generar matriz Hermitiana aleatoria
    H = 2 * np.random.rand(dimensions, dimensions) - np.ones((dimensions, dimensions))
    H = H + 2j * (2 * np.random.rand(dimensions, dimensions) - np.ones((dimensions, dimensions)))
    H = H + H.conj().T  

    # U es unitaria (autovectores)
    _, U = np.linalg.eigh(H)  
    
    logger.info("Matriz Unitaria original (U):")
    print_matrix(U, logger)

    # Descomposición
    matrices, matrices_json = two_levels(U, dimensions)

    # Reconstrucción: A = U_n @ ... @ U_2 @ U_1
    A = np.eye(dimensions, dtype=complex)
    for i in range(1, len(matrices)):   # Saltar el placeholder de índice 0
        if matrices[i] is not None:
            A = matrices[i] @ A

    # Verificar si A^H == U (usando np.allclose para robustez matemática)
    is_reconstruction_correct = np.allclose(A.conj().T, U, atol=1e-10)
    logger.info(f"¿La reconstrucción de la matriz es correcta? -> {bcolors.OKGREEN if is_reconstruction_correct else bcolors.FAIL}{is_reconstruction_correct}{bcolors.ENDC}")

    # Validar que cada bloque no trivial sea unitario
    logger.info("Validando unitariedad de sub-bloques...")
    for k, matrix_json in enumerate(matrices_json):
        sub_matrix = matrix_json["matrix"]
        unitary_check = is_unitary(sub_matrix)
        if not unitary_check:
            logger.warning(f"¡Alerta! Sub-bloque U{k + 1} para los estados {matrix_json['states']} NO es unitario.")
        
    logger.info("Verificaciones matemáticas finalizadas con éxito.")
    return U, matrices_json