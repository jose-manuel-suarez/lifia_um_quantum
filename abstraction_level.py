import importlib
import json
import os
import subprocess
import sys
import logging
import shutil
import importlib
import shlex
from pathlib import Path
import datetime

# Importación de módulos locales existentes
from shared.config import load_env
from shared.ecosystems import supports
from shared import io_utils as shared_io
from shared.env_vars import parse_arguments_and_env

# Importación de la capa modularizada de entorno virtual
from shared.venv_management import (
    ensure_venv,
    get_venv_python,
    pip_install,
    find_suitable_python,
    get_python_version,
    install_ecosystem_requirements
)

# Importación de la capa de verificación
from shared.verifications import run_mathematical_verifications

def run_workflow(env: dict, logger: logging.Logger) -> dict:
    """Ejecuta el flujo de trabajo de conversión basado en la configuración provista y realiza verificaciones."""
    
    # 1. Obtener los valores del entorno y limpiar barras iniciales/finales problemáticas
    input_dir_str = env.get("INPUT_DIR", "input").lstrip("\\/")
    output_dir = env.get("OUTPUT_DIR", "output").lstrip("\\/")
    input_filename_str = env.get("INPUT_FILE", "abstraction.json").lstrip("\\/")
    
   # 2. Construir la ruta combinada usando el directorio actual del proyecto como base
    base_project_dir = Path(__file__).resolve().parent
    
    # Ahora que no hay barras al principio, se concatenará de forma relativa impecable
    input_file = base_project_dir / input_dir_str / input_filename_str

    # Log de depuración inicial
    logger.info(f"[DEBUG] Buscando archivo de entrada en: {input_file}")

    # Verificar si el archivo realmente existe antes de abrirlo
    if not input_file.exists():
        logger.error(f"El archivo de entrada no existe en la ruta especificada: {input_file}")
        raise FileNotFoundError(f"No se encontró el archivo o directorio: '{input_file}'")

    ecosystem = env.get("ECOSYSTEM", "DEFAULT").upper()
    timestamp = datetime.datetime.now().strftime('%d_%m_%y__%H_%M')
    run_folder_name = f"run_shot_{ecosystem}_{timestamp}"

    output_path = base_project_dir / output_dir / run_folder_name
    output_path.mkdir(parents=True, exist_ok=True)

    # Guardamos la ruta absoluta limpia en formato string para compatibilidad de os.path
    run_dir = str(output_path.resolve())
    logger.info(f"Run output directory successfully created at: {run_dir}")

    # =========================================================================
    # PASO 1: Verificaciones matemáticas automatizadas
    # =========================================================================
    try:
        # Nota: Asegúrate de que 'run_mathematical_verifications' esté importada en el scope
        U_matrix, sub_matrices_json = run_mathematical_verifications(logger)
        
        if isinstance(sub_matrices_json, dict):
            serializable_verification = {
                k: (v.tolist() if hasattr(v, "tolist") else v) 
                for k, v in sub_matrices_json.items()
            }
        elif hasattr(sub_matrices_json, "tolist"):
            serializable_verification = sub_matrices_json.tolist()
        else:
            serializable_verification = sub_matrices_json

        verification_path = os.path.join(run_dir, "matrix_decomposition_check.json")
        shared_io.write_json_file(serializable_verification, verification_path, logger=logger)
        logger.info(f"Wrote mathematical verification breakdown to: {verification_path}")
        
    except Exception as e:
        logger.error(f"Mathematical verifications pipeline failed: {str(e)}")
        raise e

    # =========================================================================
    # PASO 2: Flujo de conversión secuencial
    # =========================================================================
    try:
        with open(input_file, "r", encoding="utf-8") as f:
            spec = json.load(f)
    except FileNotFoundError:
        logger.error(f"Input file {input_file} not found")
        raise

    start_level = int(env.get("INPUT_LEVEL", spec.get("abstraction_level", 1)))
    logger.info(f"Workflow starting: ecosystem={ecosystem} start_level={start_level}")

    current_spec = spec
    max_reached = start_level

    for level in range(start_level, 6):
        next_level = level + 1
        logger.info(f"Attempting conversion {level} -> {next_level}")
        try:
            module_name = f"conversion.step_{level}to{next_level}"
            converter_module = importlib.import_module(module_name)
            converter = converter_module
        except Exception:
            logger.info(f"No converter available for {level}->{next_level}, stopping conversion chain")
            break

        out_filename = f"{ecosystem}_levelabstraction_{next_level}.json"
        out_path = os.path.join(run_dir, out_filename)
        try:
            current_spec = converter.convert(current_spec, destination_file=None, ecosystem=ecosystem, logger=logger)
            shared_io.write_json_file(current_spec, out_path, logger=logger)
            logger.info(f"Wrote intermediate abstraction file: {out_path}")
        except Exception as e:
            logger.exception(f"Conversion {level}->{next_level} failed: {e}")
            break

        # Verificación de soporte del ecosistema
        try:
            if supports(ecosystem, next_level):
                logger.info(f"Ecosystem {ecosystem} supports abstraction level {next_level}")
                max_reached = next_level
            else:
                logger.warning(f"Ecosystem {ecosystem} DOES NOT fully support abstraction level {next_level}")
        except NameError:
            logger.warning("Function 'supports' is not defined in scope. Skipping ecosystem validation step.")
            max_reached = next_level

    summary = {
        "ecosystem": ecosystem,
        "start_level": start_level,
        "max_reached": max_reached,
        "output_base_dir": str(Path(output_dir).resolve()),
        "run_dir": run_dir,
    }

    logger.info(f"Workflow finished. Summary: {summary}")
    return summary


