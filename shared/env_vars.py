import os
import argparse

from datetime import datetime
from pathlib import Path
from shared.logger import get_logger
from shared.config import load_env

def parse_arguments_and_env(argv=None):
    """
    Parsea los argumentos de línea de comandos, carga el entorno configurado
    y prepara las variables iniciales del sistema (logs, timestamps, etc.).
    """
    parser = argparse.ArgumentParser(description="Run the conversion workflow (optional bootstrap)")
    parser.add_argument("--env", default=".env", help="Env file to load")
    parser.add_argument("--output-dir", default=None, help="Base output directory (overrides .env OUTPUT_DIR)")
    parser.add_argument("--bootstrap", action="store_true", help="Create venv, install requirements and run inside it")
    parser.add_argument("--venv", default=".venv", help="Virtualenv directory to create/use")
    parser.add_argument("--requirements", default="requirements/requirements.txt")
    parser.add_argument("--run-ts", default=None, help="(internal) reuse the given run timestamp")
    parser.add_argument("--python-exe", default=None, help="Optional python executable command or path")
    args = parser.parse_args(argv)

    # Carga centralizada de entorno
    env = load_env(args.env)

    # Configuración de logs y marcas de tiempo
    time_stamp = args.run_ts or datetime.now().strftime("%d_%m_%y__%H_%M")
    base_log_dir = Path(env.get("LOG_DIR", "logs"))
    os.makedirs(base_log_dir, exist_ok=True)
    log_filename = f"level_abstraction_shot_{env.get('ECOSYSTEM', 'DEFAULT')}_{time_stamp}.log"
    logger = get_logger("lifia_workflow", log_file=str(base_log_dir / log_filename))

    return args, env, time_stamp, logger