def _handle_bootstrap(args, env: dict, logger: logging.Logger) -> bool:
    """Encapsula la lógica de verificación, creación y reinvocación dentro del entorno virtual.
    
    Retorna True si el proceso debe finalizar inmediatamente en el padre.
    """
    venv_dir = Path(args.venv)
    venv_py = get_venv_python(venv_dir)

    if venv_dir.exists() and Path(sys.executable).resolve() == venv_py.resolve():
        logger.info("Already running inside target virtualenv; proceeding to run workflow")
        return False

    # Validar la existencia del archivo de entorno virtual o recrear el entorno existente
    if venv_dir.exists():
        venv_ver = get_python_version(venv_py)
        if venv_ver is not None and (venv_ver[0] > 3 or (venv_ver[0] == 3 and venv_ver[1] >= 10)):
            logger.info(f"Existing virtualenv at {venv_dir} uses Python {venv_ver[0]}.{venv_ver[1]}")
        else:
            logger.warning(f"Existing virtualenv at {venv_dir} uses Python {venv_ver or 'unknown'} which is < 3.10; recreating...")
            py_cmd = shlex.split(args.python_exe) if args.python_exe else find_suitable_python()
            if not py_cmd:
                raise RuntimeError("No suitable Python 3.10+ available to create virtualenv")
            
            shutil.rmtree(venv_dir)
            subprocess.run(py_cmd + ["-m", "venv", str(venv_dir)], check=True)
    else:
        # El entorno virtual no existe, se crea desde cero
        if sys.version_info < (3, 10):
            py_cmd = shlex.split(args.python_exe) if args.python_exe else find_suitable_python()
            if not py_cmd:
                raise RuntimeError("No suitable Python 3.10+ available to create virtualenv")
            logger.info(f"Creating virtualenv at {venv_dir} using: {' '.join(py_cmd)}")
            subprocess.run(py_cmd + ["-m", "venv", str(venv_dir)], check=True)
        else:
            ensure_venv(venv_dir, logger)

    venv_py = get_venv_python(venv_dir)

    # Instalación de dependencias básicas y específicas usando el módulo compartido venv_management
    pip_install(venv_py, Path(args.requirements), logger)
    install_ecosystem_requirements(venv_py, env.get("ECOSYSTEM", "").strip(), logger)

    # Reinvocación del script dentro del entorno virtual
    cmd = [str(venv_py), str(Path(__file__).resolve()), "--env", args.env, "--run-ts", datetime.datetime.now().isoformat()]
    if args.output_dir:
        cmd += ["--output-dir", args.output_dir]
        
    # En workflow.py dentro de _handle_bootstrap:
    logger.info(f"Re-invoking inside venv: {' '.join(cmd)}")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    
    if proc.returncode != 0:
        # Imprimir directamente en la consola estándar de MINGW64 para verlo al instante
        print("\n=== ERROR DETECTADO EN EL SUBPROCESO (VENV) ===", file=sys.stderr)
        print(proc.stderr, file=sys.stderr)
        print("================================================\n", file=sys.stderr)
        
        logger.error("Re-invoked process failed")
        logger.error("--- stdout ---\n" + (proc.stdout or ""))
        logger.error("--- stderr ---\n" + (proc.stderr or ""))
        raise subprocess.CalledProcessError(proc.returncode, cmd, output=proc.stdout, stderr=proc.stderr)
    
    logger.info("Re-invocation succeeded inside venv; exiting bootstrap parent process")
    return True


def main(argv=None):
    # Extracción de la inicialización y parseo de variables configuradas
    args, env, logger = parse_arguments_and_env(argv)

    # Manejo del bootstrapping aislado
    if args.bootstrap:
        try:
            should_exit = _handle_bootstrap(args, env, logger)
            if should_exit:
                return
        except RuntimeError as re_err:
            if "No suitable Python 3.10+" in str(re_err):
                logger.warning("Could not create a Python 3.10+ virtualenv; proceeding to run in current interpreter.")
            else:
                raise
        except Exception:
            logger.exception("Bootstrap failed")
            raise

    # Ejecución normal del workflow en el intérprete actual
    run_workflow(env=env, logger=logger)


if __name__ == "__main__":
    main